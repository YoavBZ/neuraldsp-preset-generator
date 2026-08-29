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
tone; `--excerpt` selects the most continuously active window of that length from
a longer file and records its exact start and end, or the user can supply a clipped
section. A long file does not multiply render cost, but averaging clean, rhythm and
lead sections together produces a target that is none of them.

Fingerprint the reference before spending a render budget:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/fingerprint.py" REFERENCE.wav \
  --regime separated_stem --text
```

Report the regime, confidence, duration, channel count, level, spectral tilt and
roll-off, dynamics, delay/reverb measurements, harmonic confidence, and every
caveat. A missing measurement is not zero.

## 2. Choose topology from evidence

Measurement moves values; it does not identify an artist's rig. When the request
names a song or artist, research the recorded amp, cabinet, microphone and effects
with reliable sources. Use that evidence and the pack's `tone.md` to choose the
template, amp/channel and discrete topology before matching. Keep source links.

Do not enumerate switches or selectors casually. Enumeration divides the budget
among complete inner searches, and M5 did not demonstrate an accuracy benefit on
the real backend. If trying a discrete control is material, run
`--list-enumerable`, explain the budget product, and name the uncertainty.

## 3. Choose the renderer and probe

Use `--renderer swift` when macOS has the licensed Audio Unit installed. Its
numbers are facts about that plugin version, but the reused instance reports
`reproducible=false`; preserve that warning beside every reported number.

Use `--renderer synthetic` when the plugin is unavailable. It completes the full
workflow without the plugin, but its scores describe a Python approximation of
the topology, not Neural DSP's processing.

Use the user's own DI as `--probe-di` when available. Without one, omit the flag;
the tool uses a six-second sequence of decaying white-noise bursts and records that
limitation. It is transient and aperiodic, not a played or pitched guitar part.
For `paired_di`, the exact DI is mandatory. A residual-weighted paired run must
use the complete DI and reamp: omit `--excerpt` or pass `--excerpt 0`; a partial
statistical fingerprint cannot be combined with a full-performance waveform
residual.

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
`paired_di` run, export one blind mobile-friendly file directly from the
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
fresh candidate render as its own scored trial. That last step matters on a stateful
plugin: the heard waveform, not an earlier observation of the same settings, receives
the verdict. The blind key stays separate. Do not open it until the listener answers
both questions independently:

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
