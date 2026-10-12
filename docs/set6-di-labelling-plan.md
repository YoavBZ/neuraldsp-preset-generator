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
