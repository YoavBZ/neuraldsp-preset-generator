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
amps) D_fix itself was read on V-real with the plugin read as a cost beside (F41): by the score it reads level with S
on held-out real songs (+0.036, undecided) and clearly better than the same recipe without real rows (−0.192, 7 of 7 bands),
which reads clearly worse than S (+0.228); level with a real-amp centre, so no per-track reading is shown. Proposed
next: domain work (a per-row input saying plugin render or real amp); the user's choice stays open. At the user's
suggestion FT (F42) used the plugin renders as pretraining and tuned on the real rows alone: better than D_fix on
real reamps (BKS −0.055) and, by the score, level with S, D_fix and RcG on held-out real songs (FT − S +0.022, undecided). Proposed
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
The fresh page (F47): J5 − J0 −0.224 [−0.351, −0.063] (−0.135 [−0.259, +0.031] without the offline anchors); by
the declared rule J5 is not adopted, and J0 stays. On this chord DI the effects were barely heard. Effects follow song research in the product for now, and a
robust effect part stays a research target. Next: the approved real-amp recordings and a fresh real-song test,
scored with J0.
The user chose to stop on J5 and take an effects route: a blind reader of reverb and delay on the separated stem.
Its zero-render first test (F48): on the chord DI the product's own measures read neither effect, even without a
backing (the echo detector abstains on strummed chords; the reverb rule fires rarely, and more often without a
reverb). The echo leaves a trace at the known lag; whether a reader can find it blind is untested. The reader (E1)
learns both, declared next.
The learned reader (F49, zero renders): on the separated stem it hears that reverb or delay is on, a little (AUC
0.61 for the stronger third of each, where the preset cannot give it away); it reads no knob beyond knowing the
preset draw, and even on the clean target it reads neither reverb decay nor delay time, though a simple peak picker
with no training finds the echo's time there (44% within ±10%, against 7% for a guess). Next, E1c (zero renders): a
learned head that finds the echo's lag, on the stem, against that picker.
E1c (F50, zero renders): delay time does not read on the stem or the mix, by the learned head or by the picker (a
few hits on the strongest delays); on the clean target the head matches the picker's hits. For these readers on
the stored features the echo's time is lost when the backing is added, and E1b is not declared. Next: the cloud
researcher's survey of proven blind effect-estimation tools (asked at the user's prompt) decides whether an
existing estimator is tested on rebuilt, re-separated stems (zero renders), or finer features are built.
The survey found no proven tool (none reads guitar effect settings from chords in a mix). Its cheapest idea, a
long-window cepstrum (F51, zero renders, no training): on the clean targets it reads delay time better than the
picker (57% within ±10%, 84% on the strongest third; on the faintest third its error is worse than a guess's) and
tells delay on from off at 0.92 there; E0's stems mostly tested their chord DI, on which it fails even without a
backing. Next, E1e: the wide draws' mixes rebuilt and
re-separated (zero renders), the cepstrum read on their stems.
E1e (F52): on those stems the cepstrum hits the delay time 22% of the time (the picker 14%), but its error is
worse than a guess's and a confident peak does not say when it is right: delay time does not read on the stem.
The loss is the backing's. By the declared branch the masking renders are proposed, not run; the choice between
them and the main line (the approved real-amp recordings and a fresh real-song test) is the user's. Effects follow
song research in the product meanwhile.
The user chose the main line, neither fallback rule and no scale for now (2026-11-04), and corrected the reading:
"level with S" is the score's, not the sound's. The ear so far (F53) has heard real room above S, but no current model
on a song's own performance. So the main line starts with L0, a blind ear read of S, FT, D_fix and W on V-real's parts
in their own performances; then the recordings (L1) and the fresh real-song test (L2), scored with J0 and the ear.
L0 (F54, one listener, 10 parts): W is heard below S, and the score agrees. FT and D_fix are not known by ear: FT's
rank gap is −0.07 [−0.86, +0.71], D_fix's −0.43 [−1.00, +0.21]. Beside that, S is rated "not close" on 3 of 4 clean
parts, FT and D_fix are heard far closer on two of them (picked after the answers) while the score barely moves, and
crunch leans to S; class, amp and S's setting cannot be pulled apart here. The ear-score check is not triggered, but
W carries the agreement: among S, FT and D_fix, agreement is not shown (+0.04 [−0.29, +0.39]; wide, so weak agreement
is not ruled out). The ML review of 2026-11-05 adds N1 to N3, masked FT and a better search, on trusted data. L1a, declared next: the first 50 captures, the ear gate, a blind check of search labels against S
and a placebo before the rest of the labels, then their centre against GOAT's at the same count.
Overnight (F55): masked FT reads tone better on GOAT and holds cab; by the score it is closer there by item, not shown by fold, and worse on BKS; the learning curve is undecided.
N4 (F56, one listener, the same 10 parts): FTm is not known by ear. It is above S on 4 of 10 parts (0.40 [0.11, 0.69]), level with FT on
closeness, and by the score S is closer on 8 of these 10 parts, the reverse of the two development sets (the pooled row on t reaches zero). S and FT repeat L0's split on the same clips:
the models lead on clean parts and off the ac20, S on crunch and on the ac20, and class, amp and S's setting still cannot be pulled apart.
The label check (F57, one listener, 11 parts of 12, amp and class crossed): J0's search labels through the true DI are heard closer than S on closeness (+1.45 [+0.91, +2.00] on the 0 to 3 scale) and the rank share reaches one half (8 of 11, 0.73 [0.45, 0.91]), so the declared row is not known and the closeness row is the user's evidence on whether to go on. With the listener's post hoc correction of item 8 the rank share reads 9 of 11 [0.64, 1.00] beside it, which does not move the declared reading. Neither of F56's splits shows for the labels, which does not say what drove those splits. It reads labels, not a model or a song.
Findings F1–F64.

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
      render: X-LANCE 2.14, htdemucs 3.55) exceeds every effect's clean J0, so it dominates J0's distance: J0 still
      picks the wet render for the large effects on X-LANCE stems in 22 of 24, with about a tenth of its clean
      margin (8–13%); C on X-LANCE stems picks the wet render for mix 0.40, the 3 s decay and delay time in 21 of 24 cases, and
      not the mix 0.15 effects (0–3 of 6), whose size equals X-LANCE's own slight tail trim (C −0.04). One DI, two
      presets, 3 backings, plugin-rendered guitar: descriptive. The robust effect part must be read through stems.
    - *The page's outcome (2026-11-03, F47):* J5 − J0 −0.224 [−0.351, −0.063]: undecided by the declared rule and
      not adopted; wholly below 0 with the anchors, −0.135 [−0.259, +0.031] on the plugin controls alone. On this
      chord DI the effects were barely heard (clean reverb and delay 0.40 barely, the rest the same). The tonal
      revision is not triggered. The user chose to stop here (2026-11-03) and take the effects route below; J0
      stays.
  - *The effects route (2026-11-03, after F47, at the user's go-ahead; ledger `phase_fx_reader`).* The product
    receives only the song (no DI), so a part that compares a render with the reference cannot set effects there;
    and F44–F47 show J0's weighting of effects against tone does not hold across pages, and J5's carry-over part
    did not fix it (undecided, leaning worse). So effects get their own step: a blind reader that measures reverb
    and delay in the separated guitar stem and sets those controls. (Where the judge then compares tone, drive and
    cab with effects matched on both sides is in evaluation, which has the DI; the song-only product has no J0.)
    What the code has today, the rules in `match/invert.py`, used when match runs (a song or stem without a DI is
    refused, `NO_DI_REFUSAL`, unless `--search-without-di`; on the song-only path effects follow song research):
    a delay time and a feedback (from the repeat ratio, × 100) from the fingerprint's echo detector
    (`analysis/features.time_effects`), below its confidence floor 0.15 the delay switched off, its mix left to
    the search; the reverb left as the template has it on any played material, because the RT60 estimate follows
    the notes' sustain (`research/study_rt60.py --switches`, on SW50R through two passages: on for 4 and 5 of 12
    targets with a reverb, and for 5 and 4 of 12 without).
    - **E0 (zero renders, exploratory, before any reader is built).** Do the product's own blind measures read the
      effects through X-LANCE? *Data:* the separator check's stems (`judge-v5/separator-check/stems/xlance_g`, 84:
      2 presets × 3 phase-5A backings × 2 guitar ratios × 7 renders: S; reverb mix 0.15 and 0.40 at decay 1.48,
      reverb 0.40 at decay 3.0; delay mix 0.15 and 0.40 at 500 ms, delay 0.40 at 300 ms); htdemucs's 84 beside in
      the same tables; the 14 renders without backing as the ceiling, and the S2 repeat renders as a second dry
      case. All mono (channel-averaged renders), 48 kHz, 10 s, no mastering. Settings: delay sync off, feedback
      0.30, ping-pong on, width 1, tape drive 0, band 132–2218 Hz; reverb pre-delay 60 ms, high cut 3,996 Hz, low
      cut 161 Hz; the decay is the plugin's 1–60 scale, not checked to equal an RT60. *Call:*
      `analysis.fingerprint.fingerprint(io.from_samples(stem, 48000), regime="separated_stem")` with the default
      20 s excerpt (so the whole 10 s stem; loudness-normalised, a gain only), `time_fx` read. Against the
      product: 10 s of a mono-summed render, where the product measures up to 20 s of a stereo song. The readout
      script and the hash of `analysis/features.py` are committed before the run.
      *Delay* (every stem's `delay_ms`, confidence, feedback estimate and `bpm_est` reported, whatever the floor):
      per kind (12 stems), four outcomes: (a) reported at confidence ≥ 0.15 within ±5% of the set time (a
      declared tolerance; the code's own is 1% in `fundamental()`; 285–315 and 475–525 ms do not overlap); (b)
      within ±5% at confidence 0.14, the comb cap; (c) at 2× or ½× the set time; (d) none or elsewhere. A 500 ms
      hit counts only where S of the same preset × backing × ratio does not report within ±5% of 500 ms (500 ms is
      a quarter note at 120 BPM; if it is a whole number of the part's beats, the decay gate, repeat ratio ≥ 0.80,
      can reject a real echo, so the 300 ms kind is the cleaner time test). False reports on S and the reverb stems
      (48). The confidence by mix 0.15 against 0.40 in the 12 matched pairs; the feedback estimate against the set
      0.30, by mix (it grows with the wet level by construction, so a rise is not skill).
      *Reverb:* `rt60_s` and its confidence by kind; in matched pairs, how often it rises from S to reverb 0.40
      and from decay 1.48 to 3.0. `reverb_from_rt60`'s decision applied counterfactually, as `study_rt60` does (the
      product never applies it to a stem: `RT60_REGIMES = ("probe",)`): truth on = the 36 reverb stems, off = the
      12 S stems and the 36 delay stems; its four outcomes (no tail; confidence < 0.3; RT60 below the 1 s floor;
      on with a decay) by kind.
      Every count also by preset × backing × ratio (a kind's 12 stems are 2 renders × 6 mixes, not 12 independent
      readings). Secondary, not as the product runs it: the same on 0–5 s and 5–10 s separately (the DI falls
      only in its second half; both detectors fit in 5 s). Counts reported, no bar (one DI, two presets, three
      backings, plugin guitar, no mastering: descriptive). What it informs: which measures are candidates for E1
      to test beside the learned reader, and which it must learn; one DI can show where a measure fails, not that
      it works.
    - *E0's outcome (2026-11-03, F48):* on this chord DI neither measure reads its effect, before or after
      separation: the echo detector reports nothing on any of the 36 delay stems or the 6 delay renders on the
      whole stem (the chords comb its band; at the known lag the echo leaves a trace, 2–3 times the dry level at
      mix 0.40), and the reverb rule fires on 3 of 36 X-LANCE reverb stems and 10 of 48 without. E1 learns both.
    - **E1a (2026-11-03, zero renders, declared after F48; ledger `phase_fx_reader_e1a`).** Stored data already
      holds what E1 needs for a first read: D_CC (`trusted-data/cc`) rendered every target with the rack reverb and
      the delay on or off (each in a fresh process with a priming render of its own setting, the carry-over rule;
      the kept render opens with the priming render's tail, the same setting), mixed with the song's other guitars
      and backing by the mix rule (about half mastered), and separated by X-LANCE; the uint8 half log-mels of the
      stem, the mix and the clean target are stored. The other guitars, DT doubles included, carry no rack reverb or
      delay (all 6,911 off), but about 4,500 of them have their amp's spring on. *Examples:* the 2,640 D_CC examples
      with all three stored inputs, 8 songs in 7 bands (BKS has two songs, which share player, guitar and studio);
      left out: 774 near-silent render refusals, 1 unbuilt, and NS's 393 built examples (held out); no V-real band.
      Reverb on 1,391, delay on 1,272 (sync off throughout); p10–p90 on-values: reverb mix 0.085–0.75, decay
      1.07–5.36 (the plugin's value, drawn log-uniform over 1–6; not checked to be seconds), delay mix 0.065–0.77,
      time 97–684 ms, feedback 0.08–0.75; 1,347 mastered; 263 from D_CC's FS set (harmless: E1a trains its own
      models). *The draw confound:* on/off and the knobs follow the preset draw (reverb on in 73% of factory-centred
      draws, 15% of start draws, 50% of wide; delay 62%, 16%, 52%; both on in 596 of 1,244 factory draws), so a
      reader can score by recognising the amp and preset: a no-audio lookup of the on-rate by amp × draw × class
      reaches AUC 0.75 (reverb) and 0.67 (delay) leave-one-song-out (the results review's count). Only the 770
      *wide* draws (reverb on 387, delay on 402) have every switch a fair coin and every knob uniform and
      independent of the other controls; they carry the decision. *Reader* (`learn/fx_reader.py` `e1a-*`): a small
      CNN (132k parameters) on the two halves' log-mels (4 conv blocks 16–96, mean and max pooled) plus the
      mel-envelope autocorrelation at lags 10–1,500 ms per half (where an echo shows), heads for reverb on, delay on
      (logits) and reverb mix, log2 decay, delay mix, log2 time and feedback (on items only); Adam 1e-3, batch 64,
      40 epochs, the epoch kept by loss on 15% of the training songs' sections (in-song, stated), seed 20261107,
      MPS (inputs precomputed). Training cost, measured on random tensors: about 3 minutes a fold-arm, 24
      fold-arms about 1–1.2 h with the GPU idle; the product's measures on the clean targets about 33 minutes on
      CPU. *Read:* leave one song out (each fold's test song unseen in DI and backing), three inputs: the X-LANCE
      stem (primary), the mix, the clean target (the ceiling; the drop from target to mix to stem is the masking's
      and the separator's share). *Readouts,* each on all items and on the wide draws (thirds' cut-offs within
      each), with 90% intervals from 2,000 resamples of bands (7 clusters, seed 20261108; few, so they may
      under-cover, stated): on/off AUC for each effect, overall and for the top and bottom third of on-mixes (each
      against all offs), by song and their song-weighted mean; beside each, a draw-only comparator (the training
      songs' on-rate in the same amp × draw × class cell, no audio) and the reader-minus-draw difference with its
      interval; reverb AUC with the offs split by the selected amp's spring on or off (the spring, other guitars'
      springs, room mics on in 672 targets and the doubler in 767 are reverb-like sound the label does not count);
      per knob on true-on items, mean absolute error against a no-skill prior (the training songs' median) and the
      difference with its interval; delay time within ±10%. Comparators beside: the product's own measures
      (`time_effects`, `delay_settings`' floor, the counterfactual `reverb_from_rt60`) on the clean target audio —
      their ceiling, not like for like with the stem reader. External, descriptive: the fold that holds out
      Quicksand (E0's song) read on E0's 84 X-LANCE stems (median on-probabilities, decay and time by kind), with
      the two stem sets' loudness. Each run file carries the data build's hash, checked at scoring. No bar: effect
      sizes, undecided not failed. *What follows:* if the stem reader's AUC on the wide draws' strong third has its
      interval above 0.5 for either effect, and on those wide ons its mix and its decay (reverb) or time (delay) MAE
      difference against the median prior has its interval below 0, E1b is declared to build the product's
      reader, then real songs by ear. If the mix reads but the stem does not, the loss is the separator's share and
      E1b aims there (fine-tuning only, no new separator). If only the target reads, the loss is the mix's masking
      (as `docs/tone-info-probe.md` found for linear probes: AUC 0.75 target, 0.60 mix, 0.58 stem for reverb) and
      E1b aims at that. If the target does not read on the wide draws, the reader or its features are the
      bottleneck: a research target, not a verdict on the route. The all-items figures stay descriptive beside the
      draw comparator. *Caveats:* mono mixes (no stereo pipeline exists), one separator, the songs' own backings (DI
      and backing held out together, never apart), 8 songs in 7 bands, outside the wide draws the reader can score
      by recognising the preset, a fixed seed.
    - *E1a's outcome (2026-11-03, F49):* on the wide draws the stem reader hears that an effect is on, modestly
      (strong thirds 0.614 [0.591, 0.648] reverb, 0.614 [0.584, 0.640] delay), the target much better (0.767,
      0.801). By the rule's letter delay passes, but its knob half used a prior blind to the draw: against the
      training songs' wide-draw median no knob's error is better on the stem and time is not read (Spearman 0.04),
      and even the target reads neither decay nor time, though a training-free picker (the argmax of the envelope
      autocorrelation's summed prominence, lags 6–80) finds the set time within ±10% on 43.5% of the target's wide
      delay-ons (the wide median 7.2%) and 13.7% of the stem's. So E1b is not declared; the reader is the
      bottleneck for time (declared branch), and E1c tests a learned lag head on the stem.
    - **E1c (2026-11-03, zero renders, declared after F49, amended by its review before any run; ledger
      `phase_fx_reader_e1c`).** Does a learned lag head read delay time on the stem, beyond a blind picker and a
      prior that knows the draw? Same data build (meta sha256 7ec72295…), examples, folds, seed, optimiser, epochs,
      batches and inner split as E1a. *The lag head,* on the stored envelope autocorrelation (2 halves × 150 lags of
      10 ms): each half's curve minus its local mean (lags ±3–6; at lags 1–6 and 145–150 the edge is padded by
      repetition, where the audit dropped missing neighbours), then a 1-D convolution over lags applied to each half
      with shared weights (1→16→16 channels, kernel 5, ReLU, then 16→1), the halves' logits summed, and lags outside
      6–80 (the draw's 60–800 ms, a range the product can be given) masked: 75 logits. It trains on delay-on items
      by cross-entropy against a Gaussian of one lag around the set lag, cut to lags 6–80 and renormalised (under 100 ms ±10% is less than a lag, so
      only the exact lag counts there). It reads only the autocorrelation, so it is a separate model trained on
      E1a's batches: its weights are drawn on a forked random stream and its epoch is kept by its own inner
      cross-entropy, so the trunk, its on/off and regression heads and their epoch choice repeat E1a's (up to MPS
      nondeterminism). *Estimators, fixed:* within ±10% from the argmax lag; log2 MAE from the posterior median
      lag (in log-lag); Spearman from the posterior median. The convolution slides over lags, so it learns the
      peak's shape, not where the draw puts it. Arms: the stem (primary), the mix, the clean target (the head's
      check: the blind picker already reads there); 24 fold-arms, about an hour (E1a measured 20 minutes an arm).
      *Comparators:* the training-free picker of F49's audit (argmax of the summed prominence, lags 6–80, no
      training; head minus picker with its interval); no audio, from the training songs: the wide-draw median and
      the amp × draw × class cell median (draw-aware), the all-draw median beside; E1a's regression time head.
      *Readouts* on the wide delay-ons (402), overall and by the strong and weak third of delay mix, with 90%
      intervals from 2,000 band resamples (7 clusters, seed 20261108): within ±10%, log2 MAE and Spearman for the
      head, the picker and the priors, and the differences; also on all delay-ons; every regression knob against
      both draw-aware priors (E1a's audit made formal); on/off AUC and the draw comparator, descriptive.
      *Rule:* time *reads* on an arm if, on the wide delay-ons, the head's within-±10% difference against the
      wide-draw median has its interval above 0 and its log2 MAE difference has its interval below 0; the head
      *improves on the picker* if its within-±10% difference against the picker has its interval above 0.
      *What follows:* if the head does not read on the target, or its within-±10% difference against the picker
      there has its interval below 0, the head is broken and is fixed before its stem result counts. Time reads on the stem → E1b is declared for delay
      (on/off and time) with renders, reviewed first. It does not: if the mix reads, time is lost to the separator
      (fine-tuning only); if neither reads, to the backing's masking, which E1b's renders then aim at (a backing
      split); either way a research target, not a verdict. Reverb decay is not in E1c: no cue for it is shown in
      the input yet. *Caveats:* E1a's (two songs hold 66% of the wide draws; 7 band clusters may under-cover; mono
      mixes; one separator; one seed); the head and the picker were chosen after seeing E1a's audit on these same
      examples, which leave-one-song-out does not undo for the picker.
      *Review (2026-11-03, independent, before any run):* four required changes, all made: one estimator per
      readout and the lag range declared (an argmax over 150 lags loses on MAE by its far misses); the picker as
      the comparator to beat, with branches restated around the stem (the target branch is already answered by
      the picker); the convolution described as built (1→16→16→1 per half); the trunk kept as E1a's (a forked
      random stream and the lag head's own epoch).
    - *E1c's outcome (2026-11-03, F50):* time does not read on any arm by the declared rule. On the wide
      delay-ons the stem's head lands within ±10% on 10.7% (the wide median 7.2%; the picker 13.7%), with its error
      worse than the prior's (+0.251 [+0.195, +0.348]) and Spearman −0.02; the mix alike. On the target the head's
      hits equal the picker's (46.0% against 43.5%) but its posterior-median error is not better than the prior's
      (+0.034 [−0.030, +0.099]; its argmax passes). The declared head fix was not done; post hoc, the stem verdict
      rests on the picker (which reads on the target and fails on the stem), the head's argmax and its flat stem
      loss: for these readers on the stored features the time is lost when the backing is added, separation
      recovering a few hits. E1b is not declared; the declared masking branch is deferred until the survey of
      proven blind estimators is in.
    - **E1d (2026-11-03, zero renders, no training, no download; declared after the cloud researcher's survey,
      `docs/research/blind-reverb-delay-2026-11.md`, which found no proven blind estimator; ledger
      `phase_fx_reader_e1d`).** Does an audio-domain, finer-resolution measure read delay time where the stored
      log-mels did not? `learn/fx_reader.py e1d`: the real cepstrum averaged over Hann-windowed 2^17-sample frames
      (2.7 s, 0.5 s hop), lags under 40 ms dropped (the chord's pitch), the highest peak in 60–800 ms (the draw's
      range; 40–1,500 ms secondary) is the time, its height the on/off score; a second arm subtracts the mean
      cepstrum of the training songs' wide delay-offs (leave one song out). *Step 1,* the stored clean targets of the
      770 wide draws (CPU minutes): on the 402 delay-ons, within ±10% (±3% secondary), log2 MAE and Spearman, each
      paired against F49's picker on the same items and against the training songs' wide-draw median, overall and
      by thirds of delay mix; double and half lags apart; peak-height AUC on all wide draws and on the strong third
      against all wide offs; 90% intervals from 2,000 band resamples (seed 20261108). The arm stops if its hits'
      difference against the picker has its interval wholly below 0. *Step 2,* E0's 84 stored X-LANCE stems (one
      chord DI, 2 renders × 6 mixes per kind): on each delay set (300 ms at mix 0.40, 500 ms at 0.40, 500 ms at
      0.15; 12 stems each) the hits within ±10% of the set time, against the 12 S stems' picks at that lag and
      chance (about 8% for a log-uniform guess over 60–800 ms). The subtraction arm takes E0's 48 S and reverb
      stems as its offs, which hold the S stems themselves and share the DI, presets and backings (a reference the
      product never has), so on step 2 it is descriptive only. *Positive control:* the same plain pick on E0's
      stored renders without backing (`judge-v5/renders/{clean,crunch}-{S,delay-time,delay-large,delay-small}.npy`),
      so a step-2 failure can be laid on separation and backing rather than on this chord DI and the Morgan delay;
      if the control misses the set time on both mix-0.40 renders of both classes, step 2 says nothing about
      separation. *Clearly* (declared before reading; the plain arm, counted only if it did not stop in step 1): at
      least 4 of 12 hits on either mix-0.40 set (two chances; about 1.1% a set by chance alone, under a binomial
      the 12 stems, sharing one DI, do not strictly meet) with the S stems hitting that lag at most once. *What
      follows:* step 1 stopping, or step 2 not clearly → F50's verdict extends to the cepstrum on these stems, and
      the deferred masking renders (E1b, storing stem and mix audio) are proposed next. Step 2 clearly → E1e is
      declared: the 770 wide draws' mixes rebuilt on CPU (`trusted_data.self_built_mix`, zero renders) and
      re-separated (X-LANCE about 55 minutes on MPS), passing if on the stem the cepstrum's hits beat the picker's
      on the same items (paired interval above 0) with a log2 MAE below the prior's; then the feedback readout. *Caveats:* the method is demonstrated (one vocal echo), not
      proven; step 2 is one chord DI, two presets, three backings, with the mix law of the Morgan delay unknown.
      *Review (2026-11-03, independent, before any run):* three required changes, all made: the subtraction arm
      descriptive on step 2 (its offs hold the S stems); how arms and sets combine, and the chance level per set; a
      positive control on the renders without backing. Also adopted: an interval on the all-draw height AUC, and
      E1e's pass rule paired against the picker.
    - *E1d's outcome (2026-11-03, F51):* on the clean targets the cepstrum reads time (57.2% within ±10% with the
      delay-off subtraction, +0.137 [+0.086, +0.166] over the picker, error below the prior and the picker), so it
      does not stop; on E0's stems not clearly (0 of 12 on every set), but its positive control misses 3 of 4
      mix-0.40 renders without backing (the chord DI's own 72.8 ms peak), so step 2 mostly tested the DI (where the
      control reads, crunch at 300 ms, the stems hit 0 of 6: weak evidence in F50's direction).
      Amended (post hoc): E1e before the masking renders.
    - **E1e (2026-11-03, zero renders, an amendment after F51; ledger `phase_fx_reader_e1e`).** Does the cepstrum
      read delay time on the D_CC stems where it reads on their targets? `learn/fx_reader.py e1e-build`
      (msst-venv): the 770 wide draws' mixes rebuilt by D_CC's own build recipe (the stored target and other
      guitars, the section's stems, `trusted_data.self_built_mix` with its seeded mastering) and re-separated by
      X-LANCE on MPS, mix and stem saved as audio (about 3 GB). Each rebuild is checked: the mix's uint8 half
      log-mels must equal the stored ones (an item that does not is dropped and counted); the stem's feature
      difference is logged (both were exact on a two-item smoke run). The build only writes audio and runs before
      this declaration's review; scoring waits for it. `e1e-score`: E1d's step-1 readouts on the stem and the mix
      (both arms; the subtraction arm's offs are the training songs' wide delay-offs of the same input, leave one
      song out), paired against F49's picker on that input (stem 13.7%, mix 6.7%) and the wide-draw median.
      *Primary:* the subtraction arm (the better on the targets, chosen after F51), the plain arm beside. *Rule:*
      time reads on the stem if the primary arm's within-±10% difference against the picker has its interval
      above 0 and its log2 MAE difference against the wide-draw median has its interval below 0. *What follows:*
      it reads → the feedback readout (the doubled real cepstrum at twice the time) is tested next on the same
      audio, and E1b is declared for the product's case (renders: stereo and mastered mixes, more DIs, synced
      delays, the confounders; stem and mix audio stored). It does not, but the mix does by the same rule → the
      separator's share (fine-tuning only). Neither → the backing's masking, and E1b's masking renders (a backing
      split, audio stored) are proposed. If the primary arm passes and the plain arm's hit interval reaches 0, it is
      reported as "reads, arm-sensitive". Peak-height AUC on the stem, descriptive, beside E1a's 0.614 (the same
      mask). *Caveats:* F51's; the primary arm chosen after seeing the targets; one separator; mono mixes; the
      picker reads the stored features of the original separation, the cepstrum the re-separated stem (their
      feature difference is logged per item); the scorer refuses to run if any wide item lacks its row or audio.
      *Review (2026-11-03, independent, before scoring):* three required changes, all made: failed rebuilds dropped
      in the scorer, not only counted; "step 2 tested the DI" softened (the crunch 300 ms cell); F51's weak third
      and secondary range errors added. Also adopted: the arm-sensitive reading, the picker-pairing caveat.
    - *E1e's outcome (2026-11-03, F52):* time does not read on the stem (the primary arm's hits +0.085 [+0.029,
      +0.157] over the picker, its error +0.309 [+0.210, +0.383] over the prior) nor on the mix: masking (declared
      branch). The masking renders are proposed, not run; the user chooses between them and the main line.
    - **E1b (outline; declared on its own after E1a, reviewed before any render):** what E1a leaves open, with
      renders: stereo and mastered mixes as the product's songs are (new work: the self-built mixes are mono),
      more verified DIs (E0's Quicksand DI out of training), a backing split, the confounders varied (the amps'
      springs, drive and compressor sustain, cab and room; tremolo, chorus and doubler; delays synced to the part's
      beat; playing with and without falls). Each time-effect render needs its own fresh process with a priming
      render (about 2,100 kept renders an hour measured), and separation (X-LANCE about 4.3 s a clip on MPS) cannot
      run beside renders. Comparators: the prior, the current measures, E1a's reader. Effect sizes with intervals
      clustered by DI, then a few real songs by ear; what result puts the reader into the product is stated there.

- **The user's decisions (2026-11-04, "I'd go with your recommendations"):** the main line, not the masking renders
  (they are not run); neither the S fallback nor the near-chance rule (steps 26, 27 and 37 close as User decision:
  F23, the 2026-10-27 ruling; the readout stays plain; pedals held at S, which helped a weak model, is measured again
  on the next model, a check and not a rule); no scale for now (F25; it comes back only if results keep rising as real
  recordings are added).
- **The user's correction, the same day:** "level with S" is the score's reading, not the sound's. The score is
  imperfect (F44–F47), and listening has put generated presets above S (F53). From here a real-song verdict
  says "by the score", and no real-song verdict on a model stands on the score alone: a blind ear read sits beside
  J0, declared before the read. The ear stays a development tool; the product still runs with no human.
- **L0, the ear on held-out real songs (ledger `phase_ear_vreal`; `learn/ear_vreal.py`; 80 renders, 40 kept).** The main
  line's steps are L0, this read; L1, the recordings; L2, the fresh real-song test.
  - **Question.** On a song's own performance, where does the ear put S, FT, D_fix and W, and does it agree with the
    score on the same audio? No current model has been heard that way: F53's model pages used a stand-in guitar. It
    comes first because it is the cheapest thing that can change how the main line is read, and because the main
    line's labels come from J0.
  - **Items.** V-real-11's 10 parts in 7 bands, one direction each, chosen from the record's activity and S's stored
    distances alone, before any model's answer or score is opened (`choose`): the held half is the more active half
    (share of 100-ms frames within 25 dB of the crop's loudest; 8 of the 10 parts tie at 1.0, so there the tie rule
    gives A), the amp the one whose S is closest on the search half (record match's rule); of Wickerman ElecGtr2 and 3,
    which share one input, the one with the more active held half. Choosing the amp by S's closeness leans toward S.
    Two items are repeated (seeded), at least 4 items after the first hearing, with every candidate on another letter;
    letters are balanced; only first hearings make the rows.
  - **Candidates.** S, FT, D_fix and W, each from its stored V-real answer on that direction (X-LANCE stem input, the
    product's path). W is there because the score puts it clearly below S on V-real (+0.228) while the stand-in pages
    put it above S on 5 of 8 rankings. Each is re-rendered through the part's measure DI, the input every V-real read
    used: its own performance, EQ'd to the average guitar at −22.9 LUFS. That is not record match's raw DI, it moves
    these parts' level by up to about 16 dB, and F20 found it caps even the truth, so closeness ratings and any
    comparison with record match are limited by it. It is kept because the audio must be what the score read: in
    `vreal_render`'s recipe (a fresh process, one priming render) each hash must equal the stored render's, and a
    mismatch stops the shard and is diagnosed before any page exists. The first run is one part whose W has effects on,
    since the stored rechecks cover effects-off renders only. Disk guard and the 3-process limit as ever.
  - **The page.** The held half (about 4.5 s, the judge's window), looped; mono; every clip -23 LUFS on its own and the
    item's largest peak cut applied to all; renders sample-aligned to the amp track by the judge's lag, instant switch,
    no song or band named, headphones. The listener ranks the four (forced) and rates each one against the record (very
    close, close, somewhat, not close; ties allowed, so "cannot tell them apart" can be said). Guitar only, per the
    listening rule.
  - **Reads (descriptive, band-weighted, 90% band-clustered bootstrap).** Each candidate's mean rank, mean closeness,
    first and last places. FT, D_fix and W against S on rank and on closeness, with parts and bands above S, parts
    rated level, and clean and crunch beside (means and counts; clean is 2 bands, so no interval). The score on these
    same 10 directions, band-mean ln(d_S / d_model) with its interval (plus means the model is closer, the opposite sign
    to the V-real figures quoted here): V-real's rows average every direction, and this page holds S's closest amp. The ear against the score: per item the Spearman of ear rank and held-half J0 over the
    four candidates, and how often the two put a model on the same side of S. Repeats: rank agreement and the same
    top. Any note the listener leaves.
  - **Map, per model, declared now.** No bar decides a route; effect sizes and intervals are reported either way.
    - Rank interval clear of zero above S: "heard above S on these songs, one listener". The score's row on these
      directions then says whether the score misses it. For FT and D_fix V-real's rows do not separate them from S
      (+0.022, +0.036), and for W they put it clearly below (+0.228).
    - Clear of zero below S: "heard below S on these songs, one listener". For W the ear and the score then agree; for
      FT and D_fix the ear is harsher than the score.
    - Interval reaching zero: not known by ear, not level; underpowered is not failed. The closeness row's ties say
      how often the ear could not part them at all: equal ratings on most parts would be the ear's own "level".
    - What the design can bear, simulated now (random answers, these 10 parts in 7 bands, this bootstrap): one model
      clears zero on one given side about 8% of the time, and at least one of the three clears either way on about
      35% of pages; a model truly ahead on 75% of items clears on about 48%. So a clear row is a lead for L2, not a
      verdict, and undecided is the likely outcome even if a model is really better.
    - Whatever the rows: the main line goes on, and L2 carries a blind ear read beside J0, sized from what this page
      shows.
    - If the ear-score Spearman's interval reaches zero, J0's labels are treated as unverified on real material, and
      L1 starts with a small blind check that search labels beat S by ear on real amps before any large spend.
  - **V-real.** This is at least V-real's fourth read in this plan (P4, F41, F42) and its first by ear. It chooses no
    model: any choice made from it is labelled selection-contaminated, and the fresh test is what decides. V-real's
    answers stay as stored.
  - **Caveats.** One listener; 10 items; a short window. W has reverb, delay or tremolo on in 8 of the 10 directions,
    D_fix in 1, S and FT in none: no letter says so, but the ear can recognise W across items, W's rows mix tone with
    effects, and F44 found reverb heard above its score. colour-me-red ElecGtr03's held half is only 57% active (record
    match wanted 0.8). The listener has heard these records before (T0's ear), and S on two of them: Signs ElecGtr3 and
    get-out-of-bed ElecGtr2 were on record match's page, the second at this same amp and half, through the raw DI.
  - *Reads with no result (2026-11-05):* before they had the limits, a read-only review session's loader opened two V-real
    parts' stored clips (It Was My Fault ElecGtr1 and 3), computed only one DI level and deleted the files; and one of its
    reviewers opened `ear-vreal/plan.json`, 800 characters of one unit's stored record, and the opening 2,500 characters of two
    V-real reports (per-part FT − S among them), dropping the one value it took. Two others saw NS loss fields in run logs. Nothing
    new was computed on V-real or NS, and nothing here uses any of it.
  - *L0's outcome (2026-11-04, F54):* W is heard below S on rank and closeness, one listener, and the score agrees. FT and D_fix are
    not known by ear (rank −0.07 [−0.86, +0.71], −0.43 [−1.00, +0.21]). The ear-score Spearman is +0.50 [+0.31, +0.67],
    so the declared check is not triggered; the audit finds W carries it (among the other three, agreement is not
    shown: +0.04 [−0.29, +0.39]).
    The main line goes on, and L1's declaration takes up the check on its own evidence.
- **L1a, the first capture batch (ledger `phase_l1a`; `learn/capture_labels.py`, `learn/capture_units.py`,
  `learn/capture_ear.py`, `learn/nam_load.py`; about 2,900
  renders before the listener hears a label, about 8,800 to 9,300 if everything runs, about 2,000 of them the centre
  read; about 1.5 to 1.7 h in all, about 30 min of it before the page).** Before anyone asks TONE3000 for more, the
  first 50 captures settle what more would rest on: whether they sound like amps, whether J0's search labels on them
  sound closer than S, and whether their centre moves against GOAT's at the same count.
  - **Why the label check is here.** F54: the declared ear-score check was not triggered, but W carried the agreement,
    and among S, FT and D_fix agreement is not shown. L1's labels ask J0 to search, not to rank near answers, and record
    match's search was heard above S on 5 of 5, through the true DI, on real records. Neither settles it for captures.
    L0's map put such a check before any large spend, and the cheapest test comes first, so it comes first here.
  - **Order (amended below: `phase_l1a_night`).** Units; the ear gate; the lag pass on every passed unit; the 12 ear items, drawn by seed from unit
    metadata before any search has run; those units searched first, then units in a seeded order up to a third of them;
    the stage check; the label page. Only then the remaining labels and the centre read, and neither runs if the primary share is clear below.
  - **Data (zero plugin renders; `units`).** All 50 captures (31 packs, 20 creators), by the one loader (`nam_load`,
    moved into `learn/`, its A1 translator tested). The render is `m(x, pad_start=True)` at 48 kHz on CPU, stored with
    its sha256 and the `.nam` file's, which must equal the manifest's. None is added or dropped by name.
    - *DIs.* GOAT's 139 section DIs, already screened and heard (`goat/sections/item_*.di.wav`). None is V-real's, the
      NS songs', the panel's, or Jen Hartswick & Nick Cassarino's. Captures run in a seeded order (seed 20261105). Each
      capture's amp order and first player are seeded; its candidates take the players in turn, items cycling within a
      player. No DI plays more than 3 units in the batch, and a capture never plays one DI twice, so player4's 4 items
      give at most 12 units. The capture plays the DI levelled to −22.9 LUFS, the plugin the measure DI, as for GOAT and
      BKS.
    - *Level rule, one for all 50.* Gain in dB = 9 − the stored `input_level_dbu`, 0 dB where none is stored (11 files),
      and the input's peak is held at 1.0, the top of the range the capture was trained on. Each unit stores its gain
      and whether it was held. 9 is a free choice the data do not determine: on 3 trial DIs the references 3 to 12
      cannot be told apart on the makers' labels (12 − 3 agreement −0.068 [−0.154, +0.017]; by creator [−0.153,
      +0.020]), and 7 captures reach the hold at 9 (5 at 6, 13 at 12). The hold keeps the 5 files with negative stored
      levels inside their range rather than excluding them or extrapolating, at the price that one sample sets their
      level. Reported apart: held units (4 of the 5 negative files are one creator's) and the 11 uncalibrated files,
      which play 2.5 dB hotter than the median calibrated file (stored 11.5) and gave 6 of the trial's 11 high-gain
      units. The makers' labels are a guide.
    - *Units.* Each capture on each of the 3 plugin amps, one DI per amp, 150 units before the class. Classed against
      its DI by the pool's classifier (`classify` on `gainmeasure`); high gain is out. Each capture walks its
      candidates, up to 9 DIs, and each amp takes the next DI that gives crunch if there is one, otherwise the next that
      gives clean. The walk selects on the classifier's reading. Class is partly the DI (trial crunch counts of 50:
      player1's DI 18, player2's 4, player4's 19 plus 9 high gain), and a marginal capture gets up to 9 chances to read
      crunch. Before the walk about a quarter of the trial's units read crunch (41 of 150); modelled from 3 DIs, one per
      player, the walk with its cap gives about 75 to 90 clean and 60 to 70 crunch, and a smallest cell after the ear
      and the lag rule of about 14 to 16 (lowest modelled 9), so the minimum can fire but rarely will.
    - *Folds, for later.* 4, by creator: a pack here is one amp, so a creator's rig and mics stay together.
    - *Stated before the ear:* units by amp and class, by player and class, the makers' label against the class, the
      most-used DIs, held units and uncalibrated units. Minimum 10 per amp and class (the centre's error is about half
      its shift there, resampling GOAT's labels), before the ear and again after the ear and the lag rule, in code;
      under it the batch stops and this block is revised.
  - **Trusted data, before any plugin render.** One card per capture on its most driven unit (highest non-linear share),
    on `goat_ear_page`'s instant A/B against its DI, blind to the measures and to any flag: "a believable amp tone",
    "odd amp sound", "the DI itself sounds processed or noisy", "not sure". Only the first passes, and "odd" drops the
    capture. Then every firmly driven unit (`classify`'s "driven") of a passed capture is heard on 5C's heavy page:
    "keep", "too heavy or fizzy", "not sure"; only "keep" stays, and it drops that unit alone. One clip cannot stand for
    a capture's heaviest unit (25 of 50 gave 2 or more classes across 3 DIs), and GOAT's heavy page removed 22 of 34
    units the first ear had passed. Both gates in code before any plugin render, with tests. The share outside BKS's cab
    range is stated on the page's own clips.
  - **Labels, GOAT's recipe, unchanged.** Each unit's three S renders give the judge lag (6 renders); the one-window lag
    rule refuses a unit more than 72 samples from the median. A whole-render lag above 240 samples is flagged and
    reported apart; NAM's own alignment may hide mic distance, so the flag proves nothing about a mic. Then arm A's main
    stage (`K.space`, 52 evaluations, seed 20261013, from the class's S, 53 renders) on the unit's amp and search half.
    `inputGain` stays searched. The capture's own level is fixed above: the search never sees it. About 113 to 121
    units, about 6,700 to 7,200 renders.
  - **Stops (the stage check, GOAT's, at a third of the units in the seeded order).** The search does not decidedly beat
    S where it did not search (held-half log ratio, clustered by creator, 90% interval's upper end at or above 0), or
    more than half of the labels have `inputGain` at a bound. Beside them, zero renders: label `inputGain` against the
    unit's capture gain, by creator (the bound stop cannot see the level rule setting labels inside the range), and S's
    held-half distance and the search gain on captures against GOAT's and BKS's.
  - **The ear check of the labels (blind; `learn/capture_ear.py`).**
    - *Items.* 12 units, 2 per amp and class, one held A and one held B in each cell, held half at least 0.8 active; no
      two from one pack and at most 2 from one creator; drawn by seed from unit metadata alone, before any search has
      run. The picker, placebos included, takes no search record, with a test. Amp and class are crossed; S's setting
      cannot be told from the amp-by-class cell. 2 repeats, at least 4 items after the first hearing. Letters balanced
      over the 12 first hearings, each candidate on each letter 4 times; on a repeat every candidate moves letter.
    - *Candidates.* S; the label; the placebo, the label of another capture of the same amp and class from another
      creator. Each part's placebo unit is drawn with the items, by seed, from unit metadata before any search, with a
      seeded fallback list, and searched with them. A placebo unit is not an item and serves one part. A fallback is
      taken only when a unit gives no label. A cell that cannot supply its 2 items and 2 placebos under these limits
      stops the batch, as the minimum does. The 24 units sit inside the third, so this adds no renders. The placebo
      tells "J0 fit this unit" from "S is off", which F54's two sw50r parts could not.
    - *Page.* As L0's: the held half looped, mono, −23 LUFS each, sample-aligned by the judge's lag, instant switch. The
      capture's render is the Record. Each candidate is rendered fresh in its own process through the unit's measure DI:
      72 renders. S's fresh render must equal the lag pass's hash. The label's is checked by judge (|ln ratio| against
      the in-process value within 1e-3; F34 found 36 of 120 bit-identical, largest gap 6.1e-5). The scored gaps use the
      fresh renders. Rank forced, a closeness rating each (ties allowed), sure or unsure, a note.
    - *Reads (descriptive, 90% creator-clustered bootstrap).* Primary, read pairwise from the forced rank (chance one
      half): the share of parts with the label ranked above S, then the closeness gap, with the score's gap beside.
      Beside, the same for the label against the placebo and the placebo against S. By class and by amp (means and
      counts, no intervals), a leave-one-cell-out row, and a row with unsure parts out. The ear against the score: the
      Spearman over the 12 parts of the closeness gap against ln(d_S / d_label), plus meaning the score also puts the
      label closer, with its interval. Repeats.
    - *Map, declared now.* The primary share's interval clear above one half: "heard closer than S on these captures of
      real amps, one listener", J0's search stands by ear this far. That does not show the fit is unit-specific: S may
      simply be far off (F54). Label against placebo clear above: heard closer than another capture's label, so the fit
      is specific to this unit. Clear below: another capture's label is heard closer, and J0's fit is not what the ear
      hears. Reaching one half: not known; with placebo against S clear above, S being off is the likelier reading. The
      primary share reaching one half: not known by ear; underpowered is not failed; the closeness row and its ties are
      the user's evidence on whether to go on. The primary share clear below: the labels are not what the ear wants, the
      remaining labels and the centre read do not run, and the judge's use for labels is reviewed before any next batch.
    - *What the design can bear, simulated now* (12 parts, 8 to 12 creators, this bootstrap): a true 75% clears one half on about 40 to 57% of pages, a true 85% on about 74 to 87%, a true 50% on about 2 to 7.5% each way. 10 of 12
      always clears, 9 on up to about 75% of layouts and about none at 12 creators, 8 almost never. A shared effect of S's setting lowers this. Label
      over S or label over placebo clears by chance on about 9% of pages. A true 65% clears on about a quarter, so the
      placebo row is often undecided even if the fit is real. So undecided is a likely outcome even if the labels are
      better, and a clear row is a lead, not a verdict.
  - **The centre read, by the score.** RcT, Rc's rule on the trusted capture labels; RcG_n, Rc's rule on GOAT labels
    drawn to the same count per amp and class, 3 seeded draws. Each on BKS's 40 units and the panel's 44, on all 3 amps,
    as before (504 renders a centre, about 2,000). Rows: RcT − RcG_n (mean of the draws, and each) and RcT − S, with RcG
    − S (stored) beside; BKS by DI, the panel by capped band weights. It says whether this batch's labels move the
    centre, by the score only: the gap also carries the search recipe (these labels are search v2's, GOAT's v1's, and v2's labels sit nearer S: drive 0.306 to 0.266, tone 0.284 to 0.192, cab 0.306 to 0.124, by N2), the level rule, the DI mix, the crunch preference and at most 19 creators.
    Past centre-against-centre half-widths were about 0.08 on BKS and 0.06 on the panel, so a smaller gap is undecided,
    the likely outcome. The intervals treat a centre as fixed, and the trusted cells now hold 20 to 26 labels (17 to 22 after the scope page, F60), so a zero-render row sits beside: RcT's setting distance from RcG, against what two draws from GOAT alone would show (a centre on RcT's count and one on GOAT's count, each drawn with replacement, 200 draws: *amended 2026-11-05 before any run, since a subset of RcG's own labels sits too near RcG and read a true null as moved in 54 to 98% of draws*), with a creator bootstrap of RcT as a spread, biased upward as any bootstrap of a distance, and the count of switches and mics that differ, which the rms leaves out. No row reads as moved unless its interval clears zero and RcT −
    RcG_n has the same sign on all 3 draws; the draws overlap 57 to 78% pairwise (35 to 77% a cell as drawn, F60), so that sign adds little. A missing render stops the report. This is a panel read: counted in `phase_5d_panel_reads`, and it picks no
    recipe. V-real stays unread.
  - **Reading.** No bar decides it, except that the primary share clear below holds the next batch until the judge's use for labels is
    reviewed. Otherwise the reads go to the user beside the yield and the cost of the next batch, which is the user's
    yes on the route and a fresh key. The working size stays 250 captures in all, about 100 labels per amp and class;
    this batch's yield replaces GOAT's 81% in that sum. Training comes after that, on FT's recipe, in its own
    declaration. L2 follows.
  - **N9, training on the captures, first step (declared 2026-11-06; ledger `phase_n9`; [design](capture-training-plan.md)).** On the user's go, on the 121 trusted labels in hand: FTm's recipe with and without the capture rows, on creator folds, with DI drops in every arm, read on held capture units. The second batch's labels stay unread until its gates pass. The draft below stays the plan for training on both batches.
    - *N9b (declared 2026-11-06, ledger `phase_n9b`, the same design):* does a ridge gain from capture rows, on top of BKS's and GOAT's? Zero renders, zero training, read beside N9's nets. *Outcome (F63):* mixed, drive −0.056 [−0.093, −0.019], tone +0.038 [+0.001, +0.076], neither firm; about 40% of the drive cost is the capture rows' offset in the pooled cell mean.
    - *Outcome (2026-11-06, F62):* undecided: C-cap − C-ctl +0.018, −0.014 and +0.024, each reaching zero, excluding a gain above about +0.08 and not excluding +0.05. No knob gain shown; an undeclared lead only on the search's own mic labels. The second batch is the test with more rows.
  - **Training on the captures, a draft (2026-11-05; not declared, nothing runs).** It waits on the user's yes (F57's closeness row is the evidence), on the second batch's ear page, heavy page and stage check, and on a reviewed declaration in the ledger. FTc: FTm's recipe (W's best state, searched heads only, lr 1e-4, cap 300, patience 15, 4 folds × 2 seeds, the 8 inner runs then the 8 FTc_k, two at a time on MPS). N1's runs took 8 to 10 min each by `logs/ftm.log`, and more rows will take longer.
    - *Code it needs.* `ft_rows_of` and `dfix_records` take BKS and GOAT only; capture rows need a row-id range and a rows-per-epoch rule, which the recipe does not yet define (BKS and GOAT cycle to 300 each); `cmd_train_ft`'s input hash and inner fold check must learn them; `build-dfix-real --captures` reads the first batch only, and for a capture unit `session_of` gives "cap", so the rule that a unit never gets its own session's backing does nothing, while 31 of the second batch's 49 DI files sit in a pool session.
    - *Folds, the open choice.* Linking creators and DI files gives one component of 294 of 297 units, so no clean fold exists and something must be dropped. Draft: creator folds, re-drawn on the pooled units (11 creators are in both batches), and FTc_k drops every row sharing a DI file with a fold-k capture unit. On all units before the gates that costs 17 to 30% of GOAT's rows, 18 to 27% of the first batch's and 54 to 58% of the second's; the inner runs must drop for both k and j, which costs 40 to 53% of GOAT's rows and 55 to 64% of the captures'. The reverse leak drops too: 23 to 31 of about 110 first-batch training rows sit on a DI held in GOAT's fold k, and the inner runs validate on fold j's GOAT units, so E could otherwise be chosen on a leaked DI. The alternative to count: DI-file folds for the second batch, where a capture has one unit, at the cost of creators crossing folds.
    - *Reads.* N6's rows on held capture units, with FTm_k by its own DI fold (only 39 of the first batch's 150 units share a pooled creator fold and a DI fold, and the second batch's DIs are in no GOAT fold, so FTm's comparison there needs its own rule); the score on the same units; the ear only in L2. The second batch's labels stay unread until its gates pass. No V-real, NS song or panel read.
  - **Rules and guards.** Renders as ever (isolate=True, one priming render, 0.25 s trim, at most 3 processes, the 31 GB
    guard). Captures run in `tools/nam-venv` with `python -I`, read as data from their own folder; `.nam` files stay out
    of git. No TONE3000 fetch. V-real and the NS songs untouched. Records under `captures/`, apart from `goat/` and
    `real/`. In code, each with a test: `require("phase_l1a")`; the `.nam` sha against the manifest; the DI cap; the blind item picker; the letter balance; the ear and heavy gates; the minimum at both points; the seeded search order; no BKS, GOAT or
    V-real reader sees a capture record.
  - **Caveats.** A capture is one setting of one amp, its mic not ours to choose. All DIs are GOAT's, most items one
    player's. The labels fit the measure DI, so F20's cap applies, though the Record here plays the same performance.
    One listener, 12 parts, and the listener will have heard each capture on the ear gate. Nothing here is a real song:
    a label heard closer on a capture does not show a model reading a song.
  - *Review (2026-11-04, independent, before any render):* 12 required changes, then 7 on its re-check, all made: the
    check before the spend, the DI cap, the heavy page, the minimum at both points, the judge check on the label's render,
    the placebo drawn blind with its own rows, the ear-score row, the centre read's limits, and the seeded search order.
  - *Amendment (2026-11-05, before any plugin render on a capture; ledger `phase_l1a_night`):* the labels run ahead of
    the ear. The user asked, going to sleep: "Keep working as much as possible without me, do what's needed to make a
    good progress." The ear gate needs the listener, so as declared the machine would stand idle all night.
    - *What moves.* Plugin renders run before the ear gate, on the 150 units of this batch only: the lag pass, then the
      labels in the seeded order. About 8,850 renders, about 1.4 h. The items and placebos, the label page's 72 renders and
      the page all wait for the ear.
    - *What does not move.* After both gates the items and placebos are drawn by the declared rules and seed from the
      trusted, lag-kept units. The picker reads no search record, and `items.json` is written once. No label, score, centre
      or judge figure is read before the ear. At a third of the units the machine stores only go or stop, as a fault
      check; a stop pauses the run, and its figures and the rows beside it stay unread. After the ear the lag rule and the
      stage check, with those rows, run on the trusted units alone. That is the declared check, and its stop holds the
      label page. Every unit with a lag is searched at night, whatever the lag rule later says, so the rule only ever drops a
      label. No score figure reaches the listener before the label page's answers. Apart from the go-or-stop, every reader of the search records runs behind `trusted`. The minimum after the ear and the lag rule stands, as do the capture
      page, the heavy page and the label page in that order. The centre read still waits for the primary share and stays a
      counted panel read. No training before the ear.
    - *Guards, each with a test.* `search` refuses before both gates by default. The pre-ear path needs an explicit flag,
      `phase_l1a_night` and this batch's 50 sha256s (`phase_l1a_night_batch`), and refuses any later batch. `items` refuses
      before both gates and refuses a second run. `stage-check` takes the trusted set; the pre-ear go-or-stop prints no
      figure.
    - *What it costs.* The order put the check before the spend because L0's map asked for it "before any large spend". On
      an idle night the spend is machine time alone. On "the primary share clear below" the labels go unused, and the map
      stands. The listener waits a few minutes between the heavy page and the label page. This reverses a declared rule on
      a general request, so the first message to the user says plainly that the labels ran before the ear and that nothing
      was read.
    - *Review (2026-11-05, independent):* changes required and made: the items after the ear, the placebos drawn only from
      trusted units, the stage check's figures unread before it, and the guards above.
  - **L1a's gates (2026-11-05).** First batch's ear gate: 49 of 50 passed, 1 unsure (Recording 28), which the gate drops, 3 units. Heavy check: 4 cards, 2 kept, 2 out. 145 units pass both gates; the lag rule keeps 132, from 49 captures and 20 creators, 20 to 27 per amp and class. Stage check on those: held best − S −0.356 [−0.389, −0.323] by creator (20 clusters), `inputGain` at a bound on 8%, go on; search gain 0.365 beside BKS's 0.364 and GOAT's 0.307; label `inputGain` against capture gain, Spearman −0.04 [−0.21, +0.19]; 18 of the ear page's 50 clips outside BKS's cab range. Label page built, 72 renders, every fresh render within its checks, build 04cf993bee72, 14 items.
  - **The label page's outcome (2026-11-05, F57).** 11 of the 12 parts ranked, one held out by the listener as out of scope. The primary share reaches one half whichever way that part would have gone, so by the map it is not known on the rank, and the closeness row, clear of zero at +1.45 [+0.91, +2.00], is the user's evidence on whether to go on. It is not clear below, so nothing declared stops; the centre read stands and waits for the scope check, because it reads the trusted labels. The reads go to the user beside the yield: 130 of 150 units (87%, against GOAT's 81%) before the scope page, at least 108 (72%) after it. Training still waits for the user's yes on going on, the second batch's gates and its own declaration.
  - *Amendment (2026-11-05, after F57, zero plugin renders; ledger `phase_l1a_scope`):* a scope check. The heavy page heard only `driven` units, and the two units the listener called "Too distorted, out of scope" were both `uncertain`, 2 of the 6 crunch units on the label page. The drive measure does not separate them (F57), so no line can drop such units without the ear.
    - *What changes.* `LABEL_PAGE_OUT`: the two units leave `trusted`, which leaves 130 units, 48 captures, 19 creators, 20 to 26 per amp and class; the lag rule keeps every other unit. A new page, `capture_labels scope`, on the heavy page's questions: every trusted undriven crunch unit with `nonlinear_db` at or above −3.0 not on the label page, 22 units from 14 captures. −3.0 is a free choice: of the label page's crunch parts only the flagged pair and i7 (−2.18, ranked with no note) sit above it, and the next, i8 at −3.44 and i12 at −3.81, were ranked with no note. Only "keep" stays, and it drops that unit alone, as on the heavy page; a unit below the line, or not on the page, stays in unheard. The page refuses to be read while a card is unheard or the answers are another build's, as the heavy page does. `rest_may_run` reads this build's null `branch` as reaching one half (`HELD_OUT_READ`, by build, so a truly partial file still fails closed) and waits for the scope page. `cmd_search`'s default path skips an item outside `trusted`.
    - *What does not change.* `items.json`, the stage check's stored figures and F57's rows. The stage check is not re-run. The minimum of 10 per amp and class still applies; it holds at 130 units and cannot fire on this page: with all 22 cards out the smallest cell is 12 (pr12 crunch).
    - *The second batch.* One unit a capture, so its ear card is the unit itself: the listener marks a card too distorted for scope "not sure", which drops it as any verdict but the first does. The page stands as built, and its heavy page as declared.
    - *Review (2026-11-05, independent, on F57 and this amendment):* 13 required changes, all made: the gate failing open, `rest_may_run` both ways, the crash in `cmd_search`, a missing test, seven passages on F57 that went further than the evidence or the declaration, the yield and the minimum.
- **L1b's gates (2026-11-06).** The ear page, build fe2306eaa66e, 147 of 147 heard: 49 passed, 84 odd, 14 with a bad DI, 33% against the first batch's 98%. Crunch passed 9 of 73 and clean 40 of 74. The page asked that too-distorted cards take any verdict but the first, so "odd" holds those as well as other faults, and the two cannot be told apart. The heavy page has 0 cards: no passed unit is firmly driven. The stage check goes on: held best − S −0.425 [−0.494, −0.356], 47 labels, 37 clusters, inputGain at a bound 2.1%. One unit's held half is refused by the judge in every setting, so it leaves that row and stays a label; the check's filter gained a finite test, which changes no earlier read. **47 trusted units, 38 creators, 27 DI files: ac20 clean 16, crunch 2; pr12 11, 4; sw50r 11, 3.** Crunch stays thin, so the second batch adds clean units and new players, not crunch. **The declared minimum fired:** L1a's 10 per amp and class after the ear and the lag rule, which L1b keeps, is missed on all three crunch cells (2, 4, 3), and the code's check sits in `cmd_items`, which this batch never runs. The block is revised as the rule asks: the minimum protected a cell's centre, so these labels make no centre read and no crunch row; N10 reads within-cell r, with the all row still pooling those small cells, stated there. More crunch would need new captures and the user's yes.
- **L1b, the second capture batch (ledger `phase_l1b`; 2026-11-05).** The user allowed more TONE3000 downloads the night L1a was
  declared, and signed the fetch in. 150 more named captures (`manifest-batch2.csv`): 108 packs, 79 creators (11 also in the first
  batch), 8 families, 91 crunch and 59 clean by the makers' words and the fetcher's guess on 17, 50 calibrated, 137 A2 and
  13 A1 Standard. The aim of 200 stopped at 150 because the caps (2 a pack, 5 a creator) and the named-mic rule thinned the picks.
  - **What stays as L1a.** The loader, the level rule, the walk's crunch-then-clean, the DI cap, the ear page's one card per capture on
    its most driven unit (here its only unit), the heavy page, the minimum, the gates in code.
  - **What differs.** One forced amp per capture, balanced and seeded: three amps on one recording are worth about 1.4 rows
    (the ML review's ICC of 0.55), and distinct chains are what the bet needs. DIs from the clean-DI library rather than GOAT's: its trusted, clean,
    disjoint sections, at most 40 a band, leaving out V-real's 7 bands, the NS bands, the panel's bands, Jen Hartswick & Nick
    Cassarino, and BKS. 391 sections from 19 bands, far more players and guitars than GOAT's, and the DI's section is written beside the
    render. The bands take turns as the players did, so a band of one section gives at most 3 units.
  - **Files.** `manifest.csv` is not touched. Records under `captures2/`, pages `capture-ear-2`, `capture-heavy-2`. Uncalibrated files (100 of
    150) play at 0 dB; their stored-level gap is reported apart, as is any file that will not load or does not read 48 kHz (2 A1 files, `b70728aebf23d74b` and `dcd7d0be7df79ce8`, store no rate: `.nam` 0.5.1 of May 2023, every later A1 file stores 48000 and NAM's loader allows old files without the field, so they are kept at 48 kHz, inferred and not measured).
  - **Labels ahead of the ear, nothing read (`phase_l1b_night`, digest `phase_l1b_night_batch`).** As L1a's amendment, on this batch's own files, on the same request.
    The recipe is N2's outcome: v2 if the report adopts it, otherwise GOAT's. No use of any label before both gates. 147 units (3 captures read high gain on every candidate: an Orange OR60, a Vox VBM1 and a Marshall DSL1), about 6,500 renders on v2.
  - **The ear.** The listener hears the first batch, then this one: 147 more cards in 2 parts. Dropping a capture needs no more than that verdict, as in the first batch.
  - **Use.** With the first batch, these labels feed the training declaration after L1a's label page. This batch holds no ear items of its own.
- **N1 to N3, the model's real-amp training and the labels' search (2026-11-05, ledger `phase_night2`; `learn/night2.py`).** An
  independent ML review of the labels and data (2026-11-05, read-only, BKS and GOAT only) found three things. Real rows label
  every unsearched control as S: of a real label's sounding heads, 64% of knobs and 85% of switches are S's constants, so FT's
  held loss, and the epoch count it chose, are mostly those. A no-audio table beats FT on that loss on all 4 folds (audited);
  F42's fall from 5.7 is not evidence of reading. Its audit then found FT reads per track, weakly, most robustly on GOAT's cab, from mic position and distance about equally (fold-demeaned,
  one value per recording, 90% item intervals: GOAT drive +0.088 [+0.015, +0.159], tone +0.121 [+0.028, +0.224], cab +0.191 [+0.126,
  +0.263]; own output against another recording's −0.185 [−0.236, −0.134]). W, with no real rows, reads tone about as well (FT − W −0.102
  [−0.215, +0.020]) and cab backwards. BKS's cab is not a read of skill: a no-audio table of the same rigs' labels matches it. Earlier pooled
  figures are withdrawn. And the search
  is about one and a half sweeps at a fixed step of 0.25: 52 evaluations, 8 dB input-gain resolution, 18 of them on mics
  for 11% of the gain. The user asked: "Keep working as much as possible without me, do what's needed to make a good progress."
  These runs use trusted data only, need no listener and bear on the main bet more directly than L1a's labels do. They are taken as
  covered by that request, an unplanned training that the rules otherwise ask about, and the first message to the user says so.
  - **N1, masked FT.** FT's recipe unchanged (W's best state, the same real rows, lr 1e-4, cap 300, patience 15, 4 folds × 2 seeds,
    the 8 inner runs, then 8 FT_k), except that on every real row, training or held, the heads outside `K.space(amp, S)` and the
    amp head leave the loss, so E is chosen on searched heads alone. The readout holds every control outside `K.space` at S:
    those heads stay W's, and F54 heard W's effects. Runs `P2b-ftm*`, about 12 min each on MPS, two at a time, about 2 h.
    - *Reads on held folds.* (a) Zero renders, the audited reads (`reads_v3.py`, sha256 a04785f3a4838ae2, adopted 2026-11-05 in place of v2 before any FTm read, since v2
      lacks BKS's exact permutation, GOAT's item intervals and the paired rows; independently reviewed; moved into the repo at the
      write-up), for FTm, FT and W: r demeaned within fold, amp, class and head, one value per recording, by drive, tone and cab, with
      90% item intervals on GOAT and exact permutation p on BKS, head-standardised, and without range-limit labels; FTm − FT and FTm − W
      paired; own output against another recording's; on BKS beside the no-audio rig table, whose r is the bar for cab. BKS's 4 blocks are 2 songs, so its intervals stay
      descriptive. No pooled r. (b) By the score, on read 2's units and rules, about 1,340 renders each: FTh, FT's stored answers with every
      control outside `K.space` held at S (no training), and FTm. FTh − FT reads the hold alone, FTm − FTh the mask alone, and FTm − S
      stands beside. 238 of FT's 670 stored answers have `drive2` on and 92 `drive1`, against S, so without FTh the two changes
      could not be told apart. No panel, no V-real, no ear. The held loss is not a read of skill: it flips with the comparator. The masked path has no fallback, so E is taken as it comes,
      and it now rests mostly on mic cross-entropy, the noisiest labels; the argmin of the held knob loss is reported beside E and not acted on.
    - *Reading.* Effect sizes, by group: a rise shows a reading the constants hid, a flat row with the score holding says they were
      not what blocked it, and tone is watched apart, since W reads it without real rows. A win here is a lead for L2, and any choice from BKS stays a dev choice.
  - **N2, the search.** v2 runs from S: drive and tone at step 0.25, then up to 4 mics per side (each amp's commonest in
    GOAT's labels), then the knobs of drive and tone at 0.125, then cab at 0.25; a move stays only on a log gain of 0.005 or more, at most 44 evaluations; the fine sweep skips switches, so every cab control is reached on
    each amp. Test: 16 BKS near-replicate section pairs, one amp each, balanced, about 1,250 renders. Reads: replicate rms by
    group and held-half gain against the stored labels on the same directions, clustered by recording. The report's rms is the root mean squared
    difference, √2 above the review's table, so v1 and v2 compare only within this report. Adopted for the capture labels, by the report's own fields, if v2's replicate rms is below v1's on drive and on tone and the
    held gain's v2 − v1 interval has its upper end at or above 0 (plus is v2 better). The distance moved from S sits beside, since labels that
    move less shrink rms trivially. The rule has no margin, its bootstrap runs on 8 recordings (coverage about 83%), and the 16 pairs sit on 5 DIs of
    one song. The capture labels wait for this report. Adopted or not, they run by amendment of L1a's `phase_l1a_night`, this batch only; if
    adopted, they keep `A.fallback_reason`, which v2 does not apply. `_wait_cap` counts neither of these searches, so the 3-process limit is held by hand.
  - *N2's outcome (2026-11-05, 1,207 renders, 37 evaluations on average):* adopted by the declared rule. Replicate rms (root mean squared
    difference) v1 to v2: drive 0.131 to 0.103, tone 0.126 to 0.105, cab 0.189 to 0.130; held gain 0.328 [0.276, 0.387] to 0.296 [0.228, 0.373], v2 − v1
    −0.032 [−0.082, +0.014]. The row beside says much of that fall is smaller moves: distance moved from S, drive 0.306 to 0.266, tone 0.284 to 0.192,
    cab 0.306 to 0.124, so noise against shift is about level on drive (0.43, 0.39) and worse on tone (0.44, 0.55) and cab (0.62, 1.04). It fits
    F-C's finding that most cab moves bring next to no gain, but v2 is not shown more reliable, only coarser moves dropped; the rule held no margin for this, and it is
    followed as declared. Capture labels run on v2 (`--recipe v2`), which saves about 30% of the renders and mixes recipes in training with BKS's and GOAT's. If the labels
    matter more than that, v1 on the captures is about 1.2 h a batch.
  - *N1's first read (2026-11-05, zero renders, knob units, reads_v3 as declared, by the review session):* on GOAT FTm reads tone clearly better
    than FT (FTm − FT +0.137 [+0.065, +0.207]) and now holds W's tone with FT's cab (FTm − W tone +0.036 [−0.060, +0.127], cab +0.303 [+0.219,
    +0.390]); drive is unchanged. FTm: drive +0.082 [+0.019, +0.144], tone +0.258 [+0.174, +0.338], cab +0.218 [+0.155, +0.284]; own − swap −0.294
    [−0.377, −0.210]. Without range-limit labels tone holds (+0.176). E fell from about 190 to about 60. BKS's paired rows decide nothing by the read's rule (four blocks): FTM − FT reaches zero on all three groups, and FTM − W is +0.574 on drive and +0.694 on cab, 4 of 4 blocks, tone −0.016. Its cab sits where the no-audio table does. Nothing here is sound, and nothing is through a stem. By the score (F55): the mask alone is better on GOAT (−0.023 [−0.036, −0.011]) and
    worse on BKS (+0.039 [+0.014, +0.063]); the hold alone is level on GOAT and a little worse on BKS; FTm − S −0.094 on GOAT, −0.123 on BKS.
  - **N3, the learning curve (declared 2026-11-05 after N1's first read; ledger `phase_n3`).** On FTm, the better by those reads: 25% and 50% of each
    amp-and-class cell's training records, a record's copies kept together, nested and seeded, and 100% with labels shuffled within amp and class, 4 folds × 2
    seeds, FT_k's only, at FTm's E in as many updates. 24 runs, zero plugin renders, about 1.5 h on MPS. A first start sampled rows, not records, and was stopped before any run
    finished. Reads on held GOAT, FTM25, FTM50, FTM, FTMs and W beside, pairs FTM−FTM25, FTM−FTM50, FTM−FTMs and FTM−W, by group. BKS stands beside and decides nothing (four
    blocks, the read's rule). A group rises if FTM−FTM25 and FTM−FTMs both clear zero above. An interval reaching zero is undecided and says nothing against more rows.
    FTMs is not chance: it starts from W, which reads tone without real rows (+0.222). E is not re-chosen at smaller shares, and FTm was picked on these same reads, so both
    lean toward a rise. r is agreement with search labels, not sound, so a rise is a case for trying captures, and the sound read stays L2's.
  - **N4, FTm by ear (declared 2026-11-05 after N1's score read; ledger `phase_n4`; `learn/ear_ftm.py`).** N1 and N3 read knobs and the score, and the
    user's yardstick is the ear on real songs, through the stem. So a blind page on L0's 10 parts, in L0's recipe: same directions, measure DI, held windows,
    with S, FT and FTm, S's and FT's clips being L0's stored renders. FTm is the all-labels run (both seeds, the median inner E, about 20 min on MPS), read on
    the X-LANCE stem as read 3, controls outside `K.space` held at S, 40 renders, 20 of them S controls that must equal L0's, 2 repeats, letters as L1a's page. Reads as L1a's page, pooled over parts and band-weighted, clustered by band: FTm above S and above FT from
    the forced rank, closeness, the score beside; clean and crunch beside. It picks nothing: this is V-real's fifth read at least, and the first with parts the listener has
    ranked before. A clear row is a lead for L2. A row reaching one half is not known by ear. On these 10 parts in 7 bands a true 75% clears about half the time (52%), a true 60%
    clears 20%, chance 4% (simulated on `boot_share`). L0 chose each amp by S's closeness, so FTm − S leans toward S. FT's clips carry no hold, so FTm − FT mixes the hold and the
    mask. One listener, on parts heard before. FTm's stored judges stay unread until the page is scored. No other V-real direction is read.
    - *Outcome (2026-11-05, F56):* every row reaches one half, so FTm is not known by ear, against S or FT. It picks nothing and adds no ear lead for L2 by the declared map; F55's lead on GOAT, by knob and score, stands as it was.
      By the score S is closer on these parts (ln(d_S/d_FTm) −0.107 [−0.198, −0.021]).
  - **N5, does the reading survive the stem? (declared 2026-11-05 after F55; ledger `phase_n5`; `learn/night3.py`).** Every model above trains and reads a real unit in a
    backing; the product reads an X-LANCE stem, and the ML review found the two inputs far apart (domain AUC 0.997). V-real is the only stem read so far. So each labelled BKS
    and GOAT unit's variant 0 mix is rebuilt (its features must equal the stored ones exactly), separated by X-LANCE, and brought to the product's level (the mix at −12.25 LUFS,
    the stem at the same gain). Zero plugin renders, about 25 min on MPS. Reads, reads_v3 on held GOAT with the stem in place of the backed input: FTm, FT and W by group, stem
    against backed paired, and own against another recording's. BKS beside, deciding nothing. Reading: an interval clear of zero below says the separator costs that group's reading, and the next fix is
    on the input (fine-tuning on stems) rather than on more rows; reaching zero is undecided. Knob units, no sound. A pool backing is not a song: no other guitars here, so this is the kindest stem.
  - *N5's outcome (2026-11-05, 316 units, every rebuilt mix equal to its stored features; reads_v3s, sha256 f9beeed5f3396097, independently checked; zero plugin renders; in `night2/reads-v3-n5.json`):* on held GOAT neither FT nor FTm shows a stem cost
    in any group. Stem − backed: FTm drive +0.008 [−0.033, +0.052], tone +0.054 [−0.010, +0.120], cab −0.004 [−0.044, +0.037]; FT +0.004 [−0.037, +0.048], +0.050 [−0.025, +0.131], +0.002 [−0.054, +0.053]; W −0.079 [−0.145, −0.010], +0.056 [−0.029, +0.143],
    −0.011 [−0.062, +0.034], W's drive the one clear cost of nine rows. FTm on the stem: drive +0.090 [+0.023, +0.157], tone +0.312 [+0.235, +0.383], cab +0.214 [+0.157, +0.277]; own − swap −0.322 [−0.406, −0.237]. By the declared reading these are undecided, and the
    plan's branch to fix the input has no support here for the tuned models. BKS beside, deciding nothing: all its stem − backed intervals reach zero, and FT's and FTm's six point estimates sit below zero. This is the kindest stem: no other guitars in these mixes,
    the stems sit a median 6 to 8 dB below their mixes (61 units below −12 dB, 25 below −20 dB, 2 with a silent half). Knob units, no sound.
  - **N5b, by the score through the stem (declared 2026-11-05 after N5's outcome; ledger `phase_n5b`).** FTm_k on the same stems, `P2b-ftm-stem`, controls outside `K.space` held at S, rendered on read 2's units, about 1,340 renders, the unit with no stem counted out. Rows
    by read 2's rules: FTm-stem − FTm, FTm-stem − S, FTm-stem − FT. It says what the stem costs by the score on held units, with no other guitars; it is not a song and picks nothing.
  - *N5b's outcome (2026-11-05, 1,336 renders, `real/report-n5b.json`, `goat/report-n5b.json`):* by the score on held units the stem shows no cost: FTm-stem − FTm +0.013 [−0.008, +0.033] on BKS, +0.003 [−0.009, +0.015] on GOAT.
  - **N6, the models on a set they were not chosen on (declared 2026-11-05 after F57; ledger `phase_n6`; `learn/reads_capture.py`; zero plugin renders).** F57 rates the labels above S given the true DI, and F56 cannot tell FTm from S by ear on songs. Between them sits the read, and every knob read of FTm so far is on the two sets its recipe was chosen on: its E, its adoption and its lead come from BKS and GOAT, whose labels came from search v1. Its one read elsewhere is F56, by ear and by the score on L0's 10 V-real parts, not a knob read. The first capture batch is a set no model has trained on or been chosen on, with full rigs where GOAT has a capture and a random cab IR, labels from search v2, and F57's ear check behind them. About half of it is crunch, where the deep review's step 3 asks about drive: 80 of the 150 units before the gates, and the scope page can only take crunch units out. It is also the baseline any model trained on captures has to beat.
    - *Rows.* The first batch's trusted units, after the scope page (`search_records`, 108 to 130 units, 19 creators at most). The backed input as a GOAT unit's: 25 pool backings, levelled by a lender of its class (`build-dfix-real --captures`, all 150 units, which reads no label, 3,750 inputs at the measured 0.21 s, 3 shards). The read takes variant 0.
    - *Models.* FTm_k and FT_k, where k is the fold that held out the unit's DI: every one of the 150 units' DIs is one of GOAT's 139 items, each one DI file in one fold, so the unit's performance is not in that model's real rows, as its capture is not (the 9 items with no label are in no model's real rows). W beside, with no real rows. Both seeds, as `reads_v3`.
    - *Reads.* `reads_v3`'s own functions (sha256 a04785f3a4838ae2): r by group, one value per recording in a cell, demeaned within (fold, amp, class, head), with the permutation among recordings, the answers' spread against the labels', r head-standardised and r without range-limit labels beside; own against swap by t, by creator; a bootstrap by creator and leave one creator out. All, crunch and clean. Pairs FTm − W and FTm − FT on the same draws. Primary: FTm's drive on crunch. At 19 creators at most, fewer on crunch, the percentile interval runs a little short. The permutation p sits beside it, but it moves units within cells and not creators, so it does not correct that; leave one creator out shows whether one creator carries a result. The primary row holds at most 78 units, at most 56 if the scope page takes all 22 cards. Simulated from those counts, its interval is about ±0.15 to ±0.20: a true r at GOAT's level (+0.08) clears zero about one time in five, and it takes about +0.25 to +0.30 to clear four times in five.
    - *Control, before any capture row.* The read's copied loop on GOAT's held records must give N1's stored r and own-against-swap total (`night2/reads-v3-ftm.json`) within 1e-6, for FTm, FT and W, and `reads_v3.py` its stated sha. It stops otherwise. It covers the inputs' loader, the models, the medians and the swap loop, not `fold_of`, `search_records` or the `--captures` build, whose code was read by eye.
    - *Map, no bars.* FTm's drive on crunch clear above zero, by the creator interval: its drive answers follow the search labels on a set it was not chosen on, so the question moves to the size of its answers (the spread row); what that says of F56's songs is not known, since those are stems of real mixes. Reaching zero: not shown, undecided, and at this size expected even if FTm reads crunch as it reads GOAT; the row is the baseline a model trained on captures has to beat, with step 3's representations next. Clear below zero: the read runs backwards on this set; stop and look at the input before any training. Tone and cab read the same way, beside. r is agreement with search labels, not sound, and nothing here picks a model.
    - *Limits.* The DIs are GOAT's, so these are new recordings, not new players. GOAT does not record which of its about 7,000 profiles a chain used, so a capture here may share an amp profile with a chain the model trained on, with another cab. A capture's units sit on 3 amps, and its creator is the cluster. Variant 0 is one backing draw. The labels hold search noise, which lowers every r: 16 to 32% of variance by group on v1 (the deep review, 16 near-replicate pairs on one band), and on v2 noise against shift is about level with v1 on drive and worse on tone and cab (N2's outcome). So a tone or cab r below GOAT's here may be the labels, not a weaker reading. The 3 forced amps are not the amps these captures are, which is also true of GOAT.
    - *Outcome (2026-11-05, F59):* FTm's drive on crunch +0.159 [+0.035, +0.272], clear above zero by the declared interval. The audit: it rests on one knob, ac20Power (without it +0.071 [−0.023, +0.166]), a jackknife by creator just clears zero, and the answers explain 2.5% of the within-cell label variance. Clean tone +0.354 and cab +0.301 hold.
    - *Review (2026-11-05, independent, before any run):* 5 required changes, all wording, all made, and the code found sound by reading, with `reads_v3`'s functions and a copy of `report`'s body run on made-up rows of this shape. The reviewer's first script stubbed `scope_out` to count the trusted set; the permission system refused it before it ran, and no label was read.
    FTm-stem − S −0.110 [−0.190, −0.030] by DI (by fold −0.10 [−0.22, +0.03]) and −0.091 [−0.114, −0.068]; FTm-stem − FT +0.067 [+0.035, +0.098] and −0.018 [−0.038, +0.002], the same split between the sets as F55. No other guitars in these mixes, and 2 GOAT units with a silent stem half stay in, as the product would read them.
  - **N7, the mix on its dominant cells (declared 2026-11-05, the user's go; ledger `phase_mask_read`; zero renders, no training beyond linear probes; [design](tone-info-probe.md#addition-the-mix-on-its-dominant-cells-declared-2026-11-05-before-it-is-computed)).** The largest measured loss is the mix's, 86 heads to 30, and no step so far has read the mix at the cells where the guitar dominates. A linear probe reads the stored mix on marked cells only: a true map first, as a strong case for the idea, then two stem maps, each against the plain mix and a placebo map from another section. The stem only selects cells: no stem value enters the features. This runs on FS5's self-built mixes and touches no capture, V-real part, NS song or panel unit, so it waits on none of the listener's pages. Its map of readings stops mask pooling, or moves the question to a better map or a denser read, or earns one model step, each in its own declaration; it says nothing of sound.
    - *Outcome (2026-11-05, F58):* the true map 35 readable against the plain mix's 30, 21 better / 8 worse, stem maps 19, 2 / 19 and 0 / 29: "better map next" by the declared map. The audit, at this margin and with this reader: clean values on the true map's own cells read 38, against 71 on random cells at that density and 42 to 43 on cells with the same kind of band layout, so the limit is how few bands those cells cover; (g) is no better than random cells and (t) worse. No better map is declared; mask pooling on summaries is parked.
  - **N8, does the stem lean toward another guitar? (declared 2026-11-05; ledger `phase_stem_lean`; zero renders, no training beyond linear probes; [design](stem-lean-plan.md)).** The deep review's step 4, with an interval and no NS rows. Two linear readers on T2's core twins, one learning the target's labels and one the loudest other guitar's; primary on the stem, their amp hits' difference; the mix beside, so a lean the mix already has is not charged to the separator, and a clean-target control. It runs on FS5's self-built mixes and waits on none of the listener's pages. Step 3, drive on crunch, sits in the review session's comparison.
    - *Outcome (2026-11-05, F61):* not shown, +0.025 [−0.118, +0.169]. Beside, a linear reader trained on the target leans toward the other guitar on drive and cab, in the mix as much as on the stem, so no training on real stems is proposed.
  - **Rules.** Apart from N4's declared page, BKS and GOAT only. V-real, the NS songs, the panel and the captures stay out. The capture page and its labels are
    untouched by these reads. Runs saved apart (`P2b-ftm*`, `night2/`), FT and its answers unchanged.
  - **Caveats.** The review's figures on sound are unmeasured. BKS is 8 DIs in 2 songs (the replicate pairs 5 DIs of one), and its performances sit in W's plugin rows, so held
    means held tracks, not held playing. Nothing here is a real song.

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

### F47. On this chord DI the carry-over part ranks the page worse than J0: the effects were barely heard, and |C| lifts them and the crunch steps above the high shelves heard clearly (phase_judge_v5, the fresh page)
- **Result.** The fresh blind page (headphones, build 9140fa6a723e, 2026-11-03; 30 items, every answer marked
  sure; both catches heard as the same). Before scoring, the page's 60 clips were decoded and matched to the key by
  correlation against the intended level-matched audio: 0 mismatches (`judge-v5/page-audit.txt`). J0 / J5 (w_c 8,
  frozen) and the rating, per item against S unless stated (PR12's tone 0.70 step is 0.535 down to 0, opposite in
  direction to its 0.30 step, which goes up):

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
  resamples kept). F44's inversion rule: J0 8, J5 26. J0's 8: 7 have a +6 dB high shelf heard clearly or very scored
  below clean reverb or delay 0.40 (3, heard barely), clean combined (2, same), or crunch drive +10 dB and tone 0.70
  (2, same and barely); the eighth is clean tone 0.30 (clearly) below clean delay 0.40 (barely). In 18 of J5's 26
  the heard item is a high shelf. Of the 19 pairs J5 turns wrong (one turns right), 7 put an effect above a tone or
  drive step, 7 an effect above a shelf, 3 a crunch tone or drive step above a shelf (|C| lifts them too: crunch
  tone 0.30 0.97 → 1.38), 1 combined above a shelf and 1 combined above a tone or drive step. Within the effect
  groups and within tone and drive both judges' cross-group gamma is 1.0 (few pairs: 14 and 12). Tonal trigger: not
  fired, and it could not: no effect was heard clearly or very. Reported beside: without the anchors (plugin
  controls only) J0 +0.942, J5 +0.808, J5 − J0 −0.135 [−0.259, +0.031] (16 clusters, 1,998 kept); clean alone
  −0.327 [−0.532, 0.000], crunch alone −0.174 [−0.400, 0.000] (9 clusters each; crunch kept 1,783 resamples).
- **Reading.** By the declared rule J5 is undecided and not adopted (the lower end is not above 0). The effect size
  leans against it: the interval lies wholly below 0, but that rests on the offline anchors; on the plugin controls
  alone it includes 0 (−0.135 [−0.259, +0.031]). On this chord DI this listener barely heard the effects: of the 12
  effect items only clean reverb and delay at mix 0.40 were heard, and barely. On F45's headphone recheck of the
  single-note DI, reverb, delay and spring at mix 0.40 (and clean spring 0.5) were heard clearly or very; at mix
  0.15 they were the same or barely there too. Why effects were heard less here is not separated: the chords are
  spectrally denser (10 against 2 peaks), and the presets and the sitting differ too. It is not that C missed the
  page: C reads large on half B's fall (clean reverb 0.15: 0.237; clean delay 0.15: 0.349) where the ear heard the
  same. Tone: AC20's cut steps were heard clearly or very, while PR12's treble steps (crunch here) were the same or
  barely, as on F44; the +6 dB high shelves were heard one step more than on F46 (clean barely → clearly; crunch
  SW50R clearly → PR12 very). Drive: AC20 clean +10 dB was heard very (PR12 clean +10 was the same on F44's single
  notes) and PR12 crunch +10 the same (SW50R crunch +10 clearly on F45), which bears on F44's question whether chords
  make drive more audible and on F43's drive share. J0, built before either page, ranks the plugin steps here well
  (+0.942 without anchors), but 20 of the 28 rated items were heard as the same, so this rests on 8 heard items
  (2 shelves, 3 tone, 1 drive, 2 effects).
- **What it changes.** J5 is not adopted; J0 stays the judge. Its limit as stated: J0's weighting of effects
  against tone does not hold across pages: on the single-note DI it under-counts effects against treble steps; on
  this chord DI it ranks the plugin steps well but scores +6 dB high shelves below large clean effects and crunch
  drive and tone steps heard less. The declaration leaves the next step to the user: adoption on this evidence, or a
  second page of the same design (new DI and presets) pooled with this one, and then a stop. Recommended: stop
  (adoption has nothing to rest on, and a pooled gain would need a second page to reverse this one); the user's
  choice is pending. In the product, effects follow song research for now (the user, 2026-10-27: sound-alike presets
  are fine, faint effects barely matter); a robust effect part, read through stems, stays an open research target
  (the product and separator checks above). Next on the plan: the approved real-amp recordings and a fresh
  real-song test, scored with J0.
- **Caveats.** One listener, one sitting, one chord DI, two presets (both different from F44's): descriptive; the
  DI, the presets and the sitting change together. The percentile interval may under-cover with 18 clusters
  (stated in the declaration). The reverb-decay and delay-time items share renders with the mix-0.40 items, so their
  clusters are not fully independent. The page asks "how different", not "which is closer to a target", and
  level-matches every clip. Bias: the listener knew the hypothesis (effects under-counted); the ratings went
  against it.
- **References.** `~/ndsp-presets/learn/trusted-data/judge-v5/score.json`, `measure.json`, `page-audit.txt`
  (`page-audit.py`); the answers `~/ndsp-presets/listening/judge-v5/private/answers-9140fa6a723e.txt`; code
  `learn/judge_v5.py` (`score`); ledger `phase_judge_v5`, `phase_judge_v5_frozen`, `phase_judge_v5_outcome`.
- *Results review (2026-11-03, independent):* approved with ten required changes, all made. It reproduced every
  row, gamma, interval, inversion count, the sensitivity lines, the product and separator checks' numbers and the
  page audit. Required: the inversions described as they are; the loss's make-up and its reliance on the anchors;
  the masking mechanism stated as unseparated (C reads large where the ear heard the same); J0's limit stated as
  not holding across pages; the tone and effect comparisons with F44–F46 made precise; the follow-up left to the
  user; the effect part kept as a research target; J0 through stems stated fully; the 8 heard items; the budget.

### F48. On this chord DI the product's blind measures read neither effect, before or after separation: the echo detector abstains, and the reverb rule fires rarely and more often without a reverb than with one (phase_fx_reader E0, exploratory)
- **Result.** `learn/fx_reader.py e0` (zero renders; `analysis/features.py` sha256 e3da64ab…, unchanged before the
  run; 184 items × 3 windows). *Delay:* on the whole stem the echo detector reports no delay at any confidence on
  any of the 36 delay stems of either separator, nor on the 6 delay renders without backing, nor on the 48 S and
  reverb stems: outcomes (a)–(c) are empty, the comb cap (b) never applies, and the detector abstains outright. So
  the declared confidence-by-mix and feedback-against-0.30 readouts are empty (0 against 0). On the 5 s halves (not
  as the product runs it) it reports 12 times, all at the comb cap 0.14 and all at wrong lags (72–240 ms): 3 on
  X-LANCE and 5 on htdemucs reverb stems, 3 on one X-LANCE cell's delay stems, and one htdemucs delay stem at half
  the set 500 ms. Why (`fx-reader/e0-delay-diagnostic.txt` on the 6 renders, and the results review's trace of the
  detector's own gates on those and 6 X-LANCE stems; exploratory): the echo leaves a trace at the set time
  (correlation prominence 0.20 at 500 ms and 0.24 at 300 ms at mix 0.40, against 0.07–0.12 on S; about 0.12 at mix
  0.15; repeat ratio 0.62–0.69 there, under the 0.80 gate). But the chords comb the band (112–172 strong peaks on
  the delay renders, 51–58 on S, against the cap of 12), the chord's own periodicity peaks at 42–73 ms are about
  2.5 times taller, `fundamental()` walks the set-time candidate down to a shorter strong peak (about 150 ms for 300,
  126 or 252 ms for 500), where the repeat ratio is mostly ≥ 0.80, and the envelope, which may veto on combed
  material (and on crunch's flat envelope, 1.7–2.8 dB, anyway), shows no prominence at either set lag. In the trace
  two X-LANCE cells keep the mix-0.40 trace at the set lag (0.16–0.19 at 500 ms, 0.20–0.23 at 300 ms, against
  0.056–0.084 on S stems).
  *Reverb:* `reverb_from_rt60`, counterfactually, on the whole stem: X-LANCE on for 3 of 36 reverb stems (8%) and
  10 of 48 without (21%: S 2 of 12, delay 8 of 36); htdemucs 12 of 36 (33%) and 25 of 48 (52%); the renders
  without backing 0 of 6 and 0 of 8 (confidence ≤ 0.29 against the rule's 0.3). All 13 X-LANCE fires are on the
  clean preset with the eggy and starnes backings; crunch's whole-stem confidence is 0.2 (one release segment), so
  on crunch the rule cannot fire; htdemucs's 37 are 28 clean, 9 crunch. When it fires on X-LANCE the RT60 is
  7–12 s; the whole-stem median falls from 5.8 s on S to 3.5 s at reverb 0.40, and it rises from S to reverb 0.40
  in 6 of 12 X-LANCE pairs (htdemucs 7, the renders 2 of 2). On the second half, which has one fall (confidence
  0.2 is the code's value for a single release segment), the slope rises with decay (1.48 → 3.0 in 12 of 12
  X-LANCE pairs; medians 0.80 → 1.17 s) and is higher at mix 0.40 than on S (0.80 against 0.52 s, 7 of 12 pairs),
  but not at 0.15 (0.49), and delay 0.40 reads higher still (1.39 s; delay time 1.11), so it does not single out
  reverb; htdemucs beside: S 1.59, 0.15 1.66, 0.40 5.31, decay 3.0 5.52 s (S → 0.40 10 of 12, 1.48 → 3.0 8 of 12);
  the renders without backing 0.40, 0.42, 0.83, 1.06 s. `bpm_est` reads about 73–82 on the renders and 176–201 on
  the reverb-decay stems. The repeat render S2 is bit-identical to S, so it adds no repeat-noise check.
- **Reading.** Neither existing measure is a candidate as it stands on chord material. The delay detector abstains
  by design: a ringing chord comb-fills its band, and its gates prefer no answer to a wrong one. The whole-stem
  RT60 does not track the reverb (5.8 s on S, 3.5 s at reverb 0.40), consistent with `study_rt60`'s finding on
  played passages. The failures are already there without a backing, so they start in the measures; with nothing
  to lose, E0 cannot show what separation costs, though both separators add false reverb fires (X-LANCE 10 of 48,
  htdemucs 25 of 48, against 0 of 8 without backing). The echo leaves a trace at the known lag: 2–3 times the dry
  render's correlation at mix 0.40 without a backing (about 1.6 times at 0.15), kept in two X-LANCE cells.
  Whether a reader can find it blind among the chord's peaks, at low mix and through a separator, is untested. One
  DI shows where these measures fail, not where a better one would work.
- **What it changes.** E1 must learn both effects rather than take either measure as given; the correlation at
  candidate lags and release slopes on falls are candidate inputs beside the learned reader's own, and the current
  measures stay its comparators. E1 is declared next, reviewed before any render.
- **Caveats.** One chord DI, two presets, three backings, plugin guitar, 10 s mono-summed stems, no mastering:
  descriptive. The diagnostic and the trace are on 6 renders and 6 stems, exploratory. A kind's 12 stems are 2
  renders × 6 mixes. The script labels a reading within ±5% at a confidence neither ≥ 0.15 nor 0.14 as (d); it never
  happens here.
- **References.** `~/ndsp-presets/learn/trusted-data/judge-v5/fx-reader/e0.json` (every row and the summaries),
  `e0-delay-diagnostic.py` and `.txt`, the review's trace `fx-reader/e0-review-trace.py`; code `learn/fx_reader.py`;
  ledger `phase_fx_reader`, `phase_fx_reader_e0`.
- *Results review (2026-11-03, independent):* approved with nine required changes, all made. It reproduced the
  counts, medians, pair rises and the diagnostic, checked the run followed the committed script, and traced the
  detector's gates. Required: the halves' reports and the htdemucs ½× stated correctly; the mechanism completed;
  the delay trace's scope (known lag, mix 0.40, no backing); the release slope's limits; "fires more often without"
  and the RT60 numbers; what E0 can say about separation; the by-cell breakdown and the empty readouts; a ROADMAP
  typo.

### F49. On the stem the learned reader hears whether reverb or delay is on, a little; no knob's error beats a prior that knows the preset draw, and even on the clean target it reads neither reverb decay nor delay time, though a training-free peak picker finds the echo's lag there (phase_fx_reader E1a)
- **Result.** `learn/fx_reader.py e1a-*` (zero renders; 2,640 examples, 8 songs in 7 bands, leave one song out; 24
  fold-arms, about 20 minutes an arm on MPS; every run file carries the data build's hash, checked at scoring).
  Decision subset, the 770 wide draws (every switch a fair coin, so on/off cannot be scored by knowing the preset):
  | wide draws, AUC [90%] | stem | mix | target |
  |---|---|---|---|
  | reverb, strong third | 0.614 [0.591, 0.648] | 0.552 [0.478, 0.649] | 0.767 [0.733, 0.809] |
  | reverb, all | 0.559 [0.538, 0.588] | 0.516 [0.492, 0.554] | 0.676 [0.646, 0.725] |
  | reverb, weak third | 0.477 [0.454, 0.533] | 0.488 [0.470, 0.526] | 0.574 [0.538, 0.629] |
  | delay, strong third | 0.614 [0.584, 0.640] | 0.609 [0.524, 0.719] | 0.801 [0.781, 0.841] |
  | delay, all | 0.573 [0.552, 0.611] | 0.582 [0.497, 0.675] | 0.726 [0.703, 0.758] |
  | delay, weak third | 0.514 [0.453, 0.604] | 0.543 [0.463, 0.623] | 0.624 [0.588, 0.676] |
  The draw-only comparator sits at 0.44–0.51 on the wide draws, as it should; the reader minus it, strong thirds:
  stem +0.105 [+0.068, +0.147] reverb, +0.165 [+0.132, +0.223] delay. Song-weighted means (stem): reverb 0.523,
  delay 0.579; Storm Of Particles reads reverb at 0.20 on its 15 wide items. Reverb with the offs split by the
  selected amp's spring (stem, wide): 0.524 against spring-on offs, 0.580 against spring-off offs (target 0.641,
  0.696): the spring is read as reverb. *Knobs, wide true-ons, MAE against the declared prior (the training songs'
  median over all draws):* stem reverb mix −0.036 [−0.041, −0.020], decay −0.001 [−0.013, +0.009], delay mix
  −0.044 [−0.052, −0.033], time (log2) −0.202 [−0.250, −0.125], feedback −0.022 [−0.032, −0.015]. *On all items*
  the reader sits below the draw comparator for on/off (stem reverb 0.566 against 0.746) and its knobs are not
  better than the prior beyond a trivial decay gain (−0.004 [−0.007, −0.0004]; time worse, +0.136 log2): there knowing the preset does better than listening.
  *The product's measures on the clean targets (wide):* the echo detector lands within 10% of the set time on 2.2%
  of delay-ons and fires on 8.7% of offs against 6.0% of ons; the reverb rule fires on 38% of reverb-ons and 42% of
  offs. *External* (the Quicksand-out stem fold on E0's 84 X-LANCE stems, descriptive): median delay probability
  0.29 on S, 0.44–0.56 on delay stems and 0.57–0.59 on large-reverb and reverb-decay stems, so it rises with any effect but does not
  tell them apart; median time 275–326 ms against the set 300 and 500 ms; E0's stems are about 6.6 LU quieter than
  D_CC's (−21.0 against −14.4 LUFS).
- **Audit (before the write-up, exploratory; `fx-reader/e1a/audit/`).** (1) *The knob gains are the draw, not
  the sound.* The declared prior is the median over all draws, but wide knobs are uniform, so a reader that knows
  an item is a wide draw beats that prior without hearing the effect. Against a draw-aware prior (the training
  songs' median over wide draws; and the amp × draw × class cell median) the stem reader's error is worse, not
  better: reverb mix +0.019 [+0.006, +0.032], delay mix +0.017 [−0.001, +0.035], time +0.103 [+0.029, +0.249] log2,
  feedback +0.004 [−0.003, +0.011], decay +0.001 [−0.019, +0.013] (cell median alike). It still ranks the mixes
  weakly (Spearman reader–truth on wide stem ons, unclustered, n about 390: reverb mix 0.22, delay mix 0.16,
  feedback 0.11, decay 0.01, time 0.04), so the error looks partly like miscalibration from training on all draws;
  time within ±10% is 8.5% against the wide median's 7.2%, a shift towards the wide range, not a reading. The clean
  target reads the mixes and feedback past the draw-aware prior (reverb mix −0.022 [−0.031, −0.016], delay mix
  −0.016 [−0.027, −0.008], feedback −0.032 [−0.045, −0.023]; Spearman 0.34, 0.33, 0.38), but not decay (Spearman
  0.02) or time (0.07; within ±10% 6.7%). (2) *The time is in the input, and can be found blind on the target.* On
  the stored envelope autocorrelation of the 402 wide delay-ons, the local prominence at the set lag (value minus
  the mean of lags ±3–6, both halves summed) against the same lag on wide delay-offs: AUC 0.79 on the clean
  target, 0.58 on the stem, 0.55 on the mix. A training-free picker, the argmax of that summed prominence over lags
  6–80 (the draw's 60–800 ms), lands within ±10% of the set time on 43.5% of target items (65.7% of the strong
  third; the wide median 7.2%; difference +0.363 [+0.319, +0.431], log2 MAE −0.138 [−0.223, −0.057]), 13.7% of
  stems (+0.065 [+0.019, +0.104], but log2 MAE +0.350 [+0.218, +0.488], its misses far off) and 6.7% of mixes;
  over all 150 lags 38.8%, 9.7%, 5.5%; on the target it lands on double the lag (a feedback repeat) 18%. The first
  version of this audit reported the argmax at 1%: it took the argmax across both halves' columns, so it mostly
  landed in the second half's; corrected by the results review (the as-run script and JSON kept as
  `acf_time_audit-as-run.*`). So on the target the reader fails to use a time cue its input carries and a blind
  picker finds.
- **Reading.** By the declared rule's letter, delay passes (the stem's strong-third AUC interval is above 0.5;
  delay mix and time MAE against the median prior below 0). The audit voids its knob half: against a prior that
  knows the draw no knob's error is better on the stem, and time is not read at all (Spearman 0.04), so E1b is
  **not** declared on this result; the rule's prior should have been draw-aware, as its AUC comparator was. What
  stands: on the stem the reader hears that an effect is on, modestly (strong thirds 0.61 for both; near chance on
  weak ones), genuinely (the wide switches are coin flips). Stem against mix is undecided: the mix arm's Forkupines
  fold (306 of the 770 wide draws) kept its second epoch (index 1), and without that fold the mix reads delay
  better than the stem (strong third 0.659 against 0.616) and reverb about level (0.609 against 0.620). The clean
  target reads on/off much better (0.77, 0.80), so most of the loss is the backing's masking, as
  `docs/tone-info-probe.md` found with linear probes; what separation adds or costs is not settled here. For the
  knobs the declared branch "the target does not read: the reader or its features are the bottleneck" applies to
  decay and time; for time it is the reader (the blind picker reads time on the target), for decay nothing yet
  shows a cue in the input. The product's own measures do no better than chance on the clean targets.
- **What it changes.** E1c (zero renders, declared in the effects route above, reviewed before it runs) asks
  whether a learned lag head reads time on the stem, against the blind picker and the draw-aware prior, the target
  beside. Decay waits for a cue shown in the input. E1b stays the route to the product once a knob reads on the
  stem.
- **Caveats.** Two songs hold 66% of the wide draws (Forkupines 306, BKS Bulldozer 205; Dunning Kruger 5), so
  per-song figures are thin and the 7-band intervals may under-cover; mono mixes; one separator; one seed; the
  reader trained on all draws (where knowing the preset pays), read on wide ones. The audit's priors and the ACF
  check are post hoc.
- **References.** `~/ndsp-presets/learn/trusted-data/judge-v5/fx-reader/e1a/score.json`, `score-stdout.txt`,
  `audit/knob_prior_audit.py` and `.json`, `audit/acf_time_audit.py` and `.json`, run files `e1a/runs/{arm}/`;
  code `learn/fx_reader.py`; ledger `phase_fx_reader_e1a`, `phase_fx_reader_e1a_outcome`.
- *Results review (2026-11-03, independent; one review of F49 and E1c):* approved with eight required changes,
  all made; four on F49. It reproduced the AUCs, knob differences, both priors, the measures and the external
  check, and found the audit's argmax bug (the corrected picker above). Required: the corrected time audit; stem
  against mix undecided (the mix's Forkupines fold); "no knob's error beats a draw-aware prior" with the weak
  ranks, not "reads no knob"; small figures (feedback Spearman 0.38, the external range, the trivial decay gain
  on all items, epoch index 1). The other four amended E1c before any run.

### F50. Delay time does not read on the stem or the mix, by a learned lag head or by the training-free picker, on the stored features; on the clean target the head matches the picker's hits but not, by the declared estimator, its error (phase_fx_reader E1c)
- **Result.** `learn/fx_reader.py e1c-*` (zero renders; 24 fold-arms, about 21 minutes an arm; the trunk's best
  epochs and the on/off AUCs repeat E1a's exactly, as intended). Wide delay-ons (402), against the training songs'
  wide-draw median (within ±10% 7.2%, log2 MAE 0.953):
  | wide delay-ons | stem | mix | target |
  |---|---|---|---|
  | head, within ±10% | 10.7% | 9.5% | 46.0% |
  | difference [90%] | +0.035 [+0.019, +0.078] | +0.022 [+0.002, +0.060] | +0.388 [+0.343, +0.451] |
  | head, log2 MAE diff (posterior median) | +0.251 [+0.195, +0.348] | +0.248 [+0.191, +0.339] | +0.034 [−0.030, +0.099] |
  | head − picker, within ±10% | −0.030 [−0.074, +0.036] | +0.027 [−0.008, +0.090] | +0.025 [−0.006, +0.048] |
  | Spearman, head (picker) | −0.02 (0.02) | −0.07 (0.00) | 0.39 (0.41) |
  Strong third of delay mix (134): stem head 17.2% against the prior's 4.5% (+0.127 [+0.069, +0.281]; with the
  labels shuffled within each song the head scores about 7%), Spearman −0.12, MAE still worse (+0.224 [+0.129,
  +0.412]); the picker's stem hits are flat across thirds (14.2%, 14.2%) while the head's rise with delay mix; target head 67.9%, picker 65.7%, Spearman 0.66 both; weak
  third: stem head 7.5% (below the prior's 10.4%), target 24.6%. E1a's regression time head stays at the prior
  everywhere (stem 8.5%, target 6.7%). Descriptive: the head's own argmax gives log2 MAE 0.789 on the target
  (prior 0.953; the difference −0.164 [−0.287, −0.108], so the target's error-half failure is the estimator's),
  1.314 on the stem (+0.361 [+0.180, +0.432]); the lag head's best epochs were 38–39 of 40 on every target fold
  (still improving), 12–39 on the stem. Its inner cross-entropy starts at uniform (ln 75 = 4.317) and falls to
  3.85–4.07 on the target, but only to 4.26–4.30 on the stem and 4.28–4.31 on the mix: on those it barely learns.
  Shuffled within song, the picker's chance is 6.9% on the stem and 5.9% on the mix: it scores 13.7% (twice chance)
  and 6.7% (chance); stem minus mix, picker hits +0.070 [+0.044, +0.100], head +0.012 [+0.004, +0.025] (the results
  review's checks, `e1c/audit/chk.py`, `chk2.py`). The stem head's MAE beats the all-draw median (−0.054) only
  because that median sits off the wide range's centre.
- **Reading.** By the declared rule time does not read on any arm. On the target the head passes the hit half
  (+0.388) but not the error half: its posterior median falls between candidate lags when it is unsure (its argmax
  passes, −0.164), and its hits equal the picker's (+0.025 [−0.006, +0.048]). By the declared branch the head is
  then not shown working and is fixed before its stem result counts; that fix was not done. *Departure, post
  hoc:* the stem verdict is taken instead from evidence beyond the head. The training-free picker, which reads time
  on the target on both halves of the rule (F49's audit: +0.363 and −0.138), fails the error half on the stem
  (+0.350) with Spearman 0.02 and the mix at chance; the head's argmax error is also worse than the prior's on the
  stem (+0.361); and the head's inner loss on the stem and mix barely leaves uniform, so nothing in these features
  is learned there that a better estimator could turn into a reading. So, for these two readers on the stored
  features (uint8 half log-mels at 10 ms, band-weighted envelope autocorrelation), the echo's time is lost when
  the backing is added (the target reads, the mix is at chance); separation recovers a few hits (the stem's picker
  at twice chance, +0.070 over the mix) but not usable times. A head fix (its estimator, more epochs) could close
  its gap to the picker on the target; it would not lift the stem above what the picker shows there.
- **What it changes.** E1b is not declared. Delay time from the stem, like reverb decay, has no shown route on the
  stored features; on/off reads modestly (F49). The declared masking branch (E1b's renders with a backing split)
  is deferred, not dropped: the cloud researcher's survey of proven blind effect-estimation methods and tools
  (requested at the user's prompt, 2026-11-03) comes first, because it costs nothing and an existing estimator
  would change what renders are worth making. Only uint8 log-mels are stored for the stems and mixes (audio only
  for the targets and the other guitars), so any audio-domain estimator, or finer features, needs the mixes
  rebuilt and re-separated: zero renders, but X-LANCE time (about 4.3 s a clip on MPS).
- **Caveats.** E1a's (two songs hold 66% of the wide draws; 7 band clusters; mono mixes; one separator; one seed).
  The head and the picker were chosen after seeing E1a's audit. The posterior median as the error estimator was
  declared before the run; the argmax's error is descriptive.
- **References.** `~/ndsp-presets/learn/trusted-data/judge-v5/fx-reader/e1c/score.json`, `score-stdout.txt`, run
  files `e1c/runs/{arm}/` (with `lag_curve`, `lag_best_epoch`); code `learn/fx_reader.py`; ledger
  `phase_fx_reader_e1c`, `phase_fx_reader_e1c_outcome`; the review's checks `e1c/audit/chk.py`, `chk2.py`.
- *Results review (2026-11-03, independent):* approved with five required changes, all made. It recomputed every
  figure from the run files (the trunk's predictions identical to E1a's). Required: the departure from the declared
  branch labelled as post hoc, with the head's loss curves and argmax errors that support it; "the separator does
  not recover it" corrected (the stem's picker beats the mix's); the ROADMAP's "matches the picker" narrowed to
  hits; "stored stems" corrected (only log-mels are stored for stems and mixes); the strong third's chance level.

### F51. A long-window cepstrum reads delay time on the clean targets, better than the picker (57% within ±10% on the wide delay-ons, 84% on the strong third); E0's stems mostly test that chord DI, on which the method fails even without a backing (phase_fx_reader E1d)
- **Result.** `learn/fx_reader.py e1d` (zero renders, no training; under a minute on CPU). *Step 1,* the stored
  clean targets, 402 wide delay-ons (the wide median 7.2% within ±10%, the picker 43.5%):
  | targets, wide delay-ons | plain | minus the training songs' delay-off mean |
  |---|---|---|
  | within ±10% (±3%) | 53.7% (51.7%) | 57.2% (55.0%) |
  | minus the picker [90%] | +0.102 [+0.057, +0.128] | +0.137 [+0.086, +0.166] |
  | log2 MAE minus the prior | −0.236 [−0.303, −0.170] | −0.305 [−0.391, −0.243] |
  | log2 MAE minus the picker | −0.097 [−0.177, −0.004] | −0.166 [−0.229, −0.095] |
  | Spearman (picker 0.41) | 0.38 | 0.46 |
  | strong third: within ±10%, Spearman (picker 65.7%, 0.66) | 80.6%, 0.72 | 83.6%, 0.81 |
  | weak third: within ±10% (picker 21.6%) | 19.4% | 23.9% |
  | peak height AUC, all wide draws; strong third | 0.763 [0.732, 0.797]; 0.910 [0.884, 0.934] | 0.777 [0.747, 0.813]; 0.920 [0.896, 0.944] |
  Double lags 8%, half lags 3–4%. On the weak third the error is worse than the prior's (log2 MAE +0.358 [+0.236,
  +0.487] plain, +0.277 [+0.160, +0.355] minus the mean): where the echo is faint the pick lands far off. Over
  40–1,500 ms (secondary) 47.3% and 49.8%, the plain arm's error there worse than the picker's (+0.153 [+0.061,
  +0.255]). The arm does not stop. *Step 2,* E0's
  84 X-LANCE stems (one chord DI): the plain pick hits the set time on 0 of 12 stems in every delay set (300 ms and
  500 ms at mix 0.40, 500 ms at 0.15); delay and S stems alike pick 60.8–84.9 ms, the chord's own peaks just above
  the 40 ms floor; not *clearly*. Descriptive, the subtraction arm (its offs hold these S stems): 2 of 12 at 300 ms
  (300.1, 299.8 ms), 0 at 500 ms. *Positive control,* the renders without backing: only crunch's 300 ms render
  hits (299.9 ms); the other three mix-0.40 renders, the mix-0.15 ones and both S pick 72.8 ms.
- **Reading.** On the clean targets the cepstrum reads delay time, clearly better than the picker on hits and
  error, and its peak height tells delay on from off better than any reader so far (0.92 on the strong third,
  against E1a's learned target reader's 0.80). Subtracting the training songs' delay-off mean helps (it removes
  the guitar's own cepstral peaks shared across songs). By the declared rule step 2 is not clearly, and since the
  control hit one of its four mix-0.40 renders, step 2 formally counts, which by the declared branch would extend
  F50's verdict and propose the masking renders. But the control shows the method failing on E0's chord DI without
  any backing (1 of 4; the DI's 72.8 ms peak wins), so step 2 mostly tested the DI. In the one cell where the
  control reads (crunch, 300 ms) the stems hit 0 of 6 (the subtraction arm 1 of 6): weak evidence in F50's
  direction, from one DI and one preset.
  *Amendment (post hoc, reviewed before scoring):* E1e, the stem test on the D_CC wide draws themselves, where the
  cepstrum reads on the targets, comes before the masking renders; it costs zero renders and about 75 minutes of
  X-LANCE.
- **Caveats.** Thirds and arms chosen as declared; the subtraction arm's gain is in-sample in its choice (both
  arms were declared, the primary for E1e is picked after this result). Mono 10 s targets; the wide draws only.
  The E0 control is two renders per kind.
- **References.** `~/ndsp-presets/learn/trusted-data/judge-v5/fx-reader/e1d/score.json` (the run's own output kept
  as `score-as-run.json`; the refactored scorer reproduces it exactly); code `learn/fx_reader.py` (`cepstrum`,
  `cep_pick`, `cep_readouts`, `cmd_e1d`); research `docs/research/blind-reverb-delay-2026-11.md`; ledger
  `phase_fx_reader_e1d`, `phase_fx_reader_e1d_outcome`.

### F52. On the rebuilt, re-separated stems the cepstrum hits the delay time more often than the picker (22% against 14%) but its error stays worse than a guess's, and a confident peak does not help: delay time does not read on the stem (phase_fx_reader E1e)
- **Result.** `learn/fx_reader.py e1e-build`, `e1e-score` (zero renders; 770 wide draws rebuilt by D_CC's recipe,
  every mix's stored features reproduced exactly, the re-separated stems' features within 0.01 of the stored ones;
  about 60 minutes of X-LANCE). Wide delay-ons (402; the wide median 7.2% within ±10%, log2 MAE the reference):
  | wide delay-ons | stem, minus the delay-off mean (primary) | stem, plain | mix, minus the mean | mix, plain |
  |---|---|---|---|---|
  | within ±10% (picker) | 22.1% (13.7%) | 19.4% | 12.7% (6.7%) | 16.4% |
  | minus the picker [90%] | +0.085 [+0.029, +0.157] | +0.057 [+0.018, +0.115] | +0.060 [+0.019, +0.118] | +0.097 [+0.026, +0.146] |
  | log2 MAE minus the prior | +0.309 [+0.210, +0.383] | +0.335 [+0.246, +0.383] | +0.304 [+0.235, +0.364] | +0.314 [+0.215, +0.432] |
  | Spearman | 0.04 | 0.04 | 0.18 | 0.07 |
  | strong third: within ±10% (prior 4.5%) | 28.4% | 26.9% | 18.7% | 24.6% |
  | peak-height AUC, strong third (E1a's reader 0.614) | 0.589 [0.509, 0.635] | 0.574 | 0.548 | 0.583 |
  The weak third is not shown above the prior (primary 13.4% against 10.4%, +0.030 [−0.010, +0.055]); on the strong
  third the primary arm's error against the prior is undecided (+0.200 [−0.019, +0.310]). *Audit (exploratory, post hoc;
  `e1e/audit/confidence.py`):* by quartile of the stem's peak height the hits run 8%, 20%, 34%, 27%, while 21% of
  the delay-offs reach the top quartile's height; the mix 14%, 12%, 9%, 16%.
- **Reading.** By the declared rule time does not read on the stem (hits beat the picker, +0.085, but the error is
  worse than the prior's, +0.309) nor on the mix: on these stems the cepstrum is right about one time in five and
  far off otherwise, and its peak height does not pick out the hits (at most 34% in any quartile; 21% of the offs
  reach the top quartile; post hoc). Its on/off height (0.59) is not better than E1a's learned reader (0.614, the
  same mask, unpaired). The clean targets read (57%, F51), so
  the loss is the backing's (the declared branch: masking). Separation adds a few hits on the primary arm (stem minus mix +0.095 [+0.067,
  +0.141], paired, band bootstrap); on the plain arm it is undecided (+0.030 [−0.010, +0.128]; the review's
  `e1e/audit/sep.py`). Delay time joins reverb decay and the knobs: no blind reading
  from the separated stem yet, by a learned reader, a lag picker or the cepstrum.
- **What it changes.** By the declared branch the masking renders (E1b with a backing split, stem and mix audio
  stored) are proposed, not run: they cost renders and separation, and after F49–F52 the effects route's best
  result on the stem is on/off at about 0.6. Effects follow song research in the product meanwhile (as since F47).
  The choice between them and the main line (the approved real-amp recordings and a fresh real-song test) is the
  user's.
- **Caveats.** The wide draws only; mono 10 s mixes; one separator; the primary arm chosen after F51; the audit's
  quartiles are post hoc.
- **References.** `~/ndsp-presets/learn/trusted-data/judge-v5/fx-reader/e1e/score.json`, `build-rows.jsonl`,
  `audit/confidence.py` and `.json`, audio `e1e/audio/` (770 mixes and stems, kept for later tests); code
  `learn/fx_reader.py`; ledger `phase_fx_reader_e1e`, `phase_fx_reader_e1e_outcome`.
- *Results review (2026-11-03, independent):* approved with four required changes, all made: the weak third not
  shown above the prior; the gate claim narrowed to what the audit measured; separation's share with its paired
  intervals; the build time. Also adopted: the strong third's undecided error, "not better" for the AUC.


### F53. The ear so far: real room above S, and no current model heard on the song's own performance (zero renders, descriptive)
- **Why now.** The user (2026-11-04) doubted "level with S": the score is imperfect, listening heard generated presets
  much closer to the original than S, and a similar score does not mean the same sound. The two real-song pages of
  2026-11-02 had no write-up; this is it, with record match beside them. Rankings from the stored answers and keys.
- **Own performance, true DI (record match, 2026-10-19, 5 parts):** the best-search ceiling C above S on 5 of 5, the
  closest preset heard "very close" on 3 and "somewhat" on 2 (S itself was not rated, and C is a search fitted to the
  judge); the older models H and D above S on 4 of 5 each. Mean
  ranks C 1.2, H 2.4, D 2.8, S 3.6. There the ear broadly followed the judge (Spearman mean 0.8; 0.6 without C).
- **Stand-in guitar, the current models (`listening/real-song-check` and `-2`, 2026-11-02, blind, 4 songs):**

  | Song | Page 1, chord DI | Page 2, single-note DI |
  |---|---|---|
  | Autumn Leaves | D_fix > S > W | W > D_fix > S > FT |
  | Hotel California | W > D_fix > S | W > FT > S > D_fix |
  | Still Got The Blues | D_fix > W > S | FT > S > D_fix > W |
  | Cut It Out | W > D_fix > S (unsure) | S > W > D_fix > FT |

  Some model sits above S on 7 of 8 rankings (5.7 expected by chance; 7 or more 27% of the time). Above S: D_fix 5 of 8, W 5 of 8, FT 2 of 4. S's mean
  rank 2.75 of 3 on page 1 (chance 2; that high 6% of the time, on the page with the larger confound), 2.25 of 4 on
  page 2 (chance 2.5). W, which the score puts clearly below S on
  V-real (+0.228), is first on 4 of the 8.
- **Reading.** The user's point stands: "level with S" is the score's, and F44–F47 show the score and the ear part
  ways. The ear has put presets above S (record match), though nothing there sizes the gap. On the current models it
  is not yet shown either way: pooled, the stand-in rankings are near what chance gives, 4 songs twice are not 8
  independent answers, and which model leads changes from song to song. Nothing here shows a current model level with S
  by ear, or above it. L0 is the test.
- **Caveats.** One listener. Page 1 played chords against lead songs, and on its first 3 items every preset sounded
  distorted to the user on songs heard as clean (the user's notes; item 3's reference also held a backing guitar); both pages are tone-only, the notes differ. Two
  files are karaoke-style re-recordings. On page 2 items 1 and 2 share one S render. Neither page key stores a score
  per item, so the earlier remark that the ranks did not follow the judge compares with aggregates only. Record
  match's H and D are older models, not the current ones; its C is a search through the true DI, not a product arm.
- **References.** `~/ndsp-presets/listening/real-song-check{,-2}/private/`, `listening/record-match-1/private/score.json`,
  [record match's results](record-match-listening-results.md).

### F54. L0, the first ear read of the current models on songs' own performances: W heard below S; FT and D_fix not known by ear, and heard far above S on two clean parts where the score barely moves (those two picked after the answers) (phase_ear_vreal, 80 renders, one listener)
- **Run.** As declared; all 40 renders' hashes equal the stored ones, the page's build `490e19bda8cb`. All 12 items answered,
  10 first hearings in 7 bands make the rows; one (Wickerman ElecGtr1) marked unsure; no notes.

  | Candidate | Mean rank | Mean closeness | First / last | Rank against S | Closeness against S | Above S by rank | Rated above S | Equal rating | The score, these directions |
  |---|---|---|---|---|---|---|---|---|---|
  | S | 1.93 | 1.36 | 4 / 1 | | | | | | |
  | FT | 2.00 | 1.57 | 3 / 0 | −0.07 [−0.86, +0.71] | +0.21 [−0.29, +0.79] | 5 of 10, 4 of 7 bands | 2 of 10, 2 bands | 6 of 10 | −0.080 [−0.172, +0.001] |
  | D_fix | 2.36 | 1.36 | 2 / 1 | −0.43 [−1.00, +0.21] | 0.00 [−0.50, +0.50] | 3 of 10, 2 of 7 bands | 2 of 10, 2 bands | 5 of 10 | −0.052 [−0.110, +0.001] |
  | W | 3.71 | 0.07 | 1 / 8 | −1.79 [−2.57, −0.79] | −1.29 [−1.93, −0.64] | 2 of 10, 1 of 7 bands | 1 of 10, 1 band | 2 of 10 | −0.359 [−0.490, −0.237] |

  Band-weighted, 90% band-clustered intervals. Against S, plus is above S; the score's row is ln(d_S / d_model), so plus is
  closer. Closeness: very 3, close 2, somewhat 1, not close 0.
- **By the declared map.** W: "heard below S on these songs, one listener", on rank and closeness, and the score agrees.
  W's effects, on in 8 of the 10, cannot be all of it: it is last and "not close" on both parts with them off, though
  that is two parts. FT and D_fix: the rank intervals reach zero, so not known by ear, not level. FT's ratings are equal
  to S's on 6 of 10, which the map reads as the ear's own level on most parts; its other four are +3, +3, −1, −1, and one
  of the six (femme ElecGtr5) broke on its repeat, to FT above S, so level is not the whole of it. D_fix's are equal on 5
  of 10, half, not most. The chance simulation holds: a clear row is a lead for L2, not a verdict.
- **Clean and crunch (declared beside; clean is 2 bands, so no interval).** Rank / closeness:

  | Class | Parts | S | FT | D_fix | W |
  |---|---|---|---|---|---|
  | Clean | 4 (2 bands) | 2.75 / 0.25 | 1.75 / 1.75 | 2.50 / 1.25 | 3.00 / 0.25 |
  | Crunch | 6 (5 bands) | 1.60 / 1.80 | 2.10 / 1.50 | 2.30 / 1.40 | 4.00 / 0.00 |

  FT is above S on 3 of 4 clean parts and 2 of 6 crunch, D_fix on 2 of 4 and 1 of 6, W on 2 of 4 and 0 of 6. S is "not
  close" on 3 of 4 clean parts and on no crunch part; FT and D_fix gain in rating only on the two sw50r clean parts, and
  neither is rated above S on any crunch part. On crunch (post hoc, 5 bands) the rank gaps lean below S: FT −0.50
  [−1.40, +0.50], D_fix −0.70 [−1.20, +0.10]; all these intervals reach zero.
- **Class, amp and S's setting cannot be pulled apart here (post hoc).** S is one setting per class and amp, so the 10 parts
  hold 5 S settings: clean sw50r 2 parts, clean ac20 2, crunch ac20 4, crunch sw50r 1, crunch pr12 1. By amp the split is
  sharper than by class: FT is above S on 4 of 4 parts off the ac20 and 1 of 6 on it (D_fix 2 of 4, 1 of 6), and S's mean
  rank is 3.00 on the sw50r and 1.50 on the ac20. Within clean, the amp and the held half split the result exactly: the
  gain is on the two sw50r parts (held A), and on the two ac20 parts (held B) FT's ratings equal S's. So the row near zero
  is not one result, but which of class, amp or S's setting moves it is not known.
- **Where the score misses it (picked after the answers).** On It Was My Fault ElecGtr3 and colour-me-red ElecGtr02,
  both clean and on the sw50r, S is "not close", FT "very close" on both, D_fix "very close" and "close". The score
  sits within 8% of S on all four pairs, and on three of them it puts S closer: FT −0.069 and +0.055, D_fix −0.074 and
  −0.063. colour-me-red's repeat came back with the same ranks and ratings. For one listener that is the user's point on a
  song's own performance: a similar score did not mean a similar sound. Two limits. Both parts play the same S setting,
  and FT's amp knobs on them are nearly one setting (Volume 0.356 and 0.360, Treble 0.744 and 0.789, Mid 0.423 and 0.401,
  Bass 0.302 and 0.263), so the two are not independent: one S setting on both and FT's amp side nearly the same, though its
  mics differ and its curve against S differs between them (correlation 0.61, 2.7 dB rms, post hoc, from the stored clips).
  They show this S setting is far off on these parts; they do not show that FT read the song. And colour-me-red ElecGtr02 is D_fix's only
  effects-on part (reverb, delay, compressor); F44 already has reverb heard above its score, so that "close" and its −0.063
  are partly a known mismatch. The third clean part with S "not close" (It Was My Fault ElecGtr1, ac20) does not repeat it:
  only W rises, to "somewhat", with its reverb on.
- **The ear against the score.** Spearman +0.50 [+0.31, +0.67], clear of zero, so L1's declared check is not triggered.
  Audit (post hoc): W carries that, and the rule could hardly fire once W was heard last. With W's rank held and the other three
  shuffled the Spearman stays near it (mean +0.46, 5–95% +0.27 to +0.64). Without W it is +0.04 [−0.29, +0.39], what shuffled
  answers give (0.47 reach it). On the same side of S: W 8 of 10, D_fix 6, FT 5. So among S, FT and D_fix agreement is not
  shown, and the page is wide: an ear truly following the score at +0.5 lands this low on about 1.5% of pages, at +0.27 on
  about 16% (the review's simulation), so strong agreement is unlikely and weak agreement stays open. The large gaps may
  agree where the small ones show no agreement: same side on 3 of 4 pairs at gaps of 10% or more (only 4 pairs), 8 of 16
  below.
  Record match's 0.6 without C (F53) came through the true DI on older models, so it is not comparable. L1's labels ask
  something else of J0, a search rather than a ranking of near answers, and record match's search was heard above S on 5 of
  5; that was through the true DI.
- **How close, plainly.** The best rating on a part is "very close" on 3, "close" on 2 and "somewhat" on 5. The measure DI
  limits this (F20).
- **Repeats.** Rank Spearman 1.0 and 0.8, the same top both times. Ratings match on 6 of 8; on femme ElecGtr5 S moved from
  "very" to "somewhat" and FT from "very" to "close". Ranks held better than ratings, on two repeats.
- **Audit.** The rows re-derived from the raw export and the key match the scorer's to three decimals. Without the
  unsure item: FT 0.00 [−0.79, +0.71], D_fix −0.50 [−1.14, +0.14], W unchanged. First place by letter over the 12 items: A
  4, B 3, C 2, D 3, no leaning. S is first on 4 of 10 (2.5 by chance), and some model is above S on 6 of 10 (7.5 by
  chance), so pooled, the models do not beat chance here; the rated gain sits on the two parts named above. The group
  peak cut is 0.0 on all ten parts, so level matching took nothing from any clip.
- **L2's size, as L0 asked.** The spread of the band rank gaps (standard deviation FT 1.40, D_fix 1.02, from 7 values, so
  rough) puts a 90% half-width of 0.75 of a rank at about 5 to 10 bands and of 0.5 at about 12 to 22 (about 7 to 12 and 14 to
  24 with a t-based figure). Clean has to be there in its own right: two bands here cannot size it. L2 should vary S's
  setting and the amp too, not only the class.
- **What it changes.** The main line goes on. Nothing here picks a model: FT's lead over D_fix and the class and amp splits
  are this fourth read's and selection-contaminated, leads for L2. L1 now has two reasons to be shaped by this: agreement
  is not shown among the near candidates (a small blind check of search labels is cheap, and the first batch's labels are
  needed anyway), and crunch leans below S by ear.
- **Caveats.** As declared: one listener, 10 parts, a short window, the measure DI (F20 caps even the truth), the amp chosen
  by S's closeness by the score (which leans toward S; the ear put S "not close" on the two sw50r clean parts chosen that way),
  W recognisable across items, and these records heard before, S itself on two of them (Signs ElecGtr3, get-out-of-bed
  ElecGtr2): both crunch on the ac20, S ranked 1st and 2nd there, so this bears on the crunch lean. Added by the audit: the band
  intervals treat S as independent across bands, though bands share its setting; and the measure DI moves crunch parts
  further than clean (crunch +15.6, +12.1, +10.6, +3.8, +1.9, −4.4 dB, mean +6.6; clean +6.6, 0.0, −1.0, −2.4, mean +0.8), so
  three of the six crunch parts are pushed 10 dB or more past their recorded DI level. It Was My Fault ElecGtr3 moved 0.0 dB, so that hit is not a level
  artefact; colour-me-red ElecGtr02 moved +6.6.
- **References.** `~/ndsp-presets/learn/trusted-data/pipeline-fix/ear-vreal/{key,score}.json`, ledger
  `phase_ear_vreal_outcome`. Results review: 14 required changes, all made.

### F55. Masking FT's unsearched heads and its amp head: on GOAT the reading of tone rises and the score improves; on BKS the score goes the other way; the learning curve is undecided (N1, N3, phase_night2, phase_n3; 2,680 read renders, no V-real, no ear)
- **What changed.** FT's real rows taught mostly S's constants on unsearched controls. N1 took those heads and the amp head out of the real rows' loss and held every control outside the search at S at the readout; E fell from about 190 to about 60 (48–104). The held knob loss's argmin, not acted on: 42–116, median 64 (knob_joint, unsmoothed; E's median 59). The reads below are the declared ones, run by the review session's `reads_v3.py` (sha256 a04785f3a4838ae2) and the stored reports.
- **The reading, knob units, held GOAT items** (r demeaned within fold, amp, class and head, one value per recording; 90% item intervals):

  | | Drive | Tone | Cab |
  |---|---|---|---|
  | FTm | +0.082 [+0.019, +0.144] | +0.258 [+0.174, +0.338] | +0.218 [+0.155, +0.284] |
  | FT | +0.088 [+0.016, +0.158] | +0.121 [+0.025, +0.220] | +0.191 [+0.126, +0.263] |
  | W | +0.096 [+0.030, +0.161] | +0.222 [+0.140, +0.301] | −0.086 [−0.139, −0.027] |
  | FTm − FT | −0.007 [−0.050, +0.039] | +0.137 [+0.065, +0.207] | +0.026 [−0.020, +0.068] |
  | FTm − W | −0.014 [−0.090, +0.059] | +0.036 [−0.060, +0.127] | +0.303 [+0.219, +0.390] |

  Own output against another recording's: FTm −0.294 [−0.377, −0.210], FT −0.185 [−0.236, −0.134], W −0.061 [−0.125, +0.004] (no paired interval declared). Without range-limit labels FTm's tone is +0.176, FT's +0.045 and W's +0.232 (no paired interval). So FTm has FT's cab with a tone read not shown below W's. BKS decides nothing here (four blocks from two songs, and its cab sits at a no-audio table's level). BKS r, exact p: FTm drive +0.306 (0.025), tone +0.203 (0.072), cab +0.562 (0.0009); FT +0.149, +0.215, +0.510; no-audio table +0.014, −0.197, +0.507. Head-standardised GOAT FTm +0.139, +0.272, +0.149.
- **By the score, on read 2's units** (held half; minus is closer; BKS by DI, GOAT by item):

  | Row | BKS (8 DIs) | GOAT (130 items) |
  |---|---|---|
  | FTh − FT, the hold alone | +0.015 [+0.002, +0.029] | +0.002 [−0.008, +0.012] |
  | FTm − FTh, the mask alone | +0.039 [+0.014, +0.063] | −0.023 [−0.036, −0.011] |
  | FTm − FT | +0.054 [+0.018, +0.090] | −0.021 [−0.037, −0.005] |
  | FTm − S | −0.123 [−0.205, −0.041] | −0.094 [−0.116, −0.072] |
  | FT − S | −0.177 [−0.256, −0.098] | −0.073 [−0.094, −0.052] |
  | FTm − centre (Rcs2; RcGk) | +0.035 [−0.022, +0.093] | −0.010 [−0.030, +0.010] |

  By fold: GOAT FTm − FT −0.016 [−0.035, +0.003], 4 of 4 folds, reaching zero; FTm − FTh −0.017 [−0.029, −0.005]. BKS FTm − FT +0.050 [−0.019, +0.119], FTm − FTh +0.038 [−0.008, +0.084], 3 of 4 folds, both reaching zero. FTm − FT counts: GOAT 68 of 130 items, median −0.004, so the mean rests on a few large items; BKS 1 of 8 DIs, 13 of 40 units. GOAT's S rows have 2 missing.

  The two sets disagree on the mask. GOAT's held items are new playing on mostly new chains, but capture renders, not real rigs, and 132 of its 172 DIs are one player. BKS is real amps, but shares songs and rig letters with training, its playing sits in W's rows, and FT was chosen on this row (read 2). FT's longer tuning may be memory there, though nothing here shows it, and the mask and the epoch count are not separated. On both sets FTm and FT are closer than S by the score. Against its centre FTm is undecided on both sets, by the score.
- **N3, the learning curve (held GOAT).** FTm at 25%, 50% and 100% of records: drive +0.080, +0.092, +0.082; tone +0.203, +0.242, +0.258; cab +0.195, +0.224, +0.218; labels shuffled at 100%: drive +0.025, tone +0.096, cab +0.017. FTm − FTm25: +0.001 [−0.040, +0.039], +0.055 [−0.015, +0.123], +0.023 [−0.014, +0.061]. FTm − FTm50: −0.010 [−0.041, +0.023], +0.016 [−0.041, +0.072], −0.006 [−0.034, +0.023]. FTm − shuffled clears zero above on all three. By the declared rule no group rises: undecided, and that says nothing against more rows. Point estimates: drive and cab show no trend, tone rises a little at each step; the upper ends (+0.039, +0.123, +0.061) allow a rise in any group. The reading is above the shuffle, and 25% of records (about 150 rows, cycled copies: about 85 distinct units, about 40 of them GOAT's) already carries most of the point estimate. BKS beside, deciding nothing, 25/50/100%: drive +0.377, +0.338, +0.306; tone +0.407, +0.247, +0.203; cab +0.505, +0.530, +0.562.
- **What it changes.** On held GOAT capture renders FTm is a lead for L2: tone reads better than FT's, drive and cab level, and by the score it is closer by item, with the fold interval reaching zero. On BKS it gives back about the lead that carried FT (read 2's −0.055). This moves no base. N3 says nothing for or against more rows; the captures' labels are in hand either way. Sound on a real song is N4's page, by ear.
- **Caveats.** Knob reads are agreement with search labels, not sound. Masked heads stay W's and are held at S at the readout, so nothing here tests those controls. One training recipe, both seeds pooled, the paired GOAT rows uncorrected (six knob, six score, N3's nine). FTm was chosen on the reads N3 repeats. Nothing here went through a stem.
- **References.** `learn/reads_v3.py` (verbatim, sha256 a04785f3a4838ae2), `night2/reads-v3-ftm.json`, `night2/reads-v3-n3.json`, `real/report-night2.json`, `goat/report-night2.json`, `night2/report.json`, ledger `phase_night2`, `phase_n1_first_read`, `phase_n1_score_read`, `phase_n3`, `phase_n3_outcome`; the ML review's document. Results review: 13 required changes, all made.

### F56. N4, masked FT by ear on L0's parts: not known by ear, level with FT on closeness, behind S by the score; S and FT repeat L0's split on the same clips (phase_n4, 40 renders, one listener)
- **What was heard.** 12 of 12 answered, all marked sure, 10 first hearings, 7 bands, build d1197bc57c3f. Band-weighted mean rank / closeness (0 far, 1 somewhat, 2 close, 3 very close): S 1.86/0.71, FT 1.93/0.71, FTm 2.21/0.64.

  | Row | Above, rank share | Rank gap | Closeness gap | Score, ln(d_b / d_a) |
  |---|---|---|---|---|
  | FTm over S | 4 of 10, 0.40 [0.11, 0.69] | −0.36 [−1.29, +0.64] | −0.07 [−0.71, +0.57] | −0.107 [−0.198, −0.021] |
  | FTm over FT | 4 of 10, 0.40 [0.10, 0.75] | −0.29 [−1.00, +0.43] | −0.07 [−0.36, +0.14] | −0.051 [−0.120, +0.010] |
  | FT over S | 5 of 10, 0.50 [0.20, 0.78] | −0.07 [−0.79, +0.64] | 0.00 [−0.57, +0.57] | −0.056 [−0.144, +0.005] |

  Share and score are pooled over parts, clustered by band; the gaps are band-weighted. Above zero favours the first candidate, so the score's sign here is the reverse of F55's table. FTm and FT get equal ratings on 8 of 10 parts, though 5 of those 8 are both far, a floor, and FT ranks above FTm on 4 of the 5; their clips correlate above 0.96 on 6 of 10 parts.

  Other weighting: closeness pooled FTm over S +0.10 [−0.71, +0.82], FTm over FT 0.00 [−0.25, +0.20], FT over S +0.10 [−0.56, +0.69]; score band-weighted −0.117 [−0.200, −0.038], −0.037 [−0.097, +0.014], −0.080 [−0.173, +0.001], the last with F54's mean on the same clips. No row changes its reading. FTm over S leaving one cell out: ac20/clean 0.38 [0.11, 0.71], ac20/crunch 0.67 [0.33, 1.00], pr12/crunch 0.33 [0.00, 0.64], sw50r/clean 0.25 [0.00, 0.57], sw50r/crunch 0.44 [0.12, 0.75]; all reach one half.
- **By the declared map.** All three rows reach one half: not known by ear, and FTm picks nothing. A true 75% clears about half the time on this page, so this does not rule the model out, though the primary row's upper end sits below 0.75 on the declared bootstrap (0.69; pooled cluster t 0.76) and its point estimate below one half. FTm's better reading of tone (F55) is not shown by ear against FT on these parts (0.40 [0.10, 0.75]).
- **Where the answers split (counts and means, no declared intervals).**

  | Parts | S | FT | FTm | FT above S | FTm above S |
  |---|---|---|---|---|---|
  | Clean (4 parts, 2 bands) | 2.50/0.00 | 1.75/1.00 | 1.75/1.25 | 3 of 4 | 3 of 4 |
  | Crunch (6, 5) | 1.60/1.00 | 2.00/0.60 | 2.40/0.40 | 2 of 6 | 1 of 6 |
  | ac20 (6, 5) | 1.40/0.60 | 2.20/0.00 | 2.40/0.20 | 1 of 6 | 1 of 6 |
  | Off the ac20 (4, 4) | 2.75/0.50 | 1.50/1.75 | 1.75/1.50 | 4 of 4 | 3 of 4 |

  Rank / closeness, band-weighted within each row. Class, amp and S's setting stay confounded. L0 chose every part's amp by S's closeness by the score, off the ac20 as on it, so the whole page leans toward S; that does not explain why S leads on the ac20 and trails off it. Crunch rank gaps (5 bands, t) FTm −0.80 [−2.37, +0.77], FT −0.40 [−1.68, +0.88].
- **The same clips twice.** S's and FT's clips are L0's stored renders. FT against S keeps its order on 8 of 10 parts between the pages, the closeness gaps correlate 0.88, and the amp split repeats in count (4 of 4 and 1 of 6; the one ac20 part differs). Repeats on this page: same top on 2 of 2, same order on 1. That is the listener's consistency, not a second sample: the parts, clips and listener are the same. Ratings do not carry across pages: the same clips scored S 1.36 and FT 1.57 on L0, with W on the page, and 0.71 each here.
- **Absolute closeness.** The best rating on a part was close on 3, somewhat on 6, far on 1, and very close on none. None of the three was rated very close on this page, but ratings move between pages: on L0 the same clips got very close on 3 of these parts (FT on femme ElecGtr5, colour-me-red ElecGtr02 and It Was My Fault ElecGtr3, S on femme ElecGtr5).
- **The score.** FTm is further than S on 8 of 10 parts (ln(d_FTm/d_S) median +0.066, mean without the largest part +0.070), so one part does not carry the row. On F55's development sets it goes the other way (FTm − S −0.123 and −0.094; FT − S −0.177 and −0.073), so those gains by the score did not reach these parts. The causes are not separated: amp chosen by S, other guitars in the mix, rigs outside training, the measure DI. Ear-score Spearman, FTm against S, one closeness gap and one ln(d_S/d_FTm) a part: +0.57 [−0.02, +0.93], reaching zero. On clean parts the ear moves a long way (S 0.00 to FTm 1.25) while the score stays level (ln(d_FTm/d_S) mean −0.004, FT's −0.013), as in F54.
- **The review's first step, beside (zero renders).** F55's and N5b's BKS and fold rows are t already; GOAT's item rows use the normal 1.6449 at df 129, within 0.0002 of t. Two rows change in the third place, FTm − FT −0.037 to −0.038 and FT − S −0.094 to −0.095, and no reading moves. F54 on t keeps every conclusion (W − S rank −1.79 [−2.90, −0.67]; FT and D_fix reach zero). N4's band-weighted rows on t: FTm over S rank −0.36 [−1.61, +0.89], closeness −0.07 [−0.93, +0.79], score −0.12 [−0.22, −0.02]. The pooled row on t (`rescore.clustered`) reaches zero: −0.107 [−0.220, +0.006], band sign flip p 0.11. So "behind S by the score" holds band-weighted, on 6 of 7 bands and 8 of 10 parts, not on every interval. `tonal` is not in this plan's judged rows, because `knob_ceiling.judge` keeps `distance` alone. The older factory-menu stores (`direc/rescore`, `songs-check`, `confirm`) keep it but hold no model answers, so for models that half of the step needs re-judged audio. Three more bootstrap sites were not redone: `direct_stems.py:268`, `pipeline_fix.py:4391`, `fx_reader.py:632`.
- **What it changes.** No base moves, and the answers do not choose between FT and FTm. What can separate class from amp is a crossed design: the capture label check's items, and L2 if it randomises the amp as the ML review proposes. S is one setting per amp and class, so S's setting stays tied to the cell unless L2 varies it (F54).
- **Caveats.** One listener, 10 parts, all heard before. L0's amp choice leans FTm − S toward S. FT's clips carry no hold, so FTm − FT mixes the hold and the mask. At least V-real's fifth read. Nothing here is a verdict on a real song in general.
- **References.** `learn/ear_ftm.py`, `ear-ftm/key.json`, `ear-ftm/score.json`, ledger `phase_n4`, `phase_n4_outcome`.

### F57. L1a's label check by ear: heard closer than S on closeness, the rank share reaches one half, neither of F56's splits shows for the labels (phase_l1a, 72 renders, one listener)
- **What was heard.** 14 items, build 04cf993bee72, 12 answered, all marked sure. Two came back unranked, "Too distorted, out of scope": i1, so 11 of 12 first hearings, and i14, the repeat of i4, which had been ranked on its first hearing. 11 parts, 11 creators, one part each. Mean rank / closeness (0 far, 1 somewhat, 2 close, 3 very close): S 2.36/0.64, placebo 2.09/1.36, label 1.55/2.09.

  | Row | Above, rank share | Closeness gap | Score, ln(d_b / d_a) |
  |---|---|---|---|
  | Label over S | 8 of 11, 0.73 [0.45, 0.91] | +1.45 [+0.91, +2.00] | +0.387 [+0.243, +0.550] |
  | Label over placebo | 8 of 11, 0.73 [0.55, 0.91] | +0.73 [+0.18, +1.27] | +0.291 [+0.210, +0.370] |
  | Placebo over S | 7 of 11, 0.64 [0.36, 0.82] | +0.73 [+0.09, +1.36] | +0.096 [−0.048, +0.250] |

  The declared creator bootstrap. Above zero favours the first candidate. On t, closeness [+0.79, +2.12], [+0.08, +1.38], [−0.01, +1.46], and score [+0.208, +0.567], [+0.199, +0.383], [−0.078, +0.270]: only placebo over S on closeness changes its reading, and it then reaches zero. Ratings (very close, close, somewhat, far): label 4, 4, 3, 0; placebo 1, 4, 4, 2; S 0, 2, 3, 6. Label against S on closeness: 9 parts above, 1 level, 1 below. By the score the label is closer than S on 11 of 11, and on i1, and closer than the placebo on 10 of 11. Leaving one cell out, the primary share is 0.67 to 0.78 with lower ends 0.44 to 0.56, the same edge as below.
- **The two rows at 8 of 11 are one read (post hoc).** With one part per creator this bootstrap is a binomial. At 8 of 11, P(X ≤ 5) is 0.0512, so the exact lower end is 0.45, and 20,000 draws fall either side of it by seed: over 200 other seeds the label-over-S row reads clear on 21% and the label-over-placebo row on 24%. The stored "clear above" on label over placebo is that noise, so this record does not call it clear: both rows reach one half.
- **By the declared map.** `report` stores `branch: null`, since a file with a first hearing missing decides nothing, and rightly: the map was declared on 12 parts. Either answer on i1 leaves the primary reaching one half (8 of 12 [0.42, 0.92]; 9 of 12 [0.50, 0.92], not above), so the rank does not tell: not known by ear, and underpowered is not failed. The map then names the closeness row and its ties as the user's evidence on whether to go on, and that row is clear of zero on either interval. It is not clear below, so no declared stop applies. As simulated beforehand, a true 75% clears on about 40 to 57% of pages, and at 12 creators 9 of 12 clears on about none, so a clear rank row needed 10 of 12.
- **Item 8 contradicts itself.** Ranked S, placebo, label; rated label very close, placebo close, S somewhat: the exact reverse, on the only item where rank and ratings disagree. The answer stands as given, and the rows above use it. The listener, still blind to the letters, is asked to re-hear it; a correction is recorded only if the listener says it was a slip, as a post hoc row beside these. It does not move the declared reading: this one item was chosen for re-hearing and it can only move upward (with i4 out as well it would read 8 of 10 [0.60, 1.00], clear). Taken as a reversal, label over S and over the placebo each read 9 of 11, 0.82 [0.64, 1.00], clear above, and placebo over S 8 of 11, 0.73 [0.45, 0.91]. On 12 parts that is 9 of 12, reaching, or 10 of 12, clear, by i1, which the listener held out of scope.
- **Item 8's correction (2026-11-05, post hoc, the listener's own).** Asked to re-hear item 8, the letters not revealed to them, the listener answered: "the correct order is the closeness order B>C>A", that is label, placebo, S. The words give the order, not whether the clip was played again. The answer on file stays as given (`ear-check/answers.txt`), the rows above stay as they are, and the declared reading does not move. Beside them, on the corrected order: mean rank S 2.55, placebo 2.09, label 1.36; label over S 9 of 11, 0.82 [0.64, 1.00]; label over placebo 9 of 11, 0.82 [0.64, 1.00]; placebo over S 8 of 11, 0.73 [0.45, 0.91]. Over 200 other seeds both label rows clear one half on all, the exact lower end being 0.64, and placebo over S on 23%. No item keeps a rank against its ratings. Crunch reads 5 of 5 ranked and rated, the pr12 3 of 4. With i4 out as well, 8 of 10 [0.60, 1.00]. On 12 parts it is 9 or 10 of 12, by i1, which the listener held out of scope and which decides whether that row clears. This one item was picked for re-hearing and could only move up, so this is a side row, not a clear primary. Closeness and the score do not change. Files: `ear-check/item8-correction.json`, `ear-check/audit/item8.py`.
- **Fit or S off.** The placebo row is here to tell a fit to this capture from S simply being far off. Both show a little: another capture's label of the same amp and class is rated above S (+0.73, reaching zero on t), with 7 of 11 on the rank and the score reaching zero, and this capture's own label is rated above that again (+0.73), with the score clear. On closeness and the score, S being off (F54) does not explain all of it. On the rank row, the one the map reads, that is not known: it reaches one half, a lead for a real fit, no more.
- **Crossed by amp and class (counts and means, no declared intervals).** Mean rank / closeness, parts, label ranked above S:

  | Parts | S | Placebo | Label | Label above S |
  |---|---|---|---|---|
  | Clean (6) | 2.17/0.83 | 2.33/1.17 | 1.50/2.00 | 4 of 6 |
  | Crunch (5) | 2.60/0.40 | 1.80/1.60 | 1.60/2.20 | 4 of 5 |
  | ac20 (4) | 2.25/0.50 | 2.25/1.00 | 1.50/1.75 | 3 of 4 |
  | pr12 (4) | 2.00/0.75 | 2.00/1.50 | 2.00/2.25 | 2 of 4 |
  | sw50r (3) | 3.00/0.67 | 2.00/1.67 | 1.00/2.33 | 3 of 3 |

  F56's models led on clean and off the ac20 and S led on crunch and on the ac20. Here neither split shows for the labels: on crunch the label is ranked above S on 4 of 5 parts and rated above it on all 5, the fifth being item 8, and on the ac20 it is above S on 3 of 4 by both; on the pr12 it is ranked above on 2 of 4. With i4 out, crunch reads 3 of 4 ranked and 4 of 4 rated. This does not say what drove F56's splits, because three things differ: a search label fit through the true DI, not a model reading a song; captures, not songs' parts; and a forced amp for S, where those pages chose each part's amp by S's own distance, which favours S. So the most it supports is that on these captures the plugin and the search could get past S on crunch and on the ac20. The 3 parts below S are pr12 clean i5, pr12 crunch i8 (the item above) and ac20 clean i11.
- **The ear against the score.** Spearman of the closeness gap against ln(d_S/d_label), +0.49 [+0.08, +0.76] over the 11 parts, clear of zero on the declared bootstrap, though thinly: over 200 other seeds the lower end runs 0.00 to +0.08 (median +0.05), Fisher's z gives [−0.05, +0.81], and a permutation test gives one-sided p 0.06. F56's same row, FTm against S, read +0.57 [−0.02, +0.93], reaching zero, and F54's among S, FT and D_fix +0.04 [−0.29, +0.39]. The moves here are larger (+0.025 to +1.17), but F56's point estimate is higher, so this page does not show that larger moves are why the two agree. They agree here, on a wide interval. At the small end, i7's +0.025 still came with the top rank and one rating step.
- **Repeats.** i2 against i6: S last both times, label and placebo swap at the top, and all three ratings repeat exactly. i4 against i14: ranked, then called out of scope.
- **Out of scope.** i1 (`cap/ca2a7be3-377d-48e8-94b1-d3cb5f47b32e#sw50r`, a Vox AC10 crunch capture, `nonlinear_db` −1.98, an uncalibrated file, the group that plays 2.5 dB hotter, as are 7 of the 22 scope cards and 33 of the 150 units) and i4/i14 (`cap/npd1zhu905b#pr12`, a Fender '62 Deluxe, −1.49), both `uncertain` by `classify`, so neither reached the heavy page. They are 2 of the 6 crunch units heard, among the 15 most driven of 132. The measure does not separate what the ear put out: the heavy page kept +0.11 and +3.67 and dropped +0.54 and +4.27, and i7 at −2.18, the sw50r unit of the Mark V capture whose other two units went out as heavy, was ranked with no note. These are a handful of units. The deep review's nearest row, M1, is on render-against-render steps, failed its prediction on judge-ear and agreed on judge-v5, so it neither supports nor contradicts this. With i4 out as well, the primary reads 7 of 10 [0.50, 0.90], closeness +1.30 [+0.70, +1.80], score +0.392, Spearman +0.54; no reading changes. Both units leave the trusted set, and the amendment under L1a covers their neighbours.
- **Audit (post hoc).** Every row re-derived from the raw export and the key, with the letters read by hand, and the share rows by exact binomial tail. Files: `captures/ear-check.json`, `ear-check/answers.txt`, `ear-check/audit/`.
- **What it changes.** On closeness, this listener rates J0's label, given the true DI, closer to a real amp than S, by a margin that clears zero; on the declared rank row that is not known, and nothing here says the ear rejects the labels. That is the evidence the map gives the user on whether to go on, and the go-on is the user's. It says nothing of a model or a song: FTm reads songs and F56 could not tell it from S by ear, and no page has played a label and a model's answer on the same part, so how much of this a model can reach is the open question. Drive on crunch is the deep review's step 3.
- **Limits.** One listener, who heard each capture on the ear gate. 11 parts. The labels fit the measure DI and the Record plays the same performance, which no song gives us. The DIs are GOAT's, from two players on this page (6 and 5 parts). Ratings move between pages (F56), so these closeness means are read within this page, not against F54's or F56's. The rows on crunch and by amp are counts on 3 to 6 parts.

### F58. N7, the mix on its dominant cells: a true map leads a little, the stem maps do not, and at this margin the cells' band coverage caps it (phase_mask_read, zero renders)
- **What ran.** Features 1.6 min, the read 5.4 min, 4,189 examples, both controls passed: every-cell summary 0 from the stored (b), and (b) reproduced. Readable of 116 on FS5, and paired steps against the plain mix, heads reliably better / worse:

  | Input | Readable (knobs, switches) | Against (b) | Against its placebo |
  |---|---|---|---|
  | (b) plain mix | 30 (11, 18) | | |
  | (o) true map | 35 (14, 20) | 21 / 8, p 0.012 | 47 / 2 |
  | (g) stem map, 3 dB | 19 (7, 11) | 2 / 19 | 13 / 3 |
  | (t) stem map, top tenth | 19 (7, 11) | 0 / 29 | 9 / 7 |
  | (po) another's true map | 7 (2, 5) | 3 / 36 | |
  | (pg) another's stem map | 20 (8, 11) | 1 / 21 | |
  | (pt) another's top tenth | 13 (7, 5) | 1 / 30 | |
  | (xo) true map over another's mix | 9 (3, 6) | 1 / 38 | (po) 4 / 7 |

  (o) against (xo) 48 / 0. (o)|x against (b) 21 / 8, nothing left out; against (po) 44 / 2. Today's 25 heads: (b) 4, (o) 7, 7 / 2 against (b).
- **By the declared map:** rule 1 fails, no stem map is ahead of (b); rule 2 holds, "better map next" (stored `branch`). So a stem map does not earn a model step.
- **The audit (independent, own code; every count, pair and the branch reproduced; every row below post hoc on FS5, not a declared read).** The run has no error, and its figures replace the design's pre-run ones: true map 9.0% of FS5's cells, stem map 62.2%, stem precision 15.7%, recall 92.5%.
  - *At this margin the cells' band coverage caps it, not the map's quality.* Clean target at the mix's gain: all cells 91 readable, the cells under the backing 87, random cells at (o)'s density 71 (72 under the backing alone), another example's true map 43, (o)'s per-band counts with random frames 42, (o)'s own cells 38. Kept cells sit a median 1.0 dB from the clean target, so at this margin and with this reader (o) is already about what a perfect map gives. On the clean target, random cells beat (o)'s per-band layout 61 / 0, and band layout is all that differs between them. That layout beats (o)'s own frames only 13 / 4, and another example's map is level with (o)'s, 11 / 10. So selecting on dominance costs little; covering too few bands costs most, with 44 to 49% of the summary empty. The margin and the 20-cell floor set that coverage, and neither was varied. Against random mix cells at its density (o) is 29 / 3, its main support, since the placebos themselves lose to random cells.
  - *(o) is far from the target.* +5 on (b), inside the count's noise; it reads 8 of the 57 heads (a) reads and (b) does not, and loses 6 of (b)'s. Today's 25: 7 against (a)'s 24. It closes 18% of the switch AUC gap from (b) to (a) and 10% on mics. Knobs go from 11 to 14 readable and 12 of the 21 wins are knobs, but mean knob error is unchanged (+0.064 to +0.050 pts against the constant, where (a) is −2.15).
  - *The lead is moderate.* Better stays above worse on all 12 leave-one-section-out drops (14 / 6 to 22 / 8), but 3 of them lose the sign test, and each turns the branch to "denser read next". Clustered by band, 4 clusters, 12 / 5, p 0.072, not ahead. Without the 277 columns over half filled, 11 / 9. Near-equivalent inputs differ 12 / 12, so the practical noise floor is about twice the declared 6.
  - *The shape guard removed nothing.* (o)'s held-or-filled pattern alone, no audio values, reads 28, and the plain mix beside it 40 (22 / 4 against (b)), where (xo) reads 9. So (xo) understates the map's shape and the split between shape and values is unresolved, though (o) beats the pattern alone 15 / 1. Against the mix beside the pattern (o) is 8 / 12; leaving out the heads that reader also wins it is 16 / 8, p 0.076, which would be rule 3, and past the pattern alone 19 / 8, where rule 2 holds. That pattern comes from the target, so no product has it.
  - *The stem maps' fall is not a read of their cells.* Random cells fall as well: 18 readable at (g)'s density, 23 at a tenth, with almost no gaps. Against random cells (g) is 7 / 8 and (t) 1 / 16. So (g) is no better than random cells and (t) reliably worse, which also takes away g-pg's 13 / 3 as evidence. (t) is barely a ranking: the median gap at its cut is 0.00 dB, and on one band the separator mostly passes the mix through.
  - FS5's 12 sections are disjoint from training but come from 9 tracks, all also in training.
- **What it changes.** The declared reading moves the question to a better map, and this record does not declare one. Its upside here is about +5 heads, with mean knob error unchanged, and the stem's map is no better than random cells today. At this margin and 20-cell floor the dominant cells cover too few bands to read much; no other margin was tried, and a wider one, the obvious thing that could change coverage, would need its own declaration. So mask pooling on summaries is parked, not proposed. It says nothing of a trained model's reading or of sound, and the mix's 86-to-30 loss stands as the bottleneck.
- **Limits.** A linear probe on FS5's self-built mixes, one margin and one share. A trained model might use a map differently, which nothing here tests.
- **Data note.** A reviewer's structure check for the centre read opened stored BKS and panel answers, panel judge records and panel lag records for key names and counts, with no value printed, and listed capture search file names. Its script holds no V-real path. It was not a panel read and is not counted.
- Files: `tone-probe/mask.json`, `mask-features.json`, `tone-probe/audit/`. Log `logs/n7.log`.

### F59. N6, the models on a set they were not chosen on: they follow the labels, weakly, and the primary rests on one knob (phase_n6, zero plugin renders)
- **The scope page first (2026-11-05, build 1e4b42800e7e).** 22 cards, 13 kept and 9 too distorted, the export stored before any row. With the label page's two, 11 units leave: 121 trusted units, 48 captures, 19 creators, cells 17 to 22 (pr12 crunch smallest), 81% of the batch.
- **What ran.** FTm_k, FT_k and W on the 121 units, variant 0, control passed. r, one value per recording, demeaned within fold, amp, class and head; the declared creator bootstrap:

  | | Drive | Tone | Cab | Own − swap, total |
  |---|---|---|---|---|
  | All, FTm | +0.125 [+0.048, +0.195] | +0.209 [+0.099, +0.302] | +0.220 [+0.108, +0.282] | −0.222 [−0.340, −0.104] |
  | All, FT | +0.141 [+0.056, +0.227] | +0.164 [+0.052, +0.252] | +0.200 [+0.091, +0.267] | −0.180 [−0.258, −0.102] |
  | All, W | +0.068 [−0.023, +0.160] | +0.096 [+0.007, +0.176] | +0.062 [−0.044, +0.159] | −0.084 [−0.192, +0.024] |
  | Crunch (60), FTm | **+0.159 [+0.035, +0.272]** | +0.057 [−0.093, +0.219] | +0.162 [+0.032, +0.257] | −0.209 [−0.338, −0.079] |
  | Crunch, FT | +0.162 [+0.045, +0.273] | −0.028 [−0.171, +0.124] | +0.105 [−0.015, +0.207] | −0.190 [−0.297, −0.084] |
  | Crunch, W | +0.046 [−0.088, +0.168] | +0.075 [−0.064, +0.215] | −0.002 [−0.122, +0.129] | −0.076 |
  | Clean (61), FTm | +0.066 [−0.021, +0.176] | +0.354 [+0.225, +0.455] | +0.301 [+0.143, +0.407] | −0.301 |
  | Clean, FT | +0.104 [+0.005, +0.242] | +0.324 [+0.209, +0.408] | +0.341 [+0.205, +0.413] | −0.206 |

  The primary's permutation p is 0.0145 (0.0176 at 20,000 draws). This is the first knob read of these models on a set no recipe was chosen on, and it comes out near GOAT's.
- **By the declared map:** the primary clears zero, so its drive answers follow the search labels on a set it was not chosen on, and the question moves to the size of its answers. Neither pair is shown: on crunch drive FTm − W +0.113 [−0.035, +0.233], FTm − FT −0.003 [−0.064, +0.055]. FTm and FT read alike; FTm's answers spread wider.
- **The audit (independent, own code, every row reproduced; rows below post hoc).**
  - *The primary is one knob on one amp.* ac20Power, 21 units, picked out after the read, holds 77% of the row's answer variance and 80% of its covariance, and reads +0.438 [+0.021, +0.856] on a jackknife. FT (+0.441) and W (+0.371) read it too. Without it: +0.071 [−0.023, +0.166], p 0.151. Crunch drive without the ac20: +0.125 [−0.048, +0.298]. All classes' drive without that head stays clear, +0.110 [+0.012, +0.208]. The "spread 0.50" is that head (1.32); the rest sit at 0.08 to 0.73, 0.25 pooled.
  - *"Clear" is thin.* On a jackknife by creator, [+0.002, +0.316], and at 95% it reaches zero. No one creator carries it: leaving out any one gives +0.099 to +0.193. The declared beside rows, on a jackknife: head-standardised +0.136 [−0.011, +0.282], +0.091 [−0.043, +0.224] without ac20Power; without limit labels +0.150 [+0.011, +0.289].
  - *The size is small.* The answers explain 2.5% of the within-cell label variance, 0.5% without ac20Power. One label sd moves the answer about 1.4% of the knob's range. Used as they stand, the answers lose to the cell's mean on squared error by 8.8%.
  - *By jackknife the rest:* clean tone +0.354 [+0.225, +0.482], clean cab +0.301 [+0.162, +0.440], crunch cab +0.162 [+0.044, +0.280], all drive +0.125 [+0.031, +0.220]. Crunch tone (+0.057 [−0.123, +0.236]) and clean drive (+0.066 [−0.050, +0.181]) are not shown.
  - The fold rule holds in all 16 runs. Whether a capture's amp matches a GOAT profile in training cannot be checked. Most DIs are one player's, so these are new recordings, not new players.
- **What it changes.** The reading shows on a set no recipe was chosen on: FTm follows tone and cab on clean, cab on crunch, and drive on crunch mostly through one knob picked out after the read. Two limits: a capture's overlap with GOAT's profiles cannot be checked, and the DIs and most of the playing are GOAT's. It stays a read of labels through the true chain with a backing, not of sound or of a song, and the answers follow too weakly to use as they stand: the best slope is 0.32, so they would need shrinking threefold. This row is the baseline for any model trained on captures, and by the map the next question is size.
- Files: `captures/n6-read.json`, `captures/audit-n6-centre-n8/`. Scope: `captures/scope.json`.

### F60. L1a's centre read, by the score: not shown better than GOAT's labels, ahead of S on the panel's clean units only, and its distance from RcG is mostly cab, where v2 moves little (phase_l1a, 2,016 renders, counted panel read)
- **What ran.** RcT on the 121 trusted labels and RcG_n on GOAT's labels at the same 17 to 22 a cell, 3 seeded draws, on BKS's 40 units and the panel's 44, all 3 amps. No direction dropped, missing or refused. ln ratio, below zero closer:

  | Row | BKS, by DI | Panel, capped band weights |
  |---|---|---|
  | RcT − RcG_n | +0.051 [−0.048, +0.150] | −0.057 [−0.119, +0.005] |
  | RcT − S | −0.053 [−0.171, +0.066] | −0.113 [−0.191, −0.036] |
  | RcG − S, stored | −0.106 [−0.168, −0.045] | −0.069 [−0.114, −0.025] |

- **By the declared rule:** RcT − RcG_n does not read as moved on either set, so this batch's labels are not shown to move the centre by the score. RcT − S reads as moved on the panel by the rule's letter (its interval clears and RcT − RcG_n's draws agree in sign), which says RcT beats S there by the score, as RcG does, and not that it beats GOAT's labels.
- **The distance row.** RcT sits above GOAT's two-draw q95 in 5 cells and on the line in the sixth (pr12 clean, 0.115 against 0.114). That reading does not stand alone.
- **The audit (independent, every row recomputed from the judge files; rows below post hoc).**
  - *The panel's gain is all clean,* 11 units, 4 DIs, 3 bands: RcT − S −0.265 [−0.307, −0.223] on clean and −0.038 [−0.121, +0.046] on crunch. BKS goes the other way: clean +0.067 [−0.101, +0.236], crunch −0.173 [−0.312, −0.033]; RcT − RcG_n clean −0.179 [−0.309, −0.050] on the panel against +0.167 [+0.058, +0.276] on BKS. 28 of the panel's 33 crunch units are one band.
  - *Weights matter.* Panel RcT − RcG_n is −0.096 [−0.172, −0.020] on equal bands, −0.040 [−0.103, +0.024] DI-weighted, and −0.057 [−0.138, +0.024] band-clustered.
  - *Tone and cab look like the recipe's smaller steps; drive does not.* Distance from S, RcT against RcG: drive 0.168 against 0.155, tone 0.112 against 0.142, cab 0.043 against 0.182, against N2's ratios of 0.87, 0.68 and 0.41, which are BKS's, since v2 never ran on GOAT. Cab is 72% of the squared gap to RcG. On drive and tone dims alone RcT is above GOAT's q95 in 2 of 6 cells. On a rough null of GOAT's centres shrunk by N2's ratios, RcT sits outside only in the 3 crunch cells, with drive something beyond shrink (ac20Power +0.234 against +0.019). So the distance row does not show that the captures differ from GOAT.
  - The stored RcG − S rows match the earlier reports exactly. The read draws overlap 35 to 77% a cell, 58 to 61% pooled, and the cells hold 17 to 22 labels: the declaration's 57 to 78% and 20 to 26 were stale.
- **What it changes.** It picks no recipe, as declared. It makes no case for a capture centre over RcG; against S there is one clear panel row, on 4 clean DIs, and it goes the other way on BKS's clean units. The recipe and the batch cannot be told apart here: RcT and RcG differ most on cab. What caused the panel's gain is untested. The panel has now been read twice, so its clean row stands as a lead at most. V-real stays unread.
- Files: `captures/centre-read.json`, `captures/centre-distance.json`, `captures/audit-n6-centre-n8/`.

### F61. N8, does the stem lean toward another guitar: not shown on the amp head, and this linear reader's knobs lean toward the other guitar, in the mix as much as on the stem (phase_stem_lean, zero renders)
- **What ran.** Two linear readers on the tone probe's split, T2's core twins, 3,311 training and 623 FS5 rows whose loudest other guitar is not a double; 12 sections from 4 songs. T learns the target's labels, O the loudest other's. Control held: on the clean target T's amp head reads (0.782) and O's does not (0.318).

  | Input | Amp hit T / O | O − T, by section | T's follow | Today's 26 readable, T / O |
  |---|---|---|---|---|
  | Stem | 0.451 / 0.536 | **+0.025 [−0.118, +0.169]** | −0.021 [−0.155, +0.113] | 4 / 16 |
  | Mix | 0.440 / 0.531 | +0.055 [−0.034, +0.143] | −0.030 [−0.144, +0.085] | 3 / 11 |
  | Clean target | 0.782 / 0.318 | −0.474 [−0.530, −0.419] | +0.710 [+0.615, +0.804] | 24 / 1 |

  Stem minus mix −0.029 [−0.107, +0.049]; neither draw wide (276 rows) +0.072 [−0.073, +0.217]. Conditioning alone reads 1 and 1.
- **By the declared map:** not shown, and no step follows. The half-width came out 0.143 where the design said about 0.06: three sections hold 16 to 40 rows, and one of 17 rows reads −0.706. Pooled by example the gap is +0.085 [−0.012, +0.182], and by song, 4 of them, +0.036 [−0.221, +0.293], so this is a weak statement.
- **Beside, and audited.** T, trained on the target, follows the other guitar's labels more than the target's on the stem's knobs: drive r 0.033 against 0.239, −0.206 [−0.337, −0.075]; cab 0.198 against 0.371, −0.172 [−0.257, −0.088]; tone level. The audit could not make this an artefact: not the demeaning, not spread, not shared amps, and shuffling the other's labels gives about zero. It is not shown to be the separator's: stem less mix is drive −0.057 [−0.171, +0.057], cab −0.028 [−0.088, +0.031]. The all-rows head is smaller than the pooled drive row (inputGain +0.112 against +0.253), cab is the left mic, and cab shrinks when the other's draw is not wide (stem −0.057 [−0.107, −0.007], mix +0.013 [−0.039, +0.065]). The mix's drive row is unstable across fold deals and is not quoted. It is a direction, not a size: answers' sd 0.03 against labels' 0.2.
- **Post hoc, by level.** On the stem's drive, r with the target against r with the other: +0.297 against +0.042 on the 153 of 623 rows where the target is the louder guitar, gap +0.255 [−0.232, +0.742]; −0.026 against +0.255 where the other is louder, −0.281 [−0.436, −0.126]. Cab is level when the target is louder (+0.286 against +0.293, −0.007 [−0.137, +0.123]). On the mix the drive gap stays toward the other even when the target is louder, −0.136 [−0.303, +0.030]. Amp hits, pooled by example from two readers: T 0.529, O 0.490 target louder; T 0.426, O 0.551 other louder; by section neither split clears (−0.116 [−0.328, +0.095], +0.050 [−0.094, +0.194]). r with the other rises overall with its level, +0.626 [+0.295, +0.956] per 10 dB on left cab. 115 of the 153 rows are one song, the pattern holds within it, one section reads the other +4.7 dB louder yet T hits 0.82, and even at best the target's r stays far below the clean target's 0.63 to 0.76.
- **What it changes.** No proposal to train on real stems: the separator is not shown to be the cause. The lead changes shape: this linear reader leans toward the louder guitar (post hoc), so a part under a louder guitar may be the hard case, and how far in front the part sits is worth recording in L2's choice of parts. Whether this explains F56, where other guitars played, is not tested: presets here are independent by design, which real bands' often are not.
- Files: `tone-probe/stem-lean.json`, `captures/audit-n6-centre-n8/`. Log `logs/n8.log`.

### F62. N9, training on the captures, first step: undecided, no gain shown from the capture rows, and an undeclared lead only on the search's own mic labels (phase_n9, 32 runs on MPS, zero renders)
- **What ran.** FTm's recipe on real rows, 4 creator folds × 2 seeds, 32 runs, no fault; one run was lost to an app restart at epoch 30 and rerun, its losses matching to 4 decimals. Control passed. Read on all 121 trusted units held by their model. r, all classes, the declared bootstrap for the arms and delete-one-creator t for the pairs:

  | Arm | Drive | Tone | Cab |
  |---|---|---|---|
  | C-ctl, BKS and GOAT | 0.120 | 0.185 | 0.214 |
  | C-c39, C-ctl stopped at 39 epochs | 0.091 | 0.138 | 0.187 |
  | C-cap, with capture rows | 0.138 | 0.171 | 0.238 |
  | C-mic, with mic weight 0.1 | 0.146 | 0.182 | 0.268 |
  | **C-cap − C-ctl, primary** | **+0.018 [−0.032, +0.068]** | **−0.014 [−0.093, +0.065]** | **+0.024 [−0.028, +0.076]** |
  | Head-standardised | +0.002 [−0.084, +0.088] | −0.021 [−0.085, +0.042] | +0.019 [−0.044, +0.082] |
  | C-mic − C-cap | +0.008 [−0.033, +0.049] | +0.011 [−0.052, +0.073] | +0.029 [−0.035, +0.094] |
  | C-cap − C-c39 | +0.047 [+0.014, +0.079] | +0.033 [−0.062, +0.128] | +0.051 [+0.002, +0.101] |

- **By the declared map:** undecided, the outcome the design expected. This pair is capture rows in place of a third of the updates, not capture rows on top and not more rows. It excludes a gain above about +0.07 to +0.08 in r and a cost worse than −0.03 on drive and cab and −0.09 on tone. It does not exclude +0.05, which would be 40% more drive r, and a true +0.05 clears only about half the time. All six class rows reach zero too: crunch +0.041, +0.060, +0.033; clean −0.015, −0.091, +0.016.
- **The audit (independent, own code, the stored nets rerun; every row reproduced; below post hoc).**
  - *C-cap − C-c39 is not evidence for capture labels,* though it clears on drive, cab and crunch drive (+0.081 [+0.039, +0.123]). It splits into the capture swap plus updates on BKS and GOAT alone (drive +0.018 and +0.029, tone −0.014 and +0.047, cab +0.024 and +0.027, crunch drive +0.041 and +0.040). No clear row is clear on both seeds, all reach zero with seed noise by a crude two-seed estimate, the head-standardised pairs reach zero, drive and crunch drive lose their clear without one DI (`goat/item_155`: +0.034 [−0.011, +0.080], +0.066 [−0.021, +0.153]), and cab loses it on removing any of several creators or DIs.
  - *Updates.* C-c39 is C-ctl's own run stopped early, its losses matching at every shared epoch. C-ctl − C-c39 reads +0.029 [−0.007, +0.065], +0.047 [+0.0004, +0.095], +0.027 [−0.002, +0.056], with the head-standardised rows all reaching zero, so there is no sign FTm's E is high, and it may be low on r. Squared-error skill does not settle it: drive −.009 [−.045, +.027], cab −.024 [−.067, +.020], tone +.016 [+.001, +.031]. Two points only, and this read set must not choose E.
  - *Seed noise is not small here,* against the plan's line from GOAT: C-cap − C-ctl differs between seeds by .041, .049 and .023.
  - *The drive read is still ac20Power.* It holds 63% of the covariance in C-ctl, 74% in C-cap and 64% in C-mic. The primary's +0.018 is all that knob: without it C-cap − C-ctl is −0.020 [−0.090, +0.051]. Capture rows did not move spread to inputGain: its answer spread as a ratio to ac20Power's barely changes (.114 to .117). Against the slope, ac20Power's answers run about 4× too wide and inputGain's about 3× too narrow, though ac20Power's spread is only 1.2 to 1.4× the labels'. C-mic − C-cap on inputGain alone is +0.132 [+0.008, +0.257], undeclared, a lead at most.
  - *The answers still lose to the cell mean* on drive and cab in every arm (C-cap −.060, −.039), and on tone barely win (+.026), with C-cap − C-ctl flat.
  - *The one lead is on mic labels.* Own against swap, more negative better: total C-cap − C-ctl −0.104 [−0.170, −0.037], mic −0.081 [−0.131, −0.031], knob −0.018 [−0.039, +0.004]. About 40% of the mic move is scale. The rest survives a scale-free read (own-over-other top-1 +.037 to +.158, paired +.121 [+.071, +.170]). C-cap's own top-1 of .55 barely beats a no-audio majority of .50, so its absolute mic accuracy is mostly the label prior, and only the own-over-other part is a reading. It is undeclared, no shuffled-label control has run, and BatchNorm can move toward capture audio with no label content. It is on search v2's mic labels, on which training and read share a recipe, so it says nothing of sound and is not a knob gain.
  - *C-ctl against N6's FTm:* the small native gap is about cells, not models, and the extra labels show nothing.
  - No primary row changes status on removing one creator or DI, though tone's sign flips on 2 creators or 3 DIs, its point sitting near zero. Crunch C-cap − C-ctl drive would clear without one creator (+0.080 [+0.024, +0.137]) or one DI (+0.074 [+0.015, +0.132]). No leakage on any fold, arm or source. All 32 records match the log.
- **What it changes.** Nothing is adopted. No gain is shown from replacing a third of the updates with 67 to 82 capture units, and a gain up to about +0.08 is not excluded, so by the map the second batch is the test with more rows. C-mic is not shown ahead of C-cap. The spread between ac20Power and inputGain is untouched by these rows: an untested candidate, from a post hoc scale read, and a rescale alone cannot raise r.
- The design's limits needed two corrections: "a third of C-cap's rows mostly teach cab at S" holds for the continuous cab knobs (29 to 34% left S, mic level 16%), not for mic type (67% and 43%); and seed noise was larger here than the GOAT figure it quoted.
- Files: `captrain/n9-read.json`, `captrain/audit/`. Logs `logs/n9.log`, `logs/n9-read.log`.

### F63. N9b, a ridge with and without capture rows: mixed, and neither leg firm (phase_n9b, zero renders, zero training)
- **What ran.** `M-pcs`, the mel ridge at 64 PCs, fitted per capture fold on N9's rows, each labelled record once, 473 to 565 records, capture rows 12 to 15% of a fit, so here they sit on top of BKS's and GOAT's. Read on the same 121 held units as N9, on variant 0. Control passed, worst 0.0.

  | r | Drive | Tone | Cab |
  |---|---|---|---|
  | M-ctl | 0.173 | 0.283 | 0.134 |
  | M-cap | 0.117 | 0.322 | 0.147 |
  | **M-cap − M-ctl, primary** | **−0.056 [−0.093, −0.019]** | **+0.038 [+0.001, +0.076]** | **+0.013 [−0.017, +0.044]** |
  | Head-standardised | −0.024 [−0.078, +0.031] | +0.023 [−0.046, +0.091] | +0.010 [−0.020, +0.040] |
  | 25-backing mean, the same pair | −0.044 [−0.080, −0.007] | +0.061 [+0.016, +0.106] | +0.001 [−0.029, +0.031] |
  | M-ctl − C-ctl, ridge against network | +0.053 [−0.097, +0.203] | +0.098 [−0.033, +0.229] | −0.080 [−0.190, +0.029] |

- **By the declared map:** mixed, so no step on its own. It reads differently on other backings: on each of the 25 single backings the map gives undecided 11, lead 6, cost 5, mixed 3. Measured on these answers, chance gives mixed 1.0%, lead 9.3%, cost 8.5%.
- **The audit (independent, own replica matching the stored answers to 2e-16, C-ctl's nets run on all 25 backings; every row reproduced; below post hoc).**
  - *Drive's cost is real but narrow, and variant 0 overstates it.* It holds on removing any creator, DI or capture, and all four folds are negative. But variant 0 is the most negative of the 25 backings (single-backing mean −0.030, negative on 24). About 40% is the capture rows' offset going into the pooled cell mean: with capture rows centred on their own cell mean, −0.032 [−0.062, −0.003]. Recipe and recordings cannot be separated on these rows. Much of the cost sits on pr12Volume (−0.192 [−0.335, −0.048]), which N9's C-cap also flipped, and most of that head's flip is the same offset: centring takes it to −0.054 [−0.103, −0.005], and after centring, removing that head barely moves drive (−0.028 [−0.064, +0.008]). inputGain does not move (+0.001). Centring also ends tone's clear (+0.024 [−0.012, +0.059]) and does not remove the drive cost on variant 0, so it is a candidate to test, on a ridge only: networks have no pooled cell mean, and N9's C-cap showed no drive cost.
  - *Tone's gain is a lead at most.* About two thirds comes through the penalty: at M-ctl's penalty it is +0.011 [−0.013, +0.035], and M-ctl alone gains +0.026 at M-cap's penalty. On the 25-backing mean the same step takes +0.061 to +0.017 [−0.007, +0.041]. Inner folds holding creators keep +0.034 [+0.004, +0.064], so this is not the leak the design feared. The clear ends on removing any of 13 of 19 creators, and it rests on pr12 (+0.100 [+0.025, +0.174]; without pr12Treble +0.022 [−0.031, +0.076]). Shuffled labels give +0.000 (sd .018) and the real value ranks 12 of 13, which is not decisive.
  - *The ridge is not shown to beat the cell mean, or the networks.* Skill by creator, M-ctl against C-ctl: drive +.025 [−.041, +.091] and −.057 [−.135, +.020]; tone +.069 [−.030, +.168] and +.034 [−.006, +.074]; cab −.124 [−.246, −.002] and −.040 [−.130, +.050]. The pair reaches zero on all three.
  - *The networks' readout, a lead on answer size only.* Most of drive's point lead over the nets is C-ctl's median readout on ac20Power (skill −.671 by median, −.074 by mean). C-ctl's mixture mean beats its median on squared error: +.059 [+.024, +.093], +.012 [+.004, +.019], +.057 [+.033, +.082], which moves its skill to +.001, +.046, +.017, so drive only reaches the cell mean. That is mostly narrower answers, not more following: spread falls from .388 to .247 on drive and .507 to .408 on cab, and on ac20Power from 1.17 to .67, with r going from .296 to .277. Mean against median r is +.006 [−.021, +.033], +.033 [+.011, +.054] (standardised +.010, reaching zero), +.011 [−.005, +.027]. Undeclared, on C-ctl and not FTm, and it says nothing of sound.
  - *Backing noise is a large part of the ridge's error.* M-ctl's r over 1, 4 and 25 backings: drive .147, .188, .205; tone .263, .338, .360; cab .145, .187, .198. That says the sign is no accident of variant 0. It says nothing of songs: it is the same guitar under other backings. On 25 backings the ridge-against-net skill pairs are +.061 [−.008, +.131], +.097 [+.020, +.173], −.029 [−.096, +.037] on the median readout and +.033 [−.021, +.087], +.084 [+.005, +.164], −.056 [−.125, +.012] on the mean.
  - BKS is 63 to 65% of M-ctl's records against 50% of C-ctl's rows, and 54 to 57% of M-cap's against 34% of C-cap's, so ridge-against-net pairs are not the same data balance. Variant 0 also flatters C-ctl's tone, the best of its 25 backings.
- **What it changes.** Adding capture rows on top is not shown to help a ridge, and they cost a little on drive. Centring the capture rows' offset is a candidate to test, not a fix: it was tried post hoc on a ridge only, and it left some drive cost and ended tone's clear. `E-mix`, which needs 3,025 more embedded inputs for the 121 units, waits. The mixture mean is a lead on answer size only. Averaging over more of a recording is the review session's idea, which this read does not test. The second batch's labels are search v2's too. Nothing here is sound.
- Files: `captrain/n9b-read.json`, `captrain/audit/`. Log `logs/n9b.log`.

### F64. N10, the trained models on the second batch: undecided on both pairs; tone agrees weakly, on sw50r for the networks; all-class drive is set by two units (phase_n10, zero renders, zero training)
**Corrected 2026-11-07, see F65.** 15 of the 47 units sit on DIs T0 refused or left unheard. On the 32 verified units both pairs stay undecided and the decision stands, but rows below change: read F65's beside them.

- **What ran.** 1,175 inputs built with no label read, then FTm, C-ctl, C-cap, C-mic and C-c39 by the mean of their 8 models, and the mel ridges, on the second batch's 47 trusted units, 38 creators. Controls passed. No model's real rows hold these units; 4 use a DI file in W's plugin rows, and 6 share a creator with the first batch's training rows.

  | r, all classes (perm p) | Drive | Tone | Cab |
  |---|---|---|---|
  | FTm | −0.047 (.53) | 0.153 (.08) | 0.117 (.10) |
  | C-ctl | −0.042 (.51) | 0.133 (.12) | 0.076 (.20) |
  | C-cap | −0.011 (.50) | 0.217 (.03) | 0.064 (.23) |
  | C-mic | −0.034 (.54) | 0.250 (.02) | 0.055 (.27) |
  | M-ctl | 0.120 (.13) | 0.101 (.19) | −0.006 (.53) |
  | M-cap | 0.141 (.06) | 0.046 (.36) | 0.000 (.50) |
  | M-ctl, 25 backings | 0.005 (.49) | 0.372 (.001) | 0.183 (.04) |
  | M-cap, 25 backings | 0.053 (.27) | 0.359 (.002) | 0.195 (.02) |
  | **C-cap − C-ctl, primary** | **+0.031 [−0.078, +0.140]** | **+0.084 [−0.029, +0.198]** | **−0.012 [−0.103, +0.080]** |
  | **M-cap − M-ctl, primary** | **+0.020 [−0.039, +0.080]** | **−0.055 [−0.124, +0.013]** | **+0.007 [−0.043, +0.057]** |

  Head-standardised, C-cap − C-ctl +0.013, +0.109, −0.040 and M-cap − M-ctl +0.024, −0.038, −0.017, all reaching zero. Clean alone (38 units): FTm 0.073, 0.256, 0.230; C-cap 0.192, 0.251, 0.154.
- **By the declared map:** both pairs undecided, so no new training on captures from this read, and the review session's ear page decides what follows.
- **What the rows show (audited, independent, every number reproduced; head and band rows post hoc).** p is one-sided. On all classes the networks' drive r is set by one head on two units: ac20Power in the ac20 crunch cell, answered 0.31 and 0.93 (FTm) against labels 0.61 and 0.36. Those answers hold 44–66% of the nets' drive answer variance. Without that head in that cell, r is 0.07 to 0.17 and skill −0.06 to +0.03. On clean, drive is 0.07 to 0.19, only C-cap under p .05 (.016). Tone agrees with search labels in sign on every arm. For the networks that is sw50r: 72–101% of the covariance, r 0.00 to 0.13 and p ≥ .25 without it. Cab on clean is FTm's (0.230, standardised 0.175); the other nets fade when standardised and the single-backing ridges read about zero. The ridge on 25 backings agrees best on tone (0.37, 0.36, across all three amps), but no song offers 25 backings, the nets read one, and on one backing it reads tone 0.10, 0.05 and cab about zero.
- **Declared beside rows.** Without the shared creators, C-cap − C-ctl +0.048, +0.089, −0.018 and M-cap − M-ctl −0.001, −0.055, −0.008, all reaching zero. 3 of 42 beside rows clear, about 4 by chance, none primary, each standardised pair reaching zero: M-cap-25 − M-ctl-25 drive +0.048 [+0.003, +0.094], C-mic − C-cap drive on clean −0.102 [−0.165, −0.039], C-cap − C-c39 drive on clean +0.119 [+0.028, +0.211]. Own against swap reaches zero on every total and part (FTm −0.056 [−0.171, +0.058], C-cap −0.077 [−0.212, +0.059]), so it gives no support to the tone or cab rows.
- **By band (post hoc).** Tone keeps its sign on removing any band, except M-cap, and clears on a band jackknife only for the 25-backing ridges. M-cap − M-ctl tone by band is −0.055 [−0.108, −0.003], its standardised pair reaching zero; either way the next step is no new training. A sign-flip by band runs a little above the permutation p on most rows. The ridges' drive (0.120, 0.141) rests on one unit: without its DI 0.011, 0.050.
- **Limits.** 47 units, cells of 2 to 16, 27 DI files in 14 bands, which the permutation ignores, and 8-model means that do not compare with N6's or N9's single-fold r. r is agreement with search labels, not sound. All these labels are search v2's. Disjointness from the fits' DIs is by name and session; audio was not compared.
- Files: `captures2/n10-read.json`. Log `logs/n10.log`.

### F65. The score against the ear on stored pages: J0's order follows the ear at about +0.5, large gaps agree most, and a fixed order reaches about half of it; and N10b, F64 corrected (phase_n10b, phase_n11, zero renders, one listener)
- **N10b, the correction.** L1b's draw took `training_ok` for T0's verdict, so 15 of the second batch's 47 units sat on DIs T0 refused or left unheard (Doom Flamingo 6, Eggy 4, Bernard Purdie 2, Starnes And Shah 2, Timo And The Timezone 1). `capture_labels.trusted` now drops them, and refuses a DI T0 has no verdict on. Re-read on the 32 units, 29 creators, 18 DIs, 9 bands, zero renders; the answers equal N10's.

  | On 32 units | Drive | Tone | Cab |
  |---|---|---|---|
  | FTm, r (p) | −0.114 (.64) | 0.108 (.17) | −0.079 (.74) |
  | M-ctl, r (p) | −0.002 (.49) | 0.017 (.44) | 0.088 (.22) |
  | **C-cap − C-ctl** | −0.015 [−0.072, +0.042] | +0.102 [−0.028, +0.232] | +0.046 [−0.053, +0.145] |
  | **M-cap − M-ctl** | +0.048 [−0.020, +0.115] | −0.074 [−0.189, +0.040] | −0.011 [−0.049, +0.027] |

  What changes in F64: FTm's cab falls from 0.117 to −0.079; the ridges' drive falls to −0.00 and 0.05; M-cap's tone turns negative, so "every arm" fails on tone; "on sw50r" holds for FTm and C-ctl only; the 25-backing ridges' cab p is .10 and .09. 2 of 42 beside rows clear, both new, about 4 by chance. The swap's switch part clears for C-cap and C-mic. The audit's sentence: "On the 32 verified units both pairs stay undecided, and no new capture training follows."
- **N11, what ran.** J0's held-half order against the ear on four blind pages of whole presets on the same performance: L0, N4, F57, `ear-eat`, 43 cards, 12 clusters. `record-match-1` beside. V-real's rows are stored rows only, and they brief no judge term. F57 is less the label page's out-of-scope unit, with item 8 by the listener's blind correction, and clusters on GOAT players, since its creators sit on players `ear-eat` shares.

  | Mean within-card Spearman, ear and J0 | Cards, clusters, all | All candidates | Without label | Models only |
  |---|---|---|---|---|
  | L0, V-real | 10, 7 | +0.50 [+0.20, +0.80] | same | +0.70 [+0.47, +0.93] |
  | N4, V-real | 10, 7 | +0.50 [+0.10, +0.90] | same | under 3 candidates |
  | F57 | 10, 2 | +0.60 | under 3 candidates | under 3 candidates |
  | `ear-eat` | 13, 5 | +0.62 [+0.41, +0.84] | +0.65 [+0.33, +0.97] | +0.35 [−0.21, +0.91] |
  | Pooled | 43, 12 | +0.56 [+0.41, +0.71] | +0.56 [+0.34, +0.77], 33 cards | +0.50 [+0.22, +0.78], 23 cards |

- **How much needs no score.** Pooled, S last with the rest tied reads +0.13 [−0.11, +0.37], and a fixed order from other clusters +0.25 [+0.10, +0.41]. What J0 adds over that fixed order is +0.31 [−0.08, +0.69], reaching zero. N4's own row, +0.80 [−1.61, +3.21], is unusable: near-tied mean ranks swing the baseline, passing the possible ±2. A post hoc form, card-and-type residuals, reads 0.41 [0.29, 0.52] pooled and about 0.34 on V-real.
- **Large gaps agree most (post hoc cut).** At a J0 log ratio of 0.2, 96% [92, 100] of pairs agree with the ear above it and 65% [56, 75] below, +0.31 [0.21, 0.41], also +0.31 within page and pair type, order kept and gaps shuffled p < .001. No cut was set in advance: 0.2 is a tercile edge. At 10% the difference is +0.20 [0.09, 0.31], and at 5% it is +0.09, reaching zero. A fixed order alone gets 85% above and 52% below, so J0 adds +0.11 [0.04, 0.19] above. Among models alone, outside W, 8 pairs sit above the cut. Below it models agree with the ear on about two pairs in three, 67% [53, 81], where the ear repeats its own pair order 78%.
- **Models against S.** Within page and model, gain by the score against closeness gain by the ear is +0.45 [0.26, 0.64]. On V-real's parts, above S of 10 parts by the score FT 4, D_fix 3, FTm 2, W 0, and by ear rank FT 5, D_fix 3, FTm 4, W 2; of the gaps between score and ear only W's clears. FTm between pages: rank −0.29 [−0.82, +0.24], score −0.19 [−0.40, +0.02], with S's amp and model versions confounded. So V-real against development stays unshown. FT's "side of S" agreeing 5 of 10 is one read shown twice and is chance from margins; like for like, FTm agrees 8 of 10 on V-real and 11 of 13 on `ear-eat`. Labels' agreement is J0's own choice, kappa 0.
- **The ear's own repeat.** Six repeats, r 0.75 [0.56, 0.94]. The simulated ceiling on a fixed score is about 0.83; √r's 0.87 runs high. Pairs repeat 92% above the cut and 78% below.
- **The audit's sentence.** "On one listener's 43 cards J0's order follows the ear at about +0.5, large gaps agree most, a fixed order reaches about half of that, and V-real against development stays unshown."
- **What it changes.** Nothing moves: J0 stays. The user's concern stands narrower than "the score is wrong": between close models J0 and the ear agree about two pairs in three, and on V-real's parts the two differ most on W. No fix is proposed yet. N12 follows.
- Files: `PF/score-ear-n11.json`, `captures2/n10b-read.json`. Plan: [score-ear-plan.md](score-ear-plan.md).

### F66. N12, a blind page built on 9 other bands, read on 8: by ear every model sits above S on 11 to 12 of 13 ranked cards and FTm above `EW-mix` on 11, a description; J0 follows the ear at +0.69 but adds nothing shown over a fixed order here, and parts from it mostly on small gaps between models (phase_n12, 250 renders, one listener)
- **What ran.** The second capture batch's T0-verified units: real songs' DIs through captured real amps, from 9 bands outside GOAT and BKS. 14 first hearings, 2 repeats and 2 crunch spares went on two blind pages, answered in place. Each card had five candidates: S, FTm, `M-pcs`, `EW-mix` and the search's label, each answering from the unit's search half and judged on its held half. 13 cards were read. The fourteenth, Death Of A Romantic's clean card, was left unranked with "All sound the same", and J0's spread there without the label is 0.053 in log ratio, under every read card's 0.10 to 0.61, so the score had them close too. It was not marked out of scope, and being clean, it takes no spare. 1 card unfilled is within the declared 3, so the page stands. No spare was used. The fourteenth card enters as a tie, which the sign test drops. Read both ways, every row keeps its reading except `EW-mix` over S, which reaches one half if that card counts against it (11 of 14, jackknife lower end 0.50, the PR review's check). Renders: 250 with their priming renders, against the declared about 350. Audited with separate code: every number below matches. Rows marked † come from the audit's code, not the stored report: they are stored with it in `PF/score-ear-n12-audit/`.
- **Seen†.** 5 of the 13 cards are on songs in W's plugin rows: The Travelling Band (on the same DI file), Ale Lak 2 and Storm Of Particles 2. By the plan, none are in any model's real rows. The other 8 cards, on 5 songs, are outside W's plugin rows; none is called unseen, since the readers' input pool holds backings from some of these sessions (Cnoc An Tursa among them).
- **By ear, on the declared map.** Rank share, a 90% jackknife t interval† by the DI's band (df 7), its ends clipped to [0, 1], the stored percentile beside, closeness gap on 0 to 3, one-sided sign test, Holm over the six.

  | Row | Above, of 13 | Share [jackknife] (percentile) | Closeness gap | Holm p | On the 8 cards outside W's rows |
  |---|---|---|---|---|---|
  | label over S | 13 | 1.00 (1.00) | +1.54 [+0.93, +2.15] | .001 | 8 of 8 |
  | FTm over S | 12 | 0.92 [0.78, 1.00] (0.80, 1.00) | +0.69 [+0.07, +1.31] | .009 | 7 of 8 |
  | `M-pcs` over S | 12 | 0.92 [0.78, 1.00] (0.80, 1.00) | +0.46 [+0.16, +0.76] | .009 | 7 of 8 |
  | `EW-mix` over S | 11 | 0.85 [0.55, 1.00] (0.60, 1.00) | +0.46 [+0.00, +0.92] | .034 | 6 of 8 |
  | `EW-mix` over FTm | 2 | 0.15 [0.00, 0.34] (0.00, 0.31) | −0.23 [−0.61, +0.14] | 1 | 1 of 8 |
  | `M-pcs` over FTm | 4 | 0.31 [0.09, 0.52] (0.14, 0.50) | −0.23 [−0.62, +0.16] | 1 | 3 of 8 |

  The four rows over S clear after correction. `EW-mix` over FTm, the row that led 10 of 13 on `ear-eat` without surviving correction, reads the other way here: FTm is above it on 11 of 13 cards. That direction was not a declared test, so it is a description. FTm's closeness gain over S sits on the 8 cards outside W's rows, +1.13, and is 0.0 on the 5 cards on W's songs (3 songs), a description. No model is picked from this page, as declared.
- **By the score, on all 31 units with a finite held judge.** `ln(d_x/d_y)`, clustered by the DI's band, 9 bands. FTm is 11% closer than S [3, 19], `EW-mix` 11% [3, 18], `M-pcs` 8% [0.3, 16] and the label 33% [24, 41]. `EW-mix` less FTm is +0.4% [−4.1, +5.2], and `M-pcs` less FTm +3.2% [−1.1, +7.8], both undecided, `EW-mix` level with FTm and `M-pcs` leaning worse. By the score every model beats S here, where on V-real's held parts F56 put FTm behind S.
- **The score against the ear (N11's rows on this page).**
  - J0's order within a card, without the label: +0.69 [+0.43, +0.96]. With the label: +0.78 [+0.61, +0.96]. Models only: +0.54 [+0.19, +0.89].
  - What needs no score: S last with the rest tied reads +0.62 [+0.31, +0.92], and a fixed order from the other bands +0.68 [+0.45, +0.91], or SE 0.124† when recomputed at each deletion.
  - **The primary:** what J0 adds over that fixed order is +0.02 [−0.23, +0.26], reaching zero. That is the outcome the plan called likely whatever is true, and it says nothing against J0. On `ear-eat` the same row reads +0.39 [−0.52, +1.31]. The pages' difference is −0.38 [−1.34, +0.58], as stored, with t at df 4; at Welch's df 4.7 it is [−1.30, +0.54]†. Undecided.
  - The ear's ranks lean one way on most cards† (S last on 11 of 13, the label first on 8; mean ranks label 1.7, FTm 2.3, `M-pcs` 3.0, `EW-mix` 3.3, S 4.7), so a fixed order already reaches +0.68 and leaves J0 little to add.
- **Where the two part.** These rows are descriptive, the brief for judge terms.
  - By J0's gap, in thirds. Between models only (39 pairs) the ear agrees 100%, 77% and 46%: at chance under a log ratio of about 0.06. With S in (78 pairs)†: 96%, 81% and 65%. Under 0.03, it agrees 6 of 11.
  - 15 of the 78 pairs disagree, and on 13 of those the ear gave both sides the same closeness. Clean 12 of 42 pairs against crunch 3 of 36. pr12 9 of 24, sw50r 4 of 30, ac20 2 of 24. Cnoc An Tursa 6 of 12 and The Long Wait 3 of 6. 9 of the 15 are on three clean cards, two of them pr12, so the class and amp tallies rest on few cards.
  - Against S, the score puts a model closer on 87% of the 39 model-against-S pairs, while the ear's closeness rises on 46% and stays equal on 49%. Side of S agrees for the label 13 of 13, FTm and `EW-mix` 12, and `M-pcs` 10.
  - So J0 parts from the ear mostly where its gap between models is small, and 9 of its 15 disagreements fall on three clean cards (descriptive, post hoc). With N11's development rows (on `ear-eat`, model pairs under a J0 log ratio of about 0.1 agree with the ear 16 of 26; V-real's rows stay out, as the plan says), that is one brief: where J0 sees a gap of a few per cent between models, the ear's forced order is at or near chance and its closeness rating is mostly the same.
- **The ear's own repeat.** Both repeats read r 0.9 over five candidates, and 0.8† without the label. Each swaps one pair of models. The ceiling it puts on a fixed score, √0.9, is about 0.95.
- **The audit's notes, carried here.** The ear rows' stored intervals are percentile ones; the jackknife t above is the declared primary, and no reading changes. The gap bins as stored use model pairs only, so both sets are given above. `filled` let a spare replace only a crunch card marked out of scope, not one left unanswered, where the plan's failure rule counts both. That did not trigger here, and the code now takes either. On 12 of the 16 units rendered for the page the label's fresh render hash differs from its stored one, while J0 agrees within 1e-5. The hash rule held for S; the label was held to its stored judge, within 0.1%, as `cmd_render` does.
- **The audit's sentence.** "On 13 cards in 8 other bands, one listener: by ear the label and every model sit above S (11 to 13 of 13, clear after Holm), and FTm sits above `EW-mix` on 11, a description, not a declared test. J0 orders a card's candidates about as well as a fixed order does (+0.69 against +0.68), so what it adds, +0.02 [−0.23, +0.26], reaches zero. Where they part is mostly between models on small J0 gaps: below about 6% the ear's order between models is at chance, and 9 of the 15 disagreements fall on three clean cards."
- **What it changes.** J0 stays, and FTm stays the main model: no reader is shown better than it, by ear or by the score. The judge-terms brief goes to the review session as a declared study: small gaps between models, with the clean cards noted, with N11's development rows (F57 and `ear-eat`); V-real's L0 and N4 rows stay out, as N11 and N12 declare. The held bands' test stays the user's decision.
- Files: `PF/score-ear-n12.json`, `PF/ear-wide/heard/` (the two parts' answers), `PF/ear-wide/key.json`, `PF/score-ear-n12-audit/` (the audit's code and output, the seen list, the † rows). Plan: [score-ear-plan.md](score-ear-plan.md).

### F67. H1, the dry-render pilot: the dry path changes only what it should; the doubler and the room mic move the measure most, tremolo on half its rows, reverb and delay little at the median; m = 0.5 dB (phase_h1, 150 renders, audited)
- **What ran.** 75 of W's 1,753 training rows outside Ale Lak and Storm Of Particles, seed 20261108, each in its own new plugin process with one priming render and a 0.25 s trim ([plan](heavy-cleanup-plan.md)).
  - 60 rows, 10 per family, had one switch on and were rendered dry: the time effects off, the row's own spring at 0, both room mics off.
  - 15 rows were rendered again as stored.
- **The checks pass.** All 15 rows rendered again as stored are bit-identical to their targets: the 10 with no switch and the 5 with one or more on (4 of them several). Every dry render changed only the declared keys and set each to off. 5 rows also turned off a room on a cab that is switched off, which "both room mics off" covers.
- **The shift, the stored measure less the dry one, in dB.**

  | Family | Median | Min | Max |
  |---|---|---|---|
  | doubler | +4.82 | +1.41 | +13.79 |
  | room | +3.13 | +0.01 | +7.58 |
  | tremolo | +0.88 | −0.43 | +4.21 |
  | delay | +0.32 | 0.00 | +2.37 |
  | spring | +0.24 | 0.00 | +1.14 |
  | reverb | +0.10 | −0.02 | +3.86 |

  The doubler and the room mic move the measure most: every doubler row by at least 1.41 dB and 9 of 10 room rows by 1 dB or more. Tremolo moves it by 1 dB or more on 5 of 10 rows. Reverb and delay move it little at the median (+0.10 and +0.32 dB), but not always: one reverb row by 3.86 dB, one delay row by 2.37 dB, and another delay row (0.97 dB) crossed −2.91 dB downward. One spring row sits at 0.001, so the spring family tells something on 9 rows.
- **The margin.** The worst negative shift is −0.43 dB, on an sw50r tremolo row, so m = 0.5 dB. Only 4 of the 60 shifts are negative, and 3 of those are tremolo on sw50r. No row went past −0.5 dB, but with 10 rows a family that only rules out such shifts on more than about 26% of a family's single-switch rows, or about 5% over the 60 as drawn (one-sided 95% upper bounds). So H2's audit window, not m alone, guards rows near the line. 1,202 of the 1,543 rows with a switch have more than one on, which single-switch rows don't bound. No row crossed −2.91 dB upward, and 8 crossed downward when rendered dry.
- **The audit's sentence.** "Recomputed independently from the raw audio, every number in H1's stored read is correct: the draw follows the plan and reproduces from seed 20261108, the 15 rows rendered again as stored are bit-identical to their targets, the 60 dry renders changed only the declared keys, and the shifts by family, the worst negative shift (−0.43 dB, a tremolo row) and m = 0.5 dB all match; since m rests on 60 single-switch rows and none went past it, H2's audit window, not m alone, guards the rows near the line."
- **What it changes.** H2 can render rows dry by the narrow rule, at the line less 0.5 dB, with its audit. It waits on the keep-or-drop answers for the line. 28 rows have their spring at 0.01 or less (24 at 0.001) and count it as on. 27 of them have another switch on and would be rendered dry anyway, so at most one, 801019, is rendered dry for nothing. That is harmless.
- Files: `PF/heavy/h1-plan.json`, `PF/heavy/h1-read.json`, `PF/heavy/h1/`.

### F68. The heavy clean-up, closed: the keep-or-drop answers, a tone-free measure, the plugin line, and three FTm variants retrained on what is left. None is shown better than FTm by the score or by ear; all three beat S by the score, as FTm does, and on the blind page (FTm itself 10 of 14 over S there, p 0.058) (phase_scope, phase_h2a, phase_h2, phase_h4, 5,512 renders, about 4.3 h of MPS, one listener, audited)
- **What ran.** The user asked to clear too-heavy recordings out of training and testing ([plan](heavy-cleanup-plan.md)).
  - A blind keep-or-drop page covered the real rows.
  - The declared drive meter did not fit those answers, so Amendment 1 replaced it with a tone-free flatness. A blind check page of W's stored plugin examples then set the plugin line.
  - W's doubler rows were measured with the doubler off (H2), and the exclusions were pinned.
  - H4 retrained FTm's masked recipe three ways: full cut, gentle cut, and real rows cleaned only. Each was read by FTm's stored score read (H4a), then on one blind page (H4b).
  - Each read was audited with separate code, and every number below matches.
- **Keep-or-drop (`phase_scope`).** 124 recordings on the page: 110 keep, 12 heavy, 2 unsure.
  - With the earlier pages' marks, 19 of the 316 labelled real recordings go out: GOAT pr12 crunch 9 of 35, sw50r 6 of 33, ac20 2 of 36, and BKS 2 of 80. All are crunch.
  - Many recordings are parts or guitars of one song, so every row here is clustered by song.
- **The measure (Amendment 1).**
  - **The declared rule did not fit.** It gave +1.05 dB [−2.27, +2.63]. The drive meter separates the answers at AUC 0.63 [0.55, 0.75] and reads rooms as drive.
  - **The replacement.** `heavy_cleanup.flatness_db` is the median spectral flatness of the amp's sound over 200–5000 Hz, against its own 1/3-octave average, on frames where the DI and the amp both play.
  - **How well it separates.** On GOAT it separates the answers at AUC 0.85 [0.78, 0.92]. The sources differ in scale, so no one line carries across them.
  - **The doubler lowers the reading,** so its rows are measured with the doubler off. H2 rendered 507 doubler rows with the doubler off, two renders a row with the priming one (1,014 renders). The doubler lowers the reading by a median 0.70 dB: doubler off reads 0.70 dB flatter. NS's 114 doubler rows took 228 more renders.
- **The plugin line (`phase_h2a`).** 50 blind cards from W's stored examples, zero renders: 28 heavy, 18 keep, 4 unsure.
  - The line is −4.331 dB, the 51st percentile of the 1,246 doubler-free rows. Its 90% interval is [−5.08, −3.57], the 36th to 75th percentile. That width makes it undecided: `check_read` missed the flag, and the audit caught it.
  - Drops by band were 2, 6, 10 and 8 of 10. In 4 of 4 split pairs the flatter card was dropped.
  - The full cut trips both stops (cells and 13 whole sections), and Bulldozer is 42% of it. The user ruled to train both cuts and compare.
- **The exclusions** (`PF/heavy/h4-exclusions.json`, sha256 cc7b9ab9…cb36f2, `phase_h4_exclusions`):
  - **real_out:** 19.
  - **Full cut (−4.331):** 927 of W's 1,787 rows out, 860 left. NS keeps 259 of 383.
  - **Gentle cut (−3.57385, the 75th percentile):** 496 out, 1,291 left. NS keeps 338.
  - Every arm drops real_out from training and from every epoch-choosing held set.
- **Training (H4).** 4 h 17 min of MPS in one run, with no failure:
  - Full arm: 1 h 22 min. Gentle: 1 h 41 min. Real only, which reuses W: 1 h 13 min.
  - The retrained W's best epochs were 50 and 50 (full) and 15 and 20 (gentle), of 60. The undertraining flag did not trip.
  - All 24 fold records carry their arm, the exclusions sha and their own W.
- **By the score (H4a, 4,270 renders).** Arm less FTm is the ln of the J0 distance ratio on the held half, so +0.01 is about 1% worse and lower is better.
  - BKS has 38 units clustered by DI. GOAT is by item, 126 items. N12 has 27 units clustered by band. real_out is reported apart.

  | Arm less FTm | BKS | GOAT by item | N12's 27 units |
  |---|---|---|---|
  | full | +0.017 [−0.012, +0.047] | +0.005 [−0.007, +0.017] | −0.006 [−0.047, +0.036] |
  | gentle | +0.010 [−0.013, +0.033] | +0.016 [+0.005, +0.026] | −0.012 [−0.081, +0.057] |
  | real only | −0.004 [−0.013, +0.005] | +0.001 [−0.005, +0.006] | −0.006 [−0.018, +0.006] |

  - **No arm is shown better than FTm.** Gentle reads worse on GOAT by item, about 1.6%. By fold, printed beside, it is [−0.003, +0.033], and units in a fold share their models. Real only is indistinguishable from FTm.
  - **Every arm beats S,** pooled on all three sets, by about as much as FTm does. Full less S is −0.116 on BKS, −0.083 on GOAT and −0.129 on N12. On BKS clean alone every arm's interval reaches zero.
  - **Renders:**
    - BKS: 1,440 (40 units × 3 amps × 3 tags × 4).
    - GOAT: 2,580 (215 units × 3 × 4).
    - N12: 250. That is 186 arm cards with priming, plus 60 for S and FTm on the 15 units without N12 clips, plus 4 hash controls, every one held to its stored hash.
  - **Departures:**
    - GOAT's S pairs miss one unit, `item_68@35.0#amp_5`. Its label is None, so `goat_labels()` drops it. This is inherited from FTm's stored read and is negligible.
    - On W's 4 DIs, reported apart, all three arms read +0.05 to +0.10 against FTm, real only included, which shares W with FTm. That points to noise on those units.
- **The conflict rule (PR #422).** Declared after H4a and before the sitting: an arm that wins by ear but reads reliably worse by the score goes to the user, with adoption the default. It did not trigger, since no arm won by ear.
- **By ear (H4b, zero new renders).** 14 first hearings in 7 bands plus 4 repeats, five candidates each, all answered. The 8 clean cards were never heard before; the 6 crunch cards were heard on N12. The primary is the rank share over FTm, a band-clustered jackknife t, one-sided, with Holm over the three arms.

  | Row | Above, of 14 | p (one-sided) | Holm | Closeness gap |
  |---|---|---|---|---|
  | full over FTm | 7 | 0.50 | 1 | +0.14 |
  | gentle over FTm | 7 | 0.50 | 1 | +0.07 |
  | real only over FTm | 8 | 0.29 | 0.86 | +0.29 [0.00, 0.50] (90%) |
  | full over S | 12 | 0.001 | | |
  | gentle over S | 11 | 0.003 | | |
  | real only over S | 11 | 0.033 | | |
  | FTm over S | 10 | 0.058 | | |

  - **No arm is better than FTm by ear, at this size.**
    - With these clusters the page had about 24% power for a true share of 0.7, and 53% for 0.8.
    - The one-sided 95% upper bounds on the share are 0.78, 0.65 and 0.80, so a moderate gain is not ruled out.
    - Dropping the two cards marked unsure changes nothing: shares 0.50, 0.50 and 0.58.
    - Without the one card whose DI is among W's rows (Storm Of Particles), 13 cards: 6, 6 and 7 above FTm (shares 0.46, 0.46 and 0.54). Nothing changes. The H4b audit's code could not match W's DI paths, so this row was checked by hand against `read.json`.
  - **The three arms beat S,** a beside row: one-sided p 0.001, 0.003 and 0.033. They stay below 0.05 under a post-hoc Holm over the three (0.004, 0.006 and 0.033).
  - **Leans, none tested, in both directions:**
    - Every closeness gap is positive, and full has the best mean rank (2.29 against FTm's 2.86).
    - On the 8 fresh clean cards, each arm is above FTm on 5.
    - On crunch the arms are above FTm on only 2, 2 and 3 of 6.
- **The models are near-identical to this listener.**
  - The user said the page "was harder than usual" (2026-11-09, in chat). On one card they noted that the other four candidates sounded exactly the same.
  - Closeness was rated equal between arm and FTm on 8, 10 and 10 of 14 cards.
  - The repeats' rank correlation over five candidates is 0.8, 0.3, 0.9 and 0.4. S, last on both hearings in 3 of 4, lifts that figure. Over the four models alone it is 0.6, −0.4, 1.0 and −0.2.
  - The arm-against-FTm call repeats on 5 of 12 decision pairs, at chance.
  - No model was heard very close on any card. The best candidate was rated "close" on 4 of 14, "some" on 9 and "far" on 1.
- **The score against the ear.**
  - J0's order within a card reads +0.44 [+0.24, +0.63], against +0.40 for "S last", so J0 adds +0.03 [−0.22, +0.29].
  - With S left out, among the four models it reads +0.26 [−0.03, +0.55].
  - On the 8 fresh cards J0 reads 0.14, below S-last's 0.35.
  - J0's order among the four models is not shown, as in N12 (F66).
- **The audits' sentence** (FT2 is FTm). "By the score no retrained version beats FT2 and all beat S; the gentle cut reads slightly worse than FT2 on GOAT (+1.6%, by item; undecided by fold); the real-only cleaning is indistinguishable from FT2. By ear no arm is better than FTm at this size, all three beat S, the conflict rule does not trigger, and the stop rule applies; the listener cannot repeat the arm-against-FTm call, so the four models are close to indistinguishable here."
- **What it changes.**
  - **FTm stays the model,** and the clean-up ends by its declared stop rule. No more listening or training goes into data cleaning.
  - **The exclusion lists stay opt-in** (`--h4`). Nothing was deleted, and no current model reads them. So nothing is removed: FTm keeps its rows, the 19 included, and the test sets are not screened (H3 not run).
  - **Work turns to the plugin-to-real gap and the score,** as declared. By ear, the distance to the record is far larger than any difference between these models.
  - **Two lessons for the next pages:**
    1. Between near-identical models, a forced five-way rank turns ties into coin flips. For later model comparisons, a page meant to decide such a pair needs a "can't tell" answer, or paired A/B with repeats of the decision pair. This clean-up is not reopened.
    2. The next score must track the ear on distance to the record first, and order close models second. Neither is shown for J0 here: +0.03 [−0.22, +0.29] over S-last, and +0.26 [−0.03, +0.55] among the models.
- **Files:**
  - `PF/heavy/` holds `check/`, `h2/`, `h4/` and `h4-exclusions.json`.
  - `PF/ear-wide/h4/` holds H4a's N12 clips and records.
  - `PF/ear-wide/h4b/` holds `plan.json`, `key.json`, `page/` and `read.json`. The answers are builds cbe1e1c63ced and acf351166587.
  - The logs are `logs/h4.log` and `logs/h4-read*.log`.
  - Plan: [heavy-cleanup-plan.md](heavy-cleanup-plan.md).

### F69. C1a: the EQ, both drives, the compressor and the gate on top of the labels. By the score the held half beats the label by −0.205 on N12's captures (30 of 31, 9 of 9 bands); on BKS it reads −0.030, undecided (crunch −0.052 on 21 of 21). The gain needs the new controls; the gate is inert; choosing the amp beats a blind choice by −0.058. C2's budget is 200. By ear, C1a is heard closer than the label: 0.68 [0.54, 0.82] on 14 cards (phase_c1a, phase_c1a_a1, phase_c1a_ear, 10,237 + 56 renders, no training, audited)
- **What ran** ([plan](full-controls-plan.md), Amendment 2 of the [every-control plan](every-control-plan.md)).
  - **The search.** Each record's stored J0 label was the start, and the search ran on top of it. It covered the amp EQ, drive 1, drive 2, the compressor and the gate. The core knobs re-tuned with them, input gain stayed within −20 to +12 dB, and the mic types were held.
  - **Budget.** 100 evaluations, with a seeded 12-record subset run to 300.
  - **Where.**
    - N12's 31 capture units, measurement only and never training rows.
    - BKS's 40 stage-1 units, one amp each, picked on the search half.
    - BKS's 2 real_out units are reported apart.
  - **Rows.** Held half, ln(d_C1a / d_label), lower is better. 90% cluster-jackknife t intervals, by band on N12 and by DI on BKS. Band-weighted means beside.
  - **The audit.** It was done with separate code; every row below matches the stored report, by class too. Its scripts and per-record values are in the session scratchpad (`c1a-audit/`).
- **The starts.**
  - Every start was within 0.005 of `best.judge[search]`; the largest gap was 0.0037.
  - 2 N12 starts missed with the gate on, by 0.00513 and 0.00533. They matched exactly with the gate as in the label, so they ran from there (Amendment 1).
  - Starts: N12 29 gate-on and 2 gate-off, BKS 40 gate-on; none refused; no fallback label.
  - C1a's bests are the 100-evaluation incumbents, and every subset `label_300` is the 300 incumbent. Fresh and in-process renders agree within about 1e-4.
- **By the score.**

  | Row | N12 (31, 9 bands) | BKS (38, 8 DIs) |
  |---|---|---|
  | **C1a best − label** | **−0.205 [−0.319, −0.091]**; band-weighted −0.180 [−0.261, −0.099]; 30 of 31 parts, 9 of 9 bands | **−0.030 [−0.073, +0.014]**; band-weighted −0.034; 34 of 38 parts, 6 of 8 DIs |
  | clean | −0.140 [−0.222, −0.058] (22) | −0.002 [−0.102, +0.097] (17) |
  | crunch | −0.363 [−0.641, −0.086] (9); band-weighted −0.287 [−0.590, +0.017] | −0.052 [−0.077, −0.027] (21, all 21 negative) |
  | Label − S, for scale | −0.407 | −0.403 |
  | Pedals reset to the start's (all / clean / crunch) | +0.126 / +0.049 / +0.313 | +0.020 [−0.005, +0.046] / +0.004 / +0.034 |
  | EQ reset to the label's | +0.116 / +0.117 / +0.113 | +0.020 [−0.010, +0.049] / +0.016 / +0.023 |
  | Both reset | +0.222 (30 records) | +0.034 |
  | Gate reset to the start's | −0.000 | −0.006 [−0.017, +0.005] |
  | Subset: 300 evaluations − 100 | +0.013 [−0.070, +0.097] (6) | −0.074 [−0.150, +0.003] (6) |
  | Subset: 300 evaluations − label | −0.239 [−0.522, +0.044] | −0.056 [−0.103, −0.010] |

  - **What changed.**
    - The EQ moved from S's curve on 31 of 31 N12 records and 38 of 38 BKS.
    - On N12 the compressor's switch flipped on 11 records (7 on, 4 off), drive 1's on 4 (1 on, 3 off), and drive 2 was switched off once. On BKS the compressor was switched on 3 times and drive 1 off once. Drive 2's knobs moved on 19 BKS crunch records, where S already has drive 2 on.
    - The gate's threshold moved, with the gate on in the best, on 11 N12 records and on 22 BKS (+2 real_out).
  - **BKS real_out:** −0.049 [−0.260, +0.161], n = 2.
  - **Amp choice** (BKS, from the stored stage-1 labels of all three amps: chosen on the search half, read on the held half, against the mean of the three amps): −0.058 [−0.087, −0.028]; band-weighted −0.067 [−0.103, −0.032]; 35 of 38 parts. The chosen amp is the best on the held half in 28 of 38 units. Stage 0b read −0.044 the same way.
- **The gain needs the new controls.**
  - With the EQ and pedals reset, what is left of the best is no better than the label: +0.014 [−0.009, +0.036] on N12 and +0.004 on BKS.
  - By path credit over the first 100 evaluations, core-knob moves carry 43% of N12's search-half gain (59% on crunch) and 28% of BKS's. None came before the first EQ or pedal move; they are co-moves. Input gain moved on 12 of 31 N12 records against 3 of 38 on BKS.
  - The gate is inert as searched.
- **Why N12 gains more than BKS.** It reflects N12's data, not an artefact.
  - **N12's labels are weaker.** v2 is one pass, capped at 44 evaluations (32 to 42 used, median best at evaluation 33). BKS's `main_stage` labels used 52 (median best at 46.5).
    - Within N12, C1a gains most where the label gained least over S (Spearman −0.51; BKS −0.07).
    - Per amp, the label's gain over S and then C1a's: pr12 −0.19 then −0.38, ac20 −0.45 then −0.20, sw50r −0.57 then −0.05. The totals land close together, at −0.57, −0.65 and −0.62.
  - **The targets differ in kind.** N12's are noise-free NAM captures of 31 other miked rigs. BKS's are real reamps of one session.
    - N12's held half keeps 89% of the search-half gain (−0.205 of −0.229); BKS keeps 50% (−0.030 of −0.059).
    - On BKS clean, 4 of 17 records lose on the held half (up to +0.37) while gaining on the search half.
  - **N12's top three (−1.34, −0.69, −0.69) are pr12 crunch captures;** resetting the pedals costs +0.69 over pr12 crunch's 4 records (+0.91 on the three). Without them N12 reads −0.130.
  - **Reweighting N12** to BKS's amp-by-class mix leaves −0.179.
  - **So BKS is the guide for C2's training rows:** −0.03 at 100 evaluations (38 records); the 6-record subset reads −0.056 [−0.103, −0.010] at 300.
- **C2's budget is 200,** by the declared rule. The pooled median of per-record search-half ratios is 0.483, 0.703, 0.835 and 0.952 at 50, 100, 150 and 200.
  - N12 alone would give 150; BKS alone gives 200.
  - N12's apparent held-half fall with more budget is one record, `2cstca38hta`. Two EQ low-pass moves there gained 0.0007 on the search half and cost 0.26 on the held half. N12's held means are flat after 100: .217, .253, .225, .228 and .239 at 50 to 300. These series are gains, ln(d_start/d), so higher is better.
  - BKS's held means rise after 100: +.008, −.017, +.015, +.037 and +.056, as gains (higher is better).
  - On BKS, the guide for training rows, nothing supports a budget below 200.
- **Flags, carried here.**
  - **The both-reset row covers 30 N12 records.** On `cap/9w20zyf2mb#pr12` that ablation's judge is infinite on both halves. Its best had set pr12 Volume to 0, peak −48.9 dBFS.
  - **The start check covers the search half only.** On BKS Bulldozer `31_ElecGtr5aDI@300` (sw50r crunch), the gate on at −80 shifts the held half by −0.0997 while the search half matches to 0.0000. That is about −0.003 of BKS's mean.
  - **Renders: 10,237.** The shards logged 3,442 + 3,444 + 1,246 + 2,103 = 10,235. The pre-amendment crash on `cap/1xiluf3lhnm` spent 2 more (a priming render and one evaluation). That is under the drawn bound of 10,305.
  - **Output level drift.** The best's peak fell by more than 10 dB on 7 of 31 N12 records and 5 of 38 BKS, through mic levels, drive levels, amp volume and the right cab turned off. The deepest drifted bests are −52.6 dBFS (N12) and −42.5 dBFS (BKS). Separately, one BKS best sits at −59.6 dBFS, 0.36 dB above the −60 dBFS silence floor, but its label was already at −59.2. That is free to the judge, which removes level. A written preset needs its output gain set by the loudness rule, and C2 should guard the floor.
- **The audit's sentence.** "C1a searched the amp EQ, both drives, the compressor and the gate on top of the stored J0 labels for 100 evaluations, at 10,237 renders. On N12's 31 capture units (measurement only), the held half beat the label by −0.205 [−0.319, −0.091] by the score (band-weighted −0.180; 30 of 31 parts, 9 of 9 bands): −0.140 on clean and −0.363 on crunch. On BKS's 38 units it was −0.030 [−0.073, +0.014], undecided (crunch −0.052 [−0.077, −0.027] on 21 of 21; clean −0.002). The gain needs the new controls: with the EQ and pedals reset, what is left of the best is no better than the label (+0.014 on N12, +0.004 on BKS), and the gate is inert. N12's larger number reflects its data: noise-free captures of other amps, whose held half keeps 89% of the search gain against BKS's 50%, and shorter v2 labels that C1a improved most where they were weakest. BKS's number is the one to expect on C2's training rows. Choosing the amp on the search half beat a blind choice by −0.058 [−0.087, −0.028]. The declared rule sets C2's budget at 200; BKS's held half agrees, and N12's apparent fall is one record. These are J0's scores; no one has listened."
- **By ear (phase_c1a_ear, 2026-11-10; read by `c1a-ear-read`, audited against the key by hand).** One listener heard 14 first hearings and 2 repeats, all answered, label against C1a's best with ties allowed. The user found it "pretty hard to distinguish".
  - **The primary, C1a ranked above the label, a tie a half:** 0.68 [0.54, 0.82], one-sided p 0.020 (14 cards, 12 clusters). C1a was closer on 6 cards, the label on 1, and 7 were ties. **By the declared rule this is "above"**: it supports C2 on C1a's recipe.
  - **By set:**
    - N12 0.79 [0.65, 0.92], p 0.006 (4 C1a, 3 ties, 0 label);
    - BKS 0.57 [0.32, 0.82], p 0.30, undecided (2 C1a, 4 ties, 1 label), and 0.57 by song.
  - **By class:** clean 0.72 [0.60, 0.85], p 0.007 (4, 5, 0); crunch 0.60 [0.20, 1.00], undecided (2, 2, 1).
  - **Repeats:** 1 of 2 agree. The N12 repeat went from a tie to C1a closer; the BKS repeat stayed a tie.
  - **J0 against the ear:** on the 7 cards not tied by ear, J0's sign agrees on 6. The mean closeness gap is +0.21 towards C1a, on 14 cards.
  - **The listener's note on a BKS card:** C1a had too much drive and the label too little; the reference sat between them.
  - **Reading.** The ear agrees with the score where the score's gain is large (N12's captures). On BKS, where the score's gain was small (−0.030), the ear is mostly ties, as the plan's power table expected. One listener, 14 cards.
- **What it changes.**
  - By the score, the controls FT2 never sets are worth a lot on N12's captures; on BKS's reamps the gain is undecided overall and shown only on crunch (−0.052). By ear (above), C1a is heard closer on N12 and mostly tied on BKS.
  - **Labels.** The 40 BKS records are C2's first training labels for C1a's controls. C2 continues them by replaying their stored trials if its budget is above 100. The 31 N12 records stay measurement only.
  - **The amp choice** has its first real-row label (BKS).
  - **C2's budget is 200.** Its recipe is C1a's plus C1b's, with the start rule and Amendment 1's miss rule.
  - **Next, on the user's yes of 2026-11-09:** C1b (time effects, the spring, the room mics, the left cab and the mics re-searched with the EQ; the user's yes, 2026-11-09, at about 8,500 renders; the built C1b counts 8,644–9,182), and the A/B page. C2 and C3 go to the user with their costs.
- Files: `PF/c1a/` (`records.json`, `report.json`, per-record outputs), logs `logs/c1a*.log`. Code: `learn/full_controls.py`. Plan: [full-controls-plan.md](full-controls-plan.md).


### F70. C1b: the rest of the cab, the mics with the EQ, and each time effect, on top of C1a. By the score it is −0.008 on BKS [−0.017, +0.001], undecided, with 6 of 8 DIs negative; most of it sits in the records whose mic changed. On N12 it is −0.004, undecided: clean −0.012, decided by the score; crunch +0.017 from one record. All three effects it kept are false: N12's captures can't carry a delay or a tremolo. So its keep rule is not fit for labels, and C2 writes the effects off by source (phase_c1b, 8,391 renders, no training, audited)
- **What ran** ([plan](full-controls-plan.md), "C1b in detail"). Each of C1a's 71 labels was the start: N12's 31 capture units (measurement only) and BKS's 40 stage-1 units. Three stages ran on top of it, each read against C1a's fresh best on the held half, ln(d_C1b / d_C1a), lower is better:
  - **Stage A:** the rest of the cab.
  - **Stage B:** the mic types from GOAT's short lists, jointly with the amp EQ.
  - **Stage C:** each time effect on its own, kept only if its fresh render beat B's by 0.02 on the search half.
- **The run** matched the declaration (audited with separate code; every row matches the stored report).
  - All 71 starts were canonical and within 7e-5 of C1a's best; none was refused.
  - Fresh and in-process renders agree within 7e-5 dry and 0.002 wet.
  - **Renders: 8,391,** against the declared 9,070, from four savings. 33 one-cab records tried only 2 settings in stage A (−462), inert dims saved 64, and stage B's first point was cached (−71). 44 ablations equal to the final reused its render (−88). The three passing effects' fresh renders added 6.
- **By the score.**

  | Row | N12 (31, 9 bands) | BKS (37, 8 DIs) |
  |---|---|---|
  | **C1b final − C1a best** | **−0.004 [−0.014, +0.007]**; band-weighted −0.008 [−0.019, +0.002]; 20 of 31 parts, 6 of 9 bands | **−0.008 [−0.017, +0.001]**; band-weighted −0.010 [−0.020, +0.000]; 25 of 37 parts, 6 of 8 DIs |
  | clean | −0.012 [−0.020, −0.004] (22); 7 of 8 bands | −0.009 [−0.031, +0.012] (17) |
  | crunch | +0.017 [−0.006, +0.041] (9); +0.003 without `2cstca38hta` | −0.007 [−0.023, +0.009] (20) |
  | Stage A reset (positive: it helped) | +0.004 [+0.000, +0.008] | +0.002 [−0.000, +0.004] |
  | Mics and EQ reset | +0.005 [−0.004, +0.014]; band-weighted +0.008 [+0.001, +0.016] | +0.007 [−0.002, +0.015] |
  | Effects reset | −0.003 [−0.009, +0.003]; crunch −0.013 | 0 (none kept) |

  The resets are not a decomposition: on N12 they add up to more than the primary.
- **The effects kept are all false.**
  - N12 kept 3 of 31; BKS kept none, its nearest being reverb at −0.011 to −0.016.
  - No capture of an amp carries a 350 ms echo or a 2.25 Hz tremolo, so every N12 keep is wrong by construction:
    - **`2cstca38hta`, delay** (mix 0.2, 350 ms): −0.081 on the search half, +0.076 on the held half.
    - **`wji8wcrx9yf`, tremolo** at depth 0 and level 1: a level move through the tremolo's level knob (+5.8 dB peak), not a modulation. −0.027 search, +0.043 held.
    - **`4ll6kx6g6d_a2`, tremolo** at depth 0.15 and level 0.5 (+0.95 dB peak): −0.051 search and −0.028 held. J0 rewards it on both halves, whether for the modulation or the level, so a held-half check would not have caught it.
  - **So the 0.02 search-half rule gave a false effect to 3 of N12's 31 records** (3 of its 114 effect searches; 3 of 71 records and 269 searches across both sets). It is not fit for training labels as it stands.
    - **C2** writes the effects off by source. On GOAT, capture renders, that follows from the source. On BKS, real reamps, it is assumed: "kept none" under an untested rule does not show it.
    - **The effects' route to labels** stays open in C0. It needs a keep rule tested on a source whose effects are known, such as W's plugin rows.
- **Where the gain comes from.**
  - **On BKS, most of it sits in the 17 records whose mic changed** (a split made after the run, with no interval). Their mics-and-EQ reset reads +0.016, against −0.001 on the 20 unchanged. The pooled reset is undecided, +0.007 [−0.002, +0.015]. The changes agree across sections of the same reamp, mostly to mic 9. Three of the 17 (−0.035, −0.019, −0.011) are near-silent pr12 labels with Volume 0 (−49 to −57 dBFS); the failed record below is a fourth such mic change.
  - **On N12 the stage A reset (+0.004) is about as large as the mics-and-EQ reset (+0.005).**
  - **Stage A was mostly the left cab's balance.** 34 of 38 two-cab records moved it, 4 to the +6 dB cap; 3 N12 records turned it off. The phase flipped on 0 of 38.
  - **The rooms were barely tested.** On the 33 one-cab records stage A tried one setting, the left room on at −6 dB. Room levels were searched only where a room went on (one record; its whole stage A reset, the left cab's level move included, reads −0.008). The rooms stay open in C0 for a real test.
  - **On N12 the search-half gain barely carries over:** 20% kept, Spearman 0.17. BKS keeps 68%, Spearman 0.51.
  - **N12's crunch loss is one record.** On `2cstca38hta` the false delay costs +0.076 on the held half, and stage B's best reads +0.064 against stage A's in process, on a search gain of 0.0002. Its two halves score 3.4 and 5.6–6.0 apart. The same record broke C1a's 300-evaluation row (F69).
- **Flags.**
  - **One BKS record is a C1b failure, left out of the primary:** Bulldozer `22_ElecGtr2aDI@290 #24` (pr12).
    - C1a's label already peaked at −59.6 dBFS, with pr12 Volume 0 inherited from the stored label.
    - Stage B's mic and EQ move gained 0.0035 on the search half. It left a −59.9 dBFS render that J0 refuses on the held half.
    - Its two "non-finite ablations" are that render reused. Its label is still written: the fallback check is `SILENT_DBFS` −60 on the search half only, and the final sat at −59.85. It is kept out of C3's rows.
    - **C2's rule:** a stage's best that is non-finite on either half when rendered fresh, or peaks within 3 dB of the silence floor, falls back to the previous stage's best (declared in C2). That would not catch the labels between −57 and −49 dBFS, which J0 still scores.
  - **Other near-silent labels come from C1a:** BKS −57 to −49 dBFS, N12 −52 and −51. 5 of the 6 near-silent labels share one cause, pr12 Volume 0 inherited from the stored label. The drift flag counts change from the start, so it can't see them. A written preset needs its output set by the loudness rule.
  - **BKS real_out:** +0.004, n = 2, reported apart.
- **What it changes.**
  - **C1b's labels are C3's** for the 40 BKS records, except the failed one; the 2 real_out ones as H4's exclusions decide. With effects off, their knob heads are masked in C3: a label that is always off on dry rows teaches only "off". (C1b's `searched_union` lists every effect knob, so C3 must not use it as the mask.) C2 continues these 40 to its budget. N12 stays measurement only.
  - **C2 keeps stages A and B and drops stage C,** writing effects off by source, with the fallback rule above.
  - **Still open in C0** (the table is updated with C2's declaration): the effects' labels (a keep rule tested on a source with known effects) and the room mics (a real test).
  - By ear, C1a was later heard closer than the label (F69); C1b itself was not heard.
- Files: `PF/c1b/` (`records.json`, `report.json`), per-record outputs in `PF/captures2/search-c1b/` and `PF/real/search-c1b/`, logs `logs/c1b*.log`. Code: `learn/full_controls_c1b.py`. The audit's scripts are in the session scratchpad (`recompute.py`, `decomp.py`).

### F71. C2: every searched control on all 520 of FT2's real training rows. By the score, on the held half, the labels beat their start (the stored label) by −0.208 on GOAT (121 of 126 items), by −0.108 on BKS stage 1 and −0.129 on stage 2, and by −0.056 on C1a's 40, which were already searched to 100 evaluations (6 of them to 300). All of them sit far below S. Nothing was refused or fell back. 72 labels ended more than 10 dB quieter than their start, and 90 can't reach a −12 dBFS peak through the output control alone, so the loudness step needs a second lever (phase_c2, 131,545 renders, no training, audited)
- **What ran** ([plan](full-controls-plan.md), "C2 in detail"). On each of FT2's 520 real training rows (GOAT 214, BKS stage 1 80, stage 2 186, and C1a's 40 last):
  - **Step 1:** C1a's search from the stored label, at budget 200.
  - **Step 2:** C1b's stages A and B, the rest of the cab and then the mics with the amp EQ.
  - No effect stage: the effect, spring and doubler switches are written off by source. Then one fresh render of the final.
  - The read is ln(the label's fresh render / the start's first evaluation) on the held half, lower is better.
  - 28 records were left out at the draw, as declared: GOAT 16 by the one-window lag rule, 2 with no lag and 1 silent fallback; BKS stage 2 the 9 lag-refused.
- **The run matched the declaration.** It was audited with separate code. Every primary, against-S and against-stored-label row, in every block, part and class, reproduces the stored report to 2e-16.
  - **520 of 520 labels were written.** None was refused, fell back or has no label, and none has a non-finite final.
  - **Starts.**
    - 506 starts passed the 0.005 log check at once.
    - 14 GOAT starts took Amendment 1's path: they missed with the gate on, matched with the gate as stored, and ran from that.
    - All 40 replays of C1a's block were exact. The 34 stored at 100 evaluations each had a start check, and all passed. The 6 that ran to 300 in C1a rendered nothing in step 1: their step 1 is C1a's stored evaluations to 200.
    - Every step 2 start was canonical.
  - **Fresh and in-process renders** of the final agree within 0.0002 on all 520.
  - **Every label is dry:** no time effect, spring or doubler is on.
  - **The near-silent guard** took a constrained best 11 times in step 1 and 3 times in step 2, and never failed a peak at step 2.
  - **Renders: 131,545,** against at most 134,788.
- **By the score** (held half; record-weighted 90% cluster-jackknife intervals, clustered by DI or GOAT item; real_out apart).

  | Block | Against the start | Clean | Crunch | Against S | Step 1 at 100 / at 200 |
  |---|---|---|---|---|---|
  | GOAT (197, 126 items) | **−0.208 [−0.231, −0.185]**; item-weighted −0.213, 121 of 126 negative | −0.204 (110) | −0.213 (87) | −0.518 | −0.158 / −0.181 |
  | BKS stage 1 (76, 8 DIs) | **−0.108 [−0.172, −0.045]**; DI-weighted −0.135, 7 of 8 | −0.058 [−0.189, +0.073] (34), undecided | −0.150 [−0.259, −0.040] (42) | −0.421 | −0.085 / −0.101 |
  | BKS stage 2 (186, 6 DIs) | **−0.129 [−0.159, −0.100]**; DI-weighted −0.142, 6 of 6 | −0.149 [−0.812, +0.514] (15, 2 DIs), undecided | −0.128 [−0.161, −0.094] (171) | −0.508 | −0.099 / −0.119 |
  | C1a's 40 (38, 8 DIs) | **−0.056 [−0.094, −0.018]**; DI-weighted −0.061, 7 of 8 | −0.049 [−0.157, +0.058] (17), undecided | −0.062 [−0.086, −0.038] (21) | −0.462 | −0.027 / −0.051 |
  | real_out (GOAT 17, BKS 6) | GOAT −0.217 [−0.261, −0.172]; BKS stage 1 −0.100 (4), C1a's −0.069 (2) | | | | |

  Against the stored label's stored score, the rows differ from these by at most 0.007.
- **Where the gain came from** (differences of the rows' means, no intervals):
  - **GOAT:** −0.158 by evaluation 100, −0.023 more by 200, and −0.027 from stages A and B.
  - **BKS stages 1 and 2:** −0.085 and −0.099 by 100, −0.016 and −0.020 more by 200, and −0.007 and −0.010 from A and B.
  - **C1a's 40:** their −0.027 at 100 is C1a's own reading. The continuation to 200 adds −0.024, and A and B add −0.005.
  - **C1a's 40 gain less than the other BKS records at the same checkpoint** (−0.027 against −0.085 and −0.099 at 100), on the same recipe. That follows from a selection. By C1a's draw rule each is its unit's best amp by the stored label's search half, and the other 80 stage-1 records are the same 40 units' other two amps. Paired by unit, C1a's records start closer to the target (−0.398 against S, against −0.313) and gain −0.028 at 100, against −0.084.
- **What changed, over all 520:**
  - Any pedal on in 354 labels, against 283 starts. The compressor was turned on in 175 (GOAT 64, BKS 108, C1a's 3) and off in 23, so it is on in 207 labels, against 55 starts. GOAT's capture renders carry no compressor by construction, and BKS's reamps are assumed to carry none, as the plan assumes them dry. So these are sound-alike settings by the score, not the rig's truth.
  - The mic changed in 204.
  - A room went on in 45 labels (59 rooms; no start had one), and the left cab went off in 9.
  - The phase flipped in 2.
  - The gate threshold moved in 255.
- **The output level.**
  - **72 of 520 labels ended more than 10 dB quieter than their start:** GOAT 31, BKS stage 1 10, stage 2 24, C1a's 7. 43 are more than 20 dB quieter, and the largest drop is 52.6 dB.
  - **Step 1 made it:** 68 of the 72 were already more than 10 dB down at step 1's best. Step 1 drifts them 25 dB on average, and step 2 adds 0.8. Over the 72, the search changed an amp's volume, level or power in 45 labels (41 without ac20 Power), a cab mic's level (left 32, right 40) or the input gain (28). It turned the right cab off in 10.
  - **pr12 Volume is 0 in 43 labels.** 31 of their starts already had it, so 12 went to 0. 7 of the 38 pr12 starts at 0 moved off it.
  - **29 labels are flagged quiet,** below −50 dBFS.
  - **The output control alone can't make up the rest.** `parameters/outputGain` spans −24 to +24 dB (`full_space.OUTPUT_RANGE`). At +24:
    - 90 of the 520 labels still peak below −12 dBFS, and 62 below −20 dBFS. −12 dBFS is a yardstick for this count, not a declared target.
    - 99 can't get back to their own start's peak, 94 of them by more than 0.5 dB.
    - 57 of the 78 labels under −30 dBFS are pr12.
  - **Part of it is older than C2.** 49 of the 520 starts (the stored labels FTm trained on) already peak below −12 dBFS at +24, and 40 below −20. 43 of the 90 short labels did not drift by more than 10 dB. So C2 took the count from 49 to 90, and the shortfall sits in FTm's labels too.
  - **The cab mics close few.** Raising every active cab and room mic level together until the highest reaches +6 dB keeps the blend, and so the tone if the cab is linear. It brings 11 of the 90 to −12 dBFS. 30 are already at +6, and the other 79 stay a median 14 dB short. So most need the amp's volume, which changes the tone, or a reported shortfall.
  - **The quieter labels gain more by the score.** A split made after the run, with no interval: the 43 labels more than 20 dB down read −0.233 on average, against −0.146 for the 448 not more than 10 dB down. By block:

    | Block | More than 20 dB down | Not more than 10 dB down |
    |---|---|---|
    | GOAT | −0.339 (14) | −0.198 (183) |
    | BKS stage 1 | −0.144 (5) | −0.108 (70) |
    | BKS stage 2 | −0.233 (18) | −0.118 (162) |
    | C1a's 40 | −0.057 (6) | −0.070 (33) |

    The drift comes from step 1's amp, pedal and input controls, which leans to a real tone effect such as a lower amp volume, but does not settle it. At zero renders this can't tell a closer tone at low volume from J0's handling of level near its floor. An ear read of such labels would tell them apart.
  - **A correction.** C2r's block said "31 of GOAT's 214 labels drifted 20 to 50 dB quieter". The 31 are the labels more than 10 dB quieter; 14 of them are 20 to 48 dB quieter. It is corrected there.
- **The held half got worse on 17 of 520 labels,** by more than +0.03:
  - GOAT 6 and BKS 11. 10 of BKS's 11 are on TooMuch, 5 of them on `16_ElecGtr1aDI` (both windows; @15 on all three amps, up to +0.474).
  - They train as declared. A search that picks on one half is expected to overfit it on some records.
- **What it changes.**
  - **C3 trains on these labels as declared** (started 2026-11-11 06:25). Nothing here calls for a change to its declaration.
  - **C2b, C2r and C3r follow in order.** C2r labels its 170 new records with the same recipe, so the same level drift may show there.
  - **The loudness step must be declared with a second lever before any preset ships.** At +24 dB of output, 90 of C2's 520 labels and 49 of FTm's stored ones stay below −12 dBFS. The cab mics close 11 of the 90. So the lever is the amp's volume, which changes the tone, or the product reports the shortfall. The declaration also sets its own yardstick, against something measured on the same DI (S's peak, or the factory presets'). The C0 output-gain row carries this.
  - **By the score only, and a risk for C3's adoption.** C3 is kept unless shown worse by J0, the judge that chose these labels, and the labels that dropped most in level gain most by it. If that comes from J0's handling of level rather than tone, C3's read can't see it. So C4's declaration should put a few of the 43 most-drifted labels on its blind page, level-matched against their start.
- Files:
  - `PF/c2/` (`records.json`, `report.json`);
  - per-record outputs in `PF/goat/search-c2/` and `PF/real/search-c2/`;
  - logs `logs/c2*.log`.
  - Code: `learn/full_controls_c2.py`. The audit's scripts (`recompute.py`, `a3.py` to `a6.py`) are in the session scratchpad.

### F72. C3: FTm's recipe retrained on C2's every-control labels. By the score the adopted model reads level with FTm: BKS +0.001 [−0.057, +0.058], GOAT +0.005 [−0.019, +0.028], N12 −0.032 [−0.122, +0.059], all undecided. It learns the EQ, the pedals and the gate, with the rest of the cab at S. It stays 10% closer than S. The EQ carries −0.039 on GOAT, but C3's core reads +0.034 worse than FTm's there, so the two cancel and the isolation run C3i is due. By the declared rule the adopted model replaces FTm, and C4 can reverse it (phase_c3, 71 min of MPS, 8,442 renders, audited)
- **What ran** ([plan](full-controls-plan.md), "C3 in detail").
  - **The training:** FTm's recipe on FTm's 520 real rows, every one with its C2 label (none fell back), and per-record masks of `K.space` ∪ C2's searched keys (40 to 50 keys a record). That is 8 inner runs, 8 FT_k and the all-labels pair, seeds 20261042 and 20261043, in 71 minutes of wall clock with two runs at a time (124.0 run-minutes, against FTm's 135.7). E was 48 to 74 by fold and seed, and the all-labels pair took the median, 57.
  - **The read, as H4a:** six tags on BKS (40 units × 3 amps, by DI fold), GOAT (215 units on their own amp, by item fold) and N12 (pooled, measurement only). Each answer comes from the search half and is judged on the held half: ln(d_tag / d_FTm), lower is better.
  - **The tags:**
    - C3, every trained key as answered;
    - C3 core, every trained key outside `K.space` at S;
    - one tag for each family at S: EQ, pedals, gate threshold, cab rest.
  - **Renders: 8,442,** as declared: BKS 2,880, GOAT 5,160, N12 378 and the hash check 24. Each answer is rendered twice, once to prime its process and once to keep.
- **The run matched the declaration.** It was audited with separate code: BKS's and GOAT's rows for C3, the adopted tag, C3 core, the EQ and the rest of the cab, against FTm, reproduce the stored adoption record to 1e-4.
  - Training: no NaN or failure in any of the 18 runs. Each run records C2's sha256 (661dc9a7). Before training, C3 core's hold equalled `hold_outside_space` on 98 of 98 stored answers, and no untrained key left S.
  - FTm's 12 hash-check renders matched (12 of 12), so FTm's stored scores are the comparator.
- **By the score.**

  | Row | BKS (8 DIs) | GOAT (130 items) | Pooled | N12 (8 bands, measurement) |
  |---|---|---|---|---|
  | **Adopted (C3, rest of the cab at S) − FTm** | **+0.001 [−0.057, +0.058]** | **+0.005 [−0.019, +0.028]** | **+0.003 [−0.028, +0.033]** | −0.032 [−0.122, +0.059] |
  | C3 − FTm | +0.001 [−0.056, +0.058] | +0.006 [−0.017, +0.029] | +0.003 [−0.027, +0.034] | −0.029 [−0.121, +0.063] |
  | C3 − S | −0.122 [−0.210, −0.034] | −0.088 [−0.120, −0.057] | −0.105 [−0.151, −0.059] | −0.152 [−0.329, +0.025] |
  | C3 core − FTm | −0.002 [−0.031, +0.027] | **+0.034 [+0.021, +0.046]**, 49 of 130 items negative | +0.016 [+0.000, +0.032] | +0.005 [−0.023, +0.033] |

  The family rows are C3 − (C3 with that family at S), so a negative row means the learned family helps:

  | Family | BKS | GOAT | Pooled | Verdict |
  |---|---|---|---|---|
  | EQ | −0.004 [−0.018, +0.010] | **−0.039 [−0.048, −0.029]**, 97 of 130 | −0.021 [−0.029, −0.013] | kept: it helps |
  | Pedals | +0.012 [−0.024, +0.048] | +0.008 [−0.012, +0.027] | +0.010 [−0.010, +0.030] | kept: undecided |
  | Gate threshold | −0.003 [−0.008, +0.002] | +0.001 [−0.004, +0.006] | −0.001 [−0.004, +0.003] | kept: inert, as expected |
  | Rest of the cab (left cab, rooms, right cab's phase) | +0.0003 [−0.001, +0.002] | **+0.0014 [+0.0007, +0.0020]** | +0.0008 [−0.0000, +0.0017] | shown worse on GOAT: at S |

- **What it means, by the score.**
  - **Learning every control is so far level with FTm, not ahead of it.** On GOAT, given C3's learned core, the EQ's −0.039 offsets C3's own core, which reads +0.034 worse than FTm's. The split depends on the order the families are set to S: C3 − C3 core reads −0.028, and the four family rows sum to −0.028. On BKS neither moves.
  - **The core's loss has two candidate causes, and the read can't separate them.**
    - C2's core labels were searched jointly with the EQ and the pedals, so alone they may be the wrong core values.
    - Or the wider objective (about 2.5× more dims, the mixture shaped by the EQ's 11) teaches the core heads less well.
    - The declared isolation, C3i, separates the two: FTm's mask on C2's labels. It is declared below in the plan.
  - **The rest of the cab is shown worse by 0.14% on GOAT,** and goes to S. Its labels barely searched the rooms (F70), so the rooms stay open in C0 regardless.
  - **The pedals read +0.010, undecided.** By the keep rule they stay. Their labels turned the compressor on in 175 of 520 records (F71), and the read leans, without showing it, toward S's "off".
  - **The amp pick** (W's amp head on C3's body, masked on real rows) reads −0.027 [−0.070, +0.016] against a blind choice on BKS, undecided. The amp head's real-row training is C3b's, after C2b.
  - **N12:** C3 is 0.49 [0.30, 0.67] from its own C1b labels, so the model sits far from the labels, as FTm did. On the 2 bands whose DIs W trained on (read apart), every tag reads about +0.13 against FTm.
- **What it changes.**
  - **By the declared rule, the adopted model replaces FTm** as the product candidate, since it is not shown worse than FTm. That model is C3 with EQ, pedals and gate learned, and the rest of the cab at S. C4's blind page can reverse it (PR #422's rule). C5 runs on it.
  - **C3r trains on C3's recipe,** so the core question bears on it too. C3i runs before C3r's read is interpreted.
  - **C0:** the EQ, the pedals and the gate threshold are learned; the rest of the cab is written at S, and the rooms stay open with their blocker (a real test).
  - **By the score only.** C4 is the ear check.
- Files:
  - `PF/c3/` (`check.json`, `recheck.json`, `adoption.json`, `decision.json`);
  - the reports `PF/real/report-c3.json` and `PF/goat/report-c3.json`;
  - the per-record scores in `PF/real/judge/C3-*` and `PF/goat/judge/C3-*`;
  - logs `logs/c3-*.log`, `logs/c3-n12.json`, `logs/c3-n12-c1b.json`, `logs/c3-amp.json`.
  - Code: `learn/full_controls_c3.py`, `pipeline_fix train-ft --c3`. The audit script (`c3re.py`) is in the session scratchpad.

### F73. C2b: amp choice on GOAT. By the score, picking each unit's amp by its labels' search half reads −0.054 [−0.063, −0.044] against a blind pick on the held half, on 119 of 130 items; GOAT's forced amp reads −0.001, no better than blind. But on BKS the amp a label picks depends on the label's recipe: the stored labels and C2's agree on 51 of 102 units. So GOAT's C2b amp labels, made with the stored recipe, are not like for like with BKS's C2 labels, and C3b must choose before it trains (phase_c2b, 22,684 renders, no training, audited)
- **What ran** ([plan](full-controls-plan.md), "C2b in detail").
  - Each of GOAT's 214 labelled units was searched on its two other amps: 428 records, with the stored labels' own recipe (`K.space` main stage, 52 evaluations, seed 20261013, from the class's S, the unit's stored halves and lag).
  - The unit's amp label is the argmin over its three like-for-like labels of the search half, counting labels that peak at −57 dBFS or above.
  - The read, at zero renders: the chosen amp's held half (ln) less the mean over the usable amps, clustered by item.
- **The run matched the declaration.** It was audited with separate code: all 214 choices and both rows reproduce the report to 1e-4.
  - 428 of 428 written, with none refused. Every start was bit-identical to the stored S render.
  - 1 search fell back: `item_169@15.0#amp_5` on pr12, whose best peaked at −60.6 dBFS.
  - 4 labels are quiet below −57 dBFS: 3 of C2b's and the stored `item_1@25.0#amp_4`.
  - **Renders: 22,684,** exactly the declared maximum: 428 × (1 priming + 52).
  - Under the −54 dBFS sensitivity check, 1 unit's choice changes.
- **By the score.**

  | Row | All (214 units, 130 items; forced: 213 with a usable forced amp) | Clean | Crunch |
  |---|---|---|---|
  | **Chosen amp − blind** | **−0.054 [−0.063, −0.044]**, 119 of 130 items; part-weighted −0.055 | −0.051 [−0.060, −0.041] | −0.059 [−0.074, −0.044] |
  | Forced amp − blind | −0.001 [−0.013, +0.011] | −0.009 [−0.022, +0.003] | +0.003 [−0.016, +0.022] |

  - The choice is the forced amp in 73 of 214 units (34%), about a third, as a blind pick would be. It is the held half's best in 153 (71%).
  - The choices: sw50r 109, ac20 78, pr12 27. pr12 is chosen least whatever the forced amp: 9, 8 and 10 of the forced ac20, pr12 and sw50r units.
  - GOAT's forced amp is the dataset's own assignment, and it reads as blind, so GOAT's rows give no amp information without C2b.
- **The declared check for C3b, at zero renders: the amp label moves with the recipe.** On BKS (102 units, all three amps labelled twice), the argmin over the stored 52-evaluation `K.space` labels and over C2's every-control labels agree on 51 of 102 units (50%).
  - The stored labels pick sw50r on 78, pr12 on 18 and ac20 on 6.
  - C2's labels pick pr12 on 48, sw50r on 40 and ac20 on 14. With every control searched, pr12 fits about as often as sw50r.
  - **51 of 102 is near chance.** Within one recipe, the search half's and the held half's argmin agree on 85 of 102 (stored) and 79 of 102 (C2). Chance agreement from the two recipes' shares is 40. No subset escapes it: by C2's search-half margin between its best two amps, the thirds agree on 12, 18 and 21 of 34. By class: clean 10 of 22, crunch 41 of 80. With C2's own near-silent bound instead of −57 dBFS, 50 agree.
  - **The amp choice is worth about half as much under C2's labels.** On BKS, the stored choice read on the stored labels is −0.063 [−0.091, −0.036] against blind. On C2's labels (held half, 8 DIs), C2's own choice reads −0.031 [−0.049, −0.013] and the stored labels' choice −0.022 [−0.036, −0.007]. So under every-control labels the amp's ceiling is nearer 3% than 6%.
  - **The price of the recipe.** The stored choice less C2's choice, both read on C2's labels, is +0.009 [−0.012, +0.030], undecided. That is all that relabelling on C2's recipe could buy over the stored recipe's choice, on BKS.
- **What it changes.**
  - **GOAT now has amp labels.** On its stored-recipe labels, choosing the amp is worth about 5% by the score, as the stored recipe's choice is on BKS (−0.063; F69's −0.058). Under C2's every-control labels it is worth about 3% on BKS.
  - **But GOAT's amp labels come from the stored recipe,** while BKS's would come from C2's, and the two pick different amps half the time. An amp head trained beside C3's every-control heads would learn two recipes' answers.
  - **C3b is declared separately and goes to the user first.** It must choose the amp labels' recipe. The options:
    1. GOAT's C2b labels as they are, beside BKS's C2 argmin. Zero renders, but two recipes.
    2. Both sets on the stored recipe, with BKS's stored argmin. Zero renders and like for like, but not C3's recipe.
    3. C2's recipe on GOAT's other two amps. This is like for like with C3, but costs about 112k renders: C2's GOAT records took 263 each (253 to 271), so at most about 116k. That is about 10 h if 5 processes scale fully, 14 h at 8,100 an hour, or 17 h on 3, after C2r and the reads already queued. On BKS it would gain about 0.009 over option 2's choice (the stored choice reads +0.009 worse, undecided).
    4. BKS's C2 argmin alone, with GOAT's amp rows masked. Zero renders and like for like, on 8 DIs and 2 songs.
  - **The amp head itself** is the larger open question. C3's amp pick (W's head on C3's body, untrained on real rows) reads −0.027 [−0.070, +0.016], undecided (F72).
  - By the score only.
- Files:
  - `PF/c2b/` (`records.json`, `report.json`);
  - the per-record outputs in `PF/goat/search-c2b/`;
  - logs `logs/c2b*.log`.
  - Code: `learn/full_controls_c2b.py`. The audit scripts (`c2bre.py`, `c3bcheck.py`) are in the session scratchpad.

### F74. C3b, stage 1: the amp head trained on real rows. By the score its pick beats W's by −0.027 [−0.042, −0.011] pooled, the declared "learns", and reads −0.047 against a blind pick. But it picks the sw50r on 218 of the 254 read units, and always picking the sw50r reads the same: C3b less always-sw50r is +0.002 on BKS and +0.003 on GOAT, both undecided. Its 36 other picks read worse than the sw50r would. So it learned the labels' commonest amp, not each recording's. On the labels, picking per recording is worth −0.025 on GOAT's clean units and nothing on crunch; on C3's own BKS answers it is worth about −0.09 on both, and the labels don't point to it. Stage 2 is declared (phase_c3b, 39 min of MPS, zero renders, audited)
- **What ran** ([plan](full-controls-plan.md), "C3b in detail").
  - **The recipe:** C3's, with every real row taking its unit's amp label in the amp head's slot. The labels are the stored recipe's argmin: GOAT's 214 from C2b, BKS's 102 over its three stored labels.
  - **The training:** 8 FT_k, each for C3's own inner run's E (48 to 74 epochs), and the all-labels pair at 57. It took 39 min of MPS (14:45 to 15:24), beside C2r's 5 render shards. C2r's rate went from 11,292 to 10,842 an hour (−4%), inside the 20% stop.
  - **The read:** zero renders, under a minute of CPU. Each read unit's pick comes from the FT_k that held it out, on the labels' search half, and is valued on the labels' held halves (C2b's yardstick).
- **The read matched the declaration.** It was audited with separate code: every row below reproduces the report to 1e-4. The independent review recounted all 14 numbers, the picks and C3's own BKS renders with its own code.
  - The units: BKS's 40 (8 DIs) and GOAT's 214.
  - No C3b pick lacked a usable label; W's had 2 on each set, scored as the worst usable amp.
- **By the score** (each pick's held half, ln, less the mean over the unit's usable labels; clustered by DI or item; pooled with C3's equal weights):

  | Pick, against a blind pick | BKS (40 units) | GOAT (214 units) | Pooled |
  |---|---|---|---|
  | W (C3's head, untrained on real rows) | −0.027 [−0.077, +0.024] | −0.013 [−0.025, −0.002] | −0.020 [−0.046, +0.006] |
  | **C3b** | **−0.050 [−0.093, −0.006]** | **−0.044 [−0.054, −0.033]** | **−0.047 [−0.069, −0.024]** |
  | **C3b − W (the declared reading)** | −0.023 [−0.050, +0.005] | **−0.030 [−0.047, −0.014]** | **−0.027 [−0.042, −0.011]** |
  | Always the sw50r | −0.051 [−0.094, −0.008] | −0.047 [−0.057, −0.036] | −0.049 [−0.071, −0.027] |
  | C3b − always the sw50r | +0.002 [−0.001, +0.004] | +0.003 [−0.001, +0.007] | +0.002 [−0.000, +0.005] |
  | The labels' own argmin (the ceiling) | −0.063 [−0.097, −0.029] | −0.054 [−0.063, −0.044] | −0.058 [−0.076, −0.041] |

  - **By the declared rule, stage 1 reads "learns":** better pooled and on GOAT, worse nowhere. Against blind it is better on all three.
- **The audit: what it learned is the prior.**
  - **The picks.** C3b picks the sw50r on 38 of 40 BKS units and 180 of 214 GOAT units. W picks it on 24 and 107, and the pr12 on 16 and 55. The labels' argmin is the sw50r on 28 of BKS's 40 and 109 of GOAT's 214.
  - **Its other picks are worse than the sw50r.** BKS's 2 read +0.058 worse than the sw50r on the same units, and neither is better. GOAT's 34 (31 ac20, 3 pr12) read +0.025 worse, better on 12 of the 34. Only 7 of the 34 are the labels' own argmin.
  - **Its amp loss on held rows is no lower than a constant guess.** The held rows' loss is 0.78 to 1.34 (mean 0.98). The entropy of the labels' shares is 0.97 on GOAT and 0.68 on BKS's stored labels. A head that read the audio would sit below that.
  - **The review's tests, on the read units out of fold, all find nothing beyond the prior:**
    - **Log loss:** C3b's is worse than its own mean probabilities used as a constant: 1.081 against 0.982 on GOAT, 1.003 against 0.849 on BKS. Its spread across units adds loss. W does the same, at 1.111 against 1.074.
    - **Ranking:** on GOAT, units labelled an amp get no higher probability of it. All three AUCs are 0.47 to 0.56, every interval covering 0.5, and the same within each class.
    - **The gap's size:** the head's lean to the sw50r doesn't track how much better the sw50r reads on the held half: rank correlation −0.02 [−0.14, +0.10] on GOAT, −0.24 [−0.55, +0.19] on BKS.
    - **The other picks hit the label less often than chance:** 7 of 34 against 11.7 expected; on crunch 1 of 19 against 4.8.
    - **The training curves:** the held amp loss is lowest early (epoch 2 to 6 on folds 2 and 3, 19 to 52 on folds 0 and 1), then rises while the training loss falls from about 1.0 to 0.66–0.75. The head learns the prior fast, then memorises the training rows.
  - **On the plugin rows the training holds out** (its `ns` monitor, used for no choice here) its amp loss is 1.25 to 1.55. W's head reads 1.08 to 1.13 there, about ln 3 (1.10), a uniform guess. So W's own pick was near a coin toss, with a lean to the sw50r and away from the ac20.
  - **On C3's own per-amp renders** (BKS, C3-cabS's settings on all three amps, both halves), against blind: W −0.028 [−0.070, +0.015], C3b's pick −0.055 [−0.101, −0.009], always the sw50r −0.049 [−0.102, +0.004], always the ac20 −0.003, always the pr12 +0.052. So with every control set by the model, the sw50r is still the best single amp on BKS, and the pr12 the worst.
- **What it means.**
  - **By the score the sw50r is the best single amp for these sets, and training finds it.** The product's pick would move from W's near coin toss to nearly always the sw50r: about −2.7% pooled on the labels, −2.7% on C3's own BKS renders.
  - **Picking the amp per recording is not learned. On the labels' yardstick the loss is on clean recordings** (the review's split, recounted; against blind, on the labels' held halves):

    | Set, class | Always sw50r | Always ac20 | Labels' argmin | Argmin − always sw50r | C3b − always sw50r |
    |---|---|---|---|---|---|
    | GOAT clean (110 units, 84 items) | −0.026 | −0.024 | −0.051 | **−0.025 [−0.035, −0.015]** | −0.004 [−0.011, +0.002] |
    | GOAT crunch (104, 81) | −0.063 | −0.004 | −0.059 | +0.005 [−0.017, +0.026] | **+0.010 [+0.004, +0.016]** |
    | BKS clean (17, 4 DIs) | −0.009 | **−0.029** | −0.031 | −0.022 [−0.068, +0.025] | +0.000 |
    | BKS crunch (23, 4 DIs) | −0.093 | +0.018 | −0.095 | −0.003 [−0.007, +0.002] | +0.003 [−0.004, +0.010] |

    - **The sw50r's lead is a crunch effect.** On crunch, always picking it sits at the ceiling, and C3b's departures from it are shown worse on GOAT.
    - **On clean it isn't.** On GOAT the sw50r only ties the ac20, and picking per recording is worth a further −0.025, shown better. On BKS's 4 clean DIs the ac20 reads better than the sw50r.
    - Pooled over classes, the per-recording value reads −0.010 (GOAT) to −0.014 (BKS) beyond C3b's pick, and that average hides the clean gap.
  - **On the model's own answers it is different** (the re-check, recounted; C3-cabS's own BKS renders on all three amps, 80 directions on 8 DIs):

    | Row | All | Clean (4 DIs) | Crunch (4 DIs) |
    |---|---|---|---|
    | Each unit's search-half argmin − always sw50r | **−0.093 [−0.132, −0.053]** | **−0.059 [−0.097, −0.022]** | **−0.126 [−0.203, −0.049]** |
    | The labels' argmin amp − always sw50r | **+0.055 [+0.002, +0.109]**, worse | **+0.112 [+0.018, +0.205]**, worse | −0.001 [−0.008, +0.005] |

    - **With the model's own settings the amp matters about 9% by the score,** on both classes, against about 1% on the labels.
    - **The stored labels don't point to it.** The label's amp is the held half's best in 31 of 80 directions, about chance, and with C3's settings it reads worse than always the sw50r, most of all on clean.
    - So even a perfect head on these labels would miss this headroom, and on BKS's clean recordings would read worse than the sw50r. This is 8 DIs; stage 2 reads the same rows on GOAT's 215 units.
    - **The next amp route is weighed on stage 2's rows,** on the product's own answers, in the user's clean/crunch scope. If GOAT confirms BKS, the target is the amp that suits the model's own answer (the argmin of its own per-amp renders on the training units), not the amp a full search fits best. That goes to the user, explained, before anything is proposed.
  - **The lean may be the labels' recipe.** These are stored-recipe labels, `K.space` only. Under C2's every-control labels the pr12 fits BKS as often as the sw50r (48 against 40, F73). C3's own renders, with every control the model sets, still favour the sw50r on BKS as a single amp. Stage 2 reads C3b's full answer on all three amps, on both sets.
  - **The lean may be J0's.** "By the score" is not "by ear". C4's blind page is where a sw50r-heavy product is heard.
- **Stage 2 is declared next** ([plan](full-controls-plan.md), "C3b stage 2 in detail"). It renders C3b's answers and the adopted C3's on all three amps, on both sets: 5,640 renders. It reads C3b's full answer (its pick, its settings) against C3's (W's pick, C3-cabS's settings), split into the pick alone and the settings alone, by C3's adoption rule, and by class. Beside, from the same renders: always the sw50r on each model, and each model's settings amp by amp.
  - **Adopting C3b would adopt a learned constant,** the labels' majority amp. By the score that is about 2 to 3% better than W's near coin toss, mostly on crunch. On clean, the per-recording choice is worth about 2.5% and stays unlearned.
  - The C3b declaration said about 2,400 renders. GOAT's read rendered only each unit's forced amp, so reading any pick on GOAT needs the other two amps for both models.
- Files:
  - `PF/c3/c3b-stage1.json`;
  - C3b's answers in `PF/real/answers/C3b.json` and `PF/goat/answers/C3b.json`;
  - its runs `C3b-ftm-*`;
  - logs `logs/c3b*.log`.
  - Code: `learn/full_controls_c3.py` (`c3b-rows`) and `pipeline_fix train-ft --c3b`. The audit scripts are in the session scratchpad.

### F75. C3i: FTm's recipe and mask on C2's labels, the isolation of C3's core. By the score both causes cost the core. C2's core labels alone read +0.028 [+0.016, +0.040] worse than FTm's on GOAT (BKS −0.010, undecided), and C3's wider training adds +0.007 [+0.001, +0.013] pooled. Of C3 core's +0.034 on GOAT, +0.028 is the labels. The declared reading is "both": the sizes are reported and one follow-up is declared (phase_c3i, 72 min of MPS, 1,408 renders, audited)
- **What ran** ([plan](full-controls-plan.md), "C3i in detail").
  - **The recipe:** FTm's exactly (`train-ft --masked --ft-cap 300`, W, 8 inner runs, 8 FT_k and the all-labels pair, seeds 20261042 and 20261043), with C2's labels and FTm's mask, `K.space` only. Its answer holds as FTm's.
  - **The training:** 18 runs, 121 run-minutes, 72 min of MPS wall clock (10:17 to 11:29), beside C2b's renders, which it didn't slow (6,223 to 6,643 an hour).
  - **The read:** one tag, `C3i`, on BKS (480 renders), GOAT (860) and N12 (68): 1,408 renders, each answer primed and kept.
- **The read matched the declaration.** It was audited with separate code from the judge files: every row below reproduces the report to 1e-4. No direction was missing, except 2 of GOAT's 430 against S.
- **By the score** (held half, ln, clustered by DI on BKS and by item on GOAT, pooled with C3's equal weights):

  | Row | BKS (8 DIs, 240 directions) | GOAT (130 items, 430) | Pooled |
  |---|---|---|---|
  | **C3i − FTm (the labels)** | −0.010 [−0.037, +0.017] | **+0.028 [+0.016, +0.040]**, worse | +0.009 [−0.005, +0.023] |
  | **C3 core − C3i (the objective)** | +0.009 [−0.002, +0.020] | +0.006 [−0.001, +0.012] | **+0.007 [+0.001, +0.013]**, worse |
  | C3i − S | −0.133 [−0.222, −0.044] | −0.067 [−0.092, −0.042] | −0.100 [−0.146, −0.054] |

  - **N12** (measurement only, 27 cards on 8 bands): C3i − FTm −0.012 [−0.043, +0.020], undecided; C3i − S −0.134 [−0.254, −0.015].
  - **The declared reading is "both":** C3i − FTm is worse (on GOAT), and C3 core − C3i is worse (pooled). Neither row is split.
  - The two rows add up exactly to C3 core − FTm: +0.034 on GOAT, of which +0.028 is the labels and +0.006 the objective.
- **Beside, at zero renders: the core heads' held losses.** On the 17 continuous `K.space` heads that every run of both models scores, C3's held loss (on C2's labels) is higher than C3i's in all 8 FT_k: by +0.12 to +0.29, mean +0.19. With the same labels and rows, the wider objective fits the core less well. This is a direct look at cause (b); it is reported, not deciding.
  - **The gap is 4 heads** (the review's split, recounted), each worse under C3 in 8 of 8 FT_k: the sw50r's treble +0.93, the right cab's mic level +0.85, the right cab's distance +0.43, the ac20's power +0.38. 8 of the 17 differ by less than 0.03, and the pr12's treble reads −0.02.
  - **Each of the 4 has a close relative among the controls C3 adds:** the sw50r's EQ for its treble, and C1b's mics, rooms and cab for the right cab's level and distance. So with those controls in the loss, the core heads that overlap them in sound fit their labels less well.
- **What it means.**
  - **On GOAT most of the core's loss is the labels.** C2 searched the core with the EQ and pedals, so its core values fit alongside them, and alone they read worse than the stored labels' on GOAT. On BKS they read slightly better, undecided. The adopted C3 learns the EQ and pedals as well, which is how it ends level with FTm.
  - **The wider objective costs a little:** +0.007 pooled, decided, and the held losses agree.
  - **The declared next step:** one (b) follow-up, C3's recipe with the core heads' share of the loss restored to FTm's, declared separately before it trains. Its most is about the objective's +0.007. No second variant follows.
  - **What doesn't change:** C3i is a diagnostic and replaces nothing. The adopted C3 (C3-cabS) stands, and C3r trains as declared.
  - By the score only.
- Files:
  - `PF/c3/c3i.json`;
  - `PF/{real,goat}/report-c3i.json`, `logs/c3i-n12.json`;
  - C3i's runs `C3i-ftm-*`;
  - logs `logs/c3i*.log`.
  - Code: `learn/full_controls_c3.py` (`c3i-rows`) and `pipeline_fix train-ft --c3i`.

### F76. C3b stage 2: C3b's full answer against the adopted C3's, on all three amps. By the score it reads level, −0.009 [−0.037, +0.019] pooled, and its settings alone are level too (+0.001). It is just worse on BKS's clean recordings (+0.015 [+0.000, +0.029]), so by the declared rule it went to the user, who kept C3's pick. With the model's own settings, choosing each recording's amp on its search half beats always-sw50r by −0.093 on both sets and both classes, and the labels' amp doesn't point to it. So C3c trains the amp head on the amp that suits C3's own answer (phase_c3b_s2, 5,640 renders, audited)
- **What ran** ([plan](full-controls-plan.md), "C3b stage 2 in detail").
  - C3b's answers and the adopted C3's (C3-cabS), on all three amps and both search halves.
  - BKS: C3b's 40 units, 480 renders. GOAT: both models on 215 units, 5,160 renders, in their own folders.
  - **The canary passed:** C3-cabS's forced-amp answers and amp probabilities equal its stored ones on all 215 GOAT units, and its renders are bit-identical to F72's on all 215.
  - **A render deadlock cost about 20 minutes** (19:00 to 19:20): stage 2's GOAT shards and C3r's read's shards each counted the other's waiting processes against the cap. The C3r read was stopped and rerun after stage 2. The cap is now a set of file locks (PR #446).
- **The read matched the declaration.** It was audited with separate code from the judge files: the primary, the settings, the class, the headroom and the labels' rows reproduce the report to 1e-4. No direction was dropped.
- **By the score** (held half, ln, by DI on BKS and by item on GOAT, pooled with C3's equal weights):

  | Row | BKS (40 units) | GOAT (215) | Pooled |
  |---|---|---|---|
  | **C3b − C3** (each model's own pick and settings) | −0.022 [−0.077, +0.033] | +0.005 [−0.010, +0.019] | −0.009 [−0.037, +0.019] |
  | the pick alone (C3 at C3b's pick − C3) | −0.027 [−0.075, +0.021] | +0.007 [−0.006, +0.020] | −0.010 [−0.035, +0.015] |
  | **the settings alone** (C3b − C3 at C3b's pick) | +0.005 [−0.005, +0.015] | −0.002 [−0.011, +0.006] | +0.001 [−0.005, +0.007] |
  | C3b − C3, clean | **+0.015 [+0.000, +0.029]**, worse | +0.009 [−0.013, +0.031] | +0.012 [−0.000, +0.024] |
  | C3b − C3, crunch | −0.059 [−0.188, +0.070] | −0.010 [−0.027, +0.007] | −0.035 [−0.100, +0.031] |

  - **The outcome is "user":** the primary is undecided, but on clean it is shown worse on BKS, by a hair.
  - **The user's answer (2026-11-11): keep the current pick.** They asked first whether the sw50r, the most distorted of the three, fits heavier songs. In the search labels it does: it is the labels' amp on 20 of 23 BKS crunch recordings against 8 of 17 clean, and on GOAT 59 of 104 crunch against 50 of 110 clean. But with the model's own settings it does not: on GOAT crunch the sw50r is the best amp in only 43 of 210 directions, and always picking it reads worse than blind there (+0.015 [+0.002, +0.028]).
- **The per-recording headroom, on the models' own answers:**

  | Row, on C3's own renders | BKS | GOAT | Pooled |
  |---|---|---|---|
  | Always sw50r − blind | −0.049 [−0.102, +0.004] | −0.009 [−0.020, +0.003] | −0.029 [−0.056, −0.002] |
  | W's pick − blind | −0.028 [−0.070, +0.015] | −0.013 [−0.026, +0.000] | −0.020 [−0.042, +0.002] |
  | **Search-half argmin − always sw50r** | **−0.093 [−0.132, −0.053]** | **−0.093 [−0.110, −0.075]** | **−0.093 [−0.114, −0.071]** |
  | the same, clean | −0.060 | −0.091 | −0.076 [−0.096, −0.055] |
  | the same, crunch | −0.126 | −0.104 | −0.115 [−0.152, −0.077] |
  | **The labels' argmin amp − always sw50r** | +0.055 [+0.002, +0.109], worse | +0.011 [−0.006, +0.027] | +0.033 [+0.005, +0.061], worse |
  | the same, clean | +0.112, worse | +0.023 | +0.067 [+0.021, +0.113], worse |

  - On C3b's own renders the same rows read alike: the headroom is −0.095 pooled.
  - **GOAT confirms BKS.** With the model's own settings, choosing the amp per recording is worth about 9% by the score, on both sets and both classes. The best amp is spread over all three: on GOAT it is the ac20 in 173 of 430 directions, the pr12 in 150 and the sw50r in 107.
  - **The stored search labels point away from it.** Their amp reads worse than always the sw50r on the model's answers, most of all on clean.
- **What it means.**
  - C3b is not adopted. The amp pick stays W's, near a coin toss, and the adopted C3 stands.
  - **The amp the product needs is the one that suits the model's own answer,** not the one a full search fits best. The product has no DI, so it can't render its answer per amp: a head has to predict that amp from the audio.
  - **Next: C3c** ([plan](full-controls-plan.md), "C3c in detail"). It is C3's recipe with the amp head trained on that amp, labelled from this stage's renders, at zero renders. In parallel, the review session investigates the amp choice more widely, on the user's ask ("render each song with all three amps and then train").
  - By the score only.
- Files:
  - `PF/c3/c3b-stage2.json`, `c3b-stage2-check.json` and `decision-c3b.json` (C3-cabS);
  - `PF/goat/answers-amps3/`, `PF/goat/judge-amps3/` and `PF/real/judge/C3b/`;
  - logs `logs/c3b-s2*.log`.

### F77. C2r and C3r: every trusted real row, by rotation. C2r's labels beat their starts by the score on all three new sets (captures batch 1 −0.179, batch 2 −0.356, the panel −0.073, undecided). C3r trained on them: R-all beats R-ctl, the same folds without the new rows, by −0.059 [−0.078, −0.040] on the deciding pool, decided on BKS, GOAT and the panel. Part of that is a handicap on R-ctl: its epochs were chosen on five sets, three of which it never trains on, so it trained about 12 epochs short; where the two arms' epochs match (fold 3), the new rows read about −0.04. Against C3 itself R-all reads level (BKS −0.008, GOAT −0.013, undecided). By the declared rule R-all's all-labels model replaces C3; C4 can reverse it (phase_c2r, phase_c3r; 36,948 + 3,840 renders, 2 h 9 min of MPS, audited)
- **What ran** ([plan](full-controls-plan.md), "C2r and C3r in detail", Amendments 1 and 2).
  - **C2r:** C2's recipe on the new rows the DI check kept: batch 1's captures (cap1, 121 records), batch 2's C1a records (n12, 12 of 31) and the panel (12 of 18). The DI check (Amendment 1) dropped 14 of 26 DI files: 19 n12 records and 6 panel records left the read.
    - **The run:** 5 render shards (Amendment 2, the user's "Yes, try 5"), 36,948 renders in 3 h 25 min. Nothing refused, not run, or mismatched on replay; 4 starts restarted with the gate off after a miss, none refused.
  - **C3r:** C3's recipe on every trusted real row, trained and read by rotation. R-all has GOAT's and BKS's rows plus the new ones; R-ctl has the same folds, drops and validation rows without them.
    - **The training:** 34 runs, 221 run-minutes, 2 h 9 min of MPS (16:49 to 18:59).
    - **The read:** 3,840 renders. A render deadlock with C3b's stage 2 (19:00 to 19:20) stopped it before its first render; it reran after stage 2, from 19:35.
- **Both reads matched their declarations.** They were audited with separate code: C2r's three primaries from the per-record files (the cluster means equal the report's band-weighted means), and C3r's BKS, GOAT and panel rows, the deciding pool, and R-all − C3 from the judge files, all to 1e-4.
- **C2r, by the score** (the label's fresh render against its start, held half, ln):

  | Set | Records (clusters) | Label − start | Label − S |
  |---|---|---|---|
  | cap1 (batch 1's captures) | 121 (84) | **−0.179 [−0.210, −0.148]** | −0.547 |
  | n12 (batch 2's C1a records) | 12 (7) | **−0.356 [−0.539, −0.172]** | −0.649 |
  | Panel (step 0's best as start) | 12 (5) | −0.073 [−0.167, +0.021] | −0.646 |

  - Both columns are record-weighted, with the cluster jackknife on the first. The band- or creator-weighted means beside: label − start −0.181, −0.319, −0.079; label − S −0.529, −0.607, −0.594.

  - More than 10 dB quieter than their start: cap1 20 of 121, n12 3, the panel 2.
- **C3r, by the score** (each held unit's answer from its fold's FT_k, held half, ln; BKS by DI, GOAT by item, the panel by DI, cap1 and n12 by creator):

  | Row | BKS | GOAT | Panel | Deciding pool (BKS, GOAT, panel) | cap1 | n12 |
  |---|---|---|---|---|---|---|
  | **R-all − R-ctl** | **−0.061 [−0.100, −0.022]** | **−0.039 [−0.055, −0.023]** | **−0.076 [−0.122, −0.030]** | **−0.059 [−0.078, −0.040]** | −0.027 [−0.054, −0.001] | +0.002 [−0.070, +0.074] |
  | R-all − S | −0.130 | −0.103 | −0.168 | −0.134 | −0.152 | −0.338 |
  | R-ctl − S | −0.069 | −0.064 | −0.092 | −0.075 | −0.125 | −0.340 |
  | R-all − C3-cabS (C3's stored scores) | −0.008 [−0.061, +0.046] | −0.013 [−0.027, +0.001] | — | — | — | +0.024 [−0.060, +0.109] |

  - **Beside, recounted:** R-ctl − C3-cabS reads +0.053 [+0.009, +0.098] on BKS and +0.026 [+0.013, +0.040] on GOAT, both worse.
  - **The cause is R-ctl's epochs, not its drops** (the review's finding, recounted). E, the mean of the two seeds' FT_k epochs: C3 59.5, R-ctl 47.3, R-all 59.3. The inner runs chose E on validation over all five sets, and R-ctl never trains on three of them, so it stopped early. BKS drops no rows in R-ctl, yet shows the larger gap. GOAT's drops are flat by fold (36, 36, 35, 30), while fold 3, with the fewest drops, has the largest gap and the largest E shortfall.
  - **So part of R-all − R-ctl is that handicap.** In fold 3, where the two arms' E match (48.0 and 48.5), R-all − R-ctl reads −0.046 on BKS and −0.032 on GOAT. The plan called the five-set validation "conservative for R-all"; it was the opposite.
  - **The adoption is unaffected:** R-all's all-labels pair trains to E 57, as C3's does, so the product model carries no such handicap.
- **The declared rule: kept unless shown worse.** R-all − R-ctl is not shown worse anywhere, and is better on every deciding set, so R-all's all-labels model replaces C3-cabS as the adopted model (`c3r/report.json`: replaces_c3, complete).
- **What it means.**
  - **Training on every trusted row helps, by the score:** about 4% closer where the arms' epochs match, and 6% on the deciding pool with R-ctl's early stop included. Against C3 itself the product reads level.
  - **For any later control arm:** match its E to the treated arm's, or validate it only on the sets it trains on.
  - **What changes downstream:** C4 hears R-all, reading apart the batch 3 captures whose creator trains in it (6 of 22 creators, 17 of 44 captures); C5 is restated on C3r's rows; the panel is no longer an unseen-band test.
  - **What stays open:** the amp head on the new rows (C3c reads first), the split loss (C3s, F78), and the effects, masked as in C3.
  - By the score only.
- Files:
  - `PF/c2r/` (`records.json`, `report.json`) and the per-record outputs in `captures/search-c2r/`, `captures2/search-c2r/`, `panel/search-c2r/`;
  - `PF/c3r/` (`folds.json`, `answers/`, `judge/`, `report.json`);
  - logs `logs/c2r*.log`, `logs/c3r*.log`.
  - Code: `learn/full_controls_c2r.py`, `learn/full_controls_c3r.py`.

### F78. C3s: C3's recipe with the core's share of the loss restored. By the score it improves the core: C3s-core − C3-core −0.019 [−0.025, −0.012] and C3s-core − C3i −0.011 [−0.020, −0.002], both decided, with its core heads' held losses back at C3i's level. But in the adopted configuration the gain is −0.008 [−0.026, +0.009], undecided, so by the declared rule C3's recipe stands (phase_c3s, 81 min of MPS, 2,810 renders, audited)
- **What ran** ([plan](full-controls-plan.md), "C3s in detail"). C3's recipe with `full_space.loss_split`: the core's terms exactly C3i's, the added controls' own term beside. 18 runs, 137 run-minutes, 81 min of MPS (18:59 to 20:20), its own inner runs. The read: two tags, C3s-cabS (held as C3-cabS) and C3s-core (held as C3-core), on BKS, GOAT and N12, 2,810 renders.
- **The read matched the declaration.** It was audited with separate code from the judge files: the three deciding rows reproduce the report to 1e-4.
- **By the score:**

  | Row | BKS | GOAT | Pooled |
  |---|---|---|---|
  | **C3s-cabS − C3-cabS (decides)** | −0.010 [−0.044, +0.024] | −0.007 [−0.017, +0.003] | −0.008 [−0.026, +0.009] |
  | C3s-core − C3i | −0.016 [−0.032, +0.001] | **−0.007 [−0.014, −0.000]** | **−0.011 [−0.020, −0.002]** |
  | C3s-core − C3-core | **−0.024 [−0.035, −0.014]** | **−0.013 [−0.020, −0.006]** | **−0.019 [−0.025, −0.012]** |
  | C3s-cabS − S | −0.132 | −0.097 | −0.114 [−0.155, −0.074] |

  - **N12** (27 cards): C3s-cabS − FTm −0.055 [−0.135, +0.026]; C3s-core − FTm +0.013 [−0.010, +0.035].
  - **The 4 heads that carried F75's gap,** held loss at the last epoch, mean of 8 FT_k (C3 / C3i / C3s): the sw50r's treble −0.38 / −1.31 / −1.34; the right cab's mic level −0.38 / −1.23 / −1.46; its distance +0.16 / −0.27 / −0.27; the ac20's power +0.16 / −0.22 / −0.11. Over all 17 core heads: +0.062 / −0.129 / −0.147. The split loss brings the core's fit back to C3i's.
- **The declared reading:** C3s-cabS − C3-cabS is undecided, so the split loss is not adopted for later steps (`c3/decision-c3s.json`: C3). The core rows are diagnostics: restoring the share recovers the core, and more.
- **What it means.**
  - **Cause (b) is real and fixable:** with its own term, the core learns better than in C3, and a little better than in C3i, which suggests the added controls' own term helps the shared mixture.
  - **The adopted configuration barely moves,** as the review predicted: the learned EQ and cab already make up for most of the core's loss there.
  - **The split loss stays a candidate** for the next retrain's declaration, with its −0.008 stated. It is not adopted into the model now. That declaration states that it was undecided on the product row, reads it again on its own primary, and runs on R-all's recipe.
  - **Not an epoch effect** (the review's check): C3s trains longer (E 67.8 against 59.5), but its core gain is even across folds, and C3 and C3i differ in core loss at similar E.
  - By the score only.
- Files: `PF/c3/c3s.json`, `decision-c3s.json`; `PF/{real,goat}/report-c3s.json`, `logs/c3s-n12.json`; runs `C3s-ftm-*`; logs `logs/c3s*.log`.

### F79. C3c: the amp head on the amp that suits C3's own answer. By the score it doesn't learn: its pick reads +0.031 [−0.010, +0.073] against always-sw50r, undecided, worse on BKS (+0.065), level on GOAT (−0.002). It does beat a prior-only head (the class's label majority, −0.063, decided). A zero-render cost-target probe finds nothing on the input the model actually reads, so by the declared stop rule learning the amp from the audio stops (phase_c3c, 37 min of MPS, zero renders, audited)
- **What ran** ([plan](full-controls-plan.md), "C3c in detail"). C3b's recipe with the amp label from C3b stage 2's renders: the argmin of C3-cabS's out-of-fold per-amp renders on each unit's search half (GOAT 214, BKS 40). 8 FT_k on C3's E and the all-labels pair, 37 min of MPS (21:22 to 21:59). The read: CPU predicts, zero renders, every pick valued on C3-cabS's own per-amp renders.
- **The read matched the declaration.** It was audited with separate code: C3c − always sw50r and C3c − W reproduce to 1e-4. The guard passed: each C3c FT_k holds out C3's units and records the labels' sha256.
- **By the score** (held half, ln; BKS by DI, GOAT by item, pooled with C3's weights):

  | Row | BKS (40) | GOAT (215) | Pooled |
  |---|---|---|---|
  | **C3c − always sw50r (the declared reading)** | +0.065 [−0.014, +0.145] | −0.002 [−0.020, +0.016] | +0.031 [−0.010, +0.073] |
  | C3c − W | +0.044 [−0.050, +0.138] | +0.002 [−0.016, +0.020] | +0.023 [−0.025, +0.071] |
  | C3c − the class's label majority | −0.093 [−0.200, +0.014] | **−0.034 [−0.056, −0.011]** | **−0.063 [−0.118, −0.008]** |
  | C3c − always ac20 | +0.019 | **−0.034 [−0.053, −0.015]** | −0.008 |
  | Search-half argmin − blind (the ceiling) | −0.142 | −0.101 | −0.121 |

  - **The declared reading is "undecided":** C3c doesn't beat the best constant.
  - **It isn't a prior-only head:** it beats the labels' majority (the ac20 on clean, the pr12 on crunch), the worst constants. That majority is the pooled labels', applied to BKS too, where BKS's own majority is the sw50r.
  - Its picks on GOAT: ac20 218, pr12 105, sw50r 107 of 430; 164 hit the direction's own argmin. AUC 0.53 to 0.59 on GOAT; on BKS 0.43 to 0.68.
- **The cost-target probe** (the review session's, declared before its run; `logs/amp-cost-probe.md` in its worktree).
  - A 3-output ridge regression on the per-amp centred search-half ln judges, picking the lowest predicted cost. Its inputs: class, set, the input's 53-number mel summary and C3c's out-of-fold log-probabilities. Outer folds: the 4 real folds.
  - **As first run, on the clean amp track:** GOAT −0.018 [−0.033, −0.003], shown better; BKS +0.059, undecided. The mel summary alone read −0.023.
  - **The flaw, found by the review itself:** that summary came from the clean reamped amp track, which the product never has. The model reads D_fix variant 0, the section mixed with a backing and separated. The two inputs' band shapes correlate 0.84 at the median and 0.54 at the 10th percentile.
  - **On the input the model reads,** the same frozen probe reads BKS +0.031 [−0.037, +0.099], GOAT +0.002 [−0.015, +0.019], pooled +0.016, AUC 0.51; the mel summary alone −0.000, AUC 0.52. Nothing.
- **What it means.**
  - **The declared stop rule triggers:** on the input the product sees, no probe beats the best constant on GOAT, and BKS leans worse. C3c, C3's own embedding and the spectral probe agree. Learning the amp from the song's audio stops.
  - **The user's idea** ("render each song with all three amps and then train") would only confirm a null for this question, so its 4,320 renders were declared, then withdrawn before any ran.
  - **The clean amp track carries a weak signal** (−0.018 on GOAT) that separation erases, so a cleaner stem would be the precondition for any later learned selector.
  - **What goes to the user,** explained: comparing each amp's answer rendered through a library DI with the song's separated guitar at inference (a new approach, about 2,600 renders to test), or offering three presets, one per amp, to pick by ear. Until then the product keeps W's pick.
  - By the score only.
- Files: `PF/c3/c3c.json`; runs `C3c-ftm-*`; logs `logs/c3c*.log`. `PF/c3r/answers/all-amps3.json` is the withdrawn read's zero-render answers (R-all on all three amps), unused.

### F80. A1: the amp chosen by a stock-DI comparison. By the score the declared pick (the model's own features, floored) beats always-sw50r on GOAT, −0.017 [−0.033, −0.002], and leans worse on BKS, +0.052 [−0.018, +0.122]; pooled +0.017, undecided. By the declared rule that reads "learns" (better somewhere, worse nowhere), but it is weak. On the clean amp track the same comparison reads −0.039 [−0.073, −0.005] pooled, so the separation costs most of it. A confirmation on R-all and on fresh units is declared before anything ships (phase_a1, 6,120 renders, audited)
- **What ran** ([plan](full-controls-plan.md), "A1 in detail", Amendment 1 and its floor), on the user's "Definitely A".
  - Each of GOAT's 215 and BKS's 40 units: C3-cabS's answer per amp and search half, through two stock library DIs of its class (clean: The Travelling Band 16, Ale Lak 24; crunch: Ale Lak 09, Dark Ride 29).
  - 6,120 renders in 1 h 23 min (00:02 to 01:25), then a zero-render read (01:25 to 01:28).
  - **The primary pick:** the amp whose renders' features (the C3 fold model's pooled body features, both seeds; every input floored at −90 dB) sit closest by cosine to the song's separated guitar's. Valued on the held half of C3-cabS's own per-amp renders.
- **The read matched the declaration.** It was audited with separate code: from the stored picks and the judge files, the primary, its classes and the clean-track row reproduce to 1e-4. Every stored pick equals the argmin of its stored distances (1,530 of 1,530). No direction was dropped.
- **By the score** (held half, ln; BKS by DI, GOAT by item; pooled with C3's weights):

  | Pick − always sw50r | BKS (40) | GOAT (215) | Pooled |
  |---|---|---|---|
  | **The model's features, floored (primary)** | +0.052 [−0.018, +0.122] | **−0.017 [−0.033, −0.002]** | +0.017 [−0.019, +0.053] |
  | the same, clean | +0.003 | **−0.035 [−0.057, −0.013]** | −0.016 [−0.043, +0.011] |
  | the same, crunch | +0.100 | −0.003 | +0.049 |
  | The model's features, unfloored | −0.004 | −0.010 | −0.007 [−0.045, +0.031] |
  | **The model's features, on the clean amp track** | −0.035 | **−0.043 [−0.060, −0.025]** | **−0.039 [−0.073, −0.005]** |
  | The spectral shape (declared first) | +0.094 | **−0.024 [−0.041, −0.007]** | +0.035 |
  | The shape on the clean amp track | −0.009 | **−0.043** | −0.026 |
  | The shape, 60 Hz to 8 kHz | −0.011 | +0.002 | −0.004 |
  | W (the shipped pick) | +0.021 | −0.004 | +0.009 |
  | The search half's own argmin (the ceiling) | −0.093 | −0.093 | −0.093 |

  - **Against W:** the primary reads +0.030 on BKS, −0.013 on GOAT and +0.009 pooled, all undecided. On the clean track it reads −0.047 [−0.070, −0.025], better.
  - **BKS's lean worse is the pick's amp share, not its per-recording choices** (the review's shuffle, picks permuted within set and class): GOAT reads −0.018 observed against +0.004 shuffled, so the picks carry information; BKS reads +0.056 against +0.043 shuffled (p 0.80). The pick sends 43 of BKS's 80 directions to the pr12, and always-pr12 on BKS reads +0.101.
  - **The picks spread over the amps:** the primary picks on GOAT pr12 115, sw50r 167, ac20 148 of 430; on BKS pr12 43, sw50r 28, ac20 9 of 80. The shape pick on the stem leans hard on the pr12 (329 of 430), a bias the floor and the features remove.
- **What it means.**
  - **By the declared rule the primary "learns",** on GOAT alone: about a fifth of the headroom there (−0.017 of −0.093), and on GOAT's clean units −0.035. On BKS's 8 DIs it leans worse (+0.052, wide). Pooled it is level with always-sw50r.
  - **The method works when it hears the guitar clean:** on the clean amp track it is better on both sets' pooled read (−0.039), about 40% of the headroom. The separated stem is again the bottleneck (F79): a cleaner stem is worth more than a better statistic.
  - **Two statistics were read,** as declared: the shape first, then the features by the amendment, before any read.
  - **Nothing ships on this.** The rule's next step, a product step on the adopted model with an ear check, is declared with a confirmation first: the same pick on R-all, read on units no A1 choice was made on ([plan](full-controls-plan.md), "A2 in detail").
  - By the score only.
- Files: `PF/a1/` (`plan.json`, `shapes/`, `mels/`, `embed/`, `a1.json`); logs `logs/a1*.log`. Code: `learn/amp_di_compare.py`.

### F81. A2: A1's stock-DI pick confirmed on the adopted model (R-all) and on fresh units. By the score it beats always-sw50r on cap1, −0.049 [−0.074, −0.023] (19 creators, every leave-one-out negative), level on the panel (+0.010, 5 DIs), and worse nowhere: the declared rule reads "learns". GOAT repeats A1's −0.017, and BKS now leans better (−0.016). Against the adopted model's own amp head it reads −0.022 pooled. The per-recording choices carry the gain: shuffling them within set and class loses it. The product step's ear check, A3, is declared next (phase_a2, 12,096 renders, audited)
- **What ran** ([plan](full-controls-plan.md), "A2 in detail"): A1's frozen pick (its stock DIs, the floored embedding, its rows) on R-all's out-of-fold answers, on C3r's read units outside n12. cap1 (121 units) and the panel (12) decide; GOAT (215) and BKS (40) are read beside. No unit sits on a stock DI's file, session or song (0 of 388).
  - 12,096 renders in 2 h 49 min (01:46 to 04:35): 2,784 for the other two amps through each unit's own DI, 9,312 through the stock DIs. The declaration counted 7,440: it left the search halves out of the stock-DI renders (388 × 24, not × 12). The method is unchanged.
  - "W" in A2's rows is R-all's own amp head, the pick the adopted model ships with.
- **The read matched the declaration.** It was audited with separate code, from the stored distances, the judge files and C3r's answers: every row and interval below reproduces to 1e-4, every stored pick is the argmin of its stored distances, A2's answers for the forced amps equal C3r's, and no direction was dropped.
- **By the score** (held half, ln; cap1 by creator, the panel and BKS by DI, GOAT by item; the deciding pool weights cap1 and the panel equally):

  | − always sw50r | cap1 (121) | Panel (12) | Deciding pool | GOAT (215) | BKS (40) |
  |---|---|---|---|---|---|
  | **The pick (primary)** | **−0.049 [−0.074, −0.023]** | +0.010 [−0.056, +0.076] | −0.019 [−0.054, +0.015] | **−0.017 [−0.031, −0.002]** | −0.016 [−0.062, +0.031] |
  | the same, clean | **−0.045** | **−0.039** (3 DIs) | | **−0.033** | −0.022 |
  | the same, crunch | **−0.049** | +0.083 (2 DIs) | | −0.008 | −0.009 |
  | The pick on the clean amp track | **−0.081** | +0.013 | −0.034 [−0.073, +0.004] | **−0.045** | **−0.092** |
  | R-all's amp head (W) | −0.010 | +0.014 | +0.002 | +0.002 | +0.006 |
  | **The pick − W** | **−0.039 [−0.067, −0.011]** | −0.004 | −0.022 [−0.044, +0.001] | **−0.019 [−0.034, −0.004]** | −0.021 |
  | Always ac20 | −0.028 | **+0.142** | | +0.020 | −0.029 |
  | Always pr12 | −0.004 | **+0.041** | | +0.013 | +0.050 |
  | The search half's own argmin (the ceiling) | −0.125 | −0.028 | −0.077 | −0.088 | −0.124 |

  - **The choices carry it, not the amp shares** (the picks shuffled within set and class, 2,000 times): cap1 −0.049 against −0.020 shuffled, the panel +0.010 against +0.057, GOAT −0.017 against +0.011 (each p ≤ 0.002); BKS −0.016 against −0.003 (p 0.20).
  - **cap1 isn't carried by one creator:** leaving any one out gives −0.053 to −0.040, and 16 of 19 creators read negative.
  - **The picks spread over the amps:** cap1 pr12 81, sw50r 77, ac20 84 of 242 directions; the panel 7, 10, 7 of 24; GOAT 128, 147, 155 of 430; BKS 38, 24, 18 of 80. R-all's head leans on the sw50r (cap1 148 of 242, GOAT 244 of 430) and is level with always-sw50r everywhere.
  - **On the panel** the constant amps are far apart (always-ac20 +0.142, shown worse), and the pick avoids most of that: +0.010 against +0.057 shuffled. Its crunch lean (+0.083) rests on 2 DIs. Its ceiling is only −0.028, so it had little room to show a gain.
  - **cap1 and GOAT are partly dependent reads** (the review): 111 of cap1's 121 units sit on GOAT's DI performances. No leak through them is shown: the split by whether the fold model trained on the shared performance goes opposite ways on the two sets (cap1 −0.063 against −0.014, GOAT −0.005 against −0.029). cap1 also holds by DI item (−0.041), by capture (−0.042) and with creators merged by amp family (−0.052). On real amps, expect about GOAT's −0.017.
  - **Beside, not a switch:** the unfloored pick reads better than the declared floored one, here (pooled −0.038 [−0.062, −0.015]) as in A1 (−0.007 against +0.017). The floor was fixed before any read, so it stays the pick. If the product step is ever re-read fresh, the unfloored pick is the candidate.
- **What it means.**
  - **Confirmed, by the declared rule:** on the adopted model and on units A1 never read, the stock-DI pick is better than always-sw50r on cap1 and worse nowhere. That is about 40% of cap1's headroom (−0.049 of −0.125) and a fifth of GOAT's. Against the pick the adopted model ships with it reads −0.022 pooled (undecided, upper +0.001), decided on cap1 and GOAT.
  - **The deciding pool is undecided** because the panel's 5 DIs are wide. So "learns" rests on cap1, the larger fresh set, with GOAT repeating A1 on largely the same performances. On real amps the size is about GOAT's, −0.017.
  - **BKS's lean worse in A1 doesn't repeat** on R-all's answers (−0.016, against +0.052 on C3-cabS's).
  - **The separation still costs about half:** on the clean amp track the same pick reads −0.081 on cap1 and −0.092 on BKS. A cleaner stem is worth more than a better statistic.
  - **Next, by the rule:** the product step. The pick goes into the generate path on R-all, after a blind ear check of its amp against W's ([plan](full-controls-plan.md), "A3 in detail"). Nothing ships before the model itself, which waits for C4 and the loudness step.
  - By the score only.
- Files: `PF/a2/` (`answers.json`, `judge/`, `shapes/`, `mels/`, `embed/`, `a2.json`); logs `logs/a2*.log`. Code: `learn/amp_di_compare_r.py`.

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
  (2026-11-02):** 60 (56, and 4 after the amendment), about 64,730 in all. **J5's fresh page (2026-11-03):** 56
  (28 kept, each with its priming render), about 64,790 in all. **L0 (2026-11-04):** 80 (40 kept, each with its
  priming render), about 64,870 in all. **The night of 2026-11-05 (labels ahead of the ear, nothing read from them):** L1a's lags 900 and labels 5,602 on v2, L1b's lags 882 and labels 5,539, N2 1,207, FTh and FTm's reads 2,680, N4's 40: 16,850, N5b's 1,336, L1a's label page 72: about 83,000 in all.
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
