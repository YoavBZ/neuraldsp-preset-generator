# Every control, stage 0: results (2026-10-22)

Run under the [plan](every-control-plan.md) ("Stages 0 and 1, as built", and amendment 1).
Development data only, true DI, no training. Ledger entry `every-control-stage0`.
- **Code:** `learn/every_control.py`, tests `tests/test_every_control.py`.
- **Data:** `~/ndsp-presets/learn/every-control/`: `amp-choice.json`, `screen.json`,
  `tk-smoke.json`, `logs/` (`amp-choice.log`, `screen.log`, `tk-smoke.log`, `stage0-chain.log`).
- **Renders:** 94 (the screen 60, Tone King's smoke 34); amp choice reads stored cells.
- **Readings set priorities, never membership** (amendment 1): every control is learned.

## Headline

- **Amp choice pays: high priority.** Picking the amp by its searched score beats an amp chosen
  blind by **−0.044 [−0.062, −0.026]**, 22 of 24 parts and 13 of 14 bands better.
- **No screened control is invisible to the judge.** Every one moved the score by more than 0.005
  in at least one cell. Cab phase moves it most.
- **Tone King's search renderer works.** It repeats the stored start score to about 3e-6 (log),
  at about 1.5 s a render.

## 0b. Amp choice (zero renders)

From knob ceiling's stored K_S cells (24 parts × 3 amps × 2 directions). Per part: the held half
of the amp with the best K_S search half, minus the mean of the three amps' held halves (log).

| Rows | Part-weighted mean, 90% band-clustered | Band-weighted | Parts better | Bands better |
|---|---|---|---|---|
| All | **−0.044 [−0.062, −0.026]** | −0.048 | 22 / 24 | 13 / 14 |
| Clean | −0.042 [−0.064, −0.019] | −0.045 | 17 / 19 | 8 / 9 |
| Crunch | −0.054 [−0.095, −0.012] | −0.054 | 5 / 5 | 5 / 5 |

- **Leave one band out:** −0.051 to −0.039.
- **What it is:** the worth of choosing among the three amps once the knobs are searched, with the
  true DI. Each amp's figure comes from one 150-render search, so it is a lower bound per amp.

## 0c. What the judge can hear (60 renders)

S with one control moved at a time to the far end of its range: Morgan on 3 cells (PR12, SW50R,
AC20), Tone King on 2 (clean, crunch). The rule: invisible if |log| ≤ 0.005 on both halves in
every cell. Repeat renders agreed exactly on Morgan and to 4e-6 on Tone King.

| Control | Largest move (log) | All cells |
|---|---|---|
| Tone King cab phase | 0.596 | 0.596, 0.047 |
| Morgan cab phase (both cabs on) | 0.296 | 0.296, 0.017, 0.213 |
| Morgan doubler spread | 0.053 | 0.018, 0.011, 0.053 |
| Morgan delay width | 0.024 | 0.024, 0.009, 0.009 |
| Tone King cab pan | 0.022 | 0.022, 0.002 |
| Tone King delay stereo mode | 0.018 | 0.000, 0.018 |
| Morgan delay ping-pong | 0.015 | 0.015, 0.004, 0.003 |
| Morgan cab pan | 0.008 | 0.008, 0.000, 0.004 |
| Morgan cab stereo | 0.007 | 0.000, 0.007, 0.000 |

- **Invisible by the judge's maths, no renders:** output gain (the judge removes level) and a
  single cab's pan (the mono fold). These are learned against another target (amendment 1).
- **0.005 is a size bar, not a noise bar.** The small ones (pan, stereo, ping-pong) are below it in
  most cells.

## 0d. Tone King's search renderer (34 renders)

One clean part (Drag Me Down ElecGtr4, Vintage Trem). The start repeats the stored score by
3.4e-6 and 9.5e-7 (log; the bar is 0.005), and again after the search. The canonical start matches
the raw one to 2e-8. Median 1.49 s a render, 54 s for 34 renders. The 30-render smoke search
moved its search half by about −0.20 (log). That is one cell's search half, descriptive only.

## Limits

- **Read before the trusted-data rule (2026-10-22), on all parts.** Knob ceiling's 24 parts include
  the audit's 4 high-bleed ones (First Offering GTR 1, Gym Hours GTR 1, Long Way Home,
  Sculptor's Request GTR 1), and First Offering GTR 1 is a screen cell. 0b can be re-read on the
  trusted parts from stored cells, at zero renders.
- **The screen is a screen, not a proof:** 5 cells, one move per control.
- **Development parts already read by earlier steps,** one take per part.

## Next

- **Stage 1 waits for the trusted set** from the user's data review (the user's decision), and runs
  on trusted parts only ([ROADMAP](ROADMAP.md), step 0).
- **Amp choice enters both routes at high priority:** a searched control in arm A, a 3-way head in
  the direct model.
