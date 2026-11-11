#!/bin/zsh
# C3b's stage 2 (ledger phase_c3b_s2, docs/full-controls-plan.md "C3b stage 2 in detail"), after the C3i read's launcher
# exits (its PID, given; its renders hold the 3 slots until then) and before C3r's read, which waits on C3r's training:
# GOAT's answers on all three amps for C3b and the adopted C3 (goat-predict --amps3, CPU), C3b's BKS renders on all
# three amps (real-render, as C3's read rendered C3-cabS), both models' GOAT renders on all three amps (goat-render
# --amps3), each in 3 shards (at most 3 render processes; `_wait_cap` guards), then the zero-render report
# (c3b-s2-rows). Any failure stops it.   zsh logs/launch-c3b-s2.zsh /path/to/worktree C3I_READ_LAUNCHER_PID
setopt no_bg_nice
W=${1:?the worktree to run from}
WAIT_PID=${2:?the C3i read launcher PID to wait for}
cd "${W}" || exit 1
export PYTHONPATH=. OMP_NUM_THREADS=1
PY=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
T=~/ndsp-presets/tools/demucs-venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/c3b-s2.log
PIDS=${LOGS}/c3b-s2-pids.txt
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)                  # a relaunch: the old log rotated aside
[[ -f ${PIDS} ]] && mv ${PIDS} ${PIDS}.$(date +%Y%m%d-%H%M%S)         # and the old PIDs: only this launch's are live
caffeinate -i -w $$ &
echo "launcher $$" >> ${PIDS}
note() { echo "$1 $(date)" >> ${L}; }
note "waiting for pid ${WAIT_PID} (the C3i read's launcher)"
while kill -0 ${WAIT_PID} 2>/dev/null; do sleep 60; done
note "start $(git rev-parse --short HEAD)"

run() {        # one foreground step, logged; stop on failure
  local label=$1; shift
  "$@" >> ${LOGS}/c3b-s2-${label}.log 2>&1 &
  local p=$!
  echo "${label} ${p}" >> ${PIDS}
  wait ${p} || { note "FAILED ${label}"; exit 1; }
  note "${label} done"
}

three() {      # 3 shards at once (the render cap), every one waited on before a failure stops the launcher
  local label=$1; shift
  local pids=() rc=0
  for k in 0 1 2; do
    "$@" --shard ${k}/3 > ${LOGS}/c3b-s2-${label}-${k}.log 2>&1 &
    pids+=($!)
  done
  echo "${label} ${pids}" >> ${PIDS}
  for p in ${pids}; do wait ${p} || { rc=1; note "FAILED ${label} pid ${p}"; }; done
  (( rc == 0 )) || exit 1
  note "${label} done"
}

run goat-predict-c3b env DS_DEVICE=cpu ${T} -u -m learn.pipeline_fix goat-predict --amps3 --names C3b
run goat-predict-c3 env DS_DEVICE=cpu ${T} -u -m learn.pipeline_fix goat-predict --amps3 --names C3-cabS
three real ${PY} -u -m learn.pipeline_fix real-render --names C3b
three goat ${PY} -u -m learn.pipeline_fix goat-render --amps3 --names C3b,C3-cabS
run rows ${PY} -u -m learn.full_controls_c3 c3b-s2-rows
note done
