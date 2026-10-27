from app.post_group import combine


def test_agreement_is_kept():
    assert combine("fox", "fox") == "fox"


def test_disagreement_becomes_other():
    assert combine("fox", "wolf") == "other"


def test_dictionary_misses_so_other():
    assert combine("other", "fox") == "other"


def test_both_other_stays_other():
    assert combine("other", "other") == "other"