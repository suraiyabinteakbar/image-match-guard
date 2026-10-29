"""Build a database from data/seed.json. No Gemini calls.

Usage: python scripts/import_seed.py
Use DATABASE_URL=sqlite:///data/test.db to try it on a fresh file.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select
from app.db import Image, Post, SessionLocal, init_db

init_db()
seed = json.loads(Path("data/seed.json").read_text(encoding="utf-8"))

with SessionLocal() as s:
    known_images = set(s.scalars(select(Image.filename)))
    added_images = 0
    for row in seed["images"]:
        if row["filename"] in known_images:
            continue
        s.add(Image(**row))
        added_images += 1

    added_posts = 0
    for row in seed["posts"]:
        if s.get(Post, row["id"]) is None:
            s.add(Post(**row))
            added_posts += 1
    s.commit()

print(f"Added {added_images} images, {added_posts} posts "
      f"(skipped ones already there).")