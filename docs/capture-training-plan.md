# Training on the captures, first step (N9, declared 2026-11-06, before any run)

**Why.** The user said go on 2026-11-06 ("Go ahead with any training you need"). F57 hears the search labels closer than S on closeness, F59 is the baseline, and the model comparison found no model type ahead of FTm by the score, which leaves real labels as the lever not yet tried at this scale. N3's learning curve was undecided, so nobody knows yet that more real rows help. This step asks that, on the 121 trusted labels already in hand, before the second batch's 147 clips are heard: **do capture rows teach something that shows on captures they did not train on?** Second-batch labels stay unread until its gates pass.

**Arms,** FTm's recipe (W's best state, searched heads only, lr 1e-4, Adam, batch 64) on real rows, 4 folds × 2 seeds, 32 runs, one GPU job at a time:
- **C-ctl:** BKS's and GOAT's labels, each cycled to 300 rows.
- **C-cap:** C-ctl's rows plus the trusted capture units of the other three folds, cycled to 300.
- **C-mic:** C-cap at a mic loss weight of 0.1, the model comparison's lead (`A-mic`).
- **C-c39:** C-ctl at C-cap's 39 epochs, so that a dilution can be told from a cost.

**Folds and holds.** The capture units' stored creator folds. Model k holds fold k's units, so their captures and creators are out. Every GOAT and capture row sharing a DI file with a fold-k unit leaves too, so their performance is out: 35 to 47 of GOAT's 214 labels a fold, and capture training units fall to 67 to 82. C-ctl has the same drops, and its rows are the exact start of C-cap's. At fixed updates C-cap shows each BKS and GOAT row a third less often, so C-cap − C-ctl is capture rows in place of a third of those updates, not capture rows on top, and C-cap − C-c39 is the same rows shown as often, with fewer updates than C-ctl. BKS shares no DI with the captures. GOAT's own folds are not used, since no GOAT unit is read.

**Two departures from FTm's recipe, both stated.** No inner runs: every arm but C-c39 takes FTm's own steps, the median of its 8 stored E on its rows (590 updates, 59 epochs on 606 rows, 39 on 906), since an inner run would choose E on GOAT's loss, which the deep review shows says little, and would cost 39 to 54% of capture rows and 16 to 24% of GOAT's. And all BKS labels and all GOAT labels but the dropped ones train, where FTm held a fold of each: distinct labels per fold, C-ctl against FTm, GOAT 167 to 179 against 155 to 168, BKS 306 against 192 to 282.

**Read.** `reads_capture`'s rows on all held units, variant 0: r by drive, tone and cab, demeaned within (fold, amp, class, head), one value per recording, own against swap, all, crunch and clean. The control is N6's, and the same loop reads this step's nets (`reads_capture.read_fold`), so it covers them. **Primary: C-cap − C-ctl on drive, tone and cab, all classes, by a delete-one-creator t interval,** since the deep review and F59 show the percentile bootstrap running narrow at this size. The same pair head-standardised, by the same interval: raw r pools heads of very different spread, and F59's drive rests on one knob. C-mic − C-cap and C-cap − C-c39 beside. Beside as well: per-head r and spread; how the answers do as answers, squared error against the cell mean and the slope, since F59 says size is the next question; crunch and clean rows; N6's stored FTm rows for scale, on other folds and other rows, so a scale and not a pair. Seed noise sits outside the interval; it was small on GOAT (A-ctl +0.006, −0.014, −0.000).

**Reading, first match, no effect-size bar** (`reading`):
1. A row clear above, with its head-standardised pair above zero, and a row clear below: mixed, no step on its own.
2. Such a row clear above: a lead, not a verdict. Next: capture labels shuffled within their cells (8 runs, as N3), since BatchNorm's statistics move toward capture audio with no label content, then this arm by the score on the same held units, each in its own declaration.
3. A row clear below: a cost to review, read first against C-c39, since C-cap − C-ctl can show dilution. A cab row may be the recipe's, below. This does not by itself cancel the second batch.
4. A row clear above with its standardised pair at or below zero: moved spread, not a gain.
5. Otherwise undecided, which at this size is the likely outcome even if they help.

The second batch follows on 2, 4 and 5 once it is heard, and is the test with more rows.

**What it can bear.** Swapping arms within creators at random on N6's stored answers, 300 draws a case, at least one of the three raw rows clears above with none below on 11 to 17% of tries, and the mirror case on 7 to 14%, each single row on 1 to 7%, so a clear row is a lead. Jackknife half-widths for FTm − FT on these folds run about ±0.07 on drive and cab and ±0.13 on tone, and for FTm − W ±0.10 to ±0.18; those answers came from other folds, so this is indicative.

**What it cannot show.** r is agreement with search labels, not sound. These are the captures' own rows, with GOAT's DIs and mostly two of three players (held units 57, 52 and 12 by player), read through a backing with no other guitars, so nothing here is a song. Capture labels are search v2's and BKS's and GOAT's are v1's, so the recipe differs inside a model, and it shows: 29% of the capture labels' cab slots left S, against 77% of GOAT's and 76% of BKS's, while drive is 75% against 57% and 62%, so a third of C-cap's rows mostly teach cab at S, and a cab row either way may be v2's. 121 units, 19 creators, and the creator `tone3000` holds 19 to 26% of FTm's covariance on N6.

**Outcome (2026-11-06, F62 in the [plan](pipeline-fix-plan.md)).** Undecided: C-cap − C-ctl drive +0.018 [−0.032, +0.068], tone −0.014 [−0.093, +0.065], cab +0.024 [−0.028, +0.076]. It excludes a gain above about +0.07 to +0.08 and does not exclude +0.05. C-cap − C-c39's clear rows are not evidence for capture labels: about half or more is updates alone, and no row clears on both seeds. The two limits corrected by the audit are in F62.

**Code.** `learn/capture_train.py`, `tests/test_capture_train.py`; ledger `pipeline-fix`, `phase_n9`; outputs `PF/captrain/`.

**Cost.** 590 updates took about 3.3 min at `A-ctl`'s measured rate, so about 1.5 to 2 h for 32 runs, about 140 MB of checkpoints, zero renders. Inputs are built. A run refuses under 33 GB free. The read is CPU, about 5 min.

*Review (2026-11-06, independent, before any run; a second pass during it on the read and the wording):* eight required changes, all made. No leakage found on all 4 folds, and the data path ran on real rows. The main ones: the pair is not capture rows on top, so C-c39 joins; the chance rate of a clear row; the control now covers this step's nets; the standardised pair; the recipe's limit on cab.

## N9b: does a ridge gain from capture rows? (declared 2026-11-06, before it is computed)

**Why.** N9 tested capture rows in place of updates. It could not test them on top, because a network's epoch has a fixed budget. A ridge takes each labelled record once, so capture rows simply join. The review session's `M-pcs`, the mel ridge at 64 PCs, needs no training, no GPU and no download, and it reads about as well as FTm on the development sets by the score. `E-mix` reads a little better on GOAT, but needs 3,750 more embedded inputs for a gain of −0.006, so it waits on this read. This was told to the user on 2026-11-06.

**Arms.** `M-ctl`, fitted per capture fold on C-ctl's rows, each labelled record once (a BKS unit has one per amp). `M-cap`, on C-cap's rows, likewise. The same folds, DI drops and holds as N9, through `capture_train.rows_of`. Read on variant 0, as N9, and on the mean of all 25 backings beside, which costs nothing and answers the limit below. Capture rows are about 12 to 15% of a fit's records.

**Read.** N9's rows, joined by recording and amp, so `M-*` sit beside C-ctl and C-cap on the same 121 units. **Primary: M-cap − M-ctl on drive, tone and cab, all classes, delete-one-creator t,** with the head-standardised pair. Beside: M-cap − C-cap and M-ctl − C-ctl, ridge against network on one set; the 25-backing pair, and what the mean adds to M-ctl; crunch and clean; per-head spread and squared error against the cell mean, because N9's answers lose to it.

**Controls, stopping the run.** `fit_predict` at these settings reproduces the stored `M-pcs` answers on BKS's and GOAT's fold 0 within 1e-6 (worst 0.0 when checked before this declaration, on no capture row); a fit must hold one row per labelled record; no held DI may sit in a fit's rows.

**Reading.** N9's map, first match: mixed; a row clear above with its standardised pair above zero is a lead, then labels shuffled within cells, then the score, each declared; a row clear below is a cost to review; a clear raw row with its standardised pair at or below zero is moved spread; otherwise undecided. About the chance rate, N9's figures for its network pairs are the only guide, and they were not measured on these answers: at least one of three rows clears above with none below on 11 to 17% of tries.

**Limits.** N9's, and these: on GOAT `E-mix`'s drive read on variant 0 ranks 23 of 25 backings, so one variant may flatter a read, which the 25-backing row checks. 64 PCs was chosen on plugin rows alone. The penalty is chosen inside each fit, per head and half, on that fit's rows, with inner folds that hold DIs and not creators, so M-cap's choice sees one creator on both sides of an inner fold and may lean under-regularised; only the grid and the rule were set earlier. Held backings also back training rows. Capture labels' offset from the search recipe goes into one pooled cell mean, so M-cap spends some weight on it. This is agreement with search labels, not sound.

**Cost.** Zero renders, zero training, no GPU, no new files but the read; the control's fit took 5 s, so 16 fits take minutes. Code `learn/capture_ridge.py`, `tests/test_capture_ridge.py`; ledger `phase_n9b`.

*Review (2026-11-06, independent, before any run):* six required changes, all made. The main one: a first draft kept one row per unit, which would have dropped two of each BKS unit's three amps and leaned toward a false lead; the control could not see it, so a fit now stops on the wrong count.
