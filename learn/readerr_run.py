"""The note-reading diagnosis's transcriber runner (plan `note-reading-diagnosis`, unit U2; ledger
`phase_scratch_readerr`). Called only by `learn/scratch_readerr.py`, inside the transcriber's own venv, as

    <venv>/bin/python -I learn/readerr_run.py MODE --spec JSON in1.wav out1.json [in2.wav out2.json ...]

The pattern is `learn/bp_run.py`'s: the module level is the standard library only (it runs under `-I`, so it imports
nothing from this repository either), every heavy import sits inside a mode function, Python 3.9 syntax. Several pairs
run in one process with the model loaded once.

**Modes.** `bp-grid` and `bp-shift` run Basic Pitch (ONNX on the CPU, as in `bp_run.py`); `mt3` and `kong` are torch
transcribers (YourMT3+ or MR-MT3, and the Kong-style guitar models), whose model calls are stubs in this unit: the
checkpoint is checked and loaded, then the run refuses as not wired.

**The spec** (one JSON object; unknown keys refuse):
- every mode: `model` (the pinned model or checkpoint path), `model_sha256` (its expected sha256; a missing file or
  another hash refuses before anything loads), `threads` (default 1, at most 2), `lead_in_s` (default 0);
- `bp-grid`: `settings` (exactly `bp_run.SETTING_KEYS`, the base point) and `grid` ({axis: [values]} over
  `GRID_KEYS`; an axis left out holds the base value);
- `bp-shift`: `settings` and `offsets_s` ([seconds >= 0], no repeats);
- `mt3`, `kong`: `options` (a free object, passed to the model call).

**Output**, one JSON per pair: `{mode, versions, model_sha256, threads, spec, input_sha256, seconds, events}`, events
`[{on, off, pitch, amp, bends}]` with times in seconds on the input file's own timeline. `bp-grid` adds
`grid: [{settings, events}]`, every grid point from one inference in the same process (product order over
`GRID_KEYS`); its top-level `events` is the read at `settings`. `bp-shift` adds `shifts: [{offset_s, pad_samples,
events}]`, one inference per offset on the input with that many seconds of leading zeros; its top-level `events` is the
zero-offset read when 0 is listed, else empty.

**Re-basing.** A lead-in prepends `lead_in_s` of zeros; a shift prepends `offset_s` more. The pad is whole samples at
the input's own rate (`pad_samples`), and the runner subtracts that pad (`pad_samples / sr`, within half a sample of
the seconds asked) from every event. Events that end at or before 0 are dropped; onsets below 0 are clipped to 0 (the
bend track is kept as read). With no pad the input file itself is read, exactly as `bp_run.py` reads it.
"""

import hashlib
import itertools
import json
import math
import os
import sys
import time

MODES = ("bp-grid", "bp-shift", "mt3", "kong")
BP_MODES = ("bp-grid", "bp-shift")
TORCH_MODES = ("mt3", "kong")
PROVIDERS = ["CPUExecutionProvider"]
SETTING_KEYS = ("onset_threshold", "frame_threshold", "minimum_note_length", "minimum_frequency",
                "maximum_frequency", "melodia_trick", "multiple_pitch_bends")      # bp_run.SETTING_KEYS
GRID_KEYS = ("onset_threshold", "frame_threshold", "minimum_note_length", "melodia_trick")
DEFAULT_THREADS = 1
MAX_THREADS = 2
COMMON_KEYS = ("model", "model_sha256", "threads", "lead_in_s")
MODE_KEYS = {"bp-grid": ("settings", "grid"), "bp-shift": ("settings", "offsets_s"),
             "mt3": ("options",), "kong": ("options",)}
REQUIRED = {"bp-grid": ("model", "model_sha256", "settings", "grid"),
            "bp-shift": ("model", "model_sha256", "settings", "offsets_s"),
            "mt3": ("model", "model_sha256"), "kong": ("model", "model_sha256")}
THREAD_ENV = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
              "NUMEXPR_NUM_THREADS")
OFFLINE_ENV = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1"}


def refuse(msg):
    raise SystemExit(f"readerr_run: {msg}")


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def event_record(ev):
    """(Pure.) One note event (start s, end s, MIDI pitch, amplitude, bends or None) as stored, as `bp_run.py` stores
    it: times to 0.1 ms, the amplitude to 1e-6, the bend track as ints."""
    start, end, pitch, amp, bends = ev
    return {"on": round(float(start), 4), "off": round(float(end), 4), "pitch": int(pitch),
            "amp": round(float(amp), 6), "bends": [int(b) for b in bends] if bends is not None else []}


# --- the arguments ----------------------------------------------------------------------------------------------------------

def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def check_spec(mode, spec):
    """(Pure.) Refuses a spec that is not exactly what `mode` takes. -> the spec, unchanged."""
    if not isinstance(spec, dict):
        refuse("the spec must be a JSON object")
    allowed = set(COMMON_KEYS) | set(MODE_KEYS[mode])
    extra = sorted(set(spec) - allowed)
    if extra:
        refuse(f"{mode} takes no {extra}; it takes {sorted(allowed)}")
    missing = [k for k in REQUIRED[mode] if k not in spec]
    if missing:
        refuse(f"{mode} needs {missing}")
    if not isinstance(spec["model"], str) or not spec["model"]:
        refuse("model must be a path")
    sha = spec["model_sha256"]
    if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        refuse("model_sha256 must be 64 lower-case hex digits")
    t = spec.get("threads", DEFAULT_THREADS)
    if not isinstance(t, int) or isinstance(t, bool) or not 1 <= t <= MAX_THREADS:
        refuse(f"threads must be an integer from 1 to {MAX_THREADS}")
    lead = spec.get("lead_in_s", 0)
    if not _number(lead) or lead < 0:
        refuse("lead_in_s must be a number >= 0")
    if "settings" in spec:
        s = spec["settings"]
        if not isinstance(s, dict) or sorted(s) != sorted(SETTING_KEYS):
            refuse(f"settings must be exactly {sorted(SETTING_KEYS)}")
    if "grid" in spec:
        g = spec["grid"]
        if not isinstance(g, dict) or not g:
            refuse(f"grid must be a non-empty object over {list(GRID_KEYS)}")
        bad = sorted(set(g) - set(GRID_KEYS))
        if bad:
            refuse(f"grid axes {bad} are not among {list(GRID_KEYS)}")
        for k, vals in g.items():
            if not isinstance(vals, list) or not vals:
                refuse(f"grid axis {k} must be a non-empty list")
            ok = (lambda v: isinstance(v, bool)) if k == "melodia_trick" else (lambda v: _number(v) and v >= 0)
            if not all(ok(v) for v in vals):
                refuse(f"grid axis {k} holds a value of the wrong kind")
            if len(set(vals)) != len(vals):
                refuse(f"grid axis {k} repeats a value")
    if "offsets_s" in spec:
        o = spec["offsets_s"]
        if not isinstance(o, list) or not o or not all(_number(v) and v >= 0 for v in o):
            refuse("offsets_s must be a non-empty list of seconds >= 0")
        if len(set(o)) != len(o):
            refuse("offsets_s repeats an offset")
    if "options" in spec and not isinstance(spec["options"], dict):
        refuse("options must be an object")
    return spec


def parse_args(argv):
    """(Pure.) MODE --spec JSON in out [in out ...] -> (mode, spec, [(in, out)]). Refuses an unknown mode, a missing or
    bad spec, an odd or empty pair list, and an output named as its own input."""
    if not argv or argv[0] not in MODES:
        refuse(f"the first argument is the mode, one of {list(MODES)}")
    mode, spec, rest, i = argv[0], None, [], 1
    while i < len(argv):
        a = argv[i]
        if a == "--spec":
            if i + 1 >= len(argv):
                refuse("--spec needs a JSON value")
            try:
                spec = json.loads(argv[i + 1])
            except ValueError as e:
                refuse(f"--spec is not JSON ({e})")
            i += 2
        else:
            rest.append(a)
            i += 1
    if spec is None:
        refuse("--spec is required")
    check_spec(mode, spec)
    if not rest or len(rest) % 2:
        refuse("give input and output files in pairs")
    pairs = list(zip(rest[::2], rest[1::2]))
    for src, dst in pairs:
        if os.path.abspath(src) == os.path.abspath(dst):
            refuse("an output may not be its own input")
    return mode, spec, pairs


def threads_of(spec):
    return spec.get("threads", DEFAULT_THREADS)


# --- the grid, the pad and the re-basing (pure) ------------------------------------------------------------------------------

def grid_points(settings, grid):
    """(Pure.) Every grid point as a full settings dict: the product over `GRID_KEYS` in that order (the first axis
    outermost), each axis left out of `grid` holding the base value."""
    axes = [grid.get(k, [settings[k]]) for k in GRID_KEYS]
    out = []
    for combo in itertools.product(*axes):
        p = dict(settings)
        p.update(zip(GRID_KEYS, combo))
        out.append(p)
    return out


def pad_samples(pad_s, sr):
    """(Pure.) Seconds of leading zeros -> whole samples at the input's rate."""
    return int(round(pad_s * sr))


def rebase(events, shift_s):
    """(Pure.) Raw events (start, end, pitch, amp, bends) read on a padded input -> the same on the input's own
    timeline: `shift_s` subtracted, events ending at or before 0 dropped, onsets below 0 clipped to 0, the bend track
    kept as read."""
    out = []
    for start, end, pitch, amp, bends in events:
        on, off = float(start) - shift_s, float(end) - shift_s
        if off <= 0:
            continue
        out.append((max(on, 0.0), off, pitch, amp, bends))
    return out


def grid_output(settings, grid, notes_at):
    """(Pure given `notes_at`.) `notes_at(settings) -> [raw event]` on one inference already rebased -> (the base
    point's event records, [{settings, events}] over `grid_points`)."""
    base = [event_record(e) for e in notes_at(dict(settings))]
    rows = [{"settings": p, "events": [event_record(e) for e in notes_at(p)]} for p in grid_points(settings, grid)]
    return base, rows


def shift_output(offsets_s, lead_in_s, sr, read_padded):
    """(Pure given `read_padded`.) `read_padded(n_samples) -> [raw event]` on the input with n leading zero samples ->
    (the zero-offset read's records or [], [{offset_s, pad_samples, events}] in the order given), each read re-based
    by its own pad."""
    shifts, top = [], []
    for off in offsets_s:
        n = pad_samples(lead_in_s + off, sr)
        recs = [event_record(e) for e in rebase(read_padded(n), n / sr)]
        shifts.append({"offset_s": off, "pad_samples": n, "events": recs})
        if off == 0:
            top = recs
    return top, shifts


# --- the model file -------------------------------------------------------------------------------------------------------

def checked_model(path, sha):
    """The pinned model or checkpoint, refused unless the file is there and has `sha` (nothing is ever fetched).
    -> its sha256."""
    if not os.path.isfile(path):
        refuse(f"no model file at the pinned path {path} (nothing is fetched at run time)")
    got = file_sha(path)
    if got != sha:
        refuse(f"the model file's sha256 is {got}, not the pinned {sha}")
    return got


def cap_threads(threads):
    """Caps the numeric libraries' threads and forbids hub fetches, before any heavy import."""
    for k in THREAD_ENV:
        os.environ[k] = str(threads)
    os.environ.update(OFFLINE_ENV)


# --- Basic Pitch ------------------------------------------------------------------------------------------------------------

def _input_rate(src):
    import soundfile as sf

    return sf.info(src).samplerate


def _padded(src, n, workdir):
    """The input with n leading zero samples at its own rate, as a float wav in `workdir`; the input itself when n is
    0."""
    if n == 0:
        return src
    import numpy as np
    import soundfile as sf

    x, sr = sf.read(src, dtype="float32", always_2d=True)
    y = np.concatenate([np.zeros((n, x.shape[1]), dtype=np.float32), x])
    p = os.path.join(workdir, f"pad-{n}.wav")
    sf.write(p, y, sr, subtype="FLOAT")
    return p


class BasicPitch:
    """Basic Pitch's ONNX model on the CPU with capped threads, as `bp_run.py` builds it."""

    def __init__(self, model_path, threads):
        import basic_pitch                                   # the venv's only: never imported in the main .venv or CI
        import librosa
        import numpy as np
        import onnxruntime as ort
        from basic_pitch.inference import Model

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads
        opts.inter_op_num_threads = threads
        model = Model(model_path)
        if model.model_type != Model.MODEL_TYPES.ONNX:
            refuse(f"the model loaded as {model.model_type}, not ONNX")
        model.model = ort.InferenceSession(str(model_path), sess_options=opts, providers=PROVIDERS)
        got = list(model.model.get_providers())
        if got != PROVIDERS:
            refuse(f"providers {got}, not {PROVIDERS}")
        self.model = model
        self.versions = {"basic_pitch": getattr(basic_pitch, "__version__", None), "onnxruntime": ort.__version__,
                         "numpy": np.__version__, "librosa": librosa.__version__,
                         "python": sys.version.split()[0], "providers": got}

    def infer(self, path):
        """One inference -> the model output (note, onset, contour), as `predict` makes it."""
        from basic_pitch.inference import run_inference

        return run_inference(path, self.model)

    @staticmethod
    def notes(output, settings):
        """The model output -> raw note events at `settings`, as `predict` makes them (on a copy of the output)."""
        import numpy as np
        import basic_pitch.note_creation as infer
        from basic_pitch.constants import AUDIO_SAMPLE_RATE, FFT_HOP

        out = {k: np.array(v, copy=True) for k, v in output.items()}
        min_len = int(np.round(settings["minimum_note_length"] / 1000 * (AUDIO_SAMPLE_RATE / FFT_HOP)))
        _, events = infer.model_output_to_notes(
            out, onset_thresh=settings["onset_threshold"], frame_thresh=settings["frame_threshold"],
            min_note_len=min_len, min_freq=settings["minimum_frequency"], max_freq=settings["maximum_frequency"],
            multiple_pitch_bends=settings["multiple_pitch_bends"], melodia_trick=settings["melodia_trick"],
            midi_tempo=120)
        return events


def run_bp_grid(bp, spec, src, workdir):
    sr = _input_rate(src)
    n = pad_samples(spec.get("lead_in_s", 0), sr)
    output = bp.infer(_padded(src, n, workdir))
    base, rows = grid_output(spec["settings"], spec["grid"], lambda s: rebase(bp.notes(output, s), n / sr))
    return {"events": base, "grid": rows}


def run_bp_shift(bp, spec, src, workdir):
    sr = _input_rate(src)

    def read_padded(n):
        return bp.notes(bp.infer(_padded(src, n, workdir)), spec["settings"])

    top, shifts = shift_output(spec["offsets_s"], spec.get("lead_in_s", 0), sr, read_padded)
    return {"events": top, "shifts": shifts}


# --- the torch transcribers (stubs) -----------------------------------------------------------------------------------------

def load_checkpoint(path, threads):
    """The checked checkpoint, loaded on the CPU with `weights_only=True` (a pickle of anything but tensors and plain
    containers refuses). -> (state, versions)."""
    import torch

    torch.set_num_threads(threads)
    if torch.get_num_interop_threads() != threads:        # settable once per process, before any parallel work
        try:
            torch.set_num_interop_threads(threads)
        except RuntimeError:
            refuse(f"torch's inter-op threads are already {torch.get_num_interop_threads()}, not {threads}")
    try:
        state = torch.load(path, map_location="cpu", weights_only=True)
    except Exception as e:                                # torch raises UnpicklingError or RuntimeError here
        refuse(f"the checkpoint does not load with weights_only=True ({type(e).__name__})")
    return state, {"torch": torch.__version__, "python": sys.version.split()[0]}


def transcribe_mt3(state, src, spec):
    refuse("mt3: the model call is not wired yet (stub)")


def transcribe_kong(state, src, spec):
    refuse("kong: the model call is not wired yet (stub)")


TRANSCRIBE = {"mt3": transcribe_mt3, "kong": transcribe_kong}


# --- main -------------------------------------------------------------------------------------------------------------------

def write_json(dst, out):
    tmp = f"{dst}.part"
    with open(tmp, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    os.replace(tmp, dst)


def main(argv=None):
    mode, spec, pairs = parse_args(sys.argv[1:] if argv is None else argv)
    threads = threads_of(spec)
    model_sha = checked_model(spec["model"], spec["model_sha256"])     # before any heavy import or load
    for src, _ in pairs:
        if not os.path.isfile(src):
            refuse(f"no input at {src}")
    cap_threads(threads)
    import tempfile

    if mode in BP_MODES:
        bp = BasicPitch(spec["model"], threads)
        versions, run = bp.versions, (run_bp_grid if mode == "bp-grid" else run_bp_shift)
    else:
        state, versions = load_checkpoint(spec["model"], threads)
        bp, run = None, None
    for src, dst in pairs:
        t0 = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="readerr-") as workdir:
            body = run(bp, spec, src, workdir) if bp is not None else TRANSCRIBE[mode](state, src, spec)
        out = {"mode": mode, "versions": versions, "model_sha256": model_sha, "threads": threads, "spec": spec,
               "input_sha256": file_sha(src), "seconds": round(time.perf_counter() - t0, 3)}
        out.update(body)
        write_json(dst, out)
        print(f"readerr_run: {mode} {len(out['events'])} notes -> {dst}", flush=True)


if __name__ == "__main__":
    main()
