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
    ("C", 0.0),               # centre is not "0"
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
    """`-inf dB` has a value this cannot compare, and an EMPTY display is the
    same case — several real controls in both plugins publish one. Returning
    None for those made them compare unequal to a declared range and print a
    DISAGREES that no manifest edit could fix."""
    from audit_manifest import UNPARSEABLE
    assert numeric("-inf dB") is UNPARSEABLE
    assert numeric("") is UNPARSEABLE
    assert numeric("   ") is UNPARSEABLE


def test_a_pan_display_is_refused_rather_than_guessed():
    """Both plugins display a pan as a position out of 50 — `50 L`, `L 50` — but
    Morgan stores -50..50 and Tone King stores -1..1. The display therefore
    cannot establish the range, and an earlier version of this function returned
    a signed 50 for both, which made the audit agree with a Tone King range that
    was 50x too large. Refusing sends the caller to the write probe, which
    measures the stored unit instead of inferring it."""
    from audit_manifest import UNPARSEABLE
    for shown in ("50 L", "50 R", "L 50", "R 50", "25 L", "L 25"):
        assert numeric(shown) is UNPARSEABLE, shown


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


# --- the pan fix, protected ------------------------------------------------
# A review mutated 31 lines of this change and 18 survived, including EVERY
# function added to fix the pan bug: `_same_to_float32` could return True
# unconditionally, `probe_bounds` could return "agrees" without asking the
# plugin, and `verify_via_state` could count unchecked parameters as verified —
# all with a green suite. A fix nothing tests is a fix that reverts by accident.


def test_float32_tolerance_accepts_an_ulp_and_rejects_a_real_error():
    """The plugin's parameters are 32-bit: 1.0 comes back as 0.99999994, which
    must pass. A range that is genuinely wrong differs by orders of magnitude
    and must not — a tolerance that accepts everything is worse than none."""
    from audit_manifest import _same_to_float32

    assert _same_to_float32(0.9999999403953552, 1.0)      # one float32 ULP
    assert _same_to_float32(11.999999046325684, 12.0)
    assert not _same_to_float32(-1.0, -50.0)              # the pan bug: 50x
    assert not _same_to_float32(1.0, 50.0)
    assert not _same_to_float32(500.0, 20000.0)
    assert not _same_to_float32(0.5, 1.0)


class _ClampingProbe:
    """Stands in for the plugin, recording what the checker actually wrote."""

    def __init__(self, lo, hi):
        self.lo, self.hi = lo, hi
        self.written = []

    def apply_many_with_states(self, blobs):
        from format.parser import parse
        from format.structured import build, set_parameter
        from format.writer import write

        states = []
        for blob in blobs:
            preset = build(parse(blob))
            param = preset.parameters[0]
            self.written.append(float(param.value))
            kept = min(max(float(param.value), self.lo), self.hi)
            set_parameter(preset, param.module_path, param.key, f"{kept:g}")
            states.append(write(preset.tokens))
        return None, states


def _one_param_state(key: str, value: str) -> bytes:
    body = len(value.encode()) + 2
    return (b"plug\x00" + key.encode() + b"\x00"
            + bytes([0x01, body, 0x05]) + value.encode() + b"\x00")


def _pan_spec(lo, hi):
    from packs.loader import ParamSpec
    return ParamSpec(module="", key="cabPan", kind="metered", unit="pan", min=lo, max=hi)


def test_probe_bounds_writes_past_both_ends():
    """Probing inside the range would confirm anything at all."""
    from audit_manifest import probe_bounds

    probe = _ClampingProbe(-1.0, 1.0)
    probe_bounds(probe, _one_param_state("cabPan", "0"), "/cabPan", _pan_spec(-1.0, 1.0))
    assert min(probe.written) < -1.0, probe.written
    assert max(probe.written) > 1.0, probe.written


def test_probe_bounds_catches_a_range_in_the_wrong_unit():
    """The pan bug exactly: declared -50..50, the plugin keeps -1..1."""
    from audit_manifest import probe_bounds

    verdict = probe_bounds(_ClampingProbe(-1.0, 1.0), _one_param_state("cabPan", "0"),
                           "/cabPan", _pan_spec(-50.0, 50.0))
    assert verdict[0] == "disagrees"
    assert (verdict[1], verdict[2]) == (-1.0, 1.0)


def test_probe_bounds_confirms_a_correct_range():
    from audit_manifest import probe_bounds

    verdict = probe_bounds(_ClampingProbe(-1.0, 1.0), _one_param_state("cabPan", "0"),
                           "/cabPan", _pan_spec(-1.0, 1.0))
    assert verdict[0] == "agrees"


def test_probe_bounds_declines_half_a_range_instead_of_crashing():
    """A bootstrapped draft can carry a min with no max. That used to raise a
    TypeError straight through `guarded()` as a raw traceback."""
    from audit_manifest import probe_bounds

    assert probe_bounds(_ClampingProbe(-1.0, 1.0), _one_param_state("cabPan", "0"),
                        "/cabPan", _pan_spec(None, 50.0)) is None
