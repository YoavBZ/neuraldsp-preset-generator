# Development activity-mask diagnostic

Draft 2026-10-08, following the reviewed development routing diagnostic. Independent
review and commit are required before opening audio for this new analysis.

## Why and scope

The first diagnostic finds known-DI menu headroom, but rebuilt selection refuses
Colour Me Red ElecGtr03 in every amp/band-set cell. Before any further training,
test whether choosing which moments contain playing explains that refusal, without
changing rendered waveforms. This is an exploratory case study with fixed controls,
not evidence of generalization or a way to amend the failed reserved confirmation.

- Development audio/renders only. SW50R only, all 45 frozen candidates, both band sets.
- Parts: the lexicographically first development slug in each of 11 bands, plus
  `cambridge-colour-me-red-elecgtr03`, deduplicated (12 expected).
- Use existing `phase2-set3/net/` and `measure/` saved DI arrays and renders, existing
  reference crops and original development scores. Do not generate audio, infer a
  model, train, change presets, change lags, or open any reserved score/audio file.
- Pin source scores, metadata, menu inventory, diagnostic results, code and selected
  source-file hashes in the report. Validate exact development membership and menus.

## Intervention: change only the activity-proxy argument on half A

Call the existing audio-distance primitive on unchanged net renders and reference,
with `lag=-52`, standard defaults and the original half A [1,5.5) seconds:

1. **Original:** saved rebuilt DI as the activity proxy. Reproduce cached `net_A`
   distances/refusals before interpreting other variants (absolute tolerance 1e-6,
   including matching null state; record reasons).
2. **Known-DI mask control:** saved average-measure DI moved into reference time by
   the already declared raw DI-to-reference lag (`judge_lag_samples+52`). For reference
   sample t, proxy[t] = measure_DI[t-raw_lag], zero padded. This is an unavailable
   input control and is never a product method.
3. **Isolated-reference heuristic:** the isolated amp-track reference itself as the
   proxy. This is available in this case study; transfer to a full mix or separated
   stem is untested. It can mistake distortion, effects or bleed for playing and is
   not a validated replacement judge.

No threshold sweeps, pause-limit relaxation, band-rule changes, frame-size changes or
lag fitting. Swap only the proxy argument and allow all its downstream effects:
activity/tail selection, level-offset cells, frames used to derive spectral band
support, and residual centering. Band-selection rules stay fixed, but selected bands
may change. The proxy does not replace the signal fed to the plugin. Evaluation stays the
original average-measure `measure_B` distances on [5.5,10) with the original lag.

For each proxy choose the minimum valid A score, lexicographic ties, and evaluate
the chosen preset on saved B scores. Preserve null refusals and nonpositive log
failures separately. Report every candidate refusal reason, selection changes,
paired B log ratios and raw wins/losses/ties. Include the development diagnostic's
already-computed factory-only and inclusive leave-band-out constants. Do not refit
a constant on this selected panel. Compare original choices exactly before judging
the intervention. Missing source files or baseline reproduction disagreements are
execution errors, retained and investigated; they are not sample exclusions.

## Predetermined interpretation

- Removing the target refusal with the known-DI proxy, while waveforms and lag stay
  fixed, attributes that refusal within this primitive to the proxy and its downstream
  effects. It does not prove the network's waveform is good or perceptual
  similarity improves.
- A reference proxy is eligible for a separately declared all-development check
  only if it removes the target refusal in both band sets, introduces no new missing
  selection on controls, has valid raw B evaluations for original and reference
  selections on all 11 controls plus a valid target B after rescue, and its B choices
  improve on original choices in at least
  three control parts and worsen in at most one under each band set. Ties are neutral;
  the target's formerly missing B comparison is not an improvement in this count.
  Missing B evaluations fail eligibility; they cannot disappear from counts. Zero
  distances are valid for raw comparisons but unscorable for log ratios.
- If that heuristic misses, do not tune it on this panel or silently expand it. Record
  the result and declare the next intervention after independent verification.
- No model training or product release follows this sample alone. Heavier-tone
  listening and fresh reserved confirmation remain necessary for a changed method.

## Execution and verification

Use the approved tracked entry point through `neuraldsp-safe python-file`. Re-score
baseline first with the same runtime as the variants; report runtime versions and
the baseline comparison against historical scores. CPU only, no GPU task or licensed
plugin invocation. Synthetic tests cover shift direction/zero padding, exact split
selection, refusal handling, candidate completeness and the fixed routing rule.
Independent design/code review before execution and numerical/audio spot checks
afterwards. Save a new report; never overwrite earlier experiments.

**Declared 2026-10-08:** independent design/code/documentation review approved
after the three design clarifications. All 38 mask-diagnostic synthetic checks
passed through the approved helper (the preceding score-only diagnostic's 19 checks
also passed). Implementation and declaration are committed before actual audio
execution. No new reserved-set use, rendering or model training is authorized here.
