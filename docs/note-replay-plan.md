# The note-matched replay: does render-and-compare pick well through a worse reference or dry guitar? (plan)

**Status:** declared 2026-11-20, before any run, on the user's approval of the three measurements of the 2026-11-19
strategic review (`~/ndsp-presets/handover/2026-11-19/strategic-review.md`, section 4, Direction 1). The plan passed an
independent review with changes (approve with changes, three blocking items, all wording and coding before the run,
zero extra renders). All three are built in here (section 11), with the rulings on the open questions. Nothing has run
except the zero-render smoke checks of section 10, whose outputs sit outside `PF`. Every number is by the score unless
it says "by ear": J0, ln(d_row / d_against) on the held half, below zero closer; 90% cluster t intervals; the deciding
pool is BKS, GOAT and the panel weighted equally (`full_controls_c3r.pooled`). `PF` is
`~/ndsp-presets/learn/trusted-data/pipeline-fix`.

**The user's rule (2026-11-19).** No action rests on a J0 gap under 0.05. "Passes" means decided better with the mean
at −0.1 or beyond. An interval inside ±0.05 reads "not readable by the score". By ear, J0 is trusted at gaps of about
0.1 and over ([ladder-ear-results.md](ladder-ear-results.md), A4).

- **Ledger:** `preset-ladder`:
  - `phase_replay`, this declaration;
  - `phase_replay_draw`, the draw file's sha256, before any blur, separation or render;
  - `phase_replay_picks`, the picks' sha256, before `score` loads any held-half value;
  - `phase_replay_picks_singles`, the same for the single-blur rows, only if they are triggered;
  - `phase_replay_outcome`.
- **Code:** `learn/note_replay.py` (`level_menu`, `menu_of`, `draw_parts`, `part_numbers`, `row_reading`, `R_TABLE`,
  `dry_reading`, `both_notes`, `outcome`, `control_check`). Tests: `tests/test_note_replay.py` (pure, light CI).
- **Reused:**
  - `preset_ladder`: the units, `lender_mix`, `rebuild_refusal`, `sep_blockers` and `summarise`;
  - `learnable_targets.candidates` (trial loading);
  - `di_robustness.average_balance` and `degrade` (the blurs, code unchanged);
  - `knob_ceiling.judge`'s distance (one half at a time);
  - `ladder_ear`'s draw-once and hash pattern;
  - `half_data`'s table coding and `title_of`.
- **Data:** `PF/replay/`. It holds `draw.json`, `controls/` (stored, position, control), `blur.json`, `di/`, `stems/`,
  `dist/`, `bleed.json`, `picks.json` and `report.json`. Render audio is not kept.
  - **The stems are kept after the run and the audit** (the orchestrator, 2026-11-20). They live at
    `PF/replay/stems/{xlnoG,xl}/` as one `.npy` and `.json` a unit. The rebuild work reuses them, and without them it
    would need about 244 separations again. They are 1.92 MB a stem (measured on the smoke's two), about 470 MB for
    244, well inside the 31 GB disk guard (49 GB free at declaration). They are on the cleanup protect list.
  - The blurred DIs (`di/`, about 0.7 GB for 366 files) are kept until the audit, then moved aside by the executor.
- **Names.** Grepped before naming: "note-matched replay" and the row keys (`control`, `blurred`, `stem-alone`,
  `stem-full`, `both-alone`, `both-full`, `avg-only`, `mild-only`) have no earlier use in `docs/`. `avg`, `mild` and
  `avg+mild` are `di_robustness`'s own variant names, used for the same code.
  - "The Control" here is this replay's true-DI row. It is not the ladder's stage-1 `replay` control
    (`preset_ladder cmd_replay`), which is unrelated.
  - "Arm A" is used only for the October route.

## 1. The question

On held-out ladder parts, give the search's own comparison a worse reference (X-LANCE's stem) or a worse dry guitar
(a blurred copy of the true DI). Does it still pick settings a heard size better than Cen and than a blind pick?

**The goal check.** The goal is the most accurate preset with no human step. Searching through a render at song time is
the one route heard far above Cen (the labels: −0.40 by the score, 17 of 21 cards by ear). This test asks which part of
that route is missing: the reference, the dry guitar, or neither.
- **A fail on the blurred DI** means a dry guitar this degraded does not work. It says nothing about a better dry
  guitar.
- **A pass** means the degraded comparison ranks a true-DI search's candidates well. That is necessary, not
  sufficient. Before any product claim, a from-scratch search through the degraded inputs, scored on the held half
  against Cen, comes next.
- **The stop rule:** one build, one read, and at most one conditional pair of single-blur rows, declared here.

**No old DI-rebuild model is used** (the user's ruling of 2026-11-20): not `learn/direc-sep/` nor `rebuild-gap/`.
Their training data is untrusted. The dry guitars are the true DI and its blurred copies. A real note-matched dry
guitar is a second stage, not in this plan.

## 2. How this differs from what failed

| Before | What it was | What differs now |
|---|---|---|
| Arm A, October ([ROADMAP](ROADMAP.md)) | A search through a rebuilt DI against the htdemucs stem: −0.028 and −0.046 against S; +0.012 with the true DI against that stem | X-LANCE's stem (SI-SDR median +17.2 dB with no other guitar, +0.75 dB on a full mix, ladder stage 2); every searched control; the bar is Cen and a blind pick at a heard size |
| DI robustness, October ([results](di-robustness-results.md)) | 25 parts, 21 factory presets, against template+R | 122 held-out parts in three sets, a menu in today's full space, scored against Cen and against a blind pick |
| DI-free distances and embeddings ([results](di-free-distance-results.md)) | Compared across different notes: regret 0.35 | The notes are matched (regret 0.04 there) |
| The reader (the six-step plan) | A learned map from audio to settings, about 290 chains | No map is learned |

**Why it may fail, said plainly.**
- **October's nearest precedent was weak.** The two blurs alone kept −0.168 (an average guitar's balance) and −0.199
  (mild artefacts) of the oracle's −0.267. Together (`avg+mild`, this plan's blurred DI) they kept −0.067 on the
  judge's default bands, but −0.168 on union bands. The blurred-DI row can honestly fail or read undecided. That is why
  the single-blur rows are declared now (section 6).
- On a full mix the stem is +0.75 dB. The judge takes its bands and floors from the reference, so bleed can open bands
  the guitar does not own.
- A menu pick is easier than a search. **The menu holds none of the degraded objective's own spurious optima** (bleed,
  the separator's EQ), which a from-scratch search would find. The Control picks the label on about 91% of parts at
  planning (94% on this draw without Drowning, section 10). So I largely asks "does the comparison still spot the
  true-DI full-space winner". The level menu also holds many bad settings, which makes I easier for a crude comparison.

## 3. Units and the draw (`draw`, seed 20261201, once, hashed into the ledger before any render)

A part is one unit on one plugin amp, with its own stored C2 or C2r search record.

| Set | Rule (`draw_parts`) | Parts | Clusters |
|---|---|---|---|
| BKS | Every unit on one amp: inside each DI file the units are shuffled by the seed and the amps rotate from a seeded offset | 40 | 8 DI files |
| Panel | Every part but Silent Waves' two (vocal bleed). Drowning's three are drawn and rendered, and enter the rows only on a recorded ear check before `pick` (section 8) | 10 (7) | 4 (3) DI files |
| GOAT | Per fold and class 9 parts, at most one a GOAT item, in seeded order (`preset_ladder.subset_draw`'s loop) | 72 | 72 items |
| **All** | | **122 (119)** | |

- First- and second-batch captures (cap1, n12) are not drawn: they share GOAT's DI files and never decide.
- **Why one amp a BKS unit:** at planning, all three amps tighten the pool's interval only from ±0.035 to ±0.032, for
  1 h 48 min more renders. The pool's width is set by BKS's 8 and the panel's 4 clusters, which cannot grow.
- **Refusals** (`part_refusal`): a part needs at least 20 usable step-1 trials (at planning the fewest is 53) and a
  finite stored score for Cen, S and the label on both halves.
  - A GOAT part that fails is passed over for the next in its seeded order.
  - A BKS or panel part is dropped and counted.
  - The draw refuses if a GOAT fold and class falls under 9, BKS under 8 DI files, or the panel under 3 DI files
    without Drowning (`draw_shortfall`).
- **The draw reads no held-half value:** only search-half values and whether a held-half value is finite.
- `draw.json`'s sha256 goes into the ledger (`phase_replay_draw`). Every later command refuses another hash.

## 4. The menu (`menu_of`, 23 settings a part)

0. **Cen**, the part's own fold's (the ladder's `cen` answer);
1. **S**, the class's start on the amp;
2. **the label** (the C2 or C2r record's);
3. to 22. **twenty step-1 trials by level** (`level_menu`). Take the record's distinct step-1 trials
   (`learnable_targets.candidates`, the label's twin left out) with a finite stored judge on both halves. Let s be
   each trial's ln stored judge on the **search half**. Set 20 levels evenly from the best s to the worst. For each
   level in turn, from the best, take the nearest trial not yet taken (a tie to the lower trial index).

**Why by level** (planning, stored scores, all 477 trusted parts, deciding pool):

| The menu's 20 trials | Control's pick − Cen | A blind pick − Cen | Menu settings 0.1 or more beyond Cen |
|---|---|---|---|
| by rank, evenly | −0.394 | −0.255 | 72% |
| at random | −0.394 | −0.267 | 73% |
| **by level (this plan)** | −0.394 | **−0.123** | 52% |

- The stored trials are what a true-DI search visited, so most are already far better than Cen. Under a bar against
  Cen alone, a blind pick from the level menu passes: it reads −0.12 with a half-width of about 0.08. Hence the second
  number, I (section 7).
- The level menu leaves the most room between the Control's pick and a blind one (0.27 apart). **It was chosen at
  planning for that, from the true DI's stored scores on both halves.** The reviewer was told this.
- The best menu setting on the held half reads −0.426, the worst +0.306; inside a part the menu's held-half scores
  spread 0.21 (SD).

## 5. The distance used for the pick

**J0 itself, on the search half only:** `analysis.aligned.aligned_distance(reference, render, dry guitar, lag,
render_latency)`, the judge's defaults, over the search half's window. It is `knob_ceiling.judge`'s call for that
half (`half_distance`).
- **It is the objective that made the labels**, on the same half. So the Control must reproduce stored numbers, and a
  pass means the existing search works with these inputs. No new distance needs validating.
- **It matches the notes.** Distances that ignore the notes fell to a song-blind constant.
- **It is level-free.** Both sides are loudness-normalised, so a stem needs no level rule.
- **It is what October's robustness test used**, with the degraded DI passed as the judge's DI.

**Its limits.** The judge takes its bands and floors from the reference, and uses the dry guitar for alignment and to
skip frames where it is silent. The stored lag is used throughout: the stem is sample-aligned with the amp track in the
built mix (`cmd_sep` scores it against the target with no shift). **Beside, on the position check's 12 parts,** the
lag is re-estimated on each stem (`analysis.aligned.estimate_lag` from the true DI's Cen, S and label renders, hinted
with the stored lag), and the stem rows' picks at both lags are compared (`relag`).

## 6. The rows

**The blurred DI, exactly:** `di_robustness`'s `avg+mild` variant, its code unchanged.
1. `average_balance`: a zero-phase filter (4,096 taps, gain held within ±15 dB). It takes the DI's long-term spectrum,
   smoothed over a sixth of an octave, to the mean spectrum of other guitars' DIs, and restores the level.
2. `degrade("mild", …)` adds four faults and restores the level:
   - a tilt of up to ±3 dB around 1 kHz, with a seeded sign;
   - half mixed with a copy smeared by a 10 ms decay;
   - a soft clip at 0.9 of the peak;
   - another guitar's DI added 20 dB down.

- **The one thing redefined:** `others`, since October's folds do not cover these units. The guitar sources are BKS,
  each GOAT player and each panel band. A part's `others` are the drawn parts' true DI sections from every source but
  its own: at most 8 seeded sections a source (`others_for`, seed 20261202).
- Each draw is seeded per part. The mild draws are shared by `mild` and `avg+mild`.
- Each blur is applied to the whole rendered DI section (the 0.25 s lead-in included). It keeps the true DI's level
  and timing, so no row tests a level or timing error.

| Row | Reference on the search half | Dry guitar (render and judge) | Isolates |
|---|---|---|---|
| **Control** (`control`) | the clean record | the true DI | must reproduce the stored order |
| **Blurred DI** (`blurred`) | the clean record | `avg+mild` | the dry guitar |
| **Stem alone** (`stem-alone`) | X-LANCE's stem of the mix with no other guitar (`xlnoG@-3`) | the true DI | the stem as reference |
| **Stem, full mix** (`stem-full`) | X-LANCE's stem of the full mix (`xl@-3`) | the true DI | other guitars |
| Both, alone (`both-alone`) | the `xlnoG@-3` stem | `avg+mild` | the two together |
| Both, full mix (`both-full`) | the `xl@-3` stem | `avg+mild` | the product's setting |

**The single-blur rows, declared now (the review's change 1), run only on a trigger.** When the blurred DI **fails or
reads undecided** (undecided is the likely cell: keeping 25% of the Control's I is about −0.07), two more dry guitars
are rendered:
- `avg-only`: the average balance alone;
- `mild-only`: the mild artefacts alone (the same draws as in `avg+mild`).

Each is read against the clean record. Beside, each is also read against both stems (`avg-both-alone`,
`avg-both-full`, `mild-both-alone`, `mild-both-full`). They cost 1 h 26 min to 2 h 46 min of renders at the ladder's
rate, by the render mode the position check picks.

- **The pick:** the menu setting with the smallest search-half distance. A non-finite distance is passed over, and a
  tie goes to the lower menu position (`pick_index`).
- **The stems are separated again**, since the ladder kept only features. Each unit's two lender mixes at −3 are
  rebuilt by `lender_mix`, and their features must equal the stored builds (`rebuild_refusal`). Then X-LANCE runs on
  each mid. Each new stem's SI-SDR on half A must lie within 0.5 dB of the ladder's stored value, or the stage stops.

## 7. The reference half and the scoring half

- **The score** of any pick is its **stored** held-half judge through the true DI against the clean record. That is
  the trial's, the label's fresh score, S's, or Cen's (the ladder's `judge/cen`). The search record names each part's
  search and held halves.
- **Three steps that never mix:**
  1. `render`: each kept render is compared on the **search half's window only**, against the three references. Only
     those distances and the render's hash are stored. No held-half distance is ever computed from a new render.
  2. `pick`: reads those distances only, and writes `picks.json`, whose hash goes into the ledger.
  3. `score`: refuses unless the ledger holds that hash. Only it loads held-half values, and it checks that each
     part's pick re-derived from the distances equals the hashed pick.
- **Tested:** with every stored held-half value replaced by noise, the menus and the picks are unchanged
  (`test_menu_reads_held_finiteness_only`, `test_the_picks_read_no_held_value`).

## 8. The outcome

**Two numbers a row** (deciding pool; `part_numbers`):
- **I** = the pick less the **blind pick**, the mean stored held-half score of the part's 23 menu settings. It costs
  no render and is paired within the part. **I is the honest number** (the ruling on open question 1).
- **G** = the pick less Cen. It is kept as a guard, since the menu's mean quality inflates it (a blind pick's G is
  about −0.12).

**`row_reading`** (coded and tested before any run):

| Reading | When |
|---|---|
| passes | G and I are each decided better (the whole interval below zero) with the mean at −0.10 or beyond |
| fails | G's or I's interval rules out a gain beyond −0.05 (its lower end at −0.05 or above). An interval inside ±0.05 is worded "not readable by the score" |
| undecided | the rest. The write-up says what each interval rules out. Undecided is not failed |

**The dry-guitar reading** (`dry_reading`), R_TABLE's first column:
- the blurred DI passes → passes (through `avg+mild`);
- otherwise the single-blur rows are triggered, and no cell is read until they are;
- once read: either single passing → passes (through that blur alone, named in the reading); both failing → fails;
  anything else → undecided.

**`R_TABLE`**, read only after the Control's check passed (section 9). Each triple of readings is held by exactly one
row (`table_guard`):

| Dry guitar | Stem alone | Stem, full mix | Code | Reading | Next |
|---|---|---|---|---|---|
| fails | any | any | R-dry | A dry guitar this degraded does not work: with the right notes and a perfect reference, the comparison through it does not pick a heard size better than Cen and a blind pick | Stop the route at this degradation; to the user. Not a verdict on a better dry guitar |
| passes | fails | any | R-stem | The stem is not a usable reference even alone | Stop. Separator work gets a preset-level yardstick with a known prize (the Control's I) |
| passes | passes | fails | R-alone | It works where the target is the only or the dominant guitar | Continue, scoped to such windows; count how many songs offer them. A pass is necessary, not sufficient: before any product claim, a from-scratch search through the degraded inputs, scored on the held half against Cen |
| passes | passes | passes | R-dry-only | Only the dry guitar is missing | To the user: first a from-scratch search through the degraded inputs (the stem and the blurred dry guitar), scored on the held half against Cen; only then the second stage (a real note-matched dry guitar), the exam's parts and a blind sitting. A pass is necessary, not sufficient |
| undecided, or passes then undecided on the path | | | R-undecided | Not decided | To the user, with each row's intervals, what each rules out and the share of the Control's I it kept |

- **The Both rows** change no cell alone. If a "continue" cell's matching Both row **fails or reads undecided**, the
  write-up says so: the two faults may compound. It goes to the user before any second stage (`both_notes`). For
  R-alone the matching row is `both-alone`; for R-dry-only, both Both rows. When the dry guitar passed through one blur
  alone, its own Both rows are used.
- **Coded beside every row, at zero renders** (the review's change 3):
  - the label-free menu: 22 settings, the label left out of both the pick and the blind mean (`G_nl`, `I_nl`);
  - the share of picks that are the label;
  - the within-part Spearman correlation of the row's search-half distances with the true ones (the rendered
    Control's; for the Control itself, the stored values);
  - the share of the Control's I kept;
  - each set, with GOAT alone;
  - clean and crunch, and half A;
  - each cluster left out;
  - the share of picks equal to the Control's;
  - without the heavier lenders (`summarise`).
- **Power** (at planning, from stored scores; the Control exactly, other picks simulated by adding noise to the
  stored search-half scores, 40 repeats, with Drowning):

  | Pick | G, mean ± half-width | I, mean ± half-width |
  |---|---|---|
  | the Control | −0.39 ± 0.066 | −0.276 ± 0.035 |
  | a noisy pick (0.2 of noise) | −0.33 ± 0.076 | −0.21 ± 0.042 |
  | a noisier pick (0.4) | −0.27 ± 0.084 | −0.15 ± 0.047 |
  | a blind pick | −0.12 ± 0.078 | 0.00 ± 0.050 |

  - **A pass is well powered:** a true I of −0.15 passes about 95% of the time, −0.125 about 80%, −0.10 half.
  - **A fail is weakly powered.** It needs I's mean near zero or above. A truly blind pick fails only about half the
    time and otherwise reads undecided. A row keeping a small part of the Control's gain will mostly read undecided.
  - **Without Drowning** the panel has 3 DI files: I's half-width grows to about ±0.048 and G's to ±0.10 to 0.11
    (reproduced by the review; this draw's stored control in section 10).
  - The simulated noise is unstructured. A real stem or blurred DI may err in a structured way.
  - **False alarm:** a blind pick's I reaches −0.10 with odds under 1 in 1,000.

## 9. Controls and refusals

- **The stored control, at zero renders.** Right after the draw is saved, `draw` writes `controls/stored.json`: the
  Control's picks, G, I, the blind pick, the best menu setting and the label-free numbers, from stored scores alone,
  with and without Drowning, and the simulated picks' power on this draw. It is what the rendered Control must
  reproduce.
- **The Control's check** (`control_check`, `control`): each true-DI render's search-half distance against the clean
  record, compared with its stored value.
  - **Values:** at least 99% of the 2,806 within 0.005 in ln (`knob_ceiling.REPEAT_TOL`), and none beyond 0.02 (a
    non-finite render counts beyond).
  - **Order:** the rendered pick equals the stored one on every part whose stored best two differ by more than 0.01.
  - **If it fails,** the new renders are not the renders the stored scores describe: the plugin's build or state, the
    DI section, the lag, the trim or the menu's decoding differs. Then the stored held-half scores cannot be attached
    to any pick. **No row is read** (`pick` and `score` refuse), and the replay stops. That is not a finding about
    Direction 1. Any way on is an amendment, reviewed first.
- **The position check, before the main pass** (`position-check`): 12 seeded parts (4 a set, seed 20261203, never
  Drowning) on the true DI, each part's 23 settings in one primed process (288 renders).
  - If every stored value is reproduced within 0.005, the main pass renders each part and dry guitar in one primed
    process, as the stored trials were made (`render_menu`, Cen's priming render discarded).
  - If not, every kept render gets its own primed process (`fresh_render`), as the ladder's rows.
  - It also re-times the render rate (the review's costs item).
- **The stems:** the rebuilt mixes' features equal the stored builds exactly, and each new stem's SI-SDR on half A is
  within 0.5 dB of the ladder's. Otherwise the stage stops.
- **Trusted data.** Silent Waves is never drawn.
  - **Drowning** (the ruling on open question 3) is not dropped up front. Its 3 parts are rendered (about 2 minutes)
    and enter the rows only if `bleed --verdict clean` records the user's ear check before `pick`.
  - Otherwise they are dropped at `pick`, which lists them. The user is asleep, so expect the drop. Nothing waits on
    it.
- **Sealed sets:** V-real, the reserve, NS and R1 are not touched.
- **The hashes are on main first.** `phase_replay_draw` and `phase_replay_picks` each go in as their own small PR, checked by the orchestrator and merged by the executor. `draw` refuses unless `phase_replay` is on main. Every later step (blur, sep, position-check, render, control, pick) and `score` refuses unless the matching hash is in this checkout's ledger **and** in `origin/main`'s (fetched), this checkout's `learn/note_replay.py` equals main's, and its `phase_replay*` keys equal main's. Other ledger keys and other sessions' entries never block (`require_hash`, `require_on_main`, `replay_keys_refusal`).
- **Never overwritten:** every output file refuses to be written twice. The draw, the picks and the report are read
  once.
- **The machine** (the review's costs item):
  - Renders refuse while any separation runs (`separation_running`). Separations refuse beside any render or other
    MPS user (`preset_ladder.sep_blockers`).
  - At most 3 render processes run on the whole machine (`local_objective._wait_cap`). The other session's clean-start
    page runs before the separations or during this PR's review, or takes one shard while this replay uses two.
  - Render slots are asked of the executor.
- **The audit:** an independent agent with its own code recomputes every row from `dist/`, `picks.json` and the stored
  scores.

## 10. Stages, costs and the smoke checks

| # | Step | Cost | Stop |
|---|---|---|---|
| 1 | Ledger, code, tests and the PR's independent review, with a goal check | none | — |
| 2 | `draw`: units, menus, the stored control; the hash into the ledger | 11 s (smoke) | refuses if a set falls short |
| 3 | `blur`: 122 parts × 3 dry guitars | about 3 s a part (smoke), about 6 min | — |
| 4 | `sep`: 244 separations on the MPS, never beside a render | 5.4 s a stem (smoke), about 22 min | the rebuild and SI-SDR checks |
| 5 | `position-check` | 288 renders, about 8 min at the smoke's rate | chooses the render mode |
| 6 | `render`, 3 shards: 122 parts × 2 dry guitars × 23 settings | one primed process a part and dry guitar: 5,856 renders; each kept render primed alone: 11,224. At the ladder's measured rate, 1 h 26 min or 2 h 46 min | the disk guard |
| 7 | `control` | seconds | **a failed Control stops the replay** |
| 8 | `pick`; the hash into the ledger | seconds | — |
| 9 | `score`: the rows, then R_TABLE or the singles' trigger | seconds | one read |
| 9a | only on the trigger: `render --dry avg,mild`, `pick --singles` (hash), `score --singles` | 1 h 26 min to 2 h 46 min at the ladder's rate | one read |
| 10 | The raw hand-back, the independent audit, the user | none | — |

**The ladder's rate is a lower bound here.** It was measured with one judge of both halves for each kept render. Here
each kept render is compared with three references, on one half each. The position check re-times the rate.

**Smoke checks before this declaration.** They ran from this branch's code in three short processes: `draw`, then
the one-part render and the two blurs, then one unit's separation (msst-venv, PID 36491). They exited on their own.
Every output went to the session's scratchpad (`smoke/replay/`, 18 MB); nothing was written under `PF`, and
`PF/replay/` does not exist.
- **What they read, said fully:**
  - The draw's stored control read the true DI's stored held-half scores on the drawn parts (the planner's numbers,
    recomputed).
  - The one-part render computed 23 search-half distances against their stored values.
  - The separation computed SI-SDR only.
- **No degraded-input row was rendered, picked or scored.** No blurred DI was rendered, no stem was used as a
  reference, and nothing of any test row exists.
- **The draw is seeded,** so the merged `draw` will reproduce the smoke's parts. The smoke's files are not used by the
  run.

The results:
- **`draw` on the real records** (counts only):
  - BKS 40 parts on 8 DI files, GOAT 72 on 72 items, the panel 10 on 4 DI files (3 of them Drowning);
  - 0 dropped, 1 GOAT part passed over, Silent Waves' 2 excluded;
  - no part's stored lag differs from its search record's;
  - the file is 14.6 MB.
- **Its stored control, without Drowning,** reproduces the review's figures:
  - G −0.374 [−0.489, −0.260] and I −0.265 [−0.313, −0.217];
  - label-free I −0.273;
  - the blind mean −0.11;
  - the label picked on 94% of parts.

  These are the true DI's stored scores, the planning numbers above recomputed on this draw. No test row exists yet.
- **One part's 23 settings in one primed process** (a GOAT part, the true DI, 24 renders in 40 s): every search-half
  distance within 8.3e-5 in ln of its stored value.
- **Blur** on two BKS parts: the right length, the level restored exactly, correlation with the true DI 0.98 to 0.99.
- **One unit's two separations** on the MPS (msst-venv): the features rebuilt equal; SI-SDR 16.889 and 3.521 dB,
  equal to the ladder's stored values; 5.4 s a stem.

**Limits:** one MPS job, at most 3 render processes, launched with `setopt no_bg_nice` and caffeinate; the 31 GB disk
guard; PIDs recorded at launch and only those stopped; monitoring handed to the executor session. No training.

## 11. The review's changes, as built

**Blocking (all three).**
1. **Wording.**
   - The dry-guitar fail cell (R-dry), section 1 and the stop rule say "a dry guitar this degraded does not work", not
     "Direction 1 stops / no route can".
   - The single-blur rows `avg-only` and `mild-only` are declared now, each blur alone, with their reading
     (`dry_reading`). They are triggered when the blurred DI **fails or reads undecided** (`TRIGGER`), at 1 h 26 min to
     2 h 46 min.
2. **The pass cells.** R-alone's and R-dry-only's "Next" require a from-scratch search through the degraded inputs,
   scored on the held half against Cen, before any product claim. A pass is necessary, not sufficient (tested in
   `test_the_wording_and_the_pass_cells_next`).
3. **Side readings, coded for every row:**
   - the label-free menu (`G_nl`, `I_nl`);
   - the share of picks that are the label;
   - the within-part Spearman correlation of degraded against true search-half distances.

   A Both row that reads undecided is reported, not only one that fails (`both_notes`).

**Rulings on the open questions.**
1. I, the pick less the blind pick, is the honest number; G, the pick less Cen, is kept as a guard. A row passes only
   when both pass.
2. As in change 1.
3. Drowning is kept, as in section 9.

The review's costs note is also built: the position check re-times the rate, renders refuse beside a separation, and
render slots come from the executor.

## 12. What it can't say, and what the user must do

- **It can't say:**
  - how a real note-matched dry guitar performs;
  - anything about level or timing errors in the dry guitar;
  - anything on released mixes (the mixes are built, on six lender sessions);
  - anything by ear;
  - anything about effects.
- **Kept for later, not declared:** the same picks scored through the blurred DI (the product's own question, a user
  on another guitar).
- **The user:** nothing for the run. **Optional, about a minute by ear:** listen to Drowning's three amp-track sections
  for vocal bleed, before `pick`. Without that check the panel reads on 3 DI files and the intervals widen.
