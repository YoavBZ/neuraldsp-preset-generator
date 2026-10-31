# Roadmap

The one living plan. Update it when a result lands or a decision changes; the detail
lives in the linked documents. Last updated 2026-10-31.

## Where the product is

- **Input is a song.** The user gives a song (and a time where the guitar plays), never
  a DI of the performance.
- **The goal (user, 2026-10-14):** from a song and its research, generate the most
  accurate preset by setting every control the song needs. Choosing the closest
  factory preset is not the purpose; factory presets are starting points.
  *Every control (user, 2026-10-21):* every setting the plugin exposes (the pack
  manifests), not only input gain, the amp's knobs and the mics: the pedals, EQ, time
  effects, gate, room mics, pan, phase, output and the rest. The knob values of a
  switched-off feature all count as one setting.
- **`generate`** researches the song, sorts the part into clean, crunch or heavier
  (Tone King: clean or crunch only), starts from that class's dry factory preset, and
  sets the controls research documents (today mostly effects; amp, drive, EQ and cab
  kept unless research documents a different value for the part, since edits on top
  of the start were not shown to help; with the true DI, the ML session's search over the
  controls reaches −0.293 against S, step 0):
  - **Morgan clean:** Royally Ambient (PR12), Pedal Platform Clean (SW50R), Low-Watt
    Americana (AC20), about 12% closer than the template on held-out clean parts
    ([results](clean-baseline-results.md)).
  - **Morgan crunch:** Modern Metal (Pick Hard), Hair Metal, AC20 Mid-Gain Drive, about
    7% closer than the driven presets, weak evidence
    ([results](crunch-baseline-results.md)).
  - **Morgan heavier (out of focus):** Wall Of Doom, Vintage Metal, Dirty Coil Rhythm
    ([results](driven-baseline-results.md)).
  - **Tone King:** Vintage Trem (clean, about 12% closer than the plugin's Default made
    dry) and Squishy Lead (crunch, thin evidence), both on the Rhythm channel
    ([results](toneking-baseline-results.md)).
  - Before the starting presets, on 25 mostly clean recordings: a researched preset was
    not shown to beat the template, and a researched four not shown to beat four random
    factory presets; the judge picking from four landed about 18% closer than the
    template ([results](song-only-shortlist-results.md)). Over the new starting
    presets, the class costs most and the research edits are undecided (product steps,
    [routing check](generate-routing-results.md)).
- **The listening page** (`scripts/audition.py`) is offered, not built by default: four
  presets through CC-BY riffs, with a one-file phone version. Whether a real ear
  picks better with it was tested once and came out inconclusive
  ([results](listening-check-results.md)).
- **`match`** without a DI describes the recording and keeps the starting preset: no
  song-only search has been shown to get closer
  ([re-check: void](no-di-rule-under-the-judge-results.md)). With the same take's DI it
  searches; its known defects are fixed or parked, and its search objective is untested
  by ear (product steps; history in [roadmap-history.md](roadmap-history.md#product-steps-16-as-they-stood-on-2026-10-14), step 5).
- **`edit`** changes a preset from a plain-English ask.
- **Predicting a preset from the song** is active research, not yet in the product
  (step 0). Since 2026-10-14 the aim is to generate settings, not rank presets. Two routes are
  active: arm A (a search through a DI rebuilt from the separated guitar) and a direct model
  (song to settings). Neither is yet shown better than the starting preset on fresh full mixes:
  arm A reads −0.028 [−0.064, +0.008] with htdemucs and −0.046 [−0.091, −0.000] with Mega-53
  ([results](arm-a-mega53-results.md)); the first, untuned direct model +0.033 [−0.053, +0.119]
  ([results](direct-existing-results.md)), and the direct model trained on realistic stems −0.034
  [−0.103, +0.034] (run under a user override of a GATE STOP;
  [results](direct-model-stems-results.md)). Better separation is the shared lever (step 0). The
  earlier menu-ranking route is in the [history](roadmap-history.md). Since 2026-10-22 only trusted
  data counts (the user); the trusted-data plan's checks and the user's ear now come first (step 0).
  *2026-10-27:* learning every control (T3's F5) was not shown to help, and a zero-render probe finds the
  separator loses most of the tone the mix hides; the next steps start with a mix-aware input (step 0,
  "Where it stands, 2026-10-29").
  *2026-10-30:* a step-by-step [pipeline review](ml-pipeline-review.md) (zero renders) finds that the model reads
  almost none of the sound, even on its own made-up songs. With so little read, it scores about as well as its
  training average, which leans worse than S on the real songs (undecided). Seven tests (P1–P7) are proposed to
  find the failing step (step 0). *2026-10-31:* a [fix plan](pipeline-fix-plan.md) runs them and fixes each finding,
  in place of F20's draft (step 0).
- **The judge** ([measuring-closeness.md](measuring-closeness.md)) is how closeness is
  measured. It needs the DI of the same take, and listening validated it only for clear
  differences between clean-to-crunch PR12 renders
  ([listening validation](listening-validation-results.md)). One listener heard the
  starting presets as closer than what they replaced, in-sample
  ([listening](starting-preset-listening-results.md)). On 5 guitar-exposed parts the ear broadly
  orders presets as the judge does ([record match](record-match-listening-results.md)); judge v3
  agrees a little less, so the default judge stays ([check](shrink-snr-judge-v3-results.md)).

## Scope (user decision, 2026-10-10)

**Heavy metal and high-gain tones are out of scope.** Metal players would use a
dedicated Neural DSP metal plugin, not Morgan Amps Suite or Tone King, and those plugins
aren't covered. The project focuses on clean, edge-of-breakup and crunch tones.
- Evaluation, gates and tuning use clean and crunch material; high-gain parts are
  report only, at most.
- Set 3 and set 4 are mostly heavy. Their clean and crunch parts stay useful; their
  high-gain parts don't drive decisions.
- **The driven baseline in `generate`** (Wall Of Doom, Vintage Metal, Dirty Coil Rhythm)
  was chosen on heavy set-3 material. Whether it suits crunch songs is open: the next
  candidate is a crunch starting preset chosen on crunch material, as the clean one was.
  *Done 2026-10-10 ([results](crunch-baseline-results.md)): adopted on weak evidence. The
  ML chooser over it is not shown.*

**Refined for training (user, 2026-10-26):** high-gain songs can definitely be used for
training, as long as too-heavy songs don't interfere with the model. The user doesn't play
heavy metal, so testing and perfecting stay clean/crunch-focused.
- Training sources are no longer dropped for being high gain. "Scope by ear" screens out only
  extreme cases.
- Readouts stay clean/crunch-weighted and per class, to watch for interference.
- The 2026-10-25 Cambridge scan's metal sessions outside the held-out sets become possible
  training candidates: 11 sessions from 6 bands (Arcadian Alone, Daimon B ×2, Dark Illusion ×2,
  Inhumanity Vortex, Peppermark ×3, Serapis ×2), plus DGX ×2 (hard rock/metal). V.M.GY is a
  set-3 held-out band, so it is not a candidate. The user said yes, and these 13 were downloaded
  on 2026-10-26. Their intake is PR #297: the held-out checks, T0's
  checks and the ear. *Heard 2026-10-26: 50 of 89 DIs admitted, all high gain; 5 sessions too heavy.*

## Next, in order

0. **Song-to-preset model** (the ML session; [plan](research/ml-plan-2026-10.md), approved by the
   user on 2026-10-14). Everything this section said before 2026-10-19, including the earlier
   menu-ranking work and its numbered steps, is kept unchanged in
   [roadmap-history.md](roadmap-history.md#step-0-the-song-to-preset-model-as-it-stood-on-2026-10-19).

   **The goal (the user's, 2026-10-14):** set every control so the preset sounds as close as
   possible to the song. With the true DI, a search over the controls reaches **−0.293 [−0.378,
   −0.207]** against the starting preset S ([ceiling](ks-ceiling-extend-results.md); a lower bound),
   so the plugin has the headroom. The question is how much of it a song alone can reach.
   *Coverage (2026-10-21):* both active routes set only `knob_ceiling.space` on Morgan: input
   gain, the amp's main knobs and switches (not its spring), and the mics with their cab
   placement. The rest, the amp choice included, stays at S, so neither covers the goal yet.
   The ML session's plan for how and when each route covers every control
   ([every-control plan](every-control-plan.md), PR #266) was **approved by the user on 2026-10-22
   for its first stages**; switched-off knobs are left out of losses, scores and fits. Stages 0
   (the full-space table, amp choice from stored cells, a screen of what the judge can hear, Tone
   King's search renderer) and 1 (a true-DI oracle for Morgan's unmeasured groups and Tone King's
   whole space, about 13k renders) are built. **Every control is learned (user, 2026-10-22):** no
   fixed rule stands in for a control the judge can't hear; the stage 0 screen only sets
   priorities. *Stage 0 done 2026-10-22 ([results](every-control-stage0-results.md), 94 renders):*
   amp choice pays against an amp chosen blind, band-weighted −0.048 (the plan's weighting) and
   part-weighted −0.044 [−0.062, −0.026] (22 of 24 parts, 13 of 14 bands; high priority); no
   screened control is invisible to the judge, and cab phase moves it most; Tone King's renderer
   repeats its stored scores. **Stage 1 runs on trusted parts only** (the user's decision) and can
   now run, not yet run: the trusted amp-track list now exists (T0's lists after the ear, 2026-10-25;
   7 panel parts). It needs that list, not the rebuild: it is a true-DI oracle on amp-track targets, with no backing
   or stem.

   **Where it stands (2026-10-31).** Not ready to ship; the detail is in the trusted-data items below.
   - **Pipeline fix plan (2026-10-31; [plan](pipeline-fix-plan.md), code `learn/pipeline_fix.py`, ledger
     `pipeline-fix`).** At the user's request every finding of the pipeline review below is to be fixed and verified,
     with none left open: each ends as Fixed, Ruled out, Limit, measured or User decision. It replaces F20's draft
     (PR #345) as the next step. Reviewed (12 required changes, all made).
     - **The order:** a fair yardstick (S's home advantage, Wickerman's duplicate input, render-order noise); the
       wrong training data fixed (DT doubles, runaway targets); where the tone is lost (P1, then P2's ladder of inputs:
       the clean target, the target in its backing, the mix, the stem, read by knob and by sound, on new settings and
       new songs); the located fix and one model with every fix (D_fix), chosen without V-real; then V-real, with P3's
       fallback to S as a measurement (the user's 2026-10-27 ruling stands) and P4 (real amp tracks as input). Scale
       (F20) only if the learning curves rise.
     - **Outcome (2026-10-31, audited; the plan's findings log F1–F28).** Each finding was fixed or tested on its
       own, relying only on parts already verified (the user's rule).
       - **The model can learn the tone.** Fed the clean guitar (a perfect separator), it sounds −0.241 [−0.318,
         −0.165] closer than S on 2 held-out songs, also when told a wrong amp. Knob error badly understates this, so
         every read is now by sound (F11, F19). By knob, a 5-fold new-song test reads every one of the 9 training bands
         better than the constant, by about 1 point of a knob's range (F28).
       - **Blocker 1, the mix:** any backing erases the skill. With only drums, bass and vocals it is even with S; the
         other guitars and the separator add no further loss (F15, F17). Eight backings per target, from other songs'
         stems (no new renders), recover 27% [13%, 42%] of it (F24).
       - **Blocker 2, real recordings:** fed V-real's real amp tracks (the guitar alone), the model is +0.153 [+0.039,
         +0.268] against S, and no transfer is detected: it is not shown better than its own training average (F20).
         Its penalty is mainly the core tone; the time effects are a small, undecided part (F26). The presets that suit these real parts sit at the training prior's edges about 3× as often as its own labels
         (F27).
       - **Fixed or verified alone:** the doubles (F16), early stopping (F18), the class input (F2), the by-sound read
         (F10).
       - **Ruled out as blockers:** the network (F5), the readout's pull (F12), the switch readout for a model that
         reads (F23, in distribution), and mastering for the guitar itself (F22).
       - **Not shown to help:** augmentation on the clean input (F21; song-fed untested), and more of the same data
         for the clean input's sound (F25: a 3.5× size increase bought about 0.04, undecided).
       - S's home advantage on V-real is small (F1). The near-chance rule from the F20 build's draft costs sound and is
         not recommended (F23).
       - **Community presets** (the user's question, 2026-10-31; the session's recommendation, pending the user's
         yes): as centres for the next build's draws, with a wide share kept and the effects dried, after the two
         blocker tests. They may improve the prior's coverage (F27; a zero-render check first), not whether the model
         reads real recordings (F20). Morgan Amps Suite X's presets need a plugin update: the user's yes and a parity
         check first.
       - **Phase 5 (2026-10-31, after the user's "Continue"; F29–F31).**
         - Blocker 1: backings from 13 more songs (24 per target, zero renders) recover about half of the loss on
           the held-out songs, 0.50 [0.29, 0.73] over two seeds, against a quarter with 8; the model also overfits
           far less (F29). About half remains.
         - Blocker 2: the pool's recorded amp tracks could not be used: the stock bleed check fails nearly all of
           them, but it also fails reamped and software tracks (bleed-free, inferred from their chain) through its power
           sum, so it is unreliable on amp tracks (F30). Read instead on BKS's reamped tracks (real amps, 8
           performances, known playing), the model is +0.066 [+0.030, +0.102] against S, leaning better than its
           labels' constant (undecided by DI): part of the real-amp gap appears even with known playing (+0.07 here,
           +0.15 on V-real, unpaired). The labels' average ties S on plugin renders but falls +0.119 behind it here
           (F31).
         - Re-centred on S (F32, exploratory), the model's real-amp penalty is gone and its per-track readings lean
           better than S, by about 0.03 (undecided); the shared shift alone is not seen to help. A V-real read of this
           readout (5B.1c) was withdrawn before rendering: likely undecided on 7 bands; V-real is left for D_fix.
       - **Next:** 5B.2, labels that reach real-amp tones (a true-DI search on the reamped tracks), declared and
         reviewed before it runs; community presets (pending the user's yes) bear on the same gap.
   - **Pipeline review (2026-10-30, zero renders; [record](ml-pipeline-review.md), checks `learn/pipeline_review.py`).**
     At the user's request, the direct model's whole process is listed as 38 small steps. Each step has its code, a
     status, its evidence, a fix and a test.
     - **The failure chain, each link measured:**
       - On held-out sections of its own training songs, D_F5 reads 5 of 85 knobs (about chance), 14 of 28
         switches weakly (AUC at most 0.67) and the amp slightly (step 29).
       - With so little read, the readout scores about as well as the training average, or worse: the pull, and
         the 0.5 switch cut that flips pedals (steps 26–27).
       - That average leans worse than S on V-real: +0.092 [−0.029, +0.213], undecided, 9 of 11 parts worse,
         recomputed (step 37).
       - So "never beats S" is what steps 29, 26–27 and 36 together predict.
     - **Leading suspects for step 29:**
       - The stem holds every guitar in the mix: the target a median 6.2 dB under, alone in 78 of 3,033 examples.
         On V-real, Wickerman ElecGtr2 and ElecGtr3 give byte-identical inputs (steps 16, 32).
       - Very little training: 430–1,204 steps (step 22).
       - Labels for inaudible and stereo-only controls (steps 8, 11).
       - DT doubles rendered with different drive switches (34–35%; step 12).
     - **New measurement caveats:**
       - S was chosen with the same judge on choice sets that hold 8 of V-real's 11 clips, including all 6 crunch
         clips; both start rules are re-derived exactly from stored distances (step 36).
       - On V-real-10's own parts the true-DI search reaches −0.137 shrunk and −0.192 at its best, not the −0.293
         measured on other parts (step 38).
     - **Proposed** (*2026-10-31: run under the [pipeline fix plan](pipeline-fix-plan.md); P7 dropped, its question
       answered by fixing the doubles*):
       - P5: re-pick S without V-real's clips;
       - P6: flip the class input;
       - P7: drive AUC with and without doubles;
       - P1: a memorise check;
       - P2: a model on the clean target renders, then one harder input at a time, read by knob and by sound;
       - P3: fall back to S instead of the average;
       - P4: real amp tracks as input.
   - **The clean/crunch pool is built and its first model read (2026-10-30)** ([plan](clean-crunch-pool-plan.md)):
     - The pool: 294 song sections from 33 target DIs in 9 bands (50 DIs passed the checks; 93 clean, 201 crunch;
       heavy 2%), after the data-checks audit (amendment 1, PR #329) and the user's decisions and ear pages 13–15
       (amendment 2, PR #332). D_F5bk (the
       backing fix alone, 2026-10-29) read undecided.
     - D_CC, trained on it, reads +0.090 [−0.011, +0.191] against D_F5 on V-real-11 (positive is worse; 1 band
       better, 6 worse): undecided, leaning worse. Clean +0.015, crunch +0.120. Part-weighted (descriptive) +0.090
       [+0.006, +0.175], 9 of 11 parts worse, which supports "leaning worse". It also trails D_core5, S and D_F5's
       constant (descriptive). Audited: no bug. Most of the loss (post hoc, descriptive): both drives off in all 14
       pr12-crunch directions, where D_F5 had drive2 on in 12, and one part (femme ElecGtr5) gives +0.363.
     - D_CC's follow-ups read (2026-10-30, audited; ledger `amendment_4_outcome`, 165 renders): both seeds'
       answers turn those drives off (answers only, not rendered; not the early-stopped seed alone). The sound rows
       are of D_CC's pooled answer: with its pedals at S, D_CC gains −0.076 [−0.142, −0.011]
       (all 7 bands) and is about even with D_F5 (pedals at S both: +0.015 [−0.028, +0.057], undecided), so the
       loss is mostly its pedal answers: drive2 sits near chance (probability 0.42–0.50; on in 52.7% of the
       labels) and a 0.5 readout turns it off. D_CC is worse than its own pool's constant, +0.103 [+0.051, +0.155]
       in all 7 bands (descriptive): on V-real the model does not yet beat a constant.
     - Confounds: fewer examples than D_F5 (2,699 + 334 against 3,467 + 722), a small early-stopping set, and
       recorded amp-track stand-ins in 44% of the examples.
     - Step 4's page sent (2026-10-30, audited): 25 items on clean/crunch mixes, 266 renders. 13 of the 25 items
       come from one song. Its answers came the same day (audited; ledger `amendment_3_answers`): no pair heard as
       clearly different, the four anchors included, so the page does not place tau by ear. A drive-pedal page
       with an instant A/B switch (ledger `amendment_5`) was rendered, audited and sent 2026-10-30
       (`amendment_5_outcome`: 96 renders, 17 items, about 8 min; its in-mix answers are not being asked for, the
       guitar-only answers replace them); its checks, step 4's loudest
       reverb and spring pairs, take the place of the replay of three items, which the author dropped (reported to
       the user 2026-10-30); step 4's item 4 (900215, the runaway delay) is not re-used, being a dirty (runaway)
       example. Its delay anchor is a runaway delay (a steady whine), and a zero-render scan found such targets in
       about 2% of both pools (D_CC 64 of 3,033, D_F5 87 of 4,189); excluded from the next build (F20's runaway
       check, to be declared and reviewed in the re-plan).
     - The user then asked for the guitar alone (2026-10-30: "The mixes make it harder to distinguish, please only
       the guitars if possible", then "Same for the previous effects listening page"): guitar-only versions of the
       drive page (17 items) and step 4's page (25 items, its runaway item 4 replaced by the loudest non-runaway
       delay pair, 803054) are declared (ledger `amendment_6`, zero renders, `learn/cc_solo_pages.py`); the drive
       page's in-mix version is not needed now. Both were built, audited and sent the same day
       (`clean-crunch-pool-dcc` `amendment_6_outcome`). Their answers came the same day (audited;
       `amendment_6_answers`): catches 8 of 8 right and 5 of 6 checks heard, so the format works on the guitar
       alone; 25 of the 26 pairs near tau were mostly not heard (the one heard is a tremolo below tau); mostly only
       the loudest pairs are. The listener noted that items with several effects are "harder to answer" (33 of 34
       pairs have another effect on in both clips, by design: the context the labels need).
     - *Superseded 2026-10-31 by the [pipeline fix plan](pipeline-fix-plan.md), which folds F20's draft in.* Next: F20's re-plan on this pool, for the user's yes, with two new questions: how near-chance switches are
       read out, and the model beating its constant. Forkupines Sugar Faith ElecGtr8's DI, 129.83 ms ahead of its
       amp track, joins that build from a delayed copy if the alignment check on the copy reads about 0 ms
       (`amendment_4` (c); it runs within that build, since it changes the verdicts). The size-matched top-up
       (about 1,470 more examples, about 6.7k renders, about 3 h) stays unplanned.
   - **Learning every control is not yet shown to help.** T3's F5 gate, D_F5 (every control learned) − D_core5 (today's 25
     controls), reads +0.079 [−0.065, +0.224] on V-real-11 (7 bands): not shown. The user said yes to F20 (2026-10-27);
     (b) read 2026-10-28 (the stock stem stays F20's input). F20 is re-planned on the clean/crunch
     pool; step 4, the D_CC follow-ups and the guitar-only pages' answers (`amendment_6_answers`) are in, and the
     re-plan comes next, for the user's yes.
   - **R1 (post hoc, descriptive, audited):** D_F5 with its 96 unreadable heads written at S still reads +0.062
     [−0.080, +0.204] against D_core5 (4 of 7 bands better; crunch −0.013). The delay, the one time effect still read
     (AUC 0.557, lower bound 0.505), stays on in 29 of 66 directions, and Colour Me Red ElecGtr03 drives the result
     again: +0.846 against D_core5 (+0.949 against D_F5 with time effects at S, the better evidence that delay is the cause). "Delay is the cause" is the best fit, not proven: no render isolates it. The user allowed R1 as
     a measurement only; writing S for unreadable controls is not adopted as the method.
   - **Where the tone is lost** ([tone probe](tone-info-probe.md), zero renders): a linear probe reads 86 of 116
     heads from the target render, 30 from the self-built mix and 20 from the X-LANCE stem. The separator does not
     recover what the mix masks: a 66-head gap. Level does not explain it, and finer features or the DI add nothing.
   - **Data:** the clean/crunch shortage is nearly unchanged (an F20 pool about 96.2–96.3% high gain with "unknown"
     left out, 96.6–96.7% counting it as high gain).

   **Next, in order (2026-10-27; cheapest decisive first).** Replaces the earlier lists below for what comes next.
   - (a0) **A zero-cost check first:** the tone probe's linear probe on the mix plus the stem (minutes, no training,
     no renders), to see whether the stem adds anything to the mix. *Done 2026-10-27 (#309, post hoc, reviewed): the
     mix plus the stem reads 24 of 116 against the mix alone's 30 (the stem 20); it reads 3 heads the mix does not,
     about chance, and the mix is reliably better on 11 heads against 3. So (a)'s model is fed the mix
     ([addition](tone-info-probe.md#addition-mix-plus-stem-f-declared-2026-10-27-post-hoc-before-it-is-computed)).*
   - (a) **A mix-aware input.** Train the every-control model on the mix's features (the stem adds nothing to a
     linear reader, per (a0)) instead of the stem alone. No new training renders: F5's stored mixes, targets and labels. Read first on FS5's
     readability (R0's rule, zero renders; D_F5 reads 20 of 116), then on V-real (about 99 renders per arm, as R1) only
     if it helps. Declared and reviewed before it runs. Training is about F5's size (its 4 runs took 37 min of MPS), so it
     needs the user's yes (training longer than minutes). *Declared 2026-10-27
     ([D_F5mix](trusted-data-t0-design.md#d_f5mix-the-every-control-model-fed-the-mix-roadmap-step-a-declared-2026-10-27-nothing-run),
     ledger amendment 3; revised after its review). D_F5mix against a D_F5-noaug arm
     (the stem unaugmented, so only the input differs); 4 runs, about 30–55 min of MPS; zero renders to the FS5 read,
     then 165 on V-real (no stop rule). It reads the frozen V-real-11 under a drift check instead of T0's lists hash.
     The pilot's prior leans against the mix (D_mix − D_stem +0.022, reliably worse).* *Ran 2026-10-27 after the
     user's yes ([outcome](trusted-data-t0-design.md#d_f5mix-outcome-2026-10-27-165-renders-audited), audited): the
     mix input is not shown better and leans worse, D_F5mix − D_F5-noaug +0.059 [−0.012, +0.130] (crunch +0.091). On
     FS5 it reads 22 of 116 heads (the stem 20), the delay's knobs among the 7 it reads better (the stem 13). On real
     songs it rarely turns the second drive pedal on (4 of 66 directions against 19), the best fit for the lean, not
     proven. The stem stays; (b) is read as planned. The free pooling check: D_F5mix reads 4 of 19 time-effect heads,
     the linear probe 5 from the mix.*
   - (b) **Fine-tune X-LANCE gtr_mss** on our self-built mixes against their known target renders (stored; no new
     renders to train). Allowed under the user's rule ("no new separators; fine-tuning OK"). The user said yes
     (2026-10-27); declared and in review before it runs. Rough cost, to be sized in its declaration: up to about 11 h of MPS for
     the fine-tune (a bound borrowed from the separation plan's Mega-53 head fine-tune, so rough for X-LANCE), about
     4–6 h to re-separate F5's about 4.2k examples and FS5 (T2's separations ran about 6k in 5–8 h), and about 40 min
     to retrain D. Read like (a): FS5 first, then V-real (no stop rule). *Approved by the user 2026-10-27 ("Yes for
     all"); declared the same day
     ([D_F5ft](trusted-data-t0-design.md#d_f5ft-the-every-control-model-fed-the-fine-tuned-stem-roadmap-step-b-declared-2026-10-27-nothing-run),
     ledger amendment 4); (a) has run, which it is read against. Following the [effect-detection
     research](research/effect-detection-2026-10.md): trained on the stored wet target renders as they sit in each
     rebuilt mix (zero renders), mono duplicated; the MPS gate first, with the STFTs, then the loss, then everything
     moved to the CPU as fallbacks. Cross-fitted by band (2 + 2; F5 and FS5 are 4 songs), so every stem D trains on or
     is read on comes from a model that never trained on its song; FS5 and V-real never train or choose. Stops on
     its validation curve (within-song: held-out sections of its own bands; no 0.1 dB gain for 1,000 steps) or at
     the approved 5.5 h per fold. Then about 4,200 re-separations (about 3–5 h), D_F5ft
     (D_F5-noaug with the new stem, 2 runs), and the readout: the stems' SNR, R0 on FS5, the tone probe on the new
     stems, and V-real (99 renders, no stop rule), D_F5ft − D_F5-noaug primary. About 5–16 h in all.* *Ran
     2026-10-27 10:06 to 2026-10-28 00:38 (the gate fix, PR #316, first). The gate chose the CPU: MPS failed the gradient check; MPS with
     the STFTs on the CPU passed it but peaked at 21.3 GB at the training batch, over the 20 GB cap; on the CPU 43 s a
     step (peak 18.9 GB), so each fold ran to its approved 457 steps. Validation (within-song, SNR to the wet target): fold 0 −8.24 dB stock → −0.57 dB, fold 1
     −2.81 → −0.45 dB, both best at step 250 and slightly worse by 457 (−0.86, −1.04), so step 250 is kept.* *Outcome
     ([D_F5ft outcome](trusted-data-t0-design.md#d_f5ft-outcome-2026-10-28-99-renders-audited), audited): primary
     D_F5ft − D_F5-noaug +0.078 [−0.025, +0.181] on V-real, not shown, leans worse. The audit found that the
     fine-tune learned to turn its output down rather than to separate: a silent output scores 0 dB on that SNR, both
     folds' best stayed below it, and the new stems sit about 12 dB under the target guitar (median −33 LUFS), so the
     +5.2 dB over the stock stem on FS5 is not a separation gain; on V-real the new stems are worse than stock in SI-SDR
     in 9 of 11 parts. The tone probe reads 22 heads from them (stock 20, mix 30). One D seed kept its epoch-0 weights; it does
     not explain the result. The fine-tuned stem is not adopted; F20 keeps the stock stem. The route is not judged: one
     short CPU run, under an L1 loss that likely rewards shrinking (best fit, not proven). Fixes, each needing a declaration and the user's yes: a
     scale-invariant loss, a target the mix identifies, MPS under the cap for many more steps.*
   - (c) **Audibility-aware labels for the time effects.** The probe's audibility split: from the stem, the delay's
     AUC rises from 0.62 to 0.73 on its loudest third, while reverb, tremolo and the springs stay weak even at their
     loudest. So a time effect's label should reflect how audible it is, not only its switch. Measuring audibility
     takes renders (below); a retrain to read it (about F5's size, so it needs the user's yes too). *Research delivered 2026-10-27
     ([effect detection](research/effect-detection-2026-10.md), #311; not a plan): masking by the backing, not faint
     labels, is the main loss. Audibility is measured in the mix, A_e = |log(J(r_off, m) / J(r_on, m))| against the
     stored mix, so it is not zero renders: about 1,000 for an FS5 test (up to 200 "on" examples per effect rendered
     off), thousands for all of F5. Its ranking puts (b) first; a free check rides on (a): D_F5mix's time-effect row
     against the probe's mix row (5 of 19). How the label is used needs the user's ruling (open decisions below).*
     *The measurement, approved by the user 2026-10-27 ("Yes for all") and declared the same day
     ([design](trusted-data-t0-design.md#audibility-in-the-mix-the-measurement-roadmap-step-c-declared-2026-10-27-nothing-run),
     ledger amendment 5). A_e for up to 200 "on" FS5 examples per effect (824 effect-off renders on 483
     examples, plus 36 repeats and 36 priming: 896), the tone probe's switches re-read by A_e thirds and against τ,
     and a blind listening page to check τ (0.005 log) by ear. Descriptive: the relabel and its retrain wait for the
     user's three rulings and get their own declaration.* *Ran 2026-10-27 09:44–09:57 (896 renders); the audit found
     A_e contaminated by the plugin, not the code: Morgan's tremolo, tape delay and rack reverb run on across renders
     in one process, so r_off and the stored r_on sat at different points of their cycles (2 of 36 repeats matched; the
     floor's median 0.0017 and 90th percentile 0.0156 straddle τ). The page is not sent. Re-declared before any re-render
     ([fix](trusted-data-t0-design.md#the-first-run-and-the-fresh-process-fix-2026-10-27-after-the-first-run-before-any-re-render),
     ledger `amendment_5_fix`): every render in its own new process (a priming render with the example's own
     setting, then the one kept), r_on' and m' fresh, an exact repeat per group, all pairs redone: 2,686 renders
     (about 40–70 min with the process starts). The repeat checks r_on' only; that r_off's other running
     effects sit at the same phase assumes switching one effect off resets none of the others (it holds by render
     count; untested). **A caution for earlier results:** V-real renders several presets in one process
     per group, so a comparison with a time effect on in both answers carries phase noise from render order (noise,
     not bias); flagged, not fixed.* *Fresh run 2026-10-27 10:38–11:24 (2,686 renders, all 36 repeats bit-exact;
     [outcome](trusted-data-t0-design.md#audibility-outcome-2026-10-27-fresh-run-2686-renders-audited), audited):
     23–59% of "on" effects sit below τ in the mix (delay 0.40, reverb 0.42, tremolo 0.23, PR12 spring 0.33, SW50R
     spring 0.59). The delay reads better from the mix as A_e rises (0.57 → 0.71), but so does the target without
     backing, so effect size and masking are mixed; tremolo reads weakly at every level. A_e measures how much the
     effect moves the judge's render-to-mix score, not audibility as such (it is negative for 25–49% of pairs, a judge
     property). The doubler also runs on across renders. The ear page went to the user; the relabel waits for their
     answers and the three rulings.* *The user found that page's pairs too dense to hear (2026-10-27): FS5's mixes sit
     in 4 dense rock songs, the guitar usually 5–19 dB under the rest. A second page, zero renders (PR #319,
     reviewed): the same selection over the 53 measured pairs whose guitar is exposed (at most 6 dB under the rest,
     no vocals, at most 2 other guitars), its own key; sent the same day; a third page on clean/crunch mixes (pool
     step 4) sent 2026-10-30. Its answers (2026-10-30, ledger `amendment_3_answers`): no pair heard as clearly
     different, not even the four loudest; the page's own checks did not come out, so tau is not placed by ear
     (nothing suggests switches below it are audible, but the anchors were not heard either, so the sitting cannot
     show this); the relabel's reader is still unwritten. A fourth page, drive pedals on and off in the same
     clean/crunch mixes (ledger `clean-crunch-pool-dcc` `amendment_5`, declared 2026-10-30), plays each pair in a
     player that switches between A and B at once and re-checks step 4's loudest reverb and spring pairs there, each
     beside a catch under its title (sent 2026-10-30, 17 items; `amendment_5_outcome`; its in-mix answers are not being asked for, the guitar-only
     answers below replace them). Heard
     means "They differ". A check heard there is consistent with step 4's
     format hiding differences, not proof of it: only the checks carry those titles, it is the listener's second
     hearing of those clips, and the listener may know which items are checks. The user then asked for the guitar
     alone (2026-10-30): guitar-only versions of the drive page and of step 4's page (`amendment_6`, zero renders,
     the same items; step 4's runaway item 4 replaced) show whether each switch is audible on the guitar alone,
     each clip levelled apart: roughly an upper bound on its audibility in a song, except where the switch changes
     the guitar's balance in the mix (levelling removes it). Read against step 4's in-mix answers, masking is
     confounded with the old sequential player and a repeat hearing; only the drive page's in-mix answers (same
     player, not asked for now) would isolate it. They cannot show whether a switch is heard in a song, nor tau (the
     items were picked by in-mix A_e). Both were built, audited and sent 2026-10-30 (`clean-crunch-pool-dcc` `amendment_6_outcome`: 17 and
     25 items, the guitar alone in every clip). Their answers (2026-10-30, audited; `amendment_6_answers`): catches
     8 of 8 "same", 5 of the 6 distinct checks and anchors heard (not 802682's sw50r spring); 25 of the 26 pairs near
     tau not heard (21 same, 4 maybe; the one heard is 802350's tremolo, A_e 0.0039); all 8 spring pairs same. The
     heard pairs are the top solo-J pairs in each part, though no single solo-J cut works across effects and the edge
     over A_e rests on one item (802350). So on the guitar alone the format works; most heard pairs sit well above
     tau and one below it was heard, so, as declared, this does not place tau. F20's re-plan declares how, if at
     all, these answers are used for the audibility weight. Caveats: part 1
     was answered fast (8 of 16 answers under one 10-s loop after the previous one), repeats across the parts, small
     n. Answers on the dense page still count: an
     effect not heard there is masked there. The user's direction the same day (below) points the rulings toward an audibility weight; its exact
     form is declared and reviewed before the relabel.*
   - **Clean/crunch-led pool** ([plan](clean-crunch-pool-plan.md), approved 2026-10-28): steps 0–3 done (D_F5bk and
     D_CC read, both undecided; D_CC leans worse). Step 4's answers came 2026-10-30 (tau not placed by ear). The two
     cheap D_CC follow-ups were read 2026-10-30 (`amendment_4_outcome`: the loss is mostly the pooled answer's pedals,
     and both seeds' answers turn the drives off, not rendered; D_CC trails its own constant). The drive-pedal page
     (`amendment_5`, sent 2026-10-30: 96 renders, 17 items with an instant A/B switch; its checks take the place of
     the replay of three items, which the author dropped; step 4's runaway item 4 is not re-used) is followed, at the
     user's request, by guitar-only versions of it and of step 4's page (`amendment_6`, zero renders; sent
     2026-10-30; answered the same day, `amendment_6_answers`: the format works on the guitar alone, and pairs near
     tau are mostly not heard). Next: F20's re-plan, for the user's yes, with the ElecGtr8 shift run within its build.
   - (d) **F20:** re-planned on the clean/crunch pool. Step 4, the D_CC follow-ups and the guitar-only pages' answers (`amendment_6_answers`) are in; the re-plan comes next, for the user's yes, and declares how, if at all, those answers are used for (c)'s audibility weight. Before that: the user said yes (2026-10-27); its plan is declared after (b) reads (read 2026-10-28: the stock stem stays its input). Its value now rests on (a)/(b) and on the new data. Its declared
     fixes: redraw near-silent draws (up to 5 tries; about 16% more target renders at F5's rate); an audio runaway
     check on targets (a self-oscillating delay, about 2% of both pools), refused and redrawn (to be declared and
     reviewed in the re-plan); keep each
     core/full pair on one separation device; the switch readout and prior (since 2026-10-27 the plain readout is
     the method; an at-S read only beside it; D_CC's follow-ups add how near-chance switches are read out, since a
     0.5 readout turned D_CC's bare-majority drives off); the model beating its own constant (D_CC trails its own,
     D_F5 about equals its own); the ElecGtr8 shift and its alignment check (`amendment_4` (c)), run within the build; "unknown" DIs at most 25% of draws. Its plan must also settle
     V-real-11 against V-real-12 (keeping V-real-11 needs a code change) and rebuild the DI inventory and pool. About
     51k renders (T3's plan: about 58k renders and 32–42 h wall in all, most of it F20's).
   - Not blocked by these: every-control stage 1 (can run, not run), the real-mix test and T4 (below).

   **Open decisions for the user (2026-10-27):**
   - *Settled 2026-10-27 ("Yes for all"): F20 runs, and the training time for (a), (b) and (c)'s measurement and
     retrain is approved, each once declared and reviewed.*
   - Before T4: the decision test's data and ship rule; whether arm A gets every-control coverage; whether the
     stored C′ and step 3's D keep running under a recorded exception to the trusted rule.
   - Reopening arm B, at the decision test.
   - For (c), how an audibility measure may change the labels ([research](research/effect-detection-2026-10.md#measure-audibility-in-the-mix-not-by-the-knob)):
     counting an effect inaudible on its own as off (extends the switched-off rule, touches every-control amendment 1); weight 0
     for an effect masked in the mix (changes "the switch itself is always scored"); masking idle knobs, measured
     per knob (Tone King's tremolo speed was audible at depth 0). *The user's direction (2026-10-27, in chat):
     different presets that sound similar are "definitely possible and acceptable"; an effect that can almost not be
     heard is "almost not important"; the user would also consider adjusting the effects from the song research after the preset is generated.
     Read as: an effect's label counts in proportion to how audible it is in the mix, down to near zero when masked
     (a sliding weight unless the user prefers a hard cut; τ from the ear pages). The relabel's declaration states
     the exact form and is reviewed before it runs.*
   - Follow-ups from that direction, not yet planned: training scored by sound rather than knob by knob (V-real
     already scores by sound, so a sound-alike preset already counts as right there); and a hybrid in which the
     model sets amp, drive and EQ and the time effects come from `generate`'s song research (product session).

   **Trusted data only (the user, 2026-10-22): "use only what we can trust, no dirty tracks".**
   Measurements, training, tests and listening pages use a reviewed trusted set. Dirty tracks are
   excluded, not flagged. This supersedes the 2026-10-17 bleed decision (high-bleed parts flagged,
   a no-high-bleed row beside all parts). **The user's listening verdicts define the trusted
   set,** on the data-review pages (amp and mic tracks, suspected doubles, DIs). Rule-based
   measures (the audit's checks, #273's original-take level and bleed flags) only name candidates
   for that review ([ML plan](research/ml-plan-2026-10.md) §5). *Amended 2026-10-23 by the
   trusted-data plan (below): a measured verification fail excludes, and the ear decides the rest.*
   - **The data-quality audit** ([record](data-quality-audit.md),
     zero renders; its proposed level-matched retrain was not run, the trusted-data plan
     superseded it; in `learn/verify_tracks.py`, A5 ports its `crop_match2.py` and A6 builds on
     the bleed audit it joined):
     - separated stems carry a median 45% of their power above the matched render (other music
       plus mismatch); within each band, the most contaminated third scores worse on step 3's
       sound gate, +0.103 [+0.055, +0.156];
     - doubles of the same riff stay in the training backings, and the stored leak check misses
       them;
     - the DIs are clean, and the labels are exact renders (*2026-10-23:* "clean" meant no hum or
       clipping; sitting 1 later heard 17 of 35 crop DIs as processed, and Eggy's three DIs are out);
     - bleed sits in the live-room amp and mic tracks (Telefunken). Trial 47 (Sculptor's Request
       GTR 1) is bleed, not a wrong DI.
   - **The cleaning plan** ([PR #273](https://github.com/YoavBZ/neuraldsp-preset-generator/pull/273)):
     its recommendation is to rebuild the affected training examples without the offending backing
     tracks, rather than drop them. Dropping would cost a quarter to a half of D's margin over the
     constant from size alone. The plan was reviewed (go, with changes) and the user chose "the
     best approach"; its implementation was in progress (2026-10-22; superseded below). Order: zero-render checks; a paired R_in
     rebuild read (no training); then the pool rebuild and 2 training seeds (about 2.5 GPU h). The
     rebuild is about 4k renders and 3.6k separations, and at most about 13.8k renders and 13.4k
     separations if the live-room tracks count.
     *Since 2026-10-23:* step 0 ran, the guitar doubles were rebuilt (no training) and a
     bleed-injection test ran ([result](data-cleaning-options.md#the-bleed-injection-test-result-2026-10-23-audited));
     the user keeps only clean examples for now ([decision](data-cleaning-options.md#the-users-decision-2026-10-23)).
     Under the trusted-data plan, step 2 becomes T2's SES arm.
   - **The trusted-data plan** ([plan](trusted-data-strategy-plan.md), PR #280;
     [T0–T2 design](trusted-data-t0-design.md)), approved by the user on 2026-10-23 with its recorded
     decisions. Training and development use self-built mixes from verified DIs; V-real (stage F's
     parts that pass the checks and the ear) is the final development test; the user's ear on real
     songs is the last check. It amends three approved plans (set by the ML session; the user may
     overrule): the cleaning plan's step 2 becomes T2's SES arm, every-control stage 2D becomes T3
     (read on K and V-real; *K is empty since 2026-10-25, so T3's K read is open*, [design](trusted-data-t0-design.md#t1-waived-and-the-realism-check-moved-into-t2-2026-10-25)), and the real-mix test runs
     on V-real's parts.
     - **T0 ran on 2026-10-23** (before the ear; `verify_tracks`: calibration OK, then targets, DIs, the stem scan,
       lists and the re-read; renders only for calibration's 8 cab-off negatives, plus 6 priming).
       After two ear-queue fixes (silent windows, DI-only repeats; PR #284) and the review's rules
       (PR #286, run 2026-10-24 on this machine), the lists read before the ear: targets 0 verified, 18 pending the
       ear, 41 excluded; DIs 0 verified, 50 pending the ear, 9 excluded (every DI is heard first);
       V-real 11 parts pending the ear; no stems usable until their spot-check was heard. The user
       had the listening pages `trusted-data-ear` parts 1–4 (`learn/build_ear_page.py`, rebuilt
       2026-10-24 to the live queue, nothing to skip; the earlier parts 1–6 are kept in `old-v1/`):
       202 cards, about 55 min. Part 3 holds the 6 unheard measure DIs of V-real and knob ceiling 2's
       parts; part 4 is the stem spot-check (19 backing-track clips). K and T2 waited for the ear. The plan's review-label fix ("2 amp mics summed" where
       only the main mic plays) is in `learn/build_data_review.py`, but the built data-review pages
       are not rebuilt.
     - **The ear on T0's queue: done** ([outcome](trusted-data-t0-design.md#t0-outcome-2026-10-25)).
       The user heard all 202 cards on parts 1–4 (exports 2026-10-24 and 25), read in one `lists`
       run with the sitting-1 export; nothing was superseded, cleared or skipped. Answers: targets
       35 clean amp, 1 bleed; pairs 34 amp, 1 processed; DI windows 99 clean, 13 processed; stems
       14 clean, 5 with a guitar. The lists now read:
       - targets 17 verified, 42 excluded; DIs 46 verified, 13 excluded;
         *window re-check 2026-10-25:* 3 excluded targets failed A5/A6 only because their crop window caught
         the DI silent; on 3–5 other windows each they have no measured fail (5/5, 3/3, 5/5); 13 stay out (DI
         hum, an A1 fail on 1 of 5 windows, real faults). The 3 join only after the user's ear (re-check page
         ready) and after T2's chain ends (*it ended 2026-10-26; they await the ear*)
         ([rule](trusted-data-t0-design.md#t0-window-re-check-2026-10-25)). *Heard 2026-10-26: all 3
         passed, and 2 are verified (It Was My Fault ElecGtr1, Nosso Mundo ElecGtr03). Signs ElecGtr6
         stays pending until its DI is heard as a DI (part 8, 3 cards), so targets are 19 verified,
         1 pending, 39 excluded. Each uses only its re-check windows, and none joins V-real, knob
         ceiling 2 or the level prior
         ([outcome](trusted-data-t0-design.md#parts-5-and-6-heard-2026-10-26)).* *Part 8 heard 2026-10-26:
         its DI is clean on all 3 windows, so Signs ElecGtr6 is verified on all 5 windows; targets 20
         verified, 0 pending, 39 excluded. T3's frozen V-real-11 is unchanged; a future plan would see
         V-real-12 ([outcome](trusted-data-t0-design.md#parts-7a-7b-8-and-9-heard-2026-10-26)).*
       - V-real 10 parts in 7 bands (3 clean parts in 2 bands, 7 crunch; 3 of the 10 from one song,
         Wickerman); knob ceiling 2's 7 parts in 7 bands verified;
       - K 17 DIs in 3 bands, but T1's K uses Adam Buckley and Dark Ride only (Cnoc An Tursa not
         admitted; Kimock and Swatkins now excluded by the ear: all 4 of their DIs were heard
         processed, Hikikomori, New One, Honey, Lost & Alive);
       - training 27 DIs in 8 bands, 181 usable sections, of which only 1 is clean-class and 1 crunch
         (61% high gain, the rest unclassed);
       - stems 166 usable in 14 sessions (Split Brow's click track barred, PR #289); the 5 sessions heard with a guitar are held (Eggy Farthest
         Step and Fragments, Hikikomori, Honey, Lost & Alive).

       Let's Dance ElecGtr4 (the user, 2026-10-24): the leak is in the DI (quiet high notes), and the
       target was too distorted to judge. The target is excluded and the DI counts as not clean
       (`verified.json` still shows it heard clean in sitting 1; nothing downstream uses it). That
       leak sat at about −33 dB, so A6's −30 dB line is no guarantee. **The main finding:** the
       training pool holds almost no clean or crunch playing (1 + 1 of 181 sections), against the
       clean/crunch scope. Clean-style DIs must come from new sources (EGDB, downloaded, needs its
       DI checks and a borrowed backing; GOAT, access requested; Jen Hartswick & Nick Cassarino is
       reserved for test), an open user decision before T3 (*decided 2026-10-26: Strobe and MekaPhil*). The audit's caveats are in the
       [outcome](trusted-data-t0-design.md#t0-outcome-2026-10-25): Eggy Bloomlight's 14 stems are
       unused (no Eggy DI is verified), Renesans' stems must be settled before T2 uses its
       backings, one thin DI, leaked drums on some amp tracks, and the level prior.
     - **The review before the ear (2026-10-23;
       [record](research/program-review-2026-10-23.md)):** two multi-agent reviews (11 reviewers,
       each finding checked by a skeptic) of the trusted-data change and of the whole program.
       Fixed in code, nothing rendered: the ear's import (`lists` forgot earlier exports and ran
       without the sitting-1 export, so importing part by part would have dropped answers and
       re-admitted DIs heard processed); 'unsure' on a sampled DI counted as clean; a clean answer
       cleared a flagged window it only half covered; a DI with unheard flagged windows read
       verified; and in T1/T2, other guitars 3 dB low against the stems, same-part doubles back in
       SYN with their own tone, a refused example blocking all training, stale renders reused after
       a re-plan, and a T2 reading printed from incomplete renders. The next `lists` run recomputes
       the counts above under the fixed rules (more DIs may read pending). The rest is in the open
       decisions below.
     - **Fresh test bands, reserved** in the [ledger](dev-test-ledger.json): Jen Hartswick & Nick
       Cassarino (Telefunken, 4 songs; read once at T4, in V-real) and Blue Manic "Acomatay"
       (Cambridge, 5 DI + amp pairs; outside this plan's V-real and T4). EGDB's 240 DI clips are
       downloaded; they train only once they pass the DI checks (and, for T3, only with a borrowed
       backing the user accepts). GOAT's access was requested by the user.
     - **Metal and hard-rock training sessions (2026-10-26, user):** 13 Cambridge-MT sessions in 7 bands
       (Arcadian Alone, Daimon B ×2, Dark Illusion ×2, Inhumanity Vortex, Peppermark ×3, Serapis ×2, DGX ×2)
       are training sessions (ledger `cambridge-new-training-bands-2026-10-26`). The user: high gain may
       train, as long as too-heavy parts stay out; tests stay clean to crunch. Same intake as below: role
       first, then T0's checks and the ear (a tone card per amp track: clean, crunch, high gain or too heavy).
       V.M.GY was not downloaded (set-3 held out). T0's checks (2026-10-26; guitar tracks only, so no A6):
       D3 passes all 89 electric DIs, D2 passes 78. Most D2 fails are hum not confirmed on the rests, a
       possible miscalibration on dense low riffs (left unchanged). A5 looks miscalibrated for high gain.
       The ear pages (parts 7a and 7b, 44 cards each: 1 window per DI, 78 DI and 10 tone cards) are pending;
       `lists` reads them (`metal_verdicts`). *Heard 2026-10-26: **50 of 89 DIs admitted, every one high gain**
       (Peppermark 34, DGX 11 by the DI-only rule, Arcadian Alone 3, Dark Illusion 2). 5 sessions were heard too
       heavy and dropped whole: Daimon B "Broken Again", Dark Illusion "Evil Bones", Inhumanity Vortex, and Serapis
       ×2 (30 DIs). No tone was heard clean or crunch. Part 9 (Strobe/MekaPhil) was heard the same day: all 13 DIs
       clean and admitted, but every style question was left blank (style can't be judged from a DI). Since
       2026-10-27 (PR #306) their 11 DI-only DIs with no song tone are "unknown", out of the high-gain cap, and
       Timeless Part 2's 2 take its amp track's clean tone (applied by the `lists` re-run, 2026-10-27 01:17): the
       admitted intake DIs are 51 high gain, 11 unknown and 2 clean. The clean/crunch shortage is nearly unchanged:
       an F20 pool's sections would be about 96.2–96.3% high gain with "unknown" left out, or 96.6–96.7% counting
       "unknown" as high gain (the worst case), against 96% of today's 181; the non-high-gain sections go from 7 to
       about 15–20 ([outcome](trusted-data-t0-design.md#parts-7a-7b-8-and-9-heard-2026-10-26)).*
     - **New training bands (2026-10-25, user):** five Cambridge-MT sessions (Ember Rev, Empty
       Signifier, Goran Levi, Mòpia, Sören; 9 electric DIs, 7 with an amp or mic track) are training
       bands (ledger `cambridge-new-training-bands-2026-10-25`), aimed at the pool's missing clean and
       crunch playing. They train only after T0's checks and the ear (the inventory marks them pending
       until a verified list admits them). T0's checks (2026-10-25): D2 passes 4 of 9 (Empty Signifier
       ElecGtr2DI, Goran Levi, Mòpia ×2). Ember Rev is out for clipping, Empty Signifier ElecGtr1DI for
       hum, and Sören for gating or edits. Goran Levi's amp track is a processed copy, not a miked amp.
       Mòpia is a scope worry: D4 flags both DIs and the amp tracks read heavily driven. The user's ear
       page (part6, 16 cards) is pending. *Heard 2026-10-26: **1 new training DI from 5 bands.** Empty
       Signifier 20_ElecGtr2DI was heard clean and is admitted. Its amp track is high gain, so it
       does not ease the clean/crunch shortage. Mòpia's two DIs and Goran Levi's were heard processed
       ([outcome](trusted-data-t0-design.md#parts-5-and-6-heard-2026-10-26)).*

   **Where it stood (2026-10-19; the current state is "Where it stands, 2026-10-29" above).** Not ready to ship. Fresh full mixes (stage F, 21 parts in 12
   bands) are the yardstick; figures are against S, band-weighted, with 90% intervals.
   - **Arm A** (a search through a DI rebuilt from the separated guitar, scored against that stem)
     ([results](arm-a-mega53-results.md), amendments 2 and 3):

     | Arm | What it uses | Against S |
     |---|---|---|
     | H | the htdemucs stem, rebuilt DI | −0.028 [−0.064, +0.008] |
     | M | the Mega-53 stem, rebuilt DI | −0.046 [−0.091, −0.000] |
     | XO | the true DI, the htdemucs stem as target | +0.012 [−0.088, +0.112] |
     | YT | perfect separation: the amp track as target and rebuild source | −0.094 [−0.131, −0.057] |
     | ZT | the true DI and the true target | −0.174 [−0.232, −0.115] |

     - **The lever is separation first, then the rebuild.** Perfect separation gains −0.066
       [−0.090, −0.042] over H (11 of 12 bands). A perfect DI gains nothing while the target is a
       stem (XO), and a further −0.080 [−0.113, −0.047] once the target is clean (ZT − YT).
     - **The halfway shrink hurts when the inputs are good** (ZT's unshrunk best −0.047 [−0.070,
       −0.025] against its shrunk output; YT a tie). On today's stems it still helps, and the
       best shrink does not measurably depend on stem SNR ([zero-render check (a)](shrink-snr-judge-v3-results.md)).
   - **The direct model** (song to settings; [results](direct-existing-results.md)). Its first,
     untuned version ties S: **+0.033 [−0.053, +0.119]**. This is **not a verdict on the
     approach** (the user, 2026-10-19). It reads two inputs, the separated stem and the mix. It
     was trained on perfect stems and tested on htdemucs stems, a likely mismatch. It stays an
     active route.
   - **Listening** ([results](record-match-listening-results.md)): on 5 guitar-exposed parts the
     ear broadly agrees with the judge (Spearman mean 0.8, positive in 5 of 5), and the ceiling is
     heard as closest (4 of 5). Judge v3 agrees a little less on the same clips (0.64; [check
     (b)](shrink-snr-judge-v3-results.md)), so the default judge stays.
   - **Separation.** The user heard Mega-53 as much better on the separation samples. It also
     separates the electric guitar from a (likely) acoustic one. Both separators sometimes include
     another electric guitar ([stereo and mix check](stereo-and-mix-check-results.md)).
     **Mega-53 is now the ML default separator** (htdemucs stays selectable; the direct model's
     full build uses X-LANCE gtr_mss since 2026-10-21), and unlicensed
     open-source weights are allowed (the user, 2026-10-19; widened on 2026-10-20 to anything
     unlicensed, non-commercial or gated, see ML plan §5).
   - **Our mixes are not real mixes** ([stereo and mix check](stereo-and-mix-check-results.md)).
     The development "full mixes" are the raw tracks summed at unity, and no session has a mix or
     master. [Released mixes](mix-previews-results.md) of 10 songs and a remix of Signs (same
     takes) measure that gap: Mega-53 on the real mix loses 0.62 dB SNR against the raw track on 17
     stage F parts, half of it from per-track lag (polarity flips cost nothing in a gain-fitted
     SNR). In SNR, mastering adds little. Scores on real songs need to be lag-invariant. Stereo: with the target centred, as in
     all our sums, the mono fold loses nothing.

   **The direction: two active routes, arm A and the direct model, with better separation as the
   shared lever.** *(2026-10-23 review: no step works on separation now; it is mapped and parked at a
   +0.30 dB fine-tune cap, and the order runs trusted training data first. The items parked "until
   after the earlier steps 1–2" wait on steps that are parked too, and B2's songs went to training.)*
   *(2026-10-27: the tone probe puts separation back in front. The stem recovers none of the tone the mix hides, so
   a mix-aware input and an X-LANCE fine-tune are next, (a) and (b) above.)*
   The rebuild work (the [dose probe](dose-probe-results.md)'s full-band head) waits
   until the target is clean enough for a better rebuild to pay (XO, ZT − YT).

   **The [trusted-data plan](trusted-data-strategy-plan.md)'s order (2026-10-23), with what ran.** What comes next
   is in "Next, in order (2026-10-27)" above; items still open here are dated.
   - (a) **The user's ear on T0's queue: done 2026-10-25.** All 202 cards on `trusted-data-ear`
     parts 1–4 were heard and read in one `lists` run with the sitting-1 export (the lists are
     above, the steps in the [design](trusted-data-t0-design.md#t0-outcome-2026-10-25)).
   - (b) **T1, stem quality** (no training): build K from R_in's stored truth renders and separate
     it; read K − V_sep stem SNR, paired on the same examples and draws, with V-real's stem SNR
     beside it. The design estimates about 0.8–1.5k renders for the other guitars and about 370
     separations; the plan budgets about 3.5–5.5k renders and 1.7k separations for T0–T1. The read
     is descriptive: K cleaner than V_sep is the cleaning gain the plan expects, not a realism
     verdict, and no realism lever is coded or approved, so T1 changes nothing in T2 by itself.
     *Ran 2026-10-25 on 812 examples from Adam Buckley and Dark Ride; audited
     ([T1 audited](trusted-data-t0-design.md#t1-audited-2026-10-25)).* It read +1.63 dB on a 1-df band interval
     (section-clustered [−0.31, +3.56]); 63 examples whose other guitars could not be rendered carried about +1.2 dB,
     and near-silent renders were lifted by up to +43 dB. **No cleaning gain is established and no realism lever
     follows.** Fixed in code: a section where a session guitar plays but cannot be rendered is left out of every
     arm, a near-silent render (below −50 LUFS) refuses its example, and under 3 bands the section-clustered interval
     is primary. That rule left out all 812 T1 examples and cut T2's candidates to 3,955 in 3 bands. **The user's
     decision (2026-10-25):** an active guitar that cannot be rendered is the session's own amp track(s) after an
     automatic bleed check (under −30 dB, A6's line; no listening), else the example is left out
     ([rule 1](trusted-data-t0-design.md#rule-1-after-the-users-decision-2026-10-25): bleed read once per session from
     non-guitar tracks only; a source the estimator cannot be trusted on fails the track; more active guitars than
     the cap of 4 leave the example out). After the independent review's fixes every amp track has at least one source
     the estimator cannot resolve at −30 dB (sparse vocals, synths, effects, toms), so none is used. Dry run: T1 keeps
     0 of 812; T2 keeps 5,154 candidates in 4 bands outside early stopping (Rebuild The Evil and The Long Wait drop
     out; 109 Ale Lak candidates over the cap), so the 5k pilot is still reachable, narrowly.
     *Superseded 2026-10-25 (next sentence):* **T1 must be re-planned and re-run before T2,** because K's mixes
     change: `amp-bleed` (about 20 min CPU per session) and `plan`, zero renders; as it stands the plan holds no
     example; the user was to decide whether T1 is waived or the check changes. **T1 waived, not passed
     (2026-10-25):** this follows from the user's answer to whether T2 should run on 4 bands without amp tracks, "I
     prefer reliable data and additional/longer runs than data that can't be fully trusted". K is empty under the
     reviewed rules, and T1 gates nothing; its question moves into T2 (below; [design](trusted-data-t0-design.md#t1-waived-and-the-realism-check-moved-into-t2-2026-10-25)). With K empty, T2 reads no E on
     K (`e-on-k` has nothing to read; the T2 chain treats its failure as non-fatal), and K and the T3/T4 sound gate stay
     open until a better leakage measure, or another route, brings K back.
   - (c) **T2, the 5k pilot. *Ran 2026-10-25 to 26: a tie, SYN picked (outcome at the end of this item)*.** Started 2026-10-25 at 17:54 under PR #290's rules: 5,154 candidates in 4 bands
     (Ale Lak, Death Of A Romantic, Hollow Ground, Storm Of Particles), a pilot of 5,000, early stopping 308 in 4
     sections, no amp tracks; 5,308 target renders, 10,099 other-guitar renders plus priming, 5,308 separations.
     SES (the stored stems; the cleaning plan's step 2) against SYN
     (self-built backings of the same examples, labels and draws), 2 seeds each; primary SYN − SES
     on V-real. A tie picks the self-built set (the user, 2026-10-23). If SES reads better beyond a
     tie, the realism levers still on (mix EQ and reverb) are tried at 5k before T3 (they are not
     coded yet). Controlled bleed and studio amp tracks for the other guitars are off under the
     recorded decisions (set by the ML session). SYN-E is dropped from T2 until a clean-class DI
     source (EGDB or GOAT) passes the DI checks (user, 2026-10-24). *Power (restated 2026-10-23):* V-real has 7 bands, not the plan's 10, so a paired
     arm contrast reads about ±0.036 log d (90%), before seed noise; a tie cannot rule out a
     realism loss about the size of D's whole margin over S (−0.034). The report prints per-class,
     F-song and without-MUSDB18 rows (V-real is 2 clean bands and 5 crunch), and reads
     'incomplete' until every direction is judged and no answer was refused. *Added 2026-10-24
     (user):* the song-blind per-class constant (the step 3 gate's constant on T2's training labels)
     is one more V-real arm, about 60 renders at V-real's 10 parts (about 210 for SES, SYN and the constant with 30
     shared priming renders), read beside the primary as SES − constant, SYN −
     constant and constant − S: does a model read the song, or only the constant's pull?
     **The realism check, inside T2** (the ML session's proposal, approved after review, 2026-10-25;
     [design](trusted-data-t0-design.md#t1-waived-and-the-realism-check-moved-into-t2-2026-10-25)): the primary SYN − SES on V-real is the decisive realism test. Beside it, a T2-side stem read (zero renders,
     descriptive; *built 2026-10-25, [as built](trusted-data-t0-design.md#t2s-additions-as-built-2026-10-25)*): SYN's stems against SES's on T2's examples, with T2's target
     render as the truth for both. At best a ceiling check, since above 0 cannot tell cleaner from unrealistically easy.
     `report` now labels T1's old 812-example read superseded. *Known gap:* sections with an active guitar
     that has no usable DI or amp track are left out, so dense multi-guitar arrangements are under-represented. SYN
     short of SES on V-real is a realism signal, not a gap signal (both arms train on the same examples). The gap is
     read by two zero-cost diagnostics declared now: V-real by the number of playing guitars, for SES − S and SYN − S
     (split declared at 5 or more playing: 6 V-real parts in 3 bands dense, 4 in 4 sparse); and active-guitar counts of
     kept against left-out examples (*read 2026-10-25:* left out mean 3.82 playing guitars against 2.90 kept, at least
     4 in 81% against 18%; 2,308 of the 3,260 left out are Rebuild The Evil, all at 4; V-real is denser still, 9 of 10
     parts at 4 or more). A third, *approved by the user 2026-10-25* ("Approved if you suggest following this
     approach"), is **SES-ALL**: SES's recipe, seeds and early-stopping set on a 5k draw (seed 20261104, stratified by
     band) from the 8,414 T2 candidates outside early stopping, the left-out sections included, read as SES-ALL − SES
     on V-real. N is kept equal to SES's (the build's interpretation, confirmed by the ML session), so it reads what
     the left-out sections are worth at equal size; their share is about 39% either way (1,946 of the 5,000). The
     draw spans 6 bands; its left-out examples come from 5. Extra cost: 2 runs of about 1.5 h, about 60 V-real renders plus 30 priming, no separations. It runs after
     T2's chain ([follow-up chain](trusted-data-t2-followup.sh)), adding to T2's records without re-making them. Caveat:
     the left-out data are mostly one band, so SES-ALL − SES also carries two more bands, not density alone
     ([as built](trusted-data-t0-design.md#t2s-additions-as-built-2026-10-25)). The read, the diagnostics and the `report` fix are built (2026-10-25) and independently
     reviewed before T2's results are seen. A leakage measure that resolves sparse sources (which would recover them, T1, Rebuild The Evil and The
     Long Wait) is built after T2 if these show the gap matters, or when T3 or T4 needs K. *After T2 (2026-10-26): not shown to matter: (a) is null and SES-ALL is descriptive; the sparse-source leakage measure waits until T3/T4 need K.* Before Renesans enters any
     stage: `session_guitar_parts` skips GTR 2 Amp as GTR 1's `own` (a latent bug the review of #290 found; it does
     not touch T2's four bands).
     **T2's outcome (2026-10-26, audited: every row recomputed from the V-real groups;
     [outcome](trusted-data-t0-design.md#t2-outcome-2026-10-26)).** Log ratios, lower is better, 7 bands:
     - **Primary SYN − SES on V-real +0.019 [−0.001, +0.040]: a tie** (|point| < 0.03, and the interval holds 0), so
       SYN is picked by recorded decision 4. Not "equal": SYN leans worse (5 of 7 bands lean to SES; every
       leave-one-band-out mean +0.013 to +0.026), and the upper bound exceeds D's margin over S.
     - SES − constant −0.031 [−0.068, +0.005], SYN − constant −0.012 [−0.045, +0.021]; against S, SES +0.012, SYN
       +0.031, constant +0.043. Neither arm beats S or clearly beats the constant. Each arm's pull was fitted on the shared
       278-example early-stopping set, built in its own arm's mix (median b SES 0.79, SYN 0.44), so the contrast includes it; seed noise is not in the interval.
     - Data and training clean: 334 near-silent refusals applied to every arm; all 4 runs on the same 4,696 training and
       278 early-stopping examples (5,000 + 308 drawn; 304 + 30 near-silent refused = 334); training healthy (best epochs SES 21 of 26 and 23 of 28, SYN 20 of 25 and 29 of 34).
     - SES-ALL − SES −0.026 [−0.070, +0.018], descriptive and not a density test: it adds 2 bands SES never saw,
       shares only 2,966 examples with SES, has its own pull and rests on one band (without Zeno −0.009). It reads
       "a broader draw leans better". SES-ALL − S −0.014, the first T2 arm to lean past S; its interval holds 0.
     - Diagnostic (a): dense against sparse shows nothing and is confounded with band. The stem read: SYN's stems
       are not cleaner than SES's (−0.80 dB [−1.12, −0.47] section-clustered; band-clustered holds 0), so SYN is
       not shown to be unrealistically easy (a ceiling check only).
     - **Decision 5: T3 goes ahead (user, 2026-10-26).** Pending inputs at the time: the window re-check's 3
       recovered parts and the new bands' 4 DIs ([PR #294](https://github.com/YoavBZ/neuraldsp-preset-generator/pull/294), ear page `part6-new-bands`) await the user's ear (PR #293, PR #294); the clean/crunch shortage
       stays the clearest gap. *Heard 2026-10-26: 2 targets recovered, Signs ElecGtr6 pending its DI (part 8), 1 new training DI (high gain).
       The clean/crunch shortage is unchanged.* *Parts 7a, 7b, 8 and 9 heard 2026-10-26: Signs ElecGtr6 verified (not in
       T3's frozen V-real-11); 50 metal DIs admitted, all high gain; Strobe/MekaPhil's 13 DIs admitted: 11 "unknown"
       (out of the high-gain cap) and Timeless Part 2's 2 clean (PR #306); the shortage is nearly unchanged.*
   - (d) **T3, decided after T2:** one rebuild that is also every-control stage 2D, on self-built
     mixes with full-space labels and any approved new DIs, read on K and V-real (*K empty since 2026-10-25: its
     read is open until K comes back*). Its downloads are
     asked for then. *Approved by the user 2026-10-26 (decision 5); plan declared the same day, F5 run and read the
     same day ([T3](trusted-data-t0-design.md#t3-declared-2026-10-26-nothing-run), every-control
     [amendment 2](every-control-plan.md#amendment-2-2026-10-26-stage-2d-is-t3-and-its-label-space)):* 115 Morgan
     controls learned (today 25). Two steps: **F5**, T2's examples re-rendered with full-space labels against a
     today's-space model on the same examples and fit set (the gate: what every control is worth); then **F20**, 20k
     examples with high-gain sources capped at 50%. Primary D_F20 − S on V-real (the 10 plus It Was My Fault ElecGtr1,
     and Signs ElecGtr6 if part 8 clears its DI; frozen before any T3 read: *V-real-11 at F5's plan, without Signs*), per class beside; an interference check
     (adding high-gain sources, D_F20 − D_noHG). The pull is shared, fitted on 12 sections instead of 4, and read with
     and without. Output gain is set by loudness matching, not predicted (confirmed by the user 2026-10-26). About 58k renders, 22k separations,
     5–6 h MPS, 32–42 h wall. The metal intake's DIs (13 sessions, 7 bands, downloaded 2026-10-26) join
     F20 as they pass the checks and the ear, under the caps. F5 starts with a zero-render dry run that prints the real
     pool. Clean and crunch sources for F20: Strobe and MekaPhil ×4 (approved 2026-10-26; ledger
     `cambridge-new-training-bands-2026-10-26b`) are DI only. 13 of their 18 DIs pass D2/D3; ear page part 9 (14
     cards) is pending. *Heard 2026-10-26: all 13 admitted; every style question left blank.* Each DI card also asks
     the playing style. Only a clean/crunch-style answer makes a DI-only DI not high gain. A raw DI cannot show the
     style, so the user decided on 2026-10-27: a DI-only DI with no style or song tone is **"unknown"**, its own
     group, left out of the high-gain cap and capped at 25% of F20's draws (decided; a design default the user may
     overrule) (DGX keeps high gain). Where a song has an
     amp track, its tone sets the class: only "Timeless (Part 2)", whose `ElecGtr2` part 9 heard alone as clean, so
     its 2 DIs become clean at the next `lists` run. The other songs are DI only and stay "unknown". Strobe "Gone" and "Nostalgic" (kept 2026-10-26;
     ledger `cambridge-new-training-bands-2026-10-26c`) give no usable DI: no file is named as a DI, so their 7 guitar
     tracks are excluded. F5 needs none of them.
     **F5's outcome (2026-10-26, audited: every row recomputed;
     [outcome](trusted-data-t0-design.md#f5-outcome-2026-10-26)).** Log ratios, lower is better, 7 bands, V-real-11:
     - **The gate, D_F5 − D_core5: +0.079 [−0.065, +0.224]: not shown** (2 bands better, 5 worse; per seed +0.082
       and +0.091, without the pull +0.087). By the declared rule F5 stops and reports; **F20 runs only with the
       user's yes.** D_F5 − S +0.088, D_core5 − S +0.009, D_F5 − constant −0.004; D_core5 − D_SYN −0.020 on
       V-real-10 (it reproduces T2).
     - **Why:** one part (Colour Me Red ElecGtr03, +1.015) drives it, through the time effects and spring (that
       family +0.087; every other family within ±0.002; with it at S the gate is −0.0075 [−0.069, +0.054], a post-hoc re-read, not declared; interval holds 0). The
       time-effect heads learn nothing (FS5 switch AUCs 0.49–0.56; compressor and drive about 0.58–0.59), so the readout turns reverb on in 54 of 66
       directions where S has it off. A rough probe finds reverb and delay mostly gone after separation; the factory
       draws are wet (reverb 74%, delay 63%); where the judge punishes the tails is likely one sparse part, where tails fill the gaps (one part; its sparseness not measured). The amp head is
       near chance (FS5 accuracy 0.39).
     - Integrity checks passed (control check, positive control 50 of 50, same examples and FS5 for both arms,
       V-real-11 frozen before any read, healthy training). Caveats: 785 of 4,974 full twins dropped as near-silent
       (mostly wide draws with quiet cab mics); 28% of full twins separated on another device than their core twin.
       6,246 renders.
     - **Next, the user's decision (2026-10-26; R0 and R1 since ran, below).** The ML session proposed a zero-render per-control readability check on FS5,
       then about 70 renders of D_F5 with its unreadable controls at S against D_core5, then F20's decision (its
       main value is new data: metal, Strobe/MekaPhil and the new bands' DIs, then pending the ear). Fixes for F20:
       redraw near-silent draws, keep each pair on one device, reconsider the switch readout and prior.
       *Approved by the user 2026-10-26 and declared the same day, before any of it ran
       ([F5 follow-up](trusted-data-t0-design.md#f5-follow-up-readability-r0-and-the-unreadable-controls-at-s-r1-declared-2026-10-26)):
       R0 reads each of D_F5's heads on FS5 against the constant (zero renders); R1 renders D_F5 with every
       unreadable head at S against D_core5 (99 renders), post hoc and descriptive. Whether writing S for an
       unreadable control fits amendment 1 is the user's call. F20's three fixes are declared in the plan.
       R0 read the same day: 20 of 116 heads read better than chance (5 of 85 knobs, 14 of 28 switches, the amp
       choice, no mic); time effects only the delay's switch, springs none. R1 ran 2026-10-27 (below).*
       *A zero-render tone-information probe (2026-10-27, [design and outcome](tone-info-probe.md)): the target
       render holds most of the tone (a linear probe reads 86 of 116 heads); the mix hides most of it from a linear
       reader (30); the X-LANCE stem gets none of it back and is slightly worse (20, as D_F5). The fixable loss is the
       separator failing to recover what the mix masks, a 66-head gap. Level does not explain it (the target with its
       level removed reads 91), and a finer representation or the DI adds nothing. Next: a model fed the mix, or mix
       plus stem, first; then fine-tuning X-LANCE on the self-built mixes against their known targets. Faint "on"
       labels explain part of the delay's weakness (stem AUC 0.62 → 0.73 on its loudest third), not the reverb's,
       tremolo's or springs'. Post hoc, mix plus stem reads 24, no more than the mix alone (30), to a linear reader
       ([addition](tone-info-probe.md#addition-mix-plus-stem-f-declared-2026-10-27-post-hoc-before-it-is-computed)).*
     - **R1's outcome (2026-10-27, 99 renders; post hoc and descriptive; audited, every row recomputed;
       [R1 outcome](trusted-data-t0-design.md#r1-outcome-2026-10-27-99-renders-post-hoc-and-descriptive-audited)).**
       D_F5:R (D_F5 with every unreadable head at S) − D_core5 **+0.062 [−0.080, +0.204]**, 4 bands better and 3
       worse; crunch −0.013. D_F5:R − S +0.071, D_F5:R − constant −0.022, and D_F5:R − D_F5 with time effects and
       spring at S +0.070. The delay's switch, counted readable at AUC 0.557 (lower bound 0.505), stays on in 29 of
       66 directions, and Colour Me Red ElecGtr03 again drives the result: +0.846 against D_core5 (+0.949 against D_F5 with time effects at S, the better evidence that delay is the cause). "Delay is the cause" is the best
       fit, not proven: no render isolates it. **The user's ruling (2026-10-27, the amendment 1 question):** R1 is
       allowed as a measurement only; writing S for unreadable controls is not adopted as the method.
   - **Every-control stage 1** runs on the trusted panel's parts and can now run, now that the ear
     has cleared their amp tracks (knob ceiling 2's panel: 7 parts in 7 bands, verified 2026-10-25). It needs no rebuild, so it need not
     wait for T1, T2 or T3 ((b)–(d) of the 2026-10-23 order above); they share the renderer.
   - **The real-mix test** ([plan](real-mix-test-plan.md), #267) runs on V-real's parts.
   - **T4:** V-real (with Jen Hartswick & Nick Cassarino), K (*empty since 2026-10-25; open*), then the ear. V-real picks T2's winner
     and is read again here, so T4 is not independent. Then the fresh-song decision test (item 5
     below).

   **Next, in order (2026-10-22 evening; superseded 2026-10-23 by the trusted-data plan's order
   above, kept for the record):**
   - (a) **The data review** by the user: the verdicts define the trusted set.
   - (b) After (a): **cleaning steps 0–1, then the rebuild** (PR #273, above), on the trusted set.
   - (c) After (a): **every-control stage 1** on trusted parts only. It needs the trusted amp-track
     list, not the rebuild, so it need not wait for (b); the two share the renderer.
   - (d) **The real-mix test** ([plan](real-mix-test-plan.md), approved and merged, #267), after
     the cleaning. It runs arm A and the direct model (the user's amendment 1, 2026-10-22).
   - (e) **The coverage stage 2 build:** every-control labels, clean backings and new DIs together
     (an amendment to the every-control plan first).
   - Then the fresh-song decision test (item 5 below).
   - *Proposed, not yet approved, so not in the order:* a DI-source inventory for more bands. Why:
     the 277 sections and 9 bands limit both training and test power, and part C's curve flattened
     with more renders of the same DIs. New DIs reach (e) only if the user approves it.

   **The earlier work order (from 2026-10-19), with its status:**
   1. **Better target-guitar separation** ([plan](separation-finetune-plan.md), reviewed):
      zero-render ceilings on stage F first (how much the other guitars cost; Wiener and blend
      fixes), then an oracle class-stem arm (about 7k renders) decides whether fine-tuning Mega-53's
      head can pay (YG − M ≤ −0.032) or a conditioned one-guitar separator is the route (a user
      decision: data, disk, a product question). Steps after the first need about 2 GB of disk
      freed. *2026-10-20 (user, revised the same day): fine-tuning or adapting an existing separator
      is fine, but not designing and training a new one, and there are no rented machines, so
      training runs on this Mac, and any run longer than minutes (e.g. Step 2's ≤ 11 h fine-tune)
      needs the user's approval. Step 0 is done; Steps 1–3 are open again, Step 1 can resume; a
      newly trained conditioned separator (trained route B) stays out. Released checkpoints and DSP
      splits remain. The [pan screen](stereo-side-results.md) ran: a known side is worth about
      +1.4 dB (target's channel at ±0.6 +1.50; centre model on a centred lead +1.35), short of
      +2 dB; blind picks lose. The [coherence mask](stereo-side-results.md#amendment-1-the-inter-channel-coherence-mask-2026-10-20)
      adds only +0.35.*
      *Reading, 2026-10-20: separation is mostly mapped. A class fine-tune of Mega-53 is capped at
      +0.30 dB (Step 0), so Steps 1–2 are parked by choice, not barred (Step 2's ≤ 11 h would need
      approval). What is
      left is small or a product question: the pan side from the arrangement or the user's ear
      (about +1.4 dB), the centre model on centred leads, X-LANCE gtr_mss as one more separator
      row. Moises is outside every workflow (user).*
   2. **Train the direct model on realistic separated stems,** and check how much it relies on the
      stem against the mix ([plan](direct-model-stems-plan.md), declared and reviewed 2026-10-19):
      zero-render checks of the stem mismatch on the existing model first, then a 5k pilot (≈2.4 h
      of training, approved and run; real Mega-53 stems, a mix-only model, the old recipe), then
      one stage F test, D − S primary. Step 3's 5–7.4 h of training is approved (the user,
      2026-10-20); disk is no longer a block.
      *Gate 1 done 2026-10-20 ([results](direct-model-stems-gate1-results.md)):* the stem matters
      (GATE1 STEM); the mix adds little behind a clean or separated stem, so the next model should
      read the separated target stem alone (a pilot-arm change for the user to approve).
      *Pilot done 2026-10-21 ([results](direct-model-stems-pilot-results.md)):* `PILOT STEM`.
      The stem-only model beats the old recipe (R_out −0.0127 [−0.0216, −0.0039]), and its
      augmentations help. But every pilot model is still worse than a per-class constant
      predictor (D_stem +0.0128 [−0.0013, +0.0269] on R_in). More data helps (−0.017 per
      doubling on average; the seeds differ, about −0.028 and −0.006), so the probe reads
      `PROBE CONTINUE`. Even so, the full model is projected to land near the constant (−0.020
      log-linear, likely optimistic given part C's flattening; −0.004 capped). *(2026-10-23 review:
      read the same way, the full 20k model gave +0.012 [−0.021, +0.045] against the constant on
      R_in, the pilot's +0.0128: flat from 5k to 20k, with the separator change as the caveat. So
      −0.017 per doubling should not size new plans; more distinct DIs and sections is the lever
      the evidence supports.)*
      *Amendment 2 in force 2026-10-21 (user):* the full build, step 3 and step 4 use X-LANCE
      gtr_mss stems (0.988× Mega-53 on MPS). The pilot, V_sep and the rest are separated anew, about
      19–22 h on one MPS and one CPU worker. D0 is unchanged, and Mega-53 stays the fallback. Then
      step 3's training (approved by the user on 2026-10-20).
      *Amendments 5 and 6, approved 2026-10-22 (user; PRs #263, #264), before any step 3 data:*
      step 3 reads each knob's mixture median, averaged over 3 seeds × 2 halves, then pulled toward
      the per-class constant (the pull fitted on the early-stopping set). The right cab's knobs
      leave E when that cab is off. On the pilot's early-stopping examples this reads −0.0107
      [−0.0186, −0.0027] against the constant, where the old readout read +0.0106 (in-band, not a
      forecast). The E check is now descriptive. **A sound-based gate decides step 3:** on R_in
      (1,407 examples, 4 bands), does D's preset render closer to the true preset than the
      constant's (about 5.9k renders)? Step 4 runs only on `GATE OK`.
      *Amendment 7 (2026-10-22, user):* the gate read GATE STOP (log d D − constant −0.1538
      [−0.3360, +0.0284], 4 bands; power about 46%; D − D0 −0.1266 [−0.1864, −0.0669]). Step 4
      runs anyway, unchanged, labelled "run under a user override of a GATE STOP". *(2026-10-23
      review: on the trusted rows, Dark Ride and Adam Buckley's unflagged examples, the gate reads
      about −0.016 on 2 bands, with no interval; about 93% of the −0.154 came from Kimock and
      Swatkins, now out of K. So no trusted evidence yet shows D beats the per-class constant.)*
      *Steps 3 and 4 done 2026-10-22 ([results](direct-model-stems-results.md)):* the X-LANCE
      build (V_sep 1,720, pilot 5,995, rest 15,309 examples, 0 refused), step 3's training (6
      runs) and the readout (masked E, D − constant: R_in −0.0159 [−0.0363, +0.0046], V_dev
      −0.0143 [−0.0223, −0.0063]; descriptive); the gate read STOP. **Step 4, run under a user
      override of a GATE STOP: `STEP4 NOT SHOWN`,** D − S −0.034 [−0.103, +0.034] (12 bands, 5
      better; power about 21% for that effect). The new model clearly beats the old one (D −
      D_existing −0.067 [−0.113, −0.021]) and is indistinguishable from arm A's search (D − H
      −0.006 [−0.062, +0.050]; not shown equivalence) with no renders; clean leans better than S, crunch worse.
      *(2026-10-23 review: D − D0 is −0.006 [−0.032, +0.019] on stage F, so training on separated
      stems did not move real-mix accuracy; the −0.067 is mostly the readout, the stem and the pool,
      not yet split. The 21% and 46% are observed power, which adds nothing to the interval; the
      interval says step 4 rules out a gain beyond −0.103 and a loss beyond +0.034. The song-blind
      per-class constant was never scored on stage F, so how much of D − S is the constant's pull is
      unknown; T2 now scores it on V-real, the user's decision of 2026-10-24.)*
      *Since (2026-10-22 evening):* every control (#266) and the real-mix test (#267) are approved
      and merged, and the order is above. These figures were read on all parts, before the
      trusted-data rule; they get a trusted re-read on V-real's parts now that the ear has answered (the
      trusted-data plan; stage F's no-high-bleed row read −0.023).
   3. **Two zero-render checks.** *Done 2026-10-19 ([results](shrink-snr-judge-v3-results.md)):*
      the best shrink does not measurably depend on stem SNR (a rule by SNR gains −0.003 [−0.013,
      +0.007] on held-out bands; nothing on realistic stems), and judge v3 agrees with the ear a
      little less than the default judge (Spearman 0.64 against 0.80; one pair worse in four of
      five trials, sign test p 0.125, so weak).
   4. **Real-mix previews:** downloaded 2026-10-20 ([results](mix-previews-results.md); 10 songs
      and a Signs remix). The real-mix gap is measured (about 0.6 dB of stem SNR, half from lag).
      *The real-mix test plan is approved and merged (#267, 2026-10-22); since 2026-10-23 it runs on
      V-real's parts (the order above).*
   5. **Then a fresh-song decision test** of the two routes on unseen parts (stage F is shrunk to
      V-real, and V-real's parts are reused). If one clearly beats S there, build the product around
      it. *(2026-10-23 review: no data is named for it yet. V-real is development data, read about
      ten times, and at 7 bands a route needs about −0.14 (D) or −0.10 (arm A) to show with 80%
      power; so V-real and T4 cannot decide the route. Where the decision test's data comes from,
      and its ship rule, are open decisions below.)*

   **How results are read (the user's rules):**
   - no arbitrary pass/fail bars: every comparison is an effect size with a 90% band-clustered
     interval, and any improvement is built on; under-powered is not failed;
   - the best estimate is chosen, with the cheaper option on a tie;
   - controls explain a result, they don't veto it;
   - a weak component (the separator, the rebuild) is a research target, not a reason to drop the
     route;
   - the listener's answers are trusted; layout confounds are caveats;
   - an effect left off is a correct answer on a dry record;
   - only trusted data (2026-10-22): dirty tracks are excluded, not flagged, and the user's
     listening decides what is trusted.

   **Kept:** metal out of scope, arm B (the older settings model) paused. *Superseded 2026-10-22:*
   bleed handling (no cleaning; the no-high-bleed row beside all parts) gave way to the
   trusted-data rule. **Parked until after the earlier steps 1–2:** known-answer B2
   (proposed, up to 4 fresh songs, about 14k renders), multi-section step 3 (held-out sections as arm
   A's scoring unit), and the dose probe's zero-render follow-ups (all in the
   [history](roadmap-history.md#step-0-the-song-to-preset-model-as-it-stood-on-2026-10-19)).
   **Open user decisions, as they were taken** (updated 2026-10-23 after the [review](research/program-review-2026-10-23.md);
   the ML session's recommendation first). *The decisions still open are listed under "Where it stands,
   2026-10-27" above.*
   - *Decided 2026-10-24 (user, all as recommended):* the two conflicts' measured fails stand; the
     stem spot-check joins this sitting; every DI is heard before it counts; the song-blind constant
     is a V-real arm at T2 (relayed by the cloud review, then confirmed by the user in the ML session).
   - *Decided 2026-10-24 (user, as the ML session suggested):* Cnoc An Tursa is not admitted to K; at
     most a side check, never in a deciding number. SYN-E is dropped from T2 until a clean-class DI
     source (EGDB or GOAT) passes the DI checks.
   - *Before T2:* read T2's tie from the interval (a tie when it holds 0) rather than
     |point| < 0.03. *Moot for T2 (2026-10-26): both rules read its primary as a tie.*
   - *After T2 (2026-10-26):* decision 5, whether T3 goes ahead on T2's tie. *Decided 2026-10-26 (user): T3 goes
     ahead.*
   - *After F5 (2026-10-26):* whether F20 runs on F5's gate (+0.079, not shown), and first whether the readability
     check and the ~70-render re-read run ([F5 outcome](trusted-data-t0-design.md#f5-outcome-2026-10-26)).
     *The check and the re-read approved 2026-10-26 (R0, R1).* Open: whether writing S's value for a control the
     model can't read fits amendment 1 ("no fixed rule stands in for an unheard control"); it also sets F20's readout.
     *Decided 2026-10-27 (user): R1 is a measurement only; writing S is not adopted as the method. F20 itself is
     still open (the short list under "Where it stands, 2026-10-29").*
   - *Settled by the ear (2026-10-25):* K's bands. T1's K is Adam Buckley and Dark Ride; Kimock's
     and Swatkins' 4 DIs were all heard processed, so they cannot rejoin. (Cnoc An Tursa: decided
     2026-10-24, not admitted.)
   - *Before T3:* where clean-class training DIs come from (after the ear the pool holds 1
     clean-class and 1 crunch section of 181; V-real has 2 clean bands): EGDB on a borrowed backing
     (downloaded; its DI checks first), GOAT (access requested), Jen Hartswick & Nick Cassarino as
     training instead of test, Strobe and MekaPhil now, or none. *Strobe and MekaPhil taken in 2026-10-26
     (part 9's ear pending); Strobe "Gone" and "Nostalgic" the same day, with no usable DI. Part 9 heard
     2026-10-26: 13 DIs admitted; since 2026-10-27, 11 are "unknown" (out of the high-gain cap) and Timeless Part 2's
     2 are clean.*
   - *Before T4:* the decision test's data and ship rule (keep the fresh bands out of pooled V-real
     readings; possibly bring step 7 forward with a declared verification phase); whether arm A
     gets every-control coverage (stage 2A, which dropped out after GATE STOP) or routes are
     compared on today's space; whether the stored C′ and step 3's D keep running under a recorded
     exception to the trusted rule.
   - Reopening arm B (its shuffled-input control first), at the decision test. *(Tone King's
     true-DI oracle, once the ML plan's step 2, is now every-control stage 1, approved
     2026-10-22.)*
   **After the decision test:** the ML plan's step 5 (optimiser comparison), step 6, and step 7,
   the pooled held-out test.

   **Renders:** about 370k to 2026-10-19 (250k to 2026-10-17, then multi-section 21.6k, rebuild-tone
   8.3k, B1 17.3k, dose probe 7.4k, part C 43.1k, oracle-DI 7.0k, perfect separation 14.0k,
   direct-existing 0.9k, record-match 0.8k); each later result reports its own. No fixed limit
   (2026-10-16): each step's plan declares when to stop rendering from its own evidence and reports
   what it used.

   **How the Mac is shared (the MPS GPU, 8 CPU cores, 32 GB):** one GPU job at a time; at most 3
   render processes machine-wide, with `isolate`, grouped by amp; one discarded priming render after
   any process start, amp change or DI change; separation only when the renderer is idle or light.
   Plans are reviewed by an independent agent before compute; the cloud researcher takes literature
   questions and the task executor monitors and downloads.

**Product steps** (the history of steps 1–6 is in [roadmap-history.md](roadmap-history.md)):

- **Done, 2026-10-12 to 10-14:** routing fixed and re-checked
  ([routing](generate-routing-results.md), [re-check](generate-routing-recheck-results.md));
  a second starting point when the part isn't clean or the class is a guess; the starting
  presets heard by ear ([listening](starting-preset-listening-results.md)); fixes from
  two real end-to-end runs (no default effects, don't guess the part's window, research
  the part, not the song, disclose pedal stand-ins), and two more runs where the second
  start caught a wrong guess ([end-to-end runs](e2e-runs-2026-10-13.md); the old
  "another end-to-end run" item); the DI-path
  defects D-M1 (product side), D-M7, D-M8's start and D-M13 (the carried-over render),
  and D-M17/D-M18's texts; `generate` framed as building the whole preset.
- **Done, 2026-10-17: the arrangement prior.** For a real song, `generate`'s research
  also writes every guitar, the sections each plays, and known sound changes, each with
  sources and a confidence ([format](../reference/arrangement.md),
  `scripts/arrangement.py`). It was the user's idea, and it feeds the ML session's
  planned per-section fitting: one average preset is hurt where guitars or sounds
  change. That session aligns the section names to the audio and checks every claim.
- **Done, 2026-10-21: the clean starts checked on the open-chord riff.** The SW50R and
  AC20 clean baselines break up; the PR12 template is clean and the PR12 baseline
  borderline (one listener, not blind; a linearity measure agrees). `generate` step 4
  records it. Turned down (`sw50rVolume` 15, `ac20Volume` 10) both play clean, so for a
  part documented as fully clean `generate` set those volumes; by ear on 13 real clean parts
  (2026-10-22, [results](clean-start-volume-listening-results.md)) only AC20's held (9 of 12; 4 of 7 without bleed),
  so SW50R's was reverted and PR12 stays (mostly "can't tell"). The
  faint crackle on chord decays is most likely the PR12 baseline's own slight breakup
  (one listener, by ear) ([results](clean-start-breakup-results.md)).
- **Done, 2026-10-31: the X editions.** Morgan Amps Suite X and Tone King Imperial MKII X
  install beside the originals, and both load the presets these tools write as legacy
  presets (the user checked both plugins). Morgan X's presets hold the same controls at
  the same stored values. The only change is three cab flags that replace the two
  per-side stereo switches. They are now read as the `morgan` pack: sections come from
  the file's tree (`format/valuetree.py`), because X leaves out the empty markers that
  the old reading relied on. Generated presets go to both User folders when X is there
  ([installing](../reference/installing.md)). Not done: Tone King X's own presets use a
  new layout (104 entries against 259, renamed controls) that no pack reads; renders stay
  on the original plugins.
- **Setting controls has real headroom** ([knob ceiling](knob-ceiling-results.md),
  2026-10-14): with the take's true DI, on development, a knob search got about 22%
  closer by the judge than `generate`'s starting preset (−0.253) and 19% closer than
  the best factory preset (−0.205, every band). The settings were specific to the part
  (which cannot rule out the search fitting the judge on each recording; listening
  guards against that), and in a second blind sitting one listener preferred a searched
  setting over the best factory preset on 7 of 7 trials, chosen mostly where the gains
  were largest. Lower bounds, true DI, one take.
- **Next: `generate` sets more controls from the song,** if and once the ML session's
  decision point (step 0) shows a way to get such settings without a DI
  ([plan](research/ml-plan-2026-10.md), decision 5 put the `generate` change after
  step 3's readout). As of 2026-10-22 neither ML route is ready to ship: on fresh full mixes
  arm A reads −0.028 [−0.064, +0.008] against S (htdemucs) and the direct model −0.034 [−0.103,
  +0.034]. The ML session's next steps (since 2026-10-27, a mix-aware input first) are in
  step 0. Until then `generate` sets what research documents. *The two render checks are done
  (2026-10-14, one development part, PR12):* fresh-process renders with isolation repeat exactly
  (maximum difference 0.0); the isolation fade-in (the same for every candidate) moved the match
  loss by about 0.003 weighted, mostly its dynamics term (0.012: attack and loudness range;
  timbre 0.0002), at the template's default settings. Its effect on a ranking is not
  measured: the shift is a distance to an unfaded target, so it can differ by candidate.
- **Parked, with reasons:**
  - **Riffs in the part's style and register:** *built 2026-10-15; registers and the rebuilt
    chords checked by ear 2026-10-17* for chords and single lines in three registers ([plan](riff-library-plan.md)).
    The low and mid chords were rebuilt from EGFxSet's single Strat notes after the
    Guitar-TECHS strums proved to carry clicks and fret buzz; registers were confirmed;
    `generate` picks at most two by the part. Still missing: power chords and arpeggios (no
    shippable source), and automatic chord and register detection (no open tool proven on
    stems; Basic Pitch would need a pip install and an ear-labelled check).
  - **The song's own part on the listening page:** the rebuilt DI is not good enough by
    ear yet.
  - **The part locator:** underpowered on development data (7 targets in 6 bands against
    a floor of 15 in 10; [results](part-locator-results.md)); `generate` asks for a time
    instead.
  - **Clean first when the class is a guess:** exploratory, in-sample and post hoc on the
    re-check runs (31 of 34 parts called a guess; [follow-up](generate-routing-recheck-results.md)).
    Overall undecided (+0.044, 90% −0.034 to +0.118), but it clearly costs crunch parts
    (+0.19, 0.08 to 0.30) for a small, undecided gain on clean ones (−0.05, −0.10 to
    +0.01). Not adopted.
  - **DI-path leftovers:** screening each enumerated variant, a midpoint probe, the
    tremolo rate step, `paired_di` tremolo, and the search objective (ML).
  - **Earlier research steps** (a DI-free distance, the derived-DI route, the judge's
    coverage): done or ML's; see the history file. Any search scored by the judge needs
    a positive control first.

## Parked

- **Predicting settings from a recording: reopened 2026-10-06, now step 0 above.** The
  history follows ([supervised-model-plan.md](supervised-model-plan.md)).
  - The kill tests did not pass on SW50R or clean PR12
    ([K1–K3](kill-test-results.md), [PR12](kill-tests-pr12-results.md)).
  - No cheap fix rescued recognition on real tracks ([quick checks](quick-checks-results.md)).
  - Reopen only if step 2 finds features that carry over from renders to real
    recordings. If it is ever built, its amp output is a set of acceptable amps.
  - **Reopened as a proof of concept, 2026-10-06**
    ([plan](preset-model-poc-plan.md) → [results](preset-model-poc-results.md)).
    - **What ran:** a network trained on 18,843 PR12 renders of sampled settings.
    - **Result:** not passed. It was 3.6% closer than template+R by band median, against
      the 10% bar.
    - **What it shows:** it is the first song-only method here to read part-specific
      information on clean PR12 (closer than its shuffled control on 21–22 of 28 parts).
    - **The catch:** its gain over the template rests on two parts.
    - **Next:** learn the sound rather than the knobs, train on separated stems, and
      move to heavier tones.
  - **Rebuilding the DI, 2026-10-07**
    ([plan](di-recovery-plan.md) → [results on clean PR12](di-recovery-results.md)).
    - **What ran:** a network rebuilds the guitar's DI from the recording, and the judge
      picks a menu preset through it.
    - **Result on clean PR12:** not passed. Picks were 8.5% closer than template+R (20 of
      25 parts), 52–60% of the menu oracle's gain, and short of the declared margins over
      the no-training stand-in.
    - **Follow-up, 2026-10-08:** heavier-tone development and reserved confirmation
      are complete ([confirmation](set3-heldout-confirmation-results.md)). Neither
      tested amp passes confirmation; wider search is deferred pending a development
      positive control (step 0).
    - **DI-free reranker, 2026-10-07** ([rerank-plan.md](rerank-plan.md)): ranking the menu
      by log-mel or PANNs CNN14 distance to renders through other folds' DIs did not pass.
      Neither beats `flatref` paired; `net` stays the best chooser.
    - **Tone encoder, 2026-10-08** ([tone-encoder-plan.md](tone-encoder-plan.md)): a
      contrastive encoder trained on 16,800 crossed renders identifies presets across
      players (74.5% vs 14%), but as a reranker on real recordings it is worse than
      template+R. Not passed.

## Decisions

| Date | Decision | Record |
|---|---|---|
| 2026-10-02 | Song only: the user never records a DI | — |
| 2026-10-03 | Without a DI, keep the starting preset (figures later marked unconfirmed) | #107, [no-DI re-check](no-di-rule-under-the-judge-results.md) |
| 2026-10-03 | The judge replaces the v3 score as the measure of closeness | [measuring-closeness.md](measuring-closeness.md) |
| 2026-10-04 | Crop rule 2 (where the DI plays most) for new crops | [validation-datasets.md](validation-datasets.md) |
| 2026-10-04/05 | Kill tests not passed; model work parked | [kill tests](kill-test-results.md), [PR12](kill-tests-pr12-results.md), [quick checks](quick-checks-results.md) |
| 2026-10-05 | Amp choice is a set of acceptable amps; AC20 reaches fewer of these clean parts | [amp reach](amp-reach-results.md), [quick checks](quick-checks-results.md) |
| 2026-10-05 | Research not shown to beat the template or chance at picking presets; choosing among four helps with a perfect ear | [song-only shortlist](song-only-shortlist-results.md) |
| 2026-10-05 | `generate` offers four presets on a listening page; riffs from Guitar-TECHS P1 (CC BY 4.0) ship in `samples/riffs/` | `skills/generate/SKILL.md` step 5b |
| 2026-10-06 | Song-to-preset is judged on the product's question: does an average guitar, playing the recording's notes, through the preset sound like the record (the take's DI re-equalised to an average guitar's balance, then the judge). The judge's own question, recreating the original rig on its own guitar, is reported beside it. A short listening check confirms the measure first. | [DI robustness](di-robustness-results.md) |
| 2026-10-06 | The audition page stays an option, not generate's main path (check inconclusive) | [listening-check-results.md](listening-check-results.md) |
| 2026-10-07 | The average-guitar measure is confirmed by listening (23 of 24 disagreement trials, 6/6 repeats, 6/6 swap) | [listening results](avg-measure-listening-results.md) |
| 2026-10-07 | Rebuilt-DI preset choice not passed on clean PR12 (8.5% vs 10%); continue to heavier tones and a search beyond the menu | [results](di-recovery-results.md) |
| 2026-10-07 | Open source only: no cloud APIs, commercial tools, or unlicensed or gated weights; published methods are reimplemented | [round 5](research/round-5-guitar-models.md) |
| 2026-10-07 | No hand-made DI-free distance reproduces the judge's choices; next are learned ones | [di-free-distance-results.md](di-free-distance-results.md) |
| 2026-10-08 | Rebuilding the DI works on heavier tones against the clean default and the stand-in. Against a constant driven preset: SW50R a conditional pass, PR12 not passed, AC20 failed. The constant's definition is to be declared before the held-out confirmation | [set-3 results](di-recovery-set3-results.md) |
| 2026-10-08 | Reserved confirmation not passed on SW50R or PR12 under either declared timing. Independent numerical/audio checks agree. This learned method does not ship; diagnose on development data and use fresh reserved data for future confirmation | [confirmation results](set3-heldout-confirmation-results.md) |
| 2026-10-08 | Known-DI development selection shows menu headroom on all three amps. Diagnose the rebuilt chooser's refusal on a fixed panel before more training; neither this diagnostic nor a proxy rescue is confirmation | [development diagnostic](set3-development-diagnostic-results.md), [proxy-check plan](set3-mask-diagnostic-plan.md) |
| 2026-10-09 | Codex continuation reviewed: held-out failure confirmed; ranking works with the true DI, the loss is in the rebuilt DI; native-pilot "failure" was a mis-specified test; research stays in the repo until the plugin is ready | [review](codex-continuation-review.md) |
| 2026-10-12 | `generate` asks before building the listening page; the user can decline (user decision) | `skills/generate/SKILL.md` step 5b |
| 2026-10-12 | A mix's top-end roll-off is a reason to check, not to darken (one song, mixed evidence) | `reference/reading-a-reference.md`, #167 |
| 2026-10-12 | `generate` installs a second starting point when the part is not clean (measured), and routes by the part's documented sound, not the song's genre (a rule, not yet re-checked) | `generate-routing-results.md` |
| 2026-10-12 | The new routing rule is kept: it routes better than the old skill on the same parts (in-sample) | `generate-routing-recheck-results.md` |
| 2026-10-12 | DI path: Tone King renders pre-rolled (D-M1), no tremolo from a recording (D-M7), no low EQ from a mix (D-M8 start), screen and `--enumerate` texts (D-M17, D-M18); the rest parked | [roadmap-history.md](roadmap-history.md#product-steps-16-as-they-stood-on-2026-10-14), step 5; #168–#171 |
| 2026-10-13 | The starting presets are heard as closer than what they replaced, and the clean start over the crunch start on clean parts (in-sample, one listener); step 4 says so | `starting-preset-listening-results.md` |
| 2026-10-14 | Clean first when the class is a guess: not adopted (exploratory; costs crunch parts) | `generate-routing-recheck-results.md`, follow-up |
| 2026-10-14 | ML plan decisions: train C′ for every fold; 200k render limit with knob ceiling counted; approve the three-way comparison; lift the "33" rule with a development ledger; Five-guitar and Optuna yes, GOAT not now; held-out results the render bug touched kept with a note (not re-rendered), no reserve; optimiser comparison after the readout | [ML plan](research/ml-plan-2026-10.md), section 3 |
| 2026-10-15 | Arms A and C count as failed (arm A's control), but the route is kept: the DI rebuild is the bottleneck, and a DI-recovery track opens | `song-settings-plan.md`, recorded outcome; [DI recovery](research/di-recovery-2026-10.md) |
| 2026-10-15 | Time effects are kept only when the gain is clear; "off" on a dry record counts as correct; the listener's picks are trusted despite the letter layout | `knob-ceiling-2-results.md` |
| 2026-10-15 | Mega-53 weights re-downloaded for the separator screen (MIT repo, release v1.0.21; no separate weights licence, as accepted for the 2026-10-08 test) | `~/ndsp-presets/tools/msst/provenance.json` |
| 2026-10-16 | No arbitrary pass/fail bars: report effect sizes with intervals, choose the best estimate, learn from any improvement (A, B, C) | memory and plans from this date |
| 2026-10-16 | Arm A's current best: a 52-render rebuilt-DI search shrunk halfway to S (−0.083 [−0.135, −0.032]); the shrink is the user's judgement call, the declared rule chose the unshrunk search | [arm A levers](arm-a-levers-results.md) |
| 2026-10-16 | Arm B: diagnostics done; sound-space retraining (B1, B2) approved, scored on step 3's songs too | [diagnostics](song-to-settings-diagnostics-results.md), [plan](song-to-settings-soundspace-plan.md) |
| 2026-10-16 | ML plan decision 2 revised: no fixed render limit; each step stops rendering by a declared, evidence-based stopping rule (search curve flattened, learning curve no longer improving, interval narrow enough) and reports renders used | [ML plan](research/ml-plan-2026-10.md), section 3 |
| 2026-10-16 | Arm B paused: the sound-space retrain beats the old arm B on songs but isn't shown to beat S; arm C not run | [sound-space results](song-to-settings-soundspace-results.md) |
| 2026-10-16 | Local objective: DI-only work against the htdemucs stem (and the DAC-9 add-on) dropped; improve the separator and the rebuild together | [results](local-objective-results.md) |
| 2026-10-17 | Bleed cleaning not adopted; high-bleed parts stay flagged and results report the no-high-bleed row beside all parts. *Superseded 2026-10-22: dirty tracks are excluded, not flagged (the trusted-data rule)* | [bleed listening](bleed-listening-results.md) |
| 2026-10-17 | The true-DI search to a stop (−0.293) replaces −0.269 as the ceiling reference; step 3's readings stand | [K_S extension](ks-ceiling-extend-results.md) |
| 2026-10-17 | htdemucs stays the separator: Mega-53 leans better on fresh full mixes, a tie (−0.017 [−0.039, +0.004]) | [arm A with Mega-53](arm-a-mega53-results.md) |
| 2026-10-17 | Arm A not ready to claim: −0.028 [−0.064, +0.008] against S on fresh full mixes. Fresh full mixes are the only yardstick for progress; next a rebuild change on short-time treble magnitude, then one fresh-song decision test of arm A (else arm B or a hybrid) | [arm A with Mega-53](arm-a-mega53-results.md), [rebuild gap](rebuild-gap-results.md) |
| 2026-10-17 | `chords` and `chords-mid` rebuilt from EGFxSet single notes (retuned, denoised above 3 kHz, down-up strum, even chords); Guitar-TECHS strums dropped for clicks and fret buzz | [riff plan](riff-library-plan.md), "Rebuilt" |
| 2026-10-18 | A screened DI library: 134.7 clean minutes from 237 development DIs after the hum rule's amendment 3 (159 before; the rest check may no longer refute a mains fundamental, which keeps 18 DIs' hum, Guitar-TECHS almost all hum: one P2 section stays clean); hum notch not adopted; two blind listening pages pending; known-answer test songs (part B) declared, B1 about 22k renders after the overnight runs | [clean DI library](clean-di-library-results.md) |
| earlier | Closed: response atlas, warm-start regressor, noise and synthetic probes | [tone-matching-plan.md](tone-matching-plan.md) |
| 2026-10-18 | The short-time treble loss (`stm`) lowered its error (−0.63 dB on the amp tracks) with no measurable ranking gain (+0.012 [−0.023, +0.047]); the long-term levers (leak-free EQ +0.132, `rank` second seed +0.099) lean positive, undecided; next an oracle dose probe of the short-time component before a per-bin log-gain head | [rebuild tone](rebuild-tone-results.md) |
| 2026-10-18 | Self-rendered sets declared and reviewed: B1, four known-answer songs (about 17.4k renders), then part C, a pre-training render set sized by a learning curve (40k pilot, one extension if it still improves); queued to run after the overnight runs, part C after the hum-screen amendment | [B1 plan](known-answer-b1-plan.md), [part C plan](pretrain-set-plan.md) |
| 2026-10-18 | Known-answer pilot B1: the exact-record pipeline works; arm A against S +0.001 [−0.523, +0.524] over 3 bands, undecided (Heather Jane +0.36, the other three −0.17 to −0.20); B2 proposed at the pool's cap, up to 4 fresh DI-only songs (about 14k renders) | [B1 results](known-answer-b1-results.md) |
| 2026-10-18 | Oracle dose probe (hedged): on top of the leak-free EQ, the full-band true short-time magnitude (C′'s phase, one resynthesis) recovers 0.74 [0.50, 0.86] of the remainder (+0.116 [+0.045, +0.187]); 2–8 kHz on E_st's mask only 0.25 (+0.039), below it; control undecided. Option 2 (per-bin log-gain head) only as a full-band field, ceiling `full100`, with a full-band gate metric instead of E_st | [dose probe](dose-probe-results.md) |
| 2026-10-18 | Oracle-DI arm on stage F (hedged): arm A searching through the true DI against the htdemucs full-mix stem reads +0.012 [−0.088, +0.112] vs S and +0.040 [−0.043, +0.123] vs H, so a perfect rebuild gives no measurable gain in the product setting; the stem objective, not the rebuild, limits arm A on full mixes | [arm A Mega-53, amendment 2](arm-a-mega53-results.md#amendment-2-the-oracle-di-arm-on-stage-f-2026-10-18) |
| 2026-10-19 | Part C, the pre-training render set: 43k renders; on true mixes of held-out bands the knob error flattened between 20k and 40k (Δ +0.0012 [−0.0020, +0.0045]), STOP, no extension; the guitar alone and training-style mixes still improve (post hoc). In-domain, not real-song; next a real-song test of a model trained on it; direct prediction proposed as the main route (user's decision) | [part C results](pretrain-set-results.md) |
| 2026-10-19 | Part C's existing 40k models on stage F (no training): D − S +0.033 [−0.053, +0.119], a tie leaning worse (unseen bands +0.010); the raw-DI judge leaves rebuilt-DI contrasts unchanged (H − S change +0.003), but on known-answer songs the measure DI caps the exact truth at 0.55 of S (raw: about 0) | [direct-existing results](direct-existing-results.md) |
| 2026-10-19 | Record-match listening check (5 parts, one listener, blind): the ear broadly orders S, H, D and the ceiling C as the judge does (Spearman mean 0.8, > 0 in 5/5; 0.6 without C); C heard closest in 4/5, even where only 10–15% below S; H above S in 4/5 on these high-SNR parts; D third on average | [record-match results](record-match-listening-results.md) |
| 2026-10-19 | Perfect separation on stage F (amendment 3): arm A with the amp track as target and rebuild source reads −0.094 [−0.131, −0.057] against S (−0.066 over H); the true DI on top −0.174. The lever is separation, then the rebuild; the halfway shrink hurts when inputs are good | [arm A Mega-53, amendment 3](arm-a-mega53-results.md#amendment-3-perfect-separation-on-stage-f-2026-10-19) |
| 2026-10-19 | Mega-53 is the ML default separator (htdemucs selectable), after the user heard it as much better on the separation samples; unlicensed open-source weights are allowed (user), which relaxes the 2026-10-07 rule for weights | [stereo and mix check](stereo-and-mix-check-results.md) |
| 2026-10-19 | Our development "full mixes" are unity sums of raw tracks and no session has a mix; real-mix previews (Cambridge Full Preview MP3s, Unmastered Mix WAVs) to be downloaded by the user | [stereo and mix check](stereo-and-mix-check-results.md) |
| 2026-10-19 | The direct model's tie with S is not a verdict on the approach (user): it was trained on perfect stems and tested on htdemucs stems. Two active routes, arm A and the direct model, with better separation as the shared lever; next a Mega-53 fine-tune on our multitracks, then the direct model on realistic stems | [direct-existing results](direct-existing-results.md), step 0 |
| 2026-10-19 | Zero-render checks: the best shrink does not measurably depend on stem SNR (held-out −0.003 [−0.013, +0.007]), so shrink 0.5 stays on separated stems; judge v3 agrees with the ear less than the default judge (Spearman 0.64 against 0.80, 5 parts), so the default judge stays | [checks](shrink-snr-judge-v3-results.md) |
| 2026-10-20 | Licence and cost rule (user): the project is non-commercial and open source, so anything open, non-commercial, unlicensed or gated behind an access request is fine (weights, code, tools, data); unclear licence terms go to the user to check; nothing may force other users to pay (beyond the Neural DSP plugin and Claude Code), free cloud APIs are fine, and tools the user pays for personally (e.g. Moises) are fine in development, and other paid tools need the user's yes. This replaces the 2026-10-07 "open source only" rule. ML plan §5 updated | [ML plan](research/ml-plan-2026-10.md), section 5 |
| 2026-10-20 | No separator training of any kind (fine-tune, per-song adaptation, new separator) and no rented machines (user: "way to specific and requires researches I'd like to avoid"). The separation-finetune plan's fine-tune step and trained routes are cancelled | [separation-finetune plan](separation-finetune-plan.md), [ML plan](research/ml-plan-2026-10.md), section 5 |
| 2026-10-20 | Separator rule revised (user, same day): fine-tuning or adapting an existing separator and feature extraction are fine; only designing and training a new separator, or a major modelling effort, is out (user: 'just not a major effort of modeling and training a new separator'); still no rented machines, so training runs on this Mac. Licences checked and accepted: SAM-Audio, Stable Audio Open VAE, X-LANCE/BS-RoFormer SW. Moises is for testing and sampling only, not training. Uploading Cambridge-MT or Telefunken audio to Moises, even for testing, is not yet ruled on; ask first. Models trained on Cambridge-MT or Telefunken audio may ship. Weathervane: no | [separation-finetune plan](separation-finetune-plan.md), [ML plan](research/ml-plan-2026-10.md), section 5 |
| 2026-10-20 | Training time (user): training that takes minutes is fine; any longer run (e.g. a C′ fold, about 6.5 h) needs the user's approval first; no week-long efforts. Applies to all models. Moises is not part of any workflow, testing included; it is used only when the user decides to, and uploading Cambridge-MT or Telefunken audio to it is then allowed | [ML plan](research/ml-plan-2026-10.md), section 5, [separation-finetune plan](separation-finetune-plan.md) |
| 2026-10-20 | Separation Step 0 (zero renders, audited): the other guitars, about 5.5 dB louder than the target (I +5.52 [+3.70, +7.24]), limit separation; a perfect class separator beats Mega-53 by only +0.30 dB SNR (band median, 12/12 bands); the four free test-time fixes all have negative point estimates, none survives Holm, so Step 3 has no candidate; YT − M −0.048 [−0.071, −0.026]. Step 1 (YG) stopped after 2,666 recorded renders by the no-training decision, with no reading | [separation results](separation-step01-results.md) |
| 2026-10-20 | Direct model gate 1 (zero renders): stem quality moves D_existing's answers far beyond the leak-draw null (+0.104 [+0.090, +0.120]) and Mega-53's stem costs +0.104 of E against the training stem (0.167 → 0.270), so GATE1 STEM: the separator route continues. The model leans on the stem (share 0.70); behind a clean or real separated stem the mix adds little or nothing (post hoc), so a stem-only model is recommended (user's decision) | [gate 1 results](direct-model-stems-gate1-results.md) |
| 2026-10-20 | Pan side as a separation hint (zero renders, synthetic pans of stage F, audited): with the side known, Mega-53's stereo stem gains +1.50 [+0.78, +2.33] (target's channel, ±0.6) and +1.35 [+0.31, +2.49] (MDX23C centre model, centred lead against hard-L/R rhythms) over its mid; ILD mask +0.6 to +0.8, Wiener on top no help (LSD +7 to +8); no gated cell reaches +2 dB, a gain to build on. Blind side picks follow the louder other guitars (right 5/19, 4/19, 0/19) and lose. The side must come from the arrangement or the user's ear; a product question | [pan screen](stereo-side-results.md) |
| 2026-10-20 | Coherence mask (stereo-side amendment 1; zero renders, audited): per-bin inter-channel phase coherence on Mega-53's stereo stem gains only +0.35 [+0.15, +0.59] on a centred lead against hard-L/R rhythms (+0.56 even on the class-perfect stem), below the ILD mask (+0.76) and the centre model (+1.35); with the ILD mask +0.69. It barely changes tone. Not pursued | [pan screen](stereo-side-results.md#amendment-1-the-inter-channel-coherence-mask-2026-10-20) |
| 2026-10-21 | X-LANCE screen (zero renders, CPU, audited): on the 164 audit mixes the denoise → gtr_mss chain ties Mega-53 fast on SNR (+0.14 [−0.11, +0.39]) and is better on mel-range LSD (−1.82 [−3.09, −0.54]) at 1.78× the CPU time: PASS, OVER BUDGET. [Amendment 1](xlance-screen-plan.md#amendment-1-gtr_mss-alone-on-the-audit-mixes-2026-10-21) (reviewed), gtr_mss alone: SNR +0.14 [−0.11, +0.39], mel-range LSD −2.30 [−3.00, −1.59], 1.01× CPU: passes the CPU legs, pending MPS timing after the pilot frees the GPU. Stage F failures shared by both (She's Gone, Colour Me Red ×2), so Mega-53 stays the fallback and the rest build stays on Mega-53 until the MPS check | [X-LANCE screen](xlance-screen-results.md) |
| 2026-10-21 | Direct model pilot (no judged renders): PILOT STEM. The stem-only D_stem beats the old recipe D0 on R_out (−0.0127 [−0.0216, −0.0039]) and D_mix (R_in +0.0223 for D_mix), and its augmentations help (−0.0115). But all pilot models are worse than a per-class constant predictor (D_stem +0.0128 [−0.0013, +0.0269], R_in). Amendment 4's learning curve: −0.017 per doubling on average (seeds about −0.028 and −0.006), projected −0.020 [−0.047, +0.007] at 20,311, likely optimistic given part C's flattening (capped −0.004; the seeds split), so PROBE CONTINUE, with step 3's MODEL STOP a real risk. Parity passed under post-hoc amendment 3; X-LANCE gtr_mss 0.988× on MPS (switch awaits the user) | [pilot results](direct-model-stems-pilot-results.md) |
| 2026-10-21 | Direct model amendment 2 in force (user): X-LANCE gtr_mss replaces Mega-53 fast for the full build (the rest, plus a re-separation of the pilot and V_sep, about 19–22 h), step 3's D_stem and R_in, and step 4's stems (D and D0 alike). R_out stays htdemucs, and the pilot's STEM verdict (read on Mega-53) carries. Mega-53 stays the fallback; stage F's three X-LANCE failure parts are listed in step 4's report | [plan, amendment 2](direct-model-stems-plan.md#amendment-2-in-force-2026-10-21) |
| 2026-10-21 | Every control (user): the generated preset must cover every setting the plugin exposes (the pack manifests), including the pedals (compressor, both drives), EQ, time effects (doubler and spring included), noise gate, room mics, pan, phase, output gain, the amp choice and every other manifest control; not only input gain, the amp's knobs and the mics. Exceptions come from the manifests, not from this decision (e.g. the room mic types have no control in the plugin's UI). The knob values of a switched-off feature all count as one setting (an off pedal at level min or max is the same setting), so training losses and knob scores must not count them as different; how is for the ML session to propose. Plans already declared (part C's E, the direct model's step 3) keep their definitions until amended. Both active routes set only `knob_ceiling.space` today, on Morgan only; the ML session is to propose how and when each covers every control | [ML plan](research/ml-plan-2026-10.md), sections 1, 4 (step 3) and 5 |
| 2026-10-21 | For a part documented as fully clean, `generate` turns the SW50R and AC20 clean starts down (`sw50rVolume` 15, `ac20Volume` 10): heard clean on the chord riff; closeness to records untested (user agreed) | [results](clean-start-breakup-results.md) |
| 2026-10-22 | Direct model, step 3 (user; amendments 5 and 6, declared before any step 3 data): the answer is each knob's mixture median, averaged over 3 seeds × 2 halves and pulled toward the per-class constant (b fitted on the early-stopping set); the right cab's silent knobs leave E; the E check is descriptive (it replaces MODEL OK/STOP). A sound-based gate decides step 3: D's preset against the constant's, each rendered and judged against the true preset on R_in (about 5.9k renders); step 4 runs only on GATE OK. Coverage of every control (2026-10-21) is the next planning item for both routes, proposed after step 3's result | [plan, amendments 5 and 6](direct-model-stems-plan.md#amendment-5-2026-10-21-the-readout-e-rewards) |
| 2026-10-22 | Direct model amendment 7 (user): the sound gate read GATE STOP (log d D − constant −0.1538 [−0.3360, +0.0284], 4 bands; audited correct, power about 46%; D − D0 −0.1266 [−0.1864, −0.0669]). Adopt any improvement, underpowered is not failed: step 4 runs anyway with its design, rule and early stops unchanged, every output labelled "run under a user override of a GATE STOP" | [plan, amendment 7](direct-model-stems-plan.md#amendment-7-2026-10-22-step-4-runs-despite-gate-stop-user-override) |
| 2026-10-22 | Direct model steps 3 and 4 (step 4 run under a user override of a GATE STOP): STEP4 NOT SHOWN. D − S on stage F −0.034 [−0.103, +0.034] (12 bands, 5 better, 7 worse; clean −0.071, crunch +0.016; power about 21% for that effect). D − D_existing −0.067 [−0.113, −0.021] (16/21 parts, mostly crunch); D − H −0.006 [−0.062, +0.050], D − M +0.011 [−0.040, +0.062]: indistinguishable from arm A's search (about 55 renders per direction) at zero renders, not shown equivalence; D − D0 −0.006. 321 renders, all checks passed. Next as the user decides: every control (#266), real mixes (#267), more bands | [results](direct-model-stems-results.md) |
| 2026-10-22 | By ear on 13 clean development parts (blind, one listener): keep AC20's turned-down clean start (9 of 12; 4 of 7 without bleed), revert SW50R's (5 of 11), no PR12 change (10 of 13 can't tell) | [results](clean-start-volume-listening-results.md) |
| 2026-10-22 | Every control, first stages (user): the coverage plan's stages 0 and 1 go ahead; a switched-off feature's knobs are left out of every loss, score and fit, with neutral values only where a value must be written (a saved preset, a search's canonical form). Whether a declared rule counts as setting a control the judge can't hear stays open; stage 0's screen informs it | [plan](every-control-plan.md) |
| 2026-10-22 | Every control is learned (user): no fixed rule stands in for a control the judge can't hear; the stage 0 screen only sets search and training priorities; switched-off knobs stay ignored. A data-quality audit starts (the user suspects the datasets need cleaning); stage 0 can run, stage 1's long runs wait for its first findings | [plan, amendment 1](every-control-plan.md#amendment-1-2026-10-22-every-control-is-learned) |
| 2026-10-22 | Real-mix test plan approved and merged (user): arm A on each part's released mix against its unity sum (same takes), about 5.8k renders; the direct model joins too (user, amendment 1: it first read "only on `GATE OK`"). It runs after the cleaning. *Since 2026-10-23: on V-real's parts (set by the ML session; the user may overrule)* | [plan](real-mix-test-plan.md), #267 |
| 2026-10-22 | Trusted data only (user): "use only what we can trust, no dirty tracks". Measurements, training, tests and listening pages use a reviewed trusted set; dirty tracks are excluded, not flagged. The user's listening is the authority for trust: the verdicts on the data-review page (amp and mic tracks, suspected doubles, DIs) define the set; rule-based measures only name candidates for that review. Supersedes the 2026-10-17 bleed decision | [ML plan](research/ml-plan-2026-10.md), section 5 |
| 2026-10-22 | Data-quality audit (zero renders): separated stems carry a median 45% of power above the matched render, and within each band the most contaminated third scores worse on the sound gate (+0.103 [+0.055, +0.156]); doubles stay in the training backings and the stored leak check misses them; DIs are clean; labels are exact renders; bleed sits in the live-room amp and mic tracks (trial 47, Sculptor's Request GTR 1: bleed, not a wrong DI) | [audit](data-quality-audit.md) |
| 2026-10-22 | Cleaning: #273 recommends rebuilding the affected examples without the offending backing tracks, not dropping them (dropping would cost a quarter to a half of D's margin from size alone). Reviewed (go, with changes); the user chose "the best approach"; implementation in progress. Zero-render checks, then a paired R_in rebuild read (no training), then the pool rebuild (about 4k renders and 3.6k separations; at most about 13.8k and 13.4k if the live-room tracks count) and 2 training seeds (about 2.5 GPU h) | [PR #273](https://github.com/YoavBZ/neuraldsp-preset-generator/pull/273), in progress |
| 2026-10-22 | Every control, stage 0 (94 renders): amp choice against a blind pick, band-weighted −0.048 (declared), part-weighted −0.044 [−0.062, −0.026] (22/24 parts, 13/14 bands; high priority); no screened control invisible to the judge, cab phase largest; Tone King's renderer repeats its stored scores. Stage 1 waits for the trusted amp-track list from the user's review (not the rebuild) and runs on trusted parts only | [results](every-control-stage0-results.md) |
| 2026-10-22 | Data cleaning for the direct model (user): use only what we can trust, no dirty tracks; go with the rebuild route after review (an independent review: go with changes, all applied). Untrusted backing tracks (another take of the target's part, confirmed by pitch, or a session-level take of the part at or above −30 dB of its own track) leave each section's backing; examples are rebuilt, not dropped. Step 0 (zero renders, injection-checked) and step 1 (a paired R_in rebuild read on step 3's model, zero renders) are built; step 2 retrains D_stem on the rebuilt trusted pool | [plan](data-cleaning-options.md) |
| 2026-10-23 | Cleaning (user): "Let's only keep clean ones for now"; examples with any flagged take or bleed stay out of training and the trusted test set; the rebuilt guitar doubles count as clean; Kimock and Swatkins stay out of the trusted R_in for now; not-loud bleed returns only if data size forces it | [decision](data-cleaning-options.md#the-users-decision-2026-10-23) |
| 2026-10-23 | Trusted-data plan approved (user: "Sounds good"): self-built mixes for training and development, V-real as the final development test, the ear last; every measured verification fail is excluded (amends ML plan §5); T0–T2 run (about 16–23k renders, 8.8k separations, about 2 h of training), T3 decided after T2; a tie at T2 picks the self-built set. Set by the ML session, the user may overrule: Kimock and Swatkins stay out of K, stage F shrinks to V-real, other guitars are DI renders only, controlled bleed is off, and the plan's amendments apply (the cleaning plan's step 2 becomes T2's SES arm, every-control stage 2D becomes T3, read on K and V-real, and the real-mix test runs on V-real's parts) | [plan](trusted-data-strategy-plan.md#recorded-decisions-user-2026-10-23), #280 |
| 2026-10-23 | Trusted data, T0–T2 code (reviewed and re-reviewed, fixes applied; nothing run): the verification standard (A2 keeps the plan's 12 dB pass, 3.3–12 dB to the ear; 11 known amps re-derived from the target-vs-DI measurements, less the pairs whose DI the ear rejected), a processed-DI check on the user's sitting-1 DI verdicts (30/35 in-sample, 26/35 leave-one-out; never decides an unheard DI alone), T0's lists, ear queue and re-reads, T1 and T2. A zero-render dry run: Eggy's DIs heard processed (SYN-E cannot run), V-real 11 parts in 7 bands pending the ear, an ear queue of 195 items before K and T2 can run. *T0 ran later the same day (step 0)* | [design](trusted-data-t0-design.md) |
| 2026-10-23 | New sources (user): Blue Manic "Acomatay" (Cambridge-MT, 5 DI + amp pairs, 20.2 min of DI) downloaded as a reserved test band (ledger `cambridge-new-test-band-bluemanic`; the user's test-first rule for new Telefunken DI + amp bands, applied by the ML session); EGDB's 240 DI clips (107.5 min) downloaded for training only, and only once its DIs pass the DI checks; GOAT's access requested on Zenodo by the user. Downloads through the user's browser at their request (user: never use Chrome without explicit approval) | [inventory](research/di-source-inventory-2026-10.md) |
| 2026-10-23 | The review before the ear (requested by the user; set by the ML session, no user decision in it): two multi-agent reviews, of the trusted-data change and of the whole program (11 reviewers, each finding checked by a skeptic: 73 confirmed, 23 plausible, 6 refuted). Fixed in code before the ear, zero renders: the ear's import keeps earlier exports and needs the sitting-1 export; an "unsure" answer no longer clears a DI; a DI waits while a flagged window is unheard; other guitars no longer sit 3 dB low against the stems; same-part doubles take the target's settings in SYN and K; a refused T2 example no longer blocks training; a re-plan cannot reuse stale renders; the T2 reading waits for complete renders; every-control readings decide on the declared band-weighted interval. Restated: T2's power at 7 bands (about ±0.036); the step 3 gate on trusted rows (about −0.016, 2 bands); the flat 5k-to-20k curve. The open decisions above list what is the user's | [record](research/program-review-2026-10-23.md) |
| 2026-10-24 | The review's four decisions before the ear (user, each as the ML session recommended): Quicksand ElecGtr2 and Today's The Day ElecGtr07 stay excluded on their measured fails (sitting 1 judged their DI clips, not these targets); the plan's by-ear stem spot-check joins this sitting (one backing-track clip per scanned session, the passing stem nearest the floor; a session's stems are used once it is heard clean, and a guitar heard holds them all); every DI is heard before it counts (a window heard clean, or its pair heard as an amp take); the song-blind per-class constant is one more V-real arm at T2 (about 66 renders per arm; about 231 with SES, SYN and 33 priming), read beside the primary | [design](trusted-data-t0-design.md#the-users-decisions-2026-10-24) |
| 2026-10-24 | PR #286 verified on this machine (its 10-step checklist; all passed) and fixed after an independent review: on one ear-page card the latest touch across all exports stands, and a card never touched in a browser holds no answer (an export from another browser could have erased answers); a target's measure DI is heard first too (6 `di_unheard` cards, part 6); stems fold once by channel count; notes on retired cards are kept; `check --retire` never retires an answered card. The ear pages are parts 1–6, 202 live cards (rebuilt to 4 parts in the row below) | [design](trusted-data-t0-design.md) |
| 2026-10-24 | User decisions (ML session): Cnoc An Tursa stays out of K (a side check at most); SYN-E dropped from T2 until a clean-class DI source passes the checks. The ear pages were rebuilt to the 202 live cards (4 parts, nothing to skip; old pages kept in `old-v1/`); Blue Manic's mix preview downloaded | [design](trusted-data-t0-design.md) |
| 2026-10-25 | New sources (user): five Cambridge-MT sessions downloaded and recorded as **training** bands before any audio was opened (ledger `cambridge-new-training-bands-2026-10-25`; `clean_di.TRAINING_DOWNLOADS`): Ember Rev, Empty Signifier, Goran Levi, Mòpia, Sören, 9 electric DIs. T0's checks: D2 passes 4 of 9 (Ember Rev clipped, Empty Signifier ElecGtr1DI hum, Sören gated or edited); Goran Levi's amp track is a processed copy, not a miked amp; Mòpia is a scope worry (D4 flags both DIs). The user's ear page (part6, 16 cards) is pending | [inventory](research/di-source-inventory-2026-10.md#cambridge-mt-newer-host-listing-2026-10-25) |
| 2026-10-25 | T0's ear done (the user heard all 202 cards; one `lists` run with the sitting-1 export): targets 17 verified, 42 excluded; DIs 46 verified, 13 excluded; V-real 10 parts in 7 bands (3 clean parts in 2 bands); knob ceiling 2's 7 parts verified; T1's K is Adam Buckley and Dark Ride (Kimock's and Swatkins' 4 DIs all heard processed); training 27 DIs in 8 bands, 181 sections, only 1 clean-class and 1 crunch; stems 167 usable in 14 sessions, 5 sessions held. Let's Dance ElecGtr4 (user, 2026-10-24): the leak is in the DI, the target is excluded and the DI is not clean. Open before T3 (user): clean-style DIs from new sources. T1 started the same day | [outcome](trusted-data-t0-design.md#t0-outcome-2026-10-25) |
| 2026-10-25 | Backings and spot-checks never use click, metronome or talkback tracks (`NON_MUSICAL` in `verify_tracks`, PR #289): Split Brow's BAND CLICK had passed the stem scan; usable stems 167 → 166, nothing else moved | [design](trusted-data-t0-design.md) |
| 2026-10-25 | T1 audited: K − V_sep +1.63 dB rested on a 1-df band interval (section-clustered [−0.31, +3.56]); 63 examples missing other guitars carried about +1.2 dB (without them +0.42, [−0.89, +1.72]), and near-silent renders were lifted up to +43 dB. No cleaning gain established; no realism lever follows. Fixed (zero renders): an active guitar that cannot be rendered leaves its example out of every arm, a render below −50 LUFS refuses its example, under 3 bands the section-clustered interval is primary. Re-read: the rule leaves out all 812 (parts with no DI play everywhere); on parts with a DI only, 452 read +1.67 [−0.15, +3.49]. T2 under the rule: 3,955 candidates in 3 bands; a user decision before T1 or T2 runs again | [design](trusted-data-t0-design.md#t1-audited-2026-10-25) |
| 2026-10-25 | User decision (in chat, "Sounds good, go ahead" to the ML session's option 1): in self-built mixes an active guitar that cannot be rendered is the session's own recorded amp track(s), at the session's balance, after an automatic leakage check (other-instrument bleed under −30 dB by the cleaning plan's take estimator, read once per session from non-guitar tracks only; a source it cannot be trusted on fails the track; no listening), else the example is left out; examples with more active guitars than the cap of 4 are left out too; only K's and SYN's backings change. After the independent review's fixes, dry run: every amp track fails as unmeasurable; T1 keeps 0 of 812; T2 keeps 5,154 candidates in 4 bands outside early stopping (pilot reachable, narrowly). T1 must be re-planned and re-run before T2 (K's mixes change); as it stands it holds no example | [design](trusted-data-t0-design.md#rule-1-after-the-users-decision-2026-10-25) |
| 2026-10-25 | User (in chat), asked whether T2 should run on 4 bands without amp tracks after the reviewed bleed check (PR #290) cleared none of the 23: "I prefer reliable data and additional/longer runs than data that can't be fully trusted". T2 started at 17:54 on 5,154 candidates in 4 bands (pilot 5,000, no amp tracks; Rebuild The Evil and The Long Wait drop out). Following from that answer, T1's re-run is waived, not passed: K is empty under the reviewed rules, so T2 reads no E on K, and K and the T3/T4 sound gate stay open. The ML session's proposal, approved after review: the realism question is read inside T2 (primary SYN − SES on V-real, plus a zero-render T2-side stem read, a ceiling check at best); the data gap (left-out dense sections) is read by two zero-cost diagnostics declared now, and an SES arm with the dense sections is pending the user's OK; a leakage measure that resolves sparse sources is built after T2 if they show the gap matters, or when T3/T4 needs K | [design](trusted-data-t0-design.md#t1-waived-and-the-realism-check-moved-into-t2-2026-10-25) |
| 2026-10-25 | Option (c) approved by the user (in chat, "Approved if you suggest following this approach", after the ML session suggested it): the SES-ALL arm, SES's recipe, seeds (20261042, 20261043) and early-stopping set on a 5k draw (seed 20261104, stratified by band) from every T2 candidate before rule 1 and the cap, read as SES-ALL − SES on V-real; 2 runs of about 1.5 h, about 60 V-real renders plus 30 priming, no separations; run after T2's chain, adding to its records. Built the same day before any T2 result, with the T2-side stem read (section-clustered primary; a ceiling check, never a realism certificate), diagnostic (a) (V-real split at 5 or more playing guitars, a median split of the parts' counts) and the `report` fix (T1's 812-example read labelled superseded). Diagnostic (b), read: left-out candidates are denser (mean 3.82 playing guitars against 2.90 kept), mostly Rebuild The Evil | [design](trusted-data-t0-design.md#t2s-additions-as-built-2026-10-25) |
| 2026-10-26 | New sources (user): 13 Cambridge-MT metal and hard-rock sessions (7 bands) recorded as **training** sessions before any audio was extracted (ledger `cambridge-new-training-bands-2026-10-26`; `clean_di.TRAINING_DOWNLOADS`, pending until a verified list admits a DI). High gain may train; parts heard as too heavy stay out; tests stay clean to crunch. Acoustic DIs and MIDI renders are not DI rows (`INTAKE_NOT_DI`) | [inventory](research/di-source-inventory-2026-10.md#metal-and-hard-rock-training-intake-2026-10-26) |
| 2026-10-26 | T2 read (audited; every row recomputed from the V-real groups). Primary SYN − SES on V-real +0.019 [−0.001, +0.040], 7 bands: a tie, so SYN is picked by recorded decision 4; SYN leans worse (5 of 7 bands; leave-one-band-out +0.013 to +0.026). SES − constant −0.031, SYN − constant −0.012; against S, SES +0.012, SYN +0.031: neither arm beats S or clearly beats the constant. Follow-up, descriptive: SES-ALL − SES −0.026 [−0.070, +0.018], a broader draw (2 more bands, one band carries it), not a density test; diagnostic (a) shows nothing; the stem read finds SYN's stems not cleaner than SES's (a ceiling check only). Decision 5, T3 on a tie, is open for the user | [design](trusted-data-t0-design.md#t2-outcome-2026-10-26) |
| 2026-10-26 | Parts 5 and 6 heard (user), read by `verify_tracks lists` (code, no hand edits). Window re-check: all 22 cards clean amp. It Was My Fault ElecGtr1 and Nosso Mundo ElecGtr03 are recovered, each on its re-check windows only, with its crop re-cut to a heard window. Signs ElecGtr6 stays pending: those cards never judged its DI, so part 8 (3 DI cards) asks. Targets are now 19 verified, 1 pending, 39 excluded. Signs ElecGtr6 checked: not a copy of its DI. The other three stay excluded; their answers are informative only. New bands: **1 new training DI from 5 bands** (Empty Signifier 20_ElecGtr2DI, heard clean, a high-gain part; its DI-and-amp pairing was never heard); Mòpia ×2 and Goran Levi heard processed. V-real (10) and knob ceiling 2 (7) unchanged | [outcome](trusted-data-t0-design.md#parts-5-and-6-heard-2026-10-26) |
| 2026-10-26 | Scope refined for training (user): high-gain songs can train, as long as too-heavy songs don't interfere; testing and perfecting stay clean/crunch-focused. High gain no longer drops a training source ("scope by ear" screens out only extreme cases); readouts stay clean/crunch-weighted and per class. The 2026-10-25 scan's metal sessions outside the held-out sets, 11 sessions from 6 bands (V.M.GY is set-3 held out), plus DGX ×2, become possible training candidates. With the user's yes, these 13 were downloaded on 2026-10-26 and are under intake on branch `ml/metal-intake` | [scope](#scope-user-decision-2026-10-10) |
| 2026-10-26 | Decision 5 (user): T3 goes ahead on T2's tie. T3's plan declared the same day, before any T3 data (every-control amendment 2 and the T3 design; ledger `trusted-data-t3`; pending review, nothing run): 115 Morgan controls learned, switched-off knobs masked out of loss, scores and fits; F5 (T2's examples with full-space labels against a today's-space model on the same examples, the gate) then F20 (20k, high-gain sources at most 50%); primary D_F20 − S on V-real (up to 12 parts), band-weighted, 90% band-clustered, per class; a shared, larger fit set and no-pull rows fix T2's pull caveat; about 58k renders, 22k separations, 5–6 h MPS. Open: clean and crunch sources for F20 | [design](trusted-data-t0-design.md#t3-declared-2026-10-26-nothing-run) |
| 2026-10-26 | T3's F5 read (audited; every row recomputed). The gate D_F5 − D_core5 +0.079 [−0.065, +0.224], 2 bands better and 5 worse: not shown, so F5 stops and F20 runs only with the user's yes. One part (Colour Me Red ElecGtr03, +1.015) drives it through the time effects and spring, whose heads learn nothing (FS5 switch AUCs 0.49–0.56; reverb read on in 54 of 66 directions); with that family at S the gate is −0.0075 (a post-hoc re-read, not declared; interval holds 0). D_F5 − S +0.088, D_core5 − S +0.009, D_F5 − constant −0.004; the amp head is near chance. Integrity checks passed; 785 of 4,974 full twins dropped as near-silent; 6,246 renders. Output gain is set by loudness matching, not predicted (user). Proposed next: a zero-render readability check, about 70 renders with unreadable controls at S, then F20's decision | [outcome](trusted-data-t0-design.md#f5-outcome-2026-10-26) |
| 2026-10-26 | F5 follow-up approved (user) and declared before any of it ran (ledger `trusted-data-t3` amendment 1): R0, each D_F5 head's readability on FS5 against the constant (AUC, E, accuracy; readable when its 90% interval excludes chance; zero renders); R1, D_F5 with every unreadable head at S against D_core5 on V-real-11 (99 renders), post hoc and descriptive; F20's fixes declared (redraw near-silent draws, one device per pair, unreadable heads at S instead of their prior). Writing S for an unreadable control may conflict with amendment 1: the user's call. R0 read: 20 of 116 heads readable on FS5 (5 of 85 knobs, 14 of 28 switches, the amp choice, no mic) | [design](trusted-data-t0-design.md#f5-follow-up-readability-r0-and-the-unreadable-controls-at-s-r1-declared-2026-10-26) |
| 2026-10-26 | Parts 7a, 7b, 8 and 9 heard (user), read by `verify_tracks lists` with every export (code, no hand edits; `t0/` backed up first; the runs waited for T3's R1, whose plan holds the lists' hash). Part 8: Signs ElecGtr6's measure DI heard clean on all 3 windows, so Signs is verified on all 5 re-check windows; targets 20 verified, 0 pending, 39 excluded. T3's frozen membership stays V-real-11; a future plan would see V-real-12. Metal intake: tone cards 5 too heavy (Daimon B "Broken Again", Dark Illusion "Evil Bones", Inhumanity Vortex "Cybermod", Serapis ×2: all 30 of their DIs out) and 5 high gain; DI cards 76 clean, 1 processed, 1 unsure (both in too-heavy sessions). **50 of 89 metal DIs admitted, every one high gain** (DGX's 11 by the DI-only rule). Part 9: all 13 Strobe/MekaPhil DIs heard clean and admitted; every style question left blank (the user: style can't be judged from a DI), so they counted as high gain under the merged rule (changed 2026-10-27, PR #306: 11 "unknown", out of the high-gain cap; Timeless Part 2's 2 clean). Intake 64 admitted, 52 excluded, 0 pending. An F20 pool would be about 96.2–96.3% high gain with "unknown" left out, or 96.6–96.7% with "unknown" counted as high gain (the worst case), against 96% of today's 181 sections; the clean/crunch shortage is nearly unchanged. DI inventory not rebuilt (no training draw is planned) | [outcome](trusted-data-t0-design.md#parts-7a-7b-8-and-9-heard-2026-10-26) |
| 2026-10-27 | Part 9's DI-only DIs with no style or song tone are "unknown" (user): their own T3 gain group, left out of the high-gain cap's sums, and at most 25% of F20's draws (a design constant the user may overrule). `plan` prints the high-gain share both ways. A song's amp track heard alone sets its DI-only DIs' class: Timeless Part 2's 2 DIs become clean at the next `lists` run. The other Strobe/MekaPhil songs are DI only. DGX and the metal sessions keep high gain. A per-song mix page was built and dropped as a worse repeat | [design](trusted-data-t0-design.md#part-9s-di-only-dis-unknown-or-the-songs-tone-2026-10-27) |
| 2026-10-27 | `lists` re-run after PR #306 (01:17, code, no hand edits): Timeless Part 2's 2 DIs read clean from its amp track's tone. The admitted intake DIs are 51 high gain, 11 unknown and 2 clean; T0's targets, DIs, V-real and stems unchanged | [design](trusted-data-t0-design.md#part-9s-di-only-dis-unknown-or-the-songs-tone-2026-10-27) |
| 2026-10-27 | R1 read (post hoc, descriptive; audited, every row recomputed; 99 renders): D_F5 with its 96 unreadable heads at S − D_core5 +0.062 [−0.080, +0.204], 4/3 bands, crunch −0.013; against S +0.071, against the constant −0.022, against D_F5 with time effects and spring at S +0.070. The delay's switch (AUC 0.557, lower bound 0.505) stays on in 29 of 66 directions and Colour Me Red ElecGtr03 drives it again, +0.846 against D_core5 (+0.949 against D_F5 with time effects at S, the better evidence that delay is the cause); "delay is the cause" is the best fit, not proven. The user (the amendment 1 question): R1 is a measurement only; writing S for unreadable controls is not adopted as the method | [R1 outcome](trusted-data-t0-design.md#r1-outcome-2026-10-27-99-renders-post-hoc-and-descriptive-audited) |
| 2026-10-27 | Tone-information probe (approved by the user; declared first; zero renders; ledger `trusted-data-t3` amendment 2): a linear probe reads 86 of 116 heads from the target render, 30 from the self-built mix, 20 from the X-LANCE stem. The separator does not recover what the mix masks (a 66-head gap); level, finer features and the DI explain none of it. Faint labels explain part of the delay's weakness only | [probe](tone-info-probe.md) |
| 2026-10-27 | Plan brought up to date: next, in order, (a0) a zero-cost linear probe on mix plus stem, (a) a mix-aware input (no new training renders), (b) an X-LANCE fine-tune on the self-built mixes (pending the user's yes), (c) audibility-aware time-effect labels, (d) F20 (waits for the user's yes); the open decisions in one list | [step 0](#next-in-order) |
| 2026-10-27 | The user said yes to all four next steps (in chat, "Yes for all"): (a) D_F5mix, (b) the X-LANCE fine-tune, (c) the audibility measurement, (d) F20. (a) ran the same day and was audited: the mix input is not shown better and leans worse (D_F5mix − D_F5-noaug +0.059 [−0.012, +0.130]), best fit, not proven: the second drive pedal's switch on real songs; the stem stays. (b) and (c) are declared and reviewed before they run; (c)'s relabelling waits for the user's three rulings; F20's plan waits for (b) | [outcome](trusted-data-t0-design.md#d_f5mix-outcome-2026-10-27-165-renders-audited) |
| 2026-10-27 | Audibility measurement (ROADMAP (c)), the fresh run audited: 23–59% of "on" effects sit below τ in the mix; delay reads better from the mix as A_e rises, mixed with effect size; tremolo reads weakly at every level; A_e measures the judge's render-to-mix sensitivity, not audibility as such; the doubler also runs on across renders (joins the V-real caution). The ear page went to the user; nothing relabelled | [outcome](trusted-data-t0-design.md#audibility-outcome-2026-10-27-fresh-run-2686-renders-audited) |
| 2026-10-27 | The user's direction (in chat): sound-alike presets are acceptable; barely audible effects barely matter; effects might later be adjusted from the song research. Read as a sliding audibility weight for (c)'s relabel (declared and reviewed before it runs). A second ear page with exposed-guitar pairs was added beside the dense one (zero renders, PR #319) | [(c)](#next-in-order) |
| 2026-10-28 | X-LANCE fine-tune (ROADMAP (b)) outcome, audited: D_F5ft − D_F5-noaug +0.078 [−0.025, +0.181] on V-real, not shown, leans worse; the fine-tune mostly shrank its output (F5 median about 12 dB under the target guitar, −14 to −6 dB in three bands; Ale Lak's stems louder than the target but still worse than silence), so its +5.2 dB over the stock stem is not separation; tone probe 22 against the stock stem's 20 (per head the stock stem is reliably better on 5, the fine-tuned on 3). Not adopted; F20 keeps the stock stem; the route is not judged | [outcome](trusted-data-t0-design.md#d_f5ft-outcome-2026-10-28-99-renders-audited) |
| 2026-10-28 | Clean/crunch-led pool (user: "Yes for all", after an independent review and a re-check): the trusted pool (T2/F5/FS5) is 4 heavy bands with no clean or crunch song, because stage F's 12 bands are kept out of the pool (7 are V-real), the other usable bands' DIs were heard processed or fail D2, and cleaning, rule 1 and the cap removed the rest. Decisions: A Adam Buckley trains (leaves K); B release sets 1–2's held-out Cambridge sessions, set 3's Dunning Kruger and Silona, and set 5's Hazael and Peter White into training (never tests again); C re-download set 5's backings; D heavy at most 20%, no high-gain sections (Death Of A Romantic and Hollow Ground out); E the ear sittings; F step 3's training. The leak rule becomes per example, replaced guitars only, session-level readings. V-real-11 stays the test. F20 re-planned after step 3 | [plan](clean-crunch-pool-plan.md) |
| 2026-10-29 | D_F5bk outcome, audited (clean/crunch pool step 3, the backing fix alone: F5's examples remixed under the per-example leak rule after the ear heard no guitar in its 5 backings): D_F5bk − D_F5 −0.008 [−0.076, +0.061] on V-real-11, 4 of 7 bands better, undecided; femme +0.157 and let-s-dance −0.162 cancel, the other 5 bands within ±0.03; co-primary (time effects and spring at S) −0.018 [−0.088, +0.051]; still behind S (+0.080). The per-example leak rule was already the pool's recipe (step 1); D_CC is the arm left | [ledger](dev-test-ledger.json) `trusted-data-t3` `amendment_6_outcome`, [plan](clean-crunch-pool-plan.md) |
| 2026-10-29 | The pool's data checks audited (the user's doubt, an independent audit, reviewed fixes in amendment 1, PR #329): the amp-bleed check had passed 0 of 79 amp tracks (three logic bugs in its verdict), D4 overrode heard-clean DIs, step 0's D2 rejected whole DIs for one window, part A's hiss screen flagged about 270 sections. Amendment 1 fixed the bleed verdict, D4 and D2: 89 sections with the bleed check on, 161 (51 clean) with it off, against 38 before. The ear backed the audit: part 14, 22 of 23 rejected items clean; part 15, 15 of 17 D2-rejected DIs clean. User decisions: other instruments' bleed does not rule out a background amp track (target-guitar checks stay); hiss no longer screens sections; both go into amendment 2 | [plan](clean-crunch-pool-plan.md), [ledger](dev-test-ledger.json) `clean-crunch-pool-dcc` |
| 2026-10-28 | Clean/crunch pool progress (zero renders): step 0's intake checks (80 DI rows in 21 sessions; most fail D2), set 5's backings re-downloaded, step 1's per-example leak rule merged (PR #323), step 2's groundwork merged after an independent review and re-check (PR #324): the 19 released sessions pass `refuse_held_out` under their band and are barred from every later test (`refuse_test`, `set3/set5.parts` by default); one pool entry point bars V-real's 7 bands; set-5 parts whose amp tracks are another part's (BKS "Too Much" 4a, "Bulldozer" 6a) are dropped; Fytakyte "Too Much" is spent for testing and never trains. Ear page part 11 (120 cards) sent | [plan](clean-crunch-pool-plan.md) |
| 2026-10-30 | D_CC outcome, audited (clean/crunch pool step 3: 294 sections from 33 target DIs in 9 bands, 50 DIs passed the checks; 17,661 pool renders, 3,034 separations plus 1 redo, 165 V-real renders): D_CC − D_F5 +0.090 [−0.011, +0.191] on V-real-11, 1 band better and 6 worse, undecided and leaning worse (clean +0.015, crunch +0.120); part-weighted (descriptive) +0.090 [+0.006, +0.175], 9 of 11 parts worse; co-primary +0.094 [−0.014, +0.201]; also behind D_core5 (+0.169), S (+0.177) and D_F5's constant (+0.085) (descriptive). No bug; the loss is mostly (post hoc, descriptive) both drives off in all 14 pr12-crunch directions and one part (femme ElecGtr5, +0.363). Confounds: 2,699 + 334 examples against D_F5's 3,467 + 722, a seed whose best epoch was 9 of 14, amp-track stand-ins in 44%. Next: step 4's listening page; per-seed answers, pedals at S with D_CC's own constant, and a size-matched top-up wait for the user | [ledger](dev-test-ledger.json) `clean-crunch-pool-dcc` `outcome`, [plan](clean-crunch-pool-plan.md) |
| 2026-10-30 | Step 4's listening page, audited and sent (clean/crunch pool; ROADMAP (c)'s ear check of tau on clean/crunch mixes): 71 pairs measured with the fresh-process recipe (266 renders, 30 of 30 repeats bit-exact); below tau delay 10 of 22, reverb 8 of 24, tremolo 1 of 10, pr12 spring 7 of 9, sw50r spring 1 of 6; the page holds 25 items (22 pairs, 3 catches), build a04ae2e282a3. Caveats: 13 items from one song, 4 songs in 3 bands. Nothing decided; the answers wait for a declared reader | [ledger](dev-test-ledger.json) `clean-crunch-pool-dcc` `amendment_3_outcome`, [plan](clean-crunch-pool-plan.md) |
| 2026-10-30 | Step 4's answers, audited (read under amendment_3's declared reading, descriptive): 21 same, 4 maybe, none different; all four anchors same, one of 3 catches maybe. The page checked out (all 50 clips rebuilt). Its own checks did not come out, so tau is not placed by ear; nothing suggests switches below tau are audible (the anchors were not heard either, so the sitting cannot show this); the relabel's reader is still unwritten. The delay anchor is a runaway delay (a steady whine, its stored target too); a zero-render scan finds runaway delay targets (mostly feedback 0.75 or more) in about 2% of both pools (D_CC 64 of 3,033 kept: training 58 of 2,699, FS_CC 6 of 334; D_F5 87 of 4,189: F5 70 of 3,467, FS5 17 of 722); one delay-off target per pool is flagged (801570, 356). Excluding them is the author's reading of the trusted-data rule (the labels are correct settings, the audio is not a usable target) and thins high-feedback delay draws; they are refused and redrawn in the next build (F20, to be declared and reviewed in the re-plan); D_CC and D_F5 stand as read, with that caveat. The user is asked to replay items 4, 13 and 17 | [ledger](dev-test-ledger.json) `clean-crunch-pool-dcc` `amendment_3_answers`, [plan](clean-crunch-pool-plan.md) |
| 2026-10-30 | The user said yes (in chat, "Yes for all") to D_CC's two cheap follow-ups and to the ElecGtr8 shift; declared before any run (ledger `amendment_4`, code `cc_readout` followup-*, `cc_build` shift), they run once reviewed: (a) each seed's own answer on V-real-11 (zero renders; drive switches, inputGain and amp head per seed against D_F5's stored per-seed answers); (b) D_CC with its pedals at S and D_CC's own constant (165 renders; four descriptive rows); (c) Forkupines Sugar Faith ElecGtr8's DI read from a copy delayed by 129.83 ms, in the next build only and only if the alignment check on the copy reads about 0 ms. The size-matched top-up stays unplanned | [ledger](dev-test-ledger.json) `clean-crunch-pool-dcc` `amendment_4`, [plan](clean-crunch-pool-plan.md) |
| 2026-10-30 | The user said yes (in chat, "Yes for all") to a drive-pedal listening page. Declared before any render (ledger `amendment_5`, `learn/cc_drive_page.py`): step 4's qualifying examples less the runaway-flagged (43), drive pedal 1 on in 12 and drive pedal 2 in 12 (24 pairs, 19 examples, 5 bands; 11 of the 24 pairs from one song, The Travelling Band's "Quicksand"); step 4's r_on' reused for 14, each checked by a bit-exact repeat; 96 new renders. A new player loops both mixes and switches between A and B at once; at most 21 items (about 10.5 min): at most 14 pedal pairs, 3 catches, step 4's loudest reverb and sw50r spring pairs as checks, and a catch under each check's title. Heard means "They differ" ("Maybe" reported beside). A check heard here but not on step 4's page is consistent with the old format hiding differences, not proof (only the checks carry those titles, it is a second hearing, the listener may know them). The author dropped the separate replay of items 4, 13 and 17 (reported to the user 2026-10-30); item 4 (900215) is a dirty (runaway) example and is not re-used. Descriptive; decides nothing | [ledger](dev-test-ledger.json) `clean-crunch-pool-dcc` `amendment_5`, [plan](clean-crunch-pool-plan.md) |
| 2026-10-30 | D_CC's follow-ups read, audited (ledger `amendment_4`; zero renders for (a), 165 renders for (b)): both seeds' answers turn the pr12-crunch drives off (answers only, not rendered; drive2 on in 2 and 0 of 14 directions; D_F5 12), so seed 20261043 alone is not the cause; drive2 is on in 52.7% of D_CC's pr12-crunch labels and its probability there is 0.42–0.50, so a 0.5 readout turns it off. The sound rows are of the pooled answer: D_CC with its pedals at S − D_CC −0.076 [−0.142, −0.011], all 7 bands better (V-real-10 −0.072); pedals at S in both, D_CC − D_F5 +0.015 [−0.028, +0.057] (undecided): the loss is mostly the pedal answers (with the Wall Of Death band left out, all of it: −0.045 against +0.044). D_CC − its own constant +0.103 [+0.051, +0.155], all 7 bands worse; D_CC's constant − D_F5's −0.018 [−0.057, +0.021] (descriptive). For F20's re-plan: the readout of near-chance switches and beating the constant. The ElecGtr8 shift (c) runs within the next build | [ledger](dev-test-ledger.json) `clean-crunch-pool-dcc` `amendment_4_outcome`, [plan](clean-crunch-pool-plan.md) |
| 2026-10-30 | The drive-pedal page, rendered, audited and sent (ledger `amendment_5`): 96 renders (48 priming), 19 of 19 repeats bit-exact, none refused; median A_e drive pedal 1 0.081, drive pedal 2 0.093, one pair per pedal below tau. 17 items, about 8 min (10 pedal pairs, 3 catches, step 4's loudest reverb and sw50r spring pairs as checks, a catch under each check's title). Caveats: 10 of 17 items from one song ("Quicksand"); in drive pedal 2's loudest pair the guitar sits 5.9 dB lower with the pedal off; the pairs near tau are not physically small. Answers pending; F20's re-plan waits on them | [ledger](dev-test-ledger.json) `clean-crunch-pool-dcc` `amendment_5_outcome`, [plan](clean-crunch-pool-plan.md) |
| 2026-10-30 | The user (in chat): "The mixes make it harder to distinguish, please only the guitars if possible", then "Same for the previous effects listening page". Guitar-only pages declared before any is built (ledger `amendment_6`, `learn/cc_solo_pages.py`, zero renders): part 1, the drive page's 17 items; part 2, step 4's 25 items with its runaway item 4 (900215) replaced by the loudest non-runaway delay pair (803054, A_e 0.447, its reverb on too); each clip the stored render alone (no backing, other guitars, stand-ins or mastering) at −23 LUFS, in the A/B player, new ids, order and A/B draw. The guitar plays in 96–100% of each on clip and 87–100% of each off clip; the solo clips differ more than the mixes did for 12 of 12 part-1 pairs and 21 of 22 part-2 pairs (drive pairs −2.7 to −14.4 dB, step 4's pairs −5.9 to −29.0 dB); the AAC coding error sits 12.4 dB under 801921's reverb pair difference. Heard means "They differ". The answers roughly bound audibility in a song from above, except where the switch changes the guitar's balance in the mix (levelling removes it); against step 4's in-mix answers masking is confounded with the old sequential player and a repeat hearing; they cannot show whether a switch is heard in a song, nor tau. The drive page's in-mix version is not needed now; F20's re-plan waits on these answers. Descriptive; decides nothing | [ledger](dev-test-ledger.json) `clean-crunch-pool-dcc` `amendment_6`, [plan](clean-crunch-pool-plan.md) |
| 2026-10-30 | The guitar-only pages, built, audited and sent (zero renders): part 1, the drive page's 17 items; part 2, step 4's 25 items with 803054 in place of the runaway 900215. All 84 clips rebuilt from the hash-checked stored renders, the guitar alone in each, every clip at −23.00 LUFS, catches byte-identical, the in-mix pages and keys unchanged; smallest AAC margin 23.1 dB (part 1) and 12.4 dB (part 2, 801921's reverb pair). Caveats: back-to-back items on one excerpt in part 2; 800877 (its pair and its catch) and 802682's sw50r spring pair in both parts (800877 with the same A/B order); levelling removes the switch's level drop (801895 5.9 dB). Answers pending; F20's re-plan waits on them | [ledger](dev-test-ledger.json) `clean-crunch-pool-dcc` `amendment_6_outcome`, [plan](clean-crunch-pool-plan.md) |
| 2026-10-30 | The guitar-only pages' answers, audited: catches 8 of 8 "same"; 5 of the 6 distinct checks and anchors heard (not 802682's sw50r spring: its long-term spectrum differs by about 1.1 dB, the heard 803054's by 1.2 dB, so that does not explain the miss); 25 of the 26 pairs near tau not heard (21 same, 4 maybe; the exception 802350's tremolo, A_e 0.0039, solo J 2.30); all 8 near-tau drive pairs and all 8 spring pairs same. The heard pairs are the top solo-J pairs in each part (AUC 1.00; A_e 1.00 and 0.81), but the edge over A_e rests on one item (802350) and no single solo-J cut works across effects. The listener's note: items with several effects are harder ("13 baseline is 12 with tremolo on so its delay is barely noticeable, if any"); 33 of 34 pairs have another effect on in both clips, by design (one effect switched in the full setting, the context the labels need; an isolated-effect page is not planned). Caveats: part 1 answered fast (8 of 16 under one 10-s loop), repeats across the parts, small n. Readings: the format works on the guitar alone; most heard pairs sit well above tau and one below it was heard (802350's tremolo, A_e 0.0039); as declared, this does not place tau. F20's re-plan comes next, for the user's yes, and declares how, if at all, these answers are used. Decides nothing | [ledger](dev-test-ledger.json) `clean-crunch-pool-dcc` `amendment_6_answers`, [plan](clean-crunch-pool-plan.md) |
| 2026-10-31 | The pipeline fix plan run (the user: fix and verify every finding of the pipeline review, each on its own, relying only on parts already verified). Reviewed four times, results audited three times. The model learns the tone from the clean guitar: −0.241 [−0.318, −0.165] against S by sound on 2 held-out songs, also told a wrong amp; by knob every one of 9 bands in a 5-fold new-song test. Two blockers located: any backing erases the skill (the other guitars and the separator add no further loss; more backing variety recovers 27% [13%, 42%]); on V-real's real amp tracks no transfer is detected (+0.153 [+0.039, +0.268] against S, mainly the core tone; real parts' presets sit at the training prior's edges about 3× as often as its labels). Fixed or verified alone: the doubles, early stopping, the class input, the by-sound read. Ruled out as blockers: the network, the pull, the switch readout for a model that reads, mastering for the guitar. About 9,010 renders, about 4 h of MPS. Community presets: recommended as draw centres for the next build, pending the user's yes. Phase 5 (the two blockers' fixes) waits on the user | [plan](pipeline-fix-plan.md) findings log F1–F28, [ledger](dev-test-ledger.json) `pipeline-fix` |
| 2026-10-31 | Pipeline fix phase 5 (the user's "Continue"). Blocker 1: backings from 13 more songs recover about half of the backing's loss on the held-out songs (0.50 [0.29, 0.73], two seeds; 8 backings recovered a quarter). Blocker 2: the stock amp-track bleed check fails bleed-free reamped tracks through its power sum, so the pool's recorded amp tracks were not used; on BKS's reamped tracks (real amps, known playing) the clean-input model is +0.066 [+0.030, +0.102] against S, so part of the real-amp gap is there even with known playing. Re-centred on S, the model's real-amp penalty is gone and its per-track readings lean better (−0.029, undecided). About 2,160 renders, 20 min of MPS. Next: 5B.2, labels that reach real-amp tones | [plan](pipeline-fix-plan.md) F29–F31, [ledger](dev-test-ledger.json) `pipeline-fix` `phase_5a*`, `phase_5b1*` |
| 2026-10-31 | Morgan Amps Suite X and Tone King Imperial MKII X (user-installed, both checked by the user to load the presets these tools write): generated presets also go to the X User folders; Morgan X presets are read as the `morgan` pack, with sections from the file's tree; Tone King X's own layout is not read yet | [installing](../reference/installing.md), 0.7.120 |
