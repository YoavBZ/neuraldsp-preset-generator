# Repair rebuilt-DI dynamics before swapping separators

Evidence tags used throughout: **[V]** verified (a researcher opened the source and read the claim, or it is in this repo's committed docs or code); **[I]** inferred (reasoning from verified facts); **[U]** unverified (search snippet, a local un-committed audit, or a claim that could not be traced). Links are written to work from `docs/research/`. Documents that exist only on a branch are linked on GitHub.

**Bottom line.** No open method today returns a guitar DI from a song accurately enough to steer the Morgan knob search. The project's own evidence also says the next money should go into the rebuild's **dynamics** and into a better **rebuild-quality measure**, not into another separator. The known-target control failed on clean plugin renders, before any separation. Through C′, the search objective ranks the target settings **worse than the start on 7 of 12 cells**. An oracle EQ to the true DI's spectrum does not fix that ranking. The audit blames a compressed rebuild, with crest factor 3–5 dB low ([song-settings-plan.md, ml/cprime-folds](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/song-settings-plan.md#L336-L373)) [V]. So a better stem can remove at most the second error. Separation still matters, but the zoos add no new licence-clean guitar model, no open model outputs a dry or DI guitar, and the only transient study finds that HT-Demucs flattens dynamics most ([arXiv 2609.04224](https://arxiv.org/abs/2609.04224)) [V]. In the literature, no guitar de-amping paper reports any dynamics metric. The best-supported fix is structural: the De-limiter's sample-wise gain head restored crest factor from 3.66 to 6.35–6.48 against a true 6.73, with MIT code and weights ([arXiv 2308.01187](https://arxiv.org/html/2308.01187v2)) [V]. Steering without a DI has been tried on the project's own data and failed: DI-free statistics and donor DIs gave regret of about 0.35 against 0.04 with the part's own DI ([di-free-distance-results.md](../di-free-distance-results.md)) [V]. Such signals are useful only as guards or proposers. Coherence has never been validated against search success and has moved against picks twice. The gate should be the **rank margin**, meaning whether the target ranks above the start through the rebuilt DI. It costs two renders per cell. The ranked plan below is four local experiments:

1. A two-hour separator swap on the 5 set-3 check parts, paired with a rank margin.
2. A degradation ladder that validates the margin and tests the dynamics hypothesis.
3. A fitted expander-and-tilt correction of C′.
4. A dynamics-aware retrain, run only if the correction fails.

## The rebuild alone already breaks the search objective

### What the brief's numbers are, and where they come from

Most of the brief is verbatim from the "Recorded outcome (2026-10-15)" section of the step-3 plan on `ml/cprime-folds`. Two items are not. The spectral-balance figures appear in no committed file. The 0.28 coherence was measured against clean plugin renders, not amp tracks or stems.

| Claim in the brief | Where it is | Status |
|---|---|---|
| True DI closes ≥ 50% of the gap on 9/9 control cells | 9 of 12 cells informative (d_S − d_target ≥ 0.1); "closes ≥ 50% of the gap on 9 of 9" ([L340–342](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/song-settings-plan.md#L340-L342)) | [V] |
| C′ closes ≥ 50% on only 3/9 | Same section; mean shortfall +0.320 against the true DI's −0.062 ([L343–345](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/song-settings-plan.md#L343-L345)) | [V] |
| Target scores worse than the start on 7/12 cells through C′ | Counted over all 12 cells, not just the 9 informative ones; "oracle EQ … doesn't fix the ranking. So no search budget would recover the target" ([L348–350](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/song-settings-plan.md#L348-L350)) | [V] |
| Control "recordings" were clean renders, not stems | S with five settings moved, rendered through the part's raw DI; "a pipeline check … C′'s training domain, not a stem" ([L104–119](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/song-settings-plan.md#L104-L119)) | [V] |
| C′'s output is squashed | "crest factor 3–5 dB lower on 10 of 12 cells and frame-envelope correlation 0.09–0.84", labelled "likely" ([L351–353](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/song-settings-plan.md#L351-L353)) | Number [V]. Method [U]: it was computed in a local `tmp/` audit, and no crest or envelope code is in git |
| ≈ 0.28 coherence from clean renders | "rebuilt-vs-raw coherence is about 0.28 here, against 0.13 on stems" ([L354–355](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/song-settings-plan.md#L354-L355)) | [V] number. The band is not stated, and it is measured against the **raw** DI on clean plugin renders [I] |
| ≈ 0.13 from htdemucs_6s stems | Step-1 check 2: mean 1–3 kHz coherence 0.125–0.136 over set 3's 5 clean and crunch stem parts ([cprime-folds-results.md](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/cprime-folds-results.md#L20-L48)) | [V] |
| "2–4 dB dark above 2 kHz, 1–5 dB heavy at 200–1000 Hz" | In no committed file on any of the 10 remote branches (searched with `git grep`). Probably from the local audit or the session's chat | **[U], untraceable** |

Two cautions follow from the table [I]. First, 0.28 and 0.13 come from **different parts**: the 12 control parts against the 5 set-3 parts. So "separation halves coherence" is not a paired measurement. Other committed figures sit between them: C′ scored 0.207 at 1–3 kHz on 18 amp-track parts ([residual-di-results.md](../residual-di-results.md)) [V]; a rebuild from a plugin render scored 0.196, against 0.108 from a real amp track ([sim-real-gap-results.md](../sim-real-gap-results.md)) [V]. Second, the 5-part check mean is dominated by one part. Per part, the values are 0.044–0.294, with just-don't-talk at about 0.29 and femme and get-out-of-bed near 0.05 ([cprime-folds-results.md](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/cprime-folds-results.md#L32-L41)) [V]. Any separator swap measured on those 5 parts will mostly report what happens on one or two of them [I].

The committed evidence on "tilt" is milder than the untraced figures. C's rebuild is −4.8 dB at 3–8 kHz, and C′'s is **+0.6 dB** ([residual-di-results.md](../residual-di-results.md)) [V]. Re-equalising the rebuilt DI to the true DI's long-term spectrum made menu picks **worse** (+0.101; 24 wins, 41 losses) ([set3-gap-split-results.md](../set3-gap-split-results.md)) [V]. A true DI with "mild" tilt, smear, soft clip and −20 dB bleed still kept the oracle pick on 23–24 of 25 parts ([di-robustness-results.md](../di-robustness-results.md)) [V]. Tilt is real, but nothing committed shows that it is what flips the ranking [I].

### Why the objective is biased, not just noisy

A 7-of-12 ranking inversion means the minimum of the search objective is in the wrong place. A bigger budget or a better optimiser cannot fix that; only a corrected input or a different objective can ([L348–350](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/song-settings-plan.md#L348-L350)) [V]. Four committed results point at dynamics and waveform detail rather than long-term spectrum [I]:

- The set-3 gap split puts **87% of the rebuilt-to-oracle gap in "the rest"** (dynamics, transients, detail), against 13% for level ([set3-gap-split-results.md](../set3-gap-split-results.md)) [V].
- Every network is less coherent with the true DI than the recording it was given: 0.196 against an input of 0.24 on renders, in 96 of 99 cases ([sim-real-gap-results.md](../sim-real-gap-results.md)) [V].
- Above 3 kHz the rebuild is essentially unrelated to the DI (coherence about 0.02) ([audit-2026-10-11.md](../audit-2026-10-11.md)) [V].
- The judge removes a **single** median level offset per comparison ([`analysis/aligned.py`](../../analysis/aligned.py), `_symmetric_difference`) [V]. A DI whose note-to-note dynamics are squashed therefore leaves wrong frame levels everywhere, and through a driven amp the timbre is wrong too [I].

The training recipe is consistent with the squash. C′ normalises **both** the input and the target crop to a fixed standard deviation (`x / x.std() * 0.1`, `y / y.std() * 0.1`), which removes any absolute-level cue. Its default loss is `100·L1 + MR-STFT magnitude` ([`learn/direc.py`](../../learn/direc.py), lines 269–279 and 433–434) [V]. Under L1 or L2, a regressor facing a one-to-many inverse outputs a conditional median. That flattens peaks and lifts decays, which is what a 3–5 dB crest deficit looks like [I]. The same recipe, 100·L1 + MR-STFT on a Demucs-family U-Net, is RemFX's removal loss ([arXiv 2308.16177](https://arxiv.org/html/2308.16177)) [V]. No paper using it reports crest or envelope metrics, so the squash is unmeasured in the literature rather than contradicted by it [I]. The declipping literature gives direct evidence that regression-only Demucs restorers come out over-smooth. A regression model counted 1.17 M waveform extrema against 1.52 M in clean audio; its GAN version restored 1.67 M ([DDD, arXiv 2401.03650](https://arxiv.org/html/2401.03650v1)) [V].

## Separation adds a second error that no open model removes

The merged separation report, [guitar-separation-2026-10.md](guitar-separation-2026-10.md), already answers which separator is best. Its conclusions: keep htdemucs_6s. BS-RoFormer SW leads by +3.8 dB on MVSEP but has unknown weights licence. Mega-53 gained only +0.5 to +0.6 dB paired on the project's 61 parts and loses the top octave. Multi-guitar parts, not network quality, cap every model. That report also holds the licence table, the Mac CPU timings and a declared re-test design [V]. This section adds only what matters for inversion.

### The zoos add instrumental and dereverb models, not guitar models

python-audio-separator's bundled list has 84 RoFormer entries. The only guitar-capable one is "BS Roformer SW by jarredou", which settles the merged report's open conflict. UVR's own remote list has **no** SW entry; its only guitar output is htdemucs_6s ([models.json](https://raw.githubusercontent.com/nomadkaraoke/python-audio-separator/main/audio_separator/models.json), [download_checks.json](https://raw.githubusercontent.com/TRvlvr/application_data/main/filelists/download_checks.json)) [V]. Everything else that outputs "other" is a 4-stem model or an everything-but-vocals model. The latter is useful only for a vocals-first pre-step that the development pipeline already does with an oracle vocal-free context [I]. Weights licences in the zoo are mostly missing:

| Zoo source | Code licence | Weights licence | Use under the project rule |
|---|---|---|---|
| KimberleyJSN Mel-RoFormer (base of many instrumental fine-tunes) | — | **MIT** tag; training data not stated ([HF](https://huggingface.co/KimberleyJSN/melbandroformer)) [V] | Tolerable, but it is a vocal model |
| pcunwa, GaboxR67 instrumental and other fine-tunes | — | **No tag on any repo** ([HF API](https://huggingface.co/api/models?author=pcunwa)) [V] | Flagged, unclear |
| becruily (incl. guitar, instrumental) | — | None on older repos; **CC BY-NC 4.0** on the two newest ([HF API](https://huggingface.co/api/models?author=becruily)) [V] | Excluded or flagged |
| anvuew (incl. all dereverbs) | — | **GPL-3.0** on every repo ([HF API](https://huggingface.co/api/models?author=anvuew)) [V] | Not on the project's list; research-only at most |
| Sucial dereverb/echo | — | **CC BY-NC-SA 4.0** ([HF card](https://huggingface.co/Sucial/Dereverb-Echo_Mel_Band_Roformer)) [V] | Research-only anchor, flagged |
| FoxJoy, aufr33-jarredou, viperx, "Kim Inst" (UVR release assets) | — | No statement found [V absence] | Research-only anchor until a licence is found |
| SCNet (starrytong), kuielab MDX-Net | **MIT** ([SCNet](https://raw.githubusercontent.com/starrytong/SCNet/main/LICENSE), [mdx-net](https://raw.githubusercontent.com/kuielab/mdx-net/main/LICENSE)) [V] | 4-stem, MUSDB-trained [I] | No guitar stem |

### Demucs flattens dynamics; RoFormers soften attacks

The only quantitative transient and dynamics study of separators is Ding's (arXiv 2609.04224, July 2026). It measures **drums** on MUSDB18-HQ, not guitar ([arXiv 2609.04224](https://arxiv.org/abs/2609.04224)) [V]. It finds that SDR does not predict transient or dynamic fidelity (|ρ| ≤ 0.29). It also finds that the two architecture families fail in opposite ways:

| Model | Drum SI-SDR | Attack-slope error | Envelope-variation error | SAR |
|---|---|---|---|---|
| HT-Demucs | 10.07 | 1.27 | **4.09 dB** | 8.9 |
| BS-RoFormer | 11.88 | **1.33** | 1.78 dB | 9.8 |
| SCNet-XL | 11.74 | **0.64** | 2.45 dB | **11.0** |

Onset timing survived in every model [V]. The SDX23 listening test likewise found no clear correlation between SDR and expert preference ([arXiv 2308.06979](https://arxiv.org/abs/2308.06979)) [V].

For a rebuild that drives a nonlinear amp, the inference is that htdemucs_6s stems probably arrive with flattened envelopes. That **compounds** C′'s own squash. RoFormer stems keep envelope variation better, but they blunt pick attacks and, per the merged report, lose 8–13 kHz energy [I]. SCNet-class models scored best on attacks, but no licence-clean SCNet guitar checkpoint exists [I]. Bleed from other guitars, not transient smearing, is still the more likely cause of most of the stem coherence loss. Any stem metric should therefore be reported separately for single-guitar and multi-guitar parts [I]. Ding's evaluation code (crest, attack slope, envelope variation) is public at `github.com/dingchuxin/MSS-eval`, but its licence was not checked [V/U].

### Dereverb: vocal models hurt guitar, full-track models have no licence

No open separator outputs a dry or DI guitar, and no guitar-specific dereverb model was found [V absence]. On MVSEP's reverb benchmark the "other" stem is the relevant column. There, the do-nothing reference scores **4.65**. The full-track models beat it: FoxJoy Reverb HQ scored **8.02** and aufr33-jarredou MDX23C De-Reverb **7.72**. Every vocal-only model scored below it, at 0.98–3.41, except anvuew's stereo BS at 5.40 ([MVSEP algorithm 46](https://mvsep.com/algorithms/46)) [V]. The vocal dereverbs were trained on mono single voices. Their cards say they strip off-centre parts and handle high frequencies weakly ([anvuew card](https://huggingface.co/anvuew/dereverb_mel_band_roformer), [Sucial card](https://huggingface.co/Sucial/Dereverb-Echo_Mel_Band_Roformer)) [V], and those are exactly the tilt and attack errors at stake.

The two useful full-track models have no stated weights licence, so they qualify only as research-only anchors [I]. Dereverb also cannot remove another guitar. Whether it helps at all depends on whether the project's amp tracks are drier than the stems, which is not established [I]. The closest research task, Music Source Restoration, cascades a dereverb but applies it **only to vocals**, "since reverberation for instrumental stems may be part of the intended timbre" ([X-LANCE MSR winner, arXiv 2602.09042](https://arxiv.org/abs/2602.09042)) [V].

### Apple-silicon runtime adds little new

The only new Apple figures are audio-separator's `seconds_per_minute_m3` field. Light RoFormers run at **8.6–11.2 s per minute of audio**, "BS-Roformer-De-Reverb" at **39.4 s/min**, and large Mel/BS-RoFormers at **155–192 s/min**. The M3 variant, backend and precision are undocumented ([models-scores.json](https://raw.githubusercontent.com/nomadkaraoke/python-audio-separator/main/audio_separator/models-scores.json)) [V values, U conditions]. The project's own CPU timings remain the firmest: about 30 s/min for htdemucs_6s and about 204 s/min for Mega-53's two heads ([guitar-separation-2026-10.md](guitar-separation-2026-10.md)) [V]. A dereverb post-step would roughly double to triple htdemucs_6s's cost [I]. No Apple timing exists for FoxJoy, MDX23C or SCNet [V absence].

## No published de-amper reports dynamics; a gain head is the best lead

### Methods 2019–2026: code exists for some, dynamics for none

| Method | What it inverts | Code / weights / licence | Run on project data? | Reported result |
|---|---|---|---|---|
| EG-VAE (arXiv 2608.05513, Aug 2026) | Full amp chains; tested on 96 unseen **Morgan** presets | **None**; the demo page still has a code placeholder ([demo](https://guitar-tone-demo.vercel.app/)) [V] | No; project built EG-VAE-lite instead | Removal mel 1.19 against Distortion Recovery 1.22: a tie objectively, a win by listening ([arXiv](https://arxiv.org/html/2608.05513)) [V] |
| LOUDAR (arXiv 2608.01972, Aug 2026) | Amp distortion, by latent diffusion and a fitted operator | Code **MIT**. HF checkpoint tagged MIT but trained on **GOAT (CC BY-NC)** ([LICENSE](https://raw.githubusercontent.com/michalsvento/loudar/master/LICENSE), [HF](https://huggingface.co/api/models/msvento/loudar)) [V] | No | FxEnc++ distance 0.308, against 0.323 for a supervised regressor. No dynamics metric, no listening test for guitar, runtime not reported (300 steps) ([arXiv](https://arxiv.org/html/2608.01972)) [V] |
| NLDistortionDiff (JAES 2025) | Memoryless clipping only | Code and checkpoints; **no LICENSE file** ([GitHub](https://github.com/michalsvento/NLDistortionDiff)) [V] | No | Violin plots only; "errors at sharp transitions" ([arXiv](https://arxiv.org/html/2501.05959)) [V] |
| Distortion Recovery (DAFx 2024) | BIAS FX2 chains | Evaluation code MIT; **no weights** [V-prior] | No | Best FAD; ESR 2.29, so no waveform fidelity ([arXiv](https://arxiv.org/html/2407.16639)) [V] |
| RemFX (WASPAA 2023) | Single effects incl. distortion and compression | Code **Apache-2.0**, weights **CC-NC** ([LICENSE](https://raw.githubusercontent.com/mhrice/RemFx/main/LICENSE), [Zenodo](https://zenodo.org/api/records/8218621)) [V] | No | Distortion SI-SDR 16.37 → 24.36 dB; no dynamics metric for compression removal ([arXiv](https://arxiv.org/html/2308.16177)) [V] |
| **De-limiter** (WASPAA 2023) | Mastering limiter on mixes | Code **and weights MIT**; data CC BY 4.0 ([LICENSE](https://raw.githubusercontent.com/jeonchangbin49/De-limiter/main/LICENSE)) [V] | No | **Crest 3.66 → 6.35–6.48 (true 6.73)**; LRA 7.02 → 7.40–7.48 (true 7.48) ([arXiv](https://arxiv.org/html/2308.01187v2)) [V] |
| DRC inversion (Sun et al., 2024) | Compressor, by parameter estimation and a model-based inverse | Code **MIT**; weights as release assets ([LICENSE](https://raw.githubusercontent.com/SunHaoRanCN/DRC_Inversion/main/LICENSE)) [V] | No | MSE 0.0082 with classified profiles against 0.27 for Demucs ([arXiv](https://arxiv.org/html/2411.04337v1)) [V] |
| MSR U-Former (arXiv 2505.21827) | Mix → "unprocessed" stem | Weights **Apache-2.0**, incl. `electric_guitar.pth` ([HF](https://huggingface.co/api/models/yongyizang/MSR_UFormers)) [V] | No | Electric guitar SI-SDR **−1.25 to −1.68 dB** ([arXiv](https://arxiv.org/html/2505.21827v1)) [V] |
| Project C, C′, R, L, EG-VAE-lite E0/E0b/E1 | Morgan renders → DI | In repo | Yes | C′ best among networks. R futile (+0.059). DAC E0b picks near the oracle (−0.126 against −0.131); E1 mapper failed ([residual-di-results.md](../residual-di-results.md), [egvae-lite-plan.md](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/egvae-lite/docs/egvae-lite-plan.md#L253-L275)) [V] |

The table makes one point plainly. **No guitar de-amping paper reports crest factor, envelope or transient metrics, and none tests mic'd amps, mixes or separated stems** [V, checked in EG-VAE, Distortion Recovery, Imort, RemFX, NLDistortionDiff and LOUDAR]. The 2026 work does not change the ranking of options. EG-VAE has nothing to download. LOUDAR is research-only by its training data, needs 300 diffusion steps per clip, and has a 12 Hz latent that is unlikely to carry sub-80 ms transients except by generative invention [I]. LOUDAR's own reconstruction ceiling (0.105, against about 0.31 for the restorers) says the **restoration step, not the codec, is the bottleneck**. That matches the project's E0 (codec round-trip keeps the picks) against E1 (the mapper fails) [I].

### Dynamics: structure beats loss terms, and adversarial training is a late resort

The De-limiter multiplies its input by a predicted **per-sample gain in [0, 1]**, trained with SI-SDR alone. With the same data, a direct-waveform "synthesis" network reached only **12.1–12.7 dB SI-SDR against 24.0–24.4 dB** for the gain version ([arXiv 2308.01187](https://arxiv.org/html/2308.01187v2)) [V]. For C′ this suggests a dynamics head: output = U(x) × g(t), where g is a positive frame-rate gain. An alternative is a separate envelope network that predicts the DI's log-RMS curve, imposed by frame-wise gain [I]. Unlike a limiter, the amp also reshapes the waveform, so a gain head is an add-on to C′, not a replacement [I]. Compressor inversion gives the parametric analogue: estimate the parameters, then invert with a model. Its authors warn that "parameter errors get amplified during inversion". In a black-box version, **expansion succeeded 80.0% of the time against 90.8% for compression** ([arXiv 2411.04337](https://arxiv.org/html/2411.04337v2), [arXiv 2607.19645](https://arxiv.org/html/2607.19645v1)) [V]. Undoing compression is the harder direction, and that is exactly the direction C′ must go [I].

**No paper defines and evaluates an explicit envelope or crest-factor loss for restoration** [V absence]. The only envelope-L1 loss found is in synthesis ([arXiv 2310.04811](https://arxiv.org/pdf/2310.04811)) [U]. Hyper-RNN shows that crest factor is the first thing weak conditioning loses. On an OD-3 pedal, crest error was 2.93 with concatenation against 0.68 with FiLM ([arXiv 2408.04829](https://arxiv.org/html/2408.04829v1)) [V]. The cheap, untested changes are a log-RMS envelope L1 at 10 and 50 ms, a per-window crest or peak-to-RMS term, an onset-strength term, and pre-emphasis for the dark top [I]. Each needs its own pre-check against the true DI.

Adversarial losses are the published cure for over-smoothing, but they cost objective fidelity. DDD's GAN lost PESQ at 1 dB (2.99 → 2.55) yet won listening tests ([arXiv 2401.03650](https://arxiv.org/html/2401.03650v1)) [V]. The top two MSR-challenge teams used only L1 and STFT losses ([arXiv 2601.04343](https://arxiv.org/html/2601.04343v1)) [V]. In a render-and-judge loop, an invented top would read as fizz [I]. Diffusion priors are not a dynamics fix: neither LOUDAR nor NLDistortionDiff reports dynamics, and both need 50–300 steps [I].

### Conditioning helps when the effect is known, and the search always knows its candidate

RemFX quantifies how much knowing the effect helps. At one effect, the oracle label gives **16.99 dB SI-SDR**, a predicted label 16.67 dB, and a monolithic model 11.53 dB, barely above the 11.52 dB input ([arXiv 2308.16177](https://arxiv.org/html/2308.16177)) [V]. Okita and Katayose's "predict dry, then search the chain" loop lifts wet SI-SDR from 18.18 to 23.07 dB with the true dry signal ([arXiv 2604.22276](https://arxiv.org/html/2604.22276)) [V-prior]. That is the same architecture as arm A. There is counter-evidence: blind estimation sometimes beat the informed setting in NLDistortionDiff ([arXiv 2501.05959](https://arxiv.org/html/2501.05959)) [V]. **No paper conditions an amp-inversion network on amp and knob settings** [V absence].

The project has an unusual advantage here [I]. During search the candidate preset is known, so an inverse conditioned on it can answer "if preset p made this record, what was the DI?". Self-consistency then becomes a score. That costs one inversion per candidate, so it suits re-ranking a short list. A cheaper version conditions only on amp (PR12, SW50R, AC20) and a coarse gain bucket. It tells the network how much to expand, which is the ambiguity behind the conditional-mean squash. Training with conditions randomly dropped would keep blind mode as good as C′ [I].

### Joint separation and inversion has no usable artefact

MSR is the nearest task, mapping a mix to an unprocessed stem. Its guitar target is whatever Mixing Secrets supplies, probably mostly mic'd amps rather than DIs [I], and its electric-guitar SI-SDR is negative ([arXiv 2505.21827](https://arxiv.org/html/2505.21827v1)) [V]. The newest modular system, Restore-Separate-Restore (Oct 2026), has an empty repo ([GitHub](https://github.com/theMoro/music_source_restoration)) [V]. Its idea still supports the project's structure: stem experts **fine-tuned on the separator's own artefacts** ([arXiv 2610.08284](https://arxiv.org/abs/2610.08284)) [V]. For C′'s successor, that means training on htdemucs_6s output of the project's own multitracks, not only on clean renders [I].

## Steering without a clean DI works only as a guard or a proposer

| Approach | Code exists | Tried here | Result | Verdict |
|---|---|---|---|---|
| DI-free statistics (LTAS, log-mel spread, MFCC, masked, LDA) | Project code | Yes, 8 rows | Regret about 0.35 with other notes, against 0.04 with the same notes; on stems, every row worse than the song-blind constant ([di-free-distance-results.md](../di-free-distance-results.md)) [V] | Failed; notes move these more than presets do |
| Learned processing embeddings (RLAT, AFx-Rep, Fx-Encoder++) | RLAT code at SonyResearch, licence unverified; Fx-Encoder++ NC [V/U] | Not as a search guard | RLAT cross-instrument retrieval 49.8%, against AFx-Rep 20.5% ([arXiv 2608.28127](https://arxiv.org/html/2608.28127)) [V]; no amp-settings result | Guard term only |
| Donor or register-matched DIs | Project code | Yes, 25 parts × 19–26 donors | Regret 0.32–0.48 through donors, against 0.035–0.30 through the part's own DI ([di-free-distance-results.md](../di-free-distance-results.md)) [V] | Failed for time-pooled statistics |
| Adversarial unpaired amp modelling | Wright et al. 2023 | No | Learned a tone from 30–40 min of unpaired audio; 4–10 GPU-h per model ([arXiv 2211.00943](https://arxiv.org/html/2211.00943)) [V] | A 10-s clip is far too little [I] |
| Conditioned differentiable amp proxy | PANAMA **MIT**, NAM **MIT**, NablAFx **MIT**, dasp-pytorch **Apache-2.0** ([PANAMA](https://raw.githubusercontent.com/ETH-DISCO/neural_amp_modelling/main/LICENSE), [NAM](https://raw.githubusercontent.com/sdatkinson/neural-amp-modeler/main/LICENSE), [NablAFx](https://raw.githubusercontent.com/mcomunita/nablafx/master/LICENSE)) [V] | No | PANAMA used 64 settings × 3 min ([arXiv 2507.02109](https://arxiv.org/html/2507.02109)) [V]. In DeepAFx-ST, neural-proxy gradients did **worse** than true DSP, attributed to proxy error ([arXiv 2207.08759](https://arxiv.org/pdf/2207.08759)) [V] | Proxy proposes, plugin decides |
| Joint DI + settings estimation | NLDistortionDiff (memoryless), LOUDAR (no knobs) | No | No amp-knob result exists [V absence] | New research; DI tilt and level trade off against amp EQ and input gain [I] |
| Post-correction of C′ (expander + tilt, or a fine-tuned De-limiter) | De-limiter MIT | No | No published test on a network-rebuilt DI [V absence] | Cheapest direct fix [I] |
| Judge robustness (per-frame level-normalised judge, level-conditioned spectra) | Project judge | No | Untested | Second objective, checked by rank margin [I] |

The project's own data has already closed off the purely DI-free route. "The performance (its notes, guitar and playing) moves these distances more than the preset does" ([di-free-distance-results.md](../di-free-distance-results.md)) [V]. Nothing in the 2024–2026 literature scores a learned embedding at ranking guitar-amp settings across different performances [V absence].

A content-robust embedding still has one property worth using: it never sees C′, so it does not inherit C′'s squash bias [I]. Add it as a penalty term next to `rebuilt_distance`. Then ask one question on renders that already exist: does it reduce the 7-of-12 inversions? Today's candidates have licence problems. RLAT's licence is unverified, Fx-Encoder++ is NC, and the ML plan already lists RLAT among excluded tools ([ml-plan-2026-10.md](ml-plan-2026-10.md)) [V]. Any such term is research-only until a clean model appears.

A Morgan proxy is cheap in data. Ten times PANAMA's scale is about 16k renders, under 2 h at the project's roughly 8–10k ten-second renders per hour [I; throughput is the earlier notes' project figure]. The risk is accuracy, which is where DeepAFx-ST's proxies failed. The safe pattern is to let the proxy only **propose** and to score every proposal with the real plugin and the real judge [I].

Joint estimation of DI corrections and knobs is identifiable only with a prior. One option is a coordinate-descent loop: alternate `knob_search` with a 20–40-render search over 4–8 DI-correction parameters, held inside the true-DI population's range of crest, tilt and level histogram per register. Without that prior, the loop will push the dynamics error into the knobs [I]. That makes it a follow-on to experiment 3 below, not a first step.

## Rank margin, not coherence, should gate every rebuild

### Coherence has never predicted picks and moved against them twice

None of the project's DI-quality metrics has been validated against pick or search success with a rank correlation [V]. Several committed results show they do not track it:

- **R and C′:** R's 1–3 kHz coherence (0.217) is above C′'s (0.207), yet R picks worse (+0.059). The project concluded that coherence "should not stand in for chooser quality" ([residual-di-results.md](../residual-di-results.md)) [V].
- **E0b and C′:** E0b has C′-level coherence (0.20) but oracle-level picks (−0.126 against C′'s −0.099). E0's coherence of 0.49 bought almost nothing more ([egvae-lite-plan.md](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/egvae-lite/docs/egvae-lite-plan.md#L253-L275)) [V].
- **Validation loss:** it rose while C′'s picks improved ([residual-di-results.md](../residual-di-results.md)) [V].
- **Long-term balance:** matching it made picks worse ([set3-gap-split-results.md](../set3-gap-split-results.md)) [V].

Coherence is a linear-predictability measure: scipy magnitude-squared coherence with `nperseg=4096`, averaged within bands ([residual_eval.py](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/learn/residual_eval.py#L69-L88)) [V]. The step-1 plan scoped it honestly: it "guards against a broken network, not small differences in quality" ([cprime-folds-results.md](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/cprime-folds-results.md#L74-L77)) [V].

The speech literature has the same pattern. Enhancement artifacts that a linear metric tolerates are "the main cause of ASR degradation", and adding back some of the noisy input lowered SDR while improving WER ([Iwamoto et al., arXiv 2201.06685](https://arxiv.org/abs/2201.06685)) [V]. Decision-focused learning states the principle: judge a predictor by the regret of the decision it drives ([arXiv 2310.04328](https://arxiv.org/abs/2310.04328)) [V].

### The proposed outcome and proxies

The outcome is the **rank margin** m = log d_rb(S) − log d_rb(T). These are judge distances, on the search half, through the rebuilt DI, for the start settings S and the target settings T. The binary version is m > 0, "the target ranks above S through the rebuild". This is what the user named as the comparison measure ([L360–369](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/song-settings-plan.md#L360-L369)) [V]. It costs **2 renders per cell per DI variant** [I].

A richer version is **panel agreement** τ_panel [I]. Render K ≈ 16 settings near S (S, T and 14 perturbations of the moved knobs and input gain) through both the rebuilt and the true DI, judge them, and take the Kendall τ between the two orderings. It costs about 2K renders per cell, and the true-DI half is shared across variants.

A recording-free variant is **multi-setting re-amp consistency**: the median over panel settings of d_judge(render(θ, rebuilt DI), render(θ, true DI)) [I]. Single-setting re-amp consistency against the record is not enough. Distortion is many-to-one, so many DIs reproduce the record through T and still mis-rank S [I].

The cheap intrinsic candidates need no renders: crest-factor error, log frame-RMS envelope correlation, the 90th–10th percentile RMS spread error (already computed in `learn/sound_desc.py`), onset-flux error, and band level errors at 200–1000 Hz and above 2 kHz (which also tests the untraced tilt figures). Coherence, LSD and MR-STFT are kept as baselines to beat [I].

One caution comes from the project itself. Five parts with low DI-to-record envelope correlation were fine "because their record envelopes are nearly flat from compression" ([knob-ceiling-2-results.md](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/knob-ceiling-2-results.md#L114-L115)) [V]. Envelope correlation therefore needs a floor on the true DI's own envelope variation before it means anything [I].

### How to validate it

The project already has the template: the DI-free study scored distances by regret and by Spearman agreement with the judge, against a song-blind baseline ([di-free-distance-plan.md](../di-free-distance-plan.md)) [V]. The extension has two parts [I].

First, read m on the **24 stored control searches** (12 cells × true DI and C′). Ask whether m > 0 predicts closing ≥ 50% of the gap, and report the 2×2 table, which needs no new renders.

Second, build a **controlled degradation ladder** of the true DI: lower crest by 0, 1.5, 3 and 5 dB; smear the envelope; add −2 and −4 dB shelves above 2 kHz and +1, +3 and +5 dB bells at 200–1000 Hz; scramble phase above 1 kHz; add bleed. Add the real rebuilds (C, C′ seeds and folds, R, L, E0, E0b, `flatref`, C′ with oracle EQ). Then compute, across the cell × variant pairs, Spearman ρ and AUC for m > 0, with the **band** as the bootstrap cluster. The 12 cells come from only 6 bands, so the intervals will be wide and must be reported as such. The within-cell Spearman across variants is the key statistic, because it asks whether a proxy orders DIs correctly for the same cell. Any composite weights get confirmed on other development cells, such as knob ceiling's realistic-control cells, never on held-out sets.

## Four local experiments, ranked

Every experiment below runs on development parts only. Each needs a committed `docs/<topic>-plan.md` and a `docs/dev-test-ledger.json` entry with its gate before any result exists, and reports band-clustered 90% intervals with leave-one-band-out checks ([ml-plan-2026-10.md](ml-plan-2026-10.md)) [V rules]. The control cells and the 5 check parts have been used before, so each plan must declare a **repeat development use** [I]. Non-commercial or unclear-licence weights (SW, FoxJoy, MDX23C De-Reverb, LOUDAR's guitar checkpoint, Sucial, anvuew) may appear only as flagged descriptive anchors and never become eligible. NC data needs the user's yes [V rule].

| Rank | Experiment | Tool to use first | Cost on one M-series Mac | Pass rule (proposal) |
|---|---|---|---|---|
| 1 | **Quick test:** swap the separator on the 5 set-3 check parts, re-measure coherence, and pair it with rank margins on known-target stem cells | `learn/separate.py` (htdemucs_6s, the control); Mega-53 `electric-guitar` via ZFTurbo's MSST `inference.py`; the fixed crossover blend; python-audio-separator for research-only anchors | About 150 renders (minutes). Separation under 1 h on CPU (10 contexts × up to 5 rows). About 2–3 h end to end | A screen, not a switch. A row advances to the merged report's switching test only if m_sep > 0 on more cells than htdemucs_6s, with no cell flipped from correct to inverted, **and** mean coherence ≥ htdemucs_6s − 0.02. Coherence alone never advances a row |
| 2 | **Validate the rank margin and test the dynamics hypothesis** with the degradation ladder on the 12 control cells | The project's `rebuilt_distance` and renderer; numpy/scipy for the ladder; dasp-pytorch (Apache-2.0) if a parametric compressor is needed | Zero renders for the m-against-search readout. About 600 renders for m (25 variants × 12 cells × 2) plus 192 shared; about 1.4k more for τ_panel on 9 cells × 10 variants. Under 30 min of rendering; about a day with code | Adopt m as the gate if m > 0 matches gap-closed ≥ 50% on ≥ 15 of the 18 informative searches. Dynamics is confirmed if the −3 dB crest rung alone inverts T on ≥ half of the informative cells while the tilt rungs invert ≤ 1. An intrinsic proxy is adopted if within-cell ρ ≥ 0.6 and its lower bound beats coherence's |
| 3 | **Fitted post-correction of C′** (static expander plus low-order tilt; an oracle-envelope transplant as the ceiling) | scipy.optimize on a numpy expander; De-limiter (MIT code and weights) fine-tuned on (C′, true DI) pairs only if the parametric fit fails | Fitting under 1 h. About 100 renders for the m pre-check. A full control re-run at about 3.6k renders (under 1 h of rendering). About half a day | m > 0 on ≥ 6 of 9 informative cells, then the plan's original control rule: ≥ 50% of the gap on two-thirds of informative cells, or mean shortfall within 0.03 of the true-DI run. Then repeated on experiment 1's stem cells |
| 4 | **Dynamics-aware retrain** (gain head, envelope and crest loss, input-scale normalisation, optional amp × gain-bucket conditioning, stems in training), only if 3 fails | The project's `learn/direc.py` trainer, with the De-limiter repo as the reference gain-head design | About 6.5 h per fold on MPS ([cprime-folds-plan.md](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/cprime-folds-plan.md#L68-L71)) [V]: one fold first for a pre-check on that fold's control cells, then about 26 h for four folds, plus the 3.6k-render control | The same control rule as 3, and it must beat the corrected C′'s m if experiment 3 passed on clean renders but failed on stems |

### 1. The cheapest quick test, made decisive by two margins

Re-measuring 1–3 kHz coherence on the 5 check parts with a different separator is cheap, but on its own it answers nothing: coherence has never been validated, and the 5-part mean is dominated by one part [I]. Two rank margins make it informative.

The setup [I]:

1. For each check part and for PR12 and SW50R (10 cells), render S with the control's five moved knobs (T) through the part's raw DI, over the 30-s context.
2. Mix that render into the session context in place of the amp track. The development contexts are already rebuilt from session tracks without vocals ([guitar-separation-2026-10.md](guitar-separation-2026-10.md)) [V].
3. Separate the mix with each row.

Then compute two margins [I]:

- **m_sep**, through the **true** measure DI and judged against each stem. This isolates the separator's own effect on the ranking.
- **m_both**, through C′'s rebuild of each stem.

Also report the stem's crest, envelope-variation and attack-slope error against the clean render, split into single-guitar and multi-guitar parts [I].

The rows are:

- htdemucs_6s (the control);
- Mega-53's `electric-guitar` head;
- the fixed crossover blend (Mega-53 below about 6 kHz, htdemucs_6s above);
- research-only anchors: SW, and htdemucs_6s followed by MDX23C De-Reverb.

The readout is a decision [I]. If m_sep > 0 on nearly every informative cell for htdemucs_6s, separation is not what breaks the objective, and the separator question waits behind the rebuild. If m_sep is often negative, even a perfect DI cannot steer through the stem. Separation then becomes a co-equal problem, and the merged report's re-test is promoted.

Expect m_both to stay mostly negative for every row, since C′ already inverts 7 of 12 cells on clean renders. A separator that "improves coherence" while m_both stays negative has not helped arm A [I]. With 5 parts from at most 5 bands, no band-clustered interval is meaningful, so the plan must declare the test a screen [I].

### 2. The ladder that tells the project what to fix

This is the highest-value experiment per hour. It decides three things at once [I]:

- whether m can replace coherence as the gate;
- whether crest loss, rather than tilt, flips the ranking (the audit's "likely" cause, never tested causally);
- whether any cheap intrinsic feature predicts m well enough to become a training loss.

Two extra rows cost no renders, because they only re-judge renders the control already made. The first is a per-frame level-normalised judge variant. The second is the embedding-guard objective, flagged research-only until a licence-clean embedding exists. Both answer the "steer without a DI" question by the same yardstick: does the objective rank T above S? [I] Add an **oracle-envelope transplant** row: C′'s output with the true DI's 5–10 ms RMS envelope imposed. If even that does not restore m > 0 on most cells, dynamics is not the main cause, and experiments 3 and 4 must target waveform detail instead [I].

### 3. Correct C′ before retraining it

Fit, per fold and leak-free (bands from the training folds only), a static expander on a short-term envelope (3–5 parameters) and a two-parameter tilt, from (C′ rebuild, true DI) development pairs. Run three ablation arms: tilt only, expander only, and both. Check each by m before spending a control re-run [I]. The first tool is a numpy expander fitted with scipy, because it is transparent and needs no training. A fine-tuned De-limiter is the off-the-shelf fallback: its SGI design is the only published method that restored crest factor ([arXiv 2308.01187](https://arxiv.org/html/2308.01187v2)) [V], but it was trained on mastering limiters, not on a network's squash [I]. A pass on clean renders must then be repeated on experiment 1's stem cells, because separation adds its own flattening [I].

### 4. Retrain only if a fixed correction cannot pass

Fixing the cause means four changes [I]:

- replace the per-crop target normalisation with the input's scale;
- add a gain head;
- add envelope and crest terms to the loss;
- train on separated stems of the project's multitracks.

Amp × gain-bucket conditioning, with random condition dropout, is a second arm. It uses the RemFX evidence that a known effect identity is worth several dB, and the evidence that a predicted label loses under 2% ([arXiv 2308.16177](https://arxiv.org/html/2308.16177)) [V]. The pre-check is m on the control cells of the one fold trained first. Only a pass justifies the other three folds. LOUDAR on the 18 development amp tracks can be added as a descriptive, NC-flagged anchor, to show whether a generative prior fixes the squash at all. It never becomes a candidate [I].

## Conclusion

The project has been treating the problem as "get a cleaner DI". The evidence reframes it as "get a DI that leaves the search objective's minimum in the right place". These are different targets. Cleaner-sounding rebuilds have already picked worse, and a codec rebuild with C′-level coherence picked like the oracle. A driven amp is a dynamics-sensitive instrument: it hears crest factor and envelope where linear metrics see almost nothing. So the measure that gates progress should be one the amp and judge define, the rank margin, and the losses should target the property the amp reacts to. The literature offers one transferable structural idea (a gain head) and several warnings, but no turnkey de-amper. The project's known-target control is already a better test bed than anything published.

Separation stays a real but secondary problem until experiment 1 shows that a perfect DI cannot steer through a stem. If it can, the right order is to fix the rebuild first and the separator second. Watch for an openly licensed SCNet-class guitar model, which had the best attack behaviour in the only transient study. Also watch for code from EG-VAE or Restore-Separate-Restore; either could change the build-versus-borrow decision for experiment 4.
