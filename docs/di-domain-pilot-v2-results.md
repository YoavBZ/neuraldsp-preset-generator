# Native-chain pilot attempt 2 — stopped at pairing controls

> **Review 2026-10-09** ([codex-continuation-review.md](codex-continuation-review.md)): WRONG AS A FINDING: the pairing calibration was mis-specified (2-s halves, ±512 lags, ≥0.5 correlation on a bass amp). The P2 pairs are fine; lags match the catalogue to within 1–3 samples. Native transfer is untested.


2026-10-08. **Verified QC stop: incomplete valid coverage. Scientific screen
inconclusive; no neural transfer test was run.** Procedure/review/code were committed
at `e49950b` before computation.

Both runtime metric preflights pass, retaining the original absolute 1e-8 tolerance.
The existing CPU Torch environment uses NumPy 2.0.2; the actual helper uses NumPy
2.5.1. Both produce maximum errors of 3.55e-15 against unchanged `direc.mrstft`.
Regenerated synthetic input hashes agree across environments.

Native preparation processed all twelve fixed P2 pairs in 4.50 seconds. Only three
chord pairs passed the declared calibration/QC rules. Eight pairs first failed the
requirement that full and both half-calibration GCC-PHAT sharpness exceed 10; one
scale pair first failed the absolute filtered-correlation threshold of 0.5. These
are first rejection reasons, not a claim that every other diagnostic passed.

Valid pairs: `p2-chords-drop3-7-t098`, `p2-chords-set1-7-t099`,
`p2-chords-set1-dim-t072`. All remaining nine rows are retained as rejected.
All twelve were required and none may be replaced. Native stage exit 0 means it
finished recording its report; `valid:false` prevents downstream progression.

**No Morgan rendering, model loading/inference or training followed.** This result
cannot establish whether the frozen network transfers to the recorded chain. It
shows that this fixed pairing screen is unsuitable for the full selected panel
under the declared rules; independent recomputation confirms the stop.
Do not lower thresholds, use the inherited whole-crop lag as a fallback, change
excerpts, or evaluate only the passing subset to rescue this study.

## Evidence and independent verification

- [CPU synthetic preflight](di-domain-pilot-v2-metric.json).
- [Actual helper NumPy replay](di-domain-pilot-v2-numpy.json).
- [Complete native report, including every rejection](di-domain-pilot-v2-native.json).
- [Independent numerical verification](di-domain-pilot-v2-verification.json),
  [report](research/di-domain-pilot-v2-verification-2026-10-08.md) and
  [implementation](research/di-domain-pilot-v2-independent-2026-10-08.py).
- Run: `tmp/di-domain-pilot-20261008-attempt2/`; logs:
  `tmp/di-domain-pilot-attempt2-{metric,numpy,native}.log`.
- Declaration: [attempt 2](di-domain-pilot-v2-plan.md), original scientific
  [procedure](di-domain-pilot-plan.md), [code/design review](research/di-domain-pilot-v2-review-2026-10-08.md).

Fresh-context Avicenna independently reconstructed all twelve takes from 24 exact
bounded slices and all 36 GCC estimates before opening saved numerical outcomes.
All 24 saved arrays and 39 score fields matched: maximum errors 2.22e-16 and
6.89e-13 respectively. All source hashes, both preflights, complete coverage and
the absence of render/inference artifacts agree. Zero numerical mismatches.

The independent diagnostics show several rejected chord pairs still have stable
lags and high correlation; rejection is not proof that they are bad recordings.
Scale correlations are much lower. Do not use these diagnostics to retune the
stopped screen. The verifier records every predicate, including failures masked
by the original first-error reporting.

Close this native screen. Next, separately declare the known-DI Morgan control on
all twelve original dry recordings, independent of microphone alignment. It can
test unseen-performance recovery through the frozen training-compatible chain;
it cannot establish transfer to native recordings. Original rules, failure records
and reserved material remain unchanged. No long training is justified yet.

Dataset attribution: Pedroza et al., Guitar-TECHS, CC BY 4.0,
https://zenodo.org/records/14963133. This is catalogued P2 development material from
one clean bass-amp/player/microphone/room chain, not reserved or product validation.
