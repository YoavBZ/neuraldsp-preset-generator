# Arm A and experiment 4 artefacts (2026-10-16)

Small files behind [arm-a-levers-results.md](../../arm-a-levers-results.md) and
[di-fine-structure-results.md](../../di-fine-structure-results.md), committed so the research
sessions can cite them.

**Experiment 4:**
- `exp4-step0c-dac-reading.json` and `exp4-step0c-dac-shift.json`: the DAC round-trip check, a
  two-point test.
- `exp4-step0e-capacity.json`: the capacity check (overfit).
- `exp4-screen-f3-original.json` and `exp4-screen-f3.json`: step 1d's screen, before and after
  amendment 1.
- `exp4-step2.json`: step 2's control readings for 1a, 1b and 1z.
- `exp4-step0c-dac-cells.json`: step 0c per cell (added 2026-10-16 for
  [local-objective-plan.md](../../local-objective-plan.md)): the margin m through the true DI, C′,
  DAC-4 and DAC-9; the quiet-frame level; the 1/5/10-ms crest; and the resample-only control.
  Built with zero renders by `exp4_step0c_dac_cells.py` from
  `~/ndsp-presets/learn/di-fine-structure/step0/`.

**`levers-audit/`:** the independent audit's scripts.
- `a7b_local.out`: experiment 2b's local fidelity per part, amp and direction.
- `a7c_dims.out`: the same split per knob.
- `r1_out.json`: the audit's 25 re-renders.
- `a1_exp1.out` … `a8_curse.out`: every other script's output, re-run on 2026-10-16 from the Mac's
  stored files with zero renders (the scripts read `~/ndsp-presets/`, so they can't be re-run from
  git). `a7_local.out` ranks refusals as the worst; `a7b_local.out`'s first block drops them.

**Actual renders for the levers:** about 5,890 in all, corrected by a code review.

| Step | Renders |
|---|---|
| Experiment 1 (warm-ups not recorded in the files, about 144) | about 1,114 |
| Experiment 2 | 1,740 |
| 2b (local) | 2,460 |
| Judging early stopping (3-C′) and the descriptive shrink-0.5 lever | 576 |

The repeat check added 18 renders and the audit 25. 3a's live search (3-W) and 3b did not run,
because experiment 2 chose C′.

**Two hard caps were exceeded,** because each shard checked its own cap:
- experiment 1: about 1,114 against 1,100;
- the 3-C′ judges: 576 against 450.

This was disclosed on 2026-10-16. The code now counts warm-ups and keeps both directions of a
part and amp in one shard.
