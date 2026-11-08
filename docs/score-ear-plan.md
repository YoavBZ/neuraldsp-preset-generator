# The score against the ear, on more songs (N11, N12)

**Status: declared 2026-11-07, before anything here is computed by this plan, amended after its independent review.** One post hoc look came first and is stated below. Ledger `pipeline-fix`, `phase_n10b`, `phase_n11`, `phase_n12`. N10b and N11 have run: [F65](pipeline-fix-plan.md). N12 has run, audited 2026-11-08: [F66](pipeline-fix-plan.md). Parent plan: [pipeline-fix-plan.md](pipeline-fix-plan.md). Results go in its findings, F65 on.

**Why.** The user holds that the score is not aligned with what the listening tests show, and wants it improved. The user also asks for test songs beyond GOAT and BKS, including songs used in training, marked as such. A quick post hoc look at the 13 `ear-eat` cards (zero renders, unaudited) read differently: J0's order within a card against the ear's +0.65 [0.38, 0.84] without the label, and each model's side of S the same as the ear's on 11 to 13 of 13. Among the models alone it fell to +0.35 [−0.15, 0.71]. On held real songs F56 had J0 put FTm behind S while the ear could not part them. So the question is narrower than "is the score wrong": where does J0 part from the ear, on how much material, and does it hold on songs outside the two sets everything was built on?

**How this differs from what failed.** Judges v2 to v5 and EfficientAT's terms were tuned or read on pages moving one control at a time (F44 to F47, S6). Here the ear ranks whole presets that models and the search actually produced, on the recording's own performance. Nothing here changes J0. A fix is a later step, the user's call, and must hold on cards it was not fitted on.

**Who runs it.** By the agreed split: the data, J0's calibration and these reads are the ML session's. New judge terms are the review session's, after this. `M-pcs`'s and `EW-mix`'s per-half answers on new units are computed here with code the review session supplies.

## N10b: a correction first

The plan's review found that L1b's draw took `training_ok` for T0's verdict (`capture_labels.py`, `library_dis`). 15 of the second batch's 47 trusted units sit on DIs T0 refused or left unheard: Doom Flamingo 6, Eggy 4, Bernard Purdie Tribute All-Stars 2, Starnes And Shah 2, Timo And The Timezone 1. N10 and F64 read them. `capture_labels.trusted` now drops any unit on a DI T0 did not verify, and refuses a DI it has no verdict on, so every reader sees 32 units on 18 DIs in 9 bands, all 9 crunch units kept. N10 is re-read as declared on those 32, zero renders, and reported beside F64 as its correction, audited. That re-read ran before its ledger entry, stated here: it is N10's declared code with one filter, its answers on the 32 equal N10's, and N10's files are untouched. No first-batch read changes: its DIs are GOAT's, outside T0.

## N11: every blind page we already have (zero renders, zero listening)

**Question.** On every stored blind page where a listener ranked whole presets against a recording of the same performance, how far does J0's order follow the ear's, and where does it part?

**Pages.**

| Page | Parts | Candidates | Set |
|---|---|---|---|
| `ear-vreal`, L0 | 10 | S, FT, D_fix, W | V-real, held, stored rows only |
| `ear-ftm`, N4 | 10 | S, FT, FTm | V-real, held, stored rows only |
| `capture-labels`, F57 | 11 | S, label, placebo | First capture batch |
| `ear-eat`, pages 1 and 2 | 13 | S, FTm, `M-pcs`, `EW-mix`, label | GOAT, BKS |

Beside only, never pooled: `record-match-1` (2026-10-19, 5 parts, S, H, D, C). Its parts are not development ones: Signs and get-out-of-bed are T0 `v_real` parts, Today's The Day is Eat The Feeder's, and Gym Hours, magilla and Today's fail T0 on target and DI. C is a search label and H a J0 search. It is read under the V-real stored read, its clusters merged with V-real's. Its judge is J0's distance (`aligned.py` of 10-10, `K.judge` of 10-14).

The audit of N11 changed two things: F57 leaves out the label page's out-of-scope unit and takes item 8 by the listener's blind correction, and it clusters on GOAT players, since its creators sit on players `ear-eat` shares.

Refused, by name: pages moving one control (`judge-ear*`, `judge-v5`), since that is what failed before; gate pages asking keep or drop (`panel-ear`, `capture-ear`, `goat-ear`, `capture-heavy`); pages played through a stand-in guitar, since J0 needs the same performance (`real-song-check*`, `listening-check`); `arm-a-1`, pairs filtered by J0 itself; `knob-ceiling`, pick-one; `listening-validation`, older than J0.

**V-real.** N11 re-reads stored ear answers and stored J0 values only. No model reads V-real, no new render or new J0. It is logged as a stored-rows read, not a test of any model. The NS songs and the panel are not read. V-real's rows, and `record-match-1`'s, inform this report and never brief a judge term: a fix is fitted on development cards alone, or V-real stops being able to test it.

**Stored J0.** `ear-vreal`, `ear-ftm` and `capture-labels` store J0's held-half distance in their keys. N4's per-card ranks were never stored, so they come from the listener's export, the file its `score` read, copied to `ear-ftm/ear-answers.txt`. `ear-eat` stores none: each candidate joins `eat/score/score-judge`, and the label the search's `best.judge[held]`, the same judge within 0.1% on the checked labels, against gaps of at least 0.8%.

**Rows.** Each part once per page, repeats and out-of-scope cards out, `ear-eat`'s Recording 2 in on the user's ruling.
1. **Order.** Spearman of ear rank and J0 within a card, the mean over cards, per page and pooled. Beside it: without the label, since J0 chose the label; and among models only, leaving out S and the label, where the page has at least three. `capture-labels`' cards with no label rank two candidates, so they read ±1 and stay out of the pool.
2. **Side of S.** For each model, does J0 put it on the same side of S as the ear? Share, per page.
3. **The no-score baseline, per page.** How much order needs no score at all: S last with the rest tied, and a fixed order from each candidate type's mean rank over the page's other clusters, the card's whole cluster left out so a sibling card can't lend it order, labels dropped and ranks taken again among the candidates kept. On `ear-eat` the two read 0.30 and about 0.37 against J0's 0.65, so what J0 adds is the difference, and that is what is read. Each deletion of the jackknife recomputes the baseline, since jackknifing fixed card differences understates: 0.245 against 0.316 on `ear-eat`. A shuffle of J0 within a card has mean 0 at any size, so it gives only the spread, beside.
4. **The ear's own repeat.** Repeats' rank agreement r, where a page has them, says how much order the listener's own repeat holds. Taking ear noise as independent between hearings, a fixed score's ceiling is about √r, not r. It is computed from the pages' per-item ranks. Few repeats, so a rough figure.
5. **Where it parts.** Every pair the two order oppositely, with J0's log ratio and the two closeness ratings, sorted by the size of J0's gap. Beside it: is there a J0 gap under which the ear's order is at chance? Descriptive, and post hoc by nature.
6. **The user's claim, directly.** Models' gain over S by the score (`ln(d_S/d_m)`) against the closeness gap, per card, on pages rating closeness.

**Intervals.** 90%. Clusters by set: V-real by band; GOAT by player; BKS by song, not `ear-eat`'s stored `cluster`, which is the DI there; `capture-labels` by creator; N12 by the DI's band. Bands and parts repeat across L0 and N4, and S and FT share clips there, so the pooled row counts a band as one cluster and L0 and N4 are also given apart. A jackknife t by cluster is primary, df surviving clusters less one, since percentile bootstraps ran narrow here (coverage simulated by the review at 88 to 89%), the percentile beside. On `ear-eat`, by song, J0's order without the label reads ±0.32 on df 4. Undecided is not failed, and no bars.

**Reading.** No decision rule picks anything. The report says in words: where J0 follows the ear, where it does not, and how much material each claim rests on. One listener throughout.

**Cost.** Zero renders.

## N12: a wide page on 9 other bands (the user listens)

**Question.** On songs outside GOAT and BKS, does J0 follow the ear as on the development pages, and do the search's answer and the models sit above S there by ear?

**Why these units.** The second capture batch's 32 units on T0-verified DIs, after N10b: 18 DI files in 9 bands (Ale Lak 7, Storm Of Particles 6, Dark Ride 6, Death Of A Romantic 3, Rebuild The Evil 3, Cnoc An Tursa 2, The Long Wait 2, The Travelling Band 2, Renesans 1). Real songs' performances through captured real amps, each passed by the listener's gates, with a search label, built inputs and an agreed lag. No V-real, NS or panel band and no reserved band is among them, checked by the review against `HELD_BANDS`, so nothing held is spent. The band is the DI's, `player`; `band` on a unit is the capture's creator. One unit, `cap/5pmq8qku9nq#sw50r`, has a non-finite judge on its held half, so it is out of the score's rows and of the draw: a unit with a non-finite held judge for S or the label is refused, by code.

**The training note, carried on every card.** None of this is fresh, and no reader is called unseen.
- W's plugin rows, so FTm and `EW-mix` through W: "seen" is computed from W's `train_ids` through `CB.load_plan`, per unit, song and DI, 15 of the 32 units, about 5 of the 14 cards by the review's count, the draw's own count stated on the report. It is a list, not a split row.
- `M-pcs` and `EW-mix` fit GOAT's and BKS's labels only, so their labels are clean, but their training inputs' 25 pool backings hold these sessions' backings (Ale Lak, Storm Of Particles, Cnoc An Tursa and others), and the fit's check is on DIs alone. W's stored body was chosen on NS loss, which FTm and `EW-mix` inherit.
- No model's real rows hold these units. No capture file is shared with the first batch. That shows new files, not new amps: a different capture of a like amp can't be told from the files.

**Left out, with the reason.** Real amp tracks on training bands: of the bands outside V-real and NS, only Ale Lak ElecGtr03 and The Travelling Band Quicksand ElecGtr1 are verified targets, and the rest fail the bleed rule (A6) or other checks, so trusted data says no. The 15 units of N10b are out. V-real's and the panel's bands wait for the 14-band test, the user's separate decision. BKS's and GOAT's own captures stay out, since the point is other songs.

**Cards.** 14 first hearings in 9 bands, at most 2 a band and then on different DIs, which fills exactly: Ale Lak 2, Dark Ride 2, Rebuild The Evil 2, Storm Of Particles 2, Cnoc An Tursa 2, and 1 each from Death Of A Romantic, The Long Wait, The Travelling Band and Renesans. Classes fixed now: crunch on Ale Lak's 2, Dark Ride's 2, Renesans's 1 and one of Rebuild The Evil's, 6 crunch; the rest clean, 8 clean. Within that, a seeded draw on metadata alone, before any model's answer or score is opened, with amps as even as the units allow. Rebuild The Evil's crunch card is forced to DI 21, so its clean card can take DI 23. Held-half activity was measured first, on the units' audio alone: 31 of the 32 reach `ITEM_ACTIVE`, 0.8, and the one that does not is the refused unit, so no fallback is needed and the fill stands. `draw` measures it again, filters on it and stores every value in the plan file. 2 repeats, seeded, one of each class. 2 crunch spares, the third crunch DI of Ale Lak and of Dark Ride, used in that order only if a crunch first hearing goes out, since on `ear-eat` crunch went out 5 of 11 and 6 crunch cards at that rate would fail the page about one time in four. The direction is each unit's stored search and held half. The listener heard these recordings at the gates, but no candidate on them.

**Candidates.** Each answers from the unit's search half, so no tone of the held half reaches an answer: features are per half, the feature scaling is constant and the centring uses fitted means. Its level does, as in `ear-eat`'s stored answers: `dfix_level` sets the guitar's gain on the whole section's LUFS, and the compressor's threshold comes from the whole mix. N10's answers average both halves and are knobs, so new answers are read:
- S, the stored `s_judge` and setting; the label, the search's stored best.
- FTm: `bakeoff_render.net_answers`' path per search half on the unit's backed input, its 8 fold-and-seed models pooled, every control outside `K.space` at S. A control holds that on BKS and GOAT the path reproduces stored FTm answers.
- `M-pcs` and `EW-mix`: per search half on `cmd_predict`'s recipe, residuals around an all-labels `RcBG` centre per amp and class, built on all of BKS's and GOAT's records, since none exists for captures. The review session supplies this as new code, with a control against stored fold answers, and that code is reviewed independently before any render. `EW-mix` needs a `captures2` embedding, built from variant 0 of these units with no recipe change. The all-labels centre takes `dfix_records(None)`, cycled as each fold's is, so BKS 306 and GOAT 300 from 214 labels, the first 86 GOAT labels counting double. That is the fold recipe unchanged; the fit itself uses each record once. The ridges fit all labels, while each FTm model fits three quarters.
- If `EW-mix` can't be built with no change to its recipe, the page runs with four candidates, says so before any render, and `ear-eat`'s comparison row drops `EW-mix` too.

Each renders fresh through the unit's DI, isolate=True, one priming render, 0.25 s trim, one process per time-effect render as the page code does. A stored J0 and the render's hash must agree before a clip is kept, as `ear_eat` holds. Level matched as `ear_eat`, the group peak cut stored.

**The page.** `ear_eat`'s page and its fixes: blind letters, seeded per card, the recording beside, rank and closeness, sure or unsure, an out-of-scope mark. No score, name or set on the page. 18 items in two parts of 9, since 18 at `ear-eat`'s clip size pass the artifact's 16 MB. The Record line says a real amp or a close capture of one. Answered in place, not in a downloaded copy.

**A page failure, fixed now.** More than 3 of the 14 cards left unfilled after the spares, out of scope or unanswered: rows reported, no conclusion drawn, and N12's reading is held until the user decides. A spare in use makes its band's third card. These units passed a scope gate, but on `ear-eat` crunch went out 5 of 11 and clean 0 of 7, so the page shows the out-of-scope mark as before. A card's marked slip goes to the user, as the Recording 2 ruling did.

**Rows, all with J0 beside the ear.**
- N11's rows 1 to 5 on this page, by the same code.
- By ear: `label` over S, FTm over S, `M-pcs` over S, `EW-mix` over S, `EW-mix` over FTm, `M-pcs` over FTm, as `ear_eat`'s map: rank share, closeness gap. Clustered by the DI's band. Holm over the six rows beside.
- By the score, on all 31 units with a finite held judge, not only the cards: S, FTm, `M-pcs` and `EW-mix` on the units' held half, `ln(d_b/d_a)`, clustered by the DI's band. Reported beside, not a verdict. S and label already stand.
- Beside N10's knob rows, no new knob read.

**Primary.** On this page, what J0 adds: row 1 without the label, less the fixed order's, by card, the baseline leaving out the card's whole band and recomputed at each deletion, with a jackknife t by the DI's band, df the surviving bands less one. Renesans is one crunch card, so its deletion leaves one card fewer, nothing more. Beside it, the same row on `ear-eat`, and the two pages' difference, with SE from the two jackknifes and Welch's df. No model row is primary: none is being picked on this set.

**What each reading leads to.** These go to the user, none runs by itself.
- What J0 adds on this page is clear of zero: J0 orders these songs better than a fixed order of candidates, on this page, and the fix, if any, aims where the two part.
- It reaches zero, by far the likely outcome: this page can't say J0 adds anything here beyond a fixed order. That is not a failure of J0, and the pooled rows and the disagreements are what is left.
- Against `ear-eat`, a drop can't be read as songs alone: this page differs in capture references, v2 labels, how answers are pooled and how far candidates spread. It stays "on this page", and on this size a gap between pages will rarely show, see below.
- The disagreements in N11's development rows and N12 cluster on one kind of part or one judge band: that is the brief for judge terms, which go to the review session as a declared study, fitted on one part of the cards and read on the rest. V-real's rows stay out of it.

**What this can bear.** One listener, 14 cards in 9 bands, self-built backing only for the readers' input, a captured amp rather than a miked room, songs some models may have seen. The primary as declared on `ear-eat` itself reads 0.39, SE 0.43, df 4, [−0.53, 1.31]. By the review's simulation through this code, 14 cards in 9 bands give about ±0.49, and a gain of `ear-eat`'s size shows only 18% of the time. The pages' difference is about ±0.95. So the primary will very likely read undecided whatever is true, and that outcome says nothing against J0. N12's use is descriptive: where J0 and the ear part on other songs, and the ear rows beside. It is not the fresh test, and no model is adopted from it.

**Cost.** About 160 renders for the cards and spares and about 190 for the score on 31 units with their priming renders, at most 3 processes, shared with the review session. Announced first. No training, no download. The disk rule stands, and `.nam` files stay out of git.

**Order of work.**
1. This plan is reviewed independently, then the ledger entries are written.
2. N10b and N11 run and are audited, with the auditor checking the write-up. Their results are reported to the user.
3. N12's draw is built, read by the review's auditor for leaks, then rendered, and the page goes to the user. N12 does not wait for N11's result.
4. The answers are scored and audited, then the two together go to the user with the next steps above.
