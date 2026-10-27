"""Rank all images for one post, then let the guard pick the first one that passes."""
from sqlalchemy import select

from app.db import Image
from app.embeddings import cosine
from app.guard import choose


def rank_images(session, post_vector):
    """Return all processed images with a vector, best similarity first."""
    images = session.scalars(select(Image).where(Image.caption_vector.is_not(None)))
    rows = []
    for img in images:
        rows.append({
            "image": img.filename,
            "image_group": img.group_name,
            "confidence": img.confidence,
            "flagged": img.flagged,
            "similarity": cosine(post_vector, img.caption_vector),
        })
    rows.sort(key=lambda r: r["similarity"], reverse=True)
    return rows


def suggest(session, post, similarity_min):
    """Return (best_candidate_or_None, rejections, ranked_list)."""
    ranked = rank_images(session, post.post_vector)
    best, rejections = choose(ranked, post.expected_group,
                              similarity_min=similarity_min)
    return best, rejections, ranked