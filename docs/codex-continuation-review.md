# Review of the Codex continuation (2026-10-08/09)

Codex continued the song-to-preset work from `poc/sound-model` (8d8a57a) to cc4fb8a,
then the user stopped it. It had less context than the original session and was often
interrupted by usage limits. On 2026-10-09 three independent, fresh-context reviews
re-derived its results from the stored data, with their own code. This document
records what holds, what doesn't, and the corrected readings. The individual results
documents carry a short pointer to it.

## Verdicts

| study | verdict | corrected reading |
|---|---|---|
| **Set-3 held-out confirmation** ([results](set3-heldout-confirmation-results.md)) | **valid: failure is real** | See "The held-out confirmation" below. |
| Known-DI development diagnostic ([results](set3-development-diagnostic-results.md)) | **valid; conclusion corrected** | See "The development diagnostics" below. |
| Activity-mask diagnostic ([results](set3-mask-diagnostic-results.md)) | **valid; outcome mislabelled** | See "The development diagnostics" below. |
| Prior/score rank calibration ([results](set3-rank-calibration-results.md)) | **valid; keep the positive part** | See "The development diagnostics" below. |
| Cross-amp pooling ([results](set3-cross-amp-diagnostic-results.md)) | **valid negative** | See "The development diagnostics" below. |
| Native-transfer pilot v2 ([results](di-domain-pilot-v2-results.md)) | **wrong as a finding** | See "The native-transfer pilot" below. |
| Morgan clean-chain controls ([control](di-morgan-control-results.md), [flatref](di-morgan-flatref-results.md)) | **sound, but uninformative** | See "The lab controls and proposals" below. |
| Timing, input-shift, phase and alignment controls | **uninformative** | See "The lab controls and proposals" below. |
| Morgan processing control ([results](di-morgan-processing-control-results.md)) | **void, not inconclusive** | See "The lab controls and proposals" below. |
| Morgan AU startup utility ([results](morgan-au-startup-results.md)) | **drop** | See "The lab controls and proposals" below. |
| Proposals: native data; a direct preset ranker | native data: defer; direct ranker: right direction, likely underpowered | See "The lab controls and proposals" below. |

## The held-out confirmation

- **Procedure:** the procedure followed our draft. Every addition was declared before
  data was read, and none favours failure.
- **Recomputation:** recomputed exactly, including 94 audio spot checks.
- **SW50R against the fixed constant:**
  - closer on 10 parts, tied on 5, further on 12;
  - the mean log ratio is +0.065;
  - the −0.15 band-median headline is an artefact of taking medians.
- **Correction to our development reading:** against the *declared* all-33 constant
  (Wall Of Doom), development shows no robust edge either.
  - **SW50R:** the median of band medians is −0.023 (p 0.09–0.11). The per-part mean is
    −0.076, with 12 closer, 10 tied and 10 further.
  - **PR12:** about 0.
  - Our development figure of −0.17 to −0.20 used a leave-band-out constant chosen
    after the run.
  - So development already showed at most a small, unreliable edge over this constant.
    The held-out result (mean +0.065) is in line with that.

## The development diagnostics

- **Known-DI diagnostic.** Selecting through the *true* DI beats the leave-band-out
  constant on all three amps (SW50R −0.28/−0.30, PR12 −0.11/−0.18, AC20 −0.13/−0.11;
  p 0.001–0.004). That is a ceiling for this menu and measure: it is our earlier
  measure oracle.
  - Codex's "SW50R gap is zero" is a median artefact: 6 of 11 bands tie.
  - **Rebuilt against true DI, by mean per part:** about −0.16 on SW50R, about −0.24
    on PR12, about −0.22 on AC20.
  - **So ranking is nearly perfect with the true DI, and the loss is in the rebuilt-DI
    path.**
- **Activity mask.** Using the reference as the activity proxy rescues the one refused
  part (Colour Me Red ElecGtr03: 4.11 against the constant's 19.5) and changes none of
  the 11 controls. Its declared rule, at least 3 controls improved, could not
  sensibly be met by a refusal fix. **Adopt the reference-proxy fallback.** The mask
  is not the general bottleneck.
- **Rank calibration.** Rebuilt-DI scores carry song-specific information worth about
  0.2 over the best song-blind prior (p 0.02, SW50R only). Re-weighting adds nothing.
- **Cross-amp pooling.** A valid negative: pooling under rebuilt DIs hurts, and a
  perfect amp selector would gain about −0.06.

## The native-transfer pilot

**Codex's pairing calibration was mis-specified. The P2 pairs are fine.**
- The lags match our catalogue to within 1–3 samples.
- The sharpness test used 2-s halves and only ±512 lags; widening to ±4800 lags
  roughly doubles or triples the sharpness.
- The correlation threshold of ≥ 0.5 fails on a bass amp's 80–200 Hz band.

"3 of 12 passed" says nothing about the data, and the network never ran. Native
transfer is untested.

## The lab controls and proposals

- **Morgan clean-chain controls:** the method is sound, but the test rebuilds a DI
  after one clean PR12 preset the network was trained to undo. It is a sanity check,
  not progress on choosing presets.
- **Timing, input-shift, phase and alignment controls:** near-guaranteed passes, since
  the scores ignore magnitude-level shifts.
- **Morgan processing control:** `invalidComponentID (-3000)` came from Codex's
  sandbox, where `auval` lists no components. The component codes were right. The
  study never ran, so it is void, not inconclusive.
- **Morgan AU startup utility:** duplicates the working renderer. Lesson only: run AU
  work outside Codex's sandbox.
- **Native data (EGFxSet, ToneTwist):** low value for choosing Morgan presets from
  songs, and ToneTwist's licence is unclear.
- **Direct preset ranker:** right direction (song-only, no DI). An 8-band ridge model
  on about 11 band groups is probably too small. The "one compromise preset across
  simultaneous guitars" target needs the user's approval.

## What this changes

- **Most decision-relevant:** with the true DI the ranking works, and the loss is in
  rebuilding the DI. Improving the DI rebuild, PR12 and AC20 first, is the lever. First
  split the gap cheaply (level, mask, alignment, waveform).
- **No robust edge over a fixed driven preset** has been shown on heavy material, on
  development or held-out data. A per-amp constant driven preset is a real baseline.
- **Reporting:** don't route decisions on the median of band medians alone. Report the
  mean log ratio and wins/losses/ties beside it.
- **Data:** set 3's held-out split is spent. Codex's large evidence files are outside
  git (`EVIDENCE-OUTSIDE-GIT.md`).
