# EfficientAT plan

**Status: planned; nothing read yet. Results will go in `docs/efficientat-results.md`.**

**The user's request (2026-11-06):** "EfficientAT looks really promising, make sure to understand it deeply and leverage it off
possible. Think about a few approaches we can use it, plan carefully and test in isolation. Using a proven pre-trained model,
learning from their comparisons could definitely be valuable". This answers the question left open by the model comparison:
should EfficientAT be downloaded and tested.

## Resume here

Read this block first after any compaction, then the task list, then the findings log.

- **Session:** "ML models and scoring review", branch `claude/efficientat`.
- **Worktree:** `/Users/yoavbz/projects/neuraldsp-preset-generator/.claude/worktrees/ml-models-scoring-review-8db392`. Work only there.
- **Run from the worktree root:** `TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python`; tests with
  `/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python -m pytest tests/test_eat*.py -q -n0`.
- **Downloads:** `~/ndsp-presets/tools/efficientat/` (repo at a425fdce, 5 weight files, hashes in `learn/eat_net.py`). Weights load with `weights_only=True`.
- **Peers:** SendMessage to "NeuralDSP preset generator (ML)", "(executor)", "(controller)", "(cloud researcher)".
- **Now:** S2 and S3, plugin rows.
- **Running jobs and PIDs:** S2 and S3 on CPU, this session's background job; PID 42832, watched by the executor. Each job so far ran under 15 min.
- **Mac:** the ML session has nothing planned and will say before capture training starts. Keep jobs resumable so they can pause.
- **Disk:** 34 GB free, floor 33 GB; the controller asked to stop and tell ML and the executor at 33. `PF/eat/front` (1.5 GB) can be rebuilt in 15 min.
- **Blocked on the user:** S6, fine-tuning, waits for a yes with its measured length. The rest does not.

## What EfficientAT is

MobileNetV3s trained on AudioSet (about 2M clips) by knowledge distillation from PaSST transformers, MIT, 375 stars, last pushed 2024-11. `mn10` has
4.88M weights and reaches mAP 0.471. Its input is mono 32 kHz, pre-emphasised (−0.97), 25 ms windows, 10 ms hop, 128 mel bands 0–15 kHz, log power with fixed
constants, so level reaches the network. The body downsamples frequency and time by 32, so the last map on a 4.5 s half is 4 bands by 15 frames (11 on half A, whose first second is dropped), then global
average pooling drops frequency altogether.

Its published comparisons, all on AudioSet mAP: width 0.4 / 1 / 2 / 4 gives 0.432 / 0.471 / 0.478 / 0.484, so most of the gain is by width 1. Mel bands 40 / 64 / 128 / 256 give 0.453 / 0.461 / 0.471 /
0.474. Hop 5 / 10 / 15 / 20 / 25 ms gives 0.475 / 0.471 / 0.463 / 0.456 / 0.447. Dropping ImageNet pretraining moves mn40 from 0.484 to 0.483. Dynamic convolutions add 0.006 at width 1 and 0.013 at width 2.
The cloud researcher is reporting on these and on independent uses of the family; its report feeds S8.

## How this differs from what failed

| Tried so far | How it ended |
|---|---|
| W, FT, FTm: a CNN trained on our own 1,787 plugin rows, then real rows | Reads real rows weakly. Domain AUC 0.997. FTm's drive leans on ac20Power |
| Ridges on mel statistics and on W's layer | Undecided against FTm by the score |
| A small CNN, binned heads, one mixture component, a lower mic weight | None moved on. Lower mic weight is a lead |
| Hand-built inputs: long-term spectrum, cepstra, onsets, flatness, percussive residue | None shown better than mel statistics |

**What is really different.** Every model so far learned its filters from our own renders, so it could learn the plugin's fingerprint. EfficientAT's filters never saw the plugin, and were learned from
general audio at a scale we cannot reach. That is the one mechanism for the domain gap that has not been tried.

**Why it may still fail.** Tagging rewards ignoring how something was recorded, so a tagger may discard tone by design, and published AudioSet nets detect distortion poorly (PR #394). It changes nothing about the backing that hides the guitar,
or the search labels' noise, which caps any reader's r near 0.75–0.81. And the score may not resolve what it does: every contrast with FTm so far was undecided by the score.

**What each result means.** Hears the knobs on plugin rows, clean and backed, better than mel statistics: the features are worth reading on real rows. Transfers zero-shot better than W: the domain-gap mechanism is real, whatever the score says. Reads real rows
better than FTm by knob and undecided by the score: a lead for the ear, not an adoption. Hears nothing beyond mel statistics: a frozen encoder is ruled out for this task, and only fine-tuning stays open.

## Approaches

Each is tested on its own, against its own yardstick, in the order of the tasks below.

| Label | Approach | Why it might work | Stored input usable? |
|---|---|---|---|
| A1 `top` | The last layer's channel means and stds, ridge | The standard use of a pretrained encoder | No: audio |
| A2 `mid` | Middle layers, pooled over time only, so frequency stays, ridge | Low and middle filters are generic, the top is tuned to classes, and tone and cab are spectral shapes that global pooling removes | No: audio |
| A3 `mix` | `mid` joined to the mel statistics, ridge | Published leads for this family lean on a mel summary (Combes et al. 2025) | No: audio |
| A4 `tag` | AudioSet's own outputs, such as Distortion, Effects unit and Electric guitar, with no fit | Needs no training rows, so it has no domain gap to cross. Its Distortion output already fires on GOAT tracks | No: audio |
| A5 `tune` | The pretrained body in W's place, trained on plugin rows, then on real rows. Waits for the user's yes | Frozen features may lack tone, and fine-tuning can restore it while keeping generic filters | No: the rebuilt audio |
| A6 `judge` | Distance between middle-layer statistics of render and target, as a judge term | Deep feature distances are a common stand-in for perceptual distance | No: audio |

## Rules for this work

The model comparison's rules hold unchanged ([model-comparison-plan.md](model-comparison-plan.md), "Rules for this work"), confirmed by the ML session on 2026-11-06: at most 3 render processes and one GPU job on the Mac, resumable jobs, announce each render or MPS run with its size and PIDs, disk floor 33 GB, kill only PIDs this session launched, BKS and GOAT only for choosing, W's plugin rows through `recipe_inputs`, `plugin_rows` and `rung_rows` with W's stored `train_ids`, no NS row in a fit, a choice or a printout. Closed: capture labels and `trusted` units, `captures/`, `captures2/`, `reads_capture`, N6's set, the panel (read twice), L0 and V-real audio, L2, `tone-probe/mask*`, `~/ndsp-presets/listening/`.

Also:
- New files only: `learn/eat_*.py`, tests beside them, ledger entry `efficientat`, outputs in `PF/eat/`. `learn/reads_v3.py` unchanged (sha a04785f3a4838ae2).
- `learn/eat_build.py` calls `P.cmd_build_wide` and `P.cmd_build_dfix_real` with their paths and feature step replaced at run time. `pipeline_fix.py` itself does not change. Real units come from `dfix_units()`, with `captures=False`.
- Downloaded code is not imported. `learn/eat_net.py` is this repo's own copy of the network, proven equal to theirs in S0.
- Report band- and part-weighted. Undecided is not failed. "By the score" is never "by the ear". Measured runtimes only.
- An unbiased reviewer on this plan and each amendment, every result audited before write-up, a PR that passed review and CI merged.
- GOAT and BKS have been chosen on many times, so count every candidate. Before this plan: 22 reads of 20 models.

## Tasks

Legend: `[ ]` to do, `[~]` in progress, `[x]` done.

### S0, the tool (done, no labels)
- [x] S0.1 `learn/eat_net.py`, the network with no torchvision or torchaudio. On all five weights, logits and features equal EfficientAT's own model code exactly (difference 0), and the mel bank matches torchaudio's within 1.3e-5.
- [x] S0.2 Tags: the repo's metro clip reads Train 0.81, Rail transport 0.65. GOAT amp tracks read Music, Guitar, and on some, Distortion and Effects unit.
- [x] S0.3 Can stored 96-band mels stand in for its input? Measured on 120 GOAT amp clips, offsets fitted on half, read on the rest, no labels (findings log). Yes for low layers, no for high ones. So every use here takes rebuilt audio, and the adapter is dropped.

### S1, rebuilt audio (CPU, zero renders, no labels)
- [x] S1.1 `learn/eat_build.py`: EfficientAT's input for W's 1,787 rows, clean and in their first 4 pool backings, and BKS's and GOAT's 316 labelled units in their 25 backings and on their amp tracks alone: 17,151 inputs, 15 min on three shards, 1.5 GB. On every 25th input the rebuilt audio's usual mel must match the stored input within 1 grid step, or the build stops: worst 0.
- [x] S1.2 `learn/eat_embed.py`, `mn10_as`, 2 min on MPS. Per half, mean and std of each channel at layers 1, 3, 6, 12, 15, 16 (`g`), the same pooled over time only at layers 3, 6, 12, 15 (`f`), and logits. Half A's masked frames dropped first, as `summary_of` drops them. Checked: on 64 inputs MPS and CPU agree within 1e-5 relative.
- [x] S1.3 After S3.2: `mn04_as`, `mn20_as`, `mn10_im` and an untrained `mn10` (seed 20261042), on clean and all 4 backings, `top` and `mid` only. The two non-AudioSet nets re-estimate batch norm on 512 of those inputs, no labels.

### S2, does it hear the knobs with nothing in the way? (CPU, plugin rows only)
- [x] S2.1 Clean targets, W's rows, 4 folds on whole DIs, so no held guitar part is in training. Each row in one fold. Readers through `B.candidate_answers` unchanged: within-cell centring, PCs in the fold, ridge with alpha from inner folds on whole DIs, residuals around the cell's mean, searched heads only. Each dimension scaled by its sd on the `wide` set, no labels. The mel reference runs through the same code on the stored `tgtl-cc` inputs. Output: r by group through `reads_v3.corr`, with DI-bootstrap intervals on each paired difference from mel. Output `PF/eat/s23-*.json`.
- [x] S2.2 Controls in the same run, on `top`: under shuffled labels within cell r stays near 0, and with the label spiked into the input it reads above 0.9. The spike is 10 × √dimensions: the comparison's fixed 30 is too small against 1,920 unit-scaled dimensions. At 24 PCs the bar failed, 0.69, 0.53, 0.80: plugin rows search 85 heads and 24 PCs cannot hold them, the same cap `P-ridge`'s spike showed in the comparison (0.60, 0.53, 0.86). At 128 PCs it reads 1.000, 1.000, 0.999.

Representations: `top` (`g` at layer 16), `g-L` for each layer, `f-L` for each `f` layer, `multi` (the `f` layers, each block scaled to unit total variance, joined), `logits`.

### S3, through a backing (CPU, plugin rows only)
- [x] S3.1 The same rows and DI folds. Pool sessions (21) fold too: a held row reads its first backing of a session held in that fold, and training rows use only their backings of other sessions. So no held guitar part and no held backing session is in training. About 1,220 held rows. Same representations, and the mel reference on the same backings' stored inputs. Real reads share the pool across models, so contrasts between models stand there, but absolute r is optimistic and is compared within a set only.
- [x] S3.2 **Choosing `mid` and the PC count, on plugin rows alone.** At 24 PCs, `mid` is the `f-L` or `multi` with the highest mean r over drive, tone and cab in S3, on `mn10_as`; ties within 0.01 go to the simpler. Then `top` and `mid` at 24, 64 and 128 PCs: the count with the highest mean r, the smaller within 0.01. Fixed before any real row is read, and logged. It selects on r, not on a clear against mel. **Chosen: `mid` = `f15`, 64 PCs** (findings log).
- **Amendment, after S3.2, before any real label: mel at the same PC count.** The plan kept the mel references at 24 PCs. On plugin rows that flatters EfficientAT: more PCs lift mel as much, chiefly on cab (S3, backed: mel's cab +0.186 at 24, +0.319 at 64). So every contrast with mel uses the same count, `M-pcs` and `P-pcs` at 64. `M-ridge` and `P4-ridge` at 24 stay as plain rows. `M-pcs` and `P-pcs` are new readers in their own right, counted, and read against FTm and W.
- [x] S3.3 Their comparisons on our task: `mn04`, `mn10`, `mn20`, `mn10_im` and the untrained `mn10` on `top` and `mid`. Report only. If the untrained net matches the AudioSet one, pretraining is not what helps. Calibrated random filters with a ridge can read plugin rows well, so this cannot rule pretraining out for real rows.
- [x] S3.4 The domain direction, report only: the AUC of a ridge telling plugin backed rows from real backed rows, on `top`, `mid` and mel statistics, and the cosine between that direction and each group's knob direction.
- [ ] S3.5 **The domain gap with no backing.** Readers fitted on W's clean rows, read on each held unit's amp track alone: `A-top`, `A-mid`, `A-mel`. Report only, counted as 3 candidates. Stored amp-track inputs give the mel reference on the same audio. BKS's own DIs are among W's rows (628 rows), so only GOAT is zero-shot here.

### S4, real rows by knob (CPU, BKS and GOAT, through `reads_v3`)

Nine candidates, read once, through `B.add_candidates` and `R.report`:

| Label | Input | Trained on | Primary reference | Mel reference |
|---|---|---|---|---|
| `E-top`, `E-mid`, `E-mix` | A1, A2, A3 | real rows, all 25 backings, by fold | FTm | `M-pcs` |
| `PE-top`, `PE-mid`, `PE-mix` | A1, A2, A3 | W's plugin rows, 4 backings, zero-shot on GOAT | W | `P-pcs` |
| `M-pcs` | mel statistics, 64 PCs | real rows, as `M-ridge` | FTm | — |
| `P-pcs` | mel statistics, 64 PCs | W's plugin rows, 4 backings | W | — |
| `W-pcs` | W's last hidden layer, 64 PCs | real rows, as `W-ridge` | plain rows only | — |

`W-pcs` sits beside each `E-` as a plain row: the same reader at the same count on filters learned from the plugin, which is the plan's mechanism. FTm mixes reader and filters. `M-ridge`, `W-ridge` and `P4-ridge` (`P-ridge` refitted on the same 4 backings, a new read, counted) stay at 24 PCs as plain rows.

- [ ] S4.1 `learn/eat_read.py check`. Control: `M-ridge`'s stored answers reproduce from stored mels through this code within 1e-6. Then shuffled labels on all nine, and the spike on `E-top` and `PE-top`. At 64 PCs `PE-top`'s spike is capped as S2.2 explains: plugin rows search 85 heads.
- [ ] S4.2 The ledger's entry states `mid` and the PC count. The read, `PF/eat/read.json`, with the bound over 42 contrasts: each candidate against its primary and its mel reference, on drive, tone and cab. By-player rows on GOAT, the crunch-drive row, and `p_family` from `B.family`.
- [ ] S4.3 Audit by recomputation. Log.
- [ ] S4.4 `tag`, report only, counted as 5 candidates, listed in the ledger as `tag:<class>`: each class's logit as an answer, no fit, by group, on the backed input and the amp track. Classes, fixed here: Distortion, Effects unit, Electric guitar, Reverberation, Echo.

**Declared rule for S4.** Effect sizes first. Selection is on the simultaneous 95% lower bound over the 42 contrasts on one set of GOAT item weights, with the plain 90% interval beside. A plain clear that the bound does not hold is a lead, not a move.
- An `E-` candidate moves on if the bound of `candidate − FTm` clears zero in a group, its plain intervals against both `M-pcs` and `M-ridge` clear zero in that group, and no group's plain interval against FTm sits wholly below zero. FTm's drive is depressed by misplaced spread, so clearing FTm alone can mean no gain over a plain ridge. Both mel readers count because more PCs helped mel on plugin rows, which real rows may not repeat. `M-pcs` itself moves on by the same rule without the mel clause.
- A `PE-` candidate moves on if the bound of `candidate − W` clears zero on cab or drive, its `p_family` on that group is under 0.05, and its plain intervals against both `P-pcs` and `P4-ridge` clear zero there. W reads cab backwards, so a deaf reader sits about +0.09 above it. `P-pcs` itself moves on by the same rule without the mel clause.
- BKS never selects, and can flag a candidate in its own row. `PE-` on BKS is not zero-shot: 35% of W's rows render BKS's own DIs, and 70 of 406 pool entries are BKS's. GOAT has neither. GOAT is about 76% one player, so each label's r on that player and on the rest is reported.
- Candidates so far: 22 reads of 20 models. This plan adds 10 here, counting `P4-ridge`, 3 in S3.5, 5 in S4.4, and any later ones, all stated in the results.

### S5, by the score (renders, 3 slots)
- [ ] S5.1 At most two models, 1,340 renders each. First slot: the EfficientAT candidate with the highest simultaneous lower bound against its mel reference, unless its plain interval against that reference sits wholly below zero, in which case only what moves on goes. Second slot: `M-pcs` or `P-pcs` if it moved on, the higher bound against FTm or W first, else the next EfficientAT candidate that moved on, else none. `bakeoff_render.py`'s `predict` takes only listed real-trained ridges and its `fit_fold` hardcodes real rows and RcBG, so `learn/eat_render.py` has its own fit: `E-` as `fit_fold` with this feature, and `PE-` with residuals fitted around the plugin cell mean, added to RcBG's values. Read 2 needs one GOAT unit with no labelled row, `goat/item_68@35.0#amp_5`: `eat_build real --reads-only` and its own embed set. Judges of FTm, RcBG, S and `M-ridge` are read from `PF/bakeoff/`, new ones written to `PF/eat/`. Check first: FTm's stored answers reproduce. Report `candidate − centre`, `− FTm`, `− M-ridge`, `− S`, by item on GOAT and by DI on BKS. `M-ridge`'s stored judges are at 24 PCs, so that row compares unequal counts unless `M-pcs` took a slot. Announce size and PIDs. Audit. Log.

**Declared rule for S5.** Nothing is adopted. Closer than FTm on GOAT by item, by the score, is a lead, stated with the labels' limits and the count of candidates. Which model goes to an ear page or to L2 is for the ML session and the user.

### S6, a judge term (CPU, zero renders)
- [ ] S6.1 `learn/eat_judge.py`. Terms `J-f6` and `J-f12`: the mean absolute difference between render and reference in `f` statistics at layers 6 and 12, per dimension scaled by its sd on the `wide` set, so no ear data sets any scale. J0 has no level-matched waveform: `bakeoff_judge.band_errors` takes a median in log-mel over the frames where the DI plays. Here the render is brought to the reference by the gain that matches their LUFS over the whole half, a simplification that J0's own frame-wise level step does not make, then both pass through `eat_net.front` and the network, in 4.5 s windows at J0's `HALVES`. Data as `bakeoff_judge.py`: `learn/trusted-data/judge-ear/` and `judge-v5/`, CPU only.
- [ ] S6.2 The same battery and the same pass rule as the model comparison's T3.4, in-sample, a screen. A pass leads only to a proposal for a fresh blind page.

### S7, write-up
- [ ] S7.1 `docs/efficientat-results.md`: each approach's answer, what their comparisons taught, what was not tested. Add the researcher's report. Log its claims against S3.3.
- [ ] S7.2 ROADMAP and DOCS-INDEX lines. Review, CI, merge. Memory.
- [ ] S7.3 Plain report to the user, with the fine-tuning question below.

### Waiting for the user's yes: fine-tuning

Not run without a yes for this run, since the model comparison listed fine-tuning as needing one, and the user's words here name no training. The report states its difference from what failed, what S2 to S4 found, and a measured length. Its design, after the review:

| Order | Arm | What changes | Start |
|---|---|---|---|
| 1 | `T-head` | W's heads on the frozen `mn10_as` body, tapped at `mid`'s layer if S3 chose one, eval mode | AudioSet weights, on plugin rows with one DI fold held |
| 2 | `T-body` | The whole body unfrozen at 6e-5, their ESC-50 rate, training-mode batch norm | Arm 1, both seeds |
| 3 | `T-rand` | As arm 2 from random weights at W's rate | Fresh, both seeds |
| 4 | `T-ctl` | W retrained once on the same held DI fold, so all three have a plugin-row holdout | As W |
| 5 | `T-real` | Real rows by fold: heads at 1e-4, body at 2e-5, with E re-chosen by counted inner runs, 8 per arm, since FTm's stored E and rate would leave weights almost still | Arm 2 |

- All arms read the rebuilt inputs, not an adapter, so they see 4 backings against W's 24: a handicap to state. A batch crops each half to its last 350 frames, half A's whole length. Arms 2 to 4 use W's 60 epochs and the `final` state, with no NS tracking. `T-ctl` draws its ids from W's `train_ids` less the held DIs, not `plugin_rows --fold`, which reads NS.
- Arms 2 and 3 are read zero-shot through `reads_v3` as two counted candidates, with the label-free domain measure per arm. Stop only if arm 2 loses on both to arm 3. Plugin-row r alone cannot gate this: a random body can win it by learning the plugin's fingerprint.
- `A-ctl − FTm` understates this arm's seed noise, since it shares W's start, so report the gap between its seeds.

## Findings log

Newest last. Each entry: date, task, result, output path, audited by whom.

- 2026-11-06, S0.1: network parity on `mn04_as`, `mn10_as`, `mn20_as`, `mn10_as_mels_64`, `mn10_im`: difference 0 in logits and features on random input. Mel bank within 1.3e-5 of torchaudio 2.8.0's. Weight hashes in `learn/eat_net.py`.
- 2026-11-06, S0.3: stored mels through interpolation and a per-band offset, against the true front, on 60 held GOAT clips, `mn10_as`. R² of clip-to-clip embedding differences: layers 0–4 0.89–0.95, 5–6 0.83, 7–10 0.70–0.72, 11–12 0.53–0.56, 13–15 0.40–0.49, last 0.37. On one item's two amp tracks: 0.85–0.92, 0.71, 0.58–0.60, 0.37, 0.22–0.30, 0.10. Tag correlations 0.47–0.79. `mn10_as_mels_64` is no cure on the last layer, 0.61 and 0.20. Not audited: a screen that only decided to rebuild audio.
- 2026-11-06, the plan's review (independent, code read): 10 must-fix and 9 suggestions. Fixed or adopted: no adapter; DI and session folds; `E-` must also clear `M-ridge`; `PE-` must clear `p_family` and `P4-ridge`; `mix` scaling; stored-row join by position; `P4-ridge`; `W-ridge` beside; the amp-track rung; PC counts on plugin rows; S5's route for `PE-` and the extra unit; S7's level step (now S6); fine-tuning moved behind the user's yes and redesigned. One suggestion not taken: cutting `mn10_im`, since it costs seconds.
- 2026-11-06, S1.1: 17,151 inputs. Parity worst 0 grid steps on all 692 checks, trials included. `PF/eat/front/record-*.json`.
- 2026-11-06, S1.2: `mn10_as` on all four sets, 2 min on MPS, 0.6 GB. MPS and CPU within 1e-5 relative on 64 inputs.
- 2026-11-06, the amendment's review (same reviewer): 11 faults, none in leakage. Fixed: `cmd_tags`'s rows; `mix:multi`'s double scaling; alpha and bootstrap on whole DIs (the first S2 and S3 run was stopped and discarded for this, and no selection was made from it); the cache folder names net, `mid` and PCs; `declared` takes subsets, and `cmd_tags` is declared; mel keeps 24 PCs; the spike's size, set before the rerun; S5's own fit, extra unit and stored judges; S6's gain step; the fine-tuning proposal's crop, epochs, ids and single rate.
- 2026-11-06, S2, `PF/eat/s23-mn10_as-pc24.json`, 1,787 held rows, clean, mean r over drive, tone, cab at 24 PCs: `f3` 0.411, `multi` 0.402, `f6` 0.393, `f12` 0.392, mel 0.382, `g12` 0.377, `f15` 0.370, `top` 0.350, `logits` 0.331. Shuffled labels: −0.02, +0.06, +0.03.
- 2026-11-06, S3, same file, 1,222 held rows, backed, 24 PCs: `f12` 0.220 (drive 0.295, tone 0.184, cab 0.179), `f15` 0.217 (0.281, 0.181, 0.190), `multi` 0.205, `f3` 0.201 (0.207, 0.160, 0.237), `f6` 0.200, `g15` 0.197, mel 0.182 (0.199, 0.161, 0.186), `top` 0.179 (0.239, 0.146, 0.151), `logits` 0.172. Shuffled: 0.00, −0.02, 0.00.
- 2026-11-06, S3.2: `f12` and `f15` tie within 0.01, `f12` ahead by 0.002. "Simpler" was defined at the tie as fewer dimensions, 1,280 against 1,792: `mid` = `f15`. By depth `f12` would win. `f15` sits one 1×1 conv below `top`, with 4 bands, so `E-mid` may stay close to `E-top`. PC count, mean of `top` and `f15`, backed: 24 0.198, 64 0.235, 128 0.244. On the mean 128 is within 0.01 of 64 (0.0086), so 64. On `f15` alone the gap is 0.0104 and would give 128, so the choice is thin. At 64: `f15` drive 0.305, tone 0.212, cab 0.215; `top` 0.293, 0.193, 0.190. The first S2 and S3 run, with alpha on sections, was stopped and not read for a choice beyond the reviewer's glimpse of its clean log.
- 2026-11-06, the fairness check that led to the amendment, mel on plugin rows, backed: 64 PCs drive 0.218, tone 0.191, cab 0.319, mean 0.243; 128 PCs 0.224, 0.198, 0.344, mean 0.255. Against `f15` at the same count: `f15` is better on drive, undecided on tone, worse on cab. `mix:f15` at 64 PCs: 0.291, 0.218, 0.213, mean 0.241, no gain. Stored by S3's closing runs below.
- 2026-11-06, S3 at 64 PCs for the record, `PF/eat/s23-mn10_as-pc64.json`, backed, against mel at the same count, 90% DI-bootstrap: `f15` drive +0.087 [+0.070, +0.104], tone +0.022 [−0.006, +0.052], cab −0.104 [−0.135, −0.077]. `top` +0.075, +0.003, −0.129. `mix:f15` +0.073, +0.027, −0.106. So on plugin rows a frozen `mn10` beats mel on drive, is undecided on tone, and is worse on cab.
- 2026-11-06, S3.3, `PF/eat/s33-*.json`, `f15` at 64 PCs, backed, drive, tone, cab, mean: `mn04` 0.293, 0.180, 0.190, 0.221; `mn10` 0.305, 0.212, 0.215, 0.244; `mn20` 0.312, 0.183, 0.204, 0.233; ImageNet-only `mn10` 0.166, 0.061, 0.100, 0.109; untrained `mn10` 0.092, 0.060, 0.066, 0.073. AudioSet training is what helps, and width stops paying at 1, as in their mAP curve. Clean rows narrow the gaps: `mn10_im` 0.359, untrained 0.189, `mn10` 0.398, so what AudioSet adds most is hearing through a backing.
- 2026-11-06, S3.4, `PF/eat/s34-mn10_as-pc64.json`, domain AUC at 64 PCs, plugin against real backed inputs, held by DI: mel 0.971, `f15` 0.893, `top` 0.849. Mean absolute cosine of knob and domain directions: `f15` 0.12, 0.16, 0.25; `top` 0.07, 0.14, 0.07; mel 0.15, 0.07, 0.12. The features do sit nearer across domains than mel, which is the mechanism the plan named. This is the plan's first evidence for it, on no real label.
- 2026-11-06, S3's records were rerun with mel at each file's PC count: `PF/eat/s23-mn10_as-pc64.json` with controls, `-pc128.json`.
- 2026-11-06, the amendment's third review: 5 faults, all fixed: both mel readers in the clause; the placebo on every reader; `W-pcs` at the same count; S5's slots ordered; the records.
