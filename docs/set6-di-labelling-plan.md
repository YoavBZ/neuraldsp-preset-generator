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
