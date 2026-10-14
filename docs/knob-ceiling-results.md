# Knob ceiling: results (2026-10-14)

Run under the [plan](knob-ceiling-plan.md) (amendments 1–4, all declared before the results
they govern, except one listening rule: the letter balance of the second sitting was added
after the first sitting was scored; see Listening). It used development data only, with the true DI at the average-guitar measure.

An independent audit reproduced every number and found no leakage
(`tmp/knob-ceiling-results-audit.md`, local). Raw data is under
`~/ndsp-presets/learn/knob-ceiling/`.

## In short

- **Setting the controls beats choosing a preset, by a wide margin, and the ear agrees.**
  - A search over the amp knobs, input gain and both mics, starting from the best of the 111
    menu presets, lands **about 19% closer** to the record by the judge, on the half of the
    clip it never saw (−0.205 mean log ratio, 14 of 14 bands).
  - The amp's EQ adds about another 8%.
  - In a blind listening check (one listener, a second sitting of the same 7 trials), the
    searched settings were chosen over the best menu preset on **7 of 7** trials.
- **The gain belongs to each recording, not to a generic judge preference.** Another part's
  searched settings score worse than the menu preset (+0.229), while a part's own settings
  beat the other parts' by −0.434 (14 of 14 bands). (That can't rule out the search exploiting
  the judge on each recording; listening is the guard.)
- **The menu was never near the ceiling.** That holds by the judge, with the true DI, within
  one take, on development, and with one listener. Every "a perfect DI buys only 12–17%" figure
  was the menu's limit. Predicting settings, not ranking presets, is the direction from here.
- **Both readings are lower bounds.** The search is known to fall short of reachable
  settings: by about 0.075 on average in its realistic control (amendment 2).

## Numbers

Each search ran on one half of the 10-s clip and was scored on the other (cross-half), both
ways, then averaged. Negative is closer. There are 72 cells (24 parts × 3 amps): Honey was
dropped, because the judge refuses its half B. That leaves 14 bands.

| comparison | clean + crunch | clean (9 bands) | crunch (5 bands) |
|---|---|---|---|
| **(a)** best menu preset (M) vs the product's start (S) | −0.091 | −0.065 | −0.193 |
| **(b) knobs from M (K_M) vs M** | **−0.205** [−0.274, −0.136], 14/14 bands | −0.220 | −0.148 |
| **(c) knobs from S (K_S) vs S** | **−0.253** [−0.324, −0.182], 14/14 | −0.245 | −0.284 |
| K_S vs M | −0.162, 14/14 | −0.180 | −0.091 |
| **(d) EQ on top of K_M, vs K_M** | −0.079 [−0.117, −0.040], 14/14 | −0.086 | −0.050 |
| EQ vs M (knobs and EQ together) | −0.284 | −0.307 | −0.198 |

The table gives the part-weighted mean, the band-clustered 90% interval and the bands that
improved. The band-weighted means are within 0.04 of these, except clean EQ vs M (−0.358).

- **Per amp, (b), part-weighted:** PR12 −0.205, SW50R −0.214, AC20 −0.197, each 14/14 bands.
- **Taking each part's best amp,** M against K_M: −0.201.
- **The convergence of (b)** on the held half: −0.130 after 25 renders, −0.166 after 50,
  −0.190 after 100, −0.205 after 200. Most of the gain comes early.
- **(a) reproduces the old menu headroom only roughly:** 9–10%, against the earlier 12–17%,
  which came from other parts and settings.
- **The declared reading** for (b) is "knobs add a lot by the judge" (band-weighted −0.206,
  14/14). For (d) it is "in between" (band-weighted −0.094): a lower bound, and leaning on one
  part.
  - Without `cambridge-magilla-elecgtr1dt` it is −0.069 band-weighted.
  - On clean alone it reads "a lot" (−0.119, 9/9).
- **The share of K_M searches with a setting at a range limit is 93%,** mostly cab position or
  distance at 0 or 1. Input gain sat at its −20 dB floor in 47 of 144 runs.

## Controls

- **Repeats:** a search's first render repeats a stored menu render. The largest deviation is
  1.0e-4 (log), against a stop rule of 0.005.
- **Leakage: none.** M, the search, the stored best and the EQ start all use only the search
  half. The held half is read before the search only by the declared refusal rule.
- **In-sample ≈ cross-half.** This is a cancellation: K and M are both about 0.03 optimistic
  on the half they were picked on. It shows the gain carries across the notes of one take, not
  across songs.
- **Render order.** The run found that Morgan's own reset leaves the previous render audible
  at hiss level for 2–3 s. 55 cells rebuild the plugin's render resources before every render
  (`isolate`); the first 20 cells used an equivalent 6-s pre-roll (amendment 3). The earlier
  pipelines' exposure is audited in [render-order-audit.md](render-order-audit.md).

## Is it the judge? The cross-part check (amendment 4)

The found settings share a direction across parts:
- less drive: input gain at the −20 dB floor of the searched range in 47 of 144 K_M runs;
- less bass and darker;
- EQ edge bands often at ±12 dB.

That could be the judge's taste rather than a match to the record. So every other part's best
settings (same amp, same direction) were rendered through each part's DI and scored on its held
half (about 6,600 renders):

| | clean + crunch | clean | crunch |
|---|---|---|---|
| **part-specific:** own K_M vs the median of the other parts' K_M | **−0.434**, 14/14 bands | −0.390 | −0.600 |
| **generic:** the median of the other parts' K_M vs M | **+0.229**, 0/14 | +0.170 | +0.452 |
| part-specific, EQ stage | −0.565, 14/14 | −0.533 | −0.687 |
| generic, EQ stage | +0.281, 0/14 | +0.226 | +0.489 |

**Another part's settings are about 26% further from the record than the menu preset.** The
shared direction doesn't carry over: what the search found fits each recording. So the
reading is "part-specific", not "mostly generic".

## Listening (amendment 4)

The held half only, blind. Each trial played the record, then the menu preset M, the knob
search K_M, and the EQ stage where it added at least 0.04 by the judge.

**The trials:**
- the 4 largest K_M gains;
- 2 random cells;
- 1 cell with an EQ edge band at ±12 dB, to hear the judge's spectral weakness.

That is 5 parts in 4 bands, with only 1 crunch part. `cambridge-magilla-elecgtr1dt` is 3 of
the 7, and 4 trials were chosen for the largest judge gain.

- **Sitting 1 is confounded by position.** M sat on letter A in only 1 of 7 trials. The
  listener answered A on 6 of 7, and picked K_M or EQ every time (M 0 of 7).
- **Sitting 2 was a second listen,** with the same 7 trials in the same order, by the same
  listener. Its rule was added to amendment 4 after sitting 1 was scored: M takes the least-used
  letter (A 2, B 2, C 3).
  - **The result:** a searched option was chosen on **7 of 7** trials. K_M won 4 and the EQ 3,
    including the ±12 dB EQ cell. M won none. On trial 7 the listener noted the EQ was "also
    close".
- **How strong that is:**
  - Under uniform guessing, M is never picked with probability 0.025.
  - But the listener never answered C in sitting 2, where M sat 3 times. For a listener who
    never picks C, the chance is about 0.06.
  - The stronger evidence: in trials 2, 3 and 6 the letters moved between the sittings, and
    the pick followed the sound, not the letter.
- **Descriptive, as declared:** one listener, development parts, cells chosen mostly for the
  largest gain.

## What it means

- **For the goal:** generating settings, not choosing presets, is where the accuracy is.
  Even from the product's own starting preset, a search reaches about 22% closer (c).
- **For ML:** the earlier chooser, rebuilt DI and translator results only ever ranked the
  menu. The question now is how to predict or search settings **from a song alone**. That is:
  - an amortised song-to-settings model;
  - a search scored without a DI, or through a rebuilt DI;
  - or both.

  The cloud research brief (`tmp/preset-generation-research-prompt.md`, local) asks exactly
  this.

**Limits:**
- **The true DI.** A song-only product must estimate or replace it.
- **Within-part.** The gain carries across notes of one take, not yet across songs.
- **A lower bound.** The search falls short of reachable settings.
- **Development only.** 24 parts in 14 bands were scored (Honey dropped); crunch has 5 bands.
- **The pedals and effects weren't searched,** and input gain was capped at −20 dB.
- **One listener.**
