# Arm A levers: results (2026-10-16)

Run under the [plan](arm-a-levers-plan.md), on development data only: estimates, not bars. Every
figure was recomputed by an independent audit (`~/ndsp-presets/learn/song-settings/levers/audit/`).
The stored searches replay exactly, and a re-render matched the stored main-stage best within
2e-5. These are post-hoc estimates and need a fresh draw before shipping.

All figures are held-half log ratios against S (the starting preset), band-weighted, with 90%
band-clustered intervals; negative means closer to the record. The data is 142 directions, 24
parts and 14 bands.

## Experiment 1: what to do with arm A's settings

| Variant | Against S |
|---|---|
| A (150 renders) | −0.078 [−0.157, +0.002] |
| A, moves shrunk halfway to S | −0.082 [−0.136, −0.028] |
| A, shrunk a quarter (0.75) | −0.087 [−0.157, −0.017] |
| A, shrunk three-quarters (0.25) | −0.053 [−0.088, −0.018] |
| A with S's mics | −0.040 [−0.116, +0.036] |
| S + half of (B − S) | −0.012 |
| S + half of (constant − S) | −0.011 |
| The C′ menu pick | −0.016 |

- **Shrinking halfway keeps the gain and narrows the downside.** The difference from A is
  −0.004, which is noise.
- **A's mic changes matter:** undoing them loses about half the gain.
- **Blending B or the constant adds about nothing.**

## Experiments 2 and 2b: which rebuild

- **Menu rank fidelity on fold 3's parts:** C′ 0.776, 1z 0.795, 1a 0.754, 1b 0.786, and their
  ensemble 0.792. All tie.
- **Local fidelity around S,** from 40 settings per part and amp on the true-DI search paths: C′
  −0.126 [−0.54, +0.29], and the same for every net.
  - **Near S, every rebuild's objective ranks nearby settings no better than chance, or
    inverted.** This is stable across halves, so it is a systematic local bias, not noise.
  - It splits by band (Eggy positive, the two Cambridge bands negative).
  - Input gain is where it disagrees most.
- **Reading:** a better network (the fine-structure arms) doesn't fix this. The rebuild guides
  coarse moves, not fine ones. The fold 0–2 fine-tunes were stopped as not needed.

## Experiment 3: stopping the search early

| | Against S | Against A |
|---|---|---|
| A stopped after its 52-render main stage (3-C′) | −0.085 [−0.164, −0.006] | −0.007 [−0.031, +0.016] |
| 3-C′, shrunk halfway | **−0.083 [−0.135, −0.032]**, 12/14 bands | +0.002 against 3-C′ |

- **Stopping at a third of the renders loses nothing.** A's later fine moves are noise, which
  fits the local-fidelity finding.
- **Shrinking halfway on top costs no renders and narrows the downside:**
  - worst band +0.03, against +0.16;
  - 40 directions worse than S, against 48;
  - part-weighted −0.055 [−0.091, −0.020].
- **Honest expectation after picking the best of several variants:** about −0.07 [−0.13, −0.01].
  Choosing on 13 bands and scoring the 14th gives −0.072.
- **The product needs a fallback to S:** about 1.4% of directions set a master volume to 0 and
  render silent.

## What it teaches

- **The rebuilt-DI search works coarsely.** About a third of the true-DI search's gain is
  reachable: −0.08 against −0.27. That comes in the first 52 renders.
- **What limits it now is local bias, not search budget or network quality.**
- **The next lever is therefore an objective that ranks well near S.** That means a different
  scoring route (a hedge, a verifier, or the codec route) rather than a better C′ of the same
  kind. Another option is to keep the rebuild for coarse moves only and get fine settings
  elsewhere.
