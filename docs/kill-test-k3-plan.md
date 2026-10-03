# K3: does preset recognition learned from renders carry over to real recordings?

Written 2026-10-03, after K1 and K2 passed (`~/ndsp-presets/runs/kill/k-sw50r.json`) and
before K3 was computed. It needs no new renders.

**Question.** K2 showed that the 44 SW50R factory presets can be told apart across players from
plugin renders. K3 asks whether a recogniser trained only on renders picks a good preset from a
*real* amp-track recording — the step from simulation to real audio that every model depends on.

**Method.** The same features, folds (4 folds of bands, seed 20261003) and recognisers as K2
(1-NN, LDA, LDA+1-NN), trained on the panel renders of the training bands' parts. For each part
of the held-out fold, its real amp-track crop (`reference.wav`, 1.0–10 s, frames where its DI
plays) is turned into the same features and the recogniser picks a preset. That preset's render
through the part's own DI (already rendered) is scored against the part's amp track, against
template+R's render, under ALM and v3c over 1.0–10 s, level left out. Parts whose DI plays in
under half of 1.0–10 s are left out.

**Comparators.** The K1 constant (chosen on the training bands), the K1 split-half oracle's
pick (an upper bound), and a shuffled control: the recogniser given another held-out part's
amp track.

**Pass.** For at least one recogniser: band-median log ratio against template+R ≤ log 0.9
(a 10% gain) under both distances, closer on a majority of parts under both, and better than
the shuffled control on a majority of parts. The band sign-flip p is reported, not required.

**If it fails,** renders do not transfer to real recordings at this level even for whole-preset
recognition, and the model POC would need domain adaptation before it is worth building.

## Amendment, before any K3 result was read (2026-10-03)

An independent review of the design (its results unread by anyone) found the first version
biased and incomplete, and two render defects (24-bit PCM clipped 156 renders of four hot
presets; R did not reset transpose, so six presets played pitch-shifted). The panel is
re-rendered as float with transpose 0 in R, K1 and K2 are re-run on it, and K3 changes:

- **Shuffled control**: the recogniser is given every other-band part's amp track in turn (never
  the same band, whose own best preset already gains 20–28%), and the control is the mean log
  ratio over those picks rendered through the part's DI. "Better than the shuffled control"
  compares the part's own pick with that mean; ties count half.
- **Constant**: chosen on the training bands' parts per distance (median full-window distance).
- **Pass** additionally needs the recogniser closer than that constant on a majority of parts
  under both distances.
- **Open-set reading**: real amp tracks are never one of the 44 presets, so K3 is open-set by
  nature. K2 is extended with an open-set version (each preset held out of training), reported
  beside the closed-set K2, so a K3 failure can be read against it.

The oracle comparator is chosen on half A and scored on 1–10 s (which includes A), so it is an
optimistic upper bound; reported, not used in the pass rule.

## Under the judge, declared before any K1–K3 result on the float panel was read (2026-10-04)

K1–K3 were declared under ALM and v3c. Since then `docs/measuring-closeness.md` has
retired v3c as a judge and made `analysis/aligned.py` the judge (PR #109). The tests
are still computed and reported exactly as declared, and in addition
`scripts/kill_tests_judge.py` scores K1 and K3 under the judge:

- **The same choices**: K1's split-half oracle (closest factory preset on half A,
  scored on half B against template+R) and leave-one-band-out constant, chosen under
  the judge; K3's recognisers' picks and shuffled picks as `kill_test_k3.py` made
  them, its folds, and its constant re-chosen under the judge on the training bands.
- **The judge's settings**: default bands, with the union band set reported beside
  them; one lag per part, `estimate_lag` pooled over the part's whole panel around the
  catalogued lag less the latency (±15 ms), or without the hint (±50 ms) where that is
  refused, recorded in the output.
- **K2** is not re-scored: its accuracy needs no distance, and its per-item picks are
  not stored.

**What decides.** The declared pass rules with v3c replaced by the judge (default
bands): K1 passes if the oracle's band-median log ratio is ≤ log 0.75 under ALM and
under the judge; K3 passes if one recogniser meets the declared rule under ALM and
under the judge. The verdicts under the original rule (ALM and v3c) are reported
beside it. If the default and union band sets disagree on a verdict, it is reported
as not established, since the choice between them is open (measuring-closeness.md,
"Bands").

The script was run once on three parts with stand-in K3 picks, to check that it
runs; nothing from that run is used.
