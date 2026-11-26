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
            "code": dict(ident), "checks": {"raw_is_true_di": True, "synth_inside_gate": True},
            "proofs": {p: (ok or p != "vc_fin_is_avg") for p in VB.PROOFS}, "fin_ratio": 1e-7,
            "guitars": {g: {"file_sha256": hashlib.sha256(f"{g}{k}".encode()).hexdigest(),
                            "audio_sha256": hashlib.sha256(f"a{g}{k}".encode()).hexdigest()} for g in VB.GUITARS},
            "gain_db": gain, "lufs_gain_db": {g: gain for g in VB.BUILT}, "env": {"frames": 10},
            "pad": {"real": 4800, "zeros": 0, "first_n_equal": True},
            "length_term": {"held": "B", "held_rms_ratio": 1.0, "held_rms_db": gain / 10, "logmel_held": 0.01,
                            "logmel_whole": 0.02, "reference": "pad-off vc-fin"},
            "support": {"inside": True, "nonzero": 100, "nonzero_outside_spans": 0, "nonzero_outside_gate": 1},
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
    assert set(b["parts"][keys[0]]) >= {"guitars", "gain_db", "unclaimed", "cover", "ends", "pad", "length_term"}
    assert tuple(b["parts"][keys[0]]) == VB.BUILD_PART_FIELDS
    assert b["checks"] == {c: {"held": 47, "of": 47} for c in VB.CHECKS} and "synth_inside_gate" in VB.CHECKS
    assert b["length_term"]["held_rms_db_range"] == [0.0, 0.046] and b["support"]["nonzero_outside_gate"] == 47
    assert b["pad"] == {"zero_padded_parts": 0, "first_n_unequal_parts": 0}
    assert "padded_chain" in b["rules"]["choices"] and "chain" in b["rules"]["fin"]
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
    per = {k: _rec(k) for k in keys}
    per[keys[1]]["checks"]["synth_inside_gate"] = False
    assert VB.combine_body(per, keys)["proofs_hold"] is False                 # a failed check holds nothing


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
    onsets = [0.4, 0.45, 1.3, 2.95]
    g = VB.cut_gain(onsets, length)
    inside = np.zeros(length, bool)
    inside[:480] = inside[length - 480:] = True                 # the edge fade (review B1: as vc-own's and vc-fin's)
    for t in onsets:
        o = round(t * SR)
        inside[max(0, o - 480):min(length, o)] = True
        seg = g[o - 480:o]
        j = int(np.argmin(seg))
        assert abs(20 * math.log10(seg[j]) + 15.6) < 0.2           # NOTCH: about -15.6 dB ...
        assert abs((480 - j) / SR * 1000 - 1.67) < 0.1             # ... about 1.67 ms before the onset
    assert np.all(g[~inside] == 1.0) and np.all(g <= 1.0) and g[480:length - 480].min() > 0.15
    assert np.array_equal(VB.cut_gain([], length), VB.edge_gain(length))
    assert np.array_equal(g[:480], np.linspace(0.0, 1.0, 480)) and g[-1] == 0.0


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
    length = n + VB.pad_samples()
    raw_l = np.asarray((rng.standard_normal(length) * 0.05).astype(np.float32), np.float64)   # with a continuation
    notes = [{"on": 0.3, "off": 0.9, "pitch": 52, "bends": []}, {"on": 1.2, "off": 1.4, "pitch": 60, "bends": []},
             {"on": 1.21, "off": 2.0, "pitch": 64, "bends": []}, {"on": 2.2, "off": 2.6, "pitch": 57, "bends": []}]
    trace, _ = _trace(notes, length, [1.7])
    tr = rng.standard_normal(n) * 0.08
    di = raw_l[:n] * 1.3

    def finish(y):                                               # a stand-in finish: circular, level-changing
        k = np.fft.rfft(y)
        return np.fft.irfft(k * np.linspace(1.0, 0.3, len(k)), len(y)) * 2.0
    return raw_l, notes, trace, finish, n, tr, di


def test_the_all_pass_window_gives_vc_fin_byte_for_byte():
    np = pytest.importorskip("numpy")
    raw_l, notes, trace, finish, n, tr, di = _world()
    length = len(raw_l)
    b = VB.build_guitars(raw_l, notes, trace, finish, n, tr, di)
    assert VB.same_bytes(b["all_pass"], b["guitars"]["vc-fin"])
    assert np.array_equal(VB.all_pass_gain(length), VB.edge_gain(length))
    assert np.array_equal(b["gates"]["vc-fin"], VB.edge_gain(length))
    assert not VB.same_bytes(b["guitars"]["vc-own"], b["guitars"]["vc-fin"])
    off, _ = VB.pad_off(raw_l[:n], finish, n)
    assert VB.same_bytes(b["fin_pad_off"], off) and not VB.same_bytes(off, b["guitars"]["vc-fin"])   # the pad shows
    for g in VB.BUILT:
        y = b["guitars"][g]
        assert y.dtype == np.float32 and len(y) == n and np.isfinite(y).all()
        assert abs(NR.loudness(np.asarray(y, np.float64)) - NR.ASSUMED_LUFS) < 0.02
    assert VB.fin_ratio(b["fin_pad_off"], np.asarray(b["fin_pad_off"], np.float64) * 0.5) < 1e-6
    assert VB.fin_ratio(b["fin_pad_off"], raw_l[:n - 1]) == math.inf     # another length
    with pytest.raises(ValueError):
        VB.through_gate(raw_l, np.ones(n), finish, n)
    with pytest.raises(ValueError):
        VB.pad_off(raw_l, finish, n)


def test_the_length_term_is_zero_for_the_same_guitar_and_sees_the_pad():
    np = pytest.importorskip("numpy")
    raw_l, notes, trace, finish, n, tr, di = _world()
    b = VB.build_guitars(raw_l, notes, trace, finish, n, tr, di)
    same = VB.length_term(b["fin_pad_off"], b["fin_pad_off"], "A")      # A: 1.25 s on, inside the 3-s world
    assert same["held_rms_ratio"] == 1.0 and same["held_rms_db"] == 0.0 and same["logmel_held"] == 0.0
    lt = VB.length_term(b["guitars"]["vc-fin"], b["fin_pad_off"], "A")
    assert lt["held"] == "A" and lt["logmel_held"] > 0 and lt["reference"] == "pad-off vc-fin"
    none = VB.length_term(b["guitars"]["vc-fin"], b["fin_pad_off"], "B")   # B lies past this world's end
    assert none["held_rms_ratio"] is None and none["logmel_held"] is None and none["logmel_whole"] > 0


def test_two_runs_are_byte_identical():
    raw_l, notes, trace, finish, n, tr, di = _world()
    a = VB.build_guitars(raw_l, notes, trace, finish, n, tr, di)
    b = VB.build_guitars(raw_l.copy(), [dict(x) for x in notes], [dict(x) for x in trace], finish, n, tr.copy(),
                         di.copy())
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
    raw_l, notes, _, _, n, _, _ = _world()
    length = len(raw_l)
    di = np.asarray(np.asarray(SB.measure(np.asarray(raw_l[:n], np.float32)), np.float32), np.float64)

    def finish(y):
        k = np.fft.rfft(SB.measure(y))
        return np.fft.irfft(k * np.linspace(1.0, 0.4, len(k)), len(y))
    mutes = [1.7]
    T = {"tuning": 0.0, "mutes": mutes, "tilt": 0.0, "levels": [0.0] * len(NR.onset_groups(notes))}
    p = RF.Part(notes, n, _Bank(), "ring-soft", None, finish, None, SR, "bks/fake-file.wav", "bks", di, None, T)
    x32 = RF.guitar(p, T)
    p.X, p.x_sha = np.asarray(x32, np.float64), S.npy_sha(x32)
    _, rep = NR.synthesise_redo(notes, length, _Bank(), 0.0, "ring-soft", mutes, 0.0, None, SR)
    am = tmp_path / "avg+mild.npy"
    np.save(am, np.asarray(raw_l[:n], np.float32))
    pad = {"real": VB.pad_samples(), "zeros": 0, "first_n_equal": True}
    return p, {"held": "A"}, raw_l, pad, finish(raw_l[:n]), am, S.file_sha(am), rep, VB.code_identity()


def test_one_part_writes_its_guitars_and_record_once(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    p, dp, raw_l, pad, avg, am, am_sha, rep, ident = _fake_part(monkeypatch, tmp_path)
    rec = VB.part_record(p, dp, raw_l, pad, avg, am, am_sha, rep, ident)
    assert tuple(rec) == VB.PART_FIELDS and all(rec["proofs"][k] is True for k in VB.PROOFS)
    assert rec["checks"] == {c: True for c in VB.CHECKS} and rec["pad"] == pad
    assert rec["support"]["inside"] and rec["support"]["nonzero"] > 0 and rec["length_term"]["logmel_held"] > 0
    assert rec["fin_ratio"] <= VB.FIN_PROOF_TOL and rec["tag"] == V.tag(p.key) and rec["held"] == "A"
    for g in VB.BUILT:
        y = np.load(V.dry_path(g, p.key))
        assert rec["guitars"][g] == {"file_sha256": S.file_sha(V.dry_path(g, p.key)), "audio_sha256": S.npy_sha(y)}
    assert rec["guitars"]["avg+mild"]["file_sha256"] == am_sha
    assert rec["ends"] == VB.ends_of(rep) and sum(rec["ends"].values()) == rep["played"]
    assert rec["unclaimed"]["groups"] == len(NR.onset_groups(p.notes)) and rec["cover"]["frames"] >= 0
    assert json.loads(VB.part_path(p.key).read_text())["guitars"] == rec["guitars"]
    with pytest.raises(SystemExit, match="record exists"):
        VB.part_record(p, dp, raw_l, pad, avg, am, am_sha, rep, ident)


@pytest.mark.parametrize("broken", ["avg", "report", "x", "raw", "avg+mild", "length", "synth"])
def test_a_failing_proof_stops_the_part_before_anything_is_written(monkeypatch, tmp_path, broken):
    np = pytest.importorskip("numpy")
    p, dp, raw_l, pad, avg, am, am_sha, rep, ident = _fake_part(monkeypatch, tmp_path)
    if broken == "avg":
        avg = avg * (1 + 1e-3 * np.sin(np.arange(len(avg))))       # off by about 1e-3: proof 4, never loosened
    elif broken == "report":
        rep = dict(rep, played=rep["played"] + 1)
    elif broken == "x":
        p.x_sha = "0" * 64
    elif broken == "raw":
        raw_l = raw_l * 1.001
    elif broken == "length":
        raw_l = raw_l[:p.n]                                       # the pad missing
    elif broken == "synth":
        from learn import scratch_rederive as RD

        real, calls = RD._synth, []

        def synth(*a, **k):                                      # proof 1's compose first, then the support check's
            calls.append(1)
            y, r = real(*a, **k)
            return (y + 1e-9 if len(calls) > 1 else y), r        # the second: sound outside the windows
        monkeypatch.setattr(RD, "_synth", synth)
    else:
        am_sha = "0" * 64
    with pytest.raises(SystemExit) as e:
        VB.part_record(p, dp, raw_l, pad, avg, am, am_sha, rep, ident)
    assert "fake-file" not in str(e.value) and V.tag(p.key) in str(e.value)   # tags only
    if broken == "synth":
        assert "outside the trace's windows" in str(e.value)
    assert not VB.part_path(p.key).exists()
    assert not any(V.dry_path(g, p.key).exists() for g in VB.BUILT)


# --- the review's added tests (numpy) ---------------------------------------------------------------------------------

def test_proof_4_holds_through_the_real_float32_rounding_and_average_balance():
    """Proof 4's path on synthetic signals with the real `average_balance`: the stored avg is average_balance of the
    float32-rounded measured DI (note_replay's blur); the pad-off builder runs the finish on the unrounded raw."""
    np = pytest.importorskip("numpy")
    for m in ("scipy", "pyloudnorm"):
        pytest.importorskip(m)
    from learn import di_robustness as DR

    rng = np.random.default_rng(3)
    n = int(4.0 * SR)
    t = np.arange(n) / SR
    raw = np.asarray((0.2 * np.sin(2 * np.pi * 196 * t) * np.exp(-((t % 1.0) * 3))
                      + 0.01 * rng.standard_normal(n)).astype(np.float32), np.float64)

    def measure(x):                                              # a stand-in measure: a fixed EQ and level
        return np.convolve(np.asarray(x, np.float64), [0.5, 0.3, -0.1])[:len(x)] * 3.0
    others = {"s": [np.asarray(rng.standard_normal(n) * 0.1, np.float64),
                    np.asarray(np.sin(2 * np.pi * 330 * t) * 0.1, np.float64)]}

    def finish(y):
        return DR.average_balance(measure(y), others)
    di32 = np.asarray(measure(raw), np.float32)
    avg = DR.average_balance(np.asarray(di32, np.float64), others)     # as note_replay's blur stored it
    off, _ = VB.pad_off(raw, finish, n)
    ratio = VB.fin_ratio(np.asarray(off, np.float32), avg)
    assert 0 < ratio <= VB.FIN_PROOF_TOL


class _LongBank(_Bank):
    """The stand-in bank with long samples, so a note rings until its string is plucked again."""

    def note(self, s, f, cents):
        import numpy as np

        y = np.ones(int(SR * 3.0))
        k = int(NR.NOTE_FADE_IN_S * SR)
        y[:k] *= np.linspace(0.0, 1.0, k)
        return y


def test_vc_owns_repluck_notch_is_vc_cuts_within_one_sample():
    np = pytest.importorskip("numpy")
    length = 3 * SR
    notes = [{"on": 0.5, "off": 2.0, "pitch": 83, "bends": []},   # only string 1 plays 83 and 84: a re-pluck at 1.0
             {"on": 1.0, "off": 1.6, "pitch": 84, "bends": []}]
    from learn import scratch_readerr as RX

    trace, rep = RX.played_trace(notes, length, _LongBank(), 0.0, "ring-soft", [], SR)
    assert trace[0]["end_kind"] == "repluck" and trace[0]["string"] == trace[1]["string"] == 1
    own = VB.own_gain(notes, trace, length)
    cut = VB.cut_gain(VB.group_onsets(notes), length)
    o = round(1.0 * SR)
    lo, hi = o - 600, o + 200
    jo, jc = int(np.argmin(own[lo:hi])), int(np.argmin(cut[lo:hi]))
    assert abs(jo - jc) <= 1 and abs(own[lo + jo] - cut[lo + jc]) < 1e-3
    for shift in (-1, 0, 1):
        if np.max(np.abs(own[lo:hi] - np.roll(cut, shift)[lo:hi])) < 1e-2:
            break
    else:
        pytest.fail("vc-own's re-pluck notch is not vc-cut's within one sample")


def test_the_gate_is_the_maximum_of_synthesise_redos_note_envelopes_with_replucks_and_chords():
    """Each note's own envelope is `synthesise_redo` with that note's weight 1 and the rest 0 (the placing and ends
    never depend on the gains); the gate must be their maximum exactly, and its support the full synthesis's."""
    np = pytest.importorskip("numpy")
    from learn import scratch_readerr as RX

    rng = random.Random(7)
    length = int(6.0 * SR)
    kinds = set()
    for trial in range(4):
        notes = []
        for _ in range(rng.randint(8, 14)):
            on = round(rng.uniform(0.05, 5.0), 3)
            notes.append({"on": on, "off": on + rng.uniform(0.05, 1.5), "pitch": rng.randint(45, 84), "bends": []})
        for _ in range(3):                                       # a chord
            notes.append({"on": 2.5, "off": 3.2, "pitch": rng.randint(45, 70), "bends": []})
        notes.append({"on": 4.0, "off": 5.0, "pitch": 83, "bends": []})   # a re-pluck on string 1
        notes.append({"on": 4.3, "off": 5.0, "pitch": 84, "bends": []})
        mutes = [3.6]
        trace, rep = RX.played_trace(notes, length, _LongBank(), 0.0, "ring-soft", mutes, SR)
        kinds |= set(rep["ends"])
        full, _ = NR.synthesise_redo(notes, length, _LongBank(), 0.0, "ring-soft", mutes, 0.0, None, SR)
        envs = []
        for k, t in enumerate(trace):
            if t["played"]:
                w = [1.0 if j == k else 0.0 for j in range(len(notes))]
                y, _ = NR.synthesise_redo(notes, length, _LongBank(), 0.0, "ring-soft", mutes, 0.0, None, SR,
                                          note_weights=w)
                envs.append(y)
        g = VB.own_gain(notes, trace, length)
        assert np.max(np.abs(g - np.max(envs, axis=0))) < 1e-12, trial   # the shape
        assert np.array_equal(full != 0, g > 0), trial                   # the support
        sc = VB.support_check(full, VB.own_windows(notes, trace), g)
        assert sc["inside"] and sc["nonzero_outside_gate"] == 0
    assert {"repluck", "mute"} <= kinds


def test_the_support_check_counts_sound_outside_the_windows():
    np = pytest.importorskip("numpy")
    gate = VB.window_gain([(100, 200, 10, 10)], 400)
    y = np.zeros(400)
    y[100:200] = 1.0
    assert VB.support_check(y, [(100, 200, 10, 10)], gate) == {"inside": True, "nonzero": 100,
                                                               "nonzero_outside_spans": 0, "nonzero_outside_gate": 2}
    y[250] = 1e-9
    assert VB.support_check(y, [(100, 200, 10, 10)], gate)["nonzero_outside_spans"] == 1
    with pytest.raises(ValueError):
        VB.support_check(y[:10], [], gate)


def test_the_envelope_gain_is_linear_between_frame_centres_and_held_at_the_ends():
    np = pytest.importorskip("numpy")
    rng = np.random.default_rng(5)
    n = SR
    tr = rng.standard_normal(n) * 0.1
    di = tr * np.repeat(10 ** (rng.uniform(-10, 10, n // 960 + 1) / 20), 960)[:n]
    per, _ = VB.env_db(tr, di)
    frame, hop = 960, 240
    lt, ld = NR.frame_levels_db(tr, frame, hop), NR.frame_levels_db(di, frame, hop)
    g = np.clip(ld - lt, -20, 20)
    centres = np.arange(len(g)) * hop + frame // 2                # frame / 2 is a whole sample here
    assert np.allclose(per[centres], g)
    mid = centres[:-1] + hop // 2
    assert np.allclose(per[mid], (g[:-1] + g[1:]) / 2)
    assert np.all(per[:centres[0]] == g[0]) and np.all(per[centres[-1]:] == g[-1])


def test_the_padded_chain_is_composes():
    """`compose`'s tail is `chain`: with the hiss removal stood in by the identity, the synthesis (its edge fade in
    it) through `chain` is `compose`'s guitar byte for byte; and vc-own's gate carries that same edge fade."""
    np = pytest.importorskip("numpy")
    pytest.importorskip("pyloudnorm")
    from learn import scratch_rederive as RD

    raw_l, notes, _, finish, n, _, _ = _world()
    T = {"tuning": 0.0, "mutes": [1.7], "tilt": 0.0, "levels": [0.0] * len(NR.onset_groups(notes))}
    real = NR.denoise_above
    try:
        NR.denoise_above = lambda x, rate=SR: x
        y, _ = RD.compose(notes, n, _Bank(), "ring-soft", finish, T, None, SR)
    finally:
        NR.denoise_above = real
    synth, _ = RD._synth(notes, n, _Bank(), "ring-soft", 0.0, [1.7], 0.0, T["levels"], None, SR, last=True)
    assert len(synth) == n + VB.pad_samples() == len(raw_l)
    mine, _ = VB.chain(synth, finish, n)
    assert VB.same_bytes(mine, y)
    e = VB.edge_samples(len(raw_l))
    for gate in (VB.edge_gain(len(raw_l)), VB.cut_gain([1.0], len(raw_l))):
        assert np.array_equal(gate[:e], np.linspace(0.0, 1.0, e)) and np.array_equal(gate[-e:], np.linspace(1, 0, e))


def test_the_padded_raw_section_is_the_section_and_its_real_continuation(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    pytest.importorskip("scipy")
    from learn import pretrain_set as PS

    rng = np.random.default_rng(9)
    long_f, short_f, slow_f = tmp_path / "long.wav", tmp_path / "short.wav", tmp_path / "slow.wav"
    sf.write(long_f, (rng.standard_normal(13 * SR) * 0.1).astype(np.float32), SR, subtype="FLOAT")
    sf.write(short_f, (rng.standard_normal(int(11.05 * SR)) * 0.1).astype(np.float32), SR, subtype="FLOAT")
    sf.write(slow_f, (rng.standard_normal(13 * 44100) * 0.1).astype(np.float32), 44100, subtype="FLOAT")
    pad = VB.pad_samples()
    for f, start, real in ((long_f, 1.0, pad), (short_f, 1.0, int(round(0.05 * SR))), (long_f, 0.1, pad)):
        x, rep = VB.padded_raw(f, start)
        sec = PS.section_audio(f, start)
        n = len(sec)
        assert len(x) == n + pad and x.dtype == np.float64 and np.array_equal(x[:n], np.asarray(sec, np.float64))
        assert rep == {"real": real, "zeros": pad - real, "first_n_equal": True}, (f.name, start)
        whole = sf.read(f, dtype="float32")[0]
        a = int(round((start - PS.TRIM_S) * SR))
        want = np.zeros(pad, np.float32)
        cont = whole[max(0, a) + n - max(0, -a):][:real] if a >= 0 else whole[n + a:][:real]
        want[:len(cont)] = cont
        assert np.array_equal(np.asarray(x[n:], np.float32), want), (f.name, start)
    x, rep = VB.padded_raw(slow_f, 1.0)                           # resampled: the continuation from the longer read
    assert rep["real"] == pad and rep["zeros"] == 0 and len(x) == PS.section_audio(slow_f, 1.0).size + pad
