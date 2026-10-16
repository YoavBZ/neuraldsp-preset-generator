# Bleed listening check 1: can the bleed in the amp tracks be heard, and can it be removed?

Declared 2026-10-16. Development only: a repeat use of five knob-ceiling parts (ledger entry
`bleed-listening`). Built and scored by `learn/build_bleed_listening.py`. Zero plugin renders.
The reading is descriptive. There is no pass or fail.

## Basis

The 2026-10-16 bleed audit ([audits/bleed-2026-10-16](audits/bleed-2026-10-16/README.md))
measured other-instrument bleed in each part's `reference.wav`, the amp track used as the
record. Its model (`bleed4.py`) predicts the bleed from the other session tracks:
- a model of the part's own DI first;
- then one complex weight per 4-bin band (47 Hz) per other track;
- fitted on the crop ±40 s with the judged half held out.

## Trials

- **3 high trials,** from the audit's listening candidates, each on the named held half:
  - Gym Hours GTR_1, half B (−8.4 dB; clearest spans 6.7–7.5, 8.1–9.0 and 9.2–9.9 s);
  - First Offering GTR_1, half A (−13.8 dB; 2.4–2.6 and 5.1–5.4 s);
  - Sculptor's Request GTR_1, half B (−12.6 dB; 6.6–7.3, 7.7–7.9 and 8.1–8.2 s).
- **2 low trials (controls):** Drag Me Down ElecGtr4 and Farthest Step, each on a whole half
  drawn with `random.Random(20261016)` (one `choice("AB")` per control, in sorted order).
- **1 repeat trial:** one control, drawn with the same RNG, played again with A and B both the
  original. It describes consistency only and never discards an answer.
- **Order:** the 6 trials are shuffled with the same RNG. The shuffle is redrawn while the
  repeat is trial 1 or sits next to its control.
- **Each trial plays the held half** (4.5 s) twice, as A and B:
  - **Original:** `reference.wav` cut to the half, as used in scoring.
  - **Cleaned:** the original minus the audit's held-out bleed estimate for that half. It uses
    the "clean" regressor set only, so no mic that carries this guitar is used. The estimate is
    the per-frame model output, overlap-added over every frame touching the half, upsampled
    from 24 to 48 kHz and aligned to the crop. Above 12 kHz nothing is removed.
  - Both are level-matched to −20 LUFS, with 20 ms fades.
- **The cleaned clip's letter** is drawn with `random.Random(20261017)`, balanced over the 5
  non-repeat trials (A on 2 or 3, which by a coin; the positions shuffled).
- **The builder checks** that its held-out gain reproduces the audit's `bleed_db` per half. It
  records the dB of bleed subtracted (energy of the estimate relative to the original) in the key.

## Questions

Per trial:
1. **Leaking:** which one has other instruments leaking in? A, B, Both, or N for neither.
2. **Damage:** does either one's guitar sound damaged compared with the other? No, a little,
   or a lot. The listener is not told which one is cleaned, so this reads as damage by the
   cleaning on non-repeat trials.

The answer line reads like `1A-no 2N-no 3B-little 4Both-lot`.

## Blinding

- The key (parts, halves, letters, the dB removed) is in `private/key.json`, beside the page.
- The page names no part, song, session or kind of trial. The builder asserts this.
- The page says one clip may have had leakage removed, and that some trials may have two
  identical clips.

## Reading (descriptive)

- **High trials:** how many answers name the original only, the cleaned only, both or neither,
  and the damage counts.
- **Low trials:** the same counts. Here the original and cleaned differ by little, so "neither"
  or "both" is what a reliable listener should give.
- **The repeat trial:** its answers beside its control's, as a note on consistency.
- Five trials can show whether the bleed is audible and whether cleaning harms the guitar. They
  are too few for an estimate with a useful interval.

Build: `.venv/bin/python -m learn.build_bleed_listening build`. Score:
`.venv/bin/python -m learn.build_bleed_listening score --answers "1A-no 2N-no ..."`.

## Amendment 1 (2026-10-16, after check 1's sitting): damage against a labelled original

The user noted that check 1's damage question had no known reference, so the original's drive
could be heard as damage, or damage as drive. Check 1's leak answers stand; its damage answers
are not read. Check 2 (`learn/build_bleed_damage.py`, page `listening/bleed-2/`) re-asks damage:
- the same 5 parts and halves, the same cleaning, zero renders;
- each trial plays **Original** (labelled), then X and Y: one is the original again (a hidden
  reference), the other the cleaned track; the cleaned letter balanced over the 5 trials
  (seed 20261018);
- one null trial (Gym Hours, half B) with X and Y both original, placed with the same seed, not
  first and not next to Gym Hours;
- per trial: which one differs from the Original (X, Y or neither), and how much (little or lot).

Reading (descriptive): on the high and low trials, how often the cleaned clip is named, the
hidden original is named, or neither, with the amounts; the null trial as a note on false alarms.
