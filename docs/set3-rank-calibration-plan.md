# Development preset-rank calibration

Declared 2026-10-08. Independent design/code review and commit precede computation.
This is a small supervised learning experiment using existing development scores,
not a new reserved confirmation or another waveform-network training run.

## Question

Known-DI choice establishes menu headroom, but does not establish a complete waveform
recovery gap. The activity-proxy case study is independently verified and closed:
it rescues one refusal but improves no control choices. A separate
cheap question is whether a learned combination of song-specific scores and a preset's
past performance can make better choices than either alone. This avoids assuming that
a larger reconstruction network will solve a ranking/calibration problem.

## Fixed inputs and scope

- All 33 set-3 development parts, 11 bands; SW50R only, both existing band sets.
- Frozen 45-candidate inventory and original `phase2-set3/distances.json` only.
  Use `net_A` as input features and `measure_B` as supervised labels. Do not read any
  reserved scores/audio, any audio/arrays, or activity-proxy experimental scores.
- No rendering, inference, downloads, training caches, or GPU jobs. Standard-library
  computation only. The existing DI network and preset menu stay fixed.
- Validate exact development membership, all candidate keys, and source provenance
  against the independently verified development diagnostic. Hash inputs, code and
  plan. Write a new exclusive output and retain failures.

## Model: one learned mixing weight plus a preset prior

Fit separately under recording and union bands. The only mixing candidates are
`alpha = [0, 0.25, 0.5, 0.75, 1]`.

For a training set of bands:

1. For each part, center the positive valid log `measure_B` values by their median
   across the fixed menu's scorable candidates. Report missing/zero labels separately.
2. A prior candidate must have a positive finite B label on EVERY training part.
   Exclude and list other candidates; never remove training parts. For each eligible
   candidate, its prior is the mean of training-band means of centered log B, so
   training bands get equal weight. This minimizes a mean-log criterion, which differs
   from the median-based evaluation statistic. If no candidate remains, report an
   untrainable fold and a missing selection; do not invent a fallback preset.
3. At prediction, alpha=0 chooses the lowest prior, ties lexicographic, without using
   the new part's net scores. For alpha>0, only prior-eligible candidates with positive
   valid `net_A` enter `alpha * log(net_A) + (1-alpha) * prior`. Subtracting a part's
   median log A is allowed but does not affect picks. No B value from that part is used.
4. If ALL raw net_A scores are null, fall back to the prior-only choice for every
   alpha, recording the fallback. If any net_A is zero, alpha>0 is log-unscorable for
   that part (missing selection, explicit reason); do not replace zero by epsilon.
   Other missing candidates remain explicitly excluded. alpha=1 still uses the
   training prior's completeness eligibility, so report this restricted endpoint
   separately from the original unrestricted net chooser.

## Nested band validation: labels must never reach their own prediction

For each of 11 outer excluded bands:

- Tune alpha using only the other 10 bands. For each inner excluded band, fit the
  prior on the other NINE bands and predict each inner evaluation part from net_A.
  Choose alpha with smallest mean of inner-band mean log chosen B. An alpha is
  eligible only with positive valid chosen B on every inner evaluation part.
  First find the global minimum eligible loss; among alphas with loss no greater
  than that minimum +1e-12, choose the smallest alpha. Do not use sequential pairwise
  tolerance comparisons. If no alpha is eligible, mark calibration untrainable and
  its outer selections missing; never use outer labels to repair it.
- Refit the prior on all TEN outer training bands, then predict the excluded band's
  parts with the chosen alpha. Freeze picks before consulting that band's B labels.
- Record every outer/inner training slug, eligible/excluded prior candidates, fitted
  priors, alpha losses, selected alpha, predictions, fallback/missing reasons and B
  evaluations. The outer band's net_A may be read only for its final prediction;
  its B must be absent from all fitting and alpha selection.
- Even if alpha tuning fails, independently fit the ten-band prior and compute every
  comparator wherever possible. The unrestricted net chooser can still choose from
  valid raw A when the prior is untrainable; only its all-null fallback is then absent.

Comparators, all outer band excluded:

1. Prior-only B-trained constant (same training rule, alpha=0).
2. Original unrestricted raw minimum net_A, lexicographic ties, using the SAME
   prior-only fallback only when every raw A is null. Raw zero may win here.
3. Original unrestricted net chooser without fallback, for historical comparison.
4. Existing full-development diagnostic's factory-only and inclusive leave-band-out
   A-trained constants; read, do not refit on another sample.
5. Template+R and unavailable known-DI choice from measure_A, descriptive controls.
6. The restricted alpha=1 endpoint, using the same outer-trained prior eligibility,
   with its predictions, fallbacks and paired comparisons explicitly recorded. This
   distinguishes blending from excluding candidates using training-label completeness.

The B-trained constant is essential: labels could improve a default even without
song-specific information. A win over only the old A-trained constant is insufficient.

## Report and next-step heuristic

Report all 33 outer predictions, missing/zero cases, fallback counts, selected-alpha
counts, agreement, paired log distance ratios, medians of band medians and band-weighted
joint wins with all original denominators retained. Available-case effects are only
descriptive. Enumerate the same exact two-sided band sign-flip sensitivity statistic
as the prior diagnostic (1e-12 tolerance); overlapping folds and reuse of development
data mean it is not calibrated inference.

A separately declared broader development study is justified only if, under BOTH
band sets, calibration has complete positive chosen-B comparisons and:

- at least 5% smaller paired band-median distance than BOTH the B-trained prior and
  the unrestricted net chooser with the same prior fallback;
- band-weighted joint wins over those two comparators strictly above 0.5;
- exploratory sign-flip statistic below 0.1 against each comparator.

Passing these gates supports the combined calibration procedure, not necessarily the
blend itself. Claiming a blending benefit additionally requires improvement over the
restricted alpha=1 endpoint; matching it establishes no such benefit.

Otherwise close this particular blend without tuning its grid, changing its prior,
adding features or selecting subsets after results. Declare any next intervention
separately. Even a pass supports development follow-up only: no product release,
new waveform training, or reuse of the spent reserved split. Heavy-tone listening
and fresh reserved confirmation remain necessary for a changed method.

## Verification

Synthetic tests must demonstrate outer and inner exclusion. Changing outer excluded
B labels must leave fitted priors, selected alpha and outer picks unchanged. Changing
inner excluded B labels must leave that inner fold's prior and fixed-alpha predictions
unchanged; it may legitimately change selected alpha because it scores inner predictions.
Also test failed-tuning baseline independence, restricted endpoint, global-minimum
tolerance ties (including order invariance),
equal band weighting, null/zero handling, complete prior eligibility, and exact
candidate inventory. Independent review precedes commit/computation; a separate
implementation rederives priors, nested choices and all reported conclusions afterward.

**Declaration, 2026-10-08:** design clarified after independent review (restricted
endpoint comparator, baseline independence from tuning failures, and global-minimum
tolerance ties). A fresh-context reviewer approved the final design, implementation,
synthetic tests and archived-input provenance compatibility. All 57 calibration tests
passed through the approved helper; the worker's combined diagnostic/calibration run
passed 76. Reviewed code SHA-256 begins `4082cfe8f99d`, tests `973d0c4513db`. Commit
this declaration and implementation before actual calibration computation. This
authorizes only development-score analysis, with no reserved-data use or product claim.
