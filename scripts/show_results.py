"""Print what the vision model said about every image, lowest confidence first."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select
from app.db import Image, SessionLocal

with SessionLocal() as s:
    rows = s.scalars(select(Image).where(Image.processed_at.is_not(None))
                     .order_by(Image.confidence)).all()
    print(f"{'file':<18}{'true':<26}{'group':<8}{'conf':<6}flag")
    for r in rows:
        print(f"{r.filename:<18}{(r.true_subject or '')[:24]:<26}"
              f"{r.group_name:<8}{r.confidence:<6.2f}{'FLAG' if r.flagged else ''}")
    print(f"\n{len(rows)} images processed")