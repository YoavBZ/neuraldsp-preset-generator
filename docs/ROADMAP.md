# Roadmap

The one living plan. Update it when a result lands or a decision changes; the detail
lives in the linked documents. Last updated 2026-10-24.

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

   **Trusted data only (the user, 2026-10-22): "use only what we can trust, no dirty tracks".**
   Measurements, training, tests and listening pages use a reviewed trusted set. Dirty tracks are
   excluded, not flagged. This supersedes the 2026-10-17 bleed decision (high-bleed parts flagged,
   a no-high-bleed row beside all parts). **The user's listening verdicts define the trusted
   set,** on the data-review pages (amp and mic tracks, suspected doubles, DIs). Rule-based
   measures (the audit's checks, #273's original-take level and bleed flags) only name candidates
   for that review ([ML plan](research/ml-plan-2026-10.md) §5). *Amended 2026-10-23 by the
   trusted-data plan (below): a measured verification fail excludes, and the ear decides the rest.*
   - **The data-quality audit** ([draft PR #272](https://github.com/YoavBZ/neuraldsp-preset-generator/pull/272),
     zero renders):
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
     best approach"; its implementation is in progress. Order: zero-render checks; a paired R_in
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
       reserved for test), an open user decision before T3. The audit's caveats are in the
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
     - **New training bands (2026-10-25, user):** five Cambridge-MT sessions (Ember Rev, Empty
       Signifier, Goran Levi, Mòpia, Sören; 9 electric DIs, 7 with an amp or mic track) are training
       bands (ledger `cambridge-new-training-bands-2026-10-25`), aimed at the pool's missing clean and
       crunch playing. They train only after T0's checks and the ear (the inventory marks them pending
       until a verified list admits them). T0's checks (2026-10-25): D2 passes 4 of 9 (Empty Signifier
       ElecGtr2DI, Goran Levi, Mòpia ×2). Ember Rev is out for clipping, Empty Signifier ElecGtr1DI for
       hum, and Sören for gating or edits. Goran Levi's amp track is a processed copy, not a miked amp.
       Mòpia is a scope worry: D4 flags both DIs and the amp tracks read heavily driven. The user's ear
       page (part6, 16 cards) is pending.

   **Where it stands (2026-10-19).** Not ready to ship. Fresh full mixes (stage F, 21 parts in 12
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
   The rebuild work (the [dose probe](dose-probe-results.md)'s full-band head) waits
   until the target is clean enough for a better rebuild to pay (XO, ZT − YT).

   **Next, in order (2026-10-23, the [trusted-data plan](trusted-data-strategy-plan.md)'s order):**
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
   - (c) **T2, the 5k pilot. *Started 2026-10-25 at 17:54*** under PR #290's rules: 5,154 candidates in 4 bands
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
     descriptive; not built yet): SYN's stems against SES's on T2's examples, with T2's target render as the truth for
     both. At best a ceiling check, since above 0 cannot tell cleaner from unrealistically easy. `report` still prints
     T1's old 812-example read, superseded; the same fix labels or drops it. *Known gap:* sections with an active guitar
     that has no usable DI or amp track are left out, so dense multi-guitar arrangements are under-represented. SYN
     short of SES on V-real is a realism signal, not a gap signal (both arms train on the same examples). The gap is
     read by two zero-cost diagnostics declared now: V-real by the number of playing guitars, for SES − S and SYN − S;
     and active-guitar counts of kept against left-out examples. A third, *pending the user's OK* (an unplanned longer
     run), is an SES arm trained with the left-out dense sections against SES on the kept set (2 runs, about 1.5 h, no
     renders). The read, the diagnostics and the `report` fix are built and independently reviewed before T2's results
     are seen. A leakage measure that resolves sparse sources (which would recover them, T1, Rebuild The Evil and The
     Long Wait) is built after T2 if these show the gap matters, or when T3 or T4 needs K. Before Renesans enters any
     stage: `session_guitar_parts` skips GTR 2 Amp as GTR 1's `own` (a latent bug the review of #290 found; it does
     not touch T2's four bands).
   - (d) **T3, decided after T2:** one rebuild that is also every-control stage 2D, on self-built
     mixes with full-space labels and any approved new DIs, read on K and V-real (*K empty since 2026-10-25: its
     read is open until K comes back*). Its downloads are
     asked for then.
   - **Every-control stage 1** runs on the trusted panel's parts and can now run, now that the ear
     has cleared their amp tracks (knob ceiling 2's panel: 7 parts in 7 bands, verified 2026-10-25). It needs no rebuild, so it need not
     wait for (b)–(d); they share the renderer.
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
   **Open user decisions** (updated 2026-10-23 after the [review](research/program-review-2026-10-23.md);
   the ML session's recommendation first):
   - *Decided 2026-10-24 (user, all as recommended):* the two conflicts' measured fails stand; the
     stem spot-check joins this sitting; every DI is heard before it counts; the song-blind constant
     is a V-real arm at T2 (relayed by the cloud review, then confirmed by the user in the ML session).
   - *Decided 2026-10-24 (user, as the ML session suggested):* Cnoc An Tursa is not admitted to K; at
     most a side check, never in a deciding number. SYN-E is dropped from T2 until a clean-class DI
     source (EGDB or GOAT) passes the DI checks.
   - *Before T2:* read T2's tie from the interval (a tie when it holds 0) rather than
     |point| < 0.03.
   - *Settled by the ear (2026-10-25):* K's bands. T1's K is Adam Buckley and Dark Ride; Kimock's
     and Swatkins' 4 DIs were all heard processed, so they cannot rejoin. (Cnoc An Tursa: decided
     2026-10-24, not admitted.)
   - *Before T3:* where clean-class training DIs come from (after the ear the pool holds 1
     clean-class and 1 crunch section of 181; V-real has 2 clean bands): EGDB on a borrowed backing
     (downloaded; its DI checks first), GOAT (access requested), Jen Hartswick & Nick Cassarino as
     training instead of test, Strobe and MekaPhil now, or none.
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
  +0.034]. The ML session's next steps (the trusted-data checks and the user's ear first) are in
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
| 2026-10-22 | Data-quality audit (zero renders, draft): separated stems carry a median 45% of power above the matched render, and within each band the most contaminated third scores worse on the sound gate (+0.103 [+0.055, +0.156]); doubles stay in the training backings and the stored leak check misses them; DIs are clean; labels are exact renders; bleed sits in the live-room amp and mic tracks (trial 47, Sculptor's Request GTR 1: bleed, not a wrong DI) | [draft PR #272](https://github.com/YoavBZ/neuraldsp-preset-generator/pull/272) |
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
