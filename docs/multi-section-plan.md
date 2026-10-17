# Many sections per track, not one crop: plan (2026-10-17)

Declared 2026-10-17. Step 1 (zero renders) has run; step 2 has not rendered anything except a
6-setting smoke test (22 renders, to a scratch folder, not used). Development data only. Code:
`learn/multi_section.py`, `learn/multi_section_run.zsh` (the runner), tests
`tests/test_multi_section.py`. Outputs under `~/ndsp-presets/learn/multi-section/`.

The user's rules apply:
- **No pass/fail bars.** Every result is an effect size with a 90% band-clustered interval (t,
  bands − 1 df), the leave-one-band-out range, and the bands above and below 0. Undecided is not
  failed.
- **No fixed render limit.** Step 2 has a declared, evidence-based stopping rule, an expected count,
  and reports what it used.

**Status:** reviewed 2026-10-17 by an independent agent: approve with 6 required changes, all
made; re-reviewed: **approved** (with the runner's wait matched to the workers' yield rule, done) ([amendment 1](#amendment-1-2026-10-17-review-before-any-step-2-render), which governs where
anything differs).

## Why

- **Today each part is one 10-s crop,** chosen by crop rule 2 (where the DI plays most) or, for sets
  1–2, by the older loudest-mix rule. The judge scores it on two halves (A 1.0–5.5 s, B 5.5–10 s).
  Every search, every comparison and the product's own search fit one crop.
- **The user's idea (2026-10-17):** cut each guitar track into every 10-s section where the guitar
  plays, use them all, and search for the preset that fits them all. In the product: separate the
  guitar, cut the stem into playable sections, find the preset that fits all of them.
- **The user's caution:** several guitars, and effects or amp changes mid-song, would make one
  whole-song preset an average of different sounds. So the design must find sound changes and handle
  them: group sections into consistent sounds with a preset per group, or flag them. Later, song
  information researched on the web (how many guitars, which sections) is a prior (a product-side
  step; here only an input hook).
- **What is not known, and step 2 measures first:** whether settings searched on one section carry
  to other sections of the same track at all (with the true DI, so the rebuild can't confound it),
  and whether fitting three sections at once carries better than fitting one.

## Step 1: sections (zero renders; run 2026-10-17)

**The rule** (`learn/multi_section.py`, constants at the top):
- **The session** is loaded as the crop builder does (`research/build_validation_crops.py`): 48 kHz,
  mono mean, first-sample alignment, the DI's length defines the session, the amp track zero-padded or
  cut. Every part's stored crop is reproduced from the loaded tracks to within 1e-5 (asserted).
- **The grid:** 10-s windows every 5 s from the session start.
- **A frame plays** when within 40 dB of the DI's loudest frame over the whole session (crop rule 2's
  frames: 2048 samples, hop 1024).
- **A section passes** when at least 80% of its frames play, and at least 60% of each judge half's.
- **The material counted** is the passing windows that don't overlap (greedy, earliest first).
- **Per section** (passing ones): the guitar-to-backing ratio in the full mix (the part's amp track
  against every declared mix track except its own amp tracks, vocals included; dB); the tone curve
  (the amp track's third-octave spectrum less the DI's, 100 Hz–8 kHz, on frames where the DI plays,
  after the part's lag, mean removed) with its level offset; the tone curve's distance (RMS dB) from
  the part's median curve, and between its own two halves (a within-section noise floor).
- **Bleed:** the [bleed audit](audits/bleed-2026-10-16/README.md)'s worst flag over the part's crop
  halves (its model is per crop; it is not re-run per section, see Limits).
- **Low SNR:** a section whose guitar-to-backing ratio is below −15 dB (about 10% of sections).

**The pool:** the label table's 59 clean and crunch development parts less stage F's 21 fresh parts
(used once; never touched here) = **38 parts in 17 bands** (24 of them step 3's). No held-out part:
no Guitar-TECHS P3 row, no set 4–6 part, no held-out session (asserted in the tests).

**What it found:**
- **Material: 507 non-overlapping playable sections, 5,070 s, against 380 s as single crops: about
  13× the audio.** Median 13.5 sections per part (0 to 38). On step 3's 24 parts: 3,550 s against
  240 s.
- **30 parts in 13 bands have at least 4 sections** (3 to search, at least 1 held out); 20 of them are
  step 3's. 27 have 6 or more.
- **Crunch is thin:** of the 7 crunch parts, only 2 (Magician's Nephew, Diesel13) have 4 or more
  sections. The crunch parts in this pool are fills and solos (Today's The Day E10, femme E3, Prodigal
  E5, Nosso Mundo E03: 2–3 sections; Prodigal E4: none passes, it plays at most 24% of any window). A finer grid (1 s,
  0.5 s) adds no eligible part (checked on the 10 parts with 1–5 sections).
- **The guitar sits low in the full mixes:** median guitar-to-backing −7.9 dB (5–95%: −18.5 to
  −2.5); 98% of sections are below 0 dB, 30% below −10 dB, 10% below −15 dB.
- **Tone curves vary within a track more than within a section on some parts** (statistics over the
  non-overlapping sections): median distance from the part's median 1.19 dB (90th percentile 3.55),
  against a half-to-half noise floor of 1.63 dB median (the halves are 4.5 s, so noisier). The tone
  curve's own frame rule is per section (4096-sample frames within 40 dB of the section's loudest),
  not step 1's session-wide activity rule. Cambridge parts are steady (median 0.71 dB); the
  Telefunken live-room parts vary more (1.55 dB), and their high-bleed parts most (Gym Hours GTR 1 up
  to 10 dB, First Offering GTR 1 9.6 dB, Hikikomori 12.6 dB): bleed and sound change are confounded
  there.
- **A clear sound change on a Cambridge part:** magilla ElecGtr1DT (Turbosauro, the band that carried
  most of the ceiling extension's gain) has two tone shapes: 5–30 s with the 100 Hz band near −4 dB,
  35–45 s a transition (−0.9 to +2.5), and 85–105 s and 185–205 s with it near +8 to +17 dB
  (half-to-half noise there 0.2–1.9 dB). Whether that is a
  rig change or the playing (palm muting, register) is not separable from the tone curve alone.
- Files: `sections/<part>.json` (every grid window, its activity, and for passing ones the
  measures above).

## Step 2: does a section's search transfer? (the cheap first measurement)

**The question.** With the true DI, does a preset searched on one section fit the track's other
sections, and does a search that fits three sections at once fit held-out sections better?

**Units and data.**
- **Parts:** the 30 pool parts with at least 4 sections (13 bands; 28 clean, 2 crunch).
- **Sections per part:** of its non-overlapping passing sections, up to 6 spread evenly by index
  over them in time order (all if 4–6); roles by a seeded shuffle (`random.Random("20261017|<part>")`): 3 search sections
  s1–s3, the rest (1–3) held out.
- **The DI:** the measure DI, built once per part: one EQ to the average guitar
  (`average-fold2.npy`, `confirm_run.AVERAGE`) from the part's chosen sections together, and one gain
  putting them together at −22.9 LUFS. Unlike a crop's measure DI (EQ and level per crop), the
  sections keep their relative level and the guitar one EQ: one guitar, one track.
- **The amp:** per part, the amp whose best dry menu preset is closest in the label table's stored
  menu (`label-table/<part>/menu.json`, `flat`, mean of the halves; zero renders). One amp per part.
- **The start:** S, the product's starting preset for the part's class on that amp
  (`knob_ceiling.START`), made dry by the menu's rule.
- **A section's score:** the mean over its two halves of the log judge distance (`knob_ceiling.judge`,
  the part's stored `judge_lag`); a refused half makes it infinite (worst). Roles are assigned first; a held section refused for
  S is dropped; a part with a search section refused for S, or no held section left, is skipped
  (and counted).
- **Renders:** `knob_ceiling.Renderer` (Morgan, `isolate=True`), one warm-up per part. No audio is
  kept (only the two half distances per render), so the 0.25-s trim is moot: the judge starts at
  1.0 s.

**The four searches per part,** each from S, `knob_ceiling.knob_search` over K_S's space (input
gain, the amp's knobs and switches, both mics), **150 distinct settings each** (K_S's budget), the
same seed for all four (so they differ only in their objective):
- **single1, single2, single3:** each minimises one search section's score;
- **multi:** minimises the mean score over s1–s3 (3 renders per setting).

Each search's incumbent (best on its own objective) at **25, 50, 100 and 150 settings** is scored on
every kept section. Every render is cached per part (`parts/<part>/cache.jsonl`), so a stopped
worker resumes exactly; a re-render of S on the first section at the end of each part must agree
within 0.005 (log), else the part is dropped from the readout and counted.

**What is reported** (per part, then band-weighted; held = mean over held sections of score − S's
score, a log ratio against S):
- **P (primary): multi − mean of the singles, on the held sections, at 150 settings.** Negative: the
  three-section search lands closer on sections neither searched.
- **P at equal renders (a conservative lower bound):** multi's incumbent at 50 settings (150
  renders) − the singles at 150. Multi's search was budgeted for 150 settings, so at 50 it is still in
  its main stage (52 settings) and has tried no mic alternatives or restarts; a search budgeted for 50
  would do better.
- **Each against S on the held sections:** multi, the singles' mean. How much a single section's gain
  carries: the singles' gain on their own section against on the other search sections and on the held
  ones (descriptive ratio of the band-weighted means).
- **How much sections disagree** (the first estimate of within-track sound change): for each ordered
  pair of search sections (i, j), the regret r_ij = score of single_i's settings on s_j − score of
  single_j's settings on s_j; per part its mean and maximum; the share of pairs where single_i's
  settings land farther than S on s_j; and the settings' distance between searches (mean unit
  difference, mics and switches counting 1).
- **Does the zero-render tone curve predict the disagreement?** Spearman, over search-section pairs
  (pooled, descriptive), between the two sections' tone-curve distance and their symmetric regret.
- **The curve** at 25, 50, 100 and 150 settings for P, P at equal renders, multi and the singles.
- **Rows:** all (declared); clean only; crunch (2 parts, descriptive); no high bleed; no moderate or
  high bleed; Cambridge only. Leave one band out for each.

**Stopping (evidence-based).** Parts run in batches, step 3's parts first: batch 0 is step 3's 20
eligible parts (10 bands), batch 1 the other 10 (7 bands: 3 new, and 4 of batch 0's bands, whose
non-step-3 parts join them there). After each batch: stop if
P's 90% half-width is at most 0.02 (the size fresh-mix effects are read at), else run the next batch;
the pool's end stops it. Each search is fixed at 150 settings (the true-DI ceiling's search took most
of its gain by then; its extension added −0.024 over 150 more); the curve shows whether the four
searches were still moving.

**Expected renders and hours.** About 970 renders per part (S on up to 6 sections; 3 × 150 singles;
150 × 3 multi; about 60 more for the incumbent table, less what is cached): **about 19.4k for batch 0
and 29k if batch 1 runs.** At about 1.5–2 s per render per process and 2 processes, about 5 h for
batch 0 and 7.5 h for both, plus whatever time the rebuild-tone run's renders take (its workers go
first, below). Disk: under 50 MB (no audio kept).

**The machine.** CPU only, 2 worker processes with one thread each while the rebuild-tone run trains
on the GPU. `learn.multi_section run` is added to `local_objective.RENDERS`, so every runner counts
it against the 3-process cap; each worker also waits on `local_objective._wait_cap` before each part.
**The rebuild-tone run goes first:** a worker exits (code 3) at its next render once any
`learn.rebuild_tone render` or `score` process exists, and the runner waits until none does (polling
every 2 min) before restarting the workers, which resume from their caches. The rebuild-tone shards
see the exiting workers for at most one of their 60-s cap polls. Disk guard 31 GB (exits, code 4).

**How it will be read** (not bars):
- **P clearly below 0:** fitting several sections carries better to unseen sections of the same
  track; multi-section search becomes the default unit for the next steps (step 3, below).
- **P about 0 with singles carrying most of their own gain to held sections:** one section is enough
  on these parts; the extra sections then serve as more held-out scoring and more training material,
  not as a search objective.
- **Singles losing much of their gain on other sections (large regrets):** sections disagree, and the
  pairs with the largest regrets (and their tone-curve distances) are the first candidates of a
  within-track sound change, for step 3's grouping.

## Step 3: then (declared, not run now)

1. **Multi-section arm A on rebuilt DIs** (the product's route): C′ rebuilds each section from the
   htdemucs stem; the search fits the mean over k sections; scored on held-out sections and on fresh
   full mixes (the only yardstick). Needs full-song separations of the development sessions (htdemucs,
   about 20–28 s per 10 s on the CPU; separations need the renderer idle).
2. **The product-side section rule:** the same grid on the separated stem, a frame playing when within
   40 dB of the stem's loudest **and** the stem above the mix residual by a declared margin; checked
   on development against the DI's activity (agreement, and how much of the DI's material it keeps).
3. **Section-level held-out scoring** for every later arm-A test: several sections per part, so a
   part's score no longer rests on one crop.
4. **Extra sections in rebuild training:** about 13× the real-track audio per part for C′ and its
   fine-tunes, with the fold rules unchanged (no test part's sections in training).
5. **Grouping sections into sounds:** cluster a part's sections by the tone curve (and by per-section
   optima where renders are spent), a preset per group; flag a part as mixed when the groups differ by
   more than the half-to-half noise. Step 2's regret–tone correlation says whether the zero-render
   curve is worth using; on a song (no DI) the curve must come from the rebuilt DI, which is its own
   question.
6. **Several guitars in one stem:** the separated "guitar" stem mixes every guitar. In development
   each part has its own amp track, so mixed-guitar stems can be simulated by summing the parts' amp
   tracks of one session (and their DIs for the true-DI control); measure how a one-preset search
   degrades as a second part is added, and whether grouping recovers it.
7. **The web-research hook:** the product's research (number of guitars, which sections are clean or
   driven, solos) enters as a prior on the number of groups and their sections; it is checked against
   the audio (the grouping above), never taken over it.

## Limits

- **True DI and amp tracks:** step 2 says whether sections agree on a perfect input; the product's
  rebuilt DI and separated stem add their own errors (step 3).
- **Mostly clean:** 28 of 30 parts; crunch is descriptive.
- **One amp per part,** chosen from stored menu scores.
- **Bleed per section is not modelled;** the part's flag from its crop is used for the rows. The
  Telefunken tone-curve spread is partly bleed.
- **The tone curve** is a linear ratio; a driven amp's curve also moves with playing level and
  register, so a curve change is a candidate, not a proof, of a rig change.
- **The measure DI is built per part,** not per crop, so step 2's scores are not on the same scale as
  earlier crop results; comparisons are within step 2.
- **Reuse:** step 3's 24 parts are heavily used development parts; the 6 others (and the sections
  outside the crops) are less used. Every figure is a development reading.

## Amendment 1 (2026-10-17, review, before any step-2 render)

The independent review approved with 6 required changes; all are made, and this amendment governs.

1. **The amp when the stored menu is refused.** All 10 of batch 1's parts have refused menu halves in
   the label table (5 on both halves of every preset). The rule is now: per preset, the mean of its
   finite halves; the amp with the closest best preset; **PR12 when every stored score is refused**
   (Measurements, Hikikomori, Signs E6, Lost Alive, Until I Get Back). Amps over the 30 parts: SW50R
   13, PR12 12, AC20 5. Tested on every eligible part's stored menu.
2. **Renders counted across resumes:** each part's cache file now records warm-ups too, and a part's
   renders are its cache lines (every render, the S repeat and the warm-ups), not the last session's.
3. **The cap outside this worktree:** the `local_objective.RENDERS` line is committed with the code and
   proposed for main on its own (PR #209; superseded as the launch condition by amendment 2), so a runner started from main (after a pull) counts these
   workers too. The worktree's branch isn't switched (the rebuild-tone run uses it).
4. **A floor for the regrets.** A regret mixes real differences between sections with the search's
   own path (two searches of one section rarely land on the same settings). **A fifth search,
   single1b,** searches s1 again with seed + 1 (150 renders per part, about 15% more). Reported beside
   the regrets: the gap between single1 and single1b on s1 (the absolute difference), how much
   single1's regrets on s2 and s3 move when single1b's settings are used instead, and single1b −
   single1 on the held sections. A regret is read as a sound difference only above that floor.
5. **Text matched to the code:** P at equal renders is a conservative lower bound (above); batches are
   not whole bands (above); the refused-section rule (above); "spread evenly by index" (above).
6. **Refusals can't leak into the readout:** every per-part number that touches a refused score is
   None (as the held gain already was); the report lists the parts whose P is None.

Also taken from the review's suggestions: the tone-versus-regret Spearman also within parts (each
part's pair means removed) and on Cambridge alone (the Telefunken bleed raises both measures); each
held section's distance in time to the nearest search section is reported (some sit next to one);
the workers also yield to the rebuild-tone run's CPU torch steps (`rebuild_tone_train gate`,
`rebuild`); the runner stops if there is no batch; a cut last line in a cache file is skipped;
the step-1 text above is corrected (magilla's spans, Nosso Mundo, the tone-curve frame rule, the
statistics' basis).

**Expected renders, revised:** about 1,120 per part: about 22.4k for batch 0 and 33.6k for both; about
5.5 h for batch 0 and 8.5 h for both at 2 processes, plus the rebuild-tone run's turns.

## Amendment 2 (2026-10-17, before any step-2 render)

PR #209 (the `RENDERS` line on main) could not be merged from this session; it waits for the user.
So the cap is made to hold on this step's side, whatever other checkouts' runners count:
- **Before every render,** a worker steps aside (exits, code 3, resuming later from its cache) when
  any separation runs, or when foreign render processes and this step's workers together exceed 3.
  A foreign render process is any python running a `learn` module with a render-like command (`run`,
  `render`, `search`, `probe`, `pregain`, `choose-rot`, `score-targets`, `score-songs`, `c-start`) or
  a separation; training (`train`, `fit`) and scoring don't count, as before.
- **The runner starts workers only when** nothing it yields to runs and two workers fit under the cap
  (`learn.multi_section clear`), polling every 2 min.
- So a runner that doesn't know this step can start up to its own cap; these workers leave within one
  render (about 2 s).


Re-reviewed: **approved**. From its optional notes: `clear` exits 10 for "not clear", so a crash
(any other code) stops the runner instead of waiting forever; `control` and `cross` (old
knob-ceiling commands that render) count as foreign renders.
