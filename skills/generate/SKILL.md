---
name: generate
description: Create a Neural DSP amp-sim preset for a specific guitar tone — from a song, an artist, a part, or a description of the sound. Researches how the tone was actually recorded, maps it to the plugin's amps and effects, and writes a loadable preset file.
when_to_use: >-
  Use whenever someone asks for a guitar tone, preset or patch to be built, or
  describes a sound they want to get — even without naming a plugin or a file.
  Triggers when they name a song, artist, band, genre or era; ask how to get a
  sound or what settings to use; ask to make something sound like a reference;
  or say tone, preset, patch, amp sim, amp settings, rig, Neural DSP, or Morgan
  Amps Suite. For example — give me the clean tone from Hotel California; make
  a Gilmour-ish lead patch; I need a jangly rhythm sound; set me up for blues
  lead.
argument-hint: "[song or tone description] [rhythm|lead|clean]"
allowed-tools: Read, Glob, Grep, Bash, WebSearch, WebFetch
---

# Generate a preset

Turn a description of a tone into a loadable preset. Read
[preset-spec.md](../../reference/preset-spec.md) before writing anything — it
covers the value convention, the spec format, and the scripts.

## 1. Understand the ask

The user speaks in plain language, not flags. Extract:

- **the tone** — song, artist, era, or a bare description ("jangly", "creamy lead")
- **the role** — rhythm / lead / clean, if stated
- **the plugin** — which pack. Detect it from a template they point at; if they
  don't say, detect the pack from the template's own header rather than
  assuming — more than one pack exists. If there is genuinely nothing to
  detect from, ask rather than picking.

Ask at most **one** clarifying question about the tone, and only if the answer
would change the amp choice or the gain class. When nothing documents whether the
part is clean or clearly driven, that is the question worth asking: the class is the
step most often wrong from a song (step 4). Otherwise pick sensible defaults and say what you
assumed. (Asking where in a full song the guitar plays, step 2, and offering the
listening page, step 5b, are separate.)

### Which pack, when you have to ask

Offer a shortlist rather than an open question. Run
`apply_spec.py --list-recipes --pack <id>` for what each one can actually build;
the differences that decide it are:

| | Morgan Amps Suite | Tone King Imperial MKII |
|---|---|---|
| template | ships one — `${CLAUDE_PLUGIN_ROOT}/samples/Example_Clean_PR12.xml`, IR-free and portable; clean, crunch and heavy parts start from a factory baseline per amp (step 4) | none ships here; clean and crunch parts start from a factory baseline the plugin installs (step 4), or from one of the user's own presets |
| voices | PR12 blackface Princeton (12 W, breaks up), AC20 darkened Vox, SW50R Dumble-ish high headroom | Rhythm channel clean, Lead channel with Mid-Bite, attenuator, spring reverb, tremolo |
| reach for it | jangle and chime, Dumble-style singing lead, anything needing three different amp characters | vintage Fender-flavoured cleans, edge of breakup, blues lead, real spring reverb |

Two traps worth naming out loud when you present the choice:

- **Headroom comes mostly from the amp, not a knob.** A part that never breaks up
  wants headroom: SW50R, the Tone King Rhythm channel, or PR12 kept well below the
  point where it breaks up, which comes early on a 12-watt amp. More than one amp
  usually works: on 25 mostly clean recordings, PR12 and SW50R each suited most, and
  AC20 fewer though still more than half
  ([quick checks](../../docs/quick-checks-results.md); provisional).
- **Choose Morgan or Tone King by voice, not by closeness.** Their clean and crunch
  starting presets landed about even against each other
  ([Tone King baselines](../../docs/toneking-baseline-results.md)), so the pack is a
  question of character. A heavier Tone King part has no starting preset: it needs one
  of the user's own, and if they have none, say so; it is the deciding constraint.

Read `${CLAUDE_PLUGIN_ROOT}/packs/<id>/tone.md` for the voices before
recommending one. Where a pack has no `tone.md`, say so rather than guessing at
its character.

## 2. Research the tone

When the user supplies audio, measure it to describe the recording:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/fingerprint.py" REFERENCE.wav \
  --regime mix --text
```

`mix` is a song; use `separated_stem` or `isolated_stem` for a stem (classified
below). Always pass `--regime`: the default, `probe`, skips the check that the
window holds a guitar.

Any common audio file works — mp3 included, no conversion step needed.

**Check the window before you use the numbers.** `--excerpt` ranks windows by
broadband activity, so on a dense master it ranks nothing and measures the middle
of the file, which misses a given guitar part a third of the time or more. For a
full song, ask the user for a time where the guitar is clearly heard and pass it
as `--excerpt-start SECONDS`. A fingerprint of the wrong twenty seconds is not
noisy; it is a clean description of the wrong instrument. Two things to look at
every time:

- an `activity tie` excerpt policy, a clamped or ignored `--excerpt-start`,
  or a "does not look like a guitar" caveat — each means **look at the window
  before trusting it**, and re-measure with `--excerpt-start SECONDS`
- a centroid below 200 Hz together with a −6 dB extent below 450 Hz is not a dark
  tone, it is a different instrument

[reading-a-reference.md](../../reference/reading-a-reference.md) covers this,
what each regime's confidence is worth, and — importantly for a `mix` or a
`separated_stem` — **which bands of the measurement to believe and which are
artifacts**. Read it before reading anything into a measurement.

Classify the reference conservatively: `isolated_stem` only for an original
multitrack stem, `separated_stem` for source-separated guitar, and `mix` for a
finished mix. Report the regime and its confidence together with the measured
level, spectral tilt and roll-off, dynamics, time effects, harmonic confidence,
and all caveats. The measurement describes the recording; it does not identify
the recorded rig, and without a DI it does not set values either: settings
calculated from a recording ended further from it than the starting preset as it
is on all four amps (`docs/tone-matching-plan.md`, "The real-guitar probe, from neutral settings and from the shipped presets"; measured with a score since retired, and unconfirmed by the [re-check with the judge](../../docs/no-di-rule-under-the-judge-results.md)). So choose the topology and values from
research and the pack's `tone.md`, and use the measurement to describe and
sanity-check them. Follow the [match skill](../match/SKILL.md) only when the user
also has a DI of the performance.

Use WebSearch and WebFetch to find how it was actually recorded and choose the
topology. Good sources:
Premier Guitar rig rundowns, artist interviews, Guitar World tone breakdowns,
well-cited forum threads, video lesson notes.

Capture: the **amp character** (Vox / Marshall / Fender-ish? clean, edge, or
driven?), the **effects** (delay, reverb, modulation, drive pedals), and the
part's **place in the mix**. Keep the source links — you'll cite them.

If research turns up nothing solid, say so and design from the description
instead. Don't invent a rig rundown.

## 3. Map it to the plugin

Read `${CLAUDE_PLUGIN_ROOT}/packs/<id>/tone.md` — it has the amps and their character, an
**intent → recipe stack** table, and the "when the user says X" mappings. Read
`${CLAUDE_PLUGIN_ROOT}/packs/<id>/manifest.json` for what each parameter is, its unit, and its legal
range.

**Also read the learned notes**, if there are any. `show.py` reports their path
as `learned_notes` — that's where past runs recorded what actually worked, and it
beats generic guidance. It lives under the data root, so it survives plugin
updates.

`learned_notes.exists: false` is ambiguous on its own: it means either "no run
has recorded anything yet" or "the data root resolved somewhere that is not where
your notes are". `show.py` prints `data_root_origin` beside it to tell those
apart. If the origin is not the one the user expects — they keep a library
somewhere else, or set `NDSP_PRESET_DATA` in a shell you are not running under —
pass `--data-dir` explicitly rather than generating as if there were no notes.

**Not every pack has this knowledge.** `show.py` reports `tone_knowledge.exists`,
and a bootstrapped pack has no `recipes.json` at all. When either is missing,
say so plainly: you can still edit a template the user points at, but you cannot
map a tonal description onto controls nobody has characterised. Do not invent
the mapping — that is the guess this project exists to avoid.

**Build from recipes, then adapt.** `${CLAUDE_PLUGIN_ROOT}/packs/<id>/recipes.json` holds composable
layers — amp, compressor, drive, eq, cab, delay, reverb, output. Pick one per
layer from the intent table and pass them straight to the writer with `--recipe`;
it resolves `{amp}` and note divisions for you. Then put **what the song needs**
in a `--spec`, which is applied last and overrides the recipes.

Handing back an unmodified stack is a failure — it's a renamed factory preset.
(The dry clean and driven baselines of step 4 are the exception: they are measured starting points.)
The research in step 2 is what should move the values.

Select the amp or channel through the pack's `amp/*` recipe. Morgan uses
`selectedAmp`; Tone King uses its own channel selector. Do not hard-code one
pack's selector into another pack's spec.

For **note-timed delay** ("dotted eighth", "quarter-note slapback"), prefer a
pack recipe that already expresses the timing safely. Morgan recipes resolve
note divisions to milliseconds with `${CLAUDE_PLUGIN_ROOT}/packs/timing.py`;
Tone King recipes use its verified sync-note selectors. See
[selectors-and-timing.md](../../reference/selectors-and-timing.md).

## 4. Pick a template

- For Morgan, the fallback template is `${CLAUDE_PLUGIN_ROOT}/samples/Example_Clean_PR12.xml`
  — IR-free, portable, and shipped with the repo.
- **Choose the class from the part's own documented sound,** not the song's genre, the
  band, or a write-up about the whole song. A song called rock, a metal band or a mix
  review praising "crunchy guitars" says nothing about which guitar is clean. And the
  measured excerpt of a full mix is not evidence of guitar drive: it measures every
  instrument at once, and its harmonic-to-noise ratio and fizz did not tell clean
  parts from crunch ones. When nothing documents the part, say the class is a guess
  (and it may be your one question, step 1). Routing by the song instead, as
  `generate` did before, sent 10 of 22 development clean parts to crunch or heavier,
  about 12% further from the record on average than choosing by the part's real
  class ([generate-routing-results.md](../../docs/generate-routing-results.md)); hence
  the second starting point in step 6. Re-checked on the same parts, the new text (this
  rule with the second start) routed better than the old (in-sample;
  [re-check](../../docs/generate-routing-recheck-results.md)).
- **For a clean Morgan part, start from the amp's clean baseline.** These are factory
  presets, under `/Library/Audio/Presets/Neural DSP/Morgan Amps Suite/`:

  | amp | clean baseline |
  |---|---|
  | PR12 | `Artists/Mark Johnston/Royally Ambient.xml` |
  | SW50R | `Artists/Mark Johnston/Pedal Platform Clean.xml` |
  | AC20 | `Artists/Royce Whittaker/Low-Watt Americana.xml` |

  - **The evidence.** Chosen by rule on development recordings, then checked on 13
    reserved clean parts. Dry, they landed closer to the record than the shipped
    template on every amp, about 12% on average, measured but not yet listened to
    ([clean-baseline-results.md](../../docs/clean-baseline-results.md)).
  - **Make it dry first** with the amp's dry recipe, `--recipe dry/<amp>` (below). Keep
    its compressor, amp, pedals, EQ and cab.
  - **When the research turns an effect back on, set its parameters explicitly.** The
    factory leftovers are extreme. Royally Ambient has a 16-s reverb, heavy delay
    feedback, and a PR12 dwell of 79%: set `pr12Dwell` too if its spring comes back.
    Low-Watt Americana has its tremolo level at 100%.
  - **If the file is missing,** say so and use the template.
- **For a crunch Morgan part (documented as clearly driven, but not heavy), start from
  the amp's crunch baseline.** These are factory presets, under
  `/Library/Audio/Presets/Neural DSP/Morgan Amps Suite/`. Present them to the user as
  "the crunch starting point"; two of the factory names say "Metal", which these parts
  aren't.

  | amp | crunch baseline |
  |---|---|
  | PR12 | `Artists/Keyan Houshmand/Modern Metal (Pick Hard).xml` (the heaviest of the three: a pedal boost into a second drive) |
  | SW50R | `Neural DSP/Hair Metal.xml` (bright and moderate) |
  | AC20 | `Neural DSP/AC20 Mid-Gain Drive.xml` (amp-only crunch) |

  - **The evidence is weak.** They were chosen by rule on development crunch parts.
    On 7 reserved crunch parts from 3 bands, they landed about 7% closer than the
    driven baselines below, and lighter in gain, but only just past the bar
    ([crunch-baseline-results.md](../../docs/crunch-baseline-results.md)). Say so when
    you report.
  - **Make them dry the same way,** with `--recipe dry/<amp>`, and keep their amp,
    pedals, EQ and cab.
- **For a heavier, high-gain part** (out of the project's focus, but it happens), start
  from the amp's driven baseline instead. On heavy material it beats the lighter crunch
  presets. These are factory presets the plugin installs, under
  `/Library/Audio/Presets/Neural DSP/Morgan Amps Suite/`:

  | amp | driven baseline | evidence |
  |---|---|---|
  | SW50R | `Artists/Royce Whittaker/Wall Of Doom.xml` | development, and reserved recordings |
  | PR12 | `Neural DSP/Vintage Metal.xml` | development, and reserved recordings |
  | AC20 | `Artists/Charlie Robbins/Dirty Coil Rhythm.xml` | development recordings only |

  - **The evidence.** On reserved crunch and high-gain recordings, the dry SW50R and
    PR12 baselines were closer to the record than the clean template on the same amp on
    all 23 parts, and about half the distance on average. On clean parts they were
    further on every part, so use the clean baseline for a clean part. These baselines
    are measured, not confirmed by ear: the one heavy-tone listening check tested the
    measure itself and was inconclusive. Say so when you report
    ([driven-baseline-results.md](../../docs/driven-baseline-results.md),
    [heavy-listening-results.md](../../docs/heavy-listening-results.md)).
  - **Make it dry first, always,** with `--recipe dry/<amp>` (below), because the
    installed presets are not (Wall Of Doom is transposed down 5 semitones).

    Then turn effects back on only where the research calls for them.
  - **Keep the baseline's amp, drive, pedals, EQ and cab.** Skip step 3's amp, drive,
    eq and cab recipe layers unless the research contradicts the baseline, and don't
    re-select the amp. A dry baseline chosen this way is the measured starting point,
    not the "renamed factory preset" failure step 3 warns about.
  - **If the file is missing** (an older or trimmed install), say so and use the
    clean template.
- **The dry recipe,** for every baseline in this step: `dry/pr12`, `dry/sw50r` or
  `dry/ac20` on Morgan, matching the baseline's amp, and `dry/toneking` on Tone King.
  On Morgan it sets transpose 0, the amp's spring reverb 0 (PR12 and SW50R; AC20 has
  none), and reverb, delay, tremolo, doubler and gate off, with the FX section itself
  on. On Tone King it turns reverb, delay, chorus and wah off, sets the amp's reverb
  and tremolo depth to 0 and opens the gate fully, with the time-effects section on.
  Both are as the baselines were measured. Stack it first, so your other recipes and
  the spec can turn an effect back on, with its parameters set explicitly. Preview it:

  ```bash
  python "${CLAUDE_PLUGIN_ROOT}/scripts/apply_spec.py" \
    --template BASELINE.xml --recipe dry/pr12 --out OUT.xml --dry-run
  ```

  with the baseline's full path, from the tables above, as the template.

  On the nine Morgan baselines it changes 1 to 5 settings each (on the two Tone King
  ones, 3 and 4): every one ships with the gate
  on, Wall Of Doom also with transpose −5, and Modern Metal (Pick Hard) with its FX
  section off, which the recipe turns on so an effect brought back is heard. The writer
  refuses another amp's recipe (`dry/pr12` on an SW50R preset), since it would change
  nothing you hear.
- **For a clean or crunch Tone King part, start from its factory baseline.** These are
  factory presets every owner has, under
  `/Library/Audio/Presets/Neural DSP/Tone King Imperial MKII/`, both on the Rhythm
  channel:

  | part | Tone King baseline |
  |---|---|
  | clean | `Artists/Richard Henshall/Vintage Trem.xml` |
  | crunch | `Artists/Adam Christianson/Squishy Lead.xml` |

  - **The evidence.** Chosen by rule on development recordings, then checked on
    reserved ones, measured, not heard
    ([toneking-baseline-results.md](../../docs/toneking-baseline-results.md)). Clean:
    about 12% closer than the plugin's Default made dry, on 12 of 13 parts from 8
    bands. Crunch: about 29% closer than a typical Rhythm-channel preset, on 7 of 7
    parts but only 3 bands, so say the evidence is thin. Each tied its runner-up (Spring
    Clean; Let 'er Rip and Rough Blues Lead): good starting points, not unique bests.
  - **Made dry, the names no longer describe them.** Vintage Trem becomes a lean,
    near-clean Rhythm tone (its tremolo, chorus and reverb are removed). Squishy Lead
    becomes a crunch rhythm sound: the Rhythm channel at full volume, the second
    overdrive pushing it, the compressor off. Present them as "the clean starting
    point" and "the crunch starting point".
  - **Make them dry first** with `--recipe dry/toneking`, and **keep the baseline's
    channel, amp settings, drives, compressor, EQ and cab**: skip step 3's amp, drive1,
    drive2, compressor, eq and cab layers unless the research contradicts the baseline.
    Above all, don't apply an `amp/*` recipe: every one sets the channel and the amp's
    controls, which undoes what was measured (on Squishy Lead it removes the crunch).
  - **If the file is missing,** say so and ask for one of the user's own Tone King
    presets.
- For a heavier Tone King part, there is no measured baseline: use one of the user's
  own presets, and if they have none, say so rather than stretching a clean or crunch
  one.
- One of the user's own presets is a fine template too, especially if it already
  uses the amp you want. Run `show.py` on it first.
- Either way, select the intended amp or channel explicitly through an amp
  recipe unless the inspected template already has the required value; a Tone King
  baseline keeps its Rhythm channel.

## 5. Write the spec, preview, apply

Build the spec JSON, then always `--dry-run` first and show the user the change
list before writing. See [preset-spec.md](../../reference/preset-spec.md).

Pass `--strip-irs` so the result is portable — see
[cab-and-irs.md](../../reference/cab-and-irs.md). If it warns that it stripped
nothing (Tone King declares no IR mapping), the listed paths are still in the
preset: tell the user rather than calling the result portable.

## 5b. From a song: offer to let the user hear four

When the user gave a song (a file, and where in it the guitar plays), **ask once**
whether they want to hear the preset beside three alternatives before choosing. Say in
a line what that is: a local page, ready in a few minutes, that plays four presets
through two short guitar riffs under the song excerpt, so they can pick one or ask for
a change. If they say no, or gave no song, go on to step 6 with the step 5 preset.

Why it is worth offering, and why it is not the default: choosing the best of four by
measurement landed about 18% closer than the template on 25 recordings
([the measurement](../../docs/song-only-shortlist-results.md)), but a listening check
of whether an ear does as well was inconclusive
([the check](../../docs/listening-check-results.md)).

If they say yes:

1. **Write three alternatives** beside the preset from step 5, as copies of it with
   their own specs. Use at least two amps (on Tone King, both channels: the dry baseline
   stays on Rhythm, so at least one of the other three uses the Lead channel), and make them
   differ in amp, gain, drive, EQ or cab, not only in reverb or delay: the measured
   lists were too alike to gain much. On Morgan, the shipped template as it is can be
   one of the four. Make the chosen amp's dry baseline from step 4 one of the four (clean,
   crunch or driven, by the part), made dry with `--recipe dry/<amp>`
   (`dry/toneking` on Tone King).
2. **Render them beside the song.** The page plays every preset through two shipped
   guitar riffs (strummed chords and a single-note line), at one loudness, under the
   song excerpt:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/audition.py" --song SONG.mp3 \
  --start START_SECONDS --out-dir AUDITION_DIR \
  --preset A.xml --note "what A is" --preset B.xml --note "what B is"
```

   Use a folder under the data root for `AUDITION_DIR` (`auditions/<song>`), and add
   `--open` to open the page. To listen on a phone, give the user the path to
   `phone.html` in that folder (macOS): the same page with the audio inside, as one
   file. Open it in Safari or Chrome, not a file preview. Rendering takes about 10 seconds a preset per riff, so
   give the command a few minutes, or run it in the background; if it stops partway,
   the presets it finished are kept and `--add` renders the rest. The riffs are not the song's part, so ask the user to
   listen for gain, brightness, body and space, not the notes.

   **To compare starting points** (always when the part is not clean or its class is a guess, and whenever
   the user is unsure how much gain it has), add the amp's other starting point from
   step 4 beside the one already among the four: crunch if the four hold the clean
   one, clean if they hold crunch, and for a heavier part, crunch beside the driven
   one. Write it dry, into the
   audition folder under its own name; writing directly is fine for a listening copy,
   but preview with `--dry-run` (step 4) if the user keeps it. Use the baseline's own
   amp's recipe (`dry/pr12`, `dry/sw50r`, `dry/ac20` or `dry/toneking`):

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/apply_spec.py" \
  --template BASELINE.xml --recipe dry/pr12 --out AUDITION_DIR/crunch-start.xml
```

   Then add it with a plain note, `audition.py --add AUDITION_DIR --preset
   AUDITION_DIR/crunch-start.xml --note "crunch starting point (weaker evidence)"`.
   Say how strong each starting point's evidence is, in step 4's words; none has been
   confirmed by ear.

3. **Refine.** The user picks one, or says what is off ("B, but darker"). Make the
   change on a copy with the edit skill's steps 1–4 (read, interpret, change only
   that, preview and write a new file; don't install yet), then add it to the page:
   `audition.py --add AUDITION_DIR --preset B2.xml --note "B, darker"`. Repeat until
   they keep one, then install that one (step 6) and bank what they changed (step 7).

## 6. Install and report

Write the preset into the user's preset folder and tell them how to load it —
see [installing.md](../../reference/installing.md).

**When the part is not clean, or its class is a guess, install a second starting
point beside it,** with or without the listening page, unless the user already chose
between the two starting points there: the amp's clean starting point (step 4) for
a crunch part, its crunch starting point for a heavier one or a guessed clean one,
made dry, named "… (clean start)" or "… (crunch start)". On Tone King, a heavier part
built on the user's own preset gets the crunch baseline beside it. The evidence comes
from the three Morgan amps. Tell the user to try both: the gain class is the
step most often wrong from a song, and a wrong class costs far more than any edit
([generate-routing-results.md](../../docs/generate-routing-results.md)).

Then report:
- which **template** you cloned and which **amp or channel** you selected
- the **class** you chose (clean, crunch or heavier), what documents it for this part,
  or that it is a guess, and the second starting point you installed
- what **research** the tone is based on, with links, and that the result is a
  starting point: on 25 mostly clean recordings, a researched preset was not shown to
  land closer than the shipped template, and a researched list of four was not shown
  to beat four random factory presets ([the measurement](../../docs/song-only-shortlist-results.md))
- anything you set **outside a declared range**, and why
- any **unconfirmed selector** the tool warned about
- any **guessed kind** the tool warned about (draft packs): the value was written
  through a mapping nobody has checked, so ask the user to confirm it looks right
  in the plugin

## 7. Bank what you learned

Append an entry to the `learned_notes` path that `show.py` reports — creating
the file if it doesn't exist. Record:

- the **recipes you stacked** and the **values you changed**, with why
- what the user **pushed back on**, if they did. "Too dark, ended up at 45%" is
  worth more than a successful first try, because it's the thing generic
  guidance got wrong.
- the **source link** for the research

Keep the entry concise and actionable. The notes live under the data root, not
in the plugin directory: Claude Code replaces the plugin on update, and
anything written there would be lost. Append to the same path you *read* in
step 3 — if you passed `--data-dir` to find the notes, pass it here too, or the
entry lands somewhere the next run will not look.

Worth recording beyond the values: a window you had to choose by hand and why
the automatic one was wrong, and any measured band you decided **not** to act on
because the regime made it untrustworthy. Both are the kind of thing the next run
would otherwise rediscover the hard way.
