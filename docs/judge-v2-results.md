# Judge v2 (a fixed band set): re-scoring results

Run 2026-10-10 as declared in [judge-v2-plan.md](judge-v2-plan.md) (plan and code
committed 13:33:33, scores finished at 14:10). Reported only: adoption waits for the
heavy-tone listening check. An independent reviewer re-derived every figure and audited
the code (`tmp/trim-fixed-review.md`, local).

## Numbers

Fixed-level measure, both halves, the band-clustered 90% interval, current judge →
judge v2:

| comparison | current judge | judge v2 | 90% interval (v2) |
|---|---|---|---|
| 3 kHz cut vs leave-band-out fixed preset | −0.143 | **−0.193** | −0.327 to −0.058 |
| uncut rebuilt DI vs that fixed preset | −0.073 | −0.146 | −0.315 to +0.022 |
| 3 kHz cut vs uncut | −0.070 | −0.046 | −0.091 to −0.002 |
| oracle vs that fixed preset | −0.260 | −0.320 | −0.481 to −0.158 |
| that fixed preset vs clean template | −0.297 | −0.229 | −0.477 to +0.020 |

Picks that change between the two judges, of 198: 40 for the cut chooser, 49 for the
oracle, 52 for the uncut rebuilt DI, and 86 for the fixed preset.

## What it shows, and an artefact

- **The code does what was declared.** The same 55 bands (87 Hz to 9.66 kHz) for every
  part, candidate and frame size; the default judge unchanged, bit for bit.
- **About half of v2's extra strength is an artefact of the masking floor.** In the
  treble bands v2 adds, the recording sits at its per-frame floor (40 dB under the
  frame's loudest band) in about 43% of frames. There, a darker candidate costs nothing
  and a brighter one is penalised.
  - **The reviewer's check,** with the floor turned off: the cut vs the fixed preset
    goes from −0.102 to −0.126, rather than from −0.143 to −0.193.
  - **The template's apparent change** exists only with the floor.
- **The rest is real.** On an unfloored spectrum, the fixed preset's picks are too
  bright: +4.8 dB mean in 2.5–10 kHz, relative to 200 Hz–2 kHz. The cut chooser's are
  about level, and v2's gain follows that gap (Spearman 0.34).

## Next for the judge

- **Before any adoption,** v2 needs a symmetric floor in the added bands, so it neither
  forgives darkness nor double-counts brightness.
- **The listening check** should include cases where a pick is darker than the record.
  The built check doesn't target them, so this is noted for the next listening round.
