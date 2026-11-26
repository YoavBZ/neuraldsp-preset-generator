"""The note-reading diagnosis's transcriber runner (`learn/readerr_run.py`, plan `note-reading-diagnosis` unit U2 and
the Phase 2b amendment's unit D): the arguments and every refusal, the event record, the grid's enumeration, the
shift and lead-in re-basing on synthetic events, the pinned model's sha256 and missing-file refusals, the thread cap,
the torch modes' declared options and grids, the pickle scan on hand-built pickles, the network and process refusals,
the guarded load, the key report, the torch path end to end on fakes, and the standard-library module level. Pure:
runs on the light CI runner (no numpy, no torch); torch tests are skipped without it, and the Basic Pitch check and the
torch smoke run only where their venvs are installed. Fixtures use synthetic names only."""
import ast
import collections
import contextlib
import hashlib
import io
import json
import math
import os
import pathlib
import pickle
import struct
import subprocess
import sys
import types
import wave
import zipfile

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
    if mode == "mt3":
        base.update(options={"programs": "pitched"}, allow_globals=list(ALLOW))
    if mode == "kong":
        base.update(options=dict(R.KONG_SHIPPED), allow_globals=list(ALLOW))
    base.update(kw)
    return base


ALLOW = ("collections.OrderedDict", "torch._utils._rebuild_tensor_v2")
KONG_PLAN_GRID = {"onset_threshold": [0.2, 0.3, 0.4, 0.5], "frame_threshold": [0.1, 0.2, 0.3]}


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
    assert R.parse_args(_args("kong", _spec("kong", lead_in_s=1.0)))[1]["lead_in_s"] == 1.0
    assert R.parse_args(_args("kong", _spec("kong", grid=KONG_PLAN_GRID)))[1]["grid"] == KONG_PLAN_GRID
    assert R.parse_args(_args("mt3", _spec("mt3", grid={"programs": ["pitched", "guitar"]})))[1]["grid"] == \
        {"programs": ["pitched", "guitar"]}
    for o in ({"onset_threshold": 0.5, "frame_threshold": 0.3}, {"onset_threshold": 0.2, "frame_threshold": 0.1}):
        assert R.parse_args(_args("kong", _spec("kong", options=o)))[1]["options"] == o
    assert R.parse_args(_args("mt3", _spec("mt3", options={"programs": "guitar"})))[1]["options"]["programs"] == \
        "guitar"


@pytest.mark.parametrize("argv", [
    [], ["bp-run"], ["bp-grid", "in.wav", "out.json"], ["bp-grid", "--spec"], ["bp-grid", "--spec", "{bad", "a", "b"],
    ["bp-grid", "--spec", "[1]", "a", "b"],
])
def test_parse_refuses_the_call(argv):
    with pytest.raises(SystemExit):
        R.parse_args(argv)


def test_parse_refuses_a_repeated_spec():
    s = json.dumps(_spec("mt3"))
    for argv in (["mt3", "--spec", s, "--spec", s, "a.wav", "a.json"],
                 ["mt3", "--spec", "null", "--spec", s, "a.wav", "a.json"],
                 ["mt3", "--spec", s, "a.wav", "a.json", "--spec", s]):
        with pytest.raises(SystemExit, match="once"):
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
    ("bp-grid", {"allow_globals": list(ALLOW)}), ("bp-shift", {"options": {}}),
    # the torch modes' options, grids and allowlist (Phase 2b amendment; review amendments 5 and 7)
    ("mt3", {"options": {}}), ("mt3", {"options": {"programs": "drums"}}), ("mt3", {"options": {"programs": 1}}),
    ("mt3", {"options": {"programs": "pitched", "onset_threshold": 0.3}}),
    ("mt3", {"options": dict(R.KONG_SHIPPED)}), ("kong", {"options": {"programs": "pitched"}}),
    ("kong", {"options": {"onset_threshold": 0.3}}), ("kong", {"options": {"onset_threshold": 0.35,
                                                                           "frame_threshold": 0.1}}),
    ("kong", {"options": {"onset_threshold": 0.3, "frame_threshold": 0.4}}),
    ("kong", {"options": {"onset_threshold": True, "frame_threshold": 0.1}}),
    ("kong", {"options": {"onset_threshold": "0.3", "frame_threshold": 0.1}}),
    ("mt3", {"grid": {}}), ("mt3", {"grid": {"programs": []}}), ("mt3", {"grid": {"programs": "pitched"}}),
    ("mt3", {"grid": {"programs": ["pitched", "pitched"]}}), ("mt3", {"grid": {"programs": ["drums"]}}),
    ("mt3", {"grid": {"onset_threshold": [0.3]}}), ("kong", {"grid": {"programs": ["pitched"]}}),
    ("kong", {"grid": {"onset_threshold": [0.6]}}), ("kong", {"grid": {"frame_threshold": [0.05, 0.1]}}),
    ("kong", {"grid": {"onset_threshold": [0.3, 0.3]}}), ("kong", {"grid": {"minimum_note_length": [58.0]}}),
    ("kong", {"grid": [0.3]}),
    ("mt3", {"allow_globals": []}), ("mt3", {"allow_globals": "collections.OrderedDict"}),
    ("mt3", {"allow_globals": ["OrderedDict"]}), ("mt3", {"allow_globals": [".x"]}), ("mt3", {"allow_globals": [3]}),
    ("mt3", {"allow_globals": ["collections.OrderedDict", "collections.OrderedDict"]}),
    ("kong", {"allow_globals": ["builtins.eval"]}), ("kong", {"allow_globals": ["os.system"]}),
    ("kong", {"allow_globals": ["collections.OrderedDict", "subprocess.Popen"]}),
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
    for mode in R.TORCH_MODES:                                        # the contract fixed for units D and E
        assert set(R.MODE_KEYS[mode]) == {"options", "grid", "allow_globals"}
        assert set(R.REQUIRED[mode]) == {"model", "model_sha256", "options", "allow_globals"}


def test_the_torch_modes_declared_values():
    assert R.KONG_GRID == {"onset_threshold": (0.2, 0.3, 0.4, 0.5), "frame_threshold": (0.1, 0.2, 0.3)}
    assert len(R.torch_points("kong", R.KONG_SHIPPED, {k: list(v) for k, v in R.KONG_GRID.items()})) == 4 * 3 == 12
    assert R.KONG_SHIPPED == {"onset_threshold": 0.3, "frame_threshold": 0.1}
    assert all(R.KONG_SHIPPED[k] in R.KONG_GRID[k] for k in R.KONG_SHIPPED)          # the shipped point is on the grid
    assert R.KONG_FIXED == {"offset_threshold": 0.3, "pedal_offset_threshold": 0.2}
    assert (R.KONG_MODEL_TYPE, R.KONG_BATCH, R.KONG_SEGMENT_S) == ("Regress_onset_offset_frame_velocity_CRNN", 8, 10)
    assert R.MT3_PROGRAMS == ("pitched", "guitar") and R.MT3_SHIPPED == {"programs": "pitched"}
    assert R.GUITAR_PROGRAMS == tuple(range(24, 32)) and R.MT3_MODEL_KEY == "yptf_moe_nops"
    assert R.TORCH_AXES == {"mt3": {"programs": R.MT3_PROGRAMS}, "kong": R.KONG_GRID}
    assert set(R.ADAPTERS) == set(R.TORCH_MODES) == set(R.TORCH_ALIASES)


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
    real, before = os.environ, dict(os.environ)
    with monkeypatch.context() as m:
        m.setattr(os, "environ", dict(os.environ))                     # a copy: the worker's environment untouched
        for k in R.THREAD_ENV + tuple(R.OFFLINE_ENV):
            os.environ.pop(k, None)
        R.cap_threads(2)
        assert all(os.environ[k] == "2" for k in R.THREAD_ENV)
        assert all(os.environ[k] == "1" for k in R.OFFLINE_ENV)
    assert os.environ is real and dict(os.environ) == before          # restored


# --- the torch modes' grid and note lists (pure) ----------------------------------------------------------------------------

def test_torch_points_the_kong_grid():
    pts = R.torch_points("kong", R.KONG_SHIPPED, KONG_PLAN_GRID)
    assert len(pts) == 12 and len({tuple(sorted(p.items())) for p in pts}) == 12
    assert pts[0] == {"onset_threshold": 0.2, "frame_threshold": 0.1}
    assert pts[1] == {"onset_threshold": 0.2, "frame_threshold": 0.2}                 # the last axis innermost
    assert pts[-1] == {"onset_threshold": 0.5, "frame_threshold": 0.3}
    assert R.KONG_SHIPPED in pts
    assert R.torch_points("kong", R.KONG_SHIPPED, {"frame_threshold": [0.2, 0.3]}) == \
        [{"onset_threshold": 0.3, "frame_threshold": 0.2}, {"onset_threshold": 0.3, "frame_threshold": 0.3}]
    assert R.torch_points("mt3", {"programs": "guitar"}, {"programs": ["pitched", "guitar"]}) == \
        [{"programs": "pitched"}, {"programs": "guitar"}]


def test_torch_output_from_one_source():
    seen = []

    def notes_at(o):
        seen.append(dict(o))
        return [_ev(o["onset_threshold"], o["onset_threshold"] + o["frame_threshold"], amp=0.25, bends=())]

    base, rows = R.torch_output("kong", R.KONG_SHIPPED, KONG_PLAN_GRID, notes_at)
    assert base == [R.event_record(_ev(0.3, 0.4, amp=0.25, bends=()))]
    assert [r["options"] for r in rows] == R.torch_points("kong", R.KONG_SHIPPED, KONG_PLAN_GRID)
    assert all(set(r) == {"options", "events"} for r in rows)
    assert rows[0]["events"] == [R.event_record(_ev(0.2, 0.30000000000000004, amp=0.25, bends=()))]
    assert len(seen) == 13 and seen[0] == R.KONG_SHIPPED
    base2, rows2 = R.torch_output("kong", R.KONG_SHIPPED, None, notes_at)
    assert base2 == base and rows2 is None                                            # no grid: no grid rows


def test_mt3_select_programs():
    notes = [(False, 25, 0.1, 0.5, 60, 1), (False, 0, 0.2, 0.6, 62, 1), (True, 0, 0.3, 0.31, 36, 1),
             (False, 31, 0.4, 0.9, 64, 1), (False, 32, 0.5, 0.7, 40, 1), (False, 24, 0.6, 0.8, 50, 1)]
    assert R.mt3_select(notes, "pitched") == [(0.1, 0.5, 60, 1.0, None), (0.2, 0.6, 62, 1.0, None),
                                              (0.4, 0.9, 64, 1.0, None), (0.5, 0.7, 40, 1.0, None),
                                              (0.6, 0.8, 50, 1.0, None)]
    assert R.mt3_select(notes, "guitar") == [(0.1, 0.5, 60, 1.0, None), (0.4, 0.9, 64, 1.0, None),
                                             (0.6, 0.8, 50, 1.0, None)]
    assert [R.event_record(e) for e in R.mt3_select(notes, "guitar")][0] == {"on": 0.1, "off": 0.5, "pitch": 60,
                                                                             "amp": 1.0, "bends": []}
    with pytest.raises(SystemExit):
        R.mt3_select(notes, "drums")


def test_module_versions_from_the_modules_not_metadata():
    got = R.module_versions(("pytest", "json", "json.decoder", "synthetic_never_imported_module"))
    assert got["pytest"] == pytest.__version__ and got["json"] == json.__version__
    assert got["json.decoder.sha256"] == R.file_sha(sys.modules["json.decoder"].__file__)
    assert got["synthetic_never_imported_module"] is None
    src = (REPO / "learn" / "readerr_run.py").read_text()
    assert "importlib.metadata" not in src and "from importlib import metadata" not in src
    assert R.KONG_FORK_COMMIT == "cfe28ed26be892ad7d4e8a9aadcf95cb904c9320"


def _stereo_wav(path, sr, seconds=1.0):
    """A synthetic stereo 16-bit wav: left a 220 Hz sine, right silence (standard library only)."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<hh", int(16000 * math.sin(2 * math.pi * 220 * i / sr)), 0)
                               for i in range(int(seconds * sr))))


class _FakeTranscriptor:
    """The fork's PianoTranscription stand-in: records what `transcribe` was given, answers the four maps."""

    def __init__(self):
        self.calls = []

    def transcribe(self, audio, midi_path):
        self.calls.append((audio, midi_path))
        return {"output_dict": dict({k: [[0.0]] for k in R.KONG_RAW_KEYS}, onset_output=[[1.0]])}


def test_kong_read_path_under_the_process_guard(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    pytest.importorskip("soundfile")
    src = tmp_path / "synthetic.wav"
    _stereo_wav(src, 16000)
    ad = object.__new__(R.KongAdapter)                                 # the real read path, a fake model
    ad.sr, ad.tr = 16000, _FakeTranscriptor()
    with monkeypatch.context() as m:
        R.install_refusals(m.setattr)
        with pytest.raises(SystemExit, match="refused"):
            subprocess.run(["true"])                                   # the guard is live
        raw = ad.read(str(src))
    assert sorted(raw) == sorted(R.KONG_RAW_KEYS)                      # the derived maps are dropped
    audio, midi_path = ad.tr.calls[0]
    assert midi_path is None and audio.dtype == np.float32 and audio.shape == (16000,)
    assert abs(float(np.max(np.abs(audio))) - 0.5 * 16000 / 32768) < 1e-3                  # the channel mean


def test_load_mono_resamples_like_librosa_load_under_the_guard(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    pytest.importorskip("soundfile")
    librosa = pytest.importorskip("librosa")
    src = tmp_path / "synthetic.wav"
    _stereo_wav(src, 22050)
    with monkeypatch.context() as m:
        R.install_refusals(m.setattr)
        y, sr = R.load_mono(str(src), 16000)
        ad = object.__new__(R.KongAdapter)
        ad.sr, ad.tr = 16000, _FakeTranscriptor()
        ad.read(str(src))
    assert sr == 16000 and y.dtype == np.float32 and abs(len(y) - 16000) <= 1
    assert np.array_equal(ad.tr.calls[0][0], y)
    want, _ = librosa.load(str(src), sr=16000)                         # outside the guard: soundfile's path
    assert np.allclose(y, want, atol=1e-6)


def test_load_mono_native_rate(tmp_path):
    np = pytest.importorskip("numpy")
    pytest.importorskip("soundfile")
    src = tmp_path / "synthetic.wav"
    _stereo_wav(src, 22050, seconds=0.5)
    y, sr = R.load_mono(str(src))
    assert sr == 22050 and y.shape == (11025,) and y.dtype == np.float32
    assert R.load_mono(str(src), 22050)[1] == 22050


def test_no_librosa_load_anywhere():
    tree = ast.parse((REPO / "learn" / "readerr_run.py").read_text())
    calls = [ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)]
    assert not [c for c in calls if c.endswith(".load") and "librosa" in c]
    assert "librosa.resample" in calls and "sf.read" in calls


def test_kong_events():
    notes = [{"onset_time": 0.1, "offset_time": 0.5, "midi_note": 64, "velocity": 127},
             {"onset_time": 0.2, "offset_time": 0.3, "midi_note": 40, "velocity": 0}]
    assert R.kong_events(notes) == [(0.1, 0.5, 64, 1.0, None), (0.2, 0.3, 40, 0.0, None)]
    assert R.event_record(R.kong_events([dict(notes[0], velocity=64)])[0])["amp"] == round(64 / 127, 6)


# --- the pickle scan on hand-built pickles ----------------------------------------------------------------------------------

def _u(s):
    """SHORT_BINUNICODE s."""
    b = s.encode()
    return b"\x8c" + bytes([len(b)]) + b


def test_scan_global_and_stack_global():
    assert R.scan_pickle(pickle.dumps(collections.OrderedDict(), protocol=2)) == ["collections.OrderedDict"]
    assert R.scan_pickle(pickle.dumps(collections.OrderedDict(), protocol=4)) == ["collections.OrderedDict"]  # FRAME
    assert R.scan_pickle(pickle.dumps(os.system, protocol=4)) == [f"{os.system.__module__}.system"]
    assert R.scan_pickle(pickle.dumps(eval, protocol=2)) == ["__builtin__.eval"]
    assert R.scan_pickle(pickle.dumps({"a": [1, 2.0, "x", b"y", None, True]}, protocol=4)) == []
    assert R.scan_pickle(b"(ios\nsystem\n.") == ["os.system"]                         # INST, protocol 0


def test_scan_stack_global_through_the_memo():
    memoize = b"\x80\x04" + _u("collections") + b"\x94" + _u("OrderedDict") + b"\x94" + b"00" + \
        b"h\x00h\x01\x93)R."                                    # POP POP, then BINGET 0, BINGET 1, STACK_GLOBAL
    assert R.scan_pickle(memoize) == ["collections.OrderedDict"]
    binput = b"\x80\x04" + _u("os") + b"q\x05" + _u("system") + b"q\x07" + b"00" + b"h\x05h\x07\x93."
    assert R.scan_pickle(binput) == ["os.system"]                               # BINPUT at explicit slots
    long_get = b"\x80\x04" + _u("os") + b"r\x00\x01\x00\x00" + b"0" + b"j\x00\x01\x00\x00" + _u("popen") + b"\x93."
    assert R.scan_pickle(long_get) == ["os.popen"]                              # LONG_BINPUT, LONG_BINGET
    put_get = b"\x80\x04" + _u("os") + b"p3\n0g3\n" + _u("execv") + b"\x93."
    assert R.scan_pickle(put_get) == ["os.execv"]                               # PUT, GET (text forms)


@pytest.mark.parametrize("data", [
    b"\x80\x04" + _u("os") + _u("system") + b")0\x93.",                         # a POP between: not known
    b"\x80\x04" + _u("os") + b")\x93.",                                         # one string only
    b"\x80\x04\x93.",                                                          # nothing on the stack
    b"\x80\x04" + _u("os") + b"h\x09\x93.",                                     # a memo slot never filled
    b"\x80\x04)\x94" + _u("system") + b"h\x00\x93.",                            # a memo slot holding a tuple
    b"\x80\x04" + _u("os") + b"C\x06system\x93.",                               # bytes, not a string
    b"\x80\x04" + _u("os") + _u("system") + b"\x93\x93.",                       # a second STACK_GLOBAL on a global
])
def test_scan_refuses_an_unresolved_stack_global(data):
    with pytest.raises(SystemExit, match="STACK_GLOBAL"):
        R.scan_pickle(data)


@pytest.mark.parametrize("data,why", [
    (b"\x80\x02\x82\x01.", "extension-registry"), (b"\x80\x02\x83\x01\x00.", "extension-registry"),
    (pickle.dumps(collections.OrderedDict(), protocol=2) + b"junk", "after"),
    (b"\x80\x02c", "parse"), (b"\x80\x02K\x01", "parse"), (b"\xff", "parse"),
])
def test_scan_refuses_what_it_cannot_read(data, why):
    with pytest.raises(SystemExit, match=why):
        R.scan_pickle(data)


def _zip_ckpt(path, members):
    with zipfile.ZipFile(str(path), "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    return str(path)


def test_scan_checkpoint_reads_every_pkl_member(tmp_path):
    p = _zip_ckpt(tmp_path / "synthetic.pth", {
        "archive/data.pkl": pickle.dumps(collections.OrderedDict(), protocol=2),
        "archive/data/0": b"\x00" * 16,
        "archive/extra.pkl": pickle.dumps(os.system, protocol=4),
        "archive/version": b"3\n"})
    scan = R.scan_checkpoint(p)
    assert scan == {"archive/data.pkl": ["collections.OrderedDict"],
                    "archive/extra.pkl": [f"{os.system.__module__}.system"]}
    with open(p, "rb") as f:
        assert R.scan_checkpoint(f) == scan and not f.closed                  # a handle stays open for the load
    with pytest.raises(SystemExit, match="denylisted"):
        R.check_globals(scan, ["collections.OrderedDict", f"{os.system.__module__}.system"])
    legacy = tmp_path / "legacy.pth"
    legacy.write_bytes(pickle.dumps(collections.OrderedDict(), protocol=2))
    with pytest.raises(SystemExit, match="not a zip"):
        R.scan_checkpoint(str(legacy))
    with pytest.raises(SystemExit, match="no .pkl"):
        R.scan_checkpoint(_zip_ckpt(tmp_path / "empty.pth", {"archive/data/0": b"\x00"}))
    dup = tmp_path / "dup.pth"
    with zipfile.ZipFile(str(dup), "w") as z:
        z.writestr("archive/data.pkl", pickle.dumps(collections.OrderedDict(), protocol=2))
        with pytest.warns(UserWarning):
            z.writestr("archive/data.pkl", pickle.dumps(eval, protocol=2))      # a duplicate name: both scanned
    assert R.scan_checkpoint(str(dup)) == {"archive/data.pkl": ["collections.OrderedDict", "__builtin__.eval"]}


def test_check_globals_and_the_denylist():
    scan = {"a/data.pkl": ["collections.OrderedDict", "torch._utils._rebuild_tensor_v2"], "a/b.pkl": []}
    assert R.check_globals(scan, ALLOW) == ["collections.OrderedDict", "torch._utils._rebuild_tensor_v2"]
    with pytest.raises(SystemExit, match="outside the allowlist"):
        R.check_globals(scan, ["collections.OrderedDict"])
    for name in ("builtins.eval", "builtins.exec", "builtins.compile", "builtins.getattr", "builtins.__import__",
                 "builtins.open", "__builtin__.eval", "os.system", "posix.system", "subprocess.Popen", "sys.modules",
                 "importlib.import_module", "runpy.run_path", "socket.socket", "shutil.rmtree", "pickle.loads",
                 "marshal.loads", "os.path.join", "nt.system", "_posixsubprocess.fork_exec", "torch.os.system"):
        assert R.denied_global(name), name
        with pytest.raises(SystemExit, match="denylisted"):
            R.check_globals({"m.pkl": [name]}, [name])                        # the denylist wins over the allowlist
    for name in ("collections.OrderedDict", "_codecs.encode", "numpy.core.multiarray._reconstruct",
                 "torch.FloatStorage", "utils.task_manager.TaskManager", "builtins.set"):
        assert not R.denied_global(name), name
    assert set(R.DENY_MODULES) >= {"os", "posix", "subprocess", "sys", "importlib", "runpy", "socket", "shutil",
                                   "pickle", "marshal"}
    assert {f"builtins.{n}" for n in ("eval", "exec", "compile", "getattr", "__import__", "open")} <= \
        set(R.DENY_NAMES)


def test_the_denylist_covers_python2_names_and_torchs_renames():
    for name in ("commands.getoutput", "cPickle.loads", "__builtin__.set", "copy_reg._reconstructor",
                 "cStringIO.StringIO", "urllib2.urlopen", "httplib.HTTPConnection", "__builtin__.reduce",
                 "__builtin__.intern", "copyreg._reconstructor", "functools.reduce", "io.open", "_io.open",
                 "urllib.request.urlopen", "http.client.HTTPConnection", "StringIO.StringIO", "whichdb.whichdb",
                 "_abcoll.Callable", "collections.abc.Callable", "Queue.Queue", "UserDict.UserDict",
                 "collections.UserDict", "exceptions.StandardError", "itertools.imap", "builtins.map"):
        assert R.denied_global(name), name
        with pytest.raises(SystemExit, match="denylisted"):
            R.check_globals({"m.pkl": [name]}, [name])
    assert {R.torch_py2_renamed(f"{m}.{n}") for (m, n) in R.TORCH_PY2_NAMES} <= set(R.DENY_NAMES)
    assert R.torch_py2_renamed("__builtin__.reduce") == "functools.reduce"
    assert R.torch_py2_renamed("copy_reg._reconstructor") == "copyreg._reconstructor"
    assert R.torch_py2_renamed("collections.OrderedDict") == "collections.OrderedDict"
    for name in ("collections.OrderedDict", "_codecs.encode", "numpy.core.multiarray._reconstruct",
                 "numpy.core.multiarray.scalar", "numpy.dtype", "numpy.ndarray", "numpy.dtypes.Int64DType",
                 "torch.FloatStorage", "torch.LongStorage", "torch._utils._rebuild_tensor_v2",
                 "utils.event_codec.FastCodec", "utils.note_event_dataclasses.Event",
                 "utils.note_event_dataclasses.EventRange", "utils.task_manager.TaskManager",
                 "utils.tokenizer.NoteEventTokenizer"):     # every global the audited scan found, and the safe type
        assert not R.denied_global(name), name


# --- the network and process refusals -------------------------------------------------------------------------------------

def test_every_network_and_process_call_refuses(monkeypatch):
    import _posixsubprocess
    import posix
    import socket

    originals = (os.system, os.popen, os.execv, posix.system, subprocess.Popen._execute_child,
                 _posixsubprocess.fork_exec, socket.socket.connect, socket.create_connection, socket.getaddrinfo)
    with monkeypatch.context() as m:
        labels = R.install_refusals(m.setattr)
        for want in ("os.system", "os.popen", "os.execv", "os.execl", "os.execvp", "os.execve", "os.spawnv",
                     "os.spawnlp", "os.posix_spawn", "os.posix_spawnp", "posix.system", "posix.execv",
                     "subprocess", "_posixsubprocess.fork_exec", "socket.socket.connect", "socket.socket.connect_ex",
                     "socket.socket.sendto", "socket.create_connection", "socket.getaddrinfo"):
            assert want in labels, want
        calls = [lambda: os.system("true"), lambda: os.popen("true"), lambda: os.execv("/bin/true", ["true"]),
                 lambda: os.execl("/bin/true", "true"), lambda: os.execvp("true", ["true"]),
                 lambda: os.spawnv(os.P_WAIT, "/bin/true", ["true"]), lambda: os.spawnlp(os.P_WAIT, "true", "true"),
                 lambda: os.posix_spawn("/bin/true", ["true"], {}), lambda: os.posix_spawnp("true", ["true"], {}),
                 lambda: posix.system("true"), lambda: subprocess.run(["true"]),
                 lambda: subprocess.check_output(["true"]), lambda: subprocess.Popen(["true"]),
                 lambda: _posixsubprocess.fork_exec(), lambda: socket.create_connection(("127.0.0.1", 9)),
                 lambda: socket.getaddrinfo("localhost", 80)]
        for call in calls:
            with pytest.raises(SystemExit, match="refused in the torch modes"):
                call()
        s = socket.socket()
        try:
            for call in (lambda: s.connect(("127.0.0.1", 9)), lambda: s.connect_ex(("127.0.0.1", 9)),
                         lambda: s.sendto(b"x", ("127.0.0.1", 9))):
                with pytest.raises(SystemExit, match="refused"):
                    call()
        finally:
            s.close()
    assert (os.system, os.popen, os.execv, posix.system, subprocess.Popen._execute_child, _posixsubprocess.fork_exec,
            socket.socket.connect, socket.create_connection, socket.getaddrinfo) == originals          # restored


# --- the guarded load and the key report ----------------------------------------------------------------------------------

class _FakeLoad:
    def __init__(self, result="loaded", fail=None):
        self.calls, self.result, self.fail, self.in_safe = [], result, fail, None

    def __call__(self, fh, **kw):
        self.calls.append((fh.name, fh.closed, fh.tell(), kw, self.in_safe))
        if self.fail:
            raise self.fail
        return self.result


def _guard(tmp_path, allow=("collections.OrderedDict",), fake=None, members=None):
    p = _zip_ckpt(tmp_path / "synthetic.pth", members or {
        "archive/data.pkl": pickle.dumps(collections.OrderedDict(), protocol=2)})
    fake = fake or _FakeLoad()
    resolved = []

    @contextlib.contextmanager
    def safe_globals(objs):
        fake.in_safe = list(objs)
        yield
        fake.in_safe = None

    def resolve(names, aliases):
        resolved.append((list(names), aliases))
        return [("obj", n) for n in names]

    g = R.GuardedLoad(p, R.file_sha(p), allow, {"top": "alias"}, fake, safe_globals, resolve=resolve)
    return g, p, fake, resolved


def test_guarded_load_forces_weights_only_on_its_own_handle(tmp_path):
    g, p, fake, resolved = _guard(tmp_path)
    assert g(p, map_location="cuda", weights_only=False, mmap=True) == "loaded"
    name, closed, pos, kw, safe = fake.calls[0]
    assert name == os.path.realpath(p) and not closed and pos == 0
    assert kw == {"map_location": "cpu", "weights_only": True}                 # forced, whatever the caller asked
    assert safe == [("obj", "collections.OrderedDict")]                        # exactly the allowlist made safe
    assert resolved == [(["collections.OrderedDict"], {"top": "alias"})] and g.loads == [os.path.realpath(p)]
    assert g(pathlib.Path(p)) == "loaded" and g(p.encode()) == "loaded" and len(resolved) == 1   # resolved once
    link = tmp_path / "link.pth"
    link.symlink_to(p)
    assert g(str(link)) == "loaded"                                             # the same file by its real path


def test_guarded_load_refuses(tmp_path):
    g, p, fake, _ = _guard(tmp_path)
    other = _zip_ckpt(tmp_path / "other.pth", {"archive/data.pkl": pickle.dumps(1, protocol=2)})
    with pytest.raises(SystemExit, match="only the pinned"):
        g(other)
    with open(p, "rb") as f:
        with pytest.raises(SystemExit, match="did not open"):
            g(f)                                                                # a handle opened by someone else
    with pytest.raises(SystemExit, match="did not open"):
        g(io.BytesIO(open(p, "rb").read()))
    with pytest.raises(SystemExit, match="pickle_module"):
        g(p, pickle_module=pickle)
    with pytest.raises(SystemExit, match="positional"):
        g(p, "cpu", pickle)
    assert fake.calls == []                                                     # nothing reached the loader
    pathlib.Path(p).write_bytes(pathlib.Path(other).read_bytes())
    with pytest.raises(SystemExit, match="sha256 is now"):
        g(p)                                                                    # changed after the first check
    assert fake.calls == []


def test_guarded_load_rescans_and_wraps_the_loaders_refusal(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    g, p, fake, _ = _guard(tmp_path / "a", allow=("a.b",))
    with pytest.raises(SystemExit, match="outside the allowlist"):
        g(p)                                                                    # re-scanned on the load's handle
    assert fake.calls == []
    g2, p2, _, _ = _guard(tmp_path / "b", fake=_FakeLoad(fail=pickle.UnpicklingError("Weights only load failed")))
    with pytest.raises(SystemExit, match=r"weights_only=True\) refused the checkpoint"):
        g2(p2)


def test_resolve_globals():
    assert R.resolve_globals(["collections.OrderedDict"], {}) == [(collections.OrderedDict, "collections.OrderedDict")]
    got =R.resolve_globals(["fakeutils.OrderedDict", "fakeutils.abc.Mapping"], {"fakeutils": "collections"})
    assert got == [(collections.OrderedDict, "fakeutils.OrderedDict"),
                   (collections.abc.Mapping, "fakeutils.abc.Mapping")]                 # the alias, as mt3's utils
    assert R.MT3_GLOBAL_ALIASES == {"utils": "mt3_infer.models.yourmt3.utils"}
    for bad in (["collections.NoSuchThing"], ["nosuchmodule_synthetic.X"]):
        with pytest.raises(SystemExit, match="does not resolve"):
            R.resolve_globals(bad, {})
    with pytest.raises(SystemExit, match="denylisted"):
        R.resolve_globals(["os.system"], {})


class _Result:
    def __init__(self, missing, unexpected):
        self.missing_keys, self.unexpected_keys = missing, unexpected


def test_key_report():
    calls = []

    def original(module, state, strict, *a, **k):
        calls.append((strict, a, k))
        return _Result([], ["extra.w"]) if state == "ok" else _Result(["needed.w"], [])

    class Net:
        pass

    report = R.KeyReport(original)
    f = report.wrapper()
    assert f(Net(), "ok").unexpected_keys == ["extra.w"]
    assert f(Net(), "ok", strict=False, assign=True)
    assert calls == [(False, (), {}), (False, (), {"assign": True})]          # strict=False always: keys reported
    assert report.rows == [{"module": "Net", "strict_asked": True, "missing": [], "unexpected": ["extra.w"]},
                           {"module": "Net", "strict_asked": False, "missing": [], "unexpected": ["extra.w"]}]
    with pytest.raises(SystemExit, match="lacks 1 keys"):
        f(Net(), "missing")
    assert report.rows[-1]["missing"] == ["needed.w"]


# --- the torch path end to end, on fakes (no torch, no tool) ----------------------------------------------------------------

class _FakeModule:
    def load_state_dict(self, state, strict=True):
        return _Result([], [])


def _fake_torch():
    return types.SimpleNamespace(load=None, serialization=types.SimpleNamespace(load=None, safe_globals=None),
                                 nn=types.SimpleNamespace(Module=type("Module", (_FakeModule,), {})),
                                 __version__="0.0-synthetic")


def _fake_world(monkeypatch, tmp_path, mode, order, ckpt_members=None):
    """The torch path's heavy parts replaced: torch by a namespace whose load reads nothing, the tool by an adapter
    that loads through `torch.load` and `load_state_dict` as the real ones do, soundfile by a fixed rate."""
    torch = _fake_torch()
    loaded = []

    def real_load(fh, map_location=None, weights_only=None):
        loaded.append((fh.name, map_location, weights_only))
        return {"model": {}}

    @contextlib.contextmanager
    def safe_globals(objs):
        yield

    torch.load, torch.serialization.load, torch.serialization.safe_globals = real_load, real_load, safe_globals

    class FakeAdapter:
        def __init__(self, spec, threads):
            order.append("adapter")
            state = torch.load(spec["model"], map_location="cpu", weights_only=False)   # as the upstream loaders do
            torch.nn.Module().load_state_dict(state["model"], strict=False)
            self.versions = {"tool": "0-synthetic"}

        def read(self, path):
            order.append(("read", path))
            return "raw"

        @staticmethod
        def notes(raw, options):
            if mode == "kong":
                return [(1.0 + options["onset_threshold"], 1.5 + options["frame_threshold"], 60, 0.5, None),
                        (0.2, 0.8, 40, 0.5, None)]                          # the second lies in the lead-in
            keep = [(1.2, 1.6, 64, 1.0, None)]
            return keep + ([(1.3, 1.9, 36, 1.0, None)] if options["programs"] == "pitched" else [])

    def fake_refusals(setter=setattr):
        order.append("refusals")
        return ["synthetic.refusal"]

    def fake_import(threads):
        order.append("torch")
        return torch

    monkeypatch.setattr(os, "environ", dict(os.environ))
    monkeypatch.setattr(R, "install_refusals", fake_refusals)
    monkeypatch.setattr(R, "import_torch", fake_import)
    monkeypatch.setitem(R.ADAPTERS, mode, FakeAdapter)
    monkeypatch.setattr(R, "_input_rate", lambda src: 1000)
    monkeypatch.setattr(R, "_padded", lambda src, n, wd: order.append(("pad", n)) or src)
    ckpt = _zip_ckpt(tmp_path / "synthetic.pth", ckpt_members or {
        "archive/data.pkl": pickle.dumps(collections.OrderedDict(), protocol=2)})
    src = tmp_path / "synthetic.wav"
    src.write_bytes(b"synthetic input")
    return torch, ckpt, src, loaded


def test_torch_path_kong_end_to_end_on_fakes(monkeypatch, tmp_path):
    order = []
    torch, ckpt, src, loaded = _fake_world(monkeypatch, tmp_path, "kong", order)
    spec = _spec("kong", model=ckpt, model_sha256=R.file_sha(ckpt), grid=KONG_PLAN_GRID, lead_in_s=1.0,
                 allow_globals=["collections.OrderedDict"])
    dst = tmp_path / "synthetic.json"
    R.main(_args("kong", spec, str(src), str(dst)))
    assert order == ["refusals", "torch", "adapter", ("pad", 1000), ("read", str(src))]  # refusals before torch
    assert loaded == [(os.path.realpath(ckpt), "cpu", True)]                          # through the guard
    assert isinstance(torch.load, R.GuardedLoad) and torch.serialization.load is torch.load
    out = json.loads(dst.read_text())
    assert list(out)[:8] == ["mode", "versions", "model_sha256", "threads", "spec", "input_sha256", "seconds",
                             "events"]
    assert out["mode"] == "kong" and out["spec"] == spec and out["model_sha256"] == R.file_sha(ckpt)
    assert out["input_sha256"] == R.file_sha(str(src)) and out["threads"] == 1
    assert out["versions"]["tool"] == "0-synthetic" and out["versions"]["torch"] == "0.0-synthetic"
    assert out["events"] == [{"on": 0.3, "off": 0.6, "pitch": 60, "amp": 0.5, "bends": []}]   # re-based by the lead-in
    assert [r["options"] for r in out["grid"]] == R.torch_points("kong", R.KONG_SHIPPED, KONG_PLAN_GRID)
    assert out["grid"][0]["events"] == [{"on": 0.2, "off": 0.6, "pitch": 60, "amp": 0.5, "bends": []}]
    assert out["scan"] == {"archive/data.pkl": ["collections.OrderedDict"]}
    assert out["load_report"] == [{"module": "Module", "strict_asked": False, "missing": [], "unexpected": []}]
    assert out["guards"] == ["synthetic.refusal"]


def test_torch_path_mt3_programs_on_fakes(monkeypatch, tmp_path):
    order = []
    _, ckpt, src, _ = _fake_world(monkeypatch, tmp_path, "mt3", order)
    spec = _spec("mt3", model=ckpt, model_sha256=R.file_sha(ckpt), allow_globals=["collections.OrderedDict"],
                 options={"programs": "guitar"}, grid={"programs": ["pitched", "guitar"]})
    dst = tmp_path / "synthetic.json"
    R.main(_args("mt3", spec, str(src), str(dst)))
    out = json.loads(dst.read_text())
    assert [e["pitch"] for e in out["events"]] == [64]
    assert [(r["options"]["programs"], [e["pitch"] for e in r["events"]]) for r in out["grid"]] == \
        [("pitched", [64, 36]), ("guitar", [64])]
    (tmp_path / "again").mkdir()                                        # a fresh world: one main per process
    _, ckpt, src, _ = _fake_world(monkeypatch, tmp_path / "again", "mt3", order)
    no_grid = tmp_path / "no-grid.json"
    spec = dict(spec, model=ckpt)
    spec.pop("grid")
    R.main(_args("mt3", spec, str(src), str(no_grid)))
    assert "grid" not in json.loads(no_grid.read_text())


@pytest.mark.parametrize("members,allow,why", [
    ({"archive/data.pkl": pickle.dumps(collections.OrderedDict(), protocol=2)}, ["torch.FloatStorage"],
     "outside the allowlist"),
    ({"archive/data.pkl": pickle.dumps(eval, protocol=2)}, ["collections.OrderedDict"], "denylisted"),
    ({"archive/data.pkl": b"\x80\x04" + _u("os") + _u("system") + b")0\x93."}, ["collections.OrderedDict"],
     "STACK_GLOBAL"),
])
def test_torch_path_refuses_the_checkpoint_before_any_refusal_or_import(monkeypatch, tmp_path, members, allow, why):
    order = []
    _, ckpt, src, loaded = _fake_world(monkeypatch, tmp_path, "kong", order, ckpt_members=members)
    spec = _spec("kong", model=ckpt, model_sha256=R.file_sha(ckpt), allow_globals=allow)
    with pytest.raises(SystemExit, match=why):
        R.main(_args("kong", spec, str(src), str(tmp_path / "o.json")))
    assert order == [] and loaded == []


def test_torch_path_refuses_an_adapter_that_bypasses_the_guard(monkeypatch, tmp_path):
    order = []
    _, ckpt, src, _ = _fake_world(monkeypatch, tmp_path, "kong", order)

    class Bypass:
        def __init__(self, spec, threads):
            self.versions = {}

    monkeypatch.setitem(R.ADAPTERS, "kong", Bypass)
    spec = _spec("kong", model=ckpt, model_sha256=R.file_sha(ckpt), allow_globals=["collections.OrderedDict"])
    with pytest.raises(SystemExit, match="not loaded through the guarded load"):
        R.main(_args("kong", spec, str(src), str(tmp_path / "o.json")))


# --- the guarded load on real torch (skipped without torch) -----------------------------------------------------------------

class _SyntheticHParams:
    pass


def test_guarded_load_on_real_torch(tmp_path):
    torch = pytest.importorskip("torch")
    p = str(tmp_path / "synthetic.pth")
    torch.save({"state_dict": {"w": torch.zeros(3)}}, p)
    scanned = sorted({g for gs in R.scan_checkpoint(p).values() for g in gs})
    found = R.check_globals(R.scan_checkpoint(p), scanned)
    assert found == scanned and "torch._utils._rebuild_tensor_v2" in found
    g = R.GuardedLoad(p, R.file_sha(p), found, {}, torch.load, torch.serialization.safe_globals)
    assert list(g(p)["state_dict"]) == ["w"]
    q = str(tmp_path / "custom.pth")
    torch.save({"hp": _SyntheticHParams(), "w": torch.zeros(1)}, q)
    names = sorted({x for xs in R.scan_checkpoint(q).values() for x in xs})
    assert f"{_SyntheticHParams.__module__}._SyntheticHParams" in names
    g2 = R.GuardedLoad(q, R.file_sha(q), names, {}, torch.load, torch.serialization.safe_globals)
    assert isinstance(g2(q)["hp"], _SyntheticHParams)                          # an allowlisted class loads
    lean = [n for n in names if not n.endswith("_SyntheticHParams")]
    with pytest.raises(SystemExit, match="outside the allowlist"):
        R.GuardedLoad(q, R.file_sha(q), lean, {}, torch.load, torch.serialization.safe_globals)(q)


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
    assert "weights_only=False" not in src and "torch.load(" not in src        # the only load is the guard's
    loads = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and any(k.arg == "weights_only" for k in n.keywords)]
    assert len(loads) == 1 and ast.unparse(loads[0]) == "self.load_fn(fh, map_location='cpu', weights_only=True)"
    assert "pickle.load" not in src and "pickle.loads" not in src             # the scan never unpickles


def test_no_runtime_fetch():
    src = (REPO / "learn" / "readerr_run.py").read_text()
    tree = ast.parse(src)
    deny = [n for n in tree.body if isinstance(n, ast.Assign) and [getattr(t, "id", None) for t in n.targets]
            == ["DENY_MODULES"]]
    assert len(deny) == 1                  # the denylist names network modules only to refuse them: left out here
    src = src.replace(ast.get_source_segment(src, deny[0]), "")
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


# --- the torch modes, where their venvs and checkpoints are installed (skipped on CI) --------------------------------------

SMOKE = {"mt3": ("A", "ymt3", {"programs": "pitched"}, {"programs": ["pitched", "guitar"]}),
         "kong": ("B", "kong-fl", dict(R.KONG_SHIPPED), {"onset_threshold": [0.2, 0.5]})}


@pytest.mark.parametrize("mode", R.TORCH_MODES)
def test_torch_mode_smoke_in_its_venv(tmp_path, mode):
    tools = pytest.importorskip("learn.readerr_tools")                # unit F: the venvs' and checkpoints' paths
    lock, cand, options, grid = SMOKE[mode]
    try:
        py, ckpt = tools.venv_python(lock), tools.checkpoint_path(cand)
    except SystemExit:                                                # no manifest here
        pytest.skip(f"no {mode} install here")
    if not py.exists() or not ckpt.is_file():
        pytest.skip(f"no {mode} venv or checkpoint here")
    src = tmp_path / "synthetic.wav"
    _tone_wav(src, seconds=3.0, sr=22050)                             # not the models' rate: the resample runs
    from learn import scratch_readerr as X

    allow = sorted({g for gs in R.scan_checkpoint(str(ckpt)).values() for g in gs})   # the gate audits the real list
    allow += [t for t in X.TORCH_SAFE_TYPES if t not in allow]        # as the gate's tx_allow_globals adds them
    spec = {"model": str(ckpt), "model_sha256": R.file_sha(str(ckpt)), "options": options, "grid": grid,
            "allow_globals": allow, "lead_in_s": 0.5}
    dst = tmp_path / "synthetic.json"
    r = subprocess.run([str(py), "-I", str(REPO / "learn" / "readerr_run.py"), mode, "--spec", json.dumps(spec),
                        str(src), str(dst)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    out = json.loads(dst.read_text())
    assert out["mode"] == mode and out["spec"] == spec and len(out["grid"]) == 2
    assert out["load_report"] and not any(row["missing"] for row in out["load_report"])
    assert out["versions"]["torch"] and all(v is not None for v in out["versions"].values())   # read from modules
    assert all(e["on"] >= 0 and e["off"] > e["on"] and e["bends"] == [] for e in out["events"])
