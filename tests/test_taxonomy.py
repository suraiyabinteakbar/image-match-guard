from app.taxonomy import extract_group


def test_fox_latin_name():
    assert extract_group("The behavior of Vulpes vulpes")[0] == "fox"


def test_plural_form():
    assert extract_group("Why wolves howl")[0] == "wolf"


def test_unknown_animal_is_other():
    assert extract_group("Life of the platypus")[0] == "other"


def test_tie_is_other():
    # two animals named equally often in the body, none in the title
    assert extract_group("Forest animals", "a fox and a wolf")[0] == "other"


def test_title_beats_body():
    # title counts 3x: fox = 3, wolf = 1
    assert extract_group("Fox", "wolf")[0] == "fox"