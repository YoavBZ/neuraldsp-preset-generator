# Cleaning the direct model's data: review and options

Drafted 2026-10-22: zero renders, no training, no downloads beyond web pages. It reviews the ML
session's cleaning proposal for D_stem and recommends a declared design. Development data only.
The ML plan's rules apply (effect sizes with 90% band-clustered intervals, no pass bars, renders
declared). **The user's rule (2026-10-22):** use only what we can trust, no dirty tracks.
Measurements, training and listening use a reviewed trusted set, and dirty tracks are excluded,
not flagged.

- **Inputs read:** the [data-quality audit](https://github.com/YoavBZ/neuraldsp-preset-generator/pull/272)
  (draft PR #272) and its evidence; [the plan](direct-model-stems-plan.md) (steps 3–4,
  amendments 2 and 5–7); [step 3–4 results](direct-model-stems-results.md);
  [pilot results](direct-model-stems-pilot-results.md); `learn/pretrain_set.py` and
  `learn/direct_stems.py`.
- **New counts here** come from stored files only:
  `~/ndsp-presets/learn/data-quality-2026-10-22/contam-*.jsonl`, `pretrain-set/leakage.json`,
  the audit's `di-library-match-summary.json`, `r-in-gate-vs-contamination.json.gz` and the build
  rows' `early_stop` flags.
- **Tags:** *[project]* is measured in this repo. *[published]* is from the literature.
  *[inferred]* is reasoning, not measured.

## Headline

1. **The 3-way split is right in spirit, but kinds 1 and 2 are not yet defined from data.**
   - **Kind 1 does not exist in D's own data.** Its targets are exact renders.
   - **The live-room problem reaches D only through the backing.** No stored metric gives its
     level.
   - **The stored doubles rule misses most named doubles.**
   - **The level draw is not dirt.**
2. **Comparing with step 3's models mixes "cleaner" with "fewer".**
   - Kind 2 as proposed removes 15–29% of the pool.
   - Along the pilot's learning curve, that alone costs about **+0.004 to +0.008 E**. D's whole
     margin over the constant on R_in is −0.016.
3. **The trusted test set collapses.** Applied to R_in, the proposal's own kinds leave 1–2 bands:
   no band-clustered interval is possible.
4. **Recommended: rebuild, don't drop.**
   - Measure one per-example quantity first: how loud the target's own part is in the backing
     (zero renders).
   - Rebuild the affected examples without those tracks, at the same N, band mix and level mix.
     Use the same rebuild for the test set.
   - Retrain D_stem once on the trusted pool (2 seeds) and compare with step 3's seeds on the
     rebuilt trusted R_in.
   - Rebuilding costs about as much MPS time as a size-matched control. It separates cleaner from
     fewer exactly, and keeps the data the learning curve says we need.

## A. Review of the proposal

### What it gets right

- **Kind 3 should be kept.** Separator residue on normal mixes is what the product faces. Every
  separator reads the same median contamination on V_sep (0.45).
- **One retrain, 2 seeds, amendment 5's readout and the sound gate only if E moves** is the right
  scale.

### Kind 1: well defined only where it applies

- **D's training pool and V_sep have no source-dirty target.** The label is the rendered DI
  section's settings, so it is exact. The DIs are screened (0 clip runs, 0 drop-outs, hum
  ≤ −56 dB) *[project]*.
- **Kind 1 lives in the amp-track targets:** stage F, knob ceiling 2 and the listening pages.
  - **There it has a stored, validated metric:** `audits/bleed-2026-10-16/bleed-table.json`
    gives bleed per half in dB of the amp track. Injected −25 dB reads −25 to −27, and the floor
    is about −30 dB.
  - **Flags:** low < −30 dB, moderate −30 to −20 dB, high > −20 dB.
  - **Define it per half, not per session.**
- **"Remove the Telefunken live sessions" would be the wrong tool for D.**
  - **In training,** it cuts Eggy and Renesans: 10,234 examples, 48% of the pool.
  - **In R_in,** it cuts John Morgan Kimock and Swatkins: 595 of 1,407 examples, the two bands
    where D gained.

### The live-room problem reaches D through the backing, at an unmeasured level

- **The leak check keeps some tracks.** It keeps backing tracks whose coherence excess with the
  part's own amp track is below 0.05. Cambridge studio tracks read ≤ about 0.002 *[project]*.
- **The kept tracks read far higher in the live sessions:**

  | Band | Kept tracks' coherence excess |
  |---|---|
  | Eggy | about 0.011 (Room Mic Garage, Bass Amp); "Farthest Step" VOX BASS 0.0499 |
  | Renesans | 0.018–0.042 (Bass Amp, Kick Out, Hats, Rooms) |
  | John Morgan Kimock (R_in) | 0.026 (Mono OH) |
  | Swatkins (R_in) | 0.025–0.037 (Close Rooms, Leslie) |

  At ≥ 0.01, that is 49% of the pool and 626 V_sep examples.
- **Coherence excess is not a level.**
  - **It may also be drum bleed in the amp track** rather than guitar in the room mic. The live
    amp tracks carry drums at −8 to −14 dB.
  - **A rough estimate *[inferred]*:** a room mic at excess 0.025 that holds 20–50% of the
    backing, at the median level draw, would put the original take about 10–20 dB under the
    render. That is the "high" range the user complained about, so this must be measured before
    any rule. The audit left it "not measured further".

### Doubles: the stored rule misses most of them

- **The audit's onset rule** (`hi_other`: onset r > 0.6 in ≥ 25% of the DI's windows) flags 231
  training examples: Ale Lak ElecGtr02 and 02DT.
- **It misses three cases:**
  - **Ale Lak's other named double pairs** (ElecGtr01/01DT and 04/04DT): 1,918 examples.
  - **Renesans "Labor Of Hate"**: 999 examples. Its `GTR Pre Rec` beats the own amp in 47% of
    windows, but is not `hi_other`.
  - **The Long Wait**: 77 examples. ElecGtr3 is better than the own amp in 45% of windows.
- **Why it misses:** onsets are weak through distortion, which is the audit's own stated limit.
- **Other rules, from stored data (v0):**
  - Cambridge's own "DT" naming;
  - `hi_other`;
  - `better` ≥ 0.25 with a guitar track on top over ≥ 10 windows.

  Together they flag **3,225 pool examples (15.1%), 305 of the 998 early-stopping examples (31%),
  and 374 of R_in's 405 Adam Buckley examples** *[project]*.
- **Why doubles are dirt** *[inferred]*:
  - **In a real song,** a double of the same part usually shares the target's rig, so it agrees
    with the label.
  - **Here,** it keeps the original tone beside a render with drawn settings, so the stem holds a
    confident second answer that contradicts the label.
  - **The mixture-density loss cannot absorb this.** It can widen its spread for an uninformative
    input (loss attenuation; [Kendall & Gal 2017](https://arxiv.org/abs/1703.04977)
    *[published]*), but not for an input that looks clean and points elsewhere.

### The level draw (< −15 dB) is not dirt

- **The label is exact and the tracks are clean.** The ratios are the measured real ratios: 971
  sections, 5–95% from −18.9 to −2.6 dB (`pretrain_set.ratio_values`).
- **R_in has the same draw:** 17% of R_in is below −15 dB.
- **This is where D fails, not where data is wrong.** On step 3's gate, log d D − constant reads
  *[project]*:

  | Band | Below −15 dB | −15 dB and above |
  |---|---|---|
  | John Morgan Kimock | −0.04 | −0.34 |
  | Swatkins | −0.11 | −0.33 |
  | Adam Buckley | −0.02 | −0.07 |
  | Dark Ride | +0.05 | +0.01 |

- **Dropping these examples causes a mismatch either way:**
  - from training only: a train/test shift;
  - from the test too: it changes the question.
- **Whether `match` should accept songs with a buried guitar is a product-scope question for the
  user,** not cleaning. Keep these examples, and report by level bin.

### Fewer versus cleaner: the comparison as proposed is confounded

- **Size.** Pilot slope −0.017 E per doubling (seeds −0.028 and −0.006) *[project]*. Projected
  cost of dropping *[inferred]*:

  | Dropped | Projected cost (E) | Steeper seed |
  |---|---|---|
  | 15% (doubles v0) | +0.004 | +0.007 |
  | 29% (doubles v0 and level) | +0.008 | +0.014 |
  | 48% (Telefunken) | +0.016 | +0.026 |

  Against: D − constant on R_in, −0.0159.
- **Seeds and readout.** Step 3 reads 3 seeds × 2 halves; the new arm would read 2 × 2. A2's
  averaging alone moved E by about 0.002 in the sanity check.
- **Early stopping and the pull.**
  - **31% of the early-stopping set is v0-dirty.** It chooses the checkpoints and fits amendment
    5's b.
  - **The fix:** the arms must share it, and it must be trusted.
- **Optimisation steps.** At 40 epochs, a smaller pool gets fewer steps. Step 3's seed 20261044
  already peaked at epoch 38 of 40.
- **Band mix.** The dirt is concentrated in a few bands: Ale Lak, Renesans, Telefunken.
  - **Dropping it rebalances the pool.**
  - **A band-matched random drop cannot separate cleaning from band composition** when a whole
    band is dirty.

### The trusted test set is not yet well defined

- **R_in under the proposal's own kinds:**
  - Adam Buckley keeps 31 of 405 examples (one section).
  - If the live sessions count, John Morgan Kimock and Swatkins go too.
  - Left: Dark Ride (407), the band with the most contaminated stems (0.64) and the flattest
    gate.
- **That is 1–2 bands, with no band-clustered interval.**
- **A hint that test-side doubles bias the reading** *[project]*, descriptive and tiny:
  - Adam Buckley's four double-flagged DIs read −0.05 to +0.06 on the gate (370 examples, 12
    sections).
  - Its one clean DI reads −0.26 (31 examples, 1 section).

### Other things that could mislead

- **The contamination measure is not a dirt measure.**
  - It correlates with the per-cell error at ρ 0.64, and has no measured floor.
  - Filtering on it is pruning by difficulty.
  - Use it for strata only.
- **R_in has been read many times.** Every threshold here is fixed before any model output is
  read by it.

## B. Options compared

GPU hours assume step 3's speed (67–77 min per D_stem seed at 20.3k). Separation runs on X-LANCE
with the two workers at 0.29–0.34 clips/s, about 8–10 h per 10k. Renders are training-style, about
0.94 per example plus priming.

| Approach | What it fixes | Evidence | Cost | Risk |
|---|---|---|---|---|
| **Proposal as written:** drop kinds 1–2, compare with step 3's seeds | Doubles, level, live sessions | None for this setup | 2.3–2.6 GPU h | Confounds cleaner with fewer, 3 vs 2 seeds, and the early-stopping set; drops real levels; R_in collapses |
| **Drop plus a size-matched random control** (the audit's step 1 design) | Separates cleaner from fewer when dirt is spread across bands | Standard ablation *[inferred]* | 4.6–5.2 GPU h, 0 renders | Cannot separate band-wide dirt from band mix; the control trains on dirty tracks; still loses data |
| **Rebuild affected examples without same-part tracks (recommended)** | Doubles and live-room takes, at equal N, band and level mix | Removes the cause at the source *[inferred]*; matches the user's rule | v0: about 3.6k renders and separations (about 3–3.5 h); at most about 13.4k (11–13 h) if the live-room tracks count; 2.3–2.6 GPU h | The backing loses doubles and room mics, so the input is a little less realistic; needs a small code change in the backing list |
| **Rebuild with consistent doubles** (partner DI rendered at the label's settings) | As above, and keeps realistic doubling | *[inferred]* | One more render per affected example | More code; partner DIs exist only for named pairs |
| **Drop by separator contamination** (kind 3 filter; the audit's arms a/c) | Heavy residue | Pruning beats scaling only with abundant data and a good metric ([Sorscher 2022](https://arxiv.org/abs/2206.14486)). Filtering helped little when all stems were corrupted (MDX23 bleeding, +0.5 dB; [Fabbro 2024](https://transactions.ismir.net/articles/171)). Cleaning can hurt ([CleanML](https://arxiv.org/abs/1904.09483)). All *[published]* | About 6 GPU h | Shifts training away from the test; the measure is partly difficulty |
| **Level floor** (redraw < −15 dB) | Buried guitars | *[project]*: those examples are where D fails | About 3.4k separations (about 4 h) | Not dirt; a product-scope decision |
| **Per-example weights by contamination** | Soft down-weighting | Reweighting needs a clean meta set and is complex ([Ren 2018](https://arxiv.org/abs/1803.09050), [Meta-Weight-Net](https://arxiv.org/abs/1902.07379)) *[published]* | 2.3 GPU h plus code | Keeps dirty tracks, which breaks the user's rule; shifts the distribution |
| **Loss truncation, small-loss selection, confident learning** | Label noise | MDX23 label-noise track: +1.2–1.3 dB SDR from loss truncation, +2.5 dB with filtering ([Fabbro 2024](https://transactions.ismir.net/articles/171); [Kang 2020](https://arxiv.org/abs/2004.14589); [Northcutt 2021](https://arxiv.org/abs/1911.00068)) *[published]* | 2.3–4.6 GPU h plus code | Our labels are exact, so high loss means hard, realistic examples; the drops depend on the model and cannot be audited as "trusted" |
| **Curriculum** (clean first, then all) | Kind 3 only, at equal N | Helps only with noisy labels or a short budget ([Wu 2021](https://arxiv.org/abs/2012.03107)) *[published]* | 2.3 GPU h | A small expected gain *[inferred]* |
| **Clean pretrain, realistic fine-tune** (D0 composition, then stems) | The stem mismatch | Matched noisy training beats clean training (ASR word error rate −14% to −29%, [MCT](https://ojs.cvut.cz/ojs/index.php/ap/article/view/1105)) *[published]*. D_stem already beat D0 by −0.127 log d *[project]* | 2–3 GPU h | Not cleaning; a later lever |
| **More separator-aware augmentation** | The separator mismatch | The pilot's augmentations −0.0115 E *[project]*; StemFX trains on separated stems ([2026](https://arxiv.org/abs/2607.15634)) *[published]* | Code plus 2.3 GPU h | Not cleaning |
| **Clean the test, early-stopping and readout sets** | Trust in every number | The user's rule; test-side doubles hint (§A) *[project]* | Included in the rebuild | Few bands left unless rebuilt |

## C. Recommendation: a trusted rebuild, cheapest first

### Step 0: declare the trusted sets (0 renders, 0 GPU, about 1–2 h of CPU)

No model output is read in this step.

**OTL, the original-take level,** per example and half, in dB relative to the rendered target in
the mix. It is computed in the example's own backing variant (with or without vocals):

  OTL = 10·log10((P_same + E_take) / P_backing) − ratio_db

The example's OTL is the maximum over its two halves.

- **P_same:** the full section power of every kept **same-part track**. A track is same-part if
  any of these holds:
  1. Cambridge naming: the DI's part name with "DT" added or removed.
  2. A guitar track with onset r > 0.6 in ≥ 25% of the DI's playing windows (`di_match.py`).
  3. A guitar track that beats the own amp track in ≥ 25% of ≥ 10 windows.

  Rules 2 and 3 are re-run on the windows that overlap the section.
- **E_take:** the energy of the other kept tracks explained by the part's own amp track beyond
  the session's drum and bass close mics.
  - **How:** `bleed4.py`'s held-out regression with its shifted-track null, roles swapped. The
    backing is the "record", the own amp track the source, the close mics covariates.
  - **A lower bound, reported beside:** the same with the DI as the source.
- **Trusted example:** OTL ≤ −20 dB. That is the bleed audit's "high" boundary, where every user
  bleed complaint (U0, U1, U8, U10, U13) sits.
  - **Sensitivity:** the count at −30 dB is reported. It decides nothing.
- **Trusted amp-track half** (stage F, knob ceiling 2, listening):
  - bleed flag low (< −30 dB) on both halves;
  - DI active ≥ 50% of frames;
  - DI–reference chroma ≥ 0.8 or onset ≥ 0.35.

  This leaves 16 of stage F's 21 parts.
- **Not dirt, kept:** contamination (`leak_A`/`leak_B`) and the level draw. Both are reported as
  strata.
- **Route, fixed by the count:**
  - **Drop** if the untrusted share of the training pool is ≤ 5%. The projected size cost is
    ≤ 0.0013 E.
  - **Rebuild** if it is above 5%.
  - **R_in:** rebuild its untrusted examples whenever dropping them would leave a band with fewer
    than 3 sections or 90 examples.
- **The stored-data count (v0, before the measurement):** 15.1% of the pool and 374 R_in
  examples. So the expected route is **rebuild**.

### Step 1: read the test-side effect (0 GPU; renders only for rebuilt R_in examples)

- **The models:** step 3's D_stem, called F (seeds 20261042 and 20261043, and all 3 beside).
- **The pull:** amendment 5's b refitted on the trusted early-stopping set. The constant stays
  step 3's stored one.
- **What it reads, on R_in-trusted against R_in-untrusted:**
  - masked E;
  - the gate's log d D − constant from the stored rows.
- **On rebuilt R_in examples:** F's answers are re-rendered. About 374 v0 renders plus priming;
  the truth and constant renders are reused, since they do not depend on the mix.
- **Stage F:** D − S on the trusted parts, from the stored step 4 rows.
- **It decides nothing.** It gives the trusted baseline and shows whether test-side dirt biased
  step 3.

### Step 2: the trusted retrain (the GPU test)

- **Arm T:** D_stem on the trusted pool, rebuilt.
  - **Kept as drawn:** the DI section, label, ratio, vocals, leak, LUFS and mastering draws.
  - **Changed:** the backing loses its same-part and take-carrying tracks.
  - **Then:** X-LANCE re-separates, into a new root. The old stems stay untouched.
  - **Also:** the early-stopping set is rebuilt the same way.
  - **Recipe:** step 3's, unchanged (augmentations, at most 40 epochs, patience 4), at the same
    N, so the optimisation steps are equal. Seeds 20261042 and 20261043.
- **Reference F:** step 3's seeds 20261042 and 20261043 (no training), with b refitted on the
  trusted early-stopping set.
  - **Declared mismatch:** F's checkpoints were chosen on the old early-stopping set.
- **Readout (zero renders):**
  - masked E on R_in-trusted;
  - both arms read the same way: A1+A2+A3 over 2 seeds × 2 halves;
  - paired per example, band-weighted, 90% band-clustered t interval (4 bands, 3 df, if
    rebuilt).
- **Beside it:**
  - each arm's seed difference (the noise floor);
  - contamination terciles, level bins and class;
  - rebuilt and untouched examples;
  - R_out on the trusted examples.
- **The sound gate:** only if T − F's E interval excludes 0.
  - Train T's seed 20261044, then render T's 3-seed answers on R_in-trusted (about 1.5k renders).
  - Read T − F with the gate's statistic against F's stored renders.
- **If the user declines renders and the share is above 5%:** use the drop route. Add a control
  R: the same count dropped at random within band × level bin (`random.Random(20261096)`), seeds
  20261042 and 20261043, epoch caps scaled to equal steps.
  - **T − R** reads cleaner; **R − F** reads fewer.
  - **The limit:** the contrast cannot read a band that is wholly dirty.

### What each outcome means

| Reading | Meaning | Next |
|---|---|---|
| **T − F below 0** | Training-side dirt was costing accuracy | T is the baseline. The same-part rule goes into `backing_tracks` for every future build |
| **Contains 0** | Not shown at this power | T is still the baseline (the user's rule). The open levers are buried guitars and separator residue |
| **Above 0** | The removed tracks were helping as realism | Revisit with the user; the next arm is consistent doubles |
| **Step 1: trusted and untrusted R_in differ** | Step 3's gate was biased by test-side dirt | The trusted reading becomes the record |

### Budget

| Item | Renders | Separations | GPU | CPU |
|---|---|---|---|---|
| Step 0 | 0 | 0 | 0 | 1–2 h |
| Step 1 | about 400 for v0's rebuilt R_in (up to about 1k) | counted in the rebuild rows | 0 | about 15 min |
| Step 2 rebuild, v0 | about 3.6k | about 3.6k (3–3.5 h MPS + CPU) | — | — |
| Step 2 rebuild, live-room tracks included (upper) | about 13.4k | about 13.4k (11–13 h) | — | — |
| Step 2 training (T, 2 seeds) | 0 | 0 | 2.3–2.6 h | — |
| Gate, only if E moves | about 1.5k | 0 | +1.1–1.3 h | — |

**Without the gate:** 2.3–2.6 GPU h, about 4k renders and 3.6k separations (v0), or 13.8k and
13.4k if the live-room tracks count. No held-out data is touched.

## Sources

**Published:**
- Fabbro et al., [The Sound Demixing Challenge 2023, music demixing track](https://transactions.ismir.net/articles/171),
  TISMIR 2024: loss truncation, filtering, label noise against bleeding.
- Kang & Hashimoto, [loss truncation](https://arxiv.org/abs/2004.14589), ACL 2020.
- Sorscher et al., [beyond neural scaling laws](https://arxiv.org/abs/2206.14486), NeurIPS 2022.
- Li et al., [CleanML](https://arxiv.org/abs/1904.09483), ICDE 2021.
- Wu, Dyer & Neyshabur, [when do curricula work?](https://arxiv.org/abs/2012.03107), ICLR 2021.
- Northcutt et al., [confident learning](https://arxiv.org/abs/1911.00068), JAIR 2021.
  [cleanlab for regression](https://docs.cleanlab.ai/stable/tutorials/regression.html).
- Ren et al., [learning to reweight](https://arxiv.org/abs/1803.09050), ICML 2018.
  Shu et al., [Meta-Weight-Net](https://arxiv.org/abs/1902.07379), NeurIPS 2019.
- Kendall & Gal, [what uncertainties do we need](https://arxiv.org/abs/1703.04977), NeurIPS 2017.
  Seitzer et al., [β-NLL](https://arxiv.org/abs/2203.09168), ICLR 2022: NLL training can underfit
  hard regions.
- Fonseca et al., [FSDnoisy18k](https://arxiv.org/abs/1901.01189), ICASSP 2019: noise-robust losses
  in audio tagging.
- [Multi-condition training for robust ASR](https://ojs.cvut.cz/ojs/index.php/ap/article/view/1105).
- [StemFX](https://arxiv.org/abs/2607.15634), 2026: effect chains predicted from separated stems.
- [Lyrics transcription with separation](https://arxiv.org/abs/2506.15514), 2025: separator artefacts
  in downstream models.

**Project:** the [audit](https://github.com/YoavBZ/neuraldsp-preset-generator/pull/272),
[bleed audit](audits/bleed-2026-10-16/README.md), [step 3–4 results](direct-model-stems-results.md),
[pilot results](direct-model-stems-pilot-results.md).
