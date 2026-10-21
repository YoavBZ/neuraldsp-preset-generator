# Amendment 6 (2026-10-22): a sound-based stop/go gate for step 3

*To be folded into [the direct-model plan](direct-model-stems-plan.md) in one docs pass.*

**Status:** declared 2026-10-22, before any non-smoke render, step 3 run or step 3 readout. The user
approved a sound-based gate in chat with the ML session on 2026-10-22. It changes step 3's stop/go
only. Training, the readouts and step 4 are unchanged.

- **Code:** `learn/direct_sound_gate.py`, tests `tests/test_direct_sound_gate.py`.
- **Ledger:** `direct-model-sound-gate` in [`dev-test-ledger.json`](dev-test-ledger.json).
- **Outputs:** `~/ndsp-presets/learn/direct-stems/gate/`.

## Why

- **Knob error is the wrong judge.** The ML plan says not to judge a settings model by knob error,
  because many settings sound alike ([ML plan §7](research/ml-plan-2026-10.md)).
- **Step 3's early stop reads E,** a knob error. Even read as amendment 5 reads it, E can stop a
  model whose answers sound right, or pass one whose answers sound wrong.
- **The gate asks the question that matters:** on examples with a known answer, does D's preset
  sound closer to the true preset than the constant's does?

## The gate (declared)

**The set: R_in.** It is V_sep's examples with their mix and xlance_g stem built and unrefused.
Bannockburn, and every MUSDB18-tagged section, is left out, as step 3's `readout` does.
- 1,407 examples in 4 bands: Dark Ride 407, Adam Buckley 405, John Morgan Kimock 376, Swatkins 219.
- 45 sections and 135 (section, amp) groups.

**What is rendered, per example.** Each example renders through its own DI section: part C's
measured 10-s section plus 0.25 s, the guitar alone, with no separation and no backing. Every preset
uses the same amp and the same select. All are S with the labelled dimensions replaced
(`direct_stems.settings_from`, as step 4 and `direct_existing` do). Everything outside the labelled
space is S's.
- **The truth:** part C's label settings, rebuilt by `pretrain_set.settings_for` and checked against
  the stored row. Its render must reproduce part C's stored guitar mels within one 0.5-dB step on 99%
  of cells, or the example is refused for every arm and counted. A test checks that assembling the
  label as an answer gives exactly the truth's settings.
- **The constant:** per amp and base class.
  - Continuous knobs: amendment 5's medians of D's training labels (the pool's train examples less
    the build's refusals), over the labels that leave the knob audible.
  - Switches: the training labels' majority. A switch is on if more than half the labels set it on.
  - Mics: the most frequent value over the audible labels (the lowest index on a tie).
  - The continuous constant must equal the one step 3's `readout.json` stores, within 1e-9, or
    the report reads INCOMPLETE.
- **D:** amendment 5's declared answer on R_in. That is A1 mixture medians averaged over 3 seeds ×
  2 halves, then pulled toward the constant by step 3's fitted b for the amp and class.
  - Switches and mics come from `direct_existing.ensemble` over the 6 seed × half outputs. A
    switch needs a strict majority of the 6 votes, so a 3–3 tie reads off. Mics take the argmax of
    the summed probabilities.
  - D's inputs are R_in's: the true mix and the xlance_g stem, zeroed as the arm was trained.
- **D0 (descriptive):** read the same way, with its own b. Rendered in the same pass as D. Its
  1,407 renders keep the total under 6k.

**The score.**
- **The judge:** d_X is `knob_ceiling.judge` (the project's judge: `aligned_distance` with its
  defaults, judge v1, as arm A and knob_ceiling use it) of X's render against the truth's render.
  - The truth's render plays the recording; the lag is 0, since both are renders of one DI.
  - Render latency is 52. Renders are mono (the channel mean) and trimmed by 0.25 s, and the DI is
    trimmed alike.
  - The judge reads halves A (1.0–5.5 s) and B (5.5–10.0 s), the model's own halves. The first
    second is out, past the isolate fade.
- **Per example:** the mean over its scorable halves of log(d_D / d_const), each half clipped to
  [−ln 10, +ln 10].
  - The clip bounds an answer near the truth: an identical preset re-renders at d ≈ 1e-5, so its
    ratio is unbounded.
  - A half refused for one arm only (a silent render) counts as the worst for that arm. A half
    refused for both is dropped. Clipped and dropped halves are counted.
- **The rule:** the contrast is band-weighted. **GATE OK** if its paired, band-clustered 90% t
  interval (4 bands, 3 df, t 2.353, as the pilot) lies entirely below 0. Otherwise **GATE STOP**:
  D's answers are not shown to sound closer to the truth than the constant's. Stop and revisit with
  the user, as step 3's early stop did.
- **GATE INCOMPLETE** in any of these cases:
  - an R_in example lacks a truth, constant or D row;
  - D's answers were not read under amendment 5, or come from other models than `readout.json`;
  - `readout.json` changed after `gate-predict`;
  - the constant differs from the stored one, or `readout.json` stores no constant;
  - the gate's R_in differs from the examples `gate-predict` answered, or from the count step 3's
    readout read (`gate-predict` refuses on the latter too).

**What no longer decides.** E is descriptive: amendment 5, as the user approved it on 2026-10-22,
reports it as the "E check". The gate is step 3's stop/go, and step 4's renders run only after
GATE OK.
- **The wiring:** amendment 5's `direct_stems.step3_gate` fails closed until it returns
  `direct_sound_gate.step3_verdict(root)`. That verdict is true only for a real GATE OK whose
  `full/readout.json` is unchanged since the gate read it.
- **Still to do:** the one-line change sits in amendment 5's file and is left to the merge of the
  two branches.

**Reported beside the gate, never deciding:**
- D0 − constant and D − D0 on the same scale;
- per class (clean, crunch) and per amp;
- per band;
- the share of examples where D's render is closer;
- E (masked, amendment 5) of D − constant and D0 − constant on the same examples.

## Renders, staging and machine

**Renders:** 5,898 in all.
- **Truth and constant:** 2,949 = 1,407 × 2 + 135 priming.
- **D and D0:** 2,949, in one pass.
- **Without D0:** 4,491.

At about 1.6 s each, the judge included (smoke), each pass takes about 27 min on 3 processes, or
80 min on one.

**Rendering rules:**
- `isolate=True` on the bounded server.
- One discarded priming render after a process start or a (DI section, amp) change.
- Whole sections per shard (`shard_sections`, 469 examples a shard), in (section, amp) order.
- At most 3 render processes machine-wide: `local_objective.RENDERS` now counts
  `direct_sound_gate gate-render`.
- Disk guard 31 GB, plus the memory and swap guards (swap measured from each process's start).
- Each process waits for a render slot and for free memory (4 GB floor + 1.5 GB) **before** it
  loads part C's rows (about 1.4 GB). Start the shards about 60 s apart.

**Resumable.** Rows go to `gate/rows/<arm>-<k>of3.jsonl`, one per (example, arm). A rerun skips
what is done, and one process holds each shard (a lock).

**Kept audio:**
- **Every truth render,** as 24-bit FLAC with a power-of-two scale, so it never clips, and a
  hash. Every arm is judged against it. About 0.7 MB each, about 1 GB in all.
- **The other arms' renders** only for a fixed audit sample of 40 examples
  (`random.Random(20261087)`), about 0.1 GB.

**Order.** The truth and constant renders run before D exists; the constant needs the complete build.
```
MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
# after the xlance_g build completes (during step 3's training); shards started 60 s apart
for k in 0 1 2; do
  OMP_NUM_THREADS=1 $MAIN -m learn.direct_sound_gate gate-render --what truth,constant --shard $k/3 &
  sleep 60
done; wait
# after step 3's `readout` (amendment 5's pull): zero renders, CPU, about 10 min
$TORCH_PY -m learn.direct_sound_gate gate-predict
for k in 0 1 2; do
  OMP_NUM_THREADS=1 $MAIN -m learn.direct_sound_gate gate-render --what D,D0 --shard $k/3 &
  sleep 60
done; wait
$MAIN -m learn.direct_sound_gate gate-report      # GATE OK | GATE STOP | GATE INCOMPLETE
```

## Smoke (2026-10-22, scratch directories, 33 renders in 3 runs, one process beside the two X-LANCE workers)

- **Truth and constant on 3 R_in examples:**
  - every truth render reproduced part C's mels (share 1.0);
  - the constant's d was 3.75–5.98.
- **A positive control:** `gate-predict --label-answers` (smoke only) hands each label to D and D0
  as its answer.
  - The assembled presets equalled the truth's settings exactly.
  - They re-rendered at d ≈ 2e-6 to 2e-5.
  - Every half clipped at −ln 10, and the smoke report read GATE OK.
- **Peak memory:** 1.5 GB per render process (part C's rows, freed after the set is built).

## Caveats, stated before any reading

- **Power is unknown:** there are only 4 bands. A tie reads GATE STOP ("not shown at this power").
- **The renders say nothing about songs.** They test whether the answer's sound is right on
  realistic separated inputs, not on real songs, so step 4 stays the decision.
- **One judge.** The truth plays a recording. The gate measures closeness by the project's judge,
  not by ear.
- **D's and the constant's switches and mics differ too.** The contrast is between whole answers,
  not just the continuous knobs.
- **The pull's weights come from the in-band early-stopping set** (amendment 5). R_in plays no
  part in any fit, so the gate stays out of sample.

## Declared choices (this amendment's, not amendment 5's)

- **The constant's switches and mics.** Amendment 5 defines only the continuous constant. This
  gate's constant sets each switch by the training labels' majority (on if more than half set it on)
  and each mic by the audible labels' mode (the lowest index on a tie).
- **The clip.** Each half's log(d_D / d_const) is clipped to [−ln 10, +ln 10] before the halves are
  averaged. This is declared before any reading, and the clipped halves are counted in the report.
