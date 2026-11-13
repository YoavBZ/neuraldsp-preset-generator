# The model path: a preset from the song itself

`generate`'s default sets the controls from research (its steps 2 to 5). The model path sets them from the song's
audio with the trained model instead. It sits behind a flag. Use it **only when the user asks for it**, for example
"use the model" or "make it from the audio". The user's real-song test decides whether it becomes the default.

## What it needs

- A song file, and the part's class (clean or crunch), from step 2's research.
  - The model knows these two classes only.
  - For a heavier part, or when the class is a guess, say so. A wrong class changes both the answer and the amp pick,
    and that is unmeasured.
- Where the part starts, when the user names it.
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
  --start START_SECONDS --work WORK_DIR --out OUT_DIR/model.xml --name "NAME"
```

   - **Pass `--start` whenever the user names the part.** Without it, the script takes the 10 seconds where the guitar
     is most exposed against the mix, which can land on a solo. Say which window was used.
   - Use a folder under the data root for `WORK_DIR` (`~/ndsp-presets/auditions/<song>/model`).
   - It separates the guitar, takes the model's settings on each of the three amps and renders them through two stock
     guitar recordings (12 renders). It picks the amp whose renders sound closest to the song's guitar, sets the output
     so the preset plays at the factory start's loudness, and writes the result onto that amp's factory starting
     preset.
   - A stopped run resumes with the same command.
3. **Add the effects from research** (reverb, delay, modulation, doubler) with `apply_spec.py`, as in step 5:
   - use `--template OUT_DIR/model.xml`, a spec of those effects only, and `--strip-irs`;
   - keep the dry run first.
   - Don't change the input gain, amp, EQ, pedals, gate, mics or output: those are the model's. The amp's own spring
     reverb counts as an effect (the model was rendered with it at 0), so research may turn it up.
4. Install and report as in step 6. Say:
   - that the model set the controls;
   - the amp it picked, and the window it read (given, or the most exposed);
   - the output change;
   - the limits below.

## What is known, and the limits

- **What it was read on:** reamped and stock-DI sets of clean and crunch parts (the ML session's reads), not real
  songs. By the score the model reads level with the one it replaced. By the score the amp pick beats always-SW50R on
  one set and is worse on none (F81). By ear it was heard closer than the model's own amp pick (F83), and undecided
  against always-SW50R. The output matching closed the loudness gap (F84), and a short page showed no bias by ear.
  - The pick has not yet been read on a separated guitar (A2s, declared). The ML session's real-song test reads the
    whole path on songs, and it decides the default.
- **Loud peaks.** At the matched loudness about 2 in 3 presets peak over 0 dBFS, as the plugin renders in floating
  point. Tell the user to lower the output a little if their host clips.
- **Effects** stay the research's: the model was trained with them off.
- **What the model sets:** the input gain, the amp, both mics, the EQ, the pedals and the gate. The rest of the cab
  (room mics, pan, phase) stays the factory start's.
- Every guitar there played at one input level. A much louder or quieter guitar drives the amp differently.

Where it comes from: `learn/product_path.py`, the ML session's single copy of the validated steps;
[full-controls-plan.md](../docs/full-controls-plan.md), "The model path".
