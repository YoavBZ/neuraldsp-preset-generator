# Pricing the sound gap at the real floor (`phase_scratch_voice`)

Declared 2026-11-26, on the user's route call "price the sound gap first". The planner's plan passed an independent review (Opus, high) with eight binding amendments, which win where they differ from the plan. The orchestrator's call on amendment 1: `vc-own`, `vc-cut` and `vc-fin` are built from the raw section through the part's own finish, so all three share `tr-di`'s finish chain; `vc-env` (beside) comes from `tr-di`. The declaration PR's own review (PASS WITH FIXES) added the swapped cause order beside, tagged refusal reports, and a stop on malformed floor records. Ledger `preset-ladder` `phase_scratch_voice`, then `phase_scratch_voice_dry` and `phase_scratch_voice_outcome`. Code: `learn/scratch_voice.py`, with `learn/voice_build.py` (Unit B) and `learn/voice_floors.py` (Unit C) to follow. Not run.

## Goal

When row (b)'s answer is rendered through the rebuilt guitar `tr-di` instead of the true DI, the score gets worse by T = ln(d_tr-di / d_true). On the 40 that is +0.822 [+0.714, +0.930] (seen). This test splits T into declared parts:

- real audio inside our note windows;
- our note activity (gaps, early ends, late onsets);
- the cuts themselves;
- the finish.

All four are read at the real floor, at zero search cost.

## What was tried before

| Earlier work | What it was | How this differs |
|---|---|---|
| Note-matched replay (`phase_replay*`) | Menu picks through a blurred true DI or a stem; the notes were always true | No rebuilt guitar; no split of the rebuild's gap |
| Exact-notes test (`phase_scratch_exact*`) | The mirror world, where the bank is the truth; D_swap − D* +0.426 by search | Real sound is the truth here, at the floor |
| Tone split (`phase_scratch_tone*`, 846 renders) | Stored answers through one-change guitars | The method's precedent; it priced balance and tilt at row (c)'s answer, never note events |
| Codec ceiling, LOUDAR | Other dry guitars, by search | Not a decomposition |
| rf2 real floor (`phase_scratch_rederive*`) | The four values fitted: −0.003 | Rules the four values out; this test asks about the sample |
| Stage-1 `nr-*` guitars, the GOAT true-notes test | Bank at GOAT's annotated notes | Withdrawn 2026-11-24 as one-sided; not revived |

## The guitars and the chain

A strict "our notes, real sound" guitar can't be built on real parts, because real audio exists only for what the true DI played. So `vc-own` cuts the true DI in place at our note events. It charges gaps, early ends and late onsets. It does not charge extra notes, wrong pitches, or missed notes that fall under one of our sounding notes.

The chain runs in a declared order (amendment 6):

    tr-di  →  vc-own  →  vc-cut  →  vc-fin  →  true DI

S, N and K are priced with the finish on, as `tr-di` is built. F is the finish at real sound. The shares depend on the order only through where the finish sits. The codes read S and N, and no other order runs.

| Guitar | Rule |
|---|---|
| `vc-own` | The raw section (`pretrain_set.section_audio`) gated by our played notes, then the part's finish `p.finish`, then −22.9 LUFS |
| `vc-cut` | The raw section with the worst-case notch at every one of our onset groups, then the finish, then −22.9 LUFS |
| `vc-fin` | The raw section through the finish, then −22.9 LUFS |
| `vc-env` (beside) | `tr-di` times a gain that makes its 20-ms level follow the true DI's |
| `avg+mild` (beside, stored) | Row (c)'s dry guitar, rendered at row (b)'s answer |
| true DI, `tr-di` | Stored: the exact-notes test's real floors (`floors.json`, hashed in `phase_scratch_exact_targets`) |

**The chain (review B1 of Unit B's PR).** `tr-di`'s `compose` finishes n + `END_PAD_S` samples that end in the edge fade, and cuts to n afterwards. A finish on exactly n samples changes the section's end, because `eq_to` filters circularly and `average_balance` continues with zeros. Half B ends at the last sample, so that difference would land in S. So `vc-own`, `vc-cut` and `vc-fin` are built exactly like `tr-di`'s chain:
1. the raw section on the padded length (the file's real continuation past n, else zeros, recorded per part);
2. the gate on the padded timeline;
3. the 10-ms edge fade at both padded ends, on all three, so N and K carry none of it;
4. `p.finish`, cut to n, then −22.9 LUFS.

The true DI keeps its n-length finish, so the length term sits in F. Its size is recorded beside, per part: the held-half RMS ratio and `logmel_distance` between the padded and the pad-off `vc-fin`.

**The end fade (the fix to #653's review).** On 31 parts the file ends at the section and is still sounding at n, so a zero pad made a hard cut there, and the finish's spectrum fit took the cut's leakage into the whole part's EQ. Where the pad is zero-filled, the end edge fade therefore ends at the last real sample, with zeros after it, on `vc-own`, `vc-cut` and `vc-fin` alike. Proof 3 and the length term are read on that gate. Each part records its level at n and whether the fade moved. The first build (build.json sha256 55c9e316…) is superseded and kept as seen.

**`vc-own`.** `scratch_readerr.played_trace` gives every note's span as `synthesise_redo` plays it.
- Each played note opens a window from 2 ms before its onset (`PRE_ATTACK_S`) to its own end.
- The window has a linear fade-in over [on − 2 ms, on] (`NOTE_FADE_IN_S`, amendment 6) and its end kind's linear fade ending at the end: re-pluck 10 ms, mute 30 ms, release 150 ms, sample end 150 ms.
- Notes the synthesis skips open no window.
- Windows combine by maximum, never by sum, because simultaneous notes are the same audio. The 10-ms edge fade (`EDGE_FADE_S`) applies at the padded section's edges, as on every `vc-*` built from the raw section.
- No per-note gain, tilt, tuning or denoise is applied; the cut carries them. One overall gain brings the guitar to −22.9 LUFS, and it is recorded.
- A miss is silent in our gaps and rides through under a sounding note. Extras add nothing.

**`vc-cut`.** At every onset group's first onset, a 10-ms linear fade-out ends at the onset and a 2-ms linear fade-in runs over [on − 2 ms, on]. The two combine by maximum (amendment 6), giving a notch of about −15.6 dB at 1.67 ms before the onset, about 3 ms wide.

**`vc-fin`.** `average_balance(measure(raw))`, as `tr-di`'s finish and on its padded chain, then −22.9 LUFS. The true DI is `measure(raw)` on n samples, so F is `average_balance` plus the finish-length term (amendment 1, review B1). Two proofs:
- **Proof 4.** The same builder with the pad off and no edge fade equals the stored average-balance DI (`note_replay`'s `avg`) brought to −22.9 LUFS by `at_lufs`. Max |difference| / max |pad-off `vc-fin`| must be at most 1e-5.
- **Proof 3.** The padded `vc-fin` equals the padded gate path at all-pass, byte for byte.

**`vc-env`** (beside). Per 20-ms frame at a 5-ms hop, the gain is the true DI's level less `tr-di`'s, in dB, clipped to ±20 dB. It is 0 dB where `tr-di`'s frame is under its own loudest less 40 dB. The gain in dB is linear between frame centres and held at the ends. Then −22.9 LUFS.

Every constant is an existing one in `note_rebuild.py` (`scratch_voice.WINDOWS`, `NOTCH`, `FIN_RULE`, `ENV`).

## The measure

For each guitar, row (b)'s stored, hashed answer is rendered through it (2 renders: a priming render and the kept one). It is scored by `note_replay.half_distance` on the held half against the clean record, with the true DI as the judge's DI at the part's lag, as `rederive_rows.cmd_floor_real` does. Values are paired per part through `scratch_notes.set_rows`. The 40 (BKS+GOAT) decide, and all 47 are reported beside.

| Term | Definition | Meaning |
|---|---|---|
| S | ln(d_tr-di / d_vc-own) | Real audio inside our note windows closes at most S. It is an upper bound and **not a sound gap**: S also holds every note error the gate can't see, such as extra attacks in true sustain, wrong pitches, bends and articulation, and leftover level shaping (amendment 2) |
| N | ln(d_vc-own / d_vc-cut) | Our note activity: a lower bound for notes and timing. It mixes note reading with synthesis rules (amendment 7) |
| K | ln(d_vc-cut / d_vc-fin) | The cuts themselves. Over-stated, because `vc-cut` notches every group while `vc-own` notches only where every window closes (amendment 5) |
| F | ln(d_vc-fin / d_true) | The finish: `average_balance`, and the finish-length term (review B1; its size beside) |

T = S + N + K + F exactly, per part, held to 1e-12.

**One part set** (amendment 3). A part refused in any of the six floors (true DI, `tr-di`, `vc-fin`, `vc-cut`, `vc-own`, `vc-env`) drops from all of them. `set_rows`' pooled mean is linear, so the sum holds on the 40's mean too. `avg+mild` is read beside, on its own.

**Refusals (S1).** The judge's DI is the true DI, so only a silent render can refuse. A refusal reruns once and is reported with `refusal_report`, on 12-hex tags, its kinds taken from each refused floor's own reason. A stored true-DI or `tr-di` floor that is not finite and positive drops its part with an explicit reason. The read is passing-only. The `itt_values` read, with a refused part at 0.0, sits beside the codes only, not the sums. The code is marked `refusal-sensitive` when the two codes differ.

**What a floor can conclude:** where the rendered distance comes from, at a preset that is good for the true DI.

**What it can't:**
- the search gain from fixing either side (bench floors did not order like the D's);
- timbre against note identity inside sounding spans;
- other presets, the ear, or product conditions (notes, onsets and the judge's DI all come from the true DI);
- with one preset, S also carries any static tone difference that a search would absorb;
- `song_bank.measure` re-fits its EQ to each guitar's own audio, so `vc-own` and `vc-cut` each get their own re-fit, and N and K also carry the finish's re-fit, not only the gate and the cuts.

## Outcome table

`XV_TABLE` (`scratch_voice.xv_code`): `paired_reading` of S and N on the 40, the first row that holds. F's reading is attached to every code.

| Code | When | Meaning | Next |
|---|---|---|---|
| XV-anomaly | A build proof or the repeat check fails; T does not reproduce from the stored files; the sum fails on a part; any of S, N, K, F, T has no usable interval or reading; K reads worse or better; or S or N reads better | The construction is off | Stop; to the user |
| XV-both | S worse and N worse | Real audio inside our note windows closes a heard-size part (at most S), and our note activity costs one too (at least N) | Both tracks. N's uncovered frames, by cause, go to their tracks as named targets. E1 and E2 say, loosely, which kind of sound. The spend gate holds |
| XV-sound | S worse, N not worse | Real audio inside our note windows closes at most S. "Dominates" only if N reads matches | E1 against E2 (loosely, sustain against spectrum). The spend gate holds. The search row through `vc-own` runs only on its own declaration and the user's go |
| XV-notes | N worse, S not worse | Our note activity alone costs a heard size under real sound (a lower bound) | Routed by N's cause split, each cause group to its own track as a named target. Note-track candidates may be screened here at 94 renders each; that is a screen only, and adoption needs the note track's own search row. No synthesis spend |
| XV-undecided | Anything else | Not split at the floor; undecided is not failed | If F reads worse, the finish holds it and the held `fs-tone` question returns to the user |

F reading better is possible, so it is not an anomaly (amendment 4).

**N+K beside N** (amendment 5). N+K = ln(d_vc-own / d_vc-fin) is read beside N. The code is marked `cut-sensitive` when it changes with N+K in N's place.

## The spend gate (amendment 2)

Under XV-sound or XV-both, no learned synthesis, DI restoration or search-row spend runs on this test's account until main holds one of these:
- `phase_scratch_voice_control_outcome`: a declared control that drops the unclaimed onset groups from both `tr-di` and `vc-own`. It costs 47 parts × 2 guitars × 2 renders = 188 renders and needs its own declaration, `phase_scratch_voice_control`. The outcome opens the gate only when it carries its `code`.
- `phase_scratch_voice_waiver`: the user's waiver, in the user's words and with the date.

It is coded as `scratch_voice.spend_refusal` and `require_spend`. The gate is necessary, not sufficient: the search row (about 13,100–13,500 renders, about 2 hours, measured on `xf-now`) still needs its own declaration and the user's go. Under XV-notes there is no synthesis spend at all.

**Tightened by the control's declaration (2026-11-28, its review's amendments 3 and 4).** The control's outcome opens the gate only on a declared XC code. It stays shut under XC-anomaly, and the waiver does not open it there. Under XC-notes, and under XC-part marked `coverage-sensitive`, it opens only through `phase_scratch_voice_waiver`. XC-stands, XC-undecided and an unmarked XC-part open it. See "The unclaimed-groups control" below.

**Tightened again on the declaration PR's review (#658, 2026-11-28).**
- **No fail-open.** Under XC-part and XC-notes the control's outcome must carry `coverage_label` (none, or `coverage-sensitive`). Without it the gate stays shut (binding fix 1).
- **A narrow waiver** (the orchestrator's call). `phase_scratch_voice_waiver` opens the gate only when it carries all of these:
  - `user_words`: the user's words;
  - `answers_code`: the XC code it answers, equal to the control outcome's `code`;
  - `date`: YYYY-MM-DD, on or after the control outcome's `date`;
  - `spend_kinds`: a non-empty list of the declared spend kinds (`search-row`, `synthesis`, `di-restoration`) that holds the kind asked.
- **What the waiver can't do.** A waiver without these fields opens nothing. A waiver with no control outcome on main opens nothing either. The control's outcome therefore carries `code`, `coverage_label` and `date`.

This is coded as `scratch_voice.waiver_refusal` (`WAIVER_FIELDS`, `CONTROL_OUTCOME_FIELDS`).

## Beside the read (zero renders)

- **E1, E2.** E1 = ln(d_tr-di / d_vc-env) is the level curve; E2 = ln(d_vc-env / d_vc-own) is the rest. The split is loose, because E1 also takes the level of extra attacks.
- **Fieller's share** S/T (`scratch_exact.share`).
- **The unclaimed-attack share** (amendment 2, `scratch_voice.unclaimed_groups`). Per part, the share of our onset groups with no true-DI rise of 3 dB or more within ±20 ms. In `tr-di` each of these is a fresh bank attack; in `vc-own` the true sustain passes through. The read reports S above and below the share's median on the 40, and the share's Spearman with S. Beside, not decided.
- **N's cause split** (amendment 7, `scratch_voice.cover_figures`). Each uncovered piece of a playing held-half frame is classed at its midpoint by the first rule that holds:
  1. *skipped*: inside a skipped note's [on − 2 ms, max(on, off)];
  2. *late onset*: one of our windows opens within 50 ms after it (`REFINE_S`);
  3. *after a release, re-pluck, mute, sample end or cut*: the last window before it ended within 600 ms (`TILT_ISOLATED_S`), classed by that window's end kind;
  4. *no note nearby*: anything else.

  Beside, the same split is given with no distance limit on rule 3. The figures are pooled over the 40's passing parts. Route groups: **synthesis rules** (skipped, the end kinds) and **note reading** (late onset, no note nearby). Each group is named to its own track with its share, the larger first. The count of sample ends is reported.

  The declared order leans toward note reading: the last 50 ms of every gap before one of our onsets is booked as a late onset with no other evidence, so a 60-ms gap after a release goes wholly to late onset. The declared order stays the deciding split. Beside it, the same split is given with rules 2 and 3 swapped (after an end within 600 ms before late onset). When the two orders name a different larger group, the route is marked `cause-order-sensitive` and names both groups with their shares under both orders. There is no threshold and no dB-rise rule (the review's fix 1, `route_order`).
- **Splits:** clean, crunch and all 47; each cluster of the 40 left out; the three largest parts' contributions (12-hex tags) and the 40 without them; the `avg+mild` floor against the true DI and against `tr-di`.

**The uncovered figure's definition** (amendment 8, `scratch_voice.COVER`):
- the true DI (`note_replay.di_section`) in 20-ms frames (960 samples) at a 5-ms hop (240 samples), by `note_rebuild.frame_levels_db`;
- a frame plays when it is within 40 dB of the section's loudest frame;
- the part's held half: frame centres in [a + 0.25, b + 0.25) s of the section, which is A 1.0–5.5 s or B 5.5–10.0 s on the trimmed timeline;
- covered by the windows [on − 2 ms, end] of every played note;
- the headline is each playing frame's uncovered sample share; the whole-frame share is reported beside.

## Phases, each verified before the next

1. **Declare** (this PR, zero renders). Code, tests, this doc and the ledger key. Verify: the tests pass, the table guard holds, no private strings.
2. **Build** (`learn/voice_build.py`, zero renders). Verify on 47 of 47 parts:
   - the rule off rebuilds `tr-di` byte for byte;
   - the trace equals `tr-di`'s stored report;
   - an all-pass window gives the padded `vc-fin` byte for byte;
   - the pad-off builder equals the stored `avg` at −22.9 LUFS (review B1);
   - beside, as stops: the raw section measures to the true DI, and `tr-di`'s unfinished synthesis sounds only inside the trace's windows.

   Hash PR: `phase_scratch_voice_dry`. **Done 2026-11-26**, rebuilt after the end-fade fix (#655), zero renders, 150 s on 3 shards. The four proofs, `raw_is_true_di` and `synth_inside_gate` held on 47 of 47. The 16 real-continuation parts are byte for byte the first build's; the 31 zero-filled parts get the end fade at n. Beside, the length term inside F has a median held-half logmel of 0.024 on all 47 (0.014 zero-filled, 0.060 real); the largest is 0.80, on one GOAT part, its cause not established. The first build (55c9e316…) is superseded and kept aside.
3. **Floors** (`learn/voice_floors.py`, 478 renders). Verify: on the two check parts (the first BKS and the first GOAT part by key), `tr-di` and the true DI repeat their stored floors, distance and render sha256.
4. **Read** (`python -m learn.scratch_voice read`, zero renders, once). It verifies, before the code is read:
   - T reproduces from the stored files;
   - the sum holds per part to 1e-12;
   - each cluster left out;
   - the three largest parts' contributions.
5. **Audit**, then the results PR with `phase_scratch_voice_outcome`.

## Cost (measured rates only)

- **Renders:** 5 rendered guitars × 47 parts × 2 = 470, plus 8 for the repeat check: 478 in all. `avg+mild` was rendered only at answer (c) and Cen, so it is rendered again here.
- **Time:** about 160 renders a shard. At the real floor's rate (32 renders in 106–112 s) that is about 9 minutes; at the bench floors' rate (160 in 363–366 s), about 6.
- **Disk:** about 370 MB for four guitar sets (4 × 47 × 492,000 samples × 4 bytes), against 39 GiB free and the 31 GB guard.

## Files (`PF/fs/voice/`, each written once)

| File | Writer | Holds |
|---|---|---|
| `build.json` | Unit B | `proofs` (`rule_off_is_tr_di`, `trace_is_tr_di_report`, `all_pass_is_vc_fin`, `vc_fin_is_avg`, each held of 47), `proofs_hold`; per part `guitars` (each built guitar's and `avg+mild`'s `file_sha256`, `audio_sha256`), `gain_db` (`vc-own`'s), `unclaimed` (`unclaimed_groups`), `cover` (`cover_figures`), `ends` (counts by kind), `pad` (real and zero continuation samples), `length_term` (review B1), `support`; `checks` (`raw_is_true_di`, `synth_inside_gate`); `scratch_readerr.py`'s blob sha and `played_trace`'s source sha256 |
| `build-parts/<part>.json` | Unit B | one part's build record, written by `build --shard`; `--combine` folds them into `build.json` |
| `dry/<guitar>/<part>.npy` | Unit B | the four `vc-*` guitars, float32 |
| `floors/<part>.json` | Unit C | `guitars`: per rendered guitar only (never the stored true DI or `tr-di`) `held`, `audio_sha256`, `dry_sha256` (the build's `audio_sha256`), `refused` (a reason or none), `reran`, `carried_from`. A `held` that is missing, non-finite or not positive without `refused` stops the read |
| `floors-first/<part>.json` | Unit C | the first-pass record of any part with a refusal, in the same shape as `floors/`. The read never reads it. The main pass skips the part; `--rerun` reruns its refused guitars once and writes the part's one `floors/` record |
| `repeat/<part>.json` | Unit C | on the two check parts, `tr-di` and the true DI against their stored floors; `holds` |
| `rows.json`, `report.json` | the read | the terms, the code, the figures beside (a figure that cannot be formed reads "not computable"); part keys appear only as 12-hex tags, refusals included |

## Guards

Every command refuses unless this checkout runs main's code and keys:
- the code: this module, the later units' files and the pinned imports (`scratch_search.py`, `scratch_notes.py`, `scratch_exact.py`, `note_rebuild.py`, `note_transcribe.py`, `note_replay.py`, `pretrain_set.py`);
- the keys: the `phase_scratch_voice*` keys only;
- main must hold `phase_fs_draw`, `phase_fs_answers_stem`, `phase_scratch_exact_targets`, this declaration and the keys the command reads.

The prefix sits outside every guarded prefix. `scratch_readerr.py` is the note track's file and is not pinned: only the build calls `played_trace`, and the build's proofs re-check it.

## Dependencies and risks

- **A pinned module under change.** The note track is editing `scratch_readerr.py`. Each step runs from a fresh worktree of main, and the trace proof re-checks behaviour.
- **Ledger conflicts.** Both tracks edit one ledger file, so their PRs merge one at a time.
- **One preset.** S also carries any static tone difference that a search would absorb.
- **Privacy.** Part keys hold file names, so git gets counts and 12-hex tags only.

## Seen before the declaration

From the planner's zero-render probe (in memory, from a frozen worktree at 96b2e7fc), the review's zero-render checks (at 7ded1a6c) and stored results:

- **Stored:**
  - T is +0.822 [+0.714, +0.930] on the 40 (the review's plain mean is +0.823).
  - Row (b) reproduces on all 47 parts.
  - D_swap − D* is +0.426 [+0.290, +0.562].
  - The rf2 real floor is −0.003.
  - Answer (b) loses +0.161 through the clip-free DI.
- **The planner's probe:**
  - On 47 of 47 parts the two build proofs hold, and the trace-and-gate pass took 55 s in one process.
  - Our notes leave a median 3% of the true DI's playing frames uncovered on the held half (quartiles 1.4% and 11.8%, max 31%; 10 of the 40 above 10%). That figure's frame, hop and floor were not recorded.
  - Cut artefacts in the dry domain are log-mel 0.16–0.19, against `tr-di`'s 13–17, on 4 parts. The review did not verify this.
  - `vc-own`'s overall gain is 0.0–0.15 dB.
- **The review:**
  - Uncovered frames on 8 deciding parts, by the definition above: median 4.0% by sample share (3.6% by whole frames), quartiles 1.8–5.9%, max 27.6%.
  - Unclaimed onset groups on the 40: median 7.8% (quartiles 2.0–14.6%, max 67%), by the definition in `scratch_voice.UNCLAIMED`.
  - On the 8 traced parts, release and re-pluck were most of the ends, and none had a sample end.

## Done test

`phase_scratch_voice_outcome` is on main with one audited XV code, and S, N, K and F are reported with their intervals and their limits.

## The unclaimed-groups control (`phase_scratch_voice_control`)

Declared 2026-11-28, on the user's route call "Control, then price routes". The planner's plan passed an independent review (Opus, high) with eight binding amendments, which win where they differ from the plan. The orchestrator's calls: keep "drops" literally (the reviewer agrees); rename the terms as amendment 8 asks; take the review's non-binding notes 2–5 and 7. Ledger `preset-ladder` `phase_scratch_voice_control`, then the hash PR `phase_scratch_voice_control_dry` and the results PR `phase_scratch_voice_control_outcome`. Code: `learn/voice_control.py`. Not run.

### Goal

The read was XV-both. S is +0.501 [+0.399, +0.603] on the 40, by the score. This control measures how much of S our unclaimed onset groups hold, so the sound routes are priced against the right figure. An unclaimed group is one with no true-DI rise of 3 dB within ±20 ms of its first onset (`scratch_voice.UNCLAIMED`). The control's outcome opens the spend gate.

### The drop rule, one for both guitars

The flags are build.json's `unclaimed.flags` (hashed in `phase_scratch_voice_dry`). They are recomputed and must be equal. A dropped note is any note of a flagged onset group. Dropped notes are not played in either guitar. The record stores the dropped group indices, never −∞ levels.

| Guitar | Rule |
|---|---|
| `tr-uc` | `compose`'s steps on the same notes, bank, ring, loudness option, finish and T, with the dropped groups' levels at −∞ dB, so the dropped notes add exactly zero. The steps are `_synth`, `denoise_above` and `voice_build.chain` (compose's tail, byte for byte). Placement, sources, variety, bends, tilt and every kept note's end and gain stay `tr-di`'s. No new synthesis code |
| `vc-uc` | `voice_build`'s gate path on the same padded raw section, with the dropped notes' trace records marked not played, so they open no window. Same padded chain, end fade (`real_end`), finish and −22.9 LUFS |

- **T is not re-fitted.** Tuning, mutes, tilt and the kept groups' levels stay `tr-di`'s.
- **Kept notes stay cut.** Kept notes that end at a dropped note's pluck stay cut in both guitars, as the shared trace has them.
- **The whole-signal steps are part of the counterfactual** (amendment 1). On `tr-uc` the hiss removal, the finish's EQ re-fit and the −22.9 LUFS step run again; on `vc-uc` the finish and the LUFS step do. So "every other note stays byte for byte" holds only before the hiss removal. Per part, for both guitars, the finished audio's change outside the dropped spans (held half) and the level step against the parent are recorded beside. The level step (`level_step_db`) is only `at_lufs`' residual step, since both guitars end at −22.9 LUFS; the real level change of the kept audio is `outside_change`'s `rms_ratio_db` (#658's review).
- **Why not the alternatives.** No fade-in rule on a sample bank removes only the attack. Editing the note list re-sources about 15% of the kept notes. Merging into a same-pitch note still sounding applies to few dropped notes and needs a forked synthesis.

### What it reads

The floors are read as in the main test: row (b)'s answer, the held half, the true DI as the judge's DI. Values are paired per part through `set_rows`; the 40 decide, and all 47 are reported beside. The terms are renamed so that none reuses an old term (amendment 8):

| Term | Definition | Meaning |
|---|---|---|
| Sx | ln(d_tr-uc / d_vc-uc) | S without the unclaimed groups |
| Ux | S − Sx | What the unclaimed groups hold of S |
| Ubx | ln(d_tr-di / d_tr-uc) | The bank guitar's move |
| Urx | ln(d_vc-own / d_vc-uc) | The real-sound guitar's move; below zero means the drop removed real playing |

- **Identity.** Ux = Ubx − Urx exactly, per part, held to 1e-12. Ux, Ubx and Urx are exactly 0 on every carried part.
- **One passing set** (amendment 6). The set runs over `tr-di`, `vc-own`, `tr-uc` and `vc-uc`. Each refusal reruns once (S1). A part refused in any of the four drops from every term, and refused parts are reported.
- **N needs no new guitar.** Against the stored `vc-cut`, Nc = N − Urx exactly, so Urx is N's re-read.
- **S is reproduced** per part from the stored files against the main test's `rows.json` (its sha256 the outcome key's), and to +0.501 [+0.399, +0.603] on the 40.

### Outcome table

`XC_TABLE` (`voice_control.xc_code`): `paired_reading` of Ux and Sx on the 40, the first row that holds.

| Code | When | Meaning | Next for route pricing |
|---|---|---|---|
| XC-anomaly | A proof, the repeat check or an identity fails; S does not reproduce from the stored files; Ux ≠ 0 on a carried part; any of Sx, Ux, Ubx, Urx has no usable interval; or Urx reads worse (amendment 5) | The construction is off | Stop; to the user. The gate stays shut |
| XC-stands | Ux reads matches or better | A heard-size part of S from the unclaimed groups is ruled out, by the score | Price the sound routes against S. S stays an upper bound |
| XC-part | Ux worse and Sx worse | The unclaimed groups hold a heard-size part, and one remains without them | Price against Sx as the lower figure and S as the upper (dilution pulls Sx down; amendment 4). Ux goes to the note track as a named target, with Ubx and Urx |
| XC-notes | Ux worse, Sx not worse | Without the unclaimed groups, real audio in our windows is not shown to close a heard-size part | To the user before any sound-route spend; the gate opens only through the waiver. The unclaimed groups are the first target |
| XC-undecided | Anything else | Not decided; undecided is not failed | Price against S as the upper figure, with Sx beside |

- **S stays an upper bound in every case** (non-binding note 6). Wrong pitches, bends and articulation stay inside S; the control addresses only the extra attacks.
- **Dilution.** Both guitars losing the same playing pulls Sx toward 0 and pushes Ux up, so XC-stands is the safe direction. The same mechanism can produce the XC-notes pattern and biases Sx low under XC-part.
- **`coverage-sensitive`** (amendment 4).
  - The coverage-clean parts are those whose held-half `uncovered_weight` is exactly unchanged by the drop. Carried parts are included and counted separately. Membership is written into the hashed build.json before any floor.
  - The code is also read on the coverage-clean deciding parts. When that code differs from the 40's, the read is marked `coverage-sensitive`. A subset whose intervals can't be formed reads XC-anomaly there, so the label is set.
  - Under XC-part and XC-notes, a coverage-sensitive code goes to the user with both subsets, not to the code's figure, and the gate opens only through the waiver.
  - Both subsets' Ux, Ubx, Urx and Sx are always reported.
- **The spend gate** (amendment 3, and #658's review). See "The spend gate" above. The outcome key carries `code`, `coverage_label` and `date`. Where a waiver is needed, it must answer that code, on or after that date, for the spend kind asked.

### Phases, each verified before the next

1. **Declare** (this PR, zero renders). Verify: the tests pass, the table guard holds.
2. **Build** (`python -m learn.voice_control build --shard k/3` for k = 0, 1, 2, then `--combine`; zero renders, 47 parts). A failed proof or check stops before the part writes anything:
   - `flags_are_builds`: the recomputed flags equal build.json's;
   - `rule_off_is_stored`: with no group dropped, the builder gives `tr-di` and `vc-own` byte for byte (their stored sha256), on all 47;
   - `trace_holds`: the trace equals build 2's stored report and build.json's, and `tr-uc`'s own synthesis report has the same counts;
   - `outside_dropped_same`: `tr-uc`'s synthesis before the hiss removal equals `tr-di`'s byte for byte outside the dropped notes' spans (amendment 1 scopes it there);
   - `gate_outside_same`: `vc-uc`'s gate equals `vc-own`'s byte for byte outside the dropped notes' window spans, and is at most `vc-own`'s everywhere (amendment 2);
   - `synth_inside_gate`: `voice_build`'s check on the control's pair: `tr-uc`'s synthesis before the hiss removal sounds only inside `vc-uc`'s windows;
   - `drop_is_additive`: `tr-di`'s synthesis equals `tr-uc`'s plus the dropped-only synthesis, within 1e-9 of its peak (non-binding note 5);
   - as stops beside: the raw section measures to the true DI, the pad and the coverage reproduce build.json's.

   Recorded per part: the groups and notes dropped, the uncovered share before and after, coverage-clean, the kept notes cut by a dropped pluck, the dropped groups with a true rise within ±50 ms, and amendment 1's beside figures. Then the hash PR, `phase_scratch_voice_control_dry`.

   **Done 2026-11-28:** zero renders, 111 s on 3 shards, 121 s with the combine. All seven proofs and the three stop checks held on 47 of 47.
   - **Dropped:** 161 of 1,464 groups on the 40 (204 notes, 198 played) and 173 of 1,748 on the 47 (222 notes, 216 played).
   - **Carried:** 12 parts carry both guitars. On 4 more, `vc-uc` is byte-identical to `vc-own`, so about 140 renders remain, against the declared about 148.
   - **Coverage-clean:** 26 of the 40 (11 BKS, 15 GOAT; 17 with drops, 9 carried), as the review's probe expected.
   - **The uncovered share on the 40:** a mean of 5.6% before the drop and 11.9% after (median 2.3% and 4.6%).
   - **The kept audio's level change outside the dropped spans** (`rms_ratio_db`) on the 31 deciding parts with drops:
     - `tr-uc`: median +0.06 dB, from −3.62 to +0.71;
     - `vc-uc`: median +0.00 dB, from −4.81 to +0.68.

     Both lows are on `ea5fc54a8160`, the part whose coverage the drop moves most.
   - **Build hash:** build.json sha256 7e97075f….
3. **Floors** (`python -m learn.voice_control floor --shard k/3`, then `--rerun` for any refusal). `voice_floors`' body runs on the control's own world (amendment 7): its own guitars, stored carry sources (`tr-di`, `vc-own`), repeat guitars and paths under `PF/fs/voice/control/`, so the main test's `repeat/` records never stand in. Verify first: on the two check parts, the stored `tr-di` and `vc-own` repeat their stored floors, distance and render sha256 (8 renders). Byte-identical guitars carry their parent's stored floor and name it.
4. **Read** (`python -m learn.voice_control read`, zero renders, once). Before the code, it verifies that S reproduces per part from `rows.json`, that Ux = Ubx − Urx to 1e-12, and that Ux is exactly 0 on carried parts.
5. **Audit**, then the results PR with `phase_scratch_voice_control_outcome`.

### Cost (measured rates only)

- **Renders:** 12 parts have no unclaimed group, so both guitars carry. 35 × 2 guitars × 2 = 140, plus 8 for the repeat check: about 148.
  - `scratch_voice.CONTROL_RENDERS` (188, pinned in the main declaration) is the ceiling with no carry, 2 guitars × 47 × 2.
  - With the repeat check the ceiling is 196.
- **Time:** the main floors ran 478 renders in 389 s on 3 processes, so 148 is about 2 minutes. The main build took 126–135 s a shard.
- **Disk:** about 185 MB, against 38 GiB free and the 31 GB guard.

### Files (`PF/fs/voice/control/`, each written once)

`build.json` (with the coverage membership), `build-parts/<part>.json`, `dry/tr-uc/` and `dry/vc-uc/`, `floors/`, `floors-first/`, `repeat/`, `rows.json` and `report.json`. The main test's files under `PF/fs/voice/` are only read. Git gets counts and 12-hex tags only.

### Limits

- **Timing** (non-binding note 7). The control can't tell an extra attack from a real soft or late one. The unclaimed groups with a true rise within ±50 ms of the onset are timing errors, not extras. They stay a declared limit, counted per part beside.
- **Coverage.** Dropping removes real playing too, so the read reports the two guitars' moves separately and carries `coverage-sensitive`.

### Names (grepped)

On origin/main at da4e0e22, in docs/, learn/, tests/ and the ledger (hits inside `.json.gz` blobs not counted):
- No hit for Sx, Ux, Ubx, Urx, `tr-uc`, `vc-uc`, `XC-`, `XC_TABLE`, `xc_code`, `fs/voice/control`, `coverage-sensitive`, `coverage_clean`, the new proof names or `phase_scratch_voice_control_dry`.
- `voice_control` appears only inside the declared keys `phase_scratch_voice_control` and `_control_outcome`.
- `synth_inside_gate` is `voice_build`'s existing check, reused by name for the same check on the control's pair.
- The plan's Sc, U, Ub and Ur were renamed because "Sc" collides with 5B.1b's "P2a-Sc" and "P-Sc", and "U" with rederive's "in-U".

### Seen before the declaration

From the planner's two zero-render probes (in memory, from a frozen worktree at 1747d24d, whose `learn/` equals main's) and the review's zero-render probe over all 47 parts. Where the two differ, both are given; the definitions follow.

- **Groups:** 173 unclaimed groups of 1,748 on the 47, and 161 of 1,464 on the 40 (both). 69 of the 161 lie in the held half (planner). 12 parts have no unclaimed group on the 47, 9 on the 40 (review).
- **Notes dropped:** 204 on the 40, 198 of them played; 222 and 216 on the 47 (review; the planner's played counts agree).
- **Coverage:**
  - Dropping lifts the uncovered share on the 40 from a mean 5.6% to 11.9% (median 2.3% to 4.6%). 28 parts move by at most 0.005; 12 move by 0.022 to 0.87 (both).
  - The coverage-clean subset is 26 of the 40: 11 BKS and 15 GOAT, 17 with drops and 9 without. Its S mean is 0.498, against 0.527 on the other 14 (review).
  - Two parts dominate the coverage loss: `ea5fc54a8160` (8 of 12 groups unclaimed, uncovered 6% to 93%, S 0.75) and `e8d444a97729` (+0.70) (review).
- **Kept notes cut by a dropped pluck:** 30 on the 40 (both).
- **Bank attacks:** the bank's dry guitar shows a 3-dB rise at 108 of the 161 (both). Even after the full drop, 39 of the 108 still show a rise from other notes (review).
- **Fade-in:** attacks left after a linear fade-in are 96, 89 and 77 of the 108 at 10, 20 and 50 ms (planner), or 97, 91 and 79 (review, whose fork leaves out tilt).
- **Re-sourced:** a filtered placement re-sources 413 of 2,714 kept notes on the 40 (planner), or 404 (review).
- **Mergeable:** 20 of 204 dropped notes (planner), or 12 (review).
- **Window state at the unclaimed onset:** open through 115, closing 19, absent 27 (planner), or 118, 11, 32 (review).
- **Timing:** 40 of the 161 have a true rise within ±50 ms (planner).
- **Synthesis at −∞:** before the hiss removal, the output outside the dropped spans is byte-identical on 35 of 35 parts with drops, and the compose report is unchanged. After `denoise_above` it is identical on 0 of 35; the change outside the spans reaches 2.3% of peak (median 0.24%) (review).
- **Replication:** flags, the trace report and the uncovered share equal build.json's on 47 of 47 (both).

**Definitions** (non-binding note 2; the review's, where the planner's rule was not recorded):
- **Window state:** at each unclaimed group's first onset t, over the other played notes' windows [on − 2 ms, trace end): *open through* when a window is open at t and the latest such end is after t + 3 ms; *closing* when every window open at t ends by t + 3 ms (cut at this pluck); *absent* when none is open.
- **Mergeable:** a dropped played note with a kept played note of the same pitch sounding at its onset (that note's on < this onset < its trace end).
- **Re-sourced:** a kept played note whose (string, fret), under `synthesise_redo`'s placing run on the list with the dropped notes removed, differs from its placing on the full list.
- **Fade-in point:** a linear fade-in of 10, 20 or 50 ms from each dropped note's first sample (its window start, on − 2 ms), in the synthesis before the hiss removal, cut to n. An attack still reads when the faded guitar has a 3-dB rise within ±20 ms of the unclaimed onset (`unclaimed_groups`' rule) where the unfaded one had.
- **Timing:** a true-DI rise of 3 dB or more within ±50 ms of the group's first onset (`REFINE_S`).

### Done test

`phase_scratch_voice_control_outcome` is on main with one audited XC code, and Ux, Ubx, Urx and Sx are reported with intervals on the 40 and on both coverage subsets.
