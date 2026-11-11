#!/bin/zsh
# C3c's read (ledger phase_c3c, docs/full-controls-plan.md "C3c in detail"), after C3c's training (logs/c3c-train.log
# "done"): C3c's answers on BKS and GOAT (real-predict, goat-predict, CPU, the adopted C3's hold), then its rows at zero
# renders (c3c-rows: C3c's pick and W's valued on C3-cabS's own per-amp renders). No render.
#   zsh logs/launch-c3c-read.zsh /path/to/worktree
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=. OMP_NUM_THREADS=1
PY=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
T=~/ndsp-presets/tools/demucs-venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/c3c-read.log
PIDS=${LOGS}/c3c-read-pids.txt
TAG=C3c
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)                  # a relaunch: the old log rotated aside
[[ -f ${PIDS} ]] && mv ${PIDS} ${PIDS}.$(date +%Y%m%d-%H%M%S)         # and the old PIDs: only this launch's are live
caffeinate -i -w $$ &
echo "launcher $$" >> ${PIDS}
note() { echo "$1 $(date)" >> ${L}; }
note "waiting for C3c's training"
until [[ $(tail -1 ${LOGS}/c3c-train.log 2>/dev/null) == (done*|*FAILED*|*fail*) ]]; do sleep 60; done
[[ $(tail -1 ${LOGS}/c3c-train.log) == done* ]] || { note "C3c's training did not finish; the read does not start"; exit 1; }
note "start $(git rev-parse --short HEAD)"

run() {        # one foreground step, logged; stop on failure
  local label=$1; shift
  "$@" >> ${LOGS}/c3c-read-${label}.log 2>&1 &
  local p=$!
  echo "${label} ${p}" >> ${PIDS}
  wait ${p} || { note "FAILED ${label}"; exit 1; }
  note "${label} done"
}

run predict env DS_DEVICE=cpu ${T} -u -m learn.pipeline_fix real-predict --names ${TAG}
run goat-predict env DS_DEVICE=cpu ${T} -u -m learn.pipeline_fix goat-predict --names ${TAG}
run rows ${PY} -u -m learn.full_controls_c3 c3c-rows
note done
