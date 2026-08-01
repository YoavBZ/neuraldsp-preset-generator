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

from audit_manifest import (  # noqa: E402
    BoundsChecker,
    numeric,
    published_members,
    report_state_coverage,
)


@pytest.mark.parametrize("shown,expected", [
    ("500 Hz", 500.0),
    ("-24.0 dB", -24.0),
    ("+24.0 dB", 24.0),
    ("40.0 BPM", 40.0),
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


def test_kilo_and_seconds_rescale_only_for_the_matching_unit():
    """A blanket rescale broke reverbDecay, which really is stored in seconds
    while delayTime is stored in milliseconds and displayed in seconds."""
    from audit_manifest import numeric as n
    assert n("1.00 s", "seconds") == 1.0          # stored in seconds: unchanged
    assert n("1.50 s", "ms") == 1500.0            # stored in ms: rescaled
    assert n("1.00 kHz", "hz") == 1000.0
    assert n("20,000 Hz", "hz") == 20000.0        # thousands separator
    assert n("20.0 KHZ", "hz") == 20000.0         # case-insensitive prefix


def test_an_unreadable_display_is_not_a_disagreement():
    """`-inf dB` has a value this cannot compare. Reporting it as a mismatch
    would be a failure no manifest edit could fix."""
    from audit_manifest import UNPARSEABLE
    assert numeric("-inf dB") is UNPARSEABLE
    assert numeric("") is None


def test_both_pan_conventions_parse():
    """Morgan writes `50 L`, Tone King writes `L 50`. Handling one and not the
    other reported a correctly declared -50..50 pan as a disagreement — the
    audit caught it against the second plugin."""
    assert numeric("50 L") == -50.0 and numeric("L 50") == -50.0
    assert numeric("50 R") == 50.0 and numeric("R 50") == 50.0


def test_pan_would_not_be_reported_as_a_disagreement():
    """The regression that made the first run cry wolf: `50 L` parsed as +50,
    so a correctly declared -50..50 pan looked wrong."""
    assert (numeric("50 L"), numeric("50 R")) == (-50.0, 50.0)


def test_state_audit_checks_published_selector_labels():
    """The state fallback used to promote enum kinds but never checked the
    labels that the same mapped Audio Unit control publishes."""
    from packs.loader import ParamSpec

    spec = ParamSpec(module="", key="speed", kind="enum",
                     members={"0": "Slow", "1": "Fast"})
    control = {"valueStrings": ["Slow", "Fast"]}
    assert published_members(spec, control)[0] == "agrees"

    control["valueStrings"][1] = "Quick"
    verdict = published_members(spec, control)
    assert verdict[0] == "disagrees"
    assert "manifest 'Fast', plugin 'Quick'" in verdict[1][0]


def test_state_audit_does_not_pass_an_unpublished_selector():
    from packs.loader import ParamSpec

    spec = ParamSpec(module="", key="mode", kind="enum",
                     members={"0": "A", "1": "B"})
    assert published_members(spec, {})[0] == "unchecked"


def test_unmoved_state_key_is_not_reported_as_nonexistent(capsys):
    params = {
        1: {"displayName": "Mapped"},
        2: {"displayName": "Preset Next"},
    }
    report_state_coverage(params, target_count=3, mapped={"gain": 1})
    out = capsys.readouterr().out
    assert "2 numeric state keys were not reached" in out
    assert "does not prove" in out
    assert "Preset Next" in out
    assert "they have no control" not in out


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
    probe at whatever plugin happened to match.

    Uses a pack that EXISTS but declares no plugin. Naming a pack that does not
    exist looks like the same test and is not: it dies in `load_pack` and never
    reaches the guard, so the guard could be deleted with the suite still green.
    """
    import json
    import audit_manifest
    from packs import loader

    pack_dir = tmp_path / "nameless"
    pack_dir.mkdir()
    (pack_dir / "manifest.json").write_text(json.dumps({
        "manifest_version": 1, "pack_id": "nameless", "display_name": "Nameless",
        "file_header": "nameless", "parameters": {},
    }))
    monkeypatch.setattr(loader, "PACKS_DIR", tmp_path)

    with pytest.raises(SystemExit) as exc:
        audit_manifest.audit("nameless")
    assert exc.value.code == 2


def test_a_missing_pack_is_still_reported_cleanly():
    result = subprocess.run(
        [sys.executable, str(AUDIT), "--pack", "definitely-not-a-pack"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


def test_cannot_verify_reports_and_does_not_pass(capsys):
    """A plugin whose state is opaque cannot be audited at all. That must not
    read as a clean bill: it exits 3, distinct from both 0 and a disagreement."""
    from audit_manifest import cannot_verify
    from packs.loader import load_pack

    pack = load_pack("morgan")
    code = cannot_verify(pack, {1: {}, 2: {}})
    assert code == 3
    out = capsys.readouterr().out
    assert "CANNOT VERIFY" in out
    assert "2 controls" in out
    # It has to say why, or the reader will assume the plugin is broken.
    assert "opaque bytes" in out
    assert "guess" in out
