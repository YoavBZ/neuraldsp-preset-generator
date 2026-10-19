# Two zero-render checks: shrink against stem quality, and judge v3 against the ear (2026-10-19)

Development data only, stored records only, **zero renders**. Descriptive: no plan was declared, so
both readings are post hoc. Figures are held-half log ratios (negative is closer to the record),
averaged per part, band-weighted, with 90% band-clustered t intervals.

## (a) Does the best shrink depend on the stem's quality?

**What the stored records allow.** Every arm A search stores its held-half judge at three points
only: the unshrunk best (kept fraction f = 1), the recipe's halfway shrink (f = 0.5) and S (f = 0).
Stage D's levers experiment 1 (the older 150-render search A, htdemucs instrumental stems) adds f =
0.25 and 0.75. No other shrink was rendered, so **a rule can only choose among these levels.** A
continuous shrink-by-SNR curve would need renders (about one render per direction per new level:
1,056 for one level across stage F and stage D's 52-render arms).

**What was fitted.** A threshold rule: f_lo below an SNR threshold, f_hi at or above it (a constant f
is one of the options). It is fitted on all other bands and applied to the held-out band (leave one
band out, 16 bands pooled across stages). SNR is the gain-fitted SNR of the search's target stem
against the amp track; the amp track itself counts as perfect. The arms: stage F's H (htdemucs, full
mix, median 0.43 dB), M (Mega-53, 0.70 dB), YT (perfect target) and ZT (perfect target, true DI);
stage D's H (htdemucs, instrumental, 2.15 dB), M (Mega-53, 3.97 dB) and T (perfect). That is 930
directions. Code `learn/shrink_vs_snr.py`; data `~/ndsp-presets/learn/shrink-vs-snr/report.json`.

| Held-out gain against the recipe (f = 0.5) | Estimate [90%], bands | Bands better / worse |
|---|---|---|
| **The SNR rule, all arms** | **−0.003 [−0.013, +0.007]**, 16 | 9 / 7 |
| The best constant f, all arms | +0.008 [−0.006, +0.021], 16 | 0 / 1 |
| The SNR rule against the best constant | −0.011 [−0.021, +0.000], 16 | 10 / 6 |
| The SNR rule, realistic stems only (H and M, both stages) | −0.001 [−0.004, +0.003], 16 | 2 / 2 |
| Five levels, stage D's search A only | +0.008 [−0.017, +0.033], 14 | 6 / 5 |
| Adding stage F's XO (true DI, stem target) | +0.013 [−0.003, +0.028], 16 | 2 / 6 |

Per arm, the all-arms rule's held-out gain: ZT −0.047 [−0.070, −0.025], YT −0.010, D's T −0.003,
F's H 0.000, F's M +0.006, D's M +0.007, D's H +0.011. Every fold's rule had the same shape: keep the
halfway shrink below a threshold and go unshrunk above it. Most folds put the threshold between 2.6
and 7 dB, inside the realistic range; one put it at "perfect stems only".

**Reading.**
- **The best shrink does not measurably depend on stem SNR among the stems we have.** On realistic
  stems the rule gains nothing (−0.001), and the halfway shrink stays the best fixed choice on both
  stages (on stage F unshrunk costs +0.022 for H and +0.035 for M; S costs more).
- **The only clear dependence is with a perfect target and the true DI** (ZT, −0.047), which is the
  shrink cost amendment 3 already reported. With a perfect target through the rebuilt DI (YT) it is
  a tie (−0.010). So the shrink's cost tracks how good the search objective is as a whole
  (target and DI), not stem SNR alone, and the rule's pooled −0.003 comes almost entirely from ZT.
- **A rule fitted with XO in the pool hurts** (+0.013): XO prefers S on low-SNR stems, which pushes
  the rule towards f = 0 where H and M need 0.5. This is the instability to expect when a rule is
  fitted across arms whose objectives differ for reasons SNR doesn't see.
- **Post hoc:** per part, unshrunk − recipe against SNR on realistic stems has Spearman −0.11
  (p 0.29, 90 part-arms).
- **For the next steps:** keep shrink 0.5 for arm A on separated stems. Re-check the shrink once the
  fine-tuned separator exists, at f = 0.75 and 1, as part of that step's own renders.

## (b) Judge v3 against the listener (record-match check 1)

**The stored audio was kept.** The check saved every arm's held-half clip
(`~/ndsp-presets/listening/record-match-1/private/renders/*.npz`). Placed back at the held half's
bounds, the clips reproduce the stored default-judge scores within 2.3e-8 in log, so the same clips
were re-scored with judge v3 (`JUDGE_V3`: fixed bands, symmetric floor; [spec](judge-spec.md),
[results](judge-v3-results.md)). Code `learn/record_match_v3.py`; data
`~/ndsp-presets/learn/record-match-v3/report.json`. The ear's answers are those in the
[listening results](record-match-listening-results.md).

| Trial (part) | Ear, closest first | Default judge | Judge v3 |
|---|---|---|---|
| 1 magilla elecgtr1 | C H D S | C H D S (ρ 1.0) | C D H S (ρ 0.8) |
| 2 get-out-of-bed elecgtr2 | C H D S | C D H S (0.8) | H C S D (0.6) |
| 3 Signs ElecGtr3 | C S H D | C S H D (1.0) | S C H D (0.8) |
| 4 Gym Hours GTR_2 | D C H S | C D H S (0.8) | C D H S (0.8) |
| 5 Today's The Day ElecGtr07 | C H D S | C D S H (0.4) | C S D H (0.2) |
| 6 repeat of 2 | C H S D | C D H S (0.4) | H C S D (0.8) |

| Over trials 1–5 | Default judge | Judge v3 |
|---|---|---|
| Spearman ρ with the ear, mean (positive) | **0.80** (5 of 5) | **0.64** (5 of 5) |
| ρ among S, H and D only, mean | 0.60 | 0.40 |
| Pairs ordered as the ear did | 26 of 30 | 22 of 30 |
| Pairs among S, H and D | 12 of 15 | 10 of 15 |
| Top pick is the ear's | 4 of 5 | 2 of 5 |

**Reading.**
- **On these five parts the default judge agrees with the ear a little better than judge v3.** v3
  still agrees positively on every trial, but it moves the closest pick away from the ear's twice
  (S first on Signs, H first on get-out-of-bed). The repeat (trial 6) goes the other way: v3 fits
  it better (0.8 against 0.4), because the ear's own order changed.
- **This leans against adopting v3, but weakly.** Five parts, one listener, four items a trial: a
  difference of 4 pairs in 30 is within what one or two trials can swing. C was searched with the
  default judge, which favours it here; without C (S, H and D only) the default still leads (12 of
  15 pairs against 10).
- **What a fair test would cost:** a sitting built on pairs where the two judges disagree, which
  v3's adoption was always waiting for. That needs new clips (renders), not stored ones.

## Audit

One brief independent audit re-ran both scripts from the stored records and checked the figures
above against their reports. *(Findings are added below when it is done.)*
