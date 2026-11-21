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
