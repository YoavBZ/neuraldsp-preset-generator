"""A synthetic amp chain whose topology mirrors Morgan's — the development vehicle.

Nothing here emulates Neural DSP's DSP, and it is not trying to: it is a chain of
ordinary textbook blocks in the same *order*, wired to the same parameter names,
kinds, units and ranges as `packs/morgan/manifest.json`. That is the whole point.
It gives exact ground-truth parameters and unlimited free renders, so every
inversion in M3 and the optimiser in M4 can be developed and benchmarked against
known answers before the plugin's 0.2 dB render noise and 0.29 s per render enter
the picture.

    input gain -> gate -> compressor -> drive -> 9-band graphic EQ
                -> HPF/LPF -> power-amp saturation -> cab (FIR)
                -> delay -> reverb -> output gain

Two properties are load-bearing and both are tested:

**The parameter contract comes from the manifest, not from here.** `PARAMETERS`
names keys and default values only; every kind, unit and range is looked up in the
pack at call time. So `match/space.py` can build a search space over this chain
with no special-casing, and a chain that drifts from the manifest fails a test
rather than quietly accepting values the plugin would reject.

**Values are the human ones**, exactly as `apply_spec.py` consumes them — a
rotation is a percent, a metered value is in its own unit, a switch is a bool.
The same spec therefore drives the synthetic renderer and the real preset writer,
which is what §11 of the plan requires: Morgan's live state and its preset files
are different encodings, and the only thing that keeps them from drifting is
being generated from one source.

Unlike the plugin, this is exactly reproducible: same parameters, same input,
bit-identical output, every time. That is a difference from the real backends
worth remembering when a test passes here and fails there.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Mapping, Optional, Tuple

from . import SAMPLE_RATE, require

PACK_ID = "morgan"

# The amp this chain models. Morgan conditions every amp control on `selectedAmp`,
# and writing an inactive amp's controls is a silent no-op, so the synthetic chain
# picks one and uses its module prefix throughout.
AMP = "sw50r"

Key = Tuple[str, str]

# What the chain implements, and the value each parameter takes when the caller
# does not say. Kinds, units and ranges are deliberately absent: they live in the
# manifest, and `parameter_specs()` reads them from there.
PARAMETERS: Dict[Key, Any] = {
    ("parameters", "inputGain"): 0.0,            # dB, -24..24
    ("parameters", "gateActive"): False,
    ("parameters", "gateThreshold"): -96.0,      # dB, -96..0
    ("compressor", "compressorActive"): False,
    ("compressor", "compressorCompression"): 40.0,   # percent
    ("compressor", "compressorLevel"): 50.0,
    ("compressor", "compressorMix"): 100.0,
    ("drive1", "drive1Active"): False,
    ("drive1", "drive1Drive"): 40.0,
    ("drive1", "drive1Level"): 50.0,
    ("drive1", "drive1Tone"): 50.0,
    ("sw50rAmp", "sw50rVolume"): 40.0,
    ("sw50rAmp", "sw50rBass"): 50.0,
    ("sw50rAmp", "sw50rMid"): 50.0,
    ("sw50rAmp", "sw50rTreble"): 50.0,
    ("sw50rAmp", "sw50rLevel"): 50.0,
    ("sw50rAmp", "sw50rBright"): False,
    ("sw50rEQ", "sw50rEQActive"): True,
    ("sw50rEQ", "sw50rEQHpf"): 20.0,             # Hz, 20..500
    ("sw50rEQ", "sw50rEQLpf"): 20000.0,          # Hz, 1000..20000
    ("cabParameters", "leftCabActive"): True,
    ("cabParameters", "leftCabPosition"): 0.5,   # fraction, 0..1
    ("cabParameters", "leftCabMicLevel"): 0.0,   # dB, -40..6
    ("delay", "delayActive"): False,
    ("delay", "delayMix"): 30.0,
    ("delay", "delayFeedback"): 35.0,
    ("delay", "delayTime"): 420.0,               # ms, 16..1500
    ("delay", "delayLowCut"): 60.0,              # Hz, 60..500
    ("delay", "delayHighCut"): 5000.0,           # Hz, 1000..5000
    ("reverb", "reverbActive"): False,
    ("reverb", "reverbMix"): 30.0,
    ("reverb", "reverbDecay"): 2.0,              # seconds, 1..60
    ("reverb", "reverbPreDelay"): 20.0,          # ms, 1..200
    ("reverb", "reverbLowCut"): 50.0,            # Hz, 50..700
    ("reverb", "reverbHighCut"): 10000.0,        # Hz, 1000..10000
    ("parameters", "outputGain"): 0.0,           # dB, -24..24
}

# The nine graphic-EQ bands, in manifest order. Their centre frequencies are not
# written here either: `centre_hz` is declared per band in the manifest and is
# what `match/invert.py` fits its least-squares solution onto.
EQ_BANDS = tuple(f"{AMP}EQBand{i}" for i in range(1, 10))
for _band in EQ_BANDS:
    PARAMETERS[(f"{AMP}EQ", _band)] = 0.0        # dB, -12..12
del _band


class ChainError(ValueError):
    """A parameter this chain does not implement, or a value out of its range."""


def parameter_specs():
    """The manifest's `ParamSpec` for every key the chain implements.

    Raises if the chain names a key the pack does not, which is the check that
    keeps the two from drifting apart.
    """
    from packs.loader import load_pack

    pack = load_pack(PACK_ID)
    specs = {}
    for module, key in PARAMETERS:
        spec = pack.parameters.get(f"{module}/{key}")
        if spec is None:
            raise ChainError(
                f"refchain names {module}/{key}, which packs/{PACK_ID} does not "
                f"declare. The manifest is the contract; this chain follows it."
            )
        specs[(module, key)] = spec
    return specs


def band_centres():
    """The nine EQ centre frequencies, from the manifest."""
    specs = parameter_specs()
    return [float(specs[(f"{AMP}EQ", band)].centre_hz) for band in EQ_BANDS]


def defaults() -> Dict[Key, Any]:
    return dict(PARAMETERS)


def resolve(settings: Optional[Mapping] = None) -> Dict[Key, Any]:
    """Merge caller settings over the defaults, validating against the manifest.

    Accepts keys as `(module, key)` tuples or as `"module/key"` strings, which is
    what a spec file spells them as. Values are validated through the pack, so an
    illegal value fails here for the same reason and with the same message it
    would fail in `apply_spec.py` — the synthetic chain does not accept settings
    the real plugin would refuse.
    """
    from packs.loader import PackError

    specs = parameter_specs()
    resolved = dict(PARAMETERS)
    for raw_key, value in (settings or {}).items():
        key = tuple(raw_key.split("/", 1)) if isinstance(raw_key, str) else tuple(raw_key)
        if len(key) != 2:
            raise ChainError(f"{raw_key!r} is not a module/key pair")
        if key not in resolved:
            raise ChainError(
                f"{key[0]}/{key[1]} is not implemented by the synthetic chain. "
                f"It models {len(PARAMETERS)} of Morgan's parameters; see "
                f"refchain.PARAMETERS."
            )
        spec = specs[key]
        try:
            # Round-trip through the pack's own conversion. This is what makes an
            # out-of-range value an error here rather than a strange render.
            from format.translate import from_binary

            stored = spec_to_stored(spec, value)
            from_binary(spec.kind, stored)
        except PackError as e:
            raise ChainError(str(e)) from e
        resolved[key] = value
    return resolved


def spec_to_stored(spec, value) -> str:
    """The pack's human→stored conversion, including its range check."""
    from packs.loader import load_pack

    return load_pack(PACK_ID).to_stored(spec, value, warnings=[])


# --- the blocks -------------------------------------------------------------


def _db_to_gain(db: float) -> float:
    return float(10.0 ** (float(db) / 20.0))


def _peaking(centre: float, gain_db: float, q: float, sample_rate: int):
    """One peaking-EQ biquad, as second-order sections."""
    import numpy as np

    if abs(gain_db) < 1e-9:
        return None
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * np.pi * min(centre, sample_rate * 0.49) / sample_rate
    alpha = np.sin(w0) / (2.0 * q)
    cos_w0 = np.cos(w0)
    b = [1 + alpha * A, -2 * cos_w0, 1 - alpha * A]
    a = [1 + alpha / A, -2 * cos_w0, 1 - alpha / A]
    return np.array([[b[0] / a[0], b[1] / a[0], b[2] / a[0],
                      1.0, a[1] / a[0], a[2] / a[0]]])


def _envelope_db(mono, sample_rate: int, attack_ms: float, release_ms: float):
    """A one-pole level follower, in dB — the input to the gate and compressor."""
    import numpy as np
    from scipy import signal

    rectified = np.abs(mono)
    # A single smoothing coefficient per direction, applied with lfilter rather
    # than a Python loop: a sample-accurate two-coefficient follower would cost
    # more than the whole rest of the chain.
    attack = float(np.exp(-1.0 / max(1e-6, attack_ms * 1e-3 * sample_rate)))
    release = float(np.exp(-1.0 / max(1e-6, release_ms * 1e-3 * sample_rate)))
    fast = signal.lfilter([1 - attack], [1, -attack], rectified)
    slow = signal.lfilter([1 - release], [1, -release], rectified)
    level = np.maximum(fast, slow)
    return 20.0 * np.log10(np.maximum(level, 1e-9))


def _gate(mono, sample_rate: int, threshold_db: float):
    """Open above the threshold, closed below, with a smoothed edge."""
    import numpy as np
    from scipy import signal

    level_db = _envelope_db(mono, sample_rate, 1.0, 60.0)
    open_mask = (level_db > threshold_db).astype(np.float64)
    # Smooth the mask so closing does not click, which would put broadband energy
    # into the spectrum and be measured as part of the tone.
    taps = max(1, int(0.005 * sample_rate))
    smoothed = signal.lfilter(np.ones(taps) / taps, [1.0], open_mask)
    return mono * smoothed


def _compressor(mono, sample_rate: int, compression: float, makeup: float, mix: float):
    """Downward compression with a soft knee, mixed back against the input.

    `compression` is the manifest's single knob, so threshold and ratio both move
    with it — which is what a one-knob compressor does.
    """
    import numpy as np

    amount = float(compression) / 100.0
    if amount <= 0.0:
        return mono
    threshold_db = -6.0 - 30.0 * amount
    ratio = 1.0 + 7.0 * amount

    # The attack has to be fast enough to catch a pluck transient. At 5 ms it was
    # not: the peaks escaped compression entirely while the sustain was ducked and
    # the makeup gain lifted everything, so turning the knob up *raised* the crest
    # factor from 21.8 to 30.1 dB. A compressor that increases crest is measuring
    # as the opposite of itself, and the sensitivity test caught it.
    level_db = _envelope_db(mono, sample_rate, 0.2, 120.0)
    over = np.maximum(level_db - threshold_db, 0.0)
    reduction_db = over * (1.0 - 1.0 / ratio)
    compressed = mono * (10.0 ** (-reduction_db / 20.0))
    compressed *= _db_to_gain(12.0 * amount * (float(makeup) / 100.0))

    blend = float(mix) / 100.0
    return compressed * blend + mono * (1.0 - blend)


def _drive(mono, drive: float, level: float, tone: float, sample_rate: int):
    """An overdrive pedal: a tilt filter, a waveshaper, and a level control."""
    import numpy as np
    from scipy import signal

    shaped = mono
    tilt_db = (float(tone) - 50.0) / 50.0 * 9.0
    sos = _peaking(2200.0, tilt_db, 0.7, sample_rate)
    if sos is not None:
        shaped = signal.sosfilt(sos, shaped)

    gain = 1.0 + 40.0 * (float(drive) / 100.0) ** 2
    driven = np.tanh(shaped * gain) / np.tanh(gain) if gain > 0 else shaped
    return driven * _db_to_gain(-12.0 + 24.0 * float(level) / 100.0)


def _tone_stack(mono, sample_rate: int, bass: float, mid: float, treble: float,
                bright: bool):
    """Three interacting bands, the way an amp's tone controls are arranged."""
    from scipy import signal

    out = mono
    for centre, value, q in ((100.0, bass, 0.7), (700.0, mid, 0.9), (3200.0, treble, 0.7)):
        sos = _peaking(centre, (float(value) - 50.0) / 50.0 * 12.0, q, sample_rate)
        if sos is not None:
            out = signal.sosfilt(sos, out)
    if bright:
        sos = _peaking(5000.0, 6.0, 0.8, sample_rate)
        if sos is not None:
            out = signal.sosfilt(sos, out)
    return out


def _graphic_eq(mono, sample_rate: int, centres, gains_db):
    """The nine fixed-centre bands the plan inverts analytically.

    Q is chosen so neighbouring third-octave-ish bands overlap the way a graphic
    equaliser's do; `match/invert.py` measures the real basis rather than assuming
    this one.
    """
    from scipy import signal

    out = mono
    for centre, gain_db in zip(centres, gains_db):
        sos = _peaking(float(centre), float(gain_db), 1.1, sample_rate)
        if sos is not None:
            out = signal.sosfilt(sos, out)
    return out


def _filters(mono, sample_rate: int, hpf_hz: float, lpf_hz: float):
    from scipy import signal

    out = mono
    nyquist = sample_rate / 2.0
    if hpf_hz > 20.0:
        sos = signal.butter(2, min(hpf_hz, nyquist * 0.99), "high", fs=sample_rate, output="sos")
        out = signal.sosfilt(sos, out)
    if lpf_hz < nyquist * 0.98:
        sos = signal.butter(2, min(lpf_hz, nyquist * 0.99), "low", fs=sample_rate, output="sos")
        out = signal.sosfilt(sos, out)
    return out


def _power_amp(mono, volume: float):
    """Output-stage saturation: how hard it is driven is the volume control."""
    import numpy as np

    gain = 1.0 + 8.0 * (float(volume) / 100.0) ** 2
    return np.tanh(mono * gain) / np.tanh(gain)


@lru_cache(maxsize=64)
def _cab_ir(sample_rate: int, position: float, taps: int = 512):
    """A speaker-cabinet impulse response: a bandpass with a couple of resonances.

    `position` moves the mic from centre to edge, which on a real cabinet trades
    high end for low mids — the direction M0 measured on `*CabPosition`.
    """
    import numpy as np
    from scipy import signal

    rng = np.random.default_rng(20260805)   # fixed: the cab is not a variable
    impulse = np.zeros(taps)
    impulse[0] = 1.0
    # A short noisy tail gives the response some texture without making it a room.
    impulse[1:64] += rng.standard_normal(63) * 0.08 * np.exp(-np.arange(63) / 18.0)

    edge = float(position)
    top = 3500.0 + 3000.0 * (1.0 - edge)
    sos = signal.butter(2, [80.0, min(top, sample_rate * 0.45)], "band",
                        fs=sample_rate, output="sos")
    ir = signal.sosfilt(sos, impulse)
    for centre, gain_db in ((1800.0, 4.0 * (1.0 - edge)), (450.0, 3.0 * edge)):
        peak = _peaking(centre, gain_db, 1.4, sample_rate)
        if peak is not None:
            ir = signal.sosfilt(peak, ir)
    norm = np.sqrt((ir**2).sum())
    return ir / norm if norm > 0 else ir


def _delay(mono, sample_rate: int, time_ms: float, feedback: float, mix: float,
           low_cut: float, high_cut: float):
    """A feedback delay, as a sum of decaying taps rather than a sample loop.

    An IIR feedback line is a per-sample recursion, which in Python costs more
    than every filter in this chain put together. `g**k` at successive multiples
    of the delay is the same signal to within the tail that is truncated once the
    repeat is 60 dB down.
    """
    import numpy as np
    from scipy import signal

    blend = float(mix) / 100.0
    if blend <= 0.0:
        return mono
    step = max(1, int(round(float(time_ms) * 1e-3 * sample_rate)))
    g = min(max(float(feedback) / 100.0, 0.0), 0.95)

    wet = np.zeros_like(mono)
    for k in range(1, 33):
        amplitude = g ** (k - 1)
        offset = step * k
        if amplitude < 1e-3 or offset >= len(mono):
            break
        wet[offset:] += mono[: len(mono) - offset] * amplitude

    nyquist = sample_rate / 2.0
    sos = signal.butter(1, [max(20.0, low_cut), min(high_cut, nyquist * 0.99)],
                        "band", fs=sample_rate, output="sos")
    wet = signal.sosfilt(sos, wet)
    return mono + wet * blend


@lru_cache(maxsize=64)
def _reverb_tail(sample_rate: int, rt60: float, low_cut: float, high_cut: float,
                 length: int):
    """The reverb's impulse response. Cached: it is a pure function of these five
    numbers, and regenerating 96,000 filtered samples per render was most of the
    cost of having a reverb at all."""
    import numpy as np
    from scipy import signal

    rng = np.random.default_rng(20260806)
    t = np.arange(length) / sample_rate
    tail = rng.standard_normal(length) * 10.0 ** (-3.0 * t / rt60)

    nyquist = sample_rate / 2.0
    sos = signal.butter(1, [max(20.0, low_cut), min(high_cut, nyquist * 0.99)],
                        "band", fs=sample_rate, output="sos")
    tail = signal.sosfilt(sos, tail)
    norm = np.sqrt((tail**2).sum())
    tail = tail / norm if norm > 0 else tail
    tail.setflags(write=False)   # shared between renders; never mutated in place
    return tail


def _reverb(mono, sample_rate: int, decay_s: float, predelay_ms: float, mix: float,
            low_cut: float, high_cut: float):
    """Exponentially decaying filtered noise, convolved.

    The decay is set so `decay_s` *is* the RT60, which is what makes the
    synthetic chain a ground truth for the reverb estimator.
    """
    import numpy as np
    from scipy import signal

    blend = float(mix) / 100.0
    if blend <= 0.0:
        return mono

    rt60 = float(decay_s)
    # Tail samples beyond the end of the signal cannot reach the output, which is
    # truncated to the input length — so generating them is pure cost. Capping
    # here is exact, not an approximation.
    length = min(int(min(rt60, 4.0) * sample_rate), len(mono))
    if length < 16:
        return mono
    tail = _reverb_tail(sample_rate, rt60, float(low_cut), float(high_cut), length)

    # Overlap-add rather than a single FFT: the tail is as long as the signal, so
    # one transform over their sum is markedly slower than blocking it.
    wet = signal.oaconvolve(mono, tail, mode="full")[: len(mono)]
    offset = int(float(predelay_ms) * 1e-3 * sample_rate)
    if offset > 0:
        wet = np.concatenate([np.zeros(min(offset, len(wet))), wet])[: len(mono)]
    return mono * (1.0 - blend * 0.3) + wet * blend


# --- the chain --------------------------------------------------------------


def render(di, settings: Optional[Mapping] = None, sample_rate: int = SAMPLE_RATE):
    """Run a DI through the chain and return stereo float32, shape (frames, 2).

    Deterministic: the cab and reverb draw from fixed seeds, so the same
    parameters and the same input give bit-identical output. The real plugin does
    not do that (see §11 of the plan), which is exactly why known-answer work
    belongs here.
    """
    require("synthetic rendering")
    import numpy as np

    values = resolve(settings)
    specs = parameter_specs()
    centres = [float(specs[(f"{AMP}EQ", band)].centre_hz) for band in EQ_BANDS]

    def value(module, key):
        return values[(module, key)]

    signal_1d = np.asarray(di, dtype=np.float64)
    if signal_1d.ndim > 1:
        signal_1d = signal_1d.mean(axis=1)

    out = signal_1d * _db_to_gain(value("parameters", "inputGain"))

    if value("parameters", "gateActive"):
        out = _gate(out, sample_rate, float(value("parameters", "gateThreshold")))

    if value("compressor", "compressorActive"):
        out = _compressor(out, sample_rate,
                          value("compressor", "compressorCompression"),
                          value("compressor", "compressorLevel"),
                          value("compressor", "compressorMix"))

    if value("drive1", "drive1Active"):
        out = _drive(out, value("drive1", "drive1Drive"), value("drive1", "drive1Level"),
                     value("drive1", "drive1Tone"), sample_rate)

    out = _tone_stack(out, sample_rate,
                      value("sw50rAmp", "sw50rBass"), value("sw50rAmp", "sw50rMid"),
                      value("sw50rAmp", "sw50rTreble"), bool(value("sw50rAmp", "sw50rBright")))

    if value(f"{AMP}EQ", f"{AMP}EQActive"):
        gains = [float(value(f"{AMP}EQ", band)) for band in EQ_BANDS]
        out = _graphic_eq(out, sample_rate, centres, gains)

    out = _filters(out, sample_rate,
                   float(value(f"{AMP}EQ", f"{AMP}EQHpf")),
                   float(value(f"{AMP}EQ", f"{AMP}EQLpf")))

    out = _power_amp(out, value("sw50rAmp", "sw50rVolume"))
    out = out * _db_to_gain(-12.0 + 24.0 * float(value("sw50rAmp", "sw50rLevel")) / 100.0)

    if value("cabParameters", "leftCabActive"):
        from scipy import signal as scipy_signal

        ir = _cab_ir(sample_rate, float(value("cabParameters", "leftCabPosition")))
        out = scipy_signal.fftconvolve(out, ir, mode="full")[: len(signal_1d)]
        out = out * _db_to_gain(value("cabParameters", "leftCabMicLevel"))

    if value("delay", "delayActive"):
        out = _delay(out, sample_rate, float(value("delay", "delayTime")),
                     value("delay", "delayFeedback"), value("delay", "delayMix"),
                     float(value("delay", "delayLowCut")),
                     float(value("delay", "delayHighCut")))

    if value("reverb", "reverbActive"):
        out = _reverb(out, sample_rate, float(value("reverb", "reverbDecay")),
                      float(value("reverb", "reverbPreDelay")),
                      value("reverb", "reverbMix"),
                      float(value("reverb", "reverbLowCut")),
                      float(value("reverb", "reverbHighCut")))

    out = out * _db_to_gain(value("parameters", "outputGain"))
    return np.column_stack([out, out]).astype(np.float32)


def to_spec(settings: Optional[Mapping] = None, name: str = "Synthetic") -> Dict[str, Any]:
    """The same values as a spec `apply_spec.py` accepts.

    The one direction that matters for keeping the synthetic chain and the real
    preset writer from drifting: whatever drove a render can be written to a file
    without restating any value.
    """
    values = resolve(settings)
    return {
        "name": name,
        "parameters": [
            {"module": module, "key": key, "value": value}
            for (module, key), value in values.items()
        ],
    }
