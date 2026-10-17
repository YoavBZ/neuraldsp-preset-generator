#!/bin/zsh
# The self-rendered dataset runner, unattended: docs/known-answer-b1-plan.md (B1, a test, first),
# then docs/pretrain-set-plan.md (part C's pilot, its learning curve and at most one extension).
#   0. Wait until the overnight runs are over: no `learn.rebuild_tone render` and no
#      `learn.multi_section run` process, and both run.logs end their latest run with "all done".
#   1. B1: plan, truth, mix, separate, rebuild, search (3 shards), report.
#   2. Part C: wait for the hum-screen amendment's manifest (`pretrain_set gate`), then pool,
#      backings, renders (3 shards), recheck, curve (one GPU job, guarded), decide; on
#      "DECISION EXTEND" one extension to 80k (renders, curve, decide); report; "all done".
# Every step is gated on an exact line in its own log. Launch (from this checkout's root):
#   mkdir -p ~/ndsp-presets/learn/selfrender/logs; setopt no_bg_nice
#   nohup caffeinate -i zsh learn/selfrender_run.zsh > ~/ndsp-presets/learn/selfrender/logs/run.out 2>&1 &
setopt no_bg_nice
REPO=${0:A:h:h}
cd $REPO
PY=${SELFRENDER_PY:-/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python}
TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
L=~/ndsp-presets/learn/selfrender/logs
mkdir -p $L
export PYTHONUNBUFFERED=1
log() { echo "$(date '+%F %T') $*" >> $L/run.log }
log "start pid $$, commit $(git rev-parse --short HEAD), branch $(git branch --show-current)"

RT_LOG=~/ndsp-presets/learn/rebuild-tone/logs/run.log
MS_LOG=~/ndsp-presets/learn/multi-section/logs/run.log
last_run_done() {   # the log's latest run (from its last " start pid " line) has an "all done" line
  [[ -f $1 ]] || return 1
  awk 'index($0, " start pid ") {n = NR} {l[NR] = $0} END {for (i = n; i && i <= NR; i++) print l[i]}' $1 \
    | grep -qE '^.{19} all done( |$)'
}
overnight_busy() {
  pgrep -f -- "-m learn\.rebuild_tone render" >/dev/null && return 0
  pgrep -f -- "-m learn\.multi_section run" >/dev/null && return 0
  pgrep -f -- "-m learn\.rebuild_tone_train" >/dev/null && return 0
  last_run_done $RT_LOG || return 0
  last_run_done $MS_LOG || return 0
  return 1
}
said=0
while overnight_busy; do
  (( said )) || log "waiting: the overnight runs (rebuild-tone and multi-section) are not done"
  said=1
  sleep 300
done
log "overnight runs done (rebuild-tone: $(grep -E '^.{19} all done' $RT_LOG | tail -1 | cut -c21-80); multi-section: all done)"

ok_line() { grep -qx "$2" $L/$1 }   # file, exact line
step() {   # name, exact success line, command...
  local name=$1 line=$2; shift 2
  "$@" > $L/$name.log 2>&1
  local rc=$?
  if ok_line $name.log "$line"; then log "$name: ok"; return 0; fi
  log "$name FAILED (exit $rc; no '$line' in $name.log)"; return 1
}
shards() {   # name, success-line prefix, module command...  (three shards, all must print the line)
  local name=$1 pre=$2; shift 2
  local p=() rc=0
  for i in 0 1 2; do
    OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 $PY -u -m "$@" --shard $i/3 > $L/$name-$i.log 2>&1 & p+=($!)
    sleep 20
  done
  for q in $p; do wait $q || rc=$?; done
  for i in 0 1 2; do
    ok_line $name-$i.log "$pre $i/3" || { log "$name shard $i: no '$pre $i/3' (rc $rc; see $name-$i.log)"; return 1 }
  done
  log "$name: 3 shards done"
}
gpu_guard() {   # one training job at a time, memory and disk
  while true; do
    local free=$(df -g ~ | awk 'NR==2{print $4}')
    local mem=$(memory_pressure | awk -F': ' '/free percentage/{gsub("%","",$2); print $2}')
    local other=$(pgrep -f -- "-m learn\.[a-z_0-9]+ (fit|train|curve)")
    if (( free >= 31 && mem >= 25 )) && [[ -z $other ]]; then return 0; fi
    log "GPU waiting: free ${free} GB, memory free ${mem}%, other training [${other//$'\n'/ }]"
    sleep 300
  done
}

# --- 1. B1 -------------------------------------------------------------------------------------------
run_b1() {
  step b1-plan "PLAN DONE" $PY -u -m learn.known_answer plan || return 1
  step b1-truth "TRUTH DONE" env OMP_NUM_THREADS=1 $PY -u -m learn.known_answer truth || return 1
  step b1-mix "MIX DONE" $PY -u -m learn.known_answer mix || return 1
  step b1-separate "SEPARATE DONE" env OMP_NUM_THREADS=2 $TORCH_PY -u -m learn.known_answer separate || return 1
  step b1-rebuild "REBUILD DONE" env OMP_NUM_THREADS=2 $TORCH_PY -u -m learn.known_answer rebuild || return 1
  shards b1-search "SEARCH DONE" learn.known_answer search || return 1
  step b1-report "REPORT DONE" $PY -u -m learn.known_answer report || return 1
  log "B1: $(grep -A4 '"primary": {' $L/b1-report.log | tr -s ' \n' ' ' | cut -c1-200)"
}
B1=0
if run_b1; then B1=1; log "B1 done"; else log "B1 FAILED (part C continues; it does not depend on B1)"; fi

# --- 2. part C ---------------------------------------------------------------------------------------
wait_amended() {
  local said=0 rc
  while true; do
    $PY -m learn.pretrain_set gate > $L/c-gate.log 2>&1; rc=$?
    (( rc == 0 )) && { log "manifest amended: $(tail -1 $L/c-gate.log)"; return 0 }
    (( rc == 10 )) || { log "C GATE CHECK FAILED (exit $rc; see c-gate.log)"; return 1 }
    (( said )) || log "waiting: the hum-screen amendment's manifest ($(tail -1 $L/c-gate.log))"
    said=1
    sleep 600
  done
}
render_and_curve() {   # n
  shards c-render-$1 "SHARD DONE" learn.pretrain_set render --n $1 || return 1
  $PY -u -m learn.pretrain_set report > $L/c-report-$1.log 2>&1 || log "c-report-$1 failed (descriptive; continuing)"
  gpu_guard
  step c-curve-$1 "CURVE DONE $1" env OMP_NUM_THREADS=2 $TORCH_PY -u -m learn.pretrain_set curve --n $1 || return 1
  $PY -u -m learn.pretrain_set decide --n $1 > $L/c-decide-$1.log 2>&1
  grep -qxE "DECISION (EXTEND|STOP)" $L/c-decide-$1.log || { log "decide $1: no decision line (see c-decide-$1.log)"; return 1 }
  log "decide $1: $(grep -E '^(READING|DECISION)' $L/c-decide-$1.log | tr '\n' ' ')"
}
run_c() {
  wait_amended || return 1
  step c-pool "POOL DONE" $PY -u -m learn.pretrain_set pool || return 1
  log "pool: $(grep '^pool ' $L/c-pool.log | cut -c1-300)"
  step c-backings "backings done" env OMP_NUM_THREADS=2 $PY -u -m learn.pretrain_set backings || return 1
  render_and_curve 40000 || return 1
  step c-recheck "RECHECK DONE" $PY -u -m learn.pretrain_set recheck || log "recheck failed (descriptive; continuing)"
  if grep -qx "DECISION EXTEND" $L/c-decide-40000.log; then
    render_and_curve 80000 || return 1
    log "no further extension unattended"
  fi
  $PY -u -m learn.pretrain_set report > $L/c-report.log 2>&1 || log "c-report failed"
}
C=0
if run_c; then C=1; log "part C done"; else log "part C FAILED or not started (see the lines above)"; fi
log "all done (B1 $B1, part C $C)"
