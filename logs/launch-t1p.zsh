#!/bin/zsh
# T1's arm P (ledger phase_t1p, docs/full-controls-plan.md "T1 in detail", arm P): waits for T1's launcher to write
# "done" (its read first; the MPS free), then the 40 items, their candidates through each item's own DI in 3 render
# shards while X-LANCE re-separates (MPS, one job), then the read. Any failure stops it.
#   zsh logs/launch-t1p.zsh /path/to/worktree
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=. OMP_NUM_THREADS=1
PY=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
MSST=~/ndsp-presets/tools/msst-venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/t1p.log
PIDS=${LOGS}/t1p-pids.txt
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)
[[ -f ${PIDS} ]] && mv ${PIDS} ${PIDS}.$(date +%Y%m%d-%H%M%S)
caffeinate -i -w $$ &
echo "launcher $$" >> ${PIDS}
note() { echo "$1 $(date)" >> ${L}; }
grep -q "acquire_render_slot" learn/direct_stems.py || { note "FAILED: this commit has no render-slot locks (PR #446)"; exit 1; }
note "start $(git rev-parse --short HEAD)"
note "waiting for T1's read"
until [[ $(tail -1 ${LOGS}/t1.log 2>/dev/null) == done* ]]; do
  [[ $(tail -1 ${LOGS}/t1.log 2>/dev/null) == *FAILED* ]] && { note "T1 failed: arm P doesn't run"; exit 1; }
  sleep 60
done

${PY} -u -m learn.fx_t1p t1p-draw >> ${LOGS}/t1p-draw.log 2>&1 || { note "FAILED draw"; exit 1; }
note "draw done"
env PYTORCH_ENABLE_MPS_FALLBACK=1 ${MSST} -u -m learn.fx_t1p t1p-separate --device mps >> ${LOGS}/t1p-separate.log 2>&1 &
SEPP=$!
echo "separate ${SEPP}" >> ${PIDS}
pids=() rc=0
for k in 0 1 2; do
  ${PY} -u -m learn.fx_t1p t1p-render --shard ${k}/3 > ${LOGS}/t1p-render-${k}.log 2>&1 &
  pids+=($!)
done
echo "render ${pids}" >> ${PIDS}
for p in ${pids}; do wait ${p} || { rc=1; note "FAILED render pid ${p}"; }; done
(( rc == 0 )) || { kill ${SEPP} 2>/dev/null; exit 1; }
note "render done"
wait ${SEPP} || { note "FAILED separate"; exit 1; }
note "separate done"
${PY} -u -m learn.fx_t1p t1p-read >> ${LOGS}/t1p-read.log 2>&1 || { note "FAILED read"; exit 1; }
note done
