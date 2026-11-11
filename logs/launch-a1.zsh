#!/bin/zsh
# A1 (ledger phase_a1, docs/full-controls-plan.md "A1 in detail"): the amp chosen by a stock-DI comparison. The units and
# stock DIs (a1-draw), each amp's answer through each stock DI in 3 shards (a1-render), then stops: the read waits for its
# amendment (the embedding pick, the review's Required 2). The render slots are file locks (PR #446). Any failure stops it.   zsh logs/launch-a1.zsh /path/to/worktree
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=. OMP_NUM_THREADS=1
PY=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/a1.log
PIDS=${LOGS}/a1-pids.txt
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)
[[ -f ${PIDS} ]] && mv ${PIDS} ${PIDS}.$(date +%Y%m%d-%H%M%S)
caffeinate -i -w $$ &
echo "launcher $$" >> ${PIDS}
note() { echo "$1 $(date)" >> ${L}; }
grep -q "acquire_render_slot" learn/direct_stems.py || { note "FAILED: this commit has no render-slot locks (PR #446)"; exit 1; }
note "start $(git rev-parse --short HEAD)"

run() {
  local label=$1; shift
  "$@" >> ${LOGS}/a1-${label}.log 2>&1 &
  local p=$!
  echo "${label} ${p}" >> ${PIDS}
  wait ${p} || { note "FAILED ${label}"; exit 1; }
  note "${label} done"
}

three() {
  local label=$1; shift
  local pids=() rc=0
  for k in 0 1 2; do
    "$@" --shard ${k}/3 > ${LOGS}/a1-${label}-${k}.log 2>&1 &
    pids+=($!)
  done
  echo "${label} ${pids}" >> ${PIDS}
  for p in ${pids}; do wait ${p} || { rc=1; note "FAILED ${label} pid ${p}"; }; done
  (( rc == 0 )) || exit 1
  note "${label} done"
}

run draw ${PY} -u -m learn.amp_di_compare a1-draw
three render ${PY} -u -m learn.amp_di_compare a1-render
note "renders done; the read (a1-rows) waits for the amendment's review"
note done
