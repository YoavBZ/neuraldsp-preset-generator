# The spectral-envelope steps (`phase_scratch_envelope`)

Declared 2026-11-28, on the user's choice "Spectral steps first (Recommended)", after the `vc-own` search row read XW-part. The planner's plan (Fable, high) passed an independent review (Opus, high), PASS WITH AMENDMENTS; its amendments 1 to 6 are binding and win where they differ from the plan, and its non-binding notes are taken. The orchestrator's calls: "R_win matches with R_group undecided" goes to XE-undecided with the text "window suffices; group undecided" (no new code); a proof failure stops the shard. Ledger `preset-ladder` `phase_scratch_envelope`, then `phase_scratch_envelope_dry` (build.json's sha256, before any floor) and `phase_scratch_envelope_outcome`. Code: `learn/scratch_envelope.py` (the core, the table, the read), `learn/envelope_build.py` (the guitars, zero renders), `learn/envelope_floors.py` (the floors). Built 2026-11-28 (zero renders): the four proofs held on 47 of 47; build.json sha256 8c6e8eee… (`phase_scratch_envelope_dry`, with the realised-error and clamp-share summaries). Run 2026-11-28: XE-split, audited 2026-11-28 (independent, Opus), CONFIRMED WITH CAVEATS; [results](scratch-envelope-results.md).

## Goal

Say how finely the bank guitar's spectral envelope must be corrected to close S (+0.501 [+0.399, +0.603] on the 40, by the score): per part, per onset group, or per 43-ms window. The answer points the user at route 1, route 2, or neither. Every correction is an oracle from the true DI, read by the floor; a song-only way to get that envelope is not priced here.

## The guitars

Each is `tr-di` before its finish, corrected toward `vc-own` before its finish, then `p.finish`, cut to n, −22.9 LUFS (`voice_build.chain`).

| Guitar | Correction | Read as |
|---|---|---|
| `vt-part` | One EQ per part | A check: about 0 by construction (the finish refits each guitar's long-term tone) |
| `vt-group` | One EQ per onset group | An oracle per-note EQ; not a bound on a bank |
| `vt-win` | One EQ per 43-ms window (one STFT frame), 5-ms hop | Tone moving inside the note |
| `vt-mag` (beside) | `vc-own`'s magnitude, `tr-di`'s phase | Magnitude alone |
| `vt-phase` (beside) | `tr-di`'s magnitude, `vc-own`'s phase | Phase alone |

## The transform (amendment 1: fully defined)

- **Signals.**
  - Source (`tr-di` before its finish): `note_rebuild.denoise_above` of `scratch_rederive._synth(..., last=True)` with T.
  - Target (`vc-own` before its finish): `voice_build.padded_raw(prt.di_path, prt.start_s)` times `voice_build.own_gain` on `scratch_readerr.played_trace(p.notes, n + pad, p.bank, T's tuning, p.ring, T's mutes)`, its end fade at `real_end(n, pad)`.
  - Both must be exactly n + `pad_samples()` long, or the part stops before writing.
- **STFT.** Periodic Hann 2048, hop 240, `numpy.fft.rfft` (1,025 bins). The signal is zero-extended by 1024 at both ends, so frame i is centred on sample 240·i. Frames run 0 to (L − 1) // 240, so every sample lies within 240 of a frame centre.
- **Inverse.** `irfft` of each frame times the same window, overlap-added at the hop, divided by the overlap-added w² (never 0 on 0…L−1), cut back to 0…L−1.
- **Bands.** Third-octave centres 1000·2^(k/3), k = −12 to 12, edges at ±1/6 octave on the exact centres. Bin b (frequency b·48000/2048) lies in a band when its frequency is in [lo, hi). A band with fewer than 4 bins merges with the next one up. No bin falls on an edge. That leaves 20 bands:

  | Band | Centres (Hz) | Low edge (Hz) | High edge (Hz) | Bins | Count |
  |---|---|---|---|---|---|
  | 0 | 62.5, 78.7, 99.2, 125, 157.5 | 55.7 | 176.8 | 3-7 | 5 |
  | 1 | 198.4, 250 | 176.8 | 280.6 | 8-11 | 4 |
  | 2 | 315 | 280.6 | 353.6 | 12-15 | 4 |
  | 3 | 396.9 | 353.6 | 445.4 | 16-19 | 4 |
  | 4 | 500 | 445.4 | 561.2 | 20-23 | 4 |
  | 5 | 630 | 561.2 | 707.1 | 24-30 | 7 |
  | 6 | 793.7 | 707.1 | 890.9 | 31-38 | 8 |
  | 7 | 1000 | 890.9 | 1122.5 | 39-47 | 9 |
  | 8 | 1259.9 | 1122.5 | 1414.2 | 48-60 | 13 |
  | 9 | 1587.4 | 1414.2 | 1781.8 | 61-76 | 16 |
  | 10 | 2000 | 1781.8 | 2244.9 | 77-95 | 19 |
  | 11 | 2519.8 | 2244.9 | 2828.4 | 96-120 | 25 |
  | 12 | 3174.8 | 2828.4 | 3563.6 | 121-152 | 32 |
  | 13 | 4000 | 3563.6 | 4489.8 | 153-191 | 39 |
  | 14 | 5039.7 | 4489.8 | 5656.9 | 192-241 | 50 |
  | 15 | 6349.6 | 5656.9 | 7127.2 | 242-304 | 63 |
  | 16 | 8000 | 7127.2 | 8979.7 | 305-383 | 79 |
  | 17 | 10079.4 | 8979.7 | 11313.7 | 384-482 | 99 |
  | 18 | 12699.2 | 11313.7 | 14254.4 | 483-608 | 126 |
  | 19 | 16000 | 14254.4 | 17959.4 | 609-766 | 158 |

- **Edge bins.** Bins 0–2 (below 55.7 Hz) and 767–1024 (above 17.96 kHz) keep 0 dB in the three EQ steps. `vt-mag` and `vt-phase` swap all 1,025 bins.
- **Units.**
  - `vt-part`: one unit.
  - `vt-group`: frame i is in unit `bisect_right(bounds, 240·i)`, where the bounds are the onset groups' first onsets (`voice_build.group_onsets`) less 2 ms, in samples by round(). Unit 0 is everything before the first; the last runs to the padded end. An empty unit is dropped.
  - `vt-win`: one frame each.
- **Energy.** E[unit, band] is the STFT power |X|² summed over the unit's frames and the band's bins.
- **Level alignment (the implementer's call, recorded for the orchestrator).** Before the gains, the target's STFT is scaled by one factor per part: the square root of the source's in-band power over the target's, summed over all 20 bands and every frame of the padded part.
  - Why: on 3 real parts (in memory, zero renders, nothing written), the unaligned target sat 17–37 dB under the source, so the ±20 dB clamp caught 40–100% of `vt-part`'s cells and up to 79% of `vt-group`'s. The clamp then bounded the two signals' arbitrary levels, not the envelope's shape.
  - It is harmless otherwise: the finish (`song_bank.measure`: a re-EQ to the average guitar, then −22.9 LUFS) and `chain`'s −22.9 LUFS re-level every guitar, so the factor reaches a finished guitar through the clamp and through the 0-dB cells (edge bins and floored cells), which the alignment places at the source's level.
  - It is recorded per part (`target_align_db`); proof 4 runs on the unscaled target.
- **Gain.** sqrt(E_target / E_source) per unit and band, the same for every bin of the band and every frame of the unit. Its amplitude dB is clamped to ±20 dB.
- **"Loudest" (the floor).** A cell keeps 0 dB when E_source < (that band's largest source cell over the part's units at that step) × 10⁻⁴, in power, or when E_source = 0. E_target = 0 with E_source > 0 gives −20 dB.
- **Swaps.** `vt-mag` is |X_target| with X_source's phase; `vt-phase` is |X_source| with X_target's phase, in every bin. Where the phase donor's magnitude is 0, the other signal's own bin is kept. The phase is `numpy.angle`'s, so a subnormal magnitude can't overflow.

## The proofs (amendment 6), on 47 of 47

A failure stops the shard before that part writes anything (the orchestrator's call).

1. `source_is_tr_di`: the source through `chain` is `tr-di` byte for byte (build 2's sha256).
2. `target_is_vc_own`: the target through `chain` is the stored `vc-own` byte for byte (the sound-gap build.json's `audio_sha256`). Its inputs are named above, as `voice_build.part_record` builds `vc-own`.
3. `unity_is_source`: unity gains through `apply_gains`, on each EQ step's own units, then the inverse, return the source: max |y − x| / max |x| ≤ 1e-9, float64, before the finish.
4. `swap_is_target`: the target's STFT, put through the swap with its own magnitude and phase, then the inverse, returns the target within the same tolerance. Without it a mis-wired or mis-aligned swap is caught by nothing.

**Checked in memory before the declaration** (zero renders, every write stubbed, nothing under PF): all four proofs held on 3 real parts (a BKS, a GOAT and a panel part), proofs 3 and 4 at 1.5e-16 to 4.3e-16. Each part took 7.6–8.2 s.

## The realised error (amendment 2)

Recorded per part for all five guitars, on the cells that are not floored:
- **Against the clamped intent,** before the finish: per cell 10·log10(E_y / E_source) less the intended gain. This is the transform's fidelity. `vt-mag` is read against the target's band power and `vt-phase` against the source's, both on `vt-win`'s cells and floor.
- **Against the target,** after the finish: the finished `vt-k` against the finished `vc-own`, per cell, on the step's cells and floor (`vt-win`'s for the swaps). This is what the adaptive finish leaves.
- Per part and step: the median and 90th percentile of |error| in dB, the signed median, the cell count, and the step's clamped and floored shares. Spectral convergence for `vt-mag` and `vt-phase`. The level change before the finish and the step to −22.9 LUFS.

Every "not closed" statement carries the error achieved.

## The terms

Floors at row (b)'s answer, the held half, the true DI as the judge's DI. `tr-di`'s floor is stored (the exact-notes floors.json) and so is `vc-own`'s (the sound-gap floor records, each hashed in the sound-gap rows.json).
- C_k = ln(d_tr-di / d_vt-k): what step k closes.
- R_k = ln(d_vt-k / d_vc-own): what is left.
- C_k + R_k = S per part, to 1e-12, on each step's passing set.
- **Passing sets.** One for the code: `tr-di`, `vc-own` and the three EQ guitars. The beside steps each use their own (`tr-di`, `vc-own` and that guitar), so a beside refusal never moves the code.
- **S1.** A refused render reruns once (`--rerun`, a fresh process). The intent-to-treat code (a refused part at 0.0) sits beside, and the read is marked `refusal-sensitive` when the two codes differ.

## Outcome table `XE_TABLE`

On the 40, the first that holds. Labels are `paired_reading`'s only: "C_k reads worse" means step k closes a heard-size amount; "R_k matches" means a heard-size remainder is ruled out.

| Code | When | Decides |
|---|---|---|
| XE-anomaly | A proof, the repeat check, S's reproduction or the identity fails; a C or R of the EQ steps (part, group, win) has no usable interval; or any of them reads better | Unexpected; audit. If no fault is found, the figures go to the user as read |
| XE-static | C_part reads worse (closes) | Unexpected by construction; audit the finish. If it stands, that part of S is static tone: the finish, not a sound route |
| XE-group | R_group matches | A per-note correction is enough: route 1's kind (a better-matched bank, pickup, or per-note EQ). An indication, not a bound on a bank, which also changes attacks and articulation |
| XE-window | R_win matches and R_group reads worse | The tone must move inside the note: route 2, or samples that change over the note |
| XE-split | C_win closes and R_win reads worse | Envelope correction buys about C_win, an estimate within the realised error (it understates rather than bounds); the rest is not envelope at this resolution. C_group's reading says whether per-note covers the envelope part |
| XE-detail | R_win reads worse and C_win matches | No heard-size part is envelope: note content or detail. Route 3 or the stem; route 2 only as whole-waveform generation |
| XE-undecided | Anything else | To the user with the intervals. When R_win matches and R_group is undecided, the text says "window suffices; group undecided" |

- **Faults against surprises (amendment 3).** "A C or R reads better" and XE-static can be real outcomes, not faults: per-frame gains at a 5-ms hop can harm by heard size. So when either holds without a fault, the read also records the code the rest of the table gives (`then`, from XE-group on), and lists every surprise. A fault (a failed check or a missing interval) has no `then`.
- **The tightened labels (amendment 4).** XE-window needs R_group "worse"; XE-detail needs C_win "matches"; XE-split says "about", not "at most".
- **The goal wording (amendment 5),** on every "Decides" from XE-static to XE-detail: the correction is an oracle from the true DI, read by the floor; a song-only way to get this envelope (for example from the stem, through the amp) is not priced here; the next search row (about 13,400 renders) needs its own go; a floor remainder over 0.10 may cost little by search, because the floor-to-search mapping is concave.
- **Flagged beside:** "R_group matches while R_win reads worse" as a window-step artefact.

**Beside, never changing the code:**
- `vt-mag` and `vt-phase`, each with its realised error. Neither is read as "note content or string detail".
- Fieller's C_k / S.
- `vc-env`'s stored E1 (+0.028 [+0.020, +0.037], matches): the level-only, one-band relative. It is built differently, on the finished guitar with 20-ms frames, so it is not a step. `vt-win` also corrects per-band level and decay at 43 ms.
- Clean and crunch; each cluster left out; the three largest parts; all 47.
- Spearman of C_group and C_win with −D_own (`fs-own`'s rows.json, its sha256 main's `phase_scratch_own_outcome`).
- The passing-only and intention-to-treat reads, as the sound-gap test does.

## Seen before the declaration

- S on the 40: +0.501 [+0.399, +0.603], worse (`phase_scratch_voice_outcome`); the read must reproduce it per part and to 3 places.
- E1 (`vc-env` against `tr-di`): +0.028 [+0.020, +0.037], matches; E2 +0.472 [+0.371, +0.574], worse.
- The control: Ux +0.044 [+0.017, +0.072], matches (XC-stands).
- `fs-own`: XW-part; D_own −0.191 [−0.261, −0.122], C_own +0.082 [+0.018, +0.146]; Fieller's share 0.70 [0.52, 0.92].
- The review's probe: 0.5–0.8 dB median error on the window step; about 3 dB per bin on `vt-mag`.
- The implementer's in-memory check on 3 real parts (aligned target): the intent error's median |error| on `vt-win` 0.40–0.49 dB (90th percentile 2.6–2.8 dB); on `vt-mag` 0.71–0.91 dB per band-frame cell, spectral convergence 0.15–0.29; on `vt-part` 0.03–0.06 dB. After the finish, against the finished `vc-own`: `vt-part` 0.14–0.32 dB, `vt-group` 1.02–1.57 dB, `vt-win` 1.16–1.37 dB (90th percentile 5.2–5.5 dB). The clamped share was 0–11%, the floored share on `vt-win` 32–39%. No floor was rendered.

## Names

Re-grepped on origin/main 55dea475 (after #664 merged), over docs, learn, tests, scripts and reference:
- `phase_scratch_envelope`, `scratch_envelope`, `envelope_build`, `vt-` and `XE-` each have one hit: the reservation list in `tests/test_scratch_own.py`, which scans only `scratch_own.py`.
- `fs/envelope` appears only in `scratch_own.py`'s forbidden trees, its plan, and the ledger's `phase_scratch_own` guards line.
- `envelope_floors`, `XE_TABLE`, `xe_code`, C_part, C_group, C_win, R_part, R_group, R_win, C_mag, R_mag, C_phase, R_phase, `EnvelopeWorld`, `level_align` and `target_align_db` have none.
- "ENVELOPE" (this run's log label "ENVELOPE FLOORS") also matches `ENVELOPE_RATE` in the tone-matching plan, and "window suffices" matches a sentence in `verify_tracks.py`. Neither is a term of these steps.
- No guarded key prefix covers `phase_scratch_envelope`.

## Phases

| # | Phase | Cost | Verify |
|---|---|---|---|
| 0 | Preconditions | — | #664 merged, so main holds XW-part; the user's 2026-11-28 words in the ledger; 31 GB disk guard |
| 1 | Declare, this PR | 0 renders | Tests pass; the table guard; the band table |
| 2 | `envelope_build build --shard k/3`, then `--combine`; the hash PR `_dry` | 0 renders, about 440 MB | Proofs on 47 of 47 |
| 3 | `envelope_floors floor --shard k/3`, then `--rerun` | 478 renders (5 × 47 × 2 + 8) | The two check parts repeat the stored `tr-di` and `vc-own` floors exactly |
| 4 | `scratch_envelope read`, once | 0 | S reproduces per part; the identity holds |
| 5 | Audit, results PR `_outcome` | 0 | One XE code, with its `then` field |

Measured so far: the in-memory build took 7.6–8.2 s a part on 3 parts. The sound-gap floors took 6 minutes for the same render count.

## Guards and files

- Every command refuses unless this checkout runs main's code (the three modules and the pinned files: `scratch_voice`, `voice_build`, `voice_floors`, `voice_control`, `scratch_own` and their pinned files, `scratch_readerr`) and keys (`phase_scratch_envelope*`, `phase_scratch_own*`, `phase_scratch_voice*`), and main holds the draw, row (b)'s answers, the stored floors, the voice build's hash, the sound-gap read, the `vc-own` row's read and this declaration. The steps run only under the row's XW-closed or XW-part.
- This module has its own guard (`require_envelope`, as `scratch_own.require_own`). It edits none of the pinned files and adds no `UNIT_FILES` entry to `scratch_voice.py`.
- Files, each written once, under `PF/fs/envelope/`: `dry/<guitar>/<part>.npy`, `build-parts/`, `build.json`, `floors/`, `floors-first/`, `repeat/`, `rows.json`, `report.json`. Part keys reach git only as 12-hex tags. `scratch_own`'s search never opens this tree.
- At most 3 render processes; the disk guard before every part.

## Dependencies and risks

- **Floors are screens.** fs-own showed real audio buys −0.191 by search; these floors say which kind of correction, not its search gain. A search row through the deciding guitar (about 13,400 renders) needs its own go.
- **The transform is imperfect.** Every "not closed" statement carries the error achieved.
- **Oracle and reuse.** Every correction comes from the true DI; the 47 parts have been read many times.
- **All by the score (J0), at one preset.** Nothing is heard.

## Done test

Main holds `phase_scratch_envelope_outcome` with one audited XE code (with its `then` field when it applies), the C and R intervals, and the realised errors. Stop rule: one audited code goes to the user; nothing loops.
