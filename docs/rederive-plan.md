# The rebuild's re-derivation on the exact bench, then real songs

Declared 2026-11-25, before anything in it runs. Ledger `preset-ladder` `phase_scratch_rederive`; code
`learn/scratch_rederive.py` (the core, the ladder and both outcome tables), tests `tests/test_scratch_rederive.py`.
The plan (Fable, high; plan v2 after an independent review with 11 amendments) passed an independent re-review (Opus,
high): PASS WITH AMENDMENTS. The re-review's five amendments are binding and are built in below; where they differ from
the plan's text, they win. This is the user's Go 4 of the exact-notes test (2026-11-25): improve the rebuild on the
exact bench. Results will go in `docs/rederive-results.md`.

## 1. Goal

The exact-notes test read **XN-both** ([results](scratch-search-results.md#the-exact-notes-test-rows-xn-bank-xn-swap-xn-reread-xn-list-xn-both)).
One of its costs is D_list = G(`xn-list`) − G(`xn-bank`), +0.321 [+0.180, +0.462] on the 40: the rebuild from the bank
guitar's own exact note list, with the bank guitar X handed to the rebuild as its DI, searches worse than X itself.

The goal is a re-derivation that returns X's own values when it is handed a bank guitar in the form real songs present,
so that its cost is no longer shown on the 40. Then a real-song row measures whether the same rule moves build 2's row
toward row (b) (row (b) is at −0.264, build 2 at +0.009, on the 40).

**Scope.**
- The bridge row still takes the four values and the onset snap from the true DI. `RF-closer` does not license the
  song-only path.
- The later step, not in this plan, hands the rule what a song gives. On the bench that is the part's record (X through
  the target preset) on the search half, priced by the same rows; on real songs the `xlnoG` stem, as the already-named
  stem-notes row.
- **Coverage gap.** Neither the bench nor the bridge searches time effects, spring or doubler
  ([scratch-search-plan.md](scratch-search-plan.md) line 102), and step 2 runs only C1b's stages A and B. Nothing here
  says the rebuild serves those controls.

## 2. What is re-derived

`note_rebuild.rebuild_redo` (`tr-di`) re-derives four values from the DI it is handed, in this order (`ELEMENTS`):

1. the global tuning (`global_tuning_cents`);
2. the mute times (`mute_times`);
3. the one sustain tilt (`sustain_tilt`, against a plain synthesis with no tilt and no levels);
4. the per-onset-group levels (`oracle_gains`, against the plain synthesis with the tilt).

Onsets, note lengths, bends and strings come from the exact note list unchanged. The finish (`song_bank.measure`, then
`average_balance` with the part's others) and −22.9 LUFS are functions of the synthesised audio.

The code splits `rebuild_redo` in two without changing it. `derive` returns the four values in `rebuild_redo`'s own
order. `compose` is `rebuild_redo`'s tail: the synthesis with given values, the hiss removal, the finish and the
loudness. Both call only `note_rebuild`'s existing functions. With nothing given, `compose(derive(·))` is
`rebuild_redo` byte for byte (tested on a made-up bank with the loudness option off and on).

T is the four values from the true DI; R is today's rule's values from the input it is handed.

## 3. The input forms

On the bench, `xn-list` was rebuilt from the finished X (`scratch_exact.py:829` passes the bank guitar as the DI). On
real songs `note_transcribe.build_todo` hands the rule `note_replay.di_section`, which is the DI after
`song_bank.measure` only (the re-review, section 2, with the code lines). So the ladder builds three forms of X from T:

| Input | How it is built | Role |
|---|---|---|
| `in-F` | `compose(T)` with the part's finish, as float32 (the bank guitar X itself) | beside: what `xn-list` saw |
| `in-M` | `song_bank.measure(denoise_above(synthesise_redo(T))[:n])` (amendment 4), rounded to float32 | **decides**: the form real songs hand over |
| `in-U` | `denoise_above(synthesise_redo(T))[:n]`, scaled to the true DI's RMS | beside: fully unfinished |

`synthesise_redo(T)` runs on the padded length, as in `rebuild_redo`. The probe figures match only with the hiss
removal (`denoise_above`) inside `in-M`. `in-M` is amendment 4's formula with `di_section`'s own float32
rounding applied (`note_replay.di_section` returns the measured DI as float32), so it matches the real DI's form down
to the sample type. The probe figures in `in-M` (section 12) were computed in float64 and stay labelled seen. The pick
and both decisive rows run in `in-M`.

## 4. The ladder (zero renders; `python -m learn.scratch_rederive ladder`)

Per part (the 47) and per input form:

- T and R;
- the 16 **value cells**: each element T's or R's (`VALUE_CELLS`, `RRRR` today's rule to `TTTT` all true);
- the 4 **chain cells**: one element set true, the others re-derived from the input, the later ones after it
  (`CHAIN_CELLS`). This is what a perfect fix of that element alone would give. The chain cell of an element is the
  guitar of its rung row (`xf-tuning`, `xf-mutes`, `xf-tilt`, `xf-levels`);
- the `xf-now` guitar: today's rule handed `in-M` (the value cell `RRRR` in `in-M`).

Three proofs, each on 47 of 47 parts, before a part writes anything:

1. `in-F` is X byte for byte (the four values from the true DI rebuild X);
2. today's rule handed `in-F` is `xn-list` byte for byte;
3. `xf-now` is `rebuild_redo`'s own output on `in-M` byte for byte.

The ladder stores only the guitars to be rendered: the `in-M` guitars of `xf-now` and of the four rung rows, under
`PF/fs/rederive/dry/<row>/`, each file written once. Every other cell is reported (sha256, byte-identical to X and to
`xf-now`, `logmel_distance` and envelope correlation to X) and not stored. A part's record goes under
`PF/fs/rederive/ladder/`; `ladder.json` (with the average guitar file's sha256, `confirm_run.AVERAGE`, which the
measure step reads) is written once, only when every part's proofs hold. Beside, per input form on
the 40 and all 47: today's rule's distance to X; its errors against T (tuning and tilt, absolute; each group's level;
mutes found within 30 ms, `MUTE_FADE_S`, counted extra and missed); per chain cell the parts whose `in-M` guitar
differs from `xf-now`'s, which is the number of parts each rung row must search.

The mute match is many-to-one, not a pairing: a re-derived mute is extra when no true mute lies within 30 ms of it,
a true mute is missed when no re-derived mute lies within 30 ms of it, and one mute may count as found for several
of the other list's (so true less missed need not equal re-derived less extra).

## 5. The diagnosis (zero renders; Unit 2, `learn/rederive_diag.py`)

- `xn-list` and `xf-now` against X, per part and per note, traced through a recording `Bank` proxy and a wrapped
  `note_end`, with no guarded code changed; the traced audio must be byte-identical.
- Per control group, how far each row's answer sits from the target. Only group names and aggregates leave `PF`.
- Spearman with D_list, descriptive.

## 6. The fit's rules (declared before it runs; Unit 3, `learn/rederive_fit.py`)

The constants are in `scratch_rederive.FIT`.

- **Principle.** Choose the four values so that the rebuild, measured by the same estimator in a stated domain, matches
  the input.
- **Candidates: 12, plus today's rule.** The comparison domain is the rebuild unfinished, after `song_bank.measure`, or
  finished. Passes are one correction, or iterated. Mutes are as now, or the veto.
- **The mute veto.** In time order, a detected drop is kept only if the rebuild has no mute of its own within 30 ms
  (`MUTE_FADE_S`).
- **Update.** Each pass adds the measured difference. Tuning and tilt use a secant step from the second pass on (the
  plain step closed item_69's tilt error by only about 10% a pass in the planner's probe).
- **"Repeats".** Against the previous pass, all four hold:
  - tuning moved under 0.05 cents, half of `Bank.note`'s 0.1-cent rounding;
  - the mute list is identical;
  - every level moved under 0.01 dB, `at_lufs`'s own tolerance;
  - tilt moved under 0.027 dB/s, which is 0.01 dB over the estimator's 0.375-s span.
- **Cycles.** A pass that matches any earlier pass other than its predecessor stops the fit. "Matches" means within the
  repeat tolerances (amendment 5). The pass used is the cycle's member with the lowest residual; a tie takes the
  earliest.
- **Safety stop.**
  - Price it first (amendment 2): time the passes on 2 or 3 parts and report the projected wall before the full run.
    The full run is one niced process.
  - `converge` runs every iterated candidate on the 47 bench parts in `in-M`, up to 64 passes (the measurement's own
    bound).
  - The stop is the largest pass count among fits that repeated. Every fit that reaches it is listed; its pass used is
    the lowest-residual pass at or before the stop.
  - The stop set on the bench in `in-M` also applies to `build-real`, and the real-song fits that reach it are listed
    too (amendment 5).
  - The number and both lists go into the ledger with `freeze`.
- **Deciding measure.** `note_rebuild.logmel_distance` from the candidate's finished guitar to X, in `in-M`, on the 40.
- **Tie interval.** Per-part paired differences from the lowest-mean candidate, through `scratch_notes.set_rows`'
  BKS+GOAT pool. An interval that spans zero is a tie.
- **"Simpler", a total order.** Today's rule first. Then fewer passes. Then the domain: unfinished, measured, finished.
  Then mutes as now before the veto.
- **Beside.** The four values' errors against T, the byte-identical counts on all 47, and the picked rule and today's
  rule in `in-U` and `in-F`.

## 7. The rows (Unit 4, `learn/rederive_rows.py`)

| Row | Dry guitar of the search | When |
|---|---|---|
| `xf-now` | today's rule handed `in-M` | first (stage 1) |
| `xf-fix` | the frozen rule handed `in-M` | only if stage 1 goes on (stage 2) |
| `xf-tuning`, `xf-mutes`, `xf-tilt`, `xf-levels` | the chain cells in `in-M` | only if the code asks; changed parts only |
| `xf-null` | X with a negligible change | only if the code asks (guitars near X) |
| `fs-refit` | `rf2`: build 2's notes, the frozen rule, the true DI | the bridge, on `XF-closed` or `XF-part` |

Bench rows use `scratch_exact`'s pattern: `scratch_search.search_row_part` unchanged, the exact-notes test's records,
start reference and score, lag 0. The real row uses `scratch_notes`' shared steps unchanged, with its own keys. A
guitar byte-identical to a searched one takes that record byte for byte. The score check and the search check rerun
before the first bench row and must reproduce row (c) exactly. Answers are hashed on main before any score.

## 8. The outcome tables (coded and tested before any run; the answer arm, on the 40, first that holds)

**Bench**, read in two stages (amendment 1). D_now = G(`xf-now`) − G(`xn-bank`). D_fix = G(`xf-fix`) − G(`xn-bank`).
The gain is D_fix − D_now, paired per part. D_list − D_now goes beside as the finished input's share.

| Stage | Code | When | Meaning | Next |
|---|---|---|---|---|
| 1 | `XF-anomaly` | D_now wholly below zero | A re-derived guitar beats X itself | Audit before anything is said |
| 1 | `XF-input` | D_now spans zero | In the real-song input form, today's rule's cost is not shown; D_now's hi90 is reported as the cost it rules out | `xf-fix` does not run. To the user; the bridge is the user's call |
| 1 | (go on) | D_now wholly above zero | Today's cost is shown | `xf-fix` runs |
| 2 | `XF-anomaly` | D_fix wholly below zero | A re-derived guitar beats X itself | Audit before anything is said |
| 2 | `XF-worse` | Gain wholly above zero | The rule costs more than today's | Not kept; audit; rung rows, tilt and mutes first |
| 2 | `XF-closed` | Gain wholly below zero, D_fix spans zero | The cost is no longer shown | The bridge runs |
| 2 | `XF-part` | Gain wholly below zero, D_fix wholly above zero | It helps; a residual is shown | The bridge runs. The residual is priced by the rungs the fit recovered worst, and by the null row if the guitars are near X |
| 2 | `XF-undecided` | Gain spans zero | Not decided; undecided is not failed | Rung rows, cheapest first; the bridge is the user's call |
| 1, 2 | `XF-other` | Anything else | No reading | To the user with the numbers; nothing runs on |

Paired half-widths here are about ±0.13, so an undecided stage-1 read is likely and is not a failure.

**Real songs.** D_real = G(`fs-refit`) − G(build 2), paired per part.

| Code | When | Meaning | Next |
|---|---|---|---|
| `RF-anomaly` | G(`fs-refit`) − G(row (b)) wholly below zero | The rebuilt guitar beats the true DI | Audit before anything is said |
| `RF-closer` | D_real wholly below zero | The rule moves real songs, with the DI still supplying every input | To the user: adoption, an ear page, then the later step in Scope. Not a licence for the song-only path |
| `RF-worse` | D_real wholly above zero | The bench does not carry | Not adopted; audit |
| `RF-undecided` | D_real spans zero | Not decided; labelled "level, not readable by the score" inside ±0.05 | To the user with what the interval rules out |
| `RF-other` | Anything else | No reading | To the user |

`xf_stage1`, `xf_stage2`, `xf_read` and `rf_code` code these; a test runs every combination of intervals (below,
spanning, above, an end at zero, and every malformed form) and each ends in exactly one code.

## 9. Reads

- Intervals from `scratch_notes.set_rows` on BKS+GOAT; all 47 beside. Labels only from `paired_reading` and
  `number_reading`; numbers are by the score.
- S1: a technical refusal reruns once, then reads at Cen; the passing-only read goes beside, `refusal-sensitive` when
  the two codes differ.
- Declared splits: the 40 (deciding); clean 20 and crunch 20; all 47 and the panel; the shrunk arm; checkpoints 50, 100,
  200; each cluster left out; one part per partner (33 parts); without the two design-time parts (the refused sw50r part
  and GOAT item_69); the 15 tilt parts against the 25, labelled seen.
- The bridge also reads against rows (b) and (c).
- The real floor (row (b)'s answer through the `rf2` guitar) goes beside only and gates nothing.

## 10. Phases, each verified before the next

| Phase | Work | Renders | Verify before going on |
|---|---|---|---|
| 0 | This declaration: plan doc, `phase_scratch_rederive`, core, tables, tests | 0 | Independent review; the per-PR guard check |
| 1 | `ladder`, `diagnose` | 0 | The three proofs 47 of 47; D_list and passing-only (+0.285 [+0.173, +0.396]) reproduced; audit; `phase_scratch_rederive_ladder` holds the ladder's, the diagnosis' and `xf-now`'s sha256 |
| 2 | `converge` (priced on 2 or 3 parts first), `bench`, `freeze`, `build-bench`, `build-real` | 0 | Rule off equals `rebuild_redo` byte for byte; reruns identical; `phase_scratch_rederive_frozen` holds the rule, the stop and both builds' sha256, after review |
| 3a | The score check and the search check | 62 | Both reproduce row (c) exactly |
| 3b | `xf-now`: search, answers hash, score, stage-1 read | about 13,200 | Answers hashed before the score; audit; if `XF-input`, stop and go to the user |
| 3c | Floors beside (the 4 chain cells and `xf-fix`), then `xf-fix`: search, answers hash, score, stage-2 read | 474, then about 13,200 | The stored `xn-list` floor repeats on 2 parts; audit; `phase_scratch_rederive_bench_outcome` |
| 3d | Rung rows or the null row, only if the code asks | below | As 3c |
| 4 | The bridge `fs-refit`: checks, real floor (beside), search, answers hash, score, read, control-group comparison | 62 + 94 + about 12,435 + 940 | Checks exact; audit; `phase_scratch_rederive_outcome`; to the user |
| 5 | Adoption into `rebuild_redo` | 0 | The user's go |

**Sizes (measured rates).**
- One exact row: about 6,360 s of search plus about 7.5 min of score, about 1.9 h.
- Rung rows search only changed parts, about 135 s a part on 3 processes. From the finished-input probe: tilt 13 parts,
  mutes 41, levels 47, tuning 47; `ladder` recounts them in `in-M`.
- Bridge: build 2's real search took 12,341 renders in 6,532 s. Its score ran on 2 shards, 480 and 460 renders in
  1,074 s and 1,045 s (amendment 3).
- Whole path: about 40,500 renders, about 6 h. If `xf-now` reads `XF-input`: about 13,300 renders, about 1.9 h.

## 11. Guards, data and privacy

- Every command refuses unless this checkout runs main's code (this module, `scratch_exact.py` and its six pinned
  files, `note_transcribe.CODE_FILES`, `song_bank.py`, `di_robustness.py`, `direc_check.py`, `confirm_run.py`) and
  keys (`phase_scratch_rederive*` and `phase_scratch_exact*`; `scratch_search.on_main`; `note_transcribe.redo_on_main`),
  and main holds the draw, build 2's hash (`phase_scratch_notes_dry_b2`), the exact-notes declaration and Phase A's hashes (`phase_scratch_exact_targets`)
  and this declaration.
- The per-PR check, against each PR's own base: with `BASE=$(git merge-base origin/main HEAD)`, `git diff --quiet $BASE
  HEAD --` over `note_transcribe.CODE_FILES`, `learn/scratch_exact.py`, `learn/scratch_search.py`,
  `learn/scratch_notes.py` and `learn/note_rebuild.py` exits 0, and the guarded keys (`note_transcribe.guarded_keys` on
  both ledger entries) and the `phase_scratch_exact*` keys are equal at `$BASE` and `HEAD`. Build 3's hash PRs merge
  first. After a merge, from a fresh detached worktree of main, `NT.redo_on_main()[1]` is `None` and the full suite
  passes.
- The prefix `phase_scratch_rederive` sits outside every guarded prefix (`phase_fs`, `phase_scratch_notes`,
  `phase_scratch_exact`, `phase_scratch_readerr`, `phase_nr`).
- Adoption (Phase 5) is the only guarded change, and it is not in these runs. Its price for build 3: zero renders,
  builds 1, 2, 3 and b3k rebuilt byte for byte, and re-cut worktrees. It waits for build 3's read.
- Data lives under `PF/fs/rederive/`, each file written once. Git holds no part keys, song or file names, paths, audio
  or settings; the ledger holds hashes and counts. Tests use synthetic keys.
- Render commands: at most 3 shards, the 31 GB disk guard before each part, `caffeinate -i`, `no_bg_nice`, from a
  frozen worktree of merged main. Zero-render jobs run one at a time, niced, beside a search.

## 12. Seen before the declaration

Every figure below came from exploratory zero-render probes (the planner's, the first review's and the re-review's)
or from stored results, before this declaration. They are labelled seen wherever they are reported.

- **Identity.** On 47 of 47 parts, T from the true DI rebuilds X byte for byte, and the values from X rebuild `xn-list`
  byte for byte; the first review confirmed it through `rebuild_redo` itself.
- **D_list and its splits** (stored score files): +0.321 [+0.180, +0.462] on the 40; passing-only +0.285 [+0.173,
  +0.396]; one part per partner +0.261 [+0.149, +0.372] (33 parts); without the two design-time parts +0.247 [+0.153,
  +0.342]. Fifteen of the 40 parts get a sustain tilt (3 BKS, 12 GOAT): subset means +0.530 [−1.334, +2.394] on the 15
  and +0.155 [+0.054, +0.256] on the 25 (plain means 0.646 and 0.160); as contributions to the 40's mean, +0.220
  [+0.074, +0.366] and +0.101 [+0.045, +0.156]. Three parts carry about 40% of the summed D_list; paired half-widths
  about ±0.13.
- **The two design-time parts.** The refused sw50r part is a mutes fault (2 → 6 mutes); putting the true mutes back
  lifts envelope correlation with X from 0.376 to 0.989. GOAT item_69 is a tilt fault (+10.1 → −7.1 dB/s); its finished
  X decays 13 dB over the tilt span where the plain synthesis decays 7 dB, though X carries a +10 dB/s tilt.
- **Value errors in `in-F`** on the 40: mutes 271 true, 311 re-derived, 67 extra, 75 missed; tuning off by a median
  1.1 cents (max 5.8); levels off by a median 1.7 dB per group; raw tilt values reach 612 dB/s before the clamp, and 4
  of the 15 true tilts are clamped.
- **Today's rule by input form** (on the 40; mean logmel distance to X, tilt error on tilt parts, level error median,
  extra mutes, missed mutes, tuning error median): `in-F` 3.69, 5.0 dB/s, 1.66 dB, 67, 75, 1.1 c; `in-M` 2.24, 4.0,
  1.54, 48, 75, 1.1; `in-U` 1.54, 1.9, 1.19, 34, 75, 1.1. On the sw50r part the distance goes 26.2 → 6.3 → 1.95, on
  item_69 9.8 → 8.9 → 3.65; the first review's four-part probe agrees. The re-review: in `in-M` the sw50r part 6.277
  and item_69 8.883; without the hiss removal item_69 gives 9.536.
- **Tracking.** The best Spearman values with D_list on the 40 are +0.46 to +0.49 (1 − envelope correlation, |tilt
  change|, mute changes per group); tuning +0.25, level error +0.28.
- **Screens** (the four measured rows): checkpoints keep the row order and all three decided contrasts, but D_list
  shrinks to +0.086 [+0.013, +0.158] at 50 evaluations and +0.189 [+0.084, +0.294] at 100, per-part Spearman with the
  final value 0.45 and 0.59; floors keep the within-part order on 107 of 117 pairs, but within one row their Spearman
  with D is 0.35 to 0.53; agreement on the searches' common first trials keeps the row order (rank agreement 0.98,
  0.92, 0.84) but its per-part Spearman with D is −0.28 to −0.41 (common prefix a median 13, 6 and 4 trials);
  dry-domain distance to X has Spearman +0.42 to +0.60.
- **Real songs.** Build 2 less row (b): +0.274 [+0.186, +0.361] on the 40; 0.290 on the 15 tilt parts against 0.270
  on the 25 (plain means; reproduced by the first review); the audited Spearman of D* with the real gap is −0.12; build 2's real floor read +0.557, +0.822
  above the true DI.
- **A self-consistent rule prototype** (two worst parts, untuned): envelope correlation with X 0.376 → 0.9985 on the
  sw50r part and 0.824 → 0.986 on item_69; neither byte-identical. The plain correction step closed item_69's tilt error
  by about 10% a pass.
- **Rung sizes** from the finished-input probe: tilt 13 changed parts, mutes 41, levels 47, tuning 47.
- **Machine.** The planner's 47-part probe took about 10.5 CPU minutes on one core beside the search; during the second
  probe the load average was 27 to 29 on 8 cores and the render servers ran near 60% CPU.

## 13. What it cannot show

- The bench rewards recovering build 2's own values, artefacts included; the bridge still reads every input from the
  true DI.
- `in-M` is a stand-in judged from the code; `in-U` and `in-F` go beside.
- The fit may not repeat; every such fit is listed with the pass used.
- One bank, one transcriber, one seed, the score only. Every number is by the score unless heard.
