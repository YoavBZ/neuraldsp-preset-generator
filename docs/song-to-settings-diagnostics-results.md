# Arm B diagnostics: results (arm-B rethink experiment 1, 2026-10-16)

Run under the [plan](song-to-settings-diagnostics-plan.md), with amendment 1 (readings
descriptive, by the user's rule of 2026-10-16) and its implementation notes.
- **Scope:**
  - 120 fresh development targets, each rendered through the measure DI;
  - each predicted by the fold model that never saw its band;
  - 15 sensitivity bases.
- **Renders:** 7,890, plus 21 in the audit.
- **Data:** `~/ndsp-presets/learn/song-settings/diag/`, with the audit in `diag/audit/`.
- **Independent audit:** every reading was recomputed to 4 decimals. Fold models, seeds,
  baselines, the measure DI and the single timeline were all verified.

## Fixes found by the audit

- **The set-up check:** it counted 8 targets with a refused half as failing the repeat check.
  - Their halves were silent: master volume or level near 0 on 4 targets, and DI pauses over
    the 50% limit on 4.
  - The plan drops such halves as non-finite units. The fixed check passes. The finite repeats
    are at most 8e-4 against 1e-3.
- **The calibration (PIT):** it kept only clipped values (a float-type bug).
  - Recomputed, it is roughly calibrated, slightly overconfident in the tails (PIT SD 0.30–0.36
    against 0.289).
- Both are fixed in `learn/song_diag.py`, with tests.

## What arm B does on fresh render targets

Band-weighted log ratios, 228 units, with 90% band-clustered intervals; negative means closer to
the target.

| | Against S | Notes |
|---|---|---|
| Top prediction, light view (guitar + backing) | −0.39 [−0.48, −0.30], 14/14 bands | beats S on 78%; median 27% of the gap closed |
| Top prediction, song-like view (mastered, separated) | −0.16 [−0.26, −0.06], 10/14 | beats S on 66%; median 12% |
| Best of 8 samples, picked by the true judge (song-like) | −0.54 | −0.17 [−0.28, −0.07] against the best of 8 random bank labels |

- **Arm B has real signal on renders.** It is 15–40% closer than the starting preset depending on
  the input view.
- **Mastering and separation halve that gain.**
- **Best-of-8 is mostly "8 renders, judged":** 8 random labels alone get −0.37. The model adds
  about −0.17 on top.

## Why it doesn't carry over to songs (step 3: +0.035 against S)

- **The model is weak even in its own domain.** The light view is exactly the bank's training
  branch, and it reaches only 27% of the gap.
- **One wide mode per setting:** the mixture components sit within a third of σ of each other
  (the collapse flag). So sampling gives the top mean plus prior-width noise.
- **Its prior points the wrong way on records.**
  - K_S's optima on records sit at a range limit on 35% of settings, against 20% on the render
    targets, while the model shrinks toward mid-range.
  - Ranking a song's stored K_S path by the model's density prefers settings *farther* from the
    record (ρ +0.13 [+0.03, +0.24]).
  - The song-specific part of that density is right, but small: −0.07 [−0.12, −0.03].
- **It is weakest where it matters most.**
  - **What matters most:** switches and gain staging (median judge change 0.75–2.65 for a 0.15
    move or a flip). Tone knobs come next (0.33–0.44), then cab position (0.17–0.30).
  - **The model:** input gain correlates only 0.24–0.33; cab position and distance correlate
    best (0.54–0.64).
- **Settings that sound alike are broad.** Without the target's own jitters, 49–60% of the
  candidates that close the gap are at least 0.2 from the target in knob space. Mics match the
  target only 10–23% of the time.

## What follows

- **The declared trigger, row 7, leads to experiment 2** (an isolated-DI retrain). The audit
  judges its value as modest: the light view is already in distribution and reaches 27%.
- **Best supported: 3B, training in sound space.**
  - It addresses the single wide mode, the broad equal-sound sets, the mid-range shrinkage and
    the weakness on gain and switches.
  - **Labels:** relabel the bank by rendered closeness (render in the loop).
  - **Record-like targets:** draw labels around record K_S optima.
  - A flow head on the same knob loss would learn the same wide blob.
- **3A (a verifier picking among samples) is capped.** A perfect pick among 8 closes at least
  half the gap on about 37% of units.
- **Cheap bridges for any new model:**
  - **The zero-render density check** on step 3's stored K_S paths. It takes minutes.
  - **Best-of-8 B samples on step 3's songs** (about 1.15k renders), against K_S at 8 renders
    (−0.08). This needs the user's yes, as a repeat use.

## Stated limits

- Development data only; render targets, not records.
- One model architecture.
- The knob-space landscape figures are proxies.
- The right-cab settings read "flat" only because the cab is off in 30–45% of bases.
