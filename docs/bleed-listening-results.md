# Bleed listening check 1: results (2026-10-16)

*Superseded 2026-10-22 (the user): "use only what we can trust, no dirty tracks". Dirty tracks are
now excluded, not flagged, so the "stay flagged" and no-high-bleed-row practice below is
historical ([ROADMAP](ROADMAP.md), step 0).*

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

# Bleed listening check 2: damage against a labelled original (2026-10-17)

Plan: [bleed-listening-plan.md](bleed-listening-plan.md), amendments 1 and 1a. One sitting by the user, scored with `learn.build_bleed_damage score`.
Answers: `1X-little-tone 2Y-little-tone 3Y-little-tone 4N 5N 6N`.

| Trial | Kind | Part, half | Subtracted (re track) | Picked | Names | Amount, what |
|---|---|---|---|---|---|---|
| 1 | high | Sculptor's Request GTR_1, B | −12.9 dB | X | cleaned | little, tone |
| 2 | high | First Offering GTR_1, A | −13.3 dB | Y | cleaned | little, tone |
| 3 | high | Gym Hours GTR_1, B | −9.9 dB | Y | cleaned | little, tone |
| 4 | low | Farthest Step GTR, B | −29.8 dB | N | neither | |
| 5 | low | Drag Me Down ElecGtr4, A | −36.1 dB | N | neither | |
| 6 | null | Gym Hours GTR_1, B | (X = Y) | N | neither | |

## Reading

- **On all 3 high parts the listener picked the cleaned clip, and heard the guitar's tone change
  a little.** By the declared rule that counts as damage on 3 of 3. The hidden original was never
  picked.
- **No false alarms:** "neither" on both near-null controls and on the null trial.
- **Caveats:**
  - Level matching raises the cleaned clip by about 0.7 dB on Gym Hours and about 0.2 dB on the
    other two high trials, so level can explain little of trials 1 and 2.
  - The cleaning removes the bleed's own energy below 12 kHz, so the clip's overall spectrum
    changes even if the guitar itself is untouched. The listener answered "tone" on every high
    trial and never "background" or "both", although the cleaned clip has 10–13 dB less bleed.
    So "tone" may partly be the bleed removal heard as tone, not harm to the guitar. This is a
    caveat on the reading, not grounds to discount the answers.
  - The null trial reuses trial 3's passage (trial 6, not adjacent).
  - Three trials from one band; too few for an interval.
- **Together with check 1:** this cleaning leaves audible leakage and is heard as changing the
  guitar's tone a little (counted as damage by the declared rule; see the caveats). It is not
  adopted. The high-bleed parts stay flagged, and results keep the
  no-high-bleed row beside the all-parts row.

Audited 2026-10-17 by an independent agent: table and scoring confirmed; changes: the level caveat per
trial, the spectrum caveat on "tone", and a hedged summary line.
