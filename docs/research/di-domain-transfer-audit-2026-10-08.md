# Inverse-DI domain transfer audit — 2026-10-08

**Recommendation:** run one frozen-checkpoint pilot on the already-local Guitar-TECHS P2 DI/mic-amp pairs before choosing another long training run. No new dataset or pretrained weights are needed. This is a proposed development screen, not evidence that transfer has improved. The next training decision must await the declared pilot, its positive controls, and review of its results.

**Independent review, 2026-10-08:** source/metadata claims were substantially
reproduced. The pilot sketch below required corrections and is superseded by the
[concrete draft declaration](../di-domain-pilot-plan.md), which still needs code
review and a commit before execution. In particular, the inherited catalog used the
whole ten-second crop to select/check windows; its calibration/evaluation division
is not historically untouched. The FIR must predict raw DI without evaluation-DI
EQ, and a failed short FIR is inconclusive. Training's 52-sample wet latency must be
handled explicitly. Recipe metadata and asset hashes freeze identity but do not
establish immutable historical checkpoint lineage.
[Archived independent review](di-domain-pilot-review-2026-10-08.md).

## What the network actually learned from

The audited supervision is entirely **Morgan-generated wet audio**, not native recorded amp/DI pairs. Real recordings supply the dry performances; their original paired amp tracks are not the supervised inputs.

| Cache under `~/ndsp-presets/learn/direc/` | Rows before fold filtering | Wet input | Guitar-TECHS contribution |
|---|---:|---|---|
| `cache` | 18,843 | Morgan PR12 POC renders | 996 P1 chord + 339 P1 scale renders |
| `cache-sw50r` | 14,965 | Morgan SW50R renders | 789 P1 chord + 278 P1 scale renders |
| `cache-ac20` | 14,998 | Morgan AC20 renders | 794 P1 chord + 279 P1 scale renders |

Evidence: the three `meta.json` files; PR12 kept IDs joined against `~/ndsp-presets/learn/poc/renders/index-w{0..4}.jsonl` matched all 18,843 unique IDs. The joined PR12 source paths contain no P2 or `micamp` paths. SW50R/AC20 metadata paths are exclusively Cambridge/Telefunken source DIs and P1 chords/scales DIs. All three caches contain the same 13 development-band names plus `Guitar-TECHS P1`.

- `learn/di_pool.py:26–45` selects only set-2 development session DIs and P1 **chords/scales/directinput** files. P1 single notes/techniques, P2, P3 and all native `micamp` recordings are absent. The current window manifest has 3,509 windows, including 40 distinct P1 source files. Windows are 8 s with 2 s pre-roll, 6 s kept, 4 s hop and an activity gate (`:23`, `:59–78`).
- PR12 wet audio comes from `AudioUnitRenderer("morgan")`, then loses the first 2 s (`learn/render_job.py:68–104`). `learn/direc.py:49–72` joins the kept POC metadata to that render index and reads the corresponding source DI. POC exclusion rules are in `learn/train.py:77–87`.
- SW50R/AC20 pairs use Morgan, random pre-amp DI EQ, amp/pedal/input-gain/mic variation, and 2 s pre-roll (`learn/render_pairs.py:41–86`, `:98–142`). The EQ-modified DI is their target source. `learn/direc.py:81–107` reads these rendered pairs, retaining rows at ≥ −40 LUFS. Native instrumental backings can enter training as **bleed augmentation** (`:229–235`, `:256–261`); that is not native paired amp supervision.

Launch evidence distinguishes the checkpoints: local `direc/train_folds.sh:19–22` uses PR12 alone for folds 1–3 and copies the existing PR12 fold-0 model (`:8`); `direc/train_set3.sh:19–21` uses all three caches, excludes fold 2, and runs 60 + 300 minutes. These paths are under `~/ndsp-presets/learn/`. The builders, manifests and launch scripts establish the recorded recipe; checkpoints save only a `state_dict` (`learn/direc.py:352–353`), without immutable embedded data/command lineage.

## Normalization, objective and boundaries

- **Target:** not the original guitar's DI balance. For each six-second DI, subtract its mean spectral dB, apply the frozen training-fold average minus that spectrum, clamped to ±15 dB, by FFT EQ (`learn/direc.py:241–249`). The average is a power average over retained **PR12 cache rows**, mean-removed; extra caches do not update it (`:111–129`, `:206–226`). It is therefore row-weighted, not one vote per guitar. An existing average file is reused without provenance validation (`:118–120`).
- **Scale/context:** both pair waveforms are independently peak-normalized to 0.9 before int16 storage. Training selects a random three-second crop; validation uses the center crop. Each input and target is independently divided by its **standard deviation** and multiplied by 0.1 (`:267–271`), described approximately as RMS in the module header. Absolute DI level is not learned. Input-only tilt/bell EQ, bleed and noise augment training (`:250–263`).
- **Loss:** `100 × waveform L1 + MR-STFT`; MR-STFT averages spectral-convergence plus log-magnitude L1 over FFT sizes 256/512/1024/2048/4096, Hann windows and quarter-window hops (`:182–191`, `:291`). Validation uses the same loss and an input-as-DI baseline (`:342–347`). `rebuild` uses six-second windows, five-second hops and restores input scale; it does **not** apply −22.9 LUFS itself (`:356–385`; the caller does that in `learn/direc_check.py:118–121`).
- **Split:** `learn/train.py:42–56` derives four band folds by sorting bands represented in the PR12 panel index, shuffling with seed 20261003, then assigning `i % 4`. `direc.py:223–226` trains on all rows outside the requested fold. Unmapped bands default to −1 and always train: P1 is never held out. Overlapping source windows remain together through their band, but this is neither an amp holdout nor a P1 holdout. Unknown names also silently train; adding P2 through `--extra-cache` would contaminate this pilot.
- The set-3 recipe excludes K3 fold 2, including Eat The Feeder (`docs/validation-set3.md:288–305`). The audited cache manifests add no set-3 DIs. Set-1 P3 is excluded from this training source and remains outside this pilot; its development/reserved boundaries are documented in `docs/validation-datasets.md:169–179`.

## Local native pairs and provenance

Under `~/ndsp-presets/references/datasets/guitar-techs/`, P1 chords/scales have both `audio/directinput/` and `audio/micamp/` directories. P1's DI performances were used, so its native wet recordings would test a new processing chain on familiar source performances, not independent performance transfer.

**Use P2 instead:** `P2-catalog.json` lists 46 DI/mic-amp pairs: 28 chord, 12 scale, one single-note and five technique files, plus 26 crop records. All 92 explicitly listed source paths exist under `P2-downloads/` (existence checks only). Example pair: `P2_scales/audio/directinput/directinput_A.wav` and `P2_scales/audio/micamp/micamp_A.wav`. The four local archives and saved `P2-downloads/record.json` are present. The catalog records matching published archive MD5s; this audit did not rehash audio or archives.

The authors explicitly license **all data CC BY 4.0**, and the public Zenodo record lists downloadable P1/P2 archives. The saved record agrees: `metadata.license.id = cc-by-4.0`, `access_right = open`. Preserve attribution to Pedroza and colleagues, the paper and record URL in pilot outputs. [Author site](https://guitar-techs.github.io/), [Zenodo release and checksums](https://zenodo.org/records/14963133).

The primary paper describes a simultaneous split to DI and mic'd amp. P2 uses an EVH Wolfgang neck pickup, Yamaha YB15 **bass amp**, AT2020 microphone and a domestic room; P1 uses an Orange CR60 and SM57. The paper and website disagree on P2's interface, so retain that uncertainty. Zenodo warns of recording offsets: same filenames do not establish sample alignment. [Paper, §III and Table I](https://arxiv.org/html/2501.03720v1), [Release alignment warning](https://zenodo.org/records/14963133). Local native pairs suffice; no alternative dataset search or download is justified for this screen.

## One minimal pilot to declare and review before execution

1. **Freeze inputs and selection.** Use only `models-set3/fold2.pt` and its existing `cache/average-fold2.npy`; record their hashes at execution, with code revision and manifest hashes. Choose the first six chord crop records sorted by `(take, start_frame)` and all six scale crop records from P2's catalog: 12 distinct takes. Freeze their source paths/times before scoring. No P1/P3, reserved material, model fitting, checkpoint selection or repeated window hunting. P2 is development material already inspected for cataloguing, not a pristine confirmation set.
2. **Prepare bounded pairs.** Each existing crop is 10 s (`P2-downloads/_tools/cut_crops_p2.py:1`, `:82`): use seconds 0–4 for alignment/polarity checks and a diagnostic linear inverse; score seconds 4–10, with no overlap. Confirm metadata offsets on calibration audio, then fix them for every arm. Reject and report invalid pairs by declared clipping/activity/alignment rules; do not replace them after seeing model scores. Use 48 kHz mono, actual file headers, identical channel handling and the training target transform above. P2's DI may construct scoring targets but must not alter the frozen average or neural predictions.
3. **Run frozen inference and controls.** Compare recovered DI with (a) native wet treated as DI and (b) `flatref`: native wet equalized to the frozen average, as in `learn/direc_check.py:120–121`. For each same P2 DI window, make **one** matched Morgan PR12 render through one predeclared training-compatible preset, using seconds 2–4 as pre-roll. This adds just 12 renders and tests the same unseen instrument/performance in the training processing domain. Also check an oracle target against itself (zero error) and a 256-tap wet→DI FIR fitted only on seconds 0–4 and evaluated on seconds 4–10, with ridge penalty 0.001 times the mean diagonal of the input Gram matrix. Canonicalize that FIR output with the target's scoring EQ; label it an oracle-assisted recoverability control, never a deployable competitor. If it cannot recover the native pair, failure cannot be attributed to neural domain shift alone.
4. **Score and decide once.** Primary: per-take MR-STFT against the average-balanced true DI, with each compared waveform standardized to 0.1; use the center three seconds to match validation context. Report fixed-alignment waveform L1 separately, plus a low-band MR-STFT diagnostic (80 Hz–4 kHz); no fitted delay/polarity per prediction. Report every take and separate chord/scale medians; 12 takes are still one player/amp chain, not 12 independent domains. Proposed screen gate: native recovered DI reduces median primary loss by ≥10% versus the better simple baseline per take, wins on ≥9/12 takes, and improves both content-group medians. Require ≥10% median primary improvement over input-as-DI on matched Morgan renders, oracle error <1e-6, valid alignment, and ≥10% median low-band improvement over native-input-as-DI for the FIR control. These are proposed engineering thresholds, not established effect sizes or significance claims; freeze them and the remaining QC rules in the reviewed execution declaration.

Cost: 12 native excerpts, 12 matched renders, 24 neural inferences and small linear calculations; no training, installs or downloads. Mic/room phase, noise and lost bandwidth can limit recovery even with correct pairing; the low-band control diagnoses that risk without changing the primary gate. A failure with passing controls is a reason to investigate native-domain coverage before spending more on Morgan-only training. A pass supports only this P2 chain and a subsequent broader declaration: it cannot establish driven-amp transfer, separation robustness, original pickup/EQ/level recovery, or better downstream preset rankings. Neither a pass nor current cross-amp numeric verification automatically authorizes another long run.

**Audit scope:** metadata, code and primary web sources only; no audio/arrays/checkpoint contents were opened, no model or judge scores were computed, and no experiments or agents were launched. Only this note was written; concurrent main-task edits were left untouched.
