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
   - **octave-sub:** a missed truth note 12 semitones away, onsets within 50 ms. In practice this is only an
     octave below: an octave above a missed note with onsets within 50 ms always sounds against it, so it reads
     "harmonic" first;
   - **semitone-sub:** the same, 1 semitone away;
   - **timing:** a missed truth note of its pitch, onsets 50 to 150 ms apart;
   - **bend-fragment:** 1 to 3 semitones from a bent truth note sounding then (its `bend_curve` read against the
     truth list);
   - **rest.**

**Misses** (a missed truth note) take the first class that holds, in this order:

- **never-sounded:** the trace skipped it. Nominal list only; counted apart.
- **clean-up:** a note the clean-up dropped (six at once, out of range), of its pitch, onsets within 50 ms.
- **substitution:** an unpaired re-read note 1 or 12 semitones away, above or below, onsets within 50 ms.
- **timing:** an unpaired re-read note of its pitch, onsets 50 to 150 ms apart.
- **merged:** a re-read note of its pitch began more than 50 ms before it and still sounds at its onset.
- **chord-member:** its onset group holds 2 or more notes, and another member pairs.
- **rest.**

Beside each miss's primary class, every class that holds is recorded (`truth_classes_all`), with overlap counts:
per class, the misses where it holds at all, and per pair of classes, the misses where both hold (`miss_overlap`).

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
| `build.json`'s stored dry-domain figures, `xn-reread` and `xn-list` against the bank guitar: `logmel`; the pause error (the playing-frame mask's disagreement with the bank guitar's, 1 − agree, the mean over J0's frame sizes where stored, else the pause share's excess as an absolute value) | error |
| the same two guitars' `env_corr` | similarity |

Reported beside, not in the family: the nominal list's note error, and each guitar's signed pause excess. The three
`list_*` figures (`xn-list`'s guitar) are controls: read and reported, never frozen. With 29 figures on about 40 parts, about
one false "worse" is expected by chance. Every figure is reported, and the forward test is the first priced row.

### 3d. `real-compare`

The same anatomy runs, with no model run, on two sets:

- **The 79 stored Guitar-TECHS windows:** the truth report's note files, loaded by their recorded sha256, against
  the hashed truth listing.
- **The ten lists:** the install gate's stored events against the known notes.

The truth report's own counts (matched, ref, est) must reproduce on every window, 79 of 79; otherwise nothing is
written and the result goes to the orchestrator. Track 1's stored `tx-bp` extras are compared per window as a named
report (`track1_tx_bp_extras`), never a refusal. Each window keeps its file as its cluster, for the real-DI arm's
interval. The stored real-DI headline to set the bench beside is 945 extras: 38% harmonic, 16% re-finds, 47% other.

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
3. Each half gets its interval from `set_rows`' BKS+GOAT pool. In the all-47 read beside, the split runs over all
   47 parts, but each half's interval pools only its BKS+GOAT members.
4. `diff_interval(worse, better)` is labelled by `paired_reading` at its defaults, which is on J0's scale.

**A figure tracks** when three things hold:

- the label reads "worse";
- rho's sign agrees with the orientation;
- the split is not key-broken. `median_split` breaks ties by part key, so for sparse figures with many zeros it puts
  BKS low and GOAT high, a set confound. A figure whose split puts equal values on both sides is read by Spearman
  only and never frozen.

**The frozen figure** is the tracking figure with the largest |rho|, the `list_*` controls left out; ties go by the
family's order (`RX-tracks`). If
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
to the note's onset, and only for notes actually clipped: a read on a padded input (a lead-in or a shift, the pad in
seconds asked) whose onset sits at exactly 0. The track is one value per Basic Pitch frame over the note. The end frame
is found from the note-off through Basic Pitch's own time map (`model_frames_to_time`, with its window offset once
per 172-frame window), and the start frame is the end frame less the track's length. The frames before the pad are
dropped. `record_notes` applies this to every read of a record, each by its own pad.

**The pick, no bars (amendment 4):**

- **The minimum:** the point with the frozen figure's best pooled BKS+GOAT mean.
- **The level set:** every point whose paired difference against the minimum spans zero.
- **The pick:** the point of the level set nearest the frozen defaults. Distance is L1 in grid steps, with Melodia
  one step. Ties go to the stored point, then the better mean.
- **An edge minimum** extends that axis by the axis's own step at that edge, bounded only by the parameter's own
  range. The stored 58 ms is the lower edge, so the stored point itself extends to 26 ms. Thresholds stay inside
  (0, 1). The minimum length stays between one Basic Pitch frame (11.6 ms) and the window (10.25 s; a longer
  minimum keeps no note).
- **The extension repeats** (`edge_rounds`): the new points are read, the minimum is taken again, and the rule runs
  again, until the minimum leaves the edge or the parameter's range blocks the extension. There is no round cap; the
  ranges bound it.

**The labels.** The grid winner's in-sample label is worded "selected from 144". Its code comes from the cross-set
read: picked on BKS and read on GOAT, and the reverse. Both must agree; a sign disagreement means `RX-undecided`.
Leave-one-cluster-out is reported beside. The shift vote's k follows the same rule.

Every label at `small=0, big=0` is printed as "sign only, not on J0's scale, no size ruled out". At those settings
"matches" cannot occur, and "level" needs a zero-width interval.

**The real-DI arm is two-sided (amendment 5).**

- **The figure:** the frozen figure itself, per window, from `note_figures`, which `real-compare` already computes
  for Basic Pitch. Only the six dry-domain figures have no real-DI version; for those the arm reads note F (as note
  error) and says so.
- **The interval and labeller:** per window, the candidate's figure less Basic Pitch's (`tx-bp`), then
  `note_versions.set_numbers`, `note_tx.set_summary`'s file-clustered mean and 90% t interval (`real_di_interval`).
  This is the named exception to `set_rows`. The label is `paired_reading(0, 0)`, turned by the figure's
  orientation so it reads as the candidate's. Never `clear_above` or `decided_worse`.
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
  `scratch_exact.CODE_FILES`, `note_transcribe.CODE_FILES`, `note_tx.py`, `tx_run.py`, and the three modules the
  commands import inside them (`note_replay.py`, `pipeline_fix.py`, `song_bank.py`); 20 files.
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

## 9. Phase 2 amendment (2026-11-25; ledger `phase_scratch_readerr_p2`)

Declared 2026-11-25, after Phase 1 ran and its independent audit passed (PASS: `RX-untracked`, hashed as
`phase_scratch_readerr_frozen`). The amendment (the handover's `plans/note-reading-phase2-amendment.md`, planner
Fable) passed an independent review (Opus, high): PASS WITH AMENDMENTS. Its six binding amendments are built in below
and win where they differ from the amendment's text.

- **Code:** `learn/scratch_readerr.py`. Units A (the `xr-` row) and B (this section) are this PR. Unit C (Phase
  2a's `notes` and `score`) comes next, in the same two files; unit D (the `mt3` and `kong` model calls) waits for
  9h's condition.
- **Grepped first:** `XH-`, `xr-matched`, `xr-found`, `xr-filled`, `hand-plain` and `phase_scratch_readerr_p2` had no
  hit on main. `XR-` was not used: it is a substring of track 1's `TXR-` codes.
- **Keys to come:** `phase_scratch_readerr_xr_dry`, `phase_scratch_readerr_xr_answers_<row>` and
  `phase_scratch_readerr_xr_outcome`. `phase_scratch_readerr_notes` stays reserved for unit C.

**The order.** Phase 2a is descriptive. One hybrid row decides. Downloads come after it.

### 9a. Phase 2a (unit C; declared here, built next)

`notes` runs `learn/readerr_run.py` in the Basic Pitch venv, one thread:

- **Inputs:** the 47 stored bench inputs (`exact/work/reread/NNN-tr-di.wav`, each checked against the stored record's
  `input_sha256`), and for the real-DI arm the 79 Guitar-TECHS windows and the ten lists, each through
  `real_di_source`.
- **Reads per input:** `bp-grid` at the 144 declared points; `bp-grid` at the stored point with `lead_in_s` 1.0;
  `bp-shift` at the four offsets of 9b.
- **Proof, before anything is written:** `bp-grid`'s top-level events equal the stored re-read's events on 47 of 47.
  Otherwise `RX-stop`.
- **Outputs:** `notes/<candidate>/NNN.json` and the listing `notes.json`, each written once. The listing's sha256 goes
  to main as `phase_scratch_readerr_notes` before `score`.

`score` reads those files:

- **Candidates:** the 144 grid points, the lead-in, the shift vote at k = 2, 3 and 4, and F6 on the stored re-read;
  149 in all, with the stored re-read as the base.
- **Per candidate and part:** the 23 note figures on the as-played list, and the rebuilt guitar's `logmel`,
  `env_corr` and pause error against the bank guitar (the same `rebuild_redo` call as proof 4; at the stored point
  the three must equal `build.json`'s stored values on 47 of 47).
- **Per candidate:** each figure's paired difference against the stored re-read through `set_rows` on BKS+GOAT, with
  BKS alone, GOAT alone and all 47 beside; a frontier table (pooled precision, recall, extras and misses by class);
  the real-DI arm on note figures only, by P1 and P2, chords and scales, and the lists. Output: `candidates.json`.
- **Labels:** every line carries "descriptive: no figure decided (`RX-untracked`); sign only, not on J0's scale, no
  size ruled out". `grid_pick` is printed three times, by note error, `logmel` and `env_corr`, each as "would-pick,
  not acted on". An edge minimum is reported and not extended. Phase 2a records no RX code.

**The pause error, defined.** `build.json` does not store a pause error as one value. Phase 1's `*_pause_error` (and
the same figure for every Phase 2 guitar) is defined from its stored mask fields: for each of J0's three frame sizes
(1,024, 2,048 and 4,096), `figures.mask[n_fft].agree` is the share of frames on which the guitar's playing-frame mask
(within 40 dB of its loudest frame) agrees with the bank guitar's (`note_rebuild.mask_agreement`, over the whole
window). The pause error is the mean over the three sizes of 1 − agree; where `agree` is not stored, it is the
absolute value of the mean over the sizes of (`pauses_dry` − `pauses_true`) instead. The per-half pause shares `build.json` stores (`pauses[half][n_fft]`, for `xn-reread`
and the bank guitar) are reported beside, never as the figure. `xr-build` stores both for its own guitars.

**As built (unit C).** Both commands take `--shard k/n` (any n: they render nothing) and `--first n` (the timing run
on 3 inputs), and skip an input already done; `--combine` runs once after every shard.

- **`notes`:** per shard, three runner calls (the model loaded once a call), into a temporary folder.
  - **The lead-in** is a one-point `bp-grid` at the stored point (`grid` holds the stored onset threshold alone),
    because the runner refuses an empty grid. `make_spec` refuses one too, and a test runs every spec through
    `readerr_run.check_spec`.
  - **The proof runs first, per input:** bp-grid's top-level events and its stored-point events equal the stored
    read's; the shift vote's anchor, and its k = 1 vote, each equal the stored events, compared directly. A bench
    input that fails is not written, and the shard ends with `RX-stop`. For real-DI inputs the same comparison is a
    reported check.
  - **Each input's files sit in one folder,** `notes/inputs/<input>/`: the 148 runner candidates as
    `<candidate>.json`, the raw reads as `raw-<read>.json`, and `summary.json`. The folder is built whole in a fresh
    partial folder under `notes/partial/` and moved into place in one rename. An interrupted input leaves only a
    partial folder, which is never read and never blocks its rerun (the run lists any it finds). This one folder per
    input replaces the amendment's `notes/<candidate>/NNN.json`, so an input is written all at once.
  - **Inputs** are named `bench-NNN`, `truth-NNN` and `list-<name>`, never by file or song. A truth window's input is
    found among the truth report's stored inputs by its note file's `input_sha256`, and only those 79 are kept.
  - **Timing** (seconds per shard) goes to a sidecar under `notes/timing/`, outside every hash chain, so
    `notes.json`'s sha256 is the same however the run is sharded.
- **`notes --combine`:** every input is done; `RX-stop` unless the bench proof holds on 47 of 47; then `notes.json`
  lists every summary's sha256 (each summary lists its files' sha256).
- **`score`:** refuses unless `notes.json`'s sha256 is main's `phase_scratch_readerr_notes`, and loads each candidate
  only when its file is the listed one.
  - A bench part rebuilds once per distinct note list (the stored point is the base). The base must equal
    `trace.json`'s re-read. F6 uses main's `phase_nr_1_redo_fix_bend_frozen` rule.
  - **The real-DI arm runs through F1,** as the bench does. F1 only re-zeroes bends, and the note figures read no
    bend on real DIs, so the base's note figures there equal Phase 1's real-compare.
  - Each input is written once to `score/inputs/<input>.json`; timing goes to a sidecar under `score/timing/`.
- **`score --combine`:** `RX-stop` unless the base's rebuilt `logmel`, `env_corr` and mask equal `build.json`'s stored
  `xn-reread` figures on 47 of 47. Then `candidates.json` holds the paired reads, the frontier table (the bench, and
  each real-DI group), the real-DI arm (file-clustered, sign only), and the three would-picks, with `rx_code` null.

### 9b. The shift vote

- **Offsets:** four reads at pads of 0, 35, 71 and 106 Basic Pitch frames: 0, 8,960, 18,176 and 27,136 samples at
  22,050 Hz, or 0, 0.4063, 0.8243 and 1.2307 s (`SHIFT_OFFSETS_S`). These are 0, a quarter, a half and three quarters
  of Basic Pitch's 36,164-sample window hop, to the nearest frame.
- **Anchor:** the zero-offset read. It is the stored re-read, so k = 1 must reproduce the stored events on 47 of 47 (a
  proof).
- **Votes:** an anchor note's votes are 1 plus the number of shifted reads holding a note paired with it (`pair_by`:
  same pitch, onsets within 50 ms, one to one, closest first).
- **Kept:** an anchor note with votes at or above k, for k = 2, 3 and 4, exactly as the anchor read it (onset, end,
  amplitude, bend track).
- **Order:** the vote runs on the runner's re-based events (`record_notes`); the voted list then goes through
  `timed_notes` and F1 once, like any candidate.
- **It only removes notes.** Beside, never a candidate: the notes every shifted read finds that pair with no anchor
  note (`shift_unanchored`), counted and matched to the truth. If true recoveries are material, a symmetric rule gets
  its own amendment.

### 9c. The hybrids (`xr-` rows)

Every hybrid is an oracle list, diagnostic only. Each is built from `trace.json`'s stored re-read (after timing and
F1) and its nominal exact list.

| Row | Note list | Run |
|---|---|---|
| `xr-matched` | The re-read notes that pair with an exact note (`note_versions.hand_pairs`). Each unpaired re-find first hands its end to its note (`note_fixes.refind_pairs`, `join_refinds`); every other unpaired note leaves | First |
| `xr-found` | The exact notes the re-read found, as exact | Only when the code asks (XH-rest) |
| `xr-filled` | The whole exact list plus the re-read's unpaired notes, not joined | Only when the code asks (XH-undecided) |
| `hand-plain` | The plain drop (`note_versions.hand_notes`, nv-hand's rule) | Built beside; its dry figures reported; never searched |

- **Why joined (review amendment 4).** A plain drop leaves a re-found held note with its early end, which `ring-soft`
  then cuts (nv-hand's known fault). Joining is the faithful "this extra never happened" for a re-find.
- **The chain rule (review amendment 4).** `refind_pairs` points a re-find at the latest same-pitch note still
  sounding, which may itself be an unpaired re-find. A note is joined when it is unpaired and its chain root is a kept
  note (`chain_root`); `join_refinds` already follows roots, so a chain's last end goes to its root. A re-find whose
  root is an unpaired note leaves with it.
- **Beside the build (review amendment 4):** the number of joins; how many of them the nominal anatomy calls
  re-finds (409 re-finds on the nominal list); joined ends that run past the exact partner's end; and the true notes
  dropped with timing or substitution extras (12 + 29 extras, 53 + 58 misses on the nominal list).

### 9d. `xr-build` and `xr-check`

**`xr-build`** (zero renders), from a frozen detached worktree of main:

- **The call:** `NR.rebuild_redo("tr-di", notes, len(bank), bank, bank_guitar, ring, finish=finish, loud=None)`,
  with the part's finish from `NT.build_todo`, as `cmd_trace` does. Four rebuilds a part (review amendment 5): the
  re-read, the exact list, `xr-matched` and `hand-plain`.
- **Four proofs, before anything is written:** (1) the full re-read reproduces `dry/xn-reread`'s sha256 on 47 of
  47; (2) the exact list reproduces `dry/xn-list`'s on 47 of 47; (3) the pairing's counts equal `anatomy.json`'s
  nominal `matched` per part (3,210 pooled); (4) CODE_FILES equal main's. A failing proof is `XH-stop`: nothing is
  written.
- **Outputs:** `xr/dry/<row>/<part>.npy` (each through `write_once_npy`) and `xr/build-first.json`: per part each
  guitar's sha256, the kept, joined and removed counts, the join report, the rebuild report, `NR.figures` against
  the bank guitar, the pause error, and the pause share per half beside the bank guitar's.
- **Before any search,** the build file's sha256 goes to main as `phase_scratch_readerr_xr_dry`. A part whose
  search-half pause share would make J0 refuse is listed for the orchestrator: a report, not a stop.
- `xr-found` and `xr-filled` are built by `xr-build --set found` and `--set filled` (keys `_xr_dry_found`,
  `_xr_dry_filled`), which refuse unless main's `phase_scratch_readerr_xr_outcome` reads the code that asks for them.

**`xr-check`** (about 50 renders, the exact test's two checks), on `SN.check_parts`' two parts with `xn-reread`'s
stored guitar: this module's start reference and `S.run_part(budget=10, step1_only=True)` must equal `xn-reread`'s
stored first 10 evaluations (`SN.search_check_verdict`), and this module's score of `xn-reread`'s hashed answers must
equal its stored score files (`SX.score_check_verdict`). A mismatch is `XH-stop`.

### 9e. The row's commands

They follow `scratch_exact`'s pattern, with their own paths under `PF/fs/readerr/xr/`:

| Command | Does | Reuses unchanged |
|---|---|---|
| `xr-search --row R --shard k/3 [--rerun]` | The guitar (sha256 from the build file), the blanked record, the start reference, the search | `SX.require_records`, `SX.load_record_blank`, `SX.synthetic_part`, `SX.start_reference`, `S.search_row_part`, `SX.disk_guard`, `S.rerun_path` |
| `xr-answers --row R` | Answers, refusals, coverage; sha256 to main as `phase_scratch_readerr_xr_answers_<row>` before the score | `S.with_reruns`, `S.rerun_refusal`, `SX.dry_refusal`, `SX.xn_answer_parts`, `SX.coverage` |
| `xr-score --row R --shard k/3 [--rerun]` | Cen and the five settings through the bank guitar, held half, lag 0 | `SX.score_exact_part`, `SX.load_record`, `SX.require_targets` |
| `xr-read` | The read and the XH code, once | `SX.row_numbers` for the stored rows, `SX.deciding_bug`, `S.nonfinite_rule`, `SX.xn_numbers`, `S.itt_per` |

- **Written here,** because `scratch_exact`'s versions only know its four rows: the paths (`xr_path`), the answers
  key, `load_xr_guitar` and `read_xr_parts`. A test holds `read_xr_parts` equal to `SX.read_xn_parts` on made-up
  score files.
- **The search never opens** `targets.json`, a target or score file, any answers file, `trace.json` or
  `anatomy.json` (`xr_search_open`; an `ast` test walks every function the search reaches).
- **The write rule widens.** Guitars go through `write_once_npy`. Paths handed to `SX.start_reference` and
  `S.search_row_part` come only from `xr_path`, under `PF/fs/readerr/`; a search's output path must not exist
  (`fresh_xr_path_of`), since `search_row_part` writes through `P.save`.
- **A byte-identical guitar takes the stored record byte for byte** (`write_bytes_once`). That happens for `xr-found`
  on the one part with no misses.

### 9f. The read

Per part, on the answer arm, with shrunk beside:

- **E = G(`xr-matched`) − G(`xn-reread`).** Below zero means the preset lands closer without the extras.
- **M = G(`xr-matched`) − G(`xn-list`).** Above zero means the misses and the matched notes' timing, ends and bends
  still cost.
- Reading proper is M − E, per part, exactly.

**Rules:**

- **Intervals:** `set_rows` on BKS+GOAT decides. BKS alone, GOAT alone, clean, crunch, all 47, checkpoints 50, 100
  and 200, and leave-one-cluster-out sit beside.
- **Labels:** E by `number_reading` (a gain) and `paired_reading`; M by `paired_reading`; all at their defaults, since
  both are on J0's scale.
- **Refusals, E and M alike (review amendment 1):** S1. A rerun, then Cen; intent-to-treat decides, passing-only
  beside, `refusal-sensitive` when the codes differ. M is a deciding read, so Phase 1's amendment 3 (passing-only
  primary, for the descriptive tracking figures only) does not apply to it. The exact test decided D_list the same
  way (+0.321 by intent-to-treat, +0.285 passing-only beside), and stored reading proper is +0.552 by
  intent-to-treat.
- **Beside, never deciding:** the share −E over reading proper, by `SX.fieller_share`; and the forward test: per part
  the change in `logmel` and in `env_corr` (the `xr-matched` guitar less `xn-reread`'s, each against the bank guitar)
  against E: Spearman and sign agreement pooled on the 40, as every other read, with each set's Spearman and all 47
  beside; no median split. A dry figure becomes Phase 2's
  scoring figure only by a further amendment.
- The rows are saved (`xr/rows.json`) before the code (`xr/report.json`).

**Phase 2's scoring figure follows the code, declared now (review amendment 3):**

- `XH-both`: note error.
- `XH-extras`: `extra_rate` alone rewards dropping true notes. The best no-download candidate of 2a's 149 is picked
  by `extra_rate` with `miss_rate` not decided worse (sign only), under the cross-set rule (picked on BKS and read on
  GOAT, and the reverse).
- `XH-rest`: no figure is frozen now. M bundles the 302 misses with the 3,205 matched notes' timing, ends and bends,
  and `miss_rate`'s Phase 1 halves were degenerate. Its next row, `xr-found`, separates the two (`xr-found − xn-list`
  is the misses, `xr-matched − xr-found` is matched-note error); the figure is chosen after it.
- Otherwise note error stays "fidelity only".

### 9g. The outcome table (`XH_TABLE`, the first that holds; coded and tested before any run)

| Code | When | Meaning | Next step |
|---|---|---|---|
| `XH-stop` | A build proof or `xr-check` fails, a zero distance on a deciding setting, or a label is missing (no interval) | Nothing is read | To the orchestrator |
| `XH-anomaly` | E reads "worse", or M reads "better" | The preset lands decidedly further without the extras, or an oracle list beats the exact list | Audited before anything is said; Phase 2b waits |
| `XH-both` | E passes and M reads "worse" | The extras and the rest both cost; the share sits beside | Phase 2 scores by note error; Phase 2b runs; to the user |
| `XH-extras` | E passes, M not "worse" | With M matching: the extras carry reading proper. With M undecided: the extras cost; the rest not decided | Phase 2 scores by `extra_rate` with `miss_rate` not decided worse; Phase 2b runs; to the user with the best no-download candidate by that rule as the next `xr-` row |
| `XH-rest` | M reads "worse", E does not pass | The shown cost sits in misses and matched notes; the text says whether E fails or is undecided | No figure frozen now; Phase 2b runs; to the user with `xr-found` as the next row |
| `XH-undecided` | Anything else | The split is not decided; undecided is not failed | Phase 2a stays descriptive; Phase 2b does not run on this; to the user with `xr-filled` or parking the track behind the rebuild bench |

M reading "better" is an anomaly because an oracle list beating the exact list is implausible; under intent-to-treat
the refused `xn-list` part also pushes M that way, since M there is just G(`xr`). E "worse" and E "passes" cannot both
hold, and `number_reading`'s "passes" is the same rule as `paired_reading`'s "better". A test checks that every
combination of labels ends in exactly one code.

### 9h. When Phase 2b's downloads run

- **After** `phase_scratch_readerr_xr_outcome` is on main with `XH-both`, `XH-extras` or `XH-rest`.
- **Under `XH-undecided` or `XH-anomaly`,** only on the user's word.
- **Until then** nothing is fetched, and the runner's `mt3` and `kong` stubs stay stubs.
- **When they run:** CPU only, at most 2 threads, timed on 3 parts first, under `DOWNLOAD_RULES`, beside any renders.

### 9i. Write-up wording (binding on the results text)

- Say **"no figure is decided"**. Never "nothing tracks" or "reading errors do not matter".
- **Print every pooled Spearman or split with its BKS and GOAT values beside it.** A pooled value whose sets disagree
  in sign is marked "sets disagree".
  - Note error is the example: −0.035 pooled, −0.15 on BKS, +0.08 on GOAT.
  - State the set imbalance: mean reading proper 0.638 on BKS against 0.416 on GOAT.
- **A half whose interval has under 3 degrees of freedom is printed "degenerate half: not read"**, not "undecided".
  That covers `miss_rate`, `extra_octave-sub` and the others the audit listed. `extra_timing` has no interval at all.
- **The intent-to-treat "worse" reads** (`reread_env_corr`, `extra_rate`) are stated as coming from the one refused
  part: +1.442 at Cen, about +2.43 with its baseline imputed, fragile when it is left out. They are never a finding.
  The refused part is never named.
- **The dry figures "lean the expected way in both sets, undecided".**
  - `reread_env_corr`: −0.34 on BKS, −0.24 on GOAT; pooled +0.216 [−0.138, +0.569].
  - `reread_logmel`: +0.15 and +0.30; pooled +0.190 [−0.096, +0.476].
- **The key-broken flag is broader than amendment 2 meant;** a tie-aware split gives the same code (the audit's
  recompute).
- **Anatomy:** 1,953 extras against 302 misses on the as-played list. Real DIs carry more unclassified extras, 0.422
  against 0.110 per truth note.
- **The screen reads "no screen".**

### 9j. Cost, order and render slots

**CPU, one process beside the renders, stated as ranges (review amendment 5).** The 0.85 s a rebuild is the original
plan's planner figure ("0.85 s mean under load, 2.28 s worst"); no log for it was found. `trace` measured 138.8 s for
47 parts, 2.95 s a part including the trace work: an upper bound for one rebuild.

| Work | Count | Rate | One core |
|---|---|---|---|
| Phase 2a: Basic Pitch reads | 816 (282 bench, 534 real-DI) | 1.24 to 1.64 s a read | 17 to 22 min |
| Phase 2a: note creation at 144 points | per input | not measured | timed on 3 parts first |
| Phase 2a: rebuilds | 7,050 | 0.85 to 2.28 s | about 100 min to about 4.5 h; timed on 3 parts first |
| `xr-build`: rebuilds | 188 (four a part) | 0.85 to 2.95 s | about 3 to 9 min |

**Renders (from `xn-reread`'s measured logs):** `xr-check` about 50; `xr-search` about 12,472 with the slowest
shard about 6,377 s on 3 processes; `xr-score` 564 renders (407 s for `xn-reread`); about 13,040 renders and
1 h 53 min in all.

**Order:**

1. Units A and B (this declaration), the review, the merge. Zero renders.
2. `xr-build` and its hash PR (`phase_scratch_readerr_xr_dry`).
3. Unit C, then `notes`, its hash PR (`phase_scratch_readerr_notes`), and `score`.
4. Once the rederive track's `xf-now` score has finished and no rederive row waits for the slots (the orchestrator's
   call, checked with `pgrep`): `xr-check`, then `xr-search` on 3 shards, then `xr-answers`, its hash PR, and
   `xr-score`. The 20-minute render-rate check applies.
5. `xr-read`, an independent audit, the results PR (`phase_scratch_readerr_xr_outcome`), then the code's next step.

**The check after each merge:** the test commands pass on main; `git diff --quiet` over CODE_FILES less this track's
two own files exits 0; only `phase_scratch_readerr*` keys changed; from a frozen detached worktree, `xr-build` reports
its four proofs on 47 of 47 before any render. Nothing merges into `scratch_readerr.py` while `xr-` commands are
queued, or the worktree is re-cut and the proofs rerun.

**The guard widens.** CODE_FILES now also holds the modules the new commands import inside them: `cc_build.py`,
`full_controls_c1b.py`, `local_objective.py`, `knob_ceiling.py` and `analysis/aligned.py`; 25 files in all.

**Privacy:** synthetic part keys in tests; the ledger holds hashes and counts only; the write-up never names the
refused part, since its key holds file names.

## 10. Phase 2b amendment (2026-11-26; ledger `phase_scratch_readerr_p2b`)

Declared 2026-11-26, after the `xr-matched` row read **XH-both** (#638, audited; `phase_scratch_readerr_xr_outcome`),
before anything in it is installed or run. The amendment (the handover's `plans/note-reading-phase2b-amendment.md`,
planner Fable) passed an independent review (Opus, high): PASS WITH AMENDMENTS. Its eight binding amendments are
built in below and win where they differ from the amendment's text.

- **Code:** units D (`learn/readerr_run.py`: the `mt3` and `kong` calls, the pickle scan, the guarded load, the key
  report, the network and process refusals), E (`learn/scratch_readerr.py`: `tx-notes`, `tx-score`, `select`, the
  gate, `xr-cand`, `XP_TABLE`), F (`learn/readerr_tools.py`: `tx-install`, `tx-fetch`, the manifest reader) and G
  (this section, the ledger key). They share no files and merge as one set after review (the orchestrator's call).
- **Grepped first:** `readerr_tools`, `tx-install`, `tx-fetch`, `tx-notes`, `tx-score`, `ymt3`, `kong-fl`,
  `kong-gaps`, `xr-cand`, `XP-`, `tools-gate`, `notes-tx`, `candidates-tx` and `phase_scratch_readerr_p2b` had no
  hit in `docs/`, `learn/` or `tests/` on main.
- **Keys to come:** `phase_scratch_readerr_tools` (the gate), `phase_scratch_readerr_notes_tx`,
  `phase_scratch_readerr_candidates_tx`, `phase_scratch_readerr_outcome` (the RX code, with `select.json`'s sha256),
  and only if a row runs: `phase_scratch_readerr_xr_dry_cand`, `phase_scratch_readerr_xr_answers_cand`,
  `phase_scratch_readerr_xp_outcome`.

**The goal.** At zero renders, does an open transcriber remove most of Basic Pitch's extras on the bench without
adding misses? A row is priced only for a candidate the row could actually decide.

**Why the rule changes.** `XH-both` named note error as Phase 2's figure (9f). Note error's would-pick cuts extras
1,953 → 378 but doubles misses 302 → 620. "Misses not read worse" alone is too weak: one stored setting cuts 53% of
extras with 28% more misses and still reads "undecided" on misses. The predicted net gain (10c) is what stops it. The
rule below replaces note error as Phase 2's deciding figure.

### 10a. The run flow

**The manifest.** U4's download manifest (a hand-back, outside the repo) is read only when its sha256 is the one
pinned in `readerr_tools.MANIFEST_SHA256`. Every URL, size, sha256, lock line and pinned path comes from it.

**`tx-install`** (`readerr_tools`, zero renders). Two venvs under `tools/readerr/` under the data root, each made by
the pinned standalone CPython 3.12.16 (its version checked; it replaced pyenv's 3.12.13, see 10j):

- **Lock A:** `mt3-infer` 0.2.0 with torch 2.7.1 (52 wheels). **Lock B:** the Riley models with torch 2.8.0 (52
  wheels).
- **How:** `pip install --require-hashes --only-binary :all: --no-deps --no-cache-dir` from the manifest's lock
  lines, each checked (one hashed pin a package, torch at the declared version). The installed set must equal the
  lock (`pip list`).
- **The two code archives (review amendment 7).** `hf_midi_transcription` at `96f6797` and the fork of
  `piano_transcription_inference` at `cfe28ed`, each from its commit-pinned GitHub URL, checked against the
  manifest's size and sha256 and the archive's own commit header. Their build files (`setup.py`, `pyproject.toml`)
  are read and recorded. They are **unpacked, never built**: only the import package (and `hf_midi_transcription`'s
  `instruments.json`) is unpacked, with tarfile's data filter, and one `.pth` file in lock B's site-packages points
  there. No build code runs; setuptools sits in lock B with its hash, and is never called.
- **No upstream import** in the install: the gate's refusals must come first (review amendment 7).
- **Refusals:** an existing venv or record, a hash mismatch, or free disk that would end under the 31 GB guard. Free
  disk is printed before and after. The record is `install-<lock>.json`. A failure moves what the run made aside.

**`tx-fetch`.** The three checkpoints from the manifest's pinned `resolve/<commit>` URLs to its pinned paths:
YourMT3+ `YPTF.MoE+Multi (noPS)` (kept named `last.ckpt`), `guitar-fl.pth` and `guitar-gaps.pth`. Size and sha256
must equal the manifest's. A mismatching file is moved aside, never loaded, never deleted. `mt3.pth` is never fetched
(O5). The same disk refusal and prints apply.

**Writes.** `readerr_tools` writes only under `tools/readerr/` under the data root, never over a file. `scratch_readerr`
writes only under `PF/fs/readerr/`, as before.

**The gate (unit E, review amendment 8),** before any candidate is read. It calls D's modes and F's manifest reader,
and writes `PF/fs/readerr/tools-gate.json`, hashed as `phase_scratch_readerr_tools`:

1. **Pickle scan (review amendment 7).** Standard-library `pickletools` reads every pickle member of each zip
   checkpoint (`data.pkl` and any other `.pkl`). It handles `GLOBAL` and `STACK_GLOBAL` with memo resolution. Any
   global it can't resolve refuses, and so does any global outside the manifest's list for that file.
2. **A fixed denylist** refuses, whatever the manifest lists: `builtins` `eval`, `exec`, `compile`, `getattr`,
   `__import__` and `open`; and the modules `os`, `posix`, `subprocess`, `sys`, `importlib`, `runpy`, `socket`,
   `shutil`, `pickle` and `marshal`. The allowlist is printed in the gate and audited before the hash PR.
3. **Guarded load (O6).** Every `torch.load` goes through one wrapper. It accepts only the pinned path, opens the file
   itself (a file object it did not open refuses), forces `weights_only=True`, and allowlists exactly that file's
   scanned globals. The upstream loaders that hard-code `weights_only=False` are reached only through it.
4. **Key report (O7).** Missing and unexpected keys after each load are written. A missing key the model needs
   refuses.
5. **No runtime fetch.** The offline variables are set. Before any upstream import, the runner's torch modes refuse
   any socket connect, `os.system`, `os.exec*`, `os.spawn*`, `os.posix_spawn*`, `os.popen`, `subprocess` and
   `_posixsubprocess` (review amendment 7). A test covers each.
6. **Repeatable.** Three runs on 4 bench parts give identical events, two in one process and one fresh. A candidate
   that does not repeat is reported and cannot be priced.
7. **Timed on 3 parts first** (`--first 3`), at 1 and at 2 threads. The projection for all 136 inputs is printed
   before the full run.
8. **The allowlist's source (O9).** Each file's allowlist comes from a standard-library scan of the fetched
   checkpoints, then an audit, then a manifest v2 written as a new file (U4's is never edited); a small PR then updates
   `readerr_tools.MANIFEST` and `MANIFEST_SHA256` to it.

**`tx-notes`** then runs every input through `readerr_run.py`. `tx-notes --combine` writes `notes-tx.json`; its sha256
goes to main as `phase_scratch_readerr_notes_tx` before `tx-score`.

### 10b. The candidates

- **Inputs:** Phase 2a's 136: 47 bench inputs and 89 real ones. The bench inputs are each checked against their
  stored `input_sha256`; the 79 Guitar-TECHS windows and the 10 lists go through `real_di_source`, where P3 refuses. Each tool resamples with its own
  loader, with versions recorded.

| Id | Transcriber | Own settings, from one inference | Output |
|---|---|---|---|
| `ymt3` | YourMT3+ `YPTF.MoE+Multi (noPS)`, lock A | `programs`: `pitched`, every pitched programme (as shipped), or `guitar`, the guitar programmes only | No loudness, no bends |
| `kong-fl` | Riley's `guitar-fl`, lock B | `onset_threshold` 0.2, 0.3, 0.4, 0.5 × `frame_threshold` 0.1, 0.2, 0.3; shipped 0.3 and 0.1 (the fork's defaults). The grid runs only if the pinned post-processor takes the thresholds without a patch (unit D reports which) | Loudness; no bends |
| `kong-gaps` | Riley's `guitar-gaps`, lock B | The same | The same |

- **The grids, declared (review amendment 5).** `kong` has 4 × 3 = 12 points a model; `ymt3` has 2. Each is scored
  plain and as `+bp`: (12 + 12 + 2) × 2 = 52 lists at most.
- **"Nearer the shipped settings" (review amendment 5).** For `kong`, the L1 distance in grid steps from the shipped
  point (0.3, 0.1), each axis's step 0.1. For `ymt3`, every pitched programme is 0 and the guitar programmes only is
  1. Ties go to the shipped point.
- **The bends variant.** `<id>+bp` takes loudness and bends from its paired Basic Pitch note (`note_tx.ms_with_bp`).
  This is applied after the candidate's own timing, from the stored re-read after F1, and F1 is not applied again.
- **Same treatment, figures and reads as Phase 2a.**
  - `scored_list` applies the clean-up, the window, the coarse offset, the ±20 ms snap and F1.
  - On the bench: the 23 note figures, and the rebuilt guitar's `logmel`, `env_corr` and pause error against the
    bank guitar.
  - On the real-DI arm: the note figures, by P1, P2, chords, scales and the lists, file-clustered, sign only.
  - Reads are paired against the stored re-read through `set_rows` on BKS+GOAT, with BKS alone, GOAT alone and all
    47 beside. Every label is sign only.
- **Output:** `candidates-tx.json`, hashed as `phase_scratch_readerr_candidates_tx`, with each candidate's licence
  record (10f).
- **MuScriptor stays out.** It needs the user's yes and never ships.

### 10c. The selection rule (`select`, zero renders)

**Fixed before anything is installed,** read by code from the hashed `xr/rows.json` (`phase_scratch_readerr_xr_outcome`
`rows_sha256` c7bc4b14…). The values are from the answer arm, intent-to-treat, on the 40:

- **E** = −0.2752 [−0.4057, −0.1448];
- **M** = +0.2768 [+0.1414, +0.4121] (+0.277 rounded);
- **h** = 0.1305, the half-width of E's interval: the bench's measured resolution for one row against another.

**Per candidate c,** from its as-played counts on the 40 (the stored re-read has 1,624 extras and 246 misses there):

- **x** = 1 − extras_c / extras_base, the share of extras removed;
- **y** = misses_c / misses_base − 1, the share of misses added;
- **g** = E·x + M·y, the predicted change in G against `xn-reread`. Below zero is better.

**A candidate qualifies when every item holds.** Every item is read on the `+bp` variant, the list that would be
priced (review amendment 3). Its counts equal the plain variant's, but its timing and dry figures differ.

1. `extra_rate` reads "better" against the stored re-read, sign only, on the 40.
2. `miss_rate` does not read "worse", sign only.
3. **(Review amendment 3.)** `end_error` and `onset_error` (the matched notes' median absolute onset error, in ms,
   after the snap) do not read "worse", sign only. g prices counts only. It ignores changes to matched notes' onsets, ends and bends, which
   a new transcriber changes most.
4. g ≤ −h: a row would be expected to decide it.
5. **Cross-set, for any candidate whose settings the data chose.**
   - The family's pick on BKS (the lowest g among members meeting 1 to 3 there) must meet 1 to 4 on GOAT, and the
     reverse.
   - If the two picks differ, the one nearer the shipped settings (10b) is taken, and it must pass both ways.
   - A shipped-settings candidate needs no cross-set read.
6. **No real-DI harm.** On P1, P2 or the lists, neither `extra_rate` nor `miss_rate` reads "worse" against Basic
   Pitch.
7. It repeats (gate item 6).

**The pick.** The qualifier with the lowest g. Exact ties go first to no download, then to a licence the product can
use. The priced list is the pick's `+bp` variant.

**Leak-free.**
- The rule and its constants are in this key before anything is installed.
- `select` refuses unless both candidate files' sha256 are on main.
- No J0 figure of any candidate exists before its guitar is hashed.

**What it assumes.**
- g is a straight-line prediction from two measured slopes, and it ignores E's and M's own intervals.
- M's slope overstates a miss, because M also holds matched notes' timing, ends and bends. So the rule is harsh on
  misses.
- g is never a reading. Only the row decides.

**Beside, never deciding.**
- **The refusal-sensitive check (review amendment 4).** Everything is recomputed together from the passing-only
  values: E −0.2203 [−0.3695, −0.0710], h 0.1492, M +0.2925. If the set of qualifiers changes (not only the pick),
  the read is labelled `refusal-sensitive` and goes to the user before any row.
- End error, the attack rates and the dry figures per candidate.
- **The shrunk arm's caveat.** E is not shown there (−0.007 [−0.122, +0.109]), so the predicted gain is for the full
  answer only.

### 10d. How the rule feeds `RX_TABLE` (review amendment 1)

The codes are unchanged; their inputs are redefined, superseding 9f's note-error line for `XH-both`. The code follows
the pick's kind. The order is transcriber, setting, harm, undecided, none, and the first that holds is the code:

| RX code | Under this rule | Next step |
|---|---|---|
| `RX-transcriber` | The pick (10c) is a downloaded transcriber | To the user with the licence table and the `xr-cand` row |
| `RX-setting` | The pick is a no-download candidate | To the user with the `xr-cand` row |
| `RX-harm` | Some candidate meets items 1 to 5 and 7, but item 6 fails | Reported; not priced |
| `RX-undecided` | None qualifies; some candidate has g < 0 with item 1 ("better by the mean") | No priced row; to the user with each candidate's g |
| `RX-none` | Nothing else | Basic Pitch as frozen stays; to the user |

- **What the inputs mean.** "Decided better" is items 1 to 5 and 7. "Better by the mean" is g < 0 with item 1.
  "Real worse" is item 6 failing. `RX-stop` and the table's other codes are unchanged.
- **If none qualifies:** no priced row. By the stored figures, the best no-download candidate predicts about half of
  what a row can resolve (seen, below), so about 13,000 renders would be expected to read undecided. Pricing it
  anyway is the user's option, never the default.

### 10e. The priced row: `xr-cand` (only on `RX-transcriber` or `RX-setting`, with the user's word)

- **`xr-build --set cand`** (zero renders). It refuses unless main's `phase_scratch_readerr_outcome` names the
  candidate. The guitar comes from the same `rebuild_redo` call, from the candidate's hashed `+bp` list. Four proofs
  run before anything is written:
  1. the stored re-read reproduces `dry/xn-reread`'s sha256 on 47 of 47;
  2. the candidate's note files equal the listing's sha256;
  3. the guitar's dry figures equal `tx-score`'s stored ones on 47 of 47;
  4. CODE_FILES equal main's.

  The build's sha256 goes to main as `phase_scratch_readerr_xr_dry_cand`.
- **`xr-check` is rerun (review amendment 2),** about 50 renders, before the search. The source test stays beside it:
  `cmd_xr_search`, `cmd_xr_score`, `load_xr_guitar`, `read_xr_parts` and every function they reach must be
  byte-identical to main at `cd262a10`.
  - Why the rerun: `xr-check` passed before #630 changed `scratch_readerr.py`, and unit E edits `XR_ROWS`,
    `XR_SETS` and the choices to add `xr-cand`.
  - A source test can't see the plugin or the render environment; only renders can.
- **The rest of the row** is `xr-search`, `xr-answers` and `xr-score` with `--row xr-cand`, unchanged. The answers
  hash is `phase_scratch_readerr_xr_answers_cand`.
- **The read** (`xr-read --row xr-cand`), S1 as for `xr-matched`: intent-to-treat decides, passing-only beside.
  - **P = G(`xr-cand`) − G(`xn-reread`)**, labelled by `paired_reading` at its defaults (review amendment 6;
    `number_reading` has no "worse"), with `number_reading`'s "passes" beside.
  - **L = G(`xr-cand`) − G(`xn-list`)**, labelled by `paired_reading`.
  - **Beside:** P less its prediction g; G(`xr-cand`) − G(`xr-matched`); the shrunk arm; each set; checkpoints.

**`XP_TABLE`** (the first that holds; coded and tested before any run):

| Code | When | Meaning | Next step |
|---|---|---|---|
| `XP-stop` | A build proof or `xr-check` fails, a zero distance on a deciding setting, or a label is missing | Nothing is read | To the orchestrator |
| `XP-anomaly` | L reads "better" | A transcriber's list beats the exact list | Audited before anything is said |
| `XP-closes` | P passes, L "matches" | The candidate removes the shown reading cost | To the user with the licence question and the stem-notes step |
| `XP-gain` | P passes, L "worse" or undecided | A shown gain; with L "worse", reading still costs L; with L undecided, "gain shown; the remaining cost not decided" (review amendment 6) | To the user with the licence question |
| `XP-worse` | P reads "worse" | It lands further than Basic Pitch's re-read; the prediction failed | Not adopted; reported with g; no second row without an amendment |
| `XP-undecided` | Anything else | Not decided; undecided is not failed | To the user with P's interval beside g |

A test checks that every pair of labels ends in exactly one code.

### 10f. Licences (copied by code: `readerr_tools.licence_record`)

Each candidate's record in `candidates-tx.json` and `select.json` holds `code`, `weights_data` and `product_status`,
copied from the manifest. Section 5's value is used where the manifest records none.

| Candidate | Code | Weights and training data | Product status |
|---|---|---|---|
| Basic Pitch settings | Apache-2.0 | In the wheel | Usable |
| `ymt3` | GPL-3.0 (the author's repo) or Apache-2.0 (the Space and `mt3-infer`'s copy) | No licence covers the weights | Unresolved |
| `kong-fl` | MIT claimed, no LICENSE file (`hf_midi_transcription` and the fork) | Sold transcriptions aligned to commercial recordings; the base model trained on MAESTRO (CC BY-NC-SA) | Unclear, NC assumed |
| `kong-gaps` | The same | GAPS: three claims disagree | Unclear, NC assumed |
| soxr (a lock dependency) | LGPL-2.1-or-later | — | Noted |

All are fine for development (O8). The user is asked only on `RX-transcriber`, with this table beside the proposed
row.

### 10g. CPU and disk

**CPU, measured in Phase 2a.** `notes`: 133 inputs in 441.5 s of core time over 3 shards, 3.3 s an input. `score`:
6,284 rebuilds in 8,414 s, 1.34 s a rebuild with its scoring.

| Work | Count | Rate | Core time |
|---|---|---|---|
| Torch reads | 136 inputs × 3 checkpoints | Not measured on this CPU | Timed on 3 parts first |
| Rebuilds | At most 52 lists × 47 parts = 2,444 | 1.34 s, measured | About 55 min (derived) |

One runner process at a time, at most 2 threads, beside the render rows. The 20-minute render-rate check applies.

**Disk.** About 43 GB was free when this was declared (40 GiB); the guard is 31 GB.

| Item | Size |
|---|---|
| Weights (3 files) | 759,640,462 B |
| Code archives | 4,838,161 B |
| Wheels, locks A and B | 378,095,035 B |
| **Download total** | **1,142,573,658 B** |
| Two installed torch venvs | About 1.6 to 1.8 GiB, an estimate from MuScriptor's measured 857,916 KiB venv |
| Note files | About 0.3 GB, from Phase 2a's measured 809 MB for 148 candidates |
| The `xr-cand` row | About 0.1 GB (`xr/` holds 195 MB for two guitar sets and one row) |

`tx-install` refuses unless free disk less the lock's wheels, one measured venv (857,916 KiB) and the archives stays
at or above the guard. `tx-fetch` refuses unless free disk less the files to fetch stays at or above it.

**Measured row cost (`xr-matched`).** 12,082 search renders (2 h 19 min), 96 start-reference renders and 552 score
renders (7 min). `xn-reread` alone took 1 h 53 min for about 13,040 renders.

### 10h. Seen before this rule was written (labelled so wherever printed)

- **The best stored no-download candidate:** g −0.068 on the 40 (−0.075 on the 47, with 54% of extras removed and
  26% more misses), against a needed −0.131.
- **The shift vote at k = 4:** g −0.032 on the 40 (−0.029 on the 47).
- **Note error's would-pick:** 378 extras and 620 misses, against 1,953 and 302.
- **One stored setting:** cuts 53% of extras with 28% more misses, and reads "undecided" on misses.
- **The constants:** E and M of `xr-matched`, both arms.
- **Every Phase 2a figure** in `candidates.json`.

No transcriber candidate's figure exists yet.

### 10i. Order and checks

**Order:**

1. D, E, F and G (this declaration), the review, one merge (#638 is on main).
2. `tx-install`, `tx-fetch`, the gate, and its hash PR (`phase_scratch_readerr_tools`).
3. `tx-notes` and its hash PR, then `tx-score` and its hash PR.
4. `select`, an independent audit, and the outcome PR (`phase_scratch_readerr_outcome`).
5. Only on `RX-transcriber` or `RX-setting`, with the user's word, and when no rederive row waits for the slots:
   1. `xr-build --set cand` and its hash PR;
   2. `xr-check`;
   3. the search on 3 shards;
   4. the answers PR;
   5. the score, `xr-read`, an audit, and the results PR (`phase_scratch_readerr_xp_outcome`).

**Commands refuse:**
- until main holds `phase_scratch_readerr_xr_outcome` with `XH-both`, `XH-extras` or `XH-rest`, and this key;
- `readerr_tools` also refuses unless its own file equals origin/main's.

**The check after the merge:**
- the four units' test commands pass on main;
- `git diff --quiet` over CODE_FILES, less this track's own files, exits 0;
- only `phase_scratch_readerr*` keys changed;
- from a frozen detached worktree, `tx-install` and the gate report before any candidate is read.

**The guard widens.** CODE_FILES gains `learn/readerr_tools.py`. Nothing merges into `scratch_readerr.py` while an
`xr-` command is queued.

**Privacy.** Synthetic part keys and names in tests. The ledger holds hashes, counts and the declared constants only.

### 10j. Manifest v2 (O9, 2026-11-26)

- **The scan.** After `tx-install` and `tx-fetch`, unit D's standard-library `scan_checkpoint` listed every global in
  each fetched checkpoint without loading anything.
  - YourMT3+ has 14 globals: torch's storages and rebuild, `collections.OrderedDict`, `_codecs.encode`, numpy's
    reconstruct, scalar, dtype and ndarray, and five of YourMT3's own `utils.*` classes.
  - Each Riley model has 8: the same set less the scalar and the `utils.*` classes.
  - None is on the denylist.
- **Manifest v2** is U4's manifest plus each checkpoint's `pickle_globals`, exactly as scanned. It is a new file; v1
  is never edited. `readerr_tools.MANIFEST` and `MANIFEST_SHA256` now point to it.
- **The audit:** an independent audit of these globals found them SAFE (2026-11-26).
- **One declared addition, `TORCH_SAFE_TYPES` (`numpy.dtypes.Int64DType`).** With numpy 1.25 or later, rebuilding an
  `'i8'` dtype needs it, so the guarded load would refuse without it.
  - It joins each family's allowlist in `tx_allow_globals`.
  - v2 stays the scan's record exactly.
- **The denylist widens** to Python 2's module names (`commands`, `cPickle`, `__builtin__`, `copy_reg`, `cStringIO`,
  `urllib2`, `httplib`) and the targets of torch's Python 2 renames (`torch._utils.IMPORT_MAPPING` and
  `NAME_MAPPING`). A name is checked both as read and as renamed.
- **The venvs' interpreter (2026-11-26, the orchestrator's technical call).** pyenv's 3.12.13 lacks `_lzma`
  (`librosa` imports `pooch`, which imports `lzma`), and no local Python has it. The shared pyenv builds and Homebrew
  stay untouched, because other venvs and live jobs depend on them. Instead, `tx-python` fetches
  python-build-standalone's CPython 3.12.16 (`install_only`, release `20261124`, MPL-2.0; one asset pinned by URL, size and the sha256 in the
  release's SHA256SUMS). It unpacks it with the data filter under `tools/readerr/python-3.12/` and checks that `lzma`,
  `ssl`, `sqlite3` and `ctypes` import. `tx-install` builds both venvs from it, its version checked to equal 3.12.16.
  Every locked wheel admits 3.12.16.
  - After the unpack, every symlink's real path must stay inside the folder. `tx-install` refuses unless the
    interpreter's record holds the pinned sha256 and version.
  - `tx-move-old` moves the old pyenv-built install aside, never deleting it: the two venvs (venv-b's `.pth` file
    first), their records and lock files, and the two unpacked code folders. It writes a record of what moved where.
- **Provenance: `guitar-gaps`.** The pinned `guitar-gaps.pth` is a 5,000-iteration checkpoint (`iteration: 5000`
  inside), not the paper's 12,200-iteration file. It is the file `hf_midi_transcription` ships, so the test uses it
  as shipped.
