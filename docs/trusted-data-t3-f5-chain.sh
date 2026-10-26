#!/bin/zsh
# T3's F5 chain (declared 2026-10-26: docs/trusted-data-t0-design.md, "T3"; ledger trusted-data-t3).
# Written, NOT launched: run it only after the independent code review and with the user's go, from the main checkout
# once the PR that adds `--stage t3` is merged. Renders and separations never overlap (the order below); every render
# command waits for a slot under 3 render processes machine-wide and stops under 31 GB free.
# Cost from the dry run's pool (T2's rates): about 5.2k renders (0.8 h), about 5.0k separations (3.7-5.9 h with the
# optional CPU worker), 1 crop and its stem (minutes), 4 training runs (about 1 h MPS), about 1k V-real renders (0.2 h).
setopt no_bg_nice
cd /Users/yoavbz/projects/neuraldsp-preset-generator
L=~/ndsp-presets/learn/trusted-data/logs
MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
MSST=$HOME/ndsp-presets/tools/msst-venv/bin/python
TORCH_PY=$HOME/ndsp-presets/tools/demucs-venv/bin/python
TD=(-u -m learn.trusted_data)
step() { echo "$(date) $1"; }
grep -q '"trusted-data-t3"' docs/dev-test-ledger.json || { echo "no trusted-data-t3 ledger entry"; exit 1; }
grep -q 'trusted_data_t3' learn/trusted_data.py || { echo "the main checkout lacks --stage t3: merge the PR first"; exit 1; }

step "plan (freezes V-real's membership)"
$MAIN ${TD[@]} plan --stage t3 > $L/t3-plan.log 2>&1 || { echo "PLAN FAILED"; exit 1; }
# V-real's frozen members need a stage-F-style crop (vreal-crops cuts the recovered ones); --drop-missing-crops is an
# opt-in escape only, never the default
DROP=()
[ -n "$T3_VREAL_DROP_MISSING" ] && DROP=(--drop-missing-crops)

step "render"
for k in 0 1 2; do caffeinate -i $MAIN ${TD[@]} render --stage t3 --shard $k/3 > $L/t3-render-$k.log 2>&1 & sleep 60; done; wait
for k in 0 1 2; do grep -q "RENDER DONE" $L/t3-render-$k.log || { echo "RENDER FAILED $k"; exit 1; }; done

step "build (X-LANCE; MPS ascending, CPU descending)"
caffeinate -i $MSST ${TD[@]} build --stage t3 --device mps --order asc > $L/t3-build-mps.log 2>&1 &
sleep 120
caffeinate -i $MSST ${TD[@]} build --stage t3 --device cpu --order desc > $L/t3-build-cpu.log 2>&1 &
wait
grep -q "BUILD DONE" $L/t3-build-mps.log || { echo "BUILD FAILED (mps)"; exit 1; }
# a worker that found nothing left exits early; one more pass builds anything a stopped worker left
$MSST ${TD[@]} build --stage t3 --device mps --order asc >> $L/t3-build-mps.log 2>&1 || { echo "BUILD FAILED"; exit 1; }

# the recovered V-real members' stage-F-style crops and crop-only stems (separations: before any render resumes)
step "vreal-crops"
$MSST ${TD[@]} vreal-crops --stage t3 --device mps > $L/t3-vreal-crops.log 2>&1 || { echo "VREAL-CROPS FAILED"; exit 1; }

for arm in D_core5 D_F5; do for seed in 20261042 20261043; do
  step "train $arm $seed"   # D_F5 refuses unless the positive control passed (render and build)
  caffeinate -i $TORCH_PY ${TD[@]} train --stage t3 --arm $arm --seed $seed > $L/t3-train-$arm-$seed.log 2>&1 \
    || { echo "TRAIN FAILED $arm $seed"; exit 1; }
done; done
grep -h "WARNING: best epoch" $L/t3-train-*.log && echo "a run stopped near the epoch cap: extend it before reading (report marks it)"

step "fit"; $TORCH_PY ${TD[@]} fit --stage t3 > $L/t3-fit.log 2>&1 || { echo "FIT FAILED"; exit 1; }
step "vreal-predict"
$TORCH_PY ${TD[@]} vreal-predict --stage t3 ${DROP[@]} > $L/t3-vreal-predict.log 2>&1 || { echo "VREAL-PREDICT FAILED (see the log)"; exit 1; }
for k in 0 1 2; do caffeinate -i $MAIN ${TD[@]} vreal-render --stage t3 --shard $k/3 > $L/t3-vreal-render-$k.log 2>&1 & sleep 30; done; wait
for k in 0 1 2; do grep -q "VREAL RENDER DONE" $L/t3-vreal-render-$k.log || { echo "VREAL-RENDER FAILED $k"; exit 1; }; done
step "report"; $MAIN ${TD[@]} report --stage t3 > $L/t3-report.log 2>&1 || { echo "REPORT FAILED"; exit 1; }
echo "$(date) T3 F5 CHAIN DONE"
