# Label table and stems: results (ML plan step 4, 2026-10-15)

Run under the [plan](label-table-plan.md). A data-building step with no gate.

- **Parts:** 59 clean and crunch development parts (out of 76 classed), listed in
  [label-table-parts.json](label-table-parts.json).
- **Menus:** each part's measure DI through the 111 dry menu presets on 3 amps, with `isolate`.
  - That was 6.5k renders on 3 processes, about 1 h 15 min alongside step 1's training.
  - Each preset is scored on both halves under `flat` and v3.
  - The data is in `~/ndsp-presets/learn/label-table/<part>/menu.json`, with each amp's best
    render as a FLAC.
- **Stems:** all 59 now have a guitar stem with no SNR filter.
  - 44 are reused from earlier runs with the same settings.
  - 15 are new, from `learn/separate.py` on the CPU, about 20–28 s each.
  - The index is `~/ndsp-presets/learn/label-table/parts.json`.
- **Checks:**
  - **Repeat renders** (3 parts × 5 presets, a different order): at most 6.2e-5 (log). Pass.
  - **Against the stored songs-check scores** (rendered without `isolate`), median 1e-5 to 2e-5 per
    part:
    - `It_Was_My_Fault_For_Waiting-ElecGtr1` differs by up to 0.178. This is the known
      quiet-start part ([render-order-audit.md](render-order-audit.md)).
    - `telefunken-Gym_Hours-GTR_1` differs by up to 0.0099, on one preset (median 1e-5).
    - Every other part is within 0.0045.
    - Reported, not fixed. The new table, with `isolate`, is the one later steps use.
