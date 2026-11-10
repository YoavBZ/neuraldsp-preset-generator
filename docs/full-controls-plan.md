# Every control on the real rows: labels, training and measurement for the whole plugin (C0 to C5)

**Amendment 2 of the [every-control plan](every-control-plan.md).**

## Status

- **Declared** 2026-11-09, before any render, on the user's word: "go, but make sure that everything will eventually be measured and trained on. We must learn and be able to predict every single control." That repeats their coverage rule of 2026-10-21 and 2026-10-22, "every control is learned".
- **Amended the same day after its independent review.** The review found missing controls, a wrong start, a wrong ablation and too low a budget, and asked for a stop rule that converges. All of it is folded in below.
- **The user's go for C1a:** "Go", at about 10,000 renders, with the gate included.
- **The user's word on ranking pages:** several presets may share a rank, instead of a "can't tell" answer.
- **Every later step** with renders beyond C1a's, or with training, went to the user with its cost before it ran, until 2026-11-10. Then the user said: "next time, I prefer you to leverage the night and render or train whatever is needed instead of waiting for my approval. At max, I can stop the ongoing process if needed." From C2 on, a declared and reviewed step launches without a wait, and the user is told what runs.
- **C1a ran** on 2026-11-09 (10,237 renders, audited; [F69](pipeline-fix-plan.md)): by the score −0.205 on N12 and −0.030 on BKS (undecided; crunch −0.052), against the label. The user said yes to C1b (2026-11-09, at about 8,500 renders; the built C1b counts 9,070–9,608 after its review) and to a blind A/B page of C1a against the label; both are declared before they render.
- **C1b ran** on 2026-11-10 (8,391 renders, audited; [F70](pipeline-fix-plan.md)): by the score −0.008 on BKS and −0.004 on N12 against C1a, both undecided; on BKS most of it sits in the records whose mic changed. Its 3 kept effects are all false (N12's captures), so its keep rule is not used for labels. The C1a page is out with the user.
- **Bookkeeping.** Ledger `pipeline-fix`, `phase_c1a`, `phase_c1a_a1` (Amendment 1), `phase_c1a_outcome`, `phase_c1a_ear` (C1a by ear), `phase_c1b`, `phase_c1b_outcome`, `phase_c2`, `phase_c3` and `phase_c2b`. Code: `learn/full_controls.py` (C1a), `learn/c1a_ear.py` (C1a by ear), `learn/full_controls_c1b.py` (C1b), `learn/full_controls_c2.py` (C2), `learn/full_controls_c3.py` with `pipeline_fix train-ft --c3` (C3) and `learn/full_controls_c2b.py` (C2b), tests `tests/test_full_controls.py`, `tests/test_c1a_ear.py`, `tests/test_full_controls_c1b.py`, `tests/test_full_controls_c2.py`, `tests/test_full_controls_c3.py` and `tests/test_full_controls_c2b.py`. Results go in [pipeline-fix-plan.md](pipeline-fix-plan.md), F69 on.

**The every-control plan's stage 1 never ran.** It is a true-DI oracle for the groups with no number, about 13–14k renders. It was approved on 2026-10-22 and waited for a trusted data list. Then the work moved to the trusted data and the pipeline fix. This amendment carries its goal onto today's route (FT2 and its real rows). It folds stage 1's never-measured groups in as C1b.

## Why
- **The goal** is the most accurate preset over all settings, from a song alone.
- **What the labels set.** Today's labels (J0's search through the true DI, `knob_ceiling.space`) set the input gain, each amp's own knobs and switches, the two mics, and the cab placement: position, distance, the right cab and its level.
- **What FT2 learns.** Only those. It holds every other control at S, on purpose: on real rows, unsearched heads taught S's constants (F55).
- **This is not the first model of every control.** T3's D_F5 and D_CC set all 115 Morgan controls from plugin renders. F5 was not shown better on real songs, and its time-effect heads learned nothing ([T3 design](trusted-data-t0-design.md)).
- **How C3 differs:** it learns the new controls from search labels on real rows, recorded through captured and real amps, not from plugin renders alone. That is the route on which FT2 beat S.
- **G1** (2026-11-09, zero renders) split FT2's gap to the label over drive, tone and cab. It can't see controls that the label never set.
- **What the earlier ceilings measured on other development data,** with the true DI and no model:
  - **The EQ on top of the knobs:** −0.079 [−0.117, −0.040], 14 of 14 bands ([knob ceiling](knob-ceiling-results.md)).
  - **The pedals with a wider input gain:** −0.023 [−0.033, −0.013], about half from the pedals and mostly on crunch ([knob ceiling 2](knob-ceiling-2-results.md)).
  - **Time effects:** −0.010 [−0.022, +0.002]. They are wet on 14 of 48 cells. Where the judge's gain was clear, the listener heard wet as closer on 3 of 3.
  - **Amp choice:** −0.044 [−0.062, −0.026] (every-control stage 0b).
  - **Visibility:** every screened control moves the judge (stage 0c).

## C0: coverage

Morgan's 131 rows are `every_control.table("morgan")`. Tone King's 100 rows are `every_control.table("toneking")`. Today: labelled on real rows (L), trained in FT2 (T), measured (M).

| Family (rows) | L | T | M | Route | Blocker |
|---|---|---|---|---|---|
| Input gain, amp knobs and switches, mic types, cab position and distance, right cab on and level (25) | yes | yes | F43, G1 | today | none |
| Amp choice, `selectedAmp` (1) | BKS: C1a's per-unit argmin on 40 units; C2 searches all three forced amps of every BKS row. **GOAT: C2b** (declared, not yet run), one forced amp a unit until then | no: the amp head is masked on real rows | stage 0b, −0.044; C1a: the chosen amp beats a blind one by −0.058 | BKS: the argmin over C2's three labels. GOAT: **C2b** (declared in detail below): the argmin over its three like-for-like `K.space` labels | GOAT: C2b's renders (at most 22,684); training the head on real rows waits for C3b |
| Amp EQ: on, 9 bands, high- and low-pass, ×3 amps (36) | C1a; C2 on every FT2 row | C3 | knob ceiling (d); C1a (F69) | C1a, C2 | none |
| Pedals: compressor 5, drive 1 4, drive 2 5 (14) | C1a; C2 on every FT2 row | C3 | knob ceiling 2; C1a (F69) | C1a, C2 | none |
| Gate: on, threshold (2) | C1a; C2 on every FT2 row | C3 | C1a: inert (F69) | C1a, C2 | none |
| Time effects: reverb, delay, tremolo, with tremolo level and tape drive (17) | the switches off by source in C2 (not searched, not a learned label); the knobs masked | not in C3: masked on real rows and held at S in every answer (C3 in detail) | knob ceiling 2; C1b: the 0.02 keep rule let false effects through (3 of 31 N12 records, 3 of 114 searches), not fit for labels (F70) | in order: (1) at zero renders, each effect switch's loss on NS against its marginal; (2) a reader that hears effects through a backing on rows whose truth is known; (3) only then real wet rows: Morgan's effects, amp and cab sections off, rendered onto dry real targets (check the chain order first) | no reader hears effects through a backing: W, trained on exact plugin labels, reads NS at about the marginal (switches 0.612 against 0.617), and F48 to F52 found none |
| The amp's spring: pr12 Reverb and Dwell, sw50r Reverb (3) | `springOn` off by source in C2; the knobs masked | as the time effects | knob ceiling 2; C1b: as the time effects (F70) | as the time effects | as the time effects |
| Room mics: on, level, per side (4) | C1b; C2 stage A | C3 | C1b: barely tested (one-cab records tried the left room on at −6 dB once; levels searched only where a room went on, 1 record) (F70) | a real test of the rooms; still open | stage A's budget: 16 evaluations over 7 controls |
| Left cab on and level (2) | C1b; C2 stage A | C3 | C1b: mostly balance (34 of 38 two-cab records moved it, 4 to +6 dB; 3 N12 records turned it off) (F70) | C1b, C2, with both cabs on | none |
| Cab phase, left and right (2) | C1b and C2: the right cab's phase, both cabs on | C3 | screen: J0 hears it up to 0.296; C1b: flipped on 0 of 38 two-cab records (F70) | C1b stage A; one switch carries the relative phase a mono judge hears, the left held | the left switch's own meaning is stereo: with the stereo row |
| Stereo: doubler on and spread; cab pan and stereo per side; delay width and ping-pong (8) | the doubler off by source in C2 (the sources are mono); the rest no | no | screen only | needs a stereo term from the song's stereo image | J0 is mono; no stereo target yet |
| Mic types outside GOAT's short lists | no | no | never: C1b and C2 re-test the short lists only | widen the lists, or a full mic-alternative stage (C2 does not widen them) | budget |
| Combinations of time effects (two or more on) | no | no | never | a second effect searched on top of a kept one, once a keep rule passes on a source with known effects | budget, the keep margin's comparisons multiplying, and the time effects' blocker above |
| Tempo sync: delay sync, tempo and sync note; tremolo sync and sync note (5) | no | no | none | written free, as ms and Hz; tempo-locked delay needs the song's tempo from beat tracking | no beat tracker in the pipeline |
| Section switches: amp, EQ, pedal, cab, effects (5) | no | no | none | held on; each section's own switches carry the same sounds | none: a reparametrisation |
| Output gain (1) | no | no | invisible: the judge removes level | the loudness match | none |
| Room mic types (2) | no | no | none | no UI control in the plugin | none: not exposed |
| Custom IR paths, left and right (2) | no | no | none | empty means the internal cab; learning them means shipping an open IR set | **the user's decision** |
| Transpose, preset name (2) | no | no | none | pitch, not tone; a name | none |
| **Tone King: all 94 controls** (100 rows) | no | no | stage 0d's renderer smoke only | its own oracle and labels, as knob ceiling 2 deferred | a renderer that can search; switches stored as "0" and "1" |

**No row leaves the table.** A small measured gain sets a family's priority, never whether it is learned. A family with no working route stays open, with its route and blocker named.

## The steps
- **C1a** (approved; this plan in full below): the EQ, pedals, compressor and gate on top of the label. On N12's 31 units and BKS's 40, as labels and a measurement.
- **C1b** (declared before it runs; the user's go): the time effects, the spring, the room mics and the left cab, on C1a's records.
  - Each effect is searched on its own, rendered in a fresh process, with a keep margin declared first (knob ceiling 2's stage 2).
  - Stage B re-tests GOAT's short mic lists (`night2.mic_lists`, the same lists N12's v2 labels came from), now with an EQ re-tune beside each mic, since the EQ can compensate for a wrong mic.
  - The mics outside those lists stay open in C0. The route is to widen the lists in C2, or to run a full mic-alternative stage.
- **C2** (declared in detail below): C1a's search at budget 200 and C1b's stages A and B on every FT2 real training row, with no effect stage. That is GOAT's 214 (`goat_labels`) and BKS's 306 (`real_labels(2)`: all three forced amps of every unit), of which C1a's 40 come last, continued.
  - **Cost:** at most about 129k renders, plus about 6.1k for C1a's 40.
  - **C1a's BKS records are continued, not searched again.** Each is replayed from its stored trials (`coord_search` only truncates at its budget) at zero renders, and only the evaluations past 100 are rendered. The replay was checked exact on all 40 at zero renders. The 6 that ran to 300 already hold their 200 incumbent.
- **C2b** (declared in detail below): amp choice on GOAT. `K.space`'s main stage, exactly as GOAT's stored labels were searched, on each labelled unit's two other amps; the unit's amp is the argmin over the three. At most 22,684 renders, run after C3's read. No training: the amp head on real rows is C3b's.
- **C3** (the user's go, training): FT2 retrained on the full labels.
  - **Masks.** Each record trains only the heads its own search covered: `searched_heads` generalised to a per-record space. For C2 records that is `searched_keys`: C1a's space plus stages A and B, never an effect knob. `EQActive` is masked: it is forced on. Unmasking unsearched heads would repeat F55.
  - **The effect switches** (C2's `known_keys`, off by source) are trained as C3 declares before it trains: masked on real rows, or unmasked with a read on audio that has effects (C0).
  - **A C1a or C2 label that fell back** (stored as `None`) falls back to its source label, with the source's `K.space` mask. A C2 record refused at its start, or for an inexact replay, does the same.
  - **The read is H4's,** with one row beside: C3 with the new controls at S, because C1a also re-tunes the core knobs.
  - **Adoption, per family:** "C3 less C3 with that family at S" is at or below 0 by the score, and C4 does not reverse it. A family not adopted is written at S in the product and stays open, with its next route and blocker named.
- **C4:** a blind page of full-control presets against FT2 and S.
  - Ranks allow ties: several presets may share a rank, and a tie counts as no preference. Repeats of the decision pairs.
  - Effect pages are guitar-only with instant switching.
  - It uses cards nobody has heard (below).
- **C5** (the user's question, 2026-11-09; declared before it runs; the user's go): the heavy clean-up re-tested on the full-control model, below.
- **When the sequence ends.** It returns to the user when every row of C0 has an adopted route or a named open one, with its blocker.

## C1a in detail
- **Records:**
  - **N12's 31 units:** `score_ear.wide_units()`, each with its `captures2/search` record. The search and held halves are as stored.
  - **BKS's 40 stage-1 units** (`pipeline_fix.stage_units`, stage 1), one record each. The record is the amp whose stored label has the lowest `best.judge[search]`. That is the search's own choice, made on the search half, and the first real amp label.
  - **real_out:** the 2 BKS units in H4's real_out (`pipeline_fix.h4_exclusions()`) are searched and reported apart. BKS is one band, so its clusters are its DIs.
  - **N12's labels are measurement only.** They never become C2 or C3 training rows: N12 is FT2's, H4a's and H4b's read set.
  - **Not touched:** V-real, NS, the panel, the reserve (`HELD_BANDS` apart from BKS), and GOAT (it is C2's).
- **The unheard-card pool for C4 and C5.** This is N12's 31 units less every unit already heard on N12's page and H4b's (`ear-wide/plan.json`, `ear-wide/h4b/plan.json`). That leaves **7 units**, or 9 if N12's unplayed spares count: Ale Lak 2, Storm Of Particles 2, Dark Ride, The Travelling Band (clean), and Rebuild The Evil (crunch). Counted 2026-11-09 at zero renders.
  - **No top-up source exists yet.** It was checked at zero renders:
    - batch 2's 32nd trusted unit has no finite held judge;
    - its other 115 units failed the gate;
    - batch 1's units trained N9's and N10's arms;
    - GOAT and BKS are training rows;
    - V-real and the panel are held out.
  - **C4 needs a new source before it is built,** such as a third capture batch, on the user's yes.
- **Start:** the record's stored label, with one declared change. Every S already has its amp EQ and the EQ and pedal sections on, so `knob_ceiling2.stage1_start` changes only inert keys: the knobs of pedals that are off, set to neutral.
  - **The declared change:** the start has the gate on at the factory threshold, as `every_control.group_plan("gate")` does. A label with the gate off gets it on at −80 dB, as the factory presets do: 102 of 107 have the gate on, 74 at exactly −80, median −80. A label with the gate on keeps its threshold.
  - So the search tries the threshold of a gate that is on, and the switch beside it, not a flip to a near-inert gate.
  - **The check:** the first evaluation's search-half value must equal `best.judge[search]` within 0.005 in log. That also verifies that the gate on at −80 dB is inert on the record. Its render sha is recorded beside `best.render_sha256`. A miss stops the shard.
- **Space:** `knob_ceiling2.stage1_space`'s controls, about 37 to 42 an amp. The core knobs have input gain at FT2's head range, −20 to +12 dB, not −24. Then the amp EQ, drive 1, drive 2 and the compressor, plus the gate: `gateActive` as a switch and `gateThreshold` from −96 to 0 dB.
  - The mic types are held at the label's.
  - **The factory threshold** is the median threshold of the factory menu's presets with the gate on, read from the preset files at zero renders (`full_controls.factory_gate_median`). The draw refuses if none has the gate on.
    - **Used: −80 dB.** 102 of the 107 factory presets have the gate on, with a median of −80.0, the same as the table's neutral. `c1a-draw` re-reads it and refuses on a mismatch.
  - **Canonical form:** `canon_pedals`, then the gate's: an off gate's threshold stays at −80 dB. A move that changes nothing audible costs no render.
- **Search:** `knob_ceiling.coord_search` from the start, with `canon`, seed 20261123, which no other run uses.
  - **Budget:** 100 evaluations on every record.
  - **The calibration subset:** a seeded subset of 12 records, 6 from each set, drawn by `c1a-draw` with seed 20261124, runs on to 300. The search is deterministic and the budget only truncates it, so the subset's first 100 evaluations are its 100-budget run.
  - **Checkpoints:** incumbents at 50, 100, 150, 200 and 300 evaluations, with both halves' judge from the in-process render.
  - **Declared now: C2's budget** is the first checkpoint at which the median, over the subset's records, of each record's ratio gain(n) / gain(300) on the search half reaches 0.9. The gain is ln(d_start / d_incumbent). Records with no gain at 300 are left out.
- **Harness:** `pipeline_fix.search_units`'s and `cmd_real_search`'s render path.
  - The audio: `song_bank.measure` of the section's DI, `pretrain_set`'s trim, `real_amp_track` for the reference, and the record's stored lag.
  - The renderer: `cc_build.new_renderer`, with edits in `sorted_x`'s order.
  - Each record runs in its own renderer process, primed once with its own start. At most 3 render processes, by `local_objective`'s cap. The disk guard is 31 GB.
  - `fallback_reason` is applied to each new label: a silence floor on the render's peak, or a refused search-half objective. It is not a test of high peaks. A fallback label is stored as `None`.
- **Recorded per record:**
  - **The record itself:** every evaluation's setting and both halves' judge, the checkpoints, and the in-process best.
  - **Fresh renders** (each in a new process with one priming render, as `audibility_measure.fresh_render`):
    - the 100-budget best;
    - the 300-budget best on the subset;
    - four ablations of the 100-budget best: pedals reset to the start's, amp EQ reset to the label's, both reset, and the gate reset to the start's. That is the gate on at its start threshold, or, for Amendment 1's gate-off starts, the gate off.
  - All of them are judged on both halves.
  - **Reuse:** an ablation whose canonical setting equals the best's reuses the best's fresh render, and the 300 best does too when it equals the 100 best. Each is marked `same_as_best`.
  - **Also stored:** the start's settings (`start_settings`), and `measurement_only: true` on N12's records.
- **The label is stored in today's record schema** (`unit`, `amp`, `select`, `search`, `held`, `lag`, `s_judge`, `curve`, `best`, `label`). It goes in parallel directories, `captures2/search-c1a/` and `real/search-c1a/`, with each record's searched-key list for C3's per-record masks.
- **Rows** (held half, ln ratio, per set, all and by class; clustered by DI for BKS and by band for N12; 90% cluster-jackknife t intervals, df = clusters − 1, record-weighted; beside each, the band-weighted reading from `pipeline_fix.clustered` with its per-cluster breakdown; the threshold-move count, the start row and the median gains added 2026-11-09, before any C1a result is read):
  - **The primary:** C1a's fresh 100-budget best against the stored label.
  - **Beside:**
    - Each ablation against the best.
    - Each pedal's state changed from the label's, counted, and, for each pedal on in the best, its knobs moved from the label's.
    - The amp EQ moved from S's curve, counted.
    - The gate's state changed from the start's, counted, and the threshold moves with the gate on (the threshold moved from the start's, −80 in C1a, with the gate on in the best), counted, over the main records with real_out beside.
    - The start against the label, on the held half, at zero renders: the start's first trial against the stored label.
    - The label against S, for scale.
    - The subset's checkpoint curves, from the stored checkpoint judges: on the search half (which sets C2's budget) and on the held half beside it, with the median gain at each checkpoint on both halves beside the median ratio, so records that lose are not hidden.
    - The subset's held-half rows per set: ln(fresh 300 best / fresh 100 best) and ln(fresh 300 best / label).
    - BKS's amp choice, chosen on the search half and read on the held half: the chosen amp's log held judge less the mean over the three amps, as stage 0b read it.
    - real_out apart.
- **What it leads to:** the labels and the budget for C2, and the size that orders C1b and C2. There is no bar.
- **Cost, an upper bound:** 71 records × (1 priming + 100 + 5 fresh renders × 2) ≈ 7,900 renders. The subset adds 12 × (200 + 2) ≈ 2,400. That is about 10,300 in all, about 2.5 h at H4a's measured rate. The reuse above can only lower it. No training.

### C1a, Amendment 1 (2026-11-09): a start miss is tried with the gate as in the label, else refused

- **When it was declared.** After shard 2 stopped on one record's start check, and before any C1a result is read.
  - The record: `cap/1xiluf3lhnm#ac20`. The gate-on start scored 2.9622 against the stored label's 2.9774, an ln gap of 0.0051.
  - So the gate at −80 dB may act there: the gate-on start scored about 0.5% better.
  - Shards 0 and 1 kept running, and their records are kept as written.
- **The rule, on a start miss:**
  1. One more start is rendered, in its own process with one priming render, as the start is: the same start with the gate as in the label (off, its threshold canonical at −80).
  2. **If it matches the stored label within 0.005,** the gate alone caused the miss. The record runs from this gate-off start, flagged `start_gate: "off_after_miss"`.
     - Both start values go in `first_start_miss`, with the gate-off render's sha and whether it is bit-identical to the label's.
     - The gate stays searchable: its flip tries the gate on at −80, which may act there. Step 2's search tests it, and the threshold moves if that helps.
     - If that run's own first evaluation then misses, the record is refused, with that value as well.
  3. **Otherwise** the record is written refused (`start_gate: "refused"`), with both values, and the shard continues. A shard never stops on a start miss.
- **The gate rows have two meanings, stated before any read.**
  - On a gate-on start, the gate ablation resets to the gate on at −80, and a flip means turning it off.
  - On a gate-off start, it resets to the gate off, and a flip means turning it on.
  - So `c1a-report` gives the rows over gate-on starts beside the pooled rows, and lists each gate-off start apart: its unit, primary, gate ablation, and what the best did with the gate.
- **C2 inherits this rule** for every record it searches.
- **Resume.** Records already written, refused ones included, are skipped.
- **Counts.** The shard's last line and the report count each kind: on, off after a miss, refused. Records written before the amendment carry no flag and count as on.
- **Cost.** A gate-only miss adds 4 renders (the missed start's process and the second start). A refused record costs 4 renders, or 6 when the gate-off run itself misses.

### C1a by ear (declared 2026-11-09, after C1a's score read and before any render for it; ledger `phase_c1a_ear`)

- **Why.** C1a's result is J0's alone (F69). No real-song verdict stands on the score alone, so this page reads it by ear.
- **The user's yes (2026-11-09).** "Yes" to "a short blind A/B page, about 14 items, comparing the current label with the C1a preset … costs about 30 renders. Ties are allowed."
  - The count was wrong: every item needs two fresh renders, each with its priming render. The page costs **56 renders** (14 items × 2 candidates × 2); the user was told the corrected count (2026-11-09) before any render. The repeats reuse their clips.
- **Items, 14 first hearings and 2 repeats.**
  - **N12's 7 never-heard units, all of them.** Each is outside N12's cards and spares, and was never played on a preset page (N12's or H4b's; the record-only capture-ear-2 page aside).
    - `cap/1w1lkv30jfn#ac20` and `cap/a9j26sllzrq_a2#ac20` (Storm Of Particles).
    - `cap/9nbhb9zvawu#ac20` and `cap/piou1nfi5cm_a2#ac20` (Ale Lak).
    - `cap/3iqknlf6u0x_a2#sw50r` (The Travelling Band) and `cap/rtxifphieu#sw50r` (Dark Ride).
    - `cap/wji8wcrx9yf#sw50r` (Rebuild The Evil, crunch).
    - The other six are clean. The unplayed spares are none: N12 played both of its spares.
  - **7 of BKS's searched records outside real_out, at most one a DI.** Seed 20261125: 7 of the 8 DIs, then one record each. That gives 4 crunch and 3 clean.
  - **2 repeats of the decision pair,** one from each set, seeded (20261126). Each sits at least 4 items after its first hearing, with the letters swapped.
- **Each item.**
  - The record's held half is the reference.
  - Two candidates, the letters shuffled per item, with the label on A for half the first hearings:
    - the stored label (`best.settings` of the source record);
    - C1a's best (its 100-evaluation `label`).
  - **Rendering.** Both are rendered fresh through the record's DI, in their own process with one priming render, on `full_controls`' `fresh()` path: `AM.fresh_render`, the 0.25 s trim, isolate=True, at most 3 render processes.
  - **Check.** Each render's held-half judge must match the stored one within 0.005 (ln): the source's `best.judge[held]` for the label, and C1a's `fresh.best.judge[held]` for C1a. A miss stops the shard and goes to the user; no partial page is built.
  - **The clips** are the held half's judge window at the record's lag (`score_ear.h4_window`). They are levelled as a group, as earlier pages are.
- **Answers.**
  - Per item, A and B each get a rank: 1 is closer, 2 is further. Both may hold the same rank, which is a tie; that is the user's rule, with no "can't tell" button.
  - Closeness ratings and confidence are optional.
  - Stored in the artifact's `answers/<build>` document.
- **The read, declared.**
  - **The primary:** the share of first hearings where C1a is ranked above the label, a tie counted as a half. It uses a jackknife t clustered by N12's band and BKS's DI, one-sided against one half (`score_ear.jackknife_t`). No bar: the share and its interval are the result.
  - **Beside:**
    - the same by set and by class, and BKS's row again clustered by song: its 7 DIs come from 2 songs (5 Bulldozer, 2 TooMuch);
    - the repeats' agreement (the same preference on both hearings);
    - J0 against the ear: on the items not tied by ear, how often J0's held-half sign, ln(d_C1a / d_label) from these renders, agrees;
    - the mean closeness gap where both were rated.
  - Each row also carries the share's 90% jackknife interval (`score_ear.interval`).
  - **The page is read** if at least 10 of the 14 first hearings are answered.
- **The decision rule, declared before any render.** It reads the primary row:
  - **C1a heard below the label:** a share under 0.5 with the mirrored one-sided p (1 − p) below 0.05. C2's targets then go to the user before C2.
  - **C1a heard above the label:** a one-sided p below 0.05. This supports C2 on C1a's recipe.
  - **Otherwise undecided:** C2 goes ahead on F69, by the score, and the ear read is recorded as underpowered, not failed.
- **Power.** With 14 cards in these clusters, the chance of an "above" read:

  | True share | Power |
  |---|---|
  | 0.6, no ties | about 15% |
  | 0.7, no ties | about 39% |
  | 0.8, no ties | about 72% |
  | 0.9, no ties | about 96% |
  | 0.75, with ties | about 79% |
  | N12 at 80–90% for C1a, BKS near ties or a coin flip | 37–48% |

  F69's BKS gain is small, and near-ties are likely there. **An undecided read is the likeliest outcome**, and it says nothing against C1a.
- **What it leads to.** It is a description; nothing is adopted from it alone beyond the rule above.
- **Code:** `learn/c1a_ear.py` (`c1a-ear-draw`, `c1a-ear-render`, `c1a-ear-page`, `c1a-ear-read`). Tests: `tests/test_c1a_ear.py`.

## C1b in detail (declared 2026-11-09, before any C1b render)

- **Status.** Declared on the user's "Yes" to C1b at about 8,500 renders.
  - It comes after C1a's results were read: by C1a's report, C1a's best against the stored label on the held half was −0.205 [−0.319, −0.091] on N12 and −0.030 [−0.073, +0.014] on BKS, and C2's budget was set at 200.
  - Nothing of C1b has been rendered.
  - Ledger `pipeline-fix` `phase_c1b`. Code: `learn/full_controls_c1b.py` (`c1b-draw`, `c1b-search`, `c1b-report`), tests `tests/test_full_controls_c1b.py`.
- **Records.** C1a's 71 records, read from `c1a/records.json` and C1a's outputs. The sets, clusters and real_out apart are as in C1a, and N12's records stay measurement only. A C1a record that was refused or fell back is left out and named; C1a had none.
- **Start.** Each record's C1a `label`; `label_300` is not used. It must be dry: a start with a time effect, the spring or the doubler on stops the shard. C1a's labels are dry, since every S is.
  - C1b's canonical form changes only inert keys, checked at zero renders on all 71: a room's level goes to neutral while the room is off; an off effect's knobs go to its declared on values, with the sync free; the spring's pseudo-switch is set from its level.
  - **The start check:** the first evaluation must be within 0.005 of C1a's stored best (`best.judge[search]`).
  - **On a miss,** in Amendment 1's manner:
    - A second start, the C1a label as stored with no canonical form, runs in its own process with priming.
    - If it matches, the record runs from it with no canonical form anywhere, flagged `start_kind: "raw_after_miss"`.
    - Otherwise the record is written refused, with both values, and the shard continues.
- **Order: A, then B, then the effects last.** The request listed the effects first. They go last for three reasons:
  - **Carry-over.** Morgan's time effects run on across renders in one process. So the dry stages share one process, as C1a did, and only the effect stage needs a process per effect.
  - **Precedent.** Knob ceiling 2 searched the tone first and the effects on top.
  - **A kept effect would otherwise sit under every later evaluation.**
- **Stage A, the rest of the cab.**
  - **With both cabs on:** the left cab's switch and level (−40 to +6 dB); each room mic's switch and level (−40 to +6 dB); and the right cab's phase switch. One phase switch carries the relative phase that a mono judge hears; J0 hears it up to 0.296 (stage 0c). The left switch stays as stored.
  - **With the right cab off:** the left room's switch and level alone. The left cab must stay on, and its level is then only the output level.
  - The room mic types stay as stored: they have no UI control.
  - A room switched on starts at the table's neutral −6 dB, an acting level.
  - `knob_ceiling.coord_search`, budget 16, seed 20261125, in the dry process, primed with the start.
- **Stage B, the mic re-check jointly with the EQ.** The mic type of each cab that is on, and the amp EQ (9 bands, both filters), searched together by `knob_ceiling.knob_search`. Budget 48, seed 20261126, in the same dry process.
  - **The mic alternatives are GOAT's label-derived short lists** (`night2.mic_lists`, 3 to 4 a side, with the current mic). These are the same lists N12's v2 labels came from, so stage B re-tests them, now with an EQ re-tune. Each record stores the lists it used.
  - **The budget's shares are 25%, 50% and 15%:**
    - **Main stage, 12 evaluations,** over the EQ. They never try a mic, because the first sweep over the 11 EQ dims doesn't finish.
    - **Alternatives, 24 evaluations.** Each short-list mic is set on the incumbent and followed by a quick re-tune of the EQ's 3 key dims (steps 0.25 and 0.125). With both cabs on, that is 5 to 8 alternatives at 3 or 4 evaluations each. With one cab, it is 3 or 4 alternatives at 6 to 8 each.
    - **Restarts, 6 evaluations:** two of 3 each, from the best alternatives. The rest goes to a final pass.
- **Stage C, each time effect on its own,** on top of B's best, as knob ceiling 2's stage 2: reverb, delay, tremolo, and the amp's spring (pr12: level and dwell; sw50r: level).
  - **Its knobs:** knob ceiling 2's, plus the two it left out. Those are tremolo level and delay tape drive, each continuous 0 to 1 as `every_control._dim` defines them, with declared on values for an off effect of 0.5 and 0.
  - **The search:** each effect is switched on at its declared on values, and its knobs are searched by plain `knob_ceiling.coord_search`, so ±0.25 is tried on every knob first, and delay time and tremolo rate reach their range. At 3.5 evaluations a knob: reverb 18, delay 21, tremolo 10, and the spring 7 or 4. Seed 20261127 on.
  - **Each effect runs in its own renderer process,** primed with its own start, so no other effect's tail carries in.
  - **The keep decision is on fresh renders.** Within an effect's process its own tail carries over between candidates. So an effect whose in-process best beats B's in-process best by the margin is rendered fresh, in its own process with priming, and compared with B's best rendered fresh. It is kept if ln(wet / dry) ≤ −0.02 on the search half.
  - **At most one effect a record:** the best of those kept. Combinations stay open in C0.
  - **The sync is written free** (`knob_ceiling2.FREE_SYNC`). Tempo-locked delay stays open in C0.
- **The keep margin, 0.02 search-half log, declared before use.**
  - Knob ceiling 2 declared that a margin above its 0.005 must be set before the next use. There, two near-ties passed 0.005 by a hair while the listener split, and the 3 clear-gain trials the listener confirmed were far past 0.02.
  - Four effects compete on the search half, so the best of four noisy candidates is biased low.
  - 0.02 is four times the start tolerance, about 2% in distance.
- **Budgets,** grounded in C1a's calibration and knob ceiling 2.
  - On C1a's 37 to 42 dims, 100 evaluations (about 2.5 a dim) reached a median 70% of the 300-evaluation gain, and 150 (about 3.7 a dim) reached 84%.
  - C1b gives about 2.3 a dim to stage A on two cabs (8 on one), 3.7 to stage B (whose EQ C1a already searched), and 3.5 a knob to each effect. Knob ceiling 2 gave 24 an effect, about 4.8 a knob for reverb.
  - So C1b's labels, like C1a's, are a lower bound.
- **Fresh renders and ablations,** each in its own process with one priming render:
  - B's best: the dry baseline, and the effects-reset ablation.
  - Each effect that passes in process.
  - The final with stage A's controls (the left cab, the room mics and the phase) reset to the C1a label's. Resetting the phase with them costs no extra render.
  - The final with the mics and amp EQ reset to the C1a label's.
  - An ablation equal to the final or to B's best reuses its render.
- **Recorded:**
  - the trace; each stage's in-process best;
  - each effect's in-process best, renders, settings and fresh render; the effect kept;
  - stage A's and stage B's settings; mic changes; the start kind;
  - the searched keys for C3's masks: `searched_keys` is the union of C1a's and C1b's, and `c1b_searched_keys` holds C1b's alone;
  - `label`, the plugin settings of the final, with `fallback_reason` applied.
- **Rows.** Held half, ln ratio, per set, all and by class. Record-weighted jackknife t intervals, with the band-weighted reading (`pipeline_fix.clustered`) and its per-cluster breakdown beside.
  - **The primary:** C1b's final, rendered fresh, against C1a's fresh best.
  - **Per stage:** each ablation against the final.
  - **Counts:** the wet effects kept, per effect; mic changes; and what stage A changed: the left cab turned off, rooms turned on, the phase flipped.
  - **C1a's flags, carried:** output-level drift (the final's peak more than 10 dB below the start's), counted; non-finite ablations, named, not dropped.
  - **Records left out of the primary,** named with why: a fallback label, or a non-finite final or C1a best. The fallbacks are listed by unit.
  - real_out apart.
- **Still open in C0 after C1b,** with their blockers: the stereo controls (J0 is mono), the left cab's own phase (stereo), tempo sync (no beat tracker), combinations of effects (budget and multiple comparisons), the custom IR paths (the user's decision), and Tone King (a searchable renderer).
- **Cost.**
  - **Per record:** the dry process takes at most 65 renders. The effects take Σ(1 + budget): pr12 60, sw50r 57, ac20 52. Then B's best fresh 2, two ablations 2 each, and 2 for each effect that passes.
  - **In all: 9,070 renders if no effect passes, at most 9,608 if every one did.** That is 7% to 13% above the about 8,500 the user approved, after the review added tremolo level and tape drive (+426). No training.
  - **The miss path adds renders:**
    - A canonical miss costs its process's priming and first evaluation (2), and the raw start then reruns the dry process (up to 65).
    - A refused record costs 4 in all.
- **What it leads to.** C1a and C1b's recipe for C2, and the order of C1b's groups. There is no bar.

## C2 in detail (declared 2026-11-10, after C1b's report and before any C2 render; ledger `phase_c2`)

- **Status.** Declared after C1b ran (8,391 renders, no start misses, nothing refused), and amended after its independent review and C1b's audit (F70, PR #430). Under the user's rule of 2026-11-10 it launches once its review passes, and the user is told. C1a's blind page is out with the user. If that page reads C1a *below* the label (its declared rule), C2 stops at the next record and goes to the user.
- **What C2 is.** Labels, not a measurement: every searched control for every FT2 real training row, so C3 can train each head on a searched value or mask it.
- **Records, 520,** each a stored label with its DI, target, select, halves and lag as stored:
  - **GOAT, 214:** `goat_labels()`, one forced amp a unit, as stored. The 19 stored records without a label stay out, named: 16 refused by the one-window lag rule, 2 with no lag, 1 fallback (silent).
  - **BKS stage 1, 80, and stage 2, 186:** `real_labels(2)` (306 rows: all three forced amps of every unit, the lag rule applied) less C1a's 40. Three stage-2 units are not FT2 rows and stay out, named, 9 records: TooMuch `16_ElecGtr1aDI@205`, and Bulldozer `36_ElecGtr7aDI@200` and `@205` (`lag_refused`).
  - **C1a's 40 BKS records, last, continued to 200:** their stored evaluations are replayed at zero renders, each call's setting checked against the stored one. `coord_search`'s budget only truncates its sequence, so the continuation is the 200-evaluation run; the replay was checked exact on all 40 at the draw. After one start-check render, the evaluations past 100 are rendered; the 6 that ran to 300 already hold their 200 incumbent. Then stages A and B and the fresh final, as for every record. A record of this block that is refused (an inexact replay, or a start non-finite on either half) keeps its C1b record as C3's input.
  - real_out units are flagged as in C1a (17 GOAT, 4 BKS stage 1, 2 of C1a's). N12 stays out: it is measurement only. Each record's cluster is its DI: GOAT's item, BKS's DI.
- **The recipe, per record, in order:**
  1. **C1a's search,** as declared and amended (Amendment 1's start-miss path included): the start from the stored label with the gate on at −80 dB, the start check within 0.005, `c1a_space`, seed 20261123, at **budget 200.** That is the budget C1a's calibration set: the first checkpoint whose median reached 90% of the 300 gain. No ablations. **Step 1's result is saved before step 2,** so a stop loses at most step 2's 65 renders.
  2. **C1b's stages A and B,** as declared: the rest of the cab, then the mic types with the amp EQ (GOAT's short lists; C2 does not widen them), budgets 16 and 48, seeds 20261125 and 20261126. Their start check is against step 1's in-process best; on a miss the raw label, as C1b; if that misses too, step 1's best stands with step 1's mask. No ablations.
  3. **No effect stage.** The three time-effect switches, the spring's switch (`pr12Amp/springOn`, `sw50rAmp/springOn`, FT2's head names) and `doublerActive` are recorded **off by source** in `known_keys`. That is a fact about the sources, not a learned label. The effect knobs stay masked.
     - **The sources are dry.** GOAT's targets are capture renders, which carry no time effect, and every source is mono, so no doubler. BKS's being dry is **assumed** from its being real reamps; C1b's keeping no effect on BKS's 40 does not show it, since the keep rule is untested.
     - **On a dry source the search only adds false keeps.** On N12, also captures, C1b kept 3 effects on 31 records, where the truth is off: 2 of them scored worse on the held half (+0.076, +0.043) and one better (−0.028). The pooled effects-reset row is −0.003, undecided (F70).
     - **C3 must declare before it trains** either (a) the effect switches masked on real rows, learned from W's plugin rows only, or (b) unmasked, with a read on audio that has effects. The C0 rows say what is still open.
- **The near-silent guard (F70, PR #430).** In C1b, a BKS pr12 label at −59.6 dBFS (pr12 Volume 0, inherited from the stored label) left a −59.9 dBFS final that J0 refused on the held half. 5 of the 6 near-silent labels C1b's audit found share pr12 Volume 0.
  - **The start** is unusable only if its first evaluation is non-finite on either half. There is no peak margin for the start. Such a record is refused and the shard continues. At zero renders, none of the 520 stored starts is non-finite, so no refusal is expected.
  - **A later stage's best** (a replayed one included) is unusable if it is non-finite on either half, or if it peaks below min(−57 dBFS, the start's peak), less 0.05 dB. The 0.05 dB is a tolerance: fresh and in-process peaks of one setting differ by up to 0.0038 dB in C1a. −57 is 3 dB above J0's silence floor (−60 dBFS, `arm_a_mega53.SILENT_DBFS`). So a search may not go quieter than −57 dBFS, or than its start when the start is already quieter. C1b's failed record (start −59.6, final −59.9) falls back under this.
  - **Amendment (2026-11-10, after the code review): a constrained best.** Each stage's best is the best among its evaluations whose peak passes the bound, not the overall best, which would then be rejected. This applies to step 1 and to step 2's stages A and B; every non-replayed evaluation has its peak. For C1a's block, a replayed best passes on its halves alone. If it fails the peak check at step 2's first evaluation, step 1's best becomes the best passing evaluation among those with a known peak (101 to 200), else the start, and step 2 runs from it. Why: both of C1a's near-silent bests went quieter than their start, and an N12 search drove pr12 Volume to 0 within 100 evaluations, so under the overall best those records would spend their renders and end with no label.
  - **An unusable final (its fresh render) falls back to the previous stage's best,** with `fallback_reason`. The final is read on its fresh render, and step 1's best on step 2's first evaluation, which renders it in a fresh process. A replayed best, whose peak was not stored, is read on its halves at step 1 and on its peak at step 2's first evaluation and the final's fresh render, against the same bound.
  - **If step 1's best is unusable,** the label is `None`, step 2 is skipped, and C3 falls back to the source label.
  - **The 12 near-silent labels are searched.** 12 of the 520 stored labels peak below −57 dBFS, all pr12 with Volume 0. Their bound is their own start's peak.
  - **Labels between −57 and −49 dBFS stand:** J0 removes level, so they score normally. Below −50 dBFS a label is flagged `quiet` and counted, nothing more. 14 stored labels peak between −57 and −50.
  - The read names every record whose final has no finite score.
- **A systematic-miss guard.** A shard stops when 5 of its first 10 records are refused at the start. It reads the written records, so after a restart it does not fire again on records it has already passed.
- **Fresh renders:** each record's final once, in its own process with priming.
- **Recorded,** as C1a and C1b record: the trace, each step's best, the start kind, the continuation's replay, what changed, the peaks (the start's, step 1's best, its fresh render, the final's fresh render), `searched_keys` (C1a's space plus stages A and B only, not C1b's `searched_union`, which adds every effect knob: F55 again), `known_keys` (the spring under FT2's head name, `full_space.spring_dim`: `pr12Amp/springOn`, `sw50rAmp/springOn`, recorded for C3, which masks it and holds it at S), each stage's constrained and unconstrained best, `c1b_record` for C1a's block (C3's input on a fallback there), and `label` (the final's settings, with the guard's fallback applied).
- **The read (zero renders past the fresh final).** Held half, ln(the label's fresh render / the start's first evaluation), per block and class. Beside it: against the stored label, against S, and step 1's in-process held gain at the 100 and 200 checkpoints. Record-weighted jackknife intervals, with the band-weighted reading beside, clustered by DI (GOAT by item). Counts, over every record, label `None` included: start kinds, refusals, replay mismatches, continuation start-check misses (left out of the 200-checkpoint row), constrained bests, peak failures at step 2, fallbacks, quiet, drift, mic changes, left cab off, rooms on, pedals on, gate threshold moved; real_out apart. There is no bar: C2's output is C3's input.
- **Order.** GOAT first, then BKS stage 1, then BKS stage 2, then C1a's 40. Within a block, records go by key, round robin over 3 shards. A shard skips records already written, and resumes a saved step 1 at step 2.
- **Cost.** At most 268 renders a record (step 1 201, steps A and B 65, the fresh final 2): about 129k for the 480, GOAT about 57k. C1a's 40 add about 6.1k (34 × 169 + 6 × 67). In all at most about 135k. At C1a's and C1b's measured 5,400 to 6,300 renders an hour on 3 processes, GOAT takes 9 to 11 h and the whole 21 to 25 h. No training.
- **C2b, the follow-up for amp choice on GOAT,** is declared in detail below. GOAT has one forced amp a unit, so its rows get no amp-choice label from C2.
- **What it leads to.** C3, declared before it trains.

## C3 in detail (declared 2026-11-10, while C2 runs and before any C3 training; ledger `phase_c3`)

- **Status.** Declared while C2 renders, and amended after its independent review: the seven changes it required and four of its optional ones are folded in below. It trains when C2's last record is written, since C2's labels are its input. Under the user's rule of 2026-11-10 it then launches without a wait once its code review has passed, and the user is told.
- **Built** (2026-11-10, before any training): `learn/full_controls_c3.py` (`c3-check`, `c3-gate`, `c3-recheck`, `c3-n12`, `c3-amp`, `c3-adopt`), `pipeline_fix train-ft --c3`, the per-control hold as `hold_outside_space`'s `hold` argument, and C3's tags in `real-predict`, `goat-predict`, the reports and N12's `score_ear h4-*`. Launchers `logs/launch-c3-train.zsh` (it waits for C2's end, its last line "done" or all 520 outputs and its report, so a resumed C2 needs `c2-report` by hand; it writes the gate spread and the check, then trains) and `logs/launch-c3-read.zsh` (it waits for the training). Each rotates its own old log on a relaunch, so the read never acts on a stale FAILED line. The adoption record also carries C3 − FTm, C3 − S and C3 core − FTm pooled, and whether C3 core is shown worse than FTm, which calls for the isolation run. Tests `tests/test_full_controls_c3.py`.
  - **Zero-render checks on what exists** (C2 at 15 of 520): the training refuses ("C2 is not complete"). On 98 stored FTm answers, C3 core's hold equals `hold_outside_space`, and no tag leaves an untrained key off S. The masks hold 40 to 50 keys a record (K.space 12 to 17 plus C2's), and C2's union is 46 to 51 keys an amp: EQ 11, pedals 14, gate 2 and cab rest 7, plus `K.space`.
  - **The gate's labels so far** (`c3-gate`): the search turns the gate off often, so its switch label is no finding. C1a's BKS labels have it on in 27 of 40, with the threshold moved from −80 dB on 24 of the 27, spread from −96 to −32 dB (median −56). On N12 it is on in 17 of 31, moved on 11. On C2's first 15 GOAT labels it is on in 4. The launcher writes the full spread before training.
- **Its own runs.** Every C3 run has its own base name (`C3-…`), never FTm's, since `cmd_train_ft` skips a name that exists. Each run records the sha256 of C2's records and outputs, and refuses until all 520 are written.
- **What C3 is.** FTm's recipe, retrained on C2's full labels with per-record masks, then read by the score as H4a read FTm. One tag per family, with that family at S, lets each family be adopted on its own.
- **Rows.** FTm's own rows: GOAT's 214 (`goat_labels`) and BKS's 306 (`real_labels(2)`).
  - **Each takes C2's `label`.**
  - **A record with no C2 label** (C2 fell back or refused it) takes its source:
    - the stored label for GOAT and BKS;
    - C1b's record for C1a's block, masked by C1a's space ∪ C1b's stage A and B keys, never by C1b's `searched_keys`: those list every effect knob (F70).
    - C1b's failed record (`22_ElecGtr2aDI@290 #24`, F70) takes its stored label.
  - **Nothing else changes:** no new rows, no N12 rows, and real_out as in FTm (every row; C5 holds the exclusions).
- **Masks, per record.**
  - **A record on a C2 label:** `K.space`'s keys ∪ C2's `searched_keys`.
    - Every C2 start is a label whose search covered `K.space`, so `K.space` is labelled on every record. That includes the mics: held at the source's searched value, or moved in C2's stage B.
    - This also covers C2's fallback records, whose `searched_keys` hold no mic types.
  - **A record on its stored source label:** `K.space` only, as in FTm.
  - **Masked everywhere:** `EQActive` (forced on), and `encode`'s sounding mask on top: EQ bands with the EQ off, pedal knobs with the pedal off, and room level with the room off.
  - **The amp head** stays at −100 on real rows, as in FTm.
- **The time effects, the spring and the doubler are masked on real rows and held at S in every C3 answer.**
  - **The binding blocker is the reader, not the rows.** W trained on exact plugin labels for every effect, and still reads new songs at about the marginal: its switches score 0.612 against 0.617 on NS. F48 to F52 found no reader that hears effects through a backing.
  - So adding plugin rows to FT would not help. Real wet rows would pay only once a reader passes on rows whose truth is known.
  - Training these heads on dry real rows would teach "off", S's value. Masked, they keep W's weights, which would switch an effect on about half the time if read. So they are held at S.
  - No read set has an effect on, so no read could show a gain either way.
  - **This family stays open in C0, with its order.** First, at zero renders, each effect switch's loss on NS against its marginal. Then a reader that passes on rows whose truth is known. Only then real wet rows: Morgan's effects, amp and cab sections off, rendered onto dry real targets, after checking the chain order.
- **The gate.** Every C2 start turns the gate on at −80 dB, and the switch is inert there (F69), so its label is the start's convention, not a finding.
  - The switch is masked on real rows and held on in the answer.
  - The threshold is trained wherever the gate is on.
  - Before training, the threshold labels' spread is reported at zero renders. C1a moved the threshold on 22 of 38 BKS records with no held-half gain.
- **The recipe is FTm's, unchanged** except in three places: the label source, the masks and the answer's hold.
  - **W:** P2b-wide24's NS-best state per seed.
  - **Training:** `train-ft --masked --ft-cap 300`, with FTm's 8 inner fold-and-seed runs, 8 FT_k fold runs and the all-labels pair. Seeds 20261042 and 20261043. As in FTm, each FT_k takes its own (fold, seed) inner run's E, and only the all-labels pair takes the median of the eight.
  - **Per-head held losses** are logged every epoch (`head_losses`, at zero cost). C3's objective differs from FTm's: the knob NLL averages over about 2.5× more dims, the mixture is shaped mostly by the EQ's 11 dims, and the switch loss is pooled wider.
  - **The answer's hold works per control, not per family.** `answer_settings` writes every head that can sound on the amp, and `at_S` resets whole `FAMILIES`. But three families hold heads that are masked on every real row: the left cab's phase, both pans and both stereo switches in "cab rest"; the doubler in "gate and doubler"; and `EQActive` in "EQ". Read through FT's moved trunk, those W heads would write untrained values.
    - **So C3's answer writes from the heads only `K.space` ∪ the union of C2's `searched_keys` for that amp.** It holds `EQActive` on and the gate on, and everything else at S. Each tag then sets a subset of the trained keys to S.
    - **At the six call sites,** `hold_outside_space` takes this hold as an argument. The default stays `K.space`, so every stored read reproduces.
    - **Tests:** the all-new-at-S tag must equal `hold_outside_space`'s output, and no untrained key may differ from S.
- **The read: by the score, as H4a.** BKS (40 units × 3 amps, by DI fold), GOAT (its units on their own amp, by item fold) and N12 (pooled; measurement only). Each answer comes from the search half and is judged on the held half. Its tags:
  - **C3:** every trained key as answered.
  - **C3 core:** every trained key outside `K.space` at S. This is a product comparison against FTm, not an isolation. It mixes three things: C2's shift in the core labels, core knobs tuned for partners the tag sets to S, and the changed objective. FTm's mask on C2's labels, the true isolation, is trained only if C3 core reads worse than FTm.
  - **One tag per family at S,** over the trained keys: the amp EQ, the pedals, the gate's threshold, and cab rest (the left cab, the rooms and the right cab's phase). That is 4 tags.
  - **The adopted configuration,** as its own tag when it is none of the six (at most about 1,400 renders more).
  - **FTm:** H4a's stored scores as the comparator. A few FTm answers on BKS and GOAT are re-rendered as hash checks, as H4a did on N12; FTm is re-rendered in full only if they don't match.
  - **Cost:** 6 tags × about 1,400 renders ≈ 8,400 renders, about 2 h on 3 processes at H4a's measured rate.
- **Rows read, per set and pooled.**
  - C3 − FTm, and C3 − S.
  - C3 core − FTm.
  - N12 against its C1b labels, at zero renders.
  - For each family: C3 − (C3 with that family at S).
  - Intervals: band-weighted means and record-weighted jackknife intervals, as in H4a.
- **Adoption, per family: kept unless shown worse,** as the user's rule asks. A small gain sets priority, never inclusion.
  - **Shown worse** means: C3 − (C3 with that family at S) has its 90% interval wholly above 0 on BKS, on GOAT, or pooled.
  - **Pooled** means the two sets weighted equally: the mean of the two set means, with its interval from the two sets' jackknife variances. GOAT has 126 items and BKS 8 DIs, and F55's mask split the two (GOAT −0.023, BKS +0.039), so each set is also reported apart.
  - An undecided family is kept. The families expected to be inert, the gate and the rooms, will probably read undecided.
  - C4's ear page can reverse it, through PR #422's conflict rule.
  - A family not adopted is written at S in the product, and stays open in C0 with its next route and blocker.
  - **The rooms stay open in C0 whatever "cab rest" reads.** Their labels were barely searched (F70), so they learn S's "off".
- **When C3 replaces FTm.** The adopted configuration replaces FTm unless it is shown worse than FTm, by the same test as a family. C4 can reverse that, through PR #422's conflict rule. C5 runs only if it replaces FTm.
  - **No bar on size:** an adopted family's effect size is reported. A small gain sets its priority for the next labels, never whether it is learned.
- **Amp choice** is not trained in C3: GOAT has no amp label until C2b runs.
  - On BKS, C3's per-amp renders give a zero-render read of the amp pick against a blind choice. This is W's amp head on C3's body, since `loss_fn`'s `keep` masks the head on real rows, and it is labelled that way.
  - Training the amp head on real rows comes after C2b, as C3b, at about the same training cost.
- **Stop rule.** C3 is one retrain and one read, with no tuning loop on the read sets: they choose adoption only. After it, every C0 row is adopted, written at S with its blocker, or open with its next route. Then C4 hears the adopted families.
- **Cost.** Training is about 1.2 to 2.3 h of MPS: H4's real-only arm ran this recipe in 73.5 min, and FTm measured 135.7 min, unless E grows. The read is about 8,400 renders, plus up to 1,400 for the adopted tag. No new data.
## C2b in detail (declared 2026-11-10, before any C2b render; ledger `phase_c2b`)

- **Status.** Declared while C2 renders, and amended after its independent review, which confirmed the like-for-like recipe and that the earlier callers run unchanged. It renders after C3's read, the last job queued on the render slots.
  - **The launcher** waits for C3's read launcher to exit, by its PID. Its outcome doesn't matter (done, failed or otherwise): once it has exited the render slots are free, and `_wait_cap` guards the cap. `c2b.log` records which way it ended.
  - Under the user's rule of 2026-11-10 it launches without a wait once its review has passed, and the user is told.
- **Why.** Amp choice is a control: the model picks which of the three amps to load. FT2's amp head is masked on real rows. BKS gives an amp label for every unit, since all three forced amps of each BKS unit are searched. GOAT's 214 units each have one forced amp, so the amp head would learn its real-row choice from BKS's 8 DIs and 2 songs alone.
- **Records, 428:** each of GOAT's 214 labelled units (`goat_labels`) on its two other amps (`P.AMPS3` less its forced amp), sorted by key (`unit|amp`).
- **The recipe is the stored labels' own,** so the three amps are like for like.
  - **The code:** `pipeline_fix.search_units`, the function that wrote `goat/search/`. Arm A's main stage (`K.space`, 52 evaluations, seed 20261013) runs from the class's S, with one discarded priming render, the unit's DI, its stored halves and its stored lag, in a fresh process per record.
  - **Output:** `goat/search-c2b/`.
  - **What it reuses:** GOAT's stored lags and S renders, rendered on all three amps in 5C's lag pass (phase_5c). So C2b renders no lag.
  - **`search_units` gains six options, each off by default,** so GOAT's and L1a's callers run exactly as before: an output folder, the lag files' phase, a start tolerance, a systematic-miss guard, a per-amp guard, and refusing a unit with no stored lag rather than rendering one into GOAT's stored lags.
- **The start check.**
  - The first evaluation is S on the new amp. It must be bit-identical to that amp's stored S render, as the stored labels' check was.
  - Otherwise, it is accepted and flagged if its search-half judge is within 0.005 (|log ratio|) of the stored one, as C1a's and C2's start tolerance.
  - Otherwise the record is written refused, with both values, and the shard goes on. Before C2b a mismatch stopped the shard.
- **Guards.**
  - **Disk:** `search_units`' own, 31 GB.
  - **Systematic miss.** In 5C, fresh-primed against fresh-primed was bit-identical on 214 of 214, so a start that is not bit-identical means the plugin or the environment changed. Such a start counts as a miss whether it is refused or accepted and flagged, and so does a unit with no stored lag file.
    - A shard stops when 5 of the first 10 records it reaches miss.
    - It also stops when 3 of one amp's first 5 miss (`pipeline_fix.systematic_miss`).
    - **Before a resume** after such a stop, the refused records are moved aside, never deleted, so they are searched again.
  - **Near silence:**
    - The search's own fallback writes no label when the best's peak is below −60 dBFS or its search half is non-finite (`fallback_reason`, as for the stored labels).
    - The amp choice then counts only labels whose best peaks at or above −57 dBFS, like for like on all three amps. This is not C2's min(−57, start) − 0.05 rule: every search here starts from S. It applies to the stored records and C2b's alike.
    - One stored GOAT label, `goat/item_1@25.0#amp_4` at −57.3 dBFS, therefore drops out of its unit's choice. It is listed in the report's `quiet` list with C2b's own.
    - **A sensitivity check at −54 dBFS** runs at zero renders. The report counts the units whose choice it changes.
- **Zero-render checks, done at declaration:**
  - All 214 stored searches replay exactly with `arm_a_levers.Replay` on their stored curves: the same 52 evaluations, the same best value and the same best setting. So the main stage is deterministic, and C2b's run on another amp is the stored recipe.
  - Every unit's stored lag file is phase_5c, holds a lag and holds S's judge and render sha on all three amps.
  - The stored halves equal `goat_halves`, and every unit's forced amp and class fit the draw.
- **The amp label.** For each unit, the argmin of best.judge[search] over its usable labels among the three, ties going to the first in sorted order, as `full_controls.bks_amp_choice` does on BKS.
  - It is written to `c2b/report.json`'s `labels`, with every amp's value and `n_usable`.
  - **Labels only from complete sets:** while any of the 428 records is missing, the report writes no labels.
  - **A unit with a refused record gets no label.** A refusal is a technical gap, not evidence about the amp.
  - A unit with no usable label gets none either.
- **The read, at zero renders.** Every-control stage 0b's reading, as F69's −0.058 on BKS: the chosen amp's held half, ln, less the mean log held half over the usable amps.
  - Clustered by item (`pipeline_fix.clustered`), all and by class.
  - Beside it: the same reading for the forced amp, for scale.
  - Counts: units with a choice, withheld, with three usable amps, where the choice is the forced amp, and where it is the held half's best. Also counted: units dropped from the read for a non-finite held half on the chosen amp, or with only one usable amp.
  - The choices are also reported by amp, overall and by forced amp.
  - Also listed: refusals, fallbacks, quiet labels, and starts accepted with a differing sha.
  - There is no bar: C2b makes labels.
- **The order.** Records go by key, round robin over 3 shards, at most 3 render processes. A shard skips records already written, so a stopped run resumes.
- **Cost.** One priming render and 52 evaluations a record: at most 428 × 53 = 22,684 renders. That is about 3.6 to 4.2 h at C1a's and C2's measured 5,400 to 6,300 an hour on 3 processes. A refused record costs 2. No training.
- **What it leads to: C3b,** declared separately before it trains. It is the amp head trained on real rows: BKS's argmin over C2's three labels, and GOAT's from C2b.
  - **A zero-render check for C3b, declared now.** Once C2 is done, compare on BKS the argmin over the stored 52-evaluation labels with the argmin over C2's labels. This shows how much the amp label moves with the label's recipe, since GOAT's C2b labels are 52-evaluation `K.space` labels like the stored ones.

## C5: the heavy clean-up re-tested on the full-control model
- **What F68 said, and what has changed.** F68 closed the clean-up with "This clean-up is not reopened." Its verdict on the `K.space` model stands.
  - The user asked, 2026-11-09, whether it should be re-run after these steps.
  - C5 is a new test on a changed premise: a model with a different head layout, learning every control.
- **Why it could differ.** W's plugin rows carry exact drawn labels, so heavy plugin rows can't teach wrong values. Their risk is distribution and scope, as in H4. Label noise comes from J0's searches on heavy real recordings, now for every control. That is H4's real-only arm, so C5 keeps all three arms.
- **What it is.**
  - C3's recipe, trained with H4's pinned exclusions (sha256 cc7b9ab9…cb36f2): full, gentle and real only. No new line and no new listening.
  - It is compared against C3's adopted model.
  - **First, at zero renders:** for each new family, count what each cut removes, both W rows with that family on and real labels with it on. An arm whose cut removes little of the new families goes back to the user before training.
- **The read.** The score as in H4a, then one blind page. Ranks allow ties, and the decision pairs repeat, so a page that can't decide the pair shows it.
- **The rules.**
  - **Adoption** goes through PR #422's conflict rule.
  - **No arm better by ear:** the clean-up closes again. If the page is undecided, closing it is a decision on cost, and the write-up says so.
- **The conditions.** C5 runs only if C3 is adopted. Its comparator is C3's adopted model. It reads on N12's unheard pool only while N12 stays out of training.
- **Cost:** about 4.3 h of MPS for three arms, as in H4, plus its reads.

## Caveats
- **The search half flatters the search.** The held half is the read.
- **Search order.** The core knobs re-tune with the pedals, so a pedal's gain can come back as amp-knob gain. The ablations bound that.
- **A short search.** At 100 evaluations over 37 to 42 dims, the search makes about 1.5 sweeps. So the primary is a lower bound on what these controls are worth, and the subset's 300-evaluation rows bound how loose it is.
- **The scores are J0's.** F44: J0 weighs treble and drive above the ear. C4 is the ear check.
- **N12's labels are v2's,** a different search from BKS's main stage. C1a continues from each record's stored label either way.
