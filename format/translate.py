"""
Translate between human-friendly values and the binary's stored strings.

The plugin's knobs carry no numbers — a knob is just a rotation from fully
CCW (0.0) to fully CW (1.0), and that fraction is exactly what the file
stores. So the honest human unit for a bare knob is **percent of rotation**
(0–100), which maps to the stored value as percent/100. Controls that DO show
numbers in the UI (gate dB, EQ Hz, delay ms, tempo BPM, …) are stored in those
real units and pass through unchanged.

Each parameter's `kind` (from packs/<id>/manifest.json) decides the mapping:

  kind        human value            stored string         example
  ----------  ---------------------  --------------------  ------------------
  rotation    percent 0–100          value/100             62  -> "0.62"
  fraction    0.0–1.0 (UI decimal)   passthrough           0.30 -> "0.3"
  metered     native number+unit     passthrough           -70 (dB) -> "-70"
  switch      bool / on / off        "true" / "false"      true -> "true"
  enum        integer                str(int)              1 -> "1"
  path/string text                   passthrough           "/IR/x.wav"

There is no universal per-knob default; reason from the schema's observed
factory values, with noon (50% / 0.5) as the neutral start for tone stacks.
"""

from __future__ import annotations

from typing import Any


def _fmt_num(x: float) -> str:
    """Format a number the way the preset format does: ints without a
    trailing .0, floats trimmed to <=6 decimals with no trailing zeros."""
    if x == int(x):
        return str(int(x))
    return f"{x:.6f}".rstrip("0").rstrip(".")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    if s in ("true", "on", "yes", "1"):
        return True
    if s in ("false", "off", "no", "0"):
        return False
    raise ValueError(f"cannot interpret {value!r} as a switch (true/false)")


def to_binary(kind: str, value: Any, unit: str | None = None) -> str:
    """Convert a human value to the stored string for the given kind."""
    if kind == "switch":
        return "true" if _as_bool(value) else "false"

    if kind in ("path", "string"):
        return str(value)

    if kind == "enum":
        return str(int(round(float(value))))

    if kind == "rotation":
        pct = float(value)
        if not (0.0 <= pct <= 100.0):
            raise ValueError(
                f"rotation value must be a percent in 0–100, got {pct}"
            )
        return _fmt_num(pct / 100.0)

    if kind == "fraction":
        frac = float(value)
        if not (0.0 <= frac <= 1.0):
            raise ValueError(f"fraction value must be 0.0–1.0, got {frac}")
        return _fmt_num(frac)

    if kind == "metered":
        return _fmt_num(float(value))

    raise ValueError(
        f"kind {kind!r} has no defined human→binary mapping; "
        f"use a raw value to write the stored string directly"
    )


def from_binary(kind: str, stored: str, unit: str | None = None) -> Any:
    """Convert a stored string back to a human value (inverse of to_binary)."""
    if kind == "switch":
        return stored == "true"
    if kind in ("path", "string", "enum"):
        return stored
    if kind == "rotation":
        return round(float(stored) * 100.0, 6)  # exact inverse of to_binary
    if kind in ("fraction", "metered"):
        return float(stored)
    return stored


def describe(kind: str, stored: str, unit: str | None = None) -> str:
    """One-line human label for display (show.py)."""
    if kind == "rotation":
        pct = round(float(stored) * 100.0, 1)  # display: 1 dp is plenty
        return f"{_fmt_num(pct)}%"
    if kind == "fraction":
        return _fmt_num(float(stored))
    if kind == "metered":
        u = f" {unit}" if unit else ""
        return f"{_fmt_num(float(stored))}{u}"
    if kind == "switch":
        return "on" if stored == "true" else "off"
    return stored
