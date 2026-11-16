# The real-song exam: the shipped model path on released mixes with known truth (plan)

Step 1 of the 2026-11-16 independent review's plan (summarised in [ROADMAP](ROADMAP.md) step 0). Code `learn/real_song_exam.py`, tests
`tests/test_real_song_exam.py`, ledger `pipeline-fix` `phase_exam`, `phase_exam_inputs`, `phase_exam_answers`,
`phase_exam_ear`. Data `~/ndsp-presets/learn/trusted-data/pipeline-fix/exam/`, answers and judge files beside V-real's
earlier reads (`vreal/answers/EX-*.json`, `vreal/judge/EX-*/`).

## Status

- **Declared 2026-11-17, before any run.** Planned on 2026-11-16 by a planning agent after the review, on the user's go
  to follow the review's plan; written into this repo by the implementer, checked against the source first (the
  changes are listed below).
- **Decided while the user slept (the orchestrator's defaults, for the user to confirm or change):**
  - **A baseline, not a decision.** Nothing is adopted from this read; the product default stays the user's call. V-real
    is read once, for this exam, on the user's go of 2026-11-16.
  - **The constant comes from Step 2** (the preset ladder), defined once: the all-labels constants Step 2's stage 0
    writes to `ladder/centres.json`. The labels' centre is arm C and the model's own constant is arm C-own. The
    planner's own constant (R-all's out-of-fold answers through `rc_setting`) is not built.
  - **Research runs: yes,** about 10 blinded headless generate runs, as the routing study ran them.
  - **The listening page is built** as section "The listening page" says, ready for the user; it is not published.
  - **The stronger ceiling** (a full every-control search on V-real) is not run.
- Nothing has run. Reviews and audits are run by independent agents at each checkpoint.

## The question

Given only a released mix and the part's time, how close is the shipped model path's preset to the real amp track,
played through the song's own DI? Against today's default (generate's research preset), the starting preset S, a
constant, and the stored search label.

**The primary row is M − R:** the model path against research, one preset per part each. Below 0 is closer. "Decided"
means the 90% band-clustered interval excludes 0. Every other row is beside it, a lead and never a verdict. Every row is
read by the score (J0), with a blind page beside.

| Outcome of M − R | What it would propose (nothing changes without the user) |
|---|---|
| Below 0, and the page doesn't put M below R | To the user: the model path as generate's default for clean and crunch. Step 2 still runs |
| Above 0 | The model path stays behind its flag; `reference/model-path.md` says it read worse than research on real multitracks; Step 2 runs first |
| Holds 0 | Undecided, stated with what the interval allows. No product change. This read becomes the baseline for later candidates |

Beside: M − C on M's amp (does the model read real songs per track, or is it a constant?), C − S (a lead for new
starting presets), L − S (the headroom on these songs) and (M − S) / (L − S), M-x − M (centred and off-centre apart),
and the stages one at a time off M: the class (M-lab), the selector (M-crop), released mix or unity sum (M-unity), the
amp pick (M against M3's mean and its best).

## How it differs from what was read before

| Read | Model | Input | Path | Truth |
|---|---|---|---|---|
| F41 (D_fix), F42 (FT) | Earlier models | The stored X-LANCE crop stem of a unity sum | A test path: the label's class, each amp forced, core controls; no EQ, pedals, gate, amp pick, loudness step, selector or research | V-real's amp tracks |
| F56 (FTm by ear) | FTm | As F42 | As F42 | The ear, on L0's clips |
| R1 | R-all (adopted) | The user's songs | The whole product path | None (the ear against a leaky stem) |
| **This exam** | **R-all, as shipped** | **The released mix (MP3 previews; Signs a magazine remix)** | **`scripts/model_preset.py` itself: the selector, X-LANCE, the answers, the 12 stock-DI renders, the amp pick and the loudness step; research's class from a blinded run** | **V-real's amp tracks, through each part's own DI** |

It may still be undecided for the reason every V-real read was: 7 bands.

## The items

V-real-11 as frozen (2026-10-26): 11 slugs, 10 units, 7 bands. V-real-10 rows sit beside every read.

| Unit | Band | Class (label) |
|---|---|---|
| It Was My Fault For Waiting ElecGtr3 | Atlantis Bound | clean |
| It Was My Fault For Waiting ElecGtr1 (T3's crop, 90-100 s) | Atlantis Bound | clean |
| Signs ElecGtr3 (the Mix Rescue remix) | Zeno | crunch |
| Colour Me Red ElecGtr02 | Diesel13 | clean |
| Colour Me Red ElecGtr03 | Diesel13 | clean |
| Femme ElecGtr5 | Wall Of Death | crunch |
| Get Out Of Bed ElecGtr2 | Magician's Nephew | crunch |
| Let's Dance ElecGtr3 | Szymon Skiba | crunch |
| Wickerman ElecGtr1 | Eat The Feeder | crunch |
| Wickerman ElecGtr2 and 3 (one input, two truths) | Eat The Feeder | crunch |

The truth side is V-real's verified DIs and amp tracks only; the mixes are inputs. Each slug's crop, measure DI, amp
track and judge lag come from the existing contexts (`pipeline_fix.vreal_ctx`, `arm_a_mega53.group_ctx`,
`trusted_data_t3.t3_group_ctx`).

## The inputs (`inputs`, zero renders, zero separations)

- **The released mix.** Each preview's sha256 must equal `alignment.json`'s. It is decoded whole (libsndfile, the
  alignment's own decoder) to a neutral-named float WAV at its source rate, so the product reads the very samples the
  alignment measured. A crop's place in the file is its session time less the stored per-crop offset (`alignment.json`,
  session frame − preview frame). Each stage F crop's GCC check is re-run on the decoded file and must equal the stored
  one; T3's crop (never measured in its preview) gets the same check here, and a failure drops the unit from the
  released-mix arms (a stop, for a decision before going on). Each crop's unity sum must match its `mix.wav`, and each
  session DI its `di.wav` (correlation at least 0.999), which ties the time bases.
- **The unity sum** (for M-unity only): the session's unity mono sum of the crop's `included_mix_tracks`, whole song
  (`mix_previews.unity_sum`), as a float WAV at 48 kHz.
- **The part's span** (it stands for "the user names the section"): 1-s blocks added outward from the crop while every
  member's DI stays within 25 dB of its crop level, at most 10 s a side (30 s in all), inside the preview's matched span
  and 2 s clear of the file's ends. The research run and the model path get the same span.
- **Truth-side measures, for strata only:** the target's pan in the released mix (the amp track's least-squares gain
  into each channel at the lag, within ±100 ms, that best explains both; S0's constant-power scale, centred at
  |p| ≤ 0.15, S0's centred stratum), its level against the mix, the share of the mix it explains, and the guitars
  playing (`trusted_data.vreal_playing`'s rule, T3's crop by the same code; dense at 5 or more). A unit is centred when
  every member is.
- Every input's hash and span go into the ledger (`phase_exam_inputs`) before any separation or research run.

## The arms

| Arm | What it is | How it is made |
|---|---|---|
| **S** | The label class's factory start on each amp | Stored (`vreal/judge/S`, 33 groups); re-rendered on M's amp for every slug (EX-S, 11 groups), required identical; S of M's class on M's amp beside (EX-Sm) where research's class differs, for the loudness row |
| **R** | generate's default, from research | One blinded headless run per unit (below). Its preset with the amp's dry recipe: its tonal edits kept, its time effects off (the routing study's tonal arm) |
| R-wet | R as written | The agent's own file |
| R-route | R's start alone | The agent's template with its own amp's dry recipe (a relative template path resolved against the run's folder); if only R-route fails, R and R-wet stand |
| **M** (primary) | The model path as shipped | `model_preset.py --song MIX --cls <R's class> --part A B --part-from "the user"`, default version. A heavier route runs as crunch and is flagged; a unit with no passing research run runs on the label's class |
| M3 | M's answers on all three amps | From M's `answers.json` |
| M-x | M with `--version xlst_mdxc` | `--start` at M's own window, so only the separation changes |
| M-lab | M with the label's class | Only where R's class differs; M's window is copied in, so only the class changes |
| M-crop | M with `--start` at the crop | No selector (read 3's window) |
| M-unity | M on the unity-sum song | `--start` at M's own window (in session time), so only the input changes. Mono, so no `xlst_mdxc` twin |
| **C** | Step 2's labels' centre (all labels) | `ladder/centres.json`'s `centres.cen` (the ladder's shape), its `model_sha256` required to be the adopted pair's and its `hold` C3-cabS; the label class on all three amps; on M's class and amp beside (EX-Cm) where research's class differs |
| C-own | Step 2's model's own constant (all labels) | `centres.aconst`, the same checks: so it is the adopted pair's own constant (EX-Cown, EX-Cownm) |
| C-pick | C through the model path's pick | `product_path render` once per class on C's three presets (24 stock-DI renders), then `product_path pick` per unit with M's stem features |
| **L** | The stored search label, as ceiling | `arm-a-mega53/F-perfect-sep/ZT` `settings.best` per slug, amp and search half (V-real-10 only), re-rendered, judged on the held half. 52 evaluations over the core controls: a lower bound on the headroom |

- **Stored comparators, zero renders:** FT, D_fix and RcG from F41's and F42's renders, each read on M's amp, beside.
- **Effects:** every model-path arm keeps the time effects the model path writes (S's, off); research's effects are not
  added. The amp track is dry, and J0 was never validated on effects. Only R-wet carries the agent's effects.

**The research runs.** One fresh headless `claude -p` per unit, the routing re-check's call (`research/generate_routing.py`
`_claude`: its model, Claude Opus 5.5, its tools and flags), with the scrubbed plugin (the routing study's plugin parts
at this branch's commit, checked to name no V-real title or band).
- **A fresh root,** `~/gtr-q`, holding only the venv (the routing study's, copied whole, checked to run as itself), the
  plugin, the runs' settings and this exam's runs. The routing study's own folder (`~/gtr-session`) holds runs on these
  same songs, their results and arms, so it is not used.
- **Each run's settings** are the routing study's (which deny reading the data root, `~/projects`, the session
  transcripts and the temp scratch space) plus `~/.claude`, `~/gtr-session` and every other run's folder of this exam.
- Each gets the whole song as `song-NN.flac` (rewritten with no metadata; this copy alone is clipped to ±1), the title
  and artist, the span, pack Morgan, no listening page, an empty data folder (so no learned notes), and no model flag.
  A run with no result is asked once more with the re-check's non-answer.
- **The audit (guard 5)** excludes a run on any of: a tool call naming the project's data, repository, documents, tests
  or the earlier routing runs; a call naming a path outside the run's own folder, the plugin, the venv, the factory
  presets (`/Library/Audio/`) and ordinary scratch space (`/tmp`, `/var/folders`), or under Claude's own scratch space;
  a relative `../` in a call; the user's account name (any case) in a web search or fetch; a web result naming the
  project; a file tool's result naming the repository, the earlier runs, Claude's folders, the data root's `learn`,
  `references`, `listening` or `handover` folders, or another run's folder. Other outside paths a result names are
  recorded, not a stop (the plugin's own text names its default data root). A wrong plugin version or model, or no
  readable result, excludes it too.

**When research fails** (declared now, the orchestrator's default):
- A unit takes its first run that passed. `research-prepare --again` makes a fresh folder only for a unit whose runs were
  all excluded, and only once (two runs at most); a passing R is never replaced by a later draw.
- A unit that still has no passing run has no R: M runs on the label's class (so it has no M-lab), the unit leaves the
  primary row (M − R) and the other R rows, and stays in every other row. The count is stated beside the primary.
- If no unit gets a passing run (the runner does not work here), the exam stops and hands back for the user.

## The guards (each a stop; before any judge render)

1. The ledger holds `phase_exam` (every command checks).
2. **The leakage guard, extended to C3r-all:** the adopted base is C3r-all, and no V-real band or song is in any
   training input of the adopted pair (W's plugin and held rows, every real unit of BKS, GOAT, cap1, n12 and the panel,
   a capture unit by its DI's band and session, each real unit's 25 backings from its stored inputs, every backing-pool
   entry) nor among the amp pick's four stock DIs (A1's).
3. The adopted pair's checkpoints hash to their run records and to `adopted-model.json`.
4. **The chain wrapper reproduces one stored R1 run** (`r1/cut-it-out`): from that run's stored window files, the
   answers, the stem features, the 12 stock-DI renders' loudness, the pick's distances (to 1e-9), the pick, the output
   gain and the written preset must equal the stored ones. It proves the wrapper, the environments, the model, the stock
   DIs and the renderer reproduce R1's stages from the answers to the written preset; it does not test the selector,
   X-LANCE or `xlst_mdxc`. It reads `window.npz`, which holds 10 s of the R1 song's mix and its stem, copied to
   `exam/r1-repro/work` (nothing of it goes to git); the song's own file is not read, and the window stage is not
   reproduced (it would need the song's audio, which stays sealed).
5. Research transcripts are audited (above) before R's class is used.
6. Every arm's answers file is hashed into the ledger (`phase_exam_answers`) before the first judge render; the renders
   and the report refuse otherwise. Each judge record carries its time, so the audit can check the order.
7. S's positive control passes (`s_positive_control`, 60 of 60), and EX-S's renders are identical to phase 4's.
8. L's fresh judge values are set beside the stored ones; a gap above `K.REPEAT_TOL` is reported, and the fresh values
   are used.

- **The guards gate what follows:** `chain`, `c-pick`, `answers`, `render` and `report` refuse unless `exam/guards.json`
  (guards 2, 3 and 7's stored half) and `exam/r1-repro.json` (guard 4) exist and passed; both files' sha256 go into
  `phase_exam_answers`.
- **The classes are checked:** the chain records `research.json`'s and `inputs.json`'s sha256 when it starts;
  `c-pick` and `answers` refuse if either changed, and `answers` refuses if any chain run's or C-pick's class is not
  research's model class (the label's for M-lab). The decoded mixes and unity sums are re-hashed at `research-prepare`
  and `chain`.

## Scoring and statistics

- **The judge:** `knob_ceiling.judge(ref, render, measure DI, judge lag)`, each answer fresh and primed in its own
  process (`vreal_render`'s recipe), against `reference.wav`, on both halves. J0 matches level itself, so the loudness
  step is not scored; M against M3 on M's amp checks it, and M's render loudness against S's on the same DI is its own
  row.
- **Value:** ln of the distance on the held half. A one-preset arm gives one value per slug and half; S, C, C-own and
  M3 on "three amps" are the mean of ln over the amps; L is read on its held half only. A held half where S is not
  finite on some amp drops for every row (counted; not a stop); a refused answer scores as S on its amp (the
  established V-real rules). Only a missing answer stops the report.
- **Unit:** the part (10), in its band (7); Wickerman ElecGtr2 and 3 average into one unit.
- **Interval:** band-weighted mean, 90% band-clustered t, 6 df (`pipeline_fix.clustered`).
- **Beside every row:** part-weighted, bands and parts on each side, leave one band out, clean (2 bands) and crunch (5),
  dense and sparse, centred and off-centre, V-real-10.
- **Rows** (`row_specs`): M − R (primary); M − S, M − S on M's amp; R − S, R − S on R's amp; R-wet − R, R − R-route,
  R-route − S; M3 − S per amp and on three amps; M − C and M − C-own on M's amp; M − C-pick; C − S, C-own − S,
  C-pick − S; M-x − M; M-lab − M (its units only); M-crop − M; M-unity − M; M − M3's mean, M − M3's best amp (an
  oracle: the amp is picked on the half it is scored on); L − S and M − S on V-real-10, and (M − S) / (L − S); M − FT,
  M − D_fix and M − RcG on M's amp (stored). The R rows read the units with R; R-route's, the units with R-route.
- **The loudness row:** M's render loudness against S's of M's own class on M's amp (EX-Sm where the classes differ).
- **Zero-render tables:** research's class against the label; each chain window (start, how chosen, exposure, overlap
  with the crop, the target's DI activity in it); each amp pick and its cosine margin; M's knob distance from C and
  C-own; M's movement between its input variants against its movement between units of one class (the review's "is it
  reading the separator" check).
- **What is decidable, said before the read:** about ±0.10 to ±0.15 for M − R and M − S (one amp per part), about
  ±0.05 to ±0.10 for same-amp pairs; L − S is expected decided (the stored label reads −0.192 [−0.239, −0.145]
  against S on V-real-10, 7 of 7 bands, recomputed here from the stored files); M − C and M-x − M probably not. An
  interval that holds 0 is undecided, not "no effect".

## The listening page (`phase_exam_ear`; built at checkpoint 5, not published)

- L0's design (`learn/ear_vreal.py`), which the user has answered twice on these parts: the 10 units, each on L0's
  stored held half; guitar only, each candidate through the part's DI beside the amp track, aligned by the judge lag,
  looped, −23 LUFS, instant switch; headphones asked for.
- **Candidates:** R, M, C-pick and L, each on its own amp (L on the amp whose label scores best on the page's search
  half, by its own search objective). Identical presets share a letter. It Was My Fault ElecGtr1 has no stored label,
  so its card holds three letters.
- **The audio is the judged render itself,** kept at judge time, so each clip's hash is the judged render's by
  construction (checked again when the page is built); the page needs no renders.
- 10 cards and 2 repeats (seeded, at least 4 items apart, every preset on another letter in a repeat). Ranks with ties
  allowed; closeness, confidence and a note optional (C4's practice).
- **Read:** M over R first: the share of units with M above (a tie a half), its 90% band bootstrap (L0's), rank and
  closeness gaps, J0 on the same clips beside, and the repeats. A share clear of one half reads "heard above (or below),
  one listener"; otherwise "not known by ear". By L0's simulation a model truly ahead on 75% of items clears about half
  the time.

## The independent audit (declared; the planner's section 12)

A separate script, by an independent agent, that imports nothing from `learn/real_song_exam.py` or
`learn/pipeline_fix.py`, before anything is written up:
- recomputes every row from the raw judge files with its own value, drop and interval code;
- re-derives each preset: M's amp is the least of its stored distances and its output gain follows the loudness rule;
  C and C-own equal `ladder/centres.json`'s entries; L equals the stored ZT label; R equals the agent's file with its
  amp's dry recipe (effects off); C-pick's amp is the least of its distances;
- checks that each answers file's sha256 was in the ledger (the commit's time) before the first judge record's `time`,
  and that the guards' records were in it too;
- re-renders 6 seeded groups in its own process and compares the render hashes;
- re-derives the page's read from the listener's raw export and each letter from the key.
An independent reviewer reads the plan and the code before any run, and the results before the write-up. Each brief
carries the goal check.

## The stop rule

One build, one read. No arm, span, class, window or preset changes after the first judge render. The score rows are
reported once every judge file exists and the guards pass; the page is read once. A rerun happens only for a failed
guard, and is reported. Nothing is adopted. Afterwards V-real is recorded as read once more; a later candidate is
compared with these stored renders, hash-checked, and its read declared as such.

## Runtimes and resources (measured rates only)

| Work | Amount | Measured rate |
|---|---|---|
| Chain runs, default version | up to 40 (M, M-crop, M-unity, M-lab) | R1: 7 runs in about 7.5 min |
| Chain runs, `xlst_mdxc` | 10 | 2.5 min of CPU for a 28-s part (`reference/model-path.md`) |
| Stock-DI renders inside the chain | up to 600, plus C-pick's 24 and the R1 reproduction's 12 | included above |
| Judge renders | at most about 600: one-preset arms 8 × 22, M-lab, EX-Cm, EX-Cownm and EX-Sm at most 22 each, EX-S 22, three-amp arms 3 × 66, L 120 | F41: 660 in about 9 min on 3 shards |
| Page renders | none (the judged renders are played) | |
| Research runs | 10 headless | the routing re-check's 83 runs: median 1.5 min each (1.0 to 2.7), from their transcripts |
| **Renders in all** | **at most about 1,240 (cap 1,400)** | |

- At most 3 render processes machine-wide (`local_objective._wait_cap`; the render command is registered in
  `local_objective.RENDERS`), each render primed in its own process; launched with `setopt no_bg_nice`.
  `product_path separate` is registered in `local_objective.SEPARATIONS`, so other jobs' renders wait for the chain's
  separations (and R1's).
- The chain runs one at a time and waits before each separation while any other MPS job (a separation, or a training)
  runs. Disk: about 0.8 GB of inputs (decoded mixes and unity sums), about 0.3 GB of chain work, about 0.2 GB of kept
  page renders; the 31 GB guard holds every render.

## The commands, by checkpoint

`MAIN` is the main checkout's `.venv/bin/python`; every command runs from this worktree.

- **CP2 (inputs and guards):** `$MAIN -m learn.real_song_exam inputs`; the printed `phase_exam_inputs` record committed
  to the ledger; `$MAIN -m learn.real_song_exam guards`; `$MAIN -m learn.real_song_exam r1-repro` (12 renders);
  `research-prepare`, `research-route` (background), `research-collect`; if a unit's runs were all excluded,
  `research-prepare --again KEY`, `research-route`, `research-collect` once.
- **CP3 (the chain):** `chain` launched detached (`zsh -c 'setopt no_bg_nice; nohup caffeinate -i $MAIN -u -m
  learn.real_song_exam chain > LOG 2>&1 &'`, its PID recorded; the done line `EXAM CHAIN DONE`); then `c-pick` (needs
  `ladder/centres.json`) and `answers`, whose printed `phase_exam_answers` record is committed before any judge render.
- **CP4 (the judge and the report):** three shards, `render --shard 0/3`, `--shard 1/3` and `--shard 2/3`, launched
  detached the same way (each log's done line `EXAM RENDER DONE 0/3` and so on); then `report --label exam` (it
  refuses if any report exists: V-real is read once).
- **CP5 (the page):** `page`; the user's export read by `score --answers FILE` after the sitting.

## Changes from the planner's plan, and why

- **C** is Step 2's all-labels constants (the orchestrator's choice), read in the ladder's own shape
  (`centres.cen`, `centres.aconst`) and checked to be the adopted pair's (`model_sha256`, `hold`), not R-all's
  out-of-fold answers through `rc_setting`; the model's own constant is a second arm, C-own. Where research's class
  differs from the label's, C and C-own are also rendered on M's class and amp, so M − C compares like with like and
  C − S stays on the label's class.
- **The research runs** use a fresh root, per-run settings and a wider audit (above), and the research-failure rule is
  declared ("When research fails"): the plan said only "rerun once".
- **M-x and M-unity** start at M's own window, so each changes one stage; the planner's commands reran the selector.
- **The guards gate** the chain, the renders and the report, and their records are hashed into the ledger; the classes
  and `research.json` are checked and locked between the chain and the answers.
- **S of M's class** (EX-Sm) is rendered where the classes differ, for the loudness row.
- **The report** drops a held half where S is not finite, as the plan says, and stops only on a missing answer; it
  runs once.
- **Guard 4** reproduces the answers, renders, pick and preset from the stored R1 window, not the window: re-running
  the selector would read the R1 song's audio, which the rules keep sealed.
- **S's re-render** covers M's amp on every slug (11 groups), not 10 seeded groups: the same identical check, and it
  gives the loudness row its S render on M's amp.
- **The page plays the judged renders,** kept at judge time: no page renders (the plan counted 80), and the clips'
  hashes equal the judged renders' by construction.
- **The page's L** plays on the amp its stored label scores best on the page's search half (the plan said "its own
  amp" without a rule). It Was My Fault ElecGtr1 has no stored label, so its card holds three letters, not four.
- **Closeness is optional** on the page, as on C4's, ranks required.
- **The judge render count** is at most about 600, not "at most 448": R-wet, R-route, C-own, M3's three amps, EX-Cm,
  EX-Cownm and EX-Sm are rendered beside. In all at most about 1,240 renders, inside the plan's cap of 1,400.
- **The research runs' data folder is empty,** as in the routing study, so no learned notes reach them; an installed
  plugin would read the user's own notes.
- **The research copy of the song is FLAC, clipped to ±1**; the model path reads the exact float decode.
- **M-lab reuses M's window,** so the row isolates the class step.
- The planner's numbers checked at the source here: V-real's composition and stored S groups, the released mixes and
  their stored crop checks (all 10 stage F crops covered; T3's crop not yet measured), the ZT labels (10 slugs of
  V-real-10, 52 evaluations) and their −0.192 [−0.239, −0.145] against S, 7 of 7 bands, and C3r-all's 461 real units
  (GOAT 214, cap1 121, BKS 102, n12 12, panel 12). n12's captures play library DIs from Cambridge sessions, which is
  why guard 2 checks every capture unit's DI session too.

## Risks, and what the read cannot say

- **Seven bands.** Only a large effect shows; undecided is not failed.
- **Dense songs.** Most parts sit among 4 or more guitars, and the product cannot tell the named guitar from the
  others. The user's songs are mostly exposed leads; a null here is not a verdict on those.
- **The truth is the raw amp track,** not the guitar as mixed: a preset that copies the mix's EQ counts as wrong.
- **Research is thin for these bands,** so R is close to a class and a starting preset; on a famous song research has
  more to use.
- **The judge:** treble and drive weigh above the ear, effects below; the label's ceiling is the judge's.
- **One listener,** hearing these parts a third time. **S's edge** of about 0.025 from its choice sets. The measure DI
  is the average-guitar one.
- **Inputs:** MP3 previews; Signs is a remix; one research run per part is one draw (a rerun changed 4 of 34 routes).
- **`xlst_mdxc`** removes a guitar off centre by design: its row means something on centred targets only.
- **V-real is development data,** read about ten times before 2026-10-23 and several times since (P4, F41, F42, F54,
  F56); its listener has heard these parts twice; S was chosen on sets holding 8 of its 11 clips. Reading the shipped
  model once, with nothing chosen, is fair; calling it a final exam is not.

## Open questions for the user

1. **The seal.** Is it right to record V-real from now on as the real-song development yardstick, read many times,
   rather than "the one final exam"? A true final exam needs fresh multitracks with a DI, an amp track and a released
   mix; none are on disk outside training.
2. **The defaults above:** a baseline only; C from Step 2; the research runs; the page.
3. **The sitting:** one more page on these 10 parts, 12 cards of up to 4 clips, guitar only.
4. **Should this read carry the default decision at all,** given dense songs and ±0.10 to ±0.15?
5. **Later:** a full every-control search on V-real as a stronger ceiling (about 15,000 renders), worth it only if the
   stored ceiling limits the reading.

## Not verified yet

- That T3's crop passes its check in the preview, and every target's pan and level (the `inputs` step measures them).
- That the headless runner works with today's skill and Claude Code (the first research run shows it), and how long a
  run takes now.
- That the stored ZT labels render to their stored scores under the fresh-render rule (guard 8 reports it).
- X-LANCE's seconds per clip here; the plan uses R1's wall time per run.
- `ladder/centres.json` itself (Step 2 writes it): the loader reads the ladder's `centres.<cen|aconst>.<amp>.<class>`
  = `{select, settings}` (its `all_labels.<Cen|Aconst>` variant alike), checks each select names its amp, the file's
  `model_sha256` and `hold`, and refuses anything else at `c-pick`, before any judge render.
