# image-match-guard
# image-match-guard

A system that picks the right photo for an article, and says "no confident match" when no photo fits.

A post about red foxes should get a fox photo. It should never get a wolf photo, even though the two look and read alike. The most important part of this project is the guard, which refuses a wrong match and gives a reason.

Built by Suraiya Binte Akbar.

## How it works

1. **Photos.** 62 photos (mostly animals: fox, wolf, dog, bear, deer, plus 12 hard cases like blurry, dark, or odd subjects).
2. **Gemini reads each photo.** It returns a caption, an animal group, and a confidence score from 0 to 1. Pydantic checks the answer. A bad answer is retried, never saved. The batch job stops after 3 failures in a row.
3. **Low confidence is flagged.** Photos under 0.60 are marked "not sure" and are never suggested.
4. **Text becomes numbers.** Each caption and each post is turned into 768 numbers with `gemini-embedding-2`. Cosine similarity then measures how close a post is to each caption.
5. **Each post gets an animal.** A keyword dictionary (`app/taxonomy.py`) and a Gemini call both guess it. If they disagree, the animal is `other` and nothing is suggested.
6. **The guard checks the photos from best score to worst.** The first photo that passes all rules is the suggestion. If none pass, the system returns "no confident match" with reasons.
7. **A person reviews it** through a small API: approve, reject, or see why. A person cannot approve a photo the guard refused.

~~~
photo -> Gemini caption + group + confidence -> caption numbers
post  -> dictionary + Gemini animal           -> post numbers
rank photos by similarity -> guard -> suggestion, or "no confident match"
~~~

### Guard rules

A photo must pass all four checks, in this order:

1. Gemini was sure about the photo (confidence at least 0.60, not flagged).
2. The post's animal is known (not `other`).
3. The photo's animal group equals the post's group. Example reason: `group mismatch: expected fox, detected wolf`.
4. The similarity score is at least 0.20.

Similarity alone is not enough. A fox caption and a wolf article are both about wild canines in a forest, so they score close. In my data, on the wolf post a fox photo (fox_04) scored about 0.35, a little higher than the wolf photo the system accepted (wolf_01, 0.345). The two scores are very close, but the point holds: a higher score does not mean the right animal. The group check prevents this.

## Results

All numbers come from `data/eval_results.txt` and `data/extractor_results.txt`.

**Vision (62 photos, `gemini-3.5-flash-lite`)**
- 62 calls worked with no retries. The cost log also shows 9 failed calls from an earlier run when I typed the wrong model name.
- 6 of the 7 degraded photos got low confidence and were flagged, so they are never suggested. The seventh, `ambiguous_10`, scored 0.65 and was not flagged.
- No unflagged photo had the wrong animal compared with my labels (for the 50 clear photos, my label is the file name).
- 5 husky photos in `data/hard_cases/` were all called `dog` (0.98 to 0.99).

**Matching (14 exam posts, cutoff 0.20)**

| Measure | Result |
|---|---|
| Right animal, among 12 posts that have a photo | 12 of 12 |
| Wrong animal suggested | 0 |
| Exact photo from my answer key | 5 of 12 |
| Posts with no fitting photo, refused | 2 of 2 |

The exact-photo score is lower because ten photos show each animal and my key names only one. For post 1 the system picked `fox_04` and my key says `fox_01`. Both are foxes. I report this number because it is the strict one, but "right animal" is the fairer one.

I chose 0.20 because it is the highest of the cutoffs I tried (0.10 to 0.50) that loses no posts. At 0.25 the cat post is lost (its only photo scored 0.21, just 0.01 above the cutoff), and at 0.50 almost everything is refused. Scores from this embedding model are low even for correct matches (0.21 to 0.48), so my first guess of 0.70 would have refused everything.

**Finding the animal in a post (23 posts)**

| Method | Correct |
|---|---|
| Dictionary alone | 15 of 23 |
| Gemini alone | 23 of 23 |
| Both must agree (used by the system) | 15 of 23 |

The dictionary misses 8 posts. Seven describe the animal without naming it, like "a rust-coloured hunter slips through the hedgerows". The eighth (post 23) names both a fox and a wolf, so the dictionary ties and answers "other". The dictionary alone would send these 8 posts to the guard as "other", and the guard refuses them. A wrong animal was passed to the guard 0 times. I kept the "both must agree" rule because a refused post costs little and a wrong photo costs a lot.

## Screenshots

- `docs/screenshots/post3_match.png`: Wolf post. The wolf photo is accepted, and one photo of a different animal is refused for group mismatch.
- `docs/screenshots/post9_no_match.png`: Foxes-and-wolves post. The system returns "no confident match" with reasons.
- `docs/screenshots/review_200.png`: A person approves an accepted suggestion via the API.
- `docs/screenshots/review_409.png`: The API blocks a person from approving a photo the guard refused.

## Run it

Needs Python 3.11 or newer. You do not need a Gemini key to see the results. The saved results are in `data/seed.json`.

~~~
git clone https://github.com/suraiyabinteakbar/image-match-guard.git
cd image-match-guard
python -m venv .venv
source .venv/Scripts/activate        # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python scripts/import_seed.py        # builds data/app.db from seed.json
python scripts/run_eval.py           # the exam table
python -m pytest                     # 35 tests
uvicorn app.main:app --reload        # review API, open http://127.0.0.1:8000/docs
~~~

In the API, try `GET /posts/3/images` (a match) and `GET /posts/9/images` (no confident match). Posts 15 to 23 are only used to test animal-finding and have no embedding, so the API correctly returns a 409 error for them.

### Rebuild with Gemini

This makes new Gemini calls, so numbers may differ a little between runs. The photos are already in `data/images/`, so you do not need to download them again. Copy `.env.example` to `.env` and fill in your Gemini key. Set `GEMINI_MODEL=gemini-3.5-flash-lite` and `EMBEDDING_MODEL=gemini-embedding-2`. Delete `data/app.db` if it exists. Then:

~~~
python scripts/run_batch.py          # Gemini reads the photos
python scripts/embed_images.py       # captions to numbers
python scripts/load_posts.py         # posts to the database
python scripts/compare_extractors.py # dictionary vs Gemini on posts
python scripts/export_seed.py
~~~

`download_images.py` and `make_degraded.py` made the photo set. They are only needed to create new photos.

`export_seed.py` overwrites `data/seed.json`, so copy the old one first if you want to keep it.

The free Gemini tier has daily limits. If a run stops with a 429 error, wait and run it again. Finished photos are skipped.

## Folders

- `app/`: the system (guard, ranking, embeddings, dictionary, database, API)
- `scripts/`: commands you run
- `tests/`: 35 tests
- `data/`: photos, labels, exam posts, results, `seed.json`
- `docs/`: `design.md` (the plan) and screenshots

See `docs/design.md` for the plan and `DEVELOPMENT_LOG.md` for my development process. License: MIT.

## Limits

- The exam is small: 14 posts. The posts were drafted with AI assistance, and I verified every photo by eye. 12 of 12 does not guarantee perfect behavior on new articles.
- I chose the cutoff on the same 14 posts I scored. On new posts the result may be worse.
- The cutoff does little work. The animal check does most of it. Even at 0.10 no wrong animal was suggested.
- Gemini gives 0.98 to 1.00 for almost every clear photo. Its confidence catches blur and darkness, but it cannot catch a subtle mistake. A confident wrong answer would pass the guard. The 5 husky photos did not show this, but five photos prove little.
- Confidence is not steady. `ambiguous_10` (dark, shrunken dog) got 0.82, 0.75 and 0.65 in three runs on two models. The cutoff of 0.60 is close to that.
- I fixed three exam rows after reading Gemini's captions, so my answer key is not fully independent of Gemini.
- The dictionary only knows the words in its list.
- The cat post and the owl post each have only one matching photo in the library, so they are easy tests.
- Five blurry photos score high against almost any post, because their captions are vague. The guard refuses them, but they fill the top of the ranking.
- Some hard photos are degraded copies of clear photos, made by `scripts/make_degraded.py` and listed in `data/degraded_sources.csv`.
- Costs are logged as $0.00 because the Gemini free tier was used and the prices in the code are set to 0. Token counts are recorded for vision and post-animal calls, not for embedding calls.
- The database is SQLite. It is fine for one user, not for many writers at once.