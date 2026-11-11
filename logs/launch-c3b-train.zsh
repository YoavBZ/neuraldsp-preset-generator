#!/bin/zsh
# C3b's training (ledger phase_c3b, docs/full-controls-plan.md "C3b in detail"): C3's recipe (labels, masks) with the
# amp head trained on each real row's unit amp label (the stored recipe: GOAT's C2b argmin, BKS's stored argmin), under
# C3b's own names: the 8 inner fold-and-seed runs two at a time, the 8 FT_k two at a time (each on its own inner run's
# E), then the all-labels pair. Every run refuses until C2's 520 records are written, records C2's and the amp labels'
# sha256, and chains only on runs made on the same. Any failure stops the launcher. MPS, un-niced, with no other MPS job
# meanwhile; it runs beside C2r's 5 CPU render shards, and the executor stops it by its recorded PIDs if their summed
# renders per hour in its first 20 min fall more than 20% below C2r's measured 11,495.
#   zsh logs/launch-c3b-train.zsh /path/to/worktree
# A relaunch rotates the old log and PID file first; runs already written are skipped by train-ft itself.
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=.
TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/c3b-train.log
PIDS=${LOGS}/c3b-train-pids.txt
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

ft_pass() {    # one pass over the 8 fold-and-seed pairs, two at a time; extra flags in $@
  local tag=$1; shift
  local active=()
  for k in 0 1 2 3; do
    for s in ${SEEDS}; do
      ${TORCH_PY} -u -m learn.pipeline_fix train-ft "$@" --real-fold ${k} --seed ${s} --ft-cap 300 --masked --c3b \
        > ${LOGS}/c3b-${tag}-${k}-${s}.log 2>&1 &
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
  ${TORCH_PY} -u -m learn.pipeline_fix train-ft --seed ${s} --ft-cap 300 --masked --c3b > ${LOGS}/c3b-all-${s}.log 2>&1 &
  pids+=($!)
  echo "all-${s} $!" >> ${PIDS}
done
waitall all ${pids}
echo "all-labels done $(date)" >> ${L}
echo "done $(date)" >> ${L}
