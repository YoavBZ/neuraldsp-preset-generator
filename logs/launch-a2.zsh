#!/bin/zsh
# A2 (ledger phase_a2, docs/full-controls-plan.md "A2 in detail"): A1's stock-DI pick, frozen, on R-all's out-of-fold
# answers. R-all's answers on all three amps (a2-predict, CPU), the other two amps through each unit's DI (a2-judge, 3
# shards), each amp's answer through A1's stock DIs (a2-render, 3 shards), A1's floored features (a2-embed, CPU), then
# the read (a2-rows). The render slots are file locks (PR #446). Any failure stops it.   zsh logs/launch-a2.zsh /path/to/wt
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=. OMP_NUM_THREADS=1
PY=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
T=~/ndsp-presets/tools/demucs-venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/a2.log
PIDS=${LOGS}/a2-pids.txt
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)
[[ -f ${PIDS} ]] && mv ${PIDS} ${PIDS}.$(date +%Y%m%d-%H%M%S)
caffeinate -i -w $$ &
echo "launcher $$" >> ${PIDS}
note() { echo "$1 $(date)" >> ${L}; }
grep -q "acquire_render_slot" learn/direct_stems.py || { note "FAILED: this commit has no render-slot locks (PR #446)"; exit 1; }
note "start $(git rev-parse --short HEAD)"

run() {
  local label=$1; shift
  "$@" >> ${LOGS}/a2-${label}.log 2>&1 &
  local p=$!
  echo "${label} ${p}" >> ${PIDS}
  wait ${p} || { note "FAILED ${label}"; exit 1; }
  note "${label} done"
}

three() {
  local label=$1; shift
  local pids=() rc=0
  for k in 0 1 2; do
    "$@" --shard ${k}/3 > ${LOGS}/a2-${label}-${k}.log 2>&1 &
    pids+=($!)
  done
  echo "${label} ${pids}" >> ${PIDS}
  for p in ${pids}; do wait ${p} || { rc=1; note "FAILED ${label} pid ${p}"; }; done
  (( rc == 0 )) || exit 1
  note "${label} done"
}

run predict env DS_DEVICE=cpu ${T} -u -m learn.amp_di_compare_r a2-predict
three judge ${PY} -u -m learn.amp_di_compare_r a2-judge
three render ${PY} -u -m learn.amp_di_compare_r a2-render
run embed env DS_DEVICE=cpu ${T} -u -m learn.amp_di_compare_r a2-embed
run rows ${PY} -u -m learn.amp_di_compare_r a2-rows
note done
