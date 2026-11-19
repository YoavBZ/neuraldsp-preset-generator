# The score against the ear, on today's decisions: results

**Status:** sitting 1 was sat 2026-11-18 to 19 and read once on 2026-11-19. The independent audit passed with
corrections, and they are taken here. Plan: [ladder-ear-plan.md](ladder-ear-plan.md). Ledger `preset-ladder`:
`phase_lear`, `phase_lear_draw`, `phase_lear_outcome`. Code `learn/ladder_ear.py`. Data `PF/ladder/ear/` (`read-1.json`,
`key-1.json`, `plan.json`, `answers/`); `PF` is `~/ndsp-presets/learn/trusted-data/pipeline-fix`. One listener. Items
marked **post hoc** were not declared before the read.

## The read

**Outcome (a), row 5 of the declared table: the score is trusted for the three reads the page covers.** On the
ladder's held-out parts, with the recorded guitar as the reference, the ear heard:
1. the label-centre preset Cen closer than the stock start S;
2. the search label closer than Cen;
3. the model's preset on the product's stem (`xl@-3`) not better than Cen. Its share is not known by ear, and an ear
   preference for the model above a 0.62 share is ruled out (0.69 for the re-centred answer).

These hold at score gaps of about 0.1 and over, on clean and mild crunch.

**What it does not cover:**
- anything under a score gap of 0.05: Steps 5 and 6's expected gains and the separator ceiling (−0.035). Under 0.05
  the ear tied 57% of pairs and agreed with the score on 8 of the other 13, near a coin flip;
- `rc-mix@-3 − cen`, so Step 2's stop as a whole;
- effects: every preset but the label held its effects at S.

**What it changes, in plain words:** the decisions resting on large score gaps stand by ear. Cen beats S, the labels
beat Cen, and the model path stays off by default. **But Cen beating S rests on crunch** (post hoc, below). This page
does not license making Cen the starting preset for clean tones; for crunch it supports it. The next decisions,
all under 0.05, still need their own ear read or a larger effect.

## What ran

| Stage | What | Measured |
|---|---|---|
| Draw | once from main b2635047, sha256 into the ledger (PR #515) before any render or judge read; independently audited (byte-identical reproduction) | under a minute |
| Renders | 57 cards and spares × 5 presets, each primed in its own process, 3 shards | 570 renders, 00:04 to about 00:12; 0 checks failed |
| Page | 24 items in two private Artifact parts (13.6 and 13.7 MB), answers in the page's db | zero renders |
| Sitting | part 1 on 2026-11-18, part 2 on 2026-11-19 | median 3.0 and 2.4 min from first play to last change per item |
| Read | `read --sitting 1`, once, from main 3e4a161a | about a second |

- **Checks:** every Cen, M, rc and label clip equalled its stored render by hash. S matched its stored score within
  0.005. No card was put out and no spare used. Every letter sat within 4e-9 LU of its Record after levelling.
- **The audit** (independent, its own code) reproduced every number in the read:
  - the live db documents equal the stored copies byte for byte;
  - the page order and letters re-derive from the seed;
  - all 120 J0 values equal the render records;
  - all 144 page clips trace to the intended candidate's audio.
- **21 of 22 first hearings ranked.** One card, i14 (panel, clean), was marked "Can't judge this one". At least 18
  were needed.

## The declared rows

First hearings, one card a cluster. A share counts a tie as half, with its 90% delete-one-cluster jackknife t
interval. The sign test is one-sided on untied cards. J0 is ln(d_first / d_second) on the held half, below zero
meaning the first is closer. Closeness is the first preset's rating less the second's, on 0 to 3.

| Pair | Above/tie/below | Share [90%] | Sign p | By ear | J0 mean [90%] | J0 agrees, untied | Closeness gap [90%] |
|---|---|---|---|---|---|---|---|
| L over S (the label control) | 21/0/0 | 1.000 [1.000, 1.000] | <0.0001 | heard above, firmly | −0.522 [−0.621, −0.423] | 21/21 | +2.19 [+1.86, +2.52] |
| Cen over S | 14/2/5 | 0.714 [0.551, 0.878] | 0.032 | heard above, firmly | −0.087 [−0.160, −0.014] | 17/19 | +0.57 [+0.09, +1.06] |
| L over Cen | 17/1/3 | 0.833 [0.696, 0.971] | 0.0013 | heard above, firmly | −0.434 [−0.515, −0.354] | 17/20 | +1.62 [+1.09, +2.14] |
| M over Cen | 7/5/9 | 0.452 [0.285, 0.620] | 0.77 | not known | +0.022 [−0.065, +0.110] | 13/16 | −0.24 [−0.67, +0.19] |
| rc over Cen | 7/9/5 | 0.548 [0.403, 0.692] | 0.39 | not known | −0.012 [−0.079, +0.054] | 10/12 | −0.19 [−0.52, +0.14] |

- Holm over the five pairs (beside): L over S 0.000, L over Cen 0.002, Cen over S 0.106, M and rc over Cen 1.
- **A1** (heard-pair agreement, labels out, the form row 2 reads): 0.863 [0.794, 0.932] on 95 heard pairs in 19
  clusters, so there is no row-2 trigger. S12 read 0.875 [0.803, 0.947]. With labels in: 0.881 [0.831, 0.930] on 176.
- The table's rows in order: row 1 does not hold (21 ranked); row 2 does not (nothing firmly below, A1's upper end
  0.932); row 3 does not (the control is heard above); row 4 does not (neither model firmly above Cen). **Row 5 holds:
  (a).**

## Beside

| Pair | Above/tie/below | Share [90%] | By ear | J0 mean |
|---|---|---|---|---|
| M over S | 11/3/7 | 0.595 [0.421, 0.770] | not known | −0.065 |
| rc over S | 10/3/8 | 0.548 [0.370, 0.725] | not known | −0.099 |
| rc over M | 8/9/4 | 0.595 [0.454, 0.736] | not known | −0.035 |
| L over M | 18/1/2 | 0.881 [0.763, 0.999] | heard above | −0.457 |
| L over rc | 17/1/3 | 0.833 [0.696, 0.971] | heard above | −0.422 |

**The splits.** The cells are small, so most read "not known".

| Split | Cen over S | L over Cen | M over Cen | rc over Cen |
|---|---|---|---|---|
| Deciding sets (GOAT, BKS, panel; 17 cards) | 12/1/4, 0.74, heard above | 14/0/3, 0.82, heard above | 5/4/8, 0.41 | 5/7/5, 0.50 |
| GOAT (10) | 7/1/2, 0.75, heard above | 8/0/2, 0.80, heard above | 3/2/5 | 3/4/3 |
| BKS (4) | 3/0/1 | 3/0/1 | 1/2/1 | 1/2/1 |
| Panel (3) | 2/0/1 | 3/0/0, heard above | 1/0/2 | 1/1/1 |
| cap1 (4) | 2/1/1 | 3/1/0, heard above | 2/1/1 | 2/2/0 |
| Clean (10) | 3/2/5, 0.40 | 9/0/1, 0.90, heard above | 2/4/4 | 0/8/2 |
| Crunch (11) | 11/0/0, 1.00, heard above | 8/1/2, 0.77, heard above | 5/1/5 | 7/1/3 |
| ac20 (5) | 5/0/0, heard above | 2/1/2 | 3/0/2 | 3/1/1 |
| pr12 (8) | 5/2/1 | 8/0/0, heard above | 2/2/4 | 2/3/3 |
| sw50r (8) | 4/0/4 | 7/0/1, heard above | 2/3/3 | 2/5/1 |

**Agreement:**
- **A2,** order within a card: J0 0.764 [0.672, 0.856] over 21 cards; labels out 0.728 [0.600, 0.857] over 19, with 2
  cards ranked all equal.
- **A3,** what J0 adds over a fixed order by preset type: by A1 +0.253 [0.131, 0.374] labels out, +0.136 labels in; by
  A2 +0.208 [0.099, 0.317], and labels out +0.513 [0.261, 0.765]. J0 carries real per-card information, not only the
  preset type.
- **A4,** by J0's gap, all 210 pairs:

| J0 gap | Pairs | Ear ties | Untied agreeing with J0 |
|---|---|---|---|
| under 0.05 | 30 | 57% | 8 of 13 |
| 0.05 to 0.15 | 54 | 31% | 33 of 37 |
| 0.15 and over | 126 | 0% | 114 of 126 |

- **A5,** the repeats: 9 of 10 and 8 of 10 pairs were ordered the same, 17 of 20 in all.

## The audit's corrections (all post hoc; none changes the declared (a))

1. **Cen over S rests on crunch.** Crunch reads 11/0/0; clean reads 3/2/5 (0.40 [0.13, 0.67], not known, leaning to
   S). The plan reports class beside and declares no class split, so (a) stands pooled. J0 is not contradicted on
   clean: on these clean cards it gives Cen − S +0.027 [−0.064, +0.119], and it matches the ear on 8 of 8 untied clean
   cards. On the ladder's pool J0's clean Cen − S is only about −0.06 a set, under the page's 0.1 coverage; crunch is
   −0.14 to −0.26. **So "Cen beats S on clean" is neither heard nor a covered gap, and no clean Cen-start change
   follows from this page. For crunch it is supported.**
2. **Cen over S is fragile.**
   - Holm gives it 0.106.
   - It is the pair that changed on both repeats.
   - It reads not known when the repeats replace their first hearings (0.619 [0.441, 0.797]), and when GOAT is left out.
3. **i14, vocal bleed in the Record.**
   - The listener's note on the can't-judge card reads "Leaking singing in the record". By the trusted-data rule that
     unit is excluded. It was already out of every row, so nothing changes.
   - Its DI file (Silent Waves) is in the held second sitting only as a spare, not as a card.
   - The same band's Drowning has a second-sitting card, which needs a bleed check before any use.
   - The ladder pool's Silent Waves parts feed the panel's J0 rows and need a trusted-data review.
4. **i3, "Reverb is missing in all presets".** The Record carries a reverb that even the label, whose effects were
   searched, did not reproduce. Closeness on that card is dry against wet, and its J0 gaps are compressed. Effects stay
   outside (a). The card was answered consistently (9 of 10 pairs on its repeat), so this is a caveat, not grounds to
   exclude it.
5. **A4: small gaps are not heard.** Under a J0 gap of 0.05 the ear ties 57% of pairs, and on the rest it agrees with
   J0 on 8 of 13, near a coin flip (sign p 0.29). From 0.05 to 0.15, agreement is 0.89. A decision resting on a J0 gap
   under 0.05 can't be called heard, and J0 can't steer it with ear backing.
6. **Listener consistency.** 17 of 20 repeated pairs were the same. Of the 3 pairs that changed, 2 were Cen against S,
   one on each repeated card (the third was M against rc), so the listener is least stable exactly on the weak key
   pair.
7. **J0 against a fixed order.** J0 adds over a fixed preset-type order (A1 +0.25 [0.13, 0.37]; A2 labels out +0.51),
   evidence for the score beyond the preset type.

## What this read can bear

- One listener, 21 cards, about 4.5 s of guitar alone a card. A real mix masks differences this page exposes.
- The model's input is the ladder's built mix, not a released song.
- Crunch comes from each set's milder half.
- No second sitting runs: it was declared only for (c).

## For the goal

The product steers by J0 alone, so this is the check on whether that steering follows the ear. It does, for gaps of
about 0.1 and over: the label and Cen orderings are heard, and J0 adds information over a fixed preset order. It does
not for gaps under 0.05, which is where Steps 5 and 6 and the separator ceiling sit. Those need a bigger effect or
their own ear read before any product change. Cen as the starting preset is supported for crunch, not for clean.

Files: `PF/ladder/ear/read-1.json` (sha256 ad9b55fc…33d7, in `phase_lear_outcome`), `key-1.json`, `answers/`,
`db-snapshots/`. The audit's code and notes are kept outside the repo.
