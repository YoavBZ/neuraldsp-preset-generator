# Reference-guided tone matching — implementation plan

Status: **M0 through M6 are done. M4's synthetic exit criterion was met — 50 targets,
300 renders each, the full pipeline beating inversion-alone on 49 of 49 — and M5
measured the honest real-plugin gap: the full objective is 46% worse on the mean and
59% worse on the median than the synthetic benchmark implied.** The two spikes ran on 2026-08-05
and their numbers are in §11 and in `docs/measuring-against-the-plugin.md`. The
analysis core landed the same day: `analysis/` plus `scripts/fingerprint.py` and
`scripts/compare_audio.py`. M2 added `analysis/refchain.py` and the `match/`
package — the synthetic chain and the `Renderer` protocol — with §12a recording
what its sensitivity test caught.

M3 added the conditional search space and the inversions (§12b); M4 added the
search, the store, the report and the exit-criterion benchmark (§12c).

§12, §12a, §12b and §12c record where each milestone departed from this document
and where it got something wrong before it got it right — including five
departures found by auditing M0 and M1 against their own exit criteria, and five
*fixes* from M3's second review that turned out to be wrong in their own way.
Every one of those had passed a green suite.

The real Audio Unit backend, measured EQ bases, Morgan benchmark and Tone King
end-to-end run are recorded in §12d. The remaining work named there is follow-up
design work exposed by M5, not a claim that the real backend has yet to land.
M6's user-facing match skill, machine-readable run summary, corrected paired-DI
calibration and two real-stem acceptance runs are recorded in §12e.

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
| Tone King manifest: 259 parameters, **159 marked `internal` / non-writable** | Its writable space is ~100. Its acoustic path is open through `pedalboard` only, and its render cost is **unresolved** — two measurements disagree by more than warm-up explains, so treat "roughly eleven times Morgan's" as the loose upper bound `docs/measuring-against-the-plugin.md` calls it, not a figure to plan a budget on. |
| Each amp has its own module prefix (`ac20*`, `pr12*`, `sw50r*`) and its own 9-band EQ | Search space must be *conditional* on `selectedAmp`. Writing the inactive amp's controls is a silent no-op. |
| EQ bands are at fixed declared centres (65/125/250/500/1k/2k/4k/8k/16k), ±12 dB, plus HPF (20–500 Hz) and LPF (1k–20k), with `centre_hz` already in the manifest | Spectral matching is a **bounded 9-variable least-squares fit**, not a search. See D2. **These are not all ISO third-octave centres**: the lowest is labelled 65 Hz and the ISO band beside it is 63, so `Fingerprint.band_db(65.0)` returns `None` — see §12a. An earlier version of this row said "fixed ISO centres" and the fit was written against that assumption. |
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
   pyloudnorm. `[match]` = adds nothing beyond `[analysis]` — this said "adds cma"
   and D4 below held instead, so CMA-ES is seventy lines of numpy in
   `match/search.py`. `[host]` = adds pedalboard. There is no `[separate]` extra:
   nothing imports demucs yet, and declaring it would advertise a capability that
   does not exist. Every entry point degrades with a clear message when its extra
   is absent.
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
timbre | dynamics | ambience | level | harmonic | spatial | residual |
prior_deviation | complexity
```

`residual` is the paired-DI term and was missing from this list while
`analysis/compare.py` has carried it since M1 — nine dimensions, not eight. It is
weighted 0.9 under `paired-v1` and **0.0** under `unpaired-v1`, because a sample-wise
residual against a different performance measures the performance.

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

M4 added **three** columns to `trials` beyond this list, all recorded in §12c:
`objective_key`, `di_sha` and `di_offset_db`. §12c named two of them and missed
`objective_key` — in the paragraph whose job was to enumerate the departures.
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

> **`docs/handoff-to-macos.md` is the run-book for this milestone** — the commands in
> order, the measured render costs the budget arithmetic rests on, and the seven paths
> that are shaky specifically because no machine so far could exercise them.

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
match      = ["neuraldsp-preset-generator[analysis]"]
host       = ["pedalboard>=0.9"]
```

Two entries this section planned for and `pyproject.toml` does not have. **`cma>=3.3`
is not there**, because D4 above held: `match/search.py` writes the textbook
(μ/μ_w, λ) CMA-ES out with Hansen's constants in about seventy lines of numpy. And
**`separate` is not there** either — nothing imports `demucs` yet, so declaring the
extra would advertise a capability that does not exist. Both get added when something
needs them, which is the same rule the rest of this section states.

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
`fingerprint.py`, `compare.py`, `loss_profiles.json`, plus the two CLIs and 100
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

## 12b. What M3 built

`match/space.py` and `match/invert.py`. The exit criterion holds: on the synthetic
chain, one inversion pass and **zero** renders of search cuts the objective against
an EQ-plus-level-plus-delay target from 1.151 to 0.394 — 66% — and recovers the
delay time outright rather than approaching it.

That claim was worth less than it looked when it was first written, and the
correction is the more useful thing to record. A mutation pass showed the
exit-criterion *test* passing with `invert()` performing no level match, no filter
fit and no spectral fit at all: the delay settings alone move the objective to
0.611, already inside the "better than 0.8×" gate the test used. An aggregate is
not evidence about its parts. The test now attributes the improvement — the
spectral and level fits have to beat delay-alone by a tenth rather than by any
margin at all, the band gains have to be non-trivial, and the loudness gap has to
close.

The space is 125 of Morgan's 132 parameters and 94 of Tone King's 259 — the latter
being its 100 writable ones less its paths and strings, which is the manifest's own
arithmetic rather than a number maintained here. What is excluded is excluded by
category: read-only, `internal`, strings, paths, enums whose member names are
unknown, anything whose `kind` is a bootstrap guess, and writable utility controls
the manifest marks `searchable: false`. Morgan's transpose is the first of the last
category: a separated-stem run let the optimiser move it to imitate the reference's
notes, which is content matching rather than tone matching. The control still
round-trips and can be written deliberately; generated tone searches leave it at
the template value.

Three things were worth learning while building it:

**A switch is not a selector.** The first version excluded any switch without
declared `members`, on the reasoning that applies to enums — and thereby removed
every effect on/off control from the space, so nothing could turn an effect on. An
enum's stored integer is meaningless without its table because the plugin never
displays it; a switch is true or false whatever the plugin labels it, and
`to_binary` never consults members.

The counts are worth stating because they are lopsided and this document first got
them wrong: **none** of Morgan's 32 switches declares members, and **all 21** of
Tone King's do. So the rule emptied Morgan's space completely while leaving Tone
King's untouched — a bug that would have looked pack-specific and been chased in
the wrong place.

**The gate relationships are spelled but not stated.** No manifest field says
`leftCabActive` governs `leftCabPan`, but the names do: a switch called
`<stem>Active` gates the keys in its module that share the stem, longest stem
winning, with `sectionActive` as the deliberate exception that covers its whole
module. `gate_map()` derives it, and a test pins the four cases that matter rather
than the derivation.

Gates also **compose**, which the first version missed: `cabParameters/sectionActive`
gates `leftCabActive`, which gates `leftCabPan`, and checking only the immediate gate
reported 15 of Morgan's 21 cab dimensions live behind a switch that silences all 21.
`Space.active()` walks the chain, and `Space.gate_parents` carries it — kept
separately from `dimensions` because a gate may be a parameter the space excludes
(Tone King's page bypasses are `internal`) and it still gates.

**Clamping into range is how "no effect" becomes "minimum effect".** Dry plucks
measure a *confident* 0.41 s decay — the notes ending, not a room — and the first
`reverb_settings` clamped that up into the plugin's declared 1–60 s and switched
the reverb on. A measurement below what the plugin can produce is now evidence
that the effect is absent, not a value to be rounded up. `delay_settings` and
`tremolo_settings` decline on the confidence floors `compare` itself uses, so a
reading the objective would not trust does not reach a preset either.

The EQ fit is a bounded nine-variable least-squares solve, not a search, and it
carries the caveat the plan asks for: with no `packs/<id>/eq_basis.json` it fits
idealised bell curves at the declared centres, which leak into neighbouring bands —
recovering +8/−6/+5 dB as +7.1/−6.0/+4.0 with about 2 dB of spill either side.
Closing that gap is what M5's eleven renders per amp buy, and the number to watch
is `eq_residual_db`.

`Inversion.as_settings(supported)` exists because an inversion is computed against
the *plugin's* parameters while a backend may model fewer: the synthetic chain
covers 45 and refuses the rest outright, which is correct of it but means the
caller has to filter. `dropped_for()` says what was left behind so a report can.

### What a four-way review of M3 found

Worth recording in full, because the pattern is now familiar: the code was wrong in
the places nothing exercised, and the tests were weakest exactly where the
docstrings were most confident. **31 mutations survived a green suite** — 19 of 38
in `space.py`, 12 of 31 in `invert.py`.

Four defects mattered:

1. **The advertised composition did not work.** `invert()` emits `sw50rEQ/…` keys
   and no `selectedAmp`, so `to_spec` could not tell which amp's controls mattered
   and skipped every one: fourteen values in, four parameters out, no error and no
   caveat. Both modules' docstrings point at this exact pipeline. `to_spec` now
   refuses rather than dropping, `amp_prefix` accepts all three spellings that
   occur in the codebase, and `invert()` names the amp.
2. **A delay's repeats were read as a tremolo.** A 420 ms echo modulates the
   envelope at 2.1 Hz purely enough to clear the 0.75 confidence gate, so a
   full-depth tremolo was written into a target that had none — and `tremolo_settings`
   was the one inversion that emitted no caveat when it acted, so nothing said why.
   It now attributes a modulation matching 1/T of a detected delay to the echo.
3. **`fit_filters` and `fit_graphic_eq` corrected the low end twice.** Both ran on
   one delta, so a flat −3.5 dB deficit set a corner *and* −4.6 dB on band 1 on top
   of it. The corners were also constants: the window edges were hardcoded and the
   code took the boundary of its own window, so a deficit reaching 100, 200 or
   500 Hz all produced 100.0. Both halves of this took two more attempts to get
   right — see the next section.
4. **`pack_id` was inert.** Called with `toneking`, the inversions wrote Morgan's
   parameter paths clamped to Morgan's ranges — `reverb/reverbDecay` at 30 s against
   Tone King's declared 0.5–8, for a parameter it does not have. Silently. One
   `declared()` helper now refuses, which also removed five copies of "look up the
   spec, else a hardcoded fallback", one of which had already drifted.

Two structural mistakes in the conditioning, both found by checking the second pack:

- **Four of Morgan's five section switches gate nothing**, because they live in
  modules containing only themselves while the controls they bypass live elsewhere.
  Only `cabParameters` works, by accident of sharing a module. Guessing the mapping
  would be an unmeasured claim, so the limit is reported by
  `unmodelled_sections()` and tested rather than hidden.
- **Tone King's flat namespace inverted the nesting.** Every parameter sits in one
  module, so `/eqActive` matched `/eqSectionActive` as a child — reporting the page
  bypass dormant and `eqBand1` *active* while the page was bypassed. The first fix
  ruled out every switch-on-switch gate, which overshot: a `sectionActive` gate is a
  genuine parent, and the blanket rule cost four correct gates on Morgan
  (`leftCabActive`, `rightCabActive`, `leftRoomActive`, `rightRoomActive`) while
  changing nothing on Tone King, whose defect was the prefix match alone. The rule is
  now the narrow one: no switch is gated by a switch whose stem is a *prefix* of its
  own name.

And a set of quieter dishonesty: `eq_residual_db` described the pre-floor solution
rather than the one written; `delayMix` was the detector's correlation height times
100, so a confidence of 0.95 asked for 95% wet; `encode` turned a missing key into
0.0, which is a real coordinate, inventing a hard-left pan and a 16 ms delay for
parameters the caller never mentioned; a display name became member index 0, so
`"SW50R"` round-tripped to AC20; and `encode`/`decode`/`bell_basis` raised bare
`ImportError` instead of the install hint.

The tests are now built to fail. Notably: `_exclusion_reason` is asserted against
constructed `ParamSpec`s, because neither shipped pack has a `needs_review`
parameter and the old comparison was `126 >= 126`; a rotation's bounds are asserted
as literal `(0.0, 100.0)`, because every expectation used to come from the function
under test and changing the range to `0..1` left every knob searching 1% of its
travel; and switches are turned on *through the vector*, which no test could do
before, since the fixture set them all `False`.

### What a third review found, mostly in the second round's fixes

Three more reviews on the fixes above. **13 of 56 mutations survived** — up from a
44% kill rate to 77% — and every one of the four defects that mattered now has a
test that kills it. But five of the fixes were themselves wrong, and the worst was
introduced *by* the fix. The pattern to remember is narrower than "code is wrong
where nothing exercises it": it is that a fix aimed at a named symptom tends to
close that branch and leave its twin open.

**The corner is not where the deficit stops, and the bands must not be deleted.**
Both halves of finding 3 above were fixed wrongly.

Deleting the covered bands from the delta left the bands *centred in the deleted
region* with nothing to fit against, and bounded least squares sent one to the rail:
on a target with a 4 kHz low-pass — 23.7 dB short at 16 kHz — the 16 kHz band came
out at **+10.59 dB, a boost**. It also made `eq_residual_db` describe a subset (1.34
reported against 9.82 actual) and broke `basis=`, which is sized to the full delta
and is the only reason that parameter exists. All three go away when nothing is
deleted: `fit_filters` returns the corners' modelled response and `fit_graphic_eq`
subtracts it, so every band stays constrained and fits what the corners leave.

Having the response in closed form fixed the corner too. "Where the deficit stops"
is not the corner and is not near it — a corner is 3 dB down *at* itself and 12 dB
per octave beyond, so the frequency where a roll-off becomes visible sits well above
what caused it: truth corners of 2 kHz and 4 kHz came back as 4 kHz and 6.3 kHz.
Fitting a Butterworth magnitude of `FILTER_ORDER` recovers a low-pass **exactly** —
2 k, 4 k and 8 k all come back as themselves — and end to end on the 4 kHz target the
band RMS against the reference goes from 8.99 dB to **0.38**, against 2.83 for the
rail version and 2.35 for a version that pinned the unconstrained bands instead.

A high-pass still lands low (100/200/400 Hz recover as 80/125/125) and the fit
residual is what makes that visible rather than something to be discovered later: the
cab's own low-end roll-off is in the same measurement, so past about 200 Hz what is
measured is not the shape of a high-pass at all. The residual crosses
`FILTER_MAX_FIT_DB` exactly there — 0.84, 2.43, 3.97 dB — and the caveat is driven by
that number.

The two corners are fitted **together**, over the product of the two candidate lists.
Fitting each against the whole measurement independently makes the other's roll-off
look like unexplained error: a target that really is a 200 Hz high-pass and a 4 kHz
low-pass reported 7.6 dB and 5.5 dB of misfit, chose `100 / 5000`, and said "not the
shape a corner makes" about a difference that was exactly two corners. Jointly it
chooses `160 / 4000` at 2.26 dB, and the band RMS goes 9.37 → 0.92. Two lists of
fourteen grid points is under 200 vector operations, so there was nothing to save.

Second, the same "closed the named branch, left the twin" shape, three times over:

- **The silent drop moved one line down.** `to_spec` was made to refuse a missing
  `selectedAmp`, but `_truthy(None)` is `False`, so an absent `*Active` switch still
  marked its subtree dormant: `to_spec({"selectedAmp": 2, "sw50rEQ/sw50rEQBand1":
  6.0})` emitted only `selectedAmp`. Absence is not a measurement of off; the
  template's own switch decides.
- **`_truthy` was made to share `format.translate`'s vocabulary**, which fixed the
  string half and broke the numeric one. `from_binary("switch", x)` matches the
  literal `"true"` and `"1"` — the two spellings a preset *file* uses — so
  `_truthy(1.0)` came back False while `to_binary("switch", 1.0)` writes `"true"`:
  the gate marked a delay's time and mix dormant while the writer turned the delay
  on, and the preset came out with the template's settings. The recorded rationale
  was also wrong in both halves — `format.translate` does not accept `on`/`yes` and
  does not raise.
- **`_member_index` was made to refuse an unrecognised value** and still truncated a
  non-integral one, the opposite way from the writer: `1.7` resolved to PR12 here and
  `"2"` (SW50R) through `pack.to_stored`.

Third, a set of claims made without measurement. The tremolo decline said the
modulation "is the echo rather than a tremolo" when coincidence is not evidence — a
real 3 Hz tremolo over a 333 ms echo is genuinely indistinguishable by rate, and the
check declines on it; it now says so, and runs *after* the confidence gate so a
modulation that was never tremolo-like is not blamed on an echo. `reverb_settings`
gave an absent measurement the same sentence as an unconfident one ("the notes decay
at different rates" — about a recording nothing was measured from), contradicting the
module's own header. And `−24.6 dB applied at 25 Hz` was attributed to the doubled
band gain when 24.1 dB of it is the corner's own roll-off, which the fix did not
touch.

Caveat volume was the other real finding: six per inversion, in a flat list with no
ranking, five of them still firing on a *perfect* match. Two said the same thing
whenever the delta was empty, and one of the two became false when both ends rolled
off. Now: five on the exit-criterion target, three on a perfect match. Two rules came
out of it — a caveat is for distrusting something that *was written*, so
`fit_filters` no longer reports the ordinary case of declining, and `invert()` says
"no band difference could be measured" once for both fits rather than letting each
say it.

Smaller, all measured: `PackError` was the one error in the repository that is not a
`ValueError`, so `except ValueError` around an inversion caught four of five types and
missed the one the loader raises — `scripts/_cli.py` now catches `ValueError` and
`AnalysisUnavailable` rather than enumerating names that will go stale.
`_validated_amp`'s "Accepted:" list was empty for Tone King, which declares no amps.
`to_spec`'s refusal never named the offending value, so an unrecognised amp was
reported as an absent one. `match/` had invented a module-level `require_analysis`
wrapper twice with different feature strings, against the house style of a
per-function `analysis.require()` — and one of them called `import numpy` *before*
`require`, so the install hint never fired.

Six test weaknesses closed, each a case where the assertion passed through a
different branch than the docstring claimed: the single-band dip that proved
`FILTER_MIN_BANDS` was at 63 Hz, the *fifth* third-octave centre, so the run was zero
bands long before the threshold was consulted; no test asserted a low-pass corner's
value at all, so hardcoding it survived; `0 < feedback <= 100` accepted the unscaled
fraction `0.45`; the leftover-level caveat was matched on the word "level", which the
delay's own caveat also contains; the fit weighting was unasserted; and a
`pytest.skip` stood in for the tremolo rate assertion, which meant the positive half
could vanish silently.

### What M3 deliberately leaves to later milestones

Neither of these blocks M3, and both are named here so they are not mistaken for
oversights:

- `scripts/measure_eq_basis.py` and the committed `eq_basis.json` are M5 work — they
  need the plugin. The fit is already written to consume them and says out loud when
  it is working without them.
- Nothing yet quantises against *audible* resolution measured from the plugin;
  `space.QUANTA` is a set of stated engineering choices, not measurements.

## 12c. What M4 built

`match/search.py`, `match/store.py`, `match/report.py`, `match/benchmark.py`,
`scripts/match_preset.py` and `scripts/benchmark_match.py`. The pipeline runs end to
end: measure a reference, calculate what can be calculated, search the rest on a
budget, and write a spec `apply_spec.py` consumes plus a report that leads with what
not to believe.

**Measured end to end.** Every number below comes from this, recorded so it can be
re-run rather than taken on trust:

```sh
python3 -c "
from analysis import refchain
from tests import fixtures_audio as fx
di = fx.plucks(seconds=4.0, gap=0.9, seed=5)
fx.write_wav('/tmp/ref.wav', refchain.render(di, {
    'sw50rAmp/sw50rVolume': 82.0, 'sw50rAmp/sw50rTreble': 20.0,
    'sw50rAmp/sw50rBass': 75.0}))
fx.write_wav('/tmp/probe.wav', di)"

python3 scripts/match_preset.py --template samples/Example_Clean_PR12.xml \
  --reference /tmp/ref.wav --reference-mode probe --probe-di /tmp/probe.wav \
  --amp sw50r --budget 300 --shortlist 3 --seed 0 --out-dir /tmp/run
```

**1.929 → 0.261 in 298 renders** (0.280 at worst across ±6 dB), 12 caveats, 18
parameters searched and 6 frozen, 110 s. The resulting spec applies through
`apply_spec.py` and reads back through `show.py`: the winner is written by the same
validated path as a hand-authored preset, so a search cannot produce bytes a person
could not have.

**298, not 293.** 293 is what the search spent against its 300-render budget; the other
five are the template's own render, the inversion's probe, and one per shortlisted
candidate for the report's spectrum overlays. An earlier version of this line said
"292 renders" — off by one against a count that was itself short by five, two lines
above a paragraph boasting that calling the screen "2 per parameter" was off by exactly
one. The CLI now prints both numbers and says which is which.

**And the objectives above were wrong for one commit, in the way this section exists to
prevent.** A round of review fixes changed enough of the pipeline to need a re-measurement,
so one was run — with a DI of `seconds=6.0, seed=13` instead of the `seconds=4.0, seed=5`
printed four lines up. It produced 1.719 → 0.256 in the same 298 renders, which is a
perfectly good number about a command that appears nowhere. A reader following the block
above got 1.929 → 0.261 and had no way to tell which of them was lying. The lesson is not
"check your numbers" — it is that **re-measuring means re-running the recorded invocation,
not an invocation**, and the failure is invisible precisely because the wrong number is
real.

An earlier draft of this section quoted numbers from ad-hoc scripts that were never
recorded, and a review could not reproduce a single one of them. That is worse than
having no numbers — a figure with no invocation behind it is an assertion wearing a
decimal point. Anything below that cannot be reproduced from a command in this
document should be treated the same way.

### The four stages, and what each one is for

**The screen pays for itself immediately.** Morgan has 125 searchable dimensions and
CMA-ES over 125 dimensions needs thousands of samples to do anything. Two renders per
parameter plus one baseline — 2N + 1, and calling it "2 per parameter" was off by
exactly that one — turned 24 live supported dimensions into 18 searched and 6 frozen
for 49 renders on the run above. The extremes are
the right probe *because* they are extreme: a control that cannot move the objective
from one end of its range to the other cannot matter in between, whatever the
interactions. Switches and selectors are not screened, because turning an effect off
changes what is *reachable* rather than shifting a value.

**The topology loop is exhaustive over what it is given, and neither CLI gives it
anything.** Interpolating between mic 3 and mic 4 means nothing — the numbers are
labels, and a gradient over labels is a gradient over the order somebody listed them
in. It is a product, so five two-state switches is 32 whole inner searches; guessing
which of Morgan's 32 switches are worth that is not something the code can know, so
the caller says.

**And no caller says.** `topologies()` is written, tested and reachable from Python,
but neither `match_preset.py` nor the benchmark passes `switches=` or `selectors=`, so
in the shipped pipeline it always returns the seed alone and the discrete choices are
whatever the template had. Measured consequence: the `inversion` and `full` arms score
*identical* selector accuracy in every benchmark run, because the search never changes
a discrete choice. This is a stage that exists rather than a stage that runs, and it
should be read that way until a `--enumerate` flag exists or M5 needs it.

**The run now says so too**, which it did not before. A reader of the report saw
`delay/delayActive on → off`, `/selectedAmp 1 → SW50R` and `reverb/reverbActive on → off`
in the shortlist's diff column — all of them from the *inversion* — and had every reason
to conclude discrete choices were being searched. Naming a limitation only in this
document is naming it to the wrong audience: a caveat now fires whenever the enumeration
produces a single variant, saying that the cabinet, the microphone, the amp and every
on/off switch are whatever the starting point had.

**CMA-ES is the textbook (μ/μ_w, λ) with Hansen's constants written out** rather than
tuned, numpy only, no `cma` dependency (§2, D4). Bounds clip the *evaluated* vector, and
that is the whole of it: the new mean is a weighted average of already-clipped samples
with positive weights summing to one, so it is a convex combination of points inside the
box and cannot leave it.

This paragraph has now been wrong twice in opposite directions, which is worth recording
because both versions were arguments rather than measurements. The first said clipping
the mean lets a parameter stick on a bound it was only passing through. The second said
the opposite and carried a table — unclipped 2.5e-03 against clipped 2.6e-06, mean range
(−4.2, −0.55) — that cannot have come from this algorithm: reproduced at four seeds the
two agree to every digit, and with the optimum placed *outside* the box both pin the mean
at exactly 0.000. The clip on the mean was dead code all along, and it has been removed.
The lesson is §12c's own: a figure with no invocation behind it is an assertion wearing a
decimal point, and that applies to figures that argue *for* the current design as much as
to ones that argue against it.

**The robustness re-rank earns its place.** It reorders the shortlist whenever the
reference-level winner is fragile, and says so when it does — on the run recorded
above the winner holds up (0.261 at the reference level, 0.280 at worst), which is the
outcome to hope for rather than the one that demonstrates the stage. It is ordered by
the worst level rather than the mean: a preset that is excellent at one input level
and unusable at another is not a good match that happens to vary.

**But most of that ±6 dB spread is loudness, not tone.** Measured per candidate and per
offset on the run above, the `level` dimension accounts for **84% to 100% of the change
in the total, 97% on average** — the run's own caveat prints "about 97%" — while `timbre`,
the term that would actually show breakup, moves by 0.0001 to 0.003. Turning the input up
makes the render louder and the level term counts that, so "0.280 at worst" is a much
weaker statement about breakup than it reads as. (An earlier version of this paragraph
said "35% to 96%", from the same mis-run as the objectives above.) The
score is left alone rather than having `level` dropped from it, because a preset whose
compression holds its output steady across playing levels genuinely is more robust and
that belongs in the number; what was missing was saying so, and a caveat now fires with
the percentage whenever the level term is the majority of the movement.

### Three things this got wrong first

**The screen's probes were thrown away.** Nearly fifty renders that had been paid for
and scored, discarded because they were "measurements" rather than "candidates" — and
a parameter at an extreme is a perfectly good parameter vector. On the run that found
it, one probe scored **0.525** while the entire CMA-ES stage found nothing better than
0.694; feeding them into the Pareto archive took that run to 0.539 for no extra
renders. A sixth of the budget was being spent and then binned.

**`trials` did not record which DI a render used**, and §6.4 does not list it. That
omission is an oversight rather than a decision — §6.3's own cache key includes
`di_sha256` for exactly this reason. Without it `Store.best` compared a candidate
scored at the reference level against the robustness re-rank's own renders of the same
parameters 6 dB quieter, and picked the quiet one: a quieter DI drives the amp less
hard, so it can look like a better match for a reason that has nothing to do with the
parameters. `di_sha` and `di_offset_db` are now columns and `best()` defaults to the
reference level. **This is a departure from §6.4.**

**`Dimension.quantise` could emit an illegal value**, which is M3 code that M4's
benchmark found. `_from_unit` clamped *before* stepping: `tremoloRate` is declared
0.15–15 Hz with a 1 Hz step, so the bottom of its range clamped to 0.15 and then
rounded to **0.0**, below the plugin's own minimum, in a value the search would go on
to write and `apply_spec` would refuse. Clamping now happens after stepping, so a
result at an endpoint may not sit on the step grid — which is correct, since the
endpoint of a declared range is legal by definition.

### The exit criterion, and what it says

`scripts/benchmark_match.py` samples random legal parameter vectors, renders each,
throws the vector away, and recovers it three ways. The arms are **nested** —
`inversion` is `recipe` plus the calculated step, `full` is `inversion` plus the
search — and that is not a detail. The first version searched from the recipe seed
instead of the inverted one, so the `full` arm measured search-*only* and reported
**DOES NOT SHIP** against a pipeline that works. Reproduced by patching the nesting
back out: over six targets it scored 1.211 against inversion's 1.118. A benchmark whose
arms are not nested does not measure what each stage adds, and it reports its wrong
verdict with complete confidence.

```sh
python3 scripts/benchmark_match.py --targets 50 --budget 300 \
  --json docs/m4-benchmark-50.json
```

**50 targets, a 300-render budget, zero failures, 95 minutes. It ships.**

(The `--json` is not decoration: without it nothing is written, and the version of this
line that omitted it could not have produced the committed evidence it cites four
paragraphs below. Everything else about the invocation checks out — the defaults
`--pack morgan --amp sw50r --seed 11` match the file's own header, and target 0
reproduces bit-for-bit — but a reproduction command that does not reproduce the artefact
is the same failure as a number with no command behind it.)

| arm | mean objective | median | best | worst | param MAE | selector | renders |
|---|---|---|---|---|---|---|---|
| recipe | 3.039 | 2.533 | 0.661 | 8.716 | 0.247 | 0.643 | 0 |
| inversion | 1.514 | 1.309 | 0.418 | 6.231 | 0.257 | 0.658 | 49 |
| full | **0.641** | **0.461** | **0.084** | 6.089 | 0.266 | 0.658 | 14,375 |

The mean is what the gate uses, and the per-target figures are stronger than it:
**the full pipeline beats inversion-alone on 49 of 49 targets individually**, and is
worse than the recipe seed on **none** of them.

That last one is **measured, not guaranteed**, and an earlier version of this paragraph
claimed otherwise. The mechanism it cited — "the starting point is a candidate, so the
answer cannot be worse than what was handed in" — is `fallbacks=`, which only
`match_preset.py` passes; `benchmark.py` calls `search()` without it, so in the `full`
arm the recipe seed is never evaluated and only the *inverted* seed is. The committed
data also shows the chain going backwards before the search starts: inversion is worse
than recipe on 2 of the 49 targets (t6 1.729 against 1.692, t16 0.667 against 0.661). So
"worse than the recipe on none of them" is an empirical result about these 50 targets,
like every other number in the table — which is fine, and it must not be sold as a
property of the design. The property does hold in the CLI, where `fallbacks=[template]`
is passed, and that is the path a person uses; it was added after a review found the
pipeline announcing "−488% closer" on a template it had made worse.

**Renders per target: 293 in the mean, 301 at the maximum** (target 46). The budget is
per *search*, and `_run_arm` adds the inversion's own render on top of it, so an arm can
exceed 300 by exactly that. An earlier version of this line said "293 renders per target
against a budget of 300" without the qualifier, which reads as a ceiling it is not.

One target was discarded: a legal parameter vector put the noise gate above the signal
and rendered silence, which is skipped rather than counted as any arm's failure, because
it is the sampler's doing.

Every outcome of that run is committed at `docs/m4-benchmark-50.json` — 147 rows, three
arms by 49 targets — so the table above can be checked without spending the 95 minutes
again. The command reproduces it; the file is what it produced.

**The parameter MAE gets monotonically worse** — 0.247 → 0.257 → 0.266 in the mean and
0.243 → 0.257 → 0.269 in the median. Over 50 targets that direction is consistent;
over six it is not (three small runs gave 0.245 → 0.259 → 0.253, 0.243 → 0.243 → 0.248
and 0.258 → 0.280 → 0.285), so **the claim worth making is the one at n=50 and the
small runs should not be read as confirming it.**

Either way the divergence is the actual situation rather than a flaw in the
measurement. The plugin's controls are not identifiable from its output: a different
volume with a compensating EQ curve sounds almost identical, so a search that closes
the objective by four times has no reason to close the parameter error at all. It is
the pipeline *earning* the objective by moving controls away from where the truth
vector had them. Reporting only the MAE would condemn something that works; reporting
only the objective would let a real failure through. Both are reported, and `verdict()`
states in its own output that the MAE is deliberately **not** part of the gate —
nobody should have to guess whether that was a decision or an omission.

What the gate does *not* claim: that 0.641 is good. There is no calibration that says
so, and the worst target still scores 6.089. What it claims is that each stage earns
its renders, which is the question §M4 asks.

### What a three-way review of M4 found

Three agents — mutation testing, correctness, user experience — against the code as it
stood after the previous round's fixes. Fourteen surviving mutants, every one applied and
measured rather than argued for, plus twelve defects. The pattern this repository keeps
producing held again: **a fix aimed at a named symptom closes that branch and leaves its
twin open.**

**The twins, this time.**

- `search()` grew a separate branch for a control one end of whose range silences the
  render, so the caveat block said "one end of `parameters/gateThreshold` silences the
  signal entirely". Four sections down, in the same document, the screen's table said
  `frozen — too small to matter`, because `report._screen` kept its two-way
  `if moved < 0.01`.
- `screen()` raises its floor to the backend's own render-to-render noise and then
  discarded that number, so both the caveat and the report classified against the
  `SENSITIVITY_FLOOR` constant instead. With a backend declaring 0.23 dB of band noise
  the effective floor is 0.0767, and a parameter cut by the *floor* at 0.0208 was
  reported as one of "the weakest 25% that did move it — a larger budget would search
  them". No budget will: the floor is not a budget. `screen` now returns a `Screen`
  carrying the floor it used.
- `_unmeasurable` closed the silent-reference branch of "this reference cannot be
  measured" and left the non-finite one open. A float WAV holding NaN — a corrupt bounce
  — reached a covariance eigendecomposition and came back as
  `error: Eigenvalues did not converge`, naming neither the file nor the cause, from
  inside the handler written to stop tracebacks reaching people. Refused in
  `analysis.io.load` now, where the file is still in hand.

**A measurement nobody made.** `screen` recorded `movement = 0.0` for a control whose
other end silenced the render, directly beneath a comment claiming the movement was
"recorded against the end that did render, so the control can still be frozen or searched
on evidence" — and 0.0 is below every floor, so it could only ever be frozen. Measured on
Morgan, `gateThreshold`'s live end scored 0.8438 against a baseline of 0.8025: a movement
of 0.0413, four times the floor, filed as zero and printed as `0.0000` under a column
headed "distance moved". It stays frozen — with one extreme unscoreable there is no bound
on the control's effect, so there is nothing to hand an optimiser — but that is now said
in `silences` rather than implied by a zero no floor could clear.

**Three mutants that broke the optimiser silently.** Inverting `refine`'s termination test
to `step > _quantisation_step(...)` ends the search after one generation: 53 renders of a
120 budget and a score three times worse — and it passed, because the guarding test only
required the "step became finer" caveat to be *present*, which stopping immediately also
satisfies. Recombining the worst μ samples instead of the best cost 0.144 → 0.463 and
nothing noticed, because the end-to-end winner is often one of the screen's probes rather
than anything CMA-ES found. And `ordered[cut:]` reversed froze the two strongest movers
while the caveat still said "the weakest 25%". All three now have tests that fail on the
mutation.

**Two lines the shipped pipeline depends on and no test touched.** `fallbacks=` — the
template as it arrived — could be deleted entirely and every test passed including the
CLI's, which is the regression that produced "−488% closer". So could
`candidates = list(probes)`, the line that recovers the sixth of the budget the screen
spent.

**A guarantee the bare clone did not have.** `scripts/_cli.py`'s `guarded()` imported
`analysis` for one exception name, which put the analysis extra on the path of `show.py`,
`apply_spec.py` and `bootstrap_pack.py` — the three tools `dependencies = []` is a promise
about. On a checkout without the extra, `bootstrap_pack.py` died with
`ModuleNotFoundError: No module named 'analysis'`. CI never saw it because CI installs the
package, which makes `analysis` importable from any working directory, and
`test_no_dependencies.py` never saw it because blocking numpy leaves `analysis` itself
importable. Matched by name now, like the sibling `soundfile` clause, and the test blocks
`analysis` too.

**A store the version guard could not refuse.** `SCHEMA_VERSION` stayed at 1 through two
column additions in this milestone, and the check ran *after* `executescript` — where
`CREATE TABLE IF NOT EXISTS` is a no-op on an existing table with the wrong columns but
`CREATE INDEX ... ON trials(objective_key)` is not. So an `--out-dir` holding a store from
an earlier commit of this same branch failed inside the schema and reported "either empty
or a store this tool wrote", about a store this tool had written.

**What the report was not saying.** The headline was the reference-level score in 2 rem
while the shortlist was *ordered* by the worst-case score in small grey text below it. The
objectives table put `dynamics 3.440` beside `timbre 0.755` with no weights, so the
weighted sum above could not be checked against the only breakdown offered — and it let
a run print "25% closer" while timbre and level, the two dimensions a player notices
first, both got worse. The `spatial` note hedged "a little kinder" where the source
comment eight lines up knew the answer exactly (8% of the live weight). The starting
point's `prior_deviation` and `complexity` read 0.000 against candidates' 0.077 and 0.196
because they were scored from different origins. And the shortlist listed three EQ bands
under "changed from the starting point" while a caveat above said those same twelve values
"have not been heard, only calculated". All five are fixed; none needed information the
report did not already have.

**The number a person acts on.** `--budget`'s help called 60 the floor, and at exactly 60
the optimiser cannot take a single step on Morgan — the run then said "raise --budget to
at least λ more than the fixed costs above", where nothing above had printed a fixed cost.
Two messages for one fact, and the useless one was the one that fired. There is one now,
it names the number (66 on the run that provoked it), and it is hoisted above the other
caveats because it says the headline was not searched for. The help gives the arithmetic
instead of a round number. And the benchmark, which discarded the search's caveats
entirely, ran zero optimiser generations at `--budget 60` across every target and still
printed **SHIPS**.

### Departures from §M4 worth naming

- **The envelope overlay is a table of statistics.** Against a different performance
  an envelope picture is a picture of the performance, which is why the unpaired
  profile weights dynamics down in the first place. What survives comparison across
  performances is the statistics, so those are what the report shows.
- **`--renderer swift` and `pedalboard` refuse by name.** They are M5. Accepting the
  flag and substituting the synthetic chain would be the worst option available: the
  run would succeed, the report would look right, and every number in it would
  describe a Python approximation rather than the plugin.
- **The benchmark's `recipe` arm starts from a neutral seed**, not from
  `packs/recipes.py`. Picking a recipe needs a genre or a reference, which a random
  target does not have. A recipe-stack seed would make that baseline stronger and the
  comparison more honest; the neutral seed is what a caller with no other information
  actually starts from, and this is stated in `centre_seed` rather than left to be
  discovered.
- **Sobol is not used** for the topology enumeration. Both packs' discrete spaces are
  small enough to enumerate exhaustively, and a quasi-random sample of 32 points out
  of 32 is 32 points with extra machinery.

## 12d. What M5 built, and what the plugin said about M1-M4

The first milestone whose numbers are facts about the plugin. Everything before it
was measured against `analysis/refchain.py`, which shares Morgan's topology and
models none of its DSP.

Measured on macOS 15 (Darwin 25.5.0), Morgan Amps Suite **1.1.1** (`auval` reports
`Component Version: 1.1.1 (0x10101)`), Python 3.14.6, numpy 2.5.1, scipy 1.18.0.
Every figure below has the command that produced it beside it.

### The backend

`match/renderer_au.py` drives `scripts/au_render_server.swift` behind the
`Renderer` protocol: one plugin instance, one process, commands over stdin.
`--renderer swift` on `scripts/match_preset.py` and `scripts/benchmark_match.py`.

Throughput, measured rather than assumed:

```
python3 - <<'EOF'
import time, numpy as np
from match.renderer_au import AudioUnitRenderer
from tests import fixtures_audio as fx
di = fx.plucks(seconds=3.0, gap=0.9, seed=13)
with AudioUnitRenderer('morgan') as r:
    r.render(di, {'selectedAmp': 2})
    t0 = time.time()
    for v in range(10, 90, 10):
        r.render(di, {'selectedAmp': 2, 'sw50rAmp/sw50rVolume': float(v)})
    print('%.0f ms/render' % ((time.time() - t0) / 8 * 1000))
EOF
```

431 ms for a 3-second DI, against 1.1-1.3 s to instantiate. §3.2's 291 ms was for a
2-second excitation, so per second of audio the two agree.

### Two silent defects the first real renders exposed

**`AVAudioFile.read(into:)` returns short.** Asked for all 144000 frames of a
3-second file in one call it returns 143340, and the shortfall varies with length —
916, 788, 660, 340 frames at 48000, 96000, 144000 and 200000. `au_render_server`
read once and trusted `frameLength`, so **every `--input` render was truncated**,
which is the path a search runs on. It now loops until the file is consumed and
refuses a partial read rather than rendering the front of a DI and reporting
success. Nothing had noticed because nothing had rendered through a file at scale.

**`selectedAmp` was dropped from every render.** `match/search._supported_keys`
flattened a backend's `("", "selectedAmp")` to `/selectedAmp` and compared it
against `Dimension.path`, which is `selectedAmp`. The amp selector therefore never
reached the plugin, and writing a control on an amp that is not selected is a
no-op — so a search would have moved one amp's tone stack while the plugin stayed
on another, with nothing failing and every number describing the wrong amp. The
synthetic chain models a single amp and never declared `selectedAmp`, which is why
M3 and M4 could not have caught it.

A third, in the new code rather than the old: an enum arriving as a display name
(`'SW50R'`, which is what `invert()` emits and `apply_spec.py` consumes) was
converted with `int(float(...))` instead of through the pack, so **every inversion
became a failed render**. The search reported that as "a silent render, or no
dimension the loss profile weights" — a message that named neither cause.
`Candidate` now carries the error the store had always recorded.

### The equaliser, measured

`scripts/measure_eq_basis.py` renders each band at +6 and -6 dB against a flat
reference and writes `packs/<pack>/eq_basis.json`. Both signs rather than one
against flat, so every even-order term cancels; the flat render is kept as a
linearity check and the run reports the bend.

```
python3 scripts/measure_eq_basis.py --pack morgan     # 57 renders, 67 s
```

What the fallback got wrong, which is what the caveat had been warning about:

| | textbook bell | measured (sw50r, 1.1.1) |
|---|---|---|
| 65 Hz band, at 25 Hz | 0.098 dB/dB | **0.977** — it is a shelf, not a bell |
| 16 kHz band | peaks at 16 kHz | peaks at 20 kHz — also a shelf |
| 1 kHz band, at 2 kHz | 0.171 dB/dB | **0.453** — 2.6x the assumed overlap |

Measured twice, at excitation RMS 0.1 and 0.03, because the first run peaked above
full scale on all three amps. The two bases agree to within 0.021 dB/dB, so the
peaks did not corrupt it; the committed file is the quieter one and `--level`
exists so the check can be repeated.

**A basis belongs to a backend, not to a pack.** Loading it by pack alone made two
of `tests/test_invert.py`'s assertions fail, correctly: the synthetic chain builds
its bands from `FALLBACK_Q` and is not the plugin, so fitting the plugin's overlap
to the chain's audio makes that fit *worse*. It is a `Renderer.eq_basis()` hook
that defaults to `None`, answered by `AudioUnitRenderer` and declined by the
synthetic chain.

What it bought, on a ground-truth match against the real plugin:

```
# reference: a known parameter vector rendered through Morgan, then discarded
python3 scripts/match_preset.py --template samples/Example_Clean_PR12.xml \
  --reference /tmp/ref_real.wav --reference-mode probe --probe-di /tmp/probe_real.wav \
  --amp sw50r --renderer swift --budget 300 --shortlist 3 --seed 0 --out-dir /tmp/run_real
```

| | textbook basis | measured basis |
|---|---|---|
| distance to the reference | 1.045 -> 0.488 | 1.045 -> **0.370** |
| across ±6 dB of input | 0.590 at worst | **holds up** |
| searched / frozen | 20 / 20 | 25 / 15 |

### `_backend_floor` went live, and it costs half the search space

The least-exercised path in M4. With the synthetic renderer `band_noise_db` is 0.0
and the raise never executed outside a unit test. On the plugin it is 0.23, and the
screen's floor becomes 0.0767 — which freezes **15 to 20 of 40 parameters** where
the same run on the synthetic chain froze 6 of 24.

The declared 0.23 dB is slightly optimistic. Measured over 8 renders of identical
parameters:

```
python3 - <<'EOF'
import numpy as np
from match.renderer_au import AudioUnitRenderer
from analysis.features import third_octave_bands
from tests import fixtures_audio as fx
di = fx.plucks(seconds=4.0, gap=0.9, seed=5)
with AudioUnitRenderer('morgan') as r:
    rows = [np.array(third_octave_bands(
        np.asarray(r.render(di, {'selectedAmp': 2, 'sw50rAmp/sw50rVolume': 60.0}).audio,
                   dtype=np.float64).mean(axis=1), 48000)['band_db']) for _ in range(8)]
m = np.vstack(rows); print('max spread %.3f dB' % (m.max(0) - m.min(0)).max())
EOF
```

0.79 dB overall, **0.30 dB** across 50 Hz-16 kHz, median 0.09. The constant stays at
0.23 because raising it freezes more controls and that is a decision with
consequences for every result, not a constant to change in passing — but 0.23 is
below what this machine measures, so the screen is currently slightly too
permissive.

`isolate` does **not** fix reproducibility. `au_render_server.swift` calls it "the
only way found to make a second render in the same process match the first"; on
1.1.1 two renders differ by -15.4 dB relative to the signal without it and -15.7 dB
with it, and neither is bit-exact. The comment is wrong and the -17 dB figure is
approximately right.

### `spatial` is not a guaranteed zero any more

§6.6 of the handoff: it reads 0.000 on every synthetic run because both sides are
dual-mono, and it carries 8% of the weight. Against the plugin, the seed candidate
of the ground-truth match scores `spatial: 0.0253`. It discriminates.

### The exit criterion: what the plugin costs against the approximation

```
python3 scripts/benchmark_match.py --targets 50 --budget 300 --json /tmp/bench-synthetic.json
python3 scripts/benchmark_match.py --targets 50 --budget 300 --renderer swift \
  --json docs/m5-benchmark-morgan.json
```

Both ship. Every row of both is in `docs/m4-benchmark-50.json` and
`docs/m5-benchmark-morgan.json`, and the latter carries the backend that made it,
`reproducible: false` included.

| arm | synthetic mean | **plugin mean** | synthetic median | **plugin median** |
|---|---|---|---|---|
| recipe | 3.039 | 2.572 | 2.533 | 2.323 |
| inversion | 1.514 | 1.551 | 1.309 | 1.501 |
| full | **0.638** | **0.932** | **0.453** | **0.719** |

| | synthetic | plugin |
|---|---|---|
| param MAE (recipe / inversion / full) | 0.247 / 0.257 / 0.258 | 0.253 / 0.271 / 0.271 |
| selector accuracy | 0.658 | 0.624 |
| failure rate | 0% | **0%** |
| renders | 14375 | 14827 |
| wall clock | 3171 s | 12254 s |

**The honest gap is 46% on the mean and 59% on the median.** The full pipeline
scores 0.932 against the plugin where it scored 0.638 against the approximation.
Measured as a share of the distance the recipe stack leaves on the table — which is
the comparison that survives the two arms having different targets — it closes to
36% of the recipe baseline against the plugin and to 21% against the synthetic
chain. Against the inversion alone: 60% against the plugin, 42% synthetic.

So the pipeline works against the real thing, beats both baselines on every one of
50 targets, and is roughly half as effective as the synthetic numbers implied. That
is M5's deliverable.

Two predictions in the handoff did not hold:

- **The failure rate is zero.** "A real backend will have some — a silent render,
  an instantiate that did not come back." In 14827 renders there were none. The
  gate exists and is worth keeping; it did not fire.
- **Parameter MAE does not get much worse.** It rises 0.253 → 0.271 across the
  arms, the same shape as the synthetic run, for the reason `verdict()` already
  states: the controls are not identifiable from the output.

### The benchmark reproduces across machines; the single-run walkthrough does not

The synthetic arm above reproduces `docs/m4-benchmark-50.json` closely — 0.6385
against a committed 0.641 on the full arm, 3.0386 against 3.039, the same 14375
renders — on a different machine and a different numpy. Averaging 50 targets is
what makes it portable.

One run of `match_preset.py` is not. `docs/handoff-to-macos.md` §8 gives a command
and says to expect `1.719 -> 0.256` in 298 renders with 10 caveats, adding that
"the pipeline is deterministic and it reproduces bit-for-bit on this machine, so a
difference is a finding." It gives `1.717 -> 0.180` in 298 renders with 12 caveats
here — and gives the same at `ac03d5e`, the commit that shipped those numbers, so
nothing in M5 caused it. The starting distance differs in the third decimal before
any search runs, which is a numeric-library difference rather than a code one, and
CMA-ES diverges from there.

The rule that follows: **a committed aggregate is a cross-machine check and a
committed single-run figure is not.** §8's numbers should have been recorded as
one machine's, and this is the fourth time a figure in this repository has failed
to reproduce from its own command.

### The ±6 dB re-rank still measures loudness, on the plugin too

§6.2 of the handoff: the `level` dimension accounted for 35-96% of the change
across the input offsets on the synthetic chain, while `timbre` moved by about
0.001, and the question for M5 was whether `timbre` starts moving on a plugin
whose breakup genuinely depends on how hard it is hit.

It does not. Across the 18 targets of the 50-target run that reported the figure,
the level term accounts for **50% to 100%** of the change, median **71%** —
the same range as the synthetic run.

```
python3 -c "
import json, re
d = json.load(open('docs/m5-benchmark-morgan.json'))
v = [int(m.group(1)) for c in d['caveats']
     if (m := re.search(r'about (\\d+)% of the change in score across', c))]
print(sorted(v))"
```

So the stage needs rethinking, as §6.2 said it would if this came back negative.
The caveat naming the percentage is doing real work and should stay until the
re-rank measures something other than how loud the render got.

### The first `paired-v1` run silently omitted the term carrying 0.9 of its weight

§6.7 of the handoff calls `paired-v1` "the highest-confidence path in the whole
design — regime weight 1.0, and the only profile that weights `residual` (0.9)
because with a paired DI you can compare waveforms sample-for-sample rather than
statistically", and asks whether `residual` behaves once it meets a real pair.

It does not behave, because **it never runs.** A paired run against a real reamp
— a DI rendered through Morgan from a known vector, then recovered from that DI
and that recording — completes, scores 292 trials, reports `1.454 -> 0.654`, and
produces these dimensions:

```
python3 -c "
import sqlite3, json
db = sqlite3.connect('runs/paired-001/trials.sqlite3')
rows = [json.loads(r[0]) for r in db.execute(
    'select objectives_json from trials where objectives_json is not null')]
print(sorted({k for r in rows for k in r}))"
```

```
['ambience', 'complexity', 'dynamics', 'level', 'prior_deviation', 'spatial',
 'timbre', 'total']
```

No `residual`, in any of the 292. `analysis/align.residual_db` exists and is
tested; `analysis.compare.compare()` takes a `residual_db=` argument and weights
it; and **no production caller anywhere passes it** — not
`match/search.py`'s `Evaluator.evaluate`, not `scripts/match_preset.py`, not
`scripts/compare_audio.py`. `_residual` returns `{}` for `None`, so the term
drops out and the total is formed from what is left.

`tests/test_compare.py` has known this since M1: its own comment reads "no
waveform term at all — `align.residual_db` existed and nothing consumed" it.

So `--loss-profile paired-v1` is, in practice, the unpaired objective with
different weights on the remaining dimensions. Every claim resting on the paired
regime being the strongest path rests on a term that has never been computed
outside a unit test. Nothing in the 14 caveats that run printed said so, which is
the part that most needs fixing: a profile that weights a dimension the run could
not measure should say which dimension and how much weight went with it.

It is fixed after that audit. `Evaluator` now requires `reference_audio` whenever
the selected profile gives `residual` a non-zero weight, aligns every candidate
render to those samples, passes the measured dB residual into `compare()`, and
includes the reference waveform hash in the score-cache key. The benchmark updates
the fingerprint and waveform together for every generated target. The match CLI
refuses `paired-v1` outside `--reference-mode paired_di`, and `compare_audio.py`
refuses to pretend two stored fingerprints contain samples.

Low-correlation alignment is not hidden: below absolute correlation 0.30 the
signals are compared unshifted rather than moved by an offset inferred from noise,
and the run reports how often that happened. A paired run also says that the files
themselves cannot prove the reference is a reamp of the exact DI; the mode flag is a
declaration, not provenance.

The production path is pinned by these invocations:

```
python3 -m pytest -q tests/test_search.py tests/test_analysis_cli.py \
  tests/test_match_cli.py tests/test_benchmark.py -k paired

python3 scripts/compare_audio.py reference.wav reference.wav \
  --profile paired-v1 --json
```

The second command must report a residual objective of 0.0 and a trusted
alignment. A fresh real-plugin DI/reamp calibration is still required before any
new number is attached to the 0.9 weight; the earlier `1.454 -> 0.654` run omitted
the term and is not evidence for it. No substitute pair should be used: separated
stems are different performances and belong to `unpaired-v1`.

### The topology stage now runs, and it is not free

`topologies()` was written and tested in M4 and no caller ever passed `switches=`
or `selectors=`, so every run left the cabinet, the microphone, the amp and every
on/off switch wherever the template had them. `--enumerate` on both CLIs reaches
it. Paths are routed to switches or selectors by the dimension's own kind, and
`--list-enumerable` is renderer-specific: it prints the 8 discrete controls the
synthetic chain actually models, or the 34 Morgan/sw50r controls the Swift backend
can drive. The first version printed and accepted all 34 for both backends. Values
for the other 26 were later dropped by `Evaluator._settings`, so a request such as
`--enumerate cabParameters/leftMicType` silently created eleven identical
synthetic topologies and split the budget eleven ways. Those paths now fail before
the reference is read.

The same ground-truth match, same template, same seed, same 300-render budget:

| | distance | worst across ±6 dB | searched / frozen |
|---|---|---|---|
| textbook basis, nothing enumerated | 1.045 -> 0.488 | 0.590 | 20 / 20 |
| measured basis, nothing enumerated | 1.045 -> **0.370** | holds up | 25 / 15 |
| measured basis, one switch enumerated | 1.045 -> 0.438 | 0.458 | 25 / 15 |

**Enumerating made it worse**, and that is the stage working rather than failing.
Two topologies split one budget, so each got about 107 renders instead of 293, and
the run says so:

> 2 topologies share the budget, so each got about 107 renders. Enumerating fewer
> switches gives each remaining one a deeper search.

`sw50rBright` was not part of the target vector, so there was nothing to find and
the halved search depth is pure loss. That is the trade the flag makes: breadth
against depth on a fixed budget, and it only pays when the discrete control is
actually wrong in the template. On Morgan the screen alone costs 2 per dimension —
plus one baseline — so a budget that can afford several topologies is a large one,
and the CLI refuses up front with the exact active/supported count rather than
discovering it after an hour.

**Two synthetic selector experiments were invalid, and the boundary now refuses
them.** §6.3 predicted the `inversion` and `full` arms would score identical
selector accuracy for as long as nothing was enumerated. Two early experiments
appeared to reach the topology stage and still scored identically:

| enumerated | inversion selector | full selector |
|---|---|---|
| `cabParameters/leftCabPhase` | 0.6875 | 0.6875 |
| `selectedAmp` | 0.6406 | 0.6406 |

Identical target by target, not merely on average. The immediate cause was simpler
than either interpretation first given: **the synthetic renderer supports neither
control.** The topology value remained in the candidate vector — which is why the
run and selector metric looked plausible — and was removed from every render.
These figures are evidence about the missing renderer boundary check and nothing
about whether topology search can recover a selector.

- `leftCabPhase` is not implemented by `analysis/refchain.py`; describing it as
  merely inaudible was too generous. It was never rendered.
- `selectedAmp` is not implemented by the one-amp synthetic chain **and** is held
  constant by the benchmark itself. `random_vector` has
  `if dimension.key == "selectedAmp": continue`, so no target ever asks for a
  different amp. **The synthetic benchmark therefore cannot measure amp selection
  at all**, and could not have whatever the search did.

The preflight budget arithmetic had the same boundary error: it counted all 92
space dimensions where `screen()` charged only active, continuous dimensions the
renderer supports. It now derives the exact fixed screen cost from the same
post-inversion seed and supported-path set the search will see, instead of charging
for every dormant or unsupported dimension in the pack.

The real-plugin `sw50rBright` run above proves that variants reach distinct plugin
renders and share the budget. A benchmark target with Bright deliberately wrong
in the neutral seed supplies the missing selector test:

```
python3 scripts/benchmark_match.py --targets 1 --budget 300 \
  --arms inversion,full --renderer swift \
  --enumerate sw50rAmp/sw50rBright \
  --json /tmp/bench-real-bright.json
```

| arm | objective | selector accuracy | renders |
|---|---:|---:|---:|
| inversion | 1.611 | 0.4848 | 1 |
| full | 1.623 | 0.4848 | 278 |

Plugin 1.1.1, `reproducible=false`. The target has Bright on and the neutral seed
has it off; the full arm kept it off. This is not evidence that the switch is
inaudible. A direct repeated A/B with every other target parameter held fixed
prefers the correct setting, while the same A/B on the much less accurate inverted
candidate prefers the wrong setting: the wrong topology compensates for errors
elsewhere in the vector. Repeated totals for identical settings also move enough
that one render is a weak way to rank two nearby topologies.

So enumeration now works operationally, and **its accuracy benefit is not
demonstrated**. On this target it made the objective slightly worse and did not
recover the known switch. The next design question is no longer wiring; it is how
to rank discrete variants under a backend whose full objective is substantially
noisier than its 0.23 dB per-band metadata suggests. Repeating only the topology
seed is insufficient because CMA-ES also scores every continuous candidate once,
and the store currently serves an identical vector from cache instead of rendering
another sample. That needs an explicit replicated-evaluation design and budget,
not another flag around the existing one-render comparison.

### Tone King, end to end for the first time

```
python3 scripts/match_preset.py --pack toneking --template /tmp/tk_template.xml \
  --reference /tmp/tk_ref.wav --reference-mode probe --probe-di /tmp/tk_probe.wav \
  --renderer swift --no-invert --budget 200 --shortlist 2 --seed 0 --out-dir /tmp/tk_run
```

`1.320 -> 0.819` in 191 renders and 199 s, against a reference rendered through the
plugin from a known vector. The record-state write path works: each render rebuilds
the plugin's own blob through `format.structured` and the parameters reach the
sound.

Two things it exposed, neither of which is a bug in the search:

- **`--no-invert` is not optional for this pack.** `invert()` needs an amp prefix
  and Tone King has none — `amp_modules` is empty and the whole namespace is flat,
  so there is no `{amp}EQ/{amp}EQBand{n}` to fit onto. Without `--no-invert` the
  run dies with "the template does not say which amp is selected". The inversion
  stack is written for Morgan's topology, and that should be said out loud rather
  than discovered by a user.
- **The screen freezes 44 of 61 parameters.** The backend floor is doing most of
  the work here, and the run says so.

There is still no bundled Tone King template. The one used above is the plugin's
own boot state written to a file, which parses as a preset because it is one.

## 12e. What M6 built, and the paired calibration M5 still owed

`skills/match/SKILL.md` now owns "make this preset sound more like this
recording". `skills/generate/SKILL.md` fingerprints supplied audio before choosing
values, while web research still chooses the topology. The match skill classifies
the reference regime, selects the renderer and loss profile, reports the
inversion/search split and shortlist, requires `apply_spec.py --dry-run`, and ties
the user's listening verdict to a measured fingerprint delta in
`learned-tones.md`.

### A compact result contract

Every successful `match_preset.py` run now writes `summary.json` beside the spec
and HTML report. It contains the reference fingerprint and regime confidence,
renderer identity and reproducibility, inversion changes, searched and frozen
controls, every candidate's objective vector and signed per-band fingerprint
delta, and every caveat. This is the agent-facing contract; the self-contained
HTML remains the human report. The documented synthetic workflow is executed by
`tests/test_skills.py`, so M6's exit criterion does not need an installed plugin.

### The corrected paired-DI run

The invalid M5 run in §12d omitted the residual term carrying weight 0.9. The
fresh pair below was generated from one deterministic 6-second DI and one fresh
Morgan process. The target settings are committed in
`docs/m6-paired-target.json`; the input peak is 0.150 and the rendered reference
peak is 0.767.

```
mkdir -p /tmp/m6-paired
.venv/bin/python - <<'PY'
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from analysis import io
from match.renderer_au import AudioUnitRenderer
from tests import fixtures_audio as fx

root = Path('/tmp/m6-paired')
raw = fx.plucks(seconds=6.0, gap=0.9, seed=13)
di = raw / np.max(np.abs(raw)) * 0.15
sf.write(root / 'probe.wav', di, 48000, subtype='PCM_24')
spec = json.load(open('docs/m6-paired-target.json'))
settings = {(p['module'], p['key']): p['value'] for p in spec['parameters']}
with AudioUnitRenderer('morgan') as renderer:
    result = renderer.render(io.load(root / 'probe.wav').mono(), settings)
    print(renderer.metadata().as_dict())
    print('probe peak', float(np.max(np.abs(di))))
    print('reference peak', result.peak)
    assert not result.silent and result.peak < 1.0
    sf.write(root / 'reference.wav', result.audio, 48000, subtype='PCM_24')
PY

.venv/bin/python scripts/match_preset.py \
  --template samples/Example_Clean_PR12.xml \
  --reference /tmp/m6-paired/reference.wav --reference-mode paired_di \
  --probe-di /tmp/m6-paired/probe.wav --loss-profile paired-v1 \
  --pack morgan --amp sw50r --renderer swift \
  --budget 300 --shortlist 3 --seed 0 --out-dir runs/paired-corrected-001
```

Morgan 1.1.1, `reproducible=false`: the robustly ranked candidate improved the
reported distance **1.078 → 0.807** in 299 real renders. All 294 scored trials
contained `residual`; its objective moved from 2.331 on the first trial to a
minimum of 1.271. Two alignments fell below absolute correlation 0.30 and were
compared unshifted. The term behaves and supplies information, but the result is
not evidence that 0.9 is an optimal weight.

The residual figures are reproduced from that exact run with:

```
.venv/bin/python - <<'PY'
import json, sqlite3
db = sqlite3.connect('runs/paired-corrected-001/trials.sqlite3')
rows = [json.loads(row[0]) for row in db.execute(
    'select objectives_json from trials where objectives_json is not null order by trial_id')]
print(len(rows), sum('residual' in row for row in rows))
print(rows[0]['residual'], min(row['residual'] for row in rows))
PY
```

### The two supplied WAVs through the M6 workflow

Both files are source-separated stems, so these runs use confidence 0.55 and
`unpaired-v1`. The first 30 seconds hold one target fingerprint; the renderer's
cost still follows the six-second synthetic probe. These are 100-render workflow
acceptance runs, not replacements for the earlier 300-render listening candidates.

```
.venv/bin/python scripts/match_preset.py \
  --template samples/Example_Clean_PR12.xml \
  --reference 'Hotel California-lead-D major-74bpm-438hz.wav' \
  --reference-mode separated_stem --loss-profile unpaired-v1 \
  --pack morgan --amp pr12 --renderer swift --excerpt 30 \
  --budget 100 --shortlist 3 --seed 0 --out-dir runs/m6-hotel-california-wav

.venv/bin/python scripts/match_preset.py \
  --template samples/Example_Clean_PR12.xml \
  --reference 'How Long-lead-C major-140bpm-441hz.wav' \
  --reference-mode separated_stem --loss-profile unpaired-v1 \
  --pack morgan --amp pr12 --renderer swift --excerpt 30 \
  --budget 100 --shortlist 3 --seed 0 --out-dir runs/m6-how-long-wav
```

| reference | start → selected | worst at ±6 dB | searched / frozen | caveats |
|---|---:|---:|---:|---:|
| Hotel California | 2.133 → **1.287** | 1.386 | 18 / 17 | 18 |
| How Long | 2.215 → **1.424** | 1.443 | 17 / 13 | 15 |

Both are Morgan 1.1.1 and **`reproducible=false`**. Each generated a complete
`summary.json`; each winner then passed the exact `apply_spec.py --dry-run`
invocation printed by its run. Nothing was written because M6 keeps audition and
approval between preview and preset creation.

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
