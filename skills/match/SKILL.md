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
  `--probe-di` performance. Use `paired-v2` only here.
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
roll-off, dynamics, delay measurements, the RT60 estimate (not a reverb
measurement on played material — say so), harmonic confidence, and every
caveat. The harmonic figures (odd/even, HNR, fizz) are measured on one steady
note, and between two performances they did no better than chance at
picking the setting; the default `unpaired-v3` profile does not score them, so do not read
distortion character from them. A missing measurement is not zero.

## 2. Choose topology from evidence

Measurement moves values; it does not identify an artist's rig. When the request
names a song or artist, research the recorded amp, cabinet, microphone and effects
with reliable sources. Use that evidence and the pack's `tone.md` to choose the
template, amp/channel and discrete topology before matching. Keep source links.

Decide the rack reverb here, not in the match. The inversion leaves Morgan's rack
reverb as the template has it for any recording, stem or reamp: the decay it can
measure on played guitar is mostly the notes' own sustain, and a rule reading it
switched the reverb on as often for targets without one as with one. Only a
`probe` reference, rendered through the noise-burst probe, sets it. So a
template with the rack reverb on keeps it even against a dry recording: use a
template, or an edited copy of one, with `reverb/reverbActive` set the way the
evidence says, or try both with `--enumerate reverb/reverbActive`, and add
`--process-policy fresh` whenever it is on (below).

### No response atlas

Do not build or start from a response atlas (one amp's stored responses at
sampled settings). On SW50R a search started from the nearest atlas entry ended
further from played-guitar targets than one started from neutral settings (0.548
against 0.447), and an atlas built from the user's own DI ended no closer (0.479
against 0.480) after costing 128 renders to build. The research tools are
described in `docs/tone-matching-plan.md`.

Do not enumerate switches or selectors casually. Enumeration divides the budget
among complete inner searches, and no accuracy benefit from it has been shown on
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

**Pass it too when Morgan's tremolo or rack reverb is on** — `tremolo/tremoloActive`
or `reverb/reverbActive` true in the template, or switched on by `--enumerate`
or, for a `probe` reference, by the inversion (the report lists what it
calculated; if it turned one on, rerun with fresh). Not the amp's own spring reverb: its carry-over is a
short tail, at most 0.15 in the same measurements. Both carry state from one
render to the next on a reused instance, likely a modulation oscillator, so the
same settings come out differently each time and the search ranks noise:
- the tremolo's renders of one setting came out several dB apart, measured
  through the noise probe, so it needs fresh whatever the DI;
- the rack reverb's landed 0.1 to 0.6 apart through a played DI and 0.01 to 0.04
  through the noise probe, so it needs fresh when you match with a played DI.
  Only a new instance resets it; warm-up and `isolate` do not.

The cost is AC20's: about 1.5 s of plugin start added to every render on an idle
machine, far more under load.

Use `--renderer synthetic` when the plugin is unavailable. It completes the full
workflow without the plugin, but its scores describe a Python approximation of
the topology, not Neural DSP's processing.

Use the user's own DI as `--probe-di` when available, and ask for one before
matching without it — of this part if they can, which is the nearest a player can
get to the recorded take (a guess, not a measurement); otherwise of anything they
play. Against real amp recordings (14 parts on each of SW50R and Tone King's
rhythm channel, `docs/tone-matching-plan.md`), a search through the DI of the very
take the amp recorded ended about half as far as one through the DI of another
session (13 and 14 of 14 closer), and the other session's DI still beat no DI on
11 and 13 of 14. Half of those other DIs were another excerpt of the same player
and rig, and they did no better than the rest. On 43 more SW50R parts from 13
other bands the same held (43 and 39 of 43), and there another song by the same
band ended closer than another band's DI, though that was not designed to be
shown. A user's own DI of the part is a different performance from the
recording, so it lies somewhere between the first two; it was not measured.

Without a DI, omit the flag; the tool uses a six-second sequence of decaying
white-noise bursts and records that limitation. Do not substitute another probe:
on SW50R neither turning it down to a guitar's loudness nor replacing it with a
synthetic strummed guitar helped reliably. Every candidate is then noise
through the amp compared with a guitar, so a no-DI run's own scores are
noise-against-guitar distances and a falling score is not evidence the tone got
closer. Against real amp recordings a no-DI search was no better than its
starting settings on SW50R and ended further from the recording than them on
Tone King on all 14 parts, and on 12 of 14 with loudness set aside; on 43 more
SW50R recordings the shipped no-DI match ended further from the recording than
the unsearched template on 28, with loudness set aside, while a match through
the same take's DI (a reamp, the best case) was closer on all 43 — so without a
DI, show the starting preset beside the searched one and do not present the
search as an improvement. Tell the user a match made without a DI is at best a
starting point, not a measured match, and that a DI of their playing would
change that. Without a DI the tool sets each passing candidate's output gain
through a synthetic guitar rather than the noise probe
(`search.guitar_check.level_trim` in `summary.json`); on 43 SW50R recordings
that brought answers from a median of 13 LU over their recordings to 4 over
(3 under to 11 over), so tell the user to expect it a little loud and to trim it
by ear, and report the caveat that names
any candidate whose level was left as the search set it.

A no-DI match can also leave the guitar all but silent: from the shipped SW50R
template, three of six held-out parts matched without a DI turned the preamp
volume or the amp's level nearly to zero, and through a real guitar played 16–35
LU under the recording or not at all (`docs/heldout-listening-sw50r.md`). So
without `--probe-di` the tool renders the template and the shortlist through a
synthetic guitar and moves any candidate with no measurable loudness there, 20
dB or more under the template, or that loses its loudness when its level is set,
behind those that pass (`search.guitar_check` in `summary.json`; lines set on
SW50R in sample, so treat a pass as "a guitar gets through", nothing more — on
43 SW50R recordings two answers that passed played 13 and 18 LU quiet, and the
level caveat had flagged both). Report that caveat when it fires; if every
candidate failed, offer the starting preset instead, and in any case tell the
user to confirm the preset plays with their own guitar.

For `paired_di`, the exact DI is mandatory, and after the search the tool trims
the output gain to the reamp's loudness when the reference is measured whole
(each decision is under `search.level_trims` in `summary.json`); without a DI the
output level is set through the synthetic guitar as above, and otherwise it is
left to the search. A residual-weighted paired run must
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
  --probe-di PROBE.wav --loss-profile unpaired-v3 \
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
listener answers: which is closer to the reference, A, B, or indistinguishable?
Do not ask for preference; closeness is the target of this workflow.

Overall loudness should not affect the closeness answer here. If output level needs
judgment, play the untouched raw renders afterward and record that separately.

After the user listens, record the blind label rather than manually opening and
translating the key. The logger verifies the audition file's SHA-256, resolves the
label only after the answer is supplied, then revalidates the run, trial, summary,
spec, settings, renderer and excerpt before attaching the database verdict and
learned note. Record only the closer blind label:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/log_blind_verdict.py" \
  --key RUN_DIR/audition-candidate-1/audition.flac.key.json \
  --choice A --listener LISTENER \
  --comment "the low mids are still too thick"
```

`--choice` is the closer blind label: `A`, `B`, or `indistinguishable`. Older
records may carry a preference answer; do not ask for or infer one. Pass the same `--data-dir`
used for the preset library when one was used.
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
- which candidate was closer, plus any specific mismatch in the comment, such
  as "delay is right but the low mids are too thick".

Keep the entry concise. Never copy the user's audio into the plugin or commit the
local run database, report, summary, generated preset, or learned notes.
