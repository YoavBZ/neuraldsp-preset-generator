#!/bin/zsh
# docs/cprime-sep-plan.md: separator-robust C′ for folds 0-3, the zero-render evaluation, then the
# control arm. MPS, no renders, no separation. Launch:
#   setopt no_bg_nice; nohup caffeinate -i zsh learn/cprime_sep_run.zsh > ~/ndsp-presets/learn/direc-sep/run.out 2>&1 &
setopt no_bg_nice
REPO=${0:A:h:h}
cd $REPO
PY=~/ndsp-presets/tools/demucs-venv/bin/python
D=~/ndsp-presets/learn/direc
O=~/ndsp-presets/learn/direc-sep
LIB=$O/lib.npz
L1C=~/ndsp-presets/learn/local-objective/logs/run1c.log        # read only
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONUNBUFFERED=1
mkdir -p $O
log() { echo "$(date '+%F %T') $*" >> $O/run.log }
log "start pid $$, commit $(git rev-parse --short HEAD), branch $(git branch --show-current)"

# Experiment 1c's separation refuses to run beside training: start only after it is done.
until grep -q "1c separate+rebuild done" $L1C 2>/dev/null; do
  if grep -q "FAILED" $L1C 2>/dev/null; then log "1c log shows FAILED: not starting"; exit 1; fi
  sleep 60
done
log "1c separate+rebuild done seen"

guard() {
  while true; do
    local free=$(df -g ~ | awk 'NR==2{print $4}')
    local mem=$(memory_pressure | awk -F': ' '/free percentage/{gsub("%","",$2); print $2}')
    local other=$(pgrep -f -- "-m learn\.[a-z_0-9]+ (fit|train)")
    if (( free >= 31 && mem >= 25 )) && [[ -z $other ]]; then return 0; fi
    log "waiting: free ${free} GB, memory free ${mem}%, other training [${other//$'\n'/ }]"
    sleep 300
  done
}

fold() {   # arm p f
  local arm=$1 p=$2 f=$3 R out
  if [[ $f == 2 ]]; then R=$D/models-cprime/fold2.pt; else R=$D/models-cprime-f$f/fold$f.pt; fi
  out=$O/models-$arm-f$f
  [[ -f $out/DONE ]] && { log "$arm fold $f already done"; return 0 }
  guard
  log "$arm fold $f start (resume $R, p $p)"
  $PY -u -m learn.direc fit --cache $D/cache --fold $f --seed 0 --steps 5150 --warmup 200 \
      --lr 1e-4 --lr-end 2e-5 --log-every 250 --resume $R --sep-lib $LIB --sep-p $p \
      --patience 1500 --min-steps 1500 --mark-done --out $out > $O/fit-$arm-f$f.log 2>&1 \
    || { log "$arm fold $f FAILED (see fit-$arm-f$f.log)"; return 1 }
  log "$arm fold $f done: $(grep 'final =' $O/fit-$arm-f$f.log)"
}

for f in 0 1 2 3; do fold sep 0.75 $f || exit 1; done
[[ -f $O/eval-cprime.json ]] || $PY -u -m learn.direc_sep eval --arm cprime --models cprime >> $O/eval.log 2>&1
$PY -u -m learn.direc_sep eval --arm sep --models "$O/models-sep-f{f}/fold{f}.pt" >> $O/eval.log 2>&1 \
  || { log "eval sep FAILED"; exit 1 }
$PY -u -m learn.direc_sep report > $O/report-main.log 2>&1
log "main arm evaluated: report.json"

for f in 0 1 2 3; do fold ctl 0.0 $f || exit 1; done
$PY -u -m learn.direc_sep eval --arm control --models "$O/models-ctl-f{f}/fold{f}.pt" >> $O/eval.log 2>&1 \
  || { log "eval control FAILED"; exit 1 }
$PY -u -m learn.direc_sep report > $O/report-all.log 2>&1
log "all done"
