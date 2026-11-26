# The note-reading diagnosis: results

Results of `docs/scratch-readerr-plan.md`. Every number here is by the score (J0), on the exact-notes test's bench,
unless said otherwise. The bench is sharper than real songs, so sizes carry over to real songs only as a direction.

## Phase 2b, the downloaded transcribers: RX-undecided (2026-11-26; ledger `phase_scratch_readerr_outcome`; zero renders; audited 2026-11-26 (independent, Opus))

**The question.** Does an open guitar transcriber remove most of Basic Pitch's extra notes on the bench without
losing notes, enough that a priced row could decide it?

**Who was tried.** Three transcribers, installed from hashed locks and pinned checkpoints, checked for unsafe contents
and run offline (`phase_scratch_readerr_tools`):

- YourMT3+ (`ymt3`), with every pitched programme kept (as shipped) or the guitar programmes only;
- the two Riley guitar models (`kong-fl`, `kong-gaps`), each on a 4 × 3 grid of onset and frame thresholds.

Each was read plain and as `+bp`, which borrows loudness and bends from the paired Basic Pitch note. `select` ran on
those 26 `+bp` lists and on Phase 2a's 149 Basic Pitch settings: 175 candidates in all.

**The rule.** The rule was fixed from the deciding row's own numbers before anything was installed. It predicts each
list's gain by the score from its counts on the 40, as g = E·x + M·y:

- x is the share of extras removed and y the share of misses added;
- E = −0.275 and M = +0.277 (intent-to-treat), with h = 0.1305, half the width of E's interval.

A list qualifies only if all of these hold on the 40:

1. extra_rate reads "better";
2. miss_rate, end error and onset error do not read "worse" (sign only);
3. g ≤ −h;
4. it is shipped, or it is its family's cross-set pick and passes on both BKS and GOAT;
5. it does no harm on the real-DI arm;
6. it repeats.

**The code is RX-undecided.**

- 19 lists are better by the mean (g < 0 with extra_rate better), but none qualifies.
- miss_rate reads "worse" on the 40 for all 26 transcriber lists (item 2).
- None of the 175 reaches g ≤ −h.
- Passing-only constants (E −0.220, M +0.293, h 0.149) give no qualifier either, so the code is not
  refusal-sensitive.
- Next, by the table: no priced row; to the user with each candidate's g.

**Each family's best list** (lowest g on the 40; ✓ meets, ✗ fails; "not worse" includes undecided):

| Family | Best list | g on the 40 | BKS | GOAT | 1 extras | 2 misses | 2 ends | 2 onsets | 3 g ≤ −h | 4 | 5 real DI | 6 repeats |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `kong-fl` | `kong-fl-o0.2-f0.3+bp` | −0.124 | −0.173 | −0.015 | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |
| `kong-gaps` | `kong-gaps-o0.2-f0.3+bp` | +0.113 | +0.115 | +0.117 | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ |
| `ymt3` | `ymt3-pitched+bp` (shipped) | +0.379 | +0.253 | +0.638 | ✓ | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| Basic Pitch grid | `grid-o0.6-f0.4-l58.0-m1` | −0.069 | −0.059 | −0.085 | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |
| Basic Pitch shifts | `shift-k4` | −0.032 | −0.028 | −0.041 | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✓ |

- `kong-fl`'s best list comes nearest: −0.1235 against −h = −0.1305. Its gain sits in BKS; on GOAT it is −0.015.
  It is its family's pick on both sets but fails there on g, so item 4 fails too.
- Every transcriber removes 82–95% of the stored re-read's 1,624 extras on the 40, but adds misses:
  - `kong-fl` reads 344 to 575 misses against the re-read's 246;
  - `kong-gaps` 563 to 786;
  - `ymt3` 784 and 899.
- Higher onset thresholds remove more extras but lose more notes, and g rises with them.

**The 19 better by the mean** (g on the 40, lowest first):

| Kind | Lists |
|---|---|
| `kong-fl` (8) | o0.2-f0.3 −0.124, o0.2-f0.2 −0.119, o0.2-f0.1 −0.098, o0.3-f0.3 −0.083, o0.3-f0.2 −0.080, o0.3-f0.1 −0.061 (shipped), o0.4-f0.3 −0.009, o0.4-f0.2 −0.006 (all `+bp`) |
| Basic Pitch grid (8) | o0.6-f0.4-l58.0-m1 −0.069, o0.5-f0.4-l58.0-m1 −0.063, o0.6-f0.4-l58.0-m0 −0.052, o0.5-f0.4-l58.0-m0 −0.049, o0.6-f0.3-l58.0-m1 −0.042, o0.6-f0.3-l58.0-m0 −0.027, o0.7-f0.4-l58.0-m1 −0.022, o0.4-f0.4-l58.0-m1 −0.020 |
| Basic Pitch shifts (3) | k4 −0.032, k3 −0.024, k2 −0.009 |

**The real-DI arm** (79 Guitar-TECHS windows and the 10 lists, note figures only, against Basic Pitch's stored read,
sign only):

- Every transcriber's extra_rate reads "better" in nearly every group.
- `kong-fl`'s miss_rate is undecided in every group at every setting, so it does no harm (item 5).
- `kong-gaps` reads miss_rate "worse" on P1 scales from onset 0.2, on the lists from 0.3, on P1 and P2 from 0.4, and
  everywhere at 0.5.
- Both `ymt3` lists read miss_rate "worse" on P1, P2 and the lists.
- `ymt3-guitar` read no notes at all on 16 real-DI inputs (15 windows, 1 list), where `ymt3-pitched` read 3 to 28.
  The filter is correct. The runner keeps programmes 24 to 31, the same set as mt3-infer's own vocabulary
  (`"Guitar": np.arange(24, 32)`). On those 16 inputs YourMT3+ gave every note a programme outside the guitars.
  The raw programmes are not stored, so which instrument it chose is not known.

**Licences, as recorded** (development use is fine for all; a product question only if one wins):

- `ymt3` is unresolved: two code claims (GPL-3.0 and Apache-2.0), none covers the weights, and the training-data
  licences are not audited.
- `kong-fl` and `kong-gaps` are unclear for product, NC assumed: MIT is claimed with no LICENSE file, and the
  training data includes sold transcriptions and a base model trained on MAESTRO (CC BY-NC-SA).

**A correction to the amendment.** The amendment expected a `+bp` list's timing figures to differ from its plain
list's. They are identical on all 26: `ms_with_bp` copies each note's `on` and `off` and borrows only loudness and
bends. So the counts, onset error and end error are the plain list's. Only the dry figures differ (`logmel`, `env_corr`
and pause error, from the rebuilt guitar).

**What it can't show.**

- g is a straight-line prediction from two measured slopes, never a reading; only a row decides. On the shrunk answer
  E is not shown, so the predicted gain holds for the full answer only.
- The bench prices fidelity to the song as Basic Pitch heard it, and sizes are the exact world's.
- **The bench bias** (the amendment's dependencies and risks). A transcriber with real-guitar priors may refuse the
  bank guitar's notes, and each refusal counts as a miss. That matters here for three reasons:
  - item 2 (misses) is what sinks every transcriber, and it is read on the bench only;
  - on real DIs, `kong-fl`'s miss_rate is undecided in every group, and undecided is not failed;
  - on the 47, most of `kong-fl-o0.2-f0.3`'s misses are chord members: 244 of its 454, against 54 of 302 for
    the stored re-read.

**Cost (measured; zero renders throughout):**

| Step | Wall |
|---|---|
| `tx-gate` (scan, load, keys, 3 × 4 repeats, timing) | 399 s |
| `tx-notes`, three shards (136 inputs × 3 transcribers) | 974 to 1,010 s |
| `tx-score`, three shards (2,063 rebuilds) | 937 to 1,026 s |
| `tx-score --combine` | about 2 min |
| `select` | 3.6 s |

## The `xr-matched` row: XH-both (2026-11-26; ledger `phase_scratch_readerr_xr_outcome`; audited 2026-11-26 (independent, PASS WITH FIXES, wording applied))

**The question.** Do Basic Pitch's extra notes cost the preset within a part, at the exact test's scale?

The row `xr-matched` is an oracle hybrid, diagnostic only. It is the stored re-read of the bank guitar with its extra
notes taken out, and Basic Pitch's own timing, ends and bends kept for the notes it found. Each unpaired re-find whose
chain root is a found note is joined into that note, instead of being dropped.

The row was searched and scored exactly as the exact test's rows (`docs/scratch-search-plan.md` section 15), against the
same records, and read against those rows:

- **E** = G(`xr-matched`) − G(`xn-reread`). Below zero means the preset lands closer without the extras.
- **M** = G(`xr-matched`) − G(`xn-list`). Above zero means the misses and the found notes' timing, ends and bends
  still cost.

**The code is XH-both**, on the answer arm, on BKS+GOAT (the 40), intent-to-treat deciding:

| | On the 40 (deciding) | BKS | GOAT | Clean | Crunch | All 47 |
|---|---|---|---|---|---|---|
| E, intent-to-treat | −0.275 [−0.406, −0.145] | −0.366 [−0.599, −0.134] | −0.184 [−0.324, −0.044] | −0.350 [−0.513, −0.187] | −0.201 [−0.390, −0.012] | −0.345 [−0.600, −0.090] |
| E, passing-only | −0.220 [−0.370, −0.071] | −0.256 [−0.531, +0.018] | −0.184 [−0.324, −0.044] | −0.240 [−0.543, +0.063] | −0.201 [−0.390, −0.012] | −0.308 [−0.571, −0.046] |
| M, intent-to-treat | +0.277 [+0.141, +0.412] | +0.322 [+0.076, +0.567] | +0.232 [+0.096, +0.367] | +0.152 [−0.048, +0.352] | +0.401 [+0.193, +0.610] | +0.315 [+0.207, +0.422] |
| M, passing-only | +0.293 [+0.156, +0.429] | +0.353 [+0.105, +0.602] | +0.232 [+0.096, +0.367] | +0.184 [−0.043, +0.410] | +0.401 [+0.193, +0.610] | +0.325 [+0.217, +0.433] |

- **E passes** (the 90% interval wholly below zero, the mean beyond −0.10), and **M reads "worse"**. That is XH-both:
  the extras cost, and the rest (the misses and the found notes' timing, ends and bends) costs too.
- **Passing-only gives the same code**, so the read is not refusal-sensitive. In passing-only, E still passes.
- **The share sits beside.** −E over reading proper is 0.50 [0.29, 0.72] (Fieller, bounded). Without the refused part
  (which reads as wholly extras) it is 0.43 [0.16, 0.67]; on the shrunk answer 0.37 [−0.21, 0.74]. Of reading proper's
  cost on this bench, the extras make about half on the full answer (0.43 without the refused part; beside, not
  decided). The rest is the misses with the found notes' timing, ends and bends.
- **The checkpoints agree on E:** −0.293 at 50 evaluations, −0.291 at 100, −0.283 at 200. M grows with the search,
  from +0.095 at 50 to +0.227 at 200.
- **Leave-one-cluster-out** (32 clusters) keeps both. E's mean runs from −0.309 to −0.245, with every upper end below
  −0.11. M's mean runs from +0.236 to +0.318, with every lower end above +0.10.
- **The shrunk answer, beside, reads XH-rest.** E is −0.067 [−0.160, +0.025] and M +0.113 [+0.047, +0.180]. Shrunk
  never decides. Passing-only, the shrunk E is −0.007 [−0.122, +0.109] (GOAT +0.033): on the shrunk answer the
  extras' gain is not shown, and its −0.067 comes mostly from the refused part. The extras' cost shows on the full
  answer.

**The refused part.** One BKS part refused its search at the start, twice; J0 refuses its search half. Under S1 it
reads at Cen. It is the part `xn-list` also refused, and the one `xr-build` listed for its pause share.

Its intent-to-treat E is a refusal, not a reading. E is G(`xr-matched`) at Cen (0) less that part's
G(`xn-reread`) (+1.442), so it enters as −1.442. Its M is 0, since both rows read at Cen there. That one value moves
E on the 40 from −0.220 (passing-only) to −0.275. Passing-only, without it, still passes, which is why the code does
not hang on it. The part is not named here: its key holds file names.

**The forward test, beside** (the change in a dry figure, the `xr-matched` guitar less `xn-reread`'s, each against the
bank guitar, against E). No dry figure becomes Phase 2's scoring figure without a further amendment.

| Dry figure | Spearman on the 40 | BKS | GOAT | Sign agreement on the 40 | All 47 |
|---|---|---|---|---|---|
| `logmel` | +0.305 | +0.262 | +0.383 | 0.825 | +0.204, 0.787 |
| `env_corr` | −0.316 | −0.053 | −0.530 | 0.400 | −0.284, 0.383 |

Both lean the expected way in both sets: a drop in `logmel` and a rise in `env_corr` go with a lower E. No interval:
not decided. For `env_corr` the expected sign is opposite, so its sign agreement of 0.400 means 60% of parts lean the
expected way.

**What it can't show.**

- **The joined ends.** The join hands each re-find's end to its note. The joins extend 480 kept notes (from the #629
  review); 380 of them end past the exact partner's end (`xr-build`'s join report). Of the 380, 122 already did before
  the join, against 69% of unextended kept notes (both from the #629 review). The median overrun is 118 ms (from the
  #629 review). 204 run past the as-played end, and 114 past a later same-pitch exact onset, a miss effect counted in M
  (both from the #629 review). The join adds no sounding span beyond `xn-reread`'s, so it does not bias E. 328 of the
  565 joins are re-finds by the anatomy (409 on the nominal list). Left out with the extras: 10 timing and 21
  substitution extras; misses 53 timing and 58 substitution.
- **It is an oracle.** The extras are removed by matching against the exact list, which no transcriber has. The row
  says the extras cost on this bench; it doesn't say a real rule can find them.
- **The bench prices fidelity only.** The bank guitar is the song as Basic Pitch heard it.
- **Sizes are the exact world's.**
- **One seed.**

**Next, by the table (`XH_TABLE`):**

- Phase 2 scores by note error.
- Phase 2b (the downloaded transcribers) runs, under `DOWNLOAD_RULES`.
- To the user.
- Phase 2a's would-picks stay descriptive (`candidates.json`, `phase_scratch_readerr_candidates`). By note error, the
  grid's level set nearest the stored point is onset 0.7, frame 0.5, 58 ms, Melodia on: −0.138 [−0.174, −0.102] on the
  40, sign only, not on J0's scale. That is not acted on until Phase 2's read.
- Note error is the table's declared figure, not one shown to follow the cost (Phase 1: −0.035 pooled, −0.15 BKS,
  +0.08 GOAT, sets disagree). Its Phase 2a would-pick trades extras for misses (1,953 → 378 extras, 302 → 620 misses),
  and XH-both says misses cost too, so no note-error pick is trusted before it is priced.

**Cost (measured).** Every render ran on main's code, from frozen worktrees, at most 3 render processes:

| Step | Renders | Wall |
|---|---|---|
| `xr-check` | 50 | 109 s |
| `xr-search`, three shards | 12,178 | 5,875 to 8,326 s |
| `xr-search`, the one rerun | 4 | 10 s |
| `xr-score`, three shards | 552 | 390 to 433 s |
| `xr-read` | 0 | 72 s |

`xr-build` (zero renders) took 312 s.

## Phase 1 (2026-11-25; ledger `phase_scratch_readerr_frozen`; audited, PASS)

**The code is RX-untracked: no figure is decided.** Note error stays, labelled "fidelity only".

- The four proofs held on 47 of 47.
- The screen reads "no screen".
- Anatomy, on the as-played list: 1,953 extras against 302 misses. Real DIs carry more unclassified extras, 0.422
  against 0.110 per truth note.
- The intent-to-treat "worse" reads (`reread_env_corr`, `extra_rate`) come from the one refused part (+1.442 at Cen).
  They are never a finding.
