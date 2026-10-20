# Better target-guitar separation: Step 0 and Step 1 results (2026-10-20)

Run under the [plan](separation-finetune-plan.md), ledger entry `separation-finetune`.
Development data only (stage F's 21 parts, 12 bands).

- **Code:** `learn/separation_ceiling.py` (Step 0), tests `tests/test_separation_ceiling.py`;
  the YG arm in `learn/perfect_sep_arm.py`, tests `tests/test_perfect_sep_arm.py`. The per-part
  track classes are in [separation-track-table.json](separation-track-table.json).
- **Data:** `~/ndsp-presets/learn/separation-finetune/` (Step 0: `step0-report.json`,
  `step0-parts.json`, `step0-check.json`, the oracle stems in `G/`);
  `~/ndsp-presets/learn/arm-a-mega53/F-perfect-sep/YG/` (Step 1's partial records).
- **Renders:** Step 0, 0. Step 1, **2,666 recorded** (48 of 126 directions finished, plus 26
  priming renders) before the user's decision stopped it. The three directions in flight at the
  stop were not saved, so at most about 160 more renders ran without a record.
- **Audit:** Step 0's six decision numbers were checked by an independent auditor and confirmed.

## Headline

- **The other guitars limit separation, not Mega-53's training.** On the 19 parts that have
  another electric guitar, the other guitars are about **5.5 dB louder than the target** in the
  crop (I +5.52 dB [+3.70, +7.24], band-weighted). The louder they are, the worse Mega-53's stem
  (Spearman −0.85 across parts).
- **A perfect "all electric guitars" separator would barely help.** The class ceiling G beats
  Mega-53 by only **+0.30 dB** of SNR (band median; +0.22 to +0.37 leaving one band out; above 0
  in 12 of 12 bands). That is the most a class fine-tune of Mega-53 could ever reach, because the
  other guitars are inside the class.
- **No free test-time fix helps.** All four fixes lower SNR against Mega-53 and none survives
  Holm's correction.
- **Step 1 was stopped after 2,666 renders by the user's decision not to train separators.** There
  is no YG − M reading. The partial records are kept but are not to be analysed or quoted.
- **The class fine-tune (Steps 2–3) is retired.** See [the user's decision](#the-users-decision).

## Step 0 (zero renders)

**Baselines reproduced.** Mega-53's stored stem reaches **1.6725 dB** SNR against the target
(band-weighted mean), htdemucs **0.6899 dB**, matching the stored 1.67 / 0.69 dB.

**R0a, class headroom: +0.296 dB → Step 1 (as declared).** The band median of SNR(G) − SNR(M):
- leave-one-band-out range +0.221 to +0.372; 12 of 12 bands above 0;
- without the 2 single-guitar parts (10 bands): +0.219.

G's band *means* (about +39.6 dB) must not be quoted. On the two single-guitar parts G is the
target itself, so its SNR is effectively unlimited and swamps the mean. The median is the declared
reading for this reason.

**R0b, the free fixes: none helps.** SNR change against Mega-53, band-weighted, 90% interval:

| Fix | What it is | SNR change (dB) | Holm |
|---|---|---|---|
| T1 | Wiener re-mask of the mix with Mega-53's stem | −0.25 [−0.47, −0.07] | fails |
| T2 | T1 plus one more EM pass | −0.35 [−0.66, −0.10] | fails |
| T3 | half Mega-53, half htdemucs | −0.55 [−1.29, −0.06] | fails |
| T4 | Mega-53 below the crossover, htdemucs above | −0.30 [−0.90, +0.00] | fails |

T3 and T4 do brighten the stem (+2.0 and +1.2 dB at 3–10 kHz), but they cost SNR.

One caveat for T1 and T2: the stored Mega-53 stem is not at mix scale (it is 1.14–1.44 times too
loud), and the Wiener masks were built from it as stored. That skews the masks, so T1 and T2 may
be a weak test of the Wiener idea itself.

**R0c, descriptive:**
- **I**, the other electric guitars' energy over the target's in the crop: +5.52 dB
  [+3.70, +7.24] over 19 parts (10 bands). I counts the target's *own* double-track as "other
  guitar". On Magilla, most of its +1.3 dB comes from that double.
- **X**, the share of a part's sections where the other guitars sit 10 dB or more below the
  target: **0 on 18 of 19 parts**. An "exposed passage" hint would almost never exist.
- I does not predict arm A's gains (Spearman with M − H +0.20, with YT − M −0.15; both p > 0.4).
- G_noDT − G is 0 on every part. That does **not** mean the mixes have no double-tracks. Magilla's
  mix holds the target's own double (`15_ElecGtr1DTAmp`) and another guitar's double
  (`19_ElecGtr2DTAmp`), which is near-silent in the crop.
- G_mic equals the reference on every part: the declared mixes hold only the reference mic.

**YT − M, from the stored arm A records: −0.0484 [−0.0706, −0.0261]** (band-clustered 90%, 11 of
12 bands negative). This is what perfect one-guitar separation would still add over Mega-53 in
arm A.

## Step 1 (stopped)

Step 1 ran arm A with the class-oracle stem G (arm YG) to decide between the class fine-tune and a
separator told which guitar to extract. Its only purpose was that choice. After the user's
decision, both options involve training a separator, so the step was moot and was stopped. It used
2,666 recorded renders (48 of 126 directions). **There is no YG − M reading,** and the partial
records must not be used for one.

The run used a disk guard of 25 GB instead of 31 GB (the user's approval, for this run only),
through the new opt-in `--min-free-gb` flag. The default stays 31 GB. Free disk stayed at about
30 GB.

## The user's decision

On 2026-10-20 the user decided not to train any separator: it is too specific and needs research
they want to avoid. Renting machines is not acceptable either. So:
- the class fine-tune (Steps 2–3) is retired;
- so are a conditioned one-guitar separator that would need training, route 6 of the
  [single-guitar research](research/single-guitar-separation-2026-10.md) (a fine-tune on synthetic
  multi-guitar mixes), and route 5 (solo-region adaptation, which also trains weights per song).
  Step 0's X says the regions route 5 needs barely exist on stage F anyway;
- existing checkpoints, DSP splitters (pan or level masks, Wiener-style filters) and Moises (in
  development) remain allowed.
