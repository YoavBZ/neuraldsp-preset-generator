# A crunch starting preset, and the ML chooser on crunch: results

2026-10-10, as declared in [crunch-baseline-plan.md](crunch-baseline-plan.md).
- **Order:** the plan was committed, then the choice (`crunch-baseline-choice.json`),
  then the check, run on existing scores only.
- **Review:** an independent reviewer reproduced the choice and both checks exactly
  (`tmp/crunch-baseline-review.md`, local).

**Outcomes:**
- **(1) The crunch presets are adopted for crunch songs, on weak evidence.**
- **(2) "ML adds value on crunch" is not shown,** though it leans that way.

## The presets (chosen on 13 development crunch parts from 6 bands)

- **PR12:** Keyan Houshmand / Modern Metal (Pick Hard): a pedal boost into a 54%-gain
  second drive, the heaviest of the three.
- **SW50R:** Neural DSP / Hair Metal: bright and moderate, with a light second drive
  pedal.
- **AC20:** Neural DSP / AC20 Mid-Gain Drive: amp-only crunch with no pedals, a sensible
  rock and indie start.

They are used dry. They are lighter than the driven baselines they replace for crunch.
`generate` presents them as the crunch starting point, because the factory names say
"Metal".

## Checks (held-out sets 1–2 crunch parts: 7 parts, 3 bands)

| comparison | mean log ratio | 90% interval | W / T / L | outcome |
|---|---|---|---|---|
| **(1) crunch preset vs the shipped driven preset** | −0.070 | −0.138 to −0.003 | 17 / 0 / 4 | **passes (adopt)** |
| **(2) ML chooser (3 kHz cut) vs crunch preset** | −0.056 | −0.117 to +0.005 | 13 / 5 / 3 | **not shown** |
| ML chooser (uncut) vs crunch preset | −0.058 | | 12 / 5 / 4 | |
| oracle vs crunch preset (headroom) | −0.104 (per half) | | | |

## How solid it is

**(1) is thin:**
- the upper bound is −0.003;
- weighting the bands equally fails it (−0.048, −0.144 to +0.048);
- Forkupines carries 12 of the 21 rows, and The Maybe Next Years is slightly positive.

**The development choice is unstable for PR12 and SW50R:**
- leaving one band out flips them in 2 and 3 of 6 bands;
- a median-of-band-medians rule picks Meet You In The Mids and Low Gain Solo, which fail
  check (1).

On held-out data the chosen presets still rank 1st, 3rd and 2nd against the shipped one.
The rule picked well; its edge is just small.

**By amp:** PR12 −0.098 (excludes 0), SW50R −0.049, AC20 −0.065.

**(2)'s signal is SW50R alone:**
- SW50R −0.135, 7 of 7 better;
- PR12 −0.038;
- AC20 +0.006.

**Heavier material goes the other way.** On set 4's metal-session crunch parts (out of
scope, report only), the lighter crunch presets lose 11 of 12 to the driven ones.
Getting the gain class right matters, and `generate` keeps the driven baselines for
heavier parts.

**The parts were seen before:** these 7 held-out parts were in the confirmation, where
the chooser beat the shipped preset on them by −0.126. This is their second declared
use, recorded in the ledger.

## Next

- **Firmer evidence on crunch** needs fresh rock, blues and indie crunch sessions with
  DIs, and ideally a short listening A/B.
- **The ML question moves to a different approach:**
  [sound-description prediction](ROADMAP.md) instead of rebuilding the DI.
- **Corrected by the [2026-10-11 audit](audit-2026-10-11.md):** with 3 bands this test
  could not pass (2 degrees of freedom, about 40% power), and all 3 bands lean the
  chooser's way. It is uninformative, not evidence against the network.
