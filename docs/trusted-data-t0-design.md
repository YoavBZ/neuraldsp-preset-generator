# Trusted data, T0 to T2: the code, the calibration and the launch (design)

**Status (2026-10-25):** the ear has answered T0's queue and T1 ran; an audit found no cleaning gain established. The
user then decided that an active guitar that cannot be rendered is the session's own amp track(s) after an automatic
bleed check ([rule 1 after the user's decision](#rule-1-after-the-users-decision-2026-10-25)): T2's pilot is
reachable (5,154 candidates in 4 bands outside early stopping), but under the reviewed check every amp track has an
unmeasurable source, so T1 keeps no example. See
[T1 audited (2026-10-25)](#t1-audited-2026-10-25) and [T0 outcome (2026-10-25)](#t0-outcome-2026-10-25). *Before the ear (2026-10-23):* T0 ran on the user's Mac (calibration OK; the lists and the ear queue; see the ROADMAP and the
ledger's outcome). T1 and T2 have not run. After T0 and before the ear, a multi-agent review changed the import of the
ear's answers and several rules, at zero renders: [the review before the ear](#the-review-before-the-ear-2026-10-23)
at the end. The next `lists` run recomputes every verdict under them.
- **The code review of #281** returned "go with fixes", and the re-review two more fixes plus a
  ruling. All are applied, and listed at the end.
- **The numbers below** come from zero-render dry runs on the stored crops and sections, written to
  a scratch folder. They show what T0 should find, not T0's record.
- **An input that arrived during the work is built in:** sitting 1 of data-review-1 judged the
  crops' **DI** clip, not the amp clip.

- **Plan:** [trusted-data-strategy-plan.md](trusted-data-strategy-plan.md), approved with its
  recorded decisions.
- **Code:**
  - `learn/verify_tracks.py`: the standard, its calibration, T0 and the ear queue;
  - `learn/trusted_data.py`: the self-built mix builder, T1 and T2.
- **Tests:** `tests/test_verify_tracks.py`, `tests/test_trusted_data.py`.
- **Evidence:** the target-vs-DI measurements behind the known amps are in
  [audits/target-vs-di-2026-10-23](audits/target-vs-di-2026-10-23/) (`measures.json` and
  `measure.py`).
- **Machine rules:**
  - The two render commands are in `local_objective.RENDERS`: `verify_tracks negatives`, and
    `trusted_data render` and `vreal-render`.
  - Renders run with isolate=True, a priming render, and at most 3 processes machine-wide.
  - Disk guard 31 GB. No downloads.
  - The `trusted-data` ledger entry is written; real runs check for it.

## The standard as built

Per judge half of a crop (A 1.0–5.5 s, B 5.5–10.0 s), `reference.wav` against `di.wav`.

| | Measure | Rule | Changed from the plan? |
|---|---|---|---|
| A1 | GCC-PHAT lag over 80 Hz–4 kHz | 0.1 ≤ \|lag\| ≤ 30 ms passes. A negative lag, or a peak under 12× the median (unreadable), goes to the ear | band and prominence gate added |
| A2 | H1 = S_xy/S_xx (Welch 4096), coherence ≥ 0.5; median \|H\| 1–3 kHz minus 6–10 kHz | Decided only over ≥ 17 coherent bins in each band: **≥ 12 dB passes** (the plan's), **under 3.3 dB fails**. In between, or fewer bins, goes to the ear and stays out until heard | an ear band and a fail line added; the pass is unchanged |
| A3 | Least-squares FIR (exact covariance, 24 kHz, −5..+60 ms around the A1 lag), fitted on one half, read on the other, both ways | both residuals above −40 dB | no |
| A4 | Peak \|r\| (±50 ms) with every session DI; file hash | < 0.95; no shared hash | no |
| A5 | `crop_match2.py`'s measures (ported) | play share ≥ 0.5; chroma ≥ 0.8 or onset ≥ 0.35 | no |
| A6 | The bleed audit's bleed per half; for parts read in a mix (stage F), an electric same-part track in the mix | bleed < −30 dB; such a track < −30 dB of the target | "another take" limited to electric guitar tracks |

**Gates on the measures:**
- A1–A3 read only halves where the DI plays on at least 25% of frames.
- A part whose crop DI is silent and that feeds the level prior is read on up to 3 of its prior
  sections instead.

**DIs:**
- **D1:** against the loudest own amp track, using the medians over every window the DI is read on.
- **Every session DI is read at every D-build section time of its session.** These are the
  windows where it plays as another guitar in a self-built mix. `trusted_data` refuses a window T0
  never measured, and uses only usable ones.
- **D2:** part A's flags on the window (clipping, drop-outs, hum ≥ −55 dB), plus part A's
  hum-suspect list.
  - A fail on the DI's own D-build sections excludes the DI.
  - A fail on another window excludes that window only.
- **D3:** by name.
- **D4:** below.

**The rule:**
- A measured fail of A1–A6 or D1–D3 excludes.
- The ear decides the rest, and when answers disagree, a negative answer wins:
  - **A DI heard processed** is excluded with all its sections.
  - **Heard clean** clears only the heard window.
  - **Heard clean while D4 flags it** is a conflict for the user, not a pass.
  - **D4 alone never decides an unheard DI.** A flagged section waits for the ear.
  - **Also waiting for the ear:**
    - DIs whose D1 went to the ear;
    - DI-only parts;
    - a seeded sample of D4-passed DIs (one per band, seed 20261103).
- **A target is trusted only once heard** clean, and as an amp where A1 or A2 went to the ear.
  Quicksand ElecGtr2 and Today's The Day ElecGtr07 stay excluded on their measured fails (user,
  2026-10-24). A target's measure DI is heard first too: an unheard one queues a `di_unheard` card
  (6 on 2026-10-24: 4 of V-real's parts, 2 of knob ceiling 2's).
- **`lists` recomputes every verdict** from the stored readings under the current thresholds. It
  refuses on:
  - a missing, incomplete or stale `dis` or `stem-scan` shard;
  - an incomplete or stale `targets` record;
  - a target without its crop row.

### D4, the DI is unprocessed

**Measures** (`di_processing`, on the playing 100-ms frames):
- the median crest factor;
- the slope of brightness (3–8 kHz over 0.1–1.5 kHz) against level.

**Rule:** the DI reads as processed when crest < 8.4 dB or slope < −0.2. The rule was set on the
user's 35 heard crop DIs.

**Agreement with the ear:**
- **In-sample:** 30 of 35.
- **Leave-one-out:** 26 of 35. Each DI is judged by the rule refitted on the other 34. Refitted on
  all 35, the rule is crest < 8.2 or slope < −0.28.
- **Heard processed, 17:** 16 caught. Missed: Gym Hours GTR 2, which sounds like a clean amp.
- **Heard clean, 18:** 14 passed.
- **The 4 heard clean but flagged are conflicts for the user,** not passes: Drag Me Down ElecGtr4,
  Quicksand ElecGtr2, Signs ElecGtr2, colour-me-red elecgtr03.

**Gaps:** no measure separated delay, modulation or an amp or cab signature on these 35.

## Calibration (`negatives`, then `calibrate --ear-di <sitting-1 export>`)

**Known amps (11), re-derived** from the target-vs-DI measurements, not from sitting 1:
- **The rule:** both halves follow the DI with a mic delay of 0.1–30 ms, and |H| falls at least
  12 dB from 0.5–2 kHz to 6–12 kHz (`known_amps_from`). `calibrate` checks `KNOWN_AMPS` against it.
- **Dropped:**
  - Passing Ships ElecGtr4 (the review);
  - the 7 pairs whose DI sitting 1 rejected (the re-review: a pair without a real DI cannot anchor
    a DI-to-amp calibration): Passing Ships ElecGtr6, Bloomlight, Farthest Step, First Offering
    GTR 2, Gym Hours GTR 2, Russian Cream GTR 2, She's Gone.
- **The 11:**
  - It Was My Fault ElecGtr2 and 3;
  - Signs ElecGtr2;
  - colour-me-red 02 and 03;
  - get-out-of-bed 2;
  - magilla 1 and 1DT;
  - wickerman 3;
  - Blind Spots;
  - Sculptor's Request GTR 2.

**The other cases:**
- **Known fails:** Prodigal ElecGtr3 and ElecGtr5.
- **Constructed negatives** on the DIs of It Was My Fault ElecGtr3 and magilla elecgtr1. Both DIs
  were heard clean and pass D4.
  - a copy;
  - an EQ'd DI: an 80 Hz–5 kHz band-pass with a +6 dB peak at 2 kHz, delayed 1.5 ms. Only A3 can
    catch it.
  - the DI through PR12 with the cab section off: the clean start is declared, the crunch start is
    beside. 6 renders.

**CALIBRATION OK needs all of these** (as amended by the calibration fix below; `NEG_MUST_FAIL`):
- the known amps fail none of A1–A4;
- both known fails fail one;
- the copy fails A1, A3 or A4;
- the EQ'd DI fails A3;
- every cab-off negative in `NEG_MUST_FAIL` fails A2: PR12's clean start, and (from the fix) SW50R's and AC20's.

**Dry run, zero-render part:**
- **Known amps:** none fails. 4 pass A2 (It Was My Fault ElecGtr3, colour-me-red 02, magilla 1DT,
  Blind Spots); 7 go to the ear on A2.
- **Prodigal ElecGtr5:** lag 0.0 ms, drop −0.3 and 0.4 dB over 324 and 255 bins. Fails A1 and A2.
- **Prodigal ElecGtr3:** lag 0.0 ms, drop 0.0 dB over 342 bins. Fails A1 and A2.
- **Copies:** fail A1–A4 (residual −71 to −93 dB).
- **EQ'd DIs:** fail A3 only (−86 to −108 dB, against the amps' −1 to −27 dB).
- **The cab-off DIs:** pending `negatives`. If the clean one reads 3.3 dB or more, the fail line
  moves to the midpoint of the new closest pair (recorded).

**Threshold changes** (`THRESHOLD_MOVES`):
- **A2's pass stays at the plan's 12 dB.**
  - 3.3–12 dB goes to the ear. colour-me-red 03 (6.2 dB) and Signs 2 (10.3 dB) land there.
  - The fail line, 3.3 dB, is the midpoint of Prodigal ElecGtr5's 0.4 and colour-me-red 03's
    6.2. It is unchanged with 11 known amps.
  - **Ruling (a), from the re-review:** a fail must pass the existing 17-bin gate, as a pass does,
    so no new number is fitted. A half under the gate goes to the ear and stays out until heard:
    Quicksand ElecGtr2 (12 and 10 bins) and Adam Buckley ElecGtr5's DI (one bin at −19 dB).
- **A1 band and prominence gate.**
  - The known amps' peaks stand 24–279× over the median. Unreadable high-gain pairs stand 4–7×.
    The gate sits at 12.
  - The band-limited lag agrees with the stored `di_lag_ms`.
- **D4:** as above.

## T0 (zero renders apart from calibration's cab-off negatives: 8, plus 6 priming)

Run from the merged checkout. `MAIN=…/.venv/bin/python`.

| Step | Command | Time |
|---|---|---|
| 1 | `$MAIN -u -m learn.verify_tracks negatives` (8 renders plus 6 priming) | about 2 min |
| 2 | `$MAIN -m learn.verify_tracks calibrate --ear-di <sitting-1 export>` | under 1 min |
| 3 | `$MAIN -m learn.verify_tracks targets` | about 1 min |
| 4 | `$MAIN -m learn.verify_tracks dis --shard k/3` (k = 0, 1, 2) | about 1–2 min each |
| 5 | `$MAIN -m learn.verify_tracks inject-strict` | about 20–40 min |
| 6 | `$MAIN -m learn.verify_tracks stem-scan --shard k/3` | about 30–45 min each (20 sessions, 101 sources; Hollow Ground, 8 sources over 142 s, took 235 s) |
| 7 | `$MAIN -m learn.verify_tracks lists --ear-di <sitting-1 export> [--ear <target-vs-DI export>] [--ear <each ear-page part's export> ...]`: every export in one call, every time (a run that would drop an earlier run's export refuses) | under 1 min |
| 8 | `$MAIN -m learn.verify_tracks reread` | under 1 min |

The sitting-1 export is
`~/.claude/uploads/67cfc004-f421-4d92-9cce-0e70317476ec/9422aa1d-data-review-1-sitting-1.json`.
`--ear` refuses it: it judged DIs, not targets.

**`lists` also writes `t0/ear-queue.json`:** every item the ear must hear, with counts. Each item
has an id, kind, files, window, reason and allowed verdicts. The kinds:
- **`target`:** the DI, then the target. Verdicts: clean_amp, bleed, other_guitar, not_amp,
  unsure.
- **`di_conflict`:** heard clean but D4-flagged.
- **`di_flagged`:** an unheard D4-flagged section.
- **`di_sample`:** a sampled D4-passed DI.
- **`di_only`:** a DI with no amp track.
- **`di_amp`:** the DI, then its amp track (D1 to the ear).

The page built from the queue exports to page `trusted-data-ear`. `lists --ear` reads that export
back through `t0/ear-items.json`. `learn/build_ear_page.py build` writes it as three parts, one
question each: targets (DI, then target), DI and amp pairs (DI, then amp track), and DIs. The DI
part is blind: it never shows why an item is queued, and its files are shuffled (seed 20261023),
each file's windows kept together (one limit: flagged windows come in runs, so a file with many
windows is likely a flagged one). Clips are levelled to −23 LUFS, AAC at 96 kbps. Each part
exports its own file, passed as its own `--ear`.

**Silent windows (fixed 2026-10-23).** The first queue held 15 digitally silent windows: for
`di_amp` and `di_only` it played the section with the most "playing" frames, and a silent section
counts every frame as playing. The queue now picks the busiest audible section; a DI silent in
every section (4 "other guitar" overdubs: Dark Ride ElecGtr03 and 04, Prodigal ElecGtr4 and 5,
which play outside every measured window) is excluded, since no mix uses it; `lists` retires the
silent items, and `ear_answers` skips any answer on them. The build refuses a silent clip, cached
or not, and refuses to rebuild over built pages. `build_ear_page extra` put the 11 re-picked
windows on a fourth part, leaving parts 1–3 and their stored answers alone. A `di_only` item is no
longer queued when the DI already has a flagged window queued (a flagged window heard clean clears
it too): 7 such repeats left the queue (184 items), part 4's items 4, 5, 6, 8, 9 and 11 among them.

**What the dry run shows** (scratch, zero renders):

**Ear queue: 195 items (59 DIs, 18 targets).**

| Kind | Items |
|---|---|
| target (18 targets × 2 halves) | 36 |
| di_flagged | 101 (own sections and other-guitar windows) |
| di_amp | 37 |
| di_only | 11 |
| di_sample | 7 |
| di_conflict | 3 (the fourth, Quicksand 2, has an excluded target) |

**Targets:** 41 excluded, 18 pending the ear, none trusted yet.

**Stage F (V-real): 11 parts in 7 bands, all pending the ear.** It Was My Fault ElecGtr3, Signs
ElecGtr3, colour-me-red 02 and 03, femme 5, get-out-of-bed 2, let's dance 3 and 4, and wickerman
1, 2 and 3. Excluded:

| Part | Reason |
|---|---|
| Passing Ships ElecGtr2 | A1 and A2: a zero-lag path, no roll-off |
| Passing Ships ElecGtr4 | measure-DI hum |
| Quicksand ElecGtr2 | A6 (its A2 goes to the ear under ruling (a)) |
| Today's The Day ElecGtr07 | A5 |
| magilla elecgtr1 | its DT double is in the mix |
| wickerman elecgtr7 | hum-suspect DI |
| Gym Hours GTR 2 | DI hum |
| Russian Cream GTR 1, She's Gone, Strangest Places | A6 |

**Knob ceiling 2: 7 parts pending the ear.** Drag Me Down 4, It Was My Fault 2, Quicksand 1, Signs
2, Today's The Day 10, femme 3 and get-out-of-bed 1. This is the panel for the re-reads.

**DIs:** 5 trusted outright, 49 pending the ear, 5 excluded.
- **Excluded:**
  - the three Eggy DIs, heard processed;
  - Prodigal ElecGtr1 (hum) and ElecGtr3 (D1).
- **Dark Ride's and Storm Of Particles' drop-outs** now exclude only their windows, and Adam
  Buckley ElecGtr5 waits for the ear.
- **Usable pool and V_sep sections until the ear has answered:** Ale Lak 2, Kimock 4 and Swatkins 1.
  Every other band's sections are pending, and Eggy's 96 are excluded. So K and T2 wait for the
  ear.

**The level prior** is re-derived on 308 values in 11 bands (median −7.8 dB, 5–95% −11.6 to
−2.9), against 971 values (median −7.9, −18.9 to −2.7). *T1 and T2 draw from the stored prior, not this one,* so that
K − V_sep and SYN − SES stay paired on the same draws (the plan's T1 and T2 rows: "the same examples and draws"); the
re-derived prior is for T3's new examples (the plan's (c)).

## T1 (`trusted_data`, no training)

**K** is R_in's examples:
- outside Kimock and Swatkins;
- outside the MUSDB18-tagged Bannockburn;
- on DIs and sections T0 trusts;
- each with R_in's stored truth render.

**Other guitars** respect T0's unusable sections. *Since 2026-10-25 (the user's decision):* a session guitar that plays
in the section but cannot be rendered is its own amp tracks when they pass an automatic bleed check, else the example
is left out ([rule 1](#rule-1-after-the-users-decision-2026-10-25)); a near-silent other-guitar render refuses its
example ([T1 audited](#t1-audited-2026-10-25)).

**The read:**
- K − V_sep mel-grid stem SNR, paired on the same examples and draws.
- Band-clustered with three or more bands. With one or two bands (K is Adam Buckley and Dark Ride), the
  section-clustered interval is primary (*amended 2026-10-25:* two bands, not one; [T1 audited](#t1-audited-2026-10-25)).
- V-real's stored crop stems beside, by ratio.

**Plans carry T0's lists' sha256 (`t0/verified.json`).** `render`, `build`, `t1-read`, `train`, `fit` and `e-on-k`
refuse when it has changed.

| Step | Command | Cost |
|---|---|---|
| amp-bleed | `$MAIN -u -m learn.trusted_data amp-bleed --stage t1 --shard k/2` | zero renders; about 20 min per session (CPU) |
| plan | `$MAIN -m learn.trusted_data plan --stage t1` | zero renders |
| render | `$MAIN -u -m learn.trusted_data render --stage t1 --shard k/3` | about 0.8–1.5k renders plus priming |
| build | `$MSST -m learn.trusted_data build --stage t1 --device mps --order asc` (CPU worker beside) | about 370 separations, about 30 min |
| read | `$MAIN -m learn.trusted_data t1-read` | minutes |

## T2 (`trusted_data`, the 5k pilot; code only)

*Ran 2026-10-25 to 26: a tie, SYN picked by recorded decision 4 ([outcome](#t2-outcome-2026-10-26)).*

**The examples:**
- **The pilot:** 5k trusted-pool examples (seed 20261099, stratified by band) on usable sections.
- **The early-stopping set:** about 5% of sections, at least one per band (seed 20261100), at most
  1,000 examples.

**The arms:**
- **SES:** the stored stems.
- **SYN:** the same examples, labels and draws, with self-built backings.
- **SYN-E:** a seeded third (seed 20261101) swapped for Eggy. *Dropped from T2 for now (user, 2026-10-24):* no Eggy
  DI is trusted.

**Training:** D_stem's recipe, 2 seeds per arm. The constant and pull are fitted per arm on its
early-stopping set.

**The reads:**
- **Primary:** SYN − SES on V-real, by the judge with the measure DI. Paired by direction,
  band-weighted, 90% band-clustered. A tie under 0.03 picks SYN.
- **Beside:** SYN-E − SYN, each arm − S, E on K, and T1's stem SNR. *Since 2026-10-25* ([T1
  waived](#t1-waived-and-the-realism-check-moved-into-t2-2026-10-25)): K is empty, so T2 reads no E on K; T1's stem
  SNR is the superseded 812-example read and must be labelled or dropped in `report`.
- *Added 2026-10-25 (approved after review):* the T2-side stem read and the data-gap diagnostics, declared in the
  same section and built before T2's results are seen.

| Step | Command | Cost |
|---|---|---|
| amp-bleed | `$MAIN -u -m learn.trusted_data amp-bleed --stage t2 --shard k/2` | zero renders; about 20 min on 2 processes (CPU) |
| plan, render | `$MAIN -m learn.trusted_data plan --stage t2`; `$MAIN -u … render --stage t2 --shard k/3` | about 12–18k renders, 2.5–3.5 h on 3 processes (the 2026-10-25 dry run: 5,538 targets and 8,732 other guitars, plus priming; *superseded:* the run of 2026-10-25 plans 5,308 targets and 10,099 other guitars in 4 bands) |
| build | `$MSST -m learn.trusted_data build --stage t2 --device mps` | about 6k separations, 5–8 h |
| train | `$TORCH_PY -m learn.trusted_data train --arm SES\|SYN --seed 20261042\|20261043` | 4 runs, about 1.5 h MPS |
| fit, E on K (*none since 2026-10-25: K is empty*), V-real | `fit`, `e-on-k`, `vreal-predict` (TORCH_PY); `vreal-render --shard k/3`, `report` (MAIN) | about 210 renders at 10 V-real parts (60 per arm for SES, SYN and the constant, plus 30 priming; SYN-E dropped) |

## Open questions

1. **The ear queue is large: 195 items** (184 live after the queue fixes). *Resolved:* answered 2026-10-25, queue 0. The 37 `di_amp` items cover the D1 rule on metal DIs,
   and other-guitar windows add flagged items. T2 waits until the ear has answered.
2. **SYN-E has no Eggy.** *Decided 2026-10-24 (user):* dropped from T2 until a clean-class DI source (EGDB or GOAT) passes the DI checks.
3. **K may be one band.** Admit Cnoc An Tursa despite its MUSDB18 tag? *Answered (user, 2026-10-24):* not admitted;
   T1's K is Adam Buckley and Dark Ride.
4. **The cab-off negative is pending (6 renders).** Resolved: rendered and failing A2 (the calibration fix below).
5. **Ruled:** a fail now needs the 17-bin gate, so Adam Buckley ElecGtr5's DI goes to the ear.

## The review's fixes (#281, "go with fixes")

1. **A2.**
   - The 12 dB pass is kept; 3.3–12 dB goes to the ear.
   - The bin gate no longer turns a fail into the ear.
   - The known amps are re-derived from the target-vs-DI measurements, not sitting 1.
   - Passing Ships ElecGtr4 is out of both the known amps and the negatives.
2. **D4.**
   - Leave-one-out agreement (26/35) is reported beside the in-sample 30/35.
   - D4 never decides an unheard DI.
   - A sample of flagged and passed DIs is queued, and pending until heard.
3. **Conflicts.**
   - Heard clean but D4-flagged is a conflict, not a pass.
   - Clean clears only the heard window.
4. **`lists` refuses** on missing, incomplete or stale shards, and on a target without its crop
   row.
5. **Stale results.**
   - Plans stamp the sha256 of T0's lists (`t0/verified.json`), and the later commands re-check it.
   - `targets` and `dis` refuse to resume under other thresholds.
   - `lists` recomputes every verdict from the stored readings.
   - Stem floors are checked.
6. **D1 to the ear, and DI-only parts,** are queued and pending.
7. **Other guitars** respect unusable sections.
8. **Ear inputs.**
   - `--ear` refuses a DI-verdict export.
   - A negative answer wins.
9. **T1 with one band** reads the section-clustered interval.
10. **The ledger entry** is written. `dis` calls `heldout_ok` on crops and
    `clean_di.refuse_held_out` on every DI.

## The re-review's fixes (#281, two fixes and a ruling)

1. **KNOWN_AMPS less the 7 pairs whose DI sitting 1 rejected.** 11 remain, and the fail line is
   unchanged. Recorded in `THRESHOLD_MOVES` and the calibration record.
2. **Other guitars.**
   - Every session DI, the pool's and V_sep's included, is read at every D-build section time of
     its session.
   - `trusted_data plan` refuses a window T0 never measured.
   - An other guitar enters a mix only on a usable window.
3. **Ruling (a):** an A2 fail needs the same 17-bin gate as a pass. A half under the gate goes to
   the ear and stays out until heard. Recorded.

## Calibration fix: the clean cab-off negative (2026-10-23)

**What happened.** The real T0 stopped, as designed, on `CALIBRATION FAIL`. The negative It Was
My Fault ElecGtr3 through clean PR12 with the cab off "fails none of [A2]". It wasn't diagnosed
with new renders: everything below comes from the 4 stored negative renders and the stored crops.

**Why A2 did not fail it.**
- **Its coherent |H| does not roll off at all.** It reads −2.0 and −2.8 dB from 1–3 kHz to
  6–10 kHz, rising slightly.
- **It has only 12 and 7 coherent bins above 6 kHz.** The median coherence is 0.04.
- **Under ruling (a), a fail needs 17 bins,** so the half went to the ear, not to a fail.
- **The other negatives:**
  - magilla's clean cab-off has 17 and 19 bins, and fails at −5.6 and −8.2 dB;
  - the crunch cab-off negatives have no coherent bins at all.
- **The 11 known amps** read 6.2–22.4 dB on the halves that decide. Seven go to the ear on too few
  bins.

**A1 does not catch it either.** A render is not zero-delay: Morgan's 52-sample latency
(1.06–1.08 ms) stays in the renders by design, and A1 reads it as a mic delay and passes. A3
(−13.9 dB) and A4 (r 0.91) pass as well.
- **So "must fail at least one check" would not rescue the negative:** it fails none.
- **The targeted rule is the right one.** Each negative is built to probe one measure (the cab-off
  one probes A2). A looser "any one" rule would let a gap in A2 hide behind an accident elsewhere.

**The fix: a cab signature that needs no coherence.**
- **The measure:** the target's spectral slope over 5–10 kHz, less its DI's, in dB per octave.
- **Why it works:** a speaker cab falls steeply above about 5 kHz. An amp without one, clean or
  driven, keeps the DI's top or adds harmonics to it. Measuring against the DI's own slope removes
  the pickup, the cable and the playing.
- **The rule:** where the coherent A2 goes to the ear, a relative slope above −1.65 dB/oct fails
  A2.
- **Nothing new is fitted.** The line is A2's existing 3.3 dB fail line spread over the two
  octaves between its bands.
- **It reads only on halves with bleed under −30 dB.** Bleed dominates the top of a cab-filtered
  track. Constructed negatives carry none.
- **It never overrides a coherent pass,** and it never passes anything.

**On the stored data:**

| Case | Relative slope (dB/oct) |
|---|---|
| The 10 bleed-clean known amps | −10.5 to −24.2 |
| The cab-off negatives | +0.8 to +10.9 |
| Prodigal | −0.0 to +1.5 |
| The copies | 0.0 |
| The EQ'd DIs | −27.5 (caught by A3) |

- **Sculptor's Request GTR 2** reads +11 and +12.6, but its halves carry −28.6 dB of drum-room
  bleed, so the check does not read it. It stays at "ear".
- **Calibration re-run on the stored negatives** (scratch, zero renders): **CALIBRATION OK**. All
  four cab-off renders fail A2, and no known amp fails.
- **Across all 59 real targets,** the check newly fails only halves of parts that were already
  excluded: Passing Ships ElecGtr3 B (−1.6), Gym Hours GTR 2 (its DI was heard processed) and
  Hikikomori B.
- **Recorded** in `THRESHOLD_MOVES` and `thresholds()`. The stored T0 records are therefore stale;
  T0 reruns from `calibrate` after review, and the 6 renders are reused.

**Not changed:**
- D1's per-DI A2 still uses the coherent drop alone.
- The calibration rule for negatives is unchanged.

**How to read this fix (review of #282):**
- **When it was added:** after the calibration failed, to make it pass.
- **The −1.65 dB/oct line is a relabelling,** not a derivation. It restates A2's 3.3 dB fail line
  per octave between the two bands. Nothing physical fixes it there.
- **Its only effect on today's real data** is that calibration reads OK. On the real targets it
  fails only halves of parts that other checks already exclude.
- **So its evidence is weak until fresh negatives confirm it** (below).
- **Sculptor's Request GTR 2 needs no change.** Its top end is cymbal bleed: the slope check does
  not read it, A2 stays "ear", and A6 fails it at −28.6 dB.

**Fresh negatives, declared 2026-10-23 before any of them was rendered.**
- **The renders:** SW50R and AC20, each at its clean start with the cab section off, on both source
  DIs (It Was My Fault ElecGtr3, magilla elecgtr1).
  - 4 renders plus 4 priming renders: one process, isolate=True, a priming render per DI and amp,
    at most 3 render processes machine-wide (checked first).
  - Written to a scratch root holding a copy of the stored negatives' manifest.
- **The rule:** each of the 4 must fail A2 (`NEG_MUST_FAIL`).
- **Then:** `calibrate` runs on the scratch root.
- **If any fails to fail,** the work stops there and is reported. The check is not tuned.
- **The result is recorded below.**

**Fresh negatives, result (2026-10-23).** All 4 fail A2, and `calibrate` on the scratch root reads OK.
- **Renders used:** 4 plus 4 priming, in one process, with no other render process running.
- **How each failed:** every one went to the slope check, because none had enough coherent bins
  for the coherent A2 to decide (under 17 bins in each half). A1, A3 and A4 pass all 4, as they
  do for the PR12 cab-off renders.

| Render | Coherent bins (A, B) | Slope vs DI, dB/oct (A, B) | A2 |
|---|---|---|---|
| SW50R clean, It Was My Fault ElecGtr3 | 3, 0 | +1.6, +2.0 | fail |
| AC20 clean, It Was My Fault ElecGtr3 | 5, 1 | +1.4, +1.8 | fail |
| SW50R clean, magilla elecgtr1 | 0, 0 | +5.6, +5.2 | fail |
| AC20 clean, magilla elecgtr1 | 0, 0 | +4.8, +5.3 | fail |

- **Margin:** the closest reading, +1.4 dB/oct, sits about 3 dB/oct above the −1.65 line. The
  bleed-clean known amps read −10.5 to −24.2.
- **Nothing was tuned.** The thresholds are the ones declared above.
- **The stored data root does not hold these renders yet.** Until it does, `calibrate` there refuses
  ("negatives not rendered"). The next T0 run's `negatives` step renders them (4 plus 4 priming)
  before `calibrate`.

## The review before the ear (2026-10-23)

After T0 and before the ear, two multi-agent reviews (the trusted-data change, then the whole program;
[record](research/program-review-2026-10-23.md)). No threshold moved and nothing was rendered. Changes:

**The ear's import (`verify_tracks lists`):**
- `lists` rebuilds every verdict from the exports it is given, so it now refuses a real run without `--ear-di`, and any
  run that would drop an export an earlier run read (`--drop-ear` does it on purpose). Each export's path and sha256
  are recorded in `verified.json`, and T1 and T2 refuse lists made without the sitting-1 export.
- On one ear-page card the latest touch across all exports stands (each answer carries the time it was last
  touched): a changed answer replaces the old one, and an answer taken back clears it. A card never touched in a
  browser holds no answer, so another browser's export cannot erase one. A verdict cleared by an empty touch in
  another file (a take-back, or a note typed in another browser) is printed for the ML session to check with the
  listener. (Fixed 2026-10-24: the first rule let a later export's untouched cards erase answers.)
- Notes are kept (`ear_notes`) and printed: a note can qualify or replace a verdict.

**The rule:**
- **A DI waits for the ear while any window D4 flags is not heard clean.** It was "verified" with its other windows
  usable, although a later "processed" excludes the DI with all its sections.
- **Only a clean answer clears a D4-passed sample;** "unsure" kept nothing pending.
- **A clean answer clears a flagged section only when its window covers the whole section** (it cleared any
  overlapping one).
- **A measure DI whose file was heard processed** on another window, or not the DI of its amp take, excludes its target.
- **The sample of D4-passed DIs** redraws within a band when the draw lands on a DI the measures exclude (other bands'
  draws unchanged), and skips a DI already queued as DI-only.
- **The level prior leaves out parts the ear rejected** (the target, or its measure DI). A part waiting for the ear on
  A1 or A2 still counts: it is a level statistic, not a label.
- **An OK calibration counts only under today's negatives, must-fail rule and known amps.**
- **Quiet windows:** `build_ear_page check` reads every live clip against its own file's playing level; `--retire`
  records DI windows where the DI plays on under 10% of the frames (`t0/quiet-items.json`). `lists` retires their items
  like silent ones and reads their sections as silent: their answers are skipped, no mix uses them, and they hold no
  DI back (with the rule above, an unheard quiet window would have kept its DI out for good, and a "Hum" answer on a
  noise floor would have excluded it).
- **Unchanged:** a measured fail excludes before the ear is read, so the two conflicts (Quicksand ElecGtr2, Today's The
  Day ElecGtr07) stay excluded and are not on the pages (the user confirmed it on 2026-10-24, below).

**T1 and T2 (`trusted_data`):**
- **Centred stems fold like a centred guitar** (`pan_fold(0)`): other guitars sat about 3 dB low against the stems.
- **A same-part double confirmed by pitch** (the cleaning plan's `same_part` rule on the target and other DI in the
  section) takes the target's settings and the opposite pan, as a DT double does. Step 0 removed such doubles from
  SES's backings; SYN and K rendered them with their own drawn tone.
- **Other guitars are ranked by playing against their own file's level** (a resting floor read as fully active), and a
  part whose own amp tracks are silent in the section is left out (only a part with no amp track takes the session
  median).
- **A backing with nothing in it** (no stem, no other guitar heard) is refused at build, and `plan` counts such
  examples by band.
- **A refused T2 example drops for every arm;** it was counted as unbuilt, which blocked every training run.
- **Re-planning over rendered rows refuses** when an example's recipe changed (render and build skip any example with a
  row, so the old audio would have been reused). The lists' hash ignores their run time, so a `lists` rerun that
  changes no verdict needs no re-plan. T1's completeness counts the plan's own examples.
- **T1's reading is descriptive.** K cleaner than V_sep is the cleaning gain the plan expects; realism is K against
  V-real at matched ratio (now verified parts only, LUFS on both sides). No lever is coded or approved, so T1 changes
  nothing in T2 by itself.
- **T2's reading is "incomplete"** until every V-real direction is judged for every arm, the predictions cover today's
  V-real, and no answer was refused (a refused answer would score as S, which can favour the broken arm). The report
  adds F-song, without-MUSDB18 and per-class rows, and flags runs whose best epoch is within 4 of the cap.
- **E on K** has the section-clustered fallback when K is one band, as T1 has.

**Restated, not changed:** at V-real's 7 bands a paired arm contrast reads about ±0.036 log d (90%), not the plan's
±0.028; the tie rule (|point| < 0.03 picks SYN) is unchanged.

## The user's decisions (2026-10-24)

The review's four decisions before the ear, each as the ML session recommended. Built at zero renders:
- **The two conflicts stay excluded.** Quicksand ElecGtr2 (A6) and Today's The Day ElecGtr07 (A5): their measured fails
  stand. Sitting 1, the basis of the conflict, judged their DI clips, not these targets. `EAR_DISPUTED` is gone.
- **The stem spot-check joins this sitting** (plan (f)'s T0 "spot-check stems by ear"):
  - **One clip per scanned session:** the passing stem nearest the floor (the highest guitar take; name order on a
    tie), at the D-build section time where it plays most (at least 10% of the window against its own file's level;
    up to 5 stems tried). `lists` stores the choice in `t0/stem-checks.json` and keeps it while the stem passes.
  - **Question:** is an electric guitar audible in this backing track? Clean, a guitar can be heard, or not sure. The
    pages give it part 4 on a fresh build; today it goes on the next extra part.
  - **Rule:** a session's scanned stems are used once its clip is heard clean. A guitar heard holds all of the
    session's stems (the scan missed one there, so the ML session looks before T1), and an unheard or "not sure"
    clip waits.
- **Every DI is heard before it counts.** A DI that passes every measure is verified only once heard: a window heard
  clean, or its pair heard as an amp take of it (the pair page offers "the DI itself sounds processed"). A DI with
  nothing else queued gets one window: the band's seeded draw where it had one, else a seeded D4-passed section
  (seed 20261103, its own sections first). The per-band sample is now a subset of this rule.
- **The song-blind constant is one more V-real arm at T2.** `fit` stores the step 3 gate's constant
  (`direct_sound_gate.constant_answers`: continuous medians of the audible labels, switches by majority, mics by the
  most frequent) over the SYN arm's training labels (SES's are the same). `vreal-predict` adds it as arm "constant",
  `vreal-render` renders it with the others (about 60 renders per arm at 10 parts), and `report` reads SES − constant, SYN − constant
  and constant − S beside the primary. The reading rule is unchanged.


## T0 outcome (2026-10-25)

**The ear is done.** The user heard all 202 cards on `trusted-data-ear` parts 1–4 (exports 2026-10-24 and 25). One
`lists` run read the four exports with the sitting-1 export; nothing was superseded, cleared or skipped (log
`learn/trusted-data/logs/lists-ear-final.log`). Answers: targets 35 clean amp, 1 bleed; DI and amp pairs 34 amp,
1 processed; DI windows 99 clean, 13 processed; stems 14 clean, 5 with a guitar.

**The final lists** (`t0/verified.json`):
- **Targets** 17 verified, 42 excluded. **DIs** 46 verified, 13 excluded.
  *Amended 2026-10-25:* 3 of the 42 pass on other windows, pending the ear and T2's end ([T0 window re-check](#t0-window-re-check-2026-10-25)).
  *Amended 2026-10-26:* heard: targets 19 verified, 1 pending, 39 excluded ([parts 5 and 6](#parts-5-and-6-heard-2026-10-26)).
- **V-real:** 10 parts in 7 bands (3 clean parts in 2 bands, 7 crunch; 3 of the 10 from one song, Wickerman).
- **Knob ceiling 2:** 7 parts in 7 bands verified, the panel for every-control stage 1.
- **K:** 17 DIs in 3 bands, but T1's K uses Adam Buckley and Dark Ride only. Cnoc An Tursa is not admitted (user,
  2026-10-24); Kimock and Swatkins are excluded by the ear, all 4 of their DIs heard processed (Hikikomori, New One,
  Honey, Lost & Alive).
- **Training:** 27 DIs in 8 bands, 181 usable sections; only 1 is clean-class and 1 crunch (61% high gain, the rest
  unclassed).
- **Stems:** 166 usable in 14 sessions (167 before click, metronome and talkback tracks were barred from backings and spot-checks, `NON_MUSICAL`: Split Brow's BAND CLICK; its Pre Rec.L/R are low bass playback, centroid about 120 Hz, and stay). The 5 sessions heard with a guitar are held (Eggy Farthest Step and
  Fragments, Hikikomori, Honey, Lost & Alive).

**Let's Dance ElecGtr4** (the user, 2026-10-24): the leak is in the DI (quiet high notes); the target was too distorted
to judge. The target is excluded and the DI counts as not clean. `verified.json` still shows the DI heard clean in
sitting 1; nothing downstream uses it. The leak sat at about −33 dB, so A6's −30 dB line is not a guarantee.

**The audit's caveats:**
- Eggy Bloomlight's 14 stems count as usable, but no Eggy DI is verified, so they go unused: 153 stems in 13 sessions
  in practice. Its clip was the Key Moog track; the user's note: "Might be a synthesizer, high pitch sound that can be
  confused with a guitar".
- Renesans' stem evidence is weak (a kick trigger, a playback bounce, a growl vocal). Split Brow's usable list holds
  Pre Rec.L/R, unheard there. The plan bans `GTR Pre Rec` (a different file) and allows Renesans' line-level playback
  tracks, but Pre Rec.L/R may be the same material as the banned file, so they must be checked before T2 uses
  Renesans' backings. (Less Than Nothing's Pre Rec.R was heard clean.)
- One thin DI: Ale Lak 15_ElecGtr02DTDI is verified on a single window that plays 31% (the double of 13_ElecGtr02DI,
  which has a full amp pair).
- Leaked drums were noted on the amp tracks of Honey and Renesans (×3); none is used as a target or for levels.
- The re-derived level prior (229 values, 10 bands) draws 131 values from 4 parts whose targets are excluded (allowed as
  a level statistic).

**The main finding:** the training pool holds almost no clean or crunch playing (1 + 1 of 181 sections), against the
clean/crunch scope. Clean-style DIs must come from new sources: EGDB (downloaded; needs its DI checks and a borrowed
backing), GOAT (access requested); Jen Hartswick & Nick Cassarino is reserved for test. Where they come from is an open
user decision before T3.

**T1 started** on 2026-10-25 at 08:29: 812 examples from Adam Buckley and Dark Ride, about 1.8k renders plus priming and
812 separations. It ran; see the next section.

## T1 audited (2026-10-25)

**What T1 read** (812 examples, Adam Buckley and Dark Ride, 26 sections; `t1/read.json`, log `logs/t1-read.log`):
K − V_sep mel stem SNR **+1.63 dB**, band-clustered [+0.12, +3.14] on 2 bands (1 df), section-clustered [−0.31, +3.56].
The code printed "K's stems are cleaner than V_sep's", keyed on the 1-df band interval.

**The independent audit (2026-10-25)** found:
- **Missing guitars carry most of it.** 63 examples (Adam Buckley "Drag Me Down", the ElecGtr3 DI sections at 55 s and
  65 s) had no other guitar in K's backing, although other guitars play there: their T0 windows are excluded, so they
  were silently left out, while V_sep's real backing has them. K − V_sep is about +16 dB on them, about +1.2 dB of the
  +1.63. Without them: **+0.42 dB** (median +0.08), section-clustered [−0.89, +1.72]; Adam Buckley −1.31.
- **Near-silent renders were lifted.** 65 other-guitar renders (in 63 examples) read below −45 LUFS (down to −69) and
  were scaled up by as much as +43 dB to their level; 14 renders were silent and dropped (one example lost all its
  other guitars).
- **K's tail is fatter:** 18.6% of K's stems read below 0 dB mel SNR, against 4.4% of V_sep's.

**The outcome:**
- **No cleaning gain is established.** With the missing guitars out, the interval holds 0.
- **No realism lever follows.** The gap to V-real at matched ratio is within noise and changes sign between readings.
  T2's SYN arm is otherwise unchanged.

**The fixes** (`learn/trusted_data.py`; tests in `tests/test_trusted_data.py`). Whatever leaves an example out leaves it
out of every arm, so K, SES and SYN stay paired:
1. **Plan time: an active guitar that cannot be rendered leaves the example out** (`LEFT_OUT_ACTIVE`, "an active
   guitar cannot be rendered"). For each guitar part of the section's session other than the target's
   (`session_guitar_parts`: non-DI tracks from the inventory's mix list, the stored backing's source; DIs always;
   acoustic guitars included), the part plays when any of its tracks, amp track or DI, plays on at least 10% of the
   section's frames against its own file's level (`section_activity`, as other guitars are picked). It cannot be
   rendered when it has no DI, its DI is not verified, or the DI's window is not usable in T0's lists. `plan` records
   the left-out sections with the guitars and reasons (`left_out`), counts and prints them, and for T2 removes them
   before any draw.
2. **Render time: a near-silent render is refused, never lifted.** An other guitar's render below
   `RENDER_FLOOR_LUFS` (−50.0), or silent, refuses the example through the existing refusal path ("near-silent render
   (gate or low output)"), so it drops for every arm. The example's remaining renders are skipped.
3. **The reading.** With fewer than 3 bands (`MIN_BANDS`) the primary interval is section-clustered (the one-band rule,
   extended: 2 bands give 1 df). `t1-read` prints medians beside means, the share of stems below 0 dB per arm and the
   per-band difference, and keys the reading on the primary interval ("no difference shown" when it holds 0). E on K
   takes the same rule. T2's report reads V-real at 7 bands, so its rule is unchanged.
4. **A zero-render re-read:** `t1-read --subset rules` reads the stored rows less the examples rules 1 and 2 would
   have left out, under today's lists; `--subset rules-di` is a diagnostic that applies rule 1 only to parts that
   have a DI. Both write nothing (logs `logs/t1-read-audit-subset-rules[-di]-2026-10-25.log`).

**The re-read (2026-10-25, zero renders):**
- **Rule 1 leaves out all 812 examples (26 sections).** Every K section has a playing guitar with no DI in V_sep's
  stored backing: Adam Buckley's ElecGtr1 (amp track only) and acoustic guitars, Dark Ride's ElecGtr02, 02DT, 08 and
  08DT (amp tracks only). 781 examples have such a part; 314 have an active part whose DI window T0 excluded (the 63
  above among them). Under rules 1 and 2 as coded there is nothing to read.
- **Rule 2 leaves out 61 examples:** 48 with a render below −50 LUFS, 14 with a silent render (one has both).
- **The diagnostic (`rules-di`: rule 1 on parts with a DI only, plus rule 2):** 360 left out (rule 1: 314 in 10
  sections; rule 2: 61), **452 read** (Adam Buckley 142, Dark Ride 310; 16 sections).

  | | K − V_sep (dB) |
  |---|---|
  | mean, median | +1.80, +0.65 |
  | section-clustered (primary) | +1.67 [−0.15, +3.49], 16 sections |
  | band-clustered | +1.25 [−8.11, +10.61], 2 bands |
  | Adam Buckley | −0.23 (median −0.31), n 142 |
  | Dark Ride | +2.73 (median +1.12), n 310 |

  Below 0 dB: K 10.6%, V_sep 3.1% (K mean +3.85, median +2.56; V_sep +2.05, +1.57). Reading: no difference shown.
  Dark Ride's +2.73 still has its 4 amp-only guitars in V_sep's backing and not in K's, the bias rule 1 removes.

**What this means for T2:** under rule 1 as coded, T2's candidates fall from 8,722 examples in 6 bands (114
sections) to 3,955 in 3 bands (Ale Lak, Death Of A Romantic, Storm Of Particles; 52 sections), short of the 5k pilot
and its early-stopping set; Hollow Ground, Rebuild The Evil and The Long Wait lose every section, on parts with no DI.
Restricted to parts with a DI, 7,956 in 6 bands remain. Self-built mixes cannot hold a guitar that has no DI (decision
4: other guitars are DI renders only), so T2 needs a user decision first: keep rule 1 and shrink T2, add the
session's own amp tracks for parts with no DI (decision 4's other option, verified studio amp tracks), or accept the
missing guitars for parts with no DI and read them as a known bias.

**T1 must be re-planned before any further T1 run:** T0's lists' hash changed after T1 (Split Brow's click track only,
PR #289), so `render`, `build` and `t1-read` refuse T1's stored plan (`--subset` reads it with a warning).

### Rule 1 after the user's decision (2026-10-25)

**The decision** (the user, in chat, 2026-10-25, "Sounds good, go ahead" to the ML session's option 1): in self-built
mixes, an active guitar that cannot be rendered is represented by the session's own recorded amp track(s), after an
automatic leakage check, with no listening. It replaces rule 1 above and takes decision 4's other option (verified
studio amp tracks) for these parts only; parts with a usable DI are still rendered.

**The code** (`learn/trusted_data.py`; tests in `tests/test_trusted_data.py`):
- **Which guitars:** as above (`section_blocked`): each guitar part of the session other than the target's that plays
  in the section (any of its tracks, amp track or DI, against its own file's level) and has no DI that can be rendered
  there. Acoustic guitars count. A part is grouped by name and by the inventory: a DI's own amp tracks (inventory
  `own`) are its part (`part_keys`; Hollow Ground's ElecGtr1a_Amp1, ElecGtr1b_Amp2 and ElecGtr1c_DI are one take,
  which the name key split by their letters), unless the track's name gives another part number than the DI's
  (Renesans' "GTR 2 Amp_M81", listed under "GTR 1 DI", stays part 2).
- **What goes in the backing:** all the part's amp or mic tracks in the session's mix list, summed with the stems at the
  session's balance as recorded and folded like them (a mono file by pan_fold(0); a stereo file is folded on loading;
  `backing_tracks`). Only K's and SYN's backings get them; SES keeps its stored stems, V_sep its stored stems, and
  pairing across arms is unchanged.
- **The bleed check** (`amp-bleed`, zero renders, CPU, before `plan`): each such track's other-instrument bleed must
  read under −30 dB (A6's line, `AMP_BLEED_DB`), every track of the part. The measure is the cleaning plan's take
  estimator (`data_cleaning`'s SessionMeter, counted frames and rolled nulls, the stem scan's), read once per session
  over the whole session (not per section or half: a recorded leakage path does not change between sections), with
  each non-guitar track as the source and the amp track as the reference: a take is the share of the amp track's
  energy on its playing frames that the other track explains on held-out folds, less the mean of the rolled readings
  (`data_cleaning.take_db`, raw, capped at 0 dB); the bleed is the power sum of the takes at or above −40 dB
  (`data_cleaning.FLOOR_DB`). The raw real and rolled readings and the source's active share are stored per source
  (`source_raw`), and the verdict is drawn from them (`track_bleed`, `amp_status`). T0's stored target readings were
  not used: they exist only for label-table parts (with a DI) and read the crop, not the session.
- **Sources are non-guitar tracks only** (`bleed_sources`: drums, room, vocals, bass, keys and the other non-guitar
  tracks, by the stem scan's guitar classification; amended the same day, as the coordinating session asked). A6 reads
  other-instrument bleed, and in these sessions guitars double or play the same riffs, which the estimator reads as a
  coherent path: on the first full pass, with each other guitar part's loudest amp track as a source too, Dark Ride's
  ElecGtr02 pair read each other at −24 to −27 dB and Adam Buckley's ElecGtr2 pair at −24 to −25 dB, overdubs that
  cannot leak into each other.
- **Unmeasurable sources** (the independent review of #290, replacing a 0-dB clip of the held-out readings, which
  read injected bleed of −27 to −28 dB as none or −35, so its line sat near −26 dB). A source is unmeasurable when the
  estimator cannot be trusted on it (`source_take`):
  - a blow-up: the real or a rolled reading beyond the amp track's own energy (a source silent for long stretches gives
    fold weights that blow up where it plays; the first pass read these as takes of the whole track, 0 dB);
  - rolled readings spread as wide as the line (max − min ≥ −30 dB of the amp track): the chance level is not known
    well enough to place a take on either side of it;
  - the source plays on fewer than half of the amp track's playing frames (`AMP_SOURCE_MIN_SHARE`).

  Under the trusted-data rule (use only what can be trusted) a track with any unmeasurable source fails ("amp track
  bleed unmeasurable"), with the sources and reasons recorded.
- **Left out** of every arm before any draw, each counted and printed once by reason, with the guitars, tracks and
  readings recorded in the plan:
  - "an active guitar has no usable amp track" (`LEFT_OUT_NO_AMP`): a part with no amp track, a silent one, one at or
    above −30 dB, or one with an unmeasurable source. A missing reading refuses the plan;
  - "an added amp track is in the cleaning scan's removed or same-part tracks" (`LEFT_OUT_OWN_TAKE`, `cleaning_clash`):
    a track the cleaning plan took out of the section's stored backing, or confirmed as another take of the target's
    part, never comes back (a section the scan has no row for is left out too);
  - "more active guitars than the cap" (`LEFT_OUT_CAP`, `apply_cap`): more renderable active guitars than
    `MAX_OTHERS` (4, the plan's "1–4 per example"); `pick_others` used to drop the quietest silently (Ale Lak's
    ElecGtr01DI and ElecGtr01DTDI in 65 pilot examples). Raising the cap would change the declared recipe, so the
    examples are left out instead.
- **Rule 2** (a render below −50 LUFS refuses its example) is unchanged (`place_other`); `render` and `t1-read` print
  the refusals by reason. `t1-read --subset` still re-reads the stored K
  under the audit's rule 1 (those mixes have no amp tracks).
- **A fix on the way:** T2's `plan` overwrote its left-out records with the candidate rows (the same variable), and
  would have failed when printing them.

**The injection check, in the check's own roles** (read-only, in memory; log `logs/amp-bleed-injection-2026-10-25.log`):
a copy of a real non-guitar track, 1 ms later, added to a real amp track at −25, −30 and −33 dB of its energy on its
playing frames, read with `source_raw` and `source_take`:

| Amp track | Source: reads at −25 / −30 / −33 dB injected |
|---|---|
| Hollow Ground ElecGtr1a_Amp1 | Kick −25.5 / −30.6 / −33.8; Overheads −25.1 / −30.3 / −33.7; BassDI −24.3 / −28.9 / −31.6; Vox1 −25.1 / −29.8 / −32.4 (unmeasurable: plays on 29% of the frames) |
| Dark Ride ElecGtr08 | KickMic1 −23.5 / −29.5 / −34.4; Overheads −23.3 / −28.5 / −32.1; Bass −21.1 / −26.2 / −29.4; LeadVox1 −17.3 / −22.3 / −25.3 (unmeasurable) |

The raw reading reads injected bleed back within about 1 dB, or high (the injected copy also plays where the guitar
rests, which adds playing frames): never more than 1.4 dB low. A synthetic version is a test (`tests/test_trusted_data.py`).

**The readings** (2026-10-25, a scratch root; logs `logs/amp-bleed-dryrun-raw-2026-10-25-*.log` and
`logs/plan-dryrun-rule1-raw-2026-10-25-t1|t2.log`; earlier passes' logs are kept beside). **Every amp track has at
least one unmeasurable source, so every one fails.** Per track: non-guitar sources; unmeasurable by blow-up / spread /
share; the worst take among the measurable sources; their sum:

| Session | Track | Sources | Blow-up / spread / share | Worst measurable take (dB) | Sum (dB) |
|---|---|---|---|---|---|
| AdamBuckley | 22_AcousticGtr1 | 36 | 1 / 16 / 16 | 08_HiHat -34.6 | -34.6 |
| AdamBuckley | 23_AcousticGtr2 | 36 | 0 / 1 / 27 | 49_BackingVox2DT -33.8 | -30.9 |
| AdamBuckley | 24_AcousticGtr3 | 36 | 0 / 5 / 27 | 40_Piano -46.1 | under -40 |
| AdamBuckley | 25_ElecGtr1 | 36 | 1 / 16 / 13 | 08_HiHat -32.3 | -31.3 |
| AdamBuckley | 26_ElecGtr2 | 36 | 0 / 15 / 14 | 17_DrumsRoom -35.7 | -32.9 |
| AdamBuckley | 28_ElecGtr2DT | 36 | 0 / 12 / 16 | 17_DrumsRoom -31.0 | -28.4 |
| AdamBuckley | 32_ElecGtr4 | 36 | 0 / 24 / 9 | 17_DrumsRoom -29.9 | -29.1 |
| AdamBuckley | 34_ElecGtr5 | 36 | 0 / 2 / 24 | 18_BassDI -35.7 | -33.1 |
| AleLak | 14_ElecGtr02DT | 9 | 0 / 2 / 3 | 05_Overheads -30.4 | -26.8 |
| DarkRide | 18_ElecGtr02 | 38 | 5 / 10 / 16 | none | under -40 |
| DarkRide | 19_ElecGtr02DT | 38 | 5 / 11 / 15 | none | under -40 |
| DarkRide | 25_ElecGtr08 | 38 | 0 / 8 / 22 | 06_SnareDown -37.7 | -33.6 |
| DarkRide | 26_ElecGtr08DT | 38 | 0 / 9 / 21 | 15_Bass -44.1 | under -40 |
| DeathOfARomantic | 11_ElecGtr01 | 17 | 0 / 3 / 7 | none | under -40 |
| DeathOfARomantic | 13_ElecGtr02 | 17 | 0 / 2 / 8 | none | under -40 |
| HollowGround | 12_ElecGtr1a_Amp1 | 13 | 0 / 2 / 2 | none | under -40 |
| RebuildTheEvil | 18_ElecGtr1 | 20 | 2 / 1 / 2 | 14_Tom5 -37.3 | -34.5 |
| RebuildTheEvil | 19_ElecGtr2 | 20 | 2 / 1 / 2 | 11_Tom2 -37.0 | -33.4 |
| TheLongWait | 06_AcGtr1Mic1 | 15 | 0 / 3 / 11 | none | under -40 |
| TheLongWait | 07_AcGtr1Mic2 | 15 | 0 / 2 / 11 | none | under -40 |
| TheLongWait | 11_ElecGtr2Mic1 | 15 | 0 / 4 / 9 | 03_Overheads -43.6 | under -40 |
| TheLongWait | 12_ElecGtr2Mic2 | 15 | 0 / 4 / 9 | 03_Overheads -40.6 | under -40 |
| TheLongWait | 13_ElecGtr3 | 15 | 0 / 2 / 11 | 04_DrumsRoom -31.2 | -31.2 |

Without the share rule, every track still has a source whose rolled readings spread as wide as the line (1 to 24 per
track), mostly vocals, synths, sound effects and toms: in these roles the estimator cannot resolve −30 dB on sparse
sources.

**T1 under rule 1 as reviewed: 0 kept, all 812 left out** (26 sections; Adam Buckley 405, Dark Ride 407), all with
"an active guitar has no usable amp track": every needed amp track is unmeasurable (and Dark Ride's ElecGtr09 has no
amp track, 64).

**T2 under rule 1 as reviewed:** 3,151 candidates left out for unmeasurable amp tracks (Ale Lak 152, Death Of A Romantic
307, Hollow Ground 307, Rebuild The Evil 2,308, The Long Wait 77) and 109 for the cap (Ale Lak); none for the cleaning
guard. 5,154 remain outside early stopping in 4 bands (Ale Lak 539, Death Of A Romantic 1,615, Hollow Ground 1,539, Storm
Of Particles 1,461; early stopping 308 examples in 4 sections). Rebuild The Evil and The Long Wait drop out. The 5k pilot
is still reachable, narrowly: it drew 5,000 (Ale Lak 523, Death Of A Romantic 1,567, Hollow Ground 1,493, Storm Of
Particles 1,417), with no amp tracks; 5,308 target renders, 10,099 other-guitar renders plus priming and 5,308
separations. SYN-E stays refused.

**Caveats:**
- The verdicts above are the estimator's limits, not measured bleed: the measurable sums are under −30 dB on 17 of the
  23 tracks. Adding amp tracks at all needs either a source set and thresholds the user accepts (for example the share
  rule off) or a reading that resolves sparse sources, which is a new measure.
- A fail can also be the guitar in the other track, or a part locked in time with the drums.

*Superseded 2026-10-25: T1's re-run is waived ([below](#t1-waived-and-the-realism-check-moved-into-t2-2026-10-25)).*
**T1 must be re-planned and re-run before T2,** because K's mixes change (amp tracks join the backings wherever they
pass) and T0's lists changed (PR #289): `amp-bleed --stage t1` (about 20 min CPU per session on 2 processes), then
`plan --stage t1` after moving `t1/rows` and its audio aside (the plan refuses to re-plan over rows rendered under
another recipe), then `render`, `build` and `t1-read`. Under the check as reviewed the re-plan keeps no example, so
there is nothing to render or read: T1 cannot run on K until the check or K changes, and T2 can run without it only if
the user accepts that.

## T1 waived and the realism check moved into T2 (2026-10-25)

**The user's answer** (in chat, 2026-10-25): "I prefer reliable data and additional/longer runs than data that can't
be fully trusted". It answered whether T2 should run on 4 bands without amp tracks, after the reviewed bleed check
(PR #290) cleared none of the 23 amp tracks.

**T2 started 2026-10-25 at 17:54** under PR #290's rules, as the dry run above planned it: 5,154 candidates in 4 bands
(Ale Lak, Death Of A Romantic, Hollow Ground, Storm Of Particles), a pilot of 5,000, early stopping 308 examples in 4
sections, no amp tracks; 5,308 target renders, 10,099 other-guitar renders plus priming and 5,308 separations. Rebuild
The Evil and The Long Wait drop out.

**T1's re-run is waived, not passed.** This follows from the user's answer: under the reviewed rules K is empty, since
every T1 section has an active guitar with no usable amp track. T1 was descriptive and gates nothing.

**K is empty, so T2 reads no E on K.** `e-on-k` has nothing to read: the stored T1 plan (812 examples) is refused on
T0's lists' hash, and a re-plan holds no example. The T2 chain treats its failure as non-fatal. K, and with it the
sound gate T3 and T4 read on K, stay open until a leakage measure that resolves sparse sources, or another route,
brings K back.

**T2's `report` still prints T1's old read** (the 812-example K − V_sep from `t1/read.json`). It is superseded and must
be labelled or dropped in the same `report` fix that adds the T2-side stem read (code later, not in this change).

**The realism question moves into T2** (the ML session's proposal, approved after review, 2026-10-25):
1. **T2's primary read is the decisive realism test:** SYN − SES on V-real compares a model trained on self-built
   mixes with one trained on stored real-backing stems, on verified real songs. Unchanged.
2. **A T2-side stem read** (new; zero renders; descriptive). After T2's build, SYN's stems against SES's stems on T2's
   own examples, by T1's mel-grid stem SNR and contamination, paired, with medians and the share below 0 dB per arm.
   It asks T1's question on T2's 4 bands.
   - **The truth** is T2's target render (`t2/audio/…-target.flac`), the same file for both arms. SYN's mix holds that
     file. SES's stored mix holds its own render of the same label (the D build's, or the cleaning rebuild's), which
     was not kept as audio; both renders were checked against part C's stored mels (within one 0.5-dB step on 99% of
     cells, `MATCH_SHARE`). So for SES the truth is a matched re-render, not the exact guitar in its mix.
   - **The sign is ambiguous.** Above 0 cannot tell "SYN's stems are cleaner" from "SYN's mixes are unrealistically
     easy". At best the read is a ceiling check; it is not a realism verdict.
   - **The backings differ by design.** SES's backing holds real guitars SYN lacks: other guitars that play below the
     activity line (`ACTIVE_MIN`, 10% of the section's frames), with or without a DI, which SYN never renders, so a DI-less
     guitar can sit in SES's backing only there. The left-out dense sections are not read at all.
   - **The interval:** section-clustered is primary, a declared deviation from `MIN_BANDS` (3): 4 bands give a 3-df
     band interval too wide to read, and section-clustering keeps the read comparable with T1's. The band-clustered
     interval is printed beside.
   - It needs a small `report` addition or its own command. It must be built and independently reviewed before T2's
     results are seen.

**The known gap:** a section with an active guitar that has no usable DI or amp track is left out, so dense
multi-guitar arrangements are under-represented in training. SYN short of SES on V-real is a realism signal, not a
gap signal: both arms train on the same filtered examples. The gap is read by these, declared now (zero cost; built and
reviewed before T2's results are seen):
- (a) V-real by the number of guitars playing in the part's crop (dense against sparse parts), for SES − S and
  SYN − S;
- (b) the distribution of active-guitar counts in kept against left-out examples, from the plan's `left_out`;
- (c) *proposed, pending the user's OK (an unplanned longer run):* an SES arm trained on all trusted-pool examples,
  the left-out dense sections included (SES needs no rendering), against SES on the kept set: 2 runs of about 1.5 h,
  no renders. It measures directly what the dense sections are worth on V-real. *Approved by the user 2026-10-25
  ("Approved if you suggest following this approach", after the ML session suggested it): the SES-ALL arm, [built
  below](#t2s-additions-as-built-2026-10-25).*

**The leakage measure** that resolves sparse sources (for example, reading takes only on the frames where the source
plays) would recover the dense sections, let T1 run, bring back Rebuild The Evil and The Long Wait, and give T3 and T4
a known-answer set again. Proposed: build it after T2, when (a)–(c) show the gap matters, or when T3 or T4 needs K. (After T2, 2026-10-26: not shown to matter; it waits until T3/T4 need K.)

**A latent bug** (the review of #290), to fix before Renesans enters any stage: `session_guitar_parts` skips every
track in the target DI's inventory `own` list, so an own track of another part (Renesans' "GTR 2 Amp_M81" under
"GTR 1 DI") is never counted as an active other guitar. *Checked 2026-10-25 (read-only, the inventory):* it does not
touch T2's four bands. In Ale Lak, Death Of A Romantic, Hollow Ground and Storm Of Particles every `own` track has its
DI's part number (Hollow Ground's lettered takes are one part); only Renesans' three sessions list another part's track.

## T2's additions as built (2026-10-25)

Built while T2's chain was still rendering, before any T2 result existed (code `learn/trusted_data.py`, tests in
`tests/test_trusted_data.py`). Nothing here touches T2's chain: it runs after it ends
([the follow-up chain](trusted-data-t2-followup.sh)) and only adds to T2's records.

**The approval of (c)** (the user, in chat, 2026-10-25): "Approved if you suggest following this approach", after the
ML session suggested it.

**The T2-side stem read** (`t2-stem-read`; zero renders; descriptive; writes `t2/stem-read.json`):
- **The examples:** T2's pilot and early-stopping examples, less the refusals every arm drops (and any example whose
  truth half is silent).
- **The measures:** per example, SYN's X-LANCE stem and SES's stored stem against the truth, by T1's mel-grid stem SNR
  and the audit's contamination, both halves averaged, paired.
- **The truth:** T2's target render, the same file for both arms. For SES it is a matched re-render, not the exact
  guitar in its mix (above). That biases SES's SNR a little low, so SYN − SES a little high (recorded in the read as
  its truth caveat).
- **The interval:** section-clustered primary, the declared deviation (`STEM_READ_PRIMARY`), band-clustered beside.
- **Beside it:** per arm the mean, median, share of stems below 0 dB and contamination; the paired contamination;
  per band; medians by drawn ratio.
- **The reading** keys on the primary interval and stays a ceiling check (`stem_reading`). Above 0 reads "SYN may be
  easier than real mixes, or only cleaner; this read cannot tell which". Otherwise it reads "SYN is not shown to be
  easier than SES" or "SYN is not easier on this measure". Every wording adds "a ceiling check only, not a
  realism certificate"; realism is SYN − SES on V-real. `report` carries its reading.

**What counts as a playing guitar (diagnostics (a) and (b)):** rule 1's activity rule, unchanged. The window's
guitars are the target's part plus each other guitar part of the session (`session_guitar_parts`: DIs always; amp and
mic tracks when they are in the mix list; acoustic guitars included). A part plays when any of its tracks plays on at
least 10% of the window's frames against its own file's level (`playing_count`). For a V-real part the window is the
crop's 10 s in its session, and the mix list is the crop's declared mix tracks. A DI-only part counts, as in the plan, so
the count is of guitars playing in the session, not of guitars heard in V-real's mix. `t2-density` lists the parts not
in the crop's mix: Wickerman's ElecGtr8 (DI only) plays in the crop and is counted though V-real's mix does not hold it
(Wickerman's parts count 9 where 8 are heard; the split does not move); Let's Dance's ElecGtr1 and 2 are silent there
and not counted.

**Diagnostic (a), the split** (`DENSE_MIN`, declared before any T2 result): a V-real part is dense when at least 5
guitars play in its crop, sparse with fewer. It is a median split of V-real's part counts. Those counts were read
first (zero renders; no T2 result): 2, 4, 4, 4, 5, 5, 5, 9, 9, 9 (median 4.5).
- **The first draft's line of 3** would have put 9 of the 10 parts on one side, leaving 1 sparse part in 1 band.
- **At 5 each side holds parts in several bands:**
  - dense: Signs ElecGtr3, Colour Me Red ElecGtr02 and 03, Wickerman ElecGtr1–3; 6 parts in 3 bands;
  - sparse: It Was My Fault ElecGtr3, Femme ElecGtr5, Get Out Of Bed ElecGtr2, Let's Dance ElecGtr3; 4 parts in 4
    bands.
- 5 is also 1 + `MAX_OTHERS`, the most a kept T2 example holds.
- The rule is mechanical, a median of the parts' counts. Earlier per-part results exist for these parts (stage F's
  arms and step 4), so it was not chosen blind to every outcome on them; no T2 result existed.
- **What `report` reads:** SES − S, SYN − S and SES-ALL − SES on each side and per count, band-weighted with the 90%
  band-clustered interval. Descriptive, with 3–4 bands a side.

**Diagnostic (b), read now** (`t2-density`, zero renders, writes nothing; log
`logs/t2-density-diagnostic-b-2026-10-25-v2.log`; the first log used an older V-real session path and the draft line
of 3). The candidates are T2's 8,722 before rule 1 and the cap. Each kept section's count equals 1 + the plan's other
guitars in all 71 sections.

| Examples (sections) | Mean | Median | 2 | 3 | 4 | 5 | 7 | At least 4 |
|---|---|---|---|---|---|---|---|---|
| Kept: 5,462 (71) | 2.90 | 3 | 1,846 | 2,615 | 693 | 308 | 0 | 18.3% |
| Left out, no usable amp track: 3,151 (41) | 3.71 | 4 | 307 | 307 | 2,537 | 0 | 0 | 80.5% |
| Left out, over the cap: 109 (2) | 7.00 | 7 | 0 | 0 | 0 | 0 | 109 | 100% |

- **The left-out examples are denser:** mean 3.82 against 2.90 (at least 4: 81% against 18%).
- **Mostly one band:** Rebuild The Evil gives 2,308 of the 3,260 left-out examples, all at 4. The rest:
  - Ale Lak: 152 at 4, 109 at 7;
  - Death Of A Romantic: 307 at 2 (left out for a single unrenderable guitar, not for density);
  - Hollow Ground: 307 at 3;
  - The Long Wait: 77 at 4.
- **V-real is denser than T2's kept training data:** 9 of its 10 parts have at least 4 guitars playing, against 18% of
  the kept examples.

**Option (c), the SES-ALL arm** (approved above):
- **The draw** (`plan-ses-all`, zero renders, writes `t2/ses-all.json`; `--dry` prints only): 5,000 examples from the
  8,414 candidates outside early stopping, the pilot's size.
  - **Scope (the build's interpretation; the ML session confirms it matches the intent it suggested):** N is kept
    equal to SES's, so SES-ALL − SES reads what the left-out sections are worth at equal size, not more data. The
    left-out share is about 39% either way (3,260 of the 8,414 candidates; 1,946 of the 5,000 drawn).
  - Stratified by band with a new declared seed, 20261104 (`SES_ALL_SEED`).
  - Drawn from every T2 candidate before rule 1 and the cap (the trusted pool outside Eggy, on verified DIs and
    sections T0 lets a mix use), outside T2's early-stopping sections.
- **Early stopping:** SES's set, with the shared refusals. The recipe and seeds are SES's (20261042, 20261043).
- **N can differ slightly:** SES drops the pilot examples any arm refused (shared with SYN, to stay paired), while
  SES-ALL keeps its whole draw (its stored stems need no render), so SES trains on 5,000 less those refusals.
- **The guard** (`ses_all_guard`): the draw must stay inside the D build's trusted pool, outside T2's early-stopping
  examples and sections, and off the bands of V-real, V_sep, stage F and the known-answer set. `direct_stems.Ctx`
  already refuses pool bands that overlap V_sep, stage F or the known-answer bands, and every held-out DI.
- **The dry run** (log `logs/ses-all-plan-dry-2026-10-25.log`, nothing written): 8,414 candidates outside early
  stopping.

  | Band | Drawn |
  |---|---|
  | Ale Lak | 475 |
  | Death Of A Romantic | 1,142 |
  | Hollow Ground | 1,097 |
  | Rebuild The Evil | 1,372 |
  | Storm Of Particles | 868 |
  | The Long Wait | 46 |

  The draw spans 6 bands; its 1,946 left-out examples (1,891 with no usable amp track, 55 over the cap) come from 5
  (all but Storm Of Particles). 2,966 are also in SES's pilot.
- **The read:** SES-ALL − SES on V-real, paired by direction, band-weighted, 90% band-clustered, with SES-ALL − S
  beside. `report` reads it on its own: T2's primary reading does not wait for it.
- **Caveat: the left-out data are mostly one band.** SES-ALL − SES mixes "the dense sections" with "two more bands"
  (Rebuild The Evil is 27% of SES-ALL's draw, The Long Wait 1%) and a band mix that is no longer the pilot's. A
  difference says what the left-out sections are worth together, not density alone. The Long Wait carries a MUSDB18
  artist tag, like Hollow Ground's Ill Fate (MUSDB18 test) in the pilot; the tags matter for readouts, not training.
- **What is added, never re-made:**
  - `fit` keeps an arm already fitted on the same models;
  - `vreal-predict` keeps the stored arms' answers and adds SES-ALL's (it refuses other V-real directions, changed
    inputs, or a kept arm whose recorded models differ from fit.json's; T2's own arms have no recorded models);
  - `vreal-render` renders SES-ALL alone into `vreal/groups-added/SES-ALL/`, one priming render per group, and leaves
    the groups' records as they are.
- **The extra cost:** 2 training runs of about 1.5 h; about 60 V-real renders plus 30 priming; zero separations (SES's
  stems are stored).

**`report`:**
- labels T1's 812-example read superseded (`t1 (superseded)`, not read) and carries the stem read. T2's own
  report.json, written by T2's chain with the code before this change, keeps the unlabelled `t1` key; the label
  arrives with the follow-up's report;
- adds diagnostic (a) (the parts' counts and the contrasts by side and by count);
- lists SES-ALL's gaps apart from the primary's.

**The follow-up chain** (`docs/trusted-data-t2-followup.sh`, after T2's chain prints "T2 CHAIN DONE" and the PR is
merged):
1. Refuse if T2's report lists V-real groups not done (SES-ALL is never rendered into a group's own record); copy
   fit.json, report.json and predictions.json aside.
2. `t2-stem-read` and `t2-density` (non-fatal: a failure is logged and the chain goes on), `plan-ses-all`.
3. `train --arm SES-ALL` for both seeds.
4. `fit`, `vreal-predict`, `vreal-render --shard k/3`, `report`.

## T0 window re-check (2026-10-25)

**Why.** 42 of 59 targets were excluded. A re-check (zero renders) found that some failed A5 or A6 only because their
one 10-s crop window caught the DI silent or barely playing. On other windows where the DI plays, the same unchanged
measures pass. The re-check's code reproduced the stored crop measures for all 16 parts it read (except A1–A3 of
Prodigal ElecGtr1 and 2 and Signs ElecGtr6, whose stored values came from the level prior's sections). Amended after
an independent review the same day: the rule is stricter than first drafted, because the user prefers reliable data.

**The rule (amends the standard's "a measured fail of A1–A6 excludes"):**
- **Eligible:** a target that fails A5 or A6 only because its DI is silent or sparse in the crop window (play share
  < 0.5 in a half), and whose measure DI did not fail D2 in T0 (`verified.json`'s `measure_dis`, not `targets[].why`).
- **Windows, fixed before measuring:** other 10-s windows chosen only from the DI: play share ≥ 0.5 in both halves
  (with the window's loudest DI frame within 20 dB of the DI's playing level, and no overlap with the crop), spread
  across the song (the candidate nearest the middle of each fifth, filled from the farthest if a fifth has none), up
  to 5. Every window checked is counted and reported.
- **Pass:** at least 3 windows, and no measured fail on any of them under the unchanged A1–A6 and D2 ("ear" readings,
  such as A2's, allowed, as for verified parts).
- **Then the ear:** the user hears 2 of those windows, as before (DI, then target; each window's two halves).
- **Still excluded:** a part that fails on a real track property (hum or clipping, no cab, live-room bleed, a
  different take).

**D2 is weak where the DI plays almost throughout.** D2's hum reads against the DI's 10th-percentile floor; when the DI
plays on about 95% of a window that floor is guitar, which masks hum. Drag Me Down ElecGtr3's DI failed D2 for hum in
T0 (−40.96 dB) yet reads −57 to −65 dB on its new windows; It Was My Fault ElecGtr4 at 90 s reads −275 dB, a
degenerate value. Hence eligibility goes by T0's measure-DI verdict, not by the new windows' D2.

**The result** (16 parts read; per-window numbers in
`~/ndsp-presets/listening/trusted-data-ear/part5-recheck/recheck/results.json`): **3 recovered, pending the ear; 13
stay excluded.**

| Part | Windows with no measured fail | Reading |
|---|---|---|
| It Was My Fault ElecGtr1 | 5/5 | recovered, pending the ear (crop half A plays 26%) |
| Nosso Mundo ElecGtr03 | 3/3 | recovered, pending the ear (crop half A silent; sparse DI, only 3 windows exist) |
| Signs ElecGtr6 | 5/5 | recovered, pending the ear (crop half B silent). Its measure DI is pending the ear too (D4 flags it, unheard); the ear-only D4 flags 2 of the 5 windows |
| Drag Me Down ElecGtr3 | 5/5 | excluded: its measure DI failed D2 for hum in T0 (not eligible; see above) |
| It Was My Fault ElecGtr4 | 4/5 | excluded: the 171-s window fails A1 (half-B lag 0.021 ms). Its measure DI is unheard (pending the ear) |
| Today's The Day ElecGtr07 | 1/5 | excluded: its crop DI plays fully, so the rule does not apply, and its measure DI failed D2 for hum (4/5 windows too). The user's decision of 2026-10-24 stands |
| Prodigal ElecGtr1 | 0/5 | excluded: DI hum on every window (target measures pass on 5/5) |
| Prodigal ElecGtr2 | 0/2 | excluded: DI plays about 30 s; one window D2 hum, one A1 near-zero lag |
| Prodigal ElecGtr3 | 0/5 | excluded: no cab (A1 0.0 ms, A2 0 dB on every window) |
| Prodigal ElecGtr4 | none | excluded: DI plays only about 4 s; no window qualifies |
| Passing Ships ElecGtr3 | 0/2 | excluded: DI hum on every window |
| Passing Ships ElecGtr4 | 1/5 | excluded: measure-DI hum and hiss (D2 fails 3/5), heard not clean |
| Measurements GTR (Telefunken) | 0/5 | excluded: live-room bleed −6 to −23 dB on 4/5 windows |
| colour-me-red elecgtr01 | 0/5 | excluded: DI hum and clipping on every window |
| magilla elecgtr1dt | 0/5 | excluded: DI hum on every window |
| wickerman elecgtr7 | 0/5 | excluded: hum-suspect DI (D2 fails every window) |

**Which audio a recovered part uses:** only its passing re-check windows. Its old crop is not used; the crop is re-cut
to a passing window, the one the user's ear verifies. This does not change K's backing: K's other guitars are DI renders
on windows T0 measured for each DI (D2 per window), and the amp tracks rule 1 adds pass their own bleed check; neither
reads a target's verdict (K is empty anyway since T1 was waived). None of the 3 is a V-real part. *Corrected
2026-10-26:* It Was My Fault ElecGtr1 is a knob-ceiling-2 candidate; it stays off that panel (its old crop is not used).

**The ear.** `~/ndsp-presets/listening/trusted-data-ear/part5-recheck/index.html`: 22 cards, the same cards and export
as part 1. It was built before the review, so it also holds Drag Me Down ElecGtr3, It Was My Fault ElecGtr4 (2 windows
each) and Today's The Day ElecGtr07 (1); their answers are informative only and recover nothing. Its export is page
`trusted-data-ear-recheck`, with its own item ids (`items.json` beside it), so `lists --ear` refuses it until the rule
is in code.

**When they join.** A recovered part joins the verified set only after the user's ear, and only after T2's chain
finishes: T2 runs on the current lists, which must not change mid-run. The rule goes into `verify_tracks` then
(code, reviewed), and `lists` is re-run with every export. *Done 2026-10-26: 2 recovered, Signs ElecGtr6 pending its
DI ([parts 5 and 6](#parts-5-and-6-heard-2026-10-26)).*

## T2 outcome (2026-10-26)

T2's chain reported at 02:54 on 2026-10-26, then the follow-up chain ran. An independent audit recomputed every row
below from `t2/vreal/groups` (and SES-ALL's added groups); all match. Rows are log(d_a/d_b), lower is better,
band-weighted with 90% band-clustered intervals, 7 bands unless noted (logs `t2-report.log`,
`t2-report-followup.log`, `t2-stem-read.log`, `t2-density.log`, `t2-ses-all-plan.log`; `t2/fit.json`).

**The additions were declared before any result:** committed at 3740e70 (2026-10-25 19:05), before T2's report.

**The primary, SYN − SES on V-real: +0.019 [−0.001, +0.040].** A tie under the declared rule (|point| < 0.03), so
SYN is picked by recorded decision 4; the interval holds 0, so the proposed interval rule reads a tie too. It is not
"equal": SYN leans worse, 5 of 7 bands lean to SES, and every leave-one-band-out mean is +0.013 to +0.026. The upper
bound exceeds D's margin over S (−0.034).

| Row | Point [90%] |
|---|---|
| SES − constant | −0.031 [−0.068, +0.005] |
| SYN − constant | −0.012 [−0.045, +0.021] |
| SES − S | +0.012 [−0.061, +0.084] |
| SYN − S | +0.031 [−0.039, +0.101] |
| constant − S | +0.043 [−0.015, +0.101] |

Neither arm beats S or clearly beats the constant. Caveats:
- each arm's pull was fitted on the shared 278-example early-stopping set (4 sections), built in its own arm's mix
  (median b SES 0.79, SYN 0.44),
  so the contrast includes the pull;
- seed noise is not in the interval;
- the 2-band rows (F-song, class clean) are descriptive only;
- the − S rows use stored S judges, not re-rendered.

**Data integrity:**
- 334 near-silent refusals (rule 2), applied identically to every arm (5,000 + 308 drawn; 304 + 30 near-silent
  refused = 334);
- all 4 runs used the same 4,696 training and 278 early-stopping examples;
- a second CPU build worker ran from 00:49; 1 build by both workers, matching to within 1e-6 dB; 78 refusals logged twice;
- `e-on-k` refused on T1's stale lists hash (T1 waived, K empty); it does not touch T2;
- training was healthy: best epochs SES 21 of 26 and 23 of 28, SYN 20 of 25 and 29 of 34.

**SES-ALL − SES: −0.026 [−0.070, +0.018]; crunch −0.045 [−0.099, +0.009] (5 bands).** Descriptive, and not a clean
density test:
- the draw adds 2 bands SES never saw (Rebuild The Evil 1,372, The Long Wait 46);
- it shares only 2,966 examples with SES;
- it trains on 5,000 against SES's 4,696, including 175 that SES dropped as refusals;
- its pull differs (median b 0.94);
- it rests on one band (Zeno −0.127; without it −0.009);
- it was rendered in a separate session, with no repeat render.

So it reads as "a broader draw (more bands and denser sections) leans better", not "dense sections help". SES-ALL − S
is −0.014 [−0.085, +0.057], the first T2 arm to lean past S; its interval holds 0.

**Diagnostic (a):** SES − S dense −0.050 [−0.189, +0.089] (3 bands), sparse +0.058 [−0.048, +0.165] (4 bands).
Nothing shown, and confounded with band: no band falls on both sides. **Diagnostic (b):** as read before
([as built](#t2s-additions-as-built-2026-10-25)): the left-out candidates are denser.

**The stem read (a ceiling check only):** SYN − SES mel SNR −0.80 dB [−1.12, −0.47] section-clustered (71 sections,
the declared primary), −0.56 [−1.78, +0.66] band-clustered (4 bands). SYN's stems are not cleaner than SES's, so SYN
is not shown to be unrealistically easy. Not a realism verdict, and the band-clustered interval holds 0.

**Next:** decision 5, whether T3 runs on a tie, is open for the user. Pending inputs: the window re-check's 3
recovered parts and the new bands' 4 DIs await the user's ear (PR #293, PR #294). The clean/crunch shortage stays the
clearest gap. *Heard 2026-10-26: 2 targets recovered (a third pending its DI), 1 new training DI (high gain) ([parts 5 and 6](#parts-5-and-6-heard-2026-10-26)).*

## Parts 5 and 6 heard (2026-10-26)

The user heard both pages on 2026-10-26. Exports: `learn/trusted-data/ear-exports/part5-recheck-2026-10-26.json`
and `part6-new-bands-2026-10-26.json`. One `lists` run read them with every earlier export (log
`learn/trusted-data/logs/lists-ear56.log`; `t0/` backed up first to `t0-backup-before-ear56-20261026-083849`).
Nothing was superseded, cleared or skipped.

**How `lists` reads them (code).** `ear_answers` takes both pages, each decoded through its own `items.json`. A
build that doesn't match is refused. On each card the latest touch stands, as on the ear queue's pages.
- Part 5's answers stay apart from the crop's answers.
- `recheck_eligible` and `recheck_verdict` apply the re-check rule above to the re-check's `results.json`.
- `recheck_measure_di` reads part 8 (`trusted-data-ear-signs-di`, below): DI cards for a recovered part's measure DI
  on its re-check windows.
- `intake_verdicts` reads the intake's checks (`intake-2026-10-25/summary.json`) with part 6.
- `verified.json` gains `recovered_targets`, `intake_dis` and `intake_admitted`.
- `clean_di.inventory` swaps an admitted DI's `INTAKE_PENDING` note for `INTAKE_ADMITTED` (PR #294's design). Only a
  real `lists` run admits.
- `verified.json` was not edited by hand.

**Part 5, the window re-check: 2 targets recovered, 1 pending.** All 22 cards were heard "clean amp".

| Part | Band | Windows (no measured fail) | Heard | Crop re-cut to | Now |
|---|---|---|---|---|---|
| It Was My Fault ElecGtr1 | Atlantis Bound | 5/5 | 90 s, 125.5 s | 90–100 s | verified |
| Nosso Mundo ElecGtr03 | Ale Lak | 3/3 | 52.5 s, 123.5 s | 52.5–62.5 s | verified |
| Signs ElecGtr6 | Zeno | 5/5 | 63.5 s, 82 s | 63.5–73.5 s (D4 passes there) | pending: its DI on part 8 |

Each keeps only its passing re-check windows (`targets[].recheck.windows`), less any window D4 flags until its DI is
heard clean there as a DI. Its old crop is not used. So a recovered
part joins no list read from the crops: not V-real, not knob ceiling 2, not the level prior. It Was My Fault ElecGtr1
is a knob-ceiling-2 candidate (the re-check section above missed this). It stays out of that panel until its crop is
rebuilt on the new window. Its band is already on the panel through ElecGtr2.

The other three stay excluded under the rule; their answers are informative only:
- Drag Me Down ElecGtr3: its measure DI failed D2 for hum in T0;
- It Was My Fault ElecGtr4: A1 fails on the 171-s window;
- Today's The Day ElecGtr07: its crop DI plays, so the rule does not apply.

**Signs ElecGtr6's measure DI stays pending the ear** (fixed after the PR #296 review). It was pending because D4
flagged the old crop, where the DI plays 10% of half A. The DI played first on every re-check card, but those cards
judged only the target and offered no "processed" answer, so the DI itself was never judged.
- Signs ElecGtr6 stays pending, and its measure DI stays pending (`measure_dis`).
- Its windows: 63.5, 123.5 and 200.5 s, where D4 passes. 82 s and 148 s, which D4 flags, wait for the DI ear
  (`windows_waiting_di_ear`).
- **Part 8** (`~/ndsp-presets/listening/trusted-data-ear/part8-signs-di/`, page `trusted-data-ear-signs-di`) holds 3
  DI cards for 33_ElecGtr6DI at 63.5, 82 and 148 s. These are part 6's DI cards (clean, processed, not a DI, hum, not
  sure). The clips are not silent: decoded peaks −8.2, −8.0 and −7.7 dBFS.
- When `lists` reads part 8's export:
  - a window heard other than clean excludes the part;
  - a window heard clean clears the measure DI and verifies Signs;
  - a D4-flagged window joins its windows only once heard clean.
- *Heard 2026-10-26: all 3 windows clean. Signs ElecGtr6 is verified on all 5 windows
  ([outcome](#parts-7a-7b-8-and-9-heard-2026-10-26)).*

**Signs ElecGtr6 is not a copy of its DI** (the user asked for a double-check). On the 5 re-check windows:
- A4's highest correlation with the DI is 0.70–0.75, against the < 0.95 rule;
- the two files' hashes differ;
- the mic sits 0.79–0.81 ms behind the DI on every window and half, a steady close-mic delay;
- A2 passes outright (a cab roll-off), which no copy shows;
- A3's best linear filter leaves −19.5 to −24 dB, inside the −2 to −27 dB of the calibration's known amps. The
  calibration's copy negatives sit at −71 to −93 dB, and A3 fails anything under −40.

So it is a very clean, close-miked amp, not the DI.

**Part 6, the new bands: 1 new training DI from 5 bands.** Ember Rev, Sören and Empty Signifier ElecGtr1DI were
already out on measured fails.
- **Empty Signifier 20_ElecGtr2DI: admitted.** Heard clean on both windows. Its amp track (19_ElecGtr2Mic3) was heard
  as high gain on both. Part 6 had no DI-and-amp pair card, so its "D1 to the ear" is cleared differently: the DI card
  (which offers "not a DI") heard clean, plus the amp track heard as an amp tone. **The DI-and-amp pairing itself was
  never heard.** Hear it before anything uses that amp track (`intake_dis[].pair_unheard`). It is a high-gain DI, so it
  does not ease the clean/crunch shortage.
- **Mòpia 19_ElecGtr2DI and 21_ElecGtr3DI: excluded,** heard processed on all 4 windows. Both amp tracks were heard
  high gain.
- **Goran Levi 12_ElecGtrDI: excluded,** heard processed (and D1 had already failed). Its amp track was heard clean,
  with drum and bass leaks (the user's notes). It is a processed copy of the DI anyway.

**The lists now** (`t0/verified.json`, 2026-10-26):
- targets 19 verified, 1 pending (Signs ElecGtr6, its DI on part 8), 39 excluded;
- T0's DIs 46 verified, 13 excluded (unchanged);
- intake 1 admitted, 8 excluded;
- V-real unchanged: 10 parts in 7 bands;
- knob ceiling 2 unchanged: 7;
- T0's training pool unchanged: 27 DIs, 181 sections;
- level prior and stems unchanged.

Empty Signifier's DI trains once the DI inventory is rebuilt (`clean_di inventory`) and a training draw includes it.
Nothing does yet.

## T3 (declared 2026-10-26, nothing run)

**What it is.** One rebuild that is also every-control stage 2D
([amendment 2](every-control-plan.md#amendment-2-2026-10-26-stage-2d-is-t3-and-its-label-space)): the direct model
trained on self-built mixes (SYN, picked by T2's tie under recorded decision 4) with labels over every Morgan control,
read on V-real. The user approved going ahead on 2026-10-26 (decision 5). Declared before any T3 data: the counts
below come from T2's stored plan and T0's lists, and nothing was rendered, separated or trained. No code is written
yet. K is empty, so T3 reads nothing on K. *F5 ran 2026-10-26: the gate read +0.079, not shown
([F5 outcome](#f5-outcome-2026-10-26)).*

**Two steps, cheapest decisive first:**
- **F5, the paired pilot.** T2's own examples, re-rendered with full-space labels, against a today's-space model on
  the same examples. It isolates what every control is worth, and gates the full build.
- **F20, the full build.** About 20k examples on every trusted section, and the primary read.

### 1. The label space

[Amendment 2](every-control-plan.md#amendment-2-2026-10-26-stage-2d-is-t3-and-its-label-space) declares it:
- **115 Morgan controls:** 86 continuous, 26 switches, amp choice (3-way) and the two mics (10-way). 77, 81 and 77
  sound with PR12, SW50R and AC20. Today's space is 25.
- **Encodings:** continuous on the unit interval, log for frequencies and times. Amp choice is a head that reads the
  audio only. The spring is a derived switch plus its level. Output gain is fitted to loudness, not a head
  (confirmed by the user 2026-10-26).
- **Switched-off features:** their knobs are masked out of the loss, E, the constant and the pull, and written at
  neutral in an answer.

### 2. Data

**Sources:**
- **DIs:** T0's verified training DIs (27 in 8 bands). Empty Signifier 20_ElecGtr2DI joins: the ear admitted it
  (PR #296, merged), and it trains once the DI inventory is rebuilt. So does any new source the user approves, after
  T0's checks and the ear.
- **The metal and hard-rock intake** (downloaded with the user's yes on 2026-10-26; its ledger entry lands on merge
  of #297): 13 Cambridge-MT sessions in 7 bands, 89
  electric DIs by file name (Arcadian Alone, Daimon B, Dark Illusion, Inhumanity Vortex, Peppermark, Serapis, DGX;
  V.M.GY was left out as a set-3 held-out band).
  - Each DI that passes T0's checks and the user's ear is an eligible training band under F20's caps (high-gain
    sources at most 50%, a band at most 35%). Parts heard "too heavy" are left out.
  - T2's follow-up (SES-ALL, a broader draw with 2 more bands) leaned better, so more training bands may help.
  - DGX's sessions are DI-only, so rule 1 keeps them where every playing guitar's DI passes. **Decision (the
    coordinator, 2026-10-26; the user may overrule):** DGX's DIs have no amp track for a tone card, so they join
    once heard clean and count as high gain under the 50% cap (the site labels them hard rock/metal, not extreme).
  - The metal intake's tone card classes only its own DI (`tone_class`); the session's other DIs carry the class as
    `session_tone` only, and an unclassed metal DI counts as high gain (above).
  - **Rule 1 must honour `pair_unheard`:** no metal card played a DI with its amp track (68 of the 78 DIs on the
    pages never have their own amp track heard at all), so a verified metal DI's amp track is not used as an active
    guitar's stand-in until its pairing is heard.
- **Kept out:** K's bands (Adam Buckley, Dark Ride) and Cnoc An Tursa, so that K can come back; set by the ML
  session, the user may overrule. Every reservation in the ledger, and V-real's bands.
- **Rule 1 and the cap of 4 apply unchanged.** No amp track has passed the bleed check, so Rebuild The Evil and The
  Long Wait stay out.
- **Renesans** joins only after two fixes: the `session_guitar_parts` bug (GTR 2 Amp read as GTR 1's own take, from
  the review of #290) and its stems settled.
- **What is certain** is T2's 71 sections in 4 bands. **F5's first step is the zero-render dry run**
  (`plan --stage t3 --dry`). It prints the real pool by band and gain group before any render: Renesans (up to 37
  sections); Empty Signifier (its ElecGtr1 DI was excluded for hum, so sections where ElecGtr1 plays leave unless its
  mic tracks pass the bleed check); and the metal intake's admitted DIs. F20's own `plan` prints it again with
  whatever the ear has admitted by then.

**The sets:**

| Set | What | Examples |
|---|---|---|
| **FS5**, early stopping and fit | T2's 4 early-stopping sections plus 2 more per band from T2's sections (seed 20261105): 12 sections in 4 bands, with T2's examples on them | about 800, against T2's 278 in 4 sections |
| **F5**, the pilot | T2's 4,696 training examples less those on FS5's 8 new sections | about 4.2k |
| **FS20** | FS5 plus 1 section per new band that has at least 4 sections (seed 20261105), about 70 new draws each | about 800 + 70 per new band |
| **F20**, the full build | F5 plus new draws on every trusted section outside FS20 | 20,000 |

**How a new example is drawn** (ids from 3,000,000, so no draw repeats part C's):
- **Today's space:** part C's draw, as is: amp uniform; base class clean or crunch, 50/50; modes factory 0.4, start
  0.2, wide 0.4.
- **The new controls:** a separate stream (seed 20261107 per example), in the same mode, as the plan declared:
  - factory: the same factory preset, now un-dried, so effects come at factory rates;
  - start: S's values (dry);
  - wide: uniform in unit space, each switch on with p 0.5.

  The gate threshold's wide draw stops at the factory presets' 95th percentile (computed from the menu and printed),
  so most wide gates don't silence the DI. A wide draw with both cabs off is redrawn (the plugin needs one cab on).
  The spring's derived switch is a switch like the others: on with p 0.5 in a wide draw, its level then uniform above
  0; in factory and start draws it is on when the preset's level is above 0.
- **F5's twins:** each F5 and FS5 example keeps its T2 draw for today's space and every mix draw, and takes the new
  stream for the rest. Its other-guitar renders, stems and pans are T2's stored ones. So each core twin (T2's stored
  SYN build) and its full twin differ only in the target's new controls.
- **F20's new examples:** their other guitars draw full-space presets too (seed 20261102 per example and DI, as T2).
- **The positive control:** 50 F5 examples rendered with the new controls at S's values must reproduce T2's stored
  target mels (T2's match share). They are then carried through the build and separation, and their mix and stem
  features must match T2's stored files at the same share, so the whole pipeline, not only the renderer, repeats T2.
- **The DI level:** every DI section, in training and on V-real, is measured to the yardstick's −22.9 LUFS
  (`song_bank.measure`, as part C and T2) before it is rendered. Gate thresholds and the output-gain fit are read
  against that level.

**Balance:**
- **Band:** new draws are equal per section within each gain group, and no band holds more than 35% of F20.
- **Class:** the base class is 50/50 clean and crunch (part C's draw).
- **High gain must not swamp clean and crunch:**
  - **Every section gets a gain class at zero renders, before any split,** and `plan` prints it by band. In order:
    part A's class; else the intake's ear call (`ear_call`), in this order:
    - the DI's own amp track's tone card (Empty Signifier ElecGtr2 and the metal intake's tone cards: clean, crunch,
      high gain);
    - for a **DI-only intake DI** (no amp track of its own; Strobe and MekaPhil, part 9), the playing style heard on
      its DI card (`style_class`: clean/crunch-style or high-gain-style);
    - for a DI-only intake DI with no style answer, its song's tone (`song_tone`; part 9's tone card on the song's amp
      track with no DI, heard alone: clean, crunch or high gain);
    - the session's tone card (`session_tone`; only a card that played a DI's own amp track sets it);
    - the DI-only rule (`no_tone_counts_as`). For DGX and the metal sessions it is high gain. For Strobe's and
      MekaPhil's DI-only DIs (part 9) with neither a style nor a song tone it is **"unknown"** (`B2_NO_TONE`; the
      user, 2026-10-27: these songs have no target to hear the tone in).

    **"Unknown" is its own gain group.** It counts neither as high gain nor as clean/crunch: `hg_share` leaves it out of
    both sides of the high-gain cap's sums, and `plan` prints it as its own group.

    Else part A's classifier runs on the section's own amp track. A section still
    unclassed counts as high gain if its band came in through the metal intake, and as not high gain otherwise (T2's
    unclassed bands, Ale Lak and Storm Of Particles); that is a stated limit.
  - The new draws are split so that **F20 holds at most 50% high-gain-source examples** among examples of known
    group ("unknown" is left out of the sums). T2's examples were 61%.
  - **F20's draws hold at most 25% "unknown" sections** (`UNKNOWN_CAP`; a design constant of 2026-10-27, which the
    user may overrule). `plan` prints the high-gain share both ways: with unknown left out, and with unknown counted as
    high gain (the worst case), beside the unknown share against the cap (`hg_shares`).
    F5 keeps T2's mix, which keeps its pairing.
  - Each target's rendered gain class is measured as part C did, at zero renders. If high-gain renders exceed 40% of
    F20, the training sampler down-weights them to 33%.
- **The tests stay clean and crunch:** V-real is all clean and crunch, read per class. The interference check (4)
  reads what the high-gain sources do to it.

**Refusals:** rule 2 as in T2 (a render below −50 LUFS refuses its example). At F5 a refusal in either twin drops the
example from both.

**Separation:** X-LANCE gtr_mss (`xlance_g`), as T2. The MPS worker and the CPU worker run in opposite orders.

**Render budget and disk:** in the cost table (6). F20's audio is about 1.5 MB an example (target and other-guitar
FLACs, as T2's 7.5 GB for 5.3k), so T3 adds about 31 GB. That leaves about 53 GB free of today's 84 GB, about 43 GB
with the metal intake extracted, above the 31 GB guard. `plan` refuses if the projection falls under the guard plus
5 GB (36 GB).

**V-real grows to up to 12 parts, where eligible.** The window re-check recovered targets (PR #296, merged):
- **It Was My Fault ElecGtr1** (Atlantis Bound, clean) is eligible: its band is already a V-real band and never
  trains. **Signs ElecGtr6** (Zeno, clean) is eligible on the same grounds **only if part 8 clears its DI** (it is
  pending until its DI is heard as a DI).
  - Each gets a stage-F-style crop on its heard window (90–100 s; 63.5–73.5 s): the unity sum of the session's
    tracks and the measure DI, built as stage F's crops were.
  - S is rendered on each (6 renders per part).
- **Nosso Mundo ElecGtr03 is not eligible:** Ale Lak trains.
- **With Signs, V-real-12:** 12 parts in 7 bands; clean 5 parts in 3 bands (Atlantis Bound, Diesel13, Zeno; 2 df),
  crunch 7 parts in 5 bands. **Without it, V-real-11:** clean 4 parts in 2 bands (1 df, so the clean row is
  descriptive only, as at T2), crunch unchanged.
- **Membership is frozen** in T3's `plan.json` at F5's plan step, before any T3 read on V-real. A later ear sitting
  cannot change it: if part 8 has not cleared Signs' DI by then, Signs stays out of all of T3. A part whose crop then
  fails to build under T0's rules on its window is dropped before any V-real read, and the drop is printed.
- V-real-10 rows sit beside every read, for comparison with T2.
- *Part 8 was heard after F5's plan froze V-real-11, so T3's membership stays V-real-11, without Signs. A future plan
  not bound by T3's freeze would see V-real-12 ([outcome](#parts-7a-7b-8-and-9-heard-2026-10-26)).*

### 3. Model and training

**The recipe:** D_stem's (`direct_stems.train_arm`, augmented, the stem's mels, the mix input zeroed) on `song_model`'s
network.
- The heads widen to the full space, as amendment 2 declares: the masked loss, and an amp head before the condition.
- The other knobs stay conditioned on the amp and the class.
- Max 40 epochs; patience as D_stem's. A run whose best epoch falls within 4 of the cap is extended before it is read
  (T2's rule).

**Runs and seeds:**

| Model | Trains on | Labels | Seeds | Stops and fits on |
|---|---|---|---|---|
| **D_core5**, the today's-space model | F5's core twins (T2's stored SYN builds) | today's 25 | 20261042, 20261043 | FS5, core twins |
| **D_F5** | F5's full twins | 115 | 20261042, 20261043 | FS5, full twins |
| **D_F20**, T3's model | F20 | 115 | 20261042, 20261043, 20261044 | FS20 |
| **D_noHG** | F20's examples on sections not classed high gain (about 10k) | 115 | 20261042, 20261043 | FS20 |
| **D_mixN** | the same number drawn from all of F20, at F20's mix (seed 20261108) | 115 | 20261042, 20261043 | FS20 |

D_core5 and D_F5 share examples, sections, backings, mix draws, today's-space labels, seeds and fit sections. Only the
target's new controls and their labels differ. D_core5 also lacks the amp head and the wider heads, so F5 measures the
every-control package (the new controls in the audio, their labels and the heads that learn them), not the labels
alone.

**The readout:** amendment 5's, extended:
- A1, the mixture median per seed; A2, the median over seeds; A3, the pull.
- Switches by the mean probability over seeds (on above 0.5), mics and the amp by the argmax of the mean.
- A feature the answer switches off is written at neutral.
- **Amp-fixed answers:** one per amp, the knob heads conditioned on it. **Own-amp answer:** the amp head's choice, so
  it is one of the three and costs no render.
- **Output gain:** fitted per answer to the loudness target (amendment 2; confirmed by the user 2026-10-26).

**The pull, fixed** (T2's audit: each arm's pull was fitted on its own mix of a 278-example, 4-section set, so the arm
contrast included the pull):
- **Shared:** every model in a contrast is fitted on the same sections and examples, built in the same mix type. All
  T3 models are SYN. D_core5's fit set is FS5's core twins, which differ from D_F5's only in the new controls.
- **Larger:** 12 sections and about 800 examples at F5, against 4 and 278; FS20 adds the new bands.
- **With and without:** every model contrast is also read on A1 + A2 answers, with no pull.
- **Stable:** b is refitted on FS's two section folds (amendment 5's check) and both are printed. Descriptive.
- **The constant** comes from each model's training labels (per amp and class: medians over sounding labels, switch
  majority, mic mode), as T2's.

### 4. The readout on V-real

- **Every row:** log(d_a / d_b) by the judge with the measure DI, paired per part, amp and direction as T2 read V-real.
  Band-weighted, 90% band-clustered t (7 bands, 6 df); lower is better.
- **Per class:** clean (3 bands with Signs, 2 df; 2 bands without, descriptive) and crunch (5 bands). V-real-10 beside every row.
- **Seed noise:** each seed's answer alone, for T3's model and the F5 pair (descriptive; T2's interval lacked it).
- T2's |point| < 0.03 tie rule is not used.

| Row | Read at | What it says |
|---|---|---|
| **D_F20 − S (primary)** | F20 | does T3 beat the starting preset, amp-fixed (S on the same amp) |
| **D_F5 − D_core5 (the gate)** | F5 | what every control is worth, everything else equal. Both per-seed-pair contrasts (seed 20261042 against 20261042, 20261043 against 20261043) are printed beside, each with its sign split over bands |
| D_F5 − S, D_core5 − S, D_F5 − constant | F5 | as T2's rows |
| D_core5 − D_SYN (T2's stored models, with their own pull) | F5 | what the moved sections and the new fit set change; descriptive |
| D_F20 − constant | F20 | the song against the constant's pull |
| D_F20 − D_F20 with the new controls at S | F20 | the new controls' own worth within one model (the 2D pilot's primary) |
| Amp choice: D_F20 own amp − the mean of its three amp-fixed answers; own amp − S averaged over the three amps | F20 | stage 0b's reading, for the model |
| D_F20 − D_F5; D_F20 − D_core5 | F20 | size and new bands; everything at once. Descriptive |
| **Interference: D_F20 − D_noHG** (deciding: adding high-gain sources), overall and per class; D_mixN − D_noHG beside (equal size, descriptive). D_F20's and D_mixN's high-gain share draws from every eligible high-gain band (the metal intake's included); D_noHG drops them all. `report` prints the bands each arm trained on | F20 | does high-gain-source data hurt clean and crunch (above 0 means it does) |
| Families: the answer minus the answer with one family at S (EQ; pedals; time effects and spring; gate and doubler; cab rest) | F5, F20 | each family's worth; sets priorities, never membership |
| \|LUFS error\| of the output-gain fit | F5, F20 | a pipeline check, not an arm contrast: the fit reads the stem's loudness, so the error is the same for every arm |
| E on FS per family, model against constant (zero renders, section-clustered) | F5, F20 | whether each family is read from the mix at all (the known-answer read K would have given) |

### 5. The decision rule, power and next steps

**The rule (the user's):** every row is an effect size with its interval. There is no pass bar, and any gain is built
on. Interval below 0: shown. Point below 0 with the interval holding 0: leans better, built on, and called not shown.
Undecided is not failed.

**Power** (T2's observed half-widths at these 7 bands; about 1.5× is the 80%-power effect):

| Contrast | 90% half-width | Effect seen with 80% power |
|---|---|---|
| Paired models (D_F5 − D_core5) | about 0.02–0.035 | about 0.03–0.05 |
| Interference (D_F20 − D_noHG; different examples, not paired) | about 0.045 | about 0.065 |
| Model − constant | about 0.035 | about 0.05 |
| Model − S | about 0.07 | about 0.10 |

For scale, with the true DI: amp choice −0.048, the amp EQ on top of the knobs −0.079, the pedals and time effects
about −0.01 each. T2's models did not beat S. So a lean is the likely result for the primary, and the paired gate is
the sharpest read.

**Next, on each outcome:**
- **The gate, D_F5 − D_core5:**
  - point below 0: F20 runs (the user's OK on this plan covers it);
  - at or above 0: stop and report. F20 runs only with the user's yes, as the every-control plan's 2D tie rule. The
    family and E rows show where it fails.
- **The primary, D_F20 − S:**
  - point below 0: D_F20 becomes the direct route's model. T4 follows (V-real with JHNC, then the ear), and the
    real-mix test runs on it;
  - at or above 0: not adopted. The beside rows say where it falls short (the constant: data; the new controls; amp
    choice; seed spread). The user chooses between more clean and crunch sources, the realism levers, and arm A's
    every-control coverage (2A).
- **The new controls' own worth:**
  - below 0: answers write them;
  - otherwise: the written preset keeps S's values for them while they stay learned (amendment 1).
- **Amp choice:**
  - below 0: the model's amp is used;
  - otherwise: `generate`'s research amp stays.
- **Interference, D_F20 − D_noHG:**
  - above 0 (adding high-gain sources hurts clean or crunch): the next build halves the high-gain cap to 25%;
  - otherwise: the cap stays.
- **V-real is reused** (its eleventh set of arms). T4 is not independent; the fresh-song decision test stays.

### 6. Cost

All rates are T2's measured ones:
- **Renders:** 15.4k plus 620 priming in 2 h 19 min on 3 processes, about 6.9k an hour.
- **Separation:** 5,308 in 5 h 33 min. That is about 850 an hour on MPS alone, about 1,350 with the CPU worker.
- **Training:** 11–15 min per 4.7k-example run.

| Step | Renders | Separations | MPS training | Wall time |
|---|---|---|---|---|
| F5: dry run, positive control, full twins (about 5.0k targets; other guitars reused) | about 5.3k | about 5.0k | | about 0.5 + 0.8 + 3.7–5.9 h |
| F5: 4 runs; fit; V-real (the new crops' S, 5 answer sets, per seed, families) | about 1.1k | | about 0.9 h | about 1.5 h |
| F20: about 16.8k new targets (16.1k needed, plus about 6% refusals as T2's), about 31.9k other guitars, priming | about 50.7k | about 16.8k | | about 0.5 + 7.3 + 12.4–19.8 h |
| F20: 7 runs (3 at 20k, 4 at about 10k); fit; V-real | about 1.2k | | about 4–5 h | about 5.5 h |
| **Total** | **about 58k** | **about 22k** | **about 5–6 h** | **about 32–42 h**, plus the review and any ear sitting |

The plan budgeted 50–70k renders, about 20k separations and 6–8.5 h of training for T3.

**Machine rules:**
- **Renders:** every Morgan render uses isolate=True and one discarded priming render, and trims the first 0.25 s.
  At most 3 render processes machine-wide (`local_objective.RENDERS` lists T3's commands).
- **Disk guard:** 31 GB.
- **Order:** renders and separations do not overlap. Shards resume, and plans carry the hash of T0's lists.
- **Downloads:** none unless the user says yes.

### 7. The ledger entry

`trusted-data-t3` is added to `dev-test-ledger.json` with this plan, before any render. It gives the V-real parts
(Signs' condition and the freeze) and bands, the seeds, the gate (the rows and rules above), the stopping rules and the renders. Real runs refuse
without it.

### Code to write, then review (nothing runs before)

**`learn/trusted_data.py`, stage `t3`:**
- `plan` (the sets, the draws, the allocation, the dry run);
- `render` (full-space settings through the table, the positive control);
- `build` (as T2);
- `train` (full-space heads, masks from `every_control.mask`, the amp head);
- `fit` (shared FS, pull, the two-fold check, constant);
- `vreal-crops` for the recovered parts (Signs only if part 8 clears its DI), and V-real's frozen membership;
- `vreal-predict` (amp-fixed, own amp, new controls at S, families, per seed, no pull);
- `vreal-render` (add-only);
- `report` (the rows above, per class, V-real-10);
- `e-on-fs`.

**Fixes first:** the Renesans bug. The pure parts are unit-tested. An independent review covers the code before any
render.

### F5 as built (code only, 2026-10-26; nothing rendered, separated or trained)

`learn/full_space.py` (the label space, the draw, the masked encoding, the answer, the network) and
`learn/trusted_data_t3.py` (`--stage t3` on `plan`, `render`, `build`, `train`, `fit`, `vreal-predict`,
`vreal-render`, `report`); the chain is `docs/trusted-data-t3-f5-chain.sh` (not launched). Details the plan left
open, decided here for the review:
- **The new controls in factory and start draws** take part C's draw rule around the mode's centre (continuous
  jittered by sigma 0.1 in unit space, switches kept with p 0.7, else a fair coin), as "drawn with part C's modes"
  reads. The spring's derived switch follows the centre's level there, as the plan states. Any mode with both cabs
  off is redrawn, not only wide.
- **Output gain** is held at S's value in every training render. Per answer it is fitted on V-real from the render's
  search-half loudness against the stem's, dB for dB, within -24 to +24 dB. Its |LUFS error| is scored on the held
  half against the amp track, with no extra render. *Confirmed by the user 2026-10-26: output gain is set by
  loudness matching, not predicted ([F5 outcome](#f5-outcome-2026-10-26)).*
- **The wide gate cap** is the 95th percentile (nearest rank) of every menu preset's stored threshold, over the
  three amps: -61.3 dB from 111 presets.
- **The positive control's 50** are drawn with `seed_int(20261107, "positive control")`. They must match T2's
  stored target FLAC and part C's mels at 0.99. Built from the same T2 backing, their mix and stem features must
  match T2's `mix-t2` and `xlance_g-t2` at 0.99. Every run waits for it.
- **The positive control runs first** (the review of #299). `control-check` makes 3 renders: one control example,
  then the same with the amp EQ's 1-kHz band moved to +12 dB; the output must change. Then the 50 examples are
  rendered (`render --positive-only`) and built (`build --positive-only`). Each stem is separated on the device T2
  built it on, so the stem comparison stays within one device. `pc-check` stops the chain on any miss, and all four
  runs refuse without it.
- **D_F5's merge augmentation reads its own renders** (the review of #299). The full twins' half mels and half
  loudness are saved at render (`tgt-t3`). D_F5's merge partners and its rows' `lufs_A`/`lufs_B` come from them;
  D_core5's come from part C's core renders. Both arms keep the same examples and the same partner draws.
- **The amp head** is a 256-unit MLP on the pooled audio features. The readout's switches use the mean probability
  over seeds, for D_core5 too. A per-seed answer is that seed's A1, pulled by the model's b. A both-cabs-off answer
  turns on the likelier cab.
- **A cell dimension with no FS5 example that sounds** reads b = 0 (`cell_b`'s rule). It is printed and recorded,
  not refused.
- **V-real's new crop:** `vreal-crops` cuts It Was My Fault ElecGtr1 on its ear-verified re-cut window from T0's
  re-check (90-100 s, which must equal the frozen window). It uses the validation-crop builder's new `window` rule,
  into `t3/vreal/crops/` (same files and record; no existing crop is touched). It adds the crop-only xlance_g stem,
  made as step 4 made stage F's. The judge lag is the label table's for the same DI and amp track. S is rendered in
  T3's own groups (6 renders a part). A crop that does not build is dropped before any read, and the drop is
  printed. `--drop-missing-crops` is only an opt-in escape for a member with no crop attempt.
- **The dry run's gain classes:** part A's classifier on the amp tracks classes most Ale Lak and Storm Of Particles
  sections high gain. So T2's examples are 96% high-gain-source by the declared order (61% by part A's class
  alone, the plan's figure). F5 keeps T2's mix; the 50% cap applies to F20.

### Open for the user

1. **Clean and crunch sources for F20** (open since T0). *Decided 2026-10-26: option (a). Strobe "Maya" and MekaPhil ×4
   were downloaded and taken in for training the same day (ledger `cambridge-new-training-bands-2026-10-26b`; ear page
   part 9 pending; [below](#the-strobe-and-mekaphil-intakes-ear-part-9-2026-10-26)).* After the ear the pool holds 1
   clean-class and 1 crunch section of 181, and Empty Signifier's DI is high gain. Options:
   - (a) download Strobe "Maya" and MekaPhil ×4 (about 2.4 GB, not on disk). They are DI-only sessions: every guitar has a DI, so rule
     1 keeps them. About 75 sections in 2 bands, gain unknown. They need T0's checks and one ear sitting.
     Recommended;
   - (b) EGDB (on disk) on borrowed backings;
   - (c) none.

   F5 can start without any of these.

The metal intake needs no decision here: its DIs join F20 as they pass the checks and the ear, under the caps.

## The metal intake's ear (parts 7a and 7b, 2026-10-26)

13 Cambridge-MT metal and hard-rock sessions are training-only (ledger `cambridge-new-training-bands-2026-10-26`; the
checks are in the [inventory](research/di-source-inventory-2026-10.md#metal-and-hard-rock-training-intake-2026-10-26)).
**Metal DIs get 1 ear window each.** They are training-only DIs, and the measures (D2, D3, D4, D1 and A1–A5) ran on up to
5 windows. Part 6 heard 2 windows per DI.
- **Pages:** `~/ndsp-presets/listening/trusted-data-ear/part7a-metal/` (page `trusted-data-ear-metal-a`) and
  `part7b-metal/` (`trusted-data-ear-metal-b`), 44 cards each, about 7 MB. Each is self-contained, with the same mobile
  layout as before. A 214-card single page (2 windows per DI, a tone card per amp track, 33 MB) was too heavy for a
  phone and is in the Trash.
- **DI cards:** one per D2/D3-passing DI (78), at its checked window with the highest DI play share. The answers are
  the same as part 6: clean, processed, not a DI, hum, not sure.
- **Tone cards:** one per session with an amp track (10). Each plays the session's main amp track: the own-take track of
  the passing DI that plays most. The window is that DI's busiest. The classes are clean, crunch, high-gain and too
  heavy (extreme). The two DGX sessions are DI only, and Daimon B "Crying Rivers" has no electric DI.
- **How `lists` reads them (`metal_verdicts`):**
  - a measured fail excludes whatever the ear says (`di_verdict`: D1, D2 or D3);
  - a window heard other than clean excludes;
  - one window heard clean is enough;
  - the session's tone screens heaviness: too heavy excludes every DI of the session;
  - until the tone is heard, the session's DIs wait;
  - DI-only sessions (DGX, 11 DIs) have no tone to screen: their DIs join once heard clean and count as high gain
    under T3's cap (`no_tone_counts_as`). This is the coordinator's decision of 2026-10-26, which the user may overrule.
  - The tone card classes its own DI only (`tone_class`); the session's other DIs carry `session_tone`, and an
    unclassed metal DI counts as high gain under T3's rule.
  - A heard tone does **not** clear "D1 to the ear" for a DI's own amp track: no card played a DI with its amp track,
    and 68 of the 78 DIs never have their own amp track heard. A verified DI is admitted for training as a DI; every
    one with an amp track carries `pair_unheard`, which T3's rule 1 must honour before it uses that amp track.
- Three page DIs already fail D1, so they stay excluded whatever the ear says: Serapis "The Dark Abyss" ElecGtr1DI and
  DTDI, and Dark Illusion "Evil Bones" ElecGtr4DI. Their amp tracks sit at near-zero delay (a render, not a miked cab).
- Clips were re-checked after decoding: none silent or sparse (decoded peaks −11.6 dBFS or louder; every clip has
  frames within 40 dB of its loudest on at least 30% of its length).
- *Heard 2026-10-26: 50 of the 89 DIs admitted, all high gain; 5 sessions too heavy
  ([outcome](#parts-7a-7b-8-and-9-heard-2026-10-26)).*

## The Strobe and MekaPhil intake's ear (part 9, 2026-10-26)

Strobe "Maya" and MekaPhil ×4 are part B2's parked known-answer songs. The user allowed them for training on 2026-10-23 and
approved the intake on 2026-10-26, as T3's clean/crunch source for F20. They are training-only (ledger
`cambridge-new-training-bands-2026-10-26b`); the checks are in the
[inventory](research/di-source-inventory-2026-10.md#strobe-and-mekaphil-training-intake-2026-10-26).
- **Page:** `~/ndsp-presets/listening/trusted-data-ear/part9-strobe-meka/` (page `trusted-data-ear-strobe-meka`). It
  has 14 cards (about 4 MB), built the same way as parts 7a/7b:
  - 13 DI cards, one per D2/D3-passing DI, at its busiest checked window;
  - 1 tone card. Only MekaPhil "Timeless (Part 2)" has amp tracks (`ElecGtr2`, `ElecGtr3`). Neither has a DI, and
    neither plays the same take as the session's `ElecGtr1` DI or its DT. The card plays `ElecGtr2` alone, with no DI
    of its own.
- **How `lists` reads it:** it uses `metal_verdicts` on `intake-2026-10-26b/summary.json` (`B2_PAGES`, `B2_DIR`),
  with part 9's rule for DI-only DIs (`no_tone_counts_as=B2_NO_TONE`, "unknown" since 2026-10-27; it was high gain),
  the style answers (`styles`) and the song's tone from a DI-less tone card (`screen_sets_song=True`).
  - The rules are as for the metal pages. A measured fail excludes. A window heard other than clean excludes. One
    window heard clean is enough. A too-heavy tone excludes the session's DIs.
  - **Every DI card asks a second question** (the coordinator, 2026-10-26): the playing style the DI suggests.
    The answers are clean/crunch-style playing, high-gain-style playing (for example palm-muted riffs), or can't tell.
    - The answer is exported as `style` (`STYLE_VERDICTS`) and read into `metal_style`.
    - A DI with no amp track of its own takes `style_class` from it. T3's `ear_call` reads that before the session's
      tone, so this is how a DI-only intake DI gets its gain group.
    - **Only "clean/crunch-style playing" makes a DI-only DI not high gain.** "Can't tell", conflicting answers or no
      answer leave `style_class` None; then the song's tone, else the DI-only rule makes it "unknown" (below).
    - A card counts as done once both questions are answered. A style answer counts even without a DI verdict.
  - Timeless Part 2's tone card plays `ElecGtr2`, another take with no DI. "Too heavy" excludes the session's DIs. Any
    other answer is kept as `screen_tones` and sets neither `session_tone` nor a `tone_class`. Since 2026-10-27 it
    sets the song's tone (`song_tone`) on the session's DI-only DIs (below).
- *Heard 2026-10-26: all 13 DIs clean and admitted. Every style question was left blank (the user: playing style
  can't be judged from a DI). Since 2026-10-27 they are "unknown", or take their song's tone (below;
  [outcome](#parts-7a-7b-8-and-9-heard-2026-10-26)).*

### Part 9's DI-only DIs: "unknown", or the song's tone (2026-10-27)

The user heard part 9's 13 DIs as clean but could not judge the playing style: a raw DI does not show it. So the
DI-only DIs kept no class and counted as high gain, which defeats their purpose as T3's clean/crunch source. The user
decided on 2026-10-27: label the DI-only DIs **"unknown"** (out of the high-gain cap), but where a song has an amp
track or a mix, let the user hear it and say which style.
- **Which songs have a guitar tone to hear.** Only MekaPhil "Timeless (Part 2)" holds a processed guitar track
  (`ElecGtr2`, `ElecGtr3`; no DI, other takes than the session's DIs). Strobe "Maya", "Alive (Yet Free)", "Core" and
  "Timeless (Part 1)" hold guitar DIs only (the zips' track names), so their mix has no guitar tone to hear.
- **Timeless Part 2's tone was already heard.** Part 9's tone card played `ElecGtr2` alone, and the user answered
  clean. That answer is the song's tone, so on part 9 it now sets the class of the session's DI-only DIs
  (`metal_verdicts(screen_sets_song=True)` → `song_tone`, source `SONG_FROM`: "song's amp track, heard alone (part
  9)"). Timeless Part 2's 2 DIs become clean at the next `lists` run (*it ran 2026-10-27 01:17; both read clean*). "Too
  heavy" still excludes the session.
- **No new page.** A 10-s card of Timeless Part 2's own mix was built (part 9b) and dropped the same day. The guitar
  sat about 14–17 dB under the piano, synths and lead vocal, so it would only have been a worse repeat of the card
  already heard. The page went to the Trash, and `lists` has no reader for it.
- **The rule, in T3's order** (`ear_call`): the DI's own amp track's tone card; the DI card's style; the song's tone
  (`song_tone`); the session's tone card; else part 9's DI-only rule, "unknown".
  - Clean or crunch puts the DI in the not-high-gain group, and high gain in the high-gain group. Conflicting
    answers set nothing.
  - A DI with its own amp track never takes the song's tone.
  - The metal pages keep the earlier rule: a DI-less card only screens and never classes (DGX stays high gain).
- **"Unknown" now:** Strobe "Maya", "Alive (Yet Free)" and "Timeless (Part 1)". Core's two DIs are excluded at T0.

## F5 outcome (2026-10-26)

F5's chain (`docs/trusted-data-t3-f5-chain.sh`) ran on 2026-10-26 from 10:35 to 15:47. An independent audit
recomputed every row from the stored V-real rows; all match. Rows are log(d_a/d_b), lower is better, band-weighted
with 90% band-clustered intervals, 7 bands, V-real-11 (11 parts, 66 directions; logs `t3-*.log`, `t3/fit.json`,
`t3/report.json`).

**The gate, D_F5 − D_core5: +0.079 [−0.065, +0.224]**, 2 bands better and 5 worse. The point is at or above 0, so
the declared reading applies: not shown; stop and report; F20 runs only with the user's yes.

| Row | Point [90%] |
|---|---|
| Gate, seed 20261042 pair | +0.082 (bands −/+ 3/4) |
| Gate, seed 20261043 pair | +0.091 (bands −/+ 2/5) |
| Gate without the pull | +0.087 |
| Gate, crunch (5 bands) / clean (2 bands, descriptive) | −0.003 [−0.073, +0.067] / +0.285 |
| D_F5 − S | +0.088 [−0.044, +0.220] |
| D_core5 − S | +0.009 [−0.033, +0.050] |
| D_F5 − constant | −0.004 [−0.052, +0.043] |
| D_core5 − D_SYN (T2's stored, own pull; V-real-10) | −0.020 [−0.056, +0.016]: it reproduces T2 |
| Family time effects and spring: D_F5 − D_F5 with it at S | +0.087 [−0.080, +0.253] |
| Families EQ, pedals, gate and doubler, cab rest | each within ±0.002 |

**Why:**
- **One part drives the gate.** Colour Me Red ElecGtr03 reads +1.015; every other part is between −0.12 and +0.09.
  With time effects and spring at S, D_F5 − D_core5 is −0.0075 [−0.069, +0.054] (a post-hoc re-read, not declared;
  the interval holds 0).
- **The time-effect heads learn nothing.** FS5 switch AUCs: reverb 0.49, springs 0.49–0.50, tremolo 0.51, delay
  0.56. The readout (on above 0.5) at the training base rate turns reverb on in 54 of 66 directions, delay in 29 of
  66 and the spring in 10 of 44, where S has them off.
- **Other switch heads are weak too:** compressor and drive AUCs about 0.58–0.59.
- **A rough probe:** reverb and delay are visible in the target render (AUC 0.70 and 0.73) but mostly gone after
  X-LANCE separation (stem 0.52 and 0.59, mix 0.53 and 0.58).
- **Training draws are wet:** factory draws have reverb on 74% of the time and delay 63%.
- **Where the judge punishes it, likely:** one sparse part, where the tails fill the gaps (one part; its sparseness
  not measured).
- **The amp head is near chance:** FS5 accuracy 0.39.

**Integrity:**
- The control check passed (unchanged share 0.34), and the positive control matched 50 of 50 at 1.0.
- Both arms had the same examples, the same drops and the same FS5.
- V-real-11 was frozen at 10:35:58, before any read. It Was My Fault ElecGtr1's crop is on 90–100 s.
- A 13-minute stall (a bare `wait` on caffeinate, fixed live, PR #300) skipped nothing.
- Training was healthy: best epochs D_core5 20 of 25 and 32 of 37, D_F5 20 of 25 and 15 of 20.

**Caveats and issues:**
- 785 of 4,974 full twins were dropped as near-silent, 747 of them wide draws, driven by low cab mic levels (about
  −22.6 dB). The labels are barely biased; the kept modes are 48/23/29.
- 28% of full twins were separated on CPU while their core twin was on MPS. The effect is unknown; F20 should keep
  each pair on one device.
- The |LUFS error| row compares unlike sets: S has n = 6, one part only. The ~5.6 dB is stem level against amp-track
  level, and it is the same for every arm.
- **Output gain (user, 2026-10-26):** set by loudness matching, not predicted. Amendment 2's rule is confirmed and no
  longer pending; the code's status string says so from now on (the records written on 2026-10-26 still say pending).

**Cost:** 6,246 renders (5,187 full-twin renders with 213 priming, 93 for the positive control, 3 for the control
check, 963 on V-real), about 4.2k X-LANCE separations plus the positive control's 50, and 37 min of MPS training.
The plan estimated about 6.4k renders.

**Next: the user's decision.** The ML session proposes:
- (a) a zero-render, per-control readability check on FS5;
- (b) about 70 renders of D_F5 with its unreadable controls at S, against D_core5;
- then F20's decision, whose main value is new data (metal, Strobe/MekaPhil and the new bands' DIs, pending the ear).

Fixes for F20: redraw near-silent draws instead of dropping them; keep each pair on one device; reconsider the
switch readout and prior, since time effects are barely readable from separated stems (rough probe: delay 0.59,
reverb 0.52).

## F5 follow-up: readability (R0) and the unreadable controls at S (R1) (declared 2026-10-26)

**What and why.** The user approved the ML session's proposal (a) and (b) from the [F5 outcome](#f5-outcome-2026-10-26)
on 2026-10-26. Declared here, and in the ledger (`trusted-data-t3`, amendment 1), before R0 is computed and before any
R1 render. **Both are post hoc and descriptive:** F5's V-real reads are already seen, and the audit already re-read
"time effects and spring at S" (−0.0075 [−0.069, +0.054]). Neither decides F20; F20 stays the user's call. Code:
`learn/trusted_data_t3_r.py`; chain `docs/trusted-data-t3-r-chain.sh` (not launched). Outputs go to
`t3/followup-r/` only; F5's files are read, never written.

### R0, readability on FS5 (zero renders)

D_F5's two seeds on FS5 (the shared fit set, full twins: 845 planned, 722 after F5's drops in either twin, the set
`fit` read), each example's answer as the readout makes it
(A1 + A2 over seeds and halves; the mean switch, mic and amp probabilities), against D_F5's constant from `fit.json`.
One row per head:
- **Continuous (85 heads):** E against the constant: per example |answer − label| − |constant − label| in unit
  space, on examples where the dimension sounds; 90% section-clustered t interval (12 sections). The answer is A1 + A2
  without the pull: the pull is fitted on FS5 itself, and at b = 0 it is the constant, so a pulled E is in-sample.
- **Switches (26, plus the two springs' derived switches):** AUC of the mean probability against the label, on
  examples where the switch is scored; 90% interval by the delete-one-section jackknife (t, sections − 1 df).
- **Amp choice:** the amp head's accuracy minus the base rate, per example (the base rate: D_F5's training labels'
  majority amp, guessed for every example); 90% section-clustered t.
- **The two mics** (not named in the approval; declared the same way as the amp): accuracy minus the constant's mic
  mode's, on examples where the mic sounds; 90% section-clustered t.
- **Output gain:** not a head (fitted to loudness), so no row.

**Readable** if the interval excludes chance in the right direction: AUC's lower end above 0.5; the E difference's
upper end below 0; the accuracy difference's lower end above 0. **Otherwise unreadable**, including a head with no
interval (fewer than 2 sections with data, one class only, or a jackknife fold left with one class). Printed by
family, with n, sections, point and interval, and each switch's training on-rate (the prior an unreadable head falls
back on).

Limits: about 116 rows at 90% two-sided, so about 5% of heads that read nothing come out readable by chance (no
correction, declared). FS5 is self-built mixes, so readable there does not mean readable on real songs.

### R1, D_F5 with every unreadable control at S (99 renders)

**One new answer set**, `D_F5:R`, on the frozen V-real-11 with F5's inputs, models and fit: D_F5's pulled answer (the gate's
arm), with every head R0 calls unreadable written at S's value (S of the part's class on the same amp). This covers
today's space too; the readable heads stay as F5 wrote them. D_core5 is unchanged.
- **The spring:** an unreadable derived switch puts the whole spring (level and the PR12's dwell) at S. An unreadable
  level under a readable switch takes S's level; when the switch reads on and S's level is 0, it takes the least level,
  as F5's answer does.
- **Amp choice** does not enter: the answers are amp-fixed, as F5's.
- **The rest is written as F5 writes an answer:** sync off, sections on, never both cabs off, off features neutral.
  Output gain is fitted per answer at render, and its |LUFS error| is the pipeline check.

**Renders:**
- 33 (part, amp) groups × (1 priming at S + 2 directions) = **99**, about 5 minutes on 3 processes.
- F5's rule primes once per new DI or amp (`direct_stems.run_group`), not once per process, so the count is 99, not
  about 70.
- isolate=True, the first 0.25 s trimmed, at most 3 render processes machine-wide, the 31 GB disk guard.
- No other answer set is rendered: D_F5:R's per-seed and no-pull variants would cost 66 renders each.

**Rows:** log(d_a/d_b), band-weighted, 90% band-clustered t (7 bands), per class and V-real-10 beside, the sign split
over bands:
- **R1: D_F5:R − D_core5** (post hoc, descriptive);
- D_F5:R − S, D_F5:R − constant, D_F5:R − D_F5 (what the at-S rule changes), D_F5:R − D_F5 with time effects and
  spring at S;
- **time effects only:** D_F5 with time effects and spring at S − D_core5, from F5's stored renders (the audit's
  re-read, already seen);
- every F5 row again, from F5's stored groups, beside.

**Reading:** the user's rule (an effect size with its interval, no pass bar), labelled post hoc. The unreadable list
comes from FS5 alone, but it was declared after F5's V-real reads were seen.

### R0 outcome (2026-10-26, zero renders; `t3/followup-r/r0.json`)

R0 ran once, after the declaration above was committed, on FS5's 722 examples in 12 sections. **20 of 116 heads read
better than chance; 96 do not.** About 6 of 116 would read by chance alone.

| Family | Readable | Which |
|---|---|---|
| Today's space | 5 of 25 | SW50R bright, treble boost and input mode; AC20 bright; right cab on. No knob (E within ±0.006 of the constant's), no mic |
| Amp choice | 1 of 1 | accuracy 0.40 against a base rate of 0.33: +0.069 [+0.033, +0.105] |
| Amp EQ | 4 of 36 | PR12 EQ on; PR12 bands 2 and 4; SW50R band 4 (each E about 0.002–0.004 under the constant's) |
| Pedals | 4 of 14 | the three on switches (AUC 0.58–0.67) and the compressor's release; no knob |
| Time effects | 1 of 19 | delay on, AUC 0.557 [0.505, 0.609]; reverb 0.493, tremolo 0.507, no knob |
| Spring | 0 of 5 | derived switches 0.487 and 0.498 |
| Gate and doubler | 1 of 4 | doubler on, AUC 0.585 |
| Cab rest | 4 of 12 | left cab pan, right room level, right cab stereo, right room on |

By kind: 5 of 85 continuous heads, 14 of 28 switches, 0 of 2 mics and the amp choice.
- **The knobs read nothing:** 5 of 85 knobs read, about as many as chance alone gives (about 4). Every continuous
  head's E sits within 0.01 of the constant's except three, which read worse: the EQ high-pass filters (SW50R +0.023,
  AC20 +0.013) and drive 2's treble (+0.0106).
  - **9 knobs read reliably worse than the constant** (interval above 0): input gain, right cab distance, right cab mic
    level, AC20 EQ band 1, both high-pass filters (AC20, SW50R), drive 2's level and treble, and the SW50R spring level.
- **What R1 writes:** F5's D_F5 answers rebuild exactly from F5's stored readout in all 66 directions (checked at zero
  renders, nothing written). D_F5:R therefore has reverb, tremolo and the springs off everywhere. The delay's switch
  reads, so delay stays on in 29 of 66 directions, its knobs at S's stored values (mix 0.07–0.5, 500 ms, written
  sync off).
- **For R1's reading:** 96 heads at S, today's knobs among them, make D_F5:R close to S plus the 20 readable heads.
  R1 compares that against D_core5. It does not compare D_F5's own knobs against D_core5's.

### How R1 sits with amendment 1

[Amendment 1](every-control-plan.md#amendment-1-2026-10-22-every-control-is-learned) says every control is learned
and no fixed rule stands in for a control the judge can't hear.
- **What R1 keeps:** every control stays in the learned space. The heads, labels and loss are unchanged, and nothing
  is retrained. Only the written answer takes S's value, and only where FS5 shows the head reading no better than
  chance.
- **The precedent:** T3's own decision rule already writes S's values for the new controls when their worth is not
  shown, "while they stay learned (amendment 1)" (section 5 above).
- **R1 goes beyond that rule.** T3's rule puts only the new controls at S, by family. R1 puts heads at S one by one,
  and today's space too: input gain, the amp knobs, the mics and the cab positions. So D_F5:R − D_core5 sits close to
  S − D_core5.
- **Where it may conflict (the user's call):**
  - **S is not the model's constant.** The pull's limit (b = 0) is D_F5's constant: training medians and switch
    majorities. For the time-effect switches that constant is "on", because the factory draws are wet. S's values are
    a fixed preset, chosen per control by a data test (R0), not learned from FS5.
  - So calling R1 "the model's pull to the constant (S)" is not accurate. **Read strictly, writing S for an
    unreadable control is a fixed rule standing in for it in the written answer.** It keeps amendment 1's membership
    rule but not its letter.
  - If the user rules it out, R1 still reads what the unreadable heads cost, as a description. The written answer
    would then use the constant instead (F5 read that already: D_F5 − constant −0.004) or wait for heads that read
    more.
- **The user's ruling (2026-10-27):** R1 stands as a measurement only. Writing S for unreadable controls is not
  adopted as the method.

### R1 outcome (2026-10-27, 99 renders; post hoc and descriptive; audited)

R1's chain ran on 2026-10-27 from 00:38 to 00:39 (log `logs/t3r-r1-report.log`, `t3/followup-r/r1-report.json`),
complete: 66 directions on the frozen V-real-11, 7 bands, 99 renders. An independent audit recomputed the rows below,
and they match. Log ratios, lower is better:

| Row | All (7 bands) | Bands −/+ | Crunch (5 bands) |
|---|---|---|---|
| **D_F5:R − D_core5 (R1)** | **+0.062 [−0.080, +0.204]** | 4/3 | −0.013 [−0.070, +0.044] |
| D_F5:R − S | +0.071 [−0.047, +0.188] | 1/6 | +0.012 |
| D_F5:R − constant | −0.022 [−0.093, +0.050] | 4/3 | −0.022 |
| D_F5:R − D_F5 (what the at-S rule changes) | −0.017 [−0.072, +0.038] | 4/3 | −0.010 |
| D_F5:R − D_F5 with time effects and spring at S | +0.070 [−0.108, +0.247] | 3/4 | −0.012 |

- **Putting the 96 unreadable heads at S does not close the gap.** R1 reads +0.062 against D_core5, close to F5's
  gate (+0.079). Crunch leans better (−0.013, 4 of 5 bands); the 2 clean bands carry the rest.
- **The one time effect left on is the delay.** R0 counted its switch readable at AUC 0.557, lower bound 0.505, just
  above chance, so it stays on in 29 of 66 directions. Colour Me Red ElecGtr03 again drives the result: +0.846 against D_core5 (+0.949 against D_F5 with time effects at S, the better evidence that delay is the cause).
  With the whole time-effects family at S, D_F5 reads −0.0075 against D_core5 (F5's audit re-read); D_F5:R sits
  +0.070 above that.
- **"Delay is the cause" is the best fit, not proven.** No render isolates the delay (D_F5:R with only the delay at
  S was not rendered).
- **Pipeline check:** |LUFS error| mean 5.5 dB, median 5.6, 2 of 66 clamped (stem against amp-track level, as in F5).
- **What it changes:** nothing is adopted. R1 decides nothing about F20 (declared), and under the user's ruling above
  the at-S rule is not F20's method (fix 3 below).

### F20's fixes from the F5 audit (declared in the plan only; no F20 code yet)

F20 still waits for the user's yes. When it runs:
1. **Near-silent draws are redrawn, not dropped.**
   - When a target render falls below rule 2's floor (−50 LUFS), the example's new controls are drawn again from its
     own stream: the next draw of seed 20261107's stream for that example, so a redraw can be reproduced. Up to 5 tries.
   - The same applies to an other guitar's full-space preset (seed 20261102's stream for that example and DI).
   - An example drops only when every try is silent, and that drop is printed. The kept label is the redrawn one.
   - The redraw share is printed by mode, with every switch's training on-rate before and after.
   - At F5's rate (785 of 4,974, mostly wide draws with quiet cab mics) this costs about 16% more target renders.
2. **Each core/full pair stays on one separation device.**
   - Wherever F20 builds a twin of a stored example (F5's twins carried in, or any re-run of the paired gate), the
     twin is separated on the device its stored twin used. This is the positive control's rule (`pc_todo`).
   - The CPU worker takes only examples whose stored twin was CPU-built, or that have no twin. F20's new examples have
     no twin, so either worker can take them.
   - The device is recorded per example, and the split is printed per arm.
3. **The switch readout, and the prior for controls that can't be heard.**
   - After D_F20 trains, R0's check runs on FS20 under the same rule, at zero renders.
   - **Readout:** a readable switch is written on above 0.5, as now. An unreadable head (switch, knob or mic) is
     written at S's value, R1's rule, instead of falling back on its training prior.
   - **Prior:** the training draws keep their declared rates. R0's table prints each switch's training on-rate
     beside its AUC, so the prior an unreadable head falls back on is visible. Drawing switches 50/50 was considered
     and not taken: an unreadable head then flips a coin, and still turns reverb on in about half its answers.
   - **Which readout decides:** D_F20's rows are read both ways, plain and at S. The plain readout stays primary, as
     declared, unless the user rules on amendment 1 (above) before any F20 V-real read.
   - *The user ruled on 2026-10-27: writing S for unreadable controls is not adopted as the method. So the plain
     readout is F20's readout, and an at-S read is at most descriptive beside it. How the switch readout and prior
     change is left to F20's plan, after the mix-aware model and the separator fine-tune ([ROADMAP](ROADMAP.md)).*


## Parts 7a, 7b, 8 and 9 heard (2026-10-26)

The user heard all four pages on 2026-10-26. Exports in `learn/trusted-data/ear-exports/`:
`part7a-metal-2026-10-26.json`, `part7b-metal-2026-10-26.json`, `part8-signs-di-2026-10-26.json` and
`part9-strobe-meka-2026-10-26.json`.

**How `lists` ran.** Real `lists` runs read them with every earlier export. No answer was superseded or cleared, and
no card has a note. The code was already on main: `metal_verdicts` (PR #297, part 9's reading as built) and part 8's
reader `recheck_measure_di` (PR #296). `verified.json` was not edited by hand.
1. Parts 7a, 7b and 8. `t0/` was backed up first to `t0-backup-before-ear78-20261027-003402`.
2. T3's plan holds T0's lists' hash, so `t0/` was put back from that backup while the F5 follow-up's R1 ran. The
   result was kept as `t0-after-ear78-pending-20261027-003751`.
3. The re-run after R1 matched that copy (same lists hash, `4f298b5a9ec9`; log `logs/lists-ear78.log`).
4. Part 9 was added in one more run (backup `t0-backup-before-ear9-20261027-004956`; log `logs/lists-ear789.log`).
   It changed only part 9's 13 DIs.

**Part 8: Signs ElecGtr6 is verified.** Its measure DI, 33_ElecGtr6DI, was heard clean on all 3 windows (63.5, 82 and
148 s).
- Under PR #296's rule the measure DI is cleared and the part is verified. The two windows D4 flags (82 and 148 s)
  rejoin, so it keeps all 5 re-check windows (63.5, 82, 123.5, 148 and 200.5 s). Its crop stays 63.5–73.5 s.
- Targets are now **20 verified**, 0 pending, 39 excluded.
- Like the other recovered parts, it joins no list read from the old crops. T0's V-real (10), knob ceiling 2 (7) and
  the level prior are unchanged.
- **T3's frozen membership is unchanged: V-real-11, without Signs.** F5's plan froze it at 2026-10-26 10:35:58,
  before part 8 was heard. Any later plan that is not bound by T3's freeze would see Signs (`vreal_membership` now
  gives V-real-12).

**Parts 7a and 7b: the metal intake. 50 of its 89 DIs are admitted, and every one is high gain.**
- **Tone cards (10):**
  - Heard too heavy (5): Daimon B "Broken Again", Dark Illusion "Evil Bones", Inhumanity Vortex "Cybermod", Serapis
    "Morbus Animi", Serapis "The Dark Abyss". Every DI of these sessions is excluded: 30 DIs, 24 of which would
    otherwise have passed.
  - Heard high gain (5): Arcadian Alone, Dark Illusion "Dark Illusion", Peppermark "Interlude", "Another Feeling" and
    "Lua Negra".
  - None was heard clean or crunch.
- **DI cards (78):** 76 clean, 1 processed (Daimon B 27_ElecGtr3DI) and 1 unsure (Serapis "The Dark Abyss"
  23_ElecGtr1DI). Both are in too-heavy sessions anyway, and the Serapis DI already fails D1.
- **DGX** has no amp track, so it has no tone card. All 11 of its DIs were heard clean and join as high gain under
  the recorded DI-only rule (`no_tone_counts_as`).

| Session | Tone heard | DIs | Admitted | Out |
|---|---|---|---|---|
| Arcadian Alone "The Deathless One" | high gain | 4 | 3 | 1 (D2) |
| Daimon B "Broken Again" | too heavy | 6 | 0 | 6 (too heavy; ElecGtr3DI also heard processed) |
| Dark Illusion "Dark Illusion" | high gain | 6 | 2 | 4 (D2; 2 of them also D1) |
| Dark Illusion "Evil Bones" | too heavy | 4 | 0 | 4 (too heavy; ElecGtr4DI also fails D1) |
| Inhumanity Vortex "Cybermod" | too heavy | 5 | 0 | 5 (too heavy; ElecGtr3DI also fails D2) |
| Peppermark "Another Feeling" | high gain | 14 | 12 | 2 (D2) |
| Peppermark "Interlude" | high gain | 14 | 13 | 1 (D2) |
| Peppermark "Lua Negra" | high gain | 10 | 9 | 1 (D1, D2) |
| Serapis "Morbus Animi" | too heavy | 6 | 0 | 6 (too heavy) |
| Serapis "The Dark Abyss" | too heavy | 9 | 0 | 9 (too heavy; 3 also fail D1 or D2) |
| DGX "Redemptive Pain" | none (DI only) | 7 | 7 | 0 |
| DGX "Rest In Hell" | none (DI only) | 4 | 4 | 0 |
| **Total** | | **89** | **50** | **39** (24 too heavy, 14 measured fails, 1 heard processed) |

- **By band:** the 50 admitted DIs come from 4 bands: Peppermark 34, DGX 11, Arcadian Alone 3, Dark Illusion 2.
  Daimon B, Inhumanity Vortex and Serapis drop out entirely. Peppermark is 68% of the admitted metal DIs, so F20's
  35% band cap will bind on it.
- **By gain group:** all 50 are high gain (`ear_call`). 39 are high gain from their session's tone card; the 5 tone
  cards' own DIs also carry `tone_class` high gain. 11 (DGX) are high gain by the DI-only rule.
- 39 of the 50 have an amp track, and each carries `pair_unheard`. The DI-and-amp pairing was never heard, so T3's
  rule 1 must not use those amp tracks yet.
- **A caveat on D4:** it flags most checked windows on 16 of the 50 admitted DIs. One window heard clean clears
  them, which is the declared rule for training-only metal DIs. Dense palm-muted playing may trip D4, as it may trip
  D2's hum check.

**Part 9: Strobe and MekaPhil. All 13 DIs were heard clean and are admitted, but they count as high gain for now.**

| Session | DIs | Admitted | Out |
|---|---|---|---|
| Strobe "Maya" | 4 | 4 | 0 |
| MekaPhil "Alive (Yet Free)" | 5 | 4 | 1 (D2) |
| MekaPhil "Timeless (Part 1)" | 5 | 3 | 2 (D2) |
| MekaPhil "Timeless (Part 2)" | 2 | 2 | 0 |
| MekaPhil "Core (Eternal Waltz)" | 2 | 0 | 2 (D2) |
| **Total** | **18** | **13** | **5** (T0's D2 fails, before the ear) |

- Timeless Part 2's tone card (its `ElecGtr2`, a take with no DI) was heard clean. By design it screens only, so it
  is kept as `screen_tones` and classes nothing.
- **Known limitation: the style question was left blank on every card.** The user's reason: playing style can't be
  judged from a DI. Under the merged rule a DI-only DI with no clean/crunch-style answer counts as high gain, so all
  13 do (`no_tone_counts_as`; `style_class` None).
- These were meant as F20's clean/crunch source. Until they are classed, they add nothing to it.
- **Changed 2026-10-27 (PR #306):** they are "unknown" (out of the high-gain cap), except Timeless Part 2's 2, which
  take its amp track's clean tone. A per-song mix card was built and dropped
  ([below](#part-9s-di-only-dis-unknown-or-the-songs-tone-2026-10-27)).

**The intake lists now** (`intake_dis`, 116 DIs):
- **64 admitted**, all high gain at this sitting (part 9's 13 change on 2026-10-27, below):
  - Empty Signifier 20_ElecGtr2DI (part 6);
  - the 50 metal DIs;
  - 13 Strobe/MekaPhil DIs.
- 52 excluded;
- 0 pending.

T0's DIs are unchanged (46 verified, 13 excluded), as is T0's training pool (27 DIs, 181 sections). Stems are unchanged
(166 in 14 sessions).

**The clean/crunch shortage is unchanged.**
- Every admitted metal DI is high gain, and 5 metal sessions were dropped as too heavy.
- Part 9's DIs counted as high gain at this sitting. Since 2026-10-27, 11 are "unknown" and Timeless Part 2's 2 are
  clean.
- **The high-gain share of a T3 F20 pool:**
  - Today's pool, from T3's plan table, is 181 sections, 174 of them high gain (96%). The 7 that are not are Ale Lak
    crunch 4, Starnes And Shah clean 1, Storm Of Particles crunch 1 and unclassed 1. Only 3 of the 7 are among T2's
    sections (Ale Lak 1, Storm Of Particles 2). The other 4 were excluded at cleaning or refused at the D build.
  - The 64 admitted intake DIs' sections are not cut yet; they come when the inventory and part A's sections are
    rebuilt. 51 are high gain; of part 9's 13, 11 are "unknown" and 2 clean (2026-10-27; applied by the `lists`
    re-run after PR #306 at 01:17, `logs/lists-pr306.log`, and checked in `verified.json`).
  - At T0's training DIs' mean of 6.7 sections per DI they add about 430 sections: about 342 high gain, 74 unknown and
    13 clean. The pool becomes 516 high gain, 20 not, 74 unknown of 610. **With unknown left out, 516 of 536 are high
    gain (96.3%); with unknown counted as high gain (the worst case), 590 of 610 (96.7%).** Unknown is 12%,
    under F20's 25% cap.
  - At part C's median of 4 per DI: 378 high gain, 15 not, 44 unknown of 437; 96.2% with unknown left out, 96.6%
    counted as high gain; unknown 10%.
  - So about 96.2–96.3% high gain with unknown left out, and 96.6–96.7% counting unknown as high gain.
  - The non-high-gain part grows from 7 sections to about 15–20 (Timeless Part 2's 2 DIs).
- **What that means for F20's 50% cap:**
  - F20 may hold at most 50% high-gain examples. F5's 4,974 examples are 96% high gain (4,767).
  - So F20's roughly 15k new draws need about 9.8k non-high-gain examples from 7 sections, about 1,400 draws per
    section. That figure assumes all 7 can be drawn. If only T2's 3 can, it is about 3,300 per section. With
    Timeless Part 2's sections once cut (15–20 in all), it is about 500–650 per section.

**The DI inventory was not rebuilt.** By the process, an admitted DI trains only once the DI inventory is rebuilt and
a training draw includes it (as for Empty Signifier's DI). No training draw is planned: F20 waits for the user's yes.
- A rebuild alone would add no sections. Part C's pool (`pool.json`, which records the inventory's sha256) and part
  A's sections would have to be rebuilt too.
- So the rebuild belongs to F20's plan step.

**T3 and T0's lists' hash.** T3's `plan.json` holds the hash of T0's lists, so every T3 command refuses once a
`lists` run changes them (`check_lists`). This is why the runs waited for R1.
- From here, any T3 command needs a re-plan first.
- A re-plan over T3's rendered rows refuses, because `vreal_membership` now gives V-real-12 against the frozen
  V-real-11.
- F20's plan has to settle this. **Keeping the frozen V-real-11 needs a code change.** `cmd_plan` (in
  `trusted_data_t3.py`) refuses on the membership change before the line that carries the old frozen V-real over
  can apply. Without that change, the only route is moving `t3/` aside, and the re-plan then freezes V-real-12.

## D_F5mix: the every-control model fed the mix (ROADMAP step (a); declared 2026-10-27, nothing run)

**What and why.** The [tone probe](tone-info-probe.md) read 30 of 116 heads from the self-built mix and 20 from the
X-LANCE stem with a linear reader, and the stem added nothing to the mix (mix plus stem 24; ROADMAP (a0), #309).
D_F5 reads 20 from the stem (R0). This step trains F5's every-control model on the mix instead of the stem, reads its
readability on FS5, and then reads it on V-real.
- Declared here and in the ledger (`trusted-data-t3`, amendment 3) before any training. *Revised the same day after
  the independent review of PR #310, still before any training: a D_F5-noaug arm was added, the stop rule dropped,
  the switches' summary row and the training check fixed.*
- **Pending the user's yes** (training longer than minutes); nothing runs before it.
- Nothing of D_F5mix is seen, so its rows are not post hoc. But V-real is read again after F5 and R1, and the
  probe that motivated the step read FS5.
- Code: `learn/trusted_data_t3_mix.py`. Chain: `docs/trusted-data-t3-mix-chain.sh` (not launched).
- Outputs go to `trusted-data/t3-mix/` only. `t0/`, `t2/` and `t3/` are read, never written.

**The prior result, against the mix.** The direct-stems pilot already compared a mix-only and a stem-only model
([pilot results](direct-model-stems-pilot-results.md)): D_mix − D_stem read **+0.0223 [+0.0142, +0.0304]** on R_in
(+0.0191 [+0.0069, +0.0312] on R_out), reliably worse, and its rule 2 closed the mix-only route then. That was part
C's mixes, Mega-53 stems, today's 25 controls and the E metric, not F5's self-built mixes, X-LANCE and every control;
the linear probe is the new evidence. So the prior leans against the mix, and this step reads whether the change of
separator, mixes and label space reverses it.

### The arms: F5 with one change, the input

- **D_F5mix is D_F5 in everything but the input:**
  - the network: the 115-control heads, the masked loss and the amp head;
  - the examples: F5's 3,467 full twins after F5's drops, with the full twins' labels;
  - the early-stopping and fit set: FS5's 722;
  - the seeds 20261042 and 20261043, the 40-epoch cap and patience;
  - the readout and the pull rule.
- **The input:** each full twin's stored self-built mix features (`t3/build/ex/…/<i>-mix-t3.npz`: half mels and half
  loudness) in place of its X-LANCE stem (`<i>-xlance_g-t3.npz`).
  - They exist: F5's build stored both for every full twin. There are 4,189 `mix-t3` files, which is 3,467 + 722
    (counted, nothing read). The core twins' mixes are T2's `mix-t2` and are not used.
  - The input is `direct_stems`' D_mix arm (the direct-stems pilot's amendment 1): the stem channel and the
    stem-loudness slot are zero; the mix channel and the mix loudness are kept. It mirrors D_F5's D_stem input, where
    the mix is zero.
- **Augmentation, and the D_F5-noaug arm.** D_stem's four augmentations (separator failure, a merged guitar,
  drop-outs, darkening) act on the stem channel only, because they imitate the separator's errors. With the stem
  channel zero they have nothing to act on, so D_F5mix trains unaugmented, as the pilot's D_mix did. No mix
  augmentation is invented.
  - The pilot measured augmentation helping D_stem: D_stem − D_stem-noaug **−0.0115 [−0.0184, −0.0045]** on R_in.
    So D_F5mix − D_F5 would charge the mix with the lost augmentation.
  - **D_F5-noaug** separates the two: D_F5 exactly (stem input, the same examples, FS5, seeds, cap, readout), with
    augmentation off. Zero renders to train.
  - **The input contrast is D_F5mix − D_F5-noaug:** both unaugmented, only the input differs.
  - D_F5mix − D_F5 (input and augmentation together) and D_F5-noaug − D_F5 (augmentation alone, F5's setting) are
    read beside it, descriptive.
- **The constant** comes from the training labels, which are D_F5's for both arms, so it is D_F5's constant. `fit`
  refuses unless it equals F5's stored one. Each arm's pull is refitted on FS5 from its own answers (amendment 5's
  rule), with both section folds printed.
- **The training mixes' level (measured, zero renders):** the stored training mixes sit at a median −11.4 LUFS per
  half (10–90%: −14.2 to −8.6). V-real's crops are brought to −12.25 LUFS, the one inference gain F5 used for both
  channels. F5's path is kept unchanged: the 1-dB offset is within the training spread. Stated, not corrected.
- **The training check:** each run refuses unless its examples are D_F5's: the same F5 and FS5 ids after the same
  drops (T3's dropped ids must equal D_F5's run record's `dropped` list, and the counts match).

### V-real's input

On V-real, D_F5mix reads the crop's mix through F5's path (`direct_stems.step4_half`: one gain to the training
median, the search half, the stored mel grid). It is the same audio F5 fed into the zeroed mix channel; D_F5-noaug
reads the stem, as D_F5:
- **the 10 stage F parts:** the stored context `~/ndsp-presets/learn/arm-a-mega53/F/contexts/<slug>.npy`, sliced at
  `F/contexts/log.json`'s offset. `direct_existing.f_inputs` asserts it equals the crop folder's `mix.wav`:
  - `references/validation-crops/<slug>/mix.wav` for It Was My Fault ElecGtr3 and Signs ElecGtr3;
  - `references/validation-crops-set3/<slug>/mix.wav` for Colour Me Red ElecGtr02 and ElecGtr03, Femme ElecGtr5,
    Get Out Of Bed ElecGtr2, Let's Dance ElecGtr3 and Wickerman ElecGtr1–3;
- **It Was My Fault ElecGtr1** (T3's own crop): `t3/vreal/crops/cambridge-It_Was_My_Fault_For_Waiting-ElecGtr1/mix.wav`,
  the unity sum cut on 90–100 s.
- `vreal-predict` refuses unless each part's input hashes equal those F5's predictions recorded
  (`t3/vreal/predictions.json`, `inputs`), so both arms read exactly F5's files.
- **Output gain** is fitted per answer to the stem's search-half loudness, as in F5; the stored stem is read for that
  alone. So the gain fit follows the same rule for every arm.

### Frozen V-real-11 and T0's lists

- **The issue:** T3's `plan.json` holds T0's lists' hash (`fac903559adb`). The lists have changed since (parts 7a,
  7b, 8 and 9, and PR #306; `6ac6a335d1ad` on 2026-10-27). So every T3 command refuses (`check_lists`) until a
  re-plan, and a re-plan would freeze V-real-12.
- **The handling (minimal):** this step does not re-plan and runs no `--stage t3` command. It reads T3's stored plan
  as frozen: F5's and FS5's examples, and **V-real-11** (frozen 2026-10-26 10:35:58, before part 8 was heard). T3's
  rule is that a later ear sitting cannot change it. So Signs ElecGtr6 stays out, and every row is on the same 11
  parts and 66 directions as F5 and R1.
- **A drift check refuses in place of the hash** (zero renders, every command). Under today's lists:
  1. every F5 and FS5 example's target DI and other guitars' DIs must still be verified, and its section still usable;
  2. every V-real-11 member must still be in today's membership.

  Additions (today Signs ElecGtr6, which gives V-real-12) are printed and stay out. Both hashes are recorded in every
  output. A later `lists` run that removes anything F5 or V-real-11 uses makes the step refuse.
- **Why not enforce the hash:** it would only force a re-plan that changes nothing F5 trained on or V-real-11 holds,
  or moving `t3/` aside.
- **Why not V-real-12:** the arms it is compared with (D_F5, D_core5, S, the constant) were rendered on V-real-11.
  Signs would need S and every arm rendered there. V-real-12 belongs to F20's plan (ROADMAP (d)).

### The readout, in order

**1. FS5 readability (R0's rule, zero renders), read before V-real, descriptive.**
- **Each arm's R0 table** (D_F5mix and D_F5-noaug): each of the 116 heads by R0's rule (`trusted_data_t3_r.r0_rows`)
  against the constant, on FS5's 722 examples in 12 sections, printed by family, beside D_F5's stored table
  (`t3/followup-r/r0.json`, 20 of 116). The readable counts are printed as they are, with no bar: about 6 heads per
  model read by chance, and the count has no interval.
- D_F5's readout is recomputed on FS5 from its stored models. It must reproduce that table's readable set, or the
  step refuses.
- **Paired per head,** on the same examples, for D_F5mix − D_F5-noaug (the input) and beside it D_F5mix − D_F5 and
  D_F5-noaug − D_F5:
  - knobs: the per-example E step, |a − label| − |b − label|, section-clustered 90% t;
  - switches: the AUC difference, delete-one-section jackknife 90% t;
  - the mics and the amp: the accuracy difference, section-clustered 90% t.

  Each step whose interval excludes 0 is counted, both ways.
- **Four summary rows** per pair, each with its 90% interval over the 12 sections:
  - knobs: the per-example mean E step over sounding knobs (below 0: arm a reads better);
  - switches: the mean AUC difference over the switches whose AUC is defined in every jackknife fold, so the row
    keeps its interval (above 0: better; the switches left out are printed);
  - the amp choice: the accuracy difference (above 0: better);
  - the mics: the per-example mean accuracy difference over sounding mics (above 0: better).
- **No stop rule.** The V-real read runs whatever FS5 shows: it costs a few minutes of renders, and a gate there
  would be an arbitrary bar.

**2. V-real (165 renders).**
- **Two new answer sets, D_F5mix and D_F5-noaug,** amp-fixed (S on the same amp) on the frozen V-real-11:
  - each pulled by its own FS5 fit;
  - the plain readout, as F5 wrote D_F5: switches on above 0.5, mics by argmax, off features neutral, never both cabs
    off, sync off.
- **Renders:** 33 (part, amp) groups × (1 priming at S + 2 arms × 2 directions) = **165**.
- **Rows** against each other and F5's stored renders: log(d_a/d_b), lower is better, band-weighted, 90%
  band-clustered t (7 bands), per class and V-real-10 beside, with the sign split over bands:
  - **D_F5mix − D_F5-noaug (primary):** what the mix input is worth, both unaugmented;
  - D_F5mix − D_F5 (input and augmentation together; descriptive);
  - D_F5-noaug − D_F5 (augmentation alone; descriptive);
  - **D_F5mix − D_core5:** the gate read again with the mix input (every control against today's 25);
  - D_F5mix − S; D_F5mix − constant (D_F5's constant, rendered in F5; the constants are equal).
  - Beside: F5's gate and R1's row, as stored.
- Each arm's own amp (its amp head) is recorded, not rendered.
- No per-seed, no-pull or family answer sets are rendered (66 renders each).
- **Reading (the user's rule):** effect sizes with intervals, no pass bar.
  - Interval below 0: shown.
  - Point below 0 with the interval holding 0: leans better, built on, and called not shown.
  - Undecided is not failed.
  - F5's gate read about ±0.145, driven by one part (Colour Me Red ElecGtr03), so a lean is the likely result.
- **What it changes:**
  - If D_F5mix − D_F5-noaug leans or is shown better, the mix input becomes the baseline that (b)'s separator
    fine-tune is read against, and F20's plan takes it (with whatever augmentation F20 declares).
  - Otherwise the stem stays, and (b) is read as planned.
  - Neither outcome runs F20; that stays the user's call.

### Cost

- **Training:** 4 runs on MPS, 2 per arm.
  - F5's D_F5 runs took 8.5 and 6.8 min (best epochs 20 and 15); D_core5's took 8.4 and 12.4 min.
  - At F5's rate of about 0.34 min an epoch, a run takes about 7–14 min (the cap is 40 epochs).
  - So about **30–55 min of MPS** for the four, a little less without augmentation; plus a few minutes of CPU for the
    fits and the R0 read.
  - A run whose best epoch falls within 4 of the cap is extended before it is read (T2's rule). The chain stops
    before any render then.
- **Renders:** none for the FS5 read; **165** on V-real (R1's 99 took about 2 minutes on 3 processes, so a few
  minutes). Zero separations.
- **Wall time:** about 35–65 min in all.
- **Machine rules** (F5's): every Morgan render isolate=True, with one discarded priming render and the first 0.25 s
  trimmed; at most 3 render processes machine-wide (`local_objective.RENDERS` lists `trusted_data_t3_mix
  vreal-render`); the 31 GB disk guard.

## D_F5ft: the every-control model fed the fine-tuned stem (ROADMAP step (b); declared 2026-10-27, nothing run)

**What and why.** The [tone probe](tone-info-probe.md) located the song-only loss between the wet target render (86
of 116 heads readable) and the mix (30), and found the stock X-LANCE stem recovers none of it (20; mix plus stem 24).
The [effect-detection research](research/effect-detection-2026-10.md) ranks a fine-tune of the separator on our own
wet targets first: it is the one lever aimed at what the mix masks. T3's stock stems sit at a median −5.7 dB SNR
against the wet target (F5 and FS5, as T3's build measured it), so there is room. This step fine-tunes X-LANCE gtr_mss
on F5's self-built mixes, re-separates F5 and FS5, retrains the every-control model on the new stems, and reads it as
step (a) was read.
- **Approved by the user 2026-10-27** ("Yes for all", after the ML session's summary listed this fine-tune at several
  hours plus 4–6 h of re-separation). Declared here and in the ledger (`trusted-data-t3`, amendment 4) before any
  fine-tune, separation or training.
- It runs after step (a) (D_F5mix and D_F5-noaug), which it is read against: `check` refuses until step (a)'s report
  is complete.
- Code: `learn/xlance_finetune.py`. Chain: `docs/trusted-data-t3-xlance-chain.sh` (not launched).
- Outputs go to `trusted-data/t3-xlft/` only. `t0/`, `t2/`, `t3/`, `t3-mix/` and `tone-probe/` are read, never
  written. No held-out data: F5, FS5 and the frozen V-real-11 only, under step (a)'s drift check.
- Allowed under the user's rule "no new separators; fine-tuning OK" (2026-10-20): the stock gtr_mss weights
  (hash-checked against `tools/xlance/manifest.json`), some of its layers trained further.

### The fine-tune

- **Model:** gtr_mss as `direct_stems.XLanceG` loads it (BS-RoFormer, 51.0 M parameters, stereo, one stem).
  Trainable: the last 4 of its 12 transformer layers (8.4 M), the final norm and the mask estimator (24.7 M), 33.1 M in
  all. The band split, layers 0–7 and the rotary frequencies (one tensor shared by every layer) stay frozen (the
  separation plan's choice for Mega-53, kept: a light fine-tune, less to overfit on 4 bands).
- **Recipe:** AdamW at X-LANCE's own learning rate 2e-5 and betas (0.8, 0.99), no weight decay; 100-step linear
  warm-up, then cosine to 0 at the step maximum; one 6-s window per micro-batch, 2 accumulated per step; global-norm
  clipping at 5 (each tensor's sum of squares on the device, the total on the CPU: MPS's `clip_grad_norm_` has
  returned NaN here), a non-finite step skipped (10 in a row stop the run); the config's dropout (0.1); fp32.
- **Loss:** the model's own: L1 on the waveform plus L1 on the multi-resolution STFT (windows 4096 to 256), weight 1.
- **Inputs and targets, zero renders.** For each F5 full twin, T3's build is redone exactly: the stored target render
  (`t3/audio/…-target.flac`), T2's stored other guitars, the section's stems, and the drawn ratio, loudness and
  mastering (`trusted_data.self_built_mix`).
  - The input is that mix, mono duplicated to two channels at 44.1 kHz, as the build fed gtr_mss.
  - The target is the wet target render as it sits in the mix: the render times the mix gain. For a mastered mix
    (1,704 of F5's 3,467) it is also multiplied by the compressor's gain curve and make-up gain (`compress_parts`,
    tested equal to `song_aug.compress`). The final −1 dBFS clip cannot be split per source and is left out.
  - Every rebuilt mix must reproduce its stored `mix-t3` half features (match share at least 0.99 on both halves), or
    `prep` refuses. Cached at 44.1 kHz in fp16 (about 6 GB).
  - A window whose target is below −50 dBFS RMS is redrawn (up to 20 tries).
- **The pipeline control (before any training).** Stock gtr_mss through this rebuild and the build's separation path
  must reproduce T3's stored stems: one FS5 example per section (12), each on the device its stored stem was made on,
  match share at least 0.99, or `prep` refuses.

### Cross-fitting by band: no stem D sees comes from a model that trained on its song

A separator fine-tuned on F5 and then run on F5 would hand D in-sample stems. And F5 and FS5 are only 4 songs, one per
band (11 DI tracks): a section is a DI track at a start time, so any split by section leaves every out-of-fold section
in a song, and nearly always a DI track, its model trained on. *(The first draft split by section; the independent
review of PR #313 found that near-useless, and it was changed before anything ran.)* So the fine-tune is cross-fitted
by band, 2 + 2:
- **The split** (`band_folds`, deterministic, no seed): of the splits into two pairs, the one whose F5 example counts
  are closest. Fold 0: Ale Lak and Death Of A Romantic (1,416 F5 examples); fold 1: Hollow Ground and Storm Of
  Particles (2,051).
- **Fold k** fine-tunes on its own bands' F5 examples, less 3 validation sections, and separates every F5 and FS5
  example of the other two bands. Measured (zero renders): fold 0 trains on 1,239 examples in 21 sections and
  separates 2,051 F5 and 363 FS5; fold 1 trains on 1,878 in 32 sections and separates 1,416 F5 and 359 FS5.
- So **every stem D trains on, early-stops on, is fitted on or is read on** comes from the model that never trained on
  that song, which is V-real's condition too (V-real's songs are new to both models).
- **FS5** never trains, validates or chooses anything in the fine-tune; its examples are separated with their band's
  F5 examples.
- **V-real-11's parts** are dealt alternately (seed 20261113): 6 to fold 0, 5 to fold 1.
- **What is still shared:** each model trains on 2 songs and separates 2 others. D's F5 (training) and FS5 (early
  stopping, fit, R0) stems are of the same 4 songs, as before; that is D's own design (FS5 is new sections of F5's
  bands), not the separator's. Two songs per fold is little to fine-tune on: the fine-tune may learn the 2 songs'
  backing more than guitar in general, which the out-of-band separation then shows honestly.

### Stopping on evidence, and the time

- **Validation** every 250 steps: the band mean of the mean SNR of the fold's validation examples (at most 120, a
  seeded subset; each full 10-s example in one pass) against their wet targets. Step 0 is the stock weights.
- **The validation sections are within-song:** 3 held-out sections of the fold's own two bands (seed 20261111; the
  bands in turn, one section each, round after round, a band always keeping a training section). So the stop rule
  reads how the fine-tune does on more of the songs it trains on, not on new songs; the out-of-band SNR (readout 1)
  is the new-song reading. Measured: fold 0 holds out 2 Ale Lak sections and 1 Death Of A Romantic; fold 1, 2 Hollow
  Ground and 1 Storm Of Particles.
- **Stop** when it has not improved by 0.1 dB for 1,000 steps (not before 500 steps), or at the step maximum: the
  approved time, 5.5 h of the gate's measured step time per fold (11 h in all), with a wall guard at 1.25 times that.
  A fold still improving when it stops is reported, not extended: an extension needs the user's yes. The best
  checkpoint (trainable tensors) separates.
- **Resuming:** a killed run resumes from its last checkpoint (recorded). That one file holds everything a resume
  needs (the trainable tensors, the optimizer, the step, the curve, the best tensors and their step) and is written
  atomically (a temporary file, then a rename) before the fold's record, so the record never runs ahead of it; the
  best checkpoint is written from it, atomically, when the fold stops. A resumed fold keeps the mode and step limits
  pinned in its record when it started, not today's `gate.json`. `prep` and `gate` skip when their record exists.

### The MPS gate (before training)

The model's forward and loss on MPS gave wrong gradients when the separation plan probed them (head gradient cosine
0.001 with the CPU's, trunk NaN), which fits the MPS STFT bug above 65,536 samples. So the gate runs first, on stock
weights with dropout off, on three cached F5 training examples (3, 6 and 10 s), against an all-CPU forward and
backward:
- **The test:** the loss within 1e-4 relative, and every trainable group's gradient cosine at least 0.999 (each of
  layers 8–11, the final norm, the mask estimator).
- **Modes, in order; the first that passes trains:** all on MPS; the STFTs and the iSTFT on the CPU (the gradients pass
  through the moves); that plus the loss on the CPU; all on the CPU (8 threads, the step maximum recomputed from its
  own step time; the probe measured about 3.4× slower).
- **Recorded:** the step time and peak memory at the training batch (5 timed steps). An MPS mode above 20 GB falls to
  the CPU.
- **Alone on MPS:** `gate`, `train` and `train-d` refuse while another MPS training job runs
  (`local_objective_1c.TRAINING`, which now lists `xlance_finetune gate` too, so other jobs see the gate).

### The re-separation

- Each fold's best checkpoint separates its examples through the build's path unchanged (`direct_stems.XLanceG`: two
  equal channels at 44.1 kHz, crossfaded 10-s chunks, the channel mean, back to 48 kHz), only the trainable tensors
  replaced. Half features are stored as `xlance_ft-t3`, as T3's `xlance_g-t3`.
- Two workers per fold, MPS ascending and CPU descending (MPS inference matched the CPU at 116 dB in the probe).
- Each row records the new stem's SNR against the wet target as T3's build measured it (the render times the mix
  gain), and T3's stored stock SNR for the same example.
- V-real's crops (the same `mix.wav` their stock stems came from) go through their assigned fold, hash-recorded.

### D_F5ft: D_F5-noaug with the fine-tuned stem

- **D_F5ft is D_F5-noaug (step (a)) in everything but the stem:** the 115-control heads, the masked loss and the amp
  head; F5's 3,467 full twins after F5's drops, and their labels; FS5's 722 for early stopping and the fit; seeds
  20261042 and 20261043, the cap and patience; D_stem's input (stem and mix channels) with augmentation off; the
  readout and the pull rule. Each run refuses unless every stem is in place and from the model that never trained
  on its band, and its examples are D_F5's.
- Unaugmented, because D_stem's augmentations imitate the stock separator's errors. The contrast with D_F5-noaug then
  differs in the stem alone.
- **The constant** is D_F5's (`fit` refuses otherwise); the pull is refitted on FS5.
- **V-real's input:** step (a)'s (the crop's mix through F5's path, hashes equal to F5's predictions'), with the
  fine-tuned stem in the stem channel. **Output gain** is fitted to the *stock* stem's search-half loudness, as F5 and
  step (a) did, so the gain does not move with the input.

### The readout, in order

**1. The stems (zero renders, descriptive).** Per fold: the validation curve (within-song), its best and the stock
point. Per set (F5 and FS5, every stem from the model that never trained on its song): the new stem's SNR minus the
stock one and the medians. With 4 songs, its interval is clustered by band (the mean of band means, 90% t on 3 df):
wide, and descriptive.

**2. FS5 readability (R0's rule, zero renders, descriptive), read before V-real.** D_F5ft's R0 table on FS5 beside
D_F5-noaug's and D_F5mix's (recomputed from step (a)'s stored models; their readable sets must reproduce step (a)'s),
and D_F5's (must reproduce F5's). D_F5ft trains on out-of-song stems and is read on out-of-song stems; the other
arms on stock stems. Paired per head and in the four summary rows, as step (a). R0's intervals are clustered by
section (FS5's 12 sections in 4 songs), which is optimistic here: read them as descriptive.
- **D_F5ft − D_F5-noaug (primary):** what the fine-tuned stem is worth, both unaugmented;
- D_F5ft − D_F5mix and D_F5ft − D_F5 (descriptive).

**3. The tone probe on the new stems (zero renders, descriptive).** `tone_info_probe`'s linear probes on the
fine-tuned stem's summaries, beside the stored mix (30) and stock stem (20): probe-trained on F5's stems and read on
FS5's, both out of song; readable heads per input, and the paired step fine-tuned − stock per head (section-clustered,
optimistic as R0's). This is the research's reading for a separator: what a linear reader recovers, not SDR alone.

**4. V-real (99 renders).** D_F5ft (pulled, plain readout), amp-fixed on the frozen V-real-11: 33 (part, amp) groups ×
(1 priming at S + 2 directions) = **99** renders. Rows log(d_a/d_b), lower is better, band-weighted, 90%
band-clustered t (7 bands), per class and V-real-10 beside:
- **D_F5ft − D_F5-noaug (primary)**;
- D_F5ft − D_F5mix, D_F5ft − D_F5 (descriptive);
- D_F5ft − D_core5 (the gate read with the fine-tuned stem), D_F5ft − S, D_F5ft − constant;
- beside: step (a)'s primary and F5's gate, as stored.

**No stop rule** between the readouts. **Reading (the user's rule):** effect sizes with intervals, no pass bar. An
interval below 0 is shown; a point below 0 with the interval holding 0 leans better and is built on; undecided is not
failed. **What it changes:** a stem that reads better becomes F20's input, with the fine-tuned separator. Otherwise the
record says where the fine-tune helped (SNR, the probe, FS5) and where it did not. Neither outcome runs F20 by itself.

### Cost

- **Prep:** about 20–30 min of CPU (4 processes) to rebuild and check 3,467 mixes, plus the control's 12 separations.
- **Gate:** up to about 30 min.
- **Fine-tunes:** up to 5.5 h each of measured step time (11 h in all), less at the plateau.
- **Separations:** 4,189, plus 11 V-real crops. At T3's rates (about 850 an hour on MPS, 1,350 with a CPU worker
  beside), about 3–5 h.
- **D_F5ft:** 2 runs of about 7–14 min of MPS; the fit, R0, the probe and V-real's predictions take minutes.
- **Renders:** none before V-real; **99** on V-real (a few minutes on 3 processes).
- **Disk:** about 6 GB of cache, about 1.3 GB of checkpoints (per fold: the last, with the optimizer and the best
  tensors, about 0.53 GB, and the best, 0.13 GB; a save briefly holds a second copy), about 0.4 GB of stem features;
  `check` refuses unless the 31 GB guard holds after them.
- **Wall time:** about 5–16 h in all, most of it the fine-tunes and the re-separation.
- **Machine rules:** every Morgan render isolate=True, one discarded priming render, the first 0.25 s trimmed; at most
  3 render processes machine-wide (`local_objective.RENDERS` lists `xlance_finetune vreal-render`); `prep`, `separate`
  and `vreal-stems` are listed as separations (no render starts beside them); the 31 GB disk guard and the swap guard.
