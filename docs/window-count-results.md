# The window count, W0: results (audited)

**Run 2026-11-21 and audited** (an independent recompute from the tracks: PASS WITH CORRECTIONS, all taken below).
Declaration: [window-count-plan.md](window-count-plan.md); ledger `preset-ladder` `phase_wc` and `phase_wc_outcome`.
Code `learn/window_count.py`.

**What it is.** A truth count, not a score. Each number is the share of songs whose requested guitar part has at least
one 10-s window where it plays (in at least 60% of the frames) and no other guitar plays in any frame. No judge, no
preset, no render, no listening. **Descriptive:** W-rare was out of reach (about a third of the songs have one guitar
part), and raw multitracks of small bands probably overstate what released records offer.

## What ran

- Run from merged main `ab07fc3a`, with the main guard passed.
- The timing run took 0.2 s for 3 songs. The read took 77.4 s of CPU for all 103 songs, most of it MedleyDB raw
  envelopes.
- No render, separation, training or MPS; it ran beside other sessions' renders.
- Results file `~/ndsp-presets/learn/window-count/w0-results.json`, sha256
  `12ae47c393c95d72f752758656270b956835edc2b545ac145b75f6cb3a06c024` (the audit verified it).
- **Left out by the one held-band list** (`capture_labels.HELD_BANDS`):
  - locator: 8 sessions for V-real, 1 for NS;
  - MedleyDB: 6 songs for the panel.
- No song was left out for missing truth or length.
- The audit reproduced every count on all 208 parts.

## The result: W-some in each set and pooled

p is band-weighted: each song counts once inside its band, then p is the mean of band means. The intervals are 90%
t intervals over bands.

| Set | p [90% t interval] | Bands | Songs | Target parts | Song-weighted | Code |
|---|---|---|---|---|---|---|
| Locator (development multitracks) | 0.248 [0.099, 0.396] | 20 | 36 | 84 | 0.414 | W-some |
| MedleyDB (set 6) | 0.560 [0.443, 0.676] | 39 | 67 | 124 | 0.567 | W-some |
| **Pool (headline)** | **0.454 [0.359, 0.550]** | 59 | 103 | 208 | 0.514 | **W-some** |

**Reading (`W0_TABLE`):** a share of songs offer such a window, not most and not few. The scoped route is a branch
beside today's path, not the main path. W1, the detector, runs only on the user's go after its own review.

**The pool hides a real difference between the sets** (z = 2.8, the audit). So the pool is never read without both
sets beside it, and these alternative poolings (the audit's; the code does not change in any):

| Reading | p |
|---|---|
| Set-balanced (each set weighs half; normal approximation) | 0.404 [0.313, 0.494] |
| Genre-matched (the locator with MedleyDB's rock and pop songs only) | 0.346 [0.240, 0.453] |
| MedleyDB's multi-take stems split by take (the target read from its raws only) | 0.382 to 0.396 (pool; 0.436 unsplit on the same raws-only target) |
| Acoustic guitars always active | 0.368 (pool) |
| The most-playing part only (descriptive) | 0.573 [0.469, 0.678] |

## Beside the code (declared, descriptive)

| Reading | Locator | MedleyDB | Pool |
|---|---|---|---|
| Deciding (strict) | 0.248 | 0.560 | 0.454 |
| 90% (other guitars in at most 10% of frames) | 0.260 | 0.573 | 0.467 |
| Same part (the part's own DT doubles not counted) | 0.308 | 0.560 | 0.474 |
| At least 3 disjoint windows | 0.193 | 0.497 | 0.394 |
| Other guitars allowed in up to half the frames | 0.333 | 0.626 | 0.526 |
| MedleyDB's annotation alone | | 0.536 (57 songs) | |
| MedleyDB without its bleed-marked songs | | 0.525 (52 songs) | |
| MedleyDB, single-raw target stems only | | 0.489 (34 songs) | |

**By known scope:**
- Locator:
  - in scope (clean or crunch) 0.381 [0.162, 0.599] on 25 songs; in its multi-guitar songs 0.195;
  - high-gain 0 of 6 songs;
  - unlabelled 0.204.
- MedleyDB:
  - its clean electric stems 0.608;
  - its distorted stems 0.408.

**By the locator's role:**
- lead parts 0.109 [−0.054, 0.272] on 13 songs;
- no role 0.294;
- rhythm 2 songs, none offering.

## Why the two sets differ (the audit)

- **The single-guitar share** explains 0.11 to 0.15 of the 0.31 gap. 28 of MedleyDB's 67 songs have one guitar,
  against 10 of the locator's 36.
  - The locator has 10, not the draft's 11: "She's Gone" has an acoustic track, which counts as another guitar.
- **The locator's multi-guitar songs have more guitars** (median 3 against MedleyDB's 2) and read 0.115 against
  MedleyDB's 0.352.
- **Genre acts through the single-guitar share:** MedleyDB's rock and pop songs read 0.440.
- **Band weighting matters in the locator:** single-guitar bands with several songs (Doom Flamingo 4, Eggy 3,
  Swatkins 3) each weigh one band. Hence 0.248 band-weighted against 0.414 song-weighted.

## How much material a window gives

- **Offering parts in multi-guitar songs:**
  - pooled: median 65 s alone (IQR 28–126 s), a median of 6 disjoint windows;
  - locator: median 28 s, 2 disjoint windows; 33% have under 20 s, the minimum is 13 s.
- **Single-guitar songs offer the whole song.**
- So where other guitars play, an offering part usually gives one to three disjoint 10-s sections, thin on small-band
  multitracks.

## Checks and biases (the audit)

- **Near-constant guitars are real playing.** These are the 46 MedleyDB guitars active in at least 95% of their song.
  - All sit within 9 dB of the song's loudest guitar.
  - 34 of 42 are near-constant by both the annotation and the raws.
  - The quiet frames of the Music Delta excerpts are tonal.
  - Only Ethan Hein's "Girl On A Bridge" S05 is implausible, and its song has one guitar.
  - **Post hoc:** with the 7 weakest set inactive, the pool reads 0.489 (W-some).
- **The declared optimistic biases are small**, about 0.05 or less on the pool:
  - splitting MedleyDB's multi-take target stems by take (36 to 42 of 124 hold more than one take, by two rules),
    with the target read from its raws only, moves MedleyDB from 0.532 to 0.451–0.473 and the pool from 0.436 to
    0.382–0.396;
  - the acoustic stems' annotation-only rule flips nothing;
  - the 90% tolerance adds 0.013;
  - the OR with the raw rule adds 0.024.
  - The OR flipped 13 windows against alone and 72 towards it, of 24,501.
- **One new possible bias:** John Morgan Kimock's "Pre Record Tracks" may hold guitar. If they do, the locator reads
  0.204.
- **Provenance and the exclusions hold.**

## What it changes and what it can't say

- **It changes nothing in the product.** It sizes the scoped route: on these multitracks about a third to a half of
  songs offer a window where the requested guitar plays alone, by the reading. Where other guitars play, such a window
  gives a few 10-s sections at best.
  - In scope, leads are the weak case (0.109 in the locator).
  - Heavy parts in multi-guitar arrangements offered none.
- **What it can't say:**
  - How often released records offer such windows: these are multitracks, mostly of small bands, and probably
    optimistic.
  - Whether the window is exposed enough to search on: exposure is unknown, with no mix-level stems.
  - Whether a rule can find the windows from the mix: W1, held.

## Open item

- **`pipeline_fix.t95` uses z above 30 degrees of freedom,** though its docstring says t. This report gives t
  intervals (the audit's). The shared helper is not changed here, since other results use it; it is left for a
  separate fix and check of the results that rely on it.
