# Train C′'s successor on sub-10 ms detail

Evidence tags: **[V]** verified (a researcher opened the source and read the claim, or it is in this repo's committed code or docs); **[I]** inferred (reasoning or arithmetic from verified facts); **[U]** unverified (search snippet, memory, or a local file not in git). Links are written to work from `docs/research/`: repo docs as `../<file>.md`, code as `../../<path>`, other research docs as `<file>.md`, and branch-only files as GitHub links. Background on de-amping methods, the De-limiter gain head, DDD, RemFX, LOUDAR and EG-VAE is in [di-recovery-2026-10.md](di-recovery-2026-10.md) and is not repeated here.

**Bottom line.** Experiment 4 should keep C′'s waveform U-Net and change what it is trained against. It should not change architecture family first. The ladder already shows that the 15–20 dB-too-loud quiet passages and the slow envelope are symptoms, not the lever. A transplant of the true DI's 5–10 ms envelope sets every frame's level right, yet recovers only about 6% of C′'s rank-margin loss ([ladder results](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/rank-margin-ladder-results.md?plain=1#L41-L78)) [V]. The ladder places what is left in "waveform detail under about 10 ms" [V]. That it sits under about 5 ms, where C′'s loss sees it mainly through waveform L1, is an inference, and the exact location is unconfirmed [I]. Under timing uncertainty, L1 pulls toward a smoothed median [I]. The first arms are therefore fine-tunes of a C′ checkpoint that add, in order, spectral terms at 32–128-sample windows (which DAC credits for "very quick transients"), a phase-derivative term computed on the CPU, a peakiness term at 1–2.5 ms with a gap guard, and last a gradient-balanced MPD/MSD discriminator. C′'s output comes from one linear layer at 12 kHz with no full-rate path, so a zero-render capacity check runs first. If C′ cannot even overfit the true DI's fine structure, a zero-initialised full-rate head is tried before the loss route is called failed [I]. Everything stays MIT- or Apache-licensed and MPS-safe. A continuous DAC-latent decoder ("E1′") is the second route, opened only if a zero-training ceiling check passes. Amp conditioning and training on separated stems come after the clean-render control passes. The one-fold pre-check should use **fold 3, not fold 2**. Fold 3 holds 4 of the 9 informative control cells; fold 2 holds none (committed [`diag1.out`](../audits/song-settings-control-2026-10-15/diag1.out)) [V/I]. The gate is the full known-target control. C′ closes 3 of 9 informative cells with mean shortfall +0.320. A successor passes at **6 of 9, or a mean shortfall ≤ −0.032** [I, arithmetic from the rule]. The whole plan costs about 10.4k renders. With the ladder's 921 and the separator screen's ≈ 0.14k, the running total goes from about 131k to about **142k** of the 200k limit, plus roughly one to two days of single-job MPS time. That spends about 11.4k of the DI track's ~12k allowance, and two unbudgeted branches could pass it; the user is asked first [I].

## C′'s losses barely see detail under ~5–10 ms, and the control punishes that

### What C′ actually is

C′ is a Demucs-v2-style waveform U-Net with about 9.8M parameters ([`learn/direc.py`](../../learn/direc.py#L137-L221)) [V]:

- **Encoder:** five levels, each a stride-4 convolution with 8 taps, GELU and a GLU, at channel widths 32–512.
- **Bottleneck:** four dilated residual blocks.
- **Decoder:** transposed convolutions, with additive skips.

**No full-rate path runs from input to output.** The 48 kHz waveform is synthesised by one linear 8-tap, stride-4 transposed convolution from 32-channel features at 12 kHz. The last skip also comes from 12 kHz features; none carries the input at its own rate [V, from [the decoder code](../../learn/direc.py#L193-L219)]. So if a new loss fails to restore sample-level shape, the cause could be the loss or this output stage, and a loss test alone cannot tell which [I]. Step 0e below checks this before any loss arm is judged.

Input and target are each scaled to std 0.1 per crop, independently ([L433–434](../../learn/direc.py#L429-L436)) [V]. The loss is `100·L1 + mrstft`. The MR-STFT term uses FFT sizes 256–4096 at hop n/4; each resolution adds spectral convergence and a log-magnitude L1 with a 1e-6 floor ([L336–353](../../learn/direc.py#L336-L353)) [V]. The shortest window is 256 samples, 5.3 ms at 48 kHz, at hop 64 (1.3 ms). Its overlapping frames do partly see where energy sits under 5 ms, but each frame smears it over 5.3 ms. **No spectral term resolves energy placement finely below about 5 ms, and none sees phase** [I].

The training data needs one correction to the experiment framing. C′'s pairs are 48,806 plugin renders: PR12 18,843, SW50R 14,965, AC20 14,998. They are **6-s clips trained as random 3-s crops** (`CLIP = 6·SR`, `CROP = 3·SR`), not 10-s pairs [V]. Arm B's bank renders, by contrast, are 10 s long.

A fold trains in **about 6.5 h** at 1.19–1.27 steps/s on MPS, with the spectral loss on the CPU ([cprime-folds-plan.md](../cprime-folds-plan.md), lines 66–71) [V]. The schedule is 28,250 steps at batch 12: 5,150 steps at 3e-4, then cosine decay to 2e-5.

Earlier repairs of this exact network all failed or were marginal ([v2](../di-network-v2-results.md), [v3](../di-network-v3-plan.md), [residual](../residual-di-results.md), [loss pilot](../di-loss-plan.md)) [V]:

| Repair | Result |
|---|---|
| Opening the dead bottom | Training "learns to ignore it" |
| Identity FIR pass-through (R) | Kept the amp's distortion and brightness |
| Linear-only network (L) | Bad picks |
| SI-SDR on the CPU | 1–3 kHz coherence stayed at 0.170, against 0.169 for the default loss |

Experiment 4 should not retry these.

### What the ladder says the error is, and is not

The rank-margin ladder (commit 4069de2) is decisive about what does *not* matter ([ladder results](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/rank-margin-ladder-results.md?plain=1#L20-L78)) [V]:

- **Static compression:** a compressor that cuts the true DI's crest by 3 dB inverts only 1 of 7 cells.
- **Tone balance:** C′'s long-term spectrum inverts 1 of 9.
- **C′'s envelope:** imposed on the true DI, it inverts 0 of 9.
- **Oracle envelope transplant:** giving C′ the true DI's 5- or 10-ms envelope lifts the mean margin only from 0.053 to 0.060–0.064, against 0.244 for the true DI.
- **Expander:** an oracle-fitted static expander stays at 5 of 9.

The audit locates the loss in two places [V]. "C′'s crest loss is fast: 3.6–5.5 dB, mostly at timescales under 10 ms." And "C′'s quiet passages are 15–20 dB too loud."

Two inferences follow, and they shape everything below [I]. First, **a 10-ms envelope transplant already fixes the quiet-frame levels and still recovers almost nothing**. A loss that only prices gap level or slow envelope is a guard against regression, not the fix. Second, **the 10-ms compressor cut crest without changing waveform shape and barely moved the ranking**. So crest as a single number is not what the amp responds to. The likeliest lever is fine structure under about 5–10 ms: pick-attack sharpness, pitch-period peakiness, and the harmonic phase relations that set where peaks land.

That second inference has a limit [I]. The ladder's rungs fix only static EQ and the broadband envelope. They do not rule out a spectral balance that changes over time, frame by frame. An optional rung can separate the two (about 18–36 renders, step 0b): render S and T through C′'s rebuild with the true DI's STFT magnitude and C′'s phase, and the reverse. If the true magnitude with C′'s phase restores the margin, the error is magnitude over time. If C′'s magnitude with the true phase restores it, the error is phase and fine shape.

The ladder plan flagged one bias. Envelope transplants add sidebands, which pushes D2 toward "doesn't restore" ([plan](../rank-margin-ladder-plan.md), lines 313–314) [V]. The 50-ms transplant gave the same answer as the 5- and 10-ms ones, which weakens that objection [V/I].

This matches the project's older findings. Coherence analysis found that "the network does not invert the amp. It produces a DI with a plausible spectrum whose waveform detail has drifted" ([sim-real-gap-results.md](../sim-real-gap-results.md)) [V]. The gap split put 87% of the rebuilt-to-oracle gap in "the rest", beyond level and balance ([set3-gap-split-results.md](../set3-gap-split-results.md)) [V].

### The gate, quoted exactly

The ladder results end with this: "The gate for any rebuild is the full known-target control, not the margin. A rebuild must close at least half the gap on two-thirds of the informative cells" ([L87–88](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/rank-margin-ladder-results.md?plain=1#L87-L88)) [V]. The margin itself agrees with search success on 14 of 18 searches, and on only 5 of 9 within the C′ run. The doc says: "Don't use it to pass or stop a rebuild: only the full known-target control can" ([L11–19](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/rank-margin-ladder-results.md?plain=1#L11-L19)) [V].

The control's rule ([song-settings-plan.md](../song-settings-plan.md), lines 104–119) [V] uses 12 cells: 6 bands drawn with `random.Random(20261016)`, one part per band, × PR12 and SW50R. Each cell's "recording" is S with five settings moved, played through the part's raw DI. Two runs of 150 renders each are scored on the held half. The rows are read in order, and the first match wins:

> 1. The measure-DI run closes ≥ 50% of the gap on fewer than 8 of 12: the set-up is wrong. Stop arms A and C.
> 2. The rebuilt run closes ≥ 50% on ≥ 8 of 12, or its mean shortfall is within 0.03 of the measure-DI run's: the control passes.
> 3. Otherwise: arms A and C count as failed.

Amendment 2 (lines 312–322) [V] makes a cell informative only if d_S − d_target ≥ 0.1 on the held half. With at least 6 informative cells, "8 of 12" reads as "at least two-thirds of the informative cells". The readout code adds two readings ([branch lines 402–415](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/song-settings-plan.md?plain=1#L402-L415)) [V]:

- the mean shortfall is taken over informative cells;
- "within 0.03" is one-sided;
- "at least 2/3" is inclusive.

On the recorded control, 9 of 12 cells are informative. The measure-DI run closes 9 of 9 with mean shortfall −0.062. C′ closes 3 of 9 with +0.320. A successor therefore passes with **≥ 6 of 9, or a mean shortfall ≤ −0.032** [I].

### The cells sit unevenly across folds

The fold map is committed: C′'s fold for each cell is in [`diag1.out`](../audits/song-settings-control-2026-10-15/diag1.out) and [`song-settings-folds.json`](../song-settings-folds.json). The three uninformative cells are listed in the ladder plan (lines 62–65). This resolves a gap the brief left open [V].

| Fold | Cells (part × amp) | Informative | True-DI crest → C′ crest, dB ([diag4](../audits/song-settings-control-2026-10-15/diag4.out)) |
|---|---|---|---|
| 0 | Passing Ships × 2 | 2 | 8.9 → 11.1 / 10.8 (C′ *raises* crest) |
| 1 | Blind Spots × 2, colour-me-red × 2 | 3 (Blind Spots PR12 is not) | 14.7 → 11.0 / 10.9; 15.9 → 11.1 / 10.7 |
| 2 | Today's The Day × 2 | **0** | 16.8 → 11.6 / 11.2 |
| 3 | Prodigal × 2, just-don't-talk × 2 | **4** | 13.9 → 10.0 / 9.8; 13.9 → 13.6 / 13.8 |

**Fold 3 is the natural pre-check fold** [I]. It holds the most informative cells, from two bands and two DIs. It includes one part where C′ loses 4 dB of crest (Prodigal) and one where crest is intact but the ranking still fails (just-don't-talk). That makes it a good test of "shape, not crest".

Fold 2 is the fold with extra C′ seeds, but it cannot pre-check anything: both of its cells are uninformative ([ladder plan](../rank-margin-ladder-plan.md), lines 147–152) [V]. From the committed [`diag3.json`](../audits/song-settings-control-2026-10-15/diag3.json), at lag 0 on the search half, C′ ranks the target above S on only 1 of the 4 informative fold-3 cells (Prodigal PR12, m = +0.116) [I, my arithmetic]. Which cells C′'s search actually closed is in the local `result.json` only.

## Keep the waveform U-Net; the alternatives buy representation, not detail

The literature's clearest statement of C′'s failure comes from StoRM. A regression to the posterior mean E[x|y] "will smooth out these details", removing "fine-grained detail corresponding to quiet regions ... and onsets or offsets" ([StoRM](https://arxiv.org/html/2212.11851)) [V]. That is an objective problem, not a representation problem [I]. C′ already outputs a waveform, so it already models phase. Switching to complex masks or a hybrid spectrogram network changes the representation but keeps the regression objective. **No paper found shows a representation switch restoring crest or transients** [V by absence]. Almost no restoration paper reports a transient metric at all.

One caveat about keeping C′ as it is [I]. Its output is a single linear layer from 12 kHz features, with no input-rate skip (see above). That may limit how sharp an attack it can draw, whatever the loss. Step 0e tests this for zero renders: overfit a few training crops with the new losses and see whether 1-ms crest and peakiness reach the true DI's. If they cannot, add a contingent arm before calling the loss route failed: a zero-initialised full-rate refinement head, or an input-rate skip into the last stage. Zero initialisation means the fine-tuned model starts out identical to C′. This is a small addition to the U-Net, not a change of family.

The exceptions are few. CQT-Diff's onset F1 rose from 0.67 to 0.79–0.80 in piano bandwidth extension ([arXiv 2210.15228](https://arxiv.org/html/2210.15228)) [V]. The De-limiter crest result is covered in the earlier report.

The table below weighs each family against what this project needs. The MPS column uses the project's own measurements [V]:

- `torch.stft`'s gradient is wrong above 65,536 samples, and crops are 144,000;
- complex `abs` has a NaN gradient;
- complex-STFT losses go non-finite after one update;
- unfolded-frame matmul is wrong even in the forward pass.

Demucs's own maintained code moves STFT and iSTFT to the CPU on MPS ([spec.py](https://raw.githubusercontent.com/adefossez/demucs/main/demucs/spec.py)) [V].

| Family (example) | Phase | Transient / crest evidence | Code / weights licence | MPS at C′ scale (49k pairs, ~6.5 h/fold) | Verdict |
|---|---|---|---|---|---|
| Waveform U-Net (C′, Demucs v2, Wave-U-Net) | Waveform | Demucs v2 was built to fix "hollow instruments attacks" but rated them by MOS only ([1911.13254](https://arxiv.org/html/1911.13254)) [V] | MIT ([Demucs](https://raw.githubusercontent.com/facebookresearch/demucs/main/LICENSE), [Wave-U-Net](https://raw.githubusercontent.com/f90/Wave-U-Net/master/LICENSE)) [V] | Proven: C′ itself [V] | **Keep as the backbone** |
| Hybrid waveform+spectral (HTDemucs) | Both | Spectral "phase inconsistency ... will make the attack sounds hollow" (motivation only) ([2111.03600](https://arxiv.org/html/2111.03600)) [V] | MIT [V] | STFT/iSTFT inside the net, so a CPU round-trip; attention on MPS untested [I] | No transient gain shown; skip |
| Complex mask / band-split (DCCRN, FRCRN, BS-RoFormer, TF-GridNet) | Complex | None reported; all speech or separation metrics [V] | Apache-2.0 / MIT [V] | CPU STFT in forward and backward; BS-RoFormer trained 4 weeks on 16 A100s ([2309.02612](https://arxiv.org/html/2309.02612)) [V] | Skip |
| Apollo (band-split restoration) | Complex output, magnitude-only reconstruction loss | None; it scored worse than the distorted input on LOUDAR's de-amping test (earlier report) [V-prior] | CC BY-SA 4.0, open but share-alike ([LICENSE](https://raw.githubusercontent.com/JusperLee/Apollo/main/LICENSE)) [V] | MPS inference documented, training not ([MACOS_ARM64.md](https://raw.githubusercontent.com/JusperLee/Apollo/main/MACOS_ARM64.md)) [V] | Skip |
| Vocoder head (HiFi-GAN, BigVGAN, Vocos) | Waveform from mel, or iSTFT | Vocos: time resolution "dictated by the hop size" ([2306.00814](https://arxiv.org/html/2306.00814)) [V]; no pre-echo study found [V by absence] | MIT code and weights [V] | HiFi-GAN-type convolutions are MPS-safe; BigVGAN trained 5M steps ([2206.04658](https://arxiv.org/html/2206.04658)) [V] | Borrow the **discriminators**, not the generator |
| Codec latent: DAC | Through the decoder, 86 Hz frames | Music SI-SDR 11.30 against Stable Audio Open's 6.28 ([2407.14358](https://arxiv.org/html/2407.14358)) [V]; project E0b keeps oracle-level picks [V] | MIT code and weights ([README](https://raw.githubusercontent.com/descriptinc/descript-audio-codec/main/README.md)) [V] | Real-valued convolutions; encoding all pairs took ~12 h on MPS; decoder-in-loop training unmeasured [V/I] | **Second route ("E1′")** after a ceiling check |
| Codec latent: Stable Audio VAE, Music2Latent | Through the decoder, 21.5 Hz or less | SI-SDR 6.28 and −3.85 on music ([2408.06500](https://arxiv.org/html/2408.06500)) [V] | Non-OSI community licence; **CC BY-NC** weights [V] | — | Out: fidelity and licence |
| Diffusion / bridge (CQT-Diff, StoRM, A2SB, FlowSE) | Waveform or complex | CQT-Diff onset F1 0.67 → 0.80 (bandwidth extension, not inversion) [V] | CQT-Diff and StoRM MIT; **A2SB NC**; FlowSE repos have no licence file [V] | Days of A100 time; 35–300 sampling steps [V] | Research anchor only (A2SB and FlowSE flagged) |

### A gain or envelope head no longer fits the evidence

The earlier report's strongest structural lead was the De-limiter's sample-wise gain head. That head multiplies its *input*. Here the input is the amp's distorted waveform, and R showed that passing it through carries the distortion (+3.1 dB at 3–8 kHz) ([residual-di-results.md](../residual-di-results.md)) [V]. Applied to C′'s own output instead, a gain head is a learned envelope. The ladder's oracle envelope transplants bound that at about 6% [I].

**Drop the gain head from experiment 4's first arms.** Keep the earlier report's input-scale normalisation idea as a later single-variable ablation, not a first change. The ladder's oracle expander says absolute level is not the lever [I].

### The latent route has real support, with one cheap check before any training

DAC is the one codec-latent option that keeps waveform detail. It is also the only one with project evidence. The 4-codebook round trip (E0b) matches C′'s 1–3 kHz coherence (0.20) yet keeps oracle-level picks: −0.126 against the oracle's −0.131 and C′'s −0.099 ([egvae-lite-plan](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/egvae-lite/docs/egvae-lite-plan.md?plain=1#L246-L275)) [V]. Whatever the picker needs survives DAC's decoder. That plausibly means fine-structure *statistics* rather than an exact waveform [I].

Predicting discrete codes failed, at mel 3.44, worse than the unprocessed recording's 3.10. The reason is that an 8-sample delay keeps only 33% of codebook-1 codes ([E1 results](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/egvae-lite/docs/egvae-e1-results.md?plain=1#L45-L70)) [V]. The documented repair is to predict DAC's continuous latent and train through the frozen decoder with a timing-tolerant loss, on the CPU. Plain L1 on latents is expected to land near C′ (about 2.0–2.2 mel, against C′'s 2.29) [V]. The "continuous beats discrete" result supports the repair: OVRL 3.25 against 2.89, but on speech, with no waveform metrics ([2510.26299](https://arxiv.org/html/2510.26299)) [V].

The notes disagree on which latent to predict. The project's own review warns that "DAC's pre-quantisation latent is not what the decoder uses" ([egvae-lite-plan L210–212](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/egvae-lite/docs/egvae-lite-plan.md?plain=1#L210-L212)) [V]. **Predict the post-quantisation continuous `z` the decoder consumes** [I].

Before any training, run a zero-training **DAC ceiling check** on the 12 control cells' measure DIs:

1. Round-trip each measure DI through DAC with 4 and 9 codebooks.
2. Measure crest at 1, 5 and 10 ms frames and the quiet-frame level against the true DI. These were never measured for E0 or E0b.
3. Measure the shift stability of `z` under 1–8-sample delays.
4. Read the rank margin descriptively. That costs 24–48 renders [I].

If DAC(true DI) cannot hold the true DI's margins on the fold-3 cells, no latent predictor can, and the route closes cheaply.

## Losses: resolve 1 ms, price the gaps, then add a balanced discriminator

Three things in the literature bear on transients, though no paper measures crest or pre-echo directly.

First, **very short windows**. DAC's multi-scale mel loss runs from 32-sample windows (hop 8) to 2048. Its authors write that "using the lowest hop size of 8 improves modeling of very quick transients" ([arXiv 2306.06546](https://arxiv.org/html/2306.06546), [base.yml](https://raw.githubusercontent.com/descriptinc/descript-audio-codec/main/conf/base.yml)) [V]. EnCodec's mel loss also spans 32–2048-sample windows ([2210.13438](https://arxiv.org/html/2210.13438)) [V].

Second, **phase-aware terms help even when phase is not the target**:

- Braun and Tashev: "combining magnitude-only with phase-aware objectives always leads to improvements", and compressed magnitudes add more ([2009.12286](https://arxiv.org/html/2009.12286v1)) [V].
- MP-SENet: PESQ falls from 3.50 to 3.39 without its anti-wrapping phase loss ([2305.13686](https://arxiv.org/html/2305.13686)) [V].
- SAME: a phasor-cosine phase term, motivated by "phase coherence is critical for transient fidelity", with no ablation ([2605.18613](https://arxiv.org/pdf/2605.18613)) [V].

Third, **adversarial losses are what remove over-smoothing**:

- DAC without its adversarial losses: SI-SDR falls from 9.12 to 1.07, with "many artifacts, including buzzing, as it has not learned to reconstruct phase" [V].
- HiFi-GAN without its MPD: MOS falls from 4.10 to 2.28 ([2010.05646](https://arxiv.org/html/2010.05646)) [V].
- DDD (earlier report): a GAN restored waveform "ruggedness", 1.17M → 1.67M local extrema, against 1.52M in clean audio [V-prior].

### The noise-floor analysis inverts the obvious story

A natural guess is that C′'s log-magnitude term under-weights quiet passages. The literature says the opposite. A log-magnitude L1 with a small ε **over-weights** quiet bins in gradient terms. SAME: "Small ϵ … produces very large gradients 1/(x + ϵ) at low-amplitude bins" ([2605.18613](https://arxiv.org/pdf/2605.18613)) [V]. Braun and Tashev: LSD has "large errors also at low energy bins" [V].

The **linear** terms are what under-weight gaps [I]:

- **Waveform L1:** with the target at std 0.1, a −40 dB passage contributes about 1% as much per sample as a note.
- **Spectral convergence:** a norm ratio dominated by loud bins.

C′'s log floor of 1e-6 against a std of 0.1 is already about −100 dB re the crop. So "add a floor" is close to the status quo [I, from the code]. **Do not adopt SAME's σ-adaptive knee for this purpose.** By its own description it linearises bins below the crop's std, which would make filling gaps cheaper [I].

The notes offer two mechanisms for the over-fill, and both are untested [I]:

- **A global error floor:** the network's residual sits at a fixed level below the crop RMS and spreads into gaps.
- **Amp pass-through:** U-Net skips leak the amp output's hiss and compressed sustain.

The test needs zero renders. Compare C′'s gap spectra, from the stored `<cell>-rebuilt.npy`, against the fake recording's gaps and the true DI's gaps. A high correlation with the recording means pass-through; flat broadband excess means an error floor.

Either way, the ladder says fixing gap level alone recovers little. The gap term below is a **guard**, weighted modestly, not the main lever [I].

### The proposed loss stack, in the order to add it

| Term | Definition (proposed) | Literature effect on transients | Device | Status |
|---|---|---|---|---|
| Keep C′'s loss | `100·L1 + mrstft` (256–4096) | Baseline | MPS + CPU STFT | [V] |
| Short-window MR-STFT | Add FFT 32/64/128, hop n/4, log + linear magnitude | DAC: hop 8 "improves ... very quick transients"; multi-scale against single-scale mel SI-SDR 9.12 against 7.68 [V] | CPU (STFT); about +60% STFT work, since each resolution has ≈ 290k bins per crop [I] | Proposed |
| Phase-derivative | IF/GD as SAME-style phasor cosine, magnitude-weighted, at 256/512/1024, weight ≈ 0.3 × magnitude terms (MP-SENet ratio) | MP-SENet −0.11 PESQ without; "Back to Ear" ties transients to IF/GD (qualitative) ([2509.14912](https://arxiv.org/html/2509.14912)) [V] | **CPU only** (complex autograd non-finite on MPS) [V] | Proposed. A new term, not a retry: the [loss pilot](../di-loss-plan.md)'s complex-STFT term went non-finite on MPS and never trained; the pilot ran SI-SDR instead [V] |
| Peakiness | L1 on local crest, max − mean in dB, over 1 and 2.5 ms frames | No paper tests a crest **loss** for restoration [V by absence] | MPS (no STFT) | Proposed [I] |
| Gap guard | relu(pred_dB − target_dB) on frames > 35 dB under the crop's peak frame, floor −90 dB | Speech enhancement splits noise-only terms to stop loud frames dominating ([2001.10601](https://arxiv.org/abs/2001.10601)) [V, abstract] | MPS | Proposed [I] |
| Adversarial | MPD (periods 2/3/5/7/11) + MSD, LSGAN + feature matching, after warm start | HiFi-GAN, DAC and DDD above [V] | MPS-safe (waveform convolutions); a complex MS-STFT discriminator would be CPU-bound | Last |

Two numbers govern how the adversarial step is run.

**Balancing.** EnCodec normalises each loss's gradient by an EMA of its norm. With weights (1, 2, 100, 1), its balancer gives SI-SNR 8.41, against **−35.83 without it** ([2210.13438](https://arxiv.org/html/2210.13438)) [V]. C′'s `100·L1` is exactly that kind of lopsided weight [I].

**Warm start.** MSR trained L1 for 50k steps, then added λ_g 0.001 and λ_fm 0.01 ([2505.21827](https://arxiv.org/html/2505.21827v1)) [V-prior]. MSG instead solved for weights that equalise the terms over the first 1k iterations ([2208.12387](https://arxiv.org/pdf/2208.12387)) [V]. A C′ checkpoint is the natural warm start [I].

The known risk is an invented top octave that reads as fizz after a driven amp. Spectrum matching that boosted 3–10 kHz by 3–7 dB hurt picks on high-gain and crunch ([set3-gap-split-results.md](../set3-gap-split-results.md)) [V]. **Check each adversarial arm's 3–8 kHz level against C′'s +0.6 dB before spending control renders** [I].

The torch.stft bug is the binding constraint [V]. Every new spectral and phase term must run on the CPU, as `mrstft` does, with a CPU-against-MPS gradient check at crop length before training and after 200 steps (the EG-VAE plan's check). Splitting the loss into sub-65,536-sample segments so the STFT could stay on MPS is untested [U]. Only a gradient check could clear it.

## Amp labels and separated stems belong to the second stage

### Conditioning: use it late in the network and gate it on crest

For forward effect models, FiLM beats concatenation by large margins ([SMC 2024](https://smcnetwork.org/smc2024/papers/SMC2024_paper_id83.pdf)) [V]:

- compressor ESR: 0.298 → 0.072;
- overdrive ESR: 0.459 → 0.110 (FiLM at the end of the network);
- placement: for the compressor, FiLM at the end of the network worked best; for overdrive the best was FiLM-GCU placed early ("pre", 0.105), a near-tie with the end ("post", 0.110).

On convolutional backbones, FiLM's effect on the metrics experiment 4 targets is **mixed** ([Hyper-RNN, 2408.04829](https://arxiv.org/html/2408.04829v1)) [V]:

- **OD-3:** FiLM worsened the TCN's transient error (27.6 → 33.7) and the GCN's crest error (0.78 → 1.20), but improved the TCN's crest error (1.18 → 0.89).
- **LA-2A:** FiLM improved the TCN's transient error (31.5 → 30.8) and the GCN's crest error (2.28 → 2.11).

So conditioning can help or hurt crest and transients, and a conditioned model must be gated on those metrics [I]. For inversion, RemFX is still the only label-conditioning evidence (earlier report) [V-prior]. No audio-effect paper tests robustness to an estimated condition [V by absence].

The closest precedent for training on estimated conditions is HiFi-GAN fine-tuned on Tacotron-2's predicted mels: MOS rose from 3.91 to 4.18 [V].

The project's situation makes amp identity cheap [I]. In the control and in arm A, the search runs per amp, so the amp is known. One rebuild per amp (PR12, SW50R, AC20) costs three CPU inferences, not one per candidate. Gain is not known and must be estimated. If conditioning is tried, the design is:

- **Placement:** FiLM on amp identity in the decoder's last blocks.
- **Gain:** fed through a learned "unknown" token for 10–20% of examples.
- **Reporting:** oracle, predicted and unknown conditions.
- **Gate:** the fold-3 crest and peakiness metrics, given Hyper-RNN's mixed result.

This is a stage-2 arm. It adds a variable without addressing the fine-structure objective.

### Stem training: modest gains in the literature, and the bank needs one code change

Two published systems train a restorer on separator outputs:

- **Restore-Separate-Restore:** stem experts on BS-RoFormer outputs moved guitar MMSNR only from 3.045 to 3.070 ([2610.08284](https://arxiv.org/html/2610.08284v1)) [V]. It has no licence or weights yet.
- **MSG:** a HiFi-GAN-style post-processor was preferred in 11 of 15 separator × stem tests and raised bass onset F1 from 0.36 to 0.52 ([2208.12387](https://arxiv.org/pdf/2208.12387)) [V]. It notes that separators "tend to smooth out transients" [V].

Neither targets a DI. Both support separator-output training as a **fine-tune**, with small objective gains. The project has something neither had: the exact dry target [I].

The arm B bank is closer to ready than the brief assumed [V, from code]:

- `song_bank.render` stores each **pre-mix isolated render** as a 16-bit FLAC, peak-normalised, with the peak and settings in a JSON ([`song_bank.py`](../../learn/song_bank.py#L300-L333)).
- Each example's DI window (path and start) is in `examples.json`, so the measure DI can be rebuilt with `load_window` and `measure`.
- `song_aug.build` mixes and separates, but **saves only float16 log-mel features**, not the stem waveform ([`song_aug.py`](../../learn/song_aug.py#L1-L21), line 205).

**So (stem → DI) waveform pairs need a small change that writes the separated stem to FLAC** [I]. Re-separating afterwards is costly. The label table timed htdemucs_6s at 20–28 s per item on the CPU ([label-table-results.md](../label-table-results.md)) [V], so 5k bank stems would take roughly 28–39 CPU hours [I].

If arm B's `build` has not finished, saving the stem waveforms during that run is nearly free. The ML session should ask before that run ends.

Two more details from the code [V/I]:

- **Target balance:** the bank's `measure` uses `average-fold2.npy`, while C′'s fold f trains to `average-fold{f}.npy`. Reconcile the targets before mixing bank pairs into a fold's training.
- **Fold rules:** for fold f, use only examples tagged with other folds. Guitar-TECHS P1 and P2 may train every fold.

The 59 development parts with real htdemucs_6s stems are too few to train on. They are the right **validation** set for the stem stage under fold rules [I].

Before building any stem pairs, measure the separator's share of the error. Run C′ on separated bank examples twice, from the pre-mix render and from the stem, and compare both against the measure DI on the fine-structure metrics. This costs zero renders [I]. If the stem adds little beyond the render's own error, stem training stays a low-priority fine-tune. If it adds a lot, use a roughly 50/50 mix of stem and clean pairs. No source tests that ratio [V by absence].

## Score-side fixes are diagnostics that run in parallel, not substitutes

The scoring notes offer three concrete new ideas. All three must still pass through the known-target control, because each changes the search objective.

**The diagnostic comes first (48 renders, D0)** [I]. Render S and T through C′ and through the measure DI on the 12 cells, and **save the renders this time**. The ladder kept scores only ([`rank_margin.py`](../../learn/rank_margin.py#L796-L812)) [V]. Then:

1. Split each frame's judge error into attack (≤ 50 ms after an onset), sustain, and quiet (record frame ≥ 20 dB below its peak).
2. In the same pass, read the ladder's phase-scramble > 1 kHz rung from the local `report.json`.
3. Optionally, add the swap rung described earlier (true DI's STFT magnitude with C′'s phase, and the reverse; about 18–36 renders).

The phase-scramble result decides two questions [I]. If scrambling phase above 1 kHz on the true DI inverts many cells, the error lives in harmonic phase in every frame. Then masking cannot help, and experiment 4's phase-derivative and MPD terms move to the front. If it inverts none, phase above 1 kHz is not the lever, and the short-window and peakiness terms lead.

The three ideas, after D0 [I unless tagged]:

| Idea | What it does | Renders for the 12-cell screen | Main risk |
|---|---|---|---|
| C′-invariant judge | Fit nuisance directions from Δ = L(A_θ x̂) − L(A_θ x) and signal directions from different θ on the same DI. Score in the generalised-eigen (NAP- or LDA-style) space. Analogues: NAP ([MIT LL](https://www.ll.mit.edu/r-d/publications/nuisance-attribute-projection)) and robust statistics for misspecified simulation ([2305.15871](https://arxiv.org/abs/2305.15871)) [V, abstract]. | 0 beyond D0, plus a ~1.2k-render development panel from bands outside the 6 control bands | The dirt C′ adds lies along the same directions that gain moves |
| Matched-degradation extrapolation | Render r₁ = A_θ(x̂), rebuild x̂₂ = C(r₁), render r₂ = A_θ(x̂₂). Score 2·L(r₁) − L(r₂), or d(y, r₁) − d(r₁, r₂). Analogues: Noisier2Noise ([1910.11908](https://ar5iv.labs.arxiv.org/html/1910.11908)) [V] and zero-noise extrapolation ([1612.02058](https://arxiv.org/pdf/1612.02058)) [V, abstract]. | +24 renders, +24 CPU rebuilds | C′ near-idempotent (r₂ ≈ r₁), or an error that is a contraction rather than additive noise. Check idempotence first with `crest_db` and `envelope` on x̂₂ against x̂ |
| Quiet and attack masks | Use the record as the judge's mask with `di_floor_db` 15 or 20 and `tail_s` 0; drop frames 30–80 ms after onsets. In the ladder the 40-dB mask never excluded a frame ([L24–25](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/rank-margin-ladder-results.md?plain=1#L22-L25)) [V]. | 0 beyond D0 | Attacks carry drive cues; window refusals on sparse parts |

Each idea needs the same guards [I]:

- **Screen:** recover ≥ 50% of the C′-to-true-DI margin gap (mean m ≥ 0.15, positive on ≥ 7 of 9).
- **True-DI guard:** keep the true DI at 9 of 9 with a mean ≥ 0.2, so a judge cannot win by going blind.
- **No tuning on control bands:** fit nothing on the control bands.

A survivor's control needs only the rebuilt run, about 1.8k renders. The measure-DI run's objective is unchanged, and the found settings are still scored through the measure DI with the original judge ([song-settings-plan.md](../song-settings-plan.md), lines 100–113) [V/I].

These are a hedge. If experiment 4's rebuild passes, the judge needs no change.

## A ranked, costed plan: fold 3 first, four folds only on a pre-check pass

Before running anything, commit `docs/di-fine-structure-plan.md` and a dev-ledger entry with the arms, rules and render bounds. The rest follows the project's rules [V]:

- development data only;
- sets 4, 5 and 6 and Guitar-TECHS P3 untouched;
- band-clustered statistics;
- one MPS job at a time;
- spectral and complex losses on the CPU;
- 30 GB kept free ([ml-plan-2026-10.md](ml-plan-2026-10.md), lines 477–505).

The 12 cells' use is their **third** ([ladder plan](../rank-margin-ladder-plan.md), lines 247–249) [V], or later for colour-me-red and just-don't-talk: the separator screen uses those parts after the ladder ([plan](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/separator-screen-plan.md?plain=1#L207-L209); ledger `repeat_use` in commit cc4bd87) [V]. Experiment 4 touches the cells several times: D0 and the optional swap rung, the DAC check, step 2 and step 4. Each use is declared [I]. The plan should name the weakness plainly: 9 informative cells from 5 DIs and 6 bands [V]. Every fine-tune starts from the same fold's C′ checkpoint, so it trains on the same pool and stays leak-free. Every new checkpoint is rebuilt with lag 0, re-equalised to fold 2's balance, and lag-checked to ±3 samples against the raw DI. The C′ 1-h checkpoint failed that check on 7 cells ([ladder results L100–101](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/rank-margin-ladder-results.md?plain=1#L97-L101)) [V].

| # | Step | Renders | Machine time (estimates [I] unless noted) | Decides |
|---|---|---|---|---|
| 0a | Zero-cost reads: phase-scramble and bleed rungs from `report.json`; C′'s `gate_open` on each fold checkpoint ([`direc.py` L305](../../learn/direc.py#L305-L310)); per-cell fold-3 results from `result.json`; gap-spectrum test; free disk | 0 | < 1 h CPU | Order of arms 1b/1c; the fold-3 bar |
| 0b | D0 diagnostic (save renders) + C′ idempotence; optional swap rung (true DI's STFT magnitude with C′'s phase, and the reverse) | 48 + 24, + 18–36 for the swap rung | < 1 h | Whether masking or extrapolation is worth a screen; whether the error is magnitude over time or phase and fine shape |
| 0c | DAC ceiling check on the 12 measure DIs | 24–48 | < 1 h MPS | Whether E1′ is opened |
| 0d | Implement the loss terms; 200-step timing and CPU-against-MPS gradient check per arm | 0 | ~1 h | Real step times |
| 0e | Capacity check: from `models-cprime-f3`, overfit a few fold-3 training crops with the new losses; compare 1-ms crest and peakiness with the true DI's | 0 | ~1 h | Whether C′'s output stage can draw the detail at all; if not, arm 1e joins before any loss arm is called failed |
| 1a | Fold-3 fine-tune from `models-cprime-f3`, 5,150 steps: + short windows + peakiness + gap guard | 0 | ~1.5–2 h MPS + CPU STFT | — |
| 1b | 1a + phase-derivative (CPU) | 0 | ~2–3 h | — |
| 1c | Best of 1a/1b + MPD/MSD, balancer, warm start | 0 | ~3–5 h (step time 2–3× is unmeasured [U]) | — |
| 1e | Contingent on 0e failing: best loss recipe + a zero-initialised full-rate refinement head (or an input-rate skip into the last stage), so the model starts identical to C′ | 0 | ~2–3 h | Whether the loss route failed or the output stage did |
| 1d | Per arm, in-training gates on the held fold: crest at 1/5/10 ms within 2 dB of the DI (C′ is 3.6–5.5 low); gap level within 6 dB (C′ is 15–20 over); validation and 1–3 kHz coherence not below C′'s noise; 3–8 kHz not above C′ by > 2 dB | 0 | minutes | Which arms earn renders (sanity only; never a pass) |
| 2 | **Fold-3 pre-check:** rebuilt run of the known-target control on fold 3's 4 informative cells, reusing the stored measure-DI run | ~0.6k per arm, ≤ 1.8k | ~5 min of rendering per arm at the project's ~2 renders/s (≈ 7.2k/h) [V, [song-settings-plan.md](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/song-settings-plan.md?plain=1#L265-L266)], plus rebuilds: under 1 h | **Rule (proposed): go to four folds if ≥ 3 of 4 close ≥ 50%, or the fold-3 mean shortfall is ≤ the measure-DI run's fold-3 mean + 0.03.** Stop if no better than C′'s own fold-3 count. Otherwise add fold 1 (3 informative cells) before deciding |
| 3 | Fine-tune the winning recipe on folds 0, 1, 2 | 0 | ~6–15 h MPS (three folds × 2–5 h) | — |
| 4 | **Full known-target control** (rebuilt run, 12 cells) | ~1.8k | ~15 min of rendering, under 1 h with rebuilds | **Pass (proposed): ≥ 6 of 9 informative cells close ≥ 50%, or mean shortfall ≤ −0.032 (one-sided). Report per band and leave-one-band-out** |
| 5 | Confirmation on a fresh 12-cell development draw from other bands (both runs, declared before reading) | ~3.6k | ~30 min of rendering, about 1 h with rebuilds | **Pass (proposed): the control's own rule on the new draw.** The measure-DI run must first close ≥ 50% on at least two-thirds of the informative cells; the rebuilt run then passes with ≥ 50% closed on at least two-thirds of them, or a mean shortfall within 0.03 of the measure-DI run's (one-sided). Guards against a repeat-use fit before arm A re-runs |
| 6 | Stem stage: save bank stems, separator-share test, stem fine-tune, validation on the 59 real stems, then arm A on stems as the ML plan declares | 0 new plugin renders (+ arm A's own) | 28–39 h CPU only if re-separating [I] | Whether stems are needed |
| S | Scoring hedge in parallel: C′-invariant judge panel, then its control if the screen passes | 1.2k + 1.8k | ~25 min of rendering, about 1 h with rebuilds | Alternate route to arm A |
| Not budgeted | Step 2's "add fold 1": 3 cells × 150 renders per arm, up to 3 arms | ≤ 1.35k | under 1 h | Only if step 2 is inconclusive; ask the user first if it would pass the DI-track allowance |
| Not budgeted | A second scoring-hedge control (a second surviving idea) | +1.8k | under 1 h | Same: ask the user first |

**Renders.** The running total is about 131k at the end of step 3. The declared bound with the ladder is 139k, and the DI track was allowed up to about 12k more ([ROADMAP.md](../ROADMAP.md), lines 150–152) [V]. The DI track has already spent the ladder's 921 renders (840 + 81 audit) and the separator screen's ≈ 0.14k ([ladder results](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/rank-margin-ladder-results.md?plain=1#L5); [separator-screen-plan.md](https://github.com/YoavBZ/neuraldsp-preset-generator/blob/ml/cprime-folds/docs/separator-screen-plan.md?plain=1#L283)) [V]. Experiment 4 at its budgeted maximum is about 48 + 24 + 36 + 48 + 1.8k + 1.8k + 3.6k + 3.0k ≈ **10.4k**. So the total is 131k + 0.92k + 0.14k + 10.4k ≈ **142k**, spending about 11.4k of the DI track's ~12k allowance, and well under 200k [I]. Two branches are not budgeted: step 2's "add fold 1" (≤ 1.35k) and a second scoring-hedge control (+1.8k). Either one can push the DI track past 12k [I]. It needs a running tally in the ledger, and the user is asked before going past the DI-track allowance, and before anything would pass 200k ([ROADMAP.md](../ROADMAP.md), line 154) [V rule].

**MPS time.** The fold-3 arms and the three-fold fine-tune total roughly **13–25 h** of single-job MPS time, plus about 2–3 h if the contingent arm 1e runs [I]. Retraining from scratch instead, at 28,250 steps with an unmeasured slowdown, would be about 8–20 h per fold. **Fine-tuning from each fold's C′ is the efficient choice**, and a from-scratch run is declared only if the fine-tunes stall at C′'s solution [I]. Throughput carries a caveat. The solo fold runs were measured at 1.19–1.27 steps/s, and the loss-pilot figure of 1.4 it/s predates the CPU-STFT fix [V].

**Disk.** The brief inferred only about 8 GB of headroom, but the 43 GB free on 2026-10-15 was measured while the 34.5 GB SW50R/AC20 caches still existed ([song-settings-plan.md](../song-settings-plan.md), lines 291–296; [cprime-folds-results.md](../cprime-folds-results.md), lines 58–59) [V]. With those caches deleted and the ~5–6 GB bank written, free space is likely about 70 GB [I]. The cache rebuild needs **≥ 66 GB free**, per the C′-folds pre-check ([cprime-folds-plan.md](../cprime-folds-plan.md), lines 57–63) [V]. Measure before rebuilding. If short, rebuild only what the fine-tune reads, or decode FLACs in the loader. Stem waveforms would add about 1 MB per 10-s mono 16-bit file, about 5 GB for 5k [I].

## Gaps the ML session should close first

| Gap | Where it is | Cost | Why it matters |
|---|---|---|---|
| Ladder rung 13 (phase scramble > 1 kHz) and rungs 14–15 (bleed −20/−10 dB) | Local `~/ndsp-presets/learn/rank-margin/report.json` only; declared in the [plan](../rank-margin-ladder-plan.md) (lines 131–132), absent from the results doc | 0 | Orders phase-derivative and MPD arms against short-window terms; bleed tells whether stems matter for the clean-render failure |
| C′'s `dec.0` gate state | Local `fit-cprime-f{f}*.log`; or compute `gate_open` on each checkpoint | 0 | If the bottom is dead again, 8.4 of 9.8M weights are unused and fine-tunes act only on shallow levels |
| Per-cell control results and measure-DI shortfalls on fold 3 | Local `result.json` | 0 | Sets step 2's exact bar and C′'s fold-3 baseline |
| C′'s knob-bias direction in the control | Not recorded in any committed doc | 0 | An earlier rebuild drove picks to lower gain (43 against 14) ([closeness-review-2026-10-10.md](../closeness-review-2026-10-10.md)) [V]; says whether the error acts like added dirt |
| Gap over-fill: error floor or pass-through | Stored `<cell>-rebuilt.npy` and fakes | 0 | Pass-through would argue for less skip leakage, not more loss weight |
| Arm B stem waveforms | `song_aug.build` saves features only [V] | Code change; 28–39 h CPU if re-separating | Needed for every stem-stage arm |
| DAC continuous-latent shift stability; crest and gap of DAC round trips | Never measured | < 1 h | Opens or closes E1′ |
| MPS step time and gradient correctness of each new term and discriminator | Never measured | ~1 h | Sets every hour estimate above |
| Free disk now | Last committed figure predates cache deletion | 0 | The cache rebuild needs ≥ 66 GB |
| Where in time C′'s render error lives | Never measured; D0 | 48 renders | Decides the masking route |
| Whether C′'s output stage can draw 1-ms detail at all | Never measured; step 0e | 0 | A failed loss arm is otherwise confounded with model capacity |
| Magnitude over time against phase and fine shape | Never measured; the optional swap rung in step 0b | 18–36 renders | The ladder fixed only static EQ and broadband envelope |

## Conclusion

The project has spent two experiments learning what C′'s error is *not*. That narrows experiment 4 more than any paper could. The likeliest problem is the conditional-median objective acting on fine structure under about 5–10 ms, which C′'s loss terms barely resolve [I]. The successor should change the objective first and keep the backbone. A zero-render capacity check guards that choice: if C′'s 12 kHz output stage cannot draw the detail, a zero-initialised full-rate head is added before the loss route is judged. The codec-latent and stem routes are follow-ons, with cheap ceiling checks in front of them.

The ladder's oracle transplants also change how the gap-level symptom should be read. Fixing it is necessary for a clean-sounding DI, but it is not sufficient to steer a knob search. That is why every proposed in-training metric is a sanity screen, and only the known-target control can pass or stop a rebuild.

Three zero-render reads, made before writing the plan, will tell the ML session which arm to run first: the phase-scramble rung, C′'s gate state and fold 3's per-cell results. Fold 3, with four informative cells, gives the first real signal for about 2k renders and a working day of MPS time.
