"""Turn text into vectors with Gemini, and compare vectors."""
import math
import os

from google import genai
from google.genai import types


def make_client():
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def embed_texts(client, model, texts, dims=768):
    """Embed each text in its own call. Returns (vectors, None)."""
    vectors = []
    for text in texts:
        response = client.models.embed_content(
            model=model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="SEMANTIC_SIMILARITY",
                output_dimensionality=dims,
            ),
        )
        if len(response.embeddings) != 1:
            raise ValueError(f"expected 1 embedding, got {len(response.embeddings)}")
        vectors.append(response.embeddings[0].values)
    if len(vectors) != len(texts):
        raise ValueError("number of vectors does not match number of texts")
    return vectors, None


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
def embed_all_captions(session, client, model, dims=768):
    """Embed every image caption that has no vector yet. Logs each call."""
    from sqlalchemy import select
    from app.db import CostLog, Image

    todo = list(session.scalars(
        select(Image).where(Image.caption.is_not(None),
                            Image.caption_vector.is_(None))))
    done = 0
    for img in todo:
        try:
            vectors, _ = embed_texts(client, model, [img.caption], dims)
        except Exception as e:
            session.add(CostLog(kind="embedding", model=model, image_id=img.id,
                                cost_usd=0.0, status="error"))
            session.commit()
            print(f"FAILED {img.filename}: {str(e)[:150]}")
            continue
        img.caption_vector = vectors[0]
        session.add(CostLog(kind="embedding", model=model, image_id=img.id,
                            cost_usd=0.0, status="ok"))
        session.commit()
        done += 1
        print(f"[{done}/{len(todo)}] {img.filename}")
    return done