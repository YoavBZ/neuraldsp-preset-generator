# Which distance without a DI reproduces the judge's choices?

Declared on 2026-10-07, before any distance in it is computed. This is roadmap step 2,
[research round 4](research/round-4-audio-ml.md) §5 experiment 4 ("the judge as
teacher", round 1's E6 scored under the judge). No renders, no listening, no
downloads.

The product has the song, not the take's DI. The judge needs that DI: it compares a
preset rendered through the take's own notes with the amp track. A distance that
compares a render of *other* notes with the amp track would let the product choose
presets from the song alone. This asks which such distance, if any, picks presets
nearly as well as the judge.

## Material

- **Targets:** the 25 parts of `~/ndsp-presets/runs/kill/amp-reach.json` (9 bands,
  development split), whose judge distances are stored for every candidate.
- **Menu:** the 111 candidates the judge scored for every part: 45 SW50R, 35 PR12, 31
  AC20 (factory presets and each amp's template+R; time effects, doubler and gate
  off). A candidate whose judge distance is missing for a part is left out of that
  part's menu.
- **The teacher:** the judge's full-window distance, `amp-reach.json` keys
  `<amp>:<candidate>|full|<band set>` (1.0 to 10 s, through the part's own DI), under
  both band sets.
- **Candidates playing other notes:** the panels (`~/ndsp-presets/runs/kill/<amp>/`)
  hold every candidate rendered through each of 43 parts' DIs. For a target part P,
  each **donor** Q is a panel part from a different band than P (band as in
  `kill_tests.py`, from the catalogue). Every such donor is used, so no choice of
  donor is made.
- **The reference** the distance compares with: P's amp track (`reference.wav`), and,
  for the stems condition, P's separated guitar from the full mix
  (`~/ndsp-presets/learn/poc/stems/htdemucs_6s/<part>/mix_guitar.wav`) on the parts
  its manifest marks `usable` (18 of the 25).
- Every clip is cut to 1.0–10 s, as the judge's window, and set to one loudness before
  any feature: the product does not know the level the song's guitar was recorded at.

## The distances ("rows")

All are computed from the clip alone, with frames gated by the clip's own level
(frames within 40 dB of its loudest), never by a DI.

- **v3 (the baseline):** `analysis.compare` `unpaired-v3`, level left out, as
  `research/benchmark_match_pipeline.py` calls it (reference as `isolated_stem`,
  render as `probe`). Its regret has never been computed; this check computes it.
- **v3c:** the audited variant in `research/kill_tests.py` (`_v3c_compare`), reported.
- **Long-term spectrum:** the mean log-mel spectrum (64 bands, 50 Hz to 16 kHz) over
  gated frames; Euclidean distance in dB.
- **Log-mel mean and spread:** that mean and each band's standard deviation over gated
  frames (128 values); Euclidean.
- **MFCC statistics:** the mean and standard deviation of MFCC 1 to 20 (C0 left out)
  over gated frames; Euclidean after each value is divided by its spread over all
  panel renders.
- **Lean fingerprint:** from `analysis.fingerprint` fields, the third-octave band
  levels relative to their mean, spectral tilt, the spectral statistics, crest factor
  and loudness range; Euclidean after the same scaling.

Each row's scaling uses only the panel renders, never a judge distance or a pick.
A small CNN's statistics, AFx-Rep and CLAP (round 4's other rows) need training or
downloads and are not in this check.

## Scoring

For a target P, a donor Q and a row: the row's **pick** is the menu candidate whose
render through Q's DI is nearest P's reference. Its **regret** is
log d_judge(P, pick) − min over the menu of log d_judge(P, ·), 0 when the pick is the
judge's best. P's regret is the median over its donors; the row's regret is the median
over the 25 parts. Its **agreement** is the Spearman correlation, across P's menu,
between the row's distances (through Q) and the judge's (through P's own DI), the
median over donors, then over parts.

**Gate,** per row, under both band sets (round 1's E6, as round 4 declared it):

1. its regret is at most 0.75 times v3's;
2. on stems, its regret on the 18 usable parts is no worse than v3's on stems;
3. its agreement is at least 0.6.

A row that passes all three under both band sets passes. If several pass, the one with
the lowest regret on stems is the step's answer. If none passes, no DI-free distance
here reproduces the judge, and the roadmap's next candidates are those that need
downloads or training (round 4's rows, round 1's approach 3c).

**Reported, not deciding:**

- Reference points: a random pick's expected regret (the mean over the menu), the
  constant pick (the candidate with the lowest median judge distance over the parts of
  the other bands), and the judge's own pick through the part's own DI (0).
- Each row per amp's menu alone, and per band.
- **Same notes:** for each row, how much nearer it puts a candidate rendered through
  P's own DI than the same candidate through a donor (the median of the log ratio):
  how much the notes, not the tone, move it.
- **Another teacher:** the average-guitar measure (branch `poc/sound-model`,
  `avg-yardstick-distances.json`) covers only the 21 clean PR12 presets and template+R,
  on half B. On that menu, each row's regret under it, and under the judge on the same
  menu, side by side. Its own listening check is still running; if it confirms that
  measure, this check is declared again under it once it covers all three amps.

## Limits

- **The judge is the teacher,** with its blind spots: listening validated it only for
  clear clean-to-crunch PR12 differences.
- **Clean material:** the parts are mostly clean; high-gain matching is not tested.
- **Panel renders through another band's DI** play another player on another guitar:
  that is the product's situation, but the donors' guitars and levels differ from one
  another too, which the median over donors averages over.
- **Stems** come from one separator (htdemucs_6s) on 18 parts.
