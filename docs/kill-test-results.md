# Kill tests K1–K3: results (SW50R, float panel, 2026-10-04)

Declared in `docs/supervised-model-plan.md` §0 (K1, K2) and `docs/kill-test-k3-plan.md`
(K3, its amendment, and "Under the judge"). Computed by `scripts/kill_tests.py` and
`scripts/kill_test_k3.py` at 1f67812 on the float panel (1,978 renders, 44 factory
presets plus the template with and without its time effects, through 43 development
parts' DIs), then by `scripts/kill_tests_judge.py` at 7f98fca. An independent review
re-scored every number from the renders and reproduced them exactly.

## Verdict

As coded before the results, all three pass and the gate opens. Read strictly, K3
passes on its weakest reading only because of a tie. The evidence supports "a
render-trained preset lookup is not killed"; it does not support "a supervised model
will work".

| Test | Reading | Result | Detail |
|---|---|---|---|
| K1 headroom | ALM | pass | oracle 31% closer than template+R; 26 of 27 parts, 9 of 9 bands |
| | judge, default bands | pass | 32% |
| | judge, union bands | pass | 28%; leaving out one band, the worst is 25.2% against the 25% line |
| K2 across players | as declared | pass | top-1 58% for LDA (chance 2.3%); closed set only (below) |
| K3 real amp tracks | ALM | pass (1-NN) | 27% band median; better than template+R on 18 of 30 parts, than the shuffled control on 24, than the constant on 20.5 |
| | judge, default bands | pass (1-NN) | 28%; 18, 23, 21.5 |
| | judge, union bands | pass (1-NN), by a tie | 27%; 16, 24, 15.5 — 15 better, 1 tied, 14 worse against the constant |
| | LDA, LDA+1-NN | fail | 12–20% worse than template+R (LDA) or level with it |

The tie is Fragments, where the 1-NN pick and the constant are the same preset. The
declared text says ties count half for the shuffled control and "closer on a majority"
for the constant; the code, written before the results, counts ties as half for both.
Counted that way it passes (15.5 of 30); counted as a loss it fails (15 of 30); left out
it passes (15 of 29). This document records the pass as coded and that it rests on
this reading.

## What holds up

- **The renders are the corrected ones.** All are float, written before the panel's
  index; 156 peak above 0 dBFS (nine presets, up to +12.4 dBFS on Mustang); the six
  formerly pitch-shifted presets now sit at 0 semitones. K1's ALM figure equals the
  earlier, 24-bit run's to four decimals by a coincidence of the median: every row
  differs, and five oracle picks moved to formerly clipped or shifted presets.
- **The picks are part-specific.** 1-NN makes 15 distinct picks, the most common on
  13% of parts. Given each part another band's pick, the gain is about zero; the
  shuffled control is beaten on 23–24 of 30 parts (band p about 0.012). With the picks
  permuted across parts, 0.2% of 2,000 permutations pass the whole rule.
- **Lags do not matter here.** At the other cluster's lag, Signs 3 and Strangest
  Places keep the same oracle presets and move by at most 0.007 in log ratio.
- **Gating the amp-track features by the part's DI** is not a material leak: without
  it 28 of 30 picks are unchanged (but see the margin below).

## What does not

- **The K3 margin.** Under the union bands, removing any one of 15 parts, or any one of
  7 of the 11 bands, makes K3 fail; two of those pivotal parts (Honey, She's Gone) are
  pause-heavy, where `docs/measuring-closeness.md` says rankings lean on pauses.
  Gating the features without the DI changes 2 of 30 picks and flips that reading to
  a fail (14.5 of 30).
- **The headline overstates the typical part.** The 27% is a median over band
  medians, where five one- or two-part Cambridge bands weigh as much as the eight-part
  Dom McLennon band. Per part, the median gain is 17% (ALM), 10% (judge default), 6%
  (judge union). Cambridge (14 parts): 11–12 better than template+R. Telefunken (16
  parts): 5–7 better, median part no gain; under the union bands only 4 of 16 beat the
  constant. K1 shows the same split: Telefunken bands have 0–22% headroom.
- **The recogniser that is best on renders is worst on real tracks.** LDA leads K2 on
  renders (closed and open set) and is 12–20% worse than template+R on real amp
  tracks under every measure. The plan chooses the POC's models and settings on
  simulation only; this says that choice can pick the wrong model.
- **Statistics.** Band-level sign-flip p against template+R is 0.07–0.12 (two-sided),
  short of the plan's P2 bar (one-sided p < 0.05); against the constant 0.09–0.23.
- **The three readings are nearly one.** ALM and the judge's two band sets correlate
  at Spearman 0.95–0.99 over every part × preset log ratio; requiring all three adds
  fragility, not independent confirmation. Both are unvalidated by listening.
- **The comparator matters.** A training-band constant chosen by median log ratio
  rather than median raw distance is beaten on 21–22 of 30 parts; the best single
  preset chosen in hindsight on the test parts (14–19% band median) is beaten on only
  12–14.
- **K2 is closed-set.** With each preset held out of training (what real tracks
  require), mean regret is 0.80–0.86 of the medoid constant's, short of the 0.75 the
  closed-set rule used; the recognisers recover 23–35% of the gap to the best
  available preset.
- **Narrow conditions.** Isolated amp tracks only, scored through the part's own DI
  and against the same microphone; no mixes, stems, other players' DIs or second
  microphones.

## What follows

The gate is treated as "not killed", with these conditions on the model POC
(`docs/supervised-model-plan.md` §0):

1. No POC result is read until stage 0b has validated a measure. If only the judge
   validates, K3 hangs on its union reading, whose tie rule is fixed here: ties count
   half, as coded.
2. The K3 1-NN lookup and a constant chosen by median log ratio are required
   comparators in P1 and P2, and the model chosen on simulation is checked on real
   amp tracks before any scale-up.
3. P1 and P2 report part medians and per-source (Cambridge, Telefunken) gains beside
   band medians; P2 adds another player's DI and the second microphone.
4. The POC stays at its cut-down size until P2 passes.

Outputs: `~/ndsp-presets/runs/kill/k-sw50r-run2.json`, `k3-sw50r-run2.json`,
`k-judge-run2.json` (local; not committed).
