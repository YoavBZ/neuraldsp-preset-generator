#!/bin/zsh
# ROADMAP step (b), D_F5ft: X-LANCE gtr_mss fine-tuned on the self-built mixes, then the every-control model fed the
# fine-tuned stem (declared 2026-10-27: docs/trusted-data-t0-design.md, "D_F5ft: the every-control model fed the
# fine-tuned stem"; ledger trusted-data-t3, amendment 4 "X-LANCE fine-tune (ROADMAP (b))"). Approved by the user
# 2026-10-27 ("Yes for all"). Run from the main checkout AFTER step (a)'s chain has finished (`check` refuses before).
# Cost: prep about 20-30 min of CPU (4 processes, zero renders); the gate up to about 30 min; two cross-fitted
# fine-tunes, each up to 5.5 h of the gate's measured step time (11 h in all; earlier at the validation plateau);
# about 4,190 separations, about 3-5 h on MPS + CPU; D_F5ft's 2 runs about 15-30 min of MPS; fit, R0, the probe and
# V-real's predictions minutes; V-real 99 renders (33 groups x (1 priming at S + 2 directions)), a few minutes on 3
# processes; isolate=True, 0.25 s trimmed, at most 3 render processes machine-wide, the 31 GB disk guard.
# Outputs only under trusted-data/t3-xlft/; t0/, t2/, t3/, t3-mix/ and tone-probe/ are only read.
setopt no_bg_nice
caffeinate -i -w $$ &!                   # disowned (&!): no job for a wait to hang on (PR #300); waits below name pids
cd /Users/yoavbz/projects/neuraldsp-preset-generator
L=~/ndsp-presets/learn/trusted-data/logs
MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
MSST=$HOME/ndsp-presets/tools/msst-venv/bin/python
TORCH_PY=$HOME/ndsp-presets/tools/demucs-venv/bin/python
XF=(-u -m learn.xlance_finetune)
step() { echo "$(date) $1"; }
grep -q 'X-LANCE fine-tune (ROADMAP (b))' docs/dev-test-ledger.json || { echo "no D_F5ft declaration in the ledger"; exit 1; }
[ -f learn/xlance_finetune.py ] || { echo "the main checkout lacks learn/xlance_finetune.py: merge the PR first"; exit 1; }

step "check (zero renders: the ledger, step (a) done, the frozen sets, the folds, disk)"
$MAIN -m learn.xlance_finetune check > $L/xlft-check.log 2>&1 || { echo "CHECK FAILED (see the log)"; exit 1; }

step "prep (zero renders: F5's mixes and wet targets rebuilt and checked; the stock-weights pipeline control)"
$MSST ${XF[@]} prep > $L/xlft-prep.log 2>&1 || { echo "PREP FAILED"; exit 1; }

step "gate (the MPS gate and its fallbacks; step time and memory)"
$MSST ${XF[@]} gate > $L/xlft-gate.log 2>&1 || { echo "GATE FAILED"; exit 1; }

for k in 0 1; do
  step "fine-tune fold $k"
  $MSST ${XF[@]} train --fold $k > $L/xlft-train-$k.log 2>&1 || { echo "FINE-TUNE FAILED fold $k"; exit 1; }
done
grep -h "^NOTE:" $L/xlft-train-*.log    # a fold still improving at its stop is reported, not extended (the user's call)

for k in 0 1; do
  step "separate fold $k (out-of-fold stems; mps ascending, cpu descending)"
  $MSST ${XF[@]} separate --fold $k --device mps --order asc > $L/xlft-sep-$k-mps.log 2>&1 &
  p1=$!
  sleep 60
  $MSST ${XF[@]} separate --fold $k --device cpu --order desc > $L/xlft-sep-$k-cpu.log 2>&1 &
  p2=$!
  wait $p1
  wait $p2
  for d in mps cpu; do grep -q "SEPARATE DONE fold $k" $L/xlft-sep-$k-$d.log || { echo "SEPARATE FAILED $k $d"; exit 1; }; done
done

step "vreal-stems (V-real-11's crops through their assigned fold)"
$MSST ${XF[@]} vreal-stems --device cpu > $L/xlft-vreal-stems.log 2>&1 || { echo "VREAL-STEMS FAILED"; exit 1; }

for seed in 20261042 20261043; do
  step "train-d D_F5ft $seed"   # refuses unless every stem is in place and out of fold, and the examples are D_F5's
  $TORCH_PY ${XF[@]} train-d --seed $seed > $L/xlft-traind-$seed.log 2>&1 || { echo "TRAIN-D FAILED $seed"; exit 1; }
done
if grep -l "WARNING: best epoch" $L/xlft-traind-*.log; then
  echo "A D_F5ft RUN STOPPED NEAR THE EPOCH CAP: extend it before reading (nothing read, no render)"; exit 1
fi

step "fit (zero renders)"
$TORCH_PY ${XF[@]} fit > $L/xlft-fit.log 2>&1 || { echo "FIT FAILED"; exit 1; }

step "r0 (zero renders; descriptive, read before V-real; no stop rule)"
$TORCH_PY ${XF[@]} r0 > $L/xlft-r0.log 2>&1 || { echo "R0 FAILED"; exit 1; }

step "probe (zero renders; the tone probe on the new stems)"
$MAIN ${XF[@]} probe > $L/xlft-probe.log 2>&1 || { echo "PROBE FAILED"; exit 1; }

step "vreal-predict (zero renders)"
$TORCH_PY ${XF[@]} vreal-predict > $L/xlft-vreal-predict.log 2>&1 || { echo "VREAL-PREDICT FAILED (see the log)"; exit 1; }

step "vreal-render (99 renders)"
pids=()
for k in 0 1 2; do
  $MAIN ${XF[@]} vreal-render --shard $k/3 > $L/xlft-vreal-render-$k.log 2>&1 &
  pids+=($!)
  sleep 30
done
for p in $pids; do wait $p; done
for k in 0 1 2; do grep -q "FT RENDER DONE" $L/xlft-vreal-render-$k.log || { echo "VREAL-RENDER FAILED $k"; exit 1; }; done

step "report"
$MAIN ${XF[@]} report > $L/xlft-report.log 2>&1 || { echo "REPORT FAILED"; exit 1; }
echo "$(date) T3 D_F5FT CHAIN DONE"
