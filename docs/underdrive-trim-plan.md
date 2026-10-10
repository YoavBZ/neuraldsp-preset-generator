# Correcting the under-driven picks: plan (set 3, development)

Declared 2026-10-10, before any render below. No training.

## Why

The rebuilt-DI chooser picks presets with too little gain. Its pick's gain knob is below
the true-DI oracle's on 43 part-amp cases and above on 14 (mean −0.124). The 3 kHz cut
reduces this to −0.088. The cause is the rebuilt waveform: its invented detail makes
every preset sound dirtier than it is, so the chooser compensates with less gain. The
true DI played at the same −22.9 LUFS is nearly unbiased (−0.022). So the bias is not
the level convention. Playing the rebuilt DI quieter should make every preset sound
cleaner by the same amount, and pull the picks back up.

## Method

- **Material:** the 33 development parts and three amp menus, as in the
  [fixed-level re-score](fixed-level-rescore-results.md).
- **Variants:** the 3 kHz-cut rebuilt DI (`lp3k`, the adopted chooser) played quieter,
  each rendered through every menu preset:
  - **`lp3k_m6`:** 6 dB quieter (−28.9 LUFS);
  - **`lp3k_m12`:** 12 dB quieter (−34.9 LUFS).
- **Scoring:** the protocol adopted in the
  [closeness review](closeness-review-2026-10-10.md):
  - **Measure:** the fixed-level measure (`measfix`), with the validated (`flat`) judge.
  - **Picks:** both halves (choose on A and score on B, and the reverse), averaged per
    part-amp.
  - **Statistics:** the mean log ratio with a band-clustered 90% interval, plus the
    exact band sign flip, wins, ties and losses.
  - **Code:** `learn/rescore.py`.

## Reported

Each variant against `lp3k`, against the leave-band-out fixed preset and against the
oracle. Also: its tonal and temporal parts, and the pick's gain knob against the
oracle's (the bias).

## Decision rule (declared)

For each variant against `lp3k` (smallest effect worth having: 0.05):
- **Helps:** the 90% interval lies below 0.
- **Futile:** its lower bound is above −0.05.
- **Inconclusive:** anything else. Then it is adopted provisionally if its mean is
  negative and it wins more than it loses (it is free), and otherwise dropped.

If both variants help, the one with the lower mean is adopted. Picking between two from
the same parts is reported as a further fork.

An independent reviewer re-derives the numbers before adoption. Any claim against the
fixed preset still needs fresh bands.
