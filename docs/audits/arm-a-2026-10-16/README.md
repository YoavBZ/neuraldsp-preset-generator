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

**`levers-audit/`:** the independent audit's scripts.
- `a7b_local.out`: experiment 2b's local fidelity per part, amp and direction.
- `a7c_dims.out`: the same split per knob.
- `r1_out.json`: the audit's 25 re-renders.

**Actual renders for the levers:** 5,746 in all.

| Step | Renders |
|---|---|
| Experiment 1 | 970 |
| Experiment 2 | 1,740 |
| 2b (local) | 2,460 |
| Judging early stopping (3-C′) and the descriptive shrink-0.5 lever | 576 |

The repeat check added 18 renders and the audit 25. 3a's live search (3-W) and 3b did not run,
because experiment 2 chose C′.
