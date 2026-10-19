#!/bin/zsh
# docs/rebuild-tone-plan.md: the chained runner, unattended. Two lanes:
#   GPU (MPS, one training job at a time): stm then its matched control per fold (seed 0); then the
#     second seed of rank and its control per fold;
#   CPU/renders: the leak-free curve and C′+EQ now; after stm and its control: the zero-render gate,
#     the rebuilds (stm's arms only if the gate says so), TR1 renders of group 1; after the second
#     seed: its gate rows, rebuilds and TR1 renders; scoring, the 24-part diagnostic, the report;
#     the extension (TR2) by the declared rule, rescoring and the final report; "all done".
# The code's own gates hold the rest (stop files, the render cap, swap and disk guards, the arm
# checks, the comparator). Launch:
#   mkdir -p ~/ndsp-presets/learn/rebuild-tone/logs; setopt no_bg_nice
#   nohup caffeinate -i zsh learn/rebuild_tone_run.zsh > ~/ndsp-presets/learn/rebuild-tone/logs/run.out 2>&1 &
setopt no_bg_nice
REPO=${0:A:h:h}
cd $REPO
PY=$REPO/.venv/bin/python
TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
O=~/ndsp-presets/learn/rebuild-tone
L=$O/logs
mkdir -p $L
export PYTHONUNBUFFERED=1
log() { echo "$(date '+%F %T') $*" >> $L/run.log }
RUN=$$
log "start pid $RUN, commit $(git rev-parse --short HEAD), branch $(git branch --show-current)"

guard() {   # one training job at a time, memory and disk
  while true; do
    local free=$(df -g ~ | awk 'NR==2{print $4}')
    local mem=$(memory_pressure | awk -F': ' '/free percentage/{gsub("%","",$2); print $2}')
    local other=$(pgrep -f -- "-m learn\.[a-z_0-9]+ (fit|train)")
    if (( free >= 31 && mem >= 25 )) && [[ -z $other ]]; then return 0; fi
    log "GPU waiting: free ${free} GB, memory free ${mem}%, other training [${other//$'\n'/ }]"
    sleep 300
  done
}
train() {   # arm seed fold
  local d=$O/models-$1-s$2-f$3
  [[ -f $d/DONE ]] && { log "T $1 s$2 fold $3 already done"; return 0 }
  guard
  log "T $1 s$2 fold $3 start"
  OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 $TORCH_PY -u -m learn.rebuild_tone_train train --fold $3 --arm $1 --seed $2 \
      > $L/train-$1-s$2-f$3.log 2>&1 || { log "T $1 s$2 fold $3 FAILED (see train-$1-s$2-f$3.log)"; return 1 }
  log "T $1 s$2 fold $3 done: $(tail -1 $L/train-$1-s$2-f$3.log)"
}

# --- lane GPU ---------------------------------------------------------------------------------------
(
  for f in 0 1 2 3; do train stm 0 $f || { log "GPU STM FAILED"; exit 1 }; train ctl 0 $f || { log "GPU STM FAILED"; exit 1 }; done
  log "GPU: stm and its control trained"
  for f in 0 1 2 3; do train rank 1 $f || { log "GPU SEED FAILED"; exit 1 }; train ctl 1 $f || { log "GPU SEED FAILED"; exit 1 }; done
  log "GPU: second seed trained"
) &
laneG=$!
log "lane GPU: pid $laneG"

# --- lane CPU / renders -------------------------------------------------------------------------------
shards() {   # name stage arms; three shards, all must succeed
  local p=() ok=0
  for i in 0 1 2; do
    OMP_NUM_THREADS=1 $PY -u -m learn.rebuild_tone render --stage $2 --arms $3 --shard $i/3 > $L/render-$1-$i.log 2>&1 & p+=($!)
  done
  for q in $p; do wait $q || ok=1; done
  return $ok
}
current() { awk -v k=" start pid $RUN, " 'index($0, k) {n = NR} {l[NR] = $0} END {for (i = n; i && i <= NR; i++) print l[i]}' $L/run.log }   # this run's lines (from its last start line)
has() { current | grep -qxE "^.{19} $1$" }                        # an exact log line of this run
waitfor() {   # success-line failure-line: 0 on success, 1 on failure or if the GPU lane is gone without either
  while true; do
    has "$1" && return 0
    has "$2" && return 1
    if ! kill -0 $laneG 2>/dev/null; then
      has "$1" && return 0
      log "GPU lane gone without '$1' or '$2'"; return 1
    fi
    sleep 60
  done
}
torch_cpu() { OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 DIREC_DEVICE=cpu $TORCH_PY -u -m learn.rebuild_tone_train "$@" }
score() { OMP_NUM_THREADS=1 $PY -u -m learn.rebuild_tone score --workers 3 > $L/score-$1.log 2>&1 }
(
  $PY -u -m learn.rebuild_tone curve > $L/curve.log 2>&1 || { log "CURVE FAILED"; exit 1 }
  $PY -u -m learn.rebuild_tone eq --arm arm_cprime_eq > $L/eq-cprime.log 2>&1 || { log "EQ CPRIME FAILED"; exit 1 }
  log "curve and C′+EQ built: $(tail -1 $L/curve.log | cut -c1-200)"
  waitfor "GPU: stm and its control trained" "GPU STM FAILED" || { log "stage 1 not started (GPU failed)"; exit 1 }
  torch_cpu gate --nets cprime,stm_s0,ctl_s0,rank_s0,ctl_tr > $L/gate-1.log 2>&1 || { log "GATE 1 FAILED"; exit 1 }
  $PY -u -m learn.rebuild_tone gate-report > $L/gate-report-1.log 2>&1 || { log "GATE REPORT 1 FAILED"; exit 1 }
  log "gate: $(grep -E '^stm_s0-|render stm' $L/gate-report-1.log | tr '\n' ';')"
  ARMS1=arm_cprime_eq
  if [[ $($PY -c "import json; print(json.load(open('$O/gate.json'))['render_stm'])") == True ]]; then
    for a in arm_stm arm_ctl_stm; do
      torch_cpu rebuild --arm $a > $L/rebuild-$a.log 2>&1 || { log "REBUILD $a FAILED"; exit 1 }
    done
    for a in arm_stm_eq arm_ctl_stm_eq; do
      $PY -u -m learn.rebuild_tone eq --arm $a > $L/eq-$a.log 2>&1 || { log "EQ $a FAILED"; exit 1 }
    done
    ARMS1=arm_stm,arm_ctl_stm,arm_stm_eq,arm_ctl_stm_eq,arm_cprime_eq
  else
    log "gate: stm's arms are not rendered (its E_st on the held-out band crops is not below C′'s)"
  fi
  $PY -u -m learn.rebuild_tone arms-check || { log "ARMS CHECK FAILED"; exit 1 }
  shards g1 tr1 $ARMS1 || { log "TR1 GROUP 1 RENDERS FAILED"; exit 1 }
  log "TR1 group 1 rendered ($ARMS1)"
  score g1 || { log "SCORING 1 FAILED"; exit 1 }
  SEED=1
  waitfor "GPU: second seed trained" "GPU SEED FAILED" || { log "seed stage not started (GPU failed)"; SEED=0 }
  if [[ $SEED != 0 ]]; then
    torch_cpu gate --nets rank_s1,ctl_s1 > $L/gate-2.log 2>&1 || log "GATE 2 FAILED (descriptive; continuing)"
    $PY -u -m learn.rebuild_tone gate-report > $L/gate-report-2.log 2>&1 || log "GATE REPORT 2 FAILED"
    for a in arm_rank_s1 arm_ctl_s1; do
      torch_cpu rebuild --arm $a > $L/rebuild-$a.log 2>&1 || { log "REBUILD $a FAILED"; exit 1 }
    done
    $PY -u -m learn.rebuild_tone arms-check || { log "ARMS CHECK FAILED"; exit 1 }
    shards g2 tr1 arm_rank_s1,arm_ctl_s1 || { log "TR1 GROUP 2 RENDERS FAILED"; exit 1 }
    log "TR1 group 2 rendered"
    score g2 || { log "SCORING 2 FAILED"; exit 1 }
  fi
  $PY -u -m learn.rebuild_tone diag > $L/diag.log 2>&1 || log "DIAG FAILED (descriptive; continuing)"
  $PY -u -m learn.rebuild_tone report > $L/report-1.log 2>&1 || { log "REPORT 1 FAILED"; exit 1 }
  EXT=$($PY -c "import json; print(' '.join(json.load(open('$O/report.json'))['extend']))")
  log "TR1 report: extend [$EXT]"
  if [[ -n $EXT ]]; then
    for g in ${=EXT}; do
      A=$($PY -m learn.rebuild_tone j2-arms --group $g)
      shards ext-$g tr2 $A || { log "TR2 $g RENDERS FAILED (disk guard or a check; see render-ext-$g-*.log)"; continue }
      log "TR2 $g rendered ($A)"
    done
    score ext || { log "SCORING TR2 FAILED"; exit 1 }
    $PY -u -m learn.rebuild_tone report > $L/report-2.log 2>&1 || { log "REPORT 2 FAILED"; exit 1 }
    log "TR2 report done"
  else
    log "TR2: no group extends"
  fi
) &
laneC=$!
log "lane CPU: pid $laneC"
wait $laneG; rcG=$?
wait $laneC; rcC=$?
log "all done (GPU lane $rcG, CPU lane $rcC; renders $($PY -c "import json; print(json.load(open('$O/report.json'))['renders']['total'])" 2>/dev/null))"
