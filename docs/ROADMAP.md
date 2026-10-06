# Roadmap

The one living plan. Update it when a result lands or a decision changes; the detail
lives in the linked documents. Last updated 2026-10-07.

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
- **The judge** ([measuring-closeness.md](measuring-closeness.md)) is how closeness is
  measured. It needs the DI of the same take, and listening validated it only for clear
  differences between clean-to-crunch PR12 renders
  ([listening validation](listening-validation-results.md)).

## Next, in order

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
   eight DI-free distances (v3, v3c, log-mel and MFCC statistics, the lean fingerprint,
   masked spectra, an LDA) picks presets better than a song-blind constant: regret 0.30
   to 0.48 against 0.36 to 0.42, agreement with the judge at most 0.38. Every one of
   them prefers a render of the part's own take over every other player's render: the
   performance swamps the tone. Next, the candidates that need downloads or training:
   - **Pretrained effect encoders** (AFx-Rep, about 1.2 GB to download, needs approval),
     with CLAP as the floor. General audio models (CLAP, MERT, wav2vec2) are floors
     only: once the notes differ they score near chance, and they discard the input
     level that carries the drive.
   - **Then our own contrastive encoder**
     ([round 1](research/round-1-song-only-matching.md), approach 3c), trained with the
     same settings through different playing as positives, so it learns the invariance
     the hand-made features lack. The panels already hold every preset through 43
     players' DIs; a full run is 2–3 weeks and 16k–100k renders per amp.
3. **The derived-DI route** (experiment 5): does the judge's ranking survive an
   imperfect DI? Only if it does is DI recovery worth tracking.
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

- **Predicting settings from a recording** ([supervised-model-plan.md](supervised-model-plan.md)).
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
| 2026-10-06 | The audition page stays an option, not generate's main path (check inconclusive) | [listening-check-results.md](listening-check-results.md) |
| 2026-10-07 | No hand-made DI-free distance reproduces the judge's choices; next are learned ones | [di-free-distance-results.md](di-free-distance-results.md) |
| earlier | Closed: response atlas, warm-start regressor, noise and synthetic probes | [tone-matching-plan.md](tone-matching-plan.md) |
