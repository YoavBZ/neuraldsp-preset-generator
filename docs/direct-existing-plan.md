# Part C's existing direct model on stage F, and the yardstick cap: plan

Declared 2026-10-19, before any render for it. Development data only; estimates with 90%
band-clustered intervals, no pass/fail bars. No training.
- **Code:** `learn/direct_existing.py`, tests `tests/test_direct_existing.py`.
- **Ledger:** `direct-existing` in [`dev-test-ledger.json`](dev-test-ledger.json).
- **Data:** `~/ndsp-presets/learn/direct-existing/`.

**Why now.** The [direct-model plan](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/direct-model-plan/docs/direct-model-plan.md)
(draft, branch `ml/direct-model-plan`) trains a band-clean D. Before paying for that, the user asked
for two cheap readings: how the model that already exists does on fresh full mixes, and whether
the judge's DI convention squeezes every result.

## Test 1: D_existing on stage F (primary)

- **D_existing** is part C's three 40k curve models (`pretrain-set/curve-models/40000-<seed>.pt`,
  seeds 20261042–44; [results](pretrain-set-results.md)), ensembled: continuous settings are the
  mean of the **highest-weight component of the pooled mixture** (each seed's weights divided by 3),
  not the mean of the seeds' means; switches by majority of the seeds (p > 0.5); mics by the argmax
  of the summed probabilities. The settings are S's preset for the amp and the part's class with
  the labelled dimensions replaced (`knob_ceiling.space`), as part C labels them.
- **Inputs, as part C built its val inputs:** stage F's stored full-mix context, cropped (asserted
  equal to the crop's `mix.wav`), and its stored htdemucs crop (`F/sep/htdemucs/crop`); both hashed
  at prediction and re-checked before each group's renders. One gain on both channels brings the
  10-s mix to the training median (`levels.json`'s `eval_mix_lufs_median`, −12.25 LUFS); the
  search half's arm B log-mel, quantised to the stored 0.5-dB grid; half A's first second masked;
  the conditioning holds the half's stem and mix LUFS after the gain, the amp and the part's class.
- **Parity (zero renders, before predicting):** 20 audit examples, rebuilt from their stored render
  audio and backing at the stored gains, go through the same path; at least 99% of mel cells within
  one 0.5-dB step of the stored features and the half LUFS within 0.01 LU, or nothing runs.
- **Rendered** once per direction through the part's measure DI, judged on the held half
  (`knob_ceiling.judge`, the part's `judge_lag`), exactly as arm A; paired with the stored S, H
  and XO (126 directions, 63 groups).
- **Primary:** D_existing − S, per direction log(d_D / d_S) on the held half, per part the mean,
  band-weighted, 90% band-clustered t interval over 12 bands (`arm_a_levers.effects`). Beside it:
  D − H, D − XO; rows no high bleed (direction rule), F-song, and **unseen by part C** (the 6
  stage F bands with no part C training section: Bernard Purdie Tribute All-Stars, Magician's
  Nephew, The Travelling Band, Turbosauro, Wall Of Death, Zeno); per amp and class. A refused
  answer scores as S.
- **The confound, stated before the result.** Part C trained on other DIs of stage F's own
  sessions (6 of the 12 bands), whose backings hold the stage F part's real amp track. That is why
  the draft plan rejected these models for the decision. The "unseen by part C" row (6 bands,
  8 parts) is the clean reading; the all-bands primary is the user's requested figure and leans
  optimistic by an unknown amount.
- **Secondary row on stage D: not run.** Of stage D's 14 bands only 2 (Timo And The Timezone,
  Turbosauro; 2 parts) are in neither part C's train nor val pool. That can't carry an interval.

## Test 2: does the yardstick cap every result?

The judge renders candidates through the **measure DI** (the part's DI EQ'd to the average-guitar
curve, then −22.9 LUFS); the record was made from the **raw DI**. If that mismatch puts a floor
under every candidate, all contrasts shrink.
- **Stage F:** in each group, after a priming render, S, H, XO and D_existing are rendered through
  the **raw DI** (the crop's `di.wav`, one gain to −22.9 LUFS, no EQ; the EQ is zero-phase, so the
  judge lag is unchanged) and judged on both halves against `reference.wav`. Reported: every Test 1
  contrast (and H − S, XO − S, XO − H) under each judge, the paired change (raw − measure) of each
  log ratio with its interval, each judge's band SD, and the median distances per arm.
- **Known-answer songs** ([B1](known-answer-b1-results.md); 4 songs, 3 bands, 16 sections): the
  truth and S (truth's amp, B1's S class) are rendered, each DI primed, through the **raw DI** (the
  truth's own DI, so the truth should read about 0) and through the per-section **measure DI**
  (B1's "convention floor"). Reported: medians of both, truth/S under each judge, and band-weighted
  log(truth/S) (distances floored at 0.01, as B1). The stored floor was rendered right after a DI
  change without priming, so its fresh value is compared with it, not used as a stop.
- **Reading, declared:** if the raw judge's contrasts are clearly wider (the paired change's
  interval away from 0, in the direction of the measure contrast) the measure DI caps results and
  the judge should change before more arms are scored; if they tie, the cap is not the DI EQ.

## Checks and stops

- **Priming:** one discarded render at S after the process start and every DI or amp change
  (each group: measure, then raw; each known-answer section: raw, then measure).
- **Repeat check, every group:** S's fresh measure-DI judge must reproduce the stored stage F S
  judge within 1e-3 (|log|) on both halves, or the run stops (`STOP.json`).
- Model files hashed at prediction and before rendering; inputs re-hashed per group; 31 GB disk
  guard; at most 3 render processes machine-wide (`local_objective.RENDERS`).

## Budget

| What | Renders |
|---|---|
| Stage F: 63 groups × (measure: priming, S, D × 2; raw: priming, S, H × 2, XO × 2, D × 2) | 693 |
| Known-answer: 16 sections × 2 DIs × (priming, S, truth) | 96 |
| **All** | **789** (cap 900) |

3 shards (the machine is idle), about 10 minutes; one reviewer, one auditor. The running total
before this test is about 301k renders.
