# A dry guitar rebuilt from the song's notes: the declaration (stage P, and the tables for stages 1–3)

Declared 2026-11-20, before anything in it runs, from the plan approved with changes by its independent review the same
day (the review's changes are binding and each is listed in [section 9](#9-the-reviews-changes-and-where-each-lands)).
Revised the same day after PR #525's review (changes needed: three blocking, seven required; each placed in
[section 9](#9-the-reviews-changes-and-where-each-lands)).
Ledger `note-rebuild`, phase `phase_nr_p`. Code `learn/note_rebuild.py`; tests `tests/test_note_rebuild.py` (pure) and
`tests/test_note_rebuild_synth.py` (numpy). Outputs under `PF/note-rebuild/`, each written once and never overwritten.

**Status, 2026-11-22:** stage 1 is retired unissued on the user's answer (its renders set aside unread; `N1_TABLE` never
issued; no note-route read of any part so far). The redo is declared in
[section 12](#12-the-redo-notes-transcribed-from-the-di-read-as-the-fs-notes-row-2026-11-22-ledger-phase_nr_1_redo):
notes transcribed from the DI by Basic Pitch, one rebuilt guitar (`tr-di`), read as the from-scratch search's
`fs-notes` row on its 47 parts with BKS+GOAT deciding. Nothing in it has run.

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
| P1 | The exclusion list: every DI file, GOAT item, capture, creator, pack, band and session under the ladder's 480 parts, and the six lent sessions with their guitar tracks; sha256 of every DI section, amp section and lent guitar track; GOAT zip members' CRC; the parts whose material a released transcriber trained on. A file missing on disk or a session not found is recorded and fails `p1_ok` | `exclusion` | `exclusion.json` (body hash checked on every load) |
| P2 | The note set: all 690 clean notes (5 pickups × 6 strings × 23 frets), each checked under `NOTE_RULES`, every hash checked clear of the exclusion list; source, licence and trust recorded | `notes` | `notes.json` |
| P3 | The true notes: every GOAT item's fine-aligned MIDI with each note's string, fret and articulations from its DadaGP tab; per GOAT and cap1 read unit the notes in its DI section's window; the MIDI reader's cross-check against the tab | `true-notes` | `true-notes.json`, `true-notes/<item>.json` |
| P4 | The re-synthesis: the pure functions in `learn/note_rebuild.py` (section 4), tested on made-up note lists, byte for byte repeatable | the tests | the tests' pass |
| P7 | A timing probe: seconds per 10-s window on the CPU for the oracle onset step, each arm's re-synthesis and the figures' computation, on GOAT development items outside the ladder. Timing only: no figure, level or audio is stored (development items, not evidence) | `probe` | `probe.json` |

Every command refuses before any heavy import or work unless the ledger holds `phase_nr_p`, and refuses to overwrite
its output (`true-notes` also refuses a left-over `true-notes.partial/`: its per-item files are written there and moved
into place only once every item is built). Each refusal is tested.

P5 (the trusted-pairs table for the fallbacks) is deferred to a fallback's own declaration; it must then add
Guitar-TECHS, the sessions released into training on 2026-10-28, GuitarJam and IDMT, each with its state, and the six
lent sessions' guitar tracks are already in P1. P6 (the blurred DI's distance from the true DI) is dropped: the blur
keeps exactly what re-synthesis loses, so its distance cannot bridge to a rebuild; stage 1's paired share of I is the
bridge. P8 (the full declarations of stages 1 and 2) is written once the replay's declaration is merged.

**P2's rules (`NOTE_RULES`), fixed before any note is read:** 48 kHz, 5.0 s; no sample at or above 0.999 of full scale;
an attack (first sample past a tenth of the first second's peak) inside the first second; within 50 cents of the
nominal pitch (`build_riffs.detune_cents`); the nominal note beats its rivals at −12, ±1, ±2 and +12 semitones on the
energy of harmonics 1–4 (`pitch_rival`); the mains series (50 or 60 Hz, harmonics 1–4) in the last second at least 40
dB under the note's 50-ms attack level. A failed note is never played: the placing rule avoids it. The failures are
counted by reason (the −12 rival holds the nominal note's harmonics 1 and 2, so the count shows whether it fails good
notes). **The note set's source and trust,** recorded in `notes.json`: EGFxSet's Clean set, Zenodo 7044411, CC BY 4.0;
raw single-note DI recordings of one Stratocaster, never amped; no ladder unit, capture or session uses it. Every
note's hash is checked clear of the exclusion list (`assert_clear`) when `notes.json` is built and again whenever a
bank opens, and the bank refuses any file whose hash differs from `notes.json` when it loads.

**P3's matching.** GOAT ships the item's DI, a fine-aligned MIDI (one velocity, no bends), the Guitar Pro tab and its
DadaGP tokens. Timing and pitch come from the fine-aligned MIDI. String, fret and articulation come from the tab: its
notes are read in playing order (repeats unrolled, tied notes not re-struck) and aligned to the MIDI's by pitch sequence
(`difflib.SequenceMatcher`, autojunk off; MIDI notes within `CHORD_S` = 50 ms form one chord, since the fine alignment
spreads a chord's notes; the same 50 ms makes the re-synthesis' onset groups and the clean-up's merge; the semitone
offset that pairs the most notes is taken from the tab's downtune ±3 and an octave either
way). A MIDI note with no tab partner keeps its exact pitch and takes a string by the placing rule (the lowest free
fret). A unit **carries** stage 1 when its item has fine-aligned MIDI and at least 8 notes sound in its window; the
share of its notes matched to the tab is reported, and stage 1 reads units at 80% or more beside.

**The MIDI reader's cross-check (no download).** Stage 1 relies on the riff builder's own MIDI reader, so P3 checks it
before stage 1: GOAT's unaligned MIDI is exported from the same tab, so the reader's onsets must follow the tab's ticks
(read from the DadaGP text, independently of the MIDI bytes). Over each run of 16 matched notes (hop 8) a straight line
from ticks to seconds; an item passes with a median residual within 5 ms and at least 90% of its MIDI notes matched;
**the reader passes when at least half of the items checked pass** (a broken delta-time, tempo or running-status parse
fails nearly all). At build (development smoke, nothing saved): 132 of 142 items pass, most with a residual of 0 ms;
the rest are tempo changes or repeats the runs span. P3's own pass (`p3_ok`) needs the reader's pass, all 336 GOAT and
cap1 parts recorded, every item with fine-aligned MIDI built, and some GOAT part carrying.

At planning (development smoke, nothing saved): 152 of GOAT's 172 items have fine-aligned MIDI (20 have none); of the
146 with a tab, the share of MIDI notes matched has median 0.95, 10th percentile 0.71, lowest 0.17; 144 match at the
downtune's own offset and 2 an octave apart. 15 of the ladder's 130 GOAT items have no fine-aligned MIDI, so some of the
replay's 72 GOAT parts cannot carry stage 1; P3 counts them once the replay's draw exists.

**Stage P's code (`NP_TABLE`, `np_code`):**

| Code | When | Next |
|---|---|---|
| NP-ready | P1 to P4 pass and at least 30 of the replay's drawn GOAT parts carry true notes | wait for the replay's gate |
| NP-few | P1 to P4 pass and fewer than 30 carry | stage 1's declaration adds revision-pool units (below) by a seeded rule fixed before any render; to the orchestrator |
| NP-gap | the note set at the middle pickup has failed notes | the placing rule avoids them and stage 1's declaration lists them; NP-ready or NP-few follows by the count (`np_code` returns both) |
| NP-broken | P1 (`p1_ok`: 480 parts, every key kind, no missing file, every session found with guitar tracks), P3 (`p3_ok`) or P4 (the tests) fails its own checks | stop; fix and re-declare |

## 4. The re-synthesis, every rule frozen here (P4)

For one window of the reference guitar and its notes. No randomness: a re-run is byte for byte.

1. **Clean the note list:** keep MIDI 40 to 88; merge a pitch struck twice within 30 ms; at most six notes at once.
2. **The oracle onset step (stage 1 only):** each onset group (onsets within 50 ms, `CHORD_S`) moves to the true DI's steepest
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
6. **Place and end:** each sample's attack at its onset (the sample starts 2 ms earlier); it sounds to its MIDI note-off with a 20-ms fade (the mute);
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
10. **Balance and loudness:** the replay's own chain for a dry guitar (the blurred row's: `song_bank.measure`, the
    average guitar's balance at −22.9 LUFS, then the `avg` step with the part's `others`), bound by stage 1's
    declaration; then every arm at −22.9 LUFS. `nr-oracle`'s levels come from the true DI **as the replay renders it**
    (`song_bank.measure` of its section), so it differs from `nr-plain` only by its per-group levels.

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
| N2-exposed | B-alone passes, B-full fails | to the user and stop: it would work only where the target is the only or dominant guitar, no automatic finder of such windows exists, and picking them by ear is a human step (ruled out); a finder needs its own declaration first |
| N2-stem | B-clean passes, B-alone fails | the separator breaks the notes: stop, to the user; separator and transcription work get a preset-level yardstick |
| N2-notes | B-clean fails | the transcriber's accuracy is the gap: the dose read (true notes dropped, added and shifted at three declared levels), then to the user |
| N2-between | any row that ran reads undecided | undecided, not failed: to the user with shares and intervals; one revision allowed, on fresh units |

Stage 2's declaration must carry: Basic Pitch on the existing Python 3.9.6 interpreter, with one fixed inference backend
(so byte-for-byte holds); hashes checked against PyPI's published sha256 digests (`--require-hashes`) and recorded in a
manifest with each dependency's licence; the minimum note length (its default drops fast notes; verified at install)
and the rule for notes below MIDI 40; and **the panel's units are MedleyDB (set 6), which Basic Pitch was trained on**
(P1 records them as `transcriber_overlap`), so stage 2 reads the panel beside, not as a clean held-out read at the
transcriber. The plan's "no ladder unit is affected" was wrong for the panel. Stage 2's declaration also checks the
overlap **song by song** against Basic Pitch's published training lists (verified from its paper or model card), for
every source the ladder uses, the Cambridge sessions included; a set-level check is not enough. (Stage 1 is GOAT only:
GOAT postdates Basic Pitch, and EGFxSet is not in its data.)

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

**What P8 (stages 1 and 2's declarations) must put in code:** the gate refusal, read from the replay's own report
(`R_TABLE`'s cell), not from a message; the carrying subset of the replay's GOAT parts, hashed into the ledger before
any render; the replay's GOAT-alone Control, Blurred and blind-pick rows recomputed on exactly that subset; and stage
3's handling of cards where the pick equals Cen or the blind setting.

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
| At planning (development smoke) | re-synthesis of one 10-s window | about 0.3 s with note preparation, under 0.05 s per arm after | this Mac, CPU; P7 measures it with the finishing chain |
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
| 7. Stage 2 continues only on a pass; no automatic window finder stated | `n2_next_row`, `N2_TABLE`; N2-exposed stops |
| 8. Reads capped across designs; revisions on fresh parts | section 7, the revision pool |
| 9. Basic Pitch: Python 3.9.6, one backend, PyPI hashes, licences, minimum note length, notes below MIDI 40, the MedleyDB/GuitarSet assert | stage 2's declaration (carried); P1's `transcriber_overlap` |
| 10. Stage 3 leads to a search through the rebuilt DI, not to wiring | `N3_TABLE` |
| 11. Build P1–P4 and P7; drop P6; defer P5; P8 after the replay's declaration | section 3 |
| 12. The fallbacks' data undercounted; the lent sessions' guitar tracks excluded | P5's carried list; P1 |
| The gate: the Both rows; a blurred-DI fail needs the single-blur rows | section 5 |
| Drop "removes the old faults by construction"; the case against the network route on C′'s ceiling | section 2 |
| PR #525 B1: an undecided row is not a stop | `n2_code`: any undecided row that ran gives N2-between; N2-stem and N2-exposed only on a fail; tested |
| PR #525 B2: N2-exposed needs a human | N2-exposed goes to the user and stops |
| PR #525 B3: EGFxSet checked in code | `notes.json` records source, licence, trust; `assert_clear` on the 690 hashes in `notes` and when a bank opens; the bank refuses a changed file |
| PR #525 R1: refusals before heavy imports; `ready` refuses too | every command; tests for each refusal, `write_once` and the hash checks |
| PR #525 R2: missing files recorded; a broken run caught | `p1_ok`, `p3_ok`; NP-broken |
| PR #525 R3: one chord tolerance | `CHORD_S` = 50 ms for groups, matching and merge; tested on a chord spread over 45 ms |
| PR #525 R4: `nr-oracle` reads the true DI as rendered | `rebuild_dry(finish=…)`; every arm at −22.9 LUFS |
| PR #525 R5: the MIDI reader checked before stage 1, no download | `reader_check` in P3, part of `p3_ok` |
| PR #525 R6: no figures on development items | the probe stores timings only, labelled not evidence |
| PR #525 R7: P8's code | section 6, "What P8 must put in code" |
| PR #525 nits | skipped notes counted; the tab fallback avoids its chord-mates' strings; the attack on the onset; NP-gap with its count code; the per-item files written last; the −12 rival's failures counted |

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

## 11. Stage 1's declaration (P8, 2026-11-20; ledger `phase_nr_1`)

Declared after stage P ran (NP-ready; the raw hand-back is in the handover folder) and the replay's draw was hashed on
main (`preset-ladder` `phase_replay_draw`), before any stage-1 command runs. Code `learn/note_rebuild_s1.py`, tests
`tests/test_note_rebuild_s1.py` (pure) and the synth tests. Outputs under `PF/note-rebuild/stage1/`, each written
once. Every command refuses unless this checkout's `learn/note_rebuild*.py` equal main's and its `phase_nr*` keys equal
main's (`require_main`), and each refusal is tested.

**The gate, in code (`gate_refusal`, read from the replay's own report and main's ledger, never from a message).**
`clips`, `render`, `pick` and `score` refuse unless:
- the replay's `report.json` exists and was read from the picks hashed on main (`phase_replay_picks`);
- the replay's outcome is audited and recorded on main (`phase_replay_outcome`);
- its code is R-alone or R-dry-only (the dry-guitar row passed, through the combined blur or a single one, and the stem
  alone passed). Every other code (R-dry, R-stem, R-undecided, singles-triggered, incomplete) stops stage 1. A
  blurred-DI fail or undecided row reads singles-triggered until the single-blur rows are read, so the single-blur
  rows are always read before this route closes on a blur;
- when the outcome carries a Both-row note, the user's go is recorded on main (`phase_nr_1_both_go`).

**The steps.**

| # | Command | What | Before the gate? |
|---|---|---|---|
| 1 | `subset` | The replay's drawn GOAT parts that carry true notes (`carrying_subset`), each with its item, window, note file's sha256 and stage P's per-unit figures. Its sha256 goes into the ledger as `phase_nr_1_subset` **before `build` or any render** | yes (zero renders, no held-half value) |
| 2 | `build` | The three dry guitars per part (section 4), on the true DI section **as the replay renders it** (`note_replay.di_section`), finished by the blurred row's chain (`song_bank.measure`, then `average_balance` with the part's `others` by the replay's `others_for`), every arm at −22.9 LUFS; the figures against that DI beside | yes (CPU, zero renders) |
| 3 | `clips` | **The ear check** (the plan review's item 3): 4 seeded GOAT development items clear of the exclusion list, a 10-s window each; the true DI, `nr-plain` and `nr-level` through the clean and crunch class starts on the AC20, each render primed alone: 24 clips, 48 renders, guitar only. The user's verdict goes into the ledger as `phase_nr_1_ear` (`ok`, or `fault` with what was heard: then a declared revision first) | no |
| 4 | `render --shard k/3` | Each part's three arms through its 23 menu settings in the replay's position-check mode (`note_replay.render_menu`); each kept render's search-half J0 distance against the clean record with the dry guitar as the judge's DI (`note_replay.half_distance`); no held-half distance, no audio kept. Refuses without `phase_nr_1_ear` = ok on main | no |
| 5 | `pick` | Per arm and part the smallest search-half distance (`note_replay.pick_index`); its sha256 into the ledger as `phase_nr_1_picks` before `score` | no |
| 6 | `score` | Once. Per arm the parts' numbers (`note_replay.part_numbers` on the stored held-half scores), the GOAT row of G and I (`note_replay.summary`'s `goat`: GOAT items as clusters), `row_reading`; beside, **the replay's GOAT-alone Control, Blurred and blind rows recomputed on exactly the subset** from the replay's own distance files, each arm's share of the Blurred row's I, the label-free numbers, the Spearman with the true DI's distances, the windows J0 refused, and the breakdowns (alignment-F tertile, Strat or not, tab-matched share at 0.8, articulated share about its median, clean or crunch). The rows are saved (`report-rows.json`) before N1_TABLE's code is read (`report.json`) | no |

**One change to the onset step, found at P8's build (development reads, nothing saved).** On whole GOAT items, a note's
best DI attack within ±150 ms sits a median of 9 to 36 ms *before* the fine-aligned MIDI's onset on 7 of 8 items
checked (27 to 36 ms on the four longest), and on the six items with more than 100 onsets only 37% to 61% of onsets
have an attack within ±50 ms. The ±50 ms snap alone leaves many notes unmoved,
so stage 1 would not be the upper bound the review asked for. The oracle onset step is now two stages
(`coarse_offset`, then `refine_onsets`): one constant offset per window (the median, over onset groups, of the
steepest DI rise within ±150 ms when at least 3 dB), then the ±50 ms snap per group. On the first 10 subset parts the
window offsets are −45 to +11 ms (median about −31), and the envelope correlation with the true DI rises on 7 of 10. The
MIDI's notes land on real attacks (precision within ±50 ms 0.83 to 1.0 on 7 of 10 windows); the DI shows 1.2 to 3 times
as many rises as onset groups on 9 of 10 windows, 2.2 times even on an item aligned at F 0.96, so a rise count over-counts (releases, mutes) and is
not used as a measure. Both stages and their shifts are reported per part.

**The subset, hashed now (from stage P and the replay's draw, before the replay's `pick` or `score`).** 60 of the 72
drawn GOAT parts carry (60 items; 31 clean, 29 crunch; folds 16, 14, 15, 15); 7 have no fine-aligned MIDI and 5 fewer
than 8 notes. Declared in code (`DECLARED_SUBSET`): the replay's draw file sha256 `c0f834ad…f470` and the sorted part
keys' sha256 `6570fa70…dac9`; `subset` refuses any other (`subset_refusal`), and its file's sha256 then goes into the
ledger as `phase_nr_1_subset`. One carrying part (`item_169`, SW50R) has GOAT's alignment F of 0.0: it stays in as
declared and is read in the lowest tertile, and **every row is also read beside without it** (`without_alignment_f0`),
so its effect is visible either way.

**Renders (the replay's measured rates; the position check sets the mode).** One primed process a part and arm: 60 ×
3 × 24 = 4,320; each render primed alone: 8,280. At the ladder's 68 a minute on 3 processes, about 64 min or 2 h 2 min.
The clips: 48. At most 3 render processes, never beside a separation (`no_separation_beside`), the 31 GB disk guard,
`setopt no_bg_nice` and caffeinate, PIDs recorded at launch; monitoring by the executor.

**Stage 3's card rule, coded now (`blind_setting`, `n3_card_eligible`).** The blind menu setting on each card is a
seeded menu position other than Cen. A card is drawn only where the pick differs from Cen and from the blind setting:
an equal pair is a forced tie, which the sign test leaves out anyway; such parts are counted and reported.

**Stage 2 is declared in its own PR after N1-pass.** Its rows and table are coded (section 6). Its full declaration
needs facts that only its install and research can give: Basic Pitch's wheels and PyPI digests on Python 3.9.6, one
fixed backend, its minimum note length as installed, each dependency's licence, and the song-by-song overlap of its
published training lists with every source the ladder uses (the Cambridge sessions included). None of that is a
download before N1-pass, and the stem's lag is measured there.

**Stop rule.** One build, one read. Undecided goes to the user with each arm's share of the Blurred row's I; a
revision is declared first and read only on the revision pool (49 carrying cap1 parts on 33 GOAT items outside the
draw).

### 11a. Revised after PR #528's review (2026-11-20, before any stage-1 command runs; ledger `phase_nr_1_review`)

**The gate reads the single-blur outcome (B1).** When the replay's `report.json` reads singles-triggered, the deciding
outcome is `report-singles.json`'s (`deciding_outcome`), read only from the single-blur picks hashed on main
(`phase_replay_picks_singles`), with its own code and Both-row notes. `score`'s Blurred comparison row and "share of the
Blurred row's I" come from the dry guitar that outcome rests on (`comparison_dry`: the combined blur, or the passing
single blur, avg first when both pass, mild beside). Tested on both paths, go and stop.

**The audited code itself (R1).** Main's `phase_replay_outcome` must name exactly the deciding outcome's code (a dict's
`code`, or the code as a whole word in a string); an audit correction closes the gate.

**The ear check no longer blocks the night (R2).**
- `clips` needs only the declaration and the subset, not the replay's outcome (it reads only development items). It
  takes a render slot, so it waits for the replay's renders, and it never runs beside a separation. Every clip is set
  to −23 LUFS (loudness matched); a page is published privately for the user (since 2026-11-21 the regular card
  layout, section 11d).
- `render` refuses unless the automated pre-checks pass (`precheck_refusal`), on every dry guitar in `build` and on
  the clips. `pick` and `score` (not `render`) refuse without `phase_nr_1_ear` = ok: renders read nothing, and a heard
  fault discards them under a declared revision before any read.
- **The pre-checks (`PRECHECK`, fixed here):** no non-finite sample, and a peak at most 6 dB over the true DI's at the
  same loudness; each arm's global tuning within ±5 cents of the true DI's; the hiss floor (energy above 3 kHz in the
  20-ms frames where both the true DI and the arm are at least 30 dB under their own loudest, at least 5 such frames)
  at most 6 dB over the true DI's; in the crunch clip renders, bursts above 3 kHz (5-ms frames at least 12 dB over the
  100-ms running median, more than 30 ms from every onset) at most 0.5 a second over the true DI's render; and in
  `nr-plain`, each plain (non-articulated) onset group played alone, its 50-ms level, 90th less 10th percentile at
  most 3 dB.
- **Measured before fixing the rules (27 development windows, both arms; nothing saved):**
  - *Tuning:* the first draft read every arm 5 to 7 cents sharp. EGFxSet's notes sit about 4.5 cents sharp in their
    first 300 ms (the pick attack's glide; on 10 notes, mean +4.5 early, +0.8 at 0.3–2.3 s), and most notes in a part
    sound only their first few hundred ms. So **each sample is now retuned from its own early pitch** (its first 300
    ms from the attack, `Bank.own_cents`); P2's cents still gate wrong notes. After the change, none of the 54 dry guitars fails the ±5-cent check.
  - *Level spread:* the first draft counted onset groups begun before the window (their span collapses to a sample)
    and the declared articulation gains (dead −6, ghost −10, legato −6 dB): 6 to 10 dB. Plain plucks played alone:
    0.2 to 1.8 dB. The rule now measures exactly that; `nr-level` and `nr-oracle` also give a group begun before the
    window 0 dB and leave it out of their median (`MIN_SPAN_S`).
  - *Hiss floor:* the first draft took the true DI's gaps only, where a note still ringing in the arm read as hiss; it
    now takes frames quiet in both.
  - *Peak:* sparse windows at −22.9 LUFS peak over 1 in the true DI too, so the peak is judged against the true DI's.
  - With the rules as fixed, 2 of 54 dev dry guitars failed: item_150 `nr-plain`, level spread 3.5 dB; and item_102
    `nr-level`, hiss floor 9.4 dB over the true DI's, where the level gain lifts quiet notes and their residual hiss.
  - **The orchestrator's ruling (2026-11-20, before any result): fix the cause, not the threshold.** In the level-gain
    arms (`nr-level`, `nr-oracle`) the declared hiss removal above 3 kHz (`denoise_above`, the riff library's
    parameters) now runs again on the dry guitar after the level gain. The fallback, had item_102 still failed, was
    to waive the hiss check for those arms only, as a declared known confound on their rows; it was not needed.
  - **Re-run with the thresholds unchanged** (27 development windows, all three arms, 81 dry guitars; nothing saved):
    item_102's hiss floor is now +3.4 dB (`nr-level`) and +3.1 dB (`nr-oracle`) over the true DI's, inside the 6 dB
    rule. **1 of 81 fails:** item_150 `nr-plain`, plain-group level spread 3.5 dB against 3.0. It is not a clip item,
    so it blocks nothing; it is reported in the hand-back as a known spread.
  - **No threshold was tuned to pass a known item.** The rules were fixed after measuring what the checks measured on
    development items (the four flaws above), and not changed again after the item_102 and item_150 failures.
- **What a pre-check failure does (declared 2026-11-20 before `build`, PR #528's re-review).** Development items fail
  about 1 in 81, so among the subset's 180 dry guitars at least one failure is likely, and a single one must not stop
  the night. `render` is refused only on a failing clip check (the clips are what the user hears) or when more than
  10% of a deciding arm's parts (`nr-plain`, `nr-level`) fail, a systematic fault (`precheck_refusal`,
  `PRECHECK_MAX_SHARE`). `nr-oracle`'s failures never block. Otherwise render goes on, every failure is listed (in the
  render log and in the report), and `score` reads every row beside without the parts where a deciding arm fails
  (`without_precheck_fail`, one set for every row).
- The loudness step now converges (`at_lufs` repeats until within 0.01 LU: the −70 LUFS absolute gate made one step
  miss by 0.4 LU on the oracle's large gains).

**Beside rows (R3).** Every row is also read without the subset's 4 parts whose items fail their own MIDI reader check
(item_54, item_64, item_95, item_110; `without_reader_fail`), as it is without the alignment-F 0.0 part.

**R4** was already met: `test_row_reading_agrees_with_the_replays` (merged with PR #525) asserts the two readings agree
on a grid.

**Nits taken:** true-notes.json's file sha256 is pinned in `DECLARED_SUBSET`; `score` checks each replay distance file
against the replay's hashed picks (`dist_sha256`); a row with no interval reads N1-incomplete instead of crashing after
the rows are saved.

### 11b. Amended after `build` and the first `clips` attempt (2026-11-20, before any stage-1 render is read; ledger `phase_nr_1_amend`)

**The clips crashed on a code fault.** The plugin's renders are stereo, (samples, 2), and the burst check assumed mono.
`mono` now folds every render before a frame measure (`_frames_db`, `burst_rate`); tested on a stereo array. The six
clips written before the crash were moved aside (`note-rebuild-ear.failed-stereo-…`), not deleted; `clips` runs again
from the start.

**The peak check is now report-only, and it first caught a real fault.** `build` ran from main at 26e2b635 (60 parts
× 3 arms, 225 s; build.json sha256 `0e5c077c…4e3e`). Its pre-checks failed 48 of 180 dry guitars, `nr-plain` on 12
of 60 (8 of those on the peak rule, at most 6 dB over the true DI's peak at the same loudness), which would have
refused `render` under the 10% bar.

*The fault (found on the review's zero-score look at the extreme peaks, 2026-11-20).* Every extreme peak (+10.5 to
+16 dB) sat on the window's first or last sample, with no note struck near it and its 5-ms energy above 3 kHz 30 to
60 dB over the window's median: an edge click. A note begun before the window was cut mid-waveform at the first
sample (and one at the last), with no fade, and the finishing filters turned that step into a spike. **Fixed, with
half B untouched:** the dry guitar fades in over the window's first 10 ms (`EDGE_FADE_S`), which lie before the
trimmed timeline and outside both halves. Its end is never faded: `rebuild_dry` synthesises and finishes the guitar
100 ms past the window (`END_PAD_S`; the finishing filter is 4,096 taps, about 85 ms), so the end fade and the
filters' edge fall in the pad, and then trims back to the window. (A first draft faded the window's last 10 ms too;
half B runs to the window's end and is the search half on 27 of the 60 parts, so the pad was chosen instead.) Tested:
a note ringing across the end keeps its level there, and the start still fades. On items 94, 96 and 113 (in memory,
zero score) no end spike returns, and the last 50 ms sit at 0.9 to 1.0 of the true DI's level where a note rings
across. The faulty `build` output was moved aside to a dated folder (not deleted) and `build` runs again after this PR
merges.

*After the fix* (all 60 parts rebuilt in memory, zero score, nothing written): peaks over the true DI's have medians
+1.7 dB (`nr-plain`), +2.5 (`nr-level`), +3.7 (`nr-oracle`), at most +10.4. The peak flags fall to 4, 4 and 8 parts.
Every remaining flag sits on a plain note or chord struck within the 80 ms before it, on sparse windows where the
rebuilt guitar's crest factor is 6 to 9 dB above the true DI's (measured in memory; the rerun build restates it as
6.1 to 10.1 dB on the flagged parts, section 11d): the re-synthesis' sharper attack, not a glitch.

*Why it stays report-only.* The rule was meant to catch clipping and glitches. At the measure's −22.9 LUFS, peaks
above full scale are normal (8 of the 60 true DIs the replay itself renders exceed 1.0, up to 2.02), and the
remaining flags are real attacks. Kept blocking, it would still refuse `render` (`nr-plain`: 4 peak flags and 4
other failures, 8 of 60). So the peak is a report-only flag (`flagged`), and every row is also read beside without
the parts where a deciding arm carries it (`without_peak_flag`). **The sharper attack is a declared confound of the
N1 reading** (`PEAK_CONFOUND`, `confound_sharper_attack` in the report): the attack sets how hard the amp is driven,
so on N1-fail or N1-between the read and its audit compare each arm's full row with its `without_peak_flag` row, and
a row that reads differently without the flagged parts is said so before any route decision.

The blocking checks are unchanged: non-finite samples, tuning, hiss floor, plain-group level spread, and the clips'
burst check. build.json is written once, so `render` re-derives each stored record's blocking failures under the
amended rule (`blocking_why`). With the edge fix (in memory): 4, 3 and 3 parts fail a blocking check, under the 10%
bar. No threshold was changed.
### 11c. Any failing Both row asks the user (2026-11-20, after the replay's audited outcome R-alone; ledger `phase_nr_1_both_gate`)

Plan section 5 says that if a Both row of the replay (the stem and the blurred DI together) fails, the user is asked
before stage 1. The gate checked only the Both-row notes of the cell the outcome rests on (R-alone's both-alone), so
the replay's failing both-full (+0.092 [−0.030, +0.214]) would not have stopped it. `gate_refusal` now also refuses
whenever any Both row in the deciding reports reads "fails" (`failed_both_rows`: both-alone, both-full and the
single-blur avg-both-*, mild-both-*), until the user's go is recorded on main as `phase_nr_1_both_go`. Undecided Both
rows stay with the outcome's notes. `render`, `pick` and `score` refuse until then; `build` and `clips` render no
score and are unaffected. Tested on the replay's case and the single-blur path.

### 11d. The user's go on stage 1 (2026-11-21; ledger `phase_nr_1_both_go`)

The user was asked on 2026-11-21 at 12:48 UTC (the replay's failing both-full row, +0.092 [−0.030, +0.214], plan
section 5): "Go for the rebuild's next stage? It's about 1 to 2 hours of renders. Its plan requires asking you,
because the first test failed in the toughest case, a blurred guitar with other guitars in the mix. I suggest yes: it
tests whether a guitar rebuilt from the notes alone works where the guitar plays alone." The user's "Agree." came
later, in reply to a five-item list that included "Rebuild's next stage, about 1 to 2 hours of renders: suggest go";
it answers that item, so stage 1 goes ahead. `gate_refusal` reads go once this is on main; `render` may run. `pick`
and `score` still wait for the ear check's verdict, recorded from the answers stored on the ear page
(`phase_nr_1_ear`). Three records ride with it:
- the ear page moves to the regular card layout on the user's word, in the same message: "Regarding the listening
  page, use the regular page structure used so far instead inventing a new one (any recording has it own buttons so I
  don't have to remember everything or go back and forth when answering)". Each recording gets its own card with its
  play and answer buttons; the clips and the declared reading (`ok`, or `fault` with what was heard) stay the same;
  the page's code comes in its own PR (section 11e);
- the sharper-attack confound's text (`PEAK_CONFOUND`) now gives the rerun build's measured crest figure, 6.1 to
  10.1 dB above the true DI's on the flagged parts (it said "6 to 9 dB", an in-memory figure); the reading is
  unchanged;
- Direction 2 (gear families) is parked by the user, 2026-11-21
  ([family-class-checks-results.md](family-class-checks-results.md)).

### 11e. The ear check's page in the regular card layout (2026-11-21, the user's ask; ledger `phase_nr_1_ear_page`)

The user asked that the ear check use the regular listening page, with each recording's own buttons, so nothing has
to be remembered or revisited. `learn/note_rebuild_ear.py` builds it from the same 24 clips (`clips`' index, each
checked against its sha256), on `ear_vreal`'s player and `c1a_ear`'s Artifact page: one numbered card per window and
preset (8 cards), the recorded DI and both rebuilt guitars playing in a loop and switching at the same place, and on
the same card, for each rebuilt guitar, "sounds real", each fault heard (hiss, out of tune, clicks or crackle, one note
much louder, timing), or "can't judge", with an optional note. The clips are folded to mono (the plugin's two channels
differ by at most 3e-5) and AAC-encoded at 256 kbps, as the regular pages are. Answers are kept in the page's db
(`answers/<build>`) and Export.

The declared reading is unchanged (`ok`, or `fault` with what was heard). `phase_nr_1_ear` is recorded from the stored
answers by `note_rebuild_ear read` (`ear_verdict`): "fault" when any card marks a fault on either rebuilt guitar (each
listed with the card's note), else "incomplete" when any version is unanswered, else "undecided" when any version is
"can't judge" (the cards listed; it goes to the orchestrator and the user, and `phase_nr_1_ear` is not recorded as ok
from it), else "ok", every version on every card heard as real; notes on cards without a fault are listed for the
orchestrator before the verdict is recorded. A chat "ok" is not the record.

## 12. The redo: notes transcribed from the DI, read as the `fs-notes` row (2026-11-22; ledger `phase_nr_1_redo`)

Declared 2026-11-22, before anything in it runs, from the redo plan approved after an independent review (changes
needed; every blocking and required item taken) and its re-review (approve with changes; every required item and nit
taken). Code: `learn/note_transcribe.py` (the transcription, the checks, the builds, the ear clips), `learn/bp_run.py`
(Basic Pitch in its own venv), `learn/scratch_notes.py` (the row), the redo's arms in `learn/note_rebuild.py`, the
redo's page in `learn/note_rebuild_ear.py`. Tests: `tests/test_note_transcribe.py`, `tests/test_note_rebuild_redo.py`
(pure), `tests/test_note_rebuild_redo_synth.py` (numpy), `tests/test_scratch_notes.py`. The row itself is declared in
[scratch-search-plan.md section 10](scratch-search-plan.md#10-the-fs-notes-row-2026-11-22-ledger-phase_scratch_notes).
Every number is by the score unless it says "by ear".

**The question.** The flagged song-time search (licensed by F-both, held by the user) needs a dry guitar the product
can make. Row (c) used a blurred copy of the true DI, which the product never has. With one transcriber's notes read
from the cleanest input there is, does a guitar re-played from single recorded notes drive the search as well as that
blurred DI? A pass ships nothing: the notes, levels, mutes, sustain and onsets all come from the true DI. The
product-real test is the next row, the stem-notes row (every input read from the `xlnoG@-3` stem), under its own
declaration. The full-mix case (stage 2's `B-full`) is deferred, not replaced.

**Said plainly:** by the row's own power, a match on clean needs a mean paired difference near −0.02 (answer) or +0.02
(shrunk). `FN-undecided` or `FN-crunch` is the probable outcome; the recommendation for each is declared now
(scratch-search-plan section 10).

### 12a. The user's three answers (2026-11-22, by AskUserQuestion)

| # | The user's answer | Recorded as |
|---|---|---|
| 1 | Drop stage 1's 60-part rerun. The 47-part `fs-notes` row decides. The old renders are moved aside unread | **`N1_TABLE` is retired unissued.** `note_rebuild_s1`'s commands refuse for good (`retired_refusal`) |
| 2 | One rebuilt guitar, `tr-di`, plus a zero-render `tr-plain` side figure on levels for the later stem-notes row | Section 12d |
| 3 | The deciding set is BKS+GOAT (40 parts). The 7 panel parts are read beside and cannot swing the result | **The user's explicit exception** to the from-scratch search's rule "the user's pool: never read on fewer sets", for `fs-notes` only |

**No note-route read of any part has happened.** Stage 1's 4,320 renders were never picked or scored, so section 7's
"revisions on fresh parts" rule is not breached. Retiring stage 1 loses its larger GOAT sample (60 parts), its
alignment-F breakdowns, a cheaper read (1,440 renders against about 13,450) and stage 2's three-row ladder.

**Stage 1's renders.** `note_transcribe set-aside` hashes `stage1/di` first, checks `stage1/dist` against the render
hand-back's list hash, then moves `dist`, `di` and `build.json` (never deleted, never read) to
`stage1.set-aside-20261122/`, with a note: "unread: no pick, no score". `subset.json` stays. The folder joins the
protect-in-cleanup list. The proof that the old arms' code is unchanged needs no result: a test rebuilds two parts'
stage-1 dry guitars in memory and matches `build.json`'s sha256 (it passes at declaration), and another holds every
stage-1 function byte for byte against main at `1f13b563`.

**How it differs from what failed.**

| The GOAT-annotation rebuild (failed by ear) | The redo |
|---|---|
| Notes from GOAT's aligned MIDI and tab (a median 58% of onsets); GOAT parts only | Notes transcribed from the DI (Basic Pitch); BKS and the panel too |
| Bends played plain | Bends from the transcriber's bend track |
| Each note muted 20 ms after its notated note-off | A ring rule chosen on development windows; one sustain tilt per window |
| One sample per string and fret | A re-struck pitch never reuses its last sample |
| No check compared content with the DI | Six content checks against the DI before anyone listens or renders |
| 215 refused judge windows found after the renders | The judge's own refusal dry-run per part at zero renders (`judge-accepts`) |
| Ear page: "sounds real" and five signal faults | Adds missing notes, chords as single notes, notes cut short, extra or wrong notes |
| A pick among 23 menu settings on 60 GOAT parts | A from-scratch search on the 47 Plan-1 parts, paired per part against row (c) |

### 12b. Basic Pitch: the install and its gate

- **Package and model:** `basic-pitch` 0.4.0 (Apache-2.0); its weights ship in the wheel (`nmp.onnx`). The backend is
  ONNX on the CPU (`onnxruntime` 1.19.2, MIT): with only onnxruntime installed the package runs the CPU provider.
- **Venv:** a new `~/ndsp-presets/tools/basic-pitch-venv` from `/usr/bin/python3` (3.9.6). pip is first upgraded by
  a hashed pin. The lock is made by `pip install --dry-run --ignore-installed --only-binary :all: --report` over
  basic-pitch's own requirement list for this platform without `coremltools` (with pretty_midi 0.2.11.post0 and
  mir_eval 0.8.2, the versions with wheels), plus onnxruntime; the basic-pitch wheel is added. The install is
  `--require-hashes --only-binary :all: --no-deps`. A package with no wheel stops the install (the declared sdist
  build is its own step). The install refuses under 32 GB free.
- **Manifest:** every file's name, size and sha256; the lock's and the model's sha256; `resolve.json`; the Python
  version; the installed size; the approval; the date; the MedleyDB index's sha256 (section 12f).
- **Runner:** `bp_run.py` runs under the venv's interpreter with `-I`, called by `note_transcribe`. It passes the
  `.onnx` path explicitly, replaces the package's session with one of one intra-op and one inter-op thread, and asserts
  the model type is ONNX and the providers are exactly the CPU's. Nothing in the main `.venv` or on CI imports Basic
  Pitch.
- **Fallback that keeps the design:** if ONNX does not load or repeat on 3.9.6, Python 3.11 (a declared download)
  with onnxruntime 1.19.2's cp311 macOS universal2 wheel (16,779,187 bytes, sha256
  `d863e8acdc7232d705d49e41087e10b274c42f09e259016a46f32c34e06dc4fd`, pinned in code as `ONNXRUNTIME_CP311`;
  `install --interpreter` takes it) and the same `nmp.onnx` by sha256. Every note file comes from one install.
- **The install gate** (`install-gate`; all must hold, else the fallback, else stop): repeatable (four development
  windows, three runs each, two in one process and one fresh, identical events); known notes (ten made-up lists played
  from the note bank, scales, chords of 3 to 6 notes, a let-ring arpeggio and a bend: pooled note F at least 0.90,
  onset within 50 ms, same pitch; each list reported); the seconds per 10-s window, measured.
- **Each note file names the install's lock and model sha256;** `build` refuses a file whose pair is not the
  install's (and, once the hash PR merges, main's `phase_nr_1_redo_install`'s). That key holds the lock's and the
  model's sha256 and the install gate's and the calibration's file sha256; `search` checks all four.

### 12c. The transcriber's settings and the clean-up (frozen)

| Setting | Value |
|---|---|
| Input | The part's raw DI section with up to 1.0 s of the file either side; mono; 48 kHz to 22.05 kHz by `resample_poly(x, 147, 320)`; peak at −1 dBFS; float32 WAV |
| Thresholds | onset 0.5, frame 0.3 (the defaults) |
| Minimum note length | 58 ms (the default, 127.7 ms, drops fast notes) |
| Frequency range | 60 Hz to 1,400 Hz |
| Melodia trick, bends per note | on, on |
| Kept | note events (start, end, pitch, amplitude, bend track), times to 0.1 ms |
| Clean-up | MIDI 36 to 88; below MIDI 38 an octave up (counted); a pitch struck twice within 30 ms merged; at most six at once |
| Timing | `coarse_offset`, then the onset snap at ±20 ms (a rise of 3 dB); stage 1's ±50 ms could snap a note to its neighbour |

A setting changes after the install gate only by a reviewed amendment, before any of the 47 parts is transcribed.

### 12d. The rebuilt guitars: `tr-di` and `tr-plain`

`note_rebuild.rebuild_redo` and `synthesise_redo`, added after the stage-1 code without changing it.

| Part | Rule |
|---|---|
| Note ends | A note ends when its string is plucked again (10-ms fade), at a mute in the DI (its 20-ms level falls 12 dB or more inside 60 ms, from a frame where the DI plays: a 30-ms fade on every note sounding), or at its sample's end. The transcriber's note-off: `ring-on` (it never cuts) or `ring-soft` (it starts a 150-ms release), chosen on the 27 development windows by the higher median `envelope_corr`, `ring-soft` within 0.02 |
| Strings | No tab: the lowest fret on a free string that is not still ringing, else the lowest fret |
| Sustain | One tilt per window: over onset groups with no other onset for 600 ms, the level at 300–500 ms against 0–50 ms, the DI's less the plain rebuild's; the median in dB per second, within ±12 dB/s and at most +12 dB on any note; under 3 such groups, none (reported) |
| Bends | The bend track (thirds of a semitone, 11.6-ms frames), a 3-frame median, applied by variable-rate resampling where a bend of one step or more lasts five frames; within ±3 semitones; not while another note within 2 semitones sounds |
| Variety | A pitch struck again within 2.0 s whose placed sample is the one it last played takes the next source in a fixed order: the placed string and fret; the same pitch on another free string; the placed string's neighbours a semitone either side, retuned. No randomness |
| Levels | `tr-di`: each onset group's level from the DI (`oracle_gains`); chords at 1/√k. `tr-plain`: none |
| Unchanged | Retuning; the hiss removal above 3 kHz (again after `tr-di`'s levels); the edge fade and end pad; the finish (`song_bank.measure`, `average_balance` with the part's others, as avg+mild); −22.9 LUFS |

`tr-plain` is never rendered and never on the ear page. Its content checks and figures sit beside `tr-di`'s, to show
what the stem-notes row will face on levels.

### 12e. The content checks against the DI (zero renders)

| Check | Compares | Passes when, per part | Gates |
|---|---|---|---|
| `annotated-found` | the notes with GOAT's aligned notes, both after the onset steps | on the development windows in the top alignment-F tertile whose own annotation lands on a DI rise for 90% of its notes: median recall (same pitch, onset within 50 ms) at least 0.85, no window under 0.75. Reported on the row's GOAT parts | the transcriber's settings (not a row refusal) |
| `onsets-found` | the note onsets with the DI's attacks (rise peaks of the calibrated level, merged within 50 ms, where the DI plays) | at least 0.90 of the attacks have an onset within 30 ms | the notes |
| `playing-covered` | the transcriber's own note spans with the DI's playing frames (J0's middle frame size) | a note sounds in at least 95% of the playing frames and in at most 10% of the rest | the notes |
| `judge-accepts` | the finished `tr-di` with the judge and the true DI | (i) J0 does not refuse on the search half, `tr-di` as DI and render, against the stem zeroed outside it; (ii) on each half and frame size, `tr-di`'s pause share at most the true DI's + 0.05; (iii) no stretch over 250 ms where the DI plays and `tr-di` is 40 dB under its loudest | the audio |
| `ring-kept` | the finished `tr-di` with the DI | (i) over frames where the DI plays 600 ms or more after the last onset, the median of `tr-di`'s level less the DI's (each against its own level in the 50 ms after that onset) within ±3 dB, not measured under 20 frames; (ii) `envelope_corr` at least 0.80 | the audio |
| `chords-kept` | Basic Pitch again on `tr-di`, with the DI's notes | note F at least 0.85; recall of notes in groups of 3 or more at least 0.85 (parts with 5 such notes); the pitch-class cosine reported only | the audio |

- **What a failure does.** An ear-page item failing any check: no page until fixed. A row part failing a blocking
  check (all but `annotated-found`) is refused. 3 or more refused of the 40 deciding parts stop the row before any
  render, and so does any ear item failing (`search` refuses on either); a panel refusal is listed and stops nothing.
  `annotated-found` gates the transcriber's settings: the calibration does not pass unless it does (a failure, or no
  window to read it on, stops before step 5 for a declared amendment).
- **The note checks are calibrated first (step 3)** on the 27 development windows' DI transcriptions: the declared
  pass rate is at least 25 of 27 windows for each check. The rise level is the lowest of 6, 9 and 12 dB that holds
  both bars and whose precision on the known lists is at least 95%; its precision against the annotated onsets of the
  top-tertile windows is reported. A missed bar is amended by declaration before step 5 (calibration, not the one
  fix).
- **The checks' own test (once, nothing saved as evidence):** avg+mild, the bar's own guitar, must pass every audio
  check on the 27 windows; the true DI through the same finish must pass (a code check); each clip the user rejected
  must fail a check named for it in `phase_nr_1_ear_old`, written from the user's words before the checks run (the
  default: `onsets-found` or `playing-covered`). An expected failure that does not happen is a blind spot: to the
  orchestrator, and a threshold changes only by one declared amendment that keeps avg+mild passing.
- **Beside, never gating:** crest factor, log-mel distance, energy above 2 kHz, mask agreement, pitch-class cosine.

### 12f. Basic Pitch's training data against our parts

| Source | In its training? | Our parts | Reading |
|---|---|---|---|
| GuitarSet; MAESTRO, Slakh; iKala | yes | none | — |
| MedleyDB's pitch-tracking subset (103 stems) | train | the panel: 4 of 7 parts on 2 DI files, Aimee Norwich "Flying" (3) and Big Troubles "Phantom" (1); the index holds other stems of the same songs | beside |
| Cambridge-MT sessions | no | BKS (16 parts); the panel's The Laminar Flow "Headspace" (3) | clean |
| GOAT (2025) | no, it postdates Basic Pitch | 24 parts; every development item (disjoint from the row) | clean |
| EGFxSet (the note bank) | no | — | clean |

The panel is 2 MedleyDB DI files and 1 Cambridge DI file. `note_transcribe.transcriber_overlap_songs` rebuilds the
overlap song by song from mirdata's `medleydb_pitch` index (its sha256 in the manifest), where
`note_rebuild.transcriber_overlap` marked the whole panel at set level.

### 12g. The ear page (regular card layout)

| Item | Declared |
|---|---|
| Folder | New: `listening/note-rebuild-ear-page-2`, clips in `note-rebuild-ear-2`, every file written once. The old page and its key.json are never touched (its `page` command now refuses to overwrite) |
| Items | 8 GOAT development items clear of the exclusion list: the 4 the user heard, at the same windows, and 4 new, one of each kind |
| Kinds, from the DI's transcription | chord-led (half or more of the onset groups hold 3 or more notes); single-note (80% or more hold one note, and no bend); bends (3 or more bent notes); let-ring (half or more are single notes still sounding 100 ms into the next onset). In a seeded order, each item fills the first kind it shows that is still open; its window is the 10 s with the most notes on a 5-s grid |
| Cards | 13: each item through the clean class start on the AC20; the 4 new items again through the crunch start; 1 hidden control (the true DI through the same finish, labelled "Rebuilt") on a seeded item's clean window; the cards in a seeded order |
| On a card | Recorded DI and Rebuilt, looping, switching at the same place; −23 LUFS; mono; AAC 256 kbps |
| Buttons | "Same notes and timing (the guitar's own sound may differ)"; content faults: missing notes, chords played as single notes, notes cut short, extra or wrong notes; signal faults: hiss, out of tune, clicks or crackle, one note much louder, timing off; "can't judge"; a note |
| Answers | the page's db (`answers/<build>`) and Export; the verdict read by `redo_verdict` from the stored answers, never from chat, into `phase_nr_1_redo_ear` |
| Built only when | every item passes every content check |
| Renders | 13 cards × 2 versions, each primed alone: 52 |

| Stored answers (the first that holds) | Verdict | What happens |
|---|---|---|
| a content fault on any real card | `fault-content` | stops the step; search renders set aside unread; each faulty card laid beside its checks (a check that passed a heard fault is a blind spot, fixed first); a second build needs a declared revision |
| signal faults on 3 or more real cards | `fault-signal` | stops the step; a declared fix first |
| a card unanswered | `incomplete` | nothing recorded |
| signal faults on 1 or 2 real cards; any "can't judge"; any fault on the control card | `ask` | to the user, with the cards, the notes and a recommendation |
| "Same notes and timing" on all 12 real cards | `ok` | the row's `answers`, `score` and `read` may run |

**The old page's verdict goes under its own key, `phase_nr_1_ear_old`, with the user's words beside it**, never into
`phase_nr_1_ear`: the old page has no content buttons, so its stored answers could read "ok", and that key unlocked
stage 1's `pick` and `score`. If the stored read and the user's words disagree, the user is asked.

### 12h. The order, the costs and the stop rules

| # | Step | Renders | Waits for |
|---|---|---|---|
| 1 | This declaration: both plan sections, the code, the tests | 0 | an independent review, goal check included |
| 2 | `set-aside`; the old page's read into `phase_nr_1_ear_old`, with which check must fail which rejected clip | 0 | 1 |
| 3 | `install`; `install-gate`; `calibrate` (the note checks on 25 of 27 windows, the checks' test, the ring variant) | 0 | 2 |
| 4 | `scratch_notes score-check` and `search-check` on two parts of row (c) | about 64 | 1 |
| 5 | `transcribe` the 47 parts and the 8 ear items; the note checks | 0 | 3 |
| 6 | `build` `tr-di` and `tr-plain`; the audio checks; `stem-preview` | 0 | 5 |
| 7 | Hash PR: `phase_nr_1_redo_install`, `phase_nr_1_redo_notes`, `phase_scratch_notes_dry` | 0 | 6, under 3 of the 40 refused |
| 8 | `clips` and the page; the user listens | 52 | 6, every ear item passing |
| 9 | `scratch_notes search`, 3 shards (it may run while the user listens; a heard fault sets it aside unread) | about 12,400 | 4 and 7 |
| 10 | `answers`; hash PR (`phase_scratch_notes_answers`) | 0 | 9, and the ear verdict `ok` |
| 11 | `score`, then `read`, once | 940 | 10 |
| 12 | An independent audit (its own recompute from the score files), then the results PR (`phase_scratch_notes_outcome`) | 0 | 11 |

About 13,450 renders, about 2 hours on 3 processes at row (b)'s measured rate; Basic Pitch's speed is measured at the
install gate. No training, separation or MPS job.

**Stop rules.** The content checks fail on 3 or more of the 40 deciding parts, or on any ear item: nothing is
rendered; one declared fix; a second failure goes to the user with "stop" recommended. An ear content fault stops the
step before any read; a second one goes to the user the same way. One build, one read; no rerun on these parts under
any code. After this row, at most two more reads (the stem-notes row, then a blind sitting) before a product decision.

### 12i. Filled in at declaration (the plan left these open; each is in code and tested)

- **The 27 development windows:** every GOAT item clear of the exclusion list with fine-aligned MIDI and a full window
  at the probe's start (30 s into items over 45 s, else 1 s), in item order. This rule gives exactly 27 (tested on the
  stored data), the set stage 1's declaration measured on.
- **Steps 5 and 6 read the install's own records** (the manifest, `install-gate.json`, `calibration.json`, each
  written once) because their hashes reach main only with the hash PR at step 7; from step 9 on, the row checks
  main's keys.
- **A mute** is only detected from a frame where the DI plays (within 40 dB of its loudest 20-ms frame), and the note
  ends at the end of the first frame 12 dB down.
- **"Lands on a DI rise"** (for `annotated-found`'s windows) uses the snap's own rule: a rise of 3 dB within ±20 ms.
- **Pooled note F** over the ten known lists decides the install gate's known-notes bar; each list is reported.
- **The positive control's avg+mild** on development windows draws its other guitars from the replay's non-GOAT
  parts, seeded per window.
- **Ear items have no stem:** `judge-accepts` there is clauses (ii) and (iii).
- **The bottleneck's difference interval** combines the two halves' half-widths in quadrature.
- **Variety:** the next source is taken only when the placing rule gives the sample the pitch last played (a string
  still ringing already moves it).
- **Stage 1's commands:** `subset`, `build` and `clips` refuse for good too, beside `render`, `pick` and `score`, so
  nothing set aside can be rebuilt; `gate` still prints.
- **An ear item "fails a check"** when it fails a blocking check (`annotated-found` is a set-level bar).
- **The search check** stops `run_part` after step 1 (about 11 renders a part). **The start reference** renders the
  settings step 1 evaluates first, C1a's canon applied, which equal `sx1(start)` on all 47 parts.
- **mirdata's index** is placed by a declared download before `install`, which records its sha256; the panel's
  beside split uses the MedleyDB file naming, the index only confirms the overlap.
- **A package with no wheel** stops `install`; the declared sdist build is its own step.
- **Seeds:** the ear items' order 20261401, the control card and the cards' order 20261402, the development blur
  20261403 (grepped: unused).

### 12j. What it can't say

- Anything about notes taken from a stem or a song; this row's notes, levels and mutes come from the true DI.
- Which of transcriber and synthesis caused a fail, beyond the declared descriptive split.
- Anything with other guitars in the mix, on released mixes, or about effects; anything by ear about presets.
- Whether a pass would survive another note bank or another transcriber.
- The panel: read beside; 4 of its 7 parts are songs the transcriber trained on (other stems).
- Whether the transcriber finds every note where no truth exists; chords are checked on made-up lists and by round
  trip only.
- One listener stands behind the ear check.
- Names, grepped against the docs, the ledger, `learn/` and `tests/` before use: `fs-notes`, `tr-di`, `tr-plain`,
  `ring-on`, `ring-soft`, `stem-notes`, `D_notes`, `FN-` and its codes, `FN_TABLE`, `fn_code`, `paired_reading`,
  `redo_verdict`, `CONTENT` and the six check names, `fault-content`, `fault-signal`, `lean-go`, `lean-stop`,
  `note-rebuild-ear-page-2`, `note-rebuild-ear-2`, `phase_nr_1_redo*`, `phase_nr_1_ear_old`, `phase_scratch_notes*`.

### 12k. The old page's read and the expected failures (step 2, 2026-11-22; ledger `phase_nr_1_ear_old`)

The old ear page's stored answers (build `b1efe3513bca`, the page's Artifact db, exported to
`PF/note-rebuild/ear-old-export/`, sha256 `e27df9f2…faafa`) were read by the declared method, `note_rebuild_ear read`
(`ear_verdict`, unchanged code). **The stored read is "incomplete"**: 5 of 8 cards answered, no fault button marked
(the old page had no content buttons), cards 1 to 4 "can't judge" on both rebuilt guitars, card 5 "sounds real" on
both, cards 6 to 8 unanswered. It is recorded under `phase_nr_1_ear_old` only, never `phase_nr_1_ear`.

The user's words, quoted from the stored notes:

| Card | Item, preset | The user's note |
|---|---|---|
| 1 | item_102, clean | "Many notes are missing from A and B (there's a bend in the recording which is simply missing, only notes before and after it exist)" |
| 2 | item_102, crunch | "Same comment as Recording 1" |
| 3 | item_160, clean | "Notes sound cut (short, no width), not like a real guitar playing" |
| 4 | item_160, crunch | "Same comment as Recording 3" |
| 5 | item_46, clean | "Both sound real but missing notes. R has chords while A and B only contain single notes playing" |

The stored read (incomplete, not ok) and the words (content faults, no card heard as right) do not disagree, so
nothing goes to the user on this.

**Which check must fail which rejected clip**, written from the words before any check runs on them. A clip is one old
dry guitar (item and arm; the preset does not change it). Each must fail at least one of its checks in `calibrate`'s
negative control, or it is a blind spot:

| Clips | The words | Must fail one of |
|---|---|---|
| item_102, `nr-plain` and `nr-level` | many notes missing; a bend missing | `onsets-found`, `playing-covered` (the plan's default) |
| item_160, `nr-plain` and `nr-level` | notes cut short, no width | `ring-kept`, `playing-covered` |
| item_46, `nr-plain` and `nr-level` | missing notes; chords played as single notes | `onsets-found`, `playing-covered` |

**The control holds only when all 6 clips fail one of their checks;** any clip that passes them all is a blind
spot. "Chords played as single notes" (card 5) is not testable by any of the six checks here: `negative_control`
measures `chords-kept` against the old clip's own notes, not the DI, so chords the old tab lacked leave it
nothing to recall (the transcriber's chord recall is covered only by the install gate's known notes).
`chords-kept` is reported for item_46, not counted. item_57 (cards 7 and 8) is unanswered and carries no words, so it is not in the table. The plan spoke of "the four
clips the user rejected"; the stored answers hold words on 5 cards over 3 items, each about both rebuilt guitars, so
the table holds the 6 dry guitars the words describe.

### 12l. The known-notes test amended (2026-11-22, the user's choice; ledger `phase_nr_1_redo_known_amend`)

**The first install gate failed on its known notes.** It ran once from main at `cda93caf` on `/usr/bin/python3` 3.9.6.
ONNX on the CPU loaded, so the fallback was not needed.
- Repeatable: passed (4 windows, 3 runs each, identical).
- Timing: 1.64 s of transcription per 10-s window.
- Known notes: **pooled note F 0.535** against the 0.90 bar. Recall was 0.95 (246 of 259 true notes) and precision
  0.37 (246 of 660 found).
- `install-gate.json` sha256 `0cb7b257c4cd0c9f813636300c979af94e8dca84a9fa81bb39736b81bbd5890e` (lock
  `ea700e7e…1de1`, model `2c3c1d14…a0ec`). Its raw events and inputs, `work/install-gate/` (44 files in
  `one-process/`, `fresh/` and `known/`), have the listing sha256 `24e7850fa16287b094fb1a0cb0dc7db08861d3669f6e5eb7b8b00ebe35e42329` (`listing_sha`, the
  `shasum -a 256` lines sorted by path).

**The cause, read from the raw events (nothing tuned):** the test's audio did not match its truth. `known_audio`
played the lists with `ring-on`, so every note rang on to its 5-s sample while the truth ended it at its note-off.
The transcriber then found those still-ringing pitches again at each later pluck. Faint notes an octave or a twelfth
above a played note (about 0.3 in amplitude against 0.7) also count as extra notes. Re-finding a pitch is also partly
the transcriber's own behaviour: in `let-ring-arpeggio` it re-finds pitches that are legitimately still ringing inside
their declared span, and real let-ring DIs will show the same.

**The user's choice (2026-11-22):** fix the test and run the gate once more.
- Each known note is now cut at its declared note-off (`synthesise_redo(..., cut=True)`, a 10-ms fade ending there).
  `tr-di` and `tr-plain` never pass it, so their synthesis is unchanged. A test holds that the default call reproduces
  the failed gate's stored `scale-c-major` input sample for sample.
- No Basic Pitch setting, bar or threshold changes, and no clean-up rule is added. If the faint octave and twelfth
  notes still fail precision, that goes back to the user with a reviewed clean-up rule; it is not decided here.
- **Before the one rerun, `install-gate.json` and the whole `work/install-gate/` folder move aside together, never
  deleted.** `install-gate` now refuses while either exists, so a rerun cannot overwrite a run's evidence. The rerun
  waits for this amendment on main.

**Known before the rerun (from the review; no bar or setting changed):**
- **One truth note is never played.** The first A chord of `chords-six` holds six notes, but the placing rule fills
  strings 1 to 5 low to high and leaves no string for its 69. So 35 of 36 notes sound, with or without `cut`. The effect
  on pooled F is at most about 0.002 either way; changing the voicing would change the truth list.
- **The bend list releases its bends early.** Its notes last 1.5 s, but their bend tracks last about 1.14 s, so each
  note drops back to its base pitch about 0.36 s before its note-off. In the failed run the transcriber re-found the base
  pitch there (about 3 extra notes that `cut` does not remove). Splitting a bend into separate notes is the
  transcriber's own behaviour, and real DIs will show it too.
- **The rerun will probably still fail on precision.** The reviewer sorted the failed run's 414 extra notes: 268 come
  from notes ringing past their declared off (removed by `cut`), and about 146 would remain (82 harmonics inside a note's
  sound, 48 pitches re-found while still declared sounding, 16 others). With recall about the same, that projects a
  pooled F of about 0.75 to 0.78. **This is a projection from the stored events, not a measurement.**
- **The calibration's rise precision misses its 0.95 bar with either audio.** On the real bank, pooled over the ten
  lists: 6 dB 0.193 (old audio) and 0.258 (amended), 9 dB 0.544 and 0.664, 12 dB 0.907 and 0.937. Using the amended
  audio makes the figure easier to pass, but no level reaches 0.95, so `calibration_pick` will return None and the
  calibration will need its declared amendment whatever this change does.

### 12m. The second amendment: measure first (2026-11-22, the user's decision; ledger `phase_nr_1_redo_calib_amend`)

Declared 2026-11-22, before anything in it runs, from the amendment plan approved by its independent review after
three rounds. Code: `learn/note_truth.py` (the truth), `learn/note_attacks.py` and `learn/attack_run.py` (the
detector), `learn/note_versions.py` (the read), the loudness option in `learn/note_rebuild.py`, and the wiring and
five new commands in `learn/note_transcribe.py`. Tests: `tests/test_note_truth.py`, `tests/test_note_attacks.py`,
`tests/test_note_versions.py` and additions to the redo's test files. Nothing here has run.

**Where it starts.** The gate's rerun read F 0.751: every true note found (259 of 259), 431 notes in all. Of the 172
extra notes, 126 are harmonics (median amplitude 0.36 against 0.72 for real notes), 31 re-find a pitch still sounding,
and 15 are others. The review found that no amplitude floor separates them (the best reaches F 0.895 and costs chord
notes), that the drafted clean-up rule's best case only just reaches 0.90, and that the rebuild plays every note of an
onset group at the same level, so a ghost sounds as loud as a real note.

**The user's decision (2026-11-22, by AskUserQuestion): "Measure first".**

| Term, as put to the user | Where it lands |
|---|---|
| With no renders, rebuild the dry guitar four ways and compare each with the real DI | The note-versions read |
| If loudness alone lands near the hand-cleaned version, that becomes the fix | Code `NV-loud` |
| The 0.90 note-test bar becomes a reported figure, not a stop | The install gate passes on repeatability, with timing measured; F 0.751 is recorded and reported |
| The automatic checks and the listening page still catch extra notes | Unchanged. Said plainly: the page's "extra or wrong notes" button is the main guard |
| A clean-up rule is built only if loudness isn't enough | Code `NV-short`: a rule under its own later declaration |

**1. The note-versions read.** Each version is built as `tr-di` is built (`ring-soft` deciding, `ring-on` beside,
the `song_bank.measure` finish), and compared with the DI.

| Version | Notes | Levels |
|---|---|---|
| `nv-true` | the true notes | as today |
| `nv-asis` | Basic Pitch's notes after the clean-up | as today |
| `nv-hand` | Basic Pitch's notes that pair with a true note (same pitch, onsets within 50 ms, one to one); nothing added | as today |
| `nv-loud` | all of Basic Pitch's notes | each note at its detected loudness, gamma 1 |
| beside: `nv-loud2`, `nv-hand-loud` | the stronger setting (gamma 2); the hand-cleaned notes at gamma 1 | — |

- **Each note at its detected loudness** (`synthesise_redo`'s two new options, both off by default so `tr-di` stays
  byte for byte, proved by stored hashes). Inside an onset group a note's weight is its amplitude over the group's
  largest, to the power gamma, the group rescaled to today's power. A group that starts under louder ringing notes is
  turned down by its largest amplitude over the largest still sounding (never up), applied after the group's level.
  Gamma 1 first, 2 only if 1 is not enough. No note is dropped.
- **Material:** Guitar-TECHS P1 and P2 direct-input recordings (development material, CC BY 4.0; P3 is held out and
  never read), with their MIDI cleaned first (notes under 58 ms dropped, same-pitch notes within 30 ms merged); the ten
  made-up lists (their "DI" is the list's own audio); GOAT's 27 development windows (no usable truth: `nv-asis` and the
  loud versions only).
- **A truth window is used only if its truth is consistent:** at least 8 notes, and at least 80% of its onset
  clusters (onsets chained within 150 ms) have their steepest DI rise within 30 ms of the window's one offset. The same
  test replaces `annotated-found`'s admission, whose old "lands" test passed at 84 to 88% of random times.
- **The distance**, `floored_logmel`: `logmel_distance` (left as it is) with each side floored 60 dB under its own
  loudest bin. The floor was chosen after the review's look at six windows with made-up ghosts.
- **The instrument check, `ghost-ladder`, first:** made-up octave ghosts added at 0, −6, −12 and −20 dB must lower the
  distance at every step, the −20 dB version not below the plain rebuild, on the ten lists and six real windows. Any
  list failing stops the work (to the user). A real window failing alone makes the real set reported only.
- **The numbers per set** (cluster means, 90% intervals): the extras' cost C = `nv-asis` − `nv-hand`; what loudness
  leaves, G = `nv-loud` − `nv-hand`; the other gap, E = `nv-hand` − `nv-true`. "Near": C clear of zero, G's mean at most
  a quarter of C's mean and G's upper end at most half of it. "Short": G's lower end above half of C's mean. "Cost not
  shown": C's interval is not clear above zero, whether it reaches zero or lies wholly below it (extras that bring the
  rebuild closer to the DI show no cost); it never counts as a pass and never reads "short".

| Code (the first that holds) | When | What follows |
|---|---|---|
| `NV-loud` | near on the lists; on the real DIs near, cost not shown or reported only; on GOAT `nv-loud` not decided worse than `nv-asis`; the chord guard holds; gamma 1 if it qualifies, else 2 | Loudness is adopted at that gamma. No note dropped, no Basic Pitch setting changed. The calibration then runs with it |
| `NV-short` | short on either set at both gammas | A clean-up rule under its own later declaration, fitted on fresh made-up lists; if it fails, the row runs with the listening page as the guard, or the work stops; no second rule |
| `NV-none` | cost not shown on the lists | Run as is, with the listening page as the guard |
| `NV-undecided` | anything else | If the lists read near at either gamma with the guard holding and GOAT not decided worse, adopt that gamma; otherwise run as is, with the page as the guard |

- **The chord guard:** on windows with five or more notes in groups of three or more, Basic Pitch run again on
  `nv-loud` finds chord notes no more than 0.05 less often than on `nv-asis`; the same for soft notes (truth-paired
  notes that loudness turns down by more than 3 dB). The share of such notes is reported on P1, P2 and GOAT, pooled
  over each set's paired notes. When the real set is reported only, its windows stay out of the guard too: a
  reported-only set enters no reading.
- **The `other-gap` flag:** on the real DIs, E clear of zero and larger than C. Reported, and the work goes on.
- **Expected:** gamma 1 will probably read "short" on the lists and gamma 2 is borderline; `NV-undecided` or gamma 2
  is more likely than a clean pass. The made-up lists carry the read; the real DIs will mostly say "cost not shown".

**2. The attack detector is replaced, and `onsets-found` becomes a report.** librosa's spectral-flux onset detector
(defaults except a 256-sample hop, threshold 0.07) on the transcriber's own input, run in the Basic Pitch venv. Per
part, the share of the DI's attacks with a note within 50 ms (after the detector's offset, measured on P1), flagged
under 0.90; flagged parts are listed and the row is also read beside without them. Its report carries the detector's
recall of true onset groups, overall and on ringing onsets (one that starts while another note has sounded 100 ms and
goes on 100 ms more); should it ever gate again, it needs 0.90 on both. Chords and scales are reported apart, and on
chord windows the recall is also reported on 150-ms groups, since a strum spreads 120 to 200 ms. `playing-covered` stays blocking, so the
calibration's 25-of-27 rate is `playing-covered`'s; the old rise levels and their precision bar are retired.
- **Two triggers:** P2's chord recall in the truth report under 0.85 goes to the user before any of the 47 parts is
  transcribed; `onsets-found` flags on 3 or more of the 40 deciding parts, counted straight after transcription, go to
  the user before any build. The user's go is recorded as `phase_nr_1_redo_go_chords` or `phase_nr_1_redo_go_flags`.
- **The rejected clips, measured now** (CPU only, nothing saved): all six fail the blocking `playing-covered`, and all
  sit under 0.90 on the report-only `onsets-found` (0.17, 0.67, 0.79). Should `calibrate` read differently: (a) a clip
  caught only by a report is recorded "caught by a report only", the page's "missing notes" button is its guard, the
  user is told, and the work goes on; (b) a clip caught by no check goes to the user, recommended "go on with the
  listening page as the guard" (their go: `phase_nr_1_redo_go_clips`). This spends the plan's one calibration
  amendment.

**3. The truth report (`truth-precision`), reported, never a gate.** Basic Pitch's notes against the cleaned MIDI,
precision and recall, chords and scales apart, P1 and P2 apart; a mains-hum guard; P2's rest level.
- **The hum guard, corrected twice before anything runs:** a window stops the report when over 5% of its found notes
  sit on a mains harmonic (50 or 60 Hz times 1 to 6, within 50 cents), pair with no truth note (same pitch, onsets
  within 50 ms), **and start where no truth note is sounding** (from 50 ms before a truth note's onset to its note-off).
  That is where hum would show.
  - **The plan's rule was wrong:** it counted every found note on a mains pitch, and those pitches include MIDI 43, 47,
    50, 54, 55, 59, 62 and 66 (G, B, D and F-sharp). Treating the cleaned truth itself as the found notes, the review
    found 228 of 238 windows over 5% (median 0.25): a perfect transcriber would have stopped the report.
  - **The first correction was also wrong:** it counted unpaired mains-pitch notes anywhere. The truth used as found
    notes cannot fail that test (each truth note pairs with itself), but Basic Pitch's own extra notes do. On the gate
    rerun's stored notes for the ten hum-free lists it stopped 3 of 10 (37 of 431 notes counted, every one starting
    while a truth note sounded: 24 same-pitch re-finds, 10 harmonics, 3 others). Under the rule above those lists count
    0 of 431, a test replays them, and real strums no longer trip it. The MIDI trails the DI by 25 to 35 ms on P1 and 18 to 22 ms on P2 on
scales; one offset per window leaves about ±10 ms by pitch, acceptable at 50 ms. GuitarSet is in Basic Pitch's training
data, so its published guitar score is not used as a yardstick.

**4. The install gate.** The 0.90 known-notes bar is a reported figure, by the user's decision; the gate passes on
repeatability, with its timing measured. The rerun's record stands: repeatable, 1.24 s a window, F 0.751 reported.

| # | Step | Waits for |
|---|---|---|
| 1 | This declaration | an independent review |
| 2 | `truth`: the listing (zero Basic Pitch runs); its sha256 into `phase_nr_1_redo_truth` | 1 |
| 3 | `attacks-report` (timed on 3 windows first); `ghost-ladder` (a failing list stops) | 2 |
| 4 | `truth-report`; P2's chord recall against its trigger | 3 |
| 5 | `versions`, once (3 real builds timed first); an independent recompute; `phase_nr_1_redo_versions` | 4 |
| 6 | By the code: adopt loudness, or back to the user (`phase_nr_1_redo_go_versions`) | 5 |
| 7 | `calibrate` with the adopted synthesis; then the 47 parts, the flagged-parts trigger before any build | 6 |

Zero renders throughout, no training, no download. Basic Pitch: about 265 runs on DIs and 800 round trips at the
measured 1.24 s a window; about 3,100 dry-guitar builds at the review's measured 0.14 to 0.48 s each.

**Filled in at declaration:** the user's go keys (`phase_nr_1_redo_go_chords`, `_go_flags`, `_go_clips`,
`_go_versions`), named here because the plan left them unnamed; `build` reads loudness from main's
`phase_nr_1_redo_versions` (its gamma on `NV-loud`, else the user's recorded decision); the made-up lists' "DI" goes
through the same `song_bank.measure` finish as the versions, as the development windows' DI does; `ring-on` beside is
built for every version (it enters no reading); the soft-note turndown counts weight and trim together; the six ladder
windows are the first usable window of the first two chord files and of the first scale file that have one, by name;
the ladder records how many of its ghosts the bank could play (a ghost above its range is not played); every truth
window is checked against its listing's note count and offset when read, and the lists' stored events against the
install's model and settings.

**What it can't say:** how the plugin reacts to an extra note (nothing is rendered); much about real guitars (the
lists carry the read); how many extras Basic Pitch makes on full songs (GOAT has no usable truth); anything about stems.

**Step 3 run, and the user's two answers (2026-11-23; ledger `phase_nr_1_redo_go_ladder`, `phase_nr_1_redo_go_flags`).**
Run once from main at 7697c48e, zero renders. `attacks-report` (1.30 s a window, timed on 3 real windows first):
the detector's P1 offset −14.1 ms; recall of true onset groups P1 0.943 (chords 0.766, 0.985 on 150-ms groups),
P2 0.989 (chords 0.952), the lists 0.987. Scored with the true notes, `onsets-found` reads under 0.90 on all 79 real
windows (median 0.42 and 0.45 on P1 and P2 scales): the detector fires about 2.4 times per real note. `ghost-ladder`:
9 of 10 lists pass; `chords-four` falls at every step (3.215, 2.320, 1.787, 1.713) but its −20 dB version is 0.6%
below the plain rebuild (1.7235), so the check stopped the work; 3 of 6 real windows fail.

| Asked (AskUserQuestion) | The user's answer | What follows |
|---|---|---|
| The ladder: one list 0.6% below the plain rebuild at −20 dB, where the rule allowed no tolerance | "Continue, record why" | `chords-four` still falls at every step and its 0.6% is within noise; no rule is changed after the fact; the real set is reported only. `versions` reads past the failed check only with this go naming that `ghost-ladder.json` by its sha256 (`ladder_refusal`) |
| The 3-of-40 flagged-parts trigger, when even the true notes fail `onsets-found` on every real window | "Report it, don't stop" | The trigger becomes a reported figure: `build` reads the go and does not refuse on the count; flagged parts are still listed and read beside; the listening page stays the guard for missed notes |

The ladder rule and every threshold are unchanged.

**Step 4 run, and the user's answer on the hum guard (2026-11-23; ledger `phase_nr_1_redo_go_hum`).** Run once from
main at 474fa4ee, zero renders, 51 s (Basic Pitch on the 79 usable truth windows and GOAT's 27). P2's chord recall
0.955 (85 of 89; file-clustered 90% interval 0.910 to 0.990): the 0.85 trigger did not fire. P1's chords 0.712 (116 of
163), half the misses in 4 of 15 windows.

| Set | Precision | Recall | Precision, found notes starting inside the window (beside only) | The same with the guard's 50-ms lead (beside only) |
|---|---|---|---|---|
| P1 chords | 0.228 | 0.712 | 0.261 | 0.261 |
| P1 scales | 0.616 | 0.995 | 0.622 | 0.618 |
| P2 chords | 0.431 | 0.955 | 0.509 | 0.509 |
| P2 scales | 0.677 | 1.000 | 0.686 | 0.681 |

The hum guard stopped the report on 18 of 79 windows. It was not hum. The truth keeps the notes that start inside a
window, but Basic Pitch's notes include a chord still ringing in from before it, and ringing G, B, D and F-sharp sit on
mains pitches: 34 of the 42 counted notes start in the transcriber's 1-s lead-in, and 31 of those match a same-pitch
MIDI note sounding at the window's start. Tightening the rule afterwards would still leave 4 windows over the line. The
same edge inflates the extras, hence the side precision column (re-matched from the stored note files, no rerun; the
strict cut also drops 18 true pairs that start up to 50 ms early, so its recall on scales reads 0.968 and 0.983; with the 50-ms lead no pair is lost and every recall is as stored).

| Asked (AskUserQuestion) | The user's answer | What follows |
|---|---|---|
| The guard stopped 18 of 79 clips on chords ringing in from before each clip, not hum | "Continue, record why" | The counted notes are ringing chords, not hum (real hum sits 60 to 71 dB down); no rule is changed after the fact. `versions` and `transcribe` read the stopped report only with this go, its `go` true and naming that `truth-report.json` by its sha256 (`truth_report_refusal`); `ladder_refusal` now checks its go's `go` field too |

The guard's rule and every threshold are unchanged.

**Step 5 run: the note-versions read reads `NV-none` (2026-11-23; ledger `phase_nr_1_redo_versions`).** Run once from
main at aaf97a2d, zero renders, 1,145 s (10 lists, 79 real windows, GOAT's 27), beside other sessions' jobs; the build
rate, timed on 3 real windows first under load, was 2.28 s a build; the run's own mean was about 0.85 s (1,230
builds in 1,040 s), against the review's 0.14 to 0.48 s. Every number is by `floored_logmel`, a dry-domain distance to
the DI, not the J0 judge. **Premise caveat:** the distance's own instrument check failed (the ghost-ladder on
`chords-four`) and the work went on by the user's go; by that go the real set is reported only and the read rests on
the 10 lists.

| Set (ring-soft decides) | C = as is − hand | G = loud − hand (γ 1) | G2 (γ 2) | E = hand − true | loud − as is (γ 1) |
|---|---|---|---|---|---|
| Lists (10) | +0.56 [−0.14, +1.26] | +0.24 [−0.34, +0.82] | +0.14 [−0.38, +0.66] | +1.81 [+1.20, +2.41] | −0.33 [−0.53, −0.12] |
| Real (43 files, reported only) | +0.10 [−0.28, +0.47] | −0.04 [−0.40, +0.32] | −0.20 [−0.56, +0.15] | +0.68 [+0.36, +1.00] | −0.14 [−0.20, −0.07] |
| GOAT (27) | — | — | — | — | −0.04 [−0.10, +0.02] |

- **The code: `NV-none`** at both gammas: C's interval on the lists reaches zero, so the extras' cost is not shown.
  "Cost not shown" means the set is too quiet or too noisy to say, not "no effect": the test is underpowered (SE 0.38
  with 10 clusters; one-sided p 0.087). Its declared recommendation: run as is, with the listening page as the guard. A
  code other than `NV-loud` goes to the user (`phase_nr_1_redo_go_versions`).
- **Why C reaches zero (the audit's mechanism):** `nv-hand` drops Basic Pitch's same-pitch re-finds of a held note, and
  `ring-soft` then cuts the held note 150 ms after the kept piece's early end, so on `bend` (C −1.70) and
  `triads-and-singles` (−0.88) it lands farther from the DI than `nv-asis`; its 50-ms pairing also misses real chord
  notes in strums. The other 8 lists read +0.22 to +2.03, except `chords-six` (−0.14). Side figure only, entering no
  reading: `hand-merge` (each paired note extended over its re-finds) reads C +1.18 [+0.43, +1.92] on the lists.
- **Loudness** moves the rebuild closer than as is on the lists (−0.33, clear of zero) and on the real DIs, about a
  quarter to a third of a fair C; GOAT is not decided worse.
- **The chord and soft-note guard fails at both gammas** (lists only, the real set being reported only). Gamma 1:
  chord notes 0.937 on `nv-asis` against 0.888 on `nv-loud` (holds), soft notes 7 of 10 against 0 of 10 (fails):
  Basic Pitch no longer re-finds them; in the audio they are 3–5 dB down on their own string. Gamma 2: chords 0.839
  (fails), soft notes 0.78 against 0.26 of 23 (fails).
- **The turned-down share** (truth-paired notes turned down by more than 3 dB): P1 0.004 and 0.018, P2 0.007 and 0.023,
  GOAT 0.063 and 0.157, at gamma 1 and 2.
- **`other-gap`:** not read, the real set being reported only. Beside: on the real DIs E (+0.68) is clear of zero and
  larger than C (+0.10), and on the lists E (+1.81) is larger than C too. E is dominated by early note ends together
  with the re-finds (`ring-soft` truncation) and by spurious bends; loudness is not part of it (hand-loud − hand +0.06
  on the lists, 0.00 on the real DIs).
- **The implementer's recompute** (from the per-window records, by plan text, scipy's t): code, readings, guard, shares
  and every list and GOAT interval agree. The real set's interval ends differ by about 2%: `pipeline_fix.t95` falls back
  to 1.6449 past 30 degrees of freedom (t is 1.682 at 42); the set is reported only, so no reading moves. The
  independent check is the audit (CONFIRMED WITH CORRECTIONS): every stored number agrees to 5e-6 with the fallback
  emulated; its corrections are the wording above.

**The user's decision (2026-11-23, by AskUserQuestion; ledger `phase_nr_1_redo_go_versions`): "Run as is
(Recommended)".** Rebuild with the tool's notes unchanged and no loudness (`loud` null, the shape `build` reads), then the
decisive 47-part row (about 13,450 renders). **The next fix target**, recorded now and under its own later declaration:
a same-pitch merge of a held note's re-finds and a gate for spurious bends (zero renders), taken up only if the row
shows the rebuild limits the search.

**Step 7's first `calibrate` stopped, and its fix (2026-11-23; ledger `phase_nr_1_redo_calib_fix`,
`phase_nr_1_redo_go_calib`, `phase_nr_1_redo_go_guard`).** Run once from main at e0f053cd, zero renders, 246 s (`calibration.json` sha256
`a18ec73c…3ab8`). It stopped on three counts. `playing-covered` held on 8 of 27 windows, against a declared 25: the
rebuild is silent for about 10% of the time the DI plays, against a 5% bar, which is the held-note fault the versions
audit found. `annotated-found` admitted no window. The positive control failed: the true DI failed `chords-kept` on 19
of 27, and avg+mild failed on 26 (`chords-kept` 26, `ring-kept` 7, `judge-accepts` 1). The six rejected clips were
all caught by a blocking check.

| Asked (AskUserQuestion) | The user's answer | What follows |
|---|---|---|
| Two checks are broken (mismatched timelines; no clip admitted); the third catches the deferred held-note fault | "Fix broken checks, go on (Recommended)" | The two checks are fixed below, no threshold changed; `playing-covered` is reported, not a stop, for this run; the listening page is the guard; the 47-part row decides |
| Even fixed, three checks still fail on the real DI, so all become reported figures and the 13-card page is the only guard before the row | "Proceed, listening page guards (Recommended)" | `chords-kept`, `judge-accepts` and `ring-kept` become reports, named in the go; a check the go does not name stays blocking |

- **`chords-kept` on one timeline.** As run, the DI's notes were moved by `coarse_offset` and the ±20 ms snap, and the
  round trip's were not (`item_102`: −101 ms, F 0.0). Now the round trip goes through the same steps against the audio
  that was transcribed (`round_trip_notes`), in `calibrate`, its negative control and `build`. Measured at zero cost
  from the stored inputs (every rebuilt input identical to the stored one): **the true DI passes on 11 of 27 windows**
  (8 as run), avg+mild on 0 (1 as run). The true DI's round-trip F has a median of 0.82. The timeline fix moves only 3
  windows; the first question to the user put all 19 failures down to the timelines, but the other 16 are Basic
  Pitch's own variability on the same audio: the DI's notes come from the window with its margins, the round trip from
  the section alone.
- **`annotated-found` becomes a report.** No fair test admits GOAT's windows. Measured at zero cost: the declared test
  admits **0 of 27**. Bounding each cluster's rise search halfway to its neighbours also admits 0 of 27. A ±40 ms search
  admits 8 of 25, but random onset times pass it 6 of 75 (median share 0.57), so it does not tell an annotation from
  chance. The ±150 ms search does separate them (0.45 against 0.24), but no window reaches 80%: in GOAT's dense playing
  the steepest rise near a note is often a neighbour's.
- **The positive control's rule.** A declared blocking check that the true DI or avg+mild still fails on any window
  (one window is enough), after these fixes, becomes report-only for the row only when the user's go names it
  (`phase_nr_1_redo_go_guard`, `positive_report_only`); a failing check the go does not name stays blocking, and its
  failure stops the calibration as declared before. From the first run's figures this covers `chords-kept` (the true
  DI fails it on 16 of 27), `ring-kept` (avg+mild 7) and `judge-accepts` (avg+mild 1), all three named by the user's
  go. With `playing-covered` reported, no content check then blocks, and each of the six rejected clips is caught by a
  report only: the listening page is the guard, as the user chose.
- **Blocking from here on** (`effective_blocking`): the declared blocking checks, less `playing-covered` under the go,
  less the report-only checks; used by the clip cases, `transcribe` and `build`. A rejected clip caught only by a
  report is case (a): recorded, the user told, the work goes on.
- **The rerun.** The first `calibration.json` and its work folder move aside into `calibration.failed-20261123/`,
  never deleted. `calibrate` then runs once more. It refuses unless main holds the fix and the user's go naming the
  set-aside record's sha256 (`calib_rerun_refusal`), and it never overwrites `calibration.json` or `work/calibrate/`.
- **The clip fault:** these DIs pass through `song_bank.measure`, whose ±15 dB EQ clip the track-4 audit found. Its
  clip-free re-score is declared by track 4 and reported beside new dry-guitar rows; it is not run here.

### 12n. The ear items' kinds, amended 2026-11-23 (the delegated decision; ledger `phase_nr_1_ear_kinds`)

**Why.** After the calibration's rerun passed, `transcribe` stopped before transcribing any part: "no item of kind
['let-ring', 'single-note'] among the development items". This was diagnosed from the stored scans, with no runs.
- `single-note` needs no bent note, and Basic Pitch marks nearly every note bent: `item_14` 14 of 14, `item_143` 69 of
  75. No item qualifies, even with every group a single note.
- `let-ring` needs half or more of the groups to ring 100 ms into the next onset. The highest share is 0.16
  (`item_5`). On GOAT's annotated notes, 21 of 23 annotated items read 0.00, and two read 0.037 and 0.061.
- Both are the faults the versions read's independent audit found (its section 4, summarised in the step-5 note
  above): spurious pitch bends, and held notes cut short.

**The decision** was made by the delegated decision agent under the user's standing instruction of 2026-11-23
(technical decisions go to it). It is not a go of the user's.

| Kind | Rule |
|---|---|
| `single-note` | Read from GOAT's annotated notes: the same window (the 10 s with the most notes on the 5-s grid), the same grouping, the same bar (80% or more single-note groups). "No bend" holds because the annotation carries none. Its ear window is that window |
| `chord-led`, `bends`, `let-ring` | On the transcription, as declared |
| A kind still unfilled after the declared pass through the seeded order | The not-yet-picked item with the highest value of that kind's own figure (ties by the seeded order), recorded as `{"kind", "filled": false, "nearest": true, "figure", "bar"}` and labelled "let-ring (nearest; none met 0.50)" |

- **Rejected:** a bend threshold set after the fact; dropping cards.
- **Measured on the stored scans** (the branch's code): `chord-led` `item_77`, `bends` `item_39`, `single-note`
  `item_49` (from the annotation), and `let-ring` filled by nothing, so its nearest is `item_5` (figure 0.16 against
  the bar 0.50). All four are clear of the exclusion list and are in neither the row's draw nor the replay's.
- **Statement:** No development item meets the declared let-ring bar. The figure reads note-offs, which the transcription is known to cut short, and the annotation shows almost no let-ring by this figure. This is a limit of the figure, not evidence that the pool has no let-ring playing.
- **Caveats.** The transcriber's bends are mostly spurious, so the `bends` slot is labelled by the transcriber and is
  not verified; how it is picked is unchanged. Picking `let-ring` by the transcriber's note-ends leans toward the item
  where its cutting is mildest.
- **Unchanged:** the 13 cards; the 4 crunch repeats (the nearest let-ring item included); the hidden control; the
  buttons; `redo_verdict`'s reading; the exclusion list; no other GOAT items used. The kind is not shown on the cards:
  it is kept in the transcribe record, `ear-items.json` and the clips index.
- **Code:** `kind_figures`, `ear_kinds_of`, `nearest_fill`, `choose_ear_kinds` beside `pick_ear_items` (which stays
  pure and unchanged) and `annotated_notes`. `transcribe` writes the chosen items, sources and figures to
  `ear-items.json` and `transcribe.json` (`ear_kinds`).
