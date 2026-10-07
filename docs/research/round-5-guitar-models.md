# Round 5: guitar-specific networks, tools and separators (2026-10-07)

Two research passes, done after the clean-PR12 result of `di-recovery-results.md` and
the negative PANNs reranker result (`rerank-plan.md`). [V] = checked at the source,
[S] = from a snippet or inferred. Nothing was downloaded except where noted.

## No ready-made solution

- **Tools.** No tool, commercial or open, matches a guitar tone from a song to an amp
  sim's settings with published accuracy.
  - BIAS X "Music-to-Tone" comes closest: audio in, a BIAS X preset out. It is online
    only, with no API and no accuracy figures [V].
  - Fractal Tone Match fits only an EQ curve [S]. TONEX's ToneNET searches by
    metadata [V].
  - Groundhog OnePedal is the only tool found that accounts for the user's guitar,
    and it is hardware [V].
- **Academic work.** None of it estimates a commercial amp sim's settings from real
  records with known answers (as round 4 found).

## Guitar models with weights

| Model | What it is | Weights and licence | Slot for us |
|---|---|---|---|
| **EG-VAE** (Aug 2026) | DI recovery and a 64-d tone embedding, trained on 758 h including Neural DSP presets, tested on 96 Morgan presets | **no code or weights**; ask the authors [V] | DI recovery; tone embedding |
| **Open-Amp Fx-Encoder** (Wright) | SimCLR, 113k parameters, 64-d; same amp/pedal capture on different clips = positives; GUITAR-FX-DIST 87.9%, EGFxSet 72% | 0.49 MB in the repo, **no licence file** (local research only) [V] | DI-free reranker row; its recipe can be retrained on our renders |
| AFx-Rep (ST-ITO) | general effects encoder | Apache-2.0, 1.16 GB [V]; its authors say it works poorly on guitar tone | reranker row (low prior) |
| Comunità 2021 gfx-classifier | 13 drive pedals: class + settings | BSD-3, 3–6 MB [V]; plugin pedals, isolated notes | drive-amount feature |
| RemFX | effect removal (Demucs) | **CC BY-NC 2.0** weights, not Apache as round 4 said [V] | baseline only |
| PANAMA, NablAFx, PyNeuralFx | parametric amp trainers | MIT, no Morgan-like weights [V] | a differentiable stand-in, only if trained on our renders |

**Data.** EGDB-PG is now fully on Zenodo: 135.4 GB FLAC, CC BY 4.0, 256 BIAS FX2
amp×cab presets on the EGDB DIs [V]. That is more than this machine's free disk.

## Separators

| Separator | Guitar SDR | Licence | Note |
|---|---|---|---|
| htdemucs_6s (in use) | about 4–5 dB | MIT | our stems today |
| **MVSep Mega-53** BS-RoFormer | electric 8.15, guitar 8.25 [V] | MIT repo, 1.37 GB; a 77.5 MB MLX guitar-head conversion (MIT card) [V] | splits electric from acoustic; the shippable upgrade |
| **X-LANCE MSR guitar refiner** | 1st in the ICASSP 2026 Music Source Restoration challenge | MIT, 204 MB [V] | runs after a 6-stem BS-RoFormer |
| BS-RoFormer-SW | 9.01 [V] | licence unknown | local only |
| **MVSep lead/rhythm guitar** | 9.0–9.2 [V] | cloud API only, weights not public | the only lead/rhythm splitter; uploading audio needs the user's consent and the dataset terms checked |
| Meta SAM Audio | prompted extraction, incl. time-span prompts | SAM licence, gated Hugging Face access, CUDA recommended [V] | "this part, not that one" |
| Pan-based isolation (DSP), phantom-centre MDX23C | centre SDR 8.25 [V] | MIT | splits hard-panned rhythm doubles from a centred lead |

## What follows (ranked)

1. **Replace the separator.**
   - Mega-53's guitar head, plus the X-LANCE refiner, in place of htdemucs_6s.
   - Add pan-based isolation for multi-guitar songs.
   - Measure the stems' SNR against the amp track, then re-run the stem path.
2. **A guitar tone encoder.** Screen Open-Amp's encoder with the cheap identification
   test from the PANNs review: can a feature name the preset of a render among 22, from
   other players' renders? PANNs scored 12.7% and log-mel 13.5%, against 4.5% chance.
   - Then train our own encoder on our renders: the same preset through different DIs
     = positives, other presets through the same DI = hard negatives.
   - It is the DI-free reranker that general embeddings failed to be.
3. **User actions:**
   - ask EG-VAE's authors for the weights;
   - allow, or not, uploading development audio to MVSep's API;
   - optionally run BIAS X Music-to-Tone by hand on a few songs, as a commercial bar.
