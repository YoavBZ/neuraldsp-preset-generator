# B1. Literature fact-check: effects representations, search, transcription, measurement (October 2026)

Scope: the literature claims listed for Report A (`_report_A_ours.md`) and Report B (`_report_B_second_agent.md`). Every row below was checked on 2026-10-14 against the primary source: arXiv HTML, the repo's raw `LICENSE`/README, a shallow clone (FXRepBench, OpenAmp), or the Hugging Face model API. Report B's broken citations were mapped from context: `turn10view0` = RLAT (2608.28127), `turn23view0` = Open-Amp (2411.14972), `turn7academia48` = Comunità 2021, `turn3view0` = ST-ITO, `turn0academia45` = Yu et al. 2025 (2505.11315), `turn26academia12` = CDPAM, `turn26search0/1` = ITU-R BS.2132 / BS.1534.

Status key: **CONFIRMED** = the number and wording match the source. **CORRECTED** = the value is wrong; the correct value is given. **MISLEADING** = the number is right, but its context or the conclusion drawn from it is not. **NOT FOUND** = the source does not exist or is not reachable.

---

## Summary: corrections that would change a decision

1. **FXRepBench's CMA-ES result does not show that search beats a pool of 512 candidates (Report A, approach 3).** The CMA-ES runs did not start from a learned proposal. They start from a fixed mid-range point ("Known topology optimizes active continuous controls from a 0.5 center"), with RelFx used only as the scoring objective. The 0.770 they are compared with is RelFx's *pick* from 512 random candidates, not the best candidate in that pool; the pool's best is 0.540. With the same 512 renders, CMA-ES scores 0.739–0.771, the same as random sampling. Listeners agree: CMA-ES@512 averaged 3.39 and Random@512 averaged 3.38. The benchmark's own message is that **learned proposals** save renders: RelFx Head@16 = 0.769 against Random@512 = 0.770. It also shows the search objective being gamed. In hidden topology the verifier's cosine score kept rising up to 4,096 calls, while audio error was lowest at 2,048 calls. Finally, the "true quality" target (L_d) itself correlates with listeners at only ρ = 0.36–0.43. So the literature gives no support for continuous search beyond what the pilot would show. The planted-target control and the anti-gaming protocol become essential.
2. **PEACE weights are CC BY-NC 4.0** (HF `davidbraun/peace`; the README says "The released weights are CC BY-NC 4.0"). Only the code is MIT. Under the project's open-licence rule, PEACE can no longer be a frozen candidate (Report A §5 candidates, approach 5 "PEACE/AFx-Rep embeddings"). It can only be retrained from the MIT code.
3. **The "objective metrics vs listeners |ρ| ≈ 0.4–0.6 ceiling" (Comunità et al. 2025) is overstated.** Overall |ρ| across all metrics is **0.30–0.43**. For **overdrive**, the most crunch-like category, it is **≤ 0.36** (MR-STFT 0.28). Values of 0.4–0.6 appear only for distortion and fuzz. These are correlations measured on mostly high-rated model outputs, not a ceiling. Report A's inference that a DI-free metric with τ 0.3–0.4 "may already be near what listeners support" therefore rests on a mis-stated number.
4. **The "indirect positive evidence" for approach 1 (train in the test condition) is weaker than presented.**
   - **StemFX** does not isolate separator-in-the-loop training. Its authors write "we do not quantify how these artifacts propagate into the learned representation". The Real-Mix test feeds *true* MUSDB stems, and the low anchor (54.9) is the unprocessed input itself, so StemFX beats "do nothing" by 5.7 MUSHRA points with no significance test. The authors credit autoregressive effect selection.
   - **Le Vaillant & Molle's** 14.5 → 81.7 is not "mixture training vs separation". A mixture-trained multi-encoder scored only 17.3%; the jump comes mostly from the contrastive full-triplet loss.
   - **RLAT's** "source gap > processor gap" compares its own model on training-set sources with MUSDB, and its PyTorch effects with Linux plugins. That is digital to digital, so it says nothing about plugin vs real amp.
   - The supporting evidence that remains is EGDB-PG (tone diversity) and RelFx (content mismatch).
5. **RLAT code and weights are not publicly available.** `github.com/SonyResearch/RLAT` returns 404 for LICENSE and README on both main and master, GitHub reports the repo as not found or not accessible, and no weights are on Hugging Face. The method must be reimplemented. Its frozen Stable Audio Open encoder is gated and under a community licence, so a reimplementation needs a different backbone.
6. **The prior-ITO paper Report B relies on (Yu et al., WASPAA 2025, arXiv 2505.11315) is weak support for using web research as a search prior.**
   - The prior is a Gaussian fitted to **365 generic vocal presets**, a population prior, not song-specific evidence.
   - It cut parameter MSE by 33% against uncalibrated ST-ITO (7.756 → 5.168), but that only matches simply using the **mean preset** (5.310).
   - The listening win over regression was **not significant** (p = .117).
7. **Smaller corrections:**
   - MUSHRA-1S's "may pose a higher cognitive effort" was a hypothesis its authors tested and did *not* confirm.
   - BS.1534-3's cap is 12 stimuli, with 7 the ideal, not "about 7".
   - EGDB-PG's 12.8 (MT3-Guitar, crunch) is cherry-picked: MT3-Guitar&Piano scores 73.3 on crunch.
   - Open-Amp's "394 devices / 230 h" belong to the *emulation* model, not the encoder, and the 230 h is rendered output from only 35 min of DI. On real analogue pedals (EGFX) the encoder's accuracy is the weakest figure, 72%.
   - **BoTorch ships PairwiseGP**, plus EUBO/qEUBO preference acquisition, under MIT. pycma is BSD-3 and Optuna is MIT, which closes Report A's open optimiser-licence question.
   - LAION-CLAP's repo and original checkpoints are **CC0-1.0**; only the HF `transformers` ports are Apache-2.0. Both are permissive.

---

## 1. ST-ITO / AFx-Rep (arXiv 2410.21233)

| Claim | Status | Source text / number | Note |
|---|---|---|---|
| "does not work well for … guitar tone matching" (A) | CONFIRMED (wording) | §6 Discussion: "Finally, we have found that the current system does not work well for challenging style transfer applications, such as guitar tone matching." | A one-line limitation with **no experiment or numbers**. It refers to the whole ST-ITO system (AFx-Rep + CMA-ES over their VST chain), not to AFx-Rep as an embedding. The authors also state the input is assumed to be dry: "We assume the input has minimal processing, as our system does not remove effects" (this supports Report B's "base signal" point). |
| CMA-ES population 64, 25 steps (A, B) | CONFIRMED | "we use a population size of 64 and a maximum of 25 optimization steps. The σ hyperparameter is initialized to 0.3 … early stopping, halting optimization after 10 steps of improvement less than 0.1." | At most 1,600 evaluations. The VST chain has 73 parameters and the pedalboard chain 36. |
| AFx-Rep training data; GuitarSet included? | CONFIRMED (GuitarSet: yes) | "MTG-Jamendo, ENST-Drums, URSing, FSD50k, Librispeech, Medley-solos-db, and GuitarSet"; "63 open source or freely available VST3 audio plugins compiled for Linux"; 10 presets per plugin from K-means on MFCCs; 20,000 examples per dataset, "approximately 60 hours". | GuitarSet is **acoustic** guitar, and no electric-DI or amp-sim data is listed. The pretext task is **non-blind** effect and preset classification from input+output embeddings, and "Our approach does not enforce invariance to the content". |
| MFCC 0.74 vs AFx-Rep 0.86 "style test" (A) | CONFIRMED (needs context) | Table 1, "Zero-shot style classification accuracy over 200 trials … five unique styles": MFCCs AVG 0.74, AFx-Rep 0.86 (DeepAFx-ST 0.76, DeepAFx-ST+ 0.78, CLAP 0.56). | The five styles are EQ and compression presets (telephone, bright, warm, broadcast, neutral) on DAPS speech and MUSDB18 music. There is no distortion and no guitar. In the separate style-retrieval figure, "MFCCs and FX-Encoder appear to perform worse". |
| ST-ITO code Apache-2.0 | CONFIRMED | `raw.githubusercontent.com/csteinmetz1/st-ito/main/LICENSE`: "Apache License Version 2.0". | — |
| AFx-Rep weights Apache-2.0, not gated | CONFIRMED | HF API `csteinmetz1/afx-rep`: `"license:apache-2.0"`, `"gated": false`; card front-matter `license: apache-2.0`. | The repo also holds `BEATs_iter3_plus_AS2M.pt`, `FXencoder_ps.pt` and `plugins.tar` (Linux VSTs). The repo-level tag should not be read as relicensing those. |

URL: https://arxiv.org/html/2410.21233 · https://huggingface.co/csteinmetz1/afx-rep

## 2. FXRepBench / CounterFX-200 (github.com/meteroad/fxrepbench; project page meteroad.github.io/posthoc-fx-registration)

| Claim | Status | Source text / number | Note |
|---|---|---|---|
| AFx-Rep pick 1.080 vs oracle 0.540, 512 candidates (A) | CONFIRMED | `candidate_budget/pedalboard_test200_seed20270724/afxrep_random_known/budget_curve.csv`, budget 512: `selected_ld_mean` 1.080, `oracle_ld_mean` 0.540. | Known topology, shared Global Random pool. Hidden topology: 1.667 vs 0.676. A single random candidate scores 1.612, so AFx-Rep recovers about 50% of the pool's reachable gain (Fx-Encoder++ 0.866 ≈ 70%, RelFx 0.770 ≈ 79%). |
| Spearman 0.36–0.44 (AFx-Rep) vs 0.57–0.62 (Fx-Encoder++) (A) | CONFIRMED (rounded) | `score_quality_spearman_mean`: AFx-Rep 0.337–0.436 over budgets 16–512 (0.376–0.436 at 512; known-random@512 = 0.427). Fx-Encoder++ 0.566–0.625. RelFx 0.613–0.691. | "True quality" is **L_d** (a 3-resolution STFT distance to the exact target), not listening. The project page reports L_d vs listeners at "Spearman ρ = 0.429 … Excluding source and target controls gives ρ = 0.357". The column's definition is not documented in the release. |
| "learned proposal plus CMA-ES … beats the best of 512 random candidates, 0.71–0.74 vs 0.770" (A) | **MISLEADING / CORRECTED** | `cmaes/run_0{1..4}_relativefx_cmaes_known_test200_pop64_iter25`, budget 1600: 0.714, 0.730, 0.736, 0.727. `locks/stito-cmaes.json`: "Known topology optimizes active continuous controls from a 0.5 center." | (a) There is **no learned proposal**: this is CMA-ES with RelFx as the objective, from a fixed start. (b) 0.770 is RelFx's **pick** from Random@512; the best in that pool is **0.540**. (c) It uses 1,600 renders vs 512. **At 512 renders CMA-ES gives 0.739–0.771, the same as Random@512.** The learned proposal is a separate row: Head-centered@512 = 0.708, Head@16 = 0.769 ("using 32× fewer candidates"). Listening: CMA-ES@512 3.39, Random@512 3.38, Head@512 3.57. Hidden-topology CMA-ES: "the verifier cosine objective continues to improve with more calls, while output error is lowest at 2,048 calls" (0.918 at 2,048; 0.933 at 4,096). An ST-ITO-style AFx-Rep CMA-ES@512 = 1.021. |
| Licence Apache-2.0 | CONFIRMED (+data licence) | `LICENSE` = Apache-2.0. `LICENSES.md`: "Original benchmark manifests, configurations, aggregate reference results, and documentation are licensed under … CC-BY-4.0". | FMA audio is not redistributed and keeps per-track licences. No model checkpoints are included. |
| Data: same recording, adjacent windows? | CONFIRMED | "two adjacent, non-overlapping 10-second windows are extracted from the same 30-second FMA-small excerpt. Both windows are normalized to -20 LUFS. A sampled one-to-four-effect chain …" | 200 test items of FMA full mixes across 8 genres, not guitar. Eight Pedalboard effects (HPF, LPF, peak, compressor, distortion, chorus, delay, reverb) with 22 controls. A salience filter keeps only targets with "Ld ≥ 0.8", so effects are strong. This is easier than the project's task. |

URL: https://github.com/meteroad/fxrepbench · https://meteroad.github.io/posthoc-fx-registration/

## 3. RLAT, "Exploring the Design Space of Representation Learning for Audio Transformations" (arXiv 2608.28127; Lee, Martínez-Ramírez, Koo, Liao, Lee, Mitsufuji; Sony AI; ISMIR 2026)

| Claim | Status | Source text / number | Note |
|---|---|---|---|
| Cross-instrument 48.8% vs AFx-Rep 20.5, Fx-Encoder++ 13.2, Fx-Encoder 6.7, CLAP 1.0, MERT 2.6 | CONFIRMED | Table 1, CI column: L_T 48.8 (the best configuration, L_T+L_P, is 49.8; the full model 48.7); AFx-Rep 20.5; Fx-Encoder++ 13.2; Fx-Encoder 06.7; CLAP 01.0; MERT 02.6; VGGish 1.6; PANN 1.7. | 20-way episodic retrieval (chance 5%) of **single processors**, on MUSDB test stems through 67 Linux plugins with random parameters. CI means "the positive uses a different … instrument than the query, while all negatives share the query's source". Within-stem, AFx-Rep (87.7) beats the L_T model (83.8). |
| "Source gap more severe than processor gap" | CONFIRMED (narrow scope) | "the processor gap appears small; the seen PyTorch processors are even slightly harder to distinguish than the unseen Linux plugins … the source gap is much larger … Note that the baselines show no such source gap, since they used different training data." | Measured on **RLAT's own models**: seen training-set sources 83.2 vs unseen MUSDB 61.1. The "processor gap" is its PyTorch library vs Linux plugins, digital to digital. It does **not** test plugin vs real amp, so it cannot show that the project's render-to-record gap is "not about processors" (Report A §1). |
| Batch construction | CONFIRMED | "every query is assigned a positive that applies the same processing to a different source (possibly from a different instrument). We also include hard negatives that apply different processing to the query's exact source signal." | Report B's "**nearby** but different processing" is not in the paper. |
| Dependence on Stable Audio Open | CONFIRMED | "we compose the frozen Stable Audio Open (SAO) encoder [25] with a trainable adapter". | HF `stabilityai/stable-audio-open-1.0`: `gated: auto`, licence `other` (stable-audio-community). |
| Source probe 67% | CONFIRMED | Table 3, 4-way stem classifier (drums/bass/vocals/other; chance 25%) on z_T: 67.2 (L_T only), 85.0 (L_T+L_P), 89.4 (full); on z_y 93–95; Fx-Encoder++ 89.4; AFx-Rep 92.2. | Content invariance is partial even in the best case. The authors: "it cannot eliminate the content the transformation inherently depends on". |
| Compute (H100) | CONFIRMED | "We train for 100k steps … on a single NVIDIA H100 GPU"; "We pre-render 1.5M subbatches of 64 tuples … as SAO latents"; batch 1024. | Out of reach on a Mac at this scale (Report B's point is right). |
| Code/weights licence | **NOT FOUND** | The paper says: "Our implementation and processor library are available at https://github.com/SonyResearch/RLAT." | On 2026-10-14 raw `LICENSE` and `README.md` returned 404 on main and master, GitHub reports the repo not found or not accessible, and no RLAT weights are on HF. The arXiv text is CC BY-SA 4.0, which covers the paper only. Treat as unavailable. |

URL: https://arxiv.org/html/2608.28127

## 4. Le Vaillant & Molle (arXiv 2509.13285, "Contrastive timbre representations for musical instrument and synthesizer retrieval")

| Claim | Status | Source text / number | Note |
|---|---|---|---|
| 14.5% → 81.7% top-1 (mixture-trained vs Demucs stems) | CONFIRMED (numbers) / **MISLEADING** (attribution) | Table 2, "Average QbE test accuracies (%) for mixture sounds": Demucs + single-encoder 14.5 / 25.8; Multi-encoder [1] **17.32** / 62.6; Contrastive triplet 64.8 / 85.0; **full triplet 81.7** / 95.7; InfoNCE 70.0 / 93.3. | Mixtures of three instruments (one percussion, one bass, one synth lead) from NSynth and Surge, using 1,463 instruments and 5,000 test mixtures of held-out instruments. The task is retrieving **instrument identity**, not processing. Demucs puts synth leads in "other", which handicaps the baseline. A model trained on mixtures (the multi-encoder) reached only 17.3%, so most of the gain comes from the single-model contrastive loss, not from "training on mixtures" alone. |

URL: https://arxiv.org/html/2509.13285

## 5. StemFX (arXiv 2607.15634, ISMIR 2026)

| Claim | Status | Source text / number | Note |
|---|---|---|---|
| MUSHRA 60.6 vs low anchor 54.9 on real mixes | CONFIRMED (numbers) / **MISLEADING** (as separator evidence) | "StemFX achieves the best MRSTFT of 1.44 and the highest MUSHRA score of 60.6, the only method that surpasses the FX-normalized low anchor of 54.9." High anchor 96.6. ITO+AFx-Rep 30.6, ITO+BSFiLM 19.9, StemFX forced 25.3. | 20 listeners. **The low anchor is the unprocessed input**, so the margin over doing nothing is 5.7 points, and no CI or significance test is reported. The Real-Mix input is "FX-normalized stems" (true MUSDB stems), so no separator is used at test. The authors credit the result to choosing which effects to apply. They also write: "we do not quantify how these artifacts propagate into the learned representation; a comparison against a model trained on clean multitrack stems would isolate this effect." |
| AFx-Rep single-effect top-1 3.0% | CONFIRMED | "StemFX achieves 16.8% Top-1 and 0.235 MRR versus 3.0% Top-1 and 0.067 MRR for AFx-Rep." | Mixing-style retrieval from a pool of N = 500 (chance 0.2%) on MUSDB18 four-stem sets with one Pedalboard effect. At 8 effects, AFx-Rep scores 68.4%. |
| Licence MIT, code and weights | CONFIRMED | `barry-mir/stemfx` LICENSE: "MIT License Copyright (c) 2026 The StemFX Authors"; HF `barry-mir/stemfx-bsfilm`: `license: mit`, not gated. | The SCNet separator checkpoint (~214 MB) is downloaded separately; its licence was not checked. |

URL: https://arxiv.org/html/2607.15634

## 6. RelFx, "Beyond Dry References" (arXiv 2608.10573, ISMIR 2026; Tencent Music)

| Claim | Status | Source text / number | Note |
|---|---|---|---|
| 1.399 → 1.876 without different-content pairs | CONFIRMED (number) / wording imprecise | "Removing it improves retrieval R@1 by 2.3 percentage points (69.6 vs. 67.3) but sharply degrades style transfer from 1.399 to 1.876 (+34%), because the model learns content shortcuts" (Table 3, MUSDB18, Self-ref ITO). | What is removed is **cross-segment sampling**: in normal training, the reference and the processed input are *adjacent, non-overlapping* clips of one section. Contrastive positives come from different tracks with or without it. Removing it *raises* retrieval R@1, a warning that retrieval scores can hide content shortcuts. |
| Weights CC BY-NC-SA, code MIT | CONFIRMED | HF `TMEGalaxyAudioEffect/relfx-ismir2026`: `license: cc-by-nc-sa-4.0`; repo LICENSE: "MIT License Copyright (c) 2026 Tencent Music Entertainment Group" (with Apache-2.0 third-party notices). | Training data was "a licensed internal collection … and 2,585 stems from MoisesDB", so a retrain needs the project's own data. |

URL: https://arxiv.org/html/2608.10573

## 7. EGDB-PG (arXiv 2504.07406)

| Claim | Status | Source text / number | Note |
|---|---|---|---|
| 22.8 → 79.0 F1, 1 → 256 tones (high-gain) | CONFIRMED | Table IV (out-of-domain: the EGDB-PG test set rendered through **six Neural DSP amps**): high-gain onset F1, 1 tone + content aug 22.8, 4 tones 57.4, 256 tones 79.0. "the 1-tone model (with augmentation) achieves a note-wise F1 score of 22.8%". | This isolates the **number of tones** only. Report A's "tone and player variety" adds players, which this result does not measure. The unseen tones are still plugin renders. |
| 43.6 → 84.8 with content augmentation | CONFIRMED (low-gain column) | Table IV, 256 tones: row 3 (no content aug) low-gain onset F1 43.6; row 1 (content aug) 84.8. Crunch 59.0 → 85.3; high-gain 51.7 → 79.0. | The content augmentation is GuitarSet rendered through amps. |
| Crunch onset F1: hFT 47.5, MT3-Guitar 12.8, tone-aware 81.6 | CONFIRMED (numbers) / **MISLEADING** (as "generic models drop to 12.8–47.5") | Table III (in-domain EGDB-PG test, BIAS FX2 tones): TIT 81.6; hFT-Maestro 47.5; MT3-Guitar 12.8; **MT3-Guitar&Piano 73.3**; hFT-Maestro-EGDB-PG 52.2. | MT3-Guitar scores 44.2 on low-gain and 46.8 on high-gain. Its 12.8 on crunch is an outlier, probably from MT3 labelling the guitar as piano. |

URL: https://arxiv.org/html/2504.07406

## 8. Hayes, Saitis & Fazekas (arXiv 2506.07199, ISMIR 2025)

| Claim | Status | Source text | Note |
|---|---|---|---|
| Point regression "degrades performance" on equivalent settings | CONFIRMED (quote) / scope caveat | Abstract: "we demonstrate on a synthetic task that regressing point estimates under permutation symmetry degrades performance, even when using a permutation-invariant loss function or symmetry-breaking heuristics." | The finding is specific to **permutation symmetry**, meaning structurally interchangeable parameters such as swappable oscillators, on a synthetic task (plus Surge XT). Amp-preset equivalence is perceptual many-to-one, so this is a supportive analogy, not direct evidence. |

URL: https://arxiv.org/abs/2506.07199

## 9. Okita & Katayose (arXiv 2604.22276, ICASSP 2026)

| Claim | Status | Source text / number | Note |
|---|---|---|---|
| Macro-F1 0.958 vs 0.942–0.949 | CONFIRMED | Table 3: Dry-Type-Direct + Search 0.958; Bypass-Type-Iter 0.949; Bypass-Config-Iter 0.942. | Only **3 Pedalboard effects** (chorus, distortion with drive 10–20 dB, reverb), chains of up to 3, on guitar DIs (IDMT, GuitarSet, EGDB, Guitar-TECHS). Level is RMS-normalised after every effect. |
| 23.1 vs 18.2 dB SI-SDR with the true dry signal | CONFIRMED | Table 6: Bypass-Config-Iter (baseline, no search) 18.18; Dry-Type-Direct + Search 23.07; other + Search variants 22.64–22.68. "we performed the reconstruction using ground-truth dry signals." | The gain comes from adding search to any variant. The search uses Optuna's CMA-ES, with TPE for 1-D cases. |
| Code release? | **NOT FOUND** | Only "We also provide examples of the results online: https://okitayouichi.github.io/afx-pred-sch-demo/". | The demo page has audio only; no code link exists in the paper or on the page. |

URL: https://arxiv.org/html/2604.22276

## 10. Open-Amp (arXiv 2411.14972; Wright, Carson, Juvela): reconciling Reports A and B

| Claim | Status | Source text / number | Note |
|---|---|---|---|
| 112,888-parameter encoder (B) | CONFIRMED | "giving a total of 112888 learnable parameters" (SimCLR, 64-d embedding). | Positives are "two different clips from the input dataset, processed by one of the effects models". That means **different clips**, not necessarily a "different guitar" as Report B says. |
| GFX 91.8%, EGFX 72.0%, EGDB 91.1% (B) | CONFIRMED | Table II, "Cross-dataset evaluation", Open-Amp encoder row: GFX 91.8, EGFX 72.0, EGDB 91.1, Open30 99.8. | The encoder is frozen and trained for 100k iterations, but **the single-layer MLP probe is trained on each target dataset** (85/15 split). EGFX is the only real-analogue-pedal set, and it is the weakest figure. |
| GUITAR-FX-DIST 87.9% (A's notes) | CONFIRMED (different table) | Table I, GFX's own Mono/Poly × Discrete/Continuous protocol, MLP "Overall" 87.9 (FxNet 86.9, KNN 84.5). | Both numbers are right: 87.9 comes from the FxNet comparison protocol, 91.8 from a random 85/15 split. |
| EGFxSet 72% (A's notes) | CONFIRMED | Same as Table II, 72.0. | — |
| 394 synthetic devices, 230 h IDMT (A's notes) | **CORRECTED** (attribution) | "resulting in a total of 394 synthetic devices"; "trained on an input signal of 35 minutes of (clean) audio data, giving a total of 230 hours of synthetically generated training data." | Both figures belong to the **one-to-many emulation TCN**, not the encoder. The 230 h is rendered output from 35 min of DI, not 230 h of IDMT DI. The encoder used the Proteus Tone Packs (59 amp + 101 pedal LSTM captures) with IDMT-Guitar input. |
| Transfer to real analogue pedals (B) | CONFIRMED (emulation, not classification) | §III-B: three EGFX pedals (Proco Rat, Boss Blues Driver, Tube Screamer Mini) are enrolled by learning only a new embedding in the frozen foundation model; "comparable results to training a one-to-one model". | This is evidence about the emulation latent space. For classification, the analogue figure is the 72%. |
| Repo licence | CONFIRMED: **none** | A shallow clone of `github.com/Alec-Wright/OpenAmp` has no LICENSE file; raw `LICENSE*` returns 404 on main and master. | The repo nonetheless ships `Checkpoints/FxEncoder-splendidbreeze23-ep45.pt`. Unlicensed means all rights reserved. The Proteus packs are GPL-3.0 (earlier note). |

URL: https://arxiv.org/html/2411.14972 · https://github.com/Alec-Wright/OpenAmp

## 11. Comunità, Stowell & Reiss 2021, "Guitar effects recognition and parameter estimation with CNNs" (arXiv 2012.03216, JAES)

| Claim | Status | Source text | Note |
|---|---|---|---|
| >80% classification over 13 distortion/overdrive/fuzz | CONFIRMED | Abstract: "13 overdrive, distortion and fuzz guitar effects … Classification accuracy was above 80% … the mean absolute error is in most cases below 0.05". Table 4: 81.3–91.4%. | These are plugin emulations in a matched domain. Settings estimation (SetNetCond) is **conditioned on the true effect class**. |
| BSD-3 code | CONFIRMED | `mcomunita/gfx_classifier` (master) and `gfx_classifier_models_and_results`: "BSD 3-Clause License". | — |

URL: https://arxiv.org/html/2012.03216v1

## 12. PEACE (arXiv 2610.03405, ISMIR 2026; Braun & Finkelstein)

| Claim | Status | Source text / number | Note |
|---|---|---|---|
| Reverb R@1 23.1 vs AFx-Rep 8.4, Fx-Encoder++ 2.3, CLAP 1.8 | CONFIRMED | Table 3, "RIR retrieval (gallery 1,831)": PEACE scratch BoxGraph q_A 23.1 (R@10 53.5); AFx-Rep 8.4 (28.3); Fx-Encoder++ 2.3 (11.6); LAION-CLAP 1.8 (10.7). | Content is mismatched, but the content is **vocals** (jaCappella) convolved with ReverbFX RIRs. Reverb only; no amp and no guitar. |
| Licence | **CORRECTED** | README: "Code is MIT-licensed. The released weights are CC BY-NC 4.0: non-commercial use with attribution." HF `davidbraun/peace`: `license: cc-by-nc-4.0`. | Report A listed "MIT code; weights … location unconfirmed", and the earlier notes said "Yes, once weights confirmed under MIT". The weights are **non-commercial**, so they are excluded under the project rule; retrain from the MIT code if needed. |

URL: https://arxiv.org/html/2610.03405 · https://huggingface.co/davidbraun/peace

## 13. Fx-Encoder++ (arXiv 2507.02273, ISMIR 2025)

| Claim | Status | Source text / number | Note |
|---|---|---|---|
| R@1 19.9 true stems vs ~7.1 separated | CONFIRMED | Table 3 (MUSDB, instrument-wise): Target Instrument (Oracle) 19.9; USS / MSS 2.1 / **7.1**. AFx-Rep: 14.0 → 2.1 / 4.6. "even when using high-quality source separation, we observe a clear gap" | MSS is Hybrid Demucs and USS is universal sound separation. The pool has 500 candidates. |
| AFx-Rep mixture R@1 16.7 | CONFIRMED | Table 2 (MUSDB18, Mixture column): AFx-Rep 16.7 / 30.2 / 36.9 (R@1/5/10); Fx-Encoder++ 19.4. | On the "Other" stem (where guitar sits), AFx-Rep R@1 is 10.9 and Fx-Encoder++ 17.4. |
| Licence CC BY-NC 4.0 | CONFIRMED | `SonyResearch/Fx-Encoder_PlusPlus` LICENSE: "Attribution-NonCommercial 4.0 International". HF `yytung/fxencoder-plusplus`: no licence tag. | Excluded. |

URL: https://arxiv.org/html/2507.02273v1

## 14. MERT level erasure and MARBLE

| Claim | Status | Source text / number | Note |
|---|---|---|---|
| MERT LUFS probe R² ≈ 0 (arXiv 2607.03806) | CONFIRMED | "All probes yield R² ≈ 0 or below on MERT, Wav2Vec2 and WavLM-Large … MERT applies it [normalisation] in its convolutional feature extractor, which removes global amplitude scaling". | The paper is a **CLAP** probing study (DAFx 2026, BandLab); MERT appears in its §4.3 generalisation check. It probes *global* loudness. "Therefore removes the drive cue" (Report A) is an inference: drive also changes spectral content, which MERT does see. |
| MARBLE NSynth pitch 92–94% vs instrument 71–73% | CORRECTED (minor) | MARBLE Table 3, MERT models: NSynth Pitch 92.3–94.4; NSynth Instrument **70.4–72.6** (v1-95M: 92.6 / 70.7; v1-330M: 94.4 / 72.6). | Instrument is 11-family classification and pitch is MIDI-pitch classification. Accuracies across tasks with different class counts are a loose basis for "pitch-dominated". |

URL: https://arxiv.org/html/2607.03806 · https://arxiv.org/html/2306.10548v4

## 15. Comunità, Steinmetz & Reiss 2025 (arXiv 2502.14405)

| Claim | Status | Source text / number | Note |
|---|---|---|---|
| Objective metrics vs listeners \|ρ\| ≈ 0.4–0.6 | **CORRECTED** | Table 8, Spearman vs MUSHRA, **Overall**: L1 −0.332, MR-STFT −0.427, MSE −0.314, ESR −0.311, MAPE −0.339, FAD-VGGish −0.430, FAD-PANN −0.303, FAD-CLAP −0.406, FAD-AFx-Rep −0.417. **Overdrive**: −0.061 to −0.361 (MR-STFT −0.277). Distortion up to −0.613 (FAD-CLAP). Fuzz −0.31 to −0.51. Compression ≤ 0.19. | The correct figure is **overall \|ρ\| 0.30–0.43; overdrive ≤ 0.36**. The 0.4–0.6 range holds only for distortion and fuzz. The ratings are 350 MUSHRA scores of model outputs vs a same-content reference, many rated ≥ 80. Range restriction depresses ρ, so this is not a "ceiling". |

URL: https://arxiv.org/html/2502.14405

## 16. MUSHRA-1S (arXiv 2509.19219)

| Claim | Status | Source text | Note |
|---|---|---|---|
| "may pose a higher cognitive effort" | **MISLEADING** | "We hypothesized that a direct comparison of four similar-quality codecs may pose a higher cognitive effort and may require more responses than single-condition tests. **The pattern did not change with additional responses.**" | This is an untested-then-unsupported hypothesis about speech codecs, not a finding. |
| ~7 stimuli guidance | CORRECTED (minor) | "ITU-R BS.1534-3 recommends at most 12 stimuli (ideally 7) for lab-based tests [4], and in crowdsourcing we find 5–6 is optimal". | The cap is 12; 7 is the ideal. |

URL: https://arxiv.org/html/2509.19219v1

## 17. Report B: "A 2025 inference-time-optimisation extension … incorporating a prior substantially improved parameter estimation in a low-data effects-transfer setting"

| Claim | Status | Source text / number | Note |
|---|---|---|---|
| Identity of paper | FOUND | Yu, Martínez-Ramírez, Koo, Liao, Mitsufuji, Fazekas, "Improving Inference-Time Optimisation for Vocal Effects Style Transfer with a Gaussian Prior", arXiv 2505.11315, WASPAA 2025. | — |
| "substantially improved parameter estimation … low-data" | CONFIRMED (numbers) / **MISLEADING** (as support for a research prior) | "The proposed calibration reduces the parameter mean squared error by up to 33%"; "Subjective evaluations with 16 participants confirm the superiority of our method in limited data regimes." Table 1 PMSE: AFx-Rep α = 0 7.756 → α = 0.1 5.168; **Mean preset 5.310**; NN-θ 4.145. | The prior is a Gaussian over **365 DiffVox vocal presets**, a population prior, not song-specific information. Its PMSE gain only reaches the mean-preset baseline ("the best ones are comparable to the mean baseline"). In listening, the regression vs AFx-Rep+prior difference was "not statistically significant … (p = .117)". It is vocal effects with differentiable DSP, not guitar. |

URL: https://arxiv.org/abs/2505.11315

## 18. CDPAM (Manocha et al., arXiv 2102.05109)

| Claim | Status | Source text | Note |
|---|---|---|---|
| Correlates with listeners across perturbation datasets | CONFIRMED | "CDPAM correlates well with human responses across nine varied datasets." | The metric is speech-oriented (trained on speech perturbations), as Report B itself caveats. |

URL: https://arxiv.org/abs/2102.05109

## 19. ITU-R BS.1534 / BS.2132

| Claim | Status | Source text | Note |
|---|---|---|---|
| BS.1534 = multi-stimulus intermediate quality | CONFIRMED | "BS.1534: Method for the subjective assessment of intermediate quality level of audio systems" (current BS.1534-3, 10/2015). | — |
| BS.2132 = multiple stimuli without a given reference | CONFIRMED | "BS.2132: Method for the subjective quality assessment of audible differences of sound systems using multiple stimuli without a given reference" (BS.2132-0, 10/2019). | It targets audible *differences* without a reference. A "closer to this record" task has a reference, so BS.1534-style principles fit better. |

URL: https://www.itu.int/rec/R-REC-BS.1534/en · https://www.itu.int/rec/R-REC-BS.2132/en

## 20. Kammoun, Alameda-Pineda & Leglaive (arXiv 2510.26299)

| Claim | Status | Source text / number | Note |
|---|---|---|---|
| UTMOS 3.54 vs 2.72 continuous vs discrete DAC | CONFIRMED | Table 1: C-NAR UTMOS 3.54 vs D-NAR 2.72 (C-AR 3.61, D-AR 2.76); "on average, +0.80 UTMOS". | This is **speech** enhancement with DAC 16 kHz (12 codebooks). UTMOS is a neural MOS predictor, not listening. The continuous predictions are *re-quantised* before decoding. A non-codec baseline (DPTNet) gets 3.38 UTMOS with a better dWER (10.75 vs 13.48). |

URL: https://arxiv.org/html/2510.26299v3

## 21. Licences for components and search tools

| Item | Status | Source | Note |
|---|---|---|---|
| EfficientAT MIT | CONFIRMED | `fschmid56/EfficientAT` LICENSE: "MIT License Copyright (c) 2022 Florian Schmid". | — |
| LAION-CLAP Apache-2.0 | CORRECTED (nuance) | Repo `LAION-AI/CLAP` LICENSE = **CC0 1.0**; original checkpoints HF `lukewys/laion_clap` = cc0-1.0; HF ports `laion/larger_clap_music`, `laion/clap-htsat-unfused` = apache-2.0. | Apache-2.0 applies only to the HF `transformers` ports. Both licences are permissive, so nothing changes. |
| Basic Pitch Apache-2.0 with CoreML | CONFIRMED | LICENSE "Copyright 2022 Spotify AB Apache License Version 2.0"; README: "converted to CoreML, TensorFlowLite, and ONNX … CoreML will be installed on MacOS". | — |
| dasp-pytorch | CONFIRMED Apache-2.0 | `csteinmetz1/dasp-pytorch` LICENSE: Apache License 2.0. | — |
| pycma BSD-3 | CONFIRMED | `CMA-ES/pycma` LICENSE: "The BSD 3-Clause License Copyright (c) 2014 Inria". | FXRepBench pins `cma==4.4.4` (BSD-3-Clause). |
| Optuna MIT | CONFIRMED | `optuna/optuna` LICENSE: "MIT License Copyright (c) 2018 Preferred Networks, Inc." | — |
| BoTorch MIT; ships PairwiseGP? | CONFIRMED (both) | LICENSE "MIT License Copyright (c) Meta Platforms"; `botorch/models/pairwise_gp.py`: `class PairwiseGP`, `class PairwiseLaplaceMarginalLogLikelihood`; `botorch/acquisition/preference.py`: `AnalyticExpectedUtilityOfBestOption`, `qExpectedUtilityOfBestOption`, `PairwiseBayesianActiveLearningByDisagreement`. | Report A's "unverified" can be dropped: preferential BO is supported out of the box. |
| sequential-line-search MIT | CONFIRMED | `yuki-koyama/sequential-line-search` LICENSE: "Copyright (c) 2017 Yuki Koyama Permission is hereby granted, free of charge …" (MIT text). | — |

---

### Side checks (not in the list, found while verifying)

- **Fx-Encoder (original) MIT:** confirmed (`jhtonyKoo/music_mixing_style_transfer` LICENSE: "MIT License Copyright (c) 2023 Junghyun (Tony) Koo").
- **RLAT style transfer (ITO, cross-instrument):** z_T MRSTFT 0.647 vs AFx-Rep 0.832 vs Fx-Encoder++ 1.144 (Table 5). Its processing-oriented embedding does help search when content differs.
- **GOAT:** Reports A (25.85 h of amp renders) and B (29.5 h) are both right. 29.5 h is the total; 25.85 h is the standard-tuning part.
