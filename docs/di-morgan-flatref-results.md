# Fixed Morgan renders: learned recovery versus simple correction

2026-10-08. **PASS, independently verified with zero mismatches.**
Procedure, implementation, input hashes and review committed `c8c40ad` before
computation. All twelve original saved performances were included. No rendering,
model inference, training, raw audio, catalog or checkpoint access was needed.

All 72 earlier input/network scores replayed within the unchanged absolute 1e-8
tolerance before any new stand-in was computed. The comparison completed in
4.69 seconds. The network beats the better of processed audio directly and
the existing simple spectrum correction on all twelve performances: **57.83% median
relative improvement**, with group medians **51.61% for chords** and **58.23% for scales**.
The simple spectrum correction is the better simple baseline on every take.
All declared criteria pass: median ≥10%, at least nine strict wins, and positive
medians in both groups.

Fresh-context Heisenberg independently reconstructed all twelve stand-ins, their
scores and the gate before reading the primary numerical results. **1,215 checks
pass, with zero failures or mismatches.** All stand-in waveforms match byte for byte;
the maximum original-score replay difference is 8.05e-12 and the maximum new
score/scalar/gate difference is 8.88e-16. All 36 input artifact hashes and 43 source
pins match, and commit-before-execution is verified.

## Evidence

- [Frozen procedure](di-morgan-flatref-plan.md) and
  [independent design/code review](research/di-morgan-flatref-review-2026-10-08.md).
- [Full scores and gate](di-morgan-flatref.json).
- [Independent numerical verification](di-morgan-flatref-verification.json),
  [report](research/di-morgan-flatref-verification-2026-10-08.md) and
  [implementation](research/di-morgan-flatref-independent-2026-10-08.py).
- [Mandatory original-score replay](di-morgan-flatref-baseline-replay.json).
- [Committed source and environment provenance](di-morgan-flatref-provenance.json).
- [Fixed input artifact hashes](di-morgan-flatref-inputs.sha256).
- Original run: `tmp/di-morgan-flatref-20261008/`; log:
  `tmp/di-morgan-flatref-20261008.log`.

This development comparison covers one training-compatible clean Morgan chain and
one player/guitar. It establishes no native microphone transfer, preset ranking,
driven or multi-guitar coverage, shipping readiness or case for longer training.
The original render evidence limits carry forward: eleven full wet outputs were
not retained, plugin commands lack an independent transcript, and fixed slicing
does not remeasure physical latency. The saved six-second arrays are reused exactly.
The verifier freshly checked six-second raw score QC; full ten-second QC and
renderer stability are inherited from the prior independent verification.

Next: separately review and declare a positive/negative control for the frozen
timing-confidence method that stopped the native pilot. Use artificial known
offsets and mismatched performances from saved dry arrays, without native microphone
audio, model inference or training. This will test that method's reliability;
it will not change its thresholds or rescue/reopen the closed native study.

Pedroza et al., Guitar-TECHS, CC BY4.0, https://zenodo.org/records/14963133.
