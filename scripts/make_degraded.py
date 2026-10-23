"""Create degraded copies of clear images to test low-confidence flagging.

Safe to re-run: existing outputs are skipped, and labels are added only once.
"""
import csv
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

IMG_DIR = Path("data/images")
TRUTH_CSV = Path("data/ground_truth.csv")
LOG_CSV = Path("data/degraded_sources.csv")

# output, source, true subject, shrink factor, blur, brightness, crop box (fractions) or None
JOBS = [
    ("ambiguous_07.jpg", "fox_02.jpg",  "red fox",   8, 2, 0.50, None),
    ("ambiguous_08.jpg", "wolf_02.jpg", "gray wolf", 8, 2, 0.50, None),  # fox/wolf lookalike at low res
    ("ambiguous_09.jpg", "bear_04.jpg", "brown bear", 3, 3, 0.80, (0.0, 0.0, 0.35, 0.35)),  # tiny corner crop
    ("ambiguous_10.jpg", "dog_05.jpg",  "dog",       2, 1, 0.20, None),  # very dark
    ("ambiguous_11.jpg", "deer_06.jpg", "deer",      4, 7, 0.90, None),  # heavy blur
    ("ambiguous_12.jpg", "wolf_05.jpg", "gray wolf", 3, 2, 0.70, (0.55, 0.0, 1.0, 0.45)),  # partial view
]

def degrade(src, shrink, blur, brightness, crop):
    img = Image.open(src).convert("RGB")
    if crop:
        w, h = img.size
        img = img.crop((int(crop[0]*w), int(crop[1]*h), int(crop[2]*w), int(crop[3]*h)))
    img = img.resize((max(img.width // shrink, 16), max(img.height // shrink, 16)))
    img = img.filter(ImageFilter.GaussianBlur(blur))
    return ImageEnhance.Brightness(img).enhance(brightness)

def read_col(path, col):
    if not path.exists():
        return set()
    with open(path, newline="", encoding="utf-8") as f:
        return {r[col] for r in csv.DictReader(f)}

known_truth = read_col(TRUTH_CSV, "filename")
known_log = read_col(LOG_CSV, "filename")

new_truth, new_log = [], []
for out_name, src_name, subject, shrink, blur, bright, crop in JOBS:
    out, src = IMG_DIR / out_name, IMG_DIR / src_name
    if not src.exists():
        print(f"skip {out_name}: source {src_name} not found (pick another image)")
        continue
    if not out.exists():
        degrade(src, shrink, blur, bright, crop).save(out, quality=40)
        print(f"saved {out_name} (from {src_name})")
    if out_name not in known_truth:
        new_truth.append({"filename": out_name, "true_subject": subject})
    if out_name not in known_log:
        new_log.append({"filename": out_name, "degraded_from": src_name,
                        "shrink": shrink, "blur": blur, "brightness": bright,
                        "crop": crop or ""})

def append(path, fields, rows):
    if not rows:
        return
    is_new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if is_new:
            w.writeheader()
        w.writerows(rows)

append(TRUTH_CSV, ["filename", "true_subject"], new_truth)
append(LOG_CSV, ["filename", "degraded_from", "shrink", "blur", "brightness", "crop"], new_log)
print("done.")