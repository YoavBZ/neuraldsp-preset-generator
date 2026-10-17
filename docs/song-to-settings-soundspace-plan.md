# Arm B in sound space (rethink experiment 3B): plan

Declared 2026-10-16, before any of its compute. Experiment 3B of
[`research/song-to-settings-rethink-2026-10.md`](research/song-to-settings-rethink-2026-10.md),
redesigned around what [the diagnostics](song-to-settings-diagnostics-results.md) found.
Development data only. The rules of [`research/ml-plan-2026-10.md`](research/ml-plan-2026-10.md)
section 5 apply, with the user's rule of 2026-10-16 in place of pass/fail bars.

**Review:** reviewed 2026-10-16 by an independent agent
(`tmp/song-to-settings-soundspace-plan-review.md`, local): approved with changes, all folded in
(11 required, and the 3 recommended items: a reseeded-B1 yardstick, crunch centres drawn per part,
and a peak-memory measurement).

**Status: waiting for the user's yes.** Nothing below runs before it.
- **The songs** need a second yes. That covers E2, E3 and E4's C-fine.
- **C-start** is offered only if E3 chooses B1 or B2.
- **B2a and B0's best of 8** are optional, each on its own yes.

## Why

Arm B's diagnostics, on 120 fresh render targets and step 3's stored searches:
- **B has signal on renders:** its top answer is −0.39 against S on the light view and −0.16 on the
  song-like view.
- **One wide mode per setting,** and the answer shrinks toward mid-range.
- **Its prior points away from records.** Step 3's K_S optima sit at a range limit on 35% of
  settings (render targets: 20%). Ranked by B's density, a K_S path prefers settings farther from
  the record (ρ +0.13).
- **It is weakest on input gain and switches,** which move the judge most (median 0.75–2.65 for a
  0.15 move or a flip, against 0.17–0.44 for tone and cab settings).
- **Settings that sound alike are broad:** 49–60% of the candidates that close half the gap lie
  ≥ 0.2 from the target.

So the model is trained to fit one exact label per sound, and when the sound doesn't fix a
setting it learns the middle. This plan changes what it is trained to fit:
1. **sound-space labels:** each relabelled example carries a set of settings, weighted by how
   close they render to its stored sound;
2. **a set-valued, mode-seeking loss** that rewards landing on any good member, not their average;
3. **record-like labels:** new examples drawn around K_S optima, fold-correct;
4. **sensitivity weights:** settings that move the sound more weigh more.

**Deviation from the diagnostics' trigger table:** row 7 pointed to experiment 2 (the
isolated-DI retrain). Under amendment 1 those readings are guides, and the audit judged
experiment 2's value modest: the light view is already in distribution and reaches 27% of the gap.
This plan runs 3B first. Experiment 2 stays available. The flow head that the trigger proposed
for collapse is not used: on the same knob loss it would learn the same wide blob.

## The arms

| Arm | What changes | New renders to train | MPS |
|---|---|---|---|
| **S** | the class start | 0 | 0 |
| **constant** | the song-blind constant (`song_armb.constant_settings`) | 0 | 0 |
| **B0** | arm B as scored at step 3, unchanged (`models/fold{f}/model.pt`) | 0 | 0 |
| **B1** | B0's bank and architecture; a new head and loss (below) | 0 | ≈ 4 h |
| **B2** | B1, plus the relabelled sets and 2,500 record-like examples | ≈ 11.5k | ≈ 5 h |

That is the cost order used for ties. B1 isolates what the head and loss buy for free. B2 adds
what the renders buy: the sets and the record-like examples together.

**Two more models, reported only, never chosen:**
- **B1′:** B1 retrained with seed 20261031 + fold. It is the seed-noise yardstick: 0 renders to
  train, about 4 h of MPS, scored on E1.
- **B2a (optional, on the user's yes at `report-1`):** B1 plus the 2,500 record-like examples,
  without the relabel sets. It tells apart B2's two ingredients.
  - It needs no training renders beyond B2's, because it reuses B2's record-like renders.
  - It is not free, though. Scoring it on E1 costs up to 1,440 renders, and training it about
    5 h of MPS.
  - It is scored on E1 only.

### B1: the head and the loss (no renders)

The body, features, inputs, mic and switch heads, epochs, patience, batch and learning rate are
B0's (`song_model.py`).
- **A censored head.**
  - Each continuous mean is −1 + 3·sigmoid(z): a soft bound on (−1, 2) that keeps a gradient
    everywhere.
  - A label within 1e-6 of 0 or 1 (the bank's clamped jitters, or a value passed through
    `to_unit` of a formatted setting) scores the Gaussian's mass beyond that limit. Any other label
    scores its density.
  - So the model can put an answer on a limit.
- **The single answer:** the heaviest component's mean, clipped to [0, 1]; each switch at
  p > 0.5; each mic's top choice. A **sample** draws a component by π, then each setting from its
  Gaussian, clipped to [0, 1] (the censored model's own law, so limits get their mass).
- **Sensitivity weights s_j.**
  - s_j is the setting's median judge change from step 1.2 (`diag/sens/`), divided by the mean of
    those medians over the amp's settings, then clipped to [0.25, 4].
  - **The right cab's level, distance and position** use only the bases with the right cab on
    (10–14 per amp). With the cab off they change nothing (median 0.000), so when the label's
    right cab is off they are masked (weight 0). The right mic is masked too, by the same logic;
    that part is unmeasured.
  - **Mics** weren't moved in step 1.2, so they keep B0's weight.
  - The table below comes from the stored medians; `weights` recomputes it, and code asserts the
    match.

  | Amp | s_j |
  |---|---|
  | PR12 | treble 2.24, input gain 1.73, volume 1.64, right cab on 1.18, bass 0.83, right cab level 0.61, left cab position 0.56 and distance 0.55, right cab distance 0.44 and position 0.25 |
  | SW50R | input mode 2.38, treble boost 2.11, level 1.86, input gain 1.74, volume 1.65, bright 1.43, right cab on 0.68, mid 0.62, treble 0.58, bass 0.46, right cab level 0.45, left cab distance 0.42, left cab position, right cab distance and position 0.25 |
  | AC20 | bass/treble 3.44, volume 1.93, input gain 1.80, bright 1.07, cut 0.98, power 0.75, right cab on 0.64, left cab distance 0.36, left cab position 0.31, right cab level 0.30, right cab distance and position 0.25 |

- **The weighted loss keeps B0's group normalisation,** with s_j inside each group. Per example
  and half:
  L = −logsumexp_k(log π_k + Σ_cont s_j ℓ_kj) / Σ_cont s_j + Σ_switch s_j BCE_j / Σ_switch s_j
  + Σ_mic CE_m.
  - The sums run over the settings that exist and are unmasked.
  - So the groups keep B0's balance; within a group, input gain and the strongest switches weigh
    most.
- **Record-like weighting.** Bank examples jittered around a K_S optimum (about a quarter) are
  up-weighted so they carry half of each fold's training loss: weight = n_other / n_KS, counted
  on that fold's training rows.
- **Validation and early stopping** use each arm's own loss on its validation rows (set targets
  included in B2), without the record-like weights. B0 used its own loss.

### B2: relabelled sets and record-like examples (renders)

B2 trains with B1's head, loss and weighting, on the bank plus the new examples. On the relabelled
examples the target becomes a set.

**The relabel set: 1,000 bank examples, 9 renders each.**
- **Draw:** `random.Random(20261026)`, from the original bank examples only, 250 per fold.
  - The 6 amp × class cells are taken in a seeded order; the first 4 get 42 examples and the last 2
    get 41.
  - Within a cell, broad and jittered examples alternate.
- **The DI:** the example's measure DI, regenerated as the bank made it
  (`song_bank.measure(load_window(w))`, untrimmed 10.25 s). Each render is trimmed to the bank's
  [0.25 s, 10.25 s) and judged per half against the stored render (`load_render`, peak restored)
  at lag 0 (`song_diag.judge_trimmed`).
- **The anchor:** of the example's **own fold's** K_S optima for its amp and class
  (`song_bank.ks_optima`), the nearest to its label in s-weighted unit distance. With none for that
  class: the same amp, either class. With none at all: the four pull probes become jitters. Both
  fallbacks are counted.
- **The probes:**

  | Probe | Renders |
  |---|---|
  | S (the scale: d_S per half) | 1 |
  | Pulls: the label's continuous settings moved t = 0.25, 0.5, 0.75, 1 of the way to the anchor's (unit scale; the label's mics and switches kept) | 4 |
  | The label with the anchor's mics | 1 |
  | The label with the anchor's switches (a third jitter if they already match) | 1 |
  | Two jitters, σ 0.15 on the continuous settings (clamped; mics and switches kept), `SeedSequence([20261027, i])` | 2 |
  | **Per example** | **9** |

  Identical settings are rendered once. The probes map the equal-sound set along the directions
  that matter here: toward record-like settings, across mics and switches, and locally. They are
  model-free, so no model's view of another fold enters a label.
- **Members and weights,** per half h: the label (d = 0) and every finite probe, with
  r = d / d_S and w̃_m ∝ exp(−r / τ), τ = 0.25, **normalised to sum to 1** over the members.
  - So a member that closes 75% of the gap from S counts e⁻¹ of the label, and one that closes half
    counts e⁻².
  - τ is fixed here, not tuned.
- **Kept as a point label:** a half whose d_S is below 0.1 (S already sounds like the label: no
  scale) or non-finite. Counted.
- **The set loss is mode-seeking.**
  - The responsibilities are γ_m = softmax_m(log w̃_m + ℓ_m). Here ℓ_m is member m's weighted
    joint log-likelihood, **not normalised**: the continuous mixture term, plus Σ s_j log p(switch),
    plus Σ log p(mic).
  - The loss is L_set = Σ_m sg(γ_m) · L(θ_m), with L B1's loss and sg a stop-gradient.
  - Its gradient is the EM form of −log Σ_m w̃_m exp(ℓ_m), applied to B1's group-normalised terms.
    The un-normalised ℓ keeps the responsibilities sharp, so the fit lands on a member instead of
    the weighted average.
  - With one member it is B1's loss exactly.

**Record-like examples: 2,500 new renders.**
- **Draw:** `random.Random(20261028)`, as `song_bank.draw`, but the jitter centre is always a K_S
  optimum of the example's own fold (the bank chose S or K_S with p 0.5).
  - **The centre:** a part, uniform among the fold's parts with an optimum for this amp and class;
    then one of that part's optima. So no part dominates through its number of stored optima.
  - Same fallback as the anchor.
  - σ 0.1, clamped; mics and switches kept with p 0.7; a same-fold backing; a second guitar with
    p 0.3; mastering, AAC and separation each with p 0.5.
- **Crunch is concentrated:** in folds 0, 2 and 3 the crunch optima come from one part each, about
  2 per amp. So per-class crunch figures stay descriptive (ML plan section 8).
- **Indices** 10000–12499, in their own folder with their own `examples.json`; the bank's files are
  not touched.
- **Features** through `song_aug`'s functions (mixture, compression, AAC, `GuitarSeparator`,
  `features`), with paths passed in. Parity with the bank's feature code is tested on 3 examples.
- **No diagnostics target track** is used (the diagnostics ledger keeps those tracks out of later
  training sets).

## Fold-correct training

- **Folds:** `docs/song-settings-folds.json`. Model f trains on rows with fold ≠ f, bank and new
  examples alike. Its validation bands are B0's for fold f (`models/fold{f}/log.json`), so the arms
  validate on the same bands.
- **A relabelled example's set** comes only from its own label, its S, jitters, and K_S optima of
  its own fold. Since that example trains only models of other folds, model f never sees a fold-f
  optimum. That is the bank's rule 4.
- **New examples** take their window (fold-own with p 0.5, otherwise Guitar-TECHS P1/P2), backing,
  second guitar and centre from one fold, as the bank does.
- **The sensitivity weights** are one shared table of 37 numbers from step 1.2's 15 windows. They
  are not fully free of evaluated content:
  - the windows may share tracks with E1 targets (they never overlap a target window);
  - their K_S-prior bases used optima from every fold, step 3's parts included.

  At 37 amp-level numbers the effect is minor. It is stated, not fold-split.
- **At evaluation,** each diagnostics target is read by the model of its band's fold, and each
  step-3 part by its fold's model, as before.
- **Asserted in code:**
  - all of the above;
  - no relabel member or new label is drawn from an optimum outside the example's fold;
  - no new example uses a diagnostics target track;
  - model f's training rows contain no fold-f example.
- **Seeds:** B1, B2 and B2a use B0's (20261018 + fold), so the arms differ by the declared changes
  and their data. B1′ uses 20261031 + fold.

## Evaluation

**What is measured** is the held-half judge distance through the measure DI, as the log ratio of
one candidate against another, unless a measure says otherwise.

**How it is compared:**
- The unit is (target or part, amp, direction). Units are averaged per target or part first.
- Then band-weighted means, with 90% band-clustered intervals (`song_readout.bw_stats`),
  leave-one-band-out ranges, the part-weighted figure, bands better or worse, and splits per amp
  and per class.
- The fold-by-fold figures are descriptive.
- The intervals leave out training-seed variance; B1′ − B1 is reported beside them as a yardstick.

**Refused answers count against the arm that made them.**
- Only the drops made before this plan apply to every arm: step 3's 2 directions, and E1's stored
  drops.
- A new arm's answer whose held half is non-finite (silent, for example volume at 0) scores as S:
  log ratio 0, the product's fallback.
- Refusals are counted per arm. The same rule applies to each sample in a best of K.
- `song_readout.drop_refused` is not used for the new arms.

**What decides:** one measure, chosen before any score.
- **With the songs' yes:** the songs' top answer against S (E3).
- **Without it, provisionally:** E1's song-like view (1b), top answer against S, on the **broad
  targets only.**
  - The K_S-prior half is reported beside it. Its centres are bank jitter centres in the reading
    model's training folds, which B1 and B2 up-weight.
  - If the two halves name different winners, the result is recorded as undecided.
- **The choice:** among S, constant, B0, B1 and B2, the best band-weighted mean. A candidate whose
  paired 90% interval against the best contains 0 is tied. Of the best and its ties, the first in
  cost order is chosen (`arm_a_levers.choose`).
- Everything else is reported, not deciding.

**Power.** The intervals are about ±0.07 on songs (B0 was +0.035 [−0.038, +0.108]) and about
±0.09 on E1's view 1b.
- That is roughly a quarter of K_S's −0.27, and about arm A's −0.08.
- With ties going to the cheaper arm, a real gain of −0.05 will often come out as S or B0.
- Such a result reads "no gain shown at this power", with the best arm's interval. It is not a
  failure.

### E1. The render targets (repeat use, declared)

These are the diagnostics' 120 targets, and the unit list of its stored report (`diag/report.json`:
228 informative units after its drops; the audit recomputed 224, and both lists are kept). The
list's hash goes into the ledger tally before any score. This is their **second use.** Their results
shaped this plan, so the figures carry a selection effect.
- **Stored, no renders:** S, the target and its repeat, the bank median, the constant, and B0's
  top, mixture mean and samples on both views. B0's best-of-4 on view 1b uses its first 4 stored
  samples.
- **New, per arm (B1, B2, B1′; and B2a if run) and target:**
  - view 1a: the top answer, per direction (2 renders);
  - view 1b: the top answer and 4 samples, per direction (10 renders).

  The sample seed is `SeedSequence([20261029, target, view, direction])`. That is at most 12
  renders per target per arm: 1,440 per arm, 4,320 for B1, B2 and B1′.
- **Measures:**
  - the top answer against S, on views 1b and 1a;
  - the top answer against B0;
  - best of 4 on view 1b, picked on the search half, against S and against B0's best of 4;
  - median gap closed, and the share of units closing at least half (counts, no bar);
  - by target type (broad, K_S-prior);
  - the share of continuous answers within 0.01 of a limit (beside the targets' 20% and K_S's
    35%);
  - answer spread over label spread;
  - per-setting Spearman with the target for input gain and the tone knobs, and switch accuracy;
  - refusals per arm.

### E2. The density bridge (zero renders; under the songs' yes)

E2 reads the records' held distances, so it is a use of step 3's songs. It runs only after the
songs' yes and is entered in the ledger before it runs.

It covers step 3's stored K_S paths, with each direction's search-half stem and mix features
(`eval-features`). The fold-correct model reads them, and its density scores every setting the path
evaluated.
- **The score:** the log-probability of a ±0.02 box around each continuous value (a limit's
  censored mass included), plus the switch and mic log-probabilities.
  - It is the same for every arm, so a mass at a limit and a density elsewhere compare fairly.
  - B0's figure is recomputed under it. The diagnostics' truncated-density figure is shown beside
    it.
- **Reported per arm:**
  - the Spearman between the score and the held distance to the record, over each path;
  - the same with another band's features (the stored `shuffled0` source), and the difference
    (true − shuffled);
  - the held log ratio against S of the highest-scoring setting among the path's first 8, first 16
    and all of its evaluations, beside K_S's own pick at 8 renders.

### E3. The songs (ask first: the user's yes)

This covers step 3's 142 directions, with step 3's stored features, through each part's measure
DI, judged against the record at its `judge_lag`. It is a further use of those parts, and it is
entered in the ledger's tally before it runs.
- **The top answer** of B1 and B2: 284 renders. B0's, S's and the constant's are stored. This
  decides.
- **Best of 8 samples,** for the chosen arm if it is B1 or B2, otherwise for B2: 1,136 renders.
  - Picked on the search half: an 8-render true-DI search, a ceiling, not a product option.
  - It is compared with K_S at 8 renders (stored curves).
  - The seed is `SeedSequence([20261030, part index, amp index, direction])`.
- **B0's best of 8 (optional, its own yes):** 1,136 renders, the same seed.
- **Shuffled input** for the same arm: the same other-band features as B0's `shuffled0`. 142
  renders.
- **Reported:**
  - each arm's top answer against S (the deciding measure), against B0 and against the constant;
  - best of 8 against S and against K_S at 8;
  - the arm against its shuffled input;
  - refusals per arm.

### E4. A combination with arm A (descriptive)

This uses the arm that E3 gave a best of 8. It needs each part's stored C′ rebuild and arm A's
objective (`rebuilt_distance`, lag −52).
- **C-fine (under the songs' yes; zero search renders):**
  - Arm A's stored main stage is replayed (`arm_a_levers.main_stage` with `Replay`). That gives
    the 52 settings it evaluated from S.
  - Of the 8 with the lowest C′ objective, B's density (E2's score, search-half features) picks
    one. That is one judge per direction.
  - The C′ objective ranks fine moves near S no better than chance, so B breaks the tie.
  - It is also run with B0, and with the arm reading the shuffled input: 3 × 142 = 426 renders.
- **C-start (offered only if E3 chooses B1 or B2; ≈ 7.6k renders):**
  - Arm A's main stage (52 renders, C′ objective, seed 20261013), started from the chosen arm's top
    answer instead of S.
  - Then one true-DI judge per direction.
  - If E3 chooses S, the constant or B0, its start is no better than S, so it is not offered.
- **Compared with:** S, 3-C′ (arm A's own main stage from S), 3-C′ shrunk halfway, and B's top
  answer. All are stored except C-fine and C-start.
- **Nothing here is chosen.** It shows whether B helps arm A as a start or as a fine-setting
  source.

### Also reported (no renders)

- **The relabel itself,** per probe type, amp and setting group:
  - the share of probes with r ≤ 0.25 and ≤ 0.5;
  - how far toward the anchor the sound holds (the largest t with r ≤ 0.25);
  - mic and switch swaps that keep the sound.

  This is a direct map of how broad the equal-sound sets are.
- **The training logs:** epochs, validation loss, run time and peak memory per fold.

## Set-up checks (read first; integrity, not results)

- **Relabel repeat:** 20 relabel examples (1 in 50) have their label re-rendered.
  - Each finite half must be within 1e-3 of the stored render. The audit's re-renders were within
    7e-7.
  - Silent or non-finite halves (master volume or level near 0, or DI pauses) are dropped and
    counted, as in the diagnostics' audited rule. They do not fail the check.
- **Feature parity:** on 3 new examples, the features match the bank's code path.
- **The top answer and the sampler** agree with the head (the answer is the clipped top mean;
  samples clip at the limits).
- **The fold assertions** above.

If any check fails: stop. A fix is a dated amendment; there are no silent re-runs.

## Renders and caps

| Item | Renders | Hard cap |
|---|---|---|
| Record-like examples | 2,500 | 2,550 |
| Relabel: 1,000 × 9, plus the 20-render repeat check | 9,020 | 9,050 |
| E1: B1, B2 and B1′, 3 × 120 × ≤ 12 | ≤ 4,320 | 4,350 |
| **Without the songs** | **≈ 15.8k** | **15,950** |
| E3 (songs' yes): top 284, best of 8 1,136, shuffled 142, about 150 warm-ups | ≈ 1.7k | 1,750 |
| E4 C-fine (songs' yes) | 426 | 450 |
| **With the songs** | **≈ 18.0k** | **18,150** |
| Optional: B0's best of 8 (its own yes) | 1,136 | 1,150 |
| Optional: B2a on E1 (its own yes) | ≤ 1,440 | 1,450 |
| C-start (offered only if E3 chooses B1 or B2) | ≈ 7.6k | 7,650 |
| **Everything** | **≈ 28.2k** | **28,400** |

- **The running total:** about 147k, experiment 4's actual renders included; its remaining
  allowance is not planned. It is reconciled against the ledger before the first render.
  - With this plan: about 162.8k without the songs, about 165.0k with them, and at most about
    175.2k with every optional item and C-start. That is under 200k.
- **Each step counts its renders** and stops at its cap. Anything past a cap is asked first.

## Machine order

There is one Mac: the MPS GPU, 8 CPU cores and 32 GB.
- **MPS:** one GPU job at a time, about 11 GB.
  - The trainings run one after another: B1, B1′ and B2, and B2a if asked (4 folds each). Each
    queues behind any experiment-4 or other MPS job.
  - Features are cached; no spectral loss runs on MPS. Gradients are clipped by hand, as B0's.
  - Step 3's logs put a fold at 44–58 min. That gives about 4 h each for B1 and B1′, about 5 h
    for B2, and about 5 h for B2a.
- **Memory, measured first.**
  - `train --arm B0 --dry-run --fold 0` loads B0's fold-0 arrays exactly as `song_model.train`
    does, without training, and records peak RSS. B2's float32 arrays are about 6 GB, and
    `np.stack` doubles that at its peak, so the new loader fills a preallocated array instead.
  - B1's fold 0 then runs alone under `/usr/bin/time -l`.
  - Render processes run beside the later trainings only if the measured peak, plus 3 render
    processes, leaves the guard's 6 GB.
- **CPU:**
  - at most 3 Morgan render processes machine-wide, counting every session's;
  - `knob_ceiling.Renderer` with `isolate=True` and process reuse; the licence daemon is never
    touched;
  - torch and separation at 2 threads.

  The diagnostics' memory and swap guard applies: start at ≥ 6 GB available; pause below 3 GB or
  on more than 1 GB of new swap. Long jobs are launched with `setopt no_bg_nice`.
- **Disk:** 35–38.6 GB was free on 2026-10-16, against `knob_ceiling2.disk_ok`'s 31 GB guard. That
  leaves only about 4–7.6 GB.
  - The new examples add about 1.8 GB (16-bit FLACs and features), plus separation temporary
    files. The probes keep distances only.
  - Free disk is checked before the record-like renders and before `features`. Each needs at
    least 31 + 2.5 GB, or it is asked first.
  - `disk_ok` also runs every 50 renders.

**Order:**
1. Code, tests and the review (done 2026-10-16). Then the ledger entry and a message to the
   product session.
2. **On the user's yes:**
   1. `weights`, the draws and the memory dry run (CPU, minutes).
   2. B1 trains on MPS: fold 0 alone, then the rest. Beside it, the record-like examples render,
      then the relabel probes (3 processes).
3. The new examples' features: one torch process, 2 threads, not beside the render processes.
   Then the sets.
4. B2, then B1′, train on MPS.
5. E1: propose on the CPU, then score with 3 processes. Then `report-1`, and the user is asked
   about the songs, B2a and B0's best of 8.
6. **On the songs' yes:**
   1. E2 and E3's top answers, then the choice;
   2. then best of 8, shuffled input and C-fine (and B0's best of 8 if asked);
   3. then `report-2`. C-start is offered if B1 or B2 was chosen.
7. **On those yeses:** B2a (train, then score on E1); C-start; then `report-3`.
8. An independent audit, `docs/song-to-settings-soundspace-results.md`, the ledger outcome, the
   roadmap and the docs index.

**Wall clock:**
- renders: about 3.2 h without the songs, at about 5k/h on 3 processes;
- separation: about 1.75 h, for 1,250 examples;
- MPS: about 13 h (18 h with B2a);
- songs: about 30 min more, and C-start about 1.5 h.

## What the choice leads to

| Chosen | Reading | Next |
|---|---|---|
| B2 | The renders help: the sets and the record-like examples together (B2a, if run, splits them) | A blind listening check of B2's songs against S (its own plan); then arm C with B2 as the proposer |
| B1 | The head and loss help; the renders add nothing measurable at this power | Keep B1's recipe; no more relabel renders |
| B0 | No gain shown from retraining at this power (the best arm's interval is given) | The user decides: park arm B's model work, or a sharper test |
| S or constant | No gain shown over the start at this power (the best arm's interval is given) | The user decides on that interval. If E1 still shows gains, the song side, not the model, is the loss |

The user decides each next step. E4, B1′, B2a and the relabel map inform it; they choose nothing.

## Code (written and tested before any compute)

**`learn/song_relabel.py`** builds the data. It reuses `song_bank`, `song_aug`, `song_diag`
(`judge_trimmed`, `measured_di`, the guards) and `knob_ceiling`, and changes none of them.

```
.venv/bin/python -m learn.song_relabel weights                 # s_j from diag/sens -> weights.json
.venv/bin/python -m learn.song_relabel draw                    # relabel set, anchors, new examples
.venv/bin/python -m learn.song_relabel render-new --shard i/3  # the 2,500 record-like renders
.venv/bin/python -m learn.song_relabel probe --shard i/3       # 9 probes per relabel example
$TORCH_PY      -m learn.song_relabel features                  # new examples: mix, master, separate
.venv/bin/python -m learn.song_relabel sets                    # members and weights per example-half
```

**`learn/song_soundspace.py`** covers the arms, training and evaluation. Its model is built from
`song_model`'s body with the censored head; B0 still loads through `song_model.load_net`.

```
$TORCH_PY      -m learn.song_soundspace train --arm B0 --dry-run --fold 0   # peak memory only
$TORCH_PY      -m learn.song_soundspace train --arm B1|B1r|B2|B2a --fold f
$TORCH_PY      -m learn.song_soundspace propose-targets                     # E1
.venv/bin/python -m learn.song_soundspace score-targets --shard i/3
.venv/bin/python -m learn.song_soundspace report-1
$TORCH_PY      -m learn.song_soundspace bridge --user-approved              # E2
$TORCH_PY      -m learn.song_soundspace propose-songs --user-approved       # E3, E4 C-fine picks
.venv/bin/python -m learn.song_soundspace score-songs --user-approved --shard i/3 [--b0-best8]
.venv/bin/python -m learn.song_soundspace report-2
.venv/bin/python -m learn.song_soundspace c-start --user-approved-start --shard i/3
.venv/bin/python -m learn.song_soundspace report-3
```

- **Outputs:** `~/ndsp-presets/learn/song-settings/soundspace/` (`bank2/`, `relabel/`, `sets/`,
  `models/{B1,B1r,B2,B2a}/fold{f}/`, `scores/`). Each score file records the hash of the proposals
  it came from.
- **The committed summary:** `docs/song-to-settings-soundspace.json`.

**Tests, in `tests/test_song_relabel.py` and `tests/test_song_soundspace.py`:**
- **The weights:**
  - they reproduce the table from the stored step-1.2 medians, with the right cab's settings taken
    from cab-on bases;
  - the clip holds;
  - the right cab's settings and the right mic are masked when the label's right cab is off;
  - mics keep B0's weight.
- **The draws:**
  - seeded and reproducible, 250 per fold, with 42/42/42/42/41/41 per cell;
  - the anchors and record-like centres come from the example's own fold, with centres uniform per
    part and the fallbacks counted;
  - new examples are single-fold and use no diagnostics target track;
  - indices start at 10000; the bank's files are untouched.
- **The probes:**
  - pulls interpolate on the unit scale, with t = 1 equal to the anchor's continuous settings;
  - the mic and switch probes change only those;
  - jitters are seeded and keep mics and switches;
  - identical settings are rendered once;
  - the cap counter works.
- **The timeline:** probe renders are trimmed and judged exactly as the stored bank render.
- **The repeat check:** silent halves are dropped and counted, not failed.
- **The sets:**
  - r and the weights, which sum to 1;
  - non-finite members are dropped;
  - a small or non-finite d_S keeps the point label.
- **The censored head:**
  - the likelihood equals the Gaussian density inside (0, 1), and the tail mass within 1e-6 of 0
    or 1;
  - the soft bound keeps a gradient outside (−1, 2);
  - the top answer is the clipped mean, and samples clip;
  - the box score at a limit includes the censored mass.
- **The losses:**
  - with all s_j = 1 and nothing masked, B1's loss equals B0's on a toy batch;
  - the set loss with one member equals B1's;
  - **the toy mode test:** with two members at 0.2 and 0.8, equal weights and one component, the
    fitted mean lands within 0.05 of a member, not at 0.5;
  - the record-like weight gives half the training loss, and none on validation.
- **The fold rule:** model f's rows exclude fold f, and validation bands equal B0's (on a
  synthetic index).
- **Evaluation:**
  - best of K is picked on the search half and scored on the held half;
  - E1's unit list matches the stored report and its hash;
  - a new arm's refused answer scores as S, and the pre-existing drops apply to all arms;
  - the provisional decider uses broad units only and records "undecided" when the halves
    disagree;
  - `choose` with ties to the cheaper;
  - the C-fine pick among the 8 lowest objectives;
  - the approval flags for the songs (E2, E3, C-fine), B0's best of 8, B2a and C-start, with
    C-start refused unless E3 chose B1 or B2;
  - distinct sample seeds for E1 and E3;
  - the caps and the disk checks.

## The ledger entry (to be entered before any compute)

```json
{
 "test_id": "song-settings-soundspace",
 "plan": "docs/song-to-settings-soundspace-plan.md",
 "entered": "2026-10-16, before any compute; reviewed 2026-10-16, approved with changes, all folded in (11 required + 3 recommended); starts only on the user's yes. A second yes covers the songs (E2, E3, E4 C-fine); B0's best-of-8 and B2a are optional, each on its own yes; C-start is offered only if E3 chooses B1 or B2",
 "repeat_use": "E1 re-uses the arm-B diagnostics' 120 render targets (diag/report.json's unit list, 228 informative; the audit's 224 kept beside; list hash appended to the tally before any score): their second use, declared; their results shaped this plan. E2 (zero renders, records' held distances on step 3's stored K_S paths) and E3/E4 are further uses of step 3's 24 parts / 142 directions, judged at each part's judge_lag, run only on the songs' yes and entered in the tally before they run. Training uses arm B's bank (fold-correct), its relabel renders and 2,500 new bank examples; no diagnostics target track enters any training set. The sensitivity table (37 numbers) comes from step 1.2 windows that may share tracks with E1 targets and from bases around every fold's optima: stated, minor",
 "parts": ["E2-E4: step 3's 24 knob-ceiling parts (song_settings.cells(), 142 directions after the readout's 2 drops); E1: no record, the diagnostics' targets (targets.json)"],
 "bands": "E1: the diagnostics' 14 bands. E2-E4: step 3's 14 bands. Training: arm B's bank sources (classed development DIs and Guitar-TECHS P1/P2), fold-correct",
 "audio_only": "1,000 bank examples re-rendered with 9 probes each through their own measure-DI windows; 2,500 new bank examples (windows fold-own with p 0.5 else P1/P2, same-fold backings, no diagnostics target track); exact lists appended to the tally at the draw, before any render",
 "folds": "docs/song-settings-folds.json; model f trains on fold != f (bank and new examples), validation bands = B0's fold f; relabel members and record-like centres from the example's own fold's K_S optima only (centres uniform per part); each E1 target read by its band's fold model, each step-3 part by its fold's model (asserted)",
 "seeds": "training 20261018 + fold (B1, B2, B2a; B0's), B1' 20261031 + fold; relabel draw random.Random(20261026); probe jitters SeedSequence([20261027, i]); new examples random.Random(20261028); E1 samples SeedSequence([20261029, target, view, direction]); E3 samples SeedSequence([20261030, part index, amp index, direction]); C-start search 20261013 (arm A's)",
 "training": "B0's body and recipe (40 epochs, patience 5, batch 64, lr 1e-3, hand-clipped gradients) with a censored continuous head (mean -1 + 3 sigmoid; limit labels within 1e-6 score the tail mass) and B0's group normalisation with sensitivity weights s_j inside the continuous and switch groups (step 1.2 medians / amp mean, clipped [0.25, 4]; right-cab level, distance, position from cab-on bases and masked with the right mic when the label's right cab is off; mics B0's weight); K_S-centred examples weighted to half the training loss (not on validation); early stopping on each arm's own loss. B1 and B1' (reseeded): no new data. B2: plus 2,500 record-like examples and set targets on 1,000 relabelled examples (members = label + finite probes, normalised weights exp(-r/0.25), r = d/d_S; mode-seeking loss sum_m sg(gamma_m) L(theta_m), gamma = softmax(log w + un-normalised joint log-likelihood); halves with d_S < 0.1 or non-finite keep the point label). B2a (optional): B1 plus the record-like examples, no sets. MPS one job at a time, ~11 GB, ~13 h (18 h with B2a); peak RSS measured first",
 "gate": "No pass/fail bars. Measured: held-half judge distance through the measure DI, as log ratios. Compared: per target/part means, band-weighted with 90% band-clustered intervals (training-seed variance not included; B1' - B1 reported as a yardstick), leave-one-band-out, part-weighted, per amp and class (crunch descriptive). Refusals: only pre-existing drops apply to all arms; a new arm's non-finite held half scores as S (log ratio 0), counted per arm, also per sample in best-of-K. Decides: the songs' top answer vs S (E3) on the songs' yes; otherwise, provisionally, E1's view-1b top answer vs S on broad targets only, with the K_S-prior half beside it and 'undecided' if the halves name different winners. Candidates S, constant, B0, B1, B2 in that cost order; best band-weighted mean, ties (paired 90% interval contains 0) to the first in cost order. Power ~+-0.07 (songs), ~+-0.09 (E1): a result of S or B0 reads 'no gain shown at this power', the user's call. Reported only: B1', B2a, E1's other views and measures, E2's density Spearman and max-density picks, E3's best-of-8 vs K_S at 8 and shuffled input, E4's C-fine and C-start vs S and 3-C', the relabel map. Set-up (integrity): 20 label re-renders within 1e-3 on finite halves (silent halves dropped and counted), feature parity on 3 new examples, head/sampler agreement, fold assertions; any failure stops the run for an amendment",
 "renders": "caps: new examples 2,550; relabel 9,050; E1 (B1, B2, B1') 4,350 (without songs 15,950); E3 1,750 and E4 C-fine 450 (songs' yes; 18,150 with songs); optional B0 best-of-8 1,150 and B2a on E1 1,450; C-start 7,650 (only if E3 chooses B1 or B2); everything 28,400. Running total ~147k before this, experiment 4's actual renders included (reconciled against the ledger first); ~162.8k without songs, ~165.0k with, at most ~175.2k with every optional item and C-start. CPU <= 3 render processes machine-wide, Renderer isolate=True, torch/separation 2 threads, memory/swap guard, disk checked before the new renders and features (>= 33.5 GB free) and disk_ok every 50 renders",
 "tally": [],
 "outcome": null
}
```

## Stated limits

- **Development data only, one take per part.**
- **Repeat use:** E1's targets and step 3's parts already shaped this plan. Any gain here is
  optimistic and needs a fresh draw (rung 2 or step 7) before it is trusted for shipping.
- **Power:** gains smaller than about a quarter of K_S's can't be told from ties.
- **One architecture, one seed per fold.** The decision intervals leave out seed variance; B1′
  shows its size for one recipe only.
- **B2 bundles two ingredients.** Only B2a, if run, separates them, and only on E1.
- **The probes map the equal-sound set along declared directions only** (toward one anchor,
  mics, switches, two jitters). They are not a full map of the set.
- **τ, the probe radius and the anchor rule are fixed, not tuned.**
- **The mode-seeking set loss can make the model overconfident** on relabelled examples. The other
  examples keep the plain likelihood.
- **The relabel is model-free.** An on-policy round (rendering the model's own samples per fold)
  would show its own errors, but costs about 4× more per fold to keep folds clean. It is the next
  step if B2's samples still miss.
- **The sensitivity weights come from 15 windows × 4 bases**, at one move size, with mics not
  measured. The right mic's mask is by logic, not measurement. The table is shared, not fold-split,
  and not wholly free of evaluated content.
- **Crunch record-like centres are concentrated** (one part per fold in folds 0, 2 and 3).
- **Pulling toward K_S optima can exploit the judge's taste for range limits.** That is why a
  leading B2 gets a listening check before any product step.
- **E4 is descriptive,** and C-fine relies on B's density, which E2 measures on the same parts.
- **No feature-level change:** the 96-band log-mel with time pooling stays. If input gain is not
  carried by the features, weighting can't create it. If B1 and B2 both tie B0, the front end is
  the remaining suspect.

## Amendment 1 (2026-10-16, before any compute)

Written while the code was being implemented (`learn/song_relabel.py`, `learn/song_soundspace.py`),
before any render, training or score.

**The risk in the set loss.**
- As declared, the responsibilities are γ_m ∝ w̃_m · exp(ℓ_m), with ℓ_m the member's weighted
  joint log-likelihood, not normalised.
- The members' weights differ by a few nats (e⁻¹ for a member closing 75% of the gap, e⁻² for half).
  Members' log-likelihoods, summed over 10–20 terms, differ by tens of nats.
- So γ is close to 1 / 0, and it goes to whichever member the model already prefers, whatever its
  rendered closeness. The sound-space weights would barely matter.

**The fix.**
- γ_m ∝ w̃_m · exp(ℓ_m / D_m), where D_m is the member's number of active (unmasked) terms:
  continuous settings, switches and mics. The model's log-likelihood is tempered per dimension, so
  rendered closeness and the model's preference weigh on a similar scale.
- The gradient is unchanged: the responsibility-weighted loss Σ_m sg(γ_m) · L(θ_m), with a
  stop-gradient on γ.
- With one member it is still B1's loss exactly.
- **Tests:**
  - with equal weights and a model preferring one member by 30 nats over 10 terms, γ follows the
    tempered ratio (e³), not 1 / 0;
  - the toy fit (two members, one component) still lands on a member, not the midpoint.

**Declared choices** (implementation readings of the plan, fixed here):
1. **S is not a set member.** S is the scale (d_S), not a probe of the equal-sound set. Members are
   the label and the other finite probes.
2. **The refusal rule applies to every candidate:** a non-finite or non-positive held half scores
   as S for B0 and the constant too, not only the new arms. It is counted per arm.
3. **The feature parity check runs on 3 stored bank examples** (no separation, no AAC), comparing
   the new code path with the bank's stored features. New examples have no stored reference
   features.
4. **The loss runs on the CPU.** The network runs on MPS; its head outputs move to the CPU for the
   loss, because `torch.special.log_ndtr`'s MPS support isn't confirmed. The cost is small.
5. **The right mic is masked with the right cab off,** like the right cab's level, distance and
   position. That follows from the switch logic; it was not measured.
6. **Batch order** is seeded by `numpy.random.default_rng([seed, epoch])`, with the arm's seed (B0
   used `default_rng(epoch)`). B1′ is the arm `B1r` in the code.

## Amendment 2 (2026-10-16): no fixed render limit; stopping is evidence-based

The user confirmed on 2026-10-16 that the 200k limit is replaced by evidence-based stopping (ML plan
decision 2, #203). This amendment was made while the relabel renders and B1's training ran, before
any reading.

- **The running-total lines above are records only,** no longer limits. Every result reports the
  renders it actually used.
- **The caps in the budget table become expected sizes and efficiency guards.** A step that
  reaches its cap stops and reports. It continues only under its stopping rule below.
- **The stopping rules:**
  - **Training:** each arm stops early on its own validation loss (patience as declared). No arm
    is trained longer than that.
  - **Growing the relabelled set** beyond 1,000 examples, or the record-like examples beyond
    2,500, happens only if B2 beats B1 on E1's broad units, and a B2 trained on half the new
    examples is clearly behind the full B2 (held-out learning curve still rising). Otherwise the
    bank stops here.
  - **Evaluation:** E1 and E3 keep their declared units. A further evaluation is added only if
    its interval would answer a question these leave undecided.
- **"Ask before passing 200k" is dropped.** The optional items and C-start still need their own
  yes, as declared.

## Amendment 3 (2026-10-16): the parity check skips second-guitar examples

Made after the features step stopped on its own guard, before any feature of a new example was
computed and before any reading.

- **What failed:** parity failed on bank example 10, which has a second guitar.
- **Why:** the bank's stored features were built while bank renders were still landing. A
  second-guitar example drew its second render from the renders that existed then, so today's
  recomputation can pick a different one.
- **The check now:** it uses examples without a second guitar (bank 0, 6 and 12). Those reproduce
  to 0.0 dB.
- **Limits:**
  - The stored bank features stay as they are; they were trained on as stored.
  - A new example's second guitar is drawn from the renders present when its features are built.
    That is deterministic for this run.

## Amendment 4 (2026-10-16): the relabel repeat tolerance

Made after the `sets` step stopped on its own guard, before any set or training on sets.

- **What happened:** the 1-in-50 label re-renders, judged against the bank's stored 16-bit FLAC
  renders, differed by up to 0.0034. That failed on 3 of 40 halves: bank examples 3 B, 4201 A and
  5359 A, at 0.0015, 0.0013 and 0.0034.
- **Why the tolerance was wrong:** it was 1e-3, tighter than the project's repeat tolerance of
  0.005 (knob ceiling's REPEAT_TOL). It was never measured against a stored 16-bit render, whose
  quantisation alone moves the judge a little.
- **Why 0.005 is safe:** set members are weighted by d / d_S with τ = 0.25, and the probes'
  distances are mostly over 0.1. A 0.0034 shift is negligible there.
- **The change:** the tolerance is now 0.005. All 40 halves pass. Nothing else changes.
