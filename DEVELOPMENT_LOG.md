# Development log

How I built this project, how AI helped, what went wrong, and how I checked the results.

## How I used AI

I used Claude as an AI pair-programmer to accelerate development. I acted as the lead architect and QA engineer: I designed the pipeline, directed the AI to generate the initial boilerplate and scripts, and then rigorously tested, debugged, and refactored the output. 

I ran every script myself. I never trusted code I couldn't execute. Where the AI's logic failed or hit API limits, I diagnosed the errors, read the logs, and directed the fixes. Gemini is used as the core vision and embedding engine inside the system itself.

Decisions that were mine:
- I chose the cloud path (Gemini) instead of a local model.
- I kept the Gemini call for finding a post's animal, next to the dictionary, because I thought an AI call added value. We then measured both.
- I asked for a script to check the exam captions, instead of opening 12 photos by hand.
- I dropped a comparison of two Gemini models, because it would have given about 25 images and one run each.
- I noticed that `gemini-3.8-flash` described `ambiguous_05` better, which led us to check the captions.

## Where the AI was wrong or I did not use its output

- An early AI draft gave me a JSON file of ready-made tags and confidence scores for images I had not run, and a script with photo IDs it called "verified". The tags were not real model output and the script needed files I did not have. I did not use either. All tags in this project come from running Gemini on my own photos.
- The first design had 8 tables. The AI said that was too many for 62 images. I used 5 tables and stored the number lists as JSON on the image and post rows.
- The first guard rule compared the subject text exactly. That would refuse "golden retriever" for a "dog" post. We changed it to a fixed list of groups (fox, wolf, dog, bear, deer, cat, owl, person, other).
- The first similarity cutoff of 0.70 was a guess and was wrong (see below).
- The first exam answer key had three posts whose photo did not fit the post.

## Bugs and problems

| Problem | Cause | Fix |
|---|---|---|
| Pexels refused to give an API key | Key requests were paused | Used the Pixabay API instead |
| `pip install` failed on `google-genaipip` | Two lines in `requirements.txt` were joined | Rewrote the file, one package per line |
| First batch run: 20 images failed with `429` | `gemini-3.8-flash` allowed only 20 requests a day on the free tier. Failed retries also count | Found the limit on the Rate Limit page and switched to `gemini-3.5-flash-lite` (500 a day). Kept the old results in a separate database |
| Batch kept retrying after the quota was gone | No stop rule | Added a stop after 3 failed images in a row |
| Embedding test: `IndexError` | I sent 3 texts in one call and got back one vector | Changed `embed_texts` to one call per text and added a length check |
| `check_eval_set.py` said 0 problems, but 3 posts did not fit their photos | The script only compares animal groups. A retriever post pointed to an Australian Shepherd | Read the captions, searched them with `find_captions.py`, and rewrote the three rows |
| Exam: every post got "no match" at cutoff 0.50 or more | Scores from this embedding model are low (correct photos scored 0.21 to 0.48). Blurry photos with vague captions also ranked first | Looked at the real scores with `diagnose.py`, tried cutoffs from 0.10 to 0.50, and chose 0.20 |
| `test_low_similarity_is_rejected` failed | The test used 0.40, which is above the new cutoff, so the guard accepted it | Changed the test value to 0.10 |
| `ImportError: cannot import name 'SessionLocal'` | While editing `db.py` for the API, the `SessionLocal` line was lost | Restored the bottom of the file. The edit also added `check_same_thread=False`, which SQLite needs for a web server |
| First `pytest` run took 235 seconds | Slow first start on my PC | The second run took a few seconds. Not investigated further |
| pytest failed on a clean clone | It collected `scripts/test_*.py`, which call Gemini and need a key | Added `pytest.ini` so pytest runs only `tests/` |

## The threshold story

I wrote 0.70 into the design as a starting guess. When I measured `red fox` against `Vulpes vulpes` the score was 0.53, so I expected trouble. The first full run refused almost everything. `diagnose.py` showed the correct photos scored between 0.21 and 0.48. I then ran the exam at cutoffs from 0.10 to 0.50. Results stayed the same from 0.10 to 0.20, lost one post at 0.25, and collapsed at 0.50. I chose 0.20.

I also learned that the cutoff matters less than I planned. No wrong animal was suggested even at 0.10, because the group check does that work. I changed the exam to count "right animal" next to "exact photo", because with ten photos per animal the exact-photo score punished correct answers.

## How I checked the results

- **Unit tests.** 35 tests in `tests/`. They cover the dictionary, the schema, the guard, cosine similarity, the database duplicate rule, the animal-agreement rule, and the API errors. The first guard test is a wolf with similarity 0.91 on a fox post, and it must be refused.
- **Gemini against my labels.** `check_truth.py` compares each photo's group with the true label. No unflagged photo was wrong, and the 6 flagged photos were the degraded ones.
- **Reading the captions.** I used the captions to check my exam answer key. This found 3 wrong pairs.
- **Looking at photos.** I looked at all 62 photos and checked every label. I also tested 5 husky photos on purpose, and Gemini called all five `dog`.
- **Exam on real data.** `run_eval.py` shows the right-animal count, the wrong-animal count and the refused count at each cutoff.
- **Dictionary against Gemini.** An AI assistant drafted 9 harder posts that do not name the animal. The dictionary got 15 of 23 right, Gemini got 23 of 23, and the "both agree" rule got 15 of 23 with no wrong animal passed.
- **The API in the browser.** I approved an accepted photo (200) and tried to approve a blurry refused photo (409).
- **Fresh database test.** I rebuilt a new database from `seed.json` and ran `run_eval.py` again. The `0.2` row was the same.

## What I did not check

- Only one run per photo, so I do not know how much Gemini's answers change between runs. I saw one case that changed (`ambiguous_10`).
- The system was only tested on the photos and articles I chose for this project. I do not know how it would perform on random images or articles from a real news website.