#!/bin/zsh
# T3's F5 follow-up R1 (declared 2026-10-26: docs/trusted-data-t0-design.md, "F5 follow-up"; ledger trusted-data-t3,
# amendment 1 "F5 follow-up R"). POST HOC AND DESCRIPTIVE. Written, NOT launched: run it only after the independent
# review and with the user's go, from the main checkout once the PR that adds learn/trusted_data_t3_r.py is merged.
# R0 (zero renders) ran in that PR; its table is t3/followup-r/r0.json and is read once (r0 keeps an existing file).
# Cost: r1-predict zero renders; r1-render 99 renders (33 (part, amp) groups x (1 priming at S + 2 directions)),
# about 5 minutes on 3 processes; isolate=True, 0.25 s trimmed, at most 3 render processes machine-wide (every
# r1-render waits for a slot), the 31 GB disk guard. Outputs only under t3/followup-r/; F5's files are only read.
setopt no_bg_nice
caffeinate -i -w $$ &!                   # disowned (&!): no job for a wait to hang on (PR #300); waits below name pids
cd /Users/yoavbz/projects/neuraldsp-preset-generator
L=~/ndsp-presets/learn/trusted-data/logs
R=~/ndsp-presets/learn/trusted-data/t3/followup-r
MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
TORCH_PY=$HOME/ndsp-presets/tools/demucs-venv/bin/python
TR=(-u -m learn.trusted_data_t3_r)
step() { echo "$(date) $1"; }
grep -q 'F5 follow-up R' docs/dev-test-ledger.json || { echo "no F5 follow-up R declaration in the ledger"; exit 1; }
[ -f learn/trusted_data_t3_r.py ] || { echo "the main checkout lacks learn/trusted_data_t3_r.py: merge the PR first"; exit 1; }

if [ ! -f $R/r0.json ]; then
  step "r0 (zero renders; followup-r/r0.json was expected from the PR)"
  $TORCH_PY ${TR[@]} r0 > $L/t3r-r0.log 2>&1 || { echo "R0 FAILED"; exit 1; }
fi

step "r1-predict (zero renders)"
$MAIN ${TR[@]} r1-predict > $L/t3r-r1-predict.log 2>&1 || { echo "R1-PREDICT FAILED (see the log)"; exit 1; }

step "r1-render (99 renders)"
pids=()
for k in 0 1 2; do
  $MAIN ${TR[@]} r1-render --shard $k/3 > $L/t3r-r1-render-$k.log 2>&1 &
  pids+=($!)
  sleep 30
done
for p in $pids; do wait $p; done
for k in 0 1 2; do grep -q "R1 RENDER DONE" $L/t3r-r1-render-$k.log || { echo "R1-RENDER FAILED $k"; exit 1; }; done

step "r1-report"
$MAIN ${TR[@]} r1-report > $L/t3r-r1-report.log 2>&1 || { echo "R1-REPORT FAILED"; exit 1; }
echo "$(date) T3 F5 FOLLOW-UP R1 CHAIN DONE"
