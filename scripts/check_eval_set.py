"""Check that every eval post points to an image that really fits it."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select
from app.db import Image, SessionLocal

with open("data/eval_set.csv", newline="", encoding="utf-8") as f:
    posts = list(csv.DictReader(f))

with SessionLocal() as s:
    images = {i.filename: i for i in s.scalars(select(Image))}

problems = 0
for p in posts:
    fn = p["correct_image"]
    head = f"#{p['id']:<3}{p['title'][:34]:<36}true={p['true_group']:<7}"
    if not fn:
        # no image expected: the system should refuse this post
        print(f"{head}no image expected (should be refused)")
        continue
    img = images.get(fn)
    if img is None or img.group_name is None:
        print(f"{head}PROBLEM: {fn} not found or not processed")
        problems += 1
        continue
    issues = []
    if img.group_name != p["true_group"]:
        issues.append(f"image group is {img.group_name}")
    if img.flagged:
        issues.append("image is flagged")
    status = "OK" if not issues else "PROBLEM: " + ", ".join(issues)
    if issues:
        problems += 1
    print(f"{head}{fn:<17}{img.group_name:<7}{img.confidence:.2f}  {status}")
    print(f"      caption: {(img.caption or '')[:90]}")

print(f"\n{len(posts)} posts checked, {problems} problems")