# X-LANCE against Mega-53 fast: separator screen plan (2026-10-20)

Declared before any X-LANCE weight was downloaded or run. Development data only. Zero renders,
no training. Ledger entry `xlance-screen` in [dev-test-ledger.json](dev-test-ledger.json).
Revised once after review (2026-10-20, before any download): the decision moved to the audit
mixes, which have an exact reference; a tone guard was added.

**Question.** Should X-LANCE's guitar chain replace Mega-53 (fast setting) as the ML separator
before the direct model's full build? On sets 1–3 (2026-10-08) it matched Mega-53's SNR with a
better spectral shape (single-guitar LSD 4.40 against 7.40). It was set aside only for its licence
(`gtr_mss` is fine-tuned from BS-RoFormer-SW), which the user now accepts.
See [separator-upgrade-results.md](separator-upgrade-results.md).

**Not changed:** the pilot ([direct-model-stems-plan.md](direct-model-stems-plan.md), amendment 1)
keeps Mega-53 fast, which 1c chose. This screen only decides the full build's separator.

## Material

- **Primary (decides): the 164 non-stage-F audit true mixes, 6 bands** (gate 1's (iii); 10-s,
  unmastered, `direct_stems.audit_audio`: rendered guitar + backing at the stored gain). The
  reference is the exact rendered guitar. Mega-53 fast stems: `direct-stems/gate1/stems/mega53/audit`
  (read-only), each checked against `sepcheck/fast-stem-hashes.json` before use.
- **Descriptive: stage F's 21 parts (12 bands)** and its 19 parts with another electric guitar
  (10 bands), against the amp track. Separation measures only; no arm scores read or chosen on.
  Gate 1's stage F stems have no stored hashes: their sha256 is recorded at the start.
- **Input, as Mega-53 fast got it:** the exact 10-s mix alone, mono, 48 kHz (also what the build
  separates). Mono goes in as two equal channels, resampled to X-LANCE's rate and back as
  `MsstSeparator` does; the stem is the mean of the output channels.

## Rows

| Row | What | Where |
|---|---|---|
| M_f | Mega-53 fast, gate 1's stored stems | both |
| **X** | X-LANCE `denoise.pth` → `gtr_mss.pth` | both; **decides on the audit mixes** |
| X_g | `gtr_mss.pth` alone | stage F (descriptive) |
| X_ctx | X on the stored 30-s context (10-s chunks, 1-s crossfade, as on 2026-10-08), cropped | stage F (descriptive) |
| G | class-perfect stem (`separation-finetune/G/crop`) | stage F anchor |
| mix | the mix itself | floor anchor, both |

## Checks before any readout

- **Reproduction:** three audit clips and three stage F crops (seed 20261082) are separated again
  with Mega-53 fast exactly as gate 1 ran (`run.json`: pruned to the guitar heads, chunk 441,000,
  overlap 1, 4 CPU threads). Each must match the stored stem at ≥ 100 dB SNR, or the run stops.
- **Alignment:** X's stem against the reference by GCC (`rank_margin.gcc_lag`) after resampling.
  Any lag beyond ±3 samples stops the run until the alignment is fixed.

## Measures

Per clip: gain-fitted SNR (`stereo_mix_check.snr_db`); **LSD over the direct model's mel range,
30 Hz–16 kHz** (`lsd_db` with those limits; **this LSD decides**); full LSD (80 Hz–12 kHz, as
before); brightness difference (`hf_ratio_db`, stem − reference). **Darkening spread:** per clip,
the gain-removed 1/3-octave error; per frequency band, the median and the across-clip SD and IQR
of that error, and the across-clip SD of the mean error above 3 kHz. A small spread means a
consistent darkening; a large one means an inconsistent one.

**Readout.** Paired Δ = X − M_f. Audit: band-weighted, 90% band-clustered t interval (5 df), the
deciding interval as in gate 1, with the band bootstrap (`random.Random(20261019)`, 4,000 draws)
beside it. Stage F: band-weighted with the band bootstrap. Every difference is reported with its
interval, whatever the decision.

**Exclusions (reported on both sets):** without MUSDB18 material (`locator_truth`: audit, Hollow
Ground's "Ill Fate", 25 clips; stage F, It Was My Fault For Waiting, Femme, Signs), and without
any Cambridge session, which X-LANCE or Mega-53 may have trained on. On the audit that leaves only
Eggy and Renesans, 2 bands: point estimates only.

## Decision rule (declared)

**Switch to X** only if, on the 164 audit mixes, all of these hold:
1. Δ SNR point estimate ≥ 0 (so its interval reaches 0 or above);
2. Δ mel-range LSD interval entirely below 0;
3. cost (below) within 1.5× the per-clip budget.

Otherwise **keep Mega-53** (on a tie, the cheaper incumbent). If 1 and 2 hold but 3 fails, the
result reads "pass, over budget" and the user decides. Stage F, X_g, X_ctx, brightness and the
spread inform but do not decide.

## Cost

- **Per-clip budget:** Mega-53 fast's CPU seconds per 10-s clip, measured in this screen on the
  same 10 audit clips, at the same 2 threads and nice 10, as X. X passes cost if its time is at
  most 1.5× that. The plan's build budget (13–17 h for 15,311 clips) scales by the same ratio.
  X's MPS speed must be measured on one clip, when the MPS is free, before any switch.
- **A switch re-separates the whole build:** the pilot's 7,720 examples, if reused, the rest's
  15,311, and V_sep's 1,720. Each needs a re-render, since no audio is kept.
- **Download:** `denoise.pth` 913 MB and `gtr_mss.pth` 204 MB (HF API sizes); code 0.4 MB.

## Compute and safety

About 490 model passes of 10 s on 2 CPU threads at nice 10 (the 6 reproduction clips at 4
threads, matching gate 1): roughly 3–5 h; no MPS. Outputs go to
`~/ndsp-presets/learn/xlance-screen/`; tools go to `~/ndsp-presets/tools/xlance/`, with a manifest
of sha256 and source URLs. Disk guard 31 GB. No held-out data (Guitar-TECHS P3, sets 4–6,
held-out ledger entries). Also checked: what X-LANCE's README says about its training data.
