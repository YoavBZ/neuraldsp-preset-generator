# Cutting the rebuilt DI's incoherent top end: results (set 3, development)

Run 2026-10-10 as declared in [rebuilt-di-lowpass-plan.md](rebuilt-di-lowpass-plan.md)
(commit 4d8fb83, before the first render). It made 7,326 renders. An independent
reviewer re-derived every number, checked the filter against scipy and recomputed 24
distances from the stored renders. The numbers matched exactly
(`tmp/lowpass-review.md`, local).

**Outcome under the declared rule: neither cutoff helps.** The 3 kHz cut misses the bar
by 0.0009. Low-passing does not go into the chooser.

## Numbers

Pooled over the three amps; mean log ratio of the pick's half-B distance (negative is
closer), with wins / ties / losses.

| comparison (33 parts × 3 amps) | recording bands | union bands |
|---|---|---|
| **3 kHz cut vs current rebuilt DI** | **−0.0491** (23 / 71 / 5) | −0.0492 (21 / 67 / 11) |
| 6 kHz cut vs current rebuilt DI | +0.004 (1 / 95 / 3) | +0.001 (1 / 92 / 6) |
| 3 kHz cut vs fixed driven preset | −0.086 (45 / 20 / 34) | −0.102 (48 / 18 / 33) |
| current rebuilt DI vs fixed driven preset | −0.037 (38 / 19 / 42) | −0.053 (41 / 18 / 40) |
| 3 kHz cut vs clean template | −0.435 (87 / 0 / 12) | −0.427 |

- **The bar is −0.05.** The unrounded mean is −0.04907, so it fails, with more wins than
  losses (23 to 5). The bar does not move.
- **Per amp** (recording bands): PR12 −0.056, SW50R −0.037, AC20 −0.055. Against the
  fixed preset, AC20 still loses more parts than it wins (12 to 20).
- **The 6 kHz cut changes almost nothing.** The rebuilt DI has little content above
  6 kHz.

## How solid the near miss is

- **Most picks don't change:** only 28 of 99 part-amp cases differ from the current
  rebuilt DI.
- **A few cases carry it:** the five largest wins make up 55% of the total. Without the
  single best win the mean is −0.042; without the top three, −0.032.
- **Leaving out one band** moves the mean between −0.059 and −0.041. Dropping one part
  moves it between −0.056 and −0.041.
- **Bootstrap over parts:** a 95% interval of −0.082 to −0.018. The chance the mean
  reaches −0.05 is about 0.46.

The direction is fairly consistent: it never makes picks clearly worse, and the interval
excludes zero. The size sits on the bar: "nearly passed" is no stronger than "nearly
failed".

## Biases worth knowing

- **Against the fixed presets, the method is understated.** Those presets were chosen
  on these same 33 parts.
- **The cut itself is slightly flattered.** The idea and the better of two cutoffs were
  chosen with these parts in view.
- **No held-out claim follows either way.**

## Next

Low-passing stays out of the chooser. The network itself remains the lever: its bottom
levels were dead in every run so far ([v2 results](di-network-v2-results.md)), and
[v3](di-network-v3-plan.md) repairs that. If a repaired network helps, a top-end cut can
be re-declared on top of it, and tested on fresh material.
