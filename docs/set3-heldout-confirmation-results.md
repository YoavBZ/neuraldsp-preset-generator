# Set 3 held-out confirmation: not passed

Run 2026-10-08 after the user's approval. Rendering and both scoring passes are
complete. **Verified result: neither amp passes the declared gates.** Independent
numerical and audio verification completed at 06:13:10 UTC with no discrepancies.

## Frozen procedure

- Declaration: `15aad30`, [plan](set3-heldout-confirmation-plan.md).
- Input manifest: `4ad02fa`, [frozen inputs](set3-confirmation-inputs.json).
- Model, procedure and runtime are unchanged from that manifest.
- Material: the declared 27 reserved parts from six bands; amp tracks only.
- SW50R is primary; PR12 is secondary. AC20 and held-out mixes/stems are excluded.
- Menus: 45 SW50R and 35 PR12 candidates, including template+R.
- Rendering: `measure` and `net`, three disjoint shards, one reused licensed-plugin
  instance per process, CPU inference, peak-normalised PCM24 FLAC.
- Total completed: 4,320 retained renders and 54 completion markers, plus discarded
  warmups. All three render processes exited successfully.
- Main output: `~/ndsp-presets/learn/direc/phase2-set3-heldout/`.
- Execution logs: `tmp/set3-heldout-render-{0,1,2}.log` (local, retained).
- Waveform scoring completed at 06:03:58 UTC; onset sensitivity completed at
  06:08:20 UTC. Both exited successfully with explicit completed attempt states.
  Logs: `tmp/set3-heldout-score-{waveform,onset}.log`. No retries were needed.

## Fixed constants

Chosen using all 33 development parts' raw half-A distances, with the declared rule:

| Band set | SW50R | PR12 |
|---|---|---|
| recording | Royce Whittaker / Wall Of Doom | Neural DSP / Vintage Metal |
| union | Royce Whittaker / Wall Of Doom | Keyan Houshmand / Modern Metal (Pick Hard) |

These are identifiers of local factory presets, not new presets published by this
experiment. The manifest pins their settings hashes.

## Independent verification

A separate reviewer rederived all four constants, every selection, effect and gate
from the distance records without calling the production selection or summary
functions. The sampling was fixed before outcomes existed. It checked:

- Selected/template/constant half-B audio for all 27 parts under both timing analyses,
  both amps and both band sets.
- All half-A candidates on the lexicographically first part in each of six bands,
  both amps: 12 complete menus.
- 1,586 distance comparisons, deduplicated to 1,321 distinct audio measurements,
  with zero mismatches and zero maximum absolute distance difference.
- 672 storage checks and 12 DI-construction checks (rebuilt and average-measure DI
  on six parts), all passed. The six rebuilt DIs exactly matched fresh frozen-model
  inference; independently reconstructed measure DIs also matched.
- Exactly 4,320 expected FLACs, no missing or unexpected clips, and 54 completion
  markers matching the frozen manifest. Checked input hashes did not change.
- Training inventories contain no set-3 training bands and agree with the saved
  training-log counts (38,709 training, 10,097 validation rows). Seventeen existing
  leakage checks passed. Saved metadata/logs support this exclusion but cannot prove
  every historical optimizer input; the checkpoint has no signed data lineage.

The independent implementation covers statistics, selection, DI windowing,
normalization and average-measure construction. It shares the frozen audio-distance
primitive and model architecture, and did not perform fresh plugin renders. Its
successful verification establishes agreement and procedural correctness within
that scope, not a successful model.

Machine-readable [evidence](set3-confirmation-evidence/README.md) includes both
distance records, production summaries/verdict, predetermined sampling and the full
independent report. Audio, model weights and factory preset payloads stay local.

## Numerical result

The effects are the declared median of six band medians of paired log distance
ratios; negative means closer. Win shares give every band equal weight. These are
measurement results, not percentages of perceptual similarity. All cells contain
27 parts across six bands, with **zero required-comparison refusals**.

| Timing | Bands | Amp | vs template+R | vs fixed constant | Constant paired p | Joint win share | Pass |
|---|---|---|---:|---:|---:|---:|---|
| waveform | recording | SW50R | −0.474401 | −0.150884 | 0.62500 | 0.570707 | no |
| waveform | union | SW50R | −0.475227 | −0.163302 | 0.43750 | 0.570707 | no |
| waveform | recording | PR12 | −0.305872 | +0.003293 | 0.62500 | 0.378788 | no |
| waveform | union | PR12 | −0.176651 | +0.017891 | 0.71875 | 0.409091 | no |
| onset | recording | SW50R | −0.474401 | −0.150884 | 0.62500 | 0.570707 | no |
| onset | union | SW50R | −0.474775 | −0.163302 | 0.43750 | 0.570707 | no |
| onset | recording | PR12 | −0.305872 | +0.003293 | 0.62500 | 0.378788 | no |
| onset | union | PR12 | −0.175289 | +0.017891 | 0.71875 | 0.409091 | no |

Unrounded numbers determine gates. SW50R passes the template margin, constant
margin and joint-win gates in both band sets, but fails the required constant
sign-flip test (p must be below 0.1). PR12 also fails the constant margin and
joint-win gates. The alternate declared timing changes neither amp's verdict.

For recording bands, SW50R beats the constant at the band median on Crazy Swedes,
Dunning Kruger and Silona, loses on Scott Elliott and Silence Is Near, and ties on
V.M.GY. The median gain therefore does not establish a reliable improvement across
bands. With six bands, uncertainty remains substantial; this failure does not prove
the general task impossible.

## Decision and next work

Under the frozen decision rule, this verified SW50R failure means this learned
method does not ship. The recording-selected constant remains a baseline candidate,
not a validated song-to-preset product.

Before further long training or a wider knob search, declare a development-only
diagnostic comparing true-DI selection with rebuilt-DI selection and the fixed
constant. A true-DI positive control can distinguish menu/ranking limits from the
reconstruction gap. Validate heavier-tone measurement by listening before treating
its numerical gains as product quality. Model changes, stem training and a wider
search follow evidence from those checks rather than automatic larger runs.

No training, preset adjustments, new constants or threshold changes are permitted
in response to these reserved recordings. Set 3's reserved split is now spent for
this confirmation; future improvements need development-only experiments and a
fresh declared confirmation set.

This test used isolated amp tracks. Song-mix and separated-stem performance and
heavier-tone listening are unassessed here. The existing listening validation covers
one listener and clear clean-PR12 differences. A shared audio-distance primitive in
the independent recheck cannot independently validate the measure's perceptual
meaning. Reused plugin state and operating-system behavior also limit sample-exact
reproduction; render order and logs are retained.
