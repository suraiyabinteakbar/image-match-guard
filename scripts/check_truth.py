"""List images where the model's group differs from the true group."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select
from app.db import Image, SessionLocal
from app.taxonomy import extract_group

# the dictionary only knows animals, so people need a manual true group
OVERRIDE = {"ambiguous_05.jpg": "person"}

with SessionLocal() as s:
    rows = s.scalars(select(Image).where(Image.processed_at.is_not(None))
                     .order_by(Image.filename)).all()

wrong, flagged = [], []
for r in rows:
    true = OVERRIDE.get(r.filename) or extract_group(r.true_subject or "")[0]
    if r.flagged:
        flagged.append((r.filename, true, r.group_name, r.confidence))
    elif r.group_name != true:
        wrong.append((r.filename, true, r.group_name, r.confidence))

print(f"{len(rows)} images checked\n")
print("Confident but wrong (the dangerous kind):")
for f in wrong:
    print(f"  {f[0]:<18} true={f[1]:<8} model={f[2]:<8} conf={f[3]:.2f}")
if not wrong:
    print("  none")
print("\nFlagged (low confidence, will never be suggested):")
for f in flagged:
    print(f"  {f[0]:<18} true={f[1]:<8} model={f[2]:<8} conf={f[3]:.2f}")