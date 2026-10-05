# Audio machine learning for tone matching and measurement: research round 4

*2026-10-05. Synthesises four reports, kept unchanged in `docs/research/round-4/`: closeness (A), features (B), models and search (C), tools and data (D), adding to rounds 1–3 (`docs/research/round-1-song-only-matching.md`, `round-2-full-plugin-estimation.md`, `round-3-supervised-preset-model.md`). Revised after an independent critique, each cited correction checked at its source; only small calculations were run, and nothing was downloaded. Marks: **[verified]**, the source holds the claim; **[unverified]**, snippets, inference or arithmetic; **[project]**, this repository's results; **[proposed]**, a threshold added here.*

## 1. Verdict

**How we measure.** Keep the judge (`analysis/aligned.py`). No published metric fits our question better: learned perceptual metrics were trained on speech, and quality models score a damaged copy against a clean original, not two different good tones. What should change is how we test the judge:
- **High gain is the main risk.** A published test found log-mel distance mis-ranking heavy distortion, and our listening covered clean-to-crunch only.
- **Listen only where two measures disagree.** Random trials cannot separate them.
- **Calibrate one condition per listening session** (about 40 trials): clean near-ties first, high gain once high-gain references with a DI exist.
- **For song-only work, make the judge the teacher:** a DI-free distance is good if it reproduces the judge's choices where a DI exists.

**Amp reach** [project, `docs/amp-reach-results.md`]. Another amp's factory presets came clearly closer (≥ 0.150) on 4 of 25 parts for SW50R, 4–6 for clean PR12, and 14–15 for AC20, beyond its null. At equal size, a joint menu reached no closer for SW50R or clean PR12. A joint clean menu would clear clean PR12's K1 by size alone, so the "not passed" verdicts rest on K3. Limits: 25 mostly clean parts, 8 from one band (Dom McLennon); cross-amp distances that listening never validated; factory presets only.

**How we would model.** The evidence is consistent with the user's framing, though render-and-compare evidence needs a DI and set-valued labels are a proposal:
- one shared model that chooses the amp first and the settings given the amp, counting every amp that can reach the recording as right;
- with a DI, amps compete by rendering and comparing, in one search that drops weak ones early;
- without a DI, there is no amp selector until a DI-free distance passes experiment 4 or an amp classifier passes experiment 6; the fallback is the starting preset's amp.

**Song-only search.** Every no-DI arm's median ended further from the amp track than its start: clearly for the product arms (0–3 of 37 parts closer), not significantly for the library arms; the test was void. The searches optimised the retired `unpaired-v3` and the calculations fit the probe's spectrum, so this indicts the no-DI targets more than searching (§4). Song-only matching should make a few coarse choices and fall back to the start.

**What not to do.**
- Don't use general pretrained audio models (MERT, CLAP, VGGish, wav2vec2) as features or distances; when the notes differ, they score around chance. The one exception kept as a test row is CLAP's per-channel mean and spread ("style" statistics), which did best on timbre similarity.
- Don't build gradients through the plugin, a stand-in model of it, or GAN or diffusion estimators.
- Don't count on better features to fix clean PR12 before experiment 2 shows whether its presets differ.

**First steps.** Six of the top eight experiments (§5) need no new renders or listening. The DI-robustness test needs about 1–2k renders, and high-gain calibration waits for references with a DI.

## 2. Measuring closeness

**Keep the judge.**
- In Comunità et al.'s MUSHRA test of effect models (27 listeners recruited, then screened), multi-resolution spectral distance, the judge's family, was the best signal measure (ρ = −0.427). FAD with VGGish was level overall (−0.430), FAD with AFx-Rep close (−0.417), and all were weak (|ρ| ≤ 0.43) [verified].
- Tian et al. found the multi-scale spectral distance "underperforms" on single-note timbre ratings [verified].
- Speech-trained (DPAM, CDPAM), codec-calibrated (PEAQ, ViSQOL) and no-reference metrics (PAM, NOMAD) answer other questions [verified]; waveform measures need shared phase, which a mic'd cab and the plugin lack [unverified: reasoning].

**Its risks.**
- **High gain.** In Wright et al.'s test, log-mel gaps under about 0.05 did not predict listeners at any gain. On heavy distortion, the model with the best log-mel score (0.19) got 57, against 92 and 85 for models scoring 0.22 and 0.23 [verified]. On Comunità et al.'s distortion effects, FAD with CLAP tracked listeners best (−0.613), then VGGish (−0.592), MR-STFT (−0.536) and AFx-Rep (−0.533) [verified]. 53 of the 108 Morgan presets are high-gain [project].
- **Near-ties.** Below about 0.09 in |log ratio|, 7–16% of pairs swap order under any one reasonable design change, and stage 0b had no trial below 0.15 [project].
- **Cross-amp.** Listening validated only clean-to-crunch PR12 [project], and the best matching loss depends strongly on what is matched [verified].

**Alternative measures ("rows"), cheapest first.**
- The judge's `tonal` part alone: in whole phrases, the sustained spectrum matters more than attacks [verified, McAdams].
- The judge plus a sharpness difference (MoSQITo) [unverified], since a +12 dB boost of the 8 kHz octave costs the judge only +0.10 dB [project].
- HAAQI, an auditory-model index that weighs distortion and noise more than EQ (r = 0.970 on its own data) [verified]. It may cover the distortion texture the judge misses [unverified], but our trials hold no high-gain material to test that.
- One embedding row: AFx-Rep, or CLAP "style" statistics (Huang's channel mean and standard deviation), best on human timbre ratings of single notes [verified]. Its high-gain case is weak: Comunità et al.'s FAD is a set statistic per model [verified], which says nothing about one pair's distance [unverified: inference].
- For separated stems, Torcoli's 2f-model [verified]; and band weights from the guitar's partial loudness in the song [unverified: proposal].

**Validating efficiently.**
- **Disagreement trials ("MAD competition")** play only the pairs where two measures disagree most [verified]. Separating two takes about 18 decided disagreeing trials if the better wins 80% of them, 42 at 70% [unverified: arithmetic]. The judge and ALM disagreed on 1 of 24 stage-0b pairs [project].
- **One calibration round per condition.** Spread about 40 trials over margins of 0.02–0.4, with repeats and a "can't tell" answer, and fit agreement against margin (psignifit). The margin at 75% agreement becomes the clear-difference cut [unverified]. Its 10–90% range is about 0.03–0.30 with 20 trials and 0.06–0.22 with 40 [unverified: simulation]. Repeats cap any measure's score near 0.89 if the listener repeats 80% of answers [unverified: derivation].
- **The 46 existing trials** (stage 0b's 30 and 16 earlier post-hoc ones) can screen measures but cannot fit one. They hold no high-gain material, and the post-hoc ones are in-sample for the judge, so screen on stage 0b's 22 decided pairs [project].

**Song-only distance: the judge as teacher.**
- Round 1's E6 scored DI-free distances against the retired `unpaired-v3` [project]; use the judge instead. For a part with a DI, a DI-free distance picks a preset from candidates rendered through another band's DI; its "regret" is how much further that pick is, under the judge, than the judge's best. It needs no listening or renders [project] but inherits the judge's blind spots.
- Candidate rows: MFCC and long-term spectrum statistics; harmonic envelopes within one pitch register [unverified: proposal]; channel mean-and-spread and covariance ("style") statistics; KAD over embedding frames [unverified]. The main danger is the notes leaking in: spectral distances have a poor sense of pitch [verified].
- **For song-only listening**, copy Wright et al.'s design: the reference is a few seconds of the target tone, and each candidate plays the next few seconds of the same piece, rated 0–100 for similarity [verified]. Add the amp track from another window as a hidden reference [unverified: proposal], and use guitar-exposed passages [project].

## 3. Features

**Choosing the amp.**
- No feature has been shown to identify the amp independently of its settings. In Chen et al.'s tone embedding, nine amps form their own small clusters inside two large gain clusters, but each amp was one fixed tone [verified]. Recognition errors follow circuit similarity [verified].
- Under the judge, Morgan presets from different families sit a median 3.09 apart within one amp, against 3.69 across amps [project].
- So choose the amp as in §1, and train no amp classifier unless experiment 6 passes.

**Settings within an amp.**
- **EQ, cab and mic:** a source-normalised long-term spectrum measures them directly and cheaply [unverified: reasoning]. Embeddings are not blind to EQ: in ST-ITO, CLAP audio embeddings tracked a 3-band EQ's high band at ρ 0.876 and a low shelf at 0.727 [verified].
- **Drive** needs features that keep input level; MERT, wav2vec2 and WavLM normalise it away, and THD and IMD cannot be measured from the recording alone [verified]. AFx-Rep estimated one drive knob from different notes at ρ 0.944, against CLAP's 0.852, but on effects seen in training. Compression is captured weakly everywhere (AFx-Rep ρ 0.68) [verified].

**Closeness without a DI.**
- **MFCC statistics are a floor, not a winner.** They scored 0.74 on ST-ITO's five-style EQ-and-compression classification of speech and music, against CLAP 0.56 and AFx-Rep 0.86; in its style retrieval, against random multi-effect chains rather than five fixed presets, MFCCs "appear to perform worse" than CLAP [verified].
- **"Style" statistics.** On timbre ratings, CLAP's channel mean and standard deviation (Huang) did best, ahead of its Gram matrix. On guitar-preset retrieval a wav2vec2 Gram matrix did well, though it is unclear whether the notes differed [verified].
- The training pair matters more than the architecture: the same processing on different notes is a positive, the same notes processed differently a hard negative [verified]. Our panels provide both [project].
- Through a mix, the 200 Hz–4 kHz spectral shape and coarse drive should survive; treble above about 5 kHz, attack, crest and reverb should not [unverified; experiment 11]. Music source separation cut Fx-Encoder++'s top-1 retrieval on MUSDB from 19.9% to 7.1%, and universal separation to 2.1% [verified].

**What doesn't help.**
- **General encoders as features or distances.** In RLAT's 20-way retrieval, every wrong answer plays the query's own source (chance 5%). When the right answer is another recording of the same instrument, as in our panels, CLAP scored 7.5%, MERT 5.2%, VGGish 9.0% and PANNs 5.8%, at or near chance (VGGish nearly twice it, still poor); across instruments they fall below it [verified]. They match notes, not processing; instrument-class "timbre" models and text prompts such as "bright" fail too [verified].
- **Only effect-trained encoders deserve a row:** AFx-Rep, Fx-Encoder++, RLAT and RelFx. None has been shown to separate knob positions within one amp, and ST-ITO's authors say it "does not work well" for guitar tone matching. RLAT's repository link returns 404, and it trained on Mixing Secrets stems, the Cambridge library behind many of our parts, so its scores there could leak [verified].
- **Clean PR12.** That its 21 presets are near-duplicates is a hypothesis for experiment 2. Project data are mixed. Against it: over the full window the per-part best preset is 24% / 20% closer than template+R, while the best single preset reaches about 7% (−0.072) and the constant about 0, so choosing per part matters; and K2's closed-set top-1 was 21–44% against 14.3% chance, so presets can be told apart within renders. For it: the amp is recovered mostly because a close same-amp preset usually exists, and a joint clean menu clears K1 by size alone, so the 21-preset menu limited headroom. The recognisers capture only 4–24% of the headroom either way [project].

## 4. Models and search

**The amp as a categorical choice.** A discrete choice with its own continuous settings is a known structure [verified]. C's design:
- **One shared encoder, amp first:** p(amp | audio) × p(settings | amp, audio), keeping the plan's choice of amp, pedals and compressor [project]. Shared heads cover controls that mean the same on every amp (effective drive, the EQ curve, bright and presence tilt); amp-specific heads add a correction and switch off when their amp is not chosen [C's reasoning].
- **Set-valued amp labels.** When several amps reach a part within the judge's cut, train toward the whole acceptable set (a partial-label loss) [unverified], and score "in the set", not top-1.
- **Regret in two parts:** how far the chosen amp's best preset falls behind the best overall, and how far the prediction falls behind its amp's best.

**Search across amps.**
- **With a DI**, treat each amp as a competing option and use successive halving (Hyperband, BOHB): cheap trials for many options, more for the survivors [verified].
- **A caveat.** C's "own-DI search beats neutral on 41–43 of 43 parts" was under the retired `unpaired-v3`. Under the judge, SW50R's own-DI search was closer than its start in 10 of 12 bands, not significantly (p 0.078) [project]. So a cross-amp search should optimise the judge on half A, be scored on half B, and first pass a positive control (experiment 14).
- **Without a DI, the objective is the problem.** In the void no-DI rescoring, every arm's median ended further from the amp track than its start (medians of band medians +0.07 to +0.56): clearly for the product arms, closer on 0–3 of 37 parts, and not significantly for the library arms (11–19 of 37 closer, Holm p ≥ 0.449) [project]. The searches optimised `unpaired-v3` and the calculations fit the probe's spectrum, and the noise-probe calculation was among the clearly worse arms, so this indicts the no-DI targets more than the searching. Song-only search should stay near the start, stop early and offer coarse choices (amp where reach differs, drive class, brightness). Experiment 13 tests this under experiment 4's winner.

**Renders against real recordings.**
- **Hub presets**, which become everyone's nearest neighbour, can be corrected cheaply (CSLS, mutual proximity, CORAL) [verified].
- **In open-set recognition, unseen accuracy tracks seen accuracy** [verified, Vaze et al.]. By analogy, PR12's seen-preset top-1 of 21–44% against 14% chance foretold its open-set failure [project].
- **Randomise** mic, room and cab colouring in training, never estimated quantities [verified in robotics; untested here].
- **Uncertainty and leakage.** Conformal coverage within ±0.1 needs 22 independent points [verified]; we have 13 bands from about 8 recording chains [project]. Leakage changes which method wins [verified], so select only on leave-band-out real tracks.

**To watch: DI recovery.** EG-VAE recovers the DI from a wet recording. On 96 unseen Morgan factory presets rendered through EGDB DIs, 14 listeners rated its dryness 3.50 against the true DI's 4.39, and its quality 3.69 against 4.50; its tone embedding gives Morgan presets "identifiable but less separated" clusters. There is no code or weights, only a demo page [verified]. A good enough recovered DI would make song-only matching paired; experiment 5 measures how good it must be.

**Unlikely to work here** (§7): gradients through the plugin (about 18M renders [unverified: arithmetic]); neural stand-ins, as DeepAFx-ST's fell short "especially for the parametric equalizer"; GAN or diffusion blind estimation, at one model per target [verified]. C found no published test of settings estimation on real recordings with known answers [unverified: absence].

## 5. Experiments, ranked by value for cost

Gates are declared before results are read, and each decision gets an independent review. **No renders** means the existing panels (SW50R 1,978 renders, clean PR12 about 900, AC20 about 1,300), the listening trials, the stored amp-reach distances or crops on disk. Experiments 1–3 run together.

1. **Set-valued amp reach** (C). *How many amps reach each part within 0.150 of the best overall?* Minutes re-reading `~/ndsp-presets/runs/kill/amp-reach.json`, **no renders**; also report the two-part regret (§4). Gate [proposed]: if most parts have one acceptable amp, train an amp head; otherwise show a multi-amp shortlist. A shortlist is likely, since other amps' presets reached about as close at equal size [unverified].
2. **Distinguishability map** (C). *How many distinct presets does each menu hold?* It tests the near-duplicate hypothesis (§3). Minutes, **no renders**. Gate: if clean PR12's 21 presets collapse to 3–5 classes, K3 failed on identifiability and labels shrink to those classes; if not, recognition and transfer failed.
3. **Hub and shift fixes on K3** (C, with B's F3). *Is the render-to-real gap a cheap normalisation?* Minutes, **no renders**. Gate: the top pick's share falls below 25% (from 54–57%) and the gain over template+R rises at least 5 points under both band sets; otherwise drop recognisers on near-identical menus.
4. **The judge as teacher, with content-invariance rows** (E6 under the judge, with B's F2). *Which DI-free distance reproduces the judge's choices?* Distractors include other presets through the part's own DI, playing the same notes. Rows: §2's candidates, log-mel, the lean fingerprint, and a small CNN's mean-and-spread and Gram statistics; AFx-Rep and CLAP (the floor) need downloads. Score by regret under the judge, not top-1, since "many settings sound alike" (round 1) [project]. Minutes, **no renders**, no listening. Gate (E6's): median regret at most 0.75× `unpaired-v3`'s, no worse on stems, and Spearman at least 0.6 with the judge.
5. **DI robustness, the gate for DI recovery** (D's EG-VAE lead). *Does the judge's preset ranking survive an imperfect DI?* Re-render panel presets through each part's DI degraded by round 1's E7 `same_degraded` recipe (soft clipping, ±3 dB tilt, 10 ms smear, −20 dB bleed). About 1–2k renders. Gate [proposed]: if, under the clean-DI judge, the degraded-DI pick is within 0.150 of the clean-DI pick on most parts in most bands, track DI recovery; otherwise drop the route.
6. **Amp recognition without a DI, scored against the sets** (B's F5). *Can features name an amp that reaches the part?* Expect a hard test: the judge with a DI identifies the amp 72% of the time overall (PR12 87%) but SW50R only 52%, and a renders-only gate repeats K3's trap (best recogniser on renders, worst on real tracks) [project]. So score real amp tracks against experiment 1's sets. Minutes, **no renders**. Gate [proposed]: the predicted amp is in the set more often than the best constant amp (band sign-flip, p < 0.05, both band sets); otherwise no amp classifier.
7. **High-gain calibration** (A). *Where does the listener agree with the judge 75% of the time on high-gain pairs, and do that margin and slope differ from clean?* Development parts are mostly clean (set 2 left metal out), so they cannot calibrate high-gain matching [project]. It needs high-gain references with a DI: ToneTwist's real captures (§6; recording chain undocumented). A high-gain render as the reference could run now, but it only calibrates differences between renders, not between a real amp and the plugin. Downloads or renders, then about 40 minutes of listening per condition (40 trials over five margin bins, 10 repeats), one condition per session: clean near-ties, then high gain, then cross-amp. Gate [proposed]: a high-gain margin or slope outside the clean one's interval gets its own cut or a declared fix.
8. **Alternative rows on the listening trials** (A). *Does another measure call trials differently, notably 3, 7 and 15, where every current one was wrong?* Rows: the `tonal` part, the judge plus sharpness, HAAQI, CLAP mean-and-spread, AFx-Rep; their high-gain rationale waits for experiment 7. About a day of code, **no renders**; embedding rows need downloads. Gate, on stage 0b's 22 decided pairs (the 16 post-hoc trials reported apart): forward a row that disagrees with the judge on at least 10% of clear pairs and agrees with the listener on at least 15.
9. **Threshold staircases** (A). *How does the judge weigh treble, bass and drive against 1.6 kHz?* Round 2 advised against per-control listening threshold tests; these check how the judge weights three axes that verdicts depend on, not individual controls. About 6 minutes each; drive needs tens of renders [unverified]. Gate [proposed]: an axis whose threshold costs under half of 1.6 kHz's is under-weighted, and a fix is declared.
10. **Disagreement round per surviving rival** (A, after 8). 30 trials where the rival and the judge each call a clear difference (≥ 0.15) in opposite directions, plus repeats and hidden references. About 40 minutes each, **no renders**. Gate: an exact binomial test on 18–23 decided disagreeing trials.
11. **Separation survival** (B's F4). *Which features survive Demucs?* Minutes on MPS, about 3 s per 30 s [project]; **no renders**. Gate: the stem moves a surviving feature less than half the median distance between presets.
12. **Feature swap in K2/K3** (B's F1; after 4, and only if experiment 2 finds separable presets). **No renders**. Gate: PR12 open-set regret below the medoid's, and K3 capture at least doubled for 2 of 3 recognisers.
13. **Song-only search drift** (C, after 4). *Does a no-DI search drift from the amp track as it runs?* Judge-scored checkpoints (0 to 300 iterations) on 20 parts, searching on experiment 4's winning distance; the void runs optimised `unpaired-v3`, so their drift would not transfer. About 120 renders per amp. Gate [proposed]: if distance rises from iteration 0, adopt "stay near the start, stop early".
14. **Successive halving across amps, with a DI** (C). *Does a joint-amp search beat a single-amp one at equal renders?* Its condition is met: AC20 falls short on 14–15 of 25 parts. First, as the no-DI result asks, a positive control (§4): a judge-optimised own-DI search must beat its start. About 6,600 renders plus the control. Gate [proposed]: one-sided band sign-flip, p < 0.05. Round 2 found that splitting a fixed render budget across topologies made targets worse (`docs/research/round-2-full-plugin-estimation.md`), so successive halving has to beat a single-amp search at equal renders, not merely match it.
15. **Outside data** (D; downloads). timbremetrics as an embedding floor (gate [proposed]: drop embeddings below MFCC there); GUITAR-FX-DIST for drive settings; ToneTwist for real amps; MoisesDB for "driven or clean" in mixes.

## 6. Tools and downloads

**Every item below is a download that needs the user's approval first.** Non-commercial (NC) items stay local and never ship. Already on disk: a Demucs environment with torch on MPS [project].

- **Measures:** MoSQITo (Apache-2.0); pyclarity (MIT) for HAAQI [verified]; psignifit (licence not checked); kadtk (MIT), a kernel audio distance that suits few windows better than FAD [verified].
- **Listening:** jsPsych (MIT) with HeadphoneCheck (BSD-2); webMUSHRA (MIT-like), as adapted in Neural DSP's amp-model paper [verified].
- **Separation:** audio-separator (MIT); an MVSep guitar model, MIT per a third-party card [verified card].
- **Model weights** (experiments 4 and 8) [verified]: AFx-Rep at `huggingface.co/csteinmetz1/afx-rep` (Apache-2.0 card; `afx-rep.ckpt` about 1.16 GB, fetched by st-ito's `load_param_model`); EfficientAT mn10 (MIT); PANNs Cnn14 (code MIT, weights CC BY 4.0; 327.4 MB, or 358.7 MB for Cnn14_16k); LAION `larger_clap_music` (Apache-2.0); DAC (MIT); MERT-95M (NC).
- **Datasets, in order of use:**
  1. timbremetrics (likely small; licence not stated);
  2. the ToneTwist dry set (418 MB, CC BY-NC) and its high-gain captures: Mesa Mark V Extreme, Mesa 5:50 Burn, Engl Retro Tube 50 Drive, Blackstar HT5 Metal [verified];
  3. GUITAR-FX-DIST: one 22.5 GB split archive (ten 2.1 GB parts and a final 1.0 GB), so no part extracts alone. Zenodo says CC BY 4.0, but its audio, 2-second isolated notes, derives from IDMT-SMT-Audio-Effects (CC BY-NC-ND 4.0), so keep it local [verified];
  4. an EGDB zip (1.0 GB, CC BY); MoisesDB (NC, registration); GOAT (CC BY, by request); TONE3000 captures, needing an account the user must create [verified].
- **Avoid:** essentia (AGPL-3.0; essentia-tensorflow broken on Apple silicon), OpenL3 (old Python) and torchaudio for file I/O [verified].
- **MPS:** no float64; check MPS output against the CPU once per model [verified].

## 7. What not to do

- Quality scores (PEAQ, ViSQOL), speech-trained metrics (DPAM, CDPAM), CLAP text prompts or single-pair FAD as the closeness number.
- More listening on log-mel variants: outside near-ties they swap few pairs (at most 2.5% between the band sets in the second quarter of margins) [project].
- General encoders as features, or an amp classifier before experiment 6 passes.
- Gradients through the plugin, a stand-in model of it, or GAN, diffusion or autoregressive estimators.
- A better song-only optimiser, or a song-only search test on any distance but experiment 4's winner.

## 8. Sources

Full source lists: `docs/research/round-4/A-closeness.md`, `docs/research/round-4/B-features.md`, `docs/research/round-4/C-models.md` and `docs/research/round-4/D-tools-data.md`. Key sources:
- **Metrics:** Wright et al. https://arxiv.org/pdf/2211.00943; Comunità et al. (Table 8) https://arxiv.org/html/2502.14405; Tian et al. https://arxiv.org/html/2507.07764; HAAQI https://pmc.ncbi.nlm.nih.gov/articles/PMC4849486/; MAD https://www.cns.nyu.edu/pub/lcv/wang08-preprint.pdf.
- **Features:** ST-ITO https://arxiv.org/html/2410.21233 and AFx-Rep's weights https://huggingface.co/csteinmetz1/afx-rep; RLAT https://arxiv.org/html/2608.28127; Fx-Encoder++ https://arxiv.org/html/2507.02273; Chen et al. https://arxiv.org/html/2407.10646.
- **Models:** DeepAFx-ST https://arxiv.org/html/2207.08759; CSLS https://ar5iv.labs.arxiv.org/html/1710.04087; Hyperband https://arxiv.org/abs/1603.06560; EG-VAE https://arxiv.org/html/2608.05513.
- **Data:** GUITAR-FX-DIST (Mono Continuous subset) https://zenodo.org/records/4296040; IDMT-SMT-Audio-Effects https://www.idmt.fraunhofer.de/en/publications/datasets/audio_effects.html; ToneTwist https://zenodo.org/records/10901426 and https://github.com/mcomunita/tonetwist-afx-dataset.
- **Project:** `docs/amp-reach-results.md`, `docs/kill-tests-pr12-results.md`, `docs/amp-identifiability-results.md`, `docs/no-di-rule-under-the-judge-results.md`, `docs/listening-validation-results.md`.

**Settled here** (the reports stay unchanged):
- **Best on distortion:** FAD with CLAP (−0.613), not MR-STFT; overall, FAD with VGGish (−0.430) edged MR-STFT (−0.427).
- **CLAP "style":** the channel mean and standard deviation (Huang), as A says, not a Gram matrix (B, D).
- **PANNs licence:** code MIT, weights CC BY 4.0, as D says.
- **Other report errors:** Wright et al.'s 57 called "the worst score" (A); "EQ r ≈ 0.19", which is text–audio similarity (A, B, D); Chen et al.'s clusters and Fx-Encoder++'s 6.4%, a top-5 figure (B); RLAT's 81.7%, another loss setup rather than unseen processors (C); AFx-Rep weights (B, D); GUITAR-FX-DIST (D).

**Still open:** Düvel et al. (Kemper against the real amp), where A verified d′ = 0.34 and D could not open it.
