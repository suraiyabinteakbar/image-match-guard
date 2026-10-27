"""Mismatch guard: decides whether an image is good enough for a post.

Rules and order come from docs/design.md, section 5. All must pass.
"""
from dataclasses import dataclass

CONFIDENCE_MIN = 0.60
SIMILARITY_MIN = 0.20  # chosen from data: highest value that loses no post (see README)


@dataclass
class Decision:
    accepted: bool
    reason: str


def check(image_group, image_confidence, image_flagged,
          post_group, similarity,
          confidence_min=CONFIDENCE_MIN, similarity_min=SIMILARITY_MIN):
    # 1. image must be confidently identified
    if image_flagged or image_confidence < confidence_min:
        return Decision(False, "low confidence image")

    # 2. we must know what the post is about
    if post_group == "other":
        return Decision(False, "cannot verify what the post is about")

    # 3. the image must be the same kind of thing as the post
    if image_group == "other":
        return Decision(False, "cannot verify image subject")
    if image_group != post_group:
        return Decision(
            False, f"group mismatch: expected {post_group}, detected {image_group}")

    # 4. the texts must also be close in meaning
    if similarity < similarity_min:
        return Decision(False, f"similarity {similarity:.2f} below threshold {similarity_min:.2f}")

    return Decision(True, "accepted")


def choose(candidates, post_group, **kwargs):
    """candidates: list of dicts with image_group, confidence, flagged,
    similarity, already sorted best similarity first.
    Returns (best_accepted_or_None, list_of_rejections)."""
    rejections = []
    for c in candidates:
        d = check(c["image_group"], c["confidence"], c["flagged"],
                  post_group, c["similarity"], **kwargs)
        if d.accepted:
            return c, rejections
        rejections.append((c, d.reason))
    return None, rejections