# docs

Start with **[ROADMAP.md](ROADMAP.md)** for current product capabilities, priorities
and validation limits. Keep documentation that explains or supports the plugin's
current behavior; this folder is not an experiment or session archive.

## How this folder is kept

- **Keep durable, relevant information.** Product contracts, operating guidance,
  unresolved limitations, required test fixtures and evidence necessary for a
  shipped claim belong here. Superseded proposals and incidental observations do
  not. Update current guidance instead of adding iterative progress documents.
- **Keep experiment output outside the repository.** Run logs, generated score
  dumps, failure transcripts, agent reviews, handovers and session checkpoints are
  local working material. If an experiment changes a product decision, retain the
  concise conclusion and the minimum evidence needed to support that decision.
- **Declarations are frozen.**
  - [heldout-listening-sw50r.md](heldout-listening-sw50r.md) is pinned by hash in
    code and stays byte-identical.
  - [listening-validation-plan.md](listening-validation-plan.md) is read by code,
    which requires the single trial hash in it, so it isn't edited either.
  - Preserve an existing declaration when a live validation contract depends on
    its bytes. Audit those dependencies before removing or moving old material;
    frozen files are not a reason to accumulate new progress records.
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
- **Do not turn closed studies into new repository archives.** Remove obsolete
  material once its code, fixture, validation and product-document dependencies
  have been checked. A historical citation alone does not justify keeping it.
- **`docs/research/`** is for literature that supports current technical choices.
  Research tooling belongs in the top-level `research/` folder, not among docs.
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

**Settings model and amp choice** (parked)
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
