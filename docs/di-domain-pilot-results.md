# Native-chain DI pilot: stopped at synthetic metric preflight

2026-10-08. **No native audio, matched renders or neural inference was run.**
The reviewed procedure was committed as `8e5a91b` before execution. Its mandatory
first synthetic check failed and correctly prevented the recording experiment.

## What happened

The CPU Torch environment ran the four declared float64 synthetic comparisons.
Target against itself gave zero in both implementations. The other absolute
NumPy/Torch differences were **1.1973287473e-8**, **3.1511558363e-8** and
**2.7614964537e-8**, above the fixed **1e-8** tolerance. Execution exited 1.
Torch was 2.8.0 and NumPy 2.0.2.

This is a failed numerical preflight, **not a failed neural transfer result**. No
recording-quality, recoverability, Morgan or native-model screen result exists.
All 105 targeted synthetic tests had passed in the project environment; the two
Torch parity tests were skipped there. The separate runtime check exposed a
difference those checks had not resolved.

The likely cause under independent investigation is window precision: the existing
`direc.mrstft` creates a Hann window without an explicit dtype, while the NumPy
replica constructs it in float64. That is a hypothesis until independently checked;
the small difference alone does not justify relaxing the failed tolerance.

## Evidence and continuation

- [Original metric output](di-domain-pilot-metric.json).
- Original exclusive run folder: `tmp/di-domain-pilot-20261008/metric/`, including
  result, provenance and failure JSON.
- Original log: `tmp/di-domain-pilot-metric-20261008.log`.
- No retry, tolerance change, audio access, training or reserved-data use followed.

An independent agent is inspecting source and the failed artifacts before proposing
one small synthetic probe/correction. Any changed procedure requires its own declared,
reviewed and committed version before another attempt. Preserve this failure and the
original declaration. No long training is justified by this preflight outcome.
