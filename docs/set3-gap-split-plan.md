# Where the rebuilt DI loses the preset choice: plan (set 3, development)

Roadmap step 0, next step 2. Declared 2026-10-09, before any of the renders below exist.

## Question

With the take's true DI, the judge picks menu presets well on all three amps. Through
the rebuilt DI it loses about −0.16 (SW50R), −0.24 (PR12) and −0.22 (AC20) in mean
log ratio ([review](codex-continuation-review.md)). Which part of the rebuilt DI loses
it?

- **Level.** The rebuilt DI is always fed to the amp at −22.9 LUFS. The 33 true DIs
  sit between −46.5 and −16.8 LUFS (median −29.5), so most are fed 5–20 dB too hot or
  too cold. A driven amp responds strongly to input level. On clean PR12 renders,
  level cost little (0.045, [plan](di-recovery-plan.md), "The level diagnostic").
  Driven material has not been checked.
- **Activity mask.** The judge takes the playing frames from the rebuilt DI rather than
  the true one.
- **Long-term balance.** The rebuilt DI's average spectrum differs from the true DI's.
- **The rest.** Dynamics, transients and pick detail: everything a long-term level
  and spectrum leave out.

## Material and method

- **Parts and menus:** the 33 development parts and their 11 bands; the three amp menus
  (factory presets and template+R), as in `learn/phase2_set3.py`. Amp tracks only.
  No held-out part is opened (set 3's held-out split is spent and stays untouched).
- **Network:** the frozen set-3 network. Its rebuilt DIs are the stored `net/*/di.npy`,
  reused unchanged.
- **New DIs**, each rendered through every menu over the whole crop:

  | kind | DI | changes from `net` |
  |---|---|---|
  | `netlvl` | rebuilt DI at the true DI's loudness | level |
  | `netlvleq` | rebuilt DI re-equalised to the true DI's smoothed spectrum, at the true DI's loudness | level and balance |
  | `measfix` | the measure's DI at −22.9 LUFS | the true waveform at the rebuilt DI's level |

  "The true DI" here is the measure's DI (the take's DI re-equalised to K3 fold 2's
  average balance, at its own level), since that is what the measure renders.
  Loudness is matched with the same meter (`pyloudnorm`, integrated).
- **No-render variant `netmask`:** the stored `net` renders, judged with the measure's
  DI as the activity mask, shifted onto the recording's timeline (the part's judge lag).
- **Choosing:** each variant picks the closest menu preset on half A (1.0–5.5 s)
  against the amp track. The rebuilt-DI variants use lag −52; `measfix` uses the part's
  judge lag, like the oracle. Both band sets.
- **Scoring:** unchanged, the average-guitar measure on half B (5.5–10 s).

## What is reported

For each amp and band set, per part, the log of each pick's half-B distance relative
to `net`'s pick. Three views are reported side by side:
- the mean;
- wins, ties and losses;
- the band median of band medians, with its two-sided sign-flip p.

Also reported: the steps `net → netlvl → netlvleq → oracle`, and `measfix` against the
oracle, which is the level's cost with the ideal waveform.

## Decision rule (declared)

**The gap.** G is the mean over the 33 parts × 3 amps of `oracle − net`, on recording
bands.

**A component "explains the gap"** if its step, pooled the same way:
- recovers at least half of G;
- is negative on the mean;
- has more part-amp wins than losses.

The steps are: level (`net → netlvl`), balance (`netlvl → netlvleq`), the rest
(`netlvleq → oracle`), and mask (`net → netmask`).

**What follows from each outcome:**
- **Level explains it.** A song cannot tell the take's DI level: it is the studio
  interface's gain. So the next step is not more training.
  1. Report the alternative reading: the same measure with the DI at a standard level
     (`measfix` on half B), since an "average guitar" arguably has an average level.
  2. Ask the user whether the measure should fix the DI level. This is the user's
     decision on the measure; until then the declared measure stands.
- **Balance explains it.** Next step 4 targets the rebuilt DI's average spectrum: a
  spectral-envelope loss term, or a post-rebuild re-equalisation.
- **The rest explains it.** Next step 4 goes ahead as planned: longer multi-amp
  training, stem-aware training, room and mic augmentation.
- **Mask explains it.** Adopt the true-DI-free mask fix first (the reference-proxy
  fallback is already planned).
- **None does.** Report the split as it is. Step 4 goes ahead as planned, with the
  largest component as its focus.

An independent reviewer re-derives the numbers from the stored distances before the
result drives anything. This is development data already used for earlier choices, so
the result guides the next step. It is not a confirmation.
