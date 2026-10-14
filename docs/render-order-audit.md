# Render-order carry-over: what it affected (audit, 2026-10-14)

Found by the knob-ceiling run's repeat check ([plan](knob-ceiling-plan.md), amendment 3). The
working files are `tmp/render-order-inventory.md` and `tmp/render-order-heldout-sensitivity.md`
(local). No held-out audio was read and nothing was re-rendered for this audit.

## The bug

- **What happens:** in a reused plugin process, the render server calls Morgan's `reset`
  before every render. That reset doesn't clear everything: the previous render stays audible,
  at the amp's hiss level (about −69 dB), for 2–3 s.
- **When it matters:** the judge's score moves only where the part's DI is quiet inside a scored
  half.
- **The fix:** `isolate=True` in `AudioUnitRenderer` frees and rebuilds the render resources
  around each state write. It costs nothing measurable.
  - It is used by `learn/knob_ceiling.py`, and by the product's `match_preset` since #186.
  - Fresh-process renders were never affected; that includes the audition page and the Tone
    King starting presets.

## How big it was

Measured on 10 development parts (26 cells), by comparing the knob run's fresh menu scores
(with `isolate` or the 6-s pre-roll) against the stored songs-check scores (without either):
- **A part whose DI is 76% near-silent in half A** (`It_Was_My_Fault_For_Waiting-ElecGtr1`):
  some presets moved by up to 18% on half A. The best-preset pick didn't change on any amp.
- **Every other part** has no quiet stretch. The largest move per cell was under 1% (median
  about 0.01%) on both halves.
- **The quiet DI is the likely mechanism,** but it rests on that one quiet part. Exposure can
  be screened from the DI alone.
  - The ML session measured the quiet share of the 57 sets 1–2 development crops directly from
    their DIs: 17 have a half more than 20% quiet. Most were already excluded by the pairing or
    stem checks.
  - Held-out crops carry a stored activity share; the at-risk ones are listed in the
    sensitivity file.

## The decisions

Every menu-ranking pipeline used reused processes without the fix (inventory, section 0). Each
decision was recomputed from stored scores, with the at-risk parts dropped, or scored on the
quiet-free half only.

| decision | holds? |
|---|---|
| Clean starting presets beat the old template (−0.132) | yes (−0.136 without the at-risk parts) |
| Which clean preset per amp | yes; it flips on SW50R and AC20 if the parts with no activity record are dropped too |
| Crunch starting presets (−0.070, upper bound −0.003) | yes: no at-risk parts were in it; the margin stays thin |
| The confirmation #145 (−0.087) | yes (−0.080 to −0.086) |
| Set 3's held-out run | yes, unchanged |
| Routing results | yes; the recheck is undecided if the 11 parts with no activity record are dropped, but holds when they are scored on half B |
| **Set 5: C′ beats C (−0.124, upper bound −0.003)** | **Fragile.** Dropping the at-risk parts makes it inconclusive (upper bound +0.005), because two of their cells kept a near-zero band negative. Scoring them on half B keeps it passing. The flip comes from removing cells, not from evidence of contamination. The crunch-only gate turns *into* "helps" under the same rule. |
| Residual gate 1 (development) | yes; with `Signs-ElecGtr2` scored on half B it turns inconclusive, but that part moved at most 0.0045 in the re-render, so contamination there is negligible |

**Not settled without re-rendering:**
- **The thinnest margins:** crunch 0.003, set 5 0.003 and residual gate 1 0.001. They remain
  fragile.
- **Re-rendering held-out sets** with the fix would count as another held-out use: the user's
  call.
- **Driven presets, the songs check, sound-desc, the reference-proxy fallback and the
  fixed-level re-score** (development) were not recomputed.
- **Tone King renders in reused processes** (older benchmark and match runs) are "unknown":
  the bug is measured only on Morgan.

No shipped choice changes. `match_preset` now uses `isolate` (#186). Training renders for the
DI networks also carry the hiss-level carry-over in their targets; that is not measured,
though at about −69 dB it is unlikely to matter.
