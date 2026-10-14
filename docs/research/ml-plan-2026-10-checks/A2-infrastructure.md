# A2: what already exists for the proposed experimental programme

Inventory as of 2026-10-14, read from git only. Sources: the checkout (origin/main plus one docs
commit, `a0b09d2`) and `origin/ml/knob-ceiling`, `origin/ml/set6-di-labelling`,
`origin/ml/egvae-lite`, `origin/poc/sound-model`, `origin/codex/*`. I also fetched one branch
the brief didn't list: `origin/product/match-morgan-isolate` (see item 2).

Citations take two forms:
- `path:line` refers to the checkout;
- `branch:path:line` refers to an unmerged branch.

**Caveat:** `~/ndsp-presets/` is the user's Mac, not this container, so nothing on that disk
could be checked. Every storage claim below is what code or docs say was written. The docs
record some deletions, and I list those.

Report A's plan is in `research_notes/Plan verification/_report_A_ours.md` (§2.0–2.4). It is
byte-identical to `docs/research/ml-approach-research-2026-10.md` and
`reports/Song to preset ML approaches.md`. Report B is `_report_B_second_agent.md`, section
"Concrete experimental programme".

---

## 1. ROADMAP: next steps, declared, planned, in progress, and awaiting the user

**Exists.** `docs/ROADMAP.md` is "the one living plan". It was last edited 2026-10-12, with a
merge on 10-13 (`docs/ROADMAP.md:4`).

**State.**

*"Next, in order", step 0 (song-to-preset model)* (`docs/ROADMAP.md:68-336`):

- **Done, measured:**
  - 1: fixed driven presets (`:141-148`).
  - 2: gap split (`:149-158`).
  - 3: reference-proxy fallback (`:159-160`).
  - 4: DI-network repairs, paused, then reopened by the MPS bug (`:161-193`).
  - 5: set-4 confirmation (`:196-211`).
  - 7: songs check (`:215-219`).
  - 8b, 8c, 8d, 8e, 8f, 8g, 8h (`:223-298`).
- **8i, set 6:** 5 parts labelled by ear, unused. Its next step is
  "recompute the deciding test's power with set 5 plus set 6 (8j)" (`:299-313`).
- **8j, the deciding song-level test: no power** (`:314-318`). Its note was written before set
  6's amendment 2 "so it is to be recomputed".
- **9:** "If it doesn't pass: close the rebuilt-DI chooser for the product. The candidates left
  are a cheap direct-ranker test, and recording a few guitarists (DI plus mic'd amp) for data"
  (`:319-321`).
- **10:** remove research records when the plugin is ready (`:322-323`).
- **Product checks (step 6, `:411-435`):** routing measured and re-checked; starting-preset
  listening heard 17/21. Still open: "**Another end-to-end run** of `generate` on a clean or
  Tone King song" (`:434-435`).
- **Parked** (`:325-336`):
  - network improvements;
  - judge v2;
  - "**Search beyond the menu:** on high-gain, the oracle's headroom (−0.17) is out of the
    rebuilt DI's reach" (`:329-330`);
  - the four Internet Archive sessions;
  - set 5, "Kept for the next declared test" (`:336`).
- **Standing constraint** (`:127-129`): "no more chooser or judge tweaks on the 33 development
  parts until the listening check is in". The heavy-tone check has since run
  (`docs/heavy-listening-results.md`: block 1 "neither", block 2 inconclusive). The roadmap
  never lifts the constraint explicitly.
- **Fresh confirmation size** (`:107`): "A fresh confirmation needs 20 or more new bands."

*In progress but not in the ROADMAP* (the ROADMAP doesn't mention knob ceiling, EG-VAE-lite or
the part locator):

- `ml/knob-ceiling`: declared 2026-10-13; main run restarted after amendment 3 on 2026-10-14
  (item 2).
- `ml/egvae-lite`:
  - E0 and E0b passed;
  - E1 failed pre-check 1 and is closed
    (`ml/egvae-lite:docs/egvae-e1-results.md:7-12,58-66`);
  - E1′ is "not declared"; the declared next step is E2 (`:63-70`).
- Part locator: step 1 done, underpowered (item 12).
- `product/match-morgan-isolate`: an unmerged product fix (item 2).

*Decisions awaiting the user (quoted):*

1. 8j: "Proposed: close the chooser for the product (step 9), keep C′ for research, and reopen
   with 8–12 new crunch bands recorded with a DI. The user decides." (`docs/ROADMAP.md:316-318`;
   also `docs/stem-test-power.md`, "Consequence (proposed; the user decides)").
2. Judge v3: "**Adoption is the user's call, after the listening calibration.** The built
   heavy-tone check doesn't target where v3 and the current judge disagree."
   (`docs/judge-v3-results.md:107-108`)
3. Direct ranker: "The owner must endorse this target in the later declaration. If the intended
   product instead requires a specific guitar within simultaneous parts, this experiment needs a
   different declared target and is not ready to run."
   (`docs/research/direct-preset-ranker-proposal-2026-10-09.md`, "Admission" section)
   Index: "Not declared; metadata admission, complete guitar targets and target interpretation
   remain unresolved. Its proposed equal-weight compromise is not adopted."
   (`docs/README.md:196-199`)
4. Recording guitarists, DI plus mic'd amp (`docs/ROADMAP.md:320-321`;
   `docs/stem-test-power.md`: "The remaining route is recording players directly").

**Implication for the plan.**

- Report A's programme is a new step-0 branch. It has to be reconciled with 8j and step 9, which
  are still open, rather than presented as the next numbered step.
- The plan should state whether it supersedes the 10-10 "no tweaks on the 33" constraint.
- The direct ranker (A's approach 1 baseline) and recording players are the roadmap's own
  fallback candidates. The plan is consistent with them, but it needs the user's decision on 8j
  first, or alongside.

---

## 2. `ml/knob-ceiling`

**Exists.** Three files, not merged into main:

- `origin/ml/knob-ceiling:docs/knob-ceiling-plan.md` (373 lines);
- `learn/knob_ceiling.py` (818 lines);
- `tests/test_knob_ceiling.py`.

The last commit is `32266eb`, 2026-10-14 06:27 +03:00: "isolate (rebuild render resources)
instead of a 6-s pre-roll".

**State.**

- **No results are committed.** There is no `knob-ceiling-results.md`, and none of the plan's
  outputs are in git.
- **Latest amendment:** 3 (`plan:309-347`).
- **The controls have run and failed:**
  - amendment 1: the exact positive control failed under 6 search versions (`:210-265`);
  - amendment 2: v6 also fails the exact control, mic recovered 1 of 6 (`:267-307`);
  - the realistic calibration lands 0.075 short on average on the held half (`:297-307`);
  - so every searched number is read as a **lower bound** (`:254-263`).
- **The main run was stopped once** by the repeat check (amendment 3), then restarted with
  `isolate`.
- **Order of work** (`:356-362`): "3. Message the product session, then the main run (6
  processes, `setopt no_bg_nice`). 4. The report, an independent audit of it, then the listening
  page."

**What it does** (`plan:10-15,19-27,34-50,52-85,111-122`):

- **Parts:** `songs_check.parts()` in clean or crunch, 25 development parts in 15 bands (20
  clean, 5 crunch).
- **DI and judge:** the true DI as `measfix`, judged with `flat` on halves A/B.
- **Searches, per part × amp cell (75 cells):**
  - M: menu oracle;
  - K_M: from M, 200 renders;
  - K_S: from the product start S, 150 renders;
  - EQ: from K_M's best, 100 renders.
- **Cross-half scoring** in both directions.
- **Search space:**
  - input gain −20 to +12 dB;
  - each amp's knobs and switches;
  - both mic types (10 internal);
  - cab position and distance;
  - right mic level and on/off;
  - then the 9-band EQ plus HPF/LPF.
- **Optimiser:** coordinate search plus Hooke–Jeeves, mic alternatives and restarts
  (`knob_search`). It is **not** CMA-ES.
- **Rendering:** 6 reused processes, `isolate=True`
  (`origin/ml/knob-ceiling:learn/knob_ceiling.py:387`).
- **Budget:** "about 25 × 111 + 75 × 2 × 450 ≈ **70,300 renders** … about 6–9 hours"
  (`plan:115-118`). The 6-s pre-roll version ran for about 1.5 h before it was replaced
  (`:333-334`).
- **Stored per cell** (`~/ndsp-presets/learn/knob-ceiling/cells/<part>/<amp>/`, `plan:120-122`):
  - every menu distance on both halves;
  - every evaluation;
  - the incumbent curves;
  - the best settings, and the best render as FLAC.

  The fresh menu renders are **not** kept as audio, only their distances
  (`knob_ceiling.py:444-447,505-512`).

**What it does not cover:**

| Gap | Where stated |
|---|---|
| Pedals: "Kept from the starting preset (not searched)"; the PR12 crunch start's two pedals can't be turned off | `:78-85,370` |
| Time effects: reverb, delay, tremolo, doubler and spring off "as in the menu" | `:79-80` |
| Room mics, pan, phase and amp selection kept; output levels not searched | `:78-82` |
| Tone King: Morgan only (`AMPS`) | `knob_ceiling.py:32` |
| Crunch is 5 bands, "descriptive only" | `:166,373` |
| High-gain: `IN_SCOPE = ("clean","crunch")` | `knob_ceiling.py:33` |
| Rebuilt or song-side DI: "a ceiling, not a product number" | `:371-372` |
| Judge v3: `flat` only | `:25-27` |
| Listening is not done yet: a 6-cell A/B page comes after the report and audit, and "the product session attaches it" | `:198-208,362` |
| The judge-exploitation check is optional and report-only | `:349-354` |

**Amendment 3, the carry-over finding** (`plan:309-347`):

- **Symptom:** on `cambridge-It_Was_My_Fault_For_Waiting-ElecGtr1` (PR12, clean, Atlantis Bound),
  the same preset scored 3.42 against 3.92 depending on the previous render. Half A is mostly hiss
  from 1.0 to 3.8 s, and "Without it the spread was 0.138".
- **Cause:** "Morgan's `reset` clears its delay and reverb tails but not some other internal
  state".
- **Fix:** `isolate`, which leaves at most 5e-5 on half A.
- **The sentence at issue** (`:345-347`): "**The earlier menu pipelines rendered without either
  fix**, in a fixed order after a warm-up. Their half-A scores on parts that start quietly may
  carry the same order effect. That is outside this plan; it is noted for an audit."

*Is an audit declared?* **No.**

- There is no audit plan in any branch. I searched docs, learn and research on all branches for
  "carry-over", "order effect" and "render order".
- The only other mention is on the unmerged branch `origin/product/match-morgan-isolate`
  (commit `9601d62`, 2026-10-14 06:31):
  - it sets `isolate=True` for Morgan in `scripts/match_preset.py`;
  - its ROADMAP diff says: "The shared renderer's default is unchanged; **the ML session audits
    its own pipelines**."
- On main, D-M13 is still parked: "coordinate with the ML session first"
  (`docs/ROADMAP.md:393-394`). The original defect, "Morgan reused-instance variation depends on
  history", is at `docs/ground-truth-audit-2026-10-03.md:406-412`.

*Exposed pipelines.* Every Morgan research menu pipeline on main renders with
`process_policy="reuse"`. None passes `isolate`; a grep of `learn/` and `research/` finds no use
of it. Each renders a template+R warm-up and then the menu in fixed dict order:

- `learn/phase2_set3.py:304`
- `learn/confirm_run.py:138`
- `learn/residual_eval.py:172`
- `learn/set3_gap_split.py:103`
- `learn/set5_test.py:142`
- `learn/v2_eval.py:97`
- `learn/songs_check.py:155-161`
- `learn/sound_desc.py:254-256`
- `research/render_preset_panel.py:150-163`, which warms up per part

**Past headline results that depend on half-A menu scores from those pipelines.** Most use both
directions: choose on A and score on B, then the reverse, as the protocol requires
(`docs/closeness-review-2026-10-10.md:121`). So half A enters both the choice and the measure.

| Result | Pipeline | How half A enters | Margin |
|---|---|---|---|
| Set-4 confirmation, −0.087 (`docs/set4-confirmation-results.md`) | `confirm_run` | both directions (`learn/confirm_run.py:203-228`) | |
| Clean baseline, ~12% (`docs/clean-baseline-results.md`) | | "averaged over both halves" (`docs/clean-baseline-plan.md:39`) | |
| Crunch baseline (`docs/crunch-baseline-plan.md:30-36`) | | both halves | |
| Songs check, −0.114 / 75% (`docs/songs-check-results.md`) | | both halves | |
| Residual-DI gate 1, C′ vs C (`docs/residual-di-results.md`) | | | **passed by 0.001** |
| Set-5 test (`docs/set5-test-plan.md:55-60`; ROADMAP `:290-291`) | | both directions | **passed by 0.003** |
| EG-VAE E0/E0b: oracle −0.131, C′ −0.099 (`ml/egvae-lite:docs/egvae-lite-plan.md:125-171,246-275`) | | stored measure renders | |
| Sound-desc stage 0/1 (`docs/sound-desc-plan.md:36-41`) | | 35 pinned parts' measure renders | |
| Generate-routing and its recheck (`docs/generate-routing-plan.md:23-27,45`) | `rescore` and songs-check distances | | |
| Fixed-level rescore, judge v2 and v3 results, 3 kHz lowpass, underdrive trim, gap split, DI network v2 | set 3 development | | lowpass **missed by 0.0009** |
| Set-3 dev diagnostic and held-out confirmation; K1 di-recovery (8.5%) | `phase2_set3`, `phase2` | the oracle and chooser pick on half A, scored on B (`learn/phase2_set3.py:1-12`; `docs/di-recovery-plan.md:249`) | |
| Kill tests, amp reach, song-only shortlist (house-4 0.61), DI-free distance, rerank, tone-encoder screens | `runs/kill` panels | K1's oracle is chosen on half A (`docs/kill-test-k3-plan.md:71-72`; `docs/amp-reach-plan.md:26-28`) | |

**Not exposed:** Tone King baseline renders. They used a fresh process per render with a 1-s
pre-roll (`docs/toneking-baseline-plan.md:42-45`; `learn/tk_baseline.py:219`).

**Size of the exposure:** only parts whose guitar is near-silent early in half A. Which parts
those are has not been counted anywhere.

**Implication for the plan.**

- Report A's step 1a and plan 3 (the continuous-headroom pilot with a planted-target control,
  about 18k renders), and Report B's continuous-oracle study, largely **duplicate knob ceiling**,
  which is running now. Its planted-target control has already been run and failed in its exact
  form.
- What knob ceiling leaves open: pedals, time effects, Tone King, a CMA-ES optimiser, judge v3,
  more crunch bands, and listening.
- The plan should wait for knob ceiling's report and audit, and extend it rather than re-run it.
- **Cheapest carry-over audit, zero renders:** compare knob ceiling's fresh `isolate` menu
  distances (`result.json["menu"]`) with the stored songs-check and rescore `measfix` distances
  for the same 25 parts × 3 amps. Knob ceiling uses the same DI construction
  (`knob_ceiling.py:354-364`) and the same crops.
- Any step that "reuses existing oracle renders" (report A step 1b, rung 1; the ranker labels) is
  conditional on that audit.

---

## 3. `ml/set6-di-labelling`

**Exists.** The branch is **fully merged into main**: `1f8dc61` is an ancestor of
`origin/main`. Everything is on main:

- `docs/set6-di-labelling-plan.md` (123 lines);
- `docs/validation-set6.md` (616 lines; amendment 2 at `:29-139`, caveats at `:587-616`);
- `learn/build_di_labelling.py`;
- `research/set6_di_role_calibration.py`;
- key hashes in `docs/set6-di-labelling-key.sha256` and
  `docs/set6-di-labelling-validation-key.sha256`.

**State.** Labelling is done and set 6 is re-declared. The branch is not active in git.

- **First round** (`docs/set6-di-labelling-plan.md:71-81`):
  - 74 questions: 68 same-take groups from 36 songs, plus 6 hidden checks (`:53-54`);
  - the user answered 8 letters and left the rest "none";
  - hidden checks 1 of 6 right, so "By the declared rule (at least 5 of 6), the labels are not
    usable";
  - the user reported "most groups seem to have no DI, and clean DIs are hard to tell. Crunch DIs
    are easy."
- **Validation round:** 14 development questions, 10 with a known DI (6 crunch, 4 high-gain) and
  4 decoys. It passed 10/10 with no decoy named (`docs/validation-set6.md:47-56`).
- **What counts:** 7 confident MedleyDB labels give 6 groups from 4 songs, which give
  **5 parts**:
  - 3 crunch in scope from 2 bands: Little Tybee, and Port St Willow ×2;
  - 2 high-gain, report-only;
  - Goodbye Bolero is clean, so it is excluded (`:58-82`).
- **For a stem test, only Little Tybee is in scope.** Port St Willow and Big Troubles are in
  MUSDB18-train (`:10-13`). 35 of the 73 songs are in MUSDB18-train (`:19`).
- **Caveat:** Port St Willow's reference is probably an electrical drive path, outside the
  validated range, and "**A sensitivity is required**" (`:592-610`).
- **Ledger:** `held_out_uses` is empty (`docs/validation-set6.json:8131`). "nobody may listen to
  it, until a confirmation is declared" (`docs/validation-set6.md:25-27`).

**Candidates.**

- 73 MedleyDB songs tested;
- 1,568 same-take pair tests (`docs/validation-set6.md:296-300`);
- 68 waveform-same-take groups in 36 songs. These were all shown to the user.
- 89 "envelope-only" pairs were left out (`docs/set6-di-labelling-plan.md:56-57`).
- Crunch counts are known only for labelled groups (3 in-scope parts, 2 bands).
- No automatic DI-role rule passed. The best driven rule finds 34/39 crunch DIs with 12% false
  accepts; clean is 13/95 (`docs/validation-set6.md:141-200`).

**Implication for the plan.**

- Report A §2.4 says "Label more MedleyDB DIs by ear, as set 6 did. 73 songs … only 5 parts are
  labelled". That is **already done**. Every waveform-same-take group was put to the user, who
  could only label 7 confidently. Clean labels are unusable without a clean validation round,
  and the user reported clean DIs are hard to tell by ear.
- Any further yield is small:
  - the 89 envelope-only pairs, if re-tested;
  - a clean-DI validation round, which is likely to fail.
- Set 6 adds about 2 crunch bands (1 for stems) to a pooled test, and needs a declared
  with/without-Port-St-Willow sensitivity.
- The roadmap's own reading (`docs/stem-test-power.md`) is that 8–12 new crunch bands need new
  recordings.

---

## 4. Rendering: the Swift server and the Python client

**Exists.**

- `scripts/au_render_server.swift` (513 lines);
- `match/renderer_au.py` (`AudioUnitRenderer`, 758 lines);
- `match/renderer_preset.py` (Tone King exact-preset playback);
- `research/render_preset_panel.py` (the menu definition and the `preset_edits` helper);
- `learn/render_job.py:37-46` (`daemon()`, the licence-daemon watch).

**How a job is specified.**

- **Wire format:** one JSON line per render (`au_render_server.swift:13-28`), with these fields:
  - `out` (WAV path);
  - `input` (DI WAV);
  - `amplitude`;
  - **`edits`:** `[{"module","key","value"}]` attribute edits to the plugin's XML state, or
    **`state`:** a whole state-blob path for record-state plugins (`:286-359`);
  - `selectAmp`;
  - `gateOff`;
  - `isolate`;
  - `realloc`;
  - `warmup`;
  - `settle`.
- Every command starts from the plugin's startup state (`:24-28,160`).
- **Python side:** `AudioUnitRenderer.render(di, settings)` takes a settings mapping
  `{"module/key": value}`, translated through the pack (`match/renderer_au.py:348-382`). Research
  code subclasses `_state_command` to send raw edits (`learn/phase2_set3.py:276-286`;
  `origin/ml/knob-ceiling:learn/knob_ceiling.py:376-387`).
- **Whole presets** are sent as edits of every writable parameter they store, with R (dry)
  applied (`research/render_preset_panel.py:68-94`).
- The WAV is read back and deleted (`match/renderer_au.py:274-302`).

**Arbitrary continuous parameters.** Yes for Morgan: any writable `module/key`, and knob ceiling
does exactly this. The Morgan pack declares 132 parameters: 31 rotation, 53 metered, 32 switch,
and others (`packs/morgan/manifest.json`).

**Tone King** (`packs/toneking/manifest.json:5-10`: AU `TKI2`; "maps 94 of 255 numeric preset
keys to 94 of the 96 published controls"):

- **Generic path:** supported through the record-state path. Python rewrites the binary `PARAM`
  blob per render (`match/renderer_au.py:384-403`). `isolate` is turned on automatically,
  because Tone King renders exact zeros until its resources are cycled (`:102-113,240-272`).
- **Exact-preset path:** `ToneKingPresetRenderer` "deliberately accepts no per-render knob
  edits" (`match/renderer_preset.py:1-7`).

**Throughput.**

- **Single process:** 291 ms per render at steady state for a 2-s render (one process), against
  2,030 ms for one process per render. Four servers in parallel reach 8.8 renders/s
  (`docs/measuring-against-the-plugin.md:337-342`).
- **Realised rates:**

  | Run | Renders | Processes | Time | Source |
  |---|---|---|---|---|
  | Crossed renders | 16,800 | 3 | 8,063 s (about 7.5k/h) | `docs/tone-encoder-plan.md:151-152` |
  | Knob ceiling (plan) | about 70k | 6 | 6–9 h, 1.5 s per render including scoring | knob plan `:116-118` |
  | Tone King, fresh process | 6,930 | 6 | about 1.6 h, about 5 s each | `docs/toneking-baseline-plan.md:114-120` |

  The brief's figure is 30k ten-second renders in 3–4 h on 6 processes
  (`research_notes/Song to preset ML approaches/_brief.md:73-75`).

**`isolate`** (`au_render_server.swift:362-385`): deallocate render resources, write the state,
reallocate, then `reset`.

- Off by default for Morgan; `None` means auto, which only Tone King triggers
  (`match/renderer_au.py:102-113`).
- Knob ceiling measured that it removes the carry-over at no cost, fading in over 0.25 s
  (knob plan `:323-336`).
- The older doc says isolate does not make reused renders bit-identical (about −17 dB broadband
  difference, at most 0.23 dB per third-octave band;
  `docs/measuring-against-the-plugin.md:351-388`). That is a different property from the 2–3 s
  tail.

**Process reuse.**

- `process_policy="reuse"` (the default) or `"fresh"` (`match/renderer_au.py:130-160`).
- Morgan fresh-process renders are bit-exact; reused ones are not
  (`docs/measuring-against-the-plugin.md:351-360`).
- Tone King is not reproducible even fresh (`:353-355`), but its judge distance repeats within
  1e-6 (`docs/toneking-baseline-results.md:31-32`).

**Licence-daemon rule.**

- "The daemon itself is never touched" (`learn/render_job.py:10-12`;
  `learn/render_crossed.py:18-19`).
- "Reused render processes cost about 0 licence-daemon ports. About 10 per new process. Watch the
  daemon with `learn.render_job.daemon()`" (`learn/README.md:164-165`).
- "licence daemon port count too high; reboot first" (`learn/render_pairs.py:180-181`).
- "that many restarts wear out the plugin's licence service"
  (`docs/listening-validation-plan.md:20-21`).
- Brief: "renders are shared with another session and must be scheduled. Never kill or modify
  the licence daemon. A plan needing more than about 200k renders should say why." (`_brief.md:91-92`)
- Knob ceiling does not call `daemon()`.

**Menu counts.**

- `P.menus` (`learn/phase2_set3.py:233-241`) reads the installed factory folder
  `/Library/Audio/Presets/Neural DSP/Morgan Amps Suite`, never `User/`
  (`research/render_preset_panel.py:40,97-116`).
- It keeps factory presets plus `template+R`, and drops the shipped `template`.
- **111 = 108 factory + 3 templates:** 45 SW50R, 35 PR12, 31 AC20
  (`docs/set3-development-diagnostic-results.md:21`).
- The factory split is 44 / 34 / 30 (`docs/song-only-shortlist-plan.md:20-22`).
- 53 of the 108 are high-gain (`docs/amp-reach-plan.md:98`).
- Dry rule R (`research/render_preset_panel.py:52-54`): reverb, delay, tremolo, doubler, gate and
  spring off; FX section on; transpose 0.

**Tone King menu exists.**

- 125 complete Factory/Artists presets plus `Default.xml` = 126. Three incomplete presets are
  excluded.
- Dry copies are made by `learn/tk_baseline.py dry` (`docs/toneking-baseline-plan.md:17-33`;
  `learn/tk_baseline.py:34-48`).
- Rendered on 35 pinned development parts (4,410 renders) and 20 held-out parts.
- Renders were to be "kept as FLAC until the results are reviewed, then deleted, keeping only the
  distances" (`docs/toneking-baseline-plan.md:122-123`).

**Implication for the plan.**

- Report A plan 1 says "Tone King has no menu yet. Build a dry Tone King factory menu". **That is
  wrong.** It exists, with development distances.
- Tone King at scale is about 2× slower per render, wears the licence service if run fresh, and
  has never been run reused at scale in research. Report B's "half Morgan, half Tone King" 60k
  bank needs a reuse+isolate repeatability check for Tone King first.
- Every new Morgan render should pass `isolate=True` (amendment 3).
- Renders must be scheduled around knob ceiling, which uses 6 processes for 6–9 h or more today.

---

## 5. The judge

**Exists.** `analysis/aligned.py`, `aligned_distance`. Signature and options are at `:331-361`.

**Options.**

- `bands`: `"recording"` (the default), `"union"`, or `"fixed"` (v2).
- `weighting`: `"flat"` (the default) or `"hearing"`.
- `floor`: `"recording"` (the default) or `"symmetric"` (v3).
- `JUDGE_V3 = {"bands": "fixed", "floor": "symmetric"}` (`:71-73`).
- Research wrapper (`learn/rescore.py:39-41`):

  ```
  JUDGE_OPTIONS = {"flat": {}, "hearing": {...}, "fixed": {...}, "v3": JUDGE_V3}
  ```

- Output: distance, plus `tonal` and `temporal` parts (`:76-86`).

**Average-guitar measure DI ("measfix")** (`learn/confirm_run.py:81-94`):

- the true DI, re-equalised by `eq_to(di, avg − (own − own.mean()))`;
- the target is `~/ndsp-presets/learn/direc/cache/average-fold2.npy` (`:41`), K3 fold 2's frozen
  average. It "lives in" the PR12 cache, which must not be deleted (`learn/README.md:141-143`);
- then `to_lufs` at −22.9 (`learn/direc_check.py:38`).
- The user's decision to use a fixed −22.9 LUFS: `docs/closeness-review-2026-10-10.md:136-138`.
- Knob ceiling re-implements it without torch (`knob_ceiling.py:354-364`).

**Halves.** `HALF_A, HALF_B = (1.0, 5.5), (5.5, 10.0)` seconds of the 10-s crop
(`learn/phase2_set3.py:43`; `learn/rescore.py:45`).

- Protocol: "Score on both halves (choose on A and score on B, and the reverse), and average"
  (`docs/closeness-review-2026-10-10.md:121`).
- Statistic: `confirm_run.cells` and `stats`, giving band-clustered t and leave-one-band-out
  (`learn/confirm_run.py:203-240`).

**Refusals.** The distance is `None` with a reason (`analysis/aligned.py:386-476`):

- DI silent;
- under 1 s aligned;
- no loudness;
- the DI plays in too few frames;
- more than 50% of scored frames are pauses;
- v3 only: the recording is inaudible where the DI plays;
- hearing weighting only: too few bands.

Known case: telefunken-Honey-GTR's half B is refused for every preset (`docs/songs-check-results.md:47-48`).

- **Rebuilt-DI fallback:** `learn/rebuilt_judge.py:1-8`. When the rebuilt DI looks too quiet, the
  recording is used as the activity mask; lag −52.
- **The 3 kHz lowpass is retired:** `learn/rebuilt_judge.py:15-20`. Note that
  `learn/songs_check.py:116` still applies it, because the songs check predates the retirement.

**Current judge for decisions.**

- `flat`, the default (`docs/measuring-closeness.md:13-21`), on measfix, cross-half. Example:
  "Scored with the `flat` judge" (`docs/set5-test-plan.md:47-48`).
- v3 is reported beside it. "Adoption waits for the user's listening calibration"
  (`docs/judge-v3-results.md:5-6`).
- v3 scores exist only for set-3 development, 198 cells (`:50-54`).
- Heavy listening's rule: "The judge's sum stays, and aggregate differences under 0.10 count as
  ties" (`docs/heavy-listening-results.md:27-28`).

**Implication for the plan.**

- Report A's "optimise on v1 + v3" needs v3 rescoring of everything outside set 3. That is
  zero-render: `learn.rescore score --judges v3`, and the same for the songs-check distances.
- v3 is not adopted, so any v3-based gate is a new declaration.

---

## 6. Render caches and panels: format and location

All of these are on the Mac, under `~/ndsp-presets/`. None could be verified here.

| What | Content | Format | Location |
|---|---|---|---|
| **Kill panels** | Every factory preset with R, plus template+R and the shipped template, through the **43 set-2 development parts' own DIs**: raw session level, crop rule 1, *not* measfix. Reused process, warm-up per part | **float WAV**, 10 s | `~/ndsp-presets/runs/kill/{pr12,sw50r,ac20,pr12-clean}/<slug>/<sha12>.wav` plus `index.json` (`research/render_preset_panel.py:1-21,49,150-163,200`; `docs/tone-encoder-plan.md:33-36`). The K3 folds read `runs/kill/pr12-clean/index.json` (`learn/train.py:37`) |
| Amp-reach distances | Old-measure judge distances: 108 factory + template, 25 K1 parts, half A, half B, full window, both band sets | JSON | `~/ndsp-presets/runs/kill/amp-reach.json` (`research/reach_sets.py:1-14`; `docs/song-only-shortlist-plan.md:20-22`) |
| **16,800 crossed renders** | 300 blocks: 8 **sampled settings** (not menu presets) × 7 DI windows from set 2's 13 development bands plus Guitar-TECHS P1; half pre-EQ'd. 6 s, peak-normalised with gain recorded | 16-bit FLAC, 3.5 GB, plus a 3.5 GB mel cache | `~/ndsp-presets/learn/tone-encoder/renders` (`learn/render_crossed.py:1-22`; `docs/tone-encoder-plan.md:17-30,151-153`) |
| **36k translator renders** | 323 measfix DI windows from 27 bands × 111 presets | **D130 descriptor arrays only** (`.npz`); audio kept for 5% (every 20th window). The kept files are named with Python's salted `hash(n)`, so mapping them back to presets is probably not possible | `~/ndsp-presets/learn/sound-desc/renders/<id>.npz` and `renders/audio/<id>/<amp>-<hash>.flac` (`learn/sound_desc.py:224-270`; `docs/sound-desc-results.md:30-33`) |
| **True DI (measfix) × menu** | 111 presets | 24-bit FLAC (peak-normalised; the judge ignores level) plus `di.npy` | sets 1–2 development (songs-check parts): `~/ndsp-presets/learn/direc/songs-check/measfix/<slug>/<amp>/<sha12>.flac`; set-3 development: `~/ndsp-presets/learn/direc/gap-split/measfix/...` (`learn/songs_check.py:25-34,97-100,119-163`; `learn/set3_gap_split.py:31-32`) |
| Distances for those | 52 parts in 29 songs (clean 22, crunch 13, high-gain 17); 35 pinned clean+crunch parts in 15 bands | JSON | `learn/direc/rescore/distances.json` and `songs-check/distances.json` (`docs/generate-routing-plan.md:23-27`; `docs/sound-desc-plan.md:36-41`) |
| **C′ rebuilt DI × menu** | 18 pinned development parts, 8 bands; kinds `Cp` (C′ seed 0), `Cp1`, `C`, `R`, `L`. From amp tracks, uncut | 24-bit FLAC plus `di.npy` (the C′ rebuilt DIs) | `~/ndsp-presets/learn/direc/residual/<kind>/<slug>/<amp>/` (`learn/residual_eval.py:28-55,155-176`) |
| Set-5 renders | Held out, spent once | | `learn/direc/set5-test/` (`learn/set5_test.py:26-27`) |
| Stems (songs-check) | htdemucs_6s stems, `instrumental_guitar.wav` | WAV | `~/ndsp-presets/learn/poc/stems/htdemucs_6s/` (sets 1–2) and `learn/set3/stems/htdemucs_6s/`, with manifests (`learn/songs_check.py:28-31,83-93`) |
| Songs-check stem-kind renders | Old fold networks plus 3 kHz cut | | `songs-check/stem/` |
| Other renders on disk | POC PR12 renders, 18,843 | FLAC | `learn/poc/renders` |
| | C′ training pairs, SW50R and AC20 | FLAC; caches of about 35 GB are rebuilt when needed (`docs/residual-di-plan.md:92-93`) | `learn/direc/pairs-{sw50r,ac20}` |
| | Phase-2 renders | | `learn/direc/phase2/`, `phase2-set3/` (`learn/README.md:87-106`) |

**Deleted, per the docs:**

- the set-4 confirmation's rebuilt-DI renders (`docs/audit-2026-10-11.md:70`);
- the DI-robustness renders, 19 GB (`docs/di-robustness-results.md:64`);
- the E0 and E0b renders (`ml/egvae-lite:docs/egvae-lite-plan.md:170-171,274-275`);
- Tone King baseline renders, slated for deletion (`docs/toneking-baseline-plan.md:122-123`).

**Implication for the plan.**

- **These steps are genuinely zero-render:**
  - Recall@k for Morgan starts and house/random-k on about 52 parts, from the stored distances;
  - C′ picks and drive bias on **18 parts only**;
  - R0 on the crossed renders;
  - R1 on the kill panels;
  - R3 and R4 on the stored measfix renders and the stems.
- **These are not:**
  - **Report A step 0a** ("crops within parts"): there is one 10-s crop per part, so within-part
    replication is halves A/B only. More crops need new crops and renders.
  - **The 36k translator set cannot be reused as audio.**
  - **The kill panels are at the session's own DI level and use the older crop rule**, so they
    don't match the current measure.
  - **"~136 development parts' true-DI × menu oracle rankings"** (report A plan 1): only about 52
    have measfix menu renders. About 65 classed clean+crunch parts exist (item 7); the rest need
    about 30 × 111 ≈ 3.3k renders.
- **Every reuse is conditional on the item-2 audit.**

---

## 7. Data splits

**`learn/songs_check.parts()`** (`learn/songs_check.py:74-94`):

- set-3 development parts with a usable stem, plus sets 1–2 development parts with a usable stem;
- gain classes for sets 1–2 come from the local `~/ndsp-presets/learn/direc/songs-check/prep-sets12.json`,
  where 8 of 20 are low confidence (`docs/generate-routing-plan.md:28-30`);
- clean+crunch: **25 parts, 15 bands, 20 clean / 5 crunch** (knob plan `:19-21`).

**`k3_folds`** (`learn/train.py:42-56`):

- bands come from the **local** kill-panel index `runs/kill/pr12-clean/index.json`, i.e. set 2's
  development bands only;
- shuffled with `FOLD_SEED = 20261003` and assigned `i % 4`;
- set-3 bands are fold −1.
- **C′ exists only for fold 2** (K3 fold 2 left out of training). So C′ can be evaluated without
  leakage only on the **18 pinned parts in 8 bands** whose bands no fold-2 network saw
  (`learn/residual_eval.py:38-55`).

**Development inventory** (`docs/part-locator-truth.json`): 136 DI parts, 45 songs, 28 bands.

| | Parts | Bands |
|---|---|---|
| Clean | 48 | 16 |
| Crunch | 17 | 8 |
| High-gain | 17 | 8 |
| Unclassed (no passing same-take pair, no class, or excluded) | 54 | |

- **Pinned clean+crunch set with measfix renders** (`docs/sound-desc-test-parts.json`): 35 parts,
  15 bands; clean 22 in 10 bands, crunch 13 in 6 bands.
- **Crunch parts not pinned:** Ale Lak and Zeno ElecGtr3 (2 new crunch bands), plus 2 more parts
  in pinned bands.
- Usable judge pairs: sets 1–2 development 57 parts (`docs/validation-datasets.json`, flag
  `usable`); set 3 development 33.

**The over-used "33".** These are set 3's development parts: 33 parts in 11 bands; 5 clean
(3 bands), 11 crunch (5 bands), 17 high-gain (8 bands) (`docs/validation-set3.json`;
`docs/di-recovery-set3-results.md:16`). About 15 decision comparisons were run on them
(`docs/closeness-review-2026-10-10.md:107-109`).

- **11 of the 13 pinned crunch parts are in the 33.**

**Guitar-TECHS.**

- P3_music excerpts form validation set 1: development 01, 03, 04, 05, 07, 08, 09, 12; held out
  02, 06, 10, 11 (`docs/validation-datasets.md:41,173`).
- P1 DIs are in the training DI pool (`learn/di_pool.py:4,36-39`; `learn/render_pairs.py:7`;
  `learn/set3.py:34`).
- P1 riffs ship in `samples/riffs/` (`docs/ROADMAP.md:486`).

**Held-out ledgers.**

| Ledger | Contents |
|---|---|
| `docs/validation-datasets.json:5240` (`held_out_uses`, sets 1–2) | 5 uses: `heldout-sw50r-di-vs-no-di`, `confirm-rebuilt-di-chooser-2026-10-10`, `crunch-baseline-2026-10-10`, `clean-baseline-2026-10-10`, `toneking-baseline-2026-10-11` (the "third declared use", `:5363`) |
| `docs/set3-heldout-use-ledger.json` | Set 3: "spent; excluded from further tuning, training, or confirmation" |
| `docs/validation-set4.json:2549` | The first five sessions are spent: Tholas P., Last Legacy, Decypher, The Black Crown, Lead Inc; 13 parts. **Unused:** the 4 Internet Archive sessions, 22 parts |
| `docs/validation-set5.json:3523` | `set5-cprime-test-2026-10-12`, first use; 26 of 31 parts in scope: 16 clean in 3 bands, 10 crunch in about 4 bands with BKS+Fytakyte merged |
| `docs/validation-set6.json:8131` | Empty |

Unused set-4 parts by band and class:

| Band | Crunch | Clean | High-gain |
|---|---|---|---|
| Umbriferous | 6 | | 4 |
| The Bright Star Alliance | 1 | | 6 |
| Sonnet & Alcohol | | 2 | |
| The Laminar Flow | 1 | | 2 |

That is **10 in-scope parts in 4 bands**: 2 clean in 1 band, and 8 crunch in 3 bands. These counts
are from `docs/validation-set4.json` `counts`.

**Held-out rule** (`docs/validation-datasets.md:185-191`): "**Held-out** material is used only by
a test declared in a committed file before it runs — its command, what it measures and what each
result would mean — … each such use is added to `held_out_uses` … A held-out session used for
anything else moves to development."

**Implication for the plan.**

- Report A §2.4 says "the count in scope is unknown" for set 4. It is **10 parts in 4 bands**.
- **Pooled in-scope bands, if there is no overlap:** set 5 has 5, set 4 has 4, set 6 has 2,
  giving **about 11**. About 9 of them have crunch.
- Avoiding "the 33" leaves almost no crunch: only 2 sets 1–2 crunch parts are pinned.
- Development crunch can grow to 8 bands only with new measfix renders: about 4 parts × 111.
- Any use of C′ on development is limited to 18 parts, unless C′ is retrained for other folds.

---

## 8. Separator

**Exists.**

- **No separation script is committed in `learn/`, `research/` or `scripts/`.** Stems were made
  locally:
  - htdemucs_6s, `shifts=0`, on a 30-s context of the session's instrumental mix
    (`docs/preset-model-poc-plan.md:102-105`; `docs/songs-check-results.md:53-56`);
  - outputs and manifests in `~/ndsp-presets/learn/poc/stems/` and `learn/set3/stems/`.
- Separator-upgrade scripts: `~/ndsp-presets/learn/sep2/_work/scripts/` (local), venv
  `tools/sep2-venv`, CPU only (`docs/separator-upgrade-plan.md:5-6`).
- `generate` does not run a separator. The part locator would ship one only "with the user's OK
  for the PyTorch and separator download" (`docs/part-locator-plan.md:25-26`).

**Timings** (`docs/separator-upgrade-results.md:55-65`; CPU, 4 threads, per 30-s context, on a
shared machine):

| Separator | CPU s | Wall s |
|---|---|---|
| htdemucs_6s | 39 | 15 |
| Mega-53, guitar heads only | 315 | 102 |
| X-LANCE | 193 | 87 |

There is no MPS timing.

**Separator-upgrade result.** No candidate replaces htdemucs_6s.

- Mega-53 and X-LANCE gain about 1 dB median SNR, against a 2 dB bar (`:7-18`).
- htdemucs medians: 1.11 dB (sets 1–2) and 0.63 dB (set 3). Usable: 14 of 28 and 12 of 33.
- Gains are almost all on single-guitar parts.
- Part-locator caveat: "`htdemucs_6s`'s guitar stem doesn't separate acoustic from electric
  guitar" (`docs/part-locator-results.md:62-63`).

**Implication for the plan.**

- Report A step 0e ("measure separator speed") is **half done**. The CPU figure exists: about 15 s
  wall per 30-s context, so roughly 5 s per 10-s clip if it scales linearly. That is an estimate,
  not a measurement.
- Only MPS is unmeasured.
- For about 21k separator passes: roughly 29 h on CPU at 10-s clips, or about 88 h with a 30-s
  context per clip (estimate).
- The separator script has to be written or recovered from the Mac.

---

## 9. The C′ network

**Exists.**

- **Code:** `learn/direc.py`: `build_model` `:137`, `load_model` `:285`, `fit` `:358`,
  `rebuild(net, x, device, window=6 s, hop=5 s)` `:541`.
- **Weights:**
  - `~/ndsp-presets/learn/direc/models-cprime/fold2.pt` (seed 0);
  - `models-cprime-s1/fold2.pt` (seed 1);
  - `models-cprime-s2/fold2.pt` (seed 2, used on set 5 only)

  (`learn/residual_eval.py:30-33`; `docs/set5-test-plan.md:40-42`).

**Inference.** `D.load_model(path).eval()`, then
`to_lufs(D.rebuild(net, rec.astype(np.float32), device=torch.device("cpu")))`.

- Examples: `learn/songs_check.py:113-116` (applies the retired lowpass); `learn/residual_eval.py`
  `rebuild`.
- Environment: `~/ndsp-presets/tools/learn-venv` (Python 3.9, torch 2.8, CPU inference and
  scoring). Training used `tools/demucs-venv` (torch 2.14, MPS): "Run it read-only"
  (`learn/README.md:146-153`).
- The judge for rebuilt DIs is `rebuilt_distance` at lag −52.

**Training data** (`docs/residual-di-plan.md:36-40,165-171`):

- C's recipe with the gradient fix: the PR12 `cache` plus the SW50R and AC20 pair caches, K3 fold
  2 left out;
- 100·L1 + MR-STFT magnitude loss;
- 5,150 steps at 3e-4, then 23,100 with cosine decay to 2e-5; seed 0.
- **48,806 clips:** PR12 18,843, SW50R 14,965, AC20 14,998
  (`ml/egvae-lite:docs/egvae-lite-plan.md:285`).
- **DIs:** set 2's development bands plus Guitar-TECHS P1, with a random pre-amp EQ
  (`learn/render_pairs.py:1-15`).
- **Settings:** factory bases with R, knobs redrawn, drive pushed.
- **Augmentation:** bleed from training-fold `backing_instrumental.wav` at −12 to −30 dB, and
  noise (`learn/direc.py:394-424`).

**MPS bug.** "torch.stft's gradient on MPS is wrong for signals longer than 65,536 samples (81–100%
off), and its forward is right. Training crops are 144,000 samples."
(`docs/residual-di-plan.md:189-191`)

- `mrstft` computes on the CPU when given MPS tensors (`learn/direc.py:336-346`).
- `complex_stft_loss` is routed to the CPU because it is wrong even in the forward pass
  (`:245-251`).
- Test: `tests/test_direc_mps_gradient.py`.
- Also: `clip_grad_norm_` gives NaN on MPS, so clipping is done by hand (`:472`).
- "Never run two MPS training processes at once" (`learn/README.md:158-159`).

**Implication for the plan.**

- Stacking C′'s 111 scores into a ranker, or running drive-bias checks, works leak-free only on
  the 18 parts. Wider use needs C′ trained for the other folds: about 6 h on MPS per fold, by the
  R/C′ budgets in `docs/residual-di-plan.md:94-96`.
- C′ has never been run on separated stems.
- The rebuilt DIs (`di.npy`) for the 18 parts exist, which ladder rungs 6–7 need.

---

## 10. Listening tooling

**Exists.**

- **`docs/declared-listening-runner.md`, `research/run_declared_listening.py`,
  `research/summarize_declared_listening.py`:** a frozen runner for held-out SW50R
  match-vs-no-match tests. "that summarizer currently implements only the frozen SW50R test"
  (`docs/declared-listening-runner.md:101-104`). It is not what recent tests used.
- **Recent builders**, all phone pages, which together cover the protocol's elements (hidden
  references, repeats with A/B swapped, a "?" option, a private key):
  - `learn/build_avg_listening.py`;
  - `learn/build_heavy_listening.py` (reuses the former's helpers: `:18-22`);
  - `research/starting_preset_listening.py` (parts, build, phone, score: `:1-12`);
  - `research/listening_check.py`;
  - `learn/build_di_labelling.py`;
  - `scripts/_listening_trials.py` (repeats and catches);
  - `analysis/listening.py`.
- **Product page:** `scripts/audition.py` (four presets through the CC BY riffs or a DI).

**How trials are recorded.**

- Key: `private/trials.json`, with its SHA-256 committed before the sitting.
- Answer sheet: plain text, e.g. `docs/starting-preset-listening-answers.txt`, with its SHA-256
  committed before the key is read.
- "the scorer refuses any other key"; "records the answer sheet's sha256 before it reads the key"
  (`learn/build_heavy_listening.py:18-22`; `docs/starting-preset-listening-plan.md:63-68`).
- Results go to `docs/*-results.json` / `*-score.json`.
- Knob ceiling's page goes to `~/ndsp-presets/listening/knob-ceiling/`, and "the product session
  attaches it" (knob plan `:207-208`).

**Implication for the plan.** Report A step 4 (v3 calibration about 55 trials, MAD pairs, pairwise
shortlist) can reuse `build_heavy_listening` and `starting_preset_listening`. The v3 calibration
is explicitly not built: "should include pairs from the cells where their picks differ …"
(`docs/judge-v3-results.md:107-111`).

---

## 11. Rules

**Plans.** "`<topic>-plan.md` is written and committed before anything is computed; … Changes to a
plan after it is declared are added as dated amendments, never silent edits."
(`docs/README.md:9-13`)

**Review and audit.**

- Knob ceiling's order: "1. This plan, then an independent review. … 2. The control result,
  reviewed. 3. Message the product session, then the main run … 4. The report, an independent
  audit of it, then the listening page." (`origin/ml/knob-ceiling:docs/knob-ceiling-plan.md:356-362`)
- "have an independent reviewer rederive the final result before acting on it"
  (`learn/README.md:128-129`).

**Analysis protocol** (`docs/closeness-review-2026-10-10.md:112-124`):

- "the band is the unit, with amps pooled within it";
- "three outcomes, declared in advance: helps, futile or inconclusive";
- "power is checked before running, using the true-DI oracle";
- "one ledger of tests on the development parts". **No such development ledger exists in the
  repository.**
- "Score on both halves"; "Compare against leave-band-out constants"; "Report the tonal and
  temporal parts"; "Add a drive-bias diagnostic".
- Band-weighted results are reported beside part-weighted ones (`docs/audit-2026-10-11.md:73-76`).

**Held out.**

- `docs/validation-datasets.md:185-191`, quoted in item 7.
- Sets 5 and 6: "Nothing may train, tune or choose on it, and nobody may listen to it, until a
  confirmation is declared in a committed file." (`docs/validation-set6.md:24-27`)
- EG-VAE's set-5 rule: "That test is declared, with its ledger entry recorded as set 5's second
  use, before any render." (`ml/egvae-lite:docs/egvae-lite-plan.md:237-239`)

**Product session and ML session.**

- "The product session asked for it and the ML session agreed" (`docs/part-locator-plan.md:3-4`).
- "For the product session: a `dry/toneking` recipe and `generate` step 4" (`docs/ROADMAP.md:261`).
- D-M1: "that is the ML session's"; D-M13: "coordinate with the ML session first"
  (`docs/ROADMAP.md:391-394`).
- The product branch says the ML session audits its own pipelines (item 2).

**Scheduling.**

- "renders are shared with another session and must be scheduled" (`_brief.md:91`).
- "at most two reused processes; the ML session is told first and nothing runs 03:00–04:15"
  (`docs/generate-routing-plan.md:161-163`).
- "Launch long jobs with `zsh -c 'setopt no_bg_nice; nohup … &'`" (`learn/README.md:156-157`).

**Disk.** See item 14.

**Licences.** "Open source only: no cloud APIs, commercial tools, or unlicensed or gated weights"
(`docs/ROADMAP.md:491`).

**Implication for the plan.** Each programme step needs, in order:

1. its own committed plan;
2. a review;
3. a message to the product session before renders;
4. after results, an audit.

The pooled held-out test must be entered in four ledgers (sets 1–2, 4, 5, 6). The programme
should also create the missing development-test ledger.

---

## 12. The part locator

**Exists.**

- `docs/part-locator-plan.md` (declared 2026-10-13 at the product session's request);
- `docs/part-locator-results.md`;
- `docs/part-locator-truth.json`;
- `learn/locator_truth.py`, `learn/locator_pyin.py`.
- On main via PRs #184 and #185.

**State.** Step 1 only, "underpowered". There are "**7 targets in 6 bands**" against a declared
floor of 15 targets in 10 bands. The pYIN role rule can't separate chords: only 2 of 136 parts were
labelled rhythm. "Separation isn't run for a measure that can't reach its bar"
(`docs/part-locator-results.md:9-21,44-52`).

The Eden caveat, by ear: the window the map ranked best, 8:10, is an acoustic guitar. "htdemucs_6s's
guitar stem doesn't separate acoustic from electric guitar … Any such helper has to say so, and
leave the choice to the user's ears." (`:55-64`)

**Implication for the plan.**

- The truth file is the best inventory of development parts: 136 parts with class and character
  labels.
- The locator itself is untested. The ranker's song input still needs the user's time window.
- Separator-in-the-loop training should expect acoustic/electric confusion in the stem.

---

## 13. Existing implementations of the plan's components

| Component | Exists? | Where and state |
|---|---|---|
| Direct preset ranker / ridge baseline | **Proposal only** | `docs/research/direct-preset-ranker-proposal-2026-10-09.md`: "Not a declaration" (`:4`); 8 octave-band relative powers of the half-A stem (`:61`) into "eight-input, 45-output ridge regression", λ = 1 (`:71`), SW50R menu, set-3 development. No code. A different ridge (the D130 description to T(p)) is in `learn/sound_desc_eval.py:42-99` |
| Recall@k / shortlist share | **Yes, for the old measure** | `research/score_shortlists.py:43` (`CLEAR = 0.150`) and `:188-196` (`within_share`, band-weighted share within 0.150 of the oracle). Results: house-4 0.61/0.46, random-4 0.42, template+R 0.29 (`docs/song-only-shortlist-results.md:91-104`). These are on 25 K1 parts from the kill-panel distances (raw DI, rule-1 crops), not measfix and not today's starts |
| Drive-bias analysis | **Numbers only** | Old C on set 3: gain knob below the oracle's on 43 vs 14 (`docs/closeness-review-2026-10-10.md:80-81`). Bias table (`docs/underdrive-trim-results.md:24-37`): uncut −0.094, 3 kHz cut −0.056. The analysis code is not in `learn/`; the gain-knob map is `learn/render_pairs.py:38`. **No C′ drive bias has been reported** |
| Mixing renders into backings | **Partial** | Bleed augmentation only, guitar-dominant: −12 to −30 dB backing (`learn/direc.py:394-424`; `learn/train.py:109-118`); in the mel domain for the tone encoder (`docs/tone-encoder-plan.md:58-62`). No mastering or compression, no separator in the loop. `research/build_backed_audition.py` mixes for listening only. Backings: each crop's `backing_instrumental.wav` |
| dasp-pytorch | No | Only cited in research round 3 |
| AFx-Rep | No | `docs/ROADMAP.md:366-367`: "about 1.2 GB; verify open licence before use". Not downloaded |
| Basic Pitch | No | pYIN (librosa) is used in the locator (`learn/locator_pyin.py`) |
| DAC | **Yes, on `ml/egvae-lite`** | `learn/egvae_e0_dac.py`, `egvae_e1_dac.py`, `egvae_e1_codec.py` (descript-audio-codec 1.0.0, 44 kHz, a separate `$DAC_PY` venv). E0 (9 codebooks) and E0b (4 codebooks) **already ran ladder rung 2** on the 18 parts: −0.129 and −0.126 against the oracle's −0.131 (`ml/egvae-lite:docs/egvae-lite-plan.md:125-171,246-275`). Renders deleted |
| CMA-ES | Yes, in the product | `match/search.py:934-942`: a numpy (μ/μ_w, λ)-CMA-ES in `match_preset.py`'s DI-path search, with a loss-profile objective, not the judge |
| PANNs CNN14 / log-mel rerankers | Yes, failed | `learn/rerank.py`, `learn/tone_encoder.py` |
| Time-effect estimators | **Partial, in the product** | `match/invert.py`: `delay_settings` `:854`, `reverb_settings` `:921`, `reverb_from_rt60` `:952` (RT60 only in the `probe` regime, `:64-71`), `tremolo_settings` `:1037` (no tremolo from recordings, D-M7). `research/study_rt60.py`. Report A's "Never run" is too strong |

**Implication for the plan.**

- **Step 0b** has a template in `score_shortlists.within_share`, but needs re-running on measfix
  distances with today's starts.
- **Step 0c** needs new code, which is small.
- **Plan 2's DAC rungs at 4 and 9 codebooks are done.** The ladder should add only 1, 2 and 8.
- The ridge baseline is still "never run", as report A says.

---

## 14. Disk

- Brief: "disk (about 65 GB free)" (`research_notes/Song to preset ML approaches/_brief.md:421`).
- Practice: keep 30 GB free. "To keep 30 GB free, all nine set-4 zips were deleted"
  (`docs/validation-set4-plan.md:329-331`); "disk stays above 30 GB free"
  (`docs/residual-di-plan.md:92-93`). So about 35 GB is usable.
- Policy (`learn/README.md:134-144`):
  - "Phase 2 renders are stored as level-normalised 24-bit FLAC, about 4× smaller";
  - training caches are "deleted after training, then rebuilt from the FLAC pairs"; "The PR12
    cache stays: the fold averages live in it."
- The data grew about 180 GB on 10-06/07 (`:136-137`).
- Practice of deleting renders after scoring: E0/E0b, DI robustness, Tone King.
- The C′ pair caches take about 35 GB when rebuilt (`docs/residual-di-plan.md:92`).
- Knob ceiling keeps best-render FLACs plus JSON per cell.

**Implication for the plan.** Report A's "~38 GB of the 65 GB free" ignores the 30 GB floor. In
practice, a 40k-render WAV ladder doesn't fit. The FLAC or feature-only rule is needed from the
start, and rebuilding the C′ caches would take most of the headroom.

---

## Things the plan must not duplicate

1. **The continuous-knob headroom pilot with a planted-target control.** That is knob ceiling,
   about 70k renders, now running. The exact control already failed and the result is read as a
   lower bound. Extend it (pedals, time effects, Tone King, CMA-ES, v3, crunch) only after its
   report and audit.
2. **A dry Tone King menu.** It exists: 126 presets (`learn/tk_baseline.py`).
3. **MedleyDB DI labelling by ear.** Done for all 68 waveform-same-take groups; set 6 holds 5 parts.
4. **DAC round-trip ladder rungs at 9 and 4 codebooks.** Done as E0 and E0b on the 18 parts.
5. **Exact DAC-code prediction (E1).** Closed.
6. **htdemucs_6s CPU timing and the separator upgrade.** Measured; no upgrade passes.
7. **The shortlist reach metric.** Exists (`within_share`). Re-run it; don't rebuild it.
8. **The under-drive measurement on old C.** Done. Only C′ is new.
9. **Rebuilding the true-DI × menu labels** for the 52 parts that have stored measfix renders.
   Re-score them after the carry-over audit, unless the audit says re-render.
10. **v3 scoring code.** It exists (`learn.rescore --judges v3`); only the scoring of non-set-3
    parts is missing.
11. **A CMA-ES implementation.** One exists in `match/search.py`.

## Blockers and risks discovered

1. **Render-order carry-over in every Morgan menu pipeline on main.** All are reused, without
   `isolate`, in a fixed order after a warm-up. No audit is declared; it is only "noted for an
   audit", and the unmerged product branch says the ML session audits its own pipelines.
   - Several headline gates sit within the plausible error: residual-DI gate 1 passed by 0.001,
     set 5 by 0.003, and the lowpass missed by 0.0009.
   - Every "zero-render" step that reuses stored half-A scores, and every reused rung-1 or label
     render, depends on this audit.
   - Knob ceiling's fresh `isolate` menus on 25 parts give a zero-render way to measure it.
2. **Render contention today.** Knob ceiling uses 6 processes for at least 6–9 h. The product
   session must be messaged first, and nothing runs 03:00–04:15.
3. **C′ is fold-2 only.** Leak-free development evaluation of C′ is 18 parts in 8 bands. Stacking
   or comparing against C′ on more parts needs retraining on MPS.
4. **There is little development crunch outside the over-used 33.** 11 of 13 pinned crunch parts
   are set 3. All classed crunch is 17 parts in 8 bands, and 2 extra bands need new renders.
5. **Fewer existing labels than assumed.** Measfix menu renders cover about 52 development parts,
   not 136. The kill panels are at the session's own DI level with rule-1 crops. The 36k
   translator renders are descriptors only, and their kept 5% audio is probably unmappable to
   presets (salted `hash`).
6. **Disk.** About 65 GB is free, and the practice floor is 30 GB. That leaves about 35 GB usable,
   so WAV storage of the ladder or a bank is infeasible.
7. **Tone King at scale.** Fresh processes are slow and wear the licence service (about 10 daemon
   ports per new process). Reused, isolated Tone King renders are not yet characterised for a
   research bank.
8. **Undecided user items that gate the programme:** 8j (close the chooser), v3 adoption, the
   direct-ranker target interpretation, and whether the "no tweaks on the 33" constraint still
   applies.
9. **Separator.** There is no committed separation script, and acoustic and electric guitar are
   mixed in the stem. The MPS speed is unmeasured.
10. **Pooled held-out power.** At most about 11 in-scope bands across sets 4, 5 and 6, and fewer for
    crunch (about 9). Port St Willow needs a declared sensitivity. Set 5 would be on its second
    use, and sets 1–2 are already used 3–5 times.
