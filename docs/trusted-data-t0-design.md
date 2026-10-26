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
- Pending.

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
yet. K is empty, so T3 reads nothing on K.

**Two steps, cheapest decisive first:**
- **F5, the paired pilot.** T2's own examples, re-rendered with full-space labels, against a today's-space model on
  the same examples. It isolates what every control is worth, and gates the full build.
- **F20, the full build.** About 20k examples on every trusted section, and the primary read.

### 1. The label space

[Amendment 2](every-control-plan.md#amendment-2-2026-10-26-stage-2d-is-t3-and-its-label-space) declares it:
- **115 Morgan controls:** 86 continuous, 26 switches, amp choice (3-way) and the two mics (10-way). 77, 81 and 77
  sound with PR12, SW50R and AC20. Today's space is 25.
- **Encodings:** continuous on the unit interval, log for frequencies and times. Amp choice is a head that reads the
  audio only. The spring is a derived switch plus its level. Output gain is fitted to loudness, not a head (pending
  the user's explicit confirmation).
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
  - DGX's sessions are DI-only, so rule 1 keeps them where every playing guitar's DI passes.
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
    part A's class; else the intake's ear call on the amp track (Empty Signifier ElecGtr2, and the metal intake's tone
    cards: clean, crunch, high gain); else part A's classifier run on the section's own amp track. A section still
    unclassed counts as high gain if its band came in through the metal intake, and as not high gain otherwise (T2's
    unclassed bands, Ale Lak and Storm Of Particles); that is a stated limit.
  - The new draws are split so that **F20 holds at most 50% high-gain-source examples.** T2's examples were 61%.
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
- **Output gain:** fitted per answer to the loudness target (amendment 2; pending the user's explicit
  confirmation).

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
  half against the amp track, with no extra render. Marked pending the user's confirmation in code and records.
- **The wide gate cap** is the 95th percentile (nearest rank) of every menu preset's stored threshold, over the
  three amps: -61.3 dB from 111 presets.
- **The positive control's 50** are drawn with `seed_int(20261107, "positive control")`. They must match T2's
  stored target FLAC and part C's mels at 0.99. Built from the same T2 backing, their mix and stem features must
  match T2's `mix-t2` and `xlance_g-t2` at 0.99. Every run waits for it.
- **The amp head** is a 256-unit MLP on the pooled audio features. The readout's switches use the mean probability
  over seeds, for D_core5 too. A per-seed answer is that seed's A1, pulled by the model's b. A both-cabs-off answer
  turns on the likelier cab.
- **A cell dimension with no FS5 example that sounds** reads b = 0 (`cell_b`'s rule). It is printed and recorded,
  not refused.
- **V-real:** It Was My Fault ElecGtr1 has no stage-F-style crop yet (`vreal-crops` is not in this code).
  `vreal-predict` refuses a frozen member without a crop, unless `--drop-missing-crops` drops it (printed) before
  any read.
- **The dry run's gain classes:** part A's classifier on the amp tracks classes most Ale Lak and Storm Of Particles
  sections high gain. So T2's examples are 96% high-gain-source by the declared order (61% by part A's class
  alone, the plan's figure). F5 keeps T2's mix; the 50% cap applies to F20.

### Open for the user

1. **Clean and crunch sources for F20** (open since T0). After the ear the pool holds 1 clean-class and 1 crunch
   section of 181, and Empty Signifier's DI is high gain. Options:
   - (a) download Strobe "Maya" and MekaPhil ×4 (about 2.4 GB, not on disk). They are DI-only sessions: every guitar has a DI, so rule
     1 keeps them. About 75 sections in 2 bands, gain unknown. They need T0's checks and one ear sitting.
     Recommended;
   - (b) EGDB (on disk) on borrowed backings;
   - (c) none.

   F5 can start without any of these.

The metal intake needs no decision here: its DIs join F20 as they pass the checks and the ear, under the caps.
