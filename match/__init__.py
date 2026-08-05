"""Turning a target sound into preset parameters: renderers, search, and the store.

Split from `analysis/` along one line: everything here depends on *producing*
audio from parameters, and everything there depends only on measuring audio that
already exists. So `analysis/` is testable in CI on any machine, and this package
is testable in CI only through `SyntheticRenderer` — which is precisely why the
synthetic chain exists (see `analysis/refchain.py`).

The plugin-backed renderers need macOS, a licensed Audio Unit, and the `host`
extra. Nothing in CI ever loads one, matching the rule `audit_manifest.py`
already follows: plugin-dependent checks are deliberate local runs.
"""

from __future__ import annotations
