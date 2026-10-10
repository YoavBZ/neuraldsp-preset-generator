# From a song, not an amp track: plan (development)

Declared 2026-10-10, before any render below. Roadmap step 0, next step 7.

## Question

The [confirmation](set4-confirmation-results.md) rebuilt the DI from the isolated amp
track. The product gets a song, so it rebuilds from a separated guitar stem. Two
questions:
- Does the chooser still land closer than `generate`'s starting preset when it rebuilds
  from the stem?
- How much of the amp-track gain does it keep?

A raw mix is not an input to the network. The product's path is song → separation →
stem → rebuilt DI, so the stem is what's tested.

## Material (development only)

- **Set 3:** the 12 development parts with a usable htdemucs_6s stem
  (`~/ndsp-presets/learn/set3/stems`).
  - Network: the set-3 network (`models-set3/fold2.pt`), which never heard set 3.
  - Gain classes: as declared.
- **Sets 1–2:** the 20 development parts with a usable stem
  (`~/ndsp-presets/learn/poc/stems`, crops in `validation-crops`), from 10 bands.
  - Lags: `docs/validation-lags.json`.
  - Network: each part is rebuilt by the K3 fold network that never heard its band
    (`models-final/fold{k}.pt`). The set-3 network trained on most of these bands, so it
    is not used for them.
  - Gain classes: measured by set 3's session-level rule (`gainmeasure.py`,
    `classify.py`) on the whole session, before any rendering.
- **No held-out part is used.**

## Kinds (fixed-level protocol, as in the confirmation)

| kind | DI |
|---|---|
| `measfix` | the true DI re-equalised to the pinned K3 fold-2 average, at −22.9 LUFS: the measure and the oracle |
| `amp` | rebuilt from the amp track, low-passed at 3 kHz, at −22.9 LUFS: the confirmed chooser |
| `stem` | rebuilt from the separated stem, low-passed at 3 kHz, at −22.9 LUFS |

`measfix` and `amp` already exist for set 3 (`gap-split/measfix`, `v2-eval/lp3k`). Every
other kind is rendered through the three amp menus.

## Scoring

The confirmation's code (`learn/confirm_run.py` functions):
- **Picks:** both halves, with the reference-proxy fallback.
- **Judge:** the validated `flat` judge.
- **Baselines:** the clean template on clean parts, the shipped driven presets on crunch.
- **Statistics:** band-clustered 90% intervals, with the band as the unit. High-gain
  parts are report only.

## Decision rule (declared; a development guide, not a confirmation)

On clean and crunch parts:
- **Go to the product step** (the audition-page option, marked experimental) if both
  hold:
  - the stem chooser's 90% interval against the baseline lies below 0;
  - its mean keeps at least half of the amp-track chooser's mean gain, on the same
    parts.
- **Otherwise the product step waits.** The stem path is improved first: a better
  separator, or stem-aware training (renders mixed into backings, then separated).

**Also reported:** stem against amp, paired; each source alone; per stratum; the oracle.

An independent reviewer re-derives the numbers.

## Preparation (before any rendering)

- **Sets 1–2 gain classes** (`learn/songs_check.py prep`): 18 clean, 2 crunch.
- **Set 3 stem parts:** 2 clean, 3 crunch, 7 high-gain.
- **In all:** 32 parts from 17 bands, with 25 clean or crunch parts in the decision.
- **Lags:** `validation-lags.json` gives the amp track's delay behind its DI, so the
  judge's lag is that minus the 52-sample plugin latency. This reproduces the clean-PR12
  study's judge lags (966 → 914).
