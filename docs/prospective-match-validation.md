# Prospective test of the match tool — declared before the data

Every listening round so far used How Long and Hotel California, the same two
songs every benchmark and every tuning decision in `tone-matching-plan.md` was
made against. A good verdict on them cannot show that matching works on a song
it was not tuned on. This file fixes, before the player's DI of a new song
exists, exactly how the match tool's answer for that song will be made and
judged, so the verdict can count as a test rather than an explanation. The
declaration time is when this file reaches `main` on GitHub (the pull request's
merge time, which the author cannot set); the DI must be recorded after it.

The prospective listening protocol, kept privately beside the audio it may not
publish, already declares one comparison for this song: the existing preset
against a hand-brightened copy. That tests a manual edit. This declares a second
comparison that tests the tool itself: that a match made through the player's
own DI ends closer to the reference than the preset it started from, here judged
by ear. Both follow the same rules — alternatives fixed before anything is
rendered or scored, predictions frozen before listening, nothing adjusted after a
score or a verdict.

## Target and inputs

Eric Clapton, "Autumn Leaves" (*Clapton*, 2010), 264–316 s, the guitar-forward
lead section. The hand-edit comparison is this song group's entry in the
protocol's count, under target id `autumn-leaves-clapton-264-316`. This
comparison, id `autumn-leaves-clapton-264-316-match-tool`, is built with target
id `unassigned`, which `analysis.listening`'s agreement report never aggregates,
so it cannot add a second entry for the same song or fold its in-sample
predictions into the count; its verdict is recorded here instead.

| input | file in `~/ndsp-presets/references/` | sha256 |
|---|---|---|
| mix, 264–316 s | `autumn-leaves-clapton-264-316s.wav` | `ff95c2e7…31c24` |
| lead guitar, separated (Moises) | `autumn-leaves-clapton-264-316s-lead.wav` | `340cedc6…3b067` |
| everything but the lead (Moises) | `autumn-leaves-clapton-264-316s-backing.wav` | `c9fa1a5e…360dd` |
| the player's DI | `autumn-leaves-clapton-264-316s-di.wav`, to be recorded | in the addendum |

The stems' provenance, their 46 ms offset from the mp3 and their 2.5 dB level
against the mix are in `autumn-leaves-clapton-264-316s.json` beside them.

**The DI.** Recorded after the declaration time, playing along with the backing
file above in a DAW, the backing placed on the timeline at some time T with
silence before it for a count-in. The DI file,
`autumn-leaves-clapton-264-316s-di.wav`, is the DI track exported from T to
T + 52 s: the backing's exact span, with the DAW's latency compensation on,
mono, at the recording's own level — no gain change, normalisation, editing,
comping or timing adjustment. The DAW's export is the alignment: the DI is a
different performance from the recording, so no correlation with the lead stem
can measure its timing, and none is used. One take; if several are recorded, the
player names the one to use before any of them is rendered through anything. The
same file is used for B's match and for both alternatives' audition renders.

## The two alternatives

- **A — the starting preset.** `/Library/Audio/Presets/Neural DSP/Morgan Amps
  Suite/User/Autumn Leaves - Clapton.xml`, sha256 `70815fe5…ade7a`, unchanged:
  the Morgan SW50R preset the generate skill wrote for this song, never checked
  by ear. It is A in the other comparison too.
- **B — the match tool's answer from A**, made once, with this repository at the
  commit that merges this file (plugin 0.7.23), Morgan Amps Suite 1.1.1 through
  the Swift renderer build `audio-unit-renderer-2af9432f77c6`, from a clean
  worktree at that commit run with the main checkout's interpreter,
  `/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python` (written
  `.venv/bin/python` below):

  ```bash
  .venv/bin/python scripts/match_preset.py \
    --template "/Library/Audio/Presets/Neural DSP/Morgan Amps Suite/User/Autumn Leaves - Clapton.xml" \
    --reference ~/ndsp-presets/references/autumn-leaves-clapton-264-316s-lead.wav \
    --reference-mode separated_stem --excerpt 0 \
    --probe-di ~/ndsp-presets/references/autumn-leaves-clapton-264-316s-di.wav \
    --pack morgan --amp sw50r --renderer swift --process-policy fresh \
    --budget 300 --shortlist 3 --seed 0 \
    --out-dir ~/ndsp-presets/runs/autumn-leaves-prospective-match-b
  .venv/bin/python scripts/apply_spec.py \
    --template "/Library/Audio/Presets/Neural DSP/Morgan Amps Suite/User/Autumn Leaves - Clapton.xml" \
    --spec ~/ndsp-presets/runs/autumn-leaves-prospective-match-b/match-1.json \
    --out ~/ndsp-presets/runs/autumn-leaves-prospective-match-b/B.xml
  ```

  B is `match-1.json`, the recommended candidate, applied to A as above — no
  other flag, no edit, not the best of several runs. The loss profile is the
  default, `unpaired-v2`. A's rack reverb is on, hence `--process-policy fresh`;
  no switch is enumerated, so the cab, mic, reverb and compressor stay A's. If
  the Morgan plugin, the renderer build or anything else pinned here changes
  before the DI arrives, that is a new commit to this file, made before the DI
  exists; after it arrives, a change means B is made from the pinned commit
  anyway, or the comparison is reported as not run.

**When B does not exist.** Each of these is the result, recorded as such, and
not a reason to change settings: a non-zero exit or no `match-1.json`; a caveat
beginning "the optimiser never ran"; a caveat beginning "nothing beat the preset
you started from" (then B is A, and there is nothing to compare); `apply_spec.py`
refusing the spec. One byte-identical rerun — same commit, seed and DI — is
allowed only after a crash that happened before any spec was written. Otherwise
B goes to the audition whatever its other caveats say.

**Blinding.** Nobody loads, renders or hears B before the verdict outside the
match run, `render_listening_guitar.py` and the audition builder. A match of the
same stem through the How Long DI already exists
(`~/ndsp-presets/runs/autumn-leaves-lead-howlong-001`); it rehearsed the
command, nobody listens to it, and it is not compared.

## How it is judged

A backed blind A/B, `scripts/build_backed_audition.py` at the same pinned commit,
the listener answering only which alternative sounds closer to the original
guitar (`scripts/log_backed_verdict.py --closer`). A preference, if offered, goes
in the free-text notes and is not analysed. The manifest's values, fixed now:

- the reference the listener hears and the predictions score against: the mix,
  `autumn-leaves-clapton-264-316s.wav`, regime `mix`, crop `start_s` 0,
  `duration_s` 10 — the loudest 10 s of the lead stem (at 0.5 s steps; −14.6 LUFS),
  chosen from the reference alone before any DI; the same crop of the DI and the
  backing
- the backing at `gain_db` +2.5, restoring its level in the mix
- `mix.guitar_target_lufs` −12.1 (the lead's own level in the mix over that
  crop), `master_target_lufs` −20, `peak_ceiling_dbtp` −1, `max_ab_lufs_delta`
  0.5, `gap_s` 0.5, `cycles` 2
- both alternatives rendered bare from the DI by `render_listening_guitar.py` in
  fresh processes with `--preroll-s 0`, each with its `render_record`

Before any audition render, an addendum to this file records the DI's sha256,
the commit B was made at, a sha256 of that interpreter's `pip freeze`, B's
sha256 and its run's `summary.json` sha256.

**What the verdict means.** The hypothesis is that B sounds closer than A. B
closer supports it for this song; A closer falsifies it for this song; no
audible difference does not support it. The result is appended to this file,
which is where the match tool's record across songs is kept. One verdict on one
song is one observation, and it does not validate matching.

**The objective predictions are not independent here.** The builder freezes both
predictions before listening — `unpaired-v1` without `level` primary,
`unpaired-v2` secondary, as for every audition. But B was chosen by minimising
`unpaired-v2` distance to the lead stem through this same DI, and the
predictions score against the mix over part of the same span, so they will
favour B largely by construction. This comparison's objective-to-ear agreement is
therefore recorded and reported here but kept out of the agreement count the
protocol builds across songs, by the `unassigned` target id above.

The two comparisons share A and the listener. They are heard in separate
sessions on different days, the hand-edit comparison first.
