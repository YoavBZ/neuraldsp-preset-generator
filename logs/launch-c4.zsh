#!/bin/zsh
# C4 (ledger phase_c4, docs/full-controls-plan.md "C4 in detail"): batch 3's 18 trusted units, never training rows. The lag
# pass (capture_labels --batch 3 search --lags-only: S on each amp, no label), their read inputs (build-dfix-real
# --captures --capture-batch 3, CPU), the items, each preset's answer (CPU), the held-half clips in 3 shards, then the
# page. The render slots are file locks (PR #446). Any failure stops it.   zsh logs/launch-c4.zsh /path/to/worktree
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=. OMP_NUM_THREADS=1
PY=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
T=~/ndsp-presets/tools/demucs-venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/c4.log
PIDS=${LOGS}/c4-pids.txt
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)
[[ -f ${PIDS} ]] && mv ${PIDS} ${PIDS}.$(date +%Y%m%d-%H%M%S)
caffeinate -i -w $$ &
echo "launcher $$" >> ${PIDS}
note() { echo "$1 $(date)" >> ${L}; }
grep -q "acquire_render_slot" learn/direct_stems.py || { note "FAILED: this commit has no render-slot locks (PR #446)"; exit 1; }
note "start $(git rev-parse --short HEAD)"

run() {
  local label=$1; shift
  "$@" >> ${LOGS}/c4-${label}.log 2>&1 &
  local p=$!
  echo "${label} ${p}" >> ${PIDS}
  wait ${p} || { note "FAILED ${label}"; exit 1; }
  note "${label} done"
}

three() {
  local label=$1; shift
  local pids=() rc=0
  for k in 0 1 2; do
    "$@" --shard ${k}/3 > ${LOGS}/c4-${label}-${k}.log 2>&1 &
    pids+=($!)
  done
  echo "${label} ${pids}" >> ${PIDS}
  for p in ${pids}; do wait ${p} || { rc=1; note "FAILED ${label} pid ${p}"; }; done
  (( rc == 0 )) || exit 1
  note "${label} done"
}

three lags ${PY} -u -m learn.capture_labels --batch 3 search --lags-only
run inputs ${PY} -u -m learn.pipeline_fix build-dfix-real --captures --capture-batch 3
run draw ${PY} -u -m learn.c4_ear c4-draw
run answers env DS_DEVICE=cpu ${T} -u -m learn.c4_ear c4-answers
three render ${PY} -u -m learn.c4_ear c4-render
run page ${PY} -u -m learn.c4_ear c4-page
note done
