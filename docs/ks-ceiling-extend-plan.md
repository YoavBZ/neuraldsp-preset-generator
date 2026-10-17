# The knob-search ceiling, searched to a stop: plan (2026-10-16)

Declared 2026-10-16, before any render, and amended the same day, still before any render,
after an independent review (`tmp/ks-ceiling-extend-plan-review.md`, local: approved with 6
required changes, all folded in as [amendment 1](#amendment-1-2026-10-16-before-any-render)).
Where the amendment and the sections below differ, the amendment governs. Development data, the
true DI (the measure DI), no model. Code: `learn/ks_extend.py`, tests `tests/test_ks_extend.py`. Under the user's rules: no fixed
render limit, so each search stops by an evidence-based rule and reports the renders it used
([ML plan](research/ml-plan-2026-10.md), decision 2); and no pass/fail bars, only effect sizes
with 90% band-clustered intervals.

## Why

Step 3 uses K_S as its ceiling: −0.269 [−0.342, −0.196] against S, 14 of 14 bands
([results](song-settings-results.md)). K_S is knob ceiling's search from the starting preset S
with the true DI, stopped at a fixed 150 renders per direction.

It was still improving when it stopped. Over its last 50 renders the held half gained a median
0.013 and a mean 0.027 (log); the search half gained a median 0.012. So −0.269 is a lower bound
of unknown slack. Every "share of the ceiling" figure, such as arm A's 29%, inherits that slack.

This step measures the ceiling properly: each search runs on until its own curve is flat, and
enough directions are run to pin the ceiling down (amendment 1).

## What runs

**Directions:** the 144 K_S directions (24 parts × 3 amps × 2 directions), run in 6 seeded
batches of 24 until the batch rule stops (amendment 1). Honey is out, as before, because the
judge refuses its half B.

**The continuation:**
- Each direction restarts from its stored final settings (`K_S-<search>.json`).
- It keeps the same space (`knob_ceiling.space(amp, S)`), the same objective (the judge on the
  search half, through the measure DI), the same renderer and the same judge lag.
- It is **K_S plus iterated 150-evaluation rounds**: `knob_search` at the stored search's own
  budget of 150 evaluations, with the same stage shares, each round starting from the best so
  far. This is an operational definition of the ceiling, not `knob_search` at a larger budget
  (300, 450, … would split the budget across the stages differently): every round restarts the
  main stage at step 0.25 and re-tries every mic.
- **Seeds:** round r uses 20261013 + r, so the first round uses 20261014 (the stored seed + 1).
- **The first render repeats the stored final.** It must land within 0.005 (log) on both halves;
  if not, the direction is marked `repeat_failed` with its deviation and the run goes on to the
  next direction (amendment 1).
- **Every setting the stored search already rendered is looked up, not rendered again.** That
  covers all 150 of its evaluations, recovered by a zero-render replay. The same goes for
  settings rendered earlier in this continuation. A look-up still uses one of its round's
  evaluations, just as `knob_search`'s own cache does.

**Why rounds, not a fresh 50-render search per chunk** (checked in code):
- At a budget of 50, `knob_search`'s shares give the main stage 18 evaluations, less than one
  sweep at step 0.25 (sw50r has 17 dims).
- The mic stage gets 1 evaluation per alternative mic, so a mic is swapped but the knobs are
  never re-tuned behind it.
- The restart and final stages get 10 and 4.
- So a chunked fresh search would never refine below the coarsest step. A round at 150 is the
  optimiser as declared and as run.

**One change to `knob_search`, for the continuation only:**
- `knob_search` takes an optional `gains` dict, the per-dim improvement so far.
- In the stored search, the main stage ranks the "key dims" that are re-tuned after each mic
  swap.
- In a continuation round from a near-converged point, the main stage often finds nothing. With
  all gains at zero, the key dims would fall to alphabetical order.
- So the rounds carry the stored search's main-stage gains (recovered by the replay) and add
  their own. With `gains=None` the search is unchanged, which a test checks.
- If a direction's replay doesn't reproduce its stored final settings, the run stops (amendment
  1; the review's zero-render check found 0 mismatches in 144).

## The stopping rule (per direction, search half only)

- **Chunks:** the search half's best is recorded every 50 renders.
- **Flat:** a direction stops at the first chunk end, at least 150 extra renders in, where the
  best search-half objective improved by less than **0.005 log over the last 150 renders**.
- **The held half is never read by the rule,** so it stays clean. This is a deliberate departure
  from the wording of the ML plan's decision 2 ("a search stops when its held-half curve has
  flattened"): a rule that reads the held half would let the stop depend on the half the result
  is measured on.
- **The efficiency guard:** a direction also stops at **600 extra renders**. The report gives how
  many hit it.
- **Exhausted:** a round that renders nothing (every setting already known) also stops the
  direction, as does a safety net of 40 rounds. Both are reported; neither is expected.

**A refinement of the brief's design (100-render window):**
- A 100-render window can read "flat" in the middle of a round: after the main stage (52) and
  the mic stage (36), but before the restart and final stages.
- In the stored searches those late stages carry the late gain. Restarts plus final gained a
  median 0.022 on the search half (86% of directions ≥ 0.005), against a median 0.000 for the
  mic stage (24% ≥ 0.005).
- So the window is one round's worth of renders, 150. Any 150 renders in a row span every stage.
  That sets the minimum at 150 extra renders per direction.

## What is reported

(Amendment 1 replaces items 1–3 by the per-part estimate, fixes the direction set across points
and adds the split by stop reason; its list governs.)

All figures are held-half log ratios, per part (the mean over amps and directions), then
band-weighted with 90% band-clustered intervals (`song_readout.bw`, as step 3). Clean and crunch
are reported separately, with bands better and leave-one-band-out.

1. **The ceiling curve** against S at 150 (the stored K_S), 200, 250, …, 750 total renders.
   A direction that has stopped carries its final value forward. The number still running is
   given at each point.
2. **The ceiling at the stop:** the final estimate.
3. **The extension's own gain:** the final against the stored K_S at 150, paired.
4. **Renders:** extra renders per direction (total, median, quartiles, max), stops by reason, how
   many hit the 600 guard, the largest repeat deviation, and how many directions end with a
   refused held half.
5. **Step 3's view:** the same curve on step 3's 142 directions, without its two drops. At 150
   it reproduces −0.269, so step 3's comparisons can be re-read against the new ceiling.

**How it is read:**
- The new figure replaces −0.269 as the true-DI search's reference.
- "Converged by the declared rule" is said only of directions that stopped flat (amendment 1).
  The figure is still a lower bound on the best reachable settings.
- Step 3's shares (arm A's 29%, and so on) are restated against it, descriptively. Nothing is
  re-decided.

## Zero-render checks (`check`, before any render)

1. **Replays:** every one of the 144 directions replays to its stored final settings.
2. **The stored K_S tails:**
   - search and held change over the last 50 renders (median, mean, band-weighted interval);
   - how many directions the rule already reads flat at 150 (only one whose whole search gained
     less than 0.005 can).
3. **Knob ceiling 2** ([results](knob-ceiling-2-results.md)), from the stored per-render
   evaluations, judged the same way:
   - **Stage 1** (200 renders per cell, 48 cells):
     - the search and held tails over the last 50 renders;
     - the held tail band-weighted, with its interval;
     - how many cells the rule would have stopped by 200.
   - **Stage 2** (24 renders per effect):
     - each effect search's tail over its last 12 renders;
     - the share still improving by 0.005 on the search half;
     - each cell's choice recomputed with every effect cut to 12 renders, against the stored
       choice. That gives how many choices change and the held change of the chosen result.
     - The recomputed full-budget choice reproduces all 48 stored choices (tested).

These say whether knob ceiling 2's stages were cut short too. Any follow-up gets its own plan.

## Machine

- **Renders:** CPU, `knob_ceiling.Renderer` (Morgan, `isolate=True`, reused processes).
- **Processes:** at most 3 machine-wide, each taking i::3 of the current batch (amendment 1).
- **Queueing:** they wait behind arm B's running relabel renders (`--after` their pids, hardened
  in amendment 1), and check the 3-process cap before every direction.
- **Guards:** `setopt no_bg_nice`, one numpy thread per process, the swap guard of
  `arm_a_levers`.
- **Crash-safe:** each direction saves its render log every 50 renders. A restart replays that
  log with zero renders (the setting keys are checked) and continues.
- **Expected renders (amendment 1):** 2 to 4 batches, so 48 to 96 directions at 150 to 600 extra
  renders each: about **7,200 to 57,600**, plus one warm-up per direction (at most 24 a batch).
  At about 1.5 s per render on 3 free processes, about 1 to 8 hours, plus each batch's wait for
  its slowest direction and any contention. All 6 batches would be 21,600 to 86,400 (3 to 12
  hours).
- **Disk:** scores, setting keys and final settings only, no audio.

## Commands

```
.venv/bin/python -m learn.ks_extend check                    # zero renders: replays, design, tails
mkdir -p ~/ndsp-presets/learn/ks-ceiling-extend
setopt no_bg_nice
RELABEL=$(pgrep -f "python -m learn.song_relabel")           # empty: pass --no-wait instead
for i in 0 1 2; do
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
    nohup .venv/bin/python -m learn.ks_extend run --shard $i/3 --after ${=RELABEL} \
    > ~/ndsp-presets/learn/ks-ceiling-extend/run-$i.log 2>&1 &
done
.venv/bin/python -m learn.ks_extend report                   # any time; final when the batch rule stops
```

`run` refuses an empty `--after` unless `--no-wait` is given. If a shard dies, restart the same
command: the others wait at the batch barrier, and the dead shard's direction resumes from its log.

Outputs are under `~/ndsp-presets/learn/ks-ceiling-extend/`:
- `cells/<part>/<amp>/<search>.json`, with each direction's chunks, log, stop and status;
- `<search>-settings.json`;
- `check.json` (with the batch design) and `report.json`.

## Amendment 1 (2026-10-16, before any render)

From the independent review, required changes 1–6, applied as written.

1. **Seeded batches and a search-half precision rule, in place of running all 144.**
   - **Design:** within each class (19 clean parts, 5 crunch), the sorted parts are shuffled with
     `random.Random(20261016)` and given offsets o = 0, 1, …, 5, 0, … in that order. Batch b
     (0–5) runs, for each part, combination c = (o + b) mod 6: amp `AMPS[c % 3]`, search half
     `"AB"[c % 2]`. Six batches cover all 144 directions once; each has 24 directions, one per
     part, amps 7–9 each and halves 11–13 each; a part's consecutive batches change both amp and
     half. Order within a batch: clean then crunch, each in shuffled order.
   - **Within a batch:** each direction runs the per-direction rule unchanged (flat, the 600
     guard).
   - **After each complete batch, from the second on (k ≥ 2 batches done):** with g = log(final
     search / stored search), the search-half extension gain of each finished direction, s² the
     within-part variance of g pooled over parts (n_p − 1 degrees of freedom each), n_band the
     parts in each band and B = 14 bands,
     `h = 1.645 · sqrt( s²/k · (1 − k/6) · Σ_band 1/n_band / B² )`,
     the 90% half-width of the error from the directions not yet run. **Stop adding batches when
     h ≤ 0.01**; otherwise run the next. At 6 batches h = 0. The held half is never read.
     (0.01 is under a seventh of the ceiling's own band-clustered half-width, 0.073.)
   - **Not used:** a band-clustered half-width target (it doesn't shrink with more directions:
     its width is the spread between bands) and "sign and size settled" (stopping on the mean
     biases it).
   - **Estimate:** per part, the mean of log(K_S@150 held / S held) over all of the part's
     directions, plus the mean held extension gain log(held / K_S@150 held) over the part's run
     directions; then band-weighted with the usual 90% band-clustered interval, with h beside it,
     and the same on step 3's 142 directions. At 150 (no extension) it is step 3's −0.269
     (tested).
   - **Execution:** the 3 processes split each batch (i::3 in the seeded order). A process that
     finishes its share waits until every direction of the batch is finished (`done` or
     `repeat_failed`), applies the rule itself (it is deterministic, so all three agree) and
     goes on or exits. Warm-ups are counted and reported.
2. **A fixed direction set at every reported point.** A run direction whose incumbent held half
   is refused at any reported point (150, 200, …, 750, the stop) leaves every point and both
   terms of its part's estimate; the count is reported. A part with no run direction left is
   left out of the estimate and listed.
3. **In `run`:** a failed repeat marks the direction `repeat_failed` (with its deviation) and
   moves on; it counts as finished for the barrier and gives no gain. A replay mismatch stops the
   run.
4. **Resume and queueing:**
   - a resumed direction must have the same rule (chunk, window, minimum gain, guard, round) and
     seed as the code, or the run stops;
   - `--after` must be non-empty unless `--no-wait`; only pids whose command line is a python
     running `-m learn.song_relabel` are waited on, re-checked each minute (a reused pid or a
     shell wrapper doesn't count);
   - before each direction, the process waits while 3 or more other render processes run
     (python running `learn.song_relabel render-new|probe` or `learn.ks_extend run`, this one
     excluded), so the cap is 3 including itself.
5. **Report by stop reason.** The extension gain (held, and search beside it) and the run
   directions against S are given for all, flat, guard and other stops. "Converged by the
   declared rule" is used only for directions that stopped flat. The headline line gives the
   number and share of guard hits.
6. **Wording and estimates:** the continuation is named "K_S plus iterated 150-evaluation
   rounds"; the search-half rule is stated as a deliberate departure from decision 2's
   "held-half" wording; the expected renders and hours are for the batch rule (Machine).

**What is reported, as amended:**
1. the estimate against S at 150, 200, …, 750 total renders and at the stop (all, clean, crunch;
   crunch has 5 parts and is descriptive), with the number still running at each point;
2. the batch history: h after each complete batch and the decision;
3. the held and search-half extension gains, all and by stop reason;
4. renders (total, distribution, stops by reason, guard hits on the headline), warm-ups,
   `repeat_failed` directions, directions dropped for a refused held half, the largest repeat
   deviation;
5. step 3's 142-direction view of the estimate.

## Ledger

Entered in `docs/dev-test-ledger.json` on 2026-10-16, before any render, and amended (amendment 1) the same day, before any render:

```json
{
 "test_id": "ks-ceiling-extend",
 "plan": "docs/ks-ceiling-extend-plan.md",
 "entered": "2026-10-16, before any render",
 "repeat_use": "Repeat development use of knob ceiling's 24 scored parts / 144 K_S directions (their uses so far: knob ceiling, knob ceiling 2, label table, step 3, arm A levers, the soundspace plan). Continues the stored K_S searches from their stored finals on the same halves; the held halves were read by earlier steps, so the result is a development reference, not a fresh estimate. Zero-render checks re-read knob ceiling 2's stored stage-1 and stage-2 evaluations (48 cells each)",
 "parts": [
  "cambridge-Drag_Me_Down-ElecGtr4",
  "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr1",
  "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr2",
  "cambridge-Passing_Ships-ElecGtr6",
  "cambridge-Prodigal-ElecGtr5",
  "cambridge-Quicksand-ElecGtr1",
  "cambridge-Signs-ElecGtr2",
  "cambridge-Today's_The_Day-ElecGtr10",
  "cambridge-colour-me-red-elecgtr01",
  "cambridge-femme-elecgtr3",
  "cambridge-get-out-of-bed-elecgtr1",
  "cambridge-just-don-t-talk-elecgtr3",
  "cambridge-magilla-elecgtr1dt",
  "telefunken-Blind_Spots-GTR",
  "telefunken-Bloomlight-GTR",
  "telefunken-Farthest_Step-GTR",
  "telefunken-First_Offering-GTR_1",
  "telefunken-First_Offering-GTR_2",
  "telefunken-Fragments-GTR",
  "telefunken-Gym_Hours-GTR_1",
  "telefunken-Long_Way_Home-GTR",
  "telefunken-Russian_Cream-GTR_2",
  "telefunken-Sculptor's_Request-GTR_1",
  "telefunken-Sculptor's_Request-GTR_2"
 ],
 "bands": "knob ceiling's 14 scored bands (Honey excluded: the judge refuses its half B)",
 "audio_only": "none beyond the listed parts' crops and measure DIs",
 "seeds": "round r of the continuation: 20261013 + r (round 1: 20261014, the stored K_S seed + 1); batch design random.Random(20261016), per class on the sorted parts (amendment 1)",
 "gate": "None (the user's rule of 2026-10-16). Stopping, per direction, search half only (a deliberate departure from decision 2's 'held-half' wording): flat when the best search-half objective improved by < 0.005 log over the last 150 renders (checked every 50, from 150 extra renders); guard 600 extra renders; 'exhausted' if a round renders nothing. Measured: held-half log ratio against S at 150, 200, ..., 750 total renders and at the stop, and the final against the stored K_S (paired), per part then band-weighted with 90% band-clustered intervals; clean/crunch, bands better and leave-one-band-out; step 3's 142-direction view beside. Renders used reported (total, distribution, stops by reason, guard hits). Amendment 1: directions run in seeded batches until h <= 0.01 (search half), see amendment_1; the estimate is per part, stored 150 over all directions plus the run directions' gain",
 "renders": "no fixed limit; amendment 1: 2-4 batches expected, 48-96 directions at 150-600 extra renders each (about 7,200-57,600) plus one warm-up per direction; all 6 batches would be 21,600-86,400; CPU <= 3 render processes machine-wide (checked before each direction), queued behind arm B's relabel renders; knob_ceiling.Renderer (isolate=True)",
 "outcome": null,
 "amendment_1": "2026-10-16, before any render, from the independent review (tmp/ks-ceiling-extend-plan-review.md, approved with 6 required changes, all applied). (1) Seeded batches: per class (19 clean, 5 crunch) sorted parts shuffled with random.Random(20261016), offsets o = 0..5 cycling; batch b runs per part combination c = (o + b) mod 6, amp AMPS[c % 3], search half 'AB'[c % 2]; 6 batches of 24 cover the 144 once. Per-direction rule unchanged inside a batch. After each complete batch from k = 2: h = 1.645 sqrt(s2/k (1 - k/6) sum_band 1/n_band / B^2), s2 the pooled within-part variance of the search-half extension gain log(final search / stored search); stop adding batches when h <= 0.01 (search half only; not a band-clustered width target, not 'sign and size settled'). Estimate per part: mean log(K_S@150 held / S held) over all its directions + mean held extension gain over its run directions, band-weighted with 90% band-clustered intervals, h beside; step 3's 142-direction view beside. 3 processes split each batch i::3 with a barrier; warm-ups counted. (2) A run direction with a refused incumbent held half at any reported point is dropped from every point; count reported. (3) A failed repeat marks the direction repeat_failed and moves on; a replay mismatch stops the run. (4) Resume checks the saved rule, seed and round; --after must be non-empty unless --no-wait and waits only on python learn.song_relabel pids; the 3-process cap is checked before each direction. (5) Reported by stop reason; 'converged by the declared rule' only for flat stops; guard hits and share on the headline. (6) Named 'K_S plus iterated 150-evaluation rounds'; the search-half rule is a deliberate departure from decision 2's 'held-half' wording; expected renders 2-4 batches, about 7,200-57,600"
}
```
