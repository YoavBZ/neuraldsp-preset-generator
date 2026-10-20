# The direct model with realistic stems: plan

Declared 2026-10-19, before any compute for it. Development data only. The rules of
[`research/ml-plan-2026-10.md`](research/ml-plan-2026-10.md) section 5 apply, with the user's rules
of 2026-10-16: estimates with 90% band-clustered intervals, no pass/fail bars, evidence-based
stopping, renders and hours declared, licence-clean open-source tools only.

*Training time (user, 2026-10-20): the pilot training (≈2.4 h) and the D/D0 runs (5–7.4 h) each
need the user's approval before they start.*

- **Code (after review, before any compute):** `learn/direct_stems.py`, tests
  `tests/test_direct_stems.py`.
- **Ledger:** `direct-model-stems` in [`dev-test-ledger.json`](dev-test-ledger.json).
- **Data:** `~/ndsp-presets/learn/direct-stems/`.
- **Replaces** the unmerged draft `docs/direct-model-plan.md` (branch `ml/direct-model-plan`). Its
  review findings are folded in here (listed at the end).

**Status:** declared; one independent review (go with required changes, all applied; see the end).

## The question, and why it is not settled yet

The first direct model, D_existing (part C's three 40k curve models, trained for a learning curve,
not as a product model), tied S on stage F: **D − S +0.033 [−0.053, +0.119]**, leaning better on
clean (−0.042) and worse on crunch (+0.137) ([results](direct-existing-results.md)). By ear it sat
above S on 4 of 5 guitar-exposed parts ([record-match listening](record-match-listening-results.md)).
That model was never developed for real songs, so its tie is not a verdict on direct prediction.

**The suspected flaw is a train/test mismatch in the stem channel.** The model reads two channels,
a stem and the mix (`direct_existing.features`).
- **In training** (`pretrain_set.CurveData.batch`) the "stem" is the rendered guitar plus an exact,
  scaled copy of the same backing, 0–6 dB below the guitar (`STEM_LEAK_DB`). The guitar is intact
  and the leak is the mix's own backing, so the network can cancel it against the mix cell by cell.
- **On stage F** the stem was htdemucs's separation: median SNR 0.43 dB against the amp track
  (Mega-53 0.70 dB). The error is not a copy of the backing, and the guitar itself is changed
  (darker, drop-outs, other guitars merged in; [stereo and mix check](stereo-and-mix-check-results.md)).
- **Part C's curve** points the same way: on true mixes it flattened at 20k–40k while the guitar
  alone and training-style mixes kept improving ([results](pretrain-set-results.md)).

**This plan asks, in order of cost:** (1) does the stem's quality move D_existing's answers, and
what does the mismatch cost in labelled error (zero renders)? (2) how much does it lean on the stem
against the mix? (3) what is a matched stem worth on real mixes (111 renders, descriptive)? Then (4)
a 5k pilot that pits real separated stems against a mix-only model and the old recipe, and only then
(5) the full build and one test on stage F (about 320 renders).

**What we expect, stated before any of it:**
- **B2 already trained with real htdemucs separation, mastering and AAC** (each p 0.5) and still
  tied S (−0.033 [−0.100, +0.035]; [results](song-to-settings-soundspace-results.md)). Realistic
  stems are not new. What is new: band-clean, screened 10-s sections from real sessions, each mixed
  with its own session's backing at measured levels, true sample-domain mixes, and Mega-53.
- **The mix-realism part is small in-domain.** On part C's unmastered val examples the gap between
  true and power-sum mixes at 40k is 0.1744 − 0.1626 = 0.012, about **7% of E**. Closing it fully
  moves in-domain error by that much at most.
- **The flat curve may be a floor of identifiability,** not of data: some settings may not be
  recoverable from a 4.5-s half of a mix at all. Nothing here separates the two.
- **Power is limited** (step 4): a tie is the likeliest single outcome, and a tie reads "not shown at
  this power", not "the route fails".

## Alternatives considered

| Design | Cost | Why chosen or not |
|---|---|---|
| **Retrain on real Mega-53 stems of true mixes, behind cheap checks and a 5k pilot (chosen)** | About 23k training-style renders (not judged), 20–26 h of separation (MPS + one CPU process), 7.5–10 GPU h, about 430 judged renders | The only option that removes the mismatch at its source. Each stop comes before the next spend |
| **A mix-only model (no stem channel)** | No separation: renders, true mixes and GPU only | Sidesteps the mismatch, and the product would need no separator. **A pilot arm (D_mix), and the whole route if step 1 finds the stem doesn't matter.** If it matches the separated-stem model it replaces it and saves about 15 h of separation |
| **A simulated separator** (a per-cell stand-in fitted on real stems, the draft's "P") | Cheap | Cannot make the artefacts the user heard: other guitars merged in, drop-outs, darkening that varies by part. Kept only as declared augmentations on top of real stems |
| **htdemucs instead of Mega-53** | 4.9 s per 10-s clip on 2 CPU threads (measured 2026-10-19) | About the same throughput as Mega-53's fast setting (1c). Mega-53 is the ML default and the user heard it as much better; arm A read a tie (M − H −0.017 [−0.039, +0.004]). htdemucs is used as the out-of-pipeline stem in the pilot readout |
| **Fine-tune D_existing** | Cheapest | It trained on other DIs of 6 stage F bands' sessions, whose backings hold the test parts; any stage F reading is confounded. Not used for decisions |
| **More data or a larger network** | Renders and GPU | Part C: flat at 20k–40k on true mixes, still improving on the guitar alone, so capacity and count are not the limit |
| **Stereo input** | Separation × 2 | The stereo check: no average gain as recorded; a blind pan estimate is a coin flip. Mono stays |

## Step 1: measure before building

Step 1 uses D_existing as stored (hashes checked) and the stored stage F inputs: the full-mix context
crop (hash-checked against `mix.wav`) and the stored stem crops. **The mix is held fixed; only the
stem changes.** Every stage F row is reported on all 12 bands and on the 6 bands unseen by part C
(`predictions.json`'s `unseen_by_part_c`), and without the MUSDB18 songs
(`locator_truth.MUSDB_TRAIN`/`MUSDB_TEST`: It Was My Fault For Waiting, Femme, Signs), on which
the separators may have trained.

### 1a. Does the stem's quality move the answers? (zero renders)

**Stem conditions** on all 126 stage F directions:
- **a, perfect:** the amp track (`reference.wav`'s crop).
- **a′, the training stem from the real guitar:** the amp track plus the part's own backing
  (`mix − reference`; the stored mix is the unity sum of the tracks, checked to 1.5e-7) at a leak
  drawn as part C draws it, U(0, 6) dB below the guitar. **Three draws** per direction
  (`random.Random(20261071)`); readings average over them.
- **b, htdemucs:** the stored crop (what D_existing was scored with).
- **c, Mega-53, as stored:** the 30-s context separation, cropped.
- **c_f, Mega-53, fast:** the 10-s crop alone, in the setting 1c picks.
- **z, no stem:** the stem channel set to 0 in the normalised input (−60 dB, the half-A mask's
  value), its stem LUFS held at b's. **m, stem := mix.**

**Conditioning parity.** The conditioning vector holds the half's stem and mix LUFS. Each condition
runs twice: with the stem LUFS from its own stem (as at inference), and held at b's value, so a
change of loudness cue is not read as a change of content. The mix LUFS and the one inference gain
are the same across conditions.

**Quantisation parity.** Every condition goes through the stored 0.5-dB grid from −112 dB
(`pretrain_set.quant`), as in training. Separated stems hit the floor more often (drop-outs), so the
share of cells at the floor is reported per condition.

**Measures, per seed, then averaged over the three seeds** (the ensemble answer takes one seed's top
component, `direct_existing.ensemble`, so a small input change can flip which seed wins; per-seed
readings avoid that):
- **Movement** d_k(x, y): for seed k, the mean |Δ| of its top-component means over the labelled
  continuous settings on the unit scale (part C's E metric); switch and mic agreement beside it.
- **Likelihood shift** Δℓ_k(x, y) = log p_k(θ_k,x | input x) − log p_k(θ_k,y | input x): how
  unlikely the answer from stem y looks to the model when it hears stem x. Log-likelihood, not AUC:
  it does not saturate.
- **The null:** the same measures between two leak draws of a′ (a′₁ against a′₂): how far the
  answers move under a change the model was trained to ignore.
- **Band-weighted** (12 bands; 6 unseen), 90% band-bootstrap intervals (4,000 draws,
  `random.Random(20261078)`).

**The labelled cost of the mismatch (zero renders).** The 276 audit examples store the render's
audio and their backing's audio, so their true mix can be rebuilt at the stored gains. On the **164
outside stage F's bands**, E of D_existing with (i) the training stem (leak), (ii) the guitar alone,
(iii) Mega-53's fast stem and (iv) htdemucs's stem of the true mix. They are D_existing's training
examples, so E is in-sample; the paired **difference** (iii) − (i) is the cost of the stem mismatch
with everything else held, band-clustered.

**Gate 1 (declared): does the stem route continue?** The stem matters if **any** of these holds:
- on stage F, the band-weighted interval of d(a′, b) − d(a′₁, a′₂) lies entirely above 0, on all
  bands or on the unseen bands;
- the same for d(a, b) − d(a′₁, a′₂);
- on the 164 audit examples, (iii) − (i) has an interval entirely above 0.

**Clarified 2026-10-19, after the code review and before `move` ran:** the stage F rows decide on
each condition's own stem LUFS (as at inference); the held-LUFS reading is reported beside it. The
audit condition decides on the band-clustered t interval (6 bands, 5 df); a band bootstrap is
reported beside it. Gate 1 runs without 1c, so c_f is Mega-53's fast setting (it is not used by the
gate; (iii) is defined as fast). 1d is not part of the gate and is not run with it.

If none holds, the stem barely matters to this model: **the separator route is dropped** (no
separation is spent) and the plan runs the **mix-only route**: the pilot with D0-5k and D_mix-5k
only. The true-mix and mastering parts of the fix are still tested that way.

### 1b. How much does the model lean on the stem against the mix? (zero renders, descriptive)

- **Labelled, in-domain:** part C's val examples from the 5 val bands that are **not** stage F bands
  (V_dev: 1,720 examples; Adam Buckley, Cnoc An Tursa, Dark Ride, John Morgan Kimock, Swatkins),
  stored stem and mix features. E under: as stored; stem zeroed; stem shuffled within amp × base
  class (both LUFS conventions); mix zeroed; mix shuffled; stem := mix; stem := the guitar alone.
  Reported: ΔE against as stored, paired per example, band-clustered; and the stem's share
  ΔE_stem / (ΔE_stem + ΔE_mix).
- **Unlabelled, stage F:** per-seed movement under z, m and the mix shuffled across parts.
- These say what each fix can buy: a model that leans on the mix gains little from a better stem.

### 1c. The separator setting for training (zero renders)

Measured 2026-10-19 on one 10-s clip (Passing Ships ElecGtr2), idle machine:
- **Mega-53 as stored** (20-s chunks, overlap 2): 31.5 s on 4 CPU threads and **19.3 s on MPS** for
  a 10.25-s clip (two 20-s chunks); 11.0 s on MPS for an exact 10-s clip. MPS matched the CPU to
  81 dB SNR (max |Δ| 1.3e-6): **MPS works.**
- **Fast setting** (one 10-s chunk, the model's training chunk length, overlap 1): **5.2 s on MPS,
  7.6 s on 4 CPU threads**, 25 dB SNR against the stored setting's output on the same clip.
- **htdemucs:** 4.9 s on 2 CPU threads.

**The check, off stage F:** the 164 non-stage-F audit examples' true mixes (10 s, exact), separated
in both settings. Their rendered guitar is an exact reference. SNR against it, paired,
band-clustered. **Rule (declared):** the fast setting is used for **both** training and inference
if the paired SNR difference (fast − stored) has an interval that reaches 0 or lies above it.
Otherwise the stored setting is used on exact 10-s clips (11 s on MPS) and the training set is
halved to 10k examples to hold the budget (part C's 10k → 20k step was −0.0069 of E).

### 1d. What is a matched stem worth on real mixes? (111 renders, descriptive)

- **Directions:** every stage F part on one amp (a quota of 7 per amp, `random.Random(20261070)`),
  both halves: 21 groups, 42 directions, all 12 bands.
- **Arms:** D_existing with stem a′ (its first leak draw) and with stem a, rendered once through the
  part's measure DI, judged on the held half (`knob_ceiling.judge`, the part's `judge_lag`), paired
  with the stored D_existing (stem b) and S.
- **Priming and repeat check:** one discarded render at S per group; on 6 groups
  (`random.Random(20261075)`) S is re-rendered and must reproduce the stored judge within **1e-3**
  (|log|), or the run stops.
- **Renders:** 21 × (1 + 4) + 6 = **111** (cap 150).
- **Reported:** a′ − b and a − b, both, on all bands and on the unseen bands, with intervals. **It
  decides nothing.** With a band SD near 0.15 its half-width is about 0.08, and a retrained model
  changes its mix features too, so a ceiling argument from it would not hold. It gives the scale
  of the stem's value for this model (arm A's perfect separation was worth −0.066), and since it
  chooses nothing it adds no selection on stage F.

## Step 2: the pilot (5k examples; stops before the expensive build)

### The data build (shared by the pilot and the full set)

- **The pool (band-clean):** part C's train and early-stopping examples whose band is not a stage F
  band, not a known-answer band (Chris Coltraine, Rebecca Haviland, The Apprehended), not in part
  C's reserve of stage F DIs, Guitar-TECHS P3, sets 4–6 or any held-out session
  ([`dev-test-ledger.json`](dev-test-ledger.json), `validation-datasets.json`'s held-out list).
  **21,311 examples (20,311 train, 1,000 early stopping) from 277 sections in 9 bands** (recounted
  by the review from the stored rows). The code recounts, asserts every exclusion, and prints the
  bands.
- **Separator-training overlap, flagged:** Hollow Ground's "Ill Fate" (MUSDB18 test, 25 sections)
  and The Long Wait (a MUSDB artist, 1 section) are in the pool; their stems may be unrealistically
  clean if a separator trained on them. They stay in training (about 9% of sections) and are
  tagged; readouts never use them.
- **Per example, deterministic from its index:** re-render the guitar (part C's settings and DI
  section, `pretrain_set.plan_example` / `settings_for`, on the bounded render server). The
  re-rendered half mels must match the stored `gA`/`gB` within one 0.5-dB step on 99% of cells, or
  the example is refused and counted (part C's recheck showed its renders reproduce).
- **The true mix:** the render summed in the sample domain with its own section's backing, rebuilt
  from the session's tracks by part C's rule (`pretrain_set.backing_tracks`: the mix list less the
  part's tracks, every DI and the leaking tracks), at one fixed draw per example of part C's level
  (971 measured sections), vocals (p 0.5) and loudness (`mix_params`, epoch 0). Mastered with p 0.5
  (`song_aug.compress`, seeded by index with 20261076) **before** separation, since a product
  song's stem comes from the mastered mix.
- **The stem:** Mega-53 on the exact 10-s mix, in the setting 1c chose. Mono, as at inference.
- **Stored:** the mix mels, then the stem mels, both halves, uint8 on part C's grid (about 38 KB
  each per example), their exact half LUFS (so the conditioning is exact, as at inference), and a
  JSON row. No audio is kept.
- **V_sep, the realistic dev val set:** all of V_dev's 1,720 examples, built the same way, with
  both a Mega-53 and an htdemucs stem. Never trained on, never used for early stopping. Cnoc An
  Tursa's "Bannockburn" is MUSDB18 train (`locator_truth.MUSDB_TRAIN`), so htdemucs trained on it:
  **its examples are left out of every V_sep readout** (the code prints the count).
- **Order, so the cheapest reading comes first:** renders and true mixes for the pilot's examples
  first (no separation), then separation. D0-5k and D_mix-5k can train as soon as the mixes exist.
- **Throughput:** one MPS worker and one 4-thread CPU worker for Mega-53, fed by the render shards
  through a bounded in-memory queue (renders take 1.6 s and are not the bottleneck). The idle-machine
  timings give 0.32 clips/s; sharing 8 cores with renders and htdemucs, **0.25–0.32 clips/s** is
  budgeted. **Memory guard:** Mega-53 peaks at 7.2 GB, so two workers use about 14.4 GB of 32 GB;
  each worker stops cleanly if swap grows (`separator_screen`'s swap guard) or free memory falls
  below 4 GB.

### The pilot arms

*Amendment 1 replaces D_sep with the stem-only D_stem and rewrites rule 2; see below.*

**Training data:** 5k train examples (`random.Random(20261073)`, stratified by band and amp) and the
1,000 early-stopping examples, all built as above. Part C's half-width network
(`pretrain_set.build_net`) and recipe (`train_one`: Adam 1e-3, batch 64, one half per example per
epoch, half A's first second masked, patience 4), at most **40 epochs** (4 of part C's 11 runs had
their best epoch last), 2 seeds each (20261042, 20261043):
- **D0-5k:** part C's composition (leak stem, power-sum mix redrawn every epoch) on the same 5k.
- **D_mix-5k:** the stored true mix; the stem channel always 0 (no separator).
- **D_sep-5k:** the stored Mega-53 stem and true mix, with the declared augmentations (below).
- **D_sep-5k-noaug:** the same without augmentations.

(If gate 1 dropped the separator route, only D0-5k and D_mix-5k run, and no stems are built.)

D0 redraws its mix every epoch, while D_mix and D_sep see one fixed mix per example. That difference
in mix diversity is part of every D − D0 contrast; stated, not separated.

**Augmentations (declared, on the stem mel per example and epoch, `SeedSequence([20261074, i,
epoch])`), aimed at what the user heard in the separation samples:**
- **Drop-outs** (p 0.3): 1–3 segments of 0.2–1.0 s attenuated by U(10, 40) dB.
- **A merged second guitar** (p 0.2): another **training-pool** example's guitar mel (another
  section, the same base class; never early-stopping or V_sep, asserted) added in the power domain
  to **both** channels at U(−12, 0) dB relative to the guitar; the label stays the target's.
- **Darkening** (p 0.3): above a corner at U(3, 8) kHz, attenuated by U(0, 15) dB (Mega-53 reads
  12.3 dB darker above 6 kHz than htdemucs; up to 20 dB on some parts).
- **Separator failure** (p 0.05): stem := mix + U(−6, 0) dB.

### The pilot readouts and rules (declared, applied in order)

*As amended: [amendment 1](#amendment-1-2026-10-20-stem-only-arm-approvals-order) holds the rules in force.*

All readouts: E, seed-averaged, paired per example, 90% band-clustered t intervals over V_sep's 5
bands (4 df, t 2.132), Bannockburn left out. **Power:** part C's paired ΔE had a band SD of about
0.005, so the half-width here is about 0.005; effects smaller than about 0.007 read as ties, and with
4 df the rules can fall to their defaults for lack of power rather than on evidence. Part C's
10k → 20k step (−0.0069) is the scale.

- **R_out, the readout outside the new pipeline:** V_sep's **unmastered** examples with the
  **htdemucs** stem (a separator none of the arms trained on; D_mix ignores the stem).
- **R_in:** all of V_sep with the Mega-53 stem (the product's separator).

1. **STOP** if **neither** D_sep-5k − D0-5k **nor** D_mix-5k − D0-5k on R_out has an interval
   entirely below 0: neither real stems nor true mixes beat the old recipe even on held-out bands.
2. **Mix-only** if D_sep-5k − D_mix-5k on R_in has an interval that contains 0 or lies above it (the
   separated stem adds nothing over the mix, on the product's own separator), and D_mix beat D0 in
   rule 1. The full model is then D_mix: no more separation.
3. **Otherwise build the rest** (15,311 more examples: the remaining train examples) and train
   D_sep. (If rule 1 passed only through D_sep, and D_sep beats D_mix, this is the same branch.)
4. **Augmentation:** kept unless D_sep-5k − D_sep-5k-noaug on R_in has an interval entirely above 0.

## Step 3: the full models (no judged renders)

- **D** (D_stem, or D_mix by rule 2 or gate 1; amendment 1) and **D0** (part C's composition), each on the full
  band-clean pool, 3 seeds (20261042–44), the same recipe, at most 40 epochs.
- **The answer:** the three seeds' **pooled mixture's top component** (each seed's weights / 3, the
  highest-weight component's mean, clipped to [0, 1]); switches by majority; mics by the argmax of
  summed probabilities; S's preset with the labelled dimensions replaced (`knob_ceiling.space`), as
  `direct_existing.ensemble` and `settings_from` do.
- **Guards:** part C's (an epoch skipping more than 5% of steps on non-finite gradients aborts; one
  retry); the early-stopping loss finite at the chosen epoch. Recorded per run: epochs, best epoch,
  time, examples per second, skipped steps, peak memory, masked-frame count.
- **Readouts (zero renders):** R_out, R_in and V_dev for D, D0 and D_existing; each seed against
  the ensemble in knob space.
- **Early stop (declared):** if D's E on R_in is not below a constant predictor's (the training
  label median per amp and base class; paired, band-clustered interval entirely below 0), D has
  learned nothing usable from realistic inputs: stop, no judged renders.

## Step 4: the decision test on stage F (about 320 renders)

Fixed now, before any training.
- **Directions:** stage F's 126 (21 parts, 12 bands, part × amp × search half;
  [arm A with Mega-53](arm-a-mega53-plan.md), amendment 1).
- **Inputs (stored, hash-checked):** the stored full-mix context crop; for D_sep, the Mega-53 stem in
  the setting 1c chose (the fast crop-only stems are made once, 21 separations, and hashed); D0 gets
  the same stem. The search half only; one gain brings the crop's mix to the training median;
  quantised and masked as in training. **Parity test first:** 20 V_sep examples rebuilt through this
  path match their stored features within one 0.5-dB step on 99% of cells, LUFS within 0.01 LU.
- **Arms rendered:** D and D0, once each, through the part's measure DI, judged on the held half
  against `reference.wav` at the part's `judge_lag`, paired with the stored S, H and M (and
  D_existing, XO, YT for reference).
- **Priming:** one discarded render at S per (part, amp) group. **Repeat check:** 6 groups
  (`random.Random(20261077)`) re-render S, within 1e-3 of the stored judge, or stop.
- **Renders:** 63 + 126 × 2 + 6 = **321** (cap 400). A refused answer scores as S.

**The primary contrast: P = D − S,** per direction log(d_D / d_S) on the held half, per part the
mean over amps and halves, band-weighted, **90% band-clustered t interval** (12 bands, 11 df;
`arm_a_levers.effects`, as every stage F arm).
- **Interval entirely below 0:** D lands closer to the record than S on fresh full mixes. **Build
  on it:** a product plan for direct prediction as the settings source in `generate` (and `match`
  without a DI), whose first step re-measures D on new material.
- **Interval contains 0:** not shown at this power. **Stop and revisit with the user**, with D − D0,
  step 1's numbers and the per-class rows. No further D variant without the user.
- **Interval entirely above 0:** D is worse than S. Stop and revisit.

**The fix's own reading (declared, secondary): D − D0** on the same directions. It says whether the
realistic training stems and mixes moved real-mix accuracy, whatever P shows.

**Reported beside them, never promoted:** D − H, D − M, D − D_existing; rows no high bleed
(direction rule), F-song, unseen by part C, without the MUSDB18 songs; per class (clean, crunch)
and amp; leave one band out; part-weighted; bands better and worse. Zero renders: D's answers from
stems c (stored setting) and b (htdemucs) against c_f, per seed.

**Power.** Band SDs of D-type contrasts against S: 0.166 for D_existing on stage F; 0.069 for arm A;
about 0.14 for B2. The 90% half-width on 12 bands is then 0.036–0.086, and the effect found with
80% power about **0.05–0.13** (0.05–0.11 at SDs 0.07–0.14). A gain like B2's (−0.033) would read as a
tie.

**Repeat use, stated.** This is the eighth set of arms on stage F's parts. Nothing about D is chosen
on stage F: the recipe is fixed here; gate 1 reads D_existing's answer movement, not judge scores;
1d decides nothing; the separator setting is chosen on the audit examples; the pilot reads V_sep.

## Budget and early stops

| Step | Judged renders | Training-style renders | Separation (Mega-53 clips) | GPU | Wall-clock |
|---|---|---|---|---|---|
| Code, tests, code review | 0 | 0 | 0 | 0 | about 3 h |
| 1a–1c: movement, mismatch cost, reliance, setting | 0 | 0 | 21 stage F crops + 164 × 2 audit (about 45 min MPS) + 164 htdemucs | 0 | about 2 h |
| 1d: matched stem on stage F | 111 (cap 150) | 0 | 0 | 0 | about 15 min |
| 2: pilot build (5k + 1k early stopping + 1,720 V_sep) | 0 | 7,720 | 7,720 (6.7–8.6 h) + 1,720 htdemucs (about 1.4 h, beside it) | 0 | 7–9 h |
| 2: pilot training (4 arms × 2 seeds, 5k examples, ≤ 40 epochs) | 0 | 0 | 0 | about 2.4 h | about 2.4 h |
| 3: rest of the build (15,311) | 0 | 15,311 | 15,311 (13.3–17 h) | 0 (MPS separates) | 13–17 h |
| 3: D and D0, 3 seeds each (20.3k, ≤ 40 epochs) | 0 | 0 | 0 | about 5–7.4 h | 5–7.4 h |
| 4: the decision test, report, audit | 321 (cap 400) | 0 | 0 (made in 1a) | 0 | about 2 h |
| **Total** | **432 (caps 550)** | **about 23k** | **about 23k: 20–26 h** | **7.5–10 h** | **about 2.5–3 days** |

- **GPU hours:** part C ran at 184 examples a second, and its smaller runs used all their epochs, so
  the full 40 epochs is budgeted: pilot 8 × 5k × 40 / 184 ≈ 2.4 h at most; full 6 × 20.3k × 40 / 184
  ≈ 7.4 h at most, about 5 h if early stopping acts as at 20k in part C.
- **If gate 1 or rule 2 picks the mix-only route,** separation drops to the 1c checks (and the pilot's
  stems, under rule 2), saving about 15–17 h.
- **GPU and MPS share one device:** one job at a time. D0's full training runs after the pilot, while
  separation runs CPU-only (about half the speed); the wall-clock allows for that.
- **Disk: blocked for the full build today.** 32.0–32.5 GB free on 2026-10-19 against the 31 GB
  guard; another session's temp files took it below the guard on the same day. The pilot writes
  about 0.6 GB (7,720 × 76 KB, plus the htdemucs stems for V_sep) and fits. The full set adds about
  1.2 GB, models about 0.1 GB: **the full build needs at least 34 GB free when it starts,** which
  means the user freeing some space (for example old `learn/direc` (45 GB) or `runs` (21 GB) data;
  nothing is deleted without the user). Every writer checks free disk and stops cleanly below 31 GB.
- **Agents:** 1 implementer, 1 code reviewer, 1 results auditor; monitoring by the task-executor
  session.
- **The early stops, cheapest first:** gate 1 (about 2 h, zero renders; drops the separator route);
  pilot rule 1 (7–9 h of build and 2.4 GPU h, no judged renders; ends the plan); pilot rule 2
  (switches to the mix-only model); step 3's constant baseline (GPU spent, no judged renders); then
  the decision.
- **Machine order:** at most 3 render processes machine-wide (`isolate`, the bounded render
  server); long jobs with `setopt no_bg_nice`; one Mega-53 CPU worker and one MPS worker at most;
  torch at 2 threads beside training.

## Data hygiene

- **Never in training, early stopping or V_sep:** stage F's 21 parts and every section of its 12
  bands; the known-answer songs and their 3 bands; part C's reserve of stage F DIs; Guitar-TECHS P3;
  sets 4–6; held-out sessions. Asserted in code, with unit tests for each exclusion.
- **Split by band:** training bands and V_dev/V_sep bands are disjoint (part C's val split; the 9
  training bands share none of stage F's 12, the known-answer bands or the reserve, checked by the
  review); the 1,000 early-stopping examples are whole sections of training bands (part C's split),
  stated.
- **Backings** come only from each training section's own session. The merged-guitar augmentation
  draws only from the training pool.
- **Separator training data:** the MUSDB18 songs are tagged in the pool, V_sep and stage F, and
  readouts are reported without them.
- **A fine-tuned separator ([separation fine-tune plan](separation-finetune-plan.md)):** one
  may exist again (user, 2026-10-20: fine-tuning an existing separator is fine, on this Mac
  only). If it trains on the sessions of D's training or V_dev bands, it gives those sections
  unrealistically clean stems, so **D's training stems and V_sep use the stock Mega-53**, and
  step 4 feeds D the stock Mega-53 stem it was trained with. A later switch to a fine-tuned or
  another released separator, or a DSP split of its stem, is a separator change for D, measured
  as a transfer (zero renders: answer movement on stage F), not assumed.
- **No held-out data is touched.** Nothing in this plan opens a held-out use.

## What is not done

- No arm A work; no search on top of D (a later question if D wins).
- No new DIs; labels stay part C's drawn labels (their mid-range shrinkage risk is inherited).
- No codec augmentation, EQ or reverb (they change the tone the label describes).
- No known-answer renders: their knob error against the truth is reported at zero renders as a
  descriptive row (D, D0, D_existing, S; the 3 bands carry no interval).

## The draft's review findings, and where they went

- **The quantisation confound:** every condition and the inference path use the stored grid; floor
  share reported (1a, step 4's parity test).
- **R against T₀ composition:** replaced by direct measurement: a′ (training composition with the
  real guitar) against real stems on the same parts (1a, 1d), and the audit examples' labelled cost.
- **A non-saturating metric:** log-likelihood and E, no AUC (1a, 1b, pilot).
- **D0 as the premise test:** D0 is the matched control in the pilot and in the decision test.
- **GPU budget:** now 7.5–10 h (8–9 h in the draft's review, recomputed here at 40 epochs).
- **Repeat tolerance 1e-3;** **the ensemble as the pooled mixture's top component;** **stored
  inputs, hash-checked;** **conditioning parity** (1a's two LUFS conventions; exact LUFS in the new
  set).
- **Honesty:** B2 already had realistic separation and tied; the mix-realism part is capped near 7%
  of E in-domain; the flat curve may be an identifiability floor (all in "The question").

## Amendment 1 (2026-10-20): stem-only arm, approvals, order

**Why.** Gate 1 read `GATE1 STEM`: behind a clean or real separated stem the mix adds little or
nothing (the stem carries 0.70 of the reliance; these reliance rows were read after the gate,
descriptively). The user then decided that the model should be trained on the separated target
stem, not handed the whole mix, with a mix version only as a small comparison. The reasoning that a
two-channel model would lean on the mix to do separation it cannot do well is an inference, not a
measurement. **What dropping D_sep gives up:** gate 1's caveat that a model trained on real stems
might use the mix behind drop-outs is no longer measured.

**The pilot arms (replaces "The pilot arms" list; recipe, seeds, epochs and data unchanged):**
- **D0-5k:** part C's composition, unchanged (the matched control).
- **D_mix-5k:** the stored true mix; the stem channel always 0. The small comparison.
- **D_stem-5k:** the stored Mega-53 stem with the declared augmentations; **the mix channel always
  0**, in training and at inference.
- **D_stem-5k-noaug:** the same without augmentations.

Still 4 arms × 2 seeds, about 2.4 GPU h at most. D_sep (stem plus mix) is dropped, not run.

**Zeroing (exact, for D_mix's stem and D_stem's mix):** the channel is set to 0 in the normalised
input (`song_model.norm_feat`, so −60 dB), after the half-A mask, as 1a's z condition did; its
LUFS conditioning slot is set to 0 in the normalised conditioning vector (`cond_vec`), the same
constant in training and at inference. The other channel's mel and LUFS are as stored.

**D_stem's augmentations, in this order, on the stem only:**
1. separator failure (p 0.05): stem := the stored true-mix mel + U(−6, 0) dB, and its LUFS := the
   stored mix LUFS + the same offset (the mix is still built and stored, for D_mix and this);
2. the merged second guitar (stem only; the mix channel stays 0);
3. drop-outs;
4. darkening.
Steps 2–4 do not update the LUFS conditioning (a stated approximation: the merge can raise the
true level by up to 3 dB; drop-outs and darkening lower it).

**Inference level:** as in training, where each stem is separated from a mix brought to its drawn
loudness, one gain brings the crop's mix to the training median and the stem gets the same gain.
The stem's level then carries the guitar-to-mix ratio, which is available at inference.

**Caveats:** D_stem − D0 changes three things at once (no mix channel, real stems, true mixes),
beside the mix-diversity difference already stated. R_out's htdemucs stem is further outside
D_stem's training than D0's, which can fall back on the mix; a fair test, stated.

**The rules (replace D_sep by D_stem; otherwise as declared):**
1. **STOP** if neither D_stem-5k − D0-5k nor D_mix-5k − D0-5k on R_out has an interval entirely
   below 0.
2. **Mix-only** only if D_mix-5k − D_stem-5k on R_in has an interval entirely below 0 (D_mix
   clearly better) and D_mix beat D0 in rule 1. A tie keeps D_stem, the user's chosen route.
3. **Otherwise build the rest** and train D_stem (step 3's D is D_stem).
4. **Augmentation** kept unless D_stem-5k − D_stem-5k-noaug on R_in has an interval entirely above 0.

Step 4 feeds D_stem the Mega-53 stem only. D0 keeps both channels.

**Order.**
1. 1c (the separator setting) runs first. It reuses gate 1's Mega-53 fast audit stems (hash-checked;
   the CPU matched MPS to 81 dB) and adds the stored setting on the 164 audit mixes, about 30 min on
   MPS. Separation only, no training, no renders.
2. Then the pilot build.
3. Then the pilot training.

1d stays optional and is not run.

**Approvals (user, 2026-10-20).**
- **Training time:** the pilot's training, about 2.4 h, is approved. Step 3's D and D0 runs, 5–7.4 h,
  each need a new yes.
- **Disk:** for the pilot build only, writers stop cleanly below **26 GB** free (the user approved
  25 GB; 1 GB is margin), and the override is logged. The full build still needs at least 34 GB
  free and the 31 GB guard.

**Names elsewhere in this plan:** D_sep reads D_stem, `Dsep`/`Dsep-noaug` read `Dstem`/`Dstem-noaug`,
and `PILOT STEM` reads `PILOT STEM`. In step 4, D_stem gets the Mega-53 stem only (mix channel 0); D0
gets the same stem and the mix.

## Code (after review, before any compute)

`learn/direct_stems.py`: `move` (1a and the audit cost; prints `GATE1 STEM` or `GATE1 MIX-ONLY`),
`reliance` (1b), `sepcheck` (1c, prints the chosen setting), `matched --shard i/n` and
`matched-report` (1d), `build --part pilot|rest|vsep --stage mix|stem` (renders, mixes, separates,
stores; disk and memory guards), `train --arm D0|Dmix|Dstem|Dstem-noaug --n 5000|full --seed s`,
`pilot-report` (prints `PILOT STOP`, `PILOT MIX` or `PILOT STEM`), `readout` (`MODEL STOP` or
`MODEL OK`), `predict`, `render --shard i/n`, `report`. Tests: every exclusion and tag; the a′
construction against a numeric mix; the conditioning and quantisation parity; each augmentation on
synthetic mels and its training-pool-only draw; gate 1 and the pilot rules on toy tables; the
ensemble rule; render counts, caps and priming once per group.

## Independent review (2026-10-19)

One fresh-context skeptical reviewer. **Verdict: go, with required changes, all applied.** It
recounted the pool from the stored rows (21,311 examples, 277 sections, 9 bands, disjoint from stage
F, the known-answer bands and the reserve), V_dev (5 bands, 1,720 examples) and the 164 audit
examples, and confirmed the cited figures, render counts and power arithmetic. Changes:
1. Gate 1 no longer ends the plan: if the stem doesn't matter it switches to the mix-only route.
2. Gate 1 reads per-seed movement against a declared null (two leak draws), not the ensemble answer
   against the seed spread (the ensemble takes one seed's top component, so it flips).
3. 1d (the matched stem on stage F) is descriptive: a retrained model changes its mix features too,
   so its "ceiling" reading did not hold, and a stage F reading should not decide step 4.
4. Pilot rule 1 reads outside the new pipeline (unmastered V_sep with htdemucs stems) and stops only
   if neither D_sep nor D_mix beats D0.
5. Pilot power stated (5 bands, 4 df); V_sep uses all 1,720 V_dev examples.
6. Pilot build counts the 1,000 early-stopping examples (7,720 separations); the rest is 15,311.
7. MUSDB18 overlap tagged (Ill Fate, The Long Wait in training; Bannockburn left out of V_sep
   readouts; stage F's MUSDB songs reported apart).
8. Every stage F row also on the 6 bands unseen by part C.
9. The separator setting is chosen on the 164 non-stage-F audit examples, not on stage F.
10. GPU budget 7.5–10 h at 40 epochs.
11. Separation throughput as an interval (0.25–0.32 clips/s, 20–26 h) with a memory guard.
12. The unity-sum check cited as 1.5e-7.
Optional suggestions taken: the audit examples' labelled cost feeds gate 1; renders and mixes before
separation; three a′ draws; both a′ − b and a − b reported; z's LUFS declared; the merged guitar
from the training pool only; the mix-diversity difference stated.
