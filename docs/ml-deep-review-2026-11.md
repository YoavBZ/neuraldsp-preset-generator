# Deep review of the ML flow (2026-11-05)

**Status: review only.** Zero renders, zero training. CPU inference on stored checkpoints and analysis of stored files.
Nothing here is adopted: the ML session owns `learn/`, the judge and the datasets, and declares what it takes. Figures are
in knob units or linear probes unless marked; none is a read of sound on a real song.

**Why.** The user asked for a deep review of every fundamental part of the flow, to find the best model, scoring system,
features and feature extraction, kept in sync with the ML session.

**How to read a finding.** Each carries who verified it:
- **[audited]**: recomputed on stored data by an independent auditor, with its own code.
- **[code]**: confirmed by reading the code.
- **[reviewer]**: measured by one independent reviewer, not recomputed.

Line numbers are at commit d1cef7d.

**Data.** BKS and GOAT labels and inputs; W's training-row features and stems, and FS rows without the NS sessions, by the
features reviewer; 33 `ks-ceiling-extend` directions on non-V-real parts; the `judge-ear` and `judge-v5` ear pages. W's `best`
checkpoint was chosen on NS loss, which every read of W inherits. Not read: V-real, the NS songs, the panel, the captures or
record match, except as listed under "Data touched outside the limits".

## The short answer

| Part | Best known now | What is wrong | Next test |
|---|---|---|---|
| **Scoring** | J0 stays. No candidate beats it on both ear pages. | Weak near real distances: removing a 6 dB bell reads about −0.03 to −0.04 at d 4, at the edge of what is read as meaningful. | Report `tonal` beside `distance`, stratified by d_S, on stored judged rows. |
| **Reading skill** | Own-against-swap and fold-demeaned, recording-level r. | Loss against a lookup flips with the comparator; pooled r is biased down; BKS's rows are weak (below). | In N1 already. |
| **Model** | FT stands until a read by score. Next candidate: FT corrected to searched heads, with S written on the rest (N1's first read, F55 pending, is ahead by knob on GOAT). A ridge on pooled mel statistics is the baseline any network must beat; state its input. | Unsearched heads are labelled as S, mics dominate the loss at FT's start, and the amp head fits noise. | N1's read by score. Ridge by sound, about 670 renders. |
| **Features** | 96-band log-mel is enough for tone. For drive nothing is shown better where drive actually varies. | W's skill rests on long-term colour, which transfers worst. | Tone from the long-term spectrum; a drive read on crunch before splitting inputs. |
| **Feature extraction** | None is good on stems yet. | Models train on P2b and read X-LANCE stems (domain AUC 0.997). A lead: stems may lean toward the dominant other guitar. | Train or align on real stems; test the lead by labelling the dominant guitar. |
| **Labels** | Search v2 (N2): adopted by its declared rule, about 30% fewer renders, not shown more reliable. | v1: 52 evaluations, step stuck at 0.25, 8 dB input-gain resolution. | Reliability of the capture labels. |
| **Evaluation** | t intervals, 20+ bands, an answer-swap placebo. | Percentile bootstrap covers 82%, not 90%, on 7 clusters. L2's sizing gives about 56% power. | Swap the interval (no render). Resize L2. |

**FT reads per track, weakly, most robustly on GOAT's cab, from mic position and distance about equally.** On held GOAT rows its answers
follow labels beyond their cell. On raw units its drive read separates extremes rather than grading them, and its tone read does not
survive removing range-limit labels. Head-standardised and without those labels, drive (+0.111, p .012) and cab (+0.097, p .026) hold and
tone does not (+0.059, p .144). BKS cannot decide it. Answers vary 10–30% as much as labels. Whether any of it can be heard is unknown.
FT's fall in real-row loss was not evidence of reading.

## 1. Scoring

**No arithmetic error in J0's main path** [reviewer]. Mel matrix, framing, lag and DI timeline, t tables and log-ratio
arithmetic are correct. Numerics sit far below the 0.03–0.05 read as meaningful: level, polarity and 16-bit 0.0000, DC at most
0.0002, frame grid SD at most 0.0011, lag ±36 samples p90 at most 0.004 at d of 2.7 or more, resampling at most 0.005.

**J0 is close to quadratic in a tonal error, and sensitivity falls as about 1/d²** [audited] (`analysis/aligned.py:403-410`).
Each cell already carries a spread of about 5 dB, so a small error adds almost nothing. Measured on stored renders standing in
for recordings, ln ratio on removing a known error:

| d | 3 dB bell, 1.6 kHz | 6 dB bell, 1.6 kHz | 6 dB shelf above 4 kHz |
|---|---|---|---|
| 2.73 | −0.027 | −0.088 | −0.111 |
| 3.91 | −0.010 | −0.042 | −0.063 |
| 6.05 | −0.003 | −0.013 | −0.034 |

- So "level with S" says little about errors of this size at real distances, which supports the user's reading of F54: a
  similar score need not mean a similar sound. Whether this is what happened on F54's two clean parts is untested; those parts
  are held out.
- Band means of log ratios lean on the closest parts.
- `tonal` moves 2–7× as far for the bell on most pairs (not always for the shelf: −0.052 against −0.063 at d 3.91), and
  `knob_ceiling.judge:490` discards it. Report it beside `distance`. It is not a replacement: see the next table, where a
  long-term spectrum alone tracks the ear worst on one page.

**Candidate measures against the ear** [audited; declared first; in-sample; one listener; 48 render-against-render items].
Spearman with the ear:

| Measure | All | Drive, tone, cab | judge-ear | judge-v5 |
|---|---|---|---|---|
| J0 | +0.60 | +0.60 | +0.49 | +0.73 |
| M1, DI-to-output non-linear residual | +0.32 | +0.31 | +0.23 | +0.45 |
| M2, DI-free spectral valley-to-peak | +0.54 | +0.49 | +0.63 | +0.49 |
| M3, long-term spectrum only | +0.12 | +0.57 | −0.10 | +0.45 |

- A distortion measure does not explain the ear here. M1 passes its control (linear filter −42.9 dB, clipper −13.2 to −2.5 dB; the control was not recomputed).
  The declared prediction failed: it moves 2.14 on clean against 0.67 on crunch on the judge-ear page, the reverse of what was
  heard, and agrees on judge-v5.
- M2 is unfitted and leads on judge-ear (+0.14 [−0.05, +0.36]) but trails on judge-v5 (−0.24 [−0.45, −0.05]).
- These are single-control steps between renders. A recording against a render on clean parts is a different question, left open.

**Pause noise, treble and floors** [reviewer]. Hiss in 10–20% gaps costs +0.09 to +0.31 (`aligned.py:436`). Treble above the top
scored band costs exactly 0 (`:454`). The floor's asymmetry flips sign with the median (`:477`). Three refusal rules differ
(`knob_ceiling.py:491`, `pipeline_fix.py:4656`, `:5671`).

**Measure DI** [reviewer, one DI]. `own.mean()` covers bins to 24 kHz, so the ±15 dB clip hits 59% of 80–6000 Hz bins, 3% if
band-aligned (`knob_ceiling.py:374`, `direc_check.py:52`). Its effect on renders is unmeasured.

## 2. Reading skill: how to measure it

- **Held-fold r must be demeaned within fold** [audited]. Pooling held folds shifts r down, since each fold's centre comes from the
  other folds. FT's real shift, pooled to demeaned at row level: GOAT +0.015, +0.147, +0.100; BKS +0.026, +0.280, +0.205. W, with no
  fold dependence: −0.019 to +0.060. The worst case is an answer that hears nothing, which scores −0.13 to −0.51 pooled. On pooled terms
  this review reproduces the labels reviewer's GOAT tone −0.027, so that choice explains the difference. The model reviewer's
  "within-cell-and-dataset" r looks pooled the same way (not re-run), so its +0.27 must not be a gate.
- **Searched-head NLL against a lookup decides nothing** [audited]. FT beats a single Gaussian (BKS −0.064 [−0.124, −0.003];
  GOAT −0.078 [−0.111, −0.044]) and loses to a no-audio 4-component mixture (+0.462 [+0.386, +0.538]; +0.271 [+0.171, +0.370]),
  because labels pile on the search's 0.25 grid.

**The reads, on the real readout** [audited: 8 of 8 logged losses and 334 stored answers reproduced]. Fold-demeaned, one value per
recording, upper-tail p. GOAT: 2,000 permutations, 90% item bootstrap. BKS: exact joint permutation over 2,304 arrangements.

| Set, model | Drive | Tone | Cab | Own − swap, total |
|---|---|---|---|---|
| GOAT FT | +0.088 (.003) [+0.015, +0.159] | +0.121 (.018) [+0.028, +0.224] | +0.191 (<.001) [+0.126, +0.263] | −0.185 [−0.236, −0.134], 103 of 130 |
| GOAT W | +0.096 (.006–.009) [+0.029, +0.163] | +0.222 (<.001) [+0.143, +0.301] | −0.086 (lower tail .007) [−0.143, −0.027] | −0.061 [−0.125, +0.004], 72 of 130 |
| BKS FT | +0.149 (.145) | +0.215 (.053) | +0.510 (.0017) | −0.489 on 2 reciprocal pairs, undecided |
| BKS W | −0.268 (.917) | +0.219 (.046) | −0.132 (.984) | −0.124 on 2 reciprocal pairs, undecided |
| BKS no-audio rig table | | | +0.507 (.0035) | |

- **BKS cannot show reading on cab.** BKS holds out DIs, not rigs: 13 of 14 recordings share song and rig letter with training rows,
  and a table with no audio matches FT (correlation between them +0.27, FT partial +0.45). So FT is not purely a lookup, but the
  figure cannot be read as reading a new rig. GOAT's +0.19 is the size to quote.
- **BKS own − swap is undecided:** by pair −0.728 and −0.251, t(1) [−1.99, +1.02]. Two pairs are all there is.
- **GOAT, without the 17–38% of labels at a range limit:** FT drive +0.035 (.21), tone +0.045 (.23), cab +0.113 (.016); W tone +0.232
  (<.001). Truncating on the label lowers r, so this is not "no read": on raw units FT's GOAT drive separates extremes rather than grading them.
  W's tone survives and FT's does not. BKS does not share this (+0.28, +0.22, +0.53).
- **Head-standardised GOAT** (r pools raw units, so AC20 Power and Volume carry drive): FT +0.19, +0.14, +0.15; W +0.13, +0.22, −0.05.
  Without range-limit labels as well: FT +0.111 (.012), +0.059 (.144), +0.097 (.026); W +0.103 (.024), +0.248 (<.001), −0.032. So FT's drive and cab
  hold on this basis, and part of the raw figure's weakness is pooling heads of very different spread.
- Most of GOAT's own − swap is mics; knobs alone −0.021 [−0.032, −0.009].
- **FT − W on GOAT:** drive −0.007 [−0.089, +0.071], tone −0.102 [−0.215, +0.020], cab +0.277 [+0.195, +0.367]. W, with no real rows,
  reads tone about as well as FT, so plugin training may already carry tone to real amps; that tuning gives tone back is not shown.
  FT's gain over W is cab, and that is distance (left +0.57 [+0.42, +0.73], right +0.27 [+0.09, +0.47]), heads W reads backwards. FT's own cab
  read is position 54%, distance 47% of its covariance [audited, recomputed from the cached rows].
  On BKS, 4 blocks from 2 songs allow no decision, so BKS intervals stay descriptive.
- GOAT is capture renders, 76% of labels one player. Its cab holds within player (+0.184) and with any head dropped.

## 3. Model, loss and training

**Real rows label every unsearched control as S** [code; size audited]. `pipeline_fix.py:4150` labels the whole setting and
`full_space.py` `encode` masks on sounding only. 64% of knob heads and 85% of switch heads are S constants.
- A table with no audio beats FT's held total on all 4 folds at the network's own sd clamp: 0.61, 0.60, 1.12, 1.61 against FT's 0.91–2.29
  [audited]. The clamp is fair, since those constants are exact, but it decides the result: at an sd floor of 0.01 the table reads 1.49,
  1.49, 2.03, 2.51 and loses all 4. The margin is the knob constants; mics favour FT by 0.05–0.15.
- So F42's fall from 5.7 to 1–2 is not evidence of reading, and it chose FT's epoch count. Fold 0: unsearched knobs −0.71 to −4.18 per
  head; each of the 2 mic heads 2.44 to 1.25.
- **The trap:** those constants teach FT to hold everything else at S. Mask them and those heads stay W's, so pair the mask with a
  readout that writes S there (`F.answer_settings`, `at_S`). Part of FT's gain over W may be that hold (inference).

**Other findings:**
- Loss weights, at FT's start [audited]: mics 75% of the real loss, body gradient 3.66 against 0.22 from searched knobs. At the read state
  the all-network gradient on constants is 18–22 against 0.3–0.4 searched and 2.5–2.7 mic. Real rows train the amp head on a forced amp.
- Sigma floor 0.0025 against the labels' 0.25 grid (`full_space.py:434`); may explain F42's plugin loss rise, untested [reviewer].
- FT underfits except on mics: in-sample E 0.195 / 0.224, held 0.207 / 0.230 (BKS / GOAT) [reviewer].
- **Not levers** (each at most 0.005 in E) [reviewer]: AdaBN, seeds, window or backing averaging, denoised targets, top-component readout.

**A small model** [reviewer, not recomputed]. Ridge on 24 PCs of pooled mel statistics, **on the clean track**: rms −0.020 / −0.021 against
the centre, still rising at 137 recordings. On the backed input, the only one FT reads, about −0.004 / −0.004. With a whole BKS song held
out, +0.002 [−0.013, +0.017]. So it reads in domain with no backing; transfer is not shown. By rms, FT is level with the centre (+0.005, +0.003).

**Target form.** With hundreds of labels, parameter regression in a much smaller shape looks the right form: searched controls, residual
from a real-amp centre, low capacity. Proxy, retrieval and flow rank last: too few labels, and no scorer in the product [reviewer's
judgement, untested].

## 4. Features and extraction

[reviewer] unless marked; probes on stored features. W, D_fix and FT receive one channel; the mix channel is zeroed (`direct_stems.py:1206`).

- **A lead: stems may lean toward another guitar.** This rests on amp accuracy alone: from the stem, target 0.342 (base 0.345), dominant
  other 0.404; from the clean target, 0.487. It has no interval and could not be recomputed: rows cluster by section, so it is weaker than
  its 1,637 rows suggest, and it needs `cc/rows`, which holds NS rows. Target inputGain ρ is +0.048 on the stem, +0.201 clean, which shows
  the target's read is lost, not where it went. If it holds, it challenges F15 and F17's "the other guitars add no further loss". Other
  guitars here have independent presets, so the size on real songs is unknown. The dominant-other ρ (+0.160) stays uncorrected, by the ML
  session's decision, and is not evidence here.
- **Train and read domains differ.** W, D_fix and FT train on P2b and read X-LANCE stems: AUC 0.997 [audited, 0.985–1.0 per fold], 35 dB apart
  at 8–12 kHz, grid-floor cells 0.06% against 6.35%. W on stems reads worse than the constant (+0.0052). Alignment removes the harm, not the gap.
- **W's skill rests on long-term colour.** Fixing band means takes −0.0035 to −0.0008. Long-term spectrum separates plugin from real at AUC
  0.98–1.00 per fold, dynamics at 0.64–0.96 per fold [audited]. Dynamics transfer better than the spectrum but are not close to domain-free.
- **Drive: no representation is shown better where drive varies** [audited]. Against a physical non-linearity index, plugin-trained, read on
  GOAT's 214 trusted units: dynamics + flatness +0.50 within class, but clean +0.67 and crunch +0.20, and on crunch it does not beat mel mean +
  std (0.00 [−0.21, +0.20]). Flatness alone leads on crunch (+0.32), untested. Clean's index sits near 0.10, so that rho may follow noise.
- The models' inputGain heads read −0.04 to −0.21, intervals holding 0. Other drive heads do better: W's GOAT Volume and Level heads read +0.21
  to +0.36 (n 68–76).
- Tone wants the long-term spectrum (ac20Cut +0.63 against +0.13); drive's preference is weaker.
- Rho against that index by input: target +0.51 to +0.58, P2b +0.35 to +0.43, mix +0.10 to +0.15, stem +0.09 to +0.10.
- Training tones read more driven than real clean ones (index 0.49 against 0.10), cause unknown.
- **Skip:** finer mels, unquantised input, a higher top frequency, level rules. Two-half averaging gains about 0.001.

Checked correct: parity (0 grid steps), one mel, mask and zeroing path, no power-sum, leak or AAC in the current recipes, mono fold,
nothing lost above 16 kHz.

## 5. Labels and search

- **The search barely refines** [audited]. 150 × 0.35 = 52 evaluations on all 520 labels; the step halves only after a sweep with no gain,
  and never left 0.25. Input gain has 8 dB resolution: 293 of 306 BKS gains sit on 4 values. 30 evaluations give 87% of the gain. The SW50R
  right mic reaches 5.15 of 9 options, and mics take 18 of 52 evaluations for 11% of the gain [reviewer].
- **The searched-head definition is complete** [audited]. Across 520 labels, 0 settings differ from S outside `K.space`, and every dim has a head.
- **Noise** [reviewer; 16 near-replicate pairs, one band]: search 21%, 16%, 32% of drive, tone and cab variance. Window adds to 43%, 34%, 44%.
  It comes from the search's path; J0's slopes are stable.
- **Dimension** [reviewer]: 2–4 by sound, 4–6 by label, against 12–17 searched.
- **Prior** [reviewer]: 22% of real labels sit outside the plugin labels' 5–95% range, against 8.5%. Drive leans low. This reproduces F27
  without V-real.
- **Measure DI level** explains at most 2.3% of inputGain variance, so the feared incoherence is not supported [reviewer]. 19% of labelled
  units peak above 0 dBFS.

Correct [reviewer]: 520 labels replay exactly; FT − S −0.177 reproduced; folds clean; the centre is not a search artefact (BKS and GOAT r 0.80).

## 6. Evaluation

- **Percentile bootstrap undercovers** [audited]: 0.82 at 7 clusters, 0.75 at 4, 0.50 at 2. t holds at 0.90 under normal spreads, but skew hurts it
  at 7 clusters (lognormal σ 0.5 about 0.86, σ 1 about 0.77). Used at `direct_stems.py:268`, `ear_vreal.py:124`, `fx_reader.py:632`, `pipeline_fix.py:4391`.
- `weighted_clustered` ignores band effects: 0.85, 0.78, 0.70 at ICC 0.1, 0.25, 0.5 on a generic design (`pipeline_fix.py:5648`). The real ICC is
  unmeasured [reviewer].
- **L2 is sized too small** [audited]. F54's half-widths give about 56% power; 80% needs 18 and 38 bands for rank gaps of 0.75 and 0.5.
- Add an answer-swap placebo to L2, randomise the amp rather than choosing it by S, and use one part per band. Hold out rigs and songs, not only DIs,
  when a read claims a new recording.

## Recommended order

ML session: N1's first read (F55 pending) took masked FT through these measures, beside the rig table. On GOAT it follows recordings better than FT on tone (+0.258 against +0.121; FTM − FT +0.137 [+0.065, +0.207]) and keeps cab, and BKS stays undecided; this is by knob, with no score read yet. N2 (search v2) is adopted by its declared rule after 1,207 renders, and is not shown more reliable. N3 (the learning curve; first read, recomputed by separate code, the ML session's record pending): no group rises by its declared rule. FTM − FTM25 on GOAT is +0.001 [−0.040, +0.039] on drive, +0.055 [−0.015, +0.123] on tone and +0.023 [−0.014, +0.061] on cab, while FTM − FTMs clears zero in all three. That is undecided and says nothing against more rows; tone is the one group where more rows may still help. It is by knob, not by sound. N5 (the same read on X-LANCE stems of the labelled mixes; first read, loader independently checked, the ML session's record pending): on GOAT neither FT nor FTM shows a stem cost in any group (FTM stem minus backed +0.008 [−0.033, +0.052] on drive, +0.054 [−0.010, +0.120] on tone, −0.004 [−0.044, +0.037] on cab). Only W's drive falls (−0.079 [−0.145, −0.010]). Undecided by its rule, and the kindest stem: these backings hold no other guitars, so it says nothing about the lead on real songs.

1. Zero renders: swap percentile bootstraps for t; report `tonal` beside `distance`, stratified by d_S, on stored judged rows.
2. Ridge by sound against the centres, about 670 renders, with its input stated: is its knob gain audible, and does any survive the backing?
3. Drive on crunch: which representation reads it, before any split of inputs.
4. The stem: align or train on real stems (about 19 h, needs the user's yes); test the lead by labelling the dominant guitar.
5. Resize L2.

## Errors made in this review

Each is corrected above, and the independent audit caught the last group.
- A first run of M1 was void (lag search missed the DI's 0.25 s offset). Fixed, with a control.
- The first lookup collapsed onto the label grid (52% of components under 0.01 sd). Voided.
- The row-level null for r was too narrow. Replaced by recording-level permutation.
- r first read the heaviest component, not the real readout. Redone on the real readout.
- A group bug counted `rightCabMicLevel` as drive. Every r sent before the correction is superseded.
- Caught by the audit: wrong BKS p values and a false 4 clusters; the lookup totals (a mic-term bug, first sent as 0.34–1.20); BKS cab read as reading;
  "tuning gives tone back"; a pooled drive figure of +0.64 and dynamics AUCs of 0.58–0.70 reported on a biased basis. The scratch scripts
  `final.py` and `bias.py` keep their bugs and are superseded.
- Caught by the PR's review: "mostly mic distance" for FT's cab read (only FT − W is distance), which had already reached the ML session's plan;
  "robustly only", which held on raw units alone; and stale lines on N2 and N3.
- The audited read as first adopted (`reads_v2.py`) lacked three things it was declared to do: the exact permutation, the item intervals and
  the paired differences. `reads_v3.py` adds them, passed a separate code review and reproduces the audit's table on FT and W. It is the only
  script proposed for the repo.

## Limits

- One listener; knob units and probes; no read of sound on a real song.
- GOAT is capture renders; BKS is one band with 8 DIs, and its playing is in W's plugin rows.
- Several comparisons and post-hoc leads. Each lead above needs its own declared test.
- J0's sensitivity figures use renders as stand-in recordings.
- Not recomputed: amp accuracy, ridge, noise shares, W on stems.

## Data touched outside the limits

The ML session set its limits during the review. Before they reached them, this review and its reviewers opened listings of `captures/`,
`panel/` and `vreal/`, two V-real parts' clips (deleted, nothing computed but one RMS), `ear-vreal` plan and record text, the opening of
two stored V-real reports, and stored `ns` log fields. After them: one log row's `ns` fields, two accidental metadata prints of NS rows,
one NS-derived `best_epoch`, and parsing of `cc/` files with NS rows dropped by id. No capture, panel or V-real audio was used and no
result rests on any of it. The full list is in the ML session's log.
