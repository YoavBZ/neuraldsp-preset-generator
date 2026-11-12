#!/bin/zsh
# LS (ledger phase_ls, docs/full-controls-plan.md "LS in detail"): the loudness step. The items (C4's 18 and A3's 18), S's
# loudness on each amp and class through the stock DIs, each item's renders in 3 shards (the answer through the stock DIs,
# then S, the unmatched and the matched answer through its own DI), then the report. No model runs. The render slots are
# file locks (PR #446). Any failure stops it.   zsh logs/launch-ls.zsh /path/to/worktree
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=. OMP_NUM_THREADS=1
PY=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/ls.log
PIDS=${LOGS}/ls-pids.txt
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)
[[ -f ${PIDS} ]] && mv ${PIDS} ${PIDS}.$(date +%Y%m%d-%H%M%S)
caffeinate -i -w $$ &
echo "launcher $$" >> ${PIDS}
note() { echo "$1 $(date)" >> ${L}; }
grep -q "acquire_render_slot" learn/direct_stems.py || { note "FAILED: this commit has no render-slot locks (PR #446)"; exit 1; }
note "start $(git rev-parse --short HEAD)"

run() {
  local label=$1; shift
  "$@" >> ${LOGS}/ls-${label}.log 2>&1 &
  local p=$!
  echo "${label} ${p}" >> ${PIDS}
  wait ${p} || { note "FAILED ${label}"; exit 1; }
  note "${label} done"
}

three() {
  local label=$1; shift
  local pids=() rc=0
  for k in 0 1 2; do
    "$@" --shard ${k}/3 > ${LOGS}/ls-${label}-${k}.log 2>&1 &
    pids+=($!)
  done
  echo "${label} ${pids}" >> ${PIDS}
  for p in ${pids}; do wait ${p} || { rc=1; note "FAILED ${label} pid ${p}"; }; done
  (( rc == 0 )) || exit 1
  note "${label} done"
}

run draw ${PY} -u -m learn.loudness_step ls-draw
run table ${PY} -u -m learn.loudness_step ls-table
three render ${PY} -u -m learn.loudness_step ls-render
run report ${PY} -u -m learn.loudness_step ls-report
note done
