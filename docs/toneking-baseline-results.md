# Tone King starting presets for clean and crunch: results

Run 2026-10-11 under the [plan](toneking-baseline-plan.md) (reviewed before any render,
with one recorded amendment during the development render). An independent review
re-derived every number (`tmp/toneking-baseline-result-review.md`, local).

## In short

- **Clean: adopted.** Richard Henshall / **Vintage Trem**, made dry, is about 12% closer
  to the record than the plugin's own Default made dry, on held-out clean parts.
- **Crunch: adopted, on thin evidence.** Adam Christianson / **Squishy Lead**, made dry,
  is about 29% closer than a typical preset on its channel (about 20% against the driven
  ones only), on all 7 held-out crunch parts. Those come from only 3 bands.
- **Neither is a unique best:** on held-out each ties its runner-up. What is shown is that
  each beats the start an owner would otherwise use.
- **Both are on the Rhythm channel,** and ship on it.
- **Against the Morgan starting presets** of the same class, they are about even, so the
  choice between the two plugins stays a matter of voice, not closeness.

## The choice (development, 35 parts)

The rule picks, per gain class, the dry preset with the lowest median distance:

| class | preset | median distance | runner-up |
|---|---|---|---|
| clean (22 parts) | Artists/Richard Henshall/Vintage Trem | 4.158 | Spring Clean, 4.307 |
| crunch (13 parts) | Artists/Adam Christianson/Squishy Lead | 3.989 | Let 'er Rip, 4.152 |

- **Clean is stable:** the rule run without each band picks Vintage Trem in 8 of 10.
- **Crunch is not:** Squishy Lead in 3 of 6, Rough Blues Lead in 2, and another in 1.
- **Repeatability:** for 2 presets on 3 development parts, three renders of the same preset
  and DI move the distance by at most one part in a million.

## The check (held-out sets 1–2 parts, third declared use)

Mean log ratio, band-clustered 90% interval; negative is closer.

| | clean (13 parts, 8 bands) | crunch (7 parts, 3 bands) |
|---|---|---|
| **primary** | **vs Default dry: −0.127** [−0.175, −0.079], 12 of 13 closer | **vs Rhythm median: −0.340** [−0.663, −0.017], 7 of 7 closer |
| vs Default dry | (primary) | −0.480 [−0.913, −0.048] |
| vs median of driven Rhythm presets | | −0.232 [−0.423, −0.041] |
| vs the runner-up | Spring Clean: +0.001 [−0.024, +0.026] | ties Let 'er Rip and Rough Blues Lead |
| vs median of all 125 | −0.380 | −0.262 |
| vs median of "Clean" presets | −0.113 [−0.163, −0.063] | |
| vs median, rooms off | −0.373 | −0.239 |
| rank among 125 (median) | 10th | 21st |
| oracle vs chosen (headroom) | −0.191 | −0.164 |
| vs Morgan PR12 start | −0.012 | +0.021 |
| vs Morgan SW50R start | +0.021 | −0.028 |
| vs Morgan AC20 start | −0.071 | +0.014 |

**Robustness:**
- **Clean:** every leave-one-band-out interval stays below 0 (means −0.110 to −0.138);
  the band sign-flip p is 0.008.
- **Crunch:** every leave-one-band-out mean is negative, but two of the three intervals
  span 0. Forkupines holds 4 of 7 parts. The sign-flip p is 0.25, the lowest 3 bands allow.
- **Alignment:** shifting the judge lag by up to 10 samples moves a distance by at most
  0.08%.
- **The dry Default is a fair comparator:** it renders normally and is a mid-to-good clean
  preset (median rank 24 of 126 on held-out), not a strawman.

## What the two presets are, made dry

- **Vintage Trem:** a lean, near-clean Rhythm-channel tone. Volume 0.5, bass low, input
  −7 dB, a barely-on overdrive (drive 0.02), compressor and EQ off. Its tremolo, chorus and
  reverb are removed, so the name no longer describes it.
- **Squishy Lead:** a crunch rhythm sound. The Rhythm channel at full volume with the
  attenuator bypassed, pushed by the second overdrive (drive 0.3). The compressor is off,
  so nothing is "squishy", and "Lead" is only the name.

## What this means for the product

- **`generate` can start a Tone King part from a factory preset every owner has,**
  instead of requiring one of the user's own:
  - clean: Vintage Trem, made dry, on the Rhythm channel;
  - crunch: Squishy Lead, made dry, on the Rhythm channel (thin evidence: say so).
- **Made dry means:**
  - post reverb, delay and chorus off;
  - the amp's spring reverb and tremolo depth at 0;
  - the gate off (−96 dB);
  - wah off;
  - the time section on.
  - This needs a `dry/toneking` recipe in the pack. The product session owns it.
- **The channel ships with the preset.** Switching it would ship something that wasn't
  measured.

## Limits

- **Measured, not heard.** As with the Morgan starting presets, no listening check.
- **Crunch rests on 3 bands,** and its development pick was unstable.
- **On clean, Spring Clean ties Vintage Trem** on held-out, and the dry Default is a fair,
  if weaker, fallback.
- **Three factory presets were left out** (incomplete stored state): Clean Clay, Grunge
  Sludge and Lite Mud.
