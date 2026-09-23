---
name: match
description: >-
  Match an existing Neural DSP preset to supplied reference audio by measuring
  the recording, calculating invertible controls, searching the rest, and
  presenting a shortlist before writing. Use when someone supplies or points to
  audio and asks to match, copy, recreate, approximate, or get closer to its
  guitar tone, including a DI/reamp pair, isolated or source-separated stem, or
  full mix. Use generate instead when there is no audio reference.
allowed-tools: Read, Glob, Grep, Bash, WebSearch, WebFetch
---

# Match a recording

Measure a recording, match a preset to it, and show the evidence before writing.
Read [preset-spec.md](../../reference/preset-spec.md) before applying the result.

## 1. Inspect the template and classify the reference

Run `show.py` on the template first. Detect the pack from its header and note the
live amp or channel, `tone_knowledge`, and `learned_notes` paths.

Choose the most conservative true reference regime:

- `paired_di` (confidence 1.0): the reference is a reamp of the exact
  `--probe-di` performance. Use `paired-v1` only here.
- `isolated_stem` (0.85): an original multitrack guitar stem.
- `separated_stem` (0.55): guitar extracted from a mix by source separation.
- `mix` (0.35): a finished mix containing other instruments and mastering.
- `probe` (1.0): a controlled render of a known chain, for validation.

Do not call two different performances paired. If provenance is unclear, choose
the lower-confidence regime and say why. Prefer a short section with one stable
tone; `--excerpt` selects a window of that length from a longer file and records
its exact start and end, or the user can supply a clipped section. A long file
does not multiply render cost, but averaging clean, rhythm and lead sections
together produces a target that is none of them.

Fingerprint the reference before spending a render budget — any common audio
format, mp3 included:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/fingerprint.py" REFERENCE.wav \
  --regime separated_stem --text
```

**Then check the window actually holds the part, before spending anything on
it.** `--excerpt` ranks by broadband activity, which on a dense master ranks
nothing and returns the start of the file. A budget spent against the wrong
twenty seconds buys a careful fit to the wrong instrument, and every score in the
report will look normal. Re-measure with `--excerpt-start SECONDS` when you see
any of:

- `excerpt_policy: activity_tie` — several windows scored the same and this is
  the earliest of them, so confirm it holds the part
- a clamped or ignored `--excerpt-start` — the window you named was not the
  window measured
- a "does not look like a guitar" caveat — centroid under 250 Hz or a −6 dB
  extent under 500 Hz

[reading-a-reference.md](../../reference/reading-a-reference.md) has both checks,
what each regime's confidence buys, and which bands of a `mix` or `separated_stem`
measurement are the guitar rather than the rhythm section.

Report the regime, confidence, duration, channel count, level, spectral tilt and
roll-off, dynamics, delay/reverb measurements, harmonic confidence, and every
caveat. A missing measurement is not zero.

## 2. Choose topology from evidence

Measurement moves values; it does not identify an artist's rig. When the request
names a song or artist, research the recorded amp, cabinet, microphone and effects
with reliable sources. Use that evidence and the pack's `tone.md` to choose the
template, amp/channel and discrete topology before matching. Keep source links.

### Response atlases are not a starting point yet

`show.py` lists any response atlas the pack ships: one amp's measured responses
at 128 or 1,024 sampled settings, which a query tool searches for the settings
nearest a reference without rendering anything. **Do not start a match from
one.** Start from the template, as the rest of this skill describes. Two
reasons:

- **They were measured with a noise probe, not a guitar.** Every committed atlas
  stores a synthetic noise-burst sequence played through the amp, and its gates
  were measured on that same probe. Against held-out settings rendered from a
  played guitar DI — which is what a reference is — the entry a lookup picks
  beat the amp's neutral settings on 27 or 28 of 48: it helped on SW50R
  (11 of 16), was about even on Tone King's rhythm channel (9 or 10 of 16,
  varying between runs), and hurt on PR12 (7 of 16, further away than neutral
  on average). That is one played passage per amp, and AC20, Tone King's lead
  channel and the 128-point pilots were not measured on a guitar at all.
- **A search started from one finished worse.** With the same 300-render
  budget, SW50R searches started at the atlas's nearest entry ended further from
  targets rendered from a played DI than searches started at neutral settings —
  0.609 against 0.449, closer on only 3 of 12 — although the atlas entry started
  closer on 8 of them. One amp, one played passage, twelve targets. On the noise
  probe its gates were measured on, the same comparison leaned the other way
  (9 of 12, not significant at that size).

If the user asks for an atlas start anyway, this is the query. It writes ordinary
specs; apply one with `apply_spec.py` and pass the result to `match_preset.py` as
`--template`:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/query_response_atlas.py" \
  --atlas "${CLAUDE_PLUGIN_ROOT}/packs/morgan/response_atlas_pr12_1024.json" \
  --reference REFERENCE.wav --reference-mode separated_stem --out-dir RUN_DIR
```

Report the result as an experiment, and keep six more limits in view:

- **One amp or channel each, one fixed topology.** Morgan ships atlases for PR12,
  SW50R and AC20; Tone King for its rhythm and lead channels. Each has its cabinet
  and microphones fixed and its pedals and rack effects bypassed. **The amp's own
  spring reverb is not bypassed — it is one of the swept controls**, so an atlas
  start can carry a lot of reverb; check it and set it yourself if the part is
  dry.
  Pick the one whose `amp` matches the amp or channel you chose, at the larger
  `sample_count`; `show.py` prints both. They say nothing about a part that needs
  any of those effects.
- **Switches are pinned, never swept.** Morgan's topologies are the bundled
  example with only `selectedAmp` changed; Tone King's are the pack's own neutral
  seed, with the attenuator at 0 dB and a Dynamic 57 on both cabinets. Every spec
  an atlas produces asserts those positions. The ones that move the most tone:
  AC20 pins `ac20BassTreble` on, a measured **−15.6 dB at 60 Hz**, and
  `ac20Bright` on; SW50R pins `sw50rTrebleBoost` on, +2.5 dB from 400 Hz to 4 kHz.
  If the part needs any of those the other way, an atlas start is working against
  you and no refinement inside the atlas can move it — set the switch yourself
  after applying the spec.
- **AC20's atlas is built one plugin process per render.** On a reused
  instance AC20's output depends on what was rendered before it, by up to ~0.1,
  so its atlas was rebuilt with `--process-policy fresh` and carries no render
  history. A search on AC20 needs the same policy — see step 3. PR12 and SW50R
  are barely affected.
- **A start, not an answer.** The stored settings are a place to search from.
  Say so when reporting; a nearest-neighbour hit is not a match.
- **Do not expect it to fit a full `mix`.** Every stored response is the noise
  probe through this one amp. A mix is a guitar plus bass, drums, keys and a
  master chain, so the nearest entry is the nearest of a set containing nothing
  like the target. **The out-of-range list is not a reliable tell here**: on a
  mastered mix the tool can report every compared feature inside its sampled
  range and still be nowhere near. Query an atlas for `paired_di`,
  `isolated_stem` or `separated_stem`; for a `mix`, fix the excerpt and the
  regime first.
- **Not an achievability oracle.** The file carries `achievable_ranges`, and
  those are one finite atlas's observed range on the noise probe, not limits on
  the plugin — and a played guitar has its own spectrum, so a reference landing
  inside or outside them says little. Do not tell anyone "this amp cannot get
  darker than X".

Everything an atlas reports inherits its backend's `reproducible` flag: `false`
for every atlas built on a reused plugin instance, `true` for AC20's, which was
rebuilt one process per render.

Do not enumerate switches or selectors casually. Enumeration divides the budget
among complete inner searches, and M5 did not demonstrate an accuracy benefit on
the real backend. If trying a discrete control is material, run
`--list-enumerable`, explain the budget product, and name the uncertainty.

## 3. Choose the renderer and probe

Use `--renderer swift` when macOS has the licensed Audio Unit installed. Its
numbers are facts about that plugin version, but the reused instance reports
`reproducible=false`; preserve that warning beside every reported number.

**When matching Morgan's AC20, pass `--process-policy fresh`.** A reused
instance's AC20 output depends on what it rendered before, so the same candidate
scores differently along different search paths. Fresh starts one plugin process
per render — roughly 7× slower (about 2 s each against 0.3 s reused, per the
renderer's own measurements), and the only thing that removes it. Other amps
and Tone King do not need it; Tone King's variation is per-render noise, which
the replicated shortlist scoring already handles.

Use `--renderer synthetic` when the plugin is unavailable. It completes the full
workflow without the plugin, but its scores describe a Python approximation of
the topology, not Neural DSP's processing.

Use the user's own DI as `--probe-di` when available, and ask for one before
matching without it. Without one, omit the flag; the tool uses a six-second
sequence of decaying white-noise bursts and records that limitation. It is
transient and aperiodic, not a played or pitched guitar part, and it is 6–10 dB
louder than the two played DIs it has been measured against, so it drives the amp
harder. Every candidate is then noise through the amp compared with a guitar —
the same mismatch that made atlas lookups unreliable above. What that costs a
search has not been measured, and a no-DI run's own scores are noise-against-guitar
distances, so a falling score is not evidence the tone got closer. Report a match
made without a DI as weaker evidence than one rendered from the user's playing.
For `paired_di`, the exact DI is mandatory. A residual-weighted paired run must
use the complete DI and reamp: omit `--excerpt` or pass `--excerpt 0`; a partial
statistical fingerprint cannot be combined with a full-performance waveform
residual.

For a controlled preset-recovery experiment, use `${CLAUDE_PLUGIN_ROOT}/scripts/render_paired_reference.py`
with `--preset`, `--probe-di`, `--out`, `--pack`, and `--renderer`. Pass its
`OUT.wav.paired.json` sidecar to `match_preset.py --paired-provenance` alongside
`--reference-mode paired_di` and the same DI. The sidecar records the actual render
inputs; a regime label alone is an assertion of pairing. A supplied WAV may still
be a synthetic noise probe: check its source record before using it for guitar
listening. Use a verified played DI for listening verdicts.

## 4. Match and read the compact summary

Use one output directory per run. Start with a 300-render budget unless the user
asks for a quicker exploratory pass:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/match_preset.py" \
  --template TEMPLATE.xml \
  --reference REFERENCE.wav --reference-mode separated_stem \
  --probe-di PROBE.wav --loss-profile unpaired-v1 \
  --pack morgan --amp sw50r --renderer synthetic \
  --budget 300 --shortlist 3 --out-dir RUN_DIR
```

`--amp` names the signal path being matched: a Morgan amp (`sw50r`) or a Tone
King channel (`lead`, `rhythm`), with the plugin's own display label accepted
too. It is applied to the template before the first render, so the path it names
is the one measured, inverted and searched. Omit it and the template's selector
decides. Both packs invert; use `--no-invert` only to measure what the search
alone does from the template.

Read `RUN_DIR/summary.json`, not the SVG-heavy HTML, to prepare the response. Also
give the user `RUN_DIR/report.html` for the full plots. Surface all of the following:

- reference regime and confidence;
- exact measured reference start and end from `reference.excerpt`;
- renderer, plugin version, and reproducibility;
- which controls were calculated by inversion, which were searched, and which
  were frozen by the sensitivity screen — with `sensitivity_floor_observations`,
  because a floor measured from repeated seed renders on a non-reproducible
  backend is evidence and a single-render floor is the default;
- every shortlisted score, worst ±6 dB score, named objective vector, and
  plain-language differences between candidates — quote
  `reference_level_score`, not `score`, and check `input_level_observations` for
  the level you are quoting, since a score that averages three renders and a score
  from one are different kinds of number. The run says outright when two candidates
  are closer together than their scores can resolve; pass that on rather than
  presenting the order as a finding;
- every caveat, especially synthetic probe use, low harmonic confidence,
  separation artefacts, absent measured EQ data, and unverified pack paths.

Lower distance is evidence, not a listening verdict. Ask the user to audition the
shortlist, particularly when candidates trade timbre against dynamics or ambience.

## 5. Preview, then write

The winner is a spec, not a preset. Always dry-run it and show the complete change
list before writing:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/apply_spec.py" \
  --template TEMPLATE.xml --spec RUN_DIR/match-1.json \
  --out MATCHED.xml --dry-run
```

Only drop `--dry-run` after approval. Do not overwrite the template. Preserve its
custom IR unless the user explicitly asks for portability; stripping an IR changes
the matched topology. Verify the written preset with `show.py`, then follow
[installing.md](../../reference/installing.md).

## 6. Audition at equal loudness, then record the result

Do not use raw, unequal-level renders to decide which tone is closer. Preserve them
for the separate question of whether the preset's output level is right. For a
`paired_di` run with validated `--paired-provenance`, export one blind mobile-friendly file directly from the
completed run. It renders the starting template and selected candidate through the
exact probe DI, then delegates static LUFS matching, randomisation and the
Reference → A → B montage to `build_rab_audition.py`:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/export_match_audition.py" \
  --run-dir RUN_DIR --candidate 1 --probe-di PROBE_DI.wav
```

The tool verifies the effective starting settings (including an in-memory `--amp`
selection), candidate trial, exact reference excerpt and renderer/plugin build. It
refuses changed source files and source/output aliases even with `--force`, writes
untouched template/candidate renders under its private raw directory, and writes the
fresh candidate render as its own scored trial under the search's exact post-inversion
recipe. That last step matters on a stateful plugin: the heard waveform, not an
earlier observation of the same settings, receives the verdict. The complete audition
trial is hashed into the blind key, which stays separate. Do not open it until the
listener answers both questions independently:

1. Which is closer to the reference: A, B, or indistinguishable?
2. Which do you prefer: A, B, or indistinguishable?

Overall loudness is allowed to affect neither answer here. If output level needs
judgment, play the untouched raw renders afterward and record that separately.

After the user listens, record the blind label rather than manually opening and
translating the key. The logger verifies the audition file's SHA-256, resolves the
label only after the answer is supplied, then revalidates the run, trial, summary,
spec, settings, renderer and excerpt before attaching the database verdict and
learned note. Closeness and preference remain separate inputs:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/log_blind_verdict.py" \
  --key RUN_DIR/audition-candidate-1/audition.flac.key.json \
  --choice A --prefer B --listener LISTENER \
  --comment "the low mids are still too thick"
```

`--choice` is the closer blind label: `A`, `B`, or `indistinguishable`. `--prefer`
uses the same labels and is optional; the learned note records it separately from
closeness. Pass the same `--data-dir` used for the preset library when one was used.
Other regimes, including `probe`, do not prove that the reference and DI are the
same performance; export them only with an explicit `--allow-unpaired` limitation.
The appended note includes:

- reference SHA-256, regime and confidence;
- renderer, plugin version, loss profile, starting score and chosen objective vector;
- the chosen candidate's parameter changes, and up to five bands of its
  `fingerprint_delta` — the largest deviations among the bands within 50 dB of the
  target's own peak, so a band buried in the noise floor cannot outrank an audible
  one. The full array stays in the run's `summary.json`, because this file is read
  whole by the generate and edit skills;
- which candidate was closer, plus preference and any pushback in the comment, such
  as "closer candidate; prefer template because it is less harsh" or "delay is right
  but the low mids are too thick".

Keep the entry concise. Never copy the user's audio into the plugin or commit the
local run database, report, summary, generated preset, or learned notes.
