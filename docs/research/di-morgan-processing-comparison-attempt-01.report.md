INCONCLUSIVE: VERIFICATION DISAGREEMENT

Primary outcome: INITIAL INCONCLUSIVE at render-clean. Comparison failures: 36 / 235 checks.

Independently recomputed 108 original scalar controls, 12 byte-identical original model predictions, 36 direct scalar controls and the original F gate. Validated all 12 retained float64 render-input copies against original DI, including exact suffix bytes. Unique controls are not multiplied by duplicate persisted report rows.

Maximum absolute differences by family:

- old_committed_gate: 2.7755575615628914e-15
- preflight.108: 8.04623034866836e-12
- preflight.reported_errors: 0.0
- preflight.gate: 2.7755575615628914e-15
- baseline.108: 1.7763568394002505e-15
- baseline.reported_errors: 0.0
- baseline.gate: 1.1102230246251565e-16
- direct36: 2.220446049250313e-16
- direct_reported_errors: 0.0
- direct_gate: 1.1102230246251565e-16

Startup EOF with empty partial bytes, zero protocol replies/audio returns; fallback/partial/protocol and failure/invalidation/closure agree. Host stderr: instantiate: Error Domain=NSOSStatusErrorDomain Code=-3000 "invalidComponentID". No cause attribution. No score-clean/render-panel/score-panel exists or was computed.

Scientific execution: 7.931752250000001 seconds in original CPU environment. The earlier hash-API launch failure was preserved; it preceded scientific asset access.

Evidence (full counts/checks/differences and hashes are in JSON):

- tmp/di-morgan-processing-independent.py: 5f409597bcb1a2ad47c260b375af9c03a3082466f493c456d9c7674fd03e5e47
- tmp/di-morgan-processing-independent-blind.py: b61c3475fdcd01a22cd34996013bb769fa3325ba0f523553332ccf9b5b968ced
- tmp/di-morgan-processing-independent-derivation.json: a64a49dd4d7b8800bb910d7661d8749b724263b77af607b6c1b12eab4015f9b9
- tmp/di-morgan-processing-independent-read-barrier.json: 94871591101f6a60be5dbde56772fd15317db7eb4ca2a7114be861a8fe531440
- tmp/di-morgan-processing-independent-array-hashes.json: 65ed4cd687a00aae5d9845f50eaef74a3003070ebe8ca04e8674d1f64ec57563
- tmp/di-morgan-processing-independent-transcript.jsonl: e1efe749f08e7d0c67d0c6238dfa0c3ef3c3568e7e686cbea419cb863a2a1019
- tmp/di-morgan-processing-independent.log: 0b7e937f598c590176ea88aeb36b1d19d48b2650052f75a96a226ae322a3613d

Limitations:

- Independent implementation shares installed NumPy/SciPy/Torch, CPU and platform; agreement does not independently validate those libraries or hardware.
- QC/oracle eligibility is inherited from exact old committed metadata. No raw recording QC, target regeneration, average loading, missing prerequisite computation or new audio was performed.
- Command construction matches template+R and declared overrides, but startup failed before any acknowledgement or audio command. No live parameter readback or plugin identity can be verified.
- Retained transcripts, stderr, stage logs and filesystem inventory support the recorded startup failure and closure. They are not a retrospective OS/process/runtime access audit or independent observation of historical calls.
- The record establishes observed invalidComponentID(-3000) stderr; it does not establish why the OS rejected the component.
- Main reports primary sessions completed and no CPU overlap. This verifier does not retrospectively prove process exclusivity.
- Twelve dependent performances are not twelve independent players; no native/song/preset/product or processing-robustness conclusion follows from original controls.
- First verifier launch failed on Python-version hash API compatibility before scientific inputs; preserved in transcript/log. Only one actual original model pass ran. Scientific execution was under 900 seconds.
- Tool-level source and post-barrier comparison reads are described in transcript attestations; the transcript instruments this verifier, not all shell/tool operations.
