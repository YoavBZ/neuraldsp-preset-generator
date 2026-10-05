---
name: match
description: >-
  Match an existing Neural DSP preset to supplied reference audio by measuring
  the recording, calculating invertible controls, searching the rest, and
  presenting a shortlist before writing. Use when someone supplies or points to
  audio and asks to match, copy, recreate, approximate, or get closer to its
  guitar tone, including a DI/reamp pair, isolated or source-separated stem, or
  full mix. It searches only with a DI of the performance: from a song or stem
  alone no search has beaten the starting preset, so it keeps that preset. Use
  generate instead when there is no audio reference.
allowed-tools: Read, Glob, Grep, Bash, WebSearch, WebFetch
---

# Match a recording

Measure a recording, match a preset to it, and show the evidence before writing.
Read [preset-spec.md](../../reference/preset-spec.md) before applying the result.

**A match needs a DI of the performance.** With a song or stem alone, measure and
describe the reference (steps 1–2), then hand over the starting preset as it is
and stop: no search or calculation without a DI has been shown to end closer to
the recording than that preset (step 3).

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
  --regime mix --text
```

`mix` is a song; use `separated_stem` or `isolated_stem` for a stem (step 1's regimes
say which). Always pass `--regime`: the default, `probe`, skips the check that the
window holds a guitar.

**Then check the window actually holds the part, before spending anything on
it.** `--excerpt` ranks by broadband activity, which on a dense master ranks
nothing and returns the middle of the file; on full songs that missed a given
guitar part a third of the time or more. For a full song, ask the user for a time
where the guitar is clearly heard, and pass that same `--excerpt-start SECONDS` to
`fingerprint.py` and to `match_preset.py`, so the fit runs on the window you checked. A budget spent against the wrong
twenty seconds buys a careful fit to the wrong instrument, and every score in the
report will look normal. Re-measure with `--excerpt-start SECONDS` when you see
any of:

- `excerpt_policy: activity_tie` (`activity tie` in `--text` output) — several windows scored the same and this is
  the middle one of them, so confirm it holds the part
- a clamped or ignored `--excerpt-start` — the window you named was not the
  window measured
- a "does not look like a guitar" caveat — centroid under 200 Hz and a −6 dB
  extent under 450 Hz

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

Measurement describes a recording; it does not identify an artist's rig. When the request
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
evidence says, and add `--process-policy fresh` whenever it is on (below). Don't
try both with `--enumerate`: an enumerated variant's newly enabled controls are
never searched, they keep the template's values (the ground-truth audit's D-M17).

### No response atlas

Do not build or start from a response atlas (one amp's stored responses at
sampled settings). On SW50R, by the since-superseded `unpaired-v1` objective, a
search started from the nearest atlas entry ended further from played-guitar targets
than one started from neutral settings (0.548 against 0.447), and an atlas built from
the user's own DI ended no closer (0.479 against 0.480) after costing 128 renders to
build. The research tools are
described in `docs/tone-matching-plan.md`.

Do not enumerate switches or selectors casually. Enumeration divides the budget
among complete inner searches, no accuracy benefit from it has been shown on the
real backend, and the controls a variant switches on are never searched: they keep
the template's values (audit D-M17; enumerating `selectedAmp` leaves the other amps'
amp and EQ unsearched). If trying a discrete control is material, set it in the
template and run each setting as its own match.

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
or `reverb/reverbActive` true in the template, switched on by `--enumerate`, or
calculated on by the inversion. The report lists what it calculated; if it turned
one on, rerun with fresh. The inversion can switch the tremolo on for any
recording, not only a probe: it read ordinary playing as a tremolo on about half
the development amp tracks (audit D-M7). Unless research says the part has one,
treat a calculated tremolo as a mistake: write the preset from a copy of the chosen
spec with `tremolo/tremoloActive` off, leaving the run's own spec untouched for step 6,
and tell the user that every candidate was searched, scored and auditioned with the
tremolo on. Not the amp's own spring reverb: its carry-over is a
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

**Without a DI, do not search: the starting preset is the answer.**
`match_preset.py` refuses a recording reference without `--probe-di`. Measured on
43 development recordings per amp (SW50R, PR12, AC20 and Tone King's rhythm
channel), with loudness set aside and parts grouped by band
(`docs/tone-matching-plan.md`, "The real-guitar probe, from neutral settings and
from the shipped presets"):
- through the noise-burst probe, the calculated settings alone ended further
  from the recording than the shipped preset on 33–36 of 43 on every amp, and the
  search did not recover: it ended further on PR12 and AC20 and no closer on SW50R
  and Tone King;
- through clips of other players' real guitar, the search ended level with the
  shipped preset as it is (closer on 23–30 of 43, no amp significant), though it
  beat the noise-probe search on every amp.

These figures came from a score since retired as a measure of closeness. A re-check
with its replacement, the judge, was inconclusive: its positive control, a search with
the part's own DI, was closer in most bands but not significantly
([the re-check](../../docs/no-di-rule-under-the-judge-results.md)). So the figures are
unconfirmed. As a description, not a verdict, the median of each no-DI method there was
further from the recording than its start, the library search's too, though not
significantly. The rule stands, as the re-check's plan declares for an inconclusive
result.

So without a DI, choose the starting preset with the generate skill's research
about the song, and deliver it as it is. Use `fingerprint.py` on the reference
only to describe it and its caveats, not to change settings, and do not ask the
user to record a DI to make up for it. `--search-without-di` runs the old
noise-probe search, with its guitar check and level trim, for benchmarks; do not
offer its answer as better than the starting preset.

When the user does supply a DI, pass it as `--probe-di`, and present the answer
beside the starting preset, not as an improvement on it. With the DI of the very
take recorded, the search ended closer than its start on nearly every development
part, but by the retired score. Under the judge that result is unconfirmed: the
positive control of the re-check above, exactly this search, was closer in most
bands but not significantly. A DI of another performance, the user's own included,
is less proven still.

For `paired_di`, the exact DI is mandatory, and after the search the tool trims
the output gain to the reamp's loudness when the reference is measured whole
(each decision is under `search.level_trims` in `summary.json`); otherwise the
output level is left to the search. A residual-weighted paired run must
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
  --reference REFERENCE.wav --reference-mode mix \
  --probe-di PROBE.wav --loss-profile unpaired-v3 \
  --pack morgan --amp sw50r --renderer synthetic \
  --budget 300 --shortlist 3 --out-dir RUN_DIR
```

When the user named a time, add the `--excerpt-start SECONDS` you fingerprinted with;
otherwise the match measures its own automatic window, which may be another one.

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
  plain-language differences between candidates. These scores are the search's own
  objective (`unpaired-v3`, or `paired-v2` on a paired run). The judge replaced the
  v3 objective as the measure of closeness
  ([measuring-closeness.md](../../docs/measuring-closeness.md)), and no search's own
  objective is evidence of closeness: report them as what the search optimised. Quote
  `reference_level_score`, not `score`, and check `input_level_observations` for
  the level you are quoting, since a score that averages three renders and a score
  from one are different kinds of number. The run says outright when two candidates
  are closer together than their scores can resolve; pass that on rather than
  presenting the order as a finding;
- every caveat, especially low harmonic confidence,
  separation artefacts, absent measured EQ data, and unverified pack paths.

A lower score says the search's objective preferred a candidate, not that it is
closer. The blind listen in step 6 is the verdict, so ask the user to audition the
shortlist.

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
