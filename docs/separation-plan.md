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
  drawn). The "others" track holds the session's other guitars, and the backing holds the rest. Bass, kick, snare and
  vocals are centred, and the other backing parts sit within ±0.5. The drawn ratio and mastering are kept. The
  target's placement takes one of three strata, about a third each, seeded (the review: a centred lead alone would
  favour the centre mask by construction, and the user's part isn't always the centred lead):
  - **centred lead:** the target within ±0.15, each other guitar at ±0.6 to ±1.0;
  - **off-centre target:** the target at ±0.4 to ±0.8, with another guitar opposite or centred;
  - **double-tracked target:** the target on both sides at ±0.6 to ±1.0 with a slight offset, and another guitar
    centred.
  - 200 items, stratified by band; the bands any later training uses are held out of S0's read.
- **The scores, per option:**
  - the target's SI-SDR on half A;
  - the other guitars' leak (the stem's energy correlated with the others track, against the target's);
  - the model's read: the cosine of the adopted model's floored body features (the amp pick's own measure) between
    the stem and the clean target, both at the product's input level.
  - beside, the effects row (since better stems also serve R3): the stem's cepstral delay hit and T0's delay vote;
  - all are reported per stratum and by band, with a band bootstrap, against today's input (X-LANCE on the mono mix).

## S1, existing tools (zero training)

- **(a)** X-LANCE fed the true stereo channels, the mean of its two outputs. Until now it got the mono mix twice.
- **(b)** The picker's centre mask, then X-LANCE.
- **(c)** Mega-53's guitar and electric-guitar stems.
- **(d)** An agreement ensemble: per STFT bin, the smaller of X-LANCE's and Mega-53's magnitudes, with X-LANCE's
  phase.
- **(e)** X-LANCE run again on its own stem.
- **(f)** (b) with the mask's exponent at 2 and at 8, beside 4.
- **The rule:** an option wins if its SI-SDR gain over today's is above 0 on the band bootstrap and it loses nothing
  on the model's read, meaning the paired cosine interval isn't wholly below 0. It's read per stratum: an option
  that wins only on the centred lead goes on the picker as a choice, not as the default. The best one or two go on
  the user's picker for R1's songs.
- **The trigger for S2 and S3:** the best gains under 1 dB, or the user's ear still finds the best S1 option leaky
  on R1's songs. Each of S2 and S3 carries its own stop rule when declared: a held-out S0 gain and a budget of
  nights.

## S2 and S3, declared later on S1's evidence and the cloud researcher's survey

- **S2, targeted extraction:** pull the named part only, for example query-by-example from a stretch where it plays
  clearly, test-time adaptation of X-LANCE on the song itself, or an open prompt-based model. Any download goes to
  the user first, with its size.
- **S3, our own lead-versus-rest separator:** fine-tune X-LANCE (or train a RoFormer) on thousands of stereo mixes
  built as in S0 from our multitracks, with the other guitars as the leak to remove. MPS over nights, no rented
  machines. The bands S0 reads stay out of training.

## What it can't say

S0's mixes are built, not mastered records. Their panning is drawn, not each song's own. E1e's targets are mono, so
stereo tails that a centre mask would strip (reverb, delay, chorus width) aren't in S0. The ear has to check those.
So S0 ranks the options, and the user's ear on real songs decides.
