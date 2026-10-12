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
