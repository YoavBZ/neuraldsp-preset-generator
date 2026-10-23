# Trusted data: a self-built training set and a verified real test: plan

**Draft, for the user's decision (2026-10-23).** It was drafted with zero compute: only stored files
were read.

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
  - **Parts with no DI** are left out (decision 4).
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
| **K** | V_dev's DIs in mixes built from their own sessions' clean stems; the truth rendered through the example's DI, as step 3's gate did | E (zero renders); the sound gate, log d of D against the constant |
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
| **T2, the pilot** | 5k trusted-pool examples (seed 20261099, stratified by band), three arms: **SES**, the stored stems; **SYN**, self-built backings of the same examples, labels and draws; **SYN-E**, SYN with a seeded third swapped for Eggy sections (Eggy's DIs pass (a) first). Today's control space; D_stem's recipe; 2 seeds each. All arms early-stop on one new trusted early-stopping set: about 5% of the trusted sections, at least one per band in all 6 bands (seed 20261100), held out of the 5k draw and built in each arm's own mix type. Checkpoints and amendment 5's constant and pull are fitted there | **Primary:** SYN − SES on V-real, paired by direction. **Beside:** SYN-E − SYN (the clean-band payoff; clean parts beside); E on K; stem SNR |
| **T3** | Every-control stage 2D on self-built mixes. **Pilot:** T2's examples with full-space labels, D_full-5k against D_SYN-5k on K's sound gate. **Full:** about 20k, with Eggy, Renesans and any approved new DIs; 3 seeds | 2D's rules, read on K and V-real |
| **T4** | V-real (with JHNC), K, then the ear | the route decision |

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
4. **Other guitars:** DI renders only (recommended), or also verified studio amp tracks.
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
