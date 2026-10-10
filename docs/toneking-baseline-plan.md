# Tone King starting presets for clean and crunch: plan

Declared 2026-10-11, before any Tone King preset is rendered for it, chosen or scored.
Reviewed (`tmp/toneking-baseline-plan-review.md`, local): approved with required changes,
all folded in below.

## Why

- **`generate` starts a Morgan part from a measured factory preset** for its gain class
  ([clean](clean-baseline-results.md), [crunch](crunch-baseline-results.md)).
- **A Tone King part starts from whatever preset the user owns,** with no evidence behind
  the choice.
- **Tone King's factory and artist presets ship with the plugin,** so every Tone King
  owner has them. A measured starting preset per gain class is the same cheap, proven
  idea, applied to the second plugin.

## The menu

- **All Tone King presets under `Factory/` and `Artists/`** in the plugin's preset
  folder (never `User/`), whose stored state is complete: 125 presets. `Default.xml` is
  rendered too, as a comparator.
- **Three are left out because their state is incomplete:** Clean Clay, Grunge Sludge and
  Lite Mud. The renderer refuses them, because the plugin would fill the missing parts
  with defaults.
- **Each is made dry first, as the Morgan baselines were measured:**
  - post reverb, delay and chorus off;
  - the amp's spring reverb at 0, its tremolo depth at 0;
  - the gate off (threshold −96 dB);
  - wah off (4 of the 6 presets with wah use it as an auto-wah, a time-varying effect);
  - the time-effects section itself on.
- **Kept:** the channel, amp, pedals, compressor, EQ, cab and levels.
  - Cab rooms are kept too, as Morgan's dry rule kept its rooms.
  - Tone King's doubler and transpose are internal slots, off and 0 in every preset.
- **This edit list becomes the product's `dry/toneking` recipe,** which the product
  session writes, if anything is adopted.

## Rendering and scoring

- **The measure, unchanged:** the take's DI, re-equalised to the pinned average and set
  to −22.9 LUFS, played through each dry preset; the `flat` judge on half A
  (1.0–5.5 s) and half B (5.5–10 s) against the recorded amp track.
- **Exact preset state, one fresh plugin process per render**
  (`ToneKingPresetRenderer`), after 1 s of silence that is cut from the output.
  - A fresh Tone King process starts muted for up to 0.87 s.
  - Each render asserts that the uncut output's leading silence ends inside the 1 s.
- **Latency:** 51 samples, measured on a bypassed preset (an impulse comes back 51
  samples later; Morgan's is 52). The judge lag is the part's measured lag minus 51.
- **Repeatability:** measured before the main run, in the units that decide.
  - 3 repeats × 2 presets × 3 development parts, as the spread of log distance.
  - Reported beside the decision gaps.
  - The first, broadband check (−38 to −58 dB between repeats) used a set-3 held-out DI.
    That was engineering only, and it informs no choice.

## The choice (development only)

- **Development parts:** the 35 pinned parts in `docs/sound-desc-test-parts.json`:
  - clean: 22 parts in 10 bands;
  - crunch: 13 parts in 6 bands.
- **The rule:** for each gain class, choose the preset (either channel) with the lowest
  median of the mean of its half-A and half-B distances. Ties are broken by name.
  - Only parts where every menu preset has both halves are used.
- **The choice JSON is committed with the ledger entry before any held-out render.** The
  code refuses held-out renders unless both are committed. It records:
  - the dry copies' hashes;
  - the code commit;
  - the runner-up and its gap;
  - the best preset per channel (Rhythm, Lead);
  - leave-band-out pick agreement.
- **Also reported on development:** a leave-band-out version against each comparator below
  (out of sample for the choice).

## The check (held-out parts, a further declared use)

- **Parts:** the held-out sets 1–2 parts used by the confirmation, the clean check and
  the crunch check:
  - clean: 13 parts, 8 bands;
  - crunch: 7 parts, 3 bands.
- **Their rule allows a further declared use;** this is the third. They are rendered
  through the whole menu.
- **Statistic:** per part, the log ratio of the chosen preset's distance to the
  comparator's, averaged over both halves. A band-clustered 90% t-interval, as before.
- **The comparator, as the Morgan checks compared with the product's real start:**
  - **Clean: `Default.xml` made dry.** It is the start every owner has, the analogue of
    Morgan's template.
  - **Crunch: the median preset of the chosen preset's own channel.** Crunch has no
    natural single start, and the same channel removes the channel mismatch.
- **Adopted for a gain class** if its interval lies below 0. Then `generate` starts a
  Tone King part of that class from that preset, made dry, **on the preset's own
  channel**: switching the channel would ship something that wasn't measured.
- **If clean isn't adopted** and the dry Default is itself close, the dry Default is a
  defensible start. That is the product session's call, and it is reported.
- **Report only:**
  - against the median over all 125;
  - for clean, against the median of the presets named "Clean";
  - against the median over presets with rooms off;
  - the chosen preset's held-out rank;
  - the oracle (the best preset per part), for headroom.
- **The Morgan starting presets of the same class**, on each amp, from the existing
  distances:
  - held-out: `confirm/distances.json`;
  - development: in-sample for Morgan.
  - This is report only, to inform which plugin suits a part.

## Power, honestly

- **Clean,** 8 bands, can decide a moderate effect. Against the dry Default it may well
  not pass, and that is the honest test.
- **Crunch,** 3 bands (Forkupines 4 of 7 parts), gives an interval with 2 degrees of
  freedom. Only a large, consistent effect passes, and "not shown" is the likely outcome.
- **Winner's curse:** 125 candidates on 22 (or 13) parts. The leave-band-out agreement
  and the runner-up gap show how stable the pick is.

## Cost and safety

- **A pilot first:** one preset on a few development parts in 6 parallel processes, to
  check the licence service and throughput.
- **Renders:**
  - development: 35 × 126 = 4,410 (with `Default.xml`);
  - held-out: 20 × 126 = 2,520;
  - about 5 s each, in 6 processes: about 1.6 hours in total.
- **The licence service is checked first and never touched.**
- **Renders are kept as FLAC** until the results are reviewed, then deleted, keeping
  only the distances.
- **Set 4 and the Internet Archive sessions stay unused.** They are the only fresh
  material left.
- **An independent reviewer** re-derives the result before adoption.
