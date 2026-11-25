"""The note-reading diagnosis's transcriber runner (`learn/readerr_run.py`, plan `note-reading-diagnosis` unit U2):
the arguments and every refusal, the event record, the grid's enumeration, the shift and lead-in re-basing on
synthetic events, the pinned model's sha256 and missing-file refusals, the thread cap and the standard-library module
level. Pure: runs on the light CI runner (no numpy, no torch); torch tests are skipped without it, and the Basic Pitch
check runs only where the Basic Pitch venv is installed. Fixtures use synthetic names only."""
import ast
import hashlib
import json
import math
import os
import pathlib
import struct
import subprocess
import sys
import wave

import pytest

from learn import bp_run as BP
from learn import readerr_run as R

REPO = pathlib.Path(__file__).resolve().parents[1]
SHA = "0" * 64
FROZEN = {"onset_threshold": 0.5, "frame_threshold": 0.3, "minimum_note_length": 58.0, "minimum_frequency": 60.0,
          "maximum_frequency": 1400.0, "melodia_trick": True, "multiple_pitch_bends": True}
PLAN_GRID = {"onset_threshold": [0.3, 0.4, 0.5, 0.6, 0.7, 0.8], "frame_threshold": [0.2, 0.3, 0.4, 0.5],
             "minimum_note_length": [58.0, 90.0, 127.7], "melodia_trick": [True, False]}


def _spec(mode, **kw):
    base = {"model": "m.bin", "model_sha256": SHA}
    if mode in R.BP_MODES:
        base["settings"] = dict(FROZEN)
    if mode == "bp-grid":
        base["grid"] = {"onset_threshold": [0.4, 0.5]}
    if mode == "bp-shift":
        base["offsets_s"] = [0.0, 0.25]
    base.update(kw)
    return base


def _args(mode, spec, *files):
    return [mode, "--spec", json.dumps(spec), *(files or ("in.wav", "out.json"))]


def _ev(on, off, pitch=60, amp=0.5, bends=(0, 1)):
    return (on, off, pitch, amp, list(bends))


def _tone_wav(path, seconds=2.0, sr=22050, freq=220.0, start=0.5, stop=1.5):
    """A synthetic sine tone (16-bit mono), standard library only."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        frames = bytearray()
        for i in range(int(seconds * sr)):
            t = i / sr
            v = 0.5 * math.sin(2 * math.pi * freq * t) if start <= t < stop else 0.0
            frames += struct.pack("<h", int(v * 32767))
        w.writeframes(bytes(frames))


# --- the arguments ---------------------------------------------------------------------------------------------------------

def test_parse_each_mode():
    for mode in R.MODES:
        spec = _spec(mode)
        got_mode, got_spec, pairs = R.parse_args(_args(mode, spec, "a.wav", "a.json", "b.wav", "b.json"))
        assert got_mode == mode and got_spec == spec and pairs == [("a.wav", "a.json"), ("b.wav", "b.json")]
        assert R.threads_of(got_spec) == 1
    assert R.threads_of(R.parse_args(_args("mt3", _spec("mt3", threads=2)))[1]) == 2
    assert R.parse_args(_args("kong", _spec("kong", options={"k": 1}, lead_in_s=1.0)))[1]["lead_in_s"] == 1.0


@pytest.mark.parametrize("argv", [
    [], ["bp-run"], ["bp-grid", "in.wav", "out.json"], ["bp-grid", "--spec"], ["bp-grid", "--spec", "{bad", "a", "b"],
    ["bp-grid", "--spec", "[1]", "a", "b"],
])
def test_parse_refuses_the_call(argv):
    with pytest.raises(SystemExit):
        R.parse_args(argv)


def test_parse_refuses_the_pairs():
    for files in (("a.wav",), ("a.wav", "a.json", "b.wav"), ("a.wav", "a.wav")):
        with pytest.raises(SystemExit):
            R.parse_args(["mt3", "--spec", json.dumps(_spec("mt3")), *files])
    with pytest.raises(SystemExit):
        R.parse_args(["mt3", "--spec", json.dumps(_spec("mt3"))])


@pytest.mark.parametrize("mode,change", [
    ("mt3", {"extra": 1}), ("mt3", {"settings": FROZEN}), ("kong", {"grid": {}}), ("bp-shift", {"grid": {}}),
    ("bp-grid", {"offsets_s": [0.0]}), ("bp-grid", {"options": {}}), ("mt3", {"options": []}),
    ("mt3", {"model": ""}), ("mt3", {"model": 3}), ("mt3", {"model_sha256": "ABC"}), ("mt3", {"model_sha256": "A" * 64}),
    ("mt3", {"threads": 0}), ("mt3", {"threads": 3}), ("mt3", {"threads": True}), ("mt3", {"threads": "1"}),
    ("mt3", {"threads": 1.0}), ("mt3", {"lead_in_s": -0.1}), ("mt3", {"lead_in_s": "1"}),
    ("mt3", {"lead_in_s": float("inf")}),
    ("bp-grid", {"settings": {"onset_threshold": 0.5}}), ("bp-grid", {"settings": dict(FROZEN, extra=1)}),
    ("bp-grid", {"grid": {}}), ("bp-grid", {"grid": {"minimum_frequency": [60.0]}}),
    ("bp-grid", {"grid": {"onset_threshold": []}}), ("bp-grid", {"grid": {"onset_threshold": 0.5}}),
    ("bp-grid", {"grid": {"onset_threshold": [0.5, 0.5]}}), ("bp-grid", {"grid": {"melodia_trick": [1, 0]}}),
    ("bp-grid", {"grid": {"frame_threshold": [True]}}), ("bp-grid", {"grid": {"minimum_note_length": [-1.0]}}),
    ("bp-shift", {"offsets_s": []}), ("bp-shift", {"offsets_s": [-0.1]}), ("bp-shift", {"offsets_s": [0.0, 0.0]}),
    ("bp-shift", {"offsets_s": 0.25}), ("bp-shift", {"offsets_s": [True]}),
])
def test_parse_refuses_the_spec(mode, change):
    with pytest.raises(SystemExit):
        R.parse_args(_args(mode, _spec(mode, **change)))


@pytest.mark.parametrize("mode", R.MODES)
def test_parse_refuses_a_missing_required_key(mode):
    for k in R.REQUIRED[mode]:
        spec = _spec(mode)
        del spec[k]
        with pytest.raises(SystemExit):
            R.parse_args(_args(mode, spec))


def test_the_declared_constants():
    assert R.MODES == ("bp-grid", "bp-shift", "mt3", "kong")
    assert R.SETTING_KEYS == BP.SETTING_KEYS and R.PROVIDERS == BP.PROVIDERS
    assert R.GRID_KEYS == ("onset_threshold", "frame_threshold", "minimum_note_length", "melodia_trick")
    assert (R.DEFAULT_THREADS, R.MAX_THREADS) == (1, 2)
    assert set(R.REQUIRED) == set(R.MODES) == set(R.MODE_KEYS)
    for mode in R.MODES:
        assert set(R.REQUIRED[mode]) <= set(R.COMMON_KEYS) | set(R.MODE_KEYS[mode])


# --- the event record ----------------------------------------------------------------------------------------------------

def test_event_record_matches_bp_run():
    for ev in [(0.123456, 0.5, 60, 0.3333333, [0, 1, 2]), (0.1, 0.2, 61.0, 0.5, None), (1.00005, 2.0, 40, 1, [])]:
        assert R.event_record(ev) == BP.event_record(ev)
    assert R.event_record((0.123456, 0.5, 60, 0.3333333, [0, 1, 2])) == {"on": 0.1235, "off": 0.5, "pitch": 60,
                                                                         "amp": 0.333333, "bends": [0, 1, 2]}
    assert R.event_record((0.1, 0.2, 61, 0.5, None))["bends"] == []


# --- the grid --------------------------------------------------------------------------------------------------------------

def test_grid_enumeration_the_plans_144():
    pts = R.grid_points(FROZEN, PLAN_GRID)
    assert len(pts) == 6 * 4 * 3 * 2 == 144
    assert all(sorted(p) == sorted(R.SETTING_KEYS) for p in pts)
    assert len({tuple(sorted(p.items())) for p in pts}) == 144
    assert pts[0] == dict(FROZEN, onset_threshold=0.3, frame_threshold=0.2, minimum_note_length=58.0)
    assert pts[1] == dict(pts[0], melodia_trick=False)                 # the last axis innermost
    assert pts[-1] == dict(FROZEN, onset_threshold=0.8, frame_threshold=0.5, minimum_note_length=127.7,
                           melodia_trick=False)
    assert all((p["minimum_frequency"], p["maximum_frequency"], p["multiple_pitch_bends"]) == (60.0, 1400.0, True)
               for p in pts)
    assert FROZEN in pts                                                # the stored point is on the grid


def test_grid_enumeration_axes_left_out():
    pts = R.grid_points(FROZEN, {"frame_threshold": [0.2, 0.4]})
    assert pts == [dict(FROZEN, frame_threshold=0.2), dict(FROZEN, frame_threshold=0.4)]
    assert R.grid_points(FROZEN, {"melodia_trick": [True]}) == [FROZEN]
    base = dict(FROZEN)
    R.grid_points(base, PLAN_GRID)
    assert base == FROZEN                                               # the base is never changed


def test_grid_output_reads_every_point_from_one_source():
    seen = []

    def notes_at(s):
        seen.append(s)
        return [_ev(s["onset_threshold"], s["onset_threshold"] + 1.0, pitch=50 if s["melodia_trick"] else 51)]

    base, rows = R.grid_output(FROZEN, {"onset_threshold": [0.3, 0.6], "melodia_trick": [True, False]}, notes_at)
    assert base == [R.event_record(_ev(0.5, 1.5, pitch=50))]
    assert [r["settings"] for r in rows] == R.grid_points(FROZEN, {"onset_threshold": [0.3, 0.6],
                                                                    "melodia_trick": [True, False]})
    assert [(r["events"][0]["on"], r["events"][0]["pitch"]) for r in rows] == [(0.3, 50), (0.3, 51), (0.6, 50),
                                                                               (0.6, 51)]
    assert len(seen) == 5 and seen[0] == FROZEN


# --- the re-basing ---------------------------------------------------------------------------------------------------------

def test_rebase_drop_and_clip():
    evs = [_ev(0.1, 0.4), _ev(0.2, 0.5), _ev(0.45, 0.8, bends=(2, 3)), _ev(1.0, 2.0, pitch=64, amp=0.25)]
    got = R.rebase(evs, 0.5)
    assert [(round(a, 9), round(b, 9)) for a, b, *_ in got] == [(0.0, 0.3), (0.5, 1.5)]   # two end at or before 0
    assert got[0][4] == [2, 3] and got[1][2:4] == (64, 0.25)          # the bend track kept as read
    assert R.rebase(evs, 0.0) == [(float(a), float(b), p, m, bd) for a, b, p, m, bd in evs]
    assert R.rebase([], 1.0) == []
    assert R.rebase([_ev(0.0, 0.5)], 0.5) == []                       # ends exactly at 0: dropped
    assert R.rebase([_ev(0.5, 0.5001)], 0.5)[0][0] == 0.0


def test_pad_samples():
    assert R.pad_samples(0, 22050) == 0 and R.pad_samples(1.0, 22050) == 22050
    assert R.pad_samples(0.25, 22050) == 5512                         # round half to even: 5512.5 -> 5512
    assert abs(R.pad_samples(0.1, 22050) / 22050 - 0.1) <= 0.5 / 22050


def _true_events():
    return [_ev(0.0, 0.3, 50), _ev(0.5, 1.0, 55), _ev(1.25, 2.0, 60, bends=(1,))]


def _reader(sr, ghost=False):
    """A fake transcriber: reads the true events shifted by the pad (plus, if asked, a ghost in the zeros)."""
    calls = []

    def read_padded(n):
        calls.append(n)
        s = n / sr
        out = [(a + s, b + s, p, m, bd) for a, b, p, m, bd in _true_events()]
        if ghost and n:
            out = [(0.0, s * 0.5, 40, 0.1, None), (s * 0.5, s + 0.2, 41, 0.1, None)] + out
        return out

    return read_padded, calls


def test_shift_rebases_each_read_to_the_input():
    sr = 22050
    read, calls = _reader(sr, ghost=True)
    top, shifts = R.shift_output([0.0, 0.25, 0.5, 1.0], 0.0, sr, read)
    assert calls == [0, 5512, 11025, 22050]
    want = [R.event_record(e) for e in _true_events()]
    assert top == want == shifts[0]["events"]
    assert [s["offset_s"] for s in shifts] == [0.0, 0.25, 0.5, 1.0]
    assert [s["pad_samples"] for s in shifts] == calls
    for s in shifts[1:]:
        ev = s["events"]
        assert ev[0]["pitch"] == 41 and ev[0]["on"] == 0.0 and ev[0]["off"] == 0.2   # straddling 0: onset clipped
        assert all(e["pitch"] != 40 for e in ev)                                       # inside the zeros: dropped
        assert ev[1:] == want


def test_shift_without_zero_has_no_top_level_events():
    read, _ = _reader(22050)
    top, shifts = R.shift_output([0.5, 1.0], 0.0, 22050, read)
    assert top == [] and len(shifts) == 2
    assert all(s["events"] == [R.event_record(e) for e in _true_events()] for s in shifts)


def test_lead_in_rebases_with_the_shift():
    sr = 22050
    read, calls = _reader(sr, ghost=True)
    top, shifts = R.shift_output([0.0, 0.5], 1.0, sr, read)
    assert calls == [22050, 33075]                                    # lead-in and offset padded together
    assert [s["offset_s"] for s in shifts] == [0.0, 0.5]              # each shift named by its offset alone
    want = [R.event_record(e) for e in _true_events()]
    assert top == shifts[0]["events"] and top[1:] == want and shifts[1]["events"][1:] == want


def test_lead_in_on_the_grid():
    sr = 22050
    n = R.pad_samples(1.0, sr)
    raw = [(a + n / sr, b + n / sr, p, m, bd) for a, b, p, m, bd in _true_events()] + [(0.2, 0.9, 30, 0.1, None)]
    base, rows = R.grid_output(FROZEN, {"melodia_trick": [True, False]}, lambda s: R.rebase(raw, n / sr))
    want = [R.event_record(e) for e in _true_events()]
    assert base == want and all(r["events"] == want for r in rows)


# --- the model file and the torch stubs ------------------------------------------------------------------------------------

def test_checked_model_refuses_missing_and_another_hash(tmp_path):
    with pytest.raises(SystemExit, match="no model file"):
        R.checked_model(str(tmp_path / "absent.ckpt"), SHA)
    with pytest.raises(SystemExit, match="no model file"):
        R.checked_model(str(tmp_path), SHA)                          # a folder is not a model file
    f = tmp_path / "synthetic.ckpt"
    f.write_bytes(b"synthetic weights")
    sha = hashlib.sha256(b"synthetic weights").hexdigest()
    assert R.checked_model(str(f), sha) == sha == R.file_sha(str(f))
    with pytest.raises(SystemExit, match="sha256"):
        R.checked_model(str(f), SHA)


@pytest.mark.parametrize("mode", R.MODES)
def test_main_refuses_a_missing_checkpoint_before_any_import(tmp_path, mode):
    src, dst = tmp_path / "synthetic.wav", tmp_path / "synthetic.json"
    _tone_wav(src, seconds=0.1)
    heavy = {"torch", "numpy", "basic_pitch", "onnxruntime", "soundfile"}
    before = heavy & set(sys.modules)
    spec = _spec(mode, model=str(tmp_path / "absent.pth"))
    with pytest.raises(SystemExit, match="no model file"):
        R.main(_args(mode, spec, str(src), str(dst)))
    assert heavy & set(sys.modules) == before and not dst.exists()


@pytest.mark.parametrize("mode", R.MODES)
def test_main_refuses_another_hash_before_any_import(tmp_path, mode):
    src, dst, ckpt = tmp_path / "synthetic.wav", tmp_path / "synthetic.json", tmp_path / "synthetic.pth"
    _tone_wav(src, seconds=0.1)
    ckpt.write_bytes(b"not the pinned file")
    heavy = {"torch", "numpy", "basic_pitch", "onnxruntime", "soundfile"}
    before = heavy & set(sys.modules)
    with pytest.raises(SystemExit, match="sha256"):
        R.main(_args(mode, _spec(mode, model=str(ckpt)), str(src), str(dst)))
    assert heavy & set(sys.modules) == before and not dst.exists()


def test_main_refuses_a_missing_input(tmp_path):
    ckpt = tmp_path / "synthetic.pth"
    ckpt.write_bytes(b"w")
    spec = _spec("mt3", model=str(ckpt), model_sha256=hashlib.sha256(b"w").hexdigest())
    with pytest.raises(SystemExit, match="no input"):
        R.main(_args("mt3", spec, str(tmp_path / "absent.wav"), str(tmp_path / "o.json")))


def test_thread_cap_and_offline(monkeypatch):
    for k in R.THREAD_ENV + tuple(R.OFFLINE_ENV):
        monkeypatch.delenv(k, raising=False)
    R.cap_threads(2)
    assert all(os.environ[k] == "2" for k in R.THREAD_ENV)
    assert all(os.environ[k] == "1" for k in R.OFFLINE_ENV)


def test_torch_checkpoint_loads_weights_only_then_the_stub_refuses(tmp_path, monkeypatch):
    torch = pytest.importorskip("torch")
    for k in R.THREAD_ENV + tuple(R.OFFLINE_ENV):
        monkeypatch.delenv(k, raising=False)                          # restored after the test
    ckpt = tmp_path / "synthetic.pth"
    torch.save({"w": torch.zeros(3)}, str(ckpt))
    state, versions = R.load_checkpoint(str(ckpt), 1)
    assert list(state) == ["w"] and versions["torch"] == torch.__version__
    src = tmp_path / "synthetic.wav"
    _tone_wav(src, seconds=0.1)
    for mode in R.TORCH_MODES:
        spec = _spec(mode, model=str(ckpt), model_sha256=R.file_sha(str(ckpt)))
        with pytest.raises(SystemExit, match="not wired"):
            R.main(_args(mode, spec, str(src), str(tmp_path / f"{mode}.json")))


class _NotATensor:
    pass


def test_torch_checkpoint_with_an_object_refuses(tmp_path):
    torch = pytest.importorskip("torch")
    ckpt = tmp_path / "synthetic.pth"
    torch.save({"w": _NotATensor()}, str(ckpt))
    with pytest.raises(SystemExit, match="weights_only"):
        R.load_checkpoint(str(ckpt), 1)


# --- the module level ------------------------------------------------------------------------------------------------------

def _top_imports(src):
    out = set()
    for node in ast.parse(src, feature_version=(3, 9)).body:          # it runs on the venv's Python 3.9
        if isinstance(node, ast.Import):
            out |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            out.add((node.module or "").split(".")[0])
    return out


def test_module_level_is_the_standard_library():
    src = (REPO / "learn" / "readerr_run.py").read_text()
    assert _top_imports(src) <= {"hashlib", "itertools", "json", "math", "os", "sys", "time"}
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module and not node.module.startswith(("learn", ".")), node.module   # -I: nothing from here
        if isinstance(node, ast.Import):
            assert not any(a.name.startswith("learn") for a in node.names)
    assert "weights_only=True" in src and "torch.load(" in src
    assert src.count("torch.load(") == 1


def test_no_runtime_fetch():
    src = (REPO / "learn" / "readerr_run.py").read_text()
    for word in ("urllib", "requests", "hf_hub_download", "snapshot_download", "from_pretrained", "http://",
                 "https://", "load_state_dict_from_url", "torch.hub"):
        assert word not in src, word


# --- Basic Pitch, where its venv is installed ----------------------------------------------------------------------------

def _bp_install():
    from learn import note_transcribe as T

    if not T.BP_PYTHON.exists() or not T.MANIFEST.exists():
        pytest.skip("no Basic Pitch venv here")
    return T.BP_PYTHON, json.loads(T.MANIFEST.read_text()), T.BP_SETTINGS


def test_bp_modes_match_bp_run_on_a_synthetic_tone(tmp_path):
    py, man, settings = _bp_install()
    src = tmp_path / "synthetic.wav"
    _tone_wav(src)
    ref = tmp_path / "ref.json"
    r = subprocess.run([str(py), "-I", str(REPO / "learn" / "bp_run.py"), "--model", man["model_path"],
                        "--settings", json.dumps(settings), str(src), str(ref)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-400:]
    want = json.loads(ref.read_text())["events"]
    assert want, "the tone should read as at least one note"
    common = {"model": man["model_path"], "model_sha256": man["model_sha256"]}
    specs = {"grid": dict(common, settings=settings, grid={"onset_threshold": [0.5, 0.7], "melodia_trick": [True]}),
             "shift": dict(common, settings=settings, offsets_s=[0.0, 0.5]),
             "lead": dict(common, settings=settings, offsets_s=[0.0], lead_in_s=1.0)}
    outs = {}
    for name, spec in specs.items():
        mode = "bp-grid" if "grid" in spec else "bp-shift"
        o = tmp_path / f"{name}.json"
        r = subprocess.run([str(py), "-I", str(REPO / "learn" / "readerr_run.py"), mode, "--spec", json.dumps(spec),
                            str(src), str(o)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-400:]
        outs[name] = json.loads(o.read_text())
    g = outs["grid"]
    assert g["events"] == want and g["grid"][0]["events"] == want and g["grid"][0]["settings"] == settings
    assert [p["settings"]["onset_threshold"] for p in g["grid"]] == [0.5, 0.7]
    assert g["model_sha256"] == man["model_sha256"] and g["threads"] == 1 and g["spec"] == specs["grid"]
    assert g["input_sha256"] == R.file_sha(str(src)) and g["seconds"] >= 0
    assert g["versions"]["providers"] == ["CPUExecutionProvider"]
    s = outs["shift"]
    assert s["events"] == want == s["shifts"][0]["events"]
    assert [x["offset_s"] for x in s["shifts"]] == [0.0, 0.5] and s["shifts"][1]["pad_samples"] == 11025
    for out in (s["shifts"][1]["events"], outs["lead"]["events"]):  # re-based: the tone's note near where it was
        main = max(out, key=lambda e: e["off"] - e["on"])
        ref_main = max(want, key=lambda e: e["off"] - e["on"])
        assert main["pitch"] == ref_main["pitch"] and abs(main["on"] - ref_main["on"]) < 0.05
