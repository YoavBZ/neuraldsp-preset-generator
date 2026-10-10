# From a song, not an amp track: results (development)

Run 2026-10-10 as declared in [songs-check-plan.md](songs-check-plan.md).
- **Timing:** plan 19:19:51, harness and preparation 19:21:45, renders from 19:21:48.
- **Review:** an independent reviewer re-derived every figure, recomputed 24 distances
  from audio and the rebuilt DIs, and found no leakage (`tmp/songs-check-review.md`,
  local).

**Declared decision: product step.** The stem chooser beats the product's starting
preset and keeps 75% of the amp-track chooser's gain.

## A correction to the scoring

The first scoring judged the stem chooser's renders against the isolated amp track.
Only its DI came from the stem. A product given only a song can judge only against the
stem, as the earlier stem studies did.
- **The fix:** the review caught it, and the stem kind is now judged against the stem
  itself (`learn/songs_check.py`), with no new renders.
- **What changed:** the figures below are the corrected ones; the decision is unchanged.
  The first scoring is kept as `distances-v1-ampref.json`. It read −0.142 for the stem
  and "stem ≈ amp" (+0.010), which overstated the stem.

## Numbers (clean and crunch parts: 24 parts, 14 bands)

The mean log ratio against the product's starting preset (the clean template on clean
parts, the shipped driven preset on crunch), with the band-clustered 90% interval:

| | mean | 90% interval | W / T / L |
|---|---|---|---|
| oracle (true DI) | −0.202 | −0.251 to −0.153 | 66 / 2 / 4 |
| chooser from the amp track | −0.152 | −0.191 to −0.114 | 60 / 1 / 11 |
| **chooser from the separated stem, judged against the stem** | **−0.114** | **−0.161 to −0.067** | 57 / 0 / 15 |
| stem minus amp (paired) | +0.038 | +0.014 to +0.063 | 17 / 11 / 44 |

- **The rule's two conditions:** the stem's interval lies below 0, and it keeps 75% of
  the amp gain (at least 50% required). Both are met.
- **By stratum:** clean −0.105, crunch −0.147. On crunch, the stem costs +0.075 against
  the amp track.
- **Robustness:** with any one band left out, the stem result stays between −0.133 and
  −0.099.
- **Low-confidence gain classes:** leaving out the 9 sets 1–2 parts with low-confidence
  classes leaves −0.114 unchanged.
- **High-gain** (report only): no edge, as in the confirmation.

## Limits

- **One part drops out:** 24 parts count, not 25. telefunken-Honey-GTR's half B is 94%
  pauses, so its baseline measure is refused.
- **Sets 1–2 used per-fold networks:** they were rebuilt by the K3 fold networks, trained
  on PR12 renders only, to avoid leakage. Their "amp" row is not the confirmed
  set-3 network. Stem against amp stays fair, since the same network rebuilds both.
- **The stems are optimistic:**
  - htdemucs_6s on a 30-s context of the session's instrumental mix, so other guitars
    are included but vocals removed;
  - parts were kept only where the stem reached 1 dB SNR against the part's own amp
    track, which a product can't check;
  - 7 of the 20 sets 1–2 parts come from single-guitar mixes.
- **Development data, not blind:** these stem parts were scored in earlier stem work.
  Clean dominates (57 of 72 cells), and crunch is 5 parts in 5 bands.

## What follows

- **The stem path works,** at about three-quarters of the amp-track gain.
- **But the [clean-baseline result](clean-baseline-results.md) changes the product
  question.** On clean parts a fixed clean preset already captures the chooser's edge,
  so its remaining value is on crunch songs, where it isn't confirmed. Whether to
  build the chooser into `generate` is the user's decision. It needs a separator, the
  network and about 111 renders per song.
