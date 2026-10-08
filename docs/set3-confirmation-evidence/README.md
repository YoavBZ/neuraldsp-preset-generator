# Set 3 reserved confirmation evidence

Run 2026-10-08. Read the [result](../set3-heldout-confirmation-results.md) and frozen
[declaration](../set3-heldout-confirmation-plan.md) before interpreting these files.
Both amps fail confirmation; a passing verification means the checks agree, not that
the model passed.

- `distances.json`, `distances-onset.json`: complete production distance records.
- `confirmation.json`, `confirmation-onset.json`: production selections, per-part
  and per-band effects, refusal counts and gates.
- `confirmation-verdict.json`: combined result across both timing analyses.
- `verification-set3.json`: full independent numerical/audio report, input hashes,
  storage/DI checks, training evidence and limitations.
- `verification-set3-summary.json`: compact independent result and check counts.
- `verification-set3-sampling.json`: verification sampling fixed before outcomes.

Files are copied unchanged from the completed experiment and independent verifier.
Absolute paths identify local source material; they do not distribute it. No audio,
checkpoints or factory preset payloads are included. The independent report shares
the audio-distance primitive and model architecture, and includes no fresh plugin
re-render; its scope is explicitly recorded in the report.
