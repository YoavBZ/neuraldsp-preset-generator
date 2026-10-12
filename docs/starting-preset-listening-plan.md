# Do the starting presets sound closer by ear? Listening plan

Declared 2026-10-13, before any trial is built; revised after an independent review.
Roadmap step 6: the starting presets `generate` ships were chosen and checked by the
judge only; none has been heard against what `generate` used before, or against each
other on the choice that costs most (a clean part given the crunch start).

## The question

Through the part's own notes, does the listener hear the option `generate` now
prefers as closer to the recorded guitar? Three blocks, all made dry with the amp's
dry recipe:
- **C, clean start against the old template** (clean parts, PR12 only, the template's
  amp): Royally Ambient against `samples/Example_Clean_PR12.xml`. Prefers the clean
  start.
- **X, clean start against crunch start** (clean parts, the amp rotating PR12, SW50R,
  AC20 in part order): the misroute the routing check found costly. Prefers the clean
  start.
- **K, crunch start against the driven start** `generate` used for crunch parts before
  2026-10-10 (crunch parts, amps rotating): prefers the crunch start.

## Trials

**Parts.** Development parts only (scored in `generate-routing-results.json`; nothing
held out, nothing from sets 5 or 6), screened first: the DI plays in at least 90% of
half B, and the DI's energy below 200 Hz is at most 25% (the heavy check lost trials to
broken low notes). Among those, ordered by DI activity in half B, highest first, ties
by slug in ASCII order:
- C: one clean part per band (up to 10);
- X: a second clean part from each of the first 6 bands (in the same order) that have
  one, not counting a double-track of the C part (Magilla ElecGtr1dt); 6 trials;
- K: up to two crunch parts per band, up to 10, each on the next amp in the rotation.
  If fewer than 8 survive the screen, K is report only and the primary pools C and X.
Control and practice parts are taken from parts not used in C, X or K. The list is
written to `docs/starting-preset-listening-parts.json` before any judge margin for
these trials is computed or seen.

**Format** (the heavy and average-guitar checks'): half B (5.5–10 s) of the reference
(the part's recorded amp track) and of two renders of its measfix DI, aligned at the
judge's lag; R, A, B played twice, each replayable alone; every clip at −20 LUFS
integrated with a shared true-peak guard, 10-ms fades, mono, AAC 160 kbps in one phone
page. The question: which of A and B is closer **in tone** to the reference: A, B or
"?". The page names no preset, amp, class or part.

**Controls and checks:**
- **Practice (1, unscored, first):** marked as practice.
- **Hidden reference (2):** one in each sitting; one option is the reference itself;
  missing it voids that sitting.
- **Reversed taste (1):** a spare crunch part, crunch start against clean start, where
  the judge clearly prefers the heavier option (margin over 0.15 on the stored scores),
  so a listener who simply prefers less distortion does not pass every control.
  Reported, not voiding. Its stored margins are looked at for that part only. If no
  spare crunch part passes the screen with that margin, the first K part on another
  amp with such a margin is used; if none, the control is dropped and that is reported.
- **Repeats (3):** three main trials drawn with a seeded generator, the originals in
  sitting 1 and the repeats in sitting 2, with A and B swapped; excluded from the
  tests; consistency reported.
- The preferred option is A on half the trials of each block (rounded), drawn; no part
  twice in a row; two sittings of about 16 to 17 trials each (about 33 in all).
- The page asks the listener to stop and report a clip that sounds broken or silent; a
  technically failed trial is presented once more; unanswered trials are left out.

**Key and answers.** Renders reproduce the stored judge distances first (the arm's
start against its stored `flat|measfix` score, |Δ log| < 0.005), or the build stops.
The key (in a private folder the scorer alone reads) holds the judge's log ratio for
each trial on the exact clip played; its SHA-256 is committed before the first
sitting. The answer sheet's SHA-256 is committed before the key is read, and the scorer
refuses any other key or sheet.

## Readings and decision

**Primary (decides): pooled over C, X and K,** the share of decided main trials where
the listener chose the preferred option, one-sided sign test.
- **Heard** at p < 0.05, provided C and K pooled lean the preferred way (at least 50%),
  so that X, the largest difference, cannot carry it alone: `generate` step 4 records
  the per-block counts ("the ear agreed with the judge on n of N parts in each block,
  in-sample, one listener"), naming a block as agreeing only if its own share leans
  the preferred way.
- **Not heard** (the other option chosen at p < 0.05): reported, and step 4 says the ear
  disagreed in-sample; no preset changes, because the judge's held-out results stand.
- Otherwise **undecided**: reported; no change.
- Void if a hidden reference is missed.

**Reported:** each block's share and sign test; ear–judge agreement overall and split
at a judge margin of 0.15; how often the lighter-gain option was chosen, over all
trials; the reversed-taste control; the repeats' consistency; results by band.

**Power, stated now.** With 26 decided main trials, "heard" needs 18 (p 0.038). If the
ear agrees on 70% of trials, that is reached about 63% of the time (88% at the 77% the
ear showed on clear pairs in the listening validation); with 20 decided (many "?"),
15 are needed and the chance at 70% is about 42%. A single block (6 to 12
trials) can show only a near-unanimous preference. A loss is not realistically
declarable at this size.

## Limits

The starting presets were chosen by the judge on some of these development parts, so
this asks whether the ear agrees with the judge where the judge chose, not whether the
presets generalise. Block C covers PR12 only. One listener.

## Built (2026-10-12, before any sitting)

28 trials (21 main: C 8, X 5, K 8 after the screen; 3 repeats, 2 hidden references,
1 reversed-taste control, 1 practice), renders reproduced the stored scores (worst
|Δ log| 0.00007). Key SHA-256:
`6bacfd75e2a03f04e53c9837b10b37cc98c6569afa78c79b04bc2a47dd018cbc`. With 21 main
trials the power is lower than planned: "heard" needs 16 of 21 decided (p 0.013) or
15 of 20 (p 0.021), about 40% at 70% agreement.
