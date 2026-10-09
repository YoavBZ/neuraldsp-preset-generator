# Roadmap

## Product target

Generate a usable guitar preset from a song and a time range. The user should not
need to record a DI. The preset should approximate the recording when played
through a representative guitar, including songs with several guitar parts.
Use locally runnable, open-source models and tools for learned methods.

## Current capabilities and limits

- `generate` researches the recording, measures supplied audio, writes a preset,
  and optionally offers a listening shortlist. Automatic song-only selection has
  not demonstrated reliable improvement over its starting preset.
- `match` measures supplied reference audio. Without the same performance's DI,
  it keeps the starting preset. With that DI, it can search controls; its current
  search objective still needs validation against the listening-validated judge.
- `edit` changes an existing preset from a plain-English description.
- The judge requires the same performance's DI. Listening validation covers clear
  differences between clean-to-crunch Morgan PR12 renders. High-gain, layered
  guitars and comparisons across different performances need separate validation.
- Learned DI recovery has not passed final preset-selection confirmation on
  Morgan SW50R or PR12. Success at recovering a dry signal through a single clean
  chain does not establish useful preset selection on real songs. No learned
  recovery or ranking model is approved for the plugin's matching workflow.

## Priorities

1. **Establish a useful song-only selection method.** Require a cheap comparison
   against the starting preset and a song-blind baseline on real development
   recordings before long training or large rendering runs. An improvement on
   synthetic renders alone is insufficient.
2. **Validate the intended input.** Include full mixes or separated guitar stems,
   different performances, and songs with several guitars. Define the target guitar
   or combination of guitars before scoring. Do not infer this coverage from tests
   on isolated single-guitar amp tracks.
3. **Improve audition comparability.** Match the audition riff's playing style to
   the reference: chords, single notes, arpeggios or power chords. A tone comparison
   through unrelated notes can be misleading.
4. **Broaden measurement coverage.** Validate high-gain examples, hiss and drive
   differences at matched spectrum. Run positive controls before relying on a
   measurement to choose presets.
5. **Resolve known matching defects.** Check Tone King's startup mute, Morgan's
   reused-instance history, inversion mix assumptions, tremolo detection and search
   handling of level, spectral extremes, ambience, decay and stereo.

## Validation constraints

Keep development and confirmation material separate. The third guitar validation
set's reserved split has already been used for final confirmation; it cannot be
used again to claim an independent final test or to tune a model. New confirmation
requires fresh material and an agreed procedure.

Retain only current product decisions and necessary validation constraints in this
plan. Experiment logs, agent reports, repeated reviews and session checkpoints
belong outside the repository.
