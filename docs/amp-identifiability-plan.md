# Can the judge tell which Morgan amp made a sound?

Declared on 2026-10-04, before anything is computed. The user asked why the generator
does not choose among Morgan's amps (SW50R, PR12, AC20) as one more setting.

**Why ask this first.** Choosing the amp by measurement means searching each amp and
letting the judge pick the closest result. That only makes sense if the judge can tell
the amps apart when the presets differ. This is the "imitation test" of
`docs/research-full-plugin-estimation.md` (S3) for amp choice, run with the judge.

## Material

- **Renders.** The SW50R, PR12 and AC20 panels (`scripts/render_preset_panel.py`): every
  factory preset of each amp with time effects off, through each development part's DI.
  The SW50R and PR12 panels already exist; the AC20 panel is rendered for this.
- **What is offered.** Each amp's factory presets with no drive pedal and the amp's
  volume at most 0.75, the rule stage 0b used for PR12 (17 SW50R, 21 PR12 and 17 AC20
  presets), plus each amp's template with time effects off. So 17 candidates are drawn
  per amp.
- **Parts.** Development parts whose DI plays in at least half of 1.0–10 s (the K3
  rule; 30 parts).

## Procedure

For every part, every offered render is taken in turn as the target.
- **The distance.** Every other offered render of the same part is a candidate. The
  judge scores it against the target: `aligned_distance`, default bands, over 1.0–10 s,
  lag 0, since both are renders of the same DI.
- **The draws.** In each of 20 draws (seeded by the part's name), the same number of
  candidates is drawn from each amp, the smallest amp's count less one, with the
  target's own preset excluded. The guess is the amp of the closest candidate.
- **The score.** A target's accuracy is the share of draws whose guess is its amp.
  Chance is 1/3.

## What decides

The statistic is the median over bands of each band's mean accuracy, with an exact
one-sided band sign-flip test against 1/3.

| Outcome | Rule |
|---|---|
| **recoverable** | median ≥ 0.60 and p < 0.05 |
| **not recoverable** | median ≤ 0.45 |
| **partly** | anything else |

Reported, not deciding: per-amp accuracy, and the share of targets that could not be
scored because the judge refused a window.

## What follows

- **Recoverable.** With a DI, amp choice can be measured. The next step is a declared
  benchmark of "search each amp briefly, keep the judge's closest" against searching
  one amp, before the matcher changes.
- **Not recoverable.** The judge cannot tell the amps apart once the presets differ, so
  measured amp choice would be noise. Amp choice stays a reasoned decision (the
  generate skill's routing).
- **Partly.** It is reported with its per-amp accuracies, and the user decides.

## Limits, stated now

- **The validated range.** Stage 0b validated the judge only for clear differences
  between clean-to-crunch PR12 renders. Differences between amps, and SW50R and AC20
  renders, are outside that range, so any outcome here is provisional until a listening
  check covers them.
- **Renders only.** These are renders, not real amps. A real recording is never one of
  these amps, so this tests whether the judge separates the amps' characters, not
  whether it finds a real rig's amp.
- **The volume rule.** "Volume at most 0.75" is not the same amount of drive on each
  amp: SW50R has no master volume.
- **Product scope.** The product's song-only use has no DI, and the judge does not apply
  there.
