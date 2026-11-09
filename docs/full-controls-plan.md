# Every control on the real rows: labels, training and measurement for the whole plugin (C0 to C5)

**Amendment 2 of the [every-control plan](every-control-plan.md).**

## Status

- **Declared** 2026-11-09, before any render, on the user's word: "go, but make sure that everything will eventually be measured and trained on. We must learn and be able to predict every single control." That repeats their coverage rule of 2026-10-21 and 2026-10-22, "every control is learned".
- **Amended the same day after its independent review.** The review found missing controls, a wrong start, a wrong ablation and too low a budget, and asked for a stop rule that converges. All of it is folded in below.
- **The user's go for C1a:** "Go", at about 10,000 renders, with the gate included.
- **The user's word on ranking pages:** several presets may share a rank, instead of a "can't tell" answer.
- **Every later step** with renders beyond C1a's, or with training, goes to the user with its cost before it runs.
- **Bookkeeping.** Ledger `pipeline-fix`, `phase_c1a` and `phase_c1a_a1` (Amendment 1). Code: `learn/full_controls.py`, tests `tests/test_full_controls.py`. Results go in [pipeline-fix-plan.md](pipeline-fix-plan.md), F69 on.

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
  - **The declared change:** the start has the gate on at the factory threshold, as `every_control.group_plan("gate")` does. A label with the gate off gets it on at −80 dB, as 102 of the 107 factory presets have it. A label with the gate on keeps its threshold.
  - So the search tries the threshold of a gate that is on, and the switch beside it, not a flip to a near-inert gate.
  - **The check:** the first evaluation's search-half value must equal `best.judge[search]` within 0.005 in log. That also verifies that the gate on at −80 dB is inert on the record. Its render sha is recorded beside `best.render_sha256`. A miss stops the shard.
- **Space:** `knob_ceiling2.stage1_space`'s controls, about 37 to 42 an amp. The core knobs have input gain at FT2's head range, −20 to +12 dB, not −24. Then the amp EQ, drive 1, drive 2 and the compressor, plus the gate: `gateActive` as a switch and `gateThreshold` from −96 to 0 dB.
  - The mic types are held at the label's.
  - **The factory threshold** is the median threshold of the factory menu's presets with the gate on, read from the preset files at zero renders (`full_controls.factory_gate_median`). It would be −60 dB if none had the gate on.
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
    - four ablations of the 100-budget best: pedals reset to the start's, amp EQ reset to the label's, both reset, and the gate reset to the start's (on, at its start threshold).
  - All of them are judged on both halves.
  - **Reuse:** an ablation whose canonical setting equals the best's reuses the best's fresh render, and the 300 best does too when it equals the 100 best. Each is marked `same_as_best`.
  - **Also stored:** the start's settings (`start_settings`), and `measurement_only: true` on N12's records.
- **The label is stored in today's record schema** (`unit`, `amp`, `select`, `search`, `held`, `lag`, `s_judge`, `curve`, `best`, `label`). It goes in parallel directories, `captures2/search-c1a/` and `real/search-c1a/`, with each record's searched-key list for C3's per-record masks.
- **Rows** (held half, ln ratio, per set, all and by class; clustered by DI for BKS and by band for N12; 90% cluster-jackknife t intervals, df = clusters − 1, record-weighted; beside each, the band-weighted reading from `pipeline_fix.clustered` with its per-cluster breakdown):
  - **The primary:** C1a's fresh 100-budget best against the stored label.
  - **Beside:**
    - Each ablation against the best.
    - Each pedal's state changed from the label's, counted, and, for each pedal on in the best, its knobs moved from the label's.
    - The amp EQ moved from S's curve, counted.
    - The gate's state changed, counted.
    - The label against S, for scale.
    - The subset's checkpoint curves, from the stored checkpoint judges: on the search half (which sets C2's budget) and on the held half beside it.
    - The subset's held-half rows per set: ln(fresh 300 best / fresh 100 best) and ln(fresh 300 best / label).
    - BKS's amp choice, chosen on the search half and read on the held half: the chosen amp's log held judge less the mean over the three amps, as stage 0b read it.
    - real_out apart.
- **What it leads to:** the labels and the budget for C2, and the size that orders C1b and C2. There is no bar.
- **Cost, an upper bound:** 71 records × (1 priming + 100 + 5 fresh renders × 2) ≈ 7,900 renders. The subset adds 12 × (200 + 2) ≈ 2,400. That is about 10,300 in all, about 2.5 h at H4a's measured rate. The reuse above can only lower it. No training.

### C1a, Amendment 1 (2026-11-09): a start miss is tried with the gate as in the label, else refused

- **When it was declared.** After shard 2 stopped on one record's start check, and before any C1a result is read.
  - The record: `cap/1xiluf3lhnm#ac20`. The gate-on start scored 2.9622 against the stored label's 2.9774, an ln gap of 0.0051.
  - So the gate at −80 dB is not inert there: it scores about 0.5% better.
  - Shards 0 and 1 kept running, and their records are kept as written.
- **The rule, on a start miss:**
  1. One more start is rendered, in its own process with one priming render, as the start is: the same start with the gate as in the label (off, its threshold canonical at −80).
  2. **If it matches the stored label within 0.005,** the gate alone caused the miss. The record runs from this gate-off start. The gate stays searchable: its flip tests a gate on at −80, which acts on such a record, so the threshold then moves. The record is flagged `start_gate: "off_after_miss"`, with both start values in `first_start_miss`.
  3. **Otherwise** the record is written refused (`start_gate: "refused"`), with both values, and the shard continues. A shard never stops on a start miss.
- **Resume.** Records already written, refused ones included, are skipped.
- **Counts.** The shard's last line and the report count each kind: on, off after a miss, refused. Records written before the amendment carry no flag and count as on.
- **Cost.** A gate-only miss adds 4 renders (the missed start's process and the second start). A refused record costs 4 and nothing more.

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
