# Roadmap

The one living plan. Update it when a result lands or a decision changes; the detail
lives in the linked documents. Last updated 2026-10-08.

## Where the product is

- **Input is a song.** The user gives a song (and a time where the guitar plays), never
  a DI of the performance.
- **`generate`** researches the song, measures the excerpt and writes one preset. On 25
  mostly clean development recordings, that preset was not shown to land closer than
  the shipped template, and a researched list of four was not shown to beat four random
  factory presets ([song-only shortlist](song-only-shortlist-results.md)).
- **Choosing among several helps, with a perfect ear.** The judge picking from four
  lands about 18% closer than the template. Whether a real ear does, listening through
  another performance's DI, was tested once and came out inconclusive
  ([results](listening-check-results.md)). `generate` offers four presets on a
  listening page (`scripts/audition.py`) with shipped CC-BY guitar riffs, and a refine
  loop, as an option.
- **`match`** without a DI describes the recording and keeps the starting preset: no
  song-only search has been shown to get closer
  ([re-check under the judge: void](no-di-rule-under-the-judge-results.md)). With the
  same take's DI it searches, but its figures come from a retired score.
- **`edit`** changes a preset from a plain-English ask.
- **Predicting a preset from the song** is active research, not yet in the product.
  - **Best so far:** rebuild the guitar's DI from the recording with a trained network,
    then let the judge pick a menu preset through it. Clean PR12 misses the declared
    bar ([results](di-recovery-results.md)). On heavier development recordings SW50R
    has a conditional pass against a fixed driven preset; PR12 and AC20 do not pass
    ([set-3 results](di-recovery-set3-results.md)). The reserved confirmation has now
    run: neither SW50R nor PR12 passes; independent numerical/audio checks agree
    ([confirmation](set3-heldout-confirmation-results.md)). No learned path is ready
    to ship.
  - **Measure:** the average-guitar measure, which listening confirmed (23 of 24
    trials, [results](avg-measure-listening-results.md)).
- **The judge** ([measuring-closeness.md](measuring-closeness.md)) is how closeness is
  measured. It needs the DI of the same take, and listening validated it only for clear
  differences between clean-to-crunch PR12 renders
  ([listening validation](listening-validation-results.md)).

## Next, in order

0. **Song-to-preset model** ([plan and checkpoint](di-recovery-plan.md)), in this order:
   - **Set 3, development:** done ([results](di-recovery-set3-results.md)).
     - **Large gains over the clean default and the stand-in** (SW50R −0.70, PR12 −0.42).
     - **Against a constant driven preset:** SW50R is a conditional pass, PR12 is not
       passed (the result depends on the constant's undeclared definition), and AC20
       fails.
     - **Reserved confirmation:** the [approved declaration](set3-heldout-confirmation-plan.md)
       and inputs were committed before execution. All 4,320 renders and both timing
       analyses completed successfully. Neither amp passes; independent checks of
       all selections/gates and 1,321 distinct audio measurements agree
       ([results](set3-heldout-confirmation-results.md)). SW50R misses the consistency
       test against the fixed driven preset; PR12 also misses the margin and joint-win
       requirements. No required comparisons were refused.
     - **Development diagnostic: independently verified**
       ([results](set3-development-diagnostic-results.md)). Known-DI selection beats
       the leave-band-out constant on all three amps under both band sets. All 14,067
       independently recomputed fields agree. This establishes useful menu headroom
       on development data; it does not isolate waveform recovery as the bottleneck.
       Rebuilt-DI selection refuses every candidate on one recording, and SW50R's
       recording-band median gap to known-DI selection is zero.
     - **Activity-proxy check: complete, independently verified**
       ([results](set3-mask-diagnostic-results.md)). Both alternative proxies rescue
       the one refused recording, but all 11 control choices remain unchanged under
       both band sets. It misses its declared improvement rule, so do not expand or
       tune this heuristic. Original-score replay, all 42,054 recomputed fields and
       22 fresh audio checks agree.
     - **Nested preset-rank calibration: complete, criteria missed**
       ([results](set3-rank-calibration-results.md)). Learning a blend of net scores and
       a preset prior improves on the prior alone but has median zero gain over the
       original chooser with the same fallback. Independent recomputation agrees on
       651,209 fields. Close this blend without changing its grid/prior/features.
     - **Next: test choice across the existing three amp menus**
       ([declared plan](set3-cross-amp-diagnostic-plan.md)). The product may choose any amp;
       prior tests mostly fixed one. Compare pooled known-DI/net choices with SW50R
       and global constants, keeping the same fallback. Development scores only;
       fresh review approved and all 17 checks pass independently. Commit before computation
       and verify conclusions afterward. No further long
       waveform training or knob search is justified yet.
       This model's shipping path remains closed. Any later model needs fresh reserved
       data; the spent split cannot be reused for tuning or confirmation. Wider search
       is deferred while the existing menu shows development headroom.
   - **Separator upgrade: run 2026-10-08, none replaces htdemucs_6s**
     ([plan](separator-upgrade-plan.md), [results](separator-upgrade-results.md)).
     - Mega-53 and X-LANCE add about 1 dB median SNR (2 dB was needed) and many more
       usable parts (sets 1–2: 14 → 21 of 28; set 3: 12 → 21 of 33).
     - The gain is on single-guitar parts (+4 dB); multi-guitar parts gain about
       0.4 dB. Other guitars in the stem are the bottleneck.
     - Pan isolation can't be tested here (the sessions have no pan). On a simulated
       pan, a choice of side made by ear would help multi-guitar parts by about 1 dB; a
       "loudest side" rule hurts.
   - **Our own guitar tone encoder: run 2026-10-08, not passed as a reranker**
     ([tone-encoder-plan.md](tone-encoder-plan.md)).
     - It names a render's preset among 22 from other players' renders 74.5% of the
       time, or 72% for presets it never trained on. Log-mel and PANNs manage 14%.
     - On real recordings its picks are worse than template+R. Recordings land off the
       render manifold, on one hub preset.
     - Closing that domain gap comes before the encoder can rerank (for example,
       training on recorded or room-and-mic augmented audio).
   - **Search beyond the menu:** deferred until a development positive control
     establishes that menu coverage is the bottleneck.
   - **Candidates from the POC model.**
   - **Stem-aware training of the DI network.**
   - **A declared reference for multi-guitar stems.**
   - **Open source only** ([round 5](research/round-5-guitar-models.md)).

1. **Listening check of the page: run, inconclusive**
   ([plan](listening-check-plan.md), [results](listening-check-results.md)). Sitting 1
   was void: both its controls were answered "?", and the "?" answers cluster there,
   so a playback problem in that sitting is not ruled out. The page stays an option in
   `generate`. The listener reported that for some songs the target guitar could not
   be found, or tone could not be compared across different notes. The picks leaned
   closer than chance under one band set only, and not beyond a song-blind taste.
   The declared rerun was set aside with the listener (reasons in the results); the
   own-DI version waits for the derived-DI route.
   - **Learned while setting it up:** a riff must match the song guitar's style. The
     listener found single-note parts can't be judged against strummed chords (drive
     sounds different on several notes at once), so the check now plays each part
     through the riff in its own style, measured from its clean recording. The page
     should do the same from the song alone (classifying a separated guitar stem as
     chords or single notes), and may need more styles (arpeggios, power chords).
2. **A distance without a DI: hand-made features fail**
   ([plan](di-free-distance-plan.md), [results](di-free-distance-results.md)). None of
   the eight DI-free distances tested beside the v3 baseline (v3c, log-mel and MFCC
   statistics, the lean fingerprint, masked spectra, an LDA) picks presets clearly
   better than a song-blind constant: regret 0.30 to 0.48 against 0.36 to 0.42,
   agreement with the judge at most 0.38. With the part's own notes, the masked spectra
   pick within the judge's near-tie range (0.04); through another player's notes they
   fall to the constant (0.36): the performance moves them more than the preset.
   *2026-10-07, from step 0: log-mel statistics and PANNs CNN14, used as rerankers over
   renders through other players' DIs, also failed ([rerank-plan.md](rerank-plan.md)).
   Our own contrastive guitar encoder passed identification on renders but failed on
   real recordings (step 0).* Remaining candidate, deferred while the development
   chooser diagnostic runs:
   - **Pretrained effect encoders** (AFx-Rep, about 1.2 GB; verify open licence before use),
     with CLAP as the floor. General audio models (CLAP, MERT, wav2vec2) are floors
     only: once the notes differ they score near chance, and they discard the input
     level that carries the drive.
   - **Own contrastive encoder: already tested, failed on real recordings** (step 0).
     Another run needs a declared intervention addressing transfer from renders to
     recordings and a cheap positive control; do not repeat the original training.
3. **The derived-DI route** (experiment 5). *Done, 2026-10-06*
   ([results](di-robustness-results.md)). It did not pass as declared. Under the
   average-guitar measure, a realistic rebuilt DI loses little, so DI recovery was
   built (step 0).
4. **The judge's coverage.**
   - High-gain calibration needs high-gain references with a DI (a download).
   - The listening checks the judge's review asked for: whether hiss matters, and
     whether drive with a matched spectrum is heard as the judge weights it.
   - Any search scored by the judge needs a positive control first.
5. **Open defects in the DI path** ([ground-truth audit](ground-truth-audit-2026-10-03.md)).
   The others are fixed (D-H1 by #107, D-M6 by #119, D-M9 by #114, D-M15 by #113),
   moot now that a match without a DI doesn't search (D-M2, D-M14), or were about how
   results were reported (D-H2, D-M5).
   - **Renders:** Tone King's start-up mute (D-M1); Morgan's reused-instance history
     (D-M13).
   - **Search controls:** `--enumerate` (D-M17); the screen's false premise (D-M18).
   - **Inversion:** the mix regime (D-M8); a false tremolo (D-M7).
   - **The search objective,** which still steers the DI path though it no longer
     judges: spectral extremes (D-H3), level handling (D-M3, D-M4), ambience, decay
     and renormalising (D-M10–D-M12), and an untested stereo term (D-M16).

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
| earlier | Closed: response atlas, warm-start regressor, noise and synthetic probes | [tone-matching-plan.md](tone-matching-plan.md) |
