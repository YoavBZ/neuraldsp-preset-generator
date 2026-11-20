# The family check and the class check (plan, declared 2026-11-20)

**Status:** declared 2026-11-20, before any run, on the user's approval of the same day. **Run 2026-11-20 and
audited:** the family check reads GF-thin (parking Direction 2 recommended, the user's call) and the class check
CK-stop (class stays with research); see [the results](family-class-checks-results.md) (ledger
`phase_family_check_outcome`, `phase_class_check_outcome`). These are parts A and B of the orchestrator's
three-measurement plan after the strategic review of 2026-11-19 (sections 4 to 6), with that plan's independent review
taken in (approve with changes; section C below lists each change). Part C of that plan, the note-matched replay, has
its own declaration.

Every number is by the score or in knob space as stated. **Knob-space reads are descriptive until a render read
confirms them.** The user's rule (2026-11-19): no action rests on a J0 gap under 0.05. `PF` is
`~/ndsp-presets/learn/trusted-data/pipeline-fix`.

| | Ledger | Code and tests | Output | Cost |
|---|---|---|---|---|
| A. The family check | `pipeline-fix` `phase_family_check` | `learn/gear_family.py`, `tests/test_gear_family.py` | `PF/family/` | CPU, about a minute (the smoke run took 3 s with 20 of the 2,000 shuffles) |
| B. The class check | `preset-ladder` `phase_class_check` | `learn/class_check.py`, `tests/test_class_check.py` | `PF/ladder/class/` | CPU, under a minute (the smoke run took 6 s) |

Both read stored files only. They render nothing, and neither waits for the other or for the replay.

**Names.** The orchestrator's plan calls the outcome tables D2_TABLE and D3_TABLE. This ledger already uses
"D2-hum", "D2-rejected" and "D3-passing" for unrelated things, so the codes here are **GF-go, GF-stop, GF-thin**
(the family check) and **CK-reads, CK-stop, CK-between** (the class check).

---

## A. The family check: does the named gear predict the label? (Direction 2, step 1)

### A.1 The question and the goal check

Within one plugin amp, does a capture's gear family, read from its pack's name alone, place its label nearer than the
fixed centre Cen does? If not, a table from gear to settings cannot beat Cen, and Direction 2 ends.

It changes nothing in the product. It decides whether research's gear names are worth turning into measured starting
presets. It converges: one tagging, one read, one cell. **Only step 1 is declared.** The render read (step 2: family
centre against Cen through the true DIs, at most 133 records × 2 centres × 2 renders, about 530 renders, about 8 min at
the ladder's 12,480 in 3 h 4 min) runs only on the user's yes. It gets its own declaration first.

### A.2 Units

- Labels exist for 152 capture records in C2r: 121 of the first TONE3000 batch and 31 of the second. The third
  batch's 44 have none. The review's 241 counted captures, not labelled records.
- **Trusted: 133 records,** C3r's training rows (121 first-batch and 12 second-batch). The other 19 second-batch
  records are outside the DI scope. The code refuses any other count.
- A record is one capture searched on one plugin amp. The 133 come from 60 captures in 41 packs by 27 creators, and
  each pack has one creator.
- GOAT, BKS and the panel carry no gear names. Their labels enter only through Cen.

### A.3 How it differs from what failed

- **The reader** reads the waveform. Here the rig is read from text.
- **Research as it is** sets values by judgement. Here research would only name the gear, and the settings would come
  from search labels.
- **F36 and the rig lookup** used the same rig's other recordings. A family is other rigs with the same maker's
  badge: a much weaker tie, and untested.

**Why it may fail.** A capture's label follows its maker's cab, mic and gain setting as much as the badge, and the
data are thin.

### A.4 The tagging rule (`FAMILY_RULE`)

The code lower-cases the pack slug, and the first row with a token in it wins. No judgement call is made.

| Order | Family | Tokens |
|---|---|---|
| 1 | tweed | `tweed`, `5e3`, `5d3` |
| 2 | fender | `fender`, `princeton`, `vibroverb`, `bandmaster`, `twin-reverb` |
| 3 | vox | `vox`, `ac30`, `ac15` |
| 4 | marshall | `marshall`, `jtm`, `jmp`, `1987x`, `2555` |
| 5 | hiwatt | `hiwatt` |
| 6 | orange | `orange` |
| 7 | two-rock | `two-rock`, `tworock` |
| — | none | everything else |

A maker is a family when at least two packs by different creators carry its token. The counts come from names only,
and the code refuses any others:

| Family | Packs | Creators | Captures | Records |
|---|---|---|---|---|
| fender | 8 | 8 | 12 | 25 |
| marshall | 6 | 5 | 9 | 18 |
| vox | 5 | 5 | 6 | 9 |
| hiwatt | 3 | 3 | 4 | 12 |
| tweed | 2 | 2 | 4 | 11 |
| two-rock | 2 | 2 | 3 | 9 |
| orange | 2 | 2 | 3 | 6 |
| none | 13 | 11 | 19 | 43 |

**The tags are fixed now.** `gear_family tags` writes `PF/family/tags.json` once, and only if its content hash is
the declared `TAGS_SHA256` (`2a64b6a1…5fc5a64931f`, in the code and the ledger). The read refuses on any other file.

**One oddity, kept by the rule** (from the review): the pack `prototype-amp-hiwatt-sovtek-sound-city` is tagged
hiwatt. The read without it is reported beside.

### A.5 The read

**Held out by creator.** For each record r (plugin amp a, class k, creator c, family f), every record of c is left
out of both centres. A creator's packs share cab and mic habits, and one creator alone has 5 packs in 3 families, so
leaving out only the pack would let "family" pass through the creator.

**Cen₋c.** Cen rebuilt with `preset_ladder.centre_of` over every C3r training showing of (a, k), counted as the
stored all-labels Cen counts them, less every record of c. It is written through `full_space.answer_settings` and
C3r's hold, as the stored Cen is. **Control:** rebuilt with nobody left out, it must equal `ladder/centres.json`'s
cen exactly in all six cells (it does at declaration).

**The family centre.**
- O is the mean over f's records on amp a from creators other than c, both classes. Each record contributes its label
  less the Cen₋c of its own class, head by head, over its labelled heads (C3's training mask) that sound.
- n_h is the number of such values on head h.
- **Fam = Cen₋c(a, k) + w·O, with w = n_h / (n_h + 2)**, clipped to the unit range. The other heads, and every
  switch and mic, stay at Cen₋c.
- With the shrink, a family centre beats Cen in expectation only when families hold more than 1 / (n + 5) of the
  residual label variance. With the plain mean the bar is 1 / (n + 1).

**Usable records.** A record is usable when its family is not "none" and it has at least one other-creator record of
its family on its amp. The others are left out and counted, split into "no family" and "n = 0". The record set of
every row is fixed by that rule.

**"Nearer", defined.**
- **d_g** is the RMS gap to the record's own label in `full_space` unit space. It is taken over the continuous heads of
  knob group g (`preset_ladder.knob_group`: drive, tone, cab, eq, pedals) that are labelled in the label and sound in
  both centres.
- **D_g = d_g(Fam) − d_g(Cen₋c)** per record. Below zero is nearer.
- **T_g** is D_g's mean over creators (records averaged inside a creator), with its 90% t interval
  (creators − 1 df).
- **The family-clustered interval:** D_g's mean over families (records averaged inside a family; families − 1 df).
  Its mean differs from the creator mean. It is reported beside, and GF-stop takes **the lower of the two lower ends**
  (`wider`; the review: the creator interval ignores family-level dependence).
- **Cen's distance** for GF-stop is the creator-weighted mean of d_g(Cen₋c) over the same records.

**The shuffle control** (fixed in full before the run):
- **What is permuted:** the tags of all 41 packs, the 13 "none" packs included, over the 41 packs. It is seeded: 2,000
  permutations, permutation j drawn from `random.Random("20261206:j")` over the sorted pack list.
- **The record set** is fixed to the real read's usable records. Under a permutation, a record whose new family is
  "none", or has no other-creator record on its amp, has Fam = Cen₋c, so D_g = 0. It stays in T_g. (The real read
  has no such rows, so the shuffle is not exactly exchangeable with it. This is the specification the review asked
  for, and the write-up notes it.)
- **The joint statistic:** for each of drive, tone and cab, z_g = (T_g − the shuffles' mean of T_g) / the shuffles' sd
  of T_g. The statistic is the minimum z over the three. **p** is the share of the 2,000 shuffles whose own statistic
  (standardised by the same means and sds) is at or below the real one. A group with no real T or no spread across
  shuffles is left out of the minimum.

**Beside, descriptive.** None of these enters the cell.
- The plain mean (w = 1), and the same-class-only centre.
- The read without the prototype pack.
- **Leave one family out:** T_g with each family's records left out in turn, and its range.
- **The like-for-like row with the reader:**
  - the stored fold Cen (`answers/cen.json`), and a family centre that leaves out what the reader's fold models leave
    out (fold k and every record sharing an identity with a fold-k unit);
  - the reader's answers on the same records, both halves averaged, for `clean-kind` (the capture alone) and
    `rc-xl@-3` (the product's stem), each as d_g(answer) − d_g(fold Cen);
  - the family centre less the reader, paired.
- **Switches and mics:** the share of labelled values where Cen₋c differs from the label, and where the family's
  majority (other creators, same amp, both classes; a tie goes to Cen₋c) differs.
- **The share of label variance the families hold:** per group, the mean over heads of the one-way ICC(1) of the
  residuals against Cen₋c across families (tagged records). Beside it, how many other-creator records a family centre
  would need for an expected 10% smaller RMS distance at that share (`captures_needed`; none below a share of 0.19).

### A.6 The outcome table (`GF_TABLE`)

Three readings:
- **nearer:** on drive, tone or cab, the creator-clustered interval of T_g is wholly below 0;
- **ruled out:** on each of drive, tone and cab, the lower of the two intervals' lower ends (creator- and
  family-clustered) is above −0.1 × Cen's distance;
- **p small:** the joint shuffle p is under 0.05.

| Code | When | Next |
|---|---|---|
| GF-go | nearer and p small | To the user, with the render read's declaration. Nothing renders before the user's yes |
| GF-stop | ruled out and not p small | The badge does not predict the label. Direction 2 ends |
| GF-thin | the rest (4 of the 8 combinations) | **Underpowered, not failed.** The write-up gives each group's interval, the families' variance share and the captures a family would need. To the user: the render read (about 8 min, **not run without a yes**), fetch more named captures per family (each about 255 renders of label search, F77), or park |

- **Power.** About 86 usable records in about 20 creators, with a median of three records behind each family
  centre. GF-thin is the likeliest cell unless the families are strong. The check runs anyway, since it costs only CPU
  seconds (the orchestrator's ruling).
- **False alarm:** GF-go needs the joint shuffle p under 0.05, so it fires at most 5% of the time under no family
  effect.
- The tenth in GF-stop is a declared convention. No knob distance is calibrated to the ear. The render read is what
  calibrates.

### A.7 Refusals

- The ledger phase must be declared.
- The records must be exactly C3r's 133 trusted capture rows, the family counts the table's, and tags.json the
  declared hash.
- The rebuilt Cen must equal the stored Cen.
- The ladder's capture parts must be the same 133 records.
- The stored fold Cen must be one setting per (fold, amp, class).
- Neither output is ever overwritten.

---

## B. The class check: is clean or crunch readable from the stem? (Direction 3, test 1)

### B.1 The question and the goal check

From the ladder's stored inputs, does a simple classifier name a held-out unit's class (clean or crunch, the label's
class from C2 and C2r) clearly better than 0.80, research's point figure on the exam?

A wrong class cost +0.405 and +0.136 on the exam (`docs/real-song-exam-results.md`). A pass opens one follow-up,
itself to be declared: let audio overrule research's class on the exam's stored renders. A stop leaves class with
research. One fit rule, one read, one cell. The exam's V-real parts are not used.

### B.2 Inputs, and the leak

- **Stored:** mel spectrograms (96 bands × 446 frames a half, uint8 at 0.5 dB steps) for every ladder unit and input
  row. The rows used are `clean-kind`, `xlnoG@-3`, `xl@-3` and `mixp@-3`.
- **Units: 398.**
  - **G, 348:** GOAT 215, first-batch captures 121, second-batch 12.
  - **R, 50:** BKS 40 and the panel 10 (Silent Waves's 2 units are out for vocal bleed).
- **The leak.** Each unit's lender was drawn from its own class's sections, and 384 of the 398 units have a lender
  band on their own class's side. A band's side is the class it supplies more examples to (`lends.json`
  `pool_by_band`). The other 14 units are the **off-side lender units**: 9 first-batch captures, 4 GOAT and 1 BKS.
- **The leak also reaches test time** (the review, blocking). The guitar-alone stem `xlnoG@-3` has no other guitar,
  but it still carries the lender band's backing as bleed, and that band matches the class. A level-free spectral
  classifier trained on the amp track alone could be pushed toward the right class by that bleed. The leak therefore
  can produce a pass. The guard is in B.6: T-alone may not read more than 0.02 above T-clean, the same classifier on
  the clean amp track.
- **Class is constant inside a real-amp cluster.** BKS's 8 DI files are 4 clean and 4 crunch. The panel's bands are
  Aimee Norwich (clean), Big Troubles (crunch), Jen Hartswick & Nick Cassarino (Drowning only: clean) and The Laminar
  Flow (crunch). So R is **12 clusters** (6 and 6), or **11 without Drowning** (5 clean and 6 crunch).
- **Drowning** enters only on a bleed check recorded before the run (the replay's, plan C.9). None is recorded when
  this is declared, so **the deciding read is the 11 clusters without Drowning.** The 12-cluster read is reported
  beside and never changes the cell.

### B.3 How it differs from what failed

- **The reader's drive heads** read −0.04 to −0.21, and a drive index read +0.09 to +0.10 from October's dense stems
  (`docs/ml-deep-review-2026-11.md`, section 4). Those asked for a continuous amount. This asks one coarse choice
  whose error has a heard-size cost.
- **Research** names the class from text and was right on 8 of 10 exam parts.
- It trains on real amp recordings and captures, not plugin renders.

**Why it may fail.** A classifier trained on the guitar alone may not carry to separated stems. Three GOAT players
supply most of G (GOAT and the first-batch captures reamp GOAT's DIs).

### B.4 Features, classifier, split (all fixed)

- **Features (`features`), level-free, from both halves averaged.** Active frames are those whose level (the
  power-mean over bands) is within 40 dB of the loudest frame, on the stored mel's dB scale.
  1. each band's mean over active frames, less the mean across bands (96);
  2. each band's standard deviation over active frames (96);
  3. spectral flatness per active frame (geometric over arithmetic mean power), its mean and sd (2);
  4. the active frame level's sd and its 5-to-95% range (2);
  5. the mean over active frames of the loudest band less the mean band (1).

  A test checks that +10 dB on every cell leaves all 197 unchanged.
- **Classifier:** scikit-learn's L2 logistic regression, C = 1, balanced class weights. Features are standardised on
  the training units only. Nothing is tuned.
- **The split.**
  - **G** is tested by C3r's four folds. Each fold's classifier is trained on G's other folds, **less every unit that
    shares an identity (DI file or creator) with a tested-fold unit**, as C3r's training bans them. C3r's folds share
    71 DI files across folds through captures reamped from GOAT's DIs, so this ban is not empty. Re-derived at
    declaration, it removes 285 training units summed over the four folds. The report gives the count per row.
  - **R** is tested as one block by a classifier trained on all of G. **R is in no training**, neither the G folds nor
    its own. G and R share no DI file or band (checked at run).

| Row | Trained on | Tested on | Role |
|---|---|---|---|
| **T-alone** | `clean-kind` | `xlnoG@-3` | **decides**: the stem where the target is the only guitar |
| T-full | `clean-kind` | `xl@-3` | beside: the other guitars match the class by the lender draw |
| T-clean | `clean-kind` | `clean-kind` | the ceiling, the features' control and the leak guard's reference |
| T-mix | `clean-kind` | `mixp@-3` | beside: no separator |
| In-alone, In-full | the stems | the same stems | beside, open to the lender leak; In-alone guards CK-stop |

**Beside every row:**
- each G set, the R units, and the majority class's share;
- balanced accuracy;
- **the 14 off-side lender units, reported separately**, and the 384 others (a lender-keyed classifier gets the
  off-side ones wrong);
- **GOAT's 35 items that hold both classes** (70 units): the playing is held constant there, so they separate tone
  from playing style;
- **the lender-band control:** whether the lender band itself (The Travelling Band against Hazael, among clean units)
  can be named from `xlnoG@-3`, `xl@-3` and `clean-kind` by C3r's folds. (R units carry no identities, so a BKS DI
  file can sit on both sides of a fold in this control; it is beside only.)

### B.5 "Better than 8 of 10", defined honestly

- Research's 8 of 10 comes from exam parts this test does not use, and its exact 90% interval is 0.49 to 0.96. So
  "better than research" cannot be shown here as a paired fact.
- What can be shown is that the classifier's accuracy is decided above research's **point figure, 0.80**. That
  licenses only the paired read on the exam.
- **On G, on two cluster schemes** (the PR review, blocking):
  - **C3r's clusters,** 157: GOAT by item, captures by creator;
  - **DI files,** 145.

  Each scheme misses one dependence: the captures reamp GOAT's DIs, so DI files miss the shared creator and C3r's
  clusters miss the shared performance. Joining the two gives one component of 255 units, which is not usable. Each
  scheme gives the mean of cluster accuracies with its 90% t interval. **A reading needs both to agree** (`conservative`):
  "above" needs both lower ends over the bar, and "below" needs both upper ends under it. Both means and the unit
  accuracy are beside.
- **On R:** the clusters named right. A cluster is right when most of its units are, and a tie is wrong.

### B.6 The outcome table (`CK_TABLE`)

Four readings:
- **g:** T-alone on G is "above" (both schemes' lower ends over 0.80), "below" (both upper ends under 0.80) or
  "neither".
- **r:** T-alone's R clusters right, without Drowning. "Reads" at 9 of 11 or more (10 of 12 beside). "Stop" at 6 or
  fewer, which is R's majority cluster count: 6 of 11, and 6 of 12 beside.
- **leak:** "ok" when T-alone's accuracy is no more than 0.02 above T-clean's on each of G's two cluster means (C3r's
  clusters, DI files) and R's 47 deciding units (without Drowning); else "high".
- **In-alone:** "above" when In-alone on G has either scheme's lower end over 0.80 (it guards CK-stop, so either
  scheme can hold the stop back).

| Code | When | Next |
|---|---|---|
| CK-reads | g above, r reads **and** leak ok | To the user: declare the paired read on the exam's stored renders |
| CK-stop | (g below or r stop) **and** In-alone not above, and not CK-reads | A simple classifier does not name the class better than research. Class stays with research |
| CK-between | the rest, including a leak-inflated pass and a T-alone stop with In-alone above 0.80 | **Not decided.** The write-up says which side held it back. Only here is the class-blind lender redraw offered (new separations, not declared) |

- **The control first:** both of T-clean's G intervals must lie wholly above G's majority share. Otherwise the features are
  broken, and the read stops with no cell.
- **Power.**
  - On G (348 units, 157 or 145 clusters), the half-width at an accuracy near 0.9 is about ±0.03. A true 0.87 or better
    clears 0.80 about nine times in ten.
  - On R without Drowning, 9 of 11 is reached 91% of the time at a true 0.9 a cluster, 62% at 0.8 and 12% at 0.6. A
    stop (6 or fewer of 11) happens 47% of the time at 0.6 and 5% at 0.8.
  - All three conditions together are harder.
- **False alarm.** The leak guard and the off-side units are there because the test-time bleed can push a pass. A
  pass that rides on the bleed lands in CK-between, unless T-clean itself reads as high.

### B.7 What it can't say, refusals

- **It can't say** whether audio is right where research is wrong. That needs both on the same parts (the exam).
  T-alone has no other guitars, and T-full has class-matched ones. A real song sits between the two.
- **Refusals:**
  - the ledger phase must be declared;
  - the counts (G 348, R 50, 14 off-side, 35 GOAT both-class items) and R's 12 and 11 clusters must be as stated;
  - each read part's class must equal C3r's;
  - G and R must share no DI file or band, and each R cluster must hold one class;
  - every stored feature file must exist;
  - the report is never overwritten.

---

## C. The review's changes, and where each is

| Change | Where |
|---|---|
| A: the shuffle specified in full (the "none" packs, records with n = 0, the joint statistic) | A.5, `shuffle_tags`, `joint_p`, `read_family(only=…)` |
| A: leave-one-family-out beside; GF-stop on the lower of the creator- and family-clustered lower ends | A.5, A.6, `wider`, `readings` |
| A: on GF-thin, the render read offered (about 8 min), not run | A.6, `GF_TABLE` (tested) |
| A: the prototype pack read beside | A.4, A.5 |
| A: run although GF-thin is likely | A.6 |
| B (blocking): the leak can reach test time; CK-reads needs T-alone no more than 0.02 above T-clean | B.2, B.6, `leak_reading` (tested) |
| B: the 14 off-side lender units reported separately | B.4 |
| B: R is 50 units; the thresholds for 11 clusters | B.2, B.6, `R_READS`, `R_STOP` (tested) |
| B: R is in no training | B.4 |
| B: GOAT's 35 both-class items beside | B.4 |
| B: the class-blind lender redraw only on CK-between | B.6, `CK_TABLE` (tested) |
| PR review (blocking): G read on both C3r's clusters and DI files, a reading needing both | B.5, B.6, `conservative` (tested) |
| PR review (blocking): no numpy import before the refusals | `class_check.cmd_read` |
| PR review: the leak guard's R side on the 47 deciding units | B.6, `outcome` (tested) |
| PR review: `fold_wise`'s refusals before the read and the shuffles | `gear_family.fold_wise_inputs` |
| PR review: `wider`'s wording (the two means differ) | A.5, A.6 |
| PR review: every read part's class checked against C3r's | B.7, `ladder_units` |
| PR review: a test of the shuffle's D = 0 rule | `tests/test_gear_family.py` |
| PR review: the lender-band control's R units carry no identities, so a BKS DI file can sit on both sides of a fold there (beside only) | B.4 |

## D. Hand-back

Both checks run once from the merged code, with zero renders. The raw, unaudited results go to
`~/ndsp-presets/handover/2026-11-20/zero-render-handback.md`. The audit and the results doc follow. On GF-go or
GF-thin the render read is not run without the user's yes.
