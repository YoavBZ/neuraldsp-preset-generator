#!/bin/zsh
# T1 (ledger phase_t1, docs/full-controls-plan.md "T1 in detail"): the masking-channel render-and-compare test on F52's
# strong-third delay-ons. The items, the candidates in 3 render shards (CPU, at most 3 render processes; the render slots
# are file locks, PR #446) while X-LANCE re-separates each item as its candidates land (MPS, one job), then the read.
# Any failure stops it.   zsh logs/launch-t1.zsh /path/to/worktree
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=. OMP_NUM_THREADS=1
PY=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
MSST=~/ndsp-presets/tools/msst-venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/t1.log
PIDS=${LOGS}/t1-pids.txt
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)
[[ -f ${PIDS} ]] && mv ${PIDS} ${PIDS}.$(date +%Y%m%d-%H%M%S)
caffeinate -i -w $$ &
echo "launcher $$" >> ${PIDS}
note() { echo "$1 $(date)" >> ${L}; }
grep -q "acquire_render_slot" learn/direct_stems.py || { note "FAILED: this commit has no render-slot locks (PR #446)"; exit 1; }
note "start $(git rev-parse --short HEAD)"

${PY} -u -m learn.fx_t1 t1-draw >> ${LOGS}/t1-draw.log 2>&1 || { note "FAILED draw"; exit 1; }
note "draw done"
env PYTORCH_ENABLE_MPS_FALLBACK=1 ${MSST} -u -m learn.fx_t1 t1-separate --device mps >> ${LOGS}/t1-separate.log 2>&1 &
SEPP=$!
echo "separate ${SEPP}" >> ${PIDS}
pids=() rc=0
for k in 0 1 2; do
  ${PY} -u -m learn.fx_t1 t1-render --shard ${k}/3 > ${LOGS}/t1-render-${k}.log 2>&1 &
  pids+=($!)
done
echo "render ${pids}" >> ${PIDS}
for p in ${pids}; do wait ${p} || { rc=1; note "FAILED render pid ${p}"; }; done
(( rc == 0 )) || { kill ${SEPP} 2>/dev/null; exit 1; }
note "render done"
wait ${SEPP} || { note "FAILED separate"; exit 1; }
note "separate done"
${PY} -u -m learn.fx_t1 t1-read >> ${LOGS}/t1-read.log 2>&1 || { note "FAILED read"; exit 1; }
note done
