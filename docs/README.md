# docs

Start with **[ROADMAP.md](ROADMAP.md)**: where the product is, what comes next, and the
decisions so far. It is the one living plan. Everything else here is a record: what
was declared, what was measured, and the research behind it.

## How this folder is kept

- **Each experiment is a pair, plus its data.** `<topic>-plan.md` is written and
  committed before anything is computed; `<topic>-results.md` records what came out;
  `<topic>.json` is the script's output. Changes to a plan after it is declared are
  added as dated amendments, never silent edits. The only edits made in place are
  path updates when files move.
- **Declarations are frozen.**
  - [heldout-listening-sw50r.md](heldout-listening-sw50r.md) is pinned by hash in
    code and stays byte-identical.
  - [listening-validation-plan.md](listening-validation-plan.md) is read by code,
    which requires the single trial hash in it, so it isn't edited either.
  - Other plans keep their text and gain only dated status notes at the top, or a
    note in this index.
- **Some files keep their paths because code reads them:**
  - `validation-datasets.json`, `validation-sources-2.json`, `validation-lags.json`;
  - `amp-reach.json` and `reach-sets.json` (the shortlist measurement);
  - `kill-tests-judge-lags.json` (the kill tests' `--lags` input);
  - the test fixtures `m6-paired-target.json`, `match-pipeline-set2-sw50r.json`,
    `rt60-synthetic-evidence.json` and `topology-*.json`.
- **Others keep theirs because frozen or shipped files cite them:**
  - `recordings-benchmark-sw50r.json`, which the frozen held-out declaration cites
    (its Tone King sibling moved);
  - `toneking-control-grid.json`, cited by the Tone King manifest;
  - `validation-crop-rules.json` and the listening-validation results files.
- **When an experiment closes** and nothing reads or cites its outputs, they move to
  `data/<workstream>/`.
- **`docs/research/`** holds the literature research rounds, oldest first (the
  research *tooling* is the top-level `research/` folder).
- **Crop rules:** rule 1 (the loudest 10 s) cut the crops every experiment through the
  shortlist measurement used. Rule 2 (where the DI plays most) is for crops cut from now
  on ([validation-datasets.md](validation-datasets.md)). The product's own excerpt rule
  is in [reading-a-reference.md](../reference/reading-a-reference.md).

## By workstream

**The plugin itself**
- [measuring-against-the-plugin.md](measuring-against-the-plugin.md): what the plugin
  does, measured. Current, and the reference the packs cite.

**Measuring closeness: the judge** (current)
- [measuring-closeness.md](measuring-closeness.md): what the judge is, and why it
  superseded the v1–v3 search objectives as the measure of closeness.
- [listening-validation-plan.md](listening-validation-plan.md) →
  [results](listening-validation-results.md): validated for clear clean-to-crunch PR12
  differences.
- [no-di-rule-under-the-judge-plan.md](no-di-rule-under-the-judge-plan.md) →
  [results](no-di-rule-under-the-judge-results.md): void, so the no-DI figures stay
  unconfirmed.

**Validation data** (current)
- [validation-datasets.md](validation-datasets.md): the development and held-out sets,
  crop rules, lags.

**Song-only shortlist** (current)
- [song-only-shortlist-plan.md](song-only-shortlist-plan.md) →
  [results](song-only-shortlist-results.md): research not shown to beat the template or
  a random list; choosing by ear (a perfect one) helps.
- [listening-check-plan.md](listening-check-plan.md), with its fixed inputs
  `listening-check-inputs.json` → [results](listening-check-results.md): inconclusive
  (a void sitting); for some songs the listener could not find the guitar or compare
  tone across different notes.

**Song-only distance** (current)
- [di-free-distance-plan.md](di-free-distance-plan.md) →
  [results](di-free-distance-results.md): no hand-made distance without a DI picks
  presets clearly better than a song-blind constant; they track the tone only when the
  notes match.

**Song-to-preset research and amp choice** (active; individual methods noted below)
- [supervised-model-plan.md](supervised-model-plan.md).
- Kill tests: [kill-test-k3-plan.md](kill-test-k3-plan.md),
  [kill-test-results.md](kill-test-results.md),
  [kill-tests-pr12-plan.md](kill-tests-pr12-plan.md) →
  [results](kill-tests-pr12-results.md).
- [amp-identifiability-plan.md](amp-identifiability-plan.md) →
  [results](amp-identifiability-results.md).
- [amp-reach-plan.md](amp-reach-plan.md) → [results](amp-reach-results.md).
- [quick-checks-plan.md](quick-checks-plan.md) → [results](quick-checks-results.md).
- [preset-model-poc-plan.md](preset-model-poc-plan.md) →
  [results](preset-model-poc-results.md): a trained network on PR12. Not passed, but it
  reads part-specific information.
- [di-robustness-plan.md](di-robustness-plan.md) → [results](di-robustness-results.md):
  the judge through a wrong DI.
- [di-recovery-plan.md](di-recovery-plan.md) → [results](di-recovery-results.md):
  rebuilding the DI. Not passed on clean PR12;
  [set-3 results](di-recovery-set3-results.md): strong against the clean default; against
  a constant, a conditional pass on SW50R only.
- [set3-heldout-confirmation-plan.md](set3-heldout-confirmation-plan.md): approved
  one-time SW50R confirmation, with PR12 secondary (2026-10-08). Inputs were committed
  before held-out audio was read; the procedure remains frozen.
- [set3-heldout-confirmation-results.md](set3-heldout-confirmation-results.md): neither
  amp passes under either timing. Independent numerical/audio checks agree; this
  learned method does not ship. Full evidence is linked from the result.
- [set3-development-diagnostic-plan.md](set3-development-diagnostic-plan.md) →
  [results](set3-development-diagnostic-results.md): known-DI selection shows menu
  headroom on all three amps; independently verified. One rebuilt-DI refusal routes
  the next check. No reserved-data reuse.
- [set3-mask-diagnostic-plan.md](set3-mask-diagnostic-plan.md) →
  [results](set3-mask-diagnostic-results.md): both alternative proxies rescue one
  refusal but change none of 11 control choices. Independently verified; no expansion.
- [set3-rank-calibration-plan.md](set3-rank-calibration-plan.md) →
  [results](set3-rank-calibration-results.md): supervised prior/score blend misses
  declared criteria versus the net chooser. Independently verified; fixed blend closed.
- [set3-cross-amp-diagnostic-plan.md](set3-cross-amp-diagnostic-plan.md) →
  [results](set3-cross-amp-diagnostic-results.md): pooling the three existing amp menus
  misses all declared routing conditions. Independently verified; no amp-selector or
  pooled-score tuning follows.
- [Training-domain audit](research/di-domain-transfer-audit-2026-10-08.md): native
  paired recordings are absent from audited wet supervision; source claims independently
  checked. [Frozen-model transfer pilot](di-domain-pilot-plan.md) →
  [preflight result](di-domain-pilot-results.md): mandatory synthetic NumPy/Torch
  agreement check failed before audio access. Independent numerical-cause review
  precedes any separately declared retry. No neural transfer result or new training.
- [Synthetic metric precision probe](di-domain-metric-probe-plan.md) →
  [results](di-domain-metric-probe-results.md): shared-window interventions pass at
  unchanged 1e-8, independently verified; a separate pilot correction is next.
- [Native-chain pilot attempt 2](di-domain-pilot-v2-plan.md) →
  [results](di-domain-pilot-v2-results.md): both runtime preflights pass; only 3/12
  native pairs pass calibration, so no neural test followed. Independently verified,
  scientific transfer screen inconclusive; closed without changing its rules.
- [Known-DI Morgan control](di-morgan-control-plan.md) → [results](di-morgan-control-results.md):
  verified 72.18% median improvement over processed audio directly, all twelve wins;
  767 independent checks pass. No native/product claim.
- [Fixed-render net versus simple tone correction](di-morgan-flatref-plan.md) →
  [verified result](di-morgan-flatref-results.md): 57.83% median improvement over
  the better simple baseline, all twelve wins; 1,215 independent checks agree.
- [Frozen timing-confidence control](di-alignment-control-plan.md) →
  [verified result](di-alignment-control-results.md): exact-delay/polarity and mismatch
  controls pass; seven accepted distorted cases miss timing by two/three samples.
  All 856 independent checks agree. Next: review fixed-render score sensitivity.
- [Transfer-method source follow-up](research/di-transfer-method-followup-2026-10-08.md):
  published recovery/search and augmentation choices, with explicit synthetic-data
  limits. Research hypotheses only; no new model or training run selected.
  No audio or model-asset access.
- [rerank-plan.md](rerank-plan.md): a DI-free reranker (log-mel, PANNs CNN14) on clean
  PR12. Not passed.
- [tone-encoder-plan.md](tone-encoder-plan.md): our own contrastive tone encoder. It
  passes identification across players (74.5%) but not reranking on real recordings.
- [separator-upgrade-plan.md](separator-upgrade-plan.md) →
  [results](separator-upgrade-results.md): open separators (Mega-53, X-LANCE) and pan
  isolation against htdemucs_6s. About +1 dB SNR; not passed.
- [avg-measure-listening-plan.md](avg-measure-listening-plan.md) →
  [results](avg-measure-listening-results.md): the average-guitar measure, passed 23 of 24.
- [validation-set3.md](validation-set3.md): the heavier-tone set, declared.
- [set3-heldout-use-ledger.json](set3-heldout-use-ledger.json): completed reserved-set
  use, recorded without altering the frozen metadata snapshot; the split is spent.

**Listening tests**
- [declared-listening-runner.md](declared-listening-runner.md): how declared blind tests
  run.
- [listening-objective-scoring.md](listening-objective-scoring.md): predates the judge.
- [heldout-listening-sw50r.md](heldout-listening-sw50r.md): done, inconclusive. Five
  parts ran, where six were needed.
- [prospective-match-validation.md](prospective-match-validation.md): never run. It
  needs a DI the user records, which the product no longer asks for.

**The matching engine and its benchmarks** (historical)
- [tone-matching-plan.md](tone-matching-plan.md): M0–M7 and the set-2 benchmarks, scored
  with the superseded objectives.
- [library-arm-analysis-plan.md](library-arm-analysis-plan.md): scored with v3, so
  unconfirmed.
- [ground-truth-audit-2026-10-03.md](ground-truth-audit-2026-10-03.md): the audit of
  every result to that date. The roadmap lists which of its defects are still open.
- `data/matching/`: M-series, Tone King, atlas, search-signal, RT60 and harmonic
  outputs.
- `data/set2/`: the second validation set's benchmark, pipeline, neutral-start and
  library-arm outputs.

**Research** (`docs/research/`)
1. [round-1-song-only-matching.md](research/round-1-song-only-matching.md): partly run
   under v3.
2. [round-2-full-plugin-estimation.md](research/round-2-full-plugin-estimation.md): not
   run.
3. [round-3-supervised-preset-model.md](research/round-3-supervised-preset-model.md):
   superseded by the supervised-model plan.
4. [round-4-audio-ml.md](research/round-4-audio-ml.md), with its four input reports in
   `research/round-4/`. Its §5 lists the experiments the roadmap draws on.
5. [round-5-guitar-models.md](research/round-5-guitar-models.md): guitar-specific networks, tools
   and separators; what to try next.
