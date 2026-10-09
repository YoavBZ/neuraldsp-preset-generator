# Large generated evidence kept outside git

Codex's 2026-10-08/09 continuation committed large generated evidence files (up to
198k lines each). To keep the repository light, the files below were moved, unchanged,
to `~/ndsp-presets/learn/codex-evidence/`, at the same relative paths. Scripts that
read them should be pointed there. No test reads them.

- docs/set3-rank-calibration.json.gz
- docs/di-timing-sensitivity-verification.json
- docs/set3-mask-diagnostic.json, docs/set3-mask-diagnostic-verification.json
- docs/set3-confirmation-evidence/verification-set3.json
- docs/set3-cross-amp-diagnostic.json
- docs/set3-development-diagnostic.json, docs/set3-development-diagnostic-verification.json
- docs/di-input-shift-control-verification.json.gz
- docs/di-alignment-control.json, docs/di-alignment-control-verification.json

All research and experiment records are to be removed from the repository once the
plugin is ready (user decision, 2026-10-09).
