# C′ for every fold: plan (ML plan 2026-10, step 1)

Declared 2026-10-14, before any training. Revised the same day after an independent review
(`tmp/cprime-folds-plan-review.md`, local): approved with changes, all folded in below. It is
step 1 of
[`research/ml-plan-2026-10.md`](research/ml-plan-2026-10.md), user decision 1. No renders.

## Why

C′, the corrected DI-rebuilding network ([residual-di-results.md](residual-di-results.md)),
exists only for K3 fold 2 (`~/ndsp-presets/learn/direc/models-cprime/fold2.pt`). Step 3's route-1
arms (A and C) must rebuild each part's DI with a network that never trained on its band. With
fold 2 alone, only 7 of the 24 step-3 parts are leak-free.

## What

Train C′ three more times, leaving out K3 fold 0, 1 and 3 in turn. **C′'s exact recipe**, as run
for fold 2 and its seeds (`~/ndsp-presets/learn/direc/train_cprime_seed1.sh`):
- **the interpreter:** `~/ndsp-presets/tools/demucs-venv` (torch 2.14), on MPS, with the spectral
  loss on the CPU, as `learn/direc.py` does;
- **the data:** `--cache cache --extra-cache cache-sw50r cache-ac20`, the fold's own frozen
  average (`average-fold{f}.npy`, already on disk), bleed from the training folds' backings;
- **seed 0;**
- **stage 1:** `fit --steps 5150` at 3e-4, into `models-cprime-1h-f{f}`;
- **stage 2:** `fit --steps 23100 --resume <stage 1> --lr 3e-4 --lr-end 2e-5`, into
  `models-cprime-f{f}`.

Those are the same commands with only `--fold` and the output folders changed. Nothing in
`learn/direc.py` changes.

**Before training,** the SW50R and AC20 pair caches (about 35 GB) are rebuilt from the stored
FLACs (`rebuild_caches.sh`: `learn.direc cache-pairs`).
- The stale `CACHES_REBUILT` marker (from 2026-10-11) is deleted first.
- After the rebuild:
  - each `meta.json` must be unchanged (sha256 recorded before);
  - `input.npy` and `di.npy` must have 14,965 (SW50R) and 14,998 (AC20) rows.
- When all three folds are done, only `input.npy` and `di.npy` are deleted, as before.

No new renders.

**The preflight** (`learn/cprime_folds.py preflight --fold f`) runs before each fold and stops
it on any mismatch. It recounts the split exactly as `fit` does:
- the expected train / validation / bleed counts are fold 0 34,792 / 14,014 / 27, fold 1
  38,188 / 10,618 / 29, and fold 3 38,204 / 10,602 / 33;
- fold 2 reproduces C′'s own log (38,709 / 10,097 / 37);
- the only band outside the K3 folds is Guitar-TECHS P1, which trains every fold and is never
  evaluated.

The folds come from `k3_folds()`, which reads the checkout's catalogue at run time. So the run
is pinned to a fixed checkout and commit, recorded in its log.

**Fold 2's network is protected:** `models-cprime/fold2.pt` is copied to
`models-cprime/fold2.pt.bak`, and the runner never deletes a `models-cprime*` folder.

## Pre-checks (from the ML plan)

- **Free disk ≥ 66 GB before the rebuild.**
  - Checked 2026-10-14: 67.3 GiB (70.6 GB), after deleting E1's code cache and checkpoints, with
    the user's approval. The deletion is logged in `~/ndsp-presets/CLEANUP-2026-10-13.md`.
  - The rebuild writes 34.5 GB, leaving about 36 GB.
  - The ML plan's "nothing else stored while this runs" becomes a guard: step 2's renders stop
    writing if free space falls below 31 GB.
- **The PR12 cache `~/ndsp-presets/learn/direc/cache` exists** (20 GB). Checked.
- **No other MPS job.**

## Schedule

- **The folds run one after another:** 0, 1, then 3.
- **The speed:** the solo C′ seeds ran at 1.19–1.27 steps/s (fold 2's 1.0 shared the GPU), so
  about 6.5 h per fold alone, slower while step 2 renders on the CPU. Measured, not from any log
  line that spans a pause. The ML plan said about 15 h in all: a dated deviation.
- **The 03:00–04:15 window, read as "no CPU or GPU work"** (a deviation from "schedule each fold
  around it"):
  - **The pause:** a watchdog sends SIGSTOP at 03:00 to every `learn.direc fit` and step-2
    render process, polling throughout the window so a stage boundary can't start one inside it.
    It sends SIGCONT at 04:15, then again at 04:20 as a fail-safe.
  - **Why pause, not stop:** the recipe stays unchanged. Resuming from a checkpoint would restart
    the cosine schedule (`--resume` loads the weights only).
  - The watchdog logs every action, and the Mac is kept awake with `caffeinate`.

## Checks

1. **Sanity, as it trains:**
   - no NaN loss;
   - the recovery counter (`fold f recovery`) at most 3;
   - the stage-2 validation ratio to the input-as-DI baseline at or below 0.65.

   A NaN or more than 3 recoveries stops the fold, and it is investigated before a re-run (same
   seed). Step 23,100 itself is never validated (the last validation is at step 23,000).
2. **The declared network check** (replaces the ML plan's proposed menu-pick check; see the
   note below):
   - **The measure:** the mean, over set 3's 5 usable clean and crunch stem parts, of the
     1–3 kHz coherence between the stem-rebuilt DI and the true DI (`learn/cprime_folds.py
     check`). No fold's network trained on any set-3 band, so the same 5 parts are leak-free for
     all four folds: a paired comparison.
   - **The reference, measured before any new fold exists:** fold 2's three seeds score 0.1360,
     0.1326 and 0.1343.
   - **The rule (one-sided):** a new fold fails if it is below the seeds' minimum by more than
     max(the seeds' range, 0.02): below **0.1126**. A fold that does better never fails.
   - **If one fails:** arms A and C stop until it is investigated.
   - The 12-part version was dropped before any new fold existed. 7 of its parts are high-gain,
     where distortion leaves even the amp track's coherence at about 0.03, so it couldn't tell
     networks apart.
3. **Report-only:**
   - each fold's last validation loss, and its ratio to the input-as-DI baseline (fold 2: 62.27
     / 110.57 = 0.563; seed 1, the noise reference: 0.554);
   - inside step 3, the ML plan's menu-pick figure per fold.

**Why check 2 changed.** The ML plan's proposed check compared each fold's menu-pick mean, on
3–5 bands of *different* parts, against fold 2's, within 0.05, and it was two-sided. The review
found:
- it would fire on noise: seed noise alone is about 0.05 per band;
- it would also stop the arms when a fold did *better*.

The coherence check is paired, one-sided, calibrated by fold 2's own seeds, and needs no renders.

## Ledger

Entered in `docs/dev-test-ledger.json` (`cprime-folds`) before training: the K3 bands left out
per fold, the expected counts, the P1 note, and check 2's rule and reference.

## Outputs

- `~/ndsp-presets/learn/direc/models-cprime-f{0,1,3}/fold{f}.pt`, beside fold 2's.
- The logs `fit-cprime-f{f}-1h.log` and `fit-cprime-f{f}.log`.
- The results, in `docs/cprime-folds-results.md`.

## Amendment (2026-10-15): no 03:00–04:15 pause

The "nothing runs 03:00–04:15" rule (ML plan section 5) has no reason behind it. It began as a
one-night request from the ML session on 2026-10-10, to keep the product session's renders clear
of an evaluation. The product session then carried it into its plans, and the ML plan copied it
from there. No backup or system job uses that window. The user asked for the pause to be dropped
if it wasn't required, so the watchdog is stopped, and from now on jobs run through the night.
Fold 0 was paused once (2026-10-15, 03:00–04:15), with no effect on the recipe.
