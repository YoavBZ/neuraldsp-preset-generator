"""The audit script's own logic, tested without the plugin.

The audit itself needs macOS, a licence and an installed Audio Unit, so it can
never run in CI. What *can* run in CI is everything around the plugin call: the
display parsing, the comparison, and the refusal to run against a pack that
doesn't say which plugin it describes. Those are where the bugs were — the first
version reported two false disagreements because it compared a signed pan
against the plugin's `50 L` / `50 R`, and skipped `/selectedAmp` entirely
because a leading-slash key failed the module lookup.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).parent.parent
AUDIT = REPO_ROOT / "scripts" / "audit_manifest.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from audit_manifest import BoundsChecker, numeric  # noqa: E402


@pytest.mark.parametrize("shown,expected", [
    ("-24.0 dB", -24.0),
    ("+24.0 dB", 24.0),
    ("40.0 BPM", 40.0),
    ("1.00 kHz", 1000.0),     # prefix, not a bare number
    ("20.0 kHz", 20000.0),
    ("500 Hz", 500.0),
    ("50 L", -50.0),          # the plugin signs a pan with a letter
    ("50 R", 50.0),
    ("C", 0.0),               # centre is not "0"
    ("25 L", -25.0),
    ("", None),
    ("Custom IR", None),      # a label, not a number
])
def test_display_strings_parse_to_stored_units(shown, expected):
    assert numeric(shown) == expected


def test_pan_would_not_be_reported_as_a_disagreement():
    """The regression that made the first run cry wolf: `50 L` parsed as +50,
    so a correctly declared -50..50 pan looked wrong."""
    assert (numeric("50 L"), numeric("50 R")) == (-50.0, 50.0)


class FakeProbe:
    """Stands in for the plugin: clamps to a range we control."""

    def __init__(self, lo, hi):
        self.lo, self.hi = lo, hi
        self.calls = []

    def __call__(self, binary, au, mode, *args):
        self.calls.append((mode, args))
        wrote = [float(v) for v in args[1].split(",")]
        return {"results": [
            {"wrote": f"{w:g}", "keptInState": f"{min(max(w, self.lo), self.hi):g}"}
            for w in wrote
        ]}


def _spec(lo, hi, kind="metered"):
    from packs.loader import ParamSpec
    return ParamSpec(module="ac20EQ", key="ac20EQHpf", kind=kind, unit="hz",
                     min=lo, max=hi)


def test_bounds_checker_confirms_a_correct_range(monkeypatch):
    import audit_manifest

    probe = FakeProbe(20, 500)
    monkeypatch.setattr(audit_manifest, "run_probe", probe)
    checker = BoundsChecker(pathlib.Path("/nonexistent"), {})
    assert checker.check("ac20EQ/ac20EQHpf", _spec(20, 500))[0] == "agrees"


def test_bounds_checker_catches_the_range_that_hid(monkeypatch):
    """The real defect: declared 20..20000, actually 20..500. The perturbation
    map could not see it because the parameter already held its minimum, so this
    write-probe path is the only thing standing between that bug and the user."""
    import audit_manifest

    probe = FakeProbe(20, 500)
    monkeypatch.setattr(audit_manifest, "run_probe", probe)
    checker = BoundsChecker(pathlib.Path("/nonexistent"), {})
    verdict = checker.check("ac20EQ/ac20EQHpf", _spec(20, 20000))
    assert verdict[0] == "disagrees"
    assert verdict[2] == 500.0

    # It has to write past the declared end, or the clamp never shows.
    _, args = probe.calls[0]
    written = [float(v) for v in args[1].split(",")]
    assert max(written) > 20000


def test_bounds_checker_declines_what_it_cannot_judge(monkeypatch):
    import audit_manifest

    monkeypatch.setattr(audit_manifest, "run_probe", FakeProbe(0, 1))
    checker = BoundsChecker(pathlib.Path("/nonexistent"), {})
    assert checker.check("x/y", _spec(None, None)) is None
    assert checker.check("x/y", _spec(0, 1, kind="enum")) is None


def test_audit_refuses_a_pack_that_names_no_plugin(tmp_path, monkeypatch):
    """A bootstrapped draft has no `audio_unit`, and guessing one would point the
    probe at whatever plugin happened to match."""
    result = subprocess.run(
        [sys.executable, str(AUDIT), "--pack", "definitely-not-a-pack"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
