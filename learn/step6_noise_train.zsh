#!/bin/zsh
# Step 6's stage N training (docs/stem-finetune-plan.md section 5.2; ledger pipeline-fix phase_s6_noise): R-rep's 8
# inner runs, its 8 FT_k (each at its own inner run's E), then the same-seed replay's 2, one MPS job at a time. Run from
# the repo root of a checkout at merged main, after `stem_finetune stage0` read S0-ok. A failed run stops the chain; a
# finished run's record makes its rerun a no-op (`train-ft`: "exists: nothing to do"). The disk guard (31 GB, decimal)
# is checked before every run. Logs: PF/step6/logs/.
setopt no_bg_nice err_exit
TORCH_PY=${TORCH_PY:-$HOME/ndsp-presets/tools/demucs-venv/bin/python}
PF=$HOME/ndsp-presets/learn/trusted-data/pipeline-fix
LOG=${PF}/step6/logs
mkdir -p ${LOG}
${TORCH_PY} -c 'from learn import stem_finetune as S; S.stage0_ok()' || { echo "stage 0 has not read S0-ok"; exit 1 }

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

for k in 0 1 2 3; do
  for sd in 20261181 20261182; do
    run --c3r-rep rep --seed ${sd} --real-fold ${k} --inner
  done
done
for k in 0 1 2 3; do
  for sd in 20261181 20261182; do
    run --c3r-rep rep --seed ${sd} --real-fold ${k}
  done
done
run --c3r-rep replay --seed 20261043 --real-fold 3 --inner
run --c3r-rep replay --seed 20261043 --real-fold 3
echo "$(date '+%F %T') ALL DONE" >> ${LOG}/train.log
