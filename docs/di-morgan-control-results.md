# Known-DI Morgan control

2026-10-08. **PASS, independently verified with zero mismatches.**
Procedure, implementation and review committed `a5b9605` before computation.

All twelve original P2 dry takes passed raw-DI QC and canonical-target oracles.
Both runtime metric preflights passed at the unchanged absolute 1e-8 tolerance.
All twelve fixed PR12+R renders completed in 22.72 seconds using one reused host;
the first-render repeatability check passed and renderer metadata agreed.
Twelve frozen CPU predictions completed in 3.79 seconds, without training.

Against using the latency-corrected Morgan output as DI, the verified primary score
improves on **12/12 takes**, with median relative improvement **72.18%**. Chord and
scale medians are 69.46% and 72.56%. The original standalone Morgan-control bar is
10%; group medians/wins are reported diagnostics, not extra control gates.
Every individual score and improvement is retained in the full result.

This positive control concerns one fixed training-compatible chain on
these twelve development performances. It **does not establish native microphone
transfer, learned recovery beyond simple spectrum correction, preset ranking,
driven/multi-guitar coverage or shipping readiness**. Its baseline is processed
audio directly, not the existing `flatref` tone-corrected stand-in. The raw-DI
low-band diagnostic targets a different quantity from the canonical primary and
must not be silently substituted for it.

The [native pairing pilot](di-domain-pilot-v2-results.md) remains closed and
inconclusive. None of its rules was weakened; this separate control reads no
microphone audio and uses all twelve DIs rather than the three native-valid pairs.

## Evidence

- [Full prediction scores and screen](di-morgan-control.json).
- [Independent numerical verification](di-morgan-control-verification.json),
  [report](research/di-morgan-control-verification-2026-10-08.md) and
  [implementation](research/di-morgan-control-independent-2026-10-08.py).
- [Raw-DI preparation and QC](di-morgan-control-prepare.json).
- [Render metadata](di-morgan-control-render.json) and
  [repeatability control](di-morgan-control-repeatability.json).
- [CPU metric preflight](di-morgan-control-metric.json) and
  [actual helper NumPy replay](di-morgan-control-numpy.json).
- [Declared procedure](di-morgan-control-plan.md) and
  [fresh design/code review, including corrected missing pin](research/di-morgan-control-review-2026-10-08.md).
- Original artifacts: `tmp/di-morgan-control-20261008/`; logs:
  `tmp/di-morgan-control-{metric,numpy,prepare,render,infer}.log`.

Fresh-context Ampere independently reconstructed preparation, scoring, renderer
controls and source/asset identities, and replayed all frozen predictions before
reading primary inference scores. All **767 checks** passed; every prediction
matches byte for byte. Maximum score difference is **8.26e-12**.

Evidence limits: full wet renders were saved only for the first take/canary, so
the other eleven full-render hashes/peaks and wet pre-roll cannot be reconstructed.
Saved six-second input/baseline overlaps and all original-level host inputs match.
The host log lacks a parameter command transcript; PR12+R and the warm-up/close
sequence are supported by pinned code, not separately recorded plugin state.
Fixed slicing is verified but does not independently remeasure physical latency.
These limits carry forward to any diagnostic reusing the renders.

The separately reviewed and declared comparison with the existing simple `flatref`
stand-in is now [complete and independently verified](di-morgan-flatref-results.md):
57.83% median improvement over the better simple baseline, all twelve wins and
1,215 checks agree. This adds evidence of learned improvement on this fixed clean
Morgan chain, without changing the native/product limits. No long training follows.

Pedroza et al., Guitar-TECHS, CC BY4.0, https://zenodo.org/records/14963133.
Catalogued P2 development material, one player/guitar; no reserved data used.
