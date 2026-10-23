# Trusted data, T0 to T2: the code, the calibration and the launch (design)

**Status (2026-10-23):** code only, for an independent review. Nothing here has run as T0, T1 or T2.
The numbers below come from zero-render dry runs on the stored crops and sections, written to a
scratch folder; they show what T0 should find, not T0's record. One input arrived during the work
and is built in: the user's sitting 1 of data-review-1 judged the crops' **DI** clip, not the amp
clip (see D4).

- **Plan:** [trusted-data-strategy-plan.md](trusted-data-strategy-plan.md), approved with its
  recorded decisions.
- **Code:**
  - `learn/verify_tracks.py`: the standard, its calibration and T0;
  - `learn/trusted_data.py`: the self-built mix builder, T1 and T2.
- **Tests:** `tests/test_verify_tracks.py`, `tests/test_trusted_data.py`.
- **Machine rules:**
  - The two render commands are in `local_objective.RENDERS`: `verify_tracks negatives`, and
    `trusted_data render` and `vreal-render`.
  - Renders run with isolate=True, a priming render, and at most 3 processes machine-wide.
  - Disk guard 31 GB. No downloads.
  - Real runs need a `trusted-data` entry in `dev-test-ledger.json`. It was not added here.

## The standard as built

Per judge half of a crop (A 1.0–5.5 s, B 5.5–10.0 s), `reference.wav` against `di.wav`.

| | Measure | Pass | Moved? |
|---|---|---|---|
| A1 | GCC-PHAT lag over 80 Hz–4 kHz | 0.1 ≤ \|lag\| ≤ 30 ms; a negative lag, or a peak under 12× the median (unreadable), goes to the ear | band and prominence gate added |
| A2 | H1 = S_xy/S_xx (Welch 4096), coherence ≥ 0.5; median \|H\| 1–3 kHz minus 6–10 kHz | ≥ 3.3 dB; a half with under 17 coherent bins in either band goes to the ear. A part fails if a deciding half fails | 12 → 3.3 dB; 17 bins declared |
| A3 | Least-squares FIR (exact covariance, 24 kHz, −5..+60 ms around the A1 lag), fitted on one half, read on the other, both ways | both residuals above −40 dB | no |
| A4 | Peak \|r\| (±50 ms) with every session DI; file hash | < 0.95; no shared hash | no |
| A5 | `crop_match2.py`'s measures (ported) | play share ≥ 0.5; chroma ≥ 0.8 or onset ≥ 0.35 | no |
| A6 | The bleed audit's bleed per half; for parts read in a mix (stage F), an electric same-part track (the cleaning plan's `same_part`) in the mix | bleed < −30 dB; such a track < −30 dB of the target | "another take" limited to electric guitar tracks |

**Gates on the measures:**
- A1–A3 read only halves where the DI plays on at least 25% of frames.
- A part whose crop DI is silent and that feeds the level prior is read on up to 3 of its
  prior sections instead.

**DIs:**
- **D1:** against the loudest own amp track, per section. The DI's verdict uses the median of its
  readable lags and the median drop of its deciding halves (a chain property, read robustly).
- **D2:** part A's flags on the window (clipping, drop-outs, hum ≥ −55 dB), plus part A's
  hum-suspect list. This is decision 2: hummy measure DIs are excluded.
- **D3:** by name (pedal board, line out, FX, sims).
- **D4, new:** see below.
- **The rule:** a measured fail is excluded. "To the ear" is not a fail: a DI stays in use and is
  queued for the ear. A target is trusted only once the ear has heard it clean, and as an amp
  where A1 or A2 went to the ear.
- **The two disputed parts:** Quicksand ElecGtr2 and Today's The Day ElecGtr07 stay excluded
  until the user's ear rules.

### D4, the DI is unprocessed (user, 2026-10-23)

**Measures** (`di_processing`, on the playing 100-ms frames):
- the median crest factor;
- the slope of brightness (3–8 kHz over 0.1–1.5 kHz) against level. A clean pickup gets brighter
  when picked harder; a saturating stage flattens this.

**Rule:** the DI reads as processed when crest < 8.4 dB or slope < −0.2.

**How the rule was chosen.** It was set on the user's 35 heard crop DIs. Of the features tried,
it is the best simple rule:
- crest alone: 0.86;
- leave-one-out logistic regression on crest and slope: 0.89;
- not separating: kurtosis, spectral tilts, LPC residual, waveform echoes, distance to the amp
  track.

**Agreement with the ear: 30 of 35.**
- **Heard processed, 17:** 16 caught. Missed: Gym Hours GTR 2, which reads like a clean amp.
- **Heard clean, 18:** 14 passed. Flagged: Drag Me Down ElecGtr4, Quicksand ElecGtr2, Signs
  ElecGtr2, colour-me-red elecgtr03.

**The ear is authoritative both ways on heard DIs.**
- A heard-processed DI is excluded with all its sections.
- Passing Ships ElecGtr4 counts as heard processed: half B was marked "other guitar, sounds like
  amp".

**On unheard DIs the measure decides per section.** A DI whose sections fail by majority is
excluded whole.

**Gaps:**
- No measure separated delay, modulation or an amp or cab signature on these 35. First Offering
  GTR 2's delay is caught by its crest factor.
- About 1 in 5 heard-clean DIs is flagged, so D4's flags on unheard DIs need the ear (see the
  open questions).

## Calibration (`negatives`, then `calibrate`)

**The cases:**
- **Known amps:** the 18 known amps.
- **Known fails:** Prodigal ElecGtr3 and ElecGtr5.
- **Constructed negatives** on two DIs (Passing Ships ElecGtr4, magilla elecgtr1):
  - a copy;
  - an EQ'd DI: a 4th-order 80 Hz–5 kHz band-pass with a +6 dB peak at 2 kHz, delayed 1.5 ms.
    This passes A1 and A2 by design, so only A3 can catch it.
  - the DI levelled to −22.9 LUFS by one gain, through PR12 with the cab section off: the clean
    start is declared, the crunch start is read beside. 6 renders.

**CALIBRATION OK needs all of these:**
- every known amp fails none of A1–A4;
- both known fails fail one of them;
- the copy fails A1, A3 or A4;
- the EQ'd DI fails A3;
- the clean cab-off DI fails A2.

The record holds every reading, the margins, the threshold moves and D4's agreement with the ear.
`targets` refuses without a real OK under the current thresholds.

**The zero-render part, read in the dry run:**

| Case | A1 lag (ms) | A2 drop (dB, coherent bins) | A3 residual (dB) | A4 r | Status |
|---|---|---|---|---|---|
| 18 known amps | 0.17–20.1 (TTD07 −1.1: ear) | 7 decide, 6.2–27.5; 11 to the ear | −0.7 to −32.0 | ≤ 0.94 (magilla 1DT) | none fails |
| Prodigal ElecGtr5 | 0.0 / 0.0 | −0.3 / 0.4 (324, 255) | −4.8 | 0.82 | A1, A2 fail |
| Prodigal ElecGtr3 | 0.0 / 0.0 | 0.0 / −0.1 (342) | −6.4 / −10.9 | 0.93 | A1, A2 fail |
| Copies (2) | 0.0 | 0.0 | −90 to −117 | 1.0 | A1–A4 fail |
| EQ'd DIs (2) | 1.58 | 23.2 | −80.5 to −108.4 | 0.68, 0.94 | A3 fails |
| Cab-off, PR12 clean and crunch (2 + 2) | — | — | — | — | pending `negatives` |

**Threshold moves** (recorded in `THRESHOLD_MOVES` and the calibration record):
- **A2, 12 → 3.3 dB.** The plan's 12 dB fails the known amps colour-me-red elecgtr03 (6.2 dB,
  half A) and Signs ElecGtr2 (10.3 dB). 3.3 is the midpoint between Prodigal ElecGtr5's 0.4 dB and
  6.2. If the cab-off DI reads above it, calibration fails, and the threshold moves to the
  midpoint of the new closest pair.
- **A2 minimum bins, 17 (new).** The plan gave no number. Quicksand ElecGtr2 (12 and 10 bins,
  −2.5 and −3.9 dB: a flat linear path at the top) falls under it and goes to the ear.
- **A1 band and prominence gate (new).**
  - The full-band GCC reads 0 ms on 9 of the known amps, which carry a zero-lag path above
    4 kHz. The band-limited lag agrees with the stored `di_lag_ms`.
  - The known amps' peaks stand 24–279× over the median. Unreadable high-gain pairs (Adam Buckley
    ElecGtr2 and 2DT) stand 4–7×. The gate sits at 12.
- **D4 (new):** set on the user's labels, as above.

## T0 (zero renders apart from calibration's 6)

Run from the merged checkout. Expected times, CPU unless stated:

| Step | Command (`MAIN=…/.venv/bin/python`) | Time |
|---|---|---|
| 1 | `$MAIN -u -m learn.verify_tracks negatives` (6 renders) | about 2 min |
| 2 | `$MAIN -m learn.verify_tracks calibrate --ear-di <sitting-1 export>` | under 1 min |
| 3 | `$MAIN -m learn.verify_tracks targets` | about 1 min |
| 4 | `$MAIN -m learn.verify_tracks dis --shard k/3` (k = 0, 1, 2) | about 1–2 min each |
| 5 | `$MAIN -m learn.verify_tracks inject-strict` | about 20–40 min |
| 6 | `$MAIN -m learn.verify_tracks stem-scan --shard k/3` | about 30–45 min each (20 sessions, 101 guitar sources; the dry run read Hollow Ground, 8 sources over 142 s, in 235 s) |
| 7 | `$MAIN -m learn.verify_tracks lists --ear-di <sitting-1 export> [--ear <target export>]` | under 1 min |
| 8 | `$MAIN -m learn.verify_tracks reread` | under 1 min |

The sitting-1 export is
`~/.claude/uploads/67cfc004-f421-4d92-9cce-0e70317476ec/9422aa1d-data-review-1-sitting-1.json`.

**What each step covers:**
- **`targets`** reads every label-table part in use: stage F, knob ceiling 2, the listening pages'
  parts, the level prior's 38 parts, and the calibration parts.
- **`dis`** reads:
  - the D build's 30 pool DIs and 21 V_sep DIs, per section;
  - the other DIs of those sessions, at the session's section times and at up to 4 of their own
    clean sections;
  - every crop's measure DI.
- **`stem-scan`** reads every guitar part's session-level take in every non-guitar track (the
  cleaning plan's estimator). It uses one source per part: the loudest amp or mic track, or the
  DI when the part has none. A take reaches a room through the amp, and a part's mics carry one
  take. Its floor is −30 dB, or −35 or −40 dB if `inject-strict` validates that level on the 3
  deciding sessions. In the dry run, Hollow Ground validated both stricter levels.
- **`lists`** writes `t0/trusted.json`:
  - targets by use, trusted, pending the ear, or excluded with their reasons;
  - DIs, and the sections D4 excludes;
  - passing stems;
  - V-real, and the knob ceiling 2 panel;
  - K's DIs and the training DIs;
  - D4's agreement with the ear and the excluded sections per band;
  - the re-derived level prior beside the old one.
- **`reread`** re-reads, beside each stored headline, on the panel with no measured fail (the
  ear-confirmed subset with `--trusted-only`):
  - knob ceiling's K_S − S;
  - K_S ceiling's extension;
  - knob ceiling 2's (e) and its time effects, listing the large cells on failing parts;
  - amp choice.

  It also prints the dated notes and the listening footnotes: record-match trial 5; arm A's
  trials 1–3 and 8 against 4–7; knob ceiling 2's clear-gain trials. The notes go into the results
  docs once T0 has run, not before.

**What the dry run shows T0 should find** (scratch, zero renders):

**Targets:** 59 parts; 43 excluded, 16 pending the ear, 0 trusted until the target-vs-DI page
records clean and amp.

**Stage F (V-real) keeps 11 parts in 7 bands, all pending the ear:** It Was My Fault ElecGtr3,
Signs ElecGtr3, colour-me-red 02 and 03, femme 5, get-out-of-bed 2, let's dance 3 and 4, and
wickerman 1, 2 and 3. Excluded, beyond the plan's list:
- Passing Ships ElecGtr2: A1 and A2 (a zero-lag path, no roll-off);
- Passing Ships ElecGtr4: measure-DI hum, and heard "sounds like amp";
- magilla elecgtr1: its DT double sits in the mix at +1.3 dB;
- wickerman elecgtr7: a hum-suspect DI;
- Gym Hours GTR 2: DI hum, and heard processed.

**Knob ceiling 2 keeps 5 parts,** down from the plan's 12: Drag Me Down ElecGtr4, It Was My Fault
ElecGtr2, Quicksand ElecGtr1, Signs ElecGtr2 and get-out-of-bed elecgtr1. The others go on hum,
processed DIs or A5/A6. Also excluded:
- just-don't-talk elecgtr3: A2 fails (−5.8 and −6.3 dB);
- Prodigal ElecGtr2: lag about 0 in 2 of 3 of its session windows.

**Pool and V_sep sections excluded by D1–D4 and the ear:**

| Band | Excluded |
|---|---|
| Eggy | 96/96 (all three DIs heard processed) |
| Rebuild The Evil | 20/30 |
| Dark Ride | 13/13 |
| John Morgan Kimock | 12/12 |
| Swatkins | 7/7 |
| Death Of A Romantic | 5/32 |
| Storm Of Particles | 5/24 |
| Adam Buckley | 1/13 |
| Ale Lak | 1/31 |
| Cnoc An Tursa | 1/10 |
| Renesans | 1/37 |
| Starnes And Shah | 1/1 |
| Hollow Ground | 0/25 |
| The Long Wait | 0/1 |

**The level prior** is re-derived on 308 values in 11 bands (median −7.8 dB, 5–95% −11.6 to
−2.9), against 971 values (median −7.9, −18.9 to −2.7).

## T1 (`trusted_data`, no training)

**K** is R_in's examples:
- outside Kimock and Swatkins (recorded decision);
- outside the MUSDB18-tagged Bannockburn;
- on DIs and sections that pass T0;
- each with R_in's stored truth render.

**The self-built backing** (plan (c), `trusted_data` docstring):
- **Other guitars** are the session's trusted DIs that play in the section: at most 4, the most
  active first. Each renders with its own preset (seed 20261102), sits at its amp track's LUFS
  (else the session's amp median, else the stems' median), and is pan-folded. A DT double takes
  the target's settings, panned opposite.
- **Stems** are those that pass the scan, at the session's balance.
- **Draws:** part C's ratio, vocals, loudness and mastering, so K and V_sep are paired.

**The read** is per-example stem SNR on the stored mel grid:
- K's self-built stem against V_sep's stored X-LANCE stem of the same example and draws, paired;
- band-clustered 90% intervals, section-clustered beside;
- the audit's contamination beside;
- by ratio bin, and at V-real's ratio range, with V-real's stored crop stems against their amp
  tracks.

| Step | Command | Cost |
|---|---|---|
| plan | `$MAIN -m learn.trusted_data plan --stage t1` | minutes, zero renders |
| render | `$MAIN -u -m learn.trusted_data render --stage t1 --shard k/3` | about 0.8–1.5k renders plus priming; about 10–20 min on 3 processes |
| build | `$MSST -m learn.trusted_data build --stage t1 --device mps --order asc` (`--device cpu --order desc` beside) | about 370 separations; about 30 min on MPS |
| read | `$MAIN -m learn.trusted_data t1-read` | minutes |

## T2 (`trusted_data`, the 5k pilot; code only)

**The examples:**
- **The pilot:** 5k trusted-pool examples (seed 20261099, stratified by band). These are the
  cleaning manifest's trusted examples on T0-trusted DIs and sections, Eggy aside.
- **The early-stopping set:** about 5% of the trusted sections, at least one per band (seed
  20261100), held out of the draw, at most 1,000 examples.

**The arms:**
- **SES:** the stored stems (the manifest's rebuilt files where listed).
- **SYN:** the same examples, labels and draws, with self-built backings. Targets are re-rendered
  and refused unless part C's mels match.
- **SYN-E:** SYN with a seeded third (seed 20261101) swapped for Eggy. The plan records it as
  refused when no Eggy DI passes T0, which the ear now implies.

**Training and fitting:**
- D_stem's recipe (`direct_stems.train_arm`, augmented), 2 seeds per arm.
- Early stopping on the set in each arm's own mix type.
- Per arm, the constant (its training-label medians) and amendment 5's pull, fitted on the set.

**The reads:**
- **Primary:** SYN − SES on V-real, by the judge with the measure DI. Paired by direction,
  band-weighted, 90% band-clustered. A tie under about 0.03 picks SYN (recorded decision 4).
- **Beside:** SYN-E − SYN, each arm − S, E on K, and T1's stem SNR.

| Step | Command | Cost |
|---|---|---|
| plan | `$MAIN -m learn.trusted_data plan --stage t2` | zero renders |
| render | `$MAIN -u -m learn.trusted_data render --stage t2 --shard k/3` | about 6k targets plus about 6–12k other guitars, plus priming; about 2.5–3.5 h on 3 processes |
| build | `$MSST -m learn.trusted_data build --stage t2 --device mps --order asc` (CPU worker beside) | about 6k separations; about 5–8 h |
| train | `$TORCH_PY -m learn.trusted_data train --arm SES\|SYN --seed 20261042\|20261043` | 4 runs, about 1.5 h MPS |
| fit, E on K | `$TORCH_PY -m learn.trusted_data fit`, then `… e-on-k` | minutes |
| V-real | `$TORCH_PY -m learn.trusted_data vreal-predict`, then `$MAIN -u -m learn.trusted_data vreal-render --shard k/3`, then `$MAIN -m learn.trusted_data report` | about 33 groups × 5, about 165 renders |

## Open questions for the review and the user

1. **D4 on unheard DIs.**
   - It flags about 1 in 5 heard-clean DIs.
   - Rebuild The Evil (20/30 sections) and Dark Ride (13/13) are flagged by measure alone. Should
     the user hear a sample of the flagged pool DIs before T2?
   - Is the ear's DI verdict per part (as built) or per section?
2. **SYN-E cannot run.** All Eggy DIs were heard processed. The options: drop SYN-E, or name
   another clean-class source (none passes today).
3. **K shrinks to Adam Buckley alone.** Dark Ride fails D4, Bannockburn is MUSDB-tagged, and
   Kimock and Swatkins are out. T1's paired interval then has one band, so the section-clustered
   reading stands alone. Should K add Cnoc An Tursa, despite the separator-overlap tag?
4. **Calibration's cab-off negative is pending (6 renders).** If it reads above 3.3 dB, A2 moves
   again by the recorded rule.
5. **The ledger needs a `trusted-data` entry** before any real run.
6. **Targets have no "heard clean" verdict yet.** Sitting 1 judged the DIs. Every V-real and knob
   ceiling 2 part waits for a target-vs-DI page that asks clean and amp.
