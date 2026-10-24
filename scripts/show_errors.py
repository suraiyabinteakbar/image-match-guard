import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import select
from app.db import Job, SessionLocal

with SessionLocal() as s:
    job = s.scalars(select(Job).order_by(Job.id.desc())).first()
    print(f"job {job.id}: status={job.status} done={job.done} failed={job.failed} retries={job.retries}")
    print("last error:", job.error)