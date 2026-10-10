# Cutting the rebuilt DI's incoherent top end: plan (set 3, development)

Declared 2026-10-10, before any render below. No training.

## Why

- **Above 3 kHz the rebuilt DI is unrelated to the true DI** (coherence about 0.00–0.02,
  [gap split](set3-gap-split-results.md)).
- **Boosting that region to the true level made picks worse.** The extra wrong signal
  drives the amp.
- **Training doesn't fix it.** Neither longer training nor more guitars moved the
  picks ([pilot](di-network-v2-plan.md)).

So test the opposite: remove the region the network cannot rebuild, and let the amp
see only the part it can.

## Method

- **Material:** the 33 development parts and three menus, as in the gap split. Amp
  tracks only.
- **DIs:** the stored rebuilt DIs (`phase2-set3/net`), unchanged otherwise:
  - **`lp3k`:** low-passed at 3 kHz (fourth-order Butterworth magnitude), then set back
    to −22.9 LUFS;
  - **`lp6k`:** the same at 6 kHz.
- **Picks and scoring:** `learn/v2_eval.py` (`--lowpass`). Picks on half A at lag −52,
  with the reference-proxy fallback. Each pick is scored by the stored average-guitar
  measure on half B. The current network is re-scored the same way.

## Decision rule (declared)

Pooled over the three amps, on recording bands, against the current rebuilt DI:

- **A cutoff helps** if its mean log ratio is −0.05 or lower and it has more part-amp
  wins than losses.
  - If both cutoffs pass, the one with the lower mean is adopted.
  - If one helps, low-passing becomes part of the rebuilt-DI chooser.
  - Its edge against the fixed driven preset is reported; claiming it needs fresh
    material.
- **If neither helps,** the top end is not what spoils the picks, and the remaining
  routes are the other step-4 ideas: stem-aware training, room and mic augmentation, a
  different network.

An independent reviewer re-derives the numbers before they route anything.
