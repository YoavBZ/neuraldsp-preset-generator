# C1: Report C claims, checked against primary sources

Checked 14 Oct 2026. Sources: arXiv abstract/HTML/PDF pages, the Zenodo REST API (`/api/records/<id>`), Zenodo archive previews, and raw GitHub files or shallow `git clone`s. Report C is `69c7ad87-deep-research-report-2.md`; "C:NN" means a line in it.

Status codes:

- **CONFIRMED:** the source says this.
- **CORRECTED:** a number or condition is wrong.
- **MISLEADING:** true as written, but a missing condition changes how it should be read.
- **NOT FOUND:** no source could be located or opened.

[I] marks my inference. Already settled elsewhere and not redone here: ST-ITO, prior-ITO (2505.11315), Basic Pitch, the NAM trainer, the Fx-Encoder++ licence, and Open-Amp being unlicensed.

## Decision-relevant corrections (read first)

1. **ToneTwist audio is CC BY-NC 4.0 throughout.** The audit Report C asks for ("Do not ingest wholesale until every constituent recording licence is audited", C:490) is done here.
   - All **42 of 42** Zenodo records linked from the README carry `cc-by-nc-4.0` (about 73.1 GB).
   - The MIT `LICENSE` file covers "this software and associated documentation files". The README says nothing about audio rights.
   - The dry inputs include IDMT material (CC BY-NC-ND 4.0), "Private Guitar Data" and "YouTube Bass Recordings (10:09 min)".
   - **Decision:** treat ToneTwist audio as excluded from the permissive path. The only open question is whether it may be used for NC development at all.
   - Knock-on: NablAFx code is MIT, but its paper models were trained on this NC data. [I] Any weights trained the same way inherit that problem.
2. **BE-AFX's "audio loss beats parameter loss" holds only for EQ and the full chain.** For the **compressor and the clipper**, parameter-supervised training won on *both* audio and parameter metrics. The paper's words: "leads to better results both in terms of audio quality (L_Mel = 0.069, 0.064) and parameter estimation (MSE = 0.069, 0.028)". The clipper is the closest analogue to guitar distortion, so Report C's "optimise the sound, not the knobs" (C:80) is weaker evidence for nonlinear stages than it implies. Keep acoustic equivalence as the primary metric (still sensible), but don't cite BE-AFX as showing that parameter supervision hurts audio match for distortion.
3. **Guitar-TECHS does have three players, but only one plays music.**
   - P3 contributes the 12 musical excerpts: 8 min 02 s, about 2.6% of 5:12:02. P1 and P2 recorded only techniques, chords and scales.
   - Each player also used a different guitar, amp, mic and room, so player and rig are fully confounded.
   - The project's "one player" note (`docs/validation-datasets.md:155`) is right for the `P3_music` subset it actually uses as songs.
   - Report C's "now documents three players" (C:503, C:566) is not new: arXiv v1 (Jan 2025) already says three.
   - **Decision:** this barely helps a player-invariance test on *music*. P1 vs P2 on identical exercises is the only matched-content comparison.
4. **The Marshall JVM410H "one performance" is wrong. The hold is justified.**
   - The input is "a 6-min-long dataset of guitar **and bass** audio files of different playing styles and genres … All the sounds were taken from IDMT datasets" (DAFx23 paper §2.1).
   - The Zenodo record's description does **not** mention the DI source at all.
   - Every one of the 37 setting folders includes the IDMT-derived `*-input.wav`. The IDMT-SMT-Guitar and IDMT-SMT-Bass records are `cc-by-nc-nd-4.0`, so the CC BY 4.0 label can't be relied on for that material.
   - The ToneTwist repack of the same data (10892012) is CC BY-NC 4.0.
5. **Open-Amp's 99.8% on Open30 is in-distribution, not a transfer result.**
   - Open30 is "30 randomly selected devices from the Proteus Tone Pack … using data from the IDMT transcription dataset as input". That is the same device pool and DI source the Open-Amp encoder was trained on.
   - Report C lists it among "cross-dataset effect-classification experiments" (C:90).
   - The genuine transfer figures are GFX 91.8, EGFX 72.0 and EGDB 91.1. Even there, the MLP probe is fit on each target dataset.
6. **Two more datasets have the same IDMT upstream conflict.** Neither changes a current plan.
   - GUITAR-FX-DIST (the Comunità 2021 data) is CC BY 4.0 on Zenodo, but it was built from IDMT-SMT-Audio-Effects (Zenodo 7544032, `cc-by-nc-nd-4.0`).
   - The Comunità 2021 code is BSD-3-Clause.

Smaller points (no decision changes):

- The Sound2Synth hill-climbing (21.96) and genetic-algorithm baselines are "obtained from APVST [Yee-King et al., 2018]". They were not re-run on Sound2Synth's test set.
- NablAFx's listening test covered fixed-setting pedals and compressors only, with **no amplifier**. Its one amp (JVM410H) appears only in the objective, parametric experiment.
- NablAFx metadata conflicts: the LICENSE file is MIT, but the pyproject classifier says Apache.
- DiffMoog's non-convexity evidence concerns **oscillator frequency and FM index**, with all other parameters held at ground truth. That is pitch-type parameters, not gain/EQ-type ones.

---

## 1. Guitar-TECHS (arXiv 2501.03720; guitar-techs.github.io; Zenodo 14963133)

| # | Claim (Report C) | Status | Exact quote / number | Source | Note |
|---|---|---|---|---|---|
| 1a | "three professional players, not one" (C:494, 503, 566) | CONFIRMED, but MISLEADING as a player-diversity asset | Paper §III: "The dataset consists of guitar content by three professional players (Player 01, Player 02, & Player 03), each recording on separate dates. Player 01 and Player 02 contributed recordings of various scales, chords, and tone-playing techniques, while **Player 03 focused solely on music excerpts**." Table II: Musical Excerpts 0 / 0 / 12, 00:08:02; Grand Total 1860 / 1860 / 12 | [arXiv HTML](https://arxiv.org/html/2501.03720), [site](https://guitar-techs.github.io/), [Zenodo API](https://zenodo.org/api/records/14963133) | Hardware differs per player: P1 Ibanez PF300 / Orange CR-60 / SM57; P2 EVH Wolfgang / **Yamaha YB15 bass amp** / AT2020; P3 Sire T7 / Orange CR-12 / ECM8000. "All amplifiers were set to a flat EQ". The project's "one player" (`docs/validation-datasets.md:41,155`) refers to `P3_music` and is correct for it. The brief's "one player, clean bass amp" (`_brief.md:115`) mixes P2's amp with P3's music. "Now documents" is wrong: v1, 7 Jan 2025, already says three |
| 1b | CC BY 4.0 | CONFIRMED | Zenodo `license: cc-by-4.0`, `access_right: open`. Site: "All data is licensed under a Creative Commons Attribution 4.0 License (CC BY 4.0)". Paper: "with a permissive CC BY 4.0 license" | same | Published 2025-04-06; 9 zips, 4.13 GB |
| 1c | About 5 h 12 min | CONFIRMED | Table II "Grand Total … 05:12:02" (identical on the site) | same | The duration counts each signal once, not × 4 signals. P1+P2 = 5:04:00 of exercises; P3 = 0:08:02 of music |
| 1d | DI + amplified/mic signals for all players | CONFIRMED | Every zip has `audio/directinput/` and `audio/micamp/` with equal counts: P1_chords 28/28, P2_chords 28/28, P1_scales 12/12, P2_scales 12/12, P1_techniques 5/5, P2_techniques 5/5, P1/P2_singlenotes 1/1, P3_music 12/12; plus `video/ego`, `video/exo` mp3 | [Zenodo previews](https://zenodo.org/records/14963133/preview/P3_music.zip) | Zenodo note: "Signals may exhibit ≤100ms misalignment due to recording setup" |

## 2. ToneTwist AFx dataset (github.com/mcomunita/tonetwist-afx-dataset)

| # | Claim (Report C) | Status | Exact quote / number | Source | Note |
|---|---|---|---|---|---|
| 2a | Repository `LICENSE` is MIT (C:490, 501) | CONFIRMED | "MIT License / Copyright (c) 2025 Marco Comunità / … this software and associated documentation files (the "Software")" | [LICENSE (master)](https://raw.githubusercontent.com/mcomunita/tonetwist-afx-dataset/master/LICENSE) | Added in commit "Create LICENSE" on 2025-02-18; last commit 2025-02-24. "Now carries" means since Feb 2025. The default branch is `master` (`main/LICENSE` returns 404) |
| 2b | MIT "does not by itself prove all aggregated audio has MIT rights" | CONFIRMED (understated) | The README has no audio-licence statement. It says: "This repo contains also links to external sources (i.e., data recorded by others …)"; "Attributions to the original authors are included"; "If you find your work published here and you are not happy, feel free to contact us." Dry inputs: IDMT-SMT-GUITAR ds2 (7:23), ds4 Career SG (6:08), ds4 Ibanez 2820 (5:14), IDMT-SMT-Bass-Single-Track (5:58), NAM (3:11), "Private Guitar Data - (5:19 min)", "YouTube Bass Recordings - (10:09 min)" | [README](https://github.com/mcomunita/tonetwist-afx-dataset/blob/master/README.md) | Upstream IDMT-SMT-Guitar (Zenodo 7544110) and IDMT-SMT-Bass-Single-Track (7544099) are `cc-by-nc-nd-4.0`. YouTube and private sources have no stated rights |
| 2c | Is the audio on Zenodo with its own licence? | **CORRECTED (decision)**: yes, and every record is NC | Every one of the **42** records linked from the README (dry-input records 10455730 and 10901426, 28 analog, the JVM410H repack 10892012, and the digital and digital-parametric sets) returns `license: cc-by-nc-4.0`, `open`. Total about **73.1 GB**. Example titles: "ToneTwist AFx Dataset: Dry with markers"; "ToneTwist AFx Dataset - External: Marshall JVM410H - Channel: OD1" | Zenodo API, e.g. [10455730](https://zenodo.org/api/records/10455730), [10892012](https://zenodo.org/api/records/10892012) | README links use `zenodo.org/uploads/<id>`; the public form is `/records/<id>`, used in `scripts/urls-*.yaml`. The JVM repack is NC although its source 7970723 says BY. Report C's "audit first" should be replaced by "all NC: excluded from the permissive path" |

## 3. Sound2Synth (arXiv 2205.03043; github.com/Sound2Synth/Sound2Synth)

| # | Claim (Report C) | Status | Exact quote / number | Source | Note |
|---|---|---|---|---|---|
| 3a | 155 Dexed params: 87 continuous, 66 categorical, 2 fixed | CONFIRMED | §3: "155 parameters … 87 continuous parameters, 66 discrete parameters, and 2 fixed parameters (Algorithm and Output)". App. A: "All continuous parameters are discretized into 64 classes" | [arXiv HTML](https://arxiv.org/html/2205.03043) (v2, IJCAI-22) | So every output is a classification head |
| 3b | MFCCD 6.32 / 5.36 vs PresetGen VAE 14.70 vs hill climbing 21.96 | CONFIRMED (numbers), with a caveat | Table 1: "*Hill Climbing 21.96; *Genetic Algorithm 31.32; APVST MLP 31.38; APVST LSTM 32.76; APVST LSTM++ 22.59; PresetGen VAE 14.70; *Similarity Threshold 10∼15 for Human Perception; Sound2Synth 6.32; Sound2Synth multi-modal 5.36". Footnote: "* These figures obtained from APVST [Yee-King et al., 2018]." | [PDF v2](https://arxiv.org/pdf/2205.03043v2) | The hill-climbing and GA numbers are borrowed from a 2018 paper, not re-run on this test set. Test set: 1,679 presets from "independent held-out themes"; train/val 30,106 (6,191 real, 22,237 augmented, 1,678 random). Fixed input: "middle C … maximum velocity, sustained for 4 beats, … 8 beats … 120 bpm" |
| 3c | No repository licence | CONFIRMED | No LICENSE or COPYING file in the tree; only ref is `main` @ 44d9176 (2022-07-28, "ijcai publish"). `PyAU/README.txt`: "PyAU … is a closed-source python library … We do not have the right to hold and public PyAU" | [repo](https://github.com/Sound2Synth/Sound2Synth) (git clone) | Also needs macOS ≥ 10.13 and a remote GPU server for training |
| 3d | Checkpoints not released | CONFIRMED | README: "Pre-trained checkpoints may be released in the future." and "Trained checkpoints … will be uploaded soon." No tags or releases | same | `server/app.py` raises `FileNotFoundError` without `experiment/<name>/checkpoints/latest` |

## 4. FlowSynth (arXiv 1907.00971; github.com/acids-ircam/flow_synthesizer)

| # | Claim (Report C) | Status | Exact quote / number | Source | Note |
|---|---|---|---|---|---|
| 4a | Repo MIT | CONFIRMED | "MIT License / Copyright (c) 2019 acids-ircam" | [repo](https://github.com/acids-ircam/flow_synthesizer) (HEAD 47abcca, 2020-08-03) | Pre-trained models ship in `code/results` (C doesn't mention this). The dataset is on IRCAM Nubo; its licence was not checked |
| 4b | Uses commercial Diva | CONFIRMED | Paper §4.1: "an off-the-shelf commercial synthesizer Diva developed by U-He". README: "Have an installed version of the Diva VST (The system works with the free tryout version but will produce noise every now and then)" | [PDF](https://arxiv.org/pdf/1907.00971), README | ~11k presets; "We only kept continuous parameters"; sets of 16, 32 and 64 params, with results reported for 16 and 32. The plugin also needs Max/MSP (bach, dada, MuBu) and Ableton Live; "only been tested on MacOS X High Sierra (10.13.6)" |

## 5. BE-AFX, Peladeau & Peeters (arXiv 2310.11781v2)

| # | Claim (Report C) | Status | Exact quote / number | Source | Note |
|---|---|---|---|---|---|
| 5a | Audio-loss training gives a better audio match but worse parameter error (C:80, 349, 457, 688) | CONFIRMED for EQ and the full chain; **MISLEADING as a general result** | Abstract: "our auto-encoder approach yields superior estimates of the audio quality produced by a chain of AFXs, compared to the traditional parameter-based approach, even if the latter provides a more accurate parameter estimation." §3.4.3: "These contrasting outcomes underscore that achieving accurate parameter estimation (p̂ ≈ p) does not guarantee high audio quality (ŷ ≈ y)." | [arXiv HTML](https://arxiv.org/html/2310.11781) | — |
| 5b | Numbers (Table 5) | — | Columns: trained on L_Mel → MSE(ŷ,y) / L_Mel / MSE(q̂,q) ‖ trained on MSE(q̂,q) → same three. **Eq.** 0.28 / **0.32** / 0.089 ‖ 0.27 / 0.40 / **0.072**. **Comp.** 0.011 / 0.076 / 0.11 ‖ **0.0081 / 0.069 / 0.069**. **Clip.** 0.0045 / 0.072 / 0.044 ‖ **0.0041 / 0.064 / 0.028**. **Chain** **0.31 / 0.40** / 0.10 ‖ 0.33 / 0.49 / **0.072** | same | Text: "For compression and clipping, training by minimizing the parameter distance (MSE q̂,q) leads to better results both in terms of audio quality (L_Mel = 0.069, 0.064) and parameter estimation (MSE = 0.069, 0.028)." On EQ, waveform MSE also slightly favours parameter training (0.27 vs 0.28). Setup: synthetic EQ → compressor → clipper on 10-s mono MUSDB18 mix clips, q ~ U(0,1). No listening test ("Further work will focus on performing subjective perceptual experiments") |

## 6. Comunità, Stowell & Reiss 2021 (arXiv 2012.03216; JAES 69(7/8))

| # | Claim (Report C) | Status | Exact quote / number | Source | Note |
|---|---|---|---|---|---|
| 6a | Classification > 80% over 13 effects | CONFIRMED | Abstract: "13 overdrive, distortion and fuzz guitar effects … Classification accuracy was above 80%". Table 4 range **81.3–91.4%** (in-domain 86.3 / 90.9 / 88.4 / 91.4) | [arXiv](https://arxiv.org/abs/2012.03216), [PDF](https://arxiv.org/pdf/2012.03216) | The 13 are **VST plug-ins** (10 from Audified MultiDrive Pedal Pro, plus Mercuriall Greed Smasher, Analog Obsession Pig Pie, Zupaa), not hardware |
| 6b | MAE < 0.05 in 12 of 16; RMSE < 0.1 except one | CONFIRMED | "In the majority of cases (12 out of 16) the MAE is below 0.05 and for all cases except one, the RMSE is below 0.1." The one exception is Tone/Eq, Mono Cont. → Mono Disc., RMSE 0.108 | PDF Table 6 | "16" = 8 train/test pairings × 2 controls, not 16 knob settings. Estimation uses SetNetCond, "**conditioned on the effect class ground truth**". At most 2 estimated controls (Gain, Tone); Level fixed at 1.0. Input: 2-s single notes and chords |
| 6c | Gain MAE ≈ 0.040, tone ≈ 0.038 | CONFIRMED | Table 6 "Avg 0.040 (0.060) 0.038 (0.066)" (MAE (RMSE), Gain then Tone/Eq) | same | — |
| 6d | ~250 h processed | CONFIRMED | "a total of about 250 hours"; discrete ≈ 110 h (~200,000 clips), continuous ≈ 140 h (260,000 clips) | same | Dry source: IDMT-SMT-Audio-Effects |
| 6e | Code licence ("not fully re-audited", C:487) | Now audited | `gfx_classifier` and `gfx_classifier_models_and_results`: **BSD 3-Clause** ("Copyright (c) 2020, mcomunita"). Data GUITAR-FX-DIST: Zenodo 4296040 / 4298000 / 4298017 / 4298025, all `cc-by-4.0` (22.5 / 26.8 / 23.2 / 18.5 GB) | raw GitHub LICENSE; Zenodo API | Upstream IDMT-SMT-Audio-Effects is Zenodo 7544032 `cc-by-nc-nd-4.0`: the same BY-over-NC-ND conflict as the JVM set |

## 7. NablAFx (arXiv 2502.14405; github.com/mcomunita/nablafx)

| # | Claim (Report C) | Status | Exact quote / number | Source | Note |
|---|---|---|---|---|---|
| 7a | Repo licence MIT | CONFIRMED (metadata inconsistent) | LICENSE (master): "MIT License / Copyright (c) 2025 Marco Comunità". `pyproject.toml`: `license = {file = "LICENSE"}`, but its classifier says "License :: OSI Approved :: Apache Software License". PyPI `nablafx` 1.0.0 license field = MIT text | [LICENSE](https://raw.githubusercontent.com/mcomunita/nablafx/master/LICENSE), [pyproject](https://raw.githubusercontent.com/mcomunita/nablafx/master/pyproject.toml), PyPI JSON | Both are permissive; [I] the LICENSE file governs. Last commit 2025-11-08 ("update version"). The README examples use `CUDA_VISIBLE_DEVICES`; no MPS mention (consistent with C:227). The paper's training data (ToneTwist) is NC (item 2) |
| 7b | Subjective test: state-space models strongest; TCN/conv competitive | CONFIRMED | §6.3: "subjective ratings confirm the results obtained during the training process, with S4 architectures performing best, followed by convolutional backbones, gray-box models and LSTMs." "S4 models remain the most consistent, with median ratings at or above 80 in all but one case." §7: "state-space models are the most suited to model a wide range of devices, with TCN and GCN architectures also achieving very good results." | [arXiv HTML](https://arxiv.org/html/2502.14405) | MUSHRA with 27 recruited participants, 350 valid ratings after screening. 12 of the 16 **non-parametric** devices (comp/limiter, overdrive, distortion, fuzz): **no amplifier was rated**. The amp (JVM410H OD1) appears only in the objective parametric experiment: "S4 models are the best performing on the guitar amp, with LSTM models and TCN with time-varying conditioning performing only marginally worse" (test gain fixed at 5) |
| 7c | Objective metrics have "only moderate" correlation with ratings | CONFIRMED (generous) | Table 8 overall Spearman ρ from −0.303 (FAD PANN) to −0.430 (FAD VGGish); MR-STFT −0.427. Compressor/limiter: \|ρ\| ≤ 0.194, with ESR and MAPE not significant | same | "Weak-to-moderate" is more accurate |
| 7d | "nonlinear amplifiers/distortion/compressors can be emulated … across multiple devices" (C:225) | MISLEADING (minor) | Multiple devices: 4 compressor/limiter, 4 overdrive, 4 distortion, 4 fuzz. Amplifiers: **one** (JVM410H, parametric) | Table 4 | — |

## 8. DiffMoog (Uzrad, Barkan, Elharar, Shvartzman, Laufer, Wolf, Koenigstein; arXiv 2401.12570, 23 Jan 2024)

| # | Claim (Report C) | Status | Exact quote / number | Source | Note |
|---|---|---|---|---|---|
| 8a | Substantial non-convergence | CONFIRMED | §4: "Evaluating DiffMoog for sound matching has been a challenging journey, encountering non-convergence in many experiments." "While the complexities led to a focus on key findings rather than exhaustive experimental details…" | [arXiv HTML](https://arxiv.org/html/2401.12570) | Qualitative only: no convergence rates reported |
| 8b | Signal-chain loss alone fails systematically; FM chains hard | CONFIRMED | "Using the signal-chain loss solely failed systematically, However, when applied to a relatively basic synthesizer chain (Fig. 5), training with the spectral signal-chain loss after using the parameter loss hinted superior performance over the sole usage of parameters loss on out-of-domain data". "more complex chains utilizing FM modulations refused to converge, adding up to the already hard task of frequency estimation using spectral loss [Turian & Henry]" | same | The partial positive (parameter loss, then spectral loss, on a simple chain) is omitted in C |
| 8c | Highly non-convex spectral-loss landscapes | CONFIRMED, scope MISLEADING | Fig. 7: "Loss surface for frequency and modulation index, illustrating highly non-convex behavior with many local minima … Other synth parameters are fixed to their ground truth." Table 1: gradient-direction accuracy 0.45–0.75 across loss configurations (Wasserstein-on-time best) | same | The landscape evidence is about **oscillator frequency and FM index**, which spectral losses are known to handle badly. [I] It is an analogy for amp gain/EQ, not direct evidence. The project's own "coupled valley" measurements are the stronger evidence |

## 9. Fx-Encoder++ (arXiv 2507.02273)

| # | Claim (Report C) | Status | Exact quote / number | Source | Note |
|---|---|---|---|---|---|
| 9a | R@10 39.4 oracle → 20.5 MSS → 9.9 USS | CONFIRMED | Table 3 (MUSDB18, instrument-wise), Fx-Encoder++ row: Target Instrument (Oracle) R@1 19.9, R@5 33.0, **R@10 39.4**, mAP@10 25.6. USS / MSS: R@1 2.1 / 7.1, R@5 6.4 / 15.4, **R@10 9.9 / 20.5**, mAP 4.0 / 10.8. Direct extraction from the mixture (audio / text query): R@10 11.7 / 12.2. Text: "USS-based methods suffer significant performance drops (9.9% R@10), while MSS performs better (20.5% R@10) but is limited to only four predefined stems … (approximately 19% lower), indicating that separation artifacts may distort the effects characteristics." | [arXiv HTML](https://arxiv.org/html/2507.02273) | The conditions: MSS = **Hybrid Demucs** (Défossez 2021; vocals/bass/drums/other, so guitar sits inside "other"). USS = Kong et al. 2023. Retrieval among **500 candidates**; synthetic effect chains (dasp-pytorch, torchcomp). "19% lower" is percentage points (−48% relative). Fx-Encoder++ on raw mixtures (11.7) is *worse* than separate-then-encode with MSS (20.5). MedleyDB: oracle 28.8 vs USS 7.0 |

## 10. Open-Amp (arXiv 2411.14972)

| # | Claim (Report C) | Status | Exact quote / number | Source | Note |
|---|---|---|---|---|---|
| 10a | 59 amp + 101 pedal captures | CONFIRMED | "we used the 'Proteus Tone Packs' collection from the Guitar ML tone library. This collection of models consists of 59 guitar amplifier captures and 101 effects pedal captures. Sixty-five of the models include a single parameter, typically the gain, as a conditioning parameter." | [arXiv HTML](https://arxiv.org/html/2411.14972) | "Hundreds of synthetic devices" (C:485) = 394, for the one-to-many emulation TCN: "treated as five separate models … resulting in a total of 394 synthetic devices" |
| 10b | 99.8% on Open30, cited as cross-dataset (C:90) | CONFIRMED number; **MISLEADING** as transfer | Table II, Open-Amp row: GFX 91.8, EGFX 72.0, EGDB 91.1, **Open30 99.8**. "'Open30', a dataset consisting of guitar audio processed by 30 randomly selected devices from the Proteus Tone Pack, synthesised using Open-Amp … using data from the IDMT transcription dataset as input." Encoder training: "unprocessed electric guitar audio from the IDMT-Guitar transcription dataset … as input." | same | Open30 uses the same device pool and DI source as encoder training; no held-out devices are stated, so it is in-distribution. Probe: "single-layer MLP classifier … If the training and test sets are from the same dataset, a random class-balanced train-test split of 85-15". The classes are **device identity**, not settings. Table II's Open-Amp encoder was trained for 100k iterations |

## 11. Marshall JVM410H (Zenodo 7970723)

| # | Claim (Report C) | Status | Exact quote / number | Source | Note |
|---|---|---|---|---|---|
| 11a | CC BY 4.0 | CONFIRMED (label) | `license: cc-by-4.0`, `open`, published 2023-05-25. Creators: Miklánek, Wright, Välimäki, Schimmel | [Zenodo API](https://zenodo.org/api/records/7970723) | — |
| 11b | ~4.4 GB | CONFIRMED | `MarshallJVM410H.zip` 4,369,237,770 bytes (4.37 GB / 4.07 GiB) | same | — |
| 11c | "one performance across multiple amp settings" (C:495, 566) | **CORRECTED** | DAFx23 §2.1: "we composed a 6-min-long dataset of guitar and bass audio files of different playing styles and genres … All the sounds were taken from IDMT datasets described in [32, 33]." The archive has 37 setting folders (28 `final/` + 9 `test/`), each with `-input`, `-preamp` and `-speakerout` WAVs | [paper PDF](https://www.pure.ed.ac.uk/ws/portalfiles/portal/408428956/Wright2023DAFX23NeuralGrey.pdf), [archive preview](https://zenodo.org/records/7970723/preview/MarshallJVM410H.zip) | It is one *fixed input compilation* re-amped per setting, not one performance, and it includes bass. Settings: 21 tone-stack settings at gain 5 (paper), plus a gain sweep G0/1/2/4/6/8/10 that is in the archive but not described in the paper. Folder `B5_M5_T5_G6` holds files named `…G4…`, already flagged by the project (`docs/research/native-guitar-development-data-2026-10-09.md:44`) |
| 11d | DI source per the Zenodo description; is the project's hold justified? | **Hold justified** | Zenodo description in full: "Audio dataset used in the DAFx23 paper Neural Grey-Box Guitar Amplifier Modelling with Limited Data GitHub repository: https://github.com/stepanmk/grey-box-amp/ Listening page: https://stepanmk.github.io/grey-box-amp/". **No DI source is named.** The source is only in the paper: [32] Abeßer et al., DAFx-13 (IDMT bass) and [33] Kehling et al., DAFx-14 (IDMT-SMT-Guitar). Upstream records: IDMT-SMT-Guitar 7544110, IDMT-SMT-Bass 7188892 and IDMT-SMT-Bass-Single-Track 7544099 are all `cc-by-nc-nd-4.0` | Zenodo API; [Zenodo search](https://zenodo.org/api/records?q=IDMT-SMT) | The archive redistributes the IDMT-derived DI verbatim (`*-input.wav` in every folder) and adapted amp outputs under BY. [I] NC-ND inputs can't be relicensed to BY by a downstream uploader, so the BY label isn't evidence of permission. The `grey-box-amp` repo has no LICENSE (404 on main and master). The ToneTwist repack 10892012 is CC BY-NC 4.0. The paper's own CC BY 4.0 notice covers the article, not the data |
