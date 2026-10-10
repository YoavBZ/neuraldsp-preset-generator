# Listening check H: on heavy tones, which part of the judge does the ear follow?

Declared 2026-10-10, before any trial is built or answered. It is the user's decision
"build the heavy-tone listening check" in
[closeness-review-2026-10-10.md](closeness-review-2026-10-10.md) (finding 8; design
from the perception review's section 4). Built, run and scored by
`learn/build_heavy_listening.py`, which reuses the audio, sheet and phone code of
[avg-measure-listening-plan.md](avg-measure-listening-plan.md). Nothing is rendered:
every option is an existing render.

## The two questions

1. **Texture against balance.** The judge is the sum of a *tonal* part (the long-term
   spectrum) and a *temporal* part (how each frame differs from it: drive texture,
   envelope, compression). On "the network's pick against the fixed driven preset"
   they point opposite ways and cancel. Which one does the ear follow?
2. **Does the judge hold on heavy SW50R and AC20?** Its only listening evidence is one
   listener on clean-to-crunch PR12.

## Material

- **Parts:** set 3's development parts of gain class crunch or high-gain (28), never
  held-out ones.
  - **Dropped:** parts where the judge scores fewer than 16 bands. There it cannot hear
    treble (finding 1), so its tonal part does not measure balance. Judge v2 refuses the
    same parts. This drops the three Ill Fate parts (7–12 bands) and leaves 25.
- **Options:** the stored `measfix` renders: each part's measure DI at a fixed −22.9
  LUFS (the user's decision) through every menu preset of PR12, SW50R and AC20
  (`learn/set3_gap_split.py`).
- **Half B only:** 5.5–10 s of each 10-s crop, recording bands.
- **R:** the isolated amp track (`validation-crops-set3/<part>/reference.wav`).
- **Driven presets:** factory presets that `listening_check.gain_class` does not call
  clean, and not made for bass.

## The judge's three numbers

- `aligned_distance` on half B: the `measfix` render against R, with the `measfix` DI,
  at the part's `judge_lag_samples` and `render_latency=52`.
- It returns the distance and its tonal and temporal parts. All three are compared as
  log ratios (A over B).
- Computed once for every menu preset and cached in
  `~/ndsp-presets/listening/heavy/work/components.json`. The builder stops unless every
  distance equals the stored `measfix_B` one (gap-split `distances.json`) within 1e-6
  log.

## Trials (36, in two sittings of 18)

- **Block 1, texture against balance (16).**
  - **Pairs:** a chooser's pick against its amp's fixed driven preset (Vintage Metal,
    Wall Of Doom, Dirty Coil Rhythm). The choosers are the low-pass pick and the network
    pick (half-A argmin of `v2-eval/lp3k/distances.json`, `recording|<amp>|lp3k_A` and
    `net_A`) and the true-DI oracle at the fixed level (half-A argmin of `measfix_A`).
    Menu pairs of driven presets are used only if these give fewer than 16.
  - **Qualifies when** the tonal and temporal log ratios have opposite signs and each
    is at least 0.10.
  - **The long-term (tonal-closer) option is A on 8.**
- **Block 2, clear heavy pairs (10).** Two driven presets on SW50R or AC20 (5 each;
  at least 4 each was the reviewer's bar). The judge separates them by more than 0.15
  log, and they do not qualify for block 1. The judge's option is A on 5.
- **Block 3, small differences (4).** Two driven presets, judge margin 0.03–0.08, not
  block-1 pairs, any amp. The judge's option is A on 2. Report only.
- **Reliability (6).**
  - **3 hidden references,** one per amp: one option is R itself, the other the amp's
    fixed driven preset.
  - **3 repeats:** three block-1 trials, drawn by the seed, played again with A and B
    swapped. Each original is in sitting 1, its repeat in sitting 2.
- **The choice** (deterministic, seed 20261010):
  - At most 2 trials per part and 6 per band over the whole test, and no pair twice.
  - Blocks are filled in order 1, 2, 3, then the hidden references.
  - Amps take turns (round-robin); block 2 takes 5 SW50R and 5 AC20.
  - Within an amp: a guitar-exposed part first (the DI plays in ≥ 0.9 of half B), then
    for block 1 the clearer conflict (the larger of the smaller of the two log ratios),
    and for blocks 2 and 3 the seed's order. Hidden-reference parts are any part still
    under its caps, in the seed's order.
  - If any block falls short, the builder stops; the bar is not lowered.
- **The draw.** Trial order and the A/B sides come from the system's randomness and are
  written only to the private key. Sittings: sitting 1 has 9 block-1 trials (with the
  3 originals), 5 block-2, 2 block-3 and 2 hidden references; sitting 2 has 7, 5, 2, 1
  and the 3 repeats. No part plays twice in a row.

## Audio

As the average-guitar check:

- **Excerpts.** R is half B of the amp track. A and B are aligned to it as the judge
  aligns them: recording[t] matches render[t − lag]. The render already lags the DI by
  its 52 samples.
- **Levels.** A 10-ms raised-cosine fade at each edge. Then one static gain per clip to
  the same EBU R128 integrated loudness, −20 LUFS. That target is lowered by one shared
  amount if any clip would peak above −1 dBTP. So the ear compares tone, not level.
- **Each trial** is R, A, B, then again (about 30 s), with R, A and B also alone.

## Blinding and hashes

- **The listener's folder** (`~/ndsp-presets/listening/heavy/listen/`) holds only
  numbered trial files and the phone pages.
- **The key** (`private/trials.json`) holds the pairs, the judge's three numbers, the
  blocks and the A/B sides. Nobody opens it before every answer is in. Its sha256 is
  recorded here, and the scorer refuses any other key:
  `0f0a5c3805f2e8721e372cd50f3286d9fc0fef65039771f2164211d09ffce061`
- **The answer sheet** is the two phone answer lines as sent. `check --answers SHEET`
  confirms it answers every trial and prints its sha256. That hash is committed in
  `docs/heavy-listening-answers.sha256` before `score --answers SHEET` runs. The
  scorer records the sheet's hash before it reads the key.

## Taking it (phone)

    .venv/bin/python -m learn.build_heavy_listening phone

- One self-contained page per sitting, `listen/sitting-1-phone.html` and
  `sitting-2-phone.html`, built from the listener's folder alone.
- Every clip is mono AAC at 160 kbps. The question: "Which of A and B is closer in tone
  to the Reference?" Tap A or B; this is forced choice, as in the earlier checks.
- The page keeps answers across reloads and shows an answer line
  (`Sitting 1: 1A 2B …`) to copy and send. The same headphones and level throughout,
  with a break between the sittings.

## Outcomes, and what each changes

- **Void** if 2 or more of the 3 hidden references are missed, or fewer than 2 of the 3
  repeats are answered the same way (the same preset both times). Nothing else is read.
- **Block 1** (one-sided binomial p 0.038 at 12 of 16):
  - **The ear sides with the tonal option on ≥ 12/16:** the judge over-weights frame
    texture on heavy tones.
    - Re-score the set-3 held-out confirmation and the "fixed preset is unbeaten" claim
      with a tonal-weighted measure as primary; that verdict may reverse.
    - Withdraw the claim, not the network.
    - Candidates for a heavy-tone judge: tonal plus a down-weighted temporal part.
  - **The ear sides with the temporal option on ≥ 12/16:** the judge's verdict stands,
    now validated on the deciding axis. The next lever is gain and compression
    estimation, not EQ: the picks are under-driven. Next work: a gain prior, or picking
    within the driven class only.
  - **5–11 either way:** neither part dominates for this ear. Keep the judge's sum, and
    treat aggregate differences under 0.10 between the network and the constant as
    ties.
- **Block 2:**
  - **≥ 8/10 agree with the judge** (p 0.055): its validation extends to clear
    differences on heavy SW50R and AC20.
  - **≤ 5/10:** stop treating the judge as ground truth on heavy material until it is
    redesigned.
  - **6–7:** inconclusive; the judge stays unvalidated on these amps.
- **Block 3, report only:** at or near chance (≤ 3 of 4) means single-pair differences
  under about 0.08 should not drive a decision; only means over many cases count, which
  is current practice.
- **Also reported:** block 1 against the judge's own pick, block 1 by amp and by
  sitting, block 2 by amp, and how often A was chosen.
- The hearing-weighted judge (v2) is adopted only if this check agrees with it. That
  comparison is a separate step, after scoring.

## Where this differs from the reviewer's design

- **No sure/guess tap:** the established phone pages are forced choice with no
  confidence tap, so block 3 is read on agreement alone.
- **Clips at −20 LUFS** as proposed, but the scored DI level is the fixed −22.9 LUFS
  (`measfix`), not the session level the reviewer's numbers used.
- **The three Ill Fate parts are dropped** (fewer than 16 scored bands).
- **The hidden references' other option** is the fixed driven preset, so a miss is
  never a near tie.
- **Order of work:** the builder's counts, and once its selected pairs with their log
  ratios, were looked at while it was written, before this plan; that is how the Ill
  Fate exclusion was noticed. No audio was built and no answer exists.

## What was built (2026-10-10; counts only, no pair is named)

- **Parts:** 25 of the 28 driven development parts (three dropped under 16 bands). Every
  part's DI plays in all of half B, so exposure never decided.
- **The judge's numbers:** recomputed for every menu preset; each distance equals the
  stored `measfix_B` one.
- **Qualifying pairs:**
  - block 1 from the choosers' picks: 34 (PR12 17, SW50R 11, AC20 6), on 13 parts in 7
    bands. All 16 block-1 trials came from these; no menu pair was needed;
  - block 2: 7,848 menu pairs; block 3: 1,816.
- **Trials by block and amp:**
  - block 1: 16 (PR12 6, SW50R 6, AC20 4; AC20 had qualifying picks on few parts, and
    the part and band caps bound);
  - block 2: 10 (SW50R 5, AC20 5);
  - block 3: 4 (PR12 1, SW50R 2, AC20 1);
  - hidden references: 3 (one per amp); repeats: 3.
- **Sittings:** 9 block-1, 5 block-2, 2 block-3 and 2 hidden references in sitting 1;
  7, 5, 2, 1 and the 3 repeats in sitting 2.
- **Audio:** every clip at −20.0 LUFS (no clip needed the target lowered), excerpts 4.5 s.
- **Phone pages** (`listen/sitting-1-phone.html`, `sitting-2-phone.html`): 21.0 and
  20.9 MB. Page sha256 as built: sitting 1
  fa18fa5deb6e5e967f3382fbd2b25d444737cfffd9a90aaaa902723e4416b534, sitting 2
  e0d081cbce9fb463cc4ab27a32dc2179698351d496500a5023f579f590648fa7.
