"""Compare the dictionary and Gemini at finding a post's animal."""
import csv
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db import CostLog, Post, SessionLocal, init_db
from app.embeddings import make_client
from app.post_group import combine, gemini_group
from app.taxonomy import extract_group

load_dotenv()
init_db()
model = os.getenv("GEMINI_MODEL")

rows = []
for path in ("data/eval_set.csv", "data/hard_posts.csv"):
    with open(path, newline="", encoding="utf-8") as f:
        rows += list(csv.DictReader(f))

client = make_client()
right = {"dictionary": 0, "gemini": 0, "both agree": 0}
wrong_but_accepted = 0
counted = 0

with SessionLocal() as s:
    for r in rows:
        pid, truth = int(r["id"]), r["true_group"]
        gd, note = extract_group(r["title"], r["body"])

        post = s.get(Post, pid)
        if post is None:
            post = Post(id=pid, title=r["title"], body=r["body"])
            s.add(post)
        post.group_dict = gd
        s.commit()

        if post.group_llm is None:
            tin = tout = None
            try:
                gl, tin, tout = gemini_group(client, model, r["title"], r["body"])
                status = "ok"
                post.group_llm = gl
            except Exception as e:
                status = "error"
                print(f"#{pid} Gemini failed: {str(e)[:120]}")
            s.add(CostLog(kind="text", model=model, post_id=pid,
                          input_tokens=tin, output_tokens=tout,
                          cost_usd=0.0, status=status))
            s.commit()
            time.sleep(5)

        gl = post.group_llm
        if gl is None:
            continue
        final = combine(gd, gl)
        post.expected_group = final
        post.group_note = f"dictionary={gd}, gemini={gl}"
        s.commit()

        counted += 1
        right["dictionary"] += gd == truth
        right["gemini"] += gl == truth
        right["both agree"] += final == truth
        if final != "other" and final != truth:
            wrong_but_accepted += 1
        print(f"#{pid:<3}{r['title'][:30]:<32}true={truth:<7}dict={gd:<7}"
              f"gemini={gl:<7}final={final:<7}"
              f"{'' if final == truth else 'MISS'}")

print(f"\nPosts counted: {counted}")
for name, n in right.items():
    print(f"  {name:<12}{n}/{counted} correct")
print(f"Wrong animal passed on to the guard: {wrong_but_accepted}")