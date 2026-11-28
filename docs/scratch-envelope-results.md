# The spectral-envelope steps: results (`phase_scratch_envelope_outcome`)

Plan: [scratch-envelope-plan.md](scratch-envelope-plan.md). Ledger `preset-ladder` `phase_scratch_envelope`, `_dry`, `_outcome`.
- **Run:** 2026-11-28.
- **Audit:** 2026-11-28 (independent, Opus), CONFIRMED WITH CAVEATS. Every figure reproduces.
- **Scope:** every number is by the score (J0), at one preset (row (b)'s answer), from oracle corrections built from the true DI. Nothing here is by ear.

## The code: XE-split, by the score

`tr-di` before its finish was corrected toward `vc-own`, then finished as before, in three steps of growing resolution, with two swaps beside. On the 40:

| Step | Correction | C_k: what it closes | R_k: what is left | Fieller C_k / S |
|---|---|---|---|---|
| `vt-part` | one EQ per part | +0.003 [−0.001, +0.007] matches | +0.498 [+0.395, +0.600] worse | 0.006 [−0.002, 0.015] |
| `vt-group` | one EQ per onset group | **+0.144 [+0.111, +0.177] worse** | +0.357 [+0.279, +0.435] worse | **0.29 [0.25, 0.33]** |
| `vt-win` | one EQ per 43-ms window | **+0.215 [+0.168, +0.262] worse** | **+0.286 [+0.222, +0.350] worse** | **0.43 [0.39, 0.47]** |
| `vt-mag` (beside) | `vc-own`'s STFT magnitude, `tr-di`'s phase | +0.442 [+0.338, +0.546] worse | +0.059 [+0.043, +0.076] undecided | 0.88 [0.83, 0.92] |
| `vt-phase` (beside) | `tr-di`'s STFT magnitude, `vc-own`'s phase | +0.026 [+0.018, +0.035] matches | +0.475 [+0.371, +0.578] worse | 0.05 [0.03, 0.08] |

S = ln(d_tr-di / d_vc-own) is +0.501 [+0.399, +0.603], reproduced from the stored files. "C reads worse" means the step closes a heard-size amount.

- **The code.** C_win closes and R_win reads worse, so the declared code is **XE-split**.
  - Nothing earlier in the table holds. No C or R of the EQ steps reads better; C_part does not close; R_group does not match; R_win does not match.
  - `then` is null: there is no surprise and no fault. No flag is set.
- **What XE-split says.** Band envelope correction buys about C_win = +0.215 (43% of S). The rest is not envelope at this resolution. C_group reads worse: per-note correction covers part of it, +0.144 (29%).
- **The checks.** Every check held:
  - the build's four proofs on 47 of 47;
  - the repeat check: `tr-di` and `vc-own` repeated their stored floors exactly on `f2030431a5bb` and `60c856cd5dc4`;
  - S reproduced per part, equal to the stored interval and to 3 places;
  - the identity C_k + R_k = S on every step, largest gap 3.3e-16.
- **S1.** Nothing was refused (the beside steps included), so the passing set is all 40 and there is no intent-to-treat read.

**What the table says next.** The next step is the user's route pick:
- per-note correction (route 1's kind) covers about 29%;
- per-43-ms band correction covers about 43%;
- the rest is finer structure.

Each figure is an oracle from the true DI, read by the floor. A song-only way to that envelope is not priced here, and any search row needs its own go.

## The caveats (binding, from the audit)

1. **The magnitude swap is not "magnitude detail" or timbre.** At 88% overlap, the STFT magnitude carries the true DI's pitches, partials, bends and level. The zero-render log-spectrum correlation with `vc-own` (80–2000 Hz) rises from 0.64 for `vt-part` to 0.70 for `vt-win` and 0.81 for `vt-mag`.
   - May claim: by the score, the floor's distance is carried by the STFT magnitude, not the phase.
   - May not claim: that 88% of S is timbre separable from notes. R_mag is the phase mismatch plus reconstruction error, not "what notes cost".
2. **Band envelope correction buys about C_win = +0.215 (43%).** This is an estimate within the realised error and likely understates it; it is not a bound. The group step gives +0.144 (29%).
3. **"The rest is not envelope at this resolution"** means finer than third-octave bands at 43 ms. It does not show that the rest is note content.
4. **`vt-win` overlaps E1.** It also corrects per-band level and decay over time. `vc-env`'s stored E1, the level curve alone, is +0.028 [+0.020, +0.037] (matches).
5. **An oracle at one preset, by the score.** No song-only path is priced, floors don't predict search gain, and nothing was judged by ear.
6. **R_mag reads undecided, not matches.** Don't write that the magnitude swap closes S.

## What may and may not be claimed

**May:**
- By the score, on the 40, one EQ per onset group closes about 29% of S, and one EQ per 43-ms window about 43%. Both are estimates within the realised error, likely understated.
- A static EQ per part closes nothing (C_part matches), as built: the finish refits each guitar's long-term tone.
- The rest of S is not band envelope at third-octave and 43-ms resolution.
- The floor's distance is carried by the STFT magnitude, not the phase.

**May not:**
- That 88% of S is timbre separable from notes, or that the magnitude swap closes S.
- That the rest is note content.
- That a bank, a pickup or any song-only method reaches these figures.
- Any search, product or ear claim.

## The terms on the declared splits

| Set | S | C_group | R_group | C_win | R_win | C_mag | R_mag |
|---|---|---|---|---|---|---|---|
| **The 40** | +0.501 [+0.399, +0.603] | +0.144 [+0.111, +0.177] | +0.357 [+0.279, +0.435] | +0.215 [+0.168, +0.262] | +0.286 [+0.222, +0.350] | +0.442 [+0.338, +0.546] | +0.059 [+0.043, +0.076] u |
| All 47 | +0.429 [+0.351, +0.508] | +0.130 [+0.105, +0.156] | +0.299 [+0.241, +0.357] | +0.199 [+0.156, +0.242] | +0.230 [+0.186, +0.275] | +0.377 [+0.297, +0.458] | +0.052 [+0.040, +0.064] u |
| Clean 20 | +0.671 [+0.451, +0.891] | +0.183 [+0.124, +0.242] | +0.487 [+0.329, +0.646] | +0.283 [+0.188, +0.379] | +0.388 [+0.255, +0.520] | +0.618 [+0.421, +0.815] | +0.053 [+0.033, +0.072] u |
| Crunch 20 | +0.331 [+0.269, +0.393] | +0.105 [+0.073, +0.136] | +0.226 [+0.182, +0.271] | +0.147 [+0.108, +0.187] | +0.184 [+0.147, +0.220] | +0.266 [+0.215, +0.316] | +0.065 [+0.038, +0.093] u |

- Every cell above reads worse except those marked u (undecided).
- C_part matches on every split: the 40 +0.003, all 47 −0.001, clean +0.002, crunch +0.004. C_phase matches on every split: +0.026, +0.031, +0.018 and +0.034.
- **Per part on the 40:**
  - C_win is positive on all 40 (lowest +0.001);
  - C_group is negative on 1 part;
  - R_win is positive on all 40;
  - R_mag is negative on 4 parts.

**Each cluster of the 40 left out (32 reads).** Every term keeps its reading in every read.

| Term | Range of means | Lowest lower end | Highest upper end |
|---|---|---|---|
| S | +0.454 to +0.515 | +0.383 | +0.628 |
| C_part | +0.002 to +0.005 | −0.002 | +0.009 |
| C_group | +0.132 to +0.151 | +0.102 | +0.186 |
| R_group | +0.322 to +0.368 | +0.267 | +0.453 |
| C_win | +0.196 to +0.224 | +0.157 | +0.274 |
| R_win | +0.257 to +0.294 | +0.211 | +0.364 |
| C_mag | +0.394 to +0.459 | +0.317 | +0.573 |
| R_mag | +0.055 to +0.062 | +0.039 | +0.079 |
| C_phase | +0.024 to +0.028 | +0.016 | +0.036 |
| R_phase | +0.428 to +0.489 | +0.355 | +0.604 |

**The three largest parts per term on the 40** (12-hex tags):

| Term | Parts (set, value) | The 40 without them |
|---|---|---|
| C_group | `a3b1b27272d3` (BKS, 0.363), `9c2b0e8c6bea` (BKS, 0.358), `c1ea6ef819b3` (GOAT, 0.341) | +0.129 [+0.103, +0.155], worse |
| R_group | `b2ce529e68f9` (GOAT, 0.887), `3ee6335d235b` (GOAT, 0.825), `8ae994594bad` (BKS, 0.819) | +0.335 [+0.260, +0.411], worse |
| C_win | `8ae994594bad` (BKS, 0.491), `a3b1b27272d3` (BKS, 0.468), `9c2b0e8c6bea` (BKS, 0.460) | +0.187 [+0.160, +0.213], worse |
| R_win | `b2ce529e68f9` (GOAT, 0.763), `a3b1b27272d3` (BKS, 0.699), `ea5fc54a8160` (GOAT, 0.632) | +0.265 [+0.208, +0.323], worse |
| C_part | `4ea260f59ccd` (BKS, 0.056), `c29832ab789c` (BKS, −0.027), `9c2b0e8c6bea` (BKS, 0.017) | +0.002 [+0.000, +0.003], matches |
| R_part | `a3b1b27272d3` (BKS, 1.158), `8ae994594bad` (BKS, 1.082), `b2ce529e68f9` (GOAT, 1.079) | +0.439 [+0.383, +0.495], worse |
| S | `a3b1b27272d3` (BKS, 1.167), `8ae994594bad` (BKS, 1.086), `b2ce529e68f9` (GOAT, 1.078) | +0.442 [+0.387, +0.497], worse |

## Beside the code

- **Spearman with `fs-own`'s −D_own** on the 40 (40 parts): C_group +0.44, C_win +0.47.
- **E1** (`vc-env`, the level curve alone, stored): +0.028 [+0.020, +0.037], matches. `vt-win` overlaps it (caveat 4).
- **The swaps** (caveats 1 and 6):
  - The magnitude swap closes C_mag +0.442 (Fieller 0.88), and its R_mag of +0.059 reads undecided.
  - The phase swap closes C_phase +0.026 (Fieller 0.05, matches).
  - The STFT magnitude at 43-ms frames with 88% overlap also carries the true DI's notes, so this splits magnitude from phase, not timbre from notes.

## The realised error

The median over the parts of each part's median and 90th-percentile |error|, in dB, on the cells that are not floored:
- **Intent:** before the finish, against the clamped intent (the transform's fidelity).
- **Target:** the finished guitar against the finished `vc-own` (what the adaptive finish leaves).

| Guitar | Intent median (the 40) | Intent p90 | Target median | Target p90 | Clamped share | Floored share | Level change before the finish (47) |
|---|---|---|---|---|---|---|---|
| `vt-part` | 0.05 | 0.32 | 0.24 | 0.78 | 0% | 0% | −0.14 to −0.00 dB |
| `vt-group` | 0.33 | 2.92 | 1.24 | 5.37 | 7.4% | 9.7% | −0.30 to −0.03 dB |
| `vt-win` | 0.40 | 2.66 | 1.33 | 5.69 | 6.3% | 35% | −0.38 to −0.03 dB |
| `vt-mag` | 0.93 | 3.75 | 0.80 | 3.24 | — | 35% (`vt-win`'s cells) | −1.70 to −0.06 dB |
| `vt-phase` | 0.86 | 3.65 | 5.13 | 16.19 | — | 35% (`vt-win`'s cells) | −0.99 to −0.18 dB |

- **All 47** (`phase_scratch_envelope_dry`):
  - `vt-win`'s intent median is 0.41 dB (0.08 to 0.64 across parts), its target median 1.33 dB, and its clamped share 1.4% to 26.6% across parts.
  - The spectral convergence is 0.24 for `vt-mag` and 0.26 for `vt-phase`.
  - The target's level alignment runs 17.5 to 40.6 dB.
- The window step's intent error (0.40 dB) is a little under the review's probe (0.5–0.8 dB). The magnitude swap's 0.93 dB is per band-frame cell; the review's about 3 dB was per bin. Every "not closed" figure above carries this error: C_win likely understates the band correction's worth (caveat 2).

## What ran

- **Build.** Zero renders, from a fresh detached worktree of origin/main at f8fbdbad.
  - `build --shard k/3`, k = 0, 1, 2, in parallel: 164, 163 and 153 s. Then `--combine`.
  - The four proofs held on 47 of 47 (unity and swap at most 4.8e-16 and 5.1e-16).
  - `build.json` sha256 `8c6e8eee…`, hashed in `phase_scratch_envelope_dry` (#667) before any floor.
- **Floors.** From a fresh detached worktree of origin/main at 780c7eba, 3 render processes, 18:36–18:43.
  - 470 renders (5 guitars × 47 parts × 2) plus 8 for this run's own repeat check, 478 in all; 381, 389 and 380 s a shard.
  - The repeat check was exact on both check parts.
  - 0 refusals, 0 reruns, 0 carried guitars.
- **Read.** `python -m learn.scratch_envelope read` ran once, zero renders, from the same worktree.
  - `rows.json` sha256 `fd0a075e2b3bcba7a152aff3777e1512988d4156cd4e8ec5ba471d65da03584b`.
  - `report.json` sha256 `0156a5f06197b4d0078a484d81cae6f600df2f1a31118d71a336ad37ee679fe3`.
- **Audit.** The independent audit (Opus) reproduced every figure, and its verdict was CONFIRMED WITH CAVEATS. It added the zero-render log-spectrum correlations in caveat 1.

## What it cannot show

- **No search gain.** Floors are screens: they say which kind of correction, not what a search would gain from it.
- **No song-only path.** Every correction comes from the true DI.
- **Notes against timbre.** At the magnitude swap's resolution, the two are not separated (caveat 1).
- **One preset, the score only.** The 47 parts have been read many times.
