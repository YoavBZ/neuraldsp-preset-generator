# Model comparison plan

**Status: draft under review. The research report is in (PR #394). No candidate has been read, and nothing has rendered or trained.**

**The user's request (2026-11-05):** "Yes, but first research about neutral networks and which kind fits our use case best,
same for feature extraction and scoring/judging. Finally write a detailed plan/tasks for easier and more organized process
(it will also assist with session context compaction which must not harm the process and its result when occur). Then
starting working. You can render whatever needed, just make sure to sync with the ML session since the Mac resources are
shared". The "Yes" answers a proposed no-render comparison of model types.

**Why.** The deep review ([ml-deep-review-2026-11.md](ml-deep-review-2026-11.md)) compared versions of one network. Network
type, size, features and judge were never compared with alternatives, so "best model" so far means the best version of one
residual CNN.

## Resume here

Read this block first after any compaction, then the task list, then the findings log.

- **Session:** "ML models and scoring review", branch `claude/model-comparison`, this worktree only.
- **Now:** T2.1, this plan, with the report's citations being checked by a subagent.
- **Next:** T2.2, an independent review of this plan, then T2.3 and Phase 3.
- **Running jobs and PIDs:** none.
- **Render or MPS use announced to the ML session:** none. The ML session's renders are finished and the 3 slots are free; it plans
  none tonight and will say first if an audit asks. Disk 36 GB free, floor 33 GB: outputs stay small.
- **Blocked on the user:** nothing yet. The user went to sleep at about 22:40 on 2026-11-05 (controller): carry on as far as the
  rules allow, and when finished send the controller two or three plain lines on what was found, checked and left open.

## Rules for this work

Set by the ML session on 2026-11-05 unless marked. They hold for the whole plan.

**The Mac**
- At most 3 render processes on the whole Mac, the ML session's and ours together. `_wait_cap` does not count `night2` or
  `capture_labels`, so check `pgrep` before each launch.
- Renders run as resumable shards. When the ML session says its centre read is about to start, finish the process in hand,
  start no other, and resume when it says.
- Before each render batch or MPS run, tell the ML session its size and PIDs.
- MPS is ours while the ML session is not training: one GPU job at a time on the whole Mac (the controller's rule of 2026-11-05,
  which replaces the ML session's 2), un-niced (`setopt no_bg_nice`), loss on CPU (the stft gradient bug).
- Disk guard 31 GB, 39 GB free at the start: stop new builds under 33 GB free and tell the executor (controller, 2026-11-05).
  Keep outputs small, store no audio or feature dumps.
- Morgan rules: `isolate=True`, one priming render, 0.25 s trim, a fresh process for time effects.
- Kill only PIDs this session launched. Leave render processes of others and anything PACE-related alone.

**Sets**
- Allowed for choosing: BKS and GOAT, through `learn/reads_v3.py` unchanged (sha a04785f3a4838ae2), folds as they stand.
- Off limits: capture labels and `trusted` units, `captures/`, `captures2/`, `reads_capture`, the panel, NS rows, `cc/rows`,
  L0 and V-real audio, `tone-probe/mask*` until N7 is written up, and `~/ndsp-presets/listening/`.
- N6's set: no candidate reads it before N6 has run; after that, only by asking the ML session and with its own declaration.
- L2 is not for choosing. At most one model goes in, picked beforehand, with S and a placebo.
- So finalists stop at BKS and GOAT by the score. GOAT and BKS have been used to choose many times: report selection across
  candidates in full, and state the search labels' limits.

**Files**
- New files only in `learn/` (`learn/bakeoff*.py`), tests beside them. Change none of the ML session's files.
- Own ledger entry (`test_id: model-comparison`) and this plan doc, declared before each read. Not the `pipeline-fix` entry
  or `docs/pipeline-fix-plan.md`. Small dated lines in ROADMAP and DOCS-INDEX are fine.
- Outputs in `PF/bakeoff/` (`~/ndsp-presets/learn/trusted-data/pipeline-fix/bakeoff/`).
- Never switch the main checkout.

**Recipes.** Any recipe takes extra real rows later, with the searched-head mask and a drop key on the DI file (`di`), which
holds out more than `di_item` does.

**Training.** Training longer than minutes needs the user's yes for that run, unless it is in a plan the user approved
(standing rule). Its measured length is stated when asking.

**Review.** An unbiased reviewer on every plan change, amendment and PR. Every result audited before it is written up.
A PR that passed review and CI is merged, then work continues.

**Reporting.** Band- and part-weighted. Undecided is not failed. "By the score" is never "by the ear". No fixed pass bars
beyond what is declared here. Measured runtimes only, no engineering estimates.

## Surviving compaction

1. This file is the record. Each task's state, each declared rule and each result is here, not only in the conversation.
2. After every finished task: tick it, update "Resume here", add to the findings log, commit, push.
3. Every long job writes to `PF/bakeoff/<task>/`, resumes from what is there, and records its command, seed, git sha and PID
   in a `run.json` beside its output.
4. A result is copied to the findings log, with its output path and sha256, before anything is built on it.
5. Memory `model-comparison-state` points here, so a new context finds this file first.

## Tasks

Legend: `[ ]` to do, `[~]` in progress, `[x]` done.

### Phase 1, sync and research
- [x] T1.1 Sync with the ML session: terms above.
- [~] T1.2 The cloud researcher's report on network types, features and judging, PR #394, read. Key claims being checked.

- [x] T1.3 Harness `learn/bakeoff.py`, with `tests/test_bakeoff.py`: candidates go through `reads_v3.report` unchanged.
  Done when `control` reproduces N1's stored r and swap totals within 1e-6 on BKS and GOAT, and a shuffled-label placebo
  reads near zero. Reads no candidate.

### Phase 2, plan
- [~] T2.1 Set candidates, features and judge measures from the report and write each read's declared rule here.
  The report: PR #394, `docs/research/model-features-judge-fit-2026-11.md`. Its key citations are being checked against sources.
- [ ] T2.2 Independent review of this plan; fix what it finds.
- [ ] T2.3 Ledger entry `model-comparison` listing the candidates; PR with this plan; merge after review and CI.

### Phase 3, reads without renders or training (CPU, `learn/bakeoff.py`)

All on BKS and GOAT through `reads_v3`, on real rows held by fold. Family: the 13 candidates below, with FTm, FT and W beside.
Everything is reported, dropped arms included, each with `p_family` (the largest r of any candidate under one label permutation).

| Label | Input | Reader | Trained on | Asks |
|---|---|---|---|---|
| `M-ridge` | `mel`: band means, stds, LUFS | ridge on 24 PCs | real rows | The reference, and the review's small model |
| `M-rrr` | `mel` | reduced rank 4, per amp | real rows | Does the labels' low dimension help? |
| `M-knn` | `mel` | k nearest | real rows | Retrieval by mel statistics |
| `M-trees` | `mel` | boosted trees | real rows | Named in the user's yes; the report expects overfitting |
| `W-ridge` | W's last hidden layer | ridge | real rows | Are W's features better than its heads? |
| `FTm-ridge` | FTm_k's last hidden layer | ridge | real rows | The same for FTm, the fold's own model |
| `P-ridge` | `mel` | ridge on 24 PCs | plugin rows only | Is the CNN needed for what W reads with no real rows? |
| `ltas` | band means, 80 Hz–5 kHz, floor −45 dB, LUFS | ridge | real rows | Tone and cab, report B2 |
| `ceps-lo` | DCT orders 1–20 of band means, LUFS | ridge | real rows | Tone and cab, report B4 |
| `onset` | band means and stds on attacks and sustains apart, LUFS | ridge | real rows | Drive, report B1 |
| `flat` | spectral flatness mean and std, in all and in 8 coarse bands, LUFS | ridge | real rows | Drive, report B1 |
| `hpss` | means and stds of the percussive residue, LUFS | ridge | real rows | Drive, report B1 |
| `ceps-hi` | DCT orders 21–60 per frame, mean and std, LUFS | ridge | real rows | Drive, report B4 |

Fixed choices: attacks are the 60 ms after peaks in positive spectral flux, sustains the other frames; ridge's alpha and k come from
inner folds on whole clusters; the 24 PCs are fitted inside each training fold, after centring within cell. Inputs come from the stored
mels, so nothing here needs audio. Readings for drive also run on crunch alone, the review's step 3.

- [ ] T3.1 Add the inputs and readers, with unit tests, to `learn/bakeoff.py`. Rerun `control` and `check` on the final code.
- [ ] T3.2 `bakeoff read`, output `PF/bakeoff/read-a.json`. Measured so far: the base rows 3 min, `check` under 2 min.
- [ ] T3.3 Independent audit of T3.2 by recomputation, before any result is built on.
- [ ] T3.4 Judge battery on stored pages, CPU, nothing installed. Terms: J0 `distance`, `tonal`, and a cross-fitted per-band term
  (the band's mean dB error on odd 1 s blocks times that on even blocks, averaged over scored bands, signed square root). Data:
  `learn/trusted-data/judge-ear/` and `judge-v5/` renders with `score.json`, and the review's known-error renders. Checks, from the
  report: the flip between single-note and chord DIs, treble steps not filling the top three, heard drive steps above unheard, and the
  effect size against d in split-half SDs. No weight is fitted unless a term passes the flip and the sensitivity check.
- [ ] T3.5 Audit T3.4. Log both results. Choose what moves on by the rules below.

**Declared rules for Phase 3.** Effect sizes first; no pass bars beyond these.
- A reader or frozen network moves on if `candidate − FTm` clears zero on GOAT in any group.
- An input moves on if `input − M-ridge` clears zero on GOAT in its target group: drive on crunch for `onset`, `flat`, `hpss`,
  `ceps-hi`, and tone or cab for `ltas`, `ceps-lo`.
- `P-ridge` is read against W on GOAT; level or better means the plugin read needs no CNN.
- `M-ridge` goes to Phase 5 regardless: the ML session handed over the review's step 2.
- BKS never selects. It can flag a candidate, in its own row. An interval reaching zero is undecided, not failed.
- If two candidates move on for the same group, both are reported and the one with the simpler input goes first.

### Phase 4, training arms (MPS, one job at a time, `learn/bakeoff_train.py`)

Each arm keeps W's data and FTm's recipe (`P.fit`, `P.WideData`, `P.DfixData`, the searched-head mask, lr 1e-4) and changes one thing.
As a screen, each FT_k takes FTm's stored E(k, s), chosen without fold k, so no inner runs. Measured: W 10.0 min, FTm_k 5.8 min, so an
arm with a new W is 2 × 10 + 8 × 6, about 68 min, and one on W's stored state about 48 min. The ML session is told before each arm, with its
size and PIDs. This plan declares these runs, as the controller's note of 2026-11-05 requires. Outputs and checkpoints stay in `PF/bakeoff/runs/`,
kept under 1 GB.

| Arm | Change | W retrained? | Order |
|---|---|---|---|
| `A-cat` | Knobs as 21 smoothed bins, median readout, on the masked heads; each family's loss in one unit, fixed weight 1 | Yes | 1 |
| `A-cnn` | A Comunità-size body: 2 conv layers, dense 120 and 60, same heads | Yes | 2 |
| `A-k1` | The mixture with K = 1 and an sd floor of 0.07 | Yes | 3 |
| `A-mic` | FTm with the mic loss weighted 0.1 | No | 4 |
| `A-in` | Surviving inputs from Phase 3 as a second branch, only if any survive | Yes | 5 |

- [ ] T4.1 Read `P.cmd_train`, `P.cmd_train_ft` and `P.fit`; write `learn/bakeoff_train.py`, new file, nothing in `pipeline_fix` changed.
  Any recipe takes extra rows later, with the mask and a drop key on `di`.
- [ ] T4.2 Control: an unchanged arm on one fold and seed must follow FTm's logged losses. Size about 16 min.
- [ ] T4.3 Run the arms in order. Each `run.json` records command, seed, git sha, PID, minutes. Hand the watch to the executor at launch.
- [ ] T4.4 Each arm through `reads_v3`, paired against FTm. Audit. Log.

**Declared rule for Phase 4.** An arm moves on if `arm − FTm` clears zero on GOAT in a group while no group's interval sits wholly below
zero. `A-cnn` level with FTm in all groups means network size is not the lever; spend no more on backbones. `A-k1` level with FTm means
the mixture adds nothing. An arm that moves on gets the full nested recipe (8 inner runs) before Phase 5.

### Phase 5, by the score (renders, after the ML session's hold lifts)

- [ ] T5.1 `learn/bakeoff_render.py`: answers in `goat/answers` and `real/answers`' shape, each direction read from its search half,
  on read 2's units; judged by `analysis.aligned`, storing `distance`, `tonal` and the cross-fitted term on the held half. New output
  directory, no audio kept. `M-ridge` and any ridge are centre plus predicted residual on searched knobs; switches and mics stay the
  centre's, every other control S, so `ridge − centre` reads only the knob gain. Check: FTm's stored answers rendered through it reproduce
  10 stored judge values exactly, the ML session's 20-render recheck in small.
- [ ] T5.2 `M-ridge`, then at most two finalists from Phases 3 and 4. About 1,340 renders each (670 answers, 2 renders each; the deep
  review's "about 670" counted answers), about 12 min on 3 processes at 1.6 s. Shards resumable; announce size and PIDs; stop when the
  ML session asks.
- [ ] T5.3 Report `candidate − centre`, `candidate − FTm`, `candidate − S`, by item on GOAT and by DI on BKS, by fold beside, with t
  intervals, `tonal` beside `distance`, and d_S strata. Audit. Log.

**Declared rule for Phase 5.** Nothing is adopted here. BKS and GOAT are development sets, chosen on many times. A finalist closer than FTm
on GOAT by item, by the score, is a lead, stated with the search labels' limits and the count of candidates tried. Which model goes to L2,
or to an ear page, is for the ML session and the user.

### Phase 6, write-up

- [ ] T6.1 `docs/model-comparison-results.md`: answers on network, features and judge, with every candidate's row and what was not tested.
- [ ] T6.2 Small dated lines in ROADMAP and DOCS-INDEX. Correct the deep review's "about 670 renders".
- [ ] T6.3 PR, independent review, CI, merge. Update memory `model-comparison-state`.
- [ ] T6.4 Plain report to the user, and two or three lines to the controller.

### Waiting for the user's yes

Not run tonight: each needs a download, or more than this plan declares.
- Downloads: EfficientAT mn10 weights, AFx-Rep weights, HAAQI or GstPEAQ, kadtk. None is on disk. These would add report steps 0d, 0e and
  0f: frozen encoders on rebuilt audio, and auditory measures in the judge battery.
- Fine-tuning a pretrained encoder (report 1d, tens of minutes).
- An ear page for finalists, and anything on L2 or N6's set.

Out of scope, by the report and the review: wider or deeper CNNs, from-scratch transformers, CRNN or TCN in place of pooling, flow,
diffusion or posterior heads, unsupervised alignment, per-clip band normalisation on tone and cab inputs, finer mels, CQT, scattering.

## Findings log

Newest last. Each entry: date, task, result, output path and sha256, audited by whom.

- 2026-11-05, T1.1: nothing yet to report; the ML session's terms are in the rules above.
- 2026-11-05, T1.3: `bakeoff control` passed: cached FTm, FT and W rows give N1's stored r and swap totals within 1e-6 on both
  sets (`PF/bakeoff/base.rows.pkl`, about 3 min on one CPU). `bakeoff check` on the mel ridge's plumbing (`PF/bakeoff/check.json`):
  labels shuffled within cell read GOAT −0.029, −0.012, −0.033 and BKS +0.114, −0.106, +0.063 on drive, tone, cab; labels joined
  to the input read +0.95 to +1.00 on both sets, so rows and labels line up. Neither reads a candidate. The harness is not yet
  independently reviewed.
- 2026-11-05, input from the ML session (N7, F58, audited, branch `mask-read`, not recomputed here): a linear probe on FS5, readable
  heads of 116: plain mix 30, true-map cells 35, stem maps 19 (matching random cells). Corrected by the ML session (PR #393): the limit at this margin is band coverage, not dominance. Clean target, post hoc: all cells 91,
  cells under the backing 87, random cells at the true map's density 71, another example's true map 43, the true map's per-band layout
  with random frames 42, its own cells 38. The stem's 3 dB map is no better than random cells. No other margin or floor was tried. It does
  not test a trained model's use of a map. For T2.1: any map must be per-band, so coverage holds.
- 2026-11-05, T1.2: the report's citations checked by a subagent on 12 sources (some through page summaries, not full text). Figures
  mostly hold. Readings corrected and sent to the researcher: DX7's 17.1 to 12.2 is one-hot extended to discrete numeric controls, not
  one-hot against regression, and Num-only is 16.1, so the case for `A-cat` is weaker than the report says; Comunità's 0.040 is an average
  over 8 configurations (0.017–0.064); Bruford's 3x is an MSE ratio at the only size trained; the 61.5 and 73.8 are softened centring. The
  report's direction stands. It is a judgement, and the plan's reads test it.
