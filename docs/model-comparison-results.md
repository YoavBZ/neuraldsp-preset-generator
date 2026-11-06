# Model comparison results (2026-11-06)

**Status: a development read. It adopts nothing.** [Plan](model-comparison-plan.md), ledger `model-comparison`, code `learn/bakeoff*.py`. All on BKS and GOAT, which have been used to choose many times. Nothing here is a read by ear or on a fresh set.
Cost: 6,700 renders and 139 minutes of training on one GPU job at a time. Every result below was recomputed by an independent auditor with its own code; the plan's findings log has the detail.

**Why.** The [deep review](ml-deep-review-2026-11.md) compared versions of one network, so "best model" had never been tested against other kinds. The user asked for research on network types, features and judging, then this comparison. The research is [this report](research/model-features-judge-fit-2026-11.md).

## The short answer

| Part | Best known now | What the evidence says | Not tested |
|---|---|---|---|
| **Network** | No type is shown better than masked FT (FTm) by the score. Two plain ridges are level with it. | Neither ridge beats FTm by the score: intervals on GOAT sit within about ±0.02. In these runs a small CNN and binned outputs read worse by knob, each with its own handicap. One mixture component loses nothing. | Pretrained encoders (EfficientAT, AFx-Rep): their weights need a download and the user's yes. |
| **Features** | Mel band means and stds. | No input beat them, for tone, for cab or for drive on crunch. Flatness did not hold up as the lead the review named. | Anything that needs audio, such as roughness, and any input for stems of real songs. |
| **Judge** | J0 stays. | Neither `tonal` nor a cross-fitted term tracks the ear better. The cross-fitted term does flatten less with distance. | Auditory models (HAAQI, PEAQ) and any song-only judge: they need a download. |

**The score barely separates these models.** On GOAT, S to the centre is −0.073 and every model adds about −0.02 more. A model's knob gain of this size predicts a score change near what the score can resolve, so an undecided row here is not evidence that models are equal.

## Reading knobs

GOAT is 130 items, BKS one band of 8 DIs. r is fold-demeaned and read through `reads_v3`, unchanged. BKS is descriptive.

| Model | GOAT drive | GOAT tone | GOAT cab | BKS drive | BKS tone | BKS cab |
|---|---|---|---|---|---|---|
| FTm, the reference | +0.082 | +0.258 | +0.218 | +0.306 | +0.203 | +0.562 |
| W, no real rows | +0.096 | +0.222 | −0.086 | −0.268 | +0.219 | −0.132 |
| `W-ridge`: a ridge on W's frozen last layer, on real rows | +0.234 | +0.251 | +0.283 | +0.286 | +0.284 | +0.549 |
| `M-ridge`: a ridge on 24 PCs of mel means and stds, on real rows | +0.212 | +0.201 | +0.147 | +0.457 | +0.231 | +0.452 |
| `M-rrr`: reduced rank 4 | +0.228 | +0.231 | +0.155 | +0.433 | +0.282 | +0.543 |
| `M-trees`: boosted trees | +0.150 | +0.284 | +0.196 | +0.333 | +0.302 | +0.556 |
| `M-knn`: nearest neighbours | +0.159 | +0.193 | +0.184 | +0.433 | +0.311 | +0.369 |
| `P-ridge`: a mel ridge on plugin rows only | +0.140 | +0.207 | −0.038 | +0.057 | +0.266 | −0.019 |

- **`W-ridge` moves on by the declared rule, marginally.** It is the only one of 30 contrasts to clear the simultaneous bound: `W-ridge − FTm` on drive +0.153 [+0.063, +0.235], bound +0.003. Over 20 reasonable inner-fold choices the bound averages −0.003, so it sits at zero within noise, while the plain interval clears in all 20.
- **That is not "reads drive better".** About a third of the gain is where FTm puts its spread: 68% of its answer variance sits on ac20Power, which holds 8% of label variance, and 3.4% on inputGain, which holds 59%. Paired head-standardised it is undecided (−0.011 [−0.090, +0.067]). The rest looks like reading: on pairs of one DI through two chains, inputGain reads `W-ridge` +0.326 [+0.163, +0.475], FTm +0.144. Without range-limit labels the gain is +0.062 [−0.044, +0.157], it rests on pr12's inputGain, and BKS does not repeat it.
- **W's body adds on cab, not drive.** `W-ridge − M-ridge`: cab +0.136 [+0.080, +0.191], drive +0.022 [−0.051, +0.095].
- **`P-ridge − W` is undecided in all three groups.** A linear model on mel statistics is not shown worse than the CNN at what W reads from plugin rows alone.

## Inputs

All ridges on 24 PCs, read against `M-ridge`.

| Input | Tone | Cab | Drive on crunch, head-standardised |
|---|---|---|---|
| `mel`, the reference | +0.201 | +0.147 | +0.180 |
| `ltas`, 80 Hz–5 kHz with a raised floor | +0.181 | +0.096 | |
| `ceps-lo`, low quefrency | +0.172 | +0.129 | |
| `onset`, attacks and sustains apart | | | +0.167 |
| `hpss`, the percussive residue | | | +0.199 |
| `flat`, spectral flatness | | | +0.081 |
| `ceps-hi`, high quefrency | | | +0.070 |

- No input clears the bound, and on crunch none has a plain interval above zero. The best is `hpss − M-ridge` +0.020 [−0.062, +0.113], so `A-in` was not run.
- Flatness, the review's untested lead for crunch, reads below the mel: `flat − M-ridge` −0.099 [−0.208, −0.001]. Plugin-trained, `P-flat − P-ridge` is +0.008 [−0.095, +0.111].
- Crunch holds 104 rows and 81 items, so this read was unlikely to decide. It is undecided, not closed.

## Training arms

Each arm ran FTm's recipe with one family of changes, at FTm's stored epoch counts, chosen on FTm's loss. So a clear gain counts and a null says little. GOAT, arm − FTm, 90%. Seed noise (`A-ctl`, other training seeds on W's same start) is +0.006, −0.014, −0.000.

| Arm | Drive | Tone | Cab | Mic own-against-swap |
|---|---|---|---|---|
| `A-cat`: 21 bins, median readout | +0.025 [−0.023, +0.075] | −0.092 [−0.169, −0.012] | −0.062 [−0.103, −0.018] | +0.003 [−0.010, +0.016] |
| `A-cnn`: two conv layers, fresh body | −0.039 [−0.098, +0.016] | −0.138 [−0.212, −0.053] | −0.114 [−0.184, −0.047] | +0.099 [+0.042, +0.157], worse |
| `A-k1`: one component, sd floor 0.07 | +0.026 [−0.003, +0.052] | +0.020 [−0.024, +0.062] | +0.009 [−0.012, +0.032] | +0.001 [−0.008, +0.010] |
| `A-mic`: mic loss weight 0.1 | +0.037 [+0.013, +0.063] | +0.065 [+0.012, +0.119] | +0.043 [+0.014, +0.068] | +0.057 [+0.029, +0.085], worse |

- **No arm moves on by the declared rule.**
- **`A-mic` is the knob lead.** All three plain intervals clear zero, its bounds sit just below (−0.005, −0.022, −0.001), and it gives up some mic reading. It fits the review's finding that mics take 75% of the real loss at FT's start.
- **`A-k1`:** the mixture adds nothing visible, so the simpler head is not shown worse.
- **`A-cat` and `A-cnn` lost in these runs, which is not a verdict on the idea.** Half of `A-cnn`'s tone gap exists before tuning and comes from its `final` start, at a loss 25–40% above FTm's at FTm's epochs. 58% of `A-cat`'s tone gap precedes tuning, and off the main player its tone is +0.135 [−0.007, +0.247]. The report's first pick, binned heads, rested partly on a misread citation ([plan's log](model-comparison-plan.md)), and it is not supported here.

## By the score

Minus is closer. GOAT by item, BKS by DI, 90% t. 1,340 renders each, and every stored FTm, RcBG and S record came back with the same hash and judge. FTm − S reproduces F55's −0.094 and −0.123.

| Candidate | − centre, GOAT | − centre, BKS | − FTm, GOAT | − FTm, BKS |
|---|---|---|---|---|
| FTm | −0.021 [−0.040, −0.002] | +0.018 [−0.027, +0.064] | | |
| `M-ridge` | −0.020 [−0.028, −0.012] | −0.021 [−0.041, −0.001] | +0.001 [−0.016, +0.019] | −0.039 [−0.084, +0.005] |
| `W-ridge` | −0.023 [−0.032, −0.015] | −0.007 [−0.035, +0.021] | −0.002 [−0.018, +0.013] | −0.025 [−0.074, +0.024] |
| `A-mic`, post hoc, a lead only | −0.027 [−0.045, −0.008] | +0.023 [−0.030, +0.075] | −0.006 [−0.013, +0.002] | +0.004 [−0.008, +0.017] |

- **Every contrast with FTm is undecided.**
- **`A-mic` by the score is undecided, not "no gain".** Its knob gain cuts squared error to the label by only 2%, which predicts −0.002 to −0.005, so the read fits and sits below what the score can resolve. All four folds lean closer.
- **The ridges' gain over the centre is the cleanest row.** They hold on GOAT by unit, cell, fold and player. No model's contrast with the centre clears on BKS by fold: `M-ridge` is −0.018 [−0.043, +0.008] by fold, since BKS's 8 DIs sit in pairs sharing a model and a centre, on 2 songs.
- **Contrasts with FTm mix several things.** Only the ridges move knobs alone. FTm and `A-mic` also change the centre: 64–69% of their squared move is a per-cell shift, 64% of directions change mics and 21% change switches. On GOAT with RcBG's mics and switches kept, on selected directions, FTm reads −0.027 [−0.041, −0.013] and `M-ridge` −0.023.
- No score placebo exists, and closeness to the label explains at most 40–70% of the ridges' −0.02.

## Judging

Stored pages, in-sample, one listener, so a screen only. The copy of J0's path matched every stored value with a gap of 0.0.

| Term | Spearman, judge-ear (24) | Spearman, judge-v5 (24) | Flip orders | Fall, 6 dB bell, d 2.73 to 6.05 |
|---|---|---|---|---|
| `distance` (J0) | +0.44 | +0.73 | 2 of 4 | 3.2× |
| `tonal` | +0.47 | +0.67 | 2 of 4 | 2.6× |
| cross-fitted | +0.28 | +0.55 | 2 of 4 | 1.6× |

- **No term passes.** Any fixed order scores 2 of 4 on the flip, so none tracks it: no term reverses between the pages as the ear did. The anchors come from a later sitting, which weakens this check too.
- **The sensitivity mechanism is real** and does not by itself track this ear better. The review's warning stands: sensitivity is not agreement.
- J0 stays. `tonal` and the cross-fitted term are stored beside it for these reads.

## What this changes

- **Masked FT stays the candidate, but it is not shown better than a ridge.** The simplest thing that works on both sets by knob, a ridge on mel statistics, needs no GPU and no fine-tuning, and it holds level by the score. That makes it the baseline any later network has to beat.
- **Real labels may do as much as a shallow readout as they do by fine-tuning.** `W-ridge` keeps W's body and matches FTm on tone and cab by knob and on the score, in seconds. That is the methods report's row 2, and it is a lead, not a finding about real songs.
- **The bottleneck looks like what the score can resolve and what the labels hold,** not the network's size. Differences here sit at or below about 0.02. Only the ear or fresh bands can separate them: the report's 25–45 bands, or a blind page.

## Limits

- GOAT is 76% one player, its chains are unrecorded, and BKS is one band. Sets were chosen on many times. 22 candidates were tried, and the selection is counted above for knobs, not for the score.
- Inputs are backed real units through a clean render, not separated stems of real songs.
- W's stored body was chosen on NS loss, which every arm built on it inherits, as do `W-ridge` and FTm.
- `P-ridge` was not refitted by the audit.

## Errors made in this work

Each is corrected above.
- The first harness did not compute the declared contrasts, corrected the wrong test, would have leaked FTm features, and left LUFS unscaled. The plan's review caught all of it before any read.
- The training loop hid non-finite runs and left new weights unseeded; the render check could pass a new refusal. Reviews caught these, with no result affected.
- A note to the user said `A-mic`'s gain "doesn't appear in the score", and that the ridge was closer than the centre "on both test sets". The audit corrected both: the first is undecided and below resolution, and the second does not hold on BKS by fold.
- The deep review's "about 670 renders" for this read counted answers. It is 1,340.
