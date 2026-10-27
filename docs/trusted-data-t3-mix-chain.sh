#!/bin/zsh
# ROADMAP step (a), D_F5mix: F5's every-control model fed the mix (declared 2026-10-27: docs/trusted-data-t0-design.md,
# "D_F5mix: the every-control model fed the mix"; ledger trusted-data-t3, amendment 3 "D_F5mix (ROADMAP (a))").
# Written, NOT launched. PENDING THE USER'S YES (training longer than minutes). Run it only with that yes, from the
# main checkout once the PR that adds learn/trusted_data_t3_mix.py is merged.
# Arms: D_F5mix (the mix, unaugmented) and D_F5-noaug (the stem, unaugmented); the input contrast is between them.
# Cost: 4 training runs on MPS, about 7-14 min each (F5's D_F5 runs took 8.5 and 6.8 min), about 30-55 min in all;
# fit and R0 a few minutes of CPU, zero renders (R0 is descriptive: no stop rule). V-real: 165 renders (33 (part, amp)
# groups x (1 priming at S + 2 arms x 2 directions)), a few minutes on 3 processes; isolate=True, 0.25 s trimmed, at
# most 3 render processes machine-wide (every vreal-render waits for a slot), the 31 GB disk guard. Zero separations.
# Outputs only under trusted-data/t3-mix/; t0/, t2/ and t3/ are only read. T3's plan is read as frozen (V-real-11);
# every command runs the drift check in place of T0's lists hash and refuses if today's lists remove anything it uses.
setopt no_bg_nice
caffeinate -i -w $$ &!                   # disowned (&!): no job for a wait to hang on (PR #300); waits below name pids
cd /Users/yoavbz/projects/neuraldsp-preset-generator
L=~/ndsp-presets/learn/trusted-data/logs
MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
TORCH_PY=$HOME/ndsp-presets/tools/demucs-venv/bin/python
TM=(-u -m learn.trusted_data_t3_mix)
step() { echo "$(date) $1"; }
grep -q 'D_F5mix (ROADMAP (a))' docs/dev-test-ledger.json || { echo "no D_F5mix declaration in the ledger"; exit 1; }
[ -f learn/trusted_data_t3_mix.py ] || { echo "the main checkout lacks learn/trusted_data_t3_mix.py: merge the PR first"; exit 1; }

step "check (zero renders: T3's frozen plan, the drift check, the stored full-twin mixes)"
$MAIN ${TM[@]} check > $L/t3mix-check.log 2>&1 || { echo "CHECK FAILED (see the log)"; exit 1; }

for arm in D_F5mix D_F5-noaug; do for seed in 20261042 20261043; do
  step "train $arm $seed"   # each run refuses unless its examples are D_F5's (dropped ids and counts)
  $TORCH_PY ${TM[@]} train --arm $arm --seed $seed > $L/t3mix-train-$arm-$seed.log 2>&1 \
    || { echo "TRAIN FAILED $arm $seed"; exit 1; }
done; done
# a run whose best epoch is within 4 of the cap must be extended before it is read: stop before anything is read
if grep -l "WARNING: best epoch" $L/t3mix-train-*.log; then
  echo "A RUN STOPPED NEAR THE EPOCH CAP: extend it before reading (nothing read, no render)"; exit 1
fi

step "fit (zero renders)"
$TORCH_PY ${TM[@]} fit > $L/t3mix-fit.log 2>&1 || { echo "FIT FAILED"; exit 1; }

step "r0 (zero renders; descriptive, read before V-real; no stop rule)"
$TORCH_PY ${TM[@]} r0 > $L/t3mix-r0.log 2>&1 || { echo "R0 FAILED"; exit 1; }

step "vreal-predict (zero renders)"
$TORCH_PY ${TM[@]} vreal-predict > $L/t3mix-vreal-predict.log 2>&1 || { echo "VREAL-PREDICT FAILED (see the log)"; exit 1; }

step "vreal-render (165 renders)"
pids=()
for k in 0 1 2; do
  $MAIN ${TM[@]} vreal-render --shard $k/3 > $L/t3mix-vreal-render-$k.log 2>&1 &
  pids+=($!)
  sleep 30
done
for p in $pids; do wait $p; done
for k in 0 1 2; do grep -q "MIX RENDER DONE" $L/t3mix-vreal-render-$k.log || { echo "VREAL-RENDER FAILED $k"; exit 1; }; done

step "report"
$MAIN ${TM[@]} report > $L/t3mix-report.log 2>&1 || { echo "REPORT FAILED"; exit 1; }
echo "$(date) T3 D_F5MIX CHAIN DONE"
