# Model comparison plan

**Status: done; the results are in [model-comparison-results.md](model-comparison-results.md). The task list and log below are the record of how it ran.**

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

- **Session:** "ML models and scoring review", branch `claude/model-comparison`.
- **Worktree:** `/Users/yoavbz/projects/neuraldsp-preset-generator/.claude/worktrees/ml-models-scoring-review-8db392`. Work only there.
- **Run from the worktree root:** `TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python`; `$TORCH_PY -m learn.bakeoff ...`. Tests:
  `/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python -m pytest tests/test_bakeoff.py tests/test_bakeoff_inputs.py -q -n0`.
- **Peers:** SendMessage to "NeuralDSP preset generator (ML)", "(executor)", "(controller)", "(cloud researcher)". The researcher's PR is #394.
- **Now:** T6.3, the results PR, #398.
- **Next:** T6.4, the report to the user and the controller.
- **Running jobs and PIDs:** none. Total renders 6,700; training 139 min.
- **Render or MPS use announced to the ML session:** none. Holds lifted so far: the ML session's renders finished at about 23:20 on 2026-11-05 and the 3 slots are free;
  it plans none tonight and will say first if an audit asks. A new hold, or its end, is recorded on this line.
- **Disk:** about 36–39 GB free, floor 33 GB: stop new builds under it and tell the executor.
- **Blocked on the user:** nothing. The user went to sleep at about 22:40 on 2026-11-05 (controller): carry on as far as the rules allow, and when finished send the
  controller two or three plain lines on what was found, checked and left open.

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
- Allowed by the ML session (2026-11-05): W's plugin rows through `recipe_inputs`, `plugin_rows` and `rung_rows`, W's stored `train_ids` only, which also load `cc/rows`. No NS row may enter a fit, a
  choice or a printout; if anything would need one, stop and ask. `learn/trusted-data/judge-ear/` and `judge-v5/`, CPU only.
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
- [x] T1.2 The cloud researcher's report on network types, features and judging, PR #394, read and its key citations checked (findings log).

- [x] T1.3 Harness `learn/bakeoff.py`, with `tests/test_bakeoff.py`: candidates go through `reads_v3.report` unchanged.
  Done when `control` reproduces N1's stored r and swap totals within 1e-6 on BKS and GOAT, and a shuffled-label placebo
  reads near zero. Reads no candidate.

### Phase 2, plan
- [x] T2.1 Candidates, features and judge measures set from the report (PR #394), each read's rule declared here.
- [x] T2.2 Independent review of this plan, by a reviewer who saw the code. It found 16 issues; all are fixed below or in
  `learn/bakeoff.py`, and the ML session answered the three that were its call.
- [x] T2.3 Ledger entry `model-comparison` listing the candidates; PR with this plan; merge after review and CI.

### Phase 3, reads without renders or training (CPU, `learn/bakeoff.py`, `learn/bakeoff_inputs.py`)

All on BKS and GOAT through `reads_v3`, on real rows held by fold. Family: the 16 candidates below, with FTm, FT, W and W's final state
beside. Everything is reported, dropped arms included.

| Label | Input | Reader | Trained on | Asks |
|---|---|---|---|---|
| `M-ridge` | `mel`: band means, stds, LUFS | ridge on 24 PCs | real rows | The reference, and the review's small model |
| `M-rrr` | `mel` | reduced rank 4, per amp | real rows | Does the labels' low dimension help? |
| `M-knn` | `mel` | k nearest | real rows | Retrieval by mel statistics |
| `M-trees` | `mel` | boosted trees | real rows | Named in the user's yes; the report expects overfitting |
| `W-ridge` | W's last hidden layer | ridge | real rows | Are W's features better than its heads? |
| `ltas` | band means, 80 Hz–5 kHz, floor −45 dB, LUFS | ridge | real rows | Tone and cab, report B2 |
| `ceps-lo` | DCT orders 1–20 of band means, LUFS | ridge | real rows | Tone and cab, report B4 |
| `onset` | band means and stds on attacks and sustains apart, LUFS | ridge | real rows | Drive, report B1 |
| `flat` | spectral flatness mean and std, in all and in 8 coarse bands, LUFS | ridge | real rows | Drive, report B1 |
| `hpss` | means and stds of the percussive residue, LUFS | ridge | real rows | Drive, report B1 |
| `ceps-hi` | DCT orders 21–60 per frame, mean and std, LUFS | ridge | real rows | Drive, report B4 |
| `P-ridge` | `mel` | ridge on 24 PCs | plugin rows only | Is the CNN needed for what W reads with no real rows? |
| `P-onset`, `P-flat`, `P-hpss`, `P-ceps-hi` | as above | ridge | plugin rows only | Drive, with far more rows than crunch's real ones |

Fixed choices: attacks are the 60 ms after peaks in positive spectral flux, sustains the other frames; ridge's alpha and k come from
inner folds on whole clusters; the 24 PCs are fitted inside each training fold, after centring within cell; LUFS scaled as `cond_vec`
scales it. Real rows use all 25 backing variants, plugin rows W's stored `train_ids` with their own input and first 4 backings. Inputs
come from the stored mels, so nothing here needs audio. An FTm-features arm was dropped: its training rows would be in-sample.

- [x] T3.1 Inputs and readers in `learn/bakeoff.py`, with unit tests. Rerun `control` and `check` on the final code; `check` runs every
  candidate under shuffled labels, and the spike on `M-ridge`, `W-ridge` and `P-ridge`.
- [x] T3.2 `bakeoff read`, output `PF/bakeoff/read-a.json` and its `.rows.pkl`. Each candidate's answers are cached per fold in
  `PF/bakeoff/answers/`, so a rerun resumes there; the report step reruns whole.
- [x] T3.3 Independent audit of T3.2 by recomputation, before any result is built on.
- [x] T3.4 `learn/bakeoff_judge.py`, the judge battery, CPU, nothing installed. Terms: J0 `distance`, `tonal`, and a cross-fitted per-band
  term: the band's mean dB error on odd 1 s blocks times that on even blocks, averaged over scored bands, signed square root. Data:
  `learn/trusted-data/judge-ear/` and `judge-v5/`. Control: the recomputed `distance` matches stored values within 1e-6. Checks: (a) Spearman
  and gamma with the ear on each page; (b) the flip, reverb and delay against the +6 dB shelf on the clean amp on both DIs, 4 orders, J0 right on
  2; (c) treble steps not filling the top three; (d) heard drive steps above unheard; (e) the sensitivity table's known-error protocol (the
  review's `bench.py`, moved to this file), effect in split-half SDs against d.
- [x] T3.5 Audit T3.4. Log both results. Choose what moves on by the rules below.

**Declared rules for Phase 3.** Effect sizes first. Selection is on a simultaneous 95% lower bound over all 30 contrasts in `bakeoff.BOUND`
(max-t on one set of GOAT item weights), with the plain 90% interval beside. A plain clear that the bound does not hold is a lead, not a move.
- A reader or `W-ridge` moves on if the bound of `candidate − FTm` clears zero on GOAT in a group and no group's plain interval sits wholly
  below zero.
- `ltas` or `ceps-lo` moves on if the bound of `input − M-ridge` clears zero on GOAT on tone or cab.
- Drive on crunch: 104 rows and 81 items, so this read is unlikely to decide; it is head-standardised, since inputGain carries 56% of its label
  variance. Only the bound moves an input on. `A-in` may take the input with the highest point estimate, stated as a lead.
- `P-ridge` is read against W. An interval holding zero is undecided, never "level".
- `M-ridge` goes to Phase 5 regardless: the ML session handed over the review's step 2.
- BKS never selects, and can flag a candidate in its own row. An interval reaching zero is undecided, not failed.
- GOAT is about 76% one player: each label's r on that player and on the rest is reported.
- A judge term passes if the flip gets at least 3 of 4 orders, the effect falls less than 5× from d 2.73 to 6.05, and it does not lose
  Spearman or gamma to J0 on either page. These pages are in-sample, one listener, 48 items, read many times, so a pass is a screen. It leads
  only to a proposal for a fresh blind page. `tonal` and the cross-fitted term sit beside `distance` in Phase 5 either way. No weight is fitted.

### Phase 4, training arms (MPS, one GPU job at a time, `learn/bakeoff_train.py`)

**Approval.** The user's message of 2026-11-05 told this session to write this plan and then start working, without seeing it first. The reading
used here: the runs declared below are planned runs, the standing rule's "runs already in an approved plan". The ML session and the
controller do not grant that; the user's words do, and the user can stop it. Nothing beyond the runs declared here starts without the user's
yes. The final report states this.

Each arm uses W's data and FTm's recipe (`P.fit`, `P.WideData`, `P.DfixData`, the searched-head mask, lr 1e-4). W's stored body was chosen on
NS loss, which every arm built on it inherits; no arm tracks NS. As a screen, each FT_k takes FTm's stored E(k, s), chosen without fold k, so no inner
runs. That E was tuned on FTm's loss and body, so it is unfair to the new heads: only a clear gain counts, and a null says little. Measured: W 10.0 min;
the eight FTm_k sum to 54.0 min. The ML session gets each arm's size and PIDs before launch. Outputs stay in `PF/bakeoff/runs/`, under 1 GB.

| Order | Arm | What changes | Start | Size |
|---|---|---|---|---|
| 1 | `A-ctl` | Nothing: FTm's recipe on other training seeds, so its distance from FTm shows the seed noise the bootstrap cannot see. W's seed noise stays unseen | W's stored state | 54 min |
| 2 | `A-cat` | Knob heads, loss and readout: 21 bins on 0–1, each label split between its two nearest bins, cross-entropy, interpolated median. The mixture's family weight changes with it | W's body frozen, new heads fitted on plugin rows for 30 epochs at 1e-3 (about 840 steps; frozen features and a linear head need far fewer steps than W's 1,680, and the loss is logged to show it flattened), then FTm's recipe | 54 min plus about 5 min |
| 3 | `A-cnn` | The body: 2 conv layers of 6 and 12, dense 120 and 60, same heads | Fresh, W's fixed 60 epochs, `final` state, then FTm's recipe; `P2b-wide24:final` read beside | 74 min |
| 4 | `A-k1` | Mixture K and sd floor: K = 1, floor 0.07 | As `A-cat` | 54 min plus about 5 min |
| 5 | `A-mic` | The mic loss weight, 0.1 | W's stored state | 54 min |
| 6 | `A-in` | The best input from Phase 3 as a second branch, if any moves on or leads | Fresh, as `A-cnn` | 74 min |

- [x] T4.1 Read `P.cmd_train`, `P.cmd_train_ft` and `P.fit`; write `learn/bakeoff_train.py`, a new file, nothing in `pipeline_fix` changed. Any recipe
  takes extra rows later, with the mask and a drop key on `di`.
- [x] T4.2 Control: one fold and seed of `A-ctl` on FTm's own seed; its last logged real loss within 5% of FTm's. About 6 min.
- [x] T4.3 Run the arms in order, in resumable pieces, one record each with command, seed, git sha, PID, minutes. The executor watches from launch.
- [x] T4.4 Each arm's answers fill `_ans` and `_swap` directly (`read_fold` cannot load these nets), read through `reads_v3`, paired against FTm. `bakeoff arms` runs once over all arms, so the bound holds. Audit. Log.

**Declared rule for Phase 4.** An arm moves on if `arm − FTm` clears zero on GOAT by the max-t bound over all arms' groups, beats `A-ctl − FTm`'s size in that
group, no group's plain interval sits wholly below zero, and its switch or mic own-against-swap less FTm's has no interval wholly above zero on GOAT. Knob swap is not compared: an arm's knob output can have another form. An interval holding zero is undecided: `A-cnn` undecided means network size is not shown to
matter, not that it doesn't. An arm that moves on gets the full nested recipe (8 inner runs, 70 min) before Phase 5.

### Phase 5, by the score (renders, 3 slots shared with the ML session)

- [x] T5.1 `learn/bakeoff_render.py`: answers in `goat/answers` and `real/answers`' shape, on read 2's units, each direction read from its search half. `M-ridge`
  and any ridge copy stored `RcBG`'s settings for the direction, overwrite only searched knobs, and fit residuals around RcBG's own values, so `ridge − centre`
  reads only the knob gain; `cell_centres` is not RcBG's centre (mean gap 0.022 on GOAT). Judged by `analysis.aligned` on the held half, storing `distance`, `tonal`
  and the cross-fitted term. No audio kept. Check: 10 of FTm's stored answers rendered through it match the stored judge values and `render_sha256`.
- [x] T5.2 Renders: `M-ridge`, then at most two finalists, ranked by their simultaneous lower bound. 1,340 each by the code (335 keys × 2 × 2). Stored judges hold `distance`
  only, so `tonal` beside needs FTm, RcBG and S rendered again: about 2,700 more. FTm's own batch spanned 19 min for 1,340 by its files' times. Shards resumable; announce size and PIDs;
  stop when the ML session asks.
- [x] T5.3 Report `candidate − centre`, `candidate − FTm`, `candidate − S`, by item on GOAT and by DI on BKS, by fold beside, with t intervals, `tonal` beside `distance`, and
  d_S strata. Audit. Log.

**Declared rule for Phase 5.** Nothing is adopted here. BKS and GOAT are development sets, chosen on many times. A finalist closer than FTm on GOAT by item, by the score, is a lead,
stated with the search labels' limits and the count of candidates tried. Which model goes to L2, or to an ear page, is for the ML session and the user.

**Amendment, 2026-11-06, after the arms' read, before any `A-mic` render.** `A-mic` does not move on by the declared rule: its bound sits just below zero and its mic own-against-swap is worse. Yet all three of its groups clear zero on plain intervals, on both signs of evidence the
read can give, and its only cost is the mics, which the score can weigh and the knob read cannot. So one post hoc read: `A-mic` by the score, FTm's readout on its nets (controls outside `K.space` at S), 1,340 renders. It is a lead, never a move: it adopts nothing, it is counted as the 22nd candidate tried, and it stays outside the rule above.
The renders fall under the user's "render whatever needed". Control: the same predict code on FTm's own nets must reproduce the stored `P2b-ftm` answers exactly.

- [x] T5.4 The amendment's read: `predict-arm`, its control, the renders, the report. Audit with T5.3.

### Phase 6, write-up

- [x] T6.1 `docs/model-comparison-results.md`: answers on network, features and judge, with every candidate's row and what was not tested.
- [x] T6.2 Small dated lines in ROADMAP and DOCS-INDEX. Correct the deep review's "about 670 renders" to 1,340.
- [ ] T6.3 PR, independent review, CI, merge. Update memory `model-comparison-state`.
- [ ] T6.4 Plain report to the user, and two or three lines to the controller.

### Waiting for the user's yes

Not run tonight: each needs a download, or more than this plan declares.
- Downloads: EfficientAT mn10 weights, AFx-Rep weights, HAAQI or GstPEAQ, kadtk. None is on disk. These would add report steps 0d, 0e and 0f: frozen encoders on rebuilt audio, and
  auditory measures in the judge battery.
- Fine-tuning a pretrained encoder (report 1d, tens of minutes).
- An ear page for finalists, a fresh blind page for any judge term, and anything on L2 or N6's set.

Out of scope, by the report and the review: wider or deeper CNNs, from-scratch transformers, CRNN or TCN in place of pooling, flow, diffusion or posterior heads, unsupervised alignment,
per-clip band normalisation on tone and cab inputs, finer mels, CQT, scattering.

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
- 2026-11-05, T2.2: an independent review of this plan and harness found that `bakeoff read` did not compute the declared contrasts, that its family correction tested the wrong thing,
  that FTm features would leak unseen, that LUFS was unscaled (46% of `mel`'s variance), that "level" conclusions broke the plan's own rule, and that Phases 4 and 5 misstated sizes and
  centres. Centring, PCA, inner folds, the caches, `trunk_of` and the use of `read_fold` were clean. All are fixed here or in the code; the first `check` ran on the old code and is superseded.
- 2026-11-05, T4.2: `A-ctl` on fold 0 with FTm's own seed, through `learn/bakeoff_train.py`: last training loss 2.8125 against FTm's stored 2.8125, in 4 min on MPS. The loop reproduces the recipe.
- 2026-11-05, T3.4, not yet audited (`PF/bakeoff/judge.json`): the copy of J0's path matches every stored value with a worst gap of 0.0. No term passes the declared rule: flip 2 of 4 for `distance`, `tonal` and the
  cross-fitted term alike. Spearman with the ear, judge-ear then judge-v5: `distance` +0.48, +0.74; `tonal` +0.53, +0.70; cross +0.40, +0.58. `tonal` and cross fill the top three with tone steps on judge-ear,
  `distance` does not. For a 6 dB bell from d 2.73 to 6.05 the fall is 3.2× for `distance`, 2.6× for `tonal`, 1.6× for cross, so the sensitivity mechanism is real but it does not track this ear better. In-sample, one listener.
- 2026-11-06, T3.1: `control` passed on the final base rows. `check` (`PF/bakeoff/check.json`): with labels shuffled within cell all 16 candidates read within ±0.13 on GOAT, expected for about 0.07 of noise over 48 values, and wider
  on BKS's few recordings (−0.35 to +0.27); with labels joined to the input `M-ridge` and `W-ridge` read +0.95 to +1.00 and `P-ridge`, trained on plugin labels only, +0.48 to +0.86. The second review confirmed the harness and the training code after its
  fixes; `plugin_set` and `ids is sp["train"]` rest on reading the code, and `check` has now run the first of them.
- 2026-11-06, T5.1: 16 renders of FTm's stored answers on 2 units through `learn/bakeoff_render.py` matched every stored judge and render hash. `M-ridge`'s answers are built on RcBG's settings, 9 knobs moved on the first key. The review's "about 670" for this read is corrected in the plan: 1,340 renders each.
- 2026-11-06, T3.2, not yet audited (`PF/bakeoff/read-a.json`, GOAT r on drive, tone, cab): FTm +0.082, +0.258, +0.218. `W-ridge`, a ridge on W's frozen last layer fitted on real rows, +0.234, +0.251, +0.283: `W-ridge − FTm` drive +0.153
  [+0.063, +0.235], simultaneous bound +0.003, the only contrast of 30 to clear it; cab +0.065 [+0.007, +0.119], bound −0.032; tone −0.008 [−0.089, +0.079]. `M-ridge` +0.212, +0.201, +0.147. `P-ridge`, plugin rows only, +0.140, +0.207, −0.038, against W's +0.096,
  +0.222, −0.086: undecided on all three. No tone input beats `M-ridge`. No drive input beats it on crunch: the best is `hpss` +0.020 [−0.062, +0.113], which is not worth `A-in`'s 74 min. Head-standardised drive is about level (FTm +0.14, `W-ridge` +0.13), so the raw gain needs explaining before anything is built on it.
- 2026-11-06, T5.2, not yet audited (`PF/bakeoff/score-a.json`, 4,020 renders; every stored FTm, RcBG and S record came back with the same hash and judge, GOAT's S held on 215 keys; FTm − S reproduces F55's −0.094 and −0.123): by the score, minus is closer,
  GOAT by item, BKS by DI. `M-ridge − RcBG` −0.020 [−0.028, −0.012] and −0.021 [−0.041, −0.001], closer than the centre on both sets. `M-ridge − FTm` +0.001 [−0.016, +0.019] and −0.039 [−0.084, +0.005], undecided on both. `FTm − RcBG` −0.021 [−0.040, −0.002] and +0.018 [−0.027, +0.064].
  `tonal` reads the same way: `M-ridge − RcBG` −0.036 and −0.024. Development sets, chosen on many times; none of this is sound.
- 2026-11-06, T3.3, audit of T3.2 by a subagent with its own code: `W-ridge` and `M-ridge` reproduced to 2.5e-7 on all 4 folds with the same inner folds (.225, .244, .291 and .223, .216, .149 with its own folds and alphas); the bound and BKS's pairs reproduced exactly; no held DI, item or unit reaches a fit. `P-ridge` was not refitted. `W-ridge` moves on by the letter,
  marginally: over 20 inner-fold salts the bound's mean is −.003 (range −.035 to +.018, 10 of 20 above zero); the plain interval clears zero in all 20. What the drive gain is: FTm puts 68% of its answer variance on ac20Power, which holds 8% of label variance, and 3.4% on inputGain, which holds 59%; `W-ridge` puts 2% and 60%. Paired head-standardised it is undecided (−.011 [−.090, +.067]); with both answers' spreads set
  proportional to the labels', +.100 [+.005, +.194]. So about a third is FTm's misplaced spread and two thirds reading. On same-DI, two-chain pairs inputGain reads `W-ridge` +.326 [+.163, +.475], FTm +.144, `M-ridge` +.133. Without limit labels the gain is +.062 [−.044, +.157]. It rests on pr12's inputGain, and BKS does not repeat it (−.020 [−.402, +.362]). `W-ridge − M-ridge`: drive +.022 [−.051, +.095], cab +.136 [+.080, +.191], so W's
  body adds on cab, not drive. Artefact attempts failed: distinct files, no shared DI, LUFS, player, backing and seed noise (A-ctl +.006) do not explain it. Do not write "reads drive better". Scripts: scratchpad `mcmp/audit/`, not kept.
- 2026-11-06, T4.3 and T4.4, not yet audited (`PF/bakeoff/read-arms.json`), GOAT, arm − FTm on drive, tone, cab, 90%: `A-ctl` +0.006, −0.014, −0.000, the seed noise. `A-cat` +0.025 [−0.023, +0.075], −0.092 [−0.169, −0.012], −0.062 [−0.103, −0.018]. `A-cnn` −0.039 [−0.098, +0.016], −0.138 [−0.212, −0.053], −0.114 [−0.184, −0.047], mic swap +0.099 [+0.042, +0.157] worse. `A-k1` +0.026 [−0.003, +0.052], +0.020 [−0.024, +0.062], +0.009
  [−0.012, +0.032]. `A-mic` +0.037 [+0.013, +0.063], +0.065 [+0.012, +0.119], +0.043 [+0.014, +0.068], bounds −0.005, −0.022, −0.001; mic swap +0.057 [+0.029, +0.085] worse, switch −0.015 better. No arm moves on by the declared rule. Measured: `A-cat` 33 min, `A-cnn` 13 min, `A-k1` 31 min, `A-mic` 30 min, `A-ctl` 32 min. W's stored body, chosen on NS loss, underlies `A-ctl`, `A-cat`, `A-k1` and `A-mic`; `P2b-wide24:final` reads +0.075, +0.148, −0.076 against `best`'s +0.096, +0.222, −0.086, so `A-cnn`'s `final` start costs it something on tone.
- 2026-11-06, T5.2, not yet audited (`PF/bakeoff/score-b.json`), by the score, GOAT by item, BKS by DI: `W-ridge − RcBG` −0.023 [−0.032, −0.015] and −0.007 [−0.035, +0.021]; `W-ridge − FTm` −0.002 [−0.018, +0.013] and −0.025 [−0.074, +0.024], undecided on both.
- 2026-11-06, T5.4, not yet audited (`PF/bakeoff/score-c.json`, 1,340 renders; the predict code on FTm's nets reproduced its stored answers exactly), by the score, GOAT by item, BKS by DI: `A-mic − FTm` −0.006 [−0.013, +0.002] and +0.004 [−0.008, +0.017]; `A-mic − RcBG` −0.027 [−0.045, −0.008] and +0.023 [−0.030, +0.075]. Its knob gain does not show by the score.
- 2026-11-06, audit of T3.5, T4.4, T5.3 and T5.4 by a subagent with its own code: every stored figure reproduced (score contrasts within 2.4e-5, arms exactly, folds 0 and 3 regenerated within 9e-6). Readings it corrected are in the results doc: `A-mic` by the score is undecided below resolution, not "no gain"; no contrast with the centre clears on BKS by fold; FTm and `A-mic` mix a per-cell shift, mics and switches with knobs; `A-cat` and `A-cnn` lost in these runs only; the judge's 48 items are the main pages, and any fixed order scores 2 of 4 on the flip.
