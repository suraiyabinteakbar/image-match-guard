"""Check that the Gemini key and model name work."""
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
model = os.getenv("GEMINI_MODEL")

response = client.models.generate_content(
    model=model,
    contents="Say hello in five words.",
)
print(response.text)