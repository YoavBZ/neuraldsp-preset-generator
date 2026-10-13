# Labelling MedleyDB's DI tracks by ear: plan

Declared 2026-10-13, before any labelling page is built.

## Why

MedleyDB (set 6) never marks which raw guitar track is the DI. On development data, no
automatic rule could tell a DI from a second microphone ([declaration](validation-set6.md)), so
set 6 was declared unusable. By ear, a DI is easy to recognise: thin, dry, no cabinet, no room.
The user asked to label it.

## What is labelled

- **Questions:** one per MedleyDB song that has a group of two or more electric-guitar raw
  tracks proven to be the same performance by set 4's same-take test. That evidence is already
  stored, in `datasets-medleydb/_tools/pairs/`.
  - Byte-identical duplicate files are shown once.
  - Steven Clark (the tracks labelled electric bass) is left out.
- **Each question:**
  - the group's tracks as A, B, C…, in random order;
  - each a 6-s clip from one window where every track in the group plays;
  - every clip at one loudness, so level gives nothing away.
- **The answer:** which track is the DI, or "none / not sure".
- **Hidden checks:** about 6 development songs where the DI is known (from
  `validation-set6-di-calibration.json`'s development pairs), built the same way and mixed in.
- **The answer key** is hashed, and the hash committed, before the page is sent.

## How the labels are used (declared now)

1. **The labels are used only if the user gets at least 5 of 6 hidden checks right.** Otherwise
   set 6 stays unusable.
2. **A song counts only when its labelled DI forms a same-take pair with at least one other
   track in the group,** under the stored set-4 test. The amp reference is chosen by set 5's
   preference order. "None / not sure" excludes the song.
3. **Gain class:** the set-3 classifier on (amp track, labelled DI), as for sets 4 and 5.
4. **Then set 6 is re-declared:** parts, crop rule 2 with mix crops, the MUSDB18 marks and the
   guard. Separator-trained-on songs are marked for exclusion from stem tests.
5. **After that, the deciding test's power is recomputed** with set 5 plus set 6.

## Hygiene

- The user hears raw guitar tracks only, to identify their role.
- No preset renders, no tone comparison, no judge or measure on set-6 audio.
- Labelling a track's role is data curation, not a test of any method. Set 6 stays fresh.
- An independent reviewer checks the page and the key before it is sent.

## Amendment: the page as built (2026-10-13, before it is sent)

The page was reviewed (`tmp/di-labelling-review.md`, local). The page and key are unchanged;
key `78e1fabc…` and page `f0317cae…` are committed in `set6-di-labelling-key.sha256`. The page
differs from the text above as follows:

1. **One question per same-take group, not per song.**
   - That gives 68 groups from 36 songs, plus 6 hidden checks: 74 questions.
   - Rule 2 now holds automatically: every track shown has a same-take partner in its group.
2. **Same take means the stored waveform test only,** as set 6 declares. The 89 envelope-only
   pairs are left out, so some groups may have no DI; "none" is then the right answer.
3. **Copies with identical audio are shown once,** and a label applies to every copy.
4. **Two groups were split,** because their tracks never all play at once: Dead Milkmen (two
   questions) and Trevor and the Soundwaves (two questions).
   - A DI label in one half is judged against the whole original group.
   - If both halves get a DI label, the group is flagged and left out.
5. **The window:** every track plays in at least 75% of the 6-s frames. Song windows reach at
   least 0.80, and the checks reach 1.0.
6. **Shuffling:** question order and letters are shuffled from a seed stored in the key.
7. **The hidden checks are development parts,** one per band: 3 clean, 2 crunch and 1
   high-gain, with a fixed seed.
8. **The clips** are 48 kHz mono AAC at 128 kbps, all at −27.1 LUFS. The level dropped from
   −20 to keep every clip under a −1 dBTP peak.

## Result of the first round, and a validation round (2026-10-13)

**The first round:**
- **What the user did:** labelled only the groups they trusted — 8 answers, the rest "not sure":
  29B 49A 51A 53A 55B 61C 64B 68B, with every other question "none". Stored in
  `listening/di-labelling/answers-2026-10-13.txt`.
- **Hidden checks:** 1 of 6 right (the single check answered, Q55). The other 5 were left as
  "not sure".
- **By the declared rule (at least 5 of 6), the labels are not usable.**
- **The user's report:** most groups seem to have no DI, and clean DIs are hard to tell.
  Crunch DIs are easy.

**The validation round,** declared before the page is built. The rule is not relaxed after the
fact; instead, the user's confident calls get their own check.

- **The page:** about 14 hidden questions from development songs only, none of them the six
  checks already used, answered the same way ("only when sure", otherwise "none").
  - **10 crunch or driven:** a known DI among 1–3 amp tracks of the same part.
  - **4 decoys:** groups of amp or microphone tracks only, with no DI. The correct answer is
    "none".
  - Clips are built exactly as in the first round: 6 s, one loudness, shuffled, with the key
    hashed and committed before the page is sent.
- **The rule:**
  - at least 8 confident answers (a letter, not "none");
  - at least 90% of confident answers correct;
  - a confident letter on a decoy counts as wrong.
- **If it passes,** the user's confident first-round MedleyDB labels count, but only for groups
  whose gain class (the set-3 classifier on amp track against labelled DI) is crunch or
  high-gain, the conditions the validation covered. Clean labels stay unused.
- **If it fails,** set 6 stays unusable.

## Amendment: the validation page as built (2026-10-13, before it is sent)

Built by `learn/build_di_labelling.py build-validation`. Key `21d47a65…` and page `cb9a4426…`
are committed in `set6-di-labelling-validation-key.sha256`.

- **14 questions:** 10 with a known DI (6 crunch, 4 high-gain) and 4 decoys.
  - Every question has two clips: the DI and one amp track. No crunch part outside the
    first round's bands has two same-take amp tracks.
  - The decoys are two amp or microphone tracks of one part (Amp1/Amp2, Mic1/Mic2,
    M80/TF51, two M81s). Each part reads crunch or high-gain on at least one of its
    DI → amp pairs, so the decoys sound like the questions.
- **The draw** uses a fixed seed. Decoys are drawn first, then questions by class.
  - Each draw takes a new band first, then a second part of a band it already took.
  - None of the first round's checks or bands is used. Question and decoy bands do not
    overlap. Two bands appear twice (MR1003 and Szymon Skiba, two crunch parts each).
- **Clips** are built as in round 1, at −22.4 LUFS.
- **Scoring the first round, if the validation passes:** the amp reference is the DI's
  same-take partner with the smallest lag, then the higher peak-to-sidelobe ratio (set 6's
  rule 4). MedleyDB names no amp or microphone, so set 5's name order cannot apply. The
  class is set 3's classifier on whole tracks, as sets 4 and 5. The result goes to
  `listening/di-labelling/validation-result.json`.
- **Rebuilt before sending, after review:** Starnes And Shah ElecGtr5 was replaced by Szymon Skiba ElecGtr3 (crunch). Its "amp" track had no speaker in it: flat against the DI, with 0.89 coherence at 3–6 kHz. A guard now requires every amp track's DI → amp coherence over 3–6 kHz to be below 0.3, on the whole tracks (frames where both play, aligned for lag and polarity). Further parts of a band are drawn starting with the band that has the fewest so far. The intro now says "two clips". The first build (key `34c30b32…`) was never sent.
