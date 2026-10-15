# Label table and stems for every clean and crunch development part: plan (ML plan 2026-10, step 4)

Declared 2026-10-15, before any render. It is step 4 of
[`research/ml-plan-2026-10.md`](research/ml-plan-2026-10.md). Development data only. It is a
data-building step with no gate; nothing is read as a result.

## Why

Step 3's parts are SNR-selected and few. Step 7 (and arm B's fine-tuning) needs every classed
clean and crunch development part, with:
- its menu scored by the judge, through the measure DI and with `isolate`;
- a guitar stem made **without** the SNR filter.

## The parts (derived and declared here)

The ML plan's "65" was an estimate. Derived from the catalogues, a part is **classed** if it is a
development part with a waveform-passing DI/amp pair and a gain class:
- **Sets 1–2:** the 43 development parts in `docs/validation-lags.json`. They are classed by the
  set-3 classifier's rule (`classify.py` on `gainmeasure.measures` of the reference and DI at the
  stored lag), as `songs_check.prep` did: 37 clean and 6 crunch, 13 bands.
- **Set 3:** the 33 development parts, with their catalogue class: 5 clean, 11 crunch and 17
  high-gain.

That is **76 classed**, and **59 clean or crunch**. The list is written to
`docs/label-table-parts.json` before any render, and the class of every part is committed.

## What

1. **The menu:** each part's measure DI (`knob_ceiling.measure_di`, equal to
   `confirm_run.build_di("measfix")`) through the 111 dry menu presets on the three amps, with
   `knob_ceiling.Renderer` (`isolate=True`).
   - About 59 × 111 ≈ 6.5k renders, on 3 reused processes alongside step 1's training.
   - Each preset is scored on halves A and B by the judge, `flat` and v3 (`JUDGE_V3`), at the
     part's judge lag.
   - Distances only are kept, plus each part's best render per amp (flat) as a 16-bit FLAC.
2. **The stems,** with no SNR filter: htdemucs_6s via `learn/separate.py` (step 0), on the
   instrumental context.
   - 44 of the 59 already have stems from the earlier runs, made with the same settings
     (`learn/poc/stems`, `learn/set3/stems`). These are reused, and their `usable` flags are
     ignored.
   - The other 15 are separated on the **CPU** (`DEVICE=cpu`), since the GPU belongs to step 1.

## Output

`~/ndsp-presets/learn/label-table/<part>/menu.json` holds `{amp: {preset: {flat: {A, B}, v3:
{A, B}}}}`. There is also an index `parts.json` with each part's band, class, set, fold
(`k3_folds()` where defined) and stem path.

## Checks

- **The repeat check:** for 3 parts, 5 presets are rendered twice in different orders. They must
  agree within 1e-3 (log).
- **Against the existing scores:** for the parts that have them (`songs-check`, `gap-split`), the
  `flat` distances are compared. They must agree within 0.005 (log) except on parts quiet in a half
  ([render-order-audit.md](render-order-audit.md)). Differences are reported, not fixed.
- The ledger entry `label-table` lists the parts; there is no gate.

## Order

1. Plan and parts list, committed.
2. Message the product session.
3. Renders and separations.
4. A spot audit (the checks above).
5. `docs/label-table-results.md`, which is short: counts, timings and check results.
