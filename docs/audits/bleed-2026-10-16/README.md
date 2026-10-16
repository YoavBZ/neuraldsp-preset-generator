# Bleed in the amp tracks (2026-10-16)

The question: how much other-instrument bleed is in each `reference.wav`, the amp track used as the
record? It covers all 59 label-table parts, which include the 25 knob-ceiling parts. No renders.

**Method.** Bleed is the held-out energy the other session tracks explain, after a model of the
part's own DI (with a mild nonlinearity) and above a shifted-track null. It is given in dB of the
amp track, per judge half.
- **Validated:** injected bleed at −25 dB reads −25 to −27 dB; at −35 dB it reads as none.
- **Floor:** about −30 dB.
- **Flags:**
  - low: under −30 dB;
  - moderate: −30 to −20 dB;
  - high: over −20 dB.

**Findings**
- **Cambridge overdubs are clean.** Their amp tracks are zero wherever the DI is silent.
- **Bleed is in the Telefunken live-room sessions only.**
- **Among the 25 knob-ceiling parts, four read high:**
  - Gym Hours GTR_1: −8.4 dB in half B, from GTR 2;
  - First Offering GTR_1: about −14 dB, from overheads and GTR 2;
  - Sculptor's Request GTR_1: −11 to −13 dB, from drum mics;
  - Long Way Home: −17 dB in half B, from cymbals.
- **Seven read moderate.**
- **Weak DI models (gtr ≤ 0.75) on several parts,** where the residual is amp behaviour, not bleed:
  It Was My Fault E1/E2, Today's The Day, femme, Prodigal E5, Get Out Of Bed, Long Way Home and
  Blind Spots.
- **Cross-check (descriptive, confounded with dataset):**
  - arm A gains about nothing on flagged halves (+0.007), against −0.086 on low halves;
  - K_S tracks the DI model's fit rather than bleed (ρ −0.37).
- **Prodigal E5 (listening trial 8) has no bleed and no clipping.** Its DI carries 60 Hz hum plus
  harmonics, and the measure-DI EQ lifts that floor about 10 dB. PR12's crunch then makes it audible
  in every render.

Files: `bleed4.py`, `aggregate.py`, `synth.py`, `bleed-table.json`, `crosscheck*.json` and the
Prodigal noise check.

## Robustness of the key results to bleed (zero renders)

Each result was recomputed:
- (a) with all units;
- (b) without high-bleed held halves;
- (c) without moderate or high ones;
- (d) on Cambridge only.

The scripts are `r123.py` and `r4.py`, with outputs in `r123.json`. Subset (a) reproduces every
headline exactly.

| Result | (a) | (b) | (c) | (d) |
|---|---|---|---|---|
| K_S against S | −0.269 | −0.269 | −0.267 | −0.274 |
| Arm A against S | −0.078 [−0.157, +0.002] | −0.082 | **−0.097 [−0.184, −0.011]** | −0.091 |
| 3-C′ shrunk halfway against S | −0.083 | −0.085 | −0.094 | −0.098 |
| B2 − B0 on songs (paired) | −0.068 | −0.065 | −0.070 | −0.065 |
| Local objective: matched − current | +0.252 | +0.227 | +0.253 | +0.273 |

- **Every key result holds.** Nothing moves more than about 0.03 against it.
- **Bleed diluted arm A's gain a little:** without bleed it grows by about 25%, and its interval
  excludes zero.
- **On records with neither bleed nor a weak DI model:** arm A −0.128 and K_S −0.315, from 9 parts
  and 7 bands, so with wide intervals.
