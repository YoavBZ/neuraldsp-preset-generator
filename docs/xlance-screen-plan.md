# X-LANCE against Mega-53 fast: separator screen plan (2026-10-20)

Declared before any X-LANCE weight was downloaded or run. Development data only. Zero renders,
no training. Ledger entry `xlance-screen` in [dev-test-ledger.json](dev-test-ledger.json).

**Question.** Should X-LANCE's guitar chain replace Mega-53 (fast setting) as the ML separator
before the direct model's full build? On sets 1–3 (2026-10-08) it matched Mega-53's SNR with a
better spectral shape (single-guitar LSD 4.40 against 7.40). It was set aside only for its licence
(`gtr_mss` is fine-tuned from BS-RoFormer-SW), which the user now accepts.
See [separator-upgrade-results.md](separator-upgrade-results.md).

**Not changed:** the pilot ([direct-model-stems-plan.md](direct-model-stems-plan.md), amendment 1)
keeps Mega-53 fast, which 1c chose. This screen only decides the full build's separator.

## Material and inputs

- **Stage F's 21 parts, 12 bands.** Separation measures only; no arm scores are read or chosen on.
- **Primary input, as Mega-53 fast got it:** the 10-s crop `mix.wav` alone, mono (`CR.mono`),
  48 kHz. That is also what the build separates (the exact 10-s mix).
- **Secondary, descriptive:** the stored 30-s context (`arm-a-mega53/contexts`), as X-LANCE ran on
  2026-10-08 (10-s chunks, 1-s linear crossfade, `inference_full.py`), then cropped.
- Mono goes in as two equal channels, resampled to X-LANCE's rate and back as `MsstSeparator`
  does; the stem is the mean of the output channels.

## Rows (reference: the amp track, `reference.wav`)

| Row | What | Role |
|---|---|---|
| M_f | Mega-53 fast, gate 1's stored stems (`direct-stems/gate1/stems/mega53/stagef`, read-only) | baseline |
| **X** | X-LANCE `denoise.pth` → `gtr_mss.pth` on the crop | **deciding** |
| X_g | `gtr_mss.pth` alone on the crop | descriptive |
| X_ctx | X on the 30-s context, cropped | descriptive |
| G | class-perfect stem (all electric guitars; `separation-finetune/G/crop`) | anchor |
| mix | the crop mix itself | floor anchor |

Gate 1's stage F stems have no stored hashes, so their sha256 is recorded at the start, and three
of them (seed 20261082) are re-separated with Mega-53 fast on the CPU: they must match at ≥ 100 dB,
or the run stops. Each row is also measured against G (the class job), descriptively.

## Measures and readout

Per part: gain-fitted SNR (`stereo_mix_check.snr_db`), LSD (`lsd_db`), and brightness difference
(`hf_ratio_db`, 3–10 kHz over 0.2–3 kHz, stem − reference), via `separation_ceiling.measures`.
Paired Δ = X − M_f, band-weighted, 90% band bootstrap (`band_boot`, `random.Random(20261019)`,
4,000 draws). **Primary population:** the 19 parts with another electric guitar (10 bands);
all 21 (12 bands) beside it. Also reported: leave-one-band-out minimum, and without the MUSDB18
songs.

## Decision rule (declared)

**Switch to X** only if, on **both** the 19 parts and all 21:
1. Δ SNR's interval reaches 0 or lies above it (upper bound ≥ 0), **and**
2. Δ LSD's interval lies entirely below 0 (upper bound < 0).

Otherwise **keep Mega-53**. Brightness, X_g and X_ctx inform but do not decide. A quality pass
whose cost fails the check below is reported as "pass, over budget": the user decides.

## What a switch costs

- **Re-separating the whole build:** the pilot's 7,720 examples (if reused for the full model) and
  the rest's 15,311, plus V_sep's 1,720 Mega-53 stems; each needs a re-render (no audio is kept).
- **Speed:** CPU s per 10-s clip at 2 threads, nice 10, for X, X_g and Mega-53 fast on the same
  clips (the MPS is busy, so no MPS timing now). The budget check scales the plan's Mega-53
  separation budget (13–17 h for 15,311) by the measured X / M_f ratio. Over 1.5× the budget
  fails cost. X's MPS speed must be measured on one clip, when the MPS is free, before any switch.
- **Download:** `denoise.pth` 913 MB and `gtr_mss.pth` 204 MB (HF API sizes), code repo 0.4 MB.

## Compute and safety

About 190 model passes of 10 s on 2 CPU threads at nice 10, roughly 1–2 h; no MPS. Outputs in
`~/ndsp-presets/learn/xlance-screen/`; tools in `~/ndsp-presets/tools/xlance/` with a manifest of
sha256 and source URLs. Disk guard 31 GB. No held-out data (Guitar-TECHS P3, sets 4–6, held-out
ledger entries). Caveat to check: whether X-LANCE's training data includes Cambridge sessions.
