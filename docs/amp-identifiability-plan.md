# Can the judge tell which Morgan amp made a sound?

Declared on 2026-10-04, before anything is computed. The user asked why the generator
does not choose among Morgan's amps (SW50R, PR12, AC20) as one more setting.

**Why ask this first.** Choosing the amp by measurement means searching each amp and
letting the judge pick the closest result. A precondition is that the judge can tell
the amps apart across presets: preset retrieval, with no refit. It is not the S3
imitation test of `docs/research/round-2-full-plugin-estimation.md`. S3 refits each target on
every amp from distortion-matched starts and decides with another DI; this check does
none of that.

## Material

- **Renders.** The SW50R, PR12 and AC20 panels (`scripts/render_preset_panel.py`): every
  factory preset of each amp with time effects off, through each development part's DI.
  The SW50R and PR12 panels already exist; the AC20 panel is rendered for this.
- **What is offered.** Each amp's factory presets with no drive pedal and the amp's
  volume at most 0.75 (the rule stage 0b used for PR12), with the amp and cab sections
  on, plus each amp's template with time effects off: 18 SW50R, 21 PR12 and 17 AC20, in
  23 families.
- **Families.** A preset's family is its artist folder; the three templates are one
  family. A factory preset whose amp controls and input gain equal its amp's
  template's joins the templates. This compares every amp control except the master
  level and the spring reverb (off in every render). The master also adds some drive on
  SW50R; grouping TriTone Tremolo (master 0.62 against the template's 0.30) errs toward
  lower accuracy. Two
  presets join that way: SW50R "TriTone Tremolo" and AC20 "Default". Neural DSP's own
  presets are each their own family.
- **Parts.** Development parts whose DI plays in at least half of 1.0–10 s (the K3
  rule; 30 parts).

## Procedure

For every part, every offered render is taken in turn as the target.
- **The distance.** Every offered render of the same part outside the target's family
  is a candidate. The family is left out because presets within one share settings:
  two SW50R presets render identically once tremolo is off, and the templates match
  outside the amp. The judge scores each candidate against the target:
  `aligned_distance`, default bands, over 1.0–10 s, lag 0, since both are renders of
  the same DI.
- **The draws.** In each of 200 draws (seeded by the part's name), k candidates are
  drawn from each amp, k being the smallest of the three remaining pools (at least 3,
  or the target is not scored). The guess is the amp of the closest candidate.
- **The score.** A target's accuracy is the share of draws whose guess is its amp.
  Chance is 1/3.

## What decides

The statistic is the median over bands of each band's mean accuracy, with an exact
one-sided band sign-flip test against 1/3.

| Outcome | Rule |
|---|---|
| **recoverable** | median ≥ 0.60 and p < 0.05, and each of the three amps' mean accuracy ≥ 0.50 |
| **no evidence across presets** | median ≤ 0.45 and p ≥ 0.05 |
| **partly** | anything else |

Exact ties between amps are broken at random. An amp's mean accuracy is over its
target-and-part rows, not over bands; one band holds 8 of the 30 parts. The
sign-flip test generalises over performances only: the same presets appear in every
band.

**Reported, not deciding:**
- the 3×3 confusion matrix and each amp's accuracy;
- the targets not scored;
- each target's compressor state and volume;
- the same reading on the judge's temporal part alone, which is less open to
  differences an EQ could imitate;
- the same reading on compressor-on presets only. The compressor is on in 19 of 21
  PR12, 12 of 17 AC20 and 11 of 18 SW50R offered presets, and could separate the sets
  instead of the amps.

## What follows

- **Recoverable.** The precondition holds. The next step is a declared benchmark of
  "search each amp briefly, keep the judge's closest" against searching one amp, with
  a refit, before the matcher changes.
- **No evidence across presets.** The judge does not tell the amps apart across
  presets. That does not justify S3 or the benchmark yet, but it does not show that
  searching each amp fails either, since a search removes the variation between
  presets. Amp choice stays a reasoned decision (the generate skill's routing) until
  a refit test says otherwise.
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
  amp. Only SW50R has a master (`sw50rLevel`, 0.17–0.90 here); PR12 and AC20 have
  none. The offered sets differ in drive:
  - PR12's volumes reach 0.62–0.68, near its knee;
  - AC20 includes "Mid-Gain Drive" (0.71);
  - SW50R's volumes stay at or below 0.615;
  - input gain ranges from −20 to +1.8 dB on PR12, −20 to 0 on SW50R, and down to
    −5.7 on AC20.

  The judge hears drive, so drive could separate the sets rather than the amps'
  character. Each target's volume, input gain and master are in the rows.
- **Product scope.** The product's song-only use has no DI, and the judge does not apply
  there.
