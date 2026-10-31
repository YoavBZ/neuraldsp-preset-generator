"""Sections come from the file's tree, so Morgan Amps Suite X's layout reads like the original's."""

from __future__ import annotations

import pathlib

import pytest

from format.parser import parse
from format.structured import build
from format.valuetree import property_modules
from packs.loader import detect_pack

ROOT = pathlib.Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples" / "Example_Clean_PR12.xml"


def _count(buf: bytes, i: int):
    width = buf[i] & 0x7F
    return int.from_bytes(buf[i + 1:i + 1 + width], "little"), i + 1 + width


def _read(buf: bytes, i: int = 0):
    """(type, [(name, raw value bytes)], [children]) and the end offset."""
    end = buf.index(0, i)
    kind = buf[i:end].decode()
    count, i = _count(buf, end + 1)
    props = []
    for _ in range(count):
        end = buf.index(0, i)
        name = buf[i:end].decode()
        size, j = _count(buf, end + 1)
        props.append((name, buf[end + 1:j + size]))
        i = j + size
    count, i = _count(buf, i)
    children = []
    for _ in range(count):
        child, i = _read(buf, i)
        children.append(child)
    return (kind, props, children), i


def _int(n: int) -> bytes:
    assert 0 <= n < 256, "the helper writes one-byte counts only"
    return b"\x00" if n == 0 else bytes([1, n])   # JUCE writes a zero as one width byte


def _write(node) -> bytes:
    kind, props, children = node
    out = kind.encode() + b"\x00" + _int(len(props))
    for name, raw in props:
        out += name.encode() + b"\x00" + raw
    out += _int(len(children))
    return out + b"".join(_write(c) for c in children)


def _x_layout(node):
    """Re-save the way Morgan X does: empty `subModels` children left out."""
    kind, props, children = node
    kept = [_x_layout(c) for c in children
            if not (c[0] == "subModels" and not c[1] and not c[2])]
    return kind, props, kept


def _settings(buf: bytes):
    return {k: p.value for k, p in build(parse(buf)).by_path.items()}


def test_an_original_preset_survives_a_tree_round_trip():
    buf = SAMPLE.read_bytes()
    tree, end = _read(buf)
    assert end == len(buf) and _write(tree) == buf


def test_the_x_layout_reads_the_same_settings():
    buf = SAMPLE.read_bytes()
    x = _write(_x_layout(_read(buf)[0]))
    assert len(x) < len(buf)                      # the empty markers really went
    original, rewritten = _settings(buf), _settings(x)
    assert rewritten == original
    assert ("pr12Amp", "pr12Volume") in rewritten and ("sw50rAmp", "sw50rVolume") in rewritten


def test_anything_but_one_whole_tree_is_left_to_the_old_reading():
    buf = SAMPLE.read_bytes()
    assert property_modules(buf) is not None
    assert property_modules(buf + b"\x00") is None
    assert property_modules(buf[:len(buf) // 2]) is None
    assert property_modules(b"not a preset") is None
    tokens = parse(buf)
    cut = build(tokens).by_path[("parameters", "transpose")]
    damaged = b"".join(t.to_bytes() for n, t in enumerate(tokens)
                       if n not in (cut.key_index, cut.value_index))
    assert property_modules(damaged) is None      # its count still says one more property


def test_morgan_x_presets_are_morgan_and_tone_king_x_is_not_yet():
    assert detect_pack("morgan-x").pack_id == "morgan"
    assert detect_pack("morgan").pack_id == "morgan"
    assert detect_pack("toneking") is None        # Tone King X: a new layout, no pack reads it


@pytest.mark.parametrize("damage", [
    lambda b: b.replace(b"version\x00\x01\x07\x05", b"version\x00\x05\x07\x05", 1),  # width over 4
    lambda b: b.replace(b"version\x00\x01\x07\x05", b"version\x00\x01\x07\x0b", 1),  # no such value type
    lambda b: b.replace(b"version\x00\x01\x07\x05", b"version\x00\x81\x07\x05", 1),  # negative size
])
def test_a_bad_count_or_value_type_is_not_a_tree(damage):
    buf = SAMPLE.read_bytes()
    broken = damage(buf)
    assert broken != buf and property_modules(broken) is None


ORIGINAL = pathlib.Path("/Library/Audio/Presets/Neural DSP/Morgan Amps Suite")
X_EDITION = pathlib.Path("/Library/Audio/Presets/Neural DSP/Morgan Amps Suite X")
CAB_FLAGS = {("cabParameters", k) for k in (
    "cabStereo", "leftIsCustomIR", "rightIsCustomIR", "leftCabStereo", "rightCabStereo")}


@pytest.mark.skipif(not (ORIGINAL.is_dir() and X_EDITION.is_dir()),
                    reason="needs both Morgan Amps Suite and Morgan Amps Suite X installed")
def test_installed_morgan_x_presets_read_like_the_originals():
    """Where both plugins are installed: every X-format factory preset holds the
    same settings as the original's file of the same name, apart from the cab
    flags X renamed, its browser tags, and the version string."""
    pairs = [(f, ORIGINAL / f.relative_to(X_EDITION)) for f in sorted(X_EDITION.rglob("*.xml"))
             if f.read_bytes().startswith(b"morgan-x\x00")]
    pairs = [(x, o) for x, o in pairs if o.exists()]
    assert pairs
    for x, o in pairs:
        ours, theirs = _settings(x.read_bytes()), _settings(o.read_bytes())
        skip = CAB_FLAGS | {("", "value"), ("", "version")}
        assert {k: v for k, v in ours.items() if k not in skip} == \
            {k: v for k, v in theirs.items() if k not in skip}, x.name
