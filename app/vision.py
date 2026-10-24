"""One call to Gemini for one image. Validation happens in the caller."""
import os
from pathlib import Path

from google import genai
from google.genai import types

from app.schemas import ImageMetadata

PROMPT = (
    "Describe the main subject of this image. "
    "group must be one of: fox, wolf, dog, bear, deer, cat, owl, person, other. "
    "Use 'other' if the subject is not on that list. "
    "confidence is your honest certainty from 0 to 1; "
    "give a low number if the image is blurry, dark, or the subject is unclear."
)


def make_client():
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def analyze_image(client, model, path: Path):
    """Return (raw_text, input_tokens, output_tokens)."""
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=path.read_bytes(), mime_type="image/jpeg"),
            PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ImageMetadata,
            temperature=0,
        ),
    )
    usage = response.usage_metadata
    tokens_in = getattr(usage, "prompt_token_count", None)
    tokens_out = getattr(usage, "candidates_token_count", None)
    return response.text or "", tokens_in, tokens_out