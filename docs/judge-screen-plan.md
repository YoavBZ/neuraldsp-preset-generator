# The judges we have, on whole presets the ear ranked (S12)

**Status: declared 2026-11-08, before any judge below is computed on these cards.** Owner: the review session, by the agreed split. Ledger `judge-screen`. Results go in [judge-screen-results.md](judge-screen-results.md). Code `learn/judge_screen.py`.

**Why.** The user holds that the score does not follow what the listening tests show. N11 and N12 ([F65, F66](pipeline-fix-plan.md)) found where J0 parts from the ear: mostly between models, on small J0 gaps. The ML session handed this on as a judge-terms brief. On 2026-11-08 the user picked this option of three: screen the judges already built, on the stored clips, CPU only, no fitting, a lead at most. The user's words, in the ML session, on a plan naming it: "Agreed. Let's follow your suggestions."

**What was looked at first, post hoc, unaudited.** Before this plan, J0's stored rows on these 36 cards were read once:
- On pairs the listener rated differently close, J0 orders them as the closeness does 70 of 80 times, 37 of 39 on N12.
- On pairs rated equally close, the forced rank agrees 61 of 86.
- On heard pairs with a J0 log ratio under 0.06, it agrees 8 of 14. Between models only, it agrees 2 of 7.

No other judge has been computed on these cards.

**How this differs from what failed.**
- Judges v2 to v5, `tonal` and EfficientAT's `J-f6` were tuned or screened on pages that moved one control at a time (`judge-ear`, `judge-v5`; F44 to F47, T3.4, S6). Here the ear ranked whole presets that models and the search produced, on the recording's own performance.
- Nothing is fitted here. Every judge is read as stored in its code, with its frozen constants, so all 36 cards are out of sample for every judge.
- Nothing here changes J0. J0 is the ML session's to change.

## Material

The development cards N11 and N12 used, less nothing:

| Page | Cards | Candidates | Clusters | Stored clips |
|---|---|---|---|---|
| F57, `capture-labels` | 10 | S, label, placebo | GOAT player | `captures/ear-check/renders/*/clips.npz` |
| `ear-eat`, pages 1 and 2 | 13 | S, FTm, `M-pcs`, `EW-mix`, label | GOAT player; BKS song | `eat/ear*/renders/*/clips.npz` |
| N12, `ear-wide` | 13 | S, FTm, `M-pcs`, `EW-mix`, label | the DI's band | `ear-wide/renders/*/clips.npz` |

- Cards, ranks and closeness come from `learn/score_ear.py`'s own loaders: `capture_cards`, `eat_cards`, and N12's `cmd_wide` path, with F57's item 8 correction and `ear-eat`'s Recording 2 as N11 and N12 took them.
- Clusters pool across pages by name: GOAT's players are shared by F57 and `ear-eat`. That gives 13 clusters.
- V-real's L0 and N4, `record-match-1`, NS, the panel and every held band stay out.
- The ML session confirmed on 2026-11-08 that N12's DIs (via `score_ear.wide_units`) and F57's clips may be read. The access is read only, nothing copies a `.nam` file, and nothing here depends on the captures staying after this run.

**Audio.** Each stored clip is the held half the judge scored: the reference's window [s0, s1) and each render's [s0 − lag, s1 − lag), in mono, as `ear_vreal.window` cuts it. To give every judge the inputs it takes, each clip is placed back at its offsets in zeros the length of the section. The DI is rebuilt as each page's render step built it: `B.measure(PS.section_audio(di_path, start_s))`, then trimmed. Then every judge runs on the held half, through `knob_ceiling`'s `R.HALVES[held]`.

**The control, before any other judge.** J0 is recomputed this way on every candidate of every card and must match the stored J0 within 1e-3 in |log ratio|.
- A card that fails is out of every row, and is named.
- If more than 3 cards fail, nothing is read, and the plan comes back for a fix.
- The rows compare each judge with this recomputed J0, so every judge reads the same audio.

## The judges, fixed now

| Name | What it is | Its code, unchanged |
|---|---|---|
| J0 | The judge as used: the control, and the baseline | `analysis.aligned.aligned_distance`, defaults |
| v2 | A fixed band set | the same with `bands="fixed"` |
| v3 | One floor from both sides, in Bark | the same with `**JUDGE_V3`, which holds all 18 properties of the [specification](judge-spec.md) |
| J5 | J0 plus a carry-over part for time effects, w_c frozen | `judge_v5.window` and `j5`, w_c as frozen in `v5-screen.json` and the ledger |
| `tonal` | The mean band error, ignoring frame-to-frame changes | `bakeoff_judge.band_errors` and `terms_of` |
| `J-f6` | EfficientAT's layer-6 statistics, level matched by LUFS | `eat_judge.deep_terms`, `mn10_as` on CPU, sds from `wide` |

Any judge that refuses a candidate's window (None or not finite) drops that pair from its rows, and the count is given. J0 is computed on the same pairs.

## Rows

A pair is two candidates on one card. Labels are out of the primary: the search chose them on J0, so a label's J0 is biased low. A judge agrees on a pair if it gives the lower distance to the candidate the ear put closer. A tie in the judge counts one half.

1. **Primary: heard pairs.** These are pairs whose closeness ratings differ, labels out. There are 80 of them. The row is each judge's agreement with the closeness order less J0's, pooled by pairs. It gets a cluster jackknife t, df clusters less one, with a 90% interval and two-sided p, and Holm over the five judges.
2. **All pairs by forced rank,** labels out, 166 pairs: the same contrast.
3. **Within-card order:** the mean over cards of the Spearman between the ear's rank and the judge, labels out, less J0's, by the same jackknife. F57's cards rank two candidates, so as in N11 they stay out of this row.
4. **Labels in:** rows 1 and 2.
5. **By page:** rows 1 and 2, F57, `ear-eat` and N12 apart, described only.
6. **Where they move.** The number of pairs each judge orders differently from J0, and of those how many are heard and how many go the ear's way. Heard pairs under a J0 log ratio of 0.06, given apart. Models-only pairs, given apart.

**Power, said now.** Only pairs where a judge and J0 order differently can move a row. J0 already agrees on 70 of the 80 heard pairs, so the most any judge can gain on row 1 is +0.125. With 13 clusters, the likely outcome is an interval reaching zero whatever is true, and that says nothing against any judge. Undecided is not failed.

## What each reading leads to

Nothing is adopted here, and nothing changes J0.
- **Named for H4's page.** The judge with the highest primary point estimate above zero is named to the ML session before H4's page answers are opened. Its fresh rule on that page is declared then, with the ML session, before anything there is scored. If no judge is above zero, none is named, and H4's page reads J0 alone.
- **A lead.** A named judge whose Holm-adjusted p is under 0.10 is called a lead on these cards. Otherwise it is named for the fresh test only, and called undecided here.
- **Whatever reads here,** the verdict on any judge is the fresh blind page, as the standing rule requires. These cards have been read many times.

**What this can bear.** One listener, 36 cards, 13 clusters, and pages built for other questions. Development material only.

**Cost.** Zero renders, CPU only, since the GPU is the ML session's for H4. No training and no download: `mn10_as` is already local. Output is `PF/eat/judge-screen.json`, well under 1 GB.

## Order of work

1. This plan is reviewed independently, then the ledger entry is written.
2. `learn/judge_screen.py` and its tests are written. The code is reviewed with the control's result before any other judge is read.
3. The screen runs, and its numbers are audited by separate code. The auditor checks the write-up.
4. Write-up, ROADMAP and DOCS-INDEX lines, PR, review, merge. The named judge, if any, goes to the ML session, and the result goes to the user.
