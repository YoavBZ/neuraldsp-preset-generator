# Trusted data, T0 to T2: the code, the calibration and the launch (design)

**Status (2026-10-23):** T0 ran on the user's Mac (calibration OK; the lists and the ear queue; see the ROADMAP and the
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

**Other guitars** respect T0's unusable sections.

**The read:**
- K − V_sep mel-grid stem SNR, paired on the same examples and draws.
- Band-clustered with two or more bands. With one band (K may be Adam Buckley alone), the
  section-clustered interval is primary.
- V-real's stored crop stems beside, by ratio.

**Plans carry T0's lists' sha256 (`t0/verified.json`).** `render`, `build`, `t1-read`, `train`, `fit` and `e-on-k`
refuse when it has changed.

| Step | Command | Cost |
|---|---|---|
| plan | `$MAIN -m learn.trusted_data plan --stage t1` | zero renders |
| render | `$MAIN -u -m learn.trusted_data render --stage t1 --shard k/3` | about 0.8–1.5k renders plus priming |
| build | `$MSST -m learn.trusted_data build --stage t1 --device mps --order asc` (CPU worker beside) | about 370 separations, about 30 min |
| read | `$MAIN -m learn.trusted_data t1-read` | minutes |

## T2 (`trusted_data`, the 5k pilot; code only)

**The examples:**
- **The pilot:** 5k trusted-pool examples (seed 20261099, stratified by band) on usable sections.
- **The early-stopping set:** about 5% of sections, at least one per band (seed 20261100), at most
  1,000 examples.

**The arms:**
- **SES:** the stored stems.
- **SYN:** the same examples, labels and draws, with self-built backings.
- **SYN-E:** a seeded third (seed 20261101) swapped for Eggy. It is recorded as refused while no *Dropped from T2 for now (user, 2026-10-24).*
  Eggy DI is trusted, which the ear now implies.

**Training:** D_stem's recipe, 2 seeds per arm. The constant and pull are fitted per arm on its
early-stopping set.

**The reads:**
- **Primary:** SYN − SES on V-real, by the judge with the measure DI. Paired by direction,
  band-weighted, 90% band-clustered. A tie under 0.03 picks SYN.
- **Beside:** SYN-E − SYN, each arm − S, E on K, and T1's stem SNR.

| Step | Command | Cost |
|---|---|---|
| plan, render | `$MAIN -m learn.trusted_data plan --stage t2`; `$MAIN -u … render --stage t2 --shard k/3` | about 12–18k renders, 2.5–3.5 h on 3 processes |
| build | `$MSST -m learn.trusted_data build --stage t2 --device mps` | about 6k separations, 5–8 h |
| train | `$TORCH_PY -m learn.trusted_data train --arm SES\|SYN --seed 20261042\|20261043` | 4 runs, about 1.5 h MPS |
| fit, E on K, V-real | `fit`, `e-on-k`, `vreal-predict` (TORCH_PY); `vreal-render --shard k/3`, `report` (MAIN) | about 231 renders at 11 V-real parts (66 per arm for SES, SYN and the constant, plus 33 priming; about 300 if SYN-E runs) |

## Open questions

1. **The ear queue is large: 195 items** (184 live after the queue fixes; resolved by the sitting). The 37 `di_amp` items cover the D1 rule on metal DIs,
   and other-guitar windows add flagged items. T2 waits until the ear has answered.
2. **SYN-E has no Eggy.** *Decided 2026-10-24 (user):* dropped from T2 until a clean-class DI source (EGDB or GOAT) passes the DI checks.
3. **K may be one band.** Admit Cnoc An Tursa despite its MUSDB18 tag?
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
  `vreal-render` renders it with the others (about 66 renders per arm at 11 parts), and `report` reads SES − constant, SYN − constant
  and constant − S beside the primary. The reading rule is unchanged.

