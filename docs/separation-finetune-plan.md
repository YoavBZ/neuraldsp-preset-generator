# Better target-guitar separation: plan

Declared 2026-10-19, before any measurement on stage F with a new separator. Development only;
ledger entry `separation-finetune`. Estimates with intervals; the decisions below are fixed now,
before results exist. One zero-data probe (MPS, below) ran while drafting. One independent review
(go with changes; all required changes applied, [below](#review)).

> **Status (user, 2026-10-20): no separator training of any kind, and no rented machines.** Step 2
> (option A1, the class fine-tune) and any trained form of route B are cancelled. Step 1's two
> readings decide only A1 (YG − M) and whether a route-B plan goes to the user (YT − YG), so it
> has no decision left and does not run unless the ML session gives it a new one. Step 0's
> zero-training measures and fixes (Wiener, blend, ensemble) stay open, and so does Step 3 for a
> Step 0 fix that meets its rule. Released checkpoints (route B's CPU screen included) and DSP
> splits of their output stay open. The ledger entry and the other steps are for the ML session.

## The short version

- **Why now.** Perfect separation is worth −0.066 [−0.090, −0.042] to arm A over htdemucs on stage
  F (YT − H, [amendment 3](arm-a-mega53-results.md#amendment-3-perfect-separation-on-stage-f-2026-10-19)).
  Mega-53 gets about a quarter of that (M − H −0.017). What is left, YT − M ≈ −0.049, is the prize.
- **What probably limits Mega-53 is the other guitars, not its training domain.** On sets 1–3's
  instrumental contexts, Mega-53's stem reached about 10 dB SNR on the 7 single-guitar parts, against
  1.45 dB on multi-guitar parts ([separator upgrade](separator-upgrade-results.md)). The reason is
  that its "electric guitar" stem holds every electric guitar. In 19 of stage F's 21 parts the
  session has another electric guitar. The user heard one in both separations of Signs ElecGtr3
  and get-out-of-bed elecgtr2.
- **So fine-tuning Mega-53's head, as first proposed, may buy little.** Trained unconditioned, "one
  guitar is the target, everything else is the mix" is ill-posed when two guitars play at once:
  the network can't know which one is wanted, so it learns the sum or a blur. Made well-posed
  (target = all electric guitars), it can at best reach the class ceiling: the sum of the electric
  guitars, which still contains the other guitars.
- **Recommendation: measure the ceilings before building anything.**
  - **Step 0** costs zero renders, no training and about an hour of CPU. It measures how much of
    the gap the other guitars cause and tries four free test-time fixes.
  - **Step 1** (about 7k renders, about an hour) prices a perfect class separator in arm A terms.
    That one number decides the route:
    - **the class fine-tune** (Steps 2–3) is built only if a perfect class stem is worth at least
      what the 21-part test can detect;
    - **otherwise the lever is a *conditioned* separator,** which is told which guitar: its gain
      class, its pan side by ear, or an exposed passage. That needs data, disk and product
      decisions from the user, so it is route B, with its own plan.
- **Budget if everything runs:** about 14k renders, at most 12 MPS hours, under 0.5 GB of disk,
  about 4 working days, one executor and one independent auditor per decision step.
  **Earliest stop:** Step 0's R0a, half a day, zero renders.

## What we know, and what it implies

| Finding | Source | Implication |
|---|---|---|
| Perfect separation: YT − H −0.066 [−0.090, −0.042], 11/12 bands; YT − S −0.094 | amendment 3 | Separation is worth pursuing. About −0.049 is left over Mega-53 (YT − M, a difference of point estimates; Step 0 adds its interval) |
| Mega-53 vs htdemucs on stage F: M − H −0.017 [−0.039, +0.004] (a tie) for about +1.0 dB mono SNR (1.67 against 0.69 dB) | arm A Mega-53, stereo check | A crude slope of −0.017 per dB, read from a tie. A 21-part arm A test resolves about −0.03 (below), so a new stem probably needs about +2 dB over Mega-53 before a stand-alone render test can see it |
| Sets 1–3 instrumental contexts: single-guitar parts (7) Mega-53 9.96 dB, multi-guitar 1.45 dB; on multi-guitar parts every separator gains only +0.3 to +0.4 dB over htdemucs | separator upgrade | The other guitars are probably the main residual; better class separation won't remove them |
| Stage F mixes are unity sums of raw tracks; every target is mono and centred | stereo check | Pan can't help on our data as recorded. Real mixes need augmentation to imitate them |
| Pan side, scenario P (target panned −0.6, other guitars ±0.6): own side +1.55 dB (oracle); blind guess at chance | stereo check | Pan is a real lever on panned songs, but only if someone (the user's ear) picks the side |
| Mega-53 is dark: −15 dB at 8 kHz, −36 dB at 12.7 kHz; peakier than the raw track; magilla loses 19 dB of brightness | separator upgrade, stereo check | A fine-tune could restore treble. LSD and brightness are must-not-regress checks beside SNR |
| No public source has fresh DI+amp pairs | multitrack research | Irrelevant here: **separation training needs no DI**, only multitracks with guitar amp tracks |

## Options, cost and expected value

| Option | What it is | Cost on this Mac | Expected value | Verdict |
|---|---|---|---|---|
| **A1. Class fine-tune** | Fine-tune Mega-53's electric-guitar head on our raw-sum multitracks; target = all electric guitars | ≈1 agent-day to build, ≤ 11 MPS h, < 0.3 GB | Capped by the class ceiling YG (Step 1). Likely gains on single-guitar parts and treble; little on multi-guitar parts | Only if Step 1 shows a perfect class stem is worth ≥ 0.032 |
| A2. One-guitar target, unconditioned (the literal proposal) | Target = one guitar's amp track, mix = everything else incl. other guitars | as A1 | Ill-posed when guitars overlap: it learns the sum or a blur. Restricted to windows where the target plays alone, it *is* A1 | Folded into A1 |
| **B. Conditioned target extraction** | A stage on top of the stem, or a conditioned head, told *which* guitar: gain class (known to the product), pan side (user's ear), or an exposed passage (user-marked). Variants: K permutation-invariant outputs with the pick made at test time; existing query-conditioned separators (Banquet, AudioSep; weights and licences unverified) | Own plan: 2–3 agent-days, 1–3 MPS days, external multitracks (tens of GB), licence and product decisions. Screening existing models on stored stage-F contexts costs CPU only | The only route aimed at the other-guitar residual, i.e. most of YT − M. In-scope multi-guitar data on disk is thin (below) | If Step 1 says the class route is too small, and YT − YG is large |
| C. Ensemble (Mega-53 + htdemucs or BS-Roformer) | Average or band-split the stems | Inference 1.3–2× Mega-53; MPS barely helps (below) | Small: both stems carry the same other guitars, and the earlier crossover blend did not advance ([screen](separator-screen-results.md)) | Tested free in Step 0 on the stored stems; BS-Roformer only if a blend gains |
| D. Wiener-style refinement | Re-mask the mix with the stem's power against the residual's | Minutes, on stored stems | Small (+0 to 0.5 dB typical). It may restore treble the network dropped, since the mask re-takes the mix's own spectrum | Tested free in Step 0 |
| E. Stereo, pan side by ear | Separate in stereo, keep the side the user names | Zero training; one question to the user | +1.55 dB on panned guitars (scenario P); 0 on our centred data | Product session's call (it asks the user); not testable on stage F as recorded |

**Why not start with the fine-tune.** It is the most expensive item on the list that still leaves
the main residual in place. Steps 0 and 1 tell us, for about an hour of CPU and an hour of renders,
whether the class route has room. The option most likely to pay (B) is also the most expensive and
needs user decisions. It should be justified by these numbers, not by a guess.

## Step 0: where the gap is, and the free fixes (zero renders, zero training)

Stage F's 21 parts, the 10-s crop inside the stored 30-s context, against `reference.wav`. No new
separation: the stored Mega-53 stems (`~/ndsp-presets/learn/arm-a-mega53/F/sep/mega53/`), the
stored htdemucs stems, and track sums built exactly as `learn/separate.context` builds the mix
(from each crop record's `included_mix_tracks`).

**Track table first.** Before any SNR is computed, a JSON lists every track, by name, as one of:
- target;
- the target's other mic (same guitar, e.g. `Mic2`, or `TF11` beside `M80`);
- a double-track of the target or of another guitar (`DT`);
- another electric guitar;
- rest.

It covers every stage-F part and every training session (Step 2). Ambiguous names go to rest:
`GTR KEYS AMP` is keys through an amp, and Eggy's `VOX GTR` is unclear. Each pre-recorded bounce
(`Pre Record Tracks.wav` in the John Morgan Kimock sessions, `GTR Pre Rec.L/R` in Renesans) is
listened to and either classed or dropped from both mix and target. The auditor checks the table
by name before any number exists. Bands come from the declarations' `band` and `group` fields,
never from folder names.

**Measures per part** (gain-fitted SNR as in `stereo_mix_check.snr_db`, plus SI-SDR, LSD and the
3–10 kHz brightness difference as in the stereo check):

| Name | Signal | What it says |
|---|---|---|
| M, H | stored stems vs target | the baselines (must reproduce the stored 1.67 / 0.69 dB) |
| **G** | sum of every electric-guitar track in the context (target, its mics and doubles included) vs target | **the class ceiling**, a perfect A1 separator; Step 1's stem |
| G_noDT | G without the other guitars' double-tracks | how much of G's loss is doubles, which may cost arm A little |
| G_mic | the target's own mic group vs target | the ceiling of any one-guitar separator against a one-mic reference |
| M vs G | stored Mega-53 vs G | how well Mega-53 does its own class job |
| I | other-electric-guitar energy over target energy in the crop, dB | how much the other guitars matter, per part |
| X | share of the part's 10-s session sections where the other electric guitars sit 10 dB or more below the target | whether an "exposed passage" query (route B) would exist |
| T1 | single-target Wiener: mask \|S\|²/(\|S\|²+\|X−S\|²) on the mix, STFT 2048/512 (S = Mega-53, X = mix) | test-time fix D |
| T2 | T1 with one more EM pass (powers re-estimated from T1) | test-time fix D |
| T3 | 0.5·Mega-53 + 0.5·htdemucs (each gain-fitted to the mix first) | ensemble C |
| T4 | `separator_screen.blend` (Mega-53 below the crossover, htdemucs above) | ensemble C, the treble route |

Band-weighted means with a 90% band bootstrap (4,000 draws, seed 20261019), band medians, part
means, and every part listed. **YT − M** is also computed, with its band-clustered interval, from
the stored arm records (zero renders).

**Readings (declared):**
- **R0a, class headroom:** the band median of SNR(G) − SNR(M), with its leave-one-band-out range.
  - **0 dB or below: stop the class route.** A perfect class stem isn't even cleaner than Mega-53's.
    Skip Steps 1–3 and bring route B to the user with the Step 0 numbers.
  - **Above 0 dB: Step 1.** (This is a sanity gate only. Whether the class route can pay is priced
    in arm A terms, not by an SNR slope read from a tie.)
- **R0b, free fixes.** The four T variants are compared with M on stage F in a declared order (T1,
  T2, T3, T4), with Holm's correction on one-sided band-bootstrap p-values (the share of draws
  with a gain ≤ 0) at 10%.
  - A variant that survives Holm and costs no more than 1 dB of LSD is a **post-process
    candidate**.
  - It goes **straight to the Step 3 render test** only under Step 3's own rule: a point estimate
    of +2 dB or more and a lower bound above +1 dB. If several variants qualify, the earliest in the
    declared order goes.
  - **Otherwise it is recorded as a gain to build on.** It is applied on top of a stem going
    forward only if the combination itself passes the Step 3 SNR gate.
- **R0c, descriptive:** I and X per part; Spearman of I against M − H and YT − M; G_noDT − G;
  G_mic − G; magilla's and Russian Cream's brightness.

## Step 1: price the class route in arm A (≤ 6,993 renders)

Runs unless R0a stops. Arm **YG**: stage F's H with the class-oracle stem G in both places a
product uses the stem (the search's target, and C′'s rebuild input), exactly as YT used the amp
track (`learn/perfect_sep_arm.py` with a third arm). The seed, recipe (52 renders, shrink 0.5,
fallback to S), judge and the 126 directions are H's. Renders: 63 priming + 126 × 55 = 6,993.

**Readings,** each band-weighted with a 90% band-clustered t interval (12 bands, 11 df), on the
fixed direction set where S, H, M, YT and YG all score:
- **YG − M decides A1:**
  - **point estimate −0.032 or lower, with its upper bound below 0: Step 2.** A perfect class
    stem is then worth at least what Step 3 can detect. A real fine-tune reaches only part of
    that, so Step 3 may still read a tie; this is the least that makes building worthwhile;
  - **otherwise, no fine-tune.** If YG − M is below 0, A1 could at most feed the combined
    fresh-song test of roadmap step 4. The user decides whether that is worth a day of building.
- **YT − YG prices route B:** what a perfect *one-guitar* separator adds over a perfect *class*
  separator. If it is −0.032 or lower with its upper bound below 0, a route-B plan goes to the
  user.
- The share (YG − M) / (YT − M) is reported with a Fieller 90% interval, descriptive (its
  denominator is small).

## Step 2: the class fine-tune (only if Step 1 says so)

**Model.** Mega-53 pruned to the electric-guitar head, as stored: 38.7 M parameters (trunk 25.3 M,
head 12.4 M). Train the mask estimator and the last 4 of the 12 trunk layers; freeze the rest.
- Optimiser: AdamW, learning rate 2e-5, 100-step warm-up then cosine, seed 0.
- Batch 1 × 6-s stereo at 44.1 kHz, gradient accumulation 2.
- Loss: the model's own (L1 waveform + multi-resolution STFT), with the iSTFT and the loss off the
  MPS device (the gate below).

**Examples, built on the fly from the session WAVs** (no cached audio, because of disk):
- **Target and mix.** The target is the sum of the window's electric-guitar tracks, per the track
  table. The mix is every track on a per-session mix list (vocals included, every DI excluded),
  declared in the track table.
- **Coherent and random.** Half are same-song windows (same chords, same rhythm). Half are random
  mixes: the guitars of one song over the rest of another, at ±6 dB gain.
- **Per-track variation.** Random EQ on each track (three peaking bands ±6 dB, one shelf) and a
  random pan per mono track, so the stereo model sees panned guitars.
- **Mix-bus processing,** in half the examples, done so that stems still sum to the mix:
  - one linear EQ on every stem;
  - a compressor's gain curve computed on the mix and applied to every stem;
  - loudness set to −14 to −8 LUFS.

  No clipping, because clipping can't be split per stem. The target is then the guitar *as it sits
  in the processed mix*.
- **Silence.** Windows where the target is under −40 dBFS RMS in more than half the frames are
  redrawn.
- **High-gain sessions** are extra class targets, for coverage of distorted guitars in rock
  mixes, capped at 25% of examples.

**Validation and stopping.**
- **Validation set.** Two whole in-scope bands, drawn by `random.Random(20261042)`: one from the
  four with three or more *distinct* electric guitars (Adam Buckley, Ale Lak, Starnes And Shah,
  The Long Wait), one from the other three (Eggy, John Morgan Kimock, Swatkins). 60 fixed windows,
  half with bus processing, at both 6 s and the model's own 10-s chunk.
- **Checks.** Every 250 steps: the band-mean SNR against the class target.
- **Steps.** The maximum is floor(11 MPS hours ÷ the step time the gate measures). The minimum is
  500 steps, or half the maximum if that is smaller. Training stops when validation hasn't
  improved by 0.1 dB for 1,000 steps.
- **Checkpoints.** Keep the best and the last, trainable parameters only, in fp16 (about 60 MB
  each).
- **Stage F is never used to choose anything.** One checkpoint, chosen on the validation bands, is
  separated on stage F once.

**The MPS gate (before training).** Measured today (below), the model's own forward pass and loss
on MPS give wrong gradients, so the gate runs first:
- **The test.** On 3-, 6- and 10-s chunks, against an all-CPU step: the loss within 1e-4
  relative, and gradient cosine ≥ 0.999 on head and trunk.
- **What it records.** Step time and peak memory at the real batch, which set the step maximum
  above. Peak memory must stay under 20 GB, with the swap guard on.
- **Fallbacks, in order, until one passes:**
  1. the iSTFT and the loss on the CPU;
  2. the loss computed on the masked spectrogram, before the iSTFT, on the CPU;
  3. training on the CPU with the same trainable set, with the step maximum recomputed (the probe
     measured about 3.4× slower per pass);
  4. stop and report.

## Step 3: the SNR gate, then the arm A decision test

**N** is the fine-tuned stem, or a Step 0 fix that met Step 3's rule. Stage F, the same crop and
measures as Step 0, against `reference.wav`.

**The gate,** on SNR(N) − SNR(M), band-weighted with a 90% band bootstrap. The rows are checked
in order and the first that applies holds:

| Condition | Outcome |
|---|---|
| Point estimate below +0.5 dB, or lower bound at or below 0 | **Stop.** No renders. Reported as the stem not moving |
| Point estimate +2 dB or more, and lower bound above +1 dB | **The arm A decision test** |
| Anything else | **Candidate.** No stand-alone render test, because 21 parts can't resolve it. N joins the next combined fresh-song test (roadmap step 4, with the improved rebuild). Recorded in the roadmap |

In every case N must not regress: its band-mean LSD may be at most 1 dB worse than M's, and
brightness is reported per part (magilla, Russian Cream).

**Why +2 dB.** On stage F, M − H's 90% half-width was 0.021 (SE ≈ 0.012). A paired N − M contrast
has about the same SE, so the smallest effect it detects at 90% with about 80% power is
2.7 × 0.012 ≈ 0.032. At M − H's −0.017 per +1 dB that is about +2 dB. That slope is crude: it is
read from a tie, the shape is unmeasured, and YT − M ≈ −0.049 caps it. **So the test can only see
a separator that captures about two thirds of perfect separation's remaining value.** Smaller real
gains are not failures; they are kept and built on. But a 7k-render test spent on them would read
a tie.

**The arm A decision test.** Arm N is H's recipe with N's stem in both places (C′ rebuilds the
search DI from N's stem, as M did). It runs on stage F's 126 directions (6,993 renders), paired
with the stored S, H, M, YT and YG on one fixed direction set.
- **Primary:** N − M, band-weighted, with a 90% band-clustered t interval (12 bands, 11 df).
- **Secondary:** N − YG, and the share (N − M) / (YT − M) with a Fieller 90% interval. Rows as in
  amendment 3: all, no high bleed, leave one band out, part-weighted, F-song.
- **Reading:**
  - **interval below 0:** N becomes the development default for arm A, and the separator in roadmap
    step 4's fresh-song test. It does not replace Mega-53 on this evidence alone, because the
    parts that selected N (its gate) also test it, on their 7th and 8th use;
  - **interval contains 0:** a tie. Mega-53 stays, and N stays a candidate if its estimate is below 0;
  - **interval above 0:** N is dropped.

## Route B, in outline (its own plan if chosen)

- **When:** R0a at or below 0, or Step 1 says no fine-tune and YT − YG is large.
- **What:** a stage that extracts one guitar, given a query the product can supply:
  - its gain class (clean or driven; `generate` already researches the tone);
  - its pan side, which the user picks by ear from three short clips;
  - a passage the user marks where it plays exposed. Step 0's X says how often one exists.
- **Cheapest first move:** screen existing query-conditioned separators, and permutation-invariant
  multi-instance ones, on the stored stage-F contexts, at CPU cost only. Their weights and licences
  must be checked first (open, non-commercial, unlicensed or gated is fine; unclear terms go to the
  user; beyond the Neural DSP plugin and Claude Code, nothing the product needs may cost other
  users money; ML plan §5).
- **Ceiling evidence:** the pan side is worth +1.55 dB in scenario P (stored). YT − YG, G_mic, I
  and X bound the rest.
- **Needs from the user:**
  - disk beyond the guard for external multitracks: Cambridge sessions without DIs, under the same
    educational licence as our current data, and MoisesDB (CC BY-NC-SA, allowed under the
    2026-10-20 licence rule);
  - the product session's agreement to ask the user a question.
- **Caveat:** on stage F every target is centred, so a pan query can only be scored in scenario P.

## Data

**Separation training needs no DI,** so every development multitrack counts. Only sessions already
on disk (sets 1–3) are used; nothing is downloaded. Bands come from the declarations: the `group`
field for sets 1–2, `band` for set 3.

| Use | Sessions (bands) | Why |
|---|---|---|
| **Train, in scope** (less the 2 validation bands) | Adam Buckley "Drag Me Down"; Ale Lak "Nosso Mundo"; Starnes And Shah "Prodigal"; Eggy ×3; John Morgan Kimock ×3 ("Hikikomori – Love Does", "New One", "Procession", the last with no electric-guitar target: its rest only); Swatkins ×3 (Honey, Lost & Alive, Until I Get Back); The Long Wait "Drag" | 13 sessions, 7 bands, about 60 min. Development; no stage-F, known-answer or proposed known-answer band; not held out. Four bands have three or more distinct electric guitars |
| **Train, high-gain, capped at 25% of examples** | Death Of A Romantic; Hollow Ground; Rebuild The Evil; Renesans ×3; Cnoc An Tursa; Storm Of Particles | 8 sessions, 6 bands, about 31 min. Their tones are out of scope; here they are extra class targets |
| **Validation** | 2 in-scope bands, a seeded draw (Step 2) | Early stopping and checkpoint choice only |
| **Test, never trained on** | Every session of stage F's 12 bands: Atlantis Bound, The Travelling Band, Zeno, Eat The Feeder, Diesel13, Wall Of Death, Magician's Nephew, Szymon Skiba, Turbosauro, Dom McLennon (all 4 songs), Bernard Purdie Tribute All-Stars, Doom Flamingo (all 4 songs) | Split by band, so no song, take or player of a test part is seen |
| **Never** | Known-answer songs and their bands: Rebecca Haviland ("Bourbon", "Collide With Me", "57 Chevy"), Chris Coltraine ("Heather Jane", "Memphis"), The Apprehended | Known-answer and held-out rules |
| **Never** | **Timo And The Timezone**: The Timezone "GOTGF" is a proposed B2 known-answer song, and the band becomes known-answer if it is the same band; part C also left it out | Known-answer rule |
| **Never** | Sets 1–2's held-out songs: Boogie Snakes, Forkupines ×2, Lights Off Clarity, The Maybe Next Years, Tim Taler, Briana Maia ×2, Catbite ×2, Wild & Co | Held-out rule |
| **Never** | Set 3's held-out bands: Crazy Swedes, Dunning Kruger (including "Sascha"), Scott Elliott, Silence Is Near, Silona, V.M.GY | Held-out rule |
| **Never** | Sets 4–6 and Guitar-TECHS P3 | Held-out rule |
| **Never** | The undeclared downloads Dark Ride and Umphrey's McGee | Not declared |

- **Leak checks, failing closed.** Every training session goes through:
  - `set3.is_held_out` (it raises on names it doesn't know);
  - `set4/5/6.covers`;
  - the sets 1–2 `split` field.

  Its band is also checked against stage F's 12 bands, the known-answer bands and Timo. A list of
  every file read is written next to the checkpoint.
- **Stage D.** Its stage-F bands are excluded. Its other bands, Adam Buckley, Starnes And Shah and
  Eggy, train (Timo does not). So stage D can't later serve as a separation check for N.
- **Multi-guitar targets.** In A1 the other electric guitars are part of the target, by
  definition. Against the one-guitar reference they count as interference, which is what Step 0's
  G, Step 1's YG and Step 3's gate measure. A route-B model would make them interference in
  training too.
- **Real mixes.** Our mixes are raw sums, so the bus augmentation stands in for mixing and
  mastering. When the user supplies real mix previews:
  - previews of our own sessions get a descriptive FIR-fitted SNR against the raw track, as in the
    stereo check's least-squares row;
  - any preview gets a listening check.

  Neither feeds this plan's decisions.
- **Thin data is a known limit.** After validation, 5 in-scope bands train, 3 of them with several
  electric guitars. That is enough for a partial fine-tune of a class head with heavy augmentation.
  It is not enough for route B.
- **Label noise.** Telefunken's live-room amp tracks carry drum bleed, and their overheads carry
  guitar. The target then includes a little drum, and the rest a little guitar.

## Budget

| Step | Renders | Compute | Disk | Wall clock | Agents |
|---|---|---|---|---|---|
| 0 | 0 | ≈1 h CPU (sums, Wiener, blends) | < 50 MB (JSON only) | ½ day with audit | executor + auditor |
| 1 (unless R0a stops) | 6,993 | C′ rebuild of G (CPU); about 1–1.5 h at 3 render processes (amendment 3's pace) | ≈ 60 MB | ½ day | + auditor |
| 2 (if YG − M ≤ −0.032, upper bound < 0) | 0 | MPS gate ≤ 1 h; training ≤ 11 MPS h (one run, one seed); stage F separation ≈ 35 min CPU | ≤ 0.3 GB (2 checkpoints, logs, N's stems) | 1 day to build + 1 night + ½ day | executor |
| 3 (if the gate says test) | 6,993 | C′ rebuild of N; about 1–1.5 h of renders | ≈ 60 MB | ½ day | + auditor |
| **Total if all run** | **≤ 13,986** | **≤ 12 MPS h** | **< 0.5 GB** | **about 4 working days** | **1 executor, ≤ 4 audits** |

- **Training steps are few.** A step is 12 s of audio: about 13 s on MPS from the probe's 3.3 s
  per 3-s pass, more with the loss on the CPU. So 11 hours allow roughly 3,000 steps, which the
  gate fixes from its measurement. This is a light fine-tune, not a retraining.
- **Disk is just above the guard.** 32.2 GB is free (decimal GB, as the guard measures), 1.2 GB
  above the 31 GB guard. Step 0's < 50 MB fits. **Before Step 1, ask the user to free about 2 GB**:
  the margin is thin, and other sessions write too (amendment 3's stop came from another session's
  test temp files).
- **Earliest cheap stop:** R0a, after Step 0. The next is Step 1's YG − M, after about an hour of
  renders, before anything is built.
- **Mac sharing,** as the roadmap's sharing rule says:
  - one MPS job at a time;
  - renders capped at 3 processes, grouped by amp;
  - Mega-53 on the CPU only when nothing is training, with its 11 GB memory gate.

## The MPS probe (run while drafting, synthetic noise, no data)

Run in `~/ndsp-presets/tools/msst-venv/bin/python` (torch 2.14) on this M1 Pro, one run each, so
the timings are rough.

- **Size:** the full model has 681.7 M parameters; the pruned electric-guitar head has 38.7 M
  (trunk transformers 25.3 M, head 12.4 M). An fp32 checkpoint is about 155 MB, and the trainable
  subset in fp16 is about 60 MB.
- **Inference works on MPS:** the output matches the CPU at 116 dB SNR on a 10-s chunk. But it is
  only about 1.2× faster (4.3 s against 5.2 s at the default threads).
  - So MPS doesn't rescue an ensemble's cost. Mega-53 stays at about 90 s per 30-s context on 4 CPU
    threads, and a second Roformer roughly doubles that.
- **Training does not work on MPS as-is.** One forward and backward pass on a 3-s stereo chunk
  (132,300 samples), with the model's own loss and all its weights trainable, took 11.2 s on the
  CPU and 3.3 s on MPS. But on MPS:
  - the loss differed (5.39 against 4.91);
  - the head's gradient had cosine 0.001 with the CPU's;
  - the trunk's gradient was NaN.

  This fits the known MPS STFT bug above 65,536 samples. The model's iSTFT output and its
  multi-resolution STFT loss both run on the device, and the gradients pass through both. Hence
  Step 2's gate and its fallbacks. A head-only pass was not measured.
- **Memory:** peak RSS was 14 GB, including loading the full checkpoint once. Peak memory at the
  real training batch is unmeasured; the gate measures it.

## Risks

- **The other guitars dominate** (the likeliest outcome). Then A1 can't pay. Step 0 and Step 1
  measure this before anything is built.
- **Overfitting to the Cambridge/Telefunken raw-sum style.** The test set has the same style, so a
  stage-F gain flatters what real mastered songs would see. Mitigations:
  - bus and EQ augmentation;
  - a partial fine-tune at a low learning rate;
  - early stopping on whole held-out bands;
  - the user's real previews as a later listening check.
- **Small data:** about 60 in-scope minutes over 5 training bands. Checkpoints are chosen on whole
  validation bands, never on stage F.
- **MPS:** wrong gradients, measured. The gate has declared fallbacks down to the CPU.
- **SNR may not predict arm A.** Mega-53's +1 dB read as a tie, and its darkness may cost the
  search. So LSD and brightness are must-not-regress checks, and only an arm A test (or the step-4
  fresh test) decides adoption.
- **Reuse of stage F:** these would be its 7th and 8th uses, so they give a development reading,
  not a fresh one. Selection happens on validation bands; the T variants carry Holm's correction.
  The step-7 held-out sets stay untouched.
- **Mic mismatch:** the reference is one mic, while the mix and any class stem hold both mics.
  G_mic shows how large this is.
- **Mega-53's training data is undocumented.** It may include some of our songs (several are
  MUSDB18). That affects the baseline M, not the split.
- **Licence:** Mega-53 comes from an MIT repo with no separate weights licence (as accepted
  2026-10-15). The fine-tuned weights are for internal research only. The data's terms are the
  same as in current use.

## What this plan does not do

It runs no training, separation or render; that waits for the go. It builds no route-B model.
It doesn't touch the product (`scripts/`, `skills/`); the pan question is the product session's
to take up. It doesn't spend the step-7 held-out sets.

## Review

One independent skeptical review, fresh context, read-only: **go with changes**. Required changes,
all applied above:
- disk margin stated;
- bands resolved through `group` (Hikikomori, New One and Procession are one band, John Morgan
  Kimock; Procession has no electric-guitar target);
- Timo And The Timezone moved to "never" (proposed B2 known-answer band);
- per-session mix lists, bounce classification and the track table extended to training sessions;
- the high-gain role restated;
- Step 1 made the decider instead of an SNR-slope gate, with R0a reduced to a sanity stop at 0 dB;
- Step 2's entry matched to Step 3's power (YG − M ≤ −0.032);
- YT − M with its interval;
- Holm's correction and a declared order for the T variants;
- the Step 3 gate fully partitioned;
- adoption limited to the development default and the step-4 test;
- the training budget set from the measured step time;
- MPS fallbacks declared, with the iSTFT named;
- factual fixes (19 of 21 parts have another electric guitar; the 9.96 / 1.45 dB context; M − H as
  about a quarter of YT − H; Swatkins is not in stage D).

Optional suggestions taken: route B's first move (screening existing query-conditioned and permutation-invariant
separators), X and G_noDT in Step 0, the label-noise note, and validation at the 10-s chunk.
