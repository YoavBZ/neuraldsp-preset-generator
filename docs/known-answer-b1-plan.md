# Known-answer test songs, pilot B1: plan (part B's amendment)

Declared 2026-10-18, before any of its renders. This is the amendment that
[clean-di-library-plan.md](clean-di-library-plan.md) part B asks for before any B render ("B1's
exact items, presets and seeds"), with that plan's review items 13–16 built in. Part B's question,
estimands, recipe and power argument stand as declared there; this document fixes what B1 runs.
Development data only; estimates with intervals, no pass/fail bars.
- **Code:** `learn/known_answer.py`, tests `tests/test_known_answer.py`.
- **Runner:** `learn/selfrender_run.zsh` (B1 first, then part C, [pretrain-set-plan.md](pretrain-set-plan.md)).
- **Ledger:** `known-answer-b1` in [`dev-test-ledger.json`](dev-test-ledger.json).
- **Data:** `~/ndsp-presets/learn/known-answer/b1/`.

**Status:** declared; review pending. Renders start only after the overnight runs end.

## The question (unchanged)

From a full song mix whose guitar preset is known, how close does arm A's adopted recipe land?
The recipe: the rebuilt-DI main stage (52 renders), shrink 0.5, fallback to S, the htdemucs stem,
C′'s rebuild (`arm_a_mega53.recipe`, `objective`, `fallback_reason`, unchanged). Two outcomes:
1. **log(d_A / d_S)** on the held half: the judge distance from the true DI's render through arm
   A's output to the truth, against S's;
2. **the knob error** |θ_A − θ_true| against |θ_S − θ_true| (unit scale), on the truth's amp only.

Arm **O** runs the same recipe with the isolated truth as the stem: A − O is the separator's share.

## The songs, their DIs and sections

| Song | Band (cluster) | Primary DI | Second DI (two-guitar item) | Eligible sections on the primary |
|---|---|---|---|---|
| Heather Jane | Chris Coltraine | ElecGtr1 | ElecGtr1DT (its double) | 24 non-overlapping clean |
| Bourbon | Rebecca Haviland | GTR 2 | GTR 1 | 1 clean; hum-flagged otherwise |
| Collide With Me | Rebecca Haviland | GTR 1 | GTR 2 | none clean; hum or hum+hiss flagged |
| Still Flyin' | The Apprehended | ElecGtr03 | ElecGtr04 | 4 non-overlapping clean |

- **The primary DI** is the song's DI with the most clean non-overlapping sections, then the most
  eligible ones, then the first by name (`primary_di`, tested).
- **Eligible sections:** part A's non-overlapping clean sections; when a song has fewer than 4,
  its activity-passing, non-overlapping sections whose only flags are hum or hiss. Bourbon and
  Collide With Me are in that case: their Telefunken DIs carry strong hum (−29 dB re playing on
  Bourbon GTR 1). **This is a deviation from part B's "clean sections only"**, declared here. The
  truth is rendered from the same DI, so the known answer stays exact; the hum is in the record as
  it would be on a real amp track. These two songs are also reported as their own row
  (`noisy_di`).
- **The listening check is not yet read.** The screens may still move; the report lists every
  scored section's part-A flags, so a later amendment can see which items it touches.
- **Sections per song:** four, non-overlapping, drawn by `random.Random(20261050)` among the
  eligible ones: s1 and s2 for the single and two-guitar items, s3 before and s4 after the switch.
- **The switch point:** the 5-s grid boundary nearest the song's middle at which the DI rests (no
  playing 100-ms frame within ±50 ms), else a 50-ms crossfade there; moved to the nearest grid
  boundary that leaves at least one eligible section on each side.

## The items

| Item | Truth | Mix | Arm A sections | Arm O sections |
|---|---|---|---|---|
| 1 single | P1 on the primary | with vocals | s1, s2 | s1, s2 |
| 2 single, no vocals | P1 | without vocals | s1, s2 | (same as 1) |
| 3 switch | P1 before the switch, P2 after | with vocals | s3 (P1), s4 (P2) | s3, s4 |
| 4 two guitars | P1, plus the second DI through Q | with vocals | s1, s2 | (same as 1) |
| 5 no other guitars (The Apprehended only, review item 15) | P1 | with vocals, less every other guitar track | s1, s2 | (same as 1) |

Arm O's stem is the primary's isolated truth at its mix level, which is the same for items 1, 2, 4
and 5. So it is searched once per (section, truth), and its rows are shared.

## The truth presets (seeded, realistic, no metal)

- **Classes per song** (declared): Heather Jane clean, Bourbon edge-of-breakup, Collide With Me
  clean, The Apprehended crunch. P2 (the switch) is crunch after a clean or edge P1, clean after a
  crunch P1; Q (the second guitar) has P1's class on another amp.
- **Amps:** P1's amp per song by `random.Random(20261051)`, uniform over PR12, SW50R and AC20; P2
  and Q each on a different amp from P1, drawn by the same generator.
- **The class of a factory preset is measured, not named.** Per (song, amp used), every dry factory
  preset of that amp (`phase2_set3.menus`, about 37) is rendered once on s1 of the primary and
  classed by the project's classifier (`gainmeasure.measures` against the DI at the 52-sample
  latency, `classify`). That is the menu scan, about 37 renders per (song, amp).
- **Clean or crunch truth:** a preset of that measured class, not the class's S, uniform; each
  continuous dimension of `knob_ceiling.space` moved by a uniform offset within ±0.15 of its range,
  clipped; switches and mics kept; every other module as the factory preset has it (so the truth
  may sit outside arm A's search space, as a real record does).
- **Edge-of-breakup truth** (review item 16): a measured-crunch preset (not S) with its input gain
  drawn uniform from the lower half of the measured-crunch presets' input-gain values on that amp
  (minimum to median); the other continuous dimensions jittered as above; arm A starts from the
  crunch S.
- **The check:** the jittered truth rendered on s1 is classed again. A clean truth must read clean,
  a crunch truth crunch, an edge truth clean or crunch (never high-gain). Otherwise the jitter is
  redrawn, at most 20 times, then the preset; every draw is logged.
- Arm A's S is the class's starting preset (edge uses crunch's): the true class is oracle
  information, as in stage F (review item 16).

## Building the songs

- **The DI level is one per DI track:** `di_w` = the measure-DI treatment
  (`song_bank.measure`: the average-guitar balance, then −22.9 LUFS) applied to the whole DI.
  Everything is rendered from `di_w`; a section's judge DI is `di_w`'s slice, not re-levelled.
- **Whole-track truth renders** (one render each, `isolate=True`, 0.25 s of silence prepended and
  trimmed), shifted 52 samples earlier so they line up with the session.
- **The record for the judge** is the truth rendered from the section's own slice (with 0.25 s
  before it), exactly as the judge renders every candidate. A **repeat check** per scored section
  compares it with the whole-track truth's slice: their judge distance, against d_S, is reported.
- **Level in the mix:** for the development songs, the truth's loudness over the DI's playing frames
  matches the summed loudness of the part's real amp and mic tracks there. For The Apprehended (no
  amp tracks), the guitar sits −7.9 dB under the backing over those frames (multi-section step 1's
  median). The second guitar: its own real tracks' level (development songs), or 6 dB under the
  primary (The Apprehended).
- **The backing:** every session track at unity, less every guitar DI, less the rendered DIs' own
  amp and mic tracks, less the leaking tracks (below); with and without vocals (by name: `vox`,
  `vocal`). Item 5 also drops every other guitar track (The Apprehended's 11, 12, 16–20).
- **Live-room leakage (review item 14):** each kept track's coherence with each rendered DI's own
  amp tracks, part A's bleed measure (mean magnitude-squared coherence, 100 Hz–6 kHz, 16 kHz, on
  frames where the amp track plays, less the 1/N bias). Over 0.05 (part A's bleed threshold): the
  track is dropped. Measured before declaring (zero renders):
  - **Collide With Me** drops the drum overheads, hats, kick (out), rack tom and the bass amp
    (up to +0.12);
  - **Bourbon** drops the bass amp (+0.10) and one vocal mic (+0.05);
  - **Heather Jane** drops nothing (all ≤ 0.001).

  A song that loses more than half of its backing's power to drops is reported as its own row as
  well; all drops are listed in the report.
- **Contexts:** 30 s of the item's mix centred on each scored section (clipped at the song's ends),
  the same window for every item and arm.
- **Separation:** htdemucs (`learn.separate.GuitarSeparator`, CPU, 2 threads), behind the
  separation gate (no render beside it), then the 10-s crop.
- **Rebuild:** C′ fold 2 (`models-cprime/fold2.pt`, the legacy final network). None of the three
  bands is in any C′ fold's training pool (checked: `di_fine_structure.train_pool_bands` over the
  three caches), and the code asserts it; then −22.9 LUFS, as `arm_a_mega53.rebuild_parts`.

## Renders and hours

Per scored section and arm: 3 amps × (1 warm-up + 2 directions × 55) = 333. S per (section, amp):
a warm-up and its judge, 6 per section.

| | Per song | B1 |
|---|---|---|
| Menu scans (about 37 per amp used; up to 3 amps) | about 111 | about 450 |
| Truth checks, whole-track renders, section records, repeats | about 40 | about 160 |
| S | 4 sections × 6 = 24 | 96 |
| Arm A | 8 sections × 333 = 2,664 (10 for The Apprehended: 3,330) | 11,322 |
| Arm O | 4 × 333 = 1,332 | 5,328 |
| **Total** | | **about 17.4k** (below part B's 22k estimate: arm O is shared across items) |

About **2.7 h** on 3 shards at arm A's rate, plus about 15 min of htdemucs (34 contexts of 30 s)
and a few minutes of C′ on the CPU. No fixed cap: the search is the adopted recipe's fixed 55 per
direction, so the count is the design's.

## The readout (descriptive; 3 band clusters, 2 degrees of freedom)

Units are (item, section, amp, direction); weights go unit → section → song → band.
- **Arm A against S,** primary: items 1, 3 and 4 (with vocals, every guitar), all amps. Rows: the
  truth's amp only and the other amps; each item kind; item 2 (no vocals) paired with item 1; item 4
  paired with item 1 (a second guitar); item 5 paired with item 1 (The Apprehended's other
  guitars); `noisy_di` (Bourbon, Collide With Me) against the rest; per class.
- **Arm O against S, and A − O** (the separator's share), on the shared sections.
- **The knob error** (truth's amp): per knob, over the identifiable knobs (input gain and the amp's
  tone knobs: PR12 treble and bass; SW50R treble, mid and bass; AC20 cut), and the level knobs
  (volume, level, power) apart. Mics and switches as agreement shares.
- **For B2's size (review item 13):** the between-band SD of the band means, its 90% upper bound
  (χ² with 2 degrees of freedom), and n = (t · max(upper bound, 0.069) / 0.03)². B2's amendment
  uses that number; B1 decides nothing by itself.
- **Also:** the truth repeat check, the fallbacks to S, the activity fallbacks, the menu scans'
  class counts, the leakage drops, and the songs against MUSDB18's track list (htdemucs trained on
  MUSDB18; checked by name before the report and reported as a row).

## Caveats (stated, review item 16)

- **In-family best case:** the truths are Morgan presets on arm A's own amps.
- **The truth may use modules arm A cannot reach** (a factory preset's drive pedal or EQ), which is
  realistic and counts against A and S alike.
- **The Apprehended's backing** carries amp-recorded high-gain rhythm guitars, outside the scope;
  item 5 measures what they cost.
- **Two of four songs are noisy DIs** (hum), declared above.
- **3 band clusters:** every interval is wide; this pilot's job is the spread for B2.

## Code (written and tested before any render)

`learn/known_answer.py`, subcommands `plan` (zero renders: songs, DIs, sections, switch points,
backings, leakage), `truth` (the menu scans, draws and truth renders; one process), `mix`,
`separate`, `rebuild`, `search --shard i/3`, `report`. `learn.known_answer (truth|search)` is added
to `learn/local_objective.RENDERS`, and `learn.known_answer separate` to its separations.
Unit-tested with fakes: the primary-DI rule, the section eligibility and draw, the switch point,
the backing track rules (DIs, own tracks, vocals, other guitars, leakage), the truth draw (classes,
offsets, the edge rule, redraws), the level matching, the unit list and render counts, the
sharding, the weighting and the B2 sizing.
