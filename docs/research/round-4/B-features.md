> Input report for `docs/research/round-4-audio-ml.md` (round 4), kept as written. Where the synthesis corrects a claim here after a source check (its §8), the synthesis holds.

# B. Audio features and representations for guitar tone, amp and effect characterisation

Research round, 2026-10-05. Web sources were opened and read, and nothing was downloaded or run. Tags:
- **[verified]**: I opened the source and the claim is in it.
- **[unverified]**: inference, estimate, or a search-snippet claim.
- **[project]**: this repo's docs, code or local files.

The aim is to add to `docs/research/round-1-song-only-matching.md` (round 1), `../round-2-full-plugin-estimation.md` and `../round-3-supervised-preset-model.md`, not to repeat them.

## 0. Bottom line

1. **On these tasks, general pretrained encoders lose to plain MFCC statistics, and fall below chance when content differs.**
   - ST-ITO's zero-shot effect-style test: MFCC statistics 0.74, CLAP 0.56, BEATs 0.59, VGGish 0.50, wav2vec2 0.34, AFx-Rep 0.86 [verified].
   - A 2026 Sony study's cross-instrument retrieval (20-way, chance 5%, every distractor shares the query's content): CLAP 1.0%, MERT 2.6%, VGGish 1.6%, PANN 1.7% [verified]. They match on content, not processing.
2. **Only effect-trained encoders are worth a row:** AFx-Rep, Fx-Encoder++ (non-commercial), RLAT and RelFx, all trained with "same processing, different content" positives. None has been shown to tell knob positions within one guitar amp apart. ST-ITO's authors say their system "does not work well" for guitar tone matching [verified].
3. **The open-set and K3 failures look more like menu and render-to-real (hub) problems than missing features.** Two cheap numpy checks come before any embedding: domain alignment with hubness reduction, and a content-invariance retrieval test on the existing panel.
4. **Amp choice is unlikely to become a recognition problem with any feature.** Presets within one amp sit about as far apart as across amps [project], and learned tone embeddings cluster by gain, not by amp [verified]. Amp choice should come out of render-and-compare.
5. **Through a mix, mid-band EQ and coarse drive should survive; crest, envelope, reverb and high-frequency descriptors should not.** Separation cut an effect embedding's retrieval by about two thirds [verified].

## 1. Why features are only part of the failure

The K2 and K3 recognisers use the following features [project, `scripts/kill_tests.py`]:
- 64-band log-mel, mean (centred) plus standard deviation over active frames, loudness-normalised;
- a 115-dimension "lean fingerprint".

The PR12 failure has three possible causes [project], and only the last two are about features:
- **(a) The menu:** 21 near-duplicate clean presets, where K1's headroom already fell short of the bar.
- **(b) A render-to-real shift:** LDA picks one hub preset on 16–17 of 30 parts.
- **(c) Content leaking into the features:** open-set regret is 3.62–3.68, against 3.38 for the medoid.

No encoder can add what (a) withholds, so expect at most a modest PR12 gain.

## 2. General pretrained encoders

| Model | What the evidence says it captures | Size, licence | On this Mac |
|---|---|---|---|
| **MERT-v1-95M / 330M** | Amplitude-invariant: it normalises in its feature extractor, so loudness is unrecoverable. RT60 decodes well (R² 0.94) [verified]. Embeddings stay "relatively stable" across effect levels, distortion included [verified]. Timbre peaks mid-depth (about 53%), pitch and tonal content earlier (about 30%) [verified]. | 95M, 24 kHz, 75 Hz frames, 12 layers, **CC-BY-NC-4.0** [verified] | Runs in torch on MPS. Local screen only. |
| **MuQ** | Not tested on effects. MuQ-MuLan led the CLAP family on EQ and reverb semantics, but alignment is "limited" overall [verified]. | About 300M, **weights CC-BY-NC 4.0** [verified] | Local screen only. |
| **LAION-CLAP** | Moves in "large, structured" ways under distortion, delay and chorus [verified]. LUFS and RT60 decode linearly (R² 0.92); spectral centroid mostly does not [verified]. Effects are not linearised, and the displacement subspace is high-dimensional [verified]. Scores below MFCCs on effect style [verified]. | Apache-2.0 (`larger_clap_music`) [verified] | Easy. Use as a floor only. |
| **PANNs CNN14 / EfficientAT** | Frozen PANNs plus a linear layer detects effects at 0.70–0.73. Training from scratch reaches 0.75, or 0.786 with SpecAugment (distortion 0.78, compression 0.81) [verified]. AFx-Rep uses a PANNs backbone [verified]. | MIT [verified]. EfficientAT runs from 0.98M (mn04) to 68M (mn40); mn10 reaches 47.1 mAP [verified]. | Cheapest real option: a CPU/MPS CNN. |
| **BEATs, AST, VGGish, OpenL3** | BEATs 0.59 and VGGish 0.50 on ST-ITO's effect style [verified]. OpenL3 moves monotonically but non-linearly with effects [verified]. | BEATs weights on OneDrive [verified]. Others not checked. | OpenL3 and VGGish are TensorFlow-era, so skip them. |
| **wav2vec2, HuBERT, WavLM** | Amplitude-normalised [verified for wav2vec2 and WavLM-L]. Worst on effect style (0.34) [verified]. One exception: a Gram matrix of wav2vec2 layers 4–6, projected to 32 dimensions, retrieved guitar-effect presets far better than CLAP (L2 error 8.05 against 22.3). The authors don't say whether queries and candidates share content, and the code is unreleased [verified]. | Speech models | Not a front end |
| **EnCodec, DAC, music2latent latents** | Built for reconstruction, so they keep content. In a timbre-similarity benchmark, music2latent "aligns better" with human ratings, and MFCC "remains competitive and outperforms many trained models" [verified]. | EnCodec MIT (code) and DAC MIT [verified]; music2latent **CC BY-NC 4.0**, 64 channels at about 10 Hz [verified] | Cheap |

**The useful pattern is the Gram matrix, not the encoder.** Second-order "style" statistics, meaning channel covariances pooled over time, did best in two independent places:
- for timbre similarity, a CLAP Gram embedding was best [verified];
- for guitar-preset retrieval, the wav2vec2 Gram above [verified].

The lean fingerprint already holds an MFCC covariance. Gram statistics of a small CNN's middle layers are the natural next row.

## 3. Effect- and timbre-specific representations

**AFx-Rep (ST-ITO)** [verified]:
- **Training:** a PANNs backbone trained to classify which of 63 VST plugins, and which preset, was applied. The data are about 60 h across seven datasets, GuitarSet included. It embeds mid and side separately.
- **Single-parameter estimation by optimisation, with a different recording as input (content mismatched), AFx-Rep against CLAP (ρ):**
  - MetalTone distortion: 0.862 against 0.509;
  - Distortion drive: 0.944 against 0.852;
  - Compressor threshold: 0.678 against 0.518;
  - Chorus, an effect it never saw in training: 0.408 against 0.300.
- **Caveats:** this is one knob at a time, and generalisation to unseen effects is weak. Morgan is unseen.
- **Availability:** the code is Apache-2.0, but I could not see a weights link.

**RLAT, Sony 2026** [verified]:
- **Design:** a contrastive "processing consistency" loss over a processor library that includes distortion and neural amp models. It runs on frozen Stable Audio Open latents.
- **Retrieval:** 61.1% on average, against AFx-Rep's 45.2% and Fx-Encoder++'s 36.0%; 48.7% cross-instrument.
- **Leakage:** a stem classifier on its embedding still reaches 67–89%.
- **Availability:** the repo returned 404 when I checked, and weights are not stated.

**RelFx, 2026** [verified]: positives are the same effect on adjacent clips of one song section. Dropping that cross-segment sampling made it 34% worse. CLAP and VGGish were worst. No guitar breakdown.

**Guitar-tone encoders** (none has public weights except Open-Amp's framework):
- **Chen et al. (Positive Grid):** SimCLR with "same tone, different playing" positives. Its t-SNE splits into two big cross-amp clusters, high-gain and low-gain [verified].
- **arXiv 2504.07406:** SimCLR over 256 BIAS FX2 tones. The encoder itself is never evaluated [verified].
- **EG-VAE:** 96 unseen Morgan presets form "identifiable but less separated" clusters [verified].
- **Open-Amp:** a 64-dimension SimCLR encoder trained on 160 Proteus captures, classifying devices at 87.9% [verified]. That is device level, not knob level.

**Older guitar-effect recognition:** a 128-band mel CNN separated 13 drive pedals at 86–91%. It confused identical circuits (808/TS9) and low-gain settings (OD1/SD1), which is the "similar clean presets" regime [verified].

**Distortion and dynamics descriptors from wet-only audio:**
- **THD and IMD** are not identifiable without the input. Blind estimation of guitar distortion needs a clean-signal prior and an assumed operator family, and was shown only on plugin distortions [verified, arXiv 2504.04751].
- **Usable proxies** [unverified as drive estimators on real tracks]: spectral flatness between harmonics, the high-band to mid-band ratio, crest factor and attack/decay slopes. All of them depend on picking strength and on the mix bus.

**Cab and mic:**
- In Morgan the cab is tied to the amp and folds into EQ [project].
- Blind estimation reduces to round 1's source-normalised long-term spectrum. I found no guitar-cab-specific blind method.
- The closest analogue is forensic recording-device identification. It recovers fixed-channel fingerprints from content-varied speech using time-averaged spectral statistics (MFCC supervectors, noise spectra), at about 94–98% over 24–141 devices [verified, review]. For us, that fixed linear chain is EQ, cab and mic, not drive.

## 4. Content and performance invariance

What works in the literature is always the training pair, not the architecture:
- same processing on different content counts as a positive (Fx-Encoder, Fx-Encoder++, Chen, RelFx, RLAT) [verified];
- hard negatives that share the query's content (RLAT's cross-instrument condition) [verified].

General encoders fail precisely there, falling below chance [verified].

We have the ideal positive generator already. The panel renders every preset through all 43 development DIs [project]:
- same preset, different DI: a positive;
- same DI, different preset: a content-matched hard negative.

Two warnings:
- **Leakage survives even in trained encoders** (RLAT: 67–89% stem identity).
- **Amplitude-invariant models** (MERT, wav2vec2, WavLM) **erase the input-level cue** that drive needs [verified for the invariance].

For the LDA collapse onto a hub preset, the cheap tools come from retrieval and domain adaptation:
- **CORAL** aligns the second-order statistics of unlabelled target data, here real tracks of training bands only [verified].
- **Local or global scaling** (mutual proximity) cuts hubness and improved music-retrieval quality [verified].
- **Augmenting the within-class scatter** with random mic EQ, room and noise (nuisance attribute projection, from speaker verification) is plausible [unverified].

## 5. Under mixes and separation

- **htdemucs_6s guitar quality:** "okay quality" in the Demucs README [verified]. The open BS-RoFormer guitar models score about 7.1–7.5 dB on MVSep, against 9.0 for BS-RoFormer-SW and Logic Pro [verified].
- **Effect embeddings degrade badly through separation.** Fx-Encoder++ drum R@1 is 19.9% on the true stem, 6.4% on the separated stem and 3.0% direct from the mix [verified]. The authors blame missing high frequencies and transient smearing.
- **Correction to round 1:** StemFX does *not* quantify separation artifacts. It trains on SCNet pseudo-stems and says so as a limitation [verified]. Guitar sits only inside "other".
- **What should survive** [unverified, tested in F4]: the mid-band (200 Hz–4 kHz) long-term spectral shape and coarse drive density. **What should not:** anything above about 5 kHz (cymbals, separation lowpass), crest and attack measures (smearing, bus compression), reverb and decay (mix reverb), and the noise between partials (bleed).

## 6. What would help each decision

**(a) Amp as a categorical choice.** No feature family has shown amp identity independent of settings:
- Chen's embeddings cluster by gain, and Comunità's confusions follow circuit similarity [verified].
- The judge recovers the amp mostly because a close same-amp preset usually exists: within-amp spread 3.09, across amps 3.69 [project].

So use render-and-compare per amp, the amp-reach plan's direction. Song-only, compare each amp's best render through a library DI, scored by whichever distance wins F2. Do not train an amp classifier.

**(b) Continuous settings within an amp.**
- **EQ, cab and mic:** a source-normalised long-term spectrum beats any embedding, which encode EQ weakly [verified].
- **Drive:** level-aware features. The only learned evidence is AFx-Rep's, single-knob and on seen effects.
- **Compression:** weak everywhere (AFx-Rep ρ 0.68). **Time effects:** the existing RT60-type features.

**(c) Closeness.** Paired, the judge stays. Unpaired (song-only), a distance must reproduce the judge's preset ranking when computed against renders through *another* DI; Gram and covariance texture statistics are the leading family. FAD over general embeddings depends on the embedding: PANNs above 0.5 and VGGish below 0.1 on environmental audio [unverified, search snippet]. It is unvalidated for guitar.

## 7. What would not help

- **MERT, MuQ, wav2vec2, HuBERT or WavLM as front ends.** They are amplitude-invariant or stable under effects, below chance cross-content, and mostly non-commercial.
- **Pooled final-layer CLAP, VGGish or PANNs embeddings, or raw EnCodec and DAC latents, as a distance.** They encode content.
- **"Timbre" embeddings such as MERIT,** where timbre means instrument class [verified].
- **Blind THD or IMD, or a separate cab-IR estimate,** from wet song audio.
- **Expecting any feature to rescue the 21-preset clean PR12 menu.**

## 8. Cheap experiments on existing renders (declare gates before reading)

Every experiment uses the existing panels (SW50R 1,978 renders, PR12 clean about 900, AC20 about 1,300), the crops' `reference`, `mix` and `mix_instrumental` files, and the existing folds.
- **Embeddings:** extract them in a venv cloned from `~/ndsp-presets/tools/demucs-venv`, which has torch 2.14 with MPS [project]. That is about 12 h of audio: minutes for the CNNs, perhaps 15–30 minutes for MERT-95M [unverified estimate]. The analysis is numpy and takes seconds.
- **Status:** all exploratory. Adopting anything needs a fresh declared test on held-out parts.

**F2. Content-invariance retrieval** (run first; no labels or judge needed).
- **Setup:** the query is preset *i* through DI *p*. The candidates are preset *i* through DI *q* (another band) plus the panel's other presets through DI *p*. Every distractor shares the query's content, as in RLAT's cross-instrument condition. Chance is 1 in 21 (PR12) or 1 in 44 (SW50R).
- **Rows:**
  - log-mel mean and standard deviation, lean fingerprint, MFCC mean plus covariance, source-normalised long-term spectrum;
  - EfficientAT mn10 mid-block statistics and Gram, PANNs CNN14, DAC latent covariance;
  - CLAP as the floor;
  - AFx-Rep if weights can be obtained, and MERT-95M layers 4–6 with Gram (local only).
- **Gate:** a row goes forward only if its top-1 is at least 2× the log-mel row's on **both** panels.
- **Expectation** [unverified]: general encoders fall below chance; Gram and covariance rows and AFx-Rep beat log-mel.

**F1. Feature swap in K2 and K3.** Re-run K2 (closed and open set) and K3 on SW50R and PR12 with F2's survivors and unchanged recognisers.
- **To beat:** PR12 open-set mean regret 3.62–3.68 (medoid 3.38); SW50R open-set regret ratio 0.80–0.86; PR12 K3 capture of K1 headroom 4–24%.
- **Pass:** PR12 open-set regret below the medoid's, **and** K3 capture at least doubled for 2 of 3 recognisers under both band sets.
- **Honest prior:** about a 20–30% chance on PR12 [unverified]. A failure says features are not the PR12 bottleneck.

**F3. Hub and domain diagnostic.** For log-mel and the F2 winner, measure how often each render is a real track's nearest neighbour and each preset's share of picks. Do it before and after CORAL (fitted on training bands' real tracks only) and mutual proximity. If the most-picked preset falls from 54–57% to under 25% and K3 gains, the render-to-real gap is a cheap normalisation fix that belongs in any model plan.

**F4. Separation survival.**
- **Run:** htdemucs_6s on the 43 parts' `mix_instrumental` (about 10–15 minutes on CPU [project]).
- **Measure, per feature row:** how far the features move from the amp track to the single-guitar `mix` and to the stem, divided by the median distance between presets through the same DI. Below 0.5 counts as surviving.
- **Also:** re-pick K3 presets from the stem and score them with the judge against the amp track. Report single-guitar and multi-guitar parts separately.

**F5. Amp identification without a DI.**
- **Setup:** a 3-way amp classifier, leave-band-out, on all 108 presets × 43 DIs. Report it with presets known to training and with **preset families held out**. As a control, use cross-amp preset pairs that sit closer under the judge than the within-amp median.
- **Gate:** treat the amp as recognisable only if held-out accuracy is at least 0.7 for every amp. Otherwise amp choice stays render-and-compare.
- **Expectation:** high closed-set accuracy driven by factory-preset styling, and held-out accuracy near the judge's fragile SW50R 0.52 [project].

## Sources (opened)

- ST-ITO, AFx-Rep tables and the guitar caveat: https://arxiv.org/html/2410.21233. Code: https://github.com/csteinmetz1/st-ito
- RLAT, design space of audio-transformation representations: https://arxiv.org/html/2608.28127
- RelFx: https://arxiv.org/html/2608.10573
- Fx-Encoder++: https://arxiv.org/html/2507.02273v1 and https://github.com/SonyResearch/Fx-Encoder_PlusPlus
- Probing low-level attributes in CLAP, MERT and others: https://arxiv.org/html/2607.03806
- Audio effects and foundation models (MERT stable, CLAP displaced): https://arxiv.org/html/2509.15151v2
- Deng et al., sensitivity of embeddings to effects: https://arxiv.org/abs/2501.15900
- Tian et al., timbre-similarity alignment: https://arxiv.org/html/2507.07764
- CLAP and timbre semantics: https://arxiv.org/html/2510.14249
- Layer-wise properties of music foundation models: https://arxiv.org/html/2608.14819
- TimberAgent, Gram retrieval of guitar presets: https://arxiv.org/html/2603.09332
- RemFX, effect detection baselines: https://arxiv.org/html/2308.16177
- Chen et al., tone embedding: https://arxiv.org/html/2407.10646
- Tone encoder for transcription: https://arxiv.org/html/2504.07406
- EG-VAE: https://arxiv.org/html/2608.05513v1
- Open-Amp: https://arxiv.org/html/2411.14972v1
- Comunità et al.: https://arxiv.org/html/2012.03216v1
- Unsupervised estimation of nonlinear effects: https://arxiv.org/html/2504.04751
- Hyperbolic effect-chain embeddings (MERT on IDMT guitar): https://arxiv.org/html/2507.20624
- MERIT: https://arxiv.org/html/2605.27346v1
- StemFX: https://arxiv.org/html/2607.15634
- Device-identification review: https://pmc.ncbi.nlm.nih.gov/articles/PMC10137894/
- Hubness, Schnitzer et al.: https://jmlr.org/papers/v13/schnitzer12a.html
- CORAL: https://arxiv.org/abs/1511.05547
- Models:
  - https://huggingface.co/m-a-p/MERT-v1-95M
  - https://huggingface.co/OpenMuQ/MuQ-large-msd-iter
  - https://huggingface.co/laion/larger_clap_music
  - https://github.com/qiuqiangkong/audioset_tagging_cnn
  - https://github.com/fschmid56/EfficientAT
  - https://github.com/microsoft/unilm/tree/master/beats
  - https://github.com/facebookresearch/encodec
  - https://github.com/descriptinc/descript-audio-codec
  - https://github.com/SonyCSLParis/music2latent
- Separation:
  - https://github.com/facebookresearch/demucs
  - https://mvsep.com/quality_checker/leaderboard/guitar
