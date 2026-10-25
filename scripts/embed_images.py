"""Embed all image captions and store the vectors in the database."""
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db import SessionLocal, init_db
from app.embeddings import embed_all_captions, make_client

load_dotenv()
init_db()
with SessionLocal() as s:
    n = embed_all_captions(s, make_client(), os.getenv("EMBEDDING_MODEL"),
                           int(os.getenv("EMBEDDING_DIMS", "768")))
print(f"Embedded {n} captions.")