# Set 3 held-out confirmation: execution in progress

Started 2026-10-08 after the user's approval. This file records execution status,
not an accuracy result. No model verdict is available yet.

## Frozen procedure

- Declaration: `15aad30`, [plan](set3-heldout-confirmation-plan.md).
- Input manifest: `4ad02fa`, [frozen inputs](set3-confirmation-inputs.json).
- Model, procedure and runtime are unchanged from that manifest.
- Material: the declared 27 reserved parts from six bands; amp tracks only.
- SW50R is primary; PR12 is secondary. AC20 and held-out mixes/stems are excluded.
- Menus: 45 SW50R and 35 PR12 candidates, including template+R.
- Rendering: `measure` and `net`, three disjoint shards, one reused licensed-plugin
  instance per process, CPU inference, peak-normalised PCM24 FLAC.
- Total planned: 4,320 retained renders, plus discarded warmups.
- Main output: `~/ndsp-presets/learn/direc/phase2-set3-heldout/`.
- Execution logs: `tmp/set3-heldout-render-{0,1,2}.log` (local, retained).

## Fixed constants

Chosen using all 33 development parts' raw half-A distances, with the declared rule:

| Band set | SW50R | PR12 |
|---|---|---|
| recording | Royce Whittaker / Wall Of Doom | Neural DSP / Vintage Metal |
| union | Royce Whittaker / Wall Of Doom | Keyan Houshmand / Modern Metal (Pick Hard) |

These are identifiers of local factory presets, not new presets published by this
experiment. The manifest pins their settings hashes.

## Verification planned before outcomes

A separate reviewer will rederive constants, every selection, effect and gate from
the distance records without calling the production selection or summary functions.
It will also re-score selected/template/constant half-B audio under both lag analyses,
and check the full half-A menu on the lexicographically first part in each band for
both amps. Those six parts also receive a frozen-model DI reconstruction check.

## Pending

Rendering, waveform scoring, onset sensitivity, independent verification and final
interpretation. No training or preset adjustments are permitted in response to these
recordings. Passing would confirm isolated-track selection only; song mixes and
heavier-tone listening still need their own checks.
