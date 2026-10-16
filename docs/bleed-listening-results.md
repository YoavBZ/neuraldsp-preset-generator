# Bleed listening check 1: results (2026-10-16)

Plan: [bleed-listening-plan.md](bleed-listening-plan.md). One sitting by the user, scored with
`learn.build_bleed_listening score`. Answers: `1Both-no 2N-no 3N-no 4Both-no 5Both-no 6N-no`.

| Trial | Kind | Part, half | Bleed removed | Leaking | Damage (not read) |
|---|---|---|---|---|---|
| 1 | high | Sculptor's Request GTR_1, B | −12.9 dB | both | no |
| 2 | low | Drag Me Down ElecGtr4, A | −36.1 dB | neither | no |
| 3 | repeat | Farthest Step GTR, B | (A = B) | neither | no |
| 4 | high | Gym Hours GTR_1, B | −9.9 dB | both | no |
| 5 | high | First Offering GTR_1, A | −13.3 dB | both | no |
| 6 | low | Farthest Step GTR, B | −29.8 dB | neither | no |

## Reading

- **The bleed is audible** on all 3 high parts, and inaudible on both controls. The repeat
  matches its control (a weak consistency check: it was drawn from a low control, so "neither"
  on both is an easy match). This agrees with the audit's split of which parts carry bleed.
- **This cleaning left audible leakage on all 3 high parts.** It subtracts a linear bleed
  estimate at about −10 to −13 dB of the track, below 12 kHz only (nothing above, so cymbal and
  drum-air bleed stays). Whether it *reduced* the leakage was not asked. Whether it damages the guitar is not read from this sitting: the damage question
  had no known reference (plan amendment 1), so it is re-asked in check 2.
- **So the high-bleed parts are not isolated guitar records,** even after this cleaning. Results
  that matter should keep reporting the no-high-bleed row beside the all-parts row (the audit
  found arm A's results hold without the high-bleed halves: −0.085 against −0.083 for the shrunk
  3-C′ recipe, and −0.082 against −0.078 for plain arm A). Experiment 1c's report
  carries these rows.
- **Not adopted:** the model-based cleaning as a step. A stronger route (a real separator on
  the amp track, or dropping high-bleed parts from training records) is open.
- **Caveats:** 3 high trials, all from one band (Telefunken, Dom McLennon). Too few for an
  interval.
