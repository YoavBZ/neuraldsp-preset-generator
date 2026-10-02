# Song-only tone matching: research plan

*Produced on 2026-10-02 by a research workflow:*
- *four parallel tracks:*
  - *predicting settings directly from audio;*
  - *differentiable proxies and black-box style transfer;*
  - *recovering the guitar input from the song;*
  - *representations, losses and optimisers;*
- *one adversarial critic per track, who opened every cited source, checked feasibility on this machine and tested each idea against the measured failures in `tone-matching-plan.md`;*
- *a synthesis.*

*The question it answers: what should replace or supplement the 300-render noise-probe search when the user supplies only the song file and never a DI. Nothing here has been run yet. Each approach carries the experiment and gate that would decide it.*

## 1. Executive summary

The change most likely to help is a simple one. Stop rendering candidates through the 6-second noise burst and render them through a real guitar DI taken from a public library. The committed runs already show what this is worth. A DI from another band beat neutral settings on 19 of 27 SW50R set-2 parts with level left out. The direct inversion alone through another DI also ended closer than the full 300-render noise search (median 1.11 against 1.25 on SW50R, 1.03 against 1.26 on Tone King). This needs no model and no new dependency, and a match still takes about 8 minutes. It can be tested over one night after a small change to `scripts/benchmark_recordings.py`.

It will probably help Morgan more than Tone King. On Tone King, another DI beat neutral settings on only about 20 of 33 parts. So whether a Tone King match without a DI should simply return neutral settings, rather than search, is worth deciding (§5). The noise search ended further than neutral on 29 of 43 parts with level left out, and 38 with level.

The second big unknown is the mix itself. No benchmark has yet started from a song instead of a clean amp track. The one old Demucs test (`~/ndsp-presets/separation-test`) scored the stem 0.79–1.23 from the true guitar under an older profile, which is not comparable with today's figures. It has to be measured again, on set-2 parts, before anything learned is built.

Only one idea has a real chance of closing the rest of the gap to a same-take DI (median about 1.0 against 0.5): a distance that ignores what is being played. No published model has been shown to do this for knob-level amp settings. So screen it cheaply first, and train our own only if the screen shows a gap worth chasing. Recovering a DI from the song, and predicting settings directly with a network, are long shots. One diagnostic run decides whether DI recovery deserves any work.

## 2. Ranked shortlist

### 1. Real guitar DIs instead of the noise probe

**What it is.** When the user gives no DI, the search plays one fixed 6-second probe through each candidate preset: 4 clips of 1.5 s from real DI recordings, joined with short fades. Each clip is scaled to a typical DI loudness. The 43 set-2 development DIs span −32.0 to −10.7 LUFS with a median of −22.9, so start from −22.9, not the −18 used in `study_harmonic.py`. E1 tests the level. The loss stays `unpaired-v3`, and the inversion, guitar check and level trim stay as they are. One fixed file matters, because rotating clips between candidates would make CMA-ES rank the clips instead of the settings. `Evaluator` already takes a per-call DI, and `match_preset.py` already has `--probe-di`, so this is mostly a change to which probe gets picked.

**Expected benefit.**
- **Morgan:** the search goes from "no better than its start" to clearly better than neutral. Expect roughly 65–75% of parts closer than neutral, with a median 15–25% closer, plus a tail of bad answers. It should also fix much of the no-DI loudness error: the other-DI arm won 39 of 43 with level included, against 34 of 43 with level left out.
- **Confidence:** medium-high that it beats noise, medium that it beats neutral with an outside library. 23 of the 27 other-band pairs in the committed run came from the same source library: 16 Cambridge to Cambridge, from 12 artists whose chains are not stated, and 7 Telefunken, all one room. Wins over neutral were 9 of 16 for Cambridge pairs, 6 of 7 for Telefunken pairs and 4 of 4 for cross-source pairs, so a shared-chain advantage is not shown either way. A public library is untested.
- **Tone King:** low confidence.
- **Probably not worth building, pending E1:** choosing the DI to fit the song. In an uncommitted scratch spectral check, one fixed "medoid" DI was spectrally closer to the true DI than the benchmark's `other` DI on 33 of 43 parts, and the song-matched pick beat that fixed DI on only 24 of 43. E1's `retrieved` and `oracle_pick` arms decide it.

**Cost.**
- About 2–3 days of work.
- Experiments: about 45 minutes of renders for the inversion-only screen, then about 3.4 h (SW50R) and about 3–3.4 h (Tone King, which renders at the same rate) of search.
- Match time: unchanged.
- Dependencies: none new in the core, just a few seconds of licensed DI audio. See the decisions in section 5.

**Key references.**
- ST-ITO (CMA-ES at match time against a reference with different content; the authors note, without a measurement, that it does not work well for guitar tone): https://arxiv.org/html/2410.21233
- Guitar-TECHS (CC BY 4.0, DI plus amp mic; P1/P2 are exercises; P3 music is validation set 1 and stays out): https://zenodo.org/records/14963133 and https://arxiv.org/abs/2501.03720
- EGDB, 240 DI performances: https://arxiv.org/abs/2202.09907. I checked the CC BY Zenodo record https://zenodo.org/records/12674910 and it holds only the BIAS FX2 renders (one 1.0 GB zip), not the dry DIs. The DI licence is still unconfirmed.
- GOAT, 5.9 h of DI, access on request: https://arxiv.org/abs/2509.22655
- IDMT-SMT-Guitar, CC BY-NC-ND, local experiments only: https://zenodo.org/records/7544110

### 2. Measure the mix and add a separation front end

**What it is.** Every set-2 result so far used the isolated amp track as the reference. The product's input is a song. The plan is to add reference rungs to the benchmark and score each against the clean amp track through the part's own DI:
- the amp track;
- a single-guitar mix: the amp track plus the non-guitar backing, rebuilt from the stem list in `validation-sources-2.json`;
- the htdemucs_6s guitar stem of `mix_instrumental.wav`, from `~/ndsp-presets/tools/demucs-venv`.

If the stem keeps most of the gain, ship Demucs as an optional extra. It would come with window selection by stem-to-mix ratio and a choice of side for hard-panned doubles. The existing excerpt-start option lets the user point at a passage where the guitar is exposed.

**Expected benefit.**
- This gives no tone gain by itself. It prices the mix penalty, which every song-only method pays.
- High confidence that the measurement is informative. Low-to-medium confidence that the stem keeps most of the gain.
- Two warnings:
  - At least 32 of the 43 development mixes contain other guitars, which Demucs merges into one stem.
  - `mix.wav` is a mono, unity-gain sum with no mastering, so a pass here flatters real songs.

**Cost.**
- About 1 day of harness work, plus 2–3 days for the product extra.
- Demucs on 43 crops takes about 10–15 minutes on the CPU. Each search rung takes about 1.1 h per 20 parts.
- Match time goes up by under a minute (Demucs runs at about 1.5× the excerpt length on the CPU).
- Dependency: Demucs plus torch in an optional extra. Demucs is MIT but archived.

**Key references.**
- Demucs, including the speed note and the archived status: https://github.com/facebookresearch/demucs
- MoisesDB (HT-Demucs guitar 3.07 dB SDR against 5.3 dB for an oracle mask): https://ar5iv.labs.arxiv.org/html/2307.15913
- MVSep guitar leaderboard (BS-RoFormer-SW and Logic Pro 11.2 about 9.0 dB): https://mvsep.com/quality_checker/leaderboard/guitar
- StemFX (training with separation in the loop): https://arxiv.org/html/2607.15634
- Fx-Encoder++ (instrument-wise retrieval from mixtures is weak whichever way it is done, R@1 3.0% direct and 2.1% via Demucs, and guitar was not evaluated): https://arxiv.org/html/2507.02273v1

### 3. A distance that ignores the performance (screen first, train only if needed)

**What it is.** The remaining gap after approach 1 is a loss that partly scores the notes instead of the amp. The hand features pick the right setting across performances only 22–34% of the time for timbre, dynamics and level (ambience 17–18.5%), against 14% chance. There are three tiers, cheapest first:
- **(a) Numpy only.** Learned whitening and LDA on the existing fingerprint features, fitted so that renders of the same settings through different DIs look alike, folded by band. Also a source-normalised timbre term: the reference spectrum over an average DI spectrum, against the candidate spectrum over the probe spectrum. This keeps D4.
- **(b) Pretrained effect encoders as screening rows only.** AFx-Rep, and Fx-Encoder++ (non-commercial, local only).
- **(c) Our own contrastive encoder,** trained on plugin renders of many CC BY DIs. Positives are the same settings through different DIs and backings. Its distances are regressed onto the same-DI `unpaired-v3` distance, the loss that already works on 43 of 43 parts.

**Expected benefit.**
- This is the only route toward the same-take ceiling, and the only one with a plausible chance on Tone King.
- Low-to-medium confidence. No published encoder is shown to resolve knob positions within one amp: Open-Amp separates devices, and Chen et al. show the right training recipe but give no retrieval numbers.

**Cost.**
- **Screen:** about 2–3 days of code, with about 1,100 renders per amp (minutes per amp; Tone King renders at the same rate as SW50R) plus about 30 minutes of Demucs.
- **Numpy metric:** 1–2 days.
- **Trained encoder:** 2–3 weeks. It needs 16k–100k renders per amp (about 1–2 h each for SW50R and Tone King, Tone King split into runs under two hours as a precaution; AC20 overnight for about 30k) and 2–4 h of MPS training per amp, with torch in an optional extra.
- **Match time:** the same renders as approach 1, plus about 20 ms per embedding.

**Key references.**
- ST-ITO: https://arxiv.org/html/2410.21233 and its code https://github.com/csteinmetz1/st-ito
- Open-Amp: https://arxiv.org/html/2411.14972v1
- Chen et al., zero-shot amp tone embedding (the "same tone, different playing" recipe; no released weights): https://arxiv.org/html/2407.10646
- DeepAFx-ST (training on two halves of one recording so content does not leak): https://arxiv.org/html/2207.08759
- Diff-MST (a feature loss beats multi-resolution STFT when content differs): https://arxiv.org/html/2407.08889
- Synth-JEPA (out of domain, embedding search scored 10.25 against 28.06 for regression): https://arxiv.org/html/2609.31024
- Fx-Encoder++ code, CC BY-NC 4.0: https://github.com/SonyResearch/Fx-Encoder_PlusPlus
- Neighbourhood Components Analysis: https://scikit-learn.org/stable/modules/neighbors.html#neighborhood-components-analysis
- Deng et al. (general embeddings such as CLAP and OpenL3 cannot be made robust to effects; use them as a floor only): https://arxiv.org/abs/2501.15900

### 4. A better start by rendering: topology choice and a factory-preset lookup

**What it is.** The search holds switches and selectors (amp, bright, mic type, pedals on or off), so a wrong topology is the one thing it cannot fix. M7-1 showed that a better *continuous* start ends where the neutral start does (0.479 against 0.480), but switches are the exception.

The plan has two parts:
- **Topology.** For each Morgan topology worth trying (amp, its switches, mic type, pedals on or off), invert through the library probe and keep the topology whose render is nearest the reference. This needs a small inversion-only mode. `--enumerate` runs a full inner search per position and splits the budget between them, which is far costlier. No classifier is needed.
- **Factory presets.** With a fixed probe, the 108 non-User Morgan and 130 Tone King factory presets (both counts include Default and Reset All Settings) can be fingerprinted once. A match then ranks them against the reference with no per-match renders and inverts the top 3. The `User/` folder is excluded because it holds this tool's own outputs.

**Expected benefit.**
- This is bounded by the oracle headroom after inversion, which has never been measured. Low-to-medium confidence.
- Its most likely value is a shortlist with two different voices.

**Cost.**
- About 1–2 days of work.
- The oracle test is about 1,600 renders (1.5–2 h; AC20 needs fresh processes).
- Match time goes up by about 20–40 renders: seconds on reused Morgan, about a minute on AC20.
- No new dependencies.

**Key references.**
- Hinrichs et al. 2022 (effect classification and settings from mixtures, in simulation): https://api.crossref.org/works/10.1186/s13636-022-00257-4
- Comunità et al. 2021: https://arxiv.org/html/2012.03216v1

### 5. Safety rails: stop when the search would not help, plus a prior from the factory presets

**What it is.**
- **Abstain.** Return neutral settings, or the nearest factory preset, when the no-DI search is not shown to help. On Tone King the noise search ended further than neutral on 29 of 43 parts with level left out (38 with level). Whether to abstain there now is your call (§5).
- **Prior.** Fit a shrunk diagonal Gaussian on the factory presets and add a Mahalanobis term to `prior_deviation`. This makes the search a "most likely settings" (MAP) search, which limits how far a weak loss can walk. From the shipped Example_Clean_PR12 preset, PR12 ended worse than its start on 34 of 43 parts (an uncommitted run; from a neutral start, 18 of 43). From SW50R's shipped template, 28 of 43 at seed 0 and 25 at seed 11.

**Expected benefit.** It limits damage; it cannot make a match right. Medium confidence.

**Cost.** About 1–2 days. The first test needs no renders and uses the stored answers. The follow-up is one 20-part arm (about 1.1 h). No match-time cost and no new dependencies.

**Key references.**
- Yu et al. 2025 (a Gaussian prior from 365 presets cut parameter error by up to 33%; the listening difference was not significant): https://arxiv.org/html/2505.11315v1
- RNPE (detecting when real data lie outside what the simulator can produce): https://arxiv.org/abs/2210.06564

### 6. Recover a DI from the song (learned de-amp), gated on one diagnostic

**What it is.** A model trained on our own renders of public DIs maps the separated stem back to an estimated DI. The search then runs through that estimate as if it were a paired DI. Transcribing the part and resynthesising it from real DI notes is a weaker variant that depends on the same gate.

**Expected benefit.**
- High if it worked, because the same-take DI wins on 43 of 43 parts. Low confidence overall:
  - No paper tests real mic'd amps separated out of mixes.
  - Removing high gain is an ill-posed problem.
  - The strongest models (EG-VAE, Distortion Recovery) have no public weights.
- The set-1 evidence that "the performance matters more than the rig" is confounded (rig coincides with dataset, 7 parts against 7), so measure it first.

**Cost.**
- At least 10 days of work.
- Training: 20–50k renders, and an unmeasured 12–36 h of MPS training.
- Match time: seconds of inference, then Demucs and the usual search.
- Dependency: torch.

**Key references.**
- EG-VAE (tested on unseen Morgan presets, plugin renders only): https://arxiv.org/html/2608.05513
- Distortion Recovery: https://arxiv.org/html/2407.16639
- RemFX, with public checkpoints: https://arxiv.org/html/2308.16177 and https://github.com/mhrice/RemFx
- Imort et al.: https://arxiv.org/abs/2202.01664
- Švento et al. (memoryless distortion only; guitar checkpoints released): https://arxiv.org/html/2501.05959 and https://github.com/michalsvento/NLDistortionDiff
- Okita & Katayose (predicting the dry signal and then searching worked best): https://arxiv.org/html/2604.22276
- Basic Pitch: https://github.com/spotify/basic-pitch

### 7. Predict settings directly from the song (amortised posterior), mainly for speed

**What it is.** A network trained on plugin renders of many DIs outputs a distribution over settings. K samples are rendered through the library probe, the best is kept, and a short search follows. It must never be trained on noise-probe renders.

**Expected benefit.**
- Mostly speed: 64–164 renders instead of 300.
- Low confidence on quality:
  - Even through a played-DI atlas, a better start ended exactly where the neutral search did.
  - Gain and drive are confounded with how hard the player picks.
  - Pure regression was the worst arm out of domain in Synth-JEPA.

**Cost.** About 6–7 days of work, 30–50k pilot renders, hours of MPS training, and torch.

**Key references.**
- Comunità et al.: https://arxiv.org/html/2012.03216v1
- Bruford et al. (1M renders in about 24 h; a parameter-only loss gave audible failures): https://arxiv.org/html/2407.16643
- Peladeau & Peeters (judge estimates by their audio, not by their parameters): https://arxiv.org/abs/2310.11781
- sbi: https://joss.theoj.org/papers/10.21105/joss.02505
- RNPE: https://arxiv.org/abs/2210.06564
- Synth-JEPA: https://arxiv.org/html/2609.31024

## 3. Experiment-first plan

**Ground rules for every experiment:**
- Set-2 development parts only.
- Run with `.venv/bin/python` and pass `--crops-dir ~/ndsp-presets/references/validation-crops` when running from a worktree.
- Score through each part's own DI against the amp track, with `unpaired-v3` and level left out.
- Every comparison stays within one run, because single parts moved by up to 0.91 between runs (noise arm; 0.52 for the other-song arm), measured on synthetic How Long targets.
- Count wins by part and by band.
- The 20-part runs use one seeded draw stratified by band, committed before the first run.
- Durations come from the committed runs: 3 arms × 43 parts on SW50R with 3 workers took 435 minutes, which is about 3.4 minutes per arm-part. Tone King batches of 9–10 parts took 78–103 minutes.

### Phase 0: no renders (about 1.5 days of code)

- **Harness change.** In `scripts/benchmark_recordings.py`:
  - add `--signal file=NAME=PATH` (one probe for every part);
  - add `--signal dir=NAME=DIR` (per-part WAVs named by crop slug);
  - add `--no-search`, which exposes `compare_search_signals(run_search=False)`, already in `match/signal_benchmark.py`;
  - add `--reference-source {amp,single_guitar_mix,stem}`;
  - add per-band and same-band/other-band breakdowns to the summary.

  Add a numpy probe builder: 4 × 1.5 s guitar-active clips, 50 ms fades, −22.9 LUFS (provisional: E1 checks it). It builds two libraries:
  - **L1:** for each part, DIs from three *other* set-2 bands. Local only.
  - **L2:** Guitar-TECHS P1/P2 clips (CC BY 4.0), pinned by SHA-256.
- **R1, prior check.** Fit the factory-preset prior and compute the Mahalanobis distance of every stored no-DI answer (the `runs/start-*` folders and the `match-pipeline-set2-sw50r*.json` answers). Correlate it with each answer's change in score against its own start.
  - **Pass:** Spearman ≥0.3, or answers outside the 90% region at least 1.5× as likely to have got worse.
  - **Fail:** shelve the prior.
- **B0, your call.** For Tone King without a DI, return neutral settings and skip the noise search. The measurement behind it is the objective proxy only, with no listening: further than neutral on 29 of 43 with level left out, 38 with level. See §5.

### Phase 1: the probe swap (about one evening plus two nights)

**E1, inversion-only screen.** Both amps, all 43 parts, about 20–25 minutes per amp. Arms:
- `noise`
- L1
- L2
- `retrieved`: a song-picked DI from another band
- `oracle_pick`: the other-band DI spectrally closest to the true DI
- `amptrack_as_di`: a diagnostic that uses the reference itself as the probe

Gates:
- **Sanity:** L2 closer than `noise` on ≥30 of 43. If not, fix the probe level or build before spending E2's hours.
- **Song-side retrieval** survives only if `oracle_pick` beats L1 on ≥30 of 43 with a mean gain ≥0.1. Otherwise drop it for good.
- **`amptrack_as_di`** is expected to collapse toward a transparent preset: fitted EQ curves nearly identical across parts (spread under 1 dB per band) and no better than L1 on 30 of 43. If so, close the "stem as its own DI" idea.

**E2, SW50R full search.** 20 parts, arms L2, L1 and `other`, plus in-run neutral, budget 300, about 3.4 h with 3 workers.
- **Pass:** L2 closer than neutral on ≥15 of 20 (sign test, two-sided p≈0.04) across most bands, and its median no worse than `other`'s by more than 5%.
- **Fail:** ≤12 of 20. The earlier gain then came from the shared recording chain. L1 against L2 shows whether a matching chain is what matters.
- **If it passes:** run the remaining 23 parts with L2 and neutral (about 1.3 h) as confirmation before building.

**E3, Tone King rhythm.** The same arms on the same 20 parts, in two batches of 10 parts with fresh processes, about 3–3.4 h.
- **Pass:** ≥14 of 20 closer than neutral, with a median ≥5% closer.
- **Fail:** B0 (if adopted) stands.

**Built after E2 and its confirmation pass (B1, about 2 days).** Library-DI probe as the Morgan no-DI default in `match_preset.py`, with the level trim done through the same probe and the guitar check kept. Check loudness with `benchmark_match_pipeline.py` against the "within ±3 LU" figures it already reports. Tone King joins only if E3 passes.

### Phase 2: the mix and the start (about two nights)

**E4, mix rungs.** SW50R, the same 20 parts, the winning probe. Reference rungs: amp track, single-guitar mix, and the Demucs stem of `mix_instrumental.wav`, all in one run. About 3.4 h plus 15 minutes of Demucs. Report the single-guitar sessions separately from the multi-guitar ones.
- **Pass for the stem:** closer than in-run neutral on ≥13 of 20, keeping ≥50% of the amp-rung median gain.
- **If the single-guitar mix passes and the stem fails,** separation is the bottleneck. Try a symmetric-degradation arm, which passes each candidate through the same backing and separation (about 1 s of Demucs per candidate), or a stem from a better separator.
- **If only multi-guitar parts fail,** the problem is choosing which guitar, so lean on the user-chosen passage.

**Built after E4 passes (B2, 2–3 days).** An optional `[separate]` extra with Demucs and the window selection.

**Sanity check by ear.** The Telefunken "Fragments" session ships a real master. Use it, not the unity-sum crops, before claiming anything about mastered songs.

**E5, topology headroom and factory-preset start.** 43 parts, each candidate topology, neutral settings plus inversion through L2, scored on the second 5 s of each crop after choosing on the first 5 s (this controls the bias of picking a minimum). Arms:
- the fixed SW50R topology
- the split-half oracle
- render-selection
- random
- the inverted top-ranked factory preset

About 1.5–2 h.
- **Headroom pass:** the oracle median is ≥15% closer than the fixed topology on ≥30 of 43 and ≥9 of 13 bands. Otherwise drop topology work.
- **Then:** build the render-selection start (B3, 1–2 days) if it recovers ≥50% of the oracle gain. Consider a classifier only if it does not.

**E8, prior arm (only if R1 passed).** One arm with the prior weight α tuned on 5 other parts, on E2's 20 parts, about 1.1 h.
- **Pass:** ends further than its start on ≤5 of 20, while keeping ≥90% of the median gain.

### Phase 3: the two diagnostics that decide any ML spending

**E6, cross-performance regret harness.** Extend `scripts/study_harmonic.py`:
- 16 set-2 development DIs from at least 8 bands, at native level and at the probe level E1 settles;
- 64 settings (48 Latin-hypercube samples plus 16 factory presets) on SW50R and on Tone King rhythm;
- a mixed-and-separated context for 16 settings.

About 1.5 days of code. Machine time: minutes per amp at the committed render rates, about 30 minutes of Demucs, and 5–15 minutes of extraction per model.

**Metric: regret.** For a target rendered through DI A, pick the candidate nearest to it as rendered through DI B. Regret is the same-DI distance between the target and that pick, both rendered through A. Top-k is not used, because many settings sound alike.

Rows:
- `unpaired-v3` total (reported first)
- timbre only
- numpy LDA, folded by band
- source-normalised timbre
- frame MMD
- AFx-Rep
- Fx-Encoder++
- Open-Amp, only if a checkpoint is actually obtainable
- CLAP, as the floor

Gates:
- **Pass:** median regret ≤0.75× that of `unpaired-v3` on isolated targets for both amps, not worse on separated stems, and Spearman ≥0.6 against the same-DI distance.
- **If `unpaired-v3`'s regret is already near the same-DI floor,** the loss is not the bottleneck. Stop this line.
- **If a numpy row passes:** add an `unpaired-v4` profile (B4, 1–2 days) and rerun E2's winning arm under it, about 1.1 h. Pass: ≥2 more parts beat neutral and the median is ≥10% lower.
- **If only a torch row passes, or none does while the gap is real:** go to E9.

**E7, performance versus spectrum.** SW50R, 20 parts, full search (inversion alone cannot see performance), about 3.4 h. Arms:
- L2
- `perf_generic`: the true DI re-EQ'd to L2's spectrum
- `same_degraded`: the true DI with soft clipping, a ±3 dB tilt, 10 ms smear and −20 dB bleed

Gates:
- **Fund DI recovery (approach 6)** only if `perf_generic` beats L2 on ≥15 of 20 with a mean gain ≥0.15. Otherwise close it, along with transcription and resynthesis.
- **If it passes,** `same_degraded` shows how good a recovered DI must be. Run RemFX's public checkpoints render-free on the 43 amp tracks (1 h) before training anything.

### Phase 4: built only after the gates above

- **E9, encoder pilot.** Run only if E2 passes, E6 shows a real gap, and Tone King or the mix still fails.
  - Training data: SW50R, about 16k renders of CC BY DIs (about 1 h), with no set-2 DIs.
  - Training: about 2 h on MPS.
  - Gate on E6's regret: ≤0.5× on isolated targets, ≤0.65× on stems, Spearman ≥0.7.
  - Then a 20-part arm against the best probe arm: pass at ≥14 of 20. Only then all 43 parts and Tone King.
- **Approach 7** comes only after a working encoder, and only to cut renders.

### Listening test

After B1 passes the 43-part confirmation, and again after B2 or B4 if they are built, declare a blind test in a committed file before running it, following the `docs/heldout-listening-sw50r*.md` procedure. The declaration covers:
- **Parts:** set-2 held-out parts, on passages where the guitar is exposed (dense mixes made earlier A/B tests hard).
- **Arms:** the new no-DI match against today's noise-probe match against neutral. From the song once B2 exists; from the amp track before that, stated as such.
- **Pass:** the new match is preferred over today's on at least two-thirds of the parts the listener can tell apart, and is clearly worse than neutral on no more than one part.

### Timeline

Phases 0–1 take about a week including the overnight runs, and phases 2–3 about another week. After that, the gates decide whether any ML work starts.

## 4. What not to do

- **Train anything on noise-probe or synthetic-guitar renders.** This rules out a denser atlas, an atlas plus a network, and a bigger M7-2 regressor. At the same settings, noise and guitar fingerprints sit 2.1–2.4 apart, more than a target sits from neutral (1.2–1.9). M7-2's parameter loss lowered parameter error while the sound moved further away, and 17 controls were poorly identifiable even from one source.
- **Teach an embedding that noise counts as a guitar.** The amp responds to bursts differently (the probe is about 10 LU hotter, with different crest and intermodulation). Making noise and guitar look the same would erase the drive information the match needs.
- **Tune the Karplus-Strong probe further.** It beat noise through one passage and not the other. Real DIs beat it at no extra cost to the user.
- **Use the separated stem as its own DI.** Expected to converge on the plugin's most transparent setting for every song. E1's `amptrack_as_di` arm tests this before it is closed.
- **Swap the optimiser** (Bayesian optimisation, TuRBO, SPSA, surrogate CMA-ES, multi-fidelity). With the part's own DI, today's CMA-ES wins 43 of 43, Tone King included, so the optimiser is not what failed. Revisit noise handling on Tone King only if, after a better probe, the stored searches show more than 30% rank flips.
- **Build a differentiable neural proxy now.** DeepAFx-ST's proxies underperformed even for an EQ and a compressor, it would cost about 8 days at low confidence, and it does not change the loss that failed.
- **Use distribution matching (frame MMD) as the loss.** Short frames resolve individual harmonics, so it is more sensitive to the notes, not less. It gets a free row in E6 and nothing more.
- **Ship a regressor's single prediction as the answer.** See M7-2, and Synth-JEPA's out-of-domain numbers.
- **Use Fx-Encoder++ on the full mix as the front end.** Instrument-wise R@1 is about 3% of 500, guitar was not evaluated, and the licence is non-commercial.
- **Ship non-commercial or unlicensed material.** That covers BS-RoFormer-SW (licence unknown), Fx-Encoder++ weights (CC BY-NC), anything derived from IDMT (NC-ND), and Cambridge-MT material.
- **Mix datasets that must stay apart.** Never use set-1 Guitar-TECHS P3 music or held-out parts in a library or a training set. Use leave-band-out whenever a set-2 development DI trains anything.
- **Per-song test-time training, or predicting output level from a mastered mix.** The first takes hours per song. The second is not identifiable: loudness in a master reflects mastering, not the preset.

## 5. Decisions needed from you

1. **Where the shipped DI clips come from.** The safe source is Guitar-TECHS P1/P2 (CC BY 4.0). Options:
   - bundle a 6-second probe in the repo with attribution, which needs your licence call (the licence question in the plan's §10 item 4; nothing else in that item applies, since you will not record a DI);
   - download it on first use.

   EGDB's DIs have no confirmed licence, and GOAT is by request and research-only. This is needed before B1, not before the experiments, which can use local DIs.
2. **Adding Demucs plus torch as an optional extra for songs.** It is several hundred MB, MIT-licensed, and archived. The alternative is that you supply a guitar stem yourself when you have one, for example from Logic Pro 11.2's Stem Splitter if you use Logic, which scores about 9 dB against Demucs's 3. Needed before B2.
3. **Tone King without a DI (B0).** Return neutral settings instead of the noise search? It rests on the objective proxy alone: further than neutral on 29 of 43 parts with level left out. The starting-point runs measuring Tone King's Default, Reset All Settings and neutral starts finish tonight and will inform it.
4. **Pointing at a timestamp.** Would you point the tool at a passage where the guitar is exposed (the excerpt-start option already exists)? It is cheap for you, and it is the most practical answer for songs with several guitars.
5. **Later, only if Phase 3's gates call for it:** two to three weeks of work and a torch extra for a trained encoder. Using non-commercial models for local screening (never shipped) needs only a yes now.

Not a decision: you will not be asked to record a DI. E2's L1-against-L2 arms only show whether a library DI from a similar recording chain matters, which shapes the choice of library.