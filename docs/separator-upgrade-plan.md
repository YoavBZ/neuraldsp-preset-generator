# Separator upgrade: declaration

Step 1 of `docs/research/round-5-guitar-models.md` ("Replace the separator"), under the
open-source-only decision. Declared before any candidate's stem is computed or scored.
Output: `~/ndsp-presets/learn/sep2/` (scripts in `_work/scripts/`); venv
`~/ndsp-presets/tools/sep2-venv`. CPU only (`device='cpu'`, `PYTORCH_ENABLE_MPS_FALLBACK=0`,
4 torch threads); no MLX, no cloud, no Neural DSP plugin.

## Parts

- **Sets 1–2:** K3's 28 parts (`learn/evaluate.py` `k3()`), each session checked with
  `learn/set3.py` `is_held_out` (all development).
- **Set 3:** the 33 `set3.parts("development")`; `is_held_out` asserted per part.
- Single- against multi-guitar: the manifests' `multi_guitar_mix` flag (other guitar
  tracks in the mix, at more than −30 dB to the part's own). Sets 1–2: 7 single, 21
  multi; set 3: 33 multi.

## Inputs

The 30-s instrumental contexts of the earlier stem runs
(`learn/poc/stems/_work/contexts`, `learn/set3/stems/_work/contexts`), mono 48 kHz. Every
mono-input candidate gets them exactly as htdemucs_6s did: duplicated to two channels,
48→44.1 kHz (`scipy.signal.resample_poly` 147/160), separated, channel mean, back to 48 kHz
(160/147), the crop's 10 s cut out (`crop_offset_in_context`), 480,000 frames, float32.

## Candidates

1. **`htdemucs_6s`** (baseline): the existing stems, not recomputed.
2. **`mega53`**: MVSep Mega-53 BS-RoFormer (`mvsep_mega_model_bs_roformer_53_stems_v1.ckpt`
   and its yaml, release v1.0.21 of ZFTurbo/Music-Source-Separation-Training, MIT),
   that repo's `utils.model_utils.demix` with the yaml's inference settings (20-s chunks,
   `num_overlap` 2, no normalisation), **`electric-guitar` stem**. Only the
   `electric-guitar` and `guitar` mask heads are kept: the outputs for those stems are
   bit-identical to the full model's (checked, max difference 0.0), and the 30-s context
   takes about 2 min instead of 3.2 (so the 77.5 MB MLX head conversion is not needed).
   The `guitar` stem is written too, as `mega53_guitar`: reported, not eligible.
3. **`xlance`**: the X-LANCE MSR system's published guitar chain (github.com/ModistAndrew/
   xlance-msr, MIT; weights huggingface.co/chenxie95/xlance-msr-ckpt, MIT card):
   `denoise.pth` (Mel-band RoFormer) then `gtr_mss.pth` (BS-RoFormer, one stem),
   10-s chunks with a 1-s linear crossfade as in `inference_full.py`. Note: `gtr_mss` is
   a mixture-to-guitar model (fine-tuned from BS-RoFormer-SW on degraded RawStems
   mixtures), not a stem-only refiner; its parent SW checkpoint has no stated licence.
4. **`mega53_xlance`**: `gtr_mss.pth` applied to Mega-53's stereo `electric-guitar`
   output (the "refiner after a BS-RoFormer stem" reading), same chunking.
5. **`pan`** (Avendano panning index): the winning separator among 2–4 (highest median
   SNR pooled over both sets; if none wins, still the highest) is re-run on a **stereo**
   context and the mask applied to its stereo guitar stem.
   - STFT 48 kHz, Hann, n_fft 4096, hop 1024. ψ = 2|X_L X_R*| / (|X_L|²+|X_R|²);
     Ψ = (1 − ψ)·sign(|X_R| − |X_L|). Binary masks: left Ψ < −0.2, centre |Ψ| ≤ 0.2,
     right Ψ > 0.2 (they sum to the stem). Each output is the masked channels' mean.
   - **Stereo context (`pan`)**: rebuilt like the mono one but keeping each track's
     channels (mono tracks on both channels at unity), so its channel mean is the mono
     context. Note, from a channel count before any audio was separated: the sessions
     carry no pan, and 96% of guitar tracks are mono (sets 1–2: 110 of 114; set 3: 171
     of 180), so this stereo mix puts nearly every guitar in the centre.
   - Reported: **oracle** = the best of left, centre and right against the amp track
     (an upper bound on a user picking by ear); **rule** = the region with the most
     stem energy (automatic, no reference). Only the rule is eligible.
   - **`pan_sim`** (descriptive only, never eligible): the same with a simulated pan
     layout. The part's own amp tracks share one pan, each other guitar track gets its
     own, drawn from {−1, −0.5, 0, 0.5, 1} (seed 20261007 + part index); a mono track at
     pan p goes to L = x(1 − p), R = x(1 + p), so the channel mean is unchanged; other
     tracks as in `pan`.

## Metrics (as in the existing manifests)

Against `reference.wav` (the part's amp track), on the crop's 10 s: `snr_db` after the
least-squares gain, `lsd_active_db` (and `lsd_db`), `usable` = SNR ≥ 1 dB (the baseline's
usable count is htdemucs_6s alone: 14 of 28 on sets 1–2, 12 of 33 on set 3). Per set:
median SNR, median active LSD, usable count, median paired SNR difference to htdemucs_6s;
and by single- against multi-guitar. CPU and wall seconds per part are logged.

## Decision rule

A candidate replaces htdemucs_6s if its median SNR is **at least 2 dB higher than
htdemucs_6s's on both sets** (sets 1–2 and set 3 separately), **and** its usable count is
not lower on either set. If several pass, the one with the highest median SNR pooled
over both sets wins. Four eligible rows (`mega53`, `xlance`, `mega53_xlance`, the `pan` rule) are
tested with no multiplicity correction; whatever comes out is reported.
