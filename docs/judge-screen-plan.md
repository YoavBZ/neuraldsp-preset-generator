# The judges we have, on whole presets the ear ranked (S12)

**Status: declared 2026-11-08, before any judge below is computed on these cards, amended the same day after its independent review.** Only J0's control has run, as the review allowed (all 36 cards within 4.5e-4). Owner: the review session, by the agreed split. Ledger `judge-screen`. Results go in [judge-screen-results.md](judge-screen-results.md). Code `learn/judge_screen.py`.

**Why.** The user holds that the score does not follow what the listening tests show. N11 and N12 ([F65, F66](pipeline-fix-plan.md)) found where J0 parts from the ear: mostly between models, on small J0 gaps. The ML session handed this on as a judge-terms brief. On 2026-11-08 the user picked this option of three: screen the judges already built, on the stored clips, CPU only, no fitting, a lead at most. The user's words, in the ML session, on a plan naming it: "Agreed. Let's follow your suggestions."

**What was looked at first, post hoc, unaudited.** Before this plan, J0's stored rows on these 36 cards were read once:
- On pairs the listener rated differently close, J0 orders them as the closeness does 70 of 80 times, 37 of 39 on N12.
- On pairs rated equally close, the forced rank agrees 61 of 86.
- On heard pairs with a J0 log ratio under 0.06, it agrees 8 of 14. Between models only, it agrees 2 of 7.

- No other judge has been read against the ear on these cards. One has been computed: `ear-eat`'s score renders store J0's `tonal` and `cross` on both halves (`eat/score/score-judge`). Nobody has read them on these cards.

**How this differs from what failed.**
- Judges v2 to v5, `tonal` and EfficientAT's `J-f6` were tuned or screened on pages that moved one control at a time (`judge-ear`, `judge-v5`; F44 to F47, T3.4, S6). Here the ear ranked whole presets that models and the search produced, on the recording's own performance.
- Nothing is fitted here. Every judge is read as stored in its code, with its frozen constants, so all 36 cards are out of sample for every judge.
- Nothing here changes J0. J0 is the ML session's to change.

## Material

All of the development cards N11 and N12 used:

| Page | Cards | Candidates | Clusters | Stored clips |
|---|---|---|---|---|
| F57, `capture-labels` | 10 | S, label, placebo | GOAT player | `captures/ear-check/renders/*/clips.npz`, renders only |
| `ear-eat`, pages 1 and 2 | 13 | S, FTm, `M-pcs`, `EW-mix`, label | GOAT player; BKS song | `eat/ear*/renders/*/clips.npz` |
| N12, `ear-wide` | 13 | S, FTm, `M-pcs`, `EW-mix`, label | the DI's band | `ear-wide/renders/*/clips.npz` |

- Cards, ranks and closeness come from `learn/score_ear.py`'s own loaders: `capture_cards`, `eat_cards`, and N12's `cmd_wide` path, with F57's item 8 correction and `ear-eat`'s Recording 2 as N11 and N12 took them.
- Clusters pool across pages by name: GOAT's players are shared by F57 and `ear-eat`. That gives 13 clusters, of which 11 hold a heard pair. GOAT player1 and player2 hold 8 cards each, and the report gives their share of the pairs.
- V-real's L0 and N4, `record-match-1`, NS, the panel and every held band stay out.
- The ML session confirmed on 2026-11-08 that N12's DIs (via `score_ear.wide_units`) and F57's clips may be read. The run also reads the section WAVs those use, `captures/sections/*.wav` and `*.di.wav`, which the ML session confirmed the same day. The access is read only, and nothing copies a `.nam` file. The stored result stands once the captures are deleted, but it can no longer be recomputed then.
- Interpreters: the torch venv (`tools/demucs-venv`) for `judge`, since `J-f6` needs torch, and the main `.venv` for `control` and `report`. Outputs go in `PF/eat/judge-screen/` for all three pages.

**Audio, one alignment for every judge.**
- Each stored render clip is its render's [s0 − lag, s1 − lag) of the held half, in mono, as `ear_vreal.window` cuts it.
- The reference is rebuilt from its source for every card with `P.real_amp_track(sd, track, start_s)`. On `ear-eat` and N12 it must match the stored reference clip within 1e-5 of its peak. F57 stores none.
- Each render clip goes back into zeros the length of the section at [s0, s1). So it lines up with the reference at lag 0.
- The DI is rebuilt as each page's render step built it: `B.measure(PS.section_audio(di_path, start_s))` cast to float32, then to float64, then trimmed to [TRIM_S, TRIM_S + SEC_S). It is then shifted by the lag, so the frames the judge reads before the window are the ones it read.
- Every judge then runs at lag 0 on [s0, s1), with `render_latency` 52, since every amp is Morgan.
- J5's `window` and `J-f6`'s `deep_terms` take no lag. This alignment is how they get one: `J-f6` reads exactly the aligned [s0, s1). J5 is read on the held half alone, where its stored form averages both halves.
- Each card's [s0, s1) must equal `ear_vreal.window` of its held half and stored lag, as in `rec.json`.

**The controls, before any other judge is read.**
- J0 is recomputed this way on every candidate of every card and must match the stored J0 within 1e-3 in |log ratio|.
- A label's stored J0 is the search's in-process value, which its fresh render was held to within 1e-3. A label is held to 1e-3 here too, and a label over it drops only its own pairs. Any other candidate that fails takes its card out of every row, and is named.
- If more than 3 cards are out, nothing is read, and the plan comes back for a fix. This control has run: every card passed, worst 4.5e-4.
- J5's `j0` term must equal the recomputed J0 within 1e-9.
- `tonal` is taken from `aligned_distance`'s own `tonal`, as the model comparison stored it, so it refuses where J0 does. `bakeoff_judge`'s copy must agree within 1e-9 wherever it reads.
- `J-f6` must give 0 for each reference against itself.
- Any of these failing stops the run.
- The rows compare each judge with this recomputed J0, so every judge reads the same audio.

## The judges, fixed now

| Name | What it is | Its code, unchanged |
|---|---|---|
| J0 | The judge as used: the control, and the baseline | `analysis.aligned.aligned_distance`, defaults |
| v2 | A fixed band set | the same with `bands="fixed"` |
| v3 | One floor from both sides, in Bark | the same with `**JUDGE_V3`, which holds all 18 properties of the [specification](judge-spec.md) |
| J5 | J0 plus a carry-over part for time effects, w_c frozen | `judge_v5.window` and `j5` on the held half, w_c and the file checked by `judge_v5.require_frozen` |
| `tonal` | The mean band error, ignoring frame-to-frame changes | `aligned_distance(...).tonal` |
| `J-f6` | EfficientAT's layer-6 statistics, level matched by LUFS | `eat_judge.deep_terms`, `mn10_as` on CPU, sds from `wide` |

A judge that refuses a candidate's window drops that candidate's pairs from its rows. A refusal is None or not finite, and for `J-f6` also an error, whose text is stored. More than 3 `J-f6` errors stop the run, and an error in any other judge stops it, and the count is given. Its contrast with J0 is read on the same pairs. Lower is closer for every judge.

**A baseline with no audio, beside only.** `S-last`: S farthest, otherwise J0's order. On N12 the ear put every model above S, so a judge that only pushes S away gains without hearing anything. It is reported beside each row and is never named.

## Rows

A pair is two candidates on one card. Labels are out of the primary: the search chose them on J0, so a label's J0 is biased low. A judge agrees on a pair if it gives the lower distance to the candidate the ear put closer. A tie in the judge counts one half.

1. **Primary: heard pairs.** These are pairs whose closeness ratings differ, labels out. There are 80 of them, in 11 clusters. The row is each judge's agreement with the closeness order less J0's, pooled by pairs. The order is the closeness's, not the rank's: the report gives how many heard pairs have the two opposite. It gets a delete-one-cluster jackknife t, df clusters less one (10), with a 90% interval and two-sided p, and Holm over the five judges. Beside it: the same contrast weighted by cluster, and split into pairs with S and models-only pairs.
2. **All pairs by forced rank,** labels out, 166 pairs: the same contrast.
3. **Within-card order:** the mean over cards of the Spearman between the ear's rank and the judge, labels out, less J0's, by the same jackknife. F57's cards rank two candidates, so as in N11 they stay out of this row.
4. **Labels in:** rows 1 and 2.
5. **By page:** rows 1 and 2, F57, `ear-eat` and N12 apart, described only.
6. **Where they move.** The number of pairs each judge orders differently from J0, and of those how many are heard and how many go the ear's way. Heard pairs under a J0 log ratio of 0.06, given apart. Models-only pairs, given apart. `EW-mix` is read on EfficientAT's features, so `J-f6` may share its view. `J-f6`'s pairs with `EW-mix` are given apart from its others.

**Power, said now.** Only pairs where a judge and J0 order differently can move a row. J0 already agrees on 70 of the 80 heard pairs, so the most any judge can gain on row 1 is +0.125. With 11 clusters on row 1, the likely outcome is an interval reaching zero whatever is true, and that says nothing against any judge. Undecided is not failed.

## What each reading leads to

Nothing is adopted here, and nothing changes J0.
- **Named for H4's page.** The judge with the highest primary point estimate above zero is named to the ML session before H4's page answers are opened.
  - Ties go to the higher row 2, then the smaller Holm p, then the table's order.
  - If no judge is above zero, none is named, and H4's page reads J0 alone.
  - H4 is the heavy clean-up's retrain ([heavy-cleanup-plan.md](heavy-cleanup-plan.md)). Its blind page, H4b, is the ML session's and will be declared under H4 there. The ML session agreed on 2026-11-08 that it ranks whole presets with closeness on every candidate, S among them, with at least 2 repeats a class, and stores each card's clips, window, lag, J0 and DI source. The rule below applies only if H4b's declaration says so.
  - The fresh rule is fixed now: the named judge alone, less J0, on that page's heard pairs, labels out. Pooled by pairs, with a delete-one-cluster jackknife t by the page's clusters and a two-sided 90% interval (`PS.t90`). If its lower end is above zero, the named judge orders that page's heard pairs better than J0. Otherwise it is undecided there.
  - It reuses this file's pure functions (`pairs_of`, `contrast`, `jackknife`). H4b gets its own loader, held to the same window and J0 controls. Its clusters and any page-specific detail are declared with the ML session before that page's answers are opened.
  - If those answers are opened before this screen names a judge, or the page lacks closeness or whole presets, the named judge waits for the next fresh page that meets these terms.
- **A lead.** A named judge whose Holm-adjusted p is under 0.10 is called a lead on these cards. Otherwise it is named for the fresh test only, and called undecided here.
- **Whatever reads here,** the verdict on any judge is the fresh blind page, as the standing rule requires. These cards have been read many times.

**What this can bear.** One listener, 36 cards, 13 clusters, and pages built for other questions. Development material only.

**Cost.** Zero renders, CPU only, since the GPU is the ML session's for H4. No training and no download: `mn10_as` is already local. Output is in `PF/eat/judge-screen/`, well under 1 GB.

## Order of work

1. This plan is reviewed independently, then the ledger entry is written.
2. `learn/judge_screen.py` and its tests are written. The code is reviewed with the control's result before any other judge is read.
3. The screen runs, and its numbers are audited by separate code. The auditor checks the write-up.
4. Write-up, ROADMAP and DOCS-INDEX lines, PR, review, merge. The named judge, if any, goes to the ML session, and the result goes to the user.
