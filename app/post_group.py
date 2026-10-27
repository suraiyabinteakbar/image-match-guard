"""Ask Gemini which animal a post is about, and combine it with the dictionary."""
from google.genai import types
from pydantic import BaseModel

from app.schemas import Group


class PostGroup(BaseModel):
    group: Group


PROMPT = (
    "Read this article. Which ONE animal is it mainly about? "
    "group must be one of: fox, wolf, dog, bear, deer, cat, owl, person, other. "
    "Use 'other' if the article names no animal, is about more than one animal "
    "equally, or is about an animal that is not on the list. Do not guess.\n\n"
    "Title: {title}\nText: {body}"
)


def gemini_group(client, model, title, body):
    """Return (group, input_tokens, output_tokens). Raises if the answer is invalid."""
    response = client.models.generate_content(
        model=model,
        contents=PROMPT.format(title=title, body=body),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PostGroup,
            temperature=0,
        ),
    )
    usage = response.usage_metadata
    tin = getattr(usage, "prompt_token_count", None)
    tout = getattr(usage, "candidates_token_count", None)
    result = PostGroup.model_validate_json(response.text or "")
    return result.group, tin, tout


def combine(group_dict, group_llm):
    """Trust the answer only when both methods agree. Otherwise 'other'."""
    if group_dict == group_llm:
        return group_dict
    return "other"