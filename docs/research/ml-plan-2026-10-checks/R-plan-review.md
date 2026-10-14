# Independent review of `docs/research/ml-plan-2026-10.md`

Reviewed 2026-10-14 against the checkout (`origin/main` + docs commit `a0b09d2`),
`origin/ml/knob-ceiling` (`32266eb`), `origin/ml/egvae-lite`, `origin/product/match-morgan-isolate`,
the brief, both reports and the six check files. I opened every number marked "checked" in
section (d) at its repo source, not only in the check files. Plan line numbers refer to
`docs/research/ml-plan-2026-10.md` as committed.

---

## (a) Verdict

**Revise before committing. The structure holds, but 25 points need correcting.**

What holds:
- The order: carry-over audit, then label table, then zero-render screens and the ladder,
  then the gated pilot.
- It doesn't duplicate knob ceiling.
- The licence filtering of encoders.
- Almost every headline number: the oracle gaps, E0/E0b, near-tie stats, part and band
  counts, power, separator facts, disk and the GuitarToneAdapt profile.

The errors cluster in five places:

1. **A1 (the audit) can't deliver what the plan says it does.**
   - It wrongly says knob ceiling has no set-3 parts.
   - Its 25 parts cover only a minority of the parts behind the near-bar decisions it cites.
   - Its "check set 3 only if the 25 show an effect" logic doesn't fit a part-specific defect.
   - It can't tell carry-over from plugin or judge-code drift.
   - It leaves out several exposed pipelines and held-out results, including the plan's own
     room numbers.
2. **Three held-out and decision rules are mis-stated.**
   - The "20-band rule" is a power note for one effect, not a standing rule.
   - Recording new guitarists is ruled out by the brief, not an open user decision.
   - F1's Bayesian "futile" outcome is unreachable, and its primary comparator is not
     like-for-like.
3. **Noise and room arguments mix units and data sets.**
   - The per-pick near-tie gap (0.043) is used as if it were band-mean noise.
   - Held-out room numbers are presented as the development ceiling, while today's starts
     were chosen on those same development parts.
4. **B2 and C1 have specification errors.**
   - The measure DI runs at 48 kHz, not 44.1.
   - B2's DAC-4 control can't "reproduce E0b" on different parts against a different
     comparator.
   - C1's development gate uses SNR-filtered stems, which the project's own stem-test rule
     forbids.
   - C1's label scoring is unbudgeted (about 1.3M judge calls).
5. **Internal inconsistencies.**
   - The budget in the summary disagrees with §5, and the 200k claim fails if R5 runs.
   - §5's machine order contradicts the dependency table.
   - The decision tree contradicts the A2 reading table.
   - The knob-ceiling "little" reading is contradicted.

---

## (b) Required fixes (most severe first)

### R1. A1 says knob ceiling has no set-3 parts. It has five.

- **Plan text** (l. 257): "Set-3 parts are not in knob ceiling. Checking them needs ~33 × 111 ≈ 3.7k
  isolated renders."
- **What's wrong.** `songs_check.parts()` includes set-3 development parts that have a usable
  stem. Knob ceiling uses that function, so 5 of its 25 parts are set-3 parts (2 clean,
  3 crunch). The parts *not* covered are the other 28 set-3 parts: 3 clean, 8 crunch and
  17 high-gain.
- **Evidence:**
  - `docs/songs-check-plan.md:70-72` ("Sets 1–2 gain classes: 18 clean, 2 crunch. Set 3 stem
    parts: 2 clean, 3 crunch, 7 high-gain");
  - `learn/songs_check.py:80-85`;
  - `origin/ml/knob-ceiling:docs/knob-ceiling-plan.md:19-21` ("sets 1–2 development and set-3
    development parts");
  - `origin/ml/knob-ceiling:learn/knob_ceiling.py:526` (`check_parts` asserts set-3
    membership).
- **Corrected text:** "Knob ceiling includes 5 of set 3's 33 development parts (2 clean, 3 crunch).
  The other 28 (3 clean, 8 crunch, 17 high-gain) need ~28 × 111 ≈ 3.1k isolated renders, or
  11 × 111 ≈ 1.2k for the in-scope ones." Change the overview row (l. 191) and the §5 row
  (l. 687) to match.

### R2. A1 can't re-score the decisions that motivate it, and its trigger logic doesn't fit a part-specific defect

- **Plan text:**
  - l. 95: "A1 must re-score these";
  - l. 238: "Three decisions sat within 0.003 of their bars";
  - l. 258: "Do it only if the 25-part check finds a material effect";
  - l. 263: "≥ 99% of cells within 0.005".
- **What's wrong.**
  1. **The 25 parts don't cover the decisions.**
     - Residual-DI gate 1 and the C′/E0/E0b development numbers rest on the 18 residual
       parts. Those are the 16 pinned set-3 parts plus 2 fold-2 parts, and only about 7 of
       the 18 are among the 25.
     - The lowpass decision rests on all 33 set-3 parts × 3 amps.
     - The set-5 test is held out.
     - So the zero-render check can re-score none of the three cited decisions.
  2. **A null result on 25 parts says nothing about the rest.**
     - The defect is part-specific: it shows only where the guitar is near-silent early in
       half A (knob-ceiling amendment 3).
     - Making the set-3 check conditional on the 25-part result is the wrong trigger.
     - The zero-render screen should be the activity-mask count over *every* exposed part.
       It is plan step 3, but only for the 25.
  3. **Fresh true-DI menus refresh only the measure side of these decisions.**
     - The choose side was rendered in the same exposed pipelines: the rebuilt-DI menus for
       C, C′, lp3k and the stem kinds.
     - Those renders aren't refreshed, so "re-score" can only ever be partial.
  4. **Two of the three decisions are no longer live.**
     - Residual gate 1 was superseded by the second-seed rule ("unconfirmed") and then by
       set 5.
     - The lowpass that missed by 0.0009 was adopted by the user anyway, then retired on
       2026-10-11.
     - Flipping either changes no current decision.
  5. **The gate's tolerance is larger than the margins it is meant to protect.**
     - A per-cell tolerance of 0.005 can hide a systematic band-level shift of up to 0.005.
     - That is bigger than the 0.001–0.003 margins the plan cites as the reason for A1.
- **Evidence:**
  - `learn/residual_eval.py:38-55` (pinned parts in fold −1 or 2; `assert len(out) == 18`);
  - `docs/sound-desc-test-parts.json` (16 set-3 in-scope parts);
  - `docs/rebuilt-di-lowpass-results.md:16-19` (33 parts × 3 amps);
  - `docs/residual-di-results.md:8-10`;
  - `docs/ROADMAP.md:168-176`;
  - knob plan `:317-321`.
- **Corrected text (A1 Method and Gate).**
  - "1. Zero renders first: count parts whose guitar is near-silent in the first seconds of
    half A, with the judge's activity mask, over every exposed development part (the 52
    measfix parts, the 18 residual parts, set 3's 33) and over each held-out set's stored
    crops.
  - 2. Compare stored with fresh distances on the 25 knob-ceiling parts as stated.
  - 3. Whatever step 2 finds, re-render the flagged parts outside the 25 with `isolate`, on the
    measure side (≈ n × 111).
  - Gate: no material effect when ≥ 99% of part × amp × preset × half values are within 0.005
    **and** the band-weighted change in every recomputed decision statistic is below 0.001.
  - Report that the choose-side (rebuilt-DI) renders of past tests are also exposed and are
    not refreshed.
  - Residual gate 1 and the 3 kHz lowpass are no longer live decisions (superseded, and
    retired); re-scoring them is descriptive."

### R3. A1 can't tell carry-over from version drift

- **Plan text** (l. 245-250): it compares knob ceiling's fresh 2026-10-14 isolated distances with
  "the stored measfix distances" from songs-check (scored 2026-10-10) and rescore.
- **What's wrong.** Two things changed between those dates, not only the render order:
  - the judge module (`analysis/aligned.py` gained the v3 option in #148, 2026-10-10 20:53,
    after the songs-check scoring in #147);
  - possibly the plugin build.

  A stored-vs-fresh difference could come from either, and then "past numbers were wrong"
  doesn't follow. The fix needs no new renders: knob ceiling already holds same-day
  non-isolated menus, set aside in `cells-noprerol/`.
- **Evidence:**
  - `git log -- analysis/aligned.py` (3131493 after d8a905b);
  - knob plan `:342` ("The cells rendered with neither fix are set aside (`cells-noprerol/`,
    not used)").

  I checked that DI construction, crop, lag, latency, halves and judge options are otherwise
  identical: `knob_ceiling.py:354-364, 410-417` against `songs_check.py:103-116, 187-191`. The
  retired 3 kHz lowpass applies only to the rebuilt `amp` and `stem` kinds
  (`songs_check.py:116`), never to `measfix`.
- **Corrected text (add to A1 Inputs and Method):**
  - "(a) Re-score the stored measfix FLACs with today's judge code first. This separates
    judge-code drift and costs no renders.
  - (b) Compare knob ceiling's own no-fix menus (`cells-noprerol/`) with its isolated menus
    for the same cells. Same day, same plugin build, same code: the cleanest carry-over
    estimate.
  - (c) Only then compare the stored and fresh distances.
  - Use only the `measfix_A/B` keys of `songs-check/distances.json`. The `amp` and `stem`
    keys are rebuilt DIs with the retired lowpass."

### R4. The list of exposed pipelines and held-out results is incomplete

- **Plan text:**
  - l. 236-237: "Every Morgan menu pipeline on main is exposed: `phase2_set3`, …,
    `render_preset_panel`";
  - l. 270: "Held-out results. The set-5 test is also exposed."
- **What's wrong.**
  - Eight more scripts render Morgan in reused processes without `isolate`:
    - `learn/phase2.py:135`
    - `learn/oracle.py:65`
    - `learn/evaluate.py:145`
    - `learn/set3_confirmation.py:99` (the set-3 held-out confirmation)
    - `research/generate_routing.py:610` (the routing "tonal edits" arms)
    - `research/render_shortlists.py:94`
    - `research/starting_preset_listening.py:229` (the 17/21 pages)
    - `research/listening_check.py`
  - Held-out results built from exposed `confirm_run` renders include more than set 5:
    - the set-4 confirmation;
    - the clean and crunch baselines on held-out sets 1–2, i.e. this plan's own room
      numbers −0.131 and −0.104 (§2), computed "with no new renders" from confirm-run scores;
    - the set-3 held-out confirmation.
- **Evidence:**
  - `grep -n process_policy` on the files above;
  - `docs/clean-baseline-results.md:4-5`;
  - `docs/crunch-baseline-results.md:4-5`;
  - A2 check, table at l. 225-238.
- **Corrected text:** "Every Morgan menu pipeline on main is exposed, at least: [the nine listed]
  plus `phase2`, `oracle`, `evaluate`, `set3_confirmation`, `generate_routing`,
  `render_shortlists`, `starting_preset_listening` and `listening_check`. Exposed held-out
  results: set 5's test, the set-4 confirmation, the clean and crunch baselines on sets 1–2
  (the §2 room numbers) and the set-3 confirmation. Each is either re-rendered under a
  declared amendment with a ledger entry (a further use of that set) or reported as exposed.
  The user decides (Step 0)."

### R5. The "20-band rule" is not a standing rule

- **Plan text:**
  - l. 79-81: "It cannot meet the project's own rule that 'a fresh confirmation needs 20 or more
    new bands'";
  - l. 111 (§1.1 #19): "a standing project rule";
  - l. 127;
  - Step 0 #6 (l. 226);
  - F1 (l. 654-659).
- **What's wrong.** ROADMAP:107 summarises a power table for one specific effect: the
  3 kHz-cut chooser against a fair fixed preset, observed −0.143, with 96% power at 20 bands.
  The same source says a realistic −0.072 needs 40 or more bands. It is a power conclusion,
  not a declaration rule. The project declared a held-out test on 5 bands (set 5) after
  writing it.
- **Evidence:** `docs/fixed-level-rescore-results.md:67-79`; `docs/ROADMAP.md:104-107`;
  `docs/set5-test-plan.md:21-27`.
- **Corrected text:** "ROADMAP:107 is a power note for one effect size (−0.143 needs about 20
  bands; −0.07 needs 40 or more; `fixed-level-rescore-results.md:69-77`), not a rule. F1's own
  power (0.92 at −0.10, 0.45 at −0.05 on 11 bands) already says the same thing: F1 can confirm
  only effects of about −0.10 or larger, and is declared as estimation below that." Drop
  decision 6, or restate it as "declare F1 as estimation (recommended) or as a confirmation
  of a ≥ 0.10 effect".

### R6. The brief rules out new recordings; the plan treats them as open

- **Plan text** (l. 679, G): "New recordings of guitarists (DI plus mic'd amp) | User decision
  (ROADMAP step 9) | The only route to the 8–12 new crunch bands the project needs".
- **What's wrong.** The brief says: "Recording new guitarists isn't possible for the user." That
  closes the ROADMAP 8j/9 route the plan points to.
  - F1's 11 bands (crunch 9) are then the last fresh held-out material the project will
    have, apart from new open data.
  - The plan never says so, and it doesn't ask whether to hold any of it in reserve.
- **Evidence:** `research_notes/Song to preset ML approaches/_brief.md:129`;
  `docs/ROADMAP.md:316-321`.
- **Corrected text:** "New recordings | Ruled out by the brief (`_brief.md:129`) | The 8–12
  crunch bands ROADMAP 8j asks for won't come from recordings. F1 spends the last fresh
  held-out data." Add a Step 0 decision: "Spend all of sets 4 (unused), 5 and 6 in F1, or hold
  a declared reserve."

### R7. F1's "futile" reading can't happen

- **Plan text** (l. 656-658): "'futile' if P(|effect| < 0.03) > 0.8".
- **What's wrong.** With the plan's band SD of 0.101 and 11 bands, the standard error is 0.0305.
  - Even with a posterior mean of exactly 0 (flat prior), P(|θ| < 0.03) = 0.675 (t: 0.65).
    That is below 0.8.
  - At 8–9 stem bands it is 0.60–0.63.
  - So "futile" can never be declared, and F1 has two live outcomes, not three.
- **Evidence:** my computation (`scipy.stats`, normal and t): max P(|θ|<0.03) = 0.675 (11
  bands), 0.627 (9), 0.599 (8). For |θ| < 0.05 the maximum is 0.90 (11) and 0.84 (8).
- **Corrected text:** "'futile' if P(|effect| < 0.05) > 0.8 (reachable only near a zero mean at
  ≥ 9 bands). State the prior. Check reachability against the band SD before declaring."

### R8. F1's primary comparator is not like-for-like

- **Plan text** (l. 661-662): "Primary: band-weighted log ratio of what the product would output
  (best of 2 for the hybrid, top-1 for an automatic pick) against today's class-routed start."
- **What's wrong.** A judge-picked best of 2 is a perfect-ear upper bound.
  - The project measured the real ear at 0.25–0.34 of the perfect-ear gain.
  - Any pair that contains a second start beats a single start by construction.
  - So a useless model would "help".
  - E2 itself compares against the current two-option shell (l. 612-613), not the single
    start.
- **Evidence:** `docs/listening-check-results.md:51-52`; plan l. 612-613;
  `skills/generate/SKILL.md:430-435`. The second start is installed when the part isn't
  clean or its class is a guess.
- **Corrected text:** "Primary: top-1 against today's class-routed start for an automatic pick.
  For the hybrid, best-of-2 by the judge against the current shell's best-of-2 (the start
  plus the neighbouring class's start), labelled a perfect-ear upper bound. The ear's share
  comes from the declared listening subset."

### R9. Held-out room numbers are presented as the development ceiling

- **Plan text:**
  - l. 51: "So development tests can show at most about −0.13";
  - l. 147-148: "A development gate of −0.05 against today's start asks for 40–50% of that";
  - l. 526-527 (C1): "about 40–50% of the menu room".
- **What's wrong.**
  - −0.131 and −0.104 are held-out sets 1–2 numbers, and −0.129 is held-out set 5.
  - On development, today's starts were *chosen on the same parts*: 22 clean and 13 crunch
    development parts, mostly the 35 pinned ones. Their head start is unmeasured.
  - Development room against them on C1's 25 stem parts is unknown.
  - Development oracles against other comparators run from −0.087 (clean, 18 parts) to
    −0.260 (set 3, leave-band-out). Neither is "at most −0.13".
- **Evidence:**
  - `docs/clean-baseline-results.md:17, 23`;
  - `docs/crunch-baseline-results.md:13, 26`;
  - `docs/residual-di-results.md:39`;
  - `docs/fixed-level-rescore-results.md:25`;
  - A1 check A-31.
- **Corrected text:** "Held-out room against today's starts is −0.10 to −0.13. Development room
  against them is unmeasured, and those starts were chosen in-sample on the development
  parts. A4 measures the oracle's edge over today's start, and over a leave-band-out start,
  on C1's evaluation parts. C1's gate is declared as a share of that measured edge (e.g.
  ≥ 40%), not as a fixed −0.05."

### R10. C1's development gate uses SNR-filtered stems

- **Plan text** (l. 524-525): "product input = stem on the 25 parts with stems". B1 R4 (l. 399)
  does the same.
- **What's wrong.** The 25 "parts with stems" are the parts whose htdemucs stem reached
  ≥ 1 dB SNR against the amp track: the songs-check usability filter. The project ruled
  that a stem-based decision uses "no SNR filter: the product can't apply one". Stems can be
  made cheaply for every classed part with a mix (about 15 s wall per 30-s context), so the
  filter isn't needed.
- **Evidence:** `docs/songs-check-results.md:55-56`; `docs/set5-test-plan.md:156-157`;
  `learn/songs_check.py:37-38, 81, 89`.
- **Corrected text:** "Product input: the htdemucs_6s stem of the part's instrumental mix,
  with no SNR filter, for every A3 part that has a mix (separated in A3; about 65 × 15 s).
  The 25 usable-stem parts are reported as an optimistic subset."

### R11. The near-tie gap is used as if it were band-mean noise

- **Plan text:**
  - l. 97 (§1.1 #5): "the whole range is below the judge's 0.043 near-tie scale";
  - l. 149: "Differences below about 0.04 are inside the judge's own noise";
  - l. 430-431 (B2).
- **What's wrong.** 0.043 is the median per-cell gap between the best and second-best
  presets, and 0.04 is how far one pick moves between halves. Neither is the noise of a
  band-weighted mean over many cells. The project resolved band-mean differences of this
  size on these same 18 parts:
  - E0 against C′ was −0.029 [−0.054, −0.005];
  - E0b against C′ was −0.027 [−0.052, −0.001].
- **Evidence:**
  - `docs/closeness-review-2026-10-10.md:18-19, 66-68`;
  - `origin/ml/egvae-lite:docs/egvae-lite-plan.md:144, 263`.
- **Corrected text:**
  - §1.1 #5: "the whole C′-to-oracle range is 0.032, about 1.3× the 90% half-width of a
    band-mean difference on 8 bands (≈ 0.025). A dose curve would resolve one or two steps
    at most, and C′ is leak-free only on these 18 parts."
  - §2: "single picks within about 0.04 are near-ties; band-mean differences of about 0.03
    are resolvable on 8 bands."

### R12. B2's DAC-4 control is ill-defined, and its comparator is in-sample

- **Plan text:**
  - l. 436: "DAC-4, the control: must reproduce E0b within 0.01";
  - l. 449: "as a log ratio against today's start, divided by the oracle's".
- **What's wrong.**
  - **The control can't be compared.** E0b's −0.126 is on the 18 residual parts, against a
    leave-band-out fixed preset. B2 runs on 30 different parts (17 crunch + 13 clean)
    against today's start, so the number can't be reproduced.
  - **The edge ratio is unstable.** Today's crunch start was chosen on 13 development crunch
    parts, 11 of them among B2's 17. That shrinks the oracle edge (the denominator) on the
    same parts, so the edge ratio becomes unstable and biased.
- **Evidence:**
  - `origin/ml/egvae-lite:docs/egvae-lite-plan.md:118-120, 253-262`;
  - `docs/crunch-baseline-results.md:13`;
  - `docs/sound-desc-test-parts.json`.
- **Corrected text:**
  - "DAC-4 control: on the 18 residual parts, against the leave-band-out fixed preset,
    reproduce E0b's −0.126 within 0.01. That is 18 × 111 ≈ 2k renders, since E0b's renders
    were deleted. Or, on B2's parts, pick agreement with the oracle ≥ 90% (E0b: 92%).
  - Edge kept: the band-pooled ratio of mean log ratios against the leave-band-out fixed
    preset, with today's start reported beside."

### R13. B2's sample rates are wrong

- **Plan text** (l. 445-446): "Resampling: the measfix DI and DAC/BigVGAN run at 44.1 kHz. Any
  48 kHz path is resampled and stated."
- **What's wrong.** The measfix DI, the crops and the renderer run at 48 kHz. E0 resampled the
  measure DI 48 → 44.1 kHz for DAC and back.
- **Evidence:**
  - `match/renderer_au.py:68` (`SAMPLE_RATE = 48000`);
  - `learn/direc_check.py:31`;
  - `learn/confirm_run.py:77` (`assert sr == P.SR`);
  - `origin/ml/egvae-lite:docs/egvae-lite-plan.md:130-131` ("48 → 44.1 kHz (`resample_poly`
    147/160)").
- **Corrected text:** "The measfix DI and the renderer run at 48 kHz. DAC and BigVGAN-v2 run at
  44.1 kHz. Every rung is resampled 48 → 44.1 → 48 kHz with `resample_poly` 147/160, as E0
  did. The true-DI rung gets the same round-trip resample as a control, and every rung is
  re-normalised to −22.9 LUFS."

### R14. C1's label scoring is unbudgeted

- **Plan text** (l. 487-491): "3k off-menu targets … Their labels come from the same DI's menu
  renders, so they need no extra renders"; "Labels. Set-valued: every preset within ε of the
  best under the judge".
- **What's wrong.** No renders, but many judge evaluations, and none appear in the budget:
  - every in-menu render used as a target needs its 111 × 111 distance matrix per DI clip:
    80 × 12,321 ≈ 0.99M;
  - the off-menu targets need 3k × 111 ≈ 0.33M;
  - that is about 1.3M two-half evaluations in total.
  - Knob ceiling's 1.5 s per evaluation "render plus scoring", against 0.29–0.37 s per
    render, implies roughly 1 s of CPU per two-half score [I]. That is hundreds of
    CPU-hours, competing with separation and renders.
- **Evidence:**
  - knob plan `:116-118`;
  - `docs/measuring-against-the-plugin.md:337-342` (291 ms per render);
  - `docs/measuring-against-the-plugin.md:503` (370 ms).
- **Corrected text:** "Label scoring is about 1.3M judge evaluations (an estimated 1 s each,
  so about 360 CPU-hours [I]). Measure the time per score on the first 1,000 evaluations.
  Limit in-menu labels to the top-k by a cheap pre-filter, or subsample targets, to stay
  under a declared CPU budget."

### R15. A2's "little" reading contradicts knob ceiling's own reading

- **Plan text** (l. 300): "≥ −0.04 | 'The search found little: undecided' | No more search
  budget. The optimiser is not the bottleneck to buy (§1.1 #9)."
- **What's wrong.**
  - Knob ceiling reads "little" as *undecided* precisely because its search can fall short:
    0.075 on average on the realistic control, up to 0.26.
  - FXRepBench shows CMA-ES is no better than random at equal budget. It doesn't show that
    more search can't find more.
  - The threshold is "band-weighted and part-weighted both ≥ −0.04", not a single number.
- **Evidence:** knob plan `:188-193, 256-263, 297-307`; B1 check §2.
- **Corrected text:** "Both means ≥ −0.04 | 'The search found little: undecided' (the search
  is 0.075 short on the realistic control) | No further search budget now, as a cost
  choice. The menu question stays open."

### R16. The decision tree contradicts A2's table and D2's dependency

- **Plan text:**
  - l. 715: `K -->|little or between| M[stay with the menu]`;
  - l. 726: `D1 --> D2` only.
- **What's wrong.**
  - The A2 table (l. 301) sends "In between" to "D1 only for cells listening confirms".
  - The overview (l. 200) and D2's heading (l. 562) allow "D1 or A2".
- **Corrected text:** add `K -->|between, heard per cell| D1` and `K -->|a lot, heard| D2`, and
  relabel the menu edge `little`.

### R17. Render budget: the summary disagrees with §5, and the 200k claim fails

- **Plan text:**
  - l. 82-83: "About 42k new renders up to the learned-model pilot, and about 115k at most if
    every branch opens";
  - l. 697: "Everything together stays under the 200k flag".
- **What's wrong.**
  - §5 gives ≤ 46k cumulative through C1 and ≤ 125k overall. The 42k and 115k leave out
    A1's +3.7k and E1/F1's 6k.
  - With B1's optional R5 (≤ 11k), the total is 125k + 70.3k (knob ceiling) + 11k ≈ 206k,
    which is over the brief's flag.
  - D2 (150–600 per song) and A2's added v3 renders (~150) aren't counted.
- **Evidence:** plan l. 685-694; `_brief.md:92`.
- **Corrected text:** "≤ 46k through C1 (≤ 42k without the set-3 audit); ≤ 125k if every branch
  opens, ≤ 136k with R5. With knob ceiling's ~70k, everything stays under 200k only if R5 is
  skipped or D1 is capped at 19k."

### R18. §5's machine order contradicts the dependencies

- **Plan text** (l. 700): "A1, A4 and B1 need no renders and can run while it renders".
- **What's wrong.**
  - The overview makes A4 and B1 depend on A3 (l. 194-195), which renders. R3 and R4 need
    A3's audio.
  - A1 needs knob ceiling's menus for all 75 cells, so it can't finish before knob ceiling
    nearly ends.
  - Only B1's R0 and R1, A4(c) and E1(b) are truly independent now.
- **Corrected text:** "While knob ceiling renders: B1 R0/R1, A4(c) (second-mic floor), E1(b)
  page building and D4. A1 runs once every knob-ceiling menu exists. A3 renders after A1, and
  A4(a, b, d), B1 R3/R4 and B2 follow A3."

### R19. The licence rule is stricter than the brief, and inconsistent with F1

- **Plan text:**
  - l. 179-180: "open only (MIT, Apache, BSD, CC0, CC BY). Non-commercial data or weights are
    used only if the user explicitly accepts them";
  - l. 224-225: "Default: not, per the brief's licence rule."
- **What's wrong.** The brief's open-only rule covers tools and weights, not data. The project
  already uses non-commercial research data, and F1 relies on it:
  - set 6 is MedleyDB, CC BY-NC-SA, granted to the user for non-commercial research;
  - set 5 and the Cambridge development sessions are Mixing Secrets material for
    "non-commercial research and educational purposes" only.
- **Evidence:**
  - `_brief.md:50-53`;
  - `docs/validation-set6.md:315-327`;
  - `docs/validation-set5.md:118-127`;
  - `docs/validation-datasets.md:28`.
- **Corrected text:** "Weights and tools: open licences only (MIT, Apache, BSD, CC0, CC BY), per
  the brief. Data: non-commercial research licences are already in use (MedleyDB, Mixing
  Secrets). GOAT (CC BY-NC, access by request) is the same kind, so decision 5 is whether to
  request access, not a licence exception."

### R20. Step 0 is missing decisions the plan defers to the user

- **Plan text:**
  - l. 270-272: "Re-rendering held-out audio is a held-out use … The user decides";
  - l. 679 (G): "User decision".
- **What's wrong.**
  - Neither is in the Step 0 list.
  - The second one is already settled by the brief (R6).
  - The held-out reserve question (R6) is also missing.
  - So is the exposure of the other held-out results (R4).
- **Corrected text:** add "8. A1's exposed held-out results (set 5, set 4's confirmation,
  sets 1–2 baselines): re-render under declared amendments, or report as exposed. 9. Whether
  F1 spends all remaining held-out bands or keeps a reserve."

### R21. §1.2 says knob ceiling covers three of Report B's levels; it covers a different three

- **Plan text** (l. 117): "B's four levels are useful; knob ceiling covers the first three except
  pedals."
- **What's wrong.** Report B's levels are:
  1. the menu oracle;
  2. a continuous dry chain;
  3. a continuous **full chain with time effects**;
  4. a listening-confirmed oracle.

  Knob ceiling keeps time effects off. It covers levels 1, 2 (without pedals) and 4 (its
  listening page), not level 3.
- **Evidence:** `report-b.md:17-22`; knob plan `:78-81, 198-208`.
- **Corrected text:** "knob ceiling covers levels 1, 2 (without pedals) and 4; level 3 (time
  effects) is D1."

### R22. D3's gate is labelled as an E2 rule, but E2 has none

- **Plan text** (l. 579): "Gate. The `ml/egvae-lite` E2 rule against C′: …".
- **What's wrong.** These are E1's set-5 rule (≤ −0.015 with the upper bound < +0.03) and the
  original EG-VAE-lite futile rule (lower bound > −0.02). The plan repeats the error the A1
  check flagged in Report A (A-34).
- **Evidence:** `origin/ml/egvae-lite:docs/egvae-lite-plan.md:63-67, 236-238`; A1 check A-34.
- **Corrected text:** "Gate: `ml/egvae-lite`'s E1 rule against C′ (l. 236-238) and its original
  futile rule (l. 63-67): …"

### R23. Dead-ends power claim is wrong for 5–6 bands

- **Plan text** (l. 749): "Use top-1 held-out gates on ≤ 6 bands | Sign-flip p ≥ 2^−k; power below
  0.5 even at −0.10".
- **What's wrong.** At SD 0.101, one-sided α 0.05, power at −0.10 is:

  | Bands | Power |
  |---|---|
  | 3 | 0.32 |
  | 4 | 0.45 |
  | 5 | 0.57 |
  | 6 | 0.67 |

  The 5-band figure is in A3's own table.
- **Corrected text:** "… on ≤ 6 bands | Sign-flip p ≥ 2^−k; power at −0.10 is 0.32–0.67, and
  0.15–0.28 at −0.05".

### R24. F1's stem-eligible band count is too high

- **Plan text** (l. 645): "Count stem-eligible bands at declaration; expect about 8–10 [I]."
- **What's wrong.** Under the plan's own exclusions the maximum is 9, and only 5 are confirmed:
  - set 5: 4 bands with a mix (BKS, Hazael, Ronnie Jones, Saturn Syndicate; Ferryboat Men
    has none);
  - set 6: 1 (Little Tybee);
  - set 4's unused sessions: up to 4. Their crop records carry no mix hashes, unlike set 5's
    after its amendment 2.
- **Evidence:** `docs/validation-set5.json` (`crop.mix_absent` on Fytakyte and Ferryboat Men);
  `docs/validation-set4.json` (no mix fields); `docs/validation-set5.md:106-115`.
- **Corrected text:** "at most 9 (set 5: 4; set 6: 1; set 4: up to 4, mixes to be verified),
  5 confirmed today."

### R25. Two smaller factual and consistency errors in A1 and A3

1. **The 20 pre-roll cells** (l. 275-276): "20 knob-ceiling cells used the 6-s pre-roll fix
   … They matched within 1.4e-4".
   - Only two of the 20 cells' menus were cross-checked (160 scores). The pre-roll fix
     leaves up to 1.2e-4. Knob plan `:333-339`.
   - Corrected text: "Two of them were cross-checked against `isolate` (160 scores, ≤ 1.4e-4);
     all 20 are usable at A1's 0.005 tolerance."
2. **The songs-check recompute** (l. 254-255): "recompute the songs check (−0.114) … with the
   fresh distances".
   - Fresh true-DI menus refresh only the measure side. −0.114 is the stem-kind pick of the
     old fold networks with the retired 3 kHz lowpass (`songs_check.py:113-116`), and its
     choose-side renders are exposed and not refreshed.
   - The routing re-check used 34 parts, of which about 24 are in knob ceiling.
   - Corrected text: "recompute the measure side of the songs check and of the routing
     re-check on the covered parts (descriptive)."

Also: A3's optional Tone King renders (l. 327-328) need the same reuse+isolate
repeatability check that C2 requires (l. 548; A2 item 4). Otherwise use fresh processes, at
about 5 s each and licence-service wear.

---

## (c) Suggested improvements

**A1 and A3**
- Define "cell" in the A1 gate as a part × amp × preset × half value. Ignore pick changes
  where the stored best-vs-second margin is below the repeat floor (about 2e-4): with 150
  picks, about one flips by noise.
- Reading knob ceiling's menus reveals its headline (a), M vs S, before its report. Either run
  A1 after that report, or declare A1 as a knob-ceiling amendment.
- A3's check "new distances must match stored within 0.005" (l. 335-336) is vacuous when A1
  is null, because nothing is re-rendered. Re-render a 3-part overlap (333 renders) as a
  pipeline check in every branch.
- Reuse A1's isolated set-3 renders as A3's re-renders for those parts. This avoids
  double-counting about 1.8k.
- Trim the first 0.25 s of every isolated render used as *audio* (C1 bank, B1 prototypes).
  `isolate` fades in over that span (knob plan `:336`).

**A2 and A4**
- A4(c) needs no A3 table, and neither does building E1(b)'s page: set-3 v3 cells already
  exist. Start both now.
- Define H when d_best < d_floor. `measuring-closeness.md:231-234` notes that another review put
  the best preset closer than the second mic.
- Knob ceiling (main run from 06:27, 6–9 h) may report before A2's proposed amendment. Give a
  fallback: label the additions post hoc.
- List the ~150 v3 renders in the overview (now "0 new").

**B1**
- Specify per-amp picks in R3, matching the judge's per-amp oracle and the start.
- R3 reuses the encoder's screen-2 design, which failed. Say that a pass needs the
  most-picked < 25% guard, which that encoder broke (18 of 25 on one preset).

**B2**
- Anchor the 80% and 50% thresholds with C′'s own edge kept on the same metric. That costs
  zero renders on the 18 parts: C′ keeps about 0.099/0.131 = 76% against the leave-band-out
  preset. "≥ 80%" then means "better than C′".
- Make the readings table exclusive. For example, Griffin-Lim ≥ 80% with DAC-2 < 50% fires
  both "magnitude is enough" and "close the route".
- Score under v3 too, as Report A planned.
- The optional symbolic rung and DAC-8 were dropped silently. State why: DAC-8 ≈ E0.

**C1**
- Sum a second guitar in some mixes. Multi-guitar stems sit at 0.74 dB SNR, and 54 of 61
  parts are multi-guitar.
- Add codec perturbation.
- Add Report B's stop rule: stop if the gain vanishes when the backing distribution changes.
- Calibrate the 75% domain-probe bar against a real-vs-real control first. Otherwise
  "stop after two rounds" may fire by default.
- Specify the random-setting space for off-menu targets: knob ceiling's space, and whether
  pedals are included.
- Each of the 3k targets must use one of the 80 DI clips (≈ 37 per clip).
- State the number of fold models and the training cost.
- Say what happens when the positive control fails (fix and rerun, at most N times).
- Use only DIs with a verified role. The 54 unclassed parts include failed pairings.
- "Songs are near 0 dB" (l. 494) has no source. Tag it [I] or measure it from the
  development `mix` and `backing` files.
- Training clips are separated without the 30-s context the product uses. State the
  mismatch.
- The separation script isn't committed (A2 item 8). Add "write or recover it" to C1.
- Step 0 #3 lifts the constraint on the 33 for measurement only (A3, A4, B1, B2), but C1's
  decision gate uses 5 of the 33. Name C1 explicitly, or exclude those parts from the gate.

**D steps**
- **D2:** make the band the unit, and score on the held half.
- **D2:** cite FXRepBench's positive lesson for the per-song budget: a learned proposal
  (Head@16) matched Random@512.
- **D3:** C′-family networks have never been run on separated stems (A2 item 9). Add a
  development stem check before any stem-based F1 arm.
- **D3a:** add B2-check notes: Distortion Recovery's "28.65 dB SI-SDR" is very likely a sign
  error (no waveform kept), which supports a phase-free route.
- **D3b:** EG-VAE's latent is not the released DAC.
- **D4:** cite the existing negative result: RT60-based reverb on played material was at
  chance, 4 against 5 of 12 (`match/invert.py:64-71`; `round-2-full-plugin-estimation.md:125`).
- **D4:** dry amp tracks carry no song effects, so say what the ground truth is.

**E steps**
- **E1(c):** say it runs on development songs only.
- **E2:** "−0.081" is a paired drop in *routing regret* (0.140 → 0.059), not a closeness
  gain. The second start is installed only for parts that aren't clean or whose class is a
  guess (`skills/generate/SKILL.md:430`).
- **GuitarToneAdapt:** keep the Hotel California record out of any tuning on the end-to-end
  test (B2 check).

**F1**
- "~5k renders" is low if both a C2 survivor and a D3 rebuilt-DI survivor need menus. That
  is about 4.3k per DI route on top of the oracle.
- Sizing set 5's second use with set 5's own band SD is a mild double dip. Say so.

**Wording and corrections**
- "B's 7–15% exceeds the menu room" (l. 120): only the upper end does.
- "MedleyDB labelling is exhausted" (l. 103, 744): 89 envelope-only pairs were never shown
  (`docs/set6-di-labelling-plan.md:55-57`). Say "nearly exhausted".
- Appendix 14: Report A's "~40k" equals the reuse case (12 × 30 × 111). Its error was
  "~37k if rung 1 is reused".
- Report A's drive-bias correction (top-3 most-driven) is not the quieter-DI trim that was
  tried. Dropping it is still justified by "under-drive is not the main cause", so cite that
  rather than "tried".

**Disk**
- Add a cumulative disk table: A3 4–8 GB, C1 ~5 GB, C2 ~15 GB, knob ceiling's FLACs. Rebuilding
  C′ pair caches (~35 GB, `residual-di-plan.md:92`) for any D3b control would take the whole
  usable 35 GB.

---

## (d) Items checked directly in the repo

Status: **OK** = matches the source. **WRONG** = error, with the fix in (b). **NUANCE** =
right, but the plan's use needs a caveat.

| # | Plan claim | Source checked | Status |
|---|---|---|---|
| 1 | Clean oracle −0.131 (13 parts, 8 bands, held-out sets 1–2) | `clean-baseline-results.md:23,44` | OK (held-out, not development: R9) |
| 2 | Crunch oracle −0.104 (7 parts, 3 bands) | `crunch-baseline-results.md:26,33` | OK ("per half"; held-out) |
| 3 | Set 5 crunch oracle −0.129, C′ −0.023 | `set5-test-results.md:19-21,44` | OK |
| 4 | Tone King −0.191 / −0.164 | `toneking-baseline-results.md:48` | OK |
| 5 | Development: oracle −0.131, C′ s0 −0.099 (18 parts, 8 bands) | `residual-di-results.md:31-39`; `residual_eval.py:38-55` | OK |
| 6 | E0 −0.129 (91%), E0b −0.126 (83%) | `egvae-lite-plan.md:136-142,253-262` | OK |
| 7 | Near-tie 0.043 / 10% / 27% | `closeness-review-2026-10-10.md:66-68` | OK, but misused as band-mean noise (R11) |
| 8 | Classed clean 48 in 16 bands, crunch 17 in 8 | `part-locator-truth.json` (counted) | OK |
| 9 | 35 pinned in 15 bands; 11 of 13 crunch in the 33 | `sound-desc-test-parts.json` + `validation-set3.json` (counted: 17+2 sets 1–2, 5+11 set 3) | OK |
| 10 | 25 songs-check parts, 20 clean / 5 crunch | `songs-check-plan.md:70-72`; knob plan `:19-21` | OK |
| 11 | "Set-3 parts are not in knob ceiling" | `songs_check.py:80-85`; `knob_ceiling.py:526` | WRONG (R1) |
| 12 | C′ leak-free 18 parts, 8 bands | `residual_eval.py:38-55` | OK |
| 13 | Held-out pool 39 parts / 11 bands; set 4 unused 10 (2 clean, 8 crunch) in 4 | `validation-set4.json` `counts`, `held_out_uses`; `set5-test-plan.md:21-27` | OK |
| 14 | Stem-eligible bands "about 8–10" | `validation-set5.json` `crop.mix_absent`; `validation-set4.json` | WRONG (R24) |
| 15 | Residual gate 1 passed by 0.001 | `residual-di-results.md:20` | NUANCE (superseded, `:8-10`; R2) |
| 16 | Set 5 passed by 0.003 | `set5-test-results.md:11-12`; `ROADMAP.md:291` | OK |
| 17 | 3 kHz lowpass missed by 0.0009 | `rebuilt-di-lowpass-results.md:9-10,22-23` | NUANCE (adopted, then retired: `ROADMAP.md:168-176`) |
| 18 | Knob ceiling: ~70.3k renders, 6 versions failed, 0.075 short, readings −0.04/−0.10 | knob plan `:115-118, 210-307, 185-193` | OK; "little" reading contradicted (R15) |
| 19 | Amendment 3: 3.42 vs 3.92; spread 0.138; `isolate` | knob plan `:313-331` | OK |
| 20 | 20 pre-roll cells "matched within 1.4e-4" | knob plan `:333-339` | WRONG (only 2 of 20 checked; R25) |
| 21 | Same DI, crop, judge options for the A1 comparison | `knob_ceiling.py:354-364,410-417` vs `songs_check.py:103-116,187-191` | OK (lowpass only on the rebuilt kinds); drift confound (R3) |
| 22 | Exposed pipelines list | `grep process_policy learn/ research/` | WRONG (incomplete; R4) |
| 23 | No `isolate` in research pipelines | `grep isolate learn/ research/` | OK |
| 24 | Product branch: "the ML session audits its own pipelines" | `origin/product/match-morgan-isolate` ROADMAP diff | OK |
| 25 | htdemucs 1.11 / 0.63 dB; single 5.86, multi 0.74; 15 s wall per 30 s | `separator-upgrade-results.md:15-17,55-60` | OK |
| 26 | The 20-band "rule" | `ROADMAP.md:104-107`; `fixed-level-rescore-results.md:67-79` | WRONG (power note; R5) |
| 27 | Routing −0.081 | `generate-routing-recheck-results.md:14-20` | OK (regret units, in-sample) |
| 28 | 17/21, p 0.004 | `starting-preset-listening-results.md:10-13`; recomputed p 0.0036 | OK |
| 29 | Effects +0.001 | `generate-routing-results.md:41,51` | OK |
| 30 | Second-mic floor on 23 parts, older measure | `measuring-closeness.md:226-234` (ALM) | OK |
| 31 | Disk: 65 GB free, 30 GB floor → 35 GB usable | `_brief.md:421`; `validation-set4-plan.md:329-331`; `residual-di-plan.md:92-93` | OK |
| 32 | `match/invert.py` delay, reverb and tremolo estimators; RT60 probe-only; D-M7 | `invert.py:64-71,854,921,952,1037`; `ROADMAP.md:400,501` | OK |
| 33 | Tone King menu 125 + Default | `toneking-baseline-plan.md:17-34`; `tk_baseline.py` | OK |
| 34 | Tone encoder used same-setting/different-DI positives, same-DI negatives, prototypes | `tone-encoder-plan.md:15-42,95-106` | OK |
| 35 | 16,800 crossed renders, 6 s, 7 DI windows, FLAC | `tone-encoder-plan.md:17-30,151-152` | OK (peak-normalised) |
| 36 | "Under-drive is not the main cause"; 43 vs 14 | `underdrive-trim-results.md:8-9,16-19`; `closeness-review:80-81` | OK |
| 37 | MedleyDB: 68 groups shown, 5 parts | `set6-di-labelling-plan.md:53-57,71-82` | NUANCE (89 envelope-only pairs not shown) |
| 38 | Port St Willow: electrical drive path; sensitivity required | `validation-set6.md:597-611` | OK |
| 39 | Held-out rule; no listening to sets 5 and 6 | `validation-datasets.md:185-191`; `validation-set6.md:24-27` | OK; plan complies, except the unlisted exposures (R4) |
| 40 | No development ledger exists | `ls docs/*ledger*`; `closeness-review:121` | OK |
| 41 | Sets 1–2 had 5 held-out uses | A1 check L; `validation-datasets.json` `held_out_uses` | OK |
| 42 | Power 11 bands 0.92 / 0.45; 15 bands 0.57 at −0.05; 27 bands for −0.05 | recomputed (scipy nct) | OK |
| 43 | Bayesian "futile" P(\|θ\|<0.03)>0.8 | recomputed (max 0.675) | WRONG (R7) |
| 44 | "Power below 0.5 even at −0.10" on ≤ 6 bands | recomputed (0.57 at 5, 0.67 at 6) | WRONG (R23) |
| 45 | Measfix DI and DAC/BigVGAN "at 44.1 kHz" | `renderer_au.py:68`; `direc_check.py:31`; `egvae-lite-plan.md:130` | WRONG (R13) |
| 46 | D3 gate called "E2 rule" | `egvae-lite-plan.md:63-67,201-205,236-238`; `egvae-e1-results.md:68-70` | WRONG (R22) |
| 47 | Render arithmetic: 30 × 7 × 111 = 23.3k; 80 × 111 = 8.9k; 3.3k + 3.9k = 7.2k | recomputed | OK |
| 48 | Summary budget 42k / 115k vs §5 ≤ 46k / ≤ 125k | plan l. 82-83 vs 685-694 | WRONG (R17) |
| 49 | Recordings as an open user decision | `_brief.md:129` | WRONG (R6) |
| 50 | Licence rule "per the brief" | `_brief.md:50-53`; `validation-set6.md:315-327`; `validation-set5.md:118-127` | WRONG (R19) |
| 51 | Report B levels covered by knob ceiling | `report-b.md:17-22`; knob plan `:78-81` | WRONG (R21) |
| 52 | C1 stems with an SNR filter vs the project's stem rule | `songs-check-results.md:55`; `set5-test-plan.md:156` | WRONG (R10) |
| 53 | GuitarToneAdapt: 1,252 entries, 37.8% unsourced, 47.3% ≥ 0.7, no crunch, no Eden | B2 check profile (`guitar-tones.json` not re-parsed) | OK (via check) |
| 54 | Two-option shell = start + neighbouring start | `skills/generate/SKILL.md:430-435` | NUANCE (only for parts that aren't clean or have a guessed class) |
