#!/bin/zsh
# C3s's training (ledger phase_c3s, docs/full-controls-plan.md "C3s in detail"), C3i's (b) follow-up: C3's recipe (C2's
# labels, C3's masks) with the core's share of the loss restored (`full_space.loss_split`), under C3s's own names: the 8
# inner fold-and-seed runs two at a time, the 8 FT_k two at a time (each on its own inner run's E), then the all-labels
# pair. It waits for C3r's training launcher to exit (its PID, given) and for no other train-ft to run: one MPS job at a
# time. Any failure stops the launcher. MPS, un-niced; beside CPU renders, under Amendment 2's stop check.
#   zsh logs/launch-c3s-train.zsh /path/to/worktree C3R_TRAIN_LAUNCHER_PID
# A relaunch rotates the old c3s-train.log first; runs already written are skipped by train-ft itself.
setopt no_bg_nice
W=${1:?the worktree to run from}
WAIT_PID=${2:?the C3r training launcher PID to wait for}
cd "${W}" || exit 1
export PYTHONPATH=.
TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/c3s-train.log
PIDS=${LOGS}/c3s-train-pids.txt
SEEDS=(20261042 20261043)
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)                  # a relaunch: the old log rotated aside
[[ -f ${PIDS} ]] && mv ${PIDS} ${PIDS}.$(date +%Y%m%d-%H%M%S)         # and the old PIDs: only this launch's are live
caffeinate -i -w $$ &
echo "launcher $$" >> ${PIDS}
echo "waiting for pid ${WAIT_PID} (C3r's training) and a free MPS $(date)" >> ${L}
while kill -0 ${WAIT_PID} 2>/dev/null || pgrep -f "python[0-9.]* -u -m learn.pipeline_fix train-ft" > /dev/null; do sleep 60; done
echo "start $(date) $(git rev-parse --short HEAD)" >> ${L}

waitall() {    # wait on every PID given, then stop the launcher on any failure
  local tag=$1 rc=0; shift
  for p in "$@"; do wait ${p} || { rc=1; echo "FAILED ${tag} pid ${p} $(date)" >> ${L}; }; done
  (( rc == 0 )) || exit 1
}

ft_pass() {    # one pass over the 8 fold-and-seed pairs, two at a time; extra flags in $@
  local tag=$1; shift
  local active=()
  for k in 0 1 2 3; do
    for s in ${SEEDS}; do
      ${TORCH_PY} -u -m learn.pipeline_fix train-ft "$@" --real-fold ${k} --seed ${s} --ft-cap 300 --masked --c3s \
        > ${LOGS}/c3s-${tag}-${k}-${s}.log 2>&1 &
      active+=($!)
      echo "${tag}-${k}-${s} $!" >> ${PIDS}
      if (( ${#active} == 2 )); then
        waitall "${tag}-${k}" ${active}
        active=()
      fi
    done
  done
  echo "${tag} done $(date)" >> ${L}
}

ft_pass inner --inner
ft_pass final
pids=()
for s in ${SEEDS}; do
  ${TORCH_PY} -u -m learn.pipeline_fix train-ft --seed ${s} --ft-cap 300 --masked --c3s > ${LOGS}/c3s-all-${s}.log 2>&1 &
  pids+=($!)
  echo "all-${s} $!" >> ${PIDS}
done
waitall all ${pids}
echo "all-labels done $(date)" >> ${L}
echo "done $(date)" >> ${L}
