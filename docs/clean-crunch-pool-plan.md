# Clean/crunch-led training pool (plan, 2026-10-28)

**Status: approved by the user on 2026-10-28 ("Yes for all": decisions A–F below). D_F5bk read 2026-10-29 (165 renders). Step 2 built and step 3's D_CC read 2026-10-30 (amendments 1 and 2 below): undecided, leaning worse. Step 4's page sent 2026-10-30; its answers came in the same day: no pair heard as clearly different, so the page does not place tau. Runaway delays in about 2% of both pools, excluded from the next build. The user said yes to the two cheap D_CC follow-ups and the ElecGtr8 shift (2026-10-30, amendment 4): the follow-ups ran the same day; D_CC's loss is mostly its pooled answer's pedals (both seeds' answers turn the drives off, answers only, not rendered), and D_CC is worse than its own pool's constant; the shift waits for the next build. A drive-pedal page with an instant A/B switch (amendment 5, the user's yes 2026-10-30) was rendered, audited and sent the same day (17 items). Its checks take the place of the replay of three items, which the author dropped. The user then asked for the guitar alone instead of mixes (2026-10-30): guitar-only versions of the drive page and step 4's page were declared (amendment 6, zero renders), then built, audited and sent the same day (17 and 25 items). Their answers came in the same day (amendment 6's answers): on the guitar alone the format works (catches 8 of 8 right, 5 of 6 checks heard), but 25 of the 26 pairs near tau were not heard; mostly only the loudest pairs are. F20's re-plan comes next, for the user's yes.**

**Progress (2026-10-28 to 30):**
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
- **Part 12 answered (2026-10-29):** all 12 cards clean (the 8 unsure DIs, each heard beside its amp track): 24 DIs
  clean in all, 7 processed.
- **Step 2's first dry yield (2026-10-29, zero renders): 38 of 144 eligible sections** (5 bands, BKS 68% of training).
  Rule 1 left out 105: no stand-in amp track passed the bleed check, and the new sessions had no cleaning-scan rows.
- **The audit and amendment 1 (PR #329, reviewed and merged):** 0 of 79 stored amp tracks could pass the bleed check
  (verdict bugs), and D4 and step 0's D2 were stricter than T0's own rules. Repaired verdict, D4 no longer holds a DI
  the ear heard clean, D2 gates windows, the cleaning scan on 163 sections: 89 sections with today's gate, 161 without.
- **Parts 13–15 answered (2026-10-29/30):** part 13 all 31 clean (7 stem spot-checks, 24 flagged DI windows); part 14
  (the audit's sample of rejected items) 22 of 23 clean, including all 10 bleed-rejected stand-ins heard against the
  mix and 4 of 5 D2-hum DIs; part 15 (35 cards) all 7 stem spot-checks clean, 25 of 28 DI cards clean (Tim Taler
  ElecGtr02c processed; Saturn Syndicate ElecGtr3DT heard with hum, out by the declared rule). The user's decisions:
  the non-guitar bleed gate on stand-ins is off (the target-guitar checks stay on); part A's hiss flag no longer
  screens a section (hum and bleed still do); part 15 for the DIs step 0's D2 had kept from the ear. Peter White stays
  out (two DIs heard processed, the third "sounds like an amp track").
- **The alignment check (2026-10-30, zero renders; amendment 2):** every training DI against its own amp track, on
  the windows where both play (every 5 s; GCC-PHAT over ±3 s, onset envelopes where the amp is too driven for GCC; at
  least 3 readings): 50 of 61 are in time (48 by GCC at 0.3 to 24.4 ms, mic delays; Adam Buckley ElecGtr2 and
  ElecGtr2DT by their envelopes at 0 ms, in 10-ms steps). Out (fail closed, nothing shifted):
  Forkupines SugarFaith ElecGtr8 a constant +129.8 ms offset against its amp track; Chris Durban ElecGtr3a drifts
  (10.3–10.5 ms, a 6.2 ms stretch at 4:23–4:43, 0 ms at 2:53 and −1,341.88 ms at 4:48); Tim Taler ElecGtr04a reads
  −0.25 ms, outside A1's 0.1–30 ms (its amp track 12 samples before the DI); too few readings for Forkupines
  Semantics ElecGtr03 (1 of 20 windows), Adam Buckley ElecGtr5 and Ronnie Jones ElecGtr06 (2 each, consistent, under
  the 3 needed); and 5 DIs with no amp track of their own (Storm Of Particles ElecGtr01–03, Dunning Kruger JapanSong
  Gtr4, Hannes Keseberg ElecGtr2), which cannot be timed (against the song, in-time controls peak at beat multiples
  too). A1's prominence floor of 12 was set for a ±50 ms search; over ±3 s it admits an occasional spurious peak
  (Adam Buckley ElecGtr2's +2,459.75 ms reading). Such a peak can only turn a DI into a false "drift" or "offset",
  never a false "aligned". The two notes from part 15: Hazael ElecGtr3 is in time (1.5 ms throughout), but its amp
  track is silent from 1:07 to 1:21 while the DI plays on (what the user heard), so a target section is now left out
  when no own amp track plays on 30% or more of the DI's playing frames in it (14 sections: Dunning Kruger EnDance
  Gtr6a 7, Hazael ElecGtr1 4 and ElecGtr3 3); Hannes Keseberg ElecGtr2 cannot be timed (no amp track; set 5 found
  none that passes its same-take tests) and is out.
- **Step 2 built (2026-10-30, PR #332's plan):** 3,890 examples rendered (17,661 renders with priming) and separated
  (3,034 separations, 802105 by both workers, plus 1 redo; 3,033 examples kept; 856 near-silent renders and 1 with no
  backing refused by the declared rules, the targets' 15.8% as in F5's). D_CC trains on 2,699 examples with 334 for
  early stopping (D_F5: 3,467 and 722).
- **Step 3's D_CC read (2026-10-30, audited; ledger `clean-crunch-pool-dcc` `outcome`):** D_CC − D_F5 +0.090
  [−0.011, +0.191] on V-real-11, 1 band better and 6 worse: undecided, leaning worse. Clean +0.015, crunch +0.120.
  Part-weighted (descriptive): +0.090 [+0.006, +0.175], 9 of 11 parts worse; that interval sits above 0 and supports
  "leaning worse", while the declared band-weighted primary stays undecided. Also worse (descriptive) than D_core5
  (+0.169), S (+0.177) and D_F5's constant (+0.085), each interval above 0. The audit found no bug. Most of the loss
  (post hoc, descriptive): D_CC has both drives off in all 14 pr12-crunch directions, where the constant had both on
  and D_F5 had drive2 on in 12 and drive1 in 5 (likely the seed whose best epoch was 9 of 14; not confirmed on
  V-real); and one part, Wall Of Death's femme ElecGtr5, gives +0.363 (without it +0.044). Confounds: fewer examples
  than D_F5, a small early-stopping set, and amp-track stand-ins in 44% of the examples.
- **Step 4's page (2026-10-30, audited; ledger `amendment_3_outcome`):** 266 renders, 30 of 30 repeats bit-exact; 25
  items (22 pairs, 3 catches) sent to the user. Caveat: 13 items come from one song. Nothing decided by the page itself.
- **Step 4's answers (2026-10-30, audited; ledger `amendment_3_answers`):** 21 same, 4 maybe, none different; all four
  anchors answered same, one catch maybe. The page itself checked out (clips rebuilt, right order, catches identical).
  Its own checks did not come out, so it does not place tau by ear; nothing suggests switches below tau are audible
  (the anchors were not heard either, so the sitting cannot show this). The relabel's reader is still unwritten.
  The delay anchor (900215) is a runaway delay: a steady whine, and its stored target too. The user is asked to replay
  items 4, 13 and 17. A zero-render scan then found runaway delays (mostly feedback 0.75 or more) in about 2% of both
  pools (D_CC 64 of 3,033 kept: training 58 of 2,699, FS_CC 6 of 334; D_F5 87 of 4,189: F5 70 of 3,467, FS5 17 of
  722). Excluding them is the author's reading of the trusted-data rule (the labels are correct settings, the audio is
  not a usable target), and it thins high-feedback delay draws: an audio runaway check refuses (F20: redraws) them in
  the next build, to be declared and reviewed in F20's re-plan. D_CC and D_F5 stand as read, with that caveat.
- **D_CC's follow-ups, declared (2026-10-30; the user's yes; ledger `amendment_4`; nothing run yet):** (a) each
  seed's own answer on V-real-11, zero renders: drive switches, inputGain and amp head per seed beside D_F5's stored
  per-seed answers, asking whether seed 20261043 alone turns the crunch drives off; (b) D_CC with its pedals at S and
  D_CC's own constant, 165 renders, four descriptive rows (pedals at S against D_CC and against D_F5's pedals at S;
  D_CC against its own constant; that constant against D_F5's). (c) Forkupines Sugar Faith ElecGtr8's DI is read from
  a copy delayed by 129.83 ms (its amp track runs that far behind it) and joins the next build only if the alignment
  check on the copy reads about 0 ms. The size-matched top-up stays unplanned.
- **D_CC's follow-ups, read (2026-10-30, audited; ledger `amendment_4_outcome`):** (a) both seeds turn the pr12-crunch
  drives off (answers only, not rendered: drive2 on in 2 and 0 of 14 directions; D_F5 12 of 14), so seed 20261043
  alone is not the cause. In D_CC's labels drive2 is on in a bare majority of pr12 crunch (52.7%), and the model's
  drive2 probability there is 0.42–0.50: a switch near chance, read at 0.5, comes out off. inputGain's median there:
  D_CC −1.39, its constant −0.16, D_F5 −0.49. (b) 165 renders; the sound rows are of D_CC's pooled answer only. D_CC
  with its pedals at S − D_CC −0.076 [−0.142, −0.011], better in all 7 bands (V-real-10 −0.072 [−0.139, −0.005]);
  with the pedals at S, D_CC − D_F5 is +0.015 [−0.028, +0.057] (undecided, about even; V-real-10 +0.017). So D_CC's
  loss is mostly its pedal answers; with the Wall Of Death band left out, all of it (−0.045 against +0.044). D_CC −
  its own constant +0.103 [+0.051, +0.155], worse in all 7 bands (V-real-10 +0.099; not only the drives: pr12 and
  sw50r clean too): on V-real the model does not yet beat a constant (D_F5 about equals its own). Descriptive. Two
  questions for F20's re-plan: how near-chance switches are read out, and the model beating its constant. (c) not
  run: the shift and its alignment check change the verdicts, so they run within the next build.
- **The drive-pedal page (declared 2026-10-30; ledger `amendment_5`, `learn/cc_drive_page.py`):**
  the user said yes to a page with drive pedals on and off. Step 4's qualifying examples less the runaway-flagged
  ones (43): drive pedal 1 on in 12, drive pedal 2 in 12 (24 pairs, 19 examples, 5 bands; 11 of the 24 pairs from one
  song, The Travelling Band's "Quicksand"); step 4's r_on' reused for 14 examples, each checked by a bit-exact
  repeat; 96 new renders. A new player loops both mixes and switches between A and B at once. At most 21 items, about
  10.5 min: at most 14 pedal pairs, 3 catches, step 4's loudest reverb and sw50r spring pairs as checks, and a catch
  with each check's title (0 renders), so a check's title no longer marks a real difference. Step 4's item 4 (900215,
  the runaway delay) is not re-used: it is a dirty (runaway) example. The author dropped the separate replay of items
  4, 13 and 17 (reported to the user 2026-10-30); the checks take its place. Heard means the verdict "They differ"
  ("Maybe, barely" is reported beside, not counted). A check heard here but not on step 4's page is consistent with
  the old format hiding differences, not proof of it: only the checks and their catches carry the titles reverb and
  sw50r spring, it is the listener's second hearing of those clips, and the listener may know which items are checks.
  Descriptive; decides nothing.
- **The drive-pedal page, sent (2026-10-30, audited; ledger `amendment_5_outcome`):** 96 renders (48 priming), 19 of
  19 repeats bit-exact, none refused. Median A_e: drive pedal 1 0.081, drive pedal 2 0.093; one pair per pedal below
  tau. 17 items, about 8 min: 10 pedal pairs, 3 catches, the 2 checks and a catch under each check's title. Caveats:
  10 of the 17 items come from one song ("Quicksand"); the 17 items use 10 distinct 10-s excerpts (803173's in items
  2, 3 and 17, 2 and 3 back to back; 900339's in items 1, 7 and 12; 800877's, 802682's and 801895's twice each), and
  neighbouring Quicksand windows overlap by 5 s (items 4, 13, 5, 10, 15; items 14, 2, 3, 17). On the page's pairs:
  in drive pedal 2's loudest pair the guitar sits 5.9 dB lower with the pedal off (balance, which A_e cannot see);
  the pairs near tau are not physically small (−15.0 to −20.5 dB, near the reverb check's −14.4 dB). Among all 24
  measured pairs, five others move the guitar 3.2–4.1 dB and five pedals have drive or gain at 0 (two on the page).
  Answers pending; nothing decided.
- **Guitar-only pages (declared 2026-10-30; ledger `amendment_6`, `learn/cc_solo_pages.py`):** the user, the same
  day: "The mixes make it harder to distinguish, please only the guitars if possible", then "Same for the previous
  effects listening page". Zero renders: the drive page's 17 items (part 1) and step 4's 25 (part 2) rebuilt from the
  stored renders as the guitar alone (no backing, no other guitars, no stand-ins, no mastering), each clip at
  −23 LUFS, in the drive page's A/B player, with new ids, order and A/B draw. Step 4's item 4 (900215, the runaway
  delay) is replaced by the loudest non-runaway delay pair, 803054 (A_e 0.447; its reverb is on too). The guitar plays
  in 96–100% of each on clip's window and 87–100% of each off clip's (803054's delay-off clip is about 1.3 s silent
  where the on clip has echoes). The solo clips differ more than the mixes did for all 12 of part 1's pairs and 21
  of part 2's 22 (part 1's drive pairs −2.7 to −14.4 dB, part 2's pairs −5.9 to −29.0 dB). The AAC coding error sits
  12.4 dB under 801921's reverb pair difference. The answers show whether each switch is audible on the guitar
  alone, levelled apart: roughly an upper bound on its audibility in a song, except that levelling removes a balance
  change the switch makes in the mix (801895: 5.9 dB). Against step 4's in-mix answers, masking is confounded with
  the old sequential player and a repeat hearing; only part 1 against the drive page's in-mix answers (not asked for
  now) would isolate it. They cannot show whether a switch is heard in a song, nor tau (the items were picked by
  their in-mix A_e). Not built before review; decides nothing.
- **Guitar-only pages sent (2026-10-30, audited; ledger `clean-crunch-pool-dcc` `amendment_6_outcome`):** zero
  renders; part 1 (17 items) and part 2 (25 items, 803054 in place of 900215) built from the hash-checked stored
  renders, the guitar alone in every clip, each at −23.00 LUFS, catches byte-identical, the in-mix pages and keys
  unchanged. Smallest AAC margin 23.1 dB in part 1 and 12.4 dB in part 2 (801921's reverb pair). Caveats: part 2 has
  back-to-back items on one excerpt (10–11, 12–13, 24–25); 800877 (its pair and its catch) and 802682's sw50r spring
  pair are in both parts (800877 with the same A/B order, so not independent answers); levelling each clip on its own
  removes the switch's level drop (801895 5.9 dB, 800903's pr12 spring 3.0 dB, 802200 2.0 dB). Nothing decided.
- **Guitar-only answers (2026-10-30, audited; ledger `clean-crunch-pool-dcc` `amendment_6_answers`):** both parts
  answered the same day. Catches 8 of 8 "same". Of the 6 distinct anchors and checks, 5 were heard (drive pedal 1
  801921, drive pedal 2 801895, reverb 800877, delay 803054, tremolo 803394); 802682's sw50r spring was heard in
  neither part (its long-term spectrum differs by 1 dB or less). Near tau, 25 of 26 pairs were not heard (21 same,
  4 maybe); the one heard is 802350's tremolo (A_e 0.0039, solo J 2.30). All 8 near-tau drive pairs and all 8 spring
  pairs: same. The heard pairs are the top solo-J pairs in each part (AUC 1.00 in each; A_e 1.00 and 0.81), but the
  edge over A_e rests on 2 items and no single solo-J cut works across effects. The listener noted that items with
  several effects are harder ("13 baseline is 12 with tremolo on so its delay is barely noticeable, if any"): 33 of
  34 pairs have another effect on in both clips, by design (one effect switched in the example's full setting, the
  context the labels need). Caveats: part 1 was fast (8 of 16 answers under one 10-s loop after the previous one),
  so its near-tau result is weak; repeats across the parts (7 heard answers cover 6 pairs); small n. Readings: the
  format works; tau (0.005, in-mix A_e) sits far below what is heard even alone. The audibility weight is declared in
  F20's re-plan, calibrated on these answers; nothing decided here.

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
- **Amendment 2 (2026-10-30, after ear pages 13–15 and the user's decisions; for review before any render).**
  - **The ear.** Part 13 (all clean) clears its 7 sessions' stems and 24 flagged windows; part 14 admits the 4 D2-hum
    DIs heard clean (BKS Bulldozer ElecGtr1a, Saturn Syndicate ElecGtr1DT, Tim Taler ElecGtr01d, Ronnie Jones
    ElecGtr01); part 15 admits 15 more DIs and clears 7 more sessions' stems. A part-15 export is read from either
    build (the first build's 28 DI cards, the second's 35 cards). Any processed, not-a-DI or hum answer still excludes
    a DI (Tim Taler ElecGtr02c, Saturn Syndicate ElecGtr3DT). Peter White stays out.
  - **The user's decisions.** The non-guitar bleed gate on stand-ins is off for real runs (`cc_build.BLEED_GATE`;
    `plan --dry --bleed-gate` reads the old gate, now always with the lower-bound sum); the target-guitar checks (`cleaning_clash`, `target_doubles`) stay
    on, and a stand-in the ear heard with another guitar in it leaves its sections. The lower-bound sum is adopted for
    the pool (it decides only with the gate on). Part A's hiss flag no longer screens a section; hum, bleed,
    clipping and drop-out flags still do. `AMP_NEG_PASS` stays off.
  - **The alignment check** (`cc_build align`; above): a DI trains only when it reads in time with its own amp track
    (fails closed: offset, drift, a lag outside A1's 0.1–30 ms, too few readings or no amp track to time it against
    are out; nothing is shifted; each alignment file carries a hash of the method, and a stale one refuses). A target
    section where no own amp track plays on 30% or more of the DI's playing frames is out (14 sections).
  - **DIs:** 50 train (released and tier 1 as heard and timed; Adam Buckley's, Storm Of Particles' and Ale Lak's as
    T0 verifies and the alignment check times them).
  - **Dry yield** (zero renders, 2026-10-30; 3,467 training examples by part C's cycle):

    | | Amendment 2 |
    |---|---|
    | Candidate sections of training DIs | 891 (out before rule 1: high gain 325, part A's screen 196, DI over a silent amp track 14) |
    | Eligible / kept | 356 / 294 in 9 bands (rule 1 and the cap leave out 62: no usable stand-in 29, the target's own take in a stand-in 21, a stand-in doubling the target 8, the cap 4) |
    | By band | Forkupines 101, BKS 80, The Travelling Band 36, Hazael 30, The Maybe Next Years 23, Adam Buckley 13, Ale Lak 6, Storm Of Particles 4, Dunning Kruger 1 |
    | Clean / crunch sections | 93 / 201 |
    | Training examples by band | Forkupines 1,244 (36%), BKS 975 (28%), The Travelling Band 424, Hazael 349, The Maybe Next Years 265, Adam Buckley 131, Ale Lak 39, Storm Of Particles 26, Dunning Kruger 14 |
    | Heavy share | 2% |
    | FS_CC | 32 sections, 423 examples |
    | Examples in all | about 3.9k (13 training examples per section) |

  - **Process gate.** No written plan and no render before amendment 2's independent review; the plan still refuses
    while a pool session's stem spot-check is unheard (none is now).
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

**As declared (2026-10-30; ledger `clean-crunch-pool-dcc` `amendment_3`; code `learn/cc_audibility.py`):**
- **Pairs:** 71 pairs from 32 examples in 29 sections of the D_CC pool (44 examples qualify). The rules:
  - the guitar is exposed: at most 6 dB under the rest, no vocals drawn, at most 2 other guitars counting recorded
    stand-ins;
  - drums and bass play in the window, each within 20 dB of the backing;
  - the band isn't heavy;
  - the tone is typical, read as part C's factory or start draw with the drawn class equal to the section's.
- **Effects:** the audibility page's 5: delay 22, reverb 24, tremolo 10, pr12 spring 9, sw50r spring 6. The springs
  are thin, so the page may have fewer than 28 items.
- **Recipe:** the fresh-process recipe with bit-exact repeats, 266 renders. Each process opens through `cc_build`'s
  renderer after the separation wait.
- **Page:** up to 28 blind pairs nearest tau, with anchors and 3 catch pairs.
- **Decides:** nothing alone. The answers check tau by ear; a reader for the export is written and reviewed before
  the relabel uses them. Drive pedals are a separate question for the user.

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
