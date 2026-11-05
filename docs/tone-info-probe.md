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

## Outcome (2026-10-27, zero renders; `tone-probe/probe.json`, `audible.json`, `posthoc.json`)

Run once after the declarations above were committed (main read d2ffe28, the addition a3e2aed). Probe-trained on
3,467 examples in 59 sections, read on FS5's 722 in 12. T0's lists changed at 00:49 the same day (another session's
ear update, after the declaration); the probe reads T3's stored sets as planned, so the list-hash check was recorded,
not enforced. Features took 2 minutes on 4 processes, the read 8.

**The target render holds most of the tone (86 of 116). The mix hides most of it from a linear reader (30). The
stem gets none of it back and is slightly worse (20). The fixable loss is the separator failing to recover what the
mix masks: a 66-head gap that a better stem or a mix-aware model must close.**

**Next steps this points to:**
1. A model fed the mix, or the mix plus the stem, is the cheap first try.
2. Fine-tune X-LANCE on our self-built mixes against their known targets.
3. Different features are not needed: (e) adds nothing.

| Input | Readable of 116 | Knobs (of 85) | Switches (of 28) |
|---|---|---|---|
| (a) target | **86** | 55 | 28 |
| (b) mix | 30 | 11 | 18 |
| (c) stem | 20 | 5 | 14 |
| (d) target + DI | 85 | 54 | 28 |
| (e) target, richer | 87 | 57 | 27 |
| (n) DI alone (negative control) | 8 | 3 | 5 |
| *Post hoc, from the review:* | | | |
| target, level removed | 91 | 60 | 28 |
| target loudness alone | 33 | 9 | 23 |
| conditioning alone (amp and class, no audio) | 6 | 1 | 5 |
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
  Today's space (knobs, switches, mics) goes from 24 of 25 readable to 4; the amp EQ from 25 of 36 to 9; reverb's switch from AUC 0.75 to 0.60,
  delay's from 0.81 to 0.66, tremolo's from 0.72 to 0.55.
- **The separator adds a smaller loss:** 18 heads read reliably worse from the stem than from the mix (13 of them
  already lost at the mix), 1 better. Readable heads go from 30 to 20.
- **The features are not the bottleneck:** the target reads 86 of 116 with a linear probe on summaries of the
  model's own mels, reliably but modestly for the knobs: the 55 readable knobs gain a median 3.1 points of their range
  over the constant (2.3 in today's space), against the constant's own error of about 17 points; the finer, unquantised representation (e) reads 87, its step reliable either way about equally
  often (18 better, 12 worse). The PR12's and AC20's volume (not the SW50R's), reverb and delay mix, and the amp choice (accuracy +0.26 over the
  base rate) read from the target.
- **The DI adds nothing:** (d) reads 85, 2 heads reliably better and 13 worse (more dimensions, same examples).
- **The negative control holds:** the DI alone reads 8 of 116, under the declared flag of 12. The conditioning alone
  (amp and class, no audio; post hoc) reads 6, so the DI's 8 is the conditioning, not leakage, and the stem's audio
  carries about 15 heads beyond it.
- **D_F5 is no better than the linear probe on its own input:** 20 readable on the stem, as the probe; its time
  effects read 1 of 19 against the probe's 3 (reverb AUC 0.49 against 0.58).

**Caveats:**
- **Level does not inflate (a)** (post hoc, the review's re-run, reproduced by `posthoc`): with the target's
  level-carrying summaries (per band mean and percentiles, broadband mean and percentiles) taken relative to its
  loudness, as the mix is normalised, the target reads 91 (60 knobs, 28 switches). Its loudness alone reads 33. So
  the drop to the mix is masking, not the mix's loudness normalisation.
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

## Addition: mix plus stem, (f) (declared 2026-10-27, post hoc, before it is computed)

**Why.** The outcome's first next step is a model fed the mix, or the mix plus the stem. This asks, at zero renders,
whether the two together carry more than the mix alone. Post hoc and descriptive: (b) and (c) are already read.

- **(f) mix + stem:** the mix's and the stem's summaries side by side (`mix-t3` and `xlance_g-t3`), with the
  conditioning as (b) and (c). The same probe, split (F5's training examples, FS5) and readable rule as (a)–(c).
- **Beside:** (b), (c) and the conditioning alone (amp and class, no audio), refitted the same way.
- **Read:** readable counts per family for (f), (b), (c) and the conditioning; the number of heads (f) reads that (b)
  does not, and that neither (b) nor (c) reads; and the paired step (f) − (b) per head, as the main read's steps
  (reliable if its 90% section-clustered interval, jackknife for AUC, excludes 0), counted both ways.
- Code: `$MAIN -m learn.tone_info_probe mixstem` (`tone-probe/mixstem.json`).

**Outcome (2026-10-27, run once after the declaration, 5f60bd0):** mix plus stem reads no more than the mix alone.

| Family | (f) mix + stem | (b) mix | (c) stem | Conditioning alone |
|---|---|---|---|---|
| Today's space | 3/25 | 4/25 | 3/25 | 1/25 |
| Amp choice | 1/1 | 1/1 | 1/1 | 0/1 |
| Amp EQ | 6/36 | 9/36 | 4/36 | 1/36 |
| Pedals | 3/14 | 3/14 | 3/14 | 3/14 |
| Time effects | 5/19 | 5/19 | 3/19 | 0/19 |
| Spring | 1/5 | 2/5 | 0/5 | 0/5 |
| Gate and doubler | 1/4 | 1/4 | 1/4 | 0/4 |
| Cab rest | 4/12 | 5/12 | 5/12 | 1/12 |
| **All 116** (knobs, switches) | **24** (8, 15) | **30** (11, 18) | **20** (5, 14) | **6** (1, 5) |

- **(f) reads 3 heads that (b) does not:** AC20 EQ band 5, SW50R EQ band 6 and the left cab's switch. Two of them
  (SW50R band 6, the left cab) neither (b) nor (c) reads. That is about what chance gives.
- **(b) reads 9 that (f) does not**, and the paired step favours the mix alone: (f) reliably better than (b) on 3
  heads, (b) better than (f) on 11.
- **Reading:** to a linear reader, the stem adds nothing to the mix, and its extra 740 dimensions cost a little. This
  does not rule out a trained model using the two together; it says the stem holds no tone the mix lacks that a
  linear probe can find.

## Addition: the mix on its dominant cells (declared 2026-11-05, before it is computed)

**Why.** This probe's main finding is the loss between the target and the mix: 86 heads, then 30. Models, labels and scores have changed since, and that loss has not been tested at the mix's own cells. The researchers' report ranks mask-weighted pooling as its row 5 with a zero-render screen ([report](research/proven-methods-preset-recovery-2026-11.md)); the deep review keeps it as the extraction row's screen. The user said go on 2026-11-05 after the plan below was explained in plain words. It differs from (f): (f) laid the stem beside the mix and every cell still counted; here the stem only picks cells, and every value read comes from the mix. It differs from averaging windows (no lever in the deep review), which weighs every moment alike.

**Seen before this declaration: map shares only, no settings label and no probe.** On 46 FS5 examples and 84 F5 training examples, half mels, the cells the maps below mark:

| | Median share of cells | 10th to 90th percentile |
|---|---|---|
| True map, training sample (FS5 sample) | 8.4% (5.2%) | 0.9% to 34.5% |
| Stem map at 3 dB, training sample (FS5 sample) | 56.5% (61.0%) | 22.8% to 97.8% |

Against the true map, the stem map's precision is about 20% on unmastered mixes and 6 to 7% on mastered ones (the review, 300 halves a set, before the gain fix below), its recall 94% on the FS5 sample; stem minus mix ranks true cells at a median AUC of 0.70 within an example, on the training sample. So the 3 dB rule, the researchers' untested proposal, marks far more than the guitar, and on about a tenth of halves almost every cell, where (g) is (b). That is why the true map reads first, and why a top-tenth stem map stands beside the rule. Marked cells sit a median of about 29 dB under the half's peak. Some are quiet: pooled, 16.9% of the true map's cells and 10.8% of the stem map's are over 50 dB under it, against a median of under 2% a half. No level gate is added, and this stands as a limit.

- **Maps,** per half on the stored half mels, half A's first second dropped as in training:
  - **(o) true map:** cells where `tgt-t3` at its gain in the mix is within 3 dB of `mix-t3`. The gain is the stored `gain_db`; on a mastered mix, the half's mix loudness less the target and backing's power sum at their gains (`true_gain_db`), since mastering sat those mixes about 3 dB above the target and halved the map. The product cannot have this map. It is one strong case for the idea at one margin, not its limit.
  - **(g) stem map:** cells where `xlance_g-t3` is within 3 dB of `mix-t3`.
  - **(t) top tenth:** the 10% of a half's cells with the highest stem minus mix. Stem minus mix ties on the half-dB grid on many cells, so ties go to a seeded draw per example and half. Cell order would make it a low-band map and the mix's level would make it the loudest cells, which (pt) could not copy. On a half where most cells tie, (t) is mostly a random tenth of the tied cells, so it is close to its placebo there.
  - **(po), (pg), (pt) placebos:** the same rule's map from a seeded partner example in another section of the same set (seed 20261105), read over this example's mix. Same shape of selection, wrong cells.
  - **(xo) map without its mix:** this example's true map read over the partner's mix. What (xo) reads comes from which cells are kept, since the values are another example's. It is there because a true map carries the target's shape: a head both (o) and (xo) reliably win against a comparator is left out when (o) is judged against that comparator, and (o)'s losses stay in.
- **The summary:** `masked_summary`, the same 740 entries as (b) from the mix's dB in marked cells only. Frame changes and lags run over pairs of marked frames. A band with under 20 cells, or a group or the broadband envelope with under 20 frames, has no value there, nor has a lag with under 20 pairs. The two halves average, one half standing in where the other has no value. Gaps take the probe-training rows' column mean, standardised as usual. No count or share of marked cells is a feature, but the map does reach them: an envelope averages the bands kept in each frame, so which cells are kept moves it (broadband sd about 1.9 dB plain, 4.4 on (o), 5.5 on (po)), and that is why (po) and (xo) are read.
- **Read:** the same probe, split (F5's training examples, FS5) and readable rule as (a) to (f), through `fit_input`, one run. Steps per head by `step_row`, both ways: each map against (b), each placebo against (b), each map against its placebo, (xo) against (b) and (po), and (o) against (xo) beside. (o) against (b) and against (po) are also counted without the heads both (o) and (xo) win against the same comparator, written (o)|x. Reliable means a 90% section-clustered interval, jackknife for AUC, excluding 0.
- **Controls, each stopping the run:** the every-cell summary equals the stored (b) for every example within 1e-5; (b) read through this code reproduces `probe.json`'s (b) points within 1e-9.
- **Beside:** readable counts against (b)'s 30 and the researchers' 37, about one count's noise; family counts, with today's space (25 heads) printed apart; share, precision and recall of each map on FS5.
- **Reading, no effect-size bar.** "Ahead" means more heads reliably better than worse by the researchers' one-sided sign test at 5%, and more than the 6 reliably better that chance gives. Heads are correlated, so the test is nominal, and the placebos' own rows show the noise. The first match below is the reading (`reading`, stored as `branch`):
  1. A stem map ahead of (b) and of its placebo: it earns one step, that input for a model on real labels, in its own declaration, whatever (o) shows. (g) is taken before (t).
  2. (o)|x ahead of (b) and of (po): with a true map, these cells beat the plain mix and wrong cells, leaving aside wins the map's shape takes by itself. The question moves to a better map from the stems we have, with no new separator, in its own declaration.
  3. (o)|x ahead of (po), not of (b): the right cells beat wrong cells, while pooling so few loses as much or more. Not stopped: a denser read, such as those cells beside the plain mix, is the next question, in its own declaration.
  4. (o) or a stem map ahead of (b), with none of the above met: the change is not shown to come from these cells' values, and is not credited to the map. Mask pooling stops.
  5. Otherwise: no gain shown at this margin, with this reader, on these cells. Mask pooling stops. That is a median of about 8% of cells and many filled entries, so it does not say the guitar's cells hold nothing.
- **Limits.** The probe's Limits below apply: a linear probe, FS5's self-built mixes with plugin renders, no read of sound or of a real song. (o) is generous in one way and harsh in another: which cells it keeps depends on the target, so it can carry the target's shape as well as the mix's values, which (xo) separates only head by head, leaving out what the shape wins alone and not what it adds on a head (b) also reads; and it drops every cell where the guitar sits under the backing. On mastered mixes (p 0.5) its gain is estimated from loudness, whole-section for the backing. The 3 dB line and the top tenth are one setting each; no setting is searched. Quiet cells stay in.
- **Cost.** Zero renders, zero separations, no training beyond the linear probes. CPU, at most 4 processes; features at about 0.06 s an example (the review's measure), and the main read took 8 minutes of probes on 6 inputs, here 8.
- **Code.** `$MAIN -m learn.tone_info_probe mask-features`, then `mask` (`tone-probe/mask.json`, read once). Ledger: `pipeline-fix`, `phase_mask_read`.
- **Outcome (2026-11-05, run once, F58 in the [plan](pipeline-fix-plan.md)).** Readable of 116: (b) 30, (o) 35, (g) 19, (t) 19, placebos 7, 20 and 13, (xo) 9. (o) against (b) 21 better, 8 worse; (g) 2 / 19; (t) 0 / 29. Branch: better map next. The audit, post hoc, at this margin and with this reader: clean target values on (o)'s own cells read 38, against 71 on random cells at that density and 42 to 43 on cells with the same kind of band layout, so how few bands the cells cover caps the idea at about +5 heads, with mean knob error unchanged; (g) is no better than random cells and (t) worse; the lead thins by band and on some section drops. No other margin was tried. No better map is declared, and mask pooling on summaries is parked. The shares quoted above were pre-run: on FS5 the true map marks 9.0% of cells and the stem map 62.2%, with precision 15.7% and recall 92.5%.
- *Review (2026-11-05, independent, before any run):* six required changes, all made: ties in (t), which had made it a low-band map; the mastering gain for (o), which had halved its map; the reading's order and its reads of (po) and (xo); no value for a lag with too few pairs; wording against the data; the roadmap and index. The sign test's chance count in "ahead", the extra tests and the status line came from its optional list. Its re-check of those fixes required two more: ties to the louder mix cell let (t) read its own loudest cells, which (pt) could not copy, so ties are a seeded draw per example and half; and (o) beating (xo) is near automatic, so (o) is judged without the wins it shares with (xo). A last pass kept (o)'s losses in that count and softened two lines.

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
`$MAIN -m learn.tone_info_probe features` (the summaries, cached in `tone-probe/`), then `$MAIN -m learn.tone_info_probe read` (the table, `tone-probe/probe.json`). The addition: `$MAIN -m learn.tone_info_probe audible` (`tone-probe/audible.json`). The review's post-hoc inputs: `$MAIN -m learn.tone_info_probe posthoc` (`tone-probe/posthoc.json`).
