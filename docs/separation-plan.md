# Separation plan: one guitar part from a real song

**Status:** declared 2026-11-14, on the user's "I allow working on the separator in any promising way, including
creating/retraining/using other tools and approaches … the final result is simply not good on real songs". Nothing has
run yet. Ledger `separation`.

## Why

The model now reads a separated guitar well on known-truth units (F80–F90). On real songs the input is the weak link.
X-LANCE `gtr_mss` returns every guitar plus bleed. The user's picker (R1 Amendment 4) found leaks in most songs,
even in the best version ("Still many leaks though"), and the centre mask helped on 5 of 7. The model can't be better
than what it hears.

## The goal and the stop rule

One guitar part, the one the user names, as clean as an existing or a new tool can make it. Each step is decided by
the measuring stick (S0) on held-out mixes, then by the user's ear on R1's songs. A step that doesn't gain on S0 stops
there. The steps run in cost order, cheapest first.

## S0, the measuring stick (zero renders)

Real songs have no ground truth, so every option is first measured on known-truth stereo mixes.

- **The mixes:** E1e's items rebuilt in stereo by D_CC's recipe. The target is the item's guitar (its render, as
  drawn). The "others" track holds the session's other guitars, and the backing holds the rest. Panning follows
  common practice: the target within ±0.15 of centre, each other guitar at ±0.6 to ±1.0 (seeded), bass, kick, snare
  and vocals centred, the other backing parts within ±0.5. The drawn ratio and mastering are kept.
  - 200 items, stratified by band; the bands any later training uses are held out of S0's read.
- **The scores, per option:**
  - the target's SI-SDR on half A;
  - the other guitars' leak (the stem's energy correlated with the others track, against the target's);
  - the model's read: the cosine of the adopted model's floored body features (the amp pick's own measure) between
    the stem and the clean target, both at the product's input level.
  - All are reported by band with a band bootstrap, against today's input (X-LANCE on the mono mix).

## S1, existing tools (zero training)

- **(a)** X-LANCE fed the true stereo channels, the mean of its two outputs. Until now it got the mono mix twice.
- **(b)** The picker's centre mask, then X-LANCE.
- **(c)** Mega-53's guitar and electric-guitar stems.
- **(d)** An agreement ensemble: per STFT bin, the smaller of X-LANCE's and Mega-53's magnitudes, with X-LANCE's
  phase.
- **(e)** X-LANCE run again on its own stem.
- **(f)** (b) with the mask's exponent at 2 and at 8, beside 4.
- **The rule:** an option wins if its SI-SDR gain over today's is above 0 on the band bootstrap and it loses nothing
  on the model's read. The best one or two go on the user's picker for R1's songs. If the best gains under 1 dB,
  S2 and S3 start.

## S2 and S3, declared later on S1's evidence and the cloud researcher's survey

- **S2, targeted extraction:** pull the named part only, for example query-by-example from a stretch where it plays
  clearly, test-time adaptation of X-LANCE on the song itself, or an open prompt-based model. Any download goes to
  the user first, with its size.
- **S3, our own lead-versus-rest separator:** fine-tune X-LANCE (or train a RoFormer) on thousands of stereo mixes
  built as in S0 from our multitracks, with the other guitars as the leak to remove. MPS over nights, no rented
  machines. The bands S0 reads stay out of training.

## What it can't say

S0's mixes are built, not mastered records. Their panning is drawn, not each song's own. So S0 ranks the options,
and the user's ear on real songs decides.
