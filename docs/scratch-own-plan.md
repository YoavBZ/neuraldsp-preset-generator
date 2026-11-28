# The `vc-own` search row, `fs-own` (`phase_scratch_own`)

Declared 2026-11-28, on the user's go for this row ("Yes, run it (Recommended)", after the control). The planner's plan passed an independent review (Opus, high) with eleven binding amendments, which win where they differ from the plan; non-binding notes 1, 2, 3, 9 and 10 are taken. The orchestrator's calls: the codes are `XW-*` (amendment 2; `XO` is the X_oracle arm); the control's terms are Ux, Sx, Ubx and Urx; the spectral-envelope steps are deferred, with no name reserved; and, after the control's review, the user's renewed word under a waiting control code is recorded once, in `phase_scratch_voice_waiver`, not under this row's keys. Ledger `preset-ladder` `phase_scratch_own`, then `phase_scratch_own_answers` and `phase_scratch_own_outcome`. Code: `learn/scratch_own.py`. Run 2026-11-28: XW-part, shrunk-sensitive, audited 2026-11-28 (independent, Opus), CONFIRMED WITH CAVEATS; [results](scratch-own-results.md).

## Goal

Measure, by search, what real audio inside our note windows buys. The row repeats build 2's search with one change: the dry guitar is the stored `vc-own` instead of `tr-di`. It is the search-level ceiling for any note-driven rebuild (routes 1 and 2) with today's note activity and finish.

## The row

| Row | Dry guitar | Reference on the search half |
|---|---|---|
| Row (b) `fs-stem` | the true DI | `xlnoG@-3` |
| Build 2 `fs-notes` b2 | `tr-di` | `xlnoG@-3` |
| **`fs-own`** | **`vc-own`** | `xlnoG@-3` |

- **The search sees the stem, never the real record**, as row (b). Against either comparator the only change is the dry guitar.
- **Mechanics, unchanged code.** It mirrors `fs-refit` in `rederive_rows.py`: `scratch_notes.start_reference`, then `scratch_search.search_row_part` with `dry_sha256`; `answer_parts`, `deciding_stop`, `score_row_part`, `read_row_parts`. Same draw, halves, Cen, partners, seeds, 200-evaluation step 1 and step 2. A fake-world test holds that the new `search`, `answers` and `score` (and both checks) hand the shared steps the same arguments as `fs-refit`'s; only the guitar, its sha256, the name and the paths differ (amendment 10).
- **The guitar.** `PF/fs/voice/dry/vc-own/<part>.npy`, handed as stored: it already carries its finish and −22.9 LUFS, as `tr-di` did. Its file must be build.json's `file_sha256` and its samples its `audio_sha256`, and build.json's sha256 must be main's `phase_scratch_voice_dry` (52fea1ed…).
- **The judge's frame mask moves with the dry guitar.** In the search, J0's playing and scored frames and its 50%-pause refusal are set from the dry guitar. `vc-own`'s playing frames on the search half track `tr-di`'s closely, with a few parts apart; both sit below the true DI's on many parts. This is part of "the dry guitar", as it was in build 2 against row (b).
- **The score.** Cen, the answer, cp50, cp100, cp200, the shrunk answer and the borrowed answers, through the true DI, judged on the held half against the clean record.
- **S1.** A technical refusal reruns once (`--rerun`, a fresh process), then reads at Cen; `deciding_stop` reports it. The passing-only read sits beside, and the code is marked `refusal-sensitive` when the two differ.
- **No carry.** `vc-own` is no searched guitar's audio. A sha256 match with the true DI, `tr-di`, `avg+mild` or `rf2` on a part stops the row, to the orchestrator.

## The numbers

Per part, paired; the 40 (BKS+GOAT) decide through `scratch_notes.set_rows`, all 47 beside; the answer arm decides.
- D_own = G(`fs-own`) − G(build 2).
- C_own = G(`fs-own`) − G(row (b)).

## Outcome table `XW_TABLE`

The first that holds. Labels come only from `paired_reading`, read both ways: on D_own, and on −D_own (build 2 against the row), where "matches" rules a heard-size gain out.

| Code | When | Said | Decides for the routes |
|---|---|---|---|
| XW-anomaly | A check fails, a stored figure does not reproduce, any of D_own, −D_own and C_own has no usable interval or reading (amendment 1), or C_own reads better | Unexpected; audit. If the audit finds no fault, the figures go to the user as read, never dropped | Stop; audit; nothing said before the audit |
| XW-worse | D_own reads worse | If the audit finds no fault: real audio inside our windows drives the search worse than the bank guitar | Audit the gate and the cuts first; routes 1 and 2 are not supported |
| XW-closed | D_own better, C_own matches | The cost is recovered: a heard-size loss against the true DI is ruled out | Routes 1 and 2 stay open with the whole cost to gain; finer corrections of the bank's spectral envelope may follow, on their own declaration |
| XW-part | D_own better, C_own not "matches" | A heard-size part is recovered; C_own's reading says whether a residual is shown (worse) or only not ruled out (undecided) | Routes 1 and 2 stay open; their room is at most −D_own; the envelope corrections may follow, on their own declaration; the residual belongs to N, K and F together |
| XW-level | −D_own matches | A heard-size gain from real audio inside our windows is ruled out | Routes 1 and 2 cannot pay by search. C_own's residual holds N, K and F together (F, +0.172 at the floor, is larger than N there); the cheap split of C_own is the 50-evaluation `vc-fin` row (about 2.6k renders), on its own declaration and go (amendment 5); the deferred envelope corrections do not run |
| XW-undecided | Anything else | Not decided; undecided is not failed. When C_own reads matches, the report says a heard-size loss against the true DI is ruled out (note 2) | To the user with what the intervals rule out |

C_own reading better is a stop, not an impossibility: the search target is the stem and the frame mask moves with the guitar. Under the projected +0.06 to +0.16 it would almost never happen.

## The gate

Every render command (`check-score`, `check-search`, `search`, `score`):
1. reads main's `phase_scratch_voice_control_outcome`, and refuses when it is absent;
2. stops on XC-anomaly, on an undeclared code, or on XC-part or XC-notes whose outcome carries no `coverage_label` (None or `coverage-sensitive`). This is the module's own check, beside the spend gate's. It fails closed as `spend_refusal` does since #658, and its codes must be the ones the spend gate declares (the table guard holds it);
3. then calls `scratch_voice.require_spend("search-row")` and relies on it.

| Control code | The row |
|---|---|
| XC-anomaly | Stops |
| XC-part or XC-notes with no `coverage_label`, or an unknown one | Stops (fails closed), to the orchestrator |
| XC-notes, or XC-part marked `coverage-sensitive` (`coverage_label`) | Waits for the user's renewed word. The spend gate opens only through `phase_scratch_voice_waiver` with `answers_code` the control's code, `date` on or after the control outcome's, and `spend_kinds` holding `"search-row"` |
| XC-stands, plain XC-part, XC-undecided | Goes on, on the user's 2026-11-28 go |

The control's review settled amendments 3 and 4 this way (2026-11-28): the word is recorded once, in the waiver, which names the spend kinds it opens; this row keeps no word of its own.

## Beside, never changing the code

- **Arms.** The shrunk arm's code (`shrunk-sensitive` when it differs from the answer arm's; `arm-sensitive` is taken), and the cp50, cp100 and cp200 codes.
- **LOUDAR.** G at cp50 of `fs-own` less `ld-stem`'s G50 (S1 as LOUDAR's own read), on BKS+panel (23 parts), pooled as `scratch_loudar.bp_rows` does, with the part-weighted mean beside. Read both ways. "Better" says the oracle ceiling sits above the released song-only rebuild on unseen sets; anything else says it is not shown to.
- **Fieller's share** −D_own / (build 2 − row (b)): the share of build 2's cost recovered (note 3).
- **Splits.** Each cluster of the 40 left out; the three largest parts (12-hex tags, their contribution, the 40 without them); clean, crunch, all 47, the panel; one part per partner.
- **Against row (c):** G(`fs-own`) − G(row (c)) on every arm and split.
- **Ranks.** The stored S (the sound gap's rows.json) and the control's Ux (its rows.json, hashed in its outcome) per part against −D_own: Spearman on the 40.

## Reproduced first

Before the read, `reproduce` must give, from the stored files:
- build 2 − row (b) on the 40 exactly as the exact-notes read stored it (its rows.json hashed in `phase_scratch_exact_outcome`), and +0.274 [+0.186, +0.361] to 3 places;
- LOUDAR's G50 on BKS+panel through `bp_rows`, exactly as LOUDAR's read stored it (its rows.json hashed in `phase_scratch_loudar_outcome`).

A failure reads XW-anomaly. The other seen figures below are recomputed and reported to 3 places beside; they gate nothing.

## Seen before the declaration

With weighting and checkpoint:
- Build 2 − row (b), answer, the 40, cluster read: +0.274 [+0.186, +0.361]; plain mean +0.277.
- Build 2 − row (b) at cp50: +0.230 [+0.147, +0.314]; on the shrunk arm +0.143 [+0.075, +0.212] (the review's).
- G(build 2) +0.009 [−0.088, +0.106]; G(row (b)) −0.264 [−0.310, −0.219].
- `vc-own`'s floor (N+K+F): +0.321 [+0.261, +0.380] (cluster), +0.315 (plain).
- The review's post hoc projection of C_own: +0.06 to +0.16, so D_own about −0.11 to −0.21.
- LOUDAR less build 2 at cp50 on BKS+panel, by the declared `bp_rows` pooling: +0.002 [−0.116, +0.121], part-weighted −0.009; BKS alone −0.015 [−0.146, +0.117], the panel +0.019 (amendment 9). Beside it, −0.005 [−0.103, +0.092] is the earlier reviewer's 11-cluster combined read.
- By its own power, the likely codes are XW-part or XW-undecided.
- On 47 of 47, the stored `vc-own` is 492,000 samples, −22.9 LUFS within 1e-3, its npy sha256 build.json's, and byte-identical to neither `tr-di` nor the true DI. No search in the stored rows (build 2, (b), (c), `fs-refit`) refused.
- The 47 parts have been read many times (note 10).

## Names (grepped)

`git grep -F` on origin/main da4e0e22, over docs, learn, tests, scripts and reference, gave 0 hits for `phase_scratch_own`, `fs-own`, `XW-`, `XW_TABLE`, `xw_code`, `XW_`, `scratch_own`, `D_own`, `C_own`, `fs/own` and `shrunk-sensitive`, and none for `XW` as a word. `arm-sensitive` is taken (`docs/pipeline-fix-plan.md`), so the shrunk arm's label is `shrunk-sensitive`. Re-grepped on origin/main 8bc321eb, after the control's declaration (#658) merged: still 0 hits in text files.

## Phases, each verified before the next

| # | Phase | Renders, time (measured rates) | Verify |
|---|---|---|---|
| 0 | Preconditions | — | The control's outcome on main; 35 GB free; 3 slots free |
| 1 | Declare (this PR) | 0 | Tests pass; the table guard holds |
| 2 | `check-score`, `check-search` | 62, about 1 min | Row (c)'s score and first 10 evaluations repeat exactly |
| 3 | `search --shard k/3`, then `--rerun` | 94 start references + about 12,300; 1.8–2.0 h | Every dry sha256 the declared one; refusals rerun once |
| 4 | `answers`, hash PR | 0 | `phase_scratch_own_answers` on main before any score |
| 5 | `score --shard k/3`, then `--rerun` | 940, about 12 min | The scoring control on every part |
| 6 | `reproduce`, `read`, once | 0 | Stored figures reproduce first; rows saved before the code |
| 7 | Audit, results PR | 0 | `phase_scratch_own_outcome` |

About 13,400 renders in all. The basis: `fs-refit`'s search took 4,239 + 4,228 + 3,929 = 12,396 renders (the longest shard 6,652 s), its score 940 renders at 703–728 s a shard, and its checks 40 + 22 = 62.

## Phase status

- **2026-11-28, phases 2 to 4** (from a fresh detached worktree of main at 309636c9, after the control's XC-stands):
  - `check-score` passed (40 renders, no mismatch) and `check-search` passed (22 renders, no mismatch): both repeat row (c) exactly.
  - `search --shard 0/3, 1/3, 2/3`: 4,244, 4,252 and 3,933 renders in 6,457, 6,417 and 6,247 s (12,429 in all, 94 of them start references). No part refused, so no rerun pass ran.
  - `answers`: 47 parts, 0 refused; sha256 dcd1c691…, hashed in `phase_scratch_own_answers`.
- **2026-11-28, phases 5 to 7** (from a fresh detached worktree of main at 44a686f2):
  - `score --shard 0/3, 1/3, 2/3`: 320 + 320 + 300 = 940 renders (711–736 s a shard); the scoring control on 47 of 47 parts, with no rerun.
  - `reproduce` held, and `read` ran once: **XW-part**, shrunk-sensitive (`phase_scratch_own_outcome`; [results](scratch-own-results.md)). 13,431 renders in all.
  - Audited 2026-11-28 (independent, Opus): CONFIRMED WITH CAVEATS.
- **Next:** the user picks the sound route; under XW-part the spectral-envelope steps are unlocked, on their own declaration.

## Guards

- Every command refuses unless this checkout runs main's code (`learn/scratch_own.py` and its pinned files: `scratch_search`, `scratch_notes`, `scratch_exact`, `scratch_voice`, `voice_build`, `voice_floors`, `rederive_rows`, `scratch_loudar`, `scratch_codec`, `rederive_fit`, `scratch_rederive`, `note_transcribe`, `note_replay`) and keys (`phase_fs*`, `phase_scratch_own*`, `phase_scratch_voice*`), and main holds the keys it reads. Each step runs from a fresh worktree at main.
- At most 3 shards. Each file is written once.
- **The search opens nothing scored** (amendment 6): `rederive_rows`' and `scratch_exact`'s forbidden files, and any answers, rows, report, reproduce or outcome file (`fs/outcome.json` included); anything under a score, floor or repeat folder (`repeat/`, `floor-repeat/`, `floors-first/` and their reruns, the sound gap's and the control's included); anything under `PF/fs/voice/control/` or `PF/fs/envelope/`.
- The module edits none of the pinned files (amendment 11). The envelope work, when it comes, edits none of them either.

## Files

`PF/fs/own/`: `checks/check-score/`, `checks/check-search/`, `search/`, `start-ref/`, `answers.json`, `score/`, the `-rerun` folders, `reproduce.json`, `rows.json`, `report.json`. Part keys appear in the read's files and in git only as 12-hex tags.

## Commands

Run only this row's test file while renders run. Launch long jobs with `setopt no_bg_nice` and caffeinate, and record their PIDs.

    .venv/bin/python -m pytest tests/test_scratch_own.py -q
    $MAIN -m learn.scratch_own check-score
    $MAIN -m learn.scratch_own check-search
    $MAIN -m learn.scratch_own search --shard k/3      # then --rerun
    $MAIN -m learn.scratch_own answers                 # hash PR before score
    $MAIN -m learn.scratch_own score --shard k/3       # then --rerun
    $MAIN -m learn.scratch_own reproduce
    $MAIN -m learn.scratch_own read

## What it can't show

- **An oracle.** `vc-own` is the true DI's audio, gated by notes read from the true DI. Nothing here speaks for the song-only path.
- **The residual is mixed.** C_own holds N, K and F together. Splitting it would take the 50-evaluation row through `vc-fin`, about 2.6k renders, on its own go.
- **By the score only**, one search, one seed.
