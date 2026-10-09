# Development cross-amp choice diagnostic

Declared 2026-10-08. Not executed. Independent design/code review, synthetic checks and
commit are required before computing this analysis. Its scope is the existing amp
menus, not a larger knob search or a new reserved confirmation.

## Why this distinct question

The product may choose any Morgan amp, while most prior numerical tests fixed an amp
first. Existing development scores permit a cheap check of whether amp choice adds
useful headroom, and whether reconstructed-DI scores can choose across amps. This
does not tune the failed scalar calibration grid or activity-proxy heuristic. Their
own declared procedures remain closed if independent verification confirms failure.

## Fixed data and choices

- All 33 development parts in 11 bands, both band sets, original saved scores only.
  No reserved scores/audio, new audio access, model inference, rendering or training.
- Pool the frozen SW50R 45, PR12 35 and AC20 31 candidates. Identity is the tuple
  `(amp, preset ID)`, never preset ID alone; 111 choices, including three templates.
  Validate exact inventory, membership, nonnegative finite raw distances/nulls, and
  provenance against the reviewed development diagnostic before calculation.
- Selection always minimizes valid raw A, ties lexicographic by `(amp, preset ID)`.
  Raw zero is valid for choice/wins but separately log-unscorable. Never epsilon.
- Fit global factory-only and inclusive leave-band-out A constants: minimum median
  raw measure_A over every part of other bands, lexical ties. A candidate needs a valid
  raw A on every training part. The factory-only constant excludes all three templates.
  Report training slugs/eligibility; no held-out-band label may enter its own constant.

Policies frozen before reading each part's B for evaluation:

1. **Pooled known-DI:** minimum measure_A across all 111, then saved chosen measure_B.
2. **Pooled net:** minimum net_A across all 111, then saved chosen measure_B.
3. **SW50R known-DI:** minimum measure_A within SW50R, then saved chosen measure_B.
4. **SW50R net:** minimum net_A within SW50R, then saved chosen measure_B.
5. Global factory-only and inclusive constants.

For pooled/SW50R net, use the SAME global factory-only constant only if all of that
policy's raw A candidates are null; record the fallback. If the constant is unavailable,
the fallback is unavailable. Historical versions without fallback remain descriptive
comparators, not the source of a claimed gain.

Also save each amp's standalone net pick with the same global fallback. As an explicitly
unavailable half-B control, report the best scorable B among these three fixed picks.
This asks whether a better amp selector could help without changing each amp's preset
chooser. It is hindsight, not an estimated achievable result or a product policy.
List missing per-amp picks separately from refused and zero chosen B values. When
any of the three is missing/refused, this is only best among scorable picks. Report
actual selected amp and fallback part IDs for every net policy: the global fallback
can choose a different amp even for a policy labelled SW50R/PR12/AC20.
Report full-menu half-B hindsight coverage separately; any refused B candidate means
only a best-scorable value, not a full-menu bound.

## Reporting and exploratory routing

Keep all original denominators. Report candidate eligibility, choices, amp shares,
fallbacks, missing/zero values, agreement (not a quality claim), raw wins, paired
log ratios, medians of band medians and band-weighted win shares. Refused required
comparisons make available-case summaries descriptive. Exact sign-flip sensitivity
uses 1e-12 tolerance as before; overlapping fits and repeated development use mean it
is not calibrated inference.

- **Cross-amp known-DI headroom:** pooled known-DI beats SW50R known-DI by at least 5%
  in paired band-median distance, with band-weighted wins strictly above 0.5 and
  exploratory sign-flip value below 0.1, under BOTH band sets, with complete positive
  chosen-B pairs. This only shows useful development headroom from changing amps.
- **Cross-amp net chooser improvement:** pooled net beats SW50R net and BOTH global
  constants by at least 5%, sign-flip below 0.1 for each comparison, and band-weighted
  joint wins over all three strictly above 0.5 under BOTH band sets, with complete
  positive comparisons. A pass permits a separately declared development follow-up.
- A fixed-net-pick amp-selector follow-up additionally needs complete raw B coverage
  of all three standalone picks and at least 5% paired band-median B-hindsight
  improvement over SW50R net, with positive pairs under BOTH band sets. This is an
  unavailable-input headroom control, not an inferential test or proof of learnability.
- If known-DI headroom exists, net choice does not improve, AND that fixed-pick control
  meets its headroom condition, the next separately declared candidate is a small
  amp-selector model over fixed per-amp net choices. Known-DI headroom alone does not
  establish potential among those net picks; do not train that selector without it.
- If neither is established, do not tune pooled scores or broaden knobs in this study.
  Record the failure and declare a different mechanism before more computation.

No pass authorizes release, expensive waveform training or another use of spent
reserved data. Any changed method needs heavier-tone listening and fresh reserved
confirmation. Do not turn hindsight bounds into performance claims. Constants are
declared A-trained baselines, not every possible song-blind policy. The judge's
listening validation remains limited to clear clean-to-crunch PR12 differences.

## Required verification

Fresh independent design/code review before execution. Synthetic tests must cover
tuple identity when IDs repeat across amps, full inventory, exclusions, ties/zeros,
same fallback fairness, denominator preservation, and separation of A choice from B
evaluation. Commit before calculation. Independently rederive constants, picks,
comparisons, coverage and routing before accepting conclusions. Save exclusive new
outputs and preserve errors. No actual cross-amp analysis has run under this draft.

**Declaration, 2026-10-08:** fresh independent design/code/provenance review approved
after clarifying fixed-pick hindsight coverage, fallback attribution and the extra
fixed-net-pick headroom requirement before an amp-selector follow-up. All 17 synthetic
checks passed both through the main approved-helper run and the independent reviewer.
Reviewed code SHA-256 begins `ec3e27eabc55`, tests `e0a6bfe81058`. Commit this procedure
and implementation before actual cross-amp computation. Only development scores are
authorized here; no reserved use, product release or long training follows this check.
