> Input report for `docs/research-audio-ml.md` (round 4), kept as written. Where the synthesis corrects a claim here after a source check (its §8), the synthesis holds.

# C. Models, training and search for amp settings from audio

Research round C, 2026-10-05. It adds to the three earlier research docs
(`research-song-only-matching.md`, `research-full-plugin-estimation.md`,
`research-supervised-preset-model.md`) and does not repeat their sources unless something new
was read in them. Tags: **[V]** = I opened the source and the claim is in it; **[U]** = search
snippet or background knowledge, not checked; **[repo]** = this repository's docs;
**[calc]** = my arithmetic.

## Bottom line

1. No published work tests settings estimation on **real** recordings with known answers.
   Every positive result I read was in-domain or used synthetic targets. Our K3 on real amp
   tracks is already harder than anything published.
2. Our failures come from **identifiability and the objective**, not from the optimiser or the
   network. Without a DI, searching harder ended **further** from the recording (§5). Better
   optimisers, surrogates or decoders would make that worse.
3. Treat the amp as the user asks:
   - one shared encoder, factored as p(amp | x) · p(settings | amp, x);
   - continuous settings in a shared, amp-agnostic space where possible;
   - **set-valued** amp labels, since several amps can reach a recording;
   - in search, the amp is a bandit arm with successive halving, not a separate flow.
4. The PR12 symptoms each have a zero-render fix to try first (§7):
   - one preset acting as a hub: hub correction;
   - render-trained recognisers losing on real tracks: real-domain feature standardisation;
   - open-set failure: coarser labels that can actually be told apart.
5. Not worth building: gradients through the plugin, surrogate inversion, GAN or diffusion
   blind estimation, and autoregressive or flow decoders.

## 1. Sound matching and effect estimation: what worked, and why

- **Topology is the hard part, and papers dodge it by splitting.**
  - Sound2Synth fixed DX7's 32-way "Algorithm" and the note (C4). It suggested one model per
    Algorithm, keeping the output with the smallest audio loss.
  - In-domain MFCC distance: 5.36, against hill climber 21.96, GA 31.32 and PresetGen VAE
    14.70 [V] ([PDF](https://arxiv.org/pdf/2205.03043)).
  - That is the split-per-amp design the user rejects. Its selection step needs an audio loss
    that works, which we only have with a DI.
- **Plain search held its own against networks.** On Dexed:
  - A hill climber had the second-lowest total error and was more consistent than the best
    network.
  - Both made "close" matches in about 25% of cases.
  - The GA did worst, on a small budget [V]
    ([Yee-King et al. 2018](https://research.gold.ac.uk/22516/1/myk_lf_vsti_programming.pdf)).
- **Audio losses alone fail.**
  - DiffMoog's spectral loss used alone "failed systematically", and FM chains never converged.
  - Training parameters first, then spectral loss, then fine-tuning on NSynth helped out of
    domain [V] ([DiffMoog](https://arxiv.org/html/2401.12570v1)).
  - The best loss depends on the synthesiser [V] ([2506.22628](https://arxiv.org/abs/2506.22628)).
    So the judge's validation on clean PR12 does not cover SW50R high gain or comparisons
    across amps.
- **Out of domain, search in a learned embedding beat amortised prediction.** Synth-JEPA
  (JADE, then Adam refinement) scored MSS 10.25 on NSynth, against 16.67 for flow matching [V]
  ([Synth-JEPA](https://arxiv.org/html/2609.31024)).
- **Hybrids beat prediction alone, but only with a dry signal.**
  - A DNN predicting the effect types and the dry signal, followed by CMA-ES, reached 23.07 dB
    SI-SDR against 18.18 dB for prediction alone [V]
    ([Okita & Katayose](https://arxiv.org/html/2604.22276)).
  - The data were synthetic (Pedalboard). The search works because a dry signal exists: our
    DI case.
- **Structured decoders are brittle even in-domain.**
  - The audio-processing-graph estimator decodes the topology autoregressively, then the
    parameters. Node error was 21.5% on singing and 33.5% on drums from seen sources, 24.2% and
    44.6% from unseen ones, all synthetic [V]
    ([Lee et al. 2023](https://ar5iv.labs.arxiv.org/html/2303.08610)).
  - Serum effect programming (an RNN picks the next effect, a CNN per effect sets it) reported
    no quantitative out-of-domain test [V]
    ([Mitcheltree & Koike](https://arxiv.org/html/2102.03170)).
- **Black-box compressor estimation**: BO took 80 evaluations (2–3 min per 30-s excerpt);
  pattern search took about 300 (7–9 min). Synthetic only; the authors note that different
  settings can sound alike [V] ([2607.19645](https://arxiv.org/html/2607.19645)).

## 2. Gradients through the plugin, and differentiable surrogates

- **SPSA through a black-box plugin (DeepAFx) is out of reach.**
  - It needs 3M plugin instances for a batch of M (M = 100) and 1,000 steps per epoch.
    Training took 60–202 epochs and 5–20 h on a V100 plus CPUs.
  - Its tube-amp emulation rated below a specialised model, and discrete parameters are an open
    problem [V] ([DeepAFx](https://arxiv.org/pdf/2105.04752)).
  - For us that is about 18M renders, roughly 70 days, and a dead licence daemon [calc].
- **Neural proxies were DeepAFx-ST's weak point.** They "were unable to achieve performance on
  par", blamed on proxy inaccuracy "especially for the parametric equalizer" [V]
  ([DeepAFx-ST](https://arxiv.org/html/2207.08759)).
- **Amp models conditioned on knobs** are cheap to train, but each covers a few controls and
  none has been inverted to recover settings.

  | Model | Controls | Data | Result | Source |
  |---|---|---|---|---|
  | LSTM-32 (Juvela et al.) | 5 knobs | 4.5 h of reamps | not significantly different from a SPICE simulation | [V] [link](https://arxiv.org/html/2403.08559) |
  | PANAMA | 6 knobs | 75 settings × ~3 min | MUSHRA level with NAM | [V] [link](https://arxiv.org/html/2509.26564v1) |
  | NAM parametric pedal | 2 knobs + 2 switches | ~1 h | error < 0.004 on unseen settings | [V] [link](https://www.neuralampmodeler.com/post/the-first-publicly-available-parametric-neural-amp-model) |
  | DDSP amp (~10k parameters) | 5 knobs | — | about twice the black-box's error | [V] [link](https://arxiv.org/html/2408.11405) |

  On a Marshall JVM with unseen control settings, S4 models were best and parametric gray-box
  models were substantially worse [V] ([2502.14405](https://ar5iv.labs.arxiv.org/html/2502.14405)).
- **Verdict on surrogates.**
  - Training data would be cheap to render [calc].
  - A Morgan chain has 10–15 effective controls plus switches, against 2–6 above.
  - A surrogate only speeds up optimisation, which is not what fails: the same-DI search or
    inversion already beats neutral on 41–43 of 43 parts [repo]. Not now.
- **Blind estimation without paired data needs more than we have.**
  - A GAN learned an amp tone from unpaired recordings, 30–40 min per guitar.
    - Single-guitar listening scores: supervised 81, 93 and 57 (clean, light, heavy); at least
      one unpaired model reached 80 or more in each condition.
    - It costs one model per target and 4–10 GPU-hours [V]
      ([Wright et al.](https://ar5iv.labs.arxiv.org/html/2211.00943)).
  - A clean-guitar diffusion prior estimated distortion from 18 s of wet audio [V]
    ([Moliner et al.](https://arxiv.org/html/2504.04751)).
    - Its targets were synthetic plugin distortion, and the prior took an H200 to train.
  - Distribution-level objectives can ignore content, but not with 10–30 s of stem and a
    black-box plugin.

## 3. The amp as a categorical feature

Our structure is a "parameterized action space": discrete choices, each with its own
continuous parameters [V] ([Hausknecht & Stone](https://arxiv.org/abs/1511.04143)). It is also
"categorical and category-specific continuous inputs" [V]
([Nguyen et al. 2020](https://ojs.aaai.org/index.php/AAAI/article/view/5971)).

- **One encoder, factored heads.** Keep the plan's topology softmax (amp × pedals ×
  compressor, `supervised-model-plan.md` §2). Under it:
  - **shared semantic heads** that mean the same on every amp: effective drive, the tail-curve
    EQ, bright and presence tilt;
  - **amp-specific residual heads**, masked when their amp is off.

  Shared heads let scarce real data inform every amp. They keep one continuous distribution
  alive across an amp switch, which is what "don't split flows" needs.
- **Set-valued amp labels.**
  - If two or three amps reach a part within the judge's cut, "the amp" is not identifiable.
  - Train with a partial-label loss: mass on the acceptable set [U]
    ([Cour et al. 2011](http://jmlr.org/beta/papers/v12/)).
  - Score "in the set", not top-1.
- **Not needed:**
  - **Gumbel-softmax** [U] ([1611.01144](https://arxiv.org/abs/1611.01144)). It passes
    gradients through a categorical sample. With known labels, cross-entropy is right; it
    matters only for audio-loss training through a proxy (ruled out, §2).
  - **Set or graph decoders.** Our chain has a fixed order and about 20 valid combinations.
  - **Autoregressive decoders.** They err on topology even in-domain (§1).
- **Flows or mixture densities** [U] ([Bishop](https://publications.aston.ac.uk/373/)):
  - Point regression degrades under parameter symmetries [V]
    ([Hayes et al.](https://arxiv.org/abs/2506.07199)).
  - Sorting the mic slots removes our main symmetry. Keep the plan's best-of-8 test as the gate.
- **Regret in two parts, against the joint-menu oracle:**
  - amp-choice regret: d(best preset of the chosen amp) − d(best overall);
  - within-amp regret: d(prediction) − d(best preset of the chosen amp).

  This shows which part fails, with no new renders.

## 4. Renders to real recordings, and the open set

Our symptoms [repo]:
- PR12's LDA recognisers pick "Out of this World Clean" on 16–17 of 30 parts.
- On SW50R, the recogniser best on renders was worst on real tracks.
- PR12's open-set regret (3.62–3.68 dB) is worse than the medoid preset's (3.38).

Remedies matched to them:
- **Hubs.** A few points become nearest neighbours of many queries in high dimensions [U]
  ([Radovanović et al.](https://jmlr.org/papers/v11/radovanovic10a.html)).
  - CSLS subtracts each candidate's mean neighbourhood similarity. It lifted one cross-lingual
    retrieval result from 69.8% to 75.7% [V]
    ([Conneau et al.](https://ar5iv.labs.arxiv.org/html/1710.04087)).
  - It costs nothing to try.
- **Test-time normalisation.** Tent re-estimates normalisation statistics on test data [V]
  ([Tent](https://arxiv.org/abs/2006.10726)).
  - The numpy version: standardise real-track features with other bands' real tracks, not
    with the renders.
- **Domain randomisation** transferred with no real training images (1.5 cm error) [V]
  ([Tobin et al.](https://arxiv.org/abs/1703.06907)).
  - For us: randomise mic, room and cab colouring beyond the plugin's range.
  - Never randomise what the model must estimate.
- **Calibrating to real data needs real labels.**
  - RoPE needs "a small real-world calibration set of ground-truth parameter measurements" [V]
    ([Wehenkel et al.](https://arxiv.org/abs/2405.08719)). We have only oracle menu picks.
  - Self-consistency losses on unlabelled real data are a later option [V]
    ([2501.13483](https://arxiv.org/abs/2501.13483)).
- **Open-set ability tracks closed-set accuracy** [V]
  ([Vaze et al.](https://arxiv.org/abs/2110.06207)).
  - PR12's closed-set top-1 was 21–44% against 14% chance [repo], so the open-set failure was
    predictable.
  - Remedy: predict continuous quantities, or merge presets that cannot be told apart.
- **If an encoder is trained** [V] ([2608.28127](https://arxiv.org/html/2608.28127)):
  - unseen sources cost most (retrieval 83.2% → 61.1%, against 81.7% for unseen processors);
  - use hard negatives: the same source, processed differently.

## 5. Search with the black box

- **Mixed-space optimisers.**
  - **CatCMA with margin**: one joint Gaussian × categorical search distribution. At 2,000
    evaluations it mostly beat TPE, SMAC3 and CASMOPOLITAN. It has no conditional variables [V]
    ([2504.07884](https://arxiv.org/html/2504.07884)).
  - **CoCaBO**: an EXP3 bandit for categoricals, a GP for continuous inputs [V]
    ([1906.08878](https://arxiv.org/abs/1906.08878)).
  - **Bandit-BO**: each category is an arm with its own continuous optimum [V] (§3 link).
  - **SMAC**: a random-forest surrogate [V] ([SMAC3](https://github.com/automl/SMAC3)); its
    conditional hierarchies are [U].
  - **Hyperband and BOHB**: adaptive budgets by successive halving [V]
    ([Hyperband](https://arxiv.org/abs/1603.06560), [BOHB](https://arxiv.org/abs/1807.01774)).
- **For us:**
  - The amp is the arm, and the shared semantic dimensions carry across arms.
  - Fidelity runs from one half-crop through one DI up to three crops through three DIs.
  - ST-ITO's ~1,600 evaluations fit a match, but its authors say it "does not work well for …
    guitar tone matching" [V] ([ST-ITO](https://arxiv.org/html/2410.21233)).
- **More search moved song-only answers further away.** In the no-DI runs (void as verdicts,
  descriptive only), the 300-render search ended further from the recording than the one-step
  calculation [repo, `no-di-rule-under-the-judge-results.md`]:
  - default bands: 6 of 8 amp × probe pairs, 1 tie, 1 closer; union bands: 7 of 8, 1 tie;
  - for example, SW50R noise +0.48 against +0.35, SW50R library +0.17 against +0.10, Tone
    King noise +0.56 against +0.30;
  - the exception: AC20 library, +0.08 against +0.10.

  An optimiser exploits a misaligned loss harder. For song-only matching the choice of
  optimiser is second-order. Budget allocation across amps matters in the DI case.

## 6. Small real data, uncertainty, evaluation

- **Conformal sets: reporting only.**
  - Split-conformal coverage is Beta-distributed given the calibration set.
  - ±0.1 coverage (δ = 0.1) needs 22 exchangeable points; ±0.05 needs 102 [V]
    ([Angelopoulos & Bates](https://arxiv.org/pdf/2107.07511)).
  - Our exchangeable unit is the band: 13 bands, about 8 chains.
  - Shifted songs need likelihood-ratio weights [V]
    ([Tibshirani et al.](https://arxiv.org/abs/1904.06019)).
  - So abstain on checking-render margins and report risk–coverage curves. Per-amp guarantees
    are out of reach.
- **Leakage changes which method wins.**
  - An artist filter took one collection from 71% to 27%.
  - It also erased song-level models' apparent advantage [V]
    ([Flexer 2007](https://ismir2007.ismir.net/proceedings/ISMIR2007_p341_flexer.pdf)).
  - That mirrors our LDA reversal. Select only on leave-band-out real tracks, with Telefunken
    as one cluster.

## 7. Cheap experiments, in order

1. **Distinguishability map** (zero renders, minutes).
   - For every preset pair in each existing panel, compute the judge distance through the same
     DI half.
   - Merge presets below the 0.150 cut on most parts; repeat in the recognisers' feature space,
     comparing the spread between presets with the spread across DIs.
   - *Decides:* how many classes each menu really holds. If the 21 clean PR12 presets collapse
     to 3–5, K3 failed on identifiability, and labels shrink to those classes.
2. **Hub and shift fixes on K3** (zero renders, declared first).
   - Re-score 1-NN and LDA with CSLS, with standardisation fitted on other bands' real tracks,
     and with a per-preset bias fitted leave-band-out.
   - *Pass:* the top pick's share is below 25% and the band-median gain against template+R
     rises at least 5 points on both band sets.
   - *Fail:* the gap is not a simple shift; stop recognisers on near-identical menus.
3. **Set-valued amp labels** (zero renders, after amp-reach).
   - Per part, list the amps whose best preset on half B is within 0.150 of the best overall.
   - Re-run K3 on the joint menu with the two-part regret.
   - *Decides:* whether to train an amp head (mostly one amp per part) or show a multi-amp
     shortlist (mostly 2–3 amps).
4. **Optimisation against misalignment** (about 120 renders per amp).
   - Render checkpoints of library searches (iterations 0, 10, 25, 50, 100 and 300) for 20
     parts, through each part's own DI, and score them with the judge.
   - *Decides:* if the distance rises from iteration 0, song-only search becomes shrinkage
     toward the start plus early stopping, and no optimiser upgrade is worth building.
5. **Successive halving across amps, DI case** (about 20 parts × 330 renders, 1–2 h; AC20's
   history caveat applies).
   - Rank all 108 presets on half A from the panels.
   - Run 60-render CMA-ES from the top three across amps, then give the rest of the budget to
     the winner.
   - Compare with today's single-amp search at equal renders on half B. This tests "don't
     split flows per amp" where the objective works.

## 8. Candidly

**Unlikely to work, given our measurements:**
- training through the plugin (months of renders; proxies fail on EQ);
- surrogate inversion for song-only matching (it speeds up a search whose objective is wrong);
- GAN or diffusion blind estimation (minutes of target audio and GPU-hours per target);
- more renders or bigger networks for menus like clean PR12, if experiment 1 finds few
  separable classes;
- flows, mixture densities or autoregressive decoders before multi-modality is shown, and
  per-amp conformal guarantees.

**What plausibly works:**
- with a DI: a joint-amp search with successive halving;
- song-only: coarse, identifiable choices (amp where reach differs, drive class, brightness),
  shown as a shortlist that can fall back to the starting preset.
