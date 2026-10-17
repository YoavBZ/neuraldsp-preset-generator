# Fix C′'s treble magnitude before adding GANs

*Research report, 2026-10-17, for the ML session's request on recovering short-time high-frequency detail in the DI rebuild. Research, not a declared plan: any run needs its own plan, review and ledger entry.*

No open-source method recovers short-time high-frequency (HF) detail in a way known to improve **ranking**. The battle-tested recipe from vocoders and codecs (HiFi-GAN, BigVGAN, Vocos, DAC, EnCodec) has three parts: a heavily weighted multi-scale log-spectrogram reconstruction loss, a small spectrogram-domain discriminator, and feature matching at weight 2. In those papers, regression losses alone get the spectral envelope right but leave the treble over-smoothed, metallic or buzzy. A sub-band spectrogram discriminator is what restores HF texture. All of that evidence is from **listening**, though, and listening wins (AERO, UnivNet, DAC, Distortion Recovery, EG-VAE) do not carry over to the project's yardstick, rendered local Spearman. The ICASSP 2026 Music Source Restoration (MSR) top two teams used only L1 and multi-resolution STFT (MR-STFT) losses. The repo's own probes are decisive on one point. Restoring the true short-time magnitude recovers the whole gap (+0.313), while restoring the true phase recovers nothing. That makes HiFi-GAN's multi-period discriminator (MPD) the wrong tool, and it is also the costly one: MPD+MSD comes to about 70.7M parameters, and it is what stalled arm 1c. The ranking below runs from most to least expected gain per Mac-hour:

1. The planned offset-removed 2–8 kHz log-magnitude fine-tune.
2. Cheap output-parameterisation changes, chiefly a bounded per-bin log-gain on the STFT of C′'s own output. This is exactly what the `mag` probe tested.
3. Anti-aliased upsampling, Snake or a full-rate path.
4. A small, magnitude-only, band-limited discriminator on sub-crops. This is an **untested inference** built to dodge the MPS STFT bugs.
5. A PANN early-layer feature loss.

Diffusion and flow models are excluded as too costly. No licence-clean guitar de-amping checkpoint exists. Literature GAN fine-tunes run 30k–100k steps, against the repo's 2–5k. This is research to inform a plan; the project's rules still require a declared plan and an independent review before any run.

*Tag: **[I]** marks this report's own inference. Everything else is cited to a primary source or to the repo's committed docs and code. Repo links are relative to this file.*

## Ranking follows short-time treble magnitude, which is what vocoder losses target

### What the repo has already established

C′ is a 9.8M-parameter Demucs-v2-style waveform U-Net with these properties ([`learn/direc.py`](../../learn/direc.py), [di-rebuild-fine-structure-2026-10.md](di-rebuild-fine-structure-2026-10.md)):

- It runs at 48 kHz mono on 3-s crops, and it trains with `100·L1 + MR-STFT` at FFT 256–4096.
- Its 48 kHz waveform comes from **one 8-tap, stride-4 transposed convolution** from 12 kHz features, so it has no full-rate path.
- Its shortest loss window is 5.3 ms, and nothing in the loss is weighted toward 2–8 kHz.

The rebuild-gap study measured C′'s ranking fidelity at **0.541 against a 0.864 ceiling** when it rebuilds from the amp track itself (a perfect stem) ([rebuild-gap-plan.md](../rebuild-gap-plan.md)). Its probes locate the loss ([rebuild-gap-results.md](../rebuild-gap-results.md)):

| Probe (what it restores) | Estimate | Share of the gap |
|---|---|---|
| `mag`: true STFT magnitude at 21 ms, rebuild phase | **+0.313** [+0.146, +0.481] | 1.05 |
| `high`: true signal above 2 kHz | **+0.241** [+0.104, +0.378] | 0.81 |
| `phase`: true phase, rebuild magnitude | −0.031 [−0.071, +0.010] | ≈ 0 |
| `noise`: true DI plus random-phase noise at the rebuild's 16-band frame-level error | +0.276, at the truth | 0.92 |
| `dep_eq`: long-term EQ to the average curve | +0.133 [−0.009, +0.276] | 0.46 |
| `rank`: proxy-ranking fine-tune, against C′ | +0.075 [−0.031, +0.182] | about a quarter |

The study's reading is that the costly error is **"a structured, signal-dependent magnitude error at time scales between 21-ms frames and the long-term spectrum"**. An unstructured error of the same frame-level size costs little. The two long-term fixes do not touch the short-time part: `rank` slightly *raised* the offset-removed 2–8 kHz short-time error, from 8.87 to 8.97 dB ([rebuild-gap-results.md](../rebuild-gap-results.md)). Two caveats limit the `noise` probe. It keeps the true waveform underneath, and it has a much better long-term spectrum (LSD 1.3 dB against 3.3). So it shows that random HF error at the rebuild's level is tolerable *on top of the true signal*. It does not show that any texture with the right band levels will do. Set-3 is the counterweight: boosting incoherent treble by 3–7 dB hurt high-gain and crunch picks ([set3-gap-split-results.md](../set3-gap-split-results.md)).

### What the literature says about HF texture versus envelope

The vocoder and restoration papers describe C′'s symptom almost word for word. UnivNet reports that without its spectrogram discriminator an "over-smoothing problem occurs … most notable in the high-frequency band", with "an audible metallic artifact" (MOS 3.73 against 3.15 without it) ([UnivNet](https://arxiv.org/abs/2106.07889)). DAC says spectrograms "can still appear blurry, exhibiting over-smoothing artifacts in high frequencies". It credits its sub-band discriminator with sharper HF, and its **32-sample, hop-8 loss windows** with "very quick transients" ([DAC](https://arxiv.org/abs/2306.06546)).

The restoration literature points the same way:

- **AERO**, the cleanest loss ablation in bandwidth extension: no discriminator gave the *best* LSD (0.879) but MUSHRA 32.5. Adding discriminators raised MUSHRA to 85.6, and feature matching alone to 77.6 ([AERO](https://arxiv.org/html/2211.12232)).
- **AudioSR** beat NVSR by listening (4.01 against 2.84) despite worse LSD ([AudioSR](https://arxiv.org/html/2309.07314)).
- **DDD**: a regression-only Demucs declipper counted 1.17M waveform extrema against 1.52M in clean audio. Its GAN version restored 1.67M ([DDD](https://arxiv.org/html/2401.03650v1)).
- **StoRM** gives the theory. A regressor converges to the posterior mean, which "will smooth out" onsets and fine detail ([StoRM](https://arxiv.org/html/2212.11851)).

The consensus is that the reconstruction loss fixes the envelope and the adversarial loss fixes texture. No paper measures HF transients directly, and none splits envelope error from fine-structure error.

Three things temper that consensus here. First, **every one of those wins is perceptual**, and the repo has already seen HF metrics improve without ranking following. Arms 1a and 1b cut the 3–8 kHz deficit from −7.4 to −4.7 dB and gap fill by about 11 dB, "with no breakage". They still did not steer the search better than C′ ([di-fine-structure-results.md](../di-fine-structure-results.md)). Second, on broadband mix restoration the GAN entries lost: the **ICASSP 2026 MSR challenge's top two teams used L1 + MR-STFT only**, and the three GAN teams ranked 3rd–5th ([MSR challenge](https://arxiv.org/html/2601.04343v1)). Third, HiFi-GAN's own authors report that fine-tuning raised mel error while raising perceived quality ([HiFi-GAN](https://arxiv.org/pdf/2010.05646)). A GAN can therefore move a magnitude metric the wrong way. [I] The upshot is that a GAN is a plausible next lever for the structured short-time error, but whether it helps ranking is an open question that only rendered ranking can answer.

## Vocoders share one loss template; they differ in window length and discriminator

The official code of the main recipes was read directly. The table gives what each actually ships.

| Recipe (licence) | Reconstruction loss | Discriminators | Weights recon / FM / adv | Notes |
|---|---|---|---|---|
| HiFi-GAN (MIT) | L1 on ln mel, 1 scale | MPD (periods 2–11) + MSD | 45 / 2 / 1, LSGAN | AdamW 2e-4, betas (0.8, 0.99) ([code](https://github.com/jik876/hifi-gan/blob/master/train.py)) |
| BigVGAN v2 (MIT) | log10 mel, 7 scales, windows 32–2048 | MPD + sub-band CQT-D | 15 / 2 / 1 | lr 1e-4; grad clip 500; `--freeze_step` regression warm-up ([config](https://github.com/NVIDIA/BigVGAN/blob/main/configs/bigvgan_v2_44khz_128band_512x.json)) |
| Vocos (MIT) | L1 on ln mel, 1 scale | MPD + multi-band complex MRD | 45 / FM / 1, MRD × 0.1, hinge | Code AdamW betas (0.8, 0.9), lr 5e-4 ([config](https://github.com/gemelo-ai/vocos/blob/main/configs/vocos.yaml)) |
| DAC (MIT code and weights) | log10 mel, 7 scales, windows 32–2048, hop win/4 | MPD + multi-band complex MRD (no MSD) | 15 / 2 / 1, LSGAN in code | D grad clip 10, G clip 1e3 ([base.yml](https://github.com/descriptinc/descript-audio-codec/blob/main/conf/base.yml), [train.py](https://github.com/descriptinc/descript-audio-codec/blob/main/scripts/train.py)) |
| EnCodec (MIT code; audiocraft weights CC-BY-NC) | linear-mel L1 + log-mel L2, windows 32–2048 | MS-STFT (complex), 5 scales | λ_f 1, λ_feat 3, λ_g 3, plus gradient balancer | D updated with p = 2/3 ([paper](https://arxiv.org/abs/2210.13438), [audiocraft](https://github.com/facebookresearch/audiocraft)) |
| Parallel WaveGAN (MIT) | MR-STFT spectral convergence + ln log-mag | WaveNet-style D | λ_adv 4 | D lr half of G's; D off for the first 100k steps ([config](https://github.com/kan-bayashi/ParallelWaveGAN/blob/master/egs/ljspeech/voc1/conf/parallel_wavegan.v1.yaml)) |
| auraloss (Apache-2.0) | STFT / MR-STFT / A-weighting pre-filters | — | — | Building blocks only ([freq.py](https://github.com/csteinmetz1/auraloss/blob/main/auraloss/freq.py)) |

The weights 45 and 15 are the same scale: one natural-log mel scale against seven log10 scales. DAC says it simply rescaled HiFi-GAN's 45 "to account for the multiple scales and log10 base" ([DAC](https://arxiv.org/abs/2306.06546)). No modern recipe still uses spectral convergence. [I] That matters here because SC is dominated by loud, low-frequency bins, which works against a 2–8 kHz emphasis.

Three results bear directly on C′:

- **Short windows matter.** DAC's ablation that replaced the 7 scales with one 512-window mel dropped SI-SDR from 9.12 to 7.68 dB ([DAC](https://arxiv.org/abs/2306.06546)).
- **Linear-frequency STFT distance tracks HF better than mel.** DAC notes it "captures the fidelity in higher frequencies better than the mel distance" ([DAC](https://arxiv.org/abs/2306.06546)). [I] This supports using linear-bin log-magnitude, not mel, for the 2–8 kHz term, since mel gives that band far fewer bins.
- **A cheap spectrogram discriminator is enough without MPD.** EnCodec's MS-STFT discriminator alone scored MUSHRA 77.5 against 79.0 with MPD added. "Including the MPD discriminator, adds a small gain" ([EnCodec](https://arxiv.org/abs/2210.13438)). By contrast, HiFi-GAN without MPD fell from MOS 4.10 to 2.28 ([HiFi-GAN](https://arxiv.org/abs/2010.05646)), but in a mel-to-waveform vocoder, where phase has to be invented.

Artefact cures with code behind them:

| Artefact | Cause | Cure |
|---|---|---|
| Tonal lines | Transposed-conv upsamplers. Pons et al. used **Demucs** as a test case and found "any transposed convolution setup … produces a poor initialization" ([Pons et al.](https://arxiv.org/abs/2010.14356)) | Interpolation-based upsampling; BigVGAN's MIT anti-aliased Snake activations, which "reduce the high-frequency artifacts" ([BigVGAN](https://arxiv.org/abs/2206.04658)) |
| High-frequency patterns in the gradient | Adversarial and deep-feature losses, since CNN losses backpropagate through transposed convolutions ([Pons et al.](https://arxiv.org/abs/2010.14356)) | Keep the regression term dominant [I] |
| Training instability | Discriminator overpowering the generator | Regression warm-up; a lower D learning rate or less frequent D updates; D gradient clipping at 10 ([PWG](https://github.com/kan-bayashi/ParallelWaveGAN/blob/master/egs/ljspeech/voc1/conf/parallel_wavegan.v1.yaml), [EnCodec](https://arxiv.org/abs/2210.13438), [DAC train.py](https://github.com/descriptinc/descript-audio-codec/blob/main/scripts/train.py)) |
| Lopsided loss weights | Fixed weights on very different gradient scales | EnCodec's balancer: SI-SNR 8.41 against −35.83 without it ([EnCodec](https://arxiv.org/html/2210.13438)) |

The architecture evidence is mixed:

- DAC's largest single gain came from replacing ReLU with Snake ([DAC](https://arxiv.org/abs/2306.06546)).
- Vocos found Snake gave "a slight decline" ([Vocos](https://arxiv.org/abs/2306.00814)).
- BigVGAN found that anti-aliased *upsampling* layers caused "significant training instabilities" ([BigVGAN](https://arxiv.org/abs/2206.04658)).

Paper and code disagree in several places, and these matter if anyone copies a recipe from the paper rather than the code:

- **DAC:** the paper says hinge loss, but the released code is LSGAN.
- **Vocos:** the paper says lr 2e-4 with betas (0.9, 0.999); the code uses AdamW (0.8, 0.9) at 5e-4. Its MRD coefficient is 0.1 in the config but 1.0 by code default.
- **BigVGAN:** the `mag_weight` branch compares log mels, which is harmless only because the weight is 0.
- **UnivNet:** has no official code; maum-ai's BSD-3 version is unofficial.

Sources: [DAC loss.py](https://github.com/descriptinc/descript-audio-codec/blob/main/dac/nn/loss.py), [Vocos experiment.py](https://github.com/gemelo-ai/vocos/blob/main/vocos/experiment.py), [BigVGAN loss.py](https://github.com/NVIDIA/BigVGAN/blob/main/loss.py), [univnet README](https://github.com/maum-ai/univnet).

Restoration architectures add one transferable idea: **predict relative to what you already have**.

- **De-limiter:** a 2.35–5.17M network outputs a sigmoid gain on its input. It reached 24.0 dB SI-SDR, against 12.7 dB for direct synthesis, and restored crest factor from 3.66 to 6.48 (true 6.73) ([De-limiter](https://arxiv.org/html/2308.01187v2)).
- **AudioSR:** copies the input's low band back into its output ([AudioSR](https://arxiv.org/html/2309.07314)).

For non-adversarial texture losses the evidence is thin and speech-only. PERL found that a frozen PANN audio-event network's **early layers** raised PESQ from 3.01 to 3.17, while wav2vec 2.0, ASR and speaker features *hurt* ([PERL](https://ar5iv.arxiv.org/html/2010.11860)). Germain et al. beat regression losses with a similar audio-tagging feature loss (MIT code) ([Germain et al.](https://arxiv.org/abs/1806.10522)). No published music-restoration work uses MERT, CLAP or PANN feature losses. Diffusion restorers win mainly at severe degradation, and they cost tens to hundreds of network evaluations. CQT-Diff (15M parameters) took 3 days on an A100 to train and needs 140 steps for declipping ([CQT-Diff](https://ar5iv.labs.arxiv.org/html/2210.15228)). That rules them out on one Mac.

## Guitar de-ampers win listening with generated top ends, but none ships open weights

Every published guitar de-amper that beats a waveform U-Net *perceptually* generates the top end with a GAN vocoder or a GAN-trained codec decoder. Waveform Demucs-family models keep the best waveform fidelity but lose HF detail or leave distortion harmonics behind. That is C′'s profile.

| Method | Losses | What happened to HF | Code / weights / licence |
|---|---|---|---|
| Imort et al., ISMIR 2022 | Batch SDR only, on **16 kHz** audio | Nothing above 8 kHz was modelled. Demucs was best but left "distortion features"; UMX showed "strong phasing artifacts" ([arXiv](https://arxiv.org/pdf/2202.01664)) | Demo page only; code and weights not verified |
| RemFX, WASPAA 2023 | 100·L1 + MR-STFT | Distortion SI-SDR 16.37 → 24.36 dB. Trained on **acoustic** GuitarSet, with no amp data ([arXiv](https://arxiv.org/html/2308.16177)) | Code Apache-2.0; **weights CC-NC** ([Zenodo](https://zenodo.org/api/records/8218621)) |
| Distortion Recovery, DAFx 2024 | Mel L1 denoiser, then HiFi-GAN (LSGAN + mel + FM) | Best FAD and listening (3.54 / 3.86). Demucs V3 kept the best ESR (0.869 against 2.290). Vocoder fine-tuning worsened ESR and MR-STFT ([arXiv](https://arxiv.org/html/2407.16639v1)) | Evaluation code MIT, **no weights**; EGDB/BIAS FX2 test pairs CC BY 4.0 ([Zenodo](https://zenodo.org/api/records/12674910)) |
| SunAFXiNet, DAFx 2024 | MAE + 0.05·MR-STFT | Full-chain dry recovery 1.26 → 5.81 dB SI-SDR ([paper](https://dafx.de/paper-archive/2024/papers/DAFx24_paper_53.pdf)) | No code or weights found; IDMT data CC BY-NC-ND |
| EG-VAE, Aug 2026 | 15·multi-scale mel + 1·adv + 2·FM; MPD + complex STFT discriminator | "Errors concentrate in the high-harmonic region". Won listening on **unseen Morgan presets** (3.69, against HDemucs 3.03 and Distortion Recovery 2.06) ([arXiv](https://arxiv.org/html/2608.05513v1)) | Demo only |
| UnAFx, 2025 | Diffusion EM, or hinge GAN with log-mel discriminators | Estimates the distortion operator; dry recovery not explored. The GAN degrades with less data ([arXiv](https://arxiv.org/html/2504.04751)) | Audio examples only |
| LOUDAR, Aug 2026 | Latent L1/L2 in Music2Latent space | Not discussed ([arXiv](https://arxiv.org/html/2608.01972v1)) | Code MIT; weights tagged MIT but **trained on GOAT, CC BY-NC, restricted** ([Zenodo](https://zenodo.org/api/records/15690894)) |
| MSR U-Former (mix → stem) | L1 for 50k steps, then GAN (λ_adv 0.001, λ_FM 0.01) | U-Net "exhibits deficiencies in high-frequency detail". Electric-guitar SI-SDR −1.25 to −1.68 dB ([arXiv](https://arxiv.org/html/2505.21827v1)) | Weights Apache-2.0; repo has no LICENSE |
| DTT-BSR (MSR team AC_DC) | 45·mel/STFT + 2·hinge + 4·FM, EnCodec discriminator | Guitar MMSNR 1.14; no GAN ablation ([arXiv](https://arxiv.org/html/2602.19825)) | **Code and weights MIT**, 7.1M parameters; outputs a stem, not a DI ([LICENSE](https://raw.githubusercontent.com/OrigamiShido/DTT-BSR/main/LICENSE)) |
| Wolff thesis, TU Berlin 2026 | BigVGAN v2 + Cascaded Gaze denoiser best | Robust zero-shot ([DEGEM](https://www.degem.de/?p=23708)) | No text or code |

**No guitar paper reports a per-band HF error, and none reports "hiss".** HF claims are figures and captions. The listening rankings also conflict. Distortion Recovery beat Demucs in its own test, but scored *below* HDemucs in EG-VAE's ([arXiv](https://arxiv.org/html/2608.05513v1)). So who retrains the baselines decides the result. [I] EG-VAE's unseen set is Morgan, which makes it the closest published proxy for this project. Even it measures listening, not ranking.

### Licences, other tools and datasets

**Licences of other tools:**

| Tool | Licence | Status under the open-only rule |
|---|---|---|
| ST-ITO | Apache-2.0 | Open |
| FxNorm-automix | MIT | Open |
| NablAFx | MIT | Open |
| De-limiter (code, weights) | MIT | Open |
| NLDistortionDiff | No LICENSE file | Flagged |
| DeepAFx-ST | Adobe Research License | **Not OSI**, excluded |
| Apollo | CC BY-SA 4.0 | **Share-alike**, flagged |
| audiocraft weights | CC-BY-NC | **Non-commercial**, excluded |

Sources: [ST-ITO](https://raw.githubusercontent.com/csteinmetz1/st-ito/main/LICENSE), [FxNorm](https://raw.githubusercontent.com/sony/FxNorm-automix/main/LICENSE.md), [NablAFx](https://raw.githubusercontent.com/mcomunita/nablafx/master/LICENSE), [DeepAFx-ST](https://raw.githubusercontent.com/adobe-research/DeepAFx-ST/main/LICENSE), [Apollo](https://raw.githubusercontent.com/JusperLee/Apollo/main/LICENSE), [De-limiter](https://raw.githubusercontent.com/jeonchangbin49/De-limiter/main/LICENSE).

**Openly licensed paired data:**

- **EGDB-PG and EGDB-NDSP**: 256 BIAS FX presets plus Neural DSP renders, CC BY 4.0 ([Zenodo](https://zenodo.org/api/records/19789500)). The licence of the base EGDB DIs was not checked.
- **GUITAR-FX-DIST**: CC BY 4.0 ([Zenodo](https://zenodo.org/api/records/4296040)).

**Excluded data:** GOAT (CC BY-NC, gated) and IDMT-SMT (CC BY-NC-ND).

**ToneTwist AFx.** The amp-inversion notes could not find "ToneTwist AFx" and called the reference unresolved. The repo's docs resolve it. It is a real dry/wet dataset of real analog amps, from Comunità, at [github.com/mcomunita/tonetwist-afx-dataset](https://github.com/mcomunita/tonetwist-afx-dataset). The repo is MIT, and the audio is on Zenodo under **CC BY-NC 4.0** (records 10901426, 10794425 and 10892012). The project has used it only to calibrate gain classes, and the ML plan bars it as open data ([validation-set3.md](../validation-set3.md), [round-4-audio-ml.md](round-4-audio-ml.md), [native-guitar-development-data-2026-10-09.md](native-guitar-development-data-2026-10-09.md), [ml-plan-2026-10.md](ml-plan-2026-10.md)). It is a dataset, not an inversion method. Under the open-only rule it can serve at most as local, NC-flagged test material.

### Corrections to the earlier DI-recovery report

These are corrections to `docs/research/di-recovery-2026-10.md`:

1. **RemFX's guitar** is acoustic GuitarSet with Pedalboard distortion. It contains **no electric-guitar amp data**, so its distortion and conditioning numbers say nothing about amp inversion ([arXiv](https://arxiv.org/html/2308.16177)).
2. **The MSR U-Former is not regression-only.** It adds a HiFi-GAN-style discriminator (λ_adv 0.001, λ_FM 0.01) for 35k steps after 50k L1 steps ([arXiv](https://arxiv.org/html/2505.21827v1)). The challenge finding still verifies: the top two teams used L1 + STFT only ([arXiv](https://arxiv.org/html/2601.04343v1)).
3. **EG-VAE's listening test** ranked Distortion Recovery *lowest*, below HDemucs. That contradicts Distortion Recovery's own ranking ([arXiv](https://arxiv.org/html/2608.05513v1)).
4. **Distortion Recovery** has a CC BY 4.0 EGDB pair set on Zenodo 12674910, even though it has no weights.
5. **DeepAFx-ST**, cited there for proxy gradients, is under the non-OSI Adobe Research License.
6. **Missing items:** SunAFXiNet, UnAFx, the Wolff thesis, DTT-BSR (MIT weights) and EGDB-PG/NDSP.

The later fine-structure report (`docs/research/di-rebuild-fine-structure-2026-10.md`) also needs two updates. The rebuild-gap probes have since shown phase to be worthless for ranking. That demotes its phase-derivative term and its MPD/MSD arm. Its reason for dropping a gain head was that the head would act on the amp's input or on a slow envelope. That reason does not apply to a per-bin *spectral* gain on C′'s own output (see below). [I]

## An MPS-safe discriminator must drop phase, complex numbers and long crops

The vocoder notes recommend one DAC/Vocos multi-band **complex** MRD, about 1.41M parameters. On CPU it measured about 1.6 s per pass, against 4.0 s for MPD and 8.2 s for MSD ([vocoder measurements via BigVGAN/Vocos classes](https://github.com/NVIDIA/BigVGAN/blob/main/discriminators.py)). That design collides with three faults the repo has measured on MPS ([residual-di-plan.md](../residual-di-plan.md), [`learn/direc.py`](../../learn/direc.py)):

- `torch.stft`'s gradient is 34–100% wrong for signals longer than 65,536 samples, and C′'s crops are 144,000 samples.
- Complex `abs` has a NaN gradient near zero, and gradients through complex STFT output went non-finite.
- Matmul on unfolded overlapping frames is wrong even in the forward pass. `clip_grad_norm_` also returns NaN on MPS.

Arm 1c, a full MPD+MSD at C′'s batch of 12 × 144,000 samples, "was stopped twice for memory and then stalled at 0% CPU" ([di-fine-structure-results.md](../di-fine-structure-results.md)). By rough arithmetic, its discriminators cost about 46× C′'s forward pass per audio sample. [I]

The variant below fits both the evidence and the machine. **It is an untested inference.** No published system uses exactly this design, and none of it has been run on MPS.

| Setting | Proposed value | Why |
|---|---|---|
| Discriminator input | **Log-magnitude** spectrogram. Magnitude via the repo's `_magnitude` helper (`sqrt(re² + im² + ε)`), never complex `abs` | `phase` probe ≈ 0; avoids the NaN gradient. UnivNet's MRSD was magnitude-only and still cured HF over-smoothing ([UnivNet](https://arxiv.org/abs/2106.07889)) |
| Bands | Separate heads for **2–4, 4–8 and 8–12 kHz** only (Nyquist fractions 0.083–0.5 at 48 kHz) | Matches `high`. DAC: sub-bands give "a stronger gradient signal" ([DAC](https://arxiv.org/abs/2306.06546)). [I] An 8–12 kHz head watches for fizz |
| Resolutions | Windows 512, 1024 and 2048, hop win/4 | DAC/Vocos MRD sizes; spans the 5–40 ms band the plan targets |
| Where the STFT runs | On the **CPU**, as the existing loss does, with the magnitudes moved to MPS for the conv layers. Fallback: a fixed real cos/sin DFT as a strided conv1d over non-overlapping, copied frames, gradient-checked | Status quo is correct; both MPS alternatives are unverified ([project notes](di-rebuild-fine-structure-2026-10.md)) |
| Crops fed to the discriminator | Random **0.5–1 s sub-crops** (24k–48k samples), possibly half the batch | Below the 65,536-sample bug threshold. Near HiFi-GAN's 8,192 and Vocos's 16,384. Cuts discriminator audio about 4–7× [I] |
| Architecture | DAC-style per-band Conv2d stack: 32 channels, (3, 9) kernels, frequency stride 2, `parametrizations.weight_norm` | About 0.3–1.4M parameters. Avoid UnivNet's no-stride layout, which was slow despite its size |
| Optional | Remove each bin's crop-mean log-magnitude before the discriminator | So it cannot reward an EQ that `dep_eq` already carries [I] |
| Adversarial loss | LSGAN (HiFi-GAN and DAC code) or hinge (Vocos, EnCodec) | Both work in practice |
| Loss weights | Keep reconstruction dominant: **recon ≈ 45 (ln, scale-averaged) or 15 (log10, summed over 7 scales) : FM 2 : adv 1**. C′'s `mrstft` is a scale-averaged ln term at weight 1, so the equivalent is FM ≈ 0.04 and adv ≈ 0.02 against it. MSR's 1 : 0.01 : 0.001 is the conservative end. Better: the EnCodec balancer, or MSG's least-squares equalisation over the first 1k steps | Offset removal shrinks the new loss, so fixed constants will drift ([EnCodec balancer](https://github.com/facebookresearch/encodec/blob/main/encodec/balancer.py), [MSG](https://arxiv.org/pdf/2208.12387)) |
| Optimiser | AdamW, betas (0.8, 0.99). Discriminator lr ≤ the generator's (PWG uses half). Clip the discriminator gradient norm at 10 and the generator's at 1e3, **by hand**. Optionally update the discriminator with p = 2/3 | DAC, PWG and EnCodec; `clip_grad_norm_` is NaN on MPS |
| Warm-up | Start from the C′ checkpoint. Train the discriminator alone for about 500–2k steps with the generator frozen | 1c's plan used 500; community Vocos fine-tunes do the same ([PR #37](https://github.com/kadirnar/drifting-tts/pull/37)) |
| Precision and checks | fp32 only. CPU-against-MPS gradient cosine ≥ 0.99 at the crop length, before training and after 200 steps | Project rule ([di-fine-structure-plan.md](../di-fine-structure-plan.md)) |

**Fine-tune length is the hidden cost.** Literature adversarial fine-tunes from a regression-trained generator run much longer than the repo's 2–5k steps:

- HiFi-GAN fine-tuned for up to 100k steps.
- FINALLY ran 30k adversarial steps after 100k regression steps, then 40k more at 48 kHz.
- MSR ran 35k steps.
- Distortion Recovery fine-tuned its vocoder for 0.5M steps.

Sources: [HiFi-GAN](https://arxiv.org/pdf/2010.05646), [FINALLY](https://arxiv.org/html/2410.05920v2), [MSR U-Former](https://arxiv.org/html/2505.21827v1), [Distortion Recovery](https://arxiv.org/html/2407.16639v1).

The repo's fine-tunes are 1,750–5,150 steps. Stage T ran at about 1.1–1.4 s per step ([rebuild-gap-plan.md](../rebuild-gap-plan.md)). [I] A 5k-step GAN arm risks reading as "no effect" simply because it is undertrained. A GAN plan should declare a learning-curve stopping rule, for example the treble error and the hiss guards logged every 1k steps up to 15–20k steps, rather than a fixed 5k. Assuming a 1.5–2× step-time overhead, which is unmeasured, that is roughly 6–20 h of MPS per fold-arm.

## Five options, ranked by expected ranking gain per Mac-hour

The expected gains are judgements anchored to the probe ceilings: `mag` +0.313, `high` +0.241, `dep_eq` +0.133, `rank` +0.075. No option has published evidence on ranking. Every arm is still judged by TR's design: the arm, a matched-step control, C′, and `rank` beside it, about 2.4k renders ([rebuild-gap-results.md](../rebuild-gap-results.md)).

| Rank | Option | Expected gain | Effort | MPS risk | Licence |
|---|---|---|---|---|---|
| 1 | **Planned fine-tune**: offset-removed log-magnitude L1 on linear bins 2–8 kHz, windows 256–2048 (5–43 ms), hop n/4, energy-gated like the metric (frames within 40 dB of the loudest frame, bins within 60 dB of each frame's loudest bin) or with a 1e-5-style floor. Optionally add DAC-style 64–128 windows | The only option aimed squarely at the residual `high` prices. **Moderate and uncertain**: 1a's short windows moved HF metrics but not steering, and the vocoder literature says regression alone leaves some over-smoothing | **Low.** Existing CPU-STFT path. Computing only the 2–8 kHz bins is about 25% of each DFT [I]. About 1–2 h MPS per fold-arm at 2.5–5k steps | **Low**, given the gradient check | Own code; auraloss Apache-2.0 for an optional A-weighting pre-filter ([Wright & Välimäki](https://ar5iv.arxiv.org/html/1911.08922)) |
| 2 | **Output relative to a signal the net already has.** (a) A bounded per-bin, per-frame log-gain (e.g. tanh-limited to ±12 dB) on the STFT of **C′'s own output**, resynthesised with C′'s phase, zero-initialised so it starts exactly at C′. (b) The same on the *input* STFT, reusing input phase | (a) Its ceiling is the **`mag` probe, the whole gap** (21-ms magnitude, rebuild phase), and it removes the waveform-synthesis burden from the treble fix. (b) De-limiter/AudioSR precedent, but R showed input pass-through keeps the amp's distortion and brightness ([di-rebuild-fine-structure-2026-10.md](di-rebuild-fine-structure-2026-10.md)). **Prefer (a)** [I] | **Medium.** A small head; STFT and iSTFT inside the forward pass; trained with option 1's loss | **Medium.** STFT/iSTFT and their gradients on the CPU. The iSTFT gradient on MPS is unchecked | Own code |
| 3 | **Fix the upsampler**: interpolation + conv, or BigVGAN's Kaiser-sinc anti-aliased Snake, in the last decoder stages; optionally a light full-rate head | **Low to moderate.** It targets tonal and imaging artefacts that Pons et al. show in Demucs, but the 0e overfit reached about 21 dB SNR, so capacity is not the limit. Snake evidence is mixed (DAC gain, Vocos decline) | **Medium-high.** Changes the architecture, so it likely needs retraining: about 6.5 h per fold | **Low-medium.** Elementwise ops and 12-tap filters, but conv and ConvTranspose results have differed from CPU on MPS before ([forum](https://discuss.pytorch.org/t/issue-with-convtranspose1d-on-mps/158164)) | BigVGAN MIT ([act.py](https://github.com/NVIDIA/BigVGAN/blob/main/alias_free_activation/torch/act.py)) |
| 4 | **Magnitude-only, 2–12 kHz multi-band discriminator + feature matching** (the previous section; untested) | **Unknown for ranking.** It is the literature's main cure for over-smoothed HF in listening (UnivNet, DAC, EnCodec, AERO, EG-VAE). Counter-evidence: MSR's L1-only winners, 1a, and the fizz risk through driven amps | **Medium-high.** New code, gradient checks, a discriminator warm-up, and likely 10–20k steps | **Medium-high.** 1c stalled; untested design | Own code modelled on DAC/Vocos (MIT) |
| 5 | **PANN early-layer feature loss** at small weight beside L1/STFT | **Low.** Speech-only evidence (PERL +0.16 PESQ). Its 32 kHz log-mel front end sees little fine treble structure | **Medium.** One large frozen network forward and backward per step | **Medium.** Its spectrogram front end falls under the same CPU-STFT rule [I] | PANN licence not verified in these notes; check before use |

**Excluded:**

- **MPD/MSD (about 70.7M parameters)**: phase-oriented, and it stalled.
- **Shipped complex MRD and MS-STFT discriminators**: they need complex autograd.
- **The BigVGAN-v2 CQT discriminator**: about 29 s per pass on CPU, and it depends on nnAudio.
- **Diffusion and flow restorers (CQT-Diff, StoRM, UNIVERSE++, FlowSE)**: days of A100 time and 35–300 sampling steps.
- **Phase-derivative terms**, after the `phase` probe.
- **Non-open weights**: Apollo (CC BY-SA), RemFX weights (NC), audiocraft weights (CC-BY-NC), LOUDAR (trained on NC GOAT) and DeepAFx-ST (Adobe Research License).

Every arm should pass the same **zero-render HF screen** on held-out training-fold bands before any render. It uses only existing repo metrics ([`fine_metrics` in direc.py](../../learn/direc.py), [rebuild-gap-results.md](../rebuild-gap-results.md), [di-fine-structure-plan.md](../di-fine-structure-plan.md)):

| Metric | C′ baseline | Reads as hiss or artefact when |
|---|---|---|
| Offset-removed short-time treble error, 2–8 kHz | 8.87 dB | It fails to fall, or rises as `rank`'s did (8.97) |
| `hf_3_8k_db`, the 3–8 kHz level error against the true DI | −7.4 dB (1a: −4.7) | **Amended stop rule:** the arm is more than 2 dB brighter than the brighter of C′ and the true DI, i.e. > max(C′, 0) + 2. The original "> C′ + 2 dB" wrongly stopped 1a and 1b for moving toward the truth |
| Gap-frame and quiet-frame 5-ms level | −4.0 dB on gap level (1a: −15.5) | It rises: the network is filling gaps with hiss |
| Coherence, 3–8 kHz | 0.01 | Uninformative for magnitude arms. A GAN can match magnitudes at zero coherence, so read it only beside the treble error |
| Crest error at 1–2.5 ms; LSD 2–8 kHz | Logged per probe | Crest growth means smeared, "phasey" attacks. An LSD rise means an envelope regression |

A spectrogram check for horizontal tonal lines near multiples of 12 kHz (C′'s last stride) would catch Pons-style upsampler artefacts. [I] No repo metric measures musical noise or phasiness directly. Ranking barely reacts to phase, so only a declared listening check would catch phasiness that ranking ignores. The listening runner exists, but its tests compare presets, not rebuilt DIs ([declared-listening-runner.md](../declared-listening-runner.md)).

## Conclusion

The literature and the repo agree on the diagnosis and disagree on the cure. Both see a regressor that gets the treble envelope right and its short-time structure wrong. Vocoders cure that with discriminators judged by listeners. The repo judges by ranking, and by that measure its best evidence (`mag` recovering the whole gap, `phase` nothing) points at a **magnitude-domain** fix. The most interesting new idea follows from that. A zero-initialised per-bin log-gain on C′'s own STFT is the one parameterisation whose ceiling the project has already measured. It can be trained with the planned loss alone, and it would make a later magnitude discriminator easier to add. [I]

Two cautions follow. First, a negative result from a 2–5k-step GAN fine-tune would say little, because published adversarial fine-tunes run an order of magnitude longer. Second, success on the HF metrics is necessary but not sufficient. Arms 1a and 1b already improved them without steering better. That is why the short-time treble error should gate renders, and rendered local Spearman should decide.
