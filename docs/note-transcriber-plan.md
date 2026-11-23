# A better note transcriber (research track 1): the declaration

Declared 2026-11-23, before anything in it runs, from the plan approved after three review rounds on 2026-11-22: an
independent review (approve with changes: R1 to R7 required, a Python text fix and nits) and its diff check (one
required change: `TXR-none` needs a decided negative; nit (a): the model size is decided before any list is
transcribed). Every item is taken. Ledger `note-transcriber`, phases `phase_tx` (this declaration) and `phase_tx_go`
(the user's go). Code `learn/note_tx.py` and `learn/tx_run.py`; tests `tests/test_note_tx.py` and
`tests/test_tx_run.py` (pure, light CI) and `tests/test_note_tx_np.py` (numpy). Outputs under `PF/note-rebuild/tx/`,
each written once and never overwritten.

**Status, 2026-11-23:** declared; nothing has run. The user gave the go (section 12); the weights download is the
user's own step.

**A word on names.** The user's phrase is "note reader". In this repo "reader" already means the knob reader
(`phase_fx_reader_*`), so this track says **transcriber** and uses the prefix `tx`. Every name in section 9 was grepped
against `docs/`, the ledger, `learn/` and `tests/` on main: no hits.

It touches none of the note rebuild's redo's `CODE_FILES` and no `phase_nr*` key, so no running "Measure first"
command refuses. Every figure below is by the score or a note count; nothing here is by ear.

## 1. Goal

The rebuilt dry guitar is only as good as its note list. On our ten made-up lists Basic Pitch finds every note but
adds about 40% extras (precision 0.60, F 0.751).

**That figure is from made-up lists only.** No precision figure on a real DI exists yet. The first one arrives with
"Measure first" step 4 (`truth-report.json`: Basic Pitch against Guitar-TECHS P1 and P2 truth, chords and scales
apart). So the goal is stated in two steps:

- *Now:* find out, at zero renders, whether a second transcriber can give **a note list with clearly fewer extras, no
  loss of real notes that our checks can see, and a note F that is not worse**. The ten lists are screened first.
- *When the truth report lands:* the goal is restated against Basic Pitch's real-DI precision (P1 and P2, chords and
  scales apart, copied from `truth-report.json` into the plan doc). The user then says whether the real-DI stage is
  still worth running. This is a report and a go, not a numeric bar.

> **Basic Pitch's real-DI precision, from `truth-report.json` (filled in the PR that records `phase_tx_lists`,
> before the user is asked for the stage-b go):** P1 —; P2 — (chords and scales apart). Not measured yet.

If no transcriber gives the gain, the track stops and the route stays on Basic Pitch.

It serves the main goal one way only: fewer wrong notes in the rebuilt guitar the preset search renders through. It
converges: a list screen, one read on real DIs, one bridge to the "Measure first" currency, then an amendment or a
stop. Section 7 says plainly what a win can and cannot buy the product.

## 2. What was verified (and what was not)

| Claim in the research report | Checked against | Result |
|---|---|---|
| MuScriptor EGDB onset-and-pitch F1 .789 against Basic Pitch .718; with note ends .635 against .338 | Harmonica, arXiv 2609.04640v1, Table 5 | **Confirmed.** The MuScriptor size is **medium** |
| GOAT with note ends .618 against .372 (onset-and-pitch .710 against .553) | same table | **Confirmed** |
| Tolerances | same paper | Onset 50 ms; note end within max(20% of the note, 50 ms) |
| Precision and recall apart | Harmonica; MuScriptor's paper (arXiv 2607.08168) | **Not reported anywhere.** F1 only. Our fault is precision, so the published figures cannot answer our question |
| "Scores on DI" | Harmonica | **Overstated.** These are DI *sets*; the signal scored is not stated for EGDB, and Harmonica calls GOAT "two thirds … distorted electric guitar" |
| Released checkpoints? | Harmonica | Yes for both, in effect: three baselines are "evaluated using their released checkpoints", Basic Pitch and MuScriptor among them. Basic Pitch's settings there are not ours (58 ms minimum note, 60 to 1,400 Hz) |
| MuScriptor on guitar in its own paper | arXiv 2607.08168 | **No guitar table.** Its training audio is an internal set of 170,000 recordings, sources unnamed. Whether GOAT, Guitar-TECHS, Cambridge-MT or MedleyDB are in it **cannot be known** |
| Open weights, CC BY-NC, gated | Hugging Face API for `MuScriptor/muscriptor-{small,medium,large}` | **Confirmed.** `gated: auto` (access is granted at once), licence tag `cc-by-nc-4.0`. Code MIT |
| Sizes | same | small 411,888,600 bytes; **medium 1,228,144,472 bytes**; large 5,465,642,136 bytes (one `model.safetensors` each; `config.json` is 124, 126 and 125 bytes) |
| Runs on MPS | README; `muscriptor/accelerator.py`; `transcription_model.py` | **Confirmed in code.** MPS is picked automatically and runs in float16. **No speed figure exists anywhere** |
| No velocities, no bends | model card; `tokenizer/notes.py`; open issue #103 "Velocity of all notes at 100" | **Confirmed.** A note is start, end, pitch, instrument group. Nothing else |
| Cannot hold two notes of one pitch at once | model card; the paper | **Confirmed** (per instrument). The paper drops the shorter overlapping note from its own test truth |
| Maturity | GitHub and PyPI APIs | Created 2026-07-02, 2,012 stars, last push 2026-11-15, 48 open issues and pull requests, PyPI 0.4.0 (2026-10-20), "Beta". Widely used but 4.5 months old: **not battle-tested** |

Other facts read from MuScriptor's source that the design depends on:
- Audio is cut into fixed **5-second chunks** at 16 kHz mono; times come on a 10 ms grid.
- Decoding is greedy by default (no sampling), so it should repeat; that is tested, not assumed.
- `transcribe()` says its times may all sit up to about 25 ms late. Our per-window offset step removes a constant
  lag; the lag it measures for MuScriptor is reported per window.
- An `instruments` option masks every instrument but the ones named. The groups include `acoustic_guitar`,
  `clean_electric_guitar` and `distorted_electric_guitar`.
- The loader takes a **local weights path** (with `config.json` beside it), so no token is needed on this machine.
- The released checkpoints had RL post-training, after which the paper says guidance gives no gain: guidance stays 1.0.
- **Python.** `requires-python >=3.10`; the PyPI classifiers list 3.10 to 3.13 and the repo's own `.python-version`
  is 3.13. (The README's "3.10 to 3.12" advice is for Intel Macs only.) This Mac has only 3.9.6 (system) and 3.14.6
  (pyenv), so 3.14 is one minor version past what MuScriptor was tested on. The parts `transcribe()` needs (torch,
  numpy, einops, mido, packaging, safetensors, huggingface_hub, soundfile) all have 3.14 wheels (torch 2.14.0 for
  3.14 is already in `demucs-venv`). The server and beat-tracking parts are not needed. **Whether it imports and runs
  on 3.14 must be measured at the install.** The fallback is Python **3.13** from Homebrew (present on this Mac), one
  named download.

The other candidates:

| Candidate | Open? | Battle-tested? | Velocities or bends | Verdict |
|---|---|---|---|---|
| YourMT3+ (`mimbres/YourMT3`) | Code GPL-3.0. Checkpoints only inside a Hugging Face Space tagged Apache-2.0 | No: 258 stars, last push 2024-11-29, no package, no release | Not stated (MT3-style tokens; none expected) | Not in the test. Its published scores are from a retrain, so the released file's are unknown |
| TART (arXiv 2609.11904) | **No code or weights** on the paper's page | — | Stage 1 gives velocities; a technique head names bends | Not obtainable |
| A two-model vote | — | No published test of one was found | Keeps Basic Pitch's | This plan's test is the first read |

**A named contingency only, no code held for it:** `xavriley/hf_midi_transcription`, should MuScriptor's terms be
declined. Its limits, written beside it so nobody mistakes it for a drop-in:
- The README says MIT, but GitHub detects no licence file, and the PyPI name in the README does not exist.
- 20 stars; it depends on an unpinned git dependency.
- The README says it is "optimized for monophonic performance (single notes, not chords)".
- Its default guitar checkpoint (`guitar-gaps.pth`) is trained on classical nylon-string guitar.
- On chord-heavy clean and crunch DIs it would probably cut chord recall. It does give velocities.
- Using it would need a new go and its own plan.

## 3. How this differs from what failed

| What failed or fell short | Why | This track |
|---|---|---|
| The GOAT-annotation rebuild (failed by ear) | Notes from annotation that covers a median 58% of onsets: missing notes | Notes come from audio; recall is guarded by truth and by the content checks |
| Basic Pitch alone (F 0.751 on the lists) | 172 extras on 259 true notes: 126 harmonic ghosts, 31 re-finds of a ringing pitch, 15 others | A second, unlike model must agree before a note is kept |
| An amplitude floor (the amendment's review, 12m) | No floor separates ghosts from real notes; the best costs chord notes | No amplitude threshold; nothing is fitted |
| The drafted clean-up rule | Best case only just 0.90, and it is fitted to the lists | The vote and the veto have no free number except the 50 ms pairing already used everywhere |
| "Measure first" (approved, not run) | Not failed. It keeps every extra note and plays it quieter | This removes extras instead. The two are compared in one currency (section 6) |

Why agreement might work: Basic Pitch thresholds a frame-by-frame picture, so a strong harmonic shows as a faint
note at +12, +19 or +24. MuScriptor writes notes as tokens from a language model trained on 11,000 hours. The two
make different mistakes, so a ghost only one of them lists is dropped. This is a hypothesis; the test decides.

A reference point, not a ceiling: if a vote removed every harmonic ghost and every "other" on our lists and left the
31 re-finds, precision would be 0.893 and F 0.944 (259 true of 290 kept). The re-finds need not stay, since MuScriptor
has no onset there.

Per the standing rule, nothing starts before the user's go on this difference. The go was given on
2026-11-23 (section 12).

## 4. Design

**The note lists per window**, all after the same clean-up and the same onset steps as today. Pairing between the two
transcribers is done **after** the ±20 ms onset snap, so both lists sit on the same detected attacks.

| Arm | Notes | Loudness and bends |
|---|---|---|
| `tx-bp` | Basic Pitch, as today | its own |
| `tx-ms` | MuScriptor medium, guitar groups only | borrowed from the paired Basic Pitch note; an unpaired note gets the window's median loudness and no bend |
| `tx-vote` | a Basic Pitch note is kept only if MuScriptor has the same pitch within 50 ms (one to one, closest first) | Basic Pitch's own. MuScriptor's note end is carried beside Basic Pitch's |
| beside: `tx-veto` | every paired Basic Pitch note, plus every unpaired one **unless** it sits at +12, +19 or +24 semitones above a paired note in its own onset group | Basic Pitch's own |
| beside: `tx-ms-free` | MuScriptor with no instrument mask, on the lists and GOAT windows only | — |

`tx-veto` is declared now, before any number, and has no free parameter. A vote can only lose notes: any real note
MuScriptor misses is gone. The veto removes only the known ghost shape and keeps everything else, so it shows how
much of the vote's precision gain survives without its recall risk. It is reported with the same figures, carries a
flag (`veto-holds`), and never sets the code.

**Data flow.**

```
window audio (48 kHz, section + up to 1 s either side)
   ├─ 22.05 kHz ─ Basic Pitch (its venv, CPU) ─ note file        [stored: the gate's lists; "Measure first" step 4]
   └─ 16 kHz ─── MuScriptor (its own venv)  ─── note file        [new; declared material only, refused otherwise]
both ─ clean-up ─ window offset ─ onset snap ─ pairing ─ tx-bp / tx-ms / tx-vote / tx-veto
   ├─ against truth (lists; Guitar-TECHS P1, P2): precision, recall, F, note-end F, chord recall
   └─ on GOAT's 27 development windows: the note checks; then tr-di built per arm: the audio checks
```

**Material, all development, none of the 47 row parts, in two stages:**
- *Stage a, the list screen:* the ten known lists (exact truth; each note cut at its note-off). They hold most of the
  known ghosts and need nothing from "Measure first".
- *Stage b, the real-DI read:* Guitar-TECHS P1 and P2 with PR #547's cleaned truth and its consistency test (at most
  238 windows: 76 + 36 on P1, 76 + 36 + 14 on P2, counted from the files; P3 is never read), and GOAT's 27
  development windows (no usable truth: content checks only).

**The input guard.** MuScriptor's terms forbid transcribing music without the rights to it (section 8). So the
runner refuses, in code, any input that is not one of: a known list, a P1 or P2 truth window from the hashed listing,
or one of the 27 GOAT development windows. Any of the 47 row parts, any replay part, any song on disk and any stem is
refused. A later declaration can widen the list only after the user's yes.

**What is read.**
- Per set (lists; P1; P2; chords, scales and techniques apart): precision, recall, F, and **note-end F** (a pair also
  needs its end within max(20% of the true note, 50 ms)).
- Chord-note recall (groups of three or more).
- Recall of a pitch struck again while it still rings (MuScriptor's known weak spot). Only four list notes are of
  this kind, so on the lists this is underpowered; it is reported and never drives a code.
- The extras sorted as the review sorted them: harmonic, re-find, other.
- Bends: on the bend list and on windows with bent notes, per arm, how many bent notes are kept and how much of each
  bent note's span still carries a bend track. (Basic Pitch splits bends; a vote may rightly drop a split piece and
  leave the kept note's bend cut short.)
- Differences against `tx-bp`, paired per window, with 90% cluster t intervals (cluster: the list, or the
  Guitar-TECHS file).
- On the 27 windows: `playing-covered`, `onsets-found` (a report), and on the built guitars `ring-kept`,
  `judge-accepts` (its two clauses that need no stem) and `chords-kept`; windows passing, per arm.

**The declared reading** (coded and tested before any run):
- *Precision raised:* the paired precision difference is clear of zero above.
- *Recall held* ("no loss the checks can see"): overall recall and chord-note recall each at most 0.05 under
  `tx-bp`'s (PR #547's guard size); and, in stage b, on the 27 windows each check passes on at most one window fewer
  than `tx-bp`.
- ***F not decided worse:*** the paired note-F difference against `tx-bp` is not clear of zero below. A vote is a
  subset of Basic Pitch's notes, so its precision rises almost by construction; this line stops a gain that was
  bought with lost notes (precision 0.61 with recall 0.95 is F 0.743, under Basic Pitch's 0.751). It is a direction,
  not a threshold.
- *Ends better:* note-end F clear of zero above `tx-bp` on the lists, and not decided worse on the real DIs (the
  pickup tracker's note-offs are the weaker truth).

*Stage a (the lists alone):*

| Screen result | When | What follows |
|---|---|---|
| `TXR-none` | on the lists, for **both** `tx-vote` and `tx-ms`, the precision difference is **decided not better** (its mean, or its interval's upper end, at or below zero), and ends are not better | **Stop.** Stage b does not run (section 7a) |
| `lists-go` | anything else, an undecided screen included | The result goes to the user with Basic Pitch's real-DI precision; stage b needs the go |

Undecided is not failed. The screen has ten clusters, so a real but modest gain can easily fail to clear zero; that
reads `lists-go`, never `TXR-none`. The stop is a decided negative only: with 172 known extras on the lists, a vote
whose precision does not rise at all is real evidence.

Why the lists can still differ from the real-DI fault: they are bank notes cut at their note-offs, which is not the
kind of audio MuScriptor was trained on, and their extras are of a known kind (harmonic ghosts and re-finds). On real
DIs the extras are unmeasured and may be of another kind (noise, pick and fret sounds, re-finds on real let-ring). So
even after a `TXR-none` stop, the results PR copies in Basic Pitch's P1 and P2 precision once `truth-report.json`
exists, and the user can reopen the track if the real-DI fault looks different.

*Stage b (the first that holds; every condition on the lists and on the real DIs):*

| Code | When | What follows |
|---|---|---|
| `TXR-vote` | `tx-vote` raises precision, holds recall, and its F is not decided worse | The bridge (phase 4), then the questions in section 7 |
| `TXR-ms` | `tx-ms` does, and the vote does not | Same. Basic Pitch stays beside it for loudness and bends |
| `TXR-ends` | neither, but MuScriptor's ends are better | Note ends only: Basic Pitch's notes with MuScriptor's note-off where paired, tested in the bridge |
| `TXR-undecided` | anything else (a gain on one set only; a gain that breaks a guard or lowers F) | Reported with effect sizes. No change to the route. With `veto-holds`, the veto is put to the user as the candidate |

"Ends better" and `veto-holds` are also reported as flags beside `TXR-vote` and `TXR-ms`. `veto-holds` means the veto
raises precision, holds recall and its F is not decided worse, on both sets.

A caution on ends: the lists are cut at their note-offs, which flatters every transcriber's note ends. From the
stored gate events Basic Pitch already has the right end on 216 of its 259 matched list notes, and 19 of its 43
failures are on one list (let-ring). So "ends better" on the lists rests mainly on that list. That is why `TXR-ends`
leads only to the bridge, never straight to a change.

**The product-real case (stems) is not in this declaration.** Checked on disk: the 27 development windows have no
X-LANCE stem (stems exist only for the replay's 122 tested parts). Reading notes from a stem needs new mixes, a
mic'd-amp alignment step and an answer on the Cambridge-MT rights question. It gets its own short declaration once
`phase_tx_read` carries `TXR-vote` or `TXR-ms`; the user may also ask for it on `TXR-undecided`, since MuScriptor was
trained mostly on mixes and its edge may be largest there. Reserved for it: the keys `phase_tx_stems` and
`phase_tx_stem_read`, the code prefix `TXS-`, the seeds 20261411 and 20261412, and the idea of 30 Guitar-TECHS
mic'd-amp windows so precision can be read on a stem against real truth (57 separations at the measured 4.5 s each).

## 5. Phases, and how each is verified

| # | Phase | Renders | Verified by | Waits for |
|---|---|---|---|---|
| 0 | The user's go on section 3, the terms for the declared material, and the download (section 8) | 0 | The go recorded in the ledger (`phase_tx_go`), with no account name, email or token | — |
| 1 | Declaration PR: code, tests, the tables above, docs, ledger `phase_tx` | 0 | Tests pass; an independent review, goal check included | 0; PR #547 merged |
| 2 | Install and gate; once the device and the model size are decided, the ten lists are transcribed with that model | 0 | Hashes match the lock and the weights' sha256; it imports; three runs of four windows give identical notes; seconds per window measured; hash PR `phase_tx_install` (the lock, the weights, the gate file, the device, the list note files' listing) | 1 |
| 3a | The list screen, once | 0 | `tx-bp` reproduces the gate's stored list figures exactly (below); result on main (`phase_tx_lists`) | 2 |
| — | **The user's go on stage b** | 0 | The plan doc's goal restated with Basic Pitch's P1 and P2 precision from `truth-report.json`; the go recorded (`phase_tx_go_read`) | 3a not `TXR-none`; "Measure first" step 4 |
| 3b | Transcribe the real DIs and GOAT windows, then the read, once | 0 | Note files' listing hashed on main (`phase_tx_notes`) **before** any scoring; `tx-bp` reproduces the truth report's per-window matched, ref and est exactly; an independent recompute from the note files; results PR `phase_tx_read` | the go; "Measure first" steps 2 to 4 |
| 4 | The bridge (only on `TXR-vote`, `TXR-ms` or `TXR-ends`) | 0 | One stored `nv-asis` distance reproduced exactly first; `phase_tx_bridge` | 3b; `phase_nr_1_redo_versions` on main |
| 5 | Outside this plan: the stems declaration; the amendment to the redo (each its own declaration and review) | — | — | 4, and the user's answers in sections 7 and 8 |

**Which list figure `tx-bp` must reproduce.** Two paths exist for the lists, and the plan names both:
- the gate's path (the clean-up, then `match_notes`, no offset and no snap) gives the stored 259 matched of 259 true
  and 431 found. The screen recomputes it from the stored events as an input check; it must match per list.
- the deciding list figures go through `timed_notes`, as `versions` reads the lists and as every real window is read
  (the gate's stored events, `pre_s` 0, the list's own audio through `song_bank.measure`).

## 6. How it meets "Measure first", loudness and bends

**Order.** "Measure first" goes first and is not held. Its steps 2 to 4 write three things stage b needs: the truth
listing, the attack detector's offset, and Basic Pitch's note files on every truth and GOAT window. So this track
runs **zero new Basic Pitch transcriptions on DIs**. Phases 0 to 3a run beside it and need nothing from it.

**Why the two do not disturb each other.** This track adds new code files only and touches none of the redo's
`CODE_FILES` (the redo refuses when any of those differs from main's). Its ledger keys live in a separate entry,
`note-transcriber`; the redo's guard compares keys only inside the `note-rebuild` and `preset-ladder` entries. Only
ROADMAP, DOCS-INDEX, NOTICE and the ledger file are touched by both, append-only.

**The deadline.** The redo allows a transcriber change only "by a reviewed amendment, before any of the 47 parts is
transcribed" (12c). So a winner would have to be amended in before "Measure first"'s step 7 transcribes the 47 parts.
If the read is not in by then, the `fs-notes` row runs on Basic Pitch as declared (one build, one read), and a winner
can enter only at the stem-notes row's declaration. Neither waits for the other. Whether a winner may be amended in
at all depends on section 7.

**One currency: the bridge.** "Measure first" asks whether extras cost anything in the rebuilt sound and whether
loudness fixes it. This track asks whether fewer extras can be had. The bridge joins them without rebuilding anything
"Measure first" already built:

- **Built:** only the winner's versions. `bv-asis` is the winner's notes with levels as today. `bv-loud` is the
  winner's notes at the loudness setting "Measure first" adopted (built only if it adopted one). For `TXR-ends`,
  `bv-ends` is Basic Pitch's notes with MuScriptor's note-off where paired.
- **Read against:** the per-window `nv-hand`, `nv-asis` and `nv-loud` distances already stored in `versions.json`.
  Basic Pitch's own hand-cleaned version is the reference, so every real note the winner dropped shows as a cost.
  (Passing the winner's notes through `build_versions` would have built a hand version from the winner's own notes
  and hidden exactly that loss.)
- **First:** the bridge rebuilds one stored `nv-asis` window through its own path and must match the stored distance
  exactly. If it does not, nothing is read.
- **The one deciding difference**, by "Measure first"'s code:

| "Measure first" | This track | The deciding difference | Reading |
|---|---|---|---|
| `NV-loud`, or `NV-undecided` with a loudness adopted | `TXR-vote` or `TXR-ms` | `bv-loud` − `nv-loud` (the winner at that loudness against loudness alone) | The winner adds something only if this is clear of zero below. Otherwise loudness alone stays |
| `NV-short` (loudness is not enough) | `TXR-vote` or `TXR-ms` | `bv-asis` − `nv-hand`, read as "Measure first" reads G against its stored C | "Near" makes the winner the candidate clean-up, in place of a rule fitted on fresh lists |
| `NV-none`, or `NV-undecided` with nothing adopted | any | `bv-asis` − `nv-asis` | Reported only. Extras cost nothing shown, so this is never a reason to change the route |
| any | `TXR-ends` | `bv-ends` − `nv-asis`, with `ring-soft` | Better ends count only if this is clear of zero below |

`bv-asis` − `nv-hand` and the bend figures are reported on every set whatever the code. GOAT's windows have no stored
`nv-hand`, so there the bridge reads against `nv-asis` and `nv-loud` only.

**Do the missing velocities and bends hurt the loudness fix?**
- *The vote and the veto: no.* Every kept note is a Basic Pitch note, so its loudness and bend track are there. The
  loudness fix runs unchanged on fewer notes. Two overlaps to watch. Both act on soft notes (loudness turns them
  down, the vote may drop them if MuScriptor misses them): the recall guard covers it. And a dropped piece of a split
  bend can leave a bend cut short: the bend figures cover it.
- *MuScriptor alone: yes.* It gives no loudness, so the fix has nothing to weigh notes by, and no bend, so a bent
  note is played plain or split in two (the fault the user heard on the old page). That is why `tx-ms` borrows both
  from Basic Pitch, and why **Basic Pitch stays installed in every outcome**. If `TXR-ms` wins and more than 5% of
  its notes have no Basic Pitch partner, any amendment must first add a loudness and bend lookup from Basic Pitch's
  own frame output for those notes.

## 7. What a win buys, and what it cannot

**MuScriptor can almost certainly never ship.** This is the plain reading of its terms, not legal advice:
- The conditions bind "MuScriptor **and its output**".
- Every user must warrant that they hold all the rights in the music they transcribe. Transcribing music without
  those rights is named as a prohibited use. The product's input is the end user's commercial song.
- Each end user would need their own Hugging Face login and acceptance, and would carry the indemnity. Bundling the
  weights would bypass the gate.

**So a win here is a development oracle.** It answers one question: would a cleaner note list help the search? If a
winner were amended into the redo, the `fs-notes` row would become an oracle-style test, run with a transcriber the
product can never use. That is a legitimate test and must be labelled as one. It also needs the user's answer on
running MuScriptor on the row's 47 parts (section 8); without a yes it cannot run there at all.

**The open, shippable route a win would point to** (each needs its own go; named now so the track has somewhere to
land):
1. *An open clean-up rule shaped by the result.* The veto's shape without MuScriptor: a Basic Pitch note at +12, +19
   or +24 over another Basic Pitch note in its onset group is dropped or turned down by a declared rule, fitted on
   fresh made-up lists under its own declaration. This is the same step `NV-short` already calls for. `tx-veto`'s
   figures say how much such a rule could gain at best.
2. *An open transcriber trained on electric DI* (Kong's model by TART's recipe, which reports precision .54 → .83 on
   EGDB), trained on open truth (Guitar-TECHS, EGDB, GOAT's MIDI). Training it on MuScriptor's labels is **not** a
   free development use: the terms bind the output, so that is a further question for the user.

**7a. Stop rules**

1. The user declines MuScriptor's terms: the track stops. (The named contingency needs a new go and a new plan.)
2. The install does not import on 3.14.6 and the user declines the Python 3.13 download; or the notes do not repeat
   on MPS and on the CPU: stop.
3. **`TXR-none` at the list screen: the track stops** before any real DI is transcribed. It needs a decided
   negative for both arms; an undecided screen goes on to the user. The route stays on Basic Pitch with whatever
   "Measure first" decides, and Basic Pitch's P1 and P2 precision is still copied into the results once the truth
   report exists, so the track can be reopened.
4. The user does not give the go for stage b after seeing Basic Pitch's real-DI precision: stop.
5. One read per stage. No setting changes after a number is seen. A second read needs a declared amendment.

## 8. Dependencies and risks

**What the user must do (nobody else can).**
1. Log in at huggingface.co (a free account).
2. Open `https://huggingface.co/MuScriptor/muscriptor-medium`. Fill two fields ("Company or university if
   applicable"; "I am a": Musician, AI Researcher or Other), agree to share the account's name and email with the
   authors, and accept the conditions. Access is granted at once.
3. In the Files tab, download `model.safetensors` (1,228,144,472 bytes) and `config.json` (126 bytes) with the
   browser into `~/ndsp-presets/tools/muscriptor-weights/medium/`. The install checks the sha256
   (`ac80adbd…97ec`). **No token is created, typed or stored**, and the account's name and email never go into git,
   the ledger or the install manifest.

**What the user accepts by doing so** (read from the gate text; this is not legal advice):
- CC BY-NC 4.0: non-commercial use.
- The user "undertake[s] and warrant[s] to have all the necessary rights" in what is transcribed and in how the
  output is used.
- **An indemnity:** the user must "indemnify, defend, and hold harmless Mirelo and Kyutai" for claims arising from a
  breach of the licence or these conditions, lawyers' fees included.

**The rights question, by material.**

| Material | Rights position | In this plan? |
|---|---|---|
| The ten made-up lists | EGFxSet notes, CC BY 4.0; our own arrangement | Yes. Fine |
| Guitar-TECHS P1 and P2 | CC BY 4.0 | Yes. Fine, with attribution |
| GOAT's 27 development windows | CC BY-NC, granted on request | Yes. Non-commercial research. The user should confirm GOAT's own terms allow processing by a third-party model |
| The redo's 24 GOAT parts | same | **No.** The same question, before any amendment |
| The redo's 16 BKS parts and the panel's Cambridge-MT file | Cambridge-MT: download for educational use only; the recordings belong to the artists | **No. The user's call**, before any amendment or stems work |
| The panel's two MedleyDB files | CC BY-NC-SA | **No. The user's call**, likewise |
| Stems with Cambridge-MT backing bleed | as Cambridge-MT | **No.** Asked with the stems declaration |
| Commercial songs on disk; later, users' songs | The user does not hold the rights | **Never.** Under the terms as written this is a prohibited use |

The input guard (section 4) keeps MuScriptor on the first three rows whatever anyone types.

**Other dependencies.** PR #547 merged; its steps 2 to 4 run before stage b. One MPS slot for the gate and the
transcription, if MPS is the device.

**Risks.**
- *Recall.* A vote can only lose notes: its recall is at most the lower of the two. MuScriptor was trained mostly on
  mixes and may drop quiet or fast notes on a bare DI. The guards, the F line, the veto arm and the content checks
  are there for this.
- *A ringing pitch struck again.* MuScriptor must end the first note to start the second. Onset pairing does not
  care unless it drops the second strike. Reported apart; underpowered on the lists.
- *Note ends may not be the gain the paper suggests* on our material (section 4's caution).
- *Truth on real DIs is a pickup tracker's.* Differences between arms are paired on the same truth, which removes
  most of it, not all. The lists and the checks stand beside.
- *Training overlap unknown* for MuScriptor on every set we have.
- *Chunk edges.* Fixed 5-second chunks may cut notes; the window's margins and the pairing tolerance absorb some.
- *Python 3.14 is one version past MuScriptor's tested range.* Measured at the install; the fallback is Python 3.13.
- *Repeatability on MPS in float16* is not promised by anyone. The gate tests it; the CPU in float32 is the fallback.
- *Young package* (0.4.0, beta): pinned by hash, run in its own venv, offline.
- *A later amendment disturbs running redo commands.* It would change `note_transcribe.py`, one of the redo's
  `CODE_FILES`, so every running redo command refuses until its checkout pulls. It must be scheduled between redo
  steps.

## 9. Costs (measured rates only) and names

| Item | Count | Rate | Source |
|---|---|---|---|
| Plugin renders, training, separations | 0 | — | — |
| Basic Pitch on DIs | 0 new | — | the gate's stored list events; "Measure first" step 4's note files |
| Basic Pitch round trips (`chords-kept`) | 108 (4 arms × 27 windows) | 1.24 s per 10-s window | measured, the gate's rerun |
| Dry-guitar builds for the audio checks | 216 (4 arms × 27 windows × 2 ring variants) | 0.14 to 0.48 s each | measured by the amendment plan's review (12m) |
| Bridge builds | about 1,100 (at most 275 windows × 2 versions × 2 ring variants) | same | same |
| MuScriptor, the gate | 4 windows × 3 runs per device | **not measured** | measured there, on MPS and on the CPU |
| MuScriptor, stage a | 10 lists, and 10 more for `tx-ms-free` | **not measured** | same |
| MuScriptor, stage b | at most 265 windows (at most 238 + 27), and 27 more for `tx-ms-free`; each up to 12.25 s, so 3 chunks | **not measured** | same |
| Downloads | wheel 1,850,618 bytes; weights 1,228,144,472 bytes; torch and seven small wheels | venv size **not measured** (`demucs-venv`, also torch 2.14, is 1.2 GB) | PyPI and Hugging Face APIs |
| Disk | 53 GB free against the 31 GB guard | — | `df`, 2026-11-22 |

**To measure first, in this order:** (1) does the minimal install resolve and import on 3.14.6; (2) seconds per
window, medium, MPS and CPU; (3) do the notes repeat on each. The gate prints the projected time for stage b's 265
windows. Over 2 hours on the faster repeatable device switches every MuScriptor arm, `tx-ms-free` included, to the
small model (411,888,600 bytes). **The size is decided before any list is transcribed:** on a switch the gate stops
with no list notes written, the user accepts and downloads the small model (its own gated page), the gate's repeat
and speed tests run again on it, and only then are the lists transcribed. So the hash PR never carries notes from a
model that was dropped, and no accuracy number exists when the size is chosen.

**Names** (grepped on main and on PR #547: unused):
- Ledger entry `note-transcriber`; keys `phase_tx`, `phase_tx_go`, `phase_tx_install`, `phase_tx_lists`,
  `phase_tx_go_read`, `phase_tx_notes`, `phase_tx_read`, `phase_tx_bridge`. Reserved for the stems declaration:
  `phase_tx_stems`, `phase_tx_stem_read`.
- Arms `tx-bp`, `tx-ms`, `tx-vote`, `tx-veto`, `tx-ms-free`. Bridge versions `bv-asis`, `bv-loud`, `bv-ends`.
- Codes `TXR-vote`, `TXR-ms`, `TXR-ends`, `TXR-none`, `TXR-undecided`; the screen's `lists-go`; the flag
  `veto-holds`. The codes carry `TXR` so that no code differs from an arm only by case. Reserved: `TXS-`.
- Files `learn/note_tx.py`, `learn/tx_run.py`, `tests/test_note_tx.py`, `tests/test_tx_run.py`,
  `tests/test_note_tx_np.py`, `docs/note-transcriber-plan.md`. Folders `~/ndsp-presets/tools/muscriptor-venv`,
  `~/ndsp-presets/tools/muscriptor-weights`, `PF/note-rebuild/tx/`.
- Seeds 20261411 and 20261412 are reserved for the stems declaration; the implementer greps them again then.

## 10. Done test

The plan is finished when one of these holds:
- **(a)** `phase_tx_lists` is on main with `TXR-none` and, once the truth report exists, Basic Pitch's P1 and P2
  precision beside it; or the user has declined stage b, recorded with that precision beside it.
- **(b)** `phase_tx_read` is on main with one of the four stage-b codes, from a read run once, on note files hashed
  before scoring, recomputed by an independent audit; and, on `TXR-vote`, `TXR-ms` or `TXR-ends`, `phase_tx_bridge`
  is on main with its deciding difference.

And in either case:
1. `tx-bp`'s figures equal the stored ones exactly: the gate's list figures at the screen, the truth report's
   per-window figures at the read.
2. The results doc states the code, the effect sizes, the recommendation (the stop, the open route of section 7, or
   the questions for an amendment), and what it cannot say.
3. Zero plugin renders, no training, every download in a manifest with its sha256, no token on the machine, and no
   input outside the declared material (the guard's refusals are tested).

**What it will not be able to say:** anything by ear; how the plugin reacts to an extra note; anything from a stem,
on full mixes or with a second guitar; whether MuScriptor saw our material in training; anything about the 47 row
parts; anything about a transcriber the product could ship.

## 11. Filled in at declaration

**The frozen settings**, each a constant in `learn/note_tx.py` or `learn/tx_run.py` held by a test:

| Setting | Value |
|---|---|
| Package | `muscriptor` 0.4.0, wheel 1,850,618 bytes, sha256 `a7e941b6e1d85a25f9fc4e00c2a46b43d4d516de0e751d54b42fda438ac2abb9`, installed `--no-deps` |
| Weights | `MuScriptor/muscriptor-medium` at revision `f32236969308476e01fd3aae67357de5feb05a2d`: `model.safetensors`, 1,228,144,472 bytes, sha256 `ac80adbdf85d87231735fd948af7013441c0afced316c4e9067fd5d8a7fb97ec`; `config.json` (126 bytes) beside it, its sha256 recorded at install |
| Fallback weights (speed trigger only) | `muscriptor-small` at `8c127f603b807520fa465c838e9bfee8a91ada4e`: 411,888,600 bytes, sha256 `bbd482c786b895cf7d8f44185073d951adae2ebb8a66f82ca84cd1f84569549c`; `config.json` 124 bytes |
| Venv | `~/ndsp-presets/tools/muscriptor-venv` from `~/.pyenv/versions/3.14.6/bin/python` (fallback, on the user's yes: Homebrew's `python@3.13`); lock made by `pip install --dry-run --ignore-installed --only-binary :all: --report` over `torch>=2.3`, `numpy>=2`, `einops>=0.4`, `mido>=1.3`, `packaging>=20.0`, `safetensors>=0.4`, `huggingface_hub>=0.13`, `soundfile>=0.14.0`; installed `--require-hashes --only-binary :all: --no-deps`; refuses under 36 GB free |
| Input | the window audio Basic Pitch gets (`note_transcribe.window_audio`: the section with up to 1.0 s either side; for a list, `known_audio`), mono, 48 kHz to 16 kHz by `resample_poly(x, 1, 3)`, peak at −1 dBFS, float32 WAV |
| Declared material | `list:<name>` (a key of `KNOWN_NOTES`); `truth:<window key>` (in the hashed listing, P1 or P2, `note_truth.refuse_path` passes); `goat-dev:<item>` (one of `dev_windows`' 27, clear of the exclusion list). Nothing else |
| Call | `TranscriptionModel.load_model(<local path>, device=<the gate's>, dtype=None)`; `transcribe(path, use_sampling=False, cfg_coef=1.0, instruments=["acoustic_guitar", "clean_electric_guitar", "distorted_electric_guitar"], batch_size=1, beam_size=1, prelude_forcing=True)`. `tx-ms-free`: `instruments=None`, drums dropped |
| Process | the venv's interpreter with `-I`; `HF_HUB_OFFLINE=1`; 4 torch threads; nothing may reach the network |
| Kept | every pitched note: start, end, MIDI pitch, instrument group; times to 0.1 ms; a note with no end event ends at the input's end (counted) |
| Clean-up and timing | `note_transcribe.clean_transcribed`, then the same steps as `timed_notes` (shift by `pre_s`, in the window, `coarse_offset`, the ±20 ms snap), unchanged; MuScriptor's `coarse_offset` recorded per window |
| Pairing | after the snap: same MIDI pitch, onsets within 50 ms, one to one, closest first (the rule of `match_notes`) |
| Veto | an unpaired Basic Pitch note is dropped only if a paired note in its onset group (`note_transcribe.groups_of`) sits exactly 12, 19 or 24 semitones below it |
| Device rule | MPS (float16) if its three runs repeat; else the CPU (float32); all note files from one device, named in each |

The plan left the details below open. Each is now in code and held by a test.

**The input guard.** `note_tx.declared_input` is the only way an input manifest row is made. It accepts only:
- `list:<name>`, a key of `note_transcribe.KNOWN_NOTES`;
- `truth:<window key>`, a P1 or P2 window of the hashed listing whose DI and MIDI paths pass
  `note_truth.refuse_path`;
- `goat-dev:<item>`, one of the 27 development windows (`note_transcribe.dev_windows`, clear of the exclusion list).

Everything else is refused. `run_ms` checks every source before it writes a file. It then writes the manifest (each
input's sha256 and source) beside the inputs. `tx_run` refuses a manifest that names any other kind of source, and any
input whose sha256 is not in it, before the model loads. The tests cover a row part, a replay part, a stem, a song, a
P3 window, a path outside the P1 and P2 folders, a GOAT item outside the 27, and a bare path.

**The runner.** `tx_run` reads MuScriptor's events (`NoteStartEvent`: pitch, start time, index, instrument;
`NoteEndEvent`: its start event and end time) and pairs them by the start's index. A start with no end ends at the
input's end and is counted. An end with no start is counted and dropped. Drums are dropped and counted. An end before
its start is held at the start. It also sets `TRANSFORMERS_OFFLINE=1` beside `HF_HUB_OFFLINE=1`. It refuses settings
other than the two declared ones (key set and values).

**The extras' sort.** Each unpaired note is sorted against the true notes sounding at its onset (from 50 ms before
their onset to their note-off):
- "harmonic": 12, 19 or 24 semitones above one of them;
- else "re-find": its pitch;
- else "other".

On the gate's stored list events this gives exactly the plan's 126, 31 and 15 (a test, skipped off this machine).

**Note-end F.** The end condition is part of the pairing: a pair needs both its onset and its end. On the stored
events Basic Pitch has 216 of 259 ends right, 19 of the 43 misses on `let-ring-arpeggio`, as the review recomputed.

**Which notes and ends each arm is read with.**
- `tx-vote` and `tx-veto` are read with Basic Pitch's own note-offs. `tx-vote` carries MuScriptor's beside, for
  `bv-ends`.
- "Ends better", and so `TXR-ends`, reads `tx-ms`'s own note-end F against `tx-bp`'s.
- The pitch struck again while it rings: 4 list notes, a report only.

**The sets.**
- The deciding sets are the lists (10 clusters) and the real DIs: P1 and P2 together, one cluster per Guitar-TECHS
  file.
- P1, P2 and each player's kinds are reported apart. They decide nothing.
- Recall held reads pooled recall and pooled chord-note recall over the set's windows.
- In stage b the 27 windows' guard covers `playing-covered`, `judge-accepts`, `ring-kept` and `chords-kept` on
  `ring-soft`. `onsets-found` is a report and is not guarded.
- `tx-ms-free` gets the note checks only (it is not built).

**The builds on the 27 windows.** `tr-di` is built by `note_rebuild.rebuild_redo` with levels as today (no loudness
weighting; the bridge carries loudness). It is finished by `song_bank.measure`, as `calibrate` finishes its
development windows. Basic Pitch's round trip (for `chords-kept`) runs on the deciding ring only, so 108 round trips
as costed.

**Borrowed loudness.** An unpaired `tx-ms` note gets the median of the window's Basic Pitch amplitudes. With no Basic
Pitch note in the window it gets none, so `note_weights` counts it as 1.

**The bend figures.** The reference bent notes are the truth's where the truth has bends (the bend list). Elsewhere
they are Basic Pitch's own bent notes, by `bend_curve`. Per arm the figures are:
- how many of the reference notes the arm keeps (pairs);
- the mean share of each one's span still carrying a bend track in the kept note (0 where dropped).

**The gate.**
- Seconds per window come from the one-process run (each window twice, model load included), as Basic Pitch's gate
  counts them.
- The device is MPS if its three runs repeat on all four windows, else the CPU. The projection is read on the faster
  repeatable device, as written, even when the device rule picks MPS.
- A switch to small writes `gate-medium.json` with no list notes and stops. `gate --size small` refuses unless that
  file called for small. It checks the small weights against their declared size and sha256, then repeats the repeat
  and speed tests. On small the lists are transcribed whatever its projection, since no smaller model is declared.

**The install.**
- The 3.13 fallback is `install --interpreter <Homebrew's python3.13>`. Only Python 3.14 or 3.13 is accepted. As with
  the redo's 3.11 fallback, the user's yes is a step in the order, not a check in code.
- The venv's bundled pip is used; it supports `--report`, and the redo's pinned pip upgrade was for 3.9's old pip.
- The lock must hold the muscriptor pin and every requirement. It must hold nothing from the server or the beat
  tracker (`beat-this`, `fastapi`, `typer`, `uvicorn`), and every line must be hashed.
- The install record refuses any key naming an account, an email or a token. Its approval is
  `{"date": "2026-11-23", "ledger": "note-transcriber phase_tx_go"}`.

**The later keys' records.**

| Key | What it holds |
|---|---|
| `phase_tx_install` | `lock_sha256`, `weights_sha256`, `gate_sha256`, `size`, `device`, `list_notes_listing_sha256` |
| `phase_tx_lists` | `sha256` (`tx/lists.json`), `screen` |
| `phase_tx_go_read` | the user's go, with Basic Pitch's P1 and P2 precision beside it |
| `phase_tx_notes` | `listing_sha256` |
| `phase_tx_read` | `sha256` (`tx/read.json`), `code`, `flags` |
| `phase_tx_bridge` | `sha256` (`tx/bridge.json`), `difference`, `readings` |

`bridge` also needs main's `phase_nr_1_redo_versions` to name `versions.json`'s sha256.

**The bridge's readings.**
- They are given per set (lists, real, GOAT) and are not pooled across sets.
- Every built version less every stored version is reported on both rings. So `bv-asis − nv-hand` is reported
  whatever the code (GOAT has no `nv-hand`).
- The one stored distance rebuilt first is `bend`'s `nv-asis` on `ring-soft` (the first list by name). A test shows
  the bridge's path gives the same distance as `note_versions.build_versions` on a made-up window.

**What the stored data already confirm (no new run).** These come from Basic Pitch's stored list events:
- 259 matched of 259 true notes, 431 found;
- the extras sorted 126, 31 and 15;
- 216 of 259 ends right;
- 4 re-struck list notes.

**NOTICE.md** credits MuScriptor: code MIT, weights CC BY-NC 4.0, Kyutai and Mirelo; a development tool, never
shipped.

## 12. The user's go (2026-11-23; ledger `phase_tx_go`)

Asked by AskUserQuestion; the answer was **"Go, I'll get access"**. The question's key terms:
- the gated terms;
- the rights warranty and indemnity;
- CC BY-NC;
- "a development yardstick only".

**What the user does next.** The user accepts MuScriptor's terms and downloads `model.safetensors` and `config.json`
by browser into `~/ndsp-presets/tools/muscriptor-weights/medium/`. No token is created, typed or stored.

**What is transcribed.** Only the declared material: the ten lists, the Guitar-TECHS P1 and P2 truth windows and the
27 GOAT development windows. The Cambridge-MT and MedleyDB songs wait for a separate yes. Commercial songs never.

**Privacy.** The account's name and email never go into git, the ledger or the install manifest.
