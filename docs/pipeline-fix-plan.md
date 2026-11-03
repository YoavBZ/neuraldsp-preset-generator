# Fixing the pipeline review's findings (plan, 2026-10-31)

**Status (2026-11-03):** declared and reviewed (the plan, its revision, phase 4, the isolated tests and 5B.2, each
with required changes, all made). Phases 1–4, the isolated tests and phase 5's tests (5A, 5B.1, 5B.1b, and 5B.2's
stage 1, arm P, Rc and arm R, its stage 2 and its recording oracle) have run; the findings log (F1–F36) holds
every result, audited. 5B.1c was withdrawn before any render. Declared next, at the user's choice of more real
recordings: 5C, many recordings from GOAT's capture renders (pilot), has run (F37): the model learns a per-track
reading in domain (better than the matched centre and than its shuffled-label control on held recordings), not
shown on BKS's real reamps. 5D, a real-amp panel across 7 bands (F38, a strong hint): the per-track reading is not
shown there, and a centre from GOAT's many capture labels leans better than S across the bands (descriptive); the
user's choice between domain work and more real chains stays open. D_fix (F39): its real rows, a quarter of each
epoch, cost the plugin read (FS and NS worse than P2b-wide24), so it is not built as is. Its amendment (F40): at a
third of that share the plugin read is still lost; at a tenth it is not shown worse (FS leans worse at every amp),
but BKS's real amps read about where P2a, a model without real rows, does (+0.207 against Rcs2), so D_p is not built as is either and V-real waits: no share in this joint
recipe gives the real-amp gain without the plugin cost. At the user's direction (the product always reads real
amps) D_fix itself was read on V-real with the plugin read as a cost beside (F41): it reads level with S on held-out
real songs (+0.036, undecided) and clearly better than the same recipe without real rows (−0.192, 7 of 7 bands),
which reads clearly worse than S (+0.228); level with a real-amp centre, so no per-track reading is shown. Proposed
next: domain work (a per-row input saying plugin render or real amp); the user's choice stays open. At the user's
suggestion FT (F42) used the plugin renders as pretraining and tuned on the real rows alone: better than D_fix on
real reamps (BKS −0.055), level with S, D_fix and RcG on held-out real songs (FT − S +0.022, undecided). Proposed
next: the per-recording reading on many more real-amp recordings and a fresh real-song test; the user's choice.
About 80% of FT's lead over S on real reamps is its drive (F43). At the user's question whether the score weighs each
kind of change as the ear does, a blind page (F44) found it does not: treble counts well above the ear, drive above
it, reverb below it. On headphones (F45) it holds and grows: every large effect re-heard is heard clearly or very,
the treble steps are not. Next, before more recordings are scored: a revised judge with a term for what time
effects add and less weight on steady treble, declared, reviewed and checked on a fresh blind page. Its first, zero-render stage (F46): steady 6 dB tilts are barely heard on
this page, and neither revision removes a within-preset inversion (loudness-weighted bands; J2 ran without its
decay part, which finds no note end on this DI, so the decay idea is untested), so neither is built. The user: the
product must reach the most accurate preset with no human in the loop, so the judge cannot keep that limit; a strong
go-ahead for a combined, automatic judge. Declared next: J5, the judge plus a carry-over part for what time effects
add (in-sample it removes most effect inversions, not the treble steps), checked on a fresh blind page with a
chord DI and two other presets.
The fresh page (F47): J5 ranks it worse than J0 (−0.224 [−0.351, −0.063]): on strummed chords the effects were
barely heard, and J0 already ranks that page well (+0.863), so J5 is not adopted and J0 stays; effects follow
song research. Next: the approved real-amp recordings and a fresh real-song test, scored with J0.
Findings F1–F47.

**Why.** The user (2026-10-31): "Start with the review, reevaluate our entire plan/roadmap and make sure we go
over each finding the review found, fully understand it, fix it and verify its fixed. Be organized, go step by
step and make sure no issues are opened in the end. We must fix what's blocked us from making the ML efforts
work." That asks for the [pipeline review](ml-pipeline-review.md)'s tests P1–P7 to run and each finding to be
fixed. Each phase is still entered in the ledger (`pipeline-fix`) before it runs, and each result is audited
before it is written up.

## The roadmap, re-evaluated

- **What the record shows.** Across every direct-model build (part C, the stems pilot, D_F5, D_CC), gains in
  distribution never carried over to real songs, and no build beat S on V-real. The review then found that D_F5
  reads almost nothing even on its own made-up songs (step 29). The next build (the F20 build, more data) would scale a
  pipeline that is not yet shown to learn.
- **The order changes:**
  1. Make the yardstick fair: S's home advantage (P5), Wickerman's duplicate input (step 32), render-order noise
     (step 33).
  2. Fix the training data that is wrong: the DT doubles (step 12) and the runaway targets (step 6).
  3. Find the failing step: P1 (can the network learn at all?), then P2's ladder of inputs (clean target, target in
     its backing, the full mix, the stem), read by knob and by sound, on new settings and on new songs.
  4. Fix what the ladder locates and train one model with every adopted fix (D_fix), chosen on the training pool's
     own reads, never on V-real.
  5. Read D_fix on V-real. Scale (the F20 build) only if the learning curves say size is the lever.
- **The F20 build's draft (PR #345; not finding F20 below) is folded in here** and closed as superseded when this plan merges:
  - its step 0 (a size curve) becomes P2's learning curves, on the clean input and on the stem;
  - its decisions A (the order) and B (the F20 build on the evidence) become this plan's order and phase 5;
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
  21% closer than S on 2 held-out songs (P2a, F11);
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
| 12 | Doubles with the full setting | Data checks: the positive control (46 of 46 exact); every re-rendered double carries its target's exact label and amp (980 of 980); every other guitar unchanged (1,222 of 1,222); the new mixes rebuilt exactly (F16) | nothing | fix verified on the data (F16); enters D_fix |
| 13 | Stand-ins | Not an error; their share is a data measurement | nothing | ruled out (as an error) |
| 14 | Ratio prior | Data measurement; level statistics only | nothing | limit, measured |
| 15 | Mastering | P2a reads its own NS inputs mastered with each example's draw against unmastered, by sound (zero training) | P2a, by-sound read | ruled out (F22) |
| 16, 19 | Where the tone is lost | The ladder: every rung on the verified recipe; located at the mix (F15) | recipe, by-sound read | open, located at the backing (F15, F17) |
| 16 | The fix for the mix | Phase 5's fix, trained on the verified recipe and read against P2b and P2c on the same examples | recipe, by-sound read | phase 5 (backing variety recovers 27%, F24) |
| 18 | Augmentation | P2a with dropouts and darkening against P2a, by sound. Merge and separator failure are mix-specific and are tested only once a mix model reads | recipe, by-sound read | not shown to help the clean input in distribution; song-fed untested (F21) |
| 20 | Network | P1 | nothing | ruled out (F5) |
| 21 | Loss in knob units | P2a by sound against by knob | P2a, by-sound read | ruled out as a blocker; reads are by sound (F11) |
| 22 | Length | P1, P2a's checkpoints | nothing | fixed |
| 24 | Logs | A test; P1 | nothing | fixed |
| 26 | Pull toward the average | On P2a in distribution, by sound (F12) | P2a, by-sound read | ruled out as the blocker (F12) |
| 27 | Near-chance switches | On P2a in distribution, by sound: unreadable switches at S, and the near-chance rule, against the plain readout | P2a, by-sound read | for a model that reads, in distribution: plain readout right; near-chance rule hurts (F23) |
| 29, 30 | Reads almost nothing | The ladder, by knob and by sound | recipe, by-sound read | 29 open, located (F13–F17, F20); 30 fixed (F10) |
| 31, 35 | V-real's size | Limit; the rows' Wickerman rule unit-tested | nothing | limit, measured |
| 32 | Wickerman's shared input | Unit test of the rows; P4 reads their own amp tracks | nothing | fixed (test) |
| 33 | Render-order noise | Fresh primed processes reproduce the truth (F10); in phase 4 every fresh S render must sit within 0.005 (log) of the label table's stored distance on stage F's parts, or the read stops | nothing | fixed |
| 36 | S's home advantage | Stored distances (P5) | nothing | limit, measured (F1, F20) |
| 37 | The average against S | In distribution, the constant against S by sound (F11: even) | by-sound read | limit, measured (F11, F20, F26) |
| (P4) | Transfer to real recordings | First, alone: P2a told a wrong amp and rendered on it, by sound on NS (the amp mismatch, without real recordings): it keeps most of its skill (F19). Then P4 on V-real's amp tracks: no transfer detected, +0.153 against S, not shown better than its own constant (F20) | P2a, by-sound read | measured: a second blocker (F20) |

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
| 4 | 2,699 examples from 10 songs | Learning curves on P2a and P2d (settings per performance, and performances); the F20 build is the next plan if they rise | the curves | Limit, measured |
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

*2026-10-31, superseded in part by the isolation rule (above):* P2d-aug and the curves on P2d were not run (a model
that reads little cannot test augmentation or size); augmentation and size were tested on P2a (F21, F25). The ladder
ran on the examples without DT doubles (F8).

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
     settings per performance, the F20 build's lever), and 50% of the sections with all their examples (fewer performances);
   - new songs by k-fold: the 10 songs in 5 folds by band (BKS's two songs together), P2a and P2d, one seed, the
     ladder's length, read by knob on every held-out song (band-clustered, 9 bands);
   - zero-render splits of the by-knob error: by draw mode (step 7) and by mastered (step 15).
- **Reading:** the rung whose locating row carries the loss is the failing step. If P2a has no skill, the problem
  is the model, labels or loss (steps 20–24), not the input.
- **An easier task than V-real:** on FS and NS the model is told the true amp, and the answer is rendered on it. On
  V-real no Morgan amp is the real one. Phase 5's by-sound read with the amp mismatched measures that gap.

### Phase 4: P3 and P4 on V-real (measurements)

*2026-10-31:* P3 on D_CC was dropped under the isolation rule (a readout test on a model that reads little shows
nothing); the readouts were tested on P2a in distribution (F12, F23) and as P4's pulled row (F20). P4 ran (F20), then
its dry readout (F26).

- **P3, fall back to S (steps 26, 27, 37), a measurement only.** The user ruled on 2026-10-27 that writing S for
  unreadable controls is a measurement, not the method. For D_CC and for the ladder's best rung that a song can
  feed (P2c or P2d):
  - the plain readout;
  - knobs pulled toward S, and a switch whose head did not read on FS and NS kept at S;
  - the near-chance rule (the F20 build's decision C): a switch within δ of 0.5 takes its pool's majority, δ set on FS.
- **P4, real guitar input (steps 9, 11, 32).** P2a's model reads V-real's own amp tracks at the training median
  loudness: does learning from Morgan renders carry over to real recordings?
- **Inputs on V-real:** P2c reads the crop's raw mix, P2d its stored stem, P2a the amp track (P4). P2b has no input
  on a real song and is not read there.
- Every answer, and every comparator (S, the `cls` constant, D_CC's plain answer), is rendered in its own primed
  process (step 33), since the stored comparators were rendered in shared processes. Wickerman ElecGtr2 and 3 count
  as one input in both P3 and P4. Band-weighted, 90% band-clustered t (7 bands), part-weighted beside.

### Phase 5: the located fix, D_fix, and scale

*2026-10-31, the session's recommendation on community presets, pending the user's yes* (the user's question via the
research session: "What do you think about downloading a bundle of community presets and use them for training
instead of generating unrealistic presets our own?"):
- **Recommended: as centres for the next build's draws, not as the only labels**, alongside a smaller wide share for
  coverage (every control is learned). Time effects are dried where the presets are wet (factory-centred draws are 73%
  reverb on).
- **Why:**
  - F27: the presets that suit real parts sit at the training prior's edges about 3× as often as its own labels
    (0.27–0.35 against 0.09).
  - F26: on real recordings the penalty is mainly the core tone.
  - Realistic centres may improve coverage where real tones sit. That is untested: F27 shows where real parts' presets
    sit, not that community presets sit there. A zero-render check first: place a community bundle against F27's
    search presets with the same percentile rule.
  - They would also be expected to cut step 7's refusals (s07: the refusals are mostly wide draws). The runaway
    targets are unchecked.
- **What it does not fix:** F20, that the model is not shown to read real recordings (the clean parts lean better,
  −0.126, the crunch parts not). A realistic prior also lifts scores through the fallback even when nothing is read.
  So it is read only against a model with the same prior, by sound, and only after the two blocker tests below.
- **Supply and rules** (as reported by the research session, not verified here):
  - Community presets for Morgan Amps Suite are few (tens to hundreds; no bulk library found).
  - Morgan Amps Suite X (2026-10-28, free) adds 100+ curated presets. Updating the plugin needs the user's yes and a
    parity check first: re-render stored settings and compare bit for bit, as the positive controls do.
  - Community presets' licences are the user's to check; paid packs need the user's yes.
  - "Song tone" presets (a person's attempt at a record) could serve as a yardstick, not as ground truth.
- **When:** with the next data build, after the two blocker tests.
- **The user's decision (2026-10-31, "Sounds good" to the session's suggestion):**
  - Community presets: yes, as centres for the next build's draws, a wide share of random draws kept, effects
    dried, after a zero-render check that they sit nearer real tones (F27's rule). Each download is still asked for
    with its file, source and size; licences stay the user's to check, paid packs need the user's yes.
  - Morgan Amps Suite X: yes, after 5B.2. Update, then re-render stored settings and compare bit for bit; its
    presets are used only if that parity check passes, otherwise the update is held.
  - The sources (research PR #349, `docs/research/morgan-community-presets-2026-10.md`): outside the plugin's own
    108 factory and artist presets, which the draws already centre on, the pool is small: about 15 per pack,
    mostly paid, and the only free pack with clear terms (Omega Station, 14) is doom, outside the clean/crunch
    scope. Nothing is downloaded for now; Suite X's bank ("more than 100 curated presets") is the larger source.
    Two cautions kept: a community pack must never sit in the plugin's non-User preset folder, which the menus
    read as factory, and if Suite X installs as a separate plugin, the hard-coded preset paths and the pack identity
    need updating (builds already stop when `plugin_version` changes, `learn/pretrain_set.py:709–711`).
  - Suite X installed by the user (2026-10-31), beside the old plugin rather than over it: a separate AU
    (subtype `MASX`, 1.0.0) next to the one every render loads (`NMAS`, 1.1.1, unchanged since May 2025), so stored
    renders and 5B.2 are unaffected and no parity check is needed while the renders stay on `NMAS`. Its bank is
    the same 133 files (108 factory and artist, 25 user) under the same names, re-saved in a `morgan-x 0.1.0`
    format: every stored value matches; the only change is five new cab keys (stereo cabs, custom-IR flags). It
    brings no new tones for the draws. Tone King Imperial MKII X also installed; not used by the pipeline.
    The product session's probes (no audio): X declares the old preset id as its legacy id and exposes the same
    157 controls at the same defaults as `NMAS`. That suggests renders carry over, but is not a sound check:
    moving the renders to X would still need the bit-exact parity check first.

*2026-10-31, after the user's "Continue":* the two blocker tests run, each declared and reviewed first.
- **5A, backing variety at scale (blocker 1; ledger `phase_5a`; zero renders).**
  - P2b retrained with 24 backings per training target, drawn session-first from the training songs' sections and
    from up to 20 active windows of each other session whose stems were heard clean. V-real's bands and the NS
    songs are kept out.
  - Stems: an extra session gives only its heard-clean session-wide list. The training sections keep P2b's own
    stems, as P2b-bk8 does, which may carry that song's other guitars.
  - Built exactly as P2b-bk8's variants, and read on P2b's own fixed inputs against P2b-bk8 and P2b.
  - Caveats: variants and sessions both grow; the own input is shown 1 epoch in 25, not 1 in 9; about two-thirds of
    draws come from new sessions; some extra backings are thin. One seed, NS-best: a difference under about 0.09 by
    sound is within one run's spread.
  - *Review (2026-10-31):* approved with required changes, all made. The first stem rule let guitar-bleed stems in
    (it was the loosest, not the strictest); fixed to the heard list. Also adopted: windows from −33 LUFS (the
    training backings' range), at least 2 non-vocal stems, a pool hash in every variant, a draw test.
- **5B, real recordings (blocker 2), designed next and reviewed on its own.** Pseudo-labels for the ladder's
  training sections from arm A's true-DI search against each DI's own recorded amp track. The clean-input model is
  then trained on the real amp tracks with those labels, and P4 is re-read on V-real.

*2026-10-31, after 5A's first seed (F29) and the bleed finding (F30):*
- **5A seed 2 (ledger `phase_5a_seed2`).** P2b-wide24 with seed 20261043 on the same build, read the same way
  (240 renders, about 10 minutes of MPS). Rows per seed, and pooled as each example's mean of the two seeds' paired
  log ratios (no ensemble render: an ensemble would also move the rows, by up to about 0.09 in the stored reads).
  F29's NS row is confirmed or not by it.
- **5B.1, transfer to real amps on reamped tracks (ledger `phase_5b1`, about 960 renders).**
  - Units: (section, reamped track) for every ladder training or FS section whose DI has a reamped track (BKS, both
    songs: 105 units, 14 rigs); 40 read, round-robin over the rigs.
  - P2a (both seeds, NS-best) reads each reamped track at its training inputs' median loudness, per forced amp and
    search half; judged by sound on the held half against S and the constant, with each unit's lag estimated from
    its three S renders (`estimate_lag`). Clustered by DI (8 performances in the draw; rigs sharing a DI share
    sections and S renders), by rig beside.
  - Isolation: no bleed check is relied on (bleed-free by construction); the performance is seen in training, so
    this reads real-amp sound alone, apart from new playing (which V-real covers, F20).
  - Reading: P2a better than S here says the clean-input model transfers to real amps on known playing, so F20's
    gap sits in new performances or the V-real recordings. 38 of 40 units are training sections whose DI P2a saw
    rendered by the plugin, so a gain is an upper bound for transfer. No gain says the gap already appears on a
    real-amp recording of known playing (the amp, mic, room and cab chain, the reamps' noise or tails and the judge
    on real recordings not separated), and 5B.2 (pseudo-labels on reamped tracks) is the next fix.
  - Caveats: one band (BKS, 2 songs); 14 rigs on 8 DIs; the reamp chain (a real amp and mic) differs from a mixed
    record; many reamps keep energy where their DI is more than 40 dB down (about −10 to −22 dB), likely amp noise
    or tails.
- **5B.1b, the model's deviations around S (ledger `phase_5b1b`, 480 renders; after F31).** The same P2a answers
  on the same 40 units, with each continuous control at S's value plus P2a's deviation from its labels' constant
  (switches and mics at S's). Exploratory: a readout tried after seeing F31.
  - The review found the move from S is mostly one shift shared by every track of an amp and class (per-track
    remainder near the gap between a track's two halves). So a control is read too: S-shift, S plus that shared
    shift taken from the other DIs' units (240 renders; 720 in all).
  - Rows: S-shift − S (does the shared shift help?) and P2a-Sc − S-shift (does per-track skill transfer?); P2a-Sc −
    S beside. P2a-Sc − P2a is not a skill read. Ties are not evidence of no transfer.
- **5B.1c, the S-centred readout on V-real (ledger `phase_5b1c`): withdrawn before any render.** Declared as a
  measurement; the review found its outcome largely predictable from stored reads (P4 − constant −0.017 [−0.090,
  +0.057] on V-real; on BKS P2a − constant ≈ P2a-Sc − S), so on 7 bands it would very likely be undecided while
  spending a V-real exposure. Its answers were computed (the model run on V-real's inputs, zero renders, nothing
  judged). Whether D_fix uses an S-centred readout is decided from F32 and FS/NS only, and V-real is left for D_fix.

*2026-10-31, after F32 and the user's question (are random training settings unrealistic?):*
- **5B.2, labels that reach real-amp tones (ledger `phase_5b2`; about 8,760 renders first, up to about 21,200 if
  every conditional step runs).** Question: trained with labels from a true-DI search on other performances' real
  amp tracks, does the clean-input model read held-out real amp tracks better than S? (Held out are the tracks, not
  the playing: 38 of 40 read units' sections were trained on as plugin renders.) Beside it, arm P (the user's
  question): trained only on draws centred on presets (factory and S), without the uniform "wide" draws, does it?
  - **Stage 1, the ceiling, run first (6,840 renders).** On 5B.1's 40 units, per forced amp (120 directions):
    arm A's main stage (`K.space`: input gain, the amp's knobs and switches, both mics; 52 evaluations, seed
    20261013) from the class's S, with the true DI, against the reamped track. Objective: the judge's distance on the
    search half at the unit's stored lag (5B.1's `real/lags/`), every render over the full section as 5B.1. The
    search half alternates by unit within each DI. Each direction runs in its own process after one priming render
    of S, so its first evaluation (S) sits where 5B.1's fresh S render sat: it must be bit-identical to it, or the
    stage stops. The best setting and the setting shrunk 0.5 toward S are each rendered fresh (5B.1's way) and
    judged; the held half is the read (57 renders per direction). The best's in-process held value is kept beside,
    to check that in-process values match fresh ones.
    - **Stop rule:** on the unshrunk best's held − S row by DI. If its interval lies wholly at or above 0, no setting
      in this search space beats S on these tracks, so this search's labels cannot help (`K.space` has no EQ,
      pedals or effects): arm R stops and the gap is put to the chain, the judge or the unsearched controls. An
      undecided or better row continues. Arm P runs either way.
  - **Labels.** Each direction's best setting, unshrunk (arm A's ZT found shrinking hurts with true inputs), as a
    full setting: searched controls from the search, every other from S (`F.label_of`). A direction whose best
    falls back (silent or non-finite) gives no label.
  - **Arm R, on stage 1's labels first (8 trainings, 720 renders).**
    - Training: P2a's recipe (rung a, same epochs, checkpoint rule and seeds) with real rows added. Rows are the
      labelled (unit, amp) of the other folds' DIs, cycled to 300 per epoch in every fold (about 14% of an epoch,
      each row 3–4 times), with input the reamped section's features as 5B.1 built them (training inputs' median
      loudness) and the section's class.
    - Folds: four by DI, the 8 DIs in pairs making the folds' read-unit counts most equal (10, 9, 13, 8; seed
      20261039 for ties). A fold's models never see their own DIs' real tracks. Fold 2 is all crunch and fold 3 all
      clean (stated, not balanced).
    - Rc, the control for the centre (240 renders): S moved by the mean unit deviation of exactly the labels that
      unit's fold model trained on (same amp and class), switches and mics at their most common value.
    - Read: R (both seeds as an ensemble, as 5B.1's P2a) per forced amp and search half (480 renders), judged as
      5B.1.
    - Rows: R − Rc (does it read real tones per track? primary), Rc − S (does a real-amp centre help?), R − S,
      R − P2a, and R − P2a-Sc from stored judges (do the renders beat the free S-centred readout?).
    - Reported by DI (8) with a 4-cluster fold interval beside (a fold's two DIs share models and their training
      noise), per fold, by rig, DI 19 (Bulldozer clean, whose fold trains on Too Much's clean rows only) apart, and
      R's share of the ceiling paired on its directions.
    - Zero-render reads beside: each fold's head losses on its own DIs' real labels, R against P2a, per seed; and
      NS and FS head losses against P2a's as the guard for plugin skill.
  - **Stage 2, only if R − Rc is undecided (about 11,450 renders).** The same search on the other 65 units: 390
    renders for S and the lag (three fresh S renders, as 5B.1; a unit with no lag gets no label), then 53 per
    direction with no fresh renders (labels only, the best's in-process render), checked on stage 1's fresh against
    in-process values. Then Rc and R retrained and read on stages 1 and 2's labels (720 renders). Stage 2 adds
    mostly Bulldozer crunch (59 of 65 units) and nothing for DIs 20 and 24.
    - *Amendment (2026-11-01, after stage 2's search, before any of its labels is used):* a unit whose lag is more
      than 14 samples (0.3 ms, the agreement `estimate_lag` reports for pooled renders) from the median lag of its
      recording's windows gives no label (`lag_refused`): either the estimate locked onto another peak or the
      track's alignment changes within that window, so its lag, and the search aimed by it, is not trusted. Stage
      1's 40 units all sit within 3 samples, so nothing read so far changes. Three stage 2 units are refused (9
      labels): Bulldozer 36 Reamp1 at 200 s (−21 against the recording's −56/−57) and 205 s (−94), and Too Much 16
      Reamp1 at 205 s (498 against 91–96). The review found the raw DI against Bulldozer 36 Reamp1 steady from 196
      to 207 s and about 35 samples away from 208 s on, so that track may step in alignment near 208 s; Too Much 16's
      shows no step, so its 498 is an estimator error. Any tolerance from 3 to 35 samples refuses the same three.
      Stage 2 keeps 62 units (186 labels); stages 1 and 2 give 306.
      - *Review (2026-11-01, independent):* approved with one required change, made: the reason above, which first
        said only "another peak". Noted for the write-up: 20 of stage 2's 65 pr12 labels (and 10 of stage 1's 40,
        already in Rc and R) put the amp's Volume at its floor, with best renders peaking at −37 to −59 dBFS. The
        judge compares level-normalised sound, so these are valid answers to its question but unusable as presets
        as they stand; output level is a product step D_fix has to settle.
  - **Recording oracle, RigO (declared 2026-11-01 after stage 2's read, F35, before any of its renders; ledger
    `phase_5b2_rigo`; 432 renders).** Question: do the labels' per-recording differences show by sound beyond the
    centre? Arm R read no further than Rc on either stage, yet in setting space (a post-hoc look) the labels of a
    unit's own recording sit nearer its label than Rc does (F35). This bounds what any per-track reading of these
    labels can add, so it says whether the next fix goes to the model's reading or to the labels.
    - Answers (zero renders): per read unit and amp, Rc's rule (`rc_setting`) on the labels of the same recording
      (rig) and amp, stages 1 and 2, lag-trusted, from windows whose sections do not overlap the unit's (starts at
      least 10 s apart; sections are 10 s and start 5 s apart, so a neighbour's search half can hold this unit's
      held half). 108 of 120 directions (36 units): DI 20's two recordings have no clear window, so DI 20 drops out
      (7 DIs). Labels per answer by DI: 24 one, 16 two to four, 19 three, 36 three to five, 22 nine to ten, 28 and
      31 fourteen to sixteen (mean 6.4); each DI weighs equally, so 4 of 7 clusters rest on 5 labels or fewer.
    - Count-matched control, RcM (zero renders to make): on each RigO direction, Rc's rule on as many labels as
      RigO used, drawn at random (seed 20261046 per direction) from Rcs2's pool for that unit (the other folds'
      DIs, same amp and class). It tells per-recording information from a smaller, noisier centre.
    - Read as 5B.1 (one render per answer, judged on both halves): RigO 216 renders, RcM 216.
    - Rows, on RigO's 108 directions (`real-report --within RigO`): RigO − Rcs2 (primary), RigO − RcM
      (count-matched), RigO − S; beside, P2a-reals2 − Rcs2 on the same directions, read by 5B.2's DI-and-fold rule
      and descriptive only. The subset drops DI 20, where the centre is worse than S (Rcs2 − S +0.091), so it
      favours the centre: on these directions Rcs2 − S is −0.194 and P2a-reals2 − Rcs2 +0.042 [+0.006, +0.078] by
      DI ([−0.008, +0.059] by fold), undecided by that rule (zero renders, before any RigO render;
      `PF/real/report-5b2-rigo-pre.json`).
    - Reading, declared now, on the by-DI interval (no models, so no training noise; the fold interval beside,
      since Rcs2's labels are shared within a fold). A descriptive split beside: crunch DIs (22, 28, 31, 36) against
      clean (16, 19, 24), the mean of their per-DI values.
      - RigO − Rcs2 better: the labels' per-recording differences are audible beyond the centre, so a reading of the
        track has headroom; arm R's failure to take it lies with the model (its inputs or training) or with too few
        distinct recordings to learn from (10–11 training rigs per fold): the next fix works on the model's reading
        and on more recordings.
      - Undecided or worse, with RigO − RcM better: per-recording information is audible against an equally noisy
        centre but not yet against the full one; the labels are too few or too noisy per recording, so the next fix
        works on the labels (more evaluations, windows averaged) first.
      - Undecided or worse, with RigO − RcM undecided or worse: those differences do not show by sound at this label
        noise (weak evidence where a DI has 5 labels or fewer); the next fix works on the labels, their search space
        (the unsearched controls) and their evaluations, before the model.
    - Caveats: an oracle (it knows the real amp's answers on the same track; no product can); fewer labels per
      answer than Rc's 13–62, so noisier, which works against it (RcM shares that noise); a recording's other
      windows share the performance and probably the song's chain, so its playing and the song's rig may help as
      well as its amp; it bounds a per-recording reading, not a per-window one.
  - **Arm P (4 trainings, 1,200 renders; up to 960 more).**
    - Training: P2a's recipe on the 1,296 training examples drawn around presets or S (864 factory, 432 start; the
      491 wide draws out). Its size control, P2a-pcsz: in each section as many examples as arm P keeps there, drawn
      at random from all modes (seed 20261045).
    - Read on the 40 units as 5B.1, ensembles: P (480), P2a-pcsz (480), P's labels' constant (240).
    - Rows: P − P2a-pcsz (primary: dropping wide draws beyond size), P − P2a, and P's constant − P2a's constant.
    - Zero-render: FS and NS head losses by the example's draw mode (P, pcsz, P2a); preset-centred examples are
      primary, since a model never shown wide draws loses on them by construction.
    - Only if P − pcsz leans better on the real units: by sound on FS/NS (P and pcsz ensembles against the stored
      P2a ensemble, 480), split by draw mode; and P-Sc (480) to tell its centre from per-track change.
  - **Readings, declared now.** R − Rc is decided when its by-DI and its 4-cluster fold intervals both exclude 0 on
    the same side (a fold's two DIs share models, so the DI interval alone misses training noise); otherwise it is
    undecided. Arm P's rows are decided on the by-DI interval (one pair of models reads every unit; its per-seed head
    losses show training noise beside). The expected detectable size is about 0.05 (F31/F32's by-DI half-widths are
    about 0.035); it is not a bar.
    - R − Rc better: the model learns real-amp sound per track from real labels; real rows (and more bands' reamps)
      enter D_fix's build. Undecided: stage 2 runs. Worse: not adopted. Rc − S better: a real-amp centre is a
      candidate readout for D_fix, weighed with the S-centred one.
    - P − pcsz better on real units: the wide draws hurt real-amp reads; the next build cuts or shrinks their share,
      weighed against the FS/NS cost on preset-centred examples. Tie or worse: no evidence they hurt; the mix stays.
  - Order: stage 1 and arm P together (arm P's trainings on MPS while stage 1 renders); then Rc and arm R; then
    stage 2 if called for. Held out throughout: V-real and the NS songs (BKS is a training band).
  - **Caveats.** One band (BKS), 8 performances, 14 rigs; the physical amps and mics are probably shared across a
    song's DIs, so a held DI is a new real track on possibly familiar chains. Labels are selected on one half (noisy;
    the held half is the honest read). The real rows' share is chosen, not tuned. Arm P reads one band for real
    amps; its FS/NS reads are plugin renders.
  - *Review (2026-10-31, independent, before any render):* approved with required changes, all made. It asked for:
    the Rc control (the labels sit near S on every unsearched control, and F32 showed re-centring alone moves a lot);
    ensembles throughout to match 5B.1's P2a; arm P read against its size control on the real units, and by draw
    mode on FS/NS; the readings declared; the arithmetic corrected (priming and lag renders, real-row counts);
    the code's choices declared (bit-identical S, fresh best, section-matched size control, a seed of its own); and a
    fold interval beside the DI one. Adopted suggestions: stage 1's labels first and stage 2 only if undecided,
    stage 2 without fresh renders, zero-render head reads, a fixed real share per fold, DI 19 apart, the share of the
    ceiling, and the stated power. Its re-check approved with three changes, made: every render sends its edits in
    5B.1's sorted order (so the bit-identical S check compares like with like), stage 2 resumes (S's fresh judge
    and sha saved with the lag), and the decision rule above.
  - *Results review (2026-11-01, PR #351, independent):* approved with required changes, all made. It recomputed
    every number and found no code bug or leakage. It asked for: readings no stronger than their intervals (arm P
    "not shown", the size rows "lean"); the declared P − P2a rows in F33; the ceiling's share by DI (38%) apart from
    its paired share; the ceiling as a mean with its per-unit range; F32's shift described as it was built; the
    setting-space audit stored (`real-setting-audit`); the held-tracks-not-playing caveat; last-digit fixes; and
    tests that a fold's real rows and Rc's labels never come from its own DIs (`fold_records`, `rc_records`).



*2026-11-01, after F36 and the user's choice ("More real recordings"):*
- **5C, many recordings from GOAT's capture renders (ledger `phase_5c`; pilot about 15,600 label renders, about
  2,600 read renders and 1.7 h of MPS).** Question: trained with search labels from many mostly distinct
  amp chains, each with its own DI, does the model learn to read a track per track beyond the centre of its own
  labels, first on held capture recordings (in domain), then on BKS's real reamps (transfer)? F36 put the headroom
  on BKS at up to about 0.15; arm R, learning from 10–11 recordings per fold, took none of it.
  - **Why GOAT.** No open source has 100+ real recorded amp chains with their DI; real-hardware sets total about 15
    chains (`docs/research/real-amp-chains-2026-11.md`, PR #353, and this session's search). GOAT (Zenodo
    15690894, CC BY-NC 4.0, research use on request, granted to the user and downloaded 2026-11-01, md5 checked)
    holds 172 real DI recordings, each rendered through 5 Neural Amp Modeler captures drawn from about 7,000
    profiles of over 1,000 amps, each with a random Archetype Nolly cab IR: 860 recordings whose chain is fixed
    within the recording and mostly distinct across them (about 50 repeated profiles are expected among 860 draws;
    which capture and IR is not recorded). Bleed-free and same-take by construction (the render is the DI's).
    Caveats: a capture is a model of one amp at one setting and the IR comes from another rig, so no recording is
    one real rig; 132 of the 172 DIs are one player, mostly on a Strat; BKS's 40 units are read again.
  - **Data (zero renders, run; `goat-sections`).** Read from the zip without extracting it. Per item: the pool's DI
    measures (`clean_di.measure_di`); one 10-s window where the DI passes the pool's activity rule and its screens
    (`clean_di.section_flags`: hum, hiss, clipping, drop-outs) with no clip run or hard cut, from 1 s in (seed
    20261047); a DI near full scale is out. Each of its 5 renders is checked
    for length, rate and clipping in the window, classed against the DI on the window by the pool's classifier
    (`classify` on `gainmeasure`; high gain is out, the clean/crunch scope) and given its whole-item lag to the DI
    (`estimate_lag`). Up to 2 clean/crunch renders per item are kept (seeded; two chains on the same playing), folds
    by item (4; an item's renders share one) and one forced amp per unit (a third each), both seeded. Result:
    264 units from 139 of 172 items (25 had no window that passed the screens, 6 a DI near full scale, 2 no
    clean/crunch render; of 705 renders classed, 259 were high gain); by amp and class 37–51 each (pr12 38 clean,
    50 crunch; sw50r 45, 43; ac20 37, 51); folds 63–68 units; players 200, 56 and 8 units; whole-item lags −1 to
    1,233 samples, 10 units above 300 (2 renders gave none and were out). Minimum: 30 labelled units per amp and class after the lag rule and the ear, or the
    pilot stops at the data stage and the plan is revised.
  - **Trusted data, before any GOAT render.** The user hears every kept unit's window (the render, with its DI on an
    instant switch; `learn/goat_ear_page.py`, 4 parts) and answers "a believable amp tone", "odd amp sound", "the DI
    itself sounds processed or noisy" or "not sure"; only the first passes ("not sure" is out). The code enforces
    it: `goat-search` (with `--lags-only` too) refuses to start until every kept unit has a verdict, and searches
    and trains on passed units only (`goat_heard`). Flagged for that hearing: renders whose cab
    roll-off (A2's 6–10 kHz against 1–3 kHz) or low end sits outside BKS's reamps' range (a doubled cab from an
    amp-and-cab capture plus the Nolly IR, a preamp- or pedal-only capture).
  - **Labels.** First every unit's three fresh S renders (the class's S on each amp; 6 renders a unit) give its
    judge lag (`goat-search --lags-only`). One-window lag rule: a unit whose judge lag minus its whole-item lag sits
    more than 14 samples from the median of that difference over all units gives no label, and is not searched (14 until the lag amendment below; 72 since).
    Then arm A's main stage as 5B.2's stage 2 (`K.space`, 52 evaluations, seed 20261013, from the class's S; labels
    only, the best's in-process render; 53 renders a unit) on the unit's forced amp. `inputGain` stays searched, as
    on BKS, and its spread is reported beside BKS's. Units whose whole-item lag exceeds 300 samples (possibly
    far-mic IRs the plugin's close mics cannot reach) are reported apart as well as in the whole.
  - **Code guards.** GOAT records live under `goat/` (never `real/search/`, so no BKS reader, `lag_refused`, Rc or
    RigO sees them); GOAT training rows take ids from 4,000,000 (apart from BKS's 3,000,000 rows, and above the
    `own` filter); runs are named `P2a-goat{k}` and `P2a-goatshuf{k}`. Each has a test.
  - **Models.** RG: P2a-reals2's recipe and BKS rows unchanged (fold k's DIs out, both stages' labels, 300 per
    epoch), plus 300 GOAT rows per epoch from the other GOAT folds (fold k's items out), 4 folds × 2 seeds. Model k
    reads BKS fold k's units and GOAT fold k's units, as ensembles.
  - **Controls (zero renders to make).** RcBG: Rc's rule on exactly model k's training labels, BKS and GOAT, each
    label weighted by its share of an epoch (the matched centre; 5B.2's principle). RcGk: Rc's rule on model k's
    training GOAT labels alone (the model can tell a capture render from a band reamp and keep a centre for each,
    so on GOAT units this is the matched centre). RGshuf: RG with each fold's training GOAT labels permuted among
    that fold's training units within amp and class (seeded per fold; a held fold's labels never enter), same rows,
    share and steps; run if read A's per-track row reads better, before any reading is acted on (8 trainings, about
    1,700 renders).
  - **Reads.**
    - A, in domain (isolation first): on each held GOAT unit, RG − RcGk (primary) and RG − RcBG by sound (the
      unit's forced amp, read as 5B.1 on both halves), clustered by item with the fold interval beside, each decided
      by 5B.2's rule (both intervals exclude 0 on the same side); heads and setting space beside (zero renders).
    - B, transfer, on BKS's 40 units as 5B.2: RG − RcBG and RG − Rcs2, both by 5B.2's DI-and-fold rule; a per-track
      reading on BKS needs RG better than both (RG − Rcs2 alone is the adoption row). RcG − S and RcG − Rcs2 (Rc's
      rule on all GOAT labels; by-DI rule) beside: does a capture centre move toward real amps?
    - RGshuf, if it runs: RG − RGshuf on held GOAT units (item-and-fold rule) and on BKS (DI-and-fold rule).
    - Guards: FS/NS heads against P2a-reals2's; damage is a knob NLL rise outside the range arm R's 8 runs showed
      (−0.016 to +0.027) in both seeds of a fold.
  - **Reading, declared now.**
    - A better (RG − RcGk): RGshuf runs. If RG − RGshuf on GOAT units is undecided or worse, the gain is not credited
      to the GOAT recordings' own labels (more rows or a bigger real share would do it), and the full set does not
      run; the user decides the next step with this evidence.
    - A better and RG − RGshuf better: a per-track reading is learned in domain from the recordings. With B's RG
      better than both RcBG and Rcs2 too, it transfers: the full GOAT set (about 450 clean/crunch recordings)
      follows in its own amendment, and RG is a readout candidate for D_fix.
    - A better, B's undecided or worse: learned in domain, not transferred to real reamps. The user decides between
      more real chains (TONE3000's amp-and-cab captures by research request) and domain work, with A, B and RcG − S
      as evidence; the full GOAT set does not run.
    - A undecided or worse: the model does not learn a per-track reading from the pilot's captures (the realised N
      stated). The user decides
      between the full GOAT set (the curve's next point) and model changes, with A's heads and setting space as
      evidence.
    - RG − Rcs2 decided worse on BKS, or FS/NS damaged: GOAT rows are not adopted for reading real recordings.
  - **Rules.** BKS is the only real read set; V-real and the NS songs untouched. Every render: isolate=True, one
    priming render, 0.25 s trim, at most 3 processes, the 31 GB guard (the user frees space first). GOAT's audio is
    read with `python -I` from its own folder. A staged stop (`goat-stage-check`), once a third of the trusted units
    are searched: stop if the in-process best's held-half log ratio to S, clustered by item, has its 90% interval's
    upper end at or above 0 (the searches do not decidedly beat S where they did not search), or if more than half
    of the labels put `inputGain` at a bound (the captures' calibration would set the labels). Two renders per item
    rather than one is a choice: it doubles the label renders to give about 45 units per amp and class.
  - *Review (2026-11-01, independent, before any render):* approved with required changes, all made: the matched
    centre RcBG as the per-track control (Rcs2 kept as the adoption row); RGshuf against "more rows and a bigger
    share"; GOAT held out by fold and read in domain first (isolation); a one-window lag rule; the data step run
    and N stated; the ear before any GOAT render, on the renders, with outlier flags; code guards with tests; and
    a closed reading map. Its re-check asked for four more, all made: read A against the GOAT-only centre RcGk (a
    model can keep one centre for captures and one for reamps) and a BKS per-track claim against both centres;
    RGshuf permuted within each fold's training units, with its rule and outcome mapped; the staged stop's
    thresholds; and the pool's hum and hiss screens on the window. Adopted from its suggestions: every unit's lag
    first, the search only on trusted units, and the large-lag units reported apart. Its second re-check asked for
    one more, made: the ear's verdicts applied in code before any GOAT render (`goat_heard`), with "not sure" out.
  - *Amendment (2026-11-01, after the ear, before any GOAT render): the heavy check.* The ear passed 255 of 264
    units ("odd" 9, all crunch); the user then said they may have been too permissive with heavy, fizzy ones. The
    pool's scope is clean/crunch-led, heavy tones a small minority. The 9 odd units' gain measures sit within the
    passed crunch units' (median non-linear share −2.7 dB against −1.8), so no measure reproduces that verdict;
    the candidates are named by the pool's own classifier instead: passed units whose `classify` clean_vs_driven
    split is "driven" (non-linear share at or above 0 dB and level slope at or below 0.3, its firm-driven margin).
    That is 34 units, all crunch (by the unit's forced plugin amp, not GOAT's capture amp: pr12 16, ac20 10,
    sw50r 8; 2 with whole-item lag above 300). The user hears
    them again on their own page (`learn/goat_ear_page.py heavy`, shuffled, blind to the measure, same A/B player)
    against the scope: "keep", "too heavy or fizzy" or "not sure"; only "keep" stays in. The code enforces it:
    `goat_ear_passed` subtracts `goat_heavy_out` and refuses until every candidate has a verdict, so
    `goat-search` (and `--lags-only`) cannot start before; it also refuses a heavy page whose units are no longer
    the current firmly driven passed units, or answers from another build. Units not on the page are not re-heard:
    the check is on the measure's side only, a choice (the ear already passed them; 22 passed units sit just below
    the margin, non-linear share at or above −1.5 dB and slope at or below 0.4, and stay in). Known biases: the
    page has no filler units, so every card is a candidate, which may lean verdicts toward "heavy"; and a
    narrower crunch may shrink the per-track spread read A can show. If all 34 go: 221 units from 135 items (4
    items lose every unit), by forced amp and class ac20 37 clean / 37 crunch, pr12 38 / 31, sw50r 45 / 33; folds
    52–59. The minimum (30 trusted units per amp and class after the ear, the heavy check and the lag rule)
    stands and is now in code: `goat-search`'s main stage refuses to start if any amp and class falls below it
    (`goat_short_cells`), and the pilot stops at the data stage for a revision (a third render per item, or a
    seeded rebalance of the forced amps). Label renders fall by about 13% if all 34 go.
    *Outcome (2026-11-01, user's answers exported 14:28, page build 6abd26d193e0; ledger
    `phase_5c_heavy_outcome`):* of the 34 candidates the user kept 12 and marked 22 heavy (none unsure); 233 heard
    units pass the ear and the heavy check, from 135 items, every amp and class 35–45, before the lag rule.
  - *Review of the amendment (2026-11-01, independent):* approved with required changes, all made: the stop rule
    on any amp and class, not pr12 crunch alone; the minimum enforced in code before the main stage, with a test;
    a test of the gate itself (`goat_ear_passed`). Adopted from its suggestions: the heavy answers' build and the
    candidate set checked in the gate, a test of `firmly_driven`, the two known biases, the forced-amp naming and
    the rebalance named as an alternative.
  - *Amendment (2026-11-01, after the lag pass, before any search render): the lag rule's tolerance.* The lag pass
    ran (1,398 renders; 231 of 233 units lagged, 2 gave none). With the one-window rule at 14 samples the main
    stage refused to start, as the minimum requires: 131 units left, 19–25 per amp and class. Finding: judge lag
    minus whole-item lag is bimodal (a main mode at −90 samples, 131 units within 14; a second near −45, 66
    units). Each unit's window DI-to-render lag matches its whole-item lag (median difference 0 in both modes; within
    3 samples for 93 of 131 main-mode and 56 of 66 second-mode units; all 231 checked, zero renders,
    goat/window-lag-check.py and .json), so the second mode is not a shifted window; it lies between the plugin's
    S render and the capture render. It clusters partly by item (18 items have both units in it, about 9 by
    chance), so the DI or the item-lag estimate takes part: a phase, not the playing. The rule assumed one
    constant offset, true on BKS (one chain per recording, compared with its own windows), not across GOAT's
    chains. Diagnostic (ledger `phase_5c_lag_diagnostic`; written to the ledger file in the same command, seconds
    before the run, and committed after it, at 14:59): 12 units, 6 per mode (seed 20261049), S re-rendered as the
    lag pass did (all 12 bit-identical to the stored renders), the S judge scanned over ±72 samples of the stored
    lag in 3-sample steps; run 14:55:47–14:57:54, 24 renders (goat/lag-diagnostic.py and .json). The judge is
    insensitive to the lag in both modes: its log changes by at most 0.022 over the whole scan (per unit, the larger
    change at −45 or +45: median 0.002), against search gains of about 0.35 on BKS and read effects of 0.04–0.15, and the reads are paired at the
    same unit and lag; the label is the in-process render and uses no lag. (The declared reading, where the minimum
    sits, cannot decide on a curve this flat: the best offsets scatter from −48 to +72.) So the 14-sample rule
    refuses units the judge cannot tell apart. Revised: `GOAT_LAG_TOL` = 72 samples, the scan's span, where the
    judge was shown insensitive. It refuses 18 units: 7 whose lag is 809–2,069 samples off the median (gross
    failures), 9 at 93–134 off (outside the scan, not shown to matter, refused to stay within what was shown) and
    the 2 with no lag. Honest note: 72 was chosen after the counts at 14 were known, and it clears the minimum
    (215 units; ac20 34 clean / 36 crunch, pr12 33 / 36, sw50r 43 / 33; 48 would leave pr12 at 28 / 28); every
    tolerance from 71 to 92 gives the identical set (the nearest kept units sit −70 and +67 from the median, the
    nearest refused −93 and +106). The rule now reads every heard unit's lag from goat/lags in one place
    (`goat_lags_refused`), so the search, the labels, the staged stop check and the reads refuse the same units
    whatever has been searched (the median of a two-mode set taken over a third of the records would move). Read A
    is also reported on the main-mode units alone (`goat-report --lag-tol 14`: the same models, the held units
    narrowed); read B has no such variant (it would need models trained on main-mode labels only, not run).
  - *Review of the lag amendment (2026-11-01, independent):* approved with required changes, all made: the
    diagnostic's timeline stated as it happened; the refused units described by distance (7 gross, 9 at 93–134)
    and the 71–92 invariance stated; read A's main-mode variant in code (`--lag-tol`), read B dropped from that
    promise; one lag rule for every caller, with a test; the window check saved with one count. Adopted from its
    suggestions: flatness in log-judge units, "insensitive" rather than "the stored lag is right", the item
    clustering, and a pointer from the main 5C block.
  - *Progress (2026-11-01, interim; the finding, F37, follows RGshuf).*
    - Search: 215 trusted units searched (11,395 renders, 15:08–16:55, three shards, no errors); one unit's best was
      silent (`goat/item_68@35.0#amp_5`), so it gives no label but is still read. Staged stop at 102 units
      (ledger `phase_5c_stage_check`): held-half best − S −0.336 [−0.393, −0.280], `inputGain` at a bound in 18% of
      labels; neither stop condition held.
    - Centres (`goat-centres`, zero renders) and RG's 8 trainings (16:57–18:50, best epochs 15–30 of 60), then RG's and
      the centres' read renders (860 on GOAT and 480 on BKS each).
    - Read A (215 units, 130 items): RG − RcGk −0.053 [−0.077, −0.029] by item (83 of 130 better), by fold −0.043
      [−0.063, −0.023], every fold negative: decided better. RG − RcBG −0.064 [−0.089, −0.039], by fold −0.052
      [−0.075, −0.030]. On the main-mode units alone (`--lag-tol 14`, 94 items) RG − RcGk −0.057 [−0.086, −0.028].
      Beside (zero renders; `goat/read-a-beside.py` and `.json`):
      - In setting space RG's answers sit 0.127 from RcGk's but no nearer the units' labels (rms 0.259 against
        0.259; RcBG 0.264, S 0.294; switches and mics agree 0.624 against 0.632), as on BKS (F35).
      - No model sees its held GOAT items (0 item overlap in each fold).
      - Units whose whole-item lag exceeds 300 samples, apart: 6 items, 12 directions, RG − RcGk −0.142 [−0.275,
        −0.008]; without them −0.052 [−0.076, −0.028] (129 items).
      - `inputGain` (unit scale of its searched range): GOAT labels mean 0.50, sd 0.30, at a bound 19%; BKS's stage 1
        and 2 labels mean 0.39, sd 0.26, at a bound 21%.
      - Heads on each fold's held GOAT labels (46–59 per fold, both seeds): RG's knob NLL is 0.59 to 0.95 below
        P2a-reals2's, its switch CE 0.16 to 0.25 and its mic CE 0.44 to 1.07 lower (P2a-reals2 never saw a capture
        render; these held-label NLLs include the centre, so they do not by themselves show a per-track reading).
        RGshuf's heads follow with F37 (one of its runs had finished when this ran and is in the file).
      - Not yet run: nothing else declared for read A.
    - Read B (BKS, 40 units): RG − RcBG −0.052 [−0.115, +0.011] by DI (7 of 8 better), by fold −0.047 [−0.104,
      +0.010]; RG − Rcs2 −0.035 [−0.102, +0.032], by fold −0.036 [−0.091, +0.020]: both undecided. Beside: RG − S
      −0.193 [−0.292, −0.094]; RcG − S −0.106 [−0.168, −0.045] (a capture centre moves toward real amps), RcG −
      Rcs2 +0.052 [−0.026, +0.130] (both by DI; the centres have no models, so their fold interval is not read).
      RG − P2a-reals2 −0.064 [−0.130, +0.002] by DI, by fold −0.053 [−0.115, +0.010]: undecided (the GOAT rows'
      own effect on BKS, beside). (`real-report` now gives 5C's rows their fold interval, as declared.)
    - Guard (`real-heads --names G`): knob NLL rise RG − P2a-reals2 on FS or NS above +0.027 in one seed of one
      fold only (fold 2, +0.034 on both): no fold damaged in both seeds. On each fold's held BKS labels RG's knob
      NLL is below P2a-reals2's in 7 of 8 runs.
    - As declared, read A better means RGshuf runs before any reading is acted on (launched 19:10; read in F37).
    - Notes for F37: RGshuf permutes the training labels before they are cycled to 300 rows per epoch, so which labels
      get a second copy in an epoch differs from RG's (same inputs, a near-identical label multiset). `goat-report`
      drops a refused or non-finite direction, where `real-report` scores a refused answer as S; none was refused
      (missing 0 in every row). The run files mark RG and RGshuf by name only (`--goat` and `--goat-shuffle` are
      not in their `flags`).
  - *Lag check across earlier reads (2026-11-01, at the user's question whether the lag issue hurt earlier tests;
    ledger `phase_5c_lag_scan_10ms`, `phase_5c_lag_scan_bks`, each declared before its run).* The ±72-sample
    diagnostic did not reach `estimate_lag`'s known failure, a lock onto another pitch period (about 6 ms). Two
    scans did:
    - The same 12 GOAT units over ±10 ms (24 renders): the S judge's log moves by a median 0.031 (90th percentile
      0.061) within ±6 ms, so a 6 ms error is not negligible for one score; every unit's stored lag sits at the
      judge's minimum (at most 0.013 to gain, one unit).
    - BKS's 40 units, S and Rcs2 on each amp over ±10 ms (480 renders): no unit's stored lag is off the judge's
      minimum by 0.01 or more (median 0.0002, max 0.0075), so 5B.1, 5B.2's stage 1 and 5C's read B stand on right
      lags. A 6 ms error would move a paired read, ln(Rcs2/S), by a median 0.021 (90th percentile 0.059), so lags
      stay checked.
    - An inventory of every judge call: every read is paired at one lag per unit. Earlier validation reads use
      catalogued lags (many pooled renders with stability and onset checks, `research/record_part_lags.py`) or
      the DI-to-track waveform lag. The 3-render lags of 5B.1, 5B.2 and 5C are the risky ones: covered above for
      BKS's 40 units and 12 GOAT units; 5B.2's stage 2 units by `lag_refused` (agreement across windows of one
      recording within 14 samples, which a pitch-period lock would break); GOAT's other units by agreement with
      the independent item lag within 72 samples. No earlier read is found affected.
- **5D, a real-amp test panel across bands (v1; ledger `phase_5d`; zero training; renders stated after its data step).** Question:
  does F37's per-track reading carry over to real amps when the read set is many bands, not one? The user asked
  (2026-11-01) whether the tests are broad enough; they are not: BKS, the only real read set, is one band, 8 DIs and
  mostly two songs, so read B's intervals are wide and a result there may not hold for other players, guitars or
  styles. The user approved the panel the same day.
  - **Sources, fixed now, before any of their audio is heard for this purpose** (from the session's inventory of
    every local DI-plus-real-amp recording: no verified clean/crunch band is left outside training and V-real):
    Blue Manic "Acomatay" (Cambridge-MT, 5 DIs, 6 amp tracks; a reserved test band, used here as one); The Laminar
    Flow "Headspace" (set 4's Wayback additions, 11 DIs × 3 mics; each mic track a rig); Sonnet & Alcohol "Back To
    The Nineties" (2 clean DIs); MedleyDB's crunch pairs (set 6: Little Tybee, Port St Willow, Big Troubles); and
    Guitar-TECHS P3 (12 clean solo excerpts, an Orange CR-12, mic'd). BKS's 40 units join as they are. Out: V-real
    and its bands, every training band, and Jen Hartswick & Nick Cassarino (reserved for V-real's growth, the final
    exam).
  - **Units (zero renders, `panel-sections`).** Per DI: up to 3 windows of 10 s, at least 10 s apart, where the DI
    passes the pool's activity rule and screens (`clean_di.section_flags`), seeded (20261101); a DI's windows are
    shared by all its amp tracks (as BKS's rigs share sections), each (window, amp track) a unit. Each unit is classed
    against its DI (`classify`, high gain out: the clean/crunch scope). Guitar-TECHS P3's excerpts give one window
    each. 44.1 kHz sources are resampled to 48 kHz first; every lag below is in 48 kHz samples. The DI-to-track lag:
    first over the whole track with a wide search (±1.5 s; Blue Manic's amp tracks run 0.4–1.2 s longer than its
    DIs), then on the window with that as the hint (`estimate_lag`, the DI as the render); a window whose lag sits
    more than 72 samples from its track's is out. A track whose DI-to-track lag exceeds 5 ms (MedleyDB's far-mic
    rule) is flagged far. Each unit's bleed residual: the amp track's level on frames where its DI is silent,
    against its level where the DI plays (F30's gated read; zero renders). Clipping and level checked. Each new DI
    gets a fold (seeded, balanced within its band), so new units are read exactly as BKS's and GOAT's are. The counts
    by band, class and fold are stated, and this block amended with them, before the ear and before any render.
  - **The ear, before any render.** The user hears every unit's amp-track window with its DI on an instant switch
    and answers "a real amp, the guitar alone", "other instruments audible in the amp track", "odd or processed",
    "the DI sounds processed or noisy" or "not sure". Only the first passes, enforced in code before any render.
    Minimum: at least 5 new bands with at least 4 passed units each, or the panel is revised before any read.
  - **Lags.** Each unit's judge lag from its three S renders pooled (5B.1's rule), searched around its DI-to-track
    lag less the plugin's latency; a unit whose two estimates differ by more than 72 samples is out and reported.
  - **Answers (zero training; zero renders to make).** Each new unit is read by its fold's models and centres, as
    F37: RG = `P2a-goat{k}` and P2a-reals2 = `P2a-real{k}s2` (both seeds pooled, at their training inputs' median
    loudness, per search half); RcBG_k on exactly model k's training lists (`centre_records`), Rcs2_k on model k's BKS
    list, RcG on every GOAT label, and S. Every answer on each of the three amps, as 5B.1. BKS's units keep their
    stored answers and judges.
  - **Reads** (held half; search halves alternating within each DI, as 5B.2's):
    - Primary: RG − RcBG_k on the new bands only, with capped band weights: each band weighs as the smaller of its
      DIs and 4, its DIs equal within it (more performances carry more evidence, but no band more than about a
      quarter; Guitar-TECHS P3's 12 excerpts are one amp chain, so the cap matters there). Its 90% interval is the
      weighted one, clustered by DI. Beside: equal band weights, the DI-weighted mean and the band-clustered
      interval (the population-level read). BKS's own rows (F37) sit beside, never pooled into the primary.
    - Adoption row: RG − Rcs2_k. Beside (descriptive): RG − S, P2a-reals2 − Rcs2_k, RcG − S.
    - Sanity rows (zero extra renders): RcBG_k − S and Rcs2_k − S per band (does the real-amp centre still beat S
      off BKS?), and S's held-half judge distance per band against BKS's range.
    - Every row per band (mean, interval clustered by DI within the band, or by window where a band has one DI), per
      class (clean, crunch; class is confounded with band: Guitar-TECHS P3 and Sonnet & Alcohol are clean, The
      Laminar Flow and MedleyDB crunch), leave-one-band-out, and with far-mic and high-bleed units apart (bleed and
      room reach RG's input but not the centres', so they bias the read against RG).
    - A true-DI ceiling (about 370 renders): one window per new band, on one amp, searched as 5B.2's stage 2, so an
      undecided result can be told from "nothing to read here".
  - **Reading, declared now.**
    - Decided on the primary row when its weighted DI-clustered interval excludes 0, no band's own interval excludes
      0 on the other side, and with any one band removed the weighted mean keeps its sign and at least half its size
      (no band supplies more than half the effect; the band whose removal moves it most is reported). The
      band-clustered interval is reported, not required, so a decided read speaks for these panel bands'
      performances, not for bands in general. Power (from BKS's per-DI SD of 0.094, t-intervals; the effective
      number of DIs, 1/Σw², is stated with the counts, expected about 25 under the capped weights): about 0.85 for an
      effect of −0.05 and 0.5 for −0.03 (equal band weights, about 13 effective DIs: about 0.6 and 0.3; by band, about
      7 clusters: 0.4–0.5 and 0.2). An undecided read is underpowered, not a failure.
    - Primary better and the adoption row better: the per-track reading transfers across these bands; the full GOAT set
      follows in its own amendment and RG is D_fix's readout candidate.
    - Primary better, adoption row undecided or worse: the reading transfers beyond the matched centre but RG is not
      adopted over the real-amp centre; the full GOAT set may follow (its own amendment), the readout stays Rcs2.
    - Primary undecided: not shown across bands; the user chooses between domain work and more real chains with the
      per-band rows and the ceiling as evidence.
    - Primary worse (only if it holds without the far-mic and high-bleed units): GOAT rows are not adopted for
      reading real recordings.
  - **Guards (code, with tests).** No panel file or hash appears in any of the 16 runs' training lists, in BKS's or
    GOAT's labels, or in any centre's inputs; panel reads refuse without the ear's verdicts.
  - **Rules.** No training and no tuning on the panel: it is a test set from now on. The ledger counts its reads
    (`phase_5d_panel_reads`); each later model read on it is declared and counted, and a panel read never picks a
    recipe without a fresh panel or V-real read. V-real untouched. Renders as always (isolate, one priming render,
    0.25 s trim, at most 3 processes, the 31 GB guard). Downloaded audio read with `python -I`. Caveat: Guitar-TECHS
    P1/P2 DIs are in the older DI pool (perhaps the same player and guitar as P3, not the same amp chain).
    Budget (counts stated after `panel-sections`): lags about 3 renders a unit, reads about 12 a unit for each model
    tag and 6 for each centre, the ceiling about 370.
  - *Review (2026-11-01, independent, before any code or render):* approved with required changes, all made: the
    primary row on new bands only, BKS beside; each new DI read fold-wise against its exactly matched centre; the
    counts fixed before the ear, with a band-weighted headline; a band counted reversed only when its own interval
    says so, leave-one-band-out beside; the power stated and an undecided read mapped as underpowered; bleed and
    far mics reported apart, with "worse" acted on only without them; lags searched wide and the 44.1 kHz sources
    resampled; a leakage guard with a test; the reading map closed; sanity rows. Adopted from its suggestions: a
    small true-DI ceiling, shared windows across a DI's mic tracks, and a count of the panel's reads. Not adopted: a
    mic-swap check on The Laminar Flow (extra renders; later if the primary is decided). Its re-check asked for two
    more, made, and a third adopted: the interval weighted as the headline, with the effective N and the power
    restated; leave-one-band-out as an anti-dominance rule (no band more than half the effect); and single-DI bands
    clustered by window. The headline's weights were then capped (each band as the smaller of its DIs and 4) to keep
    the power near 0.85 at −0.05 while no band weighs more than about a quarter; equal band weights stay beside.
    Its second re-check approved the cap (effective N about 25.5, power about 0.84 at −0.05 and 0.45 at −0.03) with
    caveats now stated: Blue Manic, The Laminar Flow and Guitar-TECHS P3 carry about 71% of the weight; P3's share
    rests on one amp chain and one player (independent playing, not independent chains); the read answers for these
    panel bands; and the effective N and power are recomputed from the units that pass the ear, lags and class, and
    stated before any render.
  - *Amendment (2026-11-01, after the data step, before the ear and any render): more sources, DI hum allowed.*
    `panel-sections` as declared gave 40 units from 15 DIs, and only The Laminar Flow (25 units) and Sonnet &
    Alcohol (4) reached 4 units: most spare material reads high gain (Blue Manic 7 of 10 units, Big Troubles, Laminar
    Flow ElecGtr05), and 11 of Guitar-TECHS P3's 12 excerpts fail only the DI hum screen. The minimum fails, so the
    panel is revised before the ear, at the user's word ("whatever you recommend") on the options put to them:
    - a DI's hum flag passes for the panel only (`PANEL_DI_NOISE_OK`): the amp heard the same hum, so render and
      recording share it and the comparison stays fair; every other screen stays;
    - two MedleyDB clean bands join, Aimee Norwich "Flying" (RAW_05_02 → 05_01, polarity −1) and Dahka Band "Soldier
      Man" (RAW_04_01 → 04_02, MedleyDB marks bleed), whose DI roles set 6 labelled by ear: the ear decides each;
    - Jen Hartswick & Nick Cassarino (4 songs, one amp mic each; jazz/soul, a style the panel lacked) joins, taken
      from V-real's reserve; V-real itself stays the 11 clips;
    - windows per DI stay 3 (more windows of one performance add little evidence).
    The rerun (zero renders): 62 units from 26 DIs in 10 new bands — The Laminar Flow 8 DIs / 28 units, Jen Hartswick
    & Nick Cassarino 4 / 8, Sonnet & Alcohol 2 / 6, Guitar-TECHS P3 5 / 5, Big Troubles 2 / 2, and one DI each from
    Aimee Norwich (3 units), Dahka Band (3), Port St Willow (3), Blue Manic (2) and Little Tybee (2); clean 30,
    crunch 32; folds 18, 13, 12, 19 units; one far-mic track. Out: 18 windows high gain, 13 on the lag rule, 8 DIs
    with no window. Effective N under the capped weights 24.2 (equal band weights 15.2): power about 0.83 at −0.05
    and 0.47 at −0.03.
    - The minimum is restated on what it was for (power, not units per band): after the ear, an effective N of at
      least 20 under the capped weights, from at least 6 new bands; below it the panel is revised before any read.
      (As first written, at least 5 bands with 4 units each, only 4 bands would qualify, though the power is near
      what was declared.) Bands with one DI are read per band by window, as declared, and their own intervals are
      reported, not used alone.
    - "High bleed" is fixed now, before any read: a unit whose bleed residual exceeds the largest among BKS's 40
      reamped units (no other instrument can be in a reamp; their residual is the amp's own tail and noise, measured
      the same way, zero renders) is reported apart, as declared.
  - *Review of the amendment (2026-11-01, independent):* approved with required changes, all made:
    - The panel is frozen: after the ear it may only fail the minimum, not be revised again.
    - Hum-passed units (the DI's window carries the hum flag: 20 units, The Laminar Flow 12, Guitar-TECHS P3 4,
      Sonnet & Alcohol 3, Blue Manic 1; `di_flags` in units.json) are reported apart, as far-mic and high-bleed units
      are: RG's training inputs were screened hum-free, so hum biases the read against RG; "worse" is acted on only
      if it holds without all three groups.
    - The amp window is cut pre-shifted by the track lag (`panel_cut`, tested on both signs), so each unit's judge
      lag is searched around its window's residual lag (window lag − track lag) less the plugin's latency (52).
    - The BKS reamps' largest residual is fixed: −18.35 dB (`PANEL_BLEED_MAX_DB`; 22 of their 40 units measurable,
      median −36.4). On the panel 23 units are above it and 24 unmeasured (too few DI-silent frames), reported apart
      as "unmeasured". The residual holds amp and room tails too, not only other instruments.
    - Jen Hartswick & Nick Cassarino are no longer an unseen candidate for V-real's growth (ledger).
    - Adopted from its suggestions: Guitar-TECHS P3's track lags (40–232 samples across one rig's excerpts) are
      reported with the judge-lag check; `panel_leaks` checks the pool's DI inventory, which every training list
      draws from (with BKS's set 5 and the GOAT zip, neither of which holds a panel file).
  - *The ear (2026-11-01) and the read's status.* The user heard all 62 units (40 "amp", 15 "DI bad", 6 "not sure",
    1 "odd") and asked for a check of the very clean ones ("maybe there were DIs that are actually clean amp tracks").
    Measured (zero renders): Guitar-TECHS P3's and Dahka Band's amp tracks are near copies of their DIs (1/3-octave
    difference SD about 3 dB, 12–15 dB range; elsewhere 4–13 dB SD), confirming the user's "both are the DI"; both
    bands are out (`PANEL_DI_LIKE`), the 2 units passed there included. Jen Hartswick & Nick Cassarino's, Port St
    Willow's and Aimee Norwich's pairs measure as a bright DI and a coloured amp, so their 9 doubtful units were heard
    again with that stated (panel/recheck.json: 7 "amp", 1 "DI bad", 1 "not sure"); the re-check's verdict replaces
    the first. Sonnet & Alcohol's DIs measure as compressed (crest 9–12 dB, below their amp tracks'), so "DI bad"
    stands. Passed: 45 units, 17 DIs, 7 bands (The Laminar Flow 8 DIs / 28 units, Jen Hartswick & Nick Cassarino
    3 / 6, Big Troubles 2 / 2, and one DI each from Aimee Norwich, Port St Willow, Blue Manic and Little Tybee);
    crunch 33, clean 12; hum-passed 13, high bleed 22. Effective N 15.4 under the capped weights, below the minimum
    (20): power about 0.65 at −0.05.
  - **By the minimum the panel cannot decide.** The user chose (2026-11-01) to read it anyway as a strong hint, not a
    verdict: every row is computed and reported as declared, its decision rules applied and labelled underpowered
    (effective N 15.4); a "better" there is a hint that the reading carries over across these bands, not grounds for
    adoption; an undecided read says nothing beyond its numbers. Nothing in the reading map is acted on from it
    alone. The panel is frozen; its reads are counted.

- **Chosen on FS, NS and the k-fold reads only**, before any V-real read of D_fix. Phase 4's V-real reads are
  measurements; if they shape the choice, D_fix's V-real read is labelled selection-contaminated. The candidates by
  outcome:
  - other guitars carry the loss (a − b small, b − c large): train where the target leads the other guitars; how
    the product says a part is not readable is for the product session;
  - the separator carries it (c − d large): read the mix, or the mix and the stem;
  - the clean input already fails: the loss or labels (audibility weights, a sound-aware loss), sized by P1;
  - the curves still rise at full size: scale (the F20 build's staged plan), read on V-real at each stage, in its own plan.
- **D_fix:** the recipe plus every adopted fix, 2 seeds, read by sound on FS and NS, with the amp mismatched (about
  480 renders), and on V-real with the plain readout as primary and P3's readouts beside.
  - *D_fix declared (2026-11-02, after F38, before any D_fix code or render; ledger `phase_dfix`; revised after its
    review the same night, before any code).*
    - **What is adopted, and why.** The backing fix: P2b-wide24's recipe (the target in its own backing or 1 of 24
      pool backings per epoch; F29: about half of the backing's loss recovered, both seeds, NS and FS). The fixes every
      run already carries: the class input (F2), early stopping on NS (F18), runaways out, the doubles pinned as
      every run (rung b has no re-rendered doubles; their re-render served rungs c and d only, F16), the by-sound read
      (F10). The real-amp fix: real rows, which fixed F31's real-amp penalty on k-fold reads (F34/F35: −0.19 against
      P2a on BKS, decided): BKS's stage 1–2 labels and GOAT's labels, 300 rows each per epoch, as RG (F37). GOAT rows
      are kept on a lean: neither 5C's nor 5D's adopt or reject branch fired (F37's B undecided; F38 a strong hint,
      RG − Rcs2_k −0.014, P2a-reals2 − Rcs2_k +0.039); they are part of the recipe read 2 tests, and the per-track
      reading is not claimed. The readout is plain (F23, F12); S-centred and real-amp-centred readouts stay beside,
      not chosen. Not adopted: the near-chance rule (F23), the S fallback (the user's 2026-10-27 ruling), audibility
      weights (unbuilt), more size (F25).
    - **The real rows in backings.** Plugin rows sit in a backing in 24 of 25 epochs, so clean real rows would mark
      "real-amp label" by the missing backing. Each real row is therefore built as WideData's variants are (zero
      renders), with a seeded training example of the same class lending its levels: the amp track is brought to that
      example's stored target loudness (its `y`, before the overall gain), each backing is given `cmd_build_wide`'s
      gain (the example's `gb` plus its own bare backing's level less the entry's), the sum is multiplied by the
      example's overall gain `ga`, and the example's mastering draw applies (`build-dfix-real`). Each row has 25
      variants: a BKS row 1 of its own section's backing (the section's non-guitar stems only, excluding every track
      of the same DI, whose other reamps are the same performance) and 24 pool backings from other sessions; a GOAT row
      25 pool backings. Pool backings never come from the row's own session. Their level then follows P2b's inputs
      (median about −13.7 LUFS) as the mix's does.
    - **Models.** D_fix = P2b-wide24's recipe plus all real rows, 2 seeds (20261042, 20261043), for FS, NS and V-real.
      D_fix_k = the same with fold k's BKS DIs and GOAT items out, 4 folds × 2 seeds, for the k-fold reads. 10
      trainings, about 3 h of MPS. Run names `P2b-dfix` and `P2b-dfix{k}`. The backing schedule is seeded by the
      pool's seed, so the two training seeds differ in initialisation and batch order only. The held-fold real loss
      is logged per checkpoint as a diagnostic, never for choosing.
    - **Reads, in order; D_fix is chosen on 1 and 2 only.** Every model answered the same way (`answers --seeds`,
      the two-seed ensemble).
      1. FS and NS by sound on P2b's inputs, at the true amp and both mismatched amps, as F19, for D_fix and for
         P2b-wide24 answered alike (about 1,440 renders): D_fix − P2b-wide24 must not be decided worse on either set
         at any amp. D_fix − S reported. Beside, the input the product sees: D_fix and P2b-wide24 on FS's and NS's
         stored P2d stems, at the true amp (about 480 renders), reported against S. If D_fix on the stems is not
         better than S while it is on P2b's inputs, the user is told before V-real (its outcome is then largely
         predictable, as 5B.1c's was).
      2. k-fold on BKS's 40 units (DI-and-fold rule): D_fix_k − Rcs2 (adoption), with D_fix_k − RG (the cost of the
         rung-b base) and D_fix_k − S beside; inputs the units' own backed sections (primary, as the product hears a
         song), their clean amp tracks beside (about 960 renders). On GOAT's held units, D_fix_k − RcGk by item and
         fold, beside (about 430 renders); BKS governs.
      3. V-real (the final exam, read once): its input the X-LANCE stem of each part's mix, as the product reads a
         song, brought to its input level by the same rule FS's and NS's stored stems follow (asserted in code), the
         amp tracks beside in the same sitting (separator or model); D_fix's plain readout − S primary, with P2b-wide24, RcG and the S-centred readout beside (about 600
         renders). It decides nothing about the recipe; were it used to choose, it is labelled
         selection-contaminated. It is also the fresh read the GOAT rows' lean (from the panel) needs.
    - **Reading, declared now.**
      - Read 1 decided worse on either set at any amp: D_fix is not built as is; no V-real read happens until a new
        declaration is reviewed (the real rows' share is the suspect).
      - Read 2's BKS row: D_fix_k − Rcs2 decided worse: as read 1 (no V-real until a new declaration). Undecided or
        better: D_fix stands. GOAT's row is reported; if it is better or undecided while BKS is worse, BKS governs.
      - Read 1 and 2 passed: read 3 runs. On V-real, D_fix − S better: the pipeline beats the plugin's own start on
        held-out real songs for the first time, and the scale step's plan follows; undecided or worse: the user
        decides between scale, domain work and more real chains with every read as evidence.
    - **Guards (code, with tests).** A combined `--wide --real-fold` run gets its own branch, and any other combination
      refuses; WideData's variant check takes plugin ids only; the real-row inputs live in their own cache directory
      (`dfix/inputs`), the run file stores their target loudness, and every predict path asserts it; `real-predict`
      refuses `P2b-dfix` (all labels) on BKS by name. Known-answer checks: with the real rows off the new path
      reproduces P2b-wide24's training ids and rows hash; one stored RG BKS answer reproduces exactly.
    - **Rules.** No V-real read before reads 1 and 2 are written up and reviewed. The user's choice from F37/F38
      (domain work or more real chains) stays open; D_fix uses only the evidence so far and does not wait on it.
      Budget: about 4,000 renders (read 1 1,920, read 2 1,390, read 3 about 700 with the amp tracks beside) and about
      3 h of MPS, within this approved plan.
    - *Review (2026-11-02, independent, before any code):* approved with required changes, all made above: V-real's
      input declared (the stem) and the stem tested on FS/NS first; the real rows in backings (no domain marker; their
      level follows); read 1 computable and like for like (both models answered and rendered alike at every amp); the
      map closed (read 2 worse, BKS governs, no V-real without a new declaration; D_fix_k − RG beside); the code traps
      as guards with tests; the GOAT rows' status and the user's open choice recorded. Adopted from its suggestions:
      known-answer checks, the held-fold real loss as a diagnostic, the seeds' meaning and the budget. Its re-check
      approved with three wording fixes, made: the real rows' levels follow `cmd_build_wide`'s rule exactly (the
      borrowed example's target level before its overall gain, the backing gain's own-level correction); BKS's own
      backing holds non-guitar stems only; the V-real stem's level rule and the stem read's consequence stated. Adopted:
      V-real's amp tracks beside.
  - *D_fix's outcome and its amendment (2026-11-02, after F39, before any code or render of the amendment; ledger
    `phase_dfix_outcome`, `phase_dfix_share`).*
    - **Outcome (F39).** Read 1 decided worse at the true amp on FS (+0.062) and NS (+0.123) and on NS at both
      mismatched amps; by the map D_fix is not built as is and V-real waits for this declaration's review. Read 2's
      adoption row undecided (+0.036). On P2d's stems D_fix reads NS better than W (−0.051), beside.
    - **The suspect, and the one change.** The real rows were a quarter of each epoch's rows (606 of 2,393); the
      hypothesis (F39, not shown) is that this share draws the fit away from the plugin rows. The amendment lowers
      their share and changes nothing else: in each epoch each training real row is shown with probability p, a
      seeded draw on its own key (`f"{DFIX_SEED}|show|{i}|{epoch}"`, independent of `dfix_variant`'s), so every label
      stays in and only its frequency drops. The filter is applied to `fit`'s order after `rng.permutation(tr)`, so
      the RNG stream is untouched (common random numbers against D_fix). Two shares, p = 1/3 (about 200 real rows an
      epoch, a tenth) and p = 1/10 (about 60, a thirtieth). Run names `P2b-dfixp33`, `P2b-dfixp10` (all labels) and
      `P2b-dfixp33-k{k}`, `P2b-dfixp10-k{k}` (folds; the `-k` keeps p10's fold 0 apart from a p100). Everything else
      as D_fix: inputs (the stored `dfix/inputs`, no rebuild), seeds, early stopping on NS, readout. The training
      log adds the loss on plugin rows and on real rows apart (zero cost).
    - **Guards and known answers (code, with tests).** D_fix's guards carried to the D_p names: the backed input and
      fold-wise read for each D_p name, the all-labels D_p refused on BKS by name, fold models taken from D_p's own
      prefix, goat-predict's names. Tests: the show-draw is seeded and its rate is p; the variant of a shown row does
      not depend on being shown; at p = 1 the per-epoch batch index sequences equal D_fix's and `inputs_sha256`
      equals the stored D_fix value (`2311bcb5…`); the fold names never collide.
    - **Stage A (the cheapest deciding read).** The two all-labels models, 2 seeds each (4 trainings, under an hour
      of MPS). Read 1 at the true amp only: FS and NS on P2b's inputs and on P2d's stems, against W's stored renders,
      answered as D_fix was (4 tags × 240 = 960 renders), each report saved by label. In the same sitting about 20 of W's
      stored renders are rendered again and their audio hashes asserted equal (W's renders are same-day and same-code,
      but render processes carry state). Beside, zero renders: D_p − D_fix (the dose response, from D_fix's stored
      renders) and each seed's best epoch. Gate per share: D_p − W not decided worse on FS or NS on
      P2b's inputs. The share carried on is the larger one that passes; if neither passes, stop: the real rows in
      this joint recipe cost the plugin read at every share tried, and the user decides between domain work, more
      real chains, and keeping real-amp reading out of the mix model (no more D_fix renders). A pass by "not decided
      worse" on 6 FS bands is weak, and the interval excludes seed variance: a pass near the boundary may be seed
      noise.
    - **Stage B (the chosen share, as D_fix was read).** Read 1's mismatched amps for D_p against W's stored renders
      (480 renders); the 8 fold trainings; read 2 as declared (BKS backed and clean, GOAT beside; about 1,820
      renders). The map is D_fix's: read 1 decided worse at either mismatched amp, or read 2's D_p_k − Rcs2 decided
      worse, and D_p is not built as is (no V-real; a new declaration, with no fallback to the other share without
      one); otherwise reads 1 and 2 are written up, reviewed, and read 3 (V-real, as declared) runs on D_p. D_p_k −
      D_fix_k is reported beside (zero renders). A D_p that simply converged to W would fail read 2's gate: models
      without real rows read about 0.2 worse than Rcs2 on BKS (P2a − S +0.066 against Rcs2 − S about −0.17).
    - **Selection.** Stage A chooses the share on read 1's true-amp rows, so those rows are optimistic for the chosen
      share (two candidates); stage B's rows and V-real are not selected on. The stem rows stay beside, never a gate:
      F39's stem result is not used to move the gate after the fact.
    - **Budget.** About 3,280 renders (A 960 and the W check about 20; B 480 + 1,820) and about 3 h of MPS (4 + 8
      trainings, shorter epochs), within this approved plan; V-real (about 700) is outside it. D_fix's read 2 rendered
      1,820 against the declared 1,390 (GOAT 860 against about 430: 4 renders per unit, both answer halves each on both audio halves).
    - *Review (2026-11-02, independent, before any code of the amendment):* approved with required changes, all made:
      the show-draw on its own seed key, the filter after the permutation with a batch-sequence known-answer test,
      the guards carried to the D_p names (with `-k` fold names), read 1's reports saved by label, a W render check in
      stage A's sitting, the budget lines. Adopted from its suggestions: D_p − D_fix and best epochs beside, the
      convergence-to-W note, the seed-noise note, D_p_k − D_fix_k beside.
  - *D_fix to V-real (2026-11-02, after F40, before any V-real read or code for it; ledger `phase_dfix_vreal`).*
    - **Why the gate changes.** The user (2026-11-02), on F40's choice: "I'm general well always have real-amp
      recording. What do you suggest?" The product always reads real amps; the plugin read (read 1: FS and NS, plugin
      renders with known settings) is the only read with exact answers, and it was a veto. For this step it becomes a
      cost reported beside, not a veto. This is a change made after read 1 was seen; it is made at the user's product
      direction, before any V-real read, and the plugin cost stays recorded (F39) and is the next fix's target.
    - **The one candidate.** D_fix as built (`P2b-dfix`, all labels, both seeds pooled, NS-best). It was chosen on
      reads 1 and 2 only, among D_fix, D_p33 and D_p10, before any V-real read: the best real-amp read of the
      three (BKS D_fix_k − S −0.122 [−0.222, −0.021], level with Rcs2; on P2d's stems NS better than W −0.051 and
      than S −0.077), where D_p10 lost the real-amp read (read 2 decided worse) and D_p33 has no real-amp read (stage
      A ended its line before read 2; under this step's rule its plugin cost alone would not exclude it) (F40).
      D_fix is the only one of the three with a read 2 that did not fail. V-real is fresh for it. The write-up labels
      it "D_fix (read 1 failed; gate relaxed at the user's direction)".
    - **Read 3 as D_fix declared it, with W's rows beside added:** the input the X-LANCE stem of each V-real-11
      part's mix, as the product reads a song: the crop's mix brought to the self-built mixes' median loudness
      (`levels.json` `eval_mix_lufs_median`, −12.25 LUFS: the drawn level P2d's stems were separated at, and step 4's
      and T3's V-real rule, `step4_half`), the stored crop-only stem given the same gain (X-LANCE ran on the crop at
      its own level; not re-separated); D_fix's plain readout − S primary (band-weighted, 7 bands, Wickerman ElecGtr2 and 3 one part, the
      established V-real rule); beside, P2b-wide24 on the same stems (W − S and D_fix − W: what the real rows add on
      real songs), RcG (Rc's rule on every GOAT label of the amp and class; S where there is none, counts reported)
      and the S-centred readout (D_fix's stem answer re-centred by `sc_cont` on the constant of D_fix's plugin
      training labels, P2b-wide24's ids), and the parts' own amp tracks (D_fix on the amp track − S; in the
      amp-track row Wickerman ElecGtr2 and 3 are two parts, each its own amp track, as P4, one part beside; and
      D_fix on the amp track − P4, F20's stored answers, zero renders); clean and crunch apart, part-weighted beside,
      leave one band out. Colour Me Red ElecGtr02 and 03 (Diesel13), X-LANCE's known stage F failures, stay in the
      primary as the product would read them; leaving one band out shows the read without Diesel13. The quiet-input
      side row (over 20% of frames at the grid floor) is computed on the stem inputs. As P4 (`vreal_rows`): a
      direction where S is not judged finite drops for every row; a refused answer scores as S; every declared
      direction is rendered before the read, and an incomplete row is not read. "Decided" means the 90%
      band-clustered interval excludes 0; the class rows (2 clean bands) are descriptive only.
    - **Renders:** D_fix on the stem, W on the stem, D_fix S-centred and D_fix on the amp track, 4 × 132; RcG 66;
      S re-rendered, 66, with phase 4's stored render hashes asserted equal: 660, as every Morgan render. S's
      positive control must pass on the S renders the report reads. A mismatch with phase 4's hashes stops the read
      before any row is computed; the cause is found and recorded.
    - **Map, declared now.** D_fix − S decided better: the pipeline beats the plugin's own start on held-out real
      songs for the first time; the proposed next declarations are domain work (the user's option since F37; first
      proposal: D_fix's rows with a per-row input saying plugin render or real amp, to win back the plugin cost
      without losing the real-amp read) and the scale step, each reviewed. Undecided or worse: the same domain work
      is proposed next, every read as evidence; the user's choice stays open either way. D_fix − RcG is reported
      beside: if D_fix − S is better while D_fix − RcG is not, the win is stated as a real-amp centre's (F38), not as
      a per-track reading. Beside and descriptive, not acted on: a decided loss on the stems with the amp-track row
      near S points at the separator. This map replaces D_fix's read 3 map (scale after a win; the user's choice
      after a loss). V-real is read once; any later choice that uses it is labelled selection-contaminated.
    - **Power.** V-real-11 has 7 bands and 10 parts (66 directions); P4's intervals were about ±0.11 band-weighted,
      so an effect below about 0.1 may stay undecided, and the stem rows may be noisier (Diesel13's separator
      failures), so ±0.11 is a lower bound on the width; undecided is reported as undecided, not failed.
    - **Guards (code, with tests).** Known answer: one FS example's stored `xlance_g-cc` half, fed through the
      V-real input path at 0 dB, gives exactly `RungData`'s X and C for it; the target level is read from
      `levels.json` and asserted −12.25; the V-real stems' half LUFS are reported beside P2d's stored stems' (median
      about −14.7); the amp-track row reads at D_fix's own training inputs' median (`model_input_lufs`, rung b, about
      −13.7). The answers refuse any model but the declared ones; no V-real band or song in any D_fix training input
      (plugin rows' sessions, BKS and GOAT real rows, BKS's own-section backings and the 24 pool backings; asserted
      from the run files and `dfix/inputs`'s records); renders only after the answers' file hashes are in the
      ledger.
    - *Review (2026-11-02, independent, before any code):* approved with required changes, all made: the candidate's
      reason (D_p33 has no read 2), the input level (step 4's −12.25 LUFS mix rule, the stem given the same gain) and
      its known answer, the Wickerman parts in the amp-track row, the X-LANCE failure parts, the refusal and missing
      rules, RcG and the S-centred readout defined, the exact render list (S re-rendered, hashes asserted), the
      D_fix − RcG interpretation rule, the next step named as domain work with the user's choice open, the leakage
      guard over every training input and backing. Adopted from its suggestions: D_fix on the amp track − P4, the
      write-up's label, the separator reading, the power note. Its re-check approved (2026-11-02), with the S-mismatch
      rule adopted.
  - *Fine-tuning on the real rows (2026-11-02, after F41, before any code or render of it; ledger `phase_ft`).*
    - **Why.** The user (2026-11-02), on the per-row plugin/real input proposed after F41: "Why should the model
      distinguish between plugin renders and real-amp recording? Plugin renders will never be its input on actual
      use, can't we use them as pre training for higher accuracy instead?" The product never reads a plugin render,
      so the plugin read is not a goal in itself; in the joint recipe the real rows and the plugin rows compete (F39,
      F40), and every D_fix checkpoint was chosen on NS, a plugin loss, never on real amps (F40's caveat). Here the
      plugin renders are pretraining only: P2b-wide24 (W), trained on plugin renders alone, is the starting point,
      and the real rows alone tune it, with the checkpoint chosen on held real rows.
    - **The one candidate, FT.** For seed s, W's NS-best checkpoint (`P2b-wide24-{s}-best.pt`, its hash checked
      against its run file), then D_fix's real rows only: the same labels (BKS stage 1–2 and GOAT), the same inputs
      (`build-dfix-real`'s 25 backing variants per unit, one drawn per epoch by `dfix_variant`; the inputs hash
      asserted equal to D_fix's), the same per-epoch counts (as `dfix_records`: BKS cycled to 300, GOAT to 300, an all-labels list
      longer than that kept whole), and no plugin rows in
      training. A fresh Adam at 1e-4 (a tenth of the pretraining's 1e-3, the one tuning choice, fixed now), batch 64,
      gradients scaled to norm 5, as `fit`; the training RNG (torch and the permutation) seeded with s. Nothing else
      changes: the network, the input, the readout. The network's BatchNorm statistics move toward the real rows too;
      that is part of the tuning, and the NS log shows its plugin cost.
    - **The epoch count, chosen without the read fold (nested).** FT_k (read on fold k) never sees fold k's real rows,
      in training or in choosing. Its inner run does not load fold k's rows at all; it trains from W on the folds
      other than k and j = (k + 1) mod 4 and computes, every epoch, fold j's real-row loss: `head_losses`' total
      (`F.loss_fn`) on variant 0, pooled by row over fold j's BKS and GOAT rows (W's start state's value logged as the
      reference). Up to 100 epochs, stopping after 15 epochs without a fall of 0.001 in the trailing 3-epoch moving
      average (epochs e−2..e; epochs 0–1 average what exists); E(k, s) = e + 1 for the e where that average is
      lowest. FT_k is then trained from W on the three folds
      other than k for exactly E(k, s) epochs and the state after E(k, s) epochs is the model read; no choice is made
      on fold k. The all-labels FT (V-real's) trains on every label for the median of the eight E(k, s), rounded half
      up. **Fallbacks, declared now, on inner validation only and before any FT_k is trained (recorded):** if 4 or
      more of the 8 inner runs end at the cap, the cap is raised to 300 and the inner runs continued (re-run
      from W with cap 300 on the same seeded stream, under their own names; the code review's reading, since an inner
      run keeps no state); if 4 or more
      have E ≤ 2, the rate is lowered to 3e-5 and the inner runs repeated; the rate rule is checked first, then
      the cap, each applied at most once. Logged in FT_k's run, never for choosing
      and never `fit`'s tracked set: NS loss (the plugin cost) and fold k's real-row loss every 5 epochs. Trainings:
      8 inner + 8 FT_k, and 2 all-labels only if V-real is reached; about 1 h of MPS in all (more if a fallback is
      taken). Caveats, stated now: with two folds out the inner run repeats each row more often per epoch (about 2.7
      times against FT_k's 1.4–1.9), so E is likely biased low (conservative); fold 3 holds only 24 BKS rows, so the
      inner validation for k = 2 is mostly GOAT.
    - **Read 2, as D_fix's (F39), each BKS unit by its DI's fold model and each GOAT unit by its item's, both seeds
      pooled, plain readout, the backed input (variant 0, a BKS unit's own section's backing):** primary, FT_k −
      D_fix_k on BKS's 40 units (by DI, 8 DIs) and on GOAT's 215 (by item, the fold interval beside): does tuning
      from plugin pretraining beat the joint recipe? GOAT is co-primary here, where in D_fix's map it was beside:
      D_fix's question was BKS adoption against Rcs2 with the plugin read as the gate, while this one is the recipe
      against the recipe, and GOAT's 130 items (capture renders, not real rigs) are the larger and tighter of the two
      sets; BKS is real amps but one band. Two chances at "decided better" at 90% give up to about 10% false carries
      under the null; the write-up says so. Beside: FT_k − Rcs2, FT_k − S, FT_k − RG, GOAT FT_k − RcGk (a
      per-track reading if decided better), better counts by DI, unit and item. The clean amp-track read is not run
      (the product reads songs). "Decided" means the 90% interval excludes 0.
    - **Renders:** BKS 480, GOAT 860; 20 of D_fix_k's stored read 2 renders re-rendered and asserted identical
      before any row is read: 1,360. If V-real is reached: FT on V-real-11's stems, 132, and 20 of phase 4's S renders
      re-rendered and asserted identical: 152. At most 1,512, as every Morgan render.
    - **Map, declared now.** Neither primary row decided worse and at least one decided better: FT is carried to
      V-real, one read, exactly F41's read 3 input and rules (the X-LANCE crop stems, the crop mix at −12.25 LUFS and
      the stem given the same gain, band-weighted over 7 bands, Wickerman ElecGtr2 and 3 one part, `vreal_rows`'
      drop and refusal rules); FT − S primary, FT − D_fix and FT − RcG beside from F41's stored renders (zero new);
      written up as "FT (second candidate on V-real; D_fix was the first, F41)". Otherwise FT is not read on V-real;
      the result is written up and the next step proposed for the user (for example a share of plugin rows kept in
      the tuning, or a different rate, each a new declaration). On V-real, FT − S decided better at 90% is reported
      as a win on the second candidate read, with the two-look (Bonferroni) 95% interval beside. Then: FT − S better:
      FT replaces D_fix as the model carried forward, and the scale step or domain work is proposed; undecided or
      worse: the user's choice. FT − D_fix is reported beside either way; any choice between FT and D_fix made from
      V-real's FT − D_fix row is labelled selection-contaminated. If FT wins, the write-up says it changed two things
      at once (sequential tuning, and an epoch count chosen on a real loss instead of NS): it beats the joint recipe,
      not shown to be pretraining alone.
    - **Selection.** FT is chosen on read 2 only. The idea came after F41 (the user's question on the recipe, not on
      F41's numbers per band), so V-real is fresh for FT as a model but no longer for the plan: two candidates will
      have been read on it, and the write-up says so.
    - **Power.** Read 2's BKS rows had intervals of about ±0.05 (D_fix_k − Rcs2), GOAT's about ±0.02 by item; a
      difference from D_fix_k below those may stay undecided, reported as undecided, not failed. V-real's as F41
      (about ±0.07).
    - **Guards (code, with tests).** FT_k's training rows and its inner run's rows hold no fold-k real row (asserted
      from the run files); the inner run's training rows hold no fold-j row; FT_k's and the all-labels FT's run files store the state after exactly E epochs as the read checkpoint,
      every read path (BKS, GOAT, V-real) loads that state, and a test asserts the loaded model's sha256 equals the
      final state's; the start state's tensors equal W's stored best (loaded through FT's build path, a test); no plugin row in any FT training order; the inputs hash equals D_fix's on the FT_k and all-labels runs (all units
      loaded), and the inner runs' over their own unit set is recorded; the answers refuse any model but the declared ones; the answers' hashes are in the ledger
      before any render; the V-real leakage guard as D_fix's (FT's sources are W's plugin sources and D_fix's real
      rows, a subset of D_fix's).
    - *Review (2026-11-02, independent, before any code):* approved with required changes, all made: the read
      checkpoint fixed as the state after E epochs on every read path (a leakage trap in the read code's "best"
      load), the cap and rate fallbacks on inner validation only, what the inner run loads and its loss, GOAT's
      co-primary status with the gate's multiplicity, and the V-real map closed (a win on the second candidate read,
      the two-look interval, what follows each outcome). Adopted from its suggestions: the moving-average argmin and
      W's start reference, the E-bias and fold-3 caveats, the seed, the rounding, the per-epoch counts as
      `dfix_records`, and the two-change interpretation. Its re-check approved (2026-11-02) with the
      moving-average wording fix, made; the fallbacks' order and the guard's wording adopted.
  - *FT's score by control group (2026-11-02, after F42, at the user's request; ledger `phase_ft_groups`;
    descriptive).* The user asked whether the score weighs controls sensibly ("drive probably matters much more
    than reverb"). The score is by sound, so a control counts only by what it changes in the audio; this measures
    how much of FT's BKS score each group of controls carries, as the first half of a judge-against-ear check.
    - **Groups** (every settings key in exactly one, by `ftg_group`): *drive* (input gain, the amps' volume and
      power controls, SW50R's master and input mode, both drive pedals, the compressor, the pedal section);
      *tone* (the amps' bass, mid, treble, cut, bright and treble-boost controls, the graphic EQs, the EQ
      section); *cab* (every cab, mic and room control); *effects* (reverb, delay, tremolo, doubler, the amps'
      springs and the FX section); *other* (the gate, output gain, transpose, the amp section).
    - **What can be measured here** (`ftg_change`: only what can sound, the selected amp's keys and switched-on
      modules, a gate threshold only with the gate on): FT moves drive, tone and cab in all 240 answers (mean unit
      move 0.120, 0.033 and 0.101). Effects and other are null by construction: delay, reverb and tremolo are off
      and the amps' springs at 0 in both S and FT on every answer, and the gate is off on every answer (its
      threshold differs in 126, inaudibly). So only drive, tone and cab are swapped, and **this study cannot say
      how the score weighs reverb or other effects**; that question goes to a matched-step probe on S with an ear
      page on the same pairs (each group moved by an ear-sized step, the judge's change beside the ear's), declared
      after these rows. The compressor (34 PR12 answers) is counted in drive.
    - **Hybrids, on FT's BKS read 2 answers** (each unit by its DI's FT_k, 40 units, 3 amps, 2 halves): for each
      group g, *rev-g* is FT's answer with g's keys set to S's (the unit's class S) and *add-g* is S with g's keys
      from FT's answer; select is S's and FT's (asserted equal). 6 tags × 240 answers, 2,880 renders with their
      priming renders, through `real-render` as read 2 (S's stored renders and lags reused); the answers'
      hashes in the ledger before any render, enforced in `real-render` and `real-report` (`ftg_unhashed`).
    - **Rows** (`real-report`, by DI, 8 DIs, 90%): FT − S (the total, read 2's −0.177, reproduced); per group
      FT − rev-g (negative: the group's change from S helps the score) and add-g − S (negative: that change alone
      helps); FT − S minus the sum of the three add-g − S (the interaction), clustered the same way, beside;
      per amp beside (read 2's FT − S: PR12 −0.154, SW50R −0.209, AC20 −0.167). Per group, the share of
      answers it changes and its mean unit move, so the score's effect is read per amount of change.
    - **Reading.** Descriptive; no gate. It says which groups the score credits FT for, and by how much. A
      group that carries much of the score while its change is small to the ear, or the reverse, is a candidate
      for judge mis-weighting; the second half is a short ear page on the largest-effect pairs per group (the
      same unit, S against add-g), declared with its reader after these rows. V-real is not read.
    - **Renders** 2,880 (about 35 min, 3 processes); every render as declared for Morgan.
    - *Review (2026-11-02, independent, before any render):* approved with required changes, all made: count only
      what can sound and report each group's unit move; state that effects and the gate are null here and what
      this cannot answer; drop the two null groups (1,920 renders); enforce the ledger hashes in code. Adopted:
      per-amp rows, the interaction row with its own interval, the phase listed explicitly, the tests.

  - *The judge against the ear, control by control (2026-11-02, at the user's request; ledger `phase_judge_ear`;
    descriptive).* The user: "some effects, like drive, probably matter much more than others, like reverb; same
    for any control". The score is by sound, but whether it weighs each kind of change as the ear does was never
    measured: the judge spec checks that each change costs more as it grows, and the ear agreed with the judge on
    differences of 0.05 and more between presets, not per kind of change. `phase_ft_groups` cannot answer it for
    effects (off in S and FT on every BKS answer).
    - **Pairs.** One verified clean DI of single-note lead playing (Ale Lak "Nosso Mundo Deixou De Existir"
      ElecGtr05, 110–120 s, the v2 listening page's stand-in; neither V-real nor NS), at −22.9 LUFS, through two
      starting presets: S clean on PR12 and S crunch on SW50R. On each, six groups moved from S one at a time,
      two step sizes each (small, large): *drive* (input gain +4 and +10 dB); *tone* (the amp's treble +0.15 and
      +0.35 in unit range; amended after the first measure, where both crunch tone pairs equalled S, and before
      any ear answer: down by the same where up would pass the top, as on SW50R crunch, whose treble sits at 1.0); *cab* (the left mic's distance +0.25 in unit range; the left mic type
      changed); *reverb* (the reverb module on, mix 0.15 and 0.40, its other controls at the plugin's
      defaults); *delay* (the delay on, mix 0.15 and 0.40, defaults otherwise); *spring* (the amp's spring
      reverb 0.2 and 0.5). 24 pairs (S against S + step) and 2 catches (S against itself, rendered again).
    - **Measures.** The judge's distance between the two renders of each pair (S's render as the reference, the
      same DI, `aligned_distance` as the read uses it, both halves averaged); a catch must score 0 (the renders
      bit-identical). The ear: a blind, guitar-only page with an instant A/B switch, each pair played in seeded
      order, the question "how different do these sound?" (same / barely / clearly / very), sure or unsure.
    - **Reading.** Per group, the ear's rating beside the judge's distance. The judge mis-weights a group if its
      pairs that the ear calls clearly or very different sit at judge distances below another group's pairs the
      ear calls same or barely (or the reverse): that group's weight is then proposed for change, as a new
      declaration with its own check. Otherwise the judge's weighting stands, and the per-control question is
      closed on these two presets. One listener, one DI, two presets: descriptive.
    - **Renders** 2 × (13 + 1 repeat of S) kept renders, each in its own fresh primed process: 56 with priming.
      Every render as declared for Morgan. Code `learn/judge_ear.py`; page `~/ndsp-presets/listening/judge-ear/`,
      its key outside the page.
    - *Review (2026-11-02, independent, after the amendment and before any answer):* approved with required
      changes, all made: the page rebuilt after the final measure and refusing audio `measure` did not judge; the
      amendment's order stated; the amendment required and recorded in the plan. It recomputed all 24 distances
      (identical), checked the catches bit-identical, lag ±4 samples (≤0.2%), the reference swap (≤4% but one
      pair, no order change) and the page's blindness and levels. Adopted: per-half, same-preset and ratio flags on
      each inversion, a catch heard as different flagged. Caveats for the write-up: "reverb" is the plugin's
      default 1.48 s room; a cab step moves the left of two blended mics; the judge skips the first second.
    - *Recheck on headphones (2026-11-03, after F44, ledger `phase_judge_ear_recheck`; descriptive).* The user
      heard the first page on phone speakers, which reproduce little of the low and low-mid range where drive and
      the amp's tone act, while reverb tails stay audible. Three measures tried since (the judge, CDPAM and Zwicker
      loudness, exploratory, `judge-ear/explore/`) all put the treble steps among the largest changes on the page,
      against the ear. Before a judge revision is built on F44, the ear half is re-heard on headphones.
      - **Pairs.** The same renders and clip rule, 13 items in a new seeded order (`RECHECK_SEED`): every pair in
        one of F44's inversions (clean treble +0.35, twice as a consistency check, and +0.15; crunch treble −0.35;
        drive +10 dB on both presets; reverb 0.40 on both; delay 0.40 on both; clean spring 0.5), clean drive +4 dB
        as a low comparator, and the clean catch. The page asks for headphones at a comfortable level.
      - **Reading.** Per pair, the headphone rating beside the phone one, and the declared mis-weighting rule rerun
        on the recheck's rows. If no pair heard clearly or very different sits below another group's pair heard
        the same or barely, F44's inversions are put down to playback and no judge revision is proposed on them;
        if they persist, F44 stands and the revision goes ahead (declared and reviewed). Both of the repeat's rows
        enter the rule; if they differ, that is reported as a reliability caveat beside the result, and the catch
        likewise. "None left" clears only the pairs re-heard; pairs not re-heard could form new inversions. One listener, one sitting: descriptive. Bias caveat:
        the listener was told, before this page, that the measures rank the treble steps large.
      - *Review (2026-11-03, independent, before the page was sent):* approved with one required change, made:
        the two effect pairs in F44's inversions (crunch delay 0.40, clean spring 0.5) added; the repeat's place
        in the rule declared. Adopted: the low comparator, the subset caveat, the seed's name in the key.
      - **Renders** 0. Code `learn/judge_ear.py` (`page --recheck`, `score --recheck`); page
        `~/ndsp-presets/listening/judge-ear-recheck/`, its key outside the page.
  - *The judge revised to weigh changes as the ear does (2026-11-03, after F44 and F45; ledger `phase_judge_ear_v4`;
    descriptive, for this one listener).* F44 and F45: the judge scores the treble steps, which the ear hears as the
    same or barely different on headphones, above reverb, delay and spring changes it hears clearly; CDPAM and
    Zwicker loudness rank the treble steps the same way, and a first modulation-spectrum try did not help
    (exploratory, `judge-ear/explore/`). What the treble step does, measured on F44's clips (exploratory; the
    judge scores only bands within 30 dB of the reference's long-term peak, which stops near 6 kHz on these
    clips): once level is matched, as on the page and in the judge, it is a tilt in the loud bands (clean +0.35:
    about −5 dB near 350 Hz and +4.5 dB near 5 kHz per mel band), not a change in quiet bands. Reverb leaves the
    long-term spectrum within 0.2 dB and acts over time. So either this listener, on this page, hears
    loudness-matched tilts of that size as about the same, or the judge misses what time effects add, or both. The
    stages below take the cheapest decisive step first.
    - **Stage A (zero plugin renders).**
      - *Tonal anchors (an ear page, about 5 minutes, headphones).* S's stored F44 renders with a plain offline
        EQ of known size: RBJ shelves (Audio EQ Cookbook, slope S = 1) at 250 Hz (low) and 3 kHz (high), applied
        to S's render before each clip is set to −23 LUFS on its own (the page's clip rule). PR12 clean: high +3,
        high +6, high −6 (darker), low −6, and high +12 (a positive control that should be heard); SW50R crunch:
        high +6, low −6, low +6 (darker), high −3. Each against S; with the clean reverb 0.40 pair (known heard)
        and one catch: 11 items, seeded order, the same blind page, nothing naming a control. J0's distance on
        each anchor is reported beside its rating (zero renders), to place the anchors against the treble steps on
        the judge's own scale. Reading, per item and summarised per shelf type and preset: (a) if the +12 dB
        control is heard as the same or barely, the page or the bias, not the judge, is the problem: stage B
        waits and the user is asked; (b) otherwise the anchors' ratings join the rated items J2 is fitted on (all
        outcomes), so the fit reflects how this listener hears steady tonal changes of known size; and the count
        of 6 dB anchors heard clearly or very (of 6) is reported: 4 or more, steady tilts of that size are heard
        and the treble steps' "same" is specific to them (stage B keeps F44's tone sizes); 2 or fewer, they are
        not heard on this page (stage B's tone steps doubled in unit size, so a tone pair can be heard); 3, mixed,
        F44's sizes kept and the split reported. Bias caveat: the listener knows the hypothesis (the judge
        over-counts treble; effects are heard); the page names nothing.
      - *Candidates screened in-sample* on F44's and F45's stored renders and the anchors (F45's 12 re-heard
        items count once each, with their headphone rating; F44's others with their phone rating, flagged).
        - J1: J0 (the default judge: its frame sizes, floors and band set unchanged) with each scored mel band's
          |ΔdB| weighted by the reference's loudness share in it: Zwicker time-varying loudness (`mosqito`
          `loudness_zwtv`, free field) on the reference only, scaled so its RMS is 70 dB SPL (re 20 µPa); the
          time-averaged specific loudness per 0.1 Bark bin summed over the bins whose centre frequency falls in
          each mel band, normalised over the scored bands. The reference only: excess a render adds in a band
          quiet in the reference counts little (an asymmetry, stated).
        - J2: w_t × J1's tonal part + J1-weighted frame-wise residual (weight fixed at 1) + w_d × a decay part.
          Note ends: the judge's DI playing mask (DI frames within 40 dB of its peak, the middle frame size) going
          from playing to not playing. The decay window: min(1.5 s, time to the next onset). The decay part, per
          band: the render's energy in the window over the note's own, against the reference's, in dB, mean |Δ|.
          Two weights (w_t, w_d), fitted by grid (w_t 0–1 in 0.1, w_d 0–2 in 0.1) to the highest in-sample
          cross-group gamma, ties to the larger w_t and the smaller w_d. J2-fallback: the decay part dropped and
          w_t refitted alone, frozen as well; used when the stage B DI has fewer than 8 note ends with a window
          of at least 0.3 s, counted on the DI before any render. A strummed chord DI will likely trigger it.
        - Reported per candidate: in-sample cross-group gamma, the distinct inversions left of F45's 21, and of
          the 8 within one preset on both halves. A candidate stays one for stage B if it leaves fewer of those 8
          than J0; otherwise it is a reported control. In-sample results carry no verdict.
    - **Stage B (the fresh page, the verdict; declared as its own amendment after stage A, with the exact pair
      list, before any render).** A verified clean chord DI from the trusted set (neither V-real nor NS; named
      with its verification in the amendment), two starting presets other than F44's (AC20 clean, PR12 crunch).
      Each pair, its settings and its step size listed; sizes from plugin units or F44's sizes, never from any
      candidate's distances; any amendment only on a rule that does not depend on the candidates (as F44's: a
      render equal to S). Effect parameters (reverb decay, delay time) compared against the module on at its
      default, so a pair changes one thing. S's effect and spring states stated. The page fits about 10 minutes;
      the anchors repeated there. Code and parameters of every candidate hashed in the ledger before any fresh
      render is measured.
    - **Reading (stage B).** Primary: cross-group concordance with the ear (Goodman–Kruskal gamma over item pairs
      from different groups with different ratings; it generalises the inversion rule), per candidate, with a 90%
      interval from resampling clusters of group × preset (about 14–18; the percentile interval may under-cover
      with this few, stated). Pooled Spearman and Kendall's tau-b reported beside; catches left out; a repeat's
      two ratings averaged. J2 (or J2-fallback) is the primary candidate, J1 secondary, J0 the control; CDPAM (J3) a reported
      control only (torch, 22 kHz, trained on speech). J2 is adopted if its gain over J0 has an interval above 0;
      else J1 by the same rule; otherwise undecided. A rough power check gives about a 50–55% chance of a decided
      gain if J0's mis-weight per group equals the spread of group audibility: undecided is a likely outcome. If
      undecided: one more page of the same design with a new DI and presets, pooled with this one by the same
      statistic over both pages' clusters, and then a stop (two pages at most) with the effect sizes reported.
    - **Before any adoption:** the new judge passes the judge spec's tests (catches 0, distance grows with step
      size, alignment and level handling, refusals), and its agreement with the ear on whole-preset differences
      (the stored listening answers, zero renders, each study's own statistic) minus J0's has a 90% interval not
      wholly below 0. Adoption changes the default with the old judge
      kept by name. Re-scoring past reads, and re-checking the starting presets and the models under it, are each
      declared on their own with render budgets.
    - **Renders** stage A 0 (the anchors are offline EQ of stored renders). Stage B: 2 presets × (about 17 steps + S + S again) about 38 kept renders, about 76
      with priming, plus the reverb-on and delay-on default references (about 2 per preset); recounted in its
      amendment. Every render as declared for Morgan.
    - *Review (2026-11-03, independent, two passes, before anything ran):* approved after required changes, all
      made: the mechanism corrected against J0's own bands and level matching (the first draft's "quiet bands"
      reading was wrong); a zero-render stage A first (the anchors and an in-sample screen); the statistic
      (cross-group gamma, group × preset clusters), power and the two-page cap; J2 primary, CDPAM a control only;
      the spec tests and the whole-preset agreement before adoption; every anchor outcome's consequence; a
      positive control and darker anchors; J1, J2 and J2-fallback specified; the render count.
    - *Stage A's outcome (2026-11-03, F46):* steady 6 dB tilts not heard on this page (1 of 6); J1 and J2 leave
      all 8 within-preset inversions, so both are reported controls and stage B is not run as declared.
  - *The combined judge (2026-11-03, after F46; ledger `phase_judge_v5`; for one listener, checked on a fresh
    page).* The user: the goal is the most accurate preset with no human in the loop, so the judge cannot stay with
    F46's limit and ear checks are for development only; a strong go-ahead for an automatic judge that adds a part
    for what time effects add. **What the stored renders already show** (exploratory, zero renders, in-sample on the
    33 rated items, `judge-ear/explore/`): a DI-to-output envelope response and band coherence do not separate the
    effects from the clean treble steps (both score the treble steps at or above reverb); a smoothed spectrum (DCT 2–8
    across the bands) leaves the treble steps' tonal size at that of a 9–12 dB shelf; but a *carry-over* measure
    separates them by sign: per band, the render's excess over the reference regressed on how far the reference has
    fallen below its own recent peak, level partialled out. In its declared, antisymmetric form (below) it scores
    reverb, delay and spring +0.02 to +0.24 (all positive) and the treble steps, drive, cab and every shelf −0.06 to
    +0.003; one-way, swapped (the wet side as reference), it flips sign at about two thirds the size. The declared
    fit (`judge_v5 screen`, `judge-ear/v5-screen.json`, run with this declaration) gives w_c 8: in-sample gamma
    +0.519 (J0 +0.449), 3 of the 8 within-preset inversions left (J0: 8) and 7 of F45's 21; of the 18 inversions
    with an effect heard above a tone or drive pair, 14 are removed, the 4 left all below clean treble +0.35, and all
    3 with crunch drive +10 dB (heard clearly) stay. J5 uses |C|, so the sign's separation is lost in part: |C| on the
    tone and drive items (0.01–0.07) overlaps the small effects' (crunch reverb 0.15 0.020, crunch spring 0.2 0.022),
    and clean treble +0.35's |C| 0.058 adds 0.46 to its score, which keeps 2 of the 3 within-preset inversions left.
    w_c is weakly identified: gamma stays within 0.02 of its best for w_c 4–13, and leaving one group out gives w_c
    from 3 (tone) to 20 (anchor, spring). In-sample, the declared bootstrap below (14 clusters) gives J5 − J0 +0.07
    [−0.037, +0.217]: by this page's own rule even the fitted J5 would be undecided here. The treble steps and clean
    drive (scored high, heard same) are not fixed. A loudness-matched
    third-octave look says the clean treble step is not a steady tilt: a 5–7.5 dB dip at 200–315 Hz and a 2–5 dB
    lift above 3 kHz, with a frame-wise part 4–10 times a shelf's of the same tonal size. Long-term Zwicker
    specific loudness and DIN sharpness (mosqito) also put clean treble +0.35 between the +6 and +12 dB high shelves
    (11.3 sone L1 against 8.7 and 17.9; sharpness 0.20 against 0.15 and 0.30 acum), so no standard model tried
    explains why this listener hears it as the same or barely different.
    - **J5** = J0 + w_c × |C|. C, per window: on J0's own cells at the middle frame size (2048; the floored,
      level-matched log-mel levels it scores, its scored bands), per band, the render's excess over the reference
      (dB) and the reference's decay depth (its peak over the last 1.5 s minus its level now, dB), each with the
      reference's level partialled out (its mean in 12 quantile bins of the reference's level taken away); the
      band's slope of excess on depth; the slopes averaged with weights by the reference's mean power per band.
      C is the antisymmetric mean of that slope with reference and render swapped, (C(ref→ren) − C(ren→ref)) / 2,
      so a swap only flips its sign. C uses every frame of the window (not only J0's scored frames; the depth needs
      the frames between notes), and needs the DI only through J0's masks. J5 averages the two halves as J0 does,
      and refuses where J0 refuses in either direction on either half. w_c: the highest in-sample cross-group
      gamma over the 33 rated items (`judge_v4.screen_items`) on the grid 0–40 in steps of 1, ties to the smaller;
      fitted, frozen and hashed in the ledger before any fresh render. Code `learn/judge_v5.py` (tested: C is 0 on
      a repeat, flips sign on a swap, sees a synthetic reverb, a static tilt scores under a quarter of it, and J5
      refuses where a half refuses). Synthetic checks by the review: stationary noise in the reference at −60 to −30
      dB re its RMS moves C by at most 0.01, a −20 dB swelling pad by 0.016; a delay of 500 against 300 ms gives C
      −0.07 against +0.16 for a 1.5 against 3.0 s decay, so the delay-time pair is expected to rest mostly on J0.
    - **The fresh page (the verdict).** A verified clean chord DI from the trusted set, neither V-real nor NS nor
      F44's DI: The Travelling Band "Quicksand" ElecGtr1 DI (`cambridge/TheTravellingBand_Quicksand_Full/
      16_ElecGtr1DI.wav`), 125–135 s. T0 verified the DI file and part (`verified.json`
      `targets["cambridge-Quicksand-ElecGtr1"]`, verified and heard by ear, on its 120.5–130.5 s crop; not in its
      `v_real` list; `clean_di.refuse_held_out` passes), not this window; the window is one section of the clean-DI
      manifest (`~/ndsp-presets/learn/clean-di/manifest.json`, 125–135 s: clean, no flags, hiss −90 dB; the 120 and
      140 s sections are flagged hiss). Chords, by a listen-free count to be confirmed on the page: median 10
      spectral peaks between 70 and 700 Hz (8192-sample frames, within 30 dB of the frame's top, 10 dB prominence)
      in the loudest quarter of frames, against 2 on F44's single-note DI. 1 note end by F46's detector (C needs
      none), 10 s at −22.9 LUFS with F44's DI rule (mono, soxr VHQ to 48 kHz), through two starting presets other than F44's: S clean on AC20 and S crunch on
      PR12 (`arm_a_mega53.L.menu_S()`). Per preset, each against S unless stated (15 items, 30 in all):
      *drive* input gain +4 and +10 dB; *tone* the amp's main tone control by 0.30 and 0.70 in unit range (F44's
      sizes doubled, as F46's outcome set), up, or down where up would pass the top, clipped to the range: AC20
      `ac20Cut` 0.759 → 0.459 and 0.059 (both down, less cut); PR12 `pr12Treble` 0.535 → 0.835 (up) and 0.0 (down,
      clipped, so the large step is 0.535 and opposite in direction to the small one); *cab* the left mic type to the next (F44's rule); *reverb* on, mix 0.15 and 0.40,
      Default.xml's other values; *reverb decay* reverb on at mix 0.40, decay 1.48 s (default) against 3.0 s;
      *delay* on, mix 0.15 and 0.40, free-running at 500 ms, Default.xml's other values; *delay time* delay on at
      mix 0.40, 500 against 300 ms; *combined* S against S with drive +4 dB, tone 0.30 and reverb mix 0.15 together;
      *anchors* (offline, zero renders) S's render through RBJ shelves, high +6 at 3 kHz and low −6 at 250 Hz; and a
      catch (S rendered again). No spring (AC20 has none; PR12 crunch's spring level and dwell are both 0). The reverb-decay and delay-time
      items reuse the reverb 0.40 and delay 0.40 renders, so some audio is shared across clusters. Groups for the statistic:
      drive, tone, cab, reverb, reverb decay, delay, delay time, combined, anchor. The same blind page, headphones
      asked for, seeded order, nothing naming a control; about 12 minutes. Bias caveat: the listener knows the
      hypothesis (the judge under-counts effects and over-counts treble) and that the judge is being revised toward
      effects; the page names nothing.
    - **Reading.** Primary: gamma(J5) − gamma(J0), cross-group gamma over the fresh page's rated items (catches out;
      the two halves averaged per item), with a 90% percentile interval from 2,000 resamples (`BOOT_SEED` 20261106) of
      the group × preset clusters (18; the percentile interval may under-cover with this few, stated). A resampled
      cluster keeps its group, so pairs between its copies, and between clusters of one group, stay excluded;
      resamples where either gamma is undefined are dropped and counted. J5 is adopted if the interval's lower end
      is above 0; otherwise undecided (not failed), its effect size reported. Power: with about 18 clusters a
      decided gain needs roughly +0.11 or more, and the in-sample gain is +0.07 (above); the review puts the chance
      of a decided gain at roughly 15–30%, so undecided is the likely outcome. Then the user chooses between adopting
      on the evidence and a second page of the same design with a new DI and new presets, pooled with this one over
      page × group × preset clusters by the same statistic, and then a stop. Reported beside: F44's inversion rule on the fresh page for J0 and J5; the effect groups' and
      the tone and drive groups' gammas separately (cab and anchors reported apart); the ratings of the doubled tone steps and the anchors on chords.
      If one or more effect items (reverb, reverb decay, delay, delay time) heard clearly or very sit strictly
      below a tone or drive item heard same or barely on J5's half-averaged scores, a tonal revision is proposed next (declared on its own, fitted on these and the stored ratings, checked
      on another fresh page), since the in-sample work leaves the treble steps as they were.
    - **Before adoption:** the judge spec's tests pass for J5 (a repeat scores 0, distance grows with step size,
      alignment and level handling, refusals), and its agreement with the ear on whole-preset differences (the
      stored listening answers of `docs/measuring-closeness.md`, zero renders, each study's own statistic) minus
      J0's has a 90% interval not wholly below 0. Adoption makes J5 the default with J0 kept by name. Effects off on
      both sides do not make w_c|C| negligible: in-sample it is 0.07–0.53, 6–18% of J0 (clean drive +10 dB: 0.40 on
      2.15), so past reads can move; re-scoring them is declared on its own. *Product check (zero renders), before
      the product's preset search moves to J5:* real references bring room sound and song-stem bleed that moves with
      the playing, which C could read as a missing effect. C is reported on real references with effects off on
      both sides: the `measuring-closeness` trials' amp tracks against their template renders, and T0's dry amp
      tracks against S. Bar: their median |C| below the fresh page's mean |C| of reverb mix 0.15 over its two
      presets; failing it blocks the move.
    - **Renders** per preset S, S again, 2 drive, 2 tone, cab, reverb 0.15 and 0.40, reverb decay 3.0 s, delay 0.15
      and 0.40, delay 300 ms, combined: 14 kept, 28 for both presets, 56 with priming. Every render as declared for
      Morgan (isolate, one priming render, 0.25 s trim, at most 3 processes, the disk guard).
    - *Review (2026-11-03, independent, before any render):* approved with required changes, all made. It
      reproduced the screen (w_c 8, gammas, inversions), C's ranges, the counts and the defaults, and checked the
      code against the text. Required: the DI window moved inside a clean manifest section (131 s overlapped a
      hiss-flagged one) with the verification stated as of the file and part; the power stated (undecided likely)
      and the second page specified; "separates" and "fixes" replaced by the |C| numbers; past reads can move
      (6–18%); a zero-render product check of C on real references with a bar; the tone values listed; C's frames,
      |C| in the docstring and J5's refusal rule; a decidable tonal trigger; the bias caveat; the bootstrap's
      details. Adopted: w_c's weak identification, the delay-time expectation, the shared audio, C's DI use.
    - *Product check's outcome (2026-11-03, zero renders, before the page's answers;
      `judge-v5/product-check/product-check.json`):* 579 pairs from 52 development parts in 19 bands (no V-real or
      NS): real amp-track references against dry plugin renders (K1's searched presets, SET3's template and S), every
      effect off on the render side, aligned as each read did (J0 reproduces the stored values within 4.4e-6). Median
      |C| 0.063 by pair, 0.081 by part, against the bar 0.064 (the fresh page's mean |C| at reverb mix 0.15): a
      nominal pass by pair by 0.001 and a fail by part, so not a pass in substance. The diagnostics say why: |C|
      grows with J0 (Spearman 0.43); two dry renders differing in tone or compressor give |C| 0.02–0.08; the halves
      agree in sign on only 45% of pairs; live-room parts with bleed and parts whose real amp rings on read as
      large; and on the fresh page itself every effect's C sits near 0 on half A (strummed without a fall) and
      shows only on half B (clean reverb 0.15: 0.007 and 0.237). C finds time effects only where the playing falls,
      and on real material it also reads tone, compression, room and bleed. The product's search does not move to
      J5 as built; the page still answers whether adding an effect part fixes the judge's weighting in the plugin
      domain, and a more robust effect part is the next research target either way.
    - *Separator check (2026-11-03, exploratory, at the user's question, zero plugin renders;
      `judge-v5/separator-check/`):* the fresh page's dry and wet renders mixed into 3 phase-5A backings by the
      project's mix rule (−12.25 LUFS, median and upper-quartile guitar ratios, no mastering), separated by htdemucs
      and X-LANCE (xlance_g) as the project runs them. The wet energy survives in the guitar stem: about 75% on
      X-LANCE and 55% on htdemucs (about 90% with a sparse backing, 35–58% on htdemucs against keys or organ); the
      rest goes to the backing's sustained-instrument stem, not lost. But the stem's own error (J0 against the clean
      render: X-LANCE 2.14, htdemucs 3.55) exceeds every effect's clean J0, so J0 barely sees effects through a
      stem; C on X-LANCE stems picks the wet render for mix 0.40, the 3 s decay and delay time in 21 of 24 cases, and
      not the mix 0.15 effects (0–3 of 6), whose size equals X-LANCE's own slight tail trim (C −0.04). One DI, two
      presets, 3 backings, plugin-rendered guitar: descriptive. The robust effect part must be read through stems.
    - *The page's outcome (2026-11-03, F47):* J5 − J0 −0.224 [−0.351, −0.063]: undecided by the declared rule and
      not adopted, the interval wholly below 0. On this chord DI the effects were barely heard (clean reverb and delay
      0.40 barely, the rest the same) while the tone steps and high shelves were heard clearly or very; J0 ranks the
      page well (+0.863). No second page, no tonal revision (not triggered); J0 stays.

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
- **Caveats that apply to every by-sound row** (the audit, 2026-10-31):
  - NS rows use checkpoints chosen on NS's loss, and NS is 2 songs: section-clustered intervals understate
    between-song variance.
  - Intervals cover sample variance, not training variance: one seed against the two-seed pool differs by up to
    about 0.09 (NS, P2a-f50); seed against seed was not measured and is likely larger.
  - About 10 isolated rows are each read at 90%: a row whose interval end sits near 0 carries no verdict.
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
  | NS (383) | final (seed 1) | 14 of 85 | 26 of 28 | 3 of 3 | 6 | −0.0053 [−0.0083, −0.0024] |
  | FS (207) | final (seed 1) | 16 of 85 | 21 of 28 | 3 of 3 | 6 | −0.0101 [−0.0138, −0.0064] |
  | NS (383) | final (both seeds) | 26 of 85 | 26 of 28 | 3 of 3 | 4 | −0.0116 [−0.0138, −0.0093] |
  | FS (207) | final (both seeds) | 23 of 85 | 26 of 28 | 3 of 3 | 4 | −0.0145 [−0.0173, −0.0118] |

  The stored `reads/P2a-final.json` now holds the two-seed read (re-read for F25); the seed-1 final rows above are from
  its first read. `reads/P2a-best.json` stays seed 1 (the answers and the switch rule use it).

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

### F9. Process: removing a worktree crashed running jobs
- Removing the plan's worktree while the doubles render ran from it crashed its 3 shards at a lazy import. They resumed
  from their saved sections with no data lost.
- Long jobs now run from the main checkout (a memory note records the rule).

### F10. The by-sound read reproduces the truth (its positive controls)
- **Result.** For each of the 120 sample examples, its own label was rendered through its own measure DI in a fresh
  primed process. It reproduced the stored target render: judge distance median 1.5e−6, at most 1.0e−4, against S's
  median distance of 5.7.
- **The second control.** The same label written on the class start preset's select, where every answer is written:
  identical results on all 120 (median 1.5e−6, at most 1.0e−4).
- 480 renders in all.
- **References.** `PF/sound/judge/{truth,truth-on-S-select}/`; `cmd_answers --name truth|truth-on-S-select`,
  `cmd_sound_render`; ledger `phase_3_sound`.

### F11. By sound, the model fed the clean guitar gets much closer than S and the average preset (steps 21, 30)
- **Result.** P2a's answers (seed 20261042, NS-best checkpoint) were rendered for the first 60 FS and 60 NS sample
  examples, each through the example's own measure DI. They sound much closer to the known target than S and than the
  constant.
- **Numbers** (log distance ratio; −0.241 is about 21% closer).

  | Row | FS (60, 6 bands) | NS (60 examples, 36 sections, 2 songs) |
  |---|---|---|
  | P2a − S | −0.248 [−0.382, −0.114], 6 of 6 bands better | −0.241 [−0.318, −0.165], 29 of 36 sections better |
  | P2a − constant | −0.252 [−0.372, −0.132], 5 of 6 bands better | −0.247 [−0.310, −0.185], 32 of 36 sections better |
  | constant − S | +0.004 [−0.107, +0.115] | +0.006 [−0.066, +0.078] |

  - By draw mode, P2a − S: FS wide −0.303 [−0.436, −0.171] (25), start −0.281 [−0.634, +0.073] (9), factory −0.170
    [−0.289, −0.051] (26); NS wide −0.254 [−0.355, −0.153] (15), start −0.033 [−0.216, +0.150] (14), factory −0.337
    [−0.453, −0.220] (31).
  - With both seeds pooled: NS −0.237 [−0.312, −0.161], FS −0.195 [−0.321, −0.069].
- **Reading.**
  - Fed the clean guitar, the model reads enough of the tone to sound clearly closer than S, on the two held-out songs
    and on realistic presets.
  - Knob error badly understates this (F6, F7): many settings sound alike (review step 21 confirmed).
  - On the made-up songs the constant and S are about equally far from the targets.
- **Caveats.**
  - The targets are Morgan renders on the true amp: an easier task than V-real.
  - The NS-best checkpoint is chosen on NS's loss; NS is 2 songs, and section-clustered intervals understate
    between-song variance.
  - Intervals cover sample variance, not training variance: one seed against the two-seed pool differs by up to
    about 0.09 (F25).
- **References.** `PF/sound/judge/{P2a-best,S,constant}/`, `PF/sound/report.json`; `cmd_answers`,
  `cmd_sound_render`, `cmd_sound_report`, `log_ratio`; ledger `phase_3_sound`.
- **Changes.** Every model from here is read by sound, not only by knob.

### F12. The readout's pull toward the average costs only a little sound skill (step 26)
- **Result.** P2a's answers were pulled toward the constant exactly as D_CC's readout does
  (`direct_stems.fit_pull_table`, fitted on FS by knob error per (amp, section class); switches and mics plain). The
  pull changes a median 17 settings per answer (at most 30). The pulled answers sound only slightly less close.
- **Numbers.**

  | Row | FS (the pull's fit set) | NS (primary) |
  |---|---|---|
  | plain − pulled | −0.012 [−0.022, −0.001], 5 of 6 bands better | −0.006 [−0.016, +0.004], 20 of 36 sections better |
  | pulled − S | −0.236 [−0.373, −0.100] | −0.235 [−0.311, −0.160] |

- **Reading.** The suspicion that a knob-fitted pull discards sound skill is not supported in distribution: the pull
  is a small cost, not why the old models never beat S.
- **Caveats.** One model and seed; in distribution.
- **References.** `PF/sound/answers/P2a-best-pulled.json`, `PF/sound/judge/P2a-best-pulled/`; `fit_knob_pull`; ledger
  `phase_3_readout`.

### F13. Fed the stem or the mix, the model reads almost nothing by knob, even on seen performances (steps 16, 19, 29)
- **Result.** P2d (D_CC's stored X-LANCE stem; best checkpoint epoch 20 of 60, 30.6 min) and P2c (the self-built mix;
  best checkpoint epoch 5, 12.5 min) used the same recipe as P2a. Their knob error equals the constant's, and they read
  few switches.
- **Numbers** (by knob, R0's rule, best checkpoint).

  | Model | Set | Knobs readable | Switches readable | E − constant |
  |---|---|---|---|---|
  | P2d | NS | 6 of 85 | 4 of 28 | +0.0004 [−0.0004, +0.0013] |
  | P2d | FS | 4 of 85 | 6 of 28 | +0.0000 [−0.0011, +0.0012] |
  | P2c | NS | 4 of 85 | 2 of 28 | +0.0014 [+0.0004, +0.0024] |
  | P2c | FS | 5 of 85 | 4 of 28 | +0.0010 [−0.0002, +0.0023] |

  At the final checkpoint both are reliably worse than the constant on NS (P2d +0.0055, P2c +0.0075).
- **References.** `PF/runs/P2{c,d}-20261042.json`, `PF/reads/P2{c,d}-{best,final}.json`.

### F14. By sound, the stem keeps a sixth to a third of the clean input's skill (the locating row a − d)
- **Numbers.**

  | Row | FS | NS |
  |---|---|---|
  | P2d − S | −0.072 [−0.202, +0.057], 3 of 6 bands better | −0.042 [−0.125, +0.041], 19 of 36 sections better |
  | P2d − constant | −0.076 [−0.198, +0.046] | −0.048 [−0.093, −0.003] |
  | P2a − P2d | −0.176 [−0.222, −0.130], 6 of 6 bands better | −0.199 [−0.258, −0.141], 32 of 36 sections better |

- **Reading.** The stem keeps 29% of P2a's gain over S on FS and 17% on NS: 71–83% is lost between the clean guitar
  and the stem.
- **Caveats.** One seed each; the ladder's set (F8).
- **References.** `PF/sound/judge/P2d-best/`.

### F15. The skill is lost at the mix, not at the separator (the locating rows a − c and c − d)
- **Numbers.**

  | Row | FS | NS |
  |---|---|---|
  | P2c − S | +0.059 [−0.070, +0.188], 2 of 6 bands better | −0.033 [−0.106, +0.039], 19 of 36 sections better |
  | P2a − P2c | −0.307 [−0.363, −0.251], 6 of 6 bands better | −0.208 [−0.265, −0.151], 29 of 36 sections better |
  | P2c − P2d | +0.131 [+0.066, +0.197], 0 of 6 bands better | +0.009 [−0.033, +0.050], 19 of 36 sections better |

- **Reading.** Nearly all of the clean input's skill is gone once the guitar sits in the mix. The separator does not
  lose it further; on FS the stem is better than the raw mix. The separator (the review's leading suspect, step 16) is
  cleared as the place of the loss.
- **Caveats.** One seed each; best checkpoints chosen on NS loss. One seed against the two-seed pool differs by up to
  about 0.09 (F25), as large as some of these rows.
- **References.** `PF/sound/judge/P2c-best/`, `PF/runs/P2c-20261042.json`.

### F16. The doubles fix verified on the data alone (step 12)
- **Result.** In the 604 re-rendered examples:
  - every DT double (980) now carries exactly its target's label (all stored settings) and amp;
  - every other guitar (1,222) keeps exactly its setting, amp, target level and pan. The applied gain differs in 362
    of them by a median 8e−7 dB, at most 0.0021 dB, because the new job order shifts the measured render loudness
    slightly.
- **With** the positive control (46 of 46 replayed examples exact, F3), the new mixes' exact rebuild (P2b parity 0) and
  the unchanged stem SNR, the fix is verified without any model.
- **What remains.** No run uses the re-rendered doubles yet (the ladder is pinned without them, F8); `cc_build`'s
  rule for the next build is unchanged. Both are phase 5's.
- **References.** `PF/cc-dt/rows/render-*.jsonl` against `cc/rows/render-*.jsonl`; `PF/cc-dt/control.json`.

### F17. The backing alone erases the skill; the other guitars add no further loss (the locating rows a − b, b − c)
- **Result.** P2b, the target in its non-guitar backing with no other guitar (best checkpoint epoch 5 of 60, 9.8
  min), sounds no closer than S. Adding the other guitars (P2c) changes nothing further.
- **Numbers.**

  | Row | FS | NS |
  |---|---|---|
  | P2b − S | +0.029 [−0.093, +0.152], 2 of 6 bands better | −0.021 [−0.099, +0.056], 19 of 36 sections better |
  | P2a − P2b | −0.277 [−0.323, −0.231], 6 of 6 bands better | −0.220 [−0.278, −0.162], 32 of 36 sections better |
  | P2b − P2c | −0.030 [−0.122, +0.063] | +0.012 [−0.010, +0.034] |

  - By knob: NS +0.0010 [−0.0001, +0.0021]; 8 knobs and 5 switches readable.
  - By drawn level (P2x − S over all 120 sample examples, terciles of the drawn guitar-to-full-backing ratio, cuts
    −10.6 and −6.5 dB; the 90th percentile is −3.8 dB):
    - P2a: quiet −0.217 [−0.449, +0.015], mid −0.254 [−0.371, −0.137], loud −0.306 [−0.415, −0.198];
    - P2b: +0.121 [−0.047, +0.289], −0.062 [−0.225, +0.101], −0.039 [−0.140, +0.062];
    - P2c: +0.121 [−0.091, +0.334], −0.022 [−0.139, +0.095], −0.021 [−0.103, +0.061];
    - P2d: −0.028 [−0.182, +0.126], −0.104 [−0.262, +0.055], −0.115 [−0.239, +0.009].
  - The mastering draw does not drive the loss: P2a − P2b on NS is −0.258 [−0.341, −0.175] on mastered mixes (33) and
    −0.201 [−0.277, −0.126] on unmastered ones (27).
- **Reading.**
  - The skill is lost when the guitar sits in any backing. In the loudest third the guitar is still mostly below its
    full backing, so level is not ruled out as part of it.
  - A linear probe reads 30 of 116 heads from D_F5's mixes against 86 from the clean guitar (the tone probe), so some
    of the tone is linearly present in the mix.
  - P2b and P2c peak at epoch 5, with their NS loss barely moving (5.58 → 5.44, 5.61 → 5.45).
  - Hypothesis, tested in F24: too few examples to learn to ignore the backing.
- **Caveats.** One seed; 40 examples per tercile.
- **References.** `PF/runs/P2b-20261042.json`, `PF/sound/judge/P2b-best/`; the split from `plan.json`'s
  `draw.ratio_db` and `draw.mastered`.

### F18. Steps 3, 23, 8 and 11 checked on their own
- **Steps 3 and 23 (data check).** NS shares no session, DI or time window with the training sections: 0 of 36
  sections (`pipeline_review.es_overlap` on the recipe's split). FS shares all three, 16 of 21 sections overlapping in
  time. Fixed.
- **Steps 8 and 11** (P2a's per-head losses on NS against the label-only baseline, best checkpoint).
  - The stereo-only heads sit near the baseline: delay width +0.684, ping-pong +0.002, cab pans +0.033 and −0.001,
    cab stereo −0.030 and −0.020, doubler spread −0.036. They cannot be read from a mono input: limit, measured. Stereo
    input is the next build's.
  - Time effects: 3 of their 15 knobs but 3 of 4 switches are below the baseline. Pedals: 1 of 10 knobs and 2 of 4
    switches. Springs: 0 of 3 knobs.
  - Even from the clean guitar most effect knob values do not read, while their switches do: step 8's problem,
    measured on a model that reads. Limit, measured. How much these knobs matter to the sound is not measured here.
- **References.** `PF/runs/P2a-20261042.json` (`heads.best.ns`).

### F19. Told a wrong amp, the clean-input model keeps most of its skill (the amp mismatch, alone)
- **Result.** P2a (seed 20261042, NS-best) was told, and rendered on, each of the two wrong amps, and judged against
  the target rendered on the true amp. It still sounds much closer than S on that same wrong amp.
- **Numbers.**

  | Row | FS | NS |
  |---|---|---|
  | P2a(amp+1) − S(amp+1) | −0.197 [−0.306, −0.089], 6 of 6 bands better | −0.223 [−0.295, −0.150], 28 of 36 sections better |
  | P2a(amp+2) − S(amp+2) | −0.209 [−0.373, −0.045], 5 of 6 bands better | −0.217 [−0.283, −0.151], 30 of 36 sections better |
  | P2a − P2a(amp+1) | −0.065 [−0.108, −0.022] | −0.057 [−0.119, +0.006] |
  | P2a − P2a(amp+2) | −0.071 [−0.114, −0.029] | −0.047 [−0.107, +0.014] |
  | S(amp+1) − S | +0.015 [−0.027, +0.056] | +0.038 [+0.009, +0.067] |
  | S(amp+2) − S | +0.032 [+0.006, +0.059] | +0.022 [−0.014, +0.059] |

- **Reading.** The amp mismatch V-real imposes costs a little (about 0.05–0.07), not the skill: on a wrong amp P2a
  still beats S on that amp by about 0.2.
- **Caveat.** Seed 1 alone; P4 pools both seeds.
- **References.** `PF/sound/judge/{P2a-best-amp+1,P2a-best-amp+2,S-amp+1,S-amp+2}/`,
  `PF/sound/report-{ampmismatch,ampmismatch2,ampvsown,ampvsown2}.json`; ledger `phase_3_isolated` (a).

### F20. On real recordings, even the real guitar alone, no transfer is detected (P4)
- **Result.** P2a (both seeds, NS-best, pooled) read each V-real-11 part's own recorded amp track (the real guitar
  alone, at the median loudness of its training inputs, −21.84 LUFS). It was told the part's class and each forced
  amp; answers were rendered through the measure DI in fresh primed processes (438 renders). Its answers sound clearly
  worse than S, and they are not shown better than its own training average. That average is itself clearly worse
  than S on real songs, though it was even with S on the made-up songs (F11).
- **Numbers** (band-weighted, 7 bands; Wickerman ElecGtr2 and 3 as one part; all 66 directions; none refused).

  | Row | All | Clean (2 bands) | Crunch (5 bands) |
  |---|---|---|---|
  | P4 − S | +0.153 [+0.039, +0.268], 1 of 7 bands better; part-weighted +0.129, 1 of 10 parts | +0.028 [−0.367, +0.422] | +0.203 [+0.057, +0.350] (0 better) |
  | constant − S | +0.170 [+0.056, +0.284], 1 of 7 better | +0.154 [−0.055, +0.363] | +0.176 [−0.002, +0.355] |
  | P4 − constant | −0.017 [−0.090, +0.057], 4 of 7 better | −0.126 [−0.730, +0.478] (2 of 2 better) | +0.027 [−0.017, +0.071] |
  | P4 − P4 pulled | +0.000 [−0.016, +0.017] | | |
  | S′ − S (crunch parts only, by design) | +0.034 [−0.002, +0.071], 1 of 5 better | | |

  - P4 − S per part: Colour Me Red ElecGtr02 −0.147 (the only part better); Signs ElecGtr3 +0.008; It Was My Fault
    ElecGtr1 +0.014; Colour Me Red ElecGtr03 +0.078; Wickerman ElecGtr2+3 +0.162; It Was My Fault ElecGtr3 +0.167;
    Wickerman ElecGtr1 +0.167; Get Out Of Bed ElecGtr2 +0.180; Let's Dance ElecGtr3 +0.229; Femme ElecGtr5 +0.435.
  - Leave one band out: +0.106 to +0.185.
  - Side rows: without the 2 quiet inputs (over 20% of frames at the grid floor: Colour Me Red ElecGtr03, It Was My
    Fault ElecGtr1), P4 − S +0.148 [+0.015, +0.281]; with Wickerman ElecGtr2 and 3 as two parts
    (each its own amp track), P4 − S +0.153 [+0.038, +0.268], P4 − constant −0.015 [−0.090, +0.059], constant − S
    +0.169 [+0.055, +0.283].
- **Checks.**
  - The S positive control passes: the fresh S renders match the label table's stored distances on all 60 (part, amp,
    half), at most 1.0e−4 against the 0.005 tolerance.
  - The S′ row agrees with P5's stored-distance read (+0.038).
  - The model's own amp guesses on the real tracks: SW50R 13, AC20 7, PR12 2 (of 22 halves).
- **Reading.**
  - In distribution, a wrong amp still left P2a about 0.2 better than S on that amp (F19). On V-real, P4 is +0.15
    against S: a swing of about 0.35 that the amp mismatch does not explain.
  - Fed the real guitar alone, the model is not shown to beat S or its own average on V-real. P4 − constant's interval
    still allows up to about a third of its in-distribution gain over the constant (−0.247). The clean parts lean
    better than the constant (−0.126, 2 of 2 bands), the crunch parts do not.
  - F26 checks whether the penalty is the training prior's wet time effects (it is not), and F27 where real parts'
    presets sit against the training prior.
- **Caveats.**
  - 11 parts in 7 bands.
  - The measure DI caps even the truth at about 0.55 of S's distance (step 9).
  - The amp track as input is not what the product gets; it is the best case for the input, used to isolate transfer.
- **References.** `PF/vreal/report-p4.json`, `PF/vreal/report-p4-own.json`,
  `PF/vreal/answers/{P4-P2a-best,P4-P2a-best-pulled,P4-P2a-best-constant,S,S-prime}.json`, `PF/vreal/judge/*/`;
  `cmd_p4_predict`, `cmd_vreal_comparators`, `cmd_vreal_render`, `cmd_vreal_report`; ledger `phase_4`,
  `phase_4_revised`.

### F21. Dropout and darkening augmentation does not help the clean input in distribution (step 18, alone)
- **Result.** P2a-dd is the recipe with D_stem's dropouts and darkening (p 0.3 each) on the clean input (seed
  20261042, best checkpoint epoch 25 of 60, 10.3 min).
  - By knob it reads like P2a: NS −0.0087 [−0.0110, −0.0063] against −0.0086; at the final checkpoint −0.0097.
  - By sound it is a little less close than seed-1 P2a, and even with the two-seed pool.
- **Numbers.**

  | Row | FS | NS |
  |---|---|---|
  | P2a-dd − S | −0.224 [−0.372, −0.077], 6 of 6 bands better | −0.197 [−0.274, −0.121], 28 of 36 sections better |
  | P2a − P2a-dd | −0.024 [−0.058, +0.011] | −0.044 [−0.087, −0.001] (mostly one song: Adam Buckley −0.094, The Maybe Next Years −0.016) |
  | P2a-dd − P2a (both seeds pooled) | | +0.039 [−0.007, +0.085] |

- **Reading.** Augmentation does not help the clean input in distribution, and may cost a little (one seed). Whether
  it helps a song-fed model or transfer is untested: P2d-aug was not run. The old result (D_F5-noaug, leaning towards
  augmentation helping a stem model) stands beside this.
- **References.** `PF/runs/P2a-dd-20261042.json`, `PF/reads/P2a-dd-{best,final}.json`,
  `PF/sound/judge/P2a-dd-best/`, `PF/sound/report-dd.json`.

### F22. Mastering does not affect reading the guitar's own tone (step 15, alone)
- **Result.** P2a (seed 20261042, NS-best) read its own inputs passed through the mastering compressor with each
  example's own drawn parameters (RMS compressor, ratio 2–4, a clip at −1 dBFS). Its answers sound as close as on the
  unmastered inputs.
- **Numbers.**

  | Row | FS | NS |
  |---|---|---|
  | P2a − P2a(mastered input) | −0.003 [−0.009, +0.002] | −0.002 [−0.017, +0.013] |
  | P2a(mastered input) − S | −0.245 [−0.377, −0.113], 6 of 6 bands better | −0.240 [−0.313, −0.166], 30 of 36 sections better |

- **Reading.** P2a never saw a compressed input, so a loss would have been an upper bound; the null on it rules step 15
  out for the guitar itself. Mix-keyed pumping (a compressor driven by the drums) is untested here, but mastering does
  not drive the backing loss (F17's split).
- **References.** `PF/inputs/*-tgtl-mast.npz`, `PF/sound/judge/P2a-best-mast/`, `PF/sound/report-mastering.json`;
  `mastered_inputs`; ledger `phase_3_isolated` (b).

### F23. On a model that reads, the plain 0.5 switch readout is right, in distribution (step 27, alone)
- **Result.** P2a's plain answers were compared with two readouts fitted on FS.
  - "sws": its 6 switches R0 did not find readable on FS kept at S's state: SW50R treble boost, compressor release,
    tremolo, delay ping-pong, right room mic, SW50R spring.
  - "nc": the near-chance rule (from the F20 build's draft, PR #345, decision C). δ = 0.1 was chosen by FS switch
    agreement (0.672; stored in the answers' `nc_fit`). A switch within 0.1 of 0.5 takes the constant's majority. On
    NS it made 126 switch flips: 70 undid correct answers and 56 fixed wrong ones. It also changed 341 other stored
    values (knobs of switched features, written or neutralised).
- **Numbers** (NS primary; both are fitted on FS).

  | Row | FS | NS |
  |---|---|---|
  | P2a − P2a(sws) | −0.021 [−0.066, +0.024] | +0.001 [−0.009, +0.011] |
  | P2a − P2a(nc) | −0.024 [−0.110, +0.062] | −0.064 [−0.101, −0.027], 20 of 36 sections better |
  | P2a(nc) − S | −0.224 [−0.331, −0.117] | −0.177 [−0.253, −0.101] |

- **Reading.** For a model that reads, in distribution: keeping its unreadable switches at S changes nothing, and the
  near-chance rule costs sound. No readout change is recommended. Whether a weak model (D_CC) loses its pedals to the
  0.5 cut was not re-tested here (P3 on D_CC was dropped); the review's s27 (D_CC with pedals at S, −0.076, 7 of 7
  bands) stands as the record for a weak model.
- **References.** `PF/sound/judge/{P2a-best-sws,P2a-best-nc}/`, `PF/sound/answers/P2a-best-nc.json`,
  `PF/sound/report-{sws,nc}.json`; `switch_rule`, `s_switch_state`; ledger `phase_3_isolated` (c).

### F24. More backing variety recovers about a quarter of the skill the backing takes (the isolated learnability test)
- **Result.** P2b-bk8 is P2b retrained with each of its 1,787 training targets (177 sections, 25 DIs) shown per epoch
  in its own P2b input or in 1 of 8 backings. The 8 are drawn with replacement from the non-guitar backings of the
  other 7 training songs' sections, at exactly P2b's levels (14,296 inputs, zero renders; seed 20261042). Its best
  checkpoint is at epoch 15 of 60 against P2b's 5; its NS loss still rises after epoch 35 (5.36 → about 5.9). It was
  read on P2b's own fixed inputs.
- **Numbers.**

  | Row | FS | NS |
  |---|---|---|
  | P2b-bk8 − P2b (primary) | −0.081 [−0.194, +0.033], 5 of 6 bands better | −0.059 [−0.093, −0.025], 25 of 36 sections better (both songs: −0.048, −0.065) |
  | P2b-bk8 − S | −0.051 [−0.216, +0.113] | −0.081 [−0.162, +0.001] |
  | P2a − P2b-bk8 | −0.197 [−0.280, −0.113] | −0.161 [−0.215, −0.106] |

  - By knob: NS −0.0004 against P2b's +0.0010 (13 switches readable against 5); FS −0.0023 [−0.0037, −0.0009]. At the
    final checkpoint NS +0.0026, worse than the constant.
  - Share of P2a − P2b recovered (`share`: the ratio of the log's clustered means, 4,000 cluster bootstraps): NS
    0.269 [0.131, 0.423], FS 0.291 [−0.025, 0.527] (FS includes 0, as its numerator row does).
- **Reading.**
  - More backing variety helps a backing-fed model (P2b) and delays and softens its overfitting. This is consistent with
    learnability; the variety also acts as a regulariser, so learnability is not isolated by it.
  - Most of the loss remains. Backings from these 7 other songs, with the same 25 DIs, do not restore it, so it is
    undecided between masking and too few performances and backings.
  - The direction it supports: far more backing variety (zero renders) and more performances.
- **Caveats.** One seed, with NS-chosen checkpoints; the FS row is undecided. The other-song backings are not in time or
  key with the performance.
- **References.** `PF/sound/share-backings.json` (`cmd_share`), `PF/inputs/*-mixb-k*.npz`,
  `PF/inputs/backings-{levels,pool}.json`, `PF/runs/P2b-bk8-20261042.json`,
  `PF/sound/judge/P2b-bk8-best/`, `PF/sound/report-backings.json`; `cmd_build_backings`, `BackingData`; ledger
  `phase_3_backings`.

### F25. On the clean input, a 3.5× size increase bought little sound (step 4, alone)
- **Result.** P2a was trained on nested subsets of its 1,787 training examples (both seeds each, answers pooled):
  - 511 examples (28.6%, from the 25% draw, rounded up per section);
  - 935 (52.3%);
  - all 1,787.
  The smaller sets also got fewer optimiser steps (480 and 900, against 1,680).
- **Numbers.**

  | Size | NS by knob, E − constant (best, seed 1) | Switches readable (NS) | By sound − S, NS (pooled) | By sound − S, FS (pooled) |
  |---|---|---|---|---|
  | 511 | −0.0006 [−0.0023, +0.0011] | 15 | −0.193 [−0.275, −0.111] | −0.223 [−0.404, −0.041] |
  | 935 | −0.0049 [−0.0067, −0.0031] | 23 | −0.205 [−0.290, −0.120] | −0.100 [−0.217, +0.018] |
  | 1,787 | −0.0086 [−0.0106, −0.0066] | 27 | −0.237 [−0.312, −0.161] | −0.195 [−0.321, −0.069] |

  - Paired steps by sound (pooled):
    - NS: 511 → 935 −0.012 [−0.068, +0.044]; 935 → 1,787 −0.031 [−0.080, +0.017]; 511 → 1,787
      −0.044 [−0.097, +0.010].
    - FS: 511 → 935 +0.123 [+0.033, +0.213] (worse, 6 of 6 bands); 935 → 1,787 −0.095 [−0.149, −0.041]; 511 → 1,787
      +0.028 [−0.043, +0.099]. Non-monotone: run-to-run noise. (Steps are the stored pooled pairs, negated where the
      report stores the reverse pair; 511 → 1,787 is `report-curve-ends.json`.)
  - At the final checkpoint (both seeds pooled), NS by knob: 511 −0.0060, 935 −0.0075, 1,787 −0.0116 [−0.0138,
    −0.0093] (26 knobs readable): the knob read climbs with size at both checkpoints.
  - The fewer-performances point, 50% of the sections with all their examples (905, one seed): NS by knob −0.0061
    (final −0.0066), by sound −0.201 [−0.284, −0.117].
  - Single seeds swing: seed 1 alone gives 511 −0.198, 935 −0.117, 1,787 −0.241 on NS; one seed against the two-seed
    pool differs by up to NS +0.089 (P2a-f50).
- **Reading.** In distribution on the clean input, a 3.5× size increase bought about 0.04 on NS (undecided) and
  nothing on FS, while the knob read improved at both checkpoints. Song-fed curves were not run. More of the same data
  is not shown to be a strong lever for the clean input's sound.
- **References.** `PF/runs/P2a-{f25,f50,s50}-2026104{2,3}.json`, `PF/reads/P2a-{f25,f50,s50}-{best,final}.json` (the
  final reads of f25 and f50 pool both seeds; their best reads are seed 1),
  `PF/sound/judge/P2a-*-x20261042+20261043/`, `PF/sound/report-{curve,curve-pooled,s50,seedcheck}.json`; ledger `phase_3_isolated`
  (e).

### F26. P4's penalty is the core tone, not the wet time effects (P4 dry, isolating F20)
- **Result.** P4's answers and its constant were re-rendered with the time-effect and spring family at S's values
  (198 renders). Drying them changes nothing: the core tone (amp, gain, EQ, cab, pedals) sits far from the real parts,
  and the model is not shown to move away from its own average.
- **Numbers** (7 bands).

  | Row | All | Clean | Crunch |
  |---|---|---|---|
  | P4-dry − S | +0.156 [+0.016, +0.296], 2 of 7 better | −0.023 [−0.723, +0.676] | +0.228 [+0.074, +0.382] |
  | constant-dry − S | +0.137 [+0.019, +0.255], 2 of 7 better | +0.054 [−0.338, +0.446] | +0.170 [+0.000, +0.340] |
  | P4-dry − constant-dry | +0.019 [−0.051, +0.089] | −0.077 [−0.385, +0.230] | +0.057 [−0.016, +0.131] |
  | P4 − P4-dry | −0.003 [−0.049, +0.043] | +0.051 [−0.254, +0.356] | −0.024 [−0.073, +0.024] |

  - constant − constant-dry: +0.033 [−0.021, +0.086].
  - P4-dry − S per part: Colour Me Red ElecGtr02 −0.263, Signs ElecGtr3 −0.021, Colour Me Red ElecGtr03 −0.006, It Was
    My Fault ElecGtr1 +0.016, It Was My Fault ElecGtr3 +0.159, Let's Dance ElecGtr3 +0.229, Wickerman ElecGtr1 +0.237,
    Get Out Of Bed ElecGtr2 +0.243, Wickerman ElecGtr2+3 +0.277, Femme ElecGtr5 +0.431.
  - Leave one band out: +0.110 to +0.204. The S positive control passed again.
- **Reading.** F20's penalty is mainly the core tone, mostly on crunch; the training prior's wetness is a small,
  undecided part (constant − constant-dry +0.033 [−0.021, +0.086]), unlike D_F5's on V-real (step 34).
- **References.** `PF/vreal/report-p4-dry.json`, `PF/vreal/answers/P4-P2a-best-{dry,constant-dry}.json`; ledger
  `phase_4_dry`.

### F27. The presets that suit these real parts sit at the training prior's edges about 3× as often as its own labels do (zero renders)
- **Result.** Arm A's true-DI search found, for V-real-10's parts, presets that beat S (−0.137 shrunk, −0.192 best;
  review step 38). Their searched controls were placed within the training labels' distribution: the same amp and part
  class, every today's-space continuous control that sounds, using mid-rank percentiles (ties count half).
- **Numbers.** Share of values outside the training labels' 5–95% range:

  | Set | Values | Outside | Below 5% | Above 95% |
  |---|---|---|---|---|
  | The search's best presets | 550 | 0.27 | 0.12 | 0.15 |
  | Only the controls the search moved off S | 388 | 0.35 | 0.17 | 0.18 |
  | NS labels (the reference) | 3,289 | 0.09 | 0.04 | 0.05 |
  | S presets | 58 | 0.03 | 0.02 | 0.02 |

  The controls most often outside: right cab position 0.66, SW50R treble 0.65, AC20 cut 0.50, PR12 bass 0.50, SW50R
  mid 0.45, left cab position 0.42 (each from 20–60 values).
- **Reading.** Real parts often want settings at or beyond the edges of what the model was trained on, at both ends,
  about 3× as often as the training labels themselves sit there. This compounds F20: the model is not shown to read the
  real recordings, and the targets also lie where training is thin.
- **Caveats.**
  - The search's "best" is one 52-render search per half and can sit on controls the sound barely constrains (cab
    placement). The shrunk version, halfway to S, is the robust one.
  - Descriptive and post hoc.
  - Under the first tie rule (strictly below), the split read 0.20 below and 0.10 above; mid-rank removes that lean, so
    no direction is claimed.
- **References.** `PF/prior-edges.json` (`cmd_prior_edges`: its rule, the summaries and every control), from
  `~/ndsp-presets/learn/arm-a-mega53/F-perfect-sep/ZT/*/*/{A,B}.json` (`settings.best`) and the ladder's training
  labels; zero renders.

### F28. By knob, the clean-input model reads new songs in every band (the new-song k-fold)
- **Result.** P2a (seed 20261042, the recipe, final checkpoints, so nothing is chosen on the held-out set) was
  retrained 5 times, each holding out whole bands:
  - Forkupines;
  - BKS (2 songs);
  - The Travelling Band, Ale Lak and Dunning Kruger;
  - Hazael and Storm Of Particles;
  - The Maybe Next Years and Adam Buckley.
  Each read every kept example of its held-out bands by knob (R0's rule). By sound it was not read.
- **Numbers.**

  | Fold (held out) | Training | Held out | Knobs readable | Switches readable | E − constant |
  |---|---|---|---|---|---|
  | Forkupines | 1,863 | 514 | 24 | 25 | −0.0092 [−0.0109, −0.0075] |
  | BKS | 1,626 | 751 | 25 | 28 | −0.0073 [−0.0091, −0.0055] |
  | Travelling Band, Ale Lak, Dunning Kruger | 1,972 | 405 | 16 | 27 | −0.0092 [−0.0118, −0.0066] |
  | Hazael, Storm Of Particles | 2,053 | 324 | 21 | 25 | −0.0098 [−0.0133, −0.0063] |
  | The Maybe Next Years, Adam Buckley | 1,994 | 383 | 21 | 27 | −0.0105 [−0.0130, −0.0079] |

  - Pooled over the 9 bands (each example read by the fold that held its band out): −0.0090 [−0.0101, −0.0079], 9 of
    9 bands better.
  - Per band −0.0055 (Ale Lak) to −0.0112 (Storm Of Particles); leave one band out −0.0087 to −0.0094; part-weighted
    −0.0088.
- **Reading.** The clean-input model's knob skill on new songs is general across every training band, not only the 2
  NS songs. It is small, about 1 point of a knob's range (−0.009), in every band; what it is worth is read by sound
  (F11), which still rests on the 2 NS songs.
- **Single-run spread.** Fold 4 holds out exactly the NS examples. It reads −0.0105 (with 207 more training examples,
  FS's), against −0.0053 for P2a seed 1 at its final checkpoint on the same 383 examples. One run varies a lot, so the
  per-fold differences are not read. The 9-of-9-bands result is unaffected.
- **Caveats.** By knob only; one seed per fold; fold sizes differ (1,626–2,053 training examples); the ladder's set (no
  DT doubles).
- **References.** `PF/runs/P2a-k{0..4}-20261042.json`, `PF/reads/P2a-k{0..4}-final.json` (`per_example`),
  `PF/reads/kfold-P2a.json`; `cmd_kfold_report`; ledger `phase_3`.

### F29. Backings from 13 more songs recover about half of the skill the backing takes (phase 5A, two seeds)
- **Result.** P2b-wide24 is P2b retrained with each of its 1,787 training targets shown per epoch in its own P2b
  input or in 1 of 24 backings. The pool has 406 backings from 21 sessions: the training songs' 177 sections
  (P2b-bk8's pool) and 229 windows of 13 more songs whose stems were heard clean. Each backing is drawn
  session-first, never from the example's own song, and set at P2b's levels (42,888 inputs, zero renders; seed
  20261042). Best checkpoint at epoch 50 of 60, against P2b-bk8's 15; its NS loss stays at 5.32–5.51 from epoch 20
  instead of rising to about 5.9. It was read on P2b's own fixed inputs (240 renders).
- **Numbers.**

  | Row | FS | NS |
  |---|---|---|
  | P2b-wide24 − P2b-bk8 (primary) | −0.124 [−0.236, −0.012], 5 of 6 bands better | −0.046 [−0.091, −0.001], 22 of 36 sections better (by song, example-weighted: Adam Buckley −0.112, The Maybe Next Years −0.032; section-weighted −0.104, −0.013) |
  | P2b-wide24 − S | −0.175 [−0.386, +0.035] | −0.127 [−0.213, −0.041] |
  | P2a − P2b-wide24 | −0.073 [−0.177, +0.032] | −0.115 [−0.178, −0.052] |
  | Seed 2 (20261043): P2b-wide24 − P2b-bk8 | −0.157 [−0.350, +0.036], 5 of 6 | −0.056 [−0.124, +0.012], 20 of 36 |
  | Both seeds pooled per example − P2b-bk8 | −0.141 [−0.291, +0.009], 5 of 6 | −0.051 [−0.101, −0.001], 20 of 36 |

  - Share of P2a − P2b recovered (`share --name P2b-wide24`): NS 0.478 [0.274, 0.713], against P2b-bk8's 0.269;
    FS 0.738 [0.468, 1.021]. Seed 2: NS 0.523 [0.234, 0.814], FS 0.857 [0.460, 1.332]; both seeds pooled: NS 0.501 [0.289, 0.728], FS 0.798
    [0.481, 1.155].
  - Seed 2's best checkpoint is at epoch 35. By knob, both seeds pooled: NS −0.0019 [−0.0032, −0.0005], FS −0.0041
    [−0.0058, −0.0025] against the constant.
  - By knob: NS −0.0008 [−0.0027, +0.0011] against the constant (P2b-bk8 −0.0004); FS −0.0040 [−0.0060, −0.0020]
    (P2b-bk8 −0.0023). On NS's factory-mode labels it reads worse than the constant (+0.0102, P2b-bk8 +0.0052): its
    knob gain is on the wide draws.
- **Reading.**
  - More backing variety keeps helping: about half of the backing's loss is recovered on NS, against about a quarter
    with 8 backings from the training songs. The direction is the same on both sets; of the NS songs, Adam Buckley
    carries it and The Maybe Next Years is near zero.
  - With 13 more songs the model also overfits far less within 60 epochs. At least the recovered part of the loss is
    learnable from variety alone (zero renders), not masked; whether the remaining half is masking or too little
    variety is undecided.
  - Still about half of the loss remains on NS (P2a − P2b-wide24 −0.115).
- **Caveats.**
  - NS-chosen checkpoints. By the declared rule (ledger `phase_5a_seed2`) NS's row stands: seed 2 is negative and
    the per-example pooled row excludes 0, though only just. P2b-bk8 has one seed, and the variants' schedule is the
    same for both seeds, so the spread is partial.
  - The variants (24 against 8), the sessions (21 against 8) and the own-input share (1 in 25 against 1 in 9) all
    change together, so which of them helps is not separated.
  - Other-song backings are not in time or key with the performance. Some extra backings are thin: 64 of the 229
    extra windows run past a stem's end (that instrument silent) and 12 have only one stem above −50 dBFS RMS (all
    pass the −33 LUFS floor on the sum).
  - The variants' schedule is seeded by the pool's seed, not the training seed, so a second training seed varies the
    initialisation and batch order only.
- **References.** `PF/inputs/backings-wide-pool.json`, `PF/inputs/*-mixbw-k*.npz`,
  `PF/runs/P2b-wide24-{20261042,20261043}.json`, `PF/reads/P2b-wide24-{best,final}-x20261042.json` (seed 1) and
  `PF/reads/P2b-wide24-best.json` (both seeds), `PF/sound/answers/P2b-wide24-best{,-x20261043}.json`,
  `PF/sound/judge/P2b-wide24-best{,-x20261043}/`, `PF/sound/report-wide24.json`,
  `PF/sound/share-P2b-wide24{,-x20261043,-x20261042+20261043}.json`; `cmd_wide_pool`, `cmd_build_wide`, `WideData`,
  `cmd_share`; ledger `phase_5a`, `phase_5a_seed2`.

### F30. The amp-track bleed check fails tracks that cannot hold bleed (zero renders)
- **Result.** 5B.1 was first designed on the pool's own recorded amp tracks. Measured with the stock check
  (`trusted_data.amp_status`, the −30 dB line), they nearly all fail. Every own amp track of both NS songs fails
  (The Maybe Next Years −10 to −14 dB through a backing vocal; Adam Buckley's too), as does The Travelling Band
  (−5.5 to −15 dB through the Mellotron and Hammond). Over the ladder's training and FS DIs' 45 own tracks: 34
  fail, 5 unmeasurable, 6 pass (Forkupines' ElecGtr9, Ale Lak's Amp2, BKS Bulldozer's 4 ElecGtr7 tracks); all 8 of
  NS's fail.
- **The flaw.** BKS's GR4 (software), Pod and reamped tracks are, by their names and signal chain, made from the DI
  after the session, so no other instrument should be in them (inferred: the session Readmes say nothing of it; each
  reamped track's envelope best matches its own DI, r 0.53–1.0). Of the 24 measured, the stock check fails 17 (−21.9
  to −28.1 dB), leaves 3 unmeasurable and passes 4.
  - Every one of the 17 fails through the power-sum rule; no single source fails alone. 23_ElecGtr2bGR4's −21.9 dB
    sums 13 sources, each between −29.8 and −39.1 dB, among them the kick and the line-level bass DI
    (13_BassDIDist, −38.6 dB), which no guitar can leak into.
  - So the main cause is a small positive per-source reading, likely from music played in time and in the same
    harmony, summed over many sources. The guitar leaking into other mics (room, headphones) may add to it; it is
    not shown.
  - The NS songs' and The Travelling Band's fails are different: single sources at −6 to −16 dB. Those may be real
    bleed or a leak the other way; undecided.
- **A first fix, checked on controls.** The same estimator read only on frames where the amp track's own DI is silent
  (±0.5 s), the source playing, nulls rolled within those frames:
  - negative control: 35_ElecGtr6bGR4 against the Rhodes, stock −23.9 dB (fail), gated nothing above the nulls' mean
    on 718 frames (pass). A GR4 track is near silent where its DI is, so this barely tests the estimator; a mic'd
    reamp negative control is still needed (24_ElecGtr2cReamp1 against a backing vocal had 101 frames, too few);
  - positive control: the Rhodes injected into 24_ElecGtr2cReamp1 at −25 dB reads −23.7 dB gated (stock −28.9);
  - its limit is coverage: The Travelling Band's DIs leave 1 such frame, and backing vocals 86–101 frames (under the
    200 asked), so those read nothing.
- **Reading.** The stock check's power sum fails tracks that should hold no bleed, so it is unreliable on amp tracks
  and "the pool's real amp tracks are dirty" is not established for the power-sum fails. Since no recorded amp track
  can be trusted through this check, 5B.1 uses reamped tracks, bleed-free by their chain, and relies on no bleed
  check (the isolation rule). Fixing the check (a per-source rule with intervals, or the gated read) is a candidate
  for rule 1's amp stand-ins and later real-track data; it is not yet adopted.
- **Caveats.** The gated check was tried on 5 cases, its "pass" is the real reading less the nulls' mean (no
  interval), and its raw readings are not yet stored. A DI's linear fit explains only −29 to −39 dB of the
  suspected sources, so a leak into the other mics is not shown either way. The inventory gives 35_ElecGtr6bGR4 to
  DI 19, though it matches 34_ElecGtr6aDI (r 0.96 against 0.34); it counts under DI 19 in the 45.
- **References.** `PF/real/bleed/*.json` (the stock readings), `PF/real/bleed/measure.log`; the gated trial
  `scratchpad gated.py` (to move into `pipeline_fix` with the fix's declaration); `trusted_data.measure_amp_bleed`,
  `source_raw`, `amp_status`.

### F31. On real amps the gap is already there with known playing (5B.1, reamped tracks)
- **Result.** P2a (both seeds, NS-best) read 40 reamped tracks of BKS's two songs: 14 real amp-and-mic rigs on 8
  performances, 38 of them training sections. Each was read at the training inputs' loudness, per forced amp and
  search half, and judged by sound on the held half against the reamped track (960 renders, every unit's lag found:
  Bulldozer −20 to −66 samples, Too Much +84 to +111).
- **Numbers** (clustered by DI, 8 clusters; by rig beside, 14 clusters):

  | Row | By DI | By rig | Units better |
  |---|---|---|---|
  | P2a − S (primary) | +0.066 [+0.030, +0.102], 1 of 8 better | +0.074 [+0.036, +0.112], 3 of 14 | 11 of 40 |
  | P2a − constant | −0.053 [−0.125, +0.019], 5 of 8 better | −0.056 [−0.109, −0.004], 10 of 14 | 27 of 40 |
  | constant − S | +0.119 [+0.047, +0.192], 1 of 8 better | +0.130 [+0.086, +0.175], 2 of 14 | 7 of 40 |

  - Per DI, P2a − S runs from −0.019 to +0.167; constant − S from −0.051 to +0.289. Part-weighted: +0.067, −0.060,
    +0.127.
  - S sits at a similar distance from these tracks as from V-real's (median half distance 4.8 against 4.3).
- **Reading.**
  - The clean-input model, which reads new plugin renders (F11, F28), does worse than S on BKS's reamped tracks, even
    on performances it trained on. Part of F20's gap already appears on a real-amp recording of known playing: +0.07
    here against +0.15 on V-real (unpaired, different bands). How much new playing or the V-real recordings add is
    not measured.
  - The model leans better than the constant of its labels (undecided by DI; 10 of 14 rigs). The constant roughly
    ties S on the plugin's own held-out renders (P2a − S and P2a − constant differ by about 0.005 in the ladder's
    read) but is +0.119 behind S here: on real amps the labels' average falls behind S, consistent with F27 (real
    parts' presets at the prior's edges). The model may read some real-amp sound, from a centre that suits real amps
    less than S does.
  - Not separated: the amp, the mic, room and cab chain, the reamps' noise or tails, and the judge on real
    recordings. How much better than S any preset could do here (the ceiling) is not measured.
  - The direction it supports: labels that reach real-amp tones (5B.2's pseudo-labels from a true-DI search on these
    reamped tracks, or presets made for real tones).
- **Caveats.** One band (BKS), 8 performances; 38 of 40 units are training sections; P2a's two seeds pooled at
  NS-best checkpoints; the bleed-free status of the reamps is inferred from their names and chain (F30).
- **References.** `PF/real/answers/{P2a,S,constant}.json` (the units and answers), `PF/real/lags/`,
  `PF/real/judge/{S,P2a,constant}/`, `PF/real/report-5b1.json`; `real_parts`, `cmd_real_predict`, `cmd_real_render`,
  `cmd_real_report`; ledger `phase_5b1`.

### F32. Re-centred on S, the model's per-track readings lean better on real amps (5B.1b, exploratory)
- **Result.** On F31's 40 reamped units, P2a's answers were re-centred on S (P2a-Sc: each of S's sounding continuous
  controls at S's value plus P2a's deviation from its labels' constant; switches and mics at S's). Because that
  move is mostly one shift shared by every track of an amp and class, a control was added before any render
  (S-shift: S plus the shared shift taken from the other DIs' units). 720 renders; S, the lags and P2a reused.
- **Numbers** (clustered by DI, 8; by rig beside, 14):

  | Row | By DI | By rig | Units better |
  |---|---|---|---|
  | S-shift − S (the shared shift) | +0.002 [−0.030, +0.035], 2 of 8 better | −0.003 [−0.033, +0.028], 4 of 14 | 11 of 40 |
  | P2a-Sc − S-shift (per-track skill) | −0.031 [−0.067, +0.005], 6 of 8 | −0.026 [−0.055, +0.002], 10 of 14 | 29 of 40 |
  | P2a-Sc − S | −0.029 [−0.061, +0.004], 6 of 8 | −0.029 [−0.069, +0.011], 10 of 14 | 31 of 40 |
  | P2a-Sc − P2a (not a skill read) | −0.095 [−0.148, −0.042], 7 of 8 | −0.103 [−0.143, −0.063], 13 of 14 | 35 of 40 |

- **Reading.**
  - The shared shift alone is not seen to help (undecided). The model's per-track deviations, applied around S,
    lean better than S and than the shift, by about 0.03; both rows are undecided (the intervals just include 0).
  - Re-centred on S, P2a's penalty on real amps (F31's +0.066) is gone (P2a-Sc − S −0.029, paired). What re-centring
    changes is the continuous centre (the labels' average) and the switches and mics, set to S's (P2a's differ from
    S's in all 240 answers: gate 219, right mic 207, left mic 164, compressor 155, reverb 101); the two are not
    separated. What the model reads per track is small next to what a true-DI search finds on real amp tracks
    (about −0.14 to −0.17 against S; unpaired, other parts: the roadmap's arm A ZT and step 38).
  - The direction it supports: an S-centred readout is a cheap candidate for real recordings, to be weighed for
    D_fix on FS and NS (5B.1c on V-real was withdrawn), and labels that reach real-amp tones (5B.2) are still needed
    for a larger gain.
- **Caveats.** Exploratory: the readout was designed after seeing F31. One band, 38 of 40 units seen in training;
  switches and mics held at S's, so only the continuous controls are read; the per-track remainder (0.02–0.03 per
  knob) is near the gap between a track's two halves (0.013–0.025).
- **References.** `PF/real/answers/{P2a-Sc,S-shift}.json`, `PF/real/judge/{P2a-Sc,S-shift}/`,
  `PF/real/report-5b1b.json`; `sc_cont`, `real_shift_answers`, `cmd_real_predict --names`; ledger `phase_5b1b`.

### F33. Without the uniform draws the model reads sharper near presets by head; not shown better on real amps (5B.2 arm P)
- **Result.** P2a retrained on its 1,296 preset-centred draws (factory and S; the 491 wide draws out), against a
  size control drawing the same count per section from all modes (each on 2 seeds, NS-best, read as ensembles). Read
  on 5B.1's 40 reamped units (1,200 renders), and, because P − pcsz leaned better there, S-centred (P-Sc, 480) and by
  sound on FS/NS split by draw mode (480). Zero-render head losses by draw mode beside.
- **Numbers** (real units clustered by DI, 8; by rig beside; FS by band, NS by section):

  | Row | Result | Better |
  |---|---|---|
  | P − pcsz, real units (primary) | −0.019 [−0.057, +0.020]; by rig −0.024 [−0.053, +0.005] | 5 of 8 DIs, 28 of 40 |
  | P − P2a, real units | −0.012 [−0.053, +0.030]; by rig −0.011 [−0.044, +0.023] | 5 of 8, 26 of 40 |
  | P-Sc − P2a-Sc, real units (centre removed) | −0.004 [−0.022, +0.015] | 4 of 8, 24 of 40 |
  | P's constant − P2a's constant, real units | +0.018 [−0.005, +0.041] | 3 of 8, 15 of 40 |
  | P − pcsz, FS / NS by sound | −0.029 [−0.082, +0.024] / +0.014 [−0.039, +0.068] | 4 of 6 bands / 18 of 36 |
  | the same on preset-centred examples, FS factory / start | −0.091 [−0.198, +0.016] / −0.128 [−0.314, +0.058] | 4 of 6 / 3 of 5 |
  | the same, NS factory / start | +0.002 [−0.069, +0.073] / +0.089 [−0.039, +0.218] | 14 of 24 / 6 of 13 |
  | the same on wide examples, FS / NS | +0.039 [+0.012, +0.065] / −0.003 [−0.109, +0.102] | 1 of 6 / 8 of 15 |
  | P − P2a, FS / NS by sound | +0.020 [−0.028, +0.067] / +0.042 [+0.005, +0.079] | 3 of 6 / 14 of 36 |
  | the same on preset-centred examples, FS factory / start | −0.045 [−0.182, +0.091] / −0.100 [−0.372, +0.172] | 3 of 6 / 4 of 5 |
  | the same, NS factory / start | +0.061 [−0.001, +0.124] / +0.007 [−0.070, +0.083] | 10 of 24 / 6 of 13 |
  | pcsz − P2a (size alone), FS / NS | +0.049 [−0.006, +0.103] / +0.027 [−0.010, +0.065] | 1 of 6 / 14 of 36 |

  - By head (zero renders, P − pcsz, both seeds): on preset-centred FS and NS examples lower knob NLL (−0.015 to
    −0.123) and mic CE (−0.002 to −0.230) for every seed; on wide examples far higher (+0.63 to +1.10), as expected.
  - P2a − S on these units reproduces F31 exactly (+0.066 [+0.030, +0.102]). P-Sc − S is −0.032 [−0.060, −0.005]
    (6 of 8 DIs; by fold −0.039 [−0.053, −0.025]), beside F32's P2a-Sc − S −0.029 [−0.061, +0.004].
- **Reading.**
  - Dropping the uniform draws is not shown to help on real amps (undecided). P − P2a, −0.012, becomes −0.004 once
    both are re-centred on S (P-Sc − P2a-Sc), and P's labels' constant is not nearer these tones (+0.018). The lean
    against the size control (−0.019) reaches the expected detectable size at its lower end, so a small gain is not
    ruled out. Per-track reading is not seen to change. By the declared reading (a tie: no evidence that the wide
    draws hurt), the training mix stays.
  - Near presets, on plugin renders, the model trained without uniform draws reads sharper by head (every seed). By
    sound it leans better than its size control on FS (undecided) and is mixed on NS; against full P2a it is not
    better by sound (NS +0.042, decided worse; NS factory +0.061, undecided). It loses on the wide examples it never
    saw. Fewer examples alone lean worse by about 0.03–0.05 by sound (pcsz − P2a, both undecided), in line with F25's
    size curve; the sharper heads near presets bear on F7 (knob skill mostly on random settings).
  - The user's question (do unrealistic random settings hurt?): not shown on real amps by this test (undecided).
    What real amps need is a centre that suits them (F34).
- **Caveats.** One band for real amps (BKS, 8 performances); 38 of 40 read units' sections (the playing) were
  trained on as plugin renders by every model here, so held out are the tracks, not the playing. One model pair reads
  every unit, so the by-DI interval carries no training noise (the heads read shows both seeds agree). P's checkpoint
  is chosen on NS loss that includes wide draws it never trained on; pcsz is one random draw. FS/NS strata are small
  (5–24 clusters).
- **References.** `PF/runs/P2a-pc-*`, `P2a-pcsz-*`; `PF/real/answers/{P2a-pc,P2a-pcsz,P2a-pc-constant,P2a-pc-Sc}.json`,
  `PF/real/report-5b2-armP.json`, `report-5b2-armP-sc.json`, `PF/real/heads-P.json`, `PF/sound/report-5b2-armP.json`,
  `report-5b2-armP-vsP2a.json`; `preset_centred`, `real_predict_5b2`, `cmd_real_heads`, `cmd_sound_report --by-mode`;
  ledger `phase_5b2`.

### F34. A real-amp centre beats S by about 0.13; trained on real-amp answers, the model reaches it but reads no further per track (5B.2 stage 1, Rc, arm R)
- **Result.** Stage 1, the ceiling: arm A's main stage with the true DI on 5B.1's 40 reamped units, per forced amp
  (120 directions, 6,840 renders). All 120 first evaluations of S were bit-identical to 5B.1's fresh S renders;
  120 labels, no fallbacks. Then Rc (S moved by the mean unit deviation of the labels the unit's fold model trained
  on; 9–20 labels per answer; 240 renders) and arm R (P2a's recipe plus 300 real rows per epoch from the other
  folds' DIs, 4 folds × 2 seeds, read as each fold's ensemble; 480 renders), read as declared.
- **Numbers** (held half; by DI, 8; the fold, 4, and rig, 14, beside):

  | Row | By DI | By fold | By rig | Better |
  |---|---|---|---|---|
  | best − S (the ceiling) | −0.349 [−0.437, −0.261] | | −0.335 [−0.417, −0.254] | 8 of 8 DIs, 40 of 40 units |
  | shrunk 0.5 − S | −0.211 [−0.249, −0.173] | | −0.201 [−0.238, −0.165] | 8 of 8, 40 of 40 |
  | Rc − S (a real-amp centre) | −0.133 [−0.229, −0.037] | −0.116 [−0.227, −0.006] | −0.110 [−0.188, −0.033] | 7 of 8, 34 of 40 |
  | R − Rc (per-track reading; primary) | +0.014 [−0.035, +0.062] | +0.010 [−0.068, +0.088] | +0.013 [−0.021, +0.048] | 3 of 8, 15 of 40 |
  | R − S | −0.120 [−0.188, −0.051] | −0.106 [−0.206, −0.007] | −0.097 [−0.162, −0.032] | 6 of 8, 29 of 40 |
  | R − P2a | −0.186 [−0.252, −0.120] | −0.175 [−0.238, −0.112] | −0.171 [−0.230, −0.112] | 8 of 8, 38 of 40 |
  | R − P2a-Sc (against the free readout) | −0.091 [−0.151, −0.032] | −0.074 [−0.146, −0.001] | −0.068 [−0.116, −0.020] | 6 of 8, 29 of 40 |

  - The ceiling is better than S on all 40 units, by 0.35 on average (0.04 to 0.76 per unit); per DI from −0.194
    (Too Much 20) to −0.533 (Bulldozer 31); per amp −0.32 to −0.36. On the search half it is −0.344 by DI against
    the held half's −0.349 (plain means −0.340 and −0.339), so the held half's gain is not the search fitting its
    own half.
  - Share of the ceiling, paired on its 120 directions: Rc 0.445 (Rc − S is −0.155 there), R 0.434, P2a-Sc 0.103,
    P2a −0.221 (arm P's P −0.153, its size control −0.203).
  - Per fold, R − Rc: +0.043, −0.064, +0.083, −0.023; Rc − S: −0.238, −0.099, −0.117, −0.010. DI 19 apart
    (Bulldozer clean, whose fold's clean labels all come from Too Much): Rc − S −0.171, R − S −0.153, R − Rc +0.019.
    Rc − P2a-Sc is −0.105 [−0.190, −0.019] by DI, but −0.083 [−0.173, +0.007] by fold.
  - By head (zero renders, every fold and seed): on its own DIs' real labels R's knob NLL is 0.54 to 1.25 below
    P2a's and its switch CE 0.16 to 0.33 below; its mic CE is lower in folds 0–2 but about 0.22 higher in fold 3
    on both seeds. On FS and NS its knob NLL is unchanged (−0.045 to +0.035) and its mic CE a little higher on NS
    (+0.03 to +0.17).
  - In setting space (zero renders, the audit; stored by `real-setting-audit` in `PF/real/setting-audit.json`): R's
    continuous answers sit 0.178 (mean per-answer rms over `K.space`'s continuous controls, unit scale) from Rc's, but
    no nearer the units' own labels: 0.270 against Rc's 0.260 (S 0.288, P2a 0.315). Their switches and mics agree
    with the labels 0.603 of the time, against Rc's 0.639 and S's 0.596, so no better than S's.
  - Checks: no fold's real rows include its own DIs, and each Rc answer used exactly its fold's labels (both
    re-derived from the stored records); Rc − S reproduces its first report exactly. The best's fresh and in-process
    renders agree to a |log ratio| of at most 6.1e-5 (an absolute judge difference of at most 3.0e-4; bit-identical
    in 36 of 120), so stage 2's in-process labels stand in for fresh ones.
- **Reading.**
  - The ceiling: within the searched controls (input gain, the amp's knobs and switches, both mics), a setting
    better than S by 0.35 on average exists on every one of the 40 units, as the judge measures it (the ceiling is
    scored by the judge it was searched on, so it does not test the judge). The searched controls reach a large part
    of the real-amp gap; the unsearched ones are not measured. By the stop rule, arm R went on.
  - A real-amp centre helps (decided on DI and fold): S moved by the other performances' labels wins 0.13 by DI,
    38% of the ceiling's 0.349 (0.445 paired on the ceiling's own directions), and on DI 19 the centre came from the
    other song. F32's shared shift, the mean of P2a-Sc's moves from S on the other DIs' units (a model trained on
    plugin labels), was not seen to help (+0.002 [−0.030, +0.035], undecided); labels from a search on the real amp
    tracks are what move it.
  - Trained with real rows, the model reaches the same place (R − S −0.12 and R − P2a −0.19, both decided): F31's
    real-amp penalty is fixed by real labels. Per-track reading beyond the centre is not seen: R − Rc is undecided
    (+0.014), and R's own moves away from Rc do not head toward each unit's label. By the declared rule, stage 2 runs
    (65 more units' labels).
  - About 0.2 per unit is left between Rc and the ceiling for a per-track reading to take.
  - The direction it supports: a real-amp centre (Rc's way, or a model trained with real rows) is a candidate
    readout for real recordings in D_fix, weighed with the S-centred one; more bands' reamped tracks are needed to
    tell a real-amp centre from BKS's own chain.
- **Caveats.** One band (BKS), 8 performances, 14 rigs; the physical amps and mics are probably shared within a
  song, so a held DI's centre may partly be learned on its own rig (DI 19's is from the other song). 38 of 40 read
  units' sections (the playing) were trained on as plugin renders by P2a and every R model, so held out are the
  tracks, not the playing. Fold 3 (Too Much 20 and 24, clean) gains little from Rc (−0.010). Labels are selected on
  one half; the ceiling's held half is the same section's other half, so it bounds a per-section reading, not a
  new-performance one. One ensemble per fold reads its units, so the fold interval (4 clusters) is wide.
- **References.** `PF/real/search/` (stage 1's 120 records), `PF/real/report-ceiling-1.json`,
  `PF/real/answers/{Rc,P2a-real}.json`, `PF/real/judge/{Rc,P2a-real}/`, `PF/real/report-5b2-rc.json`,
  `report-5b2-armR.json`, `PF/real/heads-R.json`, `PF/real/setting-audit.json`, `PF/runs/P2a-real*`;
  `cmd_real_search`, `cmd_real_ceiling`, `real_folds`, `real_rows`, `fold_records`, `rc_records`, `rc_setting`,
  `real_rc_answers`, `real_predict_5b2`, `cmd_real_heads`, `cmd_real_setting_audit`; ledger `phase_5b2`.

### F35. On two and a half times the real-amp labels the centre holds, and the model is still not shown to read further per track (5B.2 stage 2)
- **Result.** Stage 2 ran since R − Rc was undecided (F34): the same search on the other 65 reamped units (195
  directions, 10,725 renders, labels only, the best's in-process render). All 195 first evaluations of S were
  bit-identical to the unit's fresh S render; every unit got a lag; no fallbacks. Before any of its labels was
  used, the lag check refused 3 units (9 labels; the amendment above), leaving 186: 306 with stage 1's 120. On the
  held half the in-process best beat S in 192 of 195 directions (plain mean log ratio −0.380, search half −0.398;
  by DI −0.376 and −0.409). Then
  Rcs2 (Rc's rule on both stages' labels, 13–62 per answer; 240 renders) and arm R retrained on them (P2a-reals2:
  4 folds × 2 seeds, each fold's 300 real rows per epoch now 192–282 distinct labels, none from its own DIs or the
  refused units; best epochs 15–30; 480 renders), read on the same 40 units as declared.
- **Numbers** (held half; by DI, 8; fold, 4, and rig, 14, beside):

  | Row | By DI | By fold | By rig | Better |
  |---|---|---|---|---|
  | R2 − Rc2 (per-track reading; primary) | +0.029 [−0.011, +0.068] | +0.017 [−0.030, +0.064] | +0.019 [−0.013, +0.050] | 3 of 8 DIs, 16 of 40 units |
  | Rc2 − S (the centre) | −0.158 [−0.260, −0.057] | −0.140 [−0.285, +0.004] | −0.129 [−0.214, −0.045] | 7 of 8, 33 of 40 |
  | R2 − S | −0.129 [−0.212, −0.046] | −0.123 [−0.254, +0.008] | −0.111 [−0.186, −0.036] | 7 of 8, 28 of 40 |
  | R2 − P2a | −0.195 [−0.274, −0.117] | −0.192 [−0.293, −0.091] | −0.185 [−0.250, −0.119] | 8 of 8, 37 of 40 |
  | R2 − P2a-Sc | −0.101 [−0.174, −0.027] | −0.090 [−0.199, +0.019] | −0.082 [−0.140, −0.024] | 7 of 8, 28 of 40 |
  | Rc2 − Rc (descriptive: stage 2's labels on the centre) | −0.025 [−0.067, +0.017] | −0.024 [−0.059, +0.011] | −0.019 [−0.048, +0.010] | 5 of 8, 25 of 40 |
  | R2 − R (descriptive: on the model) | −0.009 [−0.054, +0.036] | −0.017 [−0.089, +0.056] | −0.014 [−0.048, +0.021] | 5 of 8, 23 of 40 |

  R2 is P2a-reals2, Rc2 is Rcs2. The two descriptive rows compare stage 1's and stage 2's versions on the same
  units; they were not declared, so they read nothing on their own.
  - Share of the ceiling, paired on its 120 directions (`real-ceiling --stage 1`): Rc2 0.517 (Rc2 − S −0.181
    there), R2 0.401; stage 1's Rc 0.445 and R 0.434 reproduce.
  - Per fold, R2 − Rc2: +0.020, +0.014, +0.067, −0.031; Rc2 − S: −0.305, −0.118, −0.130, −0.008. R2 trails the
    centre most in fold 2 (Bulldozer 31 and 36, crunch), whose models gain the fewest new training labels (111,
    against 129–186), though their crunch pool grows the most relative to stage 1 (30 to 126). DI 19 apart: Rc2 −
    S −0.198, R2 − S −0.118, R2 − Rc2 +0.079.
  - By head (zero renders, every fold and seed; `real-heads --stage 2`, `PF/real/heads-Rs2.json`): on its own DIs'
    real labels (24–114 per fold, both stages) R2's knob NLL is 0.67 to 1.46 below P2a's and its switch CE 0.20 to
    0.41 below; its mic CE is 0.79 to 2.47 lower in folds 0–2 and about level in fold 3 (+0.03, −0.05; stage 1's
    was +0.22). On FS and NS its knob NLL is unchanged (−0.016 to +0.027) and its NS mic CE a little higher (−0.03
    to +0.17).
  - In setting space (`real-setting-audit --stage 2`, `PF/real/setting-audit-s2.json`): R2's answers sit 0.159 from
    Rc2's but no nearer the units' labels (0.269 against Rc2's 0.260; S 0.288); switches and mics agree 0.615
    against 0.626.
  - Beside, a post-hoc look after the read, in setting space only (zero renders, `--within RigO`,
    `PF/real/setting-audit-s2-within-RigO.json`): on the 108 directions whose recording has another window clear
    of the unit's section, Rc's rule applied to that recording's own labels (RigO, 1–16 per answer) sits 0.193 from
    the unit's label, against Rc2's 0.263 and R2's 0.273; switches and mics agree 0.739 against 0.641 and 0.621.
  - Checks: no fold's real rows include its own DIs or a refused unit (re-derived with `fold_records`); Rc − S and
    stage 1's shares reproduce F34's exactly; the 8 runs hold 2,087 training ids each, 300 of them
    real, ledger `phase_5b2`.
- **Reading.**
  - Per-track reading is not shown: R2 − Rc2 is undecided by the declared rule (+0.029 by DI, +0.017 by fold;
    the DI interval's better end is −0.011), leaning the wrong way, and R2's moves off the centre do not head toward
    the labels. With stage 2 run, 5B.2's declared steps end here: arm R is not adopted over the centre.
  - The centre holds by DI: Rc2 beats S by 0.158 by DI (0.129 by rig); 52% of the ceiling paired. It is no longer
    decided by fold (the interval reaches +0.004), and neither are R2 − S (+0.008) or R2 − P2a-Sc (+0.019): all
    three rows F34 decided by fold lose that here, with fold 3 (−0.008 on Rc2 − S) against fold 0 (−0.305).
    Whether stage 2's labels move the centre further than stage 1's is undecided (−0.025, descriptive).
  - R2 still beats P2a (−0.195, decided by DI, fold and rig) and the free S-centred readout by DI (−0.101; rig
    beside): trained with real rows, the model learns the real-amp centre, as in F34.
  - Where the gap may sit (post hoc, setting space only): a recording's own other labels sit nearer each unit's
    label than any centre, and a model trained on 2.5 times the labels is not shown to read that. Whether that
    information is worth reading by sound is untested; the recording oracle (RigO, declared above) tests it, and
    says whether the next fix goes to the model's reading or to the labels.
- **Caveats.** As F34's: one band, 8 performances, 14 rigs, held tracks not held playing, labels selected on one
  half. Stage 2 adds mostly Bulldozer crunch (57 of 62 kept units), nothing for DIs 20 and 24, so the fold read
  units and the new labels are unbalanced. 20 of stage 2's 65 pr12 labels (10 of stage 1's 40) set Volume at its
  floor; the judge compares level-normalised sound, so these are valid answers but not presets as they stand.
- **References.** `PF/real/search/` (stage 2's 195 records), `PF/real/answers/{Rcs2,P2a-reals2,RigO,RcM}.json`,
  `PF/real/judge/{Rcs2,P2a-reals2}/`, `PF/real/report-5b2-rcs2.json`, `report-5b2-armR-s2.json`,
  `report-ceiling-1.json`, `heads-Rs2.json`, `setting-audit-s2.json`, `setting-audit-s2-within-RigO.json`,
  `PF/runs/P2a-real?s2-*`; `lag_refused`, `real_labels`, `rigo_records`, `real_rigo_answers`, `real_rcm_answers`;
  ledger `phase_5b2`, `phase_5b2_rigo`.

### F36. A recording's own other labels reach almost the whole ceiling: the per-track gap is not the labels' per-recording content but the model's reading or the number of recordings (5B.2 recording oracle)
- **Result.** RigO and its count-matched control RcM, as declared (`phase_5b2_rigo`, reviewed and re-checked
  before any render): 108 directions each (36 units, 7 DIs), 432 renders, every unit's stored lag, no refusals.
- **Numbers** (on RigO's 108 directions, both halves; by DI, 7; fold, 4, and rig, 12, beside):

  | Row | By DI | By fold | By rig | Better |
  |---|---|---|---|---|
  | RigO − Rcs2 (primary) | −0.145 [−0.206, −0.083] | −0.170 [−0.255, −0.085] | −0.159 [−0.205, −0.113] | 7 of 7 DIs, 36 of 36 units |
  | RigO − RcM (count-matched) | −0.150 [−0.202, −0.098] | −0.165 [−0.228, −0.103] | −0.157 [−0.194, −0.121] | 7 of 7, 35 of 36 |
  | RigO − S | −0.338 [−0.410, −0.266] | −0.335 [−0.418, −0.253] | −0.325 [−0.397, −0.254] | 7 of 7, 36 of 36 |
  | RcM − Rcs2 (descriptive) | +0.006 [−0.030, +0.042] | −0.005 [−0.032, +0.023] | −0.002 [−0.024, +0.019] | 4 of 7, 15 of 36 |
  | P2a-reals2 − Rcs2 (beside; descriptive) | +0.042 [+0.006, +0.078] | +0.026 [−0.008, +0.059] | +0.033 [+0.001, +0.064] | 2 of 7, 12 of 36 |
  | Rcs2 − S (descriptive) | −0.194 [−0.284, −0.104] | −0.165 [−0.275, −0.055] | −0.166 [−0.245, −0.087] | 7 of 7, 31 of 36 |

  - Against the ceiling on the same 108 directions, held half (`real-ceiling --stage 1 --within RigO`,
    `PF/real/report-ceiling-1-within-RigO.json`): RigO − S −0.360 against the per-window best's −0.371, a share of
    0.97 [0.94, 1.00] (RigO − best +0.011 [−0.001, +0.024]); RcM 0.57 [0.41, 0.71], Rcs2 0.59 [0.43, 0.73],
    P2a-reals2 0.45 [0.30, 0.59]. On all 120 directions Rcs2's share is 0.52 [0.30, 0.68]; dropping DI 20, where the
    centre is worse than S, favours the centre here (as declared).
  - Per DI, RigO − Rcs2: Bulldozer 19 −0.124, 22 −0.097, 28 −0.029, 31 −0.111, 36 −0.141; Too Much 16 −0.240, 24
    −0.271. Crunch DIs −0.094, clean −0.212 (the declared split, descriptive). The clean DIs' larger gain is mostly
    the centre's weakness there (Rcs2 − S −0.125 on clean, −0.245 on crunch); RigO − S is the same on both (clean
    −0.337, crunch −0.340), although clean DIs have 1 to 4 labels per answer and crunch 3 to 16, so RigO's few
    labels do not seem to hold it back (descriptive, 3 DIs against 4).
  - Audit: no RigO label comes from the unit itself or from a window starting less than 10 s from it (re-derived,
    0 of 108); RcM's 108 answers use exactly RigO's label counts; Rcs2 − S and P2a-reals2 − Rcs2 on these
    directions reproduce the pre-render report (`report-5b2-rigo-pre.json`).
- **Reading.**
  - By the declared rule, RigO − Rcs2 is better (decided by DI, and by fold and rig beside): the labels'
    per-recording differences are audible beyond the centre, and the count-matched control shows it is the
    recording, not a smaller centre's luck (RcM ≈ Rcs2). A setting taken from the same recording's other windows
    reaches 97% of the per-window best, so nearly all of what the search finds on one window is the recording's
    chain, constant across it.
  - So the per-track gap is not the labels' per-recording content: a reading of the track has headroom of at most
    about 0.15 beyond the centre, measured with a true-DI search, and arm R takes none of it (P2a-reals2 − Rcs2
    +0.042 here). By the declared reading the next fix works on the model's reading of the track and on more
    recordings: arm R learned from 10–11 recordings per fold, each giving one setting, which may be too few to learn
    a track-to-setting map (more recordings means more labelled data), or its input may not carry what tells
    recordings apart. Whether a song-only input carries that information is untested.
  - For the product this is an upper bound, not a method: RigO needs the true DI and a search on the same
    recording, which a song-only user does not have.
- **Caveats.** An oracle; one band (BKS), 7 DIs, 12 rigs; a recording's other windows share its performance and
  guitar as well as its amp and mic, so RigO's gain is the whole recording chain's, not the amp's alone. A post-hoc
  look in setting space (the review's) found the same DI's other recording as near the unit's label as RigO on two
  DIs and much farther on two; three DIs have one recording each, so recording and performance are not separated
  (not read by sound). The ceiling's best is searched on the unit's own
  other half, RigO on other windows, so the share compares like with like on the held half only. DI 20 is not
  read here.
- **References.** `PF/real/answers/{RigO,RcM}.json`, `PF/real/judge/{RigO,RcM}/`, `PF/real/report-5b2-rigo.json`,
  `report-5b2-rigo-pre.json`, `report-ceiling-1.json`, `report-ceiling-1-within-RigO.json`; `rigo_records`,
  `real_rigo_answers`, `real_rcm_answers`, `cmd_real_report --within`, `cmd_real_ceiling --within` (the share's
  interval by `share_recovered`); ledger `phase_5b2_rigo`, `phase_5b2_rigo_outcome`.
- *Results review (2026-11-01, PR #352, independent):* approved with required changes, all made: the ledger's share
  on one basis (held half), shares compared on the same directions with the share's interval, "not the labels"
  narrowed to their per-recording content with the number of recordings named, the headroom stated as at most
  about 0.15 by a true-DI search, and the clean/crunch remark restated on RigO − S. It found no leakage (no label
  within 10 s, RigO never equal to the unit's label, no judged value or render equal to a stored best).

### F37. Trained on many recordings, the model learns a per-track reading in domain; on real reamps it is not shown (5C pilot)
- **Result.** 5C's pilot as declared and amended (`phase_5c`; the heavy check and the lag tolerance, each
  reviewed before any search render): 215 trusted GOAT units from 130 items searched (11,395 renders), RG trained on
  BKS's and the other GOAT folds' labels (4 folds × 2 seeds), RGshuf with each fold's training GOAT labels permuted
  within amp and class, the centres RcGk, RcBG and RcG; 4,020 read renders, every direction scored (none missing).
- **Numbers** (held half; GOAT by item, 130, with the 4-fold interval; BKS by DI, 8, with the fold interval):

  | Row | Primary interval | Fold interval | Better |
  |---|---|---|---|
  | A: RG − RcGk (GOAT, primary) | −0.053 [−0.077, −0.029] | −0.043 [−0.063, −0.023] | 83 of 130 items |
  | A: RG − RcBG (GOAT) | −0.064 [−0.089, −0.039] | −0.052 [−0.075, −0.030] | 92 of 130 |
  | RG − RGshuf (GOAT) | −0.041 [−0.056, −0.026] | −0.035 [−0.060, −0.010] | 86 of 130 |
  | RGshuf − RcGk (GOAT) | −0.012 [−0.033, +0.010] | −0.009 [−0.051, +0.034] | 75 of 130 |
  | B: RG − RcBG (BKS) | −0.052 [−0.115, +0.011] | −0.047 [−0.104, +0.010] | 7 of 8 DIs |
  | B: RG − Rcs2 (BKS, adoption row) | −0.035 [−0.102, +0.032] | −0.036 [−0.091, +0.020] | 6 of 8 |
  | RG − RGshuf (BKS) | −0.040 [−0.116, +0.037] | −0.026 [−0.085, +0.033] | 6 of 8 |
  | RG − P2a-reals2 (BKS, beside) | −0.064 [−0.130, +0.002] | −0.053 [−0.115, +0.010] | 6 of 8 |
  | RcG − S (BKS, beside) | −0.106 [−0.168, −0.045] | (no models) | 7 of 8 |
  | RcG − Rcs2 (BKS, beside) | +0.052 [−0.026, +0.130] | (no models) | 2 of 8 |

  - Every fold reads RG better than RcGk and than RGshuf on GOAT. On the main-mode lag units alone (`--lag-tol 14`,
    94 items) RG − RcGk is −0.057 [−0.086, −0.028]; on the 6 items with a whole-item lag over 300 samples −0.142
    [−0.275, −0.008].
  - Setting space: RG's answers sit 0.127 from RcGk's and no nearer the units' labels (rms 0.259 against 0.259; S
    0.294). Heads on held GOAT labels: RG's knob NLL is 0.59–0.95 below P2a-reals2's but does not separate RG from
    RGshuf (−0.150 to +0.196, median +0.020); the sound read decides. Guard: no fold's FS or NS knob NLL rises past
    +0.027 in both seeds (one seed of fold 2, +0.034).
  - Lags: every stored lag checked by scan sits at or near the judge's minimum (all 40 BKS units under 0.01 to gain;
    11 of 12 GOAT units under 0.002, one 0.013); see the lag check in 5C's block.
- **Reading** (as declared). A is better and RG − RGshuf is better: a per-track reading is learned in domain, and it
  is the GOAT recordings' own labels that teach it (with the labels permuted the model reads like the centre). It is
  the first per-track reading this plan has shown on amp chains other than the plugin's own renders (F11 and F28
  showed one on plugin renders). RG, from about 160 GOAT recordings per fold, beats the matched centre by 0.053 on
  held capture renders, where F35's arm R, from 10–11 BKS recordings per fold, took none of F36's headroom; this is
  not a like-for-like curve over the number of recordings, since the domain and the chains' spread differ too
  (GOAT's random draw from about 7,000 captures may leave a weaker centre and more headroom), and on BKS RG −
  P2a-reals2 is itself undecided.
  B is undecided: on BKS's real reamps RG leans better than both centres and than RGshuf (6–7 of 8 DIs), but no
  interval excludes 0, so transfer to real amps is not shown. By the map: the full GOAT set does not run; the user
  decides between more real chains and domain work, with A, B and RcG − S as evidence. A capture centre does move
  toward real amps (RcG − S −0.106), though not past BKS's own centre.
- **Caveats.** Capture renders are not real rigs (a capture at one setting with a borrowed IR); 132 of GOAT's 172 DIs
  are one player, mostly on a Strat; the forced amps are a third each by design. BKS is one band, 8 DIs: B's intervals
  are wide (a test panel across bands is proposed). The lag tolerance (72) was chosen after the counts at 14 were
  known; read A holds on the main-mode units alone. Neither label measure shows what RG reads: its answers are no
  nearer the labels in setting space, and the heads do not separate it from RGshuf. So the in-domain gain may rest
  on cues specific to the captures (their level calibration or IR, say), which would fit the missing transfer. Held
  items share the player and guitar with training items (132 of 172 DIs are one player). About 50 capture profiles
  repeat among GOAT's 860 draws, so about 2 repeats are expected among the 215 kept units across folds (negligible).
  RGshuf permutes the training labels before they are cycled to 300 rows per epoch, so its doubled labels in an
  epoch differ from RG's (same inputs, a near-identical label multiset); the run files mark RG and RGshuf by name
  only (`--goat` and `--goat-shuffle` are not in their `flags`).
- **References.** `PF/goat/report-5c-A.json`, `report-5c-A-lag14.json`, `report-5c-shuf.json`, `read-a-beside.py` and
  `.json`; `PF/real/report-5c-B.json`, `report-5c-shuf.json`, `report-5c-centres.json`, `heads-G.json`; runs
  `P2a-goat{k}`, `P2a-goatshuf{k}`; ledger `phase_5c_reads_AB`, `phase_5c_rgshuf_outcome`.
- *Results review (2026-11-01, PR #356, independent):* approved with required changes, all made: "first per-track
  reading" narrowed to chains other than the plugin's own renders; the comparison with F35 stated as not like for
  like; the caveats that neither label measure shows what RG reads (so capture-specific cues are possible), and the
  shuffle-before-cycle and run-flag notes. It recomputed RG − RGshuf, RGshuf − RcGk and A's rows from the judge files
  (within 0.0003) and found the reading on the declared branch.

### F38. Across 7 real-amp bands, a centre learned from many capture recordings beats S; the per-track reading is not shown (5D panel, strong hint)
- **Result.** 5D's panel as declared and amended, read as a strong hint (effective N 14.4 against the minimum's 20;
  the user's choice): 44 units from 16 DIs in 7 new bands (one unit out on the lag cross-check: Jen Hartswick & Nick
  Cassarino's Novacaine, judge lag −171 against −52), every new DI read by its fold's models and centres, as F37;
  2,489 renders (lags 270, reads 1,848, the ceiling 371), every direction scored.
- **Numbers** (held half; capped band weights, DI-clustered 90% interval; equal band weights and band-clustered
  beside):

  | Row | Capped (primary rule) | Equal bands | Band-clustered | Bands reversed |
  |---|---|---|---|---|
  | RG − RcBG_k (primary) | +0.035 [−0.046, +0.116] | −0.013 [−0.099, +0.073] | −0.013 [−0.127, +0.102] | 1 (Aimee Norwich) |
  | RG − Rcs2_k (adoption) | −0.014 [−0.120, +0.092] | −0.078 [−0.192, +0.036] | −0.078 [−0.236, +0.080] | 1 (The Laminar Flow) |
  | RG − S | −0.033 [−0.126, +0.060] | −0.073 [−0.163, +0.018] | −0.073 [−0.193, +0.047] | 0 |
  | P2a-reals2 − Rcs2_k | +0.039 [−0.112, +0.190] | −0.034 [−0.221, +0.153] | −0.034 [−0.279, +0.211] | 3 |
  | RcG − S | −0.069 [−0.114, −0.025] | −0.065 [−0.101, −0.029] | −0.065 [−0.116, −0.015] | 0 |
  | RcBG_k − S | −0.068 [−0.118, −0.019] | −0.060 [−0.101, −0.019] | −0.060 [−0.113, −0.008] | 0 |
  | Rcs2_k − S | −0.019 [−0.091, +0.052] | +0.005 [−0.078, +0.089] | +0.005 [−0.096, +0.107] | 2 |

  - Seven rows were read; the decision checks were declared for the primary only. As descriptive rows, RcG − S and
    RcBG_k − S would pass the primary's checks: the capped interval excludes 0, no band's own interval is reversed,
    and with any band removed the mean keeps its sign and more than half its size (RcG −0.044 to −0.088, RcBG −0.045
    to −0.093). Beside them (undeclared, descriptive, recomputed by the review): RcG − Rcs2_k −0.050 [−0.114,
    +0.014], undecided; RcBG_k − Rcs2_k −0.049 [−0.092, −0.006]. Equal band weights give an effective N of 9.6. Without the high-bleed units RcG − S is −0.118 [−0.179, −0.057]; without the hum-passed
    ones −0.075 [−0.130, −0.021].
  - RG − RcBG_k by class (confounded with band): clean −0.093 [−0.148, −0.038] (Aimee Norwich, Jen Hartswick & Nick
    Cassarino, Port St Willow), crunch +0.099 [−0.009, +0.207], where The Laminar Flow (8 DIs, +0.189) carries it;
    without it −0.042; without the hum-passed units −0.027, without the high-bleed ones −0.007. RG − Rcs2_k on
    clean −0.246 [−0.353, −0.139]. Without all three apart groups (hum-passed, far-mic, high-bleed) RG − S is −0.125.
  - The ceiling (one seeded unit per band, one amp, 52 evaluations): the true-DI search beats S by −0.339 on average
    (−0.028 to −0.584), as on BKS (−0.349). On those 7 units, as a ratio of the summed effects, RcBG reaches 35% of
    it, RcG 31%, Rcs2 30%, RG −2% (the mean of per-unit ratios differs widely: RcBG 10%, Rcs2 5%, RG −69%; Big
    Troubles' ceiling is only −0.028).
- **Reading** (as declared, a strong hint, not a verdict).
  - The primary row is undecided and leans the wrong way under the capped weights: the per-track reading F37 found
    on capture recordings is not shown on real amps across these bands; it leans better on the clean bands and worse
    on crunch, where one band with hum and bleed dominates. By the map: not shown across bands; the user chooses
    between domain work and more real chains.
  - The clearest pattern is the centres' (descriptive): Rc's rule on GOAT's labels (RcG) or on BKS's and GOAT's (RcBG)
    beats S across the 7 bands by about 0.07 and would pass the band checks; BKS's own centre (Rcs2) is not shown to
    (−0.019, undecided, two bands reversed), and RcG − Rcs2_k is undecided. F34 found a real-amp centre beats S on
    BKS's own band; this hints that a centre from many varied chains carries to new bands. The headroom stays large
    (the ceiling −0.34).
  - For D_fix: a lean from a strong hint, not a choice. The declared map for an undecided primary does not make a
    centre a readout candidate, and nothing is acted on from the panel alone. D_fix is chosen on FS, NS and the
    k-fold reads before any V-real read; if V-real were to choose between readouts, that read is labelled
    selection-contaminated.
- **Caveats.** Underpowered (effective N 14.4): an undecided row says little. Class and band are confounded. The
    Laminar Flow, the largest band, is a live room with 3 mics per DI, and 12 of its units carry DI hum; live tracks'
    bleed and room reach RG's input but not the centres'. The ceiling is 7 units, one amp each. The panel's bands are
    rock-leaning with one jazz/soul band. The read answers for these bands' performances.
  - The ear-stage changes were revisions made after the user heard the clips (though before any render), where the
    block had said the panel was frozen after the ear except for failing the minimum: Guitar-TECHS P3 and Dahka Band
    were dropped on measurement (their amp tracks near copies of the DI), and 9 units were heard again with the
    measurement stated beforehand, offered only in bands whose measurement favoured passing; all 7 it passed are
    clean, the class where RG leans better. The read does not depend on it: on the first verdicts alone, RG − RcBG_k
    is +0.036 and RcG − S −0.062 [−0.107, −0.017] (the review's recompute).
- **References.** `PF/panel/units.json`, `ear.json`, `recheck.json`, `lags/`, `answers/`, `judge/`, `ceiling/`,
  `report-5d.json`; `panel-*` in `learn/pipeline_fix.py`, `learn/panel_ear_page.py`, `docs/panel-v1-pairs.json`;
  ledger `phase_5d*`.
- *Results review (2026-11-02, PR #357, independent):* approved with required changes, all made: the centres'
  contrast narrowed to "not shown" with the direct centre rows added as descriptive; the band checks stated as
  declared for the primary only; the D_fix readout made a lean, not a choice, with V-real's selection rule; the
  ear-stage revisions stated as made after the ear, with the first-verdict sensitivity; the ledger's times corrected
  from the commits and files; "45 passed, 44 read". It recomputed every row from the judge files and found no code
  error.

### F39. With the real rows at a quarter of each epoch, D_fix reads FS and NS worse than P2b-wide24; on the stems it reads NS better (D_fix, reads 1 and 2)
- **Result.** D_fix as declared (P2b-wide24's recipe plus every BKS stage 1–2 and GOAT label as real rows in
  backings, 2 seeds; D_fix_k on 4 folds × 2 seeds): 10 trainings (13.2 min each), 3,740 renders (read 1 1,920,
  read 2 BKS 960 and GOAT 860), every model answered with both seeds pooled. The real rows were 606 of 2,393 training
  rows per epoch (306 BKS, 300 GOAT): a quarter. One GOAT read unit (`goat/item_68@35.0#amp_5`, read but unlabelled)
  had no D_fix input; it was built by the same rule (`build-dfix-real --reads-only`, zero renders, never trained on)
  and the read resumed, so read 2 covers all 215 GOAT units as 5C did.
- **Read 1** (FS by band, NS by section; D = D_fix, W = P2b-wide24, lower is closer; 90% clustered intervals):

  | Input, amp | D − W FS | D − W NS | D − S FS | D − S NS | W − S NS |
  |---|---|---|---|---|---|
  | P2b's, true amp | **+0.062 [+0.009, +0.115]** | **+0.123 [+0.074, +0.171]** | −0.127 [−0.306, +0.052] | −0.066 [−0.142, +0.010] | −0.189 [−0.269, −0.109] |
  | P2b's, amp +1 | +0.029 [−0.025, +0.083] | **+0.095 [+0.042, +0.148]** | −0.098 [−0.267, +0.072] | −0.031 [−0.113, +0.051] | −0.126 [−0.200, −0.052] |
  | P2b's, amp +2 | +0.042 [−0.028, +0.111] | **+0.077 [+0.021, +0.133]** | −0.114 [−0.261, +0.033] | −0.086 [−0.165, −0.006] | −0.163 [−0.251, −0.074] |
  | P2d's stems, true amp | +0.026 [−0.007, +0.059] | −0.051 [−0.097, −0.005] | −0.066 [−0.234, +0.102] | −0.077 [−0.146, −0.008] | −0.026 [−0.113, +0.061] |

- **Read 2** (by DI on BKS's 40 units, 8 DIs; by item and fold on GOAT's 215):

  | Row | Mean [90%] | Better |
  |---|---|---|
  | D_fix_k − Rcs2 (adoption; backed, own section) | +0.036 [−0.014, +0.087] | 4 of 8 DIs, 14 of 40 units |
  | D_fix_k − RG (the rung-b base's cost) | +0.071 [+0.038, +0.105] | 2 of 8, 9 of 40 |
  | D_fix_k − S | −0.122 [−0.222, −0.021] | 6 of 8, 29 of 40 |
  | D_fix_k clean − Rcs2 (beside) | −0.022 [−0.059, +0.014] | 5 of 8, 24 of 40 |
  | D_fix_k clean − S (beside) | −0.180 [−0.270, −0.091] | 7 of 8, 36 of 40 |
  | GOAT D_fix_k − RcGk (beside) | +0.010 [−0.011, +0.031] by item; +0.016 [+0.0004, +0.031] by fold | 68 of 130 items; 0 of 4 folds |

- **Reading, by the declared map.**
  - Read 1 is decided worse at the true amp on both sets and on NS at both mismatched amps: **D_fix is not built
    as is; no V-real read happens until a new declaration is reviewed, the real rows' share the suspect.** Read 2's
    adoption row is undecided (D_fix would stand on it alone); read 1 governs.
  - Adding the real rows costs the plugin reading in distribution; on P2b's inputs D_fix is no longer shown better
    than S on NS (−0.066, undecided) where W was (−0.189). Why is a hypothesis, not shown: the real rows' share (a
    quarter of each epoch) draws the fit away from the plugin rows. Its training loss falls faster (3.26 at epoch 59
    against W's 3.82–3.87), but that loss includes the real rows and D_fix takes 38 steps an epoch against W's 28;
    the NS loss does not track the sound read (seed 20261043's best, 5.325, beats W's 5.359). A competing
    explanation is checkpoint choice on a noisy NS loss: seed 20261042's best checkpoint is epoch 10 (418 steps,
    NS loss 5.417 against W's 5.323), inside the pooled ensemble.
  - On the stems the product reads the result is mixed: NS better than W (−0.051) and than S (−0.077), FS leaning
    worse than W (+0.026, 1 of 6 bands better). Beside, not a gate.
  - On BKS D_fix_k sits about where Rcs2 does (backed +0.036, clean −0.022, both undecided) and clearly better than
    S, but behind RG (+0.071): the rung-b base (backings) costs the real-amp read that 5C's clean-input RG had. On
    GOAT the per-track reading RG showed (RG − RcGk −0.053) is gone: +0.010 by item, and by fold narrowly worse
    (+0.016 [+0.0004, +0.031], 0 of 4 folds better; beside, the map unchanged).
- **Caveats.** The intervals cover test sections and units, not training seeds; the two seeds share the backing
  schedule. The NS intervals use the normal quantile for 35 df (`t95`'s fallback), slightly narrow (+0.073 against
  +0.074 at the exact t); no decision flips. The stem row and GOAT's are beside. Read 2's units are BKS's 8 DIs (one band).
- **References.** `PF/runs/P2b-dfix*.json`, `PF/dfix/inputs`, `PF/dfix/lends-*.json`, `PF/sound/answers`, `PF/real/answers/P2b-dfix*.json`,
  `PF/goat/answers/P2b-dfix.json`, `PF/sound/report-dfix-true.json`, `report-dfix-amp+1-true.json`,
  `report-dfix-amp+2-true.json`, `report-dfix-ond-true.json` (read 1, saved after the read with zero renders: the
  launcher's reports ran without `--label`, so they printed but did not save), `PF/logs/dfix-report.log`; ledger
  `phase_dfix_outcome`.
- *Results review (2026-11-02, independent):* approved with required changes, all made: GOAT's by-fold row given
  to four decimal places (narrowly decided worse, beside); the stem result stated as mixed; the "fit harder" reading made
  a hypothesis with the checkpoint-choice alternative; read 1's reports saved. It recomputed every read 1 mean from
  the judge files and checked read 2, the render counts, the row counts and the budget; the read-only unit's inputs
  changed nothing trained or read.

### F40. No real-row share in the joint recipe keeps the plugin read and gains the real-amp read: a third costs the plugin read, a tenth reads real amps about where a model without real rows does (D_fix's amendment, stages A and B)
- **Result.** The amendment as declared (each training real row shown per epoch with probability p; everything else
  as D_fix). Stage A: P2b-dfixp33 and P2b-dfixp10, 2 seeds each (4 trainings, 10.4–11.5 min), 960 renders and W's
  recheck (20 of 20 stored renders identical). Stage B, p10 only: its 8 fold trainings (P2b-dfixp10-k0..k3 × 2
  seeds, 10.4–10.5 min, best epochs 15–59), 2,300 renders (read 1's mismatched amps 480, BKS 960, GOAT 860).
  Every model answered with both seeds pooled. About 3,280 renders and 2.1 h of MPS in all, as declared. The real
  rows were trained on: the training log's real-row loss falls (6.12 at epoch 0 to 4.25 at epoch 55, fold 0
  seed 20261042) and so does the held fold's (6.29 to 4.34).
- **Read 1** (FS by band, NS by section; D_p − W, W = P2b-wide24; lower is closer; 90% clustered intervals):

  | Model, input, amp | D_p − W FS | D_p − W NS | D_p − D_fix NS |
  |---|---|---|---|
  | p33, P2b's, true amp (A) | **+0.078 [+0.025, +0.131]** | **+0.088 [+0.029, +0.148]** | −0.034 |
  | p10, P2b's, true amp (A) | +0.042 [−0.006, +0.090] | +0.002 [−0.049, +0.053] | **−0.121 [−0.171, −0.070]** |
  | p10, P2b's, amp +1 (B) | +0.041 [−0.022, +0.104] | +0.006 [−0.041, +0.052] | **−0.089 [−0.132, −0.046]** |
  | p10, P2b's, amp +2 (B) | +0.084 [−0.010, +0.177] | +0.025 [−0.025, +0.075] | **−0.052 [−0.085, −0.019]** |
  | p10, P2d's stems, true amp (A, beside) | −0.003 | −0.027 | |
  | p33, P2d's stems, true amp (A, beside) | **+0.110** | +0.036 | |

- **Read 2, p10** (by DI on BKS's 40 units, 8 DIs; by item and fold on GOAT's 215):

  | Row | Mean [90%] | Better |
  |---|---|---|
  | D_p_k − Rcs2 (adoption; backed, own section) | **+0.207 [+0.106, +0.307]** | 1 of 8 DIs, 5 of 40 units |
  | D_p_k − RG | **+0.242 [+0.158, +0.326]** | 0 of 8, 0 of 40 |
  | D_p_k − S | +0.049 [−0.003, +0.100] | 2 of 8, 12 of 40 |
  | D_p_k − D_fix_k (beside) | **+0.170 [+0.088, +0.253]** | 0 of 8, 3 of 40 |
  | D_p_k − P2a (beside; P2a has no real rows) | −0.018 [−0.086, +0.050] | 5 of 8, 19 of 40 |
  | P2a − Rcs2 (beside, the reference) | **+0.224 [+0.133, +0.315]** | 0 of 8, 4 of 40 |
  | D_p_k clean − Rcs2 (beside) | **+0.190 [+0.116, +0.263]** | 0 of 8, 4 of 40 |
  | D_p_k clean − S (beside) | +0.032 [−0.038, +0.101] | 4 of 8, 16 of 40 |
  | D_p_k clean − D_fix_k clean (beside) | **+0.212 [+0.157, +0.267]** | 0 of 8, 0 of 40 |
  | GOAT D_p_k − RcGk (beside) | **+0.091 [+0.061, +0.121]** by item; +0.093 [+0.055, +0.131] by fold | 43 of 130 items |
  | GOAT D_p_k − D_fix_k (beside) | **+0.081 [+0.056, +0.106]** by item; +0.077 [+0.041, +0.114] by fold | 37 of 130 items |

- **Reading, by the declared map.**
  - Stage A: p33 is decided worse than W on both sets and fails; p10 passes (undecided on both) and was carried on.
  - Stage B: read 1 is not decided worse at either mismatched amp (FS at amp +2 leans worse, +0.084, 0 of 6 bands
    better), but read 2's adoption row is decided worse: **D_p is not built as is; no V-real read, and no fallback
    to p33 (it failed stage A).** By stage B's map a new declaration is needed; which one is the user's choice (the
    options stage A's stop rule named: domain work, more real chains, real-amp reading kept out of the mix model).
  - What the shares show together: at a quarter (D_fix) the real rows bring BKS level with Rcs2 (+0.036) and cost
    the plugin read; at a third they still cost it; at a tenth the plugin read is not shown worse (undecided; FS
    leans worse at every amp, +0.04 to +0.08) but the real-amp read is lost: D_p10 reads BKS about where P2a,
    trained without real rows, does (+0.207 against Rcs2, where P2a reads +0.224 on the same units; D_p10 − P2a
    −0.018 [−0.086, +0.050], undecided), no better than S, and behind D_fix on every BKS and GOAT row. In this joint recipe the real rows' gain and their cost to the plugin read move together; no share
    tried gives the gain without the cost.
  - This is a statement about one recipe (one shared model, real rows mixed into the epoch, early stopping on
    NS), not about the real labels: D_fix shows they carry a real-amp reading (−0.122 against S on BKS; GOAT level
    with RcGk by item, by fold narrowly worse, F39).
- **Caveats.** The intervals cover test sections and units, not training seeds. Stage A chose p10 on read 1's
  true-amp rows (two candidates), so those rows are optimistic for it; stage B's rows are not selected on. The
  early stopping reads NS (plugin) loss only, so a checkpoint is never chosen for the real-amp read; p10's best
  epochs range 15–59. Read 2's units are BKS's 8 DIs (one band). A pass by "not decided worse" on 6 FS bands is
  weak and the intervals exclude seed variance (the declaration's note): p10's plugin pass may be seed noise either
  way. The NS intervals use the normal quantile for 35 df (`t95`'s fallback), as in F39; no gate flips. Beside,
  p33 − D_fix NS −0.034 [−0.068, −0.0004] is decided only under that fallback (undecided at the exact t), so it is
  left unbolded. The launcher's real-report step stopped on a shell quirk (zsh read `$M:P2a-goat` as a path
  modifier); the first row had printed, and both real and GOAT reports were re-run with the pairs quoted, zero
  renders: every judge file predates both report runs, and the re-run's first row reproduces the launcher's exactly.
  The first p33 run (seed 20261042) ran on the code before 7605d2a (ledger names, guards and the recheck only, not
  training), so its run file names ledger `phase_dfix`; it records share 1/3 and the same inputs hash.
- **References.** `PF/runs/P2b-dfixp*.json`, `PF/sound/report-dshare-p{33,10}*.json`,
  `PF/real/report-dshare-p10.json`, `report-dshare-p10-vsP2a.json`, `PF/goat/report-dshare-p10.json`, `PF/real/answers/P2b-dfixp10*.json`,
  `PF/goat/answers/P2b-dfixp10.json`, `PF/logs/dshare-{a,b}-*.log`, `PF/logs/dshare-b-report2.log`; ledger
  `phase_dfix_share`, `phase_dfix_share_a_outcome`, `phase_dfix_share_b`, `phase_dfix_share_b_outcome`.
- *Results review (2026-11-02, independent):* approved with required changes, all made: p10's plugin read stated as
  not shown worse (FS leaning worse at every amp), not as kept; the "model without real rows" reading given its
  reference (P2a − Rcs2 and D_p10 − P2a, zero renders, saved); the next step attributed to stage B's map. It
  recomputed all 24 read 1 rows from the judge files, re-ran read 2's reports from the stored judge files, and
  checked the render, training and budget counts. Adopted from its suggestions: the interval, re-run and p33-seed caveats.

### F41. On held-out real songs the real rows move the plain model toward S: D_fix reads clearly better than P2b-wide24 and is not shown different from S (D_fix (read 1 failed; gate relaxed at the user's direction), read 3 on V-real-11)
- **Result.** D_fix as built (`P2b-dfix`, both seeds pooled, NS-best) read each V-real-11 part's X-LANCE crop stem,
  the crop's mix brought to −12.25 LUFS and the stem given the same gain (the stems' halves −13.7 to −24.5 LUFS,
  beside P2d's stored stems' median −14.7), told the part's class and each forced amp; P2b-wide24 (W) alike; the
  S-centred readout, RcG and D_fix on the parts' own amp tracks (−13.7 LUFS) beside. 660 renders as declared;
  the answers' hashes were in the ledger before any render; S's 66 fresh renders were identical to phase 4's (33
  of 33 groups) and its positive control passed (max |ln ratio| 0.0001 on 60). The leakage guard found no V-real
  band or song in any of D_fix's 10,792 training sources. No direction dropped, none refused, no quiet input.
- **Numbers** (band-weighted, 7 bands, 90% band-clustered; Wickerman ElecGtr2 and 3 one part on the stems; lower
  is closer):

  | Row | All | Bands better | Part-weighted | Clean (2, descriptive) | Crunch (5, descriptive) |
  |---|---|---|---|---|---|
  | **D_fix − S (primary)** | +0.036 [−0.039, +0.110] | 2 of 7 | +0.038, 4 of 10 parts | +0.061 | +0.025 |
  | W − S (beside) | **+0.228 [+0.065, +0.391]** | 0 of 7 | +0.243, 0 of 10 | +0.369 | +0.171 |
  | D_fix − W (beside) | **−0.192 [−0.348, −0.037]** | 7 of 7 | −0.205, 9 of 10 | −0.309 | −0.146 |
  | D_fix − RcG (beside) | +0.011 [−0.053, +0.074] | 5 of 7 | −0.002, 7 of 10 | −0.029 | +0.027 |
  | RcG − S (beside) | +0.025 [−0.040, +0.090] | 3 of 7 | +0.039, 4 of 10 | +0.090 | −0.001 |
  | S-centred − S (beside) | +0.041 [−0.036, +0.117] | 4 of 7 | +0.028, 6 of 10 | +0.026 | +0.047 |
  | D_fix on the amp track − S (beside; Wickerman 2 and 3 apart) | +0.093 [−0.053, +0.240] | 2 of 7 | +0.118, 2 of 11 | +0.026 | +0.121 |
  | D_fix on the amp track − P4 (beside) | −0.060 [−0.197, +0.078] | 4 of 7 | −0.014, 4 of 11 | −0.002 | −0.083 |

  - D_fix − S by band: Zeno −0.096, Magician's Nephew −0.078, Eat The Feeder +0.007, Diesel13 +0.034, Atlantis
    Bound +0.087, Wall Of Death +0.107, Szymon Skiba +0.187. Leave one band out: +0.010 to +0.057.
  - D_fix − W by band: Diesel13 −0.606, Wall Of Death −0.320, Magician's Nephew −0.182, Zeno −0.135, Eat The
    Feeder −0.088, Atlantis Bound −0.012, Szymon Skiba −0.005. Leave one band out: −0.124 to −0.224.
- **Reading, by the declared map.**
  - The primary is undecided: D_fix does not beat S on held-out real songs. By the map, domain work is proposed
    next (first proposal: a per-row input saying plugin render or real amp), every read as evidence; the user's
    choice stays open.
  - Beside, and the largest real-song movement in this plan: the plain model without real rows (W) reads clearly
    worse than S on V-real (+0.228, 0 of 7 bands better), as P4's clean-input model did (F20, +0.153; P2a on the
    amp tracks, a different model and input); D_fix,
    the same recipe with the real rows, reads clearly better than W (−0.192, 7 of 7 bands, 9 of 10 parts) and
    level with S. In point estimate the real rows take the model most of the way from W to S (+0.228 to +0.036),
    but the primary's interval still allows D_fix up to +0.110 worse than S, so closing the gap is not shown; no
    lead is shown either.
  - D_fix reads level with RcG, the real-amp centre of GOAT's labels (+0.011), and RcG level with S (+0.025): what
    D_fix gives on V-real is not shown to be more than a real-amp centre's. A per-track reading on real songs is
    not shown (as F37–F38 found on real reamps). RcG's gain over S on the real-amp panel (F38, −0.069 [−0.114,
    −0.025]) is not seen on V-real (+0.025 [−0.040, +0.090], 3 of 7 bands better). RcG used 33–43 GOAT labels in
    every group; none fell back to S.
  - On the amp tracks D_fix is not shown better than S (+0.093) nor than P4 (−0.060; P4 is P2a on the amp tracks
    at −21.8 LUFS, a different model and input). The declared separator pattern (a decided loss on the stems with
    the amp-track row near S) is not seen; D_fix on the amp track − on the stem +0.060 [−0.051, +0.171], undecided.
- **Caveats.** V-real-11 is 7 bands and 10 parts; the primary's interval is ±0.074, so an effect under about 0.07 is
  not resolved. D_fix − W is carried by two bands (Diesel13 −0.61 and Wall Of Death −0.32; W's worst bands).
  Diesel13 is Colour Me Red ElecGtr02 and 03, X-LANCE's known stage F failures (ElecGtr03 alone −0.87), so the
  largest gain is where the stem is known to be broken. Every band and leave-one-out row points the same way, and
  without both bands the row is −0.084 [−0.157, −0.011]. The stems of Let's Dance and Wickerman ElecGtr2/3 sit
  about 10 dB below P2d's stored stems' median (the declared rule; the guitar is low in those mixes); Szymon Skiba
  is D_fix − S's worst band (+0.187). The measure DI caps even the truth at about 0.55 of S's distance (F20). D_fix was chosen on reads 1–2 only; its read 1
  failed and the gate was relaxed at the user's direction before this read (`phase_dfix_vreal`). The plugin cost
  (F39) stands. Wickerman ElecGtr2 and 3 have identical stored stems and identical answers. V-real has now been
  read once more; any later choice that uses this read is selection-contaminated.
- **References.** `PF/vreal/answers/DV-*.json`, `S-recheck-dfix.json`, `PF/vreal/judge/`, `PF/vreal/report-dfix-vreal.json`,
  `PF/logs/dvreal-*.log`; ledger `phase_dfix_vreal`, `phase_dfix_vreal_answers`, `phase_dfix_vreal_outcome`.
- *Results review (2026-11-02, independent):* approved with required changes, all made: "close the gap" replaced by
  what the interval allows (up to +0.110 worse than S not excluded); RcG's F38 gain not seen on V-real stated;
  D_fix − W's Diesel13 share tied to X-LANCE's known failures, with the row without both bands (−0.084); the stem
  level range and the ledger's run times corrected. It recomputed every row from the judge files with its own
  script and checked the hashes, S's renders, the counts and the budget. Adopted from its suggestions: the separator
  remark on the declared pattern, the F20 input note, the level, RcG-count and measure-DI caveats.

### F42. Fine-tuning from plugin pretraining beats the joint recipe on real reamps; on held-out real songs it is not shown different from S or from D_fix (FT, read 2 and V-real)
- **Result.** FT (`phase_ft`): P2b-wide24's best state (W) tuned on D_fix's 606 real rows alone (lr 1e-4), the
  epoch count chosen on held real rows. All 8 inner runs at cap 100 ended at the cap (fold j's real loss from W's
  5.97–6.57 still falling at 1.22–3.05), so the declared cap fallback (300) ran (`phase_ft_fallback`); every
  cap-300 inner run stopped on its own, E 159–208. FT_k trained for its inner run's E; the all-labels FT for the
  median, 192 epochs (both seeds). Read 2: 1,340 renders after the 20-render recheck (20 of 20 identical); missing
  0, S dropped 0, refused 0. Read 2's map carried FT to V-real (`phase_ft_carry`): 152 renders (FT 132, 10 S groups
  re-rendered, identical to phase 4's), read 3's exact inputs (asserted equal to F41's recorded ones), F41's stored
  S, D_fix and RcG renders as comparators (F41's rows reproduced to 1e-12 before any row), S's positive control
  passed, the leakage guard clean (FT's 2,170 plugin and 606 real rows, 316 units, 7,900 backings, 406 pool entries).
- **Read 2** (BKS by DI, 8 DIs; GOAT by item, 130 items, the fold interval beside; 90%; lower is closer):

  | Row | BKS | GOAT |
  |---|---|---|
  | **FT_k − D_fix_k (primary)** | **−0.055 [−0.084, −0.027]**, 7 of 8 DIs, 31 of 40 units | +0.001 [−0.016, +0.018], 70 of 130 items (fold −0.008 [−0.035, +0.020]) |
  | FT_k − Rcs2 / RcGk (beside) | −0.019 [−0.062, +0.025], 4 of 8 | +0.012 [−0.011, +0.034], 68 of 130 (fold +0.008) |
  | FT_k − S (beside) | **−0.177 [−0.256, −0.098]**, 7 of 8, 33 of 40 | (no S on GOAT) |
  | FT_k − RG (beside) | +0.016 [−0.027, +0.060], 3 of 8 | |

- **V-real-11** (band-weighted, 7 bands, 90% band-clustered; Wickerman ElecGtr2 and 3 one part):

  | Row | All | Bands better | Part-weighted | Clean (2) | Crunch (5) |
  |---|---|---|---|---|---|
  | **FT − S (primary)** | +0.022 [−0.051, +0.095]; two-look 95% [−0.069, +0.114] | 2 of 7 | +0.019, 3 of 10 | +0.033 | +0.018 |
  | FT − D_fix (beside; selection-contaminated) | −0.013 [−0.089, +0.062] | 5 of 7 | −0.019, 7 of 10 | −0.028 | −0.008 |
  | FT − RcG (beside) | −0.003 [−0.051, +0.046] | 4 of 7 | −0.020, 6 of 10 | −0.057 | +0.019 |

  - FT − S by band: Magician's Nephew −0.127, Eat The Feeder −0.030, Szymon Skiba +0.005, Diesel13 +0.015, Zeno
    +0.038, Atlantis Bound +0.051, Wall Of Death +0.202. Leave one band out: −0.008 to +0.047 (without Wall Of
    Death −0.008).
  - FT − D_fix by band: Szymon Skiba −0.181, Magician's Nephew −0.049, Eat The Feeder −0.037, Atlantis Bound −0.036,
    Diesel13 −0.019, Wall Of Death +0.095, Zeno +0.133.
- **Reading, by the declared map.**
  - Read 2: neither primary row worse and BKS decided better, so FT was carried (two chances at 90%: up to about
    10% false carries under the null). On BKS FT closes D_fix's gap to the real-amp centre (FT − Rcs2 −0.019,
    undecided; D_fix − Rcs2 read +0.036, also undecided) and widens the lead over S (−0.177 against D_fix's
    −0.122); on GOAT it is level with D_fix and with RcGk. FT changed two things at once (sequential tuning, and an epoch count chosen on
    a real loss instead of NS): it beats the joint recipe on BKS, not shown to be pretraining alone.
  - V-real, the primary: FT − S is undecided (+0.022, 2 of 7 bands better). By the map: the user's choice; FT does
    not replace D_fix on this read. FT − D_fix leans better (5 of 7 bands, 7 of 10 parts) but is undecided, and any
    choice between them made from this row is selection-contaminated. FT reads level with RcG: on real songs, as
    D_fix, no per-track reading beyond a real-amp centre is shown.
  - Across this plan's three real sets the models are not shown different from the real-amp centres (BKS Rcs2,
    GOAT RcGk, V-real RcG), and on V-real the centres are not shown different from S. The independent audit of the scoring (2026-11-02, zero renders)
    found no calculation error; it found S chosen partly on V-real's parts (S re-picked without them, S′: S′ − S
    +0.025 [−0.002, +0.051], so FT − S′ is about −0.003, descriptive) and S within 0.000–0.087 of the best of 31–45
    factory presets per amp and class on these clips. A per-track factory pick using the true target and its DI
    (stored label-table distances; 10 of V-real's 11 parts, picked on the search half, scored on the held half)
    beats S by −0.118 [−0.167, −0.069] (descriptive), so per-recording headroom exists that no model here reads.
    The audit's report and scripts: `PF/audit-2026-11-02/` (ledger `phase_ft_audit`).
- **Caveats.** V-real's interval is ±0.073: effects under about 0.07 are not resolved. Wall Of Death carries FT − S
  (+0.202; without it −0.008). V-real has now been read for two candidates (D_fix, F41; FT, here), and the write-up
  says so (FT is the second candidate on V-real; D_fix was the first, F41). The plugin cost, logged and never used
  to choose: FT_k's NS loss rose from W's 5.38–5.48 to 9.3–20.4 at the read state (seed 20261042 12.6–20.4, seed
  20261043 9.3–10.0), while fold k's real loss fell from 5.6–5.8 to 0.91–2.29. E is likely biased low (the inner
  runs repeat each row more often per epoch, as declared). The cap-100 inner runs and the D_fix_k recheck started
  at 15:41–15:43, minutes before the FT code commit and its review changes; the cap-100 runs only decided the
  fallback (all hit the cap) and were superseded, and the render code did not change after the recheck. The all-labels FT's first launch
  refused before any training (a start check compared all eight inner runs with one seed's W; fixed, tested, the
  code re-reviewed). The listening page on 4 non-V-real songs (S, D_fix, W) is with the user, unanswered.
- **References.** `PF/runs/P2b-ft-*.json`, `PF/real/answers/P2b-ft.json`, `PF/goat/answers/P2b-ft.json`,
  `PF/real/recheck-ft.json`, `PF/vreal/answers/FV-P2b-ft-stem.json`, `S-recheck-ft.json`,
  `PF/vreal/report-ft-vreal.json`, `PF/logs/ft-*.log`; ledger `phase_ft`, `phase_ft_fallback`, `phase_ft_answers`,
  `phase_ft_carry`, `phase_ft_vreal_review`, `phase_ft_vreal_answers`, `phase_ft_outcome`, `phase_ft_audit`.
- *Results review (2026-11-02, independent):* approved with required changes, all made: the answers' hash time
  (20:30), the plugin cost stated from the logs, the per-track factory pick qualified and the audit kept with the
  data, D_fix − Rcs2's own interval named, the budget's punctuation and FT's MPS line. It recomputed every read 2
  and V-real row, the epochs, the provenance and the hash-before-render order with its own scripts. Adopted from its
  suggestions: "not shown different from" the centres, the ROADMAP's basis for FT's recipe, the E-bias caveat, the
  run-order note and the outcome's start time.

### F43. Drive carries most of FT's score over S on real reamps; tone and cab carry a little, and the parts add up (phase_ft_groups, descriptive)
- **Result.** FT's BKS read 2 answers split by control group (`phase_ft_groups`): rev-g (FT with g at S) and
  add-g (S with g from FT) for drive, tone and cab, 2,880 renders after the answers' hashes were in the ledger;
  S's stored renders and lags reused; missing 0, S dropped 0, refused 0. Effects and the gate are off in S and FT
  on every answer, so they are not in this read. By DI (8 DIs, 90%; lower is closer):

  | Row | All | DIs better | Units better | Group's mean unit move |
  |---|---|---|---|---|
  | FT − S (total; read 2's, reproduced) | **−0.177 [−0.256, −0.098]** | 7 of 8 | 33 of 40 | |
  | add-drive − S | **−0.143 [−0.206, −0.079]** | 8 of 8 | 35 of 40 | 0.120 |
  | add-tone − S | **−0.021 [−0.042, −0.000]** | 7 of 8 | 26 of 40 | 0.033 |
  | add-cab − S | −0.019 [−0.055, +0.017] | 5 of 8 | 27 of 40 | 0.101 |
  | FT − rev-drive | **−0.135 [−0.200, −0.070]** | 8 of 8 | 35 of 40 | |
  | FT − rev-tone | +0.004 [−0.026, +0.033] | 4 of 8 | 15 of 40 | |
  | FT − rev-cab | −0.034 [−0.073, +0.005] | 6 of 8 | 30 of 40 | |
  | FT − S − Σ(add-g − S) (the interaction) | +0.006 [−0.014, +0.026] | | | |

  Per amp (add-g − S; PR12's drive better on 7 of 8 DIs): PR12 drive −0.121, tone +0.002, cab −0.014 (FT − S −0.154); SW50R drive −0.166, tone
  −0.036, cab −0.034 (FT − S −0.209); AC20 drive −0.141, tone −0.029, cab −0.010 (FT − S −0.167).
- **Reading.** About 80% of FT's gain over S on real reamps is its drive (input gain, the amp's volume and power,
  the pedals): moving only those from S to FT's values gives −0.143 of the −0.177, on all 8 DIs and every amp, and
  taking them back loses −0.135. Tone gives a small gain (−0.021, just decided) and cab none that is decided
  (−0.019). The parts add up (interaction +0.006, undecided), so FT's changes act mostly independently in the score.
  Tone is not consistent between the two ways: adding FT's tone to S gains −0.021, taking it back from FT costs
  nothing (+0.004, 4 of 8 DIs); the interaction's interval (±0.02) is as wide as tone's or cab's whole share, so
  "the parts add up" does not mean no interaction. Per unit of knob move the score credits drive most (about 1.2
  per unit), tone next (about 0.6) and cab least (about 0.2); this mixes how right FT's moves were with how
  sensitive the judge is, and leaves out switches and choices (mic type, pedals on or off). F44 found the judge
  weighs input gain above the ear, so this ordering is the judge's, not shown to be the ear's.
- **Caveats.** BKS only (one band of real reamps, 8 DIs); FT's answers, not a controlled step per group, so the
  groups' moves differ in size and direction; unit moves are in the model's ranges, not in audible units. The
  compressor (34 PR12 answers) counts as drive. `pr12Dwell` counts as silent with the spring at 0 (an assumption;
  no render depends on it).
- **References.** `PF/real/answers/FTg-*.json`, `PF/real/judge/FTg-*/`, `PF/real/report-ftg.json`, `PF/logs/ftg-*.log`;
  the interaction and per-amp rows from `PF/real/ftg-derived.py` (the results review's script; output `ftg-derived.txt`);
  ledger `phase_ft_groups`, `phase_ft_groups_answers`, `phase_ft_groups_outcome`.

### F44. The judge weighs treble well above the ear, drive above it, and reverb below it (phase_judge_ear, descriptive)
- **Result.** The user rated 26 blind, level-matched pairs (build 55d54a4994d2, answered 2026-11-03): one verified
  clean single-note DI through S clean (PR12) and S crunch (SW50R), one group moved from S per pair. The judge's
  distance (both halves averaged) and the ear's rating:

  | Group (step) | Clean, small | Clean, large | Crunch, small | Crunch, large |
  |---|---|---|---|---|
  | drive (+4, +10 dB) | 0.84 same | 2.15 same | 1.17 same | 2.53 barely |
  | tone (treble ±0.15, ±0.35) | 2.62 barely | 3.91 barely | 0.65 same | 2.79 same |
  | cab (mic distance; mic type) | 0.20 same | 0.40 same | 0.21 barely | 0.51 same |
  | reverb (mix 0.15, 0.40) | 0.30 same | **2.10 clearly** | 0.17 barely | **1.59 clearly** |
  | delay (mix 0.15, 0.40) | 1.18 barely | **2.78 clearly** | 0.80 same | 2.02 barely |
  | spring (0.2, 0.5) | 0.87 same | 1.90 barely | 0.38 same | 0.95 same |

  Both catches (S against itself) scored 0 and were heard as the same. 14 inversions by the declared rule (a pair
  heard clearly different that the judge scores below another group's pair heard same or barely), 10 of them on
  both halves and 5 of those within one preset: on PR12 clean, treble +0.35 (3.91, barely) above reverb 0.40 and
  delay 0.40 (2.10 and 2.78, clearly); on SW50R crunch, drive +10 dB, treble −0.35 and delay 0.40 (2.53, 2.79,
  2.02; barely, same, barely) above reverb 0.40 (1.59, clearly). Rank agreement between the judge and the ear over
  the 24 pairs: Spearman 0.43; within the effects (reverb, delay, spring) 0.72; within drive, tone and cab 0.36.
- **Reading.** By the declared rule the judge mis-weights. It scores treble and drive changes the ear calls the
  same or barely different above reverb changes the ear calls clearly different (on SW50R crunch, +10 dB of input
  2.53, barely, and treble −0.35 2.79, same, above reverb 0.40 1.59, clearly; on PR12 clean, treble +0.35 3.91,
  barely, above reverb 0.40 2.10, clearly): treble weighs well above the ear (ratios 1.4–2.5 on both halves), drive
  above it (two inversions on both halves, 1.35 and 1.60), reverb less (and clean delay 0.40, but only against
  treble +0.35). Within the effects the judge orders the pairs much as the ear does, though crunch reverb 0.40 still
  sits below crunch delay 0.40 and clean spring 0.5; cab steps are small to both. What it changes: every by-sound
  read so far (F1–F43) is scored by this judge. F43's drive share includes input gain, which this page found the
  judge weighs above the ear (one single-note DI); its other drive controls were not tested. So how much of FT's
  lead is audible is not known; and S and FT have every effect off, so no read has scored the effects. The judge's
  own options do not fix it (exploratory, on these same answers, no renders): the Bark floor (judge v3), hearing
  weighting, union bands, 3 s tails and a 60 dB floor give Spearman 0.43–0.50 (the 60 dB floor cuts the inversions
  from 14 to 11; 3 s tails equal the default on every pair and union bands move them by at most 0.03, as the DI
  plays throughout, so those two are not really tested here), and the tonal and frame-by-frame parts alone 0.47
  and 0.44. The treble steps stay high in both parts, drive in the frame-by-frame part (in the tonal part only
  clean +10 dB), which suggests a different kind of measure, not a setting. Proposed next, before more recordings
  are scored: a revised judge, declared and reviewed, checked on a fresh blind page (another DI and other presets)
  that was not used to build it.
- **Caveats.** One listener, one DI, two presets: descriptive. The DI is single-note lead playing; the user noted
  that chords and single notes respond differently to distortion, so drive may be more audible on chords. The ear's
  question was how different two clips sound, not which is closer to a target. "Reverb" is the plugin's default
  1.48 s room; a cab step moves the left of two blended mics; the judge skips the first second; the page
  level-matched each pair, as the judge takes out level. Each pair appeared once (no repeat to check consistency),
  in seeded order, both clips looping with an instant switch. Only 3 of 24 pairs were heard clearly different and
  none very, so all 14 inversions rest on those 3 answers (7 on crunch reverb 0.40 alone); no answer carries a
  sure/unsure mark. Agreement differs by preset: Spearman 0.71 on PR12 clean, 0.07 on SW50R crunch. Nothing here
  fits a new weight, which needs its own check.
- **References.** `~/ndsp-presets/learn/trusted-data/judge-ear/` (plan.json, measure.json, score.json, renders/, explore/ for the options screen);
  the answers `~/ndsp-presets/listening/judge-ear/private/answers-55d54a4994d2.txt`; code `learn/judge_ear.py`;
  ledger `phase_judge_ear`, `phase_judge_ear_amendment`, `phase_judge_ear_outcome`.
- *Results review (2026-11-03, independent, of F43 and F44):* approved with required changes, all made. It rebuilt
  the blind order from the seed, recomputed every distance, rating, inversion, Spearman figure and the options
  screen, and every F43 row (interaction and per-amp rows included). Required: treble well above the ear and drive
  only above it (drive's clean +10 dB inversion fails on one half); input gain is the only drive control tested;
  the inversions rest on 3 answers; agreement by preset; the page loops with a free switch; a v2-page claim with no
  record dropped; F43's per-unit ordering the judge's; F43's derived rows stored; the budget.

### F45. On headphones the mis-weighting holds and grows: every large effect re-heard is heard clearly, the treble steps are not (phase_judge_ear_recheck, descriptive)
- **Result.** The user had heard F44's page on phone speakers. 13 items re-heard on headphones (build
  061051010403, answered 2026-11-03), the same renders and clips: every pair in one of F44's inversions, clean drive
  +4 dB as a low comparator, the clean catch, clean treble +0.35 twice. Judge distance; phone rating → headphones:

  | Pair | Judge | Phone | Headphones |
  |---|---|---|---|
  | clean drive +4 dB | 0.84 | same | same |
  | clean drive +10 dB | 2.15 | same | same |
  | crunch drive +10 dB | 2.53 | barely | **clearly** |
  | clean treble +0.15 | 2.62 | barely | same |
  | clean treble +0.35 (twice) | 3.91 | barely | same; barely |
  | crunch treble −0.35 | 2.79 | same | barely |
  | clean reverb 0.40 | 2.10 | clearly | **clearly** |
  | crunch reverb 0.40 | 1.59 | clearly | **clearly** |
  | clean delay 0.40 | 2.78 | clearly | **very** |
  | crunch delay 0.40 | 2.02 | barely | **very** |
  | clean spring 0.5 | 1.90 | barely | **clearly** |
  | clean catch | 0 | same | same |

  27 inversions by the declared rule, the repeat's two rows both counted (21 distinct pairs; 17 on both halves, 8
  of those within one preset), against 14 on the phone, 10 of which persist; the other 4 dissolved because their
  quiet pair (crunch drive +10 dB, crunch delay 0.40, clean spring 0.5) is now heard clearly or very.
- **Reading.** By the declared rule the inversions persist, so the judge revision goes ahead (declared and
  reviewed). F44's treble and reverb readings stand; its drive reading holds on the clean amp only: crunch drive
  +10 dB is now heard clearly and the judge puts it below the treble steps. On headphones the ear hears every large
  effect re-heard clearly or very (5 of the first page's 6; crunch spring 0.5, same on the phone, not re-heard) and
  crunch drive +10 dB clearly, while it hears the three treble steps and clean drive at both steps as the same or
  barely different; the three treble steps are the pairs the judge (1st, 2nd and 4th of 24), CDPAM and Zwicker
  loudness (top 3 each, `judge-ear/explore/`) score highest. Neither of the judge's parts alone tracks the ear here
  (tonal −0.23, frame-by-frame −0.14 over these items; both put clean treble +0.35 first). This suggests the
  revision needs a term for what time effects add (energy and decay after notes, repeats) and less weight on
  steady treble against drive; reweighting the present two parts cannot do it, as both put the treble steps on
  top. What it changes: the reads' scores have weighed steady treble changes the ear barely hears above effects it
  hears clearly; S and FT have every effect off, so the effects, which the ear hears most, were never scored; and a
  +10 dB input-gain step is heard clearly on SW50R crunch and not on PR12 clean (one single-note DI), while whether
  FT's own drive moves are audible is still not known.
- **Caveats.** One listener, one sitting, one single-note DI, two presets: descriptive. The 11 pairs (12 items with
  the repeat) were chosen for their inversions, so rank agreement on them is not the judge's agreement in general:
  judge vs headphones −0.21 with the repeat's two rows, −0.08 with it averaged (the phone ratings on the same
  items −0.03). Pairs not re-heard (crunch spring 0.5, the small steps but clean drive +4 dB, the cab steps, the
  crunch catch) could form new inversions. The repeat split mildly (same, barely); the catch was heard as the same.
  The clips were heard a second time, so familiarity may play a part. The listener knew, before this page, that the
  measures rank the treble steps large. Headphones: the user agreed to them and the page asked for them.
- **References.** `~/ndsp-presets/learn/trusted-data/judge-ear/score-recheck.json`; the answers
  `~/ndsp-presets/listening/judge-ear-recheck/private/answers-061051010403.txt`; ledger `phase_judge_ear_recheck`,
  `phase_judge_ear_recheck_outcome`.
- *Results review (2026-11-03, independent):* approved with required changes, all made. It reproduced the table, the
  counts and the sha from the key, the answers and the stored scores. Required: 5 of 6 large effects re-heard, not
  all; the "scores highest" claim kept to the treble steps; the repeat made explicit in the counts (21 distinct);
  F44's drive reading kept to the clean amp; the revision also needs less weight on steady treble; F43's drive left
  open; the repeat, familiarity and the pairs not re-heard as caveats.

### F46. Steady tilts of 6 dB are barely heard on this page, and neither revised judge removes a single within-preset inversion (phase_judge_ear_v4 stage A, descriptive)
- **Result.** *Anchors* (headphones, build 397f8ad7b579, 2026-11-03): S's stored renders through RBJ shelves of
  known gain, level-matched by the page. J0's distance and the rating:

  | Anchor | J0 | Ear |
  |---|---|---|
  | PR12 clean, high shelf +12 dB (positive control) | 3.16 | very (sure) |
  | SW50R crunch, high +6 | 1.81 | clearly (sure) |
  | PR12 clean, high +6 / high −6 | 1.62 / 1.56 | barely (sure) / barely (unsure) |
  | PR12 clean, low −6 | 0.37 | same (sure) |
  | SW50R crunch, low −6 / low +6 | 0.48 / 0.59 | barely (unsure) / barely (unsure) |
  | PR12 clean high +3; SW50R crunch high −3 | 0.81; 0.91 | same; same (sure) |
  | PR12 clean, reverb 0.40 (known heard) | 2.10 | clearly (sure) |
  | catch | 0 | same (sure) |

  One of the six 6 dB shelves was heard clearly: the declared outcome is that steady tilts of that size are not
  heard on this page. *In-sample screen* (`judge-ear/v4-screen.json`; 33 rated items: F44's 24 pairs, F45's
  re-heard ones with their headphone rating, and the 9 anchors): the single-note DI has no note end by the
  declared detector (it plays within 40 dB of its peak throughout), so the decay part never applies and J2 equals
  J2-fallback. Cross-group gamma: J0 +0.449, J1 +0.449, J2 +0.430 (fitted w_t 1.0). Of F45's 21 distinct
  inversions J1 leaves 17 and J2 18; of the 8 within one preset on both halves, every candidate leaves all 8.
- **Reading.** By the declared rule J1 and J2 are reported controls, not candidates, so stage B has nothing to
  test and is not run as declared. Weighting bands by loudness changes the ranking little (gamma unchanged at
  +0.449; J1/J0 from 0.66 to 1.15: the low shelves fall by 26–34%, delay and reverb rise by 8–15%, the rest within
  8%), and the declared decay part finds no note end on this DI, whose notes ring into the next within 40 dB of its
  peak. Six of the 8 within-preset inversions have a large tone step scored 1.3–2 times above the effect, beyond
  what a reweighting of a few percent can move. J2's fitted w_t sits at the top of the declared grid (gamma rises
  with it), so weighting the tonal part above 1 was not tested. On the anchors J0 orders the tonal changes much as
  the ear does (the +12 dB shelf highest; gamma +0.70 on the anchors, the misses being the 3 dB high shelves, heard
  the same, scored above the 6 dB low shelves, heard barely); what it does not do is place
  them against the treble steps and time effects as the ear does: the clean treble step (J0 3.91, heard the same or
  barely) scores above both the +12 dB shelf (3.16, very) and reverb 0.40 (2.10, clearly). For this
  listener on this page, steady tonal changes mostly need to be large (around 12 dB) to be heard clearly (one 6 dB
  shelf, crunch high +6, was), while effects of moderate mix are heard clearly; the judge's scale puts a 6 dB high
  shelf at about three quarters to 0.86 of a clearly heard reverb, a 6 dB low shelf at about a fifth to 0.28.
- **What it changes.** Neither revision is built. The judge stays as it is, with a known limit: on single-control
  changes it ranks tonal changes the ear barely hears above effects it hears clearly, and S and the models have
  every effect off, so their reads never scored effects. How to proceed is the user's decision.
- **Caveats.** One listener, one sitting per page, one single-note DI, two presets: descriptive. Three of the
  six 6 dB ratings were marked unsure. The page asks "how different", not "which is closer to a target", and
  level-matches every clip; the judge's earlier agreement with the ear was on whole-preset comparisons against a
  recording (`docs/measuring-closeness.md`). The screen is in-sample (the anchors were heard after the declaration,
  the other items before it). On this single-note DI the declared detector finds no note end (the DI stays within
  40 dB of its peak), so the decay part, the term meant for what time effects add, is untested, not refuted; the
  declaration expected a strummed chord DI to trigger the fallback too, so this detector would likely leave it
  untested in stage B as well. Bias: the listener knew the hypothesis (the judge over-counts treble; effects are
  heard); the page named nothing. J1 converts Bark to Hz by Traunmüller's formula, within about 1% of mosqito's
  table above 2 Bark (below 200 Hz it differs, where the bands carry little weight).
- **References.** `~/ndsp-presets/learn/trusted-data/judge-ear/anchors.json`, `anchors-score.json`,
  `v4-screen.json`; the answers `~/ndsp-presets/listening/judge-ear-anchors/private/answers-397f8ad7b579.txt`;
  code `learn/judge_ear.py` (`anchors`, `anchors-score`), `learn/judge_v4.py`; ledger `phase_judge_ear_v4`,
  `phase_judge_ear_v4_stage_a_outcome`.
- *Results review (2026-11-03, independent):* approved after four text changes, all made. It reproduced every
  anchor distance with its own shelves, the screen's J0 on all 33 items, the gammas, the inversions left and the
  set of 8, checked that the DI really has no note end by the declared detector (its notes decay 20–30 dB, never
  40), and that the code follows the declaration. Required: J1's change stated by item, the anchors' order, the
  decay part untested in the header, the bias caveat and the decision's place.

### F47. On a chord DI the carry-over part makes the judge worse: effects are heard far less than on single notes, and J0 already ranks the page well (phase_judge_v5, the fresh page)
- **Result.** The fresh blind page (headphones, build 9140fa6a723e, 2026-11-03; 30 items, every answer marked
  sure; both catches heard as the same). Before scoring, the page's 60 clips were decoded and matched to the key by
  correlation against the intended level-matched audio: 0 mismatches (`judge-v5/page-audit.txt`). J0 / J5 (w_c 8,
  frozen) and the rating, per item against S unless stated:

  | Item | AC20 clean J0 / J5 | Ear | PR12 crunch J0 / J5 | Ear |
  |---|---|---|---|---|
  | drive +4 dB | 1.23 / 1.30 | same | 0.66 / 0.91 | same |
  | drive +10 dB | 2.93 / 2.99 | very | 1.45 / 1.86 | same |
  | tone 0.30 | 1.93 / 1.98 | clearly | 0.97 / 1.38 | same |
  | tone 0.70 | 2.98 / 3.03 | very | 1.74 / 2.01 | barely |
  | cab (next mic) | 0.55 / 0.56 | same | 0.46 / 0.46 | same |
  | reverb mix 0.15 | 0.48 / 1.45 | same | 0.11 / 0.16 | same |
  | reverb mix 0.40 | 1.77 / 3.70 | barely | 0.80 / 1.40 | same |
  | reverb decay 1.48 vs 3.0 s | 0.62 / 1.09 | same | 0.37 / 0.66 | same |
  | delay mix 0.15 | 1.10 / 2.58 | same | 0.26 / 0.55 | same |
  | delay mix 0.40 | 2.05 / 3.45 | barely | 0.70 / 1.38 | same |
  | delay time 500 vs 300 ms | 1.22 / 1.49 | same | 0.79 / 0.89 | same |
  | combined | 1.91 / 2.78 | same | 0.85 / 1.34 | same |
  | anchor high +6 dB | 1.31 / 1.31 | clearly | 1.83 / 1.84 | very |
  | anchor low −6 dB | 0.97 / 1.00 | same | 0.95 / 0.96 | same |
  | catch | 0 / 0 | same | 0 / 0 | same |

  Primary (declared): cross-group gamma J0 +0.863, J5 +0.640; J5 − J0 −0.224 [−0.351, −0.063] (18 clusters, 2,000
  resamples kept). Within the effect groups and within tone and drive both judges order the items as the ear does
  (gamma 1.0 each); the whole loss is J5 lifting effects above tone and drive steps heard more. F44's inversion rule:
  J0 8 (7 of them a +6 dB high-shelf anchor heard clearly or very scored below a large clean effect heard barely;
  the eighth clean tone 0.30 below clean delay 0.40), J5 26. Tonal trigger: none (no effect was heard clearly or
  very). Reported beside: without the anchors J0 +0.942, J5 +0.808, J5 − J0 −0.135 [−0.259, +0.031]; clean alone
  −0.327 [−0.532, 0.000], crunch alone −0.174 [−0.400, 0.000] (9 clusters each).
- **Reading.** By the declared rule J5 is undecided and not adopted; the effect size says more: the interval lies
  wholly below 0, so on this page the carry-over part makes the judge's ranking worse. On this chord DI this listener
  barely hears the effects: of the 12 effect items (reverb, reverb decay, delay, delay time, each preset) only clean
  reverb and delay at mix 0.40 were heard, and barely; on F44/F45's single-note DI, reverb, delay and spring of
  the same mix were heard clearly or very. The strummed chords ring into each other and cover what the effects add,
  as the product check already saw in C (near 0 on half A, which has no fall). Tone moves the other way: the AC20
  cut steps and the +6 dB high shelves were heard clearly or very, where F44–F46's PR12 clean treble step and
  6 dB shelves were mostly the same or barely. J0, built without either page, ranks this page well (+0.863; +0.942
  without anchors); its misses are the high shelves scored below large clean effects. So the weight of an effect
  against a tone change depends on the playing (and perhaps the preset; the two pages differ in both), and a fixed
  weight fitted on single notes over-counts effects on chords. Real songs hold both kinds of playing, so a fixed
  weight would fit neither. The declared next steps fall away: adoption on this evidence and a second pooled
  page both have nothing to rest on (a pooled gain would need the second page to reverse this one), and the tonal
  revision is not triggered.
- **What it changes.** J5 is not adopted; J0 stays the judge, with F44–F46's limit narrowed: J0 under-counts
  effects on sparse single-note playing and does not on strummed chords. With the product check (C reads tone,
  compression, room and bleed on real references) and the separator check (J0 barely sees effects through a stem),
  an effect part in the closeness judge is not the route for now; effects follow song research (the user,
  2026-10-27: sound-alike presets are fine, faint effects barely matter). Next on the plan: the approved real-amp recordings and a fresh real-song test, scored with J0.
- **Caveats.** One listener, one sitting, one chord DI, two presets (both different from F44's): descriptive; the DI
  and the presets change together, so playing and preset are not separated. The percentile interval may
  under-cover with 18 clusters (stated in the declaration). The reverb-decay and delay-time items share renders
  with the mix-0.40 items, so their clusters are not fully independent. The page asks "how different", not "which
  is closer to a target", and level-matches every clip. Bias: the listener knew the hypothesis (effects
  under-counted) and rated against it.
- **References.** `~/ndsp-presets/learn/trusted-data/judge-v5/score.json`, `measure.json`, `page-audit.txt`
  (`page-audit.py`); the answers `~/ndsp-presets/listening/judge-v5/private/answers-9140fa6a723e.txt`; code
  `learn/judge_v5.py` (`score`); ledger `phase_judge_v5`, `phase_judge_v5_frozen`, `phase_judge_v5_outcome`.

## Budget

- **Renders used (2026-10-31):** phase 1b 2,612 (the control 232, the doubles 2,380); the ladder's by-sound read
  2,160 (controls 480, S and the constant 480, four rungs 960, the pull 240); the isolated tests 3,600 (the amp mismatch
  960, mastering 240, the switch rules 480, augmentation 240, the size curve 1,440 with the pooled seeds, the backing
  test 240); P4 438 and its dry readout 198; phase 5A 240 and its seed 2 240; 5B.1 960, 5B.1b 720. About 11,170 in all
  before 5B.2. **5B.2 (2026-11-01):** the stage 1 ceiling 6,840; arm P 1,200, its P-Sc 480 and its FS/NS read 480;
  Rc 240; arm R 480: 9,720, about 20,890 in all. Stage 2: its search 10,725, Rcs2 240, arm R's read 480: 11,445,
  about 32,340 in all. RigO and RcM 432: about 32,770 in all. **5C (2026-11-01):** the lag pass 1,398, the lag
  diagnostic 24, the search 11,395 (12,793 label renders against the declared about 15,600: 215 trusted units
  against about 264), the centres' reads 1,340 and RG's 1,340, the lag scans 504 (24 + 480): about 16,000, about
  48,770 in all; RGshuf's reads 1,340, about 50,110 in all. **5D (2026-11-01/02):** the lags 270, the reads 1,848,
  the ceiling 371: 2,489, about 52,600 in all. **D_fix (2026-11-02):** read 1 1,920, read 2 1,820 (BKS 960, GOAT
  860): 3,740, about 56,340 in all. **D_fix's amendment (2026-11-02):** stage A 960 and W's recheck 20, stage B
  2,300 (read 1 480, BKS 960, GOAT 860): 3,280, about 59,620 in all. **D_fix's V-real read (2026-11-02):** 660,
  about 60,280 in all. **FT (2026-11-02):** the recheck 20, read 2 1,340, V-real 152: 1,512, about
  61,790 in all. **FT's control groups (2026-11-02):** 2,880, about 64,670 in all. **The judge against the ear
  (2026-11-02):** 60 (56, and 4 after the amendment), about 64,730 in all.
- **MPS used:** about 4 h before 5B.2 (P1 two inputs, the four rungs, P2a's second seed, the augmentation, size and
  backing runs, the k-fold, phase 5A's two 10-minute seeds); 5B.2's 12 trainings about 2 h more (arm P 4 × 7.2–8.4 min,
  arm R 8 × 11.4 min); stage 2's 8 trainings 1.5 h more (8 × 11.4 min); 5C's RG 8 trainings 1.75 h more (8 × 13.0–13.3
  min), RGshuf's 8 1.75 h more (8 × 13.0–13.1 min); D_fix's 10 2.2 h more (10 × 13.2 min); its amendment's 12 2.1 h
  more (stage A 4 × 10.4–11.5 min, stage B 8 × 10.4–10.5 min); FT's 26 trainings about 4.9 h more (8 cap-100 inner
  runs 51 min, 8 cap-300 inner 136 min (one 46.7 min), 8 FT_k 85 min, 2 all-labels 22 min), against the declared
  about 1 h before the fallback.
- **Disk:** P2's inputs about 0.3 GB; phase 1b's audio and features about 1.2 GB; the 31 GB guard holds.
- Every render: isolate=True, a discarded priming render, 0.25 s trimmed, at most 3 render processes,
  `setopt no_bg_nice`. V-real is read only in P5's stored distances, phase 4, D_fix's declared read (F41) and FT's (F42). (5B.1c
  ran the model on V-real's inputs, zero renders and nothing judged, before it was withdrawn.)

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
