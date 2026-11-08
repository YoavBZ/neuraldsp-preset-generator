# Too-heavy recordings out of the plugin rows and the test sets (H1 to H3; H4 to follow)

**Status: declared 2026-11-08 and amended the same day after the keep-or-drop answers were read (Amendment 1: a tone-free flatness replaces the declared measure, H2's dry renders are superseded, a plugin check page sets the plugin line), the user's yes ("Go ahead for the rest", 2026-11-08, on the proposal of 2026-11-07). H1 to H3 were declared before any render, measure or answer here was read; Amendment 1 was written after the keep-or-drop answers were read. Amended after its independent review: the line's population and rule, the effects list, W's own rows, the render counts, opt-in exclusions.** One look came first and is stated: the review measured the goat-heavy page's 22 heavy recordings and showed how the existing marks fall by bin (for example 8 heavy of 10 in [3, 5) dB) before the rule was amended, and the top bin's merge-down rule was written knowing [5, 7) holds 2. No keep-or-drop answer had been read. Ledger `pipeline-fix`, `phase_h1` to `phase_h3`. H4 goes in the ledger when its detail is declared. The line comes from the keep-or-drop page (`phase_scope`, `learn/scope_page.py`), answered 2026-11-08; Amendment 1 says how it is used. Nothing is deleted: every step writes exclusion lists that only new runs read. Results go in [pipeline-fix-plan.md](pipeline-fix-plan.md), F67 on.

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

## H2: W's plugin rows (after the line; its dry renders, audit and render table superseded by Amendment 1)

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

## H4: retraining on the cleaned rows (declared 2026-11-08 after the check page was read, before any training; the user's go: "Agreed. Let's follow your suggestions")

**Why.** The check page sets a plugin line, but the line is undecided on its interval. `check_read` missed that flag; the audit caught it, and the write-up records it: −5.08 to −3.57 dB, the 36th to 75th percentile of the doubler-free rows. It also rests on a tie at one half, and Bulldozer supplies 42% of the rows it cuts. So the cut is chosen by result, not guessed. Two plugin cuts bracket the interval, and a third arm cleans the real rows only. Each is compared with FTm as it stands.

**The stops tripped, and the user's ruling.** The full cut trips both of H2's stops.
- **Cells:** counted on all 1,787 rows, 4 amp-and-class cells lose more than half: ac20 crunch, sw50r crunch, pr12 crunch, and ac20 clean at 51%. Counted outside the heavy bands, it is the 3 crunch cells, with ac20 clean just under half.
- **Sections:** 13 of the 174 sections outside the heavy bands go entirely, and half or more of 114 sections and of 13 of the 23 DIs. No DI goes entirely.
- **The gentle cut** removes 1 section entirely and trips no cell.
- **The ruling:** these went to the user. The user's "Agreed. Let's follow your suggestions" answered a proposal to train both cuts and compare, so it covers both.

**The exclusions** are an opt-in pinned ledger key, `phase_h4_exclusions`, holding a file path and its sha256: `PF/heavy/h4-exclusions.json`, written before any training. Only the new run tags read it, and `recipe_inputs`, `real_labels`, `goat_labels`, `plugin_rows`' default path and `bakeoff.plugin_set` are unchanged. The review session is told before it is written. It holds:
- **`real_out`:** the 19 labelled recordings the keep-or-drop page and the earlier marks put out (`scope/verdicts.json`'s `out`), all crunch: GOAT pr12 9, sw50r 6, ac20 2, and BKS 2. They leave the real training rows and every held set that chooses an epoch count: the inner runs' validation fold, which sets E for FT_k and the all-labels pair. The code enforces this. The score read keeps them, reported apart.
- **`plugin_out_full`:** W's rows at or past the plugin line, −4.331 dB, by stored flatness or, for doubler rows, the doubler-off value. Plus Ale Lak's and Storm Of Particles' 34 rows. That is 927 of 1,787, leaving 860.
- **`plugin_out_gentle`:** the same at the doubler-free rows' 75th percentile, −3.57385 dB (the page's band edge, not the bootstrap's `hi90` of −3.57451, which would cut one row more), where the listener dropped 18 of 20. Plus the 34. That is 496 of 1,787, leaving 1,291. Each list is written with its threshold and count.
- **`ns_out_full` and `ns_out_gentle`:** NS's 383 rows by the same rules. They are measured first, as H3 declares: stored flatness with zero renders, and the 114 doubler rows doubler off, 228 renders. Their counts and the doubler-off provenance go into the file before training. NS is W's selection set, so this use is selection inside H4, not a test read. Each arm's W selects on its own NS list, and changing the selection set is part of the arm.

**The arms.** All keep FTm's recipe unchanged except their rows:
- **Full (`P2b-wide24-hf`, then `P2b-ftmf`):** W retrained on the 860 rows (`train --rung b --wide`, both seeds, 60 epochs as the ledger's `phase_3_length`), choosing its best state on NS less `ns_out_full`. Then FTm's masked tuning (`train-ft --masked --ft-cap 300`: 4 folds × 2 seeds, inner then FT_k, plus the all-labels pair), from that W's best, on the real rows less `real_out`.
- **Gentle (`P2b-wide24-hg`, then `P2b-ftmg`):** the same on the 1,291 rows, with `ns_out_gentle`.
- **Real only (`P2b-ftmc`):** today's W, `P2b-wide24`, with FTm's tuning on the real rows less `real_out`. This says which half of the cleaning any change comes from.
- **Not equalised:** the epoch count stays the recipe's, so the full arm takes about half the steps. That is part of what is compared, and it is stated beside the result.
- **Inputs:** the inputs hash guard against D_fix's runs can't hold with units left out, so the new tags check three things:
  1. The full, unfiltered `DfixData` hash, rebuilt today, equals D_fix's stored one, so the files are unchanged.
  2. The tag's units are exactly D_fix's units less `real_out`.
  3. The filtered hash is stored on the run.
  - `ft_carry`'s check for the all-labels pair gets the same guard.
  - `FT_PRETRAIN` becomes a setting per tag: `P2b-ftmc` starts from `P2b-wide24`, and the other two from their own W.
- **Undertraining:** if a retrained W's best state falls in its last 5 epochs, it is reported as possibly undertrained, beside the result. A run with the steps equalised stays a later option, approved separately.

**Cost, measured on today's runs.** W took 10.6 min a seed on MPS, and fewer rows take less. FTm's 18 runs took 136 record minutes, 78 min wall at two at a time. So the three arms take about 4 to 5 hours of MPS wall time in all. One job group (two runs) at a time, as FTm's runs were, announced first.

**The read by the score** (H4a). FTm's stored read is `real-predict`/`goat-predict`, then `real-render`/`goat-render`, then `real-report`/`goat-report`, on read 2's units: BKS's 40 units by DI fold, GOAT's by item fold, each read by its own fold's model. The new tags are read the same way, about 1,340 renders each and 4,000 in all, at most 3 render processes.
- **The baseline:** FTm's stored reads, since the new tags read the same units, halves, render settings and judge (`aligned.py`).
- **Primary, one row per arm:** `ln(d_arm/d_FTm)` on the held half, BKS clustered by DI and GOAT by item, 90% intervals, on the units no arm's cleaning removed. The 19 removed real units are reported apart.
- **Beside:**
  - each arm less S;
  - each arm less FTm by class;
  - the full arm less the gentle arm;
  - each arm less FTm on N12's units, by N12's FTm answer path: the primary on the 27 units whose DI is not among W's training rows, with all 31 and the 4 apart beside. That set is other bands' songs, in no model's real rows.
- The N12 side read needs `score_ear`'s FTm answer path extended to the H4 tags before H4a; the by-class rows are added to the reports then.
- No bar is set, and undecided is not failed. The score is weak between close models (F65, F66), so by the score alone a small difference will likely read undecided, and the ear page decides.

**The read by ear** (H4b) is declared on its own before it is built, after training. It is one blind page with S, FTm and the three arms, built to the review session's requests: N12's stored fields per card, closeness on every candidate, at least 2 repeats a class, and S on every card. A fifth request, drawing close model pairs first, was dropped once no judge was named (S12), since it would bias the arm-over-FTm read.

**H4b, the page (declared 2026-11-08 during H4's training, before any H4 read or render is opened).** This is N12's page and code, `score_ear`'s, on N12's 31 units: real songs from 9 other bands through captured amps, in no model's real rows.
- **Candidates:** S, FTm, `P2b-ftmf`, `P2b-ftmg` and `P2b-ftmc`, each answering from the unit's search half and judged on its held half.
  - The clips come from H4a's N12 side read, which keeps every tag's held-window clip on all 31 units.
  - On the 15 units N12's page didn't use, it also renders S (checked against its stored hash) and keeps S's and FTm's clips. That adds about 60 renders to H4a.
- **Cards:** 14 first hearings, 8 clean and 6 crunch, at most 2 a band within each class (2 a band across the page can fill only 13), seeded (seed 20261112).
  - The clean cards come from the 14 clean units N12's page didn't use.
  - The crunch cards come from all of N12's crunch units, since only one was unheard. Those cards are marked "heard on N12 with other candidates".
  - Within a class the draw is plain and seeded, as N12's was. No score enters it: a draw that put close model pairs first would push each arm's share over FTm toward one half, and no judge was named to need them (S12).
  - Plus 2 repeats a class, seeded, so 18 items in two parts of 9.
- **The page:** N12's, with blind letters, the recording beside, rank and closeness on every candidate, sure or unsure, and the out-of-scope mark. Answered in place.
- **Stored per card:** each candidate's held-half clip, its window, the lag, the stored J0, and the unit's DI path and start, as N12 stored them.
- **The read:**
  - By ear, each arm over FTm: rank share and closeness gap, clustered by the DI's band. N12's rows (bootstrap share, sign test) stay beside.
  - **Primary,** new code: the one-sided p of the band-clustered jackknife t on the rank share over FTm (df the bands less one), Holm over the three arm-over-FTm rows.
  - **Beside:** the same rows on the 8 clean cards never heard before, and the rows without the 4 units whose exact DI is among W's training rows. On those 4 units FTm and `P2b-ftmc` have seen the recordings through the plugin, while the cut arms lost some or all of them. H4a's N12 side read reports the same apart group.
  - Beside: each arm over S, and the full arm over the gentle.
  - J0's order against the ear, by N12's rows.
  - Named judge: none (S12, `docs/judge-screen-results.md`), so J0 alone. In the score-against-ear rows, the heard-before crunch cards are also reported apart, beside only.
  - The page fails if more than 3 of the 14 cards are unfilled.
- **The decision rule:** an arm counts as better than FTm by ear when the primary's Holm-adjusted one-sided p is below 0.05.
  - Otherwise it is not shown at this size, and the stop rule applies.
  - **Power:** with 14 cards in about 7 bands only a large gain reads clear, so "not shown" means not shown here, not no effect.
  - The page's code is N12's, extended to 2 repeats a class, since `page_order` repeats one card a class today.
- **Cost:** no renders beyond H4a's (which include the 60 above), and one listening session of 18 cards.
- **If two arms pass,** the user decides between them, with the full-over-gentle row beside. An arm flagged by the score (below) stays a candidate, with its score row beside.

**What it leads to.** The user decides from both reads.
- **An arm better than FTm** by ear, with the score beside: its cut is adopted.
  - **If the score reads that arm reliably worse than FTm** on a primary set (BKS by DI, GOAT by item, or N12's 27 units; the lower end of its 90% interval above zero), the user decides between adopting it and keeping FTm, with both reads beside.
    - Adoption is the default. Keeping FTm counts as none better, and the clean-up stops. No new run or listening follows either way.
    - Other clusterings, such as GOAT by fold, are beside only.
    - Declared 2026-11-08 after H4a's read and before the H4b sitting. The only such case is the gentle arm on GOAT by item, +0.0155 [+0.0051, +0.0259] (by fold, beside: [−0.0028, +0.0327]). Every other arm-less-FTm row on the three sets has its interval spanning zero or below it.
- **None better:** the clean-up stops there. No more listening goes into data, and the work turns to the plugin-to-real gap and the score.

## Amendment 1 (2026-11-08): the line doesn't fit, so a tone-free flatness, and a check page of plugin examples (declared before the page is built, amended after its review)

The user's word of 2026-11-08: "Go ahead, also make sure the measurement is correct. If the line you find doesn't fit - use a different measurement (not necessarily distortion, can be other noise indication)." Everything here was found after the keep-or-drop answers were read, and is stated as such. The answers are not used to tune the measure any further: the check page below is its only fresh test.

**The line as declared doesn't fit.**
- **The answers:** 110 keep, 12 heavy and 2 unsure.
- **The declared rule** gives +1.05 dB [−2.27, +2.63]. That is `phase_h2`'s outcome, and it stays in the ledger.
- **The old measure separates the answers weakly.** Its AUC on the 176 answered recordings is 0.63 [0.55, 0.75], clustered by song. On the 124 the page asked about it points the wrong way, at 0.68.
- **Why:** a miked room reads as drive on that meter, as H1 found for the plugin's room. All 76 BKS recordings asked were kept, up to +3 dB.
- **Alignment is not the cause:** at each recording's best lag the AUC is 0.62.

**The measure: spectral flatness of the amp's sound, with each frame's tone taken out (`heavy_cleanup.flatness_db`).**
- **How it is computed:**
  - Per Hann frame of 4096, hop 2048, the power spectrum is divided by its own 1/3-octave moving average.
  - The flatness (geometric over arithmetic mean) is taken over 200–5000 Hz.
  - The median runs over the frames where both signals play: the DI within 30 dB of its loudest, the amp within 40 dB of its own.
- **What it reads:** the amp's sound alone, as the ear hears it. Distortion fills the spectrum between a note's harmonics, and dividing out the envelope removes EQ, cab and room tilt. The DI only picks the frames.
- **Test signals:** on two notes through rising drive it rises steadily, and a tone change moves it under 0.5 dB.

How it was found, after the answers were read:
- **Plain flatness** was picked from 14 measures (study in `PF/heavy/measures/`). It moved with tone as much as with heaviness: a 2 kHz low-pass took 3.6 dB off it.
- **Dividing out the envelope** fixed that. That version also subtracted the DI's own value, and on plugin rows it then mostly read each section's DI: 89% of its variance lay between sections, and the section means correlated at −0.95 with the DI term.
- **The amp side alone** is this, the 16th variant tried. Its between-section share is 0.60, near the old meter's 0.61 on dry rows. Within a section it orders rows by drive (Spearman with "drive pedal on or crunch base", median 0.45 over 162 sections). The design (band, median, frame rule) was never varied.

**On the real answers (zero renders), by song.**
- **Within GOAT it separates heavy from kept:** AUC 0.85 [0.78, 0.92] on 93 recordings (39 heavy); 0.89 for player1 and 0.83 for player2; 0.78 on the 48 GOAT recordings the page asked.
- **The scale differs by source.** BKS's 83 recordings read −19.97 to −3.35, with all 76 asked kept. Across sources the AUC falls to 0.67, and a GOAT line (−5.84 [−8.26, −4.34]) fails left out by song, at 0.49 accuracy.
- **W's plugin rows read flatter again:** median −4.63, 80% range −8.33 to −3.29. 72% sit past the GOAT line.
- So the measure orders recordings within a source, but no line carries across sources. The plugin line comes from plugin answers alone.

**On the plugin rows, the effects move it little, except the doubler.** On H1's 60 pairs, stored less dry, in dB and in W's percentile points:

| Family | dB, median [range] | Percentile points, median [range] |
|---|---|---|
| reverb | +0.02 [−0.02, +0.54] | +0.5 [−0.1, +6.7] |
| delay | +0.12 [−0.01, +1.55] | +2.2 [−0.1, +10.5] |
| doubler | −0.99 [−1.53, −0.10] | −23.1 [−44.2, −0.2] |
| tremolo | +0.02 [−0.23, +0.61] | +0.3 [−2.5, +10.3] |
| spring | +0.06 [0.00, +1.12] | +0.7 [−0.1, +4.4] |
| room | −0.04 [−0.75, +0.40] | −0.4 [−15.6, +6.3] |

- **The scale is compressed at the top.** White noise reads −2.34 dB, and W's top quarter sits between −3.74 and −2.71, so a few tenths of a dB is a whole band. W's top rows sit nearer noise than clipped harmonics: a hard-clipped three-note chord levels off near −5.2. BKS's kept recordings (median −4.01) read flatter than GOAT's heavy ones (−4.37). That fits the user's "can be other noise indication", but it means the measure is read only within a source.
- **The doubler pushes rows down.** Its fold to mono puts comb notches finer than 1/3 octave into the spectrum, which read as less flat. 507 of W's 1,753 rows have it on. So:
  - Doubler rows never go on the check page.
  - The plugin line is set on the 1,246 rows without it.
  - In H2, the doubler rows are measured with only the doubler off, on H1's path: a variant whose setting differs from the full twin in the doubler key alone, checked as `check_dry` does. That is about 1,014 renders, then a cut at the plugin line.
  - NS's doubler rows get the same in H3.
- **Otherwise the question moves from drive to heaviness as heard,** effects included, and rows without the doubler are measured as stored.

**The check page (H2a, zero renders).**
- **The cards:** 40 of W's stored targets outside the heavy bands and without the doubler (1,246 rows), the exact training audio, the guitar alone at −23 LUFS. Seed 20261110.
- **By flatness, in 4 bands of 10,** by those rows' own percentiles: under the median (−4.36 dB), to the 75th (−3.57), to the 90th (−3.21), and over (to −2.71).
- **Within a band,** songs go round robin: each round takes one row a song, the band's least used amp first. No section gives more than one card.
- **5 within-section pairs** come on top, 50 cards in all. They are sections not on the band cards, one a song, seeded among those whose lowest row sits under the doubler-free rows' median and highest at or past their 90th percentile (else the widest). Each gives its lowest- and highest-flatness rows. These pairs tell a setting's effect from a section's.
- **The page:** `scope_page`'s page and rule. It is blind and one tap each, only Keep stays, and "Not sure" counts as dropped. Answered in place. Its answers are not used to tune the measure.
- **The plugin line:** the declared isotonic rule on the 40 band cards' stored flatness, with each card weighing one.
  - Songs are resampled in the bootstrap (2,000).
  - "Not sure" as neither is reported beside.
  - **The pairs' read:** of pairs with exactly one card dropped, how often it is the flatter one. Five pairs can only show a gross failure, so an undecided result there is expected.
  - The line and its interval are also given as percentile ranks among the 1,246 doubler-free rows, since near the top a few tenths of a dB is a whole band.
- **Undecided outcomes:** if the fit never reaches one half, the line falls in the lowest band, its interval is wide, or the pairs don't favour the flatter card, that goes to the user as undecided, not as a failure. No row is dropped by measure until the user rules.

**H2 and H3 change as follows.**
- **H2:** out are W's rows at or past the plugin line, by stored flatness or, for doubler rows, by their doubler-off measure, and Ale Lak's and Storm Of Particles' 34 as before.
  - The report gives, before anything is trained, the share of each section and each DI the cut removes. If a whole DI or section goes, the user decides.
  - H2's dry renders, audit and render table are superseded: only the doubler rows are rendered again, doubler off.
  - The cell stop and the opt-in exclusion key stand.
- **H3:**
  - All of V-real's 11 parts and the panel's 45 heard read units go on H3's page, since no real line carries across sources. That is 56 test recordings.
  - Each sits beside 1 development filler: the nearest unused kept GOAT or BKS recording by flatness, never reused. Where no unused filler sits within 2 dB, the nearest is used anyway and the card is noted. That is 112 cards, under the 124-clip size.
  - NS's rows are measured by stored flatness (its 114 doubler rows doubler off, 228 renders) and cut at the plugin line, with no page.
- **H1** still stands as run. It showed that the old measure reads effects and rooms as drive.

**How this differs from what failed.** The declared line used a measure the answers show can't tell heavy from kept. This uses one that orders recordings by heaviness within a source, with tone taken out, and sets the plugin line from plugin answers before any plugin row is dropped. It chooses rows by sound, not by song or section, and the per-section report checks that. Nothing is excluded until the page is answered.

## What this can bear

- **Real amps against the plugin.** No line carries across sources: GOAT, BKS and the plugin read on different scales. The plugin line comes from plugin answers, on 40 cards and 5 pairs, one listener.
- **What is measured.** Rows are judged and measured as stored, effects included: heaviness as heard, not drive alone. Since Amendment 1, H1's dry renders are a check on the meters, not the measure.
- **What isn't measured.** The other guitars in each D_CC mix are not screened, and neither is drive inside an effect, such as a delay's tape drive.
- **The measure's design.** The band, the median and the frame rule were never varied. The tone-free form was tried once, after the answers were read.
- **The heavy bands.** Their rule is the user's choice, not a measurement.

## Order of work

1. H1 ran and was audited (F67). The keep-or-drop answers are in, and the declared line (+1.05 dB) doesn't fit (Amendment 1).
2. Amendment 1 is reviewed independently, then the ledger entry `phase_h2a` is written. `phase_h2` gets its outcome.
3. `check-measure` and `check-page` run, and the page goes to the user.
4. Once it is answered, `check-answers` sets the plugin line. That goes to the user before any exclusion is written. F68 records the keep-or-drop answers, the measure study and the check page's read together.
5. H2's list and H3's measures and page follow, each audited.
6. H4's detail is declared, reviewed, then run.
