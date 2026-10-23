# The review before the ear (2026-10-23)

The user asked, after the trusted-data change (#280–#285), for a multi-agent review: "make sure we're on the right
track. Let's avoid any mistake we could have caught in advance", then widened it to the roadmap, the ML approach, the
algorithms, cleaning, training and testing.

- **Review 1, the trusted-data change:** 5 reviewers (`verify_tracks`; `trusted_data`; the ear pages and the import of
  their answers; the docs against each other and the code; the strategy), then a skeptic per reviewer who tried to
  refute each finding.
- **Review 2, the program:** 6 reviewers (roadmap, ML approach, algorithms, cleaning, training, testing), then a
  skeptic per pair.
- **Result:** 102 findings: 73 confirmed, 23 plausible, 6 refuted.
  34 fixed in code, 23 user decision, 23 fixed in the docs, 16 later, 6 refuted.
- **Nothing was rendered, trained or listened to,** and no threshold moved. The code fixes have regression tests that
  fail on the old code. The next `verify_tracks lists` run recomputes T0's verdicts under the fixed rules.

## What mattered most

- **The ear's import would have lost answers.** `lists` rebuilds every verdict from the exports it is given and kept
  nothing between runs; the ROADMAP said to run it "with each part's export" and left out the sitting-1 export. Run
  part by part, each run would have forgotten the earlier parts, and DIs the user heard as processed (Eggy's among
  them) would have read verified and entered training. Now `lists` refuses both mistakes.
- **"Not sure" counted as clean** for the sampled DIs, and **a clean answer cleared a flagged window it only half
  covered.** Fixed.
- **The self-built mixes had two realism bugs:** other guitars sat 3 dB low against the stems, and doubles of the
  target's part came back with their own tone (the cleaning had removed them from SES). Fixed.
- **T2 could stall or mislead:** one refused example blocked every training run, a re-plan could reuse stale
  renders, and the report printed a verdict from incomplete renders. Fixed.
- **What T2 can tell:** V-real is 7 bands (2 clean), so a tie cannot rule out a loss as large as D's whole margin over
  S, and the song-blind constant has never been scored on real mixes. These are user decisions (ROADMAP, open
  decisions).
- **No fresh test is left for the decision test.** V-real is development data; where the decision test's data comes
  from is a user decision before T4.

## Every finding

Review, dimension, id, the skeptic's verdict and severity, the finding, and what was done.

| R | Dimension | Id | Verdict | Sev. | Finding | Done | How |
|---|---|---|---|---|---|---|---|
| 1 | ear-page | EAR-1 | confirmed | blocker | `lists` keeps no memory of earlier ear answers and runs without the sitting-1 export: importing one part at a time, or leaving out --ear-di, silently drops answers and re-admits DIs the user heard as processed | fixed in code | as VT-1 |
| 1 | verify-tracks | VT-1 | confirmed | blocker | `lists` stores no ear answers between runs and does not require --ear-di, so the ROADMAP's per-part import drops earlier negatives and can mark DIs the user rejected as verified | fixed in code | lists refuses without --ear-di or when it would drop an earlier export; exports hashed |
| 1 | docs-consistency | DOC-1 | confirmed | high | The import instruction drops answers: ROADMAP's next step leaves out --ear-di and does not say all exports go in one call, and `lists` keeps only the files passed on that call | fixed in the docs | one cumulative command in the ROADMAP, design, usage line and page docstring |
| 1 | ear-page | EAR-2 | confirmed | high | An 'unsure' answer on a sampled DI clears the sample and makes the DI verified, as if it had been heard clean | fixed in code | only a clean answer clears a sampled DI |
| 1 | trusted-data | TD-2 | confirmed | high | After a lists change and a re-plan, old render/build rows are reused, so an excluded DI can stay in a backing | fixed in code | re-planning over rows with another recipe refuses; the lists hash ignores run time |
| 1 | docs-consistency | DOC-2 | confirmed | medium | Recorded decision 2 says the two 'conflicts' wait for the user's ear, but they are excluded on measures before the ear is read and are never put in the queue | user decision | as VT-2; the plan's notes and ROADMAP now say what the code does |
| 1 | docs-consistency | DOC-3 | confirmed | medium | Two parts of the approved T0 sitting are missing from this sitting and from the next order: the by-ear stem spot-check and the conflicts | user decision | as VT-5 |
| 1 | docs-consistency | DOC-6 | confirmed | medium | T2's power and tie line assume about 10 V-real bands; V-real is now at most 7, and no doc restates what T2 can resolve | fixed in the docs | power restated: about ±0.036 at 7 bands |
| 1 | ear-page | EAR-3 | plausible | medium | No check that the DI actually plays in a queued window: noise-floor or hum-floor windows get picked or flagged, pass the silence check, and are raised to -23 LUFS | fixed in code | `build_ear_page check` flags clips that hardly play; re-pick them after |
| 1 | ear-page | EAR-4 | confirmed | medium | Two exports of the same part are both counted: a corrected answer cannot replace the earlier one, and a retracted 'clean' still clears | fixed in code | the latest export of an item replaces the others |
| 1 | ear-page | EAR-5 | confirmed | medium | A window heard clean also clears an overlapping flagged window that was never answered, which breaks 'heard clean clears only the heard window' | fixed in code | as VT-3 |
| 1 | ear-page | EAR-6 | confirmed | medium | Notes from the ear pages are thrown away on import, including notes that qualify or replace a verdict | fixed in code | notes kept in verified.json and printed |
| 1 | strategy | S-1 | plausible | medium | T2's primary will almost certainly read 'tie, picks SYN' whatever the backing does, and its stated power is out of date | user decision | power restated; add the constant arm, and read the tie from the interval? |
| 1 | strategy | S-2 | confirmed | medium | The trusted plan no longer tests the in-scope clean case: almost no clean or crunch training DIs, and V-real's clean class is 3 parts in 2 bands | user decision | per-class rows added; where clean-class DIs come from |
| 1 | strategy | S-4 | confirmed | medium | The recorded decision says the two conflicts wait for the user's ear, but no answer can bring them back and they are not on the pages | user decision | as VT-2 |
| 1 | strategy | S-6 | confirmed | medium | The pages ask for answers the import throws away: after one negative answer, a file's other clips cannot change its verdict | fixed in the docs | skip advice printed by `check` and given to the user |
| 1 | strategy | S-8 | plausible | medium | T1's gate compares against the wrong distribution, and its 'gap' outcome triggers nothing | fixed in code | as TD-5 |
| 1 | trusted-data | TD-1 | confirmed | medium | One refused T2 target blocks every T2 training run: refused examples are counted as 'unbuilt' | fixed in code | a refused example drops for every arm |
| 1 | trusted-data | TD-10 | confirmed | medium | Other-guitar activity is relative to the section's own peak, so a resting DI's noise floor ranks first | fixed in code | activity against the file's own level; silent own amp tracks leave a part out |
| 1 | trusted-data | TD-3 | confirmed | medium | The pan fold is applied to the other guitars but not to the centred stems, putting other guitars 3 dB too low | fixed in code | stems fold by pan_fold(0) |
| 1 | trusted-data | TD-5 | plausible | medium | T1's reading rule measures the intended cleaning gain, not realism, and its consequence is not wired | fixed in code | T1's reading is descriptive; what a realism gap would change is for before T2 |
| 1 | trusted-data | TD-6 | confirmed | medium | `report` prints the T2 decision from whatever V-real directions happen to be rendered | fixed in code | the T2 reading is 'incomplete' until every direction is judged |
| 1 | verify-tracks | VT-2 | confirmed | medium | The two user conflicts (Quicksand ElecGtr2, Today's The Day ElecGtr07) never reach the ear, and no answer could change their verdict | user decision | the two conflicts: measured fails stand, or queue and overrule |
| 1 | verify-tracks | VT-4 | confirmed | medium | A DI with unheard D4-flagged windows is listed as 'verified' (in training_dis or k_dis), and its other windows are usable, although a pending answer can still exclude the whole DI | fixed in code | a DI waits while a D4-flagged window is unheard |
| 1 | verify-tracks | VT-5 | confirmed | medium | Stems are trusted on the scan alone: the plan's T0 by-ear stem spot-check is not in this sitting and is not scheduled before T1 | user decision | the by-ear stem spot-check: an extra part now, later, or dropped |
| 1 | docs-consistency | DOC-10 | confirmed | low | The open K decision ('admit Cnoc An Tursa?') cannot take effect in the code or the budget as written | fixed in the docs | the open decision states the cost (truth renders and a code change) |
| 1 | docs-consistency | DOC-11 | confirmed | low | The re-derived prior's 'passing' set lets in parts pending the ear on A1/A2 and parts the ear rejects, against plan (a)'s 'pass A1-A4 and A6' | fixed in code | as VT-8 |
| 1 | docs-consistency | DOC-12 | confirmed | low | Some ML-set items are labelled 'recorded decision' or sit in user rows without an ML-set label; one plan edit after approval carries no note | fixed in the docs | ML-set items relabelled; the post-approval plan edit noted |
| 1 | docs-consistency | DOC-4 | confirmed | low | T1/T2 mixes draw their levels from the old prior, more than half of it from failing parts, while the plan says the re-derived prior; only a code docstring records the change | fixed in the docs | the stored prior for T1/T2 is noted in the design and plan |
| 1 | docs-consistency | DOC-5 | confirmed | low | The trusted-data ledger entry still holds the gate as first declared: 18 known amps, only the PR12 negative, no slope check, 6 renders, and no outcome after T0 ran | fixed in the docs | ledger amendment 1 and T0's outcome |
| 1 | docs-consistency | DOC-7 | confirmed | low | The three approved plans the trusted-data plan amends, and ML plan §5, carry no dated amendment | fixed in the docs | dated notes in ML plan §5, cleaning step 2, the real-mix plan, every-control 2D |
| 1 | docs-consistency | DOC-8 | confirmed | low | Status lines and dry-run figures that are out of date: the plan still says draft, and the design still says nothing has run and the cab-off negative is pending | fixed in the docs | status lines, open questions and Quicksand's reason updated |
| 1 | docs-consistency | DOC-9 | confirmed | low | Docs and code give contradictory render counts for T0's negatives | fixed in the docs | 8 renders plus 6 priming everywhere |
| 1 | ear-page | EAR-7 | confirmed | low | The 22 dead items on the pages (15 retired silent, 7 DI-only repeats) are not marked, so the user cannot listen to only the 184 live items | fixed in code | `build_ear_page check` lists the cards to skip |
| 1 | ear-page | EAR-8 | plausible | low | A sampled DI-only DI can be queued twice on the same 10-s window (di_only plus di_sample) | fixed in code | no di_sample for a DI already queued as DI-only |
| 1 | ear-page | EAR-9 | refuted | low | An item answered 'unsure' can never be asked again: `extra` skips ids already on a built part | refuted | the page lets the user change an answer; no new part needed |
| 1 | strategy | S-10 | plausible | low | The calibration-fix slope line sits inside the real-target range, and the known-amp margin is inflated by how the known amps were chosen | later | before new bands are measured: send slope fails near the line to the ear |
| 1 | strategy | S-11 | confirmed | low | The ledger's pre-registered calibration gate is stale after the #282 change | fixed in the docs | as DOC-5 |
| 1 | strategy | S-3 | refuted | low | A6 reads only the most lenient stored bleed estimate; 3 V-real parts show another guitar above −30 dB on the audit's other two estimates | refuted | the other two bleed estimates are null penalty and the target's own proxy mics |
| 1 | strategy | S-5 | confirmed | low | D4 passes admit DIs with no ear, on a population D4 was never calibrated on, and a sampled miss changes nothing | user decision | queue the D4-passed DIs no one has heard (about 1 min)? |
| 1 | strategy | S-7 | plausible | low | Queue items on DIs of bands outside K serve no planned step | fixed in the docs | told to the user: those items can come last |
| 1 | strategy | S-9 | confirmed | low | The re-derived level prior cuts the buried-guitar tail by 7 dB for T3, and parts the ear rejects still shape it | later | before T3: keep or cut the old prior's lower tail, and why |
| 1 | trusted-data | TD-11 | plausible | low | The 5k pilot can become impossible after the ear, with no fallback declared | later | plan prints the candidates by band; what to do under 5k is for before T2 |
| 1 | trusted-data | TD-4 | plausible | low | A self-built backing with no stems and no other guitars is accepted, so the SYN mix is the target alone | fixed in code | an empty backing is refused at build; plan counts them |
| 1 | trusted-data | TD-7 | refuted | low | T2's self-built mixes draw ratios from the old level prior, not the re-derived trusted one the approved plan names | refuted | the plan's T1/T2 rows require the stored draws; now noted in the design and plan |
| 1 | trusted-data | TD-8 | confirmed | low | T1's V-real reading includes pending, unverified parts and compares a LUFS ratio with an energy ratio | fixed in code | V-real's anchor: verified parts only, LUFS on both sides |
| 1 | trusted-data | TD-9 | confirmed | low | E on K has no one-band fallback (the T1 fix was not carried to e-on-k) | fixed in code | E on K gets the one-band section-clustered fallback |
| 1 | verify-tracks | VT-10 | confirmed | low | calibration_ok keys only on thresholds(), so an OK record made before the fresh negatives were declared still lets `targets` run | fixed in code | an OK calibration counts only under today's negatives and known amps |
| 1 | verify-tracks | VT-3 | confirmed | low | A clean answer on one flagged window clears an overlapping flagged window that was never heard and drops it from the queue | fixed in code | a clean answer clears only a section it covers whole |
| 1 | verify-tracks | VT-6 | confirmed | low | The one-per-band D4-passed sample is drawn before exclusions, so a band can end up with no DI heard | fixed in code | the sample redraws within the band past a measured exclusion |
| 1 | verify-tracks | VT-7 | plausible | low | An 'unsure' amp answer from the target-vs-DI export blocks a later clean_amp forever, and the target is pending with no queued item | later | only if the target-vs-DI export holds 'unsure'; re-check after the import |
| 1 | verify-tracks | VT-8 | confirmed | low | The re-derived level prior counts A1/A2 'ear' as a pass and ignores the ear's negatives and the measure DI's verdict | fixed in code | the level prior leaves out parts the ear rejected |
| 1 | verify-tracks | VT-9 | plausible | low | An ear negative on a pool or other-guitar DI does not reach the crop (measure DI) that uses the same DI file; crop negatives propagate only the other way | fixed in code | a measure DI heard processed on another window excludes its target |
| 2 | approach | ML-1 | confirmed | high | The direct model has never been compared with the song-blind per-class constant on real mixes, and T2 and the real-mix test still leave it out | user decision | as ROAD-1 |
| 2 | roadmap | ROAD-1 | confirmed | high | The song-blind per-class constant has never been scored on fresh full mixes, and T2's V-real reads leave it out, though the cheaper-on-a-tie rule could pick it | user decision | score the song-blind constant on V-real (about 66 renders) |
| 2 | roadmap | ROAD-3 | confirmed | high | No test planned after T4 can decide the route: V-real is too small, the fresh-song decision test names no data, and step 7 comes after it with a pre-trusted power claim | user decision | the decision test's data and ship rule, before T4 |
| 2 | testing | TST-1 | confirmed | high | No untouched test is left for the fresh-song decision test. The product decision would rest on V-real, the same set that picks T2's winner | user decision | as ROAD-3 |
| 2 | algorithms | ALG-1 | confirmed | medium | Every-control readings use a part-weighted interval, not the band-weighted one the plan declares; the earlier review fix changed only the docs | fixed in code | every-control readings decide on the band-weighted interval |
| 2 | approach | ML-2 | confirmed | medium | The sound-gate evidence that D beats the constant rests on two bands now excluded as untrusted; on the trusted bands it is about −0.016 on 2 bands | fixed in the docs | the gate restated on trusted rows: about −0.016, 2 bands |
| 2 | approach | ML-3 | confirmed | medium | On real mixes, training on separated stems ties the no-separation recipe (D−D0 −0.006), yet T2 and T3 spend about 27k separations on separated-stem training with no no-separation arm | fixed in the docs | D − D0 −0.006 noted beside the −0.067 headline; a no-separation T2 arm is optional |
| 2 | approach | ML-4 | confirmed | medium | The '−0.017 E per doubling' curve failed when the full build ran (like for like, 20k ≈ 5k), but it is still cited and still sizes plans | fixed in the docs | the flat 5k-to-20k curve noted in the ROADMAP and results |
| 2 | approach | ML-5 | confirmed | medium | T2's stated power assumes about 10 bands where V-real has 7, and its tie rule reads the point estimate against 0.03 regardless of the interval | user decision | as S-1 (the tie rule) |
| 2 | approach | ML-7 | confirmed | medium | Arm A's coverage stage (2A) fell out of the order after GATE STOP, so the decision test would compare a full-coverage D with a core-only arm A | user decision | as ROAD-10 |
| 2 | cleaning | CLN-1 | confirmed | medium | SYN and K bring back same-part doubles that cleaning removed from SES, now with an independently drawn tone | fixed in code | a pitch-confirmed double takes the target's settings in SYN and K |
| 2 | roadmap | ROAD-10 | confirmed | medium | Arm A and Tone King have no every-control coverage step, so the decision test would compare a full-space D against a core-space arm A, and Tone King gets no route | user decision | stage 2A for arm A, or compare routes on today's space |
| 2 | roadmap | ROAD-2 | confirmed | medium | T2's primary contrast on V-real's 7 bands cannot detect a realism loss as large as D's whole margin over S, so a 'tie, pick SYN' outcome is close to guaranteed | fixed in the docs | power restated; a tie cannot rule out a loss of D's size |
| 2 | roadmap | ROAD-4 | confirmed | medium | After T0, the training pool has no clean-class DI and V-real has 2 clean bands, but the ROADMAP frames this only as an 'SYN-E' question | user decision | where clean-class training DIs come from, before T3 |
| 2 | roadmap | ROAD-5 | plausible | medium | JHNC's test-first reservation will probably yield no V-real target, because no Telefunken amp track has survived T0, while its DIs are the likely clean-class source missing from training | user decision | a zero-render quality screen of the two reserved bands, then test or train |
| 2 | roadmap | ROAD-7 | confirmed | medium | T0's by-ear stem spot-check is not in the ear queue the user is about to hear, yet T1 and T2 build mixes from those stems | user decision | as VT-5 |
| 2 | roadmap | ROAD-8 | confirmed | medium | K shrinks to 1–2 bands because the ML session keeps out Kimock and Swatkins for a reason the plan says does not apply to K; this is not listed as an open decision | user decision | Kimock and Swatkins in K (self-built clean backings) |
| 2 | testing | TST-2 | confirmed | medium | Every planned reading lacks the power to detect the effects at stake. The stated power figures predate the trusted-data shrink, and the ship rule is undefined at the most likely outcome | user decision | power restated; declare the ship rule before the decision test |
| 2 | testing | TST-3 | confirmed | medium | V-real keeps 2 of stage F's 7 clean bands, so trusted readings become crunch readings. The re-read of D - S will move from class composition alone | fixed in code | per-class rows printed beside every T2 reading |
| 2 | testing | TST-8 | confirmed | medium | T1's stated consequence contradicts the ROADMAP's order and the code: "a gap adds realism levers to T2's SYN arm", but no lever exists | fixed in code | as TD-5 |
| 2 | training | TRN-2 | confirmed | medium | K's (and R_in's) MUSDB18 exclusion rests on htdemucs's training set, but K, T2 and V-real use X-LANCE stems, and V-real applies no such rule | fixed in the docs | the K decision's MUSDB framing corrected; T2 report has a without-MUSDB row |
| 2 | algorithms | ALG-2 | confirmed | low | A step-4-style arm whose answer renders silent is scored as S instead of worst; T2 reuses this, so a broken answer can win a direction | fixed in code | T2's reading waits while any answer was refused |
| 2 | algorithms | ALG-3 | confirmed | low | Gate 1's deciding rows use a percentile band bootstrap that is 12-30% narrower than the band-clustered t interval with 6-12 bands | fixed in the docs | footnote on gate 1's bootstrap intervals |
| 2 | algorithms | ALG-4 | confirmed | low | The t table falls back to z = 1.645 above 20 df, and known_answer's table is sparse | fixed in code | the t table never falls back to z |
| 2 | approach | ML-10 | plausible | low | An untested, nearly free combination: shrink arm A's search toward D's answer instead of toward S | later | a declared blend of arm A toward D's answer, if wanted, at T2 or T4 |
| 2 | approach | ML-6 | confirmed | low | 'Power about 21%' and 'about 46%' are observed (post-hoc) power, which cannot show that a null result is under-powered | fixed in the docs | observed power noted; what the interval rules out stated |
| 2 | approach | ML-8 | plausible | low | The median-plus-pull readout was chosen on knob error only; its sound effect against the top component was never measured, yet T2 and T3 inherit it | later | before T3: compare the top component and the median readout by sound |
| 2 | approach | ML-9 | refuted | low | The direct model's planned 3-way amp head has no defined label; the self-built labels would teach 'which Morgan amp rendered this', not the amp that stage 0b valued | refuted | in training, the rendering amp is the true amp; transfer is tested like any control |
| 2 | cleaning | CLN-2 | confirmed | low | The bleed-injection test cannot support 'live-level bleed harmless': F barely beats the constant on the probe band, and the positive control barely moved it | fixed in the docs | the bleed test's 'harmless' scaled to F's own margin |
| 2 | cleaning | CLN-3 | refuted | low | The stem scan bounds each stem at -30 dB, but the cleaning rule (and so the user's clean-only decision) bounds the section's summed take | refuted | step 0's summed rule already bounds every T1/T2 example; matters before T3's new sessions |
| 2 | cleaning | CLN-4 | confirmed | low | No path turns the ear's suspected-doubles verdicts into SES exclusions, and T0's ear queue has no doubles items | later | suspected doubles step 0 kept get no ear check; decide before T2 |
| 2 | cleaning | CLN-5 | plausible | low | A DT-named partner leaves SES backings only if it passes chroma 0.70; SYN treats the name alone as a double, and the smoke shows a named double failing pitch | later | count SES examples that keep a DT-named partner (zero compute, on the Mac) |
| 2 | roadmap | ROAD-11 | plausible | low | Arm A's rebuilder C′ and step 3's D were trained on data the trusted rule excludes, and the real-mix test and T4 run them as stored | user decision | an exception for the stored C′ and step 3's D, or retrain |
| 2 | roadmap | ROAD-12 | confirmed | low | The stated lever ('better separation') has no active step, and three parked items wait on a trigger that cannot fire (one already spent) | fixed in the docs | the separation lever's status noted |
| 2 | roadmap | ROAD-13 | confirmed | low | ML plan §5, 'the file to follow', still says measures only name candidates, and still schedules step 6 and step 7 rules that predate the no-bars and trusted rules | fixed in the docs | ML plan §5 amended; steps 6-7 restated before they run |
| 2 | roadmap | ROAD-6 | confirmed | low | T0's re-read ran, but the dated notes the approved plan requires never reached the docs, so headlines the trusted rule undermines still stand | later | after the ear: paste the re-read's dated notes beside the headlines ('DIs are clean' corrected now) |
| 2 | roadmap | ROAD-9 | plausible | low | Every-control stage 1 is in the order, but nothing consumes its result, its code has no trusted-parts filter, and its gate assumes 14 bands | later | stage 1's dated amendment (panel, parts filter, what it changes) before it runs |
| 2 | testing | TST-10 | confirmed | low | Real mixes the product will face are only partly covered: doubled guitars are excluded, the guitar-as-heard row is thin, and the real-mix test's parts list is not tied to T0's V-real list | later | bind the real-mix test's parts to T0's V-real list before it runs |
| 2 | testing | TST-4 | plausible | low | T4, the decision test and T3's V-real reading have no declared primary contrast, arm variant, amp handling or ear rule, and V-real gets read four more times before they are written | user decision | declare T4 before V-real is read again |
| 2 | testing | TST-5 | plausible | low | Step 7, the only held-out test, rests on assumptions that no longer hold: stem inputs, the trusted-data rule and the double-take exclusion. Its bands and power are overstated | later | step 7's dated amendment (stem-eligible list, verification, power) before it runs |
| 2 | testing | TST-6 | confirmed | low | The MUSDB18 and new-song rows are dropped from the new V-real readouts, although 3 of V-real's 7 bands are MUSDB18 songs | fixed in code | F-song and without-MUSDB18 rows in T2's report |
| 2 | testing | TST-7 | plausible | low | Decisions rely on the judge at differences 3-10x smaller than the range the ear validated, and no ear check sits where those decisions are made | later | an ear check at the decision scale before T3 or T4 |
| 2 | testing | TST-9 | confirmed | low | T2's tie is defined on the point estimate (/point/ < 0.03), unlike the project's interval-based ties, and its 0.03 comes from a power figure for 10 bands | user decision | as S-1 |
| 2 | training | TRN-1 | plausible | low | T2 reads SYN − SES from 2-seed ensemble point estimates against a ±0.03 tie band, but nothing in the report measures the seed noise | later | before T2: store per-seed contrasts in e-on-k |
| 2 | training | TRN-3 | plausible | low | T2 fits SYN's checkpoint and pull on self-built stems, unlike step 3's precedent of fitting on realistic inputs, so SYN − SES on V-real mixes the data effect with the calibration domain | later | before T2: fit SYN's pull on SES-type stems too, beside |
| 2 | training | TRN-4 | confirmed | low | T2 keeps the 40-epoch cap at 5k with no cap-hit flag, though this recipe's best epoch often lands at the cap at 5k | fixed in code | runs near the epoch cap are flagged |
| 2 | training | TRN-5 | refuted | low | Training on MPS cannot be reproduced from its seed, and no document says so | refuted | every step keys on the checkpoint hash, not on re-running a seed |
| 2 | training | TRN-6 | confirmed | low | The ROADMAP shows V_dev beside R_in as a second D − constant reading, but it is the same examples with part C's cleaner stand-in stems | fixed in the docs | V_dev labelled as the same examples on stand-in stems |
| 2 | training | TRN-7 | plausible | low | No test covers T2's training composition, ArmData, or StemData's input path | later | tests added for refusals; composition tests for T2's training data still open |

The reviewers' full text (evidence, failure scenarios, the skeptics' reasoning) is in
[program-review-2026-10-23-findings.json.gz](program-review-2026-10-23-findings.json.gz). In it, the strategy
reviewer's ids read VT-1 to VT-11; here they are S-1 to S-11.
