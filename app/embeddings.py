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