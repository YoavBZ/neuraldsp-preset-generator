# A better DI-rebuilding network: pilot plan (set 3, development)

Roadmap step 0, next step 4. Declared 2026-10-10, before any training or result below.

## Why

- **The gap is in the waveform's detail.** The [gap split](set3-gap-split-plan.md)
  found that what the rebuilt DI loses is neither its level, its long-term balance nor
  the activity mask. It is the rest: the fine waveform detail.
- *(Corrected 2026-10-10: the validation figure is summed over 8 batches, about 7.3 per
  batch, so the network was not memorising. See [v3 plan](di-network-v3-plan.md).)*
- **Its training guitars are few, and clean-leaning.**
  - Sources: set 2's 13 development bands and one Guitar-TECHS player.
  - It never heard a set-3 guitar.
  - Set 3's development sessions hold 51 more DI tracks from 14 bands, mostly heavier
    playing. Their use for training was declared from the start
    (`learn.set3.training_dis`).

## Two arms, both continuing the current set-3 network

Both start from `models-set3/fold2.pt` and train 3 hours more on MPS. The learning rate
follows a cosine from 1e-4 down to 1e-5. Seed 20261010. The recipe is otherwise
unchanged: same loss, augmentation and the K3 fold-2 average-balance target.

- **B, longer:** the same data as before, the PR12 cache plus the SW50R and AC20 pairs.
- **A, more guitars:** B's data, plus new pairs rendered from set-3 development DI
  windows (`learn/render_pairs.py`, unchanged recipe, 4,000 per amp).
  - **Excluded:** windows from any band in set-3 fold 2. Death Of A Romantic, Eat The
    Feeder and Rebuild The Evil are never heard.
  - **Allowed:** set 3's unfolded bands, which every fold may use.

## Material

- **A is tested only on fold 2's 12 development parts** (3 bands), the only set-3 parts
  it never heard.
- **B never heard any set-3 guitar,** so it is tested on all 33 parts.
- **The rest is as in Phase 2 on set 3:**
  - amp tracks, three amp menus;
  - picks on half A, judged against the recording at lag −52, with the reference-proxy
    fallback (`learn/rebuilt_judge.py`);
  - scored by the average-guitar measure on half B.

## Reported

Per amp and pooled over amps, recording and union bands: the mean log ratio of each
pick's half-B distance, wins/ties/losses, and the band median of band medians with its
sign-flip p.
- A against the current network on fold 2's parts; A against B on the same parts.
- B against the current network, on all 33 parts.
- Each against the declared fixed driven preset per amp
  ([driven-baseline-results.md](driven-baseline-results.md)), and against the oracle.

## Decision rule (declared)

Pooled over the three amps, on recording bands:

- **More guitars help** if A beats the current network on fold 2's parts with:
  - a mean log ratio of −0.05 or lower;
  - more part-amp wins than losses.

  Then the next run trains all four folds that way, with 3 hours each. The extra
  guitars can then be judged on all 33 parts before any new claim.
- **Longer training helps** if B beats the current network on all 33 parts by the same
  rule. Then the next runs train longer.
- **Neither:** the waveform loss is not about data quantity or training length at this
  scale. The next candidates are:
  - stem-aware training (renders mixed into backings, then separated);
  - room and mic augmentation;
  - a larger or differently built network.

**Caveats.** A on 12 parts in 3 bands is a pilot: it routes the next run, and is not a
claim. An independent reviewer re-derives the numbers before they route anything.
There is no new confirmation material; any claim against the fixed preset needs fresh
recordings (roadmap step 0, next step 7).
