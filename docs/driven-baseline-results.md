# A fixed driven preset per amp: the baseline for distorted songs

Roadmap step 0, next step 1 (2026-10-09). No new renders: this reads the distances
already stored by the set-3 development run and the set-3 reserved confirmation.

## The presets

The constants are chosen by K1's rule: the factory preset with the lowest median
half-A distance over all 33 set-3 development parts, on recording bands. They are
dry, as the panel renders them (`RULE_SET`): reverb, delay, tremolo, doubler and gate
off, the amp's spring reverb at 0, transpose 0. The installed presets are not all dry:
Wall Of Doom ships transposed down 5 semitones, with reverb, delay, spring and gate on.

- **SW50R:** Royce Whittaker / Wall Of Doom. Declared before the reserved test.
- **PR12:** Neural DSP / Vintage Metal. Declared before the reserved test.
- **AC20:** Charlie Robbins / Dirty Coil Rhythm, under the same rule. AC20 was not
  in the reserved test.

Under union bands the PR12 choice is Keyan Houshmand / Modern Metal (Pick Hard), about
2% ahead of Vintage Metal, which is third. Under recording bands Modern Metal is second,
0.3% behind. The skill uses the recording-band choice. SW50R and AC20 pick the same
preset under both.

## Against the clean template (template+R), average-guitar measure, half B

Values are the mean log ratio, with parts closer shown in brackets.

| amp | split | high gain | crunch | clean |
|---|---|---|---|---|
| SW50R | reserved (27 parts) | −0.98 (15 of 15) | −0.59 (8 of 8) | +0.38 (0 of 4) |
| PR12 | reserved (27 parts) | −0.78 (15 of 15) | −0.47 (8 of 8) | +0.44 (0 of 4) |
| SW50R | development (33) | −0.76 (17 of 17) | −0.50 (10 of 11) | +0.63 (0 of 5) |
| PR12 | development (33) | −0.58 (14 of 17) | −0.33 (10 of 11) | +0.54 (0 of 5) |
| AC20 | development (33) | −0.40 (15 of 17) | −0.34 (10 of 11) | +0.44 (0 of 5) |

- **On crunch and high-gain parts,** the reserved recordings agree with development for
  SW50R and PR12. The baseline is closer on all 23 parts.
  - **On average** it is about half the distance: a geometric mean ratio of 0.43 for SW50R
    and 0.51 for PR12.
  - **The weakest part** is still 4% (SW50R) and 8% (PR12) closer.
- **On clean parts** it is further every time, so it is for distorted songs only.
- **This reading of the reserved recordings is clean.** The constants were frozen
  before that test (commit 4ad02fa), and nothing here is tuned on it. Baseline against
  template was not one of that test's declared gates, so this is consistency with
  development, not a pass.

## What ships

- **`generate` (step 4)** starts a crunch or high-gain Morgan part from the chosen amp's
  driven baseline instead of the clean template.
  - The spec makes it dry first: transpose 0, spring 0, time effects, doubler and gate
    off.
  - It keeps the baseline's amp, drive, pedals, EQ and cab unless the research
    contradicts them.
- **The audition page** includes that dry baseline among the four.
- **The research** still chooses the amp, and which effects come back on.
- **An independent review** re-derived every number above
  (`tmp/driven-baseline-review.md`, local).

## Limits

- **Measured on isolated amp tracks of heavier set-3 sessions,** under the
  average-guitar measure. Heavy-tone listening has not been run.
- **Telling crunch from clean is left to the song research.** The gain classes here
  are the set's declared labels. The crop classifier disagrees with them on 6 of the 27
  reserved parts. Two parts declared crunch, which the classifier calls clean, were
  still closer.
- **Shipping before heavy-tone listening is a deliberate exception.** The confirmation
  plan asked for a listening check before product use; it hasn't run. The skill says
  so when it reports. The evidence is a large, consistent measured gain on every
  distorted part.
- **The DI-rebuilding chooser has not beaten these constants**
  ([held-out](set3-heldout-confirmation-results.md)). They are what the learned route
  must now beat.
