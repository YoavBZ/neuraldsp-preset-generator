#!/bin/zsh
# The learning-curve diagnostic's training (docs/half-data-plan.md; ledger pipeline-fix phase_s6_half), one arm per call:
# `half_data_train.zsh a` (half A, R-all's W states and seeds) first; `half_data_train.zsh b` (half B, R-rep's) only after
# `half_data report-a` read A-go (train-ft refuses otherwise). Each arm: 8 inner runs, then 8 FT_k, one MPS job at a time.
# Run from the repo root of a checkout at merged main, after `half_data select` saved the halves. A failed run stops the
# chain; a finished run's record makes its rerun a no-op (`train-ft`: "exists: nothing to do"). The disk guard (31 GB,
# decimal) is checked before every run. Logs and the launcher's PID file: PF/step6/half/logs/.
setopt no_bg_nice err_exit
TORCH_PY=${TORCH_PY:-$HOME/ndsp-presets/tools/demucs-venv/bin/python}
PF=$HOME/ndsp-presets/learn/trusted-data/pipeline-fix
LOG=${PF}/step6/half/logs
mkdir -p ${LOG}
ARM=${1:?usage: half_data_train.zsh a|b}
[[ ${ARM} == a || ${ARM} == b ]] || { echo "arm a or b"; exit 1 }
echo $$ > ${LOG}/train-${ARM}.pid
${TORCH_PY} -c 'from learn import half_data as H; from learn import stem_finetune as S; S.stage0_ok(); H.load_selection()' \
  || { echo "stage 0 has not read S0-ok, or no selection"; exit 1 }

guard() {
  local free_kb=$(df -k $HOME | awk 'NR==2 {print $4}')
  if (( free_kb * 1024 < 31000000000 )); then
    echo "$(date '+%F %T') DISK GUARD: ${free_kb} KB free" >> ${LOG}/train.log
    exit 1
  fi
}

run() {
  guard
  local tag=${(j:_:)@}
  tag=${tag//-/}
  echo "$(date '+%F %T') START $*" >> ${LOG}/train.log
  caffeinate -i ${TORCH_PY} -m learn.pipeline_fix train-ft --masked --ft-cap 300 --c3r all "$@" >> ${LOG}/train-${tag}.log 2>&1
  echo "$(date '+%F %T') DONE $*" >> ${LOG}/train.log
}

arm() {
  local a=$1; shift
  for k in 0 1 2 3; do
    for sd in "$@"; do
      run --c3r-half ${a} --seed ${sd} --real-fold ${k} --inner
    done
  done
  for k in 0 1 2 3; do
    for sd in "$@"; do
      run --c3r-half ${a} --seed ${sd} --real-fold ${k}
    done
  done
}

if [[ ${ARM} == a ]]; then
  arm a 20261042 20261043
else
  ${TORCH_PY} -c 'from learn import half_data as H; H.stage_a_go()' || { echo "report-a has not read A-go"; exit 1 }
  arm b 20261181 20261182
fi
echo "$(date '+%F %T') ARM ${ARM} DONE" >> ${LOG}/train.log
