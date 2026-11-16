# The preset ladder: where is the preset lost?

**Status:** declared 2026-11-17, before anything runs. Step 2 of the plan the user approved after the independent review
of 2026-11-16 ("follow the review's plan"). Ledger `preset-ladder` (`phase_l0`, `phase_l1`; stages 2 and 3 are declared
before they run). Code `learn/preset_ladder.py`, tests `tests/test_preset_ladder.py`. Data `PF/ladder/` (`PF` is
`~/ndsp-presets/learn/trusted-data/pipeline-fix`). No sealed set is used: no V-real, the reserve, NS or R1 audio.

## Why

The adopted model (R-all) trained on real amp tracks in non-guitar backings, with no separator and no other guitar. The
product feeds it an X-LANCE stem of a full song. No measurement runs the product's input against a known truth, and the
model's answers sit close to one preset per class (F59: 2.5% of the label variance; the review's audit of R-all's
out-of-fold answers: spread 16–21% of the labels', losing to the cell mean in about 60% of knob cells). Step 1 (the full
chain on V-real's 10 parts) resolves about ±0.07, too wide to say where the preset is lost.

The ladder answers that on C3r's held-out real units, where every unit has its own DI and a label: the same fold model
reads each unit from a ladder of inputs, and each answer is rendered through the unit's DI and judged against its real
amp track. Only the input changes between neighbouring rows, so each step's cost is measured by the preset itself.

**The goal check:** the decision it feeds is whether the model path earns its place over a fixed preset on product-like
input, and which part of the chain (the backing, the separator, the other guitars, the reader) to work on next. It ends
after stage 3 at the latest, and each stage can end it (section 6).

## How this differs from what came before

- **P2's ladder (pipeline-fix P2, F13–F17)** trained a separate model per rung (clean, backed, with other guitars,
  stem) on plugin-rendered targets and read them on plugin sets. Training and input changed together, and the backed
  rung had no skill left, so F17's "the other guitars add no further loss" was a floor effect. Here one trained model
  (R-all's fold pair) reads real held units; only the input changes.
- **N5 and N5b (F55–F56)** read FTm on X-LANCE stems of the backed mix: no other guitars, "the kindest stem", and FTm
  held every control outside `K.space` at S. N5b found no stem cost by the score. The ladder puts other guitars in the
  mix, sets the exposure, and reads R-all with every learned control.
- **A2s (F90)** checked the amp pick on stems, with the answers held from the backed mix and no other guitars.
- **S0 and S1 (the separation plan)** built mixes with other guitars, but scored stems by SI-SDR and a feature cosine,
  never by the preset. The ladder uses S0's recipe and scores the preset.
- **V-real (F41, F42, F56)** is real songs, but earlier models, 10 parts and about ±0.07.

**Why it may still fail:** the mixes are built, not songs (the target is foreign to its session, the other guitars are
plugin renders, one centred layout); every read is by the score (J0), whose labels sit on the EQ's rails (the review's
G5); the sets are thin (BKS is one band, most GOAT DIs one player). Section 12 lists what the read can't say.

## 1. Questions, primaries and the decision rule

Every read is by the score: ln(d_row / d_against) on the held half, below zero closer. "Decided" means the 90% interval
on the deciding pool excludes zero. No pass bars: sizes are reported, also as a share of the Cen-to-label gap.

| # | Question | Primary rows (deciding pool) | Stage |
|---|---|---|---|
| Q1 | Does R-all read, or is it a constant, on its best inputs? | `clean-kind` − Cen; `mix@-3` − Cen; `clean-kind` − Aconst; `mix@-3` − Aconst | 1 |
| Q2 | On product-like input, does the model path beat a constant? | `xl@-3` − Cen | 2 |
| Q3 | What do the separator and the other guitars each cost? | `xlnoG@-3` − `mix@-3` (the separator alone); `xl@-3` − `xlnoG@-3` (the other guitars) | 2 |
| Q4 | Does `xlst_mdxc` buy it back? Does exposure? | `xlmdxc@-3` − `xl@-3`; each row at drawn, −3 and 0 dB | 3 |

Q1's outcome is read from its four primaries: "reads at product exposure" when `mix@-3` − Cen or `mix@-3` − Aconst is
decided below zero; else "reads only an isolated guitar" when `clean-kind` − Cen or `clean-kind` − Aconst is; else
"neither".

| Outcome | Next |
|---|---|
| Q1 neither | The reader is the limit. Step 3 takes Cen as the candidate start (Step 1 confirms on songs). Separator work stays parked; Step 4 isn't run for this model. Stage 2 shrinks to a harm check: `xl@-3` on the stage 3 subset (148 separations, 456 answers); then Step 5. |
| Q1 reads only an isolated guitar | Full stage 2, with `clean@-3` (the target at the product's level) beside; Steps 4 and 6 have their case. |
| Q1 reads at product exposure | Full stages 2 and 3. |
| Q2 not shown better than Cen | On product-like input the model path hasn't earned its place over a constant. Decided worse: it leaves the road to default. |
| Q2 decided better | The model path keeps its claim; Step 1 confirms. |
| Q3: a decided cost for the other guitars | Its size is the target any separator work must recover by the preset; stage 3 runs `xlmdxc` and `xl-real`. |
| Q3: a decided cost for the separator alone | Step 6 (fine-tune on the product's input) gets a measured target. |
| `clean@-3` − `xl@-3` | The most a perfect separator could buy. Small or undecided: separator training stays parked. |
| Q4: `xlst_mdxc` decided better | A case for it as the centred-part route (needs a centre detector; Step 1 holds the arm). Undecided: stays off. |
| Q4: the rows improve with exposure | Build Step 4's exposed-window finder; R1's windows say how often songs offer each level. |

## 2. Units, models, arms

- **Units:** exactly `full_controls_c3r.read_units(state())`: 480 parts on 400 units. BKS 40 units × 3 amps (8 DI
  files; 51 clean and 69 crunch parts), GOAT 215 (130 items; 110 clean, 105 crunch), cap1 121 (19 creators; 61, 60),
  n12 12 (8 creators), the panel 12 (5 DI files, 4 bands). Each carries C3r's fold, lag, cluster, class and files.
  Nothing is re-drawn. One GOAT part has no label (a read-only unit); it counts for every row but the label's.
- **Model:** the part's fold pair, `P.load_run(P.ft_name(fold, base="C3r-all"), seed, "best")` for both seeds, pooled
  by `full_space.readout`, held as C3r's answers (`answer_hold`: C3-cabS), told the unit's class and amp. This is
  `full_controls_c3r.cmd_predict` with only the input changed; stage 0's control checks the ladder's copy reproduces
  C3r's stored answers exactly.
- **The amp is told, never picked:** BKS on each of three amps, the other sets on their record's amp. Every arm of a
  part shares it, so the reader is read apart from the amp pick.
- **Fixed arms:** S and the label (stored: `C3R.s_judges`; each C2 or C2r output's fresh label score, one direction a
  record, on its held half); Cen and Aconst (new, section 4).
- **The stage 3 subset (148 units, 228 parts, seeded `subset_draw`):** every BKS (40) and panel (12) unit; per fold 6
  clean and 6 crunch GOAT units, one a GOAT item (48); per fold 6 clean and 6 crunch cap1 units, at most 3 a creator
  (48). n12 is read beside only. Every fold and class has room for it (checked: at least 13 GOAT items and 8 capped
  cap1 units in each fold and class).

## 3. The inputs

Each unit gets one **lender**: a D_CC example from another session that lends it other guitars, a backing, a mix
loudness and a mastering draw (`lends`).

- **The pool:** D_CC's recipe split as W trained on it (`pipeline_fix.recipe_inputs`, pinned "dropped": W's training
  and FS examples, so no NS song, no runaway and no doubled example), bands other than BKS (BKS's DIs are real training
  rows of every fold model), whose other guitars (the `others` render plus the session's other-guitar amp tracks) are
  louder than −50 LUFS. 1,243 candidates, 22 out as silent: clean 60 sections (The Travelling Band 31, Hazael 27,
  Dunning Kruger 1, Forkupines 1), crunch 60 (Forkupines 51, Storm Of Particles 4, The Travelling Band 3, Ale Lak 2).
- **The draw:** a section uniformly among the unit's class's sections, from any session but the unit's own DI's (n12's
  units sit on The Travelling Band's and Ale Lak's DIs), then an example of it; seeded by the unit
  (`random.Random(f"20261161|ladder-lend|{unit}")`). Lent (a dry run of the code, to be re-run as stage 0): clean 203
  units (The Travelling Band 102, Hazael 88, Dunning Kruger 7, Forkupines 6), crunch 197 (Forkupines 173, Storm Of
  Particles 13, The Travelling Band 8, Ale Lak 3). The two heavier bands lend 16 crunch units; every primary is read
  again without them, beside.
- **The mix at exposure E** (`lender_mix`; S0's recipe with the real unit as the target):
  - the unit's amp section (`P.real_amp_track`), levelled to the lender's target loudness (`P.dfix_level`);
  - placed as S0's centred stratum, seeded by the unit: the target within ±0.15, every other guitar (the `others`
    render and the amp tracks) on one side at ±0.6 to ±1.0, the backing by `sep_s0.backing_pan` (bass, kick, snare and
    vocals centred, a stereo file keeps its image);
  - the ratio set on the mix's mid, (L + R) / 2, which the model and the default separator read: the target E dB under
    everything else (other guitars and backing together), by `trusted_data.mix_gains` with the ratio replaced; "drawn"
    keeps the lender's drawn ratio; the mix at the lender's drawn loudness either way;
  - mastered by the lender's draw (S0's linked compressor on the mid, then each channel clipped at −1 dBFS);
  - **full** is that mix; **noG** is the same with every other guitar removed at the same gains (the stems keep their
    level, so the two differ only by the other guitars). noG's target sits above the backing alone: in the dry run at
    −3 dB it was −1.7 to +2.2 dB over the bare backing;
  - recorded per unit: the built target-to-rest ratio of each (mastering moves it a little: under 1 dB in the dry run), the target against the
    other guitars, the mid's loudness and sha256; for each stem, its loudness less the mix's, its SI-SDR and the other
    guitars' leak on half A (`sep_s0.si_sdr`, `leak_db`).

| Row | What the model reads | Style | Separations | Stage |
|---|---|---|---|---|
| `mix-drawn` | D_fix variant 0, as C3r read it (stored answers and scores) | train | none | 0 |
| `clean-kind` | the amp track alone at its fold models' training inputs' median loudness (`real_predict_5b2`'s clean branch, D_fix's `-clean` read) | train | none | 1 |
| `mix@-3` | noG's mid, read as the training inputs are (`half_features`, no separator) | train | none | 1 |
| `xl-v0` | A2s's stored stems of the variant-0 mix (no other guitars; BKS 38 of 40 units, no n12) | product | none | 2 |
| `xlnoG@-3` | X-LANCE on noG's mid | product | 1 | 2 |
| `xl@-3` | X-LANCE on full's mid: the product's default | product | 1 | 2 |
| `clean@-3` | the target as it sits in full's mid: a perfect separator | product | none | 2 |
| `xlmdxc@-3` | `product_path.StereoCentre` on full's stereo pair | product | 1 stereo + MDX23C | 3 |
| `mix@drawn`, `mix@0`, `xl@…`, `xlnoG@…` | the same rows at the lender's drawn ratio and at 0 dB | as above | as above | 3 |

"Train" style is the signal at its own level, as the model's training inputs (`direct_stems.half_features`). "Product"
style brings the stem by the gain that takes its own mix to −12.25 LUFS (`DE.inference_gain_db(mix, PP.MIX_LEVEL)`,
`DS.step4_half`), as `product_path` does; `P.vreal_model_input` either way. Both halves are read; half A, the product's,
is reported apart. `full@E` (the full mix with no separator) is built beside `mix@E` and rendered only if stage 3 names
it.

**Conditional rows (stage 3, only where section 6 names them):**
- `xl-real@-3`: the mix's other guitars replaced by one real amp unit no fold model of the target saw (no DI or creator
  shared with any of its training rows; another item and creator than the target), at the others' loudness. It checks
  that the plugin-rendered others don't drive a cost.
- `pool@row`: the fold model's answers averaged over up to 5 other windows of the same recording, at least 10 s from the
  unit's section (`P.rigo_records`' rule), continuous controls by mean and switches by majority.

## 4. The two constants

Both are built per fold k, amp and class from model k's real training records only (`C3R.split(entries, k, False,
"all")[0]`, `records_of`), each record weighted by how often an epoch shows it (`mixed` then `cycled_to`, exactly as the
training cycles each source to 300; RcBG weighted its labels the same way). No record of fold k or sharing a DI file or
creator with a fold-k unit enters (checked).

- **Cen, the labels' centre:** the records' training labels (`st["sources"]`) head by head under C3's training mask
  (`full_space.encode`'s sounding mask times `C3.head_masks(keys_fn(...))`): continuous heads the mean in the model's
  unit space, switches the share on (on above one half, so the majority, a tie off), mics the most common (a tie to S's
  when among the tied, else the lowest); a head no record labels stays at S. Then `full_space.answer_settings` and the
  answers' hold. It is the real labels' centre, not the best constant under the model's loss (a mixture likelihood, and
  the fine-tune also trains on W's 1,787 plugin rows).
- **Aconst, the model's own constant:** model k's readouts on those records' stored variant-0 inputs, both halves,
  averaged the same way (continuous the mean answer, switches the share answered on, mics the most common). R-all −
  Aconst is per-unit reading plus any shift of the model's mean answer between its training inputs (in-sample) and the
  row's input; the knob reads report that shift.
- One answer per part, rendered once and judged on both halves.
- **The all-labels versions** (every training record, the all-labels R-all pair), never read on these units, go to
  `PF/ladder/centres.json` for Steps 1 and 3: per amp and class, `select` and `settings`, the hold C3-cabS, the output
  gain S's (the product's loudness step sets it).

## 5. Answers, renders, scores

- **Answers** (CPU, `$TORCH_PY`): `PF/ladder/answers/<row>.json`, C3r's layout; a part with no input (no A2s stem) is
  counted and left out.
- **Renders** (`.venv`): `full_controls_c3r.cmd_render`'s body. Each answer in its own primed process
  (`AM.fresh_render(CB.new_renderer, …)`) through the part's DI, trimmed, `K.judge(ref, y, di, lag)` on both halves.
  Three shards behind `LO._wait_cap()`; `render` and `replay` are in `LO.RENDERS`, `sep` in `LO.SEPARATIONS` (a render
  waits while a separation runs). A part with no lag is skipped, as in C3r.
- **Scores:** `PF/ladder/judge/<row>/<set>/<unit>|<amp>.json` with the answers' and the render's sha256.

## 6. Stages, costs and stops

Measured rates: C3r's read made 1,920 answers (3,840 renders, each answer with its priming render) in about 55 min on 3
shards, so about 2,100 answers an hour. X-LANCE took 4.7 s a 10-s clip on the MPS (A2s: 386 in 30 min). The dry run
of the lender draw took 31 s, and a unit's two mixes 0.4–0.7 s.

| Stage | Runs | Separations | Answers rendered (renders) | Machine time |
|---|---|---|---|---|
| 0 | the controls; the lenders; Cen and Aconst; `clean-kind`'s and `xl-v0`'s answers; the preview; the knob reads | 0 | 0 | minutes of CPU |
| 1 | the controls (60 renders); Cen, Aconst, `clean-kind`, `mix@-3` on all 480 parts | 0 | 2,880 (5,760) | about 82 min of renders |
| 2 | `xlnoG@-3`, `xl@-3` on all units; `clean@-3` and `xl-v0` beside | 800 | 1,920 (+1,884) | about 63 min MPS, then 55 (+54) min of renders |
| 3 | the subset: `xlmdxc@-3`; `mix`, `xlnoG`, `xl` at drawn and 0 dB; the conditional rows | 600 + 148 stereo | about 3,200 (+ up to 1,400) | about 47 + 35 min separating, about 90 (+40) min of renders |

- **Stage 0, zero renders.** Its controls first; a failure stops it. Then the lenders, the constants, `clean-kind`'s
  and `xl-v0`'s answers, and the read: the planner's preview reproduced (R-all on its stored input against S, and against
  5C's stored core centres RcBG, RcGk on GOAT and RcBG, Rcs2 on BKS, by set), split by each unit's guitar-to-backing
  ratio at −12 and −6 dB, twice (the lender's drawn ratio, and the stored input's own, below), with a slope on cluster
  means; the knob-space reads (per row and group: within-cell r with the labels, the answers' spread against the
  labels', the share of knob values where the answer is farther from the label than the cell's mean label of other
  clusters; how far an answer moves between inputs against how far answers differ between units); the lenders' counts;
  R1's seven windows' stem-to-mix levels beside. It decides nothing by itself (knob error understates sound, F11).
- **Stage 1.** Its controls first; a failure stops it. Then Q1. **Stop and report**; the outcome table sets stage 2's
  size.
- **Stage 2.** Full, or under Q1's "neither" only `xl@-3` on the subset. Reads Q2 and Q3. **Stop and report.**
- **Stage 3** runs a row only for a reason found: `xlmdxc` and `xl-real` if stage 2 shows a cost for the other guitars;
  the exposure rows if a −3 dB row beats Cen or differs from `mix-drawn`; `pool` if stage 1 or 2 shows a reading.
  **Stop: the step ends.**
- One build and one read a stage. A change after a read is a dated amendment here before the next stage, reviewed
  first. Renders used are reported, not capped.

## 7. Statistics

- **Unit of analysis:** C3r's clusters with `P.clustered` (BKS by DI file, GOAT by item, cap1 and n12 by creator, the
  panel by DI file), C3r's apart rule (a new set's direction on a DI file among W's plugin rows read apart).
- **The deciding pool:** `C3R.pooled` over BKS, GOAT and the panel, weighted equally (`deciding_sets`), as C3r. cap1
  shares GOAT's DI files, so it is read beside, with one row over every set clustered by DI file.
- **Beside every row:** per set, clean and crunch, cluster- and part-weighted means, clusters agreeing in sign, half A
  alone, without the heavier bands' lenders (lender rows), cap1 and n12 by whether their DI's player trains in the
  fold, and the share of the Cen-to-label gap.
- **Power, from C3r's stored rows:** a paired row resolves about ±0.02 on GOAT, ±0.04 to ±0.08 on BKS, ±0.05 to ±0.15
  on the panel, ±0.02 to ±0.055 on the pool. The label sits about 0.4 to 0.5 beyond R-all. Under about 0.05 a score
  difference isn't known to be heard (F65).
- An interval reaching zero is "undecided", never "no effect". Only section 1's primaries count as decided; every other
  row is descriptive.

## 8. Controls and the independent audit

**Stage 0 (`check0`, a failure stops it):**
- The ladder's answer code reproduces `c3r/answers/all.json` from the stored variant-0 inputs (equal sha256).
- The fold bans re-derived from the run records: per fold, the split's training units, held units, records and showings
  equal the run records' own; no read part's unit trains in its model or shares an identity with a training unit.
- The ladder's pairing reproduces C3r's report rows (R-all − S per set) from the stored judge files.
- `centres` refuses a constant that would use a record of the part's fold or sharing an identity with a fold-k unit.

**Stage 1 (`check1`, `replay`; a failure stops it):**
- The stereo assembly, given S0's own layout, gains, target and draws, reproduces 10 stored S0 centred items (L, R,
  target and others to 1e-5), none of an NS or BKS band.
- The unit's amp track, levelled and mixed as D_fix's recipe, reproduces 10 stored variant-0 features exactly
  (`amp_di_compare_s.rebuild_v0`).
- 30 stored R-all answers re-rendered give C3r's stored `render_sha256` (60 renders). Otherwise old and new renders
  can't be compared, and `mix-drawn` is re-rendered under its own row first.
- A unit with a silent stem half stays in, as the product would read it, and is counted.

**Stage 2:** `sep` rebuilds each mix and records whether its mid's sha256 equals the build's.

**The audit:** an independent agent with its own script, importing none of the ladder's statistics, recomputes every
primary row from the judge files, per set and pooled, to 1e-4. It rebuilds Cen for 20 parts from the raw label files,
re-derives the fold bans from the run records, and checks every answer's input features against the row's recipe on a
seeded sample. It tries to break each decided row: one cluster left out, clean and crunch apart, cap1 by whether its
DI's player trains in the fold. Results are written up only after it.

## 9. Code and the commands

`learn/preset_ladder.py`; its pure parts (the rows, the lender pool and draw, the layout, the gains, the stereo
assembly and mastering, the centres, the subset, the read helpers) are in `tests/test_preset_ladder.py`. Interpreters:
`.venv` for renders and audio, `$TORCH_PY` (`~/ndsp-presets/tools/demucs-venv/bin/python`) for answers, the msst-venv
for separations.

**Stage 0** (zero renders):

    .venv/bin/python -m learn.preset_ladder lends
    $TORCH_PY -m learn.preset_ladder check0
    $TORCH_PY -m learn.preset_ladder centres
    .venv/bin/python -m learn.preset_ladder build --rows clean-kind
    $TORCH_PY -m learn.preset_ladder predict --rows clean-kind,xl-v0
    .venv/bin/python -m learn.preset_ladder subset
    .venv/bin/python -m learn.preset_ladder stage0

**Stage 1:**

    .venv/bin/python -m learn.preset_ladder check1
    .venv/bin/python -m learn.preset_ladder build --rows mix@-3          # mix@-3, full@-3 and clean@-3 (zero renders)
    $TORCH_PY -m learn.preset_ladder predict --rows mix@-3
    .venv/bin/python -m learn.preset_ladder replay                       # 60 renders
    .venv/bin/python -u -m learn.preset_ladder render --rows cen,aconst,clean-kind,mix@-3 --shard k/3   # k = 0, 1, 2
    .venv/bin/python -m learn.preset_ladder report --stage 1

**Stage 2** (declared before it runs):

    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.preset_ladder sep --rows xlnoG@-3,xl@-3 --device mps
    $TORCH_PY -m learn.preset_ladder predict --rows xlnoG@-3,xl@-3,clean@-3
    .venv/bin/python -u -m learn.preset_ladder render --rows xlnoG@-3,xl@-3,clean@-3,xl-v0 --shard k/3
    .venv/bin/python -m learn.preset_ladder report --stage 2

Long jobs run detached (`zsh -c 'setopt no_bg_nice; nohup caffeinate -i …'`), their PIDs recorded at launch, each
launcher ending its log with one done line; launchers and logs live under `PF/ladder/logs/`, never in git.

## 10. Documents

This plan; the ledger's `preset-ladder` entry, each phase declared before its stage and an `_outcome` after; after the
audit, `docs/preset-ladder-results.md` and `docs/preset-ladder.json`; a line in `docs/DOCS-INDEX.md` and a dated line
in `docs/ROADMAP.md`'s step 0.

## 11. Standing rules, as applied

- **Trusted data only:** C3r's scoped units and D_CC's reviewed sessions; no V-real, reserve, NS or R1 audio (R1 enters
  as seven stem-to-mix levels read from its window records, no titles, paths or audio). **No songs in git:** library
  unit ids only.
- **Verify in isolation:** the amp and class are told; each row changes one thing against its neighbour.
- **Lean:** zero renders, then 2,880 answers, before any separation. **Undecided is not failed; no bars:** section 7.
- **Machine:** at most 3 render processes, each render primed in its own process; one MPS job at a time (checked free
  first); separations before renders; features stored, never audio; the 31 GB guard checked before each build and
  render.

## 12. Risks, and what the read can't say

- **Built mixes, not songs.** The target is foreign to its session, the other guitars are plugin renders, the layout is
  one centred case, and −3 dB is declared. R1's windows beside show how far off this is; they don't fix it.
- **By the score only.** The labels are the judge's optimum with the EQ on its rails (G5), so the ceiling is the
  judge's. A constant built from them may please the judge more than the ear. Nothing here should ship without a blind
  listening page; the results say where one is called for.
- **Not covered:** the amp pick, the loudness step, the window selector, a wrong class, the effects. Step 1 reads those
  end to end.
- **Thin independence.** BKS is one band and two songs; most GOAT DIs are one player's; cap1 reuses GOAT's DIs; captures
  aren't amps in a room; the panel is 5 DI files.
- **The lenders lean on Forkupines for crunch** (173 of 197 crunch units by the dry run): crunch's other guitars are
  mostly one session's dense four-guitar sections. Read per lender band beside.
- **`clean-kind` is outside training.** R-all never saw a guitar alone, so a failure there is read with `mix@-3`, not
  alone.
- **The backings are known to the model** (D_CC's sections are W's training backings), as in every C3r read; the other
  guitars' DIs are W's plugin targets. `xl-real` checks it only if a cost shows.
- **Aconst is in-sample** (section 4).
- **`xlst_mdxc`** is read only where it works, a centred part; off centre it needs a side hint, which is a person.

## 13. Decisions taken while the user sleeps (the orchestrator's defaults, 2026-11-16)

1. Stages 0 and 1 run before Step 1, so the exam's "centre" arm is the tested one.
2. −3 dB is the main exposure, with drawn and 0 dB on the subset (R1's windows suggest the truth lies between).
3. The lender sessions are D_CC's (the two heavier bands' non-high-gain sections kept); each primary row is reported
   once more without those two bands' lenders, beside.
4. A blind listening page before anything ships is outside this step; the results note where one is called for.
5. V-real, the reserve, NS and R1's audio are not touched; this step uses no sealed set.

## 14. Changes from the planner's draft (checked against the source before anything ran)

The planner's draft is `~/ndsp-presets/handover/2026-11-16/plan-step2.md`; its numbers marked "mine" were unaudited.
- **NS is out of the lender pool.** The draft's 7 bands with other guitars included Adam Buckley's and The Maybe Next
  Years' NS songs, which this step must not touch. The pool is W's own recipe split (no NS, runaway or doubled example).
- **Lenders by section, not by band.** With NS out, crunch has four bands: Forkupines (51 sections), The Travelling Band
  (3) and the two heavier bands (6 between them). A band-first draw would have the heavier bands lend half of crunch's
  mixes, against "a small minority" and "as D_CC has them". A section-first draw keeps them at 16 of 197 crunch units,
  at the cost of Forkupines lending 173 (section 12).
- **Never the unit's own session:** n12's units sit on The Travelling Band's and Ale Lak's DIs.
- **"Other guitars" includes the session's other-guitar amp tracks** (some lenders have only those, e.g. Dunning
  Kruger's), and silence is measured on both together (22 candidates out), not on the `others` render alone.
- **The stored input is less buried than the draft says.** Its −9 dB median (−12 to −6) is the lender's drawn ratio,
  which counted the lender's other guitars in the backing; variant 0 has none. The stored input's own target-to-backing
  ratio is a median −6.6 dB (quartiles −9.7 and −3.4; 398 of 400 units). Stage 0 splits by both.
- **The exposure is set on the mid** the model and the default separator read, not in the mono recipe, and noG keeps
  full's gains, so `mix@-3`'s target sits above the bare backing (−1.7 to +2.2 dB in the dry run).
- **R1's windows:** today's model-path window records give a stem-to-mix median of −3.8 dB (range −5.7 to −1.6; 5 of 7
  on the user's centre version), not −2.5 (−7.9 to −1.3). Stage 0 records them.
- **Cen is the labels' centre, weighted by showings**, not "the best constant under the model's own loss"; Aconst is on
  in-sample inputs (section 4).
- **Stage 0 also makes `clean-kind`'s and `xl-v0`'s answers** (zero renders) so its knob reads cover them. `xl-v0`
  covers 462 parts (A2s skipped 2 BKS units and holds no n12).
- **Counts corrected:** GOAT's classes are 110 and 105; stage 1 is 2,880 answers, 5,760 renders, plus the replay's 60.
