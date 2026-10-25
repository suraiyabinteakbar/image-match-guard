from app.embeddings import cosine


def test_same_vector_is_one():
    assert abs(cosine([1, 2, 3], [1, 2, 3]) - 1.0) < 1e-9


def test_opposite_direction_is_minus_one():
    assert abs(cosine([1, 0], [-1, 0]) + 1.0) < 1e-9


def test_perpendicular_is_zero():
    assert abs(cosine([1, 0], [0, 1])) < 1e-9


def test_length_does_not_matter():
    assert abs(cosine([1, 1], [5, 5]) - 1.0) < 1e-9


def test_zero_vector_is_safe():
    assert cosine([0, 0], [1, 1]) == 0.0