# Fine-structure C′ (DI-recovery experiment 4): results so far (2026-10-16)

Run under the [plan](di-fine-structure-plan.md) and its amendment 1, on fold 3 only. Since
2026-10-16 the readings are descriptive, under the user's rule (no pass/fail bars). The
artefacts are in [audits/arm-a-2026-10-16](audits/arm-a-2026-10-16/README.md).

## Step 0

- **0b, diagnostics:**
  - The idempotence check had a latency-shift bug, fixed and re-run: 9 of 12 cells pass the lag
    check.
  - The phase swap: true phase is positive on 6 of 9, true magnitude on 9 of 9.
- **0c, the DAC round trip (a two-point test):** through the codec, the margin is 0.168 against
  the true DI's 0.188 (bar 0.141), and crest is kept. The E1′ route stays open.
- **0d, calibration:** the share rule set the weights to short 1, peak 0.5, gap 0.07, phase 7.
- **0e, capacity:** overfit on 8 crops, C′'s own loss reaches the fine-structure targets and
  about 21 dB waveform SNR, the same as the new loss terms. The output stage can represent fine
  structure, so arm 1e (a full-rate head) wasn't added.

## The arms (fold 3 fine-tunes of C′, 5,150 steps)

Evaluation-only metrics on fold 3's 96 validation crops; errors against the true DI.

| | Validation ratio | Gap level | 3–8 kHz error | 10-ms crest error |
|---|---|---|---|---|
| C′ | 0.517 | −4.0 | −7.4 | −0.25 |
| 1z (C′'s loss, fine-tuned) | 0.508 | −4.1 | −6.8 | −0.27 |
| 1a (short-window, peak, gap) | 0.517 | −15.5 | −4.7 | −0.08 |
| 1b (1a + phase) | 0.514 | −14.5 | −4.8 | −0.12 |

- **1a and 1b do what they were built for:** about 11 dB less gap fill and 2.6 dB less treble
  deficit, with no breakage.
- **1c (adversarial)** was stopped twice for memory and then stalled at 0% CPU. It doesn't fit
  this machine as set up.

## The known-target control on fold 3's 4 informative cells

| | Cells closing ≥ 50% of the gap | Mean shortfall |
|---|---|---|
| The true DI | 4 | −0.043 |
| C′ | 2 | +0.201 |
| 1z | 2 | +0.191 |
| 1a | 1 | +0.164 |
| 1b | 1 | +0.197 |

- **Per cell,** 1a against 1z is +0.149, −0.120, −0.017 and −0.122. Its mean of −0.028 is inside
  the noise (SE about 0.065).
- **Better fine structure doesn't make the rebuild steer the search better here.**

## Later evidence ([arm A levers](arm-a-levers-results.md))

- **On real songs, 1z, 1a, 1b and their ensemble rank the menu no better than C′** (0.75–0.80).
- **Near S, every net's local ranking is about −0.12,** no better than chance.
- So the limit is a systematic local bias, not fine structure. The fold 0–2 fine-tunes were
  stopped as not needed.
- A research round on a locally accurate objective is running. Its first point: the local
  comparison changed the DI, the reference, the lag and the mask at once, so the cause isn't
  isolated yet.

## Renders

About 2.6k, from step 0 and the controls of 1a, 1b and 1z.
