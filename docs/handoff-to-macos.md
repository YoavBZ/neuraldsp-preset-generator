# Handoff: what to run on a Mac with the plugins installed

> **This was written before M5 and is kept as the brief it was.** M5 has since been
> done and several of the statements below are now false — `--renderer swift`
> exists, `packs/morgan/eq_basis.json` exists, and Tone King renders. What actually
> happened, including where this document turned out to be wrong, is
> `docs/tone-matching-plan.md` §12d. Read this for the reasoning and that for the
> results.


Written at the end of the session that built **M4** (reference-guided tone matching)
and reviewed it three times. Everything through M4 is done and merged; every number in
the repository was measured against a **Python approximation** of the plugin, not the
plugin. Closing that gap is **M5**, and it cannot be done anywhere but your machine.

Read `docs/tone-matching-plan.md` for the design. This file is only about what to run,
in what order, and what should happen.

---

## 0. What you have and what it is worth

| | Status |
|---|---|
| `show.py`, `apply_spec.py`, `bootstrap_pack.py`, `probe.py` | Work on a bare clone, no dependencies. |
| `analysis/` — fingerprint, compare, features | Done (M1). Needs `[analysis]`. |
| `analysis/refchain.py` — synthetic amp chain | Done (M2). **Mirrors Morgan's topology, models none of its DSP.** |
| `match/invert.py` — closed-form inversions | Done (M3). EQ curve, filter corners, delay, reverb, tremolo, level. |
| `match/{search,store,report,benchmark}.py` | Done (M4). Screen → enumerate → CMA-ES → ±6 dB re-rank. |
| `scripts/match_preset.py`, `scripts/benchmark_match.py` | Done (M4). |
| **`--renderer swift` / `--renderer pedalboard`** | **Refuse by name. This is M5's job.** |
| `packs/morgan/eq_basis.json`, `drive_curve.json` | **Do not exist.** Every EQ fit is textbook filter shapes. |
| Tone King end-to-end | **Never run against the plugin.** Its whole gating path is untested in anger. |

The single sentence that matters: **the 50-target benchmark says the full pipeline beats
inversion-alone on 49 of 49 targets, and it says that about a Python approximation.** The
honest gap between that and the real plugin is the thing M5 exists to write down.

---

## 1. Set up, and confirm the ground you are standing on

```bash
git clone <this repo> && cd neuraldsp-preset-generator
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[analysis,match,dev,host]'
pytest -q                     # expect 742 passed, 15 skipped, ~12 min
```

**All 15 skips will still skip on your machine, and that is by construction.** Run
`pytest -q -rs` to see them. Eleven are documentation-command checks in
`tests/test_skills.py`, and `skip_reason()` decides them by **substring match on the
command text** — `swiftc`, `/tmp/au_probe`, anything touching the user's preset folder —
with no platform or capability check at all. So the two that say "needs the licensed
Audio Unit installed on macOS" skip on macOS with the Audio Unit installed. The other
four are content-driven: a sample preset from the wrong pack, a pack with no recipes, a
render with no sustained monophonic segment, symlinks.

**That is a small job worth doing early:** make those two skips conditional on capability
rather than on spelling, so your machine actually verifies the documented plugin commands.
It is the only place in the suite that could.

The larger fact behind it: **no test in this repository touches the plugin.** Not one. The
whole suite runs green on a Linux box with nothing installed, which is what made M1–M4
possible and is exactly the blind spot you are here to close. `audit_manifest.py` *is* the
plugin check, and it is a script rather than a test precisely because CI can never run it.
Do not read a green `pytest` as evidence about the plugin.

Confirm both plugins instantiate. An unlicensed or unavailable Audio Unit normally fails
with `-1`:

```bash
auval -v aumf NMAS NDSP        # Morgan Amps Suite
auval -v aumf TKI2 NDSP        # Tone King Imperial MKII
```

---

## 2. Re-audit both manifests (an hour, and do it first)

Every fact in `packs/*/manifest.json` was measured against the plugin at some point, and
a plugin update can invalidate any of it. The audit is the cheapest thing in this
document and it gates everything else.

```bash
python3 scripts/audit_manifest.py --pack morgan
python3 scripts/audit_manifest.py --pack toneking
```

It rebuilds the Swift helper, reads the parameter table, maps stored keys and checks the
declared ranges, members and switch directions. **It exits nonzero when a declaration
disagrees or cannot be checked.** Expect it to be green; if it is not, `manifest.json` is
wrong and nothing downstream means anything.

Two things `docs/measuring-against-the-plugin.md` warns about, both of which have already
cost this project real bugs, so check the audit's own wording rather than only its exit
code:

- **A display is not a unit.** Both plugins show a pan out of 50; Morgan *stores* −50..50
  and Tone King stores −1..1. Reading the range off the display once gave Tone King's pan
  a range fifty times too large.
- **"20 of 21 declared members produced a label" is not a pass.** Writing the index a
  control already holds moves nothing, so the baseline member goes unread. That blind
  spot hid three wrong `*EQHpf` maximums through a full audit.

---

## 3. Land the real backend (M5's core)

### 3.1 What you are implementing

One class, in a new `match/renderer_au.py`, satisfying the protocol in
`match/renderer.py`. Read that file first — its module docstring encodes two M0 findings
that constrain the design.

You must provide:

| Member | Contract |
|---|---|
| `renderer_id` | `"swift"` or `"pedalboard"`. Goes in the cache key. |
| `metadata()` | `RenderMetadata`. **`reproducible=False`** for a reused instance, and `band_noise_db=REUSED_INSTANCE_BAND_NOISE_DB` (0.23) unless you measure otherwise. `plugin_version` must be the real version — results from different versions are never merged. |
| `_render(di, settings)` | Audio shaped `(frames, channels)`. Return `None` never; raise `RenderError` if nothing came back. **Silence is a legitimate return value**, not an error. |
| `parameter_specs()` | The `ParamSpec`s this backend can be driven with. `match/space.py` builds the whole search space from this. |

`render()` itself is shared and already hashes inputs consistently — do not override it.

Then wire it into `scripts/match_preset.py`'s `_renderer()`, which currently refuses both
names with a message pointing at M5.

### 3.2 Use the batched server, not one process per render

Already written and measured:

```bash
swiftc -swift-version 5 -O scripts/au_render_server.swift -o /tmp/au_render_server
printf '%s\n' \
  '{"out":"/tmp/a.wav","edits":[{"module":"sw50rAmp","key":"sw50rBright","value":"true"}],"selectAmp":2,"gateOff":true,"amplitude":0.25}' \
  '{"quit":true}' | /tmp/au_render_server aumf NMAS NDSP
```

| | renders/s | per render |
|---|---|---|
| `au_render`, one process each | 0.50 | 2030 ms |
| `au_render_server`, 20 in one process | 2.67 | 375 ms |
| steady state after the first | 3.4 | 291 ms |
| four servers in parallel (6 performance cores) | 8.8 | — |

`instantiate` alone is 1250 ms — 62% of a one-shot render. **Pass `--settle 0`**: the
200 ms settle after writing state was a guess, and the same state at 0/5/10/25/50/100/
200/400 ms produces byte-identical output, for a switch *and* for a mic change that
reloads an impulse response. (Measured on Morgan's XML state path only — re-check it for
Tone King.)

Both harnesses take `--input` / `"input"`, a 48 kHz mono or stereo file rendered in place
of the generated excitation. A search needs that: measuring a control wants noise or a
sine, but a preset can only be judged against a guitar.

### 3.3 Budget arithmetic before you start a search

At 3.4 renders/s a 300-render match is **~90 seconds** plus the ~5 renders made outside
the search (the template, the inversion's probe, one per shortlisted candidate). Four
servers in parallel makes the 50-target benchmark — 15,000 renders — about **half an
hour** rather than the 95 minutes it took synthetically.

`--budget`'s help gives the fixed-cost formula. On Morgan, roughly 70 renders go before
anything is searched, and a budget that cannot afford one whole CMA-ES generation now
says so, first among the caveats, and names the number to raise to.

### 3.4 The two findings the protocol already encodes

**A cached render is not the same render.** Two renders of identical parameters from one
plugin instance differ by about −17 dB relative to the signal — in both hosts, through
`reset`, reallocation and warm-up alike. Only a fresh process is bit-exact. So the cache
exists to save time, not to assert equivalence, and **anything committed as a measured
fact must come from a backend that reports `reproducible=True`.**

**This has a direct consequence for the search.** `match/search.py`'s sensitivity screen
raises its floor to `metadata().band_noise_db` — see `_backend_floor`. With the synthetic
renderer that is 0.0, so **the entire raise has never executed outside a unit test.** On
your backend it becomes live at 0.23 and will freeze parameters the synthetic runs
searched. That is correct behaviour, and it is also the least-exercised path in M4.
Watch the screen's caveats on your first real run.

---

## 4. The two calibrations, per pack

Neither script exists. Both are M5 deliverables, and both produce committed JSON that a
schema test validates without needing the plugin.

### 4.1 `scripts/measure_eq_basis.py` → `packs/<pack>/eq_basis.json`

**Why it matters most.** Every EQ fit in `match/invert.py` currently uses textbook filter
shapes, and every run says so:

> nobody has measured this amp's equaliser yet (`packs/morgan/eq_basis.json` does not
> exist), so the band gains were worked out from textbook filter shapes. The real bands
> overlap differently, so expect these to be a couple of dB out and to spill into their
> neighbours.

That caveat is the largest known error in the whole pipeline. Measuring it removes it.

**Method.** For each EQ band, render the amp with that band at a known gain and everything
else flat, and take the third-octave difference against flat. That gives the band's real
response shape and its overlap with its neighbours. `match/invert.py`'s `bell_basis()` and
`fit_graphic_eq()` consume it. Two renders per band per amp — cheap at 291 ms each.

### 4.2 `scripts/measure_drive_curve.py` → `packs/<pack>/drive_curve.json`

THD across the volume control at **3–4 input levels**, extending the existing PR12
measurement into a full surface. The existing spot measurement:

```bash
swiftc -swift-version 5 -O scripts/au_render.swift -o /tmp/au_render
/tmp/au_render aumf NMAS NDSP pr12Amp/pr12Volume 0.6 /tmp/v60.wav 0.05 sine:222.65625
python3 scripts/spectrum_diff.py --thd 222.65625 /tmp/v60.wav
```

**The test frequency must sit on an analysis-bin centre** — 4096-point window at 48 kHz
is 11.71875 Hz per bin. `spectrum_diff.py` refuses an off-centre fundamental and names
the nearest valid one. Check the rendered peak too, so output clipping is not recorded as
plugin distortion.

For PR12, ~5% THD is around 66% volume at the reference input and around 28% when the
input is three times stronger. **Breakup position is input-dependent**, which is exactly
why the ±6 dB robustness re-rank exists — and see §6 for what that stage is currently
mostly measuring.

### 4.3 `tests/test_calibration_schema.py`

Validates the committed JSON with no plugin. Write it alongside the measurements, not
after: it is what lets CI keep checking the files once they are in the tree.

---

## 5. Re-run the benchmark for real — the number that matters

This is M5's exit criterion.

```bash
# Synthetic, for a baseline on your machine (should reproduce the committed numbers)
python3 scripts/benchmark_match.py --targets 50 --budget 300 \
  --json /tmp/bench-synthetic.json

# The real thing, once --renderer swift exists
python3 scripts/benchmark_match.py --targets 50 --budget 300 \
  --renderer swift --json docs/m5-benchmark-morgan.json
```

`benchmark_match.py` has no `--renderer` flag yet — it hardcodes `SyntheticRenderer()`.
Adding it is part of 3.1.

The committed synthetic result, to compare against — `docs/m4-benchmark-50.json` holds
all 147 rows:

| arm | mean objective | median | best | worst | param MAE | selector | renders |
|---|---|---|---|---|---|---|---|
| recipe | 3.039 | 2.533 | 0.661 | 8.716 | 0.247 | 0.643 | 0 |
| inversion | 1.514 | 1.309 | 0.418 | 6.231 | 0.257 | 0.658 | 49 |
| full | **0.641** | **0.461** | **0.084** | 6.089 | 0.266 | 0.658 | 14,375 |

**Expect the real numbers to be worse, and do not tune until they are written down.**
Two things to hold onto when they are:

- **Parameter MAE getting worse across the arms is not a bug.** 0.247 → 0.257 → 0.266.
  The plugin's controls are not identifiable from its output: a different volume with a
  compensating EQ curve sounds nearly identical, so a search that closes the objective
  fourfold has no reason to close the parameter error. `verdict()` states in its own
  output that MAE is deliberately not part of the gate.
- **The failure rate is reported separately and gated at 10%.** The synthetic run had
  zero failures. A real backend will have some — a silent render, an instantiate that
  did not come back. They must stay visible.

Also do the paired ground-truth run the plan asks for: render a known preset through
Morgan, discard the parameters, attempt recovery. That is the honest test, and unlike the
random-vector benchmark its targets are tones a person would actually dial.

---

## 6. Things that are known-shaky and want your machine to settle them

Ranked by how much they would change a conclusion.

1. **`_backend_floor` has never run for real.** §3.4. The screen's floor raise is live
   only on a backend that declares band noise. Least-exercised path in M4.

2. **The ±6 dB re-rank is mostly measuring loudness, not tone.** Measured per candidate
   and offset: the `level` dimension accounts for **35–96%** of the change in the total,
   while `timbre` — the term that would show breakup — moves by about 0.001. Turning the
   input up makes the render louder and the level term counts that. A caveat now names
   the percentage. On the real plugin, where breakup genuinely depends on input level,
   check whether `timbre` starts moving. **If it does not, the stage needs rethinking**,
   and `drive_curve.json` is the evidence that would tell you.

3. **The topology stage never runs.** `topologies()` is written and tested, and no caller
   passes `switches=` or `selectors=` — so the cab, the mic, the amp and every on/off
   switch are whatever the template had. The `inversion` and `full` arms therefore score
   *identical* selector accuracy in every run. A run says so in a caveat now. Adding
   `--enumerate` is the obvious M5-adjacent job, and it is a product of whole inner
   searches: five two-state switches is 32 of them.

4. **Tone King has never been run end to end.** Its preset format is a binary `PARAM`
   record, not XML; `probe_state.py` handles it and `au_render` takes `--state`. Its
   gating logic in `match/space.py` — the flat namespace, where the gate chain nests the
   opposite way from Morgan's — was written against the manifest and unit tests only.
   Its switches are binary doubles `0`/`1` where Morgan uses the strings `false`/`true`
   (`switch_encoding` in the pack). Expect this to be the roughest part.

5. **Tone King renders silence from the bare CLI helpers.** It did so "for months", and
   that turned out to be a property of the bare instantiation rather than a failure to
   render. `RenderResult.silent` is how a caller asks, and the standing rule is that
   **silence is not evidence about a control either way**. If your backend gets silence
   from Tone King, that is a hosting problem, not a DSP finding — do not publish audible
   conclusions from it.

6. **`spatial` reads 0.000 on every synthetic run** — both sides are dual-mono — and it
   carries 8% of the weight, so the headline is 8% a guaranteed zero. The report says so
   with the arithmetic. On the real plugin with two cabs panned apart it should start
   discriminating. If it still reads zero, something is wrong upstream.

7. **`paired-v1` and `--reference-mode paired_di` have never met a real DI.** This is the
   highest-confidence path in the whole design — regime weight 1.0, and the only profile
   that weights `residual` (0.9) because with a paired DI you can compare waveforms
   sample-for-sample rather than statistically. Nothing has exercised it against real
   audio, because it needs the reference *and* its own DI, which means reamping. Your
   machine is the first place that is possible:

   ```bash
   python3 scripts/match_preset.py --template <preset>.xml \
     --reference reamped-through-the-real-rig.wav --reference-mode paired_di \
     --probe-di the-same-di.wav --loss-profile paired-v1 \
     --renderer swift --budget 300 --out-dir runs/paired-001
   ```

   If `residual` behaves — 0.9 of the weight — this is a substantially better objective
   than the unpaired one every committed number rests on. If it does not, say so, because
   the profile's weights are data and nobody has calibrated them against a real pair.

---

## 7. Working agreements this repository holds to

Worth knowing before you change anything, because they are load-bearing and they were
each learned the hard way.

- **A measurement that could not be made says so.** Absence is never zero. Every
  optional field carries a confidence; `None` and `0.0` are different answers.
- **Silence is not evidence about a control.** Neither for it nor against it.
- **A figure with no invocation behind it is an assertion wearing a decimal point.** Every
  number in the docs must be reproducible from a command in the docs. This was violated
  three times and caught three times, most recently by a table that argued *for* the
  current design and could not be reproduced at all.
- **A fix aimed at a named symptom closes that branch and leaves its twin open.** This has
  happened in every review round. When you fix something, go looking for the other
  caller, the other branch, the symmetric case.
- **The bare clone must keep working.** `dependencies = []` is a promise. Do not import
  `analysis` — let alone numpy — from `scripts/_cli.py`, `show.py`, `apply_spec.py`,
  `probe.py` or `bootstrap_pack.py`. `tests/test_no_dependencies.py` blocks both numpy
  *and* `analysis` itself and runs the scripts in a subprocess. CI installs the package,
  which hides this class of break, so trust the test rather than CI.
- **Mutation testing is the standard.** A test that cannot fail proves nothing. When you
  add a behaviour, break it deliberately and check something goes red.
- **Never commit a number from a backend that reports `reproducible=False`** without
  saying so next to it.

---

## 8. A first afternoon, concretely

```bash
# 1. ground truth
pip install -e '.[analysis,match,dev,host]' && pytest -q
auval -v aumf NMAS NDSP && auval -v aumf TKI2 NDSP
python3 scripts/audit_manifest.py --pack morgan
python3 scripts/audit_manifest.py --pack toneking

# 2. see the synthetic pipeline work, so you know what "working" looks like
python3 -c "
import sys; sys.path.insert(0, '.')
from analysis import refchain
from tests import fixtures_audio as fx
di = fx.plucks(seconds=6.0, gap=0.9, seed=13)
fx.write_wav('/tmp/ref.wav', refchain.render(di, {
    'sw50rAmp/sw50rVolume': 82.0, 'sw50rAmp/sw50rTreble': 20.0,
    'sw50rAmp/sw50rBass': 75.0}))
fx.write_wav('/tmp/probe.wav', di)"

python3 scripts/match_preset.py --template samples/Example_Clean_PR12.xml \
  --reference /tmp/ref.wav --reference-mode probe --probe-di /tmp/probe.wav \
  --amp sw50r --budget 300 --shortlist 3 --seed 0 --out-dir /tmp/run
# expect: 1.719 -> 0.256 in 298 renders, 10 caveats, 18 searched / 6 frozen
open /tmp/run/report.html

# 3. confirm the winner is a real preset (add --force to re-run over an existing --out)
python3 scripts/apply_spec.py --template samples/Example_Clean_PR12.xml \
  --spec /tmp/run/match-1.json --out /tmp/matched.xml
python3 scripts/show.py /tmp/matched.xml --text
# expect: "Example Clean PR12 match 1   [Morgan Amps Suite]"

# 4. time a real render, so the budget arithmetic is yours rather than mine
swiftc -swift-version 5 -O scripts/au_render_server.swift -o /tmp/au_render_server
# ... then build match/renderer_au.py against it
```

If step 2's numbers differ from the ones above, say so before doing anything else —
the pipeline is deterministic and it reproduces bit-for-bit on this machine, so a
difference is a finding.

---

## 9. Where the detail lives

| Question | File |
|---|---|
| Why the design is shaped this way | `docs/tone-matching-plan.md` §1–§9 |
| What each milestone actually built, and where it departed from the plan | same, §12 / §12a / §12b / §12c |
| Every review finding and its fix | same, "What a … review of M… found" sections |
| How to measure anything against the plugin | `docs/measuring-against-the-plugin.md` |
| The fingerprint schema | `docs/tone-matching-plan.md` §6.1, `analysis/fingerprint.py` |
| The nine objective dimensions and their weights | §6.2, `analysis/loss_profiles.json` |
| The render cache and store schema | §6.3, §6.4, `match/store.py` |
| What a backend must implement | `match/renderer.py` |
| Morgan's and Tone King's musical behaviour | `packs/*/tone.md` |

The plan's §12 sections are worth more than the design sections. They are where the
project records what turned out to be false, and every one of them was written after a
review found something the code did that the documentation denied.
