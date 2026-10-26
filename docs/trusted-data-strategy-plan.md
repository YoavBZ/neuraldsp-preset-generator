# Trusted data: a self-built training set and a verified real test: plan

**Approved by the user on 2026-10-23,** with the [recorded decisions](#recorded-decisions-user-2026-10-23)
at the end; [notes after approval](#notes-after-approval-dated) follow them. It was drafted with zero compute: only
stored files were read.

It answers the user's direction of 2026-10-23: "Consider only using songs with mix+guitar amp
track+guitar DI, which are clearly distinguishable, or using a totally different approach if
generating the entire dataset ourselves so it's accurate and can be trusted."

- **Nothing runs until the user decides.** Each stage then gets its own declaration, an independent
  review and a ledger entry.
- **Development data only.** Sets 4–6, Guitar-TECHS P3 and every reservation in
  `dev-test-ledger.json` stay untouched (except JHNC, read once at T4 as its reservation allows),
  and step 7 is unchanged.

**Terms:** K, the self-built known-answer test; V-real, the verified real set; SES and SYN,
training on session mixes and on self-built mixes; E, masked knob error; log d, the judge's log
distance ratio.

## The short version

- **The hybrid:**
  - Training and development use mixes we build ourselves. The labels are renders of verified DIs,
    and the backing comes from verified DIs and bleed-free tracks.
  - The final development test is V-real: parts with a mix or full backing, an amp track that is
    clearly an amp, and a DI that is clearly a DI.
  - The user's ear on real songs is the last check.
- **Why.** Under the user's decision of 2026-10-23, the trusted session pool is 8.7k examples from
  6 bands, about 70% from high-gain-class DIs and none clean-class: Eggy, the only clean-class band,
  is out for live bleed. Self-built mixes can bring it back with a backing we can trust.
- **The limit.** K measures how well a model recovers Neural DSP settings from Neural DSP renders.
  Only V-real and the ear speak to real amps in real rooms.
- **The order:** zero-render checks (T0); a stem-quality check (T1); a 5k pilot (T2); then one
  rebuild that is also the coverage plan's stage 2D (T3).

## (a) The verification standard

**Targets** (per judge half, on the crop's `reference.wav`, the main mic the tests use; the
project's pairing check never tested for an amp or a cab):

| # | Measure | Pass |
|---|---|---|
| A1 | Mic delay: DI-to-target lag (stored as `di_lag_ms` in the bleed table) | \|lag\| 0.1–30 ms. A negative lag is a recording offset, sent to the ear. Any processor with latency also passes, so A1 never decides alone |
| A2 | Cab roll-off: H1 = S_xy/S_xx (Welch), bins with coherence ≥ 0.5 | \|H\| over 6–10 kHz at least 12 dB under \|H\| over 1–3 kHz. Too few coherent bins above 6 kHz goes to the ear (checked in calibration) |
| A3 | Linear copy: residual of the best linear filter, DI to target, fitted cross-half | above −40 dB. This only rules out an EQ'd copy: amp parts read −2 to −27 dB, Prodigal ElecGtr5 −5 dB |
| A4 | Not a copy | peak correlation with every session DI below 0.95; no shared file hash |
| A5 | Same take (the cleaning plan's rule) | `di_play_share` ≥ 0.5; chroma ≥ 0.8 or onset r ≥ 0.35 |
| A6 | Clean (the cleaning plan's rule) | bleed under −30 dB; no other take of the part |

**DIs:**
- **D1:** the DI passes A1–A2 against its amp track.
- **D2:** on the crop window itself, no clipping or drop-outs. Hum, hiss and bleed into the DI are
  measured and shown to the user.
- **D3:** not a line out or processor output, by name and spectrum.
- **DI-only parts** take D2–D3 and the ear. They can be training or K DIs, never V-real targets.

**The ear and the rule:**
- The target-vs-DI page plays the DI, then the target. The user marks clean or not, and amp or not.
- A part is trusted only if it passes the measures and the user hears it as clean.
- A measured fail is excluded, not flagged. It goes to the user with its numbers (decision 2).

**Calibration, before any other part is read:**
- **Known amps:** the 18 targets heard clean and measured as amps must pass A1–A4.
- **Known fails:** the 2 Prodigal targets must fail. They read 0.0 ms, against magilla's 0.17 ms,
  the smallest real amp.
- **Constructed negatives:** a DI copy, an EQ'd DI and a DI through Morgan with the cab off (about
  6 renders). Morgan adds 52 samples (1.08 ms) of latency, so the cab-off case tests A2, not A1.
  Today's The Day ElecGtr07's −1.08 ms is also 52 samples; its judge lag (about 1.6 ms) suggests a
  coincidence, which T0 checks.
- **A threshold moves only** to separate these cases, toward keeping the known amps, and each move
  is recorded.

**What fails or waits today:**
- **Prodigal ElecGtr5 and ElecGtr3:** processed DIs with no cab. The session's other parts (ElecGtr1, 2, 4) are measured first in T0.
- **Stage F under A5–A6 (16 of 21 pass, in 10 bands):**
  - Russian Cream GTR 1, She's Gone and Strangest Places fail on high bleed.
  - Quicksand ElecGtr2 fails at −21 dB.
  - Today's The Day ElecGtr07 fails in half A (chroma 0.70, onsets 0.29) and has a lag of −1.08 ms.
  - The user heard both of the last two as clean: these are conflicts for the user.
  - 7 of the 16 are not yet on the target-vs-DI page.
- **Knob ceiling 2:** 13 of 24 parts pass A5–A6; after Prodigal's A1–A2 fail, 12 remain in 11
  bands (8 clean, 4 crunch). Dom McLennon, Doom Flamingo and Starnes And Shah lose every part. 8 of
  the 12 are not yet measured.
- **Measure DIs:** part A's stored flags give 8 of the 16 stage F candidates no clean section (hum,
  hiss, bleed or drop-outs), colour-me-red elecgtr03 was never screened, and wickerman elecgtr7's
  DI is hum-suspect. D2 on the crop windows
  decides; hummy measure DIs are decision 2.
- **Knife-edge passes, for the ear:** let's dance elecgtr3 (bleed −30.1 dB), Gym Hours GTR 2
  (−30.4 dB), Farthest Step (−31.4 dB), wickerman elecgtr3 (chroma 0.81), and the audit's low
  guitar shares (femme elecgtr5, wickerman 1–3, let's dance 3–4).
- **The data-review page** says "2 amp mics summed" but plays only the main mic. That is the
  tested target, so the verdicts stand, and the label is fixed.

**Results that rest on failing parts** are re-read from stored cells at zero renders, with a dated
note beside each headline; nothing re-runs.
- **Knob ceiling 2's time effects:** all three clear-gain listening trials sit on failing parts
  (Sculptor's Request GTR 2, Blind Spots, Prodigal), and so do the large delay cells. Their priority
  comes from the judge re-read on the 12 parts; the coverage plan's time-effect row gets the note.
- **The 24-part panel** (K_S ceiling −0.293, knob ceiling −0.253, knob ceiling 2's (e) −0.023,
  amp choice −0.048 declared and −0.044 part-weighted, and the other panel results) is re-read on the
  12 parts. Every-control stage 1 runs on them, as already decided.
- **Listening:** record-match trial 5 is Today's The Day ElecGtr07; arm A's trials 1–3 and 8 fail,
  but its "4 of 4 heard arm A" sits on passing parts.
- **The level prior:** about 550 of its 971 sections come from failing parts (13 from the two
  Prodigal parts; ElecGtr1 and 2 add 38, unmeasured). It is re-derived on parts that pass A1–A4 and
  A6 (a crop-only A5 fail keeps the part's other sections), with the old prior beside it. It is a
  level statistic, not a label; most of it comes from V-real's bands, which is stated.

## (b) Sources for the self-built mixes

| Group | Sections by class (part A) | Role |
|---|---|---|
| 9 training bands (Starnes And Shah out until its DIs pass) | 277: clean 97 (96 Eggy), crunch 1, high-gain 111, unclassed 68 | training |
| V_dev, 5 bands | 55 | K |
| Stage F, 12 bands | 401 | V-real; never trains |
| Jen Hartswick & Nick Cassarino (JHNC), reserved | 4 DIs, 20.4 min | V-real, read once at T4 after the user has heard it |
| Strobe "Maya", MekaPhil ×4 (allowed, not on disk) | about 75 | training; 2.4 GB download needs a yes |

- **Stems.** By file name, the 7 Cambridge studio sessions of the training bands hold about 53 drum
  and room mics, 30 vocals, 9 bass and 6 keys tracks. Telefunken live sessions give only
  line-level tracks (bass and keys DIs).
- **The stem scan.** A stem passes when every guitar track of its session reads under −30 dB in it.
  The cleaning plan's take estimator is validated at that level. T0 also runs its injection check
  at −35 and −40 dB, and adopts a stricter floor only if it validates.
- **Gaps.** One clean-class band (Eggy) and one crunch section. Eggy's backing becomes a bass DI
  and 2 keys tracks; Renesans' a bass DI and its line-level playback tracks (never `GTR Pre Rec`, a
  double of the riff). The Cambridge scan found no new DI-and-amp band on the hosts it could read.
  Blue Manic "Acomatay", downloaded through the user's browser on 2026-10-23, is a reserved test
  band with 5 DI + amp pairs. It is not in this plan's V-real or T4; a test that uses it declares
  its own gate in its own ledger entry. EGDB (downloaded the same day) and GOAT have no session, so
  they stay out of T3 unless the user accepts a borrowed backing.

## (c) How a mix is built

- **Unit:** a 10-s section, as in part C, deterministic from its index. The recipe is stored; the
  audio is not.
- **The target:** a verified DI section through drawn settings over every control: the coverage
  plan's table (`learn/every_control.py`) with part C's draw for today's space and a separate
  seeded stream for the rest.
  - Switched-off knobs are masked.
  - Output gain and pan are learned against every-control amendment 1's targets (loudness; the
    stereo build).
- **Other guitars:** the session's other verified DIs at the same moment, each through its own
  drawn preset.
  - **Level:** each sits at its real amp track's level in that section. A DI-only part takes the
    median level of the session's amp tracks.
  - **Doubles:** a "DT" double takes the target's preset, panned opposite.
  - **Parts with no DI** are left out (decision 4). *Since 2026-10-25 (user):* an active guitar that cannot be
    rendered is the session's own amp track(s) after an automatic bleed check, or the example is left out
    ([the 2026-10-25 note](#notes-after-approval-dated), [design](trusted-data-t0-design.md#rule-1-after-the-users-decision-2026-10-25)).
- **Other instruments:** stems that pass the scan, at the session's own balance.
- **Level:** the backing is set against the target by a ratio drawn from the re-derived level prior
  (today: median −7.9 dB, 5–95%: −18.9 to −2.6 dB).
- **Pan, vocals and mastering:** built in stereo from a declared pan prior and folded to mono as at
  inference; vocals with p 0.5; compressor and limiter with p 0.5; loudness at the evaluation median
  ±3 dB; all before separation, as today.
- **Controlled bleed (optional, off in T2):** the target's own render through the bleed test's
  synthetic rooms, at −18 to −14 dB in the drum and vocal stems, so the bleed carries the label's
  tone.

## (d) What the separator sees, and its cost

- **What it sees:** no other take of the target and no original-tone bleed (the gain over SES, where
  the target render is known too). The risk is stems that are too clean: every guitar is a Morgan
  render, with no real other amps, while on stage F the other guitars sit 5.5 dB above the target.
  T1 measures the gap.
- **Cost:** X-LANCE gtr_mss as is (Mega-53 the fallback), at 4.3–5 s a clip on MPS alone or
  0.29–0.35 clips/s with the CPU worker. Separation sets the wall-clock ((g)).

## (e) Tests

| Test | What | Read |
|---|---|---|
| **K** | V_dev's DIs in mixes built from their own sessions' clean stems; the truth rendered through the example's DI, as step 3's gate did | E (zero renders); the sound gate, log d of D against the constant. *Empty since 2026-10-25 (no example passes rule 1's bleed check): no E on K and no sound gate until a better leakage measure, or another route, brings K back ([design](trusted-data-t0-design.md#t1-waived-and-the-realism-check-moved-into-t2-2026-10-25))* |
| **V-real** | Stage F's parts that pass (a) (up to 16, 10 bands), plus JHNC at T4 | D − S and arm A − S by the judge with the measure DI; band-weighted, 90% band-clustered. The primary input is the unity sum (all parts have one); the released mix (10 songs) is a second reading |
| **The ear** | Real, guitar-exposed songs: S, D and arm A, blind, letters at random | the user's picks |

- **Stage F is shrunk to V-real.** Its failing parts drop out, and its past readings get a trusted
  re-read beside them. Training on its bands stays closed.
- **Kimock and Swatkins rejoin K only with the user's yes** (decision 3). Their bleed lived in live
  backings, which K does not use.
- **V-real is reused.** It picks T2's winner and is read again at T4, so T4 is not an independent
  test. The ROADMAP's fresh-song decision test stays.

## (f) Order, cheapest decisive first

| Stage | What | Reads |
|---|---|---|
| **T0** (about 6 renders) | Code and calibrate the measures; run them on every target and DI in use; re-read (a)'s results; scan and spot-check stems by ear; fix the review label. One listening sitting: the conflicts, the knife-edge passes and the unmeasured parts | the trusted parts, DIs and stems |
| **T1** (no training) | Build K (R_in's 1,407 truth renders reused) and separate it | paired K − V_sep stem SNR on the same examples and draws, 90% interval; V-real's stem SNR beside it, at matched ratio. A gap adds realism levers to T2's SYN arm |
| **T2, the pilot** | 5k trusted-pool examples (seed 20261099, stratified by band), three arms: **SES**, the stored stems; **SYN**, self-built backings of the same examples, labels and draws; **SYN-E**, SYN with a seeded third swapped for Eggy sections (Eggy's DIs pass (a) first). Today's control space; D_stem's recipe; 2 seeds each. All arms early-stop on one new trusted early-stopping set: about 5% of the trusted sections, at least one per band in all 6 bands (seed 20261100), held out of the 5k draw and built in each arm's own mix type. Checkpoints and amendment 5's constant and pull are fitted there | **Primary:** SYN − SES on V-real, paired by direction. **Beside:** SYN-E − SYN (the clean-band payoff; clean parts beside); E on K; stem SNR. *Since 2026-10-25: no E on K (K is empty); the stem SNR is the T2-side stem read, SYN's stems against SES's* |
| **T3** | Every-control stage 2D on self-built mixes. **Pilot:** T2's examples with full-space labels, D_full-5k against D_SYN-5k on K's sound gate (*K is empty since 2026-10-25; open until K comes back*). **Full:** about 20k, with Eggy, Renesans and any approved new DIs; 3 seeds | 2D's rules, read on K and V-real |
| **T4** | V-real (with JHNC), K (*empty since 2026-10-25; open*), then the ear | the route decision |

**How T2 reads** (no pass bar):
- **Power:** on about 10 bands, a paired arm contrast reads about ±0.028 log d, plus 2-seed noise.
  Effects under about 0.03 read as ties.
- **Below 0:** T3 on self-built mixes.
- **Above 0:** the realism levers are tried at 5k before T3: controlled bleed, verified studio amp
  tracks for other guitars, and mix EQ and reverb.
- **A tie:** the rule takes the cheaper option, which is SES, since its stems are stored. But SES
  cannot grow past 8.7k or add a clean band. Whether T3 goes ahead on a tie is decision 5.
- **T2 is mainly a realism check.** Only SYN-E speaks to the clean-band payoff.

## (g) Budget

| | Renders (1.6 s each) | Separations | MPS training |
|---|---|---|---|
| T0–T1 | about 3.5–5.5k (other guitars at 1–4 per example) | 1.7k | 0 |
| T2 | about 12–18k (with the early-stopping set) | about 7.1k | 6 runs, about 2 h |
| T3 | about 50–70k (pilot and full; gates; V-real) | about 20k | about 6–8.5 h |
| **Total** | **about 65–95k, about 11–16 h on 3 processes** | **about 29k: 23–28 h with the worker, 34–40 h alone** | **about 8–10.5 h** |

- **Disk:** about 3 GB of features, against 116 GB free and the 31 GB guard.
- **Downloads:** none through T2.

## (h) What it gives up, and the risks

- **The synthetic-to-real gap.** A model may learn Morgan's character, not a real amp's, and expect
  cleaner stems than songs give. Only T1, V-real and the ear guard against it.
- **Arrangement realism.** Backings keep each song's key, tempo and guitar balance, but lose the
  engineer's balance, EQ, reverb and bus compression, the live bands' drums and vocals, and real
  other amps; mix effects may be read as preset effects.
- **Few bands.** Training draws on about 8 bands (clean DIs from Eggy alone) and V-real has up to 11:
  self-built mixes fix trust, not DI scarcity. The thresholds are proposals; A3 only catches
  linear copies.

## (i) Decisions for the user

1. **The hybrid itself:** self-built for training and development, V-real for the final development
   test, the ear last.
2. **The standard:**
   - measures plus ear, with a measured fail excluded by default (this amends ML plan §5, where
     measures only named candidates);
   - the conflicts: Quicksand ElecGtr2, and Today's The Day ElecGtr07 (half A, −1.08 ms);
   - whether hummy measure DIs stay.
3. **K and stage F:**
   - Kimock and Swatkins rejoin K (it reverses "stay out for now");
   - stage F is shrunk to V-real (recommended), or its bands train once fresh test bands exist.
4. **Other guitars:** DI renders only (recommended), or also verified studio amp tracks. *Amended 2026-10-25 (user):*
   amp tracks stand for active guitars that cannot be rendered, after an automatic bleed check ([the 2026-10-25 note](#notes-after-approval-dated)).
5. **T0–T2:**
   - approve about 16–23k renders, 8.8k separations and about 2 h of training;
   - rule on a tie at T2: SES is cheaper, but only the self-built set can grow under the
     trusted-data rule.
6. **Approved plans this would amend:**
   - the cleaning plan's step 2 (#273) becomes T2's SES arm;
   - the coverage plan's stage 2D, which needed `GATE OK` (step 3 read `GATE STOP`), becomes T3,
     read on K and V-real instead of R_in;
   - the real-mix test (#267) runs on V-real's parts.
7. **Downloads for T3:** Strobe and MekaPhil (2.4 GB). EGDB and GOAT only with a borrowed backing.
8. **Controlled bleed:** an arm in T3, or off.

### Recorded decisions (user, 2026-10-23)

The user approved the plan ("Sounds good") after the ML session's summary, which proposed:
1. **The hybrid: adopted.**
2. **Every measured verification failure is excluded.** The two conflicts (Quicksand ElecGtr2, and
   Today's The Day ElecGtr07) wait for the user's ear on the target-vs-DI page; until then they are
   excluded. Hummy measure DIs are excluded too, under the trusted-data rule.
3. **T0–T2 run:** about 16–23k renders, 8.8k separations and about 2 h of training. The full rebuild
   (T3) is decided after T2.
4. **A tie at T2 picks the self-built set**, because only it can grow under the trusted-data rule.
   This replaces the "cheaper option on a tie" default for this decision only.

Set by the ML session, consistent with the user's rules; the user may overrule any of them:
- **Kimock and Swatkins stay out of K.** The user's 2026-10-23 decision to keep only clean examples
  stands; this plan's item 3 would have reversed it.
- **Stage F is shrunk to V-real** (the recommended option).
- **Other guitars are DI renders only** (the recommended option).
- **Controlled bleed is off**, under the clean-only rule.
- **The amendments in item 6 apply:** the cleaning plan's step 2 becomes T2's SES arm, coverage stage
  2D becomes T3, and the real-mix test runs on V-real's parts.
- **T3's downloads** (Strobe and MekaPhil, 2.4 GB) are asked for at T3. Downloads need the user's yes
  at the time.

### Notes after approval (dated)

Facts that changed after the approval, and what each means for the plan. None is a new user decision.
- **2026-10-23, (b), set by the ML session:** the Blue Manic, EGDB and GOAT lines were added after the approval
  (commits aa3df97 and 34106e5). They reserve a test band and record downloads; no approved step changed.
- **2026-10-23, T0 ran** (ROADMAP, step 0):
  - **Eggy's three DIs were heard processed.** So self-built mixes do not bring a clean-class band back for now, SYN-E
    cannot run, and T3's "with Eggy" no longer applies. Where clean-class DIs come from is an open user decision.
  - **V-real is 11 parts in 7 bands** (3 clean parts in 2 bands), all pending the ear (now 10 parts; see the [T0 outcome](trusted-data-t0-design.md#t0-outcome-2026-10-25)). At 7 bands a paired arm contrast
    reads about ±0.036 log d (90%), not (f)'s ±0.028 on about 10 bands, before seed noise.
  - **The two conflicts** (decision 2) fail measures (Quicksand ElecGtr2 A6; Today's The Day ElecGtr07 A5), and in
    code a measured fail excludes before the ear is read, so they are not on the ear pages and no answer can bring them
    back. Sitting 1, the basis of the conflict, judged their DI clips, not these targets. Whether the measured fails
    stand is an open user decision.
  - **T0's by-ear stem spot-check** is not queued yet; T1 and T2 would use stems that passed the scan alone. Open user
    decision.
- **2026-10-23, the review before the ear** ([record](research/program-review-2026-10-23.md)):
  - **T1 and T2 draw their levels from the stored prior,** so K − V_sep and SYN − SES stay paired on the same draws, as
    (f) requires; the re-derived prior of (c) is for T3's new examples.
  - **T1's row ("a gap adds realism levers")** has no lever coded or approved (controlled bleed and studio amp tracks are
    off; mix EQ and reverb are not built). T1 is read as descriptive.
  - **(d)'s "no other take of the target"** now holds in code: a same-part double confirmed by pitch takes the target's
    settings, as a DT double does.
- **2026-10-24, the user's decisions** (each as the ML session recommended; [design](trusted-data-t0-design.md#the-users-decisions-2026-10-24)):
  - decision 2's two conflicts stay excluded on their measured fails;
  - T0's by-ear stem spot-check joins this sitting, one clip per scanned session, and a session's stems are used once
    its clip is heard clean;
  - every DI is heard before it counts;
  - the song-blind per-class constant is one more V-real arm at T2, read beside the primary (e)/(f).
- **2026-10-25, T1 ran and was audited** ([design](trusted-data-t0-design.md#t1-audited-2026-10-25)): K − V_sep +1.63 dB
  rested on a 1-df band interval (section-clustered [−0.31, +3.56]); 63 examples whose other guitars could not be
  rendered carried about +1.2 dB of it, and near-silent renders were lifted by up to +43 dB. No cleaning gain is
  established, and no realism lever follows; T2's SYN arm is otherwise unchanged. Fixed in code: an example whose
  section has a playing guitar that cannot be rendered is left out of every arm, a near-silent render (below −50 LUFS)
  refuses its example, and with fewer than 3 bands the section-clustered interval is primary. Rule 1 leaves out all
  of T1's examples and cuts T2's candidates to 3,955 in 3 bands (parts with no DI play in most sections): a user
  decision before T1 or T2 runs again. T1 must be re-planned in any case (T0's lists changed, PR #289).
- **2026-10-25, the user's decision on rule 1** ("Sounds good, go ahead" to the ML session's option 1;
  [design](trusted-data-t0-design.md#rule-1-after-the-users-decision-2026-10-25)): in self-built mixes, an active guitar
  that cannot be rendered is the session's own recorded amp track(s), at the session's balance, after an automatic
  leakage check with no listening (other-instrument bleed under −30 dB, A6's line, read once per session by the
  cleaning plan's take estimator from the session's non-guitar tracks only, since doubled guitars read as each other's
  leakage; a source the estimator cannot be trusted on fails the track); a part with no such track, or one that fails,
  leaves the example out of every arm, as do examples with more active guitars than the cap of 4. Only K's and SYN's
  backings change; SES and pairing do not. Dry run after the independent review: every amp track has at least one
  source the estimator cannot resolve at −30 dB (sparse vocals, synths, effects, toms), so none is used; T1 keeps none of
  its 812; T2 keeps 5,154 candidates in 4 bands outside early stopping (Rebuild The Evil and The Long Wait drop out), so
  the 5k pilot is still reachable, narrowly. T1 must be re-planned and re-run before T2, because K's mixes change; as it
  stands the re-plan holds no example, so the user decides whether T1 is waived before T2 or the check changes.
  *Superseded the same day (next note).*
- **2026-10-25, T1 waived and T2 started** ([design](trusted-data-t0-design.md#t1-waived-and-the-realism-check-moved-into-t2-2026-10-25)):
  the user answered "I prefer reliable data and additional/longer runs than data that can't be fully trusted" when
  asked whether T2 should run on 4 bands without amp tracks. T2 started at 17:54 under PR #290's rules: 5,154
  candidates in 4 bands, a pilot of 5,000, no amp tracks (Rebuild The Evil and The Long Wait drop out). T1's re-run is
  waived, not passed, which follows from that answer: K is empty under the reviewed rules, and T1 gates nothing. So T2
  reads no E on K, and K's sound gate for T3 and T4 is open until a better leakage measure, or another route, brings K
  back. The realism question moves into T2 (the ML session's proposal, approved after review, 2026-10-25): the primary
  SYN − SES on V-real is the decisive test, and a zero-render, descriptive T2-side stem read (SYN's stems against
  SES's on T2's examples, T1's measure; at best a ceiling check, since above 0 cannot tell cleaner from unrealistically
  easy) is built and reviewed before T2's results are seen. Known gap: sections with an active guitar that has no
  usable DI or amp track are left out, so dense multi-guitar arrangements are under-represented. SYN short of SES on
  V-real would be a realism signal, not a gap signal (both arms train on the same examples); the gap is read by two
  zero-cost diagnostics declared now (V-real by the number of playing guitars, for SES − S and SYN − S; active-guitar
  counts of kept against left-out examples) and, pending the user's OK, an SES arm trained with the left-out dense
  sections (2 runs, about 1.5 h, no renders). A leakage measure that resolves sparse sources is built after T2 if these
  show the gap matters, or when T3 or T4 needs K.
- **2026-10-25, the SES-ALL arm approved and T2's additions built** ([design](trusted-data-t0-design.md#t2s-additions-as-built-2026-10-25)): the user approved the third
  diagnostic ("Approved if you suggest following this approach", after the ML session suggested it). SES-ALL is SES's
  recipe, seeds and early-stopping set on a 5k draw (seed 20261104, stratified by band) from every T2 candidate, the
  sections rule 1 and the cap left out included, read as SES-ALL − SES on V-real: 2 runs of about 1.5 h, about 60
  V-real renders plus 30 priming, no separations. Built before any T2 result, with the T2-side stem read (a ceiling
  check only), diagnostic (a)'s split (5 or more playing guitars, a median split of V-real's part counts) and the
  `report` fix (T1's 812-example read labelled superseded). It all runs after T2's chain and adds to its records.
  Diagnostic (b), read at zero renders: the left-out candidates are denser (mean 3.82 playing guitars against 2.90
  kept), but 2,308 of the 3,260 are one band (Rebuild The Evil), so SES-ALL − SES also carries two more bands.
- **2026-10-26, scope refined for training (user decision):** high-gain songs can definitely be used for training, as
  long as too-heavy songs don't interfere with the model. The user doesn't play heavy metal, so testing and perfecting
  stay clean/crunch-focused. For this plan:
  - a training source is no longer dropped for being high gain; "scope by ear" screens out only extreme cases;
  - V-real, K and every readout stay clean/crunch-weighted and are also read per class, to catch interference;
  - the 2026-10-25 Cambridge scan's metal sessions outside the held-out sets become possible training candidates: 11
    sessions from 6 bands (Arcadian Alone, Daimon B ×2, Dark Illusion ×2, Inhumanity Vortex, Peppermark ×3, Serapis ×2;
    V.M.GY is set-3 held out), plus DGX ×2 (hard rock/metal). With the user's yes, these 13 were downloaded on
    2026-10-26 and are under intake on branch `ml/metal-intake`: the held-out checks, T0's checks and the ear
    ([ROADMAP](ROADMAP.md#scope-user-decision-2026-10-10)).
- **2026-10-26, parts 5 and 6 heard** ([design](trusted-data-t0-design.md#parts-5-and-6-heard-2026-10-26)): the
  window re-check recovers 2 targets on their re-check windows. Signs ElecGtr6 is pending until its DI is heard as a
  DI (part 8). Targets are 19 verified and 1 pending. None joins V-real or knob ceiling 2. The new bands give **1 new training DI from 5 bands** (Empty Signifier 20_ElecGtr2DI, a high-gain
  part); Mòpia's two DIs and Goran Levi's were heard processed. The clean/crunch shortage is unchanged.
