> Input report for `docs/research-audio-ml.md` (round 4), kept as written. Where the synthesis corrects a claim here after a source check (its §8), the synthesis holds.

# A. Measuring tone closeness: what the literature offers the judge

*2026-10-05. Web sources only; nothing run but a binomial power calculation. [V] = source opened and the claim is in it; [U] = unverified (snippet, memory or my reasoning). Earlier reports already cover ST-ITO/AFx-Rep, Fx-Encoder++, Open-Amp, Chen et al., Deng et al., frame MMD, Demucs and symmetric degradation; not repeated.*

## Bottom line

1. **No off-the-shelf perceptual metric is a better judge for this task.** Learned similarity metrics were trained on speech degradations; quality models score a degraded copy against a clean reference. Neither describes two different good tones. The judge's design (multi-resolution log-mel, level removed, masking floor) matches the best signal metric in the amp-modelling literature, and its weak spots (excess treble, high gain, drive) are where that literature says log-spectral distances fail.
2. **High gain is the real risk.** In Wright et al.'s listening test, a log-mel L1 distance ranked two heavy-distortion models in the wrong order: 0.19 got a MUSHRA score of 57, while 0.22 got 92. On distortion and fuzz, an embedding FAD tracked listeners as well as MR-STFT did. Validate the judge on high gain before trusting it there.
3. **With 22 decided trials, metrics cannot be told apart.** The judge and ALM disagree on one trial. To separate two metrics you need about 18–35 *discordant* trials, so new trials should be chosen where the metrics disagree (MAD competition), not drawn at random.
4. **The cheapest big win is calibration.** First fit agreement against margin, using near-tie and high-gain trials with repeats. Then run three short threshold tests (treble excess, 100 Hz, drive) that put the judge's dB on the listener's scale.
5. **Song-only:** the earlier E6/encoder plan regresses onto `unpaired-v3`, which has since been retired. Swap the judge in as the "teacher". Measure every DI-free distance by how well it reproduces the judge's rankings on paired parts.

## 1. Learned perceptual and embedding metrics

- **DPAM** was trained on about 55k crowdsourced "same or different?" judgements, with JND probing by active learning. The material is speech only, with noise, reverb, codec, EQ and dropout perturbations. Music is named as future work. [V] https://arxiv.org/abs/2001.04460 (ar5iv)
- **CDPAM** adds contrastive learning and about 30k triplet judgements so that it handles differences larger than a JND. All nine of its evaluation sets are speech. [V] https://arxiv.org/abs/2102.05109 On human timbre-similarity ratings, CDPAM "does not adapt well to musical timbre". [V] Tian et al. 2025, https://arxiv.org/html/2507.07764
- **Which representations track timbre ratings.** Tian et al. tested 21 datasets (334 sounds, 2,614 ratings). The best was a "style" embedding: the channel mean and standard deviation of CLAP activations (Huang). **MFCC stayed competitive** and beat many trained models, while the multi-scale spectrogram underperformed. [V] Caveat: these are isolated single notes with pitch and loudness equalised, not guitar-amp settings. [V]
- **Text-audio embeddings encode timbre semantics only weakly.** LAION-CLAP was positive on 12 of 16 descriptors with mean r = 0.117. EQ-related terms reached r ≈ 0.19, against about 0.52 for reverb. [V] https://arxiv.org/html/2510.14249 This matters because EQ-like differences are most of what separates presets.
- **FAD on a single pair is the wrong tool.** FAD is a set-level statistic with a sample-size bias (Gui et al. extrapolate it to infinite samples). VGGish "does not correlate well" with music-quality ratings, while CLAP and L-CLAP do best. [V] https://arxiv.org/html/2311.01616
  - **KAD** (unbiased MMD with an RBF kernel and median bandwidth) is stable at N = 100. It correlated better than FAD with ratings at the *system* level, on Foley sounds: −0.93 against −0.80 for PANNs. Music embeddings (MERT, CLAP-music) did worse. [V] https://arxiv.org/html/2502.15602
  - For one 10 s clip, VGGish gives about 10 frames and CLAP 1–2 windows, so FAD cannot be estimated. KAD over MERT frames (about 750 per 10 s) is feasible but noisy. [U: frame counts from the models' known hop sizes]
- **No-reference quality scores (PAM, NOMAD) answer the wrong question.** PAM scores quality from audio–text prompts with no reference. [V] https://arxiv.org/abs/2402.00282 NOMAD measures degradation against non-matching references (label-free, NSIM-guided triplets). [V] https://arxiv.org/abs/2309.16284 Both would rate a clean, wrong tone as excellent.

## 2. Objective quality models (ViSQOL, PEAQ, HAAQI)

- **Torcoli et al.** checked 12 measures against 14 MUSHRA tests (coding and separation).
  - The **2f-model** was best in both domains (ρ = 0.90 for coding). It uses two PEAQ outputs: ADB, which measures distortion in JND units, and AvgModDiff1, which measures differences in loudness-envelope modulation.
  - PEAQ's overall score ranked 8th and ViSQOLAudio 9th.
  - HAAQI was among the top five, despite not being built for coding.
  - The authors warn that results apply to intermediate quality and should not be extended to small impairments without more research. [V] https://arxiv.org/abs/2110.11438
- **ViSQOL v3** compares gammatone-spectrogram patches (NSIM) and maps them to MOS. It was trained on codec data down to 24 kbps and assumes a clean reference. [V] https://arxiv.org/abs/2004.09584 Its README warns that single scores are not very meaningful and should be averaged over many samples, and that it performs poorly outside codecs and VoIP. [V] https://github.com/google/visqol
  - For us: use its per-band similarity (FVNSIM) as a feature, if at all, never its MOS.
- **HAAQI** is the most plausible alternative row. It is intrusive (it needs an aligned reference, which the DI case gives) and built on an auditory model.
  - Its nonlinear term combines cepstral correlation of envelope modulation with fine-structure correlation. Its linear term measures per-band spectral-shape differences.
  - Fitted to normal-hearing and hearing-impaired ratings, it reached r = 0.970. Noise and distortion weigh more than linear filtering. [V] https://pmc.ncbi.nlm.nih.gov/articles/PMC4849486/
  - It is in pyclarity (`compute_haaqi`), runs at 24 kHz and needs a level calibration. [V] https://cadenzachallenge.org/cadenza_tutorials/metrics/haaqi.html
  - Caveat: fitted to *quality*, band-limited to 12 kHz. Worth one row because it weights distortion texture, the judge's unmeasured axis, differently. [U: that this helps]
- **Psychoacoustic scalars.** MoSQITo (Apache-2.0) implements Zwicker loudness, DIN 45692/Aures sharpness, Daniel & Weber/ECMA-418-2 roughness, tonality and fluctuation strength. [V] https://github.com/Eomys/MoSQITo
  - A sharpness difference is a cheap, direct handle on the excess-treble blind spot. [U]

## 3. Metrics from amp/effect modelling and sound matching

- **ESR with pre-emphasis** is the standard amp-modelling loss. An A-weighting pre-emphasis gave the best listening result among the filters tried on a tube-amp model. [V] https://arxiv.org/abs/1911.08922
  - ESR is phase-sensitive. A real mic'd cab against a plugin cab shares no phase, so ESR is meaningless for our real-recording comparisons. [U: reasoning]
  - It also mis-ranked heavy distortion: ESR 0.03 scored a MUSHRA of 57, ESR 2.04 scored 92. [V, next source]
- **Wright, Välimäki & Juvela 2022 (Neural DSP co-author)** reported log-mel L1 (Elmel) alongside MUSHRA. [V] https://arxiv.org/pdf/2211.00943
  - Within a tone, large Elmel gaps (0.28–0.60 against 0.18–0.29) matched large MUSHRA drops (28–54 against 81–89); linear-magnitude spectral models were worst.
  - Gaps under about 0.05 did not predict listeners at any gain. On heavy distortion even a 0.10 gap pointed the wrong way: the best Elmel (0.19, supervised) got the worst score (57).
  - Their mismatched-guitar test is a template for song-only listening: the reference plays *the next few seconds of the music* in the target tone, candidates are rated 0–100 for similarity, with a tanh anchor and no hidden reference.
- **Comunità, Steinmetz & Reiss 2025** ran a MUSHRA test with 27 listeners. [V] https://arxiv.org/html/2502.14405
  - MR-STFT correlated best overall (ρ = −0.427), and best on distortion (−0.536).
  - VGGish-FAD reached −0.592 on distortion and was the most relevant measure on fuzz (−0.511).
  - On compression, no metric was significant.
  - VGGish and AFx-Rep were the best latent metrics overall.
  - So for high gain, an embedding term is the most plausible thing to *add* to the judge.
- **auraloss** (ESR, SI-SDR, MR-STFT with mel and perceptual weighting, FIR pre-emphasis) adds nothing the judge lacks. [V] https://github.com/csteinmetz1/auraloss
- **Sound matching.** Which loss works best depends strongly on the synthesiser. Parameter, spectrogram and listening scores were only moderately consistent (300 trials per combination). [V] https://arxiv.org/abs/2506.22628
  - Spectral distances have a poor sense of pitch, which matters whenever notes differ (song-only). [V] https://mlanthology.org/neuripsw/2020/turian2020neuripsw-im/

## 4. Timbre and distortion psychoacoustics

- **Classic timbre-space dimensions** are spectral centroid (brightness), log attack time, and spectral flux or deviation. Brightness scales with the *raw* centroid, not the centroid relative to f0. [V] McAdams 2019, https://www.mcgill.ca/mpcl/files/mpcl/mcadams_2019_timbreacoustperceptcogn_ch2.pdf
- **In musical phrases, the attack matters less than the spectral envelope.** McAdams writes that "the primacy of attack and legato transients" found with isolated tones "is greatly reduced in whole phrases", where the sustain's spectral envelope dominates. [V, same source]
  - Implication: check on the 46 trials whether the judge's `tonal` term alone agrees as well as the total. [U]
- **Pitch.** Listeners can ignore pitch differences within an octave when judging timbre. Beyond an octave the two interact, and higher pitches shift perceived brightness down. [V, same source] For song-only, compare in matched registers.
- **Distorted guitar.**
  - The first MDS dimension of distortion-effect timbre correlated with Zwicker sharpness. The other dimensions told the processor types apart and were predicted by spectral features after removing tilt (Marui & Martens 2005). [U: abstract via search snippet; their publication list, which I did open, confirms the work: https://www.geidai.ac.jp/~marui/publication/index.html]
- **Ceiling.** Listeners told a Kemper profile from the real amp at d′ = 0.34 (N = 177), "rarely" correct. [V] Düvel et al. 2020, https://d-nb.info/1331543134/34
  - Below some distance differences stop being audible; the second-microphone yardstick is the right unit.

## 5. Different performances (song-only)

- Every DI-free distance must be scored by how well it **reproduces the judge's ranking on paired parts**, where the judge is computable. This is E6's regret metric, with the judge in place of `unpaired-v3`, which was retired after E6 was written. [U: proposal]
  - No listening needed, but it inherits the judge's blind spots.
- **Candidate rows**, cheapest first:
  - MFCC and LTAS statistics (MFCC was competitive on timbre). [V, Tian et al.]
  - Pitch-conditional harmonic envelopes: frames binned by f0 register and level, comparing cepstral envelopes within bins. [U: proposal, motivated by the octave result above]
  - CLAP "Huang-style" mean and standard deviation of activations. [V: best on timbre ratings; untested on amps]
  - KAD over MERT or AFx-Rep frames. [V: KAD properties; U: usefulness here]
- **Content leakage is the main failure.** Spectral losses are poor at pitch [V], and the earlier report already found frame MMD note-sensitive.

## 6. Mixes, stems and level

- **Separation artifacts wreck timbre embeddings.** Retrieval from Demucs stems fell to 14.5% top-1, against 81.7% for a mixture-trained encoder. The material was synthesiser mixtures, not guitar. [V] https://arxiv.org/html/2509.13285
  - For separated audio, Torcoli's 2f-model and its artifacts-only variant SI-SA2f are the measures validated on separation listening tests. [V]
- **Masking.** Glasberg & Moore's partial-loudness model gives each source's audible loudness within a mix. It has been adapted to multitrack masking (MixViz). [V] https://interactiveaudiolab.github.io/assets/papers/FordCartwrightPardo_AES2015.pdf
  - Weighting bands by the guitar's partial loudness in the song is a principled replacement for "bands within 30 dB of the recording's peak". In a sparse arrangement it would also count treble the recording lacks. [U: proposal]
- **Level.** Removing level, as the judge does, is right; keep listening loudness-matched. [U]

## 7. Validating the metric against a listener efficiently

- **Forced-choice pairs** gave the smallest variance and were the most time-efficient of four methods, for a moderate number of conditions. [V] Mantiuk et al. 2012, https://www.cl.cam.ac.uk/~rkm38/pdfs/mantiuk12cfms.pdf Keep R-A-B.
  - MUSHRA with one reference and 3–4 candidates yields 3–6 pair orderings per screen. Use it for song-only, where pairs are scarce. [U]
- **MAD competition** (Wang & Simoncelli 2008) picks the stimuli where two models disagree most and tests only those. The better model is the one whose extreme pairs listeners find easier to tell apart. [V] https://www.cns.nyu.edu/pub/lcv/wang08-preprint.pdf
  - The project already did this against v3c, where the listener sided with the judge on 7 of 9. Do it for every new rival.
- **Active sampling** (ASAP, expected information gain) is the general form. [V] https://arxiv.org/abs/2004.05691
- **Numbers** (my exact binomial calculation, [U] arithmetic):
  - Showing agreement above chance at 77% needs 23 decided trials. At 70%, it needs 42.
  - Comparing two metrics (exact McNemar, one-sided α = 0.05, power 0.8) needs 18 discordant trials if the better one wins 80% of them, 28 at 75% and 42 at 70%.
  - In stage 0b the judge and ALM disagreed on 1 of 24 test pairs, so only trials selected for disagreement are affordable.
- **The listener's ceiling.** If a listener picks the "true" option with probability p, repeated trials agree with probability c = p² + (1−p)², so p = (1+√(2c−1))/2. At c = 0.8 the best any metric can score is about 0.89. Three repeats cannot estimate c; ten can, roughly. [U: derivation]
- **Calibrating the threshold.**
  - Fit a logistic function of P(listener agrees with the judge) against |log ratio|, with a lapse rate, over trials spanning 0.02–0.4. The "clear difference" is the margin where P = 0.75.
  - Stage 0b's flat 8/11 and 9/11 halves cannot place the threshold, because all its trials are above 0.15.
  - psignifit implements Bayesian psychometric fits. [V] https://github.com/wichmann-lab/psignifit
  - Count a "can't tell" answer as its own outcome. Its rate against margin gives a JND for the judge directly. [U]

## 8. Cheap experiments for this project, in order

1. **Alternative rows on the 46 existing trials** (about a day of code, no listening). The rows are:
   - HAAQI (pyclarity, normal-hearing audiogram, the same alignment);
   - the judge plus a sharpness-difference term (MoSQITo);
   - the judge's `tonal` part alone;
   - one embedding row (AFx-Rep or CLAP-style, an optional torch extra).

   Declare the rows first. Report agreement on the 36 decided trials, discordance with the judge on the clear-pair pool, and calls on trials 3, 7 and 15, where all four current measures were wrong. This is screening only: with 36 trials a "win" is noise until a new set confirms it.
   - Gate: take forward any row that disagrees with the judge on at least 10% of clear pairs and agrees on at least the judge's count minus 2.
2. **A MAD round for each surviving rival** (about 40 minutes). Use 30 trials where the judge and the rival each have |log ratio| ≥ 0.15 with opposite signs, plus 6 repeats and 3 hidden references. Decide by an exact binomial on the decided discordant trials, needing 18–23.
3. **The calibration and high-gain round** (about 40 minutes). Use 40 trials stratified over 5 margin bins (0.02–0.4), half on SW50R high-gain renders (outside stage 0b), plus 10 repeats and a "can't tell" option. Fit the psychometric curve separately for clean-to-crunch and high gain. This sets the clear-difference cut used for ties in selection, and the listener's ceiling.
4. **Three threshold staircases** (2-down-1-up, about 6 minutes each):
   - a +x dB octave at 8 kHz (treble excess);
   - +x dB at 100 Hz;
   - +x dB input gain with the spectrum re-matched (drive).

   Comparing the judge's Δ at each threshold shows how it mis-weights them (say 0.1 at the treble threshold against 0.5 at a 1.6 kHz one). The earlier report advised against *per-control* threshold tests; these are three *metric-weighting* checks on axes `measuring-closeness.md` lists as verdict-relevant and unmeasured.
5. **Song-only: the judge as teacher** (no listening, reuses the E6 renders). Score the §5 rows by regret against the judge on paired parts. For a song-only listening test, use Wright's design, and add the true amp track from a different window as a hidden reference with the same tone and different notes.

## 9. What would not help

- Using PEAQ's overall score or ViSQOL's MOS as the closeness number. Both are codec-calibrated, assume a degraded copy of a clean reference, and are documented as weak on single clips. [V]
- DPAM or CDPAM: both speech-trained, and CDPAM is poor on musical timbre. [V]
- No-reference quality scores (PAM, NOMAD), and CLAP text prompts such as "bright". Alignment is weak and EQ-blind (r ≈ 0.19). [V]
- Per-pair FAD with VGGish or CLAP windows: too few frames, and VGGish is poor on music. [V/U]
- ESR, SI-SDR or any waveform measure between a real amp and the plugin. [U: reasoning; V: ESR mis-ranks heavy distortion]
- Linear-magnitude spectral distances. [V]
- More log-mel variants (bands, floors, ALM). Outside near-ties they swap ≤2.5% of pairs, so listening cannot separate them cheaply (the project's own finding). Spend listening on structurally different rivals.
- Fitting or learning a metric on the 46 trials: too few, and they are already used for selection.
