# Kill tests K1–K3: results (SW50R, float panel, 2026-10-04)

Declared in `docs/supervised-model-plan.md` §0 (K1, K2) and `docs/kill-test-k3-plan.md`
(K3, its amendment, and "Under the judge"). Computed by `scripts/kill_tests.py` and
`scripts/kill_test_k3.py` at 026ceed (identical to 1f67812, where they ran) on the
float panel (1,978 renders, 44 factory presets plus the template with and without its
time effects, through 43 development parts' DIs), then by `scripts/kill_tests_judge.py`
at 7f98fca; later commits change only import order, path expansion and guards that do
not fire on this run. Two independent reviews re-scored the numbers from the renders;
the second corrected several labels and figures, which this version carries.

Counts of parts "better than" a comparator count a tie as half where marked (half);
the declaration counts a tie as half only against the shuffled control.

## Verdict

**As declared, the gate does not open.** K1 and K2 pass; K3 passes for 1-NN under ALM
and the judge's default bands, but under the judge's union bands 1-NN is closer than
the constant on 15 of 30 parts, with one tie, and the declaration asks for "closer
than that constant on a majority of parts". 15 of 30 is not a majority, and the
declaration's outcome table makes any such outcome "not passed".

The code, written before the results, counts that tie as half (15.5 of 30) and
reports a pass, so `gate_open` is true in the output. That reading is not the
declared text, and it is not adopted here after the fact. Leaving the tie out gives
15 of 29, a pass. Whether to proceed to the model POC on this evidence is a decision
for the user, not something this result settles; the case for and against is below.

| Test | Reading | Result | Detail |
|---|---|---|---|
| K1 headroom | ALM | pass | oracle 31% closer than template+R; 26 of 27 parts, 9 of 9 bands |
| | judge, default bands | pass | 32% |
| | judge, union bands | pass | 28%; leaving out one band, the worst is 25.2% against the 25% line |
| K2 across players | as declared | pass | top-1 58% for LDA (chance 2.3%); closed set only (below) |
| K3 real amp tracks | ALM | pass (1-NN) | 27% band median; better than template+R on 18 of 30 parts, than the shuffled control on 24, than the constant on 20 (20.5 half) |
| | judge, default bands | pass (1-NN) | 28%; 18, 23, 21 (21.5 half) |
| | judge, union bands | fail as declared | 27%; 16, 24 — and 15 better, 1 tied, 14 worse against the constant (15.5 if the tie counts half) |
| | LDA, LDA+1-NN | fail | LDA 12–20% worse than template+R; LDA+1-NN from 2% better to 6% worse |
| As first declared (ALM and v3c) | | pass | K1 under v3c 36%; K3 1-NN under v3c 13%, 22 of 30 parts, beats the shuffled control on 25 and the constant on 22 (23 half) |

Under v3c the constant chosen on the training bands (band median 18%) does better
than 1-NN (13%); v3c is retired as a judge (`docs/measuring-closeness.md`) and this
verdict is reported, not deciding.

The tie is Fragments, where the 1-NN pick and the union constant are the same preset.

## What holds up

- **The renders are the corrected ones.** All are float, written before the panel's
  index; 156 peak above 0 dBFS (nine presets, up to +12.4 dBFS on Mustang); the six
  formerly pitch-shifted presets now sit at 0 semitones. K1's ALM figure equals the
  earlier, 24-bit run's to four decimals by a coincidence of the median: every row
  differs, and five oracle picks moved to formerly clipped or shifted presets.
- **The picks are part-specific.** 1-NN makes 15 distinct picks, the most common on
  13% of parts. Given each part another band's pick, the gain is about zero; the
  shuffled control is beaten on 23–24 of 30 parts (band p about 0.006 one-sided). With
  the picks permuted across parts, 0.1–0.2% of 2,000 permutations pass the whole rule
  as coded (half ties); counting ties as losses, none of 2,000 does.
- **Lags do not matter here.** At the other cluster's lag, Signs 3 and Strangest
  Places keep the same oracle presets and move by at most 0.007 in log ratio.
- **Gating the amp-track features by the part's DI** is not a material leak: without
  it 28 of 30 picks are unchanged (but see the margin below).

## What does not

- **The K3 margin.** Even under the code's half-tie count, the union reading is a single
  part from failing: removing any one of 15 parts, or any one of 7 of the 11 bands,
  makes it fail; two of those pivotal parts (Honey, She's Gone) are pause-heavy, where
  `docs/measuring-closeness.md` says rankings lean on pauses. Gating the features
  without the DI changes 2 of 30 picks and takes that count to 14.5 of 30.
- **The headline overstates the typical part.** The 27% is a median over band
  medians, where four one- or two-part Cambridge bands weigh as much as the eight-part
  Dom McLennon band. Per part, the median gain is 17% (ALM), 10% (judge default), 6%
  (judge union). Cambridge (14 parts): 11–12 better than template+R. Telefunken (16
  parts): 5–7 better, median part no gain; under the union bands only 4 of 16 beat the
  constant. K1 shows a similar but not clean split: under the judge the Telefunken
  bands have 0–22% headroom, but under ALM Dom McLennon (Telefunken) has 28%, and the
  Cambridge band Starnes And Shah has 8.6% under ALM and about 10% under the judge.
- **The recogniser that is among the best on renders is the worst on real tracks**
  under ALM and the judge.
  LDA ties LDA+1-NN for K2's best closed-set top-1 (58%) on renders and is 12–20%
  worse than template+R on real amp tracks under ALM and the judge (12.6% better
  under the retired v3c). The plan chooses the POC's models and settings on
  simulation only; this says that choice can pick the wrong model.
- **Statistics.** Band-level sign-flip p against template+R is 0.036 (ALM), 0.052
  (judge default) and 0.059 (judge union) one-sided, so ALM meets the plan's P2 bar
  (one-sided p < 0.05) and the judge narrowly misses it; against the constant
  0.046–0.11 one-sided.
- **The three readings are nearly one.** ALM and the judge's two band sets correlate
  at Spearman 0.95–0.99 over every part × preset log ratio; requiring all three adds
  fragility, not independent confirmation. Both are unvalidated by listening.
- **The comparator matters.** A training-band constant chosen by median log ratio
  rather than median raw distance is beaten on 21–22 of 30 parts; the best single
  preset chosen in hindsight on the test parts (14–19% band median) is beaten on only
  12–14 (14–15 with ties counted half).
- **K2 is closed-set.** With each preset held out of training (what real tracks
  require), mean regret is 0.80–0.86 of the medoid constant's, short of the 0.75 the
  closed-set rule used; the recognisers recover 23–35% of the gap to the best
  available preset. (The medoid's mean leaves out renders whose true preset is the
  medoid; the recognisers' means keep them, so the ratio is over slightly different
  sets.)
- **Narrow conditions.** Isolated amp tracks only, scored through the part's own DI
  and against the same microphone; no mixes, stems, other players' DIs or second
  microphones.

## What follows

The declared outcome is "not passed". Proceeding anyway would be a judgement call
resting on: K1's large headroom under every measure; 1-NN's part-specific gain under
ALM and the judge's default bands, with ALM's band p below 0.05; and the strict union
reading failing by a single tie on one part. Against it: the gain sits in one source,
the per-part gain is modest, the judge's union reading fails, the measures are nearly
one, and the recogniser that wins on renders loses on real tracks.

If the user decides to proceed, these conditions apply to the model POC
(`docs/supervised-model-plan.md` §0):

1. No POC result is read until stage 0b has validated a measure.
2. The K3 1-NN lookup and a constant chosen by median log ratio are required
   comparators in P1 and P2, and the model chosen on simulation is checked on real
   amp tracks before any scale-up.
3. P1 and P2 report part medians and per-source (Cambridge, Telefunken) gains beside
   band medians; P2 adds another player's DI and the second microphone.
4. The POC stays at its cut-down size until P2 passes.

Stage 0b (validating the measures by listening) is worth doing either way: every
conclusion here and in `docs/measuring-closeness.md` waits on it.

Outputs: `~/ndsp-presets/runs/kill/k-sw50r-run2.json`, `k3-sw50r-run2.json`,
`k-judge-run2.json` (local; not committed).
