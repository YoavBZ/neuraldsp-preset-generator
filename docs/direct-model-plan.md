# Direct prediction, song to settings, as the main route: plan

Declared 2026-10-19, before any compute for it. Development data only. The rules of
[`research/ml-plan-2026-10.md`](research/ml-plan-2026-10.md) section 5 apply, with the user's rules
of 2026-10-16: estimates with 90% band-clustered intervals, no pass/fail bars, evidence-based
stopping, renders and hours declared, licence-clean open-source tools only.
- **Code (after review, before any compute):** `learn/direct_gap.py` (the pre-check) and
  `learn/direct_model.py` (training, inference, the decision test, the listening page), tests
  `tests/test_direct_gap.py` and `tests/test_direct_model.py`.
- **Ledger:** `direct-model` in [`dev-test-ledger.json`](dev-test-ledger.json).
- **Data:** `~/ndsp-presets/learn/direct-model/`.

**Status:** declared; independent review below.

## The decision this plan serves

**Taken with the user on 2026-10-19: arm A is paused, and direct prediction (song to settings) is
the main route.**
- **Why arm A is paused.** The audited oracle test
  ([arm A with Mega-53, amendment 2](arm-a-mega53-results.md#amendment-2-the-oracle-di-arm-on-stage-f-2026-10-18))
  searched through the part's *true* DI against the htdemucs full-mix stem and read +0.012
  [−0.088, +0.112] against S. Even a perfect rebuild doesn't help, because the separated stem it
  scores against is mostly leftover mix (median stem SNR 0.43 dB on stage F). Arm A's own recipe
  reads −0.028 [−0.064, +0.008] there.
- **Why direct prediction.** Part C ([results](pretrain-set-results.md), audited) found that the
  direct model stops improving with more data on **true** mixes (Δ 20k → 40k +0.0012 [−0.0020,
  +0.0045]) while it keeps improving on the guitar alone (−0.0063 [−0.0092, −0.0035]) and on
  training-style power-sum mixes (−0.0085 [−0.0111, −0.0059]). So the limit is how realistic the
  training mixes are, not how many examples there are. Half the true val mixes are mastered, and
  training never sees mastering; on mastered val examples E got slightly worse with more data
  (+0.0040 [+0.0008, +0.0072]).

This plan builds one direct model with the mix-realism fix and gives it **one decisive test on
real mixes**, against the starting preset S.

## What is built: D

**D** is part C's network trained on part C's stored examples, band-clean, with mel-domain
augmentations chosen by a measured gap (below). **D0** is the same with part C's composition
unchanged (no realism augmentation): the control that says what the fix bought.

- **The network:** part C's half-width arm B network (`pretrain_set.build_net`: blocks of 16, 32,
  64, 96 channels, a 256-wide trunk, the mixture head with `song_model.K_MIX` components, switch and
  mic heads), B0's loss, inputs a 2 × 96 × 446 half (stem, mix), the two half LUFS, the amp and
  the base class. **Size unchanged:** at 40k the clean-stem and power-sum errors were still falling
  (the readouts above), so capacity is not what stopped part C on true mixes.
- **The data:** part C's stored train examples whose band is **not** one of stage F's 12 bands
  and not one of the known-answer bands (none are in the pool). Counted on the stored rows
  (2026-10-19, zero renders): **21,311 examples** (20,311 train, 1,000 early stopping) from **277
  sections in 9 bands** (Eggy 96 sections, Renesans 37, Death Of A Romantic 32, Ale Lak 31,
  Rebuild The Evil 30, Hollow Ground 25, Storm Of Particles 24, Starnes And Shah 1, The Long Wait
  1); about 3.5k per amp and base class. Part C's curve puts 20k at its flat point on true mixes.
  - **Why band-clean.** 177 of part C's 520 train sections are other DIs of stage F's own
    sessions, whose backings contain the stage F part's real amp track and its mix; 66 more come
    from other songs of stage F's bands. Arm A's comparator H used a C′ that never saw the part's
    band, so D must not either. It also mirrors the product, whose songs are never in training.
  - **Asserted in code:** no training row from a stage F band, a stage F DI (part C's reserve), a
    known-answer DI or band, Guitar-TECHS P3, sets 4–6 or a held-out session.
- **The recipe:** part C's (`pretrain_set.train_one`): Adam 1e-3, batch 64, one half per example
  per epoch, half A's first second masked, gradients clipped by hand, early stopping on the 1,000
  early-stopping examples with one fixed draw, patience 4. **One change, declared:** at most **40
  epochs** (part C: 30), because in 4 of part C's 11 runs the best epoch was the last. D0 and D share
  it, so their comparison is matched.
- **Seeds:** 20261042, 20261043 and 20261044 for both D0 and D (the same initialisation and order
  per seed). Augmentation draws: `SeedSequence([20261060, i, epoch])`.
- **The answer:** the ensemble of the three seeds. Continuous settings: the mean of the three
  top-component means, clipped to [0, 1]; switches: the majority of the three (p > 0.5); mics: the
  argmax of the summed probabilities. The settings are S's preset for the amp and base class with
  the labelled dimensions (`knob_ceiling.space`) replaced, as part C labels them.

### Inference on a real section (declared now, tested for parity)

- **Inputs:** the 10-s crop's full mix and its htdemucs stem (`learn.separate.GuitarSeparator`,
  htdemucs_6s, 2 threads, a 30-s context cropped, as stage F's stems were made). The search half's
  features only (1.0–5.5 s or 5.5–10 s, `song_aug.logmel`), so D sees what arm A's search saw.
- **Loudness:** one gain on both channels so the crop's mix reads the training median
  (`levels.json`'s `eval_mix_lufs_median`), as training set its mixes; the half LUFS go to the
  conditioning as in training.
- **Quantised as stored:** 0.5-dB steps from −112 dB (`pretrain_set.quant`), so the 8-bit storage
  is not a domain cue. Half A's first second masked, as in training.
- **Parity test:** a val example's stored audio-derived features reproduce through this path within
  one quantisation step.

## Why this should beat S where B2 didn't, and why it might not

B2, arm B's sound-space retrain, tied S on step 3's songs: −0.033 [−0.100, +0.035]
([results](song-to-settings-soundspace-results.md)). What differs here:
1. **The DIs.** B2 trained on 12.5k examples (the 10k bank and 2.5k record-like ones); half the
   bank's windows are Guitar-TECHS P1/P2 exercises that part A found mostly hummy. D trains on 21k examples from
   screened clean 10-s sections of real songs. Part C showed DI diversity matters (half the
   sections: +0.0087 [+0.0032, +0.0141] worse, one seed).
2. **The composition.** The bank mixed a render into another song's crop (58% of bank examples use
   a stage F song's crop as backing, measured 2026-10-19). Part C mixes the render into **its own
   session's backing at the same time**, at guitar-to-backing levels drawn from 971 measured
   development sections: a record-like mix.
3. **The realism fix, aimed at a measured gap.** Part C's divergence is specific: true minus
   power-sum on the same unmastered examples +0.0070 [+0.0049, +0.0092]. One likely mechanism: in a
   power-sum mix the stem and mix channels are guitar + backing at two known gains, so the network
   can solve for the guitar cell by cell; true mixes break that, and a real separator's stem has no
   such relation to the mix at all. The fix targets exactly that, plus mastering.

**Against it, stated plainly:**
- B2 already trained with real htdemucs separation, mastering and AAC (each with p 0.5), and still
  tied S. So "realism" alone is not new against B2; the bet is that cleaner, record-like data plus
  realism does what neither did alone.
- The labels are drawn (factory 40%, start 20%, wide 40%), not record-like. The diagnostics found
  arm B's single answer shrinks toward mid-range while record optima sit at a range limit on 35% of
  settings ([diagnostics](song-to-settings-diagnostics-results.md)). D inherits that risk.
- Stage F's stems are poor (0.43 dB median SNR). D can lean on the mix, but the guitar sits a
  median 7.9 dB below its backing.
- **The prior expectation is modest:** somewhere between B2's −0.033 and arm A's development
  −0.083. At stage F's power (below) the interval excludes 0 only if the true effect is about −0.05
  to −0.11 or better. A tie is the likeliest single outcome; the test is cheap enough that it is
  worth one look.

## Alternatives considered

| Design | Cost | Expected value | Verdict |
|---|---|---|---|
| **D: part C's data, band-clean, mel-domain realism chosen by a measured gap** | 0 training renders; about 6–7 GPU h (D0 and D, 3 seeds each); about 815 test renders | Uncertain, modest (above); the only option that is cheap, leak-free and aimed at part C's measured limit | **Chosen** |
| **A preset class, then refine:** classify the amp's nearest dry factory preset, then regress the residual | 0 renders (factory-mode labels exist for 40% of examples; nearest-preset labels in knob space for the rest); about the same GPU | Bounded by the menu: on step 3 the true-DI search beats the best of 111 menu presets by −0.205 and S by −0.293, so even a perfect menu pick is worth roughly −0.09 against S (different part sets, so rough); a predicted pick gets a fraction. Against the user's goal (generate, not choose) | Not chosen; a later head if D's errors look like mode confusion |
| **Predict from separated stems only** (htdemucs or Mega-53), no mix channel | Training stems would still need a stand-in (no training audio is stored); Mega-53 is about 6× htdemucs at inference | The oracle-DI result says these stems are mostly leftover mix (0.43 dB); removing the mix removes the cleaner context, not the problem. Mega-53 tied htdemucs on stage F (−0.017 [−0.039, +0.004]) | Not chosen. D keeps both channels and learns to weigh them |
| **Train only on true audio mixes** (sample-domain mixing, real separation) | Part C stored no training audio: re-render about 21k examples (about 3.5 h on 3 shards) and keep audio or several fixed mixes per example (about 8 GB, against 2.7 GB of headroom above the 31 GB guard today); htdemucs over 21k mixes about 30 h of CPU | Removes the cross term exactly, but fixes one or two mixes per example (part C redraws every epoch), and the cost is an order of magnitude higher | The fallback if the pre-check shows the mel domain can't close the gap, and only after disk is freed (the 20 GB PR12 cache, the user's call) |
| **Fine-tune on arm B's bank** (real separation, mastering, AAC) | 0 renders, about 1 GPU h | The bank is contaminated for this test: 58% of its examples use a stage F song as backing and 28% take windows from stage F bands; 3,299 are clean of both, half of them Guitar-TECHS | Not chosen |

**A cheaper decisive test?** The part C curve models already exist, so rendering them on stage F
would cost about 190 renders and no training. They are not usable for the decision: a third of
their training sections come from stage F's own sessions, with the test mixes in their backings,
so any reading is confounded in an unknown direction. They are used only on the known-answer songs
(no overlap), as a descriptive row (below). The GPU cost of D is the price of a clean model.

## Step 1: measure the gap before building (zero renders, CPU)

**The question:** how do training-style inputs differ from real ones, and which augmentations close
that difference? Measured on real development mixes that the decision test doesn't use, then
checked, without choosing anything, on the test inputs.

### The real pool R (declared)

- **Sections:** multi-section step 1's passing 10-s sections (`~/ndsp-presets/learn/multi-section/sections/`)
  of the 38 label-table parts outside stage F, **less** every part whose song is a stage F song or a
  known-answer song (the same mix as a test input), less every part the
  [bleed audit](audits/bleed-2026-10-16/README.md) reads high on either half. Up to 6 sections per
  part, drawn by `random.Random(20261061)`. The code prints the pool; about 15–20 parts in 8–10
  bands are expected. **If fewer than 6 bands remain, stop and report** (leave-one-band-out
  intervals would say nothing).
- **For each section, four inputs, both halves, quantised as training stores them:**
  - **R (real):** the session's full mix at unity with vocals (`learn.separate.context`, role
    `mix`), and its htdemucs stem from the 30-s context, cropped; loudness set by the inference
    rule.
  - **T₀ (part C's recipe, real guitar):** part C's training composition (`CurveData.batch`'s
    power-sum mix and leak stem, leak U(0, 6) dB, loudness to the training target) built from the
    section's **real amp track** mel and its backing mel (part C's backing rule: the mix list less
    the part's own tracks, every DI and leaking tracks), at the section's own guitar-to-backing
    level.
  - **T_k:** T₀ with augmentation configuration k (below).
  - **G (the training domain):** part C's stored train examples (a seeded 3,000 of D's 21,311),
    composed by part C's recipe.
- **Why pair R with T₀ on the same section:** both hold the same real guitar and the same backing,
  so their difference is the composition alone (the cross term and the stand-in stem). G against
  T₀ is the remaining gap the fix does not target: rendered against real guitars, drawn against real
  settings. It is reported, not targeted.

### The measures

- **Summary features per half** (declared list in code, about 80): per channel, the mean and
  standard deviation over frames of the log-mel in 12 band groups; frame-loudness percentiles
  (10th, 50th, 90th) and crest; frame-to-frame spectral flux; envelope autocorrelation at 5 and 20
  frames per band group (temporal smear); energy above 12 kHz and the share of spectral holes (cells
  15 dB below both neighbours); and **the two channels' relation:** the mean and standard deviation
  of stem − mix per band group, the share of cells where the stem exceeds the mix by more than
  0.5 dB, and the correlation of stem − mix with the mix level.
- **The domain gap:** an L2 logistic regression (standardised features, C = 1) separating one input
  type from another, scored by **leave-one-band-out** cross-validation, so the score is always on
  bands the classifier and any fitted augmentation never saw. The gap is the pooled out-of-fold AUC,
  with a 90% interval from 2,000 band-bootstrap resamples (`random.Random(20261062)`). AUC 0.5
  means indistinguishable.
- **Per-cell diagnostics** (descriptive): the distribution of R − T₀ by band group and local
  guitar-to-backing bin, per channel, so the report says *where* the gap is.

### The candidate augmentations (declared), and how each is decided

Each acts on part C's stored guitar and backing mels on the GPU, per example and epoch.

| Candidate | What it does | Fitted on (never val, never a test input) | Decided by |
|---|---|---|---|
| **X, cross term** | Each channel gets its own cross-term draw: P = g + b′ + 2√(g b′)·c·ε, ε a unit normal smoothed over 4 frames (the STFT overlap) and scaled by 1/√(bins in the mel band), floored above 0 | c and the smoothing: matched to the measured true − power-sum error (median, 90th and 99th percentiles, lag-1 autocorrelation) on the 164 audit examples outside stage F's bands, which store the render and backing audio | R's AUC |
| **P, a separator stand-in for the stem** | Replaces the leak stem: stem power = m_g·g + m_b·b′ per cell, with m_g = σ(α + β·r) and m_b = σ(γ + δ·r) per band group (r the cell's guitar-to-backing dB), a per-example quality offset on α and γ, and per-cell log-normal noise | On R's triples (amp track, backing, htdemucs stem), leave-one-band-out for the AUC readout | R's AUC |
| **M, mastering** | `song_aug.compress` in the mel domain: a broadband RMS compressor on frame power (attack 1 frame, release 10 frames, ratio U(2, 4), threshold 3 dB over the mean, make-up U(0, 4) dB) and a frame-level ceiling, on both channels (a separated stem comes from the mastered mix), with p 0.5 | Nothing fitted: `song_aug.compress`'s own distributions. Fidelity: mel-domain M on the power-sum against `compress` on the true audio mix, on the same audit examples | **Included by declaration**: product songs are mastered and part C's mastered val readout got worse with data. R is unmastered, so M is never judged by R |
| **Vocal share** | p(vocals) in the backing draw, from part C's 0.5 to the measured share of R sections whose song has a vocal track playing | The R pool's sections | Measured share replaces 0.5 |
| **Guitar-to-backing level** | Part C already draws it from the 971 measured development sections | — | Reported against R's and stage F's levels; no change unless the distributions differ by more than their own sampling spread, which would be an amendment |
| **Codec (AAC)** | Not in stage F or the known-answer inputs; the product's files may be | Encode 30 R sections with `song_aug.aac` (128–256 kbps) and compare | Added (as the measured per-band shift and cell noise) only if R against encoded R has an AUC interval above 0.5 |
| **EQ and reverb** | **Excluded by design.** They change the guitar's tone, which is what the label describes, and the decision test's target is the dry amp track (the starting presets are dry) | — | Long-term spectrum and smear gaps are reported (G against T₀) |

**The selection rule (declared):** among k ∈ {X, P, X + P}, the configuration with the lowest R AUC
(T_k against R) is chosen; a configuration whose paired AUC difference against the lowest has an
interval containing 0 ties, and the one with fewer components wins a tie (X before P before X + P,
the cheaper and less fitted first). D's augmentation is the chosen k, plus M, plus the measured
vocal share (plus codec if its rule adds it).

### The early stop (the cheapest point to stop)

**Before any training of D:**
- if T₀ against R already reads an AUC interval that contains 0.5 (the composition gap is not
  measurable on real mixes), or
- if the chosen configuration's AUC difference against T₀ has an interval containing 0 or above it
  (the mel domain gives no measurable handle on the gap),

then **stop and revisit with the user**: the plan's premise (the gap is the composition, and it can
be closed without re-rendering) has failed, and the next step would be the true-audio fallback or a
different route. This costs about 3 h of CPU and agent time and no renders.

### Checks that the augmented mixes moved toward real ones (declared)

1. **Feature level, deciding the configuration:** AUC(T_D against R) against AUC(T₀ against R),
   paired, on held-out bands (above).
2. **Feature level, the test inputs (read before any decision render; chooses nothing):** the
   classifiers trained on the R pool score stage F's 126 search halves and the known-answer
   songs' search halves against G with part C's recipe and against G with D's augmentation. Reported
   as AUCs; if they disagree with the R pool's direction, that is reported, and nothing is re-chosen.
3. **Model level (after training; zero renders):** the same leave-one-band-out AUC on each model's
   pooled trunk input (the 1,152-wide embedding) between G and R, for D0 and D; and the in-domain
   readouts on part C's 3,000 val examples (9 bands): E on true mixes, on power-sum mixes, on
   mastered and unmastered examples, the divergence (true − power-sum on unmastered examples) for D
   and D0, paired per val example, seed-averaged, band-clustered (part C's code). D's val inputs use
   its own stem construction rebuilt from the stored guitar and backing mels with a fixed draw, its
   mix channel the stored true mix. Val's mastered examples have unmastered stems (part C's
   construction), so D's mastered readout carries that mismatch; stated.

**Second early stop (after D trains, zero renders):** if D's E on its own val inputs is not below a
constant predictor's (the training label median per amp and base class; paired, band-clustered
interval), D has learned nothing usable from realistic inputs. Stop and revisit; no decision
renders are spent.

## Step 2: training (no renders)

- **D0** (3 seeds) needs nothing from step 1, so it trains on the GPU while step 1 runs on the CPU,
  if the GPU is free. Its cost is lost if step 1 stops the plan.
- **D** (3 seeds) trains after step 1 chooses its augmentation.
- **Time:** part C trained at about 184 examples a second on the MPS GPU (20k runs took 30–50
  minutes for up to 30 epochs). At 20.3k examples, up to 40 epochs and some augmentation cost:
  about 1 h a run, at most about 1.5 h. Six runs, about 6–7 GPU hours, D0's half beside step 1.
- **Guards (part C's):** an epoch skipping more than 5% of its steps on non-finite gradients aborts
  the run; it is retried once, then the plan stops. The early-stopping loss is finite at the chosen
  epoch. Memory: the 21k examples' uint8 mels are about 1.8 GB, backings about 0.3 GB.
- **Recorded per run:** epochs, the best epoch, time, examples per second, skipped steps, peak
  memory, and the masked-frame count.

## Step 3: the decision test (about 815 renders)

All of it is fixed now, before any training.

### What is rendered

- **Stage F** ([arm A with Mega-53](arm-a-mega53-plan.md), amendment 1): 21 parts, 12 bands, **126
  directions** (part × amp × search half). D predicts from the search half's features; its settings
  are rendered **once** through the part's measure DI and judged on the held half against
  `reference.wav` at the part's `judge_lag` (`knob_ceiling.judge`), exactly as S, H and M were.
  Paired with the stored S and H (`~/ndsp-presets/learn/arm-a-mega53/F/`).
- **The known-answer songs** ([B1](known-answer-b1-results.md)): 4 songs, 3 bands, primary items 1,
  3 and 4, **144 directions** (6 item-sections × 3 amps × 2 search halves per song). The input is
  the item's full mix and its stored htdemucs stem; the base class is the one B1's S used for that
  unit. Judged as B1 judged arm A (`learn/known_answer.py`'s judge against the truth record, lag
  0). Paired with the stored S and A (arm A).
- **D0** is rendered on the same directions (descriptive, below), because what the realism fix buys
  on real mixes is the thing to learn whatever D shows.
- **The part C curve models** (40k, three seeds, ensembled the same way) on the known-answer songs
  only, where they have no overlap: descriptive.
- **Priming:** one discarded render at S after every process start, amp change or DI change (the
  [start-transient rule](audits/start-transient-2026-10-18.md)). Each (part, amp) on stage F and
  each (song, section, amp) on the known-answer songs is one DI and one amp (items 1 and 4 share
  their sections' DI), so one priming render per group, then that group's arms and items back to
  back.
- **Repeat checks first (they stop the run if they fail):** 6 stage F directions
  (`random.Random(20261063)`) and 4 known-answer directions re-render S and must reproduce the
  stored held-half judge within 0.005 (log). This catches a plugin, renderer or convention change
  that would break the pairing with stored arms.

| What | Renders |
|---|---|
| Stage F: 63 groups × 1 priming + 126 directions × (D, D0) | 315 |
| Known-answer: 48 groups × 1 priming + 144 directions × (D, D0, curve models) | 480 |
| Repeat checks: 10 × (1 priming + S) | 20 |
| **All** | **815** (cap 860) |
| D alone (stage F and known-answer, with its priming) | 381 |

D alone is the user's "about 250" (270 directions) plus the priming the start-transient rule needs.
D0 and the curve models add about 430 renders, about 15 minutes on 3 shards.

### The primary contrast and its consequence (declared)

**P = D − S on stage F, all 126 directions:** per direction log(d_D / d_S) on the held half, per
part the mean over amps and directions, then the band-weighted mean with a **90% band-clustered t
interval** (12 bands, 11 df; `song_readout.bw_stats`, as arm A's stage F).
- **Interval entirely below 0:** D lands closer to the record than S on fresh full mixes. **Build
  the product on it:** direct prediction becomes the settings source in `generate` (and `match`
  without a DI), under a product plan; the first step of that plan re-measures D on new material
  when it arrives (B2's fresh known-answer songs, the cloud researcher's sessions).
- **Otherwise** (the interval contains 0 or lies above it): **stop and revisit with the user**, with
  the numbers below. No further D variant is trained without the user.

There is one primary. Every other figure is reported, never promoted.

**A refused answer** (the held half non-finite, for example a level at 0) scores as S (log ratio 0,
the product's fallback), as in the [sound-space plan](song-to-settings-soundspace-plan.md); the
count is reported per arm. Stage F has no S refusal (its pool rule).

### Reported beside it (not deciding)

- **Stage F:** D − H (against arm A's recipe); rows no high bleed (direction rule), F-song (new
  songs only), Cambridge only; per amp; per class; leave-one-band-out range; part-weighted; bands
  better and worse. D0 − S and D − D0 with the same rows.
- **Known-answer (3 bands, 2 df; descriptive, as B1):** D − S, D − A, D0 − S, the curve models − S;
  The Apprehended (the only fresh song) as its own row; Heather Jane, where S starts near the truth,
  named. Knob error against the truth on the identifiable knobs for D, S and A (B1's table), and
  the amp-free switch and mic agreement.
- **Spread:** each seed's own answer against the ensemble's in knob space (zero renders).
- **Reading of D − D0 (descriptive):** whether the realism fix moved anything on real mixes. It is
  read against step 1's check 2 (did D's training inputs look more like the test inputs).

### Power

- **The band SD of a contrast against S** was 0.069 for arm A on stage F, and about 0.14 for B2 on
  step 3's songs. On 12 bands the 90% half-width is then about 0.036–0.074, and the effect detected
  with 80% power about 0.054–0.11 (about 18–37% of the true-DI ceiling −0.293).
- So a result like B2's (−0.033) would read as a tie here. The test can show a clear gain, not a
  small one; a tie reads "not shown at this power", which is not a failure of the route but is a
  reason to stop and decide with the user before spending more.

### Repeat use of stage F (stated)

This is the third set of arms on stage F's 21 parts (H and M, then the oracle XO, now D and D0).
- **Nothing about D is chosen on stage F:** the recipe is fixed here, the augmentation is chosen on
  the R pool (stage F's songs excluded), and the test-input check (step 1, check 2) is declared not
  to choose. No stage F outcome feeds back into D.
- **What reuse does cost:** the parts are no longer fresh to the project, and stage F's earlier
  results shaped this decision to pause arm A. Its 4 Telefunken parts carry bleed (3 high), which
  pulls every ratio toward 0 (the no-high-bleed row is beside the declared row).
- The known-answer songs' second use: arms A and O before; D, D0 and the curve models now. Three of
  the four are repeat-use development songs (B1's caveat).

## Step 4: a small blind listening test on fresh songs (about 26 renders)

The decision test's targets are unmastered session mixes. The product's are released songs. This
check puts D in front of the listener on real, fresh, mastered songs. It is descriptive and does
not change the decision.
- **The songs:** 8 songs **the user picks**, each with an exposed clean or crunch electric guitar
  part (favouring guitar-exposed passages) and the time where it plays. None may be in any dataset
  the project uses; the code checks names against every inventory and validation catalogue
  (sets 1–6, MedleyDB, Guitar-TECHS P3) and refuses a match. The files stay local.
- **The trial:** the song's excerpt (the 10-s section as heard, level-matched to −20 LUFS), then A
  and B: the product's audition riff (`samples/riffs/`, `chords` for clean, `chords-mid` for crunch,
  CC BY 4.0) played through D's preset and through S, each at −20 LUFS. "Which tone is closer to the
  guitar in the song?" A, B or Same. This is the product's own question: the user will play their
  guitar, not the record's DI, through the preset.
- **D's input:** the section's mix and its htdemucs stem; D predicts from the first half (1.0–5.5 s),
  by the inference rule. The class is the user's call (clean or crunch); the amp by a seeded quota
  (PR12 3, SW50R 3, AC20 2; `random.Random(20261064)`).
- **Blinding and balance:** D is A on exactly 4 of the 8 trials (`random.Random(20261065)`); one
  catch trial with A = B (S twice) at a drawn position; the key in `private/key.json`; the page
  names no song or preset. Renders: 8 × (priming, D, S) + catch (priming, S) = 26.
- **Reading (descriptive):** D's share of A-or-B answers with an exact 90% interval, the share with
  "same" counted against D, and the catch trial's answer. One listener, 8 trials: it can show a
  strong preference or none.

## Budget

| Step | Renders | GPU | Wall-clock | Agents |
|---|---|---|---|---|
| Code and tests (`direct_gap`, `direct_model`), then a PR review | 0 | 0 | about 3 h | 1 implementer, 1 reviewer |
| Step 1: R pool contexts and htdemucs (about 100 contexts × 15 s), features, fits, classifiers | 0 | 0 | about 1 h CPU | — |
| Step 2: D0 (beside step 1), then D | 0 | about 6–7 h (about 3 h of it beside step 1) | about 3.5 h after step 1 | — |
| Step 3: inference, about 815 renders on 3 shards, report | about 815 (cap 860) | 0 | about 1 h | — |
| Results audit | 0 | 0 | about 1 h | 1 auditor |
| Step 4: listening page | 26 | 0 | about 0.5 h, then the user's 10 minutes | — |
| **Total** | **about 840** | **about 6–7 h** | **about one day** | **3 agents** (plus the task executor for monitoring) |

- **Renders so far:** about 300k (the roadmap's 250k, then multi-section, the rebuild steps,
  B1, part C and the oracle arm). No fixed limit (decision 2): this plan's renders are a fixed set,
  and it stops at its caps.
- **Disk:** 33.7 GB free on 2026-10-19 against the 31 GB guard, so **2.7 GB of headroom**. This plan
  writes under 0.5 GB: R's features as uint8 mels (contexts and stems are deleted after their
  features are taken), models (about 30 MB), and the decision renders' FLACs (16-bit, about 0.4 GB
  at most; only the listening renders are kept as audio if disk falls below 32 GB). Every writer
  checks free disk first and stops cleanly below 31 GB.
- **The cheapest stop:** after step 1, before D trains: about 3 h of agent and CPU time, no
  renders, and only D0's GPU time (if it ran beside). The second stop, after D trains, costs the
  GPU time but no renders.

## Risks, and what makes us abandon before spending

- **Step 1 finds no handle** (its early stop). Abandon D as specified; the fallback is true-audio
  training, which needs disk the machine doesn't have without the user's approval.
- **The R pool is too small** (fewer than 6 bands after its exclusions). Stop and report; the gap
  can't be measured on held-out bands.
- **Disk falls below 31 GB** at any writer. Stop; nothing is deleted without the user.
- **The repeat checks fail** (stored S not reproduced within 0.005). Stop: the pairing with stored
  arms is broken; find out why before rendering.
- **A leakage assertion fails** (a stage F or known-answer band, DI or session in D's training; a
  listening song in a dataset). Stop.
- **Training failure** (non-finite steps after a retry, or the second early stop). Stop.
- **Named, not guarded:** the drawn labels (not record-like) and mid-range shrinkage; the stand-in
  stem being fitted on 15–20 parts; the fit of X and M on 164 audit examples; real separators'
  failures that no per-cell model captures (for example a keyboard pulled into the stem); D's
  9-band training pool (its DI diversity is narrower than part C's 15 bands); mastering is
  approximated, never checked against real releases (only by the listening test); the amp is given,
  not chosen.

## What this plan does not do

- No new training renders, no new DIs, no held-out data.
- No arm A work (paused) and no shrink or search on top of D; a combination is a later question if D
  wins.
- No Tone King; Morgan's three amps only.
- The labels are part C's; B1's censored head and sensitivity weights are not added (one change at
  a time).

## Code (written after review, before any compute)

- `learn/direct_gap.py`: `pool` (the R pool and its exclusions), `contexts`, `separate`,
  `features`, `fit` (X on audit examples, P leave-one-band-out, M fidelity, vocal share, codec),
  `gap` (classifiers and intervals, the selection rule, the early stop: prints `GAP STOP` or
  `GAP CHOSEN <k>`), `check-tests` (the test-input check), `report`.
- `learn/direct_model.py`: `train --arm D0|D --seed s`, `readout` (the model-level checks and the
  second early stop: `MODEL STOP` or `MODEL OK`), `predict --stage F|KA`, `render --stage F|KA
  --shard i/n` (priming, repeat checks, caps), `report`, `listening build|score`.
- **Tests:** the band-clean filter and every exclusion (stage F bands, the reserve, known-answer,
  held-out); the R pool's exclusions (stage F and known-answer songs, high bleed); the inference
  path's parity with stored val features; each augmentation on synthetic mels (X's error quantiles
  against a numeric cross term; P's limits; M against `song_aug.compress` on a synthetic signal);
  the ensemble rule; the selection and early-stop rules on toy AUC tables; the refusal rule; the
  render counts and caps; priming once per group; the listening page's balance and catch trial.

## Machine order

- One GPU job at a time; at most 3 render processes machine-wide, with `isolate` and the bounded
  render server; long jobs launched with `setopt no_bg_nice`; separation only when at most 2 render
  processes run. Torch and htdemucs at 2 threads beside training.
- **Order:** this plan, review, ledger and roadmap (this PR) → code, tests, PR review → step 1 (D0
  training beside it) → `GAP CHOSEN` → D trains → `MODEL OK` → step 3's repeat checks, then the
  renders → report → independent audit → step 4 → the readout to the user.
