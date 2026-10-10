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

## Pre-check result, and amendment (2026-10-10, before the v3b run)

**v3 fails its pre-check.**
- **Validation improved:** 62.5 at step 1,000, against the original's 65.0.
- **But dec.0's gate closed again:** 100% open at step 500, 2% at step 1,000. Its
  input is about 16 times the skip's size, with a gate pre-activation mean of −18.7.
  Normalising the bottleneck slowed the closing; it didn't stop it. As declared, no
  long run follows from v3.

**Amendment: v3b.** Add `open_bottom` (`--open-bottom`): the deepest decoder level uses
a convolution and a GELU instead of the GLU gate, so it can't gate the path off. That
gives 9.0M weights instead of 9.8M. Everything else is as in v3, including `--norm`.
- **Pre-check:** the same 15 minutes and the same two conditions. For the open bottom,
  "open" means the share of the level's GELU outputs above 1e-3 in size.
- **The run and the decision rule:** unchanged.

## v3b pre-check result (2026-10-10): fails; no long run

- **Validation:** 61.7 at step 1,000, against 65.0.
- **The open-bottom share:** 0.98 at step 500, then 0.39 at step 1,000, under the
  declared 0.5.
- **An ablation** (reported, not a declared gate): zeroing the deepest decoder level
  changes the output by 4.6% in the old network (its constant bias), 12.6% in v3, and
  0.1% in v3b.

Even when the bottom cannot be gated off, training learns to ignore it. The dead bottom
is a symptom: the shallow levels already give the loss what it rewards. Repairing the
architecture is closed as a lever. The next check asks whether the gap comes from the
network having trained only on plugin renders while being tested on real amps
([sim-to-real plan](sim-real-gap-plan.md)).
