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
