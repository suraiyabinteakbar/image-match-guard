"""Save the results (captions, groups, vectors) into data/seed.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select
from app.db import Image, Post, SessionLocal

with SessionLocal() as s:
    images = [{
        "filename": i.filename, "true_subject": i.true_subject,
        "subject": i.subject, "group_name": i.group_name,
        "category": i.category, "attributes": i.attributes,
        "caption": i.caption, "confidence": i.confidence,
        "flagged": i.flagged, "caption_vector": i.caption_vector,
    } for i in s.scalars(select(Image).order_by(Image.filename))]

    posts = [{
        "id": p.id, "title": p.title, "body": p.body,
        "group_dict": p.group_dict, "group_llm": p.group_llm,
        "expected_group": p.expected_group, "group_note": p.group_note,
        "post_vector": p.post_vector,
    } for p in s.scalars(select(Post).order_by(Post.id))]

Path("data/seed.json").write_text(
    json.dumps({"images": images, "posts": posts}), encoding="utf-8")
print(f"Saved {len(images)} images, {len(posts)} posts to data/seed.json")