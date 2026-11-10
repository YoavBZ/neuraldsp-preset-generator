#!/bin/zsh
# C3r's training (ledger phase_c3r, docs/full-controls-plan.md "C2r and C3r in detail"): after C2r ends (logs/c2r.log's
# last line "done"), C3's decision exists (c3/decision.json, written by launch-c3-read.zsh's last step) and the DI scope's
# verdicts hold all 26 answers (Amendment 1, phase_c2r_a1: di-scope/verdicts.json, build f75f017f9d66), the panel's
# D_fix inputs (build-dfix-real --panel, CPU, zero renders), the zero-render check and the folds, then both arms of C3's
# recipe under C3r's names: R-all's and R-ctl's 8 inner runs, then their 8 FT_k (each on its own inner run's E), two at
# a time, then R-all's all-labels pair (R-ctl has none). Every run refuses until C2's 520 and C2r's records are written
# and C3's decision exists, and records their sha256. Any failure stops the launcher. MPS, un-niced.
#   zsh logs/launch-c3r-train.zsh /path/to/worktree-at-merged-main
# A relaunch rotates the old c3r-train.log first, so launch-c3r-read.zsh never reads a stale line. A run that exists
# is skipped (train-ft prints "exists: nothing to do"), so a relaunch resumes.
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=.
TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
PY=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
PF=/Users/yoavbz/ndsp-presets/learn/trusted-data/pipeline-fix
L=${LOGS}/c3r-train.log
PIDS=${LOGS}/c3r-train-pids.txt
SEEDS=(20261042 20261043)
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)
caffeinate -i -w $$ &
echo "launcher $$ $(date)" >> ${PIDS}
note() { echo "$1 $(date)" >> ${L}; }
scope_ready() {  # Amendment 1: the DI scope's verdicts hold all the page's answers (di_scope.complete_refusal)
  ${PY} -c "import sys; from learn import di_scope as D; sys.exit(0 if D.complete_refusal() is None else 1)" > /dev/null 2>&1
}
note "waiting for C2r, C3's decision and the DI scope's answers"
until [[ $(tail -1 ${LOGS}/c2r.log 2>/dev/null) == done* && -f ${PF}/c3/decision.json ]] && scope_ready; do
  [[ $(tail -1 ${LOGS}/c2r.log 2>/dev/null) == *FAILED* ]] && { note "C2r failed; C3r does not train"; exit 1; }
  [[ $(tail -1 ${LOGS}/c3-read.log 2>/dev/null) == *FAILED* ]] && { note "C3's read failed: no decision; C3r does not train"; exit 1; }
  sleep 60
done
note "start $(git rev-parse --short HEAD)"
${PY} -u -m learn.pipeline_fix build-dfix-real --panel >> ${LOGS}/c3r-panel-inputs.log 2>&1 || { note "FAILED panel inputs"; exit 1; }
${PY} -u -m learn.full_controls_c3r c3r-check > ${LOGS}/c3r-check.log 2>&1 || { note "FAILED c3r-check"; exit 1; }
${PY} -u -m learn.full_controls_c3r c3r-folds > ${LOGS}/c3r-folds.log 2>&1 || { note "FAILED c3r-folds"; exit 1; }
note "panel inputs, check and folds written"

waitall() {    # wait on every PID given, then stop the launcher on any failure
  local tag=$1 rc=0; shift
  for p in "$@"; do wait ${p} || { rc=1; note "FAILED ${tag} pid ${p}"; }; done
  (( rc == 0 )) || exit 1
}

ft_pass() {    # one pass over an arm's 8 fold-and-seed pairs, two at a time; extra flags in $@
  local arm=$1 tag=$2; shift 2
  local active=()
  for k in 0 1 2 3; do
    for s in ${SEEDS}; do
      ${TORCH_PY} -u -m learn.pipeline_fix train-ft "$@" --real-fold ${k} --seed ${s} --ft-cap 300 --masked --c3r ${arm} \
        > ${LOGS}/c3r-${arm}-${tag}-${k}-${s}.log 2>&1 &
      active+=($!)
      echo "${arm}-${tag}-${k}-${s} $!" >> ${PIDS}
      if (( ${#active} == 2 )); then
        waitall "${arm}-${tag}-${k}" ${active}
        active=()
      fi
    done
  done
  note "${arm} ${tag} done"
}

ft_pass all inner --inner
ft_pass ctl inner --inner
ft_pass all final
ft_pass ctl final
pids=()
for s in ${SEEDS}; do
  ${TORCH_PY} -u -m learn.pipeline_fix train-ft --seed ${s} --ft-cap 300 --masked --c3r all > ${LOGS}/c3r-all-labels-${s}.log 2>&1 &
  pids+=($!)
  echo "all-labels-${s} $!" >> ${PIDS}
done
waitall all-labels ${pids}
note "all-labels done"
note "done"
