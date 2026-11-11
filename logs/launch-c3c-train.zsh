#!/bin/zsh
# C3c's training (ledger phase_c3c, docs/full-controls-plan.md "C3c in detail"): C3's recipe (labels, masks) with the
# amp head trained on the amp that suits C3's own answer (the argmin of C3-cabS's per-amp renders on each unit's search
# half: GOAT's 214, BKS's 40; every other real row keeps -100), under C3c's own names: no inner run of its own (each FT_k
# takes C3's own inner run's E, the all-labels pair the median of the eight), the 8 FT_k two at a time, then the
# all-labels pair. Every run records C2's and the amp labels' sha256. Any failure stops the launcher. MPS, un-niced; one
# MPS job at a time: before each pair it waits while any other train-ft runs. Beside CPU renders, under Amendment 2's
# stop check.   zsh logs/launch-c3c-train.zsh /path/to/worktree
# A relaunch rotates the old log and PID file first; runs already written are skipped by train-ft itself.
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=.
TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/c3c-train.log
PIDS=${LOGS}/c3c-train-pids.txt
SEEDS=(20261042 20261043)
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)                  # a relaunch: the old log rotated aside
[[ -f ${PIDS} ]] && mv ${PIDS} ${PIDS}.$(date +%Y%m%d-%H%M%S)         # and the old PIDs: only this launch's are live
caffeinate -i -w $$ &
echo "launcher $$" >> ${PIDS}
echo "start $(date) $(git rev-parse --short HEAD)" >> ${L}

waitall() {    # wait on every PID given, then stop the launcher on any failure
  local tag=$1 rc=0; shift
  for p in "$@"; do wait ${p} || { rc=1; echo "FAILED ${tag} pid ${p} $(date)" >> ${L}; }; done
  (( rc == 0 )) || exit 1
}

mps_free() {   # one MPS job at a time: wait while another train-ft runs (this launcher's own pairs are all waited on)
  while pgrep -f "python[0-9.]* -u -m learn.pipeline_fix train-ft" > /dev/null; do   # the interpreter's, not a shell's
    echo "waiting: another train-ft runs (one MPS job) $(date)" >> ${L}
    sleep 60
  done
}

active=()
for k in 0 1 2 3; do
  for s in ${SEEDS}; do
    (( ${#active} == 0 )) && mps_free
    ${TORCH_PY} -u -m learn.pipeline_fix train-ft --real-fold ${k} --seed ${s} --ft-cap 300 --masked --c3c \
      > ${LOGS}/c3c-final-${k}-${s}.log 2>&1 &
    active+=($!)
    echo "final-${k}-${s} $!" >> ${PIDS}
    if (( ${#active} == 2 )); then
      waitall "final-${k}" ${active}
      active=()
    fi
  done
done
echo "final done $(date)" >> ${L}
mps_free
pids=()
for s in ${SEEDS}; do
  ${TORCH_PY} -u -m learn.pipeline_fix train-ft --seed ${s} --ft-cap 300 --masked --c3c > ${LOGS}/c3c-all-${s}.log 2>&1 &
  pids+=($!)
  echo "all-${s} $!" >> ${PIDS}
done
waitall all ${pids}
echo "all-labels done $(date)" >> ${L}
echo "done $(date)" >> ${L}
