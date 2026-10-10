# Roadmap

The one living plan. Update it when a result lands or a decision changes; the detail
lives in the linked documents. Last updated 2026-10-09.

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

0. **Song-to-preset model** ([plan](di-recovery-plan.md); the Codex continuation is
   reviewed in [codex-continuation-review.md](codex-continuation-review.md)).

   **Where it stands:**
   - Rebuilding the DI with a network, then letting the judge pick a menu preset, beats
     the clean default and the training-free stand-in. On clean PR12 it is 8.5% (not
     passed, [results](di-recovery-results.md)). On heavier tones it is large
     ([set-3 development](di-recovery-set3-results.md)).
   - **It has not beaten a fixed driven preset.** The one-time held-out confirmation
     failed on SW50R and PR12 ([results](set3-heldout-confirmation-results.md), verified
     twice). Against the same declared constant, development showed no robust edge
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
     parts until the listening check is in.
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
      - **Closed, 2026-10-10:** five different attempts didn't move the rebuild's
        detail. Heavy distortion appears to leave too little to recover it at this scale.

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
   6. **The heavy-tone listening check** (the user). It decides judge v2, and whether
      the high-gain verdict ("no edge over the fixed preset") stands.
   7. **If the confirmation passes: songs, not amp tracks.** Rebuild from separated stems
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
      - **Exploratory:** the chooser adds nothing on top of them on clean parts (+0.009).
        Its product value now rests on crunch songs, and is unproven there.
   9. **If it doesn't pass:** close the rebuilt-DI chooser for the product. The candidates
      left are a cheap direct-ranker test, and recording a few guitarists (DI plus
      mic'd amp) for data.
   10. **When the plugin is ready:** remove research and experiment records from the
       repository.

   **Parked, with reasons:**
   - **Network improvements:** closed, as above.
   - **Judge v2:** half its gain was an artefact of the masking floor. It waits for the
     listening check, and a symmetric floor.
   - **Search beyond the menu:** on high-gain, the oracle's headroom (−0.17) is out of the
     rebuilt DI's reach, so a search through it would hit the same wall.
   - **The four Internet Archive sessions:** fresh material, kept unused for the next
     declared test.

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
| 2026-10-09 | Codex continuation reviewed: held-out failure confirmed; ranking works with the true DI, the loss is in the rebuilt DI; native-pilot "failure" was a mis-specified test; research stays in the repo until the plugin is ready | [review](codex-continuation-review.md) |
| earlier | Closed: response atlas, warm-start regressor, noise and synthetic probes | [tone-matching-plan.md](tone-matching-plan.md) |
