# Ground-truth audit, 2026-10-03

An audit of every link from the validation data to the claims in these docs:
ten independent auditors, each required to demonstrate findings with executed
tests, then independent verifiers trying to refute each medium-or-higher
finding, then this synthesis. It audited `b0000e2`. The scripts and outputs it
cites under `scratchpad/audit/` lived in a session scratch directory and are not
committed; every number here was reproduced by at least one verifier unless it
says "auditor only".

**Corrections found after it was written:**
- D-M1 says the Tone King Reset and neutral scoring renders of Hikikomori are
  "all zeros". They are not: they play near-silent, at −50.6 and −52.2 LUFS,
  because the part's DI is about −30 dBFS for its first 0.6 s (inside the
  fresh-process mute) and about −81 dBFS after it. Only the Reset searched
  answer is unmeasurable.

## Synthesis

Audited checkout: `b0000e2` (main plus the starting-points write-up). Ten areas produced 74 findings:
- 46 were confirmed by independent verifiers, most with their severity lowered.
- 1 was refuted.
- 27 low-severity findings were not separately verified.

No finding flips a headline conclusion, and none is critical. Unless marked "(auditor only)", every number below was reproduced from raw data by at least one verifier. Scripts and outputs are under `scratchpad/audit/<area>/` and `scratchpad/audit/verify/<finding>-{reproduce,impact}/`.

---

## 1. Bottom line, result by result

### Result 1: with the part's own DI, the search ends closer than its start (~43/43). STANDS.
- **Counts:** 43/43 parts and 13/13 bands on SW50R, Tone King rhythm and PR12, with level and without it.
- **Significance:** the exact band sign-flip p is 0.00024, the smallest possible with 13 bands. LMM p ≤ 1.6e-9. It survives Holm correction.
- **Against the raw DI:** same-DI answers beat the unprocessed DI on 40–41/43.
- **Robustness:** it survives every loss correction tried (band restriction, common-dimension scoring, no ambience, no decay). On the 30 crops where the guitar plays most of the time it holds 30/30.
- **Caveat:** 13/43 set-2 crops are mostly silence (D-M6 below). Per-part numbers and mean distances are biased upward on those parts: same-DI median 0.517 against 0.438 on the active parts. The counts are unaffected.

### Result 2: same-take DI > another session's DI > noise probe > neutral. STANDS WITH CORRECTIONS.
- **same > other:** 43/43 on all three amps (PR12 42/43 without level), band-robust.
- **other > noise:**
  - With level: band-robust on all amps.
  - Without level: band-robust on SW50R and PR12 only. On Tone King it is 28/43 (band sign-flip p 0.053, LMM 0.078).
- **noise > neutral:** holds only on SW50R with level (33/43).
  - Without level it is 26/43, p 0.28. That p also depends on the AM-based "ambience" term: dropping the term gives Wilcoxon p 0.010, sign test 0.066.
  - On Tone King the order reverses. The noise search ends further than neutral on 38/43 with level and 29/43 without.
- **Correct statement:** same > other > {noise, neutral}, with noise worse than neutral on Tone King. The plan doc already words it this way; the brief's "roughly" hides it.

### Result 3: without a DI the search does not beat its start, and from a good template it makes things worse. STANDS WITH CORRECTIONS.
The headline is robust. Several sub-claims are not established, and it was measured with amp tracks as the reference, not songs.

**Robust under every test:**
- The shipped PR12 and AC20 templates, unchanged, beat their own no-DI search on 34/43 and 38/43 (band p ≤ 0.002 and 0.001).
- This survives Holm correction, both 5-s halves of the crops, all 6–12 sub-windows, and every loss variant.
- An independent aligned log-mel distance agrees in direction:

| Start | Independent metric | v3 | p |
|---|---|---|---|
| SW50R shipped | 39/43 | 25/43 | ≤ 1e-6 |
| AC20 shipped | 33/43 | 38/43 | ≤ 1e-6 |
| TK Default | 33/43 | 30/43 | ≤ 1e-6 |

**Every measured correction pushes the template-start comparisons further the same way:**
- Restricting `band_shape` to audible bands: SW50R template start-closer goes from 25 to 29/43 (p 0.004); AC20 neutral from 23 to 27–31/43.
- Scoring on shared dimensions only: all 8 match-pipeline flips move toward the start.
- Counting a level-less answer as a loss: TK Reset goes from 30 to 31/43.
- The Tone King start-up mute (D-M1) biases scores toward the no-DI answer, so the TK counts are conservative.

**Not established:** each of these loses significance once parts are clustered by band and Holm is applied, or flips between excerpt windows or loss variants.
- PR12 shipped as-is beats neutral searched: 27/43, p 0.024 at part level, but band p 0.19–0.32, and 23/43 on the second half of the crops.
- AC20 shipped as-is beats neutral as-is: band p 0.08–0.18.
- TK Default is harmed by the search: band p 0.026–0.12.
- SW50R "the tone moved away": seed 0 has the answer further on 28/43 (band p 0.07–0.12); seed 11 has it further on only 25/43.
- The per-amp "song-only start" winners: SW50R neutral searched, and none for Tone King.
  - The start rule names some winner 83% of the time even when all the options are identical. It was first written in the commit that recorded its results.
  - Under every corrected `band_shape` variant (11 of them) the SW50R winner becomes an as-is start (neutral in 9, shipped in 2) and the TK winner becomes Default as-is. All these choices are between options that are statistically tied.

**From neutral settings it is a tie whose sign depends on the loss:**
- Counts are SW50R 24/43, PR12 25/43, AC20 20/43.
- Dropping ambience moves SW50R noise-vs-neutral to p 0.010.
- Removing the spurious tremolo moves PR12 neutral-search to p 0.03–0.07.

**Scope:**
- Every number used the isolated amp track as the reference, on 10-s crops, with one seed per amp except SW50R.
- The "song-only" label overstates what was tested. The mix rung and excerpt selection never entered the benchmark (D-M8, D-M9).
- Seed-to-seed spread of searched answers is about 0.21 (log) per seed. The two SW50R seeds agree on 36/43 per-part verdicts.

**The shipped tool does not act on this result** (D-H1). Without a DI it writes the searched answer, prints a 38–74% "improvement" on 387/387 runs, and its fallback fired 0/430 times.

### Result 4: the level trim brings no-DI answers to about +4 LU, and the guitar check catches near-silent answers. STANDS WITH CORRECTIONS for the benchmark; AT RISK as a statement about the product.

**+3.7 LU is the trim's own error and is right as measured:**
- The trim sets the answer's level through a synthetic guitar. What remains is how much louder a real DI plays than the synthetic guitar, both rendered in stereo. Measured with no reference term this is +3.85 on SW50R; PR12 +4.67, AC20 +4.05, Tone King +2.3 to +3.4.
- The 3.01-LU offset between a mono crop and a stereo render (D-M4) does not change it. A consistently metered pipeline reproduces the figure: in a synthetic end-to-end run the search path was identical, with a gap of -0.63 stored against -0.39 consistent.
- The auditors' restatement ("+4 becomes +0.7") mixes two metering conventions and is wrong.

**What the 3.01-LU offset does change: the levels of untrimmed starts.**
- SW50R template: +0.85 LU becomes -2.16 (within ±3 LU drops from 27 to 18/43).
- Tone King neutral start: "+0.1 LU" becomes -2.9.
- Morgan neutral "19–36 LU too quiet" becomes 22–39.
- "The template played nearer the recording's loudness than the trimmed match on 27/43" becomes 23/43, a tie.
- A user's mono reference file is targeted 3 dB low.

**On a song, which is the product's input, the trim matches the whole mix's loudness (D-M2):**
- Real-plugin counterfactual over 43 SW50R parts: the preset plays a median +11.8 LU over the guitar's level in that song (IQR +7.9 to +15.0; 32/43 more than 8 LU over).
- Against the song's own loudness it is about +3.4 LU.
- So SKILL.md's "about 4 LU, a little loud" holds only if measured against the song. The code's caveat says this; the SKILL figure is unqualified.
- On a -9 LUFS master, the output through a DI is about -5 LUFS median. Peaks above 0 dBFS are estimated on most parts; this is a proxy, nothing was rendered.

**The guitar check catches near-silence only after the search has converged on it:**
- The root cause is in the loss (D-M3). A candidate below the -70 LUFS gate loses its level term and is renormalised, so near-silence scores better than an audible match.
- The SW50R neutral search on Hikikomori converged into that region.
- #100's guard flags it after the fact, and only for the no-DI arm. The DI and library arms run no guitar check.

### Result 5: E1 library probe. STANDS WITH CORRECTIONS for "library beats noise"; NOT SUPPORTED for "calculate only, skip the search" and for adopting the library on Tone King.

**Holds:**
- Within E1, the library inversion beats the noise inversion on SW50R 38/43 (37 without level) and Tone King 42/43 (33 without level). Band p ≤ 0.003.
- It holds for each source and on 12–13/13 bands.
- It holds with an other-source-only library (E1x): 40/43 and 42/43 with level, 38 and 37 without.
- On the synthetic chain, the probe's content drives the gain, not its input level: noise played at the library's level does no better.

**Overstated:**
- "Closer than the 300-render noise search on 31/43" (SW50R) is 27/43 with level left out (Wilcoxon 0.052, band sign-flip 0.06).
  - Half the with-level gap is the level dimension. The old noise answers were never trimmed and sit 8.1 LU off.
  - Against the trimmed shipped pipeline it is 27/43, band p 0.14–0.16.
  - Tone King, 38 becoming 30/43 (p 0.0005), holds.
- "Tied with the another-session-DI search":
  - SW50R inversion: closer on only 17/43, paired median ratio about +12%, CI about [1.00, 1.28]. It leans worse; it is not tied.
  - TK inversion: 20–21/43, ratio about 1.0, CI [0.86, 1.12]. Compatible with a tie but not shown equivalent.
  - The tie does hold for the library search (E2): +1.2% without level against the old other-DI search.

**Tone King:**
- "42/43 over noise" mostly shows how bad the noise probe is: the noise inversion is further than neutral on 39/43.
- Library inversion against neutral: 27/43 (p 0.20, 7/13 bands).
- E3 has finished. Library search against neutral on all 43 parts: 29/43 (67%) with level, 26/43 (60%, median -8.3%, p 0.22) without. It fails the ≥70% gate either way.
- Only a 20-part subset chosen after the fact and read with level passes. Batch 0 alone is 17/22; it is all Cambridge parts.

**SW50R and skipping the search:**
- E2 has finished. Library search against neutral: 42/43 with level, 40/43 without, 13/13 bands. It passes.
- Within E2 the search beats its own inversion on 26/43 (p 0.015), or 28/43 (p 0.005) without level. The gain is concentrated on Cambridge parts (-16%).
- So "calculate only and skip the search" is not supported on SW50R. On Tone King, neither the inversion nor the search clearly beats neutral without level: the search adds -3.3%, p 0.46.

**Untested:**
- L2, the library that could ship: the harness cannot run it, and Guitar-TECHS P1/P2 is not on disk.
- The probe level: fixed at -22.9 LUFS, which is the median of the very DIs it is scored through.
- Variation from which clips are drawn: about ±3 parts across redraws, synthetic chain only.

### Result 6: Tone King renders vary (~5 dB band noise), grid rounding, PACE. STANDS WITH CORRECTIONS.
- **Grid rounding is verified:** 360 plugin read-backs with 0 mismatches; 126/126 grid entries consistent with `to_stored`; record-state applies synchronously.
- **The band noise is overstated:**
  - "Up to 5.23 / 6.73 dB" are the maxima at 25 Hz and 40 Hz. Each is one FFT bin about 40 dB down, with all its spread in the first 0.5 s.
  - From 50 Hz to 16 kHz, repeats agree within 0.04–0.15 dB.
  - The real non-reproducibility is a deterministic start-up mute in every fresh TK process: exact zeros to about 0.41 s (Default) or 0.87 s (Reset, neutral). It is in all 258 committed TK pipeline scoring renders because `--preroll-s 0` is hardcoded (D-M1).
  - The manifest (5.228794) and `eq_basis.json` (4.38584) disagree.
- **PACE:** silence after a daemon kill was not re-tested (killing processes was prohibited), so it rests on NOTES.md.
  - A second silence mode exists: one reused Morgan instance went permanently silent mid-run with the daemon alive. This was a single event and its trigger was not isolated.
  - The renderer checks for silence only on the first render.
- **Morgan's "0.23 dB broadband" reused-instance noise is misdescribed:**
  - Back-to-back repeats are tighter than that: ≤ 0.05 dB.
  - The variation is deterministic and depends on the previous render and on being the first render of a process. It sits at 31–100 Hz (0.38–0.89 dB) and in the first second: the delay-time glide survives `reset()`.

### Result 7: the loss tracks what a listener hears. AT RISK (not established).
- **Listening evidence:** 4 parts were heard as different, and 2 of those answers were near-silent. On the one part heard as "no difference", the scorer predicted a difference automatically, because it calls a tie only within 1e-9.
- **An independent aligned log-mel metric** agrees with v3 on the order of a pair only at chance (52–53%) when |Δv3| < 0.25, and 65–73% for larger gaps. Result 3's aggregate directions hold under it.
- **Measured blind spots:**
  - `band_shape` takes 39–64% of its error from bands far below the guitar's peak.
  - "Ambience" is an envelope-modulation statistic. It missed the template's 420 ms delay on 43/43 parts, and a 30%-wet reverb scores about like a ±2 dB/decade tilt.
  - `attack_ms` cannot resolve attacks under 25 ms.
  - `decay` is unbounded on sparse crops.
  - The spatial term was never exercised by a benchmark but is live on stereo songs.

### Implications for the runs in progress
The `lib-shipped` runs (`benchmark_match_pipeline.py --arm library`, started from origin/main `c65a1cd`) inherit these defects:
- `--preroll-s 0`, so the Tone King scores carry the start-up mute and Hikikomori's TK score will again be invalid.
- The shipped tremolo, switched on for 27/43 Morgan parts. E2 held it off, so E2 and `lib-shipped` differ by more than the pipeline.
- No guitar check and no level trim. That is by design (compare without level), but it leaves the sub-gate level renormalisation unguarded. The library probe sits about 14 LU below the noise probe, so near-gate candidates are more likely; 133 noise-probe trials already sat within 6 LU of the gate.
- Mono-reference metering, so any with-level number carries the 3-LU convention.

E1–E3 are uncommitted. Write them up without level, on all 43 parts, with a band-robust test against neutral, and fix that analysis before citing per-part results.

---

## 2. Confirmed defects, ranked

Three root causes explain most per-part anomalies:
- **The crop rule (D-M6).** Ranking windows by gated loudness yields mostly silent crops. These cause the decay slivers and LRA outliers, and they are why Hikikomori and Prodigal ElecGtr2 keep showing up as worst cases.
- **Level handling: five separate defects.**
  - Sub-gate renormalisation (D-M3).
  - Mono vs stereo metering (D-M4).
  - The mix-loudness trim target (D-M2).
  - With-level gate reporting (D-H2).
  - Untrimmed answers used as cross-run comparators (D-H2).
- **The Tone King fresh-process mute (D-M1).**

### High

**D-H1. Without a DI, the shipped match writes a preset worse than its start and prints an improvement** (product-4)
- **Wrong:**
  - The "nothing beat the preset you started from" check compares scores made through the noise probe, and the template always loses there. So the check never fires.
  - The printed "distance to the reference A → B" is a noise-probe distance.
  - SKILL step 5 writes match-1.
- **Evidence, real plugin:**
  - The printed distance fell on 387/387 runs (median -38% to -67%). Fallback fired 0/430 times.
  - The printed drop barely tracks the true change (Spearman -0.14 to +0.38).
  - match-1 ended further from the recording than the unsearched template on: SW50R 25/43 (seed 11, +8%) and 28/43 (seed 0, +17%); PR12 34/43 (+40%); AC20 38/43 (+41%); TK 28–30/43.
  - `report.html` headlines "67% closer".
- **Changes:** what the product delivers, not result 3, which it confirms.
  - Delivering the template with only its output level set through the synthetic guitar (modelled trim) is closer than match-1 on SW50R 26/43 (p 0.19) and 30/43 (p 0.017), PR12 36/43, AC20 38/43, and TK 31–35/43.
  - From neutral starts that fix is worse (16–20/43).
  - On the synthetic chain the harm comes mostly from the inversion: the inverted seed is already worse than the template on 11/12. The search makes its own seed worse on only 3–5/12. So skipping the search alone is not the fix.
- **Fix:**
  - Without a DI, deliver the template plus the calculated level only, from a real preset.
  - Relabel the headline as a noise-probe distance.
  - Have step 5 write the template variant unless the user picks the searched one by ear.
  - Measure on the plugin before adopting (§5, gap 2).

**D-H2. E1–E3 are reported with level, cross-run and post hoc; result 5 is stated more strongly than the evidence** (stats-1, -2, -3, -7, harness-4, numbers-2, e1-1, e1-2)
- **Wrong:**
  - In search mode the harness prints and stores only the with-level `against_neutral` count (`match/signal_benchmark.py:402-405`, `scripts/benchmark_recordings.py:439`). The plan's ground rule (`docs/research-song-only-matching.md:194`) says level left out.
  - The headline cross-run comparisons break the plan's own "every comparison stays within one run".
  - No 20-part draw was committed.
  - The design departed from the pre-registered one: L1 instead of L2; library only; 43 parts instead of 20; E3 batches split by source.
- **Evidence:**
  - On Morgan, level adds 5–9 parts out of 43 to every arm's count against neutral, because neutral plays a median 19 LU quiet.
  - The already-rejected noise search passes E2's count gate (≥ 15/20) on 73–77% of 20-part draws with level, 3–7% without.
  - The E1, E2 and E3 figures are as in result 5 above.
- **Changes:**
  - Correctly analysed, E2 passes and E3 fails. No conclusion flips.
  - A with-level reading of a favourable subset would wrongly pass Tone King.
  - "Skip the search" and "tied with other-DI" are not supported on SW50R.
- **Fix:**
  - Have search mode print no-level counts.
  - Decide on all 43 parts, without level, band-robust, against neutral, and record that analysis before reading per-part results.
  - Use within-run comparisons only.

**D-H3. The main timbre term is dominated by spectral extremes** (loss-3)
- **Wrong:** `band_shape` (`analysis/compare.py:143-155`) is the RMS of the mean-removed band difference over all 30 third-octave bands, 25 Hz–20 kHz. It has no floor relative to the peak. `spectral_tilt` in the same codebase deliberately limits itself to 50 Hz–10 kHz and to bands within 40 dB of the peak.
- **Evidence:**
  - Over 774 committed renders (stored v3 reproduced exactly), a median 64% of `band_shape`'s squared error comes from bands more than 30 dB below the reference peak; 39–48% under a hearing-threshold model that ignores masking.
  - `band_shape` is about 31% of the no-level scalar and the largest timbre term on 75% of renders.
  - Ranking of renders with all bands vs within 30 dB of the peak: ρ = 0.55 for `band_shape` alone, 0.97 for the full distance.
- **Changes:**
  - Distances of unchanged starts are inflated 10–28%, against 6–14% for searched answers. That favours the search in every search-vs-start comparison.
  - Corrected, result 3 strengthens (numbers in §1).
  - The SW50R and Tone King start-rule winners change in all 11 variants, but only among tied options. PR12 and AC20 are unchanged.
  - The claim that this explains the Morgan neutral spread is not supported. The spread follows the dynamics term (ρ 0.73 and 0.88), and -120 dBFS noise moves quiet renders by 3–7%, not 10%.
- **Fix:**
  - Limit `band_shape`, and the inversion's band targets, to bands within 30–40 dB of the target's peak, or to 50 Hz–10 kHz.
  - Re-run the start-rule comparison.

### Medium

**D-M1. Every fresh Tone King process starts with a mute** (renderer-1, data-2, renderer-2)
- **Evidence:**
  - Controlled launches: the first render after process start is exact zeros to 0.32–0.39 s, then 4–45 dB low until about 1 s, then identical to later renders.
  - In all 258 committed TK pipeline renders the output starts late. First non-zero sample: median 0.41 s, range 0.08–0.65 s.
  - Reset and neutral renders have a second zero run that ends near 0.87 s. Morgan renders start within 13 ms.
  - `scripts/benchmark_match_pipeline.py:147-150` passes `--preroll-s 0`, and origin/main still does.
- **Changes:**
  - Per part, held-content tests give median shifts of about 0.01 (template) and 0.05–0.07 (answer), with up to 1–2 on single parts.
  - 2–9 of 43 verdicts flip per run, net toward the no-DI answer.
  - Start-win counts with the first 1 s cut from both sides: 27/30/30 against 30/30/28 stored. The ties between starts are unchanged. LUFS moves by about 0.04 LU.
  - **Hikikomori:** 99.98% of its DI crop's energy lies in the first 0.6 s, so the TK Reset and neutral renders are all zeros.
    - "Unmeasurable" is counted as a search win (1.66 against 2.81).
    - The plan's sentence "this part's DI plays nearly silent … AC20 neutral -55" misattributes it: -55 LUFS is the norm for AC20 neutral (median -54.6).
  - The band-noise figures should be restated (result 6).
- **Fix:**
  - `--preroll-s ≥ 1.5` for TK scoring renders.
  - Assert that the opening 50 ms is not exact zeros when the DI plays there.
  - Re-score the three TK pipeline JSONs.
  - Report band noise over 50 Hz–16 kHz, and reconcile the manifest with `eq_basis.json`.

**D-M2. On a song, the no-DI trim targets the whole mix's loudness** (product-3)
- **Evidence:** `match_preset.py:563-565` targets the reference excerpt's integrated loudness.
  - Mix minus amp-track LUFS on development crops: median +7.1 (57 parts) or +8.3 (set 2).
  - Real-plugin counterfactual (outputGain is linear: 414 of 429 trims within 0.5 dB): +11.8 LU over the guitar, +3.4 over the song.
  - Synthetic end-to-end runs track the shift part by part.
  - The answer plays a median 9.8 dB louder than the template the user started from (benchmark case: 2.2).
- **Changes:** result 4 as a product statement, and SKILL.md's level guidance. No tone result changes.
- **Fix:**
  - For `mix` references, target the song's LUFS minus a development-set song-to-guitar gap. A leave-one-session-out median brings the result back to +4.1 LU.
  - Separated stems arguably keep the current target.
  - Qualify the SKILL figure.

**D-M3. A candidate under the -70 LUFS gate loses its level term** (loss-1, numbers-1, harness-3)
- **Wrong:** `compare.scalar` renormalises over the dimensions it could measure. When the target is measurable and the candidate is not, `level` disappears.
  - This contradicts the module's own promise: "nothing here silently scores an unmeasured dimension as perfect".
  - Unmeasurable renders are also fingerprinted without normalisation, which biases their distance down by 0.15–0.55.
- **Evidence:**
  - A turned-down copy of the reference scores 1.07 at -50 dB but 0.025–0.06 at -55 to -70 dB. On 37/43 parts, -60 dB scores better than -40 dB.
  - The SW50R neutral-s11 Hikikomori search converged there: 49 of 289 trials had no level term, including all 3 shortlisted. An honest level term would put them at ≥ 2.09 against the best audible trial's 1.42.
  - Overall: 198 of 116,230 trials, and 2 of about 390 shortlists.
- **Changes:**
  - SW50R neutral searched vs own start: 24/43 (p 0.31) becomes 23/43.
  - Tone King Reset start wins: 30 becomes 31/43 (p 0.13 becomes 0.04–0.06).
  - First-set Tone King other < noise: 13/14 becomes 12/14 (p 0.013 becomes 0.017–0.03); this one is not disclosed in the docs.
  - None occurred in E1, E2 or E3.
- **Fix:**
  - When the target has a loudness and the candidate does not, impute a level of at least (target_lufs + 70)/3, or reject the trial.
  - Count unmeasurable answers as failures in the summaries.

**D-M4. Mono reference crops are metered against stereo renders** (features-1, loss-2, harness-1)
- **Evidence:**
  - Identical audio reads +3.01 LU, gets a level term of 1.003 (v3 0.073), and `output_level` asks for -3.01 dB.
  - BS.1770 sums channel power. The repo never chooses a 1-vs-2-channel convention, and the `io.py` docstring warns against comparing across channel counts.
- **Changes:**
  - Levels of untrimmed starts, and the "template nearer than trimmed match" counts (numbers in §1, result 4).
  - Trimmed and inverted answers, and every no-level result, are unchanged.
  - E1's with-level counts are unchanged under a consistent fix (bound: ≤ 2 pairs per amp).
- **Fix:**
  - Promote a mono reference to dual-mono: exact for every render. Folding renders to mono would move decorrelated ones by 1–7 dB.
  - Change the target and the meter together, in `match_preset`, `invert`, `search` and the benchmark at once.
  - Add a test that `fingerprint(x).lufs_i == fingerprint([x,x]).lufs_i`.
  - Restate only the untrimmed figures.

**D-M5. Pairwise and start-rule claims are reported at part level, single seed, post hoc** (stats-4, -5, -8, -9)
- **Evidence:**
  - Band ICC is about 0.33 on three of the claims (about 20 effective parts out of 43).
  - At those ICCs a part-level Wilcoxon has a 13–25% false-positive rate (simulated with the real band sizes).
  - After band clustering and Holm, 2–3 of the doc's 11 stated wins survive (4–6 if clustering by session). The survivors common to every test are PR12 and AC20 shipped as-is beating their own search.
  - The start rule names a winner 69–84% of the time under the null.
  - Seed SD is about 0.21 (log) per answer.
  - 5-s halves flip per-part verdicts on 14 of 43 parts, but those halves are silent. On parts that play in both halves, agreement is 72–97% and counts move by ≤ 5/29.
- **Changes:** the sub-claims listed under result 3. No decision changes.
- **Fix:**
  - Report band-level p (a sign-flip over bands keeps the doc's statistic).
  - Apply Holm within each family.
  - Pre-register the start rule.
  - Run a second seed before acting on Tone King's 28–30/43.

**D-M6. The excerpt rule ("loudest 10 s, gated loudness") picks mostly silent crops** (data-1)
- **Evidence:**
  - 13/43 set-2 crops have the part playing under 50% of the time; 9 have it at most 24%.
  - On 9 Cambridge parts the remainder is digital zeros. On 4 Telefunken parts it is band bleed or decay, which carries 0.27–1.68 of distance that no render through the DI can remove.
  - Low-activity parts score worse: same-DI median 0.517 against 0.438 (p 0.013); PR12 other-DI 1.50 against 0.81 (p 0.001).
  - The match tool's own `excerpt_selection` ranks windows by activity; the validation rule overrides it.
- **Changes:** per-part readings and means. No headline count changes on the 30 active parts.
- **Fix:**
  - Rank by ungated loudness (42/43 crops then play at least half the time), or require ≥ 90% activity.
  - Re-declare the rule before re-cutting: every crop hash will change.

**D-M7. The no-DI inversion switches on a tremolo from ordinary playing** (search-1, harness-2, search-8)
- **Evidence:** the 0.75 confidence gate is the only test for recordings.
  - It fires on 16/43 dry DIs (19/43 at the default 20-s excerpt) and on 12/30 synthetic strums that contain no tremolo.
  - On amp tracks it fires 27/43. About 4 of those, the LFTL "GTR 1" parts at 2.6 Hz, show a real modulation line, so about 23/43 are false. On mixes it fires 6/43, 5 of them false.
  - It is present in all six Morgan match-pipeline runs (27/43 answers). The recordings benchmark, E1 and E2 hold it off. Tone King has no tremolo controls.
  - In rendered answers the false tremolo is measurable on only 0–2 of 23 parts per run, though a few are clearly present (about 4.5 dB at 66–69% depth).
  - With the tremolo on, reused-instance noise rises (start spread 0.010 against 0.002).
  - `tremoloRate` moves in 1 Hz steps.
- **Changes:** results 3 and 4 change by at most 1 part and 0.1 LU. The product writes a spurious effect into about half of stem matches and about 12% of mix matches. SKILL's fresh-process rule does not cover it.
- **Fix:**
  - For recordings, leave the tremolo as the template has it, as the reverb rule already does, and offer `--enumerate`.
  - Use a finer rate quantum.
  - Correct the docstring and SKILL.

**D-M8. The mix regime is ignored by the inversion and the loss** (product-2)
- **Evidence:**
  - The regime label changes nothing: values are identical on 57/57 parts.
  - On mixes the 65 Hz band is set to +12 dB on 40/57 parts (0/57 from the amp track). Searched answers keep about +9 to +10 dB there.
  - Against the amp-track pipeline, the mix answer ends 8–13% further (2 seeds; Wilcoxon p 0.03, sign test 0.15).
  - A 250 Hz–4 kHz restriction improves mix inversions by 10–15%, but improves amp-track inversions about as much.
- **Changes:** product only. It contradicts reading-a-reference.md's "never take amp bass from a mix".
- **Fix:** ignore bands below 250 Hz, at least, for `mix` and `separated_stem`, in `band_delta` and in the timbre loss. Test the same restriction for every no-DI inversion.

**D-M9. On a full song the default 20-s window lands on the intro** (product-1)
- **Evidence:**
  - Over 27 real development songs, 14–16 of 49 parts are silent in the chosen window.
  - `activity_tie` fires on every real song.
  - The "does not look like a guitar" caveat fires on about half of windows either way.
- **Changes:** the product only. Measured harm is small:
  - On the searched answer, -0.018 median over 21 mis-windowed parts, inside seed noise of 0.27.
  - On the calculated start, +0.09 (worse on 14/21).
  - The auditor's +56% on Quicksand was scored in-sample. Out of sample the Quicksand cost was +16%, and Today's The Day came out 7% better.
- **Fix:** ask the user for a timestamp, or rank windows by a guitar-band feature. Treat `activity_tie` on a mix as an unknown window.

**D-M10. "Ambience" is an envelope-modulation statistic** (loss-5, search-2)
- **Evidence:**
  - 592 of 621 present ambience values come entirely from `am_*` terms.
  - The delay detector missed the template's 420 ms delay on 43/43 parts and added echoes on 40–41/43.
  - `am_rate` is uncapped and steps between envelope harmonics (+8.9 on one HPF step).
  - In no-DI searches it acts mostly as a constant offset: median 4% of the score, and more than half of the improvement in only 10/391 searches.
- **Changes:** the SW50R noise-vs-neutral p (result 2). The plan's line "delay … keep their own ambience terms" is wrong.
- **Fix:**
  - Correct the doc.
  - Cap or drop `am_rate`.
  - Validate a time-effect measure before claiming the loss sees delay or reverb.

**D-M11. The decay estimator is unstable and its term unbounded** (features-2, loss-6)
- **Evidence:**
  - Sub-hop shifts move decay by up to 209 dB/s on reference crops.
  - 54–75 ms segments at the end of the crop give -400 to -1014 dB/s, and terms up to 166.5. A synthetic -15 dB/s note reads -359.
  - Every E1 dynamics outlier above 4.5 is Prodigal ElecGtr2.
- **Changes:** counts move by ≤ 1 per comparison.
- **Fix:**
  - Drop segments truncated by the end of the crop.
  - Require at least 3 slopes.
  - Fit a fixed -5 to -25 dB window, and cap the term.

**D-M12. Renormalising over whichever terms are present** (loss-4, harness-7)
- **Evidence:**
  - The two sides of a pair have different dimension sets on 1–12 of 43 pairs. A near-zero ambience term lowers a total by up to 24%; a large one raises it without bound.
  - Recomputing on shared dimensions flips 0–2 pairs per comparison, and all 8 match-pipeline flips favour the start.
  - Totals averaged over replicates disagree with the scalar of the averaged dimensions by up to 0.275 to 0.39 on Tone King.
- **Fix:** compare candidates only on the terms measured for the target and for both of them, and store each observation's no-level total.

**D-M13. Morgan reused-instance variation depends on history** (renderer-4)
- **Evidence:**
  - The first render of a process and renders after a different setting carry deterministic offsets of 0.38–0.89 dB at 31–100 Hz, and up to 3.5 dB in specific 0.25-s windows.
  - The delay-time glide survives `reset()`, proved with an independent render pair.
  - Effect on v3 is about 0.01–0.03 per render.
  - The E1 SW50R neutral spread (median 0.099) is not explained by these mechanisms, since that neutral has compressor, delay and reverb off.
- **Fix:** use the server's existing warm-up option, and update the doc's "broadband, not tonal" description.

**D-M14. E1 ran only L1; the plan's gates are written for L2** (e1-3)
- **Evidence:**
  - The harness has no file or directory signal.
  - Guitar-TECHS P1/P2 is not on disk.
  - `LIBRARY_LUFS` is hard-coded at -22.9.
  - E1x removes the worry that L1 wins only by sharing a dataset with the target.
- **Fix:** add the file or directory signal, download P1/P2 with the user's approval, and sweep the probe level in `--no-search` mode.

**D-M15. The "does not look like a guitar" caveat fires on real guitars** (product-6)
- **Evidence:**
  - It fires on 15/57 isolated amp tracks; the extent rule accounts for 14 of them.
  - The same rig trips it on 5/8 Guitar-TECHS excerpts.
  - The docstring claims "well below anything a guitar produces". The calibration rests on one track and the test on band-limited noise.
- **Fix:** recalibrate on the 57 amp tracks, and correct the docstring, both skills and reading-a-reference.md.

**D-M16. The spatial term is never exercised by a benchmark but is live on stereo songs** (features-3)
- **Evidence:**
  - Against a stereo master, a dual-mono candidate picks up 0.075 of distance (about 3.3% of the scalar). The term moves 0.15–0.2 between template and answer.
  - Dropping it reverses template vs answer on 3–6/43 parts.
  - No-DI searches from shipped templates already widen the stereo image on about 90% of parts with no width objective.
  - "Never exercised" is too strong: the plugin-rendered search-signal benchmarks do score it.
- **Fix:** drop it for `mix` and `separated_stem`, or add a stereo-reference arm.

**D-M17. `--enumerate` never searches the controls its switch turns on** (search-3)
- **Evidence:** the screen runs once, on the seed.
  - In a known-answer delay test the answer stayed at 0.4997. It would have reached 0.085 with the target's delay values.
  - With `selectedAmp` enumerated, the other amps get no amp or EQ search.
- **Changes:** opt-in only; no benchmark uses it.
- **Fix:** screen each variant's own active controls, and correct the `--help` text and SKILL.

**D-M18. The screen's premise is false** (search-4)
- **Evidence:**
  - A movement taken only at the two range ends cannot see an interior optimum. In known-answer sweeps it froze the only wrong control in 34/96 cases.
  - The report sentence "cannot matter at any setting in between" is false.
  - So is "a larger budget would search the frozen 25%": the cut is a fixed quantile.
- **Changes:** no end-to-end harm shown at budget 300. CMA-ES did not fix those controls even when they were searched.
- **Fix:** add a midpoint probe and correct the text.

### Low (verified)
- **loss-7, calibration:**
  - The raw DI scores closer to the amp track than most no-DI answers under v3 and under the independent metric alike. That confirms result 3 rather than showing v3 is miscalibrated.
  - The half-vs-half floor (0.71) is inflated by halves that are silent; it is 0.54 where both halves play.
  - The impact text "prefers no amplifier to most matched presets" is wrong for real matches: same-take answers beat the raw DI on 40–41/43.
- **renderer-3:** one reused Morgan instance died mid-run. Both guards are cause-agnostic and catch it. The remaining gap: a DI-mode match never checks mid-search for a dead instance.
- **e1-4:** the clip draw moves per-part inversion scores by about 15% and counts by ±3. E1's draw was the least favourable of the six tried.
- **e1-5 / stats-11:** Tone King reruns re-picked the "other" DI on 26/43 parts. Disclosed in the docs; no measurable effect.
- **product-5:** SKILL step 3 asks song-only users for a DI, and every no-DI run's caveats tell them to get one (first in the list on 21/24 runs, present on 24/24). The step-6 audition refuses a no-DI run in all 4 ways tried.
- **product-7:** "song-only" section labels describe amp-track runs. The research plan already says so.

### Low (auditor only, not separately verified)
- **data-3:** Zeno ElecGtr8 and ElecGtr9 are sample-identical, so one guitar is doubled in the Signs mix (+1.37 dB on one backing crop).
- **data-4:** the in-step pairing test depends on the estimator; 2 usable parts flip under an equally valid one. Both are aligned by GCC.
- **data-5:** crop file hashes are not byte-reproducible (libsndfile writes a PEAK timestamp); the samples are identical.
- **data-6:** "another band's DI" comes from the same source on 23/27 of the other-band pairings.
- **features-4:** `attack_ms` cannot resolve attacks under 25 ms and is not monotonic.
- **features-5:** LRA is gated on the arithmetic mean of block loudness, not the power mean EBU specifies. Verdicts move by ±1.
- **features-6:** the pitch tracker locks to its 1200 Hz boundary on low sines and chords with high confidence. Harmonic weight is 0 in v3, but `benchmark_recordings` defaults to unpaired-v2.
- **renderer-5:** plugin latency is 52 samples (Morgan) and 51 (Tone King), not 0 as the doc says.
- **renderer-6:** `_renderer_build` does not hash `format/`, the loader, the manifests or the Swift flags, so the cache would not notice changes to them.
- **search-5:** "same random numbers" gives no pairing, because each arm searches a different list of controls.
- **search-6:** winner's curse in the shortlist's reference score: the first render is lower in 229/344 groups; median bias -0.0004.
- **search-7:** level is inverted before the EQ, leaving a 3–4 dB level error when both are wrong.
- **search-9:** clip repair does worse than a penalty when the optimum lies outside the box; a design note.
- **harness-5:** the pipeline benchmark scores a match-1 that every candidate failed the guitar check on. A Hikikomori rerun would hit this.
- **harness-6:** a `--part` subset changes which "other" DI a part gets, outside library mode.
- **numbers-3:** the Tone King same-band split groups by artist; by catalog group it is 10 parts, 1.22 against 1.20.
- **numbers-4:** "a mean 0.4% further" is a mean of per-part ratios; the ratio of means is 6.3% closer.
- **numbers-5:** "12 artists" should be 7.
- **numbers-6:** the printed command differs from the recorded one; "-14.2" should be -14.25; the Hotel run also records a scratchpad path; the PR12 run called "uncommitted" is committed.
- **stats-10:** the result-2 wording (covered under result 2).
- **e1-6:** the research doc's motivating medians are without level but not labelled so.
- **product-8:** `summary.json` drops the ±6 dB fields for trimmed candidates (69/72).
- **product-9:** `fingerprint.py` defaults to the `probe` regime and so skips the guitar caveat; skill examples use `synthetic` or `separated_stem`; installing.md shows `--strip-irs`.
- **product-10:** a host-set `CLAUDE_PLUGIN_DATA` would silently override `~/ndsp-presets`. Not shown to happen.

---

## 3. Disputed items and what would settle each

1. **What the 3.01-LU offset does to result 4.**
   - Auditors (features-1, loss-2, harness-1): "+4 becomes +0.7".
   - All four verifiers: the trimmed gap is convention-independent. They showed it by derivation, by the linear-gain check (median deviation 0.00–0.11 dB) and by a synthetic end-to-end run with mono and dual-mono references.
   - Verdict: the verifiers are right.
   - Open: which playback convention defines "the recording's level" (a 0 dB or -3 dB pan law) is a choice, not a measurement. Settle by choosing one and adding the invariance test.
2. **Tone King mute: length and reach.**
   - Auditors said 0.4 s and 0.75–1 s. Verifiers found both: about 0.41 s on Default, and a second zero run to about 0.87 s on Reset and neutral.
   - Disputed: whether the first render of each reused process (recordings benchmark, E1) is muted. One verifier found E1's large neutral spreads do not line up with first-of-worker targets.
   - Settle with one TK launch: render the Hikikomori DI and a second DI crop with `--preroll-s 0`, 1 and 2, plus first-vs-second render in one reused instance. About 10 renders.
3. **`band_shape` severity and the noise attribution.**
   - One verifier rated it high, one medium. Settled as high, because it biases every search-vs-start comparison and changes two per-amp winners.
   - The noise mechanism is disputed: -120 dBFS noise moved quiet renders 7% (auditor) or 3.4% (verifier), and the stored neutral spread follows the dynamics term.
   - Settle: 3–5 repeated fresh renders of SW50R neutral on 10 parts, with the spread split by term.
4. **SW50R and Tone King start choice.** Statistically a tie under every metric. Settle with a pre-registered rule, the corrected `band_shape`, and a second seed.
5. **Full-song window cost (product-1).**
   - Auditor: +56% and 14 LU. Impact verifier, 26 parts: searched-answer change within seed noise; level closer with the intro window on 24/26.
   - Settled for the synthetic chain. Open on the plugin with real masters (gap 3).
6. **Song vs amp-track reference distance (product-7).** The song reference ended further on 9/12 in one run and 2/8 in another; pooled 11/20, a coin flip. Settle with an E4 mix rung on the plugin.
7. **Where the no-DI harm comes from on the plugin (product-4).**
   - Synthetic chain: mostly the inversion.
   - Real plugin from neutral (E1): the noise inversion is closer than neutral on only 12–22/43.
   - Settle: plugin renders through the DI of template / template + level only / template + inversion with no search / answer, for PR12 and AC20.
8. **Audibility of the false tremolo.** Measured modulation is 0.36–0.89 of a linear tremolo at the same depth, usually within noise. Settle by blind listening on the 5 deepest cases and the 4 LFTL parts that look real.
9. **stats-6 (library gain comes from Telefunken targets sharing a source): REFUTED.**
   - The other-source library (E1x) keeps the Telefunken advantage: 17/20, -43%.
   - The noise probe, which shares nothing, shows the same split.
   - Library-vs-noise shows no difference by source (p 0.44). The split is a property of the targets.
10. **"2 of 17 survive" (stats-4).**
    - Depends on how the family and the cluster unit are drawn: 2–3 of the doc's 11 stated wins at band level, 4–6 at session level.
    - Survivors under every choice: PR12 and AC20 shipped as-is beating their own search. Band is the defensible unit, since the split was drawn by band.
11. **"The search adds about 15% on Tone King" (e1-1).**
    - That came from batch 0 alone.
    - On all 43 parts: median -8.3% with level (p 0.052), -3.3% without (p 0.46).
12. **"Nearly blind to reverb" (loss-5).** Overstated: reverb registers roughly in proportion to its wet mix. Delay is the real blind spot.
13. **"The guards blame PACE" (renderer-3).** Wrong: both guard messages are cause-agnostic.
14. **harness-2 scope.** Only Morgan (E1-SW50R, E2) is affected. On stems the tremolo decision does not depend on the probe, so E1's library-vs-noise comparison is unaffected.
15. **Side observation (features-3 verifier): the Fragments session's master file is named "Bloomlight_RR Master_100623_01.wav".**
    - I checked it: its duration (403.33 s) matches the Fragments stems exactly, not Bloomlight's (311.69 s).
    - So it is the Fragments master with a misleading source name, not a catalog error.

---

## 4. Verified correct: the ground-truth inventory

**Data and catalog**
- Crops on disk match their `record.json` and every result JSON's hashes: 43 crops × 6 roles; 10 pipeline JSONs, 6 recordings JSONs and E1. The catalog SHA is consistent throughout.
- Crops are sample-exact from the declared rules (256/256).
- Catalog development entries reproduce from the audio with 0 differences (26 set-2 and 11 set-1 sessions).
- Whole-length pairing is reproduced by an independent implementation (≤ 0.001), and known-answer pairing tests pass.
- Each crop's reference is the same take as its DI. Coherence and onset tests beat every other part's reference on 43/43.
- DI and reference are aligned with constant offsets. The lag is not applied, and the residual weight is 0.
- The set-1 and set-2 splits reproduce from their seeds. No held-out material leaks into development lists, "other" choices or `library_from`.
- E1 library probes rebuild exactly: SHA 86/86. Each has 4 distinct bands, never the part's own or the other-DI's band.
- The catalog counts in `validation-datasets.md` recount correctly.
- No sample-level duplicate exists across sessions.

**Features**
- #99's batched periodicity matches the old tracker over 223,814 frames (max difference 1.3e-14), and 169 fingerprints are identical.
- Integrated loudness equals pyloudnorm exactly. The 44.1 kHz path is within 0.008 LU. `normalise(measured=)` is bit-identical to the unmeasured path.
- These give the known answers: bands, tilt, centroid, rolloff, flatness, crest, spatial, and decay, RT60, delay and tremolo on clean signals. MFCCs match an independent implementation to 5.8e-13.
- Timbre is gain-invariant down to -35 dB. Channel layout changes only the level term.
- Rate, length and channels are consistent between crops and renders (780/780). Benchmarks use the same excerpt on both sides.
- Stored scores reproduce from the stored WAVs exactly.
- Alignment recovers integer and fractional offsets and polarity.
- 92 targeted tests pass.

**Loss**
- `scalar()` implements the documented formula (to 8.9e-16 over every v2 and v3 JSON). No prior or complexity term enters any score against a recording.
- All 774 committed match-pipeline renders re-score to the stored values (max difference 0), and the bench JSONs are byte-equal to the `docs/` copies.
- Identity scores 0 and the distance is symmetric. Medians rise monotonically for lowpass, high-pass, drive and tilt.
- Replicate noise within an instance is small against paired effects: at most 4/43 pairs fall within 2 SE.
- The Tone King run1/rerun merge excludes the silent-plugin rows.

**Renderer**
- Morgan fresh-process renders are bit-exact across processes.
- XML round-trips retain values (296/300 exact; 4 rounded to 0.1 Hz). Preset-file encoding equals the live state encoding (130/130).
- Omitted controls are always inactive ones. Search-path and scoring-path TK renders are equivalent.
- TK grid rounding: 360 writes, 0 mismatches. No searched control is silently ignored: SW50R 42/43 continuous controls, TK 14/14 sampled.
- Search winner → `match-1.json` → preset → scored preset is consistent (172/172).
- The cached Swift build is byte-identical to a fresh compile.
- Input is unscaled. The silence thresholds separate dead output from live output. E1 margins exceed replicate spread.
- AC20's history dependence did not reproduce, so the fresh-process policy is conservative either way.

**Search and inversion**
- CMA-ES matches an independent implementation of Hansen's tutorial in lockstep (to 3.3e-15), and its mean stays in the box.
- Render accounting is exact; the CLI's overspend beyond the budget is disclosed.
- The inversion renders through the search's own signal.
- Level-only inversion is exact, and a clamp is reported. The EQ inversion is within a couple of dB when the level is right.
- Switches are held unless enumerated, and the enumerate budget split is correct.
- Tone King search values land on the plugin grid.
- Guitar-check reordering and numbering, `pareto` putting the lowest total first, and pool = sequential rendering all hold.
- With the same DI, the search improves 9/9 synthetic targets. The noise-probe failure mode matches the docs.
- The initial step size is not sensitive. The ±6 dB re-rank is not systematically worse.

**Harness**
- Every answer, inversion and neutral is scored through the part's own DI (traced: 0 exceptions).
- Arms get the same RNG state, budget and settings. The neutral start is identical across arms and equals `docs/neutral-*-spec.json`.
- `library_probe` behaves as documented. `other_di_index` and `pool_others` reproduce E1.
- Summary and inversion-pair arithmetic recompute exactly for 6 recordings JSONs, both E1 JSONs and 10 pipeline JSONs.
- Committed JSONs have 0 failed or unmeasurable outcomes; failures drop symmetrically.
- 172 trial stores (51,095 trials) contain no silent or errored trials.
- The pipeline benchmark really runs the shipped no-DI path. Its silent-plugin set-aside, resume and policy refusal work.
- Drift between E1 and the older runs is small: neutral differs by a median 1.5% (SW50R) and 0.2% (TK).

**Numbers versus prose**
Every checkable number reproduces from the committed JSONs, apart from numbers-1 to -6 and e1-6. That covers:
- "Matching without a DI — measured"
- the synthetic-guitar section
- the TK search-signal section
- SW50R -v2
- the set-2 recordings tables (SW50R, TK, PR12)
- the shipped match and no-DI starting-point tables
- the first-set table
- `skills/match/SKILL.md`
- the research doc and the round-2 plan

Recorded source commits exist and the elapsed times match.

**Statistics**
- The band-robust tests are calibrated for these cluster sizes: sign-flip 0.045–0.056, LMM 0.027–0.057.
- The level-left-out metric predates the set-2 data (#60, 2026-09-24).
- The development/held-out split was fixed before any result.
- No hidden alternative analyses were found in the TK start logs.
- Fresh-process scoring renders are deterministic: the template scored identically on 43/43 across seeds.

**E1**
- Every count, median and p reproduces.
- Results are robust to dimension-set mismatch and to observation noise.
- Noise and library go through one code path; only their loudness differs.
- The clips are exactly the loudest 1.5 s (172/172).
- The -22.9 LUFS level is circular by at most 0.2 dB.
- No target overlaps its library (max cross-correlation 0.23), and no recording-chain signature appears within a dataset.

**Product path (synthetic renderer)**
- Every `summary.json` field the skill names exists, except the trimmed-candidate ±6 dB fields (product-8).
- An explicit `--excerpt-start` is honoured, or clamped with a caveat.
- The trim lands on its target within ±0.12 dB, and the guitar-check tests pass (17).
- Probes are deterministic: guitar -24.00 LUFS, noise -8.45 LUFS.
- MP3 and 44.1 kHz input load consistently.
- The data root resolves correctly for an installed copy and for a clone.
- On amp tracks the synthetic replica reproduces the direction of results 3 and 4.

---

## 5. Gaps: what nobody covered, and the cheapest test for each

1. **The TK mute fix, and first renders in reused processes.** One TK launch: about 10 renders with `--preroll-s` 0, 1 and 2, plus first-vs-second render in one instance. Do this before re-scoring the TK JSONs or reading the `lib-tk-default` run.
2. **Plugin attribution of the no-DI harm (D-H1).** PR12 and AC20, 43 parts each: render the template, the template with level only, and the template with the full inversion but no search, through each DI in a fresh process. That is about 260 renders and no search. It decides the product fix.
3. **Real songs.** No full commercial stereo master is on disk; full songs were stem sums.
   - E4 mix rung on the plugin: 12–20 parts with the song as reference, with and without the band restriction and with a timestamped window.
   - Include one stereo master to exercise the spatial term and the mix-loudness trim.
4. **Listening on mid-range pairs.** 10–15 blind R-A-B pairs with |Δv3| between 0.1 and 0.5, built from existing renders (template against answer on PR12 and AC20). No new renders needed.
5. **L2 and probe level.** Add a file or directory signal; P1/P2 needs the user's approval to download. Then run `--no-search` at -30, -22.9 and -15 LUFS: inversion only, about 4 renders per part.
6. **Clip-draw variance on the plugin.** 2–3 library realisations per part in `--no-search` mode.
7. **Second seed** for the PR12, AC20 and Tone King starts.
8. **Held-out crop activity (data-1)** was not checked, by rule. Re-declare an ungated or activity-based crop rule before anyone cuts held-out crops.
9. **The Morgan instance-death trigger.** One launch: amp section off, then FX section off, repeated 3 times.
10. **The E1 SW50R neutral spread (median 0.099), still unexplained.** Re-render the neutral 5 times per part on 5 parts in one instance and log which replicate moves.
11. **Runs not audited:** E1x, `e1-pr12`, `e1-ac20` and the running `lib-shipped` runs. Re-run the E1 recount script on them once finished, with the same no-level, band-robust analysis.
12. **Separated stems (Demucs)**, the Tone King song-only product path (the synthetic renderer cannot drive Tone King), and selector enumeration end to end: none were run.
13. **Untouched code:**
    - `match/benchmark.py` `compare_baselines` (M4/M5 results) and `match/pairing.py` were read or partly exercised only. Cheapest test: re-run the M4/M5 baseline JSON command on the synthetic renderer and diff.
    - Sweeps for ignored controls on AC20, PR12 and TK lead.
    - Reverb and delay tails truncated at the DI's end.
    - The effect of the `prior_deviation` regulariser.
    - The harmonic study re-run with a fixed pitch tracker. Low priority: harmonic weight is 0 in v3.
14. **Whether Claude Code sets `CLAUDE_PLUGIN_DATA` for skill Bash calls.** Print the variable from inside a skill invocation.

### Rule deviations reported by auditors and verifiers
- The numbers auditor ran `git fetch -q` once. That contacted the remote and may have updated remote-tracking refs.
- One features script read finished WAVs and `result.json` under `bench-set2/runs/set2-rehearsal` (read-only). Its numbers were reproduced without it.
- The features-3 verifier read WAV headers (channel counts) of every crop directory, held-out ones included, before filtering. No held-out samples were loaded.
- Several verifiers (stats-1, stats-3, stats-7, loss-1, e1-1, e1-3) read the E2 and E3 JSONs after both runs had finished. The brief allowed only the logs. Read-only; nothing was touched.
- The renderer auditor used 4 plugin launches; PACE ports went from 102,762 to 110,076.
- No file whose name contains "key" was reported opened.
