#!/bin/zsh
# Resume lane R (it failed at the rotation choice on a missing folder) and then TR, after lane T.
# The main runner skips TR when lane R failed, so this script runs it instead. Same commands.
setopt no_bg_nice
cd ${0:A:h:h}
PY=.venv/bin/python
O=~/ndsp-presets/learn/rebuild-gap
L=$O/logs
export PYTHONUNBUFFERED=1
log() { echo "$(date '+%F %T') $*" >> $L/run.log }
shards() {
  local p=() ok=0
  for i in 0 1 2; do OMP_NUM_THREADS=1 $PY -u -m learn.rebuild_gap "$@" --shard $i/3 > $L/${1}-${@[-1]}-$i.log 2>&1 & p+=($!); done
  for q in $p; do wait $q || ok=1; done
  return $ok
}
log "R resume: pid $$, commit $(git rev-parse --short HEAD)"
shards choose-rot || { log "R ROTATION CHOICE FAILED (resume)"; exit 1 }
log "R: rotation chosen"
shards render --stage r1 || { log "R1 RENDERS FAILED"; exit 1 }
log "R1 renders done"
OMP_NUM_THREADS=1 $PY -u -m learn.rebuild_gap score --workers 3 > $L/score-r1.log 2>&1 || { log "R1 SCORING FAILED"; exit 1 }
$PY -u -m learn.rebuild_gap report --stage r1 > $L/report-r1.log 2>&1 || { log "R1 REPORT FAILED"; exit 1 }
log "R1 report: $(grep 'R2 extends' $L/report-r1.log)"
R2=$($PY -c "import json; print(','.join(json.load(open('$O/report-r1.json'))['r2_probes']))")
if [[ -n $R2 ]]; then
  shards render --stage r2 || { log "R2 RENDERS FAILED"; exit 1 }
  OMP_NUM_THREADS=1 $PY -u -m learn.rebuild_gap score --workers 3 > $L/score-r2.log 2>&1 || { log "R2 SCORING FAILED"; exit 1 }
  $PY -u -m learn.rebuild_gap report --stage r2 > $L/report-r2.log 2>&1 || log "R2 REPORT FAILED"
  log "R2 done ($R2)"
else
  log "R2: no probe extends"
fi
# TR after lane T
until grep -qE "^.{19} T done$|T .* FAILED|ARM REBUILD .* FAILED" $L/run.log; do sleep 60; done
grep -qE "^.{19} T done$" $L/run.log || { log "TR not started (lane T failed; resume)"; exit 1 }
shards render --stage tr1 || { log "TR1 RENDERS FAILED"; exit 1 }
OMP_NUM_THREADS=1 $PY -u -m learn.rebuild_gap score --workers 3 > $L/score-tr1.log 2>&1 || { log "TR1 SCORING FAILED"; exit 1 }
$PY -u -m learn.rebuild_gap report --stage tr > $L/report-tr.log 2>&1 || { log "TR REPORT FAILED"; exit 1 }
log "TR1 report done"
if [[ $($PY -c "import json; print(json.load(open('$O/report-tr.json'))['tr2_due'])") == True ]]; then
  shards render --stage tr2 || { log "TR2 RENDERS FAILED"; exit 1 }
  OMP_NUM_THREADS=1 $PY -u -m learn.rebuild_gap score --workers 3 > $L/score-tr2.log 2>&1 || { log "TR2 SCORING FAILED"; exit 1 }
  $PY -u -m learn.rebuild_gap report --stage tr > $L/report-tr.log 2>&1 || log "TR REPORT FAILED"
  log "TR2 done"
else
  log "TR2 not due"
fi
log "all done (resume)"
