"""Download a small, licensed-free image corpus from Pixabay.

Safe to re-run: files already downloaded are never touched, and their
records in data/image_sources.csv are kept exactly as they are.
"""
import csv
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("PIXABAY_API_KEY")
if not API_KEY:
    raise SystemExit("Missing PIXABAY_API_KEY. Add it to your .env file.")

SEARCH_URL = "https://pixabay.com/api/"
OUT_DIR = Path("data/images")
SOURCES_CSV = Path("data/image_sources.csv")
FIELDS = ["filename", "search_query", "pixabay_id", "photographer", "page_url", "tags"]
OUT_DIR.mkdir(parents=True, exist_ok=True)

# file prefix -> (search query, how many images)
PLAN = {
    "fox": ("red fox", 10),
    "wolf": ("gray wolf", 10),
    "dog": ("dog", 10),
    "bear": ("brown bear", 10),
    "deer": ("deer", 10),
    "ambiguous": ("animal dark night forest", 5),
}

# Load records from earlier runs so they are never overwritten
existing = {}
if SOURCES_CSV.exists():
    with open(SOURCES_CSV, newline="", encoding="utf-8") as f:
        existing = {r["filename"]: r for r in csv.DictReader(f)}

rows = []
for prefix, (query, count) in PLAN.items():
    print(f"Searching: {query}")
    resp = requests.get(
        SEARCH_URL,
        params={
            "key": API_KEY,
            "q": query,
            "image_type": "photo",
            "per_page": 30,
            "safesearch": "true",
        },
        timeout=30,
    )
    resp.raise_for_status()
    hits = resp.json().get("hits", [])

    for i, hit in enumerate(hits[:count], start=1):
        filename = f"{prefix}_{i:02d}.jpg"
        path = OUT_DIR / filename

        # Already recorded: keep the old record as it is
        if filename in existing:
            rows.append(existing[filename])
            continue

        # File exists but has no record (e.g. you added it by hand)
        if path.exists():
            rows.append({"filename": filename, "search_query": "manual",
                         "pixabay_id": "", "photographer": "", "page_url": "", "tags": ""})
            continue

        # New image: download and record it
        img = requests.get(hit["webformatURL"], timeout=60)
        img.raise_for_status()
        path.write_bytes(img.content)
        print(f"  saved {filename}")
        time.sleep(0.5)  # be polite to the server

        rows.append({
            "filename": filename,
            "search_query": query,
            "pixabay_id": hit["id"],
            "photographer": hit["user"],
            "page_url": hit["pageURL"],
            "tags": hit.get("tags", ""),
        })

with open(SOURCES_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)

print(f"\nDone. {len(rows)} images in {OUT_DIR}. Sources listed in {SOURCES_CSV}.")