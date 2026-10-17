#!/bin/zsh
# docs/local-objective-plan.md, amendments 4 and 4a (experiment 1d): rebuilds (with 4a's identity
# check), 7,056 + 144 renders on 3 shards, scoring, report. Unattended. Launch:
#   setopt no_bg_nice; nohup caffeinate -i zsh learn/local_objective_1d_run.zsh > ~/ndsp-presets/learn/local-objective/logs/run1d.out 2>&1 &
setopt no_bg_nice
REPO=${0:A:h:h}
cd $REPO
TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
PY=$REPO/.venv/bin/python
L=~/ndsp-presets/learn/local-objective/logs
mkdir -p $L
log() { echo "$(date '+%F %T') $*" >> $L/run1d.log }
log "start pid $$, commit $(git rev-parse --short HEAD), branch $(git branch --show-current)"

for src in stem mega53; do
  $TORCH_PY -u -m learn.local_objective_1d rebuild --src $src > $L/rebuild1d-$src.log 2>&1 \
    || { log "1d REBUILD $src FAILED (see rebuild1d-$src.log)"; exit 1 }
  log "rebuild $src: $(tail -1 $L/rebuild1d-$src.log)"
done

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUNBUFFERED=1
pids=()
for i in 0 1 2; do
  $PY -u -m learn.local_objective render --di csep_stem,csep_mega53 --shard $i/3 > $L/render1d-$i.log 2>&1 &
  pids+=($!)
done
log "render shards: ${pids[*]}"
fail=0
for p in $pids; do wait $p || fail=1; done
if (( fail )); then log "1d RENDER FAILED (see render1d-*.log)"; exit 1; fi
log "renders done"

$PY -u -m learn.local_objective score --di csep_stem,csep_mega53 --workers 3 > $L/score1d.log 2>&1 \
  || { log "1d SCORE FAILED"; exit 1 }
log "scored"
$PY -u -m learn.local_objective_1d report > $L/report1d.log 2>&1 || { log "1d REPORT FAILED"; exit 1 }
log "1d all done: report-1d.json"
