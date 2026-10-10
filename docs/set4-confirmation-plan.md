# Confirming the rebuilt-DI chooser on fresh material: plan (v2, approved and run 2026-10-10)

Drafted 2026-10-10, revised the same day after an independent review
(`tmp/set4-confirmation-review.md`, local). **Approved and run the same day:
[results](set4-confirmation-results.md), outcome confirmed.** Originally: nothing in it
runs until the user approves. It spends held-out material, and it is recorded in the held-out ledgers.

## What changed from v1, and why

- **v1's claim no longer fits the evidence.** v1 tested "the 3 kHz cut chooser beats a
  fixed driven preset" on set 4. On set 3 development that edge (−0.143) comes almost
  entirely from clean parts, where a driven preset is the wrong baseline anyway.
- **By gain class** (fixed-level measure, both halves, band-clustered 90% interval):

  | development parts | chooser vs the product's starting preset | oracle | W / T / L | bands |
  |---|---|---|---|---|
  | clean (vs the clean template) | −0.198 (−0.275 to −0.120) | −0.232 | 15 / 0 / 0 | 3 |
  | crunch (vs the fixed driven preset) | −0.146 (−0.220 to −0.072) | | 28 / 1 / 4 | 5 |
  | **clean and crunch together** | **−0.162 (−0.218 to −0.106)** | −0.215 | 43 / 1 / 4 | 7 |
  | high-gain (vs the fixed driven preset) | +0.027 (−0.048 to +0.103) | −0.17 | 26 / 5 / 20 | 8 |

  On clean and crunch parts the chooser reaches about 76% of the oracle's gain, and all
  seven band means are negative (−0.04 to −0.25). On high-gain it has no edge, though
  the oracle shows headroom of −0.17. That fits the finding that heavy distortion
  destroys the detail the rebuild needs.
- **So the product question is per gain class:** does the chooser beat what `generate`
  would start from (the clean template for a clean part, the shipped driven preset for a
  distorted one)? And it is tested where it should work. Set 4 (9 of 13 parts
  high-gain) can't test that alone.
- **The judge was validated by ear on clean-to-crunch PR12,** so the primary claim sits
  in that regime and doesn't wait for the heavy-tone listening check. The high-gain
  stratum is report only.

## Material

- **Sets 1–2 held-out sessions** ([validation-datasets.md](validation-datasets.md)):
  - 17 sessions with 39 parts that have a DI, from about 11 bands, mostly clean to
    crunch.
  - Their rule allows a declared test, and a used session stays held out for the next
    one.
  - None was used by the network, the chooser, the measure's average balance or any
    choice. The six used in the 2026-09-28 SW50R listening check stay eligible under
    that rule.
- **Set 4** ([validation-set4.md](validation-set4.md)): every part, with the declaration
  hash pinned at approval. It is spent by this test.
- **Gain class per part,** fixed before any scoring by set 3's catalogue rule: the
  session-level class from the amp track (set 3's tools, `gainmeasure.py`; set 4 already
  has it). It assigns each part to a stratum:
  - **clean:** the baseline is the clean template with the effects off (template+R);
  - **crunch:** the baseline is the shipped driven preset of that amp;
  - **high-gain:** the same baseline as crunch, report only.
- **Flagged parts** (set 4's Last Legacy and Lead Inc ElecGtr3 timing, Decypher's DI
  touching full scale) are kept. A sensitivity run without them is reported.

## Frozen inputs

- **Network:** `models-set3/fold2.pt` (sha256 `16b2b734…`, pinned in full at approval),
  CPU inference, low-passed at 3 kHz and played at −22.9 LUFS.
- **Measure:** the average balance `average-fold2.npy` (sha256 `9aa3c3bf…`), loaded from
  file and never regenerated.
- **Menus:** set 3's three amp menus.
- **Choosing:** on each half against the amp track, at lag −52, with the reference-proxy
  fallback. If every candidate is refused, the part takes its baseline (ratio 0).
- **The judge:** `flat` weighting, `recording` bands. Judge v2 is reported as a
  sensitivity check only, at the commit pinned at approval.
- **Baselines:** the presets `generate` ships, made dry as in the measurement: SW50R
  Wall Of Doom, PR12 Vintage Metal, AC20 Dirty Coil Rhythm. The fixed-level rule's
  presets (Modern Metal, Raw N Crunchy, within 1.2%) are reported as a sensitivity check.
- **Measure and scoring:**
  - the true DI re-equalised to the average balance, at −22.9 LUFS, scored on the other
    half at the part's judge lag;
  - each part-amp cell averages both directions, over all three amps;
  - a cell whose measure is refused is dropped from every comparison and reported.
- **The harness reproduces development first.** Before freezing, the confirmation
  harness must reproduce these development figures from the stored set-3 distances:
  −0.162 (clean and crunch vs baseline), −0.143 (all vs the leave-band-out constant),
  −0.260 (the oracle).

## Statistics and gates

**Statistics:**
- **The unit is the band.** The primary estimate is the part-weighted mean log ratio.
- **Interval:** a band-clustered 90% two-sided interval (t, bands − 1 degrees of
  freedom). "Below 0" is a one-sided test at α = 0.05.
- **Also reported:** the band-weighted mean, wins/ties/losses, the exact band sign flip,
  and the range with each band left out.

**Gates, on clean and crunch parts pooled, in this order:**
1. **Positive control.** The oracle's interval against the baseline must lie below 0.
   Otherwise the test is **uninformative**: the material can't resolve choosing at all.
2. **Primary: the chooser vs the baseline.**
   - **Confirmed:** its interval lies below 0, its mean stays negative with any one
     band left out, and more than half the bands are negative.
   - **No meaningful edge:** the lower bound is above −0.05.
   - **Inconclusive:** anything else.

**Reported, not gates:**
- each stratum alone (clean, crunch, high-gain);
- per amp;
- the uncut rebuilt DI;
- the tonal and temporal parts;
- the drive bias;
- judge v2.

## What each outcome does (declared)

- **Confirmed:** `generate` gets the chooser as an option for clean and crunch songs.
  It rebuilds the DI from a separated stem, renders the menu and offers the closest
  presets on the audition page. Stems are untested, so the option ships labelled
  experimental, and a stem check follows. High-gain songs keep the fixed driven preset.
- **No meaningful edge:** the rebuilt-DI chooser is closed for the product. The fixed
  baselines stay.
- **Inconclusive:** nothing ships. The result routes the next round: more fresh bands,
  or the stratum it points to.
- **Uninformative:** nothing ships, and the material's limits are reported.

**In every case,** the held-out sessions of sets 1–2 stay held out for a later declared
test, under their rule. Set 4 is spent.

## Power

The expected size is the development result shrunk by half, for forking: about −0.08.
From resampling development's clean and crunch band means, with 9 to 12 bands, a
"confirmed" result has about 87–97% power at that size, and about 100% at the full
development size.

- **These figures are optimistic.** Development has only 7 such bands, so the spread
  between bands may be larger on new material.
- **The final count is stated in the approval request,** with power re-estimated after
  gain classing. Classing reads the amp tracks' level statistics only, not any method's
  output.

## Before running

- the user's approval;
- gain classing of the sets 1–2 held-out parts, with the counts per stratum and band;
- a committed manifest of every frozen input and hash, including the harness's
  reproduction of the development figures;
- held-out ledger entries;
- an independent reviewer, who re-derives the result before it is reported.


## Approval and authorization (2026-10-10)

**Approved by the user on 2026-10-10** (draft v2, as written above).

**The sets 1–2 held-out parts this test may use:** the 27 usable parts with a DI, from
17 sessions. The block below is what `research/build_validation_crops.py`
checks. Crops follow crop rule 2 (`di-activity`), into
`~/ndsp-presets/references/validation-crops-confirm/`.

**Before any rendering,** each part's lag is measured with set 3's waveform same-take
test (`gcc.py`), and its gain class with set 3's `gainmeasure.py` on the whole session's
amp track. Neither reads any method's output.

```json
{
 "schema": "held-out-listening-test-v1",
 "test_id": "confirm-rebuilt-di-chooser-2026-10-10",
 "parts": [
  "telefunken/57 Chevy/GTR 1",
  "telefunken/57 Chevy/GTR 2",
  "cambridge/That's How I Got To Memphis/ElecGtr3",
  "cambridge/That's How I Got To Memphis/ElecGtr3DT",
  "guitar-techs/P3_music excerpt 02/02",
  "guitar-techs/P3_music excerpt 06/06",
  "guitar-techs/P3_music excerpt 10/10",
  "guitar-techs/P3_music excerpt 11/11",
  "cambridge/It's My Right/Gtr3",
  "cambridge/Semantics/ElecGtr08",
  "cambridge/Semantics/ElecGtr09",
  "cambridge/Sugar - Faith/ElecGtr1",
  "cambridge/Sugar - Faith/ElecGtr3",
  "cambridge/Sugar - Faith/ElecGtr6",
  "cambridge/Sugar - Faith/ElecGtr9",
  "cambridge/All The Same/ElecGtr12",
  "cambridge/All The Same/ElecGtr13",
  "cambridge/All The Same/ElecGtr14",
  "cambridge/All The Same/ElecGtr15",
  "cambridge/One Flip Flop/ElecGtr3",
  "cambridge/Stalker/ElecGtr01",
  "cambridge/Stalker/ElecGtr02",
  "telefunken/Pretty Peace/GTR",
  "telefunken/Safety/GTR",
  "telefunken/Bad Influence/Guitar",
  "telefunken/Die In Denver/Guitar",
  "telefunken/Past Dues/GTR"
 ]
}
```

## Preparation (2026-10-10, before any rendering or scoring)

**Crops:** all 27 authorized parts, under crop rule 2, in
`~/ndsp-presets/references/validation-crops-confirm/`.

**Lags and gain classes:** `learn/confirm_prep.py` (`prep.json` beside the crops).

**Exclusions, by set 3's waveform rule** (at least 3 windows, at least 80% in step,
peak-to-sidelobe at least 2), applied as set 3 applied it. 7 parts fail and are
excluded:
- Guitar-TECHS P3 excerpts 02, 06 and 11, and Forkupines Semantics ElecGtr09: their lags
  are consistent, but on 1–2 windows only;
- Semantics ElecGtr08: peak-to-sidelobe 1.38;
- Lights Off Clarity All The Same ElecGtr12 and 13: in step on 31–38% of windows only,
  probably different takes.

**What remains from sets 1–2:** 20 parts (13 clean, 7 crunch) from 11 bands:
- Rebecca Haviland, Chris Coltraine, Guitar-TECHS P3 (set 1);
- Boogie Snakes, Forkupines, Lights Off Clarity, The Maybe Next Years, Tim Taler, Briana
  Maia, Catbite, Wild & Co (set 2).

The band is the session's artist, as set 2 records it, and the named artist for set 1.

**Set 4 is pinned** at the declaration on main: `docs/validation-set4.json`, sha256
`6aa7a8c3…25e710ee`, with 13 parts from 5 bands. The four Internet Archive sessions now
being added are not part of this test, and stay unused.

**Stratum counts across both sources:**
- **clean:** 13 parts, 8 bands (a counting slip, "9", was corrected before rendering);
- **crunch:** 7 parts from sets 1–2 plus set 4's crunch parts;
- **high-gain:** set 4's 9 parts, report only.

The run harness is `learn/confirm_run.py`. Its development reproduction is committed
before any set-4 or sets 1–2 rendering.

**The harness reproduces development** (`learn/confirm_run.py dev-check`, from the stored
set-3 distances): −0.162, −0.1433 and −0.2599, matching the plan. The frozen manifest is
`docs/set4-confirmation-manifest.json`, committed before any rendering.
