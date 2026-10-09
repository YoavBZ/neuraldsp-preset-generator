# DI-domain pilot: independent static metric-failure review

Review date: 2026-10-08. Inspected repository HEAD
`8e5a91ba7fb30d5e972818bdca8163d710197d0b`, branch
`codex/song-model-continuation`. This is a proposal for review before any new
numerical experiment. No probe, test suite, inference, rendering or numerical
reproduction was run during this review. The only file written by this review is
this report. No Git mutations, package changes, downloads or child agents were used.

## Finding and disposition

The first declared pilot **failed its mandatory synthetic metric gate**. Keep that
outcome permanently. The strongest causal hypothesis is a coefficient-precision
mismatch: the frozen Torch implementation creates its periodic Hann window in the
global default floating dtype, normally float32, even for float64 input signals;
the independent NumPy implementation creates its periodic Hann in float64.

Static evidence establishes a mismatch in the two implementations' construction
rules under the normal Torch default. It does **not** yet establish that this
mismatch explains every observed error. The failed artifact does not record the
actual default dtype, window values or intermediate STFT terms. A small, separately
declared synthetic intervention is needed before choosing a correction. Do not
increase the failed tolerance, rerun the original folder, or edit `learn/direc.py`.

Prefer preserving the frozen implementation's window semantics in a newly declared
pilot by supplying its actual CPU float32 coefficients to the independent NumPy
FFT/reductions. A float64-window reference is also useful diagnostically, but would
be a numerical variant of the frozen metric and must be named as such if selected
for a subsequent pilot.

## Evidence inspected

The original `metric/result.json` records Torch 2.8.0 and NumPy 2.0.2:

| Synthetic prediction, target = seeded noise b | NumPy | Torch | Absolute error |
| --- | ---: | ---: | ---: |
| b.copy() | 0 | 0 | 0 |
| b * 0.5 | 1.1931456121136257 | 1.1931456240869132 | 1.1973287472599736e-08 |
| np.roll(b, 52) | 0.42241531000708454 | 0.4224152784955262 | 3.15115583626735e-08 |
| np.zeros_like(b) | 15.197900270957183 | 15.197900298572147 | 2.7614964537292508e-08 |

`learn/run_di_domain_pilot.py:190–210` constructs b with
`np.random.default_rng(20261008).normal(size=3 * P.SR) * 0.1`, converts it using
`torch.from_numpy`, and passes each prediction/target as one batch. The comparison
is absolute error <=1e-8 for **every** row. Three rows fail; self-comparison passes.
The log and `metric/failure.json` record `ValueError: synthetic metric parity failed`.
The inspected run root contains only the metric stage directory.

`learn/direc.py:182–191` calls:

```python
w = torch.hann_window(n, device=a.device)
A = torch.stft(a, n, n // 4, window=w, return_complex=True).abs() + 1e-6
B = torch.stft(b, n, n // 4, window=w, return_complex=True).abs() + 1e-6
```

No `dtype=a.dtype` is supplied. The relevant inspected modules do not set the
global default dtype. The installed environment identified in the live monitor is
`~/ndsp-presets/tools/learn-venv`; its `torch/version.py` reports 2.8.0, CPU build,
Torch source revision `a1cb3cc05d46d198467bebbb6e8fba50a325d4e7`.

Read-only installed-source evidence under that environment's
`lib/python3.9/site-packages/torch/`:

- `_torch_docs.py:12409–12451`: Hann has `periodic=True`, `dtype=None`, and uses
  the common factory dtype documentation. Periodic length n corresponds to the
  length n+1 symmetric window with the final sample removed.
- `__init__.py:1267–1275`: Torch initializes its default floating dtype to float32.
- `functional.py:557–570,718–741`: STFT defaults are centered, reflect padded and
  unnormalized. The wrapper reflect-pads n//2 samples on each side and passes the
  supplied window to the native STFT operation.

`learn/di_domain_pilot.py:436–463` converts signals to float64 and constructs:

```python
window = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / n)
```

It uses the same five FFT sizes, quarter-window hops, centered reflect padding,
one-sided unnormalized FFT, additive magnitude epsilon, target-norm epsilon,
natural-log magnitude L1 and average across resolutions. NumPy lays out frames
and frequency bins in a different axis order from Torch, but its reductions cover
all entries, so that axis order alone does not change the mathematical loss.

The mismatched window values are a credible cause of errors around 1e-8: promoting
float32 coefficients during multiplication by a float64 signal preserves their
prior rounding. Log magnitudes can make small coefficient changes visible. The
identity case cannot distinguish windows because both sides use the same window
within each implementation. Opposite error signs across cases do not contradict
this mechanism. None of these observations proves causal sufficiency.

FFT/library arithmetic and reduction order remain possible residual causes.
Periodic-versus-symmetric windows, padding, epsilon placement, normalization and
batch aggregation do not show a static semantic disagreement in these paths.

### What was and was not accessed by the first attempt

The failure precedes native audio preparation, rendering and neural inference.
However, `main()` calls `frozen_inputs()` **before** dispatching `metric()`.
`frozen_inputs()` hashes model and average files and reads the catalog. Therefore
the first metric invocation did read model/average bytes for hashes; it did not
load those arrays or instantiate/load the neural model for inference. Do not
describe it as zero asset-byte access.

This review read only source, text metadata/logs and the static failure JSON files.
It did not open the model, average array, catalog, native sources or reserved
scores. It did not invoke the runner or its provenance function.

### Why prior checks did not establish runtime parity

The review record reports 105 passed, 2 skipped in the helper environment; the
skipped tests are exactly the Torch parity cases. They are not evidence of parity.
`tests/test_di_domain_pilot.py:529–538` also uses both absolute and relative
`pytest.approx` tolerance, whereas the stage uses absolute tolerance alone. Its
seed, lengths and pairs differ from the stage. A revised test should assert the
declared absolute comparison directly for the exact stage cases.

Independent DC, epsilon and reflected-impulse fixtures are valuable checks of the
mathematical float64-window metric, but do not establish equivalence to Torch's
default window coefficients.

## Proposed separate synthetic probe — not executed or authorized by this report

Declare the following fixed protocol before execution, with exclusive output
`tmp/di-domain-metric-probe-20261008-v1/` and a new append-only log. If the path
already exists, stop and declare another path; do not overwrite it. Pin the probe,
review and inspected source hashes. This is a numerical implementation diagnostic,
not a resumed pilot or a domain-transfer result.

Use the existing CPU Torch 2.8.0 / NumPy 2.0.2 environment, two Torch threads, no
gradients, seed 20261008 and precisely the four original 144000-sample float64
pairs. No normalization or signal substitution. Do not call the runner CLI,
`frozen_inputs()`, catalog selection, any audio/array reader, model builder/loader
or renderer. Import only the inert utility/metric definitions and required numeric
libraries. Set bytecode writing off. The probe may read code/library files and
write its own synthetic text results; no dataset or model path is needed.

1. Record Python/package/build versions, CPU/device, thread count, global default
   dtype, actual default Hann dtype, input dtype and STFT output dtype. Require
   the observed default to be float32 for testing this specific explanation; stop
   for review if it is not. Do not alter the global default dtype.
2. For n = 256, 512, 1024, 2048, 4096, construct three windows: the existing NumPy
   formula W_np64, explicit CPU `torch.hann_window(n, periodic=True,
   dtype=torch.float32)` W_t32, and explicit float64 Torch Hann W_t64. Save all
   coefficients losslessly as text plus canonical little-endian byte hashes,
   dtypes and maximum pairwise coefficient differences. Require default Torch
   Hann and explicit W_t32 to be bit-identical. Report, rather than assume, whether
   `W_np64.astype(np.float32)` equals W_t32: a final cast need not reproduce
   float32 trigonometry or operation order.
3. Reproduce the original unchanged NumPy-versus-frozen-`direc.mrstft` comparison.
   Retain all results even if reproduction differs. If the original pass/fail
   pattern or maximum discrepancy materially changes, stop and investigate the
   environment rather than treating the hypothesis as established.
4. In probe-local code only, allow the NumPy STFT path to accept explicit windows.
   Compare NumPy using W_t32 promoted exactly to float64 against unchanged
   `direc.mrstft`, on every original pair. Require finite results and absolute
   error <=1e-8 for each of the four aggregate scores. Also record spectral
   convergence, log L1 and total for each FFT size; do not rely on aggregate
   cancellation as the explanation.
5. Use a probe-local Torch reference identical in operations to `direc.mrstft`
   except for explicit window arguments. First require its W_t32 results to equal
   the unchanged function's results exactly in the same CPU process. Then compare
   both FFT implementations using the **same W_np64**; require aggregate absolute
   error <=1e-8 on each original pair. This isolates FFT/reduction differences
   from the window construction. Separately compare the existing NumPy metric
   against that reference with W_t64 and report coefficient and score differences.
6. For every pair, retain original discrepancy, shared-W_t32 residual, and the
   score change caused by replacing W_np64 with W_t32 in NumPy. Check that the
   latter accounts for the original signed discrepancy within 1e-8. Save all
   intermediate summaries even on failure; use no searches over seeds, thresholds
   or implementations to obtain a pass.

A successful probe supports the window as the explanation at the declared score
resolution, not bitwise identity of the FFT libraries. If sharing windows leaves
any original pair outside 1e-8, do not patch or start a pilot: inspect framing,
promotion, FFT magnitudes and reductions under a further declaration.

The helper's `python-file` and `pytest` use the project environment, which lacks
Torch. Once tracked, pure NumPy checks can use those helper operations. The CPU
Torch probe needs a separately approved, explicit invocation of the existing
external interpreter; do not hide interpreter switching inside a helper command.
No command is run or preapproved by this report.

## Safe correction after a successful, reviewed probe

Recommended semantics: preserve the actual frozen CPU Torch float32 periodic Hann
coefficients while retaining float64 signals and independent NumPy FFT/reductions.

The smallest reliable change in numerical behavior is replacing **only the window
coefficients** in the pilot replica. A proposed implementation is an optional,
validated `windows` mapping for `mrstft_numpy`, passed through every pilot primary
and low-band scoring call. Preserve the existing default float64 formula for the
independent analytic fixtures. Supply the new pilot's five windows from one frozen
synthetic text table produced by the reviewed probe, so helper/native scoring does
not acquire a Torch runtime dependency. This is 7936 synthetic coefficients, not
audio or a learned artifact. Store float32 bit patterns losslessly and promote
them to float64; validate sizes, finiteness, dtypes, all five keys and table hash.
Fail closed on a missing or different table. Pin the table and implementation in
the new declaration/provenance. Do not silently fall back to another window.

All score-producing paths must receive the same windows, including native wet,
flatref, oracle, FIR low-band, Morgan baseline and both neural outputs. The metric
preflight must check their table against the live explicit/default Torch windows
bitwise and compare the actual NumPy scoring entry point against the unchanged
`direc.mrstft`. A shared window validates independent transforms/reductions, not
independent coefficient generation; keep separate analytic Hann/epsilon/padding
fixtures and disclose that distinction.

Do not simply cast the current float64 NumPy Hann to float32 without evidence of
coefficient equality. Do not globally set Torch's default dtype or monkeypatch the
frozen function. Either can silently change metric semantics; a global float64
default can also affect subsequent model construction. Adding `dtype=a.dtype` to
`direc.py` would change the authoritative implementation and is outside this task.

An alternative with fewer plumbing changes is to keep NumPy scoring and explicitly
declare a float64-window mathematical MR-STFT, checked against a local explicit
float64 Torch reference. That is a new numerical metric variant, not exact parity
with historical `direc.mrstft`. It requires a new declaration and cannot repair
the original failed attempt. Prefer the coefficient-preserving correction when
exact frozen-function semantics are the requirement.

### Proposed verification before a new pilot

- Keep the original four cases and absolute <=1e-8 gate. Check the exact stage
  entry point, not only a duplicated test implementation. No relative tolerance.
- Run the existing seed-101 mono and batch parity fixtures in the actual CPU Torch
  environment with shared W_t32; for float64 use the declared absolute <=1e-8
  gate. Retain the separately labeled existing float32 tolerance test; do not use
  it to justify the float64 gate. Compare float32 inputs consistently and label
  the NumPy promotion behavior explicitly.
- Retain independent float64-formula analytic tests for periodic Hann DC, both
  epsilon placements and centered reflected-edge impulses at their existing
  tolerances. Do not reinterpret their idealized windows as frozen float32 ones.
- Add table validation/refusal and propagation checks: a missing window, altered
  coefficient/hash or partial mapping must fail before scoring; every arm must
  receive the pinned mapping. Add a negative test that a synthetic parity failure
  blocks subsequent stages, plus exclusive-directory/provenance checks. Use only
  synthetic/mocked inputs, never asset hashing or reads of real arrays/models.
- After changing only pilot code/tests and declaring/pinning the table, run the
  targeted synthetic suites via `neuraldsp-safe pytest` where applicable, and the
  explicit CPU Torch interpreter for Torch checks. Record passes and skips
  separately. Stop on any failure; perform fresh independent review of the exact
  change and retained probe evidence before declaring execution.

## Proposed new execution declaration

Create a separately dated revision/declaration rather than silently replacing the
first procedure. It should state:

> Attempt 1, commit 8e5a91ba7fb30d5e972818bdca8163d710197d0b, failed the mandatory
> synthetic NumPy/Torch absolute-error gate before native audio processing,
> rendering or inference. The original failure folder and log are immutable. A
> separately declared synthetic diagnostic [insert actual retained probe location,
> hashes and reviewed outcome] established [insert measured finding]. Attempt 2
> changes only the declared pilot metric-window handling and supporting validation;
> the frozen `learn/direc.py`, model, average, input manifest and all other scientific
> choices remain pinned. The absolute metric gate remains <=1e-8 on the same four
> synthetic pairs. All downstream controls and screens remain as originally
> declared. This is a new development attempt, not a continuation or pass of
> attempt 1, and supplies no new final-confirmation result.

Freeze reviewed code, table, tests and the new declaration before execution. Use
an exclusive new folder such as `tmp/di-domain-pilot-20261008-attempt2/`, with
separate append-only logs and a recorded session. The runner currently pins HEAD
and rejects changed procedure hashes between stages: respect that mechanism by
starting a new run, never copying a passing metric into attempt 1 or resuming it.
Do not run the native stage until the new metric prerequisite passes and execution
is authorized. Preserve every failure and independently recompute eventual
decision-driving scores/gates under the new frozen coefficient definition.

The concurrent archival/document work can link this review and the preserved
attempt-1 record. This report does not edit those documents or authorize numeric
work, data access, Git changes or changes to final-confirmation artifacts.

## Static evidence hashes

SHA256 values measured only for inspected code and static failure files:

| File | SHA256 |
| --- | --- |
| learn/direc.py | 43b698ba69fc97d91b547e9948b9b0611dec7b01453eef43609e365a85885969 |
| learn/di_domain_pilot.py | af4358ee3717d9b828a1875262489047a896e953531cc2ca814750344d570eb3 |
| learn/run_di_domain_pilot.py | 7641ae0607b2505a79fe18c2cc36cfe544da8ce6e21a9910e804ebcfdaf5f75c |
| tmp/di-domain-pilot-20261008/metric/result.json | 02f53d2521fe268c28b05ff4b00b806d8199028f5c5ed3764970fff5327513b7 |
| tmp/di-domain-pilot-20261008/metric/provenance.json | f25bcc5c104c6cc70f3782f2a53e0ec635767b341fd95853e14f7bcdb5c05a58 |
| tmp/di-domain-pilot-20261008/metric/failure.json | 50b4e5a314bfc43add037aac527edff509f8b5bd296541b18693a31fdc21e3ed |
| tmp/di-domain-pilot-metric-20261008.log | 41abb6e9750975801e6fc5235624ca928421a0cd34012c83b9d0759826fa5528 |

The three code hashes match the recorded first-attempt provenance. This review
has not verified any current model/average/source bytes and makes no such claim.
