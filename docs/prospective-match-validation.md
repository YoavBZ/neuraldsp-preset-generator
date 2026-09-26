# Prospective test of the match tool — declared before the data

Every listening round so far used How Long and Hotel California, the same two
songs every benchmark and every tuning decision in `tone-matching-plan.md` was
made against. A good verdict on them cannot show that matching works on a song
it was not tuned on. This file fixes, before the player's DI of a new song
exists, exactly how the match tool's answer for that song will be made and
judged, so the verdict can count as a test rather than an explanation. Its
commit time is the declaration time.

The prospective listening protocol (kept privately, beside the audio it may not
publish) already declares one comparison for this song: the existing preset
against a hand-brightened copy. That tests a manual edit. This declares a second
comparison that tests the tool itself — the claim `skills/match/SKILL.md` makes,
that a reference and the player's own DI get closer than the starting preset.
Both follow the same rules: the two alternatives are fixed before anything is
rendered or scored, predictions are frozen before listening, closeness is asked
separately from preference, and nothing is adjusted after a score or a verdict.

## Target

Eric Clapton, "Autumn Leaves" (*Clapton*, 2010), 264–316 s: the guitar-forward
lead section. Target id `autumn-leaves-clapton-264-316`, shared with the other
comparison, so the two count as one song group, not two.

| input | file | sha256 |
|---|---|---|
| mix, 264–316 s | `~/ndsp-presets/references/autumn-leaves-clapton-264-316s.wav` | `ff95c2e7…31c24` |
| lead guitar, separated (Moises) | `…-264-316s-lead.wav` | `340cedc6…3b067` |
| everything but the lead (Moises) | `…-264-316s-backing.wav` | `c9fa1a5e…360dd` |
| the player's DI of this section | not yet recorded | recorded on arrival |

The stems' provenance, their 46 ms offset from the mp3 and their 2.5 dB level
against the mix are in `autumn-leaves-clapton-264-316s.json` beside them.

## The two alternatives

- **A — the starting preset.** `/Library/Audio/Presets/Neural DSP/Morgan Amps
  Suite/User/Autumn Leaves - Clapton.xml`, sha256 `70815fe5…ade7a`, unchanged:
  the Morgan SW50R preset the generate skill wrote for this song, never checked
  by ear. It is A in the other comparison too.
- **B — the match tool's answer from A**, made once, with the player's DI, by
  exactly this command at the plugin version current when the DI arrives, and
  nothing else:

  ```bash
  .venv/bin/python scripts/match_preset.py \
    --template "/Library/Audio/Presets/Neural DSP/Morgan Amps Suite/User/Autumn Leaves - Clapton.xml" \
    --reference ~/ndsp-presets/references/autumn-leaves-clapton-264-316s-lead.wav \
    --reference-mode separated_stem --excerpt 0 \
    --probe-di DI.wav --pack morgan --amp sw50r \
    --renderer swift --process-policy fresh \
    --budget 300 --shortlist 3 --seed 0 --out-dir RUN_DIR
  ```

  B is the recommended candidate, `match-1.json`, applied to A with
  `apply_spec.py` — not the best of several runs, and not edited. `DI.wav` is the
  player's take cropped to the same section the audition uses (its first note to
  52 s later), whatever crop the audition's alignment settles on; the loss
  profile is the default, `unpaired-v2`; A's rack reverb is on, hence
  `--process-policy fresh`; no switch is enumerated, so the cab, mic, reverb and
  compressor stay A's. If the run fails or any of its caveats says the answer is
  unusable, that is the result, recorded as such, not a reason to run it again
  with other settings.

A match of the same stem through the How Long DI already exists
(`~/ndsp-presets/runs/autumn-leaves-lead-howlong-001`). It is a rehearsal of the
command above, not B: nobody listens to it, and it will not be compared.

## How it is judged

The same backed blind A/B as the other comparison: both alternatives rendered
bare from the DI in fresh processes, loudness-matched, mixed with the backing at
the aligned time, labels hidden. The listener answers which sounds closer to the
original guitar, and separately which they prefer. Both objective predictions —
`unpaired-v1` and `unpaired-v2`, `level` excluded — are frozen by the audition
builder before listening.

The hypothesis is that **B is judged closer than A**. One verdict on one song is
one observation: it can falsify the claim for this song, and it adds a song
group to the count the protocol needs before any agreement is interpreted. It
does not validate matching.

## What would change this declaration

Nothing after the DI arrives. Anything decided before that — a different
reference regime, a different budget — is a new commit to this file, made
before the DI exists and saying why.
