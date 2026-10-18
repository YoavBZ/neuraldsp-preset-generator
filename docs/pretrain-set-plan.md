# A labelled pre-training render set (part C): plan

Declared 2026-10-18, before any of its renders. Part C of the self-rendered dataset track the user
approved on 2026-10-17 ([clean-DI plan](clean-di-library-plan.md) parts A and B). Development data
only. The rules of [`research/ml-plan-2026-10.md`](research/ml-plan-2026-10.md) section 5 apply,
with the user's rules of 2026-10-16: estimates with intervals, no pass/fail bars, evidence-based
stopping, renders and hours declared, and licence-clean open-source tools only.
- **Code:** `learn/pretrain_set.py`, tests `tests/test_pretrain_set.py`.
- **Runner:** `learn/selfrender_run.zsh` (with B1, [known-answer-b1-plan.md](known-answer-b1-plan.md)).
- **Ledger:** `pretrain-set-c` in [`dev-test-ledger.json`](dev-test-ledger.json).
- **Data:** `~/ndsp-presets/learn/pretrain-set/`.

**Status:** declared, then reviewed 2026-10-18 by an independent agent: approved with 12 required
changes, all made as [amendment 1](#amendment-1-2026-10-18-review-changes-before-any-render), which
governs where the two differ. Nothing renders before the overnight runs end, B1 has run, and the
hum-screen amendment's manifest exists (below).

## Why

- **Arm B needs more and better labelled examples.** Its sound-space retrain (B2) beat the old
  model on songs by −0.068 [−0.111, −0.024], most likely from its 2,500 record-like renders
  ([results](song-to-settings-soundspace-results.md)), but it was not shown to beat S. It trained
  on 12.5k examples, from DI windows that were never screened, half of them Guitar-TECHS P1/P2
  exercises that part A found mostly hummy.
- **The rebuild network C′ trains on DI↔amp pairs** from the same unscreened pool (its caches
  include Guitar-TECHS P1, and older renders made before `isolate`).
- **Part A gives a screened DI library:** 875 non-overlapping clean 10-s sections that may train
  (146 min). Rendering them through many settings gives a large, exactly labelled set. Pre-training
  on it, then fine-tuning on real records, is the standard route when real labels are scarce.

The question this plan answers is **how large the set should be**, by a learning-curve pilot, not
by a fixed count.

## What goes in

### The DI sections (the pool)

From part A's manifest (`~/ndsp-presets/learn/clean-di/manifest.json`), read through one filter
(`pool_rows`), so that the hum amendment's rebuilt manifest replaces it without code changes:
- rows that are `disjoint` (non-overlapping clean), `split: library` and `training_ok`;
- every row's path is checked again: its DI is in the inventory as `library` and `training_ok`
  (`assert_training_ok`'s rule, re-implemented here and tested for parity with
  `learn/clean_di.py`), and it passes `set3.is_held_out` and `set4/5/6.covers`;
- **the hum-audit exclusion (asserted in code and tested):** the 10 DIs the part-A audit found
  probably hummy (7 Guitar-TECHS P1 chord files with 102 sections, Prodigal ElecGtr1 and ElecGtr3,
  and Wickerman ElecGtr7: 134 sections) are left out until a dated amendment says otherwise. The
  code leaves out a superset of 11 DIs, 135 sections: also the one Guitar-TECHS P2 chord file with a
  clean section (1 section), since the results' "all 103 of Guitar-TECHS's" counts it.
- **Guitar-TECHS is left out by source** (`EXCLUDE_SOURCES`), declared here: every Guitar-TECHS
  clean section is in the superset today, and its exercises are not songs. A hum amendment that
  clears Guitar-TECHS sections does not bring them in without a further amendment.
- **Never:** part B's known-answer DIs (refused by the inventory rule), any held-out path, set 4–6,
  Guitar-TECHS P3.

**Gate:** part C's `pool` step refuses the manifest whose sha256 starts `22a61fb76b918b25` (the
pre-amendment one); the runner waits for a rebuilt manifest. Part C never renders before the
hum-screen amendment lands.

**Size today** (current manifest, before the hum amendment):

| | Sections | Minutes |
|---|---|---|
| Non-overlapping clean, may train | 875 | 146 |
| less the hum-audit superset | −135 | |
| **The pool** | **740** | **123** |

### The split (by DI and band, declared)

- **`reserve`:** the sections of stage F's 21 DIs (used once, by arm A's fresh test): 102 today
  (11 DIs; Wickerman ElecGtr7 is also in the hum superset). Rendered never in this plan. The reserve
  is by DI: other DIs of the same sessions still train; the `stage_f_session` tag lets later work
  drop them.
- **`val`:** whole bands, never trained on by this plan's models. Seeded (`random.Random(20261041)`)
  over the pool's bands that have a session backing, leaving out the three largest (Eat The Feeder,
  Eggy, Dom McLennon); bands are added in seeded order until the val bands hold at least 15% of
  the non-reserve sections and number at least 8. Their sections render only as validation
  examples.
- **`train`:** the rest.
- **Folds:** every example carries its band's fold from `docs/song-settings-folds.json` (or
  `null` for bands outside it). A model later evaluated on step 3's parts by fold must drop its own
  fold's examples, as arm B's models did.
- **Tagged, not split:** sessions that hold a stage-F DI (`stage_f_session`), and the band's
  part-A tags (bleed status, style, gain class).

### The settings (labels)

Morgan's three amps used in every test: PR12, SW50R and AC20 (`knob_ceiling.AMPS`). The labelled
dimensions are arm B's: `knob_ceiling.space(amp, S)`, that is input gain, the amp's knobs and
switches, and the two mics with their positions, distances, right-cab level and switch. Every
other module comes from S, the product's starting preset of a **base class** (clean or crunch,
p 0.5 each), so a label is complete relative to (amp, base class), as in arm B's bank.

Per example (deterministic from its index; `random.Random` seeded by `SeedSequence([20261040, i])`):
- **amp:** uniform over the three;
- **mode**, drawn:

  | Mode | Share | Centre | Draw around it |
  |---|---|---|---|
  | `factory` | 0.4 | a dry factory preset of the amp, uniform over its menu (`phase2_set3.menus`); its values of the labelled dimensions, on S's other modules | continuous σ 0.1 (unit scale, clamped); mics and switches kept with p 0.7, else uniform |
  | `start` | 0.2 | S of the base class | the same |
  | `wide` | 0.4 | none | continuous uniform; mics and switches uniform |

  The factory centres cover the realistic combinations of the knobs; the wide draws cover the
  space; the starts weight where the product begins.
- **No metal.** Measured on the arm-B bank's stored renders (zero renders, 600 drawn): the
  project's gain classifier calls 28% of uniform draws "high-gain", but its crunch/high-gain line is
  an ordinal compression reading, and the product's own crunch S sits on it (σ-0.1 draws around
  crunch S read high-gain 48% of the time). So the classifier's label is not the scope line. The
  scope line is **the product's crunch start**: per amp, an example is tagged `beyond_crunch_s`
  when its level slope is below the 10th percentile of the `start`-mode crunch-S examples' slopes
  for that amp (computed from the pilot's own examples). On the bank, that excluded 2–14% of
  uniform draws. Tagged examples are stored (features are cheap) and left out of training by
  default.
- **Measured per example** (zero extra renders): the classifier's measures (`gainmeasure.measures`
  of the render against its DI at the 52-sample latency, `classify`), so each example has a class
  and a clean/driven split, and the class shares are reported.

### Rendering

- **The DI:** the section with 0.25 s of the DI before it (silence if the section starts at 0),
  through the measure-DI treatment (`song_bank.measure`: the average-guitar balance, then −22.9
  LUFS), exactly as arm B's bank made its renders.
- **The render:** `knob_ceiling.Renderer` (`isolate=True`, process reuse), grouped by amp. The first
  0.25 s is trimmed, leaving the 10-s section.
- **Shards:** 3 processes, `OMP_NUM_THREADS=1`. The command `learn.pretrain_set render` is added to
  `learn/local_objective.RENDERS` (tested), and each shard waits on the 3-render cap and on any
  separation before every amp group.
- **Disk guard:** every 50 examples a shard checks free disk; below 31 GB it stops cleanly
  (exit 4), and what is stored stays valid.

### What is stored (disk is the constraint)

Measured on 600 stored bank renders (zero renders):

| Item | Format | Bytes per example |
|---|---|---|
| The isolated render's log-mel, both halves (arm B's features: 96 mel, 2048-point frames, hop 480, 30 Hz–16 kHz; halves 1.0–5.5 s and 5.5–10 s; 2 × 96 × 446) | uint8, 0.5 dB steps from −112 dB, zlib | median 55 KB, 95th percentile 62 KB (float16 would be 171 KB raw, 119 KB zlib) |
| Label, settings, measures, LUFS, peak, timings | one JSON line | about 1.5 KB |
| **Train example** | | **about 60 KB** |
| Val example: also the true mix and the true stem, as computed from audio | 3 channels | about 170 KB |
| Audit example (1% of train): also the render as a 16-bit FLAC, and the true mix and stem features | | about 560 KB |

- Quantisation error is ±0.25 dB, far under any effect in arm B's features.
- **The backings** are stored once per section, not per example: the log-mel of the section's
  session backing with and without vocals (about 0.11 MB per section). The backing audio is kept
  (16-bit FLAC) only for the val and audit sections.
- **Mixes are made at training time in the mel-power domain:** mix power = guitar power × g +
  backing power × b. That ignores the cross term. Measured on 600 bank renders against true mixes
  at −7.9 dB: median |error| 0.24 dB, 90th percentile 1.6 dB, 99th 4.7 dB, over bins within 60 dB of
  each frame's loudest. So the set stores one guitar per example and draws a fresh mix level,
  vocal choice and stem leakage every epoch. **Validation always uses true mixes** made from audio
  at render time, so the approximation never reaches the yardstick, and the audit examples measure
  it again on part C's own data.
- **No full audio for C′ (see "C′" below).**

**Pilot footprint:** 40,000 train examples about 2.4 GB, 3,000 val about 0.5 GB, 400 audit about
0.2 GB, backings about 0.2 GB: **about 3.3 GB**. An extension to 80k adds about 2.4 GB. Free disk was
43 GB on 2026-10-18 with the 31-GB guard, so the pilot fits with about 8 GB to spare if the overnight
runs leave the disk as it is; the runner checks before each stage.

### The record-like composition (the declared training mix)

- **Backing:** the section's own session, at the same time: every track of the inventory's mix
  list, less the DI's own amp and mic tracks, less every DI, at unity, as the catalogue's mix role
  does. Dark Ride (no mix list, no amp tracks): every non-DI track of its session. Vocal tracks by
  the catalogue's list, or by name (`vox`, `vocal`) where it has none.
- **Live-room leakage:** in each session, every backing track's coherence with the DI's own amp
  tracks is measured with part A's bleed measure (mean magnitude-squared coherence over 100 Hz–6
  kHz, 16 kHz, on frames where the amp track plays). A track whose coherence exceeds its 1/N bias by
  more than 0.05 (part A's bleed threshold) is dropped from that DI's backings, and the drops are
  logged. Measured on B1's songs: in a Telefunken live room the drum overheads, hats, kick and the
  bass amp cross it (up to +0.12); in a Cambridge studio session nothing does (≤ 0.001).
- **Level:** guitar-to-backing drawn from multi-section step 1's measured development sections
  (971 values; median −7.9 dB, 5–95%: −18.9 to −2.6 dB), the user's "realistic ratios".
- **Vocals:** with p 0.5 (the without-vocals backing otherwise; sessions without vocals have one).
- **Stem channel (arm B's first input):** the guitar plus the backing at a guitar-to-leak ratio
  drawn uniform on 0–6 dB. This is a crude stand-in for a separator's error: the htdemucs stems
  measured 0.4–2.1 dB median SNR (stage F, step 3). Real separation is not simulated (no htdemucs
  over 40k mixes); fine-tuning on arm B's bank, which has separated examples, does that.
- **Loudness:** the mix is set to arm B's evaluation-mix median ±3 dB (`levels.json`), by the power
  sum of the stored LUFS values (exact for val examples).

### C′

C′ is a waveform network: its pairs need the render's audio, about 0.4 MB per 10-s FLAC, so 40k
pairs would take about 16 GB, which the disk does not have. So:
- every example stores its **recipe** (DI section, settings, amp, base), from which the DI and the
  render are regenerated exactly by the same code;
- the audit sample's audio checks that a re-render reproduces the stored one: at the pilot's end,
  30 audit examples are re-rendered and compared (max |Δ|, SNR, and the share of identical uint8
  mel cells);
- C′ pre-training is a later plan. It re-renders the pairs it needs (about 6 h per 40k) when disk is
  freed for it, for example by retiring the 20-GB PR12 cache, on the user's approval.

## The size: a learning-curve pilot (the stopping rule)

**The model:** arm B's network at half width (`song_model`'s blocks with 16, 32, 64, 96 channels,
the same trunk and heads, about a quarter of the compute), its B0 loss, its inputs (a 2 × 96 × 446
half: the stem and the mix; the stem and mix LUFS; the amp; the base class). Adam 1e-3, batch 64, at
most 30 epochs, patience 4. Early stopping reads 5% of the train sections (whole sections, seeded),
never the val bands.

**The readout:** on the 3,000 val examples (true mixes, unseen bands):
- **primary:** E(n), the band-weighted mean over val examples and halves of the single answer's
  error on the continuous settings: mean |μ_top − θ| over the amp's continuous dimensions, unit
  scale (the knob error a pre-trained arm B would start from);
- **also:** the B0 loss, switch error, mic accuracy, per amp, per base class, per measured class,
  and E on the clean stem (guitar alone).

**Sizes:** nested prefixes of the train examples in index order (each index is an independent
draw): 5k, 10k, 20k and 40k, two seeds each (20261042 and 20261043).

**The rule (declared, evidence-based):**
- Δ(n → 2n) = E(2n) − E(n), seed-averaged, paired per val example, with a 90% band-clustered t
  interval over the val bands (at least 8, so at least 7 degrees of freedom).
- **Extend** (render the next 40k, then train at 80k) while the latest doubling's interval lies
  entirely below 0, the disk check passes and the pool has sections. **Stop** when it includes 0:
  the curve has flattened at what this set can resolve.
- The runner prints exactly `DECISION EXTEND` or `DECISION STOP` (`pretrain_set decide`). It runs
  at most one extension (to 80k) unattended; a further doubling needs a new launch and its disk.
- **Reported beside the rule, not deciding:** a saturating power-law fit E(n) = a + b·n^(−c) with
  its predicted gain at 2n, the seed spread at each size, and each size's E with its interval.

Undecided is not failed: a flat curve at 40k says this set's size is enough for this model on these
DIs, not that pre-training is useless. Whether pre-training helps on real songs is the fine-tuning
plan's question (arm B revived, at the roadmap's decision point), not this one's.

## Cost

| Stage | Renders | Hours | GPU (MPS) | Disk |
|---|---|---|---|---|
| Pool, backings and leakage (zero renders, CPU) | 0 | about 0.5 | — | 0.2 GB |
| Pilot renders: 40k train + 3k val + 400 audit (no extra renders: audit examples are train examples) | 43,000 | about 6.5–7 (3 shards, about 6.5k an hour; the class measures add a little CPU per example) | — | 3.1 GB |
| Re-render check | 30 | — | — | — |
| Curve: 4 sizes × 2 seeds | 0 | — | about 3–5 h (estimated: half width runs about 2.3× faster than full width on the CPU; MPS speed is logged and reported) | small |
| Extension, if the rule says so: +40k, then 80k × 2 seeds | 40,000 | about 6.5 | about 3 h | 2.4 GB |

The render rate is arm A's measured 6.75k an hour on 3 shards; part C's renders are 10.25 s, the
same as the bank's.

## Machine order

After the overnight runs end (rebuild-tone and multi-section both print `all done`, and no render
of theirs remains), then B1 (a test, first), then part C. One GPU job at a time: the curve trains
only when no other training process runs. Renders share the 3-slot cap.

## What this plan does not do

- No training of arm B or C′ for use: the curve's models exist to size the set.
- No held-out data, no part-B DI, no stage-F DI, no Guitar-TECHS P3.
- No separation over the set (cost), so separator artefacts are only crudely stood in for.
- Morgan only; Tone King is not covered.

## Code (written and tested before any render)

`learn/pretrain_set.py`, subcommands `pool`, `backings`, `draw`, `render --shard i/3`, `curve`,
`decide`, `recheck`, `report`. Unit-tested with fakes and synthetic signals: the pool filter and its
exclusions (the hum-audit superset, known-answer, held-out, the pre-amendment manifest refused),
the training-check parity with `clean_di.assert_training_ok`, the split (whole bands, sizes,
reserve), the draw (deterministic per index, modes and shares, clamping, mics and switches), the
quantiser round trip, the power-sum mixer against a numeric sum, the backing track rule (own
tracks, DIs, vocals, leakage drops), the ratio draw, the band-clustered interval and the decision
rule, the disk guard, and the render-cap pattern.

## Amendment 1 (2026-10-18): review changes, before any render

The independent review approved the plan with required changes 9–20 (its numbering; 1–8 are B1's).
All are made here and in the code; this amendment governs where the body differs.

9. **The gate is a positive marker.** `pool` runs only when the manifest carries the hum-screen
   amendment: part A's amendment 3 as `learn/clean_di.py` writes it (manifest `version` 2 or later
   with 3 in `amendments`), a top-level `hum_amendment` field, or a marker file
   `~/ndsp-presets/learn/clean-di/HUM_AMENDMENT.json` whose `manifest_sha256` equals the manifest's.
   The pre-amendment sha is still refused. A manifest rebuilt for another reason does not pass.
10. **The hum superset and the Guitar-TECHS exclusion** are stated as above ("The pool").
11. **Counts, on the current manifest with this amendment's split:** pool 740 before item 18;
    Timo And The Timezone out: 2; reserve 102 (11 DIs); val 97; train 539. The amended manifest's
    counts are those `pool` prints, reported in the results.
12. **Val bands:** whole bands of 5 to 20 non-reserve sections (small bands, so there are many),
    with a session backing, in seeded order until at least 8 bands and 15% of the sections, or the
    candidates run out. On the current manifest that gives 9 bands and 97 sections (15%): Adam
    Buckley, Cnoc An Tursa, Dark Ride, John Morgan Kimock, Magician's Nephew, Swatkins, The Travelling
    Band, Wall Of Death and Zeno; by the DIs' gain class 42 clean, 5 crunch, 6 high-gain and 44
    unclassed. Train keeps 539. The val mix is reported, and E by DI gain class.
13. **Seed noise enters the decision.** Three seeds at 20k, 40k and 80k (two at 5k and 10k):
    20261042, 20261043, 20261044. EXTEND needs the seed-averaged Δ interval below 0 **and** each
    seed's own Δ (seed k at n against seed k at 2n) to have its interval below 0.
14. **Undecided is not flat.** `decide` prints `DECISION EXTEND` or `DECISION STOP`, and on STOP a
    reading line: `READING flat` when its lower bound lies above half the previous doubling's point gain (the interval rules out a gain half as
    large as the last one), else `READING undecided`. Only EXTEND runs the extension unattended; an
    undecided stop is put to the user with the numbers.
15. **The scope threshold is frozen** after the pilot's renders (`scope-threshold.json`, written
    once by `curve` and reused by every later size), and applied to val as to train. E is reported
    with and without the tagged examples.
16. **Departures from arm B's recipe, declared:** no mastering (compressor, limiter, AAC) and no
    second guitar in the training mixes. Half the val examples are mastered with arm B's compressor
    and limiter (`song_aug.compress`; no AAC), seeded, so E is reported mastered and not; the second
    guitar's absence is a stated gap. Fine-tuning on arm B's bank covers both.
17. **C′: a decision for the user, and an exact recipe.** The pilot stores no audio for C′ beyond
    the audit sample. Offered to the user (not run unattended): keep every 8th train render's FLAC
    (about 5k renders, about 2 GB) for a C′ pilot. Every example's recipe records what re-rendering
    needs: the plugin's version as the renderer reports it, the sha256 of the measure treatment's
    average curve (`confirm_run.AVERAGE`), `isolate=True`, the 52-sample latency (left in), 48 kHz,
    and the 0.25-s lead-in. If `recheck` is not bit-identical, its SNR and max |Δ| are reported and a
    C′ plan decides whether re-rendered pairs are usable (C′ trains on spectral losses, so a
    sub-LSB difference would not matter; a larger one would be named).
18. **Timo And The Timezone is out** of the pool (2 sections), since The Timezone "GOTGF" is a part
    B2 candidate and its band would then become known-answer.
19. **Licences:** each example carries its DI's licence (Cambridge-MT: educational use only;
    Telefunken: home-studio and educational use only, no commercial use). A model trained on this
    set is for research; whether one may ship in the plugin is the user's decision.
20. **DI playing style is in scope.** About 17% of the pool comes from DIs whose original part was
    labelled high-gain. The scope rule is about the tone: the playing is rendered only through
    clean-to-crunch settings, so those sections stay. E is reported by the DI's gain class.

**Also, from the review's suggestions:**
- the guitar-to-backing ratio is drawn band-weighted (a band uniformly, then one of its values),
  so the Telefunken sessions do not dominate;
- val is also scored on power-sum mixes built from its stored guitar and backing mels, which
  measures the train/val mixing gap directly (zero renders);
- one curve axis without renders: about 20k examples over half the train sections (the first half
  of the section ids, so grouped by band and DI, not random; one seed), beside 20k over all of them,
  to tell DI diversity from settings count (reported, not deciding);
- the model's trunk is 256 wide (half of arm B's 512), and each epoch draws one half (A or B) per
  example, seeded; a full-width check at the final size is left for the fine-tuning plan.

**Smoke run before launch (2026-10-18, scratch output, not results):** `pool` on the pre-amendment
manifest (gate bypassed in the smoke only), `backings` for 3 sections (one Telefunken DI dropped its
room mic and the other guitar's amp as leaking), 3 renders (about 1.8–2.1 s each per process with
features and class measures, so about 5–6k an hour on 3 shards), `recheck` (re-render SNR 90 dB
against the stored 16-bit FLAC, every mel cell identical), `report` (power-sum error on the audit
example: median 0.38 dB, 90th percentile 1.8 dB) and a two-epoch CPU `curve` and `decide`. Bytes:
58 KB per train example, 174 KB per val example, 186 KB plus a 433-KB FLAC per audit example.

**PR review fixes (2026-10-18), before any render:**
- a training epoch that skips more than 5% of its steps on non-finite gradients aborts the run; it
  is retried once, then `curve` fails (`CURVE FAILED`) instead of feeding a barely trained model to
  the decision; skipped steps are logged per epoch;
- each run's weights are kept (`curve-models/`), and `evaluate` also stores per example the switch
  error, the mic agreement and E with the clean stem; the per-amp, per-base, per-class, mastered and
  DI-gain-class rows are derived from the per-example errors and the rows;
- a torn last line in a shard's rows (a kill mid-write) is cut on resume;
- the report reads the frozen scope threshold; a near-silent backing is not lifted more than 40 dB.

**On the amended manifest** (now in place: version 2, amendments 1–3), `pool` gives 718 sections:
train 520, val 96 (the same 9 bands), reserve 102.
- From the PR re-review's notes: rows are read in linear time, and a complete last row missing its
  newline gets one; the training-time loudness uses the same near-silent-backing cap as the gains;
  the clean-stem score is conditioned on the leaky stem's loudness (named in the report).
- **The runner also waits for PR #214** (the hum amendment) to be merged into main before part C
  starts, as the main session asked; the manifest gate stays, so a later re-version swaps in.

## Amendment 2 (2026-10-18): a bounded render server, primed re-checks and a masked first second, before the curve

Declared after the 40k pilot's disk guard stopped shard 1 at 8,800 of 14,333 renders (the other
shards near the same count), before the curve step. It changes no example already rendered, and no
render recipe.

**Why.** Each render server holds every decoded DI in memory (`excitationCache` in
`scripts/au_render_server.swift`). Part C renders a new section on almost every render, so each
server grew by about 1.7 MB per render at first: 3.1 GB of RSS after about 1,860 renders. The
growth saturates because the pool has about 600 distinct sections (5.1 GB per server at about
8,700 renders), but a job over more distinct DIs would not stop there. Part C ran on its old
code and no shard was stopped or signalled. After its disk guard (exit 4), the tail resumes from
`rows/shard-i.jsonl` on the bounded server (item 3).

0. **A learn-only bounded server.** `learn/au_render_server_bounded.swift` is the shipped server
   plus a least-recently-used bound of 4 decoded DIs (the same bound as the DI files on disk,
   `knob_ceiling.DI_FILES_KEPT`). `knob_ceiling.Renderer` builds it with `scripts/_swift.py` into a
   directory it owns and removes, and passes it to `AudioUnitRenderer` as `binary=`. The shipped
   server and `match/renderer_au.py` are unchanged, so the renderer build that Tone King's
   measurements record is unchanged. A test keeps the copy identical to the shipped server outside
   its two marked blocks. Every learn script that renders through `knob_ceiling.Renderer` now runs
   it.
1. **`recheck` primes every re-render.** Each of its 30 re-renders is preceded by one discarded
   render at the same DI and settings (`primed_render`), as the
   [start-transient audit](audits/start-transient-2026-10-18.md) asks. The same rule holds for any
   later re-render of part C examples. Priming clears the transient from the re-render only: the
   stored render was not primed, so its first seconds can still carry the previous example's
   state. `recheck` therefore also reports max |Δ|, SNR past 4 s of the stored window
   (`RECHECK_LATE_S`, where the audit's transient is below 0.005) and the share of identical half-B
   mel cells. Those late figures are the recipe check; the full-window figures include the stored
   side's transient.
2. **Training masks the first second of half A, for every example.** The mel frames whose window
   starts in half A's first second (100 of 446 frames, `MASK_A_FRAMES`) are set to 0 in the
   normalised input (−60 dB), stem and mix alike, in training batches, early stopping and every
   val readout (true, power-sum and clean-stem). Half B is never masked; stored features are
   unchanged. This covers the start transient after a process start (including this resume), an
   amp change or a DI change (the audit's cheap remedy). **Not masked, stated:** the row scalars
   computed from the whole render or half (the half LUFS conditioning, whole-render LUFS, the gain
   class and the scope threshold), estimated in the audit to move by 0.1–0.2 dB at worst on a
   quiet-start section. **No per-example priming render is added:** that would change the
   rendering method part-way through the pilot.
3. **If the tail resumes, rows from before and after the switch come from bit-identical
   renders.** Checked on 2026-10-18 before any row was rendered on the bounded server (scratch
   check, 290 renders under the 3-render cap):
   - **Bit identity.** Two 11-render sequences, each 8 distinct sections with their own example's
     amp and settings (both sequences change amp), then the first two again after the bounded
     cache had evicted them, then an immediate repeat. Each sequence ran through the shipped
     server, the bounded server and the shipped server again (a control), every one a fresh
     process through `knob_ceiling`'s renderer (so its DI files were deleted and rewritten too).
     All 22 bounded renders equal the shipped ones exactly (max |Δ| 0), as do all 22 controls.
   - **Memory.** Over 50 distinct sections the shipped server grew from 105 to 253 MB (3.0 MB
     per render over the last 30) and the bounded one from 105 to 172 MB (1.15 MB per render).
     The rest is growth per render, not per DI, in both servers: rendering one section 40 times
     grows the bounded server by 1.09 MB per render, and cycling 6 sections grows the shipped
     server (all cache hits) by 1.09 MB per render. This amendment does not change it. On part C
     it is smaller than that late in a run (each server held 5.1 GB at about 8,700 renders).

   This is equivalence of the two servers, not of a resumed run with an uninterrupted one: a
   resume restarts each shard's process, so its first render carries the process-start
   transient, which only item 2's mask covers (as for any resume). `recipe.json` records no
   renderer build, so a resumed shard passes its check unchanged.
4. **Item 2 reaches the curve only through the code the curve runs.** The runner
   (`learn/selfrender_run.zsh`) runs each step from its own checkout. If part C finishes on that
   checkout's old code, the curve step must run from a checkout that has this amendment; a curve
   run without the mask is not part C's declared readout.
