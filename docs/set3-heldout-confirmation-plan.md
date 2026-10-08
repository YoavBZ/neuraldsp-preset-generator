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
  `parts("held_out")`). The amp track is the input; the stems are reported only.
- **Amps:** SW50R (primary) and PR12 (secondary), each with its own menu of factory
  presets plus template+R. AC20 is not tested, since it failed on development.
- **Network:** the set-3 network (`models-set3/fold2.pt`) as it is, with no retraining.
  It has heard no set-3 band.
- **Procedure:** choose on half A through the rebuilt DI at lag −52. Score on half B
  under the average-guitar measure, at each part's waveform lag less 52. Lags are never
  re-measured; the onset-lag sensitivity analysis covers the 7 flagged parts
  (`validation-set3.md`).
- **The constant (declared here):** for each amp, the single preset with the best median
  *raw* half-A measure distance over **all 33 development parts**. This follows K1's
  precedent in `research/kill_tests.py`. It is fixed before any held-out audio is read.
  The development data chooses it, so no leave-band-out is needed.

## Gates (per amp, both band sets; parts weighted by band, 1/n per band)

1. **Against template+R:** band median ≤ log 0.9.
2. **Against the constant, paired:** band median of log(network / constant) ≤ log 0.95,
   and a band sign-flip p < 0.1. With 6 bands, the smallest attainable two-sided p is
   0.03.
3. **Closer than both template+R and the constant** on more than half the band-weighted
   parts.
4. **Refusals** count as losses.

- **A pass on SW50R** confirms rebuilding the DI for SW50R as the first product path.
- **PR12** is reported as secondary.
- **If SW50R fails,** the method does not ship. The constant preset ships as the
  baseline.

## Limits

- 6 held-out bands is low statistical power: a real 10% effect may not reach p < 0.1.
- V.M.GY is 11 of the 27 parts, which the band weighting handles.
- Crunch against high gain is not calibrated.

**declared:** _(user approval, date, commit)_
