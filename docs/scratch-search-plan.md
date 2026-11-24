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
**2026-11-23:** the tone split, which prices the measure step's clip fault on rows (b) and (c)'s stored answers and
asks where row (c)'s loss is made, is declared in
[section 11](#11-the-tone-split-2026-11-23-ledger-phase_scratch_tone) (ledger `phase_scratch_tone`) on the user's go.
It re-scores stored answers only (846 renders) and touches no shared code. The search row `fs-tone` is held, not
declared. **Run 2026-11-23 and audited** (`phase_scratch_tone_split`): the clip moves the yardstick (Cen), not the
found presets, so rows (b) and (c) stand and are not redone (the user's decision). Declared with it: the gentle-fix CPU
check (11f, `phase_scratch_tone_gentle`, zero renders) and the clip-free re-score beside new rows (11g,
`phase_scratch_tone_beside`).
**2026-11-23:** the codec ceiling, row `fs-codec`, is declared in [section 12](#12-the-fs-codec-row) (ledger
`phase_scratch_codec`): the true DI after a latent codec's round trip (`rt-m2l`, LOUDAR's latent; `rt-dac`) drives a
50-evaluation search, read per part against rows (b) and (c) on the full pool. It does not touch rows (b) and (c),
`OUTCOME_TABLE` or `fs-notes`. Ran and audited: both codecs `FK-clear`.
**2026-11-23:** LOUDAR's second test, row `fs-loudar`, is declared in [section 13](#13-the-fs-loudar-row) (ledger
`phase_scratch_loudar`): a dry guitar LOUDAR rebuilds from the stem's search half alone drives the same 50-evaluation
search, read against row (c)'s blurred DI on BKS and the panel. Its renders wait while `fs-notes` might still run. Not run.
**2026-11-24:** the exact-notes test, rows `xn-bank`, `xn-swap`, `xn-reread` and `xn-list`, is declared in
[section 15](#15-the-exact-notes-test-rows-xn-bank-xn-swap-xn-reread-xn-list-2026-11-24-ledger-phase_scratch_exact)
(ledger `phase_scratch_exact`, with the review's amendments and the user's Go 1): on build 2's bank guitars, where
replay is exact, what share of the dry-guitar mismatch cost comes from note reading. BKS+GOAT decides, all 47 beside.
It touches no shared code. Not run.

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
  parts with non-finite blurred-DI renders were checked at the draw: none is drawn. **Retired by section 14 (S1,
  2026-11-24): no row stops on a count of refusals.**

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
| `search` | `search_row_part` (`run_part`), `load_ref_blank`, the start check at 0.005, the disk guard, at most 3 shards | The start reference: the exact first evaluation (`sx1(start)`) through `tr-di` in its own fresh primed process, just before the part's search (2 renders), written once. Every search record holds the sha256 of the dry guitar's audio as handed to the search, measured, and the search refuses before any render unless it is the hashed build's `tr-di`. A part refused by the content checks is recorded as refused, unrendered; any failing ear item stops the search. The install record (lock, model, gate and calibration sha256) is checked |
| `answers` | `answer_parts` (`borrowed`, `shrunk` at 0.5, `centre`) | Refuses a search record whose dry guitar is not the `tr-di` of the build hashed as `phase_scratch_notes_dry`. The refusal stop counts the 40 deciding parts (3 or more stop), content refusals included |
| `score` | `score_row_part`: through the true DI, the held half against the clean record, the scoring control, 10 settings a part | — |
| `read` | `read_row_parts`, `nonfinite_rule`, `part_numbers`, `summarise_row`, `row_reading`, `number_reading` | `paired_reading`, `FN_TABLE`, `fn_code` |
| Guards | `never_overwrite` on every output; the hashes of the draw, the build and the answers | `redo_on_main`: `learn/scratch_search.py`, `scratch_notes.py`, `note_rebuild.py`, `note_rebuild_s1.py`, `note_rebuild_ear.py`, `note_transcribe.py`, `bp_run.py` and the keys `phase_fs*`, `phase_scratch_notes*`, `phase_nr*` equal main's. Every command needs `phase_scratch_both_outcome`, `phase_scratch_notes` and `phase_nr_1_redo` on main; `search` both checks passed and the install, notes and build hashed; `answers`, `score` and `read` `phase_nr_1_redo_ear` = ok, heard on clips from the hashed build |

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
clear of zero (the halves' half-widths in quadrature); otherwise "not separable by these figures". Beside it,
computed inside the one read: `D_notes` by `ring-kept`'s figure, by the share of bent notes and by the share of
chords (Spearman's rho, and each half at the figure's median with its own interval).

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

## 11. The tone split (2026-11-23; ledger `phase_scratch_tone`)

Declared 2026-11-23, before anything in it renders, on the user's go ("Run the quick check", asked by AskUserQuestion
on 2026-11-23): price the clipping fault now, at about 846 renders; the tone-search row stays held unless a real
rebuild shows a fixed tone error; whether to fix the clip itself stays the user's decision after the result. Track 4 of
the 2026-11-22 research report, after an independent review (changes needed) and its re-review (approve with changes
A to D, all taken). Code: `learn/scratch_tone.py`; tests: `tests/test_scratch_tone.py`. Data: `PF/fs/tone/`.

### 11a. The question

1. **What does the measure step's fault cost, by the score?** The scoring DI is meant to carry an average guitar's
   balance. `song_bank.measure` asks for the gain `avg − (own − own.mean())` and `direc_check.eq_to` clips it at
   ±15 dB. The gain is centred over 0 to 24 kHz, not in band, so its mean from 80 Hz to 8 kHz is −7.5 dB on the 40
   (−17 to −1) and 13% of in-band bins clip on average (up to 65%). The coded DI so sits 2.7 dB from the average
   balance on the 40 (max 7.1); without the clip, 1.3 dB (max 2.0). How far do rows (b) and (c) move when their stored
   answers are scored through a correctly balanced DI? Would a fix need those rows redone (about 26,000 renders),
   re-scored only, or nothing? The decision on the fix is the user's, afterwards.
2. **Where is row (c)'s loss made?** How much of it is the dry guitar's static tone carried to the true DI (the average
   balance, the planted tilt), and how much is everything else. `fs-notes` and the codec row need this beside their
   own reads.

**How it differs from what came before.** Nothing priced the measure step: `docs/ml-deep-review-2026-11.md` noted the
clip with "its effect on renders is unmeasured". Nothing separated row (c)'s loss: row (c) and its audit give one
number for the blur. The split is not a search. It makes no new dry guitar for a search and no new answer; it re-reads
answers that are already hashed.

**Why the search row `fs-tone` is held.** By the user's average-guitar yardstick the scoring DI is the take's DI
re-equalised to an average guitar's balance, and a rebuilt DI is finished the same way (`note_rebuild.rebuild_redo`:
the measure step, then `average_balance`). So a real rebuild has no static tilt for a search to find. On avg+mild the
target would be the planted ±3 dB a decade tilt plus the measure step's fault. `fs-tone` is reconsidered only if all
three hold: the user has decided on the measure step; a real rebuild shows a static tone error against a correctly
balanced scoring DI (`tr-di`'s long-term spectrum against `true-noclip`, CPU only, once its builds exist); and the
split's `C_planted` shows the planted tilt is not the whole of `C_tilt`. No `fs-tone` code, hook or search record
exists; `phase_scratch_tone_hook`, `_answers` and `_outcome` are held with it.

### 11b. What is rendered

Rows (b) and (c)'s stored, hashed answers on all 47 parts (the user's pool: BKS, GOAT and the panel), each through the
dry guitars below, primed alone, judged on the held half against the clean record. 18 renders a part, 846 in all.

| Dry guitar | What it is | Rendered through it |
|---|---|---|
| `true`, the coded true DI | as rows (b) and (c) were scored | Cen: the control, which must repeat both rows' stored value and render sha256 exactly |
| `true-noclip` | the raw section through the measure step with the clip removed in every bin, at −22.9 LUFS: the candidate fix | Cen, answer (c), answer (b) |
| `avg` | stored: the true DI with the average balance as the blur and `tr-di` carry it; no bleed | answer (c) |
| `true+planted` | the coded true DI with exactly the seeded ±3 dB a decade tilt, its sign from the blur's seed | answer (c) |
| `true+tilt` | the coded true DI with avg+mild's truth-fitted tilt, clipped to ±8 dB a decade | answer (c) |
| avg+mild | stored: the search's own dry guitar | Cen, answer (c) |

- **The judge's DI is the coded true DI every time,** so the scored frames never change and only the render differs
  between readings. This is a declared deviation from a fixed yardstick: a real fix would also hand the judge the fixed
  DI, which moves its frame floor slightly.
- **The tilt form:** gain in dB = s × clip(log10(f / 1 kHz), −1, +1), applied with `di_robustness.apply_gain_db` and
  brought back to the input's RMS (at s = 3 times the sign it is `degrade`'s tilt exactly). Fitted by least squares on
  81 geometric points from 80 Hz to 8 kHz, on spectra by `smoothed_spectrum` over the whole section.
- **`true-noclip`** is a new function, `scratch_tone.no_clip_measure`: `song_bank.measure`'s gain, interpolated and
  applied as `eq_to` does, without the clip, then `to_lufs`. `song_bank.measure` and `direc_check.eq_to` are unchanged:
  every stored value depends on them.
- **It is not a mild change.** On the 47 parts the in-band ask, centred in band, reaches +37 and −30 dB and goes beyond
  the EQ's ±12 dB reach on 38 of them. The boost above 8 kHz is +21 dB on average (up to +33), below 80 Hz up to
  +26 dB. Energy above 8 kHz rises 3.1 dB on average against the coded DI (up to 13.4), the peak at the same loudness
  1.6 dB (up to 9.8). These change what a driven amp sees and may lift hiss and hum. Another fix (a wider clip, a
  second pass) is not measured here and would need its own read.
- With the `mild` arm dropped, the blur's non-tone parts (smear, soft clip, bleed) are **not priced on their own**.
  They show only inside `C_blur`, with the tone.

**The fit (zero renders, run before this declaration).** `learn.scratch_tone fit` builds `true-noclip`, `true+tilt`
and `true+planted` per part (`PF/fs/tone/dry/v1/`, 3 × 47 files, about 280 MB) and hashes them with the coded DI and
the two stored guitars in `PF/fs/tone/fit-v1.json`. The declaration names its version and sha256; a changed fit writes
the next version and never overwrites. It took 62 s of CPU and reproduces the planning and review numbers (a test
holds each):

| Fact | Number |
|---|---|
| avg+mild's error against the coded true DI, RMS over parts and grid, before and after the fitted tilt | GOAT 3.69 → 2.10 dB (about two thirds of the variance); the 40 3.34 → 2.06 |
| Fitted slopes inside ±8 dB a decade | 38 of 40 |
| The planted sign against the stored `mild` file's fitted slope | the same on 40 of 40 |
| Distance from the average balance: raw, coded, without the clip (the 40) | 7.7, 2.7 (max 7.1), 1.3 dB (max 2.0) |
| The clip residual (the coded DI against `true-noclip`) | 2.1 dB on average, max 7.0 (the 40) |
| The stored `avg` against `true-noclip` and against the coded DI | 1.15 and 2.43 dB on the 40; 0.84 and 3.07 on the panel |
| The `avg` a fixed pipeline would build, against the stored `avg` and against `true-noclip` (47 parts) | 1.03 dB (max 1.53), and 0.65 dB |
| Beyond the EQ's ±12 dB reach | 38 of 47 |
| φ from the stored EQ answers (the review's regression, octave bands assumed) | 0.29 GOAT clean, 0.44 the clean 20, 0.00 crunch |

### 11c. The numbers

**The fault's price** (in each dry guitar's own terms: the answer against Cen, both through that guitar):
- `P_c` = G of row (c)'s answer through `true-noclip`, less its stored G. Below zero: row (c) reads better under a
  correctly balanced DI, so the stored number carries the fault.
- `P_b` = the same for row (b)'s answer. Above zero is expected if row (b)'s answers are tied to the coded DI.
- **The share restated on one yardstick:** row (c)'s G over row (b)'s G, both through `true-noclip`, beside the stored
  47%. Row (c) re-scored over row (b) stored is shown only as a figure labelled **mixed**.
- Beside: Cen's own shift between the two DIs; `P_c` and `P_b` against each part's clip residual (Spearman's rho, and
  the two halves at its median), which checks the mechanism by render; `P_c` and `P_b` on the parts beyond the EQ's
  reach and on the rest, with each group's rise in energy above 8 kHz and in peak.

`P_c` needs no assumption about φ, but as a stand-in for a redo of row (c) it is **approximate and conservative**: a
fixed pipeline's `avg` differs from the stored one by 1.03 dB (max 1.53) and sits 0.65 dB from the clip-free DI, so a
redo's dry guitar would sit nearer the scoring DI than the stored one does. `P_c` understates the change a redo would
show, with the redo's search noise on top.

**Where the loss is** (answer (c) through the other guitar, against the same answer's stored value through the coded
true DI):
- `C_fix` and `C_avg`: the average balance, by the fix and by the stored `avg`; −`C_avg` is the average balance's cost,
  and the two should agree. **The average balance's cost gets its own line to the user and the ML session, whatever
  the codes.**
- `C_planted`: the planted tilt alone, the synthetic share. `C_tilt`: the truth-fitted tilt; `C_tilt` less
  `C_planted` is what the tilt holds beyond the planted one.
- `C_blur`: everything, through avg+mild. Beside it, row (c) in its own terms (through avg+mild against Cen through
  avg+mild).

**The C numbers depend on φ,** the share of a blur component the answer inverted: 1 when the answer cancels it exactly,
0 when the answer did not move, below 0 when it moved the wrong way. For a component of size e, the answer is off by
φ·e through the true DI and by (1 − φ)·e through the blurred one. Under a quadratic loss row (c)'s realised cost is
about φ²·e², while C reads about (1 − 2φ)·e² (below zero: better through the blurred guitar). At φ = 1 C is exactly
minus the realised cost; under φ = 0.5 C reads zero or above although a correction before the search would help. So
the C numbers are conservative bounds, and every stop they suggest is worded **"not shown by the split"**. φ is
reported beside every code: by render per part (the long-term response of answer (c) less answer (b), both through
`true-noclip`, projected on avg+mild's error, inverted; no extra render), and from the stored EQ answers.

**Read on:** the pool; BKS+GOAT; each set; clean and crunch; the parts whose answer has no drive or compressor active
(12 of the 40 in row (c), the panel adds 3; only this group is called the exact case); and the reach groups. A
non-finite render takes the declared B3 rule inside its dry guitar (`nonfinite_rule`; a dry guitar without a Cen render
takes the coded Cen); none occurred in rows (b) and (c).

### 11d. The codes (coded and tested before any render)

**The measure step: two independent readings, one per row, on the pool.** `P_c` reads row (c) and `P_b` row (b);
neither changes the other's code. Each reads **level** (its interval inside ±0.05), **moves** (its interval clear of
zero with the mean at 0.05 or beyond, either way) or **undecided** (anything else; undecided is not failed).

| Code | When | What it tells the user |
|---|---|---|
| `MC-c-level` | `P_c` level | Row (c)'s stored number stands under the fix, as far as re-scoring can show (it is conservative) |
| `MC-c-moves` | `P_c` moves | Row (c) carries the fault. Its restated number comes from this split; a redo of its search would show at least this change |
| `MC-c-undecided` | `P_c` undecided | The size and interval go to the user |
| `MC-b-level` | `P_b` level | Row (b)'s stored number stands under the fix; its search needs no redo |
| `MC-b-moves` | `P_b` moves | Row (b)'s stored answers are tied to the coded DI. The re-scored number is where a redo starts: a redo should match it up to search noise. Nothing is claimed above it, and the stored G is not a ceiling: the fix moves the DI further from the raw guitar that made the record, on some parts beyond the EQ's reach, so the task may be harder. An exact row (b) needs its search redone under the fixed DI: 12,351 + 940 renders, about 1 h 59 min at the measured rates |
| `MC-b-undecided` | `P_b` undecided | The size and interval go to the user |

Read together: both level, rows (b) and (c) stand, no redo for their sake, and fixing the measure step is a
forward-only choice; (c) moves and (b) level, row (c) and the share are restated from the split and no search is
redone; (b) moves, the share on one yardstick is given from the split and an exact one waits on row (b)'s redo.
Otherwise each code goes to the user on its own line. A formal redo of both rows under a new measure step is about
26,000 renders; whether the numbers justify it is the user's call. A panel DI file lost stops the pool's MC codes
(`pool_refusal`).

**Where the loss is** (on BKS+GOAT; descriptive, it licenses no run):

| Code | When | Wording |
|---|---|---|
| `TN-reach` | `C_tilt` decided better, its mean at −0.10 or beyond | "By the split, a static tone error of avg+mild's size is worth a heard size." `C_planted` says how much of it is our own tilt |
| `TN-short` | Not the above, and one of the C numbers has its interval below zero | "The tone costs" only when that number is `C_tilt`, `C_planted`, `C_avg` or `C_fix`. When it is only `C_blur`: "the blur costs" (smear, soft clip and bleed included) |
| `TN-search` | No C number has its interval below zero | "Not shown by the split that row (c)'s loss is carried by the dry guitar." With φ under 0.5 this is expected even if it is |

### 11e. Guards, cost, who needs it

- **Guards.** `split` and `split-read` refuse unless this checkout's `learn/scratch_search.py` and
  `learn/scratch_tone.py` and its `phase_scratch_tone*` keys are main's (`scratch_tone.on_main`), and main holds
  `phase_scratch_tone` with the fit's version and sha256 and the user's go, and `phase_scratch_both_outcome`. Both
  rows' answers are refused unless their sha256 is main's (`require_hash`), with the draw's hash and C3r's state. Every
  dry guitar's sha256 is checked before the part's first render (the stored two also against `blur.json`), and every
  record carries them. The Cen control is exact; a part that misses it refuses; 3 refused of 47 stop the read. Every
  output is written once; the rows are saved before any code is read; the read happens once. At most 3 render
  processes, the 31 GB disk guard before every part, never beside a separation.
- **Shared code.** None is changed: `learn/scratch_search.py`, `learn/scratch_notes.py`, `learn/note_transcribe.py`,
  `song_bank.measure` and `direc_check.eq_to` are as on main. `phase_scratch_tone*` sits outside the guarded prefixes
  (`phase_fs`, `phase_scratch_notes`, `phase_nr`), so the redo's `redo_on_main` and `scratch_search.on_main` read
  nothing new (a test holds this).
- **Repeat use.** No search runs, so no search half is used and no answer is formed. The held halves of all 47 parts,
  read by rows (b) and (c) and later by `fs-notes`, are read again: a declared repeat use.
- **Cost (measured rates only).** 846 renders, about 13 minutes on 3 processes at row (c)'s score rate (940 renders in
  840 s). The fit: 0 renders, 62 s of CPU. Disk about 280 MB. No training, separation, MPS job or download.
- **Stop rule.** The split runs once and is read once; an independent audit recomputes every number from the per-part
  files before the results PR (`phase_scratch_tone_split`). Nothing else in this track runs without a new declaration.
- **Who needs the result.** The user: fix the measure step or not; restate, redo or leave rows (b) and (c).
  `fs-notes`: `tr-di` is average-balanced, so its own G against Cen carries the fault, though `D_notes` (paired with
  row (c)) cancels it to first order; the split's size goes beside that read, and `fs-notes` is never compared with row
  (b) without it. The codec row: its `D_blur` is biased in the codec's favour by the same size. The product: the
  measure step is also how a rebuilt DI enters it.
- **Public repo.** No part keys, settings values, audio or song paths in git; everything per part stays under
  `PF/fs/tone/`.

    $MAIN -m learn.scratch_tone split --shard 0/3    # and 1/3, 2/3: 846 renders in all
    $MAIN -m learn.scratch_tone split-read           # zero renders, once -> raw hand-back, audit, results PR

**Run 2026-11-23 and audited** ([results](scratch-search-results.md#the-tone-split-the-measure-steps-clip-priced-track-4),
`phase_scratch_tone_split`):
- **`MC-c-moves`** is Cen scoring 0.110 worse through the clip-free DI, with answer (c) level.
- **`MC-b-moves`** is at its threshold, and no action rests on it.
- **`TN-short`** comes from `C_tilt` −0.030 alone; the planted tilt and the average balance are level.
- **The user's decision (2026-11-23, in chat, "Ok"):** rows (b) and (c) are not redone; a gentler fix is priced on CPU
  (11f); new dry-guitar rows report a clip-free re-score beside the coded one (11g).

### 11f. The gentle-fix CPU check (declared 2026-11-23; ledger `phase_scratch_tone_gentle`; zero renders)

**Run 2026-11-23 and audited** ([results](scratch-search-results.md#the-gentle-fix-check-plan-11f-gv-caps),
`phase_scratch_tone_gentle_outcome`): **`GV-caps`**.
- Only `band-open` meets both distance bars, and every variant fails all five caps.
- The rise above 8 kHz is the average balance itself at fixed loudness: the balance fix's lift is inherent at fixed
  loudness; the coded clip avoided it only by leaving the balance off. So caps against the coded DI made `GV-caps` close
  to inevitable.
- It changes nothing: the measure step stays as it is, rows (b) and (c) are not redone, and 11g keeps `true-noclip`.

**Why.** The clip-free DI fixes the balance (1.26 dB from the average on the 47, max 2.05; coded 2.81, max 7.14). But
it adds up to +13.4 dB of energy above 8 kHz and +9.8 dB of peak, a hiss risk (the user's decision, item 2). The
check prices gentler versions on CPU before anything else.

**The variants** (`GENTLE`; new functions `applied_gain` and `gentle_measure`; `song_bank.measure` and
`direc_check.eq_to` unchanged). Every variant applies the measure step's asked gain as the coded step does out of band
(below 80 Hz and above 8 kHz: the coded ±15 dB clip, so no boost beyond today's there), and differs only in band:

| Variant | In band (80 Hz to 8 kHz) |
|---|---|
| `wide24` | the coded gain's frame, clipped at ±24 dB instead of ±15 |
| `centred24` | the clip window centred on the in-band gain's mean, ±24 dB about it |
| `band-open` | no clip in band (the clip-free fix in band only) |

The coded DI and `true-noclip` are computed beside as references, in the same run. Every DI is back at −22.9 LUFS.

**Measures,** per part against the coded DI, pooled as mean and max over the 47 parts:
- distance from the average balance (in band, weights 1/f, the weighted mean removed);
- the rise in energy above 8 kHz and below 80 Hz;
- the rise in peak;
- reach: whether the variant's in-band change from the coded DI's spectrum, centred in band, goes past ±12 dB.

**Beside, report only and never a bar** (`HISS_FIGURES`). The total energy above 8 kHz is dominated by played notes,
while hiss shows between them, so two hiss figures go beside:
- the rise above 8 kHz on the quietest frames (`quiet_hf_rise`): the quietest 10% of the coded DI's 50-ms frames among
  those within 60 dB of its loudest, Hann-windowed, the same frames in every variant;
- the rise from 2 to 8 kHz, where an in-band variant may boost by up to +24 dB.

**Bars** (`GENTLE_BARS`, each inclusive). A variant passes only if every bar holds:

| Bar | Bound | Clip-free | Coded |
|---|---|---|---|
| Distance from the average, mean | ≤ 1.5 dB | 1.26 | 2.81 |
| Distance from the average, max | ≤ 2.5 dB | 2.05 | 7.14 |
| Energy above 8 kHz, mean rise | ≤ 1.0 dB | +3.1 | 0 |
| Energy above 8 kHz, max rise | ≤ 3.0 dB | +13.4 | 0 |
| Peak, mean rise | ≤ 1.0 dB | +1.6 | 0 |
| Peak, max rise | ≤ 3.0 dB | +9.8 | 0 |
| Energy below 80 Hz (hum), max rise | ≤ 3.0 dB | — | 0 |

**Why these bars:**
- **Distance:** within 0.25 dB of the clip-free mean and 0.5 dB of its max, and far under the coded max. So a passing
  variant fixes the balance in the clip-free DI's sense.
- **Caps:** 3 dB is a doubling of power, the most any one part may rise above 8 kHz, below 80 Hz or in peak without a
  listen; a 1 dB mean keeps the typical change small.
- **Test:** the clip-free DI fails both caps.

**The codes** (`GV_TABLE`, `gv_code`; exactly one; tested):

| Code | When | What it tells the user |
|---|---|---|
| `GV-pass` | at least one variant meets every bar | a gentler fix brings the scoring DI near the clip-free balance without its side effects; the passing variant with the lowest mean distance is the candidate. Adopting it anywhere (the scoring DI, the product's measure step) is the user's decision, forward only, under its own declaration; it changes no stored value and licenses no render |
| `GV-caps` | no variant meets every bar; at least one meets both distance bars | the balance can be fixed only with side effects past the caps at these settings: keep the measure step as coded, or a listen to the side effects first |
| `GV-none` | no variant meets both distance bars | keep the measure step as coded; any other variant (a second pass, another target) needs its own declaration |

`GV-none` can hardly happen: `band-open` applies the clip-free gain in band, so it should meet both distance bars
nearly by construction (the clip-free DI's 1.26 and 2.05 dB). The real choice is `GV-pass` against `GV-caps`, that
is, whether any variant keeps the side effects under the caps.

**Guards:**
- `learn.scratch_tone gentle` refuses unless this checkout runs main's split code and keys (`on_main`) and main holds
  `phase_scratch_tone_gentle`.
- The coded DI is checked against fit v1's sha256 on every part.
- Every built DI must be finite and the section's length.
- Output: `PF/fs/tone/gentle-v1.json`, written once; the read happens once.

**Cost:** zero renders, CPU only. The fit's like work on the 47 parts measured 62 s.

### 11g. The clip-free re-score beside new rows (declared 2026-11-23; ledger `phase_scratch_tone_beside`; not coded yet)

**What.** For each new dry-guitar row (`fs-notes`, `fs-codec`), the row's stored, hashed settings are rendered again
through `true-noclip` (fit v1's file for the part, its sha256 checked). Each is primed alone and judged on the held half
against the clean record, with the coded DI as the judge's DI, exactly as in this split.

**Cen.** Cen through `true-noclip` is this split's stored value: the same render. As a control, Cen is rendered again
through `true-noclip` on the row's first BKS and first GOAT part and must repeat the split's value and render sha256
exactly.

**Reported** per arm:
- G through `true-noclip`, against Cen through `true-noclip`;
- the decomposition this split's audit requires: the answer's own shift, with Cen's shift beside;
- the row's number paired, arm by arm, against its partner row through `true-noclip`, beside its coded one.

**The partner is the row measured the same way.** An answer searched on a coded-like DI loses when the DI becomes
clip-free (row (b)'s answer: +0.161 [+0.072, +0.251]). An answer searched on an average-balanced DI does not (row
(c)'s: `C_fix` −0.011).
- **`fs-notes` pairs against row (c).** `tr-di` is finished with the measure step and then `average_balance`, so like
  avg+mild it is average-balanced. Against row (b) through `true-noclip` its pairing would be biased by row (b) being
  off its search DI, and is said so.
- **`fs-codec` pairs against row (b).** Each round trip is put through `song_bank.measure` (section 12), so the codec's
  dry guitar keeps the clip offset, like the coded true DI. Both are measured alike, as `D_true` is the clean one in the
  coded read. **Against row (c) through `true-noclip` its pairing is biased against the codec by about +0.15** (row
  (b)'s +0.161 off-DI loss less row (c)'s −0.011), and is said so wherever it is shown.

**Reported only; it never decides.** It never changes a row's code, threshold or recommendation. It is read once,
after the row's own read.

**It keeps `true-noclip`.** If the gentle-fix check (11f) reads `GV-pass`, this side read still re-scores through
`true-noclip`; switching it to the passing variant would need its own declaration.

**Renders** (about 1 a second on 3 processes, as this split measured). The partner's answer through `true-noclip` is
already stored in this split (row (c)'s answer and row (b)'s answer); its other paired settings are rendered once:

| Row | What is rendered again | Renders |
|---|---|---|
| `fs-notes` | the answer and the shrunk answer (47 × 2 × 2 = 188), row (c)'s shrunk answer once (94), the control's 4 | 286 |
| `fs-codec`, short row | each codec's `cp50` (47 × 2 a codec, 188 for both), row (b)'s `cp50` once (94), the control's 4 | 286 |
| `fs-codec`, full row | its answer and shrunk answer (188 a codec), and row (b)'s shrunk answer once (94, shared by both codecs) | 188 a codec, plus 94 once |

**Coded with the first row that needs it,** under this key and before that row is read.

> **Departure (2026-11-23; ledger `phase_scratch_tone_beside_departure`):** `fs-codec`'s short-row read runs before
> 11g is coded, against 11g's "before that row is read". Decided by the delegated decision agent under the user's
> standing instruction of 2026-11-23 (not the user's own answer). Reason: 11g decides nothing and its design is fully
> declared here and in the ledger, so the read can't shape it. To keep the later run blind to the read, these hold:
> 1. **Frozen now.** 11g's paired figure for `fs-codec` uses the row's own summary: `pool_summariser` on the full pool
>    (BKS, GOAT and the panel weighted equally), the same paired interval method as 12b's `D_true`, BKS+GOAT beside,
>    and for `rt-dac` the pool with the Phantom part left out beside. The control parts are the first BKS and first
>    GOAT part in draw order. Nothing else is chosen at coding time.
> 2. **Inputs only.** 11g's code reads only the hashed answers (`phase_scratch_codec_answers_m2l` and `_dac`), row
>    (b)'s stored answers, the split's stored `true-noclip` values and fit v1's built files. It never reads the codec
>    read's report, `D_true`, `D_blur` or the FK codes. A test asserts this.
> 3. **Any change to 11g's declared design** made after this read needs its own declaration. That declaration says it
>    was written after the `fs-codec` read and is reported as post hoc.
> 4. **The reviewer** of the 11g code PR checks it against this section and the ledger only, and confirms points 1
>    to 3.
> 5. **11g reads once**, after the row's read, as declared. If a full row runs (on `FK-shut`), 11g's full-row arm keeps
>    the same frozen summary.

## 12. The `fs-codec` row

Declared 2026-11-23, before anything in it runs (research track 2, "the codec ceiling"), on the user's go of
2026-11-23 ("Go as planned"), after an independent review (approve with changes; all six required items and the nits
taken) and its diff check (approve; its two text fixes are in 12d). Ledger `preset-ladder` `phase_scratch_codec`.
Code: `learn/scratch_codec.py` (the row) and `learn/codec_roundtrip.py` (the round trips, run in each codec's own
interpreter, importing nothing from this project); tests: `tests/test_scratch_codec.py`, `tests/test_codec_roundtrip.py`.
Data: `PF/fs/codec/`. Section 11 is track 4's.

**Status (2026-11-23): ran and audited.** Both codecs read **`FK-clear`** on the pool and on BKS+GOAT. On the pool,
`D_true` is +0.023 [+0.010, +0.037] for `rt-m2l` and +0.009 [−0.004, +0.023] for `rt-dac`: a weak go, "not ruled out
by its codec", for each. No full row runs.
- Ledger: `phase_scratch_codec_outcome`.
- Results, corrections and caveats:
  [results](scratch-search-results.md#the-codec-ceiling-row-fs-codec-track-2-both-codecs-fk-clear).
- Next on this track (recorded, not started): declare LOUDAR's second test, with BKS and the panel deciding.

**The question.** Before LOUDAR is downloaded or any latent DI rebuild is built: does a dry guitar that has only passed
through the codec still drive the search? One short search row per codec, driven by the **true DI after a codec round
trip**, read against row (b) (the true DI) and row (c) (avg+mild).

**What a result can and cannot say. A fail is a strong no-go; a pass is only a weak go.** On LOUDAR's own guitar test
(Fx-Encoder++ distance from the clean DI) the codec round trip scores 0.105, LOUDAR's output 0.308 and its distorted
input 0.381: most of LOUDAR's loss is in the generation, which this test does not see. The round trip is also only an
approximate ceiling: encoding the true DI does not give the decoder's best latent; the decoder's noise differs on every
sample; the prior's bias, the fitted operator, the stem and a second guitar are outside it. So a pass means "not ruled
out", and LOUDAR's second test still has to earn its result. A fail means even a perfect input does not get through;
it is final only after the full row (12b) confirms it.

### 12a. The dry guitars

| Name | Codec and setting | Role |
|---|---|---|
| `rt-m2l` | `linear-cae` 0.1.4, model `m2l` (Apache-2.0; a Music2Latent retrained by Torres et al.), **48 kHz in as it is** (LOUDAR's use), 1 denoising step, decode seed a | **Short row; decides for LOUDAR** |
| `rt-dac` | DAC 44.1 kHz, 8 kbps, 9 codebooks (weights on disk), its own venv | **Short row:** a DAC-rate latent (track 3's option, EG-VAE's family) |
| `rt-m2l-b` | as `rt-m2l`, decode seed b | Start read only: does the decoder's noise matter? |
| `rt-id` | no codec | Must equal the true DI byte for byte: the build wraps only the codec |
| `rt-rs` | 48 → 44.1 → 48 kHz, no codec | Zero-render figures only: what the resampling alone costs `rt-dac` |

`rt-sony` (GuitarFlow's SonyCSL codec) is dropped: a start read decides nothing, and its loader uses
`weights_only=False`.

- **Input.** `prep` writes per part the raw DI section (48 kHz mono, 492,000 samples with the 0.25 s before it,
  exactly `pretrain_set.section_audio`'s), then the DI file's own next second (540,000 in all), so the codec sees no
  hard end where half B stops. Measured at declaration: the 16 BKS parts get a full real next second; the 31 GOAT and
  panel DI files are 10.25-s section files that end with the section, so theirs is zeros. BKS's files are 44.1 kHz,
  and a longer read moves the section's last 10 samples by the resampling edge (by up to 0.002), so the section is kept
  from its own read and the next second taken from the longer one (`with_next_second`; a test checks all 47).
  **The lean this leaves:** the 11 GOAT and panel parts that search half B (8 + 3) see the file's real end inside the
  last latent frame of their search half, where the 7 BKS parts that search half B see real audio. That leans slightly
  against the codec on those 11 parts, so toward `FK-shut`, which gets its full row anyway. The held half's score goes
  through the true DI and is unaffected.
- **`rt-m2l`.** LOUDAR's level rule in (`loudar_gain`: the loudest 400-ms frame, hop 100 ms, `unfold` with the tail
  dropped, RMS floored at 1e-8, brought to −18 dB; one gain, read on the section only, undone after decoding); zero-padded
  to the least 4,096 k + 1,536 samples (542,208); `encode`, then `decode(z, full_length=542208)` with
  `torch.manual_seed(20261601 + 1000 s + j)` just before it (s is 0 for seed a and 1 for seed b; j is the part's index
  in sorted keys); cut to 492,000. CPU, 4 threads.
- **`rt-dac`.** As `learn/dac_roundtrip.py`: peak 0.5 in (over the input the codec sees) and restored,
  48 → 44.1 → 48 kHz by `resample_poly` (147/160, 160/147), 9 codebooks, cut to 492,000.
- **Level, and the measuring asymmetry (named, kept).** `build` applies the usual measure step to each round trip
  (`song_bank.measure`: the average-guitar balance, then −22.9 LUFS). That is how `note_replay.di_section` makes the
  true DI, and how a rebuilt DI would enter the product. It removes the codec's long-term spectral error by
  construction. avg+mild was made from the measured DI and only level-matched, so its ±3 dB tilt and its move to the
  average balance stay in row (c). The measure step's ±15 dB clip leaves a measured DI 2.7 dB on average (max 7.1)
  off the average balance (track 4's review; reproduced by a test here). The true DI and the codec DI keep that offset;
  avg+mild loses it. So **`D_blur` is biased in the codec's favour and partly credits the measure step; `D_true` is
  clean** (both sides are measured alike). Every code says which number it rests on.
- **No unsafe load.** Each weight file's sha256 is checked against `manifest.json` and the declared value before any
  load, and `TORCH_FORCE_WEIGHTS_ONLY_LOAD=1` is set before torch is imported. Nothing is loaded with
  `weights_only=False`.

### 12b. The row and the reading

**`fs-codec`** = (the codec's dry guitar, `xlnoG`). Same draw (`phase_fs_draw`, 47 parts), Cen, halves and stored lag
as rows (b) and (c). The codec DI is the dry guitar of every render and the judge's DI; the reference is `xlnoG@-3`
with everything outside the search half zeros (`load_ref_blank`).

- **Search:** `scratch_search.run_part(budget=50, step1_only=True)`: 1 priming render and exactly the first 50
  evaluations of a 200-evaluation search (`coord_search` uses its budget only as a cap; a test shows it on all 3 amps).
  The start check's reference is the part's start read (12c). The dry guitar's sha256 is measured from the audio
  handed to the search and must be the hashed build's. `budget_used: 50` is recorded (`run_part` writes `budget: 200`).
- **The answer:** the 50-evaluation incumbent `cp50` (`best_index` under the peak bound), as rows (b) and (c) define
  it. `answers` reads checkpoint `"50"` only: in a short record `"100"` and `"200"` equal it and are refused.
- **Score:** `scratch_search.score_row_part` unchanged: Cen and `cp50` through the **true DI**, each primed alone,
  judged on the **held half** against the **clean record**, with the scoring control (Cen within 0.005 of its stored
  value). 4 renders a part.
- **`G50`** = ln(cp50 / Cen) on the held half; a non-finite cp50 reads as Cen, counted. Paired per part (Cen is the
  same render in all three rows): **`D_true`** = G50(`fs-codec`) − G50(`fs-stem`), what the codec costs against the
  true DI (zero is transparent); **`D_blur`** = G50(`fs-codec`) − G50(`fs-both`), the ceiling against avg+mild as
  measured (below zero, the ceiling is above the blur). Rows (b) and (c)'s G50 come from their hashed answers' score
  files. A test reproduces (c) less (b) at the checkpoint, +0.141 [+0.102, +0.180] on the pool and +0.157 [+0.108,
  +0.206] on BKS+GOAT, and G50 of −0.271 and −0.130.

**The checkpoint, and what it understates.** It was chosen because, of the stored reads, it separated (c) from (b)
most sharply on these same held halves. It compresses differences: (c) less (b) grows from +0.141 at 50 evaluations to
+0.167 at the final answer, **+0.026** (row (b) gains −0.044 after the checkpoint, row (c) −0.018), so a weaker dry
guitar falls further behind later. It leans `D_true` toward `FK-clear`, and `D_blur` toward `FK-shut` or undecided.
Every report carries this note. The calibration rests on one pair of rows.

**`FK_TABLE`** (on the full pool; the first that holds):

| Code | When | Reading | What follows (a recommendation; nothing continues on its own, except the full row) |
|---|---|---|---|
| `FK-clear` | `D_true`'s upper end under +0.10 and its mean under +0.05 | At the checkpoint, a cost of 0.10 or more against the true DI is ruled out; a cost of 0.05 to 0.10 is not. Rests on `D_true` | **The route is not ruled out by its codec.** A weak go: LOUDAR's second test may be proposed, under its own declaration, timed on one clip first |
| `FK-above` | `D_blur`'s whole interval below zero and its mean at −0.05 or beyond | The ceiling is above the blur **as measured**, at the cost `D_true` shows; "by a heard size" only at −0.10 or beyond. Rests on `D_blur`, with the measure caveat | **Not ruled out, with little room.** A weak go, weaker than `FK-clear`: a rebuild that loses more than the room left lands at the blur |
| `FK-shut` | `D_blur`'s lower end at −0.05 or above | Even a perfect input leaves no readable gain over the blur, although `D_blur` favours the codec. Rests on `D_blur`, with the measure caveat | **The full row runs first.** If it confirms, the route is **parked**, not closed; audited adversarially before any park is written |
| `FK-undecided` | anything else | Not decided; undecided is not failed | To the user with the interval and what it rules out |

`FK-above` and `FK-shut` cannot both hold (a test on a grid of intervals). The window is narrow: at the checkpoint the
true DI reads G50 −0.271 and the blur −0.130 on the pool, so a codec has 0.141 of room. `FK-clear` needs it to keep
about 82% of row (b)'s gain, `FK-above` about 66%.

**What each codec's code covers** (`covers`, printed with every code):

| | `rt-m2l` | `rt-dac` |
|---|---|---|
| Covers | `m2l` fed 48 kHz: LOUDAR as released, and anything built in that latent used that way (GuitarFlow retrained on `m2l` included) | A rebuild in DAC's latent at 8 kbps: track 3's DAC option, and a codec of EG-VAE's family |
| Does not cover | GuitarFlow as published (SonyCSL weights at 44.1 kHz); `m2l` fed at its trained 44.1 kHz; any other codec | DAC at fewer codebooks; DAC-VAE itself; any 12-Hz latent |
| A weak go means | LOUDAR's second test may be proposed | Track 3 may consider DAC's latent, once `fs-notes` and its own gate say a guided rebuild is wanted |
| A park means | No LOUDAR download; no rebuild in `m2l` at 48 kHz | Track 3 stays in the waveform |

**The full row, only after `FK-shut`** (either codec; declared and coded now, so nothing is designed after a result).
`search-full`, `answers-full`, `score-full` and `read-full` refuse unless that codec's short report reads `FK-shut`
from answers hashed on main. The codec's dry guitar runs the whole search from scratch (step 1 at 200, then step 2)
through `search_row_part`, `answer_parts`, `score_row_part` and `read_row_parts` unchanged. Its first 50 evaluations
must equal the short row's exactly (`answers-full` refuses otherwise). Each arm (the answer and the shrunk answer) is
read by the same table against rows (b) and (c)'s same arm. **The park stands only if both arms read `FK-shut`**;
otherwise the more favourable arm's code (clear, above, undecided, shut, in that order) is the row's code, said as
coming from the full row (`park_code`). About 13,260 renders, about 2 hours. A full row is not proposed for the other
codes: its paired interval was wider than the checkpoint's in rows (b) and (c).

**The park, and its lift.** `FK-shut` compares with avg+mild, which itself needs the true DI; a song gives no such
blur. So a confirmed `FK-shut` parks the route: nothing is downloaded or built for it now. **The park lifts, to the
user,** when `fs-notes` is read and its best arm is 0.05 or more worse than the codec's best arm (paired on the pool,
BKS+GOAT beside; zero renders; `park_lifts`, which requires the pool's summariser `pool_summariser` and has no
plain-mean default).

**The deciding set: the full pool** (BKS, GOAT and the panel weighted equally), for both codecs, with BKS+GOAT beside
and the same table read there. A code that holds on one and not the other goes to the user.
- `rt-m2l`: no overlap with the pool is known. The retrain's default data config lists Jamendo, M4Singer, MoisesDB, DNS
  clean speech and E-GMD; whether the released weights used exactly that config is not checkable without downloads.
- `rt-dac`: DAC trains on MUSDB18's train split, Jamendo and AudioSet. **The split was checked at declaration.** The
  `musdb` package holds no train or test list (only its `validation_tracks`), so it was read from sigsep's own
  published files: the 150-track list and the SiSEC 2018 test submissions (50 tracks, the same in all 31
  submissions). "BKS - Bulldozer" and "BKS - Too Much" are in **test**; "BigTroubles - Phantom" is in **train**, and not
  among `validation_tracks`. That is as expected. MUSDB holds only mixes and four stems, so DAC heard that guitar
  processed inside "other", never its DI. `rt-dac` keeps the full pool; beside it, the pool with the Phantom part left
  out (the panel on its two other DI files), and BKS+GOAT. Switching to BKS+GOAT would be wrong: BKS is in MUSDB18 too.
- The pool rule stays: a lost panel DI file stops the row, to the user (on G50, `D_true` and `D_blur`). The refusal
  stop is 3 of 47.

**Beside in every report, never deciding:** the compression note; the measure caveat; `covers`; G50 by set and class;
the share of row (b)'s G50 kept (row (c) keeps 48% on the pool); `D_true` and `D_blur` by class, with each cluster left
out; for `rt-dac`, the Phantom-left-out pool; `D_blur` against the true DI's clip residual (Spearman); the parts at
+0.10 or worse than Cen; the start read per dry guitar (ln(start value / the draw's true-DI value); avg+mild's is
+0.293 and ranks its per-part cost at +0.70, post hoc); Spearman of `D_true` against each zero-render figure and the
start read; the search-half gain against held G50.

**The zero-render figures** (`figures.json`, from `build`; descriptive, never deciding), per part and dry guitar
against the true DI, whole and per half, each paired against avg+mild's: the floored log-mel distance at 256 and 2,048
samples, the 5-ms envelope distance and the crest change (the planner's probe's definitions; a test reproduces
avg+mild's anchors of 2.486, 3.050, 1.995 and −0.686 dB); before the measure step, the long-term spectral distance of
each raw codec output from the raw section; the measured DIs' offset from the average balance (the true DI, each codec
DI, avg+mild); `rt-m2l-b` against `rt-m2l`; and `rt-rs`. No zero-render check decides: within avg+mild a floored
log-mel distance ranks the per-part cost at +0.52 to +0.56, and a codec errs differently.

### 12c. Guards, steps and cost

- **Guards** (every command): `scratch_search.on_main` (`learn/scratch_search.py` and the `phase_fs*` keys equal
  main's); `learn/scratch_codec.py` and `learn/codec_roundtrip.py` equal main's; the `phase_scratch_codec*` keys equal
  main's; main's blob of `learn/scratch_search.py` is `2420043a4483a482925bed5b87e54692619a305d`, the one `fs-notes`'
  checks passed on (otherwise an amendment first; section 14's amendment re-pins it to `b66af002…` and L1 to
  `6687a5dc…`, its search and score path unchanged); main holds `phase_fs`, `phase_fs_draw`,
  `phase_scratch_both_outcome`
  and `phase_scratch_codec`; `fs-notes`' two checks passed, their result files' sha256 `727fda89…` (score) and
  `172e1c9f…` (search). Render commands also: `no_separation_beside`, the render-slot cap, the disk guard before every
  part, C3r's state equal to the draw's, `never_overwrite` on every output. `start`, `control` and `search` need
  `phase_scratch_codec_dry`; `search` needs the control passed; `score` and `read` need the answers' phase. This row
  edits neither `learn/scratch_search.py` nor `learn/scratch_notes.py`. Its keys sit outside `phase_fs*`,
  `phase_scratch_notes*` and `phase_nr*`, so no other row's guard sees them.
- **Steps:**
  1. Unit 0, install and smoke (no repo change, CPU): both venvs, the weights, one part round-tripped twice per codec
     with the same seed (byte-equal), seconds a part recorded.
  2. `prep` → the round trips in each venv → `build`: `rt-id` equal to the true DI on 47 of 47; finite, 492,000
     samples; −22.9 LUFS within 0.25 LU, every value recorded with the true DI's beside (the true DI itself reads up
     to 0.121 LU off on 3 of 47 parts, pyloudnorm's gate after one gain; a missed measure step sits about 12 LU off);
     the timing offset by the 1-ms envelope within 1 ms (3 or more parts beyond it stop the build). Every check runs
     before anything under `rt/` is written; a refusal leaves only a `build-stopped-<time>.json` with every value →
     hash PR `phase_scratch_codec_dry`, with unit 0's measured seconds a part.
  3. `start` (`rt-m2l`, `rt-m2l-b`, `rt-dac` on all 47; `rt-id` on the 2 check parts) → `control`: `rt-id` at a budget
     of 10 through this row's search path must equal row (b)'s stored curves, and its start values the draw's true-DI
     values within 0.005.
  4. `search --name rt-m2l` (3 shards, `--first 2` first to re-time) → `answers` → hash PR
     `phase_scratch_codec_answers_m2l`; meanwhile `rt-dac`'s search and answers → hash PR `..._answers_dac`; `score`
     and `read` for each once its hash is on main.
  5. On an `FK-shut`: that codec's full row (`..._answers_<m2l or dac>_full`).
  6. Raw hand-back, the audit (an `FK-shut` adversarially, before any park is written), results PR
     `phase_scratch_codec_outcome`.
- **Cost (measured rates):** start reads 282, controls 26, each short search 47 × 51 = 2,397 (1.51 process-s a render,
  about 20 minutes on 3 processes), each short score 188: **5,478 renders for both codecs, about 50 minutes of slot
  time**. Only after an `FK-shut`: about 13,260 for that full row, about 2 hours. Codec CPU time is not measured on this
  Mac until unit 0 times one part; nothing is promised before that.
- **Slots:** first ready, first run; a search in flight keeps its 3 slots. This row goes first if `fs-notes` is not
  ready; if it is, `fs-notes` goes first and the codec pieces fill its hash-merge gaps. Against track 4, whichever is
  declared and reviewed first runs first. The CPU round trips use no render slot and run when no render job runs.
- **Repeat use.** The 47 held halves were read by rows (b) and (c), and `fs-notes` will read them. Nothing here is
  chosen on the new row's held values: codec, setting, seed, level rule, checkpoint and table are fixed now. The
  checkpoint was chosen from rows (b) and (c)'s stored reads because it was the sharpest of them, on these same held
  halves. That is a choice made on the comparators, and it is declared.

### 12d. Downloads and environments (named; under the user's standing approval, confirmed 2026-11-23)

**`codec-venv`** (`~/ndsp-presets/tools/codec-venv`, CPython 3.12 from pyenv; `rt-m2l`, and LOUDAR later):

| What | Size | sha256 | Licence |
|---|---|---|---|
| `torch-2.10.0-2-cp312-none-macosx_11_0_arm64.whl` (pinned by file; the plain cp312 build has another hash) | 79,498,202 B | `13ec4add8c3faaed8d13e0574f5cd4a323c11655546f91fbe6afa77b57423574` | BSD |
| `numpy-1.26.4-cp312-cp312-macosx_11_0_arm64.whl` | 13,685,868 B | `03a8c78d01d9781b28a6989f6fa1bb2c4f2d51201cf99d3dd875df6fbd96b23b` | BSD |
| `linear_cae-0.1.4-py3-none-any.whl` (needs `PyYAML`, `huggingface_hub`, `matplotlib>=3.10.1`, `soundfile>=0.13.1`) | 29,437 B | `29e5e9d41fa110eeb94d0867625ebeb75eb19ceafabd8419ed59ba36fb0dd69e` | Apache-2.0 |
| `m2l` weights `1511f18a_weights/autoencoder_inference_model_last.pth` (+ 3 YAML files of 187, 88 and 639 B) | 232,976,270 B | `405499f959fbbe38496fa2c0cc5663b495058a353157304006bff5bfced5b20b` | Apache-2.0 |

**`dac-venv`** (`~/ndsp-presets/tools/dac-venv`, the system Python 3.9.6 with torch 2.8, the combination step 0c ran
on; its own venv, so a clash cannot cost `codec-venv`):

| What | Size | sha256 | Licence |
|---|---|---|---|
| `torch-2.8.0-cp39-none-macosx_11_0_arm64.whl` | 73,610,795 B | `e9f071f5b52a9f6970dc8a919694b27a91ae9dc08898b2b988abbef5eddfd1ae` | BSD |
| `torchaudio-2.8.0-cp39-cp39-macosx_11_0_arm64.whl` | 1,853,118 B | `522289e2cd57e79401fd5ccae9b1bc0ff2e47f3529092adf5acf57427ea0c6a9` | BSD |
| `descript_audio_codec-1.0.0-py3-none-any.whl` | 26,933 B | `7ecd1883040613d143494f27f199c11c7053a8a7f9fd2120568c5a98db926e61` | MIT |
| `descript_audiotools-0.7.2-py2.py3-none-any.whl` | 106,704 B | `bb7a4e837f92395e43894d99a89406485325b88c6f158caf59e18876cf5b06ea` | MIT |
| The rest of DAC's set: about 88 packages, about 207 MB by a walk of PyPI's metadata; fixed by the resolver's report | | at install | mixed open |
| DAC weights, already on disk (`~/.cache/descript/dac/weights_44khz_8kbps_0.0.1.pth`) | 306,717,287 B | `a88eed82a7024ccc1facdb1e605c4c2f99281c8118c22c9895ffa846d8fb61aa` | MIT |

- **The `tensorboard` constraint.** `descript-audiotools` needs `protobuf<3.20` and `tensorboard`; importing `dac`
  imports `torch.utils.tensorboard`, so `tensorboard` cannot be dropped. Only the newest `tensorboard`, 2.21.0, needs
  `protobuf>=6.31.1`; 2.20.0 and 2.19.0 need only `protobuf>=3.19.6,!=4.24.0`, on Python 3.9 or later. So the dry run
  pins **`tensorboard==2.20.0` and `protobuf==3.19.6` as constraints**, which makes it deterministic: in the empty
  `dac-venv`, `pip install --dry-run --ignore-installed --report dac-resolve.json -c dac-constraints.txt torch==2.8.0
  torchaudio==2.8.0 descript-audio-codec==1.0.0`, with `dac-constraints.txt` holding those two lines.
- **DAC's exact package list goes to the user before its install** (the user's go: DAC gets its own setup, its list
  first). A DAC install failure drops `rt-dac` (reported); `rt-m2l` does not wait for it.
- `~/ndsp-presets/tools/codec-models/manifest.json` names every file as `{"files": {key: {url, size, sha256,
  licence}}}`, with keys `m2l/<file name>` and `dac/<file name>`. The round trips refuse a weight file whose sha256 is
  not both the manifest's and the declared one. `m2l`'s four files are fetched with `hf_hub_download` under
  `HF_HOME=~/ndsp-presets/tools/codec-models/hf`, checked before any load, then used with `HF_HUB_OFFLINE=1`. The
  round trips set `HF_HOME` to `<--models>/hf` themselves and refuse an `HF_HOME` set elsewhere or a missing cache.
- Not in this plan: LOUDAR's `GuitarFx-175000.pt` (1,083,089,737 B), only after a go and under its own declaration;
  `music2latent` 0.1.8 and SonyCSL's weights (dropped).

### 12e. What it can't say

- How LOUDAR, GuitarFlow or any rebuild itself performs: a pass leaves the route open and proves nothing about its
  generator.
- GuitarFlow as published, `m2l` at its trained rate, or any codec, bitrate or latent rate but the two read.
- Anything from a stem, a mix, a released record, or by ear.
- The final answer after 262 renders, unless the full row ran.

## 13. The `fs-loudar` row

**Status (2026-11-24): ran; the main read audited.** The row reads **`FL-undecided`**: `D_blur` +0.067 [−0.090,
+0.225] on BKS+panel; `D_true` +0.192 [+0.060, +0.324]; G50 −0.051. `ld-rec` reads `FL-undecided` too, level with
`ld-stem` (+0.015 [−0.166, +0.197]), audited (confirmed with corrections): on these mixes, which have no other
guitar, separation is not what limits LOUDAR; its own rebuild is the larger limit (clearly on BKS).
- Ledger: `phase_scratch_loudar_outcome`.
- Results, corrections and caveats:
  [results](scratch-search-results.md#loudars-second-test-row-fs-loudar-track-2-fl-undecided).

Declared 2026-11-23, before anything in it runs (research track 2, LOUDAR's second test, the step the codec ceiling's
audit recorded). The independent review came back APPROVE WITH CHANGES, with no blockers; its six required changes
and its nits are built in below. Ledger `preset-ladder` `phase_scratch_loudar`. Code: `learn/scratch_loudar.py` (the
row) and `learn/loudar_run.py` (LOUDAR's runs, in its own venv, importing nothing from this project); tests:
`tests/test_scratch_loudar.py`, `tests/test_loudar_run.py`. Data: `PF/fs/loudar/`.

**The question.** Does LOUDAR, as released, turn a song's separated guitar into a dry guitar that drives the preset
search at least as well as the blurred true DI (avg+mild, row (c), the bar), on guitars its prior never saw? This is
the first row with **no true DI anywhere in its input**: LOUDAR hears only the stem `xlnoG@-3`. If it reaches the bar,
it is the first dry guitar from the song alone to do so. If it does not, `ld-rec` names the bottleneck.

**A pass here is still on a stem from a mix with no other guitar.** Said to the user with any result.

### 13a. The dry guitars

| Name | What it is | Parts | Role |
|---|---|---|---|
| `ld-stem` | LOUDAR's output from the stem's search half, measured on the clip, placed on the DI's timeline | BKS 16 and the panel 7; GOAT 24 beside, only if it fits the cost stop | **Short row; decides** |
| `di-cut` | The raw true DI cut to the same span, then measured on that clip (the same way as `ld-stem`) | BKS and the panel, 23 | Short row: the cut's own cost |
| `stem-in` | The stem's search half itself, measured, as the dry guitar | 23 | Short row: the null (does LOUDAR beat its own input?) |
| `ld-rec` | LOUDAR's output from the clean record's search half (no separation) | 23 | Short row, after the main read **on any code** (13f, L1): is the stem the bottleneck? |
| `ld-stem-b` | As `ld-stem`, second sampling seed | 23 | Start read only, and only if the cost stop allows |
| `di-whole` | The true DI, uncut | the 2 check parts | The control's only |

- **LOUDAR hears only the search half** (216,000 samples: 1.0 to 5.5 s or 5.5 to 10.0 s, the span `blank_plan` leaves
  the search). The held half of the stem never leaves the main environment. In the product LOUDAR would hear the
  whole window, so this test is slightly hard on it; `di-cut` measures by how much. (The delegated decision agent's
  choice under the user's standing rule of 2026-11-23, not the user's: yes, confidence 0.65.)
- **LOUDAR as released:** its guitar checkpoint and code at commit `9f3bd165`, unchanged: the `m2l` latent, the DiT
  prior, the low-rank causal operator fitted per clip, 300 steps, on the CPU at 4 threads. LOUDAR's own level rule in
  (the loudest 400-ms frame at −18 dB), zero-padded to 218,624 samples (not the stem's next audio, which is the held
  half), the output cut back. `WANDB_MODE=disabled`, `ENABLE_TORCH_COMPILE=0`.
- **Seeded per clip:** the operator's seed is set before the operator is built, then the run's before sampling, then
  the decode's before decoding (`loudar_run.seeds`); a rerun gives the same bytes.
- **The setting** (released: 1 operator update a step, AdamW 1e-3, weight decay 0.1; or the paper's: 10 updates, 1e-4,
  1, re-read from arXiv 2608.01972 section 3.1) is chosen in unit 0 on the authors' examples (13d).
- **Out:** each clip goes through the measure step on the clip (`song_bank.measure`), then is placed on the DI's
  timeline: record sample t goes to DI sample t − lag − 52 + 12,000 (the stored lag, the plugin's latency and the
  section's 0.25 s before), cut at the section's ends, zeros elsewhere. The stored lag was estimated against the true
  DI, which a song would not have; it is used as every row uses it. No timing is read from the true DI.
- **The timing check** (the codec row's rule, as a check, never as a correction): the 1-ms envelope's lag of each placed
  dry guitar against the true DI inside its span. Over 1 ms on 3 or more deciding parts for any of LOUDAR's dry
  guitars (`ld-stem`, `ld-stem-b`, `ld-rec`): the build stops, and the question goes to the user before any render.
  `stem-in`'s lag is reported beside and never stops the build: it is an amped signal, whose envelope's lag against
  the DI can differ for reasons other than timing.

  **Settled 2026-11-23 (ledger `phase_scratch_loudar_timing_amend`), after build's declared timing stop**, by an
  isolated decision agent under the user's standing rule for technical calls, option (a), about 0.8 confidence; not
  the user's own answer. The record is the handover's `decisions/loudar-timing-stop.md` (sha256 `f2beba24…acde`),
  and its diagnostic is `loudar-unit0/timing-subwin.json` (sha256 `d7f2f8ec…b8b0`, zero renders).
  - *What fired:* beyond 1 ms on `ld-stem` 9 of 23 deciding parts, `ld-stem-b` 10 of 23, `stem-in` 2 of 23.
  - *What the diagnostic found:* no part has a consistent offset over 1 ms for any name; every name's median
    whole-clip lag is 0 ms, so the placement is right. The readings sit near multiples of 11 to 12 ms (the low
    strings' pitch period): the 1-ms envelope slips a cycle on regenerated audio, and onsets jitter.
  - *What changes:* the 1-ms check is **report-only** for every name; `build.json` keeps the parts beyond, and
    `figures.json` keeps each part's whole-clip lag per name. One **placement stop** stays: if the median whole-clip
    lag over the deciding parts of any placed name (`ld-*` or `stem-in`) is beyond ±2 ms, build stops and writes
    nothing (a padding, latency or lag bug, not the generator). No other new measure.
  - *The caveat, in the read and in `ld-rec`'s read:* the row prices LOUDAR's timing and timbre together, so an
    `FL-short` or `FL-null` alone does not say which fell short. The per-part lags are printed beside the per-part
    G50 and never decide. J0 renders each answer through the true DI, so timing can only bias the row against a
    pass, never toward one.
  - Shifting each clip by its measured lag was rejected: it reads timing from the true DI, which a song does not have.
  - *The placement evidence* (added by `phase_scratch_loudar_dry`): every placed name goes through the same placement
    code, and `stem-in`'s tight lags (21 of 23 deciding parts within 1 ms, median 0 ms) are today's evidence that this
    code is right. The `ld-*` medians of 0 ms are not that evidence on their own, because LOUDAR's lags scatter.
  - *Beside G50, report only* (also added by `phase_scratch_loudar_dry`, from the review of #569): each part's
    sub-window fraction within 1 ms, from `timing-subwin.json` read by its sha256, next to the whole-clip lags; a
    descriptive Spearman of `D_true` against that fraction over the deciding parts; and every bottleneck string ends
    "(timing and timbre not separated)". None of them decides.
- **The deciding sets: BKS and the panel** (23 parts, 11 DI files), weighted equally. LOUDAR's prior trained on GOAT's
  DI, so GOAT is read beside, marked in-sample, and never decides.

### 13b. The row and the reading

The codec row's short row with another dry guitar: `scratch_codec.start_value`, `short_search`
(`run_part(budget=50, step1_only=True)`), `short_answers`, `scratch_search.score_row_part`, the comparators'
loaders and every guard, against `xlnoG@-3` with the held half zeros. Cen and `cp50` are scored through the **true DI**
on the **held half** against the **clean record**.

| Number | Definition | Says |
|---|---|---|
| `D_blur` | G50(`ld-stem`) − G50(`fs-both`) | LOUDAR against the bar. Below zero: above the blur |
| `D_true` | G50(`ld-stem`) − G50(`fs-stem`) | The whole cost against the true DI. Beside only: it does not gate, since per part `D_blur` = `D_true` − ((c) − (b)) |
| `D_cut` | G50(`di-cut`) − G50(`fs-stem`) | What cutting the dry guitar to the search half costs by itself |
| `D_bar` | `D_blur` − `D_cut` | LOUDAR against the bar with the cut's own cost taken out |
| `D_null` | G50(`ld-stem`) − G50(`stem-in`) | LOUDAR against its own input |

**References on BKS and the panel** (stored; a test reproduces them): (c) − (b) +0.125 [+0.076, +0.173]; `rt-m2l`'s
`D_true` +0.012 [−0.006, +0.030]; `rt-dac`'s +0.000 [−0.017, +0.017]; G50 of row (b) −0.242 and row (c) −0.118 (whose
interval reaches above zero: the bar is itself level with Cen here). On BKS alone row (c) reads −0.000.

**The deciding number** is `D_blur`, unless the cut itself costs something: if `D_cut`'s upper end is above +0.05, the
table reads `D_bar` and says so.

| Code (first that holds) | When | Reading | What follows (a recommendation; nothing continues on its own, except `ld-rec`) |
|---|---|---|---|
| `FL-null` | `D_null`'s lower end at −0.05 or above | LOUDAR's dry guitar is not readably better than the stem it was made from | Recommend parking LOUDAR (the user's call); the next measurement is `ld-rec`'s read, which names the bottleneck. If `stem-in` itself reaches the bar, that goes to the user as its own finding (13f) |
| `FL-above` | The deciding number's whole interval below zero, its mean at −0.05 or beyond, **and G50(`ld-stem`)'s upper end below zero on BKS+panel** | From the song's stem alone, LOUDAR's dry guitar beats the blurred true DI at the checkpoint, and beats Cen. "By a heard size" only at −0.10 or beyond | The route leads. Proposed next, each under its own declaration: its full row, a stem from a mix with other guitars, a listen |
| `FL-reach` | Its upper end under +0.10 and its mean under +0.05 | Level with the blurred true DI: a heard-size loss is ruled out. Where row (c)'s G50 interval reaches zero (as here), it reads "level with a bar that is itself level with Cen here" | To the user with `fs-notes` beside: the two routes are compared before either goes on |
| `FL-short` | Its whole interval above zero, its mean at +0.05 or beyond | Below the bar | Recommend parking the route, not closing it (the user's call); the next measurement is `ld-rec`'s read, which names the bottleneck (13f) |
| `FL-undecided` | anything else | Not decided; undecided is not failed | To the user with the intervals |

`FL-above` and `FL-reach` cannot hold with `FL-short` (a test on a grid). A pass on the deciding number without G50's
gate reads `FL-reach` and says the gate failed.

**Naming the bottleneck** (after `FL-short` or `FL-null`; coded now, `bottleneck`):
- `ld-rec`'s row is read by the same table, with `di-cut` reused. In that read `D_null` is G50(`ld-rec`) −
  G50(`stem-in`): LOUDAR on the clean record against the stem. At or above the bar (`FL-above` or `FL-reach`):
  **the stem**, and LOUDAR becomes a yardstick for separator work.
- Otherwise GOAT's beside read splits the rest. GOAT at the bar while BKS and the panel are short: **the prior's
  coverage, or memorisation**. GOAT short as well: **the generator or its operator**. GOAT not run (outside the cost
  stop): **generator against prior: not split**.
- A failing part is a research target. Nothing is closed by this test.

**Against `fs-notes`** (zero renders, `versus-notes`, once both rows are read): G50(`ld-stem`) − G50(`fs-notes`) at the
checkpoint, paired, and against `fs-notes`' best arm (answer or shrunk), said with it that that arm had 212 more
renders a part. **On BKS first**, the only set clean for both (the panel's songs were in `fs-notes`' transcriber's
training, GOAT in LOUDAR's): **16 parts from 2 songs**, so a narrow read. BKS and the panel together beside. The inputs
differ and the read says so: `fs-notes` reads its notes from the true DI; `ld-stem` hears only the stem.

**Beside in the report:** which number decided; G50 by set, with "upper end below zero on BKS: yes or no"; the room
kept, 1 − `D_true` / ((c) − (b)); `D_true` against the codec ceiling (`rt-m2l`); GOAT's read, marked in-sample; `D` by
class and with each DI file left out; parts at +0.10 or worse than Cen; the start reads (`ld-stem-b` less `ld-stem`
as the seed gauge, if built); the compression note (the checkpoint understates late losses by about +0.026); the
zero-render figures (`figures.json`: log-mel, envelope, crest, timing, the before-measure spectral distance; `stem-in`'s
beside `ld-stem`'s), descriptive, never deciding.

### 13c. Guards, steps and cost

- **Guards** (every command): `scratch_search.on_main`; this module, `learn/loudar_run.py`, `learn/scratch_codec.py`
  and `learn/codec_roundtrip.py` equal main's; the `phase_scratch_loudar*` keys equal main's; the `scratch_search.py`
  blob and `fs-notes`' two checks as the codec row; main holds `phase_fs`, `phase_fs_draw`,
  `phase_scratch_both_outcome`, `phase_scratch_codec_outcome` and `phase_scratch_loudar`. **Every render command**
  (`start`, `control`, `search`, `score`) also **waits while `fs-notes` might still run**: it refuses until
  `fs-notes`' report exists, **or** main's `phase_nr_1_redo_ear` verdict is recorded as a fault ("fault-content" or
  "fault-signal"; then `fs-notes` will not run). An "ask" or "incomplete" verdict goes to the user, and `fs-notes` may
  still run after it, so renders keep waiting. The gate keeps the render slots free for `fs-notes`; it is not a dependency on `fs-notes`
  passing. Then the render-slot cap, the disk guard before every part, C3r's state, no separation beside,
  `never_overwrite`. `search` needs the control passed; `score` and `read` the answers' keys;
  `ld-rec`'s commands an `FL-short` or `FL-null` report and their own build hash (`phase_scratch_loudar_dry_rec`).
- **The pool rule:** BKS and the panel both read, the panel on its 3 DI files; a lost panel DI file stops the row, to
  the user. The refusal stop is 3 of the 23 (retired by section 14: refusals are reported, never a stop).
- **Steps:** unit 0 (13d) → `prep` (the search halves LOUDAR hears; each equal to the blanked reference's span) →
  LOUDAR's runs (the 23 `ld-stem` clips, then GOAT's 24, then `ld-stem-b`'s 23, while under the cost stop; never beside
  a render job) → `build` (every check before anything is written) → hash PR `phase_scratch_loudar_dry` → once
  `fs-notes`' row is read (or its ear verdict on main is a fault): `start` → `control` → `search --name ld-stem` (`--first 2` first) → `answers` → hash PR → `di-cut`'s
  and `stem-in`'s searches and hash PRs → each `score` → `read` → on `FL-short` or `FL-null`: `ld-rec`'s runs →
  `build-rec` → its hash PR → its short row → `read-rec` → hand-back, audit, results PR `phase_scratch_loudar_outcome`.
- **Cost (renders, measured rates):** start reads 186, control 22, short searches 4,743 (`ld-stem` 47, `di-cut` 23,
  `stem-in` 23, at 51 a part), scores 372: **5,323**, about 53 minutes, up to about 1.5 hours under load; 3,955
  without GOAT. `ld-rec`, after the read on any code (13f): 1,311.
- **The cost stop** (CPU; the delegated decision agent's choice under the user's standing rule: yes, confidence 0.8):
  everything that runs without asking must fit **8 wall hours at 4 threads**: the gate's 18 runs, its 4 timing and
  check runs (the timed whole and cut clip, the seeded rerun, the zeros-reference run), and the 23 deciding clips. GOAT's 24 clips, then `ld-stem-b`'s 23, are added in that order only while the total stays under 8 hours (GOAT
  placed before `ld-stem-b`). If the gate and the 23 do not fit: stop and ask. Fewer steps would be another method and
  is not offered. The time for one 10-s window is reported either way.
- **`stem-in` always, `ld-rec` only after a fail** (the delegated decision agent's choice: yes, confidence 0.75).
  **Since 13f (L1): `ld-rec` runs after the main read on any code.**
- **Repeat use.** These held halves were read by rows (b), (c), `fs-codec` and soon `fs-notes`. Nothing here is chosen
  on a held value: the setting is chosen on the authors' examples; the checkpoint, table and sets are fixed now.
- **11g**, the clip-free re-score beside new rows, is declared but not coded; when it is, this row's answers join it
  under 11g's own amendment, reported only. This row does not wait for it.

### 13d. Unit 0, after this declaration merges (no repo change; CPU; none of our audio)

1. **Downloads** (under the standing approval; each in `codec-models/manifest.json` with size and sha256, a line in
   `MANIFEST-HISTORY.md`): LOUDAR's `GuitarFx-175000.pt` (Hugging Face `msvento/loudar`, 1,083,089,737 B, sha256
   `d86e08bbb94bb12cef0b907dd7f3fd67ba112cc463c8ee0e964855155985c297`, MIT tag); LOUDAR's `src/` at commit
   `9f3bd1659991b584afcfa7a3ac395c0512f24237` and the authors' 18 gate files (`distorted`, `original`, `LOUDAR` × 6) by
   a sparse checkout into `~/ndsp-presets/tools/loudar/`; 16 packages at LOUDAR's `uv.lock` versions (about 28 MB) into
   `~/ndsp-presets/tools/loudar-venv`, beside `requirements-codec.lock`'s 36 unchanged, `--require-hashes --no-deps`,
   after a resolver dry run.
2. **The checkpoint loads weights-only.** Its pickle's globals are listed by `pickletools` (nothing is executed); it
   loads with `weights_only=True` inside `torch.serialization.safe_globals([...])` naming only the omegaconf classes it
   holds, and `state["ema"]` is taken. Any other global stops, to the user.
   **Amended 2026-11-23 (ledger `phase_scratch_loudar_globals`), after that stop fired:** the listing found
   `__builtin__.dict`, `__builtin__.list`, `__builtin__.long`, `collections.defaultdict` and `typing.Any` beside torch's
   three and the 5 omegaconf classes. An isolated decision agent, under the user's standing rule for technical calls
   (not the user's own answer), chose option (a′), about 90% confident it is safe:
   - names are resolved with `_compat_pickle` as torch resolves them, against one frozen allowlist of these 13; any
     other name still stops;
   - `collections.defaultdict` is served by `_defaultdict_as_dict`, which returns a plain `{}`, never the real class
     (torch's SETITEM check accepts only a dict, `OrderedDict` or `Counter`);
   - `typing.Any` is OmegaConf's inert type marker, and `Any()` raises;
   - torch 2.10.0 and omegaconf 2.3.1 are pinned and checked at load, as are the checkpoint's sha256 and revision;
   - only `state["ema"]` is kept, asserted a dict of tensors, and the config is never resolved.
3. **The gate's reference figures, zero runs:** the floored log-mel distance from the original (the mean of the 256-
   and 2,048-sample frames) for the authors' own LOUDAR outputs and for the distorted inputs, and the authors' gain
   (their difference). The 1.0-dB tolerance is reported as a fraction of that gain.
4. **One clip timed first** (`distorted_0`, whole and cut to 4.5 s, released) and the cost stop applied.
5. **Two checks:** a second seeded run, and a run with the reference set to zeros, are byte-equal.
6. **The gate:** the six examples with both settings; the setting with the lower mean distance (within 0.1 dB, the
   released) is chosen; then the six cut to 4.5 s with it. Pass: our output closer to the original than the distorted
   input on at least 5 of 6; our mean within 1.0 dB of the authors' outputs' mean; the cut no more than 1.0 dB worse
   than the same 4.5 s of the full run. Otherwise stop and ask.

   **Amended 2026-11-23 (ledger `phase_scratch_loudar_gate_amend`), after the gate's declared stop.** Decided by an
   isolated decision agent under the user's standing rule of 2026-11-23, at about 0.8 confidence; not the user's own
   answer.

   *What the gate measured* (unit 0, from main `bf484311`, CPU):
   - The distorted inputs read 4.03 mean from the original. The authors' own LOUDAR outputs read 6.07, farther on all
     6 clips, so the authors' gain is −2.04 dB and the fraction-of-gain tolerance is undefined.
   - Ours: released 6.12, paper 6.36, so the released setting is chosen by the declared rule.
   - Reproduction: 0.05 dB from the authors' mean. Length: +0.72 dB (the mean; the reading gives the per-clip
     length gaps beside it, +1.37, +0.23, +1.90, +0.04, +0.27 and +0.54 dB, added by
     `phase_scratch_loudar_timing_amend`; the rule still reads the mean).
   - Timing: 116.8 s a whole 10.96-s clip and 58.3 s a 4.5-s clip, about 1.7 wall hours projected for everything.
   - Both byte checks are equal.

   *What changes:*
   - **The direction check is removed from the pass rule**, because the authors' reference outputs fail it 6 of 6.
     Floored log-mel cannot vouch for LOUDAR's quality here. Whether LOUDAR improves on its input is decided only by
     J0, through `D_null` / `FL-null`, as already declared. The count is still reported.
   - **Reproduction is stricter:** the mean within 1.0 dB of the authors', and each of the six clips within 1.0 dB of
     the authors' output for that clip; any clip beyond stops and asks. Re-read on the stored record, no new runs, it
     passes: ours less the authors' per clip is +0.16, −0.06, −0.10, +0.79, −0.20 and −0.27 dB.
   - No new measure: Fx-Encoder++ is not downloaded, and any other distance appears only in the descriptive
     `figures.json`, never in a gate or a reading.

   Nothing else changes: the table, the codes, the thresholds, the sets, the checkpoint, the setting rule, the cost
   stop, the timing check (later made report-only, §13a), the `stem-in` null, the `ld-rec` trigger and the
   `fs-notes` render wait stay as declared.
   **With any result:** no measure we hold showed LOUDAR improving on its input before the J0 row; the row's
   `FL-null` is the first test of that.
7. Its facts (the setting, the gate's figures, the measured seconds a clip and the projected build time) go into
   `phase_scratch_loudar_dry`.

   **Recorded 2026-11-23 (ledger `phase_scratch_loudar_dry`).** The build ran from main `7d6d2c9d` with zero renders:
   - the setting is `released` for every run; every measured clip is within 0.25 LU;
   - the runs took 59.07, 58.82 and 58.91 s a clip (ld-stem on BKS and the panel, ld-stem on GOAT, ld-stem-b), about
     69 wall minutes in all against the 1.70 hours projected; GOAT and `ld-stem-b` both fit the cost stop;
   - the placement stop did not fire: the median whole-clip lag is 0 ms for every placed name; the 1-ms check,
     report-only, reads 9, 10 and 2 of 23 beyond for `ld-stem`, `ld-stem-b` and `stem-in`.

   Renders still wait for `fs-notes` (`slots_refusal`, in code).

### 13f. L1: refusals as reports, `ld-rec` after any code, the park text (2026-11-24; ledger `phase_scratch_loudar_l1`)

Decided by an isolated decision agent under the user's rule of 2026-11-24 (no made-up bars); not the user's own
answer. The record is the handover's `decisions/bar-conversion.md` (sha256 `2e598bca…5ddb2`), its LOUDAR section
and L1. It comes after section 14 (S1) and before LOUDAR's `answers`.

- **S1 in this row.** `answers` reads each search record or its rerun (`--rerun` on `search` and `score`, once, in a
  fresh process) and waits while a technical refusal has not been rerun. The refusals are reported
  (`refusal_report`), never a stop. The read is on every part: a refused part's G50 is Cen's (0) in `ld-stem`,
  `di-cut` and `stem-in` alike. Beside: the passing-only rows, `refused_audit` and `read_codes`'s
  `refusal-sensitive` label, which sends the row to the user with both reads.
- **`ld-rec` runs after the main read on any code** (1,311 renders). It is a diagnostic: LOUDAR's ceiling without
  separation, and so whether the stem is the bottleneck. That is useful even on a pass. It waits only for the main
  read's report (`rec_refusal`). After a pass or an undecided read, `bottleneck` names none and reads `ld-rec`
  beside as the ceiling.
- **The park text becomes a label plus a recommendation.** `FL-null` and `FL-short` now say "recommend parking" and
  name the next measurement, `ld-rec`'s read. Parking is a route call and goes to the user; nothing parks itself.

Nothing else changes: the table's conditions, the codes, the thresholds (the user's SMALL and BIG), the sets, the
comparators, the timing and placement rules, and the `fs-notes` render wait.

### 13e. What it can't say

- Anything with other guitars in the mix (the stem here comes from a mix with none), on released records, or by ear.
- LOUDAR hearing the whole window, as the product would.
- The final answer after 262 renders, or long-term tone colour (the measure step removes it).
- LOUDAR with a wider prior, more steps, or another operator.
- That LOUDAR improves on its input by any measure other than J0: none we hold showed it before the row (13d's
  amendment); `FL-null` is the first test.

## 14. Refusals as reports, not row stops (S1; 2026-11-24; ledger `phase_scratch_refusal_reports`)

Decided by an isolated decision agent under the user's rule of 2026-11-24 ("no made up or random thresholds/limits");
not the user's own answer. The record is the handover's `decisions/bar-conversion.md` (sha256 `2e598bca…5ddb2`),
its refusals section and S1. It applies to every row: rows (b) and (c), `fs-notes`, `fs-codec`, the tone split and
`fs-loudar`.

1. **No row stops on a count of refusals.** `scratch_search.stopped` is always False; `scratch_notes.deciding_stop`
   and LOUDAR's `deciding_stop` list the refusals and stop nothing; `note_transcribe.refusal_count` never stops, so
   `cmd_build` builds on; `REFUSAL_STOP` is gone from every module. The count and share are reported per set and
   pooled, with a Clopper-Pearson 90% interval (`refusal_report`, each refusal's reasons unwrapped).
2. **A check against the truth is never a refusal.** A content check compares the result with the true DI, which a
   song does not carry. `fs-notes`' search now searches a content-failing part as built and writes the failed checks
   on its record as `content_label`, carried into the answers and the report. Such a part now counts as answered,
   so it is a borrowed-answer partner and a member of the other parts' centre pool. A count of content failures no
   longer stops the build (`build_refusal`, `refusal_count`). The checks themselves become report-only in the redo's
   amendment (R1).
3. **A technical refusal is rerun once, then reads at Cen.** Technical refusals are a start-check miss, non-finite
   audio, a missing borrowed answer and a scoring-control miss. The part reruns once in a fresh process (`--rerun`
   on `fs-notes`' search and score, into `<dir>-rerun/`; the search rerun recomputes its start reference there
   too; LOUDAR's in L1). The reads wait for that rerun
   (`with_reruns`, `rerun_refusal`); this finds the cause, it is not a cap. If it still refuses, the part's answer is
   Cen, the product's own fallback, and it is listed.
4. **The deciding read is on every part (intent-to-treat).** A refused part reads at Cen: every `ln(x / Cen)` number
   of its own answers is 0 (G and the checkpoints' and the shrunk answer's G; `itt_per`, `itt_values`); in a paired
   difference it costs the row its partner's gain. `G_centre` stays empty (the row's centre is no part's fallback),
   and numbers that need the partners scored on the part (I, the borrowed answer) read on the passing parts. Beside:
   the **passing-only** read; where it has no interval the report says "no passing-only interval" and labels
   nothing. The user's pool rule stays, and the Cen fallback keeps every set whole.
5. **The refused parts are audited against the rest** (`refused_audit`): set, amp, class, lender band and Cen's
   search-half start value (the draw's for rows (b) and (c), each part's start reference for `fs-notes`), then, after scoring, their value at Cen against the passing parts' as a difference of
   means with its interval. If the two reads give different codes, the row is labelled `refusal-sensitive` and goes
   to the user with both.

The shared path's guard: `scratch_codec.SCRATCH_SEARCH_BLOB` is re-pinned from `2420043a…` to `b66af002…` (L1
then to `6687a5dc…`, for rows (b)/(c)'s "no passing-only interval" in `cmd_read` only). Every
function of `learn/scratch_search.py` that `fs-notes`' two checks ran through (60, `search_row_part` and
`score_row_part` among them) keeps its source exactly (a test pins their combined sha256). Rows (b) and (c), both
codec rows and the tone split refused 0 parts, so none of their stored readings changes (tests re-derive them where
the data is present). The finished tone split and the codec's full row read on their passing parts if ever re-read
with refusals; their intent-to-treat read is to be coded first.

## 15. The exact-notes test (rows `xn-bank`, `xn-swap`, `xn-reread`, `xn-list`; 2026-11-24; ledger `phase_scratch_exact`)

Declared 2026-11-24, before anything in it runs. The plan (the handover's `plans/exact-notes-plan-v2.md`, sha256
`897e275e…51ab4`) passed two independent review rounds (both APPROVE WITH CHANGES); round 2's binding amendments G1,
T1, F1, C1, S1, A1 and N1 are built in below and override the plan's text where they differ. **The user's Go 1
(2026-11-24, AskUserQuestion):** decide on the 40 BKS+GOAT parts with all 47 beside; the target rule as presented (T1
as corrected); run straight through (Phase A, then stage 1, then stage 2) unless stage 1's gate fails. The route
decision (Go 4) stays the user's. Code: `learn/scratch_exact.py`; tests: `tests/test_scratch_exact.py`. Data:
`PF/fs/exact/`, each file written once. Grepped first: no `phase_scratch_exact*` key, row name (`xn-bank`, `xn-swap`,
`xn-reread`, `xn-list`), code (`XN-*`) or `scratch_exact` exists in `docs/`, `learn/`, `tests/` or the ledger.

**The question.** On guitars the bank reproduces exactly, what share of the whole dry-guitar mismatch cost comes from
note reading (Basic Pitch) and what share from the replay-from-samples method? The share is reported to the user beside
the real gap: real build 2 less row (b), +0.274 [+0.186, +0.361] on the 40 (`phase_scratch_notes_read_b2`). **No
outcome licenses a route change**; every code goes to the user with what the exact world cannot show.

### 15a. The bank guitar, the record and the four rows

The bank guitar is each part's build 2 `tr-di` (`phase_scratch_notes_dry_b2`): Basic Pitch's notes, build 2's fixes,
played from single recorded notes. Replay is exact on it by construction.

- **The target** (T1). The part's first partner in the draw's order whose Cen differs from its own (47 targets from 33
  partners; 18 parts in mutual pairs). Target = that partner's row (b) answer projected onto the dims every step-1
  branch searches (step 1's space, which holds the amp EQ, and the left room, `leftRoomActive` and
  `leftRoomMicLevel`), the part's own Cen everywhere else. Step 2's other dims depend on `rightCabActive`, a step-1 dim,
  so they are left at Cen. The left mic type projects only on parts where every branch keeps the left cab on: stage A
  searches the left cab's switch whenever the right cab is on, so this needs the right cab off in Cen and never
  searched in step 1. Step 1 searches `rightCabActive` on every amp, so **the rule projects the left mic type on 0 of
  47 parts** (`left_mic_on_every_branch`; the literal reading, the orchestrator's call of 2026-11-24 under the user's standing delegation of technical choices: it keeps the target reachable on every search path by construction, which is what T1 is for). A categorical value is kept only when it is in the
  part's own value list. At declaration each target differs from Cen on 22 to 35 keys, all of them searched by rows
  (b) and (c) on every part. Without the projection, the review counted 10 parts with audible unsearched keys (on
  parts with the right room off the right room's keys are inert).
- **The record** is the target rendered through the bank guitar, primed alone (`fresh_render`). Each row's search is
  handed it with everything outside the search half set to zeros (`blank_plan`). The search process opens only the
  blanked record (`records.json` holds the records' sha256 and no settings) and its dry guitar: never `targets.json`,
  a target file, `answers-fs-stem.json` or anything scored (`search_open`; a test walks every function the search
  reaches).
- **Lag 0, tested** (zero renders): per part, J0 of the record against a second target render, with the bank guitar as
  the judge's DI, is exactly 0 on both halves at lag 0 and above 0 at lag ±1 (`lag_check`).

| Row | Dry guitar of the search | Its G less `xn-bank`'s prices |
|---|---|---|
| `xn-bank` | the bank guitar | — |
| `xn-swap` | the part's real DI (`note_replay.di_section`) | D_swap: the whole mismatch between a real guitar and build 2's rebuild |
| `xn-reread` | Basic Pitch re-reads the bank guitar (no pre-roll); build 2's rule (F1 global, ring-soft, no loudness); `rebuild_redo` with the bank guitar as the DI | D*: note reading plus re-derivation |
| `xn-list` | `rebuild_redo` from the bank guitar's exact note list (build 2's notes after its fixes, as played; no fix applied again) with the bank guitar as the DI | D_list: re-derivation of levels, mutes, tilt and finish alone |

- The reading share is D* / D_swap, both costs in the exact world; no cross-world bridge. Reading proper is
  G(`xn-reread`) − G(`xn-list`). Where an `xn-list` guitar is byte-identical to the bank guitar, that part takes
  `xn-bank`'s search record byte for byte.

### 15b. The search and the score

- **The search:** `scratch_search.search_row_part` unchanged, on the exact world's part (`synthetic_part`: the draw's
  part at lag 0), each row's own start reference (`scratch_notes.start_reference`'s rule with the row's dry name, at lag
  0), same budget, seeds, checkpoints and halves as rows (b) and (c).
- **The score:** J0 on the held half against the record, through the bank guitar (the judge's DI too), lag 0.
  G = ln(d / d_Cen), the part's own Cen. Six settings a part: Cen, the answer, the three checkpoints, shrunk (12
  renders); no borrowed answer and no centre (meaningless here; a partner shortfall would zero a part's G under S1).
  The scoring control is a determinism check only: Cen within `SCORE_TOL` of its value from `targets`.
- **The bug rule:** a zero distance on any scored setting (ln 0), or a non-finite one on Cen or the answer, stops the
  read and goes to the user. A non-finite distance elsewhere takes `nonfinite_rule`.
- One seed: every paired difference includes the search's divergence from its single seed.

### 15c. The reads, the gate and the codes

Answer arm deciding, shrunk beside; BKS+GOAT (the 40) decides (Go 1), all 47 beside. Intervals from
`note_replay.summary` through `scratch_notes.set_rows`. SMALL and BIG label only, via `paired_reading` and
`number_reading`. S1 applies: a technical refusal is rerun once in a fresh process, then the part reads at Cen; the
passing-only read and the refusal report go beside, with `refusal-sensitive` when their codes differ.

- **Paired costs:** D_swap, D*, D_list, D_swap − D*, reading proper.
- **The share (F1):** for each r, the per-part values D*_i − r·D_swap_i go through `set_rows`' BKS+GOAT pool; the share
  is every r whose 90% interval spans zero (`fieller_share`), never built from the two marginal intervals. Declared
  grid: r from −4 to +4 in steps of 0.01, each boundary bisected to 1e-6, an end touching the grid followed outward by
  doubling to 1e6. Its shape is reported as it comes out (bounded, a ray, two rays, the whole line, several pieces).
  Undefined if D_swap's interval reaches zero. The same method gives every share: `xn-swap` and `xn-reread` over
  `xn-bank`, beside real build 2 over row (b).
- **Beside:** D* split at the median re-read F (`match_notes`, the exact list against the re-read notes after build 2's
  fixes); Spearman of D* with the part's real gap (build 2 less row (b)); clean and crunch; the checkpoints; one part
  per partner (the first by key, 33 parts); T1's coverage after each row (whether its searched dims covered every key
  on which the target differs from Cen).
- **The gate (G1),** read by `gate` (zero renders) after stage 1's scores: `xn-bank` reads "passes" against Cen AND
  D_swap's 90% interval lies wholly above zero (the condition for the share to be defined; no bar). The realism
  comparison goes beside it, not in it: the share of `xn-bank`'s gain that `xn-swap` keeps, beside the share real
  build 2 keeps over row (b). **N1:** stage 2 starts on its own once G1 holds, unless the user stops it; if G1 fails,
  nothing more runs and it goes to the user.

| # | Code (first that holds) | When | Said | Next |
|---|---|---|---|---|
| 1 | `XN-insensitive` | G1 fails | `xn-bank` does not pass against Cen, or D_swap is not shown above zero; the share is undefined and nothing is priced. The realism comparison is reported beside | To the user |
| 2 | `XN-anomaly` | D*'s interval wholly below zero | The re-read guitar beats the exact one | Audited before anything is said |
| 3 | `XN-overshoot` | D_swap − D* wholly below zero | Re-reading bank audio costs more than the whole real-DI mismatch measured in the exact world | Audited before anything is said |
| 4 | `XN-reading` | D* wholly above zero; D_swap − D* not wholly above zero | Reading plus re-derivation's cost is shown; a remainder beyond it is not shown (upper end hi90 = …) | To the user with the share; `xn-list` says which |
| 5 | `XN-both` | D* and D_swap − D* both wholly above zero | Both cost; the share and its interval give the split | To the user |
| 6 | `XN-rest` | D* spans zero; D_swap − D* wholly above zero | Reading's cost is not shown in the exact world; the test rules out a reading cost above D*'s hi90 | To the user; no route licensed |
| 7 | `XN-undecided` | anything else | Not decided; undecided is not failed | To the user |

- The table tilts towards `XN-both`; the share carries the size.
- **`xn-list`'s rule** (`list_split`, coded before any render): reading proper shown when G(`xn-reread`) −
  G(`xn-list`) lies wholly above zero; re-derivation shown when D_list does.

### 15d. What it can't show

- The exact world differs from real songs in more than the replay: the plugin is the target, the reference is clean
  (not the `xlnoG` stem), the objective is sharper.
- The scale bias runs both ways (the log ratio grows near a reachable optimum).
- Reading difficulty: the bank guitar is read without pre-roll, the real DI with `padded_section`'s margins. By stored
  counts it is not easier (P 0.62, R 0.91 against 0.45 to 0.61 and 0.92 to 0.99 on Guitar-TECHS).
- Content: the bank guitar is the song as Basic Pitch heard it.
- Scope: one bank, one transcriber, one seed, the score only.

### 15e. Steps, guards, cost

- **Phase 1, `build`** (zero renders; `PF/fs/exact/dry/<row>/`, `build.json`), with four proofs: (1) today's code
  rebuilds build 2's files byte for byte (`note_fixes.identity_check`); (2) the re-read's events equal build 2's round
  trip (`work/build-b2/round-trip/`) exactly (the input files' samples are compared beside; their sha256 differ by
  libsndfile's PEAK-chunk timestamp alone, checked on two parts before the declaration); (3) this module and `scratch_search.py`, `scratch_notes.py`,
  `note_transcribe.py`, `note_rebuild.py`, `note_fixes.py`, `bp_run.py` byte-identical to main; (4) `xn-reread`'s pause
  shares per half, reported beside the bank guitar's stored maximum (0.34). Proofs 1 to 3 must hold before anything is
  written. If main moves, the worktree is re-cut and the proofs rerun before the next command.
- **Phase A** (about 800 renders): A1 `score-check` (row (c)'s two check parts re-scored by this module's score on the
  six settings both share, S1: `score_check_verdict` would otherwise compare row (c)'s borrowed and centre settings
  too) and `search-check` (this module's start reference and `run_part` with row (c)'s inputs, 10 evaluations, equal to
  row (c)'s stored curve), about 50; A2 `targets` (record, second render, Cen through the bank guitar; the lag check),
  282; A3 `floors` (the target through the true DI, `xn-reread` and `xn-list`, read on the held half as ln(d / d_Cen)
  with the bank guitar as the judge's DI), 282; A4 `floors-real`, a declared read of real held halves already scored
  (row (b)'s answer through the true DI, which must reproduce row (b)'s stored render sha256 and value, and through
  `tr-di`, against the clean record with the true DI as the judge's DI: the real analogue), 188; A5 `floor-read` (zero
  renders) and the hash PR `phase_scratch_exact_targets` (build, checks, targets, records, floors). **The floors (A1)
  are read for order and rough size, never as a predicted D:** a fixed-preset floor is an upper bound on what search
  cannot recover. `xn-swap`'s floor includes the true DI's input-level offset (the `SB.measure` clip, up to about
  7 dB) at a fixed input gain, which the search can fix.
- **Stage 1:** `search` (`--rerun` once for technical refusals), `answers` and its hash PR
  (`phase_scratch_exact_answers_bank`, `_swap`), `score` (`--rerun` once for control misses), then `gate`. **Stage 2**
  the same for `xn-reread` and `xn-list` (`_reread`, `_list`). **Phase D:** `read` once, an independent audit, the
  results PR (`phase_scratch_exact_outcome`). Every render command: at most 3 shards (and render processes), the
  disk guard (31 GB) before every part, `caffeinate -i` and `no_bg_nice`, from a frozen detached worktree of main.
- **Guards:** every command refuses unless this checkout runs main's code (this module and the six files above) and
  `phase_scratch_exact*` keys (`scratch_search.on_main`), and main holds `phase_fs`, `phase_fs_draw`,
  `phase_fs_answers_stem`, `phase_scratch_notes_dry_b2` and `phase_scratch_exact`. The search waits for the targets'
  hash and both checks; `score`, `gate` and `read` for the rows' answers keys; stage 2's searches for a holding G1.
  The key prefix sits outside every guarded prefix, so the redo's guard does not read these keys and build 3's held
  search is not refused.
- **Cost (measured rates):** Phase A about 800 renders (about 10 minutes on 3 processes); a row's search about 12,435
  renders (6,532 s on 3 processes) and its score 564; stage 1 or stage 2 about 26,000 renders, about 3.9 hours; all
  four rows about 52,000, about 7.8 hours. Disk about 0.6 GB.
- **Privacy:** the ledger holds hashes and counts only; settings, song-named keys and audio stay under `PF/`.
