#!/bin/zsh
# C2r (ledger phase_c2r, docs/full-controls-plan.md "C2r and C3r in detail"): waits for C2b's launcher to exit (its PID,
# the last "launcher" line of logs/c2b-pids.txt; once it has exited the render slots are free, whatever its outcome,
# and `_wait_cap` guards the cap), then the draw (zero renders), the search in C2R_SHARDS shards at once (default 5,
# Amendment 2; each passes --cap so the 5 start together; C2's per-record recipe, the panel's step 0 first), then the
# report (zero renders). Any failure stops it. A draw already made is not redone (a relaunch after a stop resumes).
# A relaunch moves its own old log aside first.
#   zsh logs/launch-c2r.zsh /path/to/worktree-at-merged-main
# A resume after a failed shard: the same command once c2r/records.json exists fails at the draw ("drawn once"); run the
# named shards by hand instead (each skips records already written and resumes a saved step 1 at step 2), then
# c2r-report. After a systematic miss at step 0 (3 of a shard's first 5 panel records refused), run c2r-aside first:
# it moves the refused records aside (never deletes them), so they are searched again.
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=. OMP_NUM_THREADS=1
PY=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/c2r.log
PIDS=${LOGS}/c2r-pids.txt
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)
caffeinate -i -w $$ &
echo "launcher $$ $(date)" >> ${PIDS}
note() { echo "$1 $(date)" >> ${L}; }
note "waiting for C2b"
BP=$(awk '$1 == "launcher" {p = $2} END {print p}' ${LOGS}/c2b-pids.txt 2>/dev/null)
if [[ -z ${BP} ]]; then
  note "FAILED: no C2b launcher PID in c2b-pids.txt; C2r not started"
  exit 1
fi
# alive while that PID still runs launch-c2b.zsh (a reused PID running something else counts as exited)
while ps -p ${BP} -o command= 2>/dev/null | grep -q "launch-c2b"; do sleep 60; done
LAST=$(tail -1 ${LOGS}/c2b.log 2>/dev/null)
case ${LAST} in
  done*) note "C2b's launcher ${BP} exited: done" ;;
  *FAILED*) note "C2b's launcher ${BP} exited: failed (${LAST})" ;;
  *) note "C2b's launcher ${BP} exited: other (${LAST})" ;;
esac
note "start $(git rev-parse --short HEAD)"

if [[ -f ${HOME}/ndsp-presets/learn/trusted-data/pipeline-fix/c2r/records.json ]]; then
  note "draw exists: resuming (each shard skips the records written and resumes a saved step 1)"
else
  ${PY} -u -m learn.full_controls_c2r c2r-draw >> ${LOGS}/c2r-draw.log 2>&1 || { note "FAILED draw"; exit 1; }
  note "draw done"
fi

N=${C2R_SHARDS:-5}                     # Amendment 2 (phase_c2r_a2): 5 render processes, 3 on a fallback; each its own shard
(( N >= 1 && N <= 5 )) || { note "FAILED: C2R_SHARDS ${N} is not 1 to 5"; exit 1; }
note "search on ${N} shards"
pids=() rc=0
for k in $(seq 0 $(( N - 1 ))); do
  ${PY} -u -m learn.full_controls_c2r c2r-search --shard ${k}/${N} --cap ${N} >> ${LOGS}/c2r-search-${k}.log 2>&1 &
  pids+=($!)
done
echo "search ${pids}" >> ${PIDS}
for p in ${pids}; do wait ${p} || { rc=1; note "FAILED search pid ${p}"; }; done
(( rc == 0 )) || exit 1
note "search done"

${PY} -u -m learn.full_controls_c2r c2r-report >> ${LOGS}/c2r-report.log 2>&1 || { note "FAILED report"; exit 1; }
note "done"
