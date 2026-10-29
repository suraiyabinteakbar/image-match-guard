"""Print a short summary for one post. Usage: python scripts/show_post.py 3"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi.testclient import TestClient
from app.main import app

post_id = sys.argv[1]
r = TestClient(app).get(f"/posts/{post_id}/images")
if r.status_code != 200:
    print(r.status_code, r.json()["detail"])
    sys.exit()

d = r.json()
print(f"Post {d['post_id']}: {d['title']}")
print(f"Animal in the post: {d['expected_group']}    cutoff: {d['cutoff']}")
print(f"RESULT: {d['result'].upper()}")
if d["best"]:
    b = d["best"]
    print(f"Best photo: {b['image']} ({b['group']}), score {b['similarity']}, "
          f"sure {b['confidence']}")
print("\nDecisions for the photos checked:")
for reason, n in d["reason_counts"].items():
    print(f"  {n:>3} x {reason}")