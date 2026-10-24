"""Shapes that model output must fit before we trust it."""
from typing import Literal

from pydantic import BaseModel, Field

Group = Literal["fox", "wolf", "dog", "bear", "deer", "cat", "owl", "person", "other"]


class ImageMetadata(BaseModel):
    subject: str = Field(min_length=1)
    group: Group
    category: str = Field(min_length=1)
    attributes: list[str]
    caption: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)