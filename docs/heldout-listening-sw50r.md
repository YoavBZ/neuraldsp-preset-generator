# Held-out listening test: a match through the part's own DI against a match without one

This file declares, before any held-out audio is opened, the first test that uses
the held-out parts of `validation-datasets.md`. Its declaration time is when this
file reaches `main` on GitHub. Nothing above the results may change after that —
the crop builder refuses a declaration that differs from its committed version,
and records this file's hash in every crop — and the results are only ever
appended, after the last verdict.

```json
{"schema": "held-out-listening-test-v1",
 "test_id": "heldout-sw50r-di-vs-no-di",
 "parts": ["telefunken/57 Chevy/GTR 1",
           "telefunken/57 Chevy/GTR 2",
           "cambridge/That's How I Got To Memphis/ElecGtr3",
           "cambridge/That's How I Got To Memphis/ElecGtr3DT",
           "guitar-techs/P3_music excerpt 02/02",
           "guitar-techs/P3_music excerpt 06/06",
           "guitar-techs/P3_music excerpt 10/10",
           "guitar-techs/P3_music excerpt 11/11"]}
```

These are all eight usable held-out parts. They are four tones, not eight: the
two 57 Chevy guitars, one Memphis guitar and its double, and one Guitar-TECHS
player, guitar and amp setting heard in four excerpts.

## The question

On the development parts, a search through the part's own DI ended far closer
to the amp track than a search without a DI, by `unpaired-v2` distance, on every
one of 14 parts on SW50R (0.561 against 2.524 on average; "Matching amp
recordings" in `tone-matching-plan.md`). That is a distance the search itself
minimises, measured before `unpaired-v3` existed, from neutral settings, with
both arms in one regime and no level trim — this test runs the tool as it now
ships instead. This test asks whether a listener hears the same thing on parts no
tool or person has touched: **does a match made through the part's own DI sound
closer to the recording than a match made without any DI?**

## How each alternative is made

Every step runs from a clean worktree of this repository at the commit that
merges this file, with the main checkout's interpreter,
`/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python` (written
`.venv/bin/python`), Morgan Amps Suite 1.1.1 through the Swift renderer. For each
part, `SOURCE`, `SONG` and `PART` are the three fields of its ID, and `RUN` is
`runs/heldout-sw50r/SLUG` inside that worktree — git-ignored and private, and
where `render_listening_guitar.py` requires its output. `SLUG` is the part ID
with `/` replaced by `-` and every other character outside `A–Z a–z 0–9 _ -`
replaced by `_` (`telefunken-57_Chevy-GTR_1`,
`cambridge-That_s_How_I_Got_To_Memphis-ElecGtr3`). The worktree is kept until
the results are appended, since each audition binds the exact paths of its crops
and renders, and its `runs/heldout-sw50r` is then archived to
`~/ndsp-presets/runs/`. Every step's output goes to a log in `RUN`, which the
listener does not read before the verdicts: the match and apply steps print
distances and settings.

1. **Crops**, as `validation-datasets.md` declares them: the loudest 10 s of the
   M80 (Telefunken) or the one amp track, and the same span of the DI, the mix
   and the backing.

   ```bash
   .venv/bin/python scripts/build_validation_crops.py \
     --source "$SOURCE" --song "$SONG" --part "$PART" \
     --declaration docs/heldout-listening-sw50r.md --out-dir "$RUN/crops"
   ```

2. **The DI match** (first). The amp track is a performance of this exact DI, so
   the regime is `paired_di`; with no sidecar the run records the pairing as
   asserted, which does not affect the match.

   ```bash
   .venv/bin/python scripts/match_preset.py \
     --template samples/SW50R_Atlas_Topology.xml \
     --reference "$RUN/crops/reference.wav" --reference-mode paired_di --excerpt 0 \
     --probe-di "$RUN/crops/di.wav" --loss-profile unpaired-v3 \
     --pack morgan --amp sw50r --renderer swift --process-policy fresh \
     --budget 300 --shortlist 3 --seed 0 --out-dir "$RUN/with-di"
   ```

3. **The no-DI match** (second): the same, without `--probe-di`, so the tool uses
   its noise probe, and with `--reference-mode isolated_stem` — the amp track is
   an isolated stem, and without a DI there is no pairing to claim.

   ```bash
   .venv/bin/python scripts/match_preset.py \
     --template samples/SW50R_Atlas_Topology.xml \
     --reference "$RUN/crops/reference.wav" --reference-mode isolated_stem --excerpt 0 \
     --loss-profile unpaired-v3 \
     --pack morgan --amp sw50r --renderer swift --process-policy fresh \
     --budget 300 --shortlist 3 --seed 0 --out-dir "$RUN/no-di"
   ```

4. **Presets and renders.** Each run's `match-1.json`, the recommended
   candidate, applied to the template — except that when the run's
   `summary.json` has a caveat beginning "nothing beat the preset you started
   from", that arm's preset is a byte copy of the template instead — then
   rendered bare through the part's DI in a fresh process. Both alternatives are
   heard through the same DI: "without a DI" describes how the settings were
   found, not what is played.

   ```bash
   .venv/bin/python scripts/apply_spec.py --template samples/SW50R_Atlas_Topology.xml \
     --spec "$RUN/with-di/match-1.json" --out "$RUN/with-di.xml"
   .venv/bin/python scripts/apply_spec.py --template samples/SW50R_Atlas_Topology.xml \
     --spec "$RUN/no-di/match-1.json" --out "$RUN/no-di.xml"
   .venv/bin/python scripts/render_listening_guitar.py --pack morgan \
     --di "$RUN/crops/di.wav" --preset "$RUN/with-di.xml" --preroll-s 0 --out "$RUN/first.wav"
   .venv/bin/python scripts/render_listening_guitar.py --pack morgan \
     --di "$RUN/crops/di.wav" --preset "$RUN/no-di.xml" --preroll-s 0 --out "$RUN/second.wav"
   ```

The template is `samples/SW50R_Atlas_Topology.xml` (sha256 `25a3efbf…3acf`), the
shipped IR-free example with the SW50R selected. Its rack reverb, delay and
compressor are on, hence `--process-policy fresh`. No switch is enumerated, but
each arm's inversion may still change some (it turns the delay off unless it
measures one, and may turn a tremolo on). The two arms differ as the tool does
with and without a DI, not only in the signal they search through: the DI arm
runs as `paired_di`, which guards the tremolo against the playing's rhythm and
trims the answer's output level to the reference's; the no-DI arm runs as
`isolated_stem`, without either. The audition sets each guitar to the same
loudness on its own, so the trim reaches the listener only through which
candidate the tool recommends. SW50R is not the amp on any of these recordings — the 57 Chevy rigs are not
stated, Guitar-TECHS used an Orange CR-12, and Memphis may be an amp simulator —
so neither alternative can reproduce the recording; the question is which one
comes closer.

Every command above was rehearsed on development parts before this file was
declared: on Guitar-TECHS excerpt 01 (unbacked) and Bourbon GTR 1, the matches
with the synthetic renderer and a small budget, the renders through the plugin,
and both auditions built; and on Bourbon GTR 1, both match commands exactly as
written above. Nobody listened to any of it. The rehearsal found
that `render_listening_guitar.py` sent a preset's name to the plugin as a
control, which failed every Morgan preset render; this change fixes that.

**When a step fails.** A failure is a result, recorded as such, never a reason to
change a setting. A non-zero exit of any step — the crop builder, either match,
`apply_spec.py`, either render or the audition builder, which refuses for
instance a pair more than 0.5 LU apart after level matching — or a match with
no `match-1.json`, makes that part "not run". A step that crashed without
writing its output may be rerun once, byte-identical: the same command at the
same commit. A match's output is its `match-1.json`: its rerun uses the same
out-dir, where the crashed run's trial store stays as a record. A run whose caveat says the optimiser never ran still has an
answer, and it goes ahead. If both arms of a part end with the same settings
(identical `applied_settings` in the two render records), the part is run,
counts as no difference, and is not heard.

## How it is heard

One blind backed audition per part, built by `scripts/build_backed_audition.py`
from a `prospective-backed-listening-v1` manifest, mapped from the crop record
and the two render sidecars as `listening-objective-scoring.md` describes:

- `id` the part's `SLUG`, `target_id` `unassigned`, `purpose` `prospective`,
  `validation_mode` `declared`, `declared_test_id` `heldout-sw50r-di-vs-no-di`,
  `validation_crop_record` `RUN/crops/record.json`;
- `reference`: the crop's `mix.wav` and its sha256 from the record, `start_s` 0,
  `duration_s` 10, regime `mix`; `backing`: the crop's `backing.wav` and its
  sha256, `start_s` 0, `gain_db` 0, `guitar_removed` true;
- `alternatives.first`: `RUN/first.wav` (the DI match), `alternatives.second`:
  `RUN/second.wav` (the no-DI match), each with its sha256, `start_s` 0, `pack`
  `morgan`, `amp_model` `SW50R` and its render record;
- `mix`: `guitar_target_lufs` the crop record's `reference_lufs`,
  `master_target_lufs` −20, `peak_ceiling_dbtp` −1, `max_ab_lufs_delta` 0.5,
  `gap_s` 0.5, `cycles` 1. `reference_lufs` is the reference amp track's level;
  for Telefunken the mix also holds the part's TF11 microphone, so there both
  alternatives sit under the original guitar's level, equally;
- `reliability`: `hidden_repeats` 1, `catch_trial` false — each part is heard
  twice, the second time with the labels swapped, in an order the listener
  cannot see.

The manifest is `RUN/audition.json`, built with
`build_backed_audition.py --manifest "$RUN/audition.json" --out-dir
"$RUN/audition"` and no `--seed`, so the builder draws the blind seed; it
freezes the objective predictions before anything is heard, and the A/B mapping
exists only in its private key. For Guitar-TECHS the "mix" is the amp track alone and the
backing is silence: those four are heard unbacked.

The listener hears every part that has an audition in one session, in the
order of the list above, and answers only which alternative sounds closer to the original guitar
— A, B or indistinguishable — for every trial of a part before moving to the
next (`scripts/log_backed_verdict.py --trial-closer`). A preference, if offered,
goes in the notes and is not analysed. Nobody hears, and the listener is not
shown, any render or objective score of these runs before the verdicts are
logged.

## What the result means

A part **counts for** an alternative when both of its trials pick it; any other
pair of answers counts as no difference. A part is **run** unless it is "not
run" above. A **tone** — 57 Chevy GTR 1, 57 Chevy GTR 2, Memphis ElecGtr3 with
its double, Guitar-TECHS — counts for the DI match when the DI match counts on
more of its parts than the no-DI match. The result is decided in this order:

1. fewer than six parts run: **inconclusive**;
2. the DI match counts on at least 6 parts, the no-DI match on at most 1, and
   the DI match in at least 3 of the 4 tones: **supported**;
3. the no-DI match counts on at least as many parts as the DI match — including
   none on either side, where nothing was heard to differ: **falsified**;
4. anything else: **inconclusive**.

These are thresholds, not significance tests: the eight parts are four tones,
four of the parts one Guitar-TECHS tone, two sessions share a band and room with
the development songs, and one listener hears them all. A supported result says that, on new performances heard by ear,
matching through the player's own take beats matching without a DI on this one
amp model; it does not measure how close either comes, and it says nothing about
a player's own DI of a part they did not record with (a different performance
from the reference, which no test here has measured).

**The objective predictions** frozen by the builder (`unpaired-v1` without
`level` and `unpaired-v2`, bare guitar against the mix) are reported beside the
verdicts and kept out of the listening protocol's agreement count — both
alternatives were chosen by minimising distance to the amp track that is in that
mix, which is what `target_id` `unassigned` does.

The results, appended here after the last verdict, record the commit every step
ran at, a sha256 of that interpreter's `pip freeze`, every crop record's hash and
each part's two presets' hashes. `held_out_uses` in `validation-datasets.json`
gains this test's entry in the same change. Every part stays held out for the
next declared test.
