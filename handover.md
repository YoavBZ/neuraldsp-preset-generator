# Morgan song-to-preset handover

Prepared 2026-10-09. Covers the Codex continuation from the Claude handover through
the final repository/PR decisions. This is a local handover, not a plugin asset;
do not commit or publish it without an explicit request.

## 1. Read this first

**Research is stopped.** The user said Stop, requested an assessment of progress,
then requested repository review and this handover. Those later administrative
requests did not authorize renewed ML work. Do not resume because an old heartbeat
arrives. Require a new instruction from the human.

- `continue-morgan-ml-development` is PAUSED; its TOML was checked while preparing
  this handover. The earlier final-confirmation monitor was already paused.
- All known agents were closed. No training, rendering or inference session was
  live at the last scientific checkpoint. No new scientific jobs were started
  during the subsequent Git/PR work.
- PR #136 and its replacement #137 are both CLOSED without merging.
- No new model was trained during this continuation. No improved real-song preset
  matching algorithm was demonstrated or released.
- The reserved final confirmation failed. Its data is spent and must not be used
  for training, tuning or a repeated independent final confirmation.

The most useful outcome is a reliable negative confirmation and a narrow positive
lab control. The central product goal remains unmet.

## 2. Product goal and current user instructions

Input: a song/full mix or separated guitar stem, plus a time range. Output: a Morgan
preset that sounds like the recording when a representative guitar plays the
song's notes. The user does not supply a DI. Songs with several guitars remain in
scope. The average-guitar measure was chosen before this continuation and was
supported by Claude's listening study; do not replace it silently.

Use local, open-source models and tools. The installed, licensed Morgan Audio Unit
may be used for approved local operations. A controlled clean-chain recovery score
is not evidence of useful full-song preset matching.

Latest repository instruction supersedes earlier requests to archive all research:

- The repository is for the plugin, not an experiment archive.
- Do not store stale proposals, generated score dumps, agent reviews, self-referential
  session records or iterative progress checkpoints unless strictly necessary for
  the plugin itself.
- Keep durable current guidance and the minimum evidence needed for a relevant
  product claim or validation contract.
- This handover was explicitly requested as a local file; it is not an exception
  authorizing its inclusion in the repository.

Communication: plain English, short meaningful updates, no repeated permission
questions for already authorized work. Quality and proportionate verification
still take precedence over credit efficiency. Avoid duplicate agents/jobs,
unchanged polling, repeated reviews and large evidence dumps.

## 3. Where the work is saved

Repository: `/Users/yoavbz/projects/neuraldsp-preset-generator`.

- Original Claude handover: `tmp/codex-handover.md`.
- Original Claude branch: `poc/sound-model`, handover revision `8d8a57a`.
- Scientific continuation: `codex/song-model-continuation`, revision `cc4fb8a`.
  Contains 31 continuation commits after the handover, plus earlier Claude work
  that was not merged into main. This branch was pushed, but PR #136 was closed.
- Current checkout: `codex/song-model-product-docs`, revision `4ce823f`, based
  directly on main revision `64c4bd9`. Only `.gitignore`, `docs/README.md` and
  `docs/ROADMAP.md` differ. This branch was pushed, but PR #137 was closed.
- **Neither branch was merged.** Closing the PRs did not delete the branches or
  erase their remote Git history. Do not mistake the archive branch for approved
  product code, or push/merge it again without a new request.

Most result paths listed below exist only on the scientific continuation branch,
not in the current checkout. Read them without switching branches, for example:

```sh
git show cc4fb8a:docs/set3-heldout-confirmation-results.md
git show cc4fb8a:learn/README.md
```

Local output and control files remain under `tmp/`; waveform/model datasets are
outside the repository. No data download or experiment is needed to read this
handover.

Local operational checkpoint: `tmp/ml-continuation-monitor.md`. Its STOP header is
authoritative. Its later historical sections contain outdated live-agent and
next-stage instructions and must not be treated as permission to continue.
The pre-stop bytes are retained as
`tmp/ml-continuation-monitor-before-user-stop-20261009.md`.

Claude project memory is at:
`~/.claude/projects/-Users-yoavbz-projects-neuraldsp-preset-generator/memory/MEMORY.md`.
The original handover also names the previous Claude transcript. Read relevant
memory if taking over, but current human instructions override historical plans.

## 4. Starting point inherited from Claude

These were existing results, not achievements of this continuation:

- Waveform U-Net DI recovery (`learn/direc.py`) followed by preset-menu selection
  was the leading experimental method.
- Clean PR12 development improvement was 8.5%, below its 10% gate.
- On heavier development material, SW50R had a conditional pass against a constant;
  PR12 and AC20 were not established successes. Final confirmation was pending.
- PANNs/log-mel reranking did not pass.
- The contrastive tone encoder identified synthetic presets at 74.5%, but failed
  real-recording reranking. Synthetic identification was not product validation.
- Separator upgrades achieved roughly +1 dB, below the required +2 dB.

The old handover proposed shipping a constant baseline, wider search, longer
training, transfer augmentation and a multi-guitar target declaration. Those are
historical proposals, not completed work or an instruction to execute them now.

## 5. Work completed during this continuation

### A. One-time reserved confirmation: FAIL

Revision `b79ce06`; result `docs/set3-heldout-confirmation-results.md`.

- Tested 27 reserved guitar parts from six bands; SW50R primary, PR12 secondary.
- Completed 4,320 renders and both waveform/onset scoring analyses.
- Neither amp met its declared acceptance gates. SW50R's median improvement over
  the constant did not meet the significance requirement; PR12 did not establish
  improvement over the constant.
- Independent verification included 1,321 distinct audio measurements and found
  no numerical discrepancies.
- This rejects promotion of the tested method. It was an isolated amp-track test,
  not a validated full-mix, separated-stem or multi-guitar product test.

Do not repeat this confirmation, tune on its scores, or alter its frozen
model/presets/rules to reinterpret the outcome.

### B. Development preset-selection diagnostics: no successful fix

Known-DI diagnostic (`8739009`): 33 development parts, 11 bands, three amp menus.
Using the intended dry performance showed menu headroom, but the rebuilt-DI
chooser had a refusal on one part. This did not prove waveform recovery was the
only bottleneck. Result: `docs/set3-development-diagnostic-results.md`.

Activity-mask diagnostic (`79136bf`): on a fixed 12-part panel, alternative activity
proxies rescued that refusal but changed none of the eleven control choices. The
required broader improvement was absent. Closed, no expansion.
Result: `docs/set3-mask-diagnostic-results.md`.

Prior/score rank calibration (`20483ba`): grouped comparisons of a supervised
prior and score blends missed the gate against the existing net chooser. Large
verification counts reflected report fields, not additional independent songs.
Result: `docs/set3-rank-calibration-results.md`.

Cross-amp pooling (`8e5a91b`): combining the existing SW50R, PR12 and AC20 menus did
not meet routing conditions. No successful amp-selector training followed.
Result: `docs/set3-cross-amp-diagnostic-results.md`.

All four results were independently checked. Do not retune closed gates or select
favorable subsets to rescue these studies.

### C. Training-domain audit and native transfer pilot: INCONCLUSIVE

The source audit found that audited wet supervision used Morgan renders, without
native paired recordings. A domain gap remained a hypothesis, not a proven cause.
Source record: `docs/research/di-domain-transfer-audit-2026-10-08.md`.

The first pilot stopped before audio access because NumPy/Torch synthetic metric
agreement failed. A separate precision probe identified differing Hann-window
precision. A shared-window implementation passed the original 1e-8 tolerance;
the tolerance was not relaxed (`b60964f`).

The separately declared second pilot (`2baf2e3`) passed metric preflights, but only
three of twelve native pairs passed pairing calibration: three chords, no scales.
It stopped before a neural transfer test. Eight failures involved peak sharpness,
one correlation. No native-equipment recovery success or failure was measured.

Results: `docs/di-domain-pilot-results.md`,
`docs/di-domain-metric-probe-results.md`, `docs/di-domain-pilot-v2-results.md`.
This pilot remains closed; do not relax calibration or rebuild a favorable panel.

### D. Known Morgan clean-chain controls: narrow positive result

Twelve dry performances from one player/guitar were processed through one clean
Morgan PR12+R chain. Learned recovery beat the processed signal directly, with
72.18% median recovery-error improvement (`c8c40ad`).

A stronger comparison against the better of processed audio and simple spectral
correction gave **57.83% median recovery-error improvement**, with twelve wins
(`3f68a25`). Independent reconstruction agreed on all twelve stand-ins and gates.

Results: `docs/di-morgan-control-results.md`,
`docs/di-morgan-flatref-results.md`.

This is not 58% better presets. It establishes neither native transfer, driven
tones, different guitars, song separation, multiple guitars nor shipping readiness.
The original full-render evidence was incomplete: eleven full wet files were not
retained, and a full independent plugin-command transcript was absent. The saved
six-second arrays and score derivations were independently checked.

### E. Alignment, timing and phase controls: limited explanations

- Timing-confidence control: seven accepted distorted cases had two/three-sample
  lag errors. Exact-delay/polarity and mismatch controls passed. The alignment
  control did not pass its whole gate (`a697c0d`).
- Common scoring offsets: the clean-chain advantage survived thirteen tested
  output offsets (`a29ff79`).
- Four model-input shifts: the advantage remained around 57.8% (`4696573`).
- One fixed artificial periodic phase transformation: twelve wins, 57.56% median
  recovery-error improvement (`b2d7d27`).

Each was independently verified. They show robustness of the specific lab result,
not that timing explains real-world failure or that augmentation is validated.
No more timing/phase microtests were selected.

Results: `docs/di-alignment-control-results.md`,
`docs/di-timing-sensitivity-results.md`,
`docs/di-input-shift-control-results.md`, `docs/di-phase-control-results.md`.

### F. Broader Morgan processing study: stopped before audio

Declared `df68127`; archived outcome `5b58a54`.
Result: `docs/di-morgan-processing-control-results.md`.

Synthetic preflights and replay controls passed, including twelve byte-identical
predictions. The clean rendering stage failed during AU startup with
`invalidComponentID (-3000)`, before new audio or broader-panel scoring.
Independent verification agreed on 235 checks of the completed stages and retained
inputs. Failed setup/reporting attempts were preserved, not hidden.

The result is INCONCLUSIVE. The exact startup cause was not established. There is
no driven-chain comparison. This closed study was not retried or rescued.

### G. Separate Morgan startup utility: infrastructure only

Declared `9aab649`; completed `cc4fb8a`.
Result: `docs/morgan-au-startup-results.md`.

Two independent source reviews found material problems: unnecessary shared-server
DSP/state access and a main-thread wait that could deadlock AU initialization.
A dedicated minimal Swift process corrected them. Twenty-four synthetic tests
passed; a fresh source review approved the fixed procedure before host execution.

One host probe compiled, instantiated Morgan 1.1.1, returned its version, accepted
quit and exited/reaped with code zero. Logs were empty and source/binary identity
checks held. No audio, preset, model or dataset was accessed by the probe.

This proves only instance/version/process readiness. It does not prove rendering,
destructor teardown, the previous failure's cause, or model accuracy. The utility
depends on dated declaration/review hashes and a pinned SDK; it was not adopted as
a reusable plugin tool and is excluded from the final small PR.

### H. Further directions: proposals only

External-data audit: EGFxSet was a conditional hardware-pedal candidate, not cleared
or downloaded. Pairing, quality, short duration and training suitability remained
unverified. ToneTwist amp-release rights/provenance remained unresolved.
Record: `docs/research/native-guitar-development-data-2026-10-09.md`.

Direct preset ranker proposal: use real development stems and saved candidate
labels with a small feature/ridge model, avoiding DI inference. No declaration,
feature extraction, training or numerical experiment occurred.
Record: `docs/research/direct-preset-ranker-proposal-2026-10-09.md`.

The last metadata agent, Nash, hit a usage-limit error and was closed. It left:

- `tmp/direct-preset-ranker-metadata-admission.md`
- `tmp/direct-preset-ranker-development-querylist.json`

These are unfinished and not independently verified. Preliminary inventory:
33 development parts, 31 exact session/start query keys, 12 query-bearing sessions,
11 band names. Complete active-guitar targets, rights, independent source groups,
stem identity and label coverage were not established. Do not turn this draft into
a completed admission decision. The proposed equal-weight multi-guitar risk rule
was not adopted and must not silently replace the product target.

## 6. Assessment of progress and resource use

No new training or validated real-song matching improvement was delivered. Useful
progress was completing a trustworthy final rejection, eliminating some proposed
selection fixes, establishing a clean-chain positive control, and identifying
unresolved transfer/data/target issues.

The continuation overinvested in narrow timing/phase controls, repeated reviews,
navigation updates and detailed evidence archives relative to product improvement.
The user raised rapid usage-limit exhaustion and questioned whether to return to
Claude. No exact per-task credit or token attribution was audited; do not invent
usage totals or present large verification-field counts as product progress.

Any future work should start with a concrete, cheap test of a product-relevant
hypothesis, not another infrastructure or micro-control sequence. This is guidance
for a future authorized continuation, not permission to resume now.

## 7. Repository and PR decisions at the end of the session

1. At the user's request, pushed the scientific branch and opened draft PR #136:
   <https://github.com/YoavBZ/neuraldsp-preset-generator/pull/136>.
2. Inspection found 233 changed files and about 651,000 added lines against main.
   The continuation alone changed 164 docs files, with 94 non-Markdown evidence/source
   files; twelve verifier Python scripts were in the literature folder. A single
   verification JSON added nearly 198,000 lines. Earlier Claude work was also included.
3. Initially proposed reorganizing/compressing the archive. The user rejected the
   premise: the product repository should not be an archive or hold stale iterative
   progress records. Do not repeat the archive proposal.
4. Created a new branch directly from main to exclude all experimental commits,
   with only current documentation policy/roadmap and `/tmp/` ignore changes.
   Opened draft PR #137 and closed #136.
5. The user then said the replacement PR was unnecessary and requested this
   handover instead. **PR #137 is now closed too:**
   <https://github.com/YoavBZ/neuraldsp-preset-generator/pull/137>.

Nothing was merged. Existing historical content already on main was not deleted
wholesale because some files are live inputs, fixtures or frozen contracts.
The broad repository cleanup was not completed or requested as a separate job.
Do not claim that closing the PRs cleaned existing main or removed the pushed
experimental branch from GitHub.

## 8. Operational rules and environment for any later authorized work

Use the user-owned `/Users/yoavbz/.codex/bin/neuraldsp-safe` helper for its supported
Python, pytest, benchmark, branch, commit, GitHub and push operations. Do not add
project-local permission rules. Keep safe reads/tests separate from network or
approval-requiring commands. Explicit user authorization persists, but STOP
overrides old autonomous continuation instructions.

Previously verified environments:

- Project `.venv`: Python 3.14 / NumPy 2.5.1; no Torch.
- `~/ndsp-presets/tools/learn-venv/bin/python`: Python 3.9.6 / Torch 2.8 /
  NumPy 2.0.2 / SciPy 1.13.1; no pytest.
- Original Claude handover describes a separate MPS training environment. No new
  training was run here; verify its current state before any future use.

Operational cautions inherited from Claude: one MPS training process at a time;
finite-gradient/recovery monitoring; avoid self-matching process wait loops;
do not touch the PACE licence daemon; avoid repeated fresh AU processes or
unbounded inventory commands. Older disk/free-space numbers are historical, not
current measurements.

Scientific safeguards: preserve failures, cheap positive controls before expensive
runs, fixed procedures before data access, fresh independent review and independent
recomputation for decision-driving results. Earlier experiments committed exhaustive
plans/evidence; the user's latest storage policy rejects that archive approach.
Retain necessary validation discipline without resuming the rejected repository
archiving pattern.

## 9. What remains unresolved

- A useful song-only preset selector on real recordings.
- Transfer beyond the single clean Morgan/player/guitar lab control.
- Complete supervision/target definition for multi-guitar stems.
- A suitable legally usable development dataset with verified pairing and coverage.
- Broader listening validation of the judge and the actual product input.
- Whether the direct ranker proposal is feasible at all; its metadata audit is not
  complete or independently verified.

Do not restart any of these automatically. The next assistant should first answer
the user's new request, with this handover as context.
