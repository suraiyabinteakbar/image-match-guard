"""Load the eval posts into the database, find their animal, embed them."""
import csv
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db import CostLog, Post, SessionLocal, init_db
from app.embeddings import embed_texts, make_client
from app.taxonomy import extract_group

load_dotenv()
init_db()
model = os.getenv("EMBEDDING_MODEL")
dims = int(os.getenv("EMBEDDING_DIMS", "768"))

with open("data/eval_set.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

client = make_client()
right = 0

with SessionLocal() as s:
    for r in rows:
        pid = int(r["id"])
        group, note = extract_group(r["title"], r["body"])
        correct = group == r["true_group"]
        right += correct
        print(f"#{pid:<3}{r['title'][:34]:<36}true={r['true_group']:<7}"
              f"dictionary={group:<7}{'OK' if correct else 'WRONG'}")

        post = s.get(Post, pid)
        if post is None:
            post = Post(id=pid, title=r["title"], body=r["body"],
                        group_dict=group, expected_group=group, group_note=note)
            s.add(post)
            s.commit()

        if post.post_vector is None:
            try:
                vecs, _ = embed_texts(client, model,
                                      [r["title"] + ". " + r["body"]], dims)
                post.post_vector = vecs[0]
                status = "ok"
            except Exception as e:
                status = "error"
                print(f"   embedding failed: {str(e)[:120]}")
            s.add(CostLog(kind="embedding", model=model, post_id=pid,
                          cost_usd=0.0, status=status))
            s.commit()

print(f"\nDictionary found the right animal for {right} of {len(rows)} posts.")