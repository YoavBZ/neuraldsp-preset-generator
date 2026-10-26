# Where the tone information is lost: a probe on F5's examples (declared 2026-10-27, zero renders; read the same day)

**Why.** T3's R0 ([F5 follow-up](trusted-data-t0-design.md#r0-outcome-2026-10-26-zero-renders-t3followup-rr0json))
found that D_F5 reads 20 of 116 heads on FS5 from the X-LANCE stem, and no amp knob. A rough probe (F5 outcome) read
reverb and delay from the target render (AUC 0.70 and 0.73) but hardly from the stem (0.52, 0.59) or the mix (0.53,
0.58). This probe asks where on the way from the rendered guitar to the model's input the information goes. The user
approved it on 2026-10-27. Declared here and in the ledger (`trusted-data-t3`, amendment 2) before anything is
computed. **Descriptive, zero renders, zero separations, no training beyond the linear probes; it decides nothing.**

**Three explanations to separate**, per family:
- **the separator loses it:** the target reads, the stem does not, and the loss sits between the mix and the stem;
- **the mix hides it:** the target reads, the mix and the stem do not, and the loss sits between target and mix;
- **the features or the model can't carry it:** even the target does not read.

## Data

F5's examples only, as stored (`t3/`; their mixes and stems are built on T2's stored other guitars and backings):
- **Probe training:** F5's 3,467 training examples (59 sections, 4 bands), the set D_F5 trained on.
- **Read:** FS5's 722 examples (12 sections), the set R0 read. The same split as D_F5 and R0, section-disjoint.
- **Labels:** the full twins' (`full_space.label_of` on the render rows), encoded as D_F5's (`full_space.encode`).
- No V-real, K or held-out data is read. Outputs go to `~/ndsp-presets/learn/trusted-data/tone-probe/` only; `t0/`,
  `t2/` and `t3/` are read, never written.

## The inputs

| Input | What | Source |
|---|---|---|
| **(a) target** | the full-twin render: the clean DI through the preset | `tgt-t3` half mels |
| **(b) mix** | the self-built mix (SYN) | `mix-t3` half mels |
| **(c) stem** | the X-LANCE stem, D_F5's input | `xlance_g-t3` half mels |
| **(d) target + DI** | (a) with the DI's own summary beside it | the section's DI as rendered (`song_bank.measure` of `pretrain_set.section_audio`, trimmed as the target), `halves_mel` |
| **(e) target, richer** | the target render's audio, a finer representation | `t3/audio/*-target.flac` |
| **(n) DI alone** | negative control: the DI's summary and nothing of the preset | as (d) |
| *beside* | D_F5 itself (its CNN on (c)) | R0's rows, `t3/followup-r/r0.json` |

- **(a)–(d) and (n) use the model's representation**: the stored 96-band half mels (`pretrain_set.halves_mel`,
  uint8, 0.5 dB steps from −112 dB, 30 Hz–16 kHz, 10 ms hop), half A's first second masked as in training.
- **(e)** reads the same 1–10 s of the stored target audio with a 4,096-point STFT at a 5 ms hop, pooled into 160
  log-spaced bands from 30 Hz to 24 kHz, in dB without quantisation. It tests whether the mels themselves drop
  something that the target audio still holds.
- **Stereo is not testable.** Every stored render is mono (the renderer's output is averaged to mono before it is
  saved), so any stereo control (doubler spread, cab pans, stereo) has lost that part of its sound before every input.
  Recovering it needs renders; this probe has none.

## The probe

The same probe for every input:
- **Summary per half** (96 bands, frames after the mask): each band's mean, standard deviation, 10th, 50th and 90th
  percentile, and mean absolute frame-to-frame change; 8 band groups' power envelopes, each with its normalised
  autocorrelation at 16 lags (10 ms to 1.8 s) and the 5th, 25th, 75th and 95th percentile of its frame-to-frame change;
  the broadband envelope's mean, standard deviation, 10th and 90th percentile. The two halves' summaries are averaged.
  (e) uses the same summary on its 160 bands (lags scaled to the 5 ms hop, same times).
- **Conditioning:** the amp and the class, one-hot, as D_F5 is conditioned; the amp head reads the audio only.
- **Model:** ridge regression per head on features standardised on the probe-training set. The penalty is picked from
  a fixed grid (10^−1 to 10^7) by 5-fold section-grouped cross-validation on the probe-training set only: mean
  absolute error for knobs, AUC for switches, accuracy for the mics and the amp.
  - **Knobs** predict the residual from D_F5's constant (`fit.json`, per amp and class, the constant R0 used), clipped
    to the unit interval, so the largest penalty returns the constant.
  - **Switches:** the ridge score, ranked.
  - **Mics and amp:** one-vs-rest ridge on the classes, the argmax.
  - Each head trains on the examples where it is scored (sounding knobs, scored switches, sounding mics), as D_F5's
    masked loss.

## The read

- **Per head and input: R0's rule, unchanged** (`trusted_data_t3_r.r0_rows`): knobs by E against D_F5's constant
  (|answer − label| − |constant − label|, unit space, where the dimension sounds; 90% section-clustered t over the
  12 sections); switches by AUC (90% delete-one-section jackknife t); the amp by accuracy against D_F5's training
  majority amp; the mics by accuracy against the constant's mic mode (90% section-clustered t). **Readable** iff the
  interval excludes chance in the right direction.
- **Per family and input:** the readable count, and the median gain over chance: AUC − 0.5 over the family's
  switches, the constant's E minus the probe's over its knobs, accuracy over base for the amp and mics.
- **The steps, per head, paired on the same examples:** mix step (a) − (b), separator step (b) − (c), DI (d) − (a),
  representation (e) − (a). Knobs and accuracies by the per-example difference, section-clustered 90% t; switches by
  the AUC difference, delete-one-section jackknife 90% t. A step is **reliable** if its interval excludes 0.
- **Where each head is lost** (declared order):
  1. **survives:** readable on (c);
  2. otherwise, unreadable on (a): **richer features** if readable on (e); else **needs the DI** if readable on (d);
     else **not carried**;
  3. otherwise (readable on (a), not on (c)): **mix** if only the mix step is reliable (better on (a) than (b));
     **separator** if only the separator step is (better on (b) than (c)); **both** if both are; **unresolved** if
     neither is.

  Tallied per family. The family's verdict is its largest tally, the others printed beside.
- **Negative control (n):** the DI alone should read about as many heads as chance gives (about 6 of 116). More
  than about 12 means the probe or the split leaks, and the read is flagged.

## Addition: are "on" effects audible? (declared 2026-10-27, before it is computed)

**Why.** The user's hypothesis, sent by the coordinator after the main read had run: many effects may be labelled
"on" at settings too faint to hear (a low delay or reverb mix, a shallow tremolo, a spring at its least level
`SPRING_MIN` = 1e−3). Such labels are unreadable by construction. Zero renders.

**The proxy, per switch** (the label's unit-space value, as `full_space.encode` stores it):

| Switch | Audibility proxy |
|---|---|
| `reverb/reverbActive` | `reverb/reverbMix` |
| `delay/delayActive` | `delay/delayMix` |
| `tremolo/tremoloActive` | `tremolo/tremoloDepth` |
| `pr12Amp/springOn`, `sw50rAmp/springOn` | `pr12Amp/pr12Reverb`, `sw50rAmp/sw50rReverb` (the spring's level) |

**What is shown:**
- **The distribution** of each proxy among "on" labels in F5's examples (probe training and FS5 together): quantiles
  (min, 10, 25, 50, 75, 90%, max) in unit space and in the plugin's own values, by draw mode (factory, start, wide)
  and overall, and the share of springs "on" at exactly `SPRING_MIN`.
- **Readability restricted:** for inputs (a), (b) and (c), the same probes' scores (refitted exactly as in the main
  read, deterministic; not retrained on the subset) read on FS5 with "off" examples against only the "on" examples
  whose proxy is at or above a cut. **The cuts are the proxy's tertiles and median among "on" labels in the
  probe-training set** (FS5 does not set them). Primary: **the top third** against "off". Beside: the top half, the
  bottom third, and all "on" (the main read). R0's rule: AUC with the 90% delete-one-section jackknife; readable iff
  the lower end is above 0.5. FS5 cells with fewer than 2 sections holding both classes have no interval.
- **Wording, declared:** "rises sharply" if the top third's AUC is at least 0.10 above the all-"on" AUC for that
  input; said plainly per switch and input.

## Outcome (2026-10-27, zero renders; `tone-probe/probe.json`, `tone-probe/audible.json`)

Run once after the declarations above were committed (main read d2ffe28, the addition a3e2aed). Probe-trained on
3,467 examples in 59 sections, read on FS5's 722 in 12. T0's lists changed at 00:49 the same day (another session's
ear update, after the declaration); the probe reads T3's stored sets as planned, so the list-hash check was recorded,
not enforced. Features took 2 minutes on 4 processes, the read 8.

**The mix hides the tone. The separator loses a little more. The features carry most of it.**

| Input | Readable of 116 | Knobs (of 85) | Switches (of 28) |
|---|---|---|---|
| (a) target | **86** | 55 | 28 |
| (b) mix | 30 | 11 | 18 |
| (c) stem | 20 | 5 | 14 |
| (d) target + DI | 85 | 54 | 28 |
| (e) target, richer | 87 | 57 | 27 |
| (n) DI alone (negative control) | 8 | 3 | 5 |
| D_F5 on the stem (R0, beside) | 20 | 5 | 14 |

Per family: readable/heads · median AUC − 0.5 (switches) · median E gain ×100 (knobs; the constant's E minus the
probe's, unit space) · accuracy gain (amp, mics):

| Family | (a) target | (b) mix | (c) stem | (d) target + DI | (e) richer | (n) DI alone | D_F5 (R0) |
|---|---|---|---|---|---|---|---|
| Today's space | 24/25 · +0.22 · +2.3 · +0.25 | 4/25 · +0.07 · −0.1 · −0.02 | 3/25 · +0.05 · −0.2 · −0.01 | 22/25 · +0.22 · +2.3 · +0.23 | 22/25 · +0.19 · +2.6 · +0.28 | 1/25 · +0.02 · −0.3 · −0.03 | 5/25 · +0.08 · −0.1 · −0.00 |
| Amp choice | 1/1 · +0.26 | 1/1 · +0.11 | 1/1 · +0.09 | 1/1 · +0.23 | 1/1 · +0.30 | 0/1 · −0.03 | 1/1 · +0.07 |
| Amp EQ | 25/36 · +0.25 · +2.4 | 9/36 · +0.05 · −0.0 | 4/36 · +0.07 · +0.0 | 24/36 · +0.27 · +2.3 | 29/36 · +0.31 · +2.2 | 2/36 · +0.00 · −0.0 | 4/36 · +0.04 · +0.0 |
| Pedals | 8/14 · +0.24 · +0.6 | 3/14 · +0.08 · −0.2 | 3/14 · +0.10 · −0.1 | 9/14 · +0.24 · +0.5 | 8/14 · +0.24 · +0.7 | 2/14 · +0.07 · −0.2 | 4/14 · +0.09 · −0.1 |
| Time effects | 13/19 · +0.23 · +2.6 | 5/19 · +0.07 · −0.0 | 3/19 · +0.05 · −0.1 | 13/19 · +0.24 · +2.2 | 13/19 · +0.23 · +2.2 | 0/19 · −0.02 · −0.2 | 1/19 · −0.00 · +0.0 |
| Spring | 2/5 · +0.22 · +0.9 | 2/5 · +0.10 · −0.2 | 0/5 · +0.06 · −0.3 | 2/5 · +0.22 · −0.0 | 2/5 · +0.22 · −0.0 | 0/5 · −0.04 · +0.0 | 0/5 · −0.01 · −0.3 |
| Gate and doubler | 3/4 · +0.25 · +2.7 | 1/4 · +0.06 · +0.2 | 1/4 · +0.04 · −0.1 | 3/4 · +0.26 · +2.6 | 3/4 · +0.29 · +3.0 | 0/4 · −0.01 · −0.2 | 1/4 · +0.05 · +0.0 |
| Cab rest | 10/12 · +0.28 · +3.4 | 5/12 · +0.08 · +0.0 | 5/12 · +0.08 · −0.3 | 11/12 · +0.27 · +3.5 | 9/12 · +0.26 · +3.5 | 3/12 · +0.01 · −0.5 | 4/12 · +0.05 · +0.1 |

**Where each head is lost** (the declared order): mix 55, survives 20, not carried 20, both 12, richer features 7,
needs the DI 2, separator alone 0. The verdict is "mix" in today's space, amp EQ, pedals, time effects and gate and
doubler; "survives" in cab rest and the amp choice; "not carried" in the spring (3 of 5, the other 2 mix).

- **The mix step is the big loss:** 87 heads read reliably worse from the mix than from the target, none better.
  Today's knobs go from 24 of 25 readable to 4; the amp EQ from 25 of 36 to 9; reverb's switch from AUC 0.75 to 0.60,
  delay's from 0.81 to 0.66, tremolo's from 0.72 to 0.55.
- **The separator adds a smaller loss:** 18 heads read reliably worse from the stem than from the mix (12 of them
  already lost at the mix), 1 better. Readable heads go from 30 to 20.
- **The features are not the bottleneck:** the target reads 86 of 116 with a linear probe on summaries of the
  model's own mels; the finer, unquantised representation (e) reads 87, its step reliable either way about equally
  often (18 better, 12 worse). The PR12's and AC20's volume (not the SW50R's), reverb and delay mix, and the amp choice (accuracy +0.26 over the
  base rate) read from the target.
- **The DI adds nothing:** (d) reads 85, 2 heads reliably better and 13 worse (more dimensions, same examples).
- **The negative control holds:** the DI alone reads 8 of 116, under the declared flag of 12.
- **D_F5 is no better than the linear probe on its own input:** 20 readable on the stem, as the probe; its time
  effects read 1 of 19 against the probe's 3 (reverb AUC 0.49 against 0.58).

**Caveats:**
- The target carries its absolute level, set partly by the preset. The mix is built to a target loudness at a drawn
  guitar-to-backing ratio, so whatever the level told is gone from (b) and (c) by construction. Part of "the mix
  hides it" is that normalisation, not masking; this read does not split the two.
- The 7 "richer features" heads are about what chance gives one column (about 6).
- A linear probe is a lower bound; a model trained on the target could read more, not less.

### The audibility addition

"On" labels are often faint, but few are near zero:

| Switch | On-rate | Proxy, median among "on" (unit; factory / start / wide) | "On" with proxy below 0.05 / 0.1 |
|---|---|---|---|
| Reverb | 0.55 | mix 0.30 (0.27 / 0.19 / 0.54) | 7% / 12% |
| Delay | 0.49 | mix 0.30 (0.25 / 0.19 / 0.53) | 8% / 16% |
| Tremolo | 0.33 | depth 0.54 (0.56 / 0.61 / 0.49) | 4% / 8% |
| PR12 spring | 0.51 | level 0.44 (factory 0.42, wide 0.49) | 6% / 11% |
| SW50R spring | 0.43 | level 0.31 (factory 0.25, wide 0.52) | 10% / 17% |

Factory and start draws are the faint ones (reverb mix 25–75%: 0.16–0.38 factory, 0.12–0.28 start). Springs sit at
`SPRING_MIN` in 2.2% (PR12) and 3.7% (SW50R) of "on" labels. The plugin values are the unit values (these knobs run
0 to 1). The below-0.05 and below-0.1 shares were added after the declaration (descriptive).

AUC on FS5, "off" against "on" above the cut (R0's rule; R = readable):

| Switch | Input | All "on" | Top third | Top half | Bottom third | Rises sharply (≥ +0.10) |
|---|---|---|---|---|---|---|
| Reverb | (a) | 0.75 R | 0.87 R | 0.82 R | 0.64 R | **yes** |
| | (b) | 0.60 R | 0.63 R | 0.62 R | 0.58 R | no |
| | (c) | 0.58 R | 0.63 R | 0.61 R | 0.55 R | no |
| Delay | (a) | 0.81 R | 0.92 R | 0.89 R | 0.71 R | **yes** |
| | (b) | 0.66 R | 0.79 R | 0.76 R | 0.52 | **yes** |
| | (c) | 0.62 R | 0.73 R | 0.69 R | 0.54 | **yes** |
| Tremolo | (a) | 0.72 R | 0.81 R | 0.76 R | 0.66 R | no (+0.09) |
| | (b) | 0.55 R | 0.58 R | 0.56 R | 0.55 | no |
| | (c) | 0.52 | 0.52 | 0.51 | 0.56 | no |
| PR12 spring | (a) | 0.73 R | 0.77 R | 0.75 R | 0.67 R | no |
| | (b) | 0.59 R | 0.63 R | 0.60 R | 0.60 R | no |
| | (c) | 0.57 | 0.62 R | 0.59 | 0.56 | no |
| SW50R spring | (a) | 0.72 R | 0.78 R | 0.75 R | 0.70 R | no |
| | (b) | 0.61 R | 0.62 | 0.61 R | 0.58 | no |
| | (c) | 0.56 | 0.52 | 0.56 | 0.59 | no |

- **Faint labels explain part of it, and only the delay rises sharply after the mix:** its stem AUC goes from 0.62
  to 0.73 on the loudest third, and its faintest third does not read from the mix or the stem.
- **Reverb, tremolo and the springs stay weak from the stem even at their loudest third** (0.63, 0.52, 0.62, 0.52),
  while the target reads them at 0.77–0.87. So for these, the loss is the mix, not inaudible labels.
- The tremolo's depth is not its whole audibility (its level and rate matter too); the proxy is the declared one.

## Limits

- **A linear probe on summaries is a lower bound** on what an input carries. "Not carried" means not by these
  features and this probe; D_F5's own row (a CNN on (c)) is printed beside (c) for scale.
- About 116 heads at 90% two-sided per input: about 6 null heads read by chance in each column, no correction.
- FS5 is self-built mixes. Readable there does not mean readable on real songs.
- `song_bank.measure` EQs every DI to the average guitar before rendering, so (d)'s DI carries less identity than the
  raw file.
- The paired steps compare different probes on the same examples; a reliable mix step says the mix loses something
  this probe could use, not everything.

## Cost

Zero renders and zero separations. It reads about 4.2k examples' three feature files and their target audio, and the
71 DI sections' audio, on the CPU with at most 4 processes. About half an hour.

## Code

`learn/tone_info_probe.py` (written after this declaration):
`$MAIN -m learn.tone_info_probe features` (the summaries, cached in `tone-probe/`), then `$MAIN -m learn.tone_info_probe read` (the table, `tone-probe/probe.json`). The addition: `$MAIN -m learn.tone_info_probe audible` (`tone-probe/audible.json`).
