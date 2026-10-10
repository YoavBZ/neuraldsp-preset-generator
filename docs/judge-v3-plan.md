# Judge v3: a floor from both sides, in hearing's units: plan

Declared 2026-10-10, before any development comparison is scored with it. It follows
the [judge specification](judge-spec.md) and the masking-floor artefact in
[judge v2's results](judge-v2-results.md). It is an option beside the current judge
(`analysis.aligned.JUDGE_V3`), adopted only if the user's listening calibration agrees.

## Why

The specification has 17 properties. The current judge breaks five and v2 three:

- **Both clamp cuts and count boosts.** Their floor comes from the recording alone, so a
  render darker than the recording is forgiven and a brighter one is penalised (6).
- **Both depend on band width** (13). The mel filters aren't normalised, so a wide treble
  band reads up to 13 dB louder than a narrow low one of the same density.
- **The current judge alone** is deaf to treble and fizz on dark and bass-heavy parts (8,
  11), and it judges missing content by a different rule from excess (12).
- **v2 is still deaf on Ill Fate's recording** (11). It scores every band, but its floor,
  40 dB under the fundamental, clamps everything above about 700 Hz.

## The change

`JUDGE_V3 = {"bands": "fixed", "floor": "symmetric"}`. Alignment, frames, refusals, the
level steps and the per-cell |ΔdB| are as in the current judge. What changes:

1. **Bands:** the same 55 mel bands for every part and candidate, 80 Hz to 10 kHz (as in v2).
2. **Levels for the floor are per Bark.** Each band's power is divided by its filter's
   area and multiplied by the critical bandwidth at its centre. No level then depends on
   how wide a filter is, and the floor is in the units hearing integrates.
   - The differences are unchanged: both sides get the same per-band constant.
3. **One floor for both sides, per cell:** the highest of three levels.
   - **Masking:** 40 dB (the validated `mask_db`) under the louder of recording and
     level-matched render, spread over frequency at 10 dB per Bark upwards and 25
     downwards. These are the slopes of Schroeder et al. (1979), as used by the MPEG
     psychoacoustic models. So a loud fundamental no longer floors the treble.
   - **The threshold in quiet** (Terhardt 1979), placed as if the loudest cell played at
     90 dB SPL.
   - **The louder side's background:** in each band, the median level over the quietest
     tenth of the scored frames. So hiss is compared only where it rises above the
     other side's.
4. **The level** is the median difference over the playing cells that both sides hold
   above their own floors.

Swapping recording and render gives the same distance, to float precision.

## How it was designed

Designed on the synthetic checks only. No development comparison was scored with it; the
stored-render checks for v3 run after this commit. Steps tried and dropped, all on
synthetic signals:

- **Per-Hz area normalisation** (as first proposed). In per-Hz units the treble sits 10–20
  dB lower than hearing integrates it. A threshold 70–90 dB under the loudest cell then
  clamps the treble of a bass-heavy part in note decays: a ±12 dB shelf there costs
  1.36× more one way than the other.
- **A threshold 70 dB under the loudest cell** instead of the threshold in quiet, in
  Bark units. Same problem: 1.43×.
- **No background term.** The local floor then hears the recording's hiss in note decays
  and pauses. Matching −35 dB hiss brought a render 1.7 closer (spec property 16
  failed).
  - A background at the 10th percentile, or at the 90th percentile of the quietest
    frames, was also tried. The second makes a louder echo look cheaper than a quieter
    one (property 9), because the echo raises the render's own background.
- **The spec's region checks (6 and 13) were amended before this plan,** after the first
  v3 run. A 5-band region at 450–700 Hz is too narrow for the analysis windows to resolve
  a 37 dB dip: window leakage fills it, whatever the judge. The checks now use 10-band
  regions (835–1774 Hz against 5.1–8.7 kHz), 25 dB down, in gated rather than decaying
  noise. The current judge and v2 still fail them.

## Where it stands against the specification (synthetic)

- **It holds all 16 synthetic properties.** The current judge holds 11; v2 holds 14.
- **Its default path is unchanged.** 648 stored distances (current judge, v2, `union`
  and `hearing`, on 9 development parts) recompute bit for bit.
- **It runs about 1.3× slower.**

## Known limits, declared now

- **Hiss.** A render without the recording's hiss pays a near-constant cost for it, and
  a render with matching hiss is slightly rewarded. On synthetic signals, with −50 dB of
  hiss on the recording:
  - the render without hiss scores 0.71 (the current judge: 0.07);
  - adding matching hiss brings it 0.13 closer (the current judge: 0.02 further).

  A near-constant offset compresses the log ratios between candidates. Real plugin
  renders carry little hiss.
- **Renders much darker than the recording.** Noise and missing treble still look alike.
- **No listening evidence yet.** Masking is a model, and 40 dB stays conservative
  against masking data, which puts noise maskers 5–25 dB down.

## What is run, and reported

1. **The stored-render checks** (`tests/test_judge_spec_data.py`) with v3: Ill Fate's
   treble, half agreement over the 99 menus, and reproduction of the stored v3 file.
2. **The re-score:** `learn/rescore.py score --judges v3 --tag v3` (all three kinds:
   `measfix`, `net`, `lp3k`), then `report --tag v3 --judges v3`. It is reported beside
   the current judge (`flat`), with v2 for reference, on the standing comparisons:
   - the 3 kHz cut against the uncut rebuilt DI, and each against the leave-band-out
     fixed preset;
   - the oracle against that fixed preset and against the uncut rebuilt DI;
   - the fixed preset against the clean template;
   - each with its tonal and temporal parts.
3. **How many picks change** between the current judge and v3, per chooser (of 198
   part × amp × direction cells), and between v2 and v3.
4. **Ill Fate 1's winner:** its treble (2.5–10 kHz against 200 Hz–2 kHz, on unfloored
   spectra) relative to the recording, under each judge.

## Adoption

Nothing here adopts v3. It is reported, and adoption waits for the user's listening
calibration, as for v2. Once its stored-render checks pass, v3 replaces v2 as the
candidate judge, because it holds the properties v2 breaks. If a stored-render check
fails, that is reported and v3 is not a candidate until it is fixed.

## Amendment (2026-10-10, after the first stored-render check, before any re-scoring)

**What was seen.** Ill Fate's treble check passed, but only because the balanced part it
compares against had gone near-deaf. On The Well 1 (dense high gain), a +3 dB octave at
1.6 kHz applied to the recording cost 0.23 under v3, against 0.88 under the current
judge; a +12 dB shelf above 5 kHz cost 0.17, against 1.98.

**The cause** was the background term: the median over the quietest tenth of the scored
frames. On a dense, compressed part those frames are guitar, so the "background" sat at
the guitar's own level. Taken from the louder side, it rose with a boost and clamped the
whole band.

**The fix.** The background is now each band's 10th percentile over the frames where the
DI rests, under which tails have faded. Where the DI rests in fewer than 8 frames, there
is no background term. The rest of the design is unchanged. A re-score started before
this was seen was stopped before it finished. Nothing was written and no comparison was
read.

**After the fix:**
- The Well 1 costs 0.83 and 3.82; Ill Fate 1 costs 0.82 and 3.44. All 16 synthetic
  properties still hold, and the default path still recomputes bit for bit.
- A new stored-render check, added to the specification as property 18, would have
  caught it. On every development recording, a +3 dB octave at 1.6 kHz costs at least
  0.4, and ±12 dB above 5 kHz costs alike (median ratio at most 1.2).
- Under that check, over the 33 recordings, v3 gives at least 0.57 (median 0.83), with
  a median ±12 dB ratio of 1.00 (worst 1.90). The current judge gives 0.000 on the three
  Ill Fate parts. v2 has a median ratio of 1.54 (worst 15.7): its darkness artefact,
  measured directly.
- Hiss on the synthetic signals: with −50 dB of hiss on a dark recording, a render
  without it scores 1.46 (the current judge: 0.07), and matching hiss brings it 0.48
  closer. With tails, against the recording's −35 dB hiss, matching it brings v3 0.23
  closer and the current judge 3.32 closer.

