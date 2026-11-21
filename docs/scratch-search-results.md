# The from-scratch search: results (rows (b) and (c) audited; cell F-both)

**Row (b) `fs-stem` and row (c) `fs-both` ran 2026-11-21 and were audited.** Each audit was an independent recompute
from the 47 per-part score records, and each came back PASS WITH CORRECTIONS; all corrections are taken below.
- Declaration: [scratch-search-plan.md](scratch-search-plan.md).
- Ledger, entry `preset-ladder`: `phase_fs`, `phase_fs_draw`, `phase_fs_answers_stem`, `phase_fs_answers_both`,
  `phase_scratch_stem_outcome` and `phase_scratch_both_outcome`. The two outcome keys are named outside the guarded
  `phase_fs*` keys, so the declared set and the main guard stay as declared. The plan's cell is recorded in
  `phase_scratch_both_outcome`, and `phase_fs_outcome` is left unwritten.
- Code: `learn/scratch_search.py`.
- **The cell is F-both**, after (b) passes and (c) passes. [Row (c)'s section](#row-c-fs-both-the-blurred-dry-guitar-against-the-stem)
  covers its result and what it licenses. Row (a) does not run.

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
  held-half value exactly); 0 non-finite scores. That shows the renders are deterministic, not how non-Cen settings
  are applied; post hoc (the audit's), the search half's improvement predicting the held half's G (r +0.78) covers
  that.
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
  −0.296 / −0.442. Post hoc (the audit's): after 50 the search adds −0.044 [−0.059, −0.029]. Step 2 alone adds about
  −0.02, not readable by the score.
- **Shrunk halfway to Cen:** pool G −0.245, I −0.391, a little less than the answer.
- **The answer against the row's centre:** −0.319 [−0.416, −0.223].
- **Against the stored label** (C2's label, whose search used this held half, so in-sample here; zero renders): the
  label reads −0.383 [−0.482, −0.284] against Cen (declared). Post hoc (the audit's): the answer is worse than the
  label by **+0.067 [+0.038, +0.097]** and beats it on 13 of 47 parts; G and the label correlate across parts (r +0.88:
  the same parts have the most headroom), but the answer does not land in the label's region: its distance to the
  label in unit space (RMS 0.256) is larger than Cen's (0.227), and it is closer to the label than Cen on only 16 of
  47 parts. The gap is not the stem's cost
  against a clean reference: the Control row (true DI, clean record) does not run on this path.
- **By set, BKS is on the ear line:** BKS G −0.160, its interval reaching −0.086, BKS crunch −0.106. Post hoc (the
  audit's), per part: 8 of 16 BKS parts reach −0.10 (median −0.113), against 23 of 24 GOAT and 7 of 7 panel parts; one
  part of 47 has G ≥ 0 (+0.005, BKS).
- **The heavy cells are weakest:** Storm Of Particles −0.158 [−0.351, +0.035] over 4 parts (BKS crunch Storm −0.039).
  Post hoc (the audit's): BKS+GOAT without that band −0.276 [−0.323, −0.228].
- **Clean and crunch, half A, without real out, without heavy lenders, each cluster left out:** every mean beyond
  −0.10 on G and I in each set; the panel's own cuts are wide (one to three DI files).

## Fragility (post hoc, the audit's)

- **Dropping one 3-part panel DI file** leaves the panel with df 1 and the pool reads **undecided** (Aimee Norwich
  RAW_05_02 out: G −0.280 [−0.582, +0.022]; The Laminar Flow ElecGtr01 out: G −0.311 [−0.803, +0.181]), while the
  means barely move (−0.28 to −0.36). That is the panel's interval width, not the gain moving. Dropping the 1-part panel
  DI file, or any one BKS DI file, the pool still passes.
- **Leaving out one band:** BKS+GOAT passes in all 5 cases. The deciding pool passes in 4; **without Forkupines it reads
  undecided**, G −0.348 [−0.846, +0.151] (I −0.464 [−0.870, −0.059]). The same panel df mechanism: all three of The
  Laminar Flow's parts are in that band.
- The pool flooring the Welch df is conservative (with the exact df pool G is [−0.432, −0.198]).
- `pipeline_fix.t95` (z above 30 df, open from W0) touches no deciding interval here (the largest df used is 28); only
  the side row over all 47 parts by DI file (df 34) is about 2.7% too narrow. Left for its separate fix.

## The halves and the target

- The halves are disjoint but adjacent, with no gap (A 1.0–5.5 s, B 5.5–10 s; 29 parts searched A, 18 B). The held half
  is more notes of **the same recording and rig**, not an independent recording.
- The search judged the search half only, against the stem, with the held half zeroed; the score judged the held half
  against the clean record, not the stem, so the result is not circular. The lag is the stored one, shared by every
  arm, and the separator saw the whole mix.

## What row (b) does not say

Row (b) says nothing in these cases:
- without the true DI (row (b) is the ceiling on the dry guitar);
- with other guitars in the mix;
- on released mixes;
- by ear;
- about effects;
- with level, timing or lag errors.

**Row (c)** (`fs-both`: a blurred dry guitar made from the true DI, against the same stem) was the coded next row. It
passed, giving F-both; see below. Row (a) `fs-blur` does not run.

**The end user gives only the song, never a DI.** So row (b), on the true DI, is necessary, not sufficient. Nothing in
the product changes.

## Row (c) `fs-both`: the blurred dry guitar against the stem

Row (c) runs on the same 47 parts, with the same search, Cen and partners as row (b). One thing changes: the search's
dry guitar is `di_robustness`'s avg+mild blur of the true DI, in place of the true DI. The reference is still the
`xlnoG@-3` stem. The score is unchanged: the answer goes through the true DI, judged on the held half against the
clean record.

**avg+mild is a best case for a dry guitar.** It is made from the true DI, so it is note-exact and time-exact. A dry
guitar rebuilt from the song's notes must at least match it.

### What ran

- **Search:** from merged main `3a20dbe0`, held half zeros in every search process.
  - 47 of 47 parts searched, 0 refused, 0 fallbacks.
  - Step 2 kept the canonical start on all 47.
  - **12,317 search renders** in 6,287 s wall on 3 processes, about 7,050 an hour.
  - Post hoc (the audit's), the search used avg+mild on all 47 parts. Its first evaluation equals the draw's position-0
    value exactly, and differs from the true-DI value on 46 of 47. No search record holds a held-half value.
- **Answers:** built from main `6e7c7a88` with zero renders. Hashed before the score (`phase_fs_answers_both`, #542),
  and byte-identical at score time (all 47 score records carry that hash).
- **Score:** from merged main `e8f21f2f`. **940 renders** in 840 s wall, 10 settings a part, as in row (b).
  - The scoring control held on 47 of 47: Cen repeated its stored held-half value exactly, and equals row (b)'s Cen,
    render sha256 included.
  - The partners are identical to row (b)'s.
  - 0 non-finite scores and 0 refusals, against a stop of 3.
- **Read:** once.
- **Total for the row:** 13,257 renders. Trusted data only.

### The result: passes, narrowly (cell F-both)

| Reading | G (answer against Cen) | I (against borrowed answers) |
|---|---|---|
| **Pool, BKS+GOAT+panel (deciding)** | **−0.148 [−0.246, −0.050]** | **−0.376 [−0.452, −0.300]** |
| BKS+GOAT (beside) | −0.087 [−0.155, −0.018], undecided | −0.365 [−0.461, −0.269] |
| BKS (16 parts, 8 DI files) | −0.008 [−0.101, +0.085] | −0.337 [−0.516, −0.158] |
| GOAT (24 parts) | −0.166 [−0.275, −0.057] | −0.393 [−0.474, −0.313] |
| Panel (7 parts, 3 DI files) | −0.272 [−0.599, +0.055] (part-weighted −0.314) | −0.397 [−0.599, −0.195] |
| Band-weighted (5 class×lender-band cells, equal, descriptive) | −0.129 | −0.315 |

- **Reading (`row_reading`):** passes. G and I are each decided better, with the mean beyond −0.10, on the deciding pool.
  - All 3 panel DI files were read.
  - B1 (constant) does not fire, because I passes.
  - B2's lever is for row (b) only.
- **BKS+GOAT reads undecided.** G is decided better, but its mean is short of −0.10. This reading is beside; it does
  not decide.
- **The cell:** (b) passes and (c) passes, which gives **F-both**. N3 is met: W0 read W-some.
- **The edge:** the top of G's interval is −0.050, the edge of the user's 0.05 rule. With the exact t in place of the
  floored df, it is [−0.243, −0.053].

**G is the size to read.** I adds nothing beyond G here. It is larger only because the borrowed answers read
+0.227 [+0.156, +0.298] worse than Cen on the pool.

**Is the gain the part's own?** The row's centre (the mean of the other parts' answers) against Cen is
G_centre +0.024 [−0.022, +0.071].
- By `number_reading`, its lower end reads "fails": it rules out a gain beyond −0.05. So the row's centre is no better
  constant.
- On BKS+GOAT the centre is worse than Cen: +0.052 [+0.010, +0.095]. (The answer less the centre, −0.173, is inflated
  by that bad centre, so it is not cited as the evidence.)

**In-search signal: none** (post hoc, the audit's). In row (b), how much a part's search improved its search half
predicted its held-half G (r +0.78). In row (c) it does not (r 0.00, Spearman 0.21; BKS −0.48, GOAT −0.19). Nothing seen
at search time flags a bad answer.

### The pass is narrow and carried by the panel (post hoc, the audit's)

- **The panel carries it.** Its 7 parts of 47 give 61% of the pool mean (equal set weights), and 35% of the summed G.
  Without the panel the row does not pass: BKS+GOAT is undecided.
- **Dropping one panel DI file:** under the coded rule the pool reads undecided in 3 of 3 cases. With fewer than 3
  panel DI files the rule falls back to BKS+GOAT, which reads undecided.
  - Post hoc (the write-up's), with the panel kept in the pool on its 2 remaining files:
    - without Aimee Norwich RAW_05_02 it still passes (G −0.112 [−0.163, −0.060]);
    - without Big Troubles RAW_03_08 (1 part) it reads undecided;
    - without The Laminar Flow ElecGtr01 it reads undecided.
- **Dropping any single BKS or GOAT cluster** (32 of them): the pool still passes.
- **Leaving out one band:** the pool reads undecided without Forkupines or without Storm Of Particles, and passes without
  each of the other 3 bands. Post hoc (the write-up's), BKS+GOAT is undecided in all 5 cases.
- **By class, BKS+GOAT:** clean −0.079 [−0.205, +0.048] and crunch −0.095. Both are undecided, and clean is not decided
  better at all. Post hoc (the write-up's), crunch's interval is [−0.175, −0.014].

### The heard size

- **Parts at −0.10 or beyond, by set (G):** BKS 6 of 16 (median −0.014), GOAT 16 of 24, panel 6 of 7.
- **Parts at +0.10 or worse than Cen: 8 of 47, against 0 in row (b).** One GOAT clean part reads +0.777.
  - That is about 1 part in 6 landing worse than Cen, by the score, at a gap the ear usually hears.
  - Nothing in the search signals it.
- **The pool as a whole:** its interval reaches −0.050, where the score and the ear agree only at chance.
  - A heard gain is likely on the panel and GOAT.
  - It is not shown on BKS.
  - It is not assured for the pool.

### The blur's cost against row (b) (post hoc, the audit's)

Per part, answer(c) less answer(b) on the held half. Cen is identical in both rows.

- **Pool: +0.167 [+0.110, +0.224].** By set: BKS +0.153, GOAT +0.203, panel +0.146 [−0.015, +0.307].
- **Per part:** row (c) is worse by 0.10 or more on 27 of 47 parts, and better by 0.10 or more on 2.
- **Share of row (b)'s G kept:** 47% overall. BKS 5%, GOAT 45%, panel 65%.
  - BKS had the least headroom in row (b).
  - r(G(b), G(c)) within BKS is +0.33.
- **Clean loses most.**
  - BKS+GOAT clean: BKS +0.220, GOAT +0.305. Crunch: +0.086 and +0.101.
  - By band: Hazael +0.285, The Travelling Band +0.230, Forkupines +0.118, Storm Of Particles +0.083.

### Beside the deciding reading

- **Checkpoints (pool G):** at 50 evaluations −0.130 [−0.267, +0.006]; at 100 −0.121; at 200 −0.143; the final answer
  −0.148. For I: −0.358, −0.348, −0.370 and −0.376.
- **Shrunk halfway to Cen:** pool G −0.198 [−0.276, −0.120], I −0.425. Unlike in row (b), the shrunk answer reads closer
  than the answer.
  - Post hoc (the audit's), answer less shrunk: pool +0.049 [−0.027, +0.126], undecided; BKS+GOAT
    +0.061 [+0.019, +0.103].
  - This is **not overshoot**. The answer moves as far from Cen as in row (b): unit RMS 0.239 against 0.240. Post hoc,
    the reading is a noisier direction, so halving the move halves the error.
  - Even shrunk, row (c) reads +0.118 [+0.063, +0.173] worse than row (b)'s answer.
- **The stored label less Cen:** −0.383 [−0.482, −0.284]. This is the same in-sample label as row (b), zero renders.

### What it licenses

**F-both, as declared:**
- build the song-time search for alone windows behind a flag, for testing only (N3 met; W0 W-some);
- next, a real note-matched dry guitar on the same rows (waits for the user);
- then a blind sitting;
- no claim on released mixes.

The coded rule warrants this, and a flagged build is cheap to undo. The audit tempers it:
- BKS+GOAT and the clean class are undecided.
- The pass rests on the panel's 3 DI files.
- G's interval reaches the 0.05 edge.
- About 1 part in 6 lands worse than Cen at a heard gap, with no in-search signal to catch it.
- I adds nothing beyond G.
- avg+mild is a best case, and it keeps under half of row (b)'s gain, least on clean parts.

**The flagged build is held, pending the user.** The audit recommends two steps first:
1. Score the note rebuild's real dry guitar on these same 47 rows, the same way, with the shrunk answer declared as an
   arm.
2. Then a blind sitting that includes the losing parts (the 8 at +0.10 or worse) and reports regret.

### What row (c) does not say

Row (c) says nothing in these cases:
- with a dry guitar rebuilt from the song's notes (avg+mild is made from the true DI);
- with other guitars in the mix;
- on released mixes;
- by ear;
- about effects;
- with level, timing or lag errors.

The halves and the target are as in row (b): adjacent halves of the same recording and rig, and the score judged
against the clean record, not the stem. Nothing in the product changes.
