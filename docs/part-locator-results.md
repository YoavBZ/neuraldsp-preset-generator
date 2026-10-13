# Part locator: step 1 result — underpowered on development data

2026-10-13, under the [plan](part-locator-plan.md). Only the truth file was built (step 1). No
separation was run, nothing was rendered, and no held-out data was used. An independent
reviewer checked the code and counts (`tmp/part-locator-truth-review.md`, local), found two bugs
that changed counts, and reproduced the fixed numbers.

## In short

- **The decision measure can't be decided on development data.** The plan's primary set
  (in-scope targets that random windows don't already find, random Hit@3 above 0 and at most
  0.8) has **7 targets in 6 bands**. The declared floor is 15 targets in 10 bands, so the
  result is "underpowered", as the plan said it might be.
- **The role rule doesn't work.**
  - pYIN marks chord frames as voiced: 90–99.7% of frames on synthetic strummed chords,
    against 24% on noise.
  - So "mostly single notes" can't separate a lead from a rhythm part on a DI. Only 2 of 136
    parts were labelled rhythm (57 lead, 77 unlabelled).
  - In practice the rule reduced to "lead = plays in at most half the song".
- **Describing parts by clean or driven alone doesn't rescue it:** 6 primary targets in 6
  bands.
- **The cause is the material.** Most development songs have one guitar that plays nearly
  throughout, so any window finds it (random Hit@3 of about 1.0). The partial parts that make
  the product case hard rarely dominate their windows.

## Counts (`docs/part-locator-truth.json`)

- **Parts:** 136. 82 have a character label (48 clean, 34 driven).
- **Targets:** 19 with both labels. 10 are in scope and reachable, in 9 bands. 5 were dropped
  because no window contains them (random Hit@3 of 0).
- **Primary:** 7 targets in 6 bands; by fold, 3, 2 and 2.
- **Any outside upper bound** (every labelled in-scope guitar its own target, which breaks the
  plan's merge rule) reaches 21 targets in 13 bands. Six of those are almost never dominant.

## Fixed during review

- **dB envelopes were padded with 0 dB instead of silence.** 85 of 136 DIs are shorter than
  their song, and their activity was miscounted. They are now padded with −240 dB.
- **An electric piano was counted as a guitar** (Just Don't Talk). Names with "piano" are now
  excluded.
- **A part and its double now always share labels and form one target.**

## What follows

- **The locator isn't tested further on development data.** Separation isn't run for a
  measure that can't reach its bar.
- **Without a test, it can still be used qualitatively.** It offers three windows as clips,
  and the user picks by ear. That use would be labelled as untested.
- **A real test would need more material:**
  - songs with partial lead parts and annotated activity;
  - MedleyDB has these, but it is held out as set 6.
- **The Eden diagnosis stands:** the chosen window had buried guitar, and better windows
  existed.
