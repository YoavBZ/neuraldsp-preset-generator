# Set 3 held-out confirmation: DRAFT (not declared, not run)

Drafted 2026-10-08 after the development result ([di-recovery-set3-results.md](di-recovery-set3-results.md)).
**It becomes a declaration only when the user approves it and it is committed with the
`declared` line below filled in.** No held-out audio is read before then.

## Why

On set 3's development parts, choosing through the rebuilt DI beat template+R and the
stand-in by large margins. Against a constant driven preset the result depended on the
constant's definition, which had not been declared. This test fixes every choice in
advance and spends set 3's held-out bands once, as `validation-set3.md` provides.

## What runs

- **Parts:** set 3's held-out parts, 27 parts in 6 bands (`learn/set3.py`
  `parts("held_out")`). The amp track is the input. This confirmation does not read
  held-out mixes or stems; song-mix performance needs a separate declaration.
- **Amps:** SW50R (primary) and PR12 (secondary), each with its own menu of factory
  presets plus template+R. AC20 is not tested, since it failed on development.
- **Network:** the set-3 network (`models-set3/fold2.pt`) as it is, with no retraining.
  It has heard no set-3 band.
- **Procedure:** choose on half A through the rebuilt DI at lag −52. Score on half B
  under the average-guitar measure, at each part's waveform lag less 52. Lags are never
  re-measured. A sensitivity analysis substitutes the already declared onset lag for
  the four held-out parts whose onset check disagrees (`validation-set3.md`), then
  subtracts 52. Network picks and constants stay frozen; only evaluation changes.
  If either analysis fails a gate, that amp is not confirmed. A change in verdict is
  reported as not robust. The three development disagreements do not enter this test.
- **The constants:** independently for each amp and band-set, choose the factory
  preset with R having the smallest median *raw* half-A measure distance over **all
  33 development parts**. Template+R is not eligible. This follows K1's precedent in
  `research/kill_tests.py`. Exact ties use lexicographically sorted preset IDs.
  The four choices and menu settings hashes are frozen before any held-out audio is
  read. No leave-band-out is needed. The recording-selected constant is the fallback
  candidate for that amp; the union-selected constant is used for union evaluation.
  Missing, undefined, nonfinite or negative factory scores stop the freeze; zero is
  valid for raw-distance selection. Different candidates cannot use different parts.

## Frozen inputs and execution checks

`learn/set3_confirmation.py prepare` builds a manifest from development distances,
split metadata, checkpoint and average-balance files, and preset settings. It reads
no held-out audio. Preparation leaves `approved` false. After user approval, commit
the completed declaration and manifest before rendering anything held out.

The manifest pins the checkpoint, fold-2 average, validation declaration, development
distances, menu settings, and tracked computation sources and pack configuration by
SHA-256. It also records and verifies the Python and numerical-library versions,
libsndfile, renderer settings, Swift version, and installed Audio Unit bundle identity
and file hashes. Preparation, rendering and scoring use the same CPU torch environment.
The held-out harness validates
them before reading audio. It uses a separate output directory and explicit worker
configuration, so development caches cannot be reused by accident. Missing files,
incomplete panels and invalid manifests are execution errors, not exclusions. Repair
only under the frozen procedure, retaining failed-run logs. No retraining, menu
changes, stopping based on outcomes or alternative constants are allowed.
Each attempt has an explicit pending, failed or completed status; an old passing
verdict must never remain current after a failed attempt. Previous outputs are kept
as history.

The implementation and its synthetic tests receive an independent review before the
manifest is frozen. Each result receives a separate independent numerical check.

## Gates (per amp, both band sets, under both lag analyses)

Numeric effects are the median across six bands of each band's median part log
ratio. The paired p-value enumerates all 64 sign flips of the six paired band
medians, using absolute sum as the statistic (`kill_tests.py`). Gates use unrounded
values. The joint win share is the mean across bands of wins in that band divided by
its original declared part count. Ties are not wins.

1. **Against template+R:** band median ≤ log 0.9.
2. **Against the constant, paired:** band median of log(network / constant) ≤ log 0.95,
   and a band sign-flip p < 0.1. With 6 bands, the smallest attainable two-sided p is
   0.03.
3. **Closer than both template+R and the constant:** joint win share strictly > 0.5.
4. **Refusals:** if no valid network candidate can be selected, or evaluation of the
   selected preset, template or constant cannot yield finite log ratios, that amp /
   band-set cell cannot pass. The affected part has zero wins and keeps its original
   denominator. Available-case numeric summaries are descriptive only. Refusals of
   unselected candidates do not by themselves prevent a pass.

- **A pass on SW50R** confirms preset selection on isolated amp tracks. It qualifies
  this path for further product work; it does not establish performance on song mixes.
- **PR12** is reported as secondary.
- **If SW50R fails,** the learned method does not ship. The recording-selected constant
  remains the baseline candidate. Product use still needs a declared song-only path
  and a listening check on heavier tones.

## Limits

- 6 held-out bands is low statistical power: a real 10% effect may not reach p < 0.1.
- V.M.GY is 11 of the 27 parts, which the band weighting handles.
- Crunch against high gain is not calibrated.
- A pass under this measure needs a heavier-tone listening check before shipping:
  the existing check covers one listener and clear clean-PR12 differences.
- Hashes do not make the reused plugin instance sample-exact. Its state history and
  operating-system or hardware behavior remain reproducibility limits; retain run
  order and execution logs, and investigate a contradictory recheck explicitly.

## Preparation review, 2026-10-08

An independent design review found ambiguity in constant selection, missing values,
refusal handling, weighting and timing sensitivity. The definitions above resolve
those findings while this remains an unapproved draft. No held-out audio or outcome
was used for these changes.

A separate code reviewer then found two blockers: failed reruns could leave a stale
passing verdict, and the frozen inputs omitted transitive renderer sources. Both are
fixed. The reviewer approved the final integration and independently ran the 79 new
synthetic checks. The broader relevant cohort passed 111 tests, including the existing
split/leakage and judge checks. These tests validate preparation and bookkeeping, not
model accuracy. No actual confirmation manifest or constant choices have been frozen;
no held-out audio has been opened. User approval remains pending.

**declared:** _(user approval, date, commit)_
