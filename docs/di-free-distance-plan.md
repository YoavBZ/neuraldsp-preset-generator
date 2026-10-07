# Which distance without a DI reproduces the judge's choices?

Declared on 2026-10-07, before any distance in it is computed, and revised the same
day after an independent review, still before any distance existed (only the clips'
features had been cached). This is roadmap step 2,
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
- **Menus:** the 111 candidates the judge scored for every part: 45 SW50R, 35 PR12, 31
  AC20 (factory presets and each amp's template+R; time effects, doubler and gate
  off). And the **clean menu**: each amp's template+R and its factory presets that
  `plan_listening_validation.high_gain` calls clean (the rule `amp_reach.py` uses), the
  region the judge was validated in. Every part has a judge distance for every
  candidate.
- **The teacher:** the judge's full-window distance, `amp-reach.json` keys
  `<amp>:<candidate>|full|<band set>` (1.0 to 10 s, through the part's own DI), under
  both band sets.
- **Candidates playing other notes:** the panels (`~/ndsp-presets/runs/kill/<amp>/`)
  hold every candidate rendered through each of 43 parts' DIs. For a target part P,
  each **donor** Q is a panel part from a different band than P (band as in
  `kill_tests.py`, from the catalogue) whose DI plays through the window: the 16 parts
  in `amp-reach.json`'s `parts_with_a_quiet_half` are not donors (the product controls
  its own riff, so this uses nothing of the target's). Every other such donor is used,
  so no choice of donor is made.
- **The reference** the distance compares with: P's amp track (`reference.wav`), and,
  for the stems condition, P's separated guitar from the full mix
  (`~/ndsp-presets/learn/poc/stems/htdemucs_6s/<part>/mix_guitar.wav`) on the parts its
  manifest marks `usable` and where that very stem's SNR is at least 1 dB (12 of the
  25). The power on stems is low.
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
- **Masked long-term spectrum** and **masked log-mel mean and spread:** the two log-mel
  rows treated as the judge treats its spectra, from the reference alone: each frame
  floored 40 dB under its loudest band, only the bands within 30 dB of the reference's
  long-term peak kept, and the mean level offset between the two removed.
- **LDA:** round 1's numpy row. The MFCC statistics and the lean fingerprint, together,
  projected by a linear discriminant analysis that separates the 111 candidates across
  donors. It is fitted for each target's band on the renders through the other bands'
  donors only (so never on the target's band), keeping the leading 40 dimensions;
  Euclidean there.

Each row's scaling uses only panel renders, never a judge distance or a pick. Before
the run, 325 of the 4,773 renders (and most half-B clips) turned out to have no loudness
range, too short or quiet to measure: the lean row then compares the fields both clips
have, and the LDA row fills an empty field with its median over the panel renders. A small
CNN's statistics, AFx-Rep and CLAP (round 4's other rows) need training or downloads
and are not in this check.

## Scoring

For a target P, a donor Q and a row: the row's **pick** is the menu candidate whose
render through Q's DI is nearest P's reference. Its **regret** is
log d_judge(P, pick) − min over the menu of log d_judge(P, ·), 0 when the pick is the
judge's best. P's regret is the median over donor bands of each band's median over its
donors, so every donor band counts once. A statistic over parts is the project's band
statistic: the median across the targets' bands of each band's median, so a band with
eight parts counts once. A row's **agreement** is the Spearman correlation, across the
clean menu, between the row's distances (through Q) and the judge's (through P's own
DI), summarised the same way. (On the 111 menu, a ranking that ignores the song,
clean presets first, already reaches about 0.7; on the clean menu it reaches about 0.3.)

**The song-blind constant:** for P, the candidate with the lowest median judge
distance over the parts of the other bands. It uses no audio from P, so a row must beat
it to show it hears the song.

**Stop:** if v3's regret is already at most 0.09 (the judge's near-tie range) on both
menus and band sets, v3 is enough and no row is needed.

**Gate,** per row, on both menus and under both band sets:

1. its regret is at most 0.75 times the song-blind constant's, and at most 0.75 times
   v3's;
2. it beats the constant across bands: a one-sided exact sign-flip test (all 2^9
   flips) on the targets' 9 bands of (row regret − constant regret) band medians,
   p < 0.05 after Holm across the 8 rows tested (every row but v3), within each menu
   and band set. Requiring a pass on every menu and band set is an intersection, which
   needs no further correction. It is strict: the smallest possible p is 1/512, so the
   best row must win in nearly every band;
3. its agreement is at least 0.6;
4. on stems, its regret on the 12 parts is no worse than the constant's there.

A row that passes all four everywhere passes. If the stop holds, v3 is the answer and
the gate is reported for information. Otherwise, if several pass, the one whose highest
regret on stems over the four menu and band-set blocks is lowest is the step's answer, marked to be confirmed on new parts before any
later step (round 4's experiment 13) leans on it. If none passes, no DI-free distance
here reproduces the judge's choices, and the next candidates are those that need
downloads or training (round 4's rows, round 1's approach 3c).

**Reported, not deciding:**

- Reference points: a random pick's expected regret (the mean over the menu), the
  constant pick (the candidate with the lowest median judge distance over the parts of
  the other bands), and the judge's own pick through the part's own DI (0).
- Each row per amp's menu alone, and per band.
- **Own-DI advantage:** for P and each donor Q, a mixed menu of every candidate's
  render through Q and through P's own DI (same notes, same guitar); the share of the
  row's picks that are own-DI renders, summarised as above (0.5 if the row cannot tell
  them apart). It measures how much the take itself, not the tone, moves a row.
- **v3 and v3c distances that come back empty,** which drop a candidate from a pick.
- **Another teacher:** the average-guitar measure (branch `poc/sound-model`,
  `avg-yardstick-distances.json`) covers only the 21 clean PR12 presets and template+R,
  on half B (5.5 to 10 s). On that menu, with every clip cut to half B, each row's
  regret under it, and under the judge's half-B distance on the same menu, side by
  side. It cannot change this check's verdict; a check under that measure would be
  declared on its own.

## Limits

- **The judge is the teacher,** with its blind spots: listening validated it only for
  clear clean-to-crunch PR12 differences.
- **Clean material:** the parts are mostly clean; high-gain matching is not tested.
- **Panel renders through another band's DI** play another player on another guitar:
  that is the product's situation, but the donors' guitars and levels differ from one
  another too, which the median over donors averages over.
- **Stems** come from one separator (htdemucs_6s) on 12 parts.
- **25 parts in 9 bands,** three of them with one part: the band statistic is coarse,
  and the winner, if any, is chosen on the same parts it is scored on.
