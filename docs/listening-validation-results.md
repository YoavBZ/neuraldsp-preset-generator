# Stage 0b: the judge is validated for clear, clean-to-crunch differences

Scored as declared in `docs/listening-validation-plan.md` (as amended before any
answer) by `scripts/score_listening_validation.py`. Its output is
`docs/listening-validation-score.json`.

- **The answer sheet.** The listener gave the 30 answers in chat on 2026-10-04, in two
  sittings. They are transcribed with the listener's notes in
  `docs/listening-validation-answers.md`. Its sha256 (`261dca6b…`) was committed and
  pushed (`docs/listening-validation-answers.sha256`) before any key was read.
- **The trial list.** It is `docs/listening-validation-trials.json`, with sha256
  `4a0c547b…`, the one the plan records.
- **Independent check.** A fresh-context reviewer re-scored every trial from the keys,
  the order and the trial list without the scorer. Every count matched, and so did
  every file and audio hash.

## Outcome: validated

| | |
|---|---|
| Hidden references picked | 3 of 3 (the test is valid) |
| Test pairs decided | 22 of 24 (two "?") |
| **The judge agrees** | **17 of 22 (77%), one-sided p 0.0085** |
| Union band set | 17 of 22 (it predicts the judge's option on all 24) |
| ALM | 18 of 22 (it differs from the judge on one pair, which the listener sided with) |
| v3c | 12 of 22 (chance) |
| Where the judge and v3c disagree | the listener sided with the judge on 7 of 9 (two-sided p 0.18); v3c predicts the judge's option on 14 of 24 |
| Repeats | 2 answered the same; 1 had a "?" the first time |
| Reweighted to the pool's mix | 0.771 |

The rule for "validated" is at least 70% agreement with p < 0.05, which at 22 decided
pairs means 16 or more. 17 meets it; the one-sided 95% upper bound is 0.906.

## How firm it is

- **The margin is thin but holds up.**
  - With one answer flipped, it still passes (16 of 22, p 0.026); with two, it is
    inconclusive.
  - If both "?" had gone against the judge, it would still pass (17 of 24, p 0.032).
  - Leaving out any one part or any one band, it still passes: at worst 15 of 20
    (p 0.021) by share, and 13 of 17 (p 0.025, without the Dom McLennon band) by p.
- **Nothing dominates.**
  - At most 2 pairs come from one part.
  - Agreement is 8 of 11 on Cambridge parts and 9 of 11 on Telefunken parts.
  - The listener answered A 11 times and B 11 times. Agreement was 8 of 10 where the
    judge's option was A, and 9 of 12 where it was B.
- **Agreement barely depends on the judge's margin.**
  - The smaller-margin half (|log ratio| 0.151–0.228) agrees on 8 of 11, the larger
    half (0.236–0.426) on 9 of 11.
  - Of the 5 misses, 3 (trials 3, 7, 15) were pairs where all four measures predicted
    the option the listener rejected. One of them, trial 7, has the second-largest
    margin.
- **The sittings:** sitting 2 agreed on 10 of 11, sitting 1 on 7 of 11. The
  difference is not significant.

## The listener's notes

- **Trial 8.** "though both 8A and 8B don't have enough drive". The listener still
  chose an option, the judge's. The amp track can be more driven than any clean-to-crunch option.
- **Trial 9.** A "?": "Sounds like A has more reverb similar to the reference but B has
  high frequency notes similar to the reference". It is not scored. A was the template with
  time effects off, so the "reverb" was not the delay or reverb blocks. Its repeat
  (trial 22) went with the judge, but repeats are not scored.
- **Trial 29**, a hidden reference. "I could hear the backing from the guitar mic." The
  bleed alone gives the reference away, so this check is weaker than it looks. Blind
  Spots was not among the plan's bleed exclusions, and it touches no scored pair: its
  only test pair was the "?".

## Per trial

`*` marks pairs where the judge and v3c disagree (repeats 19 and 28 repeat such pairs). The listener's and the judge's
options are given with where each was played.

| # | kind | part | options | listener | judge | \|log ratio\| | agrees |
|---|---|---|---|---|---|---|---|
| 1 | test* | Quicksand ElecGtr1 | Lush Clean Wet / Spacey Clean | Spacey (A) | Spacey (A) | 0.203 | yes |
| 2 | hidden ref | Sculptor's Request GTR 2 | reference / Huge Ambient Wash | ref (A) | – | – | picked |
| 3 | test | Russian Cream GTR 2 | Lush Clean Wet / Pedal Steel | Pedal Steel (A) | Lush (B) | 0.236 | no |
| 4 | test* | Farthest Step | Jangly Combo Clean / template+R | template+R (B) | template+R (B) | 0.156 | yes |
| 5 | test | Quicksand ElecGtr2 | Cleanish Rhythm / Jangly Combo Clean | Cleanish (A) | Cleanish (A) | 0.352 | yes |
| 6 | hidden ref | Passing Ships ElecGtr2 | reference / It Can Sparkle | ref (A) | – | – | picked |
| 7 | test | Drag Me Down ElecGtr4 | Out of this World / Crystal Clean | OotW (B) | Crystal (A) | 0.390 | no |
| 8 | test | Today's The Day ElecGtr07 | Royally Ambient / Overdriven Tremolo | OD Trem (B) | OD Trem (B) | 0.294 | yes |
| 9 | test | Blind Spots | Thump Tone / template+R | ? | template+R (A) | 0.172 | – |
| 10 | test* | It Was My Fault ElecGtr3 | Thump Tone / Wide And Lucious | ? | Thump (A) | 0.203 | – |
| 11 | test | Prodigal ElecGtr5 | Thump Tone / Double Stop Funk | DSF (A) | DSF (A) | 0.239 | yes |
| 12 | test* | Quicksand ElecGtr2 | Royally Ambient / Time To Chime | Chime (B) | Royally (A) | 0.157 | no |
| 13 | test | Signs ElecGtr2 | Lush Clean Wet / Clean-ish Ambient Solo | Clean-ish (B) | Clean-ish (B) | 0.315 | yes |
| 14 | test | Signs ElecGtr2 | BC Guitar Chords / Wet Room | Wet Room (B) | Wet Room (B) | 0.152 | yes |
| 15 | test | It Was My Fault ElecGtr3 | Ambient Clean / Time To Chime | Ambient (A) | Chime (B) | 0.151 | no |
| 16 | test* | Drag Me Down ElecGtr4 | Cleanish Rhythm / Wet Room | Cleanish (B) | Cleanish (B) | 0.267 | yes |
| 17 | test* | Sculptor's Request GTR 2 | Out of this World / Heartbreaker | OotW (B) | OotW (B) | 0.290 | yes |
| 18 | test* | Gym Hours GTR 2 | Royally Ambient / Overdriven Tremolo | Royally (B) | Royally (B) | 0.178 | yes |
| 19 | repeat of 4 | Farthest Step | as 4 | template+R (A) | template+R (A) | 0.156 | same as 4 |
| 20 | test* | Fragments | Double Stop Funk / Wet Room | DSF (A) | Wet Room (B) | 0.222 | no |
| 21 | test | Farthest Step | BC Guitar Chords / Spacey Clean | BC (A) | BC (A) | 0.201 | yes |
| 22 | repeat of 9 | Blind Spots | as 9 | template+R (B) | template+R (B) | 0.172 | 9 was ? |
| 23 | test | First Offering GTR 1 | Heartbreaker / Clean-ish Ambient Solo | Clean-ish (A) | Clean-ish (A) | 0.158 | yes |
| 24 | test | First Offering GTR 2 | Pedal Steel / Spacey Clean | Pedal Steel (B) | Pedal Steel (B) | 0.269 | yes |
| 25 | test* | She's Gone | Bass Chords / Heartbreaker | Bass Chords (B) | Bass Chords (B) | 0.228 | yes |
| 26 | test | Honey | BC Guitar Chords / template+R | BC (A) | BC (A) | 0.426 | yes |
| 27 | test | She's Gone | Out of this World / Wide And Lucious | W&L (A) | W&L (A) | 0.379 | yes |
| 28 | repeat of 1 | Quicksand ElecGtr1 | as 1 | Spacey (A) | Spacey (A) | 0.203 | same as 1 |
| 29 | hidden ref | Blind Spots | reference / BC Guitar Chords | ref (B) | – | – | picked |
| 30 | test* | Passing Ships ElecGtr6 | Cleanish Rhythm / Crystal Clean | Crystal (A) | Crystal (A) | 0.221 | yes |

## What it licenses (the plan's Decision)

- **What the judge covers:** clear differences, |log ratio| > 0.150 (about 16%),
  between clean-to-crunch PR12 renders, those with no drive pedal and a PR12 volume of
  0.75 or less.
- **Reported beside it, never pooled:** the earlier 16 post hoc trials, on which the
  judge agreed on 12 of the 14 it scored (`docs/measuring-closeness.md`).
- **What it does not cover:**
  - High-gain material, other amps, and differences below the cut rest on an
    unvalidated range.
  - The test does not separate the judge from ALM or the judge's union band set.
- **The kill tests.** The plan's validated branch recomputes them under the judge's
  conditions with both band sets (`docs/kill-test-k3-plan.md`, "Under the judge"). They
  were already computed that way (`docs/kill-test-results.md`, Verdict). K3's union reading fails, so the
  verdict stays **"not passed"**.
- **Model work:**
  - Whether to proceed anyway is the user's decision.
  - Condition 1 of `docs/kill-test-results.md` ("What follows") is now met only on
    the validated range.
  - The kill tests' own renders are SW50R presets, mostly high-gain, outside that range.
  - A POC gain below the cut, on high-gain material, or on another amp cannot by
    itself open a further gate.
