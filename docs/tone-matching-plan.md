# Reference-guided tone matching — implementation plan

Status: **M0, M1 and M2 are done; M3 is next.** The two spikes ran on 2026-08-05
and their numbers are in §11 and in `docs/measuring-against-the-plugin.md`. The
analysis core landed the same day: `analysis/` plus `scripts/fingerprint.py` and
`scripts/compare_audio.py`. M2 added `analysis/refchain.py` and the `match/`
package — the synthetic chain and the `Renderer` protocol — with §12a recording
what its sensitivity test caught.

§12 records where both milestones departed from this document — including five
departures found by auditing them against their own exit criteria before starting
M2, every one of which had passed a green suite. One M0 item is deliberately
still open: the `apply_spec.py` → `pedalboard` state round trip is implemented
and tested without a plugin, but has not been *run* against one, and M5 depends
on it.

This is a handoff specification. It is written to be given to a fresh Claude
Code session as the sole context for building the feature, so it states the
repository facts, the decisions already made and *why*, the non-goals, and the
acceptance test for each work package. An implementing session should not
re-litigate the decisions in §3 without a concrete reason; it should read §1
and §5 first, then start at whichever milestone §7 says is unblocked.

---

## 1. Context the implementer needs

### 1.1 What this repository is

A Claude Code plugin that generates and edits Neural DSP preset files. Two
skills (`skills/generate`, `skills/edit`), a lossless binary format layer
(`format/`), per-plugin fact tables (`packs/<id>/manifest.json`), composable
tone recipes (`packs/<id>/recipes.json`), and a set of measurement scripts that
verify declared facts against an installed Audio Unit.

### 1.2 The accuracy problem, stated precisely

The generate path is: web research → prose → recipe stack → preset bytes.
**No audio is measured at any point.** There is no representation of the target
sound, no representation of the produced sound, and therefore no way to tell
whether the result is closer to or further from the reference. The only
corrective in the system today is a human writing "too dark" into
`learned-tones.md`.

Everything below exists to close that loop.

### 1.3 Repository facts that constrain the design

| Fact | Consequence |
|---|---|
| `pyproject.toml` has `dependencies = []`; tests pass on a bare clone | New dependencies go in **optional extras only**. `show.py` and `apply_spec.py` must keep working with stdlib alone. |
| `spectrum_diff.py` uses hand-written Goertzel to avoid numpy | That constraint applies to *reproducing a published measurement*. New analysis code may use numpy/scipy behind an extra. Do not rewrite `spectrum_diff.py`. |
| Morgan manifest: 132 parameters — 53 `metered`, 32 `switch`, 31 `rotation`, 8 `enum`, 4 `fraction`, 2 `string`, 2 `path`; 1 non-writable | Continuous search space is ≤ 88 before conditioning; per-amp conditioning cuts it to roughly 35–45. |
| Tone King manifest: 259 parameters, **159 marked `internal` / non-writable** | Its writable space is ~100. Its acoustic path is open through `pedalboard` only, at ~11× Morgan's cost per render (§11). |
| Each amp has its own module prefix (`ac20*`, `pr12*`, `sw50r*`) and its own 9-band EQ | Search space must be *conditional* on `selectedAmp`. Writing the inactive amp's controls is a silent no-op. |
| EQ bands are fixed ISO centres (65/125/250/500/1k/2k/4k/8k/16k), ±12 dB, plus HPF (20–500 Hz) and LPF (1k–20k), with `centre_hz` already declared in the manifest | Spectral matching is a **bounded 9-variable least-squares fit**, not a search. See D2. |
| `au_render.swift` renders Morgan fine and gets **exact zeros** from Tone King. M0 resolved the cause: the bare CLI instantiation, not authorization — Tone King renders in a JUCE host | Tone King work goes through the `pedalboard` backend. Nothing about it has been measured acoustically yet; do not silently produce Tone King "measurements". |
| `apply_spec.py` validates kinds, ranges, selectors, read-only fields, and never overwrites its input | Optimizer output **must** be emitted as a human-valued spec and passed through `apply_spec.py --dry-run`. Never write preset bytes directly from the optimizer. |
| Plugin-dependent checks are deliberately local, never CI (`audit_manifest.py`) | Same split applies here: plugin-free tests in CI, plugin-dependent checks local. |
| `NOTICE.md`: no Neural DSP content, no factory presets, no IRs, no audio redistributed | Reference audio, stems, and renders are **never** committed. Store hashes and derived features only. |

### 1.4 Documents this plan builds on

Two prior research passes exist. This plan adopts most of the second
("deep research report") and departs from it in six places, each argued in §2.
The implementer does not need either source document — everything actionable is
restated here.

---

## 2. Where this plan departs from the deep-research report

These are the parts worth understanding before building. Each is a place where
following the report literally would produce a worse or slower outcome for
*this* repository.

### D1. Paired DI is the **validation** regime, not the production regime

The report's headline architecture optimizes a dry DI rendered through candidate
presets against a target produced from that same DI, and rates the mix-only case
"low–medium ceiling."

But the product's actual query is *"give me the clean tone from Hotel
California."* There is never a paired DI. The user has a commercial stereo
master and a guitar. Building the paired pipeline first would deliver an
impressive system for a case the tool does not have.

**Inversion:** the unpaired, statistical path is the product. The paired path is
the *test harness* — it is how you obtain ground truth to prove the matcher
works, and it is exactly what the synthetic chain in M2 provides for free. Build
unpaired first, validate with paired.

### D2. Direct inversion before search

The report goes from recipe prior straight to 200–400 CMA-ES renders. But a
large fraction of what makes a preset wrong is **analytically invertible** given
this plugin's specific controls:

| Wrong thing | Inversion | Renders needed |
|---|---|---|
| Spectral balance | Bounded least-squares fit of the LTAS difference onto 9 fixed-centre bands + HPF/LPF | 11 per amp, **once**, committed as a measured basis |
| Delay time and feedback | Autocorrelation of the amplitude envelope; resolve to a note division against detected BPM | 0 |
| Reverb decay, pre-delay | Blind decay-slope estimation on note releases | 0 |
| Tremolo rate/depth | Peak of the AM modulation spectrum | 0 |
| Output level | LUFS difference | 0 |
| Drive amount | Lookup in a THD-vs-(volume, input level) table | ~40 per amp, **once**, committed |

Do this first. It costs a one-time calibration and removes most of the
dimensions from the search. CMA-ES then handles only the genuinely coupled,
nonlinear residual: gain staging interactions, cab/mic choice, compression
behaviour, bright/boost switches.

This also fits the repository's culture better than a black-box search does: the
EQ basis and THD table are *measured facts*, committed alongside the other
measured facts, auditable the same way.

### D3. Render throughput is the binding constraint, and the report's arithmetic hides it

The report reasons "300 evaluations × 10 s = 3,000 s of audio; at 10× offline
speed that's ~5 minutes." That assumes DSP time dominates. In this repository it
does not. `au_render.swift` pays, **per render**: a process spawn, a Swift
runtime start, `AUAudioUnit.instantiate`, a hardcoded `usleep(200000)` settle,
`allocateRenderResources`, and a file open — to render 2 seconds of audio.
Fixed overhead is plausibly 10–30× the actual DSP cost.

**Therefore the first engineering task is a persistent render process, not a
better optimizer.** Measure it before designing around it (M0-S1).

*Measured: the conclusion holds, the multiplier was overstated. Fixed overhead
is 5.6× the DSP cost, not 10–30×, and instantiate alone is 62% of a render.
See §11.*

### D4. No PyTorch in milestones 1–4

The report lists PyTorch/torchaudio at "Highest" priority, and its example
composite loss uses torch solely for STFT, mel filterbank, and average-pooling —
all of which `scipy.signal` and a mel matrix do fine, on CPU, in milliseconds,
for 10-second excerpts.

Adding torch would take this from a zero-dependency project to a ~2 GB install
for the first useful feature. That trades away a property the repository
deliberately defends. Keep the analysis core at **numpy + scipy + soundfile**.
Torch enters only if and when learned embeddings or a differentiable proxy are
actually built (M7), and stays in its own extra.

### D5. `pedalboard` is mis-classified in the report

The report's tool table lists it as "Optional — quick effect-chain prototyping;
not a replacement for the target plugin." It is not a *replacement* for the
plugin — it is a **host** for it: it loads Audio Units on macOS, enumerates and
sets parameters, processes numpy arrays, and supports getting/setting plugin
state as binary.

That makes it the strongest candidate for the `Renderer` backend, collapsing
render + analysis into one process and eliminating the per-render process spawn
from D3. And because it is a JUCE-based host rather than a bare CLI AU
instantiation, it is also the **cheapest available test of the Tone King silence
hypothesis** — if authorization is the cause, a more DAW-like host may behave
differently. Spike it early (M0-S2).

### D6. Trim the evaluation apparatus to fit the project

The report specifies MUSHRA and BS.1116 protocols, 24–32 listeners, a
216-condition benchmark, and linear mixed-effects models with Holm correction.
That is a research programme, not a plugin feature, and it would consume the
entire budget before a single preset improved.

**Replace with two things:**

1. A **synthetic recovery benchmark** (M2): known parameters → render → try to
   recover. Exact ground truth, zero humans, runs in CI, free.
2. A **lightweight A/B logger** that writes user verdicts into the existing
   `learned-tones.md` mechanism. This is already the repository's feedback
   channel; the only change is that verdicts now attach to a measured
   fingerprint delta instead of to prose.

Scale up to formal listening tests only if and when the objective numbers stop
correlating with what people say — and keep the report's statistical design on
the shelf for that day.

### What this plan adopts from the report without change

- **ST-ITO** as the closest published precedent: inference-time, gradient-free
  optimization of parameters for non-differentiable, unseen effect chains.
- The finding that a **Gaussian parameter prior improves** inference-time
  optimization — which validates using the recipe stack as an explicit prior
  term, not just as an initialization.
- **Parameter accuracy ≠ audio accuracy.** Report both, separately, always.
- **Do not use PESQ or STOI.** They are speech metrics; P.862 was deleted by the
  ITU in January 2024. They may appear as diagnostics, never as objectives.
- **Content-addressed render cache** keyed on plugin build, renderer build, DI
  hash, sample rate, parameters, and quality mode.
- **Pareto shortlist over a single winner** — "closest timbre", "best dynamics",
  "best ambience" are genuinely different presets and the user should choose.
- A **confidence score derived from the reference condition** (paired DI /
  isolated stem / separated stem / mix only), surfaced in the report.
- The **legal posture**: reference audio stays local, only hashes and derived
  descriptors persist, outputs are described as "reference-guided", never as
  exact or endorsed.

---

## 3. Locked design decisions

Do not change these without a specific reason; downstream work assumes them.

1. **Canonical analysis format: 48 kHz, float32, stereo preserved.** Matches
   `au_render.swift`. Mono folding happens per-feature, not at ingest.
2. **Two new packages, mirroring the existing flat layout:** `analysis/`
   (plugin-free, CI-testable) and `match/` (plugin-dependent, mock-testable).
   Not `optimisation/` + `models/` + seven new scripts.
3. **The fingerprint is the interface.** Every producer and consumer speaks
   `Fingerprint v1` (§6.1). Features are added by version bump, never by
   ad-hoc keys.
4. **Direct inversion runs before search, always.** Search operates on the
   residual.
5. **The optimizer never writes preset bytes.** It emits a human-valued spec;
   `apply_spec.py` writes. All existing validation stays on the path.
6. **Dependencies:** core stays stdlib. `[analysis]` = numpy, scipy, soundfile,
   pyloudnorm. `[match]` = adds cma. `[separate]` = adds demucs. `[host]` =
   adds pedalboard. Every entry point degrades with a clear message when its
   extra is absent.
7. **The experiment store is stdlib `sqlite3`.** No pandas/parquet dependency
   for the store itself.
8. **Plugin-dependent code lives behind the `Renderer` interface** with at least
   three implementations: `SyntheticRenderer` (M2, no plugin), `SwiftRenderer`
   (batched `au_render`), `PedalboardRenderer`. Backend choice is configuration.
9. **Sample rate, block size, plugin version, and licence state are recorded on
   every render** and are part of the cache key. Results from different plugin
   versions are never merged.
10. **Reference audio and renders are `.gitignore`d.** Run directories live
    under the data root (`$NDSP_PRESET_DATA`), not the plugin directory —
    same rule as `observed.json` and `learned-tones.md`.

---

## 4. Non-goals

Explicitly out of scope. If an implementing session finds itself doing one of
these, it has drifted.

- Reverse-engineering or emulating Neural DSP's DSP.
- Differentiating through the plugin.
- Any change to `format/` — the parser, writer, and round-trip guarantees are
  finished work and are not touched by this feature.
- Reinforcement learning, meta-learning, preference models, neural surrogates.
  (Listed as research in M7; not to be started before M5 lands.)
- Formal listening-test infrastructure (see D6).
- Real-time or in-performance adaptation.
- Making Tone King work acoustically *by assumption*. It is a spike with a
  binary outcome, not a milestone.
- Redistributing any audio, stem, IR, or factory preset.

---

## 5. Architecture

```
reference audio ──► ingest ──► [separate] ──► loudness-normalise ──► fingerprint(target)
                                                                          │
probe DI ──► Renderer(params) ──► render ──────────────► fingerprint(candidate)
   ▲                                                                      │
   │                                                                      ▼
   │                                                          compare → delta + objectives
   │                                                                      │
   │                          ┌───────────────────────────────────────────┤
   │                          ▼                                           ▼
   │                    direct inversion                            residual search
   │                 (EQ / delay / reverb /                        (CMA-ES over the
   │                  tremolo / level)                             conditional space)
   │                          └─────────────────┬─────────────────────────┘
   └──────────────────────────────────────────  ▼
                                          Pareto shortlist
                                                │
                                                ▼
                                   human-valued spec ──► apply_spec.py --dry-run ──► preset
```

### New files

```
analysis/                     # plugin-free. numpy/scipy/soundfile. CI-tested.
  __init__.py
  io.py                       # load/resample/normalise; LUFS; excerpt selection
  align.py                    # latency, polarity, fractional delay, drift
  features.py                 # the individual feature extractors
  fingerprint.py              # Fingerprint v1 assembly + JSON (de)serialisation
  compare.py                  # delta + objective vector, paired and unpaired
  refchain.py                 # synthetic effect chain (M2) — the ground truth rig
  separate.py                 # demucs wrapper, optional, behind [separate]

match/                        # plugin-dependent. mock-tested in CI.
  __init__.py
  renderer.py                 # Renderer protocol + RenderMetadata
  renderer_synth.py           # wraps analysis.refchain
  renderer_swift.py           # batched, persistent au_render process
  renderer_pedalboard.py      # AU host in-process
  space.py                    # conditional, typed search space from the manifest
  invert.py                   # direct inversion (EQ fit, delay, reverb, trem, level)
  search.py                   # CMA-ES + sensitivity screen + Pareto archive
  store.py                    # sqlite3 experiment store + content-addressed cache
  report.py                   # self-contained HTML report

scripts/
  fingerprint.py              # CLI: audio → fingerprint JSON
  compare_audio.py            # CLI: two audio files or fingerprints → delta table
  match_preset.py             # CLI: the whole loop
  measure_eq_basis.py         # CLI: one-time per-pack EQ basis measurement
  measure_drive_curve.py      # CLI: one-time per-pack THD surface measurement

packs/<id>/
  eq_basis.json               # committed, measured: per-band response curves
  drive_curve.json            # committed, measured: THD vs (control, input level)

tests/
  test_analysis_io.py  test_align.py  test_features.py  test_fingerprint.py
  test_compare.py  test_refchain.py  test_space.py  test_invert.py
  test_search.py  test_store.py  test_match_cli.py
  fixtures/audio/             # synthesised at test time, not committed
```

---

## 6. Data contracts

### 6.1 `Fingerprint v1`

Playing-invariant where possible, so the same schema describes a separated stem
of a 1976 master and a 2-second render of white noise. Every field is optional
and carries a confidence; consumers must handle absence.

```jsonc
{
  "fingerprint_version": 1,
  "source": {
    "sha256": "…",              // of the audio bytes; never the path
    "sample_rate": 48000,
    "channels": 2,
    "duration_s": 12.4,
    "lufs_i": -14.2,
    "true_peak_dbtp": -0.8,
    "regime": "separated_stem"  // paired_di | isolated_stem | separated_stem | mix | probe
  },
  "spectrum": {
    "band_centres_hz": [25, 31.5, …, 20000],   // 1/3 octave
    "band_db": [...],                          // LTAS, loudness-normalised
    "tilt_db_per_decade": -4.2,
    "centroid_hz":  {"p10": …, "p50": …, "p90": …},
    "rolloff85_hz": {"p10": …, "p50": …, "p90": …},
    "flatness":     {"p10": …, "p50": …, "p90": …},
    "lf_corner_hz": 92,
    "hf_corner_hz": 6300
  },
  "dynamics": {
    "crest_db": 11.3,
    "rms_percentiles_db": {"p10": …, "p50": …, "p90": …},
    "lra_lu": 6.1,
    "attack_ms": 14.0,
    "decay_db_per_s": -9.4
  },
  "harmonic": {
    "hnr_db": 21.0,
    "odd_even_ratio": 1.8,
    "hf_residual_index": 0.12,   // energy above the harmonic series — fizz proxy
    "confidence": 0.6            // low when no clean monophonic segment exists
  },
  "time_fx": {
    "delay_ms": 420.0, "delay_confidence": 0.71,
    "delay_feedback_est": 0.35,
    "delay_note_division": "1/4", "bpm_est": 143.0,
    "rt60_s": 1.8, "rt60_confidence": 0.45,
    "predelay_ms": 25.0
  },
  "modulation": { "am_rate_hz": 5.2, "am_depth": 0.15, "fm_rate_hz": null },
  "spatial": { "width": 0.42, "correlation": 0.66, "ms_ratio_by_band": [...] },
  "cepstral": { "mfcc_mean": [...], "mfcc_std": [...], "mfcc_cov_lowrank": [...] }
}
```

### 6.2 Objective vector

`compare()` returns named dimensions, never a pre-collapsed scalar. Weighting
into a scalar happens in the optimizer, from a named **loss profile**
(`paired-v1`, `unpaired-v1`) stored as JSON so it is tunable without code
changes.

```
timbre | dynamics | ambience | level | harmonic | spatial | prior_deviation | complexity
```

### 6.3 Cache key

```
sha256(renderer_id ‖ plugin_version ‖ renderer_build ‖ di_sha256 ‖
       sample_rate ‖ block_size ‖ quality_mode ‖ canonical_json(params))
```

### 6.4 Store schema (sqlite3)

`runs(run_id, created_at, pack, template, reference_sha, regime, loss_profile,
budget, renderer_id, plugin_version, notes)`
`trials(trial_id, run_id, params_json, cache_key, render_sha, peak, silent,
wall_ms, objectives_json, fingerprint_json, error)`
`verdicts(trial_id, listener, choice, comment, created_at)`

---

## 7. Milestones

Each milestone has an **exit criterion**. Do not start the next one until it
is met. Milestones M1–M4 require **no plugin, no macOS, and no licence** — this
is deliberate, so an implementing session can build and validate the entire
stack anywhere.

---

### M0 — Spikes (2 days, must run on macOS with the plugin)

Two questions whose answers change the design. Timebox hard; write findings into
`docs/measuring-against-the-plugin.md` in the style of the existing sections.

**S1 — Render throughput.** Instrument `au_render.swift`: measure process spawn,
instantiate, settle, allocate, and actual DSP time separately, for a 2-second
render. Then prototype a persistent variant that instantiates once and reads
`{params, out_path}` commands on stdin. Report renders/second for both.

*Exit:* a number for each phase, and a decision on whether the 200 ms settle can
be shortened or replaced with a state-applied poll.

**S2 — pedalboard as host, and the Tone King question.** Install `pedalboard`,
load `aumf/NMAS/NDSP`, enumerate parameters, set state from a generated preset's
`jucePluginState` blob, render, confirm non-silence. Then repeat for
`aumf/TKI2/NDSP`.

*Exit:* renders/second for pedalboard, and a definitive yes/no on whether Tone
King produces audio in a JUCE-based host. If yes, that unblocks the second pack
and is a significant finding for the existing docs. If no, the silence entry in
the docs gains a second, stronger piece of evidence.

---

### M1 — Plugin-free analysis core (4–6 days)

Build `analysis/`: `io.py`, `align.py`, `features.py`, `fingerprint.py`,
`compare.py`, plus `scripts/fingerprint.py` and `scripts/compare_audio.py`.

Implementation notes:

- **LTAS**: Welch average, 1/3-octave bands, loudness-normalised via
  `pyloudnorm`, computed on gated active frames only (drop silence).
- **Delay detection**: normalised autocorrelation of the amplitude envelope
  (Hilbert or rectified-and-smoothed), search 40–2000 ms, take the highest peak
  above a prominence threshold; feedback from the decay of successive peaks;
  note division by comparing against a BPM estimate.
- **RT60**: fit a line to the log envelope over release segments (frames after
  an offset with no onset), take the median slope across segments, report
  confidence as inter-segment agreement. Music is not an impulse — the
  confidence field is not decoration.
- **Harmonic features**: require a detected monophonic sustained segment; return
  `confidence: 0` and null values when none exists rather than producing a
  number from a chord.
- **Alignment** (`align.py`): integer cross-correlation → fractional refinement
  → polarity test. Only used in the paired regime.

Tests (all with synthesised fixtures, generated in the test, not committed):

| Test | Assertion |
|---|---|
| `test_features.py::test_ltas_matches_known_filter` | White noise through a known biquad → LTAS recovers the filter shape within 1 dB |
| `…::test_delay_detection_exact` | A signal with a synthetic 420 ms / 0.35-feedback echo → recovers 420 ± 5 ms and 0.35 ± 0.05 |
| `…::test_rt60_from_synthetic_decay` | Exponentially decaying noise bursts → recovers the known RT60 within 15% |
| `…::test_tremolo_rate` | 5 Hz AM applied → recovers 5 ± 0.2 Hz |
| `…::test_features_are_level_invariant` | The same signal at −20 dB and −6 dB → identical spectrum/harmonic fields after normalisation |
| `test_align.py::test_recovers_known_offset_and_polarity` | Known integer + fractional offset and inverted polarity → recovered |
| `test_fingerprint.py::test_roundtrip` | Fingerprint → JSON → Fingerprint is lossless and version-checked |

**Exit:** `python scripts/fingerprint.py <wav>` prints a valid Fingerprint v1 for
any input, and the full test table passes on a machine with no plugin.

---

### M2 — Synthetic reference chain (3–4 days) — *the development vehicle*

`analysis/refchain.py`: a pure-numpy effect chain whose topology **mirrors
Morgan's**, so recovery results transfer:

```
input gain → gate → compressor → drive (waveshaper) → 9-band graphic EQ
           → HPF/LPF → power-amp saturation → cab (FIR) → delay → reverb
           → output gain
```

Parameters use the same names, kinds, units, and ranges as the Morgan manifest,
so `match/space.py` can build a search space over it with no special-casing.
Wrap it as `match/renderer_synth.py` implementing the `Renderer` protocol.

This is what makes the rest of the plan executable without a plugin: you get
**exact ground-truth parameters**, unlimited free renders, and a deterministic
recovery benchmark.

**Exit:** `SyntheticRenderer` renders a DI in < 50 ms; a round-trip test shows
that changing each parameter moves the fingerprint field it should move (a
sensitivity smoke test that doubles as documentation of what each feature
detects).

---

### M3 — Search space + direct inversion (5–7 days)

**`match/space.py`** — build a typed, bounded, *conditional* space from a pack
manifest:

- include only writable parameters; exclude `internal`, `writable: false`,
  `string`, `path`;
- condition on the selected amp — only that amp's module is active;
- condition effect sub-parameters on their `*Active` switch;
- exclude anything flagged `needs_review` unless explicitly opted in;
- quantise controls whose audible resolution is coarser than storage;
- expose `encode()` / `decode()` to and from a normalised vector, and
  `to_spec()` producing the human-valued JSON `apply_spec.py` consumes.

**`match/invert.py`** — the D2 inversions:

```python
def fit_graphic_eq(target_band_db, candidate_band_db, basis, bounds_db=(-12, 12))
    -> dict[str, float]        # bounded NNLS/lsq_linear over the 9 band gains
def fit_filters(target_ltas, candidate_ltas) -> dict   # HPF / LPF corners
def delay_settings(fp_target, bpm) -> dict
def reverb_settings(fp_target) -> dict
def tremolo_settings(fp_target) -> dict
def output_level(fp_target, fp_candidate) -> float
```

`basis` comes from `packs/<id>/eq_basis.json`, produced by
`scripts/measure_eq_basis.py`: render the probe signal with each band at 0 dB
and at +12 dB, take the difference, store the measured per-band response curve.
Eleven renders per amp, run once, committed as a measured fact with a
`range_source`-style provenance note. Until that file exists for a pack, fall
back to idealised bell curves at the declared `centre_hz` **and say so in the
report** — this repository does not silently substitute a guess for a
measurement.

Tests use the synthetic chain: set a known EQ curve, render, invert, assert the
recovered gains are within 1 dB. Same for delay, reverb, tremolo, level.

**Exit:** on the synthetic chain, direct inversion alone recovers a target whose
difference from the source is purely EQ + time-effects to within a
loss-profile threshold, with **zero search iterations**.

---

### M4 — Optimizer, store, report (5–8 days)

**`match/search.py`**:

1. **Sensitivity screen** — for each active parameter, render at low/centre/high
   and compute normalised objective movement; freeze the bottom quantile. Budget
   ~2 renders per parameter, once per run.
2. **Topology enumeration** — amp × cab × mic × effect on/off as an outer loop
   over discrete choices (Sobol or exhaustive when small). Not fed to CMA-ES.
3. **CMA-ES** over the remaining continuous residual, seeded from the
   recipe-stack values (`sigma ≈ 0.15–0.2` in normalised space), with an
   explicit prior term `λ‖θ − θ_recipe‖` — the Gaussian-prior result from §2.
4. **Pareto archive** across the objective dimensions; return 3–5 non-dominated,
   perceptually distinct candidates.
5. **Robustness re-rank** — re-render the shortlist on held-out excerpts and at
   ±6 dB input level. A preset that matches at one input level and falls apart
   at another is not a match; the repository's own THD measurements already show
   how strongly breakup depends on input level.

**`match/store.py`** — sqlite3, schema in §6.4, content-addressed cache.
**`match/report.py`** — one self-contained HTML file: LTAS overlay, signed
band-difference bars, envelope overlay, per-objective convergence, the shortlist
with its parameter diffs, the confidence score, and every caveat that applied.

**`scripts/match_preset.py`**:

```bash
python scripts/match_preset.py \
  --template samples/Example_Clean_PR12.xml \
  --reference ~/audio/song-excerpt.wav --reference-mode mix \
  --probe-di data/di/probe.wav \
  --loss-profile unpaired-v1 --budget 300 --shortlist 3 \
  --renderer synthetic|swift|pedalboard \
  --out-dir "$NDSP_PRESET_DATA/runs/hotel-california-001"
```

**Exit — the benchmark that decides whether any of this worked.** On the
synthetic chain: sample 50 random legal parameter vectors, render, and attempt
recovery. Report, separately (never merged — see §2):

- normalised parameter MAE and selector accuracy;
- objective-vector distance versus the ground-truth render;
- render count and wall time;
- failure rate.

Ship only if the full pipeline beats **both** baselines: the current
recipe-only generator, and inversion-only without search.

---

### M5 — Real plugin backend and calibration (4–6 days, macOS + licence)

Land the backend chosen in M0. Then, per pack, run the one-time calibrations:
`measure_eq_basis.py` → `eq_basis.json`, `measure_drive_curve.py` →
`drive_curve.json` (THD across the volume control at 3–4 input levels, extending
the existing PR12 measurement into a full surface). Add a
`tests/test_calibration_schema.py` that validates the committed JSON without
needing the plugin.

Re-run the M4 benchmark against the real plugin with paired ground truth: render
a known preset through Morgan, discard the parameters, attempt recovery. This is
the number that matters.

**Exit:** benchmark numbers for the real plugin are in the docs, and the honest
gap between synthetic and real recovery is written down.

---

### M6 — Skill integration (3–4 days)

Add `skills/match/SKILL.md` — "make this preset sound more like this recording"
— and extend `skills/generate/SKILL.md` §2 so that *when the user supplies audio*
the skill fingerprints it and reports the numbers, instead of relying solely on
web research. Web research still chooses the topology; measurement moves the
values. That division is the point, and it should be stated in the skill text.

The skill must surface: the reference regime and its confidence, what was
inverted versus searched, the shortlist with plain-language differences, and any
caveat the run produced (no measured EQ basis, low harmonic confidence,
separation used, Tone King unverified). It must pass the winner through
`apply_spec.py --dry-run` and show the change list before writing, exactly as
the current skills do.

Append the outcome — and any user pushback — to `learned-tones.md`, now attached
to a fingerprint delta rather than to prose (D6).

**Exit:** `claude plugin validate ./.claude-plugin/plugin.json --strict` passes;
the end-to-end flow works against the synthetic renderer with no plugin
installed.

---

### M7 — Research, only after M5 lands

In priority order, each independently justifiable:

1. **Response atlas** — Latin-hypercube sample of the parameter space rendered
   once (a few thousand renders, hours, offline), fingerprints stored. Gives
   near-instant matching by nearest-neighbour + local refine, *and* an
   achievability check: "the darkest this amp and cab reach is X; the target is
   darker — no preset fixes that." Nothing in the current design can say that.
   It also completes the repository's own taxonomy: manifest = **legal**,
   `observed.json` = **typical**, atlas = **achievable**.
2. **Warm-start regressor** trained on the atlas — predicts a starting parameter
   vector from a target fingerprint, cutting the search budget.
3. **Learned perceptual embedding** as an additional objective dimension —
   only after the hand-designed features have been calibrated against real user
   verdicts, and only if they demonstrably plateau.
4. **Differentiable proxy chain** (Wiener–Hammerstein + differentiable EQ /
   compressor / FIR cab) for initialization by gradient descent.

---

## 8. Dependency and CI policy

```toml
[project.optional-dependencies]
dev        = ["pytest>=7.0", "pyyaml>=6.0"]
analysis   = ["numpy>=1.24", "scipy>=1.10", "soundfile>=0.12", "pyloudnorm>=0.1"]
match      = ["neuraldsp-preset-generator[analysis]", "cma>=3.3"]
host       = ["pedalboard>=0.9"]
separate   = ["demucs>=4.0"]
```

- `show.py`, `apply_spec.py`, `probe.py`, `bootstrap_pack.py` keep working with
  **zero** dependencies. A test must assert this (import them in a subprocess
  with numpy hidden).
- CI (`.github/workflows/ci.yml`) grows a second job installing `[analysis,match]`
  and running the analysis + synthetic-chain + optimizer tests. The bare-clone
  job stays exactly as it is.
- Plugin-dependent scripts are never run in CI, matching `audit_manifest.py`.
- Every entry point that needs an extra must fail with the install command, not
  an ImportError traceback.

---

## 9. Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Tone King silence persists in every host | Medium | M0-S2 resolves it early. If it persists, the feature is Morgan-only and says so; no fabricated measurements. |
| Separation artifacts drive the optimizer to a wrong preset | **High** | Prefer exposed passages; report the regime and lower the confidence; consider running the candidate through the same separator so both sides carry the same damage; never present a mix-only match as high confidence. |
| Overfit to one DI / one input level | High | Robustness re-rank at ±6 dB and on held-out excerpts is part of M4's exit, not an afterthought. |
| Plugin renders non-deterministically | Low | Cache validates by render hash; a repeat-render check runs before every session. |
| Search budget makes the feature unusably slow | Medium | D3 is addressed first; direct inversion removes most dimensions; budget tiers (preview 40–80 / standard 200–400) are user-facing. |
| The target is unmatchable — layered guitars, mix-bus processing, mastering | **Certain, for commercial masters** | Say so. The atlas (M7-1) turns this from a vague disclaimer into a specific statement about what the plugin can reach. A preset is not a mix. |
| Feature creep into the ML research track before the basics land | Medium | §4 non-goals; M7 is gated on M5. |

---

## 10. Decisions the user should make (none block starting)

1. **Renderer backend** — `pedalboard` (simpler, in-process, may unblock Tone
   King) versus a batched Swift server (no new dependency, keeps the existing
   measurement lineage). M0 produces the numbers; the default is pedalboard if
   it renders Morgan correctly.
2. **Third skill versus extending `generate`** — plan assumes a new `match`
   skill plus a hook in `generate`. A single extended skill is viable if the
   preference is fewer entry points.
3. **Does the implementing session have macOS + a licensed plugin?** If not,
   it can still complete M1–M4 and M6 in full; M0 and M5 wait.
4. **Probe DI source** — a user-recorded DI, a public dataset excerpt (EGDB /
   IDMT-SMT-Guitar, licence permitting), or synthetic excitation only. Plan
   ships synthetic as the always-available baseline and supports a user DI as
   the accuracy path; committing a real DI to the repository needs a licence
   decision.

---

## 11. What M0 measured, and what it changes

Ran 2026-08-05 on macOS 26 with both plugins licensed and installed. Full
evidence, with the commands that reproduce it, is in
`docs/measuring-against-the-plugin.md`.

### S1 — throughput

| | renders/s, 2 s of audio |
|---|---|
| `au_render.swift`, one process per render | 0.50 |
| `au_render_server.swift`, one instance | 3.4 steady state |
| four servers in parallel, 6 performance cores | 8.8 |
| `pedalboard`, in-process | 4.3 |

D3 is confirmed in direction: 306 ms of a 2030 ms render is DSP, the rest is
overhead, and `AUAudioUnit.instantiate` alone is 1250 ms of it. A 300-render
budget goes from 10 minutes to 34 seconds. The 200 ms settle turns out to be
unnecessary — `fullState` is applied synchronously — which is another 205 ms per
render.

### S2 — the backend, and Tone King

**Tone King renders audio in `pedalboard`.** Peak 0.164, a real amp-and-cab
response, and its controls move the spectrum. In the same session
`au_silence_check` still returned exactly 0.0 for it and 0.5546125 for Morgan,
so the silence belongs to the bare CLI instantiation and **authorization is
ruled out**. Risk-register row one is closed. The second pack is unblocked for
acoustic work, at ~11× Morgan's cost per render.

**Recommended backend: `pedalboard`**, which decides §10.1. It is the fastest,
it is the only one that renders Tone King, and it exposes named, typed, ranged
parameters instead of XML attributes to be edited by regular expression — a
better substrate for `match/space.py`. Keep `au_render.swift` as the reference
renderer for anything published, and `au_render_server.swift` as the
no-new-dependency fallback that independently corroborated the numbers.

### Three findings that change the design

1. **Renders are not reproducible within one instance.** A fresh process is
   bit-exact, but a second render from the same instance differs from the first
   by about −17 dB relative to the signal — in both hosts, and through `reset`,
   reallocation and warm-up alike. In third-octave bands that is ≤0.23 dB.
   - §6.3's content-addressed cache is a **speed optimisation, not an
     equivalence**: a cached render is one draw from a distribution.
   - M4's sensitivity screen must **freeze on a threshold above ~0.5 dB**, or it
     will screen out real parameters and keep noise.
   - Calibration that gets committed as a measured fact — `eq_basis.json`,
     `drive_curve.json` — must be rendered **one process per render**.
2. **`align.py` is not just for the paired regime.** The two backends agree to
   0.12 dB per band but sit 57 samples apart, so any waveform-domain comparison
   needs alignment even when both sides are renders.
3. **Morgan's live state and its preset files are different encodings.** The
   plugin's `jucePluginState` is XML; its preset files are the `morgan\0` record
   format that `format/` parses, and nothing converts between them. So the
   renderer takes parameter edits or a whole blob, `apply_spec.py` writes the
   preset, and **both must be driven from the same spec** or they will drift.
   Decision 5 in §3 stands, but it does not come for free.

## 12. What M1 built, and where it departed from this plan

`analysis/` is in the repository: `io.py`, `align.py`, `features.py`,
`fingerprint.py`, `compare.py`, `loss_profiles.json`, plus the two CLIs and 99
tests that synthesise every signal they measure. The exit criterion holds —
`python scripts/fingerprint.py <wav>` prints a valid Fingerprint v1 for any
input, including one-sample files, digital silence and full-scale DC, each of
which crashed something before it passed.

Recovery against signals built with the answer known:

| Measurement | Result |
|---|---|
| LTAS against a known biquad | within **0.73 dB** across 50 Hz–16 kHz |
| Delay time and feedback | **420.0 ms** and **0.319** for a 420 ms / 0.35 echo |
| RT60 | within 15% at 0.6, 1.2 and 2.4 s |
| Tremolo rate and depth | **5.0 Hz**, depth 0.60, for 5 Hz at 0.6 |
| Alignment | exact integer offset, fractional to within 0.014 samples, polarity |
| Level invariance | identical spectrum, cepstrum and crest 14 dB apart |

### Four departures, each forced by a signal that broke the obvious version

1. **Delay detection needs the waveform *and* the envelope, not either one.**
   §7's note specifies envelope autocorrelation. That returns the *tempo*: on a
   420 ms echo over notes 900 ms apart it reports 900, because a repeated phrase
   repeats its envelope. The waveform alone is worse in the other direction — a
   held 196 Hz note correlates with itself at every multiple of its period, and
   returns 51 ms. An echo is the only thing that appears in both, so the
   envelope now vetoes and the waveform ranks. Still fails on dense overlapping
   material with a strong pulse, and says so.
2. **`modulation` gained an `am_confidence` field.** A part strummed twice a
   second modulates its own envelope at 2 Hz, which no analysis of the audio
   alone can distinguish from a 2 Hz tremolo. What separates them is *purity*: a
   tremolo is a sine, so its envelope energy sits at one frequency, while a
   plucked note's envelope is rich in harmonics of the note rate. The rate is
   still reported; the confidence says whether to believe it. This is a schema
   addition, consistent with §6.1's stated principle that features carry
   confidences, and it is why `fingerprint_version` exists.
3. **`lf_corner_hz` / `hf_corner_hz` are weaker than the schema implies.** They
   track a cab's bandwidth comparatively, but they carry the *source's* tilt:
   third-octave bands of white noise rise 3 dB per octave through a flat filter,
   which moves both corners inward by about 20%. Documented as comparative,
   used in no loss term.
4. **The objective vector is built from terms that can abstain.** Rather than
   one formula per dimension, each is the mean of whatever sub-terms both sides
   could measure, and a dimension with nothing measurable returns `None` and
   drops out of the scalar entirely. Without that, a reference with no
   detectable reverb would score every candidate perfectly on ambience.

### Five more departures, found by auditing M0 and M1 rather than trusting them

The four above were written down as they happened. These came out of going back
over both milestones against their own exit criteria before starting M2, which is
the only reason they were found — every one of them passed a green suite.

5. **Three fields were added to `Fingerprint v1` without being recorded.**
   `harmonic.f0_hz`, `source.source_sample_rate` and `source.source_channels`.
   Departure 2 above documented `am_confidence` and missed these, which is
   exactly the drift §3.3 exists to prevent. They are kept — the two `source_*`
   fields say what the file was before ingest resampled it, and `f0_hz` is the
   note the harmonic features were measured on, which is what makes their
   confidence auditable — but `from_dict` only validates section names, so
   nothing would have caught them.

6. **`compare()` gained a ninth dimension, `residual`.** §6.2 lists eight.
   `paired-v1` claimed time-domain features "mean what they say" while carrying
   no waveform term at all: `align.residual_db` existed and nothing consumed it,
   so the paired profile differed from the unpaired one only in its weights. The
   caller supplies it, like `prior_deviation` and `complexity`, because a
   fingerprint keeps no waveform. Weighted zero under `unpaired-v1`, where
   subtracting a master from a render measures the difference between two
   performances, and floored at the -17 dB §11 measured between two renders of
   identical parameters rather than at zero.

7. **`predelay_ms` was in the schema and hardcoded `None`.** Now measured — and
   finding it exposed a defect underneath it: `onsets()` reported every onset
   about 30 ms early, because `_frames` is uncentred and a transient raises the
   spectral flux a whole analysis window before it happens. That bias is larger
   than the attack times measured against it. Nothing caught it because every
   feature downstream searches *forward* from an onset and finds the note anyway.

8. **The delay detector was unsafe in both directions on dense material**, which
   mattered because M3's delay inversion consumes it directly. It missed real
   echoes once notes overlapped (the envelope veto had nothing to veto with), and
   reported a repeating four-note phrase as a 1000 ms delay at confidence 0.86 —
   higher than it ever reports a correct answer. The gate that fixes both is that
   **an echo gets quieter and a phrase does not**; where the band is combed by
   pitch the confidence is capped below what `compare._ambience` will use, which
   is an admission rather than a fix. Two limits are now tested as limits:
   feedback above about 0.8, and echoes under about 150 ms beneath notes that
   ring longer than the echo.

9. **Six-channel audio crashed**, against an exit criterion of a valid
   Fingerprint v1 for *any* input. BS.1770 defines its weights up to five
   channels and a meter refuses more.

A mutation pass over `analysis/` accompanied this: of 17 mutations, 10 were
caught by the suite as it stood and 7 survived. Five are now caught. The two that
remain are recorded at the code rather than papered over with a contrived test —
half-wave rectifying the spectral flux is the right definition but not
distinguishable from an absolute value by any signal tried, and `ENVELOPE_RATE`
has headroom, since halving it leaves every measurement inside its tolerance.

### What M2 and M3 inherit

- `analysis.align` exists and is needed between backends, not only for paired
  audio — see §11, finding 2.
- Loss profiles are `analysis/loss_profiles.json`. Tuning weights is a data
  change, and M4's sensitivity screen must set its freeze threshold above the
  0.23 dB per-band render noise that §11, finding 1 measured — which it turns
  into a freeze threshold of about 0.5 dB. `RenderMetadata.band_noise_db` carries
  that number per backend so the screen can ask instead of hardcoding it.
- The signed per-band difference `match/invert.py` fits onto the nine bands comes
  from `analysis.compare.band_delta()`. See §12a for what M2 then found about
  mapping those bands onto the analysis ones.

## 12a. What M2 built, and what the sensitivity test caught

`analysis/refchain.py` is the chain, `match/renderer.py` the protocol, and
`match/renderer_synth.py` the backend that wraps them. Both exit criteria hold: a
2-second DI renders in 21 ms through the default chain, **23 ms with all 45
parameters supplied — which is what a search does** — 51 ms with every effect
engaged at a maximal reverb, and 90 ms for the pathological case of a 16 ms delay
at 95% feedback. 34 tests in `tests/test_refchain.py` show each parameter moving
the fingerprint field it should.

The all-parameters figure is the one that matters and it was nearly reported
wrong: the first measurement was taken with *no* settings supplied, the only case
that avoids re-parsing the manifest, and a review found that supplying 45
parameters cost 47 ms of which about 25 was `load_pack()` reading the same JSON 47
times. `parameter_specs()` is cached and `resolve()` loads the pack once, so the
two cases are now within 2 ms of each other — and a test asserts that as a ratio,
which means the same thing on a slow CI runner as on a fast laptop.

Two decisions are worth carrying forward.

**The chain names parameters; the manifest owns them.** `PARAMETERS` holds keys and
default values only — every kind, unit and range is read from
`packs/morgan/manifest.json` at call time, and settings go through the pack's own
validation, so the synthetic chain refuses exactly what `apply_spec.py` refuses.
That is what lets `match/space.py` build a space over it with no special-casing, and
it means a chain that drifts from the manifest fails a test rather than accepting
values the plugin would reject. `ParamSpec` gained `centre_hz` to carry it, since a
band gain means nothing without its frequency.

**Settings are human values, and `to_spec()` emits them.** §11's third finding said
the renderer and the preset writer must be driven from one source or they will
drift. They are: the same dict renders and writes.

The sensitivity test earned its place immediately by finding three things:

1. **The compressor was measuring as the opposite of itself.** Its detector had a
   5 ms attack, which let pluck transients through untouched while ducking the
   sustain, so turning compression up raised the crest factor from 21.8 to 30.1 dB.
   Fixed with a 0.2 ms attack — and the test now scores the p90−p10 level spread
   instead, which is both the term `compare._dynamics` actually consumes and a
   sturdier observable than a crest built from one surviving transient.
2. **Morgan's EQ centres are not all third-octave analysis centres.** Its lowest
   graphic band is labelled 65 Hz and the ISO band beside it is 63; the other eight
   coincide. `Fingerprint.band_db(65.0)` therefore returns `None`, and **M3's fit
   must map between the two sets rather than index one with the other.** This is
   the cheapest possible place to have learned that.
3. **Two obvious assertions were backwards, both because the spectrum is
   loudness-normalised.** A bright switch that adds 6 dB at 5 kHz pulls 125 Hz down
   about 3 dB with no filter touching it, so only differences *between* bands mean
   anything — the same reason `compare._timbre` removes the mean. And a gate
   *raises* the measured p10: it does not make quiet parts quieter, it removes
   them, leaving a louder distribution behind.

The chain is exactly reproducible, which neither real backend is. That is the
property that makes it a ground truth, and `RenderMetadata.reproducible` is where
a caller asks — defaulting to `False`, because a real host does not repeat itself.

### What a four-way review of M2 found

Four reviewers went over the branch for correctness, test rigour, simplicity and
user experience, each required to demonstrate a finding rather than suspect it.
The test-rigour pass worked by mutating the source and checking whether the suite
noticed. It is worth recording what that turned up, because the pattern repeats:

**Ten mutations survived a green suite**, including deleting the gate that three
docstrings called load-bearing. Two defects were real and both had passed every
test:

1. **A runaway echo was reported as a multiple of its own delay time.** The decay
   gate rejected a lag and then walked up to that same echo's 2T, where the ratio
   is `g²` and passes — so a 250 ms echo at 0.90 feedback came back as 500 ms at
   confidence 0.76, five times the floor `compare._ambience` uses. Fixed lists of
   divisors did not solve it either; the 7th harmonic escaped. `fundamental()` now
   searches the peaks that are present.
2. **`predelay_ms` only worked when the reverb was louder than the direct sound.**
   Anchoring on `argmax(db)` returned index 0 whenever the tail was quieter, which
   is the normal case, and the onset was dropped — 108 of 175 windows. It passed
   because the fixture's tail happened to survive smoothing louder than the 12 ms
   burst that caused it.

**And a redundant-looking gate turned out to be the only defence against the worst
false positive.** Disabling `DELAY_MAX_REPEAT_RATIO` changed nothing in the suite,
and removing it *improved* every runaway-echo case. What it actually protects
against is a phrase repeated verbatim: unpitched, so it leaves no comb, and its
envelope repeats as faithfully as its waveform. Without the gate that reads as a
delay at the loop period with confidence 0.9. The gate stays, its cost is now
written down where it is set, and `fixtures_audio.looped_phrase` exists so the
next person cannot delete it quietly.

Elsewhere: `true_peak_dbtp()` was computed twice per fingerprint (a quarter of the
call), `pyloudnorm` was caught at its call sites and turned into `None` — making a
missing library indistinguishable from unmeasurable material, and silently
suspending loudness normalisation — the multichannel fold was an average
documented as a sum, six paths in the pedalboard spike tracebacked on a mistyped
argument, unrecognised state was applied and the render reported as good, the
wheel shipped no data files at all, and the most-seen error message in the project
read "loading audio needs the analysis extra is not installed."

The mutation set now stands at 25 caught of 27. The two survivors are documented
at the code as not load-bearing rather than covered by a contrived test:
half-wave rectifying the spectral flux is the correct definition but is
indistinguishable from an absolute value on any signal tried, and `ENVELOPE_RATE`
has headroom.

### What M3 inherits

- `analysis.compare.band_delta()` already emits the signed per-band difference
  that `match/invert.py` fits onto the plugin's nine fixed-centre bands — modulo
  the 65-versus-63 mapping above.
- `SyntheticRenderer` gives ground-truth parameters and free renders, so every
  inversion can be checked against a known answer.
- `refchain.parameter_specs()` is the typed, ranged parameter set `match/space.py`
  builds its conditional space from.
- The cache key covers all eight components §6.3 lists, and each is tested to move
  the hash. It is a speed optimisation and not an equivalence: on a real backend a
  cached render is one draw from a distribution.

## 13. Reading list, in the order it becomes relevant

| When | Work | Why |
|---|---|---|
| Before M4 | **ST-ITO: Controlling Audio Effects for Style Transfer with Inference-Time Optimization** | The closest precedent: gradient-free parameter search over non-differentiable, unseen effect chains, with a style representation as the objective. |
| Before M4 | **Improving ST-ITO with a Gaussian Prior** | Evidence for the explicit recipe-prior term in the objective. |
| Before M1 | **Style Transfer of Audio Effects with Differentiable Signal Processing** (DeepAFx-ST) | Architecture and self-supervised framing; also the source of the audio-domain-loss argument. |
| Before M4's benchmark | **Blind Estimation of Audio Effects Using an Auto-Encoder Approach and DDSP** | Why parameter accuracy and audio accuracy must be reported separately. |
| Before M7-2 | **Guitar Effects Recognition and Parameter Estimation with CNNs** | Guitar-specific precedent for supervised parameter estimation, and a realistic sense of its ceiling. |
| Before M1's loss profiles | **Evaluating Sound Similarity Metrics for Differentiable, Iterative Sound-Matching** | The finding that no loss is universally best — which is why loss profiles are data, not code. |
| Before M0 | **spotify/pedalboard** docs, external-plugin section | The host API the backend decision rests on. |
| Before M7-4 | **Differentiable Signal Processing With Black-Box Audio Effects**; **Reverse Engineering Memoryless Distortion Effects with Differentiable Waveshapers**; **DDSP Guitar Amp** | Proxy-model construction, if that branch is taken. |
| Reference only | **SDR — Half-Baked or Well Done?**; ITU P.862 deletion notice | Why SI-SDR is diagnostic-only and why PESQ/STOI are excluded. |

---

## 14. First session's opening move

If the implementing session has no plugin: start at **M1**, and read
`packs/morgan/manifest.json`, `scripts/apply_spec.py`, and
`docs/measuring-against-the-plugin.md` first. The single most useful thing to
produce on day one is `analysis/fingerprint.py` plus a passing
`tests/test_features.py` — everything else in this plan consumes that schema.

If it has macOS and a licence: run **M0** first — both spikes, in one day — and
write the findings into `docs/measuring-against-the-plugin.md` before writing
any feature code. The Tone King answer alone is worth the day.
