import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base, Image, Post, Suggestion


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_duplicate_suggestion_is_rejected():
    s = make_session()
    img, post = Image(filename="fox_01.jpg"), Post(title="t", body="b")
    s.add_all([img, post])
    s.commit()

    s.add(Suggestion(post_id=post.id, image_id=img.id, similarity=0.8, decision="accepted"))
    s.commit()

    s.add(Suggestion(post_id=post.id, image_id=img.id, similarity=0.8, decision="accepted"))
    with pytest.raises(IntegrityError):
        s.commit()