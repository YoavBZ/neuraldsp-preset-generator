# The LOUDAR prior timing probe: results (`phase_scratch_prior_probe_outcome`)

Run 2026-11-28 from main at b51dd483 ([plan](prior-probe-plan.md), ledger `preset-ladder` `phase_scratch_prior_probe`).
Zero renders. No model was kept. Checked by the orchestrator under the lean-review rule (a zero-render timing probe:
the orchestrator's own check, no separate audit).

## The code: PP-mps

- Every check held on LOUDAR's own path: the m2l encoder on MPS and torch's native `clip_grad_norm_`.
- No declared fallback was needed, nothing read cpu-only, and nothing was anomalous.
- No step was non-finite: not the five check steps on MPS, not the 200 long timed steps, not the 100 short ones.
- The file rule held: no data read outside the list, no write outside the probe's folder, no weights file. The
  folder holds only JSON and the 16 segments (32 MB).

## The rate (one run, idle)

One `time` run, `time-20261128-190641.json`. Both timed blocks were idle at their start and end: 0 render processes
and 0 other torch processes. Batch 2; the rate is from steps 21 to 200 of 200 (long) and 21 to 100 of 100 (short).

| | 526,080 samples (the quoted rate) | 218,624 samples (beside) |
|---|---|---|
| Steps per second | **0.763** | 1.644 |
| Seconds a step, mean (median) | 1.311 (1.310) | 0.608 (0.607) |
| Warm-up mean, steps 1-20 | 1.328 s | 0.713 s |
| Per 1,000 steps | 1,311 s (0.364 h) | 608 s (0.169 h) |
| 175,000 steps (the released checkpoint's count) | **63.7 h** | 29.6 h |
| Audio per 1,000 steps | 6.09 h | 2.53 h |

- **The split.** Separate encode-only blocks (45 timed encodes after 5 warm-up, both idle) give:
  - at 526,080 samples, encode 1.120 s and network 0.191 s a step;
  - at 218,624 samples, encode 0.419 s and network 0.189 s.
- **The encoder is about 85% of a long step.**
- **Cached latents (arithmetic, not measured).** If the fine-tune encoded each segment once and trained on stored
  latents, the network alone would run at about 1 / 0.191 = 5.2 steps per second: about 191 s per 1,000 steps and
  about 9.3 h for 175,000. No such run was made.
- **The CPU rate** is 0.220 steps per second, from steps 2 to 5 of the check's five CPU steps at 4 threads. That is
  4,554 s (1.27 h) per 1,000 steps and 221 h for 175,000.
- **The resample.** The rate excludes LOUDAR's in-step resample (`get_batch`'s `resample_batch`, which GOAT's 44.1-kHz
  files take in LOUDAR's own training). That is right for 48 kHz data.
- **The EMA branch.** Timed steps start at it = 0, as `training_loop` does, so all ran on the EMA's ramp-up branch.

## Memory (the Mac's `hw.memsize` 34.4 GB)

| Run | Peak RSS | MPS driver, peak | MPS allocated, peak |
|---|---|---|---|
| `time`, 526,080 samples | 2.11 GB | 3.94 GB | 1.76 GB |
| `time`, 218,624 samples | (same process) | 5.33 GB | — |
| `check` | 11.7 GB | 6.19 GB | — |

`check` peaks higher because it holds the CPU, MPS and float64 copies of the network at once.

## The gradient check

Every figure passed its tolerance directly. None needed the float64 calibration.

| Check | Result | Tolerance |
|---|---|---|
| Encoder latents, [2, 64, 128] | 1.4e-6 relative L2 | 1e-3 |
| Run 1, the network on shared CPU latents: loss | 6.3e-8 | 1e-4 |
| Run 1: gradients before the clip, 137 tensors | global 1.83e-6; worst 7.1e-6 (`layers.3.pre_norm.gamma`) | 1e-3 |
| Run 1: the clip | norm 0.97847 against 0.97844 (3.1e-5); 0 non-finite; gradients after it as before it | 1e-3 |
| Run 2, end to end on the MPS run's own latents: loss | 0.0 | 1e-4 |
| Run 2: gradients | global 1.83e-6; worst 8.3e-6 (`layers.1.pre_norm.gamma`) | 1e-3 |
| Run 2: the clip | as run 1 | 1e-3 |
| AdamW, from identical gradients | global 1.0e-6; worst 2.6e-5 | 1e-3 |
| EMA at it 1 and at it 175,000 | 0.0 (exact) | 1e-3 |
| Five steps, MPS against CPU | losses equal to about 2e-7; weight change 7.4e-5 relative | reported |

- **The float64 reference held.** The CPU loss was 2.7e-8 off it and the CPU's global gradient 2.2e-6 off it. The
  draws were the same on both devices. The rotary buffer stayed float32, as declared.
- **One calibration was refused.** At EMA it 175,000 the CPU's own float32 error on those tiny deltas is above the
  tolerance, so calibration was refused there, as the gate requires. The direct check passed.
- **The five steps' losses** (MPS; CPU equal to about 2e-7): 0.716, 0.512, 0.419, 0.718, 0.705. Clip norms: 2.04,
  1.33, 0.82, 1.02, 1.02.

## Limits

- **The clip's scaling path was not compared per tensor.**
  - The check batch's gradient norm was 0.978, below max_norm 1, so the clip did not scale on the batch whose
    gradients were compared tensor by tensor.
  - It did scale in four of the five steps (norms 2.04, 1.33, 1.02, 1.02). There MPS and CPU agreed: the losses to
    about 2e-7 and the weight change to 7.4e-5.
  - It scaled in 168 of the 200 long timed steps (norms up to 8.17) and in all 100 short ones, and every step was
    finite.
- **The idle count and its launcher (a follow-up).**
  - The first `check` launch, at 19:03:41, refused itself as "another torch or MPS process" and wrote nothing.
  - Two wrappers matched the venv pattern and were not left out as the probe's own: the launching shell, whose
    command line named the venv path, and `caffeinate -i <command>`, which runs as a separate process outside the
    probe's parent chain. After nohup the probe's parent is pid 1.
  - The run went through a launcher that starts the probe with nohup and keeps the Mac awake with
    `caffeinate -i -w <pid>`, so no wrapper's command line names the venv. Both real runs then counted 0 and 0 at
    every block's start and end.
  - The idle count should leave out caffeinate wrappers and the launching shell, or the plan should name this
    launcher.
- **One run.** The rates are one run's; no repeat was timed.
- **A probe only.** 200 steps say nothing about whether a fine-tune helps. The optimizer started fresh. GOAT is the
  prior's own training data, which lowers the losses but changes neither the timing nor the MPS-against-CPU gradients.

## The hours (a count only; the fine-tune declares its own set)

**The clean-DI library: 0.889 h** (320 trusted sections).

| Source / set | Sections | Hours |
|---|---|---|
| telefunken / 2 | 206 | 0.572 |
| cambridge / 3 | 50 | 0.139 |
| cambridge / 2 | 42 | 0.117 |
| cambridge / undeclared | 13 | 0.036 |
| telefunken / 3 | 9 | 0.025 |

Excluded, each section under its first reason:

| Reason | Sections | Hours |
|---|---|---|
| Fails the library's own screens | 4,842 | 13.450 |
| Silent Waves, Drowning | 0 | 0 |
| Held bands (V-real 0.653 h, NS 0.036 h) | 248 | 0.689 |
| `clean_di.refuse_held_out` | 0 | 0 |
| The reserve's stage-F DIs | 49 | 0.136 |
| The DIs the user marked too low or metal-style | 108 | 0.300 |
| The hum superset | 4 | 0.011 |
| The fs draw's sections | 0 | 0 |

The user's marks name 17 DI files; 14 are in the library. The other 3 are the panel's, which is held anyway.

**Unscreened here:**
- EGDB: 1.791 h over 240 files. It is LOUDAR's test set, so it is a fresh source for the prior.
- EGFxSet: 0.958 h of clean single notes over 690 files.

**GOAT, apart: 4.262 h** over 117 items. This is the prior's own training data, and it was never checked for scope.

| Excluded | Items | Hours |
|---|---|---|
| item_5 (ruled out) | 1 | 0.008 |
| The fs draw's items | 24 | 1.041 |
| No screened 5C window | 24 | 0.333 |
| Near full scale | 6 | 0.314 |

By tuning, the counted GOAT hours are standard 3.578, downtuned 0.468, drop D 0.077 and other tunings 0.138. The user's
"too low" rule was never applied to GOAT.

## Terms

- LOUDAR's code: MIT.
- Its checkpoint `GuitarFx-175000.pt` (sha256 d86e08bbb94b…, as pinned) is tagged MIT and trained on GOAT (CC BY-NC,
  granted on request).
- The m2l autoencoder is linear-cae 0.1.4's (Apache-2.0).
- Research use only; nothing ships. No model, optimizer state or weights file was kept or written.

## The outputs (PF only)

| File | sha256 |
|---|---|
| `hours.json` | 4846f715e2a544d8d84d55e13f158cee343f9d69b55528485c327505e5872525 |
| `prep.json` | 6852ca67c596a537092114c3546719bc2b4a86b3c8a70ebe8fac3f2433229f5a |
| `check.json` | 8ea6a6baa494035ed2fe5cbb984b9441f29473eea5b31df47fd75908744db88e |
| `time-20261128-190641.json` | dac78f81a3190c8e26e80c10b6d20d04eb1655a7a4665a0ca7b66c96c6aaec91 |
| `outcome.json` | 32571d40b6df180244a9be1cdfe5d377fc9f54d39a861d41f7b4950022bb9288 |

The 16 segments (`segments/seg-00.npy` to `seg-15.npy`) are hashed in `prep.json`.

## What ran

| Step | Where | Time (2026-11-28) |
|---|---|---|
| `hours` | main `.venv` | about 19:03 |
| `prep` | main `.venv` | about 19:03 |
| `check` | the loudar venv; CPU at 4 threads and MPS | 19:04:43 to 19:06:09 |
| `time --steps 200` | the loudar venv; MPS | 19:06:39 to 19:13:49 |
| `read` | main `.venv` | about 19:14 |

Both `check` and `time` ran at nice 0, with no renders running.

## Next

The probe prices route 3's fine-tune; the user picks the route.
