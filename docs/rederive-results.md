# The rebuild's re-derivation: results

Declaration: [rederive-plan.md](rederive-plan.md). Ledger `preset-ladder`: `phase_scratch_rederive`,
`phase_scratch_rederive_ladder`, `phase_scratch_rederive_answers_now`, `phase_scratch_rederive_stage1`,
`phase_scratch_rederive_frozen`, `phase_scratch_rederive_answers_fix` and `phase_scratch_rederive_bench_outcome`. Code:
`learn/scratch_rederive.py` (the core), `learn/rederive_rows.py` (the rows), `learn/rederive_fit.py` (the fit) and
`learn/rederive_diag.py` (the diagnosis).

Every number here is by the score (J0), not heard. Intervals are 90%, from `scratch_notes.set_rows` on BKS+GOAT (the
40); all 47 parts go beside. Labels come only from `paired_reading`.

## Stage 2: `xf-fix`, the frozen rule in the real-song input form (2026-11-26; audit pending): XF-closed

**The bench code is XF-closed: the cost is no longer shown.** The frozen rule (measured domain, iterated, the mute
veto; stop 64; `phase_scratch_rederive_frozen`) re-derives the four values from the same `in-M` input as `xf-now`.
- **The gain** D_fix − D_now = G(`xf-fix`) − G(`xf-now`), paired per part, is **−0.174 [−0.298, −0.049]** on the 40.
  It is wholly below zero, and `paired_reading` reads it better.
- **D_fix** = G(`xf-fix`) − G(`xn-bank`) is **+0.079 [−0.015, +0.173]** and spans zero; `paired_reading` reads it
  undecided. The read rules out a remaining cost above +0.173. It does not show the cost gone: a cost up to that size
  is not ruled out.
- **Next, under the declared table:** the bridge (`fs-refit`) runs, after the audit, on the real songs.
- **The row still beats Cen.** G(`xf-fix`) is −1.132 [−1.327, −0.937] and passes, beside G(`xf-now`) −0.958 and
  G(`xn-bank`) −1.211.

### D_fix and the gain on the declared splits

| Split | D_fix | Gain (D_fix − D_now) |
|---|---|---|
| **The 40 (deciding)** | **+0.079 [−0.015, +0.173]** | **−0.174 [−0.298, −0.049]** |
| Clean 20 | +0.159 [−0.016, +0.334] | −0.292 [−0.526, −0.057] |
| Crunch 20 | −0.000 [−0.088, +0.087] | −0.056 [−0.148, +0.037] |
| All 47 | +0.101 [−0.046, +0.247] | −0.094 [−0.233, +0.044] |
| Panel (7) | +0.144 [−0.311, +0.599] | +0.064 [−0.392, +0.520] |
| Shrunk arm, the 40 | +0.021 [−0.006, +0.048] | −0.044 [−0.107, +0.020] |
| Checkpoint 50, the 40 | +0.014 [−0.020, +0.047] | −0.081 [−0.130, −0.033] |
| Checkpoint 100, the 40 | +0.045 [−0.032, +0.123] | −0.125 [−0.207, −0.043] |
| Checkpoint 200, the 40 | +0.070 [−0.012, +0.151] | −0.163 [−0.279, −0.048] |
| Each cluster of the 40 left out (32 reads) | means +0.038 to +0.099; every interval spans zero | means −0.199 to −0.132; every upper end below zero |
| One part per partner (33 parts over all 47, 30 of them on the 40) | +0.041 [−0.016, +0.099] | −0.138 [−0.263, −0.013] |
| Without the two design-time parts | +0.038 [−0.015, +0.091] | −0.118 [−0.220, −0.017] |
| Passing-only (nothing refused in `xf-now`, `xf-fix` or `xn-bank`) | +0.079 [−0.015, +0.173] | −0.174 [−0.298, −0.049] |
| The 15 tilt parts (seen) | +0.092 [−1.566, +1.751] | −0.385 [−0.604, −0.165] |
| The other 25 (seen) | +0.068 [+0.014, +0.123] | −0.020 [−0.109, +0.070] |
| Contribution to the 40's mean: tilt parts / others (seen) | +0.040 / +0.039 | −0.153 / −0.021 |

- **Robustness.** Every one of the 32 cluster-left-out reads keeps XF-closed. So do the passing-only read, one part
  per partner, and the read without the two design-time parts.
- **Where the gain sits.** It sits in the tilt parts: on those 15 it is −0.385 [−0.604, −0.165], wholly below zero,
  while the other 25 are undecided. On the point estimates it also sits mostly in clean (−0.292 against crunch's
  −0.056, which spans zero; the clean-to-crunch difference was not tested).
- **All 47 does not decide.** On all 47 the gain spans zero (−0.094 [−0.233, +0.044]), and the 7 panel parts are wide
  (+0.064 [−0.392, +0.520]).
- **The shrunk arm goes beside only.** Its stage-1 D_now already spans zero, so it would read XF-input there. Its gain
  spans zero (−0.044 [−0.107, +0.020]); the answer arm decides.
- **The remaining D_fix.** On their own, the 25 non-tilt parts still show a small cost (+0.068 [+0.014, +0.123]); the
  15 tilt parts' own interval is uninformative. By contribution to the 40's mean the remaining D_fix splits about
  evenly (+0.040 and +0.039; seen, descriptive).

### The floors, beside (they gate nothing)

Each figure is ln(d / d_Cen) at the part's target preset, against the record, with the bank guitar as the judge's DI;
lower means the guitar renders closer to the record. They show order and rough size only, never a price.

| Guitar | The 40 | All 47 |
|---|---|---|
| `xf-fix` | −3.618 [−4.290, −2.946] | −3.478 [−4.399, −2.558] |
| `xf-levels` (the levels true, the rest re-derived after) | −1.405 [−1.716, −1.094] | −1.362 [−1.633, −1.091] |
| `xf-tuning` | −1.060 [−1.246, −0.874] | −1.153 [−1.282, −1.023] |
| `xf-mutes` | −0.973 [−1.162, −0.784] | −1.067 [−1.229, −0.905] |
| `xf-tilt` | −0.884 [−1.042, −0.727] | −0.929 [−1.085, −0.773] |
| `xn-list` (stored, the exact-notes test) | −0.646 [−0.830, −0.461] | |

The stored `xn-list` floor repeated exactly on both check parts (render sha256 and both halves' distances). No part's
distance reads zero.

### What ran

Everything ran from frozen detached worktrees of main: the floors, the search and the answers at b3f5b3a6, the score
and the read at cd262a10.

- **The floors:** 462 renders. Six guitars were byte-identical to another of the same part and took its result.
- **The search** (`search --row xf-fix`, three shards, one render process each):
  - 12,377 search renders and 94 start-reference renders, about 1.8 h;
  - no refusal and no rerun;
  - no part carried: no `xf-fix` guitar is byte-identical to X, `xn-list` or `xf-now`.
- **The answers:** 47 of 47, hashed as `phase_scratch_rederive_answers_fix` before any score (#637).
- **The score:** 564 renders, 431 s at most a shard. Every part's scoring control holds (47 of 47), with no rerun.
- **The stage's total:** 13,497 renders. With stage 1's 13,112, the bench used 26,609.
- **The read** (`read --stage 2`, zero renders) first reproduced D_list and build 2 less row (b) from the stored files
  exactly, and saved its rows before its code.

### What it cannot show

- **The bench, not real songs.** The bench rewards recovering build 2's own values. XF-closed says the frozen rule
  recovers enough of them, in the real-song input form, that the search's cost is no longer shown on the bench. It
  says nothing yet about real songs: the bridge (`fs-refit`) asks that, and it still takes every input from the
  true DI.
- **Sharper than real songs.** The bench is sharper than real songs.
- **One bank, one transcriber, one seed.** The score only.

## Stage 1: `xf-now`, today's rule in the real-song input form (2026-11-25; audited 2026-11-25 (independent, PASS WITH FIXES, wording applied))

**Stage 1 goes on: today's rule's cost is shown in the real-song input form.** D_now = G(`xf-now`) − G(`xn-bank`)
is **+0.253 [+0.106, +0.400]** on the 40, wholly above zero. So under the declared table `xf-fix` runs next (stage 2),
after the fit and an independent audit of this read.

- **What the row is.** The rebuild re-derives its four values (tuning, mutes, the sustain tilt and the group levels)
  from the bank guitar after the measure step only (`in-M`, the form real songs hand it). It then searches against
  the exact-notes test's records, as `xn-bank` and `xn-list` did.
- **How it compares with the finished input.** The exact-notes test handed the same rule the finished bank guitar
  and measured D_list at +0.321 [+0.180, +0.462].
  - D_list − D_now, the finished input's share, is **+0.068 [+0.011, +0.126]**, wholly above zero; `paired_reading`
    reads it undecided (mean under +0.10, hi90 +0.126).
  - On the point estimates, about 0.07 of the 0.32 comes from the finished form alone. Most of the cost stays in
    the real-song form (a descriptive ratio, not declared).
- **The row itself still beats Cen.** G(`xf-now`) is −0.958 [−1.140, −0.776] and passes. G(`xn-bank`) is −1.211 and
  G(`xn-list`) −0.890.

### D_now on the declared splits

| Split | D_now | Reading |
|---|---|---|
| **The 40 (deciding)** | **+0.253 [+0.106, +0.400]** | worse |
| Clean 20 | +0.450 [+0.154, +0.747] | |
| Crunch 20 | +0.055 [−0.013, +0.124] | undecided (spans zero) |
| All 47 | +0.195 [+0.097, +0.293] | |
| Panel (7) | +0.080 [+0.059, +0.101] | |
| Shrunk arm, the 40 | +0.065 [−0.010, +0.140] | undecided |
| Checkpoint 50, the 40 | +0.095 [+0.034, +0.156] | undecided |
| Checkpoint 100, the 40 | +0.171 [+0.054, +0.287] | worse |
| Checkpoint 200, the 40 | +0.233 [+0.099, +0.368] | worse |
| Each cluster of the 40 left out (32 reads) | means +0.194 to +0.273; every lower end above zero (lowest +0.079) | |
| One part per partner (33 parts over all 47, 30 of them on the 40) | +0.179 [+0.075, +0.283] | |
| Without the two design-time parts | +0.156 [+0.074, +0.239] | |
| Passing-only | +0.253 [+0.106, +0.400] (nothing refused in either row) | |
| The 15 tilt parts (seen) | +0.477 [−1.547, +2.501] | |
| The other 25 (seen) | +0.088 [+0.017, +0.159] | |
| Contribution to the 40's mean: tilt parts / others (seen) | +0.192 [+0.042, +0.343] / +0.060 [+0.018, +0.103] | |

- **Robustness.** The cost holds when any one cluster is left out, on one part per partner, without the two
  design-time parts, and across checkpoints 50 to 200.
- **Where it sits.** On the point estimates it sits mostly in clean (+0.450 against +0.055). Crunch is undecided: a
  cost up to +0.124 is not ruled out, and the clean-to-crunch difference was not tested.
- **The shrunk arm goes beside only.** Its D_now spans zero, so it would read XF-input there; the answer arm decides.
- **The tilt split moved little.** With the finished input it was +0.220 from the tilt parts and +0.101 from the
  others; in `in-M` it is +0.192 and +0.060. The others' part fell more, so the tilt parts now carry about three
  quarters of it (seen; contributions to the 40's pooled mean, 0.192 of 0.253, descriptive; the 15 parts' own
  interval is uninformative).
- **Two design-time parts.** They are the refused sw50r part and GOAT item_69. The rule picked them from hashed files:
  the one refused `xn-list` part, and the part whose tilt the rebuild missed by the most.

### D_list − D_now beside (the finished input's share)

| Split | D_list − D_now |
|---|---|
| The 40 | +0.068 [+0.011, +0.126] |
| Clean / crunch | +0.043 [−0.053, +0.140] / +0.093 [+0.004, +0.183] |
| All 47 | +0.059 [−0.001, +0.119] |
| Shrunk arm, the 40 | +0.037 [+0.007, +0.066] |
| Checkpoints 50 / 100 / 200, the 40 | −0.009 / +0.019 / +0.055 |
| One part per partner; without the two design-time parts | +0.081 [+0.013, +0.149]; +0.091 [+0.028, +0.154] |
| Passing-only (without the one refused `xn-list` part) | +0.089 [+0.027, +0.151] |

### What ran

Everything ran from frozen detached worktrees of main: the checks, the searches and the answers at f44df45c, the
score and the read at 90edc3bd.

- **The bench checks** reproduce row (c) exactly: score 24 renders, search 26, no mismatch.
- **The search** (`search --row xf-now`, three shards, one render process each):
  - 12,404 search renders and 94 start-reference renders, about 1.9 h, beside the fit's niced CPU jobs;
  - no refusal and no rerun;
  - no part carried: no `xf-now` guitar is byte-identical to X or to `xn-list`.
- **The answers:** 47 of 47, hashed as `phase_scratch_rederive_answers_now` before any score (#631).
- **The score** (three shards): 564 renders, 475 s at most a shard. Every part's scoring control holds (47 of 47),
  and no part needed a scoring rerun.
- **In all: 13,112 renders.**
- **The read** (`read --stage 1`, zero renders) first reproduced D_list and build 2 less row (b) from the stored files
  exactly. It saved its rows before its code. Its go record (`stage1-go.json`, go on) is what `xf-fix`'s search reads.
- **A note on the go record.** `stage1-go.json` names its plan as "section 7", but the outcome table it reads is in
  section 8. The file is written once, so it stays as written.

### What it cannot show

- **The bench, not real songs.** The bench rewards recovering build 2's own values. This read says the cost survives
  in the real-song input form on the bench; it says nothing yet about real songs.
- **The bench is sharper than real songs, and no bridge has run.**
- **One bank, one transcriber, one seed.** The score only.
