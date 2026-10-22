# docs

Start with **[ROADMAP.md](ROADMAP.md)**: where the product is, what comes next, and the
decisions so far. It is the one living plan; what it superseded (the product steps' history,
and the song-to-preset model's as it stood on 2026-10-19) is in
[roadmap-history.md](roadmap-history.md). Everything else here is a record: what
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
- [judge-spec.md](judge-spec.md): the properties any judge version must have, each tested
  (`tests/test_judge_spec*.py`); the current judge breaks five, v2 three.
- [judge-v3-plan.md](judge-v3-plan.md) → [results](judge-v3-results.md): judge v3, a
  floor from both sides in hearing's units; holds all 18 spec properties, keeps every
  standing comparison's sign, changes about half the picks. Adoption waits for listening.

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
- [generate-routing-plan.md](generate-routing-plan.md), with its part list and run map
  → [results](generate-routing-results.md): **routing costs** (clean parts sent to
  crunch by genre or song-level write-ups; `generate` now installs the neighbouring
  starting point too); research edits undecided.
- [generate-routing-recheck-plan.md](generate-routing-recheck-plan.md) →
  [results](generate-routing-recheck-results.md): **the new routing rule helps**
  (−0.081 against the old skill, in-sample).
- [starting-preset-listening-plan.md](starting-preset-listening-plan.md), with its
  part list → [results](starting-preset-listening-results.md): **heard** (17 of 21,
  in-sample, one listener).
- [clean-start-breakup-results.md](clean-start-breakup-results.md): on the open-chord
  riff, the SW50R and AC20 clean baselines break up but play clean turned down; the PR12
  ones are clean or borderline (one listener, not blind; a linearity measure agrees).
- [clean-start-volume-listening-plan.md](clean-start-volume-listening-plan.md) →
  [results](clean-start-volume-listening-results.md): on 13 real clean parts, the
  turned-down AC20 start was closer (9 of 12, weakly: 4 of 7 without bleed), SW50R's not (5 of
  11), PR12 mostly can't tell (blind trials, one listener).

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
  headroom on all three amps; independently verified. *Review: ranking works with the true
  DI; by mean the rebuilt DI loses about 0.16 (SW50R) to 0.24 (PR12).* No reserved-data reuse.
- [set3-mask-diagnostic-plan.md](set3-mask-diagnostic-plan.md) →
  [results](set3-mask-diagnostic-results.md): both alternative proxies rescue one
  refusal but change none of 11 control choices. *Review: adopt the reference-proxy
  fallback ([review](codex-continuation-review.md)).*
- [driven-baseline-results.md](driven-baseline-results.md): a fixed driven factory preset
  per amp beats the clean template on every reserved crunch and high-gain part (SW50R,
  PR12), and loses on clean parts. `generate` now starts distorted Morgan parts from it.
  Fallback for judge refusals through a rebuilt DI: `learn/rebuilt_judge.py`.
- [set3-gap-split-plan.md](set3-gap-split-plan.md) → [results](set3-gap-split-results.md):
  where the rebuilt DI loses the preset choice. The rest of the waveform accounts for 87%
  of the gap, level 13%, the mask 0; matching the long-term spectrum hurts.
- [di-network-v2-plan.md](di-network-v2-plan.md) → [results](di-network-v2-results.md):
  neither longer training nor set 3's guitars moved the picks. Every DI network so far
  had its bottom levels dead (a shut GLU gate, 86% of the weights).
- [rebuilt-di-lowpass-plan.md](rebuilt-di-lowpass-plan.md) →
  [results](rebuilt-di-lowpass-results.md): cutting the rebuilt DI above 3 kHz misses
  the bar by 0.0009 (−0.049, 23 better and 5 worse); adopted by the user's decision.
- [di-network-v3-plan.md](di-network-v3-plan.md): repairing the network's bottom levels.
  Both pre-checks failed; training learns to ignore the bottom either way.
- [sim-real-gap-plan.md](sim-real-gap-plan.md) → [results](sim-real-gap-results.md):
  real rooms and mics are not the lever. The rebuild is less coherent with the true DI
  than its own input, so the training loss is.
- [set3-rank-calibration-plan.md](set3-rank-calibration-plan.md) →
  [results](set3-rank-calibration-results.md): supervised prior/score blend misses
  declared criteria versus the net chooser. *Review: rebuilt-DI scores carry about 0.2 of
  song-specific information over the best song-blind prior; re-weighting adds nothing.*
- [set3-cross-amp-diagnostic-plan.md](set3-cross-amp-diagnostic-plan.md) →
  [results](set3-cross-amp-diagnostic-results.md): pooling the three existing amp menus
  misses all declared routing conditions. Independently verified; no amp-selector or
  pooled-score tuning follows.
- [Training-domain audit](research/di-domain-transfer-audit-2026-10-08.md): native
  paired recordings are absent from audited wet supervision; source claims independently
  checked. [Frozen-model transfer pilot](di-domain-pilot-plan.md) →
  [preflight result](di-domain-pilot-results.md): mandatory synthetic NumPy/Torch
  agreement check failed before audio access. Independent numerical-cause review
  led to the separately declared correction below. No neural transfer result or new training.
- [Synthetic metric precision probe](di-domain-metric-probe-plan.md) →
  [results](di-domain-metric-probe-results.md): shared-window interventions pass at
  unchanged 1e-8, independently verified; the separate pilot correction is complete below.
- [Native-chain pilot attempt 2](di-domain-pilot-v2-plan.md) →
  [results](di-domain-pilot-v2-results.md): both runtime preflights pass; only 3/12
  native pairs pass calibration, so no neural test followed. *Review: the calibration
  was mis-specified and the pairs are fine. Native transfer is untested, not
  inconclusive ([review](codex-continuation-review.md)).*
- [Known-DI Morgan control](di-morgan-control-plan.md) → [results](di-morgan-control-results.md):
  verified 72.18% median improvement over processed audio directly, all twelve wins;
  767 independent checks pass. No native/product claim.
- [Fixed-render net versus simple tone correction](di-morgan-flatref-plan.md) →
  [verified result](di-morgan-flatref-results.md): 57.83% median improvement over
  the better simple baseline, all twelve wins; 1,215 independent checks agree.
- [Frozen timing-confidence control](di-alignment-control-plan.md) →
  [verified result](di-alignment-control-results.md): exact-delay/polarity and mismatch
  controls pass; seven accepted distorted cases miss timing by two/three samples.
  All 856 independent checks agree.
- [Fixed-render score sensitivity](di-timing-sensitivity-plan.md): independently
  reviewed and committed before scoring. [Verified result](di-timing-sensitivity-results.md)
  passes all tested offsets; 23,734 independent checks agree.
  Tests common output offsets, not model-input timing.
- [Known model-input shifts](di-input-shift-control-plan.md): independently reviewed
  and committed before access. Both replay controls pass, including twelve exact
  predictions. [Verified PASS](di-input-shift-control-results.md) at all four shifts;
  21,246 final comparison checks agree, with exact prediction bytes.
  Next: separately reviewed processing diversity; no native/product claim.
- [Fixed periodic phase control](di-phase-control-plan.md): reviewed and committed
  before access. All replay/construction controls pass; [verified PASS](di-phase-control-results.md)
  has twelve wins and 57.56% median improvement. All 15,976 independent checks agree; this study is closed.
- [Broader Morgan processing control](di-morgan-processing-control-plan.md): reviewed
  and declared before execution. [result](di-morgan-processing-control-results.md): *review: void, because Codex's sandbox
  cannot see AU components, so the study never ran;*
  all 235 independent checks agree. Replay controls pass; startup failed before
  audio, so no broader result exists. Closed with full failures and evidence.
- [Next development steps](di-recovery-plan.md#next-development-steps-2026-10-09):
  separate [startup/version/shutdown readiness](morgan-au-startup-plan.md) is
  [READY](morgan-au-startup-results.md), Morgan 1.1.1 with clean logs/process exit0.
  Reviewed and committed before execution; no audio/preset/model access. Cannot
  establish rendering or reopen the processing attempt. Check new study feasibility next.
- [Direct preset-ranker proposal](research/direct-preset-ranker-proposal-2026-10-09.md):
  source-only alternative using real development stems and saved average-guitar
  labels. Not declared; metadata admission, complete guitar targets and target
  interpretation remain unresolved. Its proposed equal-weight compromise is not adopted.
- [Different-equipment development data audit](research/native-guitar-development-data-2026-10-09.md):
  EGFxSet is a conditional hardware-pedal feasibility candidate; pairing and
  recording quality remain unverified. ToneTwist external amp releases have
  unresolved upstream/repack rights. No audio downloaded or new study declared.
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
- [fixed-level-rescore-results.md](fixed-level-rescore-results.md): past choices re-scored
  under the fixed-level measure and band-clustered statistics. The 3 kHz cut helps
  (−0.07); the edge over a fixed preset (−0.14) is a forked development lead.
- [underdrive-trim-plan.md](underdrive-trim-plan.md) → [results](underdrive-trim-results.md):
  playing the rebuilt DI quieter halves the under-drive but doesn't improve picks; futile.
- [judge-v2-plan.md](judge-v2-plan.md) → [results](judge-v2-results.md): a fixed band set
  for the judge; half of its stronger result is a masking-floor artefact.
- [di-loss-plan.md](di-loss-plan.md): a waveform-keeping training loss; the pre-check failed
  (no gain in coherence, worse spectrum).
- [toneking-baseline-plan.md](toneking-baseline-plan.md) →
  [results](toneking-baseline-results.md): **adopted.** Fixed Tone King factory presets
  per gain class, made dry: Vintage Trem for clean (about 12% closer than the plugin's
  Default on held-out parts) and Squishy Lead for crunch (thin evidence, 3 bands).
- [set5-test-plan.md](set5-test-plan.md) → [results](set5-test-results.md): on fresh set-5
  bands the corrected network picks better than the old one (crunch, fragile); it only
  matches `generate`'s crunch start.
- [validation-set5.md](validation-set5.md): set 5, a fresh held-out set (7 new bands; first
  use by the set-5 test).
- [validation-set6.md](validation-set6.md): set 6, MedleyDB, held out and unused. MedleyDB
  names no DI, and no automatic DI-role rule held up (amendment 1). The user then labelled
  DIs by ear, and a validation round passed (amendment 2). That gives **5 parts**: 3 crunch
  in scope (Little Tybee, and Port St Willow ×2) and 2 high-gain report-only. No clean DI.
  35 of its 73 songs are in MUSDB18's train subset (HTDemucs's training data) and are
  marked. For a stem test, only Little Tybee is in scope.
- [residual-di-plan.md](residual-di-plan.md) → [results](residual-di-results.md): the MPS
  gradient bug (every DI network trained on a corrupted spectral gradient) is fixed. The
  corrected network picks better, marginally and on crunch only (the second seed
  didn't confirm it: under-powered). A residual pass-through network is futile.
- [knob-ceiling-plan.md](knob-ceiling-plan.md) → [results](knob-ceiling-results.md): the first
  measurement of *generating* settings rather than ranking the menu. By the judge, on
  development and with the true DI, a knob search beats the best menu preset by about 19%
  (14/14 bands), plus 8% from the EQ. The gain is part-specific, and a blind check (one
  listener) chose the search on 7 of 7 trials. Lower bounds.
- [cprime-folds-plan.md](cprime-folds-plan.md) → [results](cprime-folds-results.md) (ML plan
  step 1): C′ for folds 0, 1 and 3. All three pass the network check (audited).
- [knob-ceiling-2-plan.md](knob-ceiling-2-plan.md) → [results](knob-ceiling-2-results.md) (step
  2): pedals add a little, consistently; time effects are kept only when they clearly help;
  an effect left off on a dry record is correct.
- [label-table-plan.md](label-table-plan.md) → [results](label-table-results.md) (step 4):
  menus and stems for 59 clean and crunch development parts.
- [song-settings-plan.md](song-settings-plan.md) → [results](song-settings-results.md) (step 3):
  against the starting preset, the true-DI search gets −0.269, arm A (rebuilt-DI search)
  −0.078, and arm B (a settings model) +0.035. Audited; the audit artefacts are in
  [audits/song-settings-control-2026-10-15](audits/song-settings-control-2026-10-15/README.md).
- [arm-a-levers-plan.md](arm-a-levers-plan.md) → [results](arm-a-levers-results.md): arm A's
  current best is a 52-render search shrunk halfway to S (−0.083 [−0.135, −0.032]); the declared
  rule chose the unshrunk search, and the shrink is the user's judgement call. The rebuild has no
  usable local ranking near S. Artefacts are in
  [audits/arm-a-2026-10-16](audits/arm-a-2026-10-16/README.md).
- [arm-a-listening-plan.md](arm-a-listening-plan.md) → [results](arm-a-listening-results.md): one
  listener chose arm A's current best over S on 4 of 4 trials where a difference was heard.
- [ks-ceiling-extend-plan.md](ks-ceiling-extend-plan.md) → [results](ks-ceiling-extend-results.md):
  the true-DI search continued to a stop reaches −0.293 [−0.378, −0.207] against S (from −0.269),
  with 17,550 extra renders; arm A's share becomes 27%.
- [local-objective-plan.md](local-objective-plan.md) → [results](local-objective-results.md):
  what makes the song-only objective rank nearby settings. Experiment 1: the DI and stem errors
  partly cancel, single fixes undecided. 1b: a perfect separator feeding the rebuild and the
  reference closes about 44% of the gap. 1c: on the instrumental context, Mega-53 recovers about 43% of 1b's gain. 1d: the
  separator-robust C′ in the rebuild gives no gain (−0.127 [−0.256, +0.003] on the htdemucs stem,
  −0.051 [−0.166, +0.065] on Mega-53); C′ stays.
- [arm-a-mega53-plan.md](arm-a-mega53-plan.md) → [results](arm-a-mega53-results.md): arm A with
  Mega-53 against htdemucs. On fresh full mixes Mega-53 leans better, a tie (−0.017 [−0.039,
  +0.004]), so htdemucs stayed then (Mega-53 is the ML default since 2026-10-19). Arm A's recipe on fresh full mixes reads −0.028 [−0.064, +0.008]
  against S (−0.083 on the reused development parts). 30,102 renders.
  Amendment 2: a perfect DI alone gains nothing (+0.040 against H). Amendment 3: perfect separation
  (the amp track as target and rebuild source) gains −0.066 [−0.090, −0.042] over H, and the true DI
  on top a further −0.080 (ZT − S −0.174); 13,986 renders.
- [stereo-and-mix-check-plan.md](stereo-and-mix-check-plan.md) → [results](stereo-and-mix-check-results.md):
  Mega-53 becomes the ML default. Stereo: centred targets lose nothing to the mono fold, and on a
  panned model the target's own channel gains +1.6 dB while a blind estimate gains +0.3. Our mixes
  are unity sums, so the in-song guitar is the raw track; no session ships a master. Zero renders.
- [mix-previews-results.md](mix-previews-results.md): the released mixes of 10 songs and
  Sound On Sound's remix of Signs use the same takes as our multitracks (Signs is "partial" from
  repeated sections, not edits). All 17 stage F crops there are covered. Mega-53 on the real mix
  loses 0.62 dB SNR against the raw track (0.31 with a per-stem lag; single tracks are shifted, and
  some flipped, in the real mix). In SNR, mastering adds little. Zero renders.
- [separation-finetune-plan.md](separation-finetune-plan.md) → [Step 0 results](separation-step01-results.md): how to improve target-guitar
  separation. Zero-render ceilings first (the class ceiling and free test-time fixes), then an
  oracle class arm in arm A (about 7k renders) decides between fine-tuning Mega-53's class head
  and a conditioned one-guitar separator; MPS training needs the loss off the device. Training
  cancelled, then allowed again the same day (user, 2026-10-20): fine-tuning or adapting an
  existing separator on this Mac is fine; a newly trained separator and rented machines are not.
- [xlance-screen-plan.md](xlance-screen-plan.md) → [results](xlance-screen-results.md): X-LANCE
  against Mega-53 fast as the build's separator (zero renders). The full chain: same SNR, mel-range
  LSD −1.82 dB, 1.78× the CPU time (pass, over budget). Amendment 1, gtr_mss alone: same SNR,
  mel-range LSD −2.30 dB, 1.01× the CPU time; pending MPS timing.
- [stereo-side-plan.md](stereo-side-plan.md) → [results](stereo-side-results.md): the pan side
  as a separation hint, on synthetic pans of stage F (zero renders). With the side known, keeping
  the target's channel of a stereo Mega-53 stem gains +1.50 dB at ±0.6 pan, and the MDX23C centre
  model gains +1.35 on a centred lead against hard-L/R rhythms. Neither reaches the +2 dB step (a
  gain to build on). Blind side picks follow the louder other guitars and lose; the ILD mask and
  Wiener don't help. Audited.
- [rebuild-gap-plan.md](rebuild-gap-plan.md) → [results](rebuild-gap-results.md): where C′'s
  rebuild loses ranking with a perfect stem. A structured short-time magnitude error, mostly above
  2 kHz; phase and rotation are minor. A fixed EQ (`dep_eq`, +0.133 [−0.009, +0.276]) and a
  ranking-trained rebuild (`rank`, +0.075 [−0.031, +0.182] against C′) lean better; `rank` seems to act as a
  learned long-term EQ (post hoc), and neither reduces the short-time treble error. 18,981 renders.
- [rebuild-tone-plan.md](rebuild-tone-plan.md) → [results](rebuild-tone-results.md): a C′
  fine-tune with an offset-removed 2–8 kHz short-time magnitude loss (`stm`), a leak-free long-term
  EQ and a second seed of `rank`. `stm` lowered its target error on every part, with no measurable gain in
  rendered ranking (+0.012 [−0.023, +0.047]; on top of the EQ −0.012); the leak-free EQ (+0.132 [−0.030,
  +0.294]) and `rank`'s second seed (+0.099 [−0.036, +0.233]) lean positive, undecided. Next
  proposed: an oracle dose probe of the short-time component. 8,280 renders. Audited.
- [dose-probe-plan.md](dose-probe-plan.md): an oracle dose probe on top of the leak-free EQ:
  25/50/100% of the true offset-removed short-time magnitude in 2–8 kHz, the full-band true
  magnitude (one resynthesis, or Griffin–Lim) and a time-shifted control, with the long-term
  balance held. Does the short-time magnitude carry the remaining half of the gap, and which E_st
  cut matters? → [results](dose-probe-results.md): the full-band field (one resynthesis, C′'s
  phase) recovers 0.74 [0.50, 0.86] of what the EQ leaves (+0.116 [+0.045, +0.187]); 2–8 kHz on
  E_st's mask only 0.25 (+0.039), below it; Griffin–Lim adds nothing; dose shape and control
  undecided. Option 2 only as a full-band head, ceiling `full100`, gated on a full-band error.
  7,448 renders. Audited.
- [audits/dose-stop-2026-10-18.md](audits/dose-stop-2026-10-18.md) → [audits/start-transient-2026-10-18.md](audits/start-transient-2026-10-18.md):
  why the dose probe stopped (a render after a change of plugin state starts louder for about 4 s),
  then eleven render scripts checked for it. No audited merged decision changes (arm B and
  DI-recovery scripts not yet audited); part C is exposed but
  probably harmless. Rule: a discarded priming render after any process start, amp or DI change.
- [multi-section-plan.md](multi-section-plan.md) → [results](multi-section-results.md): every
  10-s section where the guitar plays, not one crop. Step 1 (zero renders): 507 sections on 38
  development parts, about 13× the audio of one crop each. Step 2 (true DI, 19 parts, 10 bands):
  fitting three sections at once carries a little better to held-out sections than fitting one
  (−0.018 [−0.030, −0.005]) at more renders; at equal renders not shown; one section keeps about
  0.87 of its gain elsewhere in the track; the tone curve tracks where sections disagree, most on
  Cambridge. 21,647 renders. Audited.
- [cprime-sep-plan.md](cprime-sep-plan.md) → [results](cprime-sep-results.md): C′ fine-tuned on
  separator residuals; a small envelope gain, inside the noise on stems and as large on the amp
  track (zero renders).
- [clean-di-library-plan.md](clean-di-library-plan.md) → [results](clean-di-library-results.md): a
  screened library of the development DIs (237 DIs; hum, hiss, clipping, dropouts, bleed, DC and
  near-silence per 10-s section; zero renders; 134.7 clean minutes after amendment 3's hum rule),
  two blind listening checks of the screens, and part
  B, known-answer test songs rendered through chosen presets (declared; renders later).
- [known-answer-b1-plan.md](known-answer-b1-plan.md) → [results](known-answer-b1-results.md): part
  B's pilot B1, four known-answer songs (Heather Jane, Bourbon, Collide With Me, Still Flyin')
  rendered through drawn presets and mixed back, arm A's recipe scored against the exact truth. The
  pipeline is exact; arm A against S +0.001 [−0.523, +0.524] over 3 bands, undecided, the spread
  driven by Heather Jane; B2 proposed at the pool's cap (up to 4 fresh songs). 17,290 renders.
  Audited.
- [pretrain-set-plan.md](pretrain-set-plan.md) → [results](pretrain-set-results.md): part C, a
  labelled pre-training render set from the clean DI sections (Morgan, clean to crunch, record-like
  mixes built at training time), sized by a learning-curve pilot. On true mixes of held-out bands
  the knob error flattened between 20k and 40k (Δ +0.0012 [−0.0020, +0.0045]): STOP, no
  extension; the guitar alone and training-style mixes still improve. In-domain, not real-song.
  43,060 renders, 3.68 GB. Audited.
- [direct-existing-plan.md](direct-existing-plan.md) → [results](direct-existing-results.md): part C's
  existing 40k models scored on stage F without training (D − S +0.033 [−0.053, +0.119], a tie
  leaning worse), and the judge re-run through the raw DI (rebuilt-DI contrasts unchanged; on the
  known-answer songs the measure DI caps the exact truth at 0.55 of S). 852 renders. Audited.
- [direct-model-stems-plan.md](direct-model-stems-plan.md) → [gate 1 results](direct-model-stems-gate1-results.md), [pilot results](direct-model-stems-pilot-results.md), [steps 3–4 results](direct-model-stems-results.md): the direct model with realistic stems
  (declared, reviewed). Cheap checks on D_existing first (does the stem's quality move its answers;
  what the mismatch costs; 111 descriptive renders), then a 5k pilot of real Mega-53 stems against a
  mix-only model and the old recipe, then one test on stage F (D − S primary, about 321 renders).
  Amendment 2 (2026-10-21): the full build, step 3 and step 4 use X-LANCE gtr_mss stems; disk is
  no longer a block.
  **Gate 1 (2026-10-20, zero renders): GATE1 STEM**; the stem matters (Mega-53's stem costs +0.104
  of E against the training stem); the mix adds little behind a clean or separated stem, so a
  stem-only model is recommended. Audited.
  **Pilot (2026-10-21, no judged renders): PILOT STEM.** The stem-only model beats the old
  recipe (R_out −0.0127 [−0.0216, −0.0039]), but every pilot model is still worse than a
  per-class constant predictor. A learning curve (−0.017 per doubling on average; the seeds differ
  widely) projects the full model near the constant (PROBE CONTINUE). Not yet audited.
  **Amendments 5 and 6 (approved 2026-10-22, before any step 3 data):** step 3 reads each knob's
  mixture median, averaged over 3 seeds × 2 halves and pulled toward the per-class constant; the
  right cab's silent knobs leave E, and the E check is descriptive. A sound-based gate (D's preset
  against the constant's, rendered and judged against the true preset on R_in, about 5.9k renders)
  decides step 3, and step 4 runs only on GATE OK. Step 3's training follows the X-LANCE build.
  **Amendment 7 (2026-10-22, user):** the gate read GATE STOP (−0.1538 [−0.3360, +0.0284],
  power about 46%); step 4 runs anyway, unchanged, labelled "run under a user override of a GATE STOP".
  **Steps 3 and 4 (2026-10-22; step 4 run under a user override of a GATE STOP): STEP4 NOT
  SHOWN.** D − S on stage F −0.034 [−0.103, +0.034], 12 bands (clean leans better, crunch worse).
  The new model clearly beats the old one (D − D_existing −0.067 [−0.113, −0.021]) and is
  indistinguishable from arm A's search (D − H −0.006 [−0.062, +0.050]; not shown equivalence)
  at zero renders. 321 renders. Audited.
- [record-match-listening-plan.md](record-match-listening-plan.md) → [results](record-match-listening-results.md):
  a blind check of the judge by ear on 5 guitar-exposed parts: the ear broadly agrees with the
  judge's order (Spearman mean 0.8), the ceiling C is heard closest in 4/5, H beats S in 4/5, D
  third. 775 renders. Audited.
- [shrink-snr-judge-v3-results.md](shrink-snr-judge-v3-results.md): two zero-render checks from
  stored data. The best shrink does not measurably depend on stem SNR (a rule by SNR gains −0.003
  [−0.013, +0.007] on held-out bands, nothing on realistic stems; the clear shrink cost is with the
  true DI and a perfect target). Judge v3, re-scored on the record-match clips, agrees with the ear
  a little less than the default judge (Spearman 0.64 against 0.80). Audited.
- [bleed-listening-plan.md](bleed-listening-plan.md) → [results](bleed-listening-results.md), with
  the [bleed audit](audits/bleed-2026-10-16/README.md): bleed only in the Telefunken live-room
  sessions, audible on the high parts; the cleaning isn't adopted, and every key result holds
  without bleed.
- [data-quality-audit.md](data-quality-audit.md) (draft, 2026-10-22; evidence in
  [audits/data-quality-2026-10-22](audits/data-quality-2026-10-22/)): zero-render audit. A median
  45% of a training or V_sep stem's power is not the labelled guitar, and it costs on the sound
  gate (+0.103 [+0.055, +0.156] log d, high against low third, within band). No DI is paired
  with the wrong amp track. The targets' dirt is Telefunken live-room bleed. Proposes a
  clean-versus-random retrain first.
- [song-to-settings-diagnostics-plan.md](song-to-settings-diagnostics-plan.md) →
  [results](song-to-settings-diagnostics-results.md): arm B has signal on renders but hedges
  toward mid-range on records.
  [song-to-settings-soundspace-plan.md](song-to-settings-soundspace-plan.md) →
  [results](song-to-settings-soundspace-results.md): the sound-space retrain (B2) beats the old
  arm B on songs but isn't shown to beat S; arm B is paused.
- DI-recovery track:
  - [separator-screen-plan.md](separator-screen-plan.md) → [results](separator-screen-results.md):
    separation halves the margin but rarely flips it;
  - [rank-margin-ladder-plan.md](rank-margin-ladder-plan.md) →
    [results](rank-margin-ladder-results.md): C′'s error is fine structure, and the margin is
    only a screen;
  - [di-fine-structure-plan.md](di-fine-structure-plan.md) →
    [results so far](di-fine-structure-results.md): fixes gap fill and treble, but no steering
    gain shown.
- [render-order-audit.md](render-order-audit.md): reused Morgan renders carried the previous
  render at hiss level until `isolate`. No decision overturned; set 5's C′-over-C is fragile
  (inconclusive if the at-risk parts are dropped).
- [audit-2026-10-11.md](audit-2026-10-11.md): an adversarial audit of the ML negatives.
  No calculation errors; the sound translator and the DI-network route are undecided,
  not failed; the 3 kHz cut hurts on clean and is off there.
- [sound-desc-plan.md](sound-desc-plan.md) → [results](sound-desc-results.md): predict
  the sound, not the knobs. With the same notes a sound description picks crunch presets
  well. A translator trained on plugin renders is undecided on real records: level with
  the DI chooser counting each band once, pulled down by one song (see the audit).
- [crunch-baseline-plan.md](crunch-baseline-plan.md) → [results](crunch-baseline-results.md):
  crunch starting presets per amp, lighter than the driven ones, are adopted on weak
  evidence (7 parts, 3 bands). The ML chooser over them is not shown (−0.056).
- [heavy-listening-plan.md](heavy-listening-plan.md) → [results](heavy-listening-results.md):
  a reliable listener (3/3 hidden references, 3/3 repeats). Tonal against temporal:
  neither. Clear heavy pairs: 5 of 6 with the judge, inconclusive. 9 trials were
  unanswerable: low-tuned guitars' low notes broke up in both menu presets.
- [clean-baseline-plan.md](clean-baseline-plan.md) → [results](clean-baseline-results.md):
  **confirmed.** Fixed clean factory presets per amp, chosen on development, land about
  12% closer than the clean template on held-out clean parts. `generate` now starts
  clean Morgan parts from them, and the chooser is not shown to add to them on clean
  parts (exploratory).
- [songs-check-plan.md](songs-check-plan.md) → [results](songs-check-results.md): from a
  separated stem the chooser keeps 75% of its amp-track gain (−0.114 against the starting
  preset, development).
- [set4-confirmation-plan.md](set4-confirmation-plan.md) →
  [results](set4-confirmation-results.md): **confirmed** on fresh bands. The rebuilt-DI
  chooser is about 8% closer than `generate`'s starting preset on clean and crunch parts
  (clean carries it), and harmful on high-gain.
- [closeness-review-2026-10-10.md](closeness-review-2026-10-10.md): a deep, four-part review
  of how closeness is measured. The judge is treble-deaf on parts with a dominant low end;
  the measure's DI level is a recording artefact; the "unbeaten fixed preset" verdict
  depends on the judge's weighting; the pooled p-values were overconfident.
- [heavy-listening-plan.md](heavy-listening-plan.md): listening check H, declared: on
  heavy tones, does the ear follow the judge's tonal or temporal part, and does the
  judge hold on SW50R and AC20.
- [codex-continuation-review.md](codex-continuation-review.md): what holds and what
  doesn't in the Codex continuation (held-out confirmation, diagnostics, pilots). Read
  this before any Codex results doc. Large evidence files are kept outside git
  ([EVIDENCE-OUTSIDE-GIT.md](EVIDENCE-OUTSIDE-GIT.md)).
- [validation-set3.md](validation-set3.md): the heavier-tone set, declared.
- [set3-heldout-use-ledger.json](set3-heldout-use-ledger.json): completed reserved-set
  use, recorded without altering the frozen metadata snapshot; the split is spent.
- [validation-set4-plan.md](validation-set4-plan.md) → [validation-set4.md](validation-set4.md):
  fresh held-out confirmation set, unused. 9 new bands (4 via the Internet Archive,
  amendment 1), 35 parts, all held out.
- [validation-set5.md](validation-set5.md): fresh held-out set, unused. 7 new bands
  with kept parts (14 sessions tested), 31 parts, all held out. 26 clean or crunch parts
  are in scope; 5 high-gain parts are report-only.
- [validation-set6.md](validation-set6.md): MedleyDB, held out and unused. 73 songs
  tested. Amendment 1: no DI-role rule passed its development calibration. Amendment 2:
  DIs labelled by ear (validated 10/10) give 5 parts, 3 crunch in scope from 2 bands.
  35 songs are marked as in MUSDB18 (train).

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
6. [ml-plan-2026-10.md](research/ml-plan-2026-10.md): **the current ML plan** (October 2026,
   after the knob ceiling): generating settings from a song. The user's decisions are made; its
   section 4 is the ML session's work order. The three research reports behind it, which are
   background and not instructions, are in
   [`research/ml-plan-2026-10-reports/`](research/ml-plan-2026-10-reports/README.md).
7. [guitar-separation-2026-10.md](research/guitar-separation-2026-10.md): which open separator
   gives the best electric-guitar stem on Apple silicon (October 2026, for ML plan step 3).
   Keep htdemucs_6s: the best published model (BS-RoFormer SW) has no known weights licence,
   and the 2026-10-08 test's challenger gained only about +0.5 dB paired. Proposes a re-scoring
   test with a paired, band-clustered bar and spectral guards. Research, not a declared plan.
8. [di-riffs-and-part-classifier-2026-10.md](research/di-riffs-and-part-classifier-2026-10.md):
   shippable clean electric-guitar DI riffs by style and register, and open tools to tell chords
   from single notes and a part's register (October 2026, for the product session's listening
   page). Cut new riffs from Guitar-TECHS (CC BY 4.0, about 295 DI minutes; its low and mid
   chord strums later proved to buzz, and those two riffs now come from EGFxSet single notes:
   [riff plan](riff-library-plan.md)); power chords and
   riffs above open position are the one uncovered gap. Basic Pitch (Apache-2.0) is the
   recommended engine; its thresholds are untested. Research, not a declared plan.
9. [di-recovery-2026-10.md](research/di-recovery-2026-10.md): how to get a guitar DI back from a
   song well enough to steer the knob search (October 2026, for ML plan step 3's arm A). The
   rebuild alone breaks the search; the evidence points to its dynamics, so test that before
   swapping separators, and judge rebuilds by whether the target ranks above the start, not by
   coherence. Four local experiments, ranked by value, cheapest test first. Research, not a
   declared plan.
10. [di-rebuild-fine-structure-2026-10.md](research/di-rebuild-fine-structure-2026-10.md):
    designing experiment 4, a successor to C′ that rebuilds a guitar DI's fine structure under
    about 5–10 ms (October 2026, after the rank-margin ladder). Keep the waveform U-Net and change
    its training objective (loss): short-window spectral, phase-derivative and peakiness terms,
    then a balanced adversarial loss. A zero-render capacity check comes first; if C′'s output
    stage can't draw the detail, a zero-initialised full-rate head is tried before the loss route
    is called failed. A DAC-latent route only if its zero-training ceiling check passes. Fold 3
    first, gated on the known-target control. Research, not a declared plan.
11. [song-to-settings-rethink-2026-10.md](research/song-to-settings-rethink-2026-10.md): why
    step 3's arm B (a direct song-to-settings model) failed and what to try instead (October
    2026). "Many settings sound alike" fits the literature but can't explain the failure alone,
    because arm B also failed its positive control on renders. Score its existing samples in
    sound space first (best-of-K against random and jittered baselines, a direct sound-alike
    test), then an isolated-DI retrain, then one branch chosen by those results. Research, not a
    declared plan.
12. [local-objective-2026-10.md](research/local-objective-2026-10.md): how to make the song-only
    objective rank settings correctly near the starting preset, after the arm A levers results
    (October 2026). The local comparison mixes four differences (DI, stem vs reference, lag,
    mask), so separate them first. Level into the drive is the leading, untested mechanism: the
    committed per-knob split shows the rebuild wanting more input gain than the record, but some
    tone knobs are inverted too. Effect-size experiments: zero-render checks, a 14-band local set with audio kept, DI level
    and drive calibration, and leave-one-band-out corrections. Research, not a declared plan.
13. [fresh-di-amp-multitracks-2026-10.md](research/fresh-di-amp-multitracks-2026-10.md): where to
    find more fresh songs with a guitar DI and the amp track of the same take (October 2026). After
    checking the repo, no source checked adds fresh non-metal clean-to-crunch pairs: the
    project's sets 1–5 and label table have already used Cambridge-MT's, set 6 is MedleyDB, and the
    other sources are renders, single notes or unverified. Ranked routes: rule on the held-out
    sets, a local scan of the Cambridge sessions this search could not reach, Weathervane
    (declined by the user 2026-10-20), wider scope, or recording new material. Research, not a
    declared plan.
14. [cambridge-local-check-2026-10.md](research/cambridge-local-check-2026-10.md): route 2 of
    the fresh-multitracks report, run from this Mac (October 2026). The site still blocks scripts,
    but a Hugging Face re-host and the publisher's direct archives gave track lists for 11 of the
    15 unreached sessions: none has an electric-guitar DI, so 0 new DI+amp pairs. Two DI-only
    sessions no set has used turned up, both with caveats: Perpetual Escape "Stop And Rise"
    (never seen, gain unknown) and Dunning Kruger "Sascha" (set 3 downloaded it and set its one
    DI aside as unpaired). Four sessions and everything added since about April 2025 remain
    unchecked. Research, not a declared plan.
15. [hf-detail-losses-2026-10.md](research/hf-detail-losses-2026-10.md): how to recover C′'s
    short-time treble magnitude detail, the error the rebuild-gap study found (October 2026).
    Vocoder and codec recipes (HiFi-GAN, BigVGAN, Vocos, DAC, EnCodec) restore treble texture with
    a small spectrogram discriminator, but their wins are listening wins, not ranking wins; phase
    is worthless for ranking, so the period discriminator is likely misaimed. Ranked: the planned
    offset-removed 2–8 kHz loss, a bounded per-bin log-gain on C′'s output, the upsampler, an
    MPS-safe magnitude-only discriminator, a PANN feature loss. Corrects the DI recovery report.
    Research, not a declared plan.
16. [single-guitar-separation-2026-10.md](research/single-guitar-separation-2026-10.md): how to
    extract one target guitar from a mix with several guitars (October 2026). No usable model is
    shown to separate lead from rhythm or one electric guitar from another; open separators select
    by class. Ranked: keep the target's side of Mega-53's stereo stem (arrangement `pan` or the
    user's ear), a level-difference mask, centre/wide models, Mega-53's electric/acoustic heads
    when the other guitar is acoustic, per-song solo-region adaptation, then fine-tuning on
    synthetic multi-guitar mixes. Flags the licence tension and proposes a zero-render stage-F pan
    screen. Corrects the October separation report. 2026-10-20 (user): ranks 5 and 6 allowed on
    this Mac only; rank 9 (a new separator) out. Research, not a declared plan.
17. [direct-model-constant-2026-10.md](research/direct-model-constant-2026-10.md): how the direct
    model can beat the per-class constant on knob error (October 2026). The researchers found no
    paper that estimates amp-sim knobs from a song or stem with known answers, or reports a constant
    baseline. Part of the pilot's gap is likely the readout: E is minimised by each knob's median,
    but D_stem reports its top mixture component's mean and early-stops on likelihood. Ranked:
    zero-render checks on the stored models (median readout, averaging seeds and halves, a pull
    toward the constant, kNN in the trunk, a per-knob identifiability table), then one retrain with
    a residual median head early-stopped on E, trees, binned heads, frozen AFx-Rep inside the stem
    stage, then pretraining routes. Lists two licence questions for the user. Research, not a
    declared plan.
