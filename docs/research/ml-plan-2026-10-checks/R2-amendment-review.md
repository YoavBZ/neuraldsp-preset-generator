# R2: Adversarial review of Amendment 1 (`docs/research/ml-plan-2026-10.md` §0)

Reviewed 2026-10-14 against the working tree on `claude/new-session-22s984` (with origin/main
#186–#188 merged), `origin/ml/knob-ceiling` (`docs/knob-ceiling-plan.md`,
`learn/knob_ceiling.py`) and `origin/ml/egvae-lite`. No repository file was edited.

**Version reviewed.** The plan file changed during the review (mtime 07:46): §0.2 rows 93–100
and §0.8's DiffMoog row were rewritten by the literature check, and
`ml-plan-2026-10-checks/C1-report-c-claims.md` now exists. Line numbers below refer to the
1,366-line version, where Amendment 1 is lines 44–368. Report C's literature and licence rows
(93–100) are outside this review.

**Plan-file shorthand:** `L123` = `docs/research/ml-plan-2026-10.md` line 123. `KC:n` =
`origin/ml/knob-ceiling:docs/knob-ceiling-plan.md` line n.

---

## Verdict

**The direction is right, but the amendment is not ready to declare. 16 required fixes.**

Search through the real plugin as the main line, a true-DI comparator (K_S) on the same
cells, and a leak check are the right structure. The repo facts mostly hold:

- the goal quote;
- PR #186's isolation;
- "C′ only for fold 2";
- "7 of the 25", which is exact;
- K_S's definition;
- the `rebuilt_distance` feasibility;
- the 0.075/0.26 shortfall and the ~75% arithmetic.

**What fails:**

- **One attribution is wrong.** Set 4's −0.087 came from the old network C, not C′.
- **Option 2 is mis-sized.** It is "about 8 bands" with "0 renders"; in fact it is 7 bands at
  no extra renders, or 11 bands at about 21k renders.
- **B3 runs on the SNR-filtered 25 parts.** The plan elsewhere calls these an optimistic
  subset and bars that kind of filter from product-facing tests.
- **The known-target control and its branch logic don't close.** The likeliest failure,
  "control passes, development gate fails", has no branch. The pass row can fire when both
  arms fail. The control's hidden DI can leak into C′.
- **The K_S ≈ 0 skip is undefined and comes too early.** It fires before A5 and ignores that
  S was chosen on 24 of the 25 parts.
- **The budget leaves things out:**
  - the C′ menu-pick renders;
  - F1's generation search;
  - B3's own sum.

  With these counted, the 6a path is not "well under 200k".
- **Product-session ownership of D2 and E2 is stated but not carried through.**

---

## Required fixes

### 1. B3 "Why": set 4's −0.087 is the old network C, not C′

- **Text (L215–218; also row L76):** "C′ is the only song-side signal with held-out evidence:
  set 4: −0.087 against the old starts; set 5: −0.124 against the old network C; but against
  today's crunch start only −0.023 [P]."
- **What's wrong.** Set 4's confirmation ran on 2026-10-10 with `models-set3/fold2.pt` (C,
  trained under the MPS bug, with the 3 kHz cut). C′ was trained on 2026-10-11. Every
  held-out number also comes from isolated amp tracks, not songs or stems.
- **Evidence:**
  - `docs/set4-confirmation-plan.md:57` ("Network: `models-set3/fold2.pt`");
  - `docs/set4-confirmation-results.md:3,22`;
  - `docs/residual-di-results.md:3`;
  - `docs/set5-test-results.md:9-21` (C′ is a three-seed mean), `:71-72` ("doesn't establish
    anything about songs (the input was isolated amp tracks)");
  - the plan's own D3, L1045 ("C′-family networks have never been run on separated stems").
- **Corrected text:** "The rebuilt-DI route is the only song-side signal with held-out
  evidence, all from isolated amp tracks, not stems:
  - the old network C on set 4: −0.087 against the old starts;
  - C′ (three-seed mean) on set 5: −0.124 against C, but only −0.023 against today's crunch
    start [P, `set4-confirmation-plan.md:57`; `set5-test-results.md:9-21,71-72`].

  C′ has never been scored on a separated stem, so B3 is also its first stem test." In row L76,
  replace "C′ is the only song-side signal with held-out evidence" with "the rebuilt-DI route is
  the only song-side signal with held-out evidence (amp tracks only)".

### 2. The leak count: exactly 7 of 25; set 1 doesn't shrink it; Option 2 is mis-sized

- **Text:** L80, "only about 7 of those are among knob ceiling's 25"; L190–191; L202–206,
  "Option 2 … fewer bands (about 8)"; L333, "restrict B3 to the ~8 leak-free bands".
- **What the repo shows.**
  - **Folds are reproducible from the repo.** `train.k3_folds()` folds only the bands of the
    PR12-clean kill panel (`learn/train.py:35-56`). That panel is derived from the PR12 panel
    (`research/derive_panel.py:1-15`), which renders set-2 development parts only
    (`research/render_preset_panel.py:9,199`, `development_parts(catalog, None, [2])`).
  - **Re-drawing the shuffle reproduces `residual_eval.parts()`'s assertion exactly.** Seed
    20261003 over the 13 set-2 development bands with usable parts (`validation-datasets.json`)
    gives 18 parts in 8 bands, 12 crunch in 5 and 6 clean in 4 (`learn/residual_eval.py:38-55`).
    Fold 2 = {Eat The Feeder, John Morgan Kimock, Zeno}.
  - **C′'s training DIs are set-2 development bands plus Guitar-TECHS P1** (set 1 is never read;
    `learn/di_pool.py:3-5,27-30`; `learn/render_pairs.py:5-8`). The bleed comes only from the
    kill panel's parts in the training folds (`learn/direc.py:388-400`). So **set-1 and set-3
    parts are leak-free for every fold.**
  - **But knob ceiling's 25 contain no set-1 part.**
    - `songs_check.parts()` reads `band_of[slug]` from `k3_folds` (`learn/songs_check.py:86-93`),
      which would fail for a set-1 slug.
    - All 20 "sets 1–2" parts in `docs/generate-routing-parts.json` (`"set": 12`) belong to set-2
      groups.
  - **So the leak is not smaller.** The leak-free parts are:
    - Signs ElecGtr2 (Zeno, clean);
    - Today's The Day ElecGtr10 (Eat The Feeder, crunch);
    - the 5 set-3 parts.

    That is **7 parts in 7 bands, 3 clean and 4 crunch**. The 18 leaky parts are fold 0
    (Adam Buckley, Atlantis Bound, Swatkins, The Travelling Band: 6), fold 1 (Dom McLennon,
    Doom Flamingo: 8) and fold 3 (Eggy, Starnes And Shah: 4).
  - **Beyond the 25, the leak-free pool is larger than "about 8 bands".** Among classed
    clean/crunch development parts (`docs/part-locator-truth.json`) it holds 28 parts in 11
    bands: 14 clean in 7, 14 crunch in 6. It adds:
    - set 1's 6 clean parts (Rebecca Haviland, Chris Coltraine);
    - all 16 set-3 clean/crunch parts;
    - Eat The Feeder and Zeno's other parts, and JMK.
  - **Running K_S outside knob ceiling is not free:** about 21 × (111 menu + 3 × 2 × 150) ≈
    21k renders.
- **Corrected text:**
  - **L80:** "C′ exists only for fold 2. Of knob ceiling's 25, exactly 7 (in 7 bands: 3 clean,
    4 crunch) are leak-free [P, reconstructed `k3_folds`; `learn/residual_eval.py:38-55`;
    R-review R2]. Set-1 parts would be leak-free for any fold, but the 25 contain none."
  - **L202–206:** "**Option 2: restrict B3 to parts C′ never trained on.** Count them in code at
    declaration: `train.k3_folds()` fold −1 or 2, plus a check against C′'s DI pool
    (`learn/di_pool.py`).
    - **2a:** knob ceiling's 7 leak-free parts, in 7 bands. No extra renders.
    - **2b:** every leak-free classed clean or crunch development part, up to 28 parts in 11
      bands (crunch 6 bands), with A3's unfiltered stems. M and K_S are run outside knob
      ceiling, ≈ 21k renders."
  - **L333:** "… or restrict B3 to leak-free parts (7 parts in 7 bands at no cost, or up to 28
    parts in 11 bands at ≈ 21k renders)."

### 3. A6: the training time is not a measurement, and "0 renders" is wrong

- **Text (L194–201, L206; L112, L332):**
  - "About 6 h of MPS each, by R's measured time [P], so ≈ 18 h";
  - "**Check:** on its own held-out fold, its menu pick …";
  - "**Cost.** 0 renders either way."
- **What's wrong.**
  1. **The 6 h is not a measurement.** "R takes 6 hours" is the superseded minutes schedule
     (`docs/residual-di-plan.md:40,95`). C′ is step-matched: 5,150 + 23,100 steps at a
     measured ≈ 0.62 s per step ≈ 4.9 h (`:159-160,165-167`).
  2. **The menu-pick check needs renders:** the 111-preset menu through each new fold's
     rebuilds, about 18 × 111 ≈ 2.0k on the 25's set-2 parts.
  3. **Option 2b costs ≈ 21k renders** (fix 2).
- **What's right.** A new fold needs no new pair renders. `fit()` splits the same caches by
  fold (`learn/direc.py:388-390`), the fold's average is computed from the cache
  (`:111-127`), and the SW50R/AC20 caches are rebuilt from stored FLACs (~35 GB;
  `residual-di-plan.md:92-93,138`).
- **Corrected text:** "About 5 h of MPS each (28,250 steps at the measured ~0.62 s
  [P, `residual-di-plan.md:159-160,165-167`]), so ≈ 15 h, more if the CPU is shared, since the
  spectral loss runs on the CPU. No new pair renders: every fold trains from the same rebuilt
  caches. **Cost:** Option 1, ≈ 2k renders for the menu-pick check (or reuse B3's C′-menu-pick
  renders); Option 2a, 0; Option 2b, ≈ 21k." Change "≈ 18 h" to "≈ 15 h" in L112 and L332.

### 4. B3 on the 25 parts is an SNR-selected, optimistic subset

- **Text (L225–229, L116):** "Cells. Knob ceiling's 25 parts … the part's **unfiltered
  stem** (A3)".
- **What's wrong.**
  - Knob ceiling's 25 are `songs_check.parts()`: exactly the parts that passed the ≥ 1 dB
    stem-SNR filter. The plan itself says so:
    - L713: "kept by a ≥ 1 dB SNR filter";
    - L811: "the 25 usable-stem parts reported as an optimistic subset";
    - L1279: never filter stems by SNR in a product-facing test.
  - The stems are the same htdemucs_6s files. "Unfiltered" changes nothing on these parts:
    the selection is the filter.
- **Evidence:** `docs/songs-check-results.md:52-58`; `learn/songs_check.py:37-38,81,89`.
- **Corrected text (add to Cells):** "These 25 are the songs check's SNR-selected parts (≥ 1 dB),
  so B3 on them is an optimistic subset, labelled so. The generation claim also has to hold on
  unfiltered parts: either through Option 2b, or by running M and K_S on the A3 parts B3 adds.
  The gate is read on the unfiltered set when it exists."

### 5. B3 is not like-for-like with K_S unless its search space, start and amp choice are fixed

- **Text (L232):** "**Search.** A5's optimiser at 150 renders per direction, the same budget as
  K_S." L225: "Knob ceiling's 25 parts × 3 amps".
- **What's wrong.**
  - **The search space.** K_S searches only knob ceiling's K space. Pedals, EQ, room mics and
    the selected amp are kept from the dry start; time effects are off (KC:36-41, 56-84). B3
    names no space, and D2 and Report C want EQ, pedal and topology stages.
  - **The amp.** The product's top-1 needs an amp choice. Knob ceiling reports "the best amp per
    part" (KC:180-182); B3 doesn't.
  - **The count.** telefunken-Honey-GTR's half B is refused for every preset (KC:31-32;
    `songs-check-results.md:47`). So B3 scores 24 parts in 14 bands, and the Swatkins band
    drops out.
- **Evidence:**
  - `learn/knob_ceiling.py` `BUDGET`, `DIRECTIONS`, `cells()` (lines 41-42, 529-530): K_S
    exists for all 3 amps of every part, both directions;
  - the knob-ceiling `run_cell` code keeps pedals and the amp from S.
- **Corrected text:** "**Search.** A5's optimiser, 150 renders per direction, over exactly K_S's
  space and start:
  - the space is the K table (input gain, amp knobs and switches, both mics, cab position and
    distance, right-mic level and switch);
  - pedals, EQ, room mics and the amp are kept from the dry S (`knob_ceiling.START`); time
    effects are off.

  Reported per cell, and as a product-like top-1, 'best amp per part'. The amp is chosen by
  B3's own rebuilt-DI search-half distance, and K_S's by its true-DI search half. Honey drops,
  so 24 parts in 14 bands are scored."

### 6. The C′ menu-pick comparator is unbudgeted, and B3's sum is wrong

- **Text (L239; L262–264):** "the C′ menu pick through the same rebuilt DI"; "~22.5k … plus 1.8k
  for the control and ~150 true-DI scoring renders: ≈ 24.3k, about 2–3 h."
- **What's wrong.**
  1. 22,500 + 1,800 + 150 = **24,450**, not 24.3k.
  2. The C′ menu pick needs 25 × 111 = **2,775** new renders through each part's rebuilt stem
     DI. The songs check's stem renders can't be reused:
     - they came from the old fold networks (`models-final`) with the retired 3 kHz cut;
     - they were rendered before `isolate`.

     (`learn/songs_check.py:32,103-116,128,142`; `learn/rebuilt_judge.py:13-20`.)
- **Corrected text:** "~22.5k renders (25 × 3 × 2 × 150), plus 1.8k for the control (12 × 150),
  ~150 true-DI scoring renders, and 2.8k for the C′ menu pick (25 × 111, uncut, at −22.9 LUFS):
  ≈ 27.2k, about 2–3.5 h."

### 7. The known-target control can leak, its "gap" is undefined, and its table is not exclusive

- **Text (L240–249).**
- **What's wrong.**
  1. **The hidden DI may be one C′ trained on.**
     - C′ trained on Morgan renders through set-2 DIs from folds 0, 1 and 3
       (`learn/render_pairs.py:5-8`).
     - A5's 6 parts are "drawn with a declared seed" from development, with no leak rule.
     - Rebuilding a render of a training DI flatters the rebuilt arm. The control renders a
       plugin preset, which is C′'s own training domain, so it is optimistic even when
       leak-free.
  2. **"Closes ≥ 50% of the gap" is undefined on realistic targets.** These targets have a
     non-zero reachable distance. Knob ceiling's realistic "gap closed" is
     (d_start − d_found)/(d_start − d_target) (KC:287-295: 109, 93, 90, 103, 83, 91%).
  3. **The budgets don't match.** A5 runs 300 renders; the control's 1.8k = 12 × 150.
  4. **There is no pass criterion for the true-DI arm.** "Rebuilt arm … within 0.03 of the
     true-DI arm's shortfall → Pass" also fires when both arms fail, which contradicts the
     "Both fail" row.
- **Corrected text.**

  > **Known-target control** (Report C), on A5's 12 cells. A5's 6 parts are drawn only from
  > parts the C′ in use never trained on (for fold 2: set 1, set 3, Eat The Feeder, Zeno or
  > JMK). Both arms are compared at 150 renders; the true-DI arm is A5's incumbent at 150.
  > "Gap closed" = (d_start − d_found)/(d_start − d_target) on the held half. "Shortfall" =
  > log(d_found / d_target). Readings, first match wins:
  >
  > | # | Outcome | Reading |
  > |---|---|---|
  > | 1 | True-DI arm closes ≥ 50% on fewer than 8 of 12 | Optimiser or parameterisation: 6c |
  > | 2 | Rebuilt arm closes ≥ 50% on ≥ 8 of 12, or its mean shortfall is within 0.03 of the true-DI arm's | Control passes |
  > | 3 | Otherwise | The rebuilder fails even on known targets: 6b |
  >
  > The control rebuilds a plugin render, C′'s training domain, so a pass does not clear the
  > rebuilder on real stems.

### 8. A5: the secondary measure doesn't apply to its targets, and the gate has no budget

- **Text (L161–171).**
- **What's wrong.**
  - **The primary measure is right.** "Held-half shortfall … against the target settings' own
    distance" is the quantity knob ceiling reported: v6 mean +0.075, up to +0.255 (KC:287-300).
  - **Report C's measure doesn't fit realistic targets.** 1 − d(found)/d(start) is a
    known-exact-target measure. On realistic targets it is capped at 1 − d_target/d_start, so
    Report C's 70% bar doesn't transfer.
  - **The ~75% arithmetic is right but comes from the other control.** v6's exact control gives
    1 − held/start = 0.86, 0.82, 0.69, 0.54, 0.66, 0.90: median 0.755, mean 0.745. That is the
    exact control, which knob ceiling declared failed (KC:296-297). That it clears Report C's bar
    shows the bar is weak.
  - **The gate has no budget.** B3 and K_S run at 150; A5's arms run at 300.
- **Corrected text:**
  - "**Measure.** Primary: held-half shortfall, log(d_found/d_target), as knob ceiling reports
    it (v6 realistic: mean +0.075). Secondary: knob ceiling's gap closed,
    (d_start − d_found)/(d_start − d_target) (v6: median 92%, 83–109%); convergence at 50,
    100, 150, 200 and 300 renders."
  - "**Gate (to declare),** at 150 renders (B3's and K_S's budget), with 300 reported: …"
  - "Report C's 1 − d/d_start bar applies to exact targets only. On knob ceiling's exact control,
    v6 already reaches a median of 75.5% (54–90%) while failing knob ceiling's own stricter rule,
    so that bar says little [I, KC:287-295]."

### 9. The branch logic and the decision tree don't cover the likeliest outcome

- **Text:** L118–121 (6a, 6b, 6c rows); L77 ("B2 and C1 become conditional on it"); L230–231;
  L245–249; L338–356 (tree).
- **What's wrong.**
  1. **"Control passes, development gate fails" has no branch.** This is the likeliest failure:
     the control rebuilds a clean plugin render (fix 7), while real stems add separation and
     the recording domain. In that case B2 and C1, which address exactly this, never trigger.
  2. **The amp-track diagnostic arm (L230–231) never feeds the branch,** although it is the
     only thing that tells separation loss from rebuild loss.
  3. **The 6b text contradicts the budget.**
     - The 6b text: "B2 and C1, then D3 or C2".
     - The worst case counts both D3 and C2 (102k).
     - §0.5 says "not both" under a 200k flag.
     - The tree draws both.
  4. **No exit when "B3 again" fails.**
  5. **The K_S ≈ 0 route to 6c is missing from §0.3's 6c row.** The tree and B3's entry use it.
- **Corrected rows (§0.3):**

  | Order | Step | New renders | Starts after | Decides |
  |---|---|---|---|---|
  | 6a | Control **and** development gate pass → hand B3's evidence to the product session for D2 and E2 (decision 0.12); D1 if A2 is positive and heard; F1 | see §0.5 | B3 | What ships |
  | 6b | The true-DI side works (the control's true-DI arm passes, and K_S clears B3's entry) but B3 fails the control or the development gate → run the amp-track diagnostic arm. Stem arm fails and amp-track arm passes: separation is the loss → the learned route (C1 → C2). Both fail: the rebuild is the loss → the DI route (B2 → D3). One route unless decision 0.10 allows 300k. Then B3 again with the new score | DI ≈ 61k; learned ≈ 72k | B3 | A better song-side score |
  | 6c | K_S fails B3's entry after A5; or the control's true-DI arm fails; or B3 again fails | 0 | A5 / B3 | Stop generation work; ship starts + research + the ear |

- **Corrected tree:**

  ````mermaid
  flowchart TD
      D0[Step 0 decisions incl. 0.10-0.12] --> A6[A6: C-prime for folds 0,1,3, or a leak-free restriction]
      K[A2 knob ceiling report] --> A5[A5 optimiser bake-off]
      A5 -->|new optimiser| KS[re-run K_S with it]
      A5 --> E{K_S vs S below the entry threshold?}
      KS --> E
      E -->|no, and K_M vs S also small| X0[6c: ship starts + research + ear]
      E -->|no, but K_M vs S large| SP[B3 arm from the C-prime menu pick]
      E -->|yes| B3[B3 rebuilt-DI search, dev]
      SP --> B3
      A6 --> B3
      K --> A1[A1 carry-over audit] --> A3[A3 labels + unfiltered stems] --> B3
      B3 -->|control and gate pass| P6a[6a: hand-off to product session for D2/E2; D1 if heard; F1]
      B3 -->|control true-DI arm fails| X1[6c: optimiser or parameterisation]
      B3 -->|control or gate fails, true-DI side works| DG[amp-track diagnostic arm]
      DG -->|stem fails, amp track passes| L[learned route: C1, then C2]
      DG -->|both fail| DI[DI route: B2, then D3]
      L --> B3b[B3 again with the new score]
      DI --> B3b
      B3b -->|passes| P6a
      B3b -->|fails| X2[6c: stop]
  ````

### 10. The K_S ≈ 0 skip is undefined, comes before A5, and ignores that the starts were chosen in-sample

- **Text:**
  - L57–59: "if searched knobs add little even with the true DI, generation cannot beat a good
    start";
  - L222–223: "if knob ceiling's K_S against S is about zero with the *true* DI, B3 is skipped
    (step 6c)";
  - L343: the tree sends K straight to 6c.
- **What's wrong.**
  1. **"About zero" is not a number.**
  2. **Knob ceiling reads "little" as undecided.** "The search found little: undecided … this
     test can't restore the old reading" (KC:254-262). A5 exists to settle that (L142–143,
     L175), yet the tree reaches 6c without passing through A5.
  3. **K_S vs S is deflated on these parts.** The clean start was chosen on 17 of the 18 set-2
     clean parts and on set 3's clean parts; the crunch start on all 5 crunch parts. That is 24
     of the 25 (all but Honey).
     - `docs/clean-baseline-plan.md:20-22,51-53`;
     - `docs/crunch-baseline-plan.md:17-20`.
  4. **K_S ≈ 0 with a large K_M − S means the start is the lever, not that generation is
     futile.**
- **Corrected text.**
  - **L57–59:** "Knob ceiling (A2), checked by A5, now gates generation. If a true-DI search from
    today's start finds little even with A5's best optimiser, a rebuilt-DI search can't be
    expected to beat the start, and effort goes to choosing the start. Knob ceiling reads
    'little' as undecided, so that conclusion waits for A5."
  - **B3 Entry:** "A2 has reported and A5 has run. If A5 changed the optimiser, K_S is re-run with
    it. B3 is skipped (6c) only if the band-weighted K_S vs S is above −0.05 [I] (B3 would then
    need more than 60% of K_S's gain to reach −0.03) **and** K_M vs S is also above −0.05. If
    K_S is small but K_M vs S is at −0.10 or below, B3 also searches from the C′ menu pick. S
    was chosen on 24 of these 25 parts, so K_S vs S is in-sample-deflated; this is reported with
    it."

### 11. The budget (§0.3, §0.5, "Why this order") leaves out costs and doesn't add up

- **Text:**
  - L318: "E1 and F1 ≤ 11k";
  - L317–319;
  - L120: "≤ 102k";
  - L322: "The 6a path stays well under 200k";
  - L129: "saves ~45–80k".
- **What's wrong.**
  1. **E1 + F1 is ≤ 10k in §5** (L1192), not 11k.
  2. **F1 is still costed as a menu pick** ("~5–9k", L1161). F1's primary outcome is now the
     *generated* preset (L306–311), which needs a cross-half search per part: 39 parts × 2
     directions × 150–500 ≈ 11.7–39k, plus ~4.3k menus [I].
  3. **The main line omits two costs:** the C′ menu pick (2.8k; fix 6) and the conditional
     22.5k K_S re-run.
  4. **B3 is 27.2k** (fix 6), so 6b with both routes is ≈ 105.5k.
  5. **The "~45–80k" saving is really ~35–80k.** B2 + C1 alone is 35.3k; all four steps are
     78.3k. A5 + B3 add ≈ 38k back.
- **Corrected §0.5 table** (all new renders; knob ceiling 70.3k):

  | Path | New renders | With knob ceiling |
  |---|---|---|
  | Main line: A1 3.1k, A2 0.15k, A3 7.6k, A5 10.8k, B3 27.2k | ≈ 49k (≈ 71k if A5 changes the optimiser) | ≈ 119k (≈ 142k) |
  | + 6a: D1 ≤ 20k, E1 < 1k, F1 with generation ≈ 16–43k [I] | ≈ 86–113k | ≈ 156–183k |
  | 6b one route, then 6a: DI (B2 23.3k + D3 10k + B3 27.2k) | ≈ 146–174k | ≈ 217–244k |
  | 6b one route, then 6a: learned (C1 12k + C2 33k + B3 27.2k) | ≈ 158–185k | ≈ 228–256k |
  | Optional: amp-track arm 22.5k, sensitivity map ≤ 10k, R5 ≤ 11k, C3 ~5k, Option 2b ≈ 21k | — | — |

  - **The 6a path is under 200k only at the low end.** It is ≈ 183k at 500 renders per song, and
    ≈ 206k if A5 also changes the optimiser.
  - **Every 6b path exceeds 200k once knob ceiling is counted,** so decision 0.10 is needed
    before 6b, not only "choose one route".

  L129: "saves ~35–80k renders on the passing path (B2 + C1, up to all of B2, C1, C2 and D3),
  against ≈ 38k that A5 and B3 add." L120: per-route figures as in fix 9.

### 12. The product session owns `generate`, and the research input is ignored

- **Text:** L119 ("**D2** (search in `generate`) … ≤ 31k"); L296–299 (D2 "becomes search in
  `generate`"); L334–336 (decision 12).
- **What's wrong.**
  - **The ROADMAP gives this step to the product session.** It lists as a *product* step: "Next,
    once the knob-ceiling result is in: if setting controls gets meaningfully closer than the
    starting presets, plan how `generate` sets more controls from the song (the user's goal);
    two render checks first (isolated renders repeat exactly; the isolation fade-in's effect on
    the match loss)" (`docs/ROADMAP.md:344,356-359`).
  - **The amendment still runs D2 and E2 as ML steps.** It schedules them with renders and
    never mentions the hand-off or the two checks.
  - **The goal uses research, and B3 doesn't.** The goal is "from a song **and its research**"
    (ROADMAP:10-12). `generate` now sets research-documented values on top of the start
    (`skills/generate/SKILL.md:19-28`). B3 and D2 start from bare S and never say how
    documented values enter the search. Report C says research should "alter the prior
    probability of a topology, not hard-lock it" (report-c.md:185).
- **Corrected text:**
  - **6a:** "B3 passes → the ML session hands B3's evidence and a search module to the product
    session. The product session plans D2/E2 as its own step (ROADMAP 'Next', including its two
    render checks, under decision 0.12). ML runs D1 (if A2 is positive and heard) and F1."
  - **D2, add:** "Research-documented values seed the search's start, and its prior where the
    documentation is firm. They are not hard-locked."

### 13. Development-data rules: decision 0.3 and the ledger don't cover the new steps

- **Text:** L586: "Proposal: lift it for **A3, A4, B1, B2 and C1**"; L537, L729 (the development
  ledger).
- **What's wrong.** A5's control parts and B3's cells use set-3 parts from "the 33":
  - 5 of knob ceiling's 25;
  - all 16 set-3 clean/crunch parts under Option 2b.

  The 2026-10-10 constraint is lifted only for the listed steps, and the amendment doesn't
  mention the ledger.
- **Corrected text (Step 0, decision 3):** "Proposal: lift it for **A3, A4, A5, A6's check, B1,
  B2, B3 and C1**, recording every development decision in the development ledger
  (`docs/dev-test-ledger.json`), with B3's gate and A5's draw entered before any result."

### 14. Text the amendment overrides is not marked

- **Text:**
  - §1.1 #9 effect "No optimiser switch" (L446);
  - §1.2 optimiser row "No change. Knob ceiling's coordinate search stays" (L469);
  - A2's reading for "little": "No further search budget now, as a cost choice" (L691);
  - D1 "Optimiser: keep the project's coordinate search … CMA-ES has no evidenced gain"
    (L1017–1018);
  - §7 dead end "Switch to CMA-ES for 'better search'" (L1267).
- **What's wrong.** These are operative instructions that contradict A5 (testing, possibly
  adopting, CMA-ES or TPE) and B3 (search budget spent whatever (b) reads). Every other changed
  section carries an "*Amended*" note; these don't.
- **Corrected text:**
  - In each: "*Superseded by Amendment 1: A5 tests CMA-ES and TPE at equal budget; the winner is
    used (§0.4).*"
  - For L691: "*Superseded: A5 runs on any reading, and B3's entry depends on K_S (§0.4).*"
  - In §7, move the CMA-ES row to "Do not switch optimiser without A5's equal-budget test".

### 15. Order row 1 breaks A6's own MPS rule and shares the machine with knob ceiling

- **Text:**
  - L112–113: A6 and "B1 R0/R1 … now";
  - L817: B1's embedding pass takes "a few hours on MPS or CPU";
  - L198: A6 "Never run it alongside another MPS job";
  - L519: "nothing runs 03:00–04:15".
- **What's wrong.**
  - Both start "now", so B1 on MPS would run alongside A6.
  - C′ training computes its spectral loss on the CPU (`residual-di-plan.md:158-160`), while
    knob ceiling's main run uses 6 render processes on an 8-core machine (KC, "The budget").
  - A ~15 h training run crosses the 03:00–04:15 window.
- **Corrected text (L112):** "A6 (Option 1): after knob ceiling's renders finish, or with its
  step time measured under contention first; B1's embedding pass runs on the CPU while A6
  trains; each ~5-h fold is scheduled outside 03:00–04:15 (or the window is confirmed not to
  apply to training)."

### 16. Report C and the goal change: items dropped without a verdict

- **What's missing.** §0.2 gives no verdict on several Report C recommendations that bear on
  B3's design, and draws nothing from the end-to-end runs:
  1. **Robust aggregation** of 2–4 guitar-active windows, and the **context view** (the
     original mix) in the score (report-c.md:269, 370-380). B3 uses two halves of the stem
     only.
  2. **A DI-free score ensemble** calibrated on 100–150 pairwise listening judgements
     (report-c.md:410-433). E1 and C1's H2 overlap with it, but this isn't said.
  3. **A known-target control spanning Tone King, edge-of-breakup and time-effect cases**
     (report-c.md:271). A5 and B3 are Morgan-only and dry.
  4. **Topology stages** (amp, channel, pedal on/off, mic identity) before knobs
     (report-c.md:174-181, 239-247). B3 searches K space per amp (fix 5).
  5. **Report C's bar of 16 of 20 cells (80%)**, against B3's control at 8 of 12 (67%).
  6. **The end-to-end runs' lesson.** With nothing documented, the guessed class was wrong on
     both packs and the second start caught it (`docs/e2e-runs-2026-10-13.md:19-22`). B3
     searches only from the true-class start; D2 searches from the class start and the
     neighbour start.
- **Corrected text (add rows to §0.2):**
  - "Multi-window robust aggregation and a mix-context term in the objective: **deferred**. B3
    keeps the halves for like-for-like with K_S; a report-only multi-window readout is added."
  - "Calibrated DI-free ensemble: **covered by** E1b (judge calibration) and C1's H2; revisit
    after C1."
  - "Tone King, EOB and time-effect known targets: **deferred to D1**."
  - "Topology stages: **deferred to D2/D1**; B3 tests K space only."
  - "Report C's 16/20 bar: B3 uses 8/12 (looser); reported."
  - **Under B3:** "Report-only: the routed class from the generate-routing re-check, and the
    neighbour start's S, because the class guess is the product's main error (end-to-end runs)."

---

## Suggestions (not required)

1. **Rename `C1-report-c-claims.md`.** It collides with step C1 (the learned ranker).
2. **B3's gate is a point-estimate screen; say so.**
   - The band-mean SE at band SD 0.101 is ≈ 0.026 for 14–15 bands, 0.030 for 11 and 0.038 for 7.
     Report the 90% interval beside the gate.
   - The crunch guard on 5 bands (SE ≈ 0.045) fails by noise 25% of the time at a true zero
     crunch effect, and 9% at a true −0.03. Use a harm threshold (crunch mean > +0.05) or the
     interval, consistent with knob ceiling's "crunch descriptive only" (KC:166).
3. **Define "not worse than the C′ menu pick"** as band-weighted, with a tolerance (e.g.
   ≤ +0.01).
4. **A5's design:**
   - Include knob ceiling's 6 v6 control cells as a reproduction check: `knob_search` at 200
     renders should reproduce +0.075.
   - Name the 2 amps.
   - Run two seeds for the stochastic arms.
   - Say how CMA-ES handles the switches and the 2 × 10 mic choices. An "outer loop" over 100
     mic pairs can't fit in 300 renders; knob ceiling's mic-alternative stage is a model.
5. **A5 can start earlier.** It reads no recording, so it can run as soon as the machine is free
   (as knob ceiling's control did during review), not after the report.
6. **B3 under Option 1 doesn't need A1 or A3.**
   - The 25's stems exist (songs check).
   - S, M and K_S come from knob ceiling's fresh isolated menus.

   Dropping the dependency shortens the critical path.
7. **MUSDB18-train overlap.** The separator was trained on these songs, so report B3 with and
   without them, as F1 does:
   - "It Was My Fault For Waiting" (Atlantis Bound, 2 clean parts in the 25);
   - "Femme" (Wall Of Death; set 3), per `docs/part-locator-truth.json`.
8. **Two stem caveats belong under B3's risks:**
   - The stems come from the instrumental mix, with vocals removed
     (`songs-check-results.md:53-54`). The product's songs have vocals.
   - `rebuilt_distance`'s proxy fallback is "untested on mixes" (`learn/rebuilt_judge.py:8`).
     Count its use per cell.

   Also state "uncut, at −22.9 LUFS" for x̂.
9. **A6:**
   - Validation losses aren't comparable across folds (different bands), and C′'s doesn't
     track picks (`residual-di-results.md:56-57`). Use the menu-pick check as the main check.
   - Before the rebuild, confirm that the PR12 `learn/direc/cache` still exists. A rebuild would
     add about 22 GB [I: 18,843 × 6 s × 48 kHz × 2 bytes × 2 arrays].
   - Confirm that free disk is ≥ 66 GB.
10. **Smaller wording fixes:**
    - L114 "K_S is B3's ceiling" → "B3's comparator (both are lower bounds)".
    - L79 "chosen on many of these parts" → "on 24 of the 25".
    - L76: note that B3 uses 150 renders per direction, not Report C's 500.
    - L82: B1 R0/R1 matches Report C's frozen "content-swap benchmark"; its 8–12k trained-encoder
      pilot is C1's role.
11. **A stale citation.** E2 cites `skills/generate/SKILL.md:430`; after #187 the second-start
    rule is at `:442`.
12. **§8 should gain the amendment's new risks:**
    - C′ is unproven on stems;
    - the control is in-domain for C′;
    - the SNR-selected 25;
    - CPU contention during A6.

---

## Items checked

| # | Claim (plan line) | Result | Evidence |
|---|---|---|---|
| 1 | Goal quote (L51–53) | OK, verbatim | `docs/ROADMAP.md:10-12`; added in b8194b6 (#187) |
| 2 | `match` isolates every Morgan render (L61) | OK | 718a5ca (#186): `scripts/match_preset.py`, `export_match_audition.py`, `measure_eq_basis.py` pass `isolate=True` for Morgan |
| 3 | Roadmap history moved; end-to-end runs (L62–63) | OK | 5e2caa4 (#188) |
| 4 | C′ only for fold 2 (L80, L190) | OK; three seeds, all fold 2 | `learn/residual_eval.py:30-32`; `set5-test-results.md:9` |
| 5 | 18 leak-free pinned parts in 8 bands | OK; reproduced from the catalog | `residual_eval.py:38-55`; fold 2 = Eat The Feeder, JMK, Zeno |
| 6 | "About 7 of 25" | Exactly 7 (7 bands, 3 clean, 4 crunch) | Fix 2 |
| 7 | Set-1 bands in C′'s training pool? | No; but no set-1 part is in the 25 | `di_pool.py:3-5,27-30`; `songs_check.py:86-93`; `generate-routing-parts.json` |
| 8 | Option 2 "about 8 bands", 0 renders | Wrong: 7, or 11 at ≈ 21k | Fix 2 |
| 9 | C′ ~6 h per fold "measured" | ≈ 4.9 h by steps; 6 h was R's superseded schedule | Fix 3 |
| 10 | Pair caches ~35 GB, rebuild only | OK; no new pair renders per fold | `residual-di-plan.md:92-93,138`; `direc.py:388-390` |
| 11 | `rebuilt_distance` against a stem, lag −52, fallback | Feasible (the songs check did it); fallback untested on mixes | `rebuilt_judge.py:1-8,34-44`; `songs_check.py:169-194` |
| 12 | K_S = 150 renders from S, cross-half, all 3 amps | OK; Honey's 3 cells drop | KC:31-32,36-41; `knob_ceiling.py:41-42,529-530` |
| 13 | Realistic shortfall 0.075, up to 0.26 | OK (+0.075; +0.255) | KC:287-300 |
| 14 | Exact control median ~75% | OK (75.5%); but it is the exact control, not A5's realistic one | Fix 8 |
| 15 | Set 4 −0.087, set 5 −0.124 / −0.023 | Set 4 is C, not C′; set 5 OK | Fix 1 |
| 16 | Random directions no better | OK | KC:233-234 |
| 17 | Tonal edits +0.014 (L101) | OK | `generate-routing-results.md:40` |
| 18 | Starts chosen on these parts | 24 of 25 | `clean-baseline-plan.md:20-22,51-53`; `crunch-baseline-plan.md:17-20` |
| 19 | A5 cost 10.8k, 1–1.5 h | OK (12 × 3 × 300; 0.8–1.4 h) | — |
| 20 | B3 cost 24.3k | 24.45k, plus 2.8k unbudgeted | Fix 6 |
| 21 | Main line 46k / 116k | Sum OK (46.1); omits 2.8k and the conditional 22.5k | Fix 11 |
| 22 | 6a 77k / 147k | Sum OK with 11k; §5 says 10k; F1 generation not costed | Fix 11 |
| 23 | 6b ≤ 102k; worst case ≈ 179k / 250k | 102.75k; 179.85k ≈ 180k; 250.15k ≈ 250k | Fix 11 |
| 24 | "Saves ~45–80k" | 35–78k | Fix 11 |
| 25 | Throughput ≈ 14k/h on 6 processes | OK as an upper bound (6 / 1.5 s); knob ceiling's own estimate 7.8–11.7k/h | KC "The budget" |
| 26 | Decision tree vs text | Gaps: no control-pass/gate-fail branch, no B3-again exit, A5 bypassed | Fixes 9, 10 |
| 27 | Product-session ownership | Stated in decision 12, not carried into 6a/D2 | Fix 12 |
| 28 | Decision 0.3, ledger | Not extended to A5/B3 | Fix 13 |
| 29 | Superseded CMA-ES / "no search budget" text | Not marked | Fix 14 |
| 30 | MPS / CPU / quiet-window scheduling | Conflicts | Fix 15 |
| 31 | Report C coverage, end-to-end runs | Several items without a verdict | Fix 16 |
| 32 | `C1-report-c-claims.md` exists | Yes (written 07:46, during review) | — |
| 33 | Stale citations after the merge | `SKILL.md:430` → `:442` | Suggestion 11 |
