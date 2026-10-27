"""Take the exam at several cutoffs and count the results."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db import Post, SessionLocal
from app.ranking import suggest

with open("data/eval_set.csv", newline="", encoding="utf-8") as f:
    exam = list(csv.DictReader(f))

CUTOFFS = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50]
with_photo = [r for r in exam if r["correct_image"]]
no_photo = [r for r in exam if not r["correct_image"]]

with SessionLocal() as s:
    posts = {p.id: p for p in s.query(Post).all()}

    print(f"{'cutoff':<8}{'exact photo':<14}{'right animal':<14}"
          f"{'wrong animal':<14}{'no match':<10}{'refused ok'}")
    for cut in CUTOFFS:
        exact = animal = wrong = nomatch = 0
        for r in with_photo:
            best, _, _ = suggest(s, posts[int(r["id"])], cut)
            if best is None:
                nomatch += 1
                continue
            exact += best["image"] == r["correct_image"]
            if best["image_group"] == r["true_group"]:
                animal += 1
            else:
                wrong += 1
        refused = 0
        for r in no_photo:
            best, _, _ = suggest(s, posts[int(r["id"])], cut)
            refused += best is None
        print(f"{cut:<8}{exact}/{len(with_photo):<12}{animal}/{len(with_photo):<12}"
              f"{wrong:<14}{nomatch:<10}{refused}/{len(no_photo)}")

    # detail at one cutoff
    cut = 0.20
    print(f"\nDetail at cutoff {cut}")
    for r in exam:
        best, _, ranked = suggest(s, posts[int(r["id"])], cut)
        answer = best["image"] if best else "NO MATCH"
        print(f"#{r['id']:<3}{r['title'][:28]:<30}answer={answer:<17}"
              f"key={r['correct_image'] or '(refuse)':<17}")