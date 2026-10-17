# A clean DI library: part A results (2026-10-18)

These are the results of part A of the [plan](clean-di-library-plan.md), run under amendments 1
and 2. Development data only, zero renders. These are descriptive screen counts with declared
thresholds, not pass/fail bars. The blind listening check is built and waits for the user. The
screens may still move by the declared amendment rule, so treat every count below as provisional.

- **Code:** `learn/clean_di.py`.
- **Data:** in `~/ndsp-presets/learn/clean-di/`:
  - `inventory.json` (sha256 e64bd8ebbf02d2af…);
  - `screen/` (one file per DI);
  - `manifest.json` (sha256 22a61fb76b918b25…);
  - `hum-fix.json`;
  - `logs/`.

## Headline

- **Inventory:** 237 development guitar DIs over 32 bands or players.
  - 225 are library DIs, 223 of which may train.
  - 12 are part B's known-answer DIs: The Apprehended, plus set 1's Bourbon, Collide With Me and
    Heather Jane.
  - 5 "Keys GTR" DIs, the held-out material, Guitar-TECHS P3, sets 4–6, EGFxSet, ToneTwist,
    "Sascha" and "Crucial Taunt" are listed as exclusions with reasons.
- **Sections:** 5,571 ten-second sections pass the activity rule. **1,703 (31%) pass every
  screen.** Taking non-overlapping ones, that is **954 sections, 159 minutes** of clean DI. 117 of
  the 237 DIs have at least one clean section.
  - **May train:** 1,557 clean sections, 875 non-overlapping (146 minutes).
  - **Known-answer (part B):** 131 clean, 69 non-overlapping (11.5 minutes).
- **Hum is the main fault, then hiss.**

  | Flag | Sections | DIs | Sections where it is the only flag |
  |---|---|---|---|
  | Hum | 2,707 | 105 | 2,083 |
  | Hiss | 1,525 | 114 | 904 |
  | Clipping | 168 | 11 | 69 |
  | Bleed | 155 | 10 | 104 |
  | Dropout | 30 | 9 | 21 |

- **The hum fix is not adopted.** All 105 hum-flagged DIs fail its collateral condition, and 104
  of them also fail the residual-hum condition. So hum-flagged sections stay out. The listening
  page therefore has no hum-removal part.
- **Caveat (audit): the hum screen misses some hum.** The rest-frame check refuted the lines of
  50 DIs, which then count as hum-free. On 10 of them the lines look like real hum: a line at
  the mains fundamental itself stands 27–48 dB above its neighbours, with 17–37 lines, mostly
  odd harmonics, and no guitar note sits at 50 or 60 Hz. These are 7 Guitar-TECHS P1 chord files,
  Prodigal ElecGtr1 and 3 (the calibration's hum example), and Wickerman ElecGtr7.
  - Their rest frames are mostly note tails or gated silence, so the fundamental there reads
    6.6–9.8 dB, just under the 10-dB rest rule.
  - These 10 DIs give **134 of the 954 non-overlapping clean sections (22 minutes)**. They include
    all 103 of Guitar-TECHS's.
  - Treat them as probably hummy until the screen is amended (see "Next").
  - In all, the 50 refuted DIs give 505 of the 954.

## By source

| Source | Sections (activity) | Clean | Share | Non-overlapping clean | Minutes | DIs with a clean section, of those with an activity section |
|---|---|---|---|---|---|---|
| Cambridge | 2,128 | 951 | 45% | 542 | 90.3 | 88 of 117 |
| Telefunken | 1,116 | 557 | 50% | 309 | 51.5 | 21 of 28 |
| Guitar-TECHS P1 and P2 | 2,327 | 195 | 8% | 103 | 17.2 | 8 of 86 |

The inventory has 122 Cambridge DIs, 28 Telefunken and 87 Guitar-TECHS; 6 have no activity
section. Guitar-TECHS's 103 clean sections all come from the 7 chord files in the hum caveat above.

- **Guitar-TECHS is mostly hum.** Its 60-Hz lines stand 40 dB or more above their neighbours, so
  2,065 of its 2,327 sections are hum-flagged. Its exercises (scales, chords) were the bulk of the
  older DI pool (`learn/di_pool.py` uses P1's chords and scales). Anything that trained on them
  trained on hummy DIs.
- **Mains:** chosen per session, which suits the recordings' countries. Cambridge sessions mostly
  read 50 Hz (86 DIs, 36 at 60 Hz); Telefunken (27 of 28 DIs) and Guitar-TECHS read 60 Hz.
- **Gain class** (non-overlapping clean minutes; most DIs are unclassed):

  | Class | Minutes |
  |---|---|
  | Unclassed | 69.5 |
  | Clean | 57.0 |
  | High-gain | 21.5 |
  | Crunch | 11.0 |

  The library DIs that may train and carry a clean or crunch label give 408 non-overlapping
  sections.
- **Style of the clean sections:**

  | Style | Sections |
  |---|---|
  | Sparse | 228 |
  | Medium | 1,155 |
  | Dense | 320 |

## Screens: what to read into them

- **Hum.**
  - Lines are confirmed on the rest frames for 84 DIs and refuted for 50, whose lines are then
    dropped. Some refuted lines may be held notes, but at least 10 look like real hum (see the
    headline caveat).
  - 27 DIs have too few rest frames to check. Their hum is kept, and their sections are tagged
    `hum_unconfirmed_on_rests` (636 sections).
  - Prodigal, the known example: ElecGtr2 and 5 are flagged. ElecGtr1 and 3 had their lines
    refuted on rests and are not, though the calibration found 38–40 dB lines in both.
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
    | Partial | 955 |
    | Unmeasured | 332 |
    | Solo recording | 195 |
    | No rest frames | 156 |
    | Measured | 65 |

    **"Clean" means bleed-free only for the 65 `measured` sections.**
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
  - the hum caveat above: none of the 10 suspect DIs is on the page.

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

1. The user listens and sends the answer line. The page is scored, the screens are amended by
   the declared rule, and the manifest is rebuilt.
2. Part B's amendment (B1's items, presets, seeds, and the review's items 13–16), then review.
   B1 runs after the overnight runs.
3. Data use: anything that trains on DIs (the PR12 cache, C′) should draw from the manifest's
   clean sections that may train, through `assert_training_ok`. Today's pool includes
   Guitar-TECHS P1, which is mostly hum-flagged.
4. A hum-screen amendment, declared before the manifest is used, for the audit's caveat. For
   example: a strong line at the mains fundamental (no guitar note sits there) is not refuted
   by the rest check, and the 10 suspect DIs then go on the page. Until then, a training draw
   should leave those 10 DIs out.

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
