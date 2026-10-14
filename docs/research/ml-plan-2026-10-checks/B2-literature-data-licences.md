# B2: Literature, dataset and licence fact-check (Reports A and B)

Checked 14 Oct 2026 against primary sources: arXiv HTML, Zenodo REST API records, raw GitHub files, Hugging Face model APIs and cards, and official sites. Status codes:

- **CONFIRMED:** the source says this.
- **CORRECTED:** a number or condition is wrong.
- **MISLEADING:** true as written but missing a condition that changes the reading.
- **NOT FOUND:** no source could be located or opened.

[I] marks my inference.

## Decision-changing corrections (read first)

1. **EGDB-NDSP is not a check of the Tone King Imperial MKII plugin.** The EGDB demo page heads that section "Transcription on Neural DSP **Quad Cortex** rendered audio" and lists "Tone King Imperium, Rhythm Channel". Neither Neural DSP nor Tone King sells anything called "Imperium": `neuraldsp.com/plugins/tone-king-imperium` returns 404, and the only product is "Tone King Imperial MKII". Neural DSP's own plugin page still says it "will be compatible with Quad Cortex and Quad Cortex mini in a future CorOS update." The Quad Cortex got Tone King Imperial MKII *Neural Captures* in CorOS 2.0 (Guitar World, 30 Jan 2023). [I] "Imperium" is therefore a mislabel, and the render is almost certainly a Quad Cortex capture, not the plugin. **Drop the plan to use EGDB-NDSP to sanity-check the project's Tone King render pipeline** (Report A §4 table).
2. **GuitarToneAdapt is a much weaker prior than Report B implies.**
   - 473 of 1,252 entries (37.8%) have **no sources**. Only 756 have a numeric confidence; 496 carry strings ("medium" 473, "high" 23).
   - Only 47.3% of entries have confidence ≥ 0.7.
   - There is **no "crunch" label** in the data, despite the site listing one.
   - For the test songs there is **one Hotel California entry, the solo only**, and **no Long Road Out of Eden entry**.
   - Use it only as a filtered, weak prior, and log the Hotel California entry as test-song metadata to avoid leakage. Full profile below.
3. **Distortion Recovery's "SI-SDR 28.65 dB" is very probably a sign error.**
   - The same row has ESR 2.290: error energy is more than twice the signal, which is about what an *uncorrelated* output of equal energy gives (ESR ≈ 2).
   - The authors' public evaluation script uses `auraloss.time.SISDRLoss`, whose docstring says "Note that this returns the negative of the SI-SDR."
   - [I] The true SI-SDR is about −28.7 dB, which means the mel-plus-vocoder output keeps no waveform or phase.
   - Do not cite 28 dB as evidence for waveform fidelity. The result is *consistent* with the project's finding that its DAC codes are phase-sensitive.
4. **EG-VAE's objective gains are small; its edge is perceptual. Its latent is not the released DAC.**
   - Report B's "best removal baseline 1.21 → 1.10 (seen)" repeats the paper's own introduction, but Table II shows **DPTNet at 1.19 on seen tones**, so the true margin is 1.10 vs 1.19. On unseen tones it is 1.19 vs 1.22 (Distortion Recovery).
   - EG-VAE uses a self-trained DAC-VAE (the Movie Gen formulation) with **hop 1920 (~23 frames/s)** and a 1024-d latent. Report A's E1′ targets the released DAC 44 kHz model (hop 512, ~86 frames/s). EG-VAE results do not transfer to E1′ directly.
5. **Kammoun et al.'s continuous-latent win comes from the training target, not from unquantised decoding.** Their continuous predictions "are quantized before being passed to the NAC decoder". The setup is speech only (Libri1Mix) with DAC 16 kHz. Report A's E1′ rationale should say "continuous regression target" rather than "continuous latent decoding".
6. **Webb's "fewer than eleven clusters" applies to the conventional weight choices.** The same abstract proposes a 6-point weight distribution as the fix. If the wild-cluster bootstrap is used at all, use Webb weights; otherwise the Bayesian and TOST plan stands.

Smaller corrections (none of these changes a decision):

- Banquet's SNR ranges are wider than quoted.
- EG-IPT has 52,320 *files*, not notes.
- GuitarFlow is significantly more realistic than Guitar Pro once both go through an amp.
- Distortion Recovery has a public evaluation repo (MIT) and a CC BY 4.0 EGDB render set (Zenodo 12674910, 1.04 GB). It has no model code or weights.
- SynthTab's LICENSE file and README conflict.
- GOAT's amp renders total 29.5 h; the 25.85 h figure covers standard tuning only.

## 1–3: DI-recovery literature

| # | Claim | Status | Exact quote / number | Source | Note |
|---|---|---|---|---|---|
| 1a | A: EG-VAE on 96 unseen Morgan presets: Mel 1.19 vs DPTNet 1.27 vs DR 1.22; AQ 3.69 / Dry 3.50 vs true DI 4.50 / 4.39 | CONFIRMED | Table II, unseen (Morgan Amps Suite): EG-VAE Mel 1.19±0.28, STFT 1.87, AQ 3.69±0.86, Dry 3.50±0.74. DPTNet 1.27±0.37 (AQ 2.67, Dry 2.31). DR 1.22±0.34, STFT **1.86** (AQ 2.06, Dry 2.11). Oracle 4.50±0.74 / 4.39±0.77. "96 for Morgan Amps Suite" | [arXiv 2608.05513](https://arxiv.org/html/2608.05513) | 14 listeners. The closest unseen Mel baseline is DR (1.22), not DPTNet, and DR is marginally better on STFT. The large gap is in MOS, not Mel |
| 1b | A: trained on 758 h of Neural DSP + EGDB-PG renders | CONFIRMED | "256+218=474 seen tones, yielding approximately 1.6×474≈758 hours". EGDB DIs are "roughly 2 hours", split 80/5/15 | same | The earlier note (`di_recovery_and_separation.md`) says EGDB is "about 22 h" of DI. Wrong: it is ~2 h. EGDB-PG tones are BIAS FX2 (Positive Grid) |
| 1c | B: "44% Mel-distance improvement over strongest transfer baseline on seen tones" | CONFIRMED | "reduces the Mel spectral distance of EGTT by 44% … (One-to-many with EGTR … 0.86 vs. 1.53 on seen tones)" | same | Transfer task, not removal |
| 1d | B: removal "1.21 → 1.10 Mel on seen tones, matching it on unseen" | MISLEADING | Paper intro: "improves over the best EGTR model (i.e., 'Distortion Recovery', 1.10 vs. 1.21 Mel on seen tones, matching on unseen)". Table II, seen: **DPTNet 1.19**, DR 1.21 | same | Faithful to the paper's text, but the table contradicts "best". The best seen-tone Mel baseline is DPTNet (1.19). On unseen tones EG-VAE leads on Mel (1.19 vs 1.22) and matches DR only on STFT (1.87 vs 1.86) |
| 1e | B: demo uses Morgan Amps Suite as unseen tone | CONFIRMED | Demo: "unseen tones … (Morgan Amps Suite)"; seen = Archetype: Cory Wong X | [demo](https://guitar-tone-demo.vercel.app/) | The demo abstract is softer: removal "remains competitive with models" |
| 1f | Continuous DAC-VAE latents? | CONFIRMED | "EG-VAE adapts the DAC-VAE [33], the VAE-version of DAC codec". Encoder rates [2,8,10,12], "hop length of 1920", 44.1 kHz. Bottleneck "at dimension 128 before projecting back to the 1024-dimensional latent". Tone embedding 64-d | [arXiv](https://arxiv.org/html/2608.05513) | Ref [33] is Movie Gen. The model is trained by the authors on guitar renders; there is no sign it uses the released DAC weights [I]. Gaussian latents, no RVQ |
| 1g | No code or weights (A) | CONFIRMED (as of 14 Oct 2026) | arXiv v1 only (6 Aug 2026). Demo page shows a placeholder, "BibTex Code Here", and no repo link. No HF models match "eg-vae"/"egvae"; the HF paper page returns 404 | arXiv abs, demo, HF API | GitHub search API was blocked in this session; web search found no repo |
| 2a | DR listening 3.54 / 3.86 vs 4.25 / 4.29 | CONFIRMED | Ours-Large AQ 3.54±1.10, DL 3.86±1.08. Ground truth 4.25±0.89 / 4.29±0.95. "26 professional guitarists and music producers" | [arXiv 2407.16639](https://arxiv.org/html/2407.16639) | Training data was BIAS FX2 ToneCloud presets with no time effects |
| 2b | DR SI-SDR ~28 dB | MISLEADING | Table 1: "SISDR ↑ 28.650", but **ESR 2.290** in the same row. Eval code: `self.sisdr = SISDRLoss()`. auraloss: "Note that this returns the negative of the SI-SDR" | [paper](https://arxiv.org/html/2407.16639), [test.py](https://raw.githubusercontent.com/y10ab1/guitar_effect_removal/main/test.py), [auraloss](https://raw.githubusercontent.com/csteinmetz1/auraloss/main/auraloss/time.py) | [I] The reported value is most likely −SI-SDR, so true SI-SDR ≈ −28.7 dB. The EGDB demo table has the same pattern ("SISDR 30.241" with ESR 1.574) |
| 2c | DR weights? | CONFIRMED none / CORRECTED "no code" | README: "repository contains code for evaluating the recovery…" (metrics only). LICENSE: MIT | [repo README](https://raw.githubusercontent.com/y10ab1/guitar_effect_removal/main/README.md); [Zenodo 12674910](https://zenodo.org/records/12674910) | No model code or weights. Bonus: Zenodo 12674910, "EGDB Dataset Rendered with the Positive Grid BIAS FX2 Plugin", **CC BY 4.0, 1.04 GB, open**. Published at DAFx 2024 |
| 3 | Kammoun: continuous vs tokens, UTMOS 3.54 vs 2.72 | CONFIRMED | Table 1: C-NAR UTMOS 3.54 vs D-NAR 2.72 (C-AR 3.61, D-AR 2.76). "on average, +0.80 UTMOS" | [arXiv 2510.26299v3](https://arxiv.org/html/2510.26299v3) | DAC **16 kHz**, 12 RVQ, L=1024, 50 Hz; speech (Libri1Mix). "For continuous-prediction models, the estimated vectors are quantized before being passed to the NAC decoder." C-NAR dWER 13.48 is worse than DPTNet's 10.75 |

## 4–7: Codecs, vocoders, separators

| # | Claim | Status | Exact quote / number | Source | Note |
|---|---|---|---|---|---|
| 4a | DAC MIT for code and weights | CONFIRMED | LICENSE "MIT License … Descript". README: "Weights are released as part of this repo under MIT license." | [README](https://raw.githubusercontent.com/descriptinc/descript-audio-codec/main/README.md) | — |
| 4b | 44.1 kHz: 1024-d at ~86 frames/s | CONFIRMED | `encoder_rates [2,4,8,8]` gives hop 512, so 44100/512 = 86.13 Hz. `latent_dim = encoder_dim * 2**len(encoder_rates)` = 64·16 = 1024 | [dac.py](https://raw.githubusercontent.com/descriptinc/descript-audio-codec/main/dac/model/dac.py), [44khz.yml](https://raw.githubusercontent.com/descriptinc/descript-audio-codec/main/conf/final/44khz.yml) | "Continuous 4-codebook latent" mixes up two things. The pre-quantiser latent is 1024-d and independent of codebook count; the sum of the first 4 quantised codes is also 1024-d |
| 4c | 9 codebooks? | CONFIRMED (default model) | 44khz 8 kbps: `n_codebooks: 9`, size 1024, codebook_dim 8. The 44khz 16 kbps model has `n_codebooks: 18` | configs above | 24 kHz model: 32 codebooks; 16 kHz model: 12 |
| 5 | BigVGAN-v2 44 kHz 128-band 512x: MIT; trained incl. music/instruments | CONFIRMED (wording) | Card: `license: mit`. "trained using datasets containing diverse audio types, including speech in multiple languages, environmental sounds, and instruments". Dataset "Large-scale Compilation", 122M params, 5M steps | [card](https://huggingface.co/nvidia/bigvgan_v2_44khz_128band_512x), [repo LICENSE](https://raw.githubusercontent.com/NVIDIA/BigVGAN/main/LICENSE) | The card says "instruments", not "music" |
| 6a | EnCodec 48 kHz weights licence | CONFIRMED (as A describes) | HF `facebook/encodec_48khz`: `license: mit`. `encodec_24khz`: no licence tag. GitHub: "The code in this repository is released under the MIT license" | [48k card](https://huggingface.co/facebook/encodec_48khz), [README](https://raw.githubusercontent.com/facebookresearch/encodec/main/README.md) | The 48 kHz model is "trained on music-only data", stereo |
| 6b | Music2Latent CC BY-NC | CONFIRMED | README: "released under the CC BY-NC 4.0 license". LICENSE is CC BY-NC 4.0. HF card `cc-by-nc-4.0` | [repo (master)](https://raw.githubusercontent.com/SonyCSLParis/music2latent/master/README.md) | — |
| 6c | Stable Audio Open VAE licence and gating | CONFIRMED | HF: `license: other`, `license_name: stable-audio-community`, `gated: auto`, "By clicking 'Agree', you agree to the License Agreement" | [HF API](https://huggingface.co/api/models/stabilityai/stable-audio-open-1.0) | Same for stable-audio-open-small (`stability-ai-community`) |
| 7a | htdemucs_6s MIT; guitar quality | CONFIRMED (repo-level) | "Demucs is released under the MIT license". "Quick testing seems to show okay quality for `guitar`, but a lot of bleeding and artifacts for the `piano` source." | [README](https://raw.githubusercontent.com/facebookresearch/demucs/main/README.md) | There is no separate weights licence. In Banquet's Table 3 on MoisesDB, HT-Demucs guitar median SNR is **2.4 dB** vs oracle IRM 5.2 |
| 7b | Banquet: clean electric 0.6–0.9 dB vs distorted 2.4–2.8 dB median SNR | CORRECTED | Table 4 (8 trainable-encoder configs), median: clean E. Gtr **0.4–1.1**; distorted **2.4–3.0**; acoustic 1.7–1.8; E. piano 0.5–0.9 | [arXiv 2406.18747v2](https://arxiv.org/html/2406.18747v2) | Default-sampling rows alone give 0.7–1.1 / 2.4–2.8. Clean electric is the worst guitar class but ties with electric piano. Same numbers in v1 |

## 8–16: Datasets and terms

| # | Claim | Status | Exact quote / number | Source | Note |
|---|---|---|---|---|---|
| 8a | GuitarToneAdapt: CC BY 4.0 | CONFIRMED | LICENSE: "Creative Commons Attribution 4.0 International (CC BY 4.0) … Copyright (c) 2026 GuitarToneAdapt". JSON-LD `license: creativecommons.org/licenses/by/4.0/` | [site](https://guitartoneadapt.com/guitar-tone-dataset/), [LICENSE](https://raw.githubusercontent.com/Pera-Labs/guitar-tone-dataset/master/LICENSE) | Attribution: "GuitarToneAdapt (https://guitartoneadapt.com)". Settings "provided 'as is', without warranty" |
| 8b | 1,252 entries; fields | CONFIRMED | 1,252 records with 13 keys: song, artist, genre, era, tone_type, part, amp_settings, original_gear, effects, pickup, confidence, sources, url | downloaded JSON | `original_gear` has only amp, guitar and notes; there is no pedals field |
| 8c | tone_type vocabulary | CORRECTED | Site: "clean · crunch · distorted · overdriven". README: "`clean`, `distorted`, or `bass`". Data: distorted 965, clean 250, overdriven 25, bass 12 | site, README, JSON | No "crunch" anywhere |
| 8d | How produced; AI-generated? | NOT FOUND (no AI statement) | About page: "Each tone in the library is built from real sources — rig rundowns, interviews, gear lists … not guesswork." README: "community-researched starting points, not official recall sheets" | [about](https://guitartoneadapt.com/about/), [README](https://raw.githubusercontent.com/Pera-Labs/guitar-tone-dataset/master/README.md) | Neither the site nor the repo says AI-generated. The data contradicts "not guesswork": 37.8% of entries have no sources. The about page still says "500+ famous guitar tones". No terms or privacy page (`/terms` returns 404) |
| 8e | B: "confidence values and source citations" | MISLEADING | Numeric confidence in 756/1,252; "medium" in 473; "high" in 23. Sources present in 779 (62.2%) | JSON | See the profile below |
| 8f | Mirror | CORRECTED (link) | The site's mirror link `…/main/guitar-tones.json` returns 404. The file is on `master` | raw GitHub | Content identical to the site file (formatting differs) |
| 9 | GOAT: CC BY-NC 4.0 vs CC BY 4.0; restricted; contents | CONFIRMED (BY-NC) | Dataset record 15690894: `cc-by-nc-4.0`, `restricted`, 0 public files. "research purposes only and is not intended for use in any commercial product." The **CC BY 4.0 record is 17811453 = the ISMIR 2025 paper PDF**, not the data | [dataset API](https://zenodo.org/api/records/15690894), [paper record](https://zenodo.org/api/records/17811453), [paper](https://arxiv.org/html/2509.22655v1) | 5.9 h DI (5.17 h standard + 43.85 min other); 172 files. Strat 208.82+26.15 min, Strandberg 79.83, Jazzmaster 15.62+10.34, Les Paul 6.08+7.36. Amp renders: **29.5 h total** (B is right), 25.85 h standard-tuning (A's figure). About 7,000 NAM profiles plus Archetype Nolly IRs. Players: "main authors and two third party content creators"; GuitarFlow says "three guitarists on four different guitars" |
| 10 | SynthTab: README vs LICENSE; ~2 TB | CONFIRMED | README: "SynthTab is released with CC BY-NC 4.0 license". LICENSE file: "Creative Commons Attribution 4.0 International". "Total file size is close to and less than 2 TB"; zips < 50 GB | [README](https://raw.githubusercontent.com/yongyizang/SynthTab/main/README.md), [LICENSE](https://raw.githubusercontent.com/yongyizang/SynthTab/main/LICENSE) | B says plain "CC BY-NC 4.0" without the conflict (MISLEADING by omission; still the safe reading). 13,113 h, 23 timbres. "All synthesized audio for electric guitar corresponds to DI"; acoustic guitar is also included, so A's "DI-only" is loose |
| 11 | TONE3000 API terms; per-tone licences | CONFIRMED | "Do not bulk download, scrape, mirror, or cache the TONE3000 catalog. Only download models when a user requests them." "Each tone carries a license chosen by its creator (e.g. T3K, CC BY, CC BY-NC)". Free tier: "if your product is non-commercial" | [API terms](https://www.tone3000.com/api/terms) (effective 7 Jul 2026) | The API's licence enum: t3k, cc-by, cc-by-sa, cc-by-nc, cc-by-nc-sa, cc-by-nd, cc-by-nc-nd, **cco**, so A's "cc-by or cc0" is valid. Also "Do not redistribute … hosting tones on your own servers". Site ToS (12 Mar 2025): "You may not collect or download all or a substantial portion of available tones for any purpose" |
| 12 | Five guitar dataset | CONFIRMED | `cc-by-4.0`, open, 90 files, 0.73 GB. Telecaster, Ibanez ART 120 with EMG, Epiphone Joe Pass Emperor-II. "The electric guitars were plugged into a DV Mark Little Jazz guitar amp which has a DI output" | [API](https://zenodo.org/api/records/4988354) | 6 songs × 3 electric = 18 electric DIs |
| 13a | EGDB-PG 19789500: CC BY 4.0, 135 GB | CONFIRMED | `cc-by-4.0`, `EGDB_FLAC_bundle.zip` 135,406.6 MB. "FLAC versions of EGDB-PG and EGDB-NDSP"; WAV on request | [API](https://zenodo.org/api/records/19789500) | Contact f08946011@ntu.edu.tw (demo page). The original EGDB site states no licence |
| 13b | "Tone King Imperium" = the project's Imperial MKII? | CORRECTED | Demo: "Amplifier presets in EGDB-NDSP: … Tone King Imperium, Rhythm Channel", under "Transcription on Neural DSP Quad Cortex rendered audio". Neural DSP: "Tone King Imperial MKII will be compatible with Quad Cortex … in a future CorOS update" | [EGDB-PG demo](https://ss12f32v.github.io/Guitar-Transcription-with-Amplifier/), [Neural DSP](https://neuraldsp.com/plugins/tone-king-imperial-mkii), [Guitar World](https://www.guitarworld.com/news/neural-dsp-quad-cortex-update-2023) | No "Imperium" product exists. [I] It is a Quad Cortex Neural Capture of an Imperial MKII (captures added in CorOS 2.0, 2023), not the plugin. The plugin has Lead and Rhythm channels |
| 14a | Slakh2100-redux: CC BY 4.0, size | CONFIRMED | `cc-by-4.0`, `slakh2100_flac_redux.tar.gz` 104.3 GB; "almost 500 Gb" as WAV; 2,100 mixes, 145 h | [API](https://zenodo.org/api/records/4599666) | — |
| 14b | Guitar-TECHS: CC BY 4.0, ~5 h 12 min | CONFIRMED | Paper total "05:12:02". Zenodo 14963133 `cc-by-4.0`, 4.13 GB, 3 professional guitarists | [paper](https://arxiv.org/html/2501.03720), [API](https://zenodo.org/api/records/14963133) | — |
| 15a | EG-IPT: "52,320 isolated notes", CC BY 4.0 | CORRECTED | "52,320 monophonic audio files, totaling 28 hours, 22 minutes, and 56 seconds"; NIME paper: "six audio sources (five microphones, one direct input)" | [API](https://zenodo.org/api/records/15205644), [NIME paper](https://nime.org/proceedings/2025/nime2025_14.pdf) | [I] About 8,720 notes × 6 signals. 96 kHz/24-bit, 19 techniques. 2005 Gibson SG into EVH 5150 III 50W, "All amp controls were kept flat", Mesa 4×12 V30; DI via BSS AR-133. CC BY 4.0, 23.76 GB zip |
| 15b | DadaGP access | CONFIRMED | "Please contact Dadabots or Pedro Sarmento via email or twitter … to request access to the dataset for research purposes." LICENSE MIT (code) | [README](https://raw.githubusercontent.com/dada-bots/dadaGP/main/README.md) | Zenodo 5624597 (`cc-by-4.0`) holds only the paper PDF |
| 16 | Marshall JVM410H 7970723 licence; IDMT upstream | CONFIRMED (conflict real) | Record: `cc-by-4.0`, open, 4.37 GB. Paper §2.1: "we composed a 6-min-long dataset of guitar and bass audio files … the sounds were taken from IDMT datasets". IDMT-SMT-Guitar (Zenodo 7544110): `cc-by-nc-nd-4.0` | [API](https://zenodo.org/api/records/7970723), [paper PDF](https://www.pure.ed.ac.uk/ws/portalfiles/portal/408428956/Wright2023DAFX23NeuralGrey.pdf) | The project's hold is justified: the NC-ND inputs are redistributed under BY |
| 22 | Weathervane "Shaking Through": CC BY-NC; DIs? | CONFIRMED (licence) / NOT FOUND (DIs) | Terms (search snippet): "Weathervane audio files downloaded for personal use are currently subject to the Creative Commons Attribution-NonCommercial 4.0 International License. This may change in the future" | [terms](https://weathervanemusic.org/termsofuse) (direct fetch blocked by Cloudflare, 403) | Raw multitracks need Monthly or Annual "Remix" membership; Lo-Res 16/44.1, Hi-Res 24/88.2. No source lists a guitar DI track. Check one episode's track sheet |

## 17–21: Transcription, synthesis, perception, statistics

| # | Claim | Status | Exact quote / number | Source | Note |
|---|---|---|---|---|---|
| 17a | Basic Pitch onset F1 66.1 on clean commercial jazz; 79.0 on GuitarSet | CONFIRMED | Table 4 (own test split, "9 commercial jazz guitar recordings"): Basic Pitch P 54.6 / R 85.0 / F 66.1. Table 2 GuitarSet (supervised setting; value taken from the Basic Pitch paper): F 79.0 | [arXiv 2402.15258v1](https://arxiv.org/html/2402.15258v1) | Note-onset F at 50 ms. The jazz data covers "steel string, nylon string, electric, acoustic" guitars; the authors say "mostly 'clean'" |
| 17b | YourMT3+ < 10% on non-main instruments | CONFIRMED | "Particularly for non-main instruments (excluding piano, bass, vocals, and drums), our models performed below 10%." | [arXiv 2407.04822](https://arxiv.org/html/2407.04822) | Measured on RWC-Pop. The authors refined only the bass annotations ("lacked the time" for the other instruments) |
| 18 | GuitarFlow: licence, data, listening | MISLEADING (A's "only barely") | No LICENSE in repo (404 on main and master); no weights. Data: GOAT "roughly 5.75 hours … three guitarists on four different guitars" plus Guitar Pro RSE renders, in **Music2Latent** latent space. "only barely perceived as more realistic than the Guitar Pro audio in the DI scenario (H1), it is perceived as significantly more realistic when run through the distortion of a guitar amplifier (H2)" | [arXiv 2510.21872v1](https://arxiv.org/html/2510.21872v1), [repo README](https://raw.githubusercontent.com/JackJamesLoth/GuitarFlow/main/README.md) | 16 listeners, 15 clips. Through an amp, GP vs GuitarFlow p < .001; on DI, not significant. The paper is CC BY 4.0 (Zenodo 17488616 = the CMMR PDF), which does not cover code. Still excluded: no code licence, Music2Latent is NC, GOAT is NC |
| 19 | Procedural / Karplus-Strong: 81.42 / 71.58 / 68.22 / 83.49; quote | CONFIRMED | GuitarSet note F1: real 81.42, VST 71.58, Karplus-Strong 68.22, procedural pretraining plus fine-tuning 83.49 (procedural only 66.23). Full quote: "the main performance bottleneck lies **not in the composition, but** in the fidelity of the audio rendering." | [arXiv 2508.07987](https://arxiv.org/html/2508.07987) | Acoustic fingerpicking, not electric DI. Paper licence CC BY-NC-SA 4.0 |
| 20a | Wright et al. 2020: MUSHRA ≥ 90 at lower gain | CONFIRMED | Mesa 5:50 Plus (Crunch, gain 3): 97 / 97 / 93 / 98. HT-5 Metal (Overdrive, gain 10): 75 / 93 / 80 / 90 (WaveNet1 / WaveNet3 / RNN-32 / RNN-96) | [Aalto PDF](https://acris.aalto.fi/ws/portalfiles/portal/41964332/Real_time_guitar_amplifier_emulation.pdf) | 14 listeners, 5 excluded, leaving 9. Copies one amp at one setting |
| 20b | Kemper profiling d′ = 0.34 | CONFIRMED (found) | "a listening test with N = 177 showed that the overall discrimination performance was d' = .34 … (0.0 ≤ d' ≤ 0.74) … listeners are rarely able to assign audio examples to the correct condition" | Düvel, Kopiez, Wolf & Weihe 2020, *Music & Science* 3, DOI 10.1177/2059204320901952, [PDF](https://d-nb.info/1331543134/34) | Online study; single stimuli rated on an 8-point scale |
| 21 | Webb: wild cluster bootstrap unreliable below ~11 clusters | CONFIRMED with condition | "I demonstrate … that these bootstrap procedures perform poorly with fewer than eleven clusters … a 6-point bootstrap weight distribution improves the reliability of inference." | [IDEAS abstract, QED WP 1315](https://ideas.repec.org/p/ags/quedwp/274640.html) | "These procedures" means the previously suggested ones (Rademacher-type weights). Webb's 6-point weights are the remedy. Published in the *Canadian Journal of Economics*, 2023. The ageconsearch PDF returned 403/202 here |

## GuitarToneAdapt data profile

- **File:** saved to `research_notes/Plan verification/guitar-tones.json`, downloaded from `https://guitartoneadapt.com/guitar-tone-dataset/guitar-tones.json` (1,196,857 bytes, sha256 `9aeba1c8…4908`). The GitHub `master` copy (1,159,412 bytes) has the same 1,252 records and identical content. It was parsed as data with `python3 -I`; nothing was executed.
- **Counts by `tone_type`:**
  - distorted 965 (77.1%)
  - clean 250 (20.0%)
  - overdriven 25 (2.0%)
  - bass 12 (1.0%)
  - No "crunch" label exists. Gain within "distorted": ≤4 in 78 entries, 4.5–6 in 393, 6.5–8 in 394, ≥8.5 in 100. Mean gain is 1.56 for clean and 6.43 for distorted, so crunch has to be inferred from gain.
- **Counts by `part`:** riff 1,035; solo 193; plus "clean" 12, "distorted" 7 and "main" 5 (these labels are inconsistent).
- **Confidence:**
  - Numeric in 756 entries: range 0.44–0.90, mean 0.747.
  - Strings in the rest: "medium" 473, "high" 23. Every overdriven and bass entry has a string value.
  - **Confidence ≥ 0.7: 592/1,252 = 47.3%** (78.3% of the numeric ones). Counting "high" as well gives 615 (49.1%).
- **Sources:**
  - **779/1,252 (62.2%) have at least one URL.** 473 have none, and 471 of those are "medium".
  - All 592 entries with confidence ≥ 0.7 have sources.
  - Top domains: equipboard 522, reddit 438, guitarworld 207, guitarchalk 133, premierguitar 111, musicstrive 102, ultimate-guitar 71, thegearpage 65, musicradar 56, wikipedia 31.
- **Other fields:**
  - 1,176 distinct songs from 615 artists; 2 duplicate song/part keys.
  - `amp_settings` holds gain, bass, mid, treble and presence on 0–10; reverb is missing in 19.
  - `original_gear.guitar` is blank in 335 entries and `notes` in 412.
  - Effects are free-text tags (e.g. "noise_gate", "noise gate" and "noise-gate" all appear).
- **Provenance:** the site and repo say "community-researched"; neither says AI-generated (see 8d). Treat it as unverified secondary research. No terms page exists beyond CC BY 4.0 attribution and an "as is" disclaimer.
- **Project test songs (Eagles):**
  - **Hotel California:** one entry, **solo only**, "distorted", gain 5, bass 5.5, mid 7, treble 6.5, presence 6.5, reverb 4.5; confidence 0.8; 5 sources (equipboard, reverb.com, an Ultimate Guitar forum thread, a Gear Page thread). The entry names a Fender "Black Panel" Deluxe and a Telecaster for Walsh's solo, with delay, phaser and reverb. These gear claims are untrusted and unverified.
  - **Long Road Out of Eden:** no entry; the guessed URL returns 404.
  - Other Eagles-related entries: Life in the Fast Lane (riff, 0.77), Take It Easy (riff, "distorted" at gain 3, confidence "medium", no sources), Don Felder's "Heavy Metal (Takin' a Ride)" and Joe Walsh's "Rocky Mountain Way".
  - If the dataset is used as a prior, keep the Hotel California record out of any tuning on the end-to-end test.
- **Example entry** (verbatim, trimmed notes):

```json
{"song": "Hotel California", "artist": "Eagles", "genre": "rock", "era": "1970s",
 "tone_type": "distorted", "part": "solo",
 "amp_settings": {"gain": 5, "bass": 5.5, "mid": 7, "treble": 6.5, "presence": 6.5, "reverb": 4.5},
 "original_gear": {"amp": "Fender 'Black Panel' Deluxe Amp (1963-1966, studio recording, as confirmed by multiple sources)",
                   "guitar": "Fender Telecaster (circa 1953-59, maple neck, bridge pickup, as used by Joe Walsh for the solo)",
                   "notes": "Studio recording, 1976. Joe Walsh played the iconic solo using a vintage Fender Telecaster into a Fender Black Panel Deluxe amp, with a Maestro Echoplex tape delay and an MXR Phase 90 phaser. …"},
 "effects": ["delay", "phaser", "reverb"], "pickup": "Bridge pickup", "confidence": 0.8,
 "sources": ["https://equipboard.com/pros/joe-walsh?…", "https://reverb.com/news/the-gear-of-the-eagles",
             "https://www.ultimate-guitar.com/forum/showthread.php?t=516122",
             "https://www.thegearpage.net/board/index.php?threads/joe-walshs-guitar-amp-in-hotel-california.319381/",
             "https://equipboard.com/pros/joe-walsh"],
 "url": "https://guitartoneadapt.com/tone/hotel-california--eagles--solo--distorted--guitar/"}
```

## Limits of this check

- GitHub search and user endpoints were blocked in this session, so the "no EG-VAE code" check relied on the demo page, arXiv, Hugging Face and web search.
- The Weathervane and ageconsearch pages returned 403. Their quotes come from a search snippet and the IDEAS abstract respectively.
- The Distortion Recovery sign-error reading is an inference from the published evaluation code plus the ESR value. The paper's table may have been produced with other code.
