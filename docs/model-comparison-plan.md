# Model comparison plan

**Status: draft, waiting on the research report (T1.2). Nothing has run.**

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
- **Now:** T1.2, waiting for the cloud researcher's PR, which adds `docs/research/model-features-judge-fit-2026-11.md`.
- **Next:** T2.1, set the candidate list from that report.
- **Running jobs and PIDs:** none.
- **Render or MPS use announced to the ML session:** none.
- **Blocked on the user:** nothing yet.

## Rules for this work

Set by the ML session on 2026-11-05 unless marked. They hold for the whole plan.

**The Mac**
- At most 3 render processes on the whole Mac, the ML session's and ours together. `_wait_cap` does not count `night2` or
  `capture_labels`, so check `pgrep` before each launch.
- Renders run as resumable shards. When the ML session says its centre read is about to start, finish the process in hand,
  start no other, and resume when it says.
- Before each render batch or MPS run, tell the ML session its size and PIDs.
- MPS is ours while the ML session is not training: at most 2 runs at a time, un-niced (`setopt no_bg_nice`), loss on CPU
  (the stft gradient bug).
- Disk guard 31 GB, 39 GB free at the start: keep outputs small, store no audio or feature dumps.
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
- [~] T1.2 The cloud researcher's report on network types, features and judging (brief sent 2026-11-05). Done when its PR is
  read and its key claims checked against sources.

### Phase 2, plan
- [ ] T2.1 Set candidates, features and judge measures from the report and write each read's declared rule here.
- [ ] T2.2 Independent review of this plan; fix what it finds.
- [ ] T2.3 Ledger entry `model-comparison` and memory pointer; PR with this plan; merge after review and CI.

### Later phases
Written in T2.1, once the report sets the order. Known so far:
- A no-render comparison on the audited read: ridge, boosted trees, nearest neighbours, and W's frozen network with a ridge on
  top, beside FTm.
- Ridge by the score (the review's step 2, about 670 renders, handed over by the ML session), with its input stated and
  `tonal` beside `distance`.
- Candidate networks and features chosen by the report.
- Judge measures on the stored ear pages.

## Findings log

Newest last. Each entry: date, task, result, output path and sha256, audited by whom.

- 2026-11-05, T1.1: nothing yet to report; the ML session's terms are in the rules above.
