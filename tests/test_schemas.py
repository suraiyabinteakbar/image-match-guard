import pytest
from pydantic import ValidationError

from app.schemas import ImageMetadata

GOOD = {
    "subject": "red fox",
    "group": "fox",
    "category": "animal",
    "attributes": ["orange fur", "forest"],
    "caption": "A red fox standing in a forest",
    "confidence": 0.94,
}


def test_valid_data_passes():
    assert ImageMetadata(**GOOD).group == "fox"


def test_confidence_above_one_fails():
    with pytest.raises(ValidationError):
        ImageMetadata(**{**GOOD, "confidence": 1.7})


def test_unknown_group_fails():
    with pytest.raises(ValidationError):
        ImageMetadata(**{**GOOD, "group": "canine"})


def test_missing_field_fails():
    bad = {k: v for k, v in GOOD.items() if k != "caption"}
    with pytest.raises(ValidationError):
        ImageMetadata(**bad)