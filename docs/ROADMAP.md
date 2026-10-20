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
  by ear (product steps; history in [roadmap-history.md](roadmap-history.md#product-steps-16-as-they-stood-on-2026-10-14), step 5).
- **`edit`** changes a preset from a plain-English ask.
- **Predicting a preset from the song** is active research, not yet in the product
  (step 0). Since 2026-10-14 the aim is to generate settings, not rank presets. Two routes are
  active: arm A (a search through a DI rebuilt from the separated guitar) and a direct model
  (song to settings). Neither is yet shown better than the starting preset on fresh full mixes:
  arm A reads −0.028 [−0.064, +0.008] with htdemucs and −0.046 [−0.091, −0.000] with Mega-53
  ([results](arm-a-mega53-results.md)); the first, untuned direct model +0.033 [−0.053, +0.119]
  ([results](direct-existing-results.md)). Better separation is the shared lever (step 0). The
  earlier menu-ranking route is in the [history](roadmap-history.md).
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
     **Mega-53 is now the ML default separator** (htdemucs stays selectable), and unlicensed
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
   shared lever.** The rebuild work (the [dose probe](dose-probe-results.md)'s full-band head) waits
   until the target is clean enough for a better rebuild to pay (XO, ZT − YT).

   **Next, in order:**
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
      +2 dB; blind picks lose.*
   2. **Train the direct model on realistic separated stems,** and check how much it relies on the
      stem against the mix ([plan](direct-model-stems-plan.md), declared and reviewed 2026-10-19):
      zero-render checks of the stem mismatch on the existing model first, then a 5k pilot (its
      ≈2.4 h of training needs the user's approval; real Mega-53 stems, a mix-only model, the old
      recipe), then one stage F test, D − S primary. The full build (5–7.4 h of training, approval
      first) waits on the user freeing disk (34 GB free at start).
      *Gate 1 done 2026-10-20 ([results](direct-model-stems-gate1-results.md)):* the stem matters
      (GATE1 STEM); the mix adds little behind a clean or separated stem, so the next model should
      read the separated target stem alone (a pilot-arm change for the user to approve).
   3. **Two zero-render checks.** *Done 2026-10-19 ([results](shrink-snr-judge-v3-results.md)):*
      the best shrink does not measurably depend on stem SNR (a rule by SNR gains −0.003 [−0.013,
      +0.007] on held-out bands; nothing on realistic stems), and judge v3 agrees with the ear a
      little less than the default judge (Spearman 0.64 against 0.80; one pair worse in four of
      five trials, sign test p 0.125, so weak).
   4. **Real-mix previews:** once the user has downloaded them, test on real mixed songs.
   5. **Then a fresh-song decision test** of the two routes on unseen parts (the 21 stage-F parts
      are reused). If one clearly beats S there, build the product around it.

   **How results are read (the user's rules):**
   - no arbitrary pass/fail bars: every comparison is an effect size with a 90% band-clustered
     interval, and any improvement is built on; under-powered is not failed;
   - the best estimate is chosen, with the cheaper option on a tie;
   - controls explain a result, they don't veto it;
   - a weak component (the separator, the rebuild) is a research target, not a reason to drop the
     route;
   - the listener's answers are trusted; layout confounds are caveats;
   - an effect left off is a correct answer on a dry record.

   **Kept:** bleed handling (no cleaning; the no-high-bleed row beside all parts), metal out of
   scope, arm B (the older settings model) paused. **Parked until after Next steps 1–2:** known-answer B2
   (proposed, up to 4 fresh songs, about 14k renders), multi-section step 3 (held-out sections as arm
   A's scoring unit), and the dose probe's zero-render follow-ups (all in the
   [history](roadmap-history.md#step-0-the-song-to-preset-model-as-it-stood-on-2026-10-19)).
   **Open user decisions:** reopening arm B (its shuffled-input control first), at the decision
   test; Tone King for the ML plan's step 2 (knob ceiling 2; done on Morgan).
   **After the decision test:** the ML plan's step 5 (optimiser comparison), step 6, and step 7,
   the pooled held-out test.

   **Renders:** about 370k so far (250k to 2026-10-17, then multi-section 21.6k, rebuild-tone
   8.3k, B1 17.3k, dose probe 7.4k, part C 43.1k, oracle-DI 7.0k, perfect separation 14.0k,
   direct-existing 0.9k, record-match 0.8k), no fixed limit (2026-10-16): each step's plan declares when to
   stop rendering from its own evidence and reports what it used.

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
  step 3's readout). As of 2026-10-19 neither ML route is ready to ship: on fresh full mixes
  arm A reads −0.028 [−0.064, +0.008] against S (htdemucs) and the first direct model ties S.
  The ML session's next steps (separation first) are in step 0. Until then `generate` sets what
  research documents. *The two render checks are done (2026-10-14, one development
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
