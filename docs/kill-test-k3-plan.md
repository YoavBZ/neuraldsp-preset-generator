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
`scripts/kill_tests_judge.py` scores K1 and K3 under the judge and emits the verdict
below.

**What was known when this was written.**
- K1 and K2 on the earlier, 24-bit panel had been read: both passed under ALM and
  v3c, with ALM's K1 oracle gain about 31%. That panel was clipped on 156 renders and
  pitch-shifted on six presets, which is why it was re-rendered.
- The judge was built after the 16 listening answers were read, on the same 27 K1
  parts and this panel's renders, and is not yet validated by listening (stage 0b).
- The script was run once on three parts with stand-in K3 picks to check that it
  runs; its K1 summary for those three parts was seen by its author and a reviewer.
  Nothing from it is used.
- The judge and ALM are close relatives (both aligned log-mel distances), so "ALM
  and the judge" is closer to one test than "ALM and v3c" was. The rule below asks
  for both band sets as well, partly to offset that.

**The same choices.** K1's split-half oracle (closest factory preset on half A,
scored on half B against template+R) and leave-one-band-out constant, chosen under
the judge; K3's recognisers' picks and shuffled picks as `kill_test_k3.py` made them,
its folds, and its constant re-chosen under the judge on the training bands. The
thresholds stay as declared: log 0.75 for K1, log 0.9 for K3. They are log ratios,
so they carry over between distances, but the judge's scale (level offset removed,
floored) differs from ALM's, so the same ratio is not the same audible step.

**The judge's settings.** Both band sets (default and union). One lag per part,
frozen before any result in `docs/kill-tests-judge-lags.json` (`estimate_lag`
pooled over the part's whole panel, ±15 ms around the catalogued lag less the
latency; all 30 parts K1 or K3 uses were found inside it). On Signs 3 and Strangest
Places the pooled lag depends on which renders are pooled: the whole panel gives −29
and −89 samples (frozen, used for the verdict), nine-render pools 17–20 and −14 to
−16. Those two parts are scored again at 18 and −16 (in the same file, under
"alternate") and reported, not deciding. ALM uses the catalogued lags, which are 9.5–14 ms off on Signs 2,
Today's The Day 07 and 10 (K1 and K3) and It Was My Fault 1 (K3).

**What decides.**

| Test | Passes only if |
|---|---|
| K1 | the oracle's band-median log ratio is ≤ log 0.75 under ALM, under the judge with default bands, and under the judge with union bands |
| K3 | one recogniser meets the declared rule under ALM, under the judge with default bands and under the judge with union bands, and its most common pick is no more than half its parts' picks under either band set |

Any other outcome is "not passed". The model POC's gate opens only if K1 and K3 pass
as above and K2 passes as declared (`docs/supervised-model-plan.md` §0); the script
reports this as `gate_open`. Where the measures disagree, the write-up says
which way each went; that is description, not a third verdict. The verdict as first
declared (ALM and v3c) is reported beside this one and does not decide. K2's rule
never used v3c, so it stands as declared under ALM.

**Reported, not deciding.** For K3, per recogniser and band set: the number of
distinct picks, the most common pick's share, and the band median with each part
given the pick made for a part of the next band (picks moved one band along), so a
pass that is one good preset for everything shows as such. Windows the judge
refused, parts without a lag, K1's excluded parts and eligible K3 parts the
recognisers made no pick for are listed in the output. The script refuses K1–K3
outputs older than the panel's `index.json`, so the earlier render's outputs cannot
be scored by mistake.

**If stage 0b later validates** the judge but not ALM, or ALM but not the judge, the
verdicts are recomputed with only the validated distance's conditions (both band sets
for the judge), from the outputs already written. If it validates neither, these
verdicts are void and stage 0b's own rule (stop model work) applies.
