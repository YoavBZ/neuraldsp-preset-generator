# The from-scratch search: does a search from Cen through the degraded inputs land closer than Cen? (plan)

**Status:** declared 2026-11-21, before any run (Plan 1 of "Direction 1 after R-alone", on the user's "Agree" of
2026-11-21, after an independent review of the plan: approve with changes, B1 to B5 built in, N1 to N3 adopted). Row (b)
ran 2026-11-21 and was audited: [results](scratch-search-results.md), passes (G −0.315, I −0.462 on the pool). Row (c)
`fs-both` ran 2026-11-21 and was audited: passes narrowly (G −0.148 [−0.246, −0.050], I −0.376 on the pool; BKS+GOAT
undecided). **The cell is F-both.** It is recorded under `phase_scratch_both_outcome`, and `phase_fs_outcome` is left unwritten; any
future gate for the flagged build must read `phase_scratch_both_outcome`. Row (a) does not run. The flagged song-time build is
held pending the user. Every number is by the score unless it says "by ear": J0, ln(d_row / d_against) on the held half, below
zero closer; 90% cluster t intervals; the deciding pool is BKS, GOAT and the panel weighted equally
(`full_controls_c3r.pooled`), with BKS+GOAT pooled alone beside. `PF` is `~/ndsp-presets/learn/trusted-data/pipeline-fix`.
**2026-11-22:** a new row, `fs-notes`, the note rebuild's `tr-di` against the same stem, is declared in
[section 10](#10-the-fs-notes-row-2026-11-22-ledger-phase_scratch_notes) (ledger `phase_scratch_notes`), with BKS+GOAT
deciding on the user's exception for that row only. It does not touch rows (b) and (c) or `OUTCOME_TABLE`. Not run.

**The user's rule.** No action rests on a gap under 0.05. "Passes" means decided better with the mean at −0.10 or
beyond. An interval inside ±0.05 reads "not readable by the score". Undecided is not failed.

- **Ledger:** `preset-ladder`: `phase_fs` (this declaration); `phase_fs_draw` (the subset's sha256, before any render);
  `phase_fs_answers_<row>` (`_stem`, `_both`, `_blur`, `_control`: each row's answers' sha256, on main before its
  `score`); `phase_fs_outcome`. Grepped first: no `phase_fs*` key, row name (`fs-stem`, `fs-both`, `fs-blur`,
  `fs-control`) or code (`F-both`, `F-compound`, `F-dry`, `F-stem`, `F-undecided`, `F-start`, `F-constant`) exists in
  `docs/`, `learn/` or the ledger.
- **Code:** `learn/scratch_search.py` (`subset`, `with_partners`, `blank_plan`, `usable`, `step1_search`, `run_part`,
  `shrunk`, `centre`, `nonfinite_rule`, `part_numbers`, `row_reading`, `b2_lever`, `OUTCOME_TABLE`, `next_row`,
  `outcome`, `stopped`). Tests: `tests/test_scratch_search.py` (pure, light CI; two data tests where numpy and the
  stored data exist).
- **Reused unchanged:** C2's search pieces (`knob_ceiling.coord_search` and `knob_search`, `full_controls.c1a_space`,
  `c1a_start`, `make_canon`, `SEED`; C1b's stage dims, budgets, seeds and canonical form; `full_controls_c2.peak_bound`);
  the replay's draw, menus, stems, blurred DIs, `half_distance`, `summary` and `number_reading`.
- **Data:** `PF/fs/` (`draw.json`, `search/<row>/`, `answers-<row>.json`, `score/<row>/`, `report-<row>.json`,
  `outcome.json`). No render audio is kept. It reads `PF/replay/` (the stems, kept; the blurred DIs `di/avg+mild/`,
  which must stay until rows (c) and (a) are done or ruled out).

## 1. The question

On held-out ladder parts, run C2's label search from Cen, driven only by a degraded input on the search half. Does it
land a heard size closer than Cen, and closer than the same row's answers for other recordings, scored on the held half
through the true DI against the clean record? The replay showed the degraded comparison ranks a true-DI search's
candidates well; it did not show that a search through it lands well (its menu held none of the degraded comparison's
own false favourites). This is the test R-alone requires before any product claim. It converges: at most three rows
(N1), each read once.

**Why it may fail:** October's nearest precedent (a true-DI search against an htdemucs stem) failed; the replay's
full-mix row showed what false favourites look like (more gain, denser renders); from Cen, 262 renders may not get far
even with the true DI; `both-alone` kept only 51% in the replay.

## 2. The rows

| Row | Plan letter | Dry guitar (render and judge) | Reference on the search half | Runs |
|---|---|---|---|---|
| `fs-stem` | (b) | the true DI | `xlnoG@-3`: X-LANCE's stem of the mix with no other guitar | first |
| `fs-both` | (c) | the blurred DI (`avg+mild`) | `xlnoG@-3` | (b) passes, or B2's lever |
| `fs-blur` | (a) | the blurred DI | the clean record | (b) passes and (c) does not |
| `fs-control` | Control | the true DI | the clean record | (b) does not pass |

Later rows follow the coded cells without asking again (the user, 2026-11-21), each after the parent's audit of the
row before. No full-mix row: it failed as a menu pick.

## 3. The search (B3: new loop, C2's pieces)

C2's `cmd_search` cannot take a degraded reference: it hard-codes the clean record and the judge's DI, starts against a
source label, and its guards refuse any evaluation non-finite on either half, so C2 itself used the held half in its
selection. The loop is new code; only the pieces are reused.

- **Start:** the part's own fold's Cen (the replay's menu position 0), in C1a's start form (`c1a_start`). The review's
  probe: all 24 Cen settings pass `audible_change` empty without declaring the gate (already on at −80) and are dry. The
  run refuses any part where the start changes anything that sounds.
- **The start check, by render:** the search's first evaluation (Cen through the row's dry guitar, primed with Cen as the
  replay was) must be within 0.005 in ln of the replay's stored position-0 search-half distance for the same dry guitar
  and reference (`PF/replay/dist/`), or the part refuses. No second start.
- **Step 1:** `coord_search` over `c1a_space` (input gain, the core knobs, the amp EQ, the pedals, the gate), budget 200,
  `full_controls.SEED`, categoricals by levels, C1a's canonical form, in one renderer process primed with the start.
- **Step 2:** C1b's stage A (the rooms, 16) and stage B (the mic types and amp EQ, 48, `knob_search`) on step 1's best, in
  a fresh process primed with it; its first evaluation within 0.005 of step 1's best value, the canonical start then the
  raw start on a miss, step 1's best standing if both miss. Only the canonical start is audible-checked (as in C2):
  the raw start is step 1's best plus the label's spring switch.
- **The final:** rendered fresh (primed alone). C2's guards and F70's peak bound, on the search half only: an evaluation
  stands when its search-half value is finite and its peak is no lower than `peak_bound` (min of −57 dBFS and the start's
  peak) less 0.05 dB; a final that fails falls back to step 1's best, then to the start.
- **Not searched:** the time effects, the spring and the doubler stay off (dry sources), as in C2.
- **The objective:** J0 on the search half (`note_replay.half_distance`) at the stored lag, the row's dry guitar as the
  judge's DI. A render with a non-finite sample scores inf (the worst).

**The held half is never in the search process.** Each reference is handed over with every sample outside its search
half's window [int(a·48000), int(b·48000)) set to **zeros**, not NaN: `aligned_distance` refuses a non-finite sample
anywhere in the array, while a zero held half reads "no measurable loudness" (inf), and `aligned_distance` slices the
reference to the half before it normalises. No guard reads the held half. Proven at zero renders before the declaration
(both tests in `tests/test_scratch_search.py`):

- **Equivalence (B3):** with the clean reference, the true DI and a label start, the loop requests exactly the stored C2
  record's step-1 settings in order and uses every stored evaluation (C2's `replaying`), on **40 of 40** eligible stored
  records of the subset (7 skipped: 4 continued C1a records, 3 with the gate off after a start miss).
- **Independence:** on two parts (one per search half), a 20-evaluation step-1 run on a stub renderer gives the same
  values and settings with the held half zeros, the held half noise, or the reference whole; the held half on zeros
  reads inf.
- A stub-renderer smoke of the whole loop on two parts: 261 renders a part (1 + 200, 1 + 57, 2 fresh).

## 4. Units: 47 of the replay's 119 parts, drawn once (seed 20261301)

| Set | Rule | Parts | Clusters |
|---|---|---|---|
| Panel | every part of the replay's (Silent Waves never drawn, Drowning left out) | 7 | 3 DI files |
| BKS | 2 per DI file, the wanted amps rotating over the files from a seeded offset | 16 | 8 DI files |
| GOAT | 3 per fold and class, each on its own amp where possible, at most one a GOAT item | 24 | 24 items |

The pooled half-width is the same as with 119 (±0.165 against ±0.17 on the stem rows: the panel's 3 DI files set it);
BKS and GOAT alone read about ±0.06. The full 119 cannot tighten the pool. Planning read (zero renders, the same code):
47 parts, 0 refused for partners; the 3 replay parts with non-finite blurred-DI renders (B5) are not drawn.

**The borrowed partners (N2, B4: in the draw's hash).** A partner has the same amp and class, another cluster, no
shared identity (C3r's: the DI file and a capture's creator) and another rig. A part's partners are ordered: its own
set's eligible parts (seeded, 20261302), then the other sets' (seeded). The borrowed answer takes the first 3 that
answered in the row, so it comes from the own set where 3 there answered and reaches across sets otherwise (reported:
all 16 BKS and 7 panel parts reach across; GOAT has 3 same-set partners each). The draw refuses a part with fewer than 3
eligible. A part whose partners leave fewer than 3 answers refuses.

## 5. The score (renders; the only step that reads a held half)

Every setting of the hashed answers is rendered through the part's true DI, each primed alone (`fresh_render`, as the
ladder rendered Cen's stored value), and judged on the held half against the clean record at the stored lag: Cen, the
answer, step 1's incumbents at 50, 100 and 200 evaluations, the answer shrunk halfway to Cen, the row's centre and the 3
borrowed answers (identical settings rendered once). At most 20 renders a part.

- **The scoring control:** Cen's render must repeat its stored held-half value within 0.005 in ln, or the part refuses.
- **G** = ln(answer / Cen). **I** = G − the borrowed answer (the mean of the 3 partners' ln(held / Cen) on this part).
- **Non-finite on the held half (B3, declared):** a setting whose held-half score is non-finite takes the part's worst
  finite held-half score among the settings scored on that part in the row, and never better than Cen's (counted and
  listed).
- **Side readings, never deciding:** G and I at 50, 100 and 200 evaluations; the shrunk answer's G and I (October's
  device: every searched continuous control halfway back to Cen in its unit space, the rest the answer's); the row's own
  centre (from all the part's answered partners: continuous controls at the mean unit value, switches and mic types at
  the most common value, a tie to Cen's) and the answer less it; the stored label less Cen (zero renders); each set,
  clean and crunch, half A, each cluster left out; input gain and the pedals' switches against Cen's (compared with the
  Control's answers when it runs).

## 6. The outcome (coded and tested before any run)

**A row's reading** (`row_reading`, on the deciding pool):
- **passes:** G and I each decided better with the mean at −0.10 or beyond;
- **constant (B1):** G passes and I does not (fails or undecided): a better constant, the gain not shown to be this
  recording's;
- **fails:** G's or I's interval rules out a gain beyond −0.05 (and not constant);
- **undecided:** the rest, written up with what each interval rules out.

**B2's lever, declared (the user, 2026-11-21):** row (b) reads `undecided-b2` when it is undecided on the pool, passes on
BKS+GOAT alone (G and I each decided better with the mean at −0.10 or beyond), and the panel's means of G and of I are
each ≤ 0. Then, with the Control passing, row (c) runs.

| (b) `fs-stem` | Control | (c) `fs-both` | (a) `fs-blur` | Code | Reading | What it licenses |
|---|---|---|---|---|---|---|
| passes | — | passes | — | F-both | A search from Cen works through the stem and a blurred dry guitar together, where the target is alone | Build the song-time search for alone windows behind a flag, for testing only, if Plan 2's W0 is not W-rare (N3). Next: a real note-matched dry guitar on the same rows (waits for the user), then a blind sitting. No claim on released mixes |
| passes | — | not passes | passes | F-compound | Each fault alone is survivable; together not shown | To the user. The dry guitar's quality decides; the rebuild's bar is to beat this blur |
| passes | — | not passes | fails, undecided | F-dry | The stem works as a reference; a dry guitar this blurred does not drive a search | The route waits on a better dry guitar. Not a verdict on one |
| passes | — | not passes | constant | F-constant | Row (a) finds a better constant | To the user; the centre is a lead for a better constant |
| fails | passes | — | — | F-stem | The stem misleads a search even with no other guitar | Direction 1 stops at the stem as a search reference. Separator work gets this row as its yardstick |
| undecided | passes | — | — | F-undecided | Not decided | To the user, with the intervals, BKS+GOAT beside and the share of the Control kept |
| undecided-b2 | passes | passes | — | F-both | As F-both, with (b) undecided on the pool only | As F-both |
| undecided-b2 | passes | fails, undecided | — | F-undecided | Not decided | As F-undecided |
| undecided-b2 | passes | constant | — | F-constant | Row (c) finds a better constant | As F-constant |
| constant | passes | — | — | F-constant | Row (b) finds a better constant: G passes, I does not | To the user. No song-time search rests on it |
| not passes | fails, undecided | — | — | F-start | A 262-render search from Cen is not shown to beat Cen recording by recording even with the true DI | Says nothing about the degraded inputs. To the user: a longer budget or a two-stage start, as a reviewed amendment |
| not passes | constant | — | — | F-constant | The Control finds only a better constant | As F-constant |

- `table_guard` refuses unless every reachable path (32) ends in exactly one cell, every cell is reachable, and no path
  reads more than three rows (N1). A constant reading on the path that does not decide the cell is noted ("the gain is
  not shown to be this recording's").
- **The pool stays the user's:** `preset_ladder.summarise` falls back to BKS+GOAT when fewer than 3 of the panel's DI
  files are read, and the panel's DI files hold 1, 3 and 3 parts, so one refused panel part can drop it. `read`
  therefore stops the row (no reading, to the user) unless G's and I's deciding sets are BKS, GOAT and the panel
  (`pool_refusal`). The rows go to `rows-<row>.json` before the reading; `report-<row>.json` is written once, with
  its reading or its stop, and every report must be read from answers hashed on main.
- **The refusal stop (B5):** a row with **3 or more of its 47 parts refused** (a start-check miss, an unusable start, a
  missing borrowed answer, a scoring-control miss) stops: no reading, nothing runs on, to the user. The replay's 3
  parts with non-finite blurred-DI renders were checked at the draw: none is drawn.

**Power (planning read, from the replay's per-part numbers).** On a stem row the pool's half-width for G is about
±0.165, set by the panel: a true G of −0.25 or beyond passes, about −0.17 is the edge, −0.12 reads undecided; a fail
needs a mean near +0.115. Expect pass or undecided (hence B2's lever).

## 7. Cost (measured rates only)

| Step | Renders | On 3 processes |
|---|---|---|
| One row: 47 × at most 270 search renders (1 + 200, a step-2 start miss 2, 1 + 64, 2 fresh; the stub smoke used 261) + at most 20 scoring renders a part | ≤ 13,630 | 1 h 54 min to 2 h 31 min |
| The longest path, three rows (N1) | ≤ 40,890 | 5 h 43 min to 7 h 32 min |

The range is 7,160 an hour (three times the replay's position check's one-process rate, 2,387) to 5,430 (the replay's
three shards together). The first 6 parts (`--first 2` on each of 3 shards) re-time the rate before the rest is
committed. No separation, no training, no MPS job.

## 8. Stop rule, controls, house rules

- **Stop rule:** each row is read once; the plan ends at the first cell reached. No row is re-run with another seed,
  budget or start without a reviewed amendment.
- **Order in code:** `search`, `answers`, `score` and `read` refuse any row but `next_row`'s from the reports so far, and
  refuse to run unless this checkout's `learn/scratch_search.py` and `phase_fs*` keys equal main's; `score` refuses
  answers whose sha256 is not `phase_fs_answers_<row>` on main.
- **The audit:** an independent agent recomputes every row with its own code from the answers and the score files.
- **Machine:** at most 3 render processes machine-wide, slots from the executor; `setopt no_bg_nice`, caffeinate; PIDs
  recorded at launch; the house disk guard, 31 GB in decimal units (`trusted_data.DISK_GUARD_GB` = 31.0 against `pretrain_set.free_gb()`, `shutil.disk_usage(...).free / 1e9`; about 28.9 GiB), checked before every part in `search` and `score`; never beside a separation.
- **Trusted data:** Silent Waves and Drowning are out. No sealed set. No old DI-rebuild model.
- **Public repo:** no settings values and no song data in the docs; answers stay under `PF/fs/`.

## 9. What it can't say

- Anything with a real note-matched dry guitar, or with level, timing or lag errors (the stored lag is used).
- Anything on released mixes, on full mixes with other guitars, or by ear.
- Anything about effects.
- Whether a search over the whole window, as the product would run, does better than over one half.

## 10. The `fs-notes` row (2026-11-22; ledger `phase_scratch_notes`)

Declared 2026-11-22, before anything in it runs, with the note rebuild's redo
([note-rebuild-plan.md section 12](note-rebuild-plan.md#12-the-redo-notes-transcribed-from-the-di-read-as-the-fs-notes-row-2026-11-22-ledger-phase_nr_1_redo)),
after an independent review and its re-review. Code: `learn/scratch_notes.py`; tests: `tests/test_scratch_notes.py`.
Data: `PF/fs/notes/`.

**The question.** Does a guitar re-played from single recorded notes, at notes Basic Pitch read from the true DI,
drive the search as well as row (c)'s blurred true DI? A pass ships nothing; the next row (the stem-notes row) reads
every input from the stem.

**The row.** `fs-notes` = (`tr-di`, `xlnoG`). `tr-di` is the dry guitar of every search render and the judge's DI; the
search-half reference is `xlnoG@-3`, the held half zeros. The answers are rendered through the **true DI** and judged
on the **held half** against the **clean record**. Same draw (`phase_fs_draw`), Cen, partners, budget, seeds,
checkpoints and halves as rows (b) and (c). All 47 parts are searched and scored.

**The deciding set: BKS+GOAT, 40 parts** (the user's answer of 2026-11-22, the explicit exception to this plan's
"never read on fewer sets", for this row only). The panel's 7 parts are read beside, split into its MedleyDB files and
The Laminar Flow; they cannot swing the result. `pool_refusal` does not stop this row: a panel refusal or a lost panel
DI file only shortens the beside readings. The stem-notes row's deciding set comes from its own declaration.

### 10a. One code path for every row (the refactor)

`ROWS`, `phase_answers`, `require_turn`, `OUTCOME_TABLE`, `next_row`, `table_guard`, `DECIDING` and `pool_refusal`
are unchanged, so `scratch_search`'s own commands still refuse any row but its four (rows (b) and (c) are finished and
`next_row` reads none). The per-part bodies became shared functions: `search_row_part`, `answer_parts`,
`score_row_part` and `read_row_parts` (with `report_body`). `run_part` gained three arguments that do nothing at their
defaults: a start reference, the dry guitar's sha256 recorded in the record, and a stop after step 1 for the search
check.

| Step | Shared with rows (b) and (c) | New for this row |
|---|---|---|
| `search` | `search_row_part` (`run_part`), `load_ref_blank`, the start check at 0.005, the disk guard, at most 3 shards | The start reference: the exact first evaluation (`sx1(start)`) through `tr-di` in its own fresh primed process, just before the part's search (2 renders), written once. Every search record holds the dry guitar's sha256. A part refused by the content checks is recorded as refused, unrendered |
| `answers` | `answer_parts` (`borrowed`, `shrunk` at 0.5, `centre`) | Refuses a search record whose dry guitar is not the `tr-di` of the build hashed as `phase_scratch_notes_dry`. The refusal stop counts the 40 deciding parts (3 or more stop), content refusals included |
| `score` | `score_row_part`: through the true DI, the held half against the clean record, the scoring control, 10 settings a part | — |
| `read` | `read_row_parts`, `nonfinite_rule`, `part_numbers`, `summarise_row`, `row_reading`, `number_reading` | `paired_reading`, `FN_TABLE`, `fn_code` |
| Guards | `never_overwrite` on every output; the hashes of the draw, the build and the answers | `redo_on_main`: `learn/scratch_search.py`, `scratch_notes.py`, `note_rebuild.py`, `note_rebuild_s1.py`, `note_rebuild_ear.py`, `note_transcribe.py`, `bp_run.py` and the keys `phase_fs*`, `phase_scratch_notes*`, `phase_nr*` equal main's. Every command needs `phase_scratch_both_outcome`, `phase_scratch_notes` and `phase_nr_1_redo` on main; `search` both checks passed and the install, notes and build hashed; `answers`, `score` and `read` `phase_nr_1_redo_ear` = ok |

**The proof that every row is scored the same way:**
- tests: the 32 paths and every cell of `OUTCOME_TABLE` as before; the loop-equivalence test still replays 40 of 40
  stored C2 records;
- `read` at zero renders (a test on the stored data): the shared path on row (c)'s stored answers and score files
  reproduces `rows-fs-both.json` exactly, and the paired (c) less (b) reproduces +0.167 [+0.110, +0.224] on the pool
  (both pass at declaration);
- `score-check` (about 40 renders, once, after the merge): row (c)'s first BKS and first GOAT part re-scored through
  `score_row_part`; every render's sha256 and held value must equal the stored file's. It writes to
  `PF/fs/notes/check-score/` only;
- `search-check` (about 12 renders a part, once): the same two parts through `run_part` with avg+mild as the dry
  guitar (passed as this row passes `tr-di`), row (c)'s start reference passed explicitly and a step-1 budget of 10;
  its evaluations must equal the start of row (c)'s stored step-1 curve exactly. A pure test shows a budget of 10 asks
  for the same first settings as 200. It writes to `PF/fs/notes/check-search/` only. The start check alone cannot catch
  a wrong dry guitar, since the start reference comes from the same code;
- `search` refuses until both checks have passed.

### 10b. The number and the reading

**Arms:** the answer and the shrunk answer (every searched continuous control halfway back to Cen), both always scored,
each compared like for like with row (c)'s. Two arms share the parts, so a false match is at most 10%.

**`D_notes`:** per part, G(`fs-notes`) − G(`fs-both`) (Cen is the same render in both rows). Above zero, the rebuilt
guitar did worse than avg+mild. Row (c)'s bar is recomputed on exactly the parts this row scores. Read on BKS+GOAT, on
its clean 20 and on its crunch 20 by `paired_reading`:

| Reading | When |
|---|---|
| better | the whole interval below zero, the mean at −0.10 or beyond |
| matches | the upper end under +0.10 (a heard-size loss ruled out) and the mean under +0.05; an interval inside ±0.05 is worded "level, not readable by the score" |
| worse | the whole interval above zero, the mean at +0.10 or beyond |
| undecided | the rest |

**`FN_TABLE`** (BKS+GOAT; the first row that holds; "an arm" is the same arm throughout a row):

| Code | When | Reading |
|---|---|---|
| `FN-match` | an arm matches or is better on the 40 and on the clean 20, its own G on the 40 has its upper end below zero, and its own G on clean does not read "fails" | with these notes the rebuilt guitar drives the search as well as the blurred true DI, clean included, and the row itself beats Cen |
| `FN-crunch` | not the above; an arm matches or is better on the crunch 20, and its own G on crunch has its upper end below zero | it holds on crunch; clean is worded from its own reading: "worse", "undecided", or "matches, but the row does not beat Cen there" |
| `FN-worse` | both arms read worse on the 40 | it fails with the current transcriber and synthesis; not a verdict on the note route |
| `FN-clean-worse` | both arms read worse on the clean 20 | clean fails with the current parts; the 40 and crunch are not decided |
| `FN-undecided` | anything else | not decided; undecided is not failed |

**What each licenses, as a recommendation to the user (nothing continues on its own):**

| Code | Recommendation |
|---|---|
| `FN-match` | the stem-notes row, under its own declaration; then a blind sitting that includes the losing parts. The flagged build stays held |
| `FN-crunch` | the stem-notes row, its declaration asking the user for crunch to decide with clean beside. Where clean read worse: clean leaves the note route with the current parts and keeps today's start; the bottleneck is named. No clean claim |
| `FN-worse` | no stem-notes row. To the user with the bottleneck named and one recommendation: fix that part, or the declared fallbacks (the guided or network route). Audited adversarially first |
| `FN-clean-worse` | as `FN-worse` for clean; for crunch, `FN-undecided`'s rule on the crunch 20 |
| `FN-undecided` | **lean-go** when some arm's mean `D_notes` on the 40 is under +0.05 and its own G has its upper end below zero: the stem-notes row, read against row (c)'s bar directly, said with it that a heard-size loss against avg+mild is not ruled out and that the split is a cut on the point estimate of an undecided interval; **lean-stop** otherwise, worded "undecided, recommend no more renders on this build", never "fails", the bottleneck named |

In every case: no rerun on these 47 parts. One fix is allowed after a named bottleneck; it must first show at zero
renders on development windows, and its read comes under its own later declaration, with its own comparator and
measured cost (the replay holds 75 parts outside the 47: 48 GOAT on fresh items, 24 BKS on the same 8 DI files, and 3
of Drowning, which is left out; row (c) never ran on them).

**Naming the bottleneck (descriptive, after the read).** The 40 are split at the median of `onsets-found`. "The
synthesis" when `D_notes`' mean on the better-transcribed half is at +0.10 or worse with its interval clear of zero;
"the transcriber" when the lower half's mean is worse than the upper's by 0.10 or more with the difference's interval
clear of zero (the halves' half-widths in quadrature); otherwise "not separable by these figures". Beside it:
`D_notes` against `ring-kept`'s figure, the share of bent notes, the share of chords.

**Power** (planning read from rows (b) and (c), reproduced by the review; paired half-widths of (c) less (b)):

| Set | Answer | Shrunk |
|---|---|---|
| BKS+GOAT, 40 parts | ±0.067 | ±0.041 |
| Clean, 20 parts (16 clusters) | ±0.122 | ±0.077 |
| Crunch, 20 parts | ±0.062 | ±0.028 |

So "matches" needs a mean `D_notes` of about +0.03 or less (answer) or +0.05 (shrunk) on the 40, about −0.02 or +0.02
on clean, about +0.04 or +0.05 on crunch. The bar, row (c) on BKS+GOAT: the answer −0.087 [−0.155, −0.018], the shrunk
answer −0.148 [−0.201, −0.095] (both reproduced by a test at declaration); 8 of 47 parts (answer) and 2 (shrunk) at
+0.10 or worse than Cen.

**Beside, never deciding:** G and I on the pool by `row_reading`, each set, clean and crunch; `D_notes` on the pool, on
the panel by its MedleyDB and Laminar Flow files, band-weighted, with each cluster left out, and with refused parts
counted as Cen; the shrunk answer against row (c)'s full answer; the answer less the shrunk answer (declared now; row
(c)'s +0.049 was post hoc); the parts at +0.10 or worse for both arms; the share of row (b)'s gain kept; the
checkpoints; whether search-half gain predicts held G; `tr-plain`'s content checks; the stem preview (Basic Pitch on
each part's stem, search half only, against the DI's notes; it sizes the stem-notes row).

### 10c. Cost, stop rule, ledger

- **Renders:** score check 40, search check about 24, start references 94, search about 12,300 (rows (b) and (c):
  12,351 and 12,317), score 940; about 2 hours on 3 processes at row (b)'s measured re-timing rate of 6,560 an hour.
  No training, separation or MPS job.
- **Stop rule:** one build, one read. The row stops at 3 refused of the 40 deciding parts. After it, at most two more
  reads (the stem-notes row, then a blind sitting) before a product decision.
- **Ledger:** `preset-ladder` `phase_scratch_notes` (this declaration), `phase_scratch_notes_dry` (the build's sha256,
  with the install and notes hashes), `phase_scratch_notes_answers` (before `score`), `phase_scratch_notes_outcome`
  (after the audit). `phase_fs*` keys are untouched.
- **Public repo:** no settings values, audio, note files or song paths in git; answers stay under `PF/fs/notes/`.
