# Roadmap

The one living plan. Update it when a result lands or a decision changes; the detail
lives in the linked documents. Last updated 2026-10-05.

## Where the product is

- **Input is a song.** The user gives a song (and a time where the guitar plays), never
  a DI of the performance.
- **`generate`** researches the song, measures the excerpt and writes one preset. On 25
  development recordings, that preset landed no closer than the shipped template, and a
  researched list of four did no better than four random factory presets
  ([song-only shortlist](song-only-shortlist-results.md)).
- **Choosing among several helps.** A perfect ear picking from four lands about 18%
  closer than the template. Whether a real ear does, through another performance's DI,
  is untested.
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

1. **Audition page in `generate`.** Render a shortlist through a guitar riff and play it
   beside the song (`scripts/audition.py`, built). It needs:
   - a riff source that can ship (today's riffs are local development DIs; downloading
     a CC-BY DI set needs the user's OK);
   - the skill's flow and a refine loop through `edit`.
2. **Listening check of the page** (about 15 minutes, declared first). Does a real ear,
   listening through another performance, pick closer than the first choice? It decides
   whether the page is the main path or an option.
3. **A distance without a DI** ([research round 4](research/round-4-audio-ml.md) §5,
   experiment 4: the judge as teacher). Gate: it must rank candidates as the judge does
   on held-back parts. If it passes, score against real songs, not amp tracks.
4. **The derived-DI route** (experiment 5): does the judge's ranking survive an
   imperfect DI? Only if it does is DI recovery worth tracking.
5. **The judge's coverage.**
   - High-gain calibration needs high-gain references with a DI (a download).
   - Any search scored by the judge needs a positive control first.
6. **Known defects in the DI path** ([ground-truth audit](ground-truth-audit-2026-10-03.md)):
   - Tone King's start-up mute (D-M1);
   - `--enumerate` (D-M17);
   - the mix regime in the inversion (D-M8);
   - a false tremolo (D-M7);
   - the untested stereo term (D-M16).

## Parked

- **Predicting settings from a recording** ([supervised-model-plan.md](supervised-model-plan.md)).
  - The kill tests did not pass on SW50R or clean PR12
    ([K1–K3](kill-test-results.md), [PR12](kill-tests-pr12-results.md)).
  - No cheap fix rescued recognition on real tracks ([quick checks](quick-checks-results.md)).
  - Reopen only if step 3 finds features that carry over from renders to real
    recordings. If it is ever built, its amp output is a set of acceptable amps.

## Decisions

| Date | Decision | Record |
|---|---|---|
| 2026-10-02 | Song only: the user never records a DI | — |
| 2026-10-03 | Without a DI, keep the starting preset (figures later marked unconfirmed) | #107, [no-DI re-check](no-di-rule-under-the-judge-results.md) |
| 2026-10-04 | The judge replaces the v3 score as the measure of closeness | [measuring-closeness.md](measuring-closeness.md) |
| 2026-10-04 | Crop rule 2 (where the DI plays most) for new crops | [validation-datasets.md](validation-datasets.md) |
| 2026-10-04/05 | Kill tests not passed; model work parked | [kill tests](kill-test-results.md), [PR12](kill-tests-pr12-results.md), [quick checks](quick-checks-results.md) |
| 2026-10-05 | Amp choice is a set of acceptable amps; AC20 reaches fewer of these clean parts | [amp reach](amp-reach-results.md), [quick checks](quick-checks-results.md) |
| 2026-10-05 | Research doesn't beat chance at picking presets; choosing by ear does | [song-only shortlist](song-only-shortlist-results.md) |
| earlier | Closed: response atlas, warm-start regressor, noise and synthetic probes | [tone-matching-plan.md](tone-matching-plan.md) |
