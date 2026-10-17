#!/bin/zsh
# docs/rebuild-gap-plan.md (amendment 1 governs): the chained runner, unattended. Three lanes:
#   CPU now (zero renders, at most 2 threads, one step at a time): A1 where, A2 rescore, B0, A3 metrics;
#   T (MPS) after the Mega-53 runner's "lane A done:" and B0's end (a lane-A failure only alerts, and
#     T, and so TR, then wait for the coordinator): rank then ctl per fold, the arms' rebuilds, B1;
#   R (renders) after the Mega-53 runner has ended: the rotation choice, R1, scoring, the R1 report,
#     R2 by its rule;
# then TR (renders) when both T and R have ended: TR1, scoring, the TR report, TR2 by its rule.
# The code's own gates hold the rest (stop files, the render cap, swap and disk guards, the probe
# and arm checks, the comparators). Launch:
#   mkdir -p ~/ndsp-presets/learn/rebuild-gap/logs; setopt no_bg_nice; nohup caffeinate -i zsh learn/rebuild_gap_run.zsh > ~/ndsp-presets/learn/rebuild-gap/logs/run.out 2>&1 &
setopt no_bg_nice
REPO=${0:A:h:h}
cd $REPO
PY=$REPO/.venv/bin/python
TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
O=~/ndsp-presets/learn/rebuild-gap
L=$O/logs
mkdir -p $L
export PYTHONUNBUFFERED=1
log() { echo "$(date '+%F %T') $*" >> $L/run.log }
log "start pid $$, commit $(git rev-parse --short HEAD), branch $(git branch --show-current)"

# --- lane CPU: zero renders, one step at a time ---------------------------------------------------
(
  OMP_NUM_THREADS=1 $PY -u -m learn.rebuild_gap where > $L/where.log 2>&1 || { log "A1 WHERE FAILED"; exit 1 }
  log "A1 done"
  OMP_NUM_THREADS=1 $PY -u -m learn.rebuild_gap rescore --workers 1 > $L/rescore.log 2>&1 || { log "A2 RESCORE FAILED"; exit 1 }
  log "A2 done"
  OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 $TORCH_PY -u -m learn.rebuild_gap_train b0 > $L/b0.log 2>&1 || { log "B0 FAILED"; exit 1 }
  log "B0 done"
  OMP_NUM_THREADS=1 $PY -u -m learn.rebuild_gap metrics > $L/metrics.log 2>&1 || { log "A3 METRICS FAILED"; exit 1 }
  log "A3 done"
) &
laneC=$!
log "lane CPU: pid $laneC"

# --- lane T: training (MPS) -----------------------------------------------------------------------
guard() {   # one GPU job at a time, memory and disk
  while true; do
    local free=$(df -g ~ | awk 'NR==2{print $4}')
    local mem=$(memory_pressure | awk -F': ' '/free percentage/{gsub("%","",$2); print $2}')
    local other=$(pgrep -f -- "-m learn\.[a-z_0-9]+ (fit|train)" | grep -v "^$$\$")
    if (( free >= 31 && mem >= 25 )) && [[ -z $other ]]; then return 0; fi
    log "T waiting: free ${free} GB, memory free ${mem}%, other training [${other//$'\n'/ }]"
    sleep 300
  done
}
train() {   # arm fold
  local d=$O/models-$1-f$2
  [[ -f $d/DONE ]] && { log "T $1 fold $2 already done"; return 0 }
  guard
  log "T $1 fold $2 start"
  OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 $TORCH_PY -u -m learn.rebuild_gap_train train --fold $2 --arm $1 \
      > $L/train-$1-f$2.log 2>&1 || { log "T $1 fold $2 FAILED (see train-$1-f$2.log)"; return 1 }
  log "T $1 fold $2 done: $(tail -1 $L/train-$1-f$2.log)"
}
(
  $PY -u -m learn.rebuild_gap wait-lane-a > $L/wait-lane-a.log 2>&1
  log "T: lane A done seen"
  # B0's 2 threads finish first, so this study never adds more than 2 threads beside the Mega-53 test.
  until grep -q -E "B0 done|B0 FAILED|A1 WHERE FAILED|A2 RESCORE FAILED" $L/run.log; do sleep 60; done
  log "T: lane CPU's B0 has ended"
  for f in 0 1 2 3; do train rank $f || exit 1; train ctl $f || exit 1; done
  for a in rank ctl; do
    OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 $TORCH_PY -u -m learn.rebuild_gap_train rebuild --arm $a \
        > $L/rebuild-$a.log 2>&1 || { log "ARM REBUILD $a FAILED"; exit 1 }
  done
  log "T: arms rebuilt"
  OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 $TORCH_PY -u -m learn.rebuild_gap_train b0 --variants arm_rank,arm_ctl,cprime_ref \
      --out b1.json > $L/b1.log 2>&1 || log "B1 FAILED"
  log "T done"
) &
laneT=$!
log "lane T: pid $laneT"

# --- lane R: the probes (renders, after the Mega-53 runner) ---------------------------------------
shards() {   # command words...; three shards, all must succeed
  local p=() ok=0
  for i in 0 1 2; do OMP_NUM_THREADS=1 $PY -u -m learn.rebuild_gap "$@" --shard $i/3 > $L/${1}-${@[-1]}-$i.log 2>&1 & p+=($!); done
  for q in $p; do wait $q || ok=1; done
  return $ok
}
(
  $PY -u -m learn.rebuild_gap wait-mega > $L/wait-mega.log 2>&1
  log "R: the Mega-53 runner has ended"
  shards choose-rot || { log "R ROTATION CHOICE FAILED"; exit 1 }
  log "R: rotation chosen"
  shards render --stage r1 || { log "R1 RENDERS FAILED"; exit 1 }
  log "R1 renders done"
  OMP_NUM_THREADS=1 $PY -u -m learn.rebuild_gap score --workers 3 > $L/score-r1.log 2>&1 || { log "R1 SCORING FAILED"; exit 1 }
  $PY -u -m learn.rebuild_gap report --stage r1 > $L/report-r1.log 2>&1 || { log "R1 REPORT FAILED"; exit 1 }
  log "R1 report: $(grep 'R2 extends' $L/report-r1.log)"
  R2=$($PY -c "import json; print(','.join(json.load(open('$O/report-r1.json'))['r2_probes']))")
  if [[ -n $R2 ]]; then
    shards render --stage r2 || { log "R2 RENDERS FAILED"; exit 1 }
    OMP_NUM_THREADS=1 $PY -u -m learn.rebuild_gap score --workers 3 > $L/score-r2.log 2>&1 || { log "R2 SCORING FAILED"; exit 1 }
    $PY -u -m learn.rebuild_gap report --stage r2 > $L/report-r2.log 2>&1 || log "R2 REPORT FAILED"
    log "R2 done ($R2)"
  else
    log "R2: no probe extends"
  fi
) &
laneR=$!
log "lane R: pid $laneR"

wait $laneC
wait $laneR; rcR=$?
wait $laneT; rcT=$?
if (( rcT )); then log "TR not started (lane T failed)"; exit 1; fi
if (( rcR )); then log "TR not started (lane R failed)"; exit 1; fi

# --- TR: the arms on rendered ranking -------------------------------------------------------------
shards render --stage tr1 || { log "TR1 RENDERS FAILED"; exit 1 }
OMP_NUM_THREADS=1 $PY -u -m learn.rebuild_gap score --workers 3 > $L/score-tr1.log 2>&1 || { log "TR1 SCORING FAILED"; exit 1 }
$PY -u -m learn.rebuild_gap report --stage tr > $L/report-tr.log 2>&1 || { log "TR REPORT FAILED"; exit 1 }
log "TR1 report done"
if [[ $($PY -c "import json; print(json.load(open('$O/report-tr.json'))['tr2_due'])") == True ]]; then
  shards render --stage tr2 || { log "TR2 RENDERS FAILED"; exit 1 }
  OMP_NUM_THREADS=1 $PY -u -m learn.rebuild_gap score --workers 3 > $L/score-tr2.log 2>&1 || { log "TR2 SCORING FAILED"; exit 1 }
  $PY -u -m learn.rebuild_gap report --stage tr > $L/report-tr.log 2>&1 || log "TR REPORT FAILED"
  log "TR2 done"
else
  log "TR2 not due"
fi
log "all done"
