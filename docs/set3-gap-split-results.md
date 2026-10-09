# Where the rebuilt DI loses the preset choice: results (set 3, development)

Run 2026-10-10 as declared in [set3-gap-split-plan.md](set3-gap-split-plan.md)
(commit 3d2a14d, before any render). 10,989 new renders: three DI variants × 33 parts ×
111 menu presets. An independent reviewer re-derived every number with their own code,
spot-checked distances on stored renders, and found no bias in the harness
(`tmp/gap-split-review.md`, local).

**Outcome under the declared rule: the rest explains the gap.** Neither level, long-term
balance nor the activity mask does. Next step 4 goes ahead as planned: improve the
network itself.

## Numbers

Pooled over the three amps on recording bands. Each line is a step's mean log ratio of
the pick's half-B distance; negative means closer.

| step | mean | wins / ties / losses |
|---|---|---|
| **the gap:** rebuilt DI → true DI (oracle) | **−0.207** | 59 / 32 / 5 |
| level: the rebuilt DI at the true DI's loudness | −0.026 (13% of the gap) | 14 / 76 / 6 |
| balance: then re-equalised to the true DI's long-term spectrum | **+0.101** (worse) | 24 / 31 / 41 |
| the rest: from the level-matched rebuilt DI to the oracle | **−0.181 (87%)** | 57 / 36 / 3 |
| mask: the true DI's activity instead of the rebuilt one's | 0.000 | 0 / 96 / 0 |
| level with the true waveform (true DI at −22.9 LUFS → oracle) | −0.009 | 16 / 80 / 3 |

- **Union bands agree:** gap −0.200, level −0.037, balance +0.102, rest −0.163, mask 0.
- **Each amp agrees.** The gap is −0.24 (PR12), −0.16 (SW50R) and −0.22 (AC20).
- **The order of the steps matters.** The plan's own split measures the rest from the
  re-equalised DI (−0.282, 136% of the gap). That figure absorbs the re-equalising's
  harm, so the table reports the rest from the level-matched DI, the honest share.
- **One part is refused for every rebuilt-DI variant:** Colour Me Red ElecGtr03 (51%
  pauses), so n is 96 parts × amps, not 99. With the true DI's mask it scores; the mask
  changes refusals but never a pick (192 of 192 picks unchanged).

## What it shows

- **Level matters little, even on driven amps.** The true DIs span −46.5 to −16.8 LUFS,
  yet playing the rebuilt DI at the true level recovers only 13% of the gap. With the
  true waveform, playing it at −22.9 LUFS costs almost nothing (−0.009). This agrees
  with the clean-PR12 level check of 2026-10-07.
- **Matching the long-term spectrum hurts, and the reason is informative.** The
  re-equalising boosts 3–10 kHz by 3–7 dB. Above 3 kHz the rebuilt DI is essentially
  unrelated to the true DI: coherence is about 0.00–0.02. So the boost gets the average
  spectrum right while feeding more of the wrong signal into a driven amp. The harm
  lands on high-gain and crunch parts (SW50R +0.25 and +0.17, clean about 0).
- **The activity mask is not a lever.** The reference-proxy fallback
  (`learn/rebuilt_judge.py`) is still worth keeping for refusals.
- **What the network must improve is the waveform's detail:** dynamics, transients,
  and content above 1 kHz, where it departs most from the true DI.
- **Side note from the review:** by cross-correlation the rebuilt DI sits about 60
  samples early on the recording's timeline, while lag −52 assumes it is aligned.
  Re-scoring at the corrected lag left every recording-band pick unchanged, and changed
  2 of 96 on union bands. No effect on the conclusion.

## Also reported: the measure with the DI at a fixed level

If the measure fed its DI at −22.9 LUFS instead of the take's own level, the picks
against the clean template would be:
- **Through the rebuilt DI:** −0.35 (PR12), −0.61 (SW50R), −0.21 (AC20).
- **Through the true DI:** −0.52, −0.74 and −0.42.

The same picture as the declared measure. The level question does not change any
conclusion, so it is not put to the user.

## Next

Next step 4: the declared [network pilot](di-network-v2-plan.md), which trains longer
and adds set 3's development guitars. It runs on 2026-10-10.
