#!/bin/zsh
# docs/arm-a-mega53-plan.md (amendment 1 governs): the plan's launch order, unattended, with its
# gates. It waits for experiment 1d's report, runs decide-x once (before any render), then lane A
# (the identity checks, contexts, htdemucs, Mega-53, the rebuilds, check-inputs) beside stage D's
# shards 0/3 and 1/3; shard 2/3 starts when lane A exits; stage F's 3 shards after every stage-D
# shard, only if lane A passed and stage D's primary is complete; then the reports. The code's own
# gates hold the rest (render cap, separation gate, memory gate, swap and disk guards, STOP.json,
# hard caps, plumbing checks; a T or X failure stops only that arm). Launch:
#   mkdir -p ~/ndsp-presets/learn/arm-a-mega53/logs; setopt no_bg_nice; nohup caffeinate -i zsh learn/arm_a_mega53_run.zsh > ~/ndsp-presets/learn/arm-a-mega53/logs/run.out 2>&1 &
setopt no_bg_nice
REPO=${0:A:h:h}
cd $REPO
PY=$REPO/.venv/bin/python
TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
MSST_PY=~/ndsp-presets/tools/msst-venv/bin/python
O=~/ndsp-presets/learn/arm-a-mega53
L=$O/logs
R1D=~/ndsp-presets/learn/local-objective/report-1d.json
mkdir -p $L
log() { echo "$(date '+%F %T') $*" >> $L/run.log }
log "start pid $$, commit $(git rev-parse --short HEAD), branch $(git branch --show-current)"

# 1. decide-x, once, as report-1d.json stands when it appears (amendment 1).
while [[ ! -f $R1D ]]; do sleep 60; done
$PY -u -m learn.arm_a_mega53 decide-x > $L/decide-x.log 2>&1 || { log "DECIDE-X FAILED"; exit 1 }
X=$($PY -c "import json; print(json.load(open('$O/x.json'))['outcome']['arm_x'] or '')")
log "decide-x: arm X '${X:-none}' ($(tail -1 $L/decide-x.log))"

# 2. lane A (CPU, zero renders); each step's checks must pass before the next.
(
  $TORCH_PY -u -m learn.arm_a_mega53 rebuild --sep htdemucs --identity-only > $L/identity-htdemucs.log 2>&1 || exit 9
  $TORCH_PY -u -m learn.arm_a_mega53 rebuild --sep mega53 --identity-only > $L/identity-mega53.log 2>&1 || exit 10
  $PY -u -m learn.arm_a_mega53 contexts > $L/contexts.log 2>&1 || exit 11
  DEVICE=cpu $TORCH_PY -u -m learn.arm_a_mega53 separate --sep htdemucs > $L/sep-htdemucs.log 2>&1 || exit 12
  PYTORCH_ENABLE_MPS_FALLBACK=0 $MSST_PY -u -m learn.arm_a_mega53 separate --sep mega53 > $L/sep-mega53.log 2>&1 || exit 13
  $TORCH_PY -u -m learn.arm_a_mega53 rebuild --sep htdemucs > $L/rebuild-htdemucs.log 2>&1 || exit 14
  $TORCH_PY -u -m learn.arm_a_mega53 rebuild --sep mega53 > $L/rebuild-mega53.log 2>&1 || exit 15
  if [[ -n $X ]]; then                       # X is conditional: a failure stops X only (check-inputs)
    $TORCH_PY -u -m learn.arm_a_mega53 rebuild --sep x > $L/rebuild-x.log 2>&1 || log "REBUILD X FAILED: arm X will stop in stage F"
  fi
  $PY -u -m learn.arm_a_mega53 check-inputs > $L/check-inputs.log 2>&1 || exit 17
) &
laneA=$!
log "lane A: pid $laneA"

# 3. stage D: shards 0/3 and 1/3 beside lane A; 2/3 when lane A exits.
search() {
  OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUNBUFFERED=1 \
    $PY -u -m learn.arm_a_mega53 search --stage $1 --shard $2/3 > $L/search$1-$2.log 2>&1
}
d=()
for i in 0 1; do search D $i & d+=($!); done
log "stage D shards 0, 1: ${d[*]}"
wait $laneA
laneA_rc=$?
if (( laneA_rc )); then log "LANE A FAILED (exit $laneA_rc; see the lane logs): stage F will not run"
else log "lane A done: $(tail -2 $L/check-inputs.log | tr '\n' ' ')"; fi
search D 2 & d+=($!)
log "stage D shard 2: $!"
failD=0
for p in $d; do wait $p || failD=1; done
if (( failD )); then log "STAGE D: a shard failed (see searchD-*.log)"; else log "stage D renders done"; fi
$PY -u -m learn.arm_a_mega53 report --stage D > $L/reportD.log 2>&1 || log "REPORT D FAILED"
log "report D: $(grep -m1 'P_D' $L/reportD.log)"

# 4. stage F after every stage-D shard (cap of 3), only with lane A's checks passed, no global
#    stop, and stage D's primary complete. A T or X failure stops only that arm (STOP-D-T.json,
#    STOP-D-X.json) and does not hold stage F back.
if (( laneA_rc )); then log "stage F not started (lane A failed)"; exit 1; fi
if [[ -f $O/STOP.json ]]; then log "stage F not started: $O/STOP.json"; exit 1; fi
PD=$($PY -c "import json; r = json.load(open('$O/report-D.json')); print('complete' if r['primary']['refused'] is None else r['primary']['refused'])" 2>&1)
if [[ $PD != complete ]]; then log "stage F not started (stage D's primary: $PD)"; exit 1; fi
f=()
for i in 0 1 2; do search F $i & f+=($!); done
log "stage F shards: ${f[*]}"
failF=0
for p in $f; do wait $p || failF=1; done
if (( failF )); then log "STAGE F: a shard failed (see searchF-*.log)"; exit 1; fi
log "stage F renders done"
$PY -u -m learn.arm_a_mega53 report --stage F > $L/reportF.log 2>&1 || { log "REPORT F FAILED"; exit 1 }
log "report F: $(grep -m1 'P_F' $L/reportF.log)"
log "all done: report-D.json, report-F.json"
