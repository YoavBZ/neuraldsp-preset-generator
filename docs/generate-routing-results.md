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
The declared action ("when the class is unclear, offer both neighbouring classes'
starting presets") is applied in the form this data supports: when `generate` routes
a part to crunch it also writes the clean start, and when it routes heavier, the
crunch start (it cannot know when it is unclear: the misrouted agents were sure).
Offering two would have cut the regret to 0.009 (0 to 0.028), an upper bound that
assumes the better of the two is then picked by ear. The bound gives clean routes a
crunch neighbour too; the skill does that only when the class is a guess, which makes
no difference here (no crunch part was routed clean).

**Scope (a deviation from the plan).** The plan (R7) declared user-style part
descriptions from track names and arrangement. What the agents got was only the song,
the artist and the time ("the electric guitar in the excerpt starting at 2:26"), while
each mix sums every guitar in the session. So the verdict is about a user who gives
only the song and a time, and agents often routed the song rather than the part.

## Part 2, research edits: undecided

The research's tonal edits (gain, drive, EQ, bright, cab) against the same start left
alone, on every scored clean and crunch part whatever its route, through the part's
own DI. Each agent's recorded `apply_spec.py` command was replayed with only the start
swapped to the leave-band-out preset. The renders reproduced the stored scores first
(worst |Δ log| 0.00012 against the declared 0.005), and every part's dry arm
reproduced the stored score of its start (0.00014 at most).

| reading | mean log ratio | 90% interval | parts better / worse |
|---|---|---|---|
| **tonal edits against dry** (decides) | +0.014 | −0.008 to +0.036 | 12 / 22 |
| effects on top (report only) | +0.001 | −0.003 to +0.005 | |
| tonal, rows whose start is the shipped one (sensitivity) | −0.002 | −0.023 to +0.018 | |
| tonal, correctly routed rows only (secondary) | +0.040 | +0.007 to +0.078 | |

- **Undecided by the declared rule:** no change to `generate` step 4. The lean
  towards worse comes from the 12 parts whose start was swapped to the leave-band-out
  preset; where the start is the one the agent wrote its edits against, they are
  neutral (−0.002). Edits help on about a third of parts.
- **The secondary reading excludes 0,** but it selects rows on the same halves, which
  the plan declared would favour the dry arm; it does not decide.
- **Effects** (reverb, delay) barely moved the judge (+0.001), against the plan's
  expectation that a dry amp track would charge them as error; on 4 parts the agent
  added none. Whether they suit the song is a question for the ear.
- Tonal edits here include gain, drive, EQ, bright, cab and compressor recipes. The
  plan's by-edit-type reading is not reported: specs bundle several edits.

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

- **`generate` did no better than always choosing clean:** paired, +0.030 (−0.085 to
  +0.142); part-weighted −0.004. Always clean is no fix: it costs 0.25 on crunch parts.
- **The error is one-sided: clean parts sent to crunch.** Of 22 scored clean parts, 12
  were routed clean and 9 crunch (one heavier). The 10 cost a mean of 0.33
  (0 to 0.73; 8 of 10 above 0.15), in the clean-to-crunch range listening validated. Crunch parts were routed
  crunch (5) or heavier (7); crunch against heavier is report only.
- **Why, from the agents' reasons (all 10 misrouted clean parts read):** about 8
  followed the song's genre, the band or a write-up about the whole song (mix-contest
  critiques, "Mix Rescue" articles) rather than the part; about 2 led with the
  measurement, reading the mix's density or loudness as drive. On these excerpts the
  mix measurements barely separate clean from crunch parts (harmonic-to-noise ratio
  and fizz near chance, AUC 0.43 and 0.48; crest weakly, 0.79; computed in the
  independent re-derivation from the runs' fingerprints, not by the script).
- **Run to run, agents are unstable:** two near-identical Magilla excerpts 1 s apart
  were routed clean and heavier. Each part had one run. Two runs researched the wrong
  artist of the same name (no cost here).
- **Near-ties** (the declared reading): 1 of 31 misrouted rows; it changes nothing.
- **Robust:** dropping any one band leaves the mean at 0.094 or more and the lower
  bound at 0.043 or more; per amp +0.15, +0.10, +0.09, each excluding 0.
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
- The sandbox that enforced the blinding broke some shell tools in every run (1 to 5
  recovered errors each).
- The plan expected 29 songs and 11 clean bands, counting the unscored Honey part;
  the scored set is 28 songs and 10 clean bands.
- The plan's reviewer saw summary figures of the truth before the runs (declared in
  the plan); the agents could not.
