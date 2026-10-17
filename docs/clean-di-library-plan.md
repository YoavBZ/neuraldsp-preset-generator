# A clean DI library and known-answer test songs: plan (2026-10-17)

Declared 2026-10-17, before the full screen ran and before any listening page was built. The user
approved a self-rendered-dataset track on 2026-10-17. It has two parts:

- **Part A**, now, with zero renders: a cleaned library of the raw guitar (DI) tracks we are
  allowed to use, cut into 10-s sections, each screened for hum, hiss, clipping, DC, dropouts,
  bleed and near-silence. A blind listening page lets the user check the screens.
- **Part B**, a declared later stage: known-answer test songs. A DI from a multitrack session is
  rendered through a chosen Morgan preset and mixed back into the session. Then we ask whether arm
  A's adopted recipe recovers that preset. Its renders wait until the overnight runs end.

The rules of [`research/ml-plan-2026-10.md`](research/ml-plan-2026-10.md) section 5 apply, with the
user's rules of 2026-10-16: estimates with intervals, no pass/fail bars, evidence-based stopping,
renders and hours declared, and licence-clean open-source tools only. Code:
`learn/clean_di.py`, tests `tests/test_clean_di.py`. Ledger: `clean-di-library` in
[`dev-test-ledger.json`](dev-test-ledger.json). Data: `~/ndsp-presets/learn/clean-di/`.

**Status:** declared, then reviewed 2026-10-17 by an independent agent: approved with 12 required
changes for part A and 4 more for part B's amendment. All are made as
[amendment 1](#amendment-1-2026-10-17-review-changes-before-the-full-screen) below, which governs
where the two differ (the inventory counts, guards, split, hum, clipping, bleed and listening
design are restated there). The full screen ran after amendments 1–2 ([results](clean-di-library-results.md)); the listening answers are pending.

## Why

- Every test so far scores a preset against a real amp track. That track carries the room, the
  mic, bleed and an unknown rig, so the right answer is never known exactly. A rendered song has
  a known answer: we know the preset, so the true render can stand in as the record, and the
  knob error can be measured.
- Renders and training are only as good as the DIs that feed them. Known example: the noise in
  Prodigal's parts is DI hum, not the amp. Nothing so far screens the DIs themselves.
- The DIs already on disk are worth more than the 59 label-table parts. The label table keeps
  only parts whose amp track is the same take. Every DI of a development session is usable as a
  DI, paired or not.

## Part A: the library (zero renders)

### What goes in (the inventory)

`python -m learn.clean_di inventory` writes `inventory.json`. It lists every development
guitar DI on disk, and every exclusion with its reason.

| Source | DIs | What it is |
|---|---|---|
| Sets 1–2, development sessions (`docs/validation-datasets.json`) | 85 | every part's DI, paired or not, plus guitar DIs the catalogue lists as files only (Today's The Day ElecGtr03/08) |
| Set 3, development sessions (`docs/validation-set3.json`) | 59 | every DI of a development session, kept part or not, plus the catalogue's unpaired DIs (Storm Of Particles 1–3, Szymon Skiba 1–2, Wickerman 8) |
| Downloaded with set 3, never declared | 11 | Dark Ride "Dead Enemies" (8 DIs, no amp tracks; never used) and The Apprehended "Still Flyin'" (3 DIs, no amp tracks; never used; **part B**) |
| Guitar-TECHS P1 and P2, direct-input files | 87 | chords, scales, single notes, techniques (P2); CC BY 4.0; development (`learn/di_pool.py`, `docs/di-domain-pilot-plan.md`) |
| **Total** | **242** | 32 bands or players; 239 library, 3 known-answer; 230 may train |

**Left out, never read:**
- every held-out session of sets 1–2 (`split: held_out`), and every session of set 3's six
  held-out bands (spent by the 2026-10-08 confirmation; excluded from training);
- all of Guitar-TECHS P3, development excerpts too, since its excerpts share one recording with
  the held-out ones (the ledger's "no Guitar-TECHS P3" rule);
- sets 4, 5 and 6 (set 6 is MedleyDB): held out for the ML plan's step 7;
- Dunning Kruger "Sascha" (a set-3 held-out band, downloaded but undeclared);
- Umphrey's McGee "Crucial Taunt": its "DI" is a speaker-simulated line-out after the amp, not a
  raw DI ([fresh-di-amp-multitracks-2026-10.md](research/fresh-di-amp-multitracks-2026-10.md)).

**Guards, which fail closed:**
- every DI path goes through `set3.is_held_out` (sets 1–3, Guitar-TECHS P1) and
  `set4/5/6.covers`;
- the two undeclared downloads and Guitar-TECHS P2 have their band checked against every
  held-out list;
- a path the guards do not know raises an error.

**Tags per DI:**
- source, set, band, song and part;
- the label table's or set 3's gain class for the part, where it was classed (76 DIs; the rest
  `null`);
- set 3's genre;
- the licence text (below);
- `split` (`library` or `known_answer`) and `training_ok`;
- notes, such as "not a same-take pair", "no amp track in the catalogue", "stage F part (used
  once)", "band has a held-out song", or the catalogue's set-3 clipped-DI count.

**Who may train.** Set 1's Bourbon, Collide With Me and Heather Jane are development songs. But
their bands' other songs (57 Chevy, That's How I Got To Memphis) are held out. So those 7 DIs are
`training_ok: false`, as `learn/di_pool.py` already treated set 1. Stage F's 21 parts have now been
used once, as arm A's fresh draw. They stay in the library, tagged, so a later fresh draw can
leave them out.

**Licences** (recorded per DI):
- **Cambridge-MT:** educational use only, no commercial use.
- **TELEFUNKEN Live From The Lab:** home-studio and educational use only, with its attribution
  line.
- **Guitar-TECHS:** CC BY 4.0.

All three are as the validation sets already record them. Nothing here is redistributed.

### Sections

Each DI is cut on the multi-section grid (`learn/multi_section.py`, step 1):
- 10-s windows every 5 s at 48 kHz;
- a frame plays when it is within 40 dB of the DI's loudest frame;
- a section counts when 80% of its frames play, and 60% of each judge half's.

These are the same rules as every crop. The pure functions are copied into `learn/clean_di.py`,
because multi_section is not on main yet. A test checks they match it whenever it is importable.
**Near-silence** is this activity rule: a window that fails it is not a section.

### Screens (declared thresholds)

Every section that passes the activity rule is measured. A **flag** excludes the section; a
**tag** only describes it. Levels are relative to the section's **playing level**: the median dB
of its frames that play. That is the level a render normalises to, so a DI recorded quietly is
judged by its noise relative to the guitar, not by absolute dBFS.

| Screen | Measure | Flag | Tag |
|---|---|---|---|
| **Hum** (50/60 Hz and harmonics) | Track-wide: the 10th percentile of each bin's power over the DI's frames (16384-point, hop 4096), so a line must persist; a harmonic k·f0 (k ≤ 8) counts when it stands ≥ 10 dB above its ±20-Hz neighbours; mains = the one (50/60) with more such lines. Per section: those lines' power above the neighbours in the section's 10th-percentile spectrum | ≥ −55 dB re playing | ≥ −70 dB ("slight hum") |
| **Hiss** (broadband floor) | Per section, the same 10th-percentile spectrum, median-smoothed over 25 bins (lines removed), summed over 6–16 kHz, where a DI's guitar is weak | ≥ −65 dB re playing | ≥ −75 dB ("slight hiss") |
| **Clipping** | Flat tops: runs of ≥ 3 consecutive native-rate samples at ≥ 0.999 of the file's peak (set 3's catalogue rule, per position) | ≥ 1 run in the section when the file peaks within 0.1 dB of full scale; ≥ 3 runs otherwise | — |
| **Dropouts** | Runs of exact digital zero of 1–200 ms with both 10-ms neighbours within 30 dB of the playing level | ≥ 1 | longer zero runs with a loud end are edits: "hard_cut" |
| **DC** | \|mean\| re the section's RMS | — | ≥ −30 dB ("dc"; fixed by a 5-Hz high-pass, which cannot touch a guitar's lowest note) |
| **Bleed into the DI** (other instruments, including other guitars' amp tracks) | At 16 kHz, 1024-point frames. On frames where the DI rests (more than 40 dB under its loudest) and the other track plays (within 30 dB of its loudest), the mean magnitude-squared coherence over 100 Hz–6 kHz, with bins within 3 Hz of any 50/60-Hz harmonic left out. A track is a bleed source when coherence exceeds its 1/N bias by > 0.05, read on ≥ 50 frames. The bleed in each section is then predicted through the transfer function fitted on those frames | predicted bleed ≥ −40 dB re the DI in the section | — |
| **Amp-track leakage** | The DI's own amp and mic tracks are left out of the bleed regressors: the DI's note tails are the same guitar, so they would read as "leakage". Other guitars' amp tracks are in. A DI that is really a post-amp line-out cannot be told from the audio by these measures; Crucial Taunt is excluded by name, and the listening check asks about distortion | — | — |

**Style tags:**
- onsets per second (spectral-flux peaks): **sparse** under 2/s, **dense** over 5/s, **medium**
  between;
- the median spectral centroid of the playing frames.

These describe; they do not screen.

**How the thresholds were set.** Before declaring them, I measured nine DIs as a calibration
probe: Prodigal ElecGtr1, 3 and 5; Drag Me Down ElecGtr4; Gym Hours GTR 1; Bloomlight; one
Guitar-TECHS P1 chord file; Wickerman ElecGtr1; Apprehended ElecGtr03. What it showed:
- The track-wide line test finds clear 60-Hz lines in Prodigal (38–40 dB prominent) and in
  Guitar-TECHS P1 (47 dB).
- A whole-track mean spectrum does not work as a hum measure: sustained notes near k·f0 read as
  hum (Drag Me Down read −16 dB). Hence the percentile spectrum and the track-wide line test.
- The first bleed version fitted on all of the DI's rest frames. It flagged shared electrical
  noise between two silent Prodigal DIs as "bleed" (predicted −7 dB). Hence the rule that the
  other track must be playing.
- Crest factor (a "processed DI" idea) read 6–10 dB on plain DIs, so it is not used.

The flag levels are a judgement about audibility after an amp: a crunch amp compresses the
guitar but not the noise in its rests. The listening check below is what tests them.

### Hum removal: evaluated, adopted only if it leaves the guitar alone

Hum is the one fault that might be removed rather than cut. The fix is zero-phase, 1-Hz-wide
notches at the track's own hum harmonics. The mains f0 is estimated to 0.01 Hz from a 2^18-point
spectrum. Broadband hiss has no comparable fix: any denoiser changes the guitar, so hiss-flagged
sections are only cut.

`python -m learn.clean_di hum-fix` measures the fix:
1. **Collateral, on hum-free DIs.** Each hum-flagged DI's notch set is applied to 20 DIs with no
   hum line (seeded draw; the guitar alone). We record the largest third-octave change (40 Hz–8
   kHz) on playing frames and the removed power re the signal.
2. **Effect on the hum.** Each flagged DI's hum, re-measured after the fix.
3. **The ear.** A/B trials on the listening page (below).

The fix is adopted, and hum-flagged sections enter the library marked `fix: hum_notch`, only when
all three hold:
- on hum-free DIs, the collateral moves no band by more than 0.1 dB and removes less than −50 dB;
- the fixed sections' hum falls under the flag level;
- the listener hears no guitar change on any notched trial.

Otherwise hum-flagged sections stay out. Either way the manifest says which.

### The listening check (blind)

`python -m learn.clean_di listen build` writes
`~/ndsp-presets/listening/di-clean-1/di-clean.html`. The key goes to `private/key.json`. Built
like `learn/build_bleed_damage.py`:
- each clip is AAC in a data URI, padded with a random-length mp4 `free` box;
- letters and order are seeded;
- the page carries no source, band, file or flag names, and an assertion checks that;
- all clip URIs are distinct.

**Part 1, "What do you hear?" (24 clips, 8 s each, from the middle of a section).**
- **12 flagged sections:** at most 4 per flag type, at most one per DI, seeded. Every flag type
  that occurs gets a share.
- **10 passing sections:** at most one per DI, seeded, spread over Cambridge, Telefunken and
  Guitar-TECHS.
- **2 repeats**, one flagged and one passed. They describe consistency only and never discard
  answers.

Every clip is levelled to −20 LUFS as one block, which keeps noise relative to the guitar. The
order is shuffled, and a repeat is never next to its source. For each clip the listener picks
every problem heard: **ok** (none), **hum** (hum or buzz), **hiss** (hiss or noise), **click**
(clicks, dropouts or crackle), **dist** (distortion or clipping), **bleed** (other instruments),
**other**.

**Part 2, "Hum removal" (if any section is hum-flagged).** Up to 6 A/B trials: a hum-flagged
section, original against notched, with the notched clip's letter balanced and seeded. Plus one
null trial with A = B = original. Two questions:
- which has **less hum**: A, B or same;
- does **the guitar** sound different apart from the hum: no, little or lot.

**Answer format**, one line, copied from the page:
`1ok 2hum 3hiss+click ... H1A-no H2same-little`.

**Reading, descriptive.** Answers are trusted as given (the user replays clips carefully). The
reading is:
- per flag type, how many flagged clips the listener named with that problem;
- for passing clips, how many the listener named any problem in, and which;
- the repeats beside their sources;
- for Part 2, how often the notched clip was heard as having less hum, and the guitar-change
  counts.

Where the ear and a screen disagree, the screen changes, as a dated amendment here, before the
manifest is used for anything:
- a heard problem on a passing clip tightens that screen, or adds one;
- a flagged clip heard as "ok" loosens it.

### Output: the manifest

`python -m learn.clean_di manifest` writes `manifest.json` (data root, with a sha256 recorded in
the results). It has one row per section that passes the activity rule. Each row carries:
- the measures, its flags and tags, and `clean` (no flag);
- its DI's tags: source, set, band, song, part, gain class, genre, licence, split and
  `training_ok`;
- its style tags, and `fix` (`dc_highpass`, `hum_notch` once adopted);
- `disjoint`: the greedy earliest-first non-overlapping choice among the clean sections, which
  is the material counted.

`assert_training_ok(paths)` refuses three kinds of DI:
- known-answer DIs;
- set-1 DIs whose band has a held-out song;
- anything outside the inventory.

### Cost

- **Renders:** 0.
- **CPU:** one process at `nice 19` with BLAS/OMP at 2 threads; about 10–15 minutes for the screen
  (measured: 4 sessions with 10 DIs in 55 s) and a minute for the page.
- **Disk:** under 50 MB of JSON plus the page.
- It never starts while a separation holds the machine, and does not add a render process. The
  overnight runs keep their 3 render slots.

### Tests (`tests/test_clean_di.py`)

The pure functions are unit-tested with synthetic signals:
- clip runs and the full-scale rule;
- dropouts against hard cuts;
- hum lines found on a synthetic 60-Hz series and not on a sustained note near 120 Hz;
- the percentile floor;
- the hiss band;
- coherence on a planted crosstalk against independent noise;
- the section flags;
- the notch's collateral on a tone between harmonics;
- the inventory's guards: a held-out path raises, a known-answer DI is refused by
  `assert_training_ok`, and P3 raises;
- the listening draw, letters, answer parsing and scoring;
- parity with `learn.multi_section` when it is importable.

The page build reads audio and is not unit-tested, like the other builders.

## Part B: known-answer test songs (a declared later stage; renders after the overnight runs)

### The question

From a full song mix with a guitar whose preset is known, how close does arm A's adopted recipe
land to the truth? The recipe is fixed (rebuilt-DI main stage, 52 renders, shrink 0.5, fallback to
S, htdemucs stem). Asked with and without vocals, and on two outcomes:
1. the held-half judge distance from the true DI's render through the recovered preset to the
   truth render (the record here is exact), as log(d_A / d_S) against the class's starting preset
   S;
2. the knob error: the mean |θ_A − θ_true| over the amp's continuous knobs in normalised units,
   against |θ_S − θ_true|. Read only when A's amp is the truth's amp; amp misses are counted
   separately.

A second arm, **O** (oracle stem), runs the same recipe with the isolated truth render as the
stem. It splits the separator's share of the error from the rebuild's and the search's.

### The songs and the split

**The pool, in order:**
1. **Fresh DI-only sessions**, never used, never trained on: The Apprehended "Still Flyin'"
   (on disk: 3 DIs, 46 tracks with vocals). After the overnight runs end (from about 10:00–14:00
   on 2026-10-18), the research report's candidates may be downloaded: Strobe "Maya", MekaPhil,
   and The Timezone "GOTGF". All are Cambridge-MT, educational licence. Downloads are one at a
   time, with free disk kept at 31 GB or more. If The Timezone is the label table's Timo And The
   Timezone, its song is still fresh, but that band's library DIs are then marked known-answer
   too.
2. **Development songs our networks never trained on:** set 1's Bourbon, Collide With Me and
   Heather Jane. Their real amp tracks are replaced by the render. They are already
   `training_ok: false`, and C′ never saw set 1 (`learn/di_pool.py`).
3. **Only if B1's power reading asks for more songs:** a seeded draw of whole non-metal
   development bands. They are declared in an amendment before any of their renders and moved to
   `known_answer` in the inventory, which takes their DIs out of all future training.

**The split, asserted:**
- every part-B DI has `split: known_answer` in `inventory.json`;
- `assert_training_ok` refuses it;
- part B's runner asserts each item's DI is known-answer, and asserts the C′ fold it uses never
  trained on the item's band (`set3.fold_for_band`).

### Presets (realistic, no metal)

- **Classes:** clean, edge-of-breakup and crunch.
- **The truth for an item:**
  - a Morgan factory preset on one of arm A's amps (PR12, SW50R, AC20), of the item's class, and
    not the class's starting preset S;
  - each continuous knob moved by a seeded uniform offset within ±0.15 of its range, clipped;
  - switches kept.
- **The class check:** each truth render's class is checked with the project's gain-class
  measure, and a truth that leaves its class is redrawn (seeded).
- **Edge-of-breakup:** a crunch preset with its gain knob drawn from the lower half of the crunch
  presets' range.

### Song construction

- **Clean sections:** only the DI's clean sections from part A's manifest are used, and only if
  the listening check has been read.
- **Rendering:**
  - the whole DI is rendered (isolate=True), after 0.25 s of silence is prepended;
  - the first 0.25 s is trimmed, and the plugin's 52-sample latency is compensated;
  - the render is level-matched (LUFS over the DI's playing frames) to the real amp track of
    that part for development songs. For DI-only songs it is set to a guitar-in-mix ratio of
    −8 dB against the backing, the median of the development sections (multi-section step 1:
    971 sections, quartiles −10.3 and −6.3 dB).
- **Mixes:**
  - the session's other tracks are summed, less every guitar amp/mic track of the rendered parts
    and less all DIs;
  - two mixes: with vocals and without (vocal tracks by name, as the catalogues list them).
- **Item kinds per song:**
  1. **single:** one preset for the whole part;
  2. **switch:** two presets, switched at the section-grid boundary nearest the song's middle at
     which the DI rests (a 50-ms crossfade if it does not rest);
  3. **two guitars:** a second DI of the session through a different preset, mixed in.

  Kinds 2 and 3 carry the section-to-preset truth that multi-section's step 3 needs
  ([multi-section-plan.md](multi-section-plan.md)). Part B only scores arm A on single-preset
  sections; grouping is that step's job.

### Power and cost

- **Unit:** the song (clustered like bands; a song's items share a player and a guitar).
- **Estimand:** the song-weighted mean log(d_A / d_S), with a 90% song-clustered t interval.
- **The spread to expect:** stage F's H − S read −0.028 [−0.064, +0.008] over 12 bands, which
  implies a between-band SD of about 0.069.
- **Songs needed for a 90% half-width h:** n ≈ (t·0.069/h)². That is about 10 songs for h = 0.04,
  17 for h = 0.03 and about 35 for h = 0.02.

That is why B starts as a pilot. B1 is 4 songs (Apprehended, Bourbon, Collide With Me, Heather
Jane; 3 bands). It measures the known-answer SD, which may be smaller than the real-record SD,
since the record is exact. A dated amendment then sets B2's song count from that SD for h = 0.03,
capped by the pool. Stopping is evidence-based: B2 stops when the interval's half-width is 0.03
or less, or the pool runs out.

**Renders per song:**
- Per section searched: 3 amps × 2 halves × 55 renders, plus 12 warm-ups, is about 342 per arm.
- Per item: 2 sections and arms A and O, about 1.4k.
- Per song: about 4 items (single ×2 mixes, switch, two guitars), about 5.5k, plus about 8 whole-song
  truth renders.

| Stage | Songs | Renders | Hours (3 shards, about 6.75k renders an hour at arm A's rate) |
|---|---|---|---|
| B1 pilot | 4 | about 22k | about 3.3 h, plus about 10 min of htdemucs |
| B2 (if h = 0.03 needs 17 songs) | +13 | about 72k | about 11 h |
| B2 without arm O (if B1 shows O adds little) | +13 | about 36k | about 5.5 h |

No B render starts before:
- the overnight runs end;
- this plan's part B amendment (B1's exact items, presets and seeds) is reviewed;
- the render cap is respected. B's runner is added to `learn/local_objective.RENDERS` and waits
  on `wait_cap` (at most 3 render processes machine-wide).

## Order

1. This plan and the ledger entry, then independent review; required changes are folded in.
2. Part A's code and tests, the inventory, the screen, the hum-fix measurement and the listening
   page (zero renders). Then the results document, `docs/clean-di-library-results.md`, with
   screen counts and the page's path. Committed, with a PR that gets an independent review.
3. The user listens; the page is scored; screens are amended if the ear disagrees; the manifest
   is rebuilt.
4. Part B: an amendment declaring B1's items, presets and seeds, then review, then B1 after the
   overnight runs; then B2 by the power rule.

## Amendment 1 (2026-10-17): review changes, before the full screen

The independent review approved part A with 12 required changes, and set 4 more for part B's own
amendment. All are made here. Code and tests changed with them (`learn/clean_di.py`,
`tests/test_clean_di.py`). Nothing from the full screen had been seen.

Three changes were found while writing the tests and in a mechanics dry run of the hum fix on the
4 trial sessions, before the review came back:
- a hum harmonic counts only when the strongest bin within 6 Hz of k·f0 is within one bin of it,
  not on the skirt of a nearby note;
- hum needs at least 2 harmonic lines, since one persistent line can be a held note;
- zero runs over 200 ms are edits ("hard_cut", a tag), not dropouts.

The dry run also showed that the fix's declared "removed power under −50 dB" condition cannot
work. Any set of 1-Hz notches removes its slivers of a broadband guitar spectrum, about −26 to −29
dB for 4–8 notches, whether or not the guitar sounds different. Item 8 below replaces it.

**Part A (required, done):**
1. **Guards, stated as they are.**
   - Sets 1–3 and Guitar-TECHS P1 paths go through `set3.is_held_out`, which fails closed.
   - Guitar-TECHS P2 and the two undeclared downloads are an allowlist. Their band is checked
     against every held-out band name, which now includes set 1's (Rebecca Haviland, Chris
     Coltraine, via `band_of`), and their path against sets 4–6.
   - A test checks the evidence that Dark Ride and The Apprehended were never eligible for a
     held-out draw: both are in set 3's catalogue under `unpaired` ("no paired part"), and neither
     is in `band_strata`.
2. **Part B's pilot songs are known-answer now.**
   - Rebecca Haviland (Bourbon, Collide With Me) and Chris Coltraine (Heather Jane) are
     `split: known_answer`, beside The Apprehended. That is 12 DIs, which leave the library and
     every later fresh draw. The 9 set-1 DIs were already `training_ok: false`.
   - Two Wickerman DIs over set 3's clipped-DI rule (ElecGtr5, ElecGtr6) are now
     `training_ok: false`, as `set3.training_dis` drops them.
   - **Inventory now:** 237 DIs; 225 library, 223 of them may train; 12 known-answer; 32 bands or
     players.
3. **Part B's training check.** `set3.fold_for_band` raises for these bands, so part B's runner
   asserts directly that no file of the item's session or band is in the C′ fold's training list
   (`set3.training_dis(fold)`, by path and band). `assert_training_ok` still refuses the item.
4. **"Keys GTR" DIs are left out.** The 5 John Morgan Kimock DIs are excluded with a reason until
   their instrument is checked by ear.
5. **More exclusions listed:**
   - EGFxSet clean: single notes, too short for 10-s sections;
   - ToneTwist DRY: CC BY-NC, and calibration-only by set 3's declaration.
6. **Stale outputs.** The trial screen files were deleted. Outputs carry `schema:
   clean-di-screen-2`, and any other schema is recomputed.
7. **Bleed status per section:** measured, partial, unmeasured, no_rest_frames, or no_session
   (Guitar-TECHS).
   - Sections whose bleed could not be read are tagged `bleed_unread` or `bleed_partly_read`.
   - **`clean` does not mean bleed-free unless the status is `measured`.**
   - The results report clean sections by bleed status.
   - Amp-track leakage is only partly screened: the DI's own amp tracks are left out by design,
     and a post-amp line-out is not detected.
8. **Hum, three changes:**
   - **Lines up to k = 40** (2–2.4 kHz), where the buzz heard after an amp and cab sits. Used for
     detection, the per-section measure and the notch set.
   - **The mains is chosen per session** (all its DIs vote; Guitar-TECHS per player). A DI's lines
     must also be confirmed on its rest frames: one of the first 4 harmonics ≥ 10 dB above its
     neighbours in the mean spectrum of frames more than 40 dB under its loudest. If it has fewer
     than 8 such frames, the hum is kept and tagged `hum_unconfirmed_on_rests`.
   - **The fix's adoption rule, now per DI:**
     - on the 20 hum-free control DIs, its notch set moves no third-octave band by more than
       0.1 dB, read from 80 Hz (the guitar's range; low E is 82 Hz);
     - its fixed sections' hum, read over every harmonic up to 40 (not only the notched ones, so
       the check is not circular), is under the flag level;
     - the listener hears no guitar change on its notched trials.

     Removed power is reported, not used.
9. **Clipping needs flat tops.** Consecutive samples must be equal within 1e-6, as well as at
   ≥ 0.999 of the peak. A smooth low-frequency peak in a file normalised to 0 dBFS no longer
   counts. Tested.
10. **What hiss measures.**
    - The section screen reads raw-DI hiss in 6–16 kHz. A 10th-percentile floor of Gaussian noise
      reads about 10 dB under its mean power, so −65 dB "re playing" is about −55 dB of noise
      power.
    - On sections that are mostly playing, the percentile is partly guitar. In the trial, Eggy
      "Bloomlight" was tagged slight hiss on 56 of 59 sections.
    - Much of 6–16 kHz is above a guitar cab's passband. So a track-level rest-frame floor in 2–6
      kHz is added and tagged `rest_hiss` at −60 dB or more. Both describe the raw DI, not hiss
      heard after an amp.
11. **The listening page now tests the thresholds, not only the extremes.**
    - **Hum and hiss:** 2 clips in each of 4 strata of the measured value: below the tag level,
      between tag and flag, up to 10 dB over the flag, and more than 10 dB over it. A clip has no
      other flag.
    - **Others:** 2 clips each for clipping, dropout and bleed; 2 tagged `hard_cut`; 4 clean
      clips with no tag beyond `dc` or the bleed-read tags.
    - **Repeats:** 2.
    - **Size:** up to 30 clips, one per DI.

    **The amendment rule, declared** (`amend()`, unit-tested). Answers are trusted; unanswered
    clips are left out:
    - **Lower:** at least 2 clips under a flag level heard with that problem lower it to midway
      between the lowest of them and the highest clip under it heard clean, or 5 dB under it if
      there is none.
    - **Raise:** at least 2 clips at or over the flag heard clean raise it to midway between the
      highest of them and the lowest clip over it heard with the problem, or 5 dB over it.
    - **Both at once:** the level stays and the conflict is reported.
    - **The tag level** moves by the same amount.
    - **A discrete flag** (clipping, dropout, bleed) or `hard_cut`: when both its clips are heard
      clean, it becomes a tag.
    - **A problem nobody screens for:** when 2 clean clips name the same problem, a new screen is
      designed, in a further amendment.

    **Post-amp audibility is untested by this page.** The clips are raw DIs; the thresholds are
    argued from audibility after an amp. A second sitting through one fixed crunch preset (about
    30 renders, declared then) can follow after the overnight runs if the user wants it.
12. **Ledger.** The entry's held-out and split fields are corrected. Part B gets its own ledger
    entry when its amendment is declared.

Also done, from the review's suggestions:
- A line's power sums the bins within one bin width of k·f0, with the neighbours read beyond three
  bin widths.
- The bleed bins leave out everything within about 10.8 Hz of any multiple of 50 or 60 Hz, which
  is roughly 60% of the 100 Hz–6 kHz band.
- For h = 0.02, the power table's song count is about 35, not 38.

**Part B: required in its own amendment, before any B render:**

13. **Cluster by band, not song.**
    - B1 is 3 clusters: Rebecca Haviland ×2 songs, Chris Coltraine and The Apprehended. That
      leaves 2 degrees of freedom.
    - B2's size comes from max(B1's upper 90% SD bound, 0.069), not from B1's point SD.
    - The known-answer SD may come out larger, not smaller: log(d_A/d_S) is unbounded as d_A
      approaches 0.
14. **Live-room leakage of the real amp.**
    - In Bourbon, Collide With Me and Heather Jane, the real amp of the same take can leak into
      the backing mics. Each kept backing track's coherence with the real amp track is measured.
    - Tracks that leak are dropped, or the song is reported as its own row.
15. **The Apprehended is not a DI-only song.** Its band notes say the rhythm guitars are
    amp-recorded high-gain (overdrive into a Laney Ironheart), and the 3 DIs are leads that were
    run through amp sims.
    - Only 6–11 of about 50 sections pass the activity rule, and its backing is outside the
      no-metal scope.
    - B1 adds a mix variant without the other guitars, and reports other-guitar presence per
      item.
16. **Estimand caveats:**
    - **In-family best case.** The truth presets sit on arm A's own three amps, so the readout is
      the best case for arm A.
    - **One definition of edge-of-breakup.** A crunch-class factory preset with its gain knob
      drawn from the lower half of the crunch presets' range, starting from the crunch S. This
      replaces "a factory preset of the item's class".
    - **The true class is oracle information.** S is picked from it, as in stage F; this is named.
    - **Knob error** is reported per knob and over the identifiable knobs (gain, bass, mid,
      treble). Output, master and presence trade-offs are reported apart.
    - **The 342 renders per section** include the judge renders that score the recovered preset
      and S on the true DI.
    - **MUSDB18 overlap.** The songs are checked against htdemucs's MUSDB18 bands, as stage F
      did, and reported as a row.

**Part B's candidate songs, updated** (2026-10-17, from the main session's
[Cambridge local check](research/cambridge-local-check-2026-10.md), PR #210). The checks below
come before any download or use.

- **Perpetual Escape "Stop And Rise"** (MTK017, 657 MB, on the direct archive host): a DI-only
  session with 11 DI parts in 19 files. It is a candidate only if it is in scope.
  - Its genre is progressive heavy rock, and its gain is unknown. After download, its DIs are
    screened like part A. The session's other tracks are then gain-classed with the project's
    measure, and the user listens to a short sample.
  - It is used only if its guitars are clean to crunch, not metal.
  - It never appears in any held-out list (checked before the download).
  - If kept, its band joins `KNOWN_ANSWER`.
- **Strobe "Maya", MekaPhil and The Timezone "GOTGF"** (the earlier report's DI-only route):
  - each needs the same scope check and the same held-out check;
  - The Timezone is checked against the label table's Timo And The Timezone (amendment-free
    rule above);
  - each is downloaded only if it is reachable on the direct archive host
    (`mtkdata.cambridgemusictechnology.co.uk`). The cambridge-mt.com pages still answer this Mac
    with a Cloudflare challenge, and nothing here bypasses it.
- **The Apprehended:** kept for B1, with item 15's caveats.
- **Dunning Kruger "Sascha"** is never used: its band is a set-3 held-out band, spent. It stays
  in the inventory's exclusions.

**Downloads:** one at a time, after the overnight runs end, with free disk kept at 31 GB or more.

## Amendment 2 (2026-10-17): the hum fix's collateral rule, from the re-review, before `hum-fix` ran

The re-review approved amendment 1 with one required change. Amendment 1's collateral condition
(no third-octave band from 80 Hz moves more than 0.1 dB) cannot be met by any notch set:
- third-octave bands near 100–125 Hz are only 23–29 Hz wide;
- a 1-Hz zero-phase notch takes about 2.4 Hz out of one;
- so it moves that band about 0.3 dB on any broadband signal. The reviewer measured 0.12–0.36 dB
  on white and pink noise.

**The new condition.** The notch set's band changes are measured on the same seeded pink noise,
the reference. The fix then passes on collateral when, for every hum-free control DI, no band from
80 Hz moves more than the reference does plus 0.1 dB (`excess_collateral`). The question becomes
whether guitar partials sitting on the notches are hit, which is what would alter the guitar.

A unit test checks both sides:
- hum-free broadband noise passes;
- a partial placed on a notch (120 Hz) fails.

The residual-hum and listener conditions are unchanged.

From the re-review's suggestions:
- the scorer moves the tag level with the flag (`proposals[...]["tag"]`);
- the key records that part 2's null trial reuses one hum trial's section, so it is played 4 times;
- the results report that `partial` is the usual bleed status, and how many tracks were read.

## Amendment 3 (2026-10-18): the rest check may not refute a mains fundamental, before the manifest is used

The results' audit found that the rest-frame check (amendment 1, item 8) refuted the hum lines of 50
DIs, and that on 10 of them the lines look like real hum. Their rest frames are mostly note tails or
gated silence, where hum cannot show. Nothing has drawn on `manifest.json` yet.

**Why the rest check exists.** A persistent line at k·f0 can be a held note's partial, so lines must
also show where the guitar rests. That reason barely reaches the mains fundamental itself.
- In any tuning near A = 440 Hz, no equal-tempered note is within 2% of 50 or 60 Hz. The nearest
  are G1 49.0, G♯1 51.9, A♯1 58.3 and B1 61.7 Hz.
- Notes that low do occur in this inventory. Heather Jane ElecGtr1 peaks at 63.5–64.1 Hz, and
  Atlantis Bound at 61.4 Hz. Many DIs are unclassed, and some sessions are metal.
- A held note would pass only if it were at least 30 cents off pitch and persisted through 90% of
  the frames (the 10th percentile).
- A steady line at the mains frequency is therefore mains hum, whatever the rest frames show.
- Same-session DIs agree. Their siblings were rest-confirmed at the same frequencies: Guitar-TECHS
  P1 Drop3_7, Drop3_m7 and Set1_7; Prodigal ElecGtr2 and 5; and Wickerman ElecGtr8 and 9.

**The rule.** A DI whose lines the rest check refutes keeps them (`hum_rest_check:
kept_fundamental`) when both hold:
1. **The fundamental is one of its lines:** k = 1 passes the track's own line test (≥ 10 dB above
   its neighbours in the 10th-percentile spectrum, as for every other line).
2. **That line is at the mains:** in a 10th-percentile spectrum of 65,536-point frames (0.73-Hz
   bins, interpolated), the peak within 3 Hz of the mains is within **0.3 Hz** of it.
   - The grid is held within ±0.2 Hz in normal operation (UK; tighter in North America). 0.1 Hz
     more allows for the estimate.
   - On the 76 rest-confirmed DIs with a fundamental line, this reads within 0.24 Hz on 75 of them.
     The other, Atlantis Bound, reads 61.43 Hz, a low note rather than the mains: condition 1 alone
     can be fooled, and condition 2 is what catches it.
   - This tolerance was set after the frequencies were read. The outcome is the same for any value
     from 0.20 Hz (Dom McLennon reads 0.19 Hz off) to 2.4 Hz (Wickerman ElecGtr4, 47.5 Hz).

Kept lines are screened by level exactly as confirmed ones are (flag ≥ −55 dB, tag ≥ −70 dB re
playing), and flagged sections are tagged `hum_kept_by_fundamental`.
- The other 32 refuted DIs stay refuted. Confirmed and unconfirmed DIs are untouched.
- **Caveat (review):** the review re-measured the 279 sections the rule moves.
  - 218 flag on the k = 1 line alone: all of Guitar-TECHS P1, and 25 of Prodigal ElecGtr1's.
  - The other 61 flag only through the higher lines kept with it: Wickerman ElecGtr7 8, Prodigal
    ElecGtr1 9 and ElecGtr3 6, Dom McLennon 11, "Blind Spots" 7, "Long Way Home" 19, Swatkins 1.
  - In some "Long Way Home" sections the fundamental does not show at all. That is where a guitar
    partial could still pass as hum, and the page's kept clips test it.
- **The hum fix is re-measured.** Two of `hum-fix`'s 20 hum-free controls (Prodigal ElecGtr1 and 3)
  now have kept lines, and three more had refuted lines. The 14 newly flagged DIs have no fix
  measurement.
  - So after `hum-amend`, `hum-fix` runs again (zero renders), with controls drawn only from DIs
    with no line at all, kept or refuted.
  - Its earlier result is kept as `hum-fix-v1.json`, and the adoption rule is unchanged.

**Not chosen, and why:**
- **Lowering the rest threshold** below 10 dB: the 10 suspects' rests read 6.6–9.8 dB, so any new
  value would be fitted to them. The rest check's weakness is what the rests contain, not its level.
- **An odd-harmonic test:** mains hum is often, not always, odd-dominated (a ground loop is not), and
  the refuted DIs that are plainly guitar partials (Eggy, Today's The Day) are odd-dominated too.
- **Dropping the rest check:** it is needed. With it gone, Heather Jane's two ElecGtr1 DIs lose
  every section, and Eggy's two most of theirs, to "hum" read at up to −18 dB re playing: guitar
  partials at k·60 Hz.

**How it moves the DIs** (projected on the stored screen before review; every refuted DI was
re-measured, and the non-hum measures reproduce):
- **18 DIs are kept:** the 10 suspects (7 Guitar-TECHS P1 chord files, Prodigal ElecGtr1 and 3,
  Wickerman ElecGtr7), Drag Me Down's 3 DIs, Timo's ElecGtr3, and 4 Telefunken DIs (Dom McLennon,
  Doom Flamingo "Blind Spots" and "Long Way Home", Swatkins).
- **14 of them change.** Drag Me Down and Timo have no section over the flag.
- **Clean sections:** 1,703 → 1,424. **Non-overlapping:** 954 → 808 (159.0 → 134.7 min).
  - The 10 suspects: 134 → 8.
  - The 4 Telefunken DIs: 41 → 21.
  - Training_ok: 875 → 729. Known-answer: unchanged (69).
- **Hum-flagged:** 2,707 → 3,047 sections, 105 → 119 DIs.
- **Guitar-TECHS** keeps 1 clean section (P2), down from 103.
- **The 32 still refuted:**
  - If their refuted lines were screened by level, they would lose a further 195 non-overlapping
    sections. Known-answer would fall from 69 to 21, and training_ok from 729 to 584.
  - Most of this is Eggy (2 DIs), Today's The Day (4), Heather Jane ElecGtr1 (2) and Burial Of
    Silence, whose "hum" reads up to −18 dB re playing.
  - That is the rest check's job. The listening page tests where it alone decides.
- **Sensitivity:**
  - Any frequency tolerance from 0.2 to 2.4 Hz keeps the same 18 DIs. The next DI with a
    fundamental line, Wickerman ElecGtr4, peaks at 47.5 Hz.
  - Reading condition 1 on the 65,536-point spectrum instead would add Guitar-TECHS P2's two chord
    files, Doom Flamingo "Measurements" and Diesel 13 ElecGtr2: 4 more non-overlapping sections
    lost.

**The second blind listening page** (`python -m learn.clean_di listen-hum build`), written to
`~/ndsp-presets/listening/di-clean-2/di-hum.html`, with the key in `private/key.json`. Built like
page 1: padded AAC data URIs, a seeded order (seed 20261018), no names (asserted), whole 10-s
sections levelled to −20 LUFS, and one clip per DI.
- **Kept (9):** one section the rule moves (clean before, flagged for hum alone now) per unit, with
  no tag beyond the benign ones and `slight_hiss`.
  - The units are the 7 DIs outside Guitar-TECHS, plus Guitar-TECHS P1's 7 chord files as one unit
    (one recording setup, near-identical hum).
  - That unit gets 2 clips, from 2 different files.
- **Refuted (8):** 8 DIs, seeded, among those the rest check still refutes. One clean section each,
  drawn from the sections their refuted lines would flag (≥ −55 dB), where the rest check alone
  decides.
- **Anchors (2 + 2):** hum-only sections of rest-confirmed DIs at least 10 dB over the flag, and
  clean sections of DIs with no hum line.
- **Repeats (2):** one kept clip and one refuted clip.
- Refuted and anchor DIs on page 1 are left out.

**The answer:** one line copied from the page, page 1's format (`1ok 2hum 3hiss+hum …`).

**The rule, declared** (`score_hum()`, unit-tested). Answers are trusted, and unanswered clips are
left out.
- **Kept, per unit:**
  - A unit reverts when more than half of its answered clips are heard without hum. Its lines are
    then refuted again, as before this amendment.
  - When at least 2 units, and more than half of the answered units, revert, the amendment is
    withdrawn for every DI.
- **Refuted, per DI:**
  - A DI whose clip is heard with hum has its lines restored, and they are screened by level.
  - When at least half of the answered refuted clips are heard with hum, and that share is larger
    than the share of the answered clean anchors heard with hum, the refutation is suspended for
    every DI. This costs the 195 sections above, until a further amendment designs a better test.
- **Withdrawal and suspension at once:** neither applies, and the conflict is reported. Per-unit and
  per-DI changes still apply.
- **This page does not move the hum flag level.** Page 1's strata test the level, so the same answer
  does not count twice.
- **Anchors and repeats** are reported as a calibration caveat and move nothing.
- **Page 1 already holds clips from affected DIs:**
  - Dom McLennon @85 s, clean in version 1 and hum-flagged now;
  - Eggy "Fragments" @40 s, which the refuted lines would flag;
  - Renesans "Less Than Nothing" @125 s, twice.

  Page 1 is scored against its own key, which records the version 1 values.

**Applied as:**
- `python -m learn.clean_di hum-amend` re-measures the refuted DIs and asserts that the other
  measures reproduce. It keeps the screen as it stood in `screen-v1/`.
- `manifest` then writes version 2. Version 1 is kept as `manifest-v1.json`, and v2 names it and
  its sha256.
- Each section's `measures.hum_rel_db_refuted` records the refuted lines' level (not a screen).
- `hum-fix` runs again on the amended screen, as above.
- Until the second page is answered, the version 2 manifest is the one to train from.

**Review (2026-10-18, independent, before applying):** approve with 6 required changes, all made
above. Every projected count reproduced.
1. The tuning argument, restated without tuning scope.
2. Kept clips vote per unit, with Guitar-TECHS P1 as one unit; the 218/61 split is stated.
3. Refuted DIs are restored per DI, and suspension needs half the answers and more than the clean
   anchors; its full cost is stated.
4. `hum-fix` is re-measured, with controls free of refuted lines.
5. This page no longer moves the flag level, so one answer cannot act twice.
6. `hum-amend` refuses an already-amended screen with no `screen-v1/`, and asserts the re-measured
   check.

The review's small code points were fixed too:
- the page refuses a manifest with no version 1;
- the draw raises if no order separates the repeats;
- kept clips carry no other tag.
