# A fixed clean starting preset: results

2026-10-10, as declared in [clean-baseline-plan.md](clean-baseline-plan.md).
- **Order:** plan committed 19:22:08, choice committed 20:11:31, check written 20:11:44,
  with no new renders.
- **Review:** an independent reviewer reproduced the choice and the check exactly
  (`tmp/clean-baseline-review.md`, local).

**Outcome: confirmed, and adopted on all three amps.**

## The presets (chosen on development)

- **PR12:** Mark Johnston / Royally Ambient
- **SW50R:** Mark Johnston / Pedal Platform Clean
- **AC20:** Royce Whittaker / Low-Watt Americana

They were chosen on 22 clean development parts from 10 bands, and are used dry: reverb,
delay, tremolo, doubler and gate off, spring 0, transpose 0.

**Development report** (leave-band-out choice against template+R): −0.107 (−0.136 to
−0.078), 55 better, 0 tied, 11 worse, all 10 bands negative, each amp below 0.

## The check (held-out clean parts of sets 1–2: 13 parts, 8 bands)

| | mean log ratio vs template+R | 90% interval | W / T / L |
|---|---|---|---|
| **pooled** | **−0.132** | −0.195 to −0.070 | 34 / 0 / 5 |
| PR12 | −0.141 | −0.193 to −0.090 | |
| SW50R | −0.148 | −0.242 to −0.054 | |
| AC20 | −0.108 | −0.176 to −0.040 | |

- **About 12% closer than the template.**
- **The pass holds three ways:** 7 of 8 bands negative, every leave-one-band-out mean
  negative, and every interval below 0.

## Exploratory: the chooser against these presets (not declared, post hoc)

On the same held-out clean parts:

| | vs the fixed clean preset |
|---|---|
| chooser (3 kHz cut) | +0.009 (−0.057 to +0.075) |
| uncut rebuilt DI | −0.035 (−0.085 to +0.016) |
| oracle (true DI) | −0.131 (8 of 8 bands) |

- **Essentially all of the chooser's clean edge was the template being a weak start.**
  The edge was −0.123 against the template. A fixed preset captures it without a
  network, and the rebuilt-DI chooser adds nothing on top.
- **Per-song headroom exists** (the oracle is about 12% better still). It is out of the
  rebuilt DI's reach.
- **The chooser shouldn't run on clean parts for now.** This is post hoc, on viewed data
  and 8 bands.

## Caveats

- **Where the idea came from:** the hypothesis that the template is weak came from these
  same held-out parts, in the confirmation review. The selection used development only.
  On held-out, the PR12 and SW50R picks rank 3rd, not best.
- **Near-ties:** PR12 and SW50R are near-ties on development. Other summaries pick
  Jangly Combo Clean (PR12) or Big Tail Clean (SW50R). AC20 is stable.
- **Measured, not heard:** fixed-level judge scores, with no listening test on clean
  presets yet.
