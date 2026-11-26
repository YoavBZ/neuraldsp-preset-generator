"""The sound-gap test's builders (`learn/voice_build.py`, Unit B of `docs/scratch-voice-plan.md`): the windows from the
trace, the notches, the gate (maximum, never sum; each end kind's fade; the edge fade), the all-pass identity, the
envelope gain within +-20 dB, two runs byte-identical, the records and build.json, write-once, the guards off main, no
numpy at import. Synthetic keys and signals only; tests that touch numpy skip on the light CI runner."""
import ast
import hashlib
import json
import math
import pathlib
import random
import subprocess
import sys

import pytest

from learn import note_rebuild as NR
from learn import scratch_exact as SE
from learn import scratch_search as S
from learn import scratch_voice as V
from learn import voice_build as VB

REPO = pathlib.Path(__file__).resolve().parents[1]
SR = NR.SR


def _args(**kw):
    return type("A", (), dict(kw))()


# --- names, constants, imports (pure) ---------------------------------------------------------------------------------

def test_every_constant_is_note_rebuilds_or_the_cores():
    assert VB.BUILT == V.BUILT == ("vc-fin", "vc-cut", "vc-own", "vc-env")
    assert VB.GUITARS == V.BUILT + ("avg+mild",) and VB.PROOFS == V.PROOFS and VB.FIN_PROOF_TOL == V.FIN_PROOF_TOL
    assert VB.fade_in_samples() == int(NR.NOTE_FADE_IN_S * SR) == 96
    want = {"repluck": NR.REPLUCK_FADE_S, "mute": NR.MUTE_FADE_S, "release": NR.RING_SOFT_S, "sample": NR.TAIL_FADE_S,
            "cut": NR.REPLUCK_FADE_S}
    assert {k: VB.end_fade_samples(k) for k in want} == {k: int(round(v * SR)) for k, v in want.items()}
    assert VB.end_fade_samples("release") == VB.end_fade_samples("sample") == 7200
    assert VB.end_fade_samples("repluck") == 480 and VB.end_fade_samples("mute") == 1440
    with pytest.raises(ValueError):
        VB.end_fade_samples("legato")
    assert VB.edge_samples(10 * SR) == int(NR.EDGE_FADE_S * SR) == 480 and VB.edge_samples(100) == 50
    assert VB.EXTRA_CODE[0] == "learn/rederive_fit.py" and VB.MODULE in V.UNIT_FILES


def test_the_module_imports_only_the_standard_library_and_learn_at_module_level():
    tree = ast.parse((REPO / "learn" / "voice_build.py").read_text())
    mods = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            mods.add(node.module.split(".")[0])
    assert mods <= {"__future__", "argparse", "hashlib", "inspect", "json", "math", "pathlib", "time", "learn"}


def test_no_numpy_at_import():
    code = "import sys; import learn.voice_build; print('numpy' in sys.modules, 'scipy' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["False", "False"]


def test_the_part_files_sit_under_the_voice_dir():
    p = VB.part_path("bks/k/1")
    assert p.parent.name == "build-parts" and p.parent.parent == V.voice_dir() and p.name == "bks__k__1.json"
    assert p.parent != V.build_path().parent / "dry"


# --- the windows (pure) -----------------------------------------------------------------------------------------------

def test_own_windows_follow_the_trace_and_skip_the_skipped():
    notes = [{"on": 0.5, "off": 0.9}, {"on": 1.0, "off": 1.2}, {"on": 2.0, "off": 2.1}]
    trace = [{"played": True, "end": 1.0, "end_kind": "repluck"}, {"played": False, "why": "no free string"},
             {"played": True, "end": 2.25, "end_kind": "release"}]
    w = VB.own_windows(notes, trace)
    assert w == [(round((0.5 - 0.002) * SR), 48000, 96, 480), (round((2.0 - 0.002) * SR), 108000, 96, 7200)]
    with pytest.raises(ValueError):
        VB.own_windows(notes, trace[:2])
    with pytest.raises(ValueError):
        VB.own_windows(notes[:1], [{"played": True, "end": 1.0, "end_kind": "legato"}])


def test_cut_windows_put_one_notch_at_each_onset():
    n = 3 * SR
    w = VB.cut_windows([1.0, 0.5], n)                     # sorted inside
    assert w == [(0, 24000, 0, 480), (round(0.498 * SR), 48000, 96, 480), (round(0.998 * SR), n, 96, 0)]
    assert VB.cut_windows([], n) == [(0, n, 0, 0)]
    first = VB.cut_windows([0.005], n)[0]                 # a notch reaching before 0 keeps its full fade
    assert first == (240 - 480, 240, 0, 480)


def test_group_onsets_are_each_groups_first_onset():
    notes = [{"on": 1.0}, {"on": 0.5}, {"on": 0.52}, {"on": 1.049}, {"on": 2.0}]
    assert VB.group_onsets(notes) == [0.5, 1.0, 2.0]


# --- the records (pure) -----------------------------------------------------------------------------------------------

def test_ends_list_every_kind_and_refuse_an_unknown_one():
    assert VB.ends_of({"ends": {"release": 3, "repluck": 2}}) == {"release": 3, "repluck": 2, "mute": 0, "sample": 0,
                                                                  "cut": 0}
    assert VB.ends_of({}) == {k: 0 for k in V.END_KINDS}
    with pytest.raises(SystemExit, match="end kinds"):
        VB.ends_of({"ends": {"legato": 1}})


def test_proof_failures_name_every_failing_or_missing_proof():
    ok = {p: True for p in VB.PROOFS}
    assert VB.proof_failures(ok) == []
    assert VB.proof_failures(dict(ok, vc_fin_is_avg=False)) == ["vc_fin_is_avg"]
    assert VB.proof_failures({"rule_off_is_tr_di": True}) == list(VB.PROOFS[1:])
    assert VB.proof_failures(dict(ok, all_pass_is_vc_fin=1)) == ["all_pass_is_vc_fin"]   # only True holds


def test_git_blob_sha_is_gits(tmp_path):
    f = tmp_path / "x.py"
    f.write_bytes(b"print('x')\n")
    got = subprocess.run(["git", "hash-object", str(f)], capture_output=True, text=True)
    if got.returncode:
        pytest.skip("no git")
    assert VB.git_blob_sha(f.read_bytes()) == got.stdout.strip()
    ident = VB.code_identity()
    assert ident["scratch_readerr_blob_sha"] == VB.git_blob_sha((REPO / VB.READERR).read_bytes())
    assert len(ident["played_trace_sha256"]) == 64


IDENT = {"scratch_readerr_blob_sha": "a" * 40, "played_trace_sha256": "b" * 64}


def _rec(k, ok=True, ident=IDENT, gain=0.1):
    tag = V.tag(k)
    return {"plan": V.PLAN, "part": k, "tag": tag, "set": k.split("/")[0], "held": "B", "renders": 0,
            "code": dict(ident), "checks": {"raw_is_true_di": True},
            "proofs": {p: (ok or p != "vc_fin_is_avg") for p in VB.PROOFS}, "fin_ratio": 1e-7,
            "guitars": {g: {"file_sha256": hashlib.sha256(f"{g}{k}".encode()).hexdigest(),
                            "audio_sha256": hashlib.sha256(f"a{g}{k}".encode()).hexdigest()} for g in VB.GUITARS},
            "gain_db": gain, "lufs_gain_db": {g: gain for g in VB.BUILT}, "env": {"frames": 10},
            "unclaimed": {"groups": 4, "unclaimed": 1, "share": 0.25, "flags": [True, False, False, False]},
            "cover": {"frames": 10, "uncovered_share": 0.05}, "ends": {"release": 2, "repluck": 1, "mute": 0,
                                                                       "sample": 1, "cut": 0},
            "trace_report": {"notes": 4}}


def test_the_part_record_fields_are_declared():
    assert tuple(_rec("bks/a")) == VB.PART_FIELDS


def test_combine_counts_the_proofs_and_holds_only_on_all_47():
    keys = [f"bks/u{j:02d}" for j in range(V.PARTS)]
    per = {k: _rec(k, gain=j / 100) for j, k in enumerate(keys)}
    b = VB.combine_body(per, keys)
    assert b["proofs_hold"] is True and b["parts_n"] == 47 and b["renders"] == 0
    assert b["proofs"] == {p: {"held": 47, "of": 47} for p in VB.PROOFS}
    assert b["scratch_readerr_blob_sha"] == "a" * 40 and b["played_trace_sha256"] == "b" * 64
    assert b["ends"]["sample"] == 47 and b["ends"]["release"] == 94 and b["gain_db_range"] == [0.0, 0.46]
    assert set(b["parts"][keys[0]]) >= {"guitars", "gain_db", "unclaimed", "cover", "ends"}
    for g in V.RENDERED:                                  # what scratch_voice read and Unit C read
        assert b["parts"][keys[0]]["guitars"][g]["audio_sha256"]
    assert b["rules"]["windows"] == V.WINDOWS and b["rules"]["notch"] == V.NOTCH and b["rules"]["env"] == V.ENV
    assert json.dumps(b) == json.dumps(VB.combine_body(dict(reversed(per.items())), keys))   # no time, no order
    per[keys[3]] = _rec(keys[3], ok=False)
    b = VB.combine_body(per, keys)
    assert b["proofs_hold"] is False and b["proofs"]["vc_fin_is_avg"] == {"held": 46, "of": 47}
    assert VB.combine_body({k: per[k] for k in keys[:2] if k != keys[3]}, keys[:2])["proofs_hold"] is False   # < 47
    with pytest.raises(SystemExit, match="not the draw's parts"):
        VB.combine_body({k: per[k] for k in keys[:5]}, keys)
    per[keys[0]] = _rec(keys[0], ident=dict(IDENT, played_trace_sha256="c" * 64))
    with pytest.raises(SystemExit, match="different scratch_readerr code"):
        VB.combine_body(per, keys)


def test_the_dry_body_holds_no_part_keys():
    keys = [f"bks/secret-file-name-{j:02d}.wav" for j in range(V.PARTS)]
    b = VB.combine_body({k: _rec(k) for k in keys}, keys)
    body = VB.dry_body(b, "d" * 64)
    text = json.dumps(body)
    assert "secret-file-name" not in text and body["sha256"] == "d" * 64 and body["proofs_hold"] is True
    assert body["proofs"]["rule_off_is_tr_di"] == "47 of 47" and body["ends"]["sample"] == 47


# --- the guards and the command (pure, behind fakes) ------------------------------------------------------------------

def test_build_refuses_off_main(monkeypatch):
    monkeypatch.setattr(V, "on_main", lambda: (None, "this checkout's ['learn/voice_build.py'] differ from main's"))
    for args in (_args(), _args(combine=True), _args(shard=(0, 3))):
        with pytest.raises(SystemExit, match="differ from main's"):
            VB.cmd_build(args)


def test_build_refuses_without_the_declaration(monkeypatch):
    main = {S.PHASE_DRAW: {}, S.phase_answers(V.STEM_ROW): {}, SE.PHASE_TARGETS: {}}
    monkeypatch.setattr(V, "on_main", lambda: (main, None))
    with pytest.raises(SystemExit, match="has no phase_scratch_voice:"):
        VB.cmd_build(_args(combine=True))


def test_build_refuses_when_bench_parts_code_is_not_mains(monkeypatch):
    monkeypatch.setattr(V, "require_voice", lambda *a: {})

    def fake(*a):
        return type("R", (), {"returncode": 1 if a[-1] == "learn/rederive_fit.py" else 0})()
    monkeypatch.setattr(V, "_git", fake)
    assert "rederive_fit.py" in VB.code_refusal()
    with pytest.raises(SystemExit, match="rederive_fit.py"):
        VB.cmd_build(_args(combine=True))
    monkeypatch.setattr(V, "_git", lambda *a: type("R", (), {"returncode": 0})())
    assert VB.code_refusal() is None and VB.require_build() == {}


def test_the_cli_knows_only_build_and_bounds_the_shard():
    assert sorted(VB.COMMANDS) == ["build"]
    for argv in (["read"], ["build", "--shard", "0/9"], ["build", "--shard", "3/3"]):
        with pytest.raises(SystemExit):
            VB.main(argv)


def _fake_tree(monkeypatch, tmp_path, keys):
    monkeypatch.setattr(S, "fs_dir", lambda: tmp_path / "fs")
    monkeypatch.setattr(VB, "require_build", lambda: {})
    monkeypatch.setattr(VB, "_draw_parts", lambda: {k: {"pkey": k, "held": "B"} for k in keys})
    for k in keys:
        r = _rec(k)
        for g in VB.BUILT:
            p = V.dry_path(g, k)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(f"{g}|{k}".encode())
            r["guitars"][g]["file_sha256"] = S.file_sha(p)
        VB._save_once(VB.part_path(k), r)


def test_combine_is_write_once_and_refuses_missing_or_changed_parts(monkeypatch, tmp_path, capsys):
    keys = ["bks/a", "goat/b"]
    _fake_tree(monkeypatch, tmp_path, keys)
    with pytest.raises(SystemExit, match="never overwritten"):
        VB._save_once(VB.part_path("bks/a"), _rec("bks/a"))           # a part record is written once
    monkeypatch.setattr(VB, "_build_parts", lambda *a: pytest.fail("a shard rebuilt a part that is there"))
    VB.cmd_build(_args(shard=(0, 2)))                                    # every part there: nothing to build
    VB.cmd_build(_args(combine=True))
    out = capsys.readouterr().out
    assert "build.json sha256" in out and "bks/a" not in out and "goat/b" not in out
    first = V.build_path().read_bytes()
    assert json.loads(first)["parts_n"] == 2 and json.loads(first)["proofs_hold"] is False   # 2 parts, not 47
    with pytest.raises(SystemExit, match="never overwritten"):
        VB.cmd_build(_args(combine=True))
    assert V.build_path().read_bytes() == first
    V.build_path().unlink()
    V.dry_path("vc-own", "goat/b").write_bytes(b"other samples")
    with pytest.raises(SystemExit, match="changed since its record"):
        VB.cmd_build(_args(combine=True))
    VB.part_path("goat/b").unlink()
    with pytest.raises(SystemExit, match="1 of 2 parts have no record"):
        VB.cmd_build(_args(combine=True))
    with pytest.raises(SystemExit, match="separate steps"):
        VB.cmd_build(_args(combine=True, shard=(0, 2)))


def test_combine_refuses_a_malformed_part_record(monkeypatch, tmp_path):
    keys = ["bks/a"]
    _fake_tree(monkeypatch, tmp_path, keys)
    r = json.loads(VB.part_path("bks/a").read_text())
    r.pop("cover")
    VB.part_path("bks/a").write_text(json.dumps(r))
    with pytest.raises(SystemExit, match="malformed"):
        VB.cmd_build(_args(combine=True))


# --- the gate on synthetic signals (numpy) ----------------------------------------------------------------------------

class _Bank:
    """A stand-in bank: each sample a unit envelope with `prepare_sample`'s 2-ms fade-in, its length by its place."""

    def ok(self, s, f):
        return True

    def own_cents(self, s, f):
        return 0.0

    def note(self, s, f, cents):
        import numpy as np

        y = np.ones(int(SR * (0.3 + 0.1 * ((s + f) % 4))))
        k = int(NR.NOTE_FADE_IN_S * SR)
        y[:k] *= np.linspace(0.0, 1.0, k)
        return y


def _trace(notes, length, mutes=(), ring="ring-soft"):
    from learn import scratch_readerr as RX

    return RX.played_trace(notes, length, _Bank(), 0.0, ring, list(mutes), SR)


def test_the_gate_is_synthesise_redos_envelope_on_separate_notes():
    """Separate notes on the stand-in bank: synthesise_redo's audio is each note's envelope, so vc-own's gate (the same
    starts, fades, ends and edge fade) must equal it sample for sample. Release, mute and sample ends all occur."""
    np = pytest.importorskip("numpy")
    rng = random.Random(20261126)
    length = int(9.0 * SR)
    seen = set()
    for trial in range(6):
        notes, t = [], 0.003
        while t < 8.0:
            notes.append({"on": round(t, 4), "off": round(t + rng.uniform(0.02, 0.7), 4), "pitch": rng.randint(45, 80),
                          "bends": []})
            t += 0.95 + rng.uniform(0.0, 0.3)
        mutes = sorted(n["on"] + rng.uniform(0.05, 0.4) for n in notes if rng.random() < 0.3)
        audio, rep = NR.synthesise_redo(notes, length, _Bank(), 0.0, "ring-soft", mutes, 0.0, None, SR)
        trace, trep = _trace(notes, length, mutes)
        assert trep == rep
        seen |= set(rep["ends"])
        g = VB.own_gain(notes, trace, length)
        assert np.max(np.abs(g - audio)) < 1e-12, trial
    assert {"release", "mute", "sample"} <= seen


def test_each_end_kinds_fade_and_the_start_fade():
    np = pytest.importorskip("numpy")
    length = 2 * SR
    for kind, fade in (("repluck", 480), ("mute", 1440), ("release", 7200), ("sample", 7200), ("cut", 480)):
        notes = [{"on": 0.5, "off": 0.6}]
        trace = [{"played": True, "end": 1.0, "end_kind": kind}]
        g = VB.window_gain(VB.own_windows(notes, trace), length)
        a, e = round(0.498 * SR), SR
        assert np.array_equal(g[a:a + 96], np.linspace(0.0, 1.0, 96)), kind
        assert np.array_equal(g[e - fade:e], np.linspace(1.0, 0.0, fade)), kind
        assert np.all(g[a + 96:e - fade] == 1.0) and np.all(g[:a] == 0.0) and np.all(g[e:] == 0.0), kind


def test_windows_combine_by_maximum_never_by_sum():
    np = pytest.importorskip("numpy")
    length = SR
    w1, w2 = (1000, 20000, 96, 7200), (5000, 30000, 96, 480)     # overlapping, the first's release under the second
    g = VB.window_gain([w1, w2], length)
    a, b = VB.window_gain([w1], length), VB.window_gain([w2], length)
    assert np.array_equal(g, np.maximum(a, b))
    assert g.max() == 1.0 and (a + b).max() == 2.0
    assert np.array_equal(VB.window_gain([w1, w1, w1], length), a)   # simultaneous notes: the same audio, once


def test_the_edge_fade_and_a_window_before_zero():
    np = pytest.importorskip("numpy")
    length = SR
    g = VB.window_gain([(-48, 30000, 96, 0)], length, VB.edge_samples(length))
    edge = np.linspace(0.0, 1.0, 480)
    assert np.array_equal(g[:48], np.linspace(0.0, 1.0, 96)[48:] * edge[:48])   # the window cut at 0, then the edge
    assert np.array_equal(g[48:480], edge[48:]) and np.all(g[480:30000] == 1.0) and np.all(g[30000:] == 0.0)
    assert np.array_equal(g[length - 480:], np.zeros(480))      # the end edge (here past the window)
    notes = [{"on": 0.0, "off": 0.1}, {"on": 0.3, "off": 0.4}]
    trace = [{"played": True, "end": 0.2, "end_kind": "release"}, {"played": False, "why": "zero length"}]
    g = VB.own_gain(notes, trace, length)
    assert np.all(g[int(0.25 * SR):] == 0.0)                     # the skipped note opens no window


def test_notches_sit_only_at_the_onsets():
    np = pytest.importorskip("numpy")
    length = 3 * SR
    onsets = [0.4, 0.45, 1.3, 2.9995]
    g = VB.cut_gain(onsets, length)
    inside = np.zeros(length, bool)
    for t in onsets:
        o = round(t * SR)
        inside[max(0, o - 480):min(length, o)] = True
        seg = g[o - 480:o]
        j = int(np.argmin(seg))
        assert abs(20 * math.log10(seg[j]) + 15.6) < 0.2           # NOTCH: about -15.6 dB ...
        assert abs((480 - j) / SR * 1000 - 1.67) < 0.1             # ... about 1.67 ms before the onset
    assert np.all(g[~inside] == 1.0) and np.all(g <= 1.0) and g.min() > 0.15
    assert np.array_equal(VB.cut_gain([], length), np.ones(length))


def test_the_envelope_gain_stays_within_20_db_and_floors_at_0():
    np = pytest.importorskip("numpy")
    rng = np.random.default_rng(7)
    n = 2 * SR
    tr = rng.standard_normal(n) * 0.1
    tr[int(1.5 * SR):int(1.7 * SR)] *= 1e-3                      # tr-di 60 dB down: under its own 40-dB floor
    di = rng.standard_normal(n) * 0.1
    di[:int(0.5 * SR)] *= 100.0                                  # 40 dB louder: clamped to +20
    di[int(0.6 * SR):int(1.0 * SR)] *= 0.01                      # 40 dB quieter: clamped to -20
    per, rep = VB.env_db(tr, di)
    assert len(per) == n and np.all(np.abs(per) <= 20.0 + 1e-12)
    assert per[int(0.2 * SR)] == 20.0 and per[int(0.8 * SR)] == -20.0
    assert np.all(per[int(1.55 * SR):int(1.65 * SR)] == 0.0)
    assert rep["clamped"] > 0 and rep["floored"] > 0 and rep["max_abs_db"] == 20.0
    per2, _ = VB.env_db(tr, tr)
    assert np.max(np.abs(per2)) < 1e-9                           # the same level: no gain


def _world():
    np = pytest.importorskip("numpy")
    pytest.importorskip("pyloudnorm")
    rng = np.random.default_rng(11)
    n = int(3.0 * SR)
    raw = (rng.standard_normal(n) * 0.05).astype(np.float32)
    notes = [{"on": 0.3, "off": 0.9, "pitch": 52, "bends": []}, {"on": 1.2, "off": 1.4, "pitch": 60, "bends": []},
             {"on": 1.21, "off": 2.0, "pitch": 64, "bends": []}, {"on": 2.2, "off": 2.6, "pitch": 57, "bends": []}]
    length = n + int(round(NR.END_PAD_S * SR))
    trace, _ = _trace(notes, length, [1.7])
    tr = rng.standard_normal(n) * 0.08
    di = np.asarray(raw, np.float64) * 1.3

    def finish(y):                                               # a stand-in finish: deterministic, level-changing
        return np.convolve(y, [0.6, 0.3, 0.1])[:len(y)] * 2.0
    return np.asarray(raw, np.float64), notes, trace, finish, n, length, tr, di


def test_the_all_pass_window_gives_vc_fin_byte_for_byte():
    np = pytest.importorskip("numpy")
    raw64, notes, trace, finish, n, length, tr, di = _world()
    b = VB.build_guitars(raw64, notes, trace, finish, n, length, tr, di)
    assert VB.same_bytes(b["all_pass"], b["guitars"]["vc-fin"])
    assert np.array_equal(VB.all_pass_gain(length), np.ones(length))
    assert not VB.same_bytes(b["guitars"]["vc-own"], b["guitars"]["vc-fin"])
    for g in VB.BUILT:
        y = b["guitars"][g]
        assert y.dtype == np.float32 and len(y) == n and np.isfinite(y).all()
        assert abs(NR.loudness(np.asarray(y, np.float64)) - NR.ASSUMED_LUFS) < 0.02
    assert VB.fin_ratio(b["guitars"]["vc-fin"], np.asarray(b["guitars"]["vc-fin"], np.float64) * 0.5) < 1e-6
    assert VB.fin_ratio(b["guitars"]["vc-fin"], raw64[:-1]) == math.inf     # another length


def test_two_runs_are_byte_identical():
    raw64, notes, trace, finish, n, length, tr, di = _world()
    a = VB.build_guitars(raw64, notes, trace, finish, n, length, tr, di)
    b = VB.build_guitars(raw64.copy(), [dict(x) for x in notes], [dict(x) for x in trace], finish, n, length,
                         tr.copy(), di.copy())
    for g in VB.BUILT:
        assert S.npy_sha(a["guitars"][g]) == S.npy_sha(b["guitars"][g]), g
    assert a["lufs_gain_db"] == b["lufs_gain_db"] and a["env"] == b["env"]


def test_a_dry_guitar_is_written_once(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    from learn import scratch_rederive as RD

    monkeypatch.setattr(S, "fs_dir", lambda: tmp_path / "fs")
    p = V.dry_path("vc-own", "bks/a")
    y = np.arange(10, dtype=np.float32)
    sha = RD._write_once(p, y)
    assert RD._write_once(p, y.copy()) == sha                    # a rerun after a stop: the same samples
    with pytest.raises(SystemExit, match="never overwritten"):
        RD._write_once(p, y + 1)


# --- one part behind fakes (numpy) ------------------------------------------------------------------------------------

def _fake_part(monkeypatch, tmp_path):
    """A part on the stand-in bank: `song_bank.measure` and the finish stood in by fixed linear maps, X and its sha256
    made by the same compose of T, so proofs 1-3 hold by construction; proof 4 holds when avg is the finish of the
    measured raw section."""
    np = pytest.importorskip("numpy")
    for m in ("scipy", "pyloudnorm", "noisereduce"):
        pytest.importorskip(m)
    from learn import rederive_fit as RF
    from learn import song_bank as SB

    monkeypatch.setattr(S, "fs_dir", lambda: tmp_path / "fs")
    monkeypatch.setattr(SB, "measure", lambda x: np.asarray(x, np.float64) * 0.5)
    raw64, notes, _, _, n, length, _, _ = _world()
    raw = np.asarray(raw64, np.float32)
    di = np.asarray(np.asarray(SB.measure(raw), np.float32), np.float64)

    def finish(y):
        return np.convolve(SB.measure(y), [0.7, 0.3])[:len(y)]
    mutes = [1.7]
    T = {"tuning": 0.0, "mutes": mutes, "tilt": 0.0, "levels": [0.0] * len(NR.onset_groups(notes))}
    p = RF.Part(notes, n, _Bank(), "ring-soft", None, finish, None, SR, "bks/fake-file.wav", "bks", di, None, T)
    x32 = RF.guitar(p, T)
    p.X, p.x_sha = np.asarray(x32, np.float64), S.npy_sha(x32)
    _, rep = NR.synthesise_redo(notes, length, _Bank(), 0.0, "ring-soft", mutes, 0.0, None, SR)
    am = tmp_path / "avg+mild.npy"
    np.save(am, raw)
    return p, {"held": "A"}, raw, finish(raw64), am, S.file_sha(am), rep, VB.code_identity()


def test_one_part_writes_its_guitars_and_record_once(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    p, dp, raw, avg, am, am_sha, rep, ident = _fake_part(monkeypatch, tmp_path)
    rec = VB.part_record(p, dp, raw, avg, am, am_sha, rep, ident)
    assert tuple(rec) == VB.PART_FIELDS and all(rec["proofs"][k] is True for k in VB.PROOFS)
    assert rec["fin_ratio"] <= VB.FIN_PROOF_TOL and rec["tag"] == V.tag(p.key) and rec["held"] == "A"
    for g in VB.BUILT:
        y = np.load(V.dry_path(g, p.key))
        assert rec["guitars"][g] == {"file_sha256": S.file_sha(V.dry_path(g, p.key)), "audio_sha256": S.npy_sha(y)}
    assert rec["guitars"]["avg+mild"]["file_sha256"] == am_sha
    assert rec["ends"] == VB.ends_of(rep) and sum(rec["ends"].values()) == rep["played"]
    assert rec["unclaimed"]["groups"] == len(NR.onset_groups(p.notes)) and rec["cover"]["frames"] >= 0
    assert json.loads(VB.part_path(p.key).read_text())["guitars"] == rec["guitars"]
    with pytest.raises(SystemExit, match="record exists"):
        VB.part_record(p, dp, raw, avg, am, am_sha, rep, ident)


@pytest.mark.parametrize("broken", ["avg", "report", "x", "raw", "avg+mild"])
def test_a_failing_proof_stops_the_part_before_anything_is_written(monkeypatch, tmp_path, broken):
    np = pytest.importorskip("numpy")
    p, dp, raw, avg, am, am_sha, rep, ident = _fake_part(monkeypatch, tmp_path)
    if broken == "avg":
        avg = avg * (1 + 1e-3 * np.sin(np.arange(len(avg))))       # off by about 1e-3: proof 4, never loosened
    elif broken == "report":
        rep = dict(rep, played=rep["played"] + 1)
    elif broken == "x":
        p.x_sha = "0" * 64
    elif broken == "raw":
        raw = raw * np.float32(1.001)
    else:
        am_sha = "0" * 64
    with pytest.raises(SystemExit) as e:
        VB.part_record(p, dp, raw, avg, am, am_sha, rep, ident)
    assert "fake-file" not in str(e.value) and V.tag(p.key) in str(e.value)   # tags only
    assert not VB.part_path(p.key).exists()
    assert not any(V.dry_path(g, p.key).exists() for g in VB.BUILT)
