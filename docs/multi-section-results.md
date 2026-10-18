# Many sections per track: results (steps 1 and 2, 2026-10-18)

Run under the [plan](multi-section-plan.md); its amendments 1 and 2 govern. Development data only.
Outputs are in `~/ndsp-presets/learn/multi-section/`: `sections/` (step 1), `parts/<part>/`
(step 2's per-part cache and `result.json`), `report.json`, and `logs/` (`run.log`,
`decide-0.log`, `report.log`, the workers' logs). Step 2 ran 2026-10-17 21:56 to 2026-10-18 02:57
(commit f93aa4e) and stopped after batch 0 by its declared rule.
- **Audited 2026-10-18 by an independent agent; changes:** it recomputed every figure from the
  stored caches, result tables and section files with its own code. All the headline figures
  matched, and so did the stopping rule, the pairing, the held-out integrity (roles reproduce the
  seeded shuffle; no held section in any search's objective) and the NaN diagnosis and fix.
  - the curve restated on the 19 matched parts (it mixed 20-part and 19-part figures); with it,
    multi passes the singles' 150-setting figure at 100 settings (300 renders, twice the singles'),
    not "between 100 and 150", and the singles move −0.014 from 100 to 150, not −0.023;
  - multi on the 19 matched parts added beside the singles in the primary table;
  - the held carry-over ratio corrected to 0.87 (from 0.88);
  - the share of transfers worse than S labelled as band-weighted 3.9%, with the pooled 8 of 114
    (7.0%) beside it;
  - Fragments' exclusion given its direction: leaving it out is conservative for P, but it is the
    batch's worst transfer failure, so "transfers worse than S are rare" and "one section gets
    most of the way" are qualified;
  - the tone-curve association attributed to Cambridge (Telefunken about none, +0.05);
  - the seed floor described as measured with another seed, which may overstate the path noise in
    the same-seed regrets, with the settings distances between searches added (a declared output
    that was missing) and the floor on the matched 19 parts;
  - LOBO and band counts added to the rows; P at equal renders stated as defined only at 150;
  - the second declared reading's premise (P about 0) said not to hold; arm A's implication split
    into the scoring unit (supported) and the multi-section objective (provisional); the product
    implication's fixed-budget caveat added.
  - Also taken from its suggestions: the 7/3 band split called what it is; the measure DI's use of
    the held sections' DI audio stated; the part lost from the gap split named; the multi search's
    shared render cache noted.
- **Reading these figures:** they are post-hoc development estimates on heavily used parts, with the
  **true DI** and the real amp track. Every figure is band-weighted, with a 90% band-clustered t
  interval (bands − 1 df: 9 for batch 0's 10 bands), the leave-one-band-out (LOBO) range, and the
  count of bands below and above 0. Scores are log judge distances (mean over the two judge
  halves); "against S" is a log ratio to the starting preset S on the same section, negative is
  closer.
- **Scale:** the measure DI is built per part (one EQ and one gain over all its chosen sections,
  held ones included), not per crop, so these numbers are not on the scale of earlier crop results.
  Compare within this study only. Using the held sections' DI audio for that EQ is input-side and
  the same for every search, so it is not leakage between searches.

## Headline

**With the true DI, a search that fits three sections at once lands a little closer on a track's
held-out sections than a search on one section: P = −0.018 [−0.030, −0.005]** (7 bands below 0,
3 above; LOBO −0.022 to −0.014; 19 parts in 10 bands).
- **It took more renders.** Nominally multi spends 3 renders per setting. At equal renders the
  declared conservative bound goes the other way: multi's incumbent after 50 settings (150 renders)
  against the singles at 150 settings is **+0.024 [+0.005, +0.044]** (1 band below 0, 9 above;
  the interval excludes 0 against multi). That bound understates a search budgeted for 50 settings
  (the 150-setting search at 50 has not yet tried mic alternatives or restarts), so the
  equal-render comparison is not decided; it is not shown to favour multi. On the matched parts
  multi passes the singles' 150-setting figure at 100 settings, about twice the singles' renders.
- **The effect is small next to the search's own gain:** both searches gain about −0.27 to −0.29
  on held sections against S; P is about 6% of that.
- **Single-section searches carry most of their gain to the track's other sections:** 0.85 of
  their own-section gain on the other searched sections and 0.87 on the held ones (matched parts).
  The mean pairwise regret (+0.048) is close to a seed floor (+0.026 to +0.037). Band-weighted, 3.9%
  of transfers land worse than S (pooled 8 of 114, 7.0%). The one part left out, Fragments GTR, is
  the batch's worst transfer: one single search's settings are refused on another searched
  section and on two held ones.
- **The zero-render tone curve tracks where sections disagree on Cambridge:** Spearman +0.59
  pooled, +0.62 within part (descriptive). On the Telefunken parts there is about none (+0.05).
  All parts: +0.42 pooled, +0.46 within part.

## Step 1: the material (zero renders)

From step 1's stored `sections/` (38 pool parts = the label table's 59 clean and crunch
development parts less stage F's 21; 17 bands):
- **507 non-overlapping playable 10-s sections, 5,070 s,** against 380 s as single crops: about 13×
  the audio. Median 13.5 sections per part (0 to 38). On step 3's 24 parts, 3,550 s against 240 s.
- **30 parts in 13 bands have at least 4 sections** (eligible for step 2: 3 searched, at least 1
  held out); 20 of them are step 3's; 27 have 6 or more.
- **Crunch is thin:** of 7 crunch parts only 2 (Magician's Nephew, Diesel13) have 4 or more
  sections; Prodigal E4 has none.
- **The guitar sits low in the full mixes:** median guitar-to-backing −7.9 dB (5–95%: −18.5 to
  −2.5); 30% of sections below −10 dB, 10% below −15 dB.
- **Tone curves within a track:** median distance from the part's median curve 1.19 dB (90th
  percentile 3.55) against a half-to-half noise floor of 1.63 dB median; Cambridge 0.71 dB,
  Telefunken 1.55 dB (bleed and sound change confounded there). magilla ElecGtr1DT shows two tone
  shapes (the 100 Hz band near −4 dB early, +8 to +17 dB later).

## Step 2: what ran

- **Batch 0 only:** step 3's 20 eligible parts in 10 bands (18 clean, 2 crunch; 9 Cambridge, 11
  Telefunken). Amps by the amendment-1 rule: SW50R 9, PR12 6, AC20 5.
- **Per part:** up to 6 non-overlapping sections spread evenly in time, 3 searched, the rest held
  out (3 held on 18 parts, 2 on one, 1 on one; 57 held sections in all). No section was refused for
  S, so no part was skipped and no section dropped. Five searches per part (single1–3, multi over
  s1–s3, single1b = s1 with seed + 1), each 150 distinct settings from S; every incumbent at 25,
  50, 100 and 150 settings scored on every kept section.
- **One render cache per part:** a (setting, section) pair already rendered by any search is not
  rendered again, so the searches share renders, and "3 renders per setting" for multi and the
  equal-render comparisons are nominal.
- **The S repeat check:** largest deviation 2.8e-6 (tolerance 0.005); no part dropped.
- **One part has no P:** Fragments GTR. single2's final settings are refused by the judge on s1
  and on two of its three held sections, so the singles' held mean and its regrets are undefined
  and left out (amendment 1, item 6). Under the plan's "refused counts as worst" rule its P (and
  P at equal renders) would favour multi (multi is finite there: −0.211 at 150 settings, −0.165 at
  50), so leaving it out is conservative for P. Its multi and own-section figures are finite and
  kept in the 20-part figures; the matched figures below use the 19.

## The stopping rule

After batch 0, P's 90% half-width was (−0.0047 − (−0.0303)) / 2 = **0.0128**, at most the declared
0.02, with at least one batch run (MIN_BATCHES 1), so the runner stopped (`run.log`: "batch 0:
P −0.0175 half-width 0.0128 -> STOP"). Batch 1 (10 parts, 7 bands, 3 of them new, no crunch) was
not run. Its parts are the ones whose stored menus were partly refused; nothing about them is
measured here.

## Renders used

**21,647** (every cache line: renders, warm-ups and the S repeat), 976 to 1,134 per part, no
resumes, against the plan's expected about 22.4k for batch 0. About 5 h wall-clock on 2 CPU
workers. No audio kept.

## The primary and its companions (150 settings)

| | estimate [90%] | bands −/+ | LOBO | parts |
|---|---|---|---|---|
| **P** (multi − mean of singles, held) | **−0.0175 [−0.0303, −0.0047]** | 7/3 | −0.022 to −0.014 | 19 |
| P at equal renders (multi at 50 − singles at 150) | +0.0243 [+0.0045, +0.0441] | 1/9 | +0.018 to +0.030 | 19 |
| multi − S, held (matched) | −0.291 [−0.397, −0.185] | 10/0 | −0.318 to −0.257 | 19 |
| singles' mean − S, held | −0.273 [−0.373, −0.173] | 10/0 | −0.299 to −0.240 | 19 |
| multi − S, held (all) | −0.282 [−0.385, −0.180] | 10/0 | −0.308 to −0.248 | 20 |
| multi − S, its own three sections | −0.290 [−0.384, −0.197] | 10/0 | | 20 |

- **7 bands below 0 and 3 above:** the interval excludes 0 and every LOBO estimate is negative,
  but three bands go the other way; "clearly below 0" is generous for an effect this size.
- **P on held sections away from the searched ones** (post hoc, descriptive): 7 of the 57 held
  sections start 10 s from a search section (they abut it; median gap 40 s). Leaving those out, P
  is −0.022 [−0.034, −0.010] (17 parts, 9 bands; one more part drops because its only held section
  abuts a search section). Adjacency does not make P.

### The curve (held sections, against S; the 19 matched parts)

| settings | multi | singles' mean | P | bands −/+ |
|---|---|---|---|---|
| 25 | −0.213 | −0.203 | −0.010 [−0.021, +0.001] | 7/3 |
| 50 | −0.249 | −0.236 | −0.013 [−0.025, −0.001] | 7/3 |
| 100 | −0.276 | −0.259 | −0.017 [−0.027, −0.007] | 8/2 |
| 150 | −0.291 | −0.273 | −0.018 [−0.030, −0.005] | 7/3 |

- **Both searches are still moving at 150 settings** (from 100 to 150: singles −0.014, multi
  −0.015). P is steady at −0.013 to −0.018 from 50 settings on.
- **P here is at equal settings, not equal renders** (multi nominally spends 3 renders per
  setting). P at equal renders is defined only at multi-50 against singles-150 (the table above).
- **Per render:** the singles at 150 settings (150 renders each) reach −0.273; multi passes that at
  100 settings (−0.276, nominally 300 renders) and not at 50 (−0.249, 150 renders).
- The `curve_*` entries in `report.json` use all parts with a defined value (20 at 25–100 settings,
  where Fragments' single2 isn't yet refused; its P there is −0.030, −0.058, −0.051), so they
  differ slightly from this table.

## How much a single section's gain carries

On the 19 parts where every figure is defined (band-weighted means, against S):
- on its own section: −0.312;
- on the other two search sections: −0.264 (**0.85** of own);
- on the held sections: −0.273 (**0.87** of own).

All 20 parts' own-section figure is −0.304 [−0.402, −0.207]; the 19-part other-section figure
−0.264 [−0.356, −0.172]. A single section's search keeps most of its gain elsewhere in the track;
it loses about 0.04 to 0.05 of it. Fragments (left out) is the exception: one of its single
searches lands on settings the judge refuses elsewhere in the same track.

## Do sections disagree? Regrets against the seed floor

The regret r_ij = score of single_i's settings on s_j − score of single_j's on s_j (ordered pairs of
search sections). The floor (amendment 1, item 4) is single1b, s1 searched again with another seed.

| | estimate [90%] | bands −/+ | parts |
|---|---|---|---|
| mean regret per part | +0.048 [+0.026, +0.071] | 0/10 | 19 |
| largest regret per part | +0.124 [+0.080, +0.169] | 0/10 | 19 |
| share of transfers worse than S (per part, band-weighted) | 0.039 [0.001, 0.077] | 0/3 (7 bands at 0) | 19 |
| floor: \|single1 − single1b\| on s1 | +0.026 [+0.019, +0.034] | 0/10 | 19 |
| floor: how much single1's regrets move with single1b's settings | +0.037 [+0.024, +0.051] | 0/10 | 19 |
| single1b − single1 on the held sections | −0.006 [−0.032, +0.021] | 5/5 | 20 |

(On all 20 parts the two floors are +0.032 and +0.036.)

- **The mean regret is close to the floor:** +0.048 against +0.026 to +0.037. On 11 of 19 parts the
  mean regret exceeds that part's regret-change floor. The floor is measured with another seed,
  while single1–3 share one seed, so it may overstate the path noise inside the regrets: the
  settings distances (below) show the seed moves the settings more than the section does.
- **The largest regrets, with their floors,** are the first candidates of a within-track sound
  change: Farthest Step GTR 0.36 (floor 0.087), magilla ElecGtr1DT 0.24 (0.013; step 1's two tone
  shapes), Blind Spots GTR 0.20 (0.014), It Was My Fault For Waiting E1 0.19 (0.058), Gym Hours
  GTR 1 0.17 (0.019).
- **Transfers worse than S:** band-weighted 3.9% of ordered pairs per part; pooled 8 of 114 (7.0%),
  in 4 parts and 3 bands. With Fragments, whose single2 settings are refused on s1, 9 of 120
  (7.5%).
- **Two seeds of one section land equally well on held sections** (−0.006, 5/5 bands): the
  single searches' held figure is not seed-sensitive on average.

**Settings distance between the searches' final settings** (mean unit difference; mics and switches
count 1 when they differ; 20 parts):

| pair | distance [90%] |
|---|---|
| single1 vs single1b (same section, other seed) | 0.273 [0.234, 0.311] |
| between singles (other section, same seed) | 0.203 to 0.232 |
| single vs multi (same seed) | 0.161 to 0.198 |

The settings land far apart even when the scores are close: many settings fit a section about
equally well, and the seed matters more than the section.

## Does the tone curve predict the disagreement? (descriptive)

Spearman between a search-section pair's tone-curve distance (RMS dB) and its symmetric regret
(the mean of r_ij and r_ji), over the 3 pairs per part. Pairs within a part share sections, so
these are not independent and carry no interval.

| | pairs | pooled | within part (each part's pair means removed) |
|---|---|---|---|
| all | 59 (1 left out) | +0.42 | +0.46 (20 parts) |
| Cambridge only | 27 | +0.59 | +0.62 (9 parts) |
| Telefunken only (post hoc) | 30 | +0.05 | |

- **The within-part Spearman was NaN in the run's `report.json`** (and `report.log`). The cause
  was a refused score, not too few points or constant values: Fragments GTR's single2 settings
  are refused on s1, so the s1–s2 pair's symmetric regret is infinite. Centring a part's pairs on
  their mean gives inf − inf = NaN, and scipy's Spearman returns NaN for any NaN input. The same
  infinite regret was also ranked as the largest in the pooled Spearman (+0.39 in the run's
  report), which amendment 1, item 6 forbids (no readout figure may touch a refused score).
- **The fix** (`learn/multi_section.py`, `tone_pairs` and `spearman`, with a test): a pair whose
  regret is not finite is left out (counted as `pairs_left_out`), and the Spearman returns None
  for any non-finite input instead of NaN. The report was re-run (zero renders); only
  `tone_vs_regret` changed. The run's original is kept as `report-batch0-as-run.json`. Dropping
  Fragments entirely instead gives +0.41 pooled and +0.46 within part.
- **Reading:** on Cambridge (no bleed), sections whose tone curves differ more also disagree more
  on settings, within a part as well as across parts. On the Telefunken live-room parts the curve
  says about nothing, plausibly because bleed moves the curve there. The curve is worth carrying
  into step 3's grouping as a zero-render candidate signal on clean recordings, with the caveat
  that on a song it must come from the rebuilt DI.

## The rows

P (with LOBO and bands below/above 0), P at equal renders, and the regret figures:

| row | parts (P) | bands | P | bands −/+ | P LOBO | P at equal renders | mean regret | worse than S |
|---|---|---|---|---|---|---|---|---|
| all | 19 | 10 | −0.018 [−0.030, −0.005] | 7/3 | −0.022 to −0.014 | +0.024 [+0.005, +0.044] | +0.048 | 0.039 |
| no high bleed | 15 | 10 | −0.020 [−0.032, −0.007] | 7/3 | −0.024 to −0.016 | +0.021 [+0.000, +0.042] | +0.051 | 0.047 |
| no moderate or high bleed | 10 | 8 | −0.017 [−0.033, −0.002] | 5/3 | −0.023 to −0.014 | +0.032 [+0.006, +0.058] | +0.052 | 0.010 |
| Cambridge only | 9 | 7 | −0.014 [−0.031, +0.003] | 4/3 | −0.020 to −0.009 | +0.028 [−0.002, +0.059] | +0.042 | 0.012 |
| clean | 17 | 8 | −0.020 [−0.036, −0.004] | 6/2 | −0.026 to −0.015 | +0.018 [−0.003, +0.038] | +0.053 | 0.049 |
| crunch (descriptive) | 2 | 2 | −0.009 [−0.078, +0.060] | 1/1 | −0.020 to +0.002 | +0.051 [−0.153, +0.255] | +0.029 | 0 |

- **Bleed doesn't make P:** it holds without the high-bleed parts and without moderate or high.
- **Cambridge alone leans the same way,** with an interval that reaches 0 (9 parts, 7 bands, 4/3).
- **Crunch is 2 parts** (Diesel13's colour me red −0.020, Magician's Nephew's get out of bed
  +0.002): nothing can be read for crunch.

## The declared reading

The plan's readings, applied:
- **"P clearly below 0: fitting several sections carries better to unseen sections of the same
  track; multi-section search becomes the default unit for the next steps."** P is below 0, its
  interval excludes 0 and every LOBO estimate is negative (3 of 10 bands go the other way), so
  this reading applies, **with a qualification the plan's reading does not state:** the gain is
  shown at more renders (about twice to three times) and is small (about 6% of the search's gain
  over S). At equal renders it is not shown, and the conservative bound leans against it.
- **"P about 0 with singles carrying most of their own gain to held sections":** its premise, P
  about 0, does not hold; its second half does (singles keep 0.87 of their own-section gain on the
  held sections). One section is already a fair stand-in for most tracks.
- **"Large regrets":** the mean regret is near the seed floor; a handful of parts (above) stand out
  and are step 3's first grouping candidates.

## What it implies

These hold for the **true DI** on development parts. The product never has it.
- **For arm A (step 3):**
  - **Several held-out sections as the scoring unit: supported.** A part's result no longer rests
    on one crop, and the sections are there (about 13× the audio).
  - **The multi-section objective: provisional,** until a matched-budget control (e.g. a multi
    search budgeted for a third of the settings, or a single search given two to three times the
    settings) shows it pays at equal renders. The equal-render bound (+0.005 to +0.044) is against
    it today, though it understates a search budgeted for fewer settings.
  - On rebuilt DIs the balance could move either way: per-section rebuild errors that are
    independent would favour averaging over sections; a rebuild error shared across the track
    would not.
- **For the product (which sees the whole song):** fitting the preset to several playable sections
  rather than one is expected to carry a little better to the rest of the song **when the render
  budget grows with the sections; at a fixed render budget it is not shown.** The expected size is
  small (about −0.02 log here, with the true DI). A single well-played section already carries most
  of its gain on most tracks, though on one part of 20 its settings were refused elsewhere in the
  same track, so the product's check on other sections is worth keeping. None of this has been
  shown on a song with a separated stem and a rebuilt DI. The tone curve's agreement with the
  regrets on Cambridge supports detecting sound changes cheaply on clean recordings; it is a
  candidate signal only.

## Limits

- **True DI and amp tracks;** batch 0 only (19 parts with P, 10 bands); step 3's 20 parts are
  heavily reused development parts.
- **Mostly clean:** 18 of 20; crunch is descriptive.
- **One amp per part,** chosen from stored menu scores; S is the product's start on that amp.
- **Bleed per part** (the crop flag), not per section.
- **Searches fixed at 150 settings** and still moving; P at equal renders is a bound, not a
  matched-budget comparison; the searches share a render cache, so render counts per search are
  nominal.
- **Multiplicity:** one primary; everything else (rows, curve, regrets, Spearman, the gap split,
  the Telefunken row) is descriptive.
