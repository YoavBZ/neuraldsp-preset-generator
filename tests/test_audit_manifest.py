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


def test_a_switch_is_checked_against_its_two_published_labels():
    """A switch is a two-index selector and the plugin publishes both labels in
    the same `valueStrings`. Restricting this to `kind == "enum"` left every
    Tone King switch asserting nothing — 21 of the 53 parameters the audit
    honestly reported as untested."""
    from packs.loader import ParamSpec

    spec = ParamSpec(module="", key="ampsActive", kind="switch",
                     members={"0": "Inactive", "1": "Active"})
    assert published_members(spec, {"valueStrings": ["Inactive", "Active"]})[0] == "agrees"

    verdict = published_members(spec, {"valueStrings": ["Off", "On"]})
    assert verdict[0] == "disagrees"
    assert "manifest 'Active', plugin 'On'" in verdict[1][1]


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


# --- the same float32 comparison, in the other bounds checker ---------------
# `probe_bounds` learned to compare at float32 and `BoundsChecker.check` did
# not, though both measure the same physical quantity through the same 32-bit
# parameter. It was latent only because Morgan happens to round-trip its bounds
# as decimal text; a pack whose state keeps binary doubles would have reported
# a disagreement no manifest edit could fix.


def _one_float32_ulp_in(x: float) -> float:
    """The float32 one step closer to zero than x: 1.0 -> 0.99999994."""
    import struct

    bits = struct.unpack("<I", struct.pack("<f", x))[0]
    return struct.unpack("<f", struct.pack("<I", bits - 1))[0]


class _Float32Probe:
    """Stands in for the plugin at the precision it actually has.

    Clamps to the real range, then hands the endpoint back one float32 ULP
    short of it, which is what a 32-bit parameter does to a value written as
    1.0. `keptInState` is decimal text either way, so nothing but the
    comparison can tell the two apart.
    """

    def __init__(self, lo, hi):
        self.lo, self.hi = lo, hi

    def __call__(self, binary, au, mode, *args):
        rows = []
        for text in args[1].split(","):
            kept = min(max(float(text), self.lo), self.hi)
            if kept in (self.lo, self.hi):
                kept = _one_float32_ulp_in(kept)
            rows.append({"wrote": text, "keptInState": repr(kept)})
        return {"results": rows}


def test_bounds_checker_compares_at_the_precision_the_plugin_has(monkeypatch):
    import audit_manifest

    monkeypatch.setattr(audit_manifest, "run_probe", _Float32Probe(-1.0, 1.0))
    checker = BoundsChecker(pathlib.Path("/nonexistent"), {})
    verdict = checker.check("appModel/cabPan", _pan_spec(-1.0, 1.0))
    assert verdict[0] == "agrees", verdict


def test_bounds_checker_still_catches_a_real_error_at_that_precision(monkeypatch):
    """The tolerance must not be a way of agreeing with everything: the pan bug
    was a factor of fifty, not an ULP."""
    import audit_manifest

    monkeypatch.setattr(audit_manifest, "run_probe", _Float32Probe(-1.0, 1.0))
    checker = BoundsChecker(pathlib.Path("/nonexistent"), {})
    assert checker.check("appModel/cabPan", _pan_spec(-50.0, 50.0))[0] == "disagrees"


def test_bounds_checker_still_checks_that_the_endpoints_survive(monkeypatch):
    """Both halves are compared the same way. A plugin that clamps correctly
    but rewrites the maximum it was handed is still disagreeing with the
    manifest, and the float32 tolerance must not hide that."""
    import audit_manifest

    class _EatsItsMaximum(_Float32Probe):
        def __call__(self, binary, au, mode, *args):
            result = super().__call__(binary, au, mode, *args)
            for row in result["results"]:
                if float(row["wrote"]) == 1.0:       # the declared maximum
                    row["keptInState"] = "0.5"
            return result

    monkeypatch.setattr(audit_manifest, "run_probe", _EatsItsMaximum(-1.0, 1.0))
    checker = BoundsChecker(pathlib.Path("/nonexistent"), {})
    verdict = checker.check("appModel/cabPan", _pan_spec(-1.0, 1.0))
    assert verdict[0] == "disagrees"
    assert verdict[2] == 0.5


# --- a selector verified on partial evidence -------------------------------
# `check_members` skips the probe rows where nothing moved, then reports
# "agrees" on the strength of whatever did. The member that goes unseen is
# normally the one the plugin is already sitting on — the same "already at that
# value, so nothing moved" blind spot that let three wrong `*EQHpf` maximums
# through a full audit.


class _SelectorProbe:
    """Stands in for the plugin's `values` mode for a selector.

    Writing the index the control already holds moves nothing, so that member
    yields no label — exactly the case the audit used to count as verified.
    """

    def __init__(self, labels, baseline=None):
        self.labels, self.baseline = labels, baseline

    def __call__(self, binary, au, mode, *args):
        rows = []
        for text in args[1].split(","):
            index = int(text)
            moved = [] if index == self.baseline else [{"label": self.labels[index]}]
            rows.append({"wrote": text, "moved": moved})
        return {"results": rows}


LABELS = {0: "Slow", 1: "Medium", 2: "Fast"}
MEMBERS = {"0": "Slow", "1": "Medium", "2": "Fast"}


def _speed_spec():
    from packs.loader import ParamSpec

    return ParamSpec(module="tremolo", key="speed", kind="enum", members=MEMBERS)


def _check_speed(monkeypatch, probe):
    import audit_manifest

    monkeypatch.setattr(audit_manifest, "run_probe", probe)
    checker = BoundsChecker(pathlib.Path("/nonexistent"), {})
    return audit_manifest.check_members(checker, "tremolo/speed", _speed_spec())


def test_a_selector_with_an_unseen_member_is_only_partly_verified(monkeypatch):
    verdict = _check_speed(monkeypatch, _SelectorProbe(LABELS, baseline=1))
    assert verdict[0] == "partial"
    assert (verdict[1], verdict[2]) == (2, 3), "must say how many of how many"


def test_a_selector_whose_every_member_answered_is_fully_verified(monkeypatch):
    """The distinction is worthless if nothing can reach the complete verdict."""
    verdict = _check_speed(monkeypatch, _SelectorProbe(LABELS, baseline=None))
    assert verdict == ("agrees", 3)


def test_a_wrong_label_still_disagrees_even_on_partial_evidence(monkeypatch):
    """Incomplete coverage must not downgrade a contradiction to a caveat."""
    wrong = LABELS | {2: "Quick"}
    verdict = _check_speed(monkeypatch, _SelectorProbe(wrong, baseline=1))
    assert verdict[0] == "disagrees"
    assert "manifest 'Fast', plugin 'Quick'" in verdict[1][0]


def _compare_one_selector(monkeypatch, probe, capsys):
    """Drive the whole report for a single mapped selector."""
    import audit_manifest
    from packs.loader import Pack

    monkeypatch.setattr(audit_manifest, "run_probe", probe)
    pack = Pack(pack_id="fake", display_name="Fake", file_header="fake",
                parameters={"tremolo/speed": _speed_spec()})
    code = audit_manifest.compare(
        pack,
        {7: {"displayName": "Speed"}},
        [{"element": "tremolo", "key": "speed", "moved": [{"address": 7}]}],
        BoundsChecker(pathlib.Path("/nonexistent"), {}),
    )
    return code, capsys.readouterr().out


def test_partial_evidence_is_reported_as_partial_not_as_verified(monkeypatch, capsys):
    code, out = _compare_one_selector(
        monkeypatch, _SelectorProbe(LABELS, baseline=1), capsys
    )
    assert "PARTLY VERIFIED — 1" in out
    assert "tremolo/speed  (2 of 3 declared members produced a label)" in out
    # The headline still totals what agreed, but it must not read as a finished
    # check — that is the whole defect.
    assert "1 verified (0 completely, 1 on partial evidence)" in out
    # Partial evidence is still evidence: it is not a disagreement and must not
    # fail the run.
    assert "0 DISAGREE" in out and "DISAGREES" not in out
    assert code == 0


def test_a_complete_selector_check_says_so_without_the_caveat(monkeypatch, capsys):
    code, out = _compare_one_selector(
        monkeypatch, _SelectorProbe(LABELS, baseline=None), capsys
    )
    assert "1 verified, 0 DISAGREE" in out
    assert "PARTLY VERIFIED" not in out
    assert code == 0


# --- the paths a review found could be replaced with `return 0` -------------
# 55 mutations, 25 survived, and 11 of those were in `verify_via_state` — the
# path every Tone King number comes from. It could be made to return 0
# unconditionally, or to count disagreements as verified, with a green suite.


class _StubProbe:
    """A plugin that answers however the test needs."""

    def __init__(self, controls, states=None):
        self.controls, self.states = controls, states or []

    def apply_many_with_states(self, blobs):
        return None, [self.states[i] if i < len(self.states) else blobs[i]
                      for i in range(len(blobs))]


def _pack_with(**specs):
    from packs.loader import Pack
    return Pack(pack_id="stub", display_name="Stub", file_header="stub",
                parameters=specs, audio_unit={"type": "aumf", "subtype": "X", "manufacturer": "Y"})


def _metered(module, key, lo, hi, unit=None):
    from packs.loader import ParamSpec
    return ParamSpec(module=module, key=key, kind="metered", unit=unit, min=lo, max=hi)


def test_compare_returns_nonzero_when_a_range_disagrees(capsys):
    """Nothing asserted a failing exit code. `compare()` could be changed to
    ignore disagreements entirely and stay green."""
    import audit_manifest

    pack = _pack_with(**{"eq/hpf": _metered("eq", "hpf", 20, 20000, "hz")})
    params = {7: {"displayName": "HPF", "minString": "20 Hz", "maxString": "500 Hz"}}
    revmap = [{"element": "eq", "key": "hpf", "moved": [{"address": 7}]}]
    code = audit_manifest.compare(pack, params, revmap, checker=None)
    assert code == 1, "a disagreement must fail the run"
    assert "DISAGREES" in capsys.readouterr().out


def test_compare_reports_a_declared_fact_no_probe_reached(capsys):
    """An asserted-but-unreached parameter must be loud, not silent. Collapsing
    the declared/bare routing was a surviving mutation."""
    import audit_manifest

    pack = _pack_with(**{"eq/hpf": _metered("eq", "hpf", 20, 500, "hz")})
    class _Declines:
        def check(self, *a, **k):
            return None

    code = audit_manifest.compare(pack, params={}, revmap=[], checker=_Declines())
    out = capsys.readouterr().out
    assert code == 1
    assert "ASSERTS SOMETHING" in out and "eq/hpf" in out


def test_bounds_checker_still_checks_that_the_ends_survive(monkeypatch):
    """Two halves: a value written past an end must come back AS that end, and
    the end itself must survive unchanged. Deleting the first half survived
    mutation — and it is the half that catches a plugin which RETAINS an
    out-of-range value instead of clamping, which Tone King does."""
    import audit_manifest
    from audit_manifest import BoundsChecker

    # A plugin that retains whatever it is given: no clamping at all.
    def retaining(binary, au, mode, *args):
        return {"results": [{"wrote": w, "keptInState": w} for w in args[1].split(",")]}

    monkeypatch.setattr(audit_manifest, "run_probe", retaining)
    checker = BoundsChecker(pathlib.Path("/nonexistent"), {})
    verdict = checker.check("eq/hpf", _metered("eq", "hpf", 20, 500))
    assert verdict[0] == "disagrees", "a plugin that clamps nothing cannot confirm a range"


def test_float32_tolerance_is_tight_enough_to_be_worth_having():
    """Widening it to 10% survived mutation: the tests bracketed one ULP and a
    50x error with nothing in between."""
    from audit_manifest import _same_to_float32

    assert not _same_to_float32(1.09, 1.0), "9% out is not a rounding artefact"
    assert not _same_to_float32(0.9, 1.0)
    assert _same_to_float32(1.0000001, 1.0)


def test_a_switch_with_labels_is_checked_as_a_selector(monkeypatch):
    """Admitting switches to the loop without routing them to the member check
    compared them as a numeric range and reported DISAGREES on a correct
    manifest. That defect was introduced while fixing a different one."""
    import audit_manifest
    from packs.loader import ParamSpec

    spec = ParamSpec(module="", key="ampsActive", kind="switch",
                     members={"0": "Inactive", "1": "Active"})
    pack = _pack_with(**{"/ampsActive": spec})
    params = {7: {"displayName": "Amp Section Active", "minString": "0.00", "maxString": "1.00"}}
    revmap = [{"element": "appModel", "key": "ampsActive", "moved": [{"address": 7}]}]

    def probe(binary, au, mode, *args):
        return {"results": [
            {"wrote": "0", "moved": [{"address": 7, "label": "Inactive"}]},
            {"wrote": "1", "moved": [{"address": 7, "label": "Active"}]},
        ]}

    monkeypatch.setattr(audit_manifest, "run_probe", probe)
    checker = audit_manifest.BoundsChecker(pathlib.Path("/nonexistent"), {})
    assert audit_manifest.compare(pack, params, revmap, checker) == 0


def test_a_moved_control_with_no_label_is_not_counted_as_read(monkeypatch):
    """`seen` counted controls that moved, so a selector whose every index moved
    but published no label reported as completely verified on zero labels read —
    unread evidence counted as read, one level down from the bug this audit
    exists to catch."""
    import audit_manifest
    from packs.loader import ParamSpec

    spec = ParamSpec(module="", key="sel", kind="enum",
                     members={"0": "A", "1": "B"})

    def blank(binary, au, mode, *args):
        return {"results": [{"wrote": w, "moved": [{"address": 7, "label": ""}]}
                            for w in args[1].split(",")]}

    monkeypatch.setattr(audit_manifest, "run_probe", blank)
    checker = audit_manifest.BoundsChecker(pathlib.Path("/nonexistent"), {})
    assert audit_manifest.check_members(checker, "/sel", spec) is None
