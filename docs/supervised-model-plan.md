# Supervised settings model: the plan

A model that reads a song's guitar part and proposes a Neural DSP preset — amp or
channel, pedals on/off, mic family, drive, tone and EQ — trained on (settings,
plugin render) pairs we generate by hosting the plugin. This plan turns
`docs/research-supervised-preset-model.md` into stages with gates, and corrects it
where four research passes (data and simulation; features and architecture;
training, validation and statistics; deployment and sharing — 2026-10-03) found it
wrong. It is committed before any of its renders or training runs, and each
stage's analysis plan is committed in its own merged commit before that stage's
results are read.

## 0. First: a local proof of concept, starting with two kill tests

Decided 2026-10-03, revised the same day after an independent review (verdict:
"rethink"). Before any sharing, runtime or new-data work, find out locally whether
the approach can work at all, using every DI already on disk (never published). The
review's point is that two cheap tests decide that before any model is built: is
there room to beat the bar, and can settings be told apart across players? Both run
on one crossed set of renders.

**The bar, made fair.** The shipped Morgan templates have delay (mix 0.22), rack
reverb (0.3), the compressor and the gate on, while the development references are
dry amp tracks; a model whose time effects are "set by rule" could win by switching
them off without reading the song. So every arm — the template included — gets the
same rule set R: delay, rack reverb, tremolo and doubler off, spring reverb 0, gate
off, output gain as the preset has it. The bar is the template with R
("template+R"). Effective drive is converted back to `inputGain` at the assumed
level (−22.9 LUFS), never at the part's own DI level, which a user's song does not
reveal.

**Renders (SW50R).** Every SW50R factory preset (44) and the template, each with R,
through each of the 43 development parts' own DI crop: about 2,000 renders in a
reused process with a discarded warm-up, scored on two halves of each crop (1.0–5.5 s
and 5.5–10 s). Level is left out; both distances are used: v3c (the audit's
corrected `unpaired-v3`) and ALM (an aligned log-mel distance, §5.3).

(Since PR #109 retired v3c as a judge, K1 and K3 decide under ALM and
`analysis/aligned.py`; see `docs/kill-test-k3-plan.md`, "Under the judge".)

**K1, headroom.** Per part, choose the preset that is closest on half A and score it
on half B (a split-half oracle over the presets); compare it with template+R on half
B. Also score the best constant preset chosen leave-one-band-out (the preset with
the best median on the other bands' parts) — a cheap product improvement if it wins.
**Stop** if the oracle's band-median log ratio against template+R is not ≤ log 0.75
on both distances: if even picking the best of 44 real presets with the answer in
hand does not gain 25%, an estimator that has to guess will not reach the 15% the
gates need.

**K2, identifiability across players.** From the same renders, features of each
render (the long-term log-mel and the lean fingerprint of §4.2) labelled by
preset; train on the renders through the DIs of the training bands and predict the
preset from a held-out band's render (4 folds of 3–4 bands), with nearest neighbour,
LDA and NCA in numpy/scikit-learn. Score top-1/top-5 accuracy against chance (1/44)
and the regret — the distance between the predicted preset's render and the true
preset's render through the held-out DI, both already rendered — against a
constant guess (the best LOBO constant). **Stop** if no row reaches ≥3× chance
top-1 accuracy and ≤0.75× the constant guess's median distance: settings that
cannot be told apart across players with the answer's own presets as the menu will
not be estimated from a song.

**If both pass, the model POC** (§6's stages 1–2, cut down): SW50R, all development
DIs of set 2 (not the "Keys GTR" DIs; one of Zeno ElecGtr8/9; nothing from set 1 or
the held-out sessions), about 2,000 settings × 12 players crossed, rendered through
the plugin with R (EQ in the render; no factorisation, tail calibration or
sensitivity ladders yet). Re-costed: about 2–3 h of renders (the review measured
roughly 3× the earlier estimate per 8-s clip) and ~25k licence-daemon ports. Models:
the ladder's rungs 0–3 plus numpy LDA/NCA at rung 1; rungs and hyperparameters
chosen on simulation only, never on the real parts; TC-1M only; 1–2 seeds.

- **P1, simulation.** On new players × new settings drawn from factory and
  hand-made presets (not the coverage sampler), the distance between the
  prediction's render and the truth's render through the held-out DI: the CNN's
  must be lower than nearest neighbour's and than the best constant's, judged on
  the difference in log distance with a confidence interval over folds.
- **P2, real amp tracks.** For each development part, the preset predicted from its
  amp track by the fold model that never saw its band, rendered through the part's
  own DI, against template+R, the best LOBO constant and a shuffled-input control
  (the model fed another part's audio), level left out, under v3c and ALM. The
  model must beat all three on a majority of parts under both distances, with a
  one-sided band-level p < 0.05 and a band-median gain of at least 8% (13 bands
  detect a true gain reliably only at about 22%, §1). Also rendered through another
  band's DI, since the user's guitar is not the recording's.
- **P3, listening.** 16 blind R-A-B trials, model against template+R, on P2 parts
  chosen by a seeded rule fixed before P2 is read; the model must be picked on ≥10
  of the decided trials.
- **P4, stems** after P2 only: the same as P2 from htdemucs_6s stems of the
  instrumental mix.

A failed kill test or P1/P2 ends the work with a write-up. The deliverable of a
passing POC is local-only until Neural DSP's EULA is known (§7).

## 1. The bar, and what the evidence allows

- **The bar is the starting preset as it is.** Without a DI no search or
  calculation has beaten it on any amp (`docs/tone-matching-plan.md`, "The
  real-guitar probe, from neutral settings and from the shipped presets"). The
  product keeps it today; a model ships only if it beats it.
- **13 development bands cannot resolve a 10% gain.** With the variance measured
  in the library-arm analyses (band SD of the effect 0.10–0.24, within-band SD
  0.22–0.42), the band-level test detects a true 10% gain with 26–47% power and a
  15–23% gain with 80%. A 10% gain at 80% power needs about 40–65 bands. So the
  development gate is 15%, the 19 held-out parts (8 bands) check direction and
  non-inferiority only, and a real claim needs a new evaluation set ("set 3",
  §8).
- **The 43 development parts are a validation set now.** Every probe, start
  choice and audit decision was made on them. They tune and gate; they do not
  confirm.
- **A 10% gain is about 0.1 in `unpaired-v3` units**, where the audit found v3 and
  an independent aligned log-mel distance agree only at chance (|Δv3| < 0.25). No
  model can be selected or judged until a distance is shown to track the user's
  ears (stage 0b).
- **It has been done commercially, without published evidence.** Positive Grid's
  BIAS X "Music-to-Tone" (2025) builds a full preset from a song or stem after the
  user gives a timestamp, returns four options, and works best on isolated stems
  (reviews); its method and accuracy are undisclosed. Fractal's Tone Match fits a
  linear response only. No paper estimates a commercial amp-sim's full settings from
  mixes or separated stems.
- **Players, not renders, bind.** Unseen source audio costs more than unseen
  processors in every published comparison found (retrieval 83 → 61 for unseen
  sources against 83 → 82 for unseen plugins, arXiv 2608.28127); drive classes
  collapse when input level shifts (Guo & McFee, DAFx 2023). Local material has
  about 8 recording chains in 13 bands; shareable material about 10–11 players.

## 2. What the model predicts

Identifiable quantities, not 128 raw knobs (round 2, `docs/research-full-plugin-estimation.md`):

- **Topology** (one joint softmax): amp or channel × drive pedals on/off × compressor
  on/off; voicing switches as binary heads; mic family as a sorted pair of
  {dynamic, condenser, ribbon}.
- **Effective drive**: `inputGain` plus the DI's level offset from −22.9 LUFS, so a
  player's level becomes an exact label transform (subject to the level-fold check,
  stage 0c). Turning it back into `inputGain` needs an assumed user level (round 2,
  decision 2).
- **Amp and pedal knobs** in binned heads conditioned on the topology and masked by
  `match/space.py`'s gates.
- **The linear tail as a curve**: a 30-band third-octave response (EQ, filters, cab
  mics and position, room) relative to a canonical tail, plus the mic family. Round
  2's deterministic solver maps it to knobs — EQ, mic and position are
  many-to-one, and predicting knobs would learn the sampler's tie-break.
- **Set by rule, outside the model**: output level, pans, phase, stereo, doubler,
  transpose, gate, room mic type, time effects (tremolo, delay, rack and spring
  reverb), Tone King wah.

## 3. Training data

### 3.1 Factorise the plugin, if a null test passes (gate F0)

Render only the nonlinear core (pedals, compressor, amp, input gain, voicing)
through the plugin; apply the linear tail offline from measured responses. Morgan's
EQ basis rows agree across the three amps within 0.023 dB/dB
(`packs/morgan/eq_basis.json`) but were measured at low level. Neither manual
states where the EQ sits: Morgan's lists the cab before the EQ, Tone King's the EQ
before the cab. If the EQ, cab and room are all linear, the order does not matter,
which is what this gate tests.

- **Test** (about 60 fresh renders, 3 DIs × clean/edge/high gain, SW50R, AC20, Tone
  King rhythm): an EQ band at ±9 dB rendered against flat-EQ-then-offline-filter;
  cab on against cab-off convolved with each mic's measured IR; a random tail end to
  end. **Pass:** residual within the repeat floor (≤0.25 dB per third octave,
  63 Hz–12.5 kHz) and log-mel distance ≤0.1× the median between settings.
- **If it passes:** measure once per plugin version the EQ grid (~300 renders), cab
  IRs per mic × position × distance (~660 Morgan, ~1,000 Tone King) and room IRs;
  render the training set with EQ and cab off. The render space falls from about
  40–60 to 10–20 dimensions per amp and the tail's labels become exact.
- **If only the EQ fails:** keep the EQ in the render; the cab split, being an IR,
  very likely holds.

### 3.2 Settings sampling

- **Strata** (amp/channel × pedals × voicing switches) with explicit counts:
  p ∝ 0.5·uniform(valid) + 0.5·factory^0.5, and at least 2% per stratum, so
  combinations no factory preset uses (AC20 with the second drive) exist.
- **Knobs in perceptual units**: warp each by its sensitivity curve (a ladder of
  11 steps × 8 bases × 3 DIs, ~264 renders per knob), sample 75% warped and 25%
  uniform; frequencies log-uniform; scrambled Sobol per stratum in power-of-two
  sizes (`random_base2`; Latin hypercube under 64 points). Uniform random beats grids (Comunità et al. 2021: grids bias
  estimates toward grid values).
- **Proposal mixture, with its density recorded per sample**: 50% coverage, 30%
  factory presets jittered (N(0, 0.05) in warped units, switches flipped at
  p = 0.1), 20% factory marginals. Recording q(θ) lets the training prior be chosen
  by importance weights and measured, not baked in. A training set drawn without
  presets transfers badly to hand-made settings (Combes et al., JAES 2025: Dexed
  ranking 0.87 → 0.12), so the factory presets are also a held-out test panel.
- **Canonicalise**: dormant controls at template values; Tone King values on the
  plugin grid. **Bound** label-transparent regions (compressor Mix ≥ 0.15, drive
  ≥ 0.05 when on). **Reject** non-finite renders, zero runs >20 ms where the DI
  plays (renderer failure: quarantine), kept windows under −60 LUFS. **Keep**
  near-duplicate sounds from different settings: they are the many-to-one structure.
- **Linear tail sampled on the fly** (if F0 passes): EQ spike-and-slab (P(0) = 0.4,
  else Laplace 3 dB clipped to ±12 dB, measured on the factory presets), filters
  mostly open, mic pairs half factory frequency and half uniform.

### 3.3 DI material

- **Windows**: a catalog of 6-s windows with ≥70% active frames, each with its own
  preceding 2 s as pre-roll; per settings, 2 players × 4 consecutive windows (for
  pooling and for a same-settings/different-player consistency term).
- **Level**: draw the effective input level over −36 to −8 LUFS and set
  `inputGain = target − DI_LUFS` (development DIs span −39.5 to −10.7 LUFS, median
  −23.7).
- **Pickup**: the natural spread between DIs is already 6–10 dB per band, so
  augment modestly: a relative resonant filter moving the loaded pickup resonance
  (2–5 kHz, Q ≈ 3 for typical loading, per Lemme and Zollner) by a factor in
  [0.75, 1.33] and Q by [0.7, 1.4], before the plugin, on half the clips, checked
  against EGFxSet's five pickup positions.
- **Not augmented**: time stretch and post-render EQ unless folded into the tail's
  label; compression before the plugin; mixup; frequency masking. Pitch shifting is
  an ablation (the two research passes disagree), not a default.

### 3.4 Mix and stem conditions (after the render, no plugin time)

- **Backing**: the DI's own session backing, time-aligned (70%), another session's
  (20%), none (10%), at the measured guitar-to-backing balance (median −7.7 LU,
  10th–90th percentile −13.7 to −2.1). Random backings alone make separation
  unrealistically easy.
- **Mastering and codecs**: bus compression and a limiter to −14 to −7 LUFS; MP3
  and AAC on about half the clips.
- **Separation in training**: htdemucs_6s on 20–30% of clips, precomputed on whole
  30-s mixes and cropped. Deterministic settings only (`shifts=0`: the default
  `shifts=1` is random, 10.6 dB SNR between runs), pinned weights revision. MPS
  separates 30 s in about 3 s, so 30 h of audio is about 3 h. Train on the separator
  that ships. htdemucs trained on MUSDB18, whose training split includes Atlantis
  Bound's "It Was My Fault For Waiting" (development) and Tim Taler's "Stalker"
  (held out); their stem-rung results are reported apart.

### 3.5 Rendering at scale

- **Reels**: one command renders one setting through 8 segments of [2-s pre-roll +
  6-s kept], which flushes render history without fresh processes.
- **Workers**: Morgan 3, Tone King 2 (1 if the concurrency gate fails); settings
  assigned to workers at random; 2 discarded warm-up reels per process; a canary
  every 50 reels (band levels within 0.5 dB Morgan, 1 dB Tone King; quarantine
  since the last good canary on failure).
- **Licence daemon watchdog**: read its PID and port count every 60 s; stop all
  workers on a PID change; stop gracefully at 230k ports. It is at 155k now, so
  bulk jobs start after a reboot and never alongside other plugin use. Never kill
  or modify the daemon.
- **Driver**: a new `learn/render_job.py` speaking the Swift server's protocol;
  `match/renderer_au.py` is not edited (that would change the renderer identity
  and every committed calibration).
- **Budget** (±2×, Step-0 dependent): a pilot of about 25k clips per amp is ~1 h;
  production of ~130k clips per Morgan amp ~4.5 h, Tone King ~8 h.

### 3.6 Storage and provenance

48 kHz mono 16-bit FLAC (~20 GB per 100k clips; dual-mono asserted), sharded under
`<data>/learn/<dataset_version>/<pack>/<amp>/`, with a parquet index per clip:
settings (native and warped), stratum, proposal component and log q, DI and band
ids with hashes, window start, effective level, augmentation parameters, plugin
version and binary hash, renderer build, worker/launch/command, daemon PID and
ports, canary status, LUFS and flags. Dataset version = hash of all of it. Derived
audio (mix, master, codec, stem) are rows pointing at their parent clip. Features
are computed on the fly or into float16 memmaps; no HDF5.

### 3.7 Sim-to-real

- **Twins**: the same-DI search answer rendered through the part's own DI (all 43
  SW50R parts exist). A paired classifier real-against-twin, scaled by
  twin-against-one-audible-step, says whether the plugin gap is below one step, at
  each rung (amp track, + backing, + Demucs, mastered, MP3).
- **Rung decomposition with known labels**: twin + real backing → mastering →
  codec → Demucs isolates the mix and separation loss.
- **Adaptation**, cheapest first: calibrated randomisation; consistency on
  unlabelled real audio; MMD or gradient reversal as ablations; abstain when out of
  distribution.

## 4. Features and models

### 4.1 Front end

Mono 32 kHz (from 48 kHz by `resample_poly(2, 3)`), 3-s windows with a 1.5-s hop,
2048-point STFT, hop 20 ms, 128 HTK-mel bands 30 Hz–15.5 kHz in dB. Loudness is
normalised once per passage; each window's mean is subtracted and its level
relative to the passage is passed as a token (per-window normalisation would
throw away the level-against-timbre signal the drive heads need). A frequency-index
channel (CoordConv). No per-frequency normalisation, PCEN, frequency masking or
frequency pooling — each erases the EQ the model must estimate. Windows under 50%
active frames are dropped. Tone King renders lose their first second (start-up
mute). Features computed by the repository's numpy code so training and use share
one implementation.

### 4.2 The ladder (each rung must beat the one below and nearest neighbour)

0. **No learning**: the starting preset as it is (the bar), neutral, E1's
   calculation through library DIs, and a factory-prior sampler at the same K.
1. **Nearest neighbour** over a lean fingerprint subset (~115 dims: bands floored
   at peak −40 dB, tilt, centroid/rolloff/flatness percentiles, crest, RMS
   percentiles, LRA, MFCC mean/std/covariance; no decay, attack, ambience,
   harmonic or spatial terms), over the long-term log-mel, and over frozen
   embeddings (EfficientAT mn10, PANNs, AFx-Rep; CLAP as a floor; Fx-Encoder++ and
   MERT local-only screens, being non-commercial).
2. **Ridge, logistic and gradient boosting per head** on the same features — a
   per-head verdict ("does it beat the prior?") and a torch-free fallback.
3. **TC-1M then TC-3M**: a 3×3 ResNet (widths 16–256, multiples of 32) with a
   (3,7) stem striding 4× in time, mean and std over time only (the frequency axis
   kept to 16 rows), 256-d window embedding; gated-attention plus mean pooling over
   a passage's windows with the level token. Measured on this M1 Pro's MPS: about
   1,250 (TC-1M) and 530 (TC-3M) windows/s training, so 30–70 minutes per pilot
   model. A depthwise variant (900–1,400/s measured) is an ablation.
4. **EfficientAT mn10** (MIT, same front end): a frozen probe, then fine-tuning
   with its frequency masking and fmin/fmax jitter off and its frequency axis kept.
5. **Contrastive TC-3M**: SupCon over crossed renders — positives are the same
   *effective* settings through different players, the same DI through other
   settings gives content-matched negatives, pairs closer than one audible step are
   dropped from the negatives, and a term ties embedding distance to the paired
   audio distance. It is the only rung aimed at the binding constraint, and the
   source of a judge for checking renders and of an out-of-distribution score.
6. **Joint coherence**, only on evidence (best-of-8 renders ≥10% better than
   per-head modes on simulated targets): multiple-hypothesis heads, then a small
   autoregressive decoder; a flow/MNPE posterior as an uncertainty study only.

### 4.3 Heads and losses

Masked HL-Gauss cross-entropy on binned heads over perceptually warped axes (σ =
one audible step; Imani & White 2018, Farebrother et al. 2024), topology
cross-entropy with label smoothing 0.05, a consistency KL between the same
settings through two players, auxiliary heads for the DI's level and tilt and for
the chain's long-term transfer curve. No regression of raw knobs (it averages
equivalent settings; Hayes et al. 2025), no differentiable neural proxy of the
plugin (DeepAFx-ST, PNP), no `unpaired-v3` as a loss.

### 4.4 Uncertainty and abstention

Temperature scaling and split-conformal sets per head, calibrated on leave-band-out
predictions; the fold models as an ensemble; Mahalanobis distance on the pooled
embedding for out-of-distribution. The model's preset is delivered only if it is in
distribution, confident, consistent across windows and folds, and — if checking
renders are used — its judge distance beats the starting preset's by a margin set
on development folds (Learn-then-Test). Otherwise the starting preset is returned
with the reason. With 43 parts the risk bounds are wide; report risk–coverage
curves, not certified risk.

### 4.5 Tooling

torch 2.14 on MPS in fp32 (fp16 gave no speed-up), a plain training loop, argparse
plus a frozen dataclass config, plain JSON run records (MLflow on sqlite optional),
Optuna nested inside outer folds (≤30 trials), scikit-learn 1.9 for the cheap rungs.
Not torchaudio (maintenance mode), Lightning, `torch.compile` on MPS or Hydra. A
CPU/MPS parity test is a unit test of the training code. Training never runs while
renders do.

## 5. Validation

### 5.1 Splits

- **Simulation**: crossed folds — 4 DI folds by catalog `group` (each band's DIs,
  usable or not, and its backings) × 4 settings folds by parent preset (jittered
  presets are near-duplicates). Each training uses folds ≠ i on both axes and is
  scored on new DI × new settings (primary), new DI only and new settings only; the
  gaps say whether to add players or settings.
- **Real parts**: leave-one-band-out (13 models × 5 seeds, about one night with the
  small nets); stress tests leave-source-out (Cambridge ↔ Telefunken) and the six
  Telefunken bands collapsed into one cluster; a within-band random split as the
  positive control for player leakage.
- **Hyperparameters** inside each outer fold only; early stopping on a validation
  set disjoint by band and parent preset; never on the 43 real parts.
- **Set 1**: Whiskey Heart and Coltraine DIs stay out of training (their held-out
  sessions share players); Guitar-TECHS P3 stays out.

### 5.2 Leakage guards (run before every training job)

DI hashes checked against the held-out lists; exact and envelope-correlation
duplicate detection (Zeno ElecGtr8/9 are sample-identical: keep one); a chain
signature and a band-ID classifier to find the same player or guitar filed under
two bands; no test setting within one audible step of a training setting; scalers
and statistics fitted inside training folds only; checking-render libraries never
from the target's band.

### 5.3 Metrics

- **Parameter space** (reported, never used to select): error in audible steps,
  drive-ladder accuracy, top-K and balanced accuracy per discrete head with a skill
  score against the prior, calibration on the new-DI cell, and audio-equivalent
  accuracy (a render within the repeat floor of the truth counts as right).
- **Audio regret** (the primary quantity): r(p) = log D(model) − log D(starting
  preset as it is), level left out, rendered through the part's own DI against its
  amp track on 3 active crops. D is the distance validated in stage 0b; candidates:
  - **v3c**: `unpaired-v3` with `band_shape` over bands within 30 dB of the peak,
    shared dimensions only, unmeasurable as a loss, and the ambience and decay
    terms dropped;
  - **ALM**: an aligned multi-resolution log-mel distance (23/46/93 ms, 50 Hz–
    10 kHz), both sides loudness-normalised, frames where the DI plays, bins within
    30 dB of the reference's peak.
  Embedding distances are exploratory only. If checking renders rank candidates by
  one metric, the other must agree in direction.
- **Comparators at equal K**: the starting preset, the prior sampler, nearest
  neighbour, E1's calculation, neutral, and the same-DI answer (the ceiling).

### 5.4 Statistics

The primary test is an exact sign-flip over bands of each band's mean log ratio.
One-sided α = 0.05 for development screens, two-sided for confirmatory claims.
Amps are tested in a fixed sequence (SW50R → PR12 → Tone King → AC20), each at full
α only if the previous passed; Holm within secondary families; ablations
descriptive. "Not significant" is not "tied": ties are claimed only by equivalence
at a declared margin (±5%). Mixed models for estimates and moderators only. A
ledger records every look at real development results, capped at three per amp
before the held-out test.

## 6. Stages and gates

**Stage 0 — foundations (no model; about a week).**
- 0a. This plan merged; the fold draw and the crop rule (≥90% DI activity, 3 crops
  per part) committed.
- 0b. **Metric validation by listening**: v3c and ALM implemented with tests; about
  85 blind R-A-B trials from existing renders (stratified by |Δ| with 15 per bin,
  ~25 where the two metrics disagree, hidden repeats, catches, anchors), about 2.5 h
  in eight 18-minute sessions. A metric is validated if it agrees with decided
  verdicts ≥70% (p < 0.05) above the second |Δ| bin. **Stop** model work if none
  validates. The 16-trial test now running is a first look.
- 0c. **Renderer measurements**, on an idle machine after a reboot (about 2 h):
  ports per command against per audio second; seconds per command against length;
  the level-fold check; the F0 null tests; history with a 2-s pre-roll on every amp
  and channel; Tone King concurrency; Demucs MPS benchmark.
- 0d. Variance pilot (crops, repeats, library draws) on 10–15 parts; leakage-guard
  scripts.

**Stage 1 — simulation, SW50R.** Sampler, render job and (if F0 passed) tail
calibration; about 2,000 settings × 12 bands crossed (~25k clips), 6k more for the
settings curve. Rungs 0–3 and 5. **G1**: on new DI × new settings, top-1 regret
≤0.8× nearest neighbour's and ≤0.6× the starting preset's in ≥3 of 4 folds; new-DI
regret ≤1.3× seen-DI; topology ECE ≤0.05. **Stop** the CNN if it does not beat
nearest neighbour; **get more players** if the player curve is still steep. The
twin diagnostic runs here.

**Stage 2 — real amp tracks, SW50R** (leave-one-band-out, 5-seed ensemble).
**G2**: band-mean log ratio ≤ log 0.85, one-sided band p < 0.05, the secondary
metric agreeing, ≥8 of 13 bands, and beating the prior sampler and nearest
neighbour at equal K. Stop the amp below a 5% point estimate; at most two more
iterations in between.

**Stage 3 — stems, then songs.** G3: htdemucs_6s stems keep ≥50% of G2's gain and
are non-inferior to the starting preset (upper bound of the band-mean log ratio
below log 1.05), single- and multi-guitar parts reported apart. G4: full mixes with
vocals through a declared mastering chain and timestamp rule, same criteria.

**Stage 4 — other amps.** PR12 (and AC20 if its history gate passes) with a shared
amp head; Tone King after renderer hardening, one model with a channel head.

**Stage 5 — held-out, declared once.** All amps in one committed declaration:
direction plus non-inferiority on the 19 held-out parts, and blind backed
listening (model against the starting preset). Only then can a model's registry
status become `validated` (§7). A confirmatory claim of size waits for set 3.

## 7. Product integration and sharing

- **Runtime without torch**: the architecture is restricted to operations a ~200-line
  numpy runtime runs (measured: a 1.6M-parameter CNN over 20 windows in 0.33 s,
  agreeing with torch to 6e-8); weights exported to safetensors (a numpy-only reader
  loads 55 MB in 11 ms). Torch lives in a local `[learn]` extra. Not TorchScript
  (broken on Python 3.14), Core ML (no 3.14 wheel) or ONNX (needs ≥3.11; CI tests
  3.10).
- **Hosting**: GitHub Release assets with immutable releases; a committed
  `models/registry.json` (URL, sha256, licence, tier, verified plugin versions,
  feature version, status); download on first use with consent into
  `~/ndsp-presets/models/`; no Git LFS.
- **Product**: a separate `scripts/propose_preset.py`; `match_preset.py` keeps
  refusing a no-DI search. A model is offered only with registry status
  `validated`; it shows each control it sets with a probability and conformal set,
  what came from research, rule or template, and abstains with a reason. Checking
  renders, if they earn their place, run through *cleared* DIs only (Guitar-TECHS
  or synthetic) — E1's library cannot ship.
- **Separation at use time**: a stem the user brings is first-class; built-in
  htdemucs_6s in its own venv, `shifts=0`, pinned revision.
- **Drift**: the plugin's Info.plist version and binary hash; canary renders through
  code-generated DIs; a prediction canary (the model must read the canaries as it
  did when trained); a model abstains on an unverified plugin version.
- **Licence tiers for shared weights**:
  - **A, publishable**: CC BY and synthetic DIs only — Guitar-TECHS P1/P2 (3
    players with paired DI and amp mic, ~4 GB), EG-IPT (1 player, CC BY), EGFxSet
    (1 Strat), GuitarSet (6 players, hex pickup on an acoustic) — with CC BY or no
    backings. About 10–11 players.
  - **B, non-commercial**: adds Telefunken and Cambridge sessions only with written
    permission (Cambridge's FAQ says research use was never agreed with
    contributors; Telefunken allows home-studio and educational use only).
  - **C, local only**: everything, for comparison.
  A Tier A arm runs beside the full local model in stages 1–2; Tier A ships if its
  regret is ≤1.1× the full model's. **Neural DSP's plugin EULA is unread** — not
  public and not on disk; other vendors forbid AI training on plugin output (Native
  Instruments' EULA §3.1). It governs every tier and must be read before anything
  is published.
- Each release carries a model card (results by part and band, both metrics,
  listening, calibration, abstention rate, known failures), a data statement
  (sources, licences, minutes, players, hash manifests, no audio) and a
  machine-readable `model.json` the skills quote from.

## 8. More bands: set 3

Power is the binding statistical constraint. A set 3 of at least 20 new bands,
found and declared before any model is trained (following the set-2 procedure:
more Cambridge sessions, other Telefunken seasons, Guitar-TECHS P1/P2's paired
recordings), is the cheapest route to a claim of size. It needs downloads.

## 9. Decisions for the user

1. **Listening time** for stage 0b (about 2.5 h in eight sessions).
2. **A reboot** before the stage-0c measurements and each bulk render (the licence
   daemon's ports reset only then).
3. **Downloads**: Guitar-TECHS P1/P2 (~4 GB, CC BY), EGFxSet Clean (431 MB, CC BY),
   EG-IPT (23.8 GB, CC BY) and GuitarSet (~0.7–3.6 GB, CC BY) for Tier A and extra
   players; the five Cambridge sessions that failed pairing (20 DIs, local only);
   candidates for set 3.
4. **Neural DSP's EULA**: read it from the installer's licence pane or ask
   support — before any weights are published.
5. **Sharing tier**: A, B (after permission emails, which would be sent by the user
   or with their explicit OK), or C.
6. **Torch** in a local `[learn]` extra (the existing Demucs venv has torch 2.14
   with MPS and needs no download for the pilot).

## 10. Corrections to the earlier report

- Render with a coverage-heavy proposal and record q(θ); choose the prior at
  training time (not a 40/30/30 render mix).
- Normalise loudness per passage with a per-window level token, not per window.
- Select models by a listening-validated paired distance, never `unpaired-v3`.
- Top-K checking needs a validated judge; until then take top-1.
- Contrastive positives at equal *effective* drive, or invariance erases drive.
- Group settings by parent preset as well as DIs by band.
- The G2 gate is band-level at 15%; 13 bands cannot resolve 10%.
- Store 48 kHz (16-bit); model at 32 kHz. Demucs on MPS is ~0.1× real time, not 45 h.
- Weights are not necessarily local-only: Tier A is publishable once the EULA is
  known; Tier B with permission.
- htdemucs_6s's default `shifts=1` is random; use 0 and pin the revision.
- E1's library DIs cannot ship; checking renders must use cleared DIs.
