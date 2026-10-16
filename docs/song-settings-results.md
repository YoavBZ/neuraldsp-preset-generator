# Song-settings comparison: results (ML plan step 3, 2026-10-16)

Run under the [plan](song-settings-plan.md), its amendments 1–4, its recorded outcome and the
readout readings declared before any score. The readout comes from `learn/song_readout.py report`,
written to `~/ndsp-presets/learn/song-settings/readout/report.json`.
- **Scope:** 24 parts, 14 bands, 3 amps, both directions. 142 of 144 directions were used; 2 were
  dropped for every arm because arm A's renders were refused there.
- **Independent audits:**
  - the known-target control
    ([artefacts](audits/song-settings-control-2026-10-15/README.md));
  - the whole of arm B (`readout/audit/`, 95 extra renders): features, labels, scoring and the
    readout rules.

  The scoring was re-rendered on sample cells and reproduces within 0.0005.

All figures are held-half log ratios against S (the starting preset), band-weighted with 90%
band-clustered intervals. Negative means closer to the record.

| | Against S | Bands better | Status |
|---|---|---|---|
| **K_S** (a knob search with the true DI: the ceiling, not a product option) | −0.269 [−0.342, −0.196] | 14 / 14 | reference |
| **Arm A** (search through C′'s rebuilt DI) | −0.078 [−0.157, +0.002] | 11 / 14 | failed: its known-target control fails; scores descriptive |
| **Arm B** (a settings model trained on 10k renders) | +0.035 [−0.038, +0.108] | 6 / 14 | failed |
| Arm C | — | — | not run (arm A's control fails) |

## Arm A: failed by its control; the rebuild is the bottleneck

- **The control:** with the true DI the search closes at least half the gap on 9 of 9 informative
  cells. Through C′'s rebuild it does so on 3 of 9. Audited; no bug.
- **Its scores, descriptive only:**
  - against S: −0.078, about 29% of the true-DI search's gain (rule 1 needs 40%);
  - against the C′ menu pick: −0.062 [−0.112, −0.012], 11 of 14 bands.

  So even the current rebuild, searched, lands closer than ranking the menu through it.
- **The DI-recovery track** follows from this. Its results so far:
  - [the ladder](rank-margin-ladder-results.md): C′'s error is fine structure;
  - [the separator screen](separator-screen-results.md): separation halves the margin but rarely
    flips it.

  Experiment 4, a fine-structure retrain, is running.

## Arm B: fails, for a real reason

- **Positive control (planted settings, known answer):** it fails on all 4 folds.
  - Gap closed ≥ 50% on 27–35 of 53–63 units; the rule needs two-thirds.
  - It is closer than the bank median on 39–48 of those units, which would pass.
- **On the real cells:** +0.035 against S, and no better than a song-blind constant (−0.009 [−0.069,
  +0.052]).
- **The shuffled-input control passes** (−0.074, 12 of 14), so the model does use its input.
- **Not data-limited:** the full bank is not better than the half bank (+0.017 [−0.017, +0.052]),
  so the reading is "failed", not "undecided".
- **Why, per the audit:**
  - The pipeline is correct:
    - feature parity between bank, control and evaluation;
    - 0 label mismatches over 28,813 values;
    - encoding consistent;
    - no collapse onto S.
  - The model is weak even on its own kind of data. On held-out bank renders, its mean knob error
    is 0.22–0.23, against 0.23–0.25 for always predicting the median.
    - Per-setting correlations are 0.1–0.6.
    - Mic accuracy is about 0.4.
    - It shrinks toward the middle: prediction spread is about a third of label spread.
- **A control defect, found by the audit:** the planted targets were rendered through the raw DI,
  not the measure DI as the bank was, so they weren't reachable.
  - Re-rendered through the measure DI (17 targets), the control fails harder: 1 of 33 units close
    half the gap.
  - The stored control flatters the model. **No fix-and-re-run is used,** because it would only
    confirm the failure.

## The readout

The readout code reads "blocked: the positive control fails; fix and re-run allowed". With the
audit's finding above, the step is read as **no arm passed** (step 6, row 4). The plan's row-4
re-run of arm A on amp tracks is moot: the rebuild already fails on clean renders.

So the next steps are the user's call. The ML session proposes:
1. **Continue the DI-recovery track.** It is the only route that showed a gain here (arm A,
   descriptively). Experiment 4's fold-3 arms are training.
2. **Rethink arm B instead of scaling it.** Predicting each knob on its own from sound is
   ill-posed: many settings sound alike, and the model regresses to the middle.
   - **A different target:** train against a sound-space loss (rendered or proxy distance) rather
     than knob error.
   - **A different role:** use B as a proposer for a short list that a search refines. That is
     arm C's idea, and it needs a working rebuild or another way to score.

   This needs a research round before any plan.

## Stated limits

- Development data only, one take per part.
- Arm A's figures are descriptive, and they used the old judge lag (−52). The lag moves margins
  by at most 0.003–0.03.
- Arm B's model is one architecture and one recipe (an MDN on log-mel, 10k renders).
