# Separator upgrade: results (2026-10-08)

Declared in [separator-upgrade-plan.md](separator-upgrade-plan.md) before any result.
Stems and manifest: `~/ndsp-presets/learn/sep2/` (`manifest.json`; scripts in
`_work/scripts/`). CPU only throughout.

## Verdict: no candidate replaces htdemucs_6s

Every open candidate beats htdemucs_6s, but by about 1 dB in median SNR, not the 2 dB the
rule asks for on both sets. Usable counts rise sharply (sets 1–2: 14 → 20–22 of 28;
set 3: 12 → 20–21 of 33). The gain comes almost all from single-guitar parts (+4 dB
paired). On multi-guitar parts the median gain is only +0.3 to +0.4 dB, because a
"guitar" stem still holds the other guitars.

| Stem (instrumental, 10-s crop) | Sets 1–2 median SNR | usable /28 | Set 3 median SNR | usable /33 | single (7) | multi (54) | active LSD, sets 1–2 / set 3 |
|---|---|---|---|---|---|---|---|
| htdemucs_6s (baseline) | 1.11 | 14 | 0.63 | 12 | 5.86 | 0.74 | 5.47 / 4.95 |
| **mega53** (electric-guitar) | 2.32 (+1.21) | 21 | 1.48 (+0.85) | 21 | 9.96 | 1.45 | 8.56 / 5.53 |
| xlance (denoise → gtr_mss) | 2.35 (+1.24) | 20 | 1.39 (+0.76) | 20 | 9.88 | 1.43 | 7.04 / 5.59 |
| mega53_xlance | 2.11 (+1.00) | 20 | 1.48 (+0.85) | 21 | 9.96 | 1.42 | 8.64 / 5.53 |
| pan, rule (native stereo) | 2.31 (+1.20) | 22 | 1.43 (+0.80) | 21 | 10.24 | 1.47 | 8.47 / 5.38 |
| *descriptive:* mega53_guitar | 2.12 | 20 | 1.54 | 21 | 9.97 | 1.40 | 8.20 / 6.66 |
| *descriptive:* pan_sim, rule | 3.21 | 17 | 1.16 | 18 | 13.44 | 1.16 | 8.92 / 5.85 |
| *descriptive:* pan_sim, oracle | 4.45 | 25 | 1.98 | 22 | 13.44 | 2.50 | 7.25 / 5.26 |

The numbers in brackets are the gain in median over htdemucs_6s. The median of the
paired per-part differences is smaller: mega53 +0.50 dB on sets 1–2 and +0.61 dB on set 3.

## Findings

- **Mega-53 and X-LANCE are equivalent here.** Chaining `gtr_mss` after Mega-53 does
  almost nothing: it is a mixture-to-guitar model, and on a guitar stem it is close to
  the identity.
- **Mega-53 loses the spectrum's edges.** Its median band error, relative to the amp
  track, is −9 to −14 dB below 63 Hz, −15 dB at 8 kHz and −36 dB at 12.7 kHz.
  htdemucs_6s's is −2 to −3 dB there, −6 dB at 8 kHz and −18 dB at 12.7 kHz. So its
  active LSD is worse (8.56 against 5.47 on sets 1–2), as BS-RoFormer-SW's was.
  X-LANCE keeps the shape better (LSD on single-guitar parts: 4.40 against 7.40 for
  Mega-53).
- **Pan isolation can't be tested on these sessions.** They carry no pan, and 96% of
  guitar tracks are mono, so in the native stereo rebuild 99.9% of the stem's energy is
  in the centre. The rule picks the centre for all 61 parts, and the oracle is the same.
- **Simulated pan, descriptive only.** Here each guitar was given a random position from
  hard left to hard right.
  - An oracle choice of left, centre or right gains +2.6 dB paired on sets 1–2 and
    +0.7 dB on set 3. Multi-guitar parts go from 1.45 to 2.50 dB median.
  - The automatic "most energy" rule is worse than no masking on multi-guitar parts
    (1.16 dB): the loudest side is usually another guitar.
  - So pan isolation needs a choice: the user picks the side by ear from three short
    clips, or a rule matches each side against something known about the part. The
    "most energy" rule fails.
  - Stereo input alone also helps a little: Mega-53 on the simulated stereo mix, with
    no mask, scores 2.60 and 1.79 dB.

## Cost (CPU, 4 threads, per 30-s context)

| Method | CPU s | wall s |
|---|---|---|
| htdemucs_6s (set 3 run) | 39 | 15 |
| Mega-53, electric-guitar and guitar heads only | 315 | 102 |
| Mega-53, all 53 heads (timing test) | 464 | 191 |
| X-LANCE denoise + gtr_mss | 193 | 87 |
| gtr_mss on a stem | 108 | 50 |

The machine was shared with other jobs, so the wall times are inflated. Pruning
Mega-53 to the two guitar heads gives bit-identical stems.

## Licences

- **Mega-53:** checkpoint and yaml from ZFTurbo/Music-Source-Separation-Training,
  release v1.0.21. The repo is MIT; the release has no separate licence.
- **X-LANCE:** `denoise.pth` and `gtr_mss.pth` from chenxie95/xlance-msr-ckpt (MIT card);
  the code, ModistAndrew/xlance-msr, is MIT. `gtr_mss` is fine-tuned from
  BS-RoFormer-SW, which has no stated licence.
- The MLX guitar-head conversion was not needed.
- Hashes are in `manifest.json` → `provenance`.

## What this means

On these multitrack sets, a better network separator is worth about 1 dB, and many more
usable parts, but not a step change. The bottleneck is other guitars in the same stem,
not the separator. Two things could address it: a way to choose among guitars (pan
picked by the user, or the declared multi-guitar reference), or a lead/rhythm splitter.
If one separator is adopted anyway, X-LANCE gives the same SNR as Mega-53 with a better
spectral shape and at 60% of the CPU time.
