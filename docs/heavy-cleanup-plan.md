# Too-heavy recordings out of the plugin rows and the test sets (H1 to H3; H4 to follow)

**Status: declared 2026-11-08, the user's yes ("Go ahead for the rest", 2026-11-08, on the proposal of 2026-11-07), before any render, measure or answer here is read. Amended after its independent review: the line's population and rule, the effects list, W's own rows, the render counts, opt-in exclusions.** One look came first and is stated: the review measured the goat-heavy page's 22 heavy recordings and showed how the existing marks fall by bin (for example 8 heavy of 10 in [3, 5) dB) before the rule was amended, and the top bin's merge-down rule was written knowing [5, 7) holds 2. No keep-or-drop answer had been read. Ledger `pipeline-fix`, `phase_h1` to `phase_h3`. H4 goes in the ledger when its detail is declared. The line comes from the keep-or-drop page (`phase_scope`, `learn/scope_page.py`), which the user is answering. Nothing is deleted: every step writes exclusion lists that only new runs read. Results go in [pipeline-fix-plan.md](pipeline-fix-plan.md), F67 on.

## Why

The user asked to clear recordings that are too heavy or distorted out of training and testing, so they can't hurt either. The keep-or-drop page covers the labelled GOAT and BKS recordings, the real rows. It does not cover:
- W's plugin rows, the base every current network trains on.
- The test sets: V-real's 11 parts, the panel's pairs and NS's plugin rows.

The capture sets were screened by ear on their own pages. The backing pool has no guitar on it.

A first read of D_CC's kept rows on the 8 training songs found them more driven than the real labelled recordings. It took 2,640 rows, zero renders, with `nonlinear_db`'s meter at the plugin's latency of 52 samples. On the 293 rows with no time effect, spring or room mic on (a room on either cab; under H2's active-cab rule it is 313 rows, 57%, 29% and 5%):

| | At or past −2.91 dB | Past 0 | Past +3 |
|---|---|---|---|
| The 293 plugin rows | 59% | 30% | 5% |
| GOAT's and BKS's 316 labelled recordings | 45% | 19% | 1.3% |

The meter counts energy that doesn't follow the DI frame by frame as drive. So a tail from a reverb, delay, tremolo, doubler, the amp's spring or a room mic reads as drive, and those rows can't be read as they are.

**How this differs from what failed.** Arm P dropped the wide draws and tied. D_CC against D_F5 swapped songs and was undecided, leaning worse. Both chose rows by how they were drawn or by song. This chooses by how driven each row's sound is, on the line the listener sets.

**The meter reads the same on both kinds, near the line.** This is the review's check, zero renders:
- Within ±6 dB, the DI as fed against the raw DI moves the measure by 0.15 dB at the 95th percentile on plugin rows and by 0.12 dB on real ones.
- Lag 52 against each row's own lag moves it by 0.12 dB. On real recordings, lag 0 against each one's own lag moves it by 0.28 dB at the 95th percentile, 3.8 dB at most.
- The scale has no effect on the measure, and both sides measure 480,000 samples after the 0.25 s trim.

## The line (fixed now, before any answer is read)

**Who counts.** Every labelled GOAT and BKS recording at or over −3 dB with an answer. Recordings under −3 dB aren't used, so the line can't fall below −3 dB.
- The keep-or-drop page's answers, with the marks the page carries: earlier scope marks and the ear-eat cards.
- The goat-heavy page's 34 recordings (22 heavy, 12 keep). Those 22 were removed before labelling and are not on `scope/list.json`. They are measured the same way, with zero renders.

**Answers.**
- Keep is keep. Too heavy is heavy.
- "Not sure" is heavy, as the page told the listener ("Not sure counts as dropped") and as the goat-heavy page counted it. Treating it as neither is reported beside.
- An ear-eat card with no scope mark counts as keep, as `merge_marks` has it. Leaving those cards out is reported beside.

**Clusters.** The DI: a BKS DI track, a GOAT item. A recording's weight is one over its cluster's count among the recordings the fit uses.

**The rule.** A non-decreasing (isotonic) fit of heavy, as 1 or 0, against the measure, each recording weighted by one over its cluster's count. The line is the lowest measured value at which the fit reaches one half. If the fit never reaches one half, there is no line, and only the heavy bands' rule below applies.

**Reported beside, not as bars:**
- The line's 90% interval from a cluster bootstrap: 2,000 resamples, seed 20261108, with the share of resamples that have no line.
- The binned form: 2 dB bins from −3 dB. A bin with fewer than 8 recordings or fewer than 4 clusters merges up, and the top bin merges down. The line is the lower edge of the first bin whose share, weighted as above, reaches one half.

The line, its interval and the bins go to the user before any exclusion is written.

## H1: does the dry path change only what it should? (pilot, 150 renders)

**The dry twin.** A row's own setting with reverb, delay, tremolo and the doubler off, the amp's spring at level 0 and both room mics off. The spring is an amp knob, and the room is part of the cab. Both are named here, since they are not drive. A variant of `cc_build.render_target` checks the full twin against the plan first, as it does now. It then asserts that the dry setting differs from it only in these keys. Each render is a fresh process per target, isolate=True, one discarded priming render and a 0.25 s trim. The audio goes to a new folder, and the stored targets are untouched.

**Rows.** From W's training rows (`bakeoff.plugin_set()`, 1,787 rows) outside the heavy bands, 1,753 rows, seed 20261108:
- 10 rows with only reverb on, 10 with only delay, 10 doubler, 10 tremolo, 10 spring and 10 room on an active cab: 60 rows rendered dry.
- 10 rows with none of these on, rendered again as stored.
- 5 rows with an effect on, rendered again with the effects on.

**Reported.**
- The shift, the stored measure less the dry one, by family, with the worst negative shift.
- The margin m: 0.5 dB, or the worst negative shift if that is larger in size. Single-switch rows may not bound the shift where switches combine; H2's audit covers that.

**Checks that stop H2 if they fail.** The 15 renders again as stored must reproduce the stored target, bit for bit or with a residual under −90 dB of the target's energy. Stored renders have done so before: 12 of 12 in `phase_5c_lag_diagnostic`.

## H2: W's plugin rows (after the line)

**The rows.** W's 1,787 training rows: the rows FTm's base trained on. 34 of them are on Ale Lak and Storm Of Particles, which go out by the proposal the user approved: the two heavy bands of the October sittings. FS is not used by W and is out of this step. NS is under H3.

**Which rows are rendered dry.** Every row with any dry switch on, a room counting only on an active cab, whose stored measure is at or past the line less m. An audit then runs on the 2 dB window below, from line − m − 2 dB to line − m: 30 rows seeded from it, or all of them if it holds fewer, are rendered dry. If any reaches the line, every row in that window is rendered dry and the audit moves to the next 2 dB down. It stops when an audit is clean or no rows are left. On W's rows a window holds 124 to 256 rows, so each widening adds at most about 512 renders. Rows with no switch on keep their stored measure.

**Out.** Every row at or past the line, by its dry measure, or its stored measure where no switch is on. The networks' own targets stay as they are, effects included: the dry renders only measure.

**Reported before anything is trained.** What is left by amp, class (`base`), draw mode, band and section. If any amp-and-class cell of W's rows loses more than half its rows, the user decides before H4.

**Renders.** 1,543 of the 1,753 rows have a switch on, a room counting only on an active cab. Each row rendered dry takes 2 renders, the target and its priming render, at a margin of 0.5 dB:

| Line | Rows rendered dry | Renders |
|---|---|---|
| −3 dB | 1,291 | about 2,580 |
| −1 dB | 1,123 | about 2,250 |
| +1 dB | 867 | about 1,730 |
| +3 dB | 632 | about 1,260 |

The audit sample adds 60 renders. The D_CC build ran about 115 s a section of 13 to 14 targets with their others, at 3 processes. At most 3 render processes on the Mac, shared with the review session and announced first. The disk guard stands.

**The exclusion lists are opt-in.** They are a pinned ledger key, like `phase_3_doubles`, read only by H4's new run tags. `recipe_inputs`, `real_labels` and `goat_labels` don't change for anyone else, so no stored run's guard trips and no other session's read moves. The review session is told before the key exists.

## H3: the test sets (after the line; a separate declared step; no model result is read)

Measured only after the line is set.
- **V-real's 11 parts:** each part's amp track against its DI, on the sections V-real's reads use, through `nonlinear_db`.
- **The panel:** every heard unit's pairs in `docs/panel-v1-pairs.json`, through `nonlinear_db`. `PANEL_DI_LIKE` (Guitar-TECHS P3, Dahka Band) is out already: their amp tracks are near copies of the DI. A measure of the recordings alone is not a model read, so `phase_5d_panel_reads` stays at 2. It is logged as a declared data touch on the panel's entry.
- **NS's 383 rows,** the ones W selects on: first measured as stored, zero renders, since the first read left NS out, then H2's path and rule, with no page. 347 of them have a switch on, so at most about 700 renders plus audits.

**The page.** Real recordings at or past the line go on a short blind keep-or-drop page with `scope_page`'s rule: the amp track alone, one tap each, and only Keep stays in. Only an earlier answer to a scope question counts as a mark: an earlier out mark sends the recording to the user like any other V-real exclusion, and no other verdict, such as a panel ear page's or a model page's, counts. The listener has heard these parts before beside model outputs. So each test recording sits among 2 development recordings at the nearest measures, kept GOAT and BKS ones whose answers are only checks, page seed 20261109.

**Exclusions.** Exclusions are lists, as in H2. Any V-real part out goes to the user, read by band, since Eat The Feeder is 3 of the 11. Each test set's earlier reads are restated, with and without the excluded parts, in a later write-up. This step reads none of them.

## H4, fixed points only (declared in full and reviewed again before any training)

- **Two arms, each with new run tags,** since `cmd_train_ft` refuses other plugin rows than W's:
  - W retrained on H2's rows, then FTm's tuning on the rows the keep-or-drop page left.
  - The old W with FTm's tuning on the cleaned real rows. This one says which half of the cleaning any change comes from.
  - FTm's recipe is otherwise unchanged: folds, seeds, masks.
- **NS is W's selection set,** the NS-best state FTm starts from. The retrained W selects on NS less H3's NS exclusions, and that use of NS is selection inside H4, not a test read.
- **The comparison:**
  - By the score, on the held halves of GOAT's and BKS's folds, on the units both models keep, with dropped units reported apart.
  - By ear, on a blind page of whole presets beside S, with the score beside.
  - Effect sizes with 90% intervals, by class, so a heavy minority's effect on clean parts shows.
- **Cost.** FTm's 18 runs took 136 MPS minutes, and W's two took about 10 minutes each. The user's training yes of 2026-11-06 covers it. One MPS job at a time, announced first.

## What this can bear

- **Real amps against the plugin.** The line comes from one listener's answers on real amps, applied to plugin renders. The meter reads alike on both, but a plugin amp at a given measure might not sound as driven as a real one at the same measure.
- **What the dry renders measure.** They measure each row's drive, not what the networks heard. A row kept here can still carry a heavy reverb.
- **What isn't measured.** The other guitars in each D_CC mix are not screened, and neither is drive inside an effect, such as a delay's tape drive.
- **Rooms.** The real recordings keep their own rooms (BKS's reamps are miked), while plugin rows are measured with the room off. At equal drive that leans toward keeping plugin rows.
- **The heavy bands.** Their rule is the user's choice, not a measurement.

## Order of work

1. The amended plan is reviewed again, then the ledger entries are written.
2. H1 runs, is audited and is reported.
3. Once the keep-or-drop answers are in, the line is set by the rule above and shown to the user.
4. H2 and H3 run. Their lists are written and audited, and H3's page goes to the user if any recording needs it.
5. H4's detail is declared, reviewed, then run.
