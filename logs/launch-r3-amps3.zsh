#!/bin/zsh
# The amp-selector read's renders (ledger phase_r3_amps3, docs/full-controls-plan.md "The amp-selector read"): R-all's
# out-of-fold answers on all three amps for every C3r read unit outside BKS (GOAT 215, cap1 121, n12 12, the panel 12;
# BKS's 40 are on all three already). The answers (c3r-predict --amps3, CPU), then each unit's own amp first as a canary
# (c3r-render --amps3 --which forced) and its check (c3r-amps3-check, which stops the launcher on any drift from C3r's
# read), then the other two amps. 3 shards; the render slots are file locks (PR #446), so launch it from a commit that
# has them. Any failure stops it.   zsh logs/launch-r3-amps3.zsh /path/to/worktree
setopt no_bg_nice
W=${1:?the worktree to run from}
cd "${W}" || exit 1
export PYTHONPATH=. OMP_NUM_THREADS=1
PY=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
T=~/ndsp-presets/tools/demucs-venv/bin/python
LOGS=/Users/yoavbz/projects/neuraldsp-preset-generator/logs
L=${LOGS}/r3-amps3.log
PIDS=${LOGS}/r3-amps3-pids.txt
[[ -f ${L} ]] && mv ${L} ${L}.$(date +%Y%m%d-%H%M%S)                  # a relaunch: the old log rotated aside
[[ -f ${PIDS} ]] && mv ${PIDS} ${PIDS}.$(date +%Y%m%d-%H%M%S)         # and the old PIDs: only this launch's are live
caffeinate -i -w $$ &
echo "launcher $$" >> ${PIDS}
note() { echo "$1 $(date)" >> ${L}; }
grep -q "acquire_render_slot" learn/direct_stems.py || { note "FAILED: this commit has no render-slot locks (PR #446)"; exit 1; }
note "start $(git rev-parse --short HEAD)"

run() {        # one foreground step, logged; stop on failure
  local label=$1; shift
  "$@" >> ${LOGS}/r3-amps3-${label}.log 2>&1 &
  local p=$!
  echo "${label} ${p}" >> ${PIDS}
  wait ${p} || { note "FAILED ${label}"; exit 1; }
  note "${label} done"
}

three() {      # 3 shards at once, every one waited on before a failure stops the launcher
  local label=$1; shift
  local pids=() rc=0
  for k in 0 1 2; do
    "$@" --shard ${k}/3 > ${LOGS}/r3-amps3-${label}-${k}.log 2>&1 &
    pids+=($!)
  done
  echo "${label} ${pids}" >> ${PIDS}
  for p in ${pids}; do wait ${p} || { rc=1; note "FAILED ${label} pid ${p}"; }; done
  (( rc == 0 )) || exit 1
  note "${label} done"
}

run predict env DS_DEVICE=cpu ${T} -u -m learn.full_controls_c3r c3r-predict --arm all --amps3
three forced ${PY} -u -m learn.full_controls_c3r c3r-render --arms all --amps3 --which forced
run check ${PY} -u -m learn.full_controls_c3r c3r-amps3-check
three others ${PY} -u -m learn.full_controls_c3r c3r-render --arms all --amps3 --which others
note done
