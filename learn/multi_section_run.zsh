#!/bin/zsh
# docs/multi-section-plan.md, step 2: the runner, unattended. Two render workers (CPU only, one
# thread each) per batch; the rebuild-tone run goes first: a worker exits (code 3) as soon as a
# rebuild-tone render or scoring process exists, and this runner waits until none does. Each part's
# renders are cached as they happen, so a restarted worker resumes exactly. After each batch the
# declared stopping rule (`decide`) prints exactly "DECISION STOP" or "DECISION CONTINUE".
# Launch (from the repo or worktree root):
#   mkdir -p ~/ndsp-presets/learn/multi-section/logs; setopt no_bg_nice
#   nohup caffeinate -i zsh learn/multi_section_run.zsh > ~/ndsp-presets/learn/multi-section/logs/run.out 2>&1 &
setopt no_bg_nice
REPO=${0:A:h:h}
cd $REPO
PY=$REPO/.venv/bin/python
O=~/ndsp-presets/learn/multi-section
L=$O/logs
mkdir -p $L
export PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
log() { echo "$(date '+%F %T') $*" >> $L/run.log }
log "start pid $$, commit $(git rev-parse --short HEAD), branch $(git branch --show-current)"

wait_clear() {   # the rebuild-tone run's renders and scoring go first
  local said=0
  local rc
  while true; do
    $PY -m learn.multi_section clear; rc=$?
    (( rc == 0 )) && break
    (( rc == 10 )) || { log "CLEAR CHECK FAILED (exit $rc)"; exit 1 }
    (( said )) || log "waiting: rebuild-tone renders, scoring or CPU torch steps, or other renders at the cap"
    said=1
    sleep 120
  done
  (( said )) && log "clear: resuming"
  return 0
}

NB=$($PY -m learn.multi_section batches | wc -l | tr -d ' ')
log "batches: $NB"
(( NB > 0 )) || { log "NO BATCHES (see sections/)"; exit 1 }
b=0
while (( b < NB )); do
  while true; do
    wait_clear
    p=()
    for w in 0 1; do
      $PY -u -m learn.multi_section run --worker $w/2 --batch $b >> $L/run-b$b-w$w.log 2>&1 & p+=($!)
      sleep 20
    done
    codes=()
    for pid in $p; do wait $pid; codes+=($?); done
    log "batch $b workers exited: ${codes[*]}"
    done_all=1
    for w in 0 1; do
      grep -qx "WORKER DONE batch $b $w/2" $L/run-b$b-w$w.log || done_all=0
    done
    if (( done_all )) && [[ ${codes[*]} == "0 0" ]]; then break; fi
    if [[ ${codes[(I)4]} -gt 0 ]]; then log "DISK GUARD: stopping (see run-b$b-w*.log)"; exit 1; fi
    if [[ ${codes[(I)3]} -gt 0 ]]; then log "yielded to the rebuild-tone run"; sleep 60; continue; fi
    log "BATCH $b FAILED (exit codes ${codes[*]}; see run-b$b-w*.log)"
    exit 1
  done
  $PY -u -m learn.multi_section decide --batch $b > $L/decide-$b.log 2>&1 || { log "DECIDE $b FAILED"; exit 1 }
  log "batch $b: $(grep '^batch' $L/decide-$b.log)"
  if grep -qx "DECISION STOP" $L/decide-$b.log; then break; fi
  grep -qx "DECISION CONTINUE" $L/decide-$b.log || { log "DECIDE $b: no decision line"; exit 1 }
  (( b++ ))
done
$PY -u -m learn.multi_section report > $L/report.log 2>&1 || { log "REPORT FAILED"; exit 1 }
log "all done"
