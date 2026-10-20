# Pan side as a separation hint: stage F synthetic-pan screen results (2026-10-20)

Run under the [plan](stereo-side-plan.md) after one independent review (go with changes, all
applied). Development only, zero renders. Code: `learn/stereo_side_screen.py`. Data:
`~/ndsp-presets/learn/stereo-side-screen/` (`report.json` with every part, `sep/`, `centre/`,
`logs/`, `log.json` with the logged disk-guard override). Figures are band-weighted means with 90%
band-bootstrap intervals (4,000 draws, seed 20261019) on the **19 parts in 10 bands that have
another electric guitar**, unless marked. Δ is the gain in project SNR (gain-fitted, dB) over the
mid of the same Mega-53 stereo stem.

## Headline

- **Verdict: a gain to build on. No splitter clears +2 dB, and the route is not stopped.** Two
  known-side splitters come close:
  - keeping the target's channel when it is panned at −0.6 (P, a): **+1.50 [+0.78, +2.33]**;
  - the MDX23C centre model when the target is centred against hard-L/R rhythms (LC, e):
    **+1.35 [+0.31, +2.49]**.
  Neither reaches +2 dB, and neither is clear of +1 dB after Holm (p 0.93 and 1.0).
- **Without the side, every blind method loses.** The pan histogram's peak finds the *other*
  guitars, because they are louder: it named the target's side on 5/19 parts in P, 4/19 in LC
  and 0/19 in HP. Blind picks and blind masks cost −0.01 to −1.0 dB.
- **The ILD mask and the Wiener step don't help.** The mask gains +0.6 to +0.9 dB, below the plain
  channel pick wherever a pick exists. Wiener on top cancels most of that gain and adds 6 to 11 dB
  of LSD.
- **Hard panning is a ceiling, not a claim.** With the target hard left and every other guitar hard
  right (HP), the target's channel gains +6.88 [+5.69, +8.05]. With no reverb or bleed in our sums,
  that channel holds no other guitar.

## Checks

- P reproduces the stereo check: on all 21 parts, the target's channel minus the mono-fold stem is
  +1.554 dB, against +1.554 stored.
- R null: the ILD mask against mid is −0.006 dB (limit ±0.3).
- Rebuilt contexts: R's mid matches the stored mono, and P matches the stored P context. The
  largest difference on every part is under 5e-8.
- Centre model: overlap 2 against its default overlap 8 on 3 LC parts gives output agreement
  of 17–28 dB SNR and target SNR within 0.08 dB.
- Pan law's level effect: SP puts the target and every other guitar at −0.6. Its channel pick
  gains only +0.02 [+0.00, +0.05]. So the P and LC gains come from the side, not from lifting the
  guitars above the centred drums and bass.

## Results (Mega-53, oracle side, 19 parts)

| scenario (target / others) | baseline M, dB | a. pick | c. ILD mask | d. mask + Wiener | e. centre model | f. blind pick | f. blind mask |
|---|---|---|---|---|---|---|---|
| R (0 / 0, as recorded) | 0.87 | = M | −0.01 | −0.08 | −0.02 | −0.02 | −0.01 |
| P (−0.6 / ±0.6) | 0.90 | **+1.50 [+0.78, +2.33]** | +0.60 [+0.28, +0.92] | +0.08 [−0.16, +0.33] | not run | −0.01 | −0.27 |
| LC (0 / ±1) | 1.21 | = M | +0.76 [+0.31, +1.27] | +0.28 [−0.15, +0.77] | **+1.35 [+0.31, +2.49]** | −0.65 | −0.99 |
| HP (−1 / +1), ceiling | 0.72 | +6.88 [+5.69, +8.05] | +0.86 [+0.29, +1.45] | +0.17 | not run | −0.34 | −0.63 |
| SP (−0.6 / −0.6) | 1.05 | +0.02 | −0.01 | −0.17 | not run | +0.02 | −0.01 |

Absolute SNR is the baseline plus Δ. For example, P's pick reaches about 2.4 dB, against 0.87 dB
for the recorded mix's stem.

**The gate.** Six cells were gated: P a, c, d and LC c, d, e. A cell passes at Δ ≥ +2 dB with a
Holm-adjusted p(Δ ≤ +1 dB) below 0.05 and Δ LSD ≤ +1 dB.

| cell | Δ SNR | Δ SI-SDR | Δ LSD | leave one band out | Holm p | reading |
|---|---|---|---|---|---|---|
| P a | +1.50 [+0.78, +2.33] | +4.37 | −0.46 | +1.14 to +1.66 | 0.93 | gain to build on |
| P c | +0.60 [+0.28, +0.92] | +2.38 | +0.53 | +0.52 to +0.72 | 1.0 | gain |
| P d | +0.08 [−0.16, +0.33] | +0.46 | **+6.70** | 0.00 to +0.16 | 1.0 | stop side |
| LC c | +0.76 [+0.31, +1.27] | +2.19 | +0.38 | +0.59 to +0.86 | 1.0 | gain |
| LC d | +0.28 [−0.15, +0.77] | +0.41 | **+8.02** | +0.05 to +0.39 | 1.0 | stop side |
| LC e | +1.35 [+0.31, +2.49] | +2.40 | −0.32 | +0.92 to +1.61 | 1.0 | gain to build on |

No cell passes, and not every cell is on the stop side, so the result is **a gain to build on**.

**Part by part.** Every row is in `report.json`.
- **P, pick:** the gain spreads widely. The largest are magilla +4.7, Gym Hours +3.8 and Let's
  Dance 3 and 4 (+3.4, +3.2). Passing Ships ElecGtr2/4 and femme are near 0.
- **LC, centre model:** it either helps a lot or hurts. It gains +5 to +6 dB on Passing Ships
  ElecGtr2, colour-me-red elecgtr03 and femme. It loses up to 1 dB on magilla, Let's Dance and the
  Wickerman parts.
- **The 2 parts without another electric guitar:**
  - She's Gone: the pick gains +0.86 in P.
  - Strangest Places: every LC splitter loses (centre model −2.8).

**Anchors (oracle, no separator).**
- **A class-perfect stem** (every electric guitar, nothing else):
  - with a pick in P: 3.86 dB;
  - with the ILD mask in LC: 3.62 dB, against 2.22 for its mid.
  These sit about 2–3 dB above Mega-53's mid, and about 1–1.5 dB above Mega-53's best known-side
  splitter (P pick 2.40 dB, LC centre model 2.56 dB).
- **The ideal single-channel mask on the mix:** 3.35 dB (R), 4.87 (P) and 3.95 (LC).

**Not run.**
- **htdemucs.** The declared time checkpoint (first 6 Mega-53 runs) projected about 2.7 h against
  the 2.4 h budget, so htdemucs was cut first, as declared.
- **The researcher's D layout** (applies to one part).
- **The centre model on P, HP and SP** (dropped by the review).

## What it means

- **A known side is the only thing that worked, and it's worth about +1.4 dB, not +2.** That
  holds for the side's channel at a partial pan and for the centre model on a centred lead.
  Step 0 found, on the recorded (centred) mixes, that a perfect class stem beats Mega-53 by only
  +0.30 dB and that the free fixes are all negative. So none of the zero-training routes tried so
  far reaches the +2 dB step.
- **The side has to come from outside the audio.** That means the arrangement's `pan` field or the
  user's ear. The obvious blind rule picks the louder guitars. Post hoc, "the opposite of the
  peak's side" would have been right on 16/19 parts in HP (the peak sat at centre on the other 3),
  but on only 5/19 in P, where the peak sat at centre on 9. It also relies on the other guitars
  being louder, which holds on these sessions (+5.5 dB) and is unknown for real songs.
- **These numbers flatter pan.** They come from synthetic pans on unity sums, with no stereo
  reverb, delay or master. Real records would score lower.
- **Nothing here feeds arm A directly.** Stage F's targets are recorded centred. Any arm A test of
  pan needs its own plan on synthetic-pan contexts. At about +1.4 dB it would likely read a tie. The
  separation plan sets +2 dB as the step a 21-part arm A test can probably see: the test resolves
  about −0.03, and Mega-53's +1.0 dB over htdemucs bought about −0.017
  ([separation-finetune plan](separation-finetune-plan.md)).
- **For the product session.** If a song's arrangement file or the user names the guitar's side,
  keeping that side of a stereo Mega-53 stem costs nothing and gains about 1.5 dB here at ±0.6.
  The centre model is the option for a centred lead, at one ~10-s CPU pass per crop.

## Cost

- Separations:
  - Mega-53: 63 stereo separations (LC, HP and SP × 21), 5,300 s wall plus about 18 s per context
    build.
  - Centre model: 45 passes, 587 s.
- Scoring took minutes. Total about 2.1 CPU hours at nice 19 and 4 threads, beside another
  session's jobs.
- Zero renders. Disk 0.40 GB.
- The disk guard ran at 26 GB (the user approved 25 for this job and asked to stop at 26); both
  overrides are logged. Free disk stayed at or above 27.8 GB.
- Weights: wesleyr36's MDX23C phantom-centre model, from the MSST v1.0.10 release (no licence
  stated; the user's 2026-10-20 approval), hashed in the code.

## Audit

One brief independent audit recomputed the six gated cells from `report.json` with its own band
bootstrap and Holm, and spot-checked SNRs from the saved stems on 3 parts (equal to 4 decimals).
**Confirmed with corrections.** Every gated number, the verdict, the blind counts, the P
reproduction, the R null and the per-part extremes match. Corrections, applied above: SP's pick
+0.02 (not +0.03) and HP's blind mask −0.63; the post hoc "opposite side" rule's counts (16/19
HP, 5/19 P); the Step 0 class-ceiling number kept apart from this screen's anchors; the arm A
resolution sentence.

## Amendment 1: the inter-channel coherence mask (2026-10-20)

Run under [amendment 1](stereo-side-plan.md#amendment-1-2026-10-20-the-inter-channel-coherence-mask)
after one independent review (go with changes, all applied). Zero renders, no training, stored
Mega-53 stems only. Data: `~/ndsp-presets/learn/stereo-side-screen/report-coherence.json`.
Primary population, 19 parts in 10 bands; Δ SNR against the stem's mid, dB.

**Verdict: a small gain to build on, below the existing splitters. No cell is near +2 dB.**

| cell (gated, Holm over 3) | Δ SNR | Δ LSD | leave one band out | Holm p | reading |
|---|---|---|---|---|---|
| LC g | +0.35 [+0.15, +0.59] | +0.09 | +0.26 to +0.41 | 1.0 | stop side (mean < +0.5) |
| LC gc | +0.69 [+0.16, +1.28] | +0.45 | +0.46 to +0.79 | 1.0 | gain to build on |
| P gc | +0.17 [−0.12, +0.46] | +0.97 | +0.08 to +0.27 | 1.0 | stop side |

- **It doesn't beat what we have.** On LC the coherence mask alone gains +0.35. That is under the
  ILD mask (+0.76) and the centre model (+1.35). Multiplying the two masks (+0.69) adds nothing
  over the ILD mask alone.
- **Even on perfect class separation it is small.** On the class-perfect stem G, coherence gains
  only +0.56 [+0.13, +1.01] on LC. So the cap is in the idea, not in Mega-53's stem.
- **Its one good property is that it barely changes the tone.** On LC, g moves LSD by +0.09 and
  treble by −0.07 dB. The ILD mask moves them by +0.38 and −1.21.
- **Descriptive rows:**
  - P g: +0.46 [+0.20, +0.75].
  - SP g: +0.01.
  - HP g: +0.93. This row is invalid by construction (the target is hard-panned).
- **Checks passed:**
  - the R null for g is −0.004 dB;
  - (c) recomputed matches `report.json` on P, LC and HP (0.603, 0.763, 0.863).
- **Limit:** Γ here is the per-bin phase difference with no smoothing. A smoothed-coherence
  variant is untested, but the class-perfect anchor's +0.56 leaves it little room.
