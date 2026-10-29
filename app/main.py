"""Review API: see why an image was accepted or refused, then approve or reject it."""
from collections import Counter
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import Image, Post, SessionLocal, Suggestion, init_db, now
from app.guard import SIMILARITY_MIN, check
from app.ranking import rank_images

SHOW_TOP = 5

init_db()
app = FastAPI(title="image-match-guard review API")


def get_db():
    with SessionLocal() as session:
        yield session


class Review(BaseModel):
    decision: Literal["approve", "reject"]
    note: Optional[str] = Field(default=None, max_length=500)


@app.get("/posts/{post_id}/images")
def images_for_post(post_id: int,
                    cutoff: float = Query(SIMILARITY_MIN, ge=0.0, le=1.0),
                    db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(404, "post not found")
    if post.post_vector is None or post.expected_group is None:
        raise HTTPException(409, "post is not ready: no embedding or no animal group yet")

    # go down the ranking, run the guard on each photo, stop at the first accepted one
    evaluated = []
    for c in rank_images(db, post.post_vector):
        d = check(c["image_group"], c["confidence"], c["flagged"],
                  post.expected_group, c["similarity"], similarity_min=cutoff)
        evaluated.append((c, d))
        if d.accepted:
            break

    shown = evaluated[:SHOW_TOP]
    if evaluated[-1][1].accepted and not any(d.accepted for _, d in shown):
        shown.append(evaluated[-1])

    candidates = []
    for c, d in shown:
        sug = db.scalars(select(Suggestion).where(
            Suggestion.post_id == post_id,
            Suggestion.image_id == c["image_id"])).first()
        decision = "accepted" if d.accepted else "rejected"
        if sug is None:
            sug = Suggestion(post_id=post_id, image_id=c["image_id"])
            db.add(sug)
        sug.similarity = c["similarity"]
        sug.decision = decision
        sug.reason = d.reason
        if decision == "rejected" and sug.review_status == "approved":
            sug.review_status = "pending"  # an old approval must not survive a refusal
        db.flush()
        candidates.append({
            "suggestion_id": sug.id,
            "image": c["image"],
            "group": c["image_group"],
            "confidence": c["confidence"],
            "similarity": round(c["similarity"], 3),
            "decision": decision,
            "reason": d.reason,
            "review_status": sug.review_status,
        })
    db.commit()

    best = next((x for x in candidates if x["decision"] == "accepted"), None)
    return {
        "post_id": post.id,
        "title": post.title,
        "expected_group": post.expected_group,
        "cutoff": cutoff,
        "result": "match" if best else "no confident match",
        "best": best,
        "candidates": candidates,
        "reason_counts": dict(Counter(d.reason for _, d in evaluated)),
    }


@app.get("/suggestions/{suggestion_id}")
def get_suggestion(suggestion_id: int, db: Session = Depends(get_db)):
    sug = db.get(Suggestion, suggestion_id)
    if sug is None:
        raise HTTPException(404, "suggestion not found")
    img = db.get(Image, sug.image_id)
    post = db.get(Post, sug.post_id)
    return {
        "suggestion_id": sug.id,
        "post_title": post.title,
        "post_group": post.expected_group,
        "image": img.filename,
        "image_group": img.group_name,
        "caption": img.caption,
        "confidence": img.confidence,
        "flagged": img.flagged,
        "similarity": round(sug.similarity, 3),
        "decision": sug.decision,
        "reason": sug.reason,
        "review_status": sug.review_status,
        "review_note": sug.review_note,
        "reviewed_at": sug.reviewed_at,
    }


@app.post("/suggestions/{suggestion_id}/review")
def review_suggestion(suggestion_id: int, body: Review, db: Session = Depends(get_db)):
    sug = db.get(Suggestion, suggestion_id)
    if sug is None:
        raise HTTPException(404, "suggestion not found")
    if body.decision == "approve" and sug.decision != "accepted":
        raise HTTPException(
            409, f"the guard refused this image ({sug.reason}), so it cannot be approved")
    sug.review_status = "approved" if body.decision == "approve" else "rejected"
    sug.review_note = body.note
    sug.reviewed_at = now()
    db.commit()
    return {"suggestion_id": sug.id, "review_status": sug.review_status,
            "review_note": sug.review_note}