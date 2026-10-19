# Mega-53 as default, the stereo check and mix vs raw track: results (2026-10-19)

Run under the [plan](stereo-and-mix-check-plan.md) after one independent review (go with changes,
all applied). Development only, zero renders: stage F's 21 parts in 12 bands. Figures are
band-weighted means with 90% band-bootstrap intervals (4,000 draws, seed 20261019); no pass/fail
bars. Code: `learn/stereo_mix_check.py`. Data: `~/ndsp-presets/learn/stereo-mix-check/`
(`report.json` per part, `contexts/log.json` with each part's panned tracks, `logs/`).

## Why

The user listened to the separation samples (`~/ndsp-presets/listening/separation-samples-1/`).
They heard Mega-53 as much better overall, and better than htdemucs on Gym Hours, Today's The Day
(drum leakage), magilla (near-silent passages) and She's Gone (many leaks). Mega-53 also split
two guitars that htdemucs merged. On Signs ElecGtr3 and get-out-of-bed elecgtr2 both separations
carry a guitar that the true track doesn't have. magilla's raw amp track has a distortion that the
user can't hear in either separation, or in the mix.

## Task 1: Mega-53 is the ML default

- `learn/separate.py`: `DEFAULT_SEPARATOR = "mega53"`, `guitar_separator(name)` (Mega-53's
  pruned head or htdemucs on the CPU).
- Arm A (`learn/arm_a_mega53.py`): `separate` and `rebuild` take Mega-53 without `--sep`.
- The direct model (`learn/direct_existing.py`): `--sep`, Mega-53 by default. The stored
  htdemucs run stays where it is and `--sep htdemucs` reproduces it; Mega-53 writes to
  `direct-existing/sep-mega53/`, and `render` refuses predictions made with another separator.
  D_existing was trained on htdemucs stems, so a Mega-53 run of it is not a separator reading.
- The finished known-answer pilot B1 stays pinned to htdemucs, its declared separator.
- Nothing stored changed and nothing was rerun.

**The product uses no separator.** `scripts/` and `skills/` don't import demucs, Roformer or
torch. `generate` measures the song itself as a `mix` (`scripts/fingerprint.py`), or a stem the
user supplies (`separated_stem`, confidence 0.55). `analysis/io.py` folds every file to mono with a
channel mean. The product session can decide whether to add a separator.

## Task 2: the stereo check

**What the data allows.** The stored contexts and stems are mono. Every context is a unity sum of
raw tracks, and all 21 target amp tracks are mono. A stereo sum with the native channels (**R**)
therefore puts every target dead centre: its mid is the stored mono, which was checked to within
1.5e-7. Only the stereo tracks (overheads, rooms, keys, and three other guitars) differ between L
and R. To ask the panning question, a declared scenario (**P**) pans the target to −0.6 (left) and
the session's other mono guitars alternately to ±0.6. The stereo path was checked against the
stored stem: a dual-mono input reproduces it (max |Δ| 1.8e-7 for Mega-53, 2.4e-7 for htdemucs).
Each scenario's gains are against its own mono.

SNR gain over mono in dB (gain-fitted stem SNR against `reference.wav`):

| mode | Mega-53, R | htdemucs, R | Mega-53, P | htdemucs, P |
|---|---|---|---|---|
| mono SNR (level) | 1.67 [0.83, 2.68] | 0.69 [0.41, 1.06] | 1.56 [0.80, 2.48] | 0.62 [0.36, 0.95] |
| left (the target's side in P) | −0.12 [−0.43, +0.07] | +0.07 [+0.01, +0.15] | **+1.55 [+0.85, +2.34]** | **+1.17 [+0.58, +1.87]** |
| right | −0.12 [−0.36, +0.02] | +0.07 [−0.03, +0.20] | −0.97 [−1.44, −0.61] | −0.46 [−0.68, −0.28] |
| mid | −0.06 [−0.24, +0.05] | +0.11 [−0.00, +0.28] | +0.24 [+0.04, +0.56] | +0.28 [+0.04, +0.56] |
| side | −1.64 [−2.62, −0.83] | −0.68 [−1.02, −0.41] | +0.35 [−0.02, +0.81] | +0.45 [+0.19, +0.77] |
| pan-matched, **ORACLE** | −0.06 (= mid) | +0.11 (= mid) | **+0.89 [+0.49, +1.34]** | **+0.74 [+0.34, +1.22]** |
| blind, stem RMS weights | −0.07 [−0.25, +0.05] | +0.11 [−0.01, +0.28] | **+0.27 [+0.00, +0.69]** | **+0.31 [+0.04, +0.63]** |
| blind pick, louder stem channel (post hoc) | −0.16 [−0.46, +0.02] | +0.04 [−0.04, +0.13] | +0.44 [−0.18, +1.16] | +0.50 [+0.06, +1.00] |

- **As recorded, stereo doesn't help on average.** With the target centred, the mono fold is as
  good as any channel mode: band means within ±0.16 dB for both separators. Strangest Places cuts
  both ways: stereo mid is 1.1 dB worse than mono on Mega-53 and 1.1 dB better on htdemucs.
  Gym Hours' right channel is 0.4 dB worse on both.
- **When the guitar is panned, its own side helps a lot.** Separating stereo and keeping the
  target's channel gains about 1.2–1.6 dB, as much as the step from htdemucs to Mega-53 in mono
  (+1.0 dB here). The oracle pan weighting gains less (+0.7 to +0.9), because the far channel
  adds more backing than target. The pick-the-side oracle is the "left" row.
- **The blind estimate is no better than a coin flip.** A separated stem's own L/R balance
  favoured the target's side on 12/21 parts (Mega-53) and 10/21 (htdemucs), with a median blind
  pan of about 0. The stems carry the other guitars, panned the other way at similar level. The
  blind weights gain only +0.3 dB. **Under this scenario** the product can't simply read the pan
  from the stem. A mix whose other guitars are not mirrored could behave differently. The
  blind-pick row is post hoc and doesn't feed this reading.
- **The two "other guitar leaked" parts.** In R, stereo changes nothing (≤ +0.1 dB). In P the
  target's side removes some of the opposite-panned guitar: Signs +0.5 (Mega-53) and +1.0
  (htdemucs), get-out-of-bed +0.9 and +0.9. In P they sit near the median; nothing marks them out.
- **Per part (P, left):** the largest gains are on magilla (+5.0 / +4.7), Let's Dance 3 and 4
  (+3.7 / +3.1, +3.4 / +2.5), Gym Hours (+3.4 on Mega-53) and She's Gone (+2.9 on Mega-53). The
  smallest are at −0.15 to +0.3: Passing Ships ElecGtr2 and ElecGtr4, Wickerman 7, It Was My
  Fault, femme, and Strangest Places on Mega-53 (−0.01). Gym Hours on htdemucs (−0.15) and
  Passing Ships ElecGtr4 on htdemucs (−0.03) lose slightly on their own side. Every row is in
  `report.json`.
- **Caveats.** P is one declared pan model, not a measurement of real songs. The rule can split
  two mics of one guitar across the sides (Passing Ships, colour-me-red's acoustic). Separating L
  and R as two dual-mono inputs was not run; the models saw both channels at once.

## Task 3: mix vs raw track

- **No session carries a mix, master or bounce.** All 21 folders hold only the tracks and a
  Readme. Our "mix" is a unity sum of the raw tracks, so on our data the in-song guitar **is** the
  raw amp track. Checked on every part: mix − backing − reference ≤ 2.4e-7. This holds only for
  our contexts. It says nothing about mixed and mastered songs, which we can't measure without
  masters.
- What the user hears as missing (magilla's distortion) is therefore not mix processing. It is
  masking by the other instruments, plus what separation drops. Even the best linear recovery from
  the mix, an oracle 2,048-tap least-squares filter fitted on the other half of the crop, loses it on
  magilla: 7.7 dB less brightness (the 3–10 kHz over 0.2–3 kHz ratio) and 2.0 dB more crest than
  the raw track. Mega-53 loses 19.4 dB of
  brightness, htdemucs 6.3 dB. magilla's raw track is also the darkest of the 21 (3–10 kHz is
  34.7 dB under 0.2–3 kHz), so its fizz is a small, easily masked share.
- **The recovered guitar differs from the raw track on almost every part:**

| against the raw track | LSD, dB | crest diff, dB | brightness diff, dB | parts > 3 dB LSD | brightness loss > 1 dB |
|---|---|---|---|---|---|
| LS from mix (oracle, held out) | 4.92 [3.85, 6.04] | +1.31 [+1.03, +1.59] | −1.99 [−3.35, −0.63] | 18/21 | 10/21 |
| Mega-53 stem | 9.35 [7.59, 11.17] | +0.81 [+0.43, +1.16] | −3.30 [−6.55, −0.48] | 19/21 | 15/21 |
| htdemucs stem | 7.30 [5.77, 8.94] | +1.36 [+0.93, +1.83] | −0.41 [−2.63, +1.72] | 18/21 | 8/21 |

  The stems are peakier than the raw track (a higher crest reads as less compressed or less
  saturated). Mega-53 is darker, with the largest losses on Russian Cream (−20.7 dB) and magilla.
  Bleed adds transients, though, and separator high-frequency loss looks like lost fizz, so these
  measures can't separate "less distortion" from "less bleed" or "duller separation". Mega-53's
  higher SNR and larger LSD don't conflict: LSD weighs every 1/3-octave band equally, including
  quiet ones that SNR barely sees.
- **For the yardstick.** We judge against the raw track. On our summed mixes that is the in-song
  guitar exactly, so the yardstick is right for them. On real songs the product's target is the
  guitar after mix EQ, compression and mastering. That gap is unmeasured here. It would be a
  systematic difference that a preset search scored against the raw track can't see. Compression
  and limiting depend on level, so it need not be a fixed offset. Measuring it needs sessions
  that ship the released mix: Cambridge MT offers mix previews on its site, which were not
  downloaded here.

## Audit

One brief independent audit wrote its own SNR, band bootstrap and Task 3 measures and
recomputed the results from the saved stems. **Confirmed with corrections.**
- Every P mode in the table, and R's mid, matches to 0.01 dB for both separators. Per-part
  values agree with `report.json` within 1e-3.
- The left-favouring counts (12/21 and 10/21) and mix − backing − reference ≤ 2.4e-7 match.
- magilla's and two other parts' LSD and brightness match exactly.
- Corrections, applied above: the per-part lists of the smallest and losing gains; Strangest
  Places' opposite R effect on htdemucs and Gym Hours' right channel; the blind estimate called
  coin-flip and limited to scenario P; "fixed offset" reworded to a systematic difference; the
  brightness and filter wording.
