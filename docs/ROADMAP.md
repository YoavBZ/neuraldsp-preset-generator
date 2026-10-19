# Roadmap

The one living plan. Update it when a result lands or a decision changes; the detail
lives in the linked documents. Last updated 2026-10-19.

## Where the product is

- **Input is a song.** The user gives a song (and a time where the guitar plays), never
  a DI of the performance.
- **The goal (user, 2026-10-14):** from a song and its research, generate the most
  accurate preset by setting every control the song needs. Choosing the closest
  factory preset is not the purpose; factory presets are starting points.
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
  by ear (product steps; history in [roadmap-history.md](roadmap-history.md), step 5).
- **`edit`** changes a preset from a plain-English ask.
- **Predicting a preset from the song** is active research, not yet in the product
  (step 0). Since 2026-10-14 the aim is to generate settings, not rank presets: see step 0
  for where it stands. The earlier route had a network rebuild the guitar's DI from the
  recording, then let the judge pick a menu preset through it. Confirmed against the old
  starting points (the clean template, and the driven preset on crunch), mostly on clean parts
  ([results](set4-confirmation-results.md)). Against the current starting presets it is
  undecided on clean and crunch, both under-powered ([audit](audit-2026-10-11.md)).
  Arm A, the current candidate, is not yet shown better than the starting preset on fresh full mixes
  (−0.028 [−0.064, +0.008]; [results](arm-a-mega53-results.md)).
- **The judge** ([measuring-closeness.md](measuring-closeness.md)) is how closeness is
  measured. It needs the DI of the same take, and listening validated it only for clear
  differences between clean-to-crunch PR12 renders
  ([listening validation](listening-validation-results.md)). One listener heard the
  starting presets as closer than what they replaced, in-sample
  ([listening](starting-preset-listening-results.md)).

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

## Next, in order

0. **Song-to-preset model** ([current plan](research/ml-plan-2026-10.md); the earlier
   [plan](di-recovery-plan.md); the Codex continuation is
   reviewed in [codex-continuation-review.md](codex-continuation-review.md)).

   **The direction since 2026-10-14: generate settings, don't rank presets.**
   - **The goal (the user's):** set every control so the preset sounds as close as possible to
     the song. Choosing the nearest factory preset is not the goal.
   - **The knob ceiling ([results](knob-ceiling-results.md)):** by the judge, with the true DI on
     development, a search over the amp knobs, input gain and mics beats the best of the 111
     menu presets by −0.205 cross-half (about 19%, 14/14 bands). The EQ adds −0.079 more.
     - The gain is part-specific, not a generic judge preference: another part's settings are
       +0.229 worse than the menu.
     - In a blind check (one listener, a second sitting of 7 trials), the searched settings
       were chosen on 7 of 7.
     - Both are lower bounds: the search falls short.
   - **So everything below, which ranked the menu, measured the menu's limit, not the
     plugin's.** The work since then follows the [ML plan](research/ml-plan-2026-10.md),
     approved by the user on 2026-10-14. Since 2026-10-16 it has no fixed render limit: each step
     stops rendering by a declared, evidence-based stopping rule (decision 2).

   **Status (2026-10-17): not ready to claim for shipping.**
   - **Arm A on fresh full mixes reads −0.028 [−0.064, +0.008] against S**, against −0.083 on the
     reused development parts it was chosen on ([results](arm-a-mega53-results.md)). It is not
     yet shown better than the starting preset on fresh full mixes.
   - **The rebuild is the main measured bottleneck** ([results](rebuild-gap-results.md);
     development, perfect stem). With a perfect stem the loss is a structured short-time magnitude error, mostly above 2 kHz; phase and
     rotation are minor. A loss aimed at the short-time treble lowered that error with no
     measurable ranking gain; long-term balance fixes lean better, undecided ([results](rebuild-tone-results.md)).
   - **Fresh full mixes are now the only yardstick for progress.** The reused development parts
     are for exploration only.

   **Where the ML plan stands (2026-10-17):**
   - **Done:**
     - step 1, C′ for every fold ([results](cprime-folds-results.md));
     - step 2, knob ceiling 2 on Morgan ([results](knob-ceiling-2-results.md)): pedals add a
       little, and time effects are kept only when they clearly help;
     - step 4, the label table ([results](label-table-results.md)).
   - **How results are read (the user's rules):**
     - no arbitrary pass/fail bars: every comparison is an effect size with a 90% band-clustered
       interval, and any improvement is built on;
     - the best estimate is chosen, with the cheaper option on a tie;
     - controls explain a result, they don't veto it;
     - a weak component (the separator, the rebuild) is a research target, not a reason to drop
       the route;
     - the listener's answers are trusted; layout confounds are caveats;
     - an effect left off is a correct answer on a dry record.
   - **The true-DI ceiling, searched to a stop** ([results](ks-ceiling-extend-results.md)):
     **−0.293 [−0.378, −0.207]** against S, 13/14 bands. It replaces step 3's −0.269 (K_S at 150
     renders) as the reference. The longer search added −0.024 [−0.042, −0.006], mostly in its
     first 150 extra renders and mostly on two clean bands. Still a lower bound.
   - **Step 3, the song-settings comparison** ([results](song-settings-results.md)), against the
     starting preset S:
     - the true-DI search (K_S): −0.269 at 150 renders, −0.293 at the stop;
     - arm A (search through C′'s rebuilt DI): −0.078, 27% of the ceiling;
     - arm B (a settings model): +0.035;
     - arm C: not run.
   - **Arm A's current best** ([levers](arm-a-levers-results.md); adopted by the user on
     2026-10-16):
     - **The recipe:** the rebuilt-DI search stopped after its 52-render main stage, its moves
       shrunk halfway to S, falling back to S if a render is silent.
     - **The result:** −0.083 [−0.135, −0.032], 12/14 bands, 28% of the ceiling; about −0.07
       expected after picking among variants.
     - **How it was chosen:** the declared rule chose the unshrunk 52-render search (−0.085).
       Shrinking halfway was a descriptive extra; the user adopted it as a judgement call (same
       mean, narrower downside), not as the rule's output.
     - **Heard** ([listening](arm-a-listening-results.md), one listener): where a difference was
       heard, arm A was chosen 4 of 4; the smaller changes weren't heard. The first listening
       support for song-only generated settings.
     - **Without bleed** it is a little stronger: −0.094 for the recipe without moderate or high
       bleed ([bleed audit](audits/bleed-2026-10-16/README.md)).
     - **What limits it:** ranking nearby settings around S (below).
     - **On fresh full mixes it reads only −0.028 [−0.064, +0.008]**, 9/12 bands
       ([results](arm-a-mega53-results.md)). Candidate reasons, none settled: selection and reuse
       optimism (new-song parts read +0.018, post hoc, 4 bands), much poorer stems (median SNR 0.43 dB against 2.13),
       and bleed (about a third of the drop). The shrink looks more useful there (unshrunk
       −0.006).
   - **The local objective** ([results](local-objective-results.md)): how well the song-only
     objective ranks nearby settings (cross-half local Spearman; the true DI against the amp track
     gives 0.864, today's objective 0.289).
     - **Experiment 1:** a perfect DI alone (+0.062) or the amp track alone (+0.120) is undecided;
       the two errors partly cancel. Lag and mask are closed. DI-only work against the htdemucs
       stem, including the DAC-9 add-on, is dropped.
     - **1b, a perfect separator** (the amp track feeding the rebuild and the reference): 0.541,
       +0.252 [0.139, 0.365], about 44% of the gap. More than half the gap remains, which is the
       rebuild's own limit. Right around S it is undecided (+0.085).
     - **1c, a real separator (Mega-53) feeding both,** on the instrumental context: 0.398,
       +0.109 [+0.058, +0.160], about 43% [26%, 70%] of 1b's gain. Right around S no gain is
       detected (−0.002 [−0.049, +0.045]), so it doesn't by itself show a song-level gain. Mega-53
       takes about 6× htdemucs's wall-clock time (measured in the song test).
     - **1d, the separator-robust C′ in the rebuild** (htdemucs stem and Mega-53): no gain.
       Against today's objective −0.127 [−0.256, +0.003]; against 1c's Mega-53 cell −0.051
       [−0.166, +0.065]. Keep C′. Its small envelope gain didn't predict ranking, so judge
       rebuild changes on rendered ranking. No arm X in the Mega-53 song test.
   - **Separator-robust C′** ([results](cprime-sep-results.md), zero renders): C′ fine-tuned on
     separator residuals rebuilds the true DI slightly better from the htdemucs stem, inside the
     noise (envelope error −0.24 dB [−0.66, +0.17]; 1–3 kHz coherence +0.003). It gains about as
     much from the amp track, so it can't be credited to stem robustness. Rendered in 1d, it
     ranked no better (above).
   - **Bleed in the amp tracks** ([audit](audits/bleed-2026-10-16/README.md),
     [listening](bleed-listening-results.md)): only the Telefunken live-room sessions carry bleed;
     4 of the 25 knob-ceiling parts read high, and the listener heard it on all 3 high parts tried.
     The model-based cleaning left audible leakage and was heard as changing the guitar's tone a
     little, so it isn't adopted; a stronger route (a real separator on the amp track, or dropping
     high-bleed parts from training records) stays open. Every key result holds without bleed; results keep the
     no-high-bleed row beside the all-parts row. Listening trial 8's noise (Prodigal) is DI hum
     lifted by the measure-DI EQ, not bleed.
   - **Arm B is paused** ([diagnostics](song-to-settings-diagnostics-results.md),
     [sound-space retrain](song-to-settings-soundspace-results.md)): B2 beats the old arm B on
     songs (−0.068 [−0.111, −0.024]) but isn't shown to beat S (−0.033 [−0.100, +0.035]), and input
     gain didn't improve. Arm C isn't run. If arm B is reopened, B2's shuffled-input control comes
     first (about 290 renders).
   - **Earlier DI-recovery findings:** separation halves the rank margin but rarely flips it
     ([screen](separator-screen-results.md)); C′'s error is fine structure
     ([ladder](rank-margin-ladder-results.md)); better fine structure didn't steer better
     ([experiment 4](di-fine-structure-results.md)).
   - **Separation: Mega-53 against htdemucs** ([results](arm-a-mega53-results.md)). On fresh full
     mixes Mega-53 leans better, a tie: −0.017 [−0.039, +0.004], 8/4 bands, at about 6× the
     wall-clock time. On the development parts −0.008 [−0.024, +0.009]. htdemucs stayed the
     default then. A perfect stem gains little on the instrumental development stems (−0.026), but
     separation may matter more on low-SNR full mixes (not measured there): on the 6 development parts below 1 dB SNR a
     perfect stem gains −0.091 (post hoc), and 19 of the 21 fresh full-mix stems are below 1 dB.
     **Since 2026-10-19 Mega-53 is the ML default** (the user heard it as much better on the
     separation samples; htdemucs stays selectable; [stereo and mix check](stereo-and-mix-check-results.md)).
     Stereo: with the target centred, as in all our summed mixes, the mono fold loses nothing. On
     a panned model, the target's own channel gains +1.6 dB (Mega-53), but a blind pan estimate
     from the stem gains only +0.3. No session ships a master, so our in-song guitar is the raw
     track; the gap to real mixed songs is unmeasured.
   - **The rebuild gap** ([results](rebuild-gap-results.md), with a perfect stem, development):
     - **Magnitude, not phase:** the true short-time magnitude recovers the whole gap (+0.313),
       the true phase nothing (−0.031). The treble above 2 kHz carries most of it (+0.241, about
       0.8 of the gap); qualified by the [dose probe](dose-probe-results.md): `high` also restored
       phase, the band above 8 kHz and much of the long-term balance; on top of the leak-free EQ the
       2–8 kHz short-time magnitude on E_st's mask gives about a quarter of the remainder, the full
       band about three quarters. A constant phase rotation costs about 4%; rotation fixes are
       deprioritised.
     - **The costly error is structured**, at time scales between 21-ms frames and the long-term
       spectrum. A fixed long-term EQ (`dep_eq`) leans better, +0.133 [−0.009, +0.276], about
       half the gap at most.
     - **The ranking-trained rebuild (`rank`) leans better:** +0.075 [−0.031, +0.182] against C′,
       +0.104 [−0.005, +0.214] against its control. Post hoc, it looks like a learned long-term EQ: it
       follows `dep_eq` part by part and does not reduce the short-time treble error.
   - **The short-time treble loss** ([results](rebuild-tone-results.md), development, audited;
     8,280 renders):
     - **`stm` lowered its target error clearly, with no measurable ranking gain.** E_st fell −0.54 dB on
       held-out crops and −0.63 dB on all 24 amp tracks (about 8% of C′'s error), but `stm` − C′ is
       +0.012 [−0.023, +0.047], `stm` − its control +0.024 [−0.006, +0.054], and on top of the
       leak-free EQ −0.012 [−0.038, +0.014]. This loss does not capture the stage-R lever.
     - **The long-term levers lean positive and hold up, undecided:** a second seed of
       `rank` +0.099 [−0.036, +0.233] (pooled +0.087 [−0.031, +0.204]); the leak-free EQ
       (`cprime_eq`, curve without the test parts) +0.132 [−0.030, +0.294], reproducing R's
       `dep_eq`. What remains after the EQ is decided: truth − `cprime_eq` +0.157 [+0.083, +0.230].
     - **Reconciled with stage R (post hoc):** the main reading is the plan's: the error this
       network learned to lower is not the one that costs ranking. "Too little of the right
       error" stays open but weakly supported: `stm` cut it by 8%, while the stage-R probes that
       recovered most of the gap cut it by 39–98% (with much of the long-term balance), but their gains
       are not ordered by the cut. No probe yet isolates the short-time component (the dose probe
       since did; below).
   - **Next, in order** (proposed 2026-10-18; plan and review first):
     1. **A short-time oracle dose probe** (renders only, about 1.2k per dose): on top of the
        leak-free EQ, restore 25/50/100% of the true offset-removed short-time magnitude, keeping
        the long-term spectrum and C′'s phase. Does the short-time component carry the remaining
        half of the gap, and how large a cut is needed? If it does, **a bounded per-bin log-gain on
        C′'s own output** (option 2 of the [HF research](research/hf-detail-losses-2026-10.md)),
        gated on reaching that cut. If not, the declared alternatives (a learned Morgan surrogate,
        ranking in the plugin's own terms). The leak-free EQ (near-free) and `rank` are the
        long-term candidates to carry into the decision test.
        - **Planned and reviewed 2026-10-18** ([plan](dose-probe-plan.md)): 3 doses in 2–8 kHz,
          the full-band field with one resynthesis (option 2's direct ceiling) and with
          Griffin–Lim, and a time-shifted control; 7,152 renders, scored as they render. Measured
          before it (zero renders): one resynthesis with C′'s phase caps the E_st cut at about
          half (47% in 2–8 kHz, 52% full band; Griffin–Lim 69%), and a ±12 dB bound costs little.
        - **Stopped 2026-10-18 on its S-vs-warm-up check** (It_Was_My_Fault ElecGtr1, pr12, 0.0171;
          [audit](audits/dose-stop-2026-10-18.md)). A render after a change of plugin state is not clean at its
          start: on this pr12 cell the process's first render is up to 24% louder for about 4 s,
          and the part's quiet opening (−34.5 dB) exposes it. The cause is the plugin and the
          loop order, not the probe's audio, and stored scores are unaffected. Before any re-run,
          [amendment 2](dose-probe-plan.md#amendment-2-2026-10-18-after-the-stop-before-any-re-run)
          adds a priming render at S before every warm-up and a Σ-order repeat check on the stopped
          cell (reviewed; about 7,448 renders at R1 in all, 528 spent before the re-run).
        - **Other pipelines audited 2026-10-18** (code reading, zero renders;
          [audit](audits/start-transient-2026-10-18.md)): no audited merged decision changes; the
          arm B and DI-recovery scripts are not yet audited. Part C is
          exposed (no priming render) but probably below one 0.5-dB step on nearly all examples, so
          it keeps rendering; its direct check (60 renders) waits for a 4th process. New rule: one
          discarded priming render after any process start, amp change or DI change. Part C's
          [amendment 2](pretrain-set-plan.md#amendment-2-2026-10-18-a-bounded-render-server-primed-re-checks-and-a-masked-first-second-before-the-curve)
          primes `recheck`, masks half A's first second in training and val, and moves learn's
          renders to a bounded-memory copy of the render server (renders unchanged).
        - **Done 2026-10-18** ([results](dose-probe-results.md), audited; 7,448 renders, 7,518 with
          the stop audit's 70). On top of the leak-free EQ, the **full-band** true short-time
          magnitude with C′'s phase and one resynthesis (`full100`) recovers +0.116 [+0.045,
          +0.187], **0.74 [0.50, 0.86] of the remainder** (0.86 of C′'s gap); Griffin–Lim adds
          nothing measurable (+0.007 [−0.003, +0.017]). The 2–8 kHz dose on E_st's mask recovers
          only +0.039 [+0.002, +0.077] (0.25 [0.01, 0.59]), below the full-band field (−0.076
          [−0.150, −0.002]). Dose shape undecided; the time-shift control undecided (it controls
          the 2–8 kHz dose only, so the full-band reading has no control).
        - **Implication (hedged):** option 2 is supported only as a **full-band** per-bin log-gain
          with C′'s phase and one resynthesis; its oracle ceiling is `full100`. E_st (2–8 kHz) is
          not its gate metric. **Next (proposed, not yet planned):** a zero-render full-band
          short-time error and the ±12 dB bound re-measured on `full100`'s field; optionally a
          localising probe (`full100` below 1.6 kHz, and a full-band shifted control, about 2,400
          renders); then option 2, full band.
     2. **Fresh full mixes are the only yardstick for progress;** reused parts are for exploration.
        The 21 stage-F parts are now used once, so the decision test should use unseen parts
        where it can (item 3).
     3. **More fresh development material.** Request sent to the cloud researcher on 2026-10-17.
        With only 21 usable fresh parts, effects much below about 0.03 read as ties.
        - **Known-answer songs, pilot B1** ([results](known-answer-b1-results.md), audited; 17,290
          renders): four songs rendered through drawn presets and mixed back, so the record is exact.
          The pipeline works (the truth reads ≤ 0.0011 against itself). Arm A against S reads +0.001
          [−0.523, +0.524] over 3 bands: undecided, and 3 bands can show almost nothing. The spread
          is one band: Heather Jane +0.36, where S starts near the truth; the other three songs
          −0.17 to −0.20, the fresh one (The Apprehended) −0.17. With the isolated truth as the stem
          (arm O) −0.134 [−0.323, +0.056]. The knobs are not shown closer than S's (+0.038).
        - **Next: B2**, proposed at the pool's cap (the declared rule asks for 5,654 songs): up to 4
          fresh DI-only songs (Strobe "Maya", MekaPhil, The Timezone "GOTGF", Perpetual Escape
          "Stop And Rise", after scope and held-out checks and downloads), about 14k renders and
          2.5 h, for about ±0.23 over 7 bands at B1's spread. Its amendment and review come first.
     3b. **Many sections per track, not one crop** (the user's idea, 2026-10-17;
        [plan](multi-section-plan.md) → [results](multi-section-results.md), audited). Every 10-s
        section where the guitar plays gives about 13× the audio of one crop (507 sections, 38
        parts). Step 2 (true DI, development, batch 0: 19 parts, 10 bands; 21,647 renders):
        - a search fitting three sections at once lands a little closer on held-out sections than
          a one-section search, P = −0.018 [−0.030, −0.005] (7/3 bands), about 6% of the search's
          gain over S, at about twice to three times the renders; at equal renders not shown (the
          conservative bound is +0.024 [+0.005, +0.044]);
        - one section's search keeps about 0.87 of its gain on held sections; regrets are near the
          seed floor, with a few parts (magilla, Farthest Step, Blind Spots) standing out;
        - the tone curve tracks where sections disagree, most on Cambridge (Spearman +0.59); on
          the Telefunken live-room parts only within a part (+0.34; pooled +0.06).
        Next (step 3): several held-out sections as arm A's scoring unit; the multi-section
        objective provisional until a matched-budget control; then grouping sections into sounds
        (the user's caution about several guitars and mid-song changes), and song research as a
        prior.
     4. **Decision point: one fresh-song test of arm A with the improved rebuild** (and Mega-53 if
        it still leans better). If arm A clearly beats S on fresh full mixes (read as that test's
        plan declares), build the product around it. If not, revive arm B (song to settings directly) with these lessons, or a hybrid.
        **Pending user decision (2026-10-19):** the audited oracle-DI arm found a perfect DI gives
        arm A no measurable gain on fresh full mixes, so direct prediction (arm B, pre-trained on
        part C's set) is proposed as the main route. Part C's set is done
        ([results](pretrain-set-results.md), audited): on true val mixes the learning curve
        flattened between 20k and 40k (Δ +0.0012 [−0.0020, +0.0045]; STOP, no extension), while
        the guitar alone and training-style mixes still improve. Next on that route: a real-song
        test of a model trained on this set.
        **Perfect separation, measured (2026-10-19,
        [amendment 3](arm-a-mega53-results.md#amendment-3-perfect-separation-on-stage-f-2026-10-19)):**
        with the amp track as both target and rebuild source, arm A gains −0.066 [−0.090, −0.042]
        over H (−0.094 against S, 11/12 bands), and the true DI on top a further −0.080 (−0.174
        against S). The stem target, not the DI, is what limited arm A; better separation is worth
        up to about 0.07 to arm A, and a better rebuild about as much again once the target is
        clean. 13,986 renders.
   - **Kept:** bleed handling (no cleaning; the no-high-bleed row beside all parts), arm B paused
     until the decision point, metal out of scope.
   - **Renders:** about 250k used so far. Since the 2026-10-16 update: arm B's retrain about
     14.8k, the local objective 7,061 + 3,528 (1b) + 3,528 (1c) + 7,200 (1d), the ceiling
     extension 17,550 plus 72 warm-ups, the listening page 26, arm A with Mega-53 30,102, the
     rebuild-gap study 18,981, multi-section step 2 21,647, the rebuild-tone step 8,280, known-answer B1 17,290, part C 43,060 and perfect separation 13,986 (after the 250k). No fixed limit (2026-10-16): each step plan
     declares when to stop rendering from its own evidence (a flattened search curve, a learning
     curve that stops improving, an interval narrow enough to answer the question), and reports
     what it used.
   - **Open user decisions:**
     - reopening arm B (its shuffled-input control first), at the decision point above;
     - Tone King for step 2.
   - **Then, after the decision point:** step 5 (optimiser comparison), step 6, and finally step 7, the pooled held-out
     test.
   - **How the Mac is shared (the MPS GPU, 8 CPU cores, 32 GB):** one GPU job at a time; at most 3
     render processes machine-wide, with `isolate`, grouped by amp; separation only when the
     renderer is idle or light. Plans are reviewed by an independent agent before compute; the
     cloud researcher takes literature questions and the task executor monitors and downloads.
   - **Render order:** reused Morgan renders carried the previous render at hiss level until
     `isolate` (#186 for match). The [audit](render-order-audit.md) found no decision
     overturned. Set 5's C′-over-C is fragile: inconclusive if the at-risk parts are dropped,
     passing when they are scored on half B.

   **Where it stood before 2026-10-14 (the menu-ranking work; some sub-steps below remain
   open):**

   **What the menu-ranking route showed:**
   - Rebuilding the DI with a network, then letting the judge pick a menu preset, beats
     the clean default and the training-free stand-in. On clean PR12 it is 8.5% (not
     passed, [results](di-recovery-results.md)). On heavier tones it is large
     ([set-3 development](di-recovery-set3-results.md)).
   - **It has not beaten a fixed driven preset.** The one-time held-out confirmation
     did not pass on SW50R and PR12 ([results](set3-heldout-confirmation-results.md),
     verified twice); the measurement review later found that gate undecidable. Against the same declared constant, development showed no robust edge
     either.
   - **With the true DI, the ranking works.** It beats the constant on all three amps.
     The loss is in the rebuilt DI: about −0.16 (SW50R), −0.24 (PR12) and −0.22 (AC20) in
     mean log ratio.
   - **Ruled out as the main lever:** the activity mask, score re-weighting, pooling
     amps, PANNs and log-mel rerankers, separator upgrades (+1 dB), and our tone encoder
     (74.5% on renders, but it fails on real recordings).
   - **Untested** (the earlier "native transfer" pilot was mis-specified and never
     ran a model): real-amp-to-plugin transfer, full mixes, multi-guitar targets, and
     heavy-tone listening.
   - **Set 3's held-out split is spent.** A new confirmation needs fresh material.

   **Measurement review (2026-10-10, [review](closeness-review-2026-10-10.md)).**
   - **Several "fails" were undecidable,** including the held-out gate.
   - **The judge is treble-deaf** on some heavy parts.
   - **The network's picks are under-driven:** its rebuilt waveform makes presets sound
     dirtier than they are.
   - **The analysis protocol is updated.**
   - **The user's decisions:**
     - the measure plays the DI at a fixed −22.9 LUFS;
     - a heavy-tone listening check (built, awaiting the listener);
     - a hearing-weighted judge option, beside the current one.
   - **Re-scored under them** ([results](fixed-level-rescore-results.md), verified):
     - **The 3 kHz cut helps** (−0.070, 90% −0.109 to −0.030).
     - **Against a fairly chosen fixed preset,** the cut chooser reaches −0.143, but on
       two bands and many forks: a lead, not a claim.
     - **A fresh confirmation needs 20 or more new bands.**
   - **Follow-ups, 2026-10-10:**
     - **Playing the rebuilt DI quieter is futile** ([results](underdrive-trim-results.md)).
     - **Judge v2 with fixed bands** ([results](judge-v2-results.md)) strengthens the
       edge, but about half of that is an artefact of the masking floor; it needs a
       symmetric floor before any adoption.
     - **Judge v3** ([spec](judge-spec.md), [results](judge-v3-results.md)) is that
       floor, from both sides and in hearing's units. It holds every property of the new
       judge specification, keeps every standing comparison's sign, and changes about
       half the picks. The cut's edge over the uncut DI shrinks to −0.027 (inconclusive).
       It replaces v2 as the candidate judge.
     - **A waveform-keeping loss** ([plan and result](di-loss-plan.md)): failed its
       pre-check. SI-SDR kept no more waveform (1–3 kHz coherence 0.170 against 0.169),
       and the spectrum got worse. The complex-STFT term can't train on MPS. Making
       MR-STFT NaN-safe removed the old MPS glitches.
     - **Fresh bands:** 9 confirmed open sessions (about 46 parts), a ceiling of about
       12–18 bands. All nine are set 4 ([declaration](validation-set4.md)): 35 kept parts
       in 9 bands (21 high-gain, 12 crunch, 2 clean).
       - **The first five sessions (13 parts) are spent** by the confirmation.
       - **The four Internet Archive sessions (22 parts) are unused.**
   - **Rethink (2026-10-10):** no more chooser or judge tweaks on the 33 development
     parts until the listening check is in. *(Lifted 2026-10-14 for the ML plan's steps,
     with a development ledger: ML plan decision 4.)*
     - Rebuilding the DI's fine detail has failed every way tried: longer training, more
       guitars, architecture repairs and a waveform loss.
     - The development data is over-used.
     - The binding constraints are the judge's validity on heavy tones (listening) and
       fresh data.
     - **Next:** a declared [confirmation](set4-confirmation-plan.md) (draft v2). The
       chooser's development edge is all clean and crunch: −0.162 against the product's
       own starting preset, every band negative. On high-gain it is none (+0.03). So the
       test targets clean and crunch parts, on the held-out sessions of sets 1–2 plus
       set 4. It awaits the user's approval.

   **Next, in this order:**
   1. **Ship a per-amp fixed driven preset** as `generate`'s baseline for distorted
      songs. *Done 2026-10-09
      ([results](driven-baseline-results.md)).*
      - **SW50R:** Wall Of Doom; **PR12:** Vintage Metal; **AC20:** Dirty Coil Rhythm.
      - Dry, they beat the clean template on all 23 reserved crunch and high-gain parts,
        at about half the distance, and lose on clean parts.
      - `generate` now starts distorted Morgan parts from them, before heavy-tone
        listening, as a stated exception.
   2. **Split the rebuilt-DI gap cheaply** on development (no training)
      ([plan](set3-gap-split-plan.md)). The parts tested are level, mask, long-term
      balance and the rest. Alignment is left out: Codex's controls showed the judge
      ignores few-sample shifts.
      *Done 2026-10-10 ([results](set3-gap-split-results.md)), independently
      verified.* The rest of the waveform explains it, 87% of the gap.
      - **Level:** 13%.
      - **The activity mask:** 0.
      - **Matching the long-term spectrum:** makes it worse, because above 3 kHz the
        rebuilt DI is unrelated to the true one.
   3. **Adopt the reference-proxy fallback** for judge refusals. *Done 2026-10-09:
      `learn/rebuilt_judge.py`, for every new rebuilt-DI scoring.*
   4. **Improve the DI network where the gap is,** PR12 and AC20 first: longer
      multi-amp training, stem-aware training (renders mixed and separated), and
      room-and-mic augmentation.
      - **Pilot, 2026-10-10 ([results](di-network-v2-results.md), verified):** neither
        longer training (−0.012) nor set 3's guitars (−0.015) moved the picks; the bar
        was −0.05.
        - The review found every network's bottom levels dead: a GLU gate shut, cutting
          off 86% of the weights. So data and training length couldn't matter yet.
      - **Cutting the rebuilt DI above 3 kHz** ([results](rebuilt-di-lowpass-results.md),
        verified): −0.049, 23 picks better and 5 worse, missing the bar by 0.0009.
        **Adopted by the user's decision** as a free, direction-consistent near miss
        (`learn/rebuilt_judge.lowpass`). It is not counted as a pass.
        *Retired 2026-10-11 (the user's decision):*
        - it helped only on high-gain, now out of scope;
        - it hurts on held-out clean parts (+0.044) and does nothing on crunch;
        - the corrected network (C′) is measured without it.
        Rebuilt DIs are used uncut from now on.
      - **Repairing the bottom** ([v3 plan](di-network-v3-plan.md)): normalising the
        bottleneck improved early training, but the gate shut again (pre-check failed).
        v3b replaced that gate, and training still learned to ignore the bottom (0.1%
        contribution). That route is closed.
      - **Plugin renders against real amps** ([results](sim-real-gap-results.md),
        verified): not the lever. The network's rebuild is less coherent with the true
        DI than its own distorted input, on plugin renders too. The training loss
        (mostly spectral magnitude) doesn't keep the waveform, which a driven amp
        responds to.
      - **A waveform-keeping loss** ([plan and result](di-loss-plan.md)): failed too.
      - **Paused, 2026-10-10:** five different attempts didn't move the rebuild's detail.
        *The [2026-10-11 audit](audit-2026-10-11.md) found the closure not established:*
        every network discards detail its own input carries (clean, 1–3 kHz: recording
        0.72, networks 0.44–0.50), so it is a limit of the model and loss, not of
        distortion. All five shared a magnitude loss, no pass-through path and a high-gain
        training mix. A residual network is the next try.

   **Next, revised 2026-10-10 (evening), in this order:**
   5. **The declared confirmation** ([plan](set4-confirmation-plan.md),
      [results](set4-confirmation-results.md)). *Done 2026-10-10: confirmed, and
      independently re-checked.*
      - **Clean and crunch:** −0.087 (about 8% closer, 90% −0.157 to −0.017), carried
        by clean parts.
      - **High-gain:** the chooser is harmful (+0.318), so the fixed driven preset stays.
      - **The 3 kHz cut** didn't help on fresh data.
      - **The test:** the 3 kHz cut chooser against the product's own starting preset
        (the clean template for clean parts, the shipped driven preset for crunch), on
        fresh clean and crunch parts:
        - 20 held-out parts from sets 1–2 (11 bands);
        - set 4's crunch parts, with its high-gain parts report only.
      - **Why this, now:**
        - Development shows −0.162 there, negative in every band and 76% of the oracle.
        - Development is over-used.
        - Its regime is the one the judge was validated in by ear.
   6. **The heavy-tone listening check** (the user). It decides the candidate judge (now
      v3, which needs pairs where its picks differ from the current judge's), and whether
      the high-gain verdict ("no edge over the fixed preset") stands.
   7. **If the confirmation passes: songs, not amp tracks.** *Done 2026-10-10
      ([results](songs-check-results.md)): from a separated stem the chooser keeps 75% of
      the amp-track gain (−0.114, development).* Rebuild from separated stems
      and from mixes, first on development, under a declared rule. The product's input is
      a song, and set 3 showed stems lose part of the gain.
   8. **Then the product:** for clean and mild-crunch songs, `generate`'s audition page
      offers the chooser's top picks, marked experimental. High-gain songs keep the fixed
      driven preset.
   8b. **A fixed clean starting preset,** chosen on development by rule. *Done
      2026-10-10: confirmed ([results](clean-baseline-results.md)).*
      - **The presets:** Royally Ambient (PR12), Pedal Platform Clean (SW50R) and Low-Watt
        Americana (AC20), made dry, are about 12% closer than the template on held-out
        clean parts.
      - **`generate` now starts clean Morgan parts from them.**
      - **Exploratory:** the chooser is not shown to add to them on clean parts.
        *Corrected by the audit:* the +0.009 used the 3 kHz cut, which hurts on clean;
        uncut it leans better (−0.035, 6 of 8 bands, about 20% power). From a stem there
        is no edge, so it still doesn't run on clean songs. On crunch it leans better on
        all 3 bands, a test too small to decide.
   8c. **Predict the sound, not the knobs** ([plan](sound-desc-plan.md),
      [results](sound-desc-results.md)). *Run 2026-10-11, independently reviewed: not
      shown to help.* *The [2026-10-11 audit](audit-2026-10-11.md) corrects the reading:
      undecided, not failed.* Counting each band once, it is −0.147 on crunch, level
      with the chooser and near the ceiling; one song (Eat The Feeder) pulls it down, where
      it picks wet presets.
      - **The idea:** the plugin computes knobs to sound exactly, so a model predicts a
        sound description from the record, and the nearest preset description wins.
      - **Stage 0 passed:** with the same notes, a simple description picks crunch
        presets well (−0.124 against the fixed crunch preset).
      - **Stage 1, a translator trained on 36,000 plugin renders:** no better than the
        cheap untrained baselines on crunch (gates inconclusive), worse than the fixed
        preset on clean, and below the rebuilt-DI chooser everywhere. Phase B (a model of
        every setting) doesn't start.
      - **Why (first reading):** records sit far from the renders. The audit found this
        explains the MLP's collapse, not ridge's: ridge does as well on records as on
        renders in 5 of 6 crunch bands.
      - **What would be needed:** record-like training inputs or a metric learned on
        records, and more crunch bands than development has (6).
   8d. **Tone King starting presets** ([plan](toneking-baseline-plan.md),
      [results](toneking-baseline-results.md)). *Done 2026-10-11, independently re-derived:
      adopted.*
      - **Clean:** Vintage Trem (Richard Henshall), made dry, about 12% closer than the
        plugin's Default made dry on held-out clean parts (12 of 13, 8 bands).
      - **Crunch:** Squishy Lead (Adam Christianson), made dry, about 29% closer than a
        typical preset on its channel (7 of 7, but 3 bands): thin evidence.
      - **Both on the Rhythm channel,** and about even with the Morgan starting presets.
      - **For the product session:** a `dry/toneking` recipe and `generate` step 4.
   8e. **Audit of the negatives** ([audit](audit-2026-10-11.md)). *Done 2026-10-11.*
      No calculation errors; several "failed" readings were undecided. Decisions: report
      band-weighted results beside part-weighted ones; the 3 kHz cut is off for clean
      parts; next, a translator description that discounts reverb tails, and a residual
      DI network trained on clean and crunch. Fresh clean and crunch sessions with DIs
      are still needed for any firm answer.
   8f. **The MPS gradient bug** (2026-10-11, [plan amendment](residual-di-plan.md)).
      - **Every DI network was trained on MPS** (all but one CPU pilot), where torch.stft's
        gradient is wrong for signals longer than 65,536 samples. Training crops are
        144,000, so the spectral loss trained from a corrupted gradient.
      - **Fixed:** the loss is computed on the CPU, and a test guards it.
      - **Retraining:** the current network's design with correct gradients (C′), and a
        residual design (R). The conclusions about earlier networks are undecided until
        then.
   8g. **A correct gradient, and a residual DI network** ([plan](residual-di-plan.md),
      [results](residual-di-results.md)). *Done 2026-10-11, independently re-derived.*
      - **The gradient fix helps, marginally:** −0.036 band mean, all on crunch, where the
        corrected network gets −0.171 against the fixed preset (the oracle −0.186). It
        isn't robust to leaving out one band.
        - **The second seed didn't confirm it** (−0.020, inconclusive). By the declared
          rule the gain is unconfirmed: under-powered, not absent (both seeds together
          −0.028). Both seeds beat the fixed crunch preset on development (−0.12 to −0.17).
          The next test is held-out, with two or three seeds declared up front.
      - **Passing the recording through (residual) is futile:** +0.059, worse on crunch.
        The rebuilt DI keeps the recording's brightness.
      - **Earlier crunch conclusions about the network are open again.**
   8h. **Held-out test on set 5** ([plan](set5-test-plan.md), [results](set5-test-results.md)).
      *Done 2026-10-12, adversarially audited.*
      - **On fresh bands the corrected network (C′) picks better than the old one:** −0.124
        band-weighted (−0.059 by part), 5 of 5 bands, passing by 0.003.
      - **It is a crunch effect, carried by two small bands,** and fragile to leaving one out.
      - **Render-order audit (2026-10-14):** dropping two at-risk cells makes this
        inconclusive; it still passes with them scored on half B
        ([audit](render-order-audit.md)).
      - **C′ replaces C as the research network.**
      - **Product question (report only):** C′ only matches `generate`'s crunch start
        (−0.023). It goes to the combined set-5 + MedleyDB stem test.
      - **A song-level class predictor from the rebuilt DI** failed its positive control
        twice and is closed (its results doc is on the unmerged branch
        `ml/class-predictor`).
   8i. **Set 6 (MedleyDB): 5 parts from DIs labelled by ear**
      ([validation-set6.md](validation-set6.md)). *Declared 2026-10-12, amended twice on
      2026-10-13, unused.*
      - **MedleyDB names no DI,** and no automatic DI-role rule passed its development bar
        (amendment 1). Clean DIs cannot be told from two microphones.
      - **The user labelled DIs by ear** ([plan](set6-di-labelling-plan.md)). A validation
        round passed: 10 of 10 confident answers right, and no decoy named (amendment 2).
      - **That gives 6 groups from 4 songs, and 5 kept parts:**
        - 3 crunch parts in scope, from 2 bands: Little Tybee, and Port St Willow ×2. Port
          St Willow's parts are low-confidence, and their crops read clean.
        - 2 high-gain parts, report-only.
        - No clean part.
      - **For a stem test, only Little Tybee is in scope.** Port St Willow and Big Troubles
        are in MUSDB18's train subset.
      - **Next:** recompute the deciding test's power with set 5 plus set 6 (8j).
   8j. **The deciding song-level test: no power** ([note](stem-test-power.md)). Written before set
      6's amendment 2, so it is to be recomputed. MedleyDB then gave no
      usable DI parts, and set 5 has 3 crunch bands with a mix: about 9–18% power. Proposed: close
      the chooser for the product (step 9), keep C′ for research, and reopen with 8–12 new crunch
      bands recorded with a DI. The user decides.
   9. **If it doesn't pass:** close the rebuilt-DI chooser for the product. The candidates
      left are a cheap direct-ranker test, and recording a few guitarists (DI plus
      mic'd amp) for data.
   10. **When the plugin is ready:** remove research and experiment records from the
       repository.

   **Parked, with reasons:**
   - **Network improvements:** reopened by the MPS gradient bug (8f, 8g). The residual design is futile, and the corrected network is under test (set 5).
   - **Judge v2:** half its gain was an artefact of the masking floor; superseded as the
     candidate by judge v3, which waits for the listening calibration.
   - **Search beyond the menu:** on high-gain, the oracle's headroom (−0.17) is out of the
     rebuilt DI's reach, so a search through it would hit the same wall.
   - **The four Internet Archive sessions:** fresh material, kept unused for the next
     declared test.
   - **Set 5** ([declaration](validation-set5.md), 2026-10-12): fresh held-out material,
     unused. 31 parts from 7 new bands. 26 are in scope: 16 clean (Ronnie Jones, Hazael,
     BKS) and 10 crunch (BKS, Saturn Syndicate, The Ferryboat Men, Fytakyte). Nova-One's
     high-gain parts are report-only. Kept for the next declared test.

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
  step 3's readout). As of 2026-10-17 the candidate is arm A's current best (−0.083 against S on
  development; one listener chose it 4 of 4 where a difference was heard), but on fresh full mixes
  it reads only −0.028 [−0.064, +0.008]: not ready to ship. Arm B is paused until the ML
  decision point (step 0). Until then `generate` sets what research
  documents. *The two render checks are done (2026-10-14, one development
  part, PR12):* fresh-process renders with isolation repeat exactly (maximum difference
  0.0); the isolation fade-in (the same for every candidate) moved the match loss by
  about 0.003 weighted, mostly its dynamics term (0.012: attack and loudness range;
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
| 2026-10-12 | DI path: Tone King renders pre-rolled (D-M1), no tremolo from a recording (D-M7), no low EQ from a mix (D-M8 start), screen and `--enumerate` texts (D-M17, D-M18); the rest parked | [roadmap-history.md](roadmap-history.md), step 5; #168–#171 |
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
| 2026-10-17 | Bleed cleaning not adopted; high-bleed parts stay flagged and results report the no-high-bleed row beside all parts | [bleed listening](bleed-listening-results.md) |
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
