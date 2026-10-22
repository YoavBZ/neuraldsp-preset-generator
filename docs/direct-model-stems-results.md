# The direct model with realistic stems: steps 3 and 4 results (2026-10-22)

Run under the [plan](direct-model-stems-plan.md) with amendments 2 and 5–7. The
[pilot results](direct-model-stems-pilot-results.md) come first. Development data only.
- **Step 4 ran under a user override of a GATE STOP**
  ([amendment 7](direct-model-stems-plan.md#amendment-7-2026-10-22-step-4-runs-despite-gate-stop-user-override)).
  The sound gate read GATE STOP. The user chose to run step 4 anyway, with its design, rule and
  early stops unchanged. Every step 4 number below carries that label.
- **Code:** `learn/direct_stems.py`, `learn/direct_sound_gate.py`.
- **Data:** `~/ndsp-presets/learn/direct-stems/`: `full/readout.json`, `gate/report.json`,
  `step4/report.json`, `logs/` (`readout.log`, `gate-report.log`, `step4-report.log`,
  `train-full-*.log`, `xl-stem-*.log`).

Every effect is a log ratio or an E difference, band-weighted, with a 90% band-clustered t
interval. Negative means D is better.

## Headline

- **Step 4 reads `STEP4 NOT SHOWN` (run under a user override of a GATE STOP).** D − S on stage
  F is **−0.034 [−0.103, +0.034]**, 12 bands, 5 better and 7 worse. The interval contains 0, so
  the declared reading is: not shown at this power; stop and revisit with the user.
- **The new direct model clearly beats the old one (run under a user override of a GATE STOP).**
  D − D_existing is **−0.067 [−0.113, −0.021]**, 16 of 21 parts better, mostly on crunch.
- **It is indistinguishable from arm A's search (run under a user override of a GATE STOP).**
  D − H is −0.006 [−0.062, +0.050] and D − M +0.011 [−0.040, +0.062]. Arm A costs about 55
  renders per direction; D needs none. This is not a shown equivalence: the intervals allow D to
  be up to about 0.05–0.06 worse.
- **Step 3: the gate read GATE STOP.** On R_in, D's preset sounds nominally closer to the true
  preset than the constant's, −0.1538 [−0.3360, +0.0284], but the interval reaches above 0. The
  gate's power was about 46%. D sounds clearly closer than the old recipe D0 (−0.1266
  [−0.1864, −0.0669]).

## What ran

- **Build (amendment 2):** X-LANCE gtr_mss (`xlance_g`) stems for V_sep (1,720), the pilot
  (5,995) and the rest (15,309), with 0 refused. The rest's 15,309 is the mix stage's 15,311
  less its 2 refusals. The two workers (one MPS, one CPU) met in each part, so one example per
  part was separated twice: 1,721, 5,996 and 15,310 runs.
- **Step 3's training:** D_stem and D0, 3 seeds each, on MPS. Every run trained on 20,306
  examples with 998 for early stopping, and dropped the same 7 refusals.

| Run | Seed 20261042: best / run epochs, minutes | Seed 20261043 | Seed 20261044 |
|---|---|---|---|
| D_stem | 30 / 35, 66.9 | 31 / 36, 68.8 | **38 / 40**, 77.2 |
| D0 | 35 / 40, 73.4 | 25 / 30, 55.0 | 20 / 25, 45.9 |

- **GPU time:** about 6.5 h for the six runs.
- **Epoch cap:** D_stem seed 20261044 reached its best at epoch 38 of 40, so it may be
  under-trained.
- **Renders:** the gate recorded 5,628 judged renders (truth, constant, D and D0 on R_in's 1,407
  examples), plus priming. Step 4 used 321 (the cap was 400).

## Step 3's readout (amendment 5; descriptive)

D's answer is each knob's mixture median, averaged over 3 seeds × 2 halves and pulled toward the
per-class constant. E leaves out the right cab's knobs when that cab is off.

| Masked E, D − constant | Value |
|---|---|
| R_in (1,407 examples, 4 bands) | −0.0159 [−0.0363, +0.0046] |
| R_out (672, 4 bands) | −0.0110 [−0.0315, +0.0094] |
| V_dev (1,720, 5 bands) | −0.0143 [−0.0223, −0.0063] |

- **The readout matters.** The old top-component readout (as first declared: seed-averaged,
  unmasked) reads +0.012 [−0.021, +0.045] on R_in, worse than the constant.
- **This E check is descriptive.** It reads STOP. Under amendment 5 it does not decide; the sound
  gate does.
- **Beside it, on R_in:** D − D0 −0.0087 [−0.0202, +0.0028]. D0 − constant −0.0071 [−0.0165,
  +0.0022].

## The sound gate (amendment 6): GATE STOP

On R_in, each arm's preset was rendered and judged against the true preset's render. The rule
reads log(d_D / d_constant), averaged over the two halves.

| Contrast (log d) | Value | Closer share |
|---|---|---|
| **D − constant** (deciding) | **−0.1538 [−0.3360, +0.0284]** | 0.638 |
| D0 − constant | −0.0275 [−0.1668, +0.1118] | 0.520 |
| D − D0 | −0.1266 [−0.1864, −0.0669] | 0.609 |

- **Per band, D − constant:** John Morgan Kimock −0.283, Swatkins −0.287, Adam Buckley −0.061,
  Dark Ride +0.016. Two bands gain a lot and two barely move, so the 4-band interval is wide.
- **Power:** about 46% for the observed effect.
- **Unscored:** 9 examples, because the truth render was silent. 1,398 examples were scored.
- **By class:** clean −0.157, crunch −0.149; both intervals reach above 0.

## Step 4 on stage F (run under a user override of a GATE STOP)

126 directions (21 parts, 12 bands). Log ratio of held-half judge distances, per part averaged
over amps and halves.

| Contrast | Value | Bands better / worse | Parts better / worse |
|---|---|---|---|
| **D − S** (primary) | **−0.034 [−0.103, +0.034]** | 5 / 7 | 11 / 10 |
| D − D0 (declared secondary) | −0.006 [−0.032, +0.019] | 6 / 6 | 10 / 11 |
| D − H | −0.006 [−0.062, +0.050] | 7 / 5 | 11 / 10 |
| D − M | +0.011 [−0.040, +0.062] | 6 / 6 | 7 / 14 |
| D − D_existing | −0.067 [−0.113, −0.021] | 8 / 4 | 16 / 5 |
| D − XO | −0.046 [−0.133, +0.041] | 6 / 6 | 8 / 13 |
| D − YT | +0.060 [+0.006, +0.113] | 4 / 8 | 5 / 16 |
| D0 − S | −0.028 [−0.098, +0.042] | 6 / 6 | 12 / 9 |

- **By class, D − S:** clean −0.071 [−0.183, +0.042] (7 bands); crunch +0.016 [−0.068, +0.101]
  (5 bands).
- **By class, D − D_existing:** crunch −0.121 [−0.201, −0.041], clean −0.029 [−0.084, +0.027].
- **D − S's other rows:** leave one band out −0.049 to −0.008; part-weighted −0.010 [−0.062,
  +0.043]; no high bleed −0.023; unseen by part C −0.055; without the MUSDB18 songs −0.042. All
  intervals contain 0.
- **YT** (arm A's search through a perfectly separated stem) stays better than D.
- **The known-answer row** (knob error on 3 bands, no interval): D 0.158, D0 0.149, D_existing
  0.152, S 0.183. Every model sits below S; D is not below D0 or D_existing.
- **X-LANCE's three stage F failure parts, D − S:** She's Gone +0.009, Colour Me Red elecgtr02
  −0.205, elecgtr03 −0.015.
- **Power:** band SD 0.133, so the 90% half-width is 0.069 and the effect found with 80% power is
  about 0.10. The power for the observed −0.034 is about 21%.
- **Checks:** 321 renders, priming once per (part, amp) group (63), the 6 repeat groups exact
  (0.0), no refused answer, every check passed.

## What this means

- **The direct model clearly improved over the old one** (−0.067 against D_existing, run under a
  user override of a GATE STOP). The fix's own reading, D − D0, is
  only −0.006 on stage F, so D0 (part C's old recipe, retrained on the same examples and read the
  same way) likely shares most of that gain there. On R_in's sound gate D is clearly ahead of D0
  (−0.1266).
- **It is indistinguishable from arm A's search** (run under a user override of a GATE STOP),
  which costs about 55 renders per direction, while D needs none. That is not shown equivalence:
  the intervals allow D to be up to about 0.05–0.06 worse than H or M.
- **Neither route has yet clearly beaten S on stage F.** Clean leans better, crunch leans worse.
  At this power a real gain of about 0.03 would read as a tie.

## Next (the user decides)

*2026-10-22 evening:* both plans below are approved and merged, and the order is in
[ROADMAP](ROADMAP.md) step 0: the data review and cleaning first. These results were read on all
parts, before the trusted-data rule; the cleaning plan's step 1 re-reads them on trusted data.

- **Every control:** the coverage plan ([#266](https://github.com/YoavBZ/neuraldsp-preset-generator/pull/266),
  draft).
- **Real mixes:** the real-mix plan ([#267](https://github.com/YoavBZ/neuraldsp-preset-generator/pull/267),
  draft).
- **More power:** more bands, if the user wants this result tightened.
