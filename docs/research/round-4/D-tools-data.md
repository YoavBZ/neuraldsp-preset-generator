> Input report for `docs/research/round-4-audio-ml.md` (round 4), kept as written. Where the synthesis corrects a claim here after a source check (its §8), the synthesis holds.

# D. Tools, models and datasets for tone closeness and settings inference

Researched 2026-10-05. Tags: **[verified]** = I opened the linked source and it says this; **[unverified]** = from search snippets, memory or inference. Nothing was downloaded or installed.

**Already covered earlier (not repeated):** Guitar-TECHS, EGFxSet, IDMT-SMT-Guitar, GOAT, SynthTab, EG-IPT, GuitarSet, EGDB's Zenodo zip, htdemucs_6s, BS-RoFormer-SW, Logic, Moises, StemFX, ST-ITO/AFx-Rep, Fx-Encoder++, Open-Amp, EfficientAT, and PANNs/CLAP/MERT as embedding screens.

## Bottom line

1. **Closeness metric.** No public dataset of human similarity ratings for amp or drive tones turned up. The only open, human-rated timbre benchmark is `timbremetrics`: 21 datasets, 334 sounds, 2,614 pairwise ratings, all orchestral and instrument timbres. On it MFCCs "remain competitive", and CLAP "style" (Gram-matrix) embeddings did best [verified: https://arxiv.org/html/2507.07764, https://github.com/tiianhk/timbremetrics]. It is a cheap floor test for any embedding before it goes near the judge, and nothing more. The user's own listening stays the only amp-tone calibration.
2. **The most useful new datasets:**
   - GUITAR-FX-DIST: CC BY, 14 drive/fuzz plugins with parameter labels.
   - ToneTwist AFx: 12 real amps and preamps plus one parametric Marshall, but CC BY-NC.
   - EGDB-PG: 256 BIAS FX2 amp×cab labels, though the full set's hosting is unconfirmed.

   None of the three adds many new players. The gap in real DIs remains.
3. **Song-only:** "tone removal" (recovering a DI from a wet recording, EG-VAE 2026) and unpaired amp modelling (Wright et al. 2023, Chen et al. 2024) are the research lines that could turn song-only into paired. No weights are confirmed released.
4. **Mac/MPS:**
   - MPS has no float64 or complex128.
   - torchaudio ≥2.9 is in maintenance and needs TorchCodec for I/O.
   - essentia-tensorflow fails to import on arm64 (an open issue).
   - Measure Demucs on CPU against MPS yourself: one source says MPS is about 5× faster for HTDemucs, the same page says the CPU can be up to 10× faster.

## (a) Libraries

| Tool | Licence | Notes |
|---|---|---|
| torchaudio | BSD-2 [verified API] | From 2.9 "transitioned into a maintenance phase"; APIs deprecated in 2.8 are removed in 2.9; `load`/`save` are aliases to TorchCodec [verified: https://docs.pytorch.org/audio/main/torchaudio.html]. Without torchcodec, I/O raises ImportError [unverified: third-party issue]. **Keep soundfile for I/O.** Transforms (MelSpectrogram) are still usable [unverified]. |
| nnAudio | MIT [verified] | GPU/trainable STFT, Mel, CQT, VQT, Gammatone. Original repo is "seeking maintainers"; nnAudio2 (MIT, active Sept 2026) is the successor [verified: https://github.com/KinWaiCheuk/nnAudio]. |
| librosa | ISC [verified: https://github.com/librosa/librosa] | CPU reference features. |
| essentia | **AGPL-3.0** [verified: https://essentia.upf.edu/licensing_information.html] | Model weights are non-commercial, but MTG contradicts itself: CC BY-NC-SA on the models page, CC BY-NC-ND on the licensing page [verified: https://essentia.upf.edu/models.html]. It ships nsynth bright/dark and reverb classifiers. On macOS arm64 `essentia.tensorflow` will not import; issue open since Aug 2025 [verified: https://github.com/MTG/essentia/issues/1486]. **Avoid.** |
| auraloss | Apache-2.0 [verified] | MR-STFT with perceptual weighting, ESR with pre-emphasis, SI-SDR [verified: https://github.com/csteinmetz1/auraloss]. Training losses, not a judge. |
| dasp-pytorch | Apache-2.0 [verified] | Differentiable parametric EQ, distortion, compressor, reverb [verified: https://github.com/csteinmetz1/dasp-pytorch]. Gradient EQ/tilt fits on renders. Last push Dec 2023; MPS untested. |
| fadtk | MIT [verified] | Embeddings: CLAP (MS and LAION), EnCodec, MERT, VGGish, DAC, CDPAM. Per-song FAD; Python >3.10 [verified: https://github.com/microsoft/fadtk]. Chen et al. scored amp tone with VGGish FAD [verified: DAFx24 PDF]. |
| kadtk | MIT [verified] | Kernel Audio Distance, an unbiased finite-sample MMD. Adds PANNs, OpenL3, PaSST; `--indiv` scores each file [verified: https://github.com/YoonjinXD/kadtk]. **Better than FAD for few windows per part.** |
| laion-clap | code CC0-1.0 [verified] | Music checkpoints, 48 kHz [verified: https://github.com/LAION-AI/CLAP]. The HF `larger_clap_music` is Apache-2.0 and loads in transformers `ClapModel` [verified: https://huggingface.co/laion/larger_clap_music]. Checkpoint size [unverified]. |
| MERT-v1-95M | **CC BY-NC 4.0** [verified] | 24 kHz, 13 layers × 768, needs `trust_remote_code` [verified: https://huggingface.co/m-a-p/MERT-v1-95M]. |
| PANNs | code MIT; weights **CC BY 4.0** [verified] | Cnn14_16k 358.7 MB; full collection 5.6 GB [verified: https://zenodo.org/records/3987831]. |
| OpenL3 | code MIT, weights CC BY 4.0 [verified] | Needs TF2 and Python 3.6–3.8, so impractical here [verified: https://github.com/marl/openl3]. |
| pedalboard | **GPL-3.0** [verified] | VST3 and AU on macOS, releases the GIL, arm64 wheels [verified: https://github.com/spotify/pedalboard]. Already an optional `host` extra beside the repo's Swift AU renderer; GPL matters only if bundled. DawDreamer (GPL-3.0) mentions VST but not AU, so it adds nothing [verified: https://github.com/DBraun/DawDreamer]. |
| NAM trainer | MIT, active Aug 2026 [verified API] | Trains .nam from a DI and reamp pair [verified: https://neural-amp-modeler.readthedocs.io]. Useful to run DIs through real-amp captures (below). MPS training [unverified]. |
| Automated-GuitarAmpModelling | GPL-3.0 [verified] | Ships Blackstar HT-1 and Big Muff data in-repo [verified: https://github.com/Alec-Wright/Automated-GuitarAmpModelling]. NablAFx (MIT) is the newer framework [verified API]. |
| Demucs | MIT, **archived** Apr 2024 [verified API] | Demucs-GUI's notes say MPS is "about 5×" faster for HTDemucs, yet recommend the CPU "to speed up up to 10×" [verified: https://github.com/CarlGao4/Demucs-Gui/blob/main/usage.md]. Contradictory, so **benchmark on this Mac.** |
| audio-separator | MIT [verified] | Demucs, MDX and RoFormer models; MPS for .pth, CoreML for .onnx; lists htdemucs_6s guitar. Per-model weight licences not stated [verified: https://github.com/nomadkaraoke/python-audio-separator]. |
| MVSep Mega-53 guitar BS-RoFormer | claimed MIT [verified: HF card] | A 77.5 MB fp16 conversion of ZFTurbo's v1.0.21 checkpoint; the card says MIT, "no separate weight restrictions" [verified: https://huggingface.co/lumabeat/mvsep-mega53-guitar]. That is a third-party claim, so confirm in ZFTurbo's release. It could replace BS-RoFormer-SW, whose licence is unknown. |

**MPS gotchas:**
- No float64 or complex128 on MPS; only float32 and cfloat are supported [verified: https://github.com/pytorch/pytorch/issues/148670]. Compute STFTs in float32.
- Conv1d/Conv2d with more than 65,536 output channels once gave silently wrong results on MPS [verified: https://github.com/pytorch/pytorch/issues/129207]. It now raises an error, and `PYTORCH_ENABLE_MPS_FALLBACK=1` does not rescue it [verified: https://github.com/pytorch/pytorch/issues/134416].
- Always check MPS outputs against the CPU once per model.

## (b) Datasets

| Dataset | Licence / size | What it adds | Download, and why |
|---|---|---|---|
| **GUITAR-FX-DIST** (Comunità 2021) | **CC BY 4.0**; ~22.5 GB in ~2.1 GB zips [verified: https://zenodo.org/records/4296040] | 14 overdrive, distortion and fuzz effects with continuous and discrete parameter labels. Clean recordings: 624 mono notes and 420 poly. 2 guitars (Schecter, Strat). About 0.57 h clean against ~111 h rendered [verified: Chen et al. DAFx24 Table 1]. Plugins only, no amp or cab; player count [unverified]. | **One "Mono Continuous" zip (~2.1 GB):** tests whether a drive estimator or encoder resolves *settings* on another vendor's drives. It is CC BY, so it can feed shipped (Tier A) weights. |
| **ToneTwist AFx** (Comunità/Steinmetz/Reiss) | Audio **CC BY-NC 4.0** (Zenodo); repo MIT. Dry set 417.6 MB, 43 min [verified: https://zenodo.org/records/10901426] | Real devices: Blackstar HT1/HT5, Engl Retro Tube 50, Fender Blues Jr, Ibanez TSA15, Mesa 5:50 and Mark V (3 channels each), UA 6176, and one **parametric Marshall JVM410H**. Controls are labelled 0–10 in file names [verified: https://github.com/mcomunita/tonetwist-afx-dataset]. Its dry signal comes mostly from IDMT, so it adds no players. | **Dry + JVM410H + 2–3 amps (sizes [unverified]):** the only open real-amp captures with labelled controls found here. Local-only test of plugin-trained models on real amps. |
| **EGDB-PG** | Paper: 256 presets (16 amps × 16 cabs), 514 h, labelled low-gain/crunch/high-gain [verified: https://arxiv.org/html/2504.07406]. Zenodo has only a 1.0 GB random-preset zip, CC BY [verified: https://zenodo.org/records/12674910]. Hosting of the full set [unverified]. | Labels from another vendor. EGDB DIs: 1 professional player, 118 min, re-rendered via Guitar Rig 5 [verified: arXiv 2202.09907 PDF]. The DI licence is still unstated (the Google Drive link has no licence) [verified: https://ss12f32v.github.io/Guitar-Transcription/]. | Ask the authors for the full EGDB-PG and the DI licence. Worth it as a cross-vendor test of "amp class from audio". |
| GOAT (prior) | CC BY 4.0, but by request and research-only; 5.9 h DI, 4 guitars, 2 authors + 2 creators [verified: https://arxiv.org/html/2509.22655v1] | **New detail:** its amp renders used ~7,000 NAM profiles from more than 1,000 amps, plus cab IRs from Neural DSP's Archetype Nolly [verified]. That is a precedent for NAM augmentation. | Request access. It adds players. |
| **TONE3000 / NAM captures** | Each capture has a licence field (`t3k`, cc-by, cc-by-nc, cc0, …). The free API tier is non-commercial only; paid products need a signed agreement [verified: https://www.tone3000.com/api]. Library size [unverified; a blog says 700k]. | Real-amp tones beyond Neural DSP. Captures are models, not audio: run the dev DIs through them. Open-Amp used 160 GuitarML Proteus captures (GPL-3.0 repo), 65 of them gain-conditioned [verified: https://arxiv.org/html/2411.14972v1]. | The API needs an account (the user's to create). Filter to cc-by/cc0. Worth it for a real-amp robustness set. |
| MoisesDB | **CC BY-NC-SA**, research only; 240 tracks, 14.4 h. Guitar sub-stems: acoustic / clean electric / **distorted electric** [verified: https://ar5iv.labs.arxiv.org/html/2307.15913] | Real mixes with clean-or-distorted electric labels, but no DIs. | Register, then download through its Python library (size [unverified]). Use it for a song→stem→"is it driven" check. |
| MedleyDB 2.0 | CC BY-NC-SA, on request [verified: https://zenodo.org/records/1715175] | Raw tracks; guitar DIs among them [unverified]. | Check metadata first. |
| MUSDB18 | No guitar stem; **100 of 150 tracks come from DSD100, i.e. the Mixing Secrets (Cambridge) library** [verified: https://sigsep.github.io/datasets/musdb.html] | Overlap risk: separators trained on MUSDB18 may have seen Cambridge sessions. | No download; compare its public track list against the held-out sessions. |
| GuitarSet | Use v1.1: CC BY 4.0, 8.2 GB [verified: https://zenodo.org/records/3371780]; record 1422265 shows CC BY-NC [verified]. | Acoustic. | Content diversity only. |
| EGFxSet (prior) | **New detail:** the effects were recorded at the interface line input, so pedals only, no amp [verified: https://egfxset.github.io/]. | | |
| Semantic Timbre Dataset (guitar) | CC BY 4.0. 275,310 notes, 19 descriptors ("fuzzy", "bright") at magnitudes 0–100 via Guitar Rig 7. Validated by MOS from 20 listeners. Zenodo subset 1.0 GB [verified: https://arxiv.org/html/2603.16682v1, https://zenodo.org/records/11398253] | Words to effect intensity: suits `edit` more than matching. | Optional. |

## (c) Listening-test tooling and perceptual data

- **webMUSHRA:** custom MIT-like licence. Supports MUSHRA, BS.1116 A/B, forced and unforced choice, Likert; needs a PHP or Python (pymushra) backend [verified: https://github.com/audiolabs/webMUSHRA, https://openresearchsoftware.metajnl.com/articles/10.5334/jors.187]. **Neural DSP's own amp-model paper used it, modified for DMOS:** 30 expert listeners rated 1–5 closeness to a reference, with a 3.5 kHz low-pass as the low anchor and LUFS-matched samples [verified: https://arxiv.org/pdf/2403.08559]. That protocol is the one to copy if the listening ever goes beyond one listener. Their ratings and the robot-collected 4.5 h DC-30 dataset are not released [verified: no link in the paper].
- **Go Listen:** MIT. MUSHRA, ACR, A/B, ABC/HR; Docker + MongoDB, or free hosting at golisten.ucd.ie [verified: https://github.com/QxLabIreland/listening-test].
- **jsPsych:** MIT, active [verified API]. The best fit for the project's custom "which is closer to the amp track" 2AFC trials and any Prolific study. Headphone screening: McDermott HeadphoneCheck, BSD-2 [verified API]; the Huggins-pitch test of Milne et al. 2021 [unverified details].
- BeaqleJS and WAET: both GPL-3.0, last pushed 2019 and 2021 [verified API].
- **Perceptual data:**
  - ODAQ: MUSHRA ratings on 240 samples × 26 listeners for codec and separation artefacts; mixed CC BY / BY-NC / CC0; 1.0 GB [verified: https://zenodo.org/records/10405774]. Usable only to calibrate how much separation artefact the judge tolerates.
  - Düvel et al. 2020 (Kemper profiles against real amps): discrimination near chance [unverified; page returned 403].
  - Joint language-audio embeddings align weakly with timbre words: the best, LAION-CLAP, had mean r=0.117, and EQ was encoded less reliably than reverb [verified: https://arxiv.org/html/2510.14249].

## (d) Other practical items

- **RemFx:** Apache-2.0. Effect *classifier* plus removal models for chorus, delay, distortion, compression and reverb; weights on Zenodo; trained partly on GuitarSet [verified: https://github.com/mhrice/RemFx]. Accuracy is not given in the README. It could gate the time-effect detectors.
- **Unpaired / song-only modelling:**
  - Wright, Välimäki & Juvela 2023: an adversarial amp model learned from a recording alone, judged by a MUSHRA test [verified: arXiv 2211.00943 PDF].
  - Chen et al. DAFx24: a GAN using unaligned clean data, scored with FAD-VGGish and mel-L1 [verified: DAFx24 PDF].
  - Diffusion against adversarial blind estimation of distortion, DAFx25 [verified: https://arxiv.org/abs/2504.04751].
  - **EG-VAE (Aug 2026): tone transfer and tone *removal* (wet → DI)** [verified: https://arxiv.org/abs/2608.05513]; whether code is released is [unverified]. If a removal model works on stems, song-only could reuse the paired-DI pipeline. Worth watching.

## Downloads that would need approval, ranked

1. `timbremetrics` (git clone; bundles the audio of 21 rating datasets; size [unverified], likely small). It vets any embedding before it enters the judge.
2. One GUITAR-FX-DIST zip (~2.1 GB, CC BY): labelled drive settings from another vendor, and shippable.
3. ToneTwist dry set (418 MB) plus the JVM410H record and 2–3 amp records (CC BY-NC, local only): a real-amp generalisation test.
4. The EGDB BIAS FX2 zip (1.0 GB, CC BY), and a request to the authors for the full EGDB-PG and the DI licence.
5. MoisesDB (registration; non-commercial): a test of real mixes with distorted-or-clean labels.
6. Model weights, only if the supervised plan's embedding screen runs:
   - PANNs Cnn14 (~330–360 MB, CC BY);
   - the LAION-CLAP music checkpoint (CC0 / Apache);
   - MERT-95M (non-commercial);
   - the MVSep guitar RoFormer (77.5 MB, MIT per a third-party card).
7. A TONE3000 account and API key (the user creates it), for cc-by/cc0 NAM captures as a real-amp augmentation set.
