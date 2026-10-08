# Independent fixed-render Morgan flatref verification

Status: **VERIFIED_WITH_EVIDENCE_LIMITS**. 1215 checks; 0 failures.

Own NumPy formulas reconstruct flatref, targets, exact five-FFT scores and gate. No project scoring/canonical/gate functions are imported or called.

Stronger screen: **PASS**, valid=True; median improvement 57.8328280907%; 12/12 strict wins.
Group medians: {'chords': 0.5160926314261822, 'scales': 0.5823318550724486}

| Take | Wet primary | Net primary | Flatref primary | Simple | Net improvement |
| --- | ---: | ---: | ---: | --- | ---: |
| p2-chords-drop3-7-t098 | 5.31811629249 | 1.3566479893 | 3.55852047605 | flatref | 61.87606624% |
| p2-chords-drop3-m7b5-t098 | 5.14186354046 | 1.39771103654 | 3.36465257441 | flatref | 58.45897888% |
| p2-chords-set1-7-t099 | 4.81873229949 | 1.54940689564 | 3.02816527569 | flatref | 48.83347656% |
| p2-chords-set1-dim-t072 | 4.87056432244 | 1.62382009888 | 3.017100621 | flatref | 46.17945164% |
| p2-chords-set1-m7-t094 | 4.86924660773 | 1.40838395143 | 3.08754902285 | flatref | 54.38504973% |
| p2-chords-set1-maj-t072 | 5.01280275466 | 1.63364655261 | 3.16124248805 | flatref | 48.32264343% |
| p2-scales-a-t075 | 5.26872984715 | 1.49581308937 | 3.5667571345 | flatref | 58.06237899% |
| p2-scales-bb-t076 | 5.22421984088 | 1.32751601709 | 3.41885657097 | flatref | 61.17076018% |
| p2-scales-c-t075 | 5.31572256747 | 1.49185097668 | 3.58652440282 | flatref | 58.40399202% |
| p2-scales-db-t076 | 5.23029035799 | 1.36534240442 | 3.41607730413 | flatref | 60.03186454% |
| p2-scales-e-t076 | 5.2619528161 | 1.4366639417 | 3.38697505853 | flatref | 57.58268316% |
| p2-scales-g-t076 | 5.32534889766 | 1.46868720324 | 3.46415266538 | flatref | 57.60327719% |

Comparison: {"flatref_waveforms": 12, "gate_disposition": "PASS", "input_pins": 36, "original72_max_absolute_error": 8.04623034866836e-12, "original_replay_scalar_count": 72, "primary_max_score_scalar_gate_absolute_error": 8.881784197001252e-16, "primary_score_count": 108, "score_absolute_tolerance": 1e-08, "source_pins": 43, "waveform_max_absolute_error": 0.0, "waveforms_byte_identical": 12}

All twelve own values, waveform hashes and gate were saved before primary numerical access; the JSON records the timestamp and digest.

## Limits

- Inherited full ten-second raw-DI QC and original canary/renderer stability from the committed successful independent verification; only saved six-second raw score QC is freshly recomputed. Calibration seconds 0-2 are absent from allowed arrays.
- Original full wet output survives only for the first take/canary. Other eleven full-render hashes/peaks and pre-roll cannot be reconstructed in this scope.
- No separate plugin parameter-command transcript exists. This verification makes no new claim about physical plugin state.
- Saved net-input/baseline overlap checks the fixed 52-sample slicing, without remeasuring physical latency or fitting alignment.
- Predictions are frozen artifacts, checked against prior independently replayed prediction bytes; no fresh model inference is authorized or performed.
- One fixed clean Morgan chain, one player/guitar, twelve reused development performances. No native-transfer, driven-chain, multi-guitar, reserved-validation, song-ranking, shipping or long-training conclusion.
