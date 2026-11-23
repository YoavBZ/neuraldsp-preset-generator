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
- **The tone split** (plan section 11, `phase_scratch_tone_split`) ran 2026-11-23 and was audited.
  - The measure step's clip moves the yardstick (Cen +0.110 worse through a clip-free DI), not the found presets
    (answer (c) level).
  - So rows (b) and (c) stand as self-consistent and, by the user's decision, are not redone.
  - [Its section](#the-tone-split-the-measure-steps-clip-priced-track-4) covers the numbers, the user's decision and
    the two declared follow-ups.

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

## The tone split: the measure step's clip, priced (track 4)

**Ran 2026-11-23 and audited** (an independent recompute from the 47 per-part files: CONFIRMED WITH CORRECTIONS; all
six corrections are taken below). Declaration: [plan section 11](scratch-search-plan.md#11-the-tone-split-2026-11-23-ledger-phase_scratch_tone),
ledger `phase_scratch_tone`; outcome `phase_scratch_tone_split`. Code: `learn/scratch_tone.py`. Every number is **by
the score**.

**The question.** The measure step clips the correction it asks for at ±15 dB, so the scoring DI sits 2.8 dB from the
average guitar's balance on the 47 parts (max 7.1), against 1.3 dB without the clip (max 2.0). Rows (b) and (c)'s
stored answers were scored again through a clip-free DI (`true-noclip`), and row (c)'s answer through dry guitars that
each carry one part of its blur.

### What ran

- 846 renders (47 parts × 18), about 14 minutes on 3 processes, from a frozen worktree of main at `42cd5953`. The read
  ran once, at zero renders.
- The Cen control (Cen through the coded DI, equal to both rows' stored value and render sha256) was exact on 47 of 47
  parts. No part refused, and no render was non-finite.
- A first launch stopped on every shard's first part, because a stereo render reached a spectrum (fixed in #554). It
  cost 6 renders, none of them kept.
- The judge's DI was the coded DI for every render, as declared.

### The measure step: the fix moves the yardstick, not the presets

| | Pool | BKS+GOAT |
|---|---|---|
| `P_c`: row (c)'s G through `true-noclip`, less its stored G | −0.121 [−0.183, −0.059] | −0.129 [−0.201, −0.057] |
| of which Cen's shift (Cen through `true-noclip` against the coded DI) | +0.110 [+0.047, +0.173] worse | +0.117 worse |
| of which answer (c)'s own shift (`C_fix`) | −0.011 [−0.042, +0.021], level | −0.012, level |
| `P_b`: the same for row (b) | +0.051 [+0.016, +0.085] | +0.031 [−0.002, +0.065] |
| of which answer (b)'s own shift | +0.161 [+0.072, +0.251] worse | +0.148 worse |

Each P is the answer's own shift less Cen's shift; this holds per part to 2e-16.

- **`MC-c-moves`, read as the decomposition.** Cen is 0.110 worse through the clip-free DI, and answer (c) is level
  (`C_fix` −0.011). So `P_c` measures the yardstick moving, not row (c)'s answer getting closer to the record.
  - The cause is the fix's intended effect. Cen's shift follows the in-band clip residual (Spearman +0.80; partial
    +0.67 holding the high-frequency rise), not the high-frequency rise (partial −0.04) or the peak rise (−0.10).
  - On the 6 parts where the clip-free DI is bit-identical to the coded one, `P_c`, `P_b` and Cen's shift are exactly
    0.
  - Split by clip residual: the lower half (0.7 dB) gives `P_c` −0.014, the upper half (3.9 dB) −0.255.
  - The fuller re-balance moves the DI further from the raw guitar that made the record. A fixed preset (Cen) pays the
    full cost. Answer (c) was searched through avg+mild, which already carries the average balance, so it pays nothing.
- **`MC-b-moves` is at its threshold** (mean +0.0507). It fails when one cluster or one panel DI file is dropped
  (+0.042 to +0.063). BKS+GOAT is undecided, and clean (+0.088) and crunch (−0.025) have opposite signs. **No action
  rests on it.** Its content is expected: an answer searched on the coded DI loses more than Cen when the DI changes.
- **Rows (b) and (c) stand as self-consistent.** Each was searched and scored against the coded yardstick. Fixing the
  clip would add about 0.1 to every stored G against Cen (0.15 to 0.2 on clean). It would not move a found preset
  closer to its record.

**The share of row (b)'s gain row (c) keeps:**
- **Stored:** 0.47 on the pool (0.33 on BKS+GOAT).
- **Re-scored on one yardstick:** 1.02 (0.93). This figure is **biased high by row (b) being off its search DI**: 70%
  of its rise comes from answer (b)'s +0.161 off-DI loss.
- **The bracket:** 0.63 to 1.02 (BKS+GOAT 0.57 to 0.93), depending on whether a redone row (b) would regain all or none
  of that loss. It rests on assumptions; only row (b)'s redo would measure it. Both ends exceed the stored share.
- ***Mixed*** ((c) re-scored over (b) stored; a mixed figure, not a share on one yardstick): 0.85 (0.82).

**Within the EQ's reach** (9 parts, 7 BKS and 2 GOAT): `P_c` −0.009, `P_b` −0.001. This is **not evidence either way**.
Three of the 9 have a bit-identical DI, and reach is defined on the measure step's whole ask, not on what the fix
adds (3 of the 6 bit-identical parts count as beyond). The clip-residual split above is the right test.

### Where row (c)'s loss is made (BKS+GOAT): `TN-short`

| Number | BKS+GOAT | Clean | Crunch |
|---|---|---|---|
| `C_fix` (the average balance, by the fix) | −0.012 [−0.057, +0.032] | −0.052 | +0.027 |
| `C_avg` (the average balance, stored `avg`) | +0.004 [−0.043, +0.051] | −0.032 | +0.040 |
| `C_planted` (the planted tilt) | −0.003 [−0.027, +0.022] | −0.007 | +0.002 |
| `C_tilt` (the truth-fitted tilt) | −0.030 [−0.056, −0.005] | −0.071 | +0.010 |
| `C_blur` (the whole blur, through avg+mild) | +0.179 [+0.089, +0.268] | +0.195 | +0.162 |

- **`TN-short`: "the tone costs (`C_tilt`); not a heard size by the split."**
  - `C_tilt` is the only C number below zero. Its mean is under 0.05, so no action rests on it.
  - The planted tilt and the average balance are level.
  - It is **not shown by the split** that row (c)'s loss is carried by the dry guitar's static tone.
  - "Not a heard size" is not "the static tone is cheap": on clean, `C_tilt` is −0.071 at φ 0.74.
- **The average balance's cost** (−`C_avg`): −0.004 [−0.051, +0.043] on BKS+GOAT, −0.008 on the pool. Level, not
  readable by the score.
- **`C_blur` is dominated by the blur's damage beyond tone** (smear, soft clip and bleed): Cen alone scores +0.324
  worse through avg+mild.
- **φ:**
  - By render: 0.47 on BKS+GOAT; 0.74 on clean (per-part median 0.80, GOAT clean 0.92); 0.20 on crunch.
  - From the EQ answers: 0.22; 0.44 on clean; 0.00 on crunch.
  - By render reads about twice the EQ estimate on clean, because the whole chain, not only the 9 bands, takes up the
    dry guitar's tone.
- **The no-drive, no-compressor answers** (15 parts on answer (c); BKS+GOAT read): `P_c` −0.188, `C_tilt` −0.042,
  `C_blur` +0.255, the tone numbers level. They point the same way as the 40.

**On clean, the search bakes the dry guitar's balance into the preset** (φ about 0.8 by render). For the product:
- A rebuilt DI enters through `song_bank.measure`, and on clean its balance error goes into the preset. The measure
  step's balance therefore matters there.
- The clip residual (about 2.3 dB mean, max 7) is small next to a guitar's own distance from the average (7.7 dB raw).
- No score here shows a product loss. Any product change is forward-only and follows the gentle-fix CPU check (plan
  11f).

### The fix's side effects

- The measure step's whole ask above 8 kHz is about +21 dB, and +19 dB even where nothing clips. That is not what the
  fix adds.
- **The fix adds +3.1 dB of energy above 8 kHz on average (max 13.4) and +1.6 dB of peak (max 9.8).** Beyond reach
  this is +3.8 and +2.0; within reach +0.3 and +0.0.
- Once the in-band residual is known, neither explains Cen's shift.
- A rise of up to 13 dB in the highs is a hiss risk, so a gentler fix is priced first.

### The user's decision (2026-11-23, in chat)

After a plain-language explanation, the user answered "Ok" to this recommendation:
1. Don't redo rows (b) and (c). The numbers stand as self-consistent: the fix moves the yardstick (Cen), not the found
   presets.
2. Test a gentler fix on CPU with zero renders. The no-clip version boosts the highs by up to 13 dB, which is a hiss
   risk.
3. For new dry-guitar rows, report a clip-free re-score beside the coded one, at a few renders a part.

Declared with this outcome:
- the gentle-fix CPU check (plan 11f, `phase_scratch_tone_gentle`, coded, zero renders);
- the clip-free re-score beside `fs-notes` and `fs-codec` (plan 11g, `phase_scratch_tone_beside`, reported only, never
  deciding).

The measure step (`song_bank.measure`, `direc_check.eq_to`) is unchanged. `fs-tone` stays held.

### What the split does not say

- It says nothing by ear.
- It says nothing on a fix other than removing the clip; the gentler variants are priced in 11f, on CPU.
- Its share bracket rests on assumptions; only row (b)'s redo (12,351 + 940 renders) would measure it.
- It does not price the blur's non-tone parts on their own.
