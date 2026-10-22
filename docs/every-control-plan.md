# Every control: how and when each route covers the whole plugin: plan

**Approved 2026-10-22 for its first stages (the user, in chat with the ML session).** Stages 0
and 1 go ahead; switched-off knobs are left out, as proposed (below). Whether a declared rule counts
as setting a control the judge can't hear stays open; stage 0c's screen informs it. Stage 0 and 1's
declared details are in [Stages 0 and 1, as built](#stages-0-and-1-as-built-2026-10-22); they run
after an independent review of the code. The plan itself was drafted with zero compute: no renders, no training,
no downloads. It answers the user's coverage rule (2026-10-21, PR #262; [ROADMAP](ROADMAP.md) and
[ML plan](research/ml-plan-2026-10.md) §5 "Coverage"). Nothing here runs until the user decides and
each stage's own plan has had an independent review. Declared plans keep their definitions: the
direct model's step 3 and its sound gate ([plan](direct-model-stems-plan.md), amendments 5 and 6)
run as they are.

## The short version

- **Today both routes set 12–17 controls per Morgan amp, and none on Tone King.** That is
  `knob_ceiling.space`: input gain, the amp's knobs and switches, the mics and cab placement. The
  rest comes from S. Covering the manifests adds **73–75 Morgan controls per amp** and **all 94 of
  Tone King's**.
- **Most of what is missing has already been measured with the true DI.** The amp's EQ is worth
  the most. The pedals are worth a little, mostly on crunch, and the time effects only where a
  record clearly has one. The gate, doubler, room mics, cab phase, amp choice and all of Tone King
  have no number yet.
- **Switched-off knobs: leave them out** of losses and knob scores. They take their neutral values
  only where a value must be written: the search's canonical form and the saved preset.
- **The order, cheapest first:**
  - stage 0: a zero-render reading of amp choice, and a short screen of what the judge can hear;
  - stage 1: a true-DI oracle for the groups with no number yet, about 13–14k renders and no training;
  - stage 2: grow each route's space, by step 3's verdict (arm A first on `GATE STOP`; the direct
    model's pilot on `GATE OK`);
  - stage 3: Tone King, in the route that wins.

## What each route covers today, and what to add

Counts are the manifests' writable controls that change the sound of the chosen amp (Morgan:
`packs/morgan/manifest.json`, Tone King: `packs/toneking/manifest.json`). Only the chosen amp's
modules sound, so the other two amps' knobs are silent.

| Morgan group | PR12 | SW50R | AC20 | In a route today | Worth with the true DI (development, held half) |
|---|---|---|---|---|---|
| **Today's space:** input gain, amp knobs and switches, both mics, cab position and distance, right cab on and level | 12 | 17 | 14 | both | K_S −0.293 [−0.378, −0.207] against S ([extension](ks-ceiling-extend-results.md)) |
| Amp EQ: on, 9 bands, HPF, LPF | 12 | 12 | 12 | no | −0.079 [−0.117, −0.040] on top of K_M, 14/14 bands; band-weighted −0.094, leaning on one part (−0.069 without it) ([knob ceiling](knob-ceiling-results.md) (d)) |
| Pedals: compressor 5, drive 1 4, drive 2 5 | 14 | 14 | 14 | no | +0.010 [+0.005, +0.016] to reset them, about half of stage 1's −0.023; crunch +0.025, clean +0.006 ([knob ceiling 2](knob-ceiling-2-results.md)) |
| Time effects: reverb 6, delay 12, tremolo 6 | 24 | 24 | 24 | no | −0.010 [−0.022, +0.002] by the judge; the ear picked wet on all 3 clear-gain trials (knob ceiling 2) |
| Amp spring (reverb; PR12 also dwell) | 2 | 1 | 0 | no | in knob ceiling 2's stage 2 (on in 3 of 48 cells) |
| Amp choice (`selectedAmp`) | 1 | 1 | 1 | no; fixed per run | not read (stage 0) |
| Gate (on, threshold), doubler (on, spread) | 4 | 4 | 4 | no | not measured |
| Cab rest: left cab on and level; per side phase, stereo, pan, room on, room level | 12 | 12 | 12 | no | not measured |
| Output gain | 1 | 1 | 1 | no | invisible to the judge (it removes level) |
| Section switches (amp, EQ, pedals, cab, effects) | 5 | 5 | 5 | no | none; each section's own switches carry the same sounds |
| **To add** | **75** | **74** | **73** | | |

K_S's figure is band-weighted; the EQ, pedal and effect figures are part-weighted means with
band-clustered intervals, as their results report them. Stage 1 reports both weightings.

- **Manifest exceptions, never set:** the preset name; `transpose` (`searchable: false`: pitch, not
  tone); both room mic types (no control in the plugin's UI); both custom IR paths (empty means the
  internal mics).
- **Declared reparameterisations, set by rule:** delay and tremolo sync stay off, with the time in
  ms and the rate in Hz (`packs/timing.py` turns a tempo into ms). That is 5 of the 24 time-effect
  controls. Section switches are held on (`knob_ceiling2.HELD_ON` holds the pedal and EQ sections; the amp,
  cab and effects sections are added).
- **Tone King: 94 controls, none covered.** Amp and channels 14 (channel, attenuation, HFC, spring,
  amp tremolo ×2, section, Rhythm 4, Lead 3); pedals 22 (compressor 5, two drives 5 each, wah 6,
  section); EQ 11; cab 19; time effects 25 (chorus 4, delay 14, reverb 6, section); input, output
  and gate 3 (the gate has no on switch). Six delay sync, tap and display selectors are set by rule. The other channel's 3–4
  knobs are silent. Knob ceiling 2 deferred Tone King's oracle (its stage 3), so it has no number.

## Switched-off features: leave them out (approved 2026-10-22)

The user's rule: every knob value of a switched-off feature is one setting. The proposal is to
**leave those knobs out of every loss and knob score**. They get a declared **neutral value** only
where a value has to exist.

| Where | Direct model | Arm A |
|---|---|---|
| Training | Weight 0 when the label's switch is off (`song_relabel.label_weights`, generalised from the right cab to a gate table); the switch itself is always scored | No training |
| Knob scores (E, knob-space proxies) | Amendment 5's mask, generalised; the constant's medians over audible labels only | Masked the same way |
| Sound scores (judge, sound gate) | Nothing to do: identical sounds score the same | Same |
| Search | None | Canonical form (`knob_ceiling2.canon_pedals`, extended): an off feature's knob moves become cache lookups, not renders; a feature switched on starts from neutral |
| Written preset | Off feature at its neutral values | Same; the halfway shrink pulls a feature that S has off toward neutral, not toward S's stored values |

**Why leave out rather than neutral labels:**
- **The project already does it, at zero cost.** The loss takes masks (`song_model.loss_fn`), and
  amendment 5 masks the right cab's knobs in E, as `song_relabel` does for arm B. Step 3's training
  loss does not mask them yet (amendment 5: that needs a retrain), so D_full would be the first
  direct model trained with the mask.
- **Neutral labels teach a convention the audio does not contain.** The model would have to put a
  spike at neutral whenever it thinks a feature is off. Amendment 5's median readout, averaged over
  seeds and halves, would then blend that spike into the answer whenever the switch is uncertain. A
  pedal that ends up on would carry knobs pulled toward neutral. Amendment 5 names the readout as
  the likely reason the constant beat the pilot model, so a new readout artefact is the risk to
  avoid.
- **Many labels would be off.** S is dry, and part C's start and wide modes draw a switch off at
  least half the time. Neutral values would make up much of those knobs' labels, and E would
  reward guessing them.

**The gates, from the manifests** (code: one table, tested against the manifests, so a new control
cannot go unlisted):
- `selectedAmp` silences the other amps' modules and EQs, and Tone King's `ampType` the other
  channel;
- each pedal's, effect's, gate's, doubler's and EQ's on switch silences its knobs;
- a cab's on switch silences its mic, placement, level, phase, pan, stereo and room; at least one
  cab stays on;
- phase, and pan and stereo in the mono judge, only matter with both cabs on;
- a room's on switch silences its level;
- the spring's level at 0 silences the PR12's dwell (knob ceiling 2's pseudo-switch).

## The stages

Measured rates:
- **Renders:** 1.58 s median on 3 processes (part C), so about 6k an hour. Arm A's 13,986 YT and ZT
  renders took 2 h 16 min.
- **Separation:** X-LANCE gtr_mss runs 0.29–0.34 clips/s on one MPS and one CPU worker, so 19–22 h
  for about 23k clips (amendment 2).
- **Training:** 184 examples/s; step 3's 3 seeds × 2 models take 5–7.4 h.

| Stage | What | Renders | Training | Wall-clock | Disk |
|---|---|---|---|---|---|
| 0 | The full-space table and tests; amp choice from stored cells; a judge-visibility screen; Tone King's search renderer | about 40 | none | about 1 h, plus code | none |
| 1 | True-DI oracle, development, 48 cells: Morgan's unmeasured groups; Tone King's whole space | about 5.8–7.2k + 7.3k | none | about 1 h + 1.2–3.4 h | under 0.1 GB |
| 2A | Arm A on stage F, grown space, 2 budgets | about 17.1k | none | about 3 h | under 0.1 GB |
| 2D pilot | Full-space labels for 6k + V_sep's 1.7k: re-render, true mix, X-LANCE stem; D_full-5k, 2 seeds; sound gate | about 8.6k (twice if the mix and stem stages render apart, as the pilot's did) + 4.4k | about 1 h MPS | about 9–11 h | about 1.6 GB |
| 2D full | The remaining 15.3k; D_full, 3 seeds; gate; stage F | about 17k + 4.4k + 321 | 5–7.4 h MPS | about 1.5 days | about 1.3 GB |
| 3 | Tone King in the winning route | arm A about 2.3k; direct about 23k | direct 5–7.4 h | arm A about 1 h; direct about 1.5 days | up to 2 GB |

**Stage 0 (zero renders, except the screen).**
- **0a. The full-space table.** One entry per control, with its source (learned or searched,
  research, or a rule), its gate and its neutral value, plus a test that walks both manifests.
  Code only.
- **0d. Tone King's search renderer** (code, before stage 1). Knob ceiling 2 deferred Tone King
  because neither renderer can search it, and its switches are stored as "0"/"1". It needs its own
  renderer and a check against the stored start distances (`tk-baseline/distances-dev.json`,
  within 0.005 log), as knob ceiling 2's plan requires.
- **0b. Amp choice.** Read from knob ceiling's stored K_S cells (24 parts × 3 amps × 2 directions).
  Per part, pick the amp by its K_S search-half score and read its held half against the mean of
  the three amps' held halves (an amp chosen blind). That is what choosing among the three is worth
  once the knobs are searched.
- **0c. What the judge can hear.** The judge removes level and folds to mono. About 40 renders of S
  with one control moved at a time show which controls it cannot see: each pan, stereo and phase
  with both cabs on; delay width and ping-pong and doubler spread with their feature on. Output gain
  (level removed) and a single cab's pan (mono fold) follow from the judge's maths without renders.
  Those controls get a rule, not a model:
  - output gain matched to S's loudness;
  - pan centred, unless the arrangement prior documents a side;
  - the stereo widths at S's values.

**Stage 1 (true DI, development, no training).**
- **Morgan.** Knob ceiling 2's 24 parts, both directions, from each cell's stored stage 2 setting,
  so each number is worth on top of everything already searched. Each group is searched on its own
  (knob ceiling 2's amendment 1), 30 renders per group and cell: the gate; the doubler; room mics
  with the left cab's level; phase; the effects' unsearched knobs (tremolo level, tape drive). That
  is 4–5 groups, about 5.8–7.2k renders.
- **Tone King.** Knob ceiling 2's deferred stage 3, widened to the whole space: 48 cells from the
  class start (Vintage Trem or Squishy Lead), the channel one searched control, 150 renders per
  cell, about 7.3k renders. With about 80 dimensions that is a loose lower bound. A 30-render smoke
  run first measures the new renderer's speed (Morgan's through the Swift host; up to 5 s in fresh
  processes) and checks that its renders repeat.
- **Listening.** One blind page (letters drawn at random), 8 trials. It covers the gate, doubler and
  room cells where the judge's held gain is clear, plus near-ties as controls, read as knob ceiling
  2 read effects.

**Stage 2 depends on step 3's sound gate.**
- **On `GATE STOP`: arm A first (2A).** Re-run stage F's M arm (the Mega-53 stem, rebuilt DI, 52
  renders, shrink 0.5) with the grown space: the groups stages 0–1 and earlier results show to pay.
  The stored M arm is A_core at no extra render; an X-LANCE A_core would add about 6.9k. Two
  budgets:
  - equal renders (52), today's cost per song: 126 directions × 55, about 6.9k;
  - 52 for the core, then 26 for EQ and pedals, as knob ceiling staged its EQ: about 10.2k.
  - The shrink moves continuous knobs only; switches and mics keep the found value.
  - The primary contrast is A_full − A_core, paired per direction.
  - A known risk: a stem-scored EQ can fit the separator's darkening (Mega-53 reads 12 dB darker
    than htdemucs above 6 kHz). This test measures it.
  - The direct model's growth waits for the user's revisit, which `GATE STOP` already calls.
- **On `GATE OK`: step 4 runs as declared, then the direct model's pilot (2D pilot).**
  - Each label keeps part C's draw for today's space, unchanged. The new controls are drawn from a
    separate seeded stream with part C's modes: factory (the same factory preset as the core draw,
    now un-dried, so effects appear at their factory rates), start, and wide.
  - The DI sections, mix draws and separator are unchanged, so D_full and step 3's D differ only in
    the new controls.
  - A positive control: labels with the new controls at S's values must reproduce the stored mels.
  - Amp choice becomes a 3-way head only if 0b shows a gain.
  - The pilot's primary: **the new controls' own worth**. D's answer for today's space plus
    D_full-5k's answer for the new controls, against D's answer with the new controls by rule. Both
    are rendered and judged against the full-space truth on R_in, as amendment 6 does. Sharing D's
    core keeps the 5k-against-20k size out of the contrast. D's core never saw the new controls
    vary, so beside it: D_full-5k against a 5k today's-space model on X-LANCE stems (about 20 min
    more MPS).
  - Arm A's 2A follows when the renderer is free.
- **2D full.** Only if the pilot gains and step 4's D − S is below 0. If step 4 ties, the user
  revisits first, as step 4 declares.
- **Stage F's reuse, stated.** Step 4 is the eighth set of arms on stage F's parts; 2A and 2D full
  add more. Nothing in this plan is chosen on stage F.
- **Part C's 43k renders took about 8.7 h** (14:08–22:48 on 2026-10-18, including a disk-guard
  stop). The direct build keeps no audio, so it re-renders its own pool. Separation, not rendering,
  sets the wall-clock: about 19–22 h for the 23k.

## Decision rules (declared now)

Every reading is an effect size with a 90% band-clustered t interval, band-weighted, on the held
half. There are no pass/fail bars. Any gain shown is built on. A tie means "not shown at this power" and
takes the cheaper option.

- **Stage 1, per group:** the group searched minus not searched, over 14 bands.
  - Interval below 0: the group enters both routes' learned or searched space, largest gains first.
  - A tie or worse: the group keeps its declared rule (off, neutral, S's value or research), and
    the reading is reported. If the true DI cannot use a group, a song cannot either.
  - Time effects, gate and doubler enter only where the ear agrees with a clear judge gain (knob
    ceiling 2's reading). Off on a dry record is a correct answer.
- **0b, amp choice:** the picked amp minus the blind mean, over 14 bands. Below 0: amp choice enters
  both routes (a searched control in arm A, a 3-way head in the direct model). A tie: the amp stays
  `generate`'s research choice, as today (the cheaper option).
- **2A:** A_full − A_core on stage F, over 12 bands.
  - Below 0: adopt the better budget.
  - A tie: the equal-budget full space. It costs no more renders and meets the rule.
  - Above 0: keep today's searched space, with the new controls by rule.
- **2D pilot:** the new controls' worth in the sound gate, over 4 bands (3 df, so power is low).
  - Below 0: build the rest.
  - A tie: no full build without the user. The reading, its interval and the size-matched row go to
    the user; the new controls stay by rule meanwhile.
- **2D full:** D_full − S on stage F as step 4's primary, with D_full − D beside it.

## Judge and listening checks

- **The default judge throughout**, as step 4 and arm A use it. Judge v3 is beside it, never
  deciding.
- **Controls the judge cannot see** (stage 0c) are never searched or learned against it; they get
  their declared rules.
- **Listening:**
  - stage 1's page (gate, doubler, room, near-ties);
  - after any stage F test, a record-match page on 5 guitar-exposed parts: S, today's space and the
    full space, blind, letters drawn at random.
  - The listener's answers are trusted, and layout confounds are caveats.

## Approvals needed

- **The user's choices:**
  - leaving switched-off knobs out or neutral labels: **decided 2026-10-22, left out** (masked out
    of losses, scores and fits; neutral values only where a value must be written);
  - whether a declared rule counts as setting a control the judge cannot see (output gain, pan,
    stereo widths): **open**; stage 0c's screen informs it.
- **Training:** the 2D pilot's runs (about 1 h), D_full's 3 seeds (5–7.4 h), and a Tone King
  direct model (5–7.4 h) each need the user's approval before they start.
- **Renders:** stages 0–2A, about 30–32k with no training. Each runs after its own reviewed plan.
- **Paid or downloaded:** nothing.
- **Disk:** at most about 3 GB, against today's 118 GB free and the 31 GB guard.

## Stages 0 and 1, as built (2026-10-22)

Declared before any render, in `learn/every_control.py` (tests: `tests/test_every_control.py`;
ledger: `every-control-stage0`, `every-control-stage1`). Details the plan left open are decided
here; each is flagged for the review.

- **0a, the table.** One entry per writable manifest control (Morgan 131, Tone King 94 plus 6
  strings and paths), with its family, source (searched today, measured, stage 1, screen, amp
  choice, rule, never), gate and neutral value. The test walks both manifests and checks the
  plan's counts (today 12/17/14, to add 75/74/73, Tone King 94). Neutral values are knob ceiling
  2's where it declared them (pedals, the effects' "on" values, the spring), knob ceiling's flat
  EQ, and otherwise the plugin's own `Default.xml` (tested against it).
- **The masking helper.** `mask(x)` gives each control's weight (does it sound in `x`?) and
  `neutralise(x)` the canonical form. The gates are the plan's list. Pan and stereo count only with
  both cabs on under a mono judge (`mono=False` keeps them for a written stereo preset).
- **0b, amp choice.** Per part and direction with all three amps usable: log(held half of the amp
  with the lowest K_S search half) − the mean log held half of the three; per part the mean over
  directions; the plan's rule.
- **0c, the screen: 60 renders, not about 40.** Morgan: 3 cells (every 8th sorted part, on PR12,
  SW50R, AC20), from S: both cabs on (rendered twice, the repeat), each pan, stereo and phase moved;
  the delay on (knob ceiling 2's "on" values, sync off), width and ping-pong moved; the doubler on
  (spread 6), spread moved. **Added:** Tone King, 2 cells (the first clean and first crunch part,
  on their class starts): both cab pans and phases, and the delay's stereo mode, which stage 1's
  Tone King search would otherwise search blind. A move is a switch flipped or a knob to the far
  end of its range. **Invisible:** the score against the record moves by |log| ≤ 0.005 on both
  halves in every cell. Invisible controls keep their rule; **visible ones join a stage-1 group**
  (pan, stereo with phase; width and ping-pong with the effects group; spread with the doubler;
  Tone King's with its search). The plan named only the groups, not this routing.
- **0d, Tone King's renderer.** The class start's dry preset (tk-baseline) is the base state; each
  render writes only the controls that differ from it, through the pack, in a reused process with
  isolate=True and the bounded server, behind a 1-s preroll that is cut off (as tk-baseline). Its
  check: the canonical start must repeat `tk-baseline/distances-dev.json` within 0.005 log.
  Switches search as "0"/"1". `tk-smoke` runs the plan's 30-render smoke (speed, repeat).
- **Stage 1, Morgan: 48 cells (knob ceiling 2's 24 parts × 2 directions, each on its amp), from
  each cell's stored stage-2 setting.** That setting is rendered once more (after a priming render)
  and must repeat its stored score within 0.005. Each group is then searched on its own, 30
  renders, starting with its feature switched on (its stored knobs if it was on, else neutral):
  - gate: the threshold (−96 to 0 dB);
  - doubler: the spread, if visible (else one render: on at spread 6);
  - rooms: both rooms on at −6 dB (for each cab that is on), their switches and levels, **and the
    left cab's switch** with its level (−40 to +6 dB). The plan named the left cab's level; its
    switch is in the same "cab rest" row and no other group covers it;
  - phase (34 cells with both cabs on): the phase switches, plus pan and stereo if visible;
  - effects (6 cells whose stage 2 turned on tremolo or delay): tremolo level, tape drive, plus
    width and ping-pong if visible.
  A group's best is adopted only if it beats the stage-2 setting by ≥ 0.005 (log) on the search
  half (knob ceiling 2's wet margin); otherwise the cell reads 0. The reading is the plan's: held
  half, the group searched minus not searched. About 4.7k renders, cap 7,296.
- **Stage 1, Tone King: 48 cells, 150 renders each (7,248).** Its space: 77 controls, plus the
  screened ones the judge can see. Rules: the delay's sync off; its display, tap, tempo and sync
  notes at the start's values; the sections held on; output gain at the start's. Level ranges are
  narrowed to −40 to +6 dB (cab and room; the manifest allows −48 to +24 and −60 to +12),
  as Morgan's mic level. Beside the reading: Tone King searched − Morgan's stored stage-2 setting
  (descriptive).
- **Stage F is not used.** Stage 1 runs on knob ceiling 2's development parts, as the plan
  declares; like knob ceiling 2 it is a separation-free oracle (the true DI), with no stem.
- **Listening: 8 trials.** Per group (gate, doubler, rooms), the 2 adopted cells with the largest
  held gains (one trial per part), leftovers filled by the next largest gains, then 2 near-ties
  (|held| < 0.005) drawn at random; the record, then the stage-2 setting and the group's setting,
  the letter drawn at random per trial. The gate and the doubler enter only if the listener also
  picks the group's setting on both of its clear-gain trials (knob ceiling 2's reading); rooms by
  the judge, listening descriptive.
- **Smoke (2026-10-22, 56 renders into a scratch folder, one process, nothing kept):** Tone King's
  renderer repeats tk-baseline's stored start score to 3e-6 (log), about 1.5 s a render with the
  preroll; Morgan's stage-2 setting repeats exactly. Two corrections came from it:
  - Tone King's amp tremolo speed is audible at depth 0 (0.00036 log), so it is not gated by the
    depth (the PR12's dwell at spring level 0 was checked bit-identical, so that gate stays);
  - Vintage Trem's dry start has the EQ section off; a section the start has off is held on with
    its features switched off (the same sound), so the start repeats.
- **The machine:** every render command waits for a slot under 3 render processes machine-wide
  (`local_objective.RENDERS` lists them) and stops below 31 GB free; cells are written atomically
  and resume; shards by `--shard i/n`.

