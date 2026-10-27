"""Show where the correct photo ranks for each post, and what vague captions say."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select
from app.db import Image, Post, SessionLocal
from app.ranking import rank_images

with open("data/eval_set.csv", newline="", encoding="utf-8") as f:
    exam = list(csv.DictReader(f))

with SessionLocal() as s:
    img = s.scalars(select(Image).where(Image.filename == "ambiguous_09.jpg")).first()
    print("ambiguous_09 caption:", img.caption, "\n")

    for r in exam:
        if not r["correct_image"]:
            continue
        post = s.get(Post, int(r["id"]))
        ranked = [c for c in rank_images(s, post.post_vector) if not c["flagged"]]
        names = [c["image"] for c in ranked]
        pos = names.index(r["correct_image"]) + 1
        score = ranked[pos - 1]["similarity"]
        print(f"#{r['id']:<3}{r['title'][:28]:<30}correct score={score:.2f}  "
              f"place={pos}/{len(ranked)}  best={ranked[0]['image']} {ranked[0]['similarity']:.2f}")