# The note-matched replay: does render-and-compare pick well through a worse reference or dry guitar? (results)

**Status:**
- **Run:** 2026-11-20, every step from merged main. The declaration and code are PR #524's squash `6c53524f`; the
  draw's hash is #526 (`b54c5108`) and the picks' hash #530 (`bdb7b296`). `learn/note_replay.py` and every `learn/`
  module it uses are unchanged across those three commits.
- **Audited:** 2026-11-20 by an independent blind recompute with its own code, PASS WITH CORRECTIONS. Every number
  reproduced, the cell re-derived, and the provenance is clean. The corrections are taken here (marked **audit**).
- **Plan:** [note-replay-plan.md](note-replay-plan.md).
- **Ledger:** `preset-ladder` `phase_replay`, `phase_replay_draw`, `phase_replay_picks`, `phase_replay_outcome`.
- **Data:** `PF/replay/` (`PF` is `~/ndsp-presets/learn/trusted-data/pipeline-fix`). It holds `draw.json` (sha256
  `c0f834ad…f470`), `controls/`, `blur.json`, `dist/`, `picks.json` (sha256 `ab2c997d…d8a6`), `report.json` and
  `logs/`. The stems are kept for the rebuild work and are on the cleanup protect list.

Every number is by the score (J0, on the held half, through the true DI against the clean record), not by ear. Below
zero is closer. The intervals are 90% cluster t, with BKS, GOAT and the panel pooled equally. Items marked **post hoc**
were not declared before the read.

## The read

**R-alone, by the score: render-and-compare still picks well where the target is the only or the dominant guitar,
and it fails on a full mix.**
- The comparison works through a blurred dry guitar, keeping 72% of the true DI's gain over a blind pick.
- It works against X-LANCE's stem of a mix with no other guitar, keeping 83%.
- It works with both together, keeping 51%.
- Against the stem of a full mix with other guitars, it picks **worse than a blind pick**.

**What follows (the declared next):**
1. The route continues, scoped to windows where the target is the only or the dominant guitar.
2. **How many songs offer such windows is still to be counted** (**audit**). R-alone asks for that count, and it has
   not been made.
3. **A pass is necessary, not sufficient.** It says the degraded comparison ranks a true-DI search's candidates well.
   It does not say a search through it works. Before any product claim comes a from-scratch search through the
   degraded inputs (the stem and the blurred dry guitar), scored on the held half against Cen.
4. **The rebuild's stage 1 waits for the user** (**audit**). The rebuild plan's gate asks the user before stage 1 when
   a Both row of the replay fails, and `both-full` fails. Its code checks only the matching Both row's note, which is
   empty for R-alone, so it would open the gate without asking. The question goes to the user, or a ruling on what the
   gate means is recorded first, before stage 1 renders.

**What it does not say:**
- how a real note-matched dry guitar performs;
- anything on released mixes (the mixes are built, on six lender sessions);
- anything by ear;
- anything about effects or level and timing errors in the dry guitar.

## What ran

| Step | Measured | Checks |
|---|---|---|
| draw | 02:47:00, seconds | 122 parts: BKS 40 on 8 DI files, GOAT 72 on 72 items, the panel 10 on 4 DI files; 0 dropped, 1 GOAT part passed over |
| blur | 174 s, 122 parts × 3 dry guitars | — |
| sep (MPS) | 244 stems in 1,098 s | every rebuilt mix equal to its stored build; every stem's SI-SDR equal to the ladder's (medians 16.6 dB with no other guitar, 0.55 dB on the full mix) |
| position check | 288 renders in 434 s (2,387 an hour, one process) | 276 of 276 within 0.005 (max 1.2e-4): the main pass in one primed process a part |
| render, 3 shards | 5,856 renders in 3,776 to 3,882 s | no guard fired |
| control | seconds | 2,806 of 2,806 within 0.005 (max 8.1e-4), none beyond 0.02, 0 order mismatches on 45 gated parts |
| pick | seconds, on the orchestrator's go after the rebuild's P8 declaration merged | 119 parts; Drowning's 3 left out (no ear check recorded), as declared |
| score | seconds, one read | the rows saved before the outcome |

- **Totals:** 6,144 renders, 244 separations, no training. The single-blur rows did not run, since the blurred DI
  passed.
- **The order of the halves held:** the picks were hashed and merged to main before `score` loaded any held-half value.
- **Six blurred-DI renders gave no distance** (**audit**). They are on 3 parts, one of them the label's render; the
  judge refused them on all three references (18 distances). As declared, the pick passed over them. They also explain
  the audit's Spearman differences of up to 0.003: the report drops those pairs, while the audit ranked them last.
- **Smoke checks before the declaration** ran in a scratchpad only (plan, section 10).
- **The rebuild's `notes` and `probe` steps** ran from 03:09 to 03:11, during the separations. Whether they used the
  MPS is not recorded. They had no effect: every stem reproduces exactly.

## The rows

Deciding pool, 119 parts. I is the pick less a blind pick (the menu's mean), the honest number. G is the pick less Cen,
a guard.

| Row | Reference / dry guitar | G | I | Reading | Share of the Control's I | I, label-free | Label share | Within-part Spearman vs true |
|---|---|---|---|---|---|---|---|---|
| Control | clean record / true DI | −0.374 [−0.489, −0.260] | −0.265 [−0.313, −0.217] | passes | 1.00 | −0.273 | 0.93 | 1.00 (vs stored) |
| Blurred DI | clean record / avg+mild | −0.299 [−0.377, −0.222] | −0.190 [−0.231, −0.148] | **passes** | 0.72 | −0.196 | 0.28 | 0.80 |
| Stem alone | `xlnoG@-3` / true DI | −0.330 [−0.516, −0.145] | −0.221 [−0.340, −0.102] | **passes** | 0.83 | −0.229 | 0.60 | 0.90 |
| Stem, full mix | `xl@-3` / true DI | +0.062 [−0.082, +0.205] | +0.171 [+0.045, +0.298] | **fails** | −0.65 | +0.161 | 0.05 | −0.10 |
| Both, alone | `xlnoG@-3` / avg+mild | −0.245 [−0.408, −0.082] | −0.136 [−0.208, −0.064] | passes | 0.51 | −0.141 | 0.22 | 0.73 |
| Both, full mix | `xl@-3` / avg+mild | −0.018 [−0.153, +0.118] | +0.092 [−0.030, +0.214] | fails | −0.35 | +0.084 | 0.09 | 0.02 |

- **R_TABLE:** the dry guitar passes, the stem alone passes, the stem of the full mix fails: **R-alone**.
- **The Both notes:** the matching Both row for R-alone is `both-alone`, which passes, so no note fired. `both-full`
  fails, and that matters for the rebuild's gate (above).
- **No row reads "not readable by the score":** no interval sits inside ±0.05.
- **Both-alone "passes" by the declared rule but is not shown a heard size over a blind pick** (**audit**). Its
  interval, [−0.208, −0.064], does not rule out a gain under 0.1 over blind. Against Cen it reads −0.245, and 67% of
  its parts are 0.10 or more better than blind (post hoc). The panel's fragility (below) applies to it too.
- **The stem of the full mix is decided worse than a blind pick.** Its picks move away from the Control's: they equal
  it on 6% of parts and are the label on 5%.

**Per set (I):**

| Row | BKS (8 DI files) | GOAT (72 items) | Panel (3 DI files) |
|---|---|---|---|
| Control | −0.276 [−0.324, −0.228] | −0.291 [−0.315, −0.266] | −0.228 [−0.385, −0.071] |
| Blurred DI | −0.188 [−0.262, −0.113] | −0.201 [−0.238, −0.164] | −0.181 [−0.314, −0.047] |
| Stem alone | −0.267 [−0.314, −0.220] | −0.256 [−0.290, −0.222] | −0.139 [−0.483, +0.205] |
| Stem, full mix | +0.264 [+0.114, +0.413] | +0.185 [+0.134, +0.235] | +0.066 [−0.334, +0.465] |
| Both, alone | −0.160 [−0.232, −0.087] | −0.177 [−0.220, −0.134] | −0.071 [−0.301, +0.160] |
| Both, full mix | +0.111 [−0.017, +0.239] | +0.094 [+0.038, +0.150] | +0.071 [−0.326, +0.468] |

- **Clean and crunch:** every passing row is decided better in both classes on BKS and on GOAT, except BKS clean on
  `both-alone`, −0.119 [−0.243, +0.004]. The panel's class cells are too thin to read.
- **Without the heavier lenders** (pool I): blurred −0.196, stem alone −0.258, stem full mix +0.229, both alone
  −0.162, both full mix +0.142. Every reading holds.

## The adversarial read (post hoc)

**Is the menu too easy?**
- I removes the menu's average quality: a blind pick's G is −0.083, and the oracle's I is −0.299.
- No reading changes on any of these other menus: without the label; the 20 trials alone (blurred −0.182, stem alone
  −0.216, both alone −0.126); without the label and the best trial. **So the passes are not the label's.**
- I does not control what the menu leaves out. It holds only settings a true-DI search visited, none of the degraded
  comparison's own false favourites. A from-scratch search could find those, so it is still required. The full-mix
  stem shows what they look like.

**The stem of a full mix.**
- **It prefers the worst trials and more gain:**
  - its picks sit at a mean level of 13 of 0 to 19, and 79% come from the worst half;
  - it picks S on 24 of 119 parts and the label on 6;
  - its picks turn the second drive on in 66% against the Control's 34%, with the input gain 3.1 dB higher;
  - the distances spread less inside a part (SD 0.12 against 0.22), and they barely follow the menu's levels
    (Spearman −0.08, against 0.77 on the stem with no other guitar).
- **It is worse than blind even in kinder conditions:** +0.133 on the parts whose stem reaches 3 dB SI-SDR or more,
  and +0.229 without the heavier lenders.
- **A likely cause, not proven:** bleed from the other guitars opens bands the judge takes from the reference, and
  denser renders fill them.
- **For the product,** whose songs have other guitars, render-and-compare against an X-LANCE stem actively harms
  unless the window holds the target alone or dominant.

**The panel.**
- Stem alone, per panel DI file: Aimee Norwich −0.188, Big Troubles +0.085, The Laminar Flow −0.314.
- Without The Laminar Flow the panel's mean is −0.051. A pool keeping that 2-file panel reads −0.192 [−0.486, +0.103].
- BKS and GOAT alone read −0.262 [−0.290, −0.234].
- `both-alone` is as fragile: without The Laminar Flow the panel reads −0.019, and the pool is undecided.
- **The pass rests on BKS and GOAT.** On the real-band panel it is thin.

**The stem lag.**
- The stems are sample-aligned by construction: their SI-SDR is measured with no shift, a median of 16.6 dB with no
  other guitar.
- The re-estimates on the position check's 12 parts are erratic: they jump 20 to 54 samples on 3 parts.
- On the stem of the full mix the pick is the same on 12 of 12; on the stem with no other guitar, 9 of 12.
- Two of those three changes came from 1 to 3 sample shifts. They are near-ties, not a lag error.

## The audit's corrections, as taken

1. **The rebuild's gate:** `both-full` fails, so stage 1 waits for the user, or a ruling that the gate means the
   matching Both row is recorded first (the read, item 4).
2. **The six renders with no distance** are disclosed (what ran).
3. **Both-alone** "passes" and is not called a heard-size gain over blind; the panel's fragility is said for it too
   (the rows, the panel).
4. **The window count** that R-alone asks for is still owed (the read, item 2).
