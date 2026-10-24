"""Send one image to Gemini and validate the answer."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.schemas import ImageMetadata

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
model = os.getenv("GEMINI_MODEL")

PROMPT = (
    "Describe the main subject of this image. "
    "group must be one of: fox, wolf, dog, bear, deer, cat, owl, person, other. "
    "Use 'other' if the subject is not on that list. "
    "confidence is your honest certainty from 0 to 1; "
    "give a low number if the image is blurry, dark, or the subject is unclear."
)

path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/images/fox_01.jpg")
image_bytes = path.read_bytes()

response = client.models.generate_content(
    model=model,
    contents=[types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"), PROMPT],
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ImageMetadata,
        temperature=0,
    ),
)

print("RAW:", response.text)
meta = ImageMetadata.model_validate_json(response.text)
print("VALID:", meta)