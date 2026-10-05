"""PR12's settings as the model sees them: a sampler, a label encoding, and the
plugin edits that render a label.

Everything is in the plugin's *stored* units (rotations 0..1, dB, Hz, enum indices,
"true"/"false"), so a sampled setting goes to the render server without passing
through the human-value conversion. Each render starts from the PR12 template with the
rule set R of `scripts/render_preset_panel.py` (time effects, doubler, gate, spring
reverb and transpose off), and only the controls below vary.

Drive is labelled as *effective* drive: `inputGain` plus the DI window's loudness above
−22.9 LUFS (the median of the development DIs), so a quiet player at +6 dB and a loud
one at 0 dB carry the label their sound has. Turning a prediction back into a preset
uses `inputGain = effective drive`, the level a song does not reveal being assumed.
"""

from __future__ import annotations

import math
import pathlib
import random
from typing import Dict, List, Tuple

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
FACTORY = pathlib.Path("/Library/Audio/Presets/Neural DSP/Morgan Amps Suite")
TEMPLATE = PLUGIN_ROOT / "samples" / "Example_Clean_PR12.xml"
ASSUMED_LUFS = -22.9
PR12_INDEX = 1
MICS = 10                       # 0..9; 10 is Custom IR and never sampled

# name, low, high, warp ("lin" or "log"), the module whose switch gates it (or None)
CONTINUOUS: List[Tuple[str, float, float, str, str]] = [
    ("parameters/inputGain", -24.0, 24.0, "lin", None),        # effective drive
    ("pr12Amp/pr12Volume", 0.0, 1.0, "lin", None),
    ("pr12Amp/pr12Treble", 0.0, 1.0, "lin", None),
    ("pr12Amp/pr12Bass", 0.0, 1.0, "lin", None),
    *[(f"pr12EQ/pr12EQBand{i}", -12.0, 12.0, "lin", None) for i in range(1, 10)],
    ("pr12EQ/pr12EQHpf", 20.0, 500.0, "log", None),
    ("pr12EQ/pr12EQLpf", 1000.0, 20000.0, "log", None),
    ("compressor/compressorCompression", 0.0, 1.0, "lin", "compressor/compressorActive"),
    ("compressor/compressorMix", 0.0, 1.0, "lin", "compressor/compressorActive"),
    ("drive1/drive1Drive", 0.0, 1.0, "lin", "drive1/drive1Active"),
    ("drive1/drive1Tone", 0.0, 1.0, "lin", "drive1/drive1Active"),
    ("drive1/drive1Level", 0.0, 1.0, "lin", "drive1/drive1Active"),
    ("drive2/drive2Gain", 0.0, 1.0, "lin", "drive2/drive2Active"),
    ("drive2/drive2Bass", 0.0, 1.0, "lin", "drive2/drive2Active"),
    ("drive2/drive2Treble", 0.0, 1.0, "lin", "drive2/drive2Active"),
    ("drive2/drive2Level", 0.0, 1.0, "lin", "drive2/drive2Active"),
    ("cabParameters/leftCabPosition", 0.0, 1.0, "lin", None),
    ("cabParameters/leftCabDistance", 0.0, 1.0, "lin", None),
    ("cabParameters/leftCabMicLevel", -40.0, 6.0, "lin", None),
    ("cabParameters/rightCabPosition", 0.0, 1.0, "lin", "cabParameters/rightCabActive"),
    ("cabParameters/rightCabDistance", 0.0, 1.0, "lin", "cabParameters/rightCabActive"),
    ("cabParameters/rightCabMicLevel", -40.0, 6.0, "lin", "cabParameters/rightCabActive"),
]
BINARY = ["compressor/compressorActive", "compressor/compressorRelease",
          "drive1/drive1Active", "drive2/drive2Active", "cabParameters/rightCabActive"]
CATEGORICAL = [("cabParameters/leftMicType", MICS, None),
               ("cabParameters/rightMicType", MICS, "cabParameters/rightCabActive")]

RULE_SET = {"reverb/reverbActive": "false", "delay/delayActive": "false",
            "tremolo/tremoloActive": "false", "parameters/doublerActive": "false",
            "parameters/gateActive": "false", "fxParameters/sectionActive": "true",
            "parameters/transpose": "0", "pr12Amp/pr12Reverb": "0",
            "cabParameters/leftCabActive": "true", "cabParameters/leftRoomActive": "false",
            "cabParameters/rightRoomActive": "false", "pr12EQ/pr12EQActive": "true",
            "cabParameters/leftCabPan": "0", "cabParameters/rightCabPan": "0",
            "cabParameters/leftCabPhase": "false", "cabParameters/rightCabPhase": "false",
            "cabParameters/leftCabStereo": "false", "cabParameters/rightCabStereo": "false"}


def _read(path: pathlib.Path) -> Dict[str, str]:
    import sys

    sys.path.insert(0, str(PLUGIN_ROOT))
    from format.parser import parse
    from format.structured import build

    preset = build(parse(path.read_bytes()))
    return {f"{p.module_path}/{p.key}": p.value for p in preset.parameters}


def template_state() -> Dict[str, str]:
    return _read(TEMPLATE)


def factory_presets() -> Dict[str, Dict[str, str]]:
    """Every PR12 factory preset (never `User/`), by name."""
    out = {}
    for path in sorted(FACTORY.rglob("*.xml")):
        if "User" in path.relative_to(FACTORY).parts:
            continue
        state = _read(path)
        if int(float(state.get("/selectedAmp", -1))) == PR12_INDEX:
            out[str(path.relative_to(FACTORY).with_suffix(""))] = state
    return out


# --- normalised units ---------------------------------------------------------

def to_unit(value: float, lo: float, hi: float, warp: str) -> float:
    if warp == "log":
        return (math.log(value) - math.log(lo)) / (math.log(hi) - math.log(lo))
    return (value - lo) / (hi - lo)


def from_unit(u: float, lo: float, hi: float, warp: str) -> float:
    u = min(1.0, max(0.0, u))
    if warp == "log":
        return math.exp(math.log(lo) + u * (math.log(hi) - math.log(lo)))
    return lo + u * (hi - lo)


# --- the sampler -------------------------------------------------------------

def _laplace(rng: random.Random, scale: float) -> float:
    return rng.choice((-1, 1)) * rng.expovariate(1 / scale)


def sample_random(rng: random.Random) -> Dict[str, object]:
    """Coverage: every control drawn over its plausible range."""
    s: Dict[str, object] = {}
    s["parameters/inputGain"] = rng.uniform(-14, 14)
    s["pr12Amp/pr12Volume"] = rng.uniform(0, 1)
    s["pr12Amp/pr12Treble"] = rng.uniform(0, 1)
    s["pr12Amp/pr12Bass"] = rng.uniform(0, 1)
    for i in range(1, 10):
        s[f"pr12EQ/pr12EQBand{i}"] = (0.0 if rng.random() < 0.4
                                      else max(-12, min(12, _laplace(rng, 3.0))))
    s["pr12EQ/pr12EQHpf"] = (rng.uniform(20, 80) if rng.random() < 0.6
                             else math.exp(rng.uniform(math.log(20), math.log(400))))
    s["pr12EQ/pr12EQLpf"] = (20000.0 if rng.random() < 0.5
                             else math.exp(rng.uniform(math.log(3000), math.log(20000))))
    s["compressor/compressorActive"] = rng.random() < 0.6
    s["compressor/compressorRelease"] = rng.random() < 0.5
    s["compressor/compressorCompression"] = rng.uniform(0, 1)
    s["compressor/compressorMix"] = rng.uniform(0.15, 1)
    s["drive1/drive1Active"] = rng.random() < 0.2
    s["drive2/drive2Active"] = rng.random() < 0.15
    for k in ("drive1/drive1Drive", "drive1/drive1Tone", "drive1/drive1Level",
              "drive2/drive2Gain", "drive2/drive2Bass", "drive2/drive2Treble",
              "drive2/drive2Level"):
        s[k] = rng.uniform(0, 1)
    s["cabParameters/rightCabActive"] = rng.random() < 0.7
    for side in ("left", "right"):
        s[f"cabParameters/{side}MicType"] = rng.randrange(MICS)
        s[f"cabParameters/{side}CabPosition"] = rng.uniform(0, 1)
        s[f"cabParameters/{side}CabDistance"] = rng.uniform(0, 1)
        s[f"cabParameters/{side}CabMicLevel"] = rng.uniform(-12, 6)
    return s


def from_state(state: Dict[str, str], template: Dict[str, str]) -> Dict[str, object]:
    """A preset's state as a sample (missing keys from the template)."""
    s: Dict[str, object] = {}
    get = lambda k: state.get(k, template.get(k))
    for name, lo, hi, warp, _ in CONTINUOUS:
        s[name] = min(hi, max(lo, float(get(name))))
    for name in BINARY:
        s[name] = str(get(name)).lower() in ("true", "1")
    for name, n, _ in CATEGORICAL:
        v = int(float(get(name)))
        s[name] = v if 0 <= v < n else 0
    return s


def jitter(s: Dict[str, object], rng: random.Random, amount=0.07, flip=0.1) -> Dict[str, object]:
    out = dict(s)
    for name, lo, hi, warp, _ in CONTINUOUS:
        u = to_unit(float(out[name]), lo, hi, warp) + rng.gauss(0, amount)
        out[name] = from_unit(u, lo, hi, warp)
    for name in BINARY:
        if rng.random() < flip:
            out[name] = not out[name]
    for name, n, _ in CATEGORICAL:
        if rng.random() < flip:
            out[name] = rng.randrange(n)
    return out


def sample(rng: random.Random, factory: List[Dict[str, object]]) -> Tuple[str, Dict[str, object]]:
    """Half coverage, half jittered factory presets."""
    if rng.random() < 0.5:
        return "random", sample_random(rng)
    return "factory", jitter(rng.choice(factory), rng)


# --- render edits and labels -------------------------------------------------

def _fmt(v: object) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    return f"{float(v):.6g}"


def render_command(s: Dict[str, object], template: Dict[str, str],
                   input_gain_db: float) -> Dict[str, object]:
    """The server command (selectAmp + edits) for a sample, at the given inputGain."""
    state = {k: v for k, v in template.items() if k.split("/")[0]}   # module controls
    state.pop("cabParameters/leftChosenIRFilePath", None)
    state.pop("cabParameters/rightChosenIRFilePath", None)
    for k, v in s.items():
        state[k] = _fmt(v)
    state.update(RULE_SET)
    state["parameters/inputGain"] = _fmt(max(-24.0, min(24.0, input_gain_db)))
    edits = []
    for k, v in state.items():
        module, _, key = k.rpartition("/")
        edits.append({"module": module, "key": key, "value": v})
    return {"selectAmp": PR12_INDEX, "edits": edits}


def encode(s: Dict[str, object], effective_drive: float):
    """(continuous[0..1], continuous mask, binary, categorical, categorical mask)."""
    cont, mask = [], []
    for name, lo, hi, warp, gate in CONTINUOUS:
        v = effective_drive if name == "parameters/inputGain" else float(s[name])
        cont.append(to_unit(min(hi, max(lo, v)), lo, hi, warp))
        mask.append(1.0 if gate is None or s[gate] else 0.0)
    binary = [1.0 if s[name] else 0.0 for name in BINARY]
    cat = [int(s[name]) for name, _, _ in CATEGORICAL]
    cmask = [1.0 if gate is None or s[gate] else 0.0 for _, _, gate in CATEGORICAL]
    return cont, mask, binary, cat, cmask


def decode(cont, binary_p, cat_p) -> Tuple[Dict[str, object], float]:
    """A sample and its effective drive, from the model's outputs."""
    s: Dict[str, object] = {}
    drive = 0.0
    for (name, lo, hi, warp, _), u in zip(CONTINUOUS, cont):
        v = from_unit(float(u), lo, hi, warp)
        if name == "parameters/inputGain":
            drive = v
        s[name] = v
    for name, p in zip(BINARY, binary_p):
        s[name] = bool(p > 0.5)
    for (name, _, _), p in zip(CATEGORICAL, cat_p):
        s[name] = int(max(range(len(p)), key=lambda i: p[i]))
    return s, drive
