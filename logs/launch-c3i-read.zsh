#!/bin/zsh
# C3i's read (ledger phase_c3i, docs/full-controls-plan.md "C3i in detail"), after C3i's training (logs/c3i-train.log
# "done") and after C2r (logs/c2r.log "done"), so its renders take a free slot (at most 3 render processes) before
# C3r's read: C3i's answers (real-predict, goat-predict, N12's h4-answers, FTm's hold), their renders in 3 shards (BKS,
# GOAT, N12), N12's rows (h4-wide), the reports (C3i - FTm, C3 core - C3i, C3i - S) and the declared reading (c3i-rows).
# Any failure stops it.   zsh logs/launch-c3i-read.zsh /path/to/worktree
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=. OMP_NUM_THREADS=1
PY=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
T=~/ndsp-presets/tools/demucs-venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/c3i-read.log
PIDS=${LOGS}/c3i-read-pids.txt
TAG=C3i
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)                  # a relaunch: the old log rotated aside
[[ -f ${PIDS} ]] && mv ${PIDS} ${PIDS}.$(date +%Y%m%d-%H%M%S)         # and the old PIDs: only this launch's are live
caffeinate -i -w $$ &
echo "launcher $$" >> ${PIDS}
note() { echo "$1 $(date)" >> ${L}; }
note "waiting for C3i's training and C2r"
until [[ $(tail -1 ${LOGS}/c3i-train.log 2>/dev/null) == (done*|*FAILED*|*fail*) ]]; do sleep 60; done
[[ $(tail -1 ${LOGS}/c3i-train.log) == done* ]] || { note "C3i's training did not finish; the read does not start"; exit 1; }
until [[ $(tail -1 ${LOGS}/c2r.log 2>/dev/null) == (done*|*FAILED*) ]]; do sleep 60; done
[[ $(tail -1 ${LOGS}/c2r.log) == done* ]] || { note "C2r did not finish; the read does not start"; exit 1; }
note "start $(git rev-parse --short HEAD)"

run() {        # one foreground step, logged; stop on failure
  local label=$1; shift
  "$@" >> ${LOGS}/c3i-read-${label}.log 2>&1 &
  local p=$!
  echo "${label} ${p}" >> ${PIDS}
  wait ${p} || { note "FAILED ${label}"; exit 1; }
  note "${label} done"
}

three() {      # 3 shards at once (the render cap), every one waited on before a failure stops the launcher
  local label=$1; shift
  local pids=() rc=0
  for k in 0 1 2; do
    "$@" --shard ${k}/3 > ${LOGS}/c3i-read-${label}-${k}.log 2>&1 &
    pids+=($!)
  done
  echo "${label} ${pids}" >> ${PIDS}
  for p in ${pids}; do wait ${p} || { rc=1; note "FAILED ${label} pid ${p}"; }; done
  (( rc == 0 )) || exit 1
  note "${label} done"
}

run predict env DS_DEVICE=cpu ${T} -u -m learn.pipeline_fix real-predict --names ${TAG}
run goat-predict env DS_DEVICE=cpu ${T} -u -m learn.pipeline_fix goat-predict --names ${TAG}
three real ${PY} -u -m learn.pipeline_fix real-render --names ${TAG}
three goat ${PY} -u -m learn.pipeline_fix goat-render --names ${TAG}
run n12-answers env DS_DEVICE=cpu ${T} -u -m learn.score_ear h4-answers --tags ${TAG}
three n12 ${PY} -u -m learn.score_ear h4-render --tags ${TAG}
run n12-rows ${PY} -u -m learn.score_ear h4-wide ${LOGS}/c3i-n12.json --tags ${TAG}
PAIRS=$(${PY} -c "from learn import full_controls_c3 as X; print(X.c3i_pairs())")
run real-report ${PY} -u -m learn.pipeline_fix real-report --pairs ${PAIRS} --label c3i
run goat-report ${PY} -u -m learn.pipeline_fix goat-report --pairs ${PAIRS} --label c3i
run rows ${PY} -u -m learn.full_controls_c3 c3i-rows
note done
