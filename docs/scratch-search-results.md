# The from-scratch search: results (row (b) audited; row (c) running)

**Row (b) `fs-stem` ran 2026-11-21 and was audited** (an independent recompute from the 47 per-part score records:
PASS WITH CORRECTIONS, all taken below). Declaration: [scratch-search-plan.md](scratch-search-plan.md); ledger
`preset-ladder` `phase_fs`, `phase_fs_draw`, `phase_fs_answers_stem`, `phase_scratch_stem_outcome` (named outside the guarded `phase_fs*` keys, so the declared
set and the running row's main guard stay as declared). Code
`learn/scratch_search.py`. Row (c) `fs-both` is the coded next row and is running; `phase_fs_outcome` waits for the
plan's cell.

Every number is **by the score** (J0, ln(d_row / d_against) on the held half against the clean record; below zero is
closer), never heard. 90% cluster t intervals. "Passes" = decided better with the mean at −0.10 or beyond.

**What it is.** On 47 of the note-matched replay's held-out parts, C2's label search starts from the centre preset
(Cen) and is steered only on one half of the part (the search half). Row (b) gives it the true DI and X-LANCE's stem of
a self-built mix with no other guitar, at −3 dB (`xlnoG@-3`). The other half (the held half) is zeros in every search
process. The answer is then rendered through the true DI and scored on the held half against the clean record. **G** =
the answer against Cen. **I** = G less the mean of 3 borrowed answers (other parts' answers from the same search, same
amp and class), so a search that only drifts to a better fixed preset does not pass on I.

## What ran

- Search and answers from merged main `baa45d78`; score and read from merged main `3a20dbe0` (no code change between
  them). Every guard (on main, the draw's hash, the answers' hash, C3r's state) passed.
- **Search:** 47 of 47 parts, 0 refused (the stop is 3), 0 fallbacks; every start check was exact against the replay's
  position 0; step 2 kept the canonical start on all 47. Step 1 is 200 evaluations plus 1 priming render on every part;
  a part's total also holds step 2's evaluations and their primings (about 262 renders a part). **12,351 search
  renders**, measured: the first 6 parts at about 6,560 an hour on 3 processes, the other 41 at about 6,970 an hour
  (5,571 s wall).
- **Answers:** hashed before the score (`phase_fs_answers_stem`, #540) and byte-identical at score time.
- **Score:** **940 renders** in 830 s wall, 10 settings a part (Cen, the answer, the 50/100/200 checkpoints, the shrunk
  answer, the row's centre, the 3 borrowed answers). The scoring control held on 47 of 47 (Cen repeated its stored
  held-half value exactly); 0 non-finite scores.
- **Read** once. Trusted data only: Silent Waves was never in the draw and Drowning's parts were left out by the draw.

## The result: passes (G and I, on the pool and on BKS+GOAT)

| Reading | G (answer against Cen) | I (against borrowed answers) |
|---|---|---|
| **Pool, BKS+GOAT+panel (deciding)** | **−0.315 [−0.454, −0.177]** | **−0.462 [−0.579, −0.344]** |
| BKS+GOAT (beside) | −0.264 [−0.310, −0.219] | −0.454 [−0.509, −0.399] |
| BKS (16 parts, 8 DI files) | −0.160 [−0.235, −0.086] | −0.400 [−0.470, −0.329] |
| GOAT (24 parts) | −0.369 [−0.429, −0.308] | −0.508 [−0.598, −0.418] |
| Panel (7 parts, 3 DI files) | −0.417 [−0.803, −0.032] (part-weighted −0.486) | −0.477 [−0.872, −0.083] (part-weighted −0.552) |
| Band-weighted (5 lender bands, equal, descriptive) | −0.298 | −0.407 |

**Reading (`row_reading`):** passes; B1 (constant) and B2's lever do not apply. **The cell:** none yet; `next_row`
gives row (c) `fs-both` (the blurred dry guitar, avg+mild, against the same stem), the coded next row.

**In plain terms:** with the true dry guitar and a separated stem of a mix with no other guitar, a search of about 262
renders from the centre preset lands about 0.3 closer than Cen to the real record on notes it never heard, by the
score. **G is the size to read** for what might be heard. I is larger only because the borrowed answers read worse
than Cen here (+0.146 [+0.068, +0.224] on the pool; worse on 37 of 47 parts), so I carries that penalty.

**The gain is the part's own:** G passes while the row's own centre (the mean of the other parts' answers) reads level
with Cen (G_centre +0.004 [−0.025, +0.033], not readable by the score), so moving every part the same way does not
explain it. Post hoc (the audit's): how far a part's search improved its search half predicts its held-half G
(r +0.78), and a partner's own gain does not predict how its answer transplants (r −0.08).

## Beside the deciding reading

- **Checkpoints:** most of the gain is there at 50 evaluations (pool G −0.271, I −0.418); 100: −0.287 / −0.434; 200:
  −0.296 / −0.442. After 50 the search adds −0.044 [−0.059, −0.029] (the audit's); step 2 alone adds about −0.02, not
  readable by the score.
- **Shrunk halfway to Cen:** pool G −0.245, I −0.391, a little less than the answer.
- **The answer against the row's centre:** −0.319 [−0.416, −0.223].
- **Against the stored label** (C2's label, whose search used this held half, so in-sample here; zero renders): the
  label reads −0.383 [−0.482, −0.284] against Cen; the answer is worse than it by **+0.067 [+0.038, +0.097]** and
  beats it on 13 of 47 parts. G and the label correlate across parts (r +0.88: the same parts have the most headroom),
  but the answer does not land in the label's region: its distance to the label in unit space (RMS 0.256) is larger
  than Cen's (0.227), and it is closer to the label than Cen on only 16 of 47 parts. The gap is not the stem's cost
  against a clean reference: the Control row (true DI, clean record) does not run on this path.
- **By set, BKS is on the ear line:** BKS G −0.160, its interval reaching −0.086, BKS crunch −0.106; per part, 8 of 16
  BKS parts reach −0.10 (median −0.113), against 23 of 24 GOAT and 7 of 7 panel parts. One part of 47 has G ≥ 0
  (+0.005, BKS).
- **The heavy cells are weakest:** Storm Of Particles −0.158 [−0.351, +0.035] over 4 parts (BKS crunch Storm −0.039).
  Post hoc (the audit's): BKS+GOAT without that band −0.276 [−0.323, −0.228].
- **Clean and crunch, half A, without real out, without heavy lenders, each cluster left out:** every mean beyond
  −0.10 on G and I in each set; the panel's own cuts are wide (one to three DI files).

## Fragility (post hoc, the audit's)

- **Dropping one 3-part panel DI file** leaves the panel with df 1 and the pool reads **undecided** (Aimee Norwich
  RAW_05_02 out: G −0.280 [−0.582, +0.022]; The Laminar Flow ElecGtr01 out: G −0.311 [−0.803, +0.181]), while the
  means barely move (−0.28 to −0.36). That is the panel's interval width, not the gain moving. Dropping the 1-part panel
  DI file, or any one BKS DI file, the pool still passes; leaving out any one band, BKS+GOAT passes in all 5 cases.
- The pool flooring the Welch df is conservative (with the exact df pool G is [−0.432, −0.198]).
- `pipeline_fix.t95` (z above 30 df, open from W0) touches no deciding interval here (the largest df used is 28); only
  the side row over all 47 parts by DI file (df 34) is about 2.7% too narrow. Left for its separate fix.

## The halves and the target

- The halves are disjoint but adjacent, with no gap (A 1.0–5.5 s, B 5.5–10 s; 29 parts searched A, 18 B). The held half
  is more notes of **the same recording and rig**, not an independent recording.
- The search judged the search half only, against the stem, with the held half zeroed; the score judged the held half
  against the clean record, not the stem, so the result is not circular. The lag is the stored one, shared by every
  arm, and the separator saw the whole mix.

## What it does not say

Nothing without the true DI (row (b) is the ceiling on the dry guitar), with other guitars in the mix, on released
mixes, by ear, about effects, or with level, timing or lag errors. **Row (c)** (`fs-both`: a blurred dry guitar made
from the true DI against the same stem) is the coded next row; it decides whether a song-only route through a rebuilt
dry guitar stays alive. It passes only with G and I each decided better at −0.10 or beyond on BKS+GOAT+panel with all
3 panel DI files read; otherwise row (a) `fs-blur` (the blurred dry guitar against the clean record) runs, by the
cells. Nothing in the product changes.
