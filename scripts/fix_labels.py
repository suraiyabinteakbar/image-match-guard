import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select
from app.batch import load_truth
from app.db import Image, SessionLocal

truth = load_truth()
with SessionLocal() as s:
    for img in s.scalars(select(Image)):
        if img.filename in truth and img.true_subject != truth[img.filename]:
            print(f"{img.filename}: {img.true_subject} -> {truth[img.filename]}")
            img.true_subject = truth[img.filename]
    s.commit()