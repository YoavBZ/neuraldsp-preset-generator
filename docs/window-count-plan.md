# The window count, W0 (declared)

**Status:** declared 2026-11-21, before any count. It comes from Plan 2 of the draft "Direction 1 after R-alone"
plans, whose independent review approved W0 only, with changes C1 to C5 (all built in below). Code:
`learn/window_count.py` (tests `tests/test_window_count.py`). Ledger: `preset-ladder` `phase_wc`, then
`phase_wc_outcome` after the audit. Data: `~/ndsp-presets/learn/window-count/`. Not run.

**CPU only.** It makes no render, no separation and no training, uses no plugin and no MPS, and involves no listening.
It reads no preset and chooses nothing. It changes nothing in the product.

## 1. The question and the goal check

The note-matched replay ([results](note-replay-results.md), R-alone) found that render-and-compare through a same-notes
dry guitar beats a blind pick only when the target guitar plays with no other guitar. With X-LANCE's stem of the
mix with no other guitar, I against a blind pick was −0.221 by the score. With other guitars present it was worse than
blind (+0.171). So the route is scoped to windows where the requested part plays alone.

**The question:** how often does a song offer a 10-s window where the requested guitar part plays and no other guitar
does? The answer comes by truth, from multitracks.

**The goal check.** The goal is the most accurate preset from a song with no human step, and this count sizes the
scoped route's reach.
- **It is descriptive and cannot stop the route (C5).** W-rare is out of reach: about 31% of the locator's songs
  have a single guitar part.
- **Small-band multitracks probably overstate** how many windows released records offer.
- **What it cannot do:** it does not find the windows from the mix. That is W1, the detector, which is held: it needs
  a redesigned validation (C6) and its own review.
- **It converges.** It is read once, with no threshold retuned.

## 2. What changed from the draft (the review's C1 to C5 and the user's answers of 2026-11-21)

- **C1: stage D (the dose for "dominant") is dropped.** Only "alone" is counted: the replay's only evidence is
  no-other-guitar, and its full-mix row was worse than blind even at 6 to 10 dB.
- **C2: "usable" exposure is not counted.** Exposure needs mix levels, which raw multitracks do not have.
  - The review asked for exposure as a side reading where mix-level stems exist (MedleyDB).
  - **That reading is unavailable:** only MedleyDB's mixes and electric-guitar raw tracks were extracted, and the
    archives were not kept. No STEM audio is on disk.
  - W0 therefore counts "alone" only, and exposure is unknown in both sets.
- **C3: the rule is the replay's condition.**
  - **The strict rule decides:** the other guitars are inactive in 100% of the window's frames. The draft's 90% rule
    goes beside, as a side count.
  - **"Another guitar" is every track the replay's no-other-guitar backing left out:** every track that
    `data_cleaning.track_class` calls a guitar, acoustic ones and the keyboard player's guitar included. A non-DI
    track counts when it is in the session's mix list; a DI always counts (`trusted_data.session_guitar_parts`'
    rule). Click and talkback tracks never count.
  - **In MedleyDB:** every stem whose instrument names a guitar (clean or distorted electric, acoustic, lap steel).
    Banjo and mandolin stay out, as the replay's backing kept them.
- **C4: every part is counted**, with the known-scope split beside: in scope (clean or crunch), high-gain, and
  unlabelled. No unlabelled part is dropped.
- **C5: the reading is descriptive** (above).
- **MedleyDB (set 6) is used, declared** (the user).
  - It is truth for the count only: it reads no preset and trains nothing. The use is recorded in
    `docs/validation-set6.json` `held_out_uses`.
  - **Basic Pitch trained on MedleyDB, so it can never be a note-route test.**
  - The reserve's five MedleyDB bands stay sealed (Aimee Norwich, Big Troubles, Dahka Band, Little Tybee and
    Port St Willow, 6 songs), as the house rules keep the reserve. That leaves 67 songs.
- **The locator's 36 songs outside every held set stay in** (the user).
- **A double-tracked part counts as another guitar** in the deciding count; the same-part count goes beside it (the
  user).
- **The two shares 0.5 and 0.2 stay as the lines** (the user).
- **R1 is not used.**

## 3. The definitions

**A window:** 10 s on a 1-s step: the search's section length and the part locator's frames (100 ms,
`learn/locator_truth.py`).

**Activity, per 100-ms frame.**
- **The locator set:**
  - a locator part is active where its DI is within 30 dB of its own loudest frame (the locator's rule);
  - any other guitar is active where any of its tracks is: a DI within 30 dB, or an amp, mic or other track within
    20 dB, of its own loudest frame (the locator's no-DI rule);
  - tracks are grouped into guitars by `verify_tracks.guitar_part_key`, and a track whose key is a locator part's
    belongs to that part.
- **The MedleyDB set:** a guitar stem is active where MedleyDB's activation confidence reads at least 0.5 at any
  annotation sample inside the frame, OR any of its raw tracks on disk is within 20 dB of its own loudest frame.
  - Annotations: `v2` where it exists, else `original`. They are read from the metadata clone's git store at commit
    `537bb7b`, with no download and no checkout change. Each annotation's git blob id is recorded.
  - Only electric raws are on disk, so an acoustic or lap steel stem rests on its annotation alone.
  - A song with a guitar stem that has neither an annotation nor a raw on disk is left out and counted. A dry check
    of inputs and metadata found none: the 10 songs without any annotation have a single electric guitar stem, read
    from its raws.
  - Why OR: MedleyDB's confidence is normalised to the mix's energy, so a quiet guitar can read inactive. OR'ing the
    raw rule makes "no other guitar" stricter.

**The target parts.**
- **Locator:** every locator DI part in the 36 songs, which is 84 parts, the keyboard player's guitar parts included.
- **MedleyDB:** every electric guitar stem (clean or distorted electric guitar).

**Alone (deciding):** the target is active in at least 60% of the window's frames (the locator's rule), and the union
of every other guitar is active in none of them.

**Side counts:**
- **90%:** the other guitars active in at most 10% of the frames.
- **Same part:** the part's own "DT" doubles do not count as other guitars. This is the locator's name rule;
  MedleyDB names no doubles, so there it equals the deciding count.
- **Three disjoint:** at least 3 non-overlapping alone windows.
- **The curve:** offers at an allowed other-guitar share of 0, 0.05, 0.1, 0.2, 0.3, 0.5 and 1.0. At 1.0 the target
  only has to play.
- **MedleyDB, annotation only:** MedleyDB's published rule without the raw envelopes, on songs where every guitar
  stem has an annotation.
- **MedleyDB without bleed:** songs not marked `has_bleed`.
- **Rule agreement (a diagnostic):** per electric stem with both sources, the share of frames where the annotation
  and the raw rule agree.

**A part offers a window** when at least one window is alone.

## 4. The sets

| Set | Songs | Bands | Target parts | Activity from |
|---|---|---|---|---|
| `locator`: the part locator's development sessions less every band in `capture_labels.HELD_BANDS` (V-real, NS, the panel, the reserve, BKS) | 36 | 20 | 84 | The locator's stored envelopes, plus this count's own for guitar tracks they lack (three DI-only guitars in one session) |
| `medleydb`: set 6 less the reserve's bands | 67 | 39 | 124 (every electric guitar stem) | Annotations OR raw envelopes |

- **Shared bands:** none. Set 6's declaration checked its bands against every earlier set.
- **Music Delta:** MedleyDB's 15 Music Delta songs are one band.
- **Trusted data:** Silent Waves and Drowning are in neither set.

## 5. The readings and the outcome (coded before the count, `W0_TABLE`)

**p** is the share of songs whose requested part offers an alone window.
- Each song counts once, as the share of its target parts that offer one.
- Songs are averaged inside their band, and p is the mean of band means.
- The 90% interval is cluster t over bands (`pipeline_fix.clustered`), with the song-weighted mean beside.

**Reported:** each set alone and the pool (both sets, clustered by band), each with its own code. **The headline code
is the pool's;** when a set's own code differs, both are stated.

| p | Code | Reading | Next |
|---|---|---|---|
| lower end at 0.5 or above | W-wide | Most songs offer a window | To the parent and the user: the scoped route can be the main path, with today's path as the fallback. W1 still needs its redesigned validation and its own review |
| upper end at 0.2 or below | W-rare | Few songs do (out of reach here, C5) | To the parent and the user: the scoped route alone is not a product |
| the rest | W-some | A share of songs | To the parent and the user, with the split by scope and role. The route is a branch beside today's path; W1 only on the user's go after its own review |

**Beside the code, all descriptive:**
- the side counts and the curve;
- the split by known scope (in scope, high-gain, unlabelled; MedleyDB's clean or distorted label);
- the split by the locator's role (lead, rhythm, none);
- the single-guitar songs;
- the leave-one-band-out means.

**Power (the draft's planning read):** with 20 bands the locator's interval is about ±0.15 to ±0.17. Expect W-wide or
W-some.

## 6. Running it

1. **This declaration merges first.** Before the merge only a zero-outcome input check ran. It resolved every input:
   the locator's 36 songs and 84 parts, and MedleyDB's metadata, annotations and raw files. It counted no window and
   read no MedleyDB audio.
2. **Then the count.** `window_count run --limit 3` times the first 3 songs (no measured runtime exists), then
   `window_count run` once over every song. It writes `w0-results.json` and refuses to run again.
3. **The raw hand-back** goes to `~/ndsp-presets/handover/2026-11-21/window-count-handback.md` for the parent's
   audit, an independent recompute from the tracks.
4. **The results** then come with `phase_wc_outcome`.

**House rules:**
- CPU only, beside other sessions' renders;
- the disk guard at 31 GB;
- PIDs recorded at launch;
- public repo: song titles and band names only, no audio, paths or settings.

## 7. What it can't say

- How often the user's kind of released records offer a window: both sets are multitracks of mostly small bands.
- Whether a window is exposed enough to search on: exposure is unknown (C2).
- Anything about "dominant": stage D is dropped (C1).
- Whether a rule can find the windows from the mix: that is W1, held.
- Bleed: on the raw-envelope side, bleed can mark a track active where it is silent. That makes other guitars look
  more active (a stricter count), but can also make a target look more active.
