# Judge v3 (one floor from both sides, in hearing's units): results

Run 2026-10-10 as declared in [judge-v3-plan.md](judge-v3-plan.md), with its amendment.
The plan was committed at `7393b93` and the amendment at `fc87ca0`. Scoring ran 20:06–20:14
on stored development renders only (CPU, no plugin renders). Report only: adoption waits
for the user's listening calibration. No independent review has been run yet.

## Against the specification

**v3 holds all 18 properties of the [judge specification](judge-spec.md):** the 16
synthetic ones and the stored-render ones. The current judge breaks six, and v2 four.

| Stored-render check | Current judge | v2 | v3 |
|---|---|---|---|
| Ill Fate 1's treble against The Well 1's (+3 dB at 1.6 kHz) | 0.000 vs 0.88 | 0.03 vs 0.81 | **0.82 vs 0.83** |
| +3 dB at 1.6 kHz, least over the 33 recordings | 0.000 | 0.03 | **0.57** |
| ±12 dB above 5 kHz, median ratio of costs | 1.06 | 1.54 | **1.00** |
| Half A vs half B, median ρ over 99 menus (10th percentile) | 0.984 (0.826) | 0.988 (0.766) | **0.989 (0.828)** |
| Same winner on both halves | 70 of 99 | 70 | 73 |

- **The stored v3 file reproduces from the audio.**
- **The default path is unchanged bit for bit:** 648 stored distances recompute
  exactly.
- **No window is refused,** in any kind.

## The standing comparisons

Fixed-level measure, both halves, part-weighted mean log ratio, with the band-clustered
90% interval for v3. Negative means the first is closer.

| Comparison | Current judge | v2 | **v3** | 90% interval (v3) |
|---|---|---|---|---|
| 3 kHz cut vs uncut rebuilt DI | −0.070 | −0.046 | **−0.027** | −0.074 to +0.021 |
| uncut rebuilt DI vs leave-band-out fixed preset | −0.073 | −0.146 | **−0.082** | −0.193 to +0.028 |
| 3 kHz cut vs that fixed preset | −0.143 | −0.193 | **−0.109** | −0.214 to −0.004 |
| oracle vs that fixed preset | −0.260 | −0.320 | **−0.256** | −0.363 to −0.149 |
| oracle vs uncut rebuilt DI | −0.186 | −0.173 | **−0.174** | −0.214 to −0.134 |
| fixed preset vs clean template | −0.297 | −0.229 | **−0.369** | −0.586 to −0.152 |

The tonal and temporal parts (v3) keep the signs they have under the current judge:

| Comparison | Tonal: current / v3 | Temporal: current / v3 |
|---|---|---|
| 3 kHz cut vs uncut | −0.048 / −0.009 | −0.086 / −0.073 |
| uncut vs fixed preset | −0.209 / −0.189 | +0.109 / +0.095 |
| 3 kHz cut vs fixed preset | −0.257 / −0.198 | +0.023 / +0.022 |
| oracle vs fixed preset | −0.333 / −0.309 | −0.134 / −0.139 |
| fixed preset vs template | −0.267 / −0.334 | −0.395 / −0.458 |

**Picks that change, of 198 part × amp × direction cells:**

| Chooser | Current judge → v3 | v2 → v3 | Current → v2, for reference |
|---|---|---|---|
| 3 kHz cut | 100 | 97 | 40 |
| oracle | 97 | 78 | 49 |
| uncut rebuilt DI | 100 | 80 | 52 |
| leave-band-out fixed preset | 119 | 149 | 86 |

**Ill Fate's oracle winners** (half B; treble 2.5–10 kHz against 200 Hz–2 kHz,
relative to the recording, unfloored):

| Part | Current judge | v2 | v3 |
|---|---|---|---|
| Ill Fate 1 | +35 / +19 / +24 dB | +21 / +16 / +11 | +16 / +15 / +11 |
| Ill Fate 2 | +16 / +23 / +6 | +1 / +1 / +7 | +5 / 0 / +3 |
| Ill Fate 3 | +13 / +9 / +1 | 0 / −3 / −2 | −4 / −3 / −2 |

The three figures in each cell are PR12 / SW50R / AC20. On Ill Fate 1 every menu is
bright: the menu median there is about +31 dB.

## What it shows

- **v3 is the judge the specification asks for.** It hears treble on bass-heavy parts as
  on balanced ones, and judges boosts and cuts, missing and excess content, alike. It
  ranks halves as consistently as the current judge.
- **It moves magnitudes less than v2, and keeps every direction.**
  - Every standing comparison keeps its sign under all three judges.
  - v3's figures sit near the current judge's, except two. The 3 kHz cut's edge over
    the uncut rebuilt DI shrinks to −0.027, and its interval now spans zero. The fixed
    preset's edge over the template grows to −0.369.
  - **v2's extra strength against the fixed preset does not survive** (−0.193 → −0.109
    for the cut). That agrees with the review's finding that about half of it came from
    the floor forgiving darkness.
- **But it is a different judge in detail: about half the picks change** (97–119 of
  198). Many picks are near-ties (under the current judge, the best and second-best
  menu presets differ by a median 0.043), so small changes in weighting reorder them.
  Even so, a pick made under one judge is not a pick under the other. Results that rest
  on individual picks need to name the judge.
- **The cut's edge over the uncut DI** (the 3 kHz cut, adopted on the current judge's
  −0.070, interval −0.109 to −0.030) is −0.027 under v3 (−0.074 to +0.021), mostly in
  the temporal part. If v3 is adopted, that edge is inconclusive. The cut's edge over
  the fixed preset still excludes zero (−0.109, −0.214 to −0.004).

## Known limits (from the plan)

- **Hiss.** A render without the recording's hiss pays for it, and matching hiss is
  slightly rewarded. Synthetic: −50 dB hiss on a dark recording costs 1.46, and matching
  it brings a render 0.48 closer.
- **Content near the noise floor counts.** On dark clean parts (Magilla, Colour Me Red),
  a +12 dB shelf above 5 kHz costs v3 2.1 or more, where the current judge sees
  0.004. That is the property asked for, but whether the ear hears it there is untested.
- **The masking model and its constants** (40 dB, 10/25 dB per Bark, 90 dB SPL) are not
  validated by listening.

## Next

- **Adoption is the user's call, after the listening calibration.** The built heavy-tone
  check doesn't target where v3 and the current judge disagree. A calibration for v3
  should include:
  - pairs from the cells where their picks differ;
  - darker-than-the-record candidates;
  - treble excess on dark parts.
- **An independent review** should re-derive these figures before any decision rests on
  them.
- **v3 replaces v2 as the candidate judge** (as the plan declared), since its
  stored-render checks pass.
