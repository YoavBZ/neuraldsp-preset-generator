# Part C's existing direct model on stage F, and the yardstick cap: results (2026-10-19)

Run under the [plan](direct-existing-plan.md) (reviewed; PR #231), no training. Development data
only; band-weighted estimates with 90% band-clustered t intervals, no pass/fail bars.
- **Code:** `learn/direct_existing.py`. **Data:** `~/ndsp-presets/learn/direct-existing/`
  (`parity.json`, `predictions.json`, `groups/`, `report.json`, `logs/`).
- **Renders: 852** (stage F 63 × 12, known-answer 16 × 6), as planned (cap 900), on 3 shards in
  about 25 minutes. The running total is about 302k.

## Headline

- **D_existing does not beat S on fresh full mixes.** D − S is **+0.033 [−0.053, +0.119]** (12
  bands, 5 better), leaning worse. On the 6 bands part C never trained on (the clean row) it is
  +0.010 [−0.143, +0.162]. Against arm A's recipe, D − H is +0.061 [−0.011, +0.133].
- **The raw-DI judge does not widen stage F's contrasts in general.** H − S is unchanged (paired
  change +0.003 [−0.016, +0.022]); D − S moves +0.018 [−0.036, +0.071]. Only the oracle arm XO,
  the one arm whose search heard the part's true DI, gains under the raw judge (XO − S −0.063
  [−0.103, −0.022]; the D − XO and XO − H changes are the same effect). Band SDs barely move (0.07–0.22 under both judges).
- **On the known-answer songs the measure DI does cap the truth.** Through the raw DI (the
  truth's own) the true preset reads a median 0.0001 against S's 3.6; through the measure DI it
  reads 2.26 against S's 4.34, a median 0.55 of S's distance (log truth − S −0.52 [−0.96, −0.08],
  3 bands). The convention takes the exact answer from "perfect" to "about half of S".

## Test 1: D_existing on stage F (126 directions, 21 parts, 12 bands)

| Contrast (measure-DI judge, held half) | All, 12 bands | No high bleed, 10 | F-song, 4 | Unseen by part C, 6 |
|---|---|---|---|---|
| **D − S (primary)** | **+0.033 [−0.053, +0.119]** | +0.030 [−0.071, +0.131] | +0.099 [−0.085, +0.283] | +0.010 [−0.143, +0.162] |
| D − H | +0.061 [−0.011, +0.133] | +0.077 [−0.007, +0.160] | +0.081 [−0.071, +0.233] | +0.051 [−0.075, +0.177] |
| D − XO | +0.021 [−0.093, +0.135] | +0.019 [−0.121, +0.160] | +0.126 [−0.051, +0.303] | +0.038 [−0.115, +0.190] |
| H − S (stored, for reference) | −0.028 [−0.064, +0.008] | −0.047 [−0.095, +0.001] | +0.018 [−0.032, +0.069] | −0.041 [−0.117, +0.034] |

- **Bands:** D − S is better on 5 of 12. Leaving one band out runs from +0.009 to +0.059.
- **Per amp:** AC20 +0.086, PR12 −0.007, SW50R +0.019 (all intervals contain 0). **Per class:**
  clean −0.042 [−0.147, +0.063] (7 bands), crunch +0.137 [−0.004, +0.278] (5 bands). Crunch is
  where it leans worse (its interval just reaches 0).
- **The confound** (stated in the plan before the run): part C trained on other DIs of 6 of these
  bands' sessions, whose backings hold the test part's amp track. That should flatter D, yet the
  all-bands row is no better than the unseen row. The leak did not help visibly, though with
  intervals about 0.3 wide a sizeable benefit is not ruled out.
- **The model's inputs were in range:** the parity check matched stored features (worst 99.998%
  of mel cells within one 0.5-dB step, LUFS within 2e-6); the inference gains ran −7.1 to +6.6 dB,
  and the mix and stem LUFS fell inside part C's val range. The seeds disagree by a median 0.062 in
  knob units. There were no refused answers under the measure judge.
- **Repeat check:** S's fresh measure-DI judge reproduced the stored one exactly on all 63 groups
  (largest |log| 0).

## Test 2: does the yardstick cap every result?

### Stage F, raw DI (di.wav at −22.9 LUFS, no average-guitar EQ)

One part, colour-me-red elecgtr03, is refused on half A under the raw DI for every arm (the
judge's DI-activity mask), so the raw contrasts use 123 directions. On those same 123 the measure
contrasts move by at most 0.005 from the 126-direction figures.

| Contrast | Measure judge | Raw judge | Paired change (raw − measure) | Band SD, measure → raw |
|---|---|---|---|---|
| D − S | +0.033 [−0.053, +0.119] | +0.048 [−0.052, +0.148] | +0.018 [−0.036, +0.071] | 0.166 → 0.193 |
| D − H | +0.061 [−0.011, +0.133] | +0.076 [−0.013, +0.165] | +0.015 [−0.042, +0.072] | 0.139 → 0.172 |
| D − XO | +0.021 [−0.093, +0.135] | +0.103 [−0.006, +0.212] | +0.080 [+0.018, +0.143] | 0.220 → 0.210 |
| H − S | −0.028 [−0.064, +0.008] | −0.028 [−0.065, +0.009] | +0.003 [−0.016, +0.022] | 0.069 → 0.071 |
| XO − S | +0.012 [−0.088, +0.112] | −0.055 [−0.157, +0.046] | −0.063 [−0.103, −0.022] | 0.193 → 0.195 |
| XO − H | +0.040 [−0.043, +0.123] | −0.027 [−0.120, +0.065] | −0.066 [−0.115, −0.016] | 0.161 → 0.178 |

- **Median held-half distances**, measure → raw: S 4.72 → 4.58, H 4.51 → 4.40, XO 4.53 → 4.09,
  D 4.90 → 4.50. Everything sits a little closer under the raw DI, but on a real amp record every
  arm still reads above 4, far from 0.
- **Reading.** On stage F the measure DI's EQ is not what squeezes the contrasts: H − S and D − S
  barely move, and the spread does not grow. What the raw judge does change is XO's standing:
  XO's search rendered through the part's own DI (measure-treated), and its answer fits the
  raw DI better than the rebuilt-DI arms' answers do (XO − S moves −0.063). So the DI convention
  matters for an arm in proportion to how much of the part's own DI that arm used.
  The floor at about 4 on stage F comes from elsewhere (a real amp against Morgan, bleed in the
  record, the judge itself), not from the DI EQ.

### Known-answer songs (16 sections, 4 songs, 3 bands; truth's amp; both halves)

| | Raw DI (the truth's own) | Measure DI (per section) |
|---|---|---|
| Truth, median distance | 0.0001 | 2.26 |
| S, median distance | 3.62 | 4.34 |
| Truth / S, median | 0.00005 | 0.55 |
| log(truth / S), band-weighted (floored at 0.01) | −5.78 [−6.40, −5.17] | −0.52 [−0.96, −0.08] |

- Through the measure DI S itself also reads further (4.34 against 3.62), so B1's "0.79 of S"
  (measure-DI truth over raw-DI S) becomes 0.55 when both are judged the same way. The fresh,
  primed truth renders matched B1's stored convention floor within 2.7e-4 (|log|), and S's raw
  judge matched B1's stored one within 5.4e-5.
- **Reading.** Where the record is a Morgan render, the measure DI caps the best possible answer
  at about half of S's distance: an exact answer judged through it reads only about −0.5 against S
  there. On stage F's real records it doesn't measurably narrow the
  differences between arms.

## What it implies

- **The existing direct model is not a shortcut:** fresh full mixes read a tie with S leaning
  worse (+0.033), and leans worse than arm A's recipe (+0.061 [−0.011, +0.133]), on the bands
  unseen by part C as well (+0.051 [−0.075, +0.177]). This is the model
  the draft direct-model plan expected to be confounded and set aside; it does not argue for or
  against D, which changes the data (band-clean) and the training mixes (realism).
- **Changing the judge's DI barely moves stage F's comparisons of rebuilt-DI arms.** The suspicion that the yardstick
  caps every result holds on the known-answer songs (an exact truth reads only about half of S),
  not on stage F, where the contrasts and spreads of the arms that search through a rebuilt DI or
  predict (H, D) are the same under both DIs; the arm that used the part's own DI (XO) reads better
  under the raw DI. For known-answer tests,
  judging through the truth's own DI (as B1's arms already are) is the uncapped reading; any arm
  that searches through the measure DI carries the cap into its answer.

## Checks

- Inputs: the context crop equals each crop's `mix.wav`; context and stem hashes matched at every
  group; the three model hashes matched at render time.
- Priming before every DI or amp change; the S repeat check exact on 63/63 groups; no STOP.
- Render processes started: 3 (PIDs 38737, 38758, 38775), all exited normally.

Audited 2026-10-19 by an independent agent, which recomputed every contrast, interval, band SD,
median, the known-answer figures and the render count from the raw group records with its own
script (all match); changes: crunch "leans worse" (its interval reaches 0); D − H "leans worse";
"clean bands" renamed the unseen bands; the stage F reading limited to the rebuilt-DI and predicted
arms, with XO's raw-DI gain named as one effect; the leak reading hedged.
