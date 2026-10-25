"""Embed three texts and print how similar they are."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.embeddings import cosine, embed_texts, make_client

load_dotenv()
texts = [
    "A red fox standing in a forest",
    "Vulpes vulpes in the wild",
    "A bowl of pasta on a table",
]
vecs, _ = embed_texts(make_client(), os.getenv("EMBEDDING_MODEL"),
                      texts, int(os.getenv("EMBEDDING_DIMS", "768")))
print("vector length:", len(vecs[0]))
print("fox vs Vulpes vulpes:", round(cosine(vecs[0], vecs[1]), 3))
print("fox vs pasta:        ", round(cosine(vecs[0], vecs[2]), 3))