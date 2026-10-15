# Settings from a song: three arms, one comparison: plan (ML plan 2026-10, step 3)

Declared 2026-10-15, before any step-3 compute. Revised the same day after an independent review
(`tmp/song-settings-plan-review.md`, local): approved with changes, all folded in. Deviations
from the ML plan are listed at the end. It is step 3 of
[`research/ml-plan-2026-10.md`](research/ml-plan-2026-10.md), which sets its design. This file
makes it concrete: the code, the numbers, the fold map and the order. Development data only.
The user approved step 3, with its render, CPU and MPS budget (decision 3).

## The question

With only the song (a separated guitar stem), how much of the true-DI knob search's gain (K_S
against S) can each method reach? K_S against S is −0.253 part-weighted on these cells; the
bars use its band-weighted figure on the per-part unit (below).
- **Arm A:** rebuild the DI with C′, then search the plugin.
- **Arm B:** predict settings directly with a model trained on plugin renders.
- **Arm C:** arm B's prediction as the start of a short arm-A search.

## Shared

- **Cells:** knob ceiling's 24 scored parts × 3 amps, 14 bands, both directions (search half to
  held half), asserted in code. Honey stays out (its half B is refused).
  - **They are optimistic:** they were picked for clean stems (≥ 1 dB SNR).
  - **Reported with and without MUSDB18-train songs:** Atlantis Bound and Wall Of Death.
- **Input:** the part's 10-s stem from the songs check (`learn/poc/stems/htdemucs_6s/<part>/
  instrumental_guitar.wav` for sets 1–2, `learn/set3/stems/htdemucs_6s/<part>/…` for set 3).
  - The stems come from the instrumental context, so there are no vocals. That is a known
    optimism, stated.
  - The mix input for arm B is the crop's `mix_instrumental.wav`.
- **Output space:** knob ceiling's `space(amp, S)` on top of S:
  - **searched or predicted:** input gain (−20 to +12 dB), the amp's knobs and switches, both
    mics, cab position and distance, the right mic's level and switch;
  - **kept from S:** pedals, EQ, rooms, pan, phase and the amp.
- **Score:**
  - the arm's settings rendered through the **measure DI** (`isolate=True`);
  - the judge on the **held half:** `knob_ceiling.judge` against the part's `reference.wav` at its
    judge lag;
  - **a refused held half** (the judge returns no distance) drops that direction for every arm
    and comparator alike, and the count is reported;
  - the log ratio against S, per part: the mean of the two directions and the three amps;
  - band-weighted with a band-clustered 90% interval, leave-one-band-out, and clean and crunch
    apart;
  - every arm against arm difference paired, with its interval.
- **Comparators:**
  - **S;**
  - **K_S:** knob ceiling's stored result, the same space, 150 renders, true DI (one seed, a lower
    bound). It is shown at 50, 100 and 150 renders beside each arm;
  - **M;**
  - **the C′ menu pick, per amp:** C′'s stem-rebuilt DI choosing among the 111-preset menu by
    `rebuilt_distance` on the search half. Its held score comes free from step 4's stored menu
    scores (`learn/label-table/<part>/menu.json`, the same measure DI). It costs about 2.7k
    renders, through the rebuilt DI, for the choosing.
  - The per-fold menu-pick figure that step 1 promised is reported here.
- **v3:**
  - **S, M and the menu pick:** from step 4's `menu.json`, which stores `flat` and v3;
  - **K_S and every arm:** each best is re-rendered once and scored under v3, about 144 renders
    per method.
- **First, at zero renders:** K_S's held-half convergence at 25, 50 and 100 renders, from each
  cell's stored curve, reported before any arm runs.

## Folds (declared; asserted in code)

1. **K3 bands keep their fold** (`learn/train.py` `k3_folds()`, folds 0–3). Arm B's fold f and
   C′'s fold f then leave out the same bands.
2. **Every other development band** that gives a DI, a backing or a label (set 3, and the sets
   1–2 bands outside K3) gets a fold by a declared draw: sorted names,
   `random.Random(20261016).shuffle`, then i mod 4.
   - **A band already in K3 keeps its K3 fold,** even when it also appears in set 3: Eat The
     Feeder is K3 fold 2 and has 6 set-3 parts.
   - **The draw replaces set 3's own `fold` column** for this step.
   - The code asserts that every band maps to exactly one fold.
   - The band → fold map is written to `docs/song-settings-folds.json` and committed before any
     training.
3. **Sources never evaluated may train every fold:** Guitar-TECHS P1 and P2 (P3 is held out and
   never read).
   - **Five-guitar is excluded:** its "DI" is the DI output of a DV Mark Little Jazz amp, which
     has not been verified dry (`docs/research/di-riffs-and-part-classifier-2026-10.md`).
4. **The fold-f model and network** train on no render, backing or K_S optimum from a fold-f band.
5. **Every evaluated part's band** is in folds 0–3 (asserted).

**For arm A:** each part is rebuilt by the C′ of its own fold, as above. Set-3 parts were never in
C′'s training data (`learn/di_pool.py` reads set 2 and P1 only). They use the fold the draw gives
their band, so arms A, B and C read each part with the same fold. The code asserts that neither
the part's band nor its backing is in that C′'s training pool or bleed.

## Arm A: rebuilt-DI search (about 28k renders)

- **Rebuild:** the part's fold's C′ (`models-cprime-f{f}/fold{f}.pt`, or fold 2's
  `models-cprime/fold2.pt`) rebuilds the DI from the whole 10-s stem.
  - The pattern is `learn/residual_eval.py` `rebuild`: `direc.rebuild` on the CPU, with **no**
    3-kHz low-pass.
  - **Re-equalised to the measure's balance:** C′ for fold f rebuilds at fold f's average-guitar
    balance (`average-fold{f}.npy`), but the measure DI, every score and K_S use fold 2's. Each
    rebuild is re-equalised by (fold 2's average − fold f's) with `eq_to`, then `to_lufs` to
    −22.9 LUFS.
    - Without this, folds 0, 1 and 3 would carry a fixed tilt of up to about 3.5 dB, which
      can't be told apart from C′'s quality.
    - The same applies to the known-target control and the C′ menu pick.
  - `songs_check.build_di` is not used.
- **Search:** `knob_search` from S, 150 renders per direction, seed 20261013 (K_S's).
  - **Objective:** `rebuilt_distance(stem, render, rebuilt_di)` on the search half (lag −52).
  - **Recorded:** how often its activity fallback fires.
  - The search's best is then rendered once through the measure DI and scored as above.
- **Known-target control (about 3.6k renders, run first):**
  - **Cells:** 12. 6 bands are drawn with `random.Random(20261016)` from the 14, with at least 2
    crunch bands; then one part per band, by the same generator. × PR12 and SW50R.
  - It is a pipeline check: its "recording" is a clean render, which is C′'s training domain,
    not a stem.
  - **The "recording":** S with five settings moved (knob ceiling's realistic-control moves),
    played through the part's own raw DI.
  - **Two runs** at 150 renders: one scored with the measure DI, and one with C′'s rebuild of
    that recording (the fold's C′).
  - **Measures** on the held half: the gap closed, and the shortfall log(d_found / d_target).
  - **Read in order; the first match wins:**
    1. The measure-DI run closes ≥ 50% of the gap on fewer than 8 of 12: the set-up is wrong. Stop
       arms A and C.
    2. The rebuilt run closes ≥ 50% on ≥ 8 of 12, or its mean shortfall is within 0.03 of the
       measure-DI run's: the control passes.
    3. Otherwise: arms A and C count as failed.
- **Step 1's network check** must pass for every fold used (`docs/cprime-folds-plan.md`, check
  2). A failing fold stops arms A and C.

## Arm B: direct settings model (about 11k renders)

**The training bank.**
- **Renders:** 10k, `knob_ceiling.Renderer` with `isolate=True`, 10-s clips at 48 kHz.
  - **Each render:** an amp and its class start S (one of the six), with settings drawn in
    `space(amp, S)`.
  - **Broad half:** uniform on the 0–1 scale; uniform mics and switches.
  - **Jittered half:** around the six S, and around other folds' K_S optima (σ 0.1 on the 0–1
    scale; mics kept with p 0.7).
  - K_M's optima are not used.
- **DIs:**
  - the DIs of the 76 classed development parts' **sessions**, as random 10-s windows from the
    full-length DI tracks, meaning the catalogue's `di` file for each part;
  - plus Guitar-TECHS P1 and P2;
  - each window active (the DI within 40 dB of its loudest frame in ≥ 60% of 100-ms frames).
  - **Treatment:** the measure DI's (average-guitar equalisation, −22.9 LUFS), with an array
    version of `confirm_run.build_di`'s steps. So a label's input gain means what K_S's does.
  - The fold rules apply to each window's band.
- **Every example's sources come from one fold** (so no fold loses half its bank): its backing,
  its second guitar and its K_S jitter centre are drawn from the DI's own fold. Every example is
  tagged with all its source bands, and the fold-f model's exclusion is asserted.
- **Labels:** the drawn settings. **No judge is used in training.** The model is scored on sound,
  never on knob error.
- **The first 0.25 s** of every render is trimmed (the `isolate` fade-in).
- **Augmentation after rendering, at no extra renders:**
  - mix into a **other-fold** development crop's `backing_instrumental.wav`, at a
    guitar-to-backing level drawn from the development mixes' measured levels (reference against
    backing, LUFS, measured first);
  - with p 0.3, a second guitar: another bank render, 3–9 dB down;
  - **Mastering on only half the bank:** bus compression (ratio 2–4, numpy), a limiter to −1 dBTP,
    and, with p 0.5, AAC at 128–256 kbps (`afconvert`). The evaluation mixes are unmastered
    unity sums, so half the bank stays unmastered. Their loudness is measured first and the
    bank's levels are matched to it.
  - **Separation:** htdemucs_6s (`learn/separate.py`'s `GuitarSeparator`, in process, writing
    16-bit FLAC) on about half: 5k separations from the 10-s mixture. The evaluation stems come
    from 30-s contexts, which is stated as a gap. On the unseparated half, the "stem" input is the
    clean guitar render itself, mixed at its backing level.
- **Size and disk:** about 10k renders as 16-bit FLAC (about 6 GB), and features cached as float16
  (about 5 GB). Built after step 1's caches are deleted, which happens only after step 1's network
  check passes for all three new folds.

**The model.** It starts from the proof of concept's body (`learn/train.py` `build_model`), with
these changes:
1. **The front end keeps the level:** log-mel without loudness normalisation, plus the stem's and
   the mix's LUFS as side inputs.
2. **Features** are computed on the CPU and cached.
3. **Two inputs, stacked as 2 channels:** the stem's and the mix's log-mel.
4. **The amp and the class start** as a one-hot (6) into the trunk.
5. **Heads:**
   - **categorical:** softmax per mic slot (10) and per switch;
   - **continuous:** a **mixture-density head** (4 diagonal Gaussians on the 0–1 scale). To output
     one preset, take the heaviest component's mean, and each categorical's top choice.
   - **Settings that differ by amp** (each amp has its own knobs): one shared head covers the
     union of every amp's settings, and the loss masks the settings that don't exist on the
     example's amp.
6. **Arm B sees the search half only:** it reads the search half of the stem and mix (4.5 s,
   zero-padded to the clip). Its two directions are then two predictions, and it never sees the
   held half, as K_S and arm A don't.

**Training:** per fold, Adam at 1e-3, batch 64, at most **40 epochs**, on MPS (when step 1 is
done). Early stopping uses a 10% validation split, split by band among the fold's training
bands. Fold 0's first epoch is timed, and the time is reported. The loss is the MDN negative
log-likelihood plus cross-entropy, with gradients clipped by hand.

**A data-limit check, at no renders:** each fold is retrained on 50% of its bank. If the full bank
beats the half-bank by more than 0.03 band-weighted, a failing arm B reads "undecided
(data-limited)", not "failed".

**Diagnostics, at no renders:**
- the share of predictions within 0.1 (on the 0–1 scale) of S, or of a jitter centre;
- the heaviest component's weight;
- the mixture mean against the heaviest component's mean.

**Positive control** (about 0.5k renders, before anything real), per fold:
- **The targets:** at least 30 planted settings on an S, rendered through the fold's held-apart
  DIs (P1 and P2 windows not in training), mixed, mastered and separated as in the bank.
  - The planted settings are drawn like the bank's broad half.
  - A target is kept only if d_start − d_target ≥ 0.1, so there is a gap to close.
- **The scoring:** the prediction, the planted settings and the median of the fold's training
  labels, each rendered through the *measure* DI and judged against the clean planted render's
  held half. d_target is the planted settings' score, and d_start is S's.
- **Pass:** gap closed ≥ 50% on ≥ 2/3 of targets, **and** closer than the median settings on
  ≥ 2/3. At most two fix-and-re-runs.

**Controls (144 renders each unless stated):**
- **shuffled input:** 3 stems from other bands **in the same fold**, the same amp and class, so the
  model has seen none of the inputs (432 renders). It passes if, band-weighted, arm B against the
  shuffled mean is ≤ −0.05, **and** arm B is better in ≥ 60% of bands;
- **a song-blind constant:** the median of other folds' K_S optima per amp and class;
- **the amp track instead of the stem;**
- **prediction spread against label spread,** per continuous setting.

**The single-answer amp** (product-like, reported beside the per-amp results): every arm's result
on the amp whose S is best on the search half (S's own search-half score, no held half). Arm B
against the song-blind constant is reported paired in the readout.

## Arm C: combined (about 7.2k renders)

Arm B's prediction is the start of `knob_search` with arm A's objective, at 50 renders per
direction. If arm C leads at the readout, a separate 150-render run follows (step 6 of the ML
plan).
- At 50 renders, its mic-alternatives stage gets about one render per option.
- It is compared with K_S at 50 renders as well as at 150.

## Pass rule for each arm (declared now; entered in the ledger)

Held half, band-weighted, on step 3's cells, against S:
1. better than S by **at least 0.03**, **and** at least **40%** of K_S's band-weighted gain on the
   same cells, on the per-part unit (the mean of 2 directions × 3 amps);
2. better than S in **≥ 60% of bands;**
3. neither clean nor crunch worse than S by **more than 0.05** (crunch has 5 bands: a harm guard);
4. **arm A only:** not worse than the C′ menu pick by more than 0.01;
5. **arm B only:** its positive control and its shuffled-input control both pass.

At 14 bands the standard error is about 0.026, so every figure is shown with its 90% interval.

**The readout** follows the ML plan's step 6 table: the first match wins, and the leader is the
passing arm with the best band-weighted mean. Ties within the paired 90% interval go to the
cheapest per cell (B 1, C 51, A 150).

## Order and budget

1. This plan, a review, the ledger entry, the fold map, then a message to the product session.
2. K_S's convergence (zero renders).
3. **While step 1 trains:** arm B's DI windows and the evaluation mixes' loudness (CPU). The bank
   renders once step 1's check passes and its caches are deleted. Arm A waits for that check too.
4. Arm A's known-target control, then arm A and the C′ menu pick.
5. Arm B: separation, features, training per fold, the positive control, then scoring and
   controls.
6. Arm C.
7. The readout, an audit, and `docs/song-settings-results.md`.

| Arm | Renders |
|---|---|
| A (with its control and the C′ menu pick) | ≈ 28k |
| B (bank, control and scoring) | ≈ 11k |
| C | ≈ 7.2k |
| **Total** | **≈ 46k** |

The running total is about 70k (knob ceiling) + 15.7k (step 2) + 6.5k (step 4) + 46k ≈ 138k,
against the 200k limit.

**Wall clock:** at about 2 renders/s on 4 processes once steps 2 and 4 are done, 46k renders is
about 6–7 h, plus about 7 h of CPU separation and 4 × 1–3 h of training.

## Deviations from the ML plan

- **The part counts:** 76 classed parts, not 82 (step 4's derivation).
- **Five-guitar is excluded:** its DI isn't verified dry.
- **C′ rebuilds are re-equalised to fold 2's balance:** this is new, and corrects a tilt between
  folds.
- **Arm B's inputs:** the search half only, with 2 channels (stem and mix) for "how well the two
  agree".
- **The single-answer amp** is the one whose S is best on the search half.
- **Fold 0's first epoch** is timed after this declaration, not before.

## Stated limits

- **The stems are optimistic:** SNR-selected, instrumental, development parts.
- **S was chosen on these parts,** so gains against S are understated. 5 of the 24 parts are from
  "the 33".
- **K_S is one seed at 150 renders,** a lower bound.
- **Crunch is 5 bands:** descriptive.
- **The judge's taste for extremes:** listening is the guard at the readout, with a blind page on
  the leader.
- **The output space excludes pedals, EQ and effects** (step 2 found them small or undecided), so
  a "complete preset" here is S's pedals, EQ and effects plus the arm's knobs.
