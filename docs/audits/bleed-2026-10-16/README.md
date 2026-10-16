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
