# Re-scoring under the fixed-level measure (set 3, development)

2026-10-10, after the user's decisions in the
[closeness review](closeness-review-2026-10-10.md).
- **The changes:** the measure plays the true DI at a fixed −22.9 LUFS; both halves are
  scored (choose on A and score on B, and the reverse); the fixed preset is chosen
  leave-band-out; statistics are clustered by band.
- **How:** `learn/rescore.py` scored 43,956 distances from stored renders, under the
  validated judge (`flat`) and the new `hearing` option.
- **Review:** an independent reviewer re-derived every figure, recomputed 22 distances
  from audio, confirmed the default judge is unchanged, and audited the forks
  (`tmp/rescore-review.md`, local).

## Numbers (flat judge)

Each figure is the mean log ratio of the pick's distance (negative is closer), with its
band-clustered 90% interval, wins / ties / losses, and the exact band sign-flip p.

| comparison | mean | 90% interval | W / T / L | p |
|---|---|---|---|---|
| **3 kHz cut vs uncut rebuilt DI** | **−0.070** | −0.109 to −0.030 | 33 / 61 / 5 | 0.016 |
| 3 kHz cut vs leave-band-out fixed preset | −0.143 | −0.274 to −0.012 | 69 / 6 / 24 | 0.043 |
| uncut rebuilt DI vs leave-band-out fixed preset | −0.073 | −0.222 to +0.075 | 53 / 5 / 41 | 0.45 |
| 3 kHz cut vs the original (in-sample) fixed preset | −0.126 | −0.279 to +0.028 | 51 / 16 / 32 | 0.19 |
| true DI (oracle) vs leave-band-out fixed preset | −0.260 | −0.385 to −0.135 | 91 / 3 / 5 | 0.001 |
| oracle vs uncut rebuilt DI | −0.186 | −0.248 to −0.124 | 71 / 20 / 8 | 0.002 |
| leave-band-out fixed preset vs clean template | −0.297 | −0.520 to −0.074 | 77 / 0 / 22 | 0.053 |

The `hearing` judge gives the same picture: the cut −0.068, and the cut vs the
leave-band-out preset −0.131 (−0.265 to +0.002). Its results correlate 0.90 with the flat
judge's.

## What can be claimed

- **The 3 kHz cut picks closer presets than the uncut rebuilt DI, by about 7%.**
  - It holds under both judges, in both scoring directions and with any one band
    dropped (33 wins, 5 losses).
  - This settles the earlier near miss: the cut was adopted, and it helps.
- **"The learned chooser beats a fixed driven preset" is not established.**
  - **Two bands carry most of it:** Diesel13 (−0.72) and Timo (−0.64). Without Diesel13
    it is −0.085 (p 0.086); dropping single bands pushes p above 0.05 in 8 of 11 cases.
    The part that needs the fallback supplies 26% of the total.
  - **The gain is all tonal** (82 to 11). On the temporal part the picks lose (33 to
    60): they are under-driven, as the review found.
  - **The scoring direction matters:** choose on B / score on A gives −0.127, p 0.14.
  - **Many choices were made with these parts in view:**
    - the cutoff, its adoption, the level decision and the leave-band-out rule;
    - both-halves averaging, the fallback and the hearing thresholds;
    - about 15 earlier tests on the same parts.

    The reviewer expects the true effect to be about half the observed one.
- **The true-DI oracle beats the fixed preset by −0.26** (91 to 5). There is real
  headroom in choosing per song.

## The hearing-weighted judge, as built

- **It is not yet what was decided.** It still selects bands per window, then caps them
  at 10 kHz. The decision was a fixed band set per part.
- **Its weighting turns treble down** (−7.5 dB at 10 kHz, with area normalisation), which
  works against the "fizz is nearly free" finding. Only the Ill Fate parts gain bands.
- **Its thresholds were set with these parts in view:** 16 bands just excludes Ill Fate
  1 and 2, which it refuses on half B.
- **Next:** rebuild it as a fixed per-part band set up to about 10 kHz, with no treble
  penalty. Declare it before scoring, and adopt it only if the heavy-tone
  [listening check](heavy-listening-plan.md) agrees.

## What a confirmation needs

Power, from resampling the observed bands (the chance the 90% bound excludes zero):

| true effect | 6 bands | 11 bands | 20 bands | 30 bands | 45 bands |
|---|---|---|---|---|---|
| −0.143 (as observed) | 34% | 69% | 96% | | |
| −0.072 (realistic) | | 15% | 32% | 50% | 70% |
| −0.26 (the oracle) | 96% | | | | |

So a fresh confirmation needs at least 20 new bands (about 60 parts), and better 40 or
more. Everything is declared before scoring: the constant, the measure, the judge and the
test. The oracle must pass first, as a positive control. Six bands can only confirm
effects the size of the oracle's.
