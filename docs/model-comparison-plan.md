# Model comparison plan

**Status: reviewed; the harness fixes are being checked. No candidate has been read, and nothing has rendered or trained.**

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
- **Now:** T2.3 and T4.3. The reviewer is checking the fixes; `check` is running on CPU; `A-ctl` is training, as it changes nothing.
- **Next:** on the reviewer's OK, `bakeoff read` (T3.2), and the review of `learn/bakeoff_train.py` before `A-cat`.
- **Running jobs and PIDs:** `bakeoff check` PID 95505; training chain PID 97624, script `PF/bakeoff/chain.zsh`, log `PF/bakeoff/logs/chain-ctl.log`. To stop the chain after the
  process in hand: `touch PF/bakeoff/STOP`. Finished runs are skipped on a relaunch.
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
- [ ] T2.3 Ledger entry `model-comparison` listing the candidates; PR with this plan; merge after review and CI.

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

- [~] T3.1 Inputs and readers in `learn/bakeoff.py`, with unit tests. Rerun `control` and `check` on the final code; `check` runs every
  candidate under shuffled labels, and the spike on `M-ridge`, `W-ridge` and `P-ridge`.
- [ ] T3.2 `bakeoff read`, output `PF/bakeoff/read-a.json` and its `.rows.pkl`. Each candidate's answers are cached per fold in
  `PF/bakeoff/answers/`, so a rerun resumes there; the report step reruns whole.
- [ ] T3.3 Independent audit of T3.2 by recomputation, before any result is built on.
- [x] T3.4 `learn/bakeoff_judge.py`, the judge battery, CPU, nothing installed. Terms: J0 `distance`, `tonal`, and a cross-fitted per-band
  term: the band's mean dB error on odd 1 s blocks times that on even blocks, averaged over scored bands, signed square root. Data:
  `learn/trusted-data/judge-ear/` and `judge-v5/`. Control: the recomputed `distance` matches stored values within 1e-6. Checks: (a) Spearman
  and gamma with the ear on each page; (b) the flip, reverb and delay against the +6 dB shelf on the clean amp on both DIs, 4 orders, J0 right on
  2; (c) treble steps not filling the top three; (d) heard drive steps above unheard; (e) the sensitivity table's known-error protocol (the
  review's `bench.py`, moved to this file), effect in split-half SDs against d.
- [ ] T3.5 Audit T3.4. Log both results. Choose what moves on by the rules below.

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
- [~] T4.3 Run the arms in order, in resumable pieces, one record each with command, seed, git sha, PID, minutes. The executor watches from launch.
- [ ] T4.4 Each arm's answers fill `_ans` and `_swap` directly (`read_fold` cannot load these nets), read through `reads_v3`, paired against FTm. `bakeoff arms` runs once over all arms, so the bound holds. Audit. Log.

**Declared rule for Phase 4.** An arm moves on if `arm − FTm` clears zero on GOAT by the max-t bound over all arms' groups, beats `A-ctl − FTm`'s size in that
group, no group's plain interval sits wholly below zero, and its switch or mic own-against-swap less FTm's has no interval wholly above zero on GOAT. Knob swap is not compared: an arm's knob output can have another form. An interval holding zero is undecided: `A-cnn` undecided means network size is not shown to
matter, not that it doesn't. An arm that moves on gets the full nested recipe (8 inner runs, 70 min) before Phase 5.

### Phase 5, by the score (renders, 3 slots shared with the ML session)

- [ ] T5.1 `learn/bakeoff_render.py`: answers in `goat/answers` and `real/answers`' shape, on read 2's units, each direction read from its search half. `M-ridge`
  and any ridge copy stored `RcBG`'s settings for the direction, overwrite only searched knobs, and fit residuals around RcBG's own values, so `ridge − centre`
  reads only the knob gain; `cell_centres` is not RcBG's centre (mean gap 0.022 on GOAT). Judged by `analysis.aligned` on the held half, storing `distance`, `tonal`
  and the cross-fitted term. No audio kept. Check: 10 of FTm's stored answers rendered through it match the stored judge values and `render_sha256`.
- [ ] T5.2 Renders: `M-ridge`, then at most two finalists, ranked by their simultaneous lower bound. 1,340 each by the code (335 keys × 2 × 2). Stored judges hold `distance`
  only, so `tonal` beside needs FTm, RcBG and S rendered again: about 2,700 more. FTm's own batch spanned 19 min for 1,340 by its files' times. Shards resumable; announce size and PIDs;
  stop when the ML session asks.
- [ ] T5.3 Report `candidate − centre`, `candidate − FTm`, `candidate − S`, by item on GOAT and by DI on BKS, by fold beside, with t intervals, `tonal` beside `distance`, and
  d_S strata. Audit. Log.

**Declared rule for Phase 5.** Nothing is adopted here. BKS and GOAT are development sets, chosen on many times. A finalist closer than FTm on GOAT by item, by the score, is a lead,
stated with the search labels' limits and the count of candidates tried. Which model goes to L2, or to an ear page, is for the ML session and the user.

### Phase 6, write-up

- [ ] T6.1 `docs/model-comparison-results.md`: answers on network, features and judge, with every candidate's row and what was not tested.
- [ ] T6.2 Small dated lines in ROADMAP and DOCS-INDEX. Correct the deep review's "about 670 renders" to 1,340.
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
