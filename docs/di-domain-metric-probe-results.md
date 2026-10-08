# Synthetic metric-window probe

2026-10-08. **Passes; independently recomputed with zero mismatches.**
Declaration/code/review committed `6dee304` before execution. The fixed synthetic
probe completed with exit 0 in the existing CPU Torch environment. No recording,
catalog, model/average asset, neural inference, rendering or training was accessed.

All four cases reproduced the original failed NumPy/Torch comparison. Giving the
independent FFT implementations the same coefficients passed every declared
aggregate and per-resolution component check at absolute **1e-8**. The explicit
Torch float32-window reference exactly matched unchanged `direc.mrstft`; the local
NumPy float64 baseline agreed with the original NumPy scorer within **1e-12**.
The signed window intervention accounted for each original score discrepancy at
the declared resolution. The global Torch dtype remained float32 throughout.

Fresh-context Parfit completed independent recomputation after an account usage
interruption. It derived all numerical terms before opening saved case/result scores.
All 23,808 coefficient entries, 328 raw metric values, 28 case gates and 20 exact
frozen-Torch per-FFT checks agree. Maximum saved-value drift is 2.00e-15; maximum
shared-Torch-window component error is 7.55e-15. All seven source pins match the
declared commit. The original failure pattern reproduces.

This supports the coefficient-precision explanation for these synthetic cases in
this CPU environment. Use the actual Torch float32 coefficients: casting the NumPy
formula to float32 does not reproduce them. It concerns scoring only and says
nothing about neural transfer accuracy or preset improvement. Input identity was
reconstructed from the declared seed/source; original signal-array hashes were not
saved. Artifact timestamps support ordering but are not tamper-proof attestation.

## Evidence

- [Full result](di-domain-metric-probe.json).
- [Source/environment provenance](di-domain-metric-probe-provenance.json).
- [Independent verification](di-domain-metric-probe-verification.json), with its
  [independent implementation](research/di-domain-metric-probe-independent-2026-10-08.py).
- Lossless coefficient-bit archive: `di-domain-metric-probe-windows.json.gz`.
- Original folder: `tmp/di-domain-metric-probe-20261008-v1/`, including separate
  case records, windows, provenance and result.
- Original log: `tmp/di-domain-metric-probe-20261008-v1.log`.
- Attempt 1 remains [failed before audio](di-domain-pilot-results.md), unchanged.

The successful independent verification supports proposing attempt 2 with the
actual frozen Torch float32 window coefficients and the original 1e-8 tolerance.
All recording/model scientific choices and downstream controls remain subject to
a separate reviewed and committed declaration. No recording test or training has
started, and no reserved data was used.
