#!/bin/zsh
# A3 (ledger phase_a3, docs/full-controls-plan.md "A3 in detail"): the ear check of A2's declared product step. The items
# (A2's deciding units where the stock-DI pick and R-all's amp head differ), R-all's stored preset on each amp through the
# unit's DI as held-half clips in 3 shards, then the page. No model runs. The render slots are file locks (PR #446). Any
# failure stops it.   zsh logs/launch-a3.zsh /path/to/worktree
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=. OMP_NUM_THREADS=1
PY=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/a3.log
PIDS=${LOGS}/a3-pids.txt
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)
[[ -f ${PIDS} ]] && mv ${PIDS} ${PIDS}.$(date +%Y%m%d-%H%M%S)
caffeinate -i -w $$ &
echo "launcher $$" >> ${PIDS}
note() { echo "$1 $(date)" >> ${L}; }
grep -q "acquire_render_slot" learn/direct_stems.py || { note "FAILED: this commit has no render-slot locks (PR #446)"; exit 1; }
note "start $(git rev-parse --short HEAD)"

run() {
  local label=$1; shift
  "$@" >> ${LOGS}/a3-${label}.log 2>&1 &
  local p=$!
  echo "${label} ${p}" >> ${PIDS}
  wait ${p} || { note "FAILED ${label}"; exit 1; }
  note "${label} done"
}

three() {
  local label=$1; shift
  local pids=() rc=0
  for k in 0 1 2; do
    "$@" --shard ${k}/3 > ${LOGS}/a3-${label}-${k}.log 2>&1 &
    pids+=($!)
  done
  echo "${label} ${pids}" >> ${PIDS}
  for p in ${pids}; do wait ${p} || { rc=1; note "FAILED ${label} pid ${p}"; }; done
  (( rc == 0 )) || exit 1
  note "${label} done"
}

run draw ${PY} -u -m learn.a3_ear a3-draw
three render ${PY} -u -m learn.a3_ear a3-render
run page ${PY} -u -m learn.a3_ear a3-page
note done
