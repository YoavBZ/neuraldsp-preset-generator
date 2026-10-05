# Three quick checks before any model work

Declared on 2026-10-05, before any of them is computed. These are the first three
experiments of `docs/research-audio-ml.md` §5, run on data already on disk: no new
renders and no listening. Each needs a DI. They decide whether the model path is worth
reopening (`docs/kill-tests-pr12-results.md`, `docs/amp-reach-results.md`).

All three read judge distances that `scripts/amp_reach.py` stored
(`~/ndsp-presets/runs/kill/amp-reach.json`):
- every factory preset of the three Morgan amps, against each part's amp track;
- half A, half B and 1.0–10 s; both band sets;
- the 25 parts with a clear recorded lag whose DI plays in both halves.

## 1. How many amps can answer each recording?

`scripts/reach_sets.py`.

- **What counts as acceptable.** Per part, each amp's menu gives the expected half-B
  distance of the preset chosen on half A, over a random subset of its presets. Every
  amp is held to the same subset size, computed exactly from the ranks. An amp is
  acceptable when that distance is within 0.150 (log) of the best amp's.
- **Menus.** The decision uses the clean menus (17 AC20, 21 PR12, 17 SW50R; subsets of
  17); all presets (subsets of 30) are reported.
- **Decision.** If, under both band sets, exactly one amp is acceptable on at least half
  the parts, the model gets a single amp label. Otherwise the amp label is the set of
  acceptable amps, and the product would show a shortlist of amps.

## 2. How many distinct answers does each menu hold?

`scripts/reach_sets.py`.

- **What counts as one answer.** Two presets of one menu are indistinguishable as answers
  when, on at least two thirds of the parts, their full-window distances to the amp
  track differ by less than 0.150 (log), the cut listening validated.
- **Classes.** Complete-linkage clustering counts the menu's classes: a cluster joins
  another only if every pair across them is indistinguishable, so classes cannot chain.
- **Menus.** Clean PR12 (21), SW50R (44) and AC20 (30).
- **Decision.** If clean PR12's 21 presets form 5 classes or fewer under both band sets,
  K3 failed there for identifiability: the labels should shrink to those classes. Then
  "the presets sound alike" explains the clean PR12 failure, as long as SW50R does not
  collapse too. SW50R's count is the check on that, since K3 worked on SW50R.

## 3. Does a cheap fix rescue K3's recognisers?

`scripts/k3_hub_fixes.py`.

**The recognisers.** K3's recognisers are re-run as `scripts/kill_test_k3.py` ran them:
K2's features, the four folds of bands seeded 20261003, 1-NN, LDA and LDA+1-NN, on the
SW50R panel and the clean PR12 panel. Each fix below is fitted on the training folds'
real amp tracks only:
- **realnorm:** a real track's features are standardised by the training folds' real
  tracks (their mean and spread) instead of the renders'.
- **csls:** hubness correction. A candidate's distance is doubled, less its mean
  distance to its 10 nearest training real tracks and less the target's mean distance
  to its 10 nearest candidates.
- **bias:** each candidate's distances are centred by its mean distance to the training
  real tracks.
- **realnorm+csls:** both.

**Canary.** Without a fix, the recognisers must reproduce the earlier K3 picks exactly
(`k3-sw50r-run2.json`, `k3-pr12-clean.json`); if they don't, the run stops.

**Scoring.** Each pick is scored by the judge against the part's amp track, over 1.0–10 s
at the recorded lag, against template+R. That is 28 K3 parts; the three that amp-reach
didn't score are scored here.

**Decision.** A fix rescues a recogniser on clean PR12 if, under both band sets:
- its most common pick falls under a quarter of its picks (from 54–57% for the LDA
  variants);
- and its median of band medians is at least 0.05 better than the unfixed recogniser's.

There are 4 fixes × 3 recognisers, so 12 tries. A rescue is reported as one of 12, not as
evidence on its own. It would justify re-declaring K3 with that fix, not passing K3.

If nothing passes, recognisers are dropped for menus of near-alike presets. Model work
stays parked unless check 2 or the judge-as-teacher step changes the picture.

**Reported, not deciding:** every reading on SW50R. A fix that rescues clean PR12 but
makes SW50R worse by more than 0.05 is flagged.

## Limits

- These are development parts: 25 for checks 1 and 2, 28 for check 3. They are the
  same parts the kill tests used, so these are not independent tests.
- Cross-amp comparisons (check 1) and SW50R/AC20 distances lie outside the range
  listening validated.
- K3's features use the catalogued lags, as K3 did. The judge uses the recorded ones.
