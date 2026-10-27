"""Search stored captions for a word, e.g. python scripts/find_captions.py husky"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select
from app.db import Image, SessionLocal

word = sys.argv[1].lower()
with SessionLocal() as s:
    for i in s.scalars(select(Image).order_by(Image.filename)):
        text = f"{i.subject} {i.caption} {i.attributes}".lower()
        if word in text:
            print(f"{i.filename:<17}{i.confidence:.2f}  {i.caption[:90]}")