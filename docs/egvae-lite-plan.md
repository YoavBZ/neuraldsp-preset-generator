# Tone removal with a content/tone network (EG-VAE-lite): plan (development)

Declared 2026-10-13, before any code is written or trained. Asked for by the user.

## Why

[EG-VAE](https://arxiv.org/abs/2608.05513) (2026, CC BY 4.0) recovers a guitar's dry DI from a
processed recording ("tone removal").
- It separates a per-frame **content** code (what is played) from a global **tone** code (the
  rig), and decodes the content with the tone switched off: Conditional LayerNorm with γ = 1,
  β = 0.
- It trains on a contrastive grid: the same content through different tones, and the same tone
  on different content.
- It uses a multi-scale mel loss plus adversarial losses.
- On held-out Morgan Amps Suite presets it beats a distortion-recovery baseline: mel distance
  1.10 against 1.21, and a dryness MOS of 3.42 against 2.36.

Our DI network (C′) does the same job without any of these ideas. No code or weights are
released, so we reimplement the recipe (open-source only).

## Scale (what this Mac can train)

| | the paper | here |
|---|---|---|
| backbone | DAC-VAE, 1024-d latent, hop 1920 at 44.1 kHz | the same block types, 512-d latent, hop 960 at 48 kHz, about 15–25 M parameters |
| content code | per frame, 128-d variational bottleneck | the same |
| tone code | 64-d, 4-layer Transformer, mean-pooled | the same, 2 layers |
| data | 22 h of DI × 474 tones (758 h) | development DIs × Morgan menu presets (below) |
| training | 150 k + 200 k steps, GAN | stage 1: mel + KL + masked-DI loss, no GAN, about 24 h; stage 2 (GAN) only if stage 1 passes |

## Data (development only; no held-out sets)

- **DI windows:** the K3 training folds' DIs plus Guitar-TECHS, as for C′, with fold 2 and set 3
  left out. So the 18-part evaluation below is untouched.
- **Renders:** each window through about 24 tones (Morgan menu presets plus random knob draws,
  dry, `RULE_SET`). That gives the contrastive grid: the same content through several tones, and
  each tone on several contents. About 40k renders of 6 s.
- **Sampling** follows the paper: self-reconstruction, conversion and tone-masked reconstruction
  with probabilities 0.25, 0.45 and 0.30.

## Engineering rules

- **Every STFT-based loss runs on the CPU when the model is on MPS** (the MPS gradient bug). This
  is guarded by a gradient check at crop length before training.
- **Training is matched in steps**, logged, and checkpointed every 5 k steps.

## Pre-checks (before any pick test)

1. **Tone-masked output against the true DI,** on fold-2 validation renders: its mel distance
   must be lower than C′'s on the same renders.
2. **Coherence with the true DI on the 18 development parts** (the residual-di set): it must be
   at least C′'s 1–3 kHz coherence (0.207).

If either fails at the end of stage 1, stop, and report.

## The test (development; the same machinery as the residual test)

**Parts:** the 18 development parts in 8 bands that no fold-2 network trained on.
- Rebuild each DI with EG-VAE-lite (tone-masked), uncut, at −22.9 LUFS.
- Render it through the 111-preset menu, pick per amp, and score with the stored measure on the
  other half.

**The gate,** against C′ (the mean of its three seeds), on the band-mean rule with 7 degrees of
freedom:
- **Helps:** the interval lies below 0, and more than half the bands are negative.
- **Futile:** the lower bound is above −0.02.
- **Inconclusive:** anything else.

**Also reported:** each class; against the fixed preset; the oracle; coherence; mel distance; a
listening sample for the user (the "Cut It Out" span, A/B against C′, blind).

**If it helps:** EG-VAE-lite is carried to the held-out test with C′'s rules (set 5, and set 6 if
labelled). Development has been used many times, so a helps here is a lead, not a claim.

## Safety

- Renders: about 40k in 6 reused processes, coordinated with the product session.
- Disk stays ≥ 33 GB free.
- Reviews: an independent reviewer checks this plan, the code (including the MPS gradient check)
  before training, and the result.

## Amendment after review (2026-10-13, before any code or training)

The review (`tmp/egvae-lite-plan-review.md`, local) approved the plan with major changes. They
replace the design above.

1. **A correction:** the paper's 1.10 against 1.21 (mel) and 3.42 against 2.36 (dryness) are on
   tones it trained on. On unseen Morgan tones it only ties the distortion-recovery baseline
   objectively (mel 1.19 against 1.22, STFT 1.87 against 1.86). Its wins there are in listening:
   quality 3.69 against 2.06, dryness 3.50 against 2.11. So expectations are modest.
2. **Start from DAC 44 kHz,** the Descript Audio Codec, with MIT-licensed code and weights. It is
   EG-VAE's own backbone. Training from scratch is dropped: the Mac manages about 3% of the
   paper's training audio, with no adversarial training.
3. **Staged; each stage runs only if the one before shows room:**
   - **E0, no training:** round-trip the 18 parts' true measure DIs through DAC, at 44.1 kHz with
     offline resampling.
     - Measured: mel distance, coherence and lag against the true DI.
     - Then the menu renders and picks, scored like the oracle: picks by the measure on the
       round-tripped DI, scored on the other half with the stored true-DI measure.
     - If the round-trip loses most of the oracle's edge over C′ (the oracle at −0.131 against
       the fixed preset, C′ at about −0.09), the DAC route is dropped.
     - E0 also sets pre-check 2's coherence bar.
   - **E1:** DAC frozen at both ends, a small mapper from the recording's codes to the DI's
     codes, trained on C′'s own data and target (the average-balance DI, C′'s augmentations),
     then compared with C′. Its own plan section precedes training.
   - **E2:** the full content/tone model on DAC, with the paper's pitch and tone-class
     supervision and the conversion task. It runs with a control, C″: C′'s recipe on the same
     new renders. Tones come from a fixed bank, about 45% clean, 45% crunch and 10% high-gain,
     with 6–8 tones per window over 5–7k windows. It starts only if E0 or E1 shows room.
4. **Development tests are read as harm and non-inferiority checks.** The gap to the oracle is
   about 0.03–0.04, so "inconclusive" is the likely result. What a positive reading earns is a
   held-out test on set 5's crunch parts, where the room is larger.
5. **MPS:** every STFT or mel loss runs on the CPU, guarded by per-module, per-loss gradient
   checks at the real crop length, before training and after 200 steps.

### E0's bar (declared before E0 runs)

- **What's compared:** on the 18 development parts, picks from DAC-round-tripped true DIs
  against the fixed preset, as a band mean, alongside the oracle (−0.131) and C′ seed 0
  (−0.099), from `residual-di-results.md`.
- **The bar:** the DAC route continues only if the round-tripped picks keep at least half the
  oracle's edge over C′, a band mean of −0.115 or lower.
- **Reported, not gating:** mel distance, the coherence bar for later checks, and the lag.

## E0 result (2026-10-13)

Code: `learn/egvae_e0.py` (with `learn/egvae_e0_dac.py` for the DAC venv). Numbers:
`docs/egvae-e0-result.json`. DAC 44 kHz (descript-audio-codec 1.0.0, MIT weights), on the CPU,
unchunked `compress`/`decompress` with all 9 codebooks. The true measure DI
(`confirm_run.build_di('measfix')`) goes 48 → 44.1 kHz (`resample_poly` 147/160), through
DAC, and back, then to −22.9 LUFS. The menu renders and picks are done as for the oracle, with
the round-tripped DI in place of the true one.

**Picks, against the leave-band-out fixed preset.** Band-weighted first, part-weighted second:

| chooser | band-weighted | part-weighted | bands negative |
|---|---|---|---|
| DAC round trip (E0) | **−0.129** | −0.147 | 7 of 8 |
| oracle, the true DI (check: −0.131) | −0.131 | −0.148 | 8 of 8 |
| C′ seed 0 (check: −0.099) | −0.099 | −0.114 | 7 of 8 |

- The round trip keeps **91% of the oracle's edge over C′**. Its picks match the oracle's in
  94% of part-amp-half cells.
- E0 against C′: −0.029 band mean, 90% interval [−0.054, −0.005].
- E0 against the oracle: +0.003. The gap comes almost entirely from Zeno (+0.031), with a little
  from Diesel13 (−0.009).
- By class, E0 against the fixed preset is −0.079 on clean (oracle −0.087) and −0.191 on crunch
  (oracle −0.186).
- **Pipeline check.** Two parts' true DIs were put through the same render and score code. They
  reproduce the stored measure: median |log ratio| 0, at most 0.009, over 444 values.

**The round trip against the true DI** (reported, not gating):

- **Mel distance** (DAC's multi-scale L1 log-mel): median 0.91, band-weighted 0.89. For scale,
  the paper's mel distances are 1.10–1.22.
- **Coherence** (median, 80 Hz–1 kHz / 1–3 kHz / 3–8 kHz): 0.92 / 0.49 / 0.06. Band-weighted it
  is 0.93 / 0.49 / 0.06.
  - DAC keeps the waveform below 1 kHz. Above 1 kHz it rebuilds the sound, not the waveform.
  - A resample-only round trip gives about 1.00 in all three bands, so the loss is DAC's.
  - So for any DAC-decoded DI, 1–3 kHz coherence has a ceiling of about 0.49. Pre-check 2's bar
    stays C′'s 0.207, and 0.49 is the most a DAC route can reach.
  - 3–8 kHz coherence means nothing for DAC outputs. The picks show the measure does not need
    it.
- **Lag:** 0 samples on all 18 parts.

**Decision.** E0's band mean is −0.129, which beats the bar of −0.115. **The DAC route
continues to E1.**

This shows only that DAC's codes keep what the picker needs from a true DI. It does not show
that a mapper can recover those codes from a recording; that is E1's question. The E0 renders
were deleted after scoring.

## E1: a mapper in DAC's latent space (declared 2026-10-13, after E0 and before any E1 code)

**The question:** E0 showed that DAC's code of the true DI keeps what the picker needs (−0.129
against the oracle's −0.131). Can a network map the recording's DAC latent to the DI's latent?

- **Model:** DAC 44 kHz encoder and decoder, frozen.
  - **The mapper:** a 1-D convolution front end plus a small Transformer, about 10–20 M
    parameters, working on DAC's continuous pre-quantisation latent (about 86 frames a second).
  - **Its output:** the DI's latent. It is quantised by DAC's own codebooks before decoding.
- **Loss:** L1 plus cosine on the latents. Nothing STFT-based, so the MPS gradient bug doesn't
  apply; a gradient check on MPS against CPU still runs at crop length before training.
- **Data:** C′'s own pairs and target, for a fair comparison.
  - **The pairs:** `cache` (PR12), and the SW50R and AC20 pair caches rebuilt from their stored
    renders.
  - **The split:** K3 fold 2 is held out as validation; set 3 is never seen.
  - **The target:** the DI at the average balance, as C′'s.
  - **Augmentation:** C′'s, applied before encoding (EQ tilt and bell, bleed, noise).
  - **Encoding:** a fixed subset of at most 20,000 clips of 6 s is encoded once into stored
    latents, at 48 kHz → 44.1 kHz (`resample_poly`).
- **Budget:** the same order as C′ (about 28k steps), on MPS, seed 0.
- **Pre-checks, at the end, on the 18 development parts:**
  1. **Latent L1 on fold-2 validation** is below the identity baseline (the recording's latent
     taken as the DI's).
  2. **Coherence at 1–3 kHz** is at least C′'s 0.207. E0 showed a DAC-decoded DI can reach
     about 0.49.
  - If either fails: stop, and report.
- **The test:** rebuild the 18 parts' DIs (recording → DAC encoder → mapper → DAC decoder →
  48 kHz → −22.9 LUFS), then render, judge with `rebuilt_distance` and pick, exactly as for C′.
- **The gate, E1 against C′** (the mean of three seeds), on the band-mean rule with 7 degrees of
  freedom: "helps", "futile" or "inconclusive". It is read as a harm and non-inferiority check;
  the gap to the oracle is reported.
- **What it earns:** "helps", or "inconclusive" with no harm (band mean ≤ 0), takes E1 to set 5's
  held-out crunch test, declared as a further use of set 5. "Futile", or harm, sends us to E2.
- **Reviews:** independent reviews of this section, the code, and the result.

### E1 after review (2026-10-13, before any E1 code; replaces the E1 text above where they differ)

Review: `tmp/egvae-e1-review.md`, local. It found three things: DAC's pre-quantisation latent is
not what the decoder uses; averaging latents ruins the sound; and recordings and DIs share
1–3% of codes.

1. **Codes to codes.** The input is the recording's DAC codes (9 codebooks), and the output is
   the DI's codes, predicted per frame and codebook with cross-entropy. Decoding uses the
   argmax, so the output is always a valid DAC latent, with no averaging. Nothing STFT-based is
   in training.
2. **Data:** every C′ training and validation clip.
   - **Sources:** PR12 from `cache`; SW50R and AC20 encoded straight from the pairs FLACs.
     Filtering to lufs ≥ −40 and sorting by id reproduces each cache's `meta.json` row for row,
     so the stored DI spectra line up with the average-balance target.
   - **Augmentation:** C′'s own `make()` (factored out, with a test that it matches C′
     exactly), applied once per clip. A second augmented pass is added if time allows.
   - **Inputs:** set to −16 LUFS before encoding, as E0 did.
   - **Storage:** codes only.
3. **Batch size:** declared in the code. Training runs to a validation plateau, with seed 0.
4. **Pre-checks, replacing the earlier ones:**
   - (1) decoded mel on fold-2 validation, at or below C′'s;
   - (2) 80 Hz–1 kHz coherence on the 18 parts, at or above C′'s 0.472 (DAC's ceiling there is
     0.92). Coherence at 1–3 kHz is reported only.
5. **Inference:** windowed over the 10-s crops. There is no alignment to the true DI at test
   time; the lag is reported.
6. **The comparison:** against C′ as the mean of seeds 0 and 1, averaged per cell as in
   `set5_test.evaluate`. Those are the seeds with development picks. Disclosed: E1 carries a
   pretrained 76 M-parameter codec, so a gain can't be credited to the mapper alone.
7. **The set-5 rule, replacing the earlier one:** E1 earns a held-out test only with a
   development band mean of −0.015 or lower against C′, and a 90% upper bound below +0.03. That
   test is declared, with its ledger entry recorded as set 5's second use, before any render.

### E0b (declared before it runs; report only)

E0 repeated with DAC decoding only the first 4 of 9 codebooks. If those picks keep most of E0's
edge, E1 may predict 4 codebooks (an easier task). That would be declared before E1 training,
or else all 9 are kept.

## E0b result (2026-10-13; report only)

Code: `learn/egvae_e0.py` with `EGVAE_E0_VARIANT=e0b`, and `learn/egvae_e0_dac.py roundtrip DIR 4`.
Numbers: `docs/egvae-e0b-result.json` (its `e0_*` keys are E0b's picks). E0's steps exactly,
except that `compress` keeps only the first 4 of DAC's 9 codebooks, and `decompress` decodes
those 4 (DAC's own `n_quantizers=4`).

**Picks, against the leave-band-out fixed preset, band-weighted:**

| chooser | band-weighted | bands negative |
|---|---|---|
| E0b, 4 codebooks | **−0.126** | 7 of 8 |
| E0, all 9 codebooks | −0.129 | 7 of 8 |
| oracle, the true DI | −0.131 | 8 of 8 |
| C′ seed 0 | −0.099 | 7 of 8 |

- E0b keeps **91% of E0's edge over C′** (83% of the oracle's).
- E0b against C′: −0.027 band mean, 90% interval [−0.052, −0.001]. E0's was −0.029.
- E0b against the oracle: +0.006; Zeno +0.021, Wall Of Death +0.010, the rest ≤ +0.007.
- **Pick agreement:** with the oracle, 92% of part-amp-half cells (E0: 94%); with E0, 90%.
- By class, against the fixed preset: clean −0.081 (oracle −0.087), crunch −0.181 (oracle −0.186).
- **Against the true DI:** mel distance median 1.19 (E0: 0.91). Coherence, 80 Hz–1 kHz /
  1–3 kHz / 3–8 kHz: 0.72 / 0.20 / 0.05 (E0: 0.92 / 0.49 / 0.06). Lag 0 on all 18 parts.

**Reading.** The picks barely need DAC's last 5 codebooks: dropping them costs 0.003 of band
mean. The waveform does need them: 80 Hz–1 kHz coherence falls from 0.92 to 0.72, still well
above C′'s 0.472. So a 4-codebook E1 is viable for the picks. Pre-check 2 (80 Hz–1 kHz coherence ≥ 0.472) then has a ceiling of about 0.72 rather
than 0.92. The choice between 4 and 9 predicted codebooks is to be declared before E1
training; the codes are encoded with all 9 either way. The E0b renders were deleted after
scoring.
