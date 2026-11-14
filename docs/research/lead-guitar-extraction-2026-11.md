# Separate in stereo first, then pick the lead

*Research, 2026-11-14, for the ML session; not a declared plan. Web and repo reading only: nothing was downloaded, installed or run. Tags: **[M]** measured or published; **[C]** community result; **[R]** measured or stated in this repo; **[I]** inferred; **[none]** no evidence found. Builds on `single-guitar-separation-2026-10.md`, `guitar-separation-2026-10.md` and `effects-estimation.md`, and does not repeat them. It also builds on and updates `docs/stereo-side-results.md`.*

**Answer.** No open model, prompted or not, has been shown to pull one electric guitar out of several; all select by class [none; I from M]. The default route separates the plain mono fold. The centre option (`stem_C`, the user's pick on 5 of 7 R1 songs, unscored) masks the song first, leaving overlapping hard-panned takes ~7.4 dB down. No option gives the separator true stereo [R, I]. On stereo Mega-53 stems, the repo's stereo-side screen gained +1.35 dB on a centred lead with a phantom-centre model and +0.35 with unsmoothed coherence, short of +2 dB [R]. First, re-run it on `gtr_mss` with smoothed coherence and `stem_C`, no download [I]. Next come a stronger centre model (204 MB) and two unscored lead/rhythm checkpoints (337.1 and 109.8 MB) [M]. Training is slow: the CPU, the only measured rate within the 20 GB cap, needs ~12 h per fold per 1,000 steps [R, I]. SAM-Audio ranks last.

## 1. Separators split all guitars; two untested files claim lead/rhythm

| Model | Guitar SDR (MVSEP) | Size | Licence |
|---|---|---|---|
| BS-RoFormer SW | 9.01 [M] | 699.4 MB; MLX 349.5 MB ([port](https://huggingface.co/MrSimmo/BS_Roformer_SW-MLX)) [M] | Unknown [M] |
| `gtr_mss`, current (= `bs_gtr_xlancer.ckpt` by SHA-256) | 8.60 [M] | 204 MB [M] | MIT, from SW; accepted [R] |
| Mega-53 guitar head | 8.25 [M] | 1.37 GB [R] | Weights unstated [M] |
| listra92 Mel-Band RoFormer lead/rhythm | None [none] | 337.1 MB [M] | None [M] |
| Dry Paint Dealer HTDemucs lead/rhythm | None [none] | 109.8 MB [M] | None [M] |

MVSEP's board (30 one-minute tracks, acoustic and electric pooled) is the only one ranking these together ([leaderboard](https://mvsep.com/quality_checker/leaderboard/guitar/?sort=guitar)) [M]. SW's 0.42 dB lead [I from M] is about what network swaps gained on the repo's multi-guitar parts (+0.3 to +0.4 dB) [R], too little to fix the leaks [I]. The lead/rhythm files sit in a third-party mirror ([noblebarkrr/mvsepless_resources](https://huggingface.co/noblebarkrr/mvsepless_resources)) [M]. Trained on "Lead" and "Rhythm" only, they likely need a guitar stem as input; their trainer and data are unknown [I, none].

## 2. Prompts pick the class, not the guitar

Of released prompted models, only Banquet reports guitar figures: 0.7 dB median SNR on clean electric, 2.4 on distorted (MoisesDB) [M]. Its results move under 0.2 dB, electric piano apart, whether its query comes from the same song or another ([Banquet](https://arxiv.org/html/2406.18747v2)) [M]. SAM-Audio's "−" spans over rhythm-only bars might exclude the rhythm guitar; untested [I, none]. Song-level adaptation gained ~+1.7 dB (piano average) on piano concertos, tested on the same recordings' solo-only sections ([Özer & Müller 2022](https://archives.ismir.net/ismir2022/paper/000059.pdf)) [M]. Stage F has usable solo regions on 1 of 19 parts [R].

## 3. Masking after a stereo separation has a measured, modest prior

The stereo-side screen scored splitters on Mega-53 stereo stems: 19 stage-F parts with another electric guitar, synthetic pans of separate session parts, side given. Δ: project SNR over the stem's mid ([results](../../docs/stereo-side-results.md); [plan](../../docs/stereo-side-plan.md)) [R]:

| Layout | Splitter | Δ SNR, dB [R] |
|---|---|---|
| Target −0.6, others ±0.6 | Target's channel | +1.50 [+0.78, +2.33] |
| Target centred, others hard L/R | MDX23C phantom-centre model (wesleyr36) | +1.35 [+0.31, +2.49] |
| Same | ILD mask; coherence × ILD | +0.76; +0.69 |
| Same | Unsmoothed phase-cosine coherence | +0.35 (+0.56 on a class-perfect stem) |
| Target −1, others +1 (ceiling) | Target's channel | +6.88 |
| All at −0.6 | Target's channel | +0.02 |

Nothing reached +2 dB; Wiener post-processing cancelled most gains; blind side picks lost to the louder guitars [R]. A stereo stem's mid moved only −0.06 to +0.24 dB against mono ([stereo check](../../docs/stereo-and-mix-check-results.md)) [R]. Untested: stereo reverb, real doubles, `gtr_mss` [R].

With a sine/cosine pan law and independent complex-Gaussian bins, today's psi^4·max(cos, 0) cuts pan 0.5 by 12 dB (17.7 under a linear law). It leaves overlapping hard-panned takes 7.4 dB down, or 3.4 if their bin magnitudes are near-equal. It removes 82% of decorrelated reverb power (68% at correlation 0.4) and nearly all hard ping-pong, but no mono delay [I].

The screen's own limit: "a smoothed-coherence variant is simply untested" [R]. Smoothed over time as Avendano and Jot do (forgetting factor 0.90; [US 7567845](https://patents.google.com/patent/US7567845B1/en)) [M], two independent takes should read near 0.3 and a centred source near 1 [I]. The unsmoothed cap (+0.56) argues for modest hopes [R]. gilliaan's centre models beat wesleyr36's on MVSep's undescribed centre set (rank 3) ([MVSep](https://mvsep.com/algorithms/125)); their "center" is "typically" vocals, bass, kick and snare, with no guitar test ([card](https://huggingface.co/gilliaan/CenterWide-Models)) [C]. Keep an unmasked stem for the effects route [I].

## 4. A lead-vs-rest model is possible, slow, and prone to collapse

Two designs fit [I]: a small refinement net on frozen `gtr_mss`, which cannot forget but is capped by the stem (~75% of the wet energy kept) [R]; or a partial or LoRA fine-tune with lead and rest outputs, its lead head started from the stock guitar mask. Train on true stereo mixes with the session's rhythm guitars in the rest [I]; `self_built_mix` folds to mono [R]. About 70 sessions (the ML session's figure, uncounted here) is the low end: community fine-tunes used 97 pairs to 1,000+ songs ([MSST #1](https://github.com/ZFTurbo/Music-Source-Separation-Training/issues/1)) [C].

Level collapse is the main risk: D_F5ft's stems came out at a median −33 LUFS, ~12 dB under the target guitar, where stock (−15) sat ~5.5 dB over it [R]. MSST's L1SNR-dB loss targets this ([losses.py](https://raw.githubusercontent.com/ZFTurbo/Music-Source-Separation-Training/main/utils/losses.py)) [M]. Label noise cost 1.42 dB in SDX23 ([SDX23](https://arxiv.org/html/2308.06979)) [M]. The only measured in-cap training rate is the CPU's, 43.3 s per step at 18.9 GB [R]. MPS with CPU STFTs (MPS STFT gradients break above 65,536 samples) peaked at 21.3 GB, over the 20 GB cap; its estimated 12.7 s per step divides 43.3 s by the 3.4× of a broken-gradient, all-MPS Mega-53 probe [R, I].

## 5. Ranked recommendation

Cheapest and most decisive first [I]; the render-test bar is +2 dB project SNR over Mega-53 [R].

| Rank | Test | What it decides | Expected gain | Cost | User's yes? |
|---|---|---|---|---|---|
| 1 | **Stage-F re-run on `gtr_mss` stereo stems**: MDX23C centre model; smoothed coherence × ILD; psi^4 on the stem; `stem_C`; plain fold | The centre gain on `gtr_mss`; smoothing; where `stem_C` stands | Mega-53: centre +1.35 [+0.31, +2.49], unsmoothed coherence +0.35 (cap +0.56) [R]; smoothed unknown [none] | No download or training; ~1 h [I from R]; keep both output channels | No |
| 2 | **Ear check**: rank 1's best arm against `stem_C` on the R1 songs | Real doubles and reverb | Unknown [none]; `stem_C` won 5 of 7 [R] | Minutes [I]; listening | Listening only |
| 3 | **gilliaan CenterWide BS-RoFormer v2** as the centre arm; X-LANCE's keys model as a competing mask | A better centre; the keys' share of the leak | Weaker model's +1.35, wide interval [R]; centre SDR 16.45–18.93 vs 8.25 [C] | 204 MB, CC BY-NC-SA 4.0 [C]; keys 204.4 MB, = official MIT `key_mss.pth` (SHA-256) [M]; ~1 h [I] | Yes |
| 4 | **Lead/rhythm checkpoints** on the stereo stem, then R1 | Whether released weights carry roles | Unknown; no metric [none] | 446.9 MB, no licence [M]; ~1 h [I] | Yes |
| 5 | **Refinement net** on frozen `gtr_mss` | Learned cues against the gates | Unknown; stem-capped [R] | Timed minutes-long pilot first; a 2k-mix bank ~2.4 h on MPS [I from R]; labels | Yes |
| 6 | **`gtr_mss` lead-vs-rest fine-tune**: a 1,000-step pilot per fold, against silence and stock | Against rank 5 | Synthetic pre-training +0.7 to +2.3 dB (choral, from scratch) [M] | CPU ~12 h per fold, 24 h for two [I from R]; re-time MPS at 3-s windows first | Yes |
| 7 | **SAM-Audio small**: text, then "+", then "+" and "−" | Instance cues from prompts? | Unknown [none]; "guitar" near-silent on one Mac [C] | 5.10 GB + T5-base 0.89 GB + default 5.83 GB span predictor (judge 6.14 GB) [M]; decord and xformers fail; a patched fork ran on MPS; large: ~144 s per 10-s crop, ~1 h per arm, out of memory at 38 s on 64 GB, risky at the 20 GB cap [C, I] | Yes |

## Corrections and open decisions

- **The brief's order.** The brief described `gtr_mss` "plus a centre-channel mask", which reads as a mask on the separator's output. Only `stem_C` masks: the whole song, before a mono separation (`learn/product_path.py` `centre_mix`, lines 61–90; full-controls Amendment 4). Latest main (3fc430ea) keeps `stem`, the plain fold, as the default; no option gives the separator true stereo [R].
- **Round-5 figure.** `round-5-guitar-models.md` line 53's "MVSep lead/rhythm guitar 9.0–9.2" has no MVSep source [M]; it matches the all-guitar top (9.00–9.12) [I]. Its "only lead/rhythm splitter" is out of date [M].
- **ML plan §5** allows "fine-tuning or adapting an existing released separator", as D_F5ft did [R]. Open, for the ML session and the user: is a two-output lead/rest head "a new conditioned one-guitar separator" or "major modelling and training effort"?
- **Licences.** MoisesDB and MedleyDB are CC BY-NC-SA [M], so weights trained on them would likely be share-alike [I]. The plugin EULA on renders is unchecked [none].

## Links

- Notes (2026-11-14): four researcher notes files (guitar separators, query-based extraction, stereo and spatial, training a lead separator), kept locally and not committed; the figures above carry their sources.
- Repo (read 2026-11-14, main at 3fc430ea): [learn/product_path.py](../../learn/product_path.py), [learn/direct_stems.py](../../learn/direct_stems.py), [learn/xlance_finetune.py](../../learn/xlance_finetune.py), [reference/model-path.md](../../reference/model-path.md), [docs/stereo-side-results.md](../../docs/stereo-side-results.md), [docs/stereo-side-plan.md](../../docs/stereo-side-plan.md), [docs/stereo-and-mix-check-results.md](../../docs/stereo-and-mix-check-results.md), [docs/full-controls-plan.md](../../docs/full-controls-plan.md), [docs/trusted-data-t0-design.md](../../docs/trusted-data-t0-design.md), [docs/separation-finetune-plan.md](../../docs/separation-finetune-plan.md), [docs/ROADMAP.md](../../docs/ROADMAP.md), [docs/research/round-5-guitar-models.md](./round-5-guitar-models.md), [docs/research/ml-plan-2026-10.md](./ml-plan-2026-10.md), [docs/research/single-guitar-separation-2026-10.md](./single-guitar-separation-2026-10.md), [docs/research/effects-estimation.md](./effects-estimation.md).
- Checkpoints (sizes read 2026-11-14): [lead/rhythm and keys mirror](https://huggingface.co/noblebarkrr/mvsepless_resources) (337.1, 109.8, 204.4 MB); [official X-LANCE weights](https://huggingface.co/chenxie95/xlance-msr-ckpt) (`gtr_mss.pth`, `key_mss.pth`, MIT); [xlance-msr](https://github.com/ModistAndrew/xlance-msr); [SW](https://huggingface.co/FractalSurfer/BS-RoFormer-SW-6stem) (699.4 MB); [SW MLX](https://huggingface.co/MrSimmo/BS_Roformer_SW-MLX) (349.5 MB); [gilliaan CenterWide](https://huggingface.co/gilliaan/CenterWide-Models) (204–870 MB); [SAM-Audio small](https://huggingface.co/facebook/sam-audio-small) (5.10 GB), [its code](https://github.com/facebookresearch/sam-audio) (T5-base and the span predictor load from Hugging Face), [span predictor](https://huggingface.co/facebook/pe-a-frame-large) (5.83 GB), [judge](https://huggingface.co/facebook/sam-audio-judge) (6.14 GB); [Banquet weights](https://zenodo.org/api/records/13694558) (0.55–0.77 GB each).
- Benchmarks and services: [MVSEP guitar leaderboard](https://mvsep.com/quality_checker/leaderboard/guitar/?sort=guitar); [MVSep lead/rhythm news](https://mvsep.com/news/67?lang=en); [MVSep phantom centre](https://mvsep.com/algorithms/125).
- Papers and reports: [Banquet](https://arxiv.org/html/2406.18747v2); [SAM-Audio](https://arxiv.org/html/2512.18099v1); [SAM-Audio Mac setup and timings](https://gotofritz.net/blog/2025-12-20-playing-with-the-sam-audio-model-on-my-m1-macbook/); [SAM-Audio as a stem splitter](https://gotofritz.net/blog/2026-01-01-can-sam-audio-be-used-to-replace-demucs/); [Özer & Müller 2022](https://archives.ismir.net/ismir2022/paper/000059.pdf); [Avendano 2003](https://www.ee.columbia.edu/~dpwe/papers/Aven03-unmix.pdf); [Avendano–Jot patent](https://patents.google.com/patent/US7567845B1/en); [SDX23](https://arxiv.org/html/2308.06979); [choral pre-training](https://arxiv.org/pdf/2209.02871); [MSST losses.py](https://raw.githubusercontent.com/ZFTurbo/Music-Source-Separation-Training/main/utils/losses.py) and [torch-l1-snr](https://raw.githubusercontent.com/crlandsc/torch-l1-snr/main/README.md); [MSST community fine-tunes](https://github.com/ZFTurbo/Music-Source-Separation-Training/issues/1).
