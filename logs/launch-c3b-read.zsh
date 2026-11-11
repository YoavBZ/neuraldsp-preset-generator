#!/bin/zsh
# C3b's stage 1 (ledger phase_c3b, docs/full-controls-plan.md "C3b in detail"), after C3b's training (logs/c3b-train.log
# "done"): C3b's answers on BKS and GOAT (real-predict, goat-predict, CPU, the adopted C3's hold), then the stage-1 rows
# at zero renders (c3b-rows: each pick against blind on the stored-recipe labels' held halves). No render.
#   zsh logs/launch-c3b-read.zsh /path/to/worktree
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=. OMP_NUM_THREADS=1
PY=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
T=~/ndsp-presets/tools/demucs-venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/c3b-read.log
PIDS=${LOGS}/c3b-read-pids.txt
TAG=C3b
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)                  # a relaunch: the old log rotated aside
[[ -f ${PIDS} ]] && mv ${PIDS} ${PIDS}.$(date +%Y%m%d-%H%M%S)         # and the old PIDs: only this launch's are live
caffeinate -i -w $$ &
echo "launcher $$" >> ${PIDS}
note() { echo "$1 $(date)" >> ${L}; }
note "waiting for C3b's training"
until [[ $(tail -1 ${LOGS}/c3b-train.log 2>/dev/null) == (done*|*FAILED*|*fail*) ]]; do sleep 60; done
[[ $(tail -1 ${LOGS}/c3b-train.log) == done* ]] || { note "C3b's training did not finish; stage 1 does not start"; exit 1; }
note "start $(git rev-parse --short HEAD)"

run() {        # one foreground step, logged; stop on failure
  local label=$1; shift
  "$@" >> ${LOGS}/c3b-read-${label}.log 2>&1 &
  local p=$!
  echo "${label} ${p}" >> ${PIDS}
  wait ${p} || { note "FAILED ${label}"; exit 1; }
  note "${label} done"
}

run predict env DS_DEVICE=cpu ${T} -u -m learn.pipeline_fix real-predict --names ${TAG}
run goat-predict env DS_DEVICE=cpu ${T} -u -m learn.pipeline_fix goat-predict --names ${TAG}
run rows ${PY} -u -m learn.full_controls_c3 c3b-rows
note done
