# Correcting the under-driven picks: results (set 3, development)

Run 2026-10-10 as declared in [underdrive-trim-plan.md](underdrive-trim-plan.md) (plan
committed 13:30:32; renders finished at 14:01, scores at 14:04). An independent reviewer
re-derived every figure, confirmed the quieter DIs are exact scaled copies, and
recomputed distances from audio (`tmp/trim-fixed-review.md`, local).

**Outcome under the declared rule: futile for both.** Playing the rebuilt DI quieter
doesn't improve the picks. It is dropped.

## Numbers

Fixed-level measure, flat judge, both halves; mean log ratio against the 3 kHz cut
chooser (`lp3k`), with its band-clustered 90% interval:

| variant | mean | 90% interval | W / T / L |
|---|---|---|---|
| 6 dB quieter | −0.011 | −0.028 to +0.006 | 26 / 60 / 13 |
| 12 dB quieter | −0.003 | −0.017 to +0.011 | 37 / 35 / 27 |

Both lower bounds are above −0.05, so both are futile. The temporal part improves by
about 0.03, and the tonal part pays for it.

## The drive bias

The pick's gain knob minus the oracle pick's knob, under the adopted protocol:

| chooser | bias |
|---|---|
| uncut rebuilt DI | −0.094 |
| 3 kHz cut | −0.056 |
| 6 dB quieter | −0.029 |
| 12 dB quieter | −0.035 |
| leave-band-out fixed preset | +0.215 (over-driven) |

- **The trim roughly halves the under-drive, but the closeness doesn't follow.**
  Under-drive is not the main cause of the remaining gap to the oracle.
- **A correction to the plan's motivation:** its −0.124 and −0.088 were measured
  against the true-level oracle on half A only. Under the adopted protocol the bias is
  about a third smaller.
