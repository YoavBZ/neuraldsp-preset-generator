# Training on the captures, first step (N9, declared 2026-11-06, before any run)

**Why.** The user said go on 2026-11-06 ("Go ahead with any training you need"). F57 hears the search labels closer than S on closeness, F59 is the baseline, and the model comparison found no model type ahead of FTm, which leaves real labels as the lever not yet tried at this scale. N3's learning curve was undecided, so nobody knows yet that more real rows help. This step asks that, on the 121 trusted labels already in hand, before the second batch's 147 clips are heard: **do capture rows teach something that shows on captures they did not train on?** Second-batch labels stay unread until its gates pass.

**Arms,** FTm's recipe (W's best state, searched heads only, lr 1e-4, Adam, batch 64) on real rows, 4 folds × 2 seeds, 24 runs, one GPU job at a time:
- **C-ctl:** BKS's and GOAT's labels, each cycled to 300 rows.
- **C-cap:** C-ctl's rows plus the trusted capture units of the other three folds, cycled to 300.
- **C-mic:** C-cap at a mic loss weight of 0.1, the model comparison's lead (`A-mic`).

**Folds and holds.** The capture units' stored creator folds. Model k holds fold k's units, so their captures and creators are out. Every GOAT and capture row sharing a DI file with a fold-k unit leaves too, so their performance is out: 35 to 47 of GOAT's 214 labels a fold, and capture training units fall to 67 to 82. C-ctl has the same drops, so C-cap − C-ctl is what the capture rows add and nothing else. BKS shares no DI with the captures. GOAT's own folds are not used, since no GOAT unit is read.

**Two departures from FTm's recipe, both stated.** No inner runs: every arm takes FTm's own steps, the median of its 8 stored E on its rows (590 updates, 59 epochs on 606 rows, 39 on 906), since an inner run would choose E on GOAT's loss, which F42's history shows says little, and would cost a further 40 to 64% of rows. And all BKS and GOAT labels train, where FTm held a fold of each.

**Read.** `reads_capture`'s rows on all held units, variant 0: r by drive, tone and cab, demeaned within (fold, amp, class, head), one value per recording, own against swap, all, crunch and clean. The first control is N6's: the copied loop reproduces N1's stored r. **Primary: C-cap − C-ctl on drive, tone and cab, all classes, by a delete-one-creator t interval,** since the deep review and F59 show the percentile bootstrap running narrow at this size. C-mic − C-cap beside. Beside as well: the per-head r and spread, because F59's drive rests on one knob and FTm's spread sits on ac20Power; crunch and clean rows; N6's stored FTm rows for scale. Those are on other folds and more rows, so they are a scale and not a pair.

**Reading, first match, no effect-size bar** (`reading`):
1. A row clear above and a row clear below: mixed, no step on its own.
2. A row clear above: the rows help. Next: this arm by the score on the same held units, in its own declaration, and the second batch.
3. A row clear below: the rows cost. Training on captures stops for review.
4. Otherwise undecided, which at this size is the likely outcome even if they help, since N6's pair intervals run about ±0.07. The second batch is then the test with more rows.

**What it cannot show.** r is agreement with search labels, not sound. These are the captures' own rows, with GOAT's DIs and mostly one player, read through a clean backing with no other guitars, so nothing here is a song. C-ctl trains on fewer GOAT rows than FTm, so it may read a little below N6's row. Capture labels are search v2's and BKS's and GOAT's are v1's, so the recipe differs inside a model. Every held unit is 1 of 121, in 19 creators, and `tone3000` holds about a third of the score in N6.

**Cost.** About 4 to 6 min a run on MPS by `A-ctl`'s measured rate, so about 2 h, about 120 MB of checkpoints, zero renders. Inputs are built. Disk stops at 33 GB. The read is CPU, about 5 min.

**Code.** `learn/capture_train.py`, `tests/test_capture_train.py`; ledger `pipeline-fix`, `phase_n9`; outputs `PF/captrain/`.
