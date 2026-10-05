# Three quick checks before any model work

Declared on 2026-10-05, before any of them is computed. These are the first three
experiments of `docs/research/round-4-audio-ml.md` §5, run on data already on disk: no new
renders and no listening. Each needs a DI. They decide whether the model path is worth
reopening (`docs/kill-tests-pr12-results.md`, `docs/amp-reach-results.md`).

All three read judge distances that `research/amp_reach.py` stored
(`~/ndsp-presets/runs/kill/amp-reach.json`):
- every factory preset of the three Morgan amps, against each part's amp track;
- half A, half B and 1.0–10 s; both band sets;
- the 25 parts with a clear recorded lag whose DI plays in both halves.

**Shares are weighted by band.** One band, Dom McLennon, supplies 8 of the 25 parts, so
every share below counts each band once, its parts sharing its weight.

## 1. How many amps can answer each recording?

`research/reach_sets.py`.

- **What counts as acceptable.** Per part, each amp's menu gives the expected distance of
  the preset chosen on one half, scored on the other. Both directions (A→B and B→A) are
  averaged, which reduces noise that would favour a single amp. Every amp is held to the
  same subset size, computed exactly from the ranks. An amp is acceptable when that
  distance is within 0.150 (log) of the best amp's.
- **Menus.** The decision uses the clean menus (17 AC20, 21 PR12, 17 SW50R; subsets of
  17); all presets (subsets of 30) are reported.
- **Decision.** The model gets a single amp label if, under both band sets, only one amp
  is acceptable on at least half the parts (band-weighted), in at least 3 bands.
  Otherwise the amp label is the set of acceptable amps, and the product would show a
  shortlist of amps.
- **Not done here:** research §5 also asks for a two-part regret (wrong amp against wrong
  preset within the right amp); it is left for the model's own evaluation.

## 2. How many distinct answers does each menu hold?

`research/reach_sets.py`.

- **Which parts vote.** Only parts where the track separates the menu vote: the
  presets' full-window log distances to the amp track must span at least 0.300. A track
  far from every preset shrinks the ratios and would otherwise vote "same".
- **What counts as one answer.** Two presets are indistinguishable as answers when, on at
  least two thirds of the voting parts (band-weighted), their distances to the amp track
  differ by less than 0.150 (log), the cut listening validated.
- **What this does not show.** It doesn't show that two presets sound alike: a bright
  and a dark preset can sit equally far from a track. It shows that the recordings don't
  separate them as answers.
- **Classes.** Standard complete linkage (scipy) on the dissimilarity "share of voting
  parts that separate the two", cut at 1/3. It merges the closest clusters first, does
  not depend on name order, and classes cannot chain.
- **Menus.** Clean PR12 (21), SW50R (44) and AC20 (30).
- **Decision.** Identifiability explains clean PR12's failure only if both of these hold,
  under both band sets:
  - clean PR12's 21 presets form 5 classes or fewer;
  - SW50R does not collapse at the same menu size: the mean class count over 200 random
    21-preset subsets of its 44 presets is above 5. K3 worked on SW50R, so this is the
    check, matched for size since class counts grow with menu size.

## 3. Does a cheap fix rescue K3's recognisers?

`research/k3_hub_fixes.py`.

**The recognisers.** K3's recognisers are re-run as `research/kill_test_k3.py` ran them:
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
(`k3-sw50r-run2.json`, `k3-pr12-clean.json`), on the same parts and panels; if they don't,
the run stops.

**What the fixes amount to.** With squared distances, `bias` reduces to choosing the
candidate with the largest inner product with the centred target. It ignores the
target's scale and favours far-out candidates. With 10 of about 22 training tracks,
`csls` is close to the same rule.

**Scoring.** Each pick is scored by the judge against the part's amp track, over 1.0–10 s
at the recorded lag, against template+R. That is 28 K3 parts; the three that amp-reach
didn't score are scored here.

**Decision.** A fix rescues a recogniser on clean PR12 if all of these hold under both band
sets:
- its most common pick falls under a quarter of its picks (from 54–57% for the LDA
  variants);
- its median of band medians is at least 0.05 better than the unfixed recogniser's;
- it beats a pick with no information: a preset drawn from the menu at random. That is
  the exact mean over the menu per part, taken as a median of band medians. It guards
  against a fix that only scatters the hub's picks;
- it beats K3's shuffled control (the same model given other bands' tracks) on more than
  half the parts.

**Reported, not deciding:**
- the comparison with the constant chosen on the training bands;
- a band sign-flip p for the fix against the unfixed recogniser, Holm-adjusted over the
  12 tries;
- every reading on SW50R. A rescue that makes SW50R worse by more than 0.05 is flagged.

There are 4 fixes × 3 recognisers, so 12 tries. A rescue is the best of 12 on the same 28
parts. It would justify re-declaring K3 with that fix, labelled optimistic; a pass would
then need confirming on new parts.

## What follows

| Check 2 (identifiability) | Check 3 (fixes) | Reading |
|---|---|---|
| explains PR12 | any | the menu's presets aren't separated as answers. A model predicts classes, not presets, and the recognisers stop being judged on near-alike menus. |
| does not | a rescue | the gap from renders to real tracks is partly a cheap normalisation. K3 is re-declared with the fix, labelled optimistic. |
| does not | none | the failure is transfer: render-trained recognition doesn't reach real tracks with these features. Model work stays parked until the judge-as-teacher step (research §5, experiment 4) finds features that do. |

## Limits

- These are development parts: 25 for checks 1 and 2, 28 for check 3. They are the
  same parts the kill tests used, so these are not independent tests.
- Cross-amp comparisons (check 1) and SW50R/AC20 distances lie outside the range
  listening validated.
- K3's features use the catalogued lags, as K3 did. The judge uses the recorded ones.
- Both outputs record their input hashes and the commit.
