# The family check and the class check (results)

**Status:**
- **Run:** 2026-11-20, once each, from main at `e438965a` (the squash of PR #523, which holds the declared phases), in a
  clean detached worktree. Zero renders, zero separations, no MPS, no sealed set.
- **Audited:** 2026-11-20 by an independent blind recompute, PASS WITH CORRECTIONS for both checks. Every number
  reproduced, and both cells follow from the declared tables. The corrections are to wording and context and are taken
  here.
- **Plan:** [family-class-checks-plan.md](family-class-checks-plan.md).
- **Ledger:** `pipeline-fix` `phase_family_check_outcome`, `preset-ladder` `phase_class_check_outcome`.
- **Data** (`PF` is `~/ndsp-presets/learn/trusted-data/pipeline-fix`):

  | File | Written | sha256 |
  |---|---|---|
  | `PF/family/tags.json` | 02:35:59 | `be619875…ec30d7f` (content `2a64b6a1…64931f`, as declared) |
  | `PF/family/report.json` | 02:36:24 | `2c235d6e…f0073b37d5` |
  | `PF/ladder/class/report.json` | 02:36:34 | `5aba334e…82ef7f9` |

- **Cost, measured:** the family read took 23.7 s of computation (25 s wall with start-up), the class read 9.0 s.

Items marked **post hoc** come from the audit and were not declared before the run. Every knob-space number is
descriptive: no render read confirms it.

## Summary

- **The family check reads GF-thin: underpowered, not failed.**
  - A pack name's gear family does not place a capture's settings nearer than Cen does. The shuffle's p is 0.215.
  - The families hold little of the settings' variation. **Post hoc:** even with unlimited captures, a family centre
    would gain at most about 2.5% of Cen's distance on drive and tone and about 7.5% on cab, all under the declared
    10%.
  - A gap that small implies about 0.02 or less by the score, under the user's 0.05 rule.
  - **Direction 2 is parked.** The 8-minute render read stays available but is not recommended, and it has not run.
- **The class check reads CK-stop: class stays with research.**
  - A simple classifier on the guitar-alone stem names the class at 0.64 on held-out recordings, well under 0.80.
  - **Post hoc:** the cap is the 197 mel features, or how the held-out set's classes are labelled, not the
    classifier. Four other models do no better.
  - On real-amp recordings the clean track reads at 0.96. There the stem reads at 0.77, about research's level and
    undecided.
  - CK-stop licenses only "this classifier does not overrule research". It does not show that audio cannot read the
    class, and it does not close Direction 3.

## A. The family check (GF-thin)

The records: 86 usable from 22 creators and 7 families. 47 were left out: 43 with no family and 4 with no
other-creator record on their amp. The rebuilt Cen equalled the stored Cen in all six cells.

D_g = d_g(family centre) − d_g(Cen₋c), RMS gap in unit space, below zero nearer; 90% t intervals:

| Group | By creator (22) | By family (7) | Cen's distance | The bar (−0.1 × Cen's) | Ruled out? |
|---|---|---|---|---|---|
| drive | −0.0002 [−0.0137, +0.0134] | +0.0003 [−0.0319, +0.0324] | 0.218 | −0.022 | on the creator interval only |
| tone | +0.0096 [−0.0016, +0.0208] | +0.0140 [−0.0094, +0.0375] | 0.235 | −0.024 | on both |
| cab | −0.0161 [−0.0351, +0.0029] | −0.0104 [−0.0503, +0.0296] | 0.304 | −0.030 | on neither (creator lower end −0.035) |
| eq (beside) | +0.0066 [−0.0041, +0.0173] | +0.0175 [−0.0068, +0.0418] | 0.224 | | |
| pedals (beside) | +0.0059 [−0.0134, +0.0252] (17) | +0.0023 [−0.0031, +0.0077] | 0.228 | | |

**The cell.**
- **Nearer** is false: no group's creator interval lies wholly below zero (cab's upper end is +0.003).
- **Ruled out** is false: GF-stop needs all three groups ruled out on the lower of the two lower ends, and drive and
  cab fail.
- **The joint shuffle p is 0.215** (2,000 shuffles, statistic −1.433). Per group, beside: drive 0.57, tone 0.69, cab
  0.08.
- So the cell is **GF-thin**.

**Beside, descriptive.**
- **The plain mean (w = 1)** moves labels away: drive +0.024 [−0.000, +0.047], tone +0.029 [+0.007, +0.050], cab
  +0.003. The shrink is what keeps the family centre level with Cen.
- **Same class only:** drive −0.006, tone −0.001, cab −0.018 [−0.028, −0.008].
  - **Post hoc**, this is mostly not a family effect. The auditor's own same-class shuffle (500 permutations,
    undeclared) has a null mean of −0.0076 and puts the real row at a one-sided p of 0.09.
  - That leaves about −0.010 for the badge, about 3% of Cen's cab distance.
  - The main row shows the same pattern (the shuffle's cab mean is −0.005): part of any cab gain comes from averaging
    other captures on the same amp, whatever their tags.
- **Without the prototype pack** (80 records): drive −0.001, tone +0.006, cab −0.011 [−0.030, +0.008].
- **Leave one family out**, the range of the creator mean: drive −0.006 to +0.004, tone +0.005 to +0.014, cab −0.027
  to −0.009.
- **Like for like with the reader** (75 records), each against the stored fold Cen:

  | Row | drive | tone | cab |
  |---|---|---|---|
  | family centre (fold-wise) | +0.004 | +0.011 | −0.026 [−0.042, −0.010] |
  | the reader on the clean capture (`clean-kind`) | −0.002 | −0.008 | −0.035 [−0.059, −0.010] |
  | the reader on the product's stem (`rc-xl@-3`) | +0.006 | +0.007 | −0.013 [−0.028, +0.003] |
  | family centre less the clean-capture reader, paired | +0.006 | **+0.020 [+0.001, +0.038]** | +0.009 |
  | family centre less the stem reader, paired | −0.002 | +0.005 | −0.013 [−0.038, +0.011] |

  The reader on the clean capture beats the family centre on tone (and on eq). Against the reader on the product's
  stem the family centre is not shown nearer.
- **Switches and mics** (910 values): Cen differs from the label on 24.4% of them, the family majority on 26.0%.
- **The families' share of residual label variance** (ICC, mean over heads, floored at 0): drive 0.05, tone 0.05, cab
  0.14 (**post hoc:** its median over 15 heads is 0.08), eq 0.09, pedals 0.41.
  - At these shares no family size reaches a 10% smaller RMS distance on drive, tone, cab or eq.
  - **Post hoc:** with unlimited captures the best is sqrt(1 − ρ) of Cen's distance: drive 0.974, tone 0.976, cab
    0.925. Fetching more named captures cannot reach the bar unless the shares are underestimated, and seven families
    make each one noisy.

**What the render read could show (post hoc).**
- In the ladder, knob moves onto Cen of 0.04 to 0.12 RMS changed J0 by −0.004 [−0.028, +0.020].
- A cab-only gain of about 5% of Cen's distance therefore predicts a gap of about 0.02 or less by the score.
- Under the user's rule no action could rest on that. **Direction 2 is parked.** The render read (about 530 renders,
  about 8 min) stays available but is not recommended and has not run.

## B. The class check (CK-stop)

The control passed: both of T-clean's G intervals lie above G's majority share (lower end 0.711 against 0.511). The
fold bans removed 285 training unit slots over the four folds, as declared.

| Row | G, C3r clusters (157) | G, DI files (145) | GOAT both-class (70) | R units without Drowning (47) | R clusters right, 11 (12) | Off-side (14) / on-side (384) |
|---|---|---|---|---|---|---|
| **T-alone** (decides) | 0.639 [0.589, 0.690] | 0.643 [0.596, 0.689] | 0.657 | 0.766 | 8 (9) | 0.714 / 0.664 |
| T-full | 0.581 [0.528, 0.634] | 0.590 [0.541, 0.639] | 0.614 | 0.660 | 6 (6) | 0.571 / 0.594 |
| T-clean | 0.758 [0.711, 0.805] | 0.756 [0.712, 0.799] | 0.800 | 0.957 | 10 (11) | 0.857 / 0.794 |
| T-mix | 0.619 [0.564, 0.674] | 0.589 [0.535, 0.643] | 0.729 | 0.574 | 5 (6) | 0.786 / 0.589 |
| In-alone | 0.773 [0.727, 0.819] | 0.768 [0.725, 0.811] | 0.786 | 0.894 | 11 (12) | 0.643 / 0.805 |
| In-full | 0.917 [0.890, 0.944] | 0.908 [0.879, 0.938] | 0.886 | 0.915 | 10 (11) | **0.286** / 0.935 |

- T-alone per G set: GOAT 0.637 (215 units), first-batch captures 0.686 (121), second-batch 0.500 (12).
- Majority shares: G 0.511, R's 47 units 0.574, R clusters 6 of 11.

**The cell.** T-alone on G is "below" on both schemes. R is "neither" (8 of 11, between 6 and 9). The leak guard is
"ok". In-alone is "not above" (both lower ends under 0.80). So the cell is **CK-stop**.

**The leak behaves as expected.**
- The stem-trained full-stem row is lender-keyed: 0.92 overall, but 0.29 on the 14 units whose lender band is on the
  other class's side.
- In-alone falls from 0.81 on-side to 0.64 off-side.
- T-alone reads 0.71 off-side and 0.66 on-side, so it is not lender-keyed.
- The lender-band control (The Travelling Band against Hazael, 188 clean units, majority 0.537) reads 0.904 from
  `xl@-3`, 0.638 from `xlnoG@-3` and 0.521 from `clean-kind`. The bleed in the guitar-alone stem is real.

**Where the limit sits (post hoc).**
- **Not the classifier.** On the same features and splits the auditor tried logistic regression at C 0.01 and 0.1, a
  random forest, gradient boosting and 15 nearest neighbours (undeclared):
  - T-clean on G reads 0.70 to 0.78 with every model;
  - T-alone on G reads 0.58 to 0.65;
  - R clusters with T-alone run 5 to 8 of 11.

  The limit is the 197 mel statistics, or how G's classes are labelled: T-clean is only 0.80 even on GOAT's
  both-class items.
- **A plan gap.** The control required T-clean above G's majority share (0.51), not above the bar. T-clean's own G
  upper ends sit at 0.80 to 0.805, so "g above" was all but unreachable for T-alone. The "below" that carries the stop
  follows from G's ceiling more than from stem loss. The plan's power figure assumed an accuracy near 0.9, and that
  did not hold.

**Is 0.80 a comparable bar?**
- No. Research's 8 of 10 is on real exam songs, with a 90% interval of 0.49 to 0.96.
- G is GOAT reamps and captures, whose class labels even the clean track reads at only 0.76.
- R is the closest kind (real amps; T-clean 0.957). There the guitar-alone stem reads 0.766 of units and 8 of 11
  clusters: about research's level, undecided, not shown below it.

**What CK-stop licenses:** this classifier and these features do not overrule research's class, so class stays with
research for now.

**What it doesn't license:**
- that audio cannot read class;
- that research beats audio (nothing here is paired);
- closing Direction 3. On real-amp recordings the clean track reads the class at 0.96.

**Stronger cheap tests, for later** (none declared):
1. **Swap the representation** (stored J0 or EfficientAT embeddings, or a small network on the stored mels), with the
   clean-track control first. If G's T-clean stays near 0.77, G's labels are the cap and G is unfit for a 0.80 bar.
2. **Decide on real-amp clusters** (BKS, the panel and other real multitracks with a verified class), one cluster left
   out at a time, with lenders drawn blind to class.
3. **A declared, paired read** of a classifier against research on the exam's stored stems. This is the question that
   matters, though it is low-powered at 10 parts.

## Provenance

- **The commit.** The outputs reproduce exactly from `e438965a`'s code. The run worktree was removed after the run.
- **The files.** Under `~/ndsp-presets`, nothing was written between 02:30 and 02:45 but the three outputs and the
  hand-back. No render, separation or MPS output was written.
- **Once.** Both commands refuse to overwrite, and one copy of each output exists.
- **The smoke runs** (shuffled tags or classes, before the merge) wrote only to a scratch folder, never to `PF`. Their
  outputs are deleted.
- **Sealed sets.** The code reads only C3r's state, `ladder/centres.json`, `answers/{cen,clean-kind,rc-xl@-3}.json`,
  `lends.json` and the ladder's stored features. No exam or V-real path is read, and Silent Waves is out.
