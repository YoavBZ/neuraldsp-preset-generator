# Synthetic DI-metric window-precision probe

**Declared: 2026-10-08, before execution.** Fresh independent design/code review
approved the current implementation; eight synthetic unit tests pass. Commit before
computation. Review: [record](research/di-domain-metric-probe-review-2026-10-08.md).

## Purpose

Attempt 1 of the [native-chain pilot](di-domain-pilot-results.md) failed its fixed
absolute 1e-8 synthetic NumPy/Torch agreement check. This separate numerical
diagnostic tests whether different Hann-window coefficient precision explains that
failure. It neither resumes attempt 1 nor evaluates a model or recording.
[Independent static review](research/di-domain-metric-failure-review-2026-10-08.md)
supports the hypothesis but has not established its numerical sufficiency.

## Fixed procedure and access

Use the existing CPU Torch environment, two threads, no gradients, bytecode writes
disabled. No audio, catalog, model/average, cached arrays, renderer or dataset path
is needed or permitted. Do not call `frozen_inputs`, the original runner CLI or a
model builder. Import only inert metric definitions and numeric libraries. Freeze
the script/tests/declaration, `learn/direc.py`, `learn/di_domain_pilot.py` and the
original failed metric JSON by committed source hashes.

Use exactly the original four float64 pairs: seed 20261008, b = normal noise of
length 144000 times 0.1; predictions b.copy(), b*0.5, roll(b,52), zeros; target b.
FFT sizes 256/512/1024/2048/4096; all padding, epsilon, reduction, Hann periodicity
and frame-hop definitions stay as in the original metric. No seed/tolerance search.

Record versions/build, CPU/device, threads, input/STFT/default/Hann dtypes. Require
the observed global default to be float32; never alter it. For each FFT save:

- default and explicit float32 Torch Hann equality;
- exact explicit Torch float32/float64 coefficient bit patterns as lossless text,
  canonical little-endian byte SHA256, and maximum coefficient differences;
- NumPy's float64 formula and its final float32 cast comparison with Torch float32.

For each pair perform these fixed interventions:

1. Reproduce original NumPy and unchanged `direc.mrstft` scores. Require each score
   within absolute 1e-12 of the committed failed artifact and the same per-row 1e-8
   pass/fail pattern. If reproduction changes, stop the causal claim.
2. NumPy STFT/reductions using the EXACT exported Torch float32 window, promoted
   to float64, versus unchanged `direc.mrstft`. Require aggregate error ≤1e-8.
3. A local Torch reference with explicit supplied windows must EXACTLY equal the
   unchanged function under Torch float32 windows. Record per-FFT spectral
   convergence, log L1 and total. Require NumPy/shared-Torch-window differences
   ≤1e-8 for EACH term and aggregate, avoiding cancellation as an explanation.
4. Feed the SAME NumPy float64 coefficients to both local FFT implementations;
   require each component and aggregate difference ≤1e-8. Separately report the
   NumPy-formula-versus-explicit-Torch-float64 comparison as a diagnostic. Require
   this local NumPy baseline to agree with unchanged `P.mrstft_numpy` at absolute
   1e-12, so the intervention cannot silently substitute a different baseline.
5. Require the signed NumPy score change from replacing its float64 window with
   Torch float32 coefficients to explain the original Torch-minus-NumPy discrepancy
   within absolute 1e-8, for every pair. No global dtype changes or monkeypatches.

All required checks must pass to support the coefficient hypothesis at this score
resolution. Failure is inconclusive and triggers review, not a relaxed tolerance
or pilot run. Success does not establish bitwise FFT identity, neural transfer,
preset-ranking improvement or authorization for long training.

## Outputs and review

`learn/di_domain_metric_probe.py --out tmp/di-domain-metric-probe-20261008-v1`
creates that folder exclusively. Save windows/provenance/result JSON and explicit
failure evidence on errors; use a distinct log, never overwrite prior attempts.
The fixed workload is four signal pairs and five FFT sizes; use a fifteen-minute
cooperative budget checked between cases. Record the live session in the monitor.

Independent result verification must recompute component/aggregate comparisons,
coefficient-bit hashes and gates from saved text before acting. Only after a
successful reviewed probe may a separately declared pilot attempt 2 preserve the
actual frozen float32 coefficients in NumPy scoring. The original pilot declaration,
failure/output and all final-confirmation code/assets remain unchanged.
