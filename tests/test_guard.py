from app.guard import check, choose


def test_wolf_on_fox_post_is_rejected():
    # the wolf caption is semantically very close (0.91), but the group is wrong
    d = check("wolf", 0.99, False, "fox", 0.91)
    assert not d.accepted
    assert d.reason == "group mismatch: expected fox, detected wolf"


def test_matching_fox_is_accepted():
    assert check("fox", 0.99, False, "fox", 0.85).accepted


def test_low_confidence_is_rejected():
    d = check("fox", 0.30, True, "fox", 0.95)
    assert d.reason == "low confidence image"


def test_unknown_post_group_is_rejected():
    d = check("fox", 0.99, False, "other", 0.95)
    assert d.reason == "cannot verify what the post is about"


def test_other_image_group_is_rejected():
    d = check("other", 0.99, False, "fox", 0.95)
    assert d.reason == "cannot verify image subject"


def test_low_similarity_is_rejected():
    d = check("fox", 0.99, False, "fox", 0.10)
    assert "below threshold" in d.reason


def test_choose_skips_wolf_and_picks_fox():
    candidates = [
        {"image": "wolf_01", "image_group": "wolf", "confidence": 0.99, "flagged": False, "similarity": 0.91},
        {"image": "fox_01", "image_group": "fox", "confidence": 0.99, "flagged": False, "similarity": 0.85},
    ]
    best, rejections = choose(candidates, "fox")
    assert best["image"] == "fox_01"
    assert len(rejections) == 1


def test_choose_returns_none_when_nothing_fits():
    candidates = [{"image": "wolf_01", "image_group": "wolf", "confidence": 0.99,
                   "flagged": False, "similarity": 0.91}]
    best, rejections = choose(candidates, "fox")
    assert best is None
    assert rejections[0][1].startswith("group mismatch")