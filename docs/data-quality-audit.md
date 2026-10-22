# Data-quality audit (2026-10-22)

The user has listened to many of the project's pages and suspects that the datasets are too
dirty and need cleaning. This audit measures how dirty they are, where, and what it costs, and
proposes the cheapest decisive cleaning. It used zero renders, no training and no downloads.
Everything ran on the CPU (nice 10, 2 threads) from stored audio, stored mels and stored results.
Held-out data (sets 4–6, Guitar-TECHS P3, `dev-test-ledger.json`) was not touched.

- **Scripts and compact evidence:**
  [audits/data-quality-2026-10-22/](audits/data-quality-2026-10-22/).
  - `sections.json`: per section, stem contamination, guitar level and backing make-up.
  - `label-table-crop-match.jsonl`: per part and half, the DI-to-target checks.
  - `r-in-gate-vs-contamination.json.gz`: per-example sound-gate rows joined to contamination.
  - `stage-f-impact.json`: stage F per-part D − S against the dirt measures.
- **How to read it:** **Findings** are measured. **Inference** is marked as such. Intervals
  are 90%.

## Headline

1. **The biggest dirt is in the separated stems the direct model trains and is scored on, not
   in the DIs or labels.**
   - **Training pool** (21,304 stored X-LANCE stems): a median of **45%** of a stem's mel power
     is not explained by the rendered guitar it is labelled with. 41% of examples are above
     50%, and 17% are above 70%.
   - **V_sep:** the same, at 45%, with all three separators (X-LANCE, Mega-53, htdemucs).
   - **Floor:** examples where the guitar is at or above the backing level read 22%. That is
     roughly what separator colouring alone produces.
2. **Contamination costs accuracy.**
   - **Within each R_in band,** examples in the most-contaminated third score worse on step 3's
     sound gate than those in the least-contaminated third, by **+0.103 log d [+0.055,
     +0.156]**.
   - **Holding the guitar's level fixed,** each +0.1 of contamination costs **+0.026
     [+0.014, +0.040]**.
   - **The band ranking matches** (finding). Swatkins (median contamination 0.25) and John
     Morgan Kimock (0.39) are the two bands that gained (−0.287, −0.283). Adam Buckley (0.50)
     and Dark Ride (0.64) are the two that stayed flat (−0.061, +0.016).
3. **What contaminates the stems:**
   - **The guitar's level in the mix.** 16% of training examples put the guitar more than
     15 dB under the backing. Their contamination is 0.70.
   - **Other guitars in the backing.** Other electric guitars are 71% of Dark Ride's backing
     power, 30% of Adam Buckley's, and 0% of John Morgan Kimock's and Swatkins'.
   - **Doubles of the same riff.** Part C's coherence leak check cannot see them (it reads
     0.001–0.008 for a double, against a 0.05 threshold).
4. **The real amp-track targets (stage F, knob ceiling 2) carry live-room bleed.**
   - **Where:** 6 of stage F's 42 halves and 8 of knob ceiling 2's 48 halves read high bleed.
     They are all Telefunken live sessions. They are exactly the parts the user complained
     about.
   - **No DI is paired with the wrong amp track.** Wherever the DI plays, it plays the same
     notes as its target (chroma similarity ≥ 0.70 in every played half of all 59
     label-table parts).
5. **Trial 47 (Sculptor's Request GTR 1).** The render and the reference play the same notes
   at the same place (chroma 0.94), and the DI follows its amp track across the song. The
   files are not swapped. What the user heard is not explained by a wrong DI. See below.
6. **The DIs themselves are clean.** Part A's screen already removed hum, clipping and
   drop-outs. The pool's 332 sections have 0 clip runs, 0 drop-outs and hum below −56 dB.
7. **First step:** a clean-versus-random retrain at pilot scale, with E on V_dev read first
   (zero renders). It is the cheapest test that decides whether cleaning the *training* stems
   helps, as opposed to cleaning the test stems. See [the plan](#the-cleaning-plan-cheapest-decisive-first).

## 1. What the user reported

The user's own complaints about data quality, as recorded. Quotes are verbatim where the docs
keep them.

| # | When, where | What he heard | Part(s) | Kind |
|---|---|---|---|---|
| U0 | Clean-start volume page, 2026-10-22, trial 47 | "Leaking of other instruments, i.e. trial 47, and also its B follows the wrong guitar (A is clearly the original R track since I could hear the leaking there as well)" | Sculptor's Request GTR 1 (AC20) | bleed; render ≠ reference |
| U1 | Listening validation, 2026-10-04, trial 29 | "I could hear the backing from the guitar mic.." | Blind Spots | bleed in target |
| U4 | Audition-page check, 2026-10-06 | "Some songs didn't include a guitar or the song and the A-D had different notes/chords" | First Offering GTR 1, Gym Hours GTR 2 (quiet second guitars), Signs ElecGtr2 | guitar inaudible; notes differ |
| U6 | Same check | Loud vocals made it hard | several | masking |
| U7 | Heavy check H, 2026-10-10 | "sounded bad in both A and B (clipping?)", "almost only lower notes" | Burial Of Silence 3–4, Less Than Nothing, Split Brow, The Well 01, Magilla ElecGtr2 | low-tuned DIs (measured as not clipping) |
| U8 | Arm A check, 2026-10-16, trial 1 | "same; the record leaks" | First Offering GTR 1 | bleed in target (about −14 dB) |
| U9 | Arm A check, trial 8 | "A and B sound distorted with noise" | Prodigal ElecGtr5 | 60 Hz hum in the DI |
| U10 | Bleed check 1, 2026-10-16 | Leakage heard in the original and the cleaned track on all 3 high-bleed parts | Sculptor's Request GTR 1, Gym Hours GTR 1, First Offering GTR 1 | bleed in target |
| U11 | Bleed check 2, 2026-10-17 | The cleaning changed the tone a little | the same 3 parts | repair artefact |
| U13 | Knob ceiling 2, trial 6 | Another guitar in the record; the lead seemed missing | Gym Hours GTR 1 | other guitar in target (GTR 2 at −3 to −17 dB) |
| U14 | Separation samples, 2026-10-19 | htdemucs drum leakage, drop-outs, "many leaks"; another guitar in both separators' stems | Today's The Day, Magilla, She's Gone, Gym Hours; Signs ElecGtr3, get-out-of-bed elecgtr2 | stem contamination; other guitars |
| U15 | Part locator | A "clean electric" window was an acoustic guitar | Eden 8:10–8:30 | wrong instrument |
| U16 | Held-out SW50R page | Details hard to hear "because of the band, especially the vocals" | 57 Chevy | masking |

U2, U3 and U12 were about the options or the test design, not the data. U17 was a render
failure. No comments are recorded for the clean DI library's two pages, record-match,
starting-preset or separator screen.

**Pattern (finding):** the complaints fall into two groups.
- **Bleed or other guitars in the amp-track target,** on the Telefunken live sessions: U0, U1,
  U8, U10, U13.
- **Other instruments in the separated stem:** U14, and U4/U6/U16 by masking.

Only U9 is about a DI, and it was hum the screen already flags.

## 2. The datasets and what each one's "target", "DI" and "backing" are

| Dataset | Size | Sources | Target | DI | Backing |
|---|---|---|---|---|---|
| **Part C's pool** (direct model's training, `pretrain_set` → `direct_stems` build) | 21,311 examples (20,311 train, 1,000 early stop), 277 sections, 9 bands | Cambridge-MT (Ale Lak, Death Of A Romantic, Hollow Ground, Rebuild The Evil, Storm Of Particles, Starnes And Shah, The Long Wait) and Telefunken (Eggy, Renesans) | **A render:** the DI section through drawn Morgan settings. The label is the settings, so it is exact. The model's *input* is the X-LANCE stem of the true mix. | The original DI track, screened by part A | The session's other tracks: the mix list less the part's own amp tracks, every DI and any track whose coherence with the part's own amp track exceeds 0.05. Placed at a guitar-to-backing ratio drawn from real sections. |
| **V_dev / V_sep** | 1,720 examples, 55 sections, 5 bands (R_in: 1,407, 4 bands, without Bannockburn) | Cambridge-MT (Adam Buckley, Cnoc An Tursa, Dark Ride), Telefunken (John Morgan Kimock, Swatkins) | As above (part C's val renders) | As above | As above |
| **Stage F** | 21 parts, 12 bands, 126 directions | 17 Cambridge-MT, 4 Telefunken | **The real amp track** (`reference.wav`) | The original DI, measure-DI treated | A 30-s full-mix context with vocals, separated |
| **Knob ceiling 2** | 24 parts, 14 bands | Sets 1–3, Cambridge-MT and Telefunken | The real amp track | The true DI | None |
| **Known answer B1** | 3 bands, 12 DIs, 16 crops | Chris Coltraine, Rebecca Haviland, The Apprehended | A truth render, so exact | The original DI | Part C's rule; items vary vocals and other guitars |
| **DI library (part A)** | 237 DIs, 5,571 sections, 808 clean and disjoint | Cambridge-MT, Telefunken, Guitar-TECHS (Guitar-TECHS left out of part C) | n/a | Screened for hum, hiss, clipping, drop-outs, bleed and activity | n/a |

**Where dirt can enter:**
- **Part C, V_sep and B1:** the DI, and the backing. The backing reaches the model through the
  separator.
- **Stage F and knob ceiling 2:** the amp-track target itself (bleed, other guitars, a DI that
  does not match), plus the separated stem.

## 3. Findings: how dirty, and where

### 3a. Stem contamination: the part C pool and V_sep (zero renders)

**Measure.** For each example, take the stored true-render mel (part C, `gA`/`gB`) and the
stored separator stem mel (`direct-stems/build/ex`). Both are on part C's 0.5-dB grid.
- Use half A from 1 s on, and half B.
- Find the level offset as the median of (stem − render) on the render's active cells (those
  within 50 dB of its maximum).
- **Contamination** is the share of stem power that lies above the level-shifted render. In
  other words, how much of the stem is not the labelled guitar.
- **Reliability:** halves A and B agree, r = 0.87.
- **Floor:** examples whose guitar is at or above the backing (ratio ≥ −2 dB, n = 787) read
  0.22. That is about what the separator's colouring and mastering add with no backing in the
  stem.

**Training pool** (21,304 X-LANCE stems; 7 of the 21,311 were refused at build):

| | Value |
|---|---|
| Median contamination | 0.446 (10th–90th percentile 0.21–0.81) |
| Share above 0.5 / 0.6 / 0.7 | 41.1% / 27.4% / 17.3% |

| Band | Examples | Median | Share > 0.5 |
|---|---|---|---|
| The Long Wait | 77 | 0.78 | 0.97 |
| Renesans | 2,847 | 0.62 | 0.69 |
| Storm Of Particles | 1,845 | 0.48 | 0.46 |
| Eggy | 7,387 | 0.45 | 0.42 |
| Death Of A Romantic | 2,460 | 0.44 | 0.38 |
| Hollow Ground | 1,923 | 0.41 | 0.33 |
| Ale Lak | 2,380 | 0.39 | 0.31 |
| Rebuild The Evil | 2,308 | 0.36 | 0.17 |
| Starnes And Shah | 77 | 0.36 | 0.32 |

**By the guitar-to-backing ratio** (the `mix_params` draw):

| Ratio (dB) | Share of examples | Median contamination |
|---|---|---|
| < −15 | 16.1% | 0.70 |
| −15 to −10 | 29.2% | 0.53 |
| −10 to −5 | 36.2% | 0.40 |
| −5 to 0 | 18.0% | 0.29 |

A linear fit over the pool gives contamination = 0.30 − 0.019 × ratio dB − 0.14 × the backing's
guitar share. Within the training pool the ratio dominates.

**V_sep** (1,720 examples, by separator; median contamination):

| Band | X-LANCE | Mega-53 | htdemucs | Other electric guitars in the backing (median power share) |
|---|---|---|---|---|
| Swatkins | 0.25 | 0.30 | 0.42 | 0.00 |
| John Morgan Kimock | 0.39 | 0.40 | 0.42 | 0.00 |
| Cnoc An Tursa | 0.36 | 0.37 | 0.36 | 0.49 |
| Adam Buckley | 0.50 | 0.53 | 0.52 | 0.30 |
| Dark Ride | 0.64 | 0.67 | 0.65 | 0.71 |

- **Vocals and mastering barely matter:** with vocals 0.46, without 0.44; mastered 0.47,
  unmastered 0.43.
- **The ratios are similar across bands** (median −9 to −10 dB).
- **Section level:** contamination rises with the backing's guitar share, Spearman ρ = 0.54
  (p 2e-5).

**What is in the backing** (`backing_comp.py`). Median power share in the section window:

| Band | Electric guitars | Keys/synth | Drums | Bass |
|---|---|---|---|---|
| Ale Lak (train) | 0.55 | 0 | 0.10 | 0.35 |
| Rebuild The Evil (train) | 0.35 | 0 | 0.59 | 0.03 |
| Hollow Ground (train) | 0.34 | 0 | 0.20 | 0.46 |
| Death Of A Romantic (train) | 0.13 | 0 | 0.76 | 0.10 |
| Storm Of Particles (train) | 0.11 | 0.06 | 0.65 | 0.18 |
| Eggy (train) | 0 | 0.59 | 0.24 | 0.17 |
| Renesans (train) | 0 (pre-recorded tracks 0.08) | 0 | 0.67 | 0.19 |
| Dark Ride (V_sep) | 0.71 | 0 | 0.14 | 0.15 |
| Adam Buckley (V_sep) | 0.30 | 0.01 | 0.40 | 0.26 |

- **In the training pool,** guitar share does not predict contamination (ρ = −0.17). Renesans
  and Eggy read high from drums and keys at low ratios.

**Same-riff doubles in the backing.**
- **Why the leak check misses them:** part C's check is coherence with the part's *own* amp
  track. It reads a double-tracked part (another take of the same riff) at 0.001–0.008:
  Adam Buckley ElecGtr2DT 0.0022, Ale Lak ElecGtr02DT 0.0081. Every double therefore stays in
  the backing.
- **What the onset check finds** (§3c): the DI's onsets follow a non-own amp track at r > 0.6
  in at least a quarter of its windows for:
  - Adam Buckley ElecGtr2 ↔ ElecGtr2DT, and ElecGtr4;
  - Ale Lak ElecGtr02 ↔ 02DT;
  - Renesans "Labor Of Hate" ↔ its `GTR Pre Rec` tracks;
  - the full list is in §3c.
- **Result:** the stem then holds the original recording of the same riff, with its real tone,
  beside the render the label describes.

**Telefunken live sessions.** The leak check keeps room and drum mics just under its threshold:
- John Morgan Kimock's Mono OH at 0.026 (the same mic is dropped in his other song);
- Renesans' Bass Amp at 0.039 and 0.042;
- Swatkins' Leslie and room mics at 0.020–0.037.

These carry the original guitar's room sound into the backing. Not measured further.

### 3b. Amp-track targets: stage F and knob ceiling 2 (zero renders)

**Measures.** `crop_match2.py` runs on each label-table part's 10-s crop. Per judge half:
- onset correlation of DI and reference (best lag within ±100 ms);
- chroma similarity (are the same notes playing?);
- an NNLS power split of the reference into DI and backing;
- DI and reference activity against the crop's own level.

These were joined to the bleed audit
([audits/bleed-2026-10-16](audits/bleed-2026-10-16/README.md)).

**Stage F (21 parts, 42 halves):** 9 halves in 5 parts are flagged.

| Part | Half | Flag |
|---|---|---|
| Russian Cream GTR 1 | A, B | high bleed (−8.9, −8.3 dB); onsets differ (0.29, 0.32) though the notes agree (chroma 0.90, 0.94) |
| Strangest Places | A, B | high bleed (−12.8, −18.4 dB) |
| She's Gone | A, B | high bleed (−17.4, −19.3 dB); in half A the reference plays where the DI is silent (48% of frames) |
| Today's The Day ElecGtr07 | A | onsets differ (0.29; chroma 0.70) |
| wickerman elecgtr3 | A, B | onsets differ (0.33, 0.34; chroma 0.81) |

- **Unexplained share.** The bleed audit's guitar share (how much of the amp track its DI
  explains) is 0.41–0.59 on femme elecgtr5, Today's The Day 07, wickerman 1–3 and let's dance
  3–4.
  - None of these parts has a named bleed source.
  - Those parts are distorted, so the shortfall may be the audit's model, not dirt. Not
    resolved here.

**Knob ceiling 2 (24 parts, 48 halves):** 9 halves in 5 parts are flagged.
- **High bleed, both halves:** First Offering GTR 1 (−13.8, −14.7 dB), Gym Hours GTR 1 (−13.8,
  −8.4), Long Way Home (−19.9, −16.9), Sculptor's Request GTR 1 (−10.9, −12.6).
- **Silent DI:** It Was My Fault For Waiting ElecGtr1, half A; the DI plays 26% of it.

**All 59 label-table parts:**
- **Silent DIs:** 25 of 118 halves have a silent or mostly silent DI. Some are digital silence
  in both tracks. Others leave the reference holding only bleed at about −40 dB: Until I Get
  Back B, Lost & Alive B, Measurements B.
- **Stage F's rule** (a finite S on both halves) already removed all of these but She's Gone A.
- **No swapped pairs:** in every half where the DI plays, chroma similarity with the reference
  is ≥ 0.70.

### 3c. DI-to-amp-track correspondence across the DI library (session level)

`di_match.py` covers the 131 library DIs that have their own amp track, over the whole session
in 10-s windows. It compares the DI's onset correlation with its own amp track against every
other non-drum, non-vocal, non-bass track. A further 19 DIs have no amp track: Dark Ride's 8,
Storm Of Particles' 3, Eat The Feeder's 3, Szymon Skiba's 2 and The Apprehended's 3. Those were
checked against every track instead.

**Own amp track** (130 DIs scored):
- **Onset correlation with the own amp track:** median 0.55 (interquartile 0.40–0.80).
- **Low readings are mostly playing style:** 32 DIs read below 0.4, mostly high-gain or
  low-tuned parts (Cnoc An Tursa, Rebuild The Evil, Renesans, Storm Of Particles, Death Of A
  Romantic, Eat The Feeder), where onset correlation through heavy distortion is weak.
- **The suspicious ones were checked with whole-session chroma** (`chroma_check.py`): Cnoc An
  Tursa ElecGtr1 and ElecGtr2, Zeno ElecGtr1, 4 and 5, Gym Hours GTR 1, Russian Cream GTR 1,
  Today's The Day ElecGtr04 and The Long Wait ElecGtr1. Each plays the same notes as its own
  amp track (0.43–0.95). Where ensemble guitars play the same chords, others score about as
  high, but none is clearly higher.
- **No DI was found paired with the wrong amp track.**

**Same-riff tracks left in the backing.** These are non-own amp tracks whose onsets follow the
DI at r > 0.6 in at least 25% of its windows. 9 DIs have one, 7 of them in the direct pool or
V_sep:

| Band, DI | Track that follows it | Dataset |
|---|---|---|
| Adam Buckley ElecGtr2 | ElecGtr2DT (17 windows), ElecGtr4, AcousticGtr1 | V_sep |
| Adam Buckley ElecGtr2DT | ElecGtr2 (18), ElecGtr4, ElecGtr3 | V_sep |
| Adam Buckley ElecGtr3 | ElecGtr2, ElecGtr2DT | V_sep |
| Adam Buckley ElecGtr4 | ElecGtr2, ElecGtr2DT | V_sep |
| Ale Lak ElecGtr02 | ElecGtr02DT | train |
| Ale Lak ElecGtr02DT | ElecGtr02 | train |
| Swatkins "Lost & Alive" | Leslie Top (the keys track the guitar's rhythm) | V_sep |

**Renesans "Labor Of Hate" (train).** The `GTR Pre Rec` tracks follow the DI better than its
own amp tracks in 47% of windows (0.32 against 0.27, at 0 ms lag). They look like a
pre-recorded double of the riff, and they stay in the backing. Renesans is the most
contaminated training band (0.62).

**DI-only parts** (19 DIs with no amp track): no session track follows them. The best is 0.39
(Wickerman ElecGtr8 against ElecGtr7Amp); Dark Ride's DIs are 0.34 or below. So no unlabelled
original amp of the same performance sits in their backing. Dark Ride's DIs play sparsely
(3–11 scorable windows each) under loud *different* guitar parts.

### 3d. Trial 47: Sculptor's Request GTR 1 (the user's report today)

**The user's words:** "Leaking of other instruments, i.e. trial 47, and also its B follows the
wrong guitar (A is clearly the original R track since I could hear the leaking there as well)".

**What the clips are.** Trial 47 is half B of the crop, 124.0–128.5 s of the session.
- **R and A** are `GTR 1 Amp M80`. Their onset envelope matches the session file at
  r = 0.99, at 124.0 s.
- **B** (the render) follows `GTR 1 DI` at the same position (r = 0.78). It does not follow
  GTR 2's DI anywhere (best 0.45, at another time).

**Same notes.** The render plays the same notes as the reference.

| Chroma similarity | Value |
|---|---|
| R ↔ B | 0.94 |
| R ↔ GTR 1 DI | 0.97 |
| B ↔ GTR 1 DI | 0.98 |
| R ↔ GTR 2 DI | 0.19 |
| R ↔ keys | 0.29 |

**Across the song,** GTR 1's amp follows GTR 1's DI:
- log-envelope correlation 0.93–0.96 at 60, 118.5, 123.5 and 180 s;
- an NNLS power share of 0.90–1.00 from GTR 1's DI and 0.00–0.07 from GTR 2's.

GTR 2's DI follows GTR 2's amp at r ≈ 0.95 throughout. **The DIs are not swapped** (finding).

**What is in R:**
- the drum room mic at −10.9 dB (half A) and −12.6 dB (half B), per the bleed audit; flagged
  high on both halves;
- GTR 2 at about −11 dB in half A (NNLS share 0.07), and about 0 in half B.

B's onsets match R's less well (0.69) than R's match the DI (0.82).

**Inference:**
- **The leakage he heard is real and measured:** drum room, plus GTR 2 in half A.
- **"Follows the wrong guitar" is not a wrong DI or a misplaced crop.** The likeliest
  explanation is that the bleed in R (drums plus a second guitar) makes R sound like a
  different performance from the dry, isolated render. The render's attack and envelope
  differ from R's, while the notes are the same.
- **A listening recheck would settle it:** R against the GTR 1 DI soloed at the same 4.5 s.

### 3e. The DIs and the pool's make-up

**DI quality** (part A's manifest, over the 277 pool and 55 V_sep sections):

| Measure | Pool | V_sep |
|---|---|---|
| Clip runs | 0 | 0 |
| Drop-outs | 0 | 0 |
| Hard cuts | 15 sections (max 6) | 14 sections (max 12) |
| Hum measured | 10 sections, median −79 dB, max −56 dB | 16 sections, max −55 dB |
| Hiss | median −72 dB | median −80 dB |
| Bleed into the DI | measured on 25 sections, median −47 dB | — |

- 82 pool sections have bleed unreadable.
- The hum-suspect superset (11 DIs) and Guitar-TECHS are already out.

**Pool balance:**
- **One band dominates:** Eggy is 96 of 277 sections and 35% of examples, from 3 songs.
- **Playing style:** 111 of 277 sections come from DIs whose part is high-gain (68 unknown).
  The renders are clean and crunch settings, but the playing style is the metal part's.
- **Possible separator-training overlap:** Hollow Ground "Ill Fate" (MUSDB18 test, 25
  sections) and The Long Wait (1). Already tagged.

**Duplicates:**
- Sections are disjoint within a DI.
- Train and val are split by whole band, so no section crosses the split.
- **Near-duplicates:** double-tracked DIs of the same riff are both in the pool. Ale Lak has
  3 such pairs and Adam Buckley 1 (val).

## 4. Impact: do dirty examples or parts score worse? (existing results only)

**Step 3's sound gate, per example** (R_in, 1,398 scored examples, log(d_D / d_constant)
averaged over halves). Joined to each example's X-LANCE contamination:

| Band | Mean | Low-contamination third | High-contamination third | Spearman ρ (gate, contamination) |
|---|---|---|---|---|
| Adam Buckley | −0.061 | −0.121 | −0.035 | 0.12 |
| Dark Ride | +0.016 | −0.008 | +0.060 | 0.11 |
| John Morgan Kimock | −0.283 | −0.341 | −0.183 | 0.19 |
| Swatkins | −0.287 | −0.323 | −0.225 | 0.06 |

- **High third minus low third, within band and band-averaged:** **+0.103 [+0.055, +0.156]**.
  The interval is a 90% bootstrap over sections within band.
- **Regression with band fixed effects, controlling for level:**

  | Term | Effect on log d | 90% interval |
  |---|---|---|
  | +0.1 contamination | +0.026 | [+0.014, +0.040] |
  | +10 dB guitar ratio | −0.035 | [−0.072, +0.001] |

- **Contamination below 0.3 versus 0.5 and above:**

  | Band | Below 0.3 | 0.5 and above |
  |---|---|---|
  | Adam Buckley | −0.146 (n 60) | −0.025 (n 199) |
  | Dark Ride | −0.039 (n 8) | +0.025 (n 328) |
  | John Morgan Kimock | −0.354 | −0.187 |
  | Swatkins | −0.330 | −0.112 |

- **Inference:**
  - Most of the gap between the "strong" and "flat" bands is how much of each band's stem is
    other music.
  - Dark Ride has almost no clean examples (8 of 403 below 0.3).
  - This is contamination of the **test** stem, and realistic songs have it too. So it says
    contamination costs, not yet that the *training* labels are dirty enough to matter. §5
    step 1 separates the two.

**Stage F, per part** (21 parts; D − S per part from `step4/groups` and the stored S;
`stage-f-impact.json`). Spearman correlations of D − S with:

| Measure | ρ | p |
|---|---|---|
| Bleed level | +0.24 | 0.29 |
| Guitar share (from the bleed audit) | −0.31 | 0.17 |
| DI-to-reference onset correlation | −0.16 | 0.49 |

- **Undecided at n = 21** (directions consistent with "dirtier targets, worse", nothing
  shown).
- **The existing "no high bleed" row** reads −0.023 (all parts: −0.034). Both intervals
  contain 0.
- **Russian Cream GTR 1,** the dirtiest target (bleed −8.6 dB, onsets 0.31), has D − S
  +0.130. **Strangest Places,** also high bleed, has −0.195. No pattern at this size.

**Knob ceiling 2 and part C's E per band:** not re-analysed. Knob ceiling 2's flagged parts are
the ones the user already marked by ear (U10, U13).

## 5. The cleaning plan, cheapest decisive first

Each step lists what it filters, what it costs and how to tell whether it helped. Effects are to
be reported with intervals and no pass bar ([learn from improvements](ROADMAP.md)).

### Step 0 (done here, zero cost): readouts stratified by contamination

- **Add contamination to every V_sep and R_in readout,** as a covariate and as a tercile split.
  Report Dark Ride separately: only 2% of its examples are below 0.3.
- **Report stage F with and without the 9 flagged halves.**
- **Cost:** 1 minute of CPU from stored mels.

### Step 1 (cheapest decisive test): does cleaning the *training* stems help?

**Arms.** Train D_stem on the pool:
- **(a) clean:** minus examples with contamination > 0.6. That drops 5,845 (27%): Renesans
  53%, Eggy 30%, Storm 29%, Death Of A Romantic 24%, Hollow Ground 17%, Ale Lak 16%, Rebuild
  The Evil 7%.
- **(b) control:** minus the same number per band, chosen at random. This keeps quantity equal,
  so the contrast reads quality alone.

**Recipe:** the step 3 recipe, 2 seeds per arm. About 4 × 1 h of MPS on 15.5k examples. A
5k-example pilot version would take about 4 × 20 min.

**Readout first, zero renders:**
- masked E on V_dev, (a) − (b), paired per example, band-clustered t over 5 bands;
- plus the same split by test contamination tercile.

**Then, only if E moves:** step 3's sound gate on R_in for the two arms' D. It reuses the stored
truth and constant renders, so it needs about 2 × 1,407 renders.

**What it decides:** whether training-label contamination costs anything beyond what the test
stems already cost. If (a) ≈ (b), training contamination is not the lever: put the effort into
test-time separation and level (step 3). If (a) is better, adopt the filter and test a stricter
threshold (0.5, 41% dropped).

### Step 2 (zero renders): stop the level draw from burying the guitar

**Change:** the 16% of draws with the guitar more than 15 dB under the backing produce stems
that are 70% other music.

**Test:** this can ride on step 1 as a third arm. Cap the ratio at −15 dB by redrawing, which
needs a rebuild of those examples' mixes and stems: about 3.4k X-LANCE runs, roughly 4 h.
Alternatively, drop them (no rebuild) and compare with the random control.

**Inference:** the songs users bring have an audible target guitar (U4, U16). A floor matches
the product.

### Step 3 (code change, zero renders): catch doubles and live-room leaks in the backing

**Add** an onset- or chroma-based **same-riff** check to `pretrain_set.backing_tracks`, beside
the coherence check (`di_match.py` is the prototype). It **tags** a backing track whose onsets
follow the part's DI (r > 0.6 in ≥ 25% of windows); it does not drop it. Real songs have
doubles, so tag and weight rather than delete.

**For Telefunken live sessions,** also tag room and overhead mics with coherence excess
0.02–0.05.

**Test:** re-score step 1's models on V_dev with and without tagged sections (zero renders).
Rebuilding stems without the tagged tracks is a repair. It needs re-separation (about 4.5 s per
clip) and is worth it only if the tagged sections score clearly worse.

### Step 4 (zero renders): label the amp-track targets; do not repair them

**Change:**
- Flag the 14 high-bleed Telefunken halves: stage F's Russian Cream GTR 1, Strangest Places and
  She's Gone; knob ceiling 2's First Offering GTR 1, Gym Hours GTR 1, Long Way Home and
  Sculptor's Request GTR 1.
- Flag stage F's 5 onset-mismatch halves.
- **Keep them out of listening pages,** where bleed gives the reference away (U0, U1, U8, U10).
- **Keep them in judge readouts as a declared stratum,** with the "no high bleed" row reported
  beside every headline.

**Do not repair by subtraction:** the user heard the cleaning change the tone (U11).

**Test:** with the next listening page, compare answer agreement on flagged and unflagged
trials.

### Step 5 (only if step 1 shows composition matters): rebalance

Cap Eggy (35% of examples) and the high-gain-style DIs per band. Same paired design as step 1.

### Not proposed

- **More DI screening:** the DI dirt measured here is small, and part A already screens it.
- **A new separator:** see the [no new separator](ROADMAP.md) policy.

## Limits

- **The contamination measure is mel-domain and approximate.** Colouring by the separator, and
  mastering, count as "excess". Hence the 0.22 floor. Its ranking is stable across separators
  and halves (r = 0.87).
- **The onset measures are weak on heavily distorted parts.** Cnoc An Tursa ElecGtr1 reads
  0.08 against its own amp across ±3 s of lag. Chroma is the more robust check of "same notes",
  and it agrees with its own amp (0.66–0.68).
- **The stage F impact rests on 21 parts,** so it is undecided, not negative.
- **Known answer B1 was not measured.** Its targets are exact truth renders. Its backing
  follows part C's rule, so §3a's backing findings apply to it in kind.
