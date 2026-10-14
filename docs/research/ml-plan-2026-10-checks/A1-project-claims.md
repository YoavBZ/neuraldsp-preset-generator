# A1: checking the reports' project claims ([P]) against the repository

Audited 2026-10-14 against `claude/new-session-22s984` (= `origin/main` + one docs commit) and the result branches `origin/ml/egvae-lite`, `origin/ml/knob-ceiling`, `origin/ml/set6-di-labelling` (already merged into main), `origin/poc/sound-model` and `origin/codex/*` (both older than main). Paths are repo-relative. `branch:path:line` means a file that exists only on that branch.

## Summary

| Report | [P] claims checked | CONFIRMED | CORRECTED | NOT FOUND | AMBIGUOUS |
|---|---|---|---|---|---|
| A (ours) | 66 | 47 | 16 | 0 | 3 |
| B (second agent) | 25 | 17 | 7 | 1 | 0 |

There are also 7 untagged project-fact claims (section X): 6 are wrong or out of date, and 1 is ambiguous.

**Cited paths.** Every repo path that Report A cites exists, including `ml/egvae-lite:docs/egvae-lite-plan.md`. One citation, "A2 of the project digest" (A:303), is not a repo document. It is `research_notes/Song to preset ML approaches/project_history_and_hybrid.md:153-156`, a secondary synthesis. Two cited files exist but do not support the claim as worded:
- `docs/set4-confirmation-results.md` for "−0.10 to −0.19 against today's start" (A:43);
- `docs/closeness-review-2026-10-10.md` for the "0.01–0.05 head start" of today's starts (A:177, 306).

Report B cites only the brief (`fileciteturn0file0`). It gives no repo paths.

### The 10 most decision-relevant corrections

1. **The headroom pilot already exists on a branch.** It is declared and was running on `origin/ml/knob-ceiling` (`docs/knob-ceiling-plan.md`, 2026-10-13/14). This is Report A's plan 3 and Report B's "do this first". It uses the true DI, 25 development parts in 15 bands (20 clean, 5 crunch) and a coordinate search from the menu oracle and from today's start, scored on the other half (knob-ceiling-plan.md:19-21, 34-42).
   - **The control failed.** Its exact planted-target control failed under six optimiser versions. The cause is a "sharp-bottomed valley" where the settings trade off against each other (amendment 1, :210-234; v6, :285-307).
   - **What the project concluded.** Searched gains now count only as lower bounds. A realistic control leaves the search 0.075 short on the held half (:236-262, 297-307).
   - **Status.** The main run hit render-order carry-over and was fixed with `isolate` (amendment 3, :309-347). No result yet.
   - **Consequence.** Report A's planted-target pass rule (within split-half noise of the target, on 5 of 6 targets; A:241-245) is the same exact-recovery test that failed here.
2. **Under-drive (A:212, 214, 450).**
   - **What "43 against 14" counts.** Part-amp cases, not parts (underdrive-trim-plan.md:7-8). They are the picks of the old network C, trained under the MPS gradient bug, on the 33 set-3 development parts. They are scored by the flat (v1) judge against the oracle at the session's own DI level, on half A only (underdrive-trim-results.md:38-40).
   - **Under the adopted protocol** the bias is about a third smaller: −0.094 uncut, −0.056 with the 3 kHz cut (underdrive-trim-results.md:26-34).
   - **A correction was already tested.** Playing the rebuilt DI 6 or 12 dB quieter roughly halved the bias but was futile for closeness: "Under-drive is not the main cause of the remaining gap to the oracle" (underdrive-trim-results.md:8-9, 16-19, 36-37; ROADMAP.md:109).
   - **The mechanism is not new.** It is the project's own (closeness-review-2026-10-10.md:84-85).
   - **What is still open.** Only a bias check on C′.
3. **The project's encoder already used Report B's main idea (B:7, 77, 90-100, 159).**
   - **Batch construction.** It already used same-setting/different-DI positives and same-DI/different-setting hard negatives (tone-encoder-plan.md:39-42).
   - **Prototypes.** It already ranked candidates by a content-averaged prototype: the mean embedding over renders through other folds' DIs (tone-encoder-plan.md:99-101, 125-126). The log-mel and PANNs rerankers did the same (rerank-plan.md:31).
   - **What it did not have.** Separator in the loop, waveform mixing into real backings, mastering, level kept (each view was loudness-normalised, tone-encoder-plan.md:65-67) and more DI bands (only 14, tone-encoder-plan.md:17-21).
   - **Chance level.** The 74.5% is against 4.5% chance (1/22). The 14% is the log-mel and PANNs baseline (tone-encoder-plan.md:104-106, 162-165), so Report B's "74.5% versus 14% chance" is wrong; the brief makes the same error at line 211.
4. **The menu ceiling against today's Morgan starts is about −0.10 to −0.13, not −0.10 to −0.19 (A:7, 43).**
   - **Against today's starts:** clean −0.131 (clean-baseline-results.md:44), crunch −0.104 (crunch-baseline-results.md:33), set 5 crunch −0.129 (set5-test-results.md:44).
   - **−0.16 to −0.19 is Tone King only,** against its own dry menu of 125 presets (toneking-baseline-results.md:48).
   - **Set 4's −0.196** is against the old starts, the clean template and the shipped driven preset (set4-confirmation-results.md:16-21).
5. **E0 and E0b percentages are shares of a small gap (A:44, 216, 311).**
   - E0b (4 codebooks) keeps 83% of the oracle's edge over C′; E0 (9 codebooks) keeps 91%. It is not "4 codebooks keep 83–91%" (egvae-lite-plan.md:142, 262).
   - That edge is only 0.032: C′ −0.099 against the oracle −0.131, on 18 development parts, against the leave-band-out fixed preset. The project's own note: "The gap to the oracle is about 0.03–0.04" (egvae-lite-plan.md:110-112).
   - "A better DI is worth up to about −0.12" (A:44) holds only for set 5 crunch against today's start (−0.129 against −0.023).
6. **Held-out pooling (A:268-274).**
   - **Set 5:** 26 in-scope parts in 5 bands after the declared Fytakyte→BKS merge (6 as declared), not "up to 7".
   - **Set 4:** the unused in-scope count is knowable. It is 10 parts (2 clean, 8 crunch) in 4 bands, plus 12 high-gain.
   - **Set 6:** 3 parts in 2 bands.
   - **Pooled:** no band overlaps, so 11 bands and 39 parts. Crunch is 9 bands, but 2 of them hold a single low-confidence part each.
   - **A stem test needs a mix.** Set 5 then has only 3 crunch bands (stem-test-power.md:13-15), and set 6 has only Little Tybee (validation-set6.md:11-12).
7. **The no-DI search, and which "v3" is meant (A:45, 239).**
   - **The −0.147 (p 0.078) is the positive control itself.** That control is SW50R's own-DI search against its start, scored as a median of band medians under the default bands (10 of 12 bands). Under the union bands it is −0.088 (p 0.149). It needed p < 0.05 under both band sets, so it failed and the whole re-check is void (no-di-rule-under-the-judge-results.md:12-23; plan :30-34).
   - **"Retired v3" means `unpaired-v3`.** That is the old score, retired as a judge on 2026-10-03 (measuring-closeness.md:9-13).
   - **Judge v3 is a different thing.** It is not retired: it is the candidate judge, and adoption waits for a ~55-trial listening calibration that has not run (judge-v3-results.md:105-117, 150-158; ROADMAP.md:113-117, 327-328).
8. **Power (B:37).** The power is 9–18%, not 9–37%, for the 3 crunch bands that have a mix (stem-test-power.md:26, 37; ROADMAP.md:316). The 37% would need a fourth band, at −0.10. The 0.101 SD is the spread of about 4 band means: C′ against `generate`'s start on set 5 crunch amp tracks (stem-test-power.md:19-20). It is a crude, crunch-only estimate.
9. **The separator.**
   - **SNR.** htdemucs_6s median SNR is 1.11 dB (sets 1–2) and 0.63 dB (set 3), on vocal-free instrumental mixes. Multi-guitar parts are 0.74 dB and single-guitar parts 5.86 dB (separator-upgrade-results.md:17). "1.2 dB" is not in the repo (A:388; B:204, 328, 478).
   - **Speed.** htdemucs speed was measured: 15 s wall (39 s CPU) per 30-s context (separator-upgrade-results.md:59). Report A's "time unmeasured" (A:43) is wrong.
10. **The dead ends overstate the evidence.**
    - **DI network variants.** Report A's "C-family DI network: no move in picks" (A:439) and Report B's "incremental C′ tuning failed" (B:471) cover runs made under the MPS gradient bug. The roadmap formally reopened them (ROADMAP.md:268-275, 287, 326), and the fixed network C′ then beat C on fresh set 5 (−0.124; set5-test-results.md:9-13).
    - **General audio models.** "CLAP/MERT near chance" is a literature result, not a project one: the project tested only PANNs CNN14 (A:430; B:71, 473; round-4-audio-ml.md:78; ROADMAP.md:366-369).

Also notable:
- A dry Tone King menu of 125 presets already exists (A:142 says otherwise).
- The JVM410H audit "holds" the data. It does not clear development use (A:171).
- "~136 development parts" (A:71, 140) counts every DI part. Only 35 in-scope parts in 15 bands have menu distances (sound-desc-plan.md:36-39).
- Report B's "the user's ears reversed main/second in 2 of 3 end-to-end runs" exists only in the brief (lines 274-277), not in the repo.

---

## Focus questions (from the brief), answered

| # | Question | Finding |
|---|---|---|
| 1 | Oracle gaps | **Today's starts:** Morgan clean −0.131 (13 parts, 8 bands, held-out sets 1–2; clean-baseline-results.md:44). Morgan crunch −0.104 "per half" (7 parts, 3 bands; crunch-baseline-results.md:33). Set 5 crunch −0.129, with C′ −0.023 and old C +0.124 (set5-test-results.md:20-21, 44). Tone King −0.191 clean / −0.164 crunch (toneking-baseline-results.md:48).<br>**Old starts:** set 4 oracle −0.196 (clean −0.263, crunch −0.116, high-gain −0.020); chooser −0.087 (90% −0.157 to −0.017), 45% of the oracle against 76% on development (set4-confirmation-results.md:21-22, 38-40, 46-48). High-gain chooser +0.318, 24 of 27 worse (:40, 57).<br>**Stem:** keeps 75% of the amp-track gain, −0.114 against −0.152 (songs-check-results.md:9-10, 30-36).<br>**−0.131 is not a set 5 number.** It is the development oracle on the 18-part residual set against the leave-band-out fixed preset (residual-di-results.md:37; egvae-lite-plan.md:119). It also happens to equal the held-out clean figure. Note the trap: E0 is also −0.129, the same value as set 5's oracle but a different quantity. |
| 2 | E0 and E0b | All on `ml/egvae-lite`. E0 −0.129 against oracle −0.131 and C′ seed 0 −0.099, i.e. "91% of the oracle's edge over C′" (egvae-lite-plan.md:138-142). E0b (`n_quantizers=4`) −0.126: "91% of E0's edge over C′ (83% of the oracle's)" (:257-262). E0b coherence 0.72 / 0.20 / 0.05 at 80 Hz–1 kHz / 1–3 kHz / 3–8 kHz (:268). C′ is 0.472 / 0.207 / 0.015 (residual-di-results.md:45-52). So E0b matches C′ only at 1–3 kHz and is far above it below 1 kHz. E1 mean mel on 96 validation clips: 3.44 (best checkpoint; final weights 3.23), C′ 2.29, raw recording 3.10, 4-codebook floor 1.17 (egvae-e1-results.md:23-31). |
| 3 | "43 against 14" | Counts part-amp cases (underdrive-trim-plan.md:7-8), on set 3's 33 development parts × 3 amps. Network: the pre-C′ rebuilt-DI chooser (C, trained under the MPS bug), uncut. Judge: flat (v1), against the oracle at the session's own DI level, half A only, mean knob bias −0.124 (underdrive-trim-results.md:38-40; closeness-review-2026-10-10.md:78-86). Adopted protocol (fixed −22.9 LUFS, both halves): uncut −0.094, 3 kHz cut −0.056, true DI at fixed level −0.022. The quieter-DI correction was futile (underdrive-trim-results.md:8-9, 16-19, 26-40). |
| 4 | Judge facts | All confirmed:<br>• median best-vs-second gap 0.043, only 10% clear 0.15, halves disagree 27% (closeness-review-2026-10-10.md:66-68);<br>• +12 dB above 5 kHz → exactly 0, on the three Ill Fate parts (:40-41); winners 13–25 dB too bright on Colour Me Red and Magilla (:46); drive +0.05 (:53);<br>• v3 changes the oracle's pick in 97 of 198 cells (judge-v3-results.md:50-55);<br>• 23/24 (avg-measure-listening-results.md:13), and the measure's pick is closer by spectral centroid on 25 of 30 (:53-54).<br>Caveat: 0.043 is a log ratio, 0.165 as a plain difference (judge-v3-results.md:147-148). |
| 5 | Is judge v3 retired? | **No.** Judge v3 (aligned judge, symmetric floor) is the candidate judge. The default is unchanged and adoption waits for a ~55-trial listening calibration, not yet run (judge-v3-results.md:5-6, 105-121, 150-158; heavy-listening-results.md:56-60; ROADMAP.md:113-117, 327-328; README.md:58-60). **`unpaired-v3`** (with v3c and `corrected_pair`) is the older unpaired score, retired as a judge on 2026-10-03 and kept only as a search objective (measuring-closeness.md:9-13; ROADMAP.md:481). Its DI-free baseline row has regret 0.34–0.38 (di-free-distance-results.md:24). Report A's two uses refer to two different things; both are correct but unlabelled. |
| 6 | The no-DI search | **What the study tested:** whether `match_preset` answers without a DI (no-DI search, noise probe, library search) beat the shipped template, re-scored under the judge on 43 set-2 development parts (37 scored, 12 bands) (no-di-rule-under-the-judge-plan.md:3-29).<br>**The positive control:** SW50R's search with the part's own DI (`set2-rehearsal`), searched against `unpaired-v3`. It passed only if the median and sum of band medians were below 0 with sign-flip p < 0.05 under both band sets (:30-34). It got −0.147 / p 0.078 (default) and −0.088 / p 0.149 (union) → failed → everything void (results :12-23).<br>**Why:** "The data does not show why" (:34). The default bands favour Cambridge parts (18 of 21, −0.36) but not Telefunken (7 of 16, +0.04). Honey (+0.57) and Doom Flamingo (+0.13) pull it over (:37-44). |
| 7 | Amp reach | **Menu size:** −0.267 → −0.291 (default bands; union −0.206 → −0.312; K1 bar −0.288; against PR12's template) (amp-reach-results.md:47-52). **AC20:** another amp is ≥0.150 closer on 14 / 15 of 25 parts (5 / 6 bands; null 95th percentile 9) (:59). **One acceptable amp:** 3 of 25 (default) / 5 of 25 (union) (quick-checks-results.md:28-31). **Identifiability:** 0.72 median band accuracy; SW50R 0.52 against a 0.50 gate, fragile (amp-identifiability-results.md:18-20). Neither report cites 0.72 or the 3–5 count. |
| 8 | Shortlist | **Perfect-ear G4 against template+R:** −0.198 / −0.183 (median of band medians; 18 / 17 of 25). Random-4 is only −0.059 / −0.041 (song-only-shortlist-results.md:76-81). **Within 0.150 of the oracle:** house-4 0.61/0.46, random-4 0.42/0.42, G4 0.39/0.39, template+R 0.29/0.29 (:92-105). **D3:** G4 against random-4 −0.004 / −0.046, "not shown" (:60, 68-69). All on 25 mostly clean development parts, against the old template. |
| 9 | Listening and routing | **17/21** (p 0.004) and **11/13** (starting-preset-listening-results.md:11-13, 27-32). **0.25/0.34** of the perfect-ear gain; taste test p 0.32/0.23 (listening-check-results.md:51-52, 61-62). **Regret 0.140 → 0.059;** paired new-minus-old **−0.081** (−0.134 to −0.033) (generate-routing-recheck-results.md:16-20). **+0.114** is the *original* routing cost against a label router (generate-routing-results.md:11-13; ROADMAP.md:416). It is not in the brief (the brief has −0.081 at :271), and Report B quotes neither number. |
| 10 | Power | The table at 3 / 4 / 8 / 12 / 20 crunch bands gives 9/18, 13/37, **32/80**, 47/94 and 68/99% at −0.05/−0.10 (stem-test-power.md:24-30). The note's own conclusion is "about 9–18% power" (:37). The **0.101** SD is the spread of band means of C′ against `generate`'s start on set 5 crunch amp tracks, i.e. set 5's report-only result (:19-20). |
| 11 | Separator | **Mega-53:** 102 s wall / 315 s CPU per 30-s context; 4 threads; wall times inflated by a shared machine (separator-upgrade-results.md:57-61, 65). **Gain:** +1.21 / +0.85 dB in median SNR, but paired medians only +0.50 / +0.61 (:18, 26-27). **htdemucs_6s:** 1.11 / 0.63 dB (:17). |
| 12 | Data and ledger | Development: 45 songs, 28 bands, 136 DI parts (`docs/part-locator-truth.json` `counts.parts`, `songs`, `folds`). Crunch: 13 parts in 6 bands (sound-desc-plan.md:36-39; crunch-baseline-results.md:13). The "33" is set 3's development split: 33 parts in 11 bands, 5 clean / 11 crunch / 17 high-gain (`docs/validation-set3.json` `counts.by_split_gain_class`; direct-preset-ranker-proposal-2026-10-09.md:35). Ledgers: section L below. |
| 13 | JVM410H | Confirmed: "Hold; do not select as a cleared training corpus merely because its top-level record says BY" (docs/research/native-guitar-development-data-2026-10-09.md:21). The reason is IDMT ancestry under CC BY-NC-ND (:7, 60). |
| 14 | The encoder | Section E below. |
| 15 | "Ears reversed main/second in 2 of 3" | Brief only (:274-277). Not in the repo; part-locator-plan.md:10-11 records only Eden's wrong window. |
| 16 | PoC "21–22 of 28" | Confirmed: 22/28 (recording bands) and 21/28 (union) closer than the shuffled control, i.e. the model fed three other bands' amp tracks (preset-model-poc-results.md:21, 33-35). Band median −0.10, 9 of 11 bands, **p 0.17**; 19–20 of 26 without the two biggest wins. Also ROADMAP.md:452. |

---

## Report A: [P] claims

| ID | A line | Claim as stated (abridged) | Evidence | Status | Note / correct value |
|---|---|---|---|---|---|
| A-01 | 25 | Listening validated only differences of at least 0.15 | closeness-review-2026-10-10.md:67, 88-89; measuring-closeness.md:19-21 | CONFIRMED | Since then, ear and judge agreed on 14 of 18 trials below 0.15 (in-sample; starting-preset-listening-results.md:38-42). |
| A-02 | 43 (and 7) | Oracle ceiling −0.10 to −0.19 on clean and crunch [set4, set5] | clean-baseline-results.md:44; crunch-baseline-results.md:33; set5-test-results.md:44; toneking-baseline-results.md:48; set4-confirmation-results.md:16-21, 38-39 | CORRECTED | Morgan against today's starts: −0.104 (crunch), −0.129 (set 5 crunch), −0.131 (clean). −0.16 to −0.19 is Tone King only. The cited set-4 −0.196 / −0.263 / −0.116 are against the *old* starts. |
| A-03 | 44 | −0.087 against the then-start "on fresh set 4"; 45% of oracle (76% on development) | set4-confirmation-results.md:22, 46-51; ROADMAP.md:203-207 | CORRECTED | Figures right. But the test pooled 20 held-out sets 1–2 parts (11 bands) with set 4's crunch parts, which lost (0 W / 3 T / 9 L). The edge came from sets 1–2 (−0.124). Old network C with the 3 kHz cut. |
| A-04 | 44 | Stem keeps 75% of the amp-track gain | songs-check-results.md:9-10, 35-36, 52-59 | CONFIRMED | Development data (24 parts, 14 bands), old starts, old network. Stems optimistic: no vocals, parts kept only at ≥1 dB SNR. |
| A-05 | 44 | Against today's crunch start C′ −0.023, oracle −0.129 | set5-test-results.md:19-21, 44 | CONFIRMED | Report-only, on amp tracks. |
| A-06 | 44 | Harmful on high-gain (+0.318) | set4-confirmation-results.md:40, 57-58 | CONFIRMED | 24 of 27 worse. |
| A-07 | 44 | A 4-codebook DAC round trip keeps 83–91% of the oracle edge | ml/egvae-lite:docs/egvae-lite-plan.md:142, 257-262 | CORRECTED | 4 codebooks: 83%; 9 codebooks: 91%. Both are shares of the oracle's edge **over C′** (0.032). Against the fixed preset, E0b keeps 0.126/0.131 = 96%. |
| A-08 | 44 | A better DI is worth up to about −0.12 [I on P] | egvae-lite-plan.md:110-112; residual-di-results.md:34, 38; set5-test-results.md:44 | AMBIGUOUS | On development, oracle minus C′ is about 0.03. Only set 5 crunch against today's start shows a ~0.106 gap. |
| A-09 | 45 | "The only judge-scored own-DI search gave −0.147 (p 0.078), but its positive control failed and it optimised the retired v3 score" | no-di-rule-under-the-judge-results.md:12-23, 34-38; plan :30-34; measuring-closeness.md:9-13 | CORRECTED | The search *was* the positive control. −0.147 is a median of band medians (default bands; union −0.088, p 0.149). It failed, so the study is void. "Retired v3" = `unpaired-v3`, not judge v3. Not "the only" such search: `ml/knob-ceiling` is a judge-scored own-DI search (no result yet). |
| A-10 | 45 | Menu size moved clean PR12 headroom −0.267 → −0.291 | amp-reach-results.md:47-52 | CONFIRMED | Default bands (union −0.206 → −0.312). Against PR12's template; 25 development parts, 9 bands. |
| A-11 | 45 | On 14 of 25 parts another amp's preset beat AC20's by ≥0.15 | amp-reach-results.md:59, 73-76, 101-102 | CONFIRMED | 14 / 15 (default/union). A cross-amp menu result, not a knob search. Cab, mic and EQ are confounded with the amp. |
| A-12 | 46 | Perfect-ear best-of-4 −0.18 to −0.20 against the template | song-only-shortlist-results.md:76-81 | CONFIRMED | Applies to G4 (researched list), median of band medians, against the old template+R. Random-4 only −0.06 / −0.04. |
| A-13 | 46 | Researched four-list no better than four random presets | song-only-shortlist-results.md:60, 68-69 | CONFIRMED | "Not shown to beat" (−0.004 / −0.046). |
| A-14 | 46 | Routing regret 0.140 → 0.059, in-sample | generate-routing-recheck-results.md:16-20, 66-70 | CONFIRMED | Bundled with the second start. Clean-vs-not-clean regret only. |
| A-15 | 46 | Real ear 0.25–0.34 of the perfect-ear gain; not beyond a song-blind taste | listening-check-results.md:9-14, 51-52, 61-62 | CONFIRMED | Check inconclusive; sitting 1 void. |
| A-16 | 46 | Two-way choices on own notes 17/21 | starting-preset-listening-results.md:11-13, 52-55 | CONFIRMED | Starts against what they replaced; in-sample, one listener. |
| A-17 | 47 | Effects moved the judge +0.001 on dry amp tracks | generate-routing-results.md:41, 51-53 | CONFIRMED | |
| A-18 | 47 | Time-effect estimators never run despite round 2 | README.md:302-303; round-2-full-plugin-estimation.md:125, 165-177 | CONFIRMED | Nuance: an earlier RT60-based reverb estimate existed and called reverb on/off at chance, 4 against 5 of 12 (round-2:125). |
| A-19 | 60 | High-gain headroom out of the rebuilt DI's reach | ROADMAP.md:329-330 | CONFIRMED | (−0.17) |
| A-20 | 61 | Lighter option chosen 11/13 | starting-preset-listening-results.md:27-32 | CONFIRMED | The doc adds "for clean and crunch references, lighter is plausibly right". |
| A-21 | 69 | Three render-trained attempts (kill tests, translator, encoder) all failed to transfer | ROADMAP.md:236-237, 248-250; preset-model-poc-results.md:33-35 | CORRECTED | The translator was re-read by the audit as "undecided, not failed": ridge held up on records in 5 of 6 crunch bands. A fourth attempt, the settings PoC, read part-specific information on 21–22 of 28 parts. |
| A-22 | 69 | Solo renders, narrow DI pool, no separator; mel-domain augmentation | tone-encoder-plan.md:17-21, 56-64; sound-desc-plan.md:31-32 | CONFIRMED | Encoder: 14 DI bands; mel-power bleed 12–30 dB below the clip. Translator: noise-only augmentation. |
| A-23 | 71 | DI pool ~136 parts from ~28 bands | docs/part-locator-truth.json (`counts.parts` 136, 45 songs, 28 bands) | CONFIRMED | But see X-6: only 35 in-scope parts have menu distances. |
| A-24 | 73 | Hybrid half-built: routing, second start, optional page | ROADMAP.md:31-34, 411-427 | CONFIRMED | |
| A-25 | 118 | Guitar-TECHS CC BY 4.0 | validation-datasets.md:40-43 | CONFIRMED | P1 trains; P3 is held out, the same player (set4-confirmation-results.md:82-83). |
| A-26 | 131 | ε from split-half noise: median best-vs-second gap 0.043 | closeness-review-2026-10-10.md:19, 66-67; judge-v3-results.md:147-148 | CORRECTED (minor) | 0.043 is the near-tie gap. Split-half noise is "about 0.04 between halves" (:19). Both are about 0.04. |
| A-27 | 137 | dasp-pytorch Apache-2.0, cited in round 3 | round-3-supervised-preset-model.md:90 | CONFIRMED | |
| A-28 | 155 | Records-only ridge (8 octave bands → 45 SW50R risks) never run | direct-preset-ranker-proposal-2026-10-09.md:35, 59-71; ROADMAP.md:319-321 | CONFIRMED | Inputs: relative octave powers of the htdemucs stem's half A; 33 set-3 development parts, 11 bands. |
| A-29 | 163, 210 | torch.stft MPS gradient wrong above 65,536 samples | ROADMAP.md:268-272 | CONFIRMED | |
| A-30 | 165 | Mega-53 ~102 s wall per 30 s on CPU | separator-upgrade-results.md:57-61, 65 | CONFIRMED | 315 s CPU, 4 threads, inflated wall time. |
| A-31 | 177, 306 | In-sample starts have a 0.01–0.05 head start | closeness-review-2026-10-10.md:70-72 | CORRECTED | Measured for the old fixed *driven* presets chosen on the same 33 set-3 parts. Today's class starts were chosen on 22 clean and 13 crunch development parts; their head start is unmeasured. |
| A-32 | 212 | Gain knob below the oracle's on 43 parts against 14 | underdrive-trim-plan.md:7-11; underdrive-trim-results.md:8-9, 24-40; closeness-review:78-86 | CORRECTED | See Q3: part-amp cases, old network C, v1 judge, session-level oracle on half A. Adopted-protocol bias −0.094 / −0.056. The correction was already tried and was futile. |
| A-33 | 216 | E0b −0.126 against an oracle of −0.131 | egvae-lite-plan.md:255-260 | CONFIRMED | 18 development parts, 8 bands, against the leave-band-out fixed preset. "≥80% of the oracle's edge" must mean the edge over C′. |
| A-34 | 218 | "The project's existing E2 rule": ≤ −0.015 with upper bound < +0.03; futile above −0.02 (7 df) | egvae-lite-plan.md:63-67, 236-238 | CORRECTED (label) | These are E1's set-5 rule plus the original EG-VAE-lite gate. E2 has no separate rule. |
| A-35 | 239 | Find out why the previous search's control failed | no-di-rule-under-the-judge-results.md:34; ml/knob-ceiling:docs/knob-ceiling-plan.md:228-234 | AMBIGUOUS | The no-DI doc says the data don't show why. The knob-ceiling amendments already diagnose why judge-scored searches miss an exact planted target. |
| A-36 | 268 | Set 5 clean and crunch: 26 parts in up to 7 bands | validation-set5.md:78; validation-set5.json `amendments[0]`, `counts.by_band_gain_class` (l.355); set5-test-results.md:46 | CORRECTED | 26 parts in 6 bands as declared, 5 after the Fytakyte→BKS merge (3 clean, 4 crunch). Nova-One is high-gain only. Fytakyte and Ferryboat Men have no mix. |
| A-37 | 269 | Set 4's 22 unused: in-scope count unknown, most high-gain | validation-set4.json `parts`, `counts.by_band_gain_class` (l.148); validation-set4.md:46-49 | CORRECTED | 10 in scope: Sonnet & Alcohol 2 clean; Umbriferous 6 crunch (3 tones + doubles); Bright Star Alliance 1 crunch (low confidence); Laminar Flow 1 crunch (low confidence). 12 high-gain. 4 bands. |
| A-38 | 270 | Set 6's 3 in-scope crunch parts | validation-set6.md:9-14, 105-116; validation-set6.json `counts` | CONFIRMED | 2 bands. Port St Willow is low-confidence, its crops read clean, and it is in MUSDB18 train, so only Little Tybee suits a stem test. |
| A-39 | 283 | Project table: 32% and 80% at 8 bands | stem-test-power.md:24-30 | CONFIRMED | Crunch bands, SD 0.101, bar "90% upper bound < 0". |
| A-40 | 287 | 73 MedleyDB songs with electric raw tracks; only 5 parts labelled | validation-set6.json `counts` (songs 73, labelled_parts 6, kept 5); validation-set6.md:20 | CONFIRMED | Caveats for "label more": 35 of 73 songs are in the separator's training data; no clean DI could be established; the first labelling round failed its hidden checks (1 of 6). |
| A-41 | 294 | Judge repeatable, time-aligned, validated for clear clean-to-crunch | closeness-review:15-19; measuring-closeness.md:19-21 | CONFIRMED | |
| A-42 | 296 | Oracle is best of 111 dry presets | knob-ceiling-plan.md:10-12; brief:82-83 | CONFIRMED | 108 factory + 3 templates. |
| A-43 | 297 | +12 dB above 5 kHz → 0; winners 13–25 dB too bright; drive +0.05 | closeness-review-2026-10-10.md:36-46, 53 | CONFIRMED | Judge v1; Ill Fate parts. Judge v3 fixes the treble deafness (judge-v3-results.md:15-17). |
| A-44 | 298 | v3 changes the oracle's pick in 97 of 198 cells | judge-v3-results.md:50-55 | CONFIRMED | |
| A-45 | 298 | Average-guitar measure beat the judge's preference 23/24 | avg-measure-listening-results.md:13, 24-29, 49-52 | CONFIRMED | The judge's margins there were tiny (median 0.038). "Not a verdict on the old judge." |
| A-46 | 299 | 0.043 gap; 10% clear 0.15; halves differ 27% | closeness-review-2026-10-10.md:66-68 | CONFIRMED | |
| A-47 | 301 | Measure's pick closer by centroid in 25 of 30 | avg-measure-listening-results.md:45-46, 53-54 | CONFIRMED | The doc says "spectral balance"; the pick is *not* systematically brighter (11 of 30). |
| A-48 | 303 | True-DI value within the menu ~0.13–0.26 [A2 of the project digest] | research_notes/.../project_history_and_hybrid.md:156; fixed-level-rescore-results.md:25; clean-baseline-results.md:44 | AMBIGUOUS | Not a repo document. The 0.26 is set 3 development (mostly high-gain) against a leave-band-out fixed preset. Against today's Morgan starts it is 0.10–0.13. |
| A-49 | 305 | Menu size moved a gate | amp-reach-results.md:47-52 | CONFIRMED | |
| A-50 | 305 | Time effects invisible to the judge | generate-routing-results.md:41, 51-53 | CONFIRMED | +0.001, on dry amp tracks. |
| A-51 | 307 | Many deciding tests had 9–40% power | stem-test-power.md:26-27; audit-2026-10-11.md:47, 51 | CONFIRMED | 9–37% (table), 20% and 40% (audit). |
| A-52 | 311, 445 | E0b kept 83% with the same 1–3 kHz coherence as C′ (0.20 vs 0.207); residual higher coherence, worse picks → "coherence is not the mechanism", a correction to the project | egvae-lite-plan.md:228-230, 262, 268-272; residual-di-results.md:33, 45-52, 69-71 | CORRECTED (framing) | Numbers right: R 0.217 against C′ 0.207, R +0.059. But (a) the project already concluded coherence "should not stand in for chooser quality" (residual-di-results.md:69-71); (b) at 80 Hz–1 kHz E0b is 0.72 against C′ 0.472, so only 1–3 kHz coherence is contradicted; (c) 83% is of the edge over C′. |
| A-53 | 317 | House-4 0.61/0.46, random-4 0.42, template 0.29 | song-only-shortlist-results.md:92-105 | CONFIRMED | House-4 is tuned on these parts; template = old template+R; G4 0.39. |
| A-54 | 361 | JVM410H held, not cleared, by the project's audit (IDMT upstream) | native-guitar-development-data-2026-10-09.md:7, 21, 60 | CONFIRMED | |
| A-55 | 388 | Project's stem has a median SNR of 1.2 dB | separator-upgrade-results.md:15-17 | CORRECTED | 1.11 dB (sets 1–2), 0.63 dB (set 3); multi-guitar 0.74, single 5.86. "1.2" appears nowhere in the repo. |
| A-56 | 430 | General embeddings (CLAP, MERT, …) near chance once notes differ [P] | tone-encoder-plan.md:162-165; ROADMAP.md:366-369; round-4-audio-ml.md:78 | CORRECTED (tag) | The project ran only PANNs CNN14 (14.2% top-1 against 4.5% chance; reranker failed). CLAP, MERT and wav2vec2 "near chance" is literature (RLAT, round 4). |
| A-57 | 432 | A 0.18 ms shift changes 67% of codebook-1 codes | ml/egvae-lite:docs/egvae-e1-results.md:49-55 | CONFIRMED | 8-sample delay keeps 33%. |
| A-58 | 433 | Knob regression 3.6% against a 10% bar | preset-model-poc-results.md:17-18; ROADMAP.md:449-450 | CONFIRMED | |
| A-59 | 434 | DI-free regret 0.36 against song-blind 0.42; agreement ≤0.38 | di-free-distance-results.md:19-35, 46-47 | CORRECTED (minor) | Rows range 0.30–0.48 against the constant's 0.36–0.42, depending on band set and menu. 0.36 vs 0.42 is one block. Agreement ≤0.38 is right. |
| A-60 | 435 | Mega-53 +1.21 / +0.85 dB | separator-upgrade-results.md:18, 26-27 | CONFIRMED | Paired medians only +0.50 / +0.61. |
| A-61 | 437, 440 | Karplus-Strong probe failed to replicate, 7/12 | tone-matching-plan.md:1520-1526 | CONFIRMED | 9/12 then 7/12 (p 1.0), under the superseded objectives. |
| A-62 | 439 | C-family DI network capacity, training and repairs: no move in picks | ROADMAP.md:164-193, 268-275, 287, 326; set5-test-results.md:9-13 | CORRECTED | Run under the MPS gradient bug and formally reopened. The corrected C′ beat C on fresh set 5 (−0.124). |
| A-63 | 440 | Noise probe DIs ruled out (round 1) | no-di-rule-under-the-judge-results.md:66-71 | CONFIRMED | Under the judge the noise probe arms are +0.29 to +0.40 against the start (void study). |
| A-64 | 441 | Class predictor failed its positive control twice; HNR AUC 0.43, fizz 0.48 | ROADMAP.md:296-298; generate-routing-results.md:81-83 | CONFIRMED | The class-predictor results file sits on `ml/class-predictor`, which is not among the fetched remotes. |
| A-65 | 443 | Four-way audition inconclusive; not beyond taste | listening-check-results.md:9-14, 61-62 | CONFIRMED | |
| A-66 | 444 | The oracle itself failed the SW50R gate | closeness-review-2026-10-10.md:100-104 | CONFIRMED | |

### X. Untagged project-fact claims in Report A that are wrong or out of date

| ID | A line | Claim | Evidence | Status |
|---|---|---|---|---|
| X-1 | 142 | "Tone King has no menu yet" | toneking-baseline-plan.md:17-34; toneking-baseline-results.md:44-48 | CORRECTED: a dry 125-preset Tone King menu exists, with an oracle. |
| X-2 | 43, 93 | htdemucs_6s time "unmeasured" | separator-upgrade-results.md:59 | CORRECTED: 15 s wall / 39 s CPU per 30-s context. MPS untimed. At about 5 s per 10-s clip, 21k clips ≈ 30 h of CPU wall time, not "overnight". |
| X-3 | 91, 214, 450 | Drive-bias check (0c), the "near-free correction" and the "new reading" | underdrive-trim-results.md:8-9, 26-40; closeness-review:84-85 | CORRECTED: already run on C; correction futile; the mechanism is the project's own. Only a C′ check is new. |
| X-4 | 7, 94, plan 3 | Continuous headroom pilot proposed as new | ml/knob-ceiling:docs/knob-ceiling-plan.md (whole file) | CORRECTED: declared and running; the exact control failed six times; results read as lower bounds. |
| X-5 | 171 | JVM "held … so this is development-only use" | native-guitar-development-data-2026-10-09.md:21, 60 | AMBIGUOUS: the audit says "Hold"; it does not clear development use. |
| X-6 | 140 | Real-part labels from "~136 development parts' true-DI × menu oracle rankings" | sound-desc-plan.md:36-39; validation-datasets.json (57 usable sets 1–2 development parts); validation-set3.json (33 development) | CORRECTED: in-scope parts with menu distances are 35 in 15 bands. Usable same-take development pairs are about 90; 136 counts every DI part. |
| X-7 | 450 | "Two new readings" | closeness-review:84-85; underdrive-trim | CORRECTED: the first reading is the project's documented hypothesis, already partly refuted. |

---

## Report B: [P] claims

| ID | B line | Claim as stated (abridged) | Evidence | Status | Note / correct value |
|---|---|---|---|---|---|
| B-01 | 11 | E0: DAC round trip preserved the oracle; exact codes were phase-sensitive | egvae-lite-plan.md:134-148; egvae-e1-results.md:10-14, 49-58 | CONFIRMED | Picks preserved; the waveform above 1 kHz is not (coherence 0.49 / 0.06). |
| B-02 | 15, 377 | Oracle gaps −0.13 to −0.19 ≈ 12–17% closer | brief:159-162; clean-baseline:44; crunch-baseline:33; toneking:48; residual-di-results:37; fixed-level-rescore-results:25 | CONFIRMED (as the brief) | Arithmetic right. The repo shows −0.104 to −0.131 for Morgan against today's starts; development against leave-band-out presets runs −0.131 to −0.260. |
| B-03 | 15, 367 | Judge treble-deaf on some heavy parts; oracle confined to a 111-preset dry menu | closeness-review:36-42; knob-ceiling-plan:10-12 | CONFIRMED | |
| B-04 | 37 | "Your own recent crunch tests had only about 9–37% power" | stem-test-power.md:24-27, 37; ROADMAP.md:316 | CORRECTED | 9–18% with the 3 crunch bands that exist. The 37% needs a fourth band. The brief (:129) carries the 9–37%. |
| B-05 | 53, 214, 293 | Decoder preserves the ranking information; four codebooks sufficient | egvae-lite-plan.md:253-275 | CONFIRMED | E0b −0.126 against oracle −0.131. |
| B-06 | 53, 470 | E1 failed, worse than the raw recording; sub-ms phase sensitivity | egvae-e1-results.md:23-31, 49-55 | CONFIRMED | 3.44 against 3.10; 8 samples keep 33%. |
| B-07 | 57 | Log-mel, MFCC and general encoders move more with notes; encoder fails render→record | di-free-distance-results.md:52-71; tone-encoder-plan.md:199-207 | CONFIRMED | Of the "general encoders" only PANNs was tested. |
| B-08 | 66 | Approach 1 "attacks the exact thing your previous encoder did not solve: note/player dominance" | tone-encoder-plan.md:39-42, 162-173 | CORRECTED | The encoder did generalise across players on renders (74.5%; 71.8% on unseen presets) with the same batch construction. Its failure was record transfer. |
| B-09 | 69 | Routing improved when based on the part | generate-routing-recheck-results.md:14-20, 66-70 | CONFIRMED | In-sample and bundled. |
| B-10 | 69, 494 | The user's ears reversed main/second in 2 of 3 end-to-end runs (Hotel California / Eden) | brief:274-277; part-locator-plan.md:10-11 | NOT FOUND (in repo) | The brief only. No repo record of these ear verdicts. |
| B-11 | 71, 292, 473 | MERT, CLAP, PANNs etc.: "project tests are already negative" | tone-encoder-plan.md:162-165; rerank-plan.md; ROADMAP.md:366-369; round-4-audio-ml.md:78 | CORRECTED | Only PANNs, log-mel and MFCC were project-tested. MERT, CLAP, BEATs, OpenL3 and AudioMAE never were. |
| B-12 | 75 | Encoder "74.5% versus 14% chance" | tone-encoder-plan.md:104-106, 162-165 | CORRECTED | Chance is 4.5% (1/22). 13.8% and 14.2% are the log-mel and PANNs baselines. 550 trials, 25 parts × 22 clean PR12 candidates. |
| B-13 | 131 | Renderer sustains 8–10k renders/h | brief:73-74; tone-encoder-plan.md:151; set4-confirmation-results.md:5-6 | CONFIRMED | 16,800 in 8,063 s with 3 workers; 10,989 in about 1 h. |
| B-14 | 168 | Historical DI-free agreement ≤0.38 | di-free-distance-results.md:46-47 | CONFIRMED | |
| B-15 | 204, 328, 478 | Separator median SNR about 1.2 dB; no acoustic/electric split | separator-upgrade-results.md:17; part-locator-results.md (caveat); commit e7e2496 | CORRECTED (SNR) | 1.11 / 0.63 dB on vocal-free instrumentals. Acoustic/electric mixing is confirmed. |
| B-16 | 250 | C′ mel 2.29, E1 3.44 | egvae-e1-results.md:27, 30, 63-67 | CONFIRMED | The project judged a latent-L1 E1′ "marginal against C′'s 2.29" (it would land about 2.0–2.2). |
| B-17 | 251 | "C′'s approximately 0.44–0.50 [coherence] in the 1–3 kHz region on clean parts" | audit-2026-10-11.md:55-57; residual-di-plan.md:11-16; residual-di-results.md:45-52 | CORRECTED | 0.44–0.50 are the pre-fix networks on held-out clean parts (the recording itself 0.72). C′ is 0.207 at 1–3 kHz and 0.472 at 80 Hz–1 kHz, on 18 development parts of all classes. |
| B-18 | 258 | Fewer than ~10 bands is estimation, not a decision; the power audit shows why | stem-test-power.md:24-30, 41 | CONFIRMED | 8–12 new crunch bands needed. |
| B-19 | 365 | Average-guitar measure 23/24, perfect repeats and swaps | avg-measure-listening-results.md:13-15, 30-31 | CONFIRMED | One listener, clean PR12, margins ≥0.15. |
| B-20 | 377 | Set 5 crunch oracle about −0.13 against the shipped crunch start | set5-test-results.md:44 | CONFIRMED | −0.129 |
| B-21 | 471 | "Incremental C′ tuning": longer training, more guitars, GLU/bottleneck, SI-SDR, real-amp source, residual, low-pass failed to change the picks | ROADMAP.md:164-193, 169-177, 268-275, 287, 326; residual-di-results.md:33 | CORRECTED (partly) | All but the residual were C-era runs under the MPS bug, since reopened. The 3 kHz low-pass did move the picks (−0.049 / −0.070 on development; +0.044 worse on held-out clean) before it was retired. Residual +0.059 futile: right. |
| B-22 | 472 | Global MFCC and log-mel distances failed to beat a constant | di-free-distance-results.md:19-50 | CONFIRMED | |
| B-23 | 474 | Regression PoC: small, fragile part-specific gain | preset-model-poc-results.md:14-24, 33-51 | CONFIRMED | |
| B-24 | 477 | Misrouted 10 of 22 clean parts | generate-routing-results.md:73-76 | CONFIRMED | 9 crunch + 1 heavier. |
| B-25 | 482 | Current augmentation and representation has not crossed the domain gap | tone-encoder-plan.md:196-207; sound-desc ROADMAP.md:248-252 | CONFIRMED | |

### B's central methodological claim (untagged, but the basis of its #1 rank)

| Claim | Did the project's encoder already do it? |
|---|---|
| "Positive pairs must be the same processing applied to different performances" | **Yes.** "Views of the same setting are positives (SupCon)". Each group has 8 settings, each heard through the same 3 DIs (tone-encoder-plan.md:39-42). |
| "Hard negatives must be different processing applied to the exact same performance" | **Yes.** "The other settings through the same DIs are hard negatives" (:41-42). Not specifically *nearby* settings: the 8 per block were sampled, half coverage and half jittered factory (:23-27). |
| "Content-averaged embedding prototype" (μθ over 8–16 DIs) | **Yes.** Candidate = "the mean over the renders of that candidate through the DIs of development parts in K3 folds other than p's"; cosine to the re-normalised mean (:99-101, 125-126). Same for the log-mel and PANNs rerankers (rerank-plan.md:31). |
| What the project did *not* do | Separator in the loop. Waveform-domain mixing into real backings: bleed was approximated in mel power, 12–30 dB below the clip (:58-64). Mastering or codec. Level kept: each view was loudness-normalised (:65-67). A continuous judge-based loss. More than 14 DI bands (:17-21). |

---

## E. The encoder (focus question 14), exactly

- **Data:**
  - 300 crossed blocks: one amp, 8 settings, 7 DI windows, each window from a different band among 14 (set 2's 13 development bands + Guitar-TECHS P1). That makes 16,800 renders (tone-encoder-plan.md:17-30).
  - Plus factory panels through 43 development DIs (:33-37).
  - One encoder per K3 fold, never trained on its own fold's bands (:46-52).
- **Augmentation (mel-power domain, per view):**
  - EQ tilt ±3 dB and a ±4 dB half-octave bell at 200 Hz–6 kHz;
  - bleed, with probability 0.5: 3 s of another fold's instrumental backing, **12–30 dB below the clip**;
  - white noise, with probability 0.5: 45–75 dB below the clip (:58-64);
  - views loudness-normalised (:65-67).
- **Model and training:** a 487k-parameter 1-D residual conv over 128 mel bands, SupCon at temperature 0.1, 4,000 steps per fold (:68-81).
- **Screen 1 (identification):** 25 K1 parts × 22 clean PR12 candidates = 550 trials; chance 4.5%. Top-1 **74.5%** (69.8–81.0%); log-mel 13.8%, PANNs 14.2%. No-menu encoders reached 71.8% (:96-106, 158-173).
- **Screen 2 (reranker on real recordings):**
  - against template+R: `enc_ref` +0.065 / +0.070 (11 / 9 of 25); `enc_stem` +0.040 / +0.034;
  - against `net`: worse by +0.101 / +0.118 (p 0.012 / 0.008);
  - it picks "Out of this World Clean" on 18 of 25 amp tracks;
  - the recordings' cosine to the nearest candidate is a median 0.46, against 0.86 for renders (:175-207).

## L. Held-out ledgers: current contents (there is no single ledger file)

| Set | Ledger | Uses recorded | Bands (kept parts) |
|---|---|---|---|
| 1–2 | `docs/validation-datasets.json:5240` `held_out_uses` (5 entries) | (1) `heldout-sw50r-di-vs-no-di`, 2026-09-28: 57 Chevy, Memphis, Guitar-TECHS P3 02/06/10/11. (2) `confirm-rebuilt-di-chooser-2026-10-10`, 2804e38: 17 sessions, 13 scored. (3) `crunch-baseline-2026-10-10`, 38358a5: Sugar - Faith, All The Same, One Flip Flop (second use). (4) `clean-baseline-2026-10-10`, 39ed0ff: 10 sessions (second use, recorded late). (5) `toneking-baseline-2026-10-11`, 3c02a59: the 13 scored sessions (third use). | 17 held-out sessions, 27 usable parts. The 20 clean and crunch parts sit in 11 bands: Rebecca Haviland & Whiskey Heart; Briana Maia; Catbite; Wild & Co (Telefunken); Chris Coltraine; Boogie Snakes; Forkupines; Lights Off Clarity; The Maybe Next Years; Tim Taler (Cambridge); the Guitar-TECHS player. Caveat: Rebecca Haviland, Chris Coltraine and Guitar-TECHS also have development material (`part-locator-truth.json` `folds`; set4-confirmation-results.md:82-83). |
| 3 | `docs/set3-heldout-use-ledger.json:4` (1 use); `validation-set3.json:4369` `held_out_uses: []` (frozen snapshot) | 2026-10-08 SW50R/PR12 amp-track confirmation, 27 parts, 6 bands, "Neither amp passed"; state "spent" | Crazy Swedes, Silence Is Near (crunch); Dunning Kruger, Silona (clean); Scott Elliott, V.M.GY (high-gain) (`validation-set3.json:61`) |
| 4 | `docs/validation-set4.json:2549` (1 use) | `confirm-rebuilt-di-chooser-2026-10-10`, "all 13 declared parts", spent; "the Internet Archive additions are not part of it" | **Spent (13):** Decypher (4 high-gain), Last Legacy (2 crunch), Lead Inc (2 crunch, 1 high-gain), The Black Crown (2 high-gain), Tholas P. (2 high-gain). **Unused (22):** Umbriferous (6 crunch, 4 high-gain), The Bright Star Alliance (1 crunch, 6 high-gain), Sonnet & Alcohol (2 clean), The Laminar Flow (1 crunch, 2 high-gain). Unused by class: 2 clean, 8 crunch, 12 high-gain (by crop class 3 / 8 / 11). |
| 5 | `docs/validation-set5.json:3523` (1 use) | `set5-cprime-test-2026-10-12`, seeds Cp0–Cp2 with pinned hashes; "First declared use of set 5" | BKS (4 clean, 5 crunch), Fytakyte (1 crunch; merged into BKS), Hazael (4 clean), Ronnie Jones (8 clean, 1 crunch), Saturn Syndicate (2 crunch, 1 high-gain), The Ferryboat Men (1 crunch), Nova-One Studio (4 high-gain). 31 kept: 16 clean, 10 crunch, 5 high-gain. 26 in scope. No mix for Fytakyte or Ferryboat Men. (`held_out_bands` also lists 5 bands with no kept part.) |
| 6 | `docs/validation-set6.json:8131` `held_out_uses: []` | Unused | Little Tybee (1 crunch), Port St Willow (2 crunch, low confidence, crops read clean, MUSDB18 train), Big Troubles (1 high-gain, MUSDB18 train), Purling Hiss (1 high-gain). `held_out_bands` lists 44 MedleyDB artists. |

**Overlap check.** Programmatically there is no band shared between sets 3, 4, 5 and 6 (`held_out_bands` and `band_strata`).

**Pooling 4 + 5 + 6.** In scope:
- set 5: 5 bands, 26 parts;
- set 4 unused: 4 bands, 10 parts;
- set 6: 2 bands, 3 parts.

That gives **11 distinct bands and 39 parts**, consistent with Report A's "about 10–12".
- **Crunch:** 9 bands, but Bright Star Alliance and Laminar Flow have one low-confidence part each, and Port St Willow reads clean on its crop.
- **Clean:** 4 bands: BKS, Hazael, Ronnie Jones, Sonnet & Alcohol.
- **Stem or mix test:** set 5 crunch drops to 3 bands and set 6 to 1 band.
