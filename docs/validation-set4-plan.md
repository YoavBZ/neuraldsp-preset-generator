# Set 4: a fresh held-out confirmation set (plan)

Declared 2026-10-10. It is committed before the set-4 catalogue, crops or declaration
JSON exist. Until then the only things read from set 4 are file names, sizes, WAV header
fields (sample rate, channels, length, subtype) and the readme and licence texts
([tmp/set4-download.md](../tmp/set4-download.md), local).

## Purpose

Set 4 is **one-time confirmation material**. Set 3's held-out split is spent
([validation-set3.md](validation-set3.md)), so a new confirmation needs bands no method
has seen.

- **Every set-4 band is held out.** There is no development side, no draw and no folds.
- **Nothing may train, tune or choose on it.** This covers:
  - training: its DIs, renders made from them, and their average spectra;
  - choosing or tuning any method, constant, threshold or judge;
  - lag re-measurement and crop rebuilding after the declaration;
  - listening.
- **It covers every file.** Every file of every set-4 session is held out, kept part or
  not, including amp-only tracks, the archives and anything under
  `~/ndsp-presets/references/validation-crops-set4/`.
- **It is used once.** A confirmation must be declared in a committed file (its command,
  what it measures, its gates and what each result means) before it reads set-4 audio.
  Its use is then recorded in `held_out_uses` of `docs/validation-set4.json`, or in a
  ledger beside it. After that use the set is spent, as set 3's is.
- **The build is not a use.** Pairing, gain measures and crops are built before any
  method sees set 4, by tools that score nothing (below). Building them is not a use.

## The five sessions

All five are from the Cambridge Music Technology "Mixing Secrets" library, from the
publisher's direct host. They are 24-bit/44.1 kHz WAV, downloaded 2026-10-10 to
`~/ndsp-presets/references/datasets-set4/<Band - Song>/`. The archive hashes were
re-checked when this file was written. No band is in sets 1–3.

| band – song | archive (`mtkdata.cambridgemusictechnology.co.uk/…`) | bytes | sha256 |
|---|---|---|---|
| Tholas P. – Such Fine People | `MTK022/TholasP_SuchFinePeople_Full.zip` | 683,239,501 | `17965d3dabd94722b0a59193ad9d1e0ca4ab18d9b5a6740a4aa7fe1e28768ba5` |
| Last Legacy – Who's Who In Hell | `MTK013/Lastlegacy_WhosWhoInHell_Full.zip` | 362,917,685 | `241406f72a38a5670a142b4864d8d67d61b79f5073e0ed765c57faef17b193b6` |
| Decypher – Unseen | `MTK013/Decypher_Unseen_Full.zip` | 906,240,793 | `3226a6ad8a429e97a03f016d9129e2309727d4f520aed23330a99b49cf823b10` |
| The Black Crown – Flames | `MTK013/TheBlackCrown_Flames_Full.zip` | 890,232,811 | `a4259890f0b91904c1de4582b9de52b56bd68302797bb05c70ee5c401613de8c` |
| Lead Inc – The Inner Circle | `MTK011/LeadInc_InnerCircle_Full.zip` | 1,443,904,938 | `2a7eebcdfb0ffefd8fa61682c723b16890d2b470c04d85315c92b2155db90b29` |

### Licences (key lines verbatim)

- **All five readmes (Cambridge):** "provided for educational purposes only, and the
  material contained in them should not be used for any commercial purpose without the
  express permission of the copyright holders." Decypher, Last Legacy, The Black Crown
  and Lead Inc say "it" for "them". This is the same basis as sets 1–3. It is not an open
  licence: non-commercial research fits "educational" only by interpretation.
- **Lead Inc** (`Tech Details and Lyrics.rtf`): "licensed and published with Creative
  Commons (CC BY-NC-SA 3.0) which allows you to remix and publish your own mixes
  non-commercially and with this same license only." This is more specific than its
  readme.
- **Tholas P.** (readme): "Released digitally on Oct 30th, 2020 via CDBaby. All rights
  reserved." Its terms of use: "You can upload your mix of the track outside of
  cambridge-mt.com if you include a streaming or buy link for the original release."

None of the audio enters this repository. Crops stay private, as for set 3.

### Parts declared by name

A part is a guitar DI with an amp or microphone track of the same name. These are read
from file names only, before any measurement:

| band | parts (DI → amp tracks) | count |
|---|---|---|
| Tholas P. | ElecGtr01, 01DT, 03, 03DT, 04, 05, 06, 07, 08, 09: `NN_ElecGtrXXDI` → `NN_ElecGtrXX` | 10 |
| Last Legacy | ElecGtr01, 02: `ElecGtr0XDI` → `ElecGtr0X` | 2 |
| Decypher | ElecGtr01, 01DT, 02, 02DT: DI → Mic1, Mic2 | 4 |
| The Black Crown | ElecGtr1, 1DT: `…DI` → `…Amp` | 2 |
| Lead Inc | ElecGtr1, 2, 3: DI → Mic1–4 | 3 |

That is 21 parts, or 16 tones (a part and its `DT` double are one tone, as in sets 1–3).

These guitar tracks have no DI and are not parts: Tholas P. ElecGtr02 and 02DT, Last
Legacy ElecGtr03–07, and The Black Crown ElecGtr2 and 3. They stay in the session mix.

## Rules: set 3's, unchanged

Set 4 uses set 3's rules ([validation-set3.md](validation-set3.md) and the set-3
catalogue's `rules`) with the same thresholds. The set-3 tools are copied to
`datasets-set4/_tools/` with paths changed. The set-3 copies are not edited.

- **Same take: the waveform test.** GCC-PHAT, 80 Hz–4 kHz, of the amp track against the
  DI, in 20-s windows every 10 s where both are within 30 dB of their loudest.
  - A part passes when at least 80% of windows are within ±1 ms of the median lag and
    the median peak-to-sidelobe ratio is at least 2.0.
  - The envelope test is also run. A part passing both is recorded as
    `"envelope+waveform"`.
  - A part whose waveform ratio is under 1.4 over 3 or more windows is out, even if the
    envelope test passes.
- **Choosing the reference.** Amp tracks are tried in the repository's `AMP_PREFERENCE`
  order (Mic1 first). The reference is the first passing the envelope tests and not at
  waveform null, else the first passing the waveform test. The other amp tracks of the
  part are its alternates, as in set 3.
- **Exclusions:**
  - fewer than 3 passing waveform windows;
  - a clipped DI (10 or more flat-topped full-scale runs over the session);
  - two lag clusters (under 80% of windows within 0.25 ms of the median);
  - no crop;
  - keyboard-named parts, and amp tracks shared between parts.
- **Marks** (kept, flagged): `effects_or_bleed`, `late_amp_track` (more than 5 ms),
  `di_touches_full_scale` and `amp_earlier_than_di`.
- **Gain classes:** `classify.py` with set 3's thresholds, not recalibrated.
  - `gain_class` is the session-level class (clean, crunch or high-gain).
  - `gain_class_crop` is the same measure on the 10-s crop, also recorded.
  - Crunch against high-gain stays an ordinal compression reading, not a validated class.
- **Crops:** `research/build_validation_crops.build`, rule `di-activity` (crop rule 2):
  10 s on a 0.5-s grid, mono, first-sample alignment, no gain or shift.
  - The mix is the session's mix tracks at unity: every WAV except guitar DIs, the
    part's alternates, rendered mixes and click tracks.
  - Each crop holds `reference.wav`, `di.wav`, `mix.wav`, `backing.wav`, the
    instrumental versions when vocals are named, and `record.json`, in
    `~/ndsp-presets/references/validation-crops-set4/<slug>/`.
- **Lags and polarity:** the waveform median lag, in samples at 48 kHz, never applied.
  - `judge_lag_samples` is that lag less 52.
  - The onset cross-check is recorded as in set 3.
  - Polarity is as the waveform test records it.
  - Lags are never re-measured after the declaration.

### Deviations from set 3, and why

1. **Resampling to 48 kHz is the same as set 3's.** Set 3's Cambridge sessions were also
   44.1 kHz. As there, the catalogue measures at the native rate and the crops are
   resampled to 48 kHz by `analysis.io`. This is listed only because the task asked; it
   is not a deviation.
2. **The parts are declared by hand, not by set 3's name-matching script (`propose.py`).**
   Five sessions are few enough to list the pairs from the names (table above). Set 3
   also corrected its proposals by hand (Cnoc An Tursa, Renesans).
3. **Decypher's `23_ElecGtr02DIMic1` and `24_ElecGtr02DIMic2` are microphone tracks,**
   taken by their `Mic` suffix and their place beside the DTs' `Mic1`/`Mic2`. The
   repository's guitar-DI name pattern would call them DIs and leave them out of the mix.
   Set 4 therefore takes its DIs from the declared parts, not from that pattern, when it
   builds the mix. The pattern still removes any other DI-named guitar track.
4. **No split, no folds, no draw.** Every band is held out (Purpose). So set 3's strata,
   seed and fold rules do not apply. The gain-class counts are reported per band, as
   description only.

Any other change found necessary while building is recorded as a dated amendment here,
with its reason, before the declaration is committed. No method result exists to
motivate one.

## Order of work

1. This plan is committed.
2. The catalogue is built: name-declared parts, the pairing tests, gain measures, clipping
   and lags (`~/ndsp-presets/references/datasets-set4/catalog.json`).
3. The crops are cut.
4. The declaration is written from the catalogue and the crop records alone:
   `docs/validation-set4.json`, rebuilt by `research/validation_set4.py`, and
   `docs/validation-set4.md` (counts per band and gain class, exclusions with reasons).
5. The leakage guards learn set 4 (`learn/set4.py`, and `learn/set3.training_dis` refuses
   set-4 files), with tests.

No plugin is run, no render made, no preset scored, no network inference run and no
audio listened to at any step. The building agent sees only the catalogue's fields
(pairing statistics, gain measures, clipping, lags) and the crop records, as set 3's did.

## What so few bands can confirm

There are 5 bands now. Perhaps 9–12 later, if the four Internet Archive copies of
Cambridge sessions (Umbriferous, The Bright Star Alliance, Sonnet & Alcohol, The Laminar
Flow) and some doubtful-gain bands are added
([tmp/fresh-bands-research.md](../tmp/fresh-bands-research.md)). Additions must come
before any confirmation reads set 4. Each needs a dated amendment and the same rules.

The power table in [fixed-level-rescore-results.md](fixed-level-rescore-results.md)
("What a confirmation needs") gives the chance that the band-clustered 90% bound excludes
zero, by resampling set 3's development bands:

| true effect (mean log ratio) | 6 bands | 11 bands | 20 bands | 30 bands | 45 bands |
|---|---|---|---|---|---|
| −0.143 (as observed) | 34% | 69% | 96% | | |
| −0.072 (realistic) | | 15% | 32% | 50% | 70% |
| −0.26 (the true-DI oracle) | 96% | | | | |

- **With 5 bands, only oracle-sized effects can be confirmed:** about −0.26, roughly 23%
  closer. Power at the observed −0.143 is under the 6-band 34%.
- **An exact band sign-flip test needs every band to agree.** With 5 bands there are 32
  sign patterns. The smallest two-sided p is 2/32 = 0.0625, so p < 0.05 cannot be
  reached. A p < 0.1 gate, set 3's, passes only when all 5 bands go the same way: one
  band against it gives p ≥ 4/32 = 0.125.
- **With 9–12 bands,** an effect near the observed −0.143 has roughly 60–70% power. The
  realistic −0.072 stays at about 15%.
- **Approximate only.** The table was resampled from set 3's development bands under the
  fixed-level measure, and set 4 is heavier. A confirmation plan should redo the power
  calculation for its own measure and band count before it is declared.
- **Bands are uneven.** Tholas P. alone has 10 of the 21 parts. Following set 3's
  amendment (4), each band's parts should weigh 1/n, so every band counts once. A
  confirmation plan adopts or overrides this explicitly.

## Leakage guards

- **`learn/set4.py`** answers `is_held_out` for any set-4 band, session, crop slug or path.
  Everything in set 4 is held out. It raises on names it does not know.
- **`learn.set3.is_held_out`** recognises set-4 paths and names as held out.
- **`learn.set3.training_dis`** raises if a set-4 file reaches the training list.
- **`learn.set3.fold_for_band`** raises on a set-4 band.
- **Tests** cover these and do not need the audio.

## Amendment 1 (2026-10-10): four Internet Archive sessions

Committed before any of these four archives is downloaded, opened or measured. What was
read about them before this amendment: their track names and file sizes (from the zips'
central directories by HTTP range requests, in
[tmp/fresh-bands-research.md](../tmp/fresh-bands-research.md)) and the HTTP headers below.

### What is added, and why

Four more Cambridge-MT "Mixing Secrets" sessions, the "Wayback-only heavy" group of the
fresh-bands research (its table A, rows 6–9). They are heavy by genre, have DI and amp
tracks of the same part by name, and their bands are in no earlier set. The plan above
foresaw them ("What so few bands can confirm"): with 5 bands only oracle-sized effects can
be confirmed, and 9 bands give a band sign-flip test room to reach p < 0.1 without every
band agreeing.

**Nothing of set 4 has been used by any method.** No confirmation has been declared or
run, `held_out_uses` in `docs/validation-set4.json` is empty, and no plugin, render,
preset score, network inference or listening has touched any set-4 file. Adding bands now
is allowed by the plan ("Additions must come before any confirmation reads set 4").

### Route and provenance: the Internet Archive

The publisher's own host for these files, `multitracks.cambridge-mt.com`, now answers
with a Cloudflare challenge, and none of the four has a copy on the unchallenged direct
host (`mtkdata.cambridgemusictechnology.co.uk`). Each is therefore taken from the
Internet Archive's Wayback Machine capture of the publisher's file. The `id_` form of a
Wayback URL serves the archived bytes as captured, without the archive's page rewriting.
Nothing is bypassed: these are public captures, fetched one at a time with retries.

| band – song | Wayback URL (capture timestamp, UTC) | archived length (bytes) | origin `Last-Modified` |
|---|---|---|---|
| Umbriferous – Sandcastles (Illusion) | `https://web.archive.org/web/20220404030035id_/https://multitracks.cambridge-mt.com/Umbriferous_SandcastlesIllusion_Full.zip` (2022-04-04 03:00:35) | 1,070,800,716 | Tue, 25 Jan 2022 19:25:59 GMT |
| The Bright Star Alliance – Error 404 | `https://web.archive.org/web/20220403150701id_/https://multitracks.cambridge-mt.com/TheBrightStarAlliance_Error404_Full.zip` (2022-04-03 15:07:01) | 679,147,233 | Tue, 25 Jan 2022 19:22:54 GMT |
| Sonnet & Alcohol – Back To The Nineties | `https://web.archive.org/web/20220403133148id_/https://multitracks.cambridge-mt.com/SonnetAndAlcohol_BackToTheNineties_Full.zip` (2022-04-03 13:31:48) | 459,707,231 | Tue, 10 Aug 2021 15:44:01 GMT |
| The Laminar Flow – Headspace | `https://web.archive.org/web/20250610215848id_/https://multitracks.cambridge-mt.com/TheLaminarFlow_Headspace_Full.zip` (2025-06-10 21:58:48) | 1,277,721,130 | Thu, 21 Apr 2022 08:55:00 GMT |

The lengths, `Last-Modified` and `Memento-Datetime` are the archive's response headers
(`x-archive-orig-content-length`, `x-archive-orig-last-modified`) to a HEAD request on
2026-10-10. The publisher gives no checksum. A download counts as complete when its length
equals the archived length, `unzip -t` passes (every member's CRC) and its track list
equals the one read by range requests. Its SHA-256, and the readme and licence lines
verbatim, are recorded once downloaded, as for the first five
([tmp/set4-download.md](../tmp/set4-download.md), local). They go to
`~/ndsp-presets/references/datasets-set4/<Band - Song>/` like the others.

These are the publisher's own files obtained through a third party. If a readme states a
licence different from the Cambridge "educational purposes only" text, that is recorded.

### Parts declared by name

Read from the zips' track lists only, before any measurement. As before, a `DT` double
and its original are one tone.

| band | parts (DI → amp tracks) | parts | tones |
|---|---|---|---|
| Umbriferous | ElecGtr1, 1DT, 2, 2DT, 3, 3DT, 4, 4DT, 5, 5DT, 6: `NN_ElecGtrXDI` → `NN_ElecGtrX` | 11 | 6 |
| The Bright Star Alliance | ElecGtr1, 2, 2DT, 3, 4, 5, 5DT: `NN_ElecGtrXDI` → `NN_ElecGtrX` | 7 | 5 |
| Sonnet & Alcohol | ElecGtr1, 2: `NN_ElecGtrXDI` → `NN_ElecGtrX` | 2 | 2 |
| The Laminar Flow | ElecGtr01–11: `NN_ElecGtrXXDI` → `NN_ElecGtrXXMic1`, `Mic2`, `Mic3` | 11 | 11 |

That is 31 more parts (24 tones). With the first five, set 4 declares 52 parts in 9
bands.

- **The Laminar Flow has 11 parts, not 5.** The research summary listed ElecGtr01–05; its
  stored track list shows DIs for ElecGtr01 to 11.
- **Not parts (no DI):** The Laminar Flow `ElecGtr01DTMic1–3`. They stay in the mix.
- **The Bright Star Alliance ElecGtr3:** its amp file is twice its DI's size, so probably
  stereo. Stereo tracks are folded to mono by the same loader as every other session.

### Rules: the same as the first five

The rules above apply unchanged: the waveform same-take test and its thresholds, the
reference choice in `AMP_PREFERENCE` order (Mic1 first for The Laminar Flow), the
exclusions, the marks, the gain classes on set 3's thresholds, crop rule 2 (`di-activity`,
10 s, 48 kHz), the mix rule, the lags and the leakage guards. The tools in
`datasets-set4/_tools/` gain only the four sessions' entries, and the Wayback URLs in
place of the direct-host ones. The first five sessions are not re-measured: their
`measured.json` entries and crops are kept as they are.

### One added rule, for The Laminar Flow only

The research lists The Laminar Flow as "classic rock, crunch likely (unverified)". Set 4
is heavy confirmation material, and every part kept so far is firm "driven". So:

- **A Laminar Flow part is kept only if its session-level `gain_class` is `crunch` or
  `high-gain`** (`classify.py`, set 3's thresholds, not recalibrated).
- A part that passes every other rule but classifies `clean` is excluded with the reason
  "classifies clean: The Laminar Flow keeps only crunch or high-gain parts (amendment 1)".
- The crop class (`gain_class_crop`) does not decide it.
- The rule is fixed here, before any Laminar Flow audio is downloaded or measured. It is
  applied by `research/validation_set4.py` from the catalogue, with nothing else read.

The other three new bands keep set 3's rule, as the first five do: a part of any gain
class is kept.

### Order of work for the addition

1. This amendment is committed.
2. The four archives are downloaded and verified, and their hashes and readmes recorded.
3. They are added to `_tools/manifest.json`; `set4.py` measures only the new sessions;
   `write_catalog.py` rewrites the catalogue; `build_crops.py` cuts only the new crops.
4. `docs/validation-set4.json` and `docs/validation-set4.md` are regenerated and updated.
5. `learn/set4.py` and its tests are extended to the new bands, sessions and slugs.

As before, no plugin is run, no render made, no preset scored, no network inference run
and nothing listened to.
