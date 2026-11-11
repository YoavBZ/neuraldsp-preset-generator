#!/bin/zsh
# A1's read (ledger phase_a1, docs/full-controls-plan.md "A1 in detail", its amendment): after the renders (logs/a1.log
# "done"), the embedding features (a1-embed: the C3 fold models' pooled body features, CPU, zero renders), then the rows
# (a1-rows). No render. Any failure stops it.   zsh logs/launch-a1-read.zsh /path/to/worktree
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=. OMP_NUM_THREADS=1
PY=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
T=~/ndsp-presets/tools/demucs-venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/a1-read.log
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)
caffeinate -i -w $$ &
note() { echo "$1 $(date)" >> ${L}; }
note "waiting for A1's renders"
until [[ $(tail -1 ${LOGS}/a1.log 2>/dev/null) == (done*|*FAILED*) ]]; do sleep 60; done
[[ $(tail -1 ${LOGS}/a1.log) == done* ]] || { note "A1's renders did not finish; no read"; exit 1; }
note "start $(git rev-parse --short HEAD)"
env DS_DEVICE=cpu ${T} -u -m learn.amp_di_compare a1-embed >> ${LOGS}/a1-embed.log 2>&1 || { note "FAILED embed"; exit 1; }
note "embed done"
${PY} -u -m learn.amp_di_compare a1-rows >> ${LOGS}/a1-rows.log 2>&1 || { note "FAILED rows"; exit 1; }
note done
