# Supervised settings model: deep-dive report

The third research report on song-only matching, after round 1
(`docs/research-song-only-matching.md`) and round 2
(`docs/research-full-plugin-estimation.md`). It asks whether a network trained
on (settings, plugin render) pairs can map a song's separated guitar stem to the
plugin's full settings, and what a fair pilot would look like. None of its pilot
steps has been run. Some figures are the research agents' own measurements on
local data and are not committed, and the E1 figures come from an uncommitted
run of `scripts/benchmark_recordings.py --no-search` on 2026-10-03.

## 1. Verdict

A supervised model can be built here, and rendering time and compute are not what stops it. A decisive SW50R pilot needs about 25–40k renders, which is 1.5–4 hours on reused plugin processes, plus small networks that train on this Mac. Producing the full training set would take about one night of rendering per amp or channel.

Whether it works depends on three things that more renders cannot fix:
- **Players.** The training DIs are 13 development bands, but only about 8 recording chains, because six of the bands were recorded in the same Telefunken room.
- **Real recordings and stems.** Features learned from plugin renders may not carry over to real mic'd amps and separated stems.
- **What can be learned.** The model can learn about 20–25 quantities the audio actually reveals, plus the topology (amp or channel, pedals on/off, mic family). It cannot learn ~150 raw knobs.

This refines round 2's verdict rather than overturning it:
- **Where round 2 is right:** the limit is the data, not the network.
- **Where round 2 is wrong:** its cost estimate. It said about two-thirds of pilot renders would need fresh processes. That is no longer true once time effects and the amps' spring reverbs are off in training renders. SW50R and PR12 can then train entirely in reused processes, with no licence-daemon problem.
- **Where round 2 is too cautious:** its timing. It holds the model back until the hand-built drive features fail. The simulation pilot is cheap enough to run as extra rows inside round 2's recoverability screen, on the same renders.

This morning's inversion-only run (E1) set a concrete bar. Measurements are with level left out and are uncommitted:
- **SW50R:** inversion through a library DI ended closer than neutral settings on 33 of 43 parts, with a median 19% closer.
- **Tone King rhythm:** 27 of 43 parts, 11% closer.
- **For comparison, the part's own DI:** 42/43 and 41/43.

My estimate is a 15–30% chance that a learned model clearly beats that bar on real song stems. It is most likely to earn its place on drive and topology, where the hand features are weakest: 22–34% right picks across performances, against 14% chance.

**Against round 2's deterministic estimator:**
- The estimator is cheaper, needs no torch, and labels every control.
- The model may read drive and topology better, if it learns the tone rather than the players.
- Neither has yet been shown to work on a song.

**They combine naturally:**
1. The model proposes a few coherent candidates (topology plus drive).
2. The estimator's closed-form EQ and cab fit and its signal-processing time-effect detectors fill in the rest.
3. 8–40 checking renders through 3–4 library DIs choose between them.
4. When the model is unsure, it falls back to E1's inversion.

One product consequence: the useful training DIs are licensed for non-commercial use, so the trained weights stay on your Mac and cannot ship with the GitHub plugin.

## 2. What it takes

### Data

**Players and DIs (training uses only the DI, so parts that failed pairing still count)**
- **Set-2 development material:**
  - 13 bands, 74 DI tracks, 273 minutes, of which about 163 minutes is actual playing.
  - Six Telefunken bands share one room, and their backings carry bleed of the same amp. Report them separately from Cambridge.
- **Set 1:** development DIs only. Guitar-TECHS P3 never enters training or a library.
- **The cheapest extra diversity: about 15 more Cambridge sessions with DI tracks.**
  - The scratch catalogue lists 32 Cambridge sessions with paired electric-guitar DIs; 16 are on disk.
  - Training needs no pairing test, so the rest are usable as they are. Held-out bands (e.g. Forkupines, Lights Off Clarity) stay excluded.
- **Public sets:**
  - Guitar-TECHS P1/P2: 2 players playing exercises, CC BY. https://arxiv.org/html/2501.03720
  - EGFxSet: a Stratocaster at 5 pickup positions, CC BY, single notes. Use it to calibrate pickup augmentation. https://zenodo.org/records/7044411
  - IDMT-SMT-Guitar: CC BY-NC-ND, so only as an unseen-guitar test. https://zenodo.org/records/7544110
  - GOAT: by request, research-only, includes alternative tunings. https://arxiv.org/html/2509.22655
- **Synthetic players are not a substitute.**
  - SynthTab is about 13k hours of tablature rendered through about 7 sampled electric guitars, CC BY-NC. https://arxiv.org/html/2309.09085v3
  - It adds musical content, not players or picking dynamics.
  - In a related transcription study, synthetic-only data scored 66 against 81 F1 for real data, and fidelity was the bottleneck. https://arxiv.org/html/2508.07987
  - Try one clean zip only if the player learning curve is still rising after the extra Cambridge bands.

**Settings to render**
- A frozen, committed mixture:
  - 40% factory presets with jittered knobs;
  - 30% draws from the factory frequencies;
  - 30% coverage sampling in perceptual units.
- Amps and channels are balanced.
- Factory-only sampling would teach accidents as facts. For example, Dynamic 57 is the left mic in 79 of 107 Morgan presets, and there are only 20 distinct amp × drive × compressor combinations.
- The sampling distribution acts as the model's prior when several settings sound alike, so choose it on purpose.

**Augmentation before the plugin**
- **Level:** jittered, then folded into the label (see "Model and outputs").
- **Pickup and tone-knob colouring:** calibrated to the measured spread between development DIs' spectra, rather than adding a second resonance to DIs that already have one.
- **Small changes:** hum and noise; ±1 semitone on at most 20% of clips; ±8% time stretch.
- **What fixed EQ cannot fake:** pickup position, which depends on the note. https://www.ntnu.edu/documents/1001201110/1266017954/DAFx-15_submission_45.pdf

**Augmentation after the render (no plugin time)**
- **Backing mix:**
  - Mix into the session's own time-aligned backing. Random backings make separation unrealistically easy. https://www.merl.com/publications/docs/TR2024-030.pdf
  - Use the measured balance: on the development crops the guitar sits a median 7.2 LU below its backing (10th–90th percentile −13.8 to −2.2).
- **Mastering:** bus compression and a limiter to −14 to −8 LUFS, via dasp-pytorch (Apache-2.0). https://github.com/csteinmetz1/dasp-pytorch
- **Codec:** MP3 or AAC on about 30% of clips.
- **Separation:** precomputed for a share of clips.
- **Song reverb:** generic impulse responses as a nuisance. This is fine because the model does not predict time effects.
- **No EQ augmentation beyond a ±1 dB tilt.** A mix EQ looks exactly like the preset's EQ, so randomising it would teach the model to ignore what it must estimate.

**Dataset size**
- **Pilot:** 2,000 settings × 12 bands = 24k clean renders, plus about 6k for a settings curve and about 1–2k 10-s evaluation targets.
- **Production:** 100–150k settings × 2 clips per family (SW50R, PR12, AC20, Tone King rhythm, Tone King lead), only if the pilot's settings curve still improves by ≥5% from 12k to 24k.
- **Not Hayes-scale:** 2M renders would be about 100 h per pack. https://arxiv.org/html/2506.07199
- **Precedent:** 1M renders of a commercial plugin in about 24 h on a 2018 Mac mini. https://arxiv.org/html/2407.16643

**Render-hours on this Mac**
- Reused Morgan renders take about 0.3 s each (up to 0.9 s under load), with 3–4 workers.
- Pilot: 1.5–4 h in total.
- Production: about 6–12 h per family, so one night each.
- Tone King may need 2–3 nights if it must run on one worker (see below).
- Storage: about 20–35 GB of 32 kHz FLAC per family, against 266 GB free.

**Staying within the licence-daemon limits**
- **Reused workers only:**
  - Restart each worker every 2,000 renders, and immediately when the daemon's PID changes.
  - Run a canary render every 200 renders.
  - That costs about 1.5k ports per 300k renders, against the ~267k at which macOS kills the daemon.
- **Things that would otherwise force fresh processes stay off:**
  - Time effects and the gate.
  - SW50R's spring reverb, pinned off or flushed with a 6-s warm-up. Its tail carries up to 0.15 into the next render; the warm-up clears it completely.
- **AC20:**
  - Its render history is measured at about 0.09–0.1 spread (SW50R about 0.01, PR12 about 0.001), and only a new instance resets it.
  - Fresh-process AC20 at production scale would be about 1.5M ports, several daemon kills.
  - So AC20 trains in reused processes only if that history noise is ≤0.15× the typical distance between settings. Otherwise it is left to the estimator.
- **Tone King:**
  - Needs round 2's renderer hardening and discarded warm-up renders.
  - Needs a test of one serial instance against four concurrent ones. Concurrency moved one EQ band's on-screen movement 39× further in §12j, and Tone King scaled only 2.28× in §12k.
- **Never alongside other overnight queues.** The critic read the daemon at about 88k ports this morning, rising about 14k/h under other jobs.

### Model and outputs

**Encoder**
- A small CNN, 1–5M parameters, on 128-band log-mel.
- Each window is loudness-normalised, so absolute level is invisible, as in a master.
- Attention-pooled over 10–30 windows of the song's passage. One preset played at many intensities partly averages out the picking.
- EfficientAT sizes (MIT) are the template. https://github.com/fschmid56/EfficientAT
- Not general encoders: MERT is amplitude-invariant and non-commercial. https://arxiv.org/html/2607.03806
- Not large transformers from scratch at this data scale.

**Outputs: only quantities the audio can identify**
- **Topology heads:** amp or channel, pedals on/off, compressor on/off, voicing switches, mic family (Morgan's two mic slots sorted, removing a swap symmetry).
- **Continuous heads**, each a choice among bins aligned to the plugin's grid:
  - effective drive;
  - amp Volume and pedal gain;
  - 9 EQ bands plus high- and low-pass;
  - coarse tone knobs.
- **Knob heads are conditioned on the topology,** and heads for inactive controls are masked by `match/space.py`'s gates.
- **Effective drive** is `inputGain` plus the DI's level offset from the −22.9 LUFS development median. It turns the playing-level confound into an exact label transform, if a minutes-long check confirms `inputGain` sits at the plugin's input. The split back into `inputGain` still needs a pickup assumption (round 2's decision 2).
- **Set by rule, outside the model:** output levels, pans, phase, stereo, doubler, transpose, gate threshold, Morgan's room mic type, mic position and distance (they fold into the EQ), and time effects (round 2's detectors).
- **Many settings can sound alike.** Independent per-knob outputs can then combine into incoherent presets. So the model outputs the top-K joint candidates, checked by rendering, and a nearest-neighbour or autoregressive re-rank is compared with them. https://arxiv.org/html/2506.07199
- **Honest confidence and abstention:**
  - Fit a mixed discrete/continuous posterior (sbi's MNPE) on the frozen features, at small scale: drive class, amp/pedal class, effective input, tilt. https://arxiv.org/html/2605.13551
  - Abstain per family on distance from the training data, disagreement across windows and folds, and the margin of the checking renders.

**Evidence of what published estimators reach**
- **In domain:** synthesizer inverters with fixed note excitation reach about 87% categorical accuracy, but only 67% on a 32-way choice of synthesizer architecture (DX7's 'algorithm' setting). https://archives.ismir.net/ismir2023/paper/000076.pdf
- **Out of domain:** audio error grows; direct regression was the worst method. https://arxiv.org/html/2609.31024
- **Guitar effects:** the evidence is all simulation.
  - A network trained on clean guitar fell below 40% accuracy with only a kick drum mixed in. https://www.tnt.uni-hannover.de/papers/data/1571/EURASIP_2022.pdf
  - Drive classes collapsed under a different input-loudness distribution, which is our confound. https://dafx.de/paper-archive/2023/DAFx23_paper_30.pdf
- **Existence proof:** a commercial "music-to-tone" feature exists in Positive Grid's own engine, with no published accuracy. https://www.positivegrid.com/blogs/positive-grid/so-what-is-bias-x

### Losses

- **Training loss:**
  - Cross-entropy on every categorical and binned head, masked where a control is inactive.
  - Gaussian label smoothing about one audible step wide, with each knob's weight set by its measured audio sensitivity. This is a parameter loss weighted by how much each knob changes the sound. https://arxiv.org/pdf/2301.02886
  - A consistency term: the same settings rendered through two players should give the same prediction.
  - Gradient reversal on band identity as an ablation only. https://arxiv.org/abs/1505.07818
- **Audio is used only for:**
  - choosing among candidates (checking renders);
  - choosing between models, by "regret". Render the prediction through the target's own DI and score it with `unpaired-v3`, level left out.
- **Never select by parameter error.** In M7-2, parameter error fell while the sound got worse. A CNN with among the best parameter errors had some of the worst audio in FlowSynth. https://arxiv.org/abs/1907.00971
- **Audio and parameter losses each win in different places.** An audio loss beat a parameter loss on an effect chain (Mel 0.40 against 0.49), while the parameter loss won on a lone compressor or clipper. https://arxiv.org/html/2310.11781
- **Never a spectral loss alone, and never training through a neural proxy of the plugin.** PNP's spectral-loss-trained model was the worst.
- **Later, optionally: fine-tuning with an audio reward on real DI and amp pairs.**
  - It worked for synthesizers: out-of-domain loss 8.84 to 3.90 (https://archives.ismir.net/ismir2021/paper/000053.pdf), and +17.9% (https://www.ijcai.org/proceedings/2025/1129.pdf).
  - But those had thousands of targets and no player confound; we have 43 parts from 13 bands.
  - Expect a small gain. Same-DI search answers are pseudo-labels for continuous knobs in one fixed topology, not ground truth.

### Separation front end

- **Ship htdemucs_6s.**
  - MIT, archived.
  - MVSep guitar SDR 5.25 (https://mvsep.com/quality_checker/leaderboard/guitar?page=2); 3.07 dB on MoisesDB against about 5.3 dB for an oracle mask (https://ar5iv.labs.arxiv.org/html/2307.15913).
  - Already installed in `~/ndsp-presets/tools/demucs-venv`, with torch 2.14 and MPS.
- **Train on the separator you ship.** Treat other separators' stems as test sets.
- **Separation must be in training if stems fail.** Dropping stem input cost StemFX 86.8% → 48.0% top-1 (https://arxiv.org/html/2607.15634). A clean-trained model fed a 3-dB-SDR stem will probably fail, so plan to precompute separated training windows.
- **BS-RoFormer-SW (9.01)** stays a local experiment; its weights' licence is unknown.
- **Logic Pro 11.2's Stem Splitter (9.00)** is a stem you can bring yourself. https://www.apple.com/newsroom/2025/05/logic-pro-amplifies-beat-making-on-mac-and-ipad-with-advanced-new-capabilities/
- **Moises / Music.AI (6.94):**
  - $0.10/min. https://music.ai/pricing/
  - Music.AI's API terms forbid training models on its output. https://music.ai/terms/
  - The Moises app's own terms could not be read.
  - So it is a match-time input only, never training data.
- **Multi-guitar stems remain ambiguous.** At least 32 of 43 development mixes contain other guitars, so a user-chosen timestamp stays the practical answer.

### Compute: Mac against a rented GPU

- **Rendering:** always on the Mac (the Audio Unit and its iLok licence live here).
- **Pilot training:**
  - On MPS. The M1 Pro trained a ResNet-18 about 14× slower than an A6000 (https://www.lightly.ai/blog/apple-m1-and-m2-performance-for-training-ssl-models). For 1–5M-parameter CNNs on about 24k clips, that is roughly 15–60 min per model (unmeasured).
  - About 12–16 models (folds × learning-curve points) fit in one night.
- **Separating training clips:**
  - 18k clips of 6 s is about 30 h of audio, about 45 h on the CPU. That is the real compute bottleneck.
  - Benchmark Demucs on MPS first. If it is slow, a rented GPU does it in plausibly an hour or two (unmeasured).
- **Production training:** tens of hours on MPS, or a few hours on a rented A100.
  - RunPod RTX 4090 $0.34–0.74/h, A100 80 GB $1.19–1.59/h. https://www.runpod.io/pricing
  - Plausibly $5–20 per family and under $100 for everything (unmeasured), plus hours of upload (about 30 GB per family).
- **Licence for the cloud:**
  - Renders made from Cambridge and Telefunken DIs inherit those home/educational terms.
  - Uploading them is your call; CC BY material is safe but has only two players.
- **Match time:** Demucs (about 1.5× the excerpt on the CPU), under a second of inference, 8–40 checking renders. About 1–3 minutes.

## 3. A gated pilot

### Step 0, one evening (about 2 days of code, about 2 h of plugin time, idle machine)

**1. Level-fold check**
- Setup:
  - 3 settings with the compressor and a drive pedal on, gate off.
  - A DI below −24 LUFS, scaled by −12, −6 and +6 dB, with `inputGain` moved by the opposite amount.
- Pass: the sample null is within the repeat floor. The level is then free augmentation; on a fail, render level variants explicitly.
- The same renders choose the DI level statistic (LUFS, peak percentile or crest-adjusted) that best collapses drive across DIs.

**2. Render policy for training**
- Setup:
  - 200 sampler settings per amp, time effects and gate off, spring reverb pinned.
  - Reused against fresh renders.
  - AC20's drift over 2,000 reused renders.
  - Tone King serial against concurrent.
  - Ports per 1,000 renders.
  - Cost per render at 3.5 s against 10 s.
- Pass: reused-to-fresh distance ≤0.15× the median distance between settings, per amp.

**3. MPS benchmark (20 min)**
- CNN training throughput, and htdemucs_6s seconds per clip on MPS against the CPU, with the outputs agreeing.
- Train locally if MPS reaches ≥150 examples/s.

**4. Twin diagnostic from answers already on disk**
- `bench-set2/runs/set2-rehearsal/` holds the same-take answer and its render for all 43 SW50R parts. That saves about 13k renders.
- Also render each answer through a second window of its session: 43 fresh renders.
- Mix twin and real into the window's backing, run Demucs on the 172 clips, and compare E1's answers from twin against real.
- Gates:
  - Same-DI answers lose ≤30% of their gain out of window; otherwise they are crop-overfit and unusable as pseudo-labels.
  - |score from twin − score from real| ≤0.15 median; otherwise nothing trained on renders will transfer, and the deterministic estimator carries the load.

### Step 1, simulation, SW50R (about 5 days of code, 1.5–4 h of renders, one night of training)

**Renders**
- 2,000 settings × 12 development bands, crossed (this includes round 2's S4 design of 600 × 12, so the two share renders).
- About 6k for the settings curve.
- About 1–2k 10-s targets on held-out bands.

**Rows, all in one run**
- neutral;
- neutral plus E1's library-DI inversion;
- nearest neighbour over the renders;
- ridge;
- a numpy MLP on the existing fingerprint (no torch);
- the CNN (top-1, and top-8 plus a 4-library-DI check);
- a factory-prior sampler at the same K with the same checks, which shows what K renders buy without any model;
- round 2's hand-built in-note drive features (F2) on its drive ladders.

**Folds and learning curves**
- Folds: leave-3-bands-out (4 folds); Cambridge against Telefunken; an in-player split as a positive control.
- Bands: N = 2, 3, 6, 9 at a fixed 2k settings, 3 random subsets each. Run nearest neighbour and ridge first (minutes), and the CNN at three points.

**Gates**
- **Overall:** the CNN's median regret is ≤0.8× nearest neighbour's and ≤0.6× neutral's in ≥3 of 4 folds, and it beats E1's inversion on ≥60% of simulated targets.
- **Drive:** the right one of 7 steps ≥50% at −18 LUFS (timbre 26.5%, chance 14.3%).
- **Effective input:** error ≤0.6× a constant guess, and joint regret ≤0.75× `unpaired-v3`'s.
- **Generalisation:** unseen-band regret ≤1.3× seen-band regret.
- **Stop rules:**
  - If the CNN does not beat nearest neighbour, stop the CNN. Nearest neighbour may still serve as a no-torch row in round 2's estimator.
  - If regret at N=9 is ≤0.85× regret at N=2 and the last step still gains ≥5%, players are binding: download the extra Cambridge sessions before anything else.

### Step 2, real development parts (about 2 days of code, about 1–2 h)

**Amp-track rung**
- All 43 parts, models used only on bands they were not trained on.
- Harness additions: `--arm-settings` and `--save-specs` in `benchmark_recordings.py`.
- Arms:
  - neutral;
  - E1 library inversion (SW50R: 33/43, −19%, level left out);
  - nearest neighbour plus checks;
  - the factory-prior sampler plus checks;
  - the model plus checks (≤40 renders);
  - whatever of round 2's estimator exists (F3 factory retrieval, F2 drive);
  - the same-DI ceiling.
- Pass:
  - closer than E1 on ≥26 of 43 parts and ≥10 of 13 bands, with a median ≥10% closer;
  - beats the prior sampler and nearest neighbour at equal K on ≥26 of 43;
  - abstains on ≤30%.

**Zero-render check on real audio**
- Groups recorded with one tone: a part and its double, the Telefunken M80 against its alternate mic, and the Guitar-TECHS P3 development excerpts (evaluation only, never training).
- Pass: predictions agree within one drive step on ≥75% of same-tone pairs.

**Stem rung (only after the amp-track rung passes)**
- Input: the htdemucs_6s stem of `mix_instrumental`, with single- and multi-guitar parts and Cambridge and Telefunken reported separately.
- Pass: keeps ≥50% of the amp-track gain over neutral.
- Fail: retrain with an overnight precompute of 2–4k separated Cambridge windows. Pass then needs ≥3 more parts than the clean-trained model.

**Go/no-go:** about 2–3 weeks of work, about 6–10 h of plugin time and 2–3 nights of training.

### Scaling, only after SW50R passes

- **PR12** (history about 0.001, reused processes): train SW50R and PR12 together with an amp head. Compare that head with round 2's S3 imitation test, which says whether the amps can be told apart at all.
- **AC20:** joins only if Step 0's history-noise gate passes. Otherwise the learned amp head covers SW50R against PR12, and AC20 is chosen by the estimator.
- **Tone King:** after the renderer hardening. One model with a rhythm/lead head, warm-up renders discarded, and one worker if the concurrency test fails (2–3 nights per channel). E1 shows the most room here: library inversion beats neutral on only 27/43.
- **Production size per family:** set by the settings curve, likely 100–150k settings × 2 clips. Pin the plugin version; an update means about a night of re-rendering per family.
- **Combination:** the final comparison is round 2's A2, with the model plus estimator as one arm, then a declared held-out listening test.

## 4. Risks, and what not to do

**Risks**
- **It learns the players, not the tone.** 13 bands and about 8 chains, with no metal in set 2.
- **Telefunken inflates results.** The shared room and the backing bleed make cross-band results look better than they are.
- **Label noise from render history.** SW50R's spring reverb (up to 0.15), AC20 (about 0.1), Tone King concurrency.
- **Clean development mixes flatter real songs.** They are unmastered unity sums; check on Telefunken's real "Fragments" master.
- **Weak statistics.** Gates like 26 of 43 alone have p ≈ 0.11, so count wins by band too.
- **Plugin updates invalidate the dataset.**
- **Neural DSP's licence terms on training models from plugin renders were not checked.**

**What not to do**
- Regress all ~150 raw controls, or choose models by parameter error.
- Train with a spectral loss alone, or through a neural proxy.
- Put time effects, output level, pans or the gate inside the model.
- Render one fresh process per training render, or run training renders alongside other overnight jobs.
- Render 2M up front; let the learning curves set the size.
- Use Moises or Music.AI output as training data, or random backings as the only mixing scheme.
- Augment with EQ, which hides what the model must estimate.
- Train on held-out parts, set-1 P3 or IDMT, or ship weights trained on non-commercial DIs.
- Build an embedding-search model or a reward-trained token decoder now. Both need orders of magnitude more data.
- Use same-DI search answers as labels for amp, pedal or mic choices; the search holds them fixed.

## 5. Decisions for you

1. **Torch in an optional `[learn]` extra for local experiments,** so the learned rows can join round 2's screen now rather than after F2 fails. I recommend yes.
2. **Downloads:**
   - Now: about 15 more Cambridge sessions with DI tracks, Guitar-TECHS P1/P2 (CC BY) and EGFxSet clean (CC BY).
   - Only if the gates call for it: one SynthTab clean zip (under 50 GB, non-commercial) and a GOAT request.
3. **Cloud GPU:**
   - Not needed for the pilot.
   - For Demucs precompute and production training: a rented 4090 or A100 at $0.34–1.59/h, plausibly under $100 in all.
   - It means uploading renders made from home/educational-use DIs. The alternative is multi-night local runs.
4. **Weights stay on your Mac.** You accept that the learned model is a personal, local feature, not something the GitHub plugin can ship.
5. **Separator.** Demucs as the shipped default, with Logic or Moises stems accepted as input, never as training data.
6. **AC20.** If its render-history noise fails the gate, leave AC20 to the deterministic estimator rather than spending daemon-killing fresh renders on it.
7. **Carried over from round 2:**
   - A one-time pickup-output preference, needed to turn effective drive into `inputGain`.
   - A timestamp pointing at an exposed guitar passage, for multi-guitar songs.