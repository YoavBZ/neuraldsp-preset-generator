# Frozen Morgan model: broader processing control

> **Review 2026-10-09** ([codex-continuation-review.md](codex-continuation-review.md)): VOID, not inconclusive: invalidComponentID (-3000) came from Codex's sandbox, which cannot see AU components. The study never ran.


2026-10-09. **Independently verified INCONCLUSIVE. Closed.**

The procedure, reviewed sources and declaration were committed at `df68127`
before new input access. Both original replay stages passed. The first plugin
startup then failed before returning any audio, so no broader processing result
exists. This attempt will not be repeated or rescued by changing its path,
settings, thresholds or later stages.

## What completed

- Preflight: all 108 original scalar scores reproduced within absolute 1e-8.
- CPU baseline: twelve original model outputs reproduced byte for byte; all 36
  direct scores and the original acceptance rule reproduced.
- New clean render stage: stopped after 7.13 seconds, exit 1, during startup.
  The server reported `NSOSStatusErrorDomain -3000 invalidComponentID` and closed
  stdout before a complete ready reply. Partial reply was empty. Zero audio
  returns and zero completed render rows. The child was stopped with no recorded
  cleanup error. Failure, invalidation, partial/protocol fallback and closure
  records are retained.
- No clean scoring, changed-chain rendering or changed-chain scoring ran.

The replay controls establish reproducibility of the earlier clean-chain result.
They cannot answer whether the model handles other Morgan processing. The OS
error's cause is unestablished; execution in the default process sandbox alone
does not prove causality.

## Independent verification

A fresh verifier independently implemented the original model, preprocessing,
score and acceptance rule. It saved and read back the complete derivation and
thirteen output/coefficient NPZs before reading primary numerical results.
All **235 checks pass, with zero comparison failures**. This includes 108
original scalars, twelve byte-identical predictions, 36 direct scores, twelve
retained eight-second render-input copies and their exact original-DI suffixes,
failure contracts and source/asset stability. Maximum scalar discrepancy is
8.05e-12. No new render prediction was computed. One scientific CPU pass took
7.93 seconds.

The first verifier launch failed on a Python-version hash API before scientific
asset access. Its log remains. The first comparison had 36 reporting-only
mismatches: standalone JSON records contain an empty
`nonfinite_diagnostic_fields` wrapper that aggregated rows omit. Exact payload
checks were corrected; the initial full report/source remain, and inference and
scoring were not rerun. Blind and final scientific source prefixes agree.

## Evidence

- [Frozen procedure](di-morgan-processing-control-plan.md) and
  [fresh approval](research/di-morgan-processing-review-2026-10-09.md).
- [Verification summary](di-morgan-processing-verification.md),
  [full comparisons](di-morgan-processing-verification.json.gz),
  [independent derivation](di-morgan-processing-independent-derivation.json.gz),
  [read barrier](di-morgan-processing-independent-read-barrier.json),
  [transcript](di-morgan-processing-independent-transcript.jsonl.gz), and
  [output hashes](di-morgan-processing-independent-array-hashes.json).
- [Original blind source](research/di-morgan-processing-independent-blind.py),
  [final source](research/di-morgan-processing-independent.py), and
  [preserved first comparison](research/di-morgan-processing-comparison-attempt-01.report.json.gz).
- [Exact primary metadata/log bundle](di-morgan-processing-primary-metadata.json.gz):
  includes reached stages, retained-input identities, protocol/failure/closure
  records and later metadata-only infrastructure observations.
- [Archive manifest](di-morgan-processing-verification-archive.json): full source
  and archive SHA256/byte counts, with lossless readback checks.

Full local output is `tmp/di-morgan-processing-control-20261009/`.
Waveform/input/prediction NPZs and compiled server stay local, outside Git.
The installed component's metadata matches Morgan 1.1.1 and aumf/NMAS/NDSP;
that is not proof of startup. A sandboxed component inventory returned only a
banner. A separately approved host inventory produced no output and was
interrupted, exit 130. No inventory job remains. No cache, registry or license
state was changed.

## Next steps and limits

Prepare a separately reviewed, committed, one-time
[startup/version/shutdown check](morgan-au-startup-plan.md) in the approved host
execution context. It sends no audio or preset commands and cannot reopen this
study. Further model work needs a new bounded question supported by evidence,
including usable different-equipment pairs; no long training is justified yet.

The checks are reproducibility checks, not 235 musical examples. The twelve
performances are dependent examples from one player/guitar. Shared NumPy/SciPy/
Torch and CPU, inherited eligibility metadata, and retrospective process-access
limits apply. No live plugin identity/parameter readback or renderability was
verified. No native-transfer, processing-robustness, preset-selection, song or
product conclusion follows. The failed native panel and spent reserved final
confirmation remain closed; reserved audio/scores were not reused.

Attribution: Pedroza et al., Guitar-TECHS, CC BY 4.0,
https://zenodo.org/records/14963133.
