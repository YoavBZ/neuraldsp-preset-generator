# learn/: research code for predicting a preset from a song

Local research code. The product (`scripts/`, `skills/`) never imports it. The plans and
results it produced are in `docs/`; the living summary is `docs/ROADMAP.md`, step 0.

## The experimental approach

The reserved confirmation failed on both tested amps. This is a research pipeline,
not a validated product method. Development diagnostics now test where it breaks
before any further long training.

The [training-domain audit](../docs/research/di-domain-transfer-audit-2026-10-08.md)
independently supports Morgan-only wet supervision in the audited recipe. The next
[frozen-model P2 pilot](../docs/di-domain-pilot-plan.md) stopped at its mandatory
synthetic metric preflight before native audio access
([result](../docs/di-domain-pilot-results.md)). Independent numerical-cause review
precedes any separately declared retry of native recordings versus matched Morgan
renders with timing/recoverability controls. No
adaptation or long training is authorized by that source observation alone.

A song's guitar (the amp track, or a separated stem) goes through four steps:
1. `direc.py` rebuilds its DI at an average guitar's balance.
2. Each menu preset is rendered through the rebuilt DI.
3. The judge (`analysis/aligned.py`) picks the closest preset.
4. The pick is scored by the **average-guitar measure**: the take's true DI,
   re-equalised to the average balance, rendered through the preset, judged against
   the record. That measure was confirmed by listening.

## Modules, by experiment

| Module | Experiment | Plan → results |
|---|---|---|
| `pr12.py`, `di_pool.py`, `render_job.py`, `train.py`, `evaluate.py`, `diagnose.py` | POC settings model (knobs from audio) | `preset-model-poc-plan.md` → `-results.md` |
| `transfer.py`, `forward.py`, `oracle.py` | tone-curve oracle: a known curve is worth about 5% | follow-up section of `preset-model-poc-results.md` |
| `di_robustness.py`, `avg_yardstick.py` | does the judge choose well through a wrong DI | `di-robustness-plan.md` → `-results.md` |
| `build_avg_listening.py` | blind listening check of the average-guitar measure (phone pages) | `avg-measure-listening-plan.md` → `-results.md` |
| `direc.py`, `direc_check.py`, `render_pairs.py` | the DI-rebuilding network: data, training, the pre-overnight check | `di-recovery-plan.md` |
| `phase2.py` | the real-recordings test on clean PR12 (K1's 25 parts) | `di-recovery-results.md` |
| `phase2_set3.py`, `set3.py` | the same on set 3 (heavier tones); set 3's declaration and leakage guards | `di-recovery-plan.md` ("Phase 2 on set 3"), `validation-set3.md` |
| `set3_confirmation.py` | frozen inputs, exact constants and gates for the reserved set-3 test | `set3-heldout-confirmation-plan.md` (approved 2026-10-08) |
| `set3_diagnostic.py` | development positive control/menu headroom; independently verified, existing scores only | `set3-development-diagnostic-plan.md` → `-results.md` |
| `set3_mask_diagnostic.py` | fixed-panel activity-proxy check, independently verified: rescues one refusal but no control gain; closed | `set3-mask-diagnostic-plan.md` → `-results.md` |
| `set3_rank_calibration.py` | nested band-excluded prior/score blend, independently verified; criteria missed, fixed blend closed | `set3-rank-calibration-plan.md` → `-results.md` |
| `set3_cross_amp_diagnostic.py` | pooled existing amp menus, independently verified; criteria missed, no selector follow-up | `set3-cross-amp-diagnostic-plan.md` → `-results.md` |
| `di_domain_pilot.py`, `run_di_domain_pilot.py` | twelve native P2 pairs versus matched Morgan renders, frozen checkpoint; metric preflight failed before audio | `di-domain-pilot-plan.md` → `-results.md`, fixed `di-domain-pilot-inputs.json` |
| `di_domain_metric_probe.py` | synthetic window-coefficient interventions pass, independently verified; no audio/model access | `di-domain-metric-probe-plan.md` → `-results.md` |
| `run_di_domain_pilot_v2.py` | independently verified QC stop, only 3/12 pairs accepted; no render/inference; closed/inconclusive | `di-domain-pilot-v2-plan.md` → `-results.md` |
| `rerank.py` | DI-free reranker: log-mel, PANNs CNN14 | `rerank-plan.md` |
| `render_crossed.py` | crossed renders for our own guitar tone encoder | `tone-encoder-plan.md` |

## Where things live (local only, never committed)

All under `~/ndsp-presets/learn/`:
- `poc/`: POC renders (18,843 PR12 clips), caches, models, eval, and the stems of sets
  1–2.
- `direc/`:
  - DI-network caches (`cache` for PR12; `cache-sw50r`, `cache-ac20`);
  - fold models in `models-final/fold{0..3}.pt`, and the set-3 network in
    `models-set3/`;
  - Phase 2 renders and results (`phase2/`, `phase2-set3/`).
  - The reserved confirmation uses `phase2-set3-heldout/`, separate from development.
    `phase2_set3.py --split held_out` requires an approved, committed input manifest;
    it fails before opening audio when that declaration or any frozen input differs.
- `di-robust/`: the DI-robustness renders.
- `rerank/`: reranker features and results.
- `set3/stems/`: set 3's development stems.
- `sep2/`: separator-upgrade outputs.

The listening check is in `~/ndsp-presets/listening/avg-measure/`. Set 3's audio is in
`~/ndsp-presets/references/datasets-set3` and `validation-crops-set3`.

## Reserved confirmation

Execution completed 2026-10-08: 4,320 renders, 27 reserved parts, six bands and both
declared timing analyses. Neither amp passes; independent numerical/audio
verification agrees, including 1,321 distinct audio measurements
([results](../docs/set3-heldout-confirmation-results.md)). Do not retrain or tune on
this split. The commands below record the frozen procedure, not a new test to run.

The user approved the plan on 2026-10-08. `set3_confirmation.py prepare --manifest PATH`
reads development scores and metadata only, and writes `approved: false`. Constants
are factory-only, chosen separately under recording and union bands. Commit the
approved declaration and frozen manifest before any held-out run.

Render with `phase2_set3.py render --split held_out --amps sw50r pr12 --kinds measure net
--confirmation-manifest PATH`. Score with the same split, amps and manifest, first
with `--lag-mode waveform`, then `--lag-mode onset`. The onset analysis keeps the
network's primary selections and substitutes only the four already declared timing
disagreements. Both analyses and both band sets must pass. These commands require
the same CPU torch environment (`~/ndsp-presets/tools/learn-venv/bin/python`) for
preparation, rendering and scoring; its versions are part of the manifest. No new
training is required. Retain failures and
have an independent reviewer rederive the final result before acting on it.
Failed scoring attempts archive the previous outputs in `score-history/` and remove
the current verdict. After a failed onset attempt, rerun waveform scoring before onset
scoring so the primary inputs are restored under the same frozen procedure.

## Disk

The project data grew by about 180 GB during this work (2026-10-06/07). To keep it in
bounds:
- **Phase 2 renders** are stored as level-normalised 24-bit FLAC, about 4× smaller.
  Distances agree with float WAV to 1e-7; `learn/compress_renders.py` converts old
  renders.
- **Training caches** (uncompressed int16 `input.npy`/`di.npy`) are deleted after
  training, then rebuilt from the FLAC pairs with `learn.direc cache-pairs`. The PR12
  cache stays: the fold averages live in it.
- **The DI-robustness renders** were deleted (regenerable); their results are kept.

## Environments

- `.venv` (Python 3.14): rendering and the judge.
- `~/ndsp-presets/tools/learn-venv` (Python 3.9, torch 2.8 + pyloudnorm): CPU inference
  and scoring.
- `~/ndsp-presets/tools/demucs-venv` (torch 2.14, MPS): network training. Run it
  read-only; don't install into it.
- `rerank-venv`, `sep2-venv`, `sep-venv`: per-experiment.

## Operational traps (measured)

- **Launch long jobs with `zsh -c 'setopt no_bg_nice; nohup … &'`.** zsh's BG_NICE made
  MPS training about 4× slower.
- **Never run two MPS training processes at once.** The second one diverges. Test on
  CPU with `DIREC_DEVICE=cpu`.
- **On MPS, `clip_grad_norm_` gives NaN, and LSTMs diverge.** `direc.py` clips by hand,
  recovers after scattered or persistent non-finite steps, and stage scripts retry.
- **A rebuilt DI is aligned with its recording,** so the judge takes `lag=-52`.
- **Reused render processes cost about 0 licence-daemon ports.** About 10 per new
  process. Watch the daemon with `learn.render_job.daemon()`.
