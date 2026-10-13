# Part locator: where in the song does the described guitar part play? Plan (development)

Declared 2026-10-13, before any locator code. The product session asked for it and the ML
session agreed. Revised the same day after an independent review
(`tmp/part-locator-plan-review.md`, local), before any code or separation.

## Why

When the user gives a song but no time, `generate` has to guess where the target electric
guitar plays. It got this wrong on 2026-10-13's end-to-end run (the Eagles' Long Road Out of
Eden). The user had asked for "the clean electric guitar", and the agent chose 1:32–1:52.

A `htdemucs_6s` map of the song afterwards (10-s windows, numbers only) showed:
- **The window had guitar, but buried.** The guitar stem carried 5–11% of the energy, the
  vocals 30–40%, and it was dark.
- **Better windows existed.** Guitar-led, vocal-free, tonal windows sit at about 3:00, 4:40
  and 8:10. The bright and noisy ones (5:20–6:10, 7:30–7:50) look like the driven lead.

So the failure was choosing the wrong part, not a lack of guitar. Users describe the part they
want by **character** (clean or driven) and **role** (lead or solo, against rhythm or riff).
The locator's job is to find the window where that part plays and dominates.

It ships only with the user's OK for the PyTorch and separator download. It never routes the
gain class.

## The tool (offline)

**Input:** a song, and an optional description: character (clean or driven), role (lead or
rhythm), or both.

**Separation:** `htdemucs_6s` (MIT), the separator already in use.

**Windows:** 10 s long, every 1 s.

**Features per window,** all from the stems:
- `g`: the guitar stem's share of all stems' energy at 1–4 kHz, in dB.
- `v`: whether the vocal is active, meaning the vocal stem's share of energy at 300 Hz–4 kHz
  is above 15%.
- `d`: the change in `g` against the 10 s before.
- `t`: tonality, the spectral flatness of the guitar stem at 200 Hz–5 kHz. Low means tonal.
- `b`: brightness, the guitar stem's share of energy at 2–6 kHz against 80 Hz–6 kHz.

**The score:**
- **No description:** `g`.
- **Lead:** `g + w_v·(1 − v) + w_d·max(d, 0)`.
- **Rhythm:** `g + w_v·v`, which rewards guitar heard under the singing.
- **Clean:** add `−w_c·z(t, b)`. **Driven:** add `+w_c·z(t, b)`. `z` is the within-song
  z-score of the mean of the standardised `t` and `b`.

The weights `w_v`, `w_d` and `w_c` are chosen on the calibration split only, from the grid
{0, 1, 3, 6} dB.

**Top-k:** chosen greedily without overlap. Each next window starts at least 10 s from every
window already chosen. Ties go to the earlier window. A song with fewer than k distinct windows
returns fewer.

**Abstain:** if the top window's `g` is below a threshold, the confidence is "none". The tool
then asks the user for a time.
- **The threshold has a declared goal,** so it can't drift to "never abstain".
- **The rule:** it is the lowest `g` at which, on the calibration songs, at least 90% of
  windows contain some electric guitar (any-guitar truth).

## Ground truth (development multitracks only)

**Sessions:** the 45 development sessions on disk, all full length, from about 26 bands.
- 29 from sets 1–2;
- 16 from set 3's development bands;
- Guitar-TECHS is left out (short excerpts, no band).

The truth needs only the DI and amp tracks, not a passing pair, so parts that failed the
pairing test (New One, Procession, Heather Jane ElecGtr2) still count for "any guitar".

**The mix:** each set's own declared rule.
- **Set 1:** every track except the guitar DIs, both microphones included.
- **Set 2:** the session's `mix_tracks` summed at unity gain (validation-datasets.md, "The
  mix"; built by `research/build_validation_crops.py`). Alternates and DIs are left out, so each
  part is heard once, through its reference.
- **Set 3:** its catalog's `mix_tracks`, as listed in `datasets-set3/_tools/measured.json`
  (untracked).

**Short tracks** (some Cambridge tracks are shorter than their song) are padded with silence to
the song's length.

**Part activity:**
- frames of 100 ms (RMS);
- a part counts as active within 30 dB of its loudest frame.

This differs from crop rule 2's 40 dB on 2048-sample frames on purpose: a locator window needs
the part clearly playing, not just above the noise.

**"The window contains the part"** needs both:
- **activity:** the part's DI is active in at least 60% of the window's frames;
- **dominance:** at 1–4 kHz, the target guitar carries at least half the energy of all electric
  guitars in the window.
  - It is measured per guitar, not per track: each guitar's own microphones are summed.
  - A part and its double (DT), or parts with the same description in the song, count as one
    target.

**Electric guitars recorded without a DI** count from their amp tracks.
- A frame counts as active when the amp track is within 20 dB of its loudest frame. That is
  stricter than the DI's 30 dB, because `bleed_db` is missing for these tracks and for set 3.
- **Kimock's "Keys GTR" tracks** count as guitars in the dominance total, but are never
  targets. That is the conservative choice.

**Target labels:** every part is a target in turn, described by the labels below. A part
missing either label is not a target.
- **Character:**
  - **Set 3:** the catalogued gain class.
  - **Sets 1–2:** the set-3 classifier's rule (`classify.py`, thresholds unchanged), on the
    part's passing DI/amp pair.
  - Clean is "clean". Crunch and heavier are "driven".
  - High-gain parts, from either set 3's catalog or the classifier on sets 1–2, are reported
    separately (out of scope).
- **Role,** a declared rule on the part's own tracks:
  - **Lead:** active in no more than 50% of the song's windows, and mostly single notes. That
    means at least 60% of its active frames are voiced under pYIN on the DI.
  - **pYIN settings:**
    - librosa's `pyin` (ISC licence, added to the main venv);
    - fmin 70 Hz, fmax 1400 Hz;
    - frame 2048, hop 512 at 44.1 kHz;
    - the voicing decision is librosa's `voiced_flag`;
    - only the part's active frames count.
  - **Rhythm:** active in at least 50% of windows, with no more than 40% voiced frames.
  - **Otherwise:** no role label.
- **Ear check of the role rule:** before any locator result, the user labels 16 parts
  (lead / rhythm / unsure) on a listening page. The parts are stratified across sets and
  rule labels, and the page shows no rule label.
  - **If agreement on decided parts is below 80%,** the role description is report-only, and
    the primary measure uses character alone.
- **If a song has two parts with the same description,** a window containing either one counts.

**MUSDB18 overlap is marked,** and results are reported with and without these sessions:
- **in the train subset:** Atlantis Bound, Wall Of Death – Femme, Cnoc An Tursa – Bannockburn;
- **in the test subset:** Zeno – Signs, Hollow Ground – Ill Fate;
- **the same artist:** The Long Wait.

## Measures

**Primary:** described-part Hit@3. Take a target's description (character and role) and the
song. Does at least one of the locator's top 3 windows contain the target? An abstain counts as
a miss.

**Secondary:**
- described-part Hit@1;
- lead-only Hit@3 ("the solo");
- the abstain rate, and Hit when the locator answers;
- the gain from the description: the locator with the description against the same locator
  without it.

**Report-only:** any-guitar AUROC. The score of each window is set against the any-guitar
truth, within each song, then averaged. A random window already contains some guitar 86% of the
time, so Hit on any-guitar can't separate methods.

**Baselines,** each given the same song:
- **`generate`'s current excerpt choice:** `analysis/io.py`'s `excerpt_selection`, 10 s of the
  mix, the activity rank with its middle-of-tie rule;
- **the loudest 10 s** of the mix;
- **the song's middle;**
- **three evenly spaced windows** (for Hit@3);
- **random:** the exact expected Hit from the song's share of windows containing the target.
  For Hit@3, it is the exact probability under a uniform draw over all valid non-overlapping
  triples, by enumeration.

**The primary set:** in-scope targets (sets 1–2, and set-3 clean and crunch) whose random Hit@3
is above 0 and at most 0.8. Above 0.8 nothing can show a lift. The full set is reported beside
it.

**The decision:**
- **Useful:** locator Hit@3 minus the best baseline's, paired per target and band-weighted,
  has a 90% band-bootstrap lower bound above 0, and the locator's Hit@3 is at least 0.6.
  - The best baseline is re-picked inside each bootstrap resample.
- **Futile:** the upper bound is below +0.05.
- **Underpowered:** fewer than 15 primary targets or 10 bands. This is reported as such,
  never as futile.
- **Inconclusive:** anything else.

**The truth file comes first.** It lists every target's base rate, the targets with a base rate
of 0 (dropped), and the primary set's count of targets and bands. The power is restated from
those counts.

A dry run of the truth rule during the review gave about 18 reachable in-scope targets in 16
bands, and about 13 targets in 11 bands for the primary set. So "underpowered" is a likely
outcome, and is stated now.

**The clean/driven reading stays out of the tool's output** until it passes its own bar. That
bar is a window-level AUROC of at least 0.75 against the targets' character, with a 90%
lower bound above 0.6. The routing check found that mix measures and agents confuse loudness
with drive.

## Split

Bands go into **3 folds.** Each fold is evaluated with the weights and abstain threshold
calibrated on the other two, so every target is evaluated once.
- **Stratified:** single-guitar Telefunken bands, multi-guitar Cambridge bands, the other sets
  1–2 bands and set-3 bands. Within each stratum, bands are sorted by name and dealt to folds
  1, 2, 3 in turn.
- **Eat The Feeder** (Today's The Day in set 2, Wickerman in set 3) is kept whole, in one fold.
- Calibration only sets the weights and the abstain threshold.

## Order

1. **Truth file:** activity, dominance, labels, base rates and the split, computed from the
   tracks. No separation yet. It is committed before step 3.
2. **Ear check** of the role rule: the user's page.
3. **Separation:** all 45 mixes (about 3 h of audio). This runs on the CPU at low priority
   while E1 trains, or on MPS in about 25 min when MPS is free.
4. **Stem check, on calibration only:** within each song, the correlation of the guitar stem's
   1–4 kHz envelope with any-guitar truth. If the median is below 0.3, stop and report.
   Windows where the hit is an acoustic guitar or an organ are counted, because the guitar stem
   takes those in too.
5. **Calibrate,** then **evaluate** once, then the review and the report.

## Stated limits

- **The mixes are unity-gain track sums, not mastered songs.** They flatter the guitar against
  commercial releases. The Eden example is the real-world reminder.
- **Set 3 is high-gain-heavy.** Its high-gain parts are reported separately.
- **Character labels for sets 1–2** rest on the classifier's rule, which is validated on set
  3.
- **Held-out data is untouched:** sets 1–2 held out, 4, 5 and 6. MedleyDB's annotations would
  be ideal truth, but set 6 is held out in full.

## Interface (proposed to the product session after the result)

`scripts/locate_part.py SONG [--character clean|driven] [--role lead|rhythm] [--k 3] --json`

It returns:
- **`windows`:** up to k non-overlapping windows, each with `start_s`, `end_s`, `score`,
  `guitar_share_db`, `vocal_active` and a one-line `reason`. An optional `clip` path is given
  for listening.
- **`confidence`:** high, low or none. "None" means ask the user for a time.
- **`separator`** and **`stem_cache`,** so later steps reuse the stems.
- **`caveats`:** for example, "the guitar stem may include organ or acoustic".

`generate` would offer the top 3 as clips for the user to choose from, and pass the choice as
`--excerpt-start`. If the models aren't installed, it asks for a time, as it does today.

## Reviews

- **The second review** (`tmp/part-locator-plan-review2.md`, local) approved with nine changes,
  all made above.
- **The truth-file review** (step 1) confirms them on the real counts, before separation.
- **The result review** comes before anything is reported.
