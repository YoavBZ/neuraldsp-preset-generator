# A learned settings model, proof of concept: results

Run as declared in [preset-model-poc-plan.md](preset-model-poc-plan.md), with its
amendments.
- **Setup:** PR12, 18,843 usable renders of sampled settings through 14 players' DIs.
  Four fold models were trained for 15 epochs and scored with K3's test on 28 real amp
  tracks in 11 bands.
- **Verification:** an independent reviewer re-derived every distance from the audio.
  - All distances matched exactly.
  - Its own re-chosen constant reproduced K3's constant.
  - Re-running all four fold models showed each part was read by the one model that
    never saw its band.

## Verdict: not passed

| | recording bands | union bands |
|---|---|---|
| band median log ratio vs template+R (needs ≤ −0.105) | −0.037 | −0.037 |
| band sign-flip p, two-sided | 0.29 | 0.22 |
| parts closer than template+R | 17/28 | 18/28 |
| closer than the shuffled control | 22/28 | 21/28 |
| closer than K3's constant | 15/28 | 20/28 |
| part median log ratio | −0.066 | −0.066 |
| K3's recognisers (1-NN / LDA / LDA+1-NN) | −0.012 / −0.023 / −0.064 | −0.013 / −0.009 / −0.030 |

The level-informed variant (the part's own DI level used, a leak) gives the same
result (−0.036): the assumed input level costs nothing measurable here.

## What holds up

- **Reproduced exactly; no leak.** Every row was re-derived, and nothing was silent,
  clipped or truncated.
- **The model reads something specific to each part.** Fed its own amp track rather
  than three other bands', it is closer on 21–22 of 28 parts (band median −0.10, 9 of
  11 bands, p 0.17). It still does so on 19–20 of 26 without the two biggest wins.
  K3's 1-NN on this material carried no part-specific information.
- **It doesn't collapse to one preset, but it shrinks hard toward the average.**
  - Across parts, its predictions spread 0.44 as much as the training labels.
  - The EQ bands are nearly flat (0.07–0.29 of the training spread).
  - What varies is treble, the filters, cab position and distance, and drive.

## What does not

- **The median gain over template+R rests on two parts.**
  - **Today's The Day ElecGtr07 (−0.93)** is a real tonal move: high-pass at 107 Hz,
    low-pass at 7 kHz, more treble. But the template is worst of all 28 there, and the
    whole clean menu is far from the part.
  - **Honey (−0.87)** is largely the template's heavy compressor being wrong there; most
    factory presets beat the template on it.
  - Without these two, the band median is −0.001 / −0.002 (p 0.69 / 0.90), and the
    count against the constant fails under recording bands (13 of 26).
- **Against the best constant preset it is not distinguishable** (recording bands:
  −0.02, 6 of 11 bands, p 0.69).

## Why, as far as the evidence goes

Two measurements on the clean PR12 panel, recorded in the plan's amendment before this
result:
- the player's DI moves one preset's transfer curve by 1.9 dB per band;
- the 21 clean presets differ from each other by 1.45 dB.

In-domain, the model learned mic type (75% against 40% for the majority class), cab
placement, the pedal knobs and the filters. On the EQ bands and input gain it did no
better than the median. On clean PR12, much of what separates two recordings is the
player, which a model reading only the recording can't undo.

## What follows

The first learned model is the first song-only method in this project to carry
part-specific information on clean PR12, but it is not useful yet. The next iteration
(declared before it runs) should change what is learned, not tune this model:

1. **Train on the sound, not the knobs.** The target is the transfer curve plus drive
   and dynamics descriptors. Settings are chosen from the 18,843-render library, or
   through a learned forward model, to produce that sound.
2. **Train on song-like input:** renders mixed into backings, then separated. The stems
   for the 28 parts are ready (20 usable).
3. **Rerank candidates** through several typical DIs before answering.
4. **Heavier tones and all three amps,** where settings leave a larger mark. Clean PR12
   is the hardest case for song-only matching.
5. **Settle the yardstick.** The judge asks for the recording's own chain through its
   own DI. The product's goal is "my guitar sounds like the record". A preset estimated
   for a typical guitar is partly penalised by the judge whenever the recorded player
   is atypical. A listening check through another player's DI would settle which
   matters.

Outputs (local): `~/ndsp-presets/learn/poc/eval/results-run1.json`, renders in
`renders-run1/`, the models in `models/`, and the verifier's scripts in `/tmp/verify/`.
