# Attempt-2 independent result verification

**VERIFIED QC STOP; SCIENTIFIC SCREEN INCONCLUSIVE**

Pedroza et al., Guitar-TECHS, CC BY 4.0, https://zenodo.org/records/14963133

Verifier imports only standard/numerical libraries, never production P/R/V or direc functions. All twelve independent native derivations precede saved row/NPZ numerical reads. No model checkpoint/catalog read, rendering, inference, new experiment, alternative alignment, threshold, timing, crop, or selection.

## Exact counts

```json
{
  "declared": 12,
  "independently_derived": 12,
  "bounded_source_reads": 24,
  "gcc_estimates": 36,
  "calibration_pass": 3,
  "valid": 3,
  "rejected": 9,
  "valid_chords": 3,
  "valid_scales": 0,
  "first_failure_counts": {
    "calibration GCC-PHAT peak sharpness must exceed 10": 8,
    "calibration filtered correlation below 0.5": 1
  },
  "npz_arrays_checked": 24,
  "scalar_scores_checked": 39,
  "renders": 0,
  "inferences": 0
}
```

## Independent calibration diagnostics

Full / first half / second half; correlations are signed. QC after a failed calibration is diagnostic only and never rescues rejection.

| Take | Lags | Sharpness | Peak separation | Full correlation | First failure |
|---|---|---|---|---|---|
| p2-chords-drop3-7-t098 | 38/38/37 | 40.3796921/46.7441681/10.2210834 | 2.99792539/2.90737857/1.94448551 | 0.891972878567 | valid |
| p2-chords-drop3-m7b5-t098 | 38/38/38 | 42.6343626/43.1735715/9.65161311 | 3.7208832/3.39043561/1.9112103 | 0.88394223725 | calibration GCC-PHAT peak sharpness must exceed 10 |
| p2-chords-set1-7-t099 | 39/39/39 | 36.3665549/33.2831904/12.3211406 | 3.70628942/2.70460745/1.81018782 | 0.97035929546 | valid |
| p2-chords-set1-dim-t072 | -46/-46/-47 | 15.7511147/12.851368/37.4952182 | 2.24227646/2.95156513/2.7104373 | 0.980714085239 | valid |
| p2-chords-set1-m7-t094 | 40/39/39 | 39.3404242/26.0390877/9.27484264 | 3.48840859/2.3814919/2.07872585 | 0.960338059919 | calibration GCC-PHAT peak sharpness must exceed 10 |
| p2-chords-set1-maj-t072 | -47/-47/-47 | 8.89660823/9.69927885/26.5541757 | 1.47147383/2.66865749/2.18068684 | 0.966327358634 | calibration GCC-PHAT peak sharpness must exceed 10 |
| p2-scales-a-t075 | 36/37/33 | 27.9095429/38.3577541/6.72196636 | 1.47325616/2.16223907/1.02241847 | 0.465140332598 | calibration GCC-PHAT peak sharpness must exceed 10 |
| p2-scales-bb-t076 | 36/37/37 | 9.80770007/19.955541/22.9754474 | 1.30344465/1.64980659/3.46943996 | 0.0998994764198 | calibration GCC-PHAT peak sharpness must exceed 10 |
| p2-scales-c-t075 | 38/38/36 | 28.0629794/40.885173/4.29696939 | 1.68626056/2.4443454/1.27124164 | 0.383628597207 | calibration GCC-PHAT peak sharpness must exceed 10 |
| p2-scales-db-t076 | 36/37/36 | 9.89262243/21.0543928/30.5902493 | 1.27774672/1.66176551/2.5025722 | 0.118245321342 | calibration GCC-PHAT peak sharpness must exceed 10 |
| p2-scales-e-t076 | 35/37/37 | 8.05637764/20.9580356/30.5144193 | 1.21719902/1.4769379/3.57661459 | 0.354738402833 | calibration GCC-PHAT peak sharpness must exceed 10 |
| p2-scales-g-t076 | 35/37/37 | 10.6219046/21.7799616/29.6103848 | 1.22078318/1.5071425/1.63080425 | 0.333960353878 | calibration filtered correlation below 0.5 |

## Verification evidence

- The JSON records all 36 estimates, PHAT floors/used bins/peaks/runner-up lags, all calibration predicates and full/half correlations, 48 interval QC reports, 24 source-slice hashes and exact bounded-read definitions.
- Compressed/decompressed coefficient hashes and all 7,936 Torch32 coefficient bytes checked; live CPU Torch default float32 Hann bits checked without changing its default dtype. Independent synthetic component/aggregate references use only the four declared signals. Both saved runtime reports, source pins, versions, signal hashes, reference linkage and absolute 1e-8 gates checked.
- Valid-row DI/wet/render preparation requires exact bytes. Canonical target/flatref independently reconstruct the original spectrum/smoothing/mean removal/clamp/FFT formula using the pinned average. Calibration-only centered 256-tap ridge/intercept and reflected evaluation prediction independently recomputed. Array comparison tolerance is 1e-10 absolute; scalar score tolerance is 1e-8; calibration/QC 1e-12. These are verification roundoff bounds and do not alter scientific gates.
- All valid-row primary, waveform L1 and raw-DI low-band baseline/flatref/FIR/oracle scores checked. JSON retains every array and scalar absolute error; native complete/valid and exact coverage checked, progress compared with final rows and log. No render/infer artifacts or logs exist.

Mismatches: **0**.

```json
[]
```

## Interpretation and limits

Declared calibration/QC rejected the required complete twelve-take pairing. This does not measure neural transfer, prove recording-domain failure, establish irrecoverability, support selection of replacement takes, or authorize tuning/training. Valid-subset scores are diagnostic only.

Declared model SHA is recorded from manifest; checkpoint bytes deliberately not read. Native asset record pins source/catalog/revision, not model/average byte hashes. Average independently rehashed; catalog selection taken from authoritative manifest.

Historical absence of execution is supported by complete run inventory, native-only logs/progress and stage guards, not by an independent operating-system execution audit. Rejected rows lacked saved estimate diagnostics because production stops at the first calibration exception; the independent report fills these in without changing rejection.

HEAD/branch and unchanged frozen source dependencies were checked outside this script using read-only git commands. Concurrent navigation edits were observed in docs/README.md, docs/ROADMAP.md, docs/di-recovery-plan.md and learn/README.md and left untouched. JSON preserves source pins, run/log artifact hashes, verifier hash, versions, access inventory and derivation order. Existing run and failed logs were preserved; only this script and the two exclusive reports were written. No result documentation or git mutation performed.
