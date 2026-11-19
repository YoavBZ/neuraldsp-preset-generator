# The learning-curve diagnostic: would more recordings help? (plan)

**Status:** declared 2026-11-19, before any run, on the user's go of the same day. It is section 14 of the approved
Step 6 plan (the second review round's pick, [stem-finetune-plan.md](stem-finetune-plan.md) section 13's outlook),
built with that review's three non-blocking items, the training-noise result of Step 6's stage N
([results](stem-finetune-results.md)) and the user's rule of 2026-11-19 that no action rests on a gap under 0.05.
Revised the same day after the PR's independent review (changes needed, two wording items; section 8): the power is
stated, D-unreadable no longer over-reads a decided cost, and arm a is trained and read first, with arm b only if an
acting cell is still possible (the cheaper stop, `A_TABLE`). Nothing here has run. Every number is by the score unless it says "by ear": J0, ln(d_row / d_against) on the held half,
below zero closer; 90% cluster t intervals; the deciding pool is BKS, GOAT and the panel weighted equally. `PF` is
`~/ndsp-presets/learn/trusted-data/pipeline-fix`.

- **Ledger:** `pipeline-fix` `phase_s6_half` (the halves, the 32 runs, the table); `preset-ladder` `phase_l6_half`
  (the answers, renders and report).
- **Code:** `learn/half_data.py` (`D_TABLE`, the halves and their guard, the answers and the report), the
  `train-ft --c3r-half a|b` path in `learn/pipeline_fix.py` (`full_controls_c3r.rows_for(..., keep=)`), the launcher
  `learn/half_data_train.zsh`, and the rows in `learn/preset_ladder.py` (`L6H_MODEL_ROWS`, `L6H_RC_ROWS`). Tests:
  `tests/test_half_data.py` (pure, light CI) and `tests/test_train_ft_half.py` (torch).
- **Data:** `PF/step6/half/` (`selection.json`, `runs.json`, `report.json`, `logs/`), the ladder's `answers/` and
  `judge/` for the four new rows. No audio is stored.

## Why

The model reads each recording only weakly, and about 70% of its per-unit answer is the pretrained network's starting
state (stage N's gauges). One lever has shown a like-for-like gain: more rows. But that gain mixed chain count with
coverage (F77), and the one learning curve (N3) was undecided on an older model and input. The cheapest test of "would
more distinct recordings help" is to halve them and measure the cost on the product's input. It uses no new label,
capture, separation or sealed set.

**The goal check, said first.**
- It changes nothing in the product. It decides whether the "more chains" direction (Step 6 plan section 13) is worth
  the user's capture fetching and ear time, which are scarce. TONE3000's calibrated clean and low-gain rigs are mostly
  used, and about 175 labelled capture units already failed the ear or DI checks.
- **What would make it act:** a halving cost the user's rule counts (section 5). A goal-relevant figure goes with it:
  the doublings that cost would need to bring the model to about −0.06 against Cen.
- **Its power, and why that bar fits the decision.** From the measured seed spread (`rc-rep − rc-xl`, half-width 0.013
  to 0.015), H's 90% half-width should be about 0.012 to 0.02. A counted cost (lower end over 0.05) then needs a true
  halving cost of about 0.065 for even odds, and about 0.075 to 0.09 for 80%. A smaller true cost would mostly read
  unreadable or short. That loss is not decision-relevant: with the full models about level with Cen (F about 0), any
  cost under about 0.05 a doubling means at least 0.06 / 0.05 = 1.2 doublings to reach −0.06 against Cen, so at least
  about 2^1.2 − 1 = 1.3 × 293, about 380 more trusted chains. That is beyond the stated supply. A cost of 0.065 or more
  needs under one doubling, which is a direction worth the user's time. So the bar the user's rule sets is where the
  decision changes.
- **It converges:** one selection, one training, one read, one cell. A second point (a quarter of the chains) is a
  dated amendment on the user's word.

## How this differs from what came before

- **N3 (2026-11-05)** halved the rows of FTm, on the core controls, older labels and the backed input, with no
  training noise measured beside. It was undecided, which says nothing against more rows. This halves **chains**
  (whole recordings), on R-all's recipe and labels, read on the product's input (the stored X-LANCE stems, `xl@-3`),
  with the seed noise sampled on both sides (section 2).
- **F77 (R-all − R-ctl)** added whole new sets, so chain count and coverage moved together. This keeps every set and
  every fold and halves the chains inside each set, fold and class.

**Why it may fail.**
- With half the chains the inner runs may stop earlier, and an early stop can pass for a data effect (F77). Each run's
  E is reported beside its reference run's. An epoch-matched read would need more training and is not planned.
- One halving is one point of a curve. Going from "halving costs x" to "doubling gains x" assumes the gain per doubling
  does not grow with the data (section 5).
- Which half was drawn is a second source of noise. The two arms train on complementary halves, so their mean covers
  every chain once, and their spread holds the choice of half as well as the seed.
- The read set's power is limited: a model-against-model row resolves about ±0.015 to ±0.026.

## 1. What it trains

R-all's recipe exactly: `train-ft --masked --ft-cap 300 --c3r all`, C3r's folds, drops, labels, masks and two-source
epoch mix, lr 1e-4, cap 300, the E rule (the first argmin of the trailing 3-epoch average, patience 15), each FT_k at
its own inner run's E. **One change: each run's real training units are only those of its half.** Held units (the
inner runs' validation on the whole of fold k+1, and fold k for FT_k) and the identity bans are unchanged.

**Chains.** A chain is one recording's amp chain, the unit's `rig`:
- BKS: a DI file and reamp track (14 chains, 102 units);
- GOAT: a capture render (214);
- cap1 and n12: a capture (48 chains on 121 units, and 12);
- the panel: a DI file and amp track (5 chains, 12 units).

So there are 293 chains. A chain's records stay or go together, and no chain spans two folds (checked).

**The halves** (`half_data.draw`, `guard`, `choose`; seed `HALF_SEED` 20261191):
- In each (set, fold, class) stratum the chains are shuffled by a seeded generator. Half A takes the first floor(n/2),
  and an odd stratum's middle chain goes in on a seeded coin. Half B is the complement. A chain's class is its units'
  most common.
- **The guard (the review's item 1).** In every one of the 8 fold runs (FT_k and inner, k 0 to 3), each half keeps at
  least one training record of:
  - every pooled (amp, class) cell the full run trains;
  - every set the full run trains on two chains or more. One chain can't be in both halves: n12 has runs with one or
    no chain.
- **Balance.** In each half, every set with at least 4 chains keeps 40% to 60% of its records. BKS's chains run from
  2 to 18 units, so halving its chains could otherwise halve its windows very unevenly.
- The first draw (j = 0, 1, …) that passes is used. The draws are made from the code alone, with no label or result,
  before any run.
- **At declaration (zero renders, this code):** draw 20 passes.

  | Half | BKS chains (records) | GOAT | cap1 chains (records) | n12 | Panel chains (records) |
  |---|---|---|---|---|---|
  | A | 7 (144) | 108 | 24 (60) | 6 | 2 (6) |
  | B | 7 (162) | 106 | 24 (61) | 6 | 3 (6) |

  `half_data select` saves it, never overwritten (`selection.json`, its content hash in every run record). Every run
  checks that hash and C3r's state.
- **As many updates as R-all.** Each source (real amps: BKS and the panel; captures: GOAT, cap1 and n12) is still cycled
  to 300 rows an epoch. Every full run holds at most 293 records a source, so a half run has the same number of rows
  as its reference run, and the same seed draws the same epoch permutation. That permutation maps to other records, so
  the two runs' noise is correlated, not shared (section 2). Each kept record is shown about twice as often.

## 2. The design against training noise

Stage N measured the noise:
- The pretrained network's state (W) moves answers 0.067 RMS, more than units differ (0.051 to 0.057).
- The fine-tune seed alone moves them 0.016 to 0.021.
- At pool level one repeat read −0.010 on the re-centred row, with an SD that one draw only bounds roughly (0.002 to
  0.05).
- Per-set reads between separate trainings are untrustworthy at about 0.015.

So the half-data read must separate the data effect from seed noise.

| Arm | Trains on | W states | Fine-tune seeds | Matched to |
|---|---|---|---|---|
| a | half A | W 20261042, W 20261043 | 20261042, 20261043 | R-all (the same W state and seed in every fold run) |
| b | half B | W 20261042, W 20261043 | 20261181, 20261182 | R-rep (the same) |

- **Matched W states.** Every half run starts from its reference run's W state, so W's 0.067 is common to the
  comparison, not noise in it. W trained on plugin rows only (0 of its 1,787 training ids are real rows), so sharing it
  leaks no recording.
- **Matched fine-tune seeds.** Same seed, same row count: the same batch order and draws. That only correlates the
  noise; the different rows still move training apart.
- **Two seeds a side, spread reported.** The full side has two draws already (R-all, R-rep), and the half side gets
  two (arms a and b).
  - The decision row H is both halves' mean against both full models' mean, per direction.
  - Its noise is measured on both sides:
    - `rc-rep-xl@-3 − rc-xl@-3`, the fine-tune seed alone: −0.010 [−0.023, +0.003] on all parts; −0.013 [−0.028,
      +0.002] on the read's parts (section 3), computed at declaration from the stored rows.
    - `rc-half-b-xl@-3 − rc-half-a-xl@-3`, the seed and the half.
- **The noise check.** A counted H also needs each arm's matched row (H_a against R-all, H_b against R-rep) decided the
  same way.

**Why this is the cheapest that separates them** (measured run-minutes: R-rep's 16 runs logged 72.4, and stage N's 18
runs took 90.5 min of wall time one at a time; 5,760 renders took about 85 min on 3 shards). The run-minutes below are
at R-rep's rate, one job at a time. At R-all's logged rate (114.4 per 16, with the seed pairs side by side) the 32 runs
would be about 229.

| Design | Training | Renders | Separates data from seed noise? |
|---|---|---|---|
| One half arm (section 14 as first written) | 16 runs, about 72 run-min, about 80 min wall | 3,840, about 57 min | No: the half side's seed and the choice of half go unsampled; H and H2 differ only by the full side's noise |
| **Two half arms on complementary halves, matched (this plan)** | 32 runs, about 145 run-min, about 161 min wall; 16 runs if arm a stops | 7,680, about 113 min; 3,840 if arm a stops | **Yes**, on both sides, and the choice of half too |
| Two arms on the same half | the same | the same | Seed noise only; the result would hold for one draw of the half |

Training times are R-rep's by analogy, not measured for half data: E may differ.

## 3. The read

Each of the ladder's 480 parts on 400 units is answered by its own fold's pair, from the stored `xl@-3` features (zero
separations), as R-all's and R-rep's are. The answers use the ladder's code (`stem_finetune.answer_row`), with
same-input constants (`cmd_sic`) and the re-centred rows (`cmd_rc`, "rule", Cen unchanged). The statistics are exactly
the ladder's (`rows_for_pair`, `summarise`). A "+" row is the per-direction geometric mean of its rows' distances, so
`a1+a2 − b1+b2` is the mean of the two log ratios (`half_data.geo`; at declaration `rc-rep-xl@-3+rc-rep-xl@-3 −
rc-xl@-3` reproduced the stored −0.01001 [−0.02335, +0.00333] exactly).

| Row | Pair | Role |
|---|---|---|
| **H** | `rc-half-a-xl@-3+rc-half-b-xl@-3 − rc-xl@-3+rc-rep-xl@-3` | **the decision row**, re-centred, so an aim shift can't pass for data |
| H_a | `rc-half-a-xl@-3 − rc-xl@-3` | the noise check, arm a against its matched R-all |
| H_b | `rc-half-b-xl@-3 − rc-rep-xl@-3` | the noise check, arm b against its matched R-rep |
| H raw, H_a raw, H_b raw | the same on the raw answers | beside |
| H_a x, H_b x | each arm against the other full model | beside |
| half spread, full spread | `rc-half-b − rc-half-a`, `rc-rep − rc-xl` (and raw) | beside: the two noise gauges |
| full vs Cen, half vs Cen | `rc-xl@-3+rc-rep-xl@-3 − cen`, `rc-half-a-xl@-3+rc-half-b-xl@-3 − cen` | beside; full vs Cen feeds the doublings figure |
| E | each run's E beside its reference run's | beside, zero renders |

- **H's adversarial read:** per set, per class, half A; each deciding set and each cluster left out (`negatives`,
  `loo_range`).
- **Trusted data.** The panel's Silent Waves parts carry vocal bleed (the ladder's ear check, card i14) and await a
  trusted-data review. **Every row above is read without them** (478 of the 480 parts; the panel keeps 4 DI files and
  still decides). Beside, H is also read with every part, and without both of that band's recordings (Drowning awaits
  a bleed check).
- **Training keeps them, and here is why.** Silent Waves is one of the 5 panel chains R-all and R-rep trained on.
  Dropping it from the half arms alone would mix the exclusion into the halving. Retraining the full arm without it
  is a change of R-all's recipe, which belongs to the trusted-data review. It is one chain of 293, in one half only.

## 4. Leakage

Unchanged from R-all's. Each part is read by its own fold's models. A half run's training units are a subset of R-all's
same run's (refused otherwise), so no read part's unit, DI file or creator trains in the model that reads it. The
answers step re-derives that ban from the run records (`half_data.read_bans`). No sealed set is touched: V-real, the
reserve and R1 are not read, and NS's loss is logged by the fold runs as R-all's were, never tracked.

## 5. The outcome table (`D_TABLE`, coded with its tests before any run)

**The user's rule (2026-11-19):** no action rests on a gap under 0.05. By ear the score is trusted at gaps of about 0.1
and over, and is a coin flip under 0.05 ([ladder-ear-results.md](ladder-ear-results.md)). `heard_reading` reads H as
follows:

| Reading | When (H's deciding-pool 90% interval [lo, hi], mean m) |
|---|---|
| cost | decided worse (lo > 0) and (lo > 0.05 or m ≥ 0.10) |
| gain | decided better (hi < 0) and (hi < −0.05 or m ≤ −0.10) |
| unreadable | lo ≥ −0.05 and hi ≤ +0.05: **not readable by the score** |
| short | the rest: the interval reaches past ±0.05 with no counted gap (underpowered, or a decided gap under the rule) |

The noise check holds when H is not counted, or when H_a and H_b are both decided the way H reads.

| Code | H | Noise | Next |
|---|---|---|---|
| D-data | cost | holds | More chains is a live lever, and this halving's cost is its first size. The write-up gives the doublings (below). To the user with the supply limit. |
| D-noise | cost or gain | fails | Not separable from training noise. Reported with both spreads; nothing follows. |
| D-odd | gain | holds | Fewer chains reads better by a heard size: an early stop or the choice of half, not a finding. Reported; nothing follows. |
| D-unreadable | unreadable | either | **Not readable by the score;** no action rests on it. To the user, with the direction note. |
| D-short | short | either | Not decided at a heard size. No action; the write-up gives what the interval rules out, with the direction note. |

- **The direction note (`DIRECTION_NOTE`).** D-unreadable and D-short carry H's plain reading, so a decided result is
  not over-read. For example, +0.03 [+0.015, +0.045] is decided worse but inside ±0.05.
  - Worse: halving has a decided cost, but under the heard size. More chains is a lever, too small a doubling to give
    a heard-size gain soon; the doublings figure says how many it would take.
  - Better: fewer chains reads decided better, inside the heard size; an early stop or the choice of half.
  - Undecided: halving is not shown to cost. If the gain per doubling does not grow, doubling is not shown to buy a
    heard-size gain either. This read does not show where the limit lies.
- **The doublings figure (the review's item 3), for every H decided worse,** not only D-data. n = (F − (−0.06)) / H,
  where F is "full vs Cen" and −0.06 is where a row against Cen reads better (the Step 6 plan's figure).
  - It is given on a grid: H's mean and interval ends against F's mean and interval ends. F's interval (about
    ±0.057) is about as wide as the whole distance to −0.06.
  - Each doubling means 293 more trusted chains, the next 586 more, and so on.
- **The assumption, stated (the review's item 2).** A constant gain per doubling. If returns diminish, as learning
  curves usually do, more doublings are needed than the figure says, so it is a lower bound. D-unreadable's step from
  "halving costs under 0.05" to "doubling buys under 0.05" uses the same assumption: it holds if the gain per doubling
  does not grow.
- **False alarm.** Under no effect, H reads decided worse at most 5% of the time on one tail. "Cost" also needs the
  interval past 0.05 or a mean of 0.10, and the noise check needs both matched rows.
  - H's cluster interval samples the read's units for fixed models and leaves out training noise, so that 5% is per
    read set.
  - Training noise is measured beside it (both spreads, about 0.01 at pool level, five times under the 0.05 bar) and
    guarded by the noise check. At that bar the omission is harmless.
- **The mean branch.** "m ≥ 0.10" allows a lower end just above 0. At the expected half-width (0.012 to 0.02) such a
  row is past 0.05 anyway, so the branch is moot here, but it is kept as the user's rule states it.

**The cheaper stop (`A_TABLE`, the review's non-blocking point, adopted).** D-data, the only acting cell, needs H_a
(arm a against its matched R-all) decided worse. So arm a is trained, answered, rendered and read first
(`half_data report-a`, its rows saved before the cell):

| Code | H_a | Next |
|---|---|---|
| A-go | worse | Arm b's 16 runs and two rows, then `report` and `D_TABLE`. |
| A-stop | undecided or better | **Stop.** No acting cell remains: D-data needs H_a worse, and D-odd acts on nothing. Arm b is not trained, which saves about 80 min of training and 57 min of renders. Hand back H_a with its heard reading, its direction note and, when decided worse, its doublings; then the audit and the user. |

Arm b's training and answers refuse unless `report-a` read A-go (`stage_a_go`, the outcome's hash checked). The stop is
one read of one arm. It adds no false alarm, since every D-data needs H_a worse anyway.

## 6. Stages, costs and machine plan

| # | Step | Cost (measured rates) | Stop |
|---|---|---|---|
| 1 | Ledger, code and tests, and an independent review of this PR | none | — |
| 2 | `half_data select` (from merged main): the halves, saved once | CPU seconds | refuses if no draw of 1,000 passes |
| 3 | `half_data_train.zsh a`: arm a's 8 inner runs and 8 FT_k, one MPS job at a time | about 72 run-min, about 80 min wall (R-rep's rate, by analogy) | a failed run stops the chain |
| 4 | `half_data answers --arm a`: `half-a-xl@-3`, its constant and re-centred row; recipe, half and ban checks | about 1 min CPU | refuses on any difference |
| 5 | Renders, 3 shards: `half-a-xl@-3`, `rc-half-a-xl@-3` | 3,840 renders, about 57 min | the disk guard |
| 6 | `half_data report-a`: H_a and its beside rows saved, then `A_TABLE` | seconds | **A-stop ends the read here** |
| 7 | Only on A-go: `half_data_train.zsh b`, `answers --arm b`, renders of `half-b-xl@-3` and `rc-half-b-xl@-3` | about 72 run-min, about 80 min wall; 3,840 renders, about 57 min | the same |
| 8 | Only on A-go: `half_data report`: the rows saved, then the cell | seconds | `D_TABLE` |
| 9 | Hand-back (raw, unaudited; it says training includes the Silent Waves chain, in half B), then the independent audit, then the user | none | — |

- **Limits:** one MPS job at a time and at most 3 render processes, launched with `setopt no_bg_nice` and caffeinate.
  Every launcher re-checks the 31 GB disk guard; 51 GB were free at declaration. The losses stay on the CPU, as R-all's
  recipe has them (the MPS stft bug). PIDs are recorded at launch (the training launcher writes its own PID file,
  `PF/step6/half/logs/train-<arm>.pid`), and only those are stopped.
- **The read's parts:** `report-a` and `report` refuse unless exactly 2 parts are left out (Silent Waves; 478 of 480).
- **Storage:** 32 records, 16 checkpoints at 4.3 MB each, four answer files and their judge files: under 0.2 GB. No
  audio.
- **Monitoring** goes to the executor session.

## 7. What it can't say

- It is one halving, read on the ladder's built mixes at one exposure (−3 dB) and on the six lender sessions. It is
  conditional on W's two states, which are shared by every model here.
- A cost may be partly the epoch count. E is reported, and no epoch-matched read is planned.
- It does not say which chains would help: whether new captures in GOAT's DI family count as distinct recordings for
  this purpose is not tested.
- It says nothing by ear. A counted cost is a score gap of the size the ear trusts, not an ear read.
- Not built here: the calibration direction's per-group scale check that section 14 listed beside. It is separate work.

## 8. The second review round's items for section 14

| Item | Where |
|---|---|
| A guard that every (amp, class) cell keeps training records in every run | Section 1's guard, `half_data.guard`, tested |
| State D-flat's diminishing-returns assumption | Section 5, the assumption; D-unreadable's text |
| Report how many doublings would reach about −0.06 against Cen | Section 5, `half_data.doublings_grid`, in `d_outcome` and `a_outcome` for every decided cost |

**The PR's independent review (2026-11-19, changes needed; the design and code sound), all taken:**

| Item | Change |
|---|---|
| B1: state the power | The goal check: H's half-width about 0.012 to 0.02; a counted cost needs about 0.065 (even odds) to 0.075–0.09 (80%); an uncountable cost means at least 1.2 doublings, about 380 more chains, beyond supply |
| B2: D-unreadable over-reads a decided cost | Its text no longer names the labels or the reading; D-unreadable and D-short carry H's direction (`DIRECTION_NOTE`); doublings for every decided-worse H |
| The cheaper stop | Arm a first; `A_TABLE` (A-go, A-stop), `report-a`, arm b's runs and answers gated on A-go (`stage_a_go`), tested; ledger and section 6 |
| Doublings at F's ends | `doublings_grid`: H's and F's means and ends |
| H's interval leaves out training noise | Section 5, false alarm |
| "the same epoch order" overstates | Section 1 and the ledger: correlated, not shared |
| Refuse unless exactly 2 parts are left out | `LEFT_OUT_PARTS`, `read_rows` |
| The launcher's PID file | `train-<arm>.pid` |
| Comment slips (`L6H_MODEL_ROWS`, section 3) | Fixed |
| Run-minutes at R-rep's rate | Section 2: R-rep's rate; R-all's would be about 229 |
| The m ≥ 0.10 branch | Noted in section 5 |
| Silent Waves in training | The hand-back says so (section 6) |
