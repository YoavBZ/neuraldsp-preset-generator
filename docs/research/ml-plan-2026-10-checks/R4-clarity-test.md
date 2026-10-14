# R4: clarity test of ml-plan-2026-10.md

## 1. Confusing or contradictory

- **"band"** means a recording group, but "EQ bands" also appears. Never defined.
- **Used before defined:** C, C′, S, M, K_S/K_M, "the 33", K3, "bank clips", `flat`/v3, "amp track", "held-apart DIs", "the stem's agreement".
- **Pass rule** "on the unfiltered set when step 4 provides it": K_S exists only on the 24 parts, and no renders are budgeted to run the arms on step 4's 65.
- **"uncut"** (arm A) reads as "whole clip", against "reads only the search half".
- **Step 6 "fails twice"** vs "re-run at most twice" (3 attempts).
- **Arm C's 150 run:** "only if 50 passes" (step 3) vs "if arm C leads" (§6).
- **Arm A's control:** "Stop" what? Is "within 0.03" a distance or a fraction?
- **Step 1, "around 03:00–04:15":** §5 bans that window.
- **Gain floor:** step 2 goes to −24 dB; step 3 keeps knob ceiling's −20.
- **Numbers:**
  - "B leads +48–103k": I get 48–75k.
  - "Every path passes 200k" fails if A leads or no arm passes.
  - Step 5's 19k doesn't reproduce (12 × 450 × 5 = 27k).
  - Step 1 needs 66 GB free, but §5 implies about 65 GB in total.
- **Order:** step 1's check needs step 3's C′-menu renders.

## 2. Writing each step's plan

- **Step 0:** no. Where does the separation script live? What is the ledger schema?
- **Step 1:** mostly. I'd guess the two-stage schedule, the numeric "known range", and what to do if the PR12 cache is gone.
- **Step 2:** no. Unstated: cells, budget per cell, pedal and effect dimensions, Tone King's parts, starts and renderer (`Renderer` is Morgan-only), the listening protocol, and a pass rule.
- **Step 3:** largely. I'd guess:
  - 10-s clips and pre-roll (`render_job` uses 8-s windows);
  - where the backings come from;
  - arm B's sample rate;
  - what "pilot passes" means;
  - whether the positive-control target is the clean render (d_target ≈ 0) or the stem;
  - arm C under decision 1(b).
- **Step 4:** yes.
- **Step 5:** no. Which 12 cells? How are mics handled? In-repo CMA-ES or pycma (`pyproject.toml` excludes `cma`)?

## 3. Code pointers

All exist. Gaps:

- `direc.rebuild` doesn't set the level; it needs `to_lufs`.
- `confirm_run.build_di("measfix")` needs a crop folder and torch, so pool DIs need an array version.
- `run_cell` hard-wires the true-DI judge, so arms A and C need a new objective.
- The CMA-ES in `match/search.py` is `refine()`. It is continuous-only and tied to that module's `Evaluator`.
- The unnamed `learn/evaluate.py` has `shuffled_sources`.

## 4. Jargon

Mixture-density head, top-1, "censored", cross-half, band-weighted, "dry class start", "the menu", "fallback fires".

## 5. Ten wording fixes

1. "24 parts × 3 amps in 14 bands" → "24 parts × 3 amps from 14 bands (a band is one artist's recordings, the unit for folds and statistics)."
2. `Search from today's start S, vs S ("K_S")` → Add above the table: "S is today's class start. M is the menu preset closest on the search half. K_S and K_M are searches from S and M."
3. "Set 5's C′-over-C is now fragile." → "On set 5, the corrected DI network C′ beat the old one, C. That result is now fragile."
4. "`rebuild`, uncut, at −22.9 LUFS" → "`rebuild` on the search half, with no 3-kHz low-pass, then `to_lufs` to −22.9 LUFS."
5. "plan each ~5-h fold around 03:00–04:15." → "Schedule each ~5-h fold so it doesn't run 03:00–04:15."
6. "on the unfiltered set when step 4 provides it:" → "on step 3's cells. State separately how step 4's parts are scored, and the render cost."
7. "Arm B's positive control fails twice" → "Arm B's positive control still fails after two re-runs."
8. "The search setup is wrong. Stop" → "The search setup is wrong. Stop arms A and C (step 6, row 2)."
9. "A separate `budget=150` run only if 50 passes" → "A separate `budget=150` run, after the readout, only if arm C leads (section 6)."
10. "Every passing path after the readout goes past 200k" → "If arm B or C leads, the work after the readout goes past 200k."
