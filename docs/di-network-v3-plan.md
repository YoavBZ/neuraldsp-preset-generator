# A DI-rebuilding network with a working bottom: plan (set 3, development)

Declared 2026-10-10, before any v3 training.

## Why

The [v2 pilot](di-network-v2-plan.md) review found that every DI network trained so far
has its bottom levels dead.
- **What happened:** the bottleneck adds its residual blocks with no normalisation, so
  its values grew to thousands.
- **The result:** the decoder's first GLU gate saturated shut. Its input is about
  −6,000, and its output is exactly 0.
- **What was lost:** `enc.4`, the whole dilated bottleneck (the ±0.3 s of context) and
  `dec.0`, which is 8.4M of the 9.8M weights. They get zero gradient and were
  bit-identical before and after both v2 runs.

The networks ran on their shallow levels only. That fits what was measured: neither
longer training nor more guitars moved the rebuilt DI or the picks.

**A correction to the v2 plan.** "Loss 7 on training clips but 60 on validation" does
not mean memorising. The log's validation figure is summed over 8 batches, so it is
about 7.3 per batch, and the network is not overfitting.

## The change

`build_model(norm=True)`:
- a GroupNorm before each bottleneck block;
- the blocks' last convolutions start at a tenth of their usual size.

Nothing else changes: loss, data, augmentation, target and schedule. Training logs now
report the share of dec.0's gate that is open.

## Pre-check (before the long run)

- **Run:** 15 minutes on MPS from scratch, on the set-3 network's data (the PR12 cache
  plus the SW50R and AC20 pairs, K3 fold 2 held out), learning rate 3e-4.
- **It passes if both:**
  - the gate stays open on more than half of its units at every log;
  - validation at step 1,000 is no worse than the original run's at the same step,
    65.0.
- **If it fails,** stop and report; no long run.

## The run

The set-3 network's recipe, from scratch, with `--norm`, seed 20261010:
- 60 minutes at 3e-4;
- then 300 minutes on a cosine decay to 2e-5;
- the same data, the same fold.

It never hears a set-3 guitar, so it is tested on all 33 development parts with
`learn/v2_eval.py` against the current network.

## Decision rule (declared)

Pooled over the three amps, on recording bands. **v3 helps** if, against the current
network, it reaches:
- a mean log ratio of −0.05 or lower;
- more part-amp wins than losses.

The same comparisons as in the v2 plan are reported: against the fixed driven preset,
the template and the oracle. An independent reviewer re-derives them.

- **If v3 helps:** retrain with set 3's guitars added (fold-excluded), and judge against
  the fixed preset on fresh material.
- **If not:** the working bottom isn't the lever either. Then go to stem-aware training,
  and room and mic augmentation.
