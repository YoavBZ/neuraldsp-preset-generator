# The sound gap at the real floor: results (`phase_scratch_voice_outcome`)

Plan: [scratch-voice-plan.md](scratch-voice-plan.md). Ledger `preset-ladder` `phase_scratch_voice`, `_dry`, `_outcome`. Run 2026-11-26; audited 2026-11-26 (independent, Opus): CONFIRMED WITH CAVEATS. Every number is by the score (J0), at one preset (row (b)'s answer). Nothing here is by ear.

## The code: XV-both, by the score

When row (b)'s answer is rendered through the rebuilt guitar `tr-di` instead of the true DI, the score is worse by T = +0.822 [+0.714, +0.930] on the 40. Along the declared chain (`tr-di` → `vc-own` → `vc-cut` → `vc-fin` → true DI), T splits like this:

| Term | What it prices | The 40 | Reading |
|---|---|---|---|
| **S** | real audio inside our note windows (an upper bound) | **+0.501 [+0.399, +0.603]** | worse |
| **N** | our note activity (a lower bound) | **+0.135 [+0.064, +0.206]** | worse (fragile, below) |
| K | the cuts themselves | +0.013 [+0.008, +0.019] | matches |
| F | the finish (`average_balance` alone) | +0.172 [+0.114, +0.231] | worse |
| T | the whole gap | +0.822 [+0.714, +0.930] | worse |

- S and N both read worse, so the declared code is **XV-both**.
- The terms sum to T exactly on every part (largest gap 4.4e-16) and on the 40's mean (2.2e-16).
- **Not cut-sensitive.** N+K is +0.148 [+0.079, +0.218] and reads worse too, so the code with N+K in N's place is still XV-both.
- **Not refusal-sensitive.** Nothing was refused.
- **Not cause-order-sensitive** by the declared rule: the synthesis rules lead N's cause split under both orders (below).
- **Shares of T** (Fieller, `scratch_exact.share`): S/T 0.61 [0.53, 0.68], N/T 0.16 [0.08, 0.26], F/T 0.21 [0.15, 0.27].

**What the table says next.** Both tracks: N's uncovered frames go, by cause, to their tracks as named targets, and E1 and E2 say loosely which kind of sound S is. Before any synthesis, DI-restoration or search-row spend, the unclaimed-groups control (188 renders, its own declaration `phase_scratch_voice_control`) or the user's waiver must be on main. The next step is the user's route call.

## The caveats (binding, from the audit)

1. **N "worse" is fragile.**
   - Without its two largest parts, both BKS, N is undecided: +0.098 [+0.044, +0.151]. Without the largest one it still reads worse: +0.106 [+0.044, +0.168].
   - N is undecided on GOAT (+0.076 [+0.033, +0.119]) and on clean (+0.079 [−0.045, +0.203]).
   - It is concentrated in a few BKS crunch parts with many uncovered frames.
2. **The cause split, under both orders.**
   - Synthesis rules take 66–99% of N's uncovered-frame weight, and note reading takes 1–34%.
   - These are shares of uncovered-frame weight, not of N's distance.
   - Most of the weight is after a mute.
3. **S is an upper bound.** Real audio inside our windows closes at most S. S is not "the bank's sound":
   - at one preset, it also carries any static tone difference a search would absorb;
   - the control (188 renders) or the user's waiver still gates any spend;
   - the unclaimed-attack share shows no link to S (Spearman −0.05), but it covers only one of the note errors the gate can't see (extra attacks); wrong pitches, bends, articulation and level shaping stay inside S.
4. **N is a lower bound for note activity.** N and K also carry `song_bank.measure`'s EQ re-fit to each guitar's own audio, which is not priced.
5. **F costs at real sound.** It is worse on clean (+0.268 [+0.174, +0.363]) and undecided on crunch (+0.076 [+0.046, +0.106]).
6. **E1 against E2 is loose.** The safe line: the level curve is not where S lives, by the score.
7. **By the score (J0) at one preset.** Nothing here is by ear.
8. **Floors don't predict search gain.** No product or search claim follows from this read.
9. **Zero-filled parts can't be told apart from their set.** The zero-filled parts are GOAT and the panel; the parts with real continuation are BKS.

## The terms on the declared splits

| Split | S | N | K | F | T |
|---|---|---|---|---|---|
| **The 40 (deciding)** | **+0.501 [+0.399, +0.603]** | **+0.135 [+0.064, +0.206]** | +0.013 [+0.008, +0.019] | +0.172 [+0.114, +0.231] | +0.822 [+0.714, +0.930] |
| All 47 | +0.429 [+0.351, +0.508] | +0.128 [+0.049, +0.206] | +0.012 [+0.007, +0.017] | +0.183 [+0.096, +0.269] | +0.752 [+0.598, +0.906] |
| Clean 20 | +0.671 [+0.451, +0.891] | +0.079 [−0.045, +0.203] (undecided) | +0.016 [+0.006, +0.025] | +0.268 [+0.174, +0.363] | +1.034 [+0.858, +1.210] |
| Crunch 20 | +0.331 [+0.269, +0.393] | +0.192 [+0.081, +0.303] | +0.010 [+0.003, +0.018] | +0.076 [+0.046, +0.106] (undecided) | +0.609 [+0.542, +0.677] |
| BKS 16 | +0.465 [+0.277, +0.653] | +0.194 [+0.058, +0.331] | +0.011 [+0.003, +0.020] | +0.143 [+0.049, +0.237] | +0.814 [+0.639, +0.989] |
| GOAT 24 | +0.537 [+0.438, +0.635] | +0.076 [+0.033, +0.119] (undecided) | +0.015 [+0.008, +0.022] | +0.201 [+0.123, +0.280] | +0.829 [+0.685, +0.973] |
| Panel 7 | +0.286 [+0.092, +0.481] | +0.112 [−0.145, +0.370] (undecided) | +0.009 [−0.008, +0.027] | +0.204 [−0.092, +0.500] (undecided) | +0.612 [+0.095, +1.129] |

Readings come from `paired_reading`. Unmarked S, N, F and T cells read worse, and every K cell reads matches.

- **Each cluster of the 40 left out (32 reads).** Every read keeps its reading.

  | Term | Range of means |
  |---|---|
  | S | +0.454 to +0.515 |
  | N | +0.115 to +0.150 (lowest lower end +0.045) |
  | K | +0.012 to +0.014 |
  | F | +0.156 to +0.182 |
  | T | +0.780 to +0.841 |
- **The three largest parts per term** (12-hex tags):

  | Term | Parts (set, value) | Their contribution to the 40's mean | The 40 without them |
  |---|---|---|---|
  | S | `a3b1b27272d3` (BKS, 1.167), `8ae994594bad` (BKS, 1.086), `b2ce529e68f9` (GOAT, 1.078) | +0.093 | +0.442 [+0.387, +0.497], worse |
  | N | `4ea260f59ccd` (BKS, 0.947), `f2030431a5bb` (BKS, 0.547), `ddcdb0c10557` (BKS, 0.456) | +0.061 | +0.084 [+0.031, +0.136], undecided |
  | K | `8ad0ce9dc271` (GOAT), `3320de84a198` (GOAT), `c29832ab789c` (BKS), each about 0.06 | +0.004 | +0.009 [+0.005, +0.014], matches |
  | F | `b2ce529e68f9` (GOAT, 0.861), `1cc512e059fb` (GOAT, 0.768), `89cac0bf475c` (BKS, 0.592) | +0.052 | +0.131 [+0.090, +0.171], worse |
  | T | `b2ce529e68f9` (GOAT, 2.013), `c1ea6ef819b3` (GOAT, 1.630), `8ae994594bad` (BKS, 1.435) | +0.121 | +0.774 [+0.680, +0.868], worse |

- **Per part on the 40.** S is positive on all 40 (0.04 to 1.17) and F on all 40. N is negative on 12 (as low as −0.03) and K on 8 (as low as −0.004).
- **The part with the largest length term** (`89b6da562e67`, GOAT, zero-filled) doesn't matter: without it, no end of any term's interval on the 40 moves by more than 0.003, and every reading stays.

## Beside the split

- **E1 and E2.** The level curve is not where S lives, by the score (caveat 6).
  - E1 = ln(d_tr-di / d_vc-env), the level curve: +0.028 [+0.020, +0.037], matches.
  - E2 = ln(d_vc-env / d_vc-own), the rest: +0.472 [+0.371, +0.574], worse.
  - `vc-env`'s gain was clamped at ±20 dB on a median 0.15% of frames, and held at 0 dB under `tr-di`'s 40-dB floor on a median 5.7%.
- **The `avg+mild` floor** (row (c)'s dry guitar at row (b)'s answer): +0.410 [+0.322, +0.498] against the true DI and −0.412 [−0.494, −0.329] against `tr-di`.
- **The unclaimed-attack share** (our onset groups with no true-DI rise of 3 dB within ±20 ms). It does not follow S:
  - median 7.8% on the 40;
  - S on the 20 parts above the median: +0.574 [+0.362, +0.786]; on the 20 at or below: +0.446 [+0.357, +0.535];
  - Spearman with S −0.05 (40 parts).

  Beside, not decided.
- **N and the uncovered frames.** N follows how much of the true DI's playing our notes leave uncovered:
  - median uncovered share 2.3% on the 40;
  - Spearman of N with the uncovered share +0.81;
  - N on the parts above the uncovered median: +0.293 [+0.141, +0.446]; at or below: +0.008 [−0.003, +0.019].

  This is the construction's sanity check.
- **N's uncovered frames by cause,** pooled over the 40. Shares are of uncovered-frame weight, not of N's distance:

  | Order | Synthesis rules | of which after a mute | after a release | skipped notes | Note reading (late onset) | No note nearby |
  |---|---|---|---|---|---|---|
  | Declared (deciding) | 66% | 60% | 4% | 2% | 34% | 0% |
  | Swapped (after an end before late onset) | 99% | 92% | 5% | 2% | 1% | 0% |
  | Declared, no distance limit | 66% | 60% | 4% | 2% | 34% | 0% |

  The synthesis rules lead under both orders, so the route is not `cause-order-sensitive`. The three parts with the most uncovered weight (`f2030431a5bb`, `4ea260f59ccd`, `15f28c5c4310`) hold 12%, 11% and 10% of it.
- **Note ends** (the trace, all 47): 1,693 releases, 1,279 re-plucks, 535 mutes, **0 sample ends**.
- **Zero-filled parts against real continuation** (caveat 9). On the 40, the 24 zero-filled parts are all GOAT and the 16 with real continuation are all BKS, so the split is the set split. Plain means, zero-filled against real continuation (Mann-Whitney p in brackets):

  | Term | Zero-filled | Real continuation | p |
  |---|---|---|---|
  | S | +0.537 | +0.465 | 0.31 |
  | N | +0.076 | +0.194 | 0.24 |
  | F | +0.201 | +0.143 | 0.28 |
  | T | +0.829 | +0.814 | 0.97 |

## What ran

- **Build.**
  - The first build (`build.json` sha256 `55c9e316…`) was superseded: on the 31 zero-filled parts, the zero pad made a hard, unfaded cut that the finish's spectrum fit took into the whole part's EQ. #655 fixed it with the end edge fade at the real end.
  - The rebuild (`52fea1ed…`, `phase_scratch_voice_dry`) ran with zero renders. Its four proofs held on 47 of 47.
- **Floors.**
  - 470 renders (5 guitars × 47 parts × 2) plus 8 for the repeat check, 478 in all, 13:14–13:20.
  - The repeat check is exact: on both check parts, `tr-di` and the true DI repeat their stored floors, distance and render sha256.
  - 0 refusals and 0 carried guitars.
- **Read.** `python -m learn.scratch_voice read` ran once, 13:20–13:22, zero renders, from a detached worktree of origin/main at 1747d24d.
  - Every check held: the proofs, the repeat check, T reproduced from the stored files (per part exactly, and on the 40 equal to the stored read), and the sum.
  - `report.json` sha256 `484906dfd30115ec4f6e529944b9747a8a2b64f7407f39ffd508e01592550255`; `rows.json` sha256 `e428cfafb897d5c99e9176818f0647234eab6fb54db88a09e1c856aa1a51e362`.
- **Audit.** The independent audit (Opus) recomputed every term from the floor records and the stored floors and matched `report.json` exactly. It rebuilt the code by hand: XV-both. The audit's verdict was CONFIRMED WITH CAVEATS.

## What it cannot show

- **No search gain.** Floors don't order like search results: a floor says nothing about the gain a search would get from fixing either side.
- **Timbre against note identity.** S can't separate these inside sounding spans. It is everything inside our windows, including note errors the gate can't see.
- **Only the true-DI world.** Other presets, the ear and product conditions are not covered. Notes, onsets and the judge's DI all come from the true DI.
- **One preset.**
- **The EQ re-fit** of `song_bank.measure` inside N and K is not priced.

## The unclaimed-groups control: results (`phase_scratch_voice_control_outcome`)

Plan: [scratch-voice-plan.md, "The unclaimed-groups control"](scratch-voice-plan.md#the-unclaimed-groups-control-phase_scratch_voice_control). Ledger `preset-ladder`: `phase_scratch_voice_control`, `_control_dry` and `_control_outcome`.
- **Run:** 2026-11-28.
- **Audit:** 2026-11-28 (independent, Opus), CONFIRMED WITH CAVEATS. The audit recomputed every figure exactly.
- **Scope:** every number is by the score (J0), at one preset (row (b)'s answer). Nothing here is by ear.

### The code: XC-stands, by the score

The unclaimed onset groups were dropped from both guitars: from `tr-di`, giving `tr-uc`, and from `vc-own`, giving `vc-uc`. The terms on the 40:

| Term | What it prices | The 40 | Reading |
|---|---|---|---|
| S | ln(d_tr-di / d_vc-own), reproduced from the stored files | +0.501 [+0.399, +0.603] | worse |
| **Sx** | S without the unclaimed groups | **+0.456 [+0.363, +0.550]** | worse |
| **Ux** | S − Sx: what the unclaimed groups hold of S | **+0.044 [+0.017, +0.072]** | matches |
| Ubx | the bank guitar's move, ln(d_tr-di / d_tr-uc) | −0.064 [−0.130, +0.001] | matches |
| Urx | the real-sound guitar's move, ln(d_vc-own / d_vc-uc) | −0.109 [−0.188, −0.030] | better: the drop removed real playing |

- **The code.** Ux reads matches, so the code is **XC-stands**. Its upper end is under 0.10 and its mean under 0.05.
- **Labels and the gate.** `coverage_label` is none: the coverage-clean subset reads XC-stands too. The read is not refusal-sensitive, because nothing was refused. The spend gate opens on this code.
- **Identities.** Ux = Ubx − Urx on every part, to within 2.2e-16. Ux, Ubx and Urx are exactly 0 on the 12 carried parts.
- **Fieller's share** Ux/S: 0.089 [0.035, 0.140].

**What the table says next.** Price the sound routes against S. S stays an upper bound: wrong pitches, bends and articulation stay inside it, and this control addresses only the extra attacks.

### The caveats (binding, from the audit)

1. **XC-stands rests on a mean 0.006 under the 0.05 line.** The sturdy claim is that a heard-size share is ruled out on the 40. Ux is small, positive and not zero: its whole interval lies above zero.
2. **Dilution over-states Ux on the 40.** Quote both subsets:
   - coverage-clean 26: Ux +0.009 [+0.001, +0.018];
   - coverage-moved 14: Ux +0.121 [+0.028, +0.213], where the drop also removed real playing (Urx −0.30).
3. **On clean and on GOAT, Ux reads undecided,** carried by `ea5fc54a8160`:
   - clean 20: +0.069 [+0.013, +0.124];
   - GOAT 24: +0.062 [+0.011, +0.113].
4. **S stays an upper bound.** Sx is not "the bank's sound". At one preset, S and Sx also carry any static tone difference a search would absorb, and the note errors the gate can't see.
5. **The control can't tell an extra attack from a real soft or late one.** 40 of the 161 dropped groups on the 40 have a true rise within ±50 ms of the onset: likely timing errors (a real attack nearby); dropping them removed real playing, which feeds the dilution.
6. **Kept audio is re-levelled on moved parts.** The hiss removal, the finish's EQ re-fit and the −22.9 LUFS step re-run on both guitars without the dropped notes. On the parts with drops, the kept audio's level change outside the dropped spans (`rms_ratio_db`) runs from −3.62 to +0.71 dB on `tr-uc` and from −4.81 to +0.68 dB on `vc-uc`; both lows are on `ea5fc54a8160`. So on those parts Ubx and Urx are not pure note-removal effects.
7. **All by the score, at one preset.** Nothing is by ear, and floors don't predict search gain.
8. **The run.**
   - 140 renders, not the declared about 148, because 4 more `vc-uc` guitars carry.
   - `rows.json` sha256 `172ef12290ca78e0af60cd3ae784dedcaf734f18c2709fa505325c81f3d7d6e9`.
   - `report.json` sha256 `90623d69c6a9333555c5c1d135f7b9221d6079c178108135774073793e76983b`.

### What may and may not be claimed

**May:**
- By the score, on the 40, the unclaimed onset groups do not hold a heard-size part of S. Ux reads matches, at +0.044 [+0.017, +0.072], about 9% of S.
- The sound routes are priced against S, which stays an upper bound.
- Without the unclaimed groups, real audio inside our windows closes at most Sx, +0.456, which still reads worse: the upper bound stays heard-size.
- The share is small, positive and not zero.

**May not:**
- That the unclaimed groups cost nothing: Ux is above zero.
- That the result holds on clean or on GOAT: Ux reads undecided on both.
- That Sx is the bank's sound, or a sound gap.
- That an extra attack has been told apart from a real soft or late one.
- Anything by ear, or any search or product gain.

### The terms on the declared splits

| Set | S | Sx | Ux | Ubx | Urx |
|---|---|---|---|---|---|
| **The 40** | +0.501 [+0.399, +0.603] | +0.456 [+0.363, +0.550] worse | +0.044 [+0.017, +0.072] matches | −0.064 [−0.130, +0.001] matches | −0.109 [−0.188, −0.030] better |
| Coverage-clean 26 | +0.517 [+0.384, +0.651] | +0.508 [+0.373, +0.643] worse | +0.009 [+0.001, +0.018] matches | +0.008 [−0.001, +0.017] matches | −0.002 [−0.004, +0.001] matches |
| Coverage-moved 14 | +0.579 [+0.158, +0.999] | +0.458 [+0.126, +0.790] worse | +0.121 [+0.028, +0.213] worse | −0.181 [−0.364, +0.003] matches | −0.301 [−0.499, −0.103] better |
| All 47 | +0.429 [+0.351, +0.508] | +0.399 [+0.326, +0.472] worse | +0.031 [+0.012, +0.049] matches | −0.045 [−0.089, −0.001] matches | −0.076 [−0.129, −0.023] matches |
| Clean 20 | +0.671 [+0.451, +0.891] | +0.602 [+0.427, +0.778] worse | +0.069 [+0.013, +0.124] undecided | −0.039 [−0.099, +0.021] matches | −0.108 [−0.214, −0.002] better |
| Crunch 20 | +0.331 [+0.269, +0.393] | +0.311 [+0.245, +0.377] worse | +0.020 [+0.005, +0.035] matches | −0.090 [−0.216, +0.036] matches | −0.110 [−0.242, +0.022] matches |
| BKS 16 | +0.465 [+0.277, +0.653] | +0.438 [+0.273, +0.603] worse | +0.027 [+0.001, +0.052] matches | −0.030 [−0.103, +0.044] matches | −0.057 [−0.133, +0.020] matches |
| GOAT 24 | +0.537 [+0.438, +0.635] | +0.475 [+0.371, +0.578] worse | +0.062 [+0.011, +0.113] undecided | −0.099 [−0.214, +0.016] matches | −0.161 [−0.304, −0.018] better |

The coverage-clean parts are those whose held-half uncovered weight the drop leaves exactly unchanged: 26 of the 40 (11 BKS, 15 GOAT), 17 with drops and 9 carried. Their membership was hashed in `phase_scratch_voice_control_dry` before any floor.

### Beside the code

- **Each cluster of the 40 left out:** every reading is kept.

  | Term | Mean range |
  |---|---|
  | S | +0.454 to +0.515 |
  | Sx | +0.415 to +0.470 |
  | Ux | +0.031 to +0.046 (lowest lower end +0.012, highest upper end +0.075) |
  | Ubx | −0.070 to −0.036 |
  | Urx | −0.113 to −0.080 |

- **The three largest parts on the 40:**

  | Term | Parts and values | The 40 without them |
  |---|---|---|
  | Ux | `ea5fc54a8160` +0.69, `c1ea6ef819b3` +0.244, `a3b1b27272d3` +0.227 (all coverage-moved) | +0.019 [+0.010, +0.028] |
  | Ubx | `e8d444a97729` −1.426, `ea5fc54a8160` −0.73, `ddcdb0c10557` −0.336 | −0.018 [−0.053, +0.017] |
  | Urx | `e8d444a97729` −1.498, `ea5fc54a8160` −1.42, `ddcdb0c10557` −0.41 | −0.045 [−0.077, −0.013] |
  | Sx | `8ae994594bad` 1.085, `b2ce529e68f9` 1.078, `3ee6335d235b` 0.977 | +0.427 [+0.343, +0.511] |

  Without `ea5fc54a8160` alone, Ux is +0.031.
- **The 4 parts where only `vc-uc` carries.** On these parts the dropped notes' windows lie inside other notes' windows, so `vc-uc` is byte-identical to `vc-own` and Urx = 0. There Ux = Ubx:

  | Part | Set | Ux |
  |---|---|---|
  | `89b6da562e67` | GOAT | +0.112 |
  | `9c2b0e8c6bea` | BKS | +0.066 |
  | `3ee6335d235b` | GOAT | −0.010 |
  | `90074e8047e2` | GOAT | +0.002 |

  All four are coverage-clean.
- **The drop** (the build, `phase_scratch_voice_control_dry`):
  - on the 40: 161 of 1,464 groups, 204 notes, 198 of them played;
  - on the 47: 173 of 1,748 groups, 222 notes, 216 played.
  - The uncovered share on the 40 rises from a mean 5.6% to 11.9% (median 2.3% to 4.6%).

### What ran

- **Build:**
  - zero renders, 111 s on 3 shards and 121 s with the combine, from a detached worktree of origin/main at 8bc321eb;
  - all seven proofs and the three stop checks held on 47 of 47;
  - `build.json` sha256 `7e97075f…` (`phase_scratch_voice_control_dry`).
- **Floors:**
  - 132 renders plus 8 for the repeat check, 140 in all, in 151 s on 3 processes, from a detached worktree of origin/main at e1ccee29;
  - 12 parts carry both guitars, and 4 more carry `vc-uc` alone (16 `vc-uc` and 12 `tr-uc` carries);
  - the repeat check is exact: on `f2030431a5bb` and `60c856cd5dc4`, the stored `tr-di` and `vc-own` repeat their floors, distance and render sha256;
  - 0 refusals and 0 reruns.
- **Read:**
  - `python -m learn.voice_control read` ran once, zero renders;
  - every check held: the proofs, the repeat check, S reproduced (per part exactly against the sound-gap `rows.json`, and on the 40 to the stored interval), the identity, and zero on the carried parts.
- **Audit:** the independent audit (Opus) recomputed every term from the floor records and the stored floors and matched `report.json` exactly. It rebuilt the code by hand: XC-stands. Its verdict was CONFIRMED WITH CAVEATS.
