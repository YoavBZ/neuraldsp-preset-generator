# Frozen calibration correctness control

**Declared: 2026-10-08, before execution.** Fresh independent review approved
the exact scientific body, source and tests. 258 synthetic tests pass; two optional
Torch checks skip in the helper environment. Commit before real-array access.
[Review and exact snapshot hashes](research/di-alignment-control-review-2026-10-08.md).
Only this administrative section changed after approval; the scientific body and
source/test bytes remain identical to the reviewed snapshot.

<!-- alignment-approval
{"status":"DECLARED","fresh_independent_review":true,"review_sha256":"e311891fc954c383b7f746001b47818ffbb92472b4accbf8733c6333c77cba02","source_sha256":"dc0ea39b69095bd7406ed7d6908e31ee04b0a9a23e115995880bf4b9b6e62b77","test_sha256":"b543a668c35594f2900e8b74a30ad6268345afa7bddf502000584adf9281c45b","design_sha256":"f43a29402976aa99469f90a745e315ff724da5524d2c59054c09f8f7db060f49","mean_interpretation":"uncentered-input-exact-formula"}
alignment-approval -->

The approval block is main's attestation, not an automated proof of reviewer
independence. The runner verifies the archived review, source/test/scientific-body
hashes and every dependency byte against HEAD. Any scientific or input change
requires fresh review of the changed snapshot and a separate declaration.

## Frozen design

### Purpose and limits

Independent correctness study of the frozen `P.calibrate` confidence/rejections
prompted by the already closed native QC screen in
`docs/di-domain-pilot-v2-results.md`. That screen stays closed. No threshold tuning,
take substitution, native study rescue or inference about the separate flatref
outcome. Neither a positive nor negative result revises either earlier experiment.

All twelve original canonical-control **raw** six-second prepared DIs are required:
the `di` member of each `tmp/di-morgan-control-20261008/prepare/SLUG.npz`.
Do not read its target/render_di members, raw audio, microphone audio, native
arrays, catalog, average, checkpoint, rendered wet arrays or predictions. Original
manifests supply identity/path metadata only. Importing the diagnostic reads no
assets. Source, plans, reviews and hash metadata may be inspected before review;
real arrays and numerical results must remain unread until review and declaration.

Use `C.code_inputs()` for the existing **35 source pins** without calling
`C.assets()`, `R.frozen_inputs()` or coefficient decoding. Additional committed pins
are the new source/test/plan, existing flatref 36-artifact hash manifest, archived
prepare report, archived independent verification, original independent verifier
source and this study's fresh review. The archived preparation must have complete
ordered twelve-take identity coverage, valid QC and finite nonnegative primary
oracles strictly below 1e-6. Independent verification must be successful with no
failed checks, matching inherited source/verifier hashes, and complete independently
verified preparation QC/oracles. Require byte identity of the original saved prepare
report and its archive, and the original prepare provenance's 35 pins. No primary
model/flatref outcome is consulted for this study's gate.

Parse the existing committed `docs/di-morgan-flatref-inputs.sha256` as exactly the
36 unique original slugs crossed with prepare/render/infer. Select exactly twelve
prepare entries, reject unknown/duplicate/missing names, then hash **only those
twelve NPZs** before any array load and recheck before each load. Reject symlinked
prepare paths. Record the observed file hashes and loaded DI float64 hashes.

### Constructed pairs

At 48 kHz, transform the **complete six seconds first**, before cropping, finite
shifting or padding. Do not center, normalize or EQ the source:

1. `identity`: x.
2. `polarity`: -x.
3. `lowpass`: `scipy.signal.butter(4, 1200, btype="lowpass", fs=48000,
   output="sos")`, then `sosfiltfilt(..., padtype="odd", padlen=27)`; zero phase.
4. `tanh`: `tanh(3*x/std(x))*std(x)/3` using NumPy population std on all six
   seconds, with the original uncentered x as the input.

Main clarified before review that “original mean retained” means no explicit
demeaning or mean restoration. The exact formula uses uncentered x and does not
generally preserve the arithmetic output mean. This clarification changes no
formula or scientific design. The declaration's `mean_interpretation` records it.

For each arm impose integer lag -128, 0 and +128: **12 × 4 × 3 = 144** positive
cases. Truth is the exact imposed lag and polarity -1 only in the polarity arm.
Set the catalog prior to that truth lag. This is an **optimistic correct-prior
diagnostic**, not a validation of native catalog priors.

Take the first `4*48000 + 2*512 = 193024` samples of the raw and transformed
six-second DIs. These contain both guards entirely within the saved six seconds;
the calibration origin is sample 512. Construct a buffer of `10*48000 + 2*512`
samples from each compact prefix and zeros after that prefix. Form wet by finite
slicing the transformed prefix so `wet[n+lag] = transformed_di[n]` wherever both
prefix indices exist; uncovered samples are zero. No circular wrap. The 512-sample
guards exceed all imposed shifts, so padding cannot enter the calibration interval.
No extra six-second scoring segment is analyzed. P sees only its unchanged
four-second slices. The six-second transform intentionally has context outside
those slices (both zero-phase filtering and global std). There is no pristine
calibration/evaluation split claim and **no scored interval in this diagnostic**.
Test isolation at P's buffer boundary, not independence of the full-six-second
transform from later samples. The frozen P implementation also ignores the guards
when estimating calibration; they provide the declared construction margin.

Add **12 negative cases**: each DI paired with the NEXT different take within its
declared six-take content group, cycling in original manifest order independently
for chords and scales. Identity transform, zero imposed lag, nominal catalog zero,
same prefix/padding. They are different performances, not silence. Record both
take identities. There is no known matching lag/polarity for a negative; truth
fields and associated correctness errors are null rather than invented zero truth.

### Frozen estimates and gates

Call existing `P._gcc_phat` on full four seconds and each two-second half. Use the
existing `P.bandpass` and **exact** Pearson definition from `P.calibrate`: separately
filter the calibration slices, crop at full-estimate lag, remove each cropped mean,
then dot product divided by the norm product (zero denominator gives zero).
Record all three raw lag/sharpness/separation estimates and correlation/denominator.

Record every original predicate and its outcome even when actual P rejects first:
all three sharpness values >10; all three separation values >1.2; absolute full
estimate minus catalog <=16; max minus min of all three lags <=8; finite absolute
correlation >=0.5. Preserve exact strict/inclusive boundaries with no rounding
allowance. Record catalog error, lag range, all derived Calibration fields, every
positive estimate's signed truth error and derived polarity correctness.

Call actual unchanged `P.calibrate` on the same buffers/prior. Save acceptance,
all returned fields, or first exception type/message. Verify exact reproduction of
accept/reject, first rejection message/order and all returned fields on acceptance.
This recorder shares the frozen primitives; it checks decision composition, not
an independent reimplementation of FFT/correlation. Synthetic known-truth tests
exercise those primitives. Nonfinite estimates remain located in saved evidence
(null plus field paths) and make disposition INCONCLUSIVE.

### Disposition

Require exactly all 156 declared case identities/pairs/arms/shifts/truths. Invalid
coverage, nonfinite/invalid diagnostics or actual-P consistency mismatch is
**INCONCLUSIVE**, with precedence over scientific failure.

Valid **PASS** requires all 36 identity and all 36 polarity cases accepted with
lag error <=1 sample and correct polarity; no accepted positive across all 144
has lag error >1 sample or wrong polarity; all 12 mismatch negatives are rejected.
A complete valid violation is **FAIL**. Lowpass/tanh acceptance rates are diagnostic:
their rejections alone cannot fail the gate because the method may properly decline
processing. Accepted mistakes in those arms do fail the gate.

Report accepted/rejected totals and rates by arm and content (including all-content
totals), every wrong accepted positive and full details of every accepted mismatch.
A PASS establishes neither native alignment nor model transfer. Do not tune the
thresholds, fix a prior after seeing the estimate, select easier cases, reopen the
native study or use this as a model/product success claim.

### Execution and retained evidence

Only after main's fresh review, declaration and commit:

```sh
/Users/yoavbz/.codex/bin/neuraldsp-safe python-file learn/di_alignment_control.py --out tmp/di-alignment-control-20261008
```

Only this CLI and output path are allowed. Require actual helper repo `.venv`
prefix. No interpreter switching, subprocess computation, workers, installs,
network, rendering, inference, training or scoring. Git reads in the runtime guard
only establish committed bytes/revision; this implementation task does not run git.
Reject path aliases/symlinks and every existing output directory, including empty
ones. All output lives exclusively in that directory. Guard/prefix/directory
refusals occur before directory creation and raise on stderr; capture that command's
stdout/stderr in main's execution harness, without writing another study directory.

Save provenance (revision, all source pins, twelve file hashes, case declaration,
Python/prefix/package versions, attribution), inputs (DI hashes), incremental
`progress.jsonl` and stdout, and `result.json` with all case evidence and disposition.
Keep compact constructed-prefix hashes, length/origin/dtype/zero-tail recipe and
transformed-six-second hashes; full mostly-zero buffers are reconstructible and
are not saved. Exceptions during a case are retained as invalid case evidence;
continue remaining cases unless the budget expires. Run-level errors save
`failure.json` with INCONCLUSIVE and preserve progress. A cooperative 15-minute
budget starts before the guard and is checked during loading and before/after
every case. This is not a hard interrupt; main monitors a stuck library call.

Synthetic tests use noise, tones, analytic edge impulses and mocks only. Cover
known positive/negative lags and polarity, full-transform ordering, no cyclic wrap,
four-second P isolation, all cases/cyclic mismatches, exact rejection boundaries
and order, predicate/actual-P parity including early rejection, invalid data and
coverage, commit/prerequisite-before-assets, exact twelve-file subset and output
exclusivity, failure/progress and budget retention. Run through the project helper
pytest without workers or pytest's repository cache. Do not execute this diagnostic
on actual arrays as part of implementation or testing. Main owns post-run fresh
independent verification before interpreting a result.

The serial synthetic verification command explicitly overrides the repository's
default worker settings:

```sh
/Users/yoavbz/.codex/bin/neuraldsp-safe pytest -q -o addopts= -p no:cacheprovider tests/test_di_alignment_control.py
```

Pedroza et al., Guitar-TECHS, CC BY 4.0, https://zenodo.org/records/14963133.
