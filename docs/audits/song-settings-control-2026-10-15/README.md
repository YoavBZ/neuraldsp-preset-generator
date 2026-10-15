# Audit of arm A's known-target control (2026-10-15)

These are the scripts and outputs behind the "Recorded outcome" section of
[song-settings-plan.md](../../song-settings-plan.md). They are kept so the figures there can be
traced.

- `diag1.py` / `diag1.out`: per cell, the fold, lengths, LUFS, coherence, GCC lag and tilt of
  the rebuilt DI against the raw DI, the measure DI and the fake recording.
- `diag2.py` / `diag2.out`: the re-EQ curves (avg_fold2 − avg_fold f) by band, and the rebuilt
  DI's band levels against the measure DI.
- `diag3.py` / `diag3.json`: S and the target settings rendered through the rebuilt DI (and
  through an oracle-EQ'd rebuild), judged against the fake recording at lag −52 and lag 0.
  About 60 renders, `isolate=True`.
- `diag4.py` / `diag4.out`: the frame envelope correlation, the envelope RMS difference and the
  crest factor of the measure DI against the rebuilt DI.

The scripts used absolute paths to the worktree and ran on 2026-10-15. The outputs of diag1,
diag2 and diag4 were regenerated that evening from the same inputs.
