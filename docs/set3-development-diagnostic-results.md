# Set 3 development diagnostic: independently verified

Computed 2026-10-08 after committing the reviewed declaration/code/menu inventory at
`7c65d9e`. This is reused development data, not a new confirmation. Independent
recomputation agrees on all 14,067 compared scalar fields, with no discrepancies
(maximum rounding difference 1.11e-16). It used a separate standard-library
implementation without importing the production diagnostic and completed its
estimates before opening the production result.

Evidence: [complete output](set3-development-diagnostic.json) and
[independent verification](set3-development-diagnostic-verification.json).

## Execution

- 33 development parts, 11 bands; SW50R primary, PR12/AC20 diagnostic only.
- Existing development scores only. No audio, inference, rendering or training used.
- All required menus match the separately prepared factory-ID inventory across
  both band sets: 45 SW50R, 35 PR12, 31 AC20 candidates.
- The default output path already existed; the first attempt refused before reading
  scores. That artifact was not opened or used. Its log is preserved at
  `tmp/set3-development-diagnostic-run.log`.
- Successful run used a new path, `tmp/set3-development-diagnostic-20261008.json`,
  with log `tmp/set3-development-diagnostic-run-2.log`, exit 0. No data or rules changed.

## What the diagnostic finds

The known average-balanced DI can choose better than the declared leave-band-out
factory constant and the fairness control allowing template+R on all three amps,
under both band sets. The fairness control chooses the same constants here.

| Bands | Amp | Known-DI vs constant log effect | Known-DI joint wins | Known-DI vs rebuilt log effect | Rebuilt comparisons |
|---|---|---:|---:|---:|---|
| recording | SW50R | −0.277981 | 0.886364 | 0.000000 | 32/33, descriptive |
| union | SW50R | −0.297855 | 0.795455 | −0.063209 | 32/33, descriptive |
| recording | PR12 | −0.113069 | 0.893939 | −0.061962 | 32/33, descriptive |
| union | PR12 | −0.183274 | 0.833333 | −0.161953 | 32/33, descriptive |
| recording | AC20 | −0.127666 | 0.712121 | −0.172499 | 32/33, descriptive |
| union | AC20 | −0.114282 | 0.742424 | −0.142905 | 32/33, descriptive |

Negative log ratios mean smaller measured distance. These are paired medians of
band medians, not subtraction of separately summarized methods. Joint wins retain
all original part denominators and weight bands equally. Known-DI comparisons have
all 33 parts and no required refusal. Rebuilt selection has no valid candidate on
`cambridge-colour-me-red-elecgtr03` for any amp/band-set cell, so its ratios are
available-case descriptions and cannot pass the complete pipeline-gap heuristic.
There are no zero-log failures in these required comparisons.

The exploratory sign-flip values for known-DI versus constant are 0.001953/0.003906
on SW50R, 0.000977/0.001953 on PR12, and 0.003906/0.001953 on AC20 (recording/union).
They meet the declared routing heuristic; overlapping constant-fitting data means
these values are not calibrated inference. This does not reverse the failed reserved
confirmation or establish future generalization.

On SW50R, true-versus-rebuilt has median zero under recording bands despite many
different picks. This supplies no complete, across-band-set argument that more DI
training will help. PR12/AC20 have larger descriptive gaps but the same missing part.
The contrast also changes scoring masks, alignment and input level, so it does not
isolate waveform recovery.

Half-B hindsight minima are only best-scorable candidates on SW50R, because some
candidate B scores are refused; they are not full-menu bounds. PR12/AC20 have full
B coverage. Hindsight remains descriptive and unavailable for product selection.

## Next step

Follow the declared refusal-first branch: the
[activity-proxy diagnostic](set3-mask-diagnostic-plan.md) swaps only the chooser's
activity-proxy input, allowing its downstream effects on activity, offsets, spectral
support and centering, on a fixed development panel. Reuse existing audio;
no new rendering or long training. Its known-DI mask is a control, and its
isolated-reference heuristic has untested transfer to mixes or separated stems. Design and code
must pass independent review and be committed before reading audio for that check.

All reserved sets remain excluded from tuning and training. Any changed model needs
fresh reserved data and heavier-tone listening before product use.
