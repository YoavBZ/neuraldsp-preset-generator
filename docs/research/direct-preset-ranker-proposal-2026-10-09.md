# One next experiment: learn preset risk directly from development song stems

2026-10-09. Source-only proposal for `codex/song-model-continuation`.
**Not a declaration, approval, or permission to execute.** No scientific assets were inspected to prepare this proposal. The output is this repository's `tmp/morgan-next-experiment-design.md`.

## Decision

Prefer **one small, supervised, DI-free preset ranker trained on real development stems and average-guitar distance labels** over EGFxSet intake as the immediate next ML experiment. Its question is:

> Does a simple mapping from a song excerpt's separated guitar spectrum to candidate risk beat both a learned song-blind preset prior and the frozen recovered-DI chooser on other development source groups?

This changes the learning target from reconstructing a waveform to predicting which existing Morgan candidate sounds closer through an average guitar. True DIs are used only in previously computed supervision/evaluation, never in the proposed inference input. Use the existing SW50R development menu only. A useful answer would justify a separately declared broader selection study; it would not ship a model or justify expanded search.

This recommendation is conditional on a metadata admission check establishing the exact allowed development queries, rights, source groups, matching saved labels and multi-guitar coverage below. Those facts have **not** been checked against assets. If admission fails, stop with an operationally blocked proposal; do not automatically substitute a new dataset or a single-guitar-only study.

### Why this question now

- The requested [recovery plan](../docs/di-recovery-plan.md) records development menu headroom from known-DI selection, but does not establish that further waveform training is the right intervention. The reserved confirmation failed on both amps and cannot supply another test.
- The [tone encoder account](../docs/tone-encoder-plan.md) reports strong preset identification on renders followed by failed real-recording selection and hub behavior. Thus another render-identification success would carry little information. This proposal learns the *real-development selection objective* directly.
- The [rank-calibration declaration](../docs/set3-rank-calibration-plan.md) tested a preset prior plus one mixing weight on recovered-DI scores. This proposal takes new information from the native stem's spectrum; it neither extends that grid nor adjusts that closed result. Its prior and recovered-DI comparators are essential to determine whether the new information helps.
- The literature inventories support investigating task-specific, content-resistant objectives and grouped validation. They do **not** demonstrate that the ranker proposed here works. This is a hypothesis, with a low-capacity implementation chosen to make a negative result affordable and interpretable.

## Why defer EGFxSet

The [native-data audit](../docs/research/native-guitar-development-data-2026-10-09.md) documents Clean + TubeScreamer as physical-pedal replay with CC BY 4.0 audio, approximately 903 MB compressed, isolated five-second notes, normalization and two-second fades. Sample correspondence, residual timing, fade placement, original input levels, artifacts and performer/session independence remain unresolved. Five-second files do not satisfy the frozen six-second model procedure; padding, repetition or altered scoring would require a new procedure.

A metadata-first intake is defensible **when the decision is whether to admit that particular pedal corpus**. It could establish release/index identity, label joins, rights and documented edits. It cannot establish waveform pairing, usable unfaded supervision or model transfer. Even successful subsequent pairing QC would show only usable edited pedal-note pairs, with another short-input model procedure still needed. It supplies neither phrases nor simultaneous guitars nor microphone/amp transfer. Accordingly, defer it rather than make it the next ML gate.

The audit's suggestion to act “after fixing” the broader processing control is historical. That experiment is **closed VERIFIED INCONCLUSIVE**, with startup failure before audio. Its missing stages must never be computed. The separate startup checker belongs to another agent and is not a dependency of the proposed ranker, which needs no live plugin. No startup source or implementation was reviewed here.

## Exact proposed experiment

### Admission, queries and the multi-guitar target

Start from the documented **33 set-3 development parts / 11 bands and 45-candidate SW50R inventory** in the calibration declaration. These are documentary counts, not a verified inventory for this experiment. Admit only existing, permitted development stems and matching saved development distance rows. Do not load any waveform recovery checkpoint, render panel, DI, average array or encoder cache for this experiment. No new rendering, separation or model download is planned.

Define one query as **one session and exact absolute excerpt interval**, with one existing instrumental-guitar stem. Deduplicate identical queries before fitting. All excerpts, tracks, reamps and known shared performers/capture families stay in the same outer source group; conservatively merge linked bands. Unknown source relationships block an independence claim. The count of candidate labels or frames is not the independent sample size.

For simultaneous guitars, propose the following explicit product interpretation: **one compromise preset for all documented active guitars in the excerpt**, with equal weight per guitar performance. For a query q, let P(q) be that complete set of active guitar parts. Let d(p,c,B,s) be the existing average-guitar distance for part p and candidate c on half B under band set s. Define query log risk:

`L(q,c,B,s) = mean over p in P(q) of log d(p,c,B,s)`.

For a single guitar, this is the original per-part objective. For several guitars, it measures a single preset's average resemblance across their performances. It is **not** the distance between summed audio, does not require new phase/alignment experiments, and does not promise to recover a particular lead or rhythm tone from an ambiguous mixture. Equal weighting gives a quiet guitar the same target importance as a loud one; that is a proposed product choice, not an established listening preference.

The owner must endorse this target in the later declaration. If the intended product instead requires a specific guitar within simultaneous parts, this experiment needs a different declared target and is not ready to run. Do not silently use a mixture stem to predict several conflicting per-track labels.

Metadata admission must establish identity, permission, grouping and documentary coverage without outcome-based selection. Numeric validity is checked only in the later declared pass:

1. Exact session/time identity and a complete guitar inventory for each proposed query. Existing part annotations alone do not prove all audible guitars have labels. Distances from different absolute excerpts cannot be averaged together.
2. Matching saved half-A/half-B rows, the unchanged average-guitar transform provenance and the exact SW50R menu. Use the existing waveform-lag coordinate; do not compare alternative timing conventions.
3. At least **eight independent source groups overall**, and multi-guitar queries in at least **three** source groups. These are pragmatic minimum coverage rules, not a power calculation. Cap the study at the documented 33 parts / 11 bands; no expansion to reach the minima.
4. Documentary coverage of all 45 half-B labels for every active target part under both band sets. Their actual positive/finite validity can be checked only after declared score access, before fitting. Missing/zero labels are not repaired with epsilon, partial targets or a smaller menu. Failure of this contract closes the declared pass as inconclusive; metadata inspection alone cannot certify it.
5. Source permission for local supervised learning on these recordings and derived labels, plus overlap clearance against permitted training/development metadata. Open-source implementation and local execution do not themselves clear audio rights or authorize publication of weights.

List every original part, grouping, exclusion and reason. Freeze the query manifest before feature or score values are opened. Predeclared missing/silent stems remain queries with a prior fallback; do not delete the hardest product inputs. Target membership and activity must come from existing annotations or a separately approved admission procedure, not a search for favorable scores.

### Features, supervision and one fixed model

Use only the existing htdemucs_6s instrumental-guitar stem's **half A, 1.0–5.5 seconds**. No amp-track input, original DI, half-B audio, song/band identity, candidate ground-truth settings or learned embedding enters the feature vector.

Proposed frontend: 48 kHz mono with an explicitly recorded channel-mean rule; periodic Hann STFT, 2048 samples, hop 480, no centered padding, complete frames only. Sum mean frame power into eight fixed bands with edges **50, 100, 200, 400, 800, 1600, 3200, 6400, 16000 Hz**. Divide each band's power by total power across these bands, then take `10*log10(max(relative_power, 1e-20))`. Define edge-bin ownership as left-inclusive/right-exclusive, with the final edge included. These eight numbers preserve coarse spectral shape and remove overall level. They are not asserted to identify drive separately from playing, pickup or mastering.

Missing, nonfinite or sub-−35 LUFS half-A input takes the training prior. The loudness implementation/version must be pinned; the threshold is a proposal drawn from the existing reranker, not a newly validated boundary. Such queries do not fit the feature mapping but retain labels for fitting the prior and remain in evaluation denominators. Do not tune the threshold after seeing results.

Train only on the **recording** band-set labels. Center each query's 45 log risks by its candidate median: `y(q,c) = L(q,c,B,recording) − median over candidates L(q,*,B,recording)`.

For each outer excluded source group:

- Fit feature means/scales on usable training inputs only. For this fit and the regression, use `w(q) = 1 / (number of groups with usable inputs * number of usable queries in q's group)`. Thus usable groups have equal total weight and fit weights sum to one. Constant feature dimensions become zero, with an explicit record.
- Fit the prior `b(c)` as the equally source-weighted mean of training-query y labels, including fallback queries.
- Fit one **eight-input, 45-output ridge regression** to `y − b`, with no intercept and fixed `lambda = 1`: minimize `sum_q w(q) * sum_c (y(q,c) − b(c) − x(q)W(:,c))^2 + sum_j,c W(j,c)^2` over usable training inputs. No hyperparameter search, extra features, early stopping, seeds or model sizes are selected from results. With no usable training inputs, use the prior and report that fold as unlearned.
- Predict `b + xW` from the excluded group's half-A stem and choose its minimum; exact ties use the frozen lexical candidate ID. Freeze all predictions before opening that group's B labels for evaluation.

There are 360 regression coefficients plus 45 prior values, but only a small number of independent source groups. Candidate-wise supervision does not turn 11 bands into hundreds of independent examples. Strong shrinkage is a deliberate constraint. Failure would close this specific representation/target/model recipe, not prove song-only inference impossible.

### Comparators and evaluation

Use the same admitted queries, menu, grouping and fallback policy for every comparator. All choices use recording-band information; score the **same frozen choices** under recording and union bands.

1. **B-trained prior only**, refitted excluding the outer group. This tests whether the song features add information beyond a good default.
2. **Frozen recovered-DI stem chooser**, using existing `netstem_A` rows only. For multi-guitar queries aggregate log A scores over the matching target rows and minimize over candidates valid for every target. No checkpoint inference or render regeneration.
3. **Frozen flatstem chooser**, by the same aggregation from saved `flatstem_A`.
4. **Template+R**, as the fixed product baseline.
5. **Known-DI half-A chooser**, aggregated from `measure_A`, as an unavailable-at-inference reference; report its half-B score. An optimistic best-B choice is descriptive only and must never influence fitting or selection.

For raw A baselines, a null candidate is unavailable; if no candidate is valid for all target parts, use the same outer-trained prior and report the fallback. A zero/nonfinite numeric A score is a contract failure, not a score to log or repair. Missing entire score sections are an admission blocker, distinct from recorded scientific refusals.

For each rival, report per-query paired differences `L(model,B,s) − L(rival,B,s)`, source-group medians and the median across source groups. Report query and group counts, fallback counts, joint wins, menu-pick concentrations and single-/multi-guitar strata. Repeated development reuse and overlapping outer fits prevent a fresh confirmatory interpretation; no p-value is used as a product guarantee.

**One fixed development progression rule:** under BOTH band sets, the model must have complete chosen-B evaluation, a paired median of source-group medians at most `log(0.95)` against **each** of the prior, netstem and flatstem, and source-weighted joint wins over those three strictly above one half. It must also beat Template+R by that median criterion. Apply the prior/netstem/flatstem criteria again within the multi-guitar stratum; single-guitar medians must not be worse than those rivals. Ties are not wins. Report every comparison, not only the best one.

If multi-guitar coverage is inadequate, the product-facing experiment is blocked. If coverage is adequate but the stratum misses its criteria, the experiment fails progression even if pooled performance improves. A prior-like model, hub collapse, a pass on only one band set or render-identification accuracy earns no follow-up under this declaration.

### Bound and stop rules

- One admitted dataset snapshot, one frontend, one lambda, one menu, at most 11 outer fits. Local CPU only, at most two compute threads, 30 minutes of primary computation and 100 MiB of new feature/result output; these are proposed caps, not measured estimates. A separately implemented verification pass has the same compute/output caps. Neither pass invokes a plugin, separator, cloud instance or network.
- Fail closed on an undeclared path, protected-data linkage, missing rights/provenance, insufficient groups, incomplete target inventory, invalid labels, changed inputs, score-contract failure or leakage. Do not inspect spent reserved files even for overlap checks. Do not call historical loaders that open mixed development/reserved catalogues implicitly.
- On numerical/runtime failure or a cap breach, preserve the attempt and stop as inconclusive. Any repair needs a new declaration and review; no automatic repeat, quiet fallback to another implementation or retrospective subset selection.
- On a valid miss, close this fixed ranker. No lambda sweep, extra features, wider menu, EGFxSet download or additional waveform training follows automatically. On a valid pass, propose a broader study only.

## What the outcome would mean

| Evidence type | What this experiment can establish | What it cannot establish |
| --- | --- | --- |
| Operational readiness | Admitted local inputs, query/label consistency, rights and grouped execution are sufficient for this ranker. | Live Morgan startup/renderability. The other agent's checker remains separate. |
| Transfer / inference evidence | Whether real-development spectral inputs predict average-guitar candidate risk across excluded source groups better than strong existing baselines. | Native DI waveform recovery, original rig/knob identification, pedal-to-mic transfer, or proof of a processing-domain deficit in the closed attempt. |
| Product progress | A pass supports testing a small song-stem-to-menu path, including the expressly defined multi-guitar compromise. | Success on unseen commercial songs, intended-guitar disambiguation, perceptually valid heavy tones, new settings outside SW50R's menu, or a releasable model. |

The route toward the product is explicit: a passing development ranker could later become a local stem-to-factory-preset chooser, with the preset's existing coherent settings exported by the normal preset writer. No predicted DI or new preset search is needed at inference. A broader study must then establish other Morgan menus and realistic mixtures; blind listening must validate heavy tones and the multi-guitar compromise; genuinely fresh reserved material and the owner's decision to spend it are required for accuracy confirmation. None of those later steps is authorized here.

## Alternatives rejected for this next slot

| Alternative | Reason |
| --- | --- |
| EGFxSet metadata intake followed by pedal pairing | Legitimate corpus feasibility work, but several unresolved gates away from the current model and song objective. Defer, without rejecting the dataset permanently. |
| Another phase, timing, padding or short-input microtest | Existing controls already address the cited timing hypotheses; a short-input adaptation would serve isolated notes rather than resolve the immediate song-selection question. |
| Retry/rescue the broader Morgan processing control, or complete missing stages | Explicitly closed before audio. No processing sensitivity conclusion is available to motivate an augmentation recipe. |
| Rescue native P2 or reuse final bothamps | P2 closed with three valid chords and zero scales; final SW50R/PR12 confirmation failed and reserved material is spent. Neither is admissible. |
| More render-only encoder/waveform training or bigger EG-VAE | Render identification already failed to predict native selection success; no newly localized processing weakness justifies scaling. EG-VAE's reported plugin results do not supply native/song evidence or usable weights. |
| A new separator, pan heuristic or lead/rhythm cloud API | The documented separator experiment did not resolve other-guitar contamination; pan coverage is not established here and cloud/API routes violate scope. |
| ToneTwist/Marshall/EGDB-PG acquisition | Rights/upstream conflicts or plugin-generated repeated performances, plus acquisition cost, prevent a cleaner immediate native/song answer. No new corpus is needed for the proposed hypothesis. |
| Continuous knob regression, surrogate inversion or wider search | Enlarges a problem whose current menu still has documentary headroom; exact knobs are not the average-guitar target. |

## Required steps before any execution

These are future prerequisites, **not actions performed or permission granted by this report**.

1. **Target decision and source admission.** Endorse the multi-guitar compromise, or stop this design. Under a separately bounded metadata-only scope, inspect only allowlisted development provenance/rights and session/time/group metadata; verify inventory completeness, source-family grouping, stem paths, score schema/provenance and the coverage minima. Do not open score values, audio, caches or weights at this step. If current metadata cannot answer a required fact, record the missing source rather than infer it. A reader that necessarily opens protected catalogue content must be replaced with a filtered development-only export supplied by an authorized owner.
2. **Concrete declaration.** Write a new development-only protocol and query/candidate/path manifest with exact IDs, hashes/version evidence, approved audio-use scope, group assignments, fallback reasons, feature/loss equations, regularization, bands, intervals, baselines, all gates, resource caps and failure handling. Take expected asset hashes from authorized existing provenance; fresh byte checks occur only after scientific access is authorized. Missing expected identity evidence blocks this declaration rather than permitting an undeclared asset read. A reviewed read-barrier must authorize later access to the exact development stem bytes and score rows, with no directory-wide scanning. Pin the old average-guitar label provenance rather than regenerate its target or change its lag. No live-plugin readiness requirement is introduced.
3. **Source implementation.** Add a dedicated minimal ranker/runner, a development-only metadata resolver and an independent verifier. Reuse concepts from `learn/phase2_set3.py`, `learn/set3.py` and `analysis/aligned.py`, but do not invoke their broader loaders/scorers. In particular, do not call `set3.parts()` without an explicit development filter, load global mixed-split indexes, call `fold_average`, or rerun phase-2 scoring. Existing functions' presence is not proof that their import/load paths satisfy this study's read boundary. Record exact baseline row keys and refuse regeneration.
4. **Synthetic tests only before scientific access.** Test protected/mixed-split and symlink/path rejection; same-source query merging; no duplicate weighting; missing multi-guitar target rejection; exact interval joins; all-target candidate validity; half-A feature isolation; outer labels/features excluded from preprocessing/prior/fit; changing outer B leaves every fitted quantity and pick unchanged; group weighting; octave-bin boundaries and gain invariance; silent/missing-input prior fallback; ridge solution and lexical ties; zero/null contracts; identical choices under both evaluation band sets; denominators, gates, cap/failure retention and exclusive output creation. These check the new implementation, not phase/timing sensitivity. No real-science function is executed merely by importing tests.
5. **Fresh independent review and committed declaration.** A fresh-context reviewer checks the final target, admission evidence, rights, source, synthetic tests, math, protected-data boundary and reporting against this design. Resolve findings before computation and commit the reviewed protocol/implementation/manifest on the feature branch. Use the user-owned `neuraldsp-safe` helper for future tracked Python/pytest/staging/commit operations. This turn performs none of them. The owner must authorize this new experiment; earlier autonomous work does not turn this proposal into execution permission.
6. **One primary pass, then independent verification.** Only after those prerequisites, run the fixed experiment within its caps. The verifier independently derives features, ridge solutions, predictions, baselines, grouping weights and gates from the admitted development inputs, freezes its derivation before comparing primary outputs, and checks read/write boundaries and input stability. Merely replaying primary code is insufficient. This study inherits the saved distance labels and their earlier verification; it does not independently remeasure their scientific validity or the average-guitar metric. Preserve disagreements and failed attempts; no pass is claimed before they are resolved under an approved procedure.

## Source trail and unresolved facts

Read all four requested documents. Relevant additional reads were the roadmap, tone-encoder and rank-calibration declarations/accounts, published-method inventories (rounds 3–5), and the source of `learn/rerank.py`, `learn/phase2_set3.py`, `learn/set3.py` and `analysis/aligned.py`. Source establishes available interfaces and intended schemas; it does not establish current asset availability, legal admission, complete multi-guitar annotations or correct checkpoint lineage.

Published findings are carried forward from those reports, not newly verified on the web today. Primary references recorded there include [EG-VAE](https://arxiv.org/html/2608.05513), [Okita and Katayose](https://arxiv.org/html/2604.22276), the [EGFxSet paper](https://archives.ismir.net/ismir2022/latebreaking/000006.pdf), [release 7044411](https://zenodo.org/records/7044411) and [mirdata loader](https://mirdata.readthedocs.io/en/stable/_modules/mirdata/datasets/egfxset.html). They motivate questions; none validates this ridge frontend, lambda, compromise objective, sample minima or progression margins. Those are expressly proposed design choices.

Facts needing further sources before declaration: current permitted development/audio-training rights; exact candidate/score snapshot identity; complete concurrent guitar/time mappings; source/performer/capture-family independence; shared-query stem identity; saved baseline row coverage; existing separator provenance/weight permission; and training-only lineage of the frozen average used in the labels. Do not infer them from filenames or from documentary counts. No new external method or dataset claim is required to propose the experiment.

No on-disk root AGENTS.md was present; the supplied AGENTS instructions were followed. The current branch was read as `codex/song-model-continuation`. No scientific computation, scientific asset/audio/model/cache/index/CSV/score-file read, download, training, instance operation, source edit, commit, startup-checker review or other-agent work was performed. The only created file is this proposal.
