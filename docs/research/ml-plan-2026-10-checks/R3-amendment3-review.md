# R3: Adversarial review of Amendment 3 and the ML session's work order

Reviewed 2026-10-14 against commit `4d22d5e` on `claude/new-session-22s984` (main's knob
ceiling, render-order audit and isolation checks merged). Scope:

- `docs/research/ml-plan-2026-10.md` "For the ML session: what to implement, in order" (L53–78)
  and "Amendment 3" (L82–282);
- `docs/README.md` research items 6–7 (L337–345);
- `docs/ROADMAP.md` step 0, the ML-plan paragraph (L90–102).

No repository file was edited.

**Shorthand:** `L123` = `docs/research/ml-plan-2026-10.md` line 123. `KCP:n` =
`docs/knob-ceiling-plan.md`, `KCR:n` = `docs/knob-ceiling-results.md`, `PoCP:n` =
`docs/preset-model-poc-plan.md`, `PoCR:n` = `docs/preset-model-poc-results.md`.

---

## Verdict

**The direction is sound, but the work order is not yet safe to hand to the ML session.
16 required fixes.**

**What holds:**

- making B4 a main-line arm beside B3;
- scoring every arm on K_S's cells, start, space and held half;
- the disk ordering (A6 before the bank);
- most repo facts and most of the arithmetic.

The knob-ceiling numbers (−0.253, −0.205, −0.130 at 25; 24 parts × 3 amps in 14 bands), the K
table, the six dry starts, the 82 classed parts, Guitar-TECHS P1–P2 being local development
material, B3 ≈ 26.2k, A7 16k/40k, ≈ 51k and ≈ 141k all check out.

**What fails:**

- **One number is misread by 4×.** The proof of concept's "about 10 hours for 30 epochs" is
  four folds, not one. The B4 training estimate is built on that misreading.
- **One PoC finding is mis-sourced and over-generalised** (EQ 0.96–1.04, drive 0.97).
- **The PoC's own strongest evidence against a direct model is missing:** a known tone curve buys
  about 5%, the judge's aligned comparison about 20%.
- **The leak claim can't hold under the fold scheme it cites.** `k3_folds` puts set 3 and every
  other non-K3 band at fold −1, and fold −1 trains every fold. Five of the 24 evaluated parts are
  set 3, and their own DIs would be in every B4 model.
- **B4 is under-specified in ways that change results:**
  - it isn't told which class start its output sits on;
  - it can jitter around K_M optima, which sit on another base;
  - it has no DI or level convention;
  - it has no amp choice for the top-1 readout;
  - its positive control has no defined d_target.
- **B5's budget assumes `knob_search` can be extended from 50 to 150 renders.** It can't.
- **The readout table is neither exclusive nor complete.** It also contradicts §0.4's control
  readings, and its "best" can't be resolved at 14 bands.
- **The budget leaves out A5,** which is in the work order. After the readout the plan crosses
  200k.
- **Hidden dependencies:**
  - B3's control needs A5;
  - B3, B4 and B5 need decision 3 and the development ledger, which only A3 creates.
- **Several code pointers would mislead:**
  - `render_job.py` doesn't isolate;
  - `pr12.py` and `train.Frontend` are PR12-only and loudness-normalised;
  - `score_shortlists.py` is A4's code, not A3's;
  - `songs_check.build_di` applies the retired lowpass and the old networks;
  - the separation script isn't committed.

---

## Required fixes

### 1. Training time: the PoC's "10 hours" is four folds

- **Text (L176–178):** "The proof of concept measured 1.3 s per batch, about 5 h per fold for 15
  epochs on 20k renders [P, `docs/preset-model-poc-plan.md:115-117`]. So the pilot is about 2.5 h
  per fold, about 10 h for 4 folds [I]."
- **What's wrong:** the source says "30 epochs would take about 10 hours on this machine (1.3 s per
  batch)" (PoCP:115–117). That is the four folds together.
- **Evidence:**
  - Batches are 64 (`learn/train.py:229`). An epoch is one pass over the fold's training renders
    (`train.py:230,269`), which are those outside the fold (`train.py:218-219`): about 14–15k of
    18,843 (PoCR:5).
  - That is ≈ 220–240 batches × 1.3 s ≈ 5 min per epoch, so 30 epochs ≈ 2.5 h per fold and ≈ 10 h
    for four. Ten hours per fold would need ≈ 59k samples per epoch, three times the whole bank.
  - The declared 15 epochs were therefore ≈ 1.2 h per fold.
  - The 1.3 s was also measured with features on the device (`train.py:10`, `Frontend` on MPS).
    B4 computes them on the CPU, so the figure transfers only if features are precomputed.
- **Corrected text:** "**Training time.** The proof of concept trained in batches of 64 on the
  renders outside each fold (≈ 14–15k). At 1.3 s per batch that is ≈ 5 min per epoch; its
  'about 10 hours' for 30 epochs is the four folds together, and its 15 epochs took ≈ 1.2 h per
  fold [P, `docs/preset-model-poc-plan.md:115-117`; `learn/train.py:218-230`; I]. The pilot
  (≈ 7.5–8k training renders per fold) is ≈ 40 min per fold at 15 epochs with one view. Allow
  about double for the two views or 30 epochs: ≈ 0.7–2.6 h per fold, 3–10 h for four [I].
  Precompute the CPU features before training, and time fold 0's first epoch before declaring."

### 2. The EQ/drive figures are from an early one-fold diagnostic, and only EQ and drive failed

- **Text (L108–113):** "[P, `docs/preset-model-poc-results.md`] … **It did no better than the
  median on unseen players, even on renders:** EQ 0.96–1.04 of the median baseline's error, drive
  0.97."
- **What's wrong:**
  - **Wrong source.** 0.96–1.04 and 0.97 aren't in the results file. They are the plan
    amendment's diagnostic: one fold, the first 7,007 renders (PoCP:118–123).
  - **Over-generalised.** On held-out-band renders the model *did* beat the median on:
    - mic type (75% vs 40%);
    - cab placement;
    - pedal knobs (0.76–0.85);
    - filters (0.72);
    - volume (0.79).

    Only the EQ bands and input gain stayed at the median (PoCR:62–64; PoCP:121–123).
- **Corrected text:** "**On held-out-band renders it matched the median only on the EQ bands and
  input gain** (early one-fold diagnostic: EQ 0.96–1.04 of the median baseline's error, effective
  drive 0.97 [P, `docs/preset-model-poc-plan.md:118-123`]; the final models the same
  [P, `docs/preset-model-poc-results.md:62-64`]). It did learn mic type (75% against 40%), cab
  placement, the pedal knobs and the filters. K keeps the mics and cab it learned and the input
  gain it didn't. The EQ stays at S."

### 3. "Menu-limited target" is wrong, and the PoC's follow-up evidence is missing

- **Text (L117–119):** "**The room is large.** … The proof of concept was judged against a
  menu-limited target." **Also (L174–175):** "The proof of concept's warning still applies: score
  the model on sound, never on knob error."
- **What's wrong:**
  - **The PoC's bar wasn't menu-limited.** It was log 0.9 ≈ −0.105 against template+R (PoCP:49–52),
    about B4's −0.10, and it reached −0.037 (PoCR:18). The menu oracle (−0.27/−0.22) was reported
    beside the result, not used as the target (PoCP:55–56).
  - **The project's most direct evidence against a stem-only model is missing.** The PoC's
    follow-up found (PoCR:90–114):
    - choosing settings from a *perfectly known* long-term curve buys about 5%;
    - choosing by the judge's aligned comparison buys about 20%;
    - "what carries the value is the judge's aligned, moment-by-moment comparison, which needs the
      take's DI".

    K_S is exactly that kind of search, and B4 can't use it.
  - **The "warning" is misquoted.** The PoC's lesson 1 was "Train on the sound, not the knobs"
    (PoCR:73–75). B4 trains on knob labels, which departs from that lesson and should say why.
- **Corrected text:**
  - Replace the L118–119 sentence with: "The proof of concept's own bar (≈ −0.105 against
    template+R) was already this size, and it reached −0.037 [P, `preset-model-poc-plan.md:49-52`;
    `preset-model-poc-results.md:18`]. What is new is evidence that *settings*, not presets, reach
    −0.25 with the true DI."
  - Add to "Why a direct model is hard": "**The project's own follow-up points to the DI.**
    Settings chosen from a perfectly known long-term curve bought about 5%, and choosing by the
    judge's aligned comparison about 20%. 'What carries the value is the judge's aligned,
    moment-by-moment comparison, which needs the take's DI' [P,
    `docs/preset-model-poc-results.md:90-114`]. K_S's −0.253 is such a search. B4 reads only the
    stem, so expect it below B3 unless song-condition training adds what the proof of concept
    lacked."
  - Replace L174–175: "The proof of concept's lesson was to train on the sound, not the knobs
    [`preset-model-poc-results.md:73-75`]. Its own follow-up capped that route (above), so B4 keeps
    knob labels and adds the mixture-density head against averaging. It is scored on sound, never
    on knob error."

### 4. B4 is not "the proof of concept's design with three changes"

- **Text (L147–149):** "Features are computed on the CPU. It is the proof of concept's design
  (`learn/train.py`), with three changes."
- **What's wrong:**
  - The PoC computed features **on the device** (`train.py:10`, `Frontend` at `:144-165`).
  - It **loudness-normalised** each crop, setting the active RMS to −20 dBFS (`train.py:11,156-161`).
  - Its labels are PR12-only (`learn/pr12.py`).
  - "Level-preserving", "CPU features", "K on three amps" and "class start as input" are further
    changes beyond the three listed. An ML session reusing `train.Frontend` as instructed would
    silently erase level.
- **Corrected text:** "**Backbone:** the proof of concept's 2-D CNN body (`learn/train.py`
  `build_model`) and its per-fold training loop, with these changes:
  1. level-preserving log-mel, with LUFS as a side input (the proof of concept normalised each
     crop's level, `train.py:156-161`; replace `Frontend`);
  2. features computed on the CPU and cached (it computed them on the device);
  3. labels in knob ceiling's K for three amps on the six starts (replacing the PR12-only
     `learn/pr12.py`);
  4. categorical heads plus a mixture-density head;
  5. the amp and class start as input conditions;
  6. two views."

### 5. The leak claim fails under `k3_folds`: give a concrete fold rule

- **Text (L157–159):** "Folds by band: one model per fold, never trained on the evaluated part's
  band, as in the proof of concept." **And (L196–197):** "**Leakage:** none. Folds are by band over
  every band in the bank, and each evaluated part is read by the fold model that never saw its
  band."
- **What's wrong:** "as in the proof of concept" means `k3_folds` with fold −1 in every fold's
  training.
  - **How `k3_folds` assigns folds.** It covers only the 11 bands of K3's PR12 panel
    (`train.py:51-56`; `kill-tests-pr12-results.md:25`). Every other band gets
    `fold_of.get(band, -1)` = −1, and `clip_fold != fold` puts fold −1 into **every** model
    (`train.py:218-219`).
  - **In the PoC this was harmless.** Fold −1 held only Guitar-TECHS and the 2 set-2 bands outside
    K3 (13 bands in the pool, PoCP:20), and none was evaluated.
  - **In B4 it leaks:**
    - the bank adds "every classed development part's DI (82 parts)", which includes set 3
      (`docs/research/ml-plan-2026-10-checks/A2-infrastructure.md:592-599`);
    - knob ceiling's 24 include set-3 parts (`learn/knob_ceiling.py:526`; R1: five of them);
    - `songs_check.parts()` gives set-3 parts `fold=None` (`learn/songs_check.py:85`).

    So those parts' own DIs would train every B4 model.
  - **B5 adds a constraint.** It needs the B4 fold and the C′ fold to leave out the same bands
    (`learn/residual_eval.py:38-55`).
- **Corrected text (replace L157–159's fold sentence and L196–197):** "**Folds (declared,
  asserted in code):**
  1. Bands in `train.k3_folds()` keep their fold 0–3, so B4's fold f and C′'s fold f leave out the
     same bands (B5 needs both).
  2. Every other development band that contributes a DI, a backing or a label is assigned to folds
     0–3 by a declared seeded draw: sorted names, a new seed, i % 4. That covers set 3 and the
     sets 1–2 bands outside K3's panel. The band → fold map is committed with the plan, before any
     training. Band names are normalised across `validation-datasets.json` and
     `validation-set3.json`, and asserted unique.
  3. Only sources that are never evaluated may train every fold: Guitar-TECHS P1–P2 as one band,
     Five-guitar as one. Guitar-TECHS P3 (held out) is never read.
  4. The model for fold f trains on no render whose DI band is in fold f. It also uses no fold-f
     backing and no knob-ceiling optimum from a fold-f part.
  5. Assert that every evaluated part's band is in 0–3.
  6. For B5, a part whose band no C′ trained on (K3 fold −1) may use any C′ fold. Otherwise it uses
     C′ fold f."

### 6. B4 must be told its base, must jitter only around K_S optima, and needs a DI and level convention

- **Text (L154):** "**Amp:** given as an input condition, one model for all three amps." **(L160–
  162):** "random over K, with the 6 dry class starts … as the fixed base. Half broad coverage,
  half jittered around the starts and the knob-ceiling optima from *other folds*."
- **What's wrong:**
  - **The base differs by class.** K's settings sit on a start whose pedals, EQ and room mics
    differ between the clean and crunch starts (`learn/knob_ceiling.py:35-40`). The PR12 crunch
    start runs two pedals (KCP:83–85). A model conditioned only on the amp can't know what base its
    output goes onto.
  - **K_M optima sit on another base.** They sit on M's pedals, EQ and room mics, not on S
    (`knob_ceiling.py:457-460`), so jittering around them on S mislabels the sound.
  - **No DI or level convention.** The prediction is scored through the measure DI at −22.9 LUFS
    (`knob_ceiling.measure_di`, `:354-364`), and K_S's settings were found through it. The PoC
    rendered raw DIs and had to label "effective drive" (`learn/pr12.py:10-13`). Without a declared
    convention, the input-gain label means a different thing in the bank and at scoring.
- **Corrected text:**
  - "**Conditions:** the amp and the class start (one of the six). At evaluation, the part's class
    start, as K_S (the class is known, as in K_S; `generate`'s routed class is reported beside)."
  - "**Jitter centres:** the six starts and other folds' **K_S** optima (K_M's sit on M's pedals,
    EQ and room mics)."
  - "**DI and level:** bank renders use the scoring convention: each DI re-equalised to the
    average guitar at −22.9 LUFS (`knob_ceiling.measure_di`). A label's input gain then means what
    K_S's does. A raw-DI bank needs the proof of concept's effective-drive label, declared if
    chosen."

### 7. The positive control needs a defined target, a size, a cost and a stop rule

- **Text (L180–184):** "Synthetic songs from held-apart bands (planted settings, mixed, mastered and
  separated). Render the predicted settings through the true DI and score with the judge. The gap
  closed, (d_start − d_found) / (d_start − d_target), must reach ≥ 50% on ≥ 2/3 of targets, and
  must beat predicting the median settings. The proof of concept failed that bar on knob error."
- **What's wrong:**
  - **d_target is undefined.** If the planted render and the scoring render use the same DI, then
    d_target ≈ 0 and the measure becomes 1 − d_found/d_start: Report C's exact-target bar. §0.4
    (L595–597) already rejects that bar for exact targets, because knob ceiling's exact targets sat
    in sharp-bottomed valleys (KCR:27–28; L1769).
  - **Size, cost and stop rule are missing:** no number of targets, no renders, no fix-and-re-run
    cap (C1 has "at most twice", L1473).
  - **The PoC never ran this bar.** It measured knob error on renders.
- **Corrected text:** "**Positive control on renders (knob ceiling's realistic format).**
  - **Targets:** per fold, N ≥ 30 [I] from that fold's held-apart DIs. Each is planted K settings
    on the class start, rendered through the part's own raw DI. The model reads it mixed, mastered
    and separated.
  - **Scoring:** the prediction, the planted settings (d_target) and the median of that fold's
    training labels are each rendered through the measure DI. Each is judged against the planted
    render's held half (lag 0), with S as d_start.
  - **Pass:** gap closed ≥ 50% on ≥ 2/3 of targets, and closer than the median settings on ≥ 2/3.
    The targets come from the bank's own distribution, so a pass is optimistic.
  - **If it fails:** fix and re-run, at most twice.
  - **Cost:** ≈ 3 × 30 × 4 ≈ 0.4k renders.
  - The proof of concept never ran a sound-based control; on held-out renders its EQ and drive sat
    at the median."

### 8. B4's cost leaves out its controls

- **Text (L191):** "**Cost:** 24 × 3 × 2 = 144 renders." **(L268):** "B4 pilot | ≈ 10k + 144".
- **What's wrong:** the shuffled control needs renders too:
  - 144 with one other band;
  - 432 with three, as the PoC did (`learn/evaluate.py:52-62`).

  The positive control (fix 7) needs ≈ 0.4k. "Lose most of the gain" is undefined.
- **Corrected text:** "**Cost:** 144 prediction renders, 144–432 for the shuffled control and
  ≈ 0.4k for the positive control: ≈ 0.7–1k. The shuffled control 'loses most of the gain' when
  B4 vs shuffled is ≤ −0.05 band-weighted, with ≥ 60% of bands [I]." Budget row: "B4 pilot | ≈ 10k
  + ≈ 0.7–1k".

### 9. B5: `knob_search` can't be extended from 50 to 150; the convergence figure is K_M's

- **Text (L209–214):** "Knob ceiling got about 60% of its gain within the first 25 renders (−0.130
  at 25, −0.205 at 200). … It runs 50 renders per direction, with 150 reported if the 50 pass.
  **Cost.** 24 × 3 × 2 × 50 = 7.2k renders (+14.4k for the 150-render variant)."
- **What's wrong:**
  - **The curve is K_M's.** −0.130/−0.205 is (b), searching from M (KCR:50–51). K_S's curve was
    never reported: `cell_rows` computes checkpoints only for K_M (`knob_ceiling.py:700-703`).
  - **The incumbent at render 25 isn't a 25-render search.** It is the incumbent of a 200-render
    search. A 200-render `knob_search` spends its first 70 renders in the main stage.
  - **"+14.4k" assumes the 150 run continues the 50 run.** `knob_search` runs fixed stage shares
    per budget (`knob_ceiling.py:243-326`), so it can't be resumed.
  - **What budget=50 actually does:** about 18 main renders, then 18 mic alternatives at 1 render
    each with no re-tune, then 10 restart renders and 4 final.
- **Corrected text:** "Knob ceiling's (b), searching from M, had about 60% of its 200-render gain
  by render 25 (−0.130 against −0.205). That is the incumbent of a long search, not a 25-render
  search, and K_S's own curve wasn't reported. **Method:** B3's search with `knob_search(budget=50)`
  per direction. The 150-render variant is a separate `budget=150` run. **Cost:** 7.2k; +21.6k for
  the 150-render variant. Alternatively run only the 150 variant and read its incumbent at 50
  (21.6k in all), declaring which."

### 10. The readout table is not exclusive or complete, and contradicts §0.4

- **Text (L236–242).**
- **What's wrong:**
  - **Rows overlap with no first-match rule.** Row 1 (B5 best) overlaps row 2 (B4 passes, B3
    fails), row 3 (B3 passes, B4 fails) and row 4 (both fail: B5 can pass when both fail).
  - **Outcomes are missing:**
    - B3 and B4 both pass with B5 not best;
    - B4's positive control fails while B3's control passes.
  - **Row 5 contradicts §0.4.** It says "Either positive control fails → interpret nothing", but
    B3's known-target control has three readings: true-DI arm fails → 5c; rebuilt arm fails → 5b
    (L702–706; §0.3 L540–541).
  - **"At fewer renders" picks the wrong arm.** Within 0.02 of a *best B4* (one render), it would
    pick B5, which uses more.
  - **"Best" and "within 0.02" can't be resolved.** The band-mean SE is ≈ 0.026 at 14 bands, so a
    90% half-width is ≈ 0.045 (L718–719).
  - **"The same 24 × 3 cells" fails under Option 2a or 2b,** where B3 runs on 7 parts, or on
    different parts.
- **Corrected text:** "All arms are scored on the same cells: the 24 × 3, or B3's leak-free cells
  under Option 2a/2b, with B4 also reported on the 24. Read in order; the first match wins.

  | # | Outcome | Reading | Then |
  |---|---|---|---|
  | 1 | B4's positive control fails after two fixes | B4's pipeline is wrong | B4 and B5 are not read; B3 is read by §0.3 alone |
  | 2 | B3's control: the true-DI arm closes ≥ 50% on fewer than 8 of 12 | The optimiser or parameterisation is wrong | 5c for the search arms (B3, B5); B4 is read by rows 3–4, with B3 and B5 counted as failed |
  | 3 | At least one arm passes its control and gate | The leader is the passing arm with the best band-weighted held-half mean vs S. Any other passing arm whose paired 90% interval against it includes 0 is tied. Among tied arms the one with the fewest renders per cell leads (B4 1, B5 51, B3 150) | B5 leads: a proposal model plus a short search (product session, decision 12). B4 leads: the rebuilt DI is not needed; full B4, A7 + B4b, F1; B2 and D3 dropped; the product session plans a one-shot `generate` (decision 12). B3 leads: 5a as in §0.3, with B4 kept as a research line |
  | 4 | No arm passes | The song-side signal is the loss | 5b as in §0.3: the amp-track diagnostic arm, then one route under decision 10 |

  Every paired arm-vs-arm difference is reported with its band-clustered 90% interval."

### 11. B4 has no amp choice, so "H1 superseded" is only partly true; mark superseded text

- **Text (L244–247):** "C1's menu-ranking head (H1) is **superseded by B4.** …" Also L232–234:
  the comparison promises a product-like top-1, as B3's "best amp per part" (L677–678).
- **What's wrong:**
  - **B4 can't choose the amp.** It is told the amp (L154) and has no score to choose by, so its
    "best amp per part" readout is undefined. H1 picked the start *including the amp* (L762).
  - **Superseded text isn't marked.** Text overridden by Amendment 3 still stands unmarked:
    - §0.4 Changed triggers (L760–765: "H1 picks the start and topology for search");
    - C1's status line (L1399);
    - C1's H1 head (L1454);
    - C1's gate "Either head" (L1482).

    That breaks the plan's own rule (Appendix C fix 14).
- **Corrected text:**
  - Add to B4's evaluation: "**Amp for the top-1:** declared. Either the class's amp in
    `generate`, or a fourth head trained to predict which amp's K_S held-half distance is lowest
    (labels from other folds' knob-ceiling cells). Per-amp means are reported too."
  - Rewrite L244: "C1's menu-ranking head (H1) is superseded by B4 *as a start within an amp*.
    Choosing the amp stays open (B4's amp rule above); choosing topology stays with D1/D2."
  - Mark L760–765, L1399, L1454 and L1482 *Superseded by Amendment 3 (H1)*.

### 12. The budget leaves out A5, and the paths after the readout cross 200k

- **Text (L274–276):** "**Through the readout:** B3 + B4 pilot + B5 + A3 ≈ 51k, plus ≤ 20k for D1.
  **With D1 and knob ceiling's 70.3k** that is about 141k: under the 200k flag."
- **What's wrong:**
  - **A5 is missing.** It is work item 4 (L67) and costs 19.2k (L609); B4's controls are missing
    too (fix 8).
  - **The arithmetic itself is right:** 26.2 + 10.1 + 7.2 + 7.6 = 51.1k; + 20 + 70.3 = 141.4k.
  - **Every passing branch after the readout crosses 200k with knob ceiling counted:**
    - B4 passes: full B4 20k + A7 16–40k + F1 ≈ 5–9k (L1664);
    - B5 passes: its 150 variant 21.6k + F1 16–43k (L789–790).
- **Corrected text:** "**Through the readout:** B3 26.2k + B4 pilot ≈ 11k + B5 7.2k + A3 7.6k +
  A5 19.2k ≈ 71k, plus ≤ 20k for D1. **With knob ceiling's 70.3k:** ≈ 161k, under 200k. **After
  the readout the flag binds** (decision 10):
  - B4 passing adds full B4 20k, A7 16–40k and F1 (≈ 202–230k in all);
  - B5 passing adds its 150-render variant 21.6k and F1 16–43k (≈ 199–226k);
  - A5 replacing the optimiser adds 22.5k."

### 13. B3's control depends on A5; the work order says A5 can run "any time"

- **Text (L67):** "A5 … Waits for: Any time; it reads no recording". The sequence (L256–261)
  doesn't place A5.
- **What's wrong:** B3's known-target control runs "on A5's 12 leak-free cells", and its true-DI
  arm "is A5's incumbent at 150" (L694–697). B3's cost counts only the rebuilt arm (12 × 150,
  L730).
  - If A5 runs after B3, the control's true-DI arm doesn't exist.
  - The readout's row 2 (fix 10) depends on that arm.

  Amendment 2's "B3 no longer waits for A5" (L367) left this open.
- **Corrected text (work order, A5 row, "Waits for"):** "Any time. But B3's known-target control
  needs A5's 12-cell draw and its `knob_search` arm at 150 renders (1.8k) first. If A5 runs later,
  B3 renders its own true-DI arm (+1.8k; B3 ≈ 28.0k)." Add "A5's draw and `knob_search` arm" to
  the machine sequence before step 3.

### 14. Decision 3 and the development ledger: B4, B5 and A7 aren't covered, and the ledger comes too late

- **Text (L62):** "The user's decisions 10–13". ROADMAP L101–102: "The plan awaits the user's
  decisions 10–13".
- **What's wrong:**
  - **Decision 3 doesn't cover the new steps.** It proposes lifting "no more chooser or judge tweaks
    on the 33" for A3, A4, A5, A6's check, B1, B2, B3 and C1 only (L1082–1088), not B4, B5 or A7.
    The 24 evaluated parts include set-3 development parts (`knob_ceiling.py:526`), which are part
    of the 33.
  - **The ledger comes too late.** Decision 3 requires B3's gate entered in
    `docs/dev-test-ledger.json` before any result. That ledger doesn't exist (checked: no such
    file on this branch or main), and A3 creates it (L1232) as work item 3, after item 2.
- **Corrected text:**
  - Work order row 0: "The user's decisions 10–13, and decision 3 extended to B4, B5 and A7 (the
    24 parts include set-3 parts)."
  - Add before item 1: "Create `docs/dev-test-ledger.json` (moved from A3 step 8). Enter A6's
    check, B3/B4/B5's gates and A5's draw before any result."
  - ROADMAP: "The plan awaits the user's decisions 10–13 and decision 3 (re-using the set-3
    development parts)."

### 15. The work order's code pointers would mislead

- **Text (L65–66):** the code columns of items 2 and 3.
- **What's wrong:**
  - **`learn/render_job.py` breaks the isolate rule.** It renders in reused processes without
    `isolate=True` (`render_job.py:84`), against the standing rule (L72). It also samples through
    the PR12-only `pr12.sample` (`render_job.py:59`).
  - **`learn/di_pool.py` covers too little.** It reads only set-2 development DIs and Guitar-TECHS
    P1 (`di_pool.py:26-45`), not the 82 parts, P2 or Five-guitar.
  - **`learn/train.py` normalises loudness** (fix 4).
  - **`songs_check` is the wrong rebuild code for B3 and B5.** It is named for "parts, stems", but
    its `build_di` applies the **retired** 3-kHz lowpass and loads the old networks
    (`models-final`, `models-set3`), not C′ (`learn/songs_check.py:103-116,128-129`). B3 needs C′
    uncut (L681).
  - **`research/score_shortlists.py` is A4's code.** It is the Recall@k tool (L1250; A2 item:
    `within_share`), not A3's label table.
  - **The separation script isn't committed** (L1225). B4's 5k separations need it too.
- **Corrected text:**
  - **Item 2:** "`learn/knob_ceiling.py`:
    - `space`/`Dim` for K and its 0–1 scale;
    - `START`;
    - `Renderer` (isolate, amp select);
    - `measure_di`, `judge`, `knob_search`;
    - `cell_rows`/`best_amp_rows`;
    - the stored cells under `~/ndsp-presets/learn/knob-ceiling/cells/` (K_S optima and curves).

    Also:
    - `learn/direc.py` `rebuild` with C′ (`models-cprime/fold*.pt`), uncut, not
      `songs_check.build_di`;
    - `learn/rebuilt_judge.py` (`rebuilt_distance`);
    - `learn/songs_check.py` (`parts`, stem paths);
    - `learn/confirm_run.py` (`stats`).

    For B4:
    - `learn/di_pool.py`, extended to the 82 parts, P2 and Five-guitar;
    - `learn/render_job.py`'s worker and canary, with `isolate=True` and K-space sampling replacing
      `pr12.py`;
    - `learn/train.py` (`build_model`, the fold loop; `Frontend` replaced);
    - `learn/evaluate.py` (`predict`, `shuffled_sources`).

    The htdemucs separation script must be written or recovered and committed first."
  - **Item 3:** "`learn/confirm_run.py` (`build_di("measfix")`), `learn/knob_ceiling.py`
    (`Renderer.menu`, isolated), `learn/songs_check.py` (`render`/`_score_part` as the pattern),
    the separation script (to commit)." Move `research/score_shortlists.py` to A4.

### 16. B4's gate is not "as B3's"

- **Text (L198–202):** "**Gate (as B3's, so the two are comparable):** B4 vs S ≤ −0.03, and ≥ 40%
  of K_S's gain …; ≥ 60% of bands better; no class worse than S by more than +0.05; the shuffled
  control is clearly worse."
- **What's wrong:** B3's gate has two things B4's lacks (L710–717):
  - it is **band-weighted on the held half**;
  - its criterion 3 is "not worse than the C′ menu pick by more than +0.01".

  B4's gate drops criterion 3 and states no weighting, so the arms are not gated alike.
- **Corrected text:** "**Gate (B3's, band-weighted on the held half, on the unfiltered set when it
  exists):** criteria 1, 2 and 4 of B3's gate, plus 'the shuffled control is clearly worse'
  (fix 8). B3's criterion 3 (the C′ menu pick) doesn't apply to B4. It is reported for B4 from
  B3's renders."

---

## Suggestions

1. **The machine sequence (L256–261):**
   - **Step 1 contention.** It runs A6 alongside D1's renders. A6's spectral loss runs on the CPU
     (L624–625), and its scheduling says "or after measuring the step time under contention"
     (L631). Say so, and budget A6 at more than 15 h if D1 shares the CPU.
   - **A3 is missing from the sequence.** Place it after step 2; its FLACs come after A6's caches
     are deleted (L810).
   - **Separations straddle the quiet window.** The 7-h separation and the ~5-h A6 folds will cross
     03:00–04:15.
   - **Align the quiet-window wording.** The work order says "nothing renders 03:00–04:15" (L75);
     §3 says "nothing runs" (L1017), and A6 says training is in scope unless confirmed otherwise
     (L633–634).
2. **Disk.**
   - **Clip length.** Declare the bank's clip length: the separation estimate assumes 10-s clips
     (L171), but "3–5 GB" fits 6-s clips (C1: 12k × 6 s ≈ 4 GB, L1499).
   - **Fuller estimate.** Include features: 10-s float16 log-mel ≈ 256 KB per view (§1.1 #18), so
     ≈ 5 GB for two views × 10k. A fuller pilot estimate is ≈ 6–11 GB, still inside 35 GB after A6.
   - **Harmonise the two statements.** "Only if the disk allows" (L65) and "can't share the disk"
     (L252) disagree.
3. **Add two cheap B4 diagnostics (144 renders each)** so a gate failure is readable:
   - **A song-blind constant:** the median of other folds' K_S optima per amp and class. Knob
     ceiling found a common pull (less drive, less bass, darker; KCR:78–81) that a model could
     learn without reading the stem.
   - **An amp-track input arm,** as the proof of concept had, which separates the separator's loss
     from the model's.
4. **Before declaring B5's budget, compute K_S's convergence at 25, 50 and 100** from the stored
   `curve` in each cell's `result.json` (`knob_ceiling.py:489-502`). This costs zero renders.
5. **Say how the mixture-density head becomes one preset** (for example, the mean of the heaviest
   component, with argmax for categoricals). Consider B5 seeding from the top-k samples. That
   makes B5 the plan's C3 (L743–755) with a small k. State C3's status (superseded by B5, or B5
   is its pilot).
6. **Carry B3's and C1's stated mismatches into B4:**
   - the evaluation stems come from the instrumental mix, without vocals
     (`songs-check-results.md:53`);
   - bank clips are separated without the 30-s context (L1446–1447);
   - report results with and without the MUSDB18-train songs (L669–670).
7. **Guitar-TECHS.**
   - Say "P3 never read" in B4's bank.
   - If B4 goes to F1, note that the held-out pool counts the Guitar-TECHS player as a band
     (`A1-project-claims.md`, held-out uses). Training on P1–P2 repeats the set-4 process gap
     (`docs/set4-confirmation-results.md:82-83`).
8. **A7.**
   - **Reuse A3's menu renders.** A3 renders the 111 for those parts (L1218), which cuts A7 to
     ≈ 12k for one amp.
   - **Order.** B4b needs A3's unfiltered stems for those parts, so A7 comes after A3.
   - **Censored labels.** 93% of K_M searches ended at a range limit (KCR:59–60), and input gain
     at −20 dB in 47 of 144 runs.
9. **The work-order table.**
   - Row 1 omits Option 2b.
   - A3's "Waits for" cell holds a must-precede ("Before F1…"); move it to a note.
10. **README item 7 (L341–345).** "With two independent reviews" is true of Amendments 0–1, but
    Amendment 3 is unreviewed. Add this review to `ml-plan-2026-10-checks/`, list it in the plan's
    checks table (L35–42) and add an Appendix D.
11. **ROADMAP (L90–102).**
    - **List all the work items.** Add A3 (label table and unfiltered stems) and A5 (optimiser
      efficiency) to the work-order summary, so the ML session doesn't read them as dropped.
    - **Hedge the first item.** Write "C′ for every fold (or a leak-free subset; decision 11)".
    - **Fix the step-0 link.** The step's plan link (L75) still points at `di-recovery-plan.md`.
      Point it at the ML plan, or mark the old one historical.
12. **Fix stale or loose citations.**
    - **Header source (L27).** `origin/ml/knob-ceiling:docs/knob-ceiling-plan.md:356-362` is now
      main's KCP:414–419. On main, L356–362 is the cross-part check.
    - **"(§0, Amendment 2)" at L126–127.** "Sounds dirty" and "unrelated above 3 kHz" are not
      there. They are in `docs/ROADMAP.md:135,195-196`, `docs/closeness-review-2026-10-10.md:84`
      and `docs/e2e-runs-2026-10-13.md:18`.
13. **Update the decision tree** (Amendment 2's, L418–436) for B4 and B5, or say it is superseded
    where they apply.
14. **Precompute features.** B4 training on MPS alongside B3's renders keeps the one-MPS-job rule:
    `direc.rebuild` runs on the net's device, and the existing callers load it on the CPU
    (`direc.py:285,546`). Precomputing features, with fixed augmentation draws, keeps the CPU free
    for B3's six render processes.

---

## Items checked

| Claim (plan line) | Verdict | Evidence |
|---|---|---|
| PoC 18,843 renders, 14 players (L108) | Confirmed | PoCR:5; PoCP:20–21 |
| 0.44 spread, EQ nearly flat (L110–111) | Confirmed | PoCR:38–39 |
| EQ 0.96–1.04, drive 0.97 (L112–113) | Wrong source and scope (fix 2) | PoCP:118–123; PoCR:62–64 |
| 21–22 of 28 (L114–115) | Confirmed | PoCR:20–21, 33–34 |
| 1.9 vs 1.45 dB, 21 clean presets (L103–105) | Confirmed; the range fits | PoCP:124–130 |
| 1.3 s per batch, ~10 h for 30 epochs (L176–177) | Quoted right, read wrong (fix 1) | PoCP:115–117; `train.py:218-230` |
| K_S −0.253, 40% ≈ −0.10 (L117) | Confirmed (0.40 × 0.253 = 0.101) | KCR:40 |
| −0.205, −0.130 at 25 (L209–210) | Confirmed, but it is (b), from M (fix 9) | KCR:39, 50–51 |
| 24 parts × 3 amps in 14 bands (L187) | Confirmed | KCR:33–34 |
| K table; pedals, EQ, room mics, amp kept from S (L140–142) | Confirmed (also pan and phase; time effects off; the left-mic dims drop when S's left cab is off) | KCP:56–81; `knob_ceiling.py:82-100` |
| 6 dry class starts (L160) | Confirmed | `knob_ceiling.py:34-40` |
| 82 classed development parts (L157) | Confirmed (48 + 17 + 17) | `A2-infrastructure.md:592-599`; `part-locator-truth.json` |
| Guitar-TECHS P1–P2 local; P3 a validation set (L157) | Confirmed | `di_pool.py:36-39` (P1); `di-domain-pilot-plan.md:14-17` (P2, development); `validation-datasets.md:41-44` (P3) |
| Stems can be cut to the search half (L187–188) | Feasible: 10-s, crop-aligned stems; halves 1.0–5.5 and 5.5–10 s fit two 4-s windows | `songs_check.py:83,90,188-194`; `phase2_set3.py:43`; `evaluate.py` docstring |
| Fold-by-band with no leak (L196–197) | Not as cited (fix 5) | `train.py:51-56,218-219`; `songs_check.py:85`; `knob_ceiling.py:526` |
| B3 ≈ 26.2k (L267) | Confirmed (21.6 + 1.8 + 0.15 + 2.664) | L407, L727–732 |
| B4 pilot 10k + 144 (L268) | Arithmetic right; controls missing (fix 8) | — |
| B5 7.2k (+14.4k) (L214) | 7.2k right; +14.4k assumes a resumable search (fix 9) | `knob_ceiling.py:243-326` |
| A7 16k / 40k (L226–227) | Confirmed (40 × 411 = 16.4k; 40 × 1,011 = 40.4k; 65 − 25 = 40 parts) | KCP:115 |
| Through the readout ≈ 51k; ≈ 141k (L274–275) | Arithmetic right (51.1k; 141.4k); A5 left out (fix 12) | L609 |
| Separation 5k × ~5 s ≈ 7 h (L171) | Confirmed (6.9 h) [I, linear scaling] | §1.1 #13 |
| Training 2.5 h per fold (L178) | ≈ 4× too high on the stated basis (fix 1) | — |
| A6 35 GB + 30 GB floor vs the bank (L252–255) | Logic holds (A6 alone needs ≥ 66 GB free, the whole usable disk) | L626–629; §1.1 #18 |
| One MPS job: B4 trains while B3 renders (L259) | Holds (renders and rebuilds are CPU); CPU contention noted | `direc.py:285,546`; `songs_check.py:116` |
| Code named: `direc.fit`/`rebuild`, `train.k3_folds`, `knob_search`, `run_cell`, `confirm_run.build_di("measfix")`, `match/search.py` CMA-ES, `evaluate.py` prediction | All exist | `direc.py:358,541`; `train.py:42`; `knob_ceiling.py:246,439`; `confirm_run.py:81-94`; `match/search.py:934-1047`; `evaluate.py:65` |
| "K table" in code | It is `space()`/`AMP_DIMS`/`CAB`, not a table | `knob_ceiling.py:82-100` |
| `research/score_shortlists.py` for A3 | Wrong step: it is A4's Recall@k (fix 15) | L1250 |
| Decision numbering 10–13 | Consistent (§0.6 10–12; 13 new); ROADMAP matches | L815–824, L280 |
| Readout vs §0.3 5a/5b/5c | Partly inconsistent (fix 10) | L539–541, L702–706 |
| "H1 superseded by B4" | Partly; amp choice open; text not marked (fix 11) | L762, L1399, L1454, L1482 |
| Gate ≥ 40% of K_S for B4 | Sensible as a shared product bar, but ≈ 3× the PoC's amp-track effect; add diagnostics (suggestion 3) | PoCR:18, 33–35, 90–114 |
| README items 6–7; ROADMAP paragraph | House style fine; "proposed, not declared" consistent; omissions in suggestions 10–11 and fix 14 | README:9-13, 337–345; ROADMAP:90–102 |
