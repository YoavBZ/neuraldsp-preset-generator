# Knob ceiling: how much closer do searched knobs get than the best menu preset? Plan (development)

Declared 2026-10-13, before any search result. Revised the same day after an independent
review (`tmp/knob-ceiling-plan-review.md`, local), before the main run; all seven required
changes are made below. Development data only, the true DI, no model,
no training. Code: `learn/knob_ceiling.py`; tests: `tests/test_knob_ceiling.py`.

## Why

Every "a perfect DI gains only about 12–17%" figure so far comes from **ranking the menu**:
111 dry presets on the three Morgan amps (`P.menus`: 108 factory presets and the 3
templates). No knob was ever moved. So
the headroom of continuous settings (what a model that predicts settings, rather than picking
a preset, could reach) is unmeasured. This test measures it, with the true DI, so it is a
ceiling: no song-to-DI loss.

## Data

- **The parts:** `learn/songs_check.parts()`, gain class clean or crunch: **25 parts, 15
  bands** (20 clean, 5 crunch), all development (sets 1–2 development and set-3 development
  parts). Asserted in code (`check_parts`: the counts, and each part's development source).
No held-out audio is read.
- **The DI:** the measure DI ("measfix"): the true DI re-equalised to the average guitar
  (`learn/direc/cache/average-fold2.npy`) at −22.9 LUFS, as `confirm_run.build_di("measfix")`.
- **The judge:** `aligned_distance` with the flat options (`R.JUDGE_OPTIONS["flat"]`, the
  default), at the part's judge lag, halves A (1.0–5.5 s) and B (5.5–10 s). The judge
  removes level, so output levels are not searched.
- **Refusals:** the judge refuses a half it can't score (silence). A render refused on the
  search half counts as infinitely far. A direction is skipped if the start S or the menu
  oracle M is refused on either half; a cell with both directions skipped is dropped and
  counted. (`telefunken-Honey-GTR` has half B refused for every menu preset, so its three
  cells are expected to drop.) A comparison with a refused side drops that direction for it.

## Conditions, per cell (part × amp, 75 cells)

- **S:** the product's starting preset for the part's class (skills/generate step 4), dry:
  - clean: Royally Ambient (PR12), Pedal Platform Clean (SW50R), Low-Watt Americana (AC20);
  - crunch: Modern Metal (Pick Hard) (PR12), Hair Metal (SW50R), AC20 Mid-Gain Drive (AC20).
- **M:** the menu oracle: the amp's best dry factory preset on the search half.
- **K_M:** a knob search starting from M, 200 renders.
- **K_S:** a knob search starting from S, 150 renders (the product-realistic case).
- **EQ:** a second search from K_M's best over the amp's EQ, 100 renders.

**Cross-half:** each search sees only one half (the search half); its result is scored on
the other half (the held half). Both directions are run (A→B and B→A), and a cell's number is
the mean of the two. The search-half numbers are reported beside, labelled **in-sample
(optimistic)**. M is also picked on the search half.

The menu is re-rendered fresh for every cell (the amp's 31–45 presets), not reused from
stored renders.

## The search space

Stored units; continuous settings are searched on a 0–1 scale over the range below.

**K (both K_M and K_S):**

| setting | range | kind |
|---|---|---|
| `parameters/inputGain` | −20 to +12 dB (amendment 2; the manifest allows ±24) | continuous |
| PR12: `pr12Volume`, `pr12Treble`, `pr12Bass` | 0–1 | continuous |
| SW50R: `sw50rVolume`, `sw50rLevel`, `sw50rTreble`, `sw50rMid`, `sw50rBass` | 0–1 | continuous |
| SW50R: `sw50rBright`, `sw50rTrebleBoost`, `sw50rInputMode` | on/off | switch |
| AC20: `ac20Volume`, `ac20Cut`, `ac20Power` | 0–1 | continuous |
| AC20: `ac20Bright`, `ac20BassTreble` | on/off | switch |
| `cabParameters/leftMicType`, `rightMicType` | the 10 internal mics (custom IR never) | categorical |
| `left/rightCabPosition`, `left/rightCabDistance` | 0–1 | continuous |
| `rightCabMicLevel` | −40 to +6 dB (the balance of the two mics; the left stays) | continuous |
| `rightCabActive` | on/off | switch |

**EQ stage:** the amp's 9-band EQ, `{amp}EQBand1–9` (−12 to +12 dB), `{amp}EQHpf` (20–500 Hz,
log scale) and `{amp}EQLpf` (1–20 kHz, log scale), with the EQ switched on. An EQ that was off
is first set flat (bands 0, HPF 20 Hz, LPF 20 kHz) before switching on.

**The left mic is left out** when the start has the left cab off (4 menu presets do): the
search can't turn it on, so its settings can't change the sound.

**Kept from the starting preset (not searched):** the pedals (compressor and the two drives:
on/off and knobs), the room mics, pan, phase, and the selected amp. **Off, as in the menu:**
reverb, delay, tremolo, doubler, gate, the spring reverb, transpose. **Not searched because
the judge removes level:** `outputGain`, the left mic level.

The pedals are a stated limit: a pedal-on/off search is a possible second pass, not part of
this plan. The PR12 crunch start runs two pedals (a boost into a second drive), which the
search can't turn off; this is noted beside the crunch numbers.

## The optimiser

As amended (amendments 1 and 2 below): `knob_search`, deterministic for its seed (20261013;
the EQ stage uses 20261014). Every distinct setting is rendered once (cached by its settings).
Its stages, on fixed shares of the budget:
1. **Main (35%):** a coordinate search with shrinking steps (`coord_search`). A sweep visits
   the settings in a seeded random order; per setting it tries a continuous setting ± the
   step (0–1 scale, clipped) or a switch flipped, and keeps the best improving candidate. The
   mics are tried (every other mic) from the second sweep, once per step size, so the knobs
   move first. After a sweep that improved, Hooke–Jeeves pattern moves continue in the
   sweep's direction. A sweep without improvement halves the step (from 0.25, stopping below
   1/64).
2. **Mic alternatives (35%):** every other value of both mics, left and right interleaved,
   each set on the incumbent and followed by a quick re-tune of the knobs that helped most in
   stage 1 (an equal share each: in practice the mic render plus one or two knob renders, 2
   at K_S and 3 at K_M).
3. **Restarts (20%):** the two best alternatives, each with a short search of the non-mic
   settings from step 0.125 (15–20 renders each, less than one full sweep). In v6 the
   largest gains came in this stage.
4. **Final (the rest):** the full search again from the best so far.

Without mics (the EQ stage), stages 2–3 are skipped and their share goes to the final stage.
The renders and best value of every stage are stored.

Each evaluation is one render and both halves scored; the search uses only its half. The
renders run on **6 reused plugin processes** (`process_policy="reuse"`), sharded by cell
(part × amp), with numpy limited to one thread per process.

**The budget:** per cell, the amp's menu once (111 renders per part over the three amps),
then per direction 200 + 150 + 100. In total about 25 × 111 + 75 × 2 × 450 ≈ **70,300
renders**, at about 1.5 s each (render plus scoring) without contention. On 6 processes on an
8-core machine: **about 6–9 hours.**

**Stored:** per cell, every menu distance, every evaluation of every search (both halves),
each search's incumbent curve, the best settings and the best render (FLAC) per search and direction, under
`~/ndsp-presets/learn/knob-ceiling/cells/<part>/<amp>/`.

## Controls (before the main run)

1. **Repeat floor (measured 2026-10-13 on one part):** a repeat render of the same settings is
   nearly identical after the first 0.5 s (the knob-change ramp), so the judge's distance is
   the same to about 1e-4 (renders are not bit-identical, but the judge's distance moves by
   at most 1.7e-4). The render noise floor is negligible. The control re-checks this on every control cell,
   including after another preset in between.
   - **Checked on every cell of the main run, free:** K_M's first render repeats M, and K_S's
     repeats S, both already rendered in the menu. The deviation is stored. **If any exceeds
     0.005 in log ratio, the run stops** (the shard raises) and the floor is re-examined.
2. **Positive control:** 2 parts (the first development clean and crunch parts from sets 1–2,
   by name) × PR12 and SW50R = 4 cells.
   - The "recording" is the starting preset S with five settings moved, off the search's
     step grid: volume +0.17, treble −0.21, bass (PR12) or mid (SW50R) +0.13, input gain
     +5.3 dB and the left cab position +0.31 (each reflected inwards if it would leave its
     range), and the left mic changed (mic index + 4). It is rendered through the part's DI.
     Its lag is 0.
   - The search (K, 200 renders, half A) starts from S unmoved.
   - **It passes** if, on all 4 cells, the held-half (B) distance falls to at most 0.3 × the
     start's, and on at least 3 of 4 cells, at least 3 of the 5 settings land within 0.1 of
     their targets (on the 0–1 scale) and the mic is exactly recovered. (Other settings can
     compensate, so an exact recovery of every setting isn't required.)
   - A first version of the control, with offsets on the step grid (−0.25 is exactly the first
     step), was stopped after one cell on the review's advice (its log is kept as
     `control-v0-ongrid.log`). It isn't counted.
   - **If it fails,** the optimiser or the budget is wrong. It is fixed and the control re-run
     before the main run, and the change is recorded here.
   - The control's convergence curve may **lower** the budgets (never raise them) before the
     main run, if it shows no gain after a render count. Any change is recorded here first.
3. **The extremes check:** every best setting that the search moved to the end of its range is
   flagged. The share of K_M cells with such a flag is reported. The judge is known to like
   spectral extremes (ground-truth audit item D-H3), so the listening check below favours
   flagged cells as well.

The control reads no recording: only the parts' DIs and renders.

## Statistics

As `learn/confirm_run.stats`: per cell, the log ratio of distances on the held half (mean of
the two directions). Reported:
- the part-weighted mean, with a band-clustered 90% t-interval (bands − 1 df);
- the band-weighted mean, the bands negative, and leave-one-band-out;
- for clean + crunch, clean alone, and crunch alone. Crunch has 5 bands: descriptive only.

**The headline numbers:**
- **(a) M vs S:** the menu's headroom over the product's start (reproduces the old figure);
- **(b) K_M vs M:** what the knobs add beyond the menu;
- **(c) K_S vs S** and **K_S vs M:** what a search from the product's start reaches;
- **(d) EQ vs K_M** and **EQ vs M:** what the EQ adds on top.

Also, all declared now:
- the in-sample versions;
- **the convergence:** K_M's incumbent against M on the held half after 25, 50, 100, 150 and
  200 renders (so the EQ stage's extra 100 renders can be compared with K_M's own late gain);
- the share of K_M searches with a setting at a limit;
- **per amp;**
- **the best amp per part:** in each direction, M's amp is chosen by M's search-half
  distance, and K_M's amp by K_M's; the held-half log ratio, averaged over the directions. So
  knobs rescuing a badly suited amp don't inflate the per-amp means;
- the skipped directions and dropped cells, and the largest repeat deviation.

## The reading (declared; descriptive, not a gate)

On (b), cross-half, clean + crunch:
- **Knobs add little:** the band-weighted and part-weighted means are both at −0.04 or above
  (the judge's near-tie range). The menu is near the ceiling, and the old reading stands.
- **Knobs add a lot by the judge:** the band-weighted mean is at −0.10 or below, with most
  bands negative. The headroom counts as real, and predicting settings (not ranking a menu)
  as worth pursuing, only if the listening check agrees.
- **In between:** reported as such.

(d) is read the same way, separately: an EQ gain could be the judge's spectral weakness as
much as real tone, so it needs the listening check before it counts.

## Listening

Cells: the 4 with the largest cross-half K_M gain, at least one flagged at a limit (if any),
and **2 drawn at random** (seed 20261013, among the cells not already chosen), so the page
shows typical cells as well as the best. An unlabelled A/B page: the recording, the M render
and the K_M render (and the EQ render, where it adds), through the true DI, **on the held
half**: the settings searched on half A are played on half B, and the reverse. The cell's
direction is the one with the larger held-half gain for the top 4, and direction A→B for the
random 2. The user can check that the
judge's gain is audible. Built under `~/ndsp-presets/listening/knob-ceiling/`; the product
session attaches it.

## Amendment 1 (2026-10-14): the control failed; the search is a lower bound

Made after the controls and **before the main run**: no recording has been searched.

**The positive control failed as declared, under six versions of the search** (logs and
results under `~/ndsp-presets/learn/knob-ceiling/control-*`):

| version | held distance / start (4 cells) | mic recovered | passes |
|---|---|---|---|
| v1: coordinate search, mics in sweep 1 and once more | 0.12, 0.22, 0.25, 0.27 | 1 of 4 | no |
| v2: mics after the knobs move, at every step size (200 / 300 renders) | 0.12–0.25 | 1 of 4 | no |
| v3: v2 plus mic restarts with a quick re-tune (200 / 300) | 0.17–0.34 | 4 of 4 (200), 3 of 4 (300) | no |
| v4: v3, restarts from the start's own knobs (200 / 300) | 0.19–0.53 | 0–1 of 4 | no |
| v5: v3 plus Hooke–Jeeves pattern moves (200), **adopted** | 0.19, 0.25, 0.34, 0.45 | 4 of 4 | no |

The knobs were recovered within 0.1 on 1–4 of 5 settings per cell. More renders (300) didn't
help.

**The diagnosis.** Each setting moved alone through the exact target shows a smooth, V-shaped
distance falling to 0 (`tmp/kc_landscape.py`, SW50R, Drag Me Down): the judge isn't rugged.
But the settings trade off (input gain, volume, treble, mic, cab position), so the exact
target is a sharp-bottomed valley across the knobs. A search that moves a few settings at a
time stalls at about 20–35% of the start distance, with the wrong settings compensating. A
mic sweep that tests every mic and re-tunes the key knobs (v3) found the mics. A random-
direction search was no better in a simulation.

**A realistic calibration (added).** A real recording is never matched exactly. So the
"recording" became the moved preset played with the part's own DI (not re-equalised), while
the search renders the measure DI, as in the main run. The known target settings are then an
achievable, non-zero distance. With the adopted search (v5, 200 renders), its held-half
distance against the target settings' own:

| cell | search vs target settings (log ratio) | share of the gap closed |
|---|---|---|
| Drag Me Down, PR12 | −0.015 (better) | 102% |
| Drag Me Down, SW50R | +0.239 | 89% |
| Prodigal, PR12 | +0.075 | 65% |
| Prodigal, SW50R | +0.115 | 70% |
| **mean** | **+0.104** | |

**What changes:**
- **The search:** `knob_search` as in v5 (superseded by amendment 2's v6) (coordinate search; mics after the knobs move, at
  every step size; Hooke–Jeeves pattern moves; mic restarts with a quick re-tune of the three
  most useful knobs). The budgets stay 200 / 150 / 100.
- **Every searched number is a lower bound on what the settings can reach.** See amendment 2
  for the calibration of the search actually run.
- **The readings of (b) and (d):**
  - **"A lot by the judge"** (band-weighted ≤ −0.10, most bands negative) stands: the true
    gain is at least that. It still needs the listening check to count as real.
  - **"Little"** (both means ≥ −0.04) **no longer says the menu is near the ceiling.** It is
    read as "the search found little: undecided", since the search can fall short of a
    reachable setting (amendment 2: 0.075 on average on the held half, up to 0.26 on one of
    six cells; this is not a cap). The old reading can't be restored by this test.
  - **In between:** as before, reported as a lower bound.
- **The repeat check** stays: v5's exact control re-measured the repeat floor at about 1e-4,
  far below the 0.005 stop rule.

## Amendment 2 (2026-10-14): the search's stages, after a second review

Made after the second review (`tmp/knob-ceiling-control-review.md`, local), still **before
the main run**. The review approved the lower-bound reading and found that v5's stages didn't
run as described: the left mic's alternatives used the whole remaining budget, so the right
mic, the restarts and the final stage got almost no renders, and the control moved only the
left mic. Changes:
- **The stages now have fixed shares** (35% main, 35% mic alternatives with both mics
  interleaved, 20% restarts, the rest final), as described under "The optimiser". A test
  checks that both mics and every stage get renders at budgets 150 and 200.
- **Input gain is searched over −20 to +12 dB** (the factory presets use −20 to +3), so its
  first step is 8 dB rather than 12. In v5 it never moved in 7 of 8 cells.
- **The control covers AC20 too** (volume +0.17, cut −0.21, power +0.13), and moves the
  **right** mic on SW50R and AC20 (the left on PR12): 6 cells. Pass needs 3 in 4 cells
  recovered.
- **Pattern moves** step 1×, 2× and 3× the sweep's move (the review found 1×, 4×, 16×).
- `reading()` prints the amended "little" reading.

**v6, the version that runs** (`control-v6-*`, 200 renders):

| cell | exact: held / start | exact: mic | realistic: search vs target settings, held (search half) | realistic: gap closed |
|---|---|---|---|---|
| Drag Me Down, PR12 | 0.14 | yes | −0.083 (−0.058) | 109% |
| Drag Me Down, SW50R | 0.18 | no | +0.161 (+0.126) | 93% |
| Drag Me Down, AC20 | 0.31 | no | +0.255 (+0.228) | 90% |
| Prodigal, PR12 | 0.46 | no | −0.007 (−0.065) | 103% |
| Prodigal, SW50R | 0.34 | no | +0.052 (−0.044) | 83% |
| Prodigal, AC20 | 0.10 | no | +0.070 (−0.018) | 91% |
| **mean** | | 1 of 6 | **+0.075 (+0.028)** | |

**The exact control still fails** (mic 1 of 6; three cells above 0.3): with an exact copy the
target is a sharp-bottomed valley, as amendment 1 found. **The realistic control** is the one
that resembles the main run. On it the search lands on average 0.075 short of a known
reachable setting on the held half, and 0.028 on the half it searched. It is closer than the
known setting on 2 of 6 cells and short by up to 0.26 on one (it found the moved mic on 3 of
6). On it, the search-half gain grows from 100 to 150 renders and little after (150→200:
−0.001 to −0.031); on the exact control it is still improving at 200 on three cells. K_S's
budget of 150 wasn't calibrated separately. The budgets stay. **The calibration's limits:**
6 cells from 2 parts; the starts are six settings from the target; the only mismatch is the
DI's equalisation, much smaller than a real recording's. The readings
are as in amendment 1: every searched number is a lower bound.

## Optional, report-only

**The judge-exploitation check:** if (b) reads "a lot", each part's held half is also rendered
with other parts' best K_M settings (same amp). If those beat M almost as often, the gain is
the judge liking certain settings, not matching this recording. Declared now; its own budget
is stated before it runs.

## Order

1. This plan, then an independent review. The positive control may run during the review (it
   reads no recording).
2. The control result, reviewed.
3. Message the product session, then the main run (6 processes, `setopt no_bg_nice`).
4. The report, an independent audit of it, then the listening page.

## Stated limits

- **The judge is the measure.** A search that optimises the judge directly can exploit its
  weaknesses. The held half limits overfitting to the notes, not to the judge. The listening
  check is the guard.
- **A local search** from two starts: the true ceiling can only be higher.
- **The pedals aren't searched.**
- **The true DI** (re-equalised): a song-only product has to rebuild or guess it. This is a
  ceiling, not a product number.
- **25 parts, 15 bands, crunch 5 bands.**
