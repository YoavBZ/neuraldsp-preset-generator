# Known-answer test songs, pilot B1: results (2026-10-18)

Run under the [plan](known-answer-b1-plan.md) (amendment 4 of
[clean-di-library-plan.md](clean-di-library-plan.md), part B), from commit 7ce817c on the
self-render runner (`learn/selfrender_run.zsh`). Development data only; descriptive estimates with
90% band-clustered t intervals, no pass/fail bars.
- **Code:** `learn/known_answer.py`. **Data:** `~/ndsp-presets/learn/known-answer/b1/`
  (`report.json`, `truth/truth.json`, `results/<song>/*.json`); logs in
  `~/ndsp-presets/learn/selfrender/logs/b1-*.log`.
- **Ran:** 2026-10-18, 10:52 (plan) to 13:55 (report): truth 20 min, mix 2 min, htdemucs 7 min,
  C′ rebuilds 7 s, search 2 h 34 min on 3 shards.
- **Every figure below** was recomputed from the stored per-direction results, not copied from
  `report.json`; where the two meet they agree to the printed digits.

**The question:** from a full song mix whose guitar preset is known, how close does arm A's adopted
recipe (rebuilt-DI search, 52 renders, shrunk halfway to S, htdemucs stem, C′ fold 2) land, against
the class's starting preset S? Arm O runs the same recipe with the isolated truth as the stem.

## Headline

**B1 shows that the known-answer pipeline works, and that 3 band clusters can show almost nothing
about arm A.** Arm A against S on the primary items reads **+0.001 [−0.523, +0.524]** (log d_A/d_S;
3 bands). That is undecided: the interval runs from 41% closer to 69% farther, about 14 times wider
than stage F's (±0.036). One song drives the
spread: on Heather Jane, arm A lands 1.4× farther from the truth than S over all amps (+0.36), while on the other
three songs it lands 16–18% closer (−0.17 to −0.20).
- **The plumbing:** the record is exact. The truth rendered through the judge's path reads ≤ 0.0011
  against it (S: 1.7–7.2), and the whole-track truth's slice ≤ 0.001. There were no fallbacks to S
  and no floored exact recoveries.
- **Arm O (the isolated truth as the stem):** −0.134 [−0.323, +0.056] against S. A − O, the
  separator's share, is +0.112 [−0.222, +0.446]. Both lean the expected way and are undecided.
- **Knob error:** arm A's knobs are not shown closer to the truth than S's; they lean further,
  +0.038 [−0.046, +0.122] on the identifiable knobs (unit scale). Against a random setting (a post-hoc
  baseline), both lean closer, undecided: A −0.085 [−0.232, +0.062], S −0.123 [−0.247, +0.001].
- **The amp** (not declared; units share sections, so not independent): on the true DI, arm A's
  lowest-distance amp is the truth's amp on only 6 of 68
  (item, section, direction) units, against 1/3 by chance. Arm A's own search objective picks it
  on 29 of 68.
- **B2:** the declared formula asks for 5,654 songs. As the plan predicted, the pool caps B2. The
  proposal is the four fresh DI-only candidates (about 14k renders, about 2.5 h), which would take
  the interval from ±0.52 to about ±0.23 at B1's spread.

## What was run

| Song | Band | Primary DI | Truth P1 (class, amp) | P2 after the switch | Q, second guitar |
|---|---|---|---|---|---|
| Heather Jane | Chris Coltraine | ElecGtr1 | Spacey Grits (clean, AC20) | Rhythm of The Young's (crunch, SW50R) | Broken Radio (clean, SW50R) |
| Bourbon | Rebecca Haviland | GTR 2 | Dotted Eighth Tape (edge, SW50R) | Mean Little Crunchy Guy (crunch, PR12) | It's Boosted but It Chimes (edge, AC20) |
| Collide With Me | Rebecca Haviland | GTR 1 | BC Guitar Chords (clean, PR12) | Jazzy Box (crunch, AC20) | Mustang (clean, SW50R) |
| Still Flyin' | The Apprehended | ElecGtr03 | Heartbreaker Rhythm (crunch, PR12) | Jazzy Box (clean, AC20) | Blue Hotel (crunch, SW50R) |

- **The items** (as the plan declares): 1, P1 on the primary in the full backing with vocals;
  2, the same without vocals; 3, P1 before the switch and P2 after; 4, item 1 with the second
  part's real amp tracks replaced by the second DI rendered through Q; 5 (The Apprehended only),
  item 1 less every other guitar track. **Item 1 is not a single-guitar mix:** its backing keeps
  the session's other recorded guitars (Heather Jane's ElecGtr1DT, ElecGtr2 and its double and
  ElecGtr3; Bourbon's GTR 1 amp mics; Collide With Me's GTR 2 amp mics; The Apprehended's 7 other
  guitar tracks).
- **The truths are in scope.** Every truth's measured class is clean or crunch (the edge truths read
  crunch at the low end), with its level slope at or above the crunch S's line. None reads
  high-gain. Two truths needed a second jitter draw (Heather Jane P2, Bourbon P1). No amp was
  redrawn. Jazzy Box measured crunch on Collide With Me and clean on The Apprehended (the class is
  measured per DI).
- **Menu scans** (dry factory presets, rendered on s1 or the second DI's best window, then classed;
  454 renders), counts clean / crunch / high-gain:

  | Song | Primary, P1's amp | Primary, P2's amp | Second DI, Q's amp |
  |---|---|---|---|
  | Heather Jane | AC20 16 / 14 / 1 | SW50R 18 / 18 / 9 | SW50R 18 / 15 / 12 |
  | Bourbon | SW50R 18 / 14 / 13 | PR12 23 / 6 / 6 | AC20 20 / 7 / 4 |
  | Collide With Me | PR12 11 / 14 / 10 | AC20 1 / 15 / 15 | SW50R 18 / 14 / 13 |
  | The Apprehended | PR12 18 / 11 / 6 | AC20 8 / 14 / 9 | SW50R 24 / 21 / 0 |

  No pool was empty; Collide With Me's AC20 clean pool held one preset (not drawn: P2 there is
  crunch). The crunch line on PR12 is the slope of its crunch S (Modern Metal (Pick Hard)), which
  itself reads high-gain, so the line is lenient there. The PR12 truths still classify clean or
  crunch.
- **The truths keep modules outside arm A's space**, as declared: the amp's EQ active and not flat
  in 11 of 12 (all but Bourbon P1), a compressor in 8 of 12 (6 of the 8 scored P1 and P2 truths)
  and a drive pedal in 2 (Bourbon P1, The Apprehended's Q). No delay or reverb was active, and the
  amps' reverb knobs are at 0.
- **Leakage drops** (the stored 56% and 41% are the union over items):
  - Bourbon, items 1–3: the bass amp and one vocal mic, **51.9%** of the backing's power. Item 4
    also drops the drum overheads (they leak from the second DI's amp).
  - Collide With Me, items 1–3: 4 drum tracks, **2.1%**. Item 4 also drops the bass amp, most of
    the 41%.
  - Heather Jane and The Apprehended dropped nothing.
  - Bourbon crosses the plan's "more than half" line, so its own row is the song row below.
- **MUSDB18:** none of the four songs or three bands is on MUSDB18's 150-track list (checked by
  name against the local `tracklist.csv`). The separator (htdemucs_6s) also trained on undisclosed
  extra data, which can't be checked.
- **Sections:** the plan's (Heather Jane 215/235/15/205 s, Bourbon 85/105/65/235 s, Collide With Me
  185/195/85/155 s, The Apprehended 5/15/25/245 s). Part-A flags: Heather Jane and The Apprehended
  clean; Bourbon hum (s4 hum+hiss); Collide With Me hum+hiss on all four. The listening check is
  still unread, so these rows may move under its amendment.
- **δ per section** (LUFS of the section's slice of `di_w` + 22.9, amendment 1 item 3), s1–s4:
  Heather Jane +0.63, −1.19, −0.18, +0.85; Bourbon −1.47, −0.56, −0.01, −0.94; Collide With Me
  −1.23, +0.11, +1.78, −4.60; The Apprehended +0.56, −0.19, −0.32, +1.48.
- **Guitar-to-backing ratio at unity** (amendment 1, beside multi-section step 1's −7.9 dB median,
  quartiles −10.3 and −6.3): Heather Jane −8.5 dB, Bourbon −3.3 dB, Collide With Me −10.5 dB; The
  Apprehended −7.9 dB by construction.

## Arm A against S (log d_A / d_S, held half)

Units are (item, section, amp, direction), weighted unit → (item, section) → song → band. Negative means arm A lands
closer to the truth than S. 3 bands give 2 degrees of freedom (t = 2.92).

| Row | Bands | Mean [90%] |
|---|---|---|
| **Primary: items 1, 3, 4, all amps** | 3 | **+0.001 [−0.523, +0.524]** |
| The truth's amp only | 3 | +0.169 [−0.675, +1.013] |
| The other amps | 3 | −0.083 [−0.456, +0.290] |
| Item 1, single | 3 | +0.048 [−0.607, +0.702] |
| Item 2, single, no vocals | 3 | +0.046 [−0.604, +0.695] |
| Item 3, switch | 3 | −0.091 [−0.450, +0.268] |
| Item 4, two guitars | 3 | +0.046 [−0.539, +0.631] |
| Item 5, The Apprehended without its other guitars | 1 | −0.167 |
| Hum/hiss sections (`noisy_di`: Bourbon, Collide With Me) | 1 | −0.185 |
| Clean-DI songs (Heather Jane, The Apprehended) | 2 | +0.094 [−1.585, +1.772] |
| Repeat-use songs (Heather Jane, Bourbon, Collide With Me) | 2 | +0.087 [−1.630, +1.805] |
| **The Apprehended (the only fresh song)** | 1 | **−0.172** (truth's amp −0.032) |

**Per song and item** (mean over sections, amps and directions; in brackets the truth's amp only).
Class is fixed per song, so these are also the per-class rows (P1's class):

| Song | Item 1 | Item 2 | Item 3 | Item 4 | Item 5 | Primary | Arm O |
|---|---|---|---|---|---|---|---|
| Heather Jane (clean) | +0.495 (+1.016) | +0.490 (+1.016) | +0.139 (+0.249) | +0.444 (+0.953) | | **+0.359** (+0.739) | −0.022 (+0.059) |
| Bourbon (edge) | −0.150 (−0.203) | −0.169 (−0.228) | −0.209 (−0.124) | −0.157 (−0.189) | | **−0.172** (−0.172) | −0.210 (−0.225) |
| Collide With Me (clean) | −0.168 (−0.131) | −0.150 (−0.143) | −0.354 (−0.499) | −0.069 (−0.048) | | **−0.197** (−0.226) | −0.283 (−0.299) |
| The Apprehended (crunch) | −0.193 (−0.030) | −0.193 (−0.030) | −0.131 (−0.038) | −0.193 (−0.030) | −0.167 (−0.029) | **−0.172** (−0.032) | −0.133 (−0.050) |

- **Heather Jane is where arm A loses, and it is where S starts closest.** Its truth (Spacey
  Grits) and its S (Low-Watt Americana) are both AC20 cleans. S's distance on s1–s3 is 1.7–2.0, the
  lowest of all sections (others 2.9–5.4). Arm A moves away from it and lands at about 4.5.
  - Over the 16 sections (the truth's amp), arm A's log ratio falls as the log of S's starting
    distance rises (correlation −0.88; arm O −0.50).
  - This is post hoc and partly mechanical: d_S sits in both terms, so noise in d_S alone makes the
    two correlate. It is a hypothesis for B2, not a finding.
- **Leaving one band out** (a sensitivity reading, post hoc): without Chris Coltraine the primary
  reads −0.178 [−0.217, −0.140] (2 bands, 1 df). Without either other band it reads about +0.09
  [−1.6, +1.8]. The sign of B1's mean depends on one band.
- **The fresh song** (The Apprehended) reads −0.172, but only −0.032 on the truth's amp. Most of
  its gain is on the two amps the truth is not on.

## Arm O and the separator's share

| Row | Bands | Mean [90%] |
|---|---|---|
| O against S (all amps; sections s1–s4) | 3 | −0.134 [−0.323, +0.056] |
| O against S, the truth's amp | 3 | −0.084 [−0.359, +0.190] |
| A − O (items 1 and 3, paired on section, amp and direction) | 3 | +0.112 [−0.222, +0.446] |

- **With a perfect stem the recipe leans closer than S** on all four songs (−0.02 to −0.28). The
  separator's share leans against arm A (+0.11). Both intervals contain 0.
- **Arm O is not shown to add little,** so B2 should keep it (the cost table in the plan's parent
  offered dropping it only if it did).

## Distance to the true preset's render

Medians of the held-half judge distance on the truth's amp (primary items for arm A):

| Song | S | Arm A (shrunk output) | Arm A (unshrunk best) | Arm O | Convention floor |
|---|---|---|---|---|---|
| Heather Jane | 1.83 | 4.55 | 4.90 | 2.19 | 1.86 |
| Bourbon | 4.69 | 3.86 | 3.21 | 3.39 | 1.85 |
| Collide With Me | 3.06 | 2.77 | 3.14 | 2.38 | 2.75 |
| The Apprehended | 3.76 | 3.58 | 3.91 | 3.58 | 3.34 |

- **Nothing lands near the truth.** The exact record reads ≤ 0.001. Every searched output reads
  2–5, about where S starts.
- **The convention floor** is the true preset rendered on the per-section measure DI (the DI level
  and average-guitar EQ convention arm A searches under; δ from −4.6 to +1.8 LU, most within
  ±1.5). It reads 0.34–1.32 of S's distance (median 0.79). A perfect preset under arm A's own DI
  convention is, by the judge, barely closer than S. Part of what arm A cannot recover here is the
  convention, not the preset. That limits how much any search through `song_bank.measure` can show
  on an exact record.

## Knob error (the truth's amp, unit scale)

Band-weighted means of |θ − θ_true| over the identifiable knobs (input gain and the amp's tone
knobs: PR12 treble and bass; SW50R treble, mid and bass; AC20 cut). "Chance" is a uniform random
setting's expected error, (t² + (1 − t)²)/2; it is a post-hoc baseline, not in the plan's readout.
Rows are (unit, knob) pairs pooled within a song (averaging knobs within a unit first gives A − S
+0.042 [−0.038, +0.121]).

| | Arm A | S | Chance | A − S | A − chance |
|---|---|---|---|---|---|
| Identifiable knobs | 0.196 | 0.158 | 0.281 | +0.038 [−0.046, +0.122] | −0.085 [−0.232, +0.062] |
| Input gain alone | 0.098 | 0.058 | 0.267 | +0.040 [−0.016, +0.097] | |
| Level knobs (volume, level, power) | 0.130 | 0.157 | 0.302 | −0.027 [−0.076, +0.021] | |
| Arm O, identifiable | 0.184 | 0.171 | 0.284 | +0.013 [−0.032, +0.057] | −0.100 [−0.208, +0.009] |

- **Arm A is not shown closer than S, and leans further** (+0.038). Both A and S lean closer than a
  random setting, undecided (S − chance −0.123 [−0.247, +0.001]).
- **Per knob** (A − S, primary items, truth's amp), the largest each way: A further on PR12 bass
  +0.120 [+0.045, +0.195] and PR12 treble +0.089 [+0.016, +0.161] (2 bands each); A closer on SW50R
  bass −0.148 [−0.386, +0.091] and SW50R level −0.124 [−0.199, −0.049] (2 bands each). So the search
  moves some knobs toward the truth and others away, by amp. (`report.json`'s
  `knob_error_minus_S` also includes items 2 and 5.)
- **The input gain** (read with δ beside it, amendment 1 item 3) moves 0.04 further from the truth
  than S's. δ is within ±1.5 LU on 14 of 16 sections, about 0.05 of the input-gain range.
- **Mics and switches** (agreement with the truth, primary items on the truth's amp): left mic type
  A 9/48, S 42/48; right mic type 0/48 for both; AC20 bright A 4/14, S 12/14; the right cab
  stays on 44/48 (S 48/48); AC20 bass/treble A 11/14, S 10/14 (the one switch where A agrees more);
  the SW50R switches 11–12/12 for both. The search changes the left mic away from the truth's far
  more often than toward it.

## The amp (not declared; descriptive)

Per (item, section, direction), with all three amps searched, which amp lands closest?

| Picked by | Arm A | Arm O | Chance |
|---|---|---|---|
| The judge on the true DI (an oracle) | 6/68 | 10/32 | 1/3 |
| The arm's own objective (search half, shrunk output) | 29/68 | 13/32 | 1/3 |
| S's distance on the true DI | 17/68 | 9/32 | 1/3 |

Per band, arm A's own objective picks the truth's amp 14/16 (Chris Coltraine), 13/32 (Rebecca
Haviland) and 2/20 (The Apprehended); 29/68 comes mostly from one band. Within a band the units
share sections, so these are not independent. They are a baseline for a declared amp readout in
B2, not a reading of amp choice.

## The switch and two guitars (a baseline for multi-section grouping)

**Switch (item 3), per side** (all amps; truth's amp in brackets):

| Song | s3 (P1) arm A | s4 (P2) arm A | s3 arm O | s4 arm O |
|---|---|---|---|---|
| Heather Jane | +0.176 (+0.438) | +0.101 (+0.060) | −0.177 | −0.001 |
| Bourbon | −0.258 (−0.260) | −0.160 (+0.012) | −0.336 | −0.070 |
| Collide With Me | −0.108 (−0.077) | −0.600 (−0.920) | −0.330 | −0.211 |
| The Apprehended | −0.274 (−0.209) | +0.013 (+0.133) | −0.131 | −0.067 |

- **Each side is scored as a single-preset section,** as the plan declares. Grouping sections into
  sounds is multi-section step 3's job. Item 3 overall reads −0.091 [−0.450, +0.268] and item 1
  +0.048. They are not paired: item 3 uses other sections (s3, s4), and s4 has another truth (P2)
  and often another S class. So whether a switch costs a section can't be read from B1. The sides'
  section-to-preset truth is stored for step 3.
- **Item 4 against item 1, paired:** −0.002 [−0.084, +0.080]. Item 1 already holds the other
  recorded guitars, so this contrast is "the second part as a rendered Q, in place of its real
  amp tracks" (plus item 4's extra leakage drops), not "a second guitar against none".
  - The interval is narrow for a reason: on The Apprehended the second DI is silent at s1 and s2,
    so its item 4 is identical to item 1. Without it: −0.003 [−0.309, +0.304] (2 bands).
  - Per song: Heather Jane −0.051, Bourbon −0.007, Collide With Me +0.099. The stems did change
    (difference energy −4.6 to +0.9 dB against the stem), and arm A did not visibly move at this
    precision.
  - Heather Jane's second DI is a double of the same part.

## Vocals and other guitars

- **No vocals (item 2) against item 1:** −0.002 [−0.006, +0.003]. This is not a precise "vocals
  cost nothing". The vocal tracks are silent in 3 of the 8 sections (The Apprehended's s1 and s2,
  Heather Jane's s2), where the stems are identical or differ by under −107 dB. Elsewhere the per-unit change is small (mean
  |Δ| 0.033 on Bourbon and Collide With Me) and averages out.
- **The Apprehended without its other guitars (item 5) against item 1:** +0.026 (1 band; mean |Δ|
  0.05). Removing the amp-recorded high-gain rhythm guitars changed the stem by about −4 dB of
  difference energy, and did not move arm A visibly.

## Checks

- **Exactness:** self-distance ≤ 0.0011 on every section and half (S 1.7–7.2), far under amendment
  1's tenth of S. The whole-track truth's slice against the section record is ≤ 0.0010. The judge lag
  is 0 (`RECORD_LAG`, as fixed in review), which the near-zero self-distance confirms.
- **C′ fold 2** is the legacy final network. Its training pool (`di_fine_structure.train_pool_bands`
  over the three caches it trained on) is 11 bands: Adam Buckley, Ale Lak, Atlantis Bound, Bernard
  Purdie Tribute All-Stars, Dom McLennon, Doom Flamingo, Eggy, Guitar-TECHS P1, Starnes And Shah,
  Swatkins and The Travelling Band. None of B1's three bands is in it. The rebuild step's assertion
  (`assert_cprime_unseen`) checks the exact band names; its session-key half cannot match the
  pool's format, so the band names are the substantive check.
- **No B1 DI was trained on:** all 12 are `known_answer` in the clean-DI inventory, and
  `assert_training_ok` refuses them.
- **Fallbacks:** 0 of 300 directions fell back to S. No distance was floored.
- **Not recorded:** the objective's activity fallback per evaluation (the plan lists it). B1's
  results store only the objective's value. B2 should store the flag.

## Renders

**17,290 renders**: menu scans 454, truth draws, checks and whole-track renders 90 (truth total 544),
S 96, and arm A and O searches 16,650 (300 directions × 55, plus 150 warm-ups). The plan estimated
about 17.4k (search 16,746 with S, as run). The pre-launch smoke run's 168 renders (53 + 115, scratch
output) are not included. `report.json` prints 17,440: each direction's count adds
the group's shared warm-up, so 150 warm-ups are counted twice. This is the same double count as the
rebuild-gap step's. Search rate: about 6.5k renders an hour on 3 shards.

## What B1 tells us, and what it cannot

- **It can show almost nothing about arm A's effect.** With 3 band clusters and t = 2.92, an
  interval of ±0.52 cannot separate a 10% gain from a 40% loss. The one fresh song is one band, with
  no interval at all. Every per-row reading above is descriptive.
- **It does show:**
  - the pipeline is exact and complete (all 300 directions, zero fallbacks, checks at about 0);
  - **the per-item spread is large and band-driven:** between-band SD 0.31 on the primary,
    against stage F's 0.069. Most of it is one band (Chris Coltraine), where S already sits near the
    truth;
  - **arm A is not shown to recover the preset's knobs better than S** (it leans further); both lean
    closer than chance, undecided. By the judge's distance its best amp is rarely the truth's
    (6/68; not declared, descriptive). Its own objective picks the truth's amp on 29/68, mostly in one band (descriptive);
  - **with a perfect stem (arm O) the recipe leans closer than S** (−0.134). The separator's share
    leans against arm A (+0.112). Neither is decided;
  - **the switch and two-guitar items** give the per-side and per-item spread multi-section
    grouping starts from. Replacing the second part's real tracks with a render did not visibly
    move arm A (paired, −0.002), and the switch can't be read against item 1 (unpaired);
  - **the measure-DI convention alone** puts the true preset at about 0.8 of S's distance, which
    limits what an exact-record test can show through arm A's DI convention.
- **The caveats stand:** in-family best case (Morgan truths on arm A's own amps, a DI already in arm
  A's EQ convention); 3 of 4 songs are repeat-use development songs; 2 of 4 have hum-flagged DIs; the
  listening check is unread.

## B2: proposed size, cost and songs

**The declared rule gives 5,654 songs.** n = (t · max(U, 0.069) / 0.03)², with U = 1.37, the 90%
upper bound of the between-band SD 0.311 (χ², 2 df). As amendment 1 item 8 anticipated, the pool
caps B2.
- **Proposed size: every fresh DI-only candidate that passes the checks, up to 4 songs.** These
  are Strobe "Maya", MekaPhil, The Timezone "GOTGF" and Perpetual Escape "Stop And Rise", each
  first checked for scope (screened like part A; Perpetual Escape is "progressive heavy rock", so
  its other tracks are gain-classed and the user listens before it is kept), for held-out use, and
  for reachability on the direct archive host. If The Timezone is the label table's Timo And The
  Timezone, the song is fresh but that band's library DIs become known-answer too.
- **Expected precision:** with B1's 3 bands, 7 bands in all. At B1's spread (SD 0.31) the half-width
  would be about ±0.23. At stage F's (0.069) it would be about ±0.05. So B2 can tell whether Heather
  Jane is an outlier, and give the fresh songs their own interval. It cannot reach h = 0.03.
- **Not proposed:** moving development bands to known-answer (the pool's third tier). Each band costs
  part C training material, and at B1's spread even 17 bands only reach ±0.13.
- **Design changes for B2's amendment** (proposed):
  - drop item 2, as a cost trade, not a finding (vocals moved units by about 0.03 and averaged out,
    but they were silent in 3 of 8 sections, over 3 bands);
  - keep arm O;
  - choose item 4's sections where the second DI plays;
  - store the activity-fallback flag;
  - count warm-ups once;
  - declare the amp readout and the S-distance dependence (Heather Jane's pattern) as B2 rows.
- **Cost per song** (without item 2): arm A 6 sections × 333 = 1,998, arm O 4 × 333 = 1,332, S 24,
  truth about 135, about **3.5k renders**. For 4 songs that is **about 14k renders**, about 2.1 h of
  search (13.3k renders) on 3 shards at B1's rate, plus about 20 min of truth and about 7 min of htdemucs, so about
  2.5 h. With item 2 kept it is about 16.6k renders. Downloads come first, one at a time, with
  31 GB of disk kept free.

**Audited 2026-10-18 by an independent agent** (approve with required changes; every number was
recomputed from the per-direction results and reproduced). Changes:
- the truths' modules (compressor 8 of 12, not 9; the amp EQ active in 11 of 12 added);
- the leakage shares per item (Bourbon 51.9%, Collide With Me 2.1% on items 1–3);
- item 1 named as holding the other recorded guitars, so item 4 is a render in place of real tracks;
- item 3 against item 1 called unpaired;
- the knob readings softened (not shown closer; chance labelled post hoc, undecided);
- "tie" replaced by "undecided";
- per-knob rows on the table's scope, both directions;
- the MUSDB18 line limited to the list;
- the declared δ, guitar-to-backing ratios, per-class labels and menu-scan counts added;
- the C′ check reworded to the band names, with the fold-2 pool listed.
