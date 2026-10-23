"""Map free text to one canonical group using a fixed alias dictionary.

Never guesses: no match or a tie returns "other", which the guard refuses to verify.
"""
import re
from collections import Counter

GROUPS = ["fox", "wolf", "dog", "bear", "deer", "cat", "owl", "person", "other"]

# Only animals are listed: posts in this project are about animals.
ALIASES = {
    "fox": ["fox", "foxes", "vulpes", "vixen"],
    "wolf": ["wolf", "wolves", "canis lupus"],
    "dog": ["dog", "dogs", "puppy", "puppies", "retriever", "husky", "shiba inu"],
    "bear": ["bear", "bears", "grizzly", "ursus"],
    "deer": ["deer", "stag", "stags", "fawn", "fawns", "cervidae"],
    "cat": ["cat", "cats", "kitten", "kittens", "feline"],
    "owl": ["owl", "owls", "strigiformes"],
}

TITLE_WEIGHT = 3  # a word in the title counts more than one in the body


def _count(text):
    text = text.lower()
    counts = Counter()
    for group, words in ALIASES.items():
        for w in words:
            counts[group] += len(re.findall(rf"\b{re.escape(w)}\b", text))
    return counts


def extract_group(title, body=""):
    """Return (group, note). note explains any fallback to 'other'."""
    counts = _count(title)
    for g in list(counts):
        counts[g] *= TITLE_WEIGHT
    counts.update(_count(body))

    ranked = [(g, c) for g, c in counts.most_common() if c > 0]
    if not ranked:
        return "other", "no known animal named in the post"
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return "other", f"ambiguous: {ranked[0][0]} and {ranked[1][0]} tie"
    return ranked[0][0], ""