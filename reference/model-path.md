# The model path: a preset from the song itself

`generate`'s default sets the controls from research (its steps 2 to 5). The model path sets them from the song's
audio with the trained model instead. It sits behind a flag. Use it **only when the user asks for it**, for example
"use the model" or "make it from the audio". The ML session's real-song test, and the user's yes, decide whether it
becomes the default.

## What it needs

- A song file, and the part's class (clean or crunch), from step 2's research.
  - The model knows these two classes only.
  - For a heavier part, or when the class is a guess, say so. A wrong class changes both the answer and the amp pick,
    and that is unmeasured.
- **The part's span** in the song file, start and end in seconds, at least 10 s long (more gives the script windows to
  compare; a shorter section the user names is fine at 10 s or more): the section the user names,
  else the song's main guitar part from step 2's research (its time from synced lyrics, timestamped tabs or the
  song's structure, kept a second or two inside the section's edges).
- **Morgan Amps Suite (original) only.** It is not on Morgan X or Tone King.
- The machine the model lives on: `~/ndsp-presets` with the model's data and its environments (msst-venv, the torch
  venv and the main `.venv`). Elsewhere the script refuses, and the research path is the answer.
  - From the installed plugin, set `NDSP_MAIN_PY` to the repository's `.venv/bin/python` (an installed copy has no
    `.venv`); the other two are found under `~/ndsp-presets/tools`.

## The steps

1. Research the part as in steps 1 and 2, for the class and the effects.
2. Run the model:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/model_preset.py" --song SONG.mp3 --cls clean \
  --part PART_START PART_END --part-from "the user" --work WORK_DIR --out OUT_DIR/model.xml --name "NAME"
```

   - **Always pass the part with `--part`.** `--part-from` says who named it: `"the user"` or `"research"`. The model
     reads one 10-s window. The script takes the most typical one inside the part (1-s steps, clear of the track's first
     and last 2 s), among the windows where the guitar holds steady throughout and sits within 12 dB of the mix. If
     none qualifies it falls back to the steady ones, then to all, and says so. Without `--part` it searches the whole
     song, which may land on a part the user didn't mean. `--start` forces a window with no checks; use it only when
     the user names an exact moment, or a section shorter than 10 s (start it there). Say which window was read and
     how it was chosen.
   - Use a folder under the data root for `WORK_DIR` (`~/ndsp-presets/auditions/<song>/model`).
   - It separates the guitar, takes the model's settings on each of the three amps and renders them through two stock
     guitar recordings (12 renders). It picks the amp whose renders sound closest to the song's guitar, sets the output
     so the preset plays at the factory start's loudness, and writes the result onto that amp's factory starting
     preset.
   - A stopped run resumes with the same command.
   - **The delay reader, only when asked for:** add `--delay-reader` to this command. It is the real-song test's third
     arm, a candidate, never a default. Give research's delay mix and feedback as `--delay-mix` and `--delay-feedback`
     (0 to 1, both or neither). Without them it uses 0.30 each, a default the user has yet to confirm. When it hears a
     delay, it switches it on at the time it read. When it hears none, the delay is left to step 3. It doesn't read the
     echo's tone (ping-pong, tape drive, width, low and high cut). Its figures were measured with those drawn at
     random, so they don't assume the factory start's.
3. **Add the effects from research** (reverb, delay, modulation, doubler) with `apply_spec.py`, as in step 5:
   - use `--template OUT_DIR/model.xml`, a spec of those effects only, and `--strip-irs`;
   - keep the dry run first.
   - if the delay reader switched the delay on, keep its on, sync, time, mix and feedback out of the spec. Set the echo's
     tone (ping-pong, tape drive, width, low and high cut) from research where it describes it (darker repeats, tape,
     mono or ping-pong), else leave the factory start's. Say which you set.
   - Don't change the input gain, amp, EQ, pedals, gate, mics or output: those are the model's. The amp's own spring
     reverb counts as an effect (the model was rendered with it at 0), so research may turn it up.
4. Install and report as in step 6. Say:
   - that the model set the controls;
   - the amp it picked, and the window it read with how it was chosen (the script's window line, fallback included);
   - the output change;
   - with the delay reader, its line: on or off, the time, and where the mix and feedback came from;
   - the limits below.

## What is known, and the limits

- **What it was read on:** reamped and stock-DI sets of clean and crunch parts (the ML session's reads), not real
  songs. By the score the model reads level with the one it replaced. By the score the amp pick beats always-SW50R on
  one set and is worse on none (F81). By ear it was heard closer than the model's own amp pick (F83), and undecided
  against always-SW50R. The output matching closed the loudness gap (F84), and a short listening page showed no bias (5 of 12 heard quieter, 1 louder; p 0.22).
  - The pick was also read by the score on the separated guitar of those sets, the input this path uses, and holds
    there (F90). It has not yet been read by ear on real songs. The ML session's real-song test reads the whole path
    on songs, and it decides the default.
- **The delay reader** (only with `--delay-reader`), on synthetic songs:
  - it caught about a quarter of audible delays;
  - about 6 in 10 of the delays it switched on were real when half the songs had one, and 3 in 10 when a quarter had;
  - its time was within 10% only about half the time, and that figure is optimistic.
  - On real songs more false echoes are expected (F89).
- **Loud peaks.** At the matched loudness about 2 in 3 presets peak over 0 dBFS, as the plugin renders in floating
  point. Tell the user to lower the output a little if their host clips.
- **Effects** stay the research's: the model was trained with them off.
- **What the model sets:** the input gain, the amp, both mics, the EQ, the pedals and the gate. The rest of the cab
  (room mics, pan, phase) stays the factory start's.
- **Sparse parts:** a clean part with rests of half a second or more can fail the steadiness check, so the window may
  move to a denser passage of the part, or fall back as above.
- Every guitar there played at one input level. A much louder or quieter guitar drives the amp differently.

Where it comes from: `learn/product_path.py`, the ML session's single copy of the validated steps;
[full-controls-plan.md](../docs/full-controls-plan.md), "The model path".
