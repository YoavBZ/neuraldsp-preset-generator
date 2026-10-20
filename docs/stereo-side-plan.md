# Pan side as a separation hint: the stage F synthetic-pan screen (plan)

Declared 2026-10-20, before any separation for it. Development only, zero renders; ledger entry
`stereo-side-screen`. Proposed by the cloud researcher
([single-guitar separation](research/single-guitar-separation-2026-10.md), last section). Code:
`learn/stereo_side_screen.py`. Data: `~/ndsp-presets/learn/stereo-side-screen/`.

## Why

The [stereo check](stereo-and-mix-check-results.md) found that keeping the target's own channel
of a stereo Mega-53 stem gains +1.55 dB [+0.85, +2.34] when the target sits at pan −0.6, and that
the stem's own L/R balance picks the side at chance (12/21). Step 0 of the
[separation fine-tune](separation-finetune-plan.md) puts the other electric guitars about 5.5 dB
above the target. Pan is the one cheap hint that names *one* guitar. This screen asks how much a
known side buys under several declared pan layouts, which splitter uses it best, and whether any
clears the +2 dB SNR step that a 21-part arm A test needs.

## Material

Stage F's 21 parts (12 bands), the 10-s crop inside the 30-s context, scored against the crop's
`reference.wav` (the target amp track). Every stage F context is a unity sum of raw tracks with a
mono target, so pan layouts can be rebuilt from the session tracks exactly as
`stereo_mix_check.cmd_contexts` builds R and P, with no renders. **Primary population:** the 19
parts in 10 bands with at least one other electric guitar (a mono or stereo track named
`gtr|guitar`, not `acoustic`; matches Step 0's list). Eat The Feeder's 5 Wickerman parts share
one band weight of 1/10. She's Gone (acoustic only) and Strangest Places (no other guitar) are
listed apart; an all-21 row is shown beside.

## Scenarios (declared pans; not measured properties of songs)

Other guitars = the tracks named `gtr|guitar` other than the target, acoustics included. In P
they are exactly the stereo check's (mono only, stereo guitar tracks native), so P reproduces
it. In HP, LC and SP, stereo guitar tracks (get-out-of-bed ElecGtr4/5/6, Today's The Day
ElecGtr10) are folded to mono and panned too, and logged. In LC the alternation runs over
*instruments*, not tracks: the mics of one take (the name without its track number and a
trailing `Mic`/`Amp`/`Close`/`DI` index, e.g. Passing Ships ElecGtr1Mic1/Mic2) share one pan, so
two coherent mics never form a phantom centre on the target. A named double (`DT`, magilla) is a
separate take and may land opposite. Pan law gL = √2·cos θ, gR = √2·sin θ, θ = (p+1)·π/4.
Everything else as recorded.

| Code | Target | Other guitars | Role | Separation |
|---|---|---|---|---|
| R | 0 (as recorded) | 0 | null | reuse the stereo check's stems |
| P | −0.6 | alternately +0.6, −0.6 (sorted order) | reproduces the stored +1.55 dB | reuse |
| HP | −1 (hard left) | all +1 | ceiling: with no reverb or bleed the left channel holds no other guitar | new |
| LC | 0 | alternately +1, −1 by instrument | lead centred, rhythms wide | new |
| SP | −0.6 | all −0.6 | adversarial, and the control for the pan law's level effect (below) | new |

The target is always on the left or centre (models are trained with channel shuffles). The
researcher's D (target and its double hard L/R) applies to one part (magilla) and is not run.

## Separators and splitters

Mega-53 (pruned electric-guitar head, `stereo_mix_check.StereoSep`, CPU, 4 threads) and htdemucs
(`StereoSep`, CPU, 2 threads), stereo in and out on the 30-s context, cropped to the 10 s.
Contexts are built in memory (not stored); a rebuilt P must equal the stored P context within
1e-6 and a rebuilt R's mid the stored mono within 1e-5.

Each splitter turns the stereo stem (L, R) into one signal. `p_t` is the target's pan; its side
is L (p_t < 0), C (p_t = 0) or R. **Oracle side** = the scenario's true `p_t`, standing in for the
arrangement file's `pan` or the user's ear.

| Splitter | Definition |
|---|---|
| **M (baseline)** | mid (L+R)/2 of the same stem. Conservative: in P, mid beat the mono-fold stem by +0.24 dB. Also reported against the mono-fold stem where it exists (R, P) |
| a. channel pick | L, R, or mid for C |
| b. side | (L−R)/2, descriptive |
| c. ILD mask | STFT Hann 2048/512 at 48 kHz; per bin p̂ = 4/π·atan2(\|R\|, \|L\|) − 1 (the pan law inverted); mask exp(−(p̂ − p_t)²/(2·0.3²)), σ = 0.3 fixed now and not swept; bins with \|L\|² + \|R\|² below 1e-10 of the crop's peak bin get mask 0; applied to (a)'s STFT |
| d. c + Wiener | Step 0's T1 on the mixture's (a) channel X: mask \|C\|²/(\|C\|² + \|X − C\|²), C = (c)'s STFT |
| e. centre model | wesleyr36 MDX23C "phantom centre" (MSST v1.0.10 release; config and weights hashed in the log; overlap 2, see below) on Mega-53's stereo stem crop; the mid of its centre output. Run on LC (where it is read) and R (the null) only. Mega-53 only |
| f. blind | energy-weighted 41-bin histogram of p̂ over [−1, 1]; its peak p̃ replaces p_t: f-pick = (a) for p̃'s side (\|p̃\| ≤ 1/3 → C), f-mask = (c) at p̃ |

**Anchors (no separator):** the class-perfect stem G (target + the scenario's other electric
tracks, same pans) through mid, (a) and (c); the ideal ratio mask on the mixture's (a) channel
(the single-channel mask ceiling); the mixture's mid and (a) (input SNR).

## Measures and statistics

Project SNR (`stereo_mix_check.snr_db`, gain-fitted), SI-SDR, LSD (1/3-octave, 80 Hz–12 kHz) and
the 3–10 kHz brightness difference, all against `reference.wav`. Per splitter: Δ = value −
baseline M on the same part, scenario and separator. Band-weighted means, 90% band bootstrap
(4,000 draws, seed 20261019), leave-one-band-out range, every part listed. Side picks: blind
side right / wrong counts. Each scenario's absolute baseline SNR is shown beside R's (the +2 dB
step was calibrated at R's levels).

**The pan law's level effect.** A channel pick also lifts every panned guitar about 3 dB against
the centred bass, drums and vocals, whether or not the other guitars move away. SP isolates that
effect, so P's and LC's Δ are read beside SP's Δ in the main table.

**Checks before reading:** P, Mega-53, all 21: stored-stem left − P mono reproduces +1.55 within
0.01 dB; R: (c) within ±0.3 dB of M (the null; (a) is M there by definition, and (d) and (e) may
legitimately move).

## Decision rule (fixed now)

**Primary family (6 cells):** Mega-53 with the oracle side, primary population; splitters a, c,
d on P; c, d, e on LC (a = M there). HP is a ceiling and is never gated: a pass there was known
in advance.

- **A cell passes** when Δ SNR ≥ +2 dB, its Holm-adjusted (6 cells) one-sided bootstrap p for
  Δ ≤ +1 dB is below 0.05, and Δ LSD ≤ +1 dB. With 10 band clusters the percentile bootstrap is
  optimistic, so each passing cell's leave-one-band-out minimum is reported beside it. **Any
  pass (P or LC):** a known side is worth the +2 dB step in that layout. It goes to the user and the product session (who would supply the side), and
  any arm A test needs its own plan on synthetic-pan contexts: stage F's targets are recorded
  centred, so the reserved separation fine-tune Step 3 cannot test pan.
- **Stop:** for every gated cell, mean < +0.5 dB or 90% lower bound ≤ 0. Pan splitting alone is
  not the route at that scale.
- **Otherwise:** a gain to build on (effect sizes recorded, no verdict).

Secondary, descriptive, not gated: HP (the ceiling); blind (f) on the same cells (a pass there
would mean no hint is needed); htdemucs; SP; R; b; G and IRM anchors; all-21 rows.

## Budget and guards

- Separations: Mega-53 63 (3 scenarios × 21, ~86 s each when idle, about 1.5–2.5 h beside the
  renders), htdemucs 63 (about 20 min), centre model 42 crops (LC and R × 21; overlap 2 took
  11 s per 10 s on noise against 52 s at its default 8; an overlap-8 check on 3 LC parts is
  logged). Masks and scoring: minutes. About 2.4 CPU hours at nice 19, ≤ 4 threads, beside the
  running Step 1 render shards (the user's instruction for this job). Swap guard as the stereo
  check.
- **Time checkpoint:** after the first 6 Mega-53 separations the total is projected; if it
  exceeds 2.4 h, cut in this declared order: htdemucs, then SP for Mega-53.
- Zero renders. Disk ≤ 1.2 GB (10-s float32 crops of mixes, stems and centre outputs; contexts
  stay in memory). **Disk guard:** a `--disk-guard-gb` option, default 31; this job only runs
  with 26 (the user approved 25 for it on 2026-10-20 and asked to stop at 26), and the override is
  logged. Checked before every write.
- Weights: wesleyr36's MDX23C (no licence stated) under the user's 2026-10-20 approval of
  publicly released unlicensed weights.

## Limits

HP is a ceiling, not a layout to claim from. Synthetic pans on unity sums with no stereo reverb, delay, chorus, bus or master, so pan methods
look better here than on mastered records. Targets are mono. The alternating rule can split two
mics of one guitar across sides (Passing Ships, get-out-of-bed ElecGtr3). One mask width. The
centre model is out of domain on a guitar-only stem. Stage F reuse: separation measures only, no
arm scores read or chosen on; not one of the 7th/8th arm uses reserved for separation-finetune
Steps 1 and 3.

## Review and audit

One independent skeptical review of this plan before any separation (go with changes; all nine required changes applied: HP a ceiling and ungated, stereo guitars folded and panned, mics panned as one instrument, 10 bands, the R null on (c), the SP level control, the trimmed family and centre runs, the time checkpoint, the stop rule; plus the energy floor and the LOBO minimum); one brief audit of the
results that recomputes the key numbers from the saved per-part table.

## Amendment 1 (2026-10-20): the inter-channel coherence mask

**Source.** An outside report the user asked the cloud researcher to evaluate. This was the only idea
from it worth adopting, and the user approved testing it. **Cost:** zero renders, zero training,
zero new separation; it runs on the stored Mega-53 stems of every scenario (CPU, minutes).

**Why it might help where the ILD mask can't.** When two different takes sit hard left and hard right
at similar levels, their per-bin level ratio looks centred, so the ILD mask keeps them. Their phases
are unrelated, so they are incoherent. A single take panned anywhere stays coherent. This targets the
LC layout (centred lead against wide rhythms), and it needs no side for a centred target.

**Splitters (fixed now, not swept):**
- **g:** Γ(f,t) = Re{L·R*}/(|L|·|R| + ε), the cosine of the inter-channel phase difference. The
  soft mask 1/(1 + exp(−10(Γ − 0.5))) is applied to (a)'s STFT with the mixture phase. Same
  STFT (Hann 2048/512) and energy floor as (c).
- **gc:** g's mask times (c)'s ILD mask (σ = 0.3).
- **Anchor:** g on the class-perfect stem G, against G's mid.

**Family (3 cells, Holm):** Mega-53, oracle side, primary population: LC g, LC gc, P gc. The pass,
stop and gain-to-build-on rules, and the LSD guard, are the plan's, unchanged. Descriptive: R, HP,
SP, P g, all-21 rows.

**Checks before reading:**
- the R null: g within ±0.3 dB of M (R's stem comes from a mono sum, so it is coherent);
- (c) recomputed here matches `report.json` within 0.01 dB on P, LC and HP.

**Limits:**
- Our other guitars are mono takes folded and panned, so there is no stereo reverb or delay. This
  favours the mask, as real records would lower the lead's coherence.
- The alternating rule can put two mics of one guitar on opposite sides. Those stay coherent.
- τ and the slope are fixed, with one setting only.
- Output goes to `report-coherence.json`. `report.json` is not touched.

**Review and audit:** one independent review of this amendment and its code before the run, and one
brief audit of the results.
