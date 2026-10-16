# Arm B sound-space retraining (3B): results (2026-10-16)

Run under the [plan](song-to-settings-soundspace-plan.md) and its amendments 1–4.
- **Arms:** B1 (a censored head, sensitivity weights, record-like examples) and B2 (B1 plus sets of
  settings that sound alike and 2,500 record-like renders), against the current arm B (B0).
- **Renders:** the relabel and new examples took about 11.5k, and scoring about 3.3k.
- **Independent audit:** every figure reproduces; its scripts are in
  [audits/soundspace-2026-10-16](audits/soundspace-2026-10-16/).
- **Reading these figures:** band-weighted log ratios with 90% band-clustered intervals; negative
  means closer.

## On step 3's songs (E3, top answer, 142 directions)

| | Against S | Against B0 (paired) |
|---|---|---|
| B0 | +0.035 | — |
| B1 | +0.010 | −0.025 |
| **B2** | **−0.033 [−0.100, +0.035]** | **−0.068 [−0.111, −0.024]**, 10/14 bands |

- **B2 clearly beats the old model** on every amp and class, in leave-one-out, and against B1
  (−0.043 [−0.082, −0.004]).
- **It isn't shown to beat S;** the declared choice is S.
- **Its gain likely comes from the record-like data:**
  - The set loss didn't seek modes: the trained responsibilities equal the member weights.
  - Input gain didn't improve.
  - B2a wasn't run, so these can't be separated.
- **It holds without bleed-affected halves:** B2 − B0 stays at −0.065 to −0.070 in every subset.

## On render targets (E1, 228 units)

B0 −0.150, B1 −0.140, B2 −0.168, all tied.
- Retraining traded accuracy on broad targets for record-like ones: B1 and B2 are worse on the broad
  half and better on the K_S-prior half.

## The diagnosed failures

- **Mid-range shrinkage partly fixed:** answer spread over label spread went from 0.46 to 0.63, and
  on songs from 0.41 to 0.65.
- **Range-limit answers:** 0% → 3%, against about 32% of record optima.
- **Input gain:** unchanged, ρ about 0.37 on targets and 0.1 on songs.
- **Switches:** B2 agrees with the record optimum more often on songs, +0.055.
- **The density bridge:** B0 preferred settings farther from the record (+0.13); B2 doesn't (+0.02).
  Scored with the common censored box, B0 is +0.08, so B2 − B0 is −0.057 [−0.122, +0.008].
- **New failure mode:** one answer muted the amp with a level of 0. It scored as S, under the
  refusal rule.

## What it decides

- **Arm B is paused.** Sound-space training moved it the right way, but it doesn't beat the starting
  preset on songs. It isn't a better proposer for arm A either: arm A from S is already at −0.08.
- **C-fine and C-start aren't run.** The expected gain is at most about 0.02, and C-fine's cap
  arithmetic in the code would stop it.
- **A cheap control, if arm B is reopened:** B2's shuffled-input test (about 290 renders). It would
  show whether B2's gain comes from reading the song or from a better prior.
- **Noted for later:**
  - 2,237 bank examples share a track with a diagnostics target, though no window overlaps.
  - S was scored in an earlier session, and no re-render check was run against it. B2 − B1 is
    unaffected.
