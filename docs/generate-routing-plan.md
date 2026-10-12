# Does `generate` choose the right starting point? Plan

Declared 2026-10-12, before any part is routed or any edit rendered. Roadmap step 6,
from an independent review of the direction: nothing measures two of `generate`'s
riskiest steps.

1. **Routing:** research and the measured excerpt put the part in a class (clean,
   crunch or heavier), and the class picks the dry starting preset.
2. **Research edits:** `generate` step 4 then changes the starting preset from the
   research.

Revised after an independent review of the first draft (the reviewer's points are
numbered R1–R10 below where they changed the design).

**Disclosure.** To check feasibility, the plan's reviewer computed the in-sample
routing truth and two reference routers from the stored distances, and reported
summary figures to the author, including the leave-band-out regret of the
perfect-label ceiling (0.020, 90% 0.002 to 0.044) and of always clean. The routing agents have not seen them and cannot (see
blinding). Nothing about the agents' routes or the edits is known.

## Parts

Development parts only; nothing from a held-out split is opened, routed or scored.
- The union of `~/ndsp-presets/learn/direc/rescore/distances.json` and
  `songs-check/distances.json`, each part counted once (12 set-3 parts are in both,
  with identical numbers), dropping parts without all nine starting presets scored on
  both halves (telefunken-Honey-GTR). Expected: 52 parts in 29 songs; clean 22 (11
  bands), crunch 13 (6 bands), high-gain 17.
- **Labels:** set 3's catalogue labels; sets 1–2 use the gain classifier's labels from
  `songs-check/prep-sets12.json` (8 of 20 at low confidence, both crunch parts among
  them). Labels are used only for the ceiling router and for reporting, never as truth.
- **Part descriptions (R7).** Before any agent runs, one neutral, label-free
  description per part is written from the multitrack's track names and arrangement
  only, of the kind a user would give ("the left guitar's verse riff, 0:42–1:02").
  Parts that cannot be told apart that way (simultaneous guitars of different classes
  with no distinguishing description) are reported as unroutable from the input, not
  scored. Double-tracked parts (Magilla's "dt") are routed once and their rows
  averaged.
- The list, the descriptions and the time ranges are committed to
  `docs/generate-routing-parts.json` before any agent runs.

## Truth (R2, R3)

The judge distance of each class's dry starting preset, from the stored scores: key
`flat|<amp>|measfix_A/B`, element 0, the mean of the two halves' log distances; rows
are part × amp, averaged over the three amps for the primary reading (R9).

- **Primary truth uses leave-band-out starting presets:** for each part, the clean and
  crunch presets are re-chosen by their own declared rules
  ([clean](clean-baseline-plan.md), [crunch](crunch-baseline-plan.md)) without that
  part's band (both rules reproduce the shipped picks on the full data). In-sample
  presets flatter the class matching each part's label. The heavier presets stay the
  shipped ones: they were chosen on another measure that these scores cannot rebuild,
  and crunch against heavier is report only. The all-shipped truth is reported as
  secondary.
- **The deciding contrast is clean against not-clean.** The judge was validated by ear
  only for clean-to-crunch differences above 0.15, and barely sees drive amount
  ([review](closeness-review-2026-10-10.md)). Crunch against heavier, and every
  high-gain row, are reported only.
- **Regret, clean against not-clean:** 0 when the routed class is in the same group as
  the best class (clean, or crunch and heavier), otherwise the routed class's distance
  minus the best class's.
- **Near-tie (R9):** a class is tied with the best if its sign against the best flips
  between the halves.

## Part 1: routing (no renders)

### Blinding (R6)

Each part is routed by a fresh headless Claude Code session (`claude -p`):
- run from a neutral empty working directory (no project memory, no CLAUDE.md);
- loading the plugin with `--plugin-dir` from a scrubbed copy of main: `skills/`,
  `scripts/`, `packs/`, `reference/`, `analysis/`, `format/`, `match/`, `samples/`
  and `.claude-plugin/` only, no `docs/`, no `research/`, no `learn/`, no `tests/`;
- given the song's mix copied to a neutral name (`song-NN.wav`, metadata stripped),
  the song title and artist, and the part description and time range;
- with its own fresh, empty data directory (`NDSP_PRESET_DATA`), since an installed
  plugin otherwise finds `~/ndsp-presets` by itself;
- with file access limited to its working directory, the scrubbed plugin and that
  data directory (`--add-dir` only those), and web search allowed. `--add-dir` limits
  Claude Code's file tools, not shell commands; Bash runs in Claude Code's sandbox
  where it can be confined to those folders, and otherwise the transcript audit
  (covering every shell command and its output) is the only safeguard, as stated with
  the results;
- with the skill's questions answered up front: pack Morgan, the given time, no
  listening page.

Afterwards every transcript is audited for paths under `~/ndsp-presets`, the
repository, `docs/validation*`, and this project's GitHub repository; any run that
touched them is excluded and reported. The "mix" here is an unmastered unity-gain
sum of the multitracks, not a finished song; that is stated with the results.

### Routers compared (R1, R8)

- **The agent** (the thing under test): its class, amp, reasons, and its spec.
- **The ceiling:** the part's label routed through the same class table.
- **The floor:** always clean.
- **A cheap proxy:** one short fixed prompt per part (title, artist, the part
  description and `fingerprint.py --regime mix --text` of the excerpt, web search
  allowed) answering only "clean, crunch or heavier", under the same blinding. If it
  agrees with the full agent on most parts, later re-checks can use it alone.

### Readings

Band-weighted primary, part-weighted beside it, 90% band bootstrap throughout (R9).
- **Regret** of each router: the routed class's preset against the best class's, on
  leave-band-out truth.
- **Costly misroutes:** rows with regret above 0.15 (the judge's validated by-ear
  margin), as a count and a share.
- **The confusion table:** label × routed class × best class, high-gain rows
  included as report-only.
- **The best-of-two bound:** the regret if the listening page offered the routed and
  the neighbouring class, the most the "offer both" action could gain (R10).

### Decision (R1)

On clean and crunch parts, clean against not-clean:
- **Routing costs:** the agent's regret minus the ceiling's, paired, is above 0.05 with
  its lower bound above 0. Then `generate` step 1 says that when the class is unclear
  from research it offers both neighbouring classes' starting presets, and the
  audition page shows them. If always clean beats the agent, that is reported plainly.
- **Routing is fine:** the agent's regret minus the ceiling's, paired, has its upper
  bound below 0.05. No change.
- Otherwise **undecided**; report it, no change.

0.05 is the median menu near-tie size, not a validated by-ear margin; the costly
misroute count (above 0.15) is reported beside it for that reason. Expected power:
the rule fires at about four to eight misroutes among 35 parts.

## Part 2: research edits (renders)

Every clean and crunch part, whatever class the agent routed to, as the product does.
Selecting correctly-routed rows on the same halves would favour a lucky dry arm, so
those rows are a secondary reading only.

### Arms (R4)

On the agent's chosen amp, starting from that class's **leave-band-out** preset (so
the start is not one selected on this part):
- **dry:** the preset with the dry recipe;
- **tonal:** dry plus the agent's tonal edits only (gain, drive, EQ, bright, cab, mic),
  with time effects stripped by re-applying the dry recipe after the spec;
- **full:** the agent's whole spec.

The agent's whole `apply_spec.py` command (template, recipes, spec) is recorded and
replayed with only `--template` swapped to the leave-band-out preset. The agent wrote
its values against the shipped preset, so rows where the two are the same preset are
reported as a sensitivity reading.

### Measurement (R5)

Through the part's own DI exactly as the stored scores were made: the `measfix`
preparation (re-equalised as stored, −22.9 LUFS, the same lag, crop and halves), the
`flat` judge. Before any arm is read, the dry arm of a shipped preset is re-rendered
through the new route (`apply_spec.py --recipe dry/<amp>`, then
`research/render_preset_panel.py`'s `preset_edits`), for at least one set-3 part and
one sets 1–2 part on all three amps, and must reproduce its stored `flat|measfix`
distance within |Δ log distance| < 0.005; a full-arm render must not be silent. If
either fails, Part 2 stops and is reported. Rendering follows `learn/songs_check.py`
(stored `di.npy` measfix DIs, `aligned_distance` over `learn/rescore.HALVES`), read
only; no ML code is changed. About 35 × 3
arms × 2 halves, about 210 renders, at most two reused processes; the ML session is
told first and nothing runs 03:00–04:15.

### Readings and decision

Decided on **tonal against dry** (time effects are scored against a dry amp track,
which charges a mix's reverb as error, so **full against tonal** is reported only):
mean log ratio, band-weighted, 90% band bootstrap, wins and losses, and by edit type
where the spec allows.
- **Edits hurt** (lower bound above 0): `generate` step 4 keeps the starting preset's
  tonal values unless research names a specific setting (a documented rig or a stated
  sound), and the change is recorded in the skill and the roadmap.
- **Edits help** (upper bound below 0): no change; recorded.
- **Undecided:** report it, no change. With about 16 bands the smallest detectable
  effect is about ±0.04 to 0.05, so undecided is a real possibility.

## What this cannot show

The judge is validated by ear only for clear clean-to-crunch PR12 differences;
crunch against heavier is reported, not decided. Development parts have been used
many times; nothing here is a confirmation. The agents route obscure multitrack songs
from unmastered sums, so their research is often thin, as a user's less-known songs
would be.
