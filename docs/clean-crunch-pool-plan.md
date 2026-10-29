# Clean/crunch-led training pool (plan, 2026-10-28)

**Status: approved by the user on 2026-10-28 ("Yes for all": decisions A–F below). D_F5bk read 2026-10-29 (165 renders); the pool waits for ear page part 12.**

**Progress (2026-10-28 and 29):**
- **Step 0 (intake checks, `~/ndsp-presets/learn/trusted-data/intake-2026-10-28/`):** 80 DI rows in 21 sessions (the
  released sessions and tier 1's additions). Most fail D2 (46 of 79 summarized; 12 of them on a single failing
  window, since one bad window fails the DI, and one with no window to check). Set 5's backings were re-downloaded (6 sessions, all checksums match).
- **Step 1 (the leak rule, PR #323):** merged. Not adopted: the −10 dB reverse-bleed reading (the line-level
  exemption by name stands in for it); the stand-ins' bleed from replaced guitars is unmeasurable with this meter and
  is left to the ear. Its 5 backing clips (Death Of A Romantic ×2, Storm Of Particles ×3,
  no vocals) are on the ear page. T2 holds no rule-1 stand-in example, so the stand-in clip waits for step 2's pool.
- **Ear sitting E (one page, `listening/trusted-data-ear/part11-clean-crunch`, 120 cards):** the DIs that pass the
  measured checks, their amp tones' class (clean, crunch, high gain), and the 5 backing clips. Sent 2026-10-28; the
  answers decide the DIs, the classes and the leak rule.
- **Step 2 groundwork (PR #324, below):** merged. 74 DI rows in 19 released sessions (all pending the ear), 1,297
  sections (381 clean by part A's screen), backing metadata, and T0's stem scan on the new sessions. Under the old
  session-wide rule many lose most drums and bass (North To Alaska keeps 0 of 12 stems); the per-example rule keeps
  most.
- **Step 3's D_F5bk inputs (PR #325):** F5/FS5 remixed under the per-example backings and separated, done
  2026-10-29 01:09: 2,479 examples built, none refused, pipeline control 42 of 42. On the full builds the backing gain
  moved a median −6.7 dB (Death Of A Romantic) and −2.3 dB (Storm Of Particles), and the stem's SNR rose +6.5 / +1.6 dB.
  The readout commands are in PR #327.
- **Ear sitting E answered (2026-10-29):** all 5 backings "No guitar in it", so the leak rule stands. DIs: 16 clean, 7
  processed (Peter White ×2, Silona ×3, Ronnie Jones ElecGtr04, Doom Flamingo), 9 unsure. Amp tones mostly crunch;
  high gain heard on The Maybe Next Years ElecGtr1 and Turbosauro ElecGtr2DT (both windows) and ElecGtr2 (one). The
  user asked to judge the unsure DIs beside their amp track: part 12 (12 cards, DI then amp track) is sent. Starnes And
  Shah ElecGtr4 is out (its DI plays only its last 5 s).
- **D_F5bk read (2026-10-29, audited; ledger `trusted-data-t3` `amendment_6_outcome`):** D_F5bk − D_F5 −0.008
  [−0.076, +0.061], 4 of 7 bands better: undecided. Two large band swings cancel (femme +0.157, let-s-dance −0.162;
  the other 5 within ±0.03). Co-primary −0.018 [−0.088, +0.051]. Still behind S (+0.080) and D_core5 (+0.072). The
  backing fix alone is undecided on V-real; D_CC (the new songs) is the arm left.

Draft 1 was reviewed independently on 2026-10-28, and the same reviewer re-checked draft 2 (no blockers left). This
draft takes in the findings: tiers by release status, set 5's
missing backings, a leak rule kept session-level, a backing-only control arm, a declared readout, and engineering.

## Why

The user, after the audibility listening page (2026-10-28), said every pair was "too heavy and not clear" and
that metal "might confuse the model". They then ruled that heavy songs stay "as a small minority if they are not
too heavy".

Measured, read-only, with the review's corrections:
- **The trusted pool is 4 heavy bands.** T2's 5,308 examples are Death Of A Romantic 1,644, Hollow Ground 1,570,
  Storm Of Particles 1,494 and Ale Lak 600. F5 (4,129) and FS5 (845) come from the same bands. The pool has no
  clean or crunch song.
  - T2's target settings are mixed: base clean 2,616 and crunch 2,692 (`t2/plan.json`).
  - Backings hold no guitars. The other guitars are DI renders with drawn settings.
  - So the heaviness lies in the playing, the drums and the vocals, not in the target tone.
- **Why the clean and crunch songs are missing.**
  - Stage F's 12 bands are kept out of part C's pool (`direct_stems.pool_examples`, `arm_a_mega53.F_POOL`).
    V-real uses 7 of them.
  - Of the other 5, Dom McLennon and Bernard Purdie have no usable DI: every one was heard processed or fails
    D2 (`t0/verified.json` measure_dis). Turbosauro (progressive metal): 2 DIs checked, both fail D2; 3 unchecked. Doom Flamingo "Measurements" and Quicksand
    ElecGtr2 wait for the ear. Quicksand ElecGtr1 is verified.
  - Eggy, Kimock and Swatkins DIs were heard processed.
  - The cleaning manifest, rule 1 and the cap removed the rest:
    - all of Renesans, Starnes And Shah, Rebuild The Evil and The Long Wait;
    - 1,764 Ale Lak examples (cleaning 1,503, rule 1 152, cap 109, refused 4).
  - The intake added no clean/crunch material with a backing. MekaPhil and Strobe are DI-only sessions.
- **The stem leak check strips backings, though less than first stated.**
  - The check is session-wide: any guitar at or above −35 dB in a stem drops that stem. That includes guitars
    silent in the example's section, and acoustic guitars.
  - Death Of A Romantic lost kick, snare, overheads and bass. Storm Of Particles lost snare, ride, overheads and
    room. Ale Lak lost bass and vocals. Hollow Ground lost nothing.
  - Line-level tracks read high too (Death Of A Romantic BassDI −18.8 dB, Adam Buckley BassDI +1.4 dB). The
    meter reads shared content in both directions, not only acoustic leakage.

## Sources, by what using them costs

**Tier 1: development material, no release needed.**
- Quicksand ElecGtr1 (The Travelling Band), plus ElecGtr2 and Doom Flamingo "Measurements" after the ear.
- Starnes And Shah and The Long Wait: verified DIs, dropped by cleaning or rule 1.
- Adam Buckley: clean, 5 verified DIs. It is one of K's 2 bands, so using it is a user decision.

Also Turbosauro's 3 unchecked DIs and Quicksand ElecGtr3 (checked in step 0).

This tier is small: about 6 bands, 8 verified DIs (5 of them Adam Buckley) and 3 pending the ear. Starnes And
Shah and The Long Wait are 1 section each and stay out unless cleaning and rule 1 change.

**Tier 2: held-out material on disk with full backings. Release is the user's call; released material is never
a test again.**
- Sets 1–2 held-out Cambridge (about 3 test uses each): Boogie Snakes, Forkupines ×2, Lights Off Clarity
  ("North To Alaska"), The Maybe Next Years, Tim Taler. That is 6 sessions, 5 bands and 24 guitar DIs, all with
  drums and bass.
- Set 3, held-out split spent: Dunning Kruger ×3 and Silona (indie rock, dream pop).
- Set 5 (1 test use): only Hazael ×2 and Peter White have backings on disk. Using them spends part of the only
  lightly used clean/crunch held-out set.

**Tier 3: needs a re-download (user's yes).** Set 5's other sessions are on disk as guitar tracks only: BKS ×2,
Ronnie Jones, Saturn Syndicate, Chris Durban, Hannes Keseberg. Three Hugging Face re-hosts have offset timelines.

**Weak prior:** the Telefunken live-room sessions (Briana Maia, Catbite, Wild & Co, Crazy Swedes). Their DIs
have often been heard processed, and their drums carry bleed.

V-real (7 bands) is not trained on and is read again as the test. A guard bars all 7 bands, including their
other songs, from the pool. Set 4 stays out: it is mostly metal, and its 2 clean Sonnet & Alcohol parts don't
justify spending it. A later confirmation needs fresh songs.

## Steps

**Step 0: tier 1 checks and tier 2–3 metadata (zero renders, CPU, about 2–4 h, plus one ear sitting).**
- Tier 1: run T0's DI checks and the cleaning scan, then a `cmd_plan`-style dry run.
  - Report the yield after rule 1, the cap and cleaning, per band and class.
  - Name the rule that drops each example, such as acoustic guitars counted as active, or `MAX_OTHERS=4`.
  - DIs that need the ear go to one sitting with the user.
- Tiers 2–3: read the catalogs only. No audio is read before release.
  - Per session: guitar parts with a DI, genre, the gain class where one is stored (sets 1–2 have none; it comes after release), the backing tracks, and the guitar count
    against the cap.
- The user approved releasing tier 2 and re-downloading tier 3 (B and C, 2026-10-28), so the released sessions go
  through the same checks and dry run straight away, and their numbers are reported (the user can still stop it).

**Step 1: the leak rule (zero renders, CPU).**
- Keep the meter session-level, since that is where the −35 dB floor was validated. For each example, apply a
  (guitar, stem) reading only when that guitar is both replaced in the example and active in its section.
- Treat a target double with no DI as the target, and leave the example out.
- Also check rule-1 amp-track stand-ins for bleed from the replaced guitars.
- Exempt only tracks named DI, sample or synth. Pre-recorded tracks, master bounces and mic'd keys, bass or
  Leslie tracks stay under the meter.
- Negative controls: read the line-level tracks' false-drop rate. A reading above about −10 dB counts as reverse
  bleed (the stem in the guitar mic), not leakage.
- Validate before use:
  - stems kept and dropped per session under both rules;
  - 5 backing clips under the new rule, heard by the user;
  - unit tests.

**Step 2: the pool (renders; ledger first).**
- **Composition.**
  - Clean and crunch non-metal songs lead.
  - Heavy examples are at most 20%, with backings rebuilt under step 1.
  - The review notes that "not high gain" also removes Death Of A Romantic (all its DIs are high gain) and
    Hollow Ground. Storm Of Particles and Ale Lak have no class, so they are classified first, and only their
    non-high-gain sections are eligible.
- **Size and recipes.**
  - The size matches F5 (about 4.1k examples). If the yield is smaller, use all of it, report it, and note the
    size confound.
  - Recipes follow `example_recipe`. Settings are drawn as part C drew them.
- **Engineering.** New sessions need inventory, sections, backing metadata and mix parameters. The guards need
  amending: F_POOL, `check_example`, `refuse_held_out`, `clean_di.REFUSED_SESSIONS` (Dunning Kruger "Sascha") and the set3/set5 covers, which fail
  closed. Tests and a
  review come before any render.
  - **Groundwork (2026-10-28, `learn/cc_pool.py`, zero renders).**
    - The 19 released sessions are declared in `cc_pool.RELEASED`. `refuse_held_out` passes them, under their
      declared band only. Their crops and their bands' unreleased material stay held out.
    - "Sascha" stays in part A's `excluded` list (part A's inventory reproduces); it is released to this pool only.
    - Each declaration's `held_out_uses` records the release. `refuse_test` bars them, their songs, slugs, crop
      folders and bands from any later test (names casefolded, `_`, `-` and spaces alike, every path component),
      plus Fytakyte "Too Much" (BKS's song, re-hosted), which never trains either. `set3.parts`, `set5.parts` and
      `set5_test.parts` leave them out by default; reproductions of earlier tests opt in (`include_released`).
    - Every pool row enters through `pool_rows` (released, tier 1 and part A rows alike): it bars V-real's 7 bands
      (any of their songs), the known-answer and reserved bands (names casefolded, punctuation ignored), and fails
      closed on a missing band.
    - Set-5 parts whose only passing amp tracks belong to another part are no DI rows (BKS "Too Much" ElecGtr4a,
      "Bulldozer" ElecGtr6a). Set 5's other excluded and failing parts stay pending, and set 5's status and reasons
      are in each row's notes.
    - Part C's `F_POOL`, `check_example` and `pool_examples` are unchanged: the new pool does not go through part
      C's pool.
    - The released sessions' DI rows (pending the ear), part A's screen and sections, their backing metadata and
      T0's stem scan are written under their own names (`~/ndsp-presets/learn/clean-crunch-pool/`,
      `t0/ccstems-*`). Part A's inventory and manifest and T0's `stems` shards are not touched.
- **Amendment 1 (2026-10-29, after the audit of the pool's checks; independently reviewed, the review's fixes in).**
  The first dry run kept 38 of 144 eligible sections (5 bands, BKS 68% of training): rule 1 left out 105, almost all
  because no stand-in amp track passed the bleed check. The audit (`trusted-data/audit-checks-2026-10-29/`) found
  that 0 of 79 stored amp tracks could pass, through bugs in the verdict, and that two other checks were stricter
  than T0's own. Changes (`learn/cc_build.py`, `learn/trusted_data.py`):
  - **The bleed verdict, repaired.** Per non-guitar source in a stand-in: a source silent where the amp track plays
    cannot fail it; the take's interval (the real reading less each rolled reading) decides: pass when its upper
    bound is under −30 dB, fail when its lower bound is at or above it, else unmeasurable (the track fails, as
    before); the "plays on under half the frames" rule is dropped; a blow-up (a reading beyond the amp track's own
    energy) is unmeasurable whatever the real reading's sign, and so is a source with no rolled reading. The track
    also fails when its takes' power sum reaches −30 dB (A6's line, unchanged). The audit's floored-ridge estimator
    is not used (the audit found it worse). Its "a non-positive real reading passes" is **not** adopted: the repo's
    synthetic injection at −25 dB reads a real value of −0.0023 against rolled readings of −0.0056, so that clause
    would pass a real leak (it stays a flag, `AMP_NEG_PASS`, off). Tests: the audit's repros and its injection on a
    real amp track (BKS "Too Much", −20/−25 dB fail, −30 straddles, −35 passes). The same verdict serves T2's rule 1:
    a re-run of T2's (or T3's) plan would read its stand-ins under it.
  - **A power sum over lower bounds (a flag, off).** The review found 37 of the 54 failing tracks fail only on the
    power sum, every source passing alone: summed noise excursions. `AMP_SUM_LOWER` (`plan --dry --sum-lower`) sums
    each source's lower bound (real less its highest roll) instead of its point take. Not adopted; read in the table.
  - **D4 no longer holds windows of a DI the ear heard clean.** This reverses T0's rule (`verify_tracks.py` near line
    2706: a verified DI waits while any D4-flagged window is unheard). Processing is a property of the track, the ear
    heard these DIs clean, and D4 separates clean from processed DIs at near-chance AUC 0.57 (the audit's
    cross-table). D4 still sends windows of unheard DIs to the ear. It admits 26 candidate sections with D4-flagged,
    unheard windows (part A's screen clean, not high gain). Quicksand ElecGtr2 (heard clean, held by D4 alone) is
    admitted; Quicksand ElecGtr3's step-0 status is read, and it stays out until heard.
  - **Step 0's D2 gates windows, not whole DIs** (as T0's `di_row_status` reads it). It changes nothing today: it
    only decides which DIs go to the ear, and an unheard DI never trains.
  - **The cleaning scan** (zero renders) now covers the pool's 163 eligible sections that had no row (rows in
    `trusted-data/cc/scan/`, read with part C's).
  - **Open policy for the user:** should a stand-in's non-guitar bleed (drums, vocals, keys) block it, given the
    real song's mix holds the same bleed? A flag (`plan --dry --no-bleed-gate`); today's gate stays on until the user
    rules. The target-guitar checks (`cleaning_clash`, `target_doubles`) stay on either way.
  - **The hiss screen** is unchanged until the user answers ear page part 14.
  - **Dry yield** (zero renders, 2026-10-29; 3,467 training examples by part C's cycle, FS_CC beside):

    | | Gate on (today) | Gate on, lower-bound sum | Gate off (the open policy) |
    |---|---|---|---|
    | Sections kept (of 176 eligible) | 89 in 5 bands | 101 in 5 bands | 161 in 7 bands |
    | By band | Forkupines 31, BKS 32, Travelling Band 18, Ale Lak 5, Storm Of Particles 3 | Forkupines 43, BKS 32, Travelling Band 18, Ale Lak 5, Storm Of Particles 3 | Forkupines 59, BKS 35, Travelling Band 28, The Maybe Next Years 17, Adam Buckley 14, Ale Lak 5, Storm Of Particles 3 |
    | Clean / crunch sections | 25 / 64 | 25 / 76 | 51 / 110 |
    | BKS share of training examples | 37% | 32% | 22% |
    | Heavy share | 7% | 6% | 4% |
    | FS_CC | 14 sections, 647 examples | 14 sections, 558 examples | 21 sections, 520 examples |
    | Examples in all | about 4.1k | about 4.0k | about 4.0k |
    | Left out by rule 1 and the cap | 87 | 75 | 15 |

    With the gate off the lower-bound sum changes nothing (161): the bleed verdict no longer decides.
  - **Process gate.** No written (non-dry) plan and no render until the user has answered ear page part 13 (the new
    sessions' stem spot-checks; `plan` refuses until they are heard clean) and decided the bleed gate.
- **Cost.** About 12–16k renders: about 8–12 h with priming and the carry-over rule. About 4k separations, 3–5 h.
- **Report.** Bands, sections and DIs for both pools.

**Step 3: train and read (training approved with the plan; minutes per run, as F5's 4 runs took 37 min).**
- **Arms**, each with 2 seeds matched to D_F5's:
  - D_CC: the new pool;
  - D_F5bk: F5's stored renders remixed under step 1's backings. This separates the backing fix from the
    change of songs. Its fit set is FS5 remixed the same way, so it differs from D_F5 only in the
    backing. It costs about 4.1k separations and no target renders. Measured: 2,479 examples change (Death Of A
    Romantic and Storm Of Particles), about 2.5k separations. The mix holds each example's drawn
    guitar-to-backing ratio, so the louder backing gets a lower gain (median −4.8 dB and −2.3 dB on the first
    builds): the other guitars sit lower against the target and the stem's SNR rises (median +4.5 / +1.0 dB).
    D_F5bk − D_F5 is read with that beside it (ledger `trusted-data-t3`, amendment 6).
- **Fit and early stopping:** a declared set drawn from the new pool, with no V-real band.
- **Readout,** declared before the first read:
  - on V-real-11, as D_F5 was read, so no new D_F5 renders are needed;
  - D_CC − D_F5 and D_F5bk − D_F5, band-weighted, with 90% band-clustered intervals;
  - per class, with wins, ties and losses;
  - time-effect heads set to S as a co-primary. D_F5's gate was driven by one part through time-effect heads.
- **Power.** The clean read is 3 parts in 2 bands, so it cannot decide alone. Crunch carries most of the power.
  No pass/fail bar: build on any gain, and report underpowered results as undecided.
- **V-real renders:** 165 per arm (33 groups × a priming render and 2 answers × 2 directions): the co-primary needs its
  own rendered answer (ledger `trusted-data-t3`, `amendment_6_readout`; code `learn/cc_readout.py`). The arm's answers
  render right after the priming render, while D_F5's stored ones came later in their groups, so the primary carries
  the render-order noise of delay and reverb (amendment 5's caution); the co-primary sets the time effects and spring to
  S's (off), so it does not.

**Step 4: listening page.** Pairs come from the new pool's clean and crunch examples:
- full backing, with drums and bass present;
- the guitar exposed;
- an original guitar tone that sounds typical.

Ledger first. The render recipe is the audibility page's.

## Decisions for the user

- **A. Use tier 1, including Adam Buckley.** Adam Buckley is one of K's 2 bands.
- **B. Release tier 2 into training:** sets 1–2 Cambridge held-out, set 3's Dunning
  Kruger and Silona, and set 5's Hazael and Peter White.
- **C. Re-download set 5's backings (tier 3).**
- **D. The heavy share:** at most 20%, non-high-gain sections only. This drops Death Of A Romantic and Hollow
  Ground.
- **E. The ear sittings:** tier 1 DIs, the released DIs, and 5 backing clips.
- **F. Step 3's training:** minutes per run, approved with the plan.

F20 waits for step 3's reading and is re-planned on this pool.
