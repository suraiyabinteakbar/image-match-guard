"""Batch job: run every unprocessed image through the vision model."""
import csv
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError
from sqlalchemy import func, select

from app.db import CostLog, Image, Job, SessionLocal, init_db
from app.schemas import ImageMetadata
from app.vision import analyze_image, make_client

load_dotenv()

IMG_DIR = Path("data/images")
TRUTH_CSV = Path("data/ground_truth.csv")
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 2
MAX_FAILS_IN_A_ROW = 3  # circuit breaker: stop if this many images fail back to back
PAUSE_SECONDS = float(os.getenv("SECONDS_BETWEEN_CALLS", "4"))  # stay under free-tier limits
CONFIDENCE_MIN = float(os.getenv("CONFIDENCE_MIN", "0.60"))
MAX_BUDGET_USD = float(os.getenv("MAX_BUDGET_USD", "1.00"))
PRICE_IN_PER_M = float(os.getenv("PRICE_INPUT_PER_M_TOKENS", "0"))   # free tier: 0
PRICE_OUT_PER_M = float(os.getenv("PRICE_OUTPUT_PER_M_TOKENS", "0"))


def utcnow():
    return datetime.now(timezone.utc)


def load_truth():
    if not TRUTH_CSV.exists():
        return {}
    with open(TRUTH_CSV, newline="", encoding="utf-8") as f:
        return {r["filename"]: r["true_subject"] for r in csv.DictReader(f)}


def seed_images(s):
    """Add a row for every file in data/images that is not in the DB yet."""
    truth = load_truth()
    known = set(s.scalars(select(Image.filename)))
    for path in sorted(IMG_DIR.glob("*.jpg")):
        if path.name in known:
            continue
        # for non-ambiguous files the label comes from the filename: check them by eye
        label = truth.get(path.name) or path.name.split("_")[0]
        s.add(Image(filename=path.name, true_subject=label))
    s.commit()


def spent(s):
    return s.scalar(select(func.coalesce(func.sum(CostLog.cost_usd), 0.0)))


def log_call(s, model, image_id, tin, tout, status):
    cost = ((tin or 0) * PRICE_IN_PER_M + (tout or 0) * PRICE_OUT_PER_M) / 1_000_000
    s.add(CostLog(kind="vision", model=model, image_id=image_id,
                  input_tokens=tin, output_tokens=tout, cost_usd=cost, status=status))
    s.commit()


def process_one(s, client, model, img, job):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            text, tin, tout = analyze_image(client, model, IMG_DIR / img.filename)
        except Exception as e:  # network error, rate limit, API error
            log_call(s, model, img.id, None, None, "error")
            job.error = f"{img.filename}: {str(e)[:300]}"
            if attempt < MAX_ATTEMPTS:
                job.retries += 1
                s.commit()
                time.sleep(BACKOFF_SECONDS * 2 ** (attempt - 1))
            continue

        try:
            meta = ImageMetadata.model_validate_json(text)
        except ValidationError as e:
            log_call(s, model, img.id, tin, tout, "invalid")
            job.error = f"{img.filename}: invalid output ({str(e)[:200]})"
            if attempt < MAX_ATTEMPTS:
                job.retries += 1
                s.commit()
            continue

        log_call(s, model, img.id, tin, tout, "ok")
        img.subject = meta.subject
        img.group_name = meta.group
        img.category = meta.category
        img.attributes = meta.attributes
        img.caption = meta.caption
        img.confidence = meta.confidence
        img.flagged = meta.confidence < CONFIDENCE_MIN
        img.processed_at = utcnow()
        s.commit()
        return True
    s.commit()  # save job.error from the last failed attempt
    return False


def run(limit=None):
    init_db()
    model = os.getenv("GEMINI_MODEL")
    with SessionLocal() as s:
        seed_images(s)
        todo = list(s.scalars(
            select(Image).where(Image.processed_at.is_(None)).order_by(Image.filename)))
        if limit:
            todo = todo[:limit]

        job = Job(kind="vision", status="running", total=len(todo))
        s.add(job)
        s.commit()
        print(f"Job {job.id}: {len(todo)} images to process")

        client = make_client()
        streak = 0  # failures in a row
        for img in todo:
            if spent(s) >= MAX_BUDGET_USD:
                job.status = "aborted"
                job.error = f"budget of {MAX_BUDGET_USD} USD reached"
                s.commit()
                print("Stopped: budget reached")
                return job.id

            if process_one(s, client, model, img, job):
                job.done += 1
                streak = 0
                print(f"[{job.done + job.failed}/{job.total}] {img.filename}: "
                      f"{img.group_name} {img.confidence:.2f}"
                      f"{'  FLAGGED' if img.flagged else ''}")
            else:
                job.failed += 1
                streak += 1
                print(f"[{job.done + job.failed}/{job.total}] {img.filename}: FAILED")
                if streak >= MAX_FAILS_IN_A_ROW:
                    job.status = "aborted"
                    s.commit()
                    print(f"Stopped: {MAX_FAILS_IN_A_ROW} failures in a row. "
                          "Run scripts/show_errors.py to see why, then re-run.")
                    return job.id
            s.commit()
            time.sleep(PAUSE_SECONDS)

        job.status = "done" if job.failed == 0 else "done_with_failures"
        s.commit()
        print(f"Finished: {job.done} ok, {job.failed} failed, {job.retries} retries")
        return job.id