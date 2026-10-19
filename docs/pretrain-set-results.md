# A labelled pre-training render set (part C): results (2026-10-19)

Run under the [plan](pretrain-set-plan.md) (amendments 1 and 2) on the self-render runner
(`learn/selfrender_run.zsh`), the tail and the curve from commit 5fe3c5d (amendment 2).
Development data only; descriptive estimates with 90% band-clustered t intervals over the 9 val
bands, no pass/fail bars.
- **Code:** `learn/pretrain_set.py`. **Data:** `~/ndsp-presets/learn/pretrain-set/` (`curve.json`,
  `decide-40000.json`, `recheck.json`, `report.json`, `rows/`); logs in
  `~/ndsp-presets/learn/selfrender/logs/` (`c-render-40000-*.log`, `c-curve-40000.log`,
  `c-decide-40000.log`, `c-recheck.log`, `c-report-40000.log`, `resume-c.log`, `run.log`).

**The question:** how many self-rendered examples (clean DI sections through drawn Morgan settings,
mixed into their own session backings) does arm B's network at half width need before more stop
helping? The declared rule doubles the set while the last doubling's interval lies below 0.

## Headline

**On the declared readout the curve flattened at about 20k examples: DECISION STOP, read "flat", no
extension to 80k.** But the same models keep improving on the guitar alone and on the training-style
mixes; only the true mixes stop. So the limit on true mixes looks like the gap between the power-sum
training mixes and true sample-domain mixes (half of them mastered, which training never sees), not
the number of examples. Both are rendered: none of this is real-song accuracy.

| Size | E(n), true mixes (primary) | Δ from the previous size |
|---|---|---|
| 5k | 0.1934 [0.1803, 0.2065] | |
| 10k | 0.1872 [0.1749, 0.1995] | −0.0062 [−0.0093, −0.0032] |
| 20k | 0.1802 [0.1679, 0.1926] | −0.0069 [−0.0092, −0.0047] |
| 40k | 0.1814 [0.1670, 0.1959] | **+0.0012 [−0.0020, +0.0045]** |

- **The rule.** Δ(20k → 40k) includes 0, so STOP. It reads "flat", not "undecided", because its
  lower bound (−0.0020) lies above half the previous doubling's gain (−0.0035): the interval rules
  out a gain half as large as the last one. Per seed at 20k → 40k: −0.0015 [−0.0091, +0.0062],
  +0.0050 [+0.0017, +0.0082], +0.0002 [−0.0040, +0.0043] (seeds 20261042–44; two seeds below 20k).
  Seed spread of E: 5k 0.1933–0.1935, 10k 0.1835–0.1908, 20k 0.1786–0.1814, 40k 0.1792–0.1836.
- **Scope-tagged examples** (1,780 beyond the gain-scope threshold, excluded from E as declared):
  including them changes nothing (E(40k) 0.1807, E(20k) 0.1798).
- **The power-law fit** the plan lists beside the rule was not computed by `decide`. With E rising
  from 20k to 40k it would add nothing.

## What E measures, and what it doesn't

E(n) is the knob error a pre-trained arm B would start from: the band-weighted mean, over 3,000 val
examples (each example's value already averaged over its two halves), of |μ_top − θ| on the amp's continuous settings (unit scale). The val
examples are renders of **held-out bands' DIs**, through drawn settings, in **true mixes** made from
audio with their own session backings. It is **in-domain validation on rendered mixes, not accuracy
on real songs**: the settings are drawn, the guitar is our render, and no separator is involved (the
stem channel is a simulated leak). It says how well this model learns this set, not how close a
preset lands on a song.

## Beside the rule (post hoc, not deciding)

Recomputed from `curve.json` with the plan's own functions (same val examples, same intervals):

| Readout (9 bands) | 20k | 40k | Δ 20k → 40k |
|---|---|---|---|
| True mixes, primary | 0.1802 | 0.1814 | +0.0012 [−0.0020, +0.0045] |
| Clean stem (the guitar alone) | 0.1757 | 0.1694 | −0.0063 [−0.0092, −0.0035] |
| Power-sum mixes (the training composition, unmastered val examples) | 0.1711 | 0.1626 | −0.0085 [−0.0111, −0.0059] |
| True mixes, the same unmastered examples | 0.1758 | 0.1744 | −0.0015 [−0.0053, +0.0024] |
| True mixes, mastered examples | 0.1843 | 0.1883 | +0.0040 [+0.0008, +0.0072] |

- **The model still learns from 20k to 40k**, about as fast as from 10k to 20k, on the guitar alone
  and on mixes built the way training builds them. On the same unmastered examples the true mix
  flattens (−0.0015 [−0.0053, +0.0024]), and on mastered ones it gets slightly worse. The
  divergence is clear: true minus clean-stem Δ +0.0076 [+0.0059, +0.0093]; true minus power-sum on
  unmastered examples +0.0070 [+0.0049, +0.0092]. The mel-power mix ignores the cross term
  (median 0.31 dB, 90th percentile 1.65 dB, 99th 4.99 dB on part C's own audit examples) and the
  stem channel is a crude leak, and training never sees mastering. Which of the three causes the
  divergence is not separated.
- **Diversity of DIs matters** (one seed, at 20k). 20k examples drawn from half the train sections (one seed) read
  +0.0087 [+0.0032, +0.0141] worse than 20k from all of them (clean stem +0.0088 [+0.0048, +0.0128]).
- **Training length.** 7 of the 11 runs used all 30 epochs, and in 4 of them (one at each size)
  the best early-stopping epoch was the last, so some runs may be slightly under-trained.

## The recheck, renders, disk and history

- **Recheck** (30 stored examples re-rendered, each after one discarded priming render, amendment 2
  item 1): SNR past 4 s of the stored window median 85.9 dB (min 61.9, max 91.7); half-B mel cells
  identical median 99.97% (min 99.85%); late max |Δ| at most 9.3e-4, the size the start-transient
  audit saw left after a DI change in 16-bit audio. The stored renders reproduce.
- **Renders:** 43,000 examples (40,000 train, 3,000 val; 276 audit examples with audio), plus 60
  for the recheck (30 priming + 30). Median 1.58 s per render on 3 shards: 14:08–20:15 on
  2026-10-18, then the tail 20:16–22:48. The curve (11 runs) took 22:48–07:40 on the GPU.
- **Disk:** 3.68 GB of examples and backings after the renders (planned about 3.3 GB); 3.71 GB
  in `report.json` now, with the curve models and the recheck.
- **History.** The disk guard (31 GB free) stopped shards 0 and 1 cleanly at about 8,800 renders
  each (8,950 and 8,850 rows); shard 2 finished its 14,333. The servers' memory growth caused it
  (about 5 GB each). Amendment 2 then moved learn's renders to the bounded server (#224, #226;
  bit-identical renders, checked), primed the recheck and masked half A's first second in every
  training batch, early-stopping pass and val readout (`curve.json` records 100 masked frames, and
  `curve` refuses runs trained without it). The tail resumed from the stored rows (5,384 and
  5,483 renders) and finished.

## What it implies

- **On this readout, with this model size and training recipe, the gain stopped somewhere between
  20k and 40k examples.** The curve gives no reason to expect 80k to move it; one seed (20261043)
  alone got worse (+0.0050 [+0.0017, +0.0082]). The model's capacity is not the limit on the guitar
  alone (still improving at 40k). The divergence between true and training-style mixes is clear, but
  its cause (the mel-power approximation, the leak stem, or mastering) is not separated, and more
  DIs leaned more useful than more draws per DI (one seed). If the set grows, the levers are true audio mixes in training (or a
  better mix approximation and a real separator's stems) and more distinct DIs, not more draws.
- **The open question is real-song transfer.** E says nothing about songs. Arm B's earlier
  sound-space retrain, B2, tied S on songs (−0.033 [−0.100, +0.035];
  [results](song-to-settings-soundspace-results.md)). **Next: a real-song test of a model trained
  on this set** (pre-trained here, fine-tuned on arm B's bank), scored against S on fresh songs.
- **A strategic decision is pending with the user.** The audited oracle test
  ([arm A with Mega-53, amendment 2](arm-a-mega53-results.md#amendment-2-the-oracle-di-arm-on-stage-f-2026-10-18))
  found that a perfect DI doesn't help arm A on fresh full mixes (+0.012 [−0.088, +0.112] against
  S): the stem objective, not the rebuild, limits it. The proposal is to make direct prediction
  (arm B, song to settings, with this set as its pre-training) the main route. That is the user's
  call.

Audited 2026-10-19 by an independent agent (recomputed E, every Δ, the reading and the decision from
`curve.json` with its own interval code; checked the half-A mask on every curve run, the post-hoc
rows, the recheck, the render counts and disk; all match); changes: the mix gap named as power-sum
against true sample-domain mixes and its cause marked as not separated, with the divergence's
intervals; the stop stated as "between 20k and 40k, for this model and recipe", with the seed that
got worse; the half-sections result marked one seed; the unmastered interval, the seed spread and
the disk's two readings added.
