# Confirming the rebuilt-DI chooser on fresh material: results

Run 2026-10-10 as declared in [set4-confirmation-plan.md](set4-confirmation-plan.md),
with frozen inputs in the [manifest](set4-confirmation-manifest.json).
- **Timing:** approved at 17:07, manifest committed at 17:16:36, first render at 17:16:58;
  10,989 renders, scored at 18:14.
- **Independent re-check** (`tmp/confirmation-review.md`, local): every figure
  reproduced with separate code; 22 distances recomputed from audio; DIs rebuilt
  bit-identically; all manifest hashes matching; no later edits to code or plan.

**Declared outcome: confirmed.** On fresh clean and crunch parts, the chooser lands
closer to the record than the preset `generate` starts from, by the judge.

## Gates (clean and crunch parts, pooled over three amps, 13 bands)

Mean log ratio against the product's starting preset (the clean template on clean parts,
the shipped driven preset on crunch), with the band-clustered 90% interval:

| | mean | 90% interval | W / T / L | bands negative | one band left out |
|---|---|---|---|---|---|
| **oracle** (positive control) | −0.196 | −0.248 to −0.143 | 64 / 6 / 2 | 13 of 13 | −0.212 to −0.182 |
| **chooser** (3 kHz cut) | **−0.087** | **−0.157 to −0.017** | 49 / 5 / 18 | 9 of 13 | −0.107 to −0.066 |
| uncut rebuilt DI (report) | −0.100 | −0.181 to −0.019 | 53 / 3 / 16 | 10 of 13 | |

Every condition of "confirmed" holds:
- the oracle's interval is below 0;
- the chooser's interval is below 0;
- its mean stays negative with any one band left out;
- 9 of 13 bands are negative.

The same outcome under every declared sensitivity check: the fixed-level rule's presets
(−0.097), without set 4's flagged parts (−0.114), and judge v2 (−0.103).

## Reported, not gated

| stratum | chooser | oracle |
|---|---|---|
| clean (8 bands, 13 parts) | −0.123 (−0.220 to −0.027), 31 / 0 / 8 | −0.263 |
| crunch (5 bands, 7 + 4 parts) | −0.045 (−0.189 to +0.099), 18 / 5 / 10 | −0.116 |
| high-gain (4 bands, set 4) | **+0.318** (+0.061 to +0.574), 3 / 0 / 24 | −0.020 |

By amp (clean and crunch): PR12 −0.107, SW50R −0.121, AC20 −0.033.

## What it shows

- **The size is about 8% closer** (a 90% range of about 2–15%). That is 54% of the
  development effect, as the plan expected after halving for forks. The chooser now
  captures 45% of the oracle's gain, against 76% on development.
- **Clean parts carry it.** Crunch alone is −0.045, with an interval crossing zero.
  Set 4's crunch parts lose: 0 wins, 3 ties and 9 losses. They read high-gain on their
  crop, and 3 of 4 are flagged. The edge comes from the sets 1–2 parts (−0.124).
- **The clean template is a weak starting point.** A post-hoc check by the reviewer
  replaced it with a fixed clean preset chosen from other bands' distances. The clean edge
  shrinks to −0.049 (interval crossing zero). The pooled edge survives at −0.089
  (−0.138 to −0.039, 11 of 13 bands negative). So part of the clean gain is "any decent
  clean preset beats the template". That is a cheap product lesson in its own right.
- **On high-gain the chooser is clearly harmful** (+0.318, 24 of 27 worse). It picks
  low-drive presets. The oracle shows almost no room there (−0.020), so the shipped driven
  presets are already near the best the menu offers. This confirms the plan's split:
  high-gain songs keep the fixed driven preset.
- **The 3 kHz cut didn't help on fresh clean and crunch parts:** +0.013 against the
  uncut rebuild, not significant. It helps only on high-gain, where the chooser isn't
  used. The development "adoption" doesn't carry over; the cut can stay or go without
  consequence.

## Limits

- **By the judge, not by ear.** The judge is validated by one listener on clean-to-crunch
  PR12.
- **Isolated amp tracks.** The product's input is a song: separated stems and mixes are
  untested here.
- **Crunch alone, heavier crunch, and a well-chosen fixed clean preset are not
  established.**
- **Process gaps** (disclosed, none changes a number):
  - The plan promised a power re-estimate after gain classing in the approval request.
    Classing came after approval, and no re-estimate was made.
  - The ledgers were updated after the run, not before.
  - The plan's development figure for crunch used the leave-band-out constant rather
    than the shipped presets (−0.156 with the shipped ones).
  - Guitar-TECHS P1 is in training and P3 in the test: one part, which goes against the
    claim.

## Held-out use

- **Sets 1–2:** 17 sessions were cropped and 13 scored. They are recorded in
  `docs/validation-datasets.json` and stay held out for a later declared test, under
  their rule.
- **Set 4:** spent (`docs/validation-set4.json`).

## Next (as declared, plus what the result adds)

1. **Songs, not amp tracks.** Rebuild from separated stems and mixes, on development
   first, under a declared rule.
2. **Then the product:** for clean and mild-crunch songs, the audition page offers the
   chooser's top picks, marked experimental. High-gain songs keep the fixed driven
   preset.
3. **A fixed clean starting preset,** chosen on development by rule. It is cheap, and
   the reviewer's check suggests the template leaves easy gain on the table.
