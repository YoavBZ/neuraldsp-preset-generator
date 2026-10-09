# Does the judge still choose well through a wrong DI? Results

Run as declared in [di-robustness-plan.md](di-robustness-plan.md), with its dated
amendments, by `learn/di_robustness.py`.
- **Material:** K1's 25 parts in 9 bands, the 21 clean PR12 factory presets plus
  template+R, and 2,750 renders through degraded or rebuilt DIs.
- **Check:** the `true` row reproduces K1's split-half oracle exactly (−0.267 / −0.206),
  so the procedure is K1's.

## The declared verdict: not passed

| choose on half A through… | band median vs template+R, scored through the true DI on half B (recording / union) | picks within 0.150 of the true-DI pick (parts; bands) | meets the rule |
|---|---|---|---|
| the true DI (K1's oracle) | −0.267 / −0.206 | 25/25; 9/9 | — |
| **swap**: another band's tonal balance | −0.115 / −0.146 | 15–17/25; 4/9 | no |
| **mild**: tilt, smear, soft clip, −20 dB bleed | −0.199 / −0.179 | 23–24/25; 9/9 | yes |
| **swap+mild** | −0.052 / −0.098 | 15–16/25; 6/9 | no |
| *added after the verdict:* **avg**, an average guitar's balance | −0.168 / −0.115 | 17–19/25; 5–7/9 | yes |
| *added after the verdict:* **avg+mild** | −0.067 / −0.168 (p 0.03 / 0.02) | 17–19/25; 5–6/9 | no (recording bands) |
| training-free: the amp track re-equalised to an average DI | 0.000 / +0.034 | 13/25; 4/9 | no |
| training-free: the separated stem, likewise (18 parts) | −0.012 / −0.027 | 11–12/18; 5/9 | no |

What the table shows:
- **Wrong guitar balance costs the most.** The judge's choice survives artefacts (mild)
  but not a wrong guitar balance at full size (swap).
- **An average balance costs much less** than another player's.
- **Without training, a rebuilt DI doesn't work.** The recording still carries the
  original amp's compression and drive, so each candidate is processed twice.

## Exploratory, not declared: the same picks under the product's question

The judge asks whether settings recreate *this* recording's chain on *its* guitar. The
product's user plays their own guitar. So the same half-B renders were re-scored
through the `avg` DI: the true take, at an average guitar's tonal balance. That asks
"how close does an average guitar playing these notes get to the record?" Nothing was
re-rendered.

| picks made through… | band median vs template+R under the average-guitar question (recording / union) | parts closer |
|---|---|---|
| the true DI | −0.078 / −0.057 (p 0.34 / 0.31) | 20/25 |
| avg | −0.149 / −0.153 (p 0.004) | 23–24/25 |
| avg+mild (a realistic rebuilt DI) | −0.149 / −0.136 (p 0.008) | 22/25 |
| this question's own split-half oracle | −0.149 / −0.153 | — |

Under that question, choosing through a realistic rebuilt DI loses essentially nothing
against the best choice from this menu. The true-DI choice, which fits the original
guitar, is worse.

This is exploratory, for three reasons:
- the question was framed after the declared results were read;
- no listening test yet confirms that an average-guitar render compared with the record
  tracks what a player hears;
- it rests on the same 25 development parts and a menu of 21.

## What follows

- **DI recovery as declared:** not justified on the judge's own question. Its realistic
  gain there is 7–17%, failing the rule under recording bands.
- **Whether to adopt the average-guitar question** as the product's measure, and build
  DI recovery on it, is the user's decision. If adopted, a short declared listening
  check comes first: does the ear agree that the average-guitar render of the
  better-scored preset sounds closer to the record?

**Storage note, 2026-10-07.** The robustness renders (19 GB of float WAV) were deleted
to free disk. The results, the distances and the degraded or rebuilt DIs
(`~/ndsp-presets/learn/di-robust/{result.json, avg-yardstick-distances.json, di/}`)
are kept. The renders can be regenerated with `learn/di_robustness.py render`.
