# Design: image-match-guard

## 1. Problem
Given a library of images and a set of articles, suggest the right image for
each article, and refuse (with a reason) when no image is good enough.

## 2. Non-goals
- No frontend (API endpoints and tables only).
- Not a general image search engine.
- No model training; I use pretrained vision and embedding models.

## 3. Image metadata schema (validated with Pydantic)
{
  "subject": "red fox",
  "group_name": "fox",
  "category": "animal",
  "attributes": ["orange fur", "forest"],
  "caption": "A red fox standing in a forest",
  "confidence": 0.94
}
- confidence must be between 0 and 1.
- group must be one of: fox, wolf, dog, bear, deer, cat, owl, person, other.
  The model must pick from this fixed list (a controlled vocabulary), so
  "Vulpes vulpes" and "red fox" both become "fox".

I fixed the list because the guard needs a plain equality check. Comparing
free text would reject "golden retriever" against a post about dogs. If the
model returns anything outside the list, validation fails and the call is
retried.

## 4. Pipeline
Images -> batch job -> vision model -> validate -> metadata
metadata.caption -> embedding -> stored with the image
Post text -> two independent group extractors:
    (a) taxonomy.py keyword dictionary (local Python, free, deterministic)
    (b) Gemini text call, output validated against the same allowed list
  -> if (a) and (b) agree: expected_group = that group
  -> if they disagree: expected_group = "other" (cannot verify)
Post text -> embedding -> stored with the post
Post vector x image vectors -> cosine ranking -> mismatch guard -> suggestion

I use two extractors because each one fails in a different way. The dictionary
is free and easy to test, but it only knows the words I typed in. The Gemini
call understands paraphrases, but it can be confidently wrong. When they agree
I trust the answer more than either one alone. When they disagree I would
rather refuse than pick one. I'll measure the dictionary, Gemini, and their
agreement on the eval posts and report all three numbers.

## 5. Mismatch guard rules (all must pass)
1. Confidence: image.confidence >= 0.60 and not flagged, else REJECT
   "low confidence image".
2. Post group known: post.expected_group != "other", else REJECT
   "cannot verify what the post is about".
3. Group match: image.group == post.expected_group, else REJECT
   "group mismatch: expected fox, detected wolf".
   If image.group is "other", REJECT "cannot verify image subject".
4. Similarity: cosine >= T (tuned on the eval set, initial guess 0.20), else
   REJECT "similarity below threshold".
If every candidate is rejected -> "no confident match" + the reasons.

## 5b. Safety and reliability
The core goal is not to find a match but to avoid a wrong one.
- Structured output: all model output is schema-validated (Pydantic) before it
  touches the database. This catches malformed output, not wrong answers.
- Wrong-but-well-formed answers are handled by the guard and measured by the
  eval set.
- Low-confidence flagging: confidence < 0.60 means the image is flagged and
  cannot be recommended.
- Two independent extractors for the post group: agreement is stronger
  evidence than either alone.
- Explainability: every rejection returns a human-readable reason.

## 6. Database tables (SQLite via SQLAlchemy)
- images: id, filename, true_subject, subject, group, category, attributes (JSON),
  caption, confidence, flagged, caption_vector (JSON), processed_at
- posts: id, title, body, group_dict, group_llm, expected_group, group_note,
  post_vector (JSON)
- suggestions: id, post_id, image_id, similarity, decision (accepted/rejected),
  reason, review_status (pending/approved/rejected), review_note, reviewed_at
- cost_log: id, kind (vision/embedding/text), model, image_id, post_id,
  input_tokens, output_tokens, cost_usd, status, created_at
- jobs: id, kind, status, total, done, failed, retries, error, created_at
Indexes: unique(post_id, image_id) on suggestions (a retry cannot create a
duplicate), index on suggestions.post_id, index on images.group.

Vectors are stored as JSON arrays on the image and post rows instead of in
separate tables. With about 60 images the extra joins would only make the code
longer. If the library grew to a few thousand images I would move to Postgres
with pgvector.

## 7. Evaluation
- data/ground_truth.csv holds the true subject of each image.
- data/eval_set.csv: 10+ posts, each labeled with its one correct image and
  its true group.
- Metrics: top-1 precision for ranking; accuracy of each group extractor
  (dictionary, Gemini, and agreement of both).
- T is chosen by sweeping values on this set.

## 8. Known risks
- Model confidence can be high even when the model is wrong.
- Small dataset (about 62 images): results are indicative, not statistical proof.
- Some ambiguous images are degraded copies of clear photos (degraded_sources.csv).
- A husky labeled "wolf" by the model would pass the group check; the guard
  cannot fix a wrong model answer, only catch inconsistencies.
- The dictionary can miss new animals or mixed posts; it returns "other"
  instead of guessing.
- SQLite instead of Postgres: fine at this scale, not for concurrent production.

## 9. Batch processing and cost tracking
Vision, embedding, and post-group calls run in a background job tracked in the
jobs table, with retries. Every AI call is logged in cost_log, attributed to an
image or post. A budget guard (MAX_BUDGET_USD in .env) aborts the job if spend
exceeds the limit. On the free tier the cost is $0, but tokens are still
recorded. The dictionary extractor is local Python and adds no AI cost.