# The rebuild's re-derivation: results

Declaration: [rederive-plan.md](rederive-plan.md). Ledger `preset-ladder`: `phase_scratch_rederive`,
`phase_scratch_rederive_ladder`, `phase_scratch_rederive_answers_now` and `phase_scratch_rederive_stage1`. Code:
`learn/scratch_rederive.py` (the core), `learn/rederive_rows.py` (the rows), `learn/rederive_fit.py` (the fit) and
`learn/rederive_diag.py` (the diagnosis).

Every number here is by the score (J0), not heard. Intervals are 90%, from `scratch_notes.set_rows` on BKS+GOAT (the
40); all 47 parts go beside. Labels come only from `paired_reading`.

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
