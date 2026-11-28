"""The spectral-envelope steps' floors (`learn/envelope_floors.py`) on this run's own world behind fakes (no numpy, no
renders): `voice_floors.run_floor` makes the same calls as on the control's world (its own 8 repeat renders of tr-di
and vc-own on the two check parts first, then the five guitars of every part in order), writes only under
PF/fs/envelope/ while the sound-gap test's and the control's records exist, carries name their source, a repeat
mismatch stops everything, the other shards wait for this run's own repeat, the rerun reruns only the refused, and no
render runs before the guards. Made-up keys only."""
import hashlib
import json
import math

import pytest

from learn import envelope_floors as EF
from learn import scratch_envelope as E
from learn import scratch_search as S
from learn import scratch_voice as V
from learn import voice_control as VC
from learn import voice_floors as VF


def _h(*a):
    return hashlib.sha256("|".join(a).encode()).hexdigest()


def _args(**kw):
    return type("A", (), dict({"rerun": False}, **kw))()


def _parts(n=6):
    sets = ["bks", "goat", "panel"]
    return [{"pkey": f"{sets[i % 3]}/fake{i}", "set": sets[i % 3], "lag": 0, "held": "A"} for i in range(n)]


HELD = {"vt-part": 1.99, "vt-group": 1.7, "vt-win": 1.4, "vt-mag": 1.5, "vt-phase": 1.9}


class Fake(EF.EnvelopeRuns):
    """This run's guitars and paths (EF.EnvelopeRuns, as EnvelopeWorld carries them) on made-up renders: `carry`
    {pkey} makes vt-part byte-identical to tr-di; `refuse` {(pkey, guitar): times}."""

    def __init__(self, parts, carry=(), refuse=None, stored_off=None):
        self.parts, self.check_keys = parts, V.check_parts(parts)
        self.stored = {p["pkey"]: {"tr-di": {"held": 2.0, "audio_sha256": _h("b", p["pkey"])},
                                   "vc-own": {"held": 1.2, "audio_sha256": _h("o", p["pkey"])}} for p in parts}
        self.shas = {f: f[0].upper() * 64 for f in EF.SHA_FIELDS}
        self.carry, self.refuse, self.stored_off = set(carry), dict(refuse or {}), dict(stored_off or {})
        self.calls, self.logs, self.caps, self.t = [], [], 0, 0.0

    def render(self, pk, g):
        self.calls.append((pk, g))
        if self.refuse.get((pk, g), 0) > 0:
            self.refuse[(pk, g)] -= 1
            return math.inf, _h("silent", g), True
        if g in E.STORED:
            h, sha = self.stored_off.get((pk, g), (self.stored[pk][g]["held"], self.stored[pk][g]["audio_sha256"]))
            return h, sha, True
        return HELD[g], _h("r", g, pk), True

    def dry_shas(self, pk):
        out = {g: _h("d", g, pk) for g in E.STORED + E.BUILT}
        if pk in self.carry:
            out["vt-part"] = out["tr-di"]
        return out

    def free_gb(self):
        return 100.0

    def wait_cap(self):
        self.caps += 1

    def clock(self):
        return self.t

    def sleep(self, s):
        self.t += s

    def now(self):
        return "2026-11-28 00:00:00"

    def log(self, msg):
        self.logs.append(msg)


class ControlFake(VC.ControlRuns, Fake):
    """The control's world on the same fake renders: the reference for "the same calls"."""

    def render(self, pk, g):
        self.calls.append((pk, g))
        if g in VC.STORED:
            return self.stored[pk][g]["held"], self.stored[pk][g]["audio_sha256"], True
        return 1.0, _h("r", g, pk), True

    def dry_shas(self, pk):
        return {g: _h("d", g, pk) for g in VC.FOUR}


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "fs_dir", lambda: tmp_path / "fs")
    return tmp_path / "fs"


def _old_records(parts):
    """The sound-gap test's and the control's records as they sit on disk: repeat/ (held) and floors/."""
    olds = []
    for k in V.check_parts(parts):
        for path in (V.repeat_path(k), VC.repeat_path(k)):
            VF.write_once(path, {"holds": True, "tag": V.tag(k)}, V.tag(k))
            olds.append(path)
    for p in parts:
        for path in (V.floor_path(p["pkey"]), VC.floor_path(p["pkey"])):
            VF.write_once(path, {"guitars": {}}, V.tag(p["pkey"]))
            olds.append(path)
    return {q: q.read_bytes() for q in olds}


def _shard_all(w, rerun=False):
    return sum(VF.run_floor(_args(shard=(k, 3), rerun=rerun), w) for k in range(3))


def test_the_runs_attributes():
    assert EF.EnvelopeRuns.order == E.BUILT and EF.EnvelopeRuns.stored_guitars == E.STORED == ("tr-di", "vc-own")
    assert EF.EnvelopeRuns.repeat_guitars == E.STORED and EF.EnvelopeRuns.plan == E.PLAN
    assert EF.SHA_FIELDS == ("build", "answers", "floors", "voice_rows", "voice_build")
    assert issubclass(EF.EnvelopeWorld, VF.RealWorld) and issubclass(EF.EnvelopeWorld, EF.EnvelopeRuns)
    f = Fake(_parts(3))
    assert VF.w_order(f) == E.BUILT and VF.w_stored(f) == VF.w_repeat(f) == E.STORED
    assert VF.w_floor_path(f, "a/b") == E.floor_path("a/b") and VF.w_repeat_path(f, "a/b") == E.repeat_path("a/b")
    assert VF.w_first_path(f, "a/b") == E.first_path("a/b") and VF.w_label(f) == "ENVELOPE FLOORS"


def test_the_same_calls_as_the_controls_floors(world):
    parts = _parts(6)
    w = Fake(parts)
    _shard_all(w)
    c = ControlFake(parts)                                          # the control's run, its own paths
    _shard_all(c)
    ck = V.check_parts(parts)
    assert w.calls[:4] == c.calls[:4] == [(k, g) for k in ck for g in ("tr-di", "vc-own")]   # the same repeat
    order = [p["pkey"] for k in range(3) for p in VF.mine(parts, (k, 3))]
    assert w.calls[4:] == [(pk, g) for pk in order for g in E.BUILT]
    assert c.calls[4:] == [(pk, g) for pk in order for g in VC.BUILT]
    assert w.caps == c.caps == 3


def test_its_own_repeat_and_writes_only_under_envelope(world):
    parts = _parts(6)
    old = _old_records(parts)
    carry = {parts[1]["pkey"]}
    w = Fake(parts, carry=carry)
    total = _shard_all(w)
    assert total == 8 + (len(parts) * len(E.BUILT) - len(carry)) * 2
    assert {q: q.read_bytes() for q in old} == old                  # the other runs' records untouched
    new = [q for q in world.rglob("*.json") if q not in old]
    assert new and all(q.relative_to(world).parts[0] == "envelope" for q in new)
    for k in V.check_parts(parts):
        r = json.loads(E.repeat_path(k).read_text())
        assert r["holds"] is True and r["renders"] == 4 and sorted(r["guitars"]) == sorted(E.STORED)
        assert r["plan"] == E.PLAN
    for p in parts:
        r = json.loads(E.floor_path(p["pkey"]).read_text())
        assert sorted(r["guitars"]) == sorted(E.BUILT) and all(f"{f}_sha256" in r for f in EF.SHA_FIELDS)
        if p["pkey"] in carry:
            assert r["guitars"]["vt-part"]["carried_from"] == "tr-di" and r["guitars"]["vt-part"]["held"] == 2.0
        else:
            assert all(x["carried_from"] is None for x in r["guitars"].values()) and r["renders"] == 10
    assert any("ENVELOPE FLOORS" in m for m in w.logs)
    text = "\n".join(q.read_text() for q in new) + "\n".join(w.logs)
    assert all(p["pkey"] not in text and "fake" not in text for p in parts)


def test_a_repeat_mismatch_stops_everything(world):
    parts = _parts(6)
    _old_records(parts)                                       # the other runs' held records do not stand in
    k0 = V.check_parts(parts)[0]
    w = Fake(parts, stored_off={(k0, "vc-own"): (1.2000001, _h("o", k0))})
    with pytest.raises(SystemExit, match="REPEAT MISMATCH"):
        VF.run_floor(_args(shard=(0, 3)), w)
    assert w.calls == [(k0, "tr-di"), (k0, "vc-own")]
    assert not (world / "envelope" / "floors").exists()
    w2 = Fake(parts)
    with pytest.raises(SystemExit, match="REPEAT MISMATCH"):
        VF.run_floor(_args(shard=(1, 3)), w2)
    assert w2.calls == [] and w2.caps == 0


def test_the_other_shards_wait_for_this_runs_own_repeat(world):
    parts = _parts(6)
    _old_records(parts)
    w = Fake(parts)
    with pytest.raises(SystemExit, match="did not finish"):
        VF.run_floor(_args(shard=(1, 3)), w)
    assert w.calls == [] and w.caps == 0


def test_the_rerun_reruns_only_the_refused(world):
    parts = _parts(6)
    k = parts[4]["pkey"]
    w = Fake(parts, refuse={(k, "vt-mag"): 1})
    _shard_all(w)
    assert not E.floor_path(k).exists() and E.first_path(k).exists()
    w.calls.clear()
    _shard_all(w, rerun=True)
    assert w.calls == [(k, "vt-mag")]
    r = json.loads(E.floor_path(k).read_text())
    assert r["guitars"]["vt-mag"]["reran"] is True and r["guitars"]["vt-mag"]["refused"] is None
    recs = {p["pkey"]: json.loads(E.floor_path(p["pkey"]).read_text()) for p in parts}
    assert V.pending_reruns(recs) == []
    build = {"parts": {p["pkey"]: {"guitars": {g: {"audio_sha256": _h("d", g, p["pkey"])} for g in E.BUILT}}
                       for p in parts}}
    st = {p["pkey"]: w.stored[p["pkey"]] for p in parts}
    fl, why = E.floors_of(st, recs, build)                     # the read takes the records as written
    assert fl[k]["vt-mag"] == HELD["vt-mag"] and why == {}


def test_no_render_before_the_guards(monkeypatch, world):
    calls = []
    monkeypatch.setattr(EF.EnvelopeWorld, "render", lambda self, pk, g: calls.append((pk, g)))
    with pytest.raises(SystemExit, match="one render process a shard"):
        EF.cmd_floor(_args(shard=(0, 2)))
    monkeypatch.setattr(E, "require_envelope", lambda *a: (_ for _ in ()).throw(SystemExit("differ from main's")))
    with pytest.raises(SystemExit, match="differ from main's"):
        EF.cmd_floor(_args(shard=(0, 3)))
    asked = []
    monkeypatch.setattr(E, "require_envelope", lambda *a: asked.append(a) or {})
    with pytest.raises(SystemExit, match="no envelope build.json"):
        EF.cmd_floor(_args(shard=(0, 3)))
    assert asked[0] == (E.PHASE_DRY,)
    assert calls == []
