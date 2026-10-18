#!/bin/zsh
# docs/dose-probe-plan.md: the dose probe, unattended. Build and check the probes (zero renders),
# render R1 probe by probe in free render slots (three lanes; a render process never waits: it
# yields with exit 75 on a full machine and its lane retries), the report, R2 by the declared rule,
# the final report, "all done". The code's own gates hold the rest (stop files, the probe hashes, the
# comparators, S against its warm-up, FLAC against float, swap and disk guards). Launch:
#   mkdir -p ~/ndsp-presets/learn/rebuild-dose/logs; setopt no_bg_nice
#   nohup caffeinate -i zsh learn/rebuild_dose_run.zsh > ~/ndsp-presets/learn/rebuild-dose/logs/run.out 2>&1 &
setopt no_bg_nice
REPO=${0:A:h:h}
cd $REPO
PY=$REPO/.venv/bin/python
O=~/ndsp-presets/learn/rebuild-dose
L=$O/logs
mkdir -p $L
export PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
log() { echo "$(date '+%F %T') $*" >> $L/run.log }
RUN=$$
log "start pid $RUN, commit $(git rev-parse --short HEAD), branch $(git branch --show-current)"
PROBES=(dose100 shift100 full_gl full100 dose50 dose25)
YIELD=75

mem() { memory_pressure | awk -F': ' '/free percentage/{gsub("%","",$2); print $2}' }
free_slot() { $PY -m learn.rebuild_dose slots 2>/dev/null | grep -q "free yes" }

lane() {   # stage shard probes...: each probe on this shard until its RENDER DONE line
  local stage=$1 i=$2; shift 2
  local probe rc f
  for probe in "$@"; do
    f=$L/render-$stage-$probe-$i.log
    while true; do
      if ! free_slot; then sleep $(( 90 + RANDOM % 31 )); continue; fi
      $PY -u -m learn.rebuild_tone render-dose --stage $stage --probe $probe --shard $i/3 > $f 2>&1 &
      local pid=$!
      log "lane $stage $i: $probe started pid $pid (memory free $(mem)%)"
      wait $pid; rc=$?
      cat $f >> $f.all
      if (( rc == 0 )) && grep -qxF "RENDER DONE $probe $stage $i/3" $f; then
        log "lane $stage $i: $probe done"; break
      elif (( rc == YIELD )); then
        log "lane $stage $i: $probe yielded ($(grep -m1 '^YIELD' $f | cut -c1-80))"
        sleep $(( 90 + RANDOM % 31 ))
      else
        log "lane $stage $i: $probe FAILED rc $rc (see $f): $(tail -1 $f | cut -c1-160)"; return 1
      fi
    done
  done
  log "lane $stage $i: all probes done"
}

stage_render() {   # stage probes...: three lanes, staggered; 0 only if all three finish
  local stage=$1; shift
  local p=() ok=0
  for i in 0 1 2; do
    lane $stage $i "$@" & p+=($!)
    log "lane $stage $i: pid ${p[-1]}"
    sleep 30
  done
  for q in $p; do wait $q || ok=1; done
  return $ok
}

renders() { $PY -c "import json,pathlib; print(json.loads(pathlib.Path('$O/report.json').read_text())['renders']['total'])" 2>/dev/null }

# --- build (zero renders) -------------------------------------------------------------------------------
if $PY -u -m learn.rebuild_dose build > $L/build.log 2>&1 && grep -qxF "BUILD DONE" $L/build.log; then
  log "build done"
else
  log "BUILD FAILED (see build.log): $(tail -1 $L/build.log | cut -c1-200)"
  log "all done (build failed; renders 0)"; exit 1
fi

# --- R1 -------------------------------------------------------------------------------------------------
if stage_render r1 $PROBES; then
  log "R1 done"; r1=ok
else
  log "R1 FAILED"; r1=failed
fi

# --- report and R2 --------------------------------------------------------------------------------------
if $PY -u -m learn.rebuild_dose report > $L/report-r1.log 2>&1 && grep -qxF "REPORT DONE" $L/report-r1.log; then
  log "report r1 done: $(grep '^extend:' $L/report-r1.log)"
  cp $O/report.json $O/report-r1.json
else
  log "REPORT R1 FAILED (see report-r1.log)"
  log "all done (R1 $r1, report failed; renders ?)"; exit 1
fi
if [[ $r1 == ok ]]; then
  ext=($($PY -m learn.rebuild_dose extend --with-anchor))
  if (( ${#ext} )); then
    log "R2: $ext"
    if stage_render r2 $ext; then log "R2 done"; else log "R2 FAILED"; fi
    if $PY -u -m learn.rebuild_dose report > $L/report-r2.log 2>&1 && grep -qxF "REPORT DONE" $L/report-r2.log; then
      log "report r2 done"
    else
      log "REPORT R2 FAILED (see report-r2.log)"
    fi
  else
    log "R2: no probe extends"
  fi
fi
log "all done (R1 $r1; renders $(renders))"
