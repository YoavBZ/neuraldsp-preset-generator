# Native-chain frozen-model pilot — attempt 2

**Declared: 2026-10-08, before execution.** Fresh independent Curie review
approved the exact scientific procedure and implementation; 142 synthetic tests
pass, two optional Torch tests skip in the helper. Commit before computation.
[Review record](research/di-domain-pilot-v2-review-2026-10-08.md). This declaration
and review link are administrative updates to the approved draft, with no
scientific or implementation change.

## Change and limits

Attempt 1 stopped before audio at its synthetic metric comparison. The separately
declared [precision probe](di-domain-metric-probe-results.md), committed `6dee304`
and independently verified in `b60964f`, establishes that the different Hann
coefficient precision explains that synthetic failure. This attempt uses the exact
saved CPU Torch float32 coefficients, promoted losslessly for NumPy's float64 FFT.
It does not raise the **absolute 1e-8** comparison tolerance or change `direc.py`.
Casting the NumPy Hann formula to float32 is not an equivalent correction.

The [original procedure](di-domain-pilot-plan.md) supplies every scientific choice:
the exact twelve P2 takes, frozen fold2 checkpoint and average, fixed PR12 preset+R,
all alignment/QC/FIR rules, calibration and score intervals, 52-sample timing,
normalization, all arms and success/control gates. No take replacement, threshold
change, tuning, training or reserved-data access. The original procedure, input
manifest and failed run remain unchanged; its implementation is archived at
`8e5a91b`. This declaration supersedes only its execution/precision mechanism.

Original inputs are referenced by SHA256 in [attempt-2 inputs](di-domain-pilot-v2-inputs.json).
The already verified coefficient-bit archive is checked at compressed-byte,
decompressed-text and per-window byte levels. Require all five FFT sizes, exact
dtype/length, valid unsigned bits and finite values. No reconstruction or fallback.
An optional explicit-window argument in the shared utilities propagates to every
primary and low-band score, including FIR, oracle and both Morgan arms. Omission
retains the first implementation's NumPy behavior; attempt 2 always supplies it.

## Preconditions and stages

Use `learn/run_di_domain_pilot_v2.py STAGE --run tmp/di-domain-pilot-20261008-attempt2`.
Create the run and each stage exclusively. Pin committed declarations, manifests,
dependency code/tests and the coefficient archive. Fail on dirty/changed sources.
Metric preflights may read only code, declarations, window bits and original path
manifest bytes, not catalog/model/average bytes or any recording. Imports are inert.

1. **metric**, existing CPU Torch interpreter: require unchanged global float32
   default and bit-identical live default Torch Hann against every saved window.
   Same seed 20261008 and four 144000-sample float64 signals as the original probe:
   identity, half gain, roll52, zero. Compare corrected NumPy with unchanged
   `direc.mrstft`; all absolute errors ≤1e-8 and identity <1e-6. Save every score,
   signal byte hash and versions. No dtype mutation or model inference.
2. **numpy**, actual project helper environment: regenerate exactly those four
   cases, require byte-identical signal hashes, and independently replay corrected
   NumPy scores against saved CPU Torch references at the same gates. This verifies
   the actual native-stage scoring environment, rather than assuming its NumPy
   version matches the Torch environment. No catalog/assets/recording access yet.
3. **native**, helper: only after both preflights pass with identical source pins,
   validate original catalog selection and model/average hashes, then run original
   bounded native QC, baseline/FIR/oracle scores. Record all rejected takes. Complete
   valid coverage requires all twelve; no replacements. Asset identities recorded.
4. **render**, helper: only after valid native coverage, repeatability canary and
   twelve matched Morgan renders under the original procedure, one reused renderer,
   finally-close and preserve host logs. Failures stop progression.
5. **infer**, existing CPU Torch interpreter: only after complete valid native and
   render reports, 24 frozen CPU inferences, score every arm with the same corrected
   table. Compare asset identities with native; no training or checkpoint selection.

Explicit runtime selection: CPU Torch stages require prefix
`/Users/yoavbz/ndsp-presets/tools/learn-venv`; helper stages require the repo `.venv`.
Use the approved helper for supported operations; no embedded interpreter switching.
Separate per-stage logs, exclusive folders, failure JSON and progress retained.
Cooperative fifteen-minute stage budget remains; monitor progress and halt stuck
processes while preserving artifacts. It is not a hard interrupt inside a library.

## Decision and verification

Original native screen: median net improvement ≥10% versus better wet/flatref,
≥9/12 strict wins, both content-group medians positive. Controls: all twelve valid,
all identity scores <1e-6, Morgan net median improvement ≥10%, FIR native raw-lowband
median improvement ≥10%. Keep original inclusive-boundary roundoff treatment.
Failed native QC prevents rendering/inference; a completed score does not imply
successful recovery. Failed control makes the transfer diagnosis inconclusive.
No outcome authorizes long training or a shipping claim.

Meaningful synthetic tests and fresh independent design/code review must approve
the exact implementation before this is declared and committed. After execution,
fresh independent recomputation must verify coverage, preprocessing, numerical
scores and gates before any result drives the next experiment. For QC failure,
independently recompute calibration/QC from the same bounded twelve excerpts; do
not silently alter rejection rules or rerun a revised study. Preserve rejected
evidence, input hashes and logs. Update result/roadmap/index/DI plan/learn README.
P2 is already catalogued development material from one player and one clean
bass-amp/microphone/room chain, not pristine held-out or multi-guitar validation.

Logs: `tmp/di-domain-pilot-attempt2-{metric,numpy,native,render,infer}.log`.
No old run/log is overwritten. No expensive training, installs or downloads needed.
