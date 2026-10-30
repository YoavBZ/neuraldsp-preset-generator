# The direct model, step by step: a pipeline review (2026-10-30)

**Status: review only.** Zero renders, zero separations, no training. It reads code and stored files and
decides nothing. The tests it proposes (P1–P7, below) each need their own declaration and review, and the
user's yes for any training, before they run.

**Why.** The user (2026-10-30): "We are working too long on the ML effort and can't make it beat the starting
presets for some reason. I find it very odd. Go over the entire ML model process, list it step by step (many
small steps, not a few large ones), so we could go one by one and test where are the failing points." The user
then asked for this record, with each step given its own verification, fix and test, so that later work does not
start the investigation again.

**What it covers.** The direct model (song to settings) as last built: D_CC on the
[clean/crunch pool](clean-crunch-pool-plan.md), with D_F5 and D_core5 (T3, [design](trusted-data-t0-design.md))
where they differ. Arm A (search through a rebuilt DI) is out of scope.

**Sources.** Three read-only code traces (data, model, evaluation) and the author's own checks. Every number
below comes from one of two places: a check in [`learn/pipeline_review.py`](../learn/pipeline_review.py), whose
output is [`ml-pipeline-review.json`](ml-pipeline-review.json) (the check is named, e.g. `s16`), or a linked
record. Code is cited as `file:line` at commit e124367.

## How to use this record

- **Steps keep their numbers.** These are the numbers in the chat list the user saw on 2026-10-30. Refer to
  "step 16", not to a section title.
- **Every step has the same fields:**
  - *What happens*: the step, in plain words.
  - *Code*: where it happens.
  - *Status*: one of four words.
    - **OK**: checked, no problem found.
    - **Problem**: checked, and a problem was found.
    - **Suspect**: the code shows a risk whose effect is not measured.
    - **Unchecked**: never tested.
  - *Evidence*: the check (`sNN`) or record, with its figures.
  - *Verify*: how to confirm the step is right, where that is still open.
  - *Fix*: the candidate fix, where there is a problem. None is adopted.
  - *Test*: the test that decides it (P1–P7 below).
- **When a test runs or a fix lands,** add a dated line under the step and update its row in the table. Don't
  rewrite what was found.
- **Re-running the checks:** `.venv/bin/python -m learn.pipeline_review --out docs/ml-pipeline-review.json`
  takes about a second.
  - From a worktree, call the main checkout's `.venv/bin/python`. The module is stdlib only.
  - The paths the checks read (the table at the end) are under `~/ndsp-presets/learn/`; the default
    `--data-dir` is `~/ndsp-presets`.
  - Add `--only s16 s32` for some checks, or `--data-dir PATH` for another data root.
  - A check whose input is missing reports `missing` and the rest still run.
  - After a rebuild, the checks read the new pool. Read the old figures from this commit's JSON.

## The short answer

**The failure chain** (each link measured):
1. **The model reads almost none of the sound, even on its own made-up songs** (step 29). On held-out sections
   of its training songs (FS5), D_F5:
   - reads 5 of 85 knobs better than the training average, about what chance gives, and 9 reliably worse;
   - reads 14 of 28 switches, but weakly (AUC at most 0.67; reverb 0.49);
   - reads the amp slightly (accuracy 0.40 against a base rate of 0.33).
2. **With so little read, the readout scores about as well as the training average (the "constant"), or worse**
   (steps 26 and 27).
   - Knobs are pulled toward that average, all the way for over a third of them.
   - A near-chance switch read at 0.5 flips a whole pedal.
   - D_F5 − constant is −0.004 [−0.052, +0.043].
   - D_CC − its own constant is +0.103 [+0.051, +0.155]: worse than its own average, through its pedal flips.
3. **On real songs that average leans worse than S** (step 37): constant − S +0.092 [−0.029, +0.213].
   - The interval holds 0, so this is undecided.
   - 5 of 7 bands and 9 of 11 parts are worse, and every leave-one-band-out mean is +0.042 to +0.123 (the lowest
     without Diesel13).
   - The average is wet and centred on random draws. S is a dry factory preset chosen by the same judge, on a
     choice set that holds 8 of the 11 test clips (step 36).
4. **So "never beats S" is what steps 29, 26–27 and 36 together predict,** without anything else being wrong.
   The question that matters most is why the model reads so little.

**The leading suspects for step 29,** most evidence first:
- **Step 16, the input holds the wrong guitars.** The X-LANCE stem holds every guitar in the mix, the target a
  median 6.2 dB under the rest. Only 78 of 3,033 kept examples (training and early stopping) have the target as
  the only guitar. On V-real, two parts (Wickerman ElecGtr2 and ElecGtr3) give the model byte-identical inputs
  and so get one answer, scored against two different amp tracks (step 32).
- **Step 22, far too little training.** 2,699 examples and 430–1,204 steps to the best epoch (whole runs of
  3.6–8.3 minutes). The earlier part C model kept improving with size up to 20,000 examples, and on the guitar
  alone up to 40,000.
- **Steps 8 and 11, labels for what cannot be heard.** Inaudible effects and stereo-only controls are scored in
  full.
- **Step 12, doubles with different pedals.** A doubled part is rendered with different drive and compressor
  switches from the target's label in 34–39% of the examples that have one.
- **Step 21, a knob-unit loss in a space where many settings sound alike.**
- **Step 5, a class input that means one thing in training and another on real songs.**

**The measurement also limits what can be seen** (steps 9, 32, 35, 36).
- D_F5 − S's interval is ±0.13; D_core5 − S's is ±0.04, and D_F5 − constant's ±0.05.
- On known-answer songs, whose records are Morgan renders, the truth itself only reaches about half of S's
  distance.
- S has a home advantage of unmeasured size.

## Status at a glance

| Step | What | Status | Evidence | Test |
|---|---|---|---|---|
| 1 | DIs from released sessions, test bands kept out | OK | pool plan, ear pages | |
| 2 | Every DI timed against its own amp track | OK | pool amendment 2: 50 of 61 in time | |
| 3 | 10-s sections every 5 s | Suspect (with 23) | `clean_di.py:48-53` | |
| 4 | Section screens; pool size | Problem (size) | `s04`: 262 sections, 32 DIs, 9 bands | P2 |
| 5 | Class input = a coin flip in training, the real class on songs | Suspect | `s05`: 1,512 of 3,033 differ | P6 |
| 6 | Settings drawn: factory / start / wide | Suspect | `s06`: factory draws reverb 73%, delay 62% | P3 |
| 7 | Near-silent draws refused | Problem | `s07`: wide 38%, factory 1.6%, start 0% | |
| 8 | Labels count inaudible settings | Problem | audibility outcome; step 4's ear page | P2 |
| 9 | DI re-EQ'd to an average guitar, −22.9 LUFS | OK (consistent) | same in training and scoring | P4 |
| 10 | Target render, fresh process, warm-up | OK | positive control 50 of 50 | |
| 11 | Render folded to mono | Problem | tone probe: every render mono | P2, P4 |
| 12 | Doubles rendered with the target's core setting | Suspect | `s12`: drive switches differ in 34–35% | P7 |
| 13 | Recorded amp-track stand-ins | Suspect | `s13`: 44% of examples (F5: 0) | |
| 14 | Target-to-backing level drawn from real songs | Suspect (minor) | `s14`: median −9.1 dB | |
| 15 | Half the mixes mastered | Suspect (minor) | V-real mixes are raw sums | |
| 16 | X-LANCE stem as the model's input | **Problem (leading)** | `s16`: median −6.2 dB; 78 alone | P2 |
| 17 | Mel features, same code in training and on songs | OK | parity check | |
| 18 | Augmentation (dropouts, darkening, merges) | Suspect (weak) | no-augmentation +0.051, undecided; leans towards it helping | |
| 19 | How much tone survives to the input | Problem (located) | `s19`: 86 → 30 → 20 of 116 | P2 |
| 20 | Network shape | Unchecked | can it fit at all? | P1 |
| 21 | Loss in knob units | Suspect | probe: +3.1 points over a 17-point error | P2 |
| 22 | Training size and length | **Problem (leading)** | `s22`: 430–1,204 steps | P1, P2 |
| 23 | Early stopping on the same songs | Problem | `s23`: 26 of 32 overlap in time | |
| 24 | Missing training diagnostics | Unchecked | `s22`: only total losses logged | P1 |
| 25 | Each knob's mixture median, 2 seeds | OK | constant research | |
| 26 | Knobs pulled toward the training average | Problem | `s26`: b = 0 for 36–38% | P3 |
| 27 | Switches on above 0.5 | Problem | `s27`: pedals at S −0.076, 7 of 7 bands | P3 |
| 28 | Everything else at S | OK | | |
| 29 | Fake-song test (FS5) | **Problem (central)** | `s29`: 5 of 85 knobs; switches weak | P1, P2 |
| 30 | Fake-song test by sound | Unchecked | never run | P2 |
| 31 | V-real: 11 parts in 7 bands | Problem (size) | 3 parts from one song | |
| 32 | V-real input: the stem of a raw mix | Problem | `s32`: 2 parts, identical inputs | P4 |
| 33 | Each answer forced onto 3 amps × 2 halves | OK (caveat) | render-order phase noise | |
| 34 | The judge scores 1.5 s tails | OK (explains the loss) | `s34`: time effects at S → +0.001 | |
| 35 | Band-weighted log ratio, 90% interval | Problem (power) | `s34`: D_F5 − S width 0.26 | |
| 36 | S chosen on most of the same clips | Problem (size unmeasured) | `s36`: rules re-derived; 8 of 11 clips in the choice sets | P5 |
| 37 | The training average against S | **Problem (explains "never beats S", with 26–27 and 36)** | `s34`: +0.092, undecided; 9 of 11 parts worse | P3 |
| 38 | Headroom with the true DI on these parts | OK | `s38`: −0.137 shrunk, −0.192 best | |

## The proposed tests (nothing run)

Cheapest and most decisive first. Each one needs a declaration (here as a dated amendment, or its own plan), an
independent review and a ledger entry before it runs. P1 and P2 train, so they also need the user's yes.

- **P5, S's home advantage** (step 36). Zero renders.
  - Re-run the clean and crunch start rules from the stored distances, with V-real's clips left out.
    `pipeline_review.pick_start` already reproduces both rules exactly, so this is a few lines.
  - If S changes, S was flattered on V-real; read the new S's stored distances on V-real (no render if they are
    stored, else 66 directions).
  - Limit: with V-real's 6 crunch clips removed, 6 of the 7 crunch parts left still come from V-real's bands, so
    a band-level version is not possible for crunch.
- **P6, the class input** (step 5). Zero renders, model inference only.
  - Read V-real-11 with each part's class flipped, and count how many written settings change. If almost none
    change, the input is ignored. Many changes show only that it is used.
  - To measure what the mismatch costs, read FS by knob error with the drawn class and with the section's class
    (both are known there).
- **P7, doubles and the drive heads** (step 12). Zero renders, model inference only.
  - D_CC's drive and compressor switch AUC on FS_CC, split by whether the example has a DT double.
  - Likely undecided: FS_CC holds only 52 examples with a DT double, from 5 sections, and doubled examples are
    also denser (a confound). The decisive version is a rebuild that gives doubles the target's full setting
    (renders), declared with F20.
- **P1, a memorise check** (steps 20, 21, 22, 24, 29). Minutes of MPS, zero renders.
  - Train the D_CC network on about 200 training examples until the training loss stops falling.
  - Log each head's loss in eval mode, against a no-input baseline in the same units: the labels' own marginals
    on those examples, per amp and class (each knob a 4-component mixture fitted to its labels, each switch its
    on-rate, each mic and the amp their frequencies). The constant itself is a point answer, so it has no loss in
    these units.
  - The reading, with no pass bar (the user's rule): how far below that baseline each head gets. A healthy
    network memorising 200 examples should drive most heads far below it. If it can't, the network, the loss or
    the labels are broken, whatever the data.
- **P2, a clean-input model, then one harder input at a time** (steps 4, 8, 11, 16, 19, 21, 22, 29, 30).
  - P2a: train on the stored clean target renders (`tgt-cc`, `tgt-t3`; already on disk, zero new renders), about
    4–8 minutes of MPS a seed.
  - Read FS by knob (R0's rule, zero renders) and by sound: render the model's, the constant's and S's answers
    for a fixed sample of FS examples through each example's own DI, and judge them against its known target
    render (a few hundred renders).
  - Then step the input down one rung at a time:
    - P2b: the target alone in its backing (no other guitar; needs mixes without the others, zero renders);
    - P2c: the self-built mix;
    - P2d: the stem.
  - The rung where by-sound skill disappears is the failing step. If P2a already fails, the problem is the
    model, labels or loss (steps 20–24), not separation.
- **P3, fall back to S, not the average** (steps 6, 26, 27, 37). Zero training, about 99 renders on V-real (as
  R1).
  - The pull's target becomes S's value, and a switch whose head did not read on FS keeps S's state.
  - Expected: from "worse than S" to "about S, plus whatever the model really reads". It is a readout change for
    the product, not a fix of step 29.
- **P4, real guitar input** (steps 9, 11, 32). After P2a, zero training, about 99 renders.
  - P2a's model reads V-real's own amp tracks (the real guitar alone). The input level of a real amp track needs
    declaring: the stem's gain rule does not apply to it.
  - This shows whether learning from Morgan renders carries over to real recordings at all.

## The steps

### Choosing the training guitars

**Step 1. Take DIs from the released multitrack sessions, keeping the test bands out.**
- *What happens:* 19 released sessions are training sources. V-real's 7 bands, the known-answer bands and the
  reserved bands are barred, failing closed on a missing band. Acoustic, MIDI and synth DIs are dropped.
- *Code:* `learn/cc_pool.py:99` (`VREAL_BANDS`), `learn/cc_pool.py:331` (`inventory`).
- *Status:* OK.
- *Evidence:* the [pool plan](clean-crunch-pool-plan.md)'s step 0 and ear sittings E and 12–15. Every DI was
  heard or measured, and dirty ones are excluded.

**Step 2. Check each DI is in time with its own amp track.**
- *What happens:* GCC-PHAT over ±3 s on a window every 5 s, with an onset-envelope fallback. A DI needs 3
  readings that agree within 10 ms. It fails closed when it can't be timed.
- *Code:* `learn/cc_build.py:1158` (`align_di`), `learn/cc_build.py:1123` (`align_verdict`).
- *Status:* OK.
- *Evidence:* pool amendment 2: 50 of 61 DIs in time. Forkupines Sugar Faith ElecGtr8 (+129.8 ms) waits for the
  next build's shifted copy.

**Step 3. Cut each DI into 10-second sections every 5 seconds.**
- *What happens:* neighbouring sections share 5 s of audio. A section needs 80% of its frames within 40 dB of
  the file's loudest, and 60% in each half.
- *Code:* `learn/clean_di.py:48-53`.
- *Status:* Suspect, only through step 23: early-stopping sections overlap training sections in time.
- *Fix:* draw early-stopping sections by song or band, not by section (step 23).

**Step 4. Drop sections that are hummy, high gain, or where the amp track stops; size the pool.**
- *What happens:* sections are removed for part A's flags (not hiss), a D2 fail, high gain, or an amp track
  silent on 30% or more of the DI's playing frames. Heavy bands are capped at 20%.
- *Code:* `learn/cc_build.py:1409` (`candidates`), `:1467` (`amp_silent`), `:215` (`heavy_trim`),
  `:236` (`allocate`).
- *Status:* Problem (size, not cleanliness).
- *Evidence:* `s04`.
  - D_CC trains on 2,699 examples from 262 sections (32 DIs, 9 bands), and early-stops on 334 from 32 sections.
  - F5 planned 4,129 from 59 sections in 4 bands.
  - About 10 kept examples per section (2,699 / 262; 13 planned, 3,467 / 262): the same performance with
    different settings.
- *Fix:* more sections (the unplanned size-matched top-up, F20), or several settings per riff on purpose.
- *Test:* P2 (if a clean-input model learns at this size, size is not the first problem).

### Making up a preset for each example

**Step 5. Pick an amp, and a class by a coin flip.**
- *What happens:* the amp is uniform over three. The class ("base", clean or crunch) is a fair coin,
  independent of the section's sound. The network is conditioned on that coin in training, but on V-real it is
  given the part's real class.
- *Code:*
  - the draw: `learn/pretrain_set.py:297` (`plan_example`);
  - training's conditioning: `learn/direct_stems.py:2386` (`StemData.batch`: `cond_vec(..., rows[j]["base"], ...)`).
    The same call at `:700`, `:789` and `:857` is in audit tools (`audit_cost`, `cmd_reliance`, `cmd_audit_mix`),
    not in training;
  - V-real's: `learn/trusted_data_t3.py:1508` and `learn/cc_readout.py:381` (`cls, _ = part_info(...)`).
- *Status:* Suspect.
- *Evidence:* `s05`: the coin differs from the section's class in 1,512 of 3,033 kept examples (49.9%). The
  coin shapes the label mostly through start-mode draws (20%), which centre on that class's S.
- *Verify:* whether the trained network uses the input at all (P6).
- *Fix:* condition on the section's class (as on V-real), or drop the input.
- *Test:* P6.

**Step 6. Draw the settings.**
- *What happens:* 40% of draws are near a random factory preset (σ 0.1 in unit space), 20% near S, and 40% fully
  random, over 116 controls. A switch keeps its centre's state with p 0.7, else it is a coin.
- *Code:* `learn/pretrain_set.py:86` (`MODES`), `:306` (`settings_for`); `learn/full_space.py:264`
  (`draw_once`), `:313` (`draw_new`); `learn/trusted_data_t3.py:362` (`full_twin`).
- *Status:* Suspect. This prior is not what real presets look like, and it makes the constant wet (step 37).
- *Evidence:* `s06`, D_CC's 2,699 kept training examples.
  - Modes after refusals: factory 1,268, wide 788, start 643.
  - Switch on-rates: drive1 36%, drive2 39%, compressor 49%, reverb 52%, delay 48%, tremolo 32%, doubler 29%,
    gate 57%.
  - Factory draws: reverb on 73%, delay 62%. Start draws: 16% and 16%.
  - Delay feedback when on: median 0.33, 90th percentile 0.75; 10% at 0.75 or more (runaway risk, pool plan).
- *Fix:* centre draws on dried factory presets, or on real-song statistics. Or leave the time effects to
  `generate`'s song research (the ROADMAP's hybrid).
- *Test:* P3 shows how much of the loss is the prior's average.

**Step 7. Throw away draws that render near-silent.**
- *What happens:* a target render below −50 LUFS, or silent, is refused.
- *Code:* `learn/trusted_data.py:133` (`RENDER_FLOOR_LUFS`), `:432` (`near_silent`).
- *Status:* Problem. The refusal removes mostly wide draws, so what remains is not the declared mix.
- *Evidence:* `s07`.
  - 614 of 3,890 targets refused (15.8%). Wide: 589 of 1,557 (38%); factory 25 of 1,565 (1.6%); start 0 of 768.
  - Another 242 were refused because another guitar rendered near-silent (factory 118, wide 72, start 52), and 1
    for no backing. That makes 857 refused, and 3,890 − 857 = 3,033 kept.
- *Fix:* F20's declared redraw (up to 5 tries) keeps the mode mix.

**Step 8. The label is the exact settings.**
- *What happens:* a knob counts when its feature is switched on, on the selected amp, with a cab on. How
  audible it is plays no part: a delay at 1% mix counts in full.
- *Code:* `learn/full_space.py:188` (`encode`), `:177` (`sounding`); `learn/every_control.py:402` (`mask`).
- *Status:* Problem (known).
- *Evidence:*
  - [Audibility outcome](trusted-data-t0-design.md#audibility-outcome-2026-10-27-fresh-run-2686-renders-audited):
    23–59% of "on" time effects sit below tau in the mix.
  - Step 4's ear page: 21 of 25 pairs heard the same, 4 maybe, none different.
- *Fix:* the audibility-weighted labels the user pointed to (ROADMAP (c)).
- *Test:* P2a shows which heads are learnable even from the clean render.

### Rendering

**Step 9. Prepare the DI: re-EQ to an average guitar, −22.9 LUFS.**
- *What happens:* the DI is EQ'd to the average guitar's long-term spectrum (1/6 octave, ±15 dB) and set to
  −22.9 LUFS. Scoring renders through the same "measure DI".
- *Code:* `learn/song_bank.py:287` (`measure`), `learn/knob_ceiling.py:364` (`measure_di`).
- *Status:* OK. Training and scoring agree.
- *Caveat:* this convention caps even the true preset at about 0.55 of S's distance on known-answer songs, whose
  records are Morgan renders ([direct-existing results](direct-existing-results.md)). The same record found that
  on stage F's real records, judging with the raw DI instead did not measurably widen the differences between
  arms. See step 35.
- *Test:* P4 reads whether learning from these renders carries over to real recordings.

**Step 10. Render the target.**
- *What happens:* each target is rendered in a new plugin process, after one discarded warm-up render of the
  same setting and DI. F5 used one shared process with a primer on each (section, amp) change, so its time
  effects ran on across examples.
- *Code:* `learn/cc_build.py:1667` (`render_target`), `learn/audibility_measure.py:140` (`fresh_render`).
- *Status:* OK for D_CC. Repeats are bit-exact, and F5's positive control matched 50 of 50.
- *Caveat:* the kept render starts with the warm-up's effect state. That is realistic for a song, but a runaway
  delay builds over two passes (step 6).

**Step 11. Fold the render to mono.**
- *What happens:* the renderer's stereo output is averaged to mono before it is saved.
- *Code:* noted in the [tone probe](tone-info-probe.md)'s inputs ("every stored render is mono").
- *Status:* Problem. Stereo-only controls (cab pans, cab stereo, doubler spread, ping-pong) are labelled but
  unhearable in every input.
- *Fix:* leave stereo-only heads out of the loss and write them at S, or render and feed stereo.
- *Test:* P2a's per-head table.

**Step 12. Render the section's other guitars.**
- *What happens:* an ordinary other guitar gets a random dried factory preset (no delay, reverb, tremolo,
  doubler or gate). A DT double gets the target's *core* setting: today's 25 controls drawn on a dried centre,
  not the target's full label.
- *Code:* `learn/cc_build.py:1761` (`if o["dt"]:` takes `cores[...]`), `learn/trusted_data_t3.py:362`
  (`full_twin` returns the core setting beside the full one), `learn/trusted_data.py:202` (`other_settings`).
- *Status:* Suspect. The double plays the same part as the target with different pedals, in the input the label
  describes.
- *Evidence:* `s12`: 606 of 3,033 kept examples have a DT double. Against the target's label, the double's
  switch differs for drive1 in 210 (35%), drive2 in 209 (34%) and the compressor in 237 (39%). In 470 of the
  606, the target has a time effect on and the double has none.
- *Fix:* render a double with the target's full setting (a doubled part usually shares the rig), or leave
  doubles out.
- *Test:* P7.

### Building the fake song

**Step 13. Add the backing, the other guitars and recorded stand-ins.**
- *What happens:* the backing is the session's non-guitar stems, with vocals on half. A guitar that cannot be
  rendered enters as its own recorded amp track (a "stand-in"); the non-guitar bleed gate on stand-ins is off
  (the user, 2026-10-29).
- *Code:* `learn/trusted_data.py:1219` (`apply_rule1`), `:1304` (`stems_for`), `:215` (`pick_others`);
  `learn/cc_build.py:110` (`BLEED_GATE`).
- *Status:* Suspect, as a confound between D_CC and D_F5 rather than as an error.
- *Evidence:* `s13`: 1,335 of 3,033 D_CC examples carry stand-ins (44%); F5 had none.

**Step 14. Set the target's level against the backing.**
- *What happens:* a band is drawn, then one of its measured guitar-to-backing ratios. The mix is set to the eval
  median loudness ± 3 LU.
- *Code:* `learn/pretrain_set.py:402` (`ratio_values`), `:413` (`mix_params`), `:383` (`mix_gains_db`).
- *Status:* Suspect (minor).
- *Evidence:* `s14`: the ratio's median is −9.1 dB (10th percentile −18.0, 90th −4.4; range −30.3 to +19.1).
- *Two details from code reading, effect unmeasured:*
  - the ratios are mean-power ratios against the full backing (`learn/multi_section.py:193`), applied in the
    mix as a loudness ratio;
  - the ratio prior (971 values from 17 bands) holds 6 of the 7 V-real bands' measurements (Atlantis Bound,
    Diesel13, Eat The Feeder, Magician's Nephew, Wall Of Death, Zeno), including 36 from a V-real part's own
    sections (It Was My Fault ElecGtr1). These are level statistics, not labels (`s14`'s `ratio_prior`).

**Step 15. Master half of the mixes.**
- *What happens:* an RMS compressor (ratio 2–4) and a hard clip at −1 dBFS, with p 0.5.
- *Code:* `learn/song_aug.py:98` (`compress`).
- *Status:* Suspect (minor). V-real's mixes are unmastered unity sums of the session's tracks, so the mismatch
  runs the other way.
- *Evidence:* `s14`: 51% mastered.

**Step 16. Separate the guitar with X-LANCE.**
- *What happens:* X-LANCE `gtr_mss` runs on the mono 10-s mix. Its output is every guitar in the mix, not the
  target's.
- *Code:* `learn/direct_stems.py:1807` (`XLanceG`).
- *Status:* **Problem: the leading suspect for step 29.** The label describes one guitar the model has no way to
  single out.
- *Evidence:* `s16`, target render against stem:
  - D_CC: median −6.2 dB; 87% below 0 dB, 58% below −5 dB. F5: median −5.7 dB.
  - By the number of other guitars: none +6.7 dB (78 examples), 1 −2.7, 2 −5.7, 3 −5.7, 4 −7.7, 5 −8.0, 6 or
    more −8.5.
  - The target is the only guitar in 78 of 3,033 examples.
  - V-real is denser still: 9 of its 10 stage-F parts have at least 4 guitars playing
    ([T2 diagnostics](trusted-data-t0-design.md), "V-real is denser"). In D_CC, 1,872 of 3,033 examples (62%)
    have at least 4.
- *Fix:* a training target the input can identify. Options:
  - label what the stem holds;
  - restrict training and use to sections where one guitar dominates;
  - give the model a cue for which guitar the user means (the product's "time where the guitar plays" is not
    one when several play).
- *Test:* P2b against P2c.

### What the model sees

**Step 17. Turn the stem into features.**
- *What happens:* a 96-band log-mel (30 Hz–16 kHz, 10-ms hop, level kept), quantised to 0.5 dB, for one 4.5-s
  half. Half A's first second is blanked. Inputs are the stem, its loudness, the amp and the class; the mix
  channel is zeroed.
- *Code:* `learn/direct_stems.py:1045` (`half_features`), `:1206` (`zero_inputs`), `:2420` (`model_input`),
  `:3874` (`step4_half`); `learn/song_aug.py:66` (`logmel`); `learn/pretrain_set.py:348` (`quant`), `:364`
  (`mask_half_a`); `learn/song_model.py:116` (`norm_feat`), `:121` (`cond_vec`).
- *Status:* OK. Training and V-real share one code path, and [direct-existing](direct-existing-results.md)'s
  parity check matched stored features.

**Step 18. Augment in training.**
- *What happens:* p 0.05 the stem is replaced by the mix; p 0.2 another target's mel is merged at −12 to 0 dB;
  p 0.3 there are 1–3 dropouts; p 0.3 the highs above 3–8 kHz are darkened by up to 15 dB.
- *Code:* `learn/direct_stems.py:1287` (`augment`).
- *Status:* Suspect. Darkening may hide the treble cues that bright, EQ and mic labels depend on.
- *Evidence:* D_F5-noaug − D_F5 +0.051 [−0.049, +0.150], undecided
  ([D_F5mix outcome](trusted-data-t0-design.md#d_f5mix-outcome-2026-10-27-165-renders-audited)). It leans towards
  augmentation helping, against the suspicion.

**Step 19. How much tone survives to the input.**
- *What happens:* nothing here; this is a measurement of steps 13–18.
- *Status:* Problem, located.
- *Evidence:* `s19`, [tone probe](tone-info-probe.md): a linear probe reads 86 of 116 heads from the clean
  render, 30 from the self-built mix and 20 from the stem. Most of the loss happens at the mix (55 heads), before
  the separator. The DI alone reads 8.
- *Test:* P2's rungs repeat this with a trained model and a by-sound score.

### Training

**Step 20. The network.**
- *What happens:* four residual conv blocks (16, 32, 64, 96 channels), mean and std pooling over time, and two
  256-unit layers. Heads: a 4-component mixture density for 85 knobs, 28 switches, 2 ten-way mics, and the amp.
  About 1.07M weights (estimated from the file size), trained from scratch.
- *Code:* `learn/full_space.py:388` (`build_net`); `learn/pretrain_set.py:119` (`WIDTHS`);
  `learn/song_model.py:31` (`K_MIX`).
- *Status:* Unchecked. Nobody has shown it can fit even its training set.
- *Test:* P1.

**Step 21. The loss.**
- *What happens:* an unweighted sum of four terms: the mixture's negative log-likelihood over sounding knobs
  (per-example mean), masked binary cross-entropy for the switches, cross-entropy for the mics, and
  cross-entropy for the amp.
- *Code:* `learn/full_space.py:439` (`loss_fn`).
- *Status:* Suspect. It scores knob units, not sound. Many settings sound alike, and every knob weighs the same,
  audible or not.
- *Evidence:* even from the clean render, the probe's 55 readable knobs gain a median 3.1 points of their range
  over the constant, whose own error is about 17 points ([tone probe](tone-info-probe.md)).
- *Fix:* audibility weights (step 8), or a loss that scores the sound.
- *Test:* P2a's by-sound read against its by-knob read.

**Step 22. How much training.**
- *What happens:* Adam at lr 1e-3, batch 64, one random half per example per epoch, at most 40 epochs, with
  patience 4.
- *Code:* `learn/direct_stems.py:2507` (`train_arm`), `:890` (`MAX_EPOCHS`); `learn/pretrain_set.py:120`.
- *Status:* **Problem: a leading suspect.**
- *Evidence:* `s22`, from the run logs.
  - D_CC: 43 steps an epoch. Seed 20261042: best at epoch index 27 (the 28th epoch), 1,204 steps; the whole run
    took 8.3 minutes. Seed 20261043: best at epoch index 9, 430 steps; 3.6 minutes.
  - D_F5: 880 and 1,155 steps. D_core5: 1,155 and 1,815.
  - Training loss moves only 5.83 → 5.05 (D_CC 20261042).
  - Part C kept improving with far more data ([part C results](pretrain-set-results.md)). On true mixes, E was
    0.193 at 5k examples, 0.187 at 10k and 0.180 at 20k, then flat. On the guitar alone it still improved from
    20k to 40k (0.176 → 0.169). That record reports no constant. For scale only: the stems pilot's constant
    scored E 0.203, a different readout ([constant research](research/direct-model-constant-2026-10.md)).
- *Test:* P1, then a learning curve inside P2a.

**Step 23. Early stopping.**
- *What happens:* stopping uses the summed loss on the FS set, in eval mode, on a fixed half. The same set also
  fits the pull (step 26) and R0's readability (step 29).
- *Code:* `learn/cc_build.py:199` (`fs_sections`); `learn/pretrain_set.py:120` (`PATIENCE`).
- *Status:* Problem. The stopping set measures new settings on performances the model has already seen, not
  new songs.
- *Evidence:* `s23`.
  - D_CC: all 32 FS sections share a session with training, 30 share a DI, and 26 overlap a training section in
    time.
  - F5: all 12 share a DI, none overlap.
  - The stopping loss falls only 5.74 → 5.35 / 5.44.
- *Fix:* stop on held-out songs or bands, and on a metric that follows the sound.

**Step 24. What training logs.**
- *What happens:* each epoch logs only the total training loss (with dropout and augmentation) and the total
  stopping loss.
- *Status:* Unchecked. Three things were never read:
  - an eval-mode training-set loss (can it fit?);
  - per-head losses (which heads learn?);
  - the constant's loss on the same examples (does it beat the average in its own units?).
- *Evidence:* `s22`'s `logged_per_epoch`.
- *Test:* P1 adds all three.

### Turning outputs into a preset

**Step 25. Read each knob.**
- *What happens:* each knob takes the median of its predicted mixture, averaged over 2 seeds (A1, A2).
- *Code:* `learn/direct_stems.py:2982` (`mixture_median`), `:3002` (`median_answers`).
- *Status:* OK. This is the [constant research](research/direct-model-constant-2026-10.md)'s recommendation.

**Step 26. Pull each knob toward the training average.**
- *What happens:* answer = constant + b × (model − constant), with b in [0, 1] fitted per knob, amp and class on
  the FS set. A knob without a fitted b gets b = 0.
- *Code:* `learn/direct_stems.py:3024` (`fit_pull`), `:3076` (`pull`), `:3086` (`cell_b`), `:2873`
  (`label_medians`).
- *Status:* Problem. The pull's target is the training average, which leans worse than S on real songs (step 37).
  It is fitted in-sample on FS.
- *Evidence:* `s26`.
  - D_F5: median b 0.39; b = 0 for 36% of cells, 1 for 36%.
  - D_CC: median b 0.50; b = 0 for 38%, 1 for 41%. Its two fit folds disagree (median b 0.32 and 0.51).
- *Fix:* pull toward S instead.
- *Test:* P3.

**Step 27. Switch a feature on above 0.5.**
- *What happens:* a switch is on when its seed-mean probability exceeds 0.5. Mics and the amp take the argmax.
- *Code:* `learn/full_space.py:486` (`readout`), `learn/trusted_data_t3.py:1461` (`full_answer`).
- *Status:* Problem. A head that learned nothing sits near its training rate, and a 0.5 cut flips the whole
  pedal on or off.
- *Evidence:* `s27`, the 14 PR12-crunch directions.
  - D_CC writes drive2 on in 0 (its seeds: 2 and 0); its own constant writes it on in all 14; D_F5 in 12.
  - D_CC with its pedals at S − D_CC: −0.076 [−0.142, −0.011], better in all 7 bands.
  - D_CC − its own constant: +0.103 [+0.051, +0.155], worse in all 7 bands.
  - The drive2 probability there is 0.42–0.50, against an on-rate of 52.7% in its labels (pool plan,
    `amendment_4_outcome`).
- *Fix:* a switch whose head does not read on held-out data keeps S's state; or calibrate the threshold.
- *Test:* P3.

**Step 28. Everything else stays at S.**
- *What happens:* only controls that can sound on the chosen amp are written; switched-off features are
  neutralised; sync off; at least one cab on.
- *Code:* `learn/full_space.py:334` (`answer_settings`).
- *Status:* OK.

### The fake-song test

**Step 29. D_F5 on held-out sections of its own songs (FS5).**
- *What happens:* R0's rule: a head is readable when its 90% interval beats the constant (knobs by error,
  switches by AUC, the amp and mics by accuracy).
- *Code:* `learn/trusted_data_t3_r.py:170` (`r0_rows`).
- *Status:* **Problem: the central failure.** The model fails before any real song is involved.
- *Evidence:* `s29`.
  - Knobs: 5 of 85 readable, about chance (about 4); 9 reliably worse than the constant. The median error is
    0.177, against the constant's 0.172.
  - Switches: 14 of 28 readable but weak. AUC: drive2 0.67, compressor 0.59, doubler 0.58, drive1 0.58, delay
    0.56, gate 0.52, tremolo 0.51, reverb 0.49.
  - Amp choice: accuracy 0.40 against a base rate of 0.33, readable: +0.069 [+0.033, +0.105].
- *Test:* P1 and P2 say whether it is the model (20–24) or the input (13–19).

**Step 30. The fake-song test by sound.**
- *What happens:* never done. The model's answers on FS have not been rendered and judged against their known
  targets, so knob error is the only in-distribution score.
- *Status:* Unchecked.
- *Test:* P2's by-sound read. It also covers the case where wrong knobs still give the right sound.

### The real-song test (V-real-11)

**Step 31. The test parts.**
- *What happens:* 11 parts in 7 bands, 4 clean and 7 crunch, frozen on 2026-10-26.
- *Code:* `learn/trusted_data_t3.py:120` (`vreal_membership`).
- *Status:* Problem (size). Wickerman's three parts make one band, and 3 of the 11 parts come from that one
  song. Single parts swing results: femme ElecGtr5, Wall Of Death's only part, reads D_CC − D_F5 +0.363, and
  without it the row is +0.044 (pool plan, D_CC's outcome).

**Step 32. What the model reads on a real song.**
- *What happens:* X-LANCE separates the crop's mix, which is a unity sum of the session's tracks with every
  amp track in it, the target's and the other guitars'. The mix is brought to the training median loudness and
  the stem gets the same gain.
- *Code:* `learn/trusted_data_t3.py:1477` (`cmd_vreal_predict`), `learn/direct_existing.py:179`
  (`inference_gain_db`).
- *Status:* Problem.
- *Evidence:* `s32`: Wickerman ElecGtr2 and ElecGtr3 have byte-identical stored stems (one sha256), so D_F5
  writes the same answer for both, and each is scored against its own amp track.
  - The cause: both crops cut the same window (170.5–180.5 s), so their mixes are sample-identical. Their amp
    tracks and DIs are uncorrelated, so they really are two parts (checked by the review).
  - Step 16's density applies.
- *Test:* P4 (the real guitar alone) separates "Morgan renders don't transfer" from "the stem is the wrong
  guitar".

**Step 33. Render each answer.**
- *What happens:* each answer is forced onto each of the 3 amps, for each half (66 directions), on S's factory
  select, and rendered through the part's measure DI. One warm-up render at S per (part, amp) group, then the
  answers in a fixed order.
- *Code:* `learn/trusted_data_t3.py:1328` (`vreal_dirs`), `learn/direct_stems.py:3252` (`run_group`),
  `learn/knob_ceiling.py:441` (`Renderer`).
- *Status:* OK, with a caveat. Answers with time effects in one process carry phase noise from render order
  (ROADMAP (c), flagged, not fixed).

**Step 34. Judge each render against the real amp track.**
- *What happens:* `aligned_distance` at the part's fixed lag. Each side is level-matched. Bands and the floor
  come from the recording. Each playing frame is extended by 1.5 s of tail. The score is the mean |ΔdB| over
  three frame sizes.
- *Code:* `analysis/aligned.py:331` (`aligned_distance`, `tail_s=1.5`), `learn/knob_ceiling.py:485` (`judge`).
  Spec: [measuring-closeness.md](measuring-closeness.md).
- *Status:* OK. It explains the loss: wet answers lose against a dry recording, as they should.
- *Evidence:* `s34`, recomputed from the stored judges.
  - D_F5 − S is +0.088 (it reproduces the report). One part, Colour Me Red ElecGtr03, gives +1.000.
  - With D_F5's time effects and spring at S, D_F5 − S is +0.001 [−0.084, +0.086], and that part gives −0.118.

**Step 35. Aggregate and compare with S.**
- *What happens:* ln(d_answer / d_S) on the held half per direction, averaged per part, then per band, then over
  the 7 bands. A 90% band-clustered t interval with 6 df.
- *Code:* `learn/song_readout.py:57` (`bw_stats`).
- *Status:* Problem (power).
- *Evidence:*
  - `s34`'s interval widths: D_F5 − S 0.264, D_F5 − D_core5 0.289, D_F5 − constant 0.096, D_core5 − S 0.083.
  - The width depends on the arm. D_F5 − S's half-width of 0.132 is driven by Colour Me Red ElecGtr03 (+1.0).
    D_core5 − S's is 0.042, D_F5 − constant's 0.048, and D_CC − S's about 0.16. A difference smaller than the
    arm's half-width cannot be told from 0.
  - The measure DI caps the true preset at about 0.55 of S's distance (step 9).
- *Fix:* more verified parts (V-real-12 and beyond); a part-weighted co-primary.

**Step 36. Where S came from.**
- *What happens:* each class's S is, per amp, the factory preset with the lowest median `flat` measure-DI
  distance over development parts. The clean rule names set 3's `rescore` distances and the sets 1–2
  `songs-check` distances.
- *Code:* the rules are in [clean-baseline-plan.md](clean-baseline-plan.md) and
  [crunch-baseline-plan.md](crunch-baseline-plan.md); their choices are in `clean-baseline-choice.json` and
  `crunch-baseline-choice.json`.
- *Status:* Problem. S has a home advantage on V-real; its size is unmeasured.
- *Evidence:* `s36`.
  - The rules are re-derived exactly. On the pinned development parts (`docs/sound-desc-test-parts.json`: 22
    clean, 13 crunch), `pick_start` re-picks all six presets with the recorded parts-used counts (22, 13).
  - The crunch choice set holds all 6 of V-real's crunch clips (femme ElecGtr5, get-out-of-bed ElecGtr2, let's
    dance ElecGtr3, Wickerman ElecGtr1–3). 12 of its 13 parts come from V-real's bands.
  - The clean choice set holds Colour Me Red ElecGtr02 and ElecGtr03, and It Was My Fault ElecGtr1 on another
    clip (12.5–22.5 s in `validation-crops`; V-real's crop is 90–100 s, no overlap). So `s36` lists 3 V-real parts
    in the clean set, 2 of them on V-real's own clips. 5 of its 22 parts come from V-real's bands.
  - So 8 of the 11 V-real clips were in S's choice sets. Their stored S distances equal V-real's S values within
    4.1e-4. It Was My Fault ElecGtr3 and Signs ElecGtr3 are in neither set.
- *Test:* P5.

**Step 37. The training average against S.**
- *What happens:* the constant (per amp and class: knob medians, switch majorities, mic modes, from the
  training labels) is written on S and rendered like an answer.
- *Code:* `learn/direct_stems.py:2873` (`label_medians`).
- *Status:* **Problem: with steps 26–27 and 36, this explains "never beats S".** A model that reads little lands
  here or below (steps 26–27).
- *Evidence:* `s34`.
  - constant − S: +0.092 [−0.029, +0.213] (D_F5's constant). The interval holds 0, so it is undecided; it leans
    worse in 5 of 7 bands and 9 of 11 parts, and every leave-one-band-out mean is +0.042 to +0.123.
  - D_F5 − constant: −0.004 (it reproduces the report).
  - D_CC − its own constant: +0.103 (step 27).
- *Test:* P3.

### Headroom

**Step 38. How much room there is, with the true DI.**
- *What happens:* nothing new; this reads stored searches.
- *Status:* OK. There is room on these very parts, given the DI.
- *Evidence:* `s38`, stage F's ZT, a 52-render search with the true DI against the amp track,
  [arm-a-mega53 results](arm-a-mega53-results.md). On V-real-10's parts:
  - shrunk 0.5 toward S: −0.137 [−0.170, −0.104];
  - its best: −0.192 [−0.239, −0.145];
  - all 7 bands better in both.
- *Note:* the often-quoted −0.293 ([ks-ceiling-extend](ks-ceiling-extend-results.md)) is a different
  experiment: 24 development parts (It Was My Fault ElecGtr1 among them, on another clip), today's 25 controls, a
  longer search scored on the other half of the same clip. It is not V-real's ceiling.

## The checks run for this review

Each check reads stored files only. Its output is `checks.<name>` in [ml-pipeline-review.json](ml-pipeline-review.json).

| Check | Step(s) | What it reads | Result |
|---|---|---|---|
| `s04_pool` | 4 | `trusted-data/cc/plan.json`, build rows; `t3/plan.json` | 2,699 / 334 examples; 262 / 32 sections; F5 59 sections, 4 bands |
| `s05_class_input` | 5 | D_CC plan; `learn/direct_stems.py` | 1,512 of 3,033 coins differ from the class; lines 700, 789, 857, 2386 condition on it |
| `s06_label_prior` | 6 | D_CC plan (kept training examples) | switch on-rates; factory reverb 73%, delay 62%; feedback ≥ 0.75 in 10% |
| `s07_silent_refusals` | 7 | `cc/rows/render-*.jsonl`, `build-*.jsonl` | targets: wide 38%, factory 1.6%, start 0%; 857 refused in all |
| `s12_doubles` | 12 | D_CC plan's `core` and `settings`; `learn/cc_build.py` | 606 with a double; drive1 35%, drive2 34%, compressor 39% differ |
| `s13_stand_ins` | 13 | D_CC plan | 1,335 of 3,033 (44%) |
| `s14_level_draws` | 14, 15 | D_CC plan's draws; `multi-section/sections/*.json` | ratio median −9.1 dB; 51% mastered; prior holds 6 V-real bands |
| `s16_stem` | 16 | `cc/rows/build-*.jsonl`, `t3/rows/build-*.jsonl` | median −6.2 dB (F5 −5.7); 78 alone |
| `s19_tone_probe` | 19 | `tone-probe/probe.json` | 86 / 30 / 20 of 116 |
| `s22_training` | 20–24 | `cc/runs/*.json`, `t3/runs/*.json` | 430–1,815 steps to best; only total losses logged |
| `s23_early_stop` | 3, 23 | D_CC and F5 plans | D_CC 26 of 32 overlap in time; F5 0 of 12 |
| `s26_pull` | 26 | `t3/report.json`, `cc-readout/D_CC/fit.json` | b = 0 for 36–38% |
| `s27_switch_readout` | 27 | `cc-readout/D_CC/followups/report.json` | drives off; pedals at S −0.076 |
| `s29_fake_song_test` | 29 | `t3/followup-r/r0.json` | 5 of 85 knobs; switch AUCs |
| `s32_vreal_inputs` | 32 | `direct-stems/step4/stems/xlance_g/stems.json`, `t3/vreal/predictions.json` | Wickerman 2 = 3, answers identical |
| `s34_vreal` | 34, 35, 37 | `t3/vreal/groups/*.json`, `arm-a-mega53/F/S/`, `t3/report.json` | reproduces the report's rows to 1e-9; constant − S +0.092, 9 of 11 parts, leave-one-band-out +0.042 to +0.123 |
| `s36_s_selection` | 36 | `direc/rescore` and `songs-check` distances; the choice files; `docs/sound-desc-test-parts.json` | all six presets re-derived; 8 of 11 clips in the choice sets; S equal within 4.1e-4 |
| `s38_headroom` | 38 | `arm-a-mega53/F-perfect-sep/ZT/`, `F/S/` | −0.137 / −0.192 on V-real-10 |

Code readings checked by the author, beyond the three traces:
- the double's setting (`learn/cc_build.py:1761`, `learn/trusted_data_t3.py:362-370`);
- the class conditioning in training and on V-real (`learn/direct_stems.py:2386`, `learn/trusted_data_t3.py:1508`,
  `learn/cc_readout.py:381`);
- the ratio prior's bands (`learn/pretrain_set.py:402`, the 17 bands in `multi-section/sections/*.json`).

Tests: `tests/test_pipeline_review.py` covers the helpers (quantiles, the section overlap rule, band
weighting with its interval and leave-one-band-out, switch parsing, the start rule), the step naming, and that
every check reports a missing input instead of raising.

**Review (2026-10-30).** An independent review of PR #343 approved with required changes. All of them are made:
- the failure chain hedged (the constant leans worse than S, undecided; the model reads a few switches and the
  amp);
- step 36 proven by re-deriving both start rules;
- step 7 and step 22's run logs report a missing input instead of raising or staying silent;
- the per-section count, the audit-tool lines, the arm-specific intervals and the part C comparison corrected.

Its optional points are folded in too: step 7's other refusals, the run times, the AUC rounding, the test links,
the tests' limits, step 32's shared window, the re-run notes, step 14's V-real part and step 18's direction.
