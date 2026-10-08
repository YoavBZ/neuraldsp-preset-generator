# Independent known-input-shift verification

Verification: **VERIFIED**. Scientific disposition: **PASS**.

Revision `885907f27ea487662ae6c6216226ae7ba6ca8e77`. 21246 checks; 0 failures.

Independent scorer, gates, finite shifts, Torch architecture and original ordered float32 six-second reconstruction. No project numerical functions imported or called.

| Offset | Screen | Median advantage | Wins | Chords | Scales |
| ---: | --- | ---: | ---: | ---: | ---: |
| -3 | PASS | 57.79588331% | 12/12 | 51.58301978% | 58.24387995% |
| -2 | PASS | 57.81210656% | 12/12 | 51.57988975% | 58.24567659% |
| 0 | PASS | 57.83282809% | 12/12 | 51.60926314% | 58.23318551% |
| 2 | PASS | 57.85996785% | 12/12 | 51.66900416% | 58.21684658% |
| 3 | PASS | 57.86591146% | 12/12 | 51.70093897% | 58.20767721% |

Maximum scalar discrepancy: 8.255618411112664e-12; absolute tolerance 1e-08.

Full derivation, compressed expected raw/corrected prediction NPZ bytes, all mismatches, identity checks and read audit are retained in the JSON report.

## Evidence limits

- Independent implementation shares underlying NumPy/SciPy/Torch libraries and CPU kernels with the primary; this is not library-independent verification.
- Pinned source, reviewed synthetic tests and saved timestamps support primary call-order barriers. Actual primary runtime calls were not independently observed retrospectively; the verifier directly observes only its own calls and read barrier.
- Twelve dependent same-player/guitar development takes and one clean Morgan chain. Known input perturbations include finite padding, context and whole-window standard-deviation effects; no isolated stride causation, native transfer/failure, product or long-training claim.
- Original full wet renders survive for the first take/canary only; other full-render/pre-roll evidence is inherited. No separate plugin command transcript; physical latency and plugin state are not remeasured.
- Original ten-second preparation QC, canonical target construction and prior provenance remain inherited; allowed six-second raw DI QC and frozen target identities are rechecked. No average/catalog/raw/native/reserved data accessed.
- Completion/exit0/session53958/19.60s are supplied by main. Saved output completeness is independently inspected; the historical process exit is not independently reobserved.

## Preserved initial comparison

The initial comparison retained 36 schema mismatches: this verifier omitted the required empty `nonfinite_diagnostic_fields` list on replay records. All prediction byte checks and numeric comparisons passed. The final comparison adds only that source-defined metadata field and reuses the complete previously persisted independent derivation. No model inference, scoring, tolerance change or case selection was repeated. Original failed checks, logs and source identities are preserved in JSON.

## Discrepancies and stability

- new_primary_numerical_comparisons: maximum 0, 5403 scalar fields; largest at `None`.
- original108_and_direct36_replays: maximum 8.0462303486683595e-12, 159 scalar fields; largest at `p2-chords-set1-m7-t094 replay wet.raw_lowband`.
- inherited_metadata_comparisons: maximum 8.255618411112664e-12, 21609 scalar fields; largest at `p2-chords-set1-m7-t094 oracle scores.raw_lowband`.

All 63 pinned source/dependency identities, HEAD, 48 original artifacts, original model and 67 primary artifacts remained stable. No new inference or scoring was performed during the schema correction.
