# Every control on the real rows: labels, training and measurement for the whole plugin (C0 to C5)

**Amendment 2 of the [every-control plan](every-control-plan.md).**

## Status

- **Declared** 2026-11-09, before any render, on the user's word: "go, but make sure that everything will eventually be measured and trained on. We must learn and be able to predict every single control." That repeats their coverage rule of 2026-10-21 and 2026-10-22, "every control is learned".
- **Amended the same day after its independent review.** The review found missing controls, a wrong start, a wrong ablation and too low a budget, and asked for a stop rule that converges. All of it is folded in below.
- **The user's go for C1a:** "Go", at about 10,000 renders, with the gate included.
- **The user's word on ranking pages:** several presets may share a rank, instead of a "can't tell" answer.
- **Every later step** with renders beyond C1a's, or with training, goes to the user with its cost before it runs.
- **C1a ran** on 2026-11-09 (10,237 renders, audited; [F69](pipeline-fix-plan.md)): by the score −0.205 on N12 and −0.030 on BKS (undecided; crunch −0.052), against the label. The user said yes to C1b (2026-11-09, at about 8,500 renders; the built C1b counts 8,644–9,182) and to a blind A/B page of C1a against the label; both are declared before they render.
- **Bookkeeping.** Ledger `pipeline-fix`, `phase_c1a`, `phase_c1a_a1` (Amendment 1), `phase_c1a_outcome` and `phase_c1a_ear` (C1a by ear). Code: `learn/full_controls.py` and `learn/c1a_ear.py`, tests `tests/test_full_controls.py` and `tests/test_c1a_ear.py`. Results go in [pipeline-fix-plan.md](pipeline-fix-plan.md), F69 on.

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
| Amp choice, `selectedAmp` (1) | no: forced per record | no: the amp head is masked on real rows | stage 0b, −0.044 | C1a gives the first real amp label (BKS's per-unit argmin); C2 extends it to every training unit | none |
| Amp EQ: on, 9 bands, high- and low-pass, ×3 amps (36) | C1a | C3 | knob ceiling (d) | C1a, C2 | none |
| Pedals: compressor 5, drive 1 4, drive 2 5 (14) | C1a | C3 | knob ceiling 2 | C1a, C2 | none |
| Gate: on, threshold (2) | C1a | C3 | never | C1a, C2 | none |
| Time effects: reverb, delay, tremolo, with tremolo level and tape drive (17) | C1b | C3 | knob ceiling 2 | C1b, each effect on its own, with a keep margin declared first | time carry-over; fresh-process renders |
| The amp's spring: pr12 Reverb and Dwell, sw50r Reverb (3) | C1b | C3 | knob ceiling 2 | C1b | as above |
| Room mics: on, level, per side (4) | C1b | C3 | never | C1b | none |
| Left cab on and level (2) | C1b | C3 | never | C1b | none |
| Stereo: doubler on and spread; cab phase, pan and stereo per side; delay width and ping-pong (10) | no | no | screen only | needs a stereo term from the song's stereo image | J0 is mono; no stereo target yet |
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
  - It re-checks the mics and re-searches the amp EQ jointly with them, since N12's v2 mics came from a 4-mic short list and the EQ can compensate for a wrong mic.
- **C2** (the user's go): C1a and C1b's recipe on every training record. That is GOAT's, BKS's stage-2 records, and BKS's other 80 stage-1 records, because FT2 trains all three forced-amp records per unit.
  - **Cost, stated now:** about 490 records × 105 ≈ 51k renders at a budget of 100. Up to about 150k at 300. C1a's calibration sets the budget.
  - **C1a's BKS records are continued, not searched again.** If C2's budget exceeds 100, each one is replayed from its stored trials (the search is deterministic) at zero renders, and only the evaluations past 100 are rendered.
- **C3** (the user's go, training): FT2 retrained on the full labels.
  - **Masks.** Each record trains only the heads its own search covered: `searched_heads` generalised to a per-record space. That is C1a's space plus the mics for C1a and C2 records, and `K.space` for the rest. `EQActive` is masked: it is forced on. Unmasking unsearched heads would repeat F55.
  - **A C1a label that fell back** (stored as `None`) falls back to its source label, with the source's `K.space` mask.
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
