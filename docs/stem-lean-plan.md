# Does the separated guitar lean toward another guitar? (N8, declared 2026-11-05, before it is computed)

**Why.** The deep review's step 4 (`docs/ml-deep-review-2026-11.md`, section 4). From the stem, an amp reader hit the dominant other guitar's amp more often than the target's (0.404 against 0.342, base 0.345; from the clean target 0.487), with no interval, on rows that hold NS sections. N5 and N5b show no stem cost, but on mixes with no other guitars, and F56's gains on the development sets did not reach real songs, where other guitars play, among other causes it could not separate. If the stem follows the wrong guitar, more labels will not fix that. This is the review's own test, run with an interval on a set that holds no NS rows. **It is a diagnostic: zero renders, zero separations, no training beyond linear probes, descriptive.**

**Data.** The tone probe's split: F5's training examples and FS5 ([tone probe](tone-info-probe.md)), the stored summaries in `tone-probe/features.npz`. Rows are those whose loudest other guitar, by render level plus gain, is not a double of the target (a double shares the target's preset, so it can show no lean). Its preset comes from T2's render rows, its class from T2's plan. V-real, the NS songs, the panel and the captures are not read. Other guitars here have independent presets, which real bands often do not, so a size here does not carry to songs.

**Two readers per input.** `tone_info_probe.fit_probe`, unchanged, on the same rows. **T** learns the target's labels and **O** the loudest other's, each conditioned on its own amp and class (its amp head on no conditioning, as ever), with the constant of its own cell. Inputs: (c) the stem, (b) the mix, and (a) the clean target as a control.

**Rows.**
- **Primary, on the stem: O − T,** amp-head hit minus amp-head hit per example, section-clustered t, 90%.
- **T's follow, on the stem,** on rows whose two amps differ: T's answer on the target's amp minus on the other's, section-clustered. This is what a model trained on the target would do.
- **Beside:** each reader's amp hit against its majority share; readable heads of today's 25 plus the amp choice, for T and O; for T's knob answers on heads scored for both guitars, r with the target's label and with the other's by drive, tone and cab (`reads_v3.HEADS`), demeaned within section and head, the difference with a delete-one-section interval. The same rows on (b), so that a lean the mix already has is not charged to the separator.
- **Control:** on (a), T reads and O does not. O reading the clean target would mean the labels are tied, and every row here would stand void.

**Reading, first match** (`reading`):
1. O − T clear above zero: the lead holds. The stem carries the other guitar's preset better than the target's. Training or aligning on real stems becomes a proposal for the user, about 19 h for the stems alone, and it does not start without their yes.
2. O − T clear below zero, with T's follow clear above zero: the lead does not hold on this set, and F15 and F17 stand.
3. Otherwise not shown: undecided, and no step follows from it. T's follow is read beside.

**Limits.** A linear probe on summaries; 12 sections from 9 tracks, all of them also in training; self-built mixes, with presets independent by design. The review's figure was from another reader, so a gap between the two is not a contradiction. The target's labels are the full twins' and the others' are core draws, so O's and T's knob heads differ in range: the amp head is primary for this reason, since it has one scale for both.

**Cost.** Zero renders; CPU, the probe's read took about 40 s an input, here 6 fits. Code `learn/stem_lean.py`, `tests/test_stem_lean.py`; ledger `pipeline-fix`, `phase_stem_lean`; output `tone-probe/stem-lean.json`, read once.
