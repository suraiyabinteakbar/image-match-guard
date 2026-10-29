from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, Image, Post
from app.main import app, get_db


def make_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as s:
        s.add_all([
            Image(filename="fox_01.jpg", group_name="fox", confidence=0.99,
                  flagged=False, caption_vector=[0.8, 0.6]),
            Image(filename="wolf_01.jpg", group_name="wolf", confidence=0.99,
                  flagged=False, caption_vector=[1.0, 0.0]),
            Post(id=1, title="Foxes", body="b", expected_group="fox", post_vector=[1.0, 0.0]),
            Post(id=2, title="Platypus", body="b", expected_group="other", post_vector=[1.0, 0.0]),
            Post(id=3, title="No vector", body="b", expected_group="fox"),
        ])
        s.commit()

    def override():
        with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def test_wolf_is_refused_and_fox_is_suggested():
    r = make_client().get("/posts/1/images").json()
    assert r["result"] == "match"
    assert r["best"]["image"] == "fox_01.jpg"
    first = r["candidates"][0]
    assert first["image"] == "wolf_01.jpg"
    assert first["decision"] == "rejected"
    assert first["reason"].startswith("group mismatch")


def test_unknown_post_is_404():
    assert make_client().get("/posts/99/images").status_code == 404


def test_post_with_unknown_animal_gets_no_match():
    r = make_client().get("/posts/2/images").json()
    assert r["result"] == "no confident match"
    assert r["best"] is None


def test_post_without_embedding_is_409():
    assert make_client().get("/posts/3/images").status_code == 409


def test_bad_cutoff_is_422():
    assert make_client().get("/posts/1/images?cutoff=5").status_code == 422


def test_refused_image_cannot_be_approved():
    client = make_client()
    wolf = client.get("/posts/1/images").json()["candidates"][0]
    r = client.post(f"/suggestions/{wolf['suggestion_id']}/review",
                    json={"decision": "approve"})
    assert r.status_code == 409


def test_accepted_image_can_be_approved():
    client = make_client()
    best = client.get("/posts/1/images").json()["best"]
    r = client.post(f"/suggestions/{best['suggestion_id']}/review",
                    json={"decision": "approve", "note": "looks right"})
    assert r.status_code == 200
    assert r.json()["review_status"] == "approved"


def test_bad_review_decision_is_422():
    client = make_client()
    best = client.get("/posts/1/images").json()["best"]
    r = client.post(f"/suggestions/{best['suggestion_id']}/review",
                    json={"decision": "maybe"})
    assert r.status_code == 422