# Frozen-model Morgan control on known P2 dry performances

**Declared: 2026-10-08, before computation.** Fresh Pauli review approves the
corrected exact snapshot; 178 synthetic tests pass and two optional Torch checks
skip in the helper. Commit before execution. [Review and initial finding](research/di-morgan-control-review-2026-10-08.md).
Only this administrative declaration/review link changes the approved draft.

## Why this separate control

The [native pilot](di-domain-pilot-v2-results.md) stopped at pairing requirements,
independently verified with zero mismatches (`2baf2e3`). It did not test the neural
model. This control asks whether the existing frozen model recovers a useful
average-balanced DI from these unseen performances after the same fixed Morgan
chain. It needs no microphone alignment and cannot answer native-chain transfer.
The stopped screen remains closed with its original rejection rules and records.

Use **all twelve original P2 takes** in [the original manifest](di-domain-pilot-inputs.json),
not just the three accepted native pairs. Keep the same raw DI files/crop starts,
fold2 checkpoint, frozen average, PR12 shipped preset+R, input level and all timing,
target and scoring definitions from [the first declaration](di-domain-pilot-plan.md).
No new take selection, fitting, checkpoint choice, knob search, training or reserved
data. The original independent native verification already read these exact DIs;
this is development diagnostic reuse, not an untouched confirmation.

## Exact preparation and execution

Separate entry point: `learn/di_morgan_control.py STAGE --run tmp/di-morgan-control-20261008`.
Stages: `metric`, `numpy`, `prepare`, `render`, `infer`. Every run/stage/output is
exclusive. Pin committed code/tests/declarations/manifests/coefficient bits before
every stage. Preserve logs and partial/failure reports; no duplicate hosts/jobs.

1. Repeat the approved attempt-2 synthetic **metric** and actual helper **numpy**
   replay in this new run. Same four cases, exact saved/live Torch32 windows,
   unchanged absolute **1e-8** gate, identity <1e-6 and byte-identical regenerated
   signals. Code/declaration/path-manifest/window bytes only before both pass.
2. Validate the original catalog selection and frozen model/average hashes; record
   the observed model/average hashes explicitly in asset provenance. `prepare`
   reads only the twelve bounded raw DI slices (10 seconds plus 512 guards, 48 kHz,
   mean channels), never microphone audio. Strip guards without alignment. Apply
   original raw-waveform QC separately to 0–4 and 4–10 seconds: finite, clipping
   fraction ≤1e-4 at abs≥0.999, RMS≥1e-5, activity≥80% at the original 10-ms/−40-dB
   definition. All twelve required, no replacements. Native pairing thresholds are
   irrelevant to this known-DI control and are not changed or waived in the closed pilot.
3. Build the canonical target from each raw DI's six seconds 4–10 using the same
   frozen average/own mean-removed smoothed spectrum, ±15-dB clamp and FFT EQ.
   Save raw score DI, target and original-level raw DI seconds2–10 for rendering.
   Target-against-itself primary score must be <1e-6 for every take. Report all
   preparation failures; incomplete valid coverage stops before the plugin.
4. **render:** same shared renderer and fixed PR12+R edits as originally reviewed,
   but source preparation is explicitly `prepare/`, never a fabricated successful
   native report. One reused host; first warm-up and immediate first-render canary,
   original1-dB RMS/fixed-band gates and both metadata/waves saved; finally-close.
   Two seconds pre-roll, six retained seconds, extra52samples. Network input keeps
   raw52sample latency, input-as-DI baseline advances52. No gain/delay fitting.
5. **infer:** twelve CPU frozen-model six-second predictions, `rebuild` on float32
   render input, no fitted output timing/EQ or gradient. Score prediction and
   latency-corrected wet-as-DI against the same canonical target with exact shared
   Torch32 coefficients. Score center three seconds after independent std-to0.1
   normalization; also report waveform L1 and raw-DI low-band diagnostic unchanged.
   Retain every prediction, score, hash and versions. Failed/nonfinite/zero-denominator
   comparison stops or marks the screen inconclusive; no row is dropped.

CPU metric/infer prefix: `/Users/yoavbz/ndsp-presets/tools/learn-venv`.
Helper numpy/prepare/render: repo `.venv`, through `neuraldsp-safe python-file`.
No embedded interpreter switching, installs/downloads or GPU process. Cooperative
15-minute budget per stage, checked between takes; monitor stuck calls externally.
No hard wall-clock interrupt is claimed. Logs:
`tmp/di-morgan-control-{metric,numpy,prepare,render,infer}.log`.

## Fixed gate and interpretation

For each take `improvement = (wet_primary-net_primary)/wet_primary`, then take the
median across all twelve. This is the **same standalone Morgan positive-control
rule** from the original pilot: median improvement **≥10%**, with eight
`math.ulp(0.1)` roundoff allowance only at that inclusive boundary. All twelve raw
DIs, all oracles, renderer stability and complete score coverage must be valid.
Strict win count and six-chord/six-scale group medians are reported as diagnostics,
not added post hoc to the control gate. Baseline denominators must be positive.

- Pass: supports recovery through this one training-compatible fixed Morgan chain
  on these performances. It permits declaring the next bounded diagnostic; it
  does not establish native transfer, driven/multi-guitar coverage, preset ranking
  or product readiness, and does not authorize long training.
- Completed valid fail: the frozen network misses its existing Morgan-control
  margin on this panel. Investigate that model/target/preprocessing/generalization
  issue before attributing past failures to microphone domain shift or training longer.
- Preparation/render/metric/inference control failure: inconclusive, review the
  specific failed control; do not tune this run to pass.

Meaningful synthetic tests, fresh independent design/code review and commit must
precede execution. Post-run fresh-context verification independently recomputes
raw preparation, metric/score definitions, coverage and gate; reproduce predictions
from the same pinned model and saved render input when inference runs. Preserve
render evidence without rerendering or selecting repeats. Update result/roadmap/
index/DI plan/learn README before following results into another bounded experiment.

Pedroza et al., Guitar-TECHS, CC BY4.0, https://zenodo.org/records/14963133.
One player/guitar, six chords/six scales, one clean fixed Morgan chain. No P1/P3 or
reserved songs/scores are used. No claim of multi-guitar or driven-amp coverage.
