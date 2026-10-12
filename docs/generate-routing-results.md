# Does `generate` choose the right starting point? Results

Run 2026-10-12 as declared in [generate-routing-plan.md](generate-routing-plan.md)
(committed before any agent ran); part list in `generate-routing-parts.json`, run map
in `generate-routing-runs.json`, numbers in `generate-routing-results.json`, code in
`research/generate_routing.py`; part 2 in `generate-edits-results.json` and
`generate-edits-summary.json`.

## Verdict: routing costs

By the declared rule, `generate`'s class choice costs: its regret, paired against a
router that knows each part's label, is +0.114 (90% band bootstrap +0.060 to +0.173,
15 bands, 34 clean and crunch parts), above the 0.05 bar with a lower bound above 0.
The declared action follows: when `generate` routes a part away from clean, the
listening page also offers the neighbouring class's starting preset. Offering two
would have cut the regret to 0.009 (0 to 0.028).

## Part 2, research edits: undecided

The research's tonal edits (gain, drive, EQ, bright, cab) against the same start left
alone, on every scored clean and crunch part whatever its route, through the part's
own DI. Each agent's recorded `apply_spec.py` command was replayed with only the start
swapped to the leave-band-out preset. The renders reproduced the stored scores first
(worst |Δ log| 0.00012 against the declared 0.005).

| reading | mean log ratio | 90% interval | parts better / worse |
|---|---|---|---|
| **tonal edits against dry** (decides) | +0.014 | −0.008 to +0.036 | 12 / 22 |
| effects on top (report only) | +0.001 | −0.003 to +0.005 | |
| tonal, rows whose start is the shipped one (sensitivity) | −0.002 | −0.023 to +0.018 | |
| tonal, correctly routed rows only (secondary) | +0.040 | +0.007 to +0.078 | |

- **Undecided by the declared rule:** no change to `generate` step 4. The edits lean
  slightly worse than leaving the start alone, and help on about a third of parts.
- **The secondary reading excludes 0,** but it selects rows on the same halves, which
  the plan declared would favour the dry arm; it does not decide.
- **Effects** (reverb, delay) barely move the judge against a dry amp track, as the
  plan expected; whether they suit the song is a question for the ear.

## Part 1 numbers

Regret is the log ratio of the routed class's dry starting preset to the best class's,
on clean against not-clean (a crunch-or-heavier mix-up costs nothing here), per part
averaged over the three amps, band-weighted.

| router | regret | 90% interval | rows over 0.15 (of 102) |
|---|---|---|---|
| `generate` (the agent) | 0.135 | 0.082 to 0.191 | 25 |
| the label (ceiling) | 0.020 | 0.002 to 0.044 | 4 |
| always clean (floor) | 0.105 | 0.038 to 0.177 | 29 |
| the one-question proxy | 0.110 | 0.055 to 0.172 | 26 |
| `generate`, plus the neighbouring class | 0.009 | 0 to 0.028 | |

- **`generate` did no better than always choosing clean** (0.135 against 0.105; the
  intervals overlap, so not shown to be worse either).
- **The error is one-sided: clean parts sent to crunch.** Of 22 scored clean parts, 12
  were routed clean and 9 crunch (one heavier). Each of those costs about 0.3 by the
  judge, in the clean-to-crunch range listening validated. Crunch parts were routed
  crunch (5) or heavier (7); crunch against heavier is report only.
- **Why, from the agents' reasons:** they read the excerpt's measurement (noise-like
  1–4 kHz, low harmonic-to-noise ratio) as drive. On an unmastered sum of a band's
  tracks that measures the whole mix, cymbals and distorted bass included, not the
  guitar ([reading a reference](../reference/reading-a-reference.md) already warns that
  a mix's extremes are not the guitar).
- **The cheap proxy** (title, artist, the measurement, web search, one word) agreed
  with the full skill on 38 of 50 parts and did about as well. A later re-check can use
  it.
- **Secondary truth** (the shipped starting presets instead of leave-band-out ones):
  the same verdict, +0.119 (+0.067 to +0.176).

## Blinding and audit

Each of the 49 routing runs was a fresh, sandboxed `claude -p` session in a neutral
folder, with a scrubbed copy of the plugin (no `docs/`, `research/`, `learn/`,
`tests/`), its own empty data folder, file reads of the project's data, repository and
session scratch space denied (checked by a probe before the runs), and messaging tools
disabled. Every tool call in every transcript was audited for the project's data
paths, repository and GitHub page: none asked for them. Several found public
Cambridge-MT pages about their songs, which a user could do too. One part
(telefunken-Honey-GTR) has no scored half B and is left out; two Wickerman parts
playing at once with different labels were not routable from the input.

## What this cannot show

- The "songs" were unmastered sums of each session's tracks, 10 s long, by obscure
  bands: harder than most users' songs, where research finds the rig.
- The judge is validated by ear for clear clean-to-crunch differences, which is what
  decided here; crunch against heavier is not decided.
- Development parts, used many times before; a description, not a confirmation.
- The plan's reviewer saw summary figures of the truth before the runs (declared in
  the plan); the agents could not.
