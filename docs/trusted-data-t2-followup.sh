#!/bin/zsh
# T2's follow-up chain (declared 2026-10-25; docs/trusted-data-t0-design.md, "T2's additions as built").
# Run ONLY after T2's own chain has printed "T2 CHAIN DONE" (logs/t2-chain.log) and the PR that adds these commands
# is merged into the main checkout. It adds, never re-makes: fit, vreal-predict and vreal-render keep what T2's chain
# made and add the SES-ALL arm (option (c), approved by the user 2026-10-25); the T2-side stem read and diagnostic (b)
# are zero renders. Cost: 2 training runs of about 1.5 h (MPS), about 60 V-real renders plus 30 priming, no
# separations (SES-ALL trains on SES's stored stems).
setopt no_bg_nice
cd /Users/yoavbz/projects/neuraldsp-preset-generator
L=~/ndsp-presets/learn/trusted-data/logs
T2=~/ndsp-presets/learn/trusted-data/t2
MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
TORCH_PY=$HOME/ndsp-presets/tools/demucs-venv/bin/python
TD=(-u -m learn.trusted_data)
step() { echo "$(date) $1"; }
grep -q "T2 CHAIN DONE" $L/t2-chain.log || { echo "T2's chain is not done: wait"; exit 1; }
grep -q '"plan-ses-all"' learn/trusted_data.py || { echo "the main checkout lacks the T2 additions: merge the PR first"; exit 1; }
# keep T2's own records as they were (the add-only commands leave them, this is a second guard)
mkdir -p $T2/before-followup
for f in fit.json report.json vreal/predictions.json; do [ -e $T2/$f ] && cp -n $T2/$f $T2/before-followup/${f:t}; done
step "t2-stem-read"; $MAIN ${TD[@]} t2-stem-read > $L/t2-stem-read.log 2>&1 || { echo "STEM READ FAILED"; exit 1; }
step "t2-density"; $MAIN ${TD[@]} t2-density > $L/t2-density.log 2>&1 || { echo "DENSITY FAILED"; exit 1; }
step "plan-ses-all"; $MAIN ${TD[@]} plan-ses-all > $L/t2-ses-all-plan.log 2>&1 || { echo "PLAN SES-ALL FAILED"; exit 1; }
for seed in 20261042 20261043; do
  step "train SES-ALL $seed"
  caffeinate -i $TORCH_PY ${TD[@]} train --arm SES-ALL --seed $seed > $L/t2-train-SES-ALL-$seed.log 2>&1 \
    || { echo "TRAIN FAILED SES-ALL $seed"; exit 1; }
done
step "fit (adds SES-ALL)"; $TORCH_PY ${TD[@]} fit > $L/t2-fit-ses-all.log 2>&1 || { echo "FIT FAILED"; exit 1; }
step "vreal-predict (adds SES-ALL)"
$TORCH_PY ${TD[@]} vreal-predict > $L/t2-vreal-predict-ses-all.log 2>&1 || { echo "VREAL-PREDICT FAILED"; exit 1; }
step "vreal-render (SES-ALL only)"
for k in 0 1 2; do caffeinate -i $MAIN ${TD[@]} vreal-render --shard $k/3 > $L/t2-vreal-render-ses-all-$k.log 2>&1 & sleep 30; done; wait
for k in 0 1 2; do grep -q "VREAL RENDER DONE" $L/t2-vreal-render-ses-all-$k.log || { echo "VREAL-RENDER FAILED $k"; exit 1; }; done
step "report"; $MAIN ${TD[@]} report > $L/t2-report-followup.log 2>&1 || { echo "REPORT FAILED"; exit 1; }
echo "$(date) T2 FOLLOW-UP DONE"
