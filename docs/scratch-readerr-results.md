# The note-reading diagnosis: results

Results of `docs/scratch-readerr-plan.md`. Every number here is by the score (J0), on the exact-notes test's bench,
unless said otherwise. The bench is sharper than real songs, so sizes carry over to real songs only as a direction.

## The `xr-matched` row: XH-both (2026-11-26; ledger `phase_scratch_readerr_xr_outcome`; audit pending)

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
- **The share sits beside.** −E over reading proper is 0.50 [0.29, 0.72] (Fieller, bounded). Of reading proper's cost
  on this bench, about half is the extras. The other half is the misses with the found notes' timing, ends and bends.
- **The checkpoints agree on E:** −0.293 at 50 evaluations, −0.291 at 100, −0.283 at 200. M grows with the search,
  from +0.095 at 50 to +0.227 at 200.
- **Leave-one-cluster-out** (32 clusters) keeps both. E's mean runs from −0.309 to −0.245, with every upper end below
  −0.11. M's mean runs from +0.236 to +0.318, with every lower end above +0.10.
- **The shrunk answer, beside, reads XH-rest.** E is −0.067 [−0.160, +0.025] and M +0.113 [+0.047, +0.180]. Shrunk
  never decides.

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

Both lean the expected way in both sets: a drop in `logmel` and a rise in `env_corr` go with a lower E.

**What it can't show.**

- **The joined ends.** The join hands each re-find's end to its note. On the bench, the 565 joins leave 380 found notes
  ending past their exact partner's end (`xr-build`'s join report). So `xr-matched` takes the extras away, but some of its
  held notes ring longer than the exact notes do. E prices "no extras, Basic Pitch's own ends", not a clean
  extras-only change.
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
