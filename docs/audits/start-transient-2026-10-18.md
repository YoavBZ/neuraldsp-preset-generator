# Audit: the start-of-render transient across the render pipelines (2026-10-18)

**Status:** code-reading audit plus stored-check evidence, zero renders. Part C's direct
measurement is pending the user's permission for a 4th render process (script ready at
`<scratchpad>/stx/cprime.py`: 60 renders).

The [dose-stop audit](dose-stop-2026-10-18.md) (merged via #219 and #220) found that a render is
not clean when the plugin's previous state differs. On the first render of a process the output
starts louder and the excess fades over about 4 s; an amp change leaves a smaller excess, and a
preset or DI change on the same amp sometimes leaves a short one. That audit did not survey other
steps. This one reads the eleven render scripts listed below, asks which scored renders can
follow a different plugin state without a discarded render first, and bounds the effect from
stored checks.

**Not yet audited:** `song_settings` (step 3's arm A), `song_soundspace`, `song_armb`,
`song_bank`, `song_relabel`, `separator_screen`, `di_fine_structure` and `song_diag`. Code reading
already shows one exposure there: step 3's arm A judge renders the measure DI right after the
rebuild-DI search with no priming (`learn/song_settings.py:177`). That is the same pattern as
Mega-53's judges (pipeline 4), estimated at up to about 7e-4 log on the quiet-opening part, far
from arm A's step-3 effect against S (−0.078).

## Summary

- **No merged decision among the audited pipelines changes.** Every stored score that decided
  something there either follows a warm-up at the same amp and DI, or is exposed only at a level
  well under its tolerance or interval. The scripts listed above are not yet audited.
- **One step is affected and is being fixed:** the dose probe (`rebuild_dose`), by its
  amendment 2 (in progress).
- **Part C (`pretrain_set`, rendering now) is exposed but probably harmless.** It has no priming
  render. On the first render of a process or after an amp change, the excess is about one 0.5-dB
  quantisation step on the first 0.5–1 s of half A, on under 0.1% of examples. No reason to stop.
- **Three steps are possibly affected at a tiny level:** arm A levers' 3-W ensembles, arm A
  Mega-53's stage D/E judges (and the first search evaluation of a group's second direction), and
  multi-section's later sections. None is near flipping a result. `rebuild_gap`'s dep_rot choice
  could flip on a few near-tied parts, but only changes which rotation was probed.
- **Measured versus estimated:** pipelines 8 and 9 are measured from stored checks. The sizes for
  part C, arm A levers' 3-W and Mega-53's judges are estimates carried over from the dose-stop
  cell and the rebuild-gap check, not measurements on those renders.
- **Recommended project rule:** in all future render code, one discarded priming render after any
  process start, amp change or DI change.

## What the effect looks like (from the dose-stop audit)

- On the pr12 quiet-opening cell (It_Was_My_Fault ElecGtr1), the process's first render is up to
  about 24% louder at its start. The excess roughly halves every 0.5 s: +0.23 over 0–0.5 s, +0.14,
  +0.08, +0.04, +0.02, and below 0.005 by 3.5–4 s.
- It moves a score only where the scored window is quiet early on. Half A of that part is
  −34.5 dB against its 1–10 s level; the next quietest of 24 parts is −2.1 dB.
- Replaying the dose run's shards, warm-ups that came first in a process or after another amp or
  preset moved the scored halves by at most 2.8e-5 on every other part.
- On the quiet cell, two settings changes on the same amp and DI moved the scores by at most
  5e-7 (the only ones tested).
- Same-amp DI changes can leave waveform differences of 0.01–0.34 in the first second (Prodigal
  pr12 after the quiet cell: 0.22, still 8.7e-4 after 5 s). They stayed harmless on scores because
  those parts are loud from 1 s on.

All pipelines below use `knob_ceiling.Renderer` (`learn/knob_ceiling.py:378`), a reused plugin
process with `isolate=True` and `PREROLL_S = 0.0` (`:375`). Isolation clears the 2–3 s hiss tail
it was added for, but not this transient.

## Per pipeline

### 1. Part C (`learn/pretrain_set.py`, rendering now): exposed

- **No priming render.** `cmd_render` (`:643`) sorts each shard's examples by amp, then base
  (`:673`), and renders each example once (`:707`): a new 10.25-s DI section with new settings.
  An amp change only waits for the render cap (`:697–699`); it renders nothing.
- **What is stored.** The render is trimmed by `TRIM_S = 0.25` (`:50`, `:709`) and the log-mel
  halves are `HALVES = {"A": (1.0, 5.5), "B": (5.5, 10.0)}` (`:96`), quantised in
  `Q_STEP_DB = 0.5` steps (`:95`, `:333`). So half A starts at 1.25 s of render time.
- **Size, first render in a process or after an amp change.** On a section as quiet at its start
  as the pr12 cell, the excess is about +8% (about 0.7 dB) at 1 s and about 0.04 dB by 3.5–4 s.
  That is about one 0.5-dB quantisation step on the first 0.5–1 s of half A. On sections loud
  from 1 s on, the dose replay shows it far smaller (scores moved ≤ 2.8e-5). These sizes are
  carried over from one cell, not measured on part C. Because of the amp-then-base sort, it applies to under 0.1% of
  examples (one per process start or resume, and one per amp change in a shard).
- **Same-amp transitions** (all the remaining examples: new DI, new settings, often a new base)
  are not measured on part C. The indirect evidence says they are tiny on the scored halves:
  - the dose replay moved scored halves by at most 2.8e-5 (dose-stop audit, section 2);
  - multi-section's S repeat, a same-amp DI change, moved scores by at most 2.8e-6 (pipeline 8);
  - song_relabel's 40 label re-renders against stored arm B bank renders (the same recipe as
    part C) differed by up to 0.0034. That was put down to 16-bit storage (soundspace plan,
    amendment 4), but part of it may be this transient;
  - B1's truth self-distance is at most 1.05e-3 absolute and at most 2.4e-4 relative to the S
    distance (pipeline 9).
- **Row scalars.** LUFS (`:718`) and the gain class (`gain_class`, `:628`) move by an estimated
  0.1–0.2 dB at worst on a quiet-start section (whole-render LUFS; it also feeds the val and
  audit mix gains).
- **Re-renders and `recheck`** (`:809`): the stored audio depends on the render before it, which
  the recipe does not record. `recheck`'s 30 re-renders are unprimed, so differences in their
  first ~1–4 s can come from this transient rather than a broken recipe. Prime each re-render
  (one render at the same settings and DI first) in `recheck` and in any later re-render.
- **Verdict:** probably below one quantisation step for nearly all examples. No reason to stop
  the run.
- **Remedies:**
  - cheap: mask or drop the first ~1 s of half A at training time. This must be declared before
    part C's training step;
  - or a priming render per example, which doubles the render cost.
- **Direct measurement:** pending (see the status line). The script measures first-render and
  same-amp transitions on part C's own recipe.

### 2. `knob_ceiling` / `knob_ceiling2` (knob search): not affected

- `run_cell` warms up per (part, amp) with the same DI (`learn/knob_ceiling.py:454`). After that,
  only the preset or settings change. Settings changes are covered by the repeat check:
  `knob_ceiling2`'s 104 stored repeats are at most 5.2e-5.
- The first search render repeats a stored menu render and must match it within
  `REPEAT_TOL = 0.005` (`:434`, check at `:480–485`). `knob_ceiling2.search_cell` warms up the
  same way (`learn/knob_ceiling2.py:202`) and checks the repeat (`:240`, `:297`).

### 3. `arm_a_levers`: experiment 1, early and repeat-check not affected; 3-W possibly, tiny

- **Not affected:** `cmd_repeat_check` (`learn/arm_a_levers.py:508`, warm-up `:526`), `cmd_judge_variants`
  (`:563–565`) and `cmd_judge_early` (`:611–613`) warm up with the measure DI at S per (part, amp)
  before judging. Experiment 2's screen and 2b's local draws warm up per amp and DI
  (`:767`, `:871`). `:752` is the C′ repeat check's warm-up, whose 3 sampled renders can follow
  an amp change: a conservative check, and it passed.
- **3-W ensembles** (`cmd_early_search`, `:915`): each member's rebuilt DI is warmed up once
  (`:944–945`), but the objective then renders the members in turn on every evaluation
  (`:947–949`), so each render follows another member's DI. `K.judge` then renders the measure DI
  unprimed (`:953`).
- **Size:** the quiet-opening part has no levers outputs, so the expected shift is at most about
  2.8e-5 (the dose replay's loud-part bound; an estimate). No decision changes.

### 4. `arm_a_mega53`: stage D/E judges possibly affected, tiny

- **Search objective:** `_warm` primes each (arm, part, amp) with the arm's rebuild at S
  (`learn/arm_a_mega53.py:1157–1165`, called at `:1389`), and the objective renders that same
  rebuild (`:1184–1185`).
- **Judges:** `run_direction` renders the measure DI (`di32`) for `judge_shrunk` and `judge_best`
  right after the rebuild (`rb32`) renders, with no priming (`:1206–1208`).
  - Expected shift: up to about 7e-4 log on the quiet-opening part (the rebuild-gap worst case on
    that cell, pipeline 6), and at most about 2.8e-5 elsewhere (estimates carried over from other
    renders, not measured here). Unlikely to flip anything.
- **A group's second direction:** its first search evaluation (S through `rb32`) follows the first
  direction's two `di32` judge renders. This is the same tiny DI-change exposure on one evaluation
  of 52. At stage D it is checked against the stored S objective within `TOL` (`:1188–1195`).
- **Stage F's S:** `run_s_group` renders a measure-DI warm-up then S (`:1257–1258`), checked
  against the label table within 0.005. Not affected. The stage-D repeat check also warms up per
  direction (`:1280`).
- **Remedy (future runs):** a priming render with `di32` before the judges, and with `rb32` before
  each direction's search.

### 5. `local_objective` render: not affected

`cmd_render` (`learn/local_objective.py:1321`) renders one counted warm-up at S per (cell, DI)
(`:1394`) before Σ through that DI (`:1396–1397`), and `render_checks` (`:1292`) checks S against
the warm-up for DIs with no stored values, and against stored scores otherwise.

### 6. `rebuild_gap` / `rebuild_tone`: stored scores not affected

- `rebuild_gap.cmd_render` (`learn/rebuild_gap.py:1231`) warms up per (cell, probe) (`:1295`)
  and checks S against the warm-up (`:1303–1310`). `rebuild_tone.cmd_render` runs the same loop
  (`learn/rebuild_tone.py:341`). The comparator also renders its own warm-up (`:1197–1198`).
- dep_rot's choice warms up once per cell (`:1146`), but rotations 1–7 each follow another
  rotation's DI unprimed (`:1148–1151`). On 5 of 24 parts the chosen rotation leads the next by
  under 6e-4, within the estimated transient, so the choice could flip there. dep_rot's own
  scores are primed, so at worst a different rotation would have been probed.
- Cells run in the outer loop, so a cell's probes render consecutively on its amp. The worst
  S-vs-warm-up deviation stored was 7.4e-4 (the quiet-opening cell, `arm_rank_s1`, half A),
  under the 0.005 tolerance.

### 7. `rebuild_dose`: affected, being fixed

- `cmd_render` (`learn/rebuild_dose.py:453`) runs probes in the outer loop and cells in the inner
  loop, so a cell's warm-up (`:517`) can be the process's first render. That is what stopped the
  run (dose-stop audit).
- Fixed by the dose-probe plan's amendment 2 (in progress): a priming render at S before every
  (cell, probe) warm-up.

### 8. `multi_section`: possibly affected, small

- `run_part` warms up once per part, on the first section scored (`learn/multi_section.py:585`,
  `:595–598`). Later sections' judges (`:600–601`) follow another section's DI with no priming:
  S on every section (`:610`), the searches (`:629`) and the checkpoint table (`:644`).
- **Size:** measured. The S repeat (`:645–649`) re-renders S on the first kept section after the
  table's renders on other sections, unprimed. Its largest deviation is 2.8e-6 over 20 parts
  (tolerance 0.005). Not near flipping P = −0.018 [−0.030, −0.005]
  ([results](../multi-section-results.md)).
- **Remedy (future runs):** prime on every section change.

### 9. `known_answer` B1: measured from stored checks, harmless

- In `cmd_truth` each section's record is rendered (`learn/known_answer.py:659`) after the
  previous section's renders, then rendered again with the same DI and settings (`:666`). The
  self-distance between the two (`:669`) therefore measures the transient on the record directly.
- Stored: the self-distance is at most 1.05e-3 (a distance between two renders), at most 2.4e-4
  of the S distance (`:670`). That bounds the score shift at about 2.4e-4 in log terms. Harmless.

## Recommendation

- **Project rule:** in all future render code, one discarded priming render after any process
  start, amp change or DI change. It is counted, not scored and not stored. The cost is one render
  per change.
- **Part C:** let it run. Before its training step, declare whether half A's first ~1 s is masked
  or dropped, informed by the 60-render measurement if the user permits the 4th process.
- **Merged decisions:** none among the audited pipelines changes. The dose probe re-runs under
  its amendment 2. The unaudited scripts listed at the top are a follow-up.

**Renders used by this audit:** 0.
