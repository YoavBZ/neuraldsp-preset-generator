# The note-reading diagnosis on the exact bench (ledger `phase_scratch_readerr`)

Declared 2026-11-25, before anything in it runs. The user approved this track on 2026-11-25. The plan (the
handover's `plans/note-reading-diagnosis-plan.md`, planner Fable) passed an independent review (Opus, high): PASS WITH
AMENDMENTS. Its nine binding amendments and the orchestrator's calls O1 to O8 are built in below. Where they differ
from the plan's text, they win. The orchestrator's calls are technical decisions, delegated under the user's
2026-11-23 rule.

- **Code:** `learn/scratch_readerr.py` (this unit) and `learn/readerr_run.py` (the transcriber runner, its own PR).
- **Tests:** `tests/test_scratch_readerr.py` and `tests/test_readerr_run.py`.
- **Data:** `PF/fs/readerr/`. Each file is written once.
- **Ledger:** `preset-ladder` `phase_scratch_readerr`, then `phase_scratch_readerr_frozen`,
  `phase_scratch_readerr_notes` and `phase_scratch_readerr_outcome`.
- **Grepped first:** `readerr`, `scratch_readerr`, `phase_scratch_readerr`, `xr-`, `RX-`, `anatomy` and
  `screen-check` had no hit in `docs/`, `learn/`, `tests/` or the ledger.

In this repo "reader" means the knob reader, so this text says "transcriber" or "note reading".

## 1. Goal

The exact-notes test (`scratch-search-plan.md` section 15, `XN-both`) priced reading proper at +0.552
[+0.421, +0.683] on the 40, by the score. Reading proper is G(`xn-reread`) − G(`xn-list`): the cost of Basic Pitch
re-reading the bank guitar, against rebuilding from the bank guitar's exact notes.

This track asks two questions at zero renders:

- What in that re-read costs the preset?
- Which open transcriber, setting or post-fix reads the bench best?

Then it hands the user one priced next step.

**Read this first:**

- **The bench prices fidelity only.** The bank guitar is the song as Basic Pitch heard it. Its exact list therefore
  holds Basic Pitch's own ghost-shaped notes as real notes, and its bends as fragments. Ghost vetoes, F6 and any
  transcriber with real-guitar priors are penalised here. The real-DI arm (section 4) is two-sided because of this.
- **No validated cheaper screen exists (O1).** The 50-evaluation prefix fails its own rule on stored data: two pairs
  flip their label (D_list and `fs-both` − build 1). `screen-check` still runs, but only as a beside line. No step
  prices anything by the screen.
- **Nothing open besides Basic Pitch and MuScriptor is both battle-tested and electric-guitar-capable.** YourMT3+
  is the one open candidate with published electric-guitar figures above Basic Pitch, and those figures come from a
  retrain.

## 2. Phases

| Phase | Does | Verified by |
|---|---|---|
| 0 | This declaration, the code, the tests, every table coded | Tests green; names grepped; guarded files byte-identical |
| 1 | `trace`, then `anatomy`, `real-compare`, `screen-check`, `freeze`; zero renders, no model run | Four proofs on 47 of 47; an independent recompute; the hash PR `phase_scratch_readerr_frozen` before Phase 2 |
| 2a | Basic Pitch's grid, the 1-s lead-in, the shift vote, F6 on the re-read | At the frozen settings, the grid runner's events equal the stored re-read on 47 of 47; the note listing hashed (`phase_scratch_readerr_notes`) before `score` |
| 2b | The downloaded transcribers (U4's manifest, O4 to O8) | Hashes match; three identical runs on 4 parts; timed on 3 parts first |
| 2 read | `score`, `read`, the RX code | An audit; the results PR (`phase_scratch_readerr_outcome`) |

**Phase 2's commands are declared, not built.** Three pieces come with their own amendment and review before any of
Phase 2 runs: the candidates' run flow, the shift vote's clustering rule, and the downloads' load path. Their pure
rules are coded and tested now: the grid pick, the edge extension, the cross-set read, the real-DI labeller and
`RX_TABLE`.

## 3. Phase 1 (zero renders, no model run)

### 3a. `trace` (first) and its four proofs

The exact list is recomputed with the same calls as `scratch_exact.cmd_build`: `timed_notes`, then `apply_fixes`
with build 2's fixes. `played_trace` then follows `note_rebuild.synthesise_redo`'s rules step for step, without the
audio. The rules are placing, variety, skip and end, with the true DI's tuning and mutes, as build 2's `tr-di` was
made.

Two truths are kept:

- **The nominal list:** what `xn-list` consumed. It explains reading proper.
- **The as-played list:** the notes that sound, each ending at the end of its fade, inside the window. It is what a
  perfect transcriber could hear.

The stored re-read (`exact/work/reread/`) goes through `timed_notes` and F1. Beside it are kept the re-read's notes
before the onset snap, and the notes the clean-up dropped (six at once, out of range).

The four proofs:

1. `match_notes(exact, re-read)` equals `build.json`'s stored `reread_f` counts.
2. The trace's counts (played, skipped, ends by kind, bent, swaps) equal build 2's stored `tr-di` report.
3. CODE_FILES equal origin/main's (section 6).
4. The module's rebuild of the stored re-read reproduces `dry/xn-reread`'s sha256.

`trace.json` is written either way. If a proof fails, the code is `RX-stop`: nothing is read, and the result goes to
the orchestrator. Every later command refuses unless the proofs hold.

### 3b. `anatomy`

Every exact note and every re-read note lands in exactly one class, on both truths. A test checks the partition. Only
existing constants are used: the 50-ms onset, `VETO_INTERVALS`, `CHORD_S`, `note_tx.end_match`, and
`BEND_MAX_SEMITONES` for the bend fragments.

**Extras** (an unpaired re-read note) take the first class that holds:

1. `extras_sorted`'s own three come first, so the bench is like for like with the stored real-DI figures:
   - **harmonic:** 12, 19 or 24 semitones above a truth note sounding at its onset (from 50 ms before that note's
     onset to its end);
   - **re-find:** that note's own pitch.
2. Then "other" is split, the first that holds:
   - **octave-sub:** a missed truth note 12 semitones away, onsets within 50 ms;
   - **semitone-sub:** the same, 1 semitone away;
   - **timing:** a missed truth note of its pitch, onsets 50 to 150 ms apart;
   - **bend-fragment:** 1 to 3 semitones from a bent truth note sounding then (its `bend_curve` read against the
     truth list);
   - **rest.**

**Misses** (a missed truth note) take the first class that holds:

- **never-sounded:** the trace skipped it. Nominal list only; counted apart.
- **substitution:** an unpaired re-read note 1 or 12 semitones away, onsets within 50 ms.
- **timing:** an unpaired re-read note of its pitch, onsets 50 to 150 ms apart.
- **merged:** a re-read note of its pitch began more than 50 ms before it and still sounds at its onset.
- **clean-up:** a dropped note of its pitch, onsets within 50 ms.
- **chord-member:** its onset group holds 2 or more notes, and another member pairs.
- **rest.**

**Matched notes:** the onset error before and after the snap, the offset error against each truth, and the ends
(`end_match`). Bends: `note_fixes.bend_error` and `bent_but_cleared`.

**Groups:** missed attacks (a truth group with no re-read onset within 50 ms of its first onset) and extra attacks
(the reverse). Recall and precision by group size 1, 2 and 3+.

**Bench bias:** the ghost-shaped share of the exact list (notes 12, 19 or 24 above another note of their own onset
group), and recall on those notes against the rest.

### 3c. The declared figure family

The family holds 29 figures per part, on the as-played list, each with its orientation. An "error" figure is worse
when higher. A "similarity" is worse when lower.

| Figures | Orientation |
|---|---|
| note error 1 − F (the default primary); miss rate; extra rate; end error | error |
| attack miss rate; extra attack rate | error |
| frame error (11.6-ms frames, (frame, pitch) cells); octave-folded note error; uncovered and false sounding time | error |
| each extra class (7) and each miss class (6), per exact note | error |
| `build.json`'s stored dry-domain figures, `xn-reread` and `xn-list` against the bank guitar: `logmel`; pause excess (the pause share less the bank guitar's, the mean over J0's frame sizes) | error |
| the same two guitars' `env_corr` | similarity |

The nominal list's note error is reported beside; it is not in the family. With 29 figures on about 40 parts, about
one false "worse" is expected by chance. Every figure is reported, and the forward test is the first priced row.

### 3d. `real-compare`

The same anatomy runs, with no model run, on two sets:

- **The 79 stored Guitar-TECHS windows:** the truth report's note files, loaded by their recorded sha256, against
  the hashed truth listing.
- **The ten lists:** the install gate's stored events against the known notes.

Beside each window, two stored results must reproduce: the truth report's own counts, and track 1's stored `tx-bp`
extras. The stored real-DI headline to set the bench beside is 945 extras: 38% harmonic, 16% re-finds, 47% other.

**P3 has a mechanism (amendment 6).** Every real-DI input goes through `real_di_source`. That calls
`note_tx.declared_input`, which runs `note_truth.refuse_path` on the window's files. Only consistent P1 and P2 truth
windows and the ten lists pass. A P3 window or path refuses, and so does a GOAT item, a part or any path. A test
covers each case.

### 3e. `screen-check` (a beside line, O1)

The 12 stored pairs (`SCREEN_PAIRS`) are each read as new less old:

- **The exact world:** D_swap, D*, D_list, reading proper, `xn-swap` − `xn-reread`, `xn-swap` − `xn-list`.
- **The real world:** `fs-both`, build 1's `fs-notes` and build 2's `fs-notes` against row (b), and each against the
  rows before it.

For each pair, the checkpoint-50 paired difference sits beside the answer's. Both are read on the 40,
intent-to-treat (refusals at Cen), with intervals and `paired_reading` labels. The per-part Spearman and the sign
agreement come from the passing parts. Sign agreement is sign equality: D_list's is 0.67 on the 39 parts (amendment 9).

The line reads "holds" only when every pair keeps its label. The review found it reads "no screen". It is never a
pricing path.

### 3f. `freeze` (last) and the tracking read

**Reading proper per part** comes from `scratch_exact.row_numbers`. The passing-only read is the primary (39 parts;
amendment 3). Under intent-to-treat, the one refused `xn-list` part contributes +1.442, a refusal rather than reading.
Intent-to-treat is reported beside, and any disagreement is stated.

**Each figure** is read on the 40, with all 47 beside:

1. `scratch_notes.by_figure` gives Spearman and the median split.
2. The worse half is the upper half for an error, the lower half for a similarity.
3. Each half gets its interval from `set_rows`' BKS+GOAT pool.
4. `diff_interval(worse, better)` is labelled by `paired_reading` at its defaults, which is on J0's scale.

**A figure tracks** when three things hold:

- the label reads "worse";
- rho's sign agrees with the orientation;
- the split is not key-broken. `median_split` breaks ties by part key, so for sparse figures with many zeros it puts
  BKS low and GOAT high, a set confound. A figure whose split puts equal values on both sides is read by Spearman
  only and never frozen.

**The frozen figure** is the tracking figure with the largest |rho|; ties go by the family's order (`RX-tracks`). If
no figure tracks, note error stays, labelled "fidelity only" (`RX-untracked`).

The five files' sha256, counts, the code, the figure and the screen's line go into the ledger as
`phase_scratch_readerr_frozen` before any candidate is scored. `frozen_body` refuses anything else.

## 4. Phase 2's rules (declared now; the commands come later)

**Candidates:**

| Candidate | Kind | Download |
|---|---|---|
| Basic Pitch grid: onset 0.3 to 0.8, frame 0.2 to 0.5 (steps of 0.1), minimum length 58, 90 and 127.7 ms, Melodia on or off (144 points; one inference a part) | setting | none |
| 1-s zero lead-in | setting | none |
| Shift vote: 4 shifted reads, keep notes found in k = 2, 3 or 4 | setting | none |
| F6 (build 3's frozen rule) on the re-read; fidelity only, biased against, said beside | setting | none |
| YourMT3+ via `mt3-infer` (CPU) | transcriber | yes |
| Riley, Edwards and Dixon's `guitar-fl` and `guitar-gaps` | transcriber | yes |
| MuScriptor large | reference, never ships | none; only on the user's yes; recommended skip |

MR-MT3 is dropped (O5): the file `mt3-infer` loads is the original MT3 checkpoint, which is excluded on its scores.

**Transcribers without bends** borrow them through `note_tx.ms_with_bp`, scored both ways.

**The runner.** Every candidate runs only through `learn/readerr_run.py`, as
`PY -I learn/readerr_run.py MODE --spec JSON in.wav out.json [...]`. Its records are checked by `runner_refusal`:

- the contract's keys, mode, spec, model and input sha256;
- events on the input's own timeline;
- `bp-grid`'s points in the runner's order;
- `bp-shift`'s offsets with their whole-sample pads, and the top-level events.

When the runner clips an onset to 0, the note keeps its full bend track. `runner_notes` therefore trims that track
to the note's onset.

**The pick, no bars (amendment 4):**

- **The minimum:** the point with the frozen figure's best pooled BKS+GOAT mean.
- **The level set:** every point whose paired difference against the minimum spans zero.
- **The pick:** the point of the level set nearest the frozen defaults. Distance is L1 in grid steps, with Melodia
  one step. Ties go to the stored point, then the better mean.
- **An edge minimum** extends that axis by the axis's own step at that edge, bounded only by the parameter's own
  range. The stored 58 ms is the lower edge, so the stored point itself extends to 26 ms. Thresholds stay inside
  (0, 1), and the minimum length stays at one Basic Pitch frame (11.6 ms) or more.

**The labels.** The grid winner's in-sample label is worded "selected from 144". Its code comes from the cross-set
read: picked on BKS and read on GOAT, and the reverse. Both must agree; a sign disagreement means `RX-undecided`.
Leave-one-cluster-out is reported beside. The shift vote's k follows the same rule.

Every label at `small=0, big=0` is printed as "sign only, not on J0's scale, no size ruled out". At those settings
"matches" cannot occur, and "level" needs a zero-width interval.

**The real-DI arm is two-sided (amendment 5).**

- **The labeller:** `paired_reading(0, 0)` on `note_tx.set_summary`'s file-clustered interval. This is the named
  exception to `set_rows`. The figure is the frozen figure's field (note error to F, miss rate to recall, extra rate
  to precision, end error to end accuracy; otherwise note F, said beside). That field is higher-is-better against
  `tx-bp`, and the label is turned so it reads as the candidate's. Never `clear_above` or `decided_worse`.
- **The beside line "real-DI lead":** better on P1, P2 and the lists by the frozen figure, and not better on the
  bench.
- **Beside each candidate:** a read on the exact list with its ghost-shaped notes (and the re-read notes they pair
  with) left out. A gain that exists only on Basic Pitch-shaped notes then shows.
- P3 stays held out by the mechanism in 3d.

**Downloads (amendment 7, O4 to O8).** The download rules are in `DOWNLOAD_RULES`:

- Every checkpoint is pre-fetched to a pinned path with its sha256 in the manifest.
- Every run is offline.
- Before any load, a standard-library `pickletools` scan lists every global. Loads use
  `torch.load(weights_only=True)` with exactly the expected globals allowlisted. Any other global refuses; never
  `weights_only=False`.
- After each load, missing and unexpected keys are reported. A missing key the model needs refuses.
- Two Python 3.12 environments, each from its project's own `uv.lock`.

All remaining items are fine for development. YourMT3+, `guitar-fl`, `guitar-gaps` and soxr go to the user only if
one of them wins.

**Ties between kinds:** no download first, then a licence the product can use.

## 5. The outcome table (`RX_TABLE`, coded and tested before any run)

| Code | Phase | When (the first that holds) | Next step |
|---|---|---|---|
| `RX-stop` | 1 | A Phase 1 proof fails | Stop; to the orchestrator; nothing read |
| `RX-tracks` | 1 | A declared figure's worse half costs more, labelled "worse", rho agreeing, not key-broken | That figure is frozen; Phase 2 scores by it |
| `RX-untracked` | 1 | No figure tracks | Note error stays, "fidelity only"; Phase 2 still runs; recommend pricing a matched-notes-only hybrid as one `xr-` row before any transcriber |
| `RX-transcriber` | 2 | A downloaded open transcriber is decided better than the best Basic Pitch variant, not decided worse on Guitar-TECHS or the lists | To the user with the licence table and one priced `xr-` row |
| `RX-setting` | 2 | A no-download setting or post-fix is decided better, not decided worse on real DIs | To the user with one priced `xr-` row |
| `RX-harm` | 2 | Better on the bench, decided worse on Guitar-TECHS or the lists | Reported; not proposed for pricing |
| `RX-reference-only` | 2 | Only a non-product reference is decided better | Headroom shown; no open tool reaches it; to the user |
| `RX-undecided` | 2 | A product candidate better by the mean, none decided | To the user; undecided is not failed; option: price the top two as `xr-` rows |
| `RX-none` | 2 | Nothing better than the stored re-read | Basic Pitch as frozen stays; to the user with the re-derivation track's result beside |

**The best Basic Pitch variant** is the best setting decided better without harm. If no setting is decided better,
it is the stored re-read itself. A test checks that every combination of candidates' facts ends in exactly one code.

Two lines sit beside the code and never change it: the screen's line, and "real-DI lead".

## 6. Pricing a winner (described, not built here)

**The row.** The row is `xr-<id>`, coded in this module, because `scratch_exact.py` is guarded:

- Its guitar is `rebuild_redo` from the candidate's notes, with the bank guitar as the DI.
- It reuses `records.json`, `scratch_exact.start_reference`, `scratch_search.search_row_part` and `score_exact_part`
  unchanged.
- G(`xr`) − G(`xn-reread`) is the gain. G(`xr`) − G(`xn-list`) is what reading still costs.

**The cost** is about 13,040 renders and 1 h 53 min on 3 free processes. Both figures come from `xn-reread`'s
measured logs: search 12,472 renders, slowest shard 6,377 s; score 564 renders. There is no screen path (O1).

## 7. Guards, risks, cost

**The guard (amendment 8).** Every command first runs `scratch_exact.require_exact`. That covers its seven files and
the `phase_scratch_exact*` keys, and requires the exact test's targets, four answers keys and outcome on main. Then
this module's own guard runs:

- CODE_FILES must exist here and on origin/main and equal origin/main's: this module, `learn/readerr_run.py`,
  `scratch_exact.CODE_FILES`, `note_transcribe.CODE_FILES`, `note_tx.py` and `tx_run.py`; 17 files.
- The `phase_scratch_readerr*` keys must equal main's.
- Phase 2 checks each Phase 1 file's sha256 against `phase_scratch_readerr_frozen`.

**Guarded files.** `note_transcribe.CODE_FILES`, `scratch_exact.py`, `scratch_search.py` and `scratch_notes.py` are
imported, never patched. A test checks that the module assigns no attribute on an imported module. The key prefix
sits outside every guarded prefix: `phase_fs`, `phase_scratch_notes`, `phase_nr`, `phase_scratch_exact`,
`phase_replay` and `phase_wc`. Build 3's guard therefore never reads these keys.

**Order.** The units merge one at a time (O2): the runner first, then this module with this declaration. Phase 1 runs
only after both are on main, from a frozen detached worktree. No readerr PR merges while a build 3 hash PR is open
(O3).

**Writes.** Every write goes through `write_once`: under `PF/fs/readerr/` only, never over a file. A test walks the
module's code to check this.

**Privacy.** The ledger holds hashes and counts only (`ledger_body_refusal`). Tests use synthetic part keys. No song
title, file name, path, audio or setting is in git.

**Risks:**

- Correlation across parts is not cause within a part.
- Dry bank audio is not an amped stem with bleed.
- Web facts came through a summarising fetch; U4's manifest re-read them from primary sources.

**Cost (measured):** Phase 1 is CPU only, single thread. `scratch_exact build`, which also ran Basic Pitch and
rebuilt 94 guitars, took 344.7 s; that is an upper bound for `trace`. The other Phase 1 commands read stored files.

## 8. Done test

- `anatomy.json`, `real-compare.json`, `screen.json` and `candidates.json` exist under `PF/fs/readerr/`, each hashed
  on main.
- The four proofs held on 47 of 47.
- One RX code is recorded under `phase_scratch_readerr_outcome` after an audit.
- The guarded files and guarded keys on main are unchanged.
- The user holds a results section naming the tracking figure, the best candidate with its licence, and the priced
  next step.
