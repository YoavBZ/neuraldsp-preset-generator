# Independent known-DI Morgan control verification

**Status: VERIFIED_WITH_EVIDENCE_LIMITS**

Pedroza et al., Guitar-TECHS, CC BY 4.0, https://zenodo.org/records/14963133

Frozen revision: `a5b96052bb16d6a3695b4040a9b3923ba90de645`. Primary scores unread: False.

Independent NumPy five-FFT metric, target, raw QC, repeatability canary and gate. Only frozen `direc.build_model/rebuild` are shared.

Checks: 767; failures: 0.
Raw preparation rows: 12; replay rows: 12.

Standalone scientific positive control: **PASS**.

Median improvement: 72.17797505%; strict wins: 12/12 (diagnostic).

Group medians (diagnostics): {'chords': 0.6946105454854318, 'scales': 0.7255898018614853}.

| Take | Wet primary | Net primary | Improvement |
|---|---:|---:|---:|
| p2-chords-drop3-7-t098 | 5.318116292 | 1.356647989 | 74.4901% |
| p2-chords-drop3-m7b5-t098 | 5.14186354 | 1.397711037 | 72.8170% |
| p2-chords-set1-7-t099 | 4.818732299 | 1.549406896 | 67.8462% |
| p2-chords-set1-dim-t072 | 4.870564322 | 1.623820099 | 66.6605% |
| p2-chords-set1-m7-t094 | 4.869246608 | 1.408383951 | 71.0759% |
| p2-chords-set1-maj-t072 | 5.012802755 | 1.633646553 | 67.4105% |
| p2-scales-a-t075 | 5.268729847 | 1.495813089 | 71.6096% |
| p2-scales-bb-t076 | 5.224219841 | 1.327516017 | 74.5892% |
| p2-scales-c-t075 | 5.315722567 | 1.491850977 | 71.9351% |
| p2-scales-db-t076 | 5.230290358 | 1.365342404 | 73.8955% |
| p2-scales-e-t076 | 5.261952816 | 1.436663942 | 72.6971% |
| p2-scales-g-t076 | 5.325348898 | 1.468687203 | 72.4208% |

## Evidence limits

- Full wet renders were retained only for the first take/canary. For the other 11, full-render hashes/peaks and wet pre-roll cannot be independently reconstructed; six-second input/baseline overlap and all original-level host inputs are verified.
- Saved host log has no parameter command transcript. Fixed PR12+R and warm-up/close sequence are supported by pinned code; actual plugin state is not separately recorded.
- The fixed 52-sample slicing is checked exactly from saved waves. This does not remeasure physical plugin latency or fit a delay.

One player/guitar and one fixed clean Morgan chain. No native-transfer or product claim. Win count and group medians do not add gates.
