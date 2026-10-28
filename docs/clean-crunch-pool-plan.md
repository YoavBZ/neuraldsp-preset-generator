# Clean/crunch-led training pool (plan, 2026-10-28)

**Status: approved by the user on 2026-10-28 ("Yes for all": decisions A–F below). Nothing run yet.**

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
    - "Sascha" left `REFUSED_SESSIONS`.
    - Each declaration's `held_out_uses` records the release. `refuse_test` bars them, their songs, slugs and
      bands from any later test, plus Fytakyte "Too Much" (BKS's song, re-hosted), which never trains either.
    - The pool's own guard (`refuse_pool_band`, `check_pool_rows`) bars V-real's 7 bands (any of their songs), the
      known-answer and reserved bands, and fails closed on a missing band.
    - Part C's `F_POOL`, `check_example` and `pool_examples` are unchanged: the new pool does not go through part
      C's pool.
    - The released sessions' DI rows (pending the ear), part A's screen and sections, their backing metadata and
      T0's stem scan are written under their own names (`~/ndsp-presets/learn/clean-crunch-pool/`,
      `t0/ccstems-*`). Part A's inventory and manifest and T0's `stems` shards are not touched.
- **Cost.** About 12–16k renders: about 8–12 h with priming and the carry-over rule. About 4k separations, 3–5 h.
- **Report.** Bands, sections and DIs for both pools.

**Step 3: train and read (training approved with the plan; minutes per run, as F5's 4 runs took 37 min).**
- **Arms**, each with 2 seeds matched to D_F5's:
  - D_CC: the new pool;
  - D_F5bk: F5's stored renders remixed under step 1's backings. This separates the backing fix from the
    change of songs. Its fit set is FS5 remixed the same way, so it differs from D_F5 only in the
    backing. It costs about 4.1k separations and no target renders.
- **Fit and early stopping:** a declared set drawn from the new pool, with no V-real band.
- **Readout,** declared before the first read:
  - on V-real-11, as D_F5 was read, so no new D_F5 renders are needed;
  - D_CC − D_F5 and D_F5bk − D_F5, band-weighted, with 90% band-clustered intervals;
  - per class, with wins, ties and losses;
  - time-effect heads set to S as a co-primary. D_F5's gate was driven by one part through time-effect heads.
- **Power.** The clean read is 3 parts in 2 bands, so it cannot decide alone. Crunch carries most of the power.
  No pass/fail bar: build on any gain, and report underpowered results as undecided.
- **V-real renders:** about 99 per arm.

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
