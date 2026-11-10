#!/bin/zsh
# C3r's read (ledger phase_c3r, docs/full-controls-plan.md "C2r and C3r in detail"): after C3r's training (the last line
# of logs/c3r-train.log "done"), both arms' answers (CPU, zero renders), their renders in 3 shards at once (at most 3
# render processes; each answer a fresh primed process, `_wait_cap` guarding the cap), then the report and the
# adoption rule (zero renders). Any failure stops it.   zsh logs/launch-c3r-read.zsh /path/to/worktree-at-merged-main
# A resume: the same command; predict rewrites the answers (the same models give the same answers), and each render
# shard skips the records already written from those answers.
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=. OMP_NUM_THREADS=1
T=~/ndsp-presets/tools/demucs-venv/bin/python
PY=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/c3r-read.log
PIDS=${LOGS}/c3r-read-pids.txt
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)
caffeinate -i -w $$ &
echo "launcher $$ $(date)" >> ${PIDS}
note() { echo "$1 $(date)" >> ${L}; }
note "waiting for C3r's training"
until [[ $(tail -1 ${LOGS}/c3r-train.log 2>/dev/null) == done* ]]; do
  [[ $(tail -1 ${LOGS}/c3r-train.log 2>/dev/null) == *FAILED* ]] && { note "C3r's training failed; no read"; exit 1; }
  sleep 60
done
note "start $(git rev-parse --short HEAD)"
for arm in all ctl; do
  env DS_DEVICE=cpu ${T} -u -m learn.full_controls_c3r c3r-predict --arm ${arm} >> ${LOGS}/c3r-predict-${arm}.log 2>&1 \
    || { note "FAILED predict ${arm}"; exit 1; }
done
note "answers done"
pids=() rc=0
for k in 0 1 2; do
  ${PY} -u -m learn.full_controls_c3r c3r-render --arms all,ctl --shard ${k}/3 >> ${LOGS}/c3r-render-${k}.log 2>&1 &
  pids+=($!)
done
echo "render ${pids}" >> ${PIDS}
for p in ${pids}; do wait ${p} || { rc=1; note "FAILED render pid ${p}"; }; done
(( rc == 0 )) || exit 1
note "renders done"
${PY} -u -m learn.full_controls_c3r c3r-report >> ${LOGS}/c3r-report.log 2>&1 || { note "FAILED report"; exit 1; }
note "done"
