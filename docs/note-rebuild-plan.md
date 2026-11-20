# A dry guitar rebuilt from the song's notes: the declaration (stage P, and the tables for stages 1–3)

Declared 2026-11-20, before anything in it runs, from the plan approved with changes by its independent review the same
day (the review's changes are binding and each is listed in [section 9](#9-the-reviews-changes-and-where-each-lands)).
Ledger `note-rebuild`, phase `phase_nr_p`. Code `learn/note_rebuild.py`; tests `tests/test_note_rebuild.py` (pure) and
`tests/test_note_rebuild_synth.py` (numpy). Outputs under `PF/note-rebuild/`, each written once and never overwritten.

**The user's word (2026-11-20):** try the rebuild again, and "this time we must do it right". **The user's rule:** no
action rests on a J0 gap under 0.05; "passes" means decided better with the mean at −0.10 or beyond. Everything here is
by the score until the blind sitting.

## 1. What this is for, and the goal check

Direction 1 of the strategic review searches the plugin's settings at song time: render candidates through a dry
guitar that plays the song's notes, and keep the one closest to the song's separated guitar. Its first test, the
note-matched replay (`preset-ladder` `phase_replay`), uses a blurred copy of the true DI as the dry guitar. If that
passes, the one missing part is a dry guitar built from the song alone. This declaration builds that part.

**Goal check.** It serves "the most accurate preset without any human intervention" only if the rebuilt dry guitar lets
the search pick a preset a heard size better than both the fixed centre preset Cen and a blind pick from the same menu,
on the product's input. Every stage has a coded stop ([section 7](#7-stop-rules)). Nothing trains, and nothing is
downloaded, before the replay's gate reads "pass".

## 2. The route, and how it differs from what failed

**The note route first:** read the notes, play each one back from single recorded DI notes (EGFxSet's clean set: a
Stratocaster, every string and fret recorded alone, CC BY 4.0, on disk), then level and balance the result as the
measure sets every DI. The **network route** (a rebuild network retrained on trusted pairs) and the **guided route** (a
network given the stem and the note route's output) stay as declared fallbacks, each only on the user's go after a
stage-1 or stage-2 stop. (The plan's "Route A/B/C" are not used as names: "route B" is already a separator term in
`docs/separation-finetune-plan.md`.)

**The case against starting with the network route rests on C′'s measured ceiling:** even with a perfect stem, a search
through C′'s rebuild kept about half of the true DI's gain (−0.094 against −0.174 against S, ROADMAP 2026-10-19), and
its rebuild lost the ranking through short-time magnitude above 2 kHz, not phase (`docs/rebuild-gap-results.md`). The
note route is not claimed to remove those faults "by construction"; it is the cheapest route whose first test can
decide anything, with no training and no download.

| What failed before | How it is met here |
|---|---|
| C′ trained on plugin renders from before the trusted-data rules (the trust audit) | Nothing trains. Every input file is hashed; every build input is checked against the exclusion list in code (`assert_clear`) |
| C′ never saw an X-LANCE stem | Stage 2 reads X-LANCE stems of the ladder's built mixes (the replay's, kept), alone and with other guitars |
| Every C′ result under 0.05, gated on a broken-network check | Component figures are reports, never gates. Every gate is the two-number bar (G and I) |
| A bar any menu passes (beat S, or beat Cen) | G = pick − Cen and I = pick − blind pick, each decided better with the mean at −0.10 or beyond |
| Asserted in prose, not in code | Exclusion, tables and refusals are code with tests |
| The old models | None is loaded (the user's ruling); only stored figures are quoted |

## 3. Stage P: preparation (zero renders, separations, downloads and training)

Runs beside the replay, after this declaration's PR is merged.

| # | Work | Command | Output |
|---|---|---|---|
| P1 | The exclusion list: every DI file, GOAT item, capture, creator, pack, band and session under the ladder's 480 parts, and the six lent sessions with their guitar tracks; sha256 of every DI section, amp section and lent guitar track; GOAT zip members' CRC; the parts whose material a released transcriber trained on | `exclusion` | `exclusion.json` (body hash checked on every load) |
| P2 | The note set: all 690 clean notes (5 pickups × 6 strings × 23 frets), each checked under `NOTE_RULES` | `notes` | `notes.json` |
| P3 | The true notes: every GOAT item's fine-aligned MIDI with each note's string, fret and articulations from its DadaGP tab; per GOAT and cap1 read unit the notes in its DI section's window | `true-notes` | `true-notes.json`, `true-notes/<item>.json` |
| P4 | The re-synthesis: the pure functions in `learn/note_rebuild.py` (section 4), tested on made-up note lists, byte for byte repeatable | the tests | the tests' pass |
| P7 | A timing probe: seconds per 10-s window on the CPU for the oracle onset step, each arm's re-synthesis and the figures, on GOAT development items outside the ladder | `probe` | `probe.json` |

P5 (the trusted-pairs table for the fallbacks) is deferred to a fallback's own declaration; it must then add
Guitar-TECHS, the sessions released into training on 2026-10-28, GuitarJam and IDMT, each with its state, and the six
lent sessions' guitar tracks are already in P1. P6 (the blurred DI's distance from the true DI) is dropped: the blur
keeps exactly what re-synthesis loses, so its distance cannot bridge to a rebuild; stage 1's paired share of I is the
bridge. P8 (the full declarations of stages 1 and 2) is written once the replay's declaration is merged.

**P2's rules (`NOTE_RULES`), fixed before any note is read:** 48 kHz, 5.0 s; no sample at or above 0.999 of full scale;
an attack (first sample past a tenth of the first second's peak) inside the first second; within 50 cents of the
nominal pitch (`build_riffs.detune_cents`); the nominal note beats its rivals at −12, ±1, ±2 and +12 semitones on the
energy of harmonics 1–4 (`pitch_rival`); the mains series (50 or 60 Hz, harmonics 1–4) in the last second at least 40
dB under the note's 50-ms attack level. A failed note is never played: the placing rule avoids it.

**P3's matching.** GOAT ships the item's DI, a fine-aligned MIDI (one velocity, no bends), the Guitar Pro tab and its
DadaGP tokens. Timing and pitch come from the fine-aligned MIDI. String, fret and articulation come from the tab: its
notes are read in playing order (repeats unrolled, tied notes not re-struck) and aligned to the MIDI's by pitch sequence
(`difflib.SequenceMatcher`, autojunk off; MIDI notes within 50 ms form one chord, since the fine alignment spreads a
chord's notes; the semitone offset that pairs the most notes is taken from the tab's downtune ±3 and an octave either
way). A MIDI note with no tab partner keeps its exact pitch and takes a string by the placing rule (the lowest free
fret). A unit **carries** stage 1 when its item has fine-aligned MIDI and at least 8 notes sound in its window; the
share of its notes matched to the tab is reported, and stage 1 reads units at 80% or more beside.

At planning (development smoke, nothing saved): 152 of GOAT's 172 items have fine-aligned MIDI (20 have none); of the
146 with a tab, the share of MIDI notes matched has median 0.95, 10th percentile 0.71, lowest 0.17; 144 match at the
downtune's own offset and 2 an octave apart. 15 of the ladder's 130 GOAT items have no fine-aligned MIDI, so some of the
replay's 72 GOAT parts cannot carry stage 1; P3 counts them once the replay's draw exists.

**Stage P's code (`NP_TABLE`, `np_code`):**

| Code | When | Next |
|---|---|---|
| NP-ready | P1 to P4 pass and at least 30 of the replay's drawn GOAT parts carry true notes | wait for the replay's gate |
| NP-few | P1 to P4 pass and fewer than 30 carry | stage 1's declaration adds revision-pool units (below) by a seeded rule fixed before any render; to the orchestrator |
| NP-gap | the note set at the middle pickup has failed notes | the placing rule avoids them and stage 1's declaration lists them; then NP-ready or NP-few by the count |
| NP-broken | P1, P3 or P4 fails its own checks | stop; fix and re-declare |

## 4. The re-synthesis, every rule frozen here (P4)

For one window of the reference guitar and its notes. No randomness: a re-run is byte for byte.

1. **Clean the note list:** keep MIDI 40 to 88; merge a pitch struck twice within 30 ms; at most six notes at once.
2. **The oracle onset step (stage 1 only):** each onset group (onsets within 30 ms) moves to the true DI's steepest
   rise within ±50 ms (high-passed at 1 kHz, 2-ms frames at a 1-ms hop) when that rise is at least 3 dB; else it is
   kept. The shift is reported per unit.
3. **The source of each note:** the tab's string and fret (when matched); if the tab's fret is more than 2 semitones
   from the note's pitch (an octave apart in the MIDI), the same string at the fret that plays it; else, or with no tab,
   the placing rule. A failed note is skipped by the same rules.
4. **Retune:** each sample resampled from its own measured pitch (P2's cents) to the note's pitch plus the
   reference's global tuning (the magnitude-weighted circular mean of spectral peaks' deviations from A440, 80–1,400
   Hz). This covers the riff library's 15-cent spread, downtuned items (up to 2 semitones) and the record's tuning.
5. **Prepare each sample** (the riff library's lessons, `research/build_riffs.py`): denoised above 3 kHz only
   (noisereduce, non-stationary, prop 0.9, time constant 2 s), started 2 ms before its attack with a 2-ms fade in, set
   to a common level by its first 0.3 s. The pickup is named: **Middle**, the riff library's (EGFxSet's quietest).
6. **Place and end:** each sample's attack at its onset; it sounds to its MIDI note-off with a 20-ms fade (the mute);
   cut with a 10-ms fade when its string is plucked again; faded over its last 150 ms if the note outlasts the sample.
7. **Articulations (stated limits):** dead notes a 40-ms pluck 6 dB down; palm-muted notes held at most 150 ms; ghost
   notes 10 dB down; hammer-ons, pull-offs and slides 6 dB down (no pick attack). Bends, vibrato, harmonics, grace notes
   and tremolo are played plain. The articulated share is reported per unit.
8. **Equal onset groups:** a group of k notes struck together plays each at 1/√k, so chords and single notes are
   equally loud (the riff library's lesson).
9. **Levels, one per arm:**
   - `nr-plain`: no further gain;
   - `nr-level`: each group's gain from the reference's RMS over 50 ms from its onset (cut at the next group), in dB
     about the window's median, held within ±9 dB;
   - `nr-oracle` (a diagnostic, never a pass path): each group's gain so the plain re-synthesis' RMS over the same span
     equals the true DI's, about the median ratio, held within ±20 dB.
10. **Balance and loudness:** the replay's `avg` step (`di_robustness.average_balance` with the replay's `others`),
    bound by stage 1's declaration; then `nr-plain` and `nr-level` at −22.9 LUFS (the product's DI level), `nr-oracle`
    at the true DI's loudness.

**Figures per window (reports, zero render cost):** crest-factor difference, frame-envelope correlation, frame-by-frame
log-mel distance over the frames where the true DI plays, the share of energy above 2 kHz (both sides), and J0's
playing-frame mask from the rebuilt guitar against the true DI's at each of J0's frame sizes (agreement and pause
shares), with the windows J0 would refuse.

## 5. The gate (the replay's declared table decides; added here)

Nothing beyond stage P runs until the orchestrator says the replay's gate has passed. Two additions:
- **The Both rows.** If a Both row of the replay (stem and blurred DI together) fails, the user is asked before stage 1.
- **A blurred-DI fail.** Re-synthesis also ends at the average balance, so before a fail of the replay's `avg+mild` row
  closes this route, the replay's rows with each blur alone must have been read (the replay has declared them).

## 6. The tables for stages 1–3 (coded in `learn/note_rebuild.py`, tested)

**The two-number bar (`row_reading`, the replay's own):** G = the pick less Cen, I = the pick less the blind pick (the
mean held-half score of the part's menu), each with its 90% cluster t interval on the deciding pool.

| Reading | When |
|---|---|
| passes | G and I each decided better (the whole interval below zero) with the mean at −0.10 or beyond |
| fails | G's or I's interval rules out a gain beyond −0.05 (its lower end at −0.05 or above); an interval inside ±0.05 is worded "not readable by the score" |
| undecided | the rest; undecided is not failed |

When the replay's `learn/note_replay.py` is merged, stage 1 imports its `row_reading`, and a test asserts the two agree.

**Stage 1, the true-notes test (renders only).** Units: the replay's GOAT parts that carry true notes, read against the
replay's **GOAT-alone** Control, Blurred and blind-pick rows recomputed on the same parts (zero renders); the share of
the GOAT-alone Blurred row's I kept is reported beside. Dry guitars: `nr-plain`, `nr-level` and `nr-oracle`, all with
the tab's strings and the oracle onset step. Reference: the clean record. Renders: at 72 parts × 23 settings × 3 arms ×
2 for priming, 9,936, about 2 h 26 min at the ladder's 68 a minute (about half with one primed process per part, if the
replay's position check allows it).

| Code (`N1_TABLE`, `n1_code`) | When | Next |
|---|---|---|
| N1-pass | `nr-plain` or `nr-level` passes | stage 2 with the simpler passing arm (`nr-plain` if both) |
| N1-fail | `nr-plain` and `nr-level` both fail | the re-synthesis with true notes, oracle onsets and the tab's strings does not pick a heard size better; with `nr-oracle`'s row and the breakdowns to the user: the guided or the network route, or stop. Audited adversarially before it is written up. Only then may it read "no transcriber can rescue plain re-synthesis" |
| N1-between | anything else | undecided, not failed; to the user with each arm's share of the Blurred row's I; one revision allowed, declared first, read on fresh units |

Two deciding arms share the units, so the chance of a false pass is at most 10%. Beside each arm, at no render cost:
by alignment-F tertile, guitar brand (Strat against the rest: EGFxSet is a Strat), the tab-matched share (80% or more
against less), the articulated share, J0's mask agreement and the count of windows J0 refuses; the onset step's shift.

**Stage 2, the transcriber (the first download; its own declaration).** Rows run in order, each **only after the one
before passes** (`n2_next_row`):

| Row | Reference | Dry guitar rebuilt from |
|---|---|---|
| B-clean | the clean record | the clean record |
| B-alone | the stem alone | the stem alone |
| B-full | the stem of the full mix | the stem of the full mix |

| Code (`N2_TABLE`, `n2_code`) | When | Next |
|---|---|---|
| N2-full | B-full passes | stage 3 |
| N2-exposed | B-alone passes, B-full does not | stage 3 on exposed windows only; no automatic finder of such windows exists (today the user picks them by ear, a human step), and how many songs offer them is not known |
| N2-stem | B-clean passes, B-alone does not | the separator breaks the notes: stop, to the user; separator and transcription work get a preset-level yardstick |
| N2-notes | B-clean fails | the transcriber's accuracy is the gap: the dose read (true notes dropped, added and shifted at three declared levels), then to the user |
| N2-between | B-clean undecided | to the user; one revision allowed, on fresh units |

Stage 2's declaration must carry: Basic Pitch on the existing Python 3.9.6 interpreter, with one fixed inference backend
(so byte-for-byte holds); hashes checked against PyPI's published sha256 digests (`--require-hashes`) and recorded in a
manifest with each dependency's licence; the minimum note length (its default drops fast notes; verified at install)
and the rule for notes below MIDI 40; and **the panel's units are MedleyDB (set 6), which Basic Pitch was trained on**
(P1 records them as `transcriber_overlap`), so stage 2 reads the panel beside, not as a clean held-out read at the
transcriber. The plan's "no ladder unit is affected" was wrong for the panel.

**Stage 3, the blind sitting.** 21 cards drawn by seed from the passing row's units, guitar exposed, clean and crunch
only; each card holds the record and four presets through the true DI: Cen, the rebuilt-DI pick, the blurred-DI pick and
a seeded blind menu setting. Ranks with ties allowed (a tie counts as no preference). One-sided sign tests at 5% on the
untied cards (`n3_code`):

| Code (`N3_TABLE`) | When | Next |
|---|---|---|
| N3-heard | the pick is ranked above Cen and above the blind setting | a search through the rebuilt DI (from Cen, against the stem), with fresh held-half renders through the true DI, under its own declaration; not product wiring (the menu here is a true-DI search's own trials, which the product won't have) |
| N3-blind | above Cen, not above the blind setting | heard over Cen without the comparison working: stop, to the user |
| N3-not-heard | Cen ranked above the pick | the score's gain is not heard: stop, to the user |
| N3-between | anything else | undecided, to the user |

## 7. Stop rules

- No training and no download before the replay's gate reads "pass"; nothing beyond stage P before the orchestrator
  says so.
- **One build, one read per stage.** A stage may be revised once, declared and reviewed before the second read.
- **Reads are capped across designs, not only within one.** A revision is read on fresh parts only: the **revision
  pool**, cap1 units whose DI is a GOAT item not among the replay's drawn parts (they carry GOAT's notes and their own
  search records). The replay's own parts are read once per stage.
- No human window-picking anywhere in the route.
- A "fails" or "stops" reading is audited adversarially before it is written up. Undecided is not failed and goes to
  the user with its intervals, shares and breakdowns.
- The route stops at N1-fail, N2-stem, N3-blind or N3-not-heard unless the user chooses a fallback.

## 8. Costs, measured rates only

| Item | Count | Time | Rate |
|---|---|---|---|
| Stage P | zero renders | CPU; P7 measures it | — |
| At planning (development smoke) | re-synthesis of one 10-s window | about 0.3 s with note preparation, under 0.05 s per arm after | this Mac, CPU |
| Stage 1 | 9,936 renders | about 2 h 26 min (about half with one primed process a part) | the ladder's 12,480 in 3 h 4 min on 3 processes |
| An ear check before stage 1 | a few clips of development items through two presets | stage 1's declaration counts them | — |
| Stage 2, three rows | 72 × 23 × 3 × 2 at most | about 2 h 26 min; a third if B-clean does not pass | as above |
| Basic Pitch on a window | — | measured by stage 2's probe | — |
| Stage 3 | about 570 renders and 21 cards | about 8 min of renders; about 50 to 63 min of the user's time | the ladder's ear page and sitting |

Limits throughout: at most 3 render processes and one MPS job; `setopt no_bg_nice` and caffeinate; the 31 GB disk
guard; PIDs recorded at launch and only those stopped; monitoring by the executor session. No coding time is estimated.

## 9. The review's changes, and where each lands

| Review item | Where |
|---|---|
| 1. The two-number bar; a blind-menu arm on stage 3 | `row_reading`, every table; `N3_TABLE` and the cards |
| 2. Stage 1 a true upper bound: the tab's strings and articulations, the oracle onset step, alignment-F tertiles, 1-fail only on the refined arms | P3, section 4 steps 2–3, stage 1's breakdowns; every arm is refined |
| 3. The riff library's lessons: hiss above 3 kHz, retuning, mutes, equal chord levels, the pickup named; retuning to the record's own tuning; an ear check of development clips first | section 4 steps 4–8; section 8 |
| 4. `nr-oracle`; brand, articulated share, alignment F, mask agreement at no render cost | stage 1; `figures` |
| 5. 72 GOAT parts against the replay's GOAT-alone rows; 9,936 renders | stage 1; section 8 |
| 6. Keep the stems | the replay now keeps them; stage 2 reuses them |
| 7. Stage 2 continues only on a pass; no automatic window finder stated | `n2_next_row`, `N2_TABLE` |
| 8. Reads capped across designs; revisions on fresh parts | section 7, the revision pool |
| 9. Basic Pitch: Python 3.9.6, one backend, PyPI hashes, licences, minimum note length, notes below MIDI 40, the MedleyDB/GuitarSet assert | stage 2's declaration (carried); P1's `transcriber_overlap` |
| 10. Stage 3 leads to a search through the rebuilt DI, not to wiring | `N3_TABLE` |
| 11. Build P1–P4 and P7; drop P6; defer P5; P8 after the replay's declaration | section 3 |
| 12. The fallbacks' data undercounted; the lent sessions' guitar tracks excluded | P5's carried list; P1 |
| The gate: the Both rows; a blurred-DI fail needs the single-blur rows | section 5 |
| Drop "removes the old faults by construction"; the case against the network route on C′'s ceiling | section 2 |

## 10. What it can't say, and what is not verified

- The panel is MedleyDB (section 6, stage 2). Stage 1 is GOAT only and is unaffected.
- GOAT's fine-aligned MIDI is not exact (median alignment F 0.845 across GOAT); the oracle onset step corrects timing
  within ±50 ms only, and a missed or extra note stays. Results are reported by alignment-F tertile for that reason.
- One guitar's notes (a Strat at the middle pickup). The balance step removes its long-term colour, not its attacks.
- Bends, vibrato and slides are not modelled.
- Stage 1's reference is the clean record, not a stem; stage 2 brings the stem.
- One listener stands behind every ear result.
- Names: `nr-plain`, `nr-level`, `nr-oracle`, the codes NP-, N1-, N2-, N3-, the rows B-clean, B-alone, B-full, and
  "the revision pool" are new here (grepped against the docs and the ledger).
