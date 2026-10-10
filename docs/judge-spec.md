# The judge's specification

Written 2026-10-10, after the [closeness review](closeness-review-2026-10-10.md) and
[judge v2](judge-v2-results.md). It lists what the judge (`analysis/aligned.py`) must do
to be trusted, each with its reason, and the test that checks it. Any judge version is
held to it.

- **Synthetic checks** (`tests/test_judge_spec.py`) run in CI. The rigs are shaped like the
  set-3 development recordings octave by octave: a typical driven part, a bass-heavy one
  like Ill Fate, a dark clean one, and an open-topped one.
- **Checks on stored renders** (`tests/test_judge_spec_data.py`) run where
  `~/ndsp-presets` is present. Development renders only.
- **A property a judge is known to break** is marked `xfail(strict=True)` with the
  reason. A fix that makes it hold fails the run until the mark is removed, so every
  change in what the judge does shows.

"Costs" below means the distance from the recording to the changed copy.

## The properties

1. **The same audio is at zero.** Anything else means the judge measures something
   other than the difference.
2. **Level doesn't count**, on either side. Output level is a separate control, and the
   renders and recordings come at arbitrary levels.
3. **Time alignment is right.** The lag found is the true one, across rigs and inverted
   polarity, and the DI's timeline follows the lag and the plugin's latency. A frame-wise
   judge compares the wrong instants otherwise.
4. **An EQ change costs more as it grows, roughly in proportion.** Boosts and cuts of 1,
   3 and 6 dB at 200 Hz, 800 Hz, 2.5 kHz and 6 kHz, on a driven part:
   - strictly increasing, and 1 dB already costs something;
   - 6 dB costs 1.6–2.4 times what 3 dB costs;
   - no octave where the guitar sounds is close to free (the dearest 6 dB change costs at
     most 3.5 times the cheapest).

   This is what lets a search follow the judge: it must point the right way, and a bigger
   mistake must look bigger.
5. **A tilt costs more as it grows, either way:** ±0.5, 1 and 2 dB per octave, on driven
   and bass-heavy parts.
6. **A boost and the same cut cost alike** (within 20%): ±6 dB bells, ±12 dB shelves at 2,
   4 and 6 kHz, and ±12 dB on a quiet region of an even spectrum. A judge that forgives
   cuts favours dark candidates, and v2's strength was partly this
   ([results](judge-v2-results.md)).
7. **More drive costs more:** ×1.5, ×2 and ×4 of the recording's drive, on driven and
   bass-heavy parts. Drive is the main high-gain control.
8. **Fizz above the recording costs more as it grows.** Band-passed (5–12 kHz) clipping at
   −40, −30, −20 and −10 dB:
   - non-decreasing, and strictly increasing from −30 dB;
   - at −10 dB it costs at least a +3 dB octave at 800 Hz;
   - on dark and bass-heavy parts, so does −20 dB.

   "Too fizzy" is the main failure of high-gain amp sims, and the review found winners
   13–41 dB too bright that the judge didn't see.
9. **Reverb and echo cost more as they grow:** a 1.2 s reverb at −30, −20 and −10 dB, and a
   420 ms echo at −12 and −6 dB. The v3 search objective missed time effects, and the
   listener heard them.
10. **A small time shift costs more as it grows** (1, 3 and 10 ms). Attack and timing are
    part of the sound.
11. **Treble is heard on bass-heavy recordings.** A treble change (+6 dB at 2.5 or 6 kHz,
    ±12 dB above 5 kHz) costs on a bass-heavy part at least half what it costs on a
    balanced one. A loud low end doesn't mask 2.5–10 kHz.
    - On stored renders: the same, on Ill Fate 1's recording against The Well 1's
      (+3 dB at 1.6 kHz, ±12 dB above 5 kHz).
12. **Missing and excess content cost alike.** Swapping recording and render changes the
    distance by at most 10%, on fizz, a bright shelf on a bass-heavy part, fizz on a clean
    part, more drive, and reverb.
    - Otherwise a render lacking what the recording has is judged by a different rule
      from one with the same thing extra, and one direction is systematically preferred.
13. **No dependence on mel-band width.** On an even spectrum, the same change to a region
    of equal mel width costs the same (within 25%) low, where mel bands are narrow, as high,
    where they are wide.
    - Floors and band choices must not depend on how much bandwidth a band happens to sum.
14. **The ranking holds across halves.** Ten unlike candidates, ranked on two halves of
    one performance, must agree (Spearman ρ ≥ 0.9, same winner). On stored renders:
    half A and half B rank the 99 set-3 development menus alike, median ρ ≥ 0.95 and 10th
    percentile ≥ 0.7. The default judge scores 0.984 and 0.826.
    - A judge that changes its mind between two takes of one part cannot pick presets.
15. **What can't be judged is refused, not scored.** A silent DI, a silent render, under a
    second once aligned, a window mostly of pauses, a recording inaudible where the DI
    plays (all give `distance=None` and a reason), and non-finite or channels-first input
    (a `ValueError`).
16. **Noise far under the guitar isn't rewarded** for imitating the recording's own hiss.
    This is a property of the validated design; it is kept so that a new floor doesn't
    lose it.
17. **The stored distances reproduce from the audio** (to 1e-12), so the judge as coded is
    the judge whose numbers the docs quote.

## Where the current judge stands

The default judge (`bands="recording"`, `weighting="flat"`) holds properties 1–5, 7, 9,
10 and 14–17, and breaks five:

| Property | Measured | Why |
|---|---|---|
| 6. Boost and cut alike | ±12 dB above 4 kHz: 2.20 against 1.79; quiet region: 0.78 against 0.38 | The floor comes from the recording alone, so a cut into it is clamped while the boost counts in full. |
| 8. Fizz | Clean part: −10 dB of fizz costs 0.40, under a +3 dB octave (0.59); bass-heavy: 0.06 | The scored bands stop below the treble on dark parts. |
| 11. Treble on bass-heavy parts | +6 dB at 2.5 kHz: 0.36 against 1.42 on the balanced part; Ill Fate: +3 dB at 1.6 kHz costs 0.0002 against 0.88 | Bands and floor sit 30/40 dB under the loudest band, the fundamental. |
| 12. Missing against excess | Fizz at −20 dB: 0.51 one way, 1.64 the other | Bands and floor come from the recording only. |
| 13. Band width | A 12 dB cut of a quiet region: 0.38 low, 0.85 high | The mel filters aren't area-normalised: a wide treble band reads up to 13 dB louder. |

Judge v2 (`bands="fixed"`) is also tested. It holds 8, 12 and the synthetic part of 11,
and breaks three:
- **6 and 13,** for the same reasons: it keeps the default's floor and mel bands.
- **11 on Ill Fate's recording.** It scores every band, but the per-frame floor (40 dB
  under the fundamental) still clamps the recording above about 700 Hz. There, +3 dB at
  1.6 kHz costs 0.03, against 0.81 on The Well 1. The synthetic bass-heavy rig is less
  extreme frame by frame than Ill Fate, so only the stored-render check catches it.
