# Fixing the pipeline review's findings (plan, 2026-10-31)

**Status: declared 2026-10-31; independently reviewed and re-reviewed the same day (required changes all made,
below). Phase 1 has run (P5, P6, the dirty-double scan; zero renders, audited): see the review's steps 5, 12 and 36
and the ledger's `phase_1_outcome`.**

**Why.** The user (2026-10-31): "Start with the review, reevaluate our entire plan/roadmap and make sure we go
over each finding the review found, fully understand it, fix it and verify its fixed. Be organized, go step by
step and make sure no issues are opened in the end. We must fix what's blocked us from making the ML efforts
work." That asks for the [pipeline review](ml-pipeline-review.md)'s tests P1–P7 to run and each finding to be
fixed. Each phase is still entered in the ledger (`pipeline-fix`) before it runs, and each result is audited
before it is written up.

## The roadmap, re-evaluated

- **What the record shows.** Across every direct-model build (part C, the stems pilot, D_F5, D_CC), gains in
  distribution never carried over to real songs, and no build beat S on V-real. The review then found that D_F5
  reads almost nothing even on its own made-up songs (step 29). The next build (F20, more data) would scale a
  pipeline that is not yet shown to learn.
- **The order changes:**
  1. Make the yardstick fair: S's home advantage (P5), Wickerman's duplicate input (step 32), render-order noise
     (step 33).
  2. Fix the training data that is wrong: the DT doubles (step 12) and the runaway targets (step 6).
  3. Find the failing step: P1 (can the network learn at all?), then P2's ladder of inputs (clean target, target in
     its backing, the full mix, the stem), read by knob and by sound, on new settings and on new songs.
  4. Fix what the ladder locates and train one model with every adopted fix (D_fix), chosen on the training pool's
     own reads, never on V-real.
  5. Read D_fix on V-real. Scale (F20) only if the learning curves say size is the lever.
- **F20's draft (PR #345) is folded in here** and closed as superseded when this plan merges:
  - its step 0 (a size curve) becomes P2's learning curves, on the clean input and on the stem;
  - its decisions A (the order) and B (F20 on the evidence) become this plan's order and phase 5;
  - its near-chance switch rule (decision C) is read beside P3, as a measurement;
  - its audibility weights (decision D) are a phase 5 candidate.
- **Unchanged:** the product (`generate`, `match`, `edit`), arm A, the scope (clean, edge-of-breakup and crunch),
  the trusted-data rules and V-real-11's freeze.

## When a finding counts as closed

Each step that is not OK gets a dated line in the review, under the step and in its table row, saying which of
these holds:
- **Fixed:** the code change is merged with a test, and a run in this plan that uses it is named.
- **Ruled out:** a declared test shows the step does not limit the model (an effect size with its interval).
- **Limit, measured:** a limit this plan cannot remove (for example V-real's 7 bands), with its size stated, the
  mitigation in use and the plan that would remove it.
- **User decision:** the evidence is in and the choice is the user's (the readout's fallback, below).

The plan ends when every step reads OK, Fixed, Ruled out, Limit, measured or User decision. Which steps can end
as a limit or a decision is said in the table.

## Verifying each fix in isolation (the user, 2026-10-31)

The user (2026-10-31), on the pipeline review: "make sure to fix and test each part separately ... fixing the
dataset and evaluating the fix using the faulty training would still yield incorrect and untrustworthy results ...
evaluate each fix without relying on other parts if possible."

**The rule.** Each review finding's fix is checked by a test that relies only on parts already verified on their
own. A model that reads little (the mix and stem models, D_CC) never serves as the instrument for another fix.

**The verified base so far** (each verified without relying on the others):
- the by-sound read: each example's own label reproduces its stored target (F10);
- the training recipe: it can fit (P1, F5), and fed the clean guitar it learns the tone well enough to sound about
  22% closer than S on new songs (P2a, F11);
- the dataset's audio parts: the target, other-guitar and mix renders reproduce exactly (the positive control in F3,
  the input parity in F4).

**Each step's isolated check.**

| Step | Fix | Isolated check | Relies on | Status |
|---|---|---|---|---|
| 3, 23 | Stop on held-out songs; checkpoints | Data check: NS shares no session, DI or time window with training (`s23` on the recipe's split) | nothing | fixed (F18) |
| 4 | Size | Learning curve on the clean input (P2a at 25% and 50%, and at 50% of sections), by NS loss and by sound | recipe, by-sound read | limit, measured (F25) |
| 5 | Class from the section | Structural: one field in every consumer (a test); the mismatch measured in D_CC itself, where it exists (P6) | nothing | fixed, measured (F2) |
| 6 | Runaway targets out | Data check: the scan's rules hit 0–1 of the 2,645 examples that cannot self-oscillate (`cc_drive_page.RUNAWAY`) | nothing | fixed |
| 6 | The wide, wet prior | Measured on P2a: by sound per draw mode (F11) | recipe, by-sound read | limit, measured |
| 7 | Refusal skew | Data measurement (`s07`) | nothing | limit, measured |
| 8 | Inaudible labels | P2a's per-head table: which heads read from the clean guitar | recipe | limit, measured (F18) |
| 11 | Stereo-only labels | The same table, the stereo-only heads | recipe | limit, measured (F18) |
| 12 | Doubles with the full setting | Data checks: the positive control (46 of 46 exact); every re-rendered double carries its target's exact label and amp (980 of 980); every other guitar unchanged (1,222 of 1,222); the new mixes rebuilt exactly (F16) | nothing | fixed |
| 13 | Stand-ins | Not an error; their share is a data measurement | nothing | ruled out (as an error) |
| 14 | Ratio prior | Data measurement; level statistics only | nothing | limit, measured |
| 15 | Mastering | P2a reads its own NS inputs mastered with each example's draw against unmastered, by sound (zero training) | P2a, by-sound read | ruled out (F22) |
| 16, 19 | Where the tone is lost | The ladder: every rung on the verified recipe; located at the mix (F15) | recipe, by-sound read | located |
| 16 | The fix for the mix | Phase 5's fix, trained on the verified recipe and read against P2b and P2c on the same examples | recipe, by-sound read | phase 5 |
| 18 | Augmentation | P2a with dropouts and darkening against P2a, by sound. Merge and separator failure are mix-specific and are tested only once a mix model reads | recipe, by-sound read | ruled out as a lever (F21) |
| 20 | Network | P1 | nothing | ruled out (F5) |
| 21 | Loss in knob units | P2a by sound against by knob | P2a, by-sound read | confirmed (F11) |
| 22 | Length | P1, P2a's checkpoints | nothing | fixed |
| 24 | Logs | A test; P1 | nothing | fixed |
| 26 | Pull toward the average | On P2a in distribution, by sound (F12) | P2a, by-sound read | measured (F12) |
| 27 | Near-chance switches | On P2a in distribution, by sound: unreadable switches at S, and the near-chance rule, against the plain readout | P2a, by-sound read | measured: plain readout right; near-chance rule hurts (F23) |
| 29, 30 | Reads almost nothing | The ladder, by knob and by sound | recipe, by-sound read | located (F13–F15) |
| 31, 35 | V-real's size | Limit; the rows' Wickerman rule unit-tested | nothing | limit, measured |
| 32 | Wickerman's shared input | Unit test of the rows; P4 reads their own amp tracks | nothing | fixed (test) |
| 33 | Render-order noise | Fresh primed processes reproduce the truth (F10); in phase 4 every fresh S render must sit within 0.005 (log) of the label table's stored distance on stage F's parts, or the read stops | nothing | fixed |
| 36 | S's home advantage | Stored distances (P5) | nothing | measured (F1) |
| 37 | The average against S | In distribution, the constant against S by sound (F11: even) | by-sound read | measured |
| (P4) | Transfer to real recordings | First, alone: P2a told a wrong amp and rendered on it, by sound on NS (the amp mismatch, without real recordings): it keeps most of its skill (F19). Then P4 on V-real's amp tracks: no transfer, +0.153 against S, about its own constant (F20) | P2a, by-sound read | measured: a second blocker (F20) |

**What this changes in the plan.**
- Step 12 closes on its data checks (F16), not on D_fix.
- Steps 15, 18 and 27 are tested on P2a in distribution, not on the mix and stem models.
- P3 on D_CC is dropped: a readout test on a model that reads little shows nothing. V-real's readout rows ride on P4's
  model instead.
- The learning curves run on the clean input, where the training is verified.

## The common recipe for every retrain in this plan

So that the ladder's rungs differ only in their input:
- **Split (step 23).** Two whole songs are held out ("NS", new songs): Adam Buckley "Drag Me Down" (clean) and The
  Maybe Next Years "One Flip Flop" (crunch). They were chosen as one clean and one crunch song of middling size,
  outside the two largest songs. NS holds 383 examples from 36 sections and 5 DIs in 2 bands. It is less dense than
  V-real: 144 of its 383 examples have one other guitar, and it has no DT doubles.
  - Training is D_CC's training examples of the other 8 songs: 2,327 examples, 232 sections, 27 DIs, 7 bands.
  - FS is FS_CC's examples of those songs: 259 examples in 6 bands, new settings on seen performances.
- **Dirty examples (steps 6, 12).**
  - The 64 runaway targets (`cc_drive_page.RUNAWAY`, the 2026-10-30 scan; 10 in the NS songs) are dropped
    everywhere.
  - Every DT double differs from its target's label: the zero-render scan finds 606 kept examples with one, all 606
    differing in at least one sounding control, 565 in at least one of the eight switches, and a median 73 stored
    settings. They are re-rendered with the target's full setting (phase 1b), so every rung trains and reads the
    same examples. If phase 1b's positive control fails, all 606 are dropped from every rung instead.
- **Class (step 5).** Every consumer keys on the section's class (`cls`), as V-real does: the network's class input,
  the constant, the pull's cells and the merge pools. Consequence, stated: D_CC's labels were drawn around the
  coin's (`base`) S, so `cls` carries no label information in this build, and the constant per (amp, `cls`) is
  roughly class-blind (pr12-crunch drive2 is on in 52.7% of labels by `base`, 42% by `cls`, so its majority flips to
  off). A future build draws the class from the section.
- **Inputs.**
  - P2a: the target render at its level in its own mix (the stored target times the mix's stored gain), so no rung
    can read absolute level, which a song does not carry. This is a perfect-separator rung.
  - P2b: P2c's mix minus every other guitar (the rendered ones and the recorded stand-ins), at P2c's own backing and
    overall gains and the same mastering draw. No gain is recomputed.
  - P2c: the stored self-built mix. P2d: its stored X-LANCE stem.
  - Each in the network's first channel, the second zeroed (D_stem's layout).
- **Augmentation (step 18).** None on the ladder. P2d-aug, D_CC's full augmentation on the stem, is a separate arm.
- **Length (step 22).** A fixed, generous epoch cap with a checkpoint every 10 epochs, the cap set from P1 and
  entered in the ledger before the ladder trains. Reads use both the final checkpoint and the NS-best one. A
  stopping metric that follows the sound (step 23's second fix) is not done here.
- **Diagnostics (step 24).** Each checkpoint logs, in eval mode: the loss on a fixed 300-example training subset
  and on NS, each head family's loss, and the label-marginal baseline in the same units.
  - The baseline is fitted on the training labels per (amp, `cls`) and read out of sample on NS: each knob a
    4-component 1-D mixture by EM, its sigma held to the network's range [e^-6, e^1]; each switch its on-rate; each
    mic and the amp their frequencies (add-half smoothing).
  - In P1 it is fitted on the memorised examples themselves (in sample), said so.
- **Seeds.** One seed (20261042) on the ladder's first pass; the second (20261043) where a paired difference is
  undecided, and for D_fix.

## The findings, one by one

Steps 1, 2, 9, 10, 17, 25, 28, 34 and 38 are OK in the review and need nothing. The rest:

| Step | Finding | Fix | Verified by | Can end as |
|---|---|---|---|---|
| 3 | Overlapping sections leak into early stopping | Stopping on held-out songs (step 23) | the recipe | Fixed |
| 4 | 2,699 examples from 10 songs | Learning curves on P2a and P2d (settings per performance, and performances); F20 is the next plan if they rise | the curves | Limit, measured |
| 5 | Class input is the coin in training, the part's class on songs | `cls` everywhere | P6 (FS half), a test that training, reads and V-real use one field, every run | Fixed |
| 6 | Wide, wet prior; runaway targets | Runaways dropped; the constant re-taken by `cls`; the prior itself is the next build's | every run; P3 measures the readout's share | Fixed (runaways), Limit, measured (prior) |
| 7 | Silent refusals skew the mode mix | The redraw in `cc_build` for the next build; by-knob error split by mode | the split | Limit, measured |
| 8 | Inaudible settings labelled in full | P2a's per-head table: which heads read even from the clean target; the audibility-weighted loss in phase 5 if the time effects fail there | P2a | Ruled out, or Fixed in D_fix, or Limit, measured |
| 11 | Stereo-only controls labelled, input mono | Their heads read on P2a's table; stereo input is the next build's | P2a | Limit, measured |
| 12 | DT doubles rendered with a different setting | Re-rendered with the target's full setting; `cc_build` renders them so in the next build | the positive control, P2c, P2d | Fixed |
| 13 | Stand-ins in 44% (a D_CC/D_F5 confound) | All comparisons here are within one build; P2b removes every other guitar | b − c | Ruled out (as an error) |
| 14 | The level prior holds V-real bands' statistics | V-real bands out of the ratio prior for the next build; level statistics, not labels | a test | Limit, measured |
| 15 | Half the mixes mastered; V-real's raw | By-knob error split by mastered on P2c and P2d | the split | Ruled out, or Limit, measured |
| 16 | The stem holds every guitar | Located by the ladder; the fix chosen in phase 5 | a − b, b − c, c − d | Fixed in D_fix, or Limit, measured |
| 18 | Augmentation may hide treble cues | P2d against P2d-aug | the pair | Ruled out, or Fixed |
| 19 | Tone lost before the model | Re-read with trained models by the ladder | the ladder | Ruled out, or as 16 |
| 20 | Network never shown to fit | P1 | P1 | Ruled out, or Fixed |
| 21 | Loss in knob units | P2a by sound against by knob | P2a | Ruled out, or a phase 5 candidate |
| 22 | Very little training | P1, the ladder's checkpoints, the curves | as named | Fixed (the length) |
| 23 | Early stopping on the training songs | Held-out songs and checkpoints | the recipe | Fixed |
| 24 | Training logs only total losses | Eval-mode, per-head and baseline logs | a test, P1 | Fixed |
| 26 | Knobs pulled toward the training average | P3 (toward S) read beside the plain readout | P3 | User decision |
| 27 | A 0.5 cut flips near-chance pedals | P3 (S's state) and the near-chance rule, beside the plain readout | P3 | User decision |
| 29 | Reads almost nothing on FS5 | P1 and the ladder locate it; D_fix | the ladder, D_fix | Fixed, or Limit, measured |
| 30 | Never read by sound on FS | The by-sound reads | P2 | Fixed |
| 31 | V-real: 11 parts, 7 bands | Part-weighted co-primary; Wickerman ElecGtr2 and 3 counted as one input | the rows | Limit, measured |
| 32 | Wickerman ElecGtr2 and 3 share one input | Counted once in every new row (P3 and P4 alike); P4 reads their own amp tracks | rows, P4 | Fixed |
| 33 | Render-order noise for time effects | Every new render, comparators included, in its own primed process | the renderer | Fixed |
| 35 | Low power | As 31; leave-one-band-out beside | the rows | Limit, measured |
| 36 | S chosen on V-real's clips | P5: S re-picked without them; read against both | P5 | Ruled out, or Fixed (S' as the comparator) |
| 37 | The training average leans worse than S | The constant re-taken by `cls`, re-rendered; P3 | P3 | User decision |

## Phases

### Phase 1: zero renders, no training

- **P5, S's home advantage (step 36).** Both start rules (`pipeline_review.pick_start`) re-run on the pinned
  development parts minus V-real's 9 part slugs (its 8 clips in the choice sets, and It Was My Fault ElecGtr1's
  other clip), then minus V-real's bands (clean only; crunch keeps one part). Where a pick changes (S'), S' − S on
  V-real from the stored distances where they exist; T3's own crop of It Was My Fault ElecGtr1, It Was My Fault
  ElecGtr3 and Signs ElecGtr3 have none and are listed (their renders are declared before they run, at most 66).
- **P6, the class input (step 5), FS half only.** D_CC's knob error on FS_CC with the coin it was trained on against
  the section's class. The V-real flip is dropped: the class fix is adopted either way, so it would touch held-out
  inputs for nothing.
- **P7 is dropped.** Its question, how much the doubles cost, is answered by fixing them (phase 1b); its "matching"
  group would hold 2 FS examples.
- **Code, each with tests:** the recipe (split, runaway and doubles handling, `cls` everywhere, eval-mode per-head
  and baseline logs, checkpoints). Phases 3 and 4 add their own: the by-sound read with a fresh primed process per
  answer render (step 33), and the V-real rows with Wickerman ElecGtr2 and 3 counted as one input and a
  part-weighted co-primary (steps 31, 32, 35). The next build's `cc_build` changes (the redraw, step 7; the ratio
  prior without V-real's bands, step 14; the class drawn from the section, step 5; doubles with the full setting,
  step 12) are written with phase 5, versioned so that D_CC's stored plan still reproduces.
- **The dirty-double scan** (done 2026-10-31, zero renders, training data only): 606 of 3,033 kept examples have a
  DT double; 565 differ in at least one of the eight switches, 424 in a pedal switch; a median 73 stored settings
  differ.

### Phase 1b: the doubles fix (renders, no training)

- For each of the 606 doubled examples, every other guitar re-rendered as `cc_build` rendered it, except that each
  DT double takes the target's full setting and renders in its own primed process (the target's time effects run on
  across renders in one process).
- **Positive control first:** the sections of 4 doubled examples are replayed exactly as `cc_build` rendered them
  (each section's whole job list in one shared process, the same order and priming), and every example's sum must
  reproduce its stored others within one FLAC step. If not, phase 1b stops and the 606 are dropped from every rung
  instead.
- The production re-render puts the ordinary other guitars in a new job order: valid renders, not necessarily
  bit-identical to the stored ones. After it, P2b of the doubled examples is rebuilt from their new mix, at its
  recomputed backing gain, with the same parity check.
- Then their mixes and X-LANCE stems (`cc_build build`'s recipe), written to `pipeline-fix/cc-dt/`; D_CC's files are
  never written.
- About 3,600 renders with priming and 606 separations, about 1.5–2 h.

### Phase 2: P1, can the network learn? (minutes of MPS)

- D_CC's network on 200 fixed training examples, inputs P2a and P2d, no augmentation, no early stopping, until the
  eval-mode loss on them stops falling (at most 1,500 epochs).
- Read per head family: how far below the in-sample label-marginal baseline its loss gets. No pass bar.
- If most heads stay near their baseline even on P2a, the network, loss or labels are broken: that is found and fixed,
  and P1 re-run, before phase 3.
- **Setting the ladder's length from P1:** the cap is the number of optimiser steps at which P1's P2a loss came within
  10% of its final fall, in the ladder's epochs (37 steps each), at least 60 epochs and at most 200. It is entered in
  the ledger before the ladder trains. A cap that would take the plan's MPS budget past 12 h comes back to the user.

### Phase 3: P2, where is the tone lost?

In the lean order: each step runs only while the one before leaves the question open.
1. **P2a and P2d** (one seed each), read by knob on FS and NS (R0's rule; zero renders), at both checkpoints.
2. **P2b and P2c**, unless a − d is already closed by knob.
3. **By sound:** a fixed sample of 60 FS and 60 NS examples (drawn once, spread over sections, entered in the ledger),
   grown to 120 each while the locating rows stay undecided.
   - Each model's answer (both halves' readouts and both seeds pooled, the plain readout on the example's own amp)
     is rendered through the example's own measure DI in its own process, primed with the same setting (as the
     targets were), and judged against the stored target render on both halves (`knob_ceiling.judge`).
   - S (the `cls` start preset) and the constant (`cls`) are rendered once for the sample.
   - **Positive control first:** each sampled example's own label on its own select ("truth") must reproduce its
     stored target render (the judge at its floor), and on the class start preset's select, where answers are
     written, too. At most 480 renders.
   - A judge refusal (a silent render) is counted and shown per row, never dropped quietly.
   - **The locating rows:** a − b, b − c and c − d, paired on the same examples. Beside them, each rung − S and −
     constant. FS rows are band-clustered (6 bands); NS rows are section-clustered with the caveat that NS is one
     clean and one crunch song (2 bands).
4. **Beside the ladder:**
   - P2d-aug (step 18);
   - learning curves on P2a and P2d, by knob: 25% and 50% of the training examples nested within sections (more
     settings per performance, F20's lever), and 50% of the sections with all their examples (fewer performances);
   - new songs by k-fold: the 10 songs in 5 folds by band (BKS's two songs together), P2a and P2d, one seed, the
     ladder's length, read by knob on every held-out song (band-clustered, 9 bands);
   - zero-render splits of the by-knob error: by draw mode (step 7) and by mastered (step 15).
- **Reading:** the rung whose locating row carries the loss is the failing step. If P2a has no skill, the problem
  is the model, labels or loss (steps 20–24), not the input.
- **An easier task than V-real:** on FS and NS the model is told the true amp, and the answer is rendered on it. On
  V-real no Morgan amp is the real one. Phase 5's by-sound read with the amp mismatched measures that gap.

### Phase 4: P3 and P4 on V-real (measurements)

- **P3, fall back to S (steps 26, 27, 37), a measurement only.** The user ruled on 2026-10-27 that writing S for
  unreadable controls is a measurement, not the method. For D_CC and for the ladder's best rung that a song can
  feed (P2c or P2d):
  - the plain readout;
  - knobs pulled toward S, and a switch whose head did not read on FS and NS kept at S;
  - the near-chance rule (F20's decision C): a switch within δ of 0.5 takes its pool's majority, δ set on FS.
- **P4, real guitar input (steps 9, 11, 32).** P2a's model reads V-real's own amp tracks at the training median
  loudness: does learning from Morgan renders carry over to real recordings?
- **Inputs on V-real:** P2c reads the crop's raw mix, P2d its stored stem, P2a the amp track (P4). P2b has no input
  on a real song and is not read there.
- Every answer, and every comparator (S, the `cls` constant, D_CC's plain answer), is rendered in its own primed
  process (step 33), since the stored comparators were rendered in shared processes. Wickerman ElecGtr2 and 3 count
  as one input in both P3 and P4. Band-weighted, 90% band-clustered t (7 bands), part-weighted beside.

### Phase 5: the located fix, D_fix, and scale

- **Chosen on FS, NS and the k-fold reads only**, before any V-real read of D_fix. Phase 4's V-real reads are
  measurements; if they shape the choice, D_fix's V-real read is labelled selection-contaminated. The candidates by
  outcome:
  - other guitars carry the loss (a − b small, b − c large): train where the target leads the other guitars; how
    the product says a part is not readable is for the product session;
  - the separator carries it (c − d large): read the mix, or the mix and the stem;
  - the clean input already fails: the loss or labels (audibility weights, a sound-aware loss), sized by P1;
  - the curves still rise at full size: scale (F20's staged build), read on V-real at each stage, in its own plan.
- **D_fix:** the recipe plus every adopted fix, 2 seeds, read by sound on FS and NS, with the amp mismatched (about
  480 renders), and on V-real with the plain readout as primary and P3's readouts beside.
- **Decisions for the user, with the evidence:** whether to adopt the S fallback or the near-chance rule
  (steps 26, 27, 37), and whether to scale.

## Findings log

Every result of this plan, in the order it landed: what was found, its numbers, its caveats, where it is stored and
what it changes. Each is audited before it is entered; the review's steps carry the same results as dated lines.

**Where things are.**
- Data: `~/ndsp-presets/learn/trusted-data/pipeline-fix/` (below, `PF/`).
- Code: `learn/pipeline_fix.py`.
- Ledger: `docs/dev-test-ledger.json`, entry `pipeline-fix`.
- Logs: `logs/pf-*.log` in the main checkout.
- The plan and phase 1's code merged in PR #346 (merge commit c8d80ee); phase 2 onward on branch `ml/pipeline-fix-p2`.

**How to read the numbers.**
- "E − constant" is the mean absolute knob error, in a knob's unit range, minus the constant's. Negative is better;
  0.01 is 1 point of a knob's range.
- Intervals are 90%. By-knob reads are clustered by section (R0's rule, `trusted_data_t3_r.section_t`). FS spans
  21 sections in 6 bands; NS spans 36 sections in 2 songs.
- "Readable" is R0's rule: knobs whose error interval is below the constant's; switches whose AUC interval is above
  0.5; mics and the amp whose accuracy interval is above the base rate.

### F1. S has only a small home advantage on V-real (review step 36)
- **Result.** The start rules were re-run on the pinned development parts without V-real's 9 part slugs.
  - The clean picks stay (19 parts).
  - The crunch picks (7 parts left) all change: Standout Thrash Rhythm (PR12), Wall Of Doom (SW50R) and Dirty Coil
    Rhythm (AC20).
- **Numbers.** On V-real, from stored distances:
  - S′ − S on the crunch parts: +0.0380 [−0.0099, +0.0858], 6 parts, 4 bands, 3 worse; part-weighted +0.0542.
  - All parts: +0.0253 [−0.0052, +0.0558].
- **Caveats.**
  - Signs ElecGtr3 has no stored distance; its 3 groups are rendered in phase 4.
  - Without V-real's bands the crunch rule keeps 1 part, so that variant's +0.574 says nothing about home advantage.
    The clean AC20 pick changes there (Gtr Lead FX).
- **References.** `PF/p5.json`; `cmd_p5`, `start_rules`, `s_prime_rows`; `pipeline_review.pick_start` (re-derives both
  stored choices exactly); ledger `phase_1_outcome`.
- **Changes.** S is a roughly fair bar. S′ (crunch) is rendered and read beside S in phase 4.

### F2. The class input is used, and its training/real-song mismatch costs a little (step 5)
- **Result.** On FS_CC, D_CC was told the section's class instead of the coin it was trained on. This was tried on
  the 174 of 334 examples where the two differ.
- **Numbers.** Knob error +0.0030 [+0.0019, +0.0042], worse in 7 of 8 bands. Unpulled seed-mean medians, both halves.
- **References.** `PF/p6.json`; `cmd_p6`; D_CC's runs `cc/runs/D_CC-2026104{2,3}.pt`; ledger `phase_1_outcome`.
- **Changes.** Every retrain conditions on the section's class: the network, the constant, the pull cells and the
  merge pools (`RungData`, `constant_of`, `arm_data`; tested in `test_every_run_and_read_conditions_on_the_section_class`).

### F3. Every DT double in D_CC was rendered with a different preset from its target (step 12)
- **Result.** All 606 kept examples with a DT double were affected. The double used the target's 25-control core on
  a dried centre, not its full label.
- **Numbers.**
  - Every one differs in some sounding control; 565 differ in at least one of 8 switches.
  - By switch: drive1 210, drive2 209, compressor 237, reverb 322, delay 284, tremolo 206, doubler 188, gate 337.
  - A median 73 stored settings differ (10th–90th percentile 66–79).
- **The fix (phase 1b).** The doubles were re-rendered with the target's full setting, each in its own primed
  process.
  - Positive control first: the original job lists of 4 sections were replayed. All 46 examples reproduced their
    stored others to half a FLAC step (max 1.2e−7). That took 232 renders.
  - Then 2,380 renders: 604 of 606 were re-rendered. Two were refused (802610, 802889: a near-silent double, the rule
    of `trusted_data.near_silent`).
  - Their mixes and X-LANCE stems were built for all 604 (`build-doubles`, an MPS and a CPU worker; 26 examples were
    built by both, with identical files). The stem's SNR against the target is unchanged: a median change of
    +0.01 dB (10th–90th percentile −0.3 to +0.3; median −7.9 dB new, −8.1 dB old). The doubles now match the label;
    the separator recovers the target no better or worse.
  - P2b's input for these examples is rebuilt from their new mix (`build-inputs --doubled`).
- **References.** `PF/dirty-doubles.json`, `PF/cc-dt/control.json`, `PF/cc-dt/rows/`; `double_status`,
  `cmd_render_doubles`, `other_jobs`; `cc_build.py` (`if o["dt"]:`, the original rule); ledger `phase_1b`.
- **Changes.** The re-rendered doubles enter D_fix (see F8).

### F4. A clean target's raw level would leak the settings (P2's design)
- **Result.** A target render's level is set by its own settings. To sit at the drawn mix loudness it needs a gain of
  −48.5 to +35.9 dB (10th–90th percentile −20 to +16, median −4.1; 3,034 build rows).
  - A model fed the raw render could read volume and gain from level, which a song never offers.
- **The fix.** P2a is fed the target times its mix's stored gain. P2b is P2c's mix without any other guitar, at the
  stored gains and with the same mastering draw.
  - The full mix rebuilt beside them matched every stored mix exactly: 0 grid steps on 3,033 examples.
- **References.** `PF/inputs/`; `cmd_build_inputs`, `rung_mixes`; `logs/pf-inputs-*.log`; ledger `phase_2`.

### F5. The network, loss and labels can learn (step 20 ruled out; step 24's logs in place)
- **Result.** P1 trained on 200 fixed training examples without a DT double, on the clean input (P2a), with no
  augmentation. It ran 871 epochs (3,484 steps, 16.2 min on MPS); the best checkpoint is at epoch 770.
- **Numbers.** Eval-mode loss against the in-sample label-only baseline:
  - knobs (joint) −2.51 against −0.84; knobs (marginal) −2.42 against −0.85;
  - switches 0.037 against 0.58;
  - mics 0.0016 against 1.73;
  - amp 0.0005 against 1.09;
  - every one of the 85 knobs and 28 switches is below its baseline.
- **Length.** The loss made 90% of its fall by 1,124 steps (epoch 280). By the plan's rule the ladder runs 60
  epochs with a checkpoint every 5.
- **P1 on the stem (P2d):** it memorises as fully (knobs −2.50 against −0.84, switches 0.041 against 0.58, every head
  below baseline), but more slowly: best checkpoint at epoch 1,070 against 770 on the clean input
  (`PF/runs/P1-d.json`).
- **Caveat.** It memorises; it says nothing about generalising.
- **References.** `PF/runs/P1-a.json`; `cmd_p1`, `fit`, `head_losses`, `Baseline`; ledger `phase_2_outcome`,
  `phase_3_length`.

### F6. Even a perfect separator barely helps the knobs (steps 16, 19, 21, 29)
- **Result.** P2a, the clean target at its in-mix level, was read at its NS-best checkpoint (epoch 25 of 60) and at
  its final one. It reads most switches and both mics, but its knob error beats the constant by only about 1 point of
  a knob's range. New songs read about like seen performances.
- **Numbers** (by knob, R0's rule).

  | Set | Checkpoint | Knobs readable | Switches readable | Mics and amp readable | Knobs worse | E − constant |
  |---|---|---|---|---|---|---|
  | NS (383) | best | 23 of 85 | 27 of 28 | 3 of 3 | 6 | −0.0086 [−0.0106, −0.0066] |
  | FS (207) | best | 14 of 85 | 22 of 28 | 3 of 3 | 4 | −0.0097 [−0.0119, −0.0076] |
  | NS (383) | final | 14 of 85 | 26 of 28 | 3 of 3 | 6 | −0.0053 [−0.0083, −0.0024] |
  | FS (207) | final | 16 of 85 | 21 of 28 | 3 of 3 | 6 | −0.0101 [−0.0138, −0.0064] |

  - The median knob error is 0.163 against the constant's 0.175 (NS, best).
  - By loss, on NS its knobs stay worse than the label-only baseline (joint −0.24 against −0.33). Switches 0.592
    against 0.617, mics 1.24 against 2.02, amp 1.0996 against 1.0992 (no better than chance).
  - The NS loss is lowest at epoch 25 and rises after it, while the training loss keeps falling: it overfits the
    training performances.
- **Caveats.**
  - The NS-best checkpoint is chosen on NS, so its NS read leans optimistic.
  - NS is 2 songs (one clean, one crunch).
  - One seed so far. Trained on 1,787 examples (F8).
- **References.** `PF/runs/P2a-20261042.json` (curves in its `log`), `PF/reads/P2a-best.json`,
  `PF/reads/P2a-final.json`; `cmd_train`, `cmd_read`; ledger `phase_3`.
- **Changes.** The separator is not the first blocker for the knobs. Whether knob error is the wrong yardstick
  (many settings sound alike, step 21) or the model truly reads little is decided by the by-sound read, which is
  running.

### F7. The knob skill is only on random settings, not on realistic presets (steps 6, 7, 21)
- **Result.** P2a's E − constant was split by how each label was drawn.
  - Fully random ("wide") settings carry the gain.
  - Settings near S ("start") gain a little.
  - Settings near a factory preset ("factory"), the most realistic kind, gain nothing; at the final checkpoint they
    are reliably worse than the constant.
- **Numbers** (E − constant, section-clustered).

  | Set | Checkpoint | wide | start | factory |
  |---|---|---|---|---|
  | NS | best | −0.0224 [−0.0262, −0.0186] (117) | −0.0116 [−0.0155, −0.0077] (89) | +0.0014 [−0.0007, +0.0034] (177) |
  | FS | best | −0.0243 [−0.0285, −0.0201] (65) | −0.0086 [−0.0139, −0.0033] (46) | −0.0002 [−0.0028, +0.0024] (96) |
  | NS | final | −0.0286 [−0.0334, −0.0237] | −0.0047 [−0.0103, +0.0009] | +0.0074 [+0.0041, +0.0108] |
  | FS | final | −0.0298 [−0.0353, −0.0242] | −0.0082 [−0.0184, +0.0020] | +0.0017 [−0.0024, +0.0058] |

- **Reading.** The model learns to tell extreme random settings from the average. It does not tell realistic presets
  apart, and real songs use realistic presets. Step 7's skew (wide draws refused most) is a second-order issue
  beside this.
- **Caveats.**
  - "factory" labels sit nearer the constant, so the constant's own error is smaller there. That is part of why no
    gain shows; the by-sound read and a per-mode constant check it.
  - One seed.
- **Mastering (step 15).** The split by mastered is no different (NS best: −0.0088 unmastered, −0.0082 mastered).
  P2a's input is not mastered, so step 15 is read on P2c and P2d.
- **References.** `PF/reads/P2a-*.json`, `e_minus_constant_by_mode` and `e_minus_constant_by_mastered`; `split_e`.
- **Changes.** At first this looked like a root blocker: the prior (step 6) trains mostly on unrealistic settings,
  and the knob loss rewards telling them apart. **F11 corrects it:** by sound, P2a's answers on factory draws are
  among its best (NS −0.337). So the knob read misses skill there; it does not show that skill is absent.

### F8. Deviation: the ladder runs on the examples without DT doubles
- **Result.** P2a trained before phase 1b finished, so the recipe used its fallback: every doubled example out.
  - To keep every rung, curve, k-fold run and the by-sound sample on one set, the whole ladder is pinned to that set:
    1,787 training, 207 FS and 383 NS (NS has no DT doubles).
  - The by-sound sample was drawn from it: 120 FS and 120 NS in a fixed order, the first 60 of each read first.
- **References.** Ledger `phase_3_doubles`, `phase_3_doubles_why`; `PF/sound/sample.json`; `recipe_inputs(pin=...)`.
- **Changes.** The re-rendered doubles (F3) enter D_fix, which verifies step 12.

### F10. The by-sound read reproduces the truth (its positive control)
- **Result.** Each of the 120 sampled examples' own label, on its own select, was rendered through its own measure DI
  in a fresh primed process. Each one reproduces its stored target render: judge distance median 1.5e−6, at most
  1.0e−4, against S's distances of a few dB. 240 renders.
- **References.** `PF/sound/judge/truth/`; `cmd_answers --name truth`, `cmd_sound_render`; ledger `phase_3_sound`.
- **Changes.** The by-sound path (DI, trim, select, judge) is sound. Its second control, the label on the class start
  preset's select (where answers are written), is rendering.

### F11. By sound, the model fed the clean guitar gets much closer than S and the average preset (steps 21, 30)
- **Result.** P2a's answers (NS-best checkpoint, one seed) were rendered for the first 60 FS and 60 NS sample
  examples, each through the example's own measure DI. They sound much closer to the known target than S and than
  the constant, on seen performances and on new songs alike.
- **Numbers** (log distance ratio; −0.24 is about 21% closer).

  | Row | FS (60, 6 bands) | NS (60, 36 sections) |
  |---|---|---|
  | P2a − S | −0.248 [−0.383, −0.114], 6 of 6 bands better | −0.241 [−0.318, −0.165], 29 of 36 better |
  | P2a − constant | −0.252 [−0.372, −0.132], 5 of 6 better | −0.247 [−0.310, −0.185], 32 of 36 better |
  | constant − S | +0.004 [−0.107, +0.115] | +0.006 [−0.066, +0.078] |

  By draw mode, P2a − S:
  - FS: wide −0.303 [−0.436, −0.171] (25); start −0.281 [−0.634, +0.073] (9); factory −0.170 [−0.289, −0.051] (26).
  - NS: wide −0.254 [−0.355, −0.153] (15); start −0.033 [−0.216, +0.150] (14); factory −0.337 [−0.453, −0.220] (31).

  S's median distance to the targets is 5.7 on both sets.
- **Reading.**
  - Fed the clean guitar, the model reads the tone well enough to sound clearly closer than S, even on new songs and
    on realistic presets.
  - Knob error badly understates this (F6, F7): many settings sound alike, so the right sound often sits on "wrong"
    knobs (review step 21 confirmed).
  - On the made-up songs the constant and S are about equally far from the targets, so the yardstick is fair.
  - A suspected mechanism for "never beats S", that the readout's knob-fitted pull shrinks this skill away, was
    tested at once and is refuted (F12).
- **Caveats.**
  - The targets are Morgan renders on the true amp, an easier task than V-real's real amp tracks with no matching amp.
  - The NS-best checkpoint is chosen on NS's loss (not its sound).
  - One seed; the first 60 of each sample.
- **References.** `PF/sound/judge/{P2a-best,S,constant}/`, `PF/sound/report.json`, `PF/sound/answers/P2a-best.json`;
  `cmd_answers`, `cmd_sound_render`, `cmd_sound_report`, `log_ratio`; ledger `phase_3_sound`; `logs/pf-sound-*.log`.
- **Changes.** The ladder's question is now sharp: how much of this survives the mix (P2c) and the stem (P2d)? Every
  model and readout from here is read by sound, not only by knob.

### F12. The readout's pull toward the average costs only a little sound skill (steps 26, 27)
- **Result.** P2a's answers were pulled toward the constant exactly as D_CC's readout does, then rendered on the same
  sample. The pull is `direct_stems.fit_pull_table`, fitted on FS by knob error per (amp, section class); switches and
  mics stay plain. It changes a median 17 settings per answer (at most 30). The pulled answers sound only slightly
  less close.
- **Numbers.**

  | Row | FS (the pull's fit set) | NS (primary) |
  |---|---|---|
  | plain − pulled | −0.012 [−0.022, −0.001], 5 of 6 bands | −0.006 [−0.016, +0.004], 20 of 36 sections |
  | pulled − S | −0.236 [−0.373, −0.100] | −0.236 [−0.311, −0.160] |
  | pulled − constant | −0.240 [−0.370, −0.111] | −0.242 [−0.302, −0.181] |

- **Reading.** The suspected mechanism (F11), that a knob-fitted pull discards the sound skill, is refuted in
  distribution. The pull is a small cost, not the reason the old models never beat S. The loss must come later: the
  mix and stem input (P2c, P2d) or the step to real songs (P3, P4).
- **Caveats.** One model and seed; in distribution. Switches are not pulled here; step 27's switch readout is read in
  P3.
- **References.** `PF/sound/answers/P2a-best-pulled.json`, `PF/sound/judge/P2a-best-pulled/`; `fit_knob_pull`,
  `cmd_answers --readout pulled`; ledger `phase_3_readout`; `logs/pf-sound-pull-*.log`.
- **Changes.** Step 26: the pull is ruled out as the main loss (a small cost, measured). Step 27's switch rule is
  still read in P3.

### F13. Fed the stem, the model reads almost nothing, even on seen performances (steps 16, 19, 29)
- **Result.** P2d is the same recipe as P2a on D_CC's stored X-LANCE stem (one seed, best checkpoint epoch 20 of
  60, 30.6 min). Its knob error equals the constant's, and it reads few switches.
- **Numbers** (by knob, R0's rule).

  | Set | Checkpoint | Knobs readable | Switches readable | Mics and amp readable | Knobs worse | E − constant |
  |---|---|---|---|---|---|---|
  | NS | best | 6 of 85 | 4 of 28 | 1 of 3 | 4 | +0.0004 [−0.0004, +0.0013] |
  | FS | best | 4 of 85 | 6 of 28 | 2 of 3 | 8 | +0.0000 [−0.0011, +0.0012] |
  | NS | final | 4 of 85 | 5 of 28 | 0 of 3 | 30 | +0.0055 [+0.0040, +0.0070] |
  | FS | final | 1 of 85 | 7 of 28 | 0 of 3 | 11 | +0.0031 [+0.0009, +0.0053] |

  By loss on NS (best): switches 0.617 against the baseline's 0.617, mics 1.99 against 2.02, amp 1.086 against 1.099,
  9 of 85 knobs below baseline.
- **P2c (the mix), the same recipe** (best checkpoint epoch 5 of 60, 12.5 min): by knob NS +0.0014 [+0.0004,
  +0.0024], FS +0.0010 [−0.0002, +0.0023] (best); 4–5 knobs and 2–4 switches readable; by loss on NS at the
  baseline (switches 0.618 against 0.617). The mix reads no better than the stem by knob (`PF/reads/P2c-*.json`).
- **Reading.** Between the clean guitar (P2a: 22–27 switches, both mics and the amp readable) and the stem, almost
  everything is lost, on seen performances too; by knob it is already lost at the mix. This is the review's step 16/19 suspicion, now measured with
  trained models on one example set. P2c (the mix) says whether it is lost at the mix or at the separator; P2b
  whether at the other guitars or at the backing. P2d's by-sound read is rendering.
- **Caveats.** One seed; the ladder's pinned set (F8); the stem of the old doubles is not in this set.
- **References.** `PF/runs/P2d-20261042.json`, `PF/reads/P2d-best.json`, `PF/reads/P2d-final.json`;
  `logs/pf-P2d.log`.

### F14. By sound, the stem keeps about a fifth of the clean input's skill (the locating row a − d)
- **Result.** P2d's answers (best checkpoint), rendered on the same sample, lean only slightly closer than S. The
  paired row against P2a is large and reliable.
- **Numbers.**

  | Row | FS (60, 6 bands) | NS (60, 36 sections) |
  |---|---|---|
  | P2d − S | −0.072 [−0.202, +0.058], 3 of 6 bands better | −0.042 [−0.125, +0.041], 19 of 36 better |
  | P2d − constant | −0.076 [−0.198, +0.046] | −0.048 [−0.093, −0.003], 21 of 36 better |
  | P2a − P2d | −0.176 [−0.222, −0.130], 6 of 6 better | −0.199 [−0.258, −0.141], 32 of 36 better |

- **Reading.** Of P2a's −0.24 against S, the stem keeps −0.04 to −0.07: about 80% of the skill is lost between the
  clean guitar and the stem, on new settings and new songs alike. This is the failure the review called central
  (step 29), located at the input (steps 16, 19), not the model (F5, F11). P2c's and P2b's reads split it between
  the other guitars, the backing and the separator.
- **Caveats.** One seed each; the ladder's set (F8); the targets are Morgan renders on the true amp.
- **References.** `PF/sound/judge/P2d-best/`, `PF/sound/report.json`; `logs/pf-sound-d-*.log`.

### F15. The skill dies at the mix, not at the separator (the locating rows a − c and c − d)
- **Result.** P2c's answers (the self-built mix as input; best checkpoint) sound no closer than S. The stem (P2d)
  sounds as close as the mix, or closer.
- **Numbers.**

  | Row | FS (60, 6 bands) | NS (60, 36 sections) |
  |---|---|---|
  | P2c − S | +0.059 [−0.070, +0.188], 2 of 6 better | −0.033 [−0.106, +0.039], 19 of 36 better |
  | P2c − constant | +0.055 [−0.098, +0.208] | −0.039 [−0.078, −0.000] |
  | P2a − P2c | −0.307 [−0.363, −0.251], 6 of 6 better | −0.208 [−0.265, −0.151], 29 of 36 better |
  | P2c − P2d | +0.131 [+0.066, +0.197], 0 of 6 better | +0.009 [−0.033, +0.050] |

- **Reading.**
  - Nearly all of the clean input's skill is gone once the guitar sits in the mix.
  - The separator does not lose it further; on FS the stem is reliably better than the raw mix.
  - So the review's leading suspect, the separator (step 16), is cleared as the place of the loss. What kills the
    skill is the guitar being in a mix: the other guitars, the backing, or both. P2b splits them.
  - The earlier mix-input arm (D_F5mix, not shown better than the stem) agrees.
- **Caveats.** One seed each; best checkpoints chosen on NS loss (P2c's at epoch 5).
- **References.** `PF/sound/judge/P2c-best/`, `PF/reads/P2c-*.json`, `PF/runs/P2c-20261042.json`;
  `logs/pf-sound-c-*.log`.

### F16. The doubles fix verified at the data level, on its own (step 12)
- **Result.** In the 604 re-rendered examples, every DT double (980) now carries exactly its target's label (all
  stored settings equal) and amp, and every other guitar (1,222) keeps exactly its original setting, amp and level.
  With the positive control (46 of 46 replayed examples exact, F3), the new mixes' exact rebuild (P2b parity 0 grid
  steps) and the unchanged stem SNR, the fix is verified without any model.
- **References.** `PF/cc-dt/rows/render-*.jsonl` against `cc/rows/render-*.jsonl`; `PF/cc-dt/control.json`;
  `logs/pf-inputs-dt-*.log`.
- **Changes.** Step 12: fixed. Its effect on a model is read only by a model that reads (the rule above).

### F17. The backing alone kills the skill; it is not only level (the locating rows a − b, b − c)
- **Result.** P2b, the target in its non-guitar backing with no other guitar at all (best checkpoint epoch 5 of 60,
  9.8 min), sounds no closer than S. Adding the other guitars (P2c) changes nothing further.
- **Numbers.**

  | Row | FS (60, 6 bands) | NS (60, 36 sections) |
  |---|---|---|
  | P2b − S | +0.029 [−0.094, +0.152] | −0.021 [−0.099, +0.056] |
  | P2a − P2b | −0.277 [−0.323, −0.232], 6 of 6 better | −0.220 [−0.278, −0.162], 32 of 36 better |
  | P2b − P2c | −0.030 [−0.122, +0.063] | +0.012 [−0.010, +0.034] |

  By knob: NS +0.0010 [−0.0001, +0.0021], 8 knobs and 5 switches readable (`PF/reads/P2b-*.json`).
- **By drawn level** (P2x − S, all 120 sample examples, terciles of the drawn guitar-to-backing ratio, cuts −10.6 and
  −6.5 dB):

  | Rung | quiet | mid | loud |
  |---|---|---|---|
  | P2a | −0.217 [−0.449, +0.015] | −0.254 [−0.371, −0.137] | −0.306 [−0.415, −0.198] |
  | P2b | +0.121 [−0.047, +0.289] | −0.062 [−0.225, +0.101] | −0.039 [−0.140, +0.062] |
  | P2c | +0.121 [−0.091, +0.334] | −0.022 [−0.139, +0.095] | −0.021 [−0.103, +0.061] |
  | P2d | −0.028 [−0.182, +0.126] | −0.104 [−0.262, +0.055] | −0.115 [−0.239, +0.009] |

- **Reading.**
  - The loss happens when the guitar is put in any backing, even a guitar loud against drums, bass and vocals.
  - Such a guitar is clearly audible, and a linear probe still reads 30 heads from the mix (the tone probe). So the
    information is likely there but not learned.
  - Every backing model peaks by epoch 5 and then overfits: about 1,800 examples from 8 training songs are too few to
    learn to ignore the backing.
  - Learnability, not masking, is the leading hypothesis. Its isolated test is P2b retrained on the same targets with
    many backings (no new renders), read on P2b's own fixed inputs.
- **Caveats.** One seed; 40 examples per tercile; the drawn ratio is against the full backing including other guitars.
- **References.** `PF/runs/P2b-20261042.json`, `PF/sound/judge/P2b-best/`; the split from `plan.json`'s
  `draw.ratio_db`.

### F18. Steps 3, 23, 8 and 11 checked on their own
- **Steps 3 and 23 (data check).** The held-out songs (NS) share no session, DI or time window with the training
  sections: 0 of 36 sections (`pipeline_review.es_overlap` on the recipe's split). FS, by contrast, shares all three,
  16 of 21 sections overlapping in time. Fixed.
- **Steps 8 and 11** (P2a's per-head losses on NS against the label-only baseline, best checkpoint):
  - The stereo-only heads sit at the baseline or above: delay width +0.684, ping-pong +0.002, cab pans +0.033 and
    −0.001, cab stereo −0.030 and −0.020, doubler spread −0.036. They cannot be read from a mono input: limit,
    measured. Stereo input is the next build's.
  - Time effects: 3 of their 15 knobs but 3 of 4 switches are below the baseline. Pedals: 1 of 10 knobs, 2 of 4
    switches. Springs: 0 of 3 knobs.
  - Even from the clean guitar most effect knob values do not read, while their switches do. That is step 8's
    inaudible-value problem, measured on a working model. By sound the answers still beat S (F11), so these knobs
    matter little to the sound: limit, measured.
- **References.** `PF/runs/P2a-20261042.json` (`heads.best.ns`).

### F19. Told a wrong amp, the clean-input model keeps most of its skill (the amp mismatch, alone)
- **Result.** P2a (seed 20261042, NS-best) was told, and rendered on, each of the two wrong amps, and judged against
  the target rendered on the true amp. It still sounds much closer than S on that same wrong amp; the mismatch costs
  about a quarter of the skill.
- **Numbers.**

  | Row | FS (60, 6 bands) | NS (60, 36 sections) |
  |---|---|---|
  | P2a(amp+1) − S(amp+1) | −0.197 [−0.306, −0.089], 6 of 6 better | −0.223 [−0.295, −0.150], 28 of 36 better |
  | P2a(amp+2) − S(amp+2) | −0.209 [−0.373, −0.045], 5 of 6 better | −0.217 [−0.283, −0.151], 30 of 36 better |
  | P2a − P2a(amp+1) | −0.065 [−0.108, −0.022] | −0.057 [−0.119, +0.006] |
  | P2a − P2a(amp+2) | −0.071 [−0.114, −0.029] | −0.047 [−0.107, +0.014] |
  | S(amp+1) − S | +0.015 [−0.027, +0.056] | +0.038 [+0.009, +0.067] |
  | S(amp+2) − S | +0.032 [+0.006, +0.059] | +0.022 [−0.014, +0.059] |

- **Reading.** The amp mismatch V-real imposes (no Morgan amp is the real one) costs a little, not the skill. A null
  P4 could not be put down to the mismatch. P4 runs next.
- **References.** `PF/sound/judge/{P2a-best-amp+1,P2a-best-amp+2,S-amp+1,S-amp+2}/`,
  `PF/sound/report-{ampmismatch,ampmismatch2,ampvsown,ampvsown2,samps}.json`; `cmd_answers --amp-shift`; ledger
  `phase_3_isolated` (a).

### F20. On real recordings, even the real guitar alone, the clean-input model does not transfer (P4)
- **Result.** P2a (both seeds, NS-best, pooled) read each V-real-11 part's own recorded amp track (the real guitar
  alone, at the median loudness of its training inputs, −21.84 LUFS). It was told the part's class and each forced
  amp, and its answers were rendered through the measure DI in fresh primed processes (438 renders).
  - Its answers sound clearly worse than S.
  - They are about as far as its own training average (the constant), which is itself clearly worse than S on real
    songs, though even with S on the made-up songs (F11).
- **Numbers** (band-weighted, 7 bands; Wickerman ElecGtr2 and 3 as one part; all 66 directions; none refused).

  | Row | All | Without the 2 quiet inputs | Clean | Crunch |
  |---|---|---|---|---|
  | P4 − S | +0.153 [+0.039, +0.268], 1 of 7 bands better; part-weighted +0.129, 1 of 10 parts better | +0.148 [+0.015, +0.281] | +0.028 (2 bands) | +0.203 (5 bands, 0 better) |
  | constant − S | +0.170 [+0.056, +0.284], 1 of 7 better | +0.142 [+0.020, +0.264] | +0.154 | +0.177 |
  | P4 − constant | −0.017 [−0.090, +0.057], 4 of 7 better | +0.006 [−0.054, +0.067] | −0.126 | +0.027 |
  | P4 − P4 pulled | +0.000 [−0.016, +0.017] | | | |
  | S′ − S (crunch parts only) | +0.035 [−0.002, +0.071], 1 of 5 better | | | |

  - P4 − S per part: Colour Me Red ElecGtr02 −0.147 (the only part better), Signs ElecGtr3 +0.008, Colour Me Red
    ElecGtr03 +0.078, It Was My Fault ElecGtr1 +0.167, Wickerman ElecGtr1 +0.167, Wickerman ElecGtr2+3 +0.162, Get Out
    Of Bed ElecGtr2 +0.180, Let's Dance ElecGtr3 +0.229, Femme ElecGtr5 +0.435.
  - Leave one band out: +0.106 to +0.185.
- **Checks.**
  - The positive control passes: the fresh S renders match the label table's stored distances on all 60 (part, amp,
    half), at most 1.0e−4 against the 0.005 tolerance. So render order (step 33) does not move V-real's S.
  - The side row declared before the read (inputs with over 20% of frames at the grid floor: Colour Me Red ElecGtr03
    and It Was My Fault ElecGtr1) changes nothing.
  - The S′ row covers only the crunch parts by design; it agrees with P5's stored-distance read (+0.038).
  - The model's own amp guesses on the real tracks: SW50R 13, AC20 7, PR12 2 (of 22 halves).
- **Reading.**
  - The amp mismatch alone costs about 0.06 (F19), so it does not explain +0.15.
  - On real recordings the model adds nothing over its own average, and that average is far from what real songs
    need: the training prior (random, factory-centred and S-centred settings, wet) does not look like real tones.
  - Two gaps, each with its own check: (1) the prior (what the answers fall back to) and (2) the domain (Morgan renders
    against real recorded amps; the measure DI caps even the truth at about 0.55 of S's distance, step 9).
  - The roadmap's long-run observation, that in-distribution gains never carried over, is now located: even a perfect
    separator would not carry the skill to real songs with this training data.
- **Caveats.**
  - 11 parts in 7 bands.
  - The amp track as input is not what the product gets (a song). It is the best case for the input, used here to
    isolate transfer.
- **References.** `PF/vreal/report-p4.json`, `PF/vreal/answers/{P4-P2a-best,P4-P2a-best-pulled,P4-P2a-best-constant,
  S,S-prime}.json`, `PF/vreal/judge/*/`; `cmd_p4_predict`, `cmd_vreal_comparators`, `cmd_vreal_render`,
  `cmd_vreal_report`; ledger `phase_4`, `phase_4_revised`; `logs/pf-p4-*.log`.

### F21. Dropout and darkening augmentation does not help the clean input; it costs a little (step 18, alone)
- **Result.** P2a-dd is the recipe with D_stem's dropouts and darkening (p 0.3 each) on the clean input (seed
  20261042, best checkpoint epoch 25 of 60, 10.3 min). By knob it reads the same as P2a: NS −0.0087 [−0.0110,
  −0.0063] against −0.0086, with 19 knobs and 23 switches readable. By sound it is a little less close.
- **Numbers** (by sound).

  | Row | FS | NS |
  |---|---|---|
  | P2a-dd − S | −0.224 [−0.372, −0.077], 6 of 6 better | −0.197 [−0.274, −0.121], 28 of 36 better |
  | P2a − P2a-dd | −0.024 [−0.058, +0.011] | −0.044 [−0.087, −0.001], 25 of 36 better |

- **Reading.** Tested alone on a model that reads, these augmentations do not hide the treble cues badly, but they
  do not help either: they cost about 0.04 on new songs. The ladder's choice of no augmentation stands. Step 18 is
  ruled out as a lever. The merge and separator-failure augmentations are mix-specific and wait for a mix model that
  reads.
- **Caveat.** One seed each.
- **References.** `PF/runs/P2a-dd-20261042.json`, `PF/reads/P2a-dd-best.json`, `PF/sound/judge/P2a-dd-best/`,
  `PF/sound/report-dd.json`.

### F22. Mastering does not affect reading the tone (step 15, alone)
- **Result.** P2a (seed 20261042, NS-best) read its own inputs passed through the mastering compressor with each
  example's own drawn parameters (an RMS compressor, ratio 2–4, then a clip at −1 dBFS), whether or not that example's
  mix was drawn mastered. Its answers sound as close as on the unmastered inputs.
- **Numbers.**

  | Row | FS | NS |
  |---|---|---|
  | P2a − P2a(mastered input) | −0.003 [−0.009, +0.003] | −0.002 [−0.017, +0.013] |
  | P2a(mastered input) − S | −0.245 [−0.377, −0.113], 6 of 6 better | −0.240 [−0.313, −0.166], 30 of 36 better |

- **Reading.** P2a never saw a compressed input, so a loss would have been an upper bound. A null on that upper bound
  rules step 15 out: mastering neither hides the tone nor confuses the model. The compressor here keys on the guitar
  alone, not on a mix.
- **References.** `PF/inputs/*-tgtl-mast.npz`, `PF/sound/judge/P2a-best-mast/`, `PF/sound/report-mastering.json`;
  `mastered_inputs`; ledger `phase_3_isolated` (b).

### F23. On a model that reads, the plain 0.5 switch readout is right; the S-switch rule changes nothing and the near-chance rule hurts (step 27, alone)
- **Result.** P2a's plain answers against two readouts fitted on FS.
  - "sws": the 6 switches R0 did not find readable on FS kept at S's state: SW50R treble boost, compressor release,
    tremolo, delay ping-pong, right room mic, SW50R spring.
  - "nc": F20's near-chance rule, δ = 0.1 chosen by FS switch agreement (0.672); a switch within 0.1 of 0.5 takes the
    constant's majority.
- **Numbers** (NS primary; both are fitted on FS).

  | Row | FS | NS |
  |---|---|---|
  | P2a − P2a(sws) | −0.021 [−0.066, +0.024] | +0.001 [−0.010, +0.011] |
  | P2a − P2a(nc) | −0.024 [−0.110, +0.062] | −0.064 [−0.101, −0.027], 20 of 36 better |
  | P2a(nc) − S | −0.224 [−0.331, −0.117] | −0.177 [−0.253, −0.101] |

- **Reading.** When a model reads, flipping near-chance switches to the pool's majority costs sound (it flipped
  answers the model had right), and keeping its unreadable switches at S changes nothing. D_CC's lost pedals (the
  review's step 27) came from a model that read nothing, not from the 0.5 cut. Step 27: measured, no readout change
  adopted. The near-chance rule (F20's decision C) is not recommended.
- **References.** `PF/sound/judge/{P2a-best-sws,P2a-best-nc}/`, `PF/sound/answers/P2a-best-nc.json` (`nc_fit`),
  `PF/sound/report-{sws,nc}.json`; `switch_rule`, `s_switch_state`; ledger `phase_3_isolated` (c).

### F24. More backing variety recovers about a quarter of the skill the backing takes (the isolated learnability test)
- **Result.** P2b-bk8 is P2b retrained with each training target shown in its own P2b input or in 8 other training
  songs' non-guitar backings, at exactly P2b's levels (14,296 inputs, zero renders; seed 20261042, best checkpoint
  epoch 15 of 60 against P2b's 5). It was read on P2b's own fixed inputs. It sounds reliably closer than P2b on new
  songs.
- **Numbers.**

  | Row | FS (60, 6 bands) | NS (60, 36 sections) |
  |---|---|---|
  | P2b-bk8 − P2b (primary) | −0.081 [−0.195, +0.033], 5 of 6 better | −0.059 [−0.093, −0.025], 25 of 36 better |
  | P2b-bk8 − S | −0.051 [−0.216, +0.113] | −0.081 [−0.162, +0.001], 21 of 36 better |
  | P2a − P2b-bk8 | −0.197 [−0.280, −0.113] | −0.161 [−0.215, −0.106] |

  By knob, NS −0.0004 against P2b's +0.0010 (13 switches readable against 5); FS −0.0023 [−0.0037, −0.0009].
- **Reading.**
  - Share of P2a − P2b recovered on NS: 0.059 of 0.220, about 27%.
  - Part of the loss in the mix is learnability: more backing variety helps, and it stops the early overfitting.
  - Most remains. Backings from the same 8 songs, with the same 27 DIs, do not restore it, so it is undecided
    between masking and too few performances and backings.
  - The fix direction this supports: far more backing variety (other songs' and sessions' stems, zero renders) and
    more performances.
- **Caveats.** One seed. The other-song backings are not in time or key with the performance.
- **References.** `PF/inputs/*-mixb-k*.npz`, `PF/inputs/backings-levels.json`, `PF/inputs/backings-pool.json`,
  `PF/runs/P2b-bk8-20261042.json`, `PF/sound/judge/P2b-bk8-best/`, `PF/sound/report-backings.json`;
  `cmd_build_backings`, `BackingData`; ledger `phase_3_backings`.

### F25. On the clean input, more of the same data sharpens the knobs but adds little sound (step 4, alone)
- **Result.** P2a was trained at 25% and 50% of its training examples (nested within sections) and at 100%, each with
  both seeds and the answers pooled. Read by knob, skill climbs steeply with size; by sound, most of the gain over S is
  already there at 25%.
- **Numbers.**

  | Size | Training examples | NS by knob, E − constant (seed 1) | Switches readable (NS) | By sound, − S, NS (pooled) | By sound, − S, FS (pooled) |
  |---|---|---|---|---|---|
  | 25% | 447 | −0.0006 [−0.0023, +0.0011] | 15 | −0.193 [−0.275, −0.111] | −0.223 [−0.405, −0.041] |
  | 50% | about 894 | −0.0049 [−0.0067, −0.0031] | 23 | −0.205 [−0.290, −0.120] | −0.100 [−0.217, +0.018] |
  | 100% | 1,787 | −0.0086 [−0.0106, −0.0066] | 27 | −0.237 [−0.313, −0.161] | −0.195 [−0.321, −0.069] |

  - Steps by sound on NS (pooled, paired): 25% → 50% −0.012 [−0.068, +0.044]; 50% → 100% −0.031 [−0.080, +0.017].
  - The fewer-performances point, 50% of the sections with all their examples (905, one seed): NS by knob −0.0061, by
    sound −0.201 [−0.284, −0.117]. That is at least as good as 50% of the examples over every section; one seed.
  - Single seeds swing (seed 1 alone: 25% −0.198, 50% −0.117, 100% −0.241 on NS), so only the pooled points are read.
- **Reading.**
  - With the clean input, size improves the knob read a lot and the sound a little, leaning but undecided at this
    sample.
  - The sound gain comes early, from what little data teaches (the main switches and gains). Scaling the same kind of
    data is not the lever for the clean input's sound.
  - For the mix, variety mattered more (F24): more backings recovered about 27% with no new targets.
  - Step 4: limit, measured. F20's re-plan (scale) is not supported as the next step by itself.
- **Caveats.** In distribution only; 60 + 60 sample; FS has 6 bands.
- **References.** `PF/runs/P2a-{f25,f50,s50}-2026104{2,3}.json`, `PF/reads/P2a-{f25,f50,s50}-best.json`,
  `PF/sound/judge/P2a-*-x20261042+20261043/`, `PF/sound/report-{curve,curve-pooled,s50,seedcheck}.json`; ledger
  `phase_3_isolated` (e).

### F26. P4's penalty is the core tone, not the wet time effects (P4 dry, isolating F20)
- **Result.** P4's answers and its constant were re-rendered with the time-effect and spring family at S's values
  (198 renders). Drying them changes nothing: the model's core tone (amp, gain, EQ, cab, pedals) is what sits far
  from the real parts, and the model still adds nothing over its own average.
- **Numbers.**

  | Row | All (7 bands) | Clean | Crunch |
  |---|---|---|---|
  | P4-dry − S | +0.156 [+0.016, +0.296], 2 of 7 better | −0.023 | +0.228 |
  | constant-dry − S | +0.137 [+0.019, +0.255], 2 of 7 better | +0.054 | +0.170 |
  | P4-dry − constant-dry | +0.019 [−0.051, +0.089], 3 of 7 better | −0.077 | +0.058 |
  | P4 − P4-dry | −0.003 [−0.049, +0.043] | +0.051 | −0.024 |

  - P4-dry − S per part: Colour Me Red ElecGtr02 −0.263, Signs ElecGtr3 −0.021, Colour Me Red ElecGtr03 −0.006; the
    rest +0.159 to +0.431.
  - Leave one band out: +0.110 to +0.204.
  - The S positive control passed again.
- **Reading.** F20's penalty is not the training prior's wetness (unlike D_F5's on V-real, step 34). It is the core
  tone, mostly on crunch, and the model does not move its answers toward the real parts.
- **References.** `PF/vreal/report-p4-dry.json`, `PF/vreal/answers/P4-P2a-best-{dry,constant-dry}.json`; ledger
  `phase_4_dry`.

### F27. The presets that suit these real parts sit at the training prior's edges more often than its own labels do (zero renders)
- **Result.** Arm A's true-DI search found, for V-real-10's parts, presets that beat S (−0.137 shrunk, −0.192 best;
  review step 38). Their searched controls were placed within the training labels' distribution (same amp and section
  class, the controls that sound).
- **Numbers.** Share of values outside the training labels' 5–95% range:

  | Set | Share outside | Below 5% | Above 95% |
  |---|---|---|---|
  | The search's best presets (550 values) | 0.30 | 0.20 | 0.10 |
  | NS labels, the reference (3,289 values) | 0.12 | 0.07 | 0.05 |
  | S presets (58 values) | 0.05 | 0.05 | 0.00 |

  Per control, most often outside: right cab position 0.66, left cab distance 0.52, PR12 bass 0.50 (median percentile
  0.08), SW50R mid 0.45 (0.18), left cab position 0.43, right cab distance 0.32, input gain 0.25, AC20 power 0.25.
- **Reading.** Real parts often want settings at or beyond the edges of what the model was trained on (low bass and
  mids, unusual cab placement). This compounds the domain gap: F26 shows the model does not read the real recordings
  at all, and even if it did, the targets lie where training is thin.
- **Caveats.** The search's "best" is one 52-render search per half and can sit on controls the sound barely
  constrains (cab placement); the shrunk version, halfway to S, is the robust one. These are descriptive, post hoc.
- **References.** `~/ndsp-presets/learn/arm-a-mega53/F-perfect-sep/ZT/*/*/{A,B}.json` (`settings.best`), the
  ladder's training labels; computed in this session (zero renders).

### F9. Process: removing a worktree crashed running jobs
- **Result.** Removing the plan's worktree while the doubles render ran from it crashed its 3 shards at a lazy
  import. They resumed from their saved sections with no data lost.
- **Changes.** Long jobs run from the main checkout (a memory note records the rule).

## Budget

- **Renders:** about 3,600 for phase 1b (2,612 used); about 2,200 for P2's by-sound read; about 1,600 for phase 4
  (P4: 438); about 1,000 for D_fix's reads; and, added 2026-10-31 under the isolation rule, about 2,880 for the
  isolated tests on P2a and the backing-variety test. About 11,700 in all, roughly 5 h of render time at
  3 processes.
- **MPS:** about 12 h at a 100-epoch cap (P1, the ladder with second seeds where needed, P2d-aug, 6 curve points,
  10 k-fold runs, D_fix). A cap from P1 that goes past it comes back to the user.
- **Disk:** P2's inputs about 0.3 GB; phase 1b's audio and features about 1.2 GB; the 31 GB guard holds.
- Every render: isolate=True, a discarded priming render, 0.25 s trimmed, at most 3 render processes,
  `setopt no_bg_nice`. V-real is read only in P5's stored distances, phase 4 and D_fix's declared read.

## Review (2026-10-31)

An independent review approved with 12 required changes, all made above:
1. the rungs now differ only in their input (level, augmentation, examples, P2b's construction);
2. every DT double counts as dirty (the doubles are re-rendered), and P7 is dropped;
3. NS's intervals are section-clustered with the caveat, and new songs are read by k-fold over all bands;
4. P3 is a measurement, the S fallback a decision for the user;
5. `cls` replaces `base` in every consumer, with its consequence stated;
6. the budget is re-costed;
7. each closure is reachable in this plan, or named as a limit or a decision;
8. paired locating rows;
9. a fixed cap with checkpoints, and the baseline declared;
10. curves on the stem too, and a fewer-performances point;
11. V-real inputs per rung, and the amp mismatch;
12. D_fix is chosen without V-real.

**Re-review (2026-10-31)** of the revision and its code: approve with 4 required changes, all made: phase 1b's
positive control replays the original job order; P2b of a doubled example uses its new mix's backing gain; the
by-sound read gets a "truth" positive control; the bookkeeping (P5 and P6 entered, the ledger's held-out and band
lines). It audited P5 and P6 and agrees with their readings.

Its optional points are folded in: the lean order, P6's FS half only, a sample that grows on evidence, one
Wickerman weighting for P3 and P4, the runaway list named, the by-sound protocol, step 23's unfinished second fix,
the product's ownership and PR #345's decisions.
