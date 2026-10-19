# Record-match listening check 1: results (2026-10-19)

Run under the [plan](record-match-listening-plan.md) (PR #233, mono fold #234). Development data
(stage F's parts, fifth use), one blind sitting by Yoav, descriptive: no pass or fail.
- **Code:** `learn/record_match_listening.py`. **Page, key and scores:**
  `~/ndsp-presets/listening/record-match-1/` (`private/key.json`, `private/score.json`).
- **Renders: 775** (5 parts × 155), as planned. Every plumbing check passed (largest deviation
  0.00012 against the 0.005 limit).
- **Answers:** `1 A>B>C>D very; 2 C>A>B>D some; 3 C>B>A>D some; 4 A>C>B>D very; 5 B>A>C>D very;
  6 A>D>C>B very`.

## Headline

- **The ear's order broadly agrees with the judge's.** Spearman's ρ between the listener's ranks
  and the judge's held-half ranks averages **0.8** and is positive in **5 of 5** trials (1.0, 0.8,
  1.0, 0.8, 0.4). Much of that agreement comes from C, which is fitted to the judge and tops both
  orders in 4 trials. Among S, H and D alone ρ is 1, 0.5, 1, 1, −0.5 (mean 0.6), with one reversal
  (trial 5, where the judge puts H last and the ear second). So on these parts the measure is not
  obviously what limits our results, but this is not proof that it isn't.
- **The ceiling C is heard as closest in 4 of 5 trials** (second in the other), mean rank **1.2**.
  Two of those four were answered "very close". The judge puts C a geometric mean 0.64 of S's
  distance (log −0.45; per part 0.36 to 0.90). On the two parts where C is only 10–15% below S
  (Signs, get-out-of-bed), the ear still picked C first, a hint that a 10–15% gap in judge distance
  can be audible (the judge's scale may be compressed while its order holds).
- **Arm A (H) beats S by ear in 4 of 5** (mean rank 2.4 against S's 3.6). Caveat: the parts were
  picked for guitar exposure (highest htdemucs stem SNR), the setting that favours arm A, so this
  may not carry over to dense mixes.
- **The direct model D comes third on average** (mean rank 2.8; above S in 4 of 5). It was the
  closest once (Gym Hours, "very close"), where the judge also ranks it second, behind C.

## Per trial

| Trial | Part (class) | Ear, closest first | Judge order | ρ | Closest is | Judge: S, C |
|---|---|---|---|---|---|---|
| 1 | magilla elecgtr1 (clean) | C H D S | C H D S | 1.0 | very | 4.89, 1.77 |
| 2 | get-out-of-bed elecgtr2 (crunch) | C H D S | C D H S | 0.8 | some | 3.66, 3.12 |
| 3 | Signs ElecGtr3 (crunch) | C S H D | C S H D | 1.0 | some | 2.63, 2.37 |
| 4 | Gym Hours GTR_2 (clean) | D C H S | C D H S | 0.8 | very | 4.21, 2.51 |
| 5 | Today's The Day ElecGtr07 (crunch) | C H D S | C D S H | 0.4 | very | 4.77, 3.05 |
| 6 | repeat of 2 | C H S D | C D H S | 0.4 | very | |

- **Mean rank (of 5):** S 3.6, H 2.4, D 2.8, C 1.2. **Above S:** C 5/5, H 4/5, D 4/5.
- **Closeness:** very 3, some 2, not 0. The two "some" answers are the two crunch parts with the
  smallest S-to-C gap.
- **Repeat (trial 6 against trial 2):** ρ 0.8, the same top choice (C); the closeness answer moved
  from "some" to "very". Only the 3rd and 4th places (S, D) swapped.

## Limits

- Five parts, one amp each, one listener (trusted, per our rule). With 4 items a single trial's ρ
  is coarse (by the plan's figure a random order gets ρ ≥ 0.8 one time in 6), and over 5 trials
  no interval of useful width exists; these are counts, not estimates.
- C is fitted to the judge on the other half of the same part, so the ear preferring C partly
  checks the judge itself; it is an upper reference, not a product arm.
- The record is the part's amp track, and the renders use the true DI. This tests the judge's
  ordering on clean material, not arm A or D in the product setting (song only, separated stem).
