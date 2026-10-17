# A clean DI library: part A results (2026-10-18)

These are the results of part A of the [plan](clean-di-library-plan.md), run under amendments 1
and 2, with the hum screen amended by amendment 3 (2026-10-18, below) before the manifest was
used. Development data only, zero renders. These are descriptive screen counts with declared
thresholds, not pass/fail bars. Two blind listening pages are built and wait for the user. The
screens may still move by their declared rules, so treat every count below as provisional.

- **Code:** `learn/clean_di.py`.
- **Data:** in `~/ndsp-presets/learn/clean-di/`:
  - `inventory.json` (sha256 e64bd8ebbf02d2af…);
  - `screen/` (one file per DI);
  - `manifest.json`, version 2, under amendment 3 (sha256 9de80dd499680990…). **This is the one to
    train from.**
  - `manifest-v1.json`, version 1, before amendment 3 (sha256 22a61fb76b918b25…; v2 names it);
  - `screen-v1/`, the screen before amendment 3;
  - `hum-fix.json`, re-measured after amendment 3; `hum-fix-v1.json`, the earlier run;
  - `logs/`.

## Headline

- **Inventory:** 237 development guitar DIs over 32 bands or players.
  - 225 are library DIs, 223 of which may train.
  - 12 are part B's known-answer DIs: The Apprehended, plus set 1's Bourbon, Collide With Me and
    Heather Jane.
  - 5 "Keys GTR" DIs, the held-out material, Guitar-TECHS P3, sets 4–6, EGFxSet, ToneTwist,
    "Sascha" and "Crucial Taunt" are listed as exclusions with reasons.
- **Sections:** 5,571 ten-second sections pass the activity rule. **1,424 (26%) pass every
  screen.** Taking non-overlapping ones, that is **808 sections, 134.7 minutes** of clean DI. 110 of
  the 237 DIs have at least one clean section.
  - **May train:** 1,278 clean sections, 729 non-overlapping (121.5 minutes).
  - **Known-answer (part B):** 131 clean, 69 non-overlapping (11.5 minutes).
  - **Before amendment 3** (manifest v1): 1,703 clean, 954 non-overlapping (159.0 minutes), 875
    that may train. The change is 146 non-overlapping sections (24.3 minutes), all hum.
- **Hum is the main fault, then hiss.**

  | Flag | Sections | DIs | Sections where it is the only flag |
  |---|---|---|---|
  | Hum | 3,047 | 119 | 2,362 |
  | Hiss | 1,525 | 114 | 843 |
  | Clipping | 168 | 11 | 69 |
  | Bleed | 155 | 10 | 104 |
  | Dropout | 30 | 9 | 21 |

- **The hum fix is not adopted.** After amendment 3, all 119 hum-flagged DIs fail its collateral
  condition, and 118 of them also fail the residual-hum condition (105 and 104 before). So hum-flagged sections stay out. The listening
  page therefore has no hum-removal part.
- **Amendment 3 closes the audit's hum caveat.**
  - The audit's finding: the rest-frame check refuted the lines of 50 DIs, and on 10 of them the
    lines look like real hum (7 Guitar-TECHS P1 chord files, Prodigal ElecGtr1 and 3, Wickerman
    ElecGtr7). Their rests are note tails or gated silence.
  - The rule now: the rest check may not refute the mains fundamental when it is one of the DI's
    lines and sits within 0.3 Hz of the mains. That keeps the lines of 18 DIs: the 10, Drag Me
    Down's 3, Timo's ElecGtr3, and 4 Telefunken DIs.
  - 14 of the 18 lose sections. The 10 suspects go from 134 non-overlapping clean sections to 8,
    and the 4 Telefunken DIs from 41 to 21.
  - Details in "Amendment 3" below. A second blind page tests it (answers pending).

## By source

| Source | Sections (activity) | Clean | Share | Non-overlapping clean | Minutes | DIs with a clean section, of those with an activity section |
|---|---|---|---|---|---|---|
| Cambridge | 2,128 | 903 | 42% | 518 | 86.3 | 88 of 117 |
| Telefunken | 1,116 | 519 | 47% | 289 | 48.2 | 21 of 28 |
| Guitar-TECHS P1 and P2 | 2,327 | 2 | 0% | 1 | 0.2 | 1 of 86 |

The inventory has 122 Cambridge DIs, 28 Telefunken and 87 Guitar-TECHS; 6 have no activity
section.
- Before amendment 3, Guitar-TECHS had 195 clean sections (103 non-overlapping).
  - 193 of them (102 non-overlapping) came from the 7 P1 chord files whose hum amendment 3 keeps.
  - 2 (1) came from P2, and these stay clean.
- Cambridge had 542 (Drag Me Down and Timo lose none; Prodigal and Wickerman ElecGtr7 lose 24).
- Telefunken had 309.

- **Guitar-TECHS is hum.** Its 60-Hz lines stand 40 dB or more above their neighbours. Under
  amendment 3, 2,267 of its 2,327 sections are hum-flagged (2,065 before), and one P2 section is
  clean. Its exercises (scales, chords) were the bulk of the
  older DI pool (`learn/di_pool.py` uses P1's chords and scales). Anything that trained on them
  trained on hummy DIs.
- **Mains:** chosen per session, which suits the recordings' countries. Cambridge sessions mostly
  read 50 Hz (86 DIs, 36 at 60 Hz); Telefunken (27 of 28 DIs) and Guitar-TECHS read 60 Hz.
- **Gain class** (non-overlapping clean minutes; most DIs are unclassed):

  | Class | Minutes |
  |---|---|
  | Unclassed | 52.5 |
  | Clean | 50.5 |
  | High-gain | 21.5 |
  | Crunch | 10.2 |

  The library DIs that may train and carry a clean or crunch label give 364 non-overlapping
  sections (408 before amendment 3).
- **Style of the clean sections:**

  | Style | Sections |
  |---|---|
  | Sparse | 187 |
  | Medium | 929 |
  | Dense | 308 |

## Screens: what to read into them

- **Hum.**
  - Lines are confirmed on the rest frames for 84 DIs and refuted for 50.
  - Amendment 3 keeps the lines of 18 of the 50, whose mains fundamental is a line at the mains
    frequency. The other 32 have their lines dropped. Their level is still recorded per section
    (`hum_rel_db_refuted`).
  - 27 DIs have too few rest frames to check. Their hum is kept, and their sections are tagged
    `hum_unconfirmed_on_rests` (636 sections).
  - Prodigal, the known example: ElecGtr2 and 5 are flagged on confirmed lines. ElecGtr1 and 3 are
    flagged under amendment 3 (34 and 6 sections).
- **Hiss** is read on the raw DI (6–16 kHz, 10th percentile):
  - 2,564 sections are tagged `slight_hiss`, and 1,807 carry the track-level `rest_hiss` tag
    (2–6 kHz rest floor at −60 dB or more). The tags are common.
  - On dense sections the percentile is partly guitar, so this screen likely over-flags bright,
    busy playing. The listening page's strata test that directly.
- **Bleed.**
  - 108 DIs come from multitrack sessions. Each checked a median of 26 other tracks, and a
    median of 13 could be read: the other track played while the DI rested.
  - **`partial` is the usual status.** Among clean sections:

    | Bleed status | Clean sections |
    |---|---|
    | Partial | 914 |
    | Unmeasured | 298 |
    | No rest frames | 156 |
    | Measured | 54 |
    | Solo recording | 2 |

    **"Clean" means bleed-free only for the 54 `measured` sections.**
  - **Sources found:** 21 track pairs over 12 DIs, 10 of which have a bleed-flagged section. Most are other guitars' amp or mic tracks in
    the same session; the strongest are Quicksand ElecGtr2's room mic (0.39) and Wickerman
    ElecGtr2 against ElecGtr3's amp (0.36).
  - Some of these may be one guitarist's part split over two tracks, or unison doubles, rather
    than electrical crosstalk. The page's two bleed clips are the check.
- **Clipping (flat tops):** 168 sections in 11 DIs. They include Wickerman ElecGtr5 and 6 (set
  3's catalogue already rules them clipped) and one Guitar-TECHS P2 technique file (345 runs).
- **Dropouts:** 30 sections in 9 DIs. A further 124 sections carry `hard_cut` edits; that is a
  tag, not a flag.
- **DI-level:** 6 DIs have no section that passes the activity rule.

## The hum fix (measured; not adopted)

This section's table is the first run (`hum-fix-v1.json`, 105 flagged DIs).
- The run after amendment 3 (`hum-fix.json`, 119 DIs) reads, at the 10th percentile, median and
  90th percentile:
  - collateral 0.53, 0.61 and 1.07 dB;
  - hum before the fix −44.9, −35.5 and −25.6 dB;
  - hum after the fix −46.5, −39.0 and −28.4 dB.
- The verdict is the same.

On 20 hum-free control DIs (seeded), each flagged DI's notch set was compared with what the same
set does to pink noise (amendment 2).

| Measure | 10th percentile | Median | 90th percentile | DIs that fail |
|---|---|---|---|---|
| Collateral: the largest third-octave change (from 80 Hz) beyond the pink-noise reference | 0.41 dB | 0.67 dB | 1.75 dB | 105 of 105, against a 0.1-dB limit |
| Worst flagged section's hum, read over every harmonic up to 40: before | −44.8 dB | −35.5 dB | −22.6 dB | — |
| Worst flagged section's hum after the fix (each DI's worst section after) | −46.5 dB | −40.0 dB | −27.2 dB | 104 of 105 stay over the −55 dB flag level |

What this means:
- **Collateral:** guitar partials do sit on many of the notched harmonics, especially when up to
  40 lines are notched.
- **Residual:** 1-Hz notches remove the lines they target, but hum is not confined to them.
  - The all-harmonic read also picks up some persistent guitar content, so it is an upper bound.
  - Even so, the fix does not bring hum under the flag level.

By the declared rule the fix is not adopted, and the ear is not asked. A broadband hum remover
would change the guitar, as the plan expected for hiss. **Hum-flagged sections are cut, not
repaired.**

## The listening check (built; waiting for the user)

- **Page:** `~/ndsp-presets/listening/di-clean-1/di-clean.html` (8.4 MB, 30 clips).
- **Key:** `private/key.json` (sha256 2faa7ad1751a6661…).
- **Blinding:** AAC data URIs with random-length mp4 `free` boxes, seeded order, no names in the
  page (asserted), and distinct clip bytes (asserted).
  - The bytes are distinct only through the padding: a repeat's AAC stream is identical to its
    source's, and sizes follow the content (the hiss clips encode about 5% larger, an edit to
    silence about 15% smaller). This blinds the ear, not a look at the page's source.
  - Each clip is a whole 10-s section, levelled to −20 LUFS. The plan's part 1 said 8 s from the
    middle; amendment 1 did not restate the length.
- **The clips:**
  - hum and hiss: 2 each in four strata around their tag and flag levels;
  - 2 each for clipping, dropout and bleed;
  - 2 `hard_cut`;
  - 4 clean;
  - 2 repeats.
- **The answer:** one line copied from the page, one token per clip, combining the problems
  heard with `+`. For example: `1ok 2hum 3hiss+click …`.
  - The tokens are `ok`, `hum`, `hiss`, `click` (clicks, dropouts, crackle), `dist`
    (distortion, clipping), `bleed` (other instruments) and `other`.
- **Scoring:** `python -m learn.clean_di listen score --answers "<line>"`. It prints the counts
  and `amend()`'s proposals; the screens then change by amendment.
- **What it cannot test:**
  - post-amp audibility, since the clips are raw DIs;
  - amendment 3's hum rule, which the second page below tests. Page 1 was drawn from manifest
    v1 and is scored against its own key.
  - Page 1 holds clips from DIs that amendment 3 touches:
    - Dom McLennon "Gym Hours" @85 s is still clean (−57.6 dB, `slight_hum`). It overlaps by 5 s
      page 2's kept clip @90 s, which is now flagged.
    - Eggy "Fragments" @40 s and Wickerman ElecGtr5 @35 s (already clipping-flagged) would be
      flagged by their refuted lines.
    - Renesans "Less Than Nothing" @125 s (twice) would not: its refuted lines read −70 dB.

## Amendment 3: the hum rule (applied; the second page waits for the user)

The [plan's amendment 3](clean-di-library-plan.md#amendment-3-2026-10-18-the-rest-check-may-not-refute-a-mains-fundamental-before-the-manifest-is-used)
was declared and reviewed (approve with 6 required changes, all made; re-review approve) before it
was applied.

**The rule.** The rest check may not refute a DI's hum lines when both hold:
- the mains fundamental is one of them (k = 1 passes the track's ≥ 10-dB line test);
- in a 0.73-Hz 10th-percentile spectrum, it peaks within 0.3 Hz of the mains.

Why it is principled: near A = 440 Hz no note is within 2% of 50 or 60 Hz. A held note would have
to be 30 cents off and last through 90% of the frames.

**How it moved the DIs.** `hum-amend` re-measured all 50 refuted DIs, and every non-hum measure
reproduced.

| | Before (v1) | After (v2) |
|---|---|---|
| DIs kept by the rule | — | 18 (of 50 refuted) |
| Clean sections | 1,703 | 1,424 |
| Non-overlapping clean | 954 (159.0 min) | 808 (134.7 min) |
| May train | 875 (145.8 min) | 729 (121.5 min) |
| Known-answer | 69 | 69 |
| Hum-flagged sections / DIs | 2,707 / 105 | 3,047 / 119 |
| DIs with a clean section | 117 | 110 |

- **The 18 kept DIs:** the 10 suspects, Drag Me Down's 3 DIs, Timo's ElecGtr3, and 4 Telefunken
  DIs (Dom McLennon "Gym Hours", Doom Flamingo "Blind Spots" and "Long Way Home", Swatkins).
  - Their fundamentals read 59.81–60.01 Hz or 49.94–50.11 Hz, at 13.7–53.8 dB.
  - 14 of them lose sections; Drag Me Down and Timo have none over the flag.
- **Non-overlapping sections lost, per DI:**

  | DI | Before | After |
  |---|---|---|
  | Guitar-TECHS P1 (7 chord files) | 102 | 0 |
  | Prodigal ElecGtr1 | 18 | 1 |
  | Prodigal ElecGtr3 | 4 | 2 |
  | Wickerman ElecGtr7 | 10 | 5 |
  | Dom McLennon "Gym Hours" | 17 | 13 |
  | Doom Flamingo "Blind Spots" | 7 | 2 |
  | Doom Flamingo "Long Way Home" | 13 | 3 |
  | Swatkins | 4 | 3 |
- **How the moved sections flag.** The review re-measured the 279 sections the rule moves.
  - 218 flag on the fundamental alone.
  - 61 flag only through the higher lines kept with it.
- **The 32 still refuted:** their refuted lines would flag a further 195 non-overlapping sections
  if screened by level, mostly guitar partials (Eggy, Today's The Day, Heather Jane ElecGtr1,
  Burial Of Silence). Known-answer would then fall from 69 to 21, and the sections that may train
  from 729 to 584.
- **Sensitivity:**
  - Any tolerance from 0.20 to 2.4 Hz keeps the same 18 DIs.
  - Reading the fundamental's line test on the finer spectrum would cost 4 more sections.

**The hum fix, re-measured** (`hum-fix.json`; the earlier run is `hum-fix-v1.json`).
- The 20 controls were redrawn with the same seed, from DIs with no line at all, kept or refuted.
- All 119 flagged DIs fail the collateral condition. The median largest band excess is 0.61 dB,
  and the 10th–90th percentiles are 0.53–1.07 dB.
- 118 of them also stay over the flag after the fix.
- **Still not adopted:** hum-flagged sections stay out.

### The second blind page (built; waiting for the user)

- **Page:** `~/ndsp-presets/listening/di-clean-2/di-hum.html` (6.5 MB, 23 clips).
- **Key:** `private/key.json` (sha256 0c1ff0d3d0e74921…).
- **Built like page 1:** padded AAC data URIs, seeded order (seed 20261018), no names (asserted),
  10-s sections at −20 LUFS, one clip per DI.
- **The clips:**
  - **9 kept:** one section the rule moves, for each of the 7 single-DI units, and 2 for
    Guitar-TECHS P1, which counts as one unit.
  - **8 refuted:** seeded, one per DI, among clean sections their refuted lines would flag. They
    are Heather Jane ElecGtr1 and its DT, Today's The Day ×4, Burial Of Silence and Eggy
    "Bloomlight".
  - **4 anchors:** 2 hum-only sections of rest-confirmed DIs, both Guitar-TECHS P2, and 2 clean
    sections of DIs with no line.
    - Caveat: both hum anchors are Guitar-TECHS P2 chord exercises, like the kept P1 clips, so
      they calibrate one recording setup's hum more than hum in general.
  - **2 repeats:** one kept, one refuted.
- **The answer:** one line copied from the page, page 1's format. For example: `1ok 2hum 3hiss+hum …`.
- **Scoring:** `python -m learn.clean_di listen-hum score --answers "<line>"`.
- **The declared rule:**
  - A kept unit heard mostly without hum reverts. If at least 2 units, and more than half, revert,
    the amendment is withdrawn.
  - A refuted DI heard with hum gets its lines back. If at least half the refuted clips are heard
    with hum, and a larger share than the clean anchors, the refutation is suspended for every DI.
  - Withdrawal and suspension together: neither applies.
  - The page does not move the flag level.

## Part B: planned cost (declared, not started)

- **B1, the pilot:** about 22k renders, about 3.3 h on 3 shards, plus about 10 min of htdemucs.
  - Its songs are The Apprehended, Bourbon, Collide With Me and Heather Jane: 3 band clusters.
  - It runs after the overnight runs end, and after its own amendment and review.
- **B2:** sized from max(B1's upper SD bound, 0.069) for a 90% half-width of 0.03 (17 songs at
  0.069).
  - About 72k renders (11 h) for 13 more songs, or about 36k (5.5 h) if arm O is dropped.
  - The fresh songs need downloads first. Strobe, MekaPhil, The Timezone and Perpetual Escape
    are each subject to the scope and held-out checks. The cambridge-mt.com pages are blocked by
    Cloudflare, so only the direct archive host is used.

## Next

1. The user listens to both pages and sends the two answer lines. Each page is scored, the
   screens are amended by its declared rule, and the manifest is rebuilt (version 3).
2. Part B's amendment (B1's items, presets, seeds, and the review's items 13–16), then review.
   B1 runs after the overnight runs.
3. Data use: anything that trains on DIs (the PR12 cache, C′) should draw from
   `manifest.json` (version 2): its clean sections that may train, through `assert_training_ok`.
   Version 2 already cuts the hum that amendment 3 keeps. The older DI pool uses Guitar-TECHS P1,
   which is now hum-flagged throughout.

Audited 2026-10-18 by an independent agent. Every headline count was recomputed from the stored
inventory, manifest, screens and `hum-fix.json`, and matches. The inventory and manifest sha256
prefixes match too. No held-out path, set 4–6 or Guitar-TECHS P3 file is in the inventory. The
only inventory bands with held-out songs are the known-answer ones, which `assert_training_ok`
refuses.

Changes:
- The hum fix's wording: all 105 fail on collateral and 104 on residual, not "both on all 105".
  The ledger was corrected too.
- The hum-screen caveat was added (10 refuted DIs that look like real hum: 134 sections, 22
  minutes, all of Guitar-TECHS's clean sections), with Next item 4. "Refuted lines were held
  notes" and "Prodigal flagged as expected" were overclaims, and were corrected.
- Bleed sources: 12 DIs, not 10. Telefunken mains: 27 of 28 DIs. The by-source table's
  denominators are named, and the "after" row is named.
- The listening page's limits were added: byte-level blinding, and clips of 10 s, not the
  plan's 8.
- Elsewhere: README 242 → 237 DIs, the roadmap row's date order, the tests skip without
  numpy/scipy (the bare CI job), and a comment on the page's distinct-bytes assert.

Amendment 3 was audited on 2026-10-18 by a fresh independent agent.
- Every amendment-3 and version-2 count was recomputed from the stored screens, manifests, page key
  and `hum-fix.json`, and matches.
- `manifest_rows` reproduces v2 from `screen/` and v1 from `screen-v1/`.
- Only the 50 refuted DIs' hum fields differ between the two screens.
- The page key and HTML check out: 23 clips, no names, no overlap with page 1's refuted or anchor
  DIs.

Corrections it made:
- the page-1 overlap note: Dom McLennon @85 s is still clean, Wickerman ElecGtr5 was added, and
  Renesans would not flag;
- Guitar-TECHS before amendment 3 was 193 clean sections from P1 and 2 from P2;
- the hum fix's headline now gives the second run's 119 and 118, and its table is labelled as the
  first run;
- the collateral's 10th percentile is 0.53 dB.
