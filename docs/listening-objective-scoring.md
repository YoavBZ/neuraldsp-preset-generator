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

The primary prediction uses the existing `unpaired-v1` audio objectives, **with
`level` excluded** and the remaining measured weights renormalized. Auditions
deliberately remove loudness differences. Each alternative also retains the
standard audio distance with `level`, its fingerprint, individual objectives,
effective weights, source hashes, and scorer/profile hashes. Preset-prior and
complexity penalties cannot be recovered from audio alone: these are audio
distances, not full optimization scores. Matching weights are not changed.
If the alternatives have different measurable objectives or component terms,
the distances remain diagnostic but the objective comparison is inconclusive;
it does not count toward the agreement fraction.
The builder scores cropped and gained source samples before montage encoding;
24-bit FLAC quantization can make the decoded listening file differ minutely.

For backing mixes, supply the processed guitar file **before backing is added**.
Record its crop, timing and gain processing and the actual reference source.
Do not score the backing mix, subtract the backing to guess a guitar, substitute
a different reference, or align/normalize the signals to hide the listening versus
measurement gap. The gap is part of the experiment. Reference regime must be
explicit: generated probe, paired DI, isolated/separated stem, or full mix.

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
