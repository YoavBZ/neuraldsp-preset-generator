# The direct model with realistic stems: gate 1 results (2026-10-20)

Run under the [plan](direct-model-stems-plan.md) (steps 1a and 1b). These are the zero-render checks
only. There was no training, no training-set build, no render, and step 1d was not run (it is not
part of the gate). Development data only.
- **Code:** `learn/direct_stems.py`, tests `tests/test_direct_stems.py`. One independent code
  review came before any model was run: go with fixes. They are applied, and the plan's
  clarification was written before `move` ran.
- **Data:** `~/ndsp-presets/learn/direct-stems/gate1/` (`move.json`, `move-directions.json`,
  `reliance.json`, `reliance-per-example.json`, `stems/`, `logs/`).
- **Compute:** 349 separations on the CPU at nice 19:
  - htdemucs on 164 audit mixes, 612 s;
  - Mega-53 fast on 164 audit mixes and 21 stage F crops, 1,524 s.

  Model inference ran at 4 threads (`move`, `reliance`, and the post-hoc `audit-mix`).
  **Renders: 0.**
- **Checks passed:**
  - The stored D_existing run is reproduced on stem b: every seed and component choice is the
    same, and the pooled weights match within 1e-4.
  - The model hashes match.
  - mix − reference equals `backing.wav` within 1e-4 on all 21 parts.
  - The rebuilt audit training stems match the stored features: at least 99% of cells fall
    within one 0.5-dB step.

## Headline

- **Stem quality moves the answers a lot. Gate 1 reads `GATE1 STEM`, so the separator route
  continues.** All three declared conditions hold, on all bands and on the unseen bands, and under
  both LUFS conventions:
  - **Stage F.** Swapping the training-style stem a′ for htdemucs's moves each seed's answer by
    **0.104 [0.090, 0.120]** of the unit scale more than two leak draws do. The null itself is
    0.017.
  - **Audit examples.** On the 164 audit examples, Mega-53's stem raises the knob error E from
    0.167 to 0.270, a cost of **+0.104 [+0.088, +0.120]** (6 bands). That is about 60% more error,
    and 15 times part C's 10k → 20k step. The cost is in-sample; the step was a held-out gain.
- **The model leans on the stem. Behind a clean or a real separated stem, the mix adds little or
  nothing measurable.** On V_dev:
  - zeroing the stem costs +0.099 of E;
  - zeroing the mix costs +0.043, so the stem carries 0.70 of the reliance;
  - shuffling reads the same way: stem +0.071, mix +0.036.
  - **With the clean guitar as the stem, removing the mix costs little:** +0.011 [+0.005,
    +0.016], about 6% of E, and that is with zeroing, which lies outside the model's training.
  - Shuffling the mix behind a clean guitar costs +0.003 [+0.001, +0.005].
  - The clean guitar alone beats the stored training stem (−0.013 [−0.021, −0.005]).
  - **Behind a real separated stem the mix is worth nothing measurable** (the audit examples,
    zeroing the mix): Mega-53 +0.001 [−0.009, +0.010], htdemucs +0.005 [−0.004, +0.014]. Behind
    the training stem it is worth +0.057 [+0.045, +0.070].
  - The mix's larger weight behind the training stem fits it being used to cancel that stem's
    leak, an exact copy of the backing. This was not tested directly; a clean stem making the mix
    redundant reads the same.
  - These clean-stem and real-stem rows are post hoc.

  This fits the user's design: a clean, correctly chosen target guitar, and as little else as
  possible.
- **Recommendation: drop the mix input.** Train the next model on the separated target stem alone,
  as a stem-only pilot arm in place of the stem-plus-mix arm. Treat a mix-only model as a cheap
  comparison arm at most, not a route.
  - The evidence is from one model trained with a mix. A model trained on real stems could find a
    use for the mix behind drop-outs and merged guitars.
  - On stage F, zeroing the mix behind htdemucs's stem still moves the answers by 0.092, 5 times
    the null. That is movement, not error; the labelled audit rows show no cost.
  - This changes the pilot's arms, so it is the user's decision. The plan is not amended here.

## 1a. Stem-swap movement on stage F (126 directions, 21 parts, 12 bands)

**How the readings are made:**
- Per seed, the movement is the mean |Δ| of the top-component means over the amp's labelled
  continuous settings, then averaged over the three seeds.
- Rows are band-weighted (part means, then band means), with 90% band-bootstrap intervals (4,000
  draws, seed 20261078).
- The decision reads each stem's own LUFS. The held-LUFS reading agrees to within 0.003 everywhere.

| Movement above the two-leak-draw null | All, 12 bands | Unseen by part C, 6 | Without MUSDB18 songs, 9 |
|---|---|---|---|
| **d(a′, b) − null (gate)** | **+0.104 [+0.090, +0.120]** | **+0.106 [+0.079, +0.137]** | +0.101 [+0.084, +0.122] |
| **d(a, b) − null (gate)** | **+0.114 [+0.103, +0.128]** | **+0.123 [+0.104, +0.147]** | +0.111 [+0.098, +0.130] |
| d(a′, c) − null (Mega-53, as stored) | +0.105 [+0.096, +0.114] | +0.101 [+0.092, +0.110] | +0.110 [+0.100, +0.119] |
| d(a′, c_f) − null (Mega-53 fast) | +0.108 [+0.099, +0.117] | +0.103 [+0.089, +0.114] | +0.111 [+0.100, +0.121] |
| Likelihood shift Δℓ(a′, b) − null (nats per setting) | +0.206 [+0.147, +0.277] | +0.163 [+0.132, +0.197] | +0.222 [+0.155, +0.314] |

**Movement levels** (band-weighted; the switch and mic columns give the share that agree):

| Pair | Move | Switches agree | Mics agree |
|---|---|---|---|
| null: a′ against another leak draw | 0.017 | 0.96 | 0.89 |
| a′ (training-style) against b (htdemucs) | 0.121 | 0.67 | 0.29 |
| a′ against c (Mega-53) | 0.122 | 0.67 | 0.24 |
| a (amp track) against a′ | 0.073 | 0.77 | 0.55 |
| b against c (htdemucs against Mega-53) | 0.129 | 0.70 | 0.37 |
| c against c_f (Mega-53 stored against fast) | 0.029 | 0.87 | 0.81 |
| b against z (stem zeroed) | 0.140 | 0.60 | 0.16 |

**What this means:**
- A real separated stem moves the answer most of the way to where **deleting the stem** takes it
  (0.121 against 0.140), and seven times as far as the leak draws the model was trained to ignore.
- Mic choices on real stems are close to arbitrary: they agree with the training-style stem's
  23–29% of the time, against 15–16% with no stem and 89% for the null. Switches agree 67% of the
  time (null 96%).
- **Mega-53's stems sit at the quantisation floor in 23–24% of cells.** The training stems and
  htdemucs's sit there in about 0%, and the amp track in 2%. Mega-53 writes near-silence where it hears no guitar, which the
  model never saw in training. Any stem-trained model needs that in its training data, and the
  plan's real-stem build supplies it.

## 1a. The labelled cost on the 164 non-stage-F audit examples (6 bands)

Every condition uses the same true mix (the stored gains, sample domain), and E is averaged over
the seeds. These are D_existing's training examples, so E is in-sample. The interval is the
band-clustered t with 5 df, which the clarification made the deciding interval. The bootstrap is
reported beside it.

| Stem | E | Against (i), the training stem |
|---|---|---|
| (i) training stem (leak, as trained) | 0.167 | — |
| (ii) guitar alone | 0.170 | +0.003 [−0.006, +0.013] |
| **(iii) Mega-53 fast of the true mix (gate)** | **0.270** | **+0.104 [+0.088, +0.120]** (bootstrap [+0.089, +0.114]) |
| (iv) htdemucs of the true mix | 0.259 | +0.092 [+0.083, +0.101] |

Mega-53 − htdemucs for this model is +0.012 [−0.003, +0.026], a tie. This model was trained on
neither separator.

## 1b. Reliance on the mix against the stem

**V_dev** (part C's 1,720 val examples of 5 bands not in stage F; stored features). ΔE is measured
against the stored inputs (E 0.189), paired, with a band-clustered t interval (4 df). Shuffles are
within amp × base class, never within the same section (seed 20261079, set in the code; the plan
gave none).

| Condition | ΔE |
|---|---|
| Stem zeroed | +0.099 [+0.072, +0.126] |
| Stem shuffled | +0.071 [+0.043, +0.099] |
| **Mix zeroed** | **+0.043 [+0.026, +0.059]** |
| **Mix shuffled** | **+0.036 [+0.022, +0.049]** |
| Both zeroed | +0.079 [+0.054, +0.104] |
| Stem := mix | +0.060 [+0.040, +0.081] |
| Stem := guitar alone | −0.013 [−0.021, −0.005] |
| Guitar alone, mix zeroed (post hoc) | −0.003 [−0.015, +0.010] |
| Guitar alone, mix shuffled (post hoc) | −0.011 [−0.019, −0.002] |

- **The stem's share** of the reliance is 0.70 when zeroing and 0.67 when shuffling.
- Zeroing both channels (+0.079) costs less than zeroing the stem alone (+0.099). With the stem
  gone, the mix pushes the answer the wrong way.
- **With a clean stem, the mix adds little. This is post hoc, added after the declared rows.**

| Contrast (V_dev) | ΔE |
|---|---|
| Guitar, mix zeroed − guitar with mix | +0.011 [+0.005, +0.016] |
| Guitar, mix shuffled − guitar with mix | +0.003 [+0.001, +0.005] |

  The model was trained with the mix present, so zeroing it is outside its training. Even so, a
  clean stem leaves the mix worth about 1–6% of E, against 23% behind the training stem. Its main
  role was to cancel the stand-in stem's leak, which is an exact copy of the mix's own backing.

**The audit examples, mix zeroed behind each stem** (post hoc, the audit's suggestion; `audit-mix`,
`audit-mix.json`; 164 examples, 6 bands, own stem LUFS):

| Stem | E with mix | E mix zeroed | Mix zeroed − with mix |
|---|---|---|---|
| (i) training stem | 0.167 | 0.224 | +0.057 [+0.045, +0.070] |
| (ii) guitar alone | 0.170 | 0.179 | +0.009 [+0.006, +0.012] |
| (iii) Mega-53 fast | 0.270 | 0.271 | +0.001 [−0.009, +0.010] |
| (iv) htdemucs | 0.259 | 0.264 | +0.005 [−0.004, +0.014] |

Zeroing lies outside the model's training in every row, including the training-stem row.

`reliance` ran three times: the later runs added the post-hoc rows and saved per-example E. The
declared rows were identical in all three runs.

**Stage F** (unlabelled, per-seed movement; null 0.017):

| Input changed | Movement |
|---|---|
| Stem zeroed | 0.140 |
| Stem shuffled across bands | 0.151 |
| Mix zeroed | 0.092 |
| Mix shuffled across bands | 0.063 |

Shuffling the mix moves the answer less than half as far as shuffling the stem.

## The gate, and what follows

**Declared decision: `GATE1 STEM`.** All five checks hold: d(a′, b) and d(a, b) on all bands and on
the unseen bands, and the audit cost. The reading is the same with the held LUFS. The separator
route continues, and the mix-only route is not adopted as a route.

**What the results say for the design, given the user's guidance of 2026-10-19:**
- **Feed the model a clean, correctly chosen target guitar, and nothing else.** On the existing
  model, the mix earns most of its place only when the stem is the training stand-in, whose leak
  it can cancel (+0.043 of E on V_dev, +0.057 on the audit examples). Behind a clean stem it is
  worth +0.003 to +0.011, and behind Mega-53's or htdemucs's stem nothing measurable.
- **Recommended:** train the next model on the separated target stem alone: Mega-53 now, the
  fine-tuned or one-guitar separator later. Training stems should be real separator output, so
  that drop-outs, floor cells and merged guitars are seen in training.
- **The mix-only arm (D_mix) stays a cheap comparison at most,** not a route.
- Replacing the pilot's D_sep (stem plus mix) with a stem-only arm is a plan change, so the user
  decides.

**Caveats:**
- **One model.** D_existing was trained with a mix channel and a leak stem. A model trained
  without the mix could use the stem differently, and one trained on real stems could find a use
  for the mix behind drop-outs and merged guitars. The pilot can measure this with a stem-only arm
  beside the stem-plus-mix arm.
- **The clean-target and real-stem mix rows are post hoc** (labelled as such).
- **Audit E is in-sample.** V_dev E is in-domain (training-style mixes), not real songs.
- **Stage F has no labels,** so movement says the answers change, not that they get worse. The
  audit cost supplies the labelled direction.
- **a′ is a waveform sum with measured LUFS.** Part C mixed in the mel-power domain and took its
  conditioning from power-summed stored loudness values. The leak-draw null (0.017) suggests the
  difference is small.
- **c_f is Mega-53's fast setting.** 1c, which would choose the training setting, was not run.
  c_f and c differ by 0.029.
- **Disk:** about 0.7 GB written; 29 GB was free at the start, below the build's 31 GB guard. The
  build stays blocked on disk, as the plan says.

## Audit

One fresh-context auditor checked every number against the JSON and the logs: **confirmed with
corrections, all applied.**
- The held-LUFS agreement is within 0.003, and the mic agreement range is 23–29%.
- "Close to arbitrary" is now said only for mics, and the reading that the mix cancels the leak is
  marked as an inference.
- The recommendation is hedged: it holds for one model, and the stage F mix movement is stated.
- The 15× figure is labelled in-sample.
- On the auditor's suggestion, the audit examples were rerun with the mix zeroed behind each stem
  (zero renders, post hoc). The mix is worth nothing measurable behind a real separated stem.

Before any model ran, the code review found no bug that would change the numbers. It asked for
three things, all done: declare the deciding LUFS convention and interval (in the plan,
2026-10-19), take the label mask by gain class, and label c_f as fast.
