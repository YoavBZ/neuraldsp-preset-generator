# EfficientAT results (2026-11-06)

**Status: a development read. It adopts nothing.** [Plan](efficientat-plan.md), ledger `efficientat`, code `learn/eat_*.py`, research [report](research/efficientat-pretrained-reuse-2026-11.md). All on BKS and GOAT, which have now been read 58 times more. Nothing here is a read by ear or on a fresh set.
Cost: 6,700 renders of five readers, 36 control renders, and 38 minutes on the GPU, all of it the tuning. Weights and repo 134 MB.

**Audit.** The plan took four rounds of independent review. Two audits, each with its own code, recomputed every score contrast, refitted `E-mix`, `TE-mix` and `EW-mix` on all folds within 1.6e-6, and found no leak of a held DI, unit or label. Their limits on each claim are carried below.

**Why.** The [model comparison](model-comparison-results.md) left pretrained encoders as the one untested network type. Every model so far learned its filters from our own renders, so it could learn the plugin's fingerprint. EfficientAT's filters never saw the plugin. The user approved the download, then asked for several uses, each tested in isolation, and for any training that gets us closer to the goal.

**Terms.** S is the class's starting preset. The centre (`RcBG`) is the average of a fold's training labels for each amp and class. J0 is the judge, and "by the score" means J0's distance, never sound. FTm is the masked fine-tune, the model to beat. W is the CNN trained on 1,787 plugin rows. A number in brackets is a 90% interval. Undecided means it holds zero.

## The short answer

By the score, on sets read 58 times, frozen EfficientAT adds 0.6% over mel statistics on GOAT and is undecided on BKS. Tuning it on plugin rows changed nothing. The post hoc three-way reader `EW-mix` sits 3.7% closer than the centre on GOAT and leans 1.7% closer than FTm, a lead that fails by fold, by player and after correction. Nothing here is an ear read or a fresh set.

| Use | Finding |
|---|---|
| Frozen, on real rows, beside mel (`E-mix`) | On GOAT by knob it leads mel on tone and cab, by plain intervals. Only cab holds the simultaneous bound. By the score the gain over mel at the same size is small |
| Frozen, trained on plugin rows only | Zero-shot, tone rises (+0.279 against mel's +0.203). Cab does not transfer: +0.024 |
| Fine-tuned on plugin rows (`TE-mix`) | Not shown to help. By the score +0.000 against `E-mix`, and the domain gap did not move |
| Fine-tuned on real rows | Not run: the plan runs it only if plugin tuning leads, and the researcher's report advises the same |
| As a judge | Both terms fail. J0 stays |
| Its AudioSet tags (Distortion and others) | Nothing on GOAT, −0.16 to +0.04 |
| As a window chooser | Not built: its guitar outputs follow exposure at Spearman 0.29–0.30, under the report's 0.5 |

## By the score

ln ratio of J0's distance on the held half, 90% t intervals, 670 directions, each reader on the same ones. Negative is closer. GOAT by item, BKS by DI.

| Reader | − RcBG, GOAT | − RcBG, BKS | − FTm, GOAT | − FTm, BKS |
|---|---|---|---|---|
| FTm | −0.021 [−0.040, −0.002] | +0.018 [−0.027, +0.064] | | |
| `M-ridge`, 24 PCs | −0.020 | −0.021 | +0.001 [−0.016, +0.019] | −0.039 [−0.084, +0.005] |
| `M-pcs`, mel, 64 PCs | −0.025 [−0.034, −0.017] | −0.025 [−0.047, −0.003] | −0.004 [−0.022, +0.013] | −0.043 [−0.090, +0.003] |
| `W-pcs`, W's layer, 64 PCs | −0.027 [−0.036, −0.018] | −0.010 [−0.038, +0.018] | −0.006 [−0.022, +0.010] | −0.028 [−0.076, +0.020] |
| `E-mix`, EfficientAT beside mel | −0.031 [−0.040, −0.022] | −0.028 [−0.049, −0.007] | −0.010 [−0.027, +0.007] | −0.046 [−0.090, −0.003] |
| `TE-mix`, tuned on plugin rows | −0.031 [−0.040, −0.022] | −0.028 [−0.049, −0.008] | −0.010 [−0.027, +0.007] | −0.047 [−0.090, −0.004] |
| `EW-mix`, post hoc | −0.038 [−0.048, −0.028] | −0.022 [−0.050, +0.006] | −0.017 [−0.033, −0.001] | −0.040 [−0.085, +0.004] |

- **What EfficientAT adds.** `E-mix − M-pcs` is −0.006 [−0.011, −0.001] on GOAT and −0.003 [−0.015, +0.010] on BKS, p about 0.07 on GOAT. `M-pcs − M-ridge` is about the same size, −0.006. So the step from `M-ridge` to `E-mix` is half more PCs and half the network, each small.
- **`E-mix` against FTm on GOAT is undecided.** None of 130 leave-one-outs clears.
- **BKS is weaker than it looks.** `E-mix − RcBG` clears by DI but not by fold, −0.028 [−0.062, +0.005], and on one song: Bulldozer −0.043, TooMuch −0.002. `E-mix − FTm` by DI rests on three DIs, fails correction, and about 40% of it is FTm trailing the centre. Lean, not shown.
- **`EW-mix − FTm` on GOAT is a lead, not a finding.** It was built after S4 showed `W-pcs`'s cab and `E-mix`'s tone on the same GOAT. By fold −0.020 [−0.054, +0.015], main player −0.012 [−0.028, +0.005], rest −0.034 [−0.079, +0.011], crunch −0.041, clean −0.005, ac20 +0.001. Holm over its ten rows 0.43. BKS does not repeat it: `EW-mix − E-mix` +0.006 [−0.003, +0.015], though W saw those DIs, and `W-pcs − M-pcs` is a plain BKS loss, +0.015 [+0.007, +0.023].
- **Size.** On GOAT `E-mix` is 3.1% closer than the centre and takes 14% of the centre-to-label gap on held halves. These reads sit far below the labels' cap near 0.75–0.81 r.

## By knob

Within-cell r on GOAT, drive, tone, cab. Every read here, and every answer above, rests on one backing, variant 0: `E-mix`'s drive ranks 23 of 25 backings, and `EW-mix − E-mix` on cab, +0.046 here, averages +0.025 over all 25.

| Reader | Drive | Tone | Cab |
|---|---|---|---|
| FTm | +0.082 | +0.258 | +0.218 |
| `M-ridge` | +0.212 | +0.201 | +0.147 |
| `M-pcs` | +0.219 | +0.233 | +0.173 |
| `W-pcs` | +0.238 | +0.261 | +0.309 |
| `E-top`, the network's last layer | +0.175 | +0.212 | +0.239 |
| `E-mid`, its four published blocks | +0.246 | +0.319 | +0.264 |
| `E-mix` | +0.233 | +0.317 | +0.250 |
| `TE-mix` | +0.224 | +0.340 | +0.234 |
| `EW-mix`, post hoc | +0.255 | +0.316 | +0.297 |
| Zero-shot: W | +0.096 | +0.222 | −0.086 |
| Zero-shot: `P-pcs`, mel | +0.146 | +0.203 | +0.030 |
| Zero-shot: `PE-mix` | +0.165 | +0.279 | +0.024 |

- **Nothing moved on by the declared rule.** `E-mid − FTm` drive holds the bound by +0.003 but is not ahead of mel there. `E-mix − M-pcs` cab +0.077 [+0.039, +0.115] holds the bound against mel, the only such clear, on 12 of 12 other bootstrap seeds. `E-mix` took S5's slot on that.
- **Most of drive is FTm's weakness.** Head-standardised, `E-mid − FTm` is +0.017 [−0.067, +0.111]. FTm puts 68% of its drive answer variance on ac20Power, and `M-pcs` and `W-pcs` gain the same. Fixing FTm's spread needs no encoder.
- **Tone and cab gains over mel are soft.** Within amp track they are undecided. Tone rests on the main player, +0.149 against −0.065 on the rest, and on crunch. BKS repeats neither. `W-pcs`, whose filters saw the plugin, beats `E-mix` on cab, −0.058 [−0.103, −0.011].
- **The domain-gap idea is not borne out on real-trained readers.** Top and tuned features do sit nearer across domains than mel by AUC, `top` 0.849, `pub` 0.945, mel 0.971, but a body that saw the plugin still reads cab best.
- **Cab does not transfer zero-shot, even with no backing.** Fitted on clean plugin rows, read on real amp tracks alone: `A-mid` drive +0.249, tone +0.464, cab −0.028; mel +0.111, +0.468, +0.043. So tone transfers for any reader, EfficientAT adds drive, and cab's gap is the plugin-to-real gap itself.

## On plugin rows

Held DIs and held pool sessions, 1,222 rows, no real label, used to choose the input.

- Its middle blocks hear the knobs through an unheard backing better than its last layer. The authors' four blocks read 0.256 mean r against `top`'s 0.225 at 64 PCs.
- Kept beside mel with each block's own PCs, it adds to drive and tone and gives up nothing on cab: `mix:pub` against mel +0.093 [+0.074, +0.112], +0.036 [+0.020, +0.055], −0.013 [−0.034, +0.008]. Joint PCs lost cab.
- More PCs matter for mel too, chiefly cab: +0.186 at 24, +0.319 at 64, +0.344 at 128. This one check, made for fairness, changed the plan: every contrast with mel then used the same count.

## What their comparisons taught

On our task, `f15` on backed plugin rows, mean r:

| Their comparison | Their result | Ours |
|---|---|---|
| Width 0.4, 1, 2 | mAP 0.432, 0.471, 0.478 | 0.221, 0.244, 0.233: width stops paying at 1 |
| AudioSet against ImageNet only | ImageNet start adds 1.2–1.6 points | ImageNet only 0.109, untrained 0.073: the audio training is what helps |
| Blocks plus mel against the last layer | HEAR 86.2 against 76.2 | The same order: `mix:pub` 0.281, `pub` 0.256, `top` 0.225 |
| Mel alone on music | Beat every network-only set | Held at the same PCs: mel 0.243 against `pub` 0.256, and by the score the two sit within about 0.6% |
| Frozen wins on time structure, ties on colour | Combes's LFO rates and filter cutoff | Drive gains on plugin rows, tone is undecided, cab is worse |

The report's forecast held: "a tie is the likeliest result". Their other gains, distillation and an ImageNet start, come only through the weights.

## Found along the way

- **Mel reads better with more PCs.** `M-pcs` needs no download and no network, and is about as close as anything clean here. The ML session will read it on captures.
- **One backing's noise limits a read, by about the same in each group.** Averaged over backings, one backing reads +0.200, +0.340, +0.264 on GOAT and five random ones +0.244, +0.387, +0.298. This does not show what reading more of a song would add: a song has one backing, and these backings also back other rows of the fold. Holding their sessions out, `E-mix`'s tone moves −0.023 [−0.063, +0.017].
- **Labels.** A curve over shares of each fold's DIs rises to all labels on drive and cab, roughly. Its shares are uneven, 8–46% of rows at "25%", and tone at "50%" reads +0.259 and +0.398 by draw, so it says no more than that.

## Candidates and limits

- 58 reads in this study, 53 by knob and 5 by the score. Three amendments were made before any real label: mel at the same PC count, `pub` for `f15`, each block's own PCs. `EW-mix` was post hoc, and one scaling bug in it was found and fixed before its reads were used.
- W heard all 406 pool entries and lends GOAT its levels, so a lead with W's block in it may carry familiarity with the backings, which cannot be tested here.
- The search labels' limits stand: 520 labels on a 0.25 lattice, each label fitted on one window. GOAT is about 76% one player. BKS is one band.
- W and the tuned bodies saw BKS's DIs, and `E-mix` did not, so BKS can only flag them.

## Not tested

Fine-tuning on real rows, wider nets and DyMN, reading more windows of a song, and any ear read. The ML session will read `E-mix` and `M-pcs` on held capture units, with their DIs held out, under its own declaration.
