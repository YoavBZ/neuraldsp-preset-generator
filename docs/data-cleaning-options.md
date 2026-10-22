# Cleaning the direct model's data: declared plan

Declared 2026-10-22, before any non-smoke run. Development data only. The ML plan's rules apply
(effect sizes with 90% band-clustered intervals, no pass bars, renders declared). **The user's rule
(2026-10-22):** use only what we can trust, no dirty tracks. Measurements, training and listening
use a reviewed trusted set, and dirty tracks are excluded, not flagged.

- **Status.** The user decided on 2026-10-22 to go with the rebuild approach: "review, search and
  go with the best"; the review agreed that rebuilding beats dropping. An independent review read
  **go with changes**. Its seven required changes are applied below
  ([what the review changed](#what-the-independent-review-changed)).
- **Code:** `learn/data_cleaning.py` (steps 0 and 1), tests `tests/test_data_cleaning.py`.
- **Ledger:** `data-cleaning` in [`dev-test-ledger.json`](dev-test-ledger.json), entered before any
  compute.
- **Data:** `~/ndsp-presets/learn/data-cleaning/`.
- **Amendment 1 (2026-10-22, from the PR #273 code review, before any real run):** the injection check
  votes per session, and only the sessions the estimator was not developed on decide. The code
  review's other six fixes are folded in with it
  ([amendment 1](#amendment-1-2026-10-22-code-review-the-injection-check-votes-per-session)).
- **Not run yet.** Only scratch smoke runs exist (listed under [Smoke](#smoke-development-decides-nothing)).
  Step 2's data part (the candidate-driven pool rebuild) is built too; training waits for the user's
  listening verdicts on the suspected doubles.
- **Inputs read:** the [data-quality audit](https://github.com/YoavBZ/neuraldsp-preset-generator/pull/272)
  (draft PR #272) and its evidence; [the plan](direct-model-stems-plan.md) (steps 3–4,
  amendments 2 and 5–7); [step 3–4 results](direct-model-stems-results.md);
  [pilot results](direct-model-stems-pilot-results.md); `learn/pretrain_set.py` and
  `learn/direct_stems.py`.
- **Tags:** *[project]* is measured in this repo. *[published]* is from the literature.
  *[inferred]* is reasoning, not measured.

## Headline

1. **The ML session's 3-way split is right in spirit, but its kinds 1 and 2 were not defined from
   data** (§A).
   - Kind 1 does not exist in D's own data, because its targets are exact renders.
   - The live-room problem reaches D only through the backing.
   - The stored doubles rule missed most named doubles.
   - The level draw is not dirt.
2. **Dropping would mix "cleaner" with "fewer"** (§A). The learning curve prices a 15–29% drop at
   +0.004 to +0.008 E. D's whole margin over the constant on R_in is −0.016.
3. **The declared plan rebuilds instead of dropping** (§C).
   - **Step 0** (zero renders, CPU) measures, per section, how much of the target's own part each
     backing track carries.
   - **Step 1** (zero renders) rebuilds every untrusted R_in example without those tracks, and reads
     step 3's model on the original against the rebuilt stems of the same examples.
   - **Step 2** retrains D_stem on the rebuilt trusted pool at the same N.
4. **One threshold, −30 dB of the target's own track,** for training and test backings and for
   amp-track targets.
5. **The take estimator must pass an injection check first** (amendment 1).
   - **The vote:** every drum, room and overhead track of each clean session gets an injected take,
     and 3 sessions the estimator was not developed on decide.
   - **In development smoke runs,** close mics read takes back within about 1.5 dB, but one loud room
     mic read −34.4 dB for −30 dB.
   - **The check can fail.** If it does, step 0 stops and returns to review.

## A. Review of the ML session's proposal (as first written)

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

## B. Options compared (as first written)

GPU hours assume step 3's speed (67–77 min per D_stem seed at 20.3k). X-LANCE separation runs at
4.3–5 s a clip on the MPS alone (about 12–14 h per 10k), or about 0.35 clips/s with the CPU worker
beside it (about 8 h per 10k). Renders are training-style, about 0.94 per example plus priming.

| Approach | What it fixes | Evidence | Cost | Risk |
|---|---|---|---|---|
| **Proposal as written:** drop kinds 1–2, compare with step 3's seeds | Doubles, level, live sessions | None for this setup | 2.3–2.6 GPU h | Confounds cleaner with fewer, 3 vs 2 seeds, and the early-stopping set; drops real levels; R_in collapses |
| **Drop plus a size-matched random control** (the audit's step 1 design) | Separates cleaner from fewer when dirt is spread across bands | Standard ablation *[inferred]* | 4.6–5.2 GPU h, 0 renders | Cannot separate band-wide dirt from band mix; the control trains on dirty tracks; still loses data |
| **Rebuild affected examples without same-part tracks (recommended)** | Doubles and live-room takes, at equal N, band and level mix | Removes the cause at the source *[inferred]*; matches the user's rule | v0: about 3.6k renders and separations (4.3–5 h MPS alone, about 2.9 h with the CPU worker); at most about 13.4k (16–19 h, or about 10.6 h); 2.3–2.6 GPU h | The backing loses doubles and room mics, so the input is a little less realistic; needs a small code change in the backing list |
| **Rebuild with consistent doubles** (partner DI rendered at the label's settings) | As above, and keeps realistic doubling | *[inferred]* | One more render per affected example | More code; partner DIs exist only for named pairs |
| **Drop by separator contamination** (kind 3 filter; the audit's arms a/c) | Heavy residue | Pruning beats scaling only with abundant data and a good metric ([Sorscher 2022](https://arxiv.org/abs/2206.14486)). Filtering helped little when all stems were corrupted (MDX23 bleeding, +0.5 dB; [Fabbro 2024](https://transactions.ismir.net/articles/171)). Cleaning can hurt ([CleanML](https://arxiv.org/abs/1904.09483)). All *[published]* | About 6 GPU h | Shifts training away from the test; the measure is partly difficulty |
| **Level floor** (redraw < −15 dB) | Buried guitars | *[project]*: those examples are where D fails | About 3.4k separations (about 4 h) | Not dirt; a product-scope decision |
| **Per-example weights by contamination** | Soft down-weighting | Reweighting needs a clean meta set and is complex ([Ren 2018](https://arxiv.org/abs/1803.09050), [Meta-Weight-Net](https://arxiv.org/abs/1902.07379)) *[published]* | 2.3 GPU h plus code | Keeps dirty tracks, which breaks the user's rule; shifts the distribution |
| **Loss truncation, small-loss selection, confident learning** | Label noise | MDX23 label-noise track: +1.2–1.3 dB SDR from loss truncation, +2.5 dB with filtering ([Fabbro 2024](https://transactions.ismir.net/articles/171); [Kang 2020](https://arxiv.org/abs/2004.14589); [Northcutt 2021](https://arxiv.org/abs/1911.00068)) *[published]* | 2.3–4.6 GPU h plus code | Our labels are exact, so high loss means hard, realistic examples; the drops depend on the model and cannot be audited as "trusted" |
| **Curriculum** (clean first, then all) | Kind 3 only, at equal N | Helps only with noisy labels or a short budget ([Wu 2021](https://arxiv.org/abs/2012.03107)) *[published]* | 2.3 GPU h | A small expected gain *[inferred]* |
| **Clean pretrain, realistic fine-tune** (D0 composition, then stems) | The stem mismatch | Matched noisy training beats clean training (ASR word error rate −14% to −29%, [MCT](https://ojs.cvut.cz/ojs/index.php/ap/article/view/1105)) *[published]*. D_stem already beat D0 by −0.127 log d *[project]* | 2–3 GPU h | Not cleaning; a later lever |
| **More separator-aware augmentation** | The separator mismatch | The pilot's augmentations −0.0115 E *[project]*; StemFX trains on separated stems ([2026](https://arxiv.org/abs/2607.15634)) *[published]* | Code plus 2.3 GPU h | Not cleaning |
| **Clean the test, early-stopping and readout sets** | Trust in every number | The user's rule; test-side doubles hint (§A) *[project]* | Included in the rebuild | Few bands left unless rebuilt |

## C. The declared plan

### What the independent review changed

| # | Required change | Where it is now |
|---|---|---|
| 1 | Confirm "same part" by pitch (chroma), not onsets alone | Step 0: a candidate (naming or onsets) must also reach chroma ≥ 0.70. Onsets alone never decide. Swatkins' Leslie is judged by its data, not its name |
| 2 | Remove tracks per section, not per example | Step 0: the take is read against the target's own track, so it does not depend on the example's level draw. Removal lists are per section, and no level filter comes back |
| 3 | Validate the swapped-role take estimate by injection first; decide the amp-source estimate | Step 0a: injection at −20, −25 and −30 dB into clean Cambridge backings, with declared pass rules. `scan` refuses without INJECTION OK. The amp-source reading decides (upper bound); the DI-source reading is reported beside |
| 4 | One threshold, or justify two | One: −30 dB of the target's own track, for backings and for amp-track targets |
| 5 | Step 1 is paired; rebuild every untrusted R_in example; no target renders | Step 1: F read on the original and the rebuilt stems of the same examples. The gate's 1,407 stored truth renders are the targets |
| 6 | Step 2: untouched trusted R_in co-primary; doubled test examples with consistent doubles; the gate on F's re-rendered answers | Step 2 |
| 7 | Both separation rates in the budget | Budget: MPS alone 4.3–5 s a clip; MPS with the CPU worker about 0.35 clips/s |

### Step 0: declare the trusted sets (zero renders, CPU)

No model output is read in this step.

**The take level.** For a kept backing track in a section, the take level is the energy of the
target's own part that the track carries, in dB of the target's own close-mic (amp) track. This is
the same reference the bleed audit uses for amp-track targets.
- **Not tied to the level draw.** The rule cannot become a level filter (review change 2).
- **Dropped:** the per-example level relative to the render, OTL in the first draft.

- **Same-part tracks** (another take of the part, such as a double):
  - **Their whole power counts**, read per section as the larger half.
  - **Candidates:**
    - Cambridge "DT" naming (ElecGtr01 and ElecGtr01DT);
    - section onset correlation with the DI ≥ 0.6;
    - onsets that follow the DI at least as well as the own amp track does.
  - **Confirmed by pitch:** chroma similarity with the own amp track (the DI when there is none)
    ≥ 0.70 in the section. That is the label table's weakest verified own pair (0.696).
- **Any other track: a session-level take.** A room path does not change between sections, and the
  whole session gives far more frames than a 9-s section.
  - **The regression:** a per-bin complex ridge regression of the track on the own amp track, with
    lags −1 to 6 STFT frames (about −43 to +256 ms).
    - Analysis rate 24 kHz, STFT 2048/1024, 250 Hz–8 kHz.
    - Ridge 0.3 relative to the bin's mean diagonal.
  - **Cross-validated:** in 10 contiguous blocks of the session, on frames where the amp plays.
  - **Less chance:** minus the mean of four nulls, the source rolled by ±2 and ±3 s. The nulls
    are past the lags, and close enough to keep the music's structure.
  - **Never above the track's own power.**
  - **The amp-source reading decides.** It is an upper bound, since a live amp track's own drum
    bleed can pose as take. The DI-source reading is reported beside it.
  - **Floor:** takes under −40 dB count as none.
  - **Parts with no amp track** (Dark Ride's DIs) recorded no original take, so only confirmed
    same-part tracks count there.
- **The rule:** per section, remove the fewest tracks, largest take first, until the section's
  summed take is ≤ −30 dB.
  - An example is untrusted only if its own backing variant (with or without vocals) loses a track.
  - A section's removal list applies to every example of that section.
- **Why −30 dB, for both backings and amp-track targets** (review change 4):
  - It is the bleed audit's "low" boundary and its measured floor.
  - In both cases the quantity is the same: foreign content in dB of the target's own track.
- **Not dirt, kept:** separator contamination (`leak_A`/`leak_B`) and the level draw. Both are
  reported as strata.
- **Route:**
  - **Drop** if at most 5% of the training pool is untrusted. The projected size cost is
    ≤ 0.0013 E.
  - **Rebuild** otherwise.
  - **R_in:** every untrusted example is rebuilt (review change 5).

**0a, the injection check** (`inject`; it gates `scan`), as amendment 1 has it:
- **The sessions:** the clean Cambridge training sessions. Each has an own amp track, and every
  kept track reads coherence ≤ 0.002 in part C's leak check. There are 6, with 17 DIs.
  - **Deciding (3):** Hollow Ground "Ill Fate", Rebuild The Evil "Burial Of Silence" and The Long
    Wait "Drag". The estimator was not developed on them.
  - **Read beside (3):** Ale Lak, Death Of A Romantic and Storm Of Particles, the development
    sessions.
  - **The source:** one DI per session, drawn by seed 20261097; its own amp track is the injected
    source.
- **The injection:** a room-filtered copy of the own amp track (direct path after 5–20 ms, an
  exponential tail with RT60 0.3–0.8 s), added in turn to every kept drum, room and overhead track
  at −20, −25 and −30 dB.
- **A session passes when, at every level:**
  - ≥ 80% of its targets read back (within 3 dB at −20 and −25 dB, ≥ −33 dB at −30 dB);
  - ≥ 80% of its room and overhead targets read back, when it has any;
  - ≥ 90% of its targets read under −35 dB uninjected.
- **INJECTION OK requires all of these:**
  - all 3 deciding sessions pass;
  - they hold at least one room or overhead target;
  - at most 5% of their other non-guitar tracks read ≥ −30 dB uninjected.
- **Fail closed:**
  - **A record is never overwritten,** so a FAIL cannot be rerun silently.
  - **`--dev`** (the development sessions alone) runs only as a scratch smoke.
  - **`scan` checks the record:** it must be real, OK, made under the current rule and estimator,
    and hold exactly the 3 deciding sessions with their drawn DIs.
- **On INJECTION FAIL:** step 0 stops and returns to review. There is no silent fallback.

**0b, the scan, and 0c, the lists:**
- **The scan** (`scan`) covers all 332 sections of the D build (277 pool, 55 V_sep).
- **The lists** (`lists`) write `trusted.json` with:
  - per section, the removed tracks, with their class and both readings;
  - per example, trusted or untrusted;
  - counts for the training pool, early stopping, V_sep and R_in per band;
  - the route;
  - descriptive counts at −25 and −20 dB.
- **Review before use.** The removal lists are reviewed before step 1 or 2 reads them, which is the
  "reviewed trusted set" of the user's rule.

**Amp-track targets** (stage F, knob ceiling 2, listening pages; not in steps 0–2):
- **A trusted half needs all of these:**
  - bleed flag low (< −30 dB, `audits/bleed-2026-10-16/bleed-table.json`);
  - the DI active on ≥ 50% of frames;
  - DI–reference chroma ≥ 0.8, or onset correlation ≥ 0.35.
- **A trusted part has both halves trusted.** That leaves 16 of stage F's 21 parts.

### Step 1: the paired R_in rebuild (zero renders, X-LANCE on MPS)

- **Driven by the candidate list** (amendment 1). The R_in examples rebuilt are those a switched-on
  candidate touches. Examples a pending candidate touches are excluded from the trusted R_in, as are
  refused ones. Files and rows are keyed by the removed tracks, and a row under another key is never
  read: `rin-read` refuses while any wanted example is not built under the current list.
- **1a, the rebuild** (`rin-rebuild`). For each R_in example the list wants rebuilt:
  - **The target:** the gate's stored truth render (24-bit FLAC, hash-checked) is the example's
    rendered guitar, so no target is rendered.
  - **A parity check first:** the original mix is re-made from it with the stored draw, and must
    match the stored mix mels (99% of cells within one 0.5-dB step, half LUFS within 0.01).
    Otherwise the example is refused and counted.
  - **The rebuilt mix:**
    - drops the section's removed tracks from the example's backing variant;
    - keeps the ratio, vocals, loudness and mastering draws;
    - rescales the backing to the same drawn ratio (the overall gain is unchanged);
    - is separated by X-LANCE gtr_mss on the MPS.
  - **The null** (amendment 1): the re-made original mix is separated the same way.
    - **Why:** 653 of V_sep's 1,721 stored stems were separated on the CPU, from rendered rather
      than FLAC-made mixes.
    - **The primary contrast** therefore compares two stems made by the same path.
- **1b, the read** (`rin-read`, descriptive, decides nothing). It reads **F**, step 3's D_stem: all
  3 seeds, with the 20261042/20261043 pair beside.
  - **How:** amendment 5's A1+A2+A3, masked E, with step 3's stored constant and pull. Model
    hashes are checked against `full/readout.json`.
  - **What it reports:**
    - **primary:** rebuilt − re-separated original per example, on the same rebuilt examples,
      band-clustered, with a section-clustered reading beside;
    - **the null:** re-separated original − stored original;
    - **beside:** rebuilt − stored original;
    - F − constant on the untouched trusted R_in;
    - F − constant on the trusted R_in (untouched and rebuilt);
    - F − constant on the rebuilt examples (both stems), the untrusted examples as stored, and R_in
      as stored (step 3's reading).

### Step 2: the trusted retrain (declared here, launched separately)

- **Arm T:** D_stem on the rebuilt trusted pool.
  - **Same as before:** the same examples, DI sections, labels and level, vocals, loudness and
    mastering draws.
  - **Changed:** each untrusted section's backing loses its removed tracks, and X-LANCE re-separates
    into a new root. The old stems stay untouched.
  - **The early-stopping set** is rebuilt the same way.
  - **Recipe:** step 3's, unchanged, at the same N, so the optimisation steps are equal. Seeds
    20261042 and 20261043.
  - **Training targets need renders**, about 0.94 per example plus priming; no audio was kept.
- **Reference F:** step 3's seeds 20261042 and 20261043, with the pull b refitted on the trusted
  early-stopping set. F's checkpoints were chosen on the old early-stopping set; that is a declared
  mismatch.
- **The test set: R_in trusted.**
  - **Doubled examples** (a removed same-part track with its own DI in the library) are rebuilt
    with **consistent doubles**: the partner DI is rendered at the example's label settings and
    placed at the original track's section level. That takes about 374 renders plus priming.
  - **Every other untrusted example** uses step 1's rebuild.
- **Co-primary readouts** (masked E, A1+A2+A3 over 2 seeds × 2 halves, paired per example,
  band-weighted, 90% band-clustered t):
  1. **T − F on the untouched trusted R_in examples.** Identical inputs for both arms; nothing
     rebuilt.
  2. **T − F on the whole trusted R_in.**
- **Beside them:**
  - each arm's seed difference (the noise floor);
  - contamination terciles, level bins and class;
  - R_out on the trusted examples.
- **The sound gate,** only if either co-primary E interval excludes 0:
  - **Renders:** T's answers on the trusted R_in. F's answers are re-rendered on the rebuilt
    examples, whose stems changed; F's stored renders are reused on the untouched ones. Truth and
    constant renders are reused.
  - **Reading:** T − F on the gate's statistic.
- **If the route is "drop":** T drops the untrusted examples, and the epoch cap is scaled to equal
  optimisation steps.
  - A size-matched random control is used only if the user declines the rebuild's renders and more
    than 5% is untrusted: same count, within band × level bin, `random.Random(20261096)`.

### Step 2's data: the candidate-driven pool rebuild (built; no training)

The user listens to the suspected doubles first (2026-10-23 morning), so the pool rebuild is driven by
an editable candidate list. A verdict can then rebuild, or stop using, exactly the difference.
- **`pool-candidates`** turns step 0's removals into `candidates.json`, one entry per (DI, track,
  kind):
  - **Guitar-class doubles** (pitch-confirmed same-part guitar tracks): `rebuild: true` until a
    verdict says otherwise.
  - **Everything else is pending** (`rebuild: false`, no verdict): non-guitar doubles (a
    riff-following bass or keys track can pass the pitch test; amendment 1) and live-room takes.
  - **A pending candidate excludes its examples.** They are neither rebuilt nor read as original
    until a verdict either keeps the track (`rebuild: false` with a verdict) or switches it on.
  - **Each entry lists:** its sections, the per-section evidence (chroma, onsets, power, both take
    readings) and the pool and R_in examples it touches.
  - **Verdicts are safe:** it never overwrites an existing list; a fresh one goes to
    `candidates-new.json`.
- **`pool-rebuild`:** for every pool example whose backing variant loses a switched-on candidate
  track, it:
  - **re-renders the guitar** (knob_ceiling's renderer, isolate=True, primed per section and amp, at
    most 3 render processes machine-wide; `local_objective.RENDERS` counts it);
  - **checks the original mix** against the stored one (99% of cells, LUFS within 0.01), or refuses
    the example;
  - **rebuilds the mix** without the tracks, as in step 1 (same draws, backing rescaled to the drawn
    ratio);
  - **separates** with X-LANCE.
- **Storage:**
  - Files go to `pool/build/ex/…-mix-<key>.npz` and `…-xlance_g-<key>.npz`, where the key names the
    removed tracks; rows go to `pool/rows/`.
  - The D build's original files are never touched, and no rebuild overwrites another.
  - Two workers (MPS ascending, CPU descending) meet in the middle.
- **`pool-status`** compares the list with what is built:
  - **to build:** wanted, not yet built;
  - **current:** built under the wanted key;
  - **stale:** built under a key no longer wanted. The files are kept, and the example reads its
    original again.
  - **excluded** (amendment 1): a refused rebuild, or an example a pending candidate touches. Arm T
    never reads these, as original or rebuilt.
  - It writes `pool/manifest.json`, the file list arm T would read. Arm T needs it complete, with
    nothing left to build.
- **Nothing here trains.** Arm T waits for the verdicts and its own launch.

### What each outcome means

| Reading | Meaning | Next |
|---|---|---|
| **0a INJECTION FAIL** | The estimator cannot enforce −30 dB on some backings | Stop; review the estimator or the threshold; no lists are used |
| **Step 1: rebuilt − original below or above 0** | Test-side dirt moved step 3's reading | The trusted reading becomes the record |
| **Step 2: T − F below 0** | Training-side dirt was costing accuracy | T is the baseline; the same-part and take rule goes into `backing_tracks` for every future build |
| **Contains 0** | Not shown at this power | T is still the baseline (the user's rule); the open levers are buried guitars and separator residue |
| **Above 0** | The removed tracks were helping as realism | Revisit with the user; consistent doubles in training are the next arm |

### Budget and launch

The run order and expected times:

```
MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
MSST=~/ndsp-presets/tools/msst-venv/bin/python; TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
$MAIN -m learn.data_cleaning inject                                # 0a: about 10 min CPU (6 sessions)
for k in 0 1 2; do nice -n 10 $MAIN -m learn.data_cleaning scan --shard $k/3 & done; wait   # 0b: about 1-1.5 h
$MAIN -m learn.data_cleaning lists                                 # 0c: under a minute; then review
$MAIN -m learn.data_cleaning pool-candidates                       # seconds; listen, edit verdicts
$MSST -m learn.data_cleaning rin-rebuild --device mps              # 1a: about 10 s per R_in example (2 separations)
$TORCH_PY -m learn.data_cleaning rin-read                          # 1b: about 3 min CPU
$MSST -m learn.data_cleaning pool-rebuild --device mps --order asc  # 2 data: renders + X-LANCE
$MSST -m learn.data_cleaning pool-rebuild --device cpu --order desc # optional second worker
$MAIN -m learn.data_cleaning pool-status                           # 2 data: the difference; the manifest
```

| Item | Renders | Separations | GPU / MPS | CPU |
|---|---|---|---|---|
| 0a inject | 0 | 0 | 0 | about 10 min (6 sessions, about 1.5 min each; 2 GB) |
| 0b scan | 0 | 0 | 0 | about 3 h single, about 1–1.5 h on 3 shards (about 4 GB each) |
| 1a R_in rebuild | 0 | 2 per example (rebuilt and re-made original), about 10 s an example: about 1 h for 374, up to about 4 h for all 1,407 | MPS | — |
| 1b read | 0 | 0 | 0 | about 3 min |
| 2 data: pool rebuild of the confirmed doubles (about 1–3.2k examples, set by step 0) | one per example plus priming | 4.3–5 s per example on the MPS alone (1.2–4.5 h); about 0.35 examples/s with the CPU worker (0.8–2.6 h) | MPS | — |
| 2 training-pool rebuild, all untrusted, v0 (about 3.6k) | about 3.6k | 4.3–5 h MPS alone, about 2.9 h with the CPU worker | MPS | — |
| 2 rebuild, upper (about 13.4k) | about 13.4k | 16–19 h MPS alone, about 10.6 h with the CPU worker | MPS | — |
| 2 consistent doubles (R_in) | about 374 plus priming | counted in 1a's re-separation | — | — |
| 2 training (T, 2 seeds) | 0 | 0 | 2.3–2.6 h | — |
| 2 gate, only if E moves | about 1.4k for T plus F's rebuilt examples, plus priming | 0 | — | — |

- **Machine:** at most 3 render processes machine-wide; steps 0–1 render nothing.
- **Disk:** guard 31 GB, plus memory and swap guards.
- **Held-out data:** none touched.

### Smoke (development, decides nothing)

The smoke runs used scratch directories only.
- **0a on the 4 development sessions:**
  - close mics (snare) read −20.8, −25.9 and −31.2 dB for −20, −25 and −30 injected;
  - a loud drum-room mic read −20.9, −26.5 and −34.4;
  - no uninjected target, and no other non-guitar track, read ≥ −35 or ≥ −30 dB.
  - That would read FAIL on these 4 (3 of 4 at −30 dB). The declared check uses the other 13
    sessions.
- **How the settings were chosen.** The 250-Hz floor, per-bin weights, ridge 0.3, session folds
  and near nulls were chosen there.
  - **Drops 1 and 2:** per-section fits read musical phase-lock (kick against palm-mutes, other
    guitars) as take at −22 to −31 dB.
  - **Drop 3:** far (±30 s) nulls missed a room mic's offset.
- **0b on 4 DIs:**
  - **Ale Lak ElecGtr02:** its double 02DT was confirmed by pitch (chroma 0.93–0.98) and removed.
  - **Adam Buckley ElecGtr3:** ElecGtr2 and 2DT follow its onsets (0.53–0.71), but play other notes
    (chroma 0.05–0.21). They were not confirmed and not removed; the audit's "same riff" there was
    onsets only.
  - **Adam Buckley ElecGtr2:** its named double 2DT failed pitch (0.50) but read a take of
    −24.1 dB and was removed.
  - **Swatkins "Honey":** removed Close Rooms (−19.6), Mono OH (−22.4), OH, a keys DI and both
    vocal mics. The amp-source upper bound bites in live rooms; the DI-source reading is in the
    lists for review.
- **1a on 3 Adam Buckley examples:** the re-made original mixes matched the stored ones (cells
  1.0, LUFS within 2×10⁻⁶).
- **1b:** F − constant on R_in as stored read −0.0159 [−0.0363, +0.0046], exactly step 3's
  reading. The read path is right.
- **After amendment 1:**
  - **0a on the deciding session Hollow Ground:** 9 targets (2 room or overhead) read back at
    −20.7 to −20.9, −25.7 to −25.9 and −30.5 to −31.0 dB, and every uninjected target read under
    −50 dB. The session passed (84 s, 1.9 GB).
  - **1a/1b with Adam Buckley's takes switched on in a copy of the list:** 2 examples, about 10 s
    each.
    - The null (re-separated − stored original) read −0.0000 and the rebuilt contrast +0.0013,
      both on 2 examples.
    - Swatkins' 125 examples were excluded by their pending takes.
- **Step 2's data:**
  - `pool-candidates` listed Ale Lak's 02DT as a double: 154 pool examples, chroma 0.98 and 0.93.
  - `pool-rebuild` rebuilt 3 of them with 4 renders (1 priming); the original mixes matched the
    stored ones (cells 1.0).
  - Switching the candidate off in a copy of the list turned those 3 stale (read as original), and
    switching it back made them current again.

### Limits

- **The amp-source take is an upper bound in live rooms.** A live amp track's drum and keys bleed
  can pose as take, so live-room backings may lose drum, keys and vocal mics. The DI-source reading
  and the per-class counts are reviewed before use.
- **The near nulls can absorb a true take** when a part repeats sample-exactly every 2 or 3 s
  (programmed loops). Human playing does not.
- **The estimator's settings were developed on 4 DIs from 3 sessions.** Only the other 3 sessions
  decide the check (amendment 1). That is few sessions, all studio overdubs; live-room estimation is
  untested by injection.
- **Consistent doubles** exist only where the partner part has its own DI.

## Amendment 1 (2026-10-22, code review): the injection check votes per session

Declared before any real run, from PR #273's code review ("go with fixes"). Only fix 1 changes the
plan. Fixes 2–7 make the code match the plan, or fail closed where it did not.

1. **The injection check was not independent.**
   - **The problem:**
     - The first draw took 12 DIs from only 6 sessions, and 7 of them shared a session with the
       4 development DIs (Ale Lak, Death Of A Romantic, Storm Of Particles).
     - The target was the loudest drum track, mostly a close mic, while room mics are the failing
       case.
   - **Now:**
     - one DI per session;
     - the take injected into every drum, room and overhead track;
     - a vote per session, with room and overhead targets voting on their own;
     - only Hollow Ground, Rebuild The Evil and The Long Wait deciding, and the development
       sessions read beside.
   - The plan, the code and the ledger no longer say "12 sessions".
2. **Fail closed:**
   - `inject --dev` runs only as a smoke;
   - `inject` never overwrites a record, so a FAIL stays;
   - `scan` checks the record's rule, estimator, deciding sessions and their DIs, and re-checks the
     stored readings.
3. **No dirty fallback:** a refused rebuild, and any example a pending candidate touches, is
   excluded in the manifest (and from the trusted R_in), never read as original.
4. **R_in follows the verdicts:** `rin-rebuild` and `rin-read` take the same candidate list as the
   pool. Files are keyed by the removed tracks, and stale or missing rows are refused.
5. **Step 1's null:** the re-made original mix is separated by the same path as the rebuilt one.
   Rebuilt − re-separated original is primary, and re-separated − stored original is the null.
6. **Guards:** `scan` stops on the disk, memory and swap guards (`direct_stems._guards`), as the
   plan promised.
7. **Doubles on by default are guitar-class only.** Bass, keys and other doubles start pending.

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
