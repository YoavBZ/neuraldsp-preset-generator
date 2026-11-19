# The score against the ear, on today's decisions (the ladder's ear check)

**Status: declared 2026-11-17, after two independent review rounds (approve with changes, then approve). Drawn
2026-11-17 (`phase_lear_draw`), rendered and sat 2026-11-18 to 19, read once and audited 2026-11-19: outcome (a), row 5
([results](ladder-ear-results.md), `phase_lear_outcome`). Cen over S rests on crunch (post hoc); no second sitting.** Ledger `preset-ladder`: `phase_lear` (this declaration, before the draw),
`phase_lear_draw` (the draw file's sha256, written before any judge file is read), `phase_lear_outcome` (after the
read). Code `learn/ladder_ear.py`, tests `tests/test_ladder_ear.py`. Data `PF/ladder/ear/` (`PF` is
`~/ndsp-presets/learn/trusted-data/pipeline-fix`); the pages under `~/ndsp-presets/listening/ladder-ear/`. Parent:
[preset-ladder-plan.md](preset-ladder-plan.md). It runs after the exam page's sitting.

**What the planner read to write this (zero renders):** the ladder's plan and results, its stored report files at pool
and set level only (means, intervals and counts of parts on each side), and the 480 parts' metadata. No single part's
score was opened, and the draw uses none.

## Why

Every decision since the ladder rests on J0, ln(d_row / d_ref) on the held half, below zero closer. By that score, on
the ladder's 480 held-out parts (deciding pool BKS, GOAT and the panel):

| Row | Deciding pool | Parts where J0 puts the first one closer (deciding sets) |
|---|---|---|
| Cen − S | −0.121 [−0.177, −0.065] | 253 of 347 (73%) |
| label − Cen | −0.404 [−0.458, −0.350] | 331 of 346 (96%) |
| model on the stem − Cen (`xl@-3`) | +0.061 [+0.005, +0.117] | 171 of 347 (49%) |
| re-centred on the stem − Cen (`rc-xl@-3`) | +0.008 [−0.042, +0.058] | 196 of 347 (56%) |
| re-centred − raw, on the stem | −0.052 [−0.078, −0.027] | 195 of 347 (56%) |

From these rows: Cen is the candidate start, the model path is not the default, Step 2 stopped, and Steps 5 and 6 were
ranked. None of these presets has been heard. What is known about J0 and the ear: no arithmetic error, and no judge
beats it against the ear ([S12](judge-screen-results.md)). Large gaps agree (F57: labels above S on 9 of 11). Between
close candidates the two agree about two pairs in three (F65). An audible 6 dB bell moves J0 only about −0.03 to −0.04.
The user asked whether the score can be trusted before more rests on it.

**What an (a) would cover, and what it would not.** It covers three reads at gaps of about 0.1 and over:
- Cen over S;
- the label over Cen;
- "the model's preset on the product's stem is not better than Cen" (the model-path default, and branch 1 of Step 2's
  stop rule).

It covers clean and mild crunch only, since the cards' crunch comes from each set's milder half. It does not cover:
- **the next decisions, which are all under 0.05.** Steps 5 and 6's expected gains and the separator ceiling after
  re-centring (−0.035) are all that size. Under 0.05 a score difference stays "not known to be heard" whatever this
  page reads.
- **Step 2's stop as a whole.** Branch 3 rests on two undecided rows, `rc-xl@-3 − cen` and `rc-mix@-3 − cen` (−0.027
  [−0.061, +0.007], where the heard-size clause fired). Only the first is on the page. The backed-mix answer is not
  heard, so the page neither confirms nor reopens the separator-work reading.

**The goal check.** The product must reach the most accurate preset with no person in the loop, so the score is the
only steering it has. This page says whether the three reads above may steer. It converges: one sitting, one read, a
coded outcome, and at most one declared second sitting.

## The question, and what each outcome means

On held-out recordings, with the recorded guitar (the amp track) as the reference and every preset through the part's
own DI, does the ear order S, Cen, the model's answer on the product's stem, the re-centred answer and the label the
way J0 does?

| Outcome | In words | Next (to the user; nothing runs by itself) |
|---|---|---|
| **(a) trusted for these decisions** | The ear hears Cen over S and the label over Cen as scored, and does not hear the model's preset above Cen | The three covered reads stand. J0 may read gaps of about 0.1 and over, on clean and mild crunch. Under 0.05 stays "not known to be heard", so the next decisions are not licensed by this page. An ear read before anything ships stays the rule |
| **(b) the ear disagrees** | The ear inverts a decided score row, or hears the model's preset above Cen | The decisions resting on the contradicted pair are held and re-read by ear. No new score-only decision. A judge fix is declared as its own study (the review session's), fitted on the 36 development cards and tested on fresh ones |
| **(c) not known** | The page could not tell, or the label control was not heard (page or score) | The second sitting declared below, read pooled. If still (c), the write-up says what each interval rules out and the user chooses |

## How this differs from the earlier ear checks

- **F54 (L0, 10 V-real parts; S, FT, D_fix, W):** earlier models, and one far-off arm (W) carried the agreement. No
  fixed preset and no label. Among the close arms agreement was not shown (+0.04 [−0.29, +0.39]).
- **F57 (11 capture parts; label, S, a placebo):** only the largest gap, label against S. No model and no Cen.
- **F65 (N11, 43 stored cards) and S12 (36 cards, five judges):** re-reads of pages built for other questions, read many
  times, post hoc. Their candidates were older readers (FT, FTm, `M-pcs`, `EW-mix`) on the backed mix.
- **F66 (N12, 13 cards):** descriptive by declaration ("no decision rule picks anything"). FTm held most controls at S
  and read a self-built backing. 5 of 13 cards were on songs in W's plugin rows, and what J0 adds read ±0.25.
- **C4, A3 (F82, F83) and the exam page:** model against model, or amp against amp. The exam page holds a centre preset
  (C-pick), but on 10 sealed V-real parts where M and R tie by the score, so it was declared "expected not known". This
  page does not replace it.

**What is new here:**
1. **The presets are the ones today's decisions compare.** Cen has never been on an answered page. The model's answer
   comes from the product's actual input, X-LANCE's stem of a full mix with other guitars (`xl@-3`), not the backed mix
   or a clean track. The re-centred answer has never been heard.
2. **Today's gap sizes sit on one card:** Cen − S about −0.12, the model within ±0.06 of Cen, and the label −0.40 beyond
   Cen as an anchor. Earlier pages held either one large gap or several close models, not both.
3. **A coded outcome tied to the decisions,** declared before any answer. Earlier reads were descriptive.
4. **Out of sample and wider:** every model answer and every Cen comes from a fold that never saw the part. There are
   22 cards in 22 clusters over four sets, against 10 to 13 cards before, sized for the Cen-over-S pair, with the power
   stated.

**Why it may still read (c):** by J0 itself Cen is closer than S on only 73% of parts. So even an ear that followed J0's
sign on every part would show Cen over S on about three cards in four, and 22 cards resolve that about three times in
four (see "Power").

## The cards

**Pool.** The ladder's 480 parts (`full_controls_c3r.read_units(state())`). Every one has already passed the listener's
scope gates: GOAT's ear and heavy pages, the scope page, the capture gates, the panel's ear page and the DI check. Left
out: n12's 12 parts (beside the deciding pool, mostly on heavier bands' DIs), and any part without a lag, a C2 or C2r
label with its fresh render hash, or the ladder's `cen`, `xl@-3` and `rc-xl@-3` answers on the label's search half. No
V-real, reserve, NS or R1 audio is touched.

**The rule, fixed before any score of these parts is read** (`draw`, seeded 20261171). It reads metadata and audio only
and uses no judge value. `full_controls_c3r.state()` loads the C2 and C2r outputs, which carry judge values; the draw
takes only the label's search half and render hash from their own fields, and the answers from the ladder's answer
files, and opens no judge file. The audit checks both. The draw file also stores, per earlier page, how many of its
unit ids match a ladder part, so the "fresh" filter's matching can be checked. **The draw file's sha256 goes into the ledger (`phase_lear_draw`)
before any judge file is read**, and `render`, `page` and `read` refuse a draw file with another hash.
- **Judgeable:** guitar only, with no backing on the page, so the guitar is exposed by construction. Half the cards are
  clean and half crunch. A crunch part enters only from **the milder half of its set** by the stored drive measure:
  `scope/list.json`'s `nl` for BKS and GOAT, `nonlinear_db` for cap1, at or under the median of the set's crunch units
  in the pool. A crunch unit with no measure stays out. The panel has no such measure; its DIs carry the listener's
  "keep". The held half's activity must be at least 0.8 (`capture_labels.ITEM_ACTIVE`), measured on the amp track by
  `ear_vreal.activity`, as N12's draw did, and stored in the plan file.
- **Fresh:** a unit that was a card on an earlier ranking page (F57, `ear-eat` 1 and 2, N12, C1a, C4, A3, H4b) is left
  out. The filter reads unit ids only from those pages' keys, never their scores or answers. BKS and the panel are too
  small to fill without such units, so there a heard unit is taken only after every fresh one of its cell, and the plan
  file counts them.
- **One card a cluster:** GOAT by item, BKS by DI file, the panel by DI file, cap1 by creator. A cap1 card's DI item is
  never a GOAT card's or spare's item, in either sitting. A BKS unit plays on one of its three amps.
- **Spread, 22 first hearings a sitting:**

| Set | Cards | Clean / crunch | Clusters to draw from | Other limits |
|---|---|---|---|---|
| GOAT | 10 | 5 / 5 | 130 items | at most 7 on one player; amps 4, 3, 3 |
| BKS | 4 | 2 / 2 | 8 DI files (4 clean, 4 crunch) | both songs; no amp more than twice |
| Panel | 4 | 2 / 2 | 5 DI files in 4 bands | first sitting: one card a band (the two crunch DIs, Aimee Norwich, one of Jen Hartswick's two) |
| cap1 | 4 | 2 / 2 | 19 creators | one a creator; three amps |
| **All** | **22** | **11 / 11** | | each amp 6 to 8 cards |

- **The direction is the label's.** The label was searched on one half, so the card plays its held half, and every model
  answer is the one read from the label's search half. No choice is left.
- **Spares, in the draw's order:** 2 GOAT, 2 BKS, 1 panel and 2 cap1 a sitting, each set's two one clean and one crunch.
  The panel's one spare takes the first class with a window left, clean first (its four crunch windows fill both
  sittings). BKS's spares sit on the sitting's own DI files, since its clusters are few, else on another DI file of
  their class; a spare never claims a DI file the other sitting needs. A spare replaces a card of its
  set and class only before the page is built, after a failed guard, never after an answer.
- **The second sitting's 22 cards are drawn in the same pass:** GOAT 10 more items, BKS's other 4 DI files, cap1 4 more
  creators, and the panel 4 other windows of its 5 DI files (so the panel's clusters repeat, clustered by DI file when
  pooled). They are rendered with the first and held, and built into a page only if the first reads (c). A cell the
  pool can't fill in the second sitting runs short and is counted, and the 6 to 8 cards an amp still hold; the first
  sitting must fill, or the draw refuses.

**Counted before this declaration** (metadata and amp-track activity only, no judge value, as N12 measured activity
before its draw): 467 parts read, 301 in the pool. Out: 31 under the activity floor, 112 crunch parts over their set's
median, and 23 heard GOAT or cap1 parts. Every first-sitting cell fills. Only 3 of BKS's 4 crunch DI files keep a mild
unit, so the second sitting's BKS has one crunch card and that sitting holds 21. To check that the declared code
completes, the seeded draw was run in memory, once before the PR's review and once after its fixes (both songs on BKS,
the amp limits kept for the second sitting). Each printed only its attempt counts (85 and 17, then 85 and 215) and sizes
(22 cards and 7 spares; 21 and 7), and no card was listed or kept. The draw that counts is the one run from merged code,
written once to the plan file. The earlier pages' matches, by unit id among the ladder's parts in these four sets: F57
10 of 12, `ear-eat` 12 of 12 and 6 of 6, C1a 7 of 14, A3 18 of 18; N12, C4 and H4b none (n12's or batch 3's units).

## The presets on a card

| Tag | Preset | Stored at |
|---|---|---|
| S | the stock start on the part's amp and class | the live menu's S (`pipeline_fix.A_menu_S`), held to the stored S judge (`full_controls_c3r.s_judges`) |
| Cen | the labels' centre for the part's fold, amp and class | `PF/ladder/answers/cen.json` |
| M | R-all's fold answer read from X-LANCE's stem of the full mix | `answers/xl@-3.json`, the label's search half |
| rc | M re-centred onto Cen (`recentre`, the rule variant) | `answers/rc-xl@-3.json`, the same half |
| L | the search's label | the C2 or C2r output's `label` |

Every one is on the part's own amp, so the amp pick plays no part. Presets with identical settings share a letter; such
a pair is left out of its rows and counted. `rc-mix@-3` (the backed mix, re-centred, −0.027 against Cen) is not on the
card: five letters is the limit (the review's ruling), so the page does not cover the row Step 2's branch 2 rests on.

## Renders and guards

- Each preset renders fresh and primed in its own process through the part's DI (`audibility_measure.fresh_render`, the
  DI by `song_bank.measure`), trimmed as the judge renders are, judged on both halves at the part's lag. The held
  window is cut at the lag (`score_ear.h4_window`). This is C4's render path with five presets.
- **The clip must be the judged render.**
  - Cen, M and rc: the fresh render's sha256 must equal the stored one in `PF/ladder/judge/<row>/`. The ladder's replay
    control found 30 of 30 renders bit-equal, so a mismatch is a fault.
  - The label: its sha256 must equal the output's `fresh.label.render_sha256`. **Where it differs, the fresh held J0 must
    equal the stored label judge within `full_controls.START_TOL` (0.005 in log ratio).** That is N12's rule: on N12,
    12 of 16 label renders differed in hash from their stored ones while J0 agreed within 1e-5 (F66's audit note).
    Which guard passed is stored per clip and reported.
  - S: its fresh held J0 must equal the stored one within `START_TOL`.
  - A clip that fails its guard puts its card out for a spare, and that is reported.
- The J0 values in the key are the fresh renders' held-half distances, of exactly these clips. Where the hash matches,
  that is the stored value.
- Launched by house practice: at most 3 render processes (`local_objective._wait_cap`), `setopt no_bg_nice`, PIDs
  recorded, the 31 GB disk guard, and monitoring handed to the executor session.

## The page

- **The exam page's pattern** (`real_song_exam`'s per-item letters and player, `ear_vreal`'s cards, `c1a_ear.artifact_page`):
  a private Artifact whose answers are kept in its db (`answers/<build>`) and read back with `ArtifactData`, with the
  Export text as the fallback. It is usable on a phone, as those pages are, and the intro asks for headphones.
- **A card:** "Record" and up to five blind letters, seeded per card, guitar only. Each clip is the held half (about
  4.5 s), looped, and switches instantly between any two at the same position. No name, set, score or arm appears on the
  page (`page_leaks`).
- **The answer:** a rank from 1 to the card's letter count per letter, **ties allowed** (the same rank for any number of
  letters). Optional, as on C4's page: closeness on the four-step scale, sure or unsure, and a note. One mark, "Can't
  judge this one", takes the card out.
- **Items:** 22 first hearings and 2 repeats, 24 items in all. The repeats are seeded, one clean and one crunch, at
  least 4 items after their first hearing, with every preset group on another letter. At the measured 0.19 MB a clip
  (C4's page: 80 clips in 15.1 MB), six clips an item make two Artifact parts of 12 items, each about 13.7 MB, under the
  16 MB limit.
- **New on this page:** it stores when each card was first played (`t_play`) and last changed (`t_last`), so the next
  plan can cite a measured time a card. No such time is stored from earlier sittings. The first-play stamp is armed
  only once the page's db has connected and restored its stored answers (or failed to), since an answer created by a
  play before the restore would block it and the next save would overwrite the stored answers. A test holds that order.
- **Five letters on a phone:** the card is checked at a phone's width (ranks, ties, the play row) before the page is
  published. A layout that does not fit stops the publish.
- **Read once:** `page` refuses when a key exists, and `read` refuses when a read exists and keeps the raw answers
  beside it. `page` also refuses, writing nothing, when a card a guard put out has no spare left, so a short page is
  never locked in; that goes to the orchestrator.

## Loudness

By house practice level does not decide. Every clip, the Record and each letter, is brought to −23 LUFS on its own
measured loudness, then the whole card is lowered by its largest peak cut (`ear_vreal.level_group`,
`build_data_review.level_clip`). The gains are stored in the key. The product's own loudness step (F84) is not used here:
it matches a preset to S on stock DIs and leaves a median 0.65 dB on the song's DI, while unmatched presets sat a median
8.2 dB off S. J0 matches level itself, so score and ear both judge at equal level.
- **A guard:** after levelling, every letter's loudness is within 0.5 LU of the Record's, or the card goes out for its
  spare.
- **A caveat, stated now:** equal LUFS is not always equal heard loudness between different tones. On F84's page, 12
  matched pairs were heard as the same 6 times, quieter 5 and louder 1, with no bias shown. The letters are seeded, so
  this adds noise, not a lean.

## Statistics, declared before any answer

**Unit and intervals.** First hearings only, one card a cluster in the first sitting. A share counts a tie as one half
(the house rule). Its 90% interval is the delete-one-cluster jackknife t (`score_ear.interval`), since percentile
bootstraps ran narrow here (F65). Clusters carry their set (`goat:item_…`). A pair reads **"heard above"** when its
interval lies wholly above one half, **"heard below"** wholly below, and otherwise **"not known by ear"**. One listener
throughout.

**"Firmly", for every (b) trigger.** With many ties the interval alone can rest on a handful of cards: 19 ties, 3 above
and none below reads "heard above" (lower end 0.504), while the sign test on those 3 gives p 0.125 (the review's
finding; the tests hold this case). So a pair is **firmly** heard above (or below) only when its interval says so
**and** the one-sided sign test on its untied cards gives p ≤ 0.05, which needs at least 5 untied cards all one way.
Rows 2 and 4 below need "firmly". The review asked for this on row 4. It is also applied to row 2's pairs, the same
fault in the other direction; it can only turn a weak inversion into a (c), never an (a). Row 5's pairs keep the
interval alone: the sign test would cost the weak pair power (Cen over S at a 0.73 share: 62% against 78%), and a false
"heard above" there stays at the interval's 5 to 7%. The untied counts are printed beside every pair, and the audit
reads an (a) resting on few untied cards adversarially.

**The pairs in the outcome table** (the first named is the one J0 puts closer, or level):

| Pair | J0 on the pool | Role |
|---|---|---|
| L over S | about −0.5 (Cen − S plus label − Cen; the rows' directions differ, so approximate) | **the label control:** score and ear should both show it. J0 optimised the label, so it controls the page and the score together, not the page alone |
| Cen over S | −0.121, decided | key pair 1 |
| M over Cen | +0.061, decided worse (fragile) | key pair 2 |
| rc over Cen | +0.008, undecided, a gain beyond 0.042 ruled out | key pair 2, the re-centred answer |
| L over Cen | −0.404, decided | key pair 3. It also checks that a preset the search tuned to J0 is heard closer than one it did not tune: the held half removes fitting to the window, not a blind spot the judge has on both halves |

**Per pair, each row** (`pair_row`):
- the ear's share with its interval, and the cards above, tied and below;
- the one-sided sign test on the untied cards;
- J0's mean ln ratio on the same clips with its interval, and on how many cards J0 puts the first one closer;
- on how many untied cards J0 and the ear agree;
- the closeness gap where both are rated.

Holm over the five pairs is beside, on the jackknife t's two-sided p. Every pair is also given on the deciding sets' 18
cards alone (GOAT, BKS, the panel), per set, per class and per amp. cap1's four cards stay in the main rows (other
creators' amps). The other five pairs (M over S, rc over S, rc over M, L over M, L over rc) are reported the same way,
beside.

**Agreement per card:**
- **A1, heard-pair agreement (S12's measure):** of the pairs on a card the ear did not tie, the share J0 orders the ear's
  way, pooled over cards by pairs, with the cluster jackknife interval. It is given labels out (the primary, as S12's,
  and the form row 2 reads) and labels in, since J0 chose the label. S12 read 0.875 [0.803, 0.947] on 80 heard pairs,
  labels out.
- **A2, order within a card (N11's row 1):** the Spearman of the ear's ranks (ties as average ranks) and J0 over the
  card's letter groups, the mean over cards, all candidates and labels out. Earlier pages read +0.5 pooled, then +0.65
  and +0.69. A card ranked all equal has no order and is counted apart.
- **A3, what J0 adds over no audio:** A1 and A2 for a fixed order by preset type (L, then Cen and rc level, then M, then
  S: the pool's J0 order, fixed now; a fixed tie counts a half in A1), and J0's less it. N12 resolved this to ±0.25 on
  13 cards, so it is expected undecided and decides nothing.
- **A4, by the size of J0's gap:** every pair binned by |ln ratio| (under 0.05, 0.05 to 0.15, and over), with the tie
  rate and the agreement on untied pairs per bin. It tests the ladder's 0.05 "heard size" floor. Descriptive.
- **A5, the repeats:** of the pairs on a repeated card, how many the listener ordered the same twice. It bounds what any
  score could agree with.

**How ties count.** In a share, one half. In A1 and A4, a tie is left out of the agreement and counted in the tie rate.
A tie is the listener saying "no difference heard", never a disagreement with J0.

**The outcome: the first row that holds** (`outcome`, coded and tested before the page is published; `read` refuses a
missing pair):

| # | When | Outcome |
|---|---|---|
| 1 | Fewer than 18 of a sitting's first hearings are ranked (22 in the first, 21 in the second; each sitting, when pooled) | **(c), the page failed.** Rows reported, nothing concluded |
| 2 | L over S, Cen over S or L over Cen is firmly heard below; or A1's interval (labels out) lies wholly under one half | **(b), the ear inverts the score** on the named row |
| 3 | L over S is not heard above | **(c), the label control not heard: page or score.** Either the page (the clips, the level, the listener on the day) or J0's own largest gap failing to be heard. The write-up puts it beside F57 (labels heard above S on 9 of 11, closeness +1.45) and A5 (the listener's own consistency), and says which of the two they point to. No other pair is read as evidence either way |
| 4 | M over Cen or rc over Cen is firmly heard above | **(b), the ear hears the model's preset on the product's stem closer than Cen,** where the score reads it level or worse. "The model path is not the default" (stage 2's Q2) and branch 1 of Step 2's stop rule (the re-centred stem against Cen) are held and re-read by ear. Nothing else of Step 2's stop is touched: the backed-mix row is not on the page |
| 5 | Cen over S and L over Cen are both heard above | **(a), for the three covered reads.** With M over Cen heard below, the ear agrees the model sits behind Cen. With it not known, the model is not contradicted, and the interval's upper end says how large an ear preference for the model is ruled out |
| 6 | Otherwise (Cen over S or L over Cen not known, nothing contradicted) | **(c), not known** on the named pair, with what its interval rules out; the second sitting follows |

- (a) covers the three reads and gaps of their size, on clean and mild crunch. It does not show that gaps under 0.05 are
  heard, or that J0 orders close models (A4 and A3 describe that). It does not license Steps 5 and 6 or the separator
  ceiling's reading, which all sit under 0.05, and it does not cover `rc-mix@-3 − cen`.
- If row 4 fires on rc alone, the raw model's decisions stand and the re-centred readout is what is re-read.
- A pair heard above or below by its interval but not firmly triggers no (b). It is reported with its untied count, and
  the table goes on to the next row.
- No row is tuned after the answers. A change after the sitting is a dated amendment, reviewed first.

**Power** (`power_tables`, tested; 60,000 draws, seed 20261173, independent cards, one a cluster, so the jackknife t is
the plain t; recomputed here from the code, replacing the planner's figures):

| True ear share for the pair (ties counted as half) | 22 cards: heard above (firmly) | 44 cards: heard above (firmly) |
|---|---|---|
| 0.90 (F57's and N12's labels over S) | 99.9% (99.6%) | 100% (100%) |
| 0.80 | 94% (87%) | 99.7% (99.7%) |
| 0.73 (the ear follows J0's own sign on every part, Cen over S) | 78% (62%) | 94% (94%) |
| 0.70, with one card in five tied | 70% (63%) | 93% (91%) |
| 0.65 | 48% (31%) | 64% (64%) |
| 0.50 (no preference): a false "heard above" | 6.7% (2.6%) | 5.0% (5.0%) |
| 0.50, half the cards tied | 5.2% (2.4%) | 4.9% (3.4%) |
| 0.50, 85% tied | 5.0% (0.6%) | 4.8% (1.7%) |

- **The label control** (L over S) and L over Cen: about 0.9 expected, so close to certain.
- **Cen over S is the weak link.** On N12, models about 0.11 ahead of S by the score were heard above S on 11 to 13 of
  13 cards, which would put it at 94% or better. If the ear only mirrors J0's part-by-part sign (0.73), 78%.
- **The odds of (a) when the score is right** (the label pairs at 0.9, no true preference between the model and Cen,
  tie rates on those pairs from none to 85%): **0.62 to 0.77 on the first sitting** at a Cen-over-S share of 0.70 to
  0.73, and 0.88 to 0.93 at 0.80. After the pooled second sitting, as declared, 0.82 to 0.93 at 0.70 to 0.73, and 0.93
  to 0.98 at 0.80.
- **Row 4, the model heard above Cen, with the sign test.** One pair with no true preference reads firmly above on 0.6
  to 2.6% of first sittings (tie rates from 85% down to none). Without the sign test row 4's two pairs gave 10 to 13%.
  If the ear truly prefers the model on 8 cards in 10, it fires 87% of the time on 22 cards, and nearly always on 44.
- **The combined false (b) when the score is right,** over every simulated trigger (Cen over S at 0.70 to 0.80, M and
  rc taken as independent, the worst case): **1 to 7% on the first sitting, and 1 to 8% after the pooled second, after
  a (c), as declared.** If both sittings always ran, it would be 4 to 12%. Nearly all of it is row 4; row 2's pairs add
  under 0.1%. A1's trigger is not simulated; with J0 near S12's 0.875 on heard pairs it adds nothing visible.
- **The second sitting** reads all 43 cards (22 and 21) by the same table. Two looks raise a single pair's false "heard above" by
  the interval alone to 8 to 10%, and firmly to 2 to 6% (both looks forced, the same simulation); the write-up says so.
- Cards share players (GOAT), a band (BKS) and a listener, so the real spread is somewhat wider than the simulation's.

## What this read can't say

- One listener, 22 cards, about 4.5 s of guitar alone a card. A real mix masks differences this page exposes.
- The model's input is the ladder's built mix (a lender's backing and other guitars around the part), not a released
  song. The exam page covers songs.
- Crunch comes from each set's milder half, so the most driven in-scope parts are not heard, and an (a) covers clean and
  mild crunch only.
- The backed-mix re-centred answer (`rc-mix@-3`) is not heard, so Step 2's branch 2 and the separator-work reading are
  outside the page.
- GOAT is mostly one player, BKS one band, and cap1's Record is a capture of an amp.
- Every preset but the label holds the effects at S, so nothing here speaks for effects.
- It checks the score on three reads. It does not fix the score, and (a) is not a licence for small gaps: the next
  decisions (Steps 5 and 6, the separator ceiling at −0.035) are all under 0.05.

## Costs (measured rates only)

| Work | Amount | Measured rate | Time |
|---|---|---|---|
| The draw (metadata, held-half activity on audio) | 480 parts | the ladder's lender draw took 31 s | about a minute |
| Renders, first sitting | (22 cards + 7 spares) × 5 presets × 2 (one priming) = 290 | fresh primed renders: 8,640 in 2 h 4 min on 3 processes (ladder stage 1, 05:35 to 07:39), 3,840 in 55 min (C3r), about 4,200 an hour | about 4 min |
| Renders, the second sitting's cards | 280 more (21 cards and 7 spares) | the same | about 4 min |
| Separations, training, downloads | none | | |
| The page | 144 clips encoded, two parts | C4's page: 80 clips, 15.1 MB | a minute or two |
| **The user** | **24 items: 22 cards and 2 repeats, about 120 preset clips and 24 Records** | no time a card is stored; on 2026-11-12 the user sat C4 and A3 together, 40 items and 120 preset clips | **one sitting, planned at 20 to 30 min** |

At five letters a card, 24 items hold about as many preset clips as the C4 and A3 sitting did. More power means the
second sitting, whose cards are already rendered and held.

## Code, commands, order of work

`learn/ladder_ear.py`. Its pure parts (the draw's filters and spread, the guards, the spare rule, the page order, the
tie-aware unblinding, every row, `outcome`, the power simulation, which is checked against `outcome` and the jackknife
interval) are tested in `tests/test_ladder_ear.py`, numpy behind `pytest.importorskip`.

    .venv/bin/python -m learn.ladder_ear draw                       # both sittings' cards and spares (zero renders)
    .venv/bin/python -u -m learn.ladder_ear render --shard k/3      # k = 0, 1, 2; 570 renders, the guards
    .venv/bin/python -m learn.ladder_ear page --sitting 1           # two Artifact parts and the key (zero renders)
    .venv/bin/python -m learn.ladder_ear read --sitting 1 --answers P1 P2   # the rows and the outcome, once
    .venv/bin/python -m learn.ladder_ear power --draws 60000        # the figures above

1. The plan was reviewed independently twice, also against the goal and its stop rule. This declaration, the ledger
   entry and `outcome` are merged before the draw.
2. The draw runs from merged code. Its file's sha256 goes into the ledger (`phase_lear_draw`, its own small change)
   before any render or judge read. An auditor reads the draw for leaks: no judge value used, the "fresh" filter
   reading unit ids only, the spread as declared.
3. The renders and guards run for both sittings' cards. The first page is built, its five-letter layout is checked at a
   phone's width, and it is published privately to the user, after the exam page's sitting.
4. The user sits it. The read runs once, on the orchestrator's go. An independent audit recomputes every row and the
   outcome from the raw answers and the key, and reads a (c) or an (a) resting on "not known" adversarially.
5. The result goes to the user in plain words with the outcome letter. A second sitting runs only on (c).

**Stop rule.** One page, one read, and at most one second sitting read pooled. No third page and no re-draw.

## Settled by the review (2026-11-17)

1. **The size:** 22 cards and 2 repeats now. The second 22 are drawn and rendered in the same pass and held; they are sat
   only on a (c). Sequential costs less of the user's time in expectation.
2. **Crunch from the milder half only:** yes, it is the scope rule; an (a) covers clean and mild crunch only.
3. **Five letters,** keeping `rc-xl@-3`, after the five-letter phone layout is checked. `rc-mix@-3` is not added.
4. **The exam page first.** It is built and the user is sitting it now; this page follows.
5. **cap1's four cards stay** (independent creators and amps); the deciding sets' rows are reported beside.

## Details fixed in the build (for the PR's review)

The planner's draft left these open; each is fixed here before the draw:
- **The label's guard** takes N12's rule where its hash differs (above).
- **Row 2's A1 trigger** reads A1 labels out, S12's form.
- **Row 1 when pooled** needs each sitting to reach 18 ranked first hearings.
- **Spares** match their card's set and class; BKS's sit on the sitting's own DI files, else another of their class,
  never claiming it; the panel's takes the first class with a window left, clean first.
- **The crunch median** is over the set's crunch units in the pool, before the activity and fresh filters; a crunch unit
  with no measure stays out.
- **The second sitting** may run short in a cell, counted, keeping the amp limits; the first may not.
- **BKS's both songs** is enforced by the draw on a full set of BKS cards.
- **Holm** uses the jackknife t's two-sided p.
- **The draw's hash** goes into the ledger by its own small change between the draw and the renders, so the renders run
  from merged code that holds it.
