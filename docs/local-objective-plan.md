# Arm A's local objective, step 0 and experiment 1: plan (2026-10-16)

Declared 2026-10-16, before any render. It runs the first two items of
[research/local-objective-2026-10.md](research/local-objective-2026-10.md) (PR #201): step 0
and experiment 1 from "Three experiments", with the cheap diagnostics. Development data only.
Code: `learn/local_objective.py`, tests `tests/test_local_objective.py`.

The user's rules apply:
- **No pass/fail bars.** Every result is an effect size with a 90% band-clustered interval.
- **No fixed render limit** ([ML plan](research/ml-plan-2026-10.md), decision 2). Each step
  declares an evidence-based stopping rule, gives its expected renders and hours, and reports
  the renders it used.

**Status:** reviewed 2026-10-16 (`tmp/local-objective-plan-review.md`, local): approved with 10
required changes, all folded in as [amendment 1](#amendment-1-2026-10-16-before-any-render), before
any render. Where the amendment and the sections below differ, the amendment governs. Nothing
renders before the user's yes. Experiment 1 has run ([results](local-objective-results.md)).
[Amendment 2](#amendment-2-2026-10-16-before-any-1b-render) adds experiment 1b, the matched cell.
[Amendment 3](#amendment-3-2026-10-16-before-any-1c-separation-or-render) adds experiment 1c, a real
separator (Mega-53) in 1b's matched design, with the review's six changes as
[amendment 3a](#amendment-3a-2026-10-16-before-any-1c-separation).

## Why

- Near the starting preset S, arm A's rebuilt objective ranks settings at a Spearman of
  **−0.126** against the true objective (2b: fold 3 only, 3 bands, 5 parts, 15 cells). It ranks
  the factory menu at about 0.78.
- That local comparison changes four things at once:
  - the DI: C′'s rebuild against the measure DI;
  - the reference: the separated stem against `reference.wav`;
  - the lag: −52 against the part's `judge_lag`;
  - the activity mask: from the rebuilt DI against the measure DI.
- Nothing committed separates them. The DI and the stem stay in any song-only product; the lag and
  the mask are free to change.
- Step 0 settles the plumbing and reads stored data. Experiment 1 builds a 14-band local set,
  keeps its audio, and separates the four.

## Inputs committed with this plan (zero renders)

The research asked for these before any render; they are in
[audits/arm-a-2026-10-16](audits/arm-a-2026-10-16/README.md):
- **The audit scripts' outputs** `a1`–`a5b`, `a6_exp2`, `a7_local`, `a8` (`levers-audit/*.out`),
  re-run on 2026-10-16 from the Mac's stored files. Two that this plan uses:
  - `a7_local.out` gives the true DI's cross-half Spearman per fold-3 cell, with refusals ranked
    worst: median 0.94, and only one cell below 0.66 (Prodigal on the AC20, 0.45). With refusals
    ranked worst, C′'s local fidelity is −0.045 (its first line), against −0.126 with them
    dropped (`a7b_local.out`).
  - `a6_exp2.out` finds no fallback to the record as the mask in any net's menu scores, and
    repeat renders within 3e-5 (log).
- **Step 0c's per-cell figures**, `exp4-step0c-dac-cells.json` (built by
  `exp4_step0c_dac_cells.py` from `~/ndsp-presets/learn/di-fine-structure/step0/`): per-cell m,
  the 4-codebook figures, the quiet-frame level, the 1/5/10-ms crest and the resample-only control.
  - On fold 3's 4 cells, the mean margin m is 0.188 (true DI), 0.168 (DAC-9), 0.118 (DAC-4) and
    0.010 (C′).
  - On all 12 cells, DAC-4 and DAC-9 keep the true DI's sign of m on 12 of 12.
  - The resample-only control is exact to within 0.003 dB on every crest and quiet figure.

## Step 0: settle the plumbing

### 0a. Is input gain a pure pre-gain? (5 renders)

- **Cell:** just-don't-talk on the PR12 (fold 3, clean, in one of the two negative bands).
  - All six S presets have input gain at 0 dB and the gate off.
  - Only the PR12 clean S has a stage that could sit ahead of input gain: its compressor is on.
    So this cell is the one where exactness could break.
- **Renders**, through the part's measure DI at S. The LUFS normaliser is bypassed: the DI array
  itself is scaled.
  1. warm-up: (DI, input gain g + 6 dB);
  2. (DI × 10^(6/20), g) and (DI, g + 6);
  3. (DI × 10^(−6/20), g) and (DI, g − 6).
  - That is the check's 4 renders plus the usual warm-up, 5 in all. The warm-up repeats render 2's
    second setting, so it also gives the repeat floor.
- **Read, per pair:**
  - the residual energy in dB, after the 0.25 s isolate fade-in;
  - the largest sample difference;
  - the judge on both halves (the unscaled DI as the mask for all) and the |log| between the two
    members, against the 0.005 repeat tolerance and the repeat floor.
- **What follows.** At the repeat floor and within 0.005, a DI level error of ε dB is exactly an
  input-gain error of ε dB, so experiment 2's level variants and input-gain shifts become one
  experiment.
- **If it is not exact,** the same 5 renders run once on the same part's SW50R, whose S has the
  compressor off (`pregain --cell "cambridge-just-don-t-talk-elecgtr3|sw50r"`). That tells
  whether the compressor is the cause. It runs without a further yes.
- **Stopping:** a fixed set (5 renders, or 10 with the follow-up). Minutes.

### 0b. Zero-render diagnostics

`diag` writes `~/ndsp-presets/learn/local-objective/step0/diagnostics.json`. It uses 2b's stored
local files (fold 3: 15 cells × 40 settings × 4 nets, true d on both halves), the stored K_S and
arm A searches (all 144 directions, replayed exactly) and the stored rebuilds.

The 2b rows have 3 bands and 5 parts, so they are descriptive. They are shown with the band
interval and the part interval. D2 and D3 come first, because they decide what experiment 2
leads with.

| | Diagnostic | Data | Computed | What it tells |
|---|---|---|---|---|
| D1 | The true DI's cross-half local Spearman, and the true-d spread | 2b | ρ(d_A, d_B) on each cell's 40 settings: pairwise-finite and with refusals ranked worst; SD of log d; the number of reliable pairs | How stable the true local order is across musical content. That is the scale that places −0.126 (the menu analogue is 0.97) |
| D2 | **Partial Spearman controlling Δinput gain**, and Spearman at S's input gain | 2b, every net and the 4-net ensemble | Per half, the rank partial correlation of the objective and the true d given the signed input-gain move from S, averaged over halves. Also the plain Spearman on the settings whose input gain equals S's (at least 5 needed) | Whether the inversion is mostly the drive axis (profile it out) or also in the tone knobs and mics |
| D3 | Per-knob bias regression and 3-way sign agreement | 2b (C′) | Per cell and half, OLS of log obj − log true on each continuous knob's unit move from S (knobs with ≥ 4 distinct values; input gain signed). The same fit on log obj and log true separately, each coefficient classed −/0/+ at one standard error. Reported: the band-weighted bias per knob, the true × obj sign table, and agreement where the truth's sign is not 0 | Which knobs are biased, which way, per part. This is a partial version of the committed marginal split (input gain 3/13, SW50R Mid/Level/Bass 0/10) |
| D4 | DI level statistics per part | 24 rebuilds and measure DIs | GCC-aligned rebuild against measure DI: 99.9th-percentile level difference, quiet-frame level, 1/5/10-ms crest error, gap level, 3–8 kHz share; Spearman across fold-3 parts against D3's input-gain bias | Whether the input-gain disagreement tracks a level error (n = 5: descriptive) |
| D5 | σ_d | 2b | The band SD of the paired net differences (1z, 1a, 1b, E4 − C′), pairwise-finite and with refusals ranked worst | The noise scale for paired comparisons in experiments 1–2 |
| D6 | The coarse/fine split inside 2b | 2b (C′, E4) | Concordance on pairs whose largest knob move is ≥ 0.25 (coarse), 0.125–0.25 (mid) or < 0.125 (fine), or that differ in a mic or switch (categorical) | Whether the 0.78-against-−0.13 split holds within one local set, which would support a step-size floor |
| D7 | Arm A ∩ K_S on all 144 directions | stored curves | Per direction, the settings both searches evaluated (same S, same seed): their count; the Spearman of A's objective against K_S's true d (search half; at least 8 shared); the length of the identical prefix; and per knob, decisions taken alike before the first divergence against the knob where they diverged | Free (rebuilt, true) pairs on 14 bands, and the first decision each search disagrees on |
| D8 | K_S optima at the knob limits | 144 stored K_S finals | Per amp, class and knob: the share at each limit and in the interior, and whether a part's two directions land within 1/8 of each other | A knob-specific prior (for example input gain at the floor), if any. Location priors in general did badly |
| D9 | Fallback counts | 2b local files, arm A files | How often the stem stood in as the mask | Whether the mask was ever in play on the rebuilt side |
| D10 | Step 0c per cell | committed JSON (above) | — | Already read |

**What to expect (expectations, not rules):**
- If D2's partial Spearman is clearly positive while the plain one is negative, experiment 2
  leads with input-gain profiling and a learned offset.
- If the tone knobs are also inverted, with a band-dependent sign, it leads with the learned
  correction and with experiment 1's reference decomposition.
- The committed marginal split (SW50R Mid, Level and Bass agree on 0 of 10) makes the second
  branch the likelier one.

**Stopping and cost:** zero renders. Minutes of CPU.

## Experiment 1: a 14-band local set with audio, and a four-way decomposition

### The settings Σ (frozen; zero renders to build)

- **Cells:** all 72 (part, amp) cells of step 3: 24 parts × 3 amps, in 14 bands (Honey is out,
  as before).
- **Per cell, 48 settings, in this order:**
  1. **S**, the starting preset.
  2. **S's ±1/8 neighbourhood.** Each continuous knob moves ±1/8 of its range in unit scale, so
     input gain moves ±4 dB. Each switch is flipped. A side that would leave the range is
     dropped. Mics are left to the next two groups. That is 19 settings on the PR12, 26 on the
     SW50R and 21 on the AC20 when the left cab is on, fewer when it is off (1,479 in all). Values
     are formatted exactly as `coord_search` formats its candidates.
  3. **A seeded draw from both K_S directions, up to 40 settings.** Both directions' K_S
     trajectories are replayed, pooled and deduplicated, and the settings already in Σ are
     removed. The draw uses `random.Random("20261032|<part>|<amp>")` (1,329 in all).
  4. **8 points from arm A's paths.** Both directions' arm A searches are replayed (all 150
     evaluations each), pooled and deduplicated, and the settings already in Σ are removed. The
     draw uses `random.Random("20261033|<part>|<amp>")` (576 in all).
- **In all:** 3,456 settings. Computed with zero renders on 2026-10-16, Σ hashes to
  **`ee91f710947dbb5c`**. `sigma` refuses to freeze any other set. Every stored search replayed
  exactly (0 mismatches).
- **Why this mix:**
  - The neighbourhood is the step-1/8 decision a search makes. It is the only part that is
    balanced by design, and it carries the 3-way and regret measures.
  - The K_S points are where the true search goes (2b's design).
  - The arm A points are where the rebuilt search goes. Without them the set would be limited to
    the true search's range.
- **Stored values carried by each setting** (for the corner checks, below):
  - K_S's stored true d, on 1,425 settings (S and any neighbour K_S also rendered included);
  - arm A's stored rebuilt objective on its search half, on 697;
  - on fold 3, 2b's stored C′ objective, on 44.

### Renders

- **Every setting renders twice:**
  - through C′'s rebuild of the part's stem (its own fold's C′:
    `song-settings/rebuilt/<part>.npy`, leak-free by fold);
  - through the measure DI.
- **Warm-ups:** one per (cell, DI), at S.
- **Total:** 2 × 3,456 + 144 = **7,056 renders**.
- **Audio:** each render is saved as a 16-bit mono FLAC, peak-normalised to 0.99. The level
  factor is kept in the cell's record, so scoring restores the level exactly.
- **Machine:**
  - `knob_ceiling.Renderer` (`isolate=True`), 3 shards;
  - at most 3 render processes machine-wide, checked before each cell, counting this step,
    `ks_extend run`, `song_relabel render-new/probe` and `song_soundspace
    score-targets/score-songs/c-start`;
  - the swap guard; launched with `setopt no_bg_nice` and `OMP_NUM_THREADS=1`; `--after PID` to
    queue behind a job.
- **Hours:** about 5k renders per hour at 3 processes (the label table ran 6.5k in about 1 h
  15 min). So about **1.4 hours**, longer if other sessions' jobs share the cap.

### The stopping rule: a fixed set, for a declared reason

**Every cell is needed for the 14-band power.**
- Experiment 1 is a measurement, not a search, so there is no curve to flatten.
- Its precision comes from bands, not from settings:
  - the minimum detectable paired effect is 0.71 σ_d with 14 bands, against 2.30 σ_d with 3;
  - at 40 settings, the within-cell SD of a Spearman (about 0.16) is already below the
    between-band spread.
- So all 72 cells run with 48 settings each. There is no data-dependent stopping and no
  extension.

**Only breakage stops it:**
- **The true-d check,** run as each measure-DI render lands. A K_S setting's re-rendered true d
  differs from its stored value by more than 0.005 (log) on either half. Stored repeats agree
  within 3e-5 (a6), and S's own repeat within 2e-6.
- **The disk guard** (below).
- **The swap guard.**
- **The live menu's S differs from arm B's stored copy.**

The report gives the renders used per DI, warm-ups included, read from the cell records,
against the 7,056 expected.

### Scoring: the factorial (CPU only, from the FLACs)

- **Every render is scored 12 ways:**
  - reference {stem, `reference.wav`};
  - lag {−52 (`rebuilt_distance`'s), the part's `judge_lag`, 0};
  - mask {the render's own DI, the record}.
  - With 2 DIs, that is 24 configurations, each on both halves.
- **The own mask:**
  - For C′, it keeps `rebuilt_distance`'s fallback: the record stands in as the mask when the
    rebuilt DI is refused for activity. That is the current objective.
  - For the measure DI there is no fallback, as in `knob_ceiling.judge`. That is the true d.
  - A refusal scores inf.
- **The two check corners:**
  - C′ / stem / −52 / own is arm A's objective. It should reproduce arm A's stored values (697
    settings) and 2b's (44).
  - measure / reference / judge_lag / own is the true d. It should reproduce K_S's (1,425).
  - Reported: the median, the largest and the count beyond 0.005, from the float renders (at
    render time) and from the FLACs (at score time). The FLAC figures also bound the 16-bit
    quantisation's effect.
- **CPU:** measured at about 1.7 CPU-seconds per render for all 24 judge calls (a smoke run of
  the scorer on 192 stand-in FLACs). That is about 3.4 CPU-hours, or **about 1.2 hours** on 3
  workers. Scoring runs after the renders, not beside them.

### Measures (declared now)

**Aggregation:**
- Each cell's value is the mean over its two halves.
- Cells are averaged to parts (over amps), then to bands.
- The figure is the band-weighted mean with a 90% band-clustered t interval (13 df,
  `song_readout.bw_stats`).
- Reported beside it: the part-weighted interval, the leave-one-band-out range, the bands above
  and below 0, and per-amp and per-class figures. Crunch (5 parts) is descriptive.

**Primary measure: same-half local Spearman.**
- Per half, the Spearman of a configuration's distance against the true d over Σ. Settings where
  either is non-finite are dropped, as in 2b's headline.
- The C′ corner on 14 bands is the headline, with the ceiling beside it. On fold 3 it should land
  near 2b's −0.126 (same objective, new settings).
- Every other configuration is reported as its cell-paired difference from the C′ corner.

**Co-primary: reliable-pair accuracy.**
- A reliable pair is one whose true order is the same, and not tied, on both halves.
- The measure is the share of reliable pairs the configuration orders correctly (a tie counts
  half), on each half, averaged.
- Chance is 0.5; the truth is 1.
- It strips the near-ties that pull any Spearman toward 0.

**The ceiling: the true DI's cross-half local Spearman** ρ(d_A, d_B) per cell.
- Every configuration also gets a cross-half Spearman, ρ(objective on one half, true d on the
  other). That is what a search faces when it reads one half and is judged on the other.
- The truth's own cross-half figure is the ceiling. So in cross-half form, all 24 configurations
  and the ceiling are on one scale.
- Fractions of the ceiling (ratios of band-weighted means) are descriptive.

**The decision-relevant contrast: measure DI / stem / judge_lag / own ("decisive").**
- It is the best any DI fix could reach with only the reference a song gives.
- Reported:
  - same-half, paired against the C′ corner;
  - cross-half, paired against the ceiling and as a fraction of it.

**The decomposition:**
- **One change at a time from the current objective** (same-half, paired against it): DI,
  reference, lag `judge_lag`, lag 0, mask, and all four DI-and-reference changes together
  (decisive).
- **One change at a time from the truth** (cross-half, paired against the ceiling): DI (C′),
  reference (stem, which is decisive), lag −52, lag 0, mask.
- **Main effects,** each the mean over the other factors' levels, and the **DI × reference
  interaction**. These are computed on the cross-half Spearman and on reliable-pair accuracy.

**Secondary measures, in this order:**
1. **Per-knob 3-way agreement on the neighbourhood.** Does the configuration keep what the truth
   keeps among {S−, S, S+}, exactly as one `coord_search` step decides? A switch is 2-way.
   - Order: input gain first, then amp knobs, cab, switches.
   - Chance is 1/3 (1/2 for switches).
   - With the regret, log true d of the kept setting minus the best of the three.
   - For the C′ corner, decisive, measure / stem / −52 / own, and C′ / reference / judge_lag /
     own.
2. **The neighbourhood pick's regret:** the configuration's best of S and all its neighbours,
   in log true d against the neighbourhood's best.
3. **The partial Spearman controlling Δinput gain,** for every configuration.
4. **Concordance by pair class:** coarse (largest knob move ≥ 0.25), mid, fine (< 0.125), and
   categorical (a mic or switch differs). For the C′ corner and decisive.
5. **Spearman with refusals ranked worst** (`a7_local.py`'s convention).
6. **Fallback counts** per configuration.

The end-to-end held-half log ratio of the stopped-and-shrunk search is experiment 3's, not this
step's.

**What to expect (expectations, not bars):**
- If decisive comes out close to the ceiling, the stem costs little and the DI is the lever.
- If it is far below, the reference is the bottleneck, and DI work should pause while the
  experiment 2 plan is written.
- With σ_d of about 0.06–0.16 (2b's band means), 14 bands can resolve differences of about
  0.04–0.11 in Spearman.

### Optional: the DAC-9 add-on (fold 3 only, on the user's yes)

- **The DI:** each fold-3 part's measure DI, round-tripped through DAC 44 kHz with 9 codebooks
  (`learn/dac_roundtrip.py` in `dac-venv`, CPU), back at 48 kHz and −22.9 LUFS.
  - A GCC lag check against the raw DI stops the run beyond ±3 samples.
- **Renders:** Σ's 15 fold-3 cells: 15 × 48 + 15 = **735 renders, about 9 minutes**.
  - The research's "about 600" assumed 2b's 40 settings. The 135 extra renders keep the add-on
    paired with all of Σ.
- **Scoring:** the same 12 configurations, with the own mask and no fallback.
- **Reported, paired on fold 3 with the wider of the band and part intervals (3 bands):**
  - DAC-9 / stem / judge_lag / own, against decisive and against the C′ corner;
  - DAC-9's main effect against C′.
- **The research's reading (not a bar):** if this ceiling is not clearly above C′, no E1′
  training is justified.
- **Stopping:** a fixed set, for the same reason as above.

### Disk

- **Measured size:** 48 stored step-0b renders (10 s, 16-bit mono FLAC) average 0.48 MB, at most
  0.68 MB.
- **This experiment:** 3.4–4.8 GB, plus 0.35–0.5 GB for the DAC add-on. Scores take tens of MB.
- **Free space** on 2026-10-16: 36.7 GB, against the 31 GB guard the other steps use (the ML
  plan keeps 30 GB free).
- **The guard:**
  - `render` refuses to start unless free space, less the remaining renders at 0.7 MB each, stays
    at 31 GB or more. The full run needs about 35.9 GB free.
  - It stops before any cell that would take free space under 31 GB.
  - If other sessions leave too little room, the user is asked what to delete. This plan deletes
    nothing.
- **Retention:** the FLACs stay until experiments 2 and 3 are done. Deleting them needs the
  user's yes.

## Relation to experiments 2 and 3

- **They are planned after experiment 1's readout.** Each gets its own plan, stopping rule,
  ledger entry and yes. Neither is declared here.
- **Experiment 1 gives them:**
  - a frozen Σ;
  - C′ baseline FLACs and scores to pair with: experiment 2's level and drive variants render the
    same Σ through C′;
  - the true d on Σ, on 14 bands, for learned corrections scored leave-one-band-out (3a).
- **Step 0 gives them their lead:** 0a's exactness reading, and D2 and D3 (above).
- **The product rule is unchanged:** "52 renders, then shrink halfway to S" stays until something
  beats it on held halves.

## Run order

1. `diag` and `sigma` (zero renders).
2. `pregain` (5 renders; 5 more only on a miss).
3. `render --shard i/3` (experiment 1), queued behind any running render jobs by the cap.
4. `score --workers 3`, after the renders end.
5. `report` (zero renders) writes `report.json`, and the readout goes to
   `docs/local-objective-results.md`.
6. On the user's yes, the DAC add-on: `dac-prep`, the DAC round trip, `render --di dac9`,
   `score --di dac9`, `report`.

| Step | Renders | Hours |
|---|---|---|
| 0a | 5 (10 with the follow-up) | minutes |
| 0b | 0 | minutes (CPU) |
| Experiment 1 | 7,056 | about 1.4 h rendering at 3 processes, then about 1.3 h scoring on 3 workers (amendment 1) |
| DAC-9 add-on (optional) | 735 (+2,793 if its extension rule fires, on the user's yes) | about 0.15 h (+0.6 h), then about 0.1 h scoring |

## Ledger and limits

**Ledger.** The entry `local-objective` in [dev-test-ledger.json](dev-test-ledger.json) was
entered on 2026-10-16, before any render. Its `repeat_use`:
- This is a further post-hoc, unblinded use of step 3's 24 scored parts and 142 directions.
  Their uses so far: knob ceiling, knob ceiling 2, label table, step 3, arm A levers, the
  soundspace plan, the K_S ceiling extension and the arm A listening test.
- It is at least the fifth use of fold 3's 5 parts (step 3, experiment 4, the levers' experiments 2
  and 2b, now this).
- Their held halves were read by earlier steps, so every figure is a development reading, not a
  fresh estimate.
- Any fix that is to ship is scored on a fresh draw of parts outside the 24 before it ships.

**Seeds:** 20261032 (the K_S draw) and 20261033 (the arm A draw), each as
`random.Random("<seed>|<part>|<amp>")`. Nothing else is random: cells are sorted, shards are
`i::3`, and the render order is fixed.

**Limits:**
- **Bands:** 14 bands, 24 parts, 19 of them clean. Crunch (5 parts) is descriptive.
- **Σ is a mixed set.** The K_S points lean toward where the true search went, and the arm A
  points toward where the rebuild went. A Spearman over Σ depends on that mix. Only the
  neighbourhood is balanced by design, and it carries the 3-way and regret measures.
- **One separator and one net:** the stems as stored, and C′ (each part's own fold).
- **The lag levels are literal values,** not "the right lag" for each pairing.
- **The truth is the judge** (flat weighting, the recording's bands), not listening.
- **Refusals:** silent settings (1.4% of arm A's directions) score inf. The pairwise measures
  drop them; the refusals-ranked-worst version is reported beside.
- **Step 0a** checks one cell (two at most).
- **Step 0b's 2b rows** are 3 bands, 5 parts: descriptive.
- **Development data only.** No listening to sets 5 or 6. Open-licence tools only (DAC is MIT).

## Amendment 1 (2026-10-16, before any render)

From the independent review (`tmp/local-objective-plan-review.md`, local: approve with 10 required
changes) and the judge-lag audit of the same day. All 10 changes are made in code and tested; no
render has run. Each item below replaces what the sections above say on the same point.

**1. Lags are relative to each DI's own alignment.**
- **The audit.** The three large judge lags are real session offsets, not a bug:
  Drag_Me_Down (judge_lag + 52 = 966 samples), Today's_The_Day (672) and femme (573), 12–20 ms.
  The amp tracks sit behind their DIs throughout those sessions; this is documented in
  [validation-lags.json](validation-lags.json) and the catalogue (femme is flagged
  `late_amp_track`).
  - The measure DI keeps the raw DI's timing, because `eq_to` is zero-phase. C′'s rebuild sits on
    the recording's timeline, as does the flat-reference DI. The review's "about −2 samples" came
    from a recording-timeline DI.
  - `aligned_distance` uses a fixed lag; moving it by ±25 samples changes d by at most 0.005.
  - The audit, its scripts and their outputs are in
    [audits/judge-lag-2026-10-16](audits/judge-lag-2026-10-16/README.md). `judge_lag` and its
    source are unchanged.
- **The lag levels** are now, per DI:
  - **native:** the DI's own lag. For C′, −52 − Δ with Δ = 0 (`rebuilt_distance`'s, the current
    objective). For the measure DI and DAC-9, the part's `judge_lag`. These are the declared lags.
  - **other:** the other DI's native lag. **Diagnostic only.**
  - **zero:** 0. **Diagnostic only.**
  - **gcc** (C′ only, CPU, deployable, diagnostic): −52 − GCC(rebuild, stem), the rebuild's own
    measured alignment with the stem. The review found GCC(rebuild, stem) near −53 on 11 parts and
    0 on 13; the report records the value per part.
- **Corners and decisive** are at native lags: the current objective is C′ / stem / native / own,
  the true d is measure / reference / native / own, and decisive is measure / stem / native / own.
  So the "DI" step from the current objective is decisive itself, and it no longer adds a
  misalignment.
- **The DI, reference and mask main effects and DI × reference** are taken at native lags only.
  **Lag effects are reported within each DI** (other − native and 0 − native for C′, the measure
  DI and DAC-9; gcc − native for C′).
- **Every DI or lag contrast is reported twice:** on all cells, and without the 3 large-offset
  parts (|judge_lag + 52| > 100 samples, computed from the parts: those three, in the bands Adam
  Buckley, Eat The Feeder and Wall Of Death).
- **A zero-render alignment table** is added to step 0 (`align`, and D0 in `diag`): per part,
  judge_lag + 52; GCC for rebuild ↔ measure DI, rebuild ↔ stem, stem ↔ reference and reference ↔
  measure DI; the GCC-aligned C′ lag; and the closure of the four. It is a record, read with the
  audit above; the large offsets are explained by that audit, not by this table.

**2. The record mask is moved into DI time.** The judge reads the mask at DI time t − lag − 52 for
recording time t, so passing the recording as the mask at any lag other than −52 shifted it by
lag + 52 samples. The recording is now advanced by lag + 52 (zero-padded) before it is used as the
mask, both for the `record` level and for the C′ fallback. At −52 this is the identity, so the
current objective still equals `rebuilt_distance` exactly (a test checks it on real signals,
fallback included). "Record" means the reference in use: the stem or `reference.wav`.

**3. Cross-half contrasts from the current objective.** The one-change-at-a-time contrasts from
the current objective are reported cross-half and as reliable-pair accuracy as well as same-half.
The DI-against-reference reading rests on the cross-half and reliable-pair figures; same-half stays
only for comparability with −0.126. Reliable-pair accuracy is 1 for the truth by construction: a
trivial corner, not a ceiling.

**4. A breakage stops every shard.**
- The corner checks run on every render as it lands (the plan's wording, now the code's).
- A failed check records the cell as `check_failed` (never `done`), writes a shared stop file
  (`STOP.json` under the step's folder), and exits. Every shard checks the stop file before each
  cell and at start. A `check_failed` cell is not re-rendered until it is investigated and the stop
  file deleted.

**5. The C′ corner is checked at render time.** For the settings with a stored arm A value (697,
about 10 per cell) or a 2b value (44), the current objective is computed from the float render and
compared with the stored search-half value. Beyond 0.005 (log), change 4's stop applies.

**6. The disk check covers all shards.**
- `render`'s start check now counts every shard's remaining renders, as the plan said.
- Free space at amendment time: **36.0 GB** (it was 36.07 GB at review and 36.7 GB when the
  plan was written; `song_soundspace train` and `song_relabel features` are writing). The full run
  needs about 35.9 GB at the start, so it would not start today.
- **Before launch, the user is asked** to free about 3–5 GB, or to accept a resumable guard stop
  (`render --accept-guard-stop`: the start check is skipped, the per-cell 31 GB guard still stops
  the run, and a stop loses at most one partial cell, whose renders are still counted). The
  free-space figure at launch is recorded in the results.

**7. The cap is one-directional.** Only this job enforces the 3-process cap against the others:
`ks_extend`'s pattern list doesn't count `local_objective` or `song_soundspace`, and
`song_soundspace` has no cap. So the shards launch only when no other render job is queued, or the
other sessions start theirs with `--after` on these shards' PIDs. One foreign render pauses all
three shards; that is conservative and accepted.

**8. The DAC add-on and its extension rule.**
- It keeps 735 renders on all 48 settings of the 15 fold-3 cells.
- On fold 3 every DAC-9 figure, the "DI dac9 − cprime" main effect included, uses the wider of the
  band and part intervals (it used a 2-df band interval before).
- Fold 3 has 3 bands, where the minimum detectable effect is 2.30 σ_d, so "not clearly above C′"
  is the likely reading whether or not DAC-9 helps. That reading is *undecided*, not negative.
- **The extension rule (declared now):** if the fold-3 interval of DAC-9 / stem / native / own
  against the current objective, or against decisive, contains 0 (cross-half Spearman), the add-on
  extends to the other 57 cells: 57 × 49 = **2,793 renders, about 35 minutes**, on the user's yes
  (`dac-prep --all-folds`, the DAC round trip, `render --di dac9 --all-folds`). The report states
  whether the rule fires. Its FLACs add about 1.3–1.9 GB, under the same disk guard.

**9. Three-way chance per knob.** Chance is 1 / the number of settings compared: 1/3 for a
continuous knob with both sides, 1/2 where a side was clamped and for a switch. The report gives
each knob's chance beside its agreement.

**10. The ledger** entry records this review and amendment, says "at least the fifth use" of fold
3's parts, and records the lag, mask and stop changes.

**Also folded in (the review's optional items):**
- `load_sigma` recomputes Σ's hash and refuses a file that is not the plan's Σ.
- D1's true-d spread uses both halves.
- 0a flags its reading (`clip_risk`) if the DI's peak + 6 dB exceeds 0 dBFS.
- Every aggregate reports its realised σ_d (the SD of the band means), so each contrast's own noise
  scale is visible; "resolves 0.04–0.11" assumed the nets' σ_d.

**Cost changes:**
- C′ renders are now scored 16 ways (the gcc level), so scoring takes about 2.0 CPU-seconds per
  render (a smoke run on 192 stand-in FLACs): about 3.9 CPU-hours, **about 1.3 hours** on 3
  workers.
- Renders are unchanged: 5 (or 10) for step 0a, 7,056 for experiment 1, 735 for the DAC add-on,
  and 2,793 more only if its extension rule fires and the user says yes.

## Amendment 2 (2026-10-16, before any 1b render)

Experiment 1b, the matched cell that experiment 1's audit asked for
([results](local-objective-results.md), "What it decides"). Declared after experiment 1's readout
and before any 1b render. Same rules: no pass/fail bars, a declared stopping rule, renders reported.

**Why.** Experiment 1 found that the rebuild's error and the stem's partly cancel: today's
objective (C′ rebuilt from the stem, scored against the stem) is 0.289, C′ scored against the amp
track is 0.409, and the ceiling is 0.864 (cross-half local Spearman). The missing cell is C′
rebuilt from the amp track *and* scored against it: what today's C′ would give with a perfect
separator. **It is the ceiling for any separator with today's C′.**

**What runs.**
- **The rebuild (zero renders, CPU, the torch interpreter):** `rebuild-ref` rebuilds each part's
  `reference.wav` (the amp track) with its own fold's C′, exactly as `song_settings.rebuild_all`
  rebuilds the stem: the same network (DONE marker required), re-EQ'd by fold 2's average − fold
  f's, at −22.9 LUFS. Experiment 4's leak assertion runs per part. The log records the network and
  the GCC lag against `reference.wav` and against C′'s stem rebuild. 24 arrays of about 4 MB.
- **Renders:** the same frozen Σ (hash `ee91f710947dbb5c`) through the matched rebuild: 72 × 48 =
  3,456 renders plus 72 warm-ups, **3,528**. About 0.7 h at 5k/h on 3 processes.
- **Scoring (CPU, from the 16-bit FLACs):** against `reference.wav` with the rebuild's own mask
  and the C′ fallback (the record, moved into DI time, as amendment 1):
  - **matched:** C′'s native lag, −52 (the declared configuration);
  - **matched, gcc lag:** −52 − GCC(matched rebuild, `reference.wav`). Diagnostic only.
  - 4 judge calls per render: about 0.3 CPU-s, a few minutes on 3 workers.
- **The truth** is experiment 1's measure-DI scores on the same Σ (no new truth renders). Today's
  objective and C′ / reference are experiment 1's C′ scores.

**Report (`report-1b`, zero renders), on all of Σ and on its three subsets** (S and its ±1/8
neighbourhood; the K_S points; the arm A points):
- **matched:** the cross-half local Spearman and reliable-pair accuracy (and same-half, for
  comparability), band-weighted with 90% band-clustered intervals, with the ceiling beside them;
- **the simple effect against today's objective (C′ / stem), cell-paired:** matched − current,
  cross-half and reliable-pair accuracy;
- matched − C′ / reference, paired (what rebuilding from the amp track adds once the amp track is
  the reference);
- **per band:** matched, current, their difference and the ceiling (cross-half);
- the gcc-lag diagnostic, and the renders used against the 3,528 expected.

**Reading (estimates only, declared now)**, on matched − current, cross-half, all of Σ:
- **above** (the 90% interval is above 0): today's C′ ranks clearly better with a perfect stem.
  The next step tests a better real separator feeding both the rebuild and the reference.
- **near** (the interval contains 0, and its top closes less than a quarter of the gap from today's
  objective to the ceiling, about 0.14 on experiment 1's figures): the rebuild limits even with a
  perfect stem.
- **undecided** (otherwise) or **below**: reported as such; the next step is the user's choice.
- The share of the gap the estimate closes is reported beside it. The subsets are descriptive; the
  arm A subset carries the winner's curse noted in experiment 1.

**Stopping rule: a fixed set, declared.** 1b is a measurement paired cell by cell with experiment
1's Σ; every one of the 72 cells is needed for the 14-band interval, as in experiment 1. No
data-dependent stopping and no extension. Only breakage stops it.

**Guards (as amendment 1):**
- **Render-time check:** the matched rebuild has no stored values, so each cell's render of S is
  checked against the cell's warm-up at S (a repeat) on the matched objective, within 0.005 (log)
  on both halves. A failure records the cell `check_failed` and writes the shared `STOP.json`, which
  every shard checks before each cell.
- **Disk:** about 1.7–2.5 GB of FLACs (0.48–0.7 MB each). The start check counts all shards'
  remaining renders against the 31 GB guard (66.9 GB free when this amendment was written); the
  per-cell guard still applies.
- **The cap:** at most 3 render processes machine-wide, enforced only by this job (amendment 1,
  change 7); swap guard; `setopt no_bg_nice`, `OMP_NUM_THREADS=1`; `--after PID` to queue.

**Run order:**
1. `~/ndsp-presets/tools/demucs-venv/bin/python -m learn.local_objective rebuild-ref` (torch 2.14,
   the interpreter that built the stem rebuilds; CPU, zero renders), which must pass its checks;
2. `render --di cprime_ref --shard i/3` (3,528 renders);
3. `score --di cprime_ref --workers 3`;
4. `report-1b`, then the readout in `docs/local-objective-results.md`.

| Step | Renders | Hours |
|---|---|---|
| 1b rebuild | 0 | minutes (CPU) |
| 1b renders | 3,528 | about 0.7 h at 3 processes |
| 1b scoring and report | 0 | minutes (CPU) |

**Ledger and limits.** The `local-objective` entry gains `amendment_2`, entered before any 1b
render. It is a further unblinded use of the same 24 parts and of experiment 1's Σ, read after
experiment 1's results: a development reading, not a fresh estimate. The amp track is not
available for a released song, so 1b is a ceiling, not a product figure. One net (C′, each part's
own fold) and one rebuild recipe; the separator it stands in for would also change the reference.

### Amendment 2a: review changes (2026-10-16, before any 1b render)

A quick review approved 1b with four changes, all made in code and tested:
1. **Pre-render checks on the matched rebuilds.** `rebuild-ref` asserts, per part, that the matched
   rebuild sits within **3 samples** of C′'s stem rebuild (GCC) and at **−22.9 LUFS within 0.05**.
   If any part fails, or is missing, it stops and records why (`rebuilt-ref/check.json`), and
   `render --di cprime_ref` refuses to start until all 24 pass.
2. **No reading on an incomplete set.** `report-1b` gives its figures, but refuses a reading unless
   it has all **72 cells and exactly 3,528 renders**. A resumed cell that re-renders its warm-up
   therefore blocks the reading until it is explained.
3. **The reading rule is strict.** With 90% interval half-widths of about 0.16–0.35 (experiment 1),
   an interval that contains 0 almost always reaches above a quarter of the gap (about 0.14). So an
   estimate near 0 reads **"undecided"**, not "near"; "near" needs a narrow interval. "Above" still
   needs the whole interval above 0.
4. **FLAC against float.** Each cell's render of S is scored on the DI's own objective from the
   float render and stored with the cell; scoring compares the FLAC score with it (|log| per half),
   and `report-1b` gives the count, the largest and the number beyond 0.005.


## Amendment 3 (2026-10-16, before any 1c separation or render)

Experiment 1c: a real separator in 1b's matched design. Declared after 1b's audited readout
([results](local-objective-results.md), experiment 1b), before any separation or render. Same rules:
no pass/fail bars, a declared stopping rule, renders reported. **Status:** reviewed 2026-10-16
(`tmp/local-objective-1c-review.md`, local): approved with 6 required changes, all made as
amendment 3a below, which governs where the two differ. The user said yes to running 1c on
2026-10-16, after amendment 3a.

**Why.**
- 1b showed that a perfect separator (the amp track) feeding both C′'s rebuild and the reference
  lifts the cross-half local Spearman from 0.289 to 0.541: **+0.252 [0.139, 0.365]**.
- 1c asks how much of that gain a real, better separator recovers.
- **The separator:** Mega-53's `electric-guitar` head, already on disk (`~/ndsp-presets/tools/msst/`,
  approved by the user on 2026-10-15; MIT repo, no separate weights licence).
  - On the 2026-10-08 test it gained +0.5 to +0.6 dB paired SNR over htdemucs_6s, almost all of it
    on single-guitar parts. 18 of the 24 parts here are multi-guitar.
  - In the separator screen, its real-song coherence was higher on all 5 parts. Through C′ (m_both),
    the two separators could not be told apart on 10 cells.

**What runs.**

1. **Separation** (`$MSST_PY -m learn.local_objective_1c separate`; CPU only, alone, zero renders).
   - **The input is exactly what step 3's htdemucs stem got:**
     `<stems>/_work/contexts/<part>/mix_instrumental.wav`, for set 3 (`learn/set3/stems`, 5 parts)
     and sets 1–2 (`learn/poc/stems`, 19 parts).
     - That is about 30 s: the crop − 10 s to the crop + 10 s, shifted inside the session.
     - The crop's 10 s are cut at `crop_offset_in_context`.
     - A set-3 context not rebuilt exactly would fall back to the 10-s crop, as
       `_work/separate_demucs.py` did. None of the 24 does, and a test checks it.
   - **The separator:** `separator_screen.MsstSeparator`, as in the screen.
     - It checks the provenance hashes and commit ea7eb9c.
     - It is pruned to the one head, because the screen's identity check was exact.
     - CPU, 4 threads, `PYTORCH_ENABLE_MPS_FALLBACK=0`.
     - 48 → 44.1 kHz, `demix`, the `electric-guitar` stem, channel mean, back to 48 kHz.
   - **Checks per part.** If any part fails, `separate` stops and records why
     (`sep/mega53/check.json`), and `rebuild` refuses to start:
     - the input's crop slice equals the crop file (under 1e-6, the stem builders' check);
     - the crop is 480,000 samples;
     - **its timing:** GCC(Mega-53 crop, the htdemucs stem) is within ±3 samples.
   - **Logged (descriptive):**
     - both stems' gain-fitted SNR against `reference.wav`;
     - Mega-53's level above 6 kHz relative to htdemucs;
     - on the screen's 5 parts, the largest difference from the screen's Mega-53 stems.
   - **The memory gate.** Mega-53 loads only when all of these hold:
     - no render process from the cap's list is running, and no render server;
     - no MPS training job (`-m learn.<module> train|fit`) and no other separation is running;
     - at least **18 GB** is available (free + inactive + speculative pages). The screen peaked at
       17.1 GB with the full and pruned models both loaded; the pruned head alone peaked at 7.2 GB.
   - It waits for the gate (or exits with `--no-wait`). If anything that blocks it starts between
     parts, it stops; the run resumes per part. The screen's swap guard (256 MB) stays.
   - In turn, `render` now waits while any separation runs.
2. **The rebuild** (`$TORCH_PY -m learn.local_objective_1c rebuild --sep mega53`; CPU, zero renders).
   - It is exactly 1b's: the fold's final C′ (DONE marker), the leak assertion, re-EQ'd by fold 2's
     average − fold f's, at −22.9 LUFS. 1b's `rebuild-ref` now calls the same function.
   - **Amendment 2a's checks:** within 3 samples of C′'s stem rebuild (GCC), and at −22.9 LUFS
     within 0.05. `render --di cprime_mega53` refuses to start until all 24 pass
     (`rebuilt-mega53/check.json`).
   - Logged: GCC against the Mega-53 crop, against `reference.wav` and against C′'s stem rebuild.
3. **Renders:** the frozen Σ (hash `ee91f710947dbb5c`) through the rebuild. That is 72 × 48 + 72
   warm-ups = **3,528 renders**, as 1b. Its guards are 1b's:
   - S against the cell's warm-up at S, within 0.005 (log);
   - S's float score stored for the FLAC check;
   - the shared `STOP.json`, the disk guard (all shards counted at the start), the swap guard and
     the 3-process cap.
4. **Scoring** (CPU, from the 16-bit FLACs): `score --di cprime_mega53,cprime@mega53`.
   - **mega53-matched (the declared configuration):** C′'s rebuild of the Mega-53 crop, scored
     against that crop at C′'s native lag (−52). It uses its own mask and the C′ fallback (the crop,
     moved into DI time, as amendment 1).
   - **Three diagnostics:**
     - **gcc lag:** −52 − GCC(rebuild, the Mega-53 crop);
     - **rebuild only:** the same renders scored against the htdemucs stem;
     - **reference only,** with zero renders (`cprime@mega53`): experiment 1's C′ FLACs rescored
       against the Mega-53 crop.
   - The truth, today's objective and 1b's matched cell are the stored scores of experiments 1 and
     1b.

**Report (`report --sep mega53`, zero renders).** It covers all of Σ, its three subsets (S's
neighbourhood, the K_S points, the arm A points) and all of Σ without the arm A points, and it is
given per band. It reports:
- **mega53-matched:** the cross-half local Spearman, reliable-pair accuracy and same-half, with the
  ceiling beside them;
- **mega53 − current,** cell-paired (cross-half and reliable-pair accuracy). This is the primary
  contrast;
- **the share of 1b's separator gain recovered:** (mega53 − current) / (1b − current).
  - It is band-weighted, on the cells with both, with **Fieller's 90% interval** (t, bands − 1 df).
    That is the ratio's analogue of the band-clustered interval.
  - The interval is unbounded where 1b's own gain is undecided (as near S: +0.085 [−0.03, +0.20]).
  - The leave-one-band-out range is given beside it;
- mega53 − 1b;
- **the decomposition:** reference only − current, rebuild only − current, and mega53 − reference
  only;
- per band: mega53, current, 1b, the ceiling and both differences;
- the stems' SNRs, the gcc-lag diagnostic, the renders used against the 3,528 expected, and FLAC
  against float.

**Reading (estimates only, declared now),** on mega53 − current, cross-half, all of Σ:
- **above** (the 90% interval is above 0): Mega-53 recovers part of the separator's share, and the
  share with its interval says how much. **The product path is to switch the separator,** after a
  fresh-draw check on parts outside the 24. That decision also weighs its cost: about 81–102 s per
  30-s context on the CPU, against htdemucs's 15 s.
- **near zero** (the interval contains 0, and its top recovers less than a quarter of 1b's gain,
  about 0.063): Mega-53 isn't better for this purpose.
- **below** (the interval is under 0): it is worse for this purpose.
- **undecided** otherwise. That is the likely reading for a small effect: 1b's interval half-width
  was 0.11.
- As 2a: there is no reading unless the set is complete, with **72 cells and exactly 3,528
  renders**.
- The subsets are descriptive. The arm A subset carries the winner's curse, so "without arm A" is
  the robustness row.

**Stopping rule: a fixed set, declared.**
- 1c is a measurement paired cell by cell with experiments 1 and 1b. Every cell is needed for the
  14-band interval.
- **Running fold 3 or set 3 first was considered and rejected.** Fold 3 has 3 bands, where the
  minimum detectable effect is 2.30 σ_d, against 0.71 σ_d on 14. So a first look at it could only
  read "undecided".
- There is no data-dependent stopping and no extension. Only breakage stops it.

**The blend (optional add-on, on the user's yes after the Mega-53 readout).**
- `blend` (zero renders) builds LP(Mega-53) + (htdemucs − LP(htdemucs)). It uses the screen's
  filter: a 4th-order Butterworth at 6 kHz, zero-phase.
- **A deviation from the screen:** step 3's htdemucs stem exists only as its 10-s crop.
  - So its high band is filtered on the crop; Mega-53's low band is filtered on its 30-s stem
    before the cut.
  - The edge effects stay within a few milliseconds of the crop's ends, inside the 0.25-s isolate
    fade.
- As in the screen, a part whose relative lag is not 0 gets no blend.
  - `rebuild --sep blend` refuses unless all 24 have one. The screen stopped magilla on a ±1-sample
    lag, so this may block the add-on.
- Then 3,528 more renders (`render --di cprime_blend`), scored and reported the same way
  (`score --di cprime_blend,cprime@blend`, `report --sep blend`).

**Disk.**
- FLACs: about 1.7–2.5 GB.
- Stems: 24 × (30 s + 10 s) of float32, about 0.2 GB.
- Rebuilds: about 0.1 GB.
- Free space when this amendment was written: 58 GB, against the 31 GB guard.

**Scheduling and run order.**
1. `separate`, alone, behind the memory gate. The screen measured 80.6–81.4 s per 30-s context
   (pruned, 4 threads), so about **35 minutes** for 24 parts, with the model load.
2. `rebuild` (CPU, minutes), after `separate` exits.
3. `render --di cprime_mega53 --shard i/3`, under the 3-process cap: about **0.7 h** at 5k per hour.
4. `score --di cprime_mega53,cprime@mega53 --workers 3`, after the renders.
   - That is 6 judge calls per new render and 2 per rescored C′ render, about 35 CPU-minutes.
   - So about **0.2–0.3 h** on 3 workers.
5. `report --sep mega53`, then the readout in `docs/local-objective-results.md`.

| Step | Renders | Hours |
|---|---|---|
| 1c separation | 0 | about 0.6 h (CPU, alone) |
| 1c rebuild | 0 | minutes (CPU) |
| 1c renders | 3,528 | about 0.7 h at 3 processes |
| 1c scoring and report | 0 | about 0.2–0.3 h (CPU) |
| Blend add-on (optional, the user's yes) | 3,528 | about 0.7 h, then about 0.2 h scoring |

**Ledger and limits.**
- The `local-objective` entry gains `amendment_3`, entered before any 1c separation or render.
- It is a further unblinded use of the same 24 parts and of experiment 1's Σ, read after
  experiments 1 and 1b: a development reading, not a fresh estimate.
- **The limits:**
  - one real separator and one net (C′, each part's own fold);
  - **like step 3's stems, it separates the instrumental context** (the record's vocal tracks
    removed). A product would get the full mix;
  - the truth is the judge, not listening.
- Any switch of separator is scored on a fresh draw of parts outside the 24 before it ships.

### Amendment 3a (2026-10-16, before any 1c separation)

The independent review (`tmp/local-objective-1c-review.md`, local) approved 1c with six required
changes. All six are made in code and tested; nothing has been separated or rendered.

**1. Bleed and leak rows** (`report --sep`, `bleed_and_leak_rows`).
- **Every row is on all of Σ.** In each row, the share's numerator (mega53 − current) and its
  denominator (1b − current) sit on the same cells, with Fieller on that row's bands.
- **The bleed flags** come from the bleed audit (`docs/audits/bleed-2026-10-16/bleed-table.json`).
  - The **cell rule** (r4's, the bleed README's table) drops a cell if either half is flagged.
  - The **direction rule** is reported beside it. It drops a direction (objective on one half,
    truth on the other) whose truth half is flagged.
- **The rows,** with 1b's matched − current on each, recomputed from the stored scores:

  | Row | Bands (df) | 1b − current |
  |---|---|---|
  | (a) all of Σ: **the declared reading** | 14 (13) | +0.252 [0.139, 0.365] |
  | (b) no high bleed (cell rule) | 14 (13) | +0.227 [0.127, 0.326] |
  | (c) no moderate or high bleed (cell rule) | 12 (11) | +0.253 [0.145, 0.360] |
  | (d) Cambridge only | 11 (10) | +0.273 [0.162, 0.385] |
  | Telefunken only (descriptive at most) | 3 (2) | +0.174 [−0.49, +0.83] |
  | Without the MUSDB18-train bands (Atlantis Bound, Wall Of Death) | 12 (11) | +0.265 [0.135, 0.396] |

  - The direction rule's rows are beside them: (b) +0.227 on 14 bands; (c) +0.232 on 13.
  - A test checks that (a)–(d) reproduce the audited +0.252, +0.227, +0.253 and +0.273, with their
    band counts.
- **(d), Cambridge only, is the row where the share reads cleanest.** There 1b really is a
  perfect-separator cell.
- **The reading stays on (a).** The 0.063 "near zero" bar applies to (a) only; the other rows are
  descriptive.
- **Fieller's interval is on that row's bands − 1 df** (13, 11 or 10, as above).
  - When the denominator's own interval contains 0, the set is unbounded. With A < 0 and a positive
    discriminant it is two rays (the ratio lies outside a finite gap); otherwise it is the whole
    line.
  - Both are reported as "unbounded", and the shape is named.
- **Also reported:** the decomposition's interaction, mega53 − reference only − rebuild only +
  current. Experiment 1 found that the stem's errors cancel rather than add. So "rebuild only" (C′
  of Mega-53, scored against htdemucs) breaks that cancellation, and it may read negative even if
  Mega-53 helps.

**2. What the share means.**
- **On the bleed parts, 1b is not a separator ceiling, so the share can exceed 1.**
  - In the Telefunken live rooms, the drum and cymbal bleed in `reference.wav` comes from separate
    sources in the mix.
  - A separator can assign that bleed to the drums, so its stem can be cleaner than the amp track,
    which can't shed it.
  - So the share is not capped at 1, and a value above 1 is not an error. 1b's matched cell is 0.60
    on Cambridge but 0.32 on Telefunken (3 bands, confounded with the session).
- **The truth's reference carries the same bleed.** That can't be fixed here; it is a limit.
- **Separator training data.**
  - htdemucs_6s trained on MUSDB18's train split, which holds Atlantis Bound (2 parts) and Wall Of
    Death (femme). So today's objective is optimistic on those 2 of the 14 bands; the row without
    them is the check.
  - Mega-53's training data is not stated. A leak in it can't be ruled out.

**3. The memory gate and scheduling.**
- **The gate is keyed on what loads.** Pruning is decided first, from the screen's
  `identity.json`. The gate is then:
  - **about 11 GB** for the pruned head (the screen's pruned runs peaked at 7.13–7.18 GB RSS, plus
    about 50%);
  - **18 GB** only for the full model, if `identity.json` is missing or not identical.
- **Renders no longer block `separate`.** It may run beside ks_extend:
  - CPU torch at a fixed 4 threads is deterministic (the screen's pruned/full identity was 0.0);
  - offline renders are load-independent, and ks_extend checks its own repeats.
- **Kept:** the training-job, other-separation and memory blockers, and the 256 MB swap-growth
  guard, which is the real backstop.
- `render` still waits while a separation runs.
- **The schedule:**
  1. separate now, beside ks_extend;
  2. rebuild (minutes);
  3. queue the renders with `--after` on ks_extend's shard PIDs, since ks_extend holds all 3 slots
     of the cap.
- **The hours:**
  - separation: about 35 minutes alone, or about **40–50 minutes beside ks_extend** (3 render
    servers + 4 threads on 8 cores);
  - renders: 0.7 h, then 0.2–0.3 h of scoring.
  - **Wall time is dominated by queuing behind ks_extend** (2–4 batches, possibly hours).

**4. The blend's lag rule (declared now, before any blend).**
- The rule is now |relative lag| ≤ 1 sample, with no shift; the lags are reported. Beyond ±1, a part
  gets no blend, and `rebuild --sep blend` refuses.
- Both stems sit on the mix's timeline by construction, so a ±1 GCC reading is most likely
  estimator jitter. Shifting by a jittery estimate could create an offset that wasn't there.
- A real 1-sample offset would cost a dip of −0.28, −0.69 and −0.64 dB at 5, 6 and 7 kHz on the
  shared component (the review's measurement). That is small next to Mega-53's own 8–13 kHz loss.

**5. The blend's edges (corrected wording).**
- The judge's halves are 1.0–5.5 s and 5.5–10.0 s.
  - The start transient of filtering htdemucs's high band on the crop is outside both halves.
  - **The end transient is inside half B,** because the crop ends at 10.0 s. Amendment 3's "inside
    the 0.25-s isolate fade" was wrong.
- **It is negligible.** The review measured it on a 30-s htdemucs stem (femme), filtering on the
  crop against filtering on the full stem and then cutting:
  - the largest difference is −56 dB relative to the peak, at the very edge;
  - it is under −113 dB beyond 0.5 ms, and exactly 0 beyond 5 ms.
- **`blend` now logs this bound per part** (zero renders): the largest difference in dB relative to
  the crop's peak, and how far from the crop's ends it exceeds −100 dB.
  - It is measured on the part's Mega-53 30-s stem as a proxy.
  - On the screen's 5 parts, it is measured exactly on their 30-s htdemucs stems.

**6. Scope.**
- **The headline and the reading are "on the instrumental context":** both separators see the
  record with its vocal tracks removed, as step 3's stems did. The report carries this as `scope`.
- **Any separator switch's fresh-draw check runs on full mixes, with vocals, for both separators.**
  Sets 1–2 contexts also keep `mix.wav`, so a later with-vocals check is possible on 19 of these
  parts.
