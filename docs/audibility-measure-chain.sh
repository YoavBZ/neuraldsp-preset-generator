#!/bin/zsh
# ROADMAP step (c), the measurement: how audible each "on" time effect is in its self-built mix (declared 2026-10-27:
# docs/trusted-data-t0-design.md, "Audibility in the mix: the measurement"; ledger trusted-data-t3, amendment 5
# "audibility measurement (ROADMAP (c))", and its fix, amendment_5_fix "audibility fresh-process recipe (ROADMAP (c))").
# Approved by the user 2026-10-27 ("Yes for all"). Run it from the main checkout once the fix's PR is merged.
# The fix: Morgan's tremolo, tape delay and rack reverb run on across renders in one plugin process, so every render
# now runs in its own new process (one discarded priming render with the example's own setting, then the one kept).
# Cost: archive (the first run moved aside, zero renders), plan (zero renders), then about 2,700 renders on 3 shards
# (r_on' for each of the ~483 examples, ~824 effect-off renders, one exact repeat per (section, amp) group, each job
# 2 renders: priming + kept), about 40-70 min when the slots are free; measure (zero renders, 4 CPU workers), read (the
# tone probe refitted, zero renders) and the page. isolate=True, 0.25 s trimmed, at most 3 render processes machine-wide
# (every new process waits for a slot and for any separation, e.g. step (b)'s), the 31 GB disk guard. Zero
# separations, zero training. FS5 only; V-real untouched. Outputs only under trusted-data/audibility/ and
# listening/audibility-mix/; t0/, t2/, t3/ and tone-probe/ are read.
setopt no_bg_nice
caffeinate -i -w $$ &!                   # disowned (&!): no job for a wait to hang on (PR #300); waits below name pids
cd /Users/yoavbz/projects/neuraldsp-preset-generator
L=~/ndsp-presets/learn/trusted-data/logs
MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
AM=(-u -m learn.audibility_measure)
step() { echo "$(date) $1"; }
grep -q 'audibility measurement (ROADMAP (c))' docs/dev-test-ledger.json || { echo "no amendment 5 in the ledger"; exit 1; }
grep -q 'audibility fresh-process recipe (ROADMAP (c))' docs/dev-test-ledger.json || { echo "no amendment 5's fix in the ledger"; exit 1; }
[ -f learn/audibility_measure.py ] || { echo "the main checkout lacks learn/audibility_measure.py: merge the PR first"; exit 1; }

step "archive (zero renders: the first run moved under audibility/first-run-2026-10-27/)"
$MAIN ${AM[@]} archive > $L/audibility-archive.log 2>&1 || { echo "ARCHIVE FAILED (see the log)"; exit 1; }

step "plan (zero renders: FS5's on examples, the draw, the repeats; the drift check)"
$MAIN ${AM[@]} plan > $L/audibility-plan-fresh.log 2>&1 || { echo "PLAN FAILED (see the log)"; exit 1; }

step "render (about 2,700 renders on 3 shards, each job a new process)"
pids=()
for k in 0 1 2; do
  $MAIN ${AM[@]} render --shard $k/3 > $L/audibility-render-fresh-$k.log 2>&1 &
  pids+=($!)
  sleep 30
done
for p in $pids; do wait $p; done
for k in 0 1 2; do grep -q "AUDIBILITY RENDER DONE" $L/audibility-render-fresh-$k.log || { echo "RENDER FAILED $k"; exit 1; }; done

step "measure (zero renders; refuses unless every repeat is bit-identical)"
$MAIN ${AM[@]} measure > $L/audibility-measure-fresh.log 2>&1 || { echo "MEASURE FAILED (see the log)"; exit 1; }

step "read (zero renders: the tone probe's switches by A_e)"
$MAIN ${AM[@]} read > $L/audibility-read-fresh.log 2>&1 || { echo "READ FAILED (see the log)"; exit 1; }

step "page (the ear check of tau)"
$MAIN ${AM[@]} page > $L/audibility-page-fresh.log 2>&1 || { echo "PAGE FAILED (see the log)"; exit 1; }
echo "$(date) AUDIBILITY CHAIN DONE"
