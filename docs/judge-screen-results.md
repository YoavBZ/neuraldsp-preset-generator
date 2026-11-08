# The judges we have, on whole presets the ear ranked (S12): results

Run 2026-11-08 as declared in [judge-screen-plan.md](judge-screen-plan.md), after two independent reviews. CPU only, zero renders, about 95 s. Ledger `judge-screen`. Audited by separate code. Every mean, count, p and the naming result reproduce exactly. Interval ends differ by at most 4e-5, since the stored code's t table is rounded. The audit also rebuilt every card's ranks and closeness from the raw answers.

**The short answer.** None of the five judges we already have orders these presets more like the ear than J0. So none is named for H4b's fresh page, which will read J0 alone. Judge v3 leans worse. `J-f6` is level on the heard pairs but leans worse on the forced ranks and within-card order. The rest come out level. Where the listener heard a difference, J0 already agrees with it 70 times in 80.

## What ran

- The cards were the 36 development cards: F57 10, `ear-eat` 13 and N12 13. They fall in 13 clusters, 11 of which hold a heard pair. A heard pair is two candidates rated differently close.
- J0, rebuilt from the stored clips, gives back its stored value on every candidate. The worst miss is 4.5e-4, on `EW-mix` on `ear-eat`'s p1:i12, not a label. The audit's path at the true lag matches the stored J0 within 4e-8 there. The miss comes from this plan's shift of the DI to lag 0. It moves the DI's loudest-frame level by up to 0.2 dB, and so the threshold for where the DI plays. On this card 2 frames cross it. The size of the lag is not the cause. On that card and on p2:i5, the other judges move by up to 8e-4 the same way. No pair's order changes on either card. The other 34 cards match within 1.3e-4. No card and no label dropped out.
- Every judge read the same aligned audio, and every in-run check held. J5's J0 term equals J0. `bakeoff_judge`'s `tonal` equals J0's own. `J-f6` gives 0 for a reference against itself. No judge refused a candidate, and none tied a pair.
- The rows below have labels left out, since the search chose the labels on J0. On 2 of the 80 heard pairs the listener's rank runs against its closeness rating. The rows follow closeness.

## By the ear's heard differences (the primary)

Each judge's share of heard pairs ordered as the closeness says, less J0's. Pooled by pairs, with a 90% interval from a delete-one-cluster jackknife (df 10), and Holm over the five judges.

| Judge | Less J0, heard pairs (80) | Holm p | By cluster | All pairs by rank (166) | Within-card order (26 cards) |
|---|---|---|---|---|---|
| J0 | 0.875 agree [0.803, 0.947] | | | 0.801 agree | |
| v2 | +0.000 | 1 | +0.000 | −0.048 [−0.117, +0.021] | −0.11 [−0.26, +0.05] |
| v3 | −0.087 [−0.153, −0.022] | .18 | −0.105 [−0.216, +0.007] | −0.078 [−0.141, −0.016] | −0.18 [−0.32, −0.04] |
| J5 | −0.062 [−0.136, +0.011] | .62 | −0.125 [−0.278, +0.029] | −0.042 [−0.086, +0.002] | −0.11 [−0.23, +0.02] |
| `tonal` | −0.013 [−0.073, +0.048] | 1 | −0.012 [−0.105, +0.081] | −0.036 [−0.098, +0.026] | −0.08 [−0.20, +0.05] |
| `J-f6` | −0.062 [−0.174, +0.049] | 1 | −0.014 [−0.129, +0.100] | −0.108 [−0.186, −0.031] | −0.25 [−0.46, −0.05] |
| `S-last`, no audio | −0.050 [−0.156, +0.056] | | −0.010 [−0.103, +0.083] | −0.054 [−0.135, +0.026] | −0.14 [−0.33, +0.05] |

- No judge's mean is above zero, so by the plan none is named. v2 orders every heard pair as J0 does. It parts from J0 only on 16 pairs the listener rated alike.
- v3 is the only one whose plain interval sits below zero on the primary. After Holm it reaches .18, so "worse" is a lean. It is below zero on every row, and its interval stays below zero except by cluster (+0.007). It rests on 7 of the 80 heard pairs, on 5 cards in 4 clusters, and v3 gets all 7 wrong. Leaving out one cluster at a time, it reads −0.100 to −0.065. J5 also changes 7 heard pairs, on 5 cards, and gets 6 wrong, nearly all on margins under 0.06. Leaving out one cluster, it reads −0.080 to −0.039.
- Labels in, the reading is the same. Only v2 reads above zero, +0.006 [−0.005, +0.016] on 174 heard pairs, and the primary leaves labels out. The rest are below zero.

## Where they part from J0 (row 6, descriptive)

| Judge | Pairs ordered unlike J0 | Of them heard | Heard ones going the ear's way | Heard pairs under a J0 log ratio of 0.06 (14): agree, J0 8 | Models-only heard pairs (27): agree, J0 20 |
|---|---|---|---|---|---|
| v2 | 16 | 0 | 0 | 8 | 20 |
| v3 | 23 | 7 | 0 | 5 | 17 |
| J5 | 17 | 7 | 1 | 5 | 20 |
| `tonal` | 18 | 5 | 2 | 8 | 21 |
| `J-f6` | 40 | 13 | 4 | 10 | 19 |

- Where J0 is weakest, on small gaps and between models, no judge gains more than two pairs. `J-f6` gets 10 of the 14 small-gap pairs against J0's 8. But it loses 9 of the 13 heard pairs where it parts from J0. `tonal` gains one models-only pair.
- `J-f6` on pairs with `EW-mix`, which reads EfficientAT's features too: 26 of 33, the same as J0. Without `EW-mix` it gets 39 of 47, against J0's 44.
- By page, every primary row is at or below zero. `ear-eat` carries v3's lean (−0.152 [−0.289, −0.014]). On F57 only S and the placebo are compared, and no judge but `J-f6` orders them unlike J0.

## What this means

- **J0 stays,** and it was never in question here. The judges built to fix its known faults on synthetic tests (v2, v3) and on pages moving one control (J5) don't order whole presets better. Neither do `tonal` or a deep-feature distance.
- **The score's gap with the ear is where the ear hears little.** Of the 80 differences the listener heard, J0 misses 10. On the 86 pairs rated alike, its forced order misses 25. The forced order between candidates rated alike is the larger part of the disagreement, and no judge here moves it either.
- **H4b reads J0 alone,** as the plan says when none is named. A judge that would beat J0 would have to be new. That would need its own plan and a fresh page, and nothing here points at one.
- **What this can bear.** One listener, 36 cards, 11 clusters on the primary, and pages built for other questions, read many times. Undecided is not failed, and a lean here is not a verdict. A judge's verdict needs a fresh blind page.

Files: `PF/eat/judge-screen/` (`control.json`, `judges.json`, `report.json`, `judge.log`, `audit/`). The result can't be recomputed once the captures are deleted, since F57's and N12's sources are capture recordings.
