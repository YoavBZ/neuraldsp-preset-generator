# Does the judge still choose well through a wrong DI? The plan

Written 2026-10-06, before any render for it. This is roadmap step 4 (round 4,
experiment 5). It decides whether to build DI recovery: rebuilding an estimated DI from
the song's guitar, so that song-only matching can choose by the judge.

## Why now

Two results from the learned-model work, recorded in `preset-model-poc-results.md` and
the follow-up section of that results file:
- **The learned model.** Reading only the recording, it got 3.6% closer than template+R.
- **The tone-curve oracle.** Even knowing each part's true long-term transfer curve
  (measured with its DI on half A), settings chosen to reproduce that curve were only
  about 5% closer on half B. Choosing among the 21 clean factory presets by the judge on
  half A was about 20% closer (K1's oracle).

So choosing by the judge carries most of the value, and the judge needs the take's DI.
A rebuilt DI would be wrong in known ways. Above all it can't know the guitar's own
tonal balance, which is the confound measured on 2026-10-06: DI spectra differ by
5.6 dB per band across players.

## What is run

- **Parts:** K1's 25 parts (clean PR12 panel, recorded lags, half A 1.0–5.5 s, half B
  5.5–10 s).
- **Candidates:** the 21 clean factory presets plus template+R.
- **The degraded DIs.** Each candidate is rendered through each part's DI after one of
  three degradations, each fixed per part by a seed:
  1. **swap:** the DI is equalised so that its long-term spectrum takes the average of
     another band's DIs, a different player. That band is drawn from K3's other folds.
     This is the tonal confound at its real size.
  2. **mild:** in order:
     - a ±3 dB tilt across 100 Hz–10 kHz (sign by seed);
     - a 10-ms smear: convolution with a decaying exponential of 10-ms time constant,
       mixed 50/50 with the dry signal;
     - soft clipping, tanh at 0.9 of peak;
     - another band's DI mixed in at −20 dB.
  3. **swap+mild:** both.
- **Choosing and scoring.**
  - On half A, the judge scores each candidate's degraded-DI render against the amp
    track. The degraded DI is passed as the judge's DI, as a recovered DI would be.
  - The candidate with the smallest distance is the pick.
  - The pick is scored on half B through the panel's *true-DI* render, against
    template+R, as K1 scores its oracle.
- **Both band sets.**

## Decision rule

- **DI recovery is worth building** if, for swap and for swap+mild, under both band
  sets:
  - the degraded-DI pick is within 0.150 in log distance of the true-DI pick (K1's
    oracle) on more than half the parts and in more than half the bands; and
  - its band median against template+R is at most log 0.9.
- **Otherwise DI recovery is dropped**, and the report says which degradation broke it.
- Reported too: each degradation's band median against template+R and the share of
  picks equal to K1's.

## Limits

- 25 development parts, clean PR12 only, and a menu of 21 presets.
- A real recovered DI may err in ways these degradations don't cover.
