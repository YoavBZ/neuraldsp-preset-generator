"""The floors of the sound-gap test (`learn/voice_floors.py`, Unit C of `docs/scratch-voice-plan.md`) behind fakes: no
render before the guards (nor numpy), records written once, a repeat mismatch stops everything, refusals recorded with
key-free reasons, `--rerun` reruns only the refused, the carry for byte-identical guitars, the shards disjoint and
covering all 47, no numpy at import. Synthetic keys, a fake world, no renders: runs on the light CI runner."""
import ast
import hashlib
import json
import math
import pathlib
import subprocess
import sys

import pytest

from learn import scratch_exact as SE
from learn import scratch_search as S
from learn import scratch_voice as V
from learn import voice_floors as VF

REPO = pathlib.Path(__file__).resolve().parents[1]


def _h(*a):
    """A made-up sha256 (hex, so no record holds a part key through it)."""
    return hashlib.sha256("|".join(a).encode()).hexdigest()


def _args(**kw):
    return type("A", (), dict({"rerun": False}, **kw))()


def _parts(n=6):
    sets = ["bks", "goat", "panel"]
    return [{"pkey": f"{sets[i % 3]}/part-{i:02d}|u{i}", "set": sets[i % 3], "lag": 0, "held": "A"}
            for i in range(n)]


class Fake:
    """A world with made-up guitars: every render is recorded; `refuse` {(pkey, guitar): times} makes a render
    silent that many times; `same` {(pkey, guitar): other guitar} makes its dry guitar byte-identical to another's."""

    def __init__(self, parts, refuse=None, same=None, stored_off=None, free=100.0):
        self.parts, self.check_keys = parts, V.check_parts(parts)
        self.stored = {p["pkey"]: {"true": {"held": 1.0, "audio_sha256": _h("t", p["pkey"])},
                                   "tr-di": {"held": 2.0, "audio_sha256": _h("b", p["pkey"])}} for p in parts}
        self.stored_off = stored_off or {}           # {(pkey, guitar): (held, sha)} the repeat renders instead
        self.shas = {"build": "B" * 64, "floors": "F" * 64, "answers": "A" * 64}
        self.refuse, self.same, self.free = dict(refuse or {}), dict(same or {}), free
        self.calls, self.logs, self.caps, self.t = [], [], 0, 0.0

    def render(self, pk, g):
        self.calls.append((pk, g))
        if self.refuse.get((pk, g), 0) > 0:
            self.refuse[(pk, g)] -= 1
            return math.inf, _h("silent", g), True
        if g in VF.STORED:
            h, sha = self.stored_off.get((pk, g), (self.stored[pk][g]["held"], self.stored[pk][g]["audio_sha256"]))
            return h, sha, True
        return 3.0 + VF.ORDER.index(g), _h("r", g, pk), True

    def dry_shas(self, pk):
        out = {g: _h("d", g, pk) for g in VF.ORDER + VF.STORED}
        for (k, g), other in self.same.items():
            if k == pk:
                out[g] = out[other]
        return out

    def free_gb(self):
        return self.free

    def wait_cap(self):
        self.caps += 1

    def clock(self):
        return self.t

    def sleep(self, s):
        self.t += s

    def now(self):
        return "2026-11-26 00:00:00"

    def log(self, msg):
        self.logs.append(msg)


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "voice_dir", lambda: tmp_path)
    return tmp_path


def _rec(pk):
    return json.loads(V.floor_path(pk).read_text())


def _shard_all(w, rerun=False):
    """The three shards, shard 0 first (it runs the repeat check)."""
    return sum(VF.run_floor(_args(shard=(k, 3), rerun=rerun), w) for k in range(3))


# --- the module -------------------------------------------------------------------------------------------------------

def test_no_numpy_at_import():
    code = "import sys; import learn.voice_floors; print('numpy' in sys.modules, 'scipy' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["False", "False"]


def test_the_module_imports_only_the_standard_library_at_module_level():
    tree = ast.parse((REPO / "learn" / "voice_floors.py").read_text())
    mods = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            mods.add(node.module.split(".")[0])
    assert mods <= {"__future__", "argparse", "json", "math", "os", "pathlib", "time", "learn"}


def test_the_names_and_counts():
    assert VF.MODULE in V.UNIT_FILES and VF.PLAN == V.PLAN
    assert VF.ORDER == V.RENDERED == ("vc-fin", "vc-cut", "vc-own", "vc-env", "avg+mild")
    assert VF.STORED == ("true", "tr-di") and VF.SHARDS == 3 and VF.RENDERS_EACH == 2
    assert len(VF.ORDER) * V.PARTS * VF.RENDERS_EACH == V.RENDERS["floors"] == 470
    assert len(VF.STORED) * V.CHECK_PARTS * VF.RENDERS_EACH == V.RENDERS["repeat"] == 8
    assert VF.DISK_GUARD_GB == 31.0
    assert VF.first_path("a/b").parent.name == "floors-first" and VF.first_path("a/b").parent.parent == V.voice_dir()
    assert VF.first_path("a/b").name == V.floor_path("a/b").name


def test_the_disk_guard_matches_the_house_one():
    tdm = pytest.importorskip("learn.trusted_data")           # trusted_data may pull numpy in
    assert VF.DISK_GUARD_GB == tdm.DISK_GUARD_GB


def test_the_cli_knows_only_the_floor():
    assert sorted(VF.COMMANDS) == ["floor"]
    with pytest.raises(SystemExit):
        VF.main(["floor"])                                 # --shard is required
    with pytest.raises(SystemExit):
        VF.main(["floor", "--shard", "0/4"])


# --- the shards -------------------------------------------------------------------------------------------------------

def test_the_shards_are_disjoint_and_cover_all_47():
    parts = _parts(47)
    got = [[p["pkey"] for p in VF.mine(parts, (k, 3))] for k in range(3)]
    assert sorted(sum(got, [])) == sorted(p["pkey"] for p in parts)
    assert all(not set(a) & set(b) for i, a in enumerate(got) for b in got[i + 1:])
    assert [len(g) for g in got] == [16, 16, 15]
    assert got == [[p["pkey"] for p in SE.mine({"parts": parts}, (k, 3))] for k in range(3)]


def test_only_k_of_3_runs():
    for ok in ((0, 3), (1, 3), (2, 3)):
        assert VF.shard_refusal(ok) is None
    for bad in ((0, 1), (0, 2), (3, 3), (-1, 3), (0, 4), None, "0/3"):
        assert VF.shard_refusal(bad), bad


# --- the guards come first --------------------------------------------------------------------------------------------

def _no_render(monkeypatch):
    calls = []
    monkeypatch.setattr(VF.RealWorld, "render", lambda self, pk, g: calls.append((pk, g)))
    monkeypatch.setattr(VF, "run_floor", lambda args, w: calls.append("run"))
    return calls


def test_no_render_before_the_guards(monkeypatch, world):
    calls = _no_render(monkeypatch)
    with pytest.raises(SystemExit, match="one render process a shard"):
        VF.cmd_floor(_args(shard=(0, 2)))
    monkeypatch.setattr(V, "require_voice", lambda *a: (_ for _ in ()).throw(SystemExit("differ from main's")))
    with pytest.raises(SystemExit, match="differ from main's"):
        VF.cmd_floor(_args(shard=(0, 3)))
    asked = []
    monkeypatch.setattr(V, "require_voice", lambda *a: asked.append(a) or {})
    monkeypatch.setattr(V, "_build", lambda m: {"proofs_hold": False, "parts": {}})
    with pytest.raises(SystemExit, match="proofs did not hold"):
        VF.cmd_floor(_args(shard=(1, 3)))
    assert asked == [(V.PHASE_DRY,)]                       # the build's hash on main is required
    assert calls == []


def test_the_real_command_refuses_off_main(monkeypatch, world):
    calls = _no_render(monkeypatch)
    monkeypatch.setattr(V, "on_main", lambda: (None, "this checkout's ['learn/voice_floors.py'] differ from main's"))
    with pytest.raises(SystemExit, match="differ from main's"):
        VF.cmd_floor(_args(shard=(0, 3)))
    main = {S.PHASE_DRAW: {}, S.phase_answers("fs-stem"): {}, SE.PHASE_TARGETS: {}, V.PHASE: {}}
    monkeypatch.setattr(V, "on_main", lambda: (main, None))
    with pytest.raises(SystemExit, match="has no phase_scratch_voice_dry"):
        VF.cmd_floor(_args(shard=(0, 3)))
    assert calls == []


def _guarded(monkeypatch, tmp_path, parts, build_parts=None, stored=None, answers=None, proofs=True):
    keys = [p["pkey"] for p in parts]
    build = {"proofs_hold": proofs, "parts": build_parts if build_parts is not None else {
        k: {"guitars": {g: {"audio_sha256": "a", "file_sha256": "f"} for g in VF.ORDER}} for k in keys}}
    st = stored if stored is not None else {k: {"true": {"held": 1.0}, "tr-di": {"held": 2.0}} for k in keys}
    monkeypatch.setattr(V, "require_voice", lambda *a: {})
    monkeypatch.setattr(V, "_build", lambda m: build)
    monkeypatch.setattr(V, "_stored_floors", lambda m: (st, None))
    monkeypatch.setattr(S, "require_hash", lambda phase, path: answers if answers is not None else
                        {"parts": {k: {} for k in keys}})
    monkeypatch.setattr(SE, "bank_build", lambda m: {})
    monkeypatch.setattr(SE, "context", lambda: ({"parts": parts}, None))
    monkeypatch.setattr(S, "file_sha", lambda p: "s" * 64)
    monkeypatch.setattr(V, "PARTS", len(parts))


def test_the_guards_refuse_a_build_or_stored_floors_that_do_not_cover_the_draw(monkeypatch, world):
    parts = _parts(6)
    keys = [p["pkey"] for p in parts]
    _guarded(monkeypatch, world, parts)
    ctx = VF.require_floors()
    assert sorted(ctx["shas"]) == ["answers", "build", "floors"] and ctx["draw"]["parts"] == parts
    _guarded(monkeypatch, world, parts, build_parts={k: {"guitars": {}} for k in keys[:-1]})
    with pytest.raises(SystemExit, match="do not cover the same parts"):
        VF.require_floors()
    bp = {k: {"guitars": {g: {"audio_sha256": "a", "file_sha256": "f"} for g in VF.ORDER}} for k in keys}
    del bp[keys[2]]["guitars"]["avg+mild"]
    _guarded(monkeypatch, world, parts, build_parts=bp)
    with pytest.raises(SystemExit, match="every rendered guitar") as e:
        VF.require_floors()
    assert keys[2] not in str(e.value) and V.tag(keys[2]) in str(e.value)
    st = {k: {"true": {"held": 1.0}, "tr-di": {"held": 2.0}} for k in keys}
    st[keys[1]]["true"]["held"] = math.inf
    _guarded(monkeypatch, world, parts, stored=st)
    with pytest.raises(SystemExit, match="stored floor is not finite"):
        VF.require_floors()
    _guarded(monkeypatch, world, parts, answers={"parts": {k: {} for k in keys[1:]}})
    with pytest.raises(SystemExit, match="row \\(b\\) has no answer"):
        VF.require_floors()
    _guarded(monkeypatch, world, parts, proofs=None)
    with pytest.raises(SystemExit, match="proofs did not hold"):
        VF.require_floors()


def test_guards_run_before_numpy_or_any_render():
    code = ("import sys; from learn import scratch_voice as V, voice_floors as VF\n"
            "def no(*a): raise SystemExit('refused')\n"
            "V.require_voice = no\n"
            "VF.RealWorld.render = lambda *a: print('RENDERED')\n"
            "try:\n    VF.main(['floor', '--shard', '0/3'])\nexcept SystemExit as e:\n    print(e)\n"
            "print('numpy' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["refused", "False"]


# --- the main pass ----------------------------------------------------------------------------------------------------

def test_every_guitar_floored_once_a_part(world):
    parts = _parts(6)
    w = Fake(parts)
    total = _shard_all(w)
    assert total == len(parts) * len(VF.ORDER) * 2 + len(VF.STORED) * V.CHECK_PARTS * 2
    floor_calls = [c for c in w.calls if c[1] in VF.ORDER]
    assert sorted(floor_calls) == sorted((p["pkey"], g) for p in parts for g in VF.ORDER)
    assert w.caps == 3                                     # one render slot a shard
    for p in parts:
        r = _rec(p["pkey"])
        assert sorted(r["guitars"]) == sorted(VF.ORDER) and r["tag"] == V.tag(p["pkey"])
        for g, x in r["guitars"].items():
            assert set(x) == set(VF.FIELDS) and x["refused"] is None and x["reran"] is False
            assert x["dry_sha256"] == _h("d", g, p["pkey"]) and x["carried_from"] is None
        assert r["renders"] == 10 and not VF.first_path(p["pkey"]).exists()
    recs = {p["pkey"]: _rec(p["pkey"]) for p in parts}
    floors, why = V.floors_of(w.stored, recs)                # Unit A's read takes the records as they are
    assert why == {} and V.pending_reruns(recs) == []
    assert floors[parts[0]["pkey"]] == {"true": 1.0, "tr-di": 2.0, "vc-fin": 3.0, "vc-cut": 4.0, "vc-own": 5.0,
                                        "vc-env": 6.0, "avg+mild": 7.0}


def test_no_part_key_in_any_record_or_log(world):
    parts = _parts(6)
    w = Fake(parts, refuse={(parts[4]["pkey"], "vc-own"): 1})
    _shard_all(w)
    _shard_all(w, rerun=True)
    text = "\n".join(p.read_text() for p in world.rglob("*.json")) + "\n".join(w.logs)
    for p in parts:
        assert p["pkey"] not in text and p["pkey"].split("|")[0] not in text and "part-" not in text


def test_a_record_is_written_once(world):
    parts = _parts(6)
    w = Fake(parts)
    _shard_all(w)
    before = {p["pkey"]: V.floor_path(p["pkey"]).read_bytes() for p in parts}
    w.calls.clear()
    assert _shard_all(w) == 0 and w.calls == []                # a part with a record is never rendered again
    assert {p["pkey"]: V.floor_path(p["pkey"]).read_bytes() for p in parts} == before
    with pytest.raises(SystemExit, match="never overwritten"):
        VF.floor_part(w, parts[0]["pkey"])
    with pytest.raises(SystemExit, match="never overwritten"):
        VF.write_once(V.floor_path(parts[0]["pkey"]), {"x": 1}, "t")
    assert V.floor_path(parts[0]["pkey"]).read_bytes() == before[parts[0]["pkey"]]
    assert not list(world.rglob("*.tmp"))


def test_write_once_never_writes_nan(world):
    with pytest.raises(ValueError):
        VF.write_once(world / "x" / "y.json", {"held": math.inf})
    assert not (world / "x" / "y.json").exists() and not list(world.rglob("*.tmp"))


def test_the_disk_guard_stops_before_a_part(world):
    assert VF.disk_refusal(31.2) is None and VF.disk_refusal(31.05) and VF.disk_refusal(10.0)
    parts = _parts(6)
    w = Fake(parts, free=31.05)
    with pytest.raises(SystemExit, match="DISK GUARD"):
        VF.run_floor(_args(shard=(0, 3)), w)
    assert w.calls == [] and not list(world.rglob("*.json"))


# --- the repeat check -------------------------------------------------------------------------------------------------

def test_the_repeat_check_runs_first_on_the_two_check_parts(world):
    parts = _parts(6)
    w = Fake(parts)
    VF.run_floor(_args(shard=(0, 3)), w)
    ck = V.check_parts(parts)
    assert len(ck) == 2 and w.calls[:4] == [(k, g) for k in ck for g in VF.STORED]
    for k in ck:
        r = json.loads(V.repeat_path(k).read_text())
        assert r["holds"] is True and r["renders"] == 4 and r["tag"] == V.tag(k)
        assert all(x["distance_repeats"] and x["sha_repeats"] for x in r["guitars"].values())
    w.calls.clear()
    VF.run_floor(_args(shard=(0, 3)), w)                     # held records are not rendered again
    assert w.calls == []


@pytest.mark.parametrize("off", [(2.0000001, None), (None, "other")])
def test_a_repeat_mismatch_stops_everything(world, off):
    parts = _parts(6)
    ck = V.check_parts(parts)
    k0 = ck[0]
    held, sha = off
    w = Fake(parts, stored_off={(k0, "tr-di"): (held or 2.0, sha or _h("b", k0))})
    with pytest.raises(SystemExit, match="REPEAT MISMATCH"):
        VF.run_floor(_args(shard=(0, 3)), w)
    assert w.calls == [(k0, "true"), (k0, "tr-di")]          # nothing after the mismatch
    r = json.loads(V.repeat_path(k0).read_text())
    assert r["holds"] is False and r["guitars"]["true"]["holds"] and not r["guitars"]["tr-di"]["holds"]
    assert not (world / "floors").exists() and not (world / "floors-first").exists()
    for k in (1, 2):                                         # the other shards stop at once, rendering nothing
        w2 = Fake(parts)
        with pytest.raises(SystemExit, match="REPEAT MISMATCH"):
            VF.run_floor(_args(shard=(k, 3)), w2)
        assert w2.calls == [] and w2.caps == 0
    w3 = Fake(parts)                                         # shard 0 again: the stored failure stops it
    with pytest.raises(SystemExit, match="REPEAT MISMATCH"):
        VF.run_floor(_args(shard=(0, 3)), w3)
    assert w3.calls == []
    with pytest.raises(SystemExit, match="repeat check fails"):
        VF.run_floor(_args(shard=(1, 3), rerun=True), Fake(parts))


def test_the_other_shards_wait_for_the_repeat_and_take_no_slot_meanwhile(world):
    parts = _parts(6)
    w = Fake(parts)
    with pytest.raises(SystemExit, match="did not finish"):
        VF.run_floor(_args(shard=(1, 3)), w)
    assert w.calls == [] and w.caps == 0 and w.t >= VF.REPEAT_WAIT_S
    w0 = Fake(parts)
    VF.run_floor(_args(shard=(0, 3)), w0)
    w1 = Fake(parts)
    VF.run_floor(_args(shard=(1, 3)), w1)
    assert w1.caps == 1 and {c[1] for c in w1.calls} <= set(VF.ORDER) and w1.t == 0


def test_repeat_state_and_verdict():
    assert VF.repeat_state({}) == "pending"
    assert VF.repeat_state({"a": {"holds": True}, "b": None}) == "pending"
    assert VF.repeat_state({"a": {"holds": True}, "b": {"holds": True}}) == "holds"
    assert VF.repeat_state({"a": {"holds": False}, "b": None}) == "fails"
    assert VF.repeat_state({"a": {"holds": True}, "b": {}}) == "fails"
    st = {"true": {"held": 1.0, "audio_sha256": "x"}, "tr-di": {"held": 2.0, "audio_sha256": "y"}}
    assert VF.repeat_verdict(st, st)["holds"] is True
    assert VF.repeat_verdict(dict(st, true={"held": None, "audio_sha256": "x"}), dict(
        st, true={"held": None, "audio_sha256": "x"}))["holds"] is False      # no distance never repeats
    assert VF.repeat_verdict({"true": st["true"]}, st)["holds"] is False


# --- S1: refusals and the rerun ---------------------------------------------------------------------------------------

def test_refusal_reasons_are_fixed_and_key_free():
    assert VF.refusal_of(True, 1.0) is None
    assert VF.refusal_of(False, 1.0) == VF.REASONS["nonfinite_render"]
    assert VF.refusal_of(True, math.inf) == VF.REASONS["no_distance"]
    assert VF.refusal_of(True, math.nan) == VF.REASONS["nonfinite_distance"]
    assert VF.refusal_of(True, None) == VF.REASONS["nonfinite_distance"]
    assert VF.refusal_of(True, 0.0) == VF.REASONS["nonpositive_distance"]
    assert VF.refusal_of(True, -1.0) == VF.REASONS["nonpositive_distance"]
    for r in VF.REASONS.values():
        assert "/" not in r and "|" not in r and "PF" not in r


def test_a_refusal_is_recorded_first_and_never_in_floors(world):
    parts = _parts(6)
    k = parts[4]["pkey"]
    w = Fake(parts, refuse={(k, "vc-cut"): 5})
    _shard_all(w)
    assert not V.floor_path(k).exists()
    first = json.loads(VF.first_path(k).read_text())
    x = first["guitars"]["vc-cut"]
    assert x["refused"] == VF.REASONS["no_distance"] and x["held"] is None and x["reran"] is False
    assert VF.refused_guitars(first) == ["vc-cut"]
    assert [g for g, r in first["guitars"].items() if r["refused"]] == ["vc-cut"]
    assert k not in VF.first_path(k).read_text()


def test_rerun_reruns_only_the_refused_and_records_a_second_refusal(world):
    parts = _parts(6)
    k1, k2 = parts[1]["pkey"], parts[4]["pkey"]
    w = Fake(parts, refuse={(k1, "vc-own"): 1, (k2, "avg+mild"): 2})
    _shard_all(w)
    firsts = {k: VF.first_path(k).read_text() for k in (k1, k2)}
    w.calls.clear()
    _shard_all(w, rerun=True)
    assert sorted(w.calls) == sorted([(k1, "vc-own"), (k2, "avg+mild")])
    r1, r2 = _rec(k1), _rec(k2)
    assert r1["guitars"]["vc-own"] == {"held": 5.0, "audio_sha256": _h("r", "vc-own", k1),
                                       "dry_sha256": _h("d", "vc-own", k1),
                                       "refused": None, "reran": True, "carried_from": None}
    assert r2["guitars"]["avg+mild"]["refused"] == VF.REASONS["no_distance"] and r2["guitars"]["avg+mild"]["reran"]
    for k, r in ((k1, r1), (k2, r2)):
        first = json.loads(firsts[k])
        for g in VF.ORDER:
            if not first["guitars"][g]["refused"]:
                assert r["guitars"][g] == first["guitars"][g]           # the passing guitars byte for byte
        assert r["rerun_renders"] == 2 and r["renders"] == 12 and VF.first_path(k).read_text() == firsts[k]
    recs = {p["pkey"]: _rec(p["pkey"]) for p in parts}
    assert V.pending_reruns(recs) == []
    floors, why = V.floors_of(w.stored, recs)
    assert floors[k2]["avg+mild"] is None and why == {k2: {"avg+mild": VF.REASONS["no_distance"]}}
    assert floors[k1]["vc-own"] == 5.0
    w.calls.clear()
    assert _shard_all(w, rerun=True) == 0 and w.calls == []       # once only
    assert _shard_all(w) == 0 and w.calls == []                   # and the main pass leaves them alone


def test_rerun_waits_for_the_repeat_check(world):
    parts = _parts(6)
    with pytest.raises(SystemExit, match="repeat check pending"):
        VF.run_floor(_args(shard=(0, 3), rerun=True), Fake(parts))


# --- the carry --------------------------------------------------------------------------------------------------------

def test_a_byte_identical_guitar_is_carried_without_a_render(world):
    parts = _parts(6)
    k = parts[0]["pkey"]
    w = Fake(parts, same={(k, "vc-env"): "vc-fin", (k, "avg+mild"): "tr-di"})
    _shard_all(w)
    rendered = [g for kk, g in w.calls if kk == k and g in VF.ORDER]
    assert rendered == ["vc-fin", "vc-cut", "vc-own"]
    r = _rec(k)
    assert r["guitars"]["vc-env"] == dict(r["guitars"]["vc-fin"], carried_from="vc-fin")
    assert r["guitars"]["avg+mild"] == {"held": 2.0, "audio_sha256": _h("b", k), "dry_sha256": _h("d", "tr-di", k),
                                        "refused": None, "reran": False, "carried_from": "tr-di"}
    assert r["renders"] == 6
    floors, why = V.floors_of(w.stored, {k: r})
    assert floors[k]["vc-env"] == floors[k]["vc-fin"] and floors[k]["avg+mild"] == 2.0 and why == {}


def test_a_carry_from_a_refused_guitar_is_rerun_with_it(world):
    parts = _parts(6)
    k = parts[2]["pkey"]
    w = Fake(parts, refuse={(k, "vc-cut"): 1}, same={(k, "vc-own"): "vc-cut"})
    _shard_all(w)
    first = json.loads(VF.first_path(k).read_text())
    assert VF.refused_guitars(first) == ["vc-cut", "vc-own"] and first["guitars"]["vc-own"]["carried_from"] == "vc-cut"
    w.calls.clear()
    _shard_all(w, rerun=True)
    assert w.calls == [(k, "vc-cut")]
    r = _rec(k)
    assert r["guitars"]["vc-own"] == dict(r["guitars"]["vc-cut"], carried_from="vc-cut")
    assert r["guitars"]["vc-own"]["reran"] and r["guitars"]["vc-cut"]["refused"] is None


def test_carry_source():
    assert VF.carry_source("x", [("true", "a"), ("tr-di", "x"), ("vc-fin", "x")]) == "tr-di"
    assert VF.carry_source("x", [("true", "a")]) is None
    assert VF.carry_source(None, [("true", None)]) is None


def test_a_guitar_without_a_declared_sha_refuses_before_its_render():
    calls = []
    with pytest.raises(SystemExit, match="no declared dry sha256"):
        VF.floor_guitars(["vc-fin"], {}, lambda g: calls.append(g), {g: {"held": 1.0} for g in VF.STORED})
    assert calls == []


# --- the real world's loading (no numpy needed for the refusals) ------------------------------------------------------

def test_the_dry_files():
    assert VF.dry_file("vc-own", "a/b") == V.dry_path("vc-own", "a/b")
    nr = pytest.importorskip("learn.note_replay")
    assert VF.dry_file("avg+mild", "a/b") == nr.blur_path("avg+mild", "a/b")


# --- the review's additions: the real world behind patched renders, crashes, the wait, the disk in the repeat -------

def _real(monkeypatch, tmp_path, n=1000, lo=10, hi=900):
    """A RealWorld on a made-up context: the section, the record, the answer and every render patched (numpy only)."""
    np = pytest.importorskip("numpy")
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import note_transcribe as NT
    from learn import pipeline_fix as P

    parts = [{"pkey": "bks/k0|u0", "set": "bks", "unit": "u0", "amp": "a", "lag": 3, "held": "B"},
             {"pkey": "goat/k1|u1", "set": "goat", "unit": "u1", "amp": "a", "lag": 0, "held": "A"}]
    pk = parts[0]["pkey"]
    rng = np.random.default_rng(0)
    di32 = rng.standard_normal(n).astype(np.float32)
    tr32 = rng.standard_normal(n).astype(np.float32)
    clean = rng.standard_normal(n)
    monkeypatch.setattr(R, "di_section", lambda prt: di32)
    monkeypatch.setattr(SE, "_trim", lambda: (lo, hi))
    monkeypatch.setattr(P, "real_amp_track", lambda sd, track, start: clean)
    monkeypatch.setattr(LO, "tdict", lambda a: {"x": a})
    monkeypatch.setattr(NT, "load_dry", lambda arm, key, b2: tr32)
    monkeypatch.setattr(R, "blur_path", lambda dry, k: tmp_path / "blur" / f"{SE._f(k)}.npy")
    guitars = {}
    for g in VF.ORDER:
        x = (rng.standard_normal(n) * 0.1).astype(np.float32)
        path = VF.dry_file(g, pk)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, x)
        guitars[g] = {"file_sha256": S.file_sha(path), "audio_sha256": S.npy_sha(x)}
    sd = type("SD", (), {"units": {(p["set"], p["unit"], p["amp"]): {"prt": {"sd": "s", "track": "t", "start_s": 1.0}}
                                   for p in parts}})()
    ctx = {"draw": {"parts": parts}, "sd": sd, "b2": {}, "stored": {}, "shas": {},
           "answers": {"parts": {pk: {"select": "sel", "answer": "ans"}}},
           "build": {"parts": {pk: {"guitars": guitars}}}}
    calls = {"render": [], "judge": []}
    out = {"y": None}

    def fresh(make, x, sel, xp, xk):
        calls["render"].append((make, x, sel, xp, xk))
        return np.arange(n, dtype=np.float64) * 1e-3 if out["y"] is None else out["y"]

    def judge(ref, y, di, lag, half):
        calls["judge"].append((ref, y, di, lag, half))
        return 0.5

    monkeypatch.setattr(AM, "fresh_render", fresh)
    monkeypatch.setattr(R, "half_distance", judge)
    return np, VF.RealWorld(ctx), pk, calls, out, (di32, tr32, clean, CB, AM)


def test_the_real_render_calls_exactly_as_the_real_floor_does(monkeypatch, world):
    np, w, pk, calls, out, (di32, tr32, clean, CB, AM) = _real(monkeypatch, world)
    held, sha, finite = w.render(pk, "vc-own")
    (make, x, sel, xp, xk), = calls["render"]
    assert make is CB.new_renderer and sel == "sel" and xp == xk == {"x": "ans"}
    assert np.array_equal(x, np.load(V.dry_path("vc-own", pk))) and x.dtype == np.float32
    (ref, y, di, lag, half), = calls["judge"]
    assert ref is clean and lag == 3 and half == "B"
    assert np.array_equal(y, (np.arange(1000) * 1e-3)[10:900]) and np.array_equal(di, di32.astype(np.float64)[10:900])
    assert (held, finite) == (0.5, True) and sha == AM.audio_sha((np.arange(1000) * 1e-3)[10:900])
    w.render(pk, "true")
    w.render(pk, "tr-di")
    assert calls["render"][1][1] is di32 and calls["render"][2][1] is tr32      # the stored guitars as stored
    assert w.dry_shas(pk)["true"] == S.npy_sha(di32) and w.dry_shas(pk)["tr-di"] == S.npy_sha(tr32)
    assert w.dry_shas(pk)["avg+mild"] == w.ctx["build"]["parts"][pk]["guitars"]["avg+mild"]["audio_sha256"]
    out["y"] = np.full(1000, np.nan)
    held, sha, finite = w.render(pk, "avg+mild")
    assert held == math.inf and finite is False and len(calls["judge"]) == 3   # no judge on a non-finite render
    assert sha == AM.audio_sha(np.zeros(890))
    assert VF.render_floor(held, sha, finite, "d")["refused"] == VF.REASONS["nonfinite_render"]


def test_the_real_load_refuses_another_file_other_samples_or_length(monkeypatch, world):
    np, w, pk, calls, out, _ = _real(monkeypatch, world)
    ent = w.ctx["build"]["parts"][pk]["guitars"]
    good = dict(ent["vc-fin"])
    ent["vc-fin"] = dict(good, file_sha256="0" * 64)
    with pytest.raises(SystemExit, match="file is not build.json's") as e:
        w.render(pk, "vc-fin")
    assert pk not in str(e.value)
    ent["vc-fin"] = dict(good, audio_sha256="0" * 64)
    with pytest.raises(SystemExit, match="samples are not build.json's"):
        w.render(pk, "vc-fin")
    short = np.zeros(999, np.float32)
    np.save(V.dry_path("vc-cut", pk), short)
    ent["vc-cut"] = {"file_sha256": S.file_sha(V.dry_path("vc-cut", pk)), "audio_sha256": S.npy_sha(short)}
    with pytest.raises(SystemExit, match="section's length"):
        w.render(pk, "vc-cut")
    V.dry_path("vc-own", pk).unlink()
    with pytest.raises(SystemExit, match="file is not build.json's"):
        w.render(pk, "vc-own")
    assert calls["render"] == []                          # every refusal before the render


class Crash(Fake):
    def __init__(self, parts, at, **kw):
        super().__init__(parts, **kw)
        self.at = at

    def render(self, pk, g):
        if (pk, g) == self.at:
            self.at = None
            self.calls.append((pk, g))
            raise RuntimeError("the plugin server died")
        return super().render(pk, g)


def test_a_render_exception_mid_part_writes_nothing_and_a_restart_renders_it_again(world):
    parts = _parts(6)
    k = VF.mine(parts, (1, 3))[0]["pkey"]
    VF.run_floor(_args(shard=(0, 3)), Fake(parts))
    w = Crash(parts, (k, "vc-own"))
    with pytest.raises(RuntimeError):
        VF.run_floor(_args(shard=(1, 3)), w)
    assert not V.floor_path(k).exists() and not VF.first_path(k).exists() and not list(world.rglob("*.tmp"))
    w.calls.clear()
    VF.run_floor(_args(shard=(1, 3)), w)
    assert [g for kk, g in w.calls if kk == k] == list(VF.ORDER)
    assert _rec(k)["renders"] == 10 and VF.refused_guitars(_rec(k)) == []


class Later(Fake):
    """The repeat records appear after `polls` sleeps (shard 0 working meanwhile)."""

    def __init__(self, parts, polls, **kw):
        super().__init__(parts, **kw)
        self.polls, self.slept = polls, 0

    def sleep(self, s):
        super().sleep(s)
        self.slept += 1
        if self.slept == self.polls:
            VF.run_repeat(Fake(self.parts))


def test_the_wait_goes_from_pending_to_holds_after_a_few_polls(world):
    parts = _parts(6)
    w = Later(parts, 3)
    VF.run_floor(_args(shard=(2, 3)), w)
    assert w.slept == 3 and w.t == 3 * VF.REPEAT_POLL_S and w.caps == 1
    assert {g for _, g in w.calls} == set(VF.ORDER)
    assert all(V.floor_path(p["pkey"]).exists() for p in VF.mine(parts, (2, 3)))


class Draining(Fake):
    def __init__(self, parts, frees, **kw):
        super().__init__(parts, **kw)
        self.frees = list(frees)

    def free_gb(self):
        return self.frees.pop(0)


def test_the_disk_guard_fires_inside_the_repeat_check(world):
    parts = _parts(6)
    ck = V.check_parts(parts)
    w = Draining(parts, [31.05])
    with pytest.raises(SystemExit, match="DISK GUARD"):
        VF.run_repeat(w)
    assert w.calls == [] and not (world / "repeat").exists()
    w = Draining(parts, [100.0, 31.05])                   # room for the first check part only
    with pytest.raises(SystemExit, match="DISK GUARD"):
        VF.run_floor(_args(shard=(0, 3)), w)
    assert w.calls == [(ck[0], g) for g in VF.STORED]
    assert V.repeat_path(ck[0]).exists() and not V.repeat_path(ck[1]).exists() and not (world / "floors").exists()


def test_a_rerun_refuses_a_first_pass_on_other_inputs(world):
    parts = _parts(6)
    k = parts[4]["pkey"]
    w = Fake(parts, refuse={(k, "vc-cut"): 1})
    _shard_all(w)
    for f in VF.SHA_FIELDS:
        w2 = Fake(parts)
        w2.shas = dict(w.shas, **{f: "9" * 64})
        with pytest.raises(SystemExit, match=f"another {f} file") as e:
            VF.rerun_part(w2, k)
        assert k not in str(e.value) and w2.calls == [] and not V.floor_path(k).exists()
    VF.rerun_part(Fake(parts), k)
    assert _rec(k)["guitars"]["vc-cut"]["reran"] is True


def test_write_once_leaves_no_temp_file_when_the_write_fails(world, monkeypatch):
    def boom(*a, **kw):
        raise OSError("disk full")
    monkeypatch.setattr(VF.os, "link", boom)
    with pytest.raises(OSError):
        VF.write_once(world / "z" / "a.json", {"x": 1})
    assert not (world / "z" / "a.json").exists() and not list(world.rglob("*.tmp"))
    monkeypatch.undo()
    monkeypatch.setattr(pathlib.Path, "write_text", lambda self, t: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError):
        VF.write_once(world / "z" / "b.json", {"x": 1})
    assert not list(world.rglob("*.tmp")) and not (world / "z" / "b.json").exists()
