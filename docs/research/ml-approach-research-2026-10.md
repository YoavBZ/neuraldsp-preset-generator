# ML approach research, October 2026

No method has yet been shown to beat today's starting presets on held-out songs. The approach most likely to work is a **shortlist system built around a set-valued preset ranker**, and the project has never tried that ranker in the right conditions. The ranker reads the separated guitar stem and scores every preset in a dry menu. It is trained on plugin renders that have been **mixed into real backing tracks, mastered, and passed back through the same separator the product uses**, and its labels allow several presets, and several amps, to be right at once. Web research sets the tone class (clean or crunch), the ranker narrows the menu to 2–3 options, and the user's ear makes the final pick. The current rebuilt-DI chooser stays on as the measured baseline, and as the way to play candidates on the song's own notes.

This bet is chosen for two reasons. First, the three levers that recent work shows closing a render-to-real gap are exactly the ones the project's failed encoder and translator lacked. Those levers are training on the test condition (14.5% → 81.7% top-1 on synthetic instrument mixtures), training on pairs with different notes, and wide tone and player variety (22.8 → 79.0 F1 on unseen guitar tones). Second, the published alternatives fail on the brief's own terms: ST-ITO's authors say it "does not work well" for guitar tone matching, and its AFx-Rep embedding tracks true quality at a Spearman correlation of only 0.36–0.44, even on easier data.

The ranker's ceiling is the menu oracle: about −0.10 to −0.19 against the best fixed start on clean and crunch. The user is right to doubt that "a perfect DI only buys a little". That figure describes a **dry 111-preset menu, scored by a judge that is deaf to treble on some parts and nearly blind to drive**, and no continuous-settings search has ever been run with a passing control. So the first things to run are measurements, not models:

- a zero-render audit of candidate song representations;
- a ~18k-render continuous-headroom pilot with a planted-target control;
- a ~40k-render "DI degradation ladder".

Together these cost under 60k renders, and they decide which route gets the remaining budget. The whole programme fits in about 110k committed renders (up to ~180k if every optional branch opens). It should end in **one pooled, pre-declared held-out test**, because no single held-out set has the power to detect a −0.05 effect.

## How to read this report

Every claim carries a tag:

- **[V]**: verified at source by the researchers (paper, licence file or model card opened).
- **[V-earlier]**: verified in one of the project's earlier literature rounds and not re-opened this time.
- **[S]**: seen only in a search-result summary, so weaker.
- **[P]**: this project's own measured result, from the brief or the repository docs (paths given).
- **[I]**: inferred, meaning reasoning or arithmetic by the researchers or this writer.

Scores are the project's **mean log ratio** of the chosen preset's distance against a comparator's: negative is closer, −0.105 ≈ 10% closer, and listening has validated only differences of at least 0.15 [P]. "Today's start" means the product's class-routed starting preset: on Morgan, Royally Ambient, Pedal Platform Clean or Low-Watt Americana for clean, and Modern Metal (Pick Hard), Hair Metal or AC20 Mid-Gain Drive for crunch; on Tone King, Vintage Trem or Squishy Lead. The five failure modes the brief documents are referred to by code throughout:

| Code | Failure mode |
|---|---|
| F1 | The domain gap between renders and real records |
| F2 | No DI exists for songs |
| F3 | Too few crunch bands to reach a decision |
| F4 | The notes played move features more than the tone does |
| F5 | Separation artefacts |

## 1. A set-valued ranker trained in the song's own conditions ranks first

Ten approaches are worth ranking. The ranking weighs expected gain against the odds of success. It does not weigh evidence of success alone: approach 2 has more measured evidence than approach 1, but a lower ceiling once compared with today's starts.

### Table 1a. Expected gain, evidence and needs

| Rank | Approach | Expected gain and evidence (licences) | Needs |
|---|---|---|---|
| 1 | **Set-valued direct ranker trained in the test condition.** Stem → scores over the dry menu, trained on renders mixed into real backings, mastered and re-separated. Labels are all presets within a judge margin. It may also take the rebuilt-DI chooser's scores as an input. It outputs a top-k list. | **Top-1 roughly −0.03 to −0.07 against today's start; best-of-3 with a good ear up to about −0.10** [I]. The ceiling is the menu oracle, −0.10 to −0.19 on clean and crunch [P, `docs/set4-confirmation-results.md`, `docs/set5-test-results.md`].<br><br>No guitar render-to-record result exists anywhere [V, by absence across the papers opened]. The positive evidence is indirect:<br>• Training on mixtures rather than separating first took timbre retrieval from 14.5% to 81.7% top-1 (synthetic instruments) ([Le Vaillant & Molle](https://arxiv.org/html/2509.13285)) [V].<br>• StemFX (code and weights MIT), which trains through a separator, was the only method above the low anchor on real mixes: MUSHRA 60.6 vs 54.9 ([StemFX](https://arxiv.org/html/2607.15634)) [V].<br>• Removing different-content training pairs worsened RelFx from 1.399 to 1.876 L_d ([RelFx](https://arxiv.org/html/2608.10573)) [V].<br>• Tone diversity took unseen-tone F1 from 22.8 to 79.0 ([EGDB-PG](https://arxiv.org/html/2504.07406)) [V].<br>• Point regression of equivalent settings "degrades performance" ([Hayes et al.](https://arxiv.org/abs/2506.07199)) [V]. | **~43k renders** (~5 h). htdemucs_6s passes on half of them (time unmeasured; probably an overnight job off the render server [I]). Training: 1–2 h on MPS for a small CNN, or overnight to fine-tune AFx-Rep. **~4 GB disk if log-mels are stored instead of WAV** [I]. |
| 2 | **Rebuilt-DI chooser, repaired by a route the DI degradation ladder picks.** The candidates are continuous DAC-latent regression (E1′), mel prediction plus the BigVGAN-v2 vocoder, or unit-selection resynthesis. | **Measured:**<br>• −0.087 against the then-start on fresh set 4, which is 45% of the oracle (76% on development) [P, `docs/set4-confirmation-results.md`].<br>• The stem keeps 75% of the amp-track gain [P, `docs/songs-check-results.md`].<br>• Against today's crunch start, C′ reaches only −0.023, with the oracle at −0.129 [P, `docs/set5-test-results.md`].<br>• Harmful on high-gain (+0.318) [P].<br><br>**Ceiling:** a DAC 4-codebook round-trip of the true DI keeps 83–91% of the oracle edge [P, `ml/egvae-lite:docs/egvae-lite-plan.md`], so a much better DI would be worth up to about −0.12 [I].<br><br>**Literature:**<br>• EG-VAE beats DPTNet only slightly on unseen Morgan tones (mel 1.19 vs 1.27) and has no code or weights ([EG-VAE](https://arxiv.org/html/2608.05513)) [V].<br>• Continuous codec latents beat discrete tokens in speech enhancement (UTMOS 3.54 vs 2.72) ([Kammoun et al.](https://arxiv.org/html/2510.26299v3)) [V].<br><br>DAC is MIT ([repo](https://github.com/descriptinc/descript-audio-codec)) [V]; BigVGAN-v2 is MIT ([card](https://huggingface.co/nvidia/bigvgan_v2_44khz_128band_512x)) [V]. | Ladder **~40k renders** (4–5 h) with no training. Then one route: E1′ is a 1–3-day MPS job [I]. |
| 3 | **Continuous-settings search beyond the menu.** CMA-ES warm-started from the chosen preset, with time effects as a separate stage. On songs it runs through the rebuilt DI, or through the ear via preferential Bayesian optimisation. | **Unmeasured.**<br>• The only judge-scored own-DI search gave −0.147 (p 0.078), but its positive control failed and it optimised the retired v3 score [P, `docs/no-di-rule-under-the-judge-results.md`].<br>• Menu size alone moved clean PR12 headroom from −0.267 to −0.291 [P, `docs/amp-reach-results.md`].<br>• On 14 of 25 parts, another amp's preset beat AC20's by at least 0.15 [P].<br>• In the literature, search adds 23.07 vs 18.18 dB SI-SDR given the true dry signal ([Okita & Katayose](https://arxiv.org/html/2604.22276)) [V], and a learned proposal plus CMA-ES beats the best of 512 random candidates, 0.71–0.74 vs 0.770 ([FXRepBench](https://github.com/meteroad/fxrepbench), Apache-2.0) [V]. | Pilot **~18k renders** (~2 h), full measurement 48k. About 1,500 renders per song per amp (~10 min) in the product [I]. |
| 4 | **Hybrid shell: research → class; model → 2–3 options; ear → pick by pairwise comparison.** | **Perfect-ear best-of-4 is −0.18 to −0.20 against the template** [P, `docs/song-only-shortlist-results.md`].<br>• A researched four-list did no better than four random presets [P].<br>• Routing by the part's documented sound cut class regret from 0.140 to 0.059, in-sample [P, `docs/generate-routing-recheck-results.md`].<br>• The real ear captured only 0.25–0.34 of the perfect-ear gain on a four-way page using other notes, and did not beat a song-blind taste [P, `docs/listening-check-results.md`].<br>• Two-way choices on the part's own notes went 17/21 [P].<br>• Listening practice caps comparisons at about 7 items; comparing four similar systems "may pose a higher cognitive effort" ([MUSHRA-1S](https://arxiv.org/html/2509.19219v1)) [V]. | No extra renders beyond k per song; listening sessions. |
| 5 | **Time-effect estimators (DSP, no learning).** Delay from onset autocorrelation, tremolo from envelope periodicity, reverb via an RT60 regressor or the PEACE/AFx-Rep embeddings. | **The judge cannot score this.** Effects moved it by +0.001 on dry amp tracks [P, `docs/generate-routing-results.md`]. Hinrichs found slapback and feedback indistinguishable by ear below feedback 0.3 ([EURASIP 2022](https://asmp-eurasipjournals.springeropen.com/articles/10.1186/s13636-022-00257-4)) [V]. PEACE (MIT code) beats AFx-Rep on reverb retrieval with mismatched content, R@1 23.1 vs 8.4 ([PEACE](https://arxiv.org/html/2610.03405)) [V]. Never run, despite round 2 recommending it [P]. | No renders. Days of DSP work. |
| 6 | **Learned DI-free distance (tone encoder plus note-normalised features) used for search.** | Same components as approach 1, but used as a metric that an optimiser pushes against. The literature ceiling for objective metrics against listeners is about \|ρ\| 0.4–0.6 ([Comunità et al. 2025](https://arxiv.org/html/2502.14405)) [V-earlier]. | As approach 1, plus ~11k renders for the judge-agreement check. |
| 7 | **ST-ITO with frozen AFx-Rep (Apache-2.0).** | **Low.**<br>• The authors: "does not work well for … guitar tone matching" ([ST-ITO](https://arxiv.org/html/2410.21233)) [V].<br>• Spearman against true quality is 0.36–0.44; selected 1.080 vs oracle 0.540 on same-recording data ([FXRepBench](https://github.com/meteroad/fxrepbench)) [V].<br>• Single-effect top-1 is 3.0% ([StemFX](https://arxiv.org/html/2607.15634)) [V]. | 0 renders to audit. |
| 8 | **Full EG-VAE reimplementation (E2).** | Small objective gain in the paper (above), only on renders; the authors released no weights [V]. | Around 758 h of renders in the paper; **days of MPS training** [I]. |
| 9 | **Symbolic DI** (transcribe, then resynthesise from owned DI notes). | Bounded by transcription on driven guitar. On crunch, non-tone-aware models drop to 47.5 (hFT) or 12.8 (MT3-Guitar) onset F1 ([EGDB-PG](https://arxiv.org/html/2504.07406)) [V]. Basic Pitch scores 66.1 on clean commercial jazz ([Riley et al.](https://arxiv.org/html/2402.15258v1)) [V]. | Only one ladder rung to test. |
| 10 | **Large-scale synthetic DI pretraining** (SynthTab, Karplus-Strong). | SynthTab-only zero-shot transfer is weak: GuitarSet tablature F1 43.1 vs 80.1 in-domain ([SynthTab](https://arxiv.org/html/2309.09085v4)) [V]. "The main performance bottleneck lies … in the fidelity of the audio rendering" ([procedural guitar](https://arxiv.org/html/2508.07987)) [V]. | ~2 TB of data (SynthTab); the licence is unclear. |

### Table 1b. Risk, cheapest decisive experiment, and how each approach meets the failure modes

| Rank | Main risk | Cheapest decisive experiment | How it handles F1–F5 |
|---|---|---|---|
| 1 | It repeats the encoder failure: fits renders, misses records. Separator artefacts that correlate with brightness become shortcuts [I]. | **Zero renders:** R3 transfer and R4 separation-survival screens on existing panels (section 5), plus a domain-classifier probe (can a classifier tell augmented render stems from real stems? It should not exceed 75%). **Then** a 43k-render pilot gated on development parts. | **F1:** real backings, mastering, separator in the loop, and a domain probe before any use. **F2:** no DI needed. **F3:** set-valued labels and Recall@k give a better-powered outcome. **F4:** same-DI hard negatives, a content vector and note-normalised features. **F5:** trains on htdemucs output. |
| 2 | Any trained de-amper meets the same render-to-record gap. Regressed latents decode to "dirty" artefacts [I]. | **The DI degradation ladder:** corrupt the *true* DI in controlled ways and see which corruptions lose the oracle's picks. 40k renders, no training. | **F4:** avoided by construction (same notes). **F2:** answered by rebuilding the DI. **F1 and F5:** handled only if training runs through the separator. |
| 3 | The optimiser exploits the judge (treble-deaf, drive-blind) or the rebuilt DI's artefacts. On high-gain the oracle's headroom was already out of the rebuilt DI's reach [P, `docs/ROADMAP.md:329`]. | **The headroom pilot with true DIs and a planted-target control** (plan 3). | **F4:** same-notes scoring. **F3:** a within-part paired contrast on development. **F2:** not avoided for songs. |
| 4 | The ear cannot compare across different notes, and may follow a taste for lighter gain: the lighter option was chosen 11/13 times [P, `docs/starting-preset-listening-results.md`]. | **Offline Recall@k(τ = 0.15)** of the starts, house-k, random-k and the model on development (existing renders). **Then** a declared pairwise listening run on the song's notes, played through the rebuilt DI. | **F3:** listening trials add N. **F4:** plays the song's own notes. |
| 5 | Mix and room reverb get attributed to the guitar chain [I]. | Score detectors on development amp tracks against the parts' documented effects; listen. | Kept apart from the dry chooser, so it cannot pollute it. |
| 6 | An optimiser drives the metric into its blind spots [I]. | R5 judge agreement (section 5). | As approach 1. |
| 7 | Content and mix artefacts dominate the embedding [V]. | The R1/R3/R4 audit (zero renders). | Does not handle F4. |
| 8 | Big cost; no evidence on real input [V]. | Only if the ladder says codec latents are the route. | F1 not handled. |
| 9 | Onset errors break the time-aligned judge [I]. | Ladder rung 8. | Handles F5 by construction, not F1. |
| 10 | Wrong dynamics for driving a preamp [I]. | Train with and without synthetic DIs; test on real records. | Does not touch F1, which sits on the record side [I]. |

Approach 1 leads despite having no result of its own, and the reason should be said plainly. The project tried learning from renders three times (kill tests, sound-description translator, contrastive encoder), and all three failed to transfer [P]. All three were trained on **solo renders, with a narrow pool of DIs and no separator in the loop**. Mel-domain augmentation stood in for real mix conditions [P, `docs/tone-encoder-plan.md`]. The 2026 evidence says unseen *sources* (players, content) are the main bottleneck, not unseen processors ([RLAT, Sony AI](https://arxiv.org/html/2608.28127)) [V]. It also says training in the target condition is the strongest fix [V, sources above]. The project has never run that experiment.

The adversarial case is equally strong. Approach 1 inherits a DI pool of about 136 parts from about 28 bands, and diversity is the lever that matters. It also inherits the judge's blind spots through its labels. Approach 2 is therefore not a fallback but a **parallel arm**. It already has measured held-out signal, it is the only way to play candidates on the song's own notes, and its scores can feed approach 1 as an input, so a stacked ranker should do no worse than the chooser on development [I].

Approach 4 is the product frame for 1–3, not a competitor. Today it is half-built: routing, a second start, and an optional audition page [P, `docs/ROADMAP.md`].

## 2. Run measurement first: a sequenced programme and three plans

### 2.0 The merged programme, and what to run first

The researchers proposed overlapping experiments. These are merged below so that renders are shared and each step decides the next. The overlaps were:

- an AFx-Rep audit;
- an R0–R5 representation ladder;
- a DI degradation ladder;
- a continuous-headroom pilot;
- a direct ranker.

| Step | What | New renders | Wall time | What it decides |
|---|---|---|---|---|
| **0a** | **Variance split:** crops within parts within bands, for today's 0.101 between-band SD | 0 | hours | Whether scoring many crops per part buys power (section 3) |
| **0b** | **Offline Recall@k(τ = 0.15) and best-of-k gain:** today's two starts, house-k, random-k and the C′ chooser, on development | 0 | hours | The bar every model must beat for the hybrid |
| **0c** | **Drive-bias check on existing C′ picks:** are they systematically cleaner than the oracle's? | 0 | hours | Whether "dirty" rebuilt DIs bias picks toward lighter gain (prediction in plan 2) |
| **0d** | **Representation ladder R0–R4,** with the AFx-Rep audit folded in (section 5) | 0 | ~1–2 days | Whether *any* DI-free feature survives notes, records and separation; kills approach 7 cheaply |
| **0e** | **Measure separator speed:** htdemucs_6s on 100 ten-second clips on MPS and CPU | 0 | minutes | Whether separator-in-the-loop training is affordable |
| **1a** | **Headroom pilot, first look,** with the planted-target control (plan 3) | ~18k | ~2 h | Whether continuous settings open real room beyond the menu |
| **1b** | **DI degradation ladder** (plan 2) | ~37–40k | 4–5 h | What a rebuilt DI must preserve; which DI route, if any, to build |
| **2** | **Set-valued ranker pilot** (plan 1); reuses the ladder's true-DI × menu renders as real-part labels | ~43k | ~5 h + separation overnight | Whether approach 1 transfers to records |
| **3** | **Optional branches:** full headroom (48k); the DI route the ladder picks (≤30k); encoder fine-tune (≤30k) | ≤108k | — | Only branches whose gates passed |
| **4** | **Listening calibration,** merged: judge v3 (~55 trials), disagreement (MAD) trials for any DI-free metric, and a pairwise shortlist test | 0 | sittings | Which measure to trust at small margins |
| **5** | **One pooled, pre-declared held-out test** of the survivors (section 2.4) | ~5k | ~1 h | The only held-out spend |

**Run step 0 first.** It costs no renders, and step 0d alone can retire AFx-Rep, ST-ITO and the DI-free search family in a day or two.

**Then run 1a before 1b.** It answers the user's central doubt in about two hours, and it decides whether approach 3 gets any budget.

**Then run 1b before step 2.** The ladder's rung-1 renders (each true DI through all 111 presets) are the real-part labels that the ranker needs anyway, so running it first means no render is wasted.

Committed renders through step 2 come to about **100–110k**. With every branch open the total is about 180k, under the 200k flag.

**Disk is the tighter limit.** One 10-s, 48 kHz, 16-bit mono clip is about 0.96 MB, so 40k ladder renders kept as WAV would take ~38 GB of the 65 GB free [I]. The rule should be: score renders as they arrive, keep only distances and log-mel features (~50 KB per clip), and keep FLAC for a small audit subset only [I].

### 2.1 Plan 1: set-valued ranker trained in the test condition

**Data and generation.**

DIs:

- about 200 ten-second DI clips from the development parts, split into training folds *by band*, and weighted towards crunch;
- Guitar-TECHS (CC BY 4.0) [P];
- the 18 electric DIs of the Five-guitar dataset (CC BY 4.0, [Zenodo 4988354](https://zenodo.org/records/4988354)) [V], once checked to be true DIs;
- GOAT, only if access is granted and its non-commercial terms are accepted (section 4).

Renders, in three batches:

1. **Each clip through all 111 dry Morgan presets:** 22.2k renders.
2. **A pre-amp variant for half the clips,** with input level shifted ±4 dB and a random pickup EQ (a resonant low-pass peaking at 2–5 kHz, with its range calibrated on the Five-guitar and EGFxSet guitars) [I]: ~11k renders. Level is the strongest drive confound, so this matters most for crunch [I].
3. **About 10k "off-menu target" renders:** a DI through random continuous settings, standing in for a real record's unknown tone. Each needs only one render, because its labels come from the menu renders of the same DI that already exist [I]. This is what teaches the model to *rank near-misses*, the task the project's encoder was never trained for [I, from `docs/tone-encoder-plan.md`].

Labels are set-valued:

- For a target rendered through DI *d*, the positives are all menu presets whose render through *d* lies within ε of the best, under the judge.
- ε is set from the judge's own split-half noise: the median best-vs-second gap is 0.043 [P, `docs/closeness-review-2026-10-10.md`].
- A listwise loss on −distance carries the full ordering [I].

Augmentation runs on the fly, with no renders:

- mix into band-disjoint real backings (development sessions minus their guitars; Slakh2100, CC BY 4.0, as an extra pool) at −12 to +3 dB guitar-relative;
- add random bus compression and limiting to −14…−8 LUFS (dasp-pytorch, Apache-2.0, cited in round 3) [P, `docs/research/round-3-supervised-preset-model.md`];
- run **htdemucs_6s (MIT) on 50%** and train on the stem.

Real-part labels come from the ~136 development parts' true-DI × menu oracle rankings. These are the records' own labels: few, but real, and off-menu by nature. They are used in leave-band-out fine-tuning, not only in testing [I].

Tone King has no menu yet. Build a dry Tone King factory menu the same way, and render it once the Morgan pilot passes [I].

**Model, code and weights.** The input is level-preserving: no per-clip loudness normalisation, because the drive cue lives in level [V, MERT erases level, [probe study](https://arxiv.org/html/2607.03806)]. The model is built in three parts:

- **Encoder T,** in three options run in parallel:
  - a small CNN on 128-band log-mel, from scratch;
  - EfficientAT mn10 (MIT, [licence](https://github.com/fschmid56/EfficientAT/blob/main/LICENSE)) [V];
  - AFx-Rep's CNN14 fine-tuned (Apache-2.0, [weights](https://huggingface.co/csteinmetz1/afx-rep)) [V].
- **Side inputs:**
  - the note-normalised feature block N and the content vector c (section 5), built from Basic Pitch note masks (Apache-2.0, ships CoreML; [repo](https://github.com/spotify/basic-pitch)) [V];
  - optionally, the C′ chooser's 111 judge scores, so the model is stacked on top of the chooser [I].
- **Head:** 111 outputs, trained with multi-label cross-entropy plus a listwise loss.

Two baselines run alongside. One is the project's own **records-only ridge** (8 octave-band powers → 45 SW50R preset risks), the "cheap direct-ranker test" never run [P, `docs/research/direct-preset-ranker-proposal-2026-10-09.md`]. The other is today's start.

**Training on the Mac** [I]:

- small CNN: 1–2 h on MPS;
- EfficientAT: 3–6 h;
- AFx-Rep fine-tune: overnight.

Precompute log-mels on CPU. The project found torch.stft's gradient on MPS is wrong for signals longer than 65,536 samples [P], so no STFT may sit inside the MPS graph.

Separation is the bottleneck. Mega-53 takes ~102 s of wall time per 30 s on CPU [P, `docs/separator-upgrade-results.md`], about 200 h for 21k clips [I], so use htdemucs_6s and measure it first (step 0e).

**Pre-check.**

1. **Domain probe.** A logistic model on frozen features separating augmented render stems from real development stems must stay **below 75% accuracy**. If not, fix the augmentation before training [I].
2. **Real-amp positive control.** Each representation's frozen drive axis must order the Marshall JVM410H 0–10 gain sweep at **Spearman ≥ 0.8** [I]. The JVM set's licence is held by the project's own audit (section 4), so this is development-only use.

**Positive control.** On synthetic songs from held-apart *bands* (renders mixed, mastered and separated), top-5 containment of an ε-equivalent preset must reach **≥ 60%**, and top-1 regret must be at most half that of the constant start [I]. If this fails, the model or pipeline is broken. That is not a transfer failure.

**Development gate.** Write the gate before any result. It uses leave-band-out cross-validation over all clean and crunch development parts (not only the over-used 33), with band weighting. The ranker must pass all three:

1. **Recall@3(τ = 0.15)** beats house-3, random-3 and the ridge baseline.
2. **Band-weighted top-1 log ratio ≤ −0.05** against today's class-routed start *and* against leave-band-out constants. The in-sample starts have a 0.01–0.05 head start [P, `docs/closeness-review-2026-10-10.md`].
3. It is not worse than the C′ chooser, with wins in at least 60% of bands.

**Held-out test.** Only the pooled test in section 2.4.

**Stop if any of these happens:**

- the positive control passes but the development gate fails twice, with two different augmentation recipes (this reproduces the encoder failure, so close approach 1);
- the domain probe stays above 75% after two augmentation rounds;
- the real-part learning curve is flat from 22k to 43k renders. Do not scale towards 200k on render-domain gains alone [I].

### 2.2 Plan 2: DI degradation ladder, then one repaired DI route

**Data and generation.** Choose about 30 development parts with true DIs, stratified by band into clean and crunch, and avoid the over-used 33 where possible. Build these versions of the **true DI**, all at average-guitar balance and −22.9 LUFS [I]:

1. the true DI;
2. a DAC 44 kHz round-trip at 1, 2, 4 and 8 codebooks;
3. BigVGAN-v2 resynthesis from the true DI's log-mel;
4. Griffin-Lim from the true magnitude, so magnitude is kept and phase destroyed;
5. phase randomised above 1 kHz, and separately above 3 kHz;
6. the true DI plus C′'s error signal, at 0.25, 0.5 and 1.0 scale;
7. C′'s output with its spectral envelope replaced by the true DI's;
8. optionally, Basic Pitch transcription resynthesised from other bands' DI notes.

Each version is rendered through all 111 presets: about **30 × 12 × 111 ≈ 40k renders**, or ~37k if rung 1 is reused from existing oracle renders [I]. Every rung is scored under both judge v1 and v3, at no extra render cost.

**Model, code and weights.** The ladder itself needs no model. DAC is MIT, weights included ([repo](https://github.com/descriptinc/descript-audio-codec)) [V]; BigVGAN-v2 44 kHz is MIT ([card](https://huggingface.co/nvidia/bigvgan_v2_44khz_128band_512x)) [V]; Basic Pitch is Apache-2.0 [V]. The route after the ladder depends on its result:

- **If the Griffin-Lim and phase rungs keep the picks while the C′-error rungs lose them,** artefact energy is the failure, not phase. Build **E1′**: predict the continuous 4-codebook DAC latent (1024-d at ~86 frames/s [I]) from the stem. Train it with a multi-resolution mel loss through the frozen decoder, a latent MSE term, and a **"no added fizz" penalty** on rebuilt-DI energy where the true DI has none [I]. Train with the separator in the loop, on mixes rebuilt from the project's multitracks.
- **If the BigVGAN rung keeps the picks,** use the cheaper mel-predict-then-vocode route (as in [Distortion Recovery](https://arxiv.org/html/2407.16639), which has no code or weights [V]).
- **If DAC at 1–2 codebooks or the symbolic rung keeps the picks,** the judge needs very little detail. Favour unit-selection resynthesis or the DI-free ranker over any de-amping network.
- **If even mild corruption loses the picks,** no open model will get close enough (section 6), and the DI route should be closed.

**Training on the Mac.** The ladder needs none. E1′ is roughly 1–3 days on MPS for a transformer feeding a ~75M-parameter frozen decoder [I], with losses computed on segments of at most 65,536 samples (~1.49 s at 44.1 kHz) or on CPU, because of the MPS bug [P].

**Pre-check.** This is zero-render step 0c. The closeness review already found the network's picks **under-driven**: the gain knob sat below the oracle's on 43 parts against 14 [P, `docs/closeness-review-2026-10-10.md`].

That fits a mechanism: broadband error in the rebuilt DI drives the amp's nonlinearity into extra fizz, so the judge compensates by picking lighter presets [I]. The ladder's error-dose rungs test this directly. If confirmed, a cheap **drive-bias correction** becomes its own development arm: choose, among the chooser's top 3, the one with the most drive. It needs zero new renders, because the chooser's menu renders through rebuilt DIs exist [I].

**Positive control.** Rung 1 must reproduce the oracle exactly; that checks the pipeline. The 4-codebook rung must reproduce E0b, keeping at least 80% of the oracle's edge (E0b: −0.126 against an oracle of −0.131) [P, `ml/egvae-lite:docs/egvae-lite-plan.md`].

**Development gate.** Use the project's existing E2 rule against C′: a band mean ≤ −0.015 with a 90% upper bound below +0.03 earns held-out use; a lower bound above −0.02 means futile (7 degrees of freedom) [P, `ml/egvae-lite:docs/egvae-lite-plan.md`]. Add one condition: the pick drive bias must shrink.

**Held-out test.** Only the pooled test in section 2.4.

**Stop if** the BigVGAN, Griffin-Lim and DAC 1–2-codebook rungs all lose more than half the oracle's edge *and* the error-dose curve is smooth. In that case the judge needs a near-perfect DI that no open method gives, so move the budget to plan 1 [I]. Also stop if the chosen route fails its development gate twice.

### 2.3 Plan 3: continuous-headroom pilot, then search beyond the menu

**Data and generation** [I]:

- **Parts:** 6 development parts in about 6 bands for the first look, crunch-heavy, including parts where AC20 was weak; 12 parts for the full run. Use the true DI at −22.9 LUFS.
- **Search space:** one amp at a time; about 15–25 continuous parameters (gain, EQ, presence, master, pedal knobs, post-EQ). Cab, mic and pedal on/off go in an outer loop over the oracle's top 3.
- **Optimiser:** CMA-ES warm-started from the menu oracle, with step size about 0.15 of each range, population ≈ 12–14, 80–120 generations: ~1,500 renders per part and amp.
- **Render budget:** first look 6 × 1 × 1,500 = 9k, plus the **planted-target control** (below) at another 9k. Full run 12 × 2 × 1,500 = 36k, plus a 12k time-effects stage started from the best dry result.

The time-effects stage covers reverb mix, size and decay; delay time, feedback and mix; and modulation. It is scored dry and wet separately, because mix reverb is not the guitar chain [I].

**Model and code.** There is no model, only a search. Use any CMA-ES implementation; the researchers did not check optimiser licences (pycma, Optuna) this round. For the ear-in-the-loop version on songs, **Sequential Line Search / Sequential Gallery** is MIT ([repo](https://github.com/yuki-koyama/sequential-line-search); [paper](https://arxiv.org/pdf/2005.04107)) [V], and **BoTorch** is MIT ([repo](https://github.com/pytorch/botorch)) [V]. That BoTorch ships a pairwise-preference model is unverified [I].

**Training on the Mac.** None. The renders take ~2 h for the first look and ~6 h for the full run.

**Pre-check.** Find out why the previous search's control failed before re-running it [P, `docs/no-di-rule-under-the-judge-results.md`].

**Positive control (planted target).** Render each pilot part's true DI through a *random off-menu setting*, and treat that render as the "record". Starting from the menu oracle, the search must:

- end within the judge's split-half noise of the planted target;
- beat the menu oracle by at least 0.10;
- do both on at least 5 of 6 targets.

This shows the optimiser can find a known answer before its real result is read [I].

**Anti-gaming protocol.** Optimise on half A under the **sum of judge v1 and v3**. Report on half B under v1, v3 and the average-guitar measure. Add a tonal/temporal split, a drive-bias check and a treble/fizz excess check. Finish with a listening audit: reference vs continuous optimum vs menu oracle vs start, 12 parts × 2 crops, with repeats [I].

**Development gate (the readout):**

- **Continuous minus menu oracle on half B ≤ −0.10** under both judges refutes "a perfect DI only buys a little" in its menu framing, and opens approach 3 for songs.
- **About 0** (≥ −0.03) means the menu was not the bottleneck: the floor between a real amp and a plugin dominates.

Also report the floor-normalised headroom H (section 3). For a song-side product, a further gate applies: the search run through C′'s rebuilt DI must beat C′'s menu pick, scored by the true-DI judge, on at least 60% of parts.

**Held-out test.** None for the measurement, which is development only. A song-side search product joins the pooled test.

**Stop if** the continuous gain is ≥ −0.03 under both judges. That parks search beyond the menu for good, and points the remaining effort at choosing well within the menu. If the planted-target control fails, fix the optimiser and interpret nothing.

### 2.4 The pooled held-out test, and why power is still too low for small effects

Every held-out set alone is under-powered, and an exact sign-flip test on k bands cannot reach p below 2^−k: 0.125 with 3 bands, 0.0156 with 6 [I]. Declare **one** test, after the development gates, for whichever approaches survive.

**Material.** Check the ledger first for band overlap between these sets [I]:

- set 5's clean and crunch parts (26 parts in up to 7 bands; this would be its second declared use) [P];
- set 4's 22 unused parts, restricted to clean and crunch (the count in scope is unknown; most are high-gain) [P];
- set 6's 3 in-scope crunch parts [P].

**Outcomes.** The primary outcome is the **band-weighted best-of-3 log ratio against today's class-routed start**, alongside **Recall@3(τ = 0.15)**. Top-1 log ratio is secondary.

**Analysis.** Use a Bayesian hierarchical model: bands random, class fixed, a half-normal prior on the band SD at about 0.1. Write the rules down beforehand: "helps" if P(effect < 0) > 0.9 and the posterior mean ≤ −0.05; "futile" if P(|effect| < 0.03) > 0.8 [I]. Expect about 10–12 in-scope bands if the sets do not overlap [I].

**Power.** Noncentral-t power with the band SD at 0.101 is:

| Bands | Power at −0.05 | Power at −0.10 |
|---|---|---|
| 9 | 0.39 | 0.86 |
| 12 | 0.49 | 0.94 |

[I; the project's own table gives 32% and 80% at 8 bands, `docs/stem-test-power.md`]. **A −0.10 effect is decidable when clean and crunch are pooled; a −0.05 effect is not, and a crunch-only claim is not decidable at all.**

**How to get more power:**

1. **Label more MedleyDB DIs by ear,** as set 6 did. 73 songs have electric-guitar raw tracks and only 5 parts are labelled [P]; licence terms as the project already applies them.
2. **Use listening trials as a high-N secondary outcome:** 2–3 trials per part, analysed with a mixed logistic model (section 3).
3. **Use synthetic songs with known answers** for every development decision, so real held-out bands are spent once.
4. **Get new sources** (section 4). None of them adds crunch bands of real records with DIs; only new recordings would. The brief rules recording out for the user, so section 4 lists the closest legal substitutes.

## 3. Measurement critique: "perfect DI only buys a little" is unmeasured, not small

**Keep the judge as a development instrument, but stop treating it as the definition of success.** It is repeatable, time-aligned and listening-validated for clear clean-to-crunch differences [P]. But it has four limits as a target:

1. **It only scores menu-reachable improvement relative to other menu items.** The oracle is the best of 111 dry presets [P].
2. **Its distances carry a large shared floor** (mic, room, cab, bleed, noise), so log ratios compress real changes [I]. Adding 12 dB above 5 kHz moved the distance by exactly 0 on parts with a dominant low fundamental. Winners were 13–25 dB too bright at 5–10 kHz on some clean parts. Once the spectrum matches, the judge "barely sees drive amount" (+0.05) [P, `docs/closeness-review-2026-10-10.md`].
3. **At small margins it disagrees with its own successor and with listening.** Moving to v3 changes the oracle's pick in 97 of 198 cells [P, `docs/judge-v3-results.md`]. On disagreement trials, the average-guitar measure beat the judge's preference 23/24 [P, `docs/avg-measure-listening-results.md`].
4. **Its decisions are made among near-ties:** the median best-vs-second gap is 0.043, only 10% of gaps clear the validated 0.15, and halves A and B pick different winners 27% of the time [P].

The listening support for the average-guitar measure also has a caveat: its pick was closer by spectral centroid in 25 of 30 trials, so ear and measure may both be tracking overall brightness [P].

**The headroom question.** Within the menu, the true DI's value is bounded at roughly **0.13–0.26** in log distance [P, A2 of the project digest], which is about the validated "clear difference" (0.15): audible, but modest. That reading is weak for three reasons:

1. **The menu is dry and fixed.** Menu size alone moved a gate [P, `docs/amp-reach-results.md`], and time effects are invisible to the judge [P].
2. **The baselines were partly chosen on the same parts,** which gives them a 0.01–0.05 head start [P].
3. **Many deciding tests had 9–40% power** [P, `docs/stem-test-power.md`, `docs/audit-2026-10-11.md`].

The headroom could also be *smaller* than it looks, if the real-amp-vs-plugin floor is large and fixed [I]. No literature measures how close a different amp model with tuned knobs can get to a recording of a real amp. Capture studies only cover copying *one* amp: MUSHRA ≥ 90 at lower gain ([Wright et al. 2020](https://acris.aalto.fi/ws/portalfiles/portal/41964332/Real_time_guitar_amplifier_emulation.pdf)) [V].

There is one more correction to the project's reasoning. **Coherence is not the mechanism.** E0b kept 83% of the oracle edge with the same 1–3 kHz coherence as C′ (0.20 vs 0.207), and the residual network had higher coherence but worse picks [P]. The DI ladder (plan 2) replaces coherence with a direct test.

**Proposal: seven changes.**

**First, headroom and floor.** Measure headroom directly with plan 3. Report a **floor-normalised headroom**, H = (d_start − d_best) / (d_start − d_floor), next to every log ratio [I]. d_floor is the judge distance between two simultaneous microphones of the same take (round 4's "second-mic yardstick"), or failing that the best distance any search reaches. A −0.13 log ratio can be 80% or 20% of what is reachable; H says which.

**Second, a product metric.** Make **Recall@k(τ = 0.15)** the primary metric for the product: the band-weighted share of parts where at least one of the k shown presets is within 0.15 of the oracle. Report it with best-of-k gain and k = 1…6 curves, against random-k and "class prior plus second start". The project already computes this quantity (house-4 0.61/0.46, random-4 0.42, template 0.29) [P, `docs/song-only-shortlist-results.md`].

**Third, the optimisation target.** Optimise against **v1 + v3**, never one judge alone. Finish the ~55-trial v3 listening calibration, choosing trials by **MAD competition** (stimuli where the measures disagree most). Fit P(listener agrees) against |Δ metric| with a lapse rate, and report the margin at which P = 0.75 [I]. That margin compares any two measures on one perceptual scale. Exact binomial counts to show true agreement of 0.90 / 0.80 / 0.75 / 0.70 are 8 / 18 / 23 / 37 decided trials [I]. A listener with repeat consistency 0.8 cannot exceed about 0.89 agreement [I].

**Fourth, a DI-free closeness ladder.** Build any DI-free closeness through four stages, V0 to V3 [I]:

| Stage | Test |
|---|---|
| V0 | On renders: same preset with different notes must sit closer than different presets with the same notes (AUC) |
| V1 | Real-amp control: JVM gain-sweep ordering, and Guitar-TECHS rig-vs-riff |
| V2 | Judge reproduction on development parts, gated *relative to the judge's own split-half regret* |
| V3 | Listening with a different-notes reference, the design of [Wright 2022](https://arxiv.org/pdf/2211.00943) [V-earlier] and ST-ITO [V], with 20% known-answer trials and hidden repeats |

Expect a ceiling: purpose-built effect metrics reach only |ρ| ≈ 0.4–0.6 with listeners even on same-content comparisons [V-earlier, [Comunità et al.](https://arxiv.org/html/2502.14405)]. A DI-free metric matching the judge at Kendall τ 0.3–0.4 may already be near what listeners support at small margins [I].

**Fifth, power.** Run the variance split (step 0a). If a meaningful part of the 0.101 band SD is within-band noise, score **every** crop and both halves [I]. Use Bayesian hierarchical pooling and equivalence (TOST) futility rules rather than superiority-only gates. Wild-cluster bootstrap is unreliable below about 11 clusters ([Webb](https://ageconsearch.umn.edu/record/274640/files/qed_wp_1315.pdf)) [S].

**Sixth, screening with known answers.** Replace the over-used 33-part development set with **synthetic songs**: development DIs through random off-menu settings, mixed into other bands' backings, mastered and separated. Their right answers are known, and N is limited only by renders [I]. They measure only the render side of the gap, so they are for screening, not for claims.

**Seventh, listening protocol.** Test the hybrid with **pairwise forced choice on the song's notes** (rebuilt DI), not a four-way page through other riffs. Add a taste-only control (the same choice without the song) and repeats [I]. Forced-choice pairs had the smallest variance and were the most time-efficient of four methods (Mantiuk et al., per round 4) [V-earlier]. Webb & Picinali's simulation favours Bayesian sampling of pairs ([arXiv 2508.17840](https://www.arxiv.org/abs/2508.17840)) [V].

## 4. New data: one clean CC BY set, several licence corrections, nothing that fixes crunch

No new open source adds crunch bands of real records with DIs. The table lists what exists, with access steps; licence corrections are in bold.

| Source | What it adds | Licence | Access steps | Use here |
|---|---|---|---|---|
| **Five guitar dataset** (Vergés Franch), [Zenodo 4988354](https://zenodo.org/records/4988354) | 6 songs × 5 guitars (3 electric: Telecaster, Ibanez ART120 with EMG, Epiphone Emperor-II). Each is recorded at once as DI, phone mic and laptop mic. The electric DI comes from a DV Mark Little Jazz amp's DI output. 730 MB [V] | CC BY 4.0 [V] | Direct download | 18 electric DIs from 1 player, clean only. Check that the DI out is pre-EQ. Usable as a "real amp, bad mic" mini-band [I] |
| **GOAT**, [Zenodo 15690894](https://zenodo.org/records/15690894), [paper](https://arxiv.org/html/2509.22655v1) | 5.9 h of DI (Strat ~235 min, Strandberg ~80, Jazzmaster ~26, Les Paul ~13), plus 25.85 h of NAM-amp renders [V] | **CC BY-NC 4.0, restricted. The earlier project note said CC BY, which is wrong** [V] | On the Zenodo page press "Request access" and describe the use; it is "research purposes only" [V]. Ask for per-file performer IDs [I] | New players for training and development; personal, non-commercial use only. Request it now: cheap and slow |
| **EGDB-PG / EGDB-NDSP**, [Zenodo 19789500](https://zenodo.org/records/19789500) | EGDB DIs through 256 BIAS FX2 tones, plus **6 Neural DSP presets, one listed as "Tone King Imperium Rhythm"** [V] | CC BY 4.0 on the record; the underlying EGDB DI licence is unstated [V] | The 135 GB zip does not fit the disk. Email f08946011@ntu.edu.tw for WAV or a subset; ask for EGDB-NDSP only [V, I] | An external sanity check of the Tone King render pipeline (confirm it is the same plugin as the Imperial MKII) [I] |
| **Slakh2100-redux**, [Zenodo 4599666](https://zenodo.org/records/4599666) | 2,100 synthesised mixes with stems and MIDI. Guitar patches have built-in effects, so its guitars are not DIs [V] | CC BY 4.0 [V] | 105 GB; use BabySlakh or stream a subset [V, I] | Backing tracks only. Real development backings come first, because synthetic-only training transfers weakly ([Slakh](https://ar5iv.arxiv.org/html/1909.08494)) [V] |
| **SynthTab**, [paper](https://arxiv.org/html/2309.09085v4), [repo](https://github.com/yongyizang/SynthTab) | ~13,113 h of DI-only renders from commercial Ample Sound plugins [V] | **Contradictory: the README says CC BY-NC 4.0, the LICENSE file is CC BY 4.0. Treat it as non-commercial** [V, I] | UR Box download, about 2 TB in ≤50 GB zips; one `electric_clean` zip would nearly fill the disk [V, I] | Last-resort pretraining only, behind a real-DI control |
| **TONE3000 / NAM**, [API terms](https://www.tone3000.com/api/terms) | 700k+ captures and IRs [S] | **The API terms forbid bulk download, scraping, mirroring and caching. The free tier is non-commercial. Each tone carries its own licence** [V] | The user hand-selects ~50–200 captures licensed cc-by or cc0 through the site's Select flow, keeping attribution [I] | A real-amp robustness test: development DIs through hand-picked captures. NAM runs outside the PACE queue [I]. The NAM trainer is MIT ([licence](https://raw.githubusercontent.com/sdatkinson/neural-amp-modeler/main/LICENSE)) [V] |
| **GuitarML ToneLibrary / Proteus; AIDA-X** | Small LSTM and WaveNet capture libraries [V] | GPL-3.0 ([ToneLibrary](https://raw.githubusercontent.com/GuitarML/ToneLibrary/main/README.md), [AIDA-X](https://raw.githubusercontent.com/AidaDSP/AIDA-X/main/LICENSE)) [V] | GitHub | Fine locally; copyleft applies only if redistributed [I] |
| **EG-IPT**, [Zenodo 15205644](https://zenodo.org/records/15205644) | 52,320 isolated notes, Gibson SG into an EVH 5150 III with controls flat, DI plus 5 mics [V] | CC BY 4.0 [V] | 23.8 GB zip | A note source for real-note recombination ([Pedroza et al.](https://arxiv.org/html/2405.14679v3)) [I] |
| **DadaGP** | 26,181 GuitarPro tabs [V] | Code MIT; **the dataset is by email request for research; Zenodo's CC BY covers only the paper** [V] | Email Dadabots or Pedro Sarmento ([README](https://raw.githubusercontent.com/dada-bots/dadaGP/main/README.md)) | Tab source for content coverage only [I] |
| **Weathervane "Shaking Through"** | Filmed studio sessions with raw multitracks; DIs unverified [S] | CC BY-NC 4.0 for personal use, per its terms page ([terms](https://weathervanemusic.org/termsofuse)) [S] | Membership; check one episode's file list before paying [I] | The best lawful "real song, visible rig" source; personal use only |
| **Pedroza et al. EGSet12** | 12 real mic'd electric solos [V] | Unstated [V] | Ask the authors | A tiny real test set |
| **MoisesDB**, [repo](https://github.com/moises-ai/moises-db) | Clean-electric vs distorted-electric labels; no DIs [S] | Non-commercial [S] | — | An evaluation set for electric separation, if non-commercial use is accepted |

**Other licence corrections and confirmations:**

| Item | Finding |
|---|---|
| Marshall JVM410H (Zenodo 7970723) | Listed as CC BY 4.0 in the brief, but **held, not cleared, by the project's own audit** because of a conflict with its IDMT upstream [P, `docs/research/native-guitar-development-data-2026-10-09.md`] |
| AFx-Rep | **Apache-2.0, confirmed** (this answers the brief's open question). Its Hugging Face repo also carries `FXencoder_ps.pt`, a BEATs checkpoint and a Linux VST3 tarball under their own terms [V] |
| Fx-Encoder++ | Code CC BY-NC 4.0, weights unlabelled: excluded [V] |
| RelFx | Weights CC BY-NC-SA 4.0: excluded; the code is MIT, so it can be retrained [V] |
| StemFX | Code and weights MIT; its bundled SCNet separator is unchecked [V] |
| DeepAFx-ST | Adobe licence, non-commercial research only [V] |
| YourMT3 | Code GPL-3.0, Hugging Face weights tagged Apache-2.0 [V] |
| EnCodec | Weights listed MIT on one card; another check found no tag. Treat as implicit MIT via the repo [V, conflicting] |
| BS-RoFormer-SW and the X-LANCE refiner derived from it | Upstream licence unknown [V-earlier] |

## 5. Song representation: a trained tone encoder plus note-normalised features, screened by a zero-render ladder

**No off-the-shelf embedding is evidenced to separate guitar tone from notes,** and the general models are the wrong tool:

| Model | Evidence | Licence |
|---|---|---|
| CLAP | 1.0% cross-instrument effect retrieval | Apache-2.0 |
| MERT | 2.6% cross-instrument effect retrieval ([RLAT](https://arxiv.org/html/2608.28127)) [V-earlier]. NSynth pitch accuracy 92–94% against instrument 71–73% ([MARBLE](https://arxiv.org/html/2306.10548v4)) [V]. **Erases level: LUFS probe R² ≈ 0** ([probe study](https://arxiv.org/html/2607.03806)) [V], which removes the drive cue | **CC BY-NC 4.0** ([card](https://huggingface.co/m-a-p/MERT-v1-95M)) [V] |

Effect-trained encoders do better when the content differs, but none has been tested on amp knobs or real guitar records:

| Encoder | Licence | Evidence |
|---|---|---|
| **AFx-Rep** | Apache-2.0 [V] | Mixture retrieval R@1 16.7 ([Fx-Encoder++ paper](https://arxiv.org/html/2507.02273v1)) [V]; cross-instrument retrieval 20.5% ([RLAT](https://arxiv.org/html/2608.28127)) [V] |
| **Fx-Encoder** | MIT ([repo](https://github.com/jhtonyKoo/music_mixing_style_transfer)) [V] | Weaker on cross-source tasks: 6.7% cross-instrument [V] |
| **PEACE** | MIT code; weights stated released, location unconfirmed ([repo](https://github.com/DBraun/PEACE/blob/main/LICENSE)) [V] | Strongest on reverb; untested on drive [V] |

Separation costs effect encoders about two-thirds of retrieval: Fx-Encoder++ R@1 drops from 19.9 on true stems to about 7.1 on separated ones [V]. The project's stem has a median SNR of 1.2 dB [P].

**The recommended representation has four parts** [I]:

1. **A tone encoder T, trained by the project.** Start from AFx-Rep or EfficientAT weights. Feed level-preserving log-mel. Use positives of the same preset through different DIs, and hard negatives of different presets through the same DI. Train with the separator in the loop and with real backings. Pool over windows with covariance (Gram) statistics or attention. Second-order statistics did best twice in round 4's sources [V-earlier].
2. **A small note-normalised block N.** It is computed on confident Basic Pitch notes in guitar-dominant stem windows, and contains:
   - the 200 Hz–4 kHz envelope averaged *per register bin*, so a different note distribution changes only which bins are filled;
   - **dynamics-response slopes:** how brightness and between-harmonic energy rise with local level, relative to the song's own median. A fixed mastering gain cannot change these slopes; bus compression flattens them;
   - between-harmonic flatness on non-power-chord voicings, because power chords mask intermodulation;
   - the onset-to-sustain ratio.
3. **A content vector c** (register histogram, note density, polyphony). It is used only to choose content-matched library DIs, to condition, or to regress out, **never as tone evidence**.
4. **Separate time-effect estimates,** so they do not pollute the dry chooser.

**One comparison trick: symmetric corruption.** Mix each candidate render into the song's own residual (mix minus stem), re-separate it, and compare stem to stem. This puts the separator's band-limiting, smearing and bleed on both sides of the comparison, at a cost of one separator pass per candidate [I]. It has no published evaluation.

**Transcription is reliable only on clean, sparse material.** Basic Pitch scores 66.1 onset F1 on clean commercial jazz [V], while generic models drop to 12.8–47.5 on crunch renders [V] and fall below 10% for non-main instruments in real pop mixes ([YourMT3+](https://arxiv.org/html/2407.04822)) [V]. So N must tolerate missing notes, and "render the transcribed notes through each preset" should not be the main route [I].

**The validation ladder.** Development only, gates declared first, losers cut at each rung [I]. It merges the researchers' R0–R5 ladder with the AFx-Rep audit: the audit's "same notes" condition is part of R5, its "other players' DIs" condition is R3, and its "on the stem" condition is R4.

| Rung | Question | Data and cost | Gate |
|---|---|---|---|
| R0 | Does the preset move the feature more than the player does? | 16,800 crossed renders and the existing panels; 0 renders | σ²(preset) / σ²(DI) ≥ 1.5 |
| R1 | Can it name the preset across players when every distractor plays the same notes? | Panels; minutes | Top-1 ≥ 2× log-mel on PR12 *and* SW50R (round-4 F2); also report judge regret |
| R2 | Does it see real drive the way it sees plugin drive? | JVM410H gain sweep (licence held; development only) and HT-1 | Spearman ≥ 0.8 between the frozen drive axis and the real gain knob |
| R3 | Does a real amp track rank the oracle's presets high when candidates are rendered through *other* players' DIs? | 33 development amp tracks; existing renders | Regret below the medoid's in ≥ 2/3 of bands; the most-picked preset's share < 25%. **The cheapest decisive test** |
| R4 | Does it survive separation? | Amp track vs single-guitar mix vs stem | Drift ratio < 0.5, and R3 on stems loses ≤ 30% of its gain; symmetric corruption as a separate row |
| R5 | Does a DI-free distance reproduce the judge's ranking? | Content-matched proxy DIs, ≤ 3 × 111 per part ≈ 11k renders for 33 parts (~1–1.5 h) | Spearman ≥ 0.6 with the judge; median regret ≤ 0.75× that of `unpaired-v3`. The audit's same-notes condition must reach Spearman ≥ 0.5 and at least half the oracle's gain, or AFx-Rep is dropped |

**Candidates for R0–R1, all frozen:**

- AFx-Rep, Fx-Encoder and PEACE (mean and Gram pooling);
- EfficientAT mid-block Gram;
- N-block variants;
- MFCC statistics: a must-have control, since MFCCs scored 0.74 against AFx-Rep's 0.86 in ST-ITO's style test [V];
- CLAP, as the floor.

**Only R0–R4 survivors earn the renders for R5 and the fine-tuning of T** (≤ 30k renders). **Stop rule:** if no row, frozen or fine-tuned, beats log-mel on R1 *and* the medoid on R3, stop investing in DI-free representations. Approach 1 then falls back to the stacked rebuilt-DI scores plus N, and the hybrid shell carries the product [I].

## 6. Dead ends: what the literature and the project's own results already rule out

| Approach | Why it is ruled out | Reopen only if |
|---|---|---|
| General audio and music embeddings (CLAP, MERT, MuQ, wav2vec2, PANNs, VGGish, BEATs) as a tone distance | Near chance once notes differ [P]; 1.0–2.6% cross-instrument effect retrieval [V-earlier]; MERT and wav2vec2 erase level [V]; MERT and MuQ weights are non-commercial [V] | Never as tone evidence; MERT-like models only as a content descriptor |
| Zero-shot ST-ITO with frozen AFx-Rep for guitar | The authors say it fails for guitar tone matching [V]; Spearman 0.36–0.44 against true quality [V]; 3.0% single-effect top-1 [V] | R3 and R4 pass (section 5) |
| Predicting exact discrete codec tokens (E1) | A 0.18 ms shift changes 67% of codebook-1 codes [P]; continuous latents beat tokens in speech [V] | — (use E1′ instead) |
| Knob regression as the final answer | 3.6% against a 10% bar [P]; point regression degrades on equivalent settings ([Hayes](https://arxiv.org/abs/2506.07199)) [V] | Only as a start for local search |
| Hand-made DI-free distances against other players' DIs | Regret 0.36 against a song-blind 0.42; judge agreement ≤ 0.38 [P, `docs/di-free-distance-results.md`] | Note-normalised versions pass R0–R3 |
| Waiting for a better open separator | Mega-53 gave +1.21 / +0.85 dB [P]; clean electric separates worst, at 0.6–0.9 dB median SNR ([Banquet](https://arxiv.org/html/2406.18747v2)) [V]; no open lead/rhythm splitter [V] | — |
| Diffusion or flow restoration of the DI | Generative, so it can invent notes; slow on MPS; no open music checkpoint; AudioSR only fills high frequencies ([repo](https://github.com/haoheliu/versatile_audio_super_resolution)) [V, I] | — |
| Neural electric-DI synthesis as the main data source | None is open: GuitarFlow has no licence, needs GOAT and Guitar Pro, and was "only barely" above Guitar Pro by ear ([GuitarFlow](https://arxiv.org/html/2510.21872v1)) [V]; rendering fidelity is the bottleneck [V]; the project's Karplus-Strong probe failed to replicate [P] | — |
| Bulk NAM capture harvesting | TONE3000 API terms forbid it [V] | — |
| More capacity, longer training or architecture repairs to the C-family DI network | No move in picks [P] | The ladder points to a specific fix |
| Noise or synthetic probe DIs | Round 1 [P]; Karplus-Strong probe 7/12 on replication [P] | — |
| Clean-vs-not-clean class predictor from the rebuilt DI; mix measurements for class | Failed its positive control twice [P]; mix HNR AUC 0.43, fizz 0.48 [P] | — (route by research text) |
| Domain-adversarial training as the main fix | +7 to +11 points in scene classification ([DCASE study](https://arxiv.org/pdf/2607.25887)) [V]; +0.02 F1 in transcription ([arXiv 2312.10402](https://arxiv.org/html/2312.10402v3)) [V] | Only as a minor add-on |
| Four-way audition through other players' riffs | Inconclusive; did not beat a song-blind taste [P] | — (use pairwise choice on the song's notes) |
| Top-1 held-out gates on ≤ 6 bands | Sign-flip p cannot go below 0.125 with 3 bands [I]; the oracle itself failed the SW50R gate [P] | — (use the pooled test) |
| Coherence as the mechanism metric | E0b and the residual network contradict it [P] | — |
| Non-open weights (Fx-Encoder++, RelFx weights, DeepAFx-ST, RemFX, Music2Latent, Stable Audio Open's VAE, the unlicensed Open-Amp encoder, EG-VAE which has none) | Excluded by the open-licence rule [V] | Reimplement the method from the paper |

## Conclusion

The project's problem is less about model architecture than it has looked. Every learned route so far was trained in conditions the songs never present: solo renders, narrow DI pools, no separator. It was then judged by a measure whose blind spots (treble, drive, near-ties) fall exactly where decisions are made. Two new readings come out of putting the notes together. First, the chooser's under-driven picks (43 against 14 parts) and the user's "dirty" verdict on rebuilt DIs are probably one fault, not two: broadband error in the rebuilt DI turns into fizz in the amp, and the judge steers toward lighter presets to compensate. The ladder tests this, and a near-free correction can be tried on development data. Second, the "perfect DI only buys a little" debate cannot be settled with the current numbers. It is a question about the menu and the floor, and a two-hour pilot with a planted target answers it.

The practical consequence is an ordering, not a single bet. Spend days and zero renders retiring weak representations and setting the Recall@k bar. Spend under 60k renders measuring headroom and DI needs. Only then spend ~43k renders on the one learned model that has never been tried in the song's own conditions. And keep the held-out sets for a single pooled test that can detect a −0.10 gain, because nothing available can detect −0.05. If that model fails its development gate twice, the evidence will point firmly to a research-plus-ear product with fixed class starts, and to new real crunch recordings as the only remaining lever.
