# Development cross-amp diagnostic: independently verified

Computed 2026-10-08 after fresh independent review and declaration/code commit
`20483ba`. All 17 synthetic checks passed in the main and independent runs before
execution. The score-only analysis completed successfully. Independent recomputation
agrees on all 20,864 scalar fields with zero discrepancies (maximum rounding
difference 1.11e-16), including constants, choices, fallbacks, comparisons, coverage,
gates, provenance and commit-before-run timing. The archived report exactly matches
production. Evidence: [complete output](set3-cross-amp-diagnostic.json) and
[independent verification](set3-cross-amp-diagnostic-verification.json).

## Findings

None of the three declared routing conditions meets its criterion under both band
sets: cross-amp known-DI headroom, pooled-net improvement, or headroom for choosing
among fixed per-amp net picks. No amp-selector training follows this diagnostic.

| Comparison | Paired band-median effect, recording / union | Raw wins / losses / ties, recording | Union |
|---|---:|---:|---:|
| pooled known DI vs SW50R known DI | 0.000000 / 0.000000 | 11 / 3 / 19 | 11 / 3 / 19 |
| pooled net vs SW50R net | 0.000000 / 0.000000 | 7 / 9 / 17 | 7 / 8 / 18 |
| pooled net vs global constant | −0.136230 / −0.040460 | 16 / 14 / 3 | 14 / 14 / 5 |
| B-hindsight best fixed net pick vs SW50R net | 0.000000 / 0.000000 | 15 / 0 / 18 | 14 / 0 / 19 |

Negative log ratios mean smaller measured distance. All required policy comparisons
have 33 positive pairs; the global factory-only/inclusive constants happen to agree.
Pooled-net joint wins over SW50R and both constants are 0.083333/0.053030. Its actual
chosen amps are AC20/PR12/SW50R = 9/8/16 under recording, 11/4/18 under union. Varying
amp choice alone does not establish better choices.

The known-DI pooled control remains materially better than the global constant
(−0.264428/−0.314090), and pooled net is worse than pooled known-DI choice
(+0.253266/+0.091741). These are pipeline contrasts, not isolated waveform errors.
They do not license a larger waveform training run from this diagnostic alone.

All three standalone net choices have raw-scorable B values for every part, so the
fixed-pick hindsight comparison is complete. The full 111-candidate hindsight menu
has a refused candidate and is only best among scorable candidates. Hindsight is
unavailable at prediction time and cannot establish learnability.

The shared fallback is used on one part per net policy; its actual selected amp is
recorded. Labels such as SW50R net describe the normal policy, not a promise that a
global fallback chooses SW50R. Historical no-fallback comparisons retain one missing
part and remain descriptive.

## Next

Close this pooled-menu route under its declared rules. Do not train an amp selector,
tune pooled scores or expand knobs after this result. This procedure did not meet
the declared development improvement criteria; it does not show that every possible
cross-amp method fails.

The next mechanism to investigate is transfer from plugin-generated training audio
to recorded guitar rigs. Audit the existing training sources, open-licensed paired
recordings, losses and normalization before declaring a small controlled transfer
pilot. Do not start another long training run based on an untested domain-gap story.

The judge remains listening-validated only for clear clean-to-crunch PR12 differences.
Changed methods still need heavier-tone listening and fresh reserved confirmation.
The spent reserved split stays excluded from training, tuning and repeated tests.
