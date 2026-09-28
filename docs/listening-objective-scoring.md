# Objective predictions for listening comparisons

Every comparison needs an explicit reference crop, the two **bare-guitar**
alternatives, their blind labels, and a private target-group identifier. Repeated
passages and backed revisits of a target keep the same identifier. Do not infer
independence from different filenames, presets, passages, or comparison numbers.

`build_rab_audition.py` stores an `objective_record` in the private blind key.
Declare `--reference-regime` and, for grouped reporting, `--target-id`; optionally
give `--comparison-id`. Declare `--a-amp-model` and `--b-amp-model`.
For an AC20 alternative, render the DI and full effective settings through
`scripts/render_listening_guitar.py`, which uses
`AudioUnitRenderer(process_policy="fresh")`. Pass its private `*.render.json`
record using `--a-render-record` or `--b-render-record`. The builder verifies
that the record hashes the exact audio and names AC20 with a fresh process.
The same bare file must be used for objective scoring. Morgan's AC20 on a reused
instance changes with prior renders, by as much as about 0.09 unpaired-v1 in a
separate tooling check; warm-up does not clear it. Historical AC20 audio remains
the stimulus the listener actually heard and must be flagged as having uncertain
instance history. Rerendering it would create a different comparison requiring
a new blind judgment. PR12 did not show this effect; SW50R showed a smaller one.
When an archived alternative has no known amp model, the audit records
`amp_model_unknown`; it does not silently count that audio as history-independent.

Match audition exports take the reference regime from the
completed run and accept the same grouping/identifier options. Do not reveal
predictions before collecting the listener's answer.

To measure whether a listener gives stable closeness answers, a blind audition
can include hidden repeat blocks and an optional identical-alternative catch:

```sh
python scripts/build_rab_audition.py ... --hidden-repeats 1 --catch-trial
python scripts/export_match_audition.py ... --hidden-repeats 1 --catch-trial
```

For a backed audition, put `"reliability": {"hidden_repeats": 1,
"catch_trial": true}` in its private manifest. Builders number and randomize
the blocks without revealing which is primary, repeated, or a catch. Ask for
one closeness answer per numbered block, in order: use repeated
`--trial-choice A|B|indistinguishable` with `log_blind_verdict.py`, or repeated
`--trial-closer A|B|indistinguishable` with `log_backed_verdict.py`. The private
key holds the answer mapping and must remain hidden until all answers are
recorded. The first repeat reverses A/B labels; the catch plays one alternative
twice. The audit recomputes role-consistency on repeats and the fraction of
catch answers marked indistinguishable. These are descriptive within-listener
checks, separate from objective agreement. Only the primary trial receives an
objective score; hidden trials do not increase the comparison or independent
target count. One session's checks cannot establish listener reliability.

The primary prediction uses the existing `unpaired-v1` audio objectives, **with
`level` excluded** and the remaining measured weights renormalized. Auditions
deliberately remove loudness differences. Each alternative also retains the
standard audio distance with `level`, its fingerprint, individual objectives,
effective weights, source hashes, and scorer/profile hashes. Preset-prior and
complexity penalties cannot be recovered from audio alone: these are audio
distances, not full optimization scores. Matching weights are not changed.
New blind auditions also freeze a separate `unpaired-v2` prediction before
listening, with `level` excluded in the same way. The verdict sidecar reports
agreement with v1 and v2 separately; neither rewrites the other's distances.
The private audition key and its objective record both declare the frozen
profiles. A missing or damaged v2 prediction in a key that declares v2 keeps
the listener's answer but makes the objective result unscored; it must not be
treated as an old v1-only key. The aggregate validates the frozen v2 fields
and derives agreement from the listener answer, rather than trusting a stored
agreement label alone.
Older v1-only keys stay v1-only. Do not compute v2 after hearing a verdict and
count it as a prospective test. When a match audition verifies its sources again
at verdict time, a changed score is reported as unscored rather than silently
replacing the pre-listening prediction. Per-target v2 summaries can be produced
from frozen verdict records with `analysis.listening.match_v2_agreement_report`.
Historical manifest backfills through `score_listening.py` remain v1-only.
To audit logger-produced blind and backed verdicts together, use the private,
no-render command:

```sh
python scripts/audit_frozen_listening.py \
  --record PRIVATE_BLIND_OBJECTIVE_VERDICT.json \
  --record PRIVATE_BACKED_VERDICT.json \
  --out-dir PRIVATE_NEW_IGNORED_DIRECTORY
```

New blind verdicts carry a hash of the entire private audition key, including
the A/B mapping and match provenance. The audit checks that binding, the frozen
scores and the recorded heard-audio binding, then reports closeness only,
counting repeated comparisons within their target group. Older v1-only verdicts
without a whole-key
hash remain readable but unscored for v2. The
private report contains target IDs; keep it out of Git. This binding does not
prove when the key was created, authenticate the listener's answer, or show
that target groups are independent. It does
not reopen or rescore the raw audio, so a source can be archived after the
verdict without changing the frozen audit.
If the alternatives have different measurable objectives or component terms,
the distances remain diagnostic but the objective comparison is inconclusive;
it does not count toward the agreement fraction.
The sidecar also records a **common-term sensitivity check**: it recomputes
each distance from only term names measured on both alternatives, retaining the
same dimension weights and excluding `level`. This is a post-hoc diagnostic,
not the match objective or a replacement prediction. An absent term can itself
reflect an audible difference, and dropping it does not make the original
comparison valid for agreement. The primary distances, verdict, and target
count remain unchanged. For an older immutable key, inspect its frozen terms
without opening or modifying it:

```sh
python scripts/inspect_listening_coverage.py --record PRIVATE_KEY.json
```

The inspector needs no raw audio but cannot verify that the archived audio was
the audio heard. It refuses to recompute with a changed loss profile. On played
guitar passages, the RT60 estimator can produce implausible, history-sensitive
values; a common-term check does not repair it. Matching now defaults to `-v2`
profiles that omit RT60, but listening objective scores remain frozen on
`unpaired-v1` and can still include it. Its confidence measures agreement among
release slopes, not evidence that the sound contains reverb.
A deterministic [synthetic control](rt60-synthetic-evidence.json), reproduced by
`scripts/simulate_rt60_evidence.py`, makes that limitation checkable without a
plugin: all three no-reverb inputs clear the `-v1` gate. On the guitar-like
input, a 1.2 s rack-reverb setting measures as 2.85 s. This control alone does
not validate an estimator or explain what a listener would hear.
The builder scores cropped and gained source samples before montage encoding;
24-bit FLAC quantization can make the decoded listening file differ minutely.

For backing mixes, supply the processed guitar file **before backing is added**.
Record its crop, timing and gain processing and the actual reference source.
Do not score the backing mix, subtract the backing to guess a guitar, substitute
a different reference, or align/normalize the signals to hide the listening versus
measurement gap. The gap is part of the experiment. Reference regime must be
explicit: generated probe, paired DI, isolated/separated stem, or full mix.

## Declared validation-crop auditions

For a held-out part, first commit a separate prospective test declaration in a
`docs/*.md` file. Besides the test command, measured outcome, and interpretation
required by `docs/validation-datasets.md`, it must contain one unambiguous fenced
`json` authorization block with `"schema": "held-out-listening-test-v1"`, a nonempty `test_id`,
and `"parts": ["source/song/part", ...]`. The crop builder checks the exact
part against the unchanged HEAD version of that file before reading any audio.
The crop record retains the declaration path, its last-changing commit, HEAD,
hash, and test ID. Register the held-out use in `held_out_uses` of
`docs/validation-datasets.json` as the dataset policy requires; the crop builder
does not write that ledger. Development parts need no declaration.

Build one private crop set with `build_validation_crops.py --source SOURCE
--song SONG --part PART --declaration docs/DECLARATION.md --out-dir runs/CROPS`.
The record's `outputs.mix` is the reference, `outputs.backing` is the backing,
and `outputs.di` is the *same* DI used to render both alternatives. Render each
candidate preset separately with `render_listening_guitar.py --di runs/CROPS/di.wav
--preset PRIVATE_PRESET --out runs/FIRST.wav` (and then `runs/SECOND.wav`). That
script uses a fresh process for every alternative and writes a `.wav.render.json`
sidecar. A preset found without a DI is still rendered through this same DI for
the listening comparison; "without DI" describes how its settings were found.
No plugin is run by the crop or backed-audition builder.

Write a private `prospective-backed-listening-v1` manifest for
`build_backed_audition.py`. Copy exact paths and SHA-256 values from the crop
record and fresh-render sidecars; this template shows the required mapping:

```json
{
  "schema": "prospective-backed-listening-v1",
  "id": "ONE_COMPARISON_ID",
  "target_id": "ONE_INDEPENDENT_SONG_GROUP",
  "declared_test_id": "TEST_ID_FROM_DECLARATION",
  "validation_crop_record": "runs/CROPS/record.json",
  "reference": {"path": "runs/CROPS/mix.wav", "sha256": "MIX_HASH",
                "start_s": 0, "duration_s": 10, "regime": "mix"},
  "backing": {"path": "runs/CROPS/backing.wav", "sha256": "BACKING_HASH",
              "start_s": 0, "gain_db": 0, "guitar_removed": true},
  "alternatives": {
    "first": {"path": "runs/FIRST.wav", "sha256": "FIRST_HASH", "start_s": 0,
              "pack": "morgan", "amp_model": "PR12",
              "render_record": "runs/FIRST.wav.render.json"},
    "second": {"path": "runs/SECOND.wav", "sha256": "SECOND_HASH", "start_s": 0,
               "pack": "morgan", "amp_model": "PR12",
               "render_record": "runs/SECOND.wav.render.json"}
  },
  "mix": {"guitar_target_lufs": -29, "master_target_lufs": -20,
          "peak_ceiling_dbtp": -1, "max_ab_lufs_delta": 0.5,
          "gap_s": 0.5, "cycles": 1}
}
```

Use the actual pack and amp model from each sidecar; the example values are
placeholders, not suggested tones or mix levels. Fix mix levels and the blind
seed before listening. With `validation_crop_record` present, the builder
requires the whole mix crop, unaltered backing, fresh-process records for both
alternatives, and each record's DI binding to the crop DI. It freezes separate
unpaired-v1 and unpaired-v2 predictions before the verdict. The listener hears
the backed mixes, while both objective scores compare bare guitars to the mix
reference; this deliberate difference is recorded, not corrected away.

`log_blind_verdict.py` writes a separate immutable objective/verdict sidecar per
listener/session, leaving the original blind key untouched. Ask only which
alternative is closer. Historical preference fields remain readable for schema
compatibility, but new rounds leave them null and never infer them. The command-line
audit summary displays closeness only; archived JSON retains historical preference
results. Unknown target groups stay `unassigned` and are excluded from target-level
summaries.
If a raw source is later unavailable, the intact hashed audition still permits
the subjective verdict; its objective sidecar is marked unscored.

For historical or custom comparisons, create a **private** JSON manifest:

```json
{"comparisons": [{
  "id": "unique-comparison", "target_id": "same-target-for-revisits",
  "reference": {"path": "/private/reference.wav", "sha256": "...", "regime": "mix"},
  "alternatives": {
    "A": {"path": "/private/guitar-a.flac", "sha256": "..."},
    "B": {"path": "/private/guitar-b.flac", "sha256": "..."}
  },
  "listening_context": "Listener heard shared backing; scorer hears bare guitar",
  "verdict": {"closer": "A", "preferred": null}
}]}
```

Audio descriptors also accept `start_s`, `duration_s`, `gain_db`, `mono`, and
`promote_stereo`. Transformations must describe the saved audition, not new tone
corrections. Run:

```sh
python scripts/score_listening.py --manifest PRIVATE_MANIFEST.json --out-dir NEW_PRIVATE_AUDIT
```

When the output is inside a Git worktree, the tool requires the audit files to
be Git-ignored (for example, under this project's `runs/`). Verdict sidecars
next to private blind keys are ignored too. Keep all audit outputs private.

The audit keeps failures visible and never silently reuses stale scores. Its
per-target agreement fractions are descriptive: within-target comparison counts
are **not independent n**. Overall summaries weight target groups equally. Ties,
unknown judgments and unscored records are reported separately. Numerical score
equality is not a measured perceptual threshold. With few targets, report that
the evidence is too small to conclude whether the objective predicts the ear.
Keep unmatched-loudness pilots and materially different reference regimes as
separate diagnostic cohorts. Never tune and validate on the same listening set.

Audio, judgments, identities, private paths, audit records and learned conclusions
belong in private storage, not in this repository.
