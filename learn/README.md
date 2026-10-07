# learn/: research code for predicting a preset from a song

Local research code. The product (`scripts/`, `skills/`) never imports it. The plans and
results it produced are in `docs/`; the living summary is `docs/ROADMAP.md`, step 0.

## The approach today

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
- `di-robust/`: the DI-robustness renders.
- `rerank/`: reranker features and results.
- `set3/stems/`: set 3's development stems.
- `sep2/`: separator-upgrade outputs.

The listening check is in `~/ndsp-presets/listening/avg-measure/`. Set 3's audio is in
`~/ndsp-presets/references/datasets-set3` and `validation-crops-set3`.

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
