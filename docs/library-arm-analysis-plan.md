# As-shipped library arm: analysis fixed before reading the final results

Written 2026-10-03, after the ground-truth audit and before any final per-part numbers were read.
Disclosure: an interim count was read on the first 13–18 parts per amp (library closer than the template
as it is on 13/18 PR12, 12/16 SW50R, 11/13 Tone King, stored v3 without level).

## Question
For each amp, without a DI: should the match deliver the search through the library probe, started from
the shipped preset (`library` arm), or the shipped preset as it is (`template`)? The noise-probe search
is not a candidate: it already lost to the template on every amp.

## Data
`benchmark_match_pipeline.py --set 2 --seed 11 --arm library` from c65a1cd, runs under
`bench-set2/runs/lib-{pr12-shipped,sw50r-shipped,tk-default,ac20-shipped}`. Template and answer are both
rendered through the part's own DI in fresh processes by the same run.

## Scoring (two readings, both reported)
- **Stored:** `v3_no_level` from each part's result.json.
- **Corrected** (the audit's fixes, applied identically to both sides):
  - `band_shape` over the bands within 30 dB of the reference's peak band only (D-H3);
  - each pair scored over the dimensions measured on both sides (D-M12);
  - Tone King: the first 1.0 s of reference and render removed before fingerprinting (D-M1, the
    fresh-process mute); Morgan scored whole.
- Level left out in both. An answer with no measurable loudness counts as a loss for its arm.

## Tests
- Part level: library closer than template on how many of the parts measured in both.
- Band level: per band (catalog `group`), the median log ratio library/template; exact two-sided
  sign-flip test over bands.

## Decision rule, per amp
- **Adopt the library search** if it is closer than the template on a majority of parts under both
  readings AND the band-level p < 0.05 under the corrected reading.
- **Not shown** if the majority holds but the band test does not: deliver the template (with its level
  set) by default, and offer the library search as an option.
- **Template** otherwise.

Secondary, informative only (cross-run): library against the shipped noise search, corrected scoring of
the stored no-DI renders.

## Second measurement, added before it ran: calculation only (the audit's gap 2)
For each amp and part, the shipped preset with the match's calculated settings applied and no search
(`search.starting_settings` of the match's summary.json), rendered through the part's DI in a fresh
process exactly as the run's own renders (`render_listening_guitar.py --preroll-s 0`):
- `calc-library`: from this run's library match;
- `calc-noise`: from the committed no-DI (noise) match of the same seed and template.
Scored with the corrected reading (and the stored reading for reference), level left out.
Comparisons: calc-library vs template (decision rule as above), calc-library vs the library search,
calc-noise vs template. Parts whose match did not record starting settings are reported, not dropped
silently.
