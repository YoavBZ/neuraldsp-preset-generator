# Independent design and code review: known DI input shifts

Verdict: APPROVE

Reviewed on 2026-10-08 in a fresh review context. No blocking design or implementation defect found in the snapshot below. Approval covers the draft design and implementation, subject to main's separate declaration, hash attestation, archive and commit before execution. It supplies no numerical result or execution authorization.

## Reviewed snapshot

Repository: `/Users/yoavbz/projects/neuraldsp-preset-generator`  
Branch: `codex/song-model-continuation`  
HEAD: `a29ff798af29ae13096b55ae8dee28440dee2a1e`

| Item | Bytes | SHA256 |
| --- | ---: | --- |
| `learn/di_input_shift_control.py` | 24210 | `6ecc61a9e6d3a2327f01709a43139ab48ce807d56debcd477f05a7fd20762219` |
| `tests/test_di_input_shift_control.py` | 39293 | `7486ea56aeb2e1349a6ab3ea4a61d999d2657d4f19d4c68170adc324f8a811fb` |
| Draft `docs/di-input-shift-control-plan.md`, complete file | 12581 | `7a894d61ab3ab58d7bf37db74395bef4ee74d92abadc68e99201588be89e603d` |
| Frozen design body | 11002 | `7736e42b6f88e65bc82b780c0462913011af27db074dc5d9ef92075f5a595589` |
| Existing `docs/di-timing-sensitivity-inputs.sha256` | 6084 | `1c6cde4a6bdaa5ceb71fd43e56a21049cffb2bbd023a359d8f7b44de4f6dc527` |

The frozen design digest covers the exact raw UTF-8 bytes **after** the first literal `## Frozen design\n`, including its leading blank line and final newline. UTF-8 decoding was checked strictly. The source, test and frozen-design hashes match the supplied worker prefixes. Repeated snapshot checks during review found these hashes and HEAD unchanged. The three implementation/design files are currently untracked draft files; main must commit the approved snapshot and declaration before running it.

## Scope and evidence

Read the complete new runner, tests and draft plan, plus the needed inherited T/F/C/P/R/V/D source, scientific restrictions, original input declarations, the unchanged 48-entry hash manifest, archived T metadata and independent verifier source. Read and hashed only the permitted source/text/report metadata. No actual scientific NPZ/NPY, audio, checkpoint, average, catalog or coefficient asset was read or hashed. No study scoring, model inference, rendering, training, network operation, agent delegation or Git mutation was performed. The sole review deliverable is this file.

Independently inspected archived metadata: T is `VERIFIED`, scientific disposition `PASS`, with 23,734 passing checks and no failures; 53 source pins; 156 retained rows and 13 screens; complete passed 12-take/108-scalar baseline replay; and 48 artifact identities. The archived verifier source hashes to `d232b74395d060af3da71c97daff170224359cd08718fca09e0d462d1f850ec8`, matching its verification record. Provenance/source dictionaries, artifact dictionaries, archived input identities and the exact existing 48-entry manifest agree. All six original T report/progress/log files match their recorded byte counts and SHA256 values; the four original JSON reports equal their committed archive counterparts byte for byte. Both retained progress and stdout contain the exact 156 archived rows. These are metadata and report-identity checks, not a new numerical verification of the guitar study.

## Design and implementation assessment

- The experiment uses only the twelve frozen dependent clean Morgan takes and exact offsets `(-3, -2, 0, 2, 3)`. It shifts the complete raw-level six-second `net_input` with finite zero padding, preserves its dtype and original 52-sample convention, converts to `<f4` before unchanged `D.rebuild`, and reverses only the imposed offset on the raw prediction. Target, raw DI, wet and saved flatref competitors remain fixed. There is no fitted lag, selected offset, changed target or new flatref computation.
- The repaired inverse explicitly casts the unchanged helper's float64 result back to `<f4`. The meaningful synthetic test verifies retained float32 sample bytes, both signed zeros, a subnormal, a next-representable value, nontrivial amplitudes and zero-filled lost edges at every nonzero offset. Separate tests verify shift sign, no wrap, retained extra timing error and full input conversion before normalization. The original `D.build_model`/`D.rebuild` source remains the model path used by the runner.
- Prefix and DRAFT checks precede guarded coefficient/asset access. The new guard retains unchanged `T.guard`, requires 53 inherited pins and ten disjoint own pins, checks committed bytes and fresh review/declaration hashes, validates archived derivation/replay evidence and exact original report snapshots, and rechecks source identities and HEAD. The fixed exclusive output refuses existing paths and aliases.
- Array access is restricted to the existing five members plus `render.net_input`, within the original 48-file manifest. All-file hash barriers, immediate per-file checks, loaded identities, finite active mono lengths, exact dtype/byte overlap at 52 samples and later stability checks are present. Regular-file, symlink, lexical-alias, hardlink and duplicate-inode checks are enforced. Model access is restricted to the original fold2 path/hash after declaration, with repeated observed hash checks, CPU loading, eval mode and two Torch threads. The runner does not call inherited average/catalog/render/training paths.
- Both mandatory barriers are durable before later inference: all 108 original replay scalars and the original stronger screen must pass before model loading; all twelve unshifted prediction byte identities, 36 scores compared directly to the original archive, valid QC/oracles and the zero gate must pass before any nonzero inference. Ordinary failures continue through the twelve baseline takes. Last-take failures block all 48 shifted calls. Zero predictions and scores are reused without another inference or score call.
- Each of five offsets uses unchanged `F.compare`, including the better simple competitor, inclusive median threshold, nine strict wins and positive group medians. Zero PASS is mandatory; each of the four nonzero screens must pass. Missing, duplicate, invalid or nonfinite cases override valid scientific failures with `INCONCLUSIVE`. Exactly 60 result cases are required; the successful progress stream has twelve baseline-stage entries plus 60 case-stage entries.
- Returned predictions are saved before validity/parity checks and after-call budget checks. Ordinary shifted failures preserve evidence and allow remaining cases; baseline inference timeout writes a partial replay; case timeout retains prior progress, returned prediction archives and the run failure record. Final stability failure preserves all 60 cases and five screens as `INCONCLUSIVE`. The cooperative 900-second budget covers guards, hashing/loading, model calls and scoring, with checks around inherited guards. A stuck call still requires main's external monitoring as declared.

The interpretation correctly includes finite context, normalization and shift effects. It does not isolate encoder stride causation, reopen the closed native panel, alter native gates, establish native/song/product transfer, use held-out evidence or authorize training. Original D/T/P/F scientific definitions are preserved.

## Synthetic verification

Executed only the authorized helper command:

```sh
/Users/yoavbz/.codex/bin/neuraldsp-safe pytest -q -n0 -p no:cacheprovider tests/test_di_input_shift_control.py
```

Result: **93 passed, 1 skipped in 2.70 seconds**. The skip is the expected optional actual-Torch synthetic-module test because Torch is unavailable in the helper environment. The suite meaningfully exercises both last-take barriers, direct archive tolerance, fixed competitors, inverse bytes, gates and invalid priority, drift/refusals, progress and retained failure evidence. No interpreter switching was attempted.

The future twelve exact original prediction checks remain the mandatory control in the explicitly required original CPU environment. Main retains ownership of declaration/commit, actual execution and fresh independent numerical verification before interpreting any result. Any change to the reviewed source, tests, frozen design or prerequisites requires fresh review and declaration.
