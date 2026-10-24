import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import func, select
from app.db import CostLog, SessionLocal

with SessionLocal() as s:
    rows = s.execute(select(CostLog.status, func.count(), func.sum(CostLog.input_tokens),
                            func.sum(CostLog.output_tokens), func.sum(CostLog.cost_usd))
                     .group_by(CostLog.status)).all()
    for status, n, tin, tout, cost in rows:
        print(f"{status:<8} calls={n:<4} in_tokens={tin} out_tokens={tout} cost=${cost:.4f}")