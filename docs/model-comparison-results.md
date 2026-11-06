# Model comparison results (2026-11-06)

**Status: a development read. It adopts nothing.** [Plan](model-comparison-plan.md), ledger `model-comparison`, code `learn/bakeoff*.py`. All on BKS and GOAT, which have been used to choose many times. Nothing here is a read by ear or on a fresh set.
Cost: 6,700 renders and 139 minutes of training, one GPU job at a time.

**Audit.** Two independent audits, each with its own code, refitted `M-ridge` and `W-ridge`, regenerated two folds of `A-mic` and `A-cat`, and recomputed every score contrast, arm read and judge term. The other candidates' fits and `P-ridge` rest on the harness's controls. The audits' scripts and logs are in `PF/bakeoff/audit/`; figures marked [audit] come from them, not from the stored reads.

**Why.** The [deep review](ml-deep-review-2026-11.md) compared versions of one network, so "best model" had never been tested against other kinds. The user asked for research on network types, features and judging, then this comparison. The research is [this report](research/model-features-judge-fit-2026-11.md).

**Terms.** S is the class's starting preset. The centre (`RcBG`) is the average of a fold's training labels for each amp and class. J0 is the judge, and "by the score" means J0's distance, never sound. BKS is one band of 8 DIs and GOAT 130 captured items, both real amp rows, with labels from a search through the true DI. FTm is the current candidate: W, trained on plugin renders, then fine-tuned on real rows on the controls the search set.

## The short answer

| Part | Best known now | What the evidence says | Not tested |
|---|---|---|---|
| **Network** | No type is shown better than FTm by the score. | Every contrast with FTm by the score is undecided, including two plain ridges, whose GOAT intervals sit within about ±0.02. By knob, a small CNN and binned outputs read worse in these runs, each with its own handicap. One mixture component is not shown worse. | Pretrained encoders (EfficientAT, AFx-Rep): their weights need a download and the user's yes. Larger networks are out of scope, by the report. |
| **Features** | Mel band means and stds, the best hand-built input. | None is shown better for tone, for cab or for drive on crunch. Flatness did not hold up as the lead the review named. W's learned features read cab better than any of them. | Anything that needs audio, such as roughness, and any input on stems of real songs. |
| **Judge** | J0 stays. | Neither `tonal` nor a cross-fitted term passes the screen. | Auditory models (HAAQI, PEAQ) and any song-only judge: they need a download. |

**The score barely separates these models.** On GOAT, S to the centre is −0.073 and every model adds about −0.02 more. A knob gain of this size predicts a score change near what the score can resolve, so an undecided row here is not evidence that models are equal.

## Reading knobs

r is fold-demeaned and read through `reads_v3`, unchanged, on held rows. BKS is descriptive.

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

- **`W-ridge` moves on by the declared rule, marginally.** It is the only one of 30 contrasts to clear the simultaneous bound: `W-ridge − FTm` on drive +0.153 [+0.063, +0.235], bound +0.003. Over 20 reasonable inner-fold choices the bound averages −0.003, so it sits at zero within noise, while the plain interval clears in all 20 [audit]. On cab it is +0.065 [+0.007, +0.119], a plain lead; on tone −0.008 [−0.089, +0.079], undecided.
- **That is not "reads drive better".** About a third of the gain is where FTm puts its spread: 68% of its answer variance sits on ac20Power, which holds 8% of label variance, and 3.4% on inputGain, which holds 59% [audit]. Paired head-standardised it is undecided (−0.011 [−0.090, +0.067]) [audit]. The rest looks like reading: on pairs of one DI through two chains, inputGain reads `W-ridge` +0.326 [+0.163, +0.475], FTm +0.144 [audit]. Without range-limit labels the gain is +0.062 [−0.044, +0.157], it rests on pr12's inputGain, and BKS does not repeat it.
- **`M-ridge − FTm`:** drive +0.131 [+0.036, +0.221], tone −0.057 [−0.146, +0.032], cab −0.070 [−0.136, −0.008], a plain loss on cab. It reached the score read by the ML session's handover, not by the rule.
- **W's body adds on cab, not drive.** `W-ridge − M-ridge`: cab +0.136 [+0.080, +0.191], drive +0.022 [−0.051, +0.095] [audit].
- **`P-ridge − W` is undecided in all three groups.** A linear model on mel statistics is not shown worse than the CNN at what W reads from plugin rows alone.
- **One player carries 76% of GOAT.** r on that player, then the rest, on drive, tone, cab: FTm +0.097, +0.201, +0.198, then +0.168, +0.279, +0.234. `M-ridge` +0.235, +0.192, +0.140, then +0.244, +0.107, +0.103. `W-ridge` +0.233, +0.240, +0.259, then +0.334, +0.105, +0.298. Off the main player, tone falls for both ridges: `W-ridge − FTm` −0.174 [−0.414, +0.066], `M-ridge − FTm` −0.171 [−0.434, +0.032].

## Inputs

Ridges on 24 PCs. Tone and cab are GOAT r on real-trained ridges. Drive on crunch is head-standardised: 104 rows, 81 items, so this read was unlikely to decide.

| Input | Tone | Cab | Drive on crunch, real rows | Drive on crunch, plugin rows |
|---|---|---|---|---|
| `mel`, the reference | +0.201 | +0.147 | +0.180 | +0.198 |
| `ltas`, 80 Hz–5 kHz with a raised floor | +0.181 | +0.096 | | |
| `ceps-lo`, low quefrency | +0.172 | +0.129 | | |
| `onset`, attacks and sustains apart | | | +0.167 | +0.190 |
| `hpss`, the percussive residue | | | +0.199 | +0.079 |
| `flat`, spectral flatness | | | +0.081 | +0.206 |
| `ceps-hi`, high quefrency | | | +0.070 | +0.096 |

- No input clears the bound, and on crunch none has a plain interval above zero. The best is `hpss − M-ridge` +0.020 [−0.062, +0.113], so `A-in` was not run.
- Flatness, the review's untested lead for crunch, reads below the mel on real rows: `flat − M-ridge` −0.099 [−0.208, −0.001]. Plugin-trained, `P-flat − P-ridge` is +0.008 [−0.095, +0.111], `P-onset` −0.008 [−0.052, +0.041], `P-hpss` −0.118 [−0.210, −0.031], `P-ceps-hi` −0.101 [−0.240, +0.025].
- Drive on crunch stays undecided, not closed.
- An arm on FTm's own features was dropped before any read: its training rows would have been in-sample.

## Training arms

Each arm ran FTm's recipe with one family of changes, at FTm's stored epoch counts, chosen on FTm's loss. So a clear gain counts and a null says little. GOAT, arm − FTm, 90% plain intervals. Seed noise (`A-ctl`, other training seeds on W's same start) is +0.006, −0.014, −0.000; W's own seed noise is not seen.

| Arm | Drive | Tone | Cab | Mic own-against-swap | BKS r: drive, tone, cab |
|---|---|---|---|---|---|
| FTm | | | | | +0.306, +0.203, +0.562 |
| `A-cat`: 21 bins, median readout | +0.025 [−0.023, +0.075] | −0.092 [−0.169, −0.012] | −0.062 [−0.103, −0.018] | +0.003 [−0.010, +0.016] | +0.050, +0.179, +0.434 |
| `A-cnn`: two conv layers, fresh body | −0.039 [−0.098, +0.016] | −0.138 [−0.212, −0.053] | −0.114 [−0.184, −0.047] | +0.099 [+0.042, +0.157], worse | +0.000, +0.298, +0.140 |
| `A-k1`: one component, sd floor 0.07 | +0.026 [−0.003, +0.052] | +0.020 [−0.024, +0.062] | +0.009 [−0.012, +0.032] | +0.001 [−0.008, +0.010] | +0.272, +0.246, +0.586 |
| `A-mic`: mic loss weight 0.1 | +0.037 [+0.013, +0.063] | +0.065 [+0.012, +0.119] | +0.043 [+0.014, +0.068] | +0.057 [+0.029, +0.085], worse | +0.348, +0.290, +0.546 |

- **No arm moves on by the declared rule.**
- **`A-mic` is the knob lead.** All three plain intervals clear zero, its bounds sit just below (−0.005, −0.022, −0.001), and it gives up some mic reading. It fits the review's finding that mics take 75% of the real loss at FT's start.
- **`A-k1`:** undecided in all three, so the mixture's extra components are not shown to help.
- **`A-cat` and `A-cnn` read worse in these runs, which is not a verdict on the idea.** Their losses on tone and cab are plain-interval losses, and neither arm's clears a simultaneous bound. Each has a handicap. `A-cnn` starts from a `final` state, and W's own `final` reads tone 0.074 below its `best`, while its loss at FTm's epochs sits 25–40% above FTm's [audit]. 58% of `A-cat`'s tone gap precedes tuning, and off the main player its tone gap is +0.135 [−0.007, +0.247] [audit]. The report's first pick, binned heads, rested partly on a misread citation (the plan's log), and it is not supported here.

## By the score

Minus is closer. 1,340 renders each, and every stored FTm, RcBG and S record came back with the same hash and judge. FTm − S reproduces F55's −0.094 and −0.123. 90% t on `distance`; `tonal` beside.

**GOAT, by item (130):**

| Candidate | − S | − centre | − centre, by fold | − FTm | `tonal` − centre | `tonal` − FTm |
|---|---|---|---|---|---|---|
| FTm | −0.094 [−0.116, −0.072] | −0.021 [−0.040, −0.002] | −0.017 [−0.046, +0.013] | | −0.051 [−0.077, −0.025] | |
| `M-ridge` | −0.093 [−0.115, −0.071] | −0.020 [−0.028, −0.012] | −0.018 [−0.026, −0.011] | +0.001 [−0.016, +0.019] | −0.036 [−0.050, −0.021] | +0.015 [−0.010, +0.041] |
| `W-ridge` | −0.097 [−0.118, −0.076] | −0.023 [−0.032, −0.015] | −0.021 [−0.032, −0.011] | −0.002 [−0.018, +0.013] | −0.040 [−0.053, −0.026] | +0.011 [−0.011, +0.034] |
| `A-mic`, post hoc, a lead only | −0.100 [−0.122, −0.079] | −0.027 [−0.045, −0.008] | −0.024 [−0.053, +0.005] | −0.006 [−0.013, +0.002] | −0.060 [−0.086, −0.034] | −0.009 [−0.022, +0.004] |

**BKS, by DI (8):**

| Candidate | − S | − centre | − centre, by fold | − FTm | `tonal` − centre | `tonal` − FTm |
|---|---|---|---|---|---|---|
| FTm | −0.123 [−0.205, −0.041] | +0.018 [−0.027, +0.064] | +0.020 [−0.048, +0.089] | | +0.007 [−0.079, +0.093] | |
| `M-ridge` | −0.162 [−0.261, −0.064] | −0.021 [−0.041, −0.001] | −0.018 [−0.043, +0.007] | −0.039 [−0.084, +0.005] | −0.024 [−0.054, +0.007] | −0.031 [−0.109, +0.047] |
| `W-ridge` | −0.148 [−0.254, −0.042] | −0.007 [−0.035, +0.021] | −0.005 [−0.048, +0.038] | −0.025 [−0.074, +0.024] | +0.000 [−0.038, +0.039] | −0.007 [−0.080, +0.067] |
| `A-mic`, post hoc, a lead only | −0.119 [−0.200, −0.038] | +0.023 [−0.030, +0.075] | +0.025 [−0.062, +0.112] | +0.004 [−0.008, +0.017] | +0.010 [−0.081, +0.100] | +0.003 [−0.018, +0.023] |

- **Every contrast with FTm is undecided.**
- **`A-mic` by the score is undecided, not "no gain".** Its knob gain cuts squared error to the label by only 2%, which predicts −0.002 to −0.005 [audit], so the read fits and sits below what the score can resolve. All four folds lean closer on GOAT; two of four do on BKS.
- **The ridges' gain over the centre on GOAT is steady but not everywhere.** It holds by unit, cell, fold and player [audit], and it vanishes in the closest third of directions: `M-ridge − centre` by thirds of S's distance is −0.001, −0.030, −0.024 (the first −0.001 [−0.012, +0.010]), and `W-ridge` −0.006, −0.025, −0.032. FTm reads +0.002, −0.019, −0.031.
- **On BKS no model's contrast with the centre clears by fold.** Its 8 DIs sit in pairs sharing a model and a centre, on 2 songs.
- **Contrasts with FTm mix several things.** Only the ridges move knobs alone. FTm and `A-mic` also change the centre: 64–69% of their squared move is a per-cell shift, 64% of directions change mics and 21% change switches [audit]. On GOAT with RcBG's mics and switches kept, on selected directions, FTm reads −0.027 [−0.041, −0.013] and `M-ridge` −0.023 [audit].
- No score placebo exists, and closeness to the label explains at most 40–70% of the ridges' −0.02 [audit].

## Judging

Stored pages, in-sample, one listener, so a screen only. The copy of J0's path matched every stored value with a gap of 0.0. Spearman is on the 48 main items, 24 a page, without anchors [audit]. Gamma and the other checks, from `judge.json`, include the anchors (33 and 28 items).

| Term | Spearman, judge-ear, judge-v5 | Gamma | Flip orders | Tone steps in the top three | Heard drive above unheard | Fall, 6 dB bell, d 2.73 to 6.05 |
|---|---|---|---|---|---|---|
| `distance` (J0) | +0.44, +0.73 | +0.48, +0.88 | 2 of 4 | 2, 1 | 1.00, 1.00 | 3.2× |
| `tonal` | +0.47, +0.67 | +0.54, +0.86 | 2 of 4 | 3, 2 | 0.67, 1.00 | 2.6× |
| cross-fitted | +0.28, +0.55 | +0.41, +0.69 | 2 of 4 | 3, 2 | 0.67, 1.00 | 1.6× |

- **No term passes the declared screen.** Any fixed order scores 2 of 4 on the flip, so none tracks it: no term reverses between the pages as the ear did. The anchors come from a later sitting, which weakens this check too.
- **The cross-fitted term falls less with distance in its own units,** but in split-half sds it is no stronger far out (0.32 against 0.34 at d 6.05 on the bell). It does not track this ear better. The review's warning stands: sensitivity is not agreement.
- J0 stays. `tonal` and the cross-fitted term are stored beside it for these reads.

## What this changes

- **FTm stays the candidate, but it is not shown better than a ridge by the score.** A ridge on mel statistics needs no GPU and no fine-tuning, and it is undecided against FTm by the score on both sets. By knob it reads drive above FTm and cab below. That makes it a baseline any later network has to beat, with its input stated.
- **Real labels may do as much through a shallow readout as through fine-tuning.** `W-ridge` keeps W's body: by knob it is undecided against FTm on tone and a plain lead on cab, and undecided by the score. That is the methods report's row 2. It is a lead, not a finding about real songs.
- **Network size is not shown to matter, in either direction.** One handicapped smaller body read worse, and larger ones were not tried.
- **What the score can resolve and what the labels hold look like the nearer limits.** Differences here sit at or below about 0.02. Only the ear or fresh bands can separate them: the report's 27–45 bands, or a blind page.

## Limits

- GOAT is 76% one player, its chains are unrecorded, and BKS is one band. These sets were chosen on many times. 22 reads of 20 models: 16 Phase 3 candidates and 4 arms, plus `A-ctl`, and `A-mic`'s post hoc score read. The selection is counted for knobs, not for the score.
- Labels are search results through the true DI, not ground truth, with search noise of 16–32% of variance by group.
- Inputs are backed real units through a clean render, not separated stems of real songs.
- W's stored body was chosen on NS loss, which every arm built on it inherits, as do `W-ridge` and FTm.
- `P-ridge` was not refitted by an audit.

## Errors made in this work

Each is corrected above.
- The first harness did not compute the declared contrasts, corrected the wrong test, would have leaked FTm features, and left LUFS unscaled. The plan's review caught all of it before any read.
- The training loop hid non-finite runs and left new weights unseeded; the render check could pass a new refusal. Reviews caught these, with no result affected.
- Notes to the user during the night said `A-mic`'s gain "doesn't appear in the score", and that a ridge was closer than the centre "on both test sets". The audit corrected both: the first is undecided and below resolution, and the second does not hold on BKS by fold.
- The first draft of this document said "level" and "cleanest", and claimed more audit than was done. The PR's review caught them.
- The deep review's "about 670 renders" for this read counted answers. It is 1,340.
