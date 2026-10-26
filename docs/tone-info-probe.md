# Where the tone information is lost: a probe on F5's examples (declared 2026-10-27, zero renders)

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
`$MAIN -m learn.tone_info_probe features` (the summaries, cached in `tone-probe/`), then `$MAIN -m learn.tone_info_probe read` (the table, `tone-probe/probe.json`).
