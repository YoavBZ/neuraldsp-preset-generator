"""The note-reading diagnosis's transcriber runner (plan `note-reading-diagnosis`, unit U2; ledger
`phase_scratch_readerr`). Called only by `learn/scratch_readerr.py`, inside the transcriber's own venv, as

    <venv>/bin/python -I learn/readerr_run.py MODE --spec JSON in1.wav out1.json [in2.wav out2.json ...]

The pattern is `learn/bp_run.py`'s: the module level is the standard library only (it runs under `-I`, so it imports
nothing from this repository either), every heavy import sits inside a mode function, Python 3.9 syntax. Several pairs
run in one process with the model loaded once.

**Modes.** `bp-grid` and `bp-shift` run Basic Pitch (ONNX on the CPU, as in `bp_run.py`). `mt3` runs YourMT3+
`YPTF.MoE+Multi (noPS)` through `mt3-infer` 0.2.0, and `kong` runs Riley's guitar models (`guitar-fl`, `guitar-gaps`)
through the `piano_transcription_inference` fork at `cfe28ed`, both on the CPU (Phase 2b amendment, unit D). Each
tool's upstream calls sit in one adapter class (`Mt3Adapter`, `KongAdapter`), written from the pinned code read at
its commit and marked "to confirm on install".

**The spec** (one JSON object; unknown keys refuse):
- every mode: `model` (the pinned model or checkpoint path), `model_sha256` (its expected sha256; a missing file or
  another hash refuses before anything loads), `threads` (default 1, at most 2), `lead_in_s` (default 0);
- `bp-grid`: `settings` (exactly `bp_run.SETTING_KEYS`, the base point) and `grid` ({axis: [values]} over
  `GRID_KEYS`; an axis left out holds the base value);
- `bp-shift`: `settings` and `offsets_s` ([seconds >= 0], no repeats);
- `mt3`: `options` {programs} (one of `MT3_PROGRAMS`); `kong`: `options` {onset_threshold, frame_threshold}, each one
  of `KONG_GRID`'s declared values (4 onset x 3 frame, amendment 5's grid; the shipped point is `KONG_SHIPPED`);
- `mt3`, `kong`: `allow_globals` (required: the manifest's pickle globals for this checkpoint, "module.name") and an
  optional `grid` {axis: [values]} over the mode's own axes, values among the declared ones.

**Output**, one JSON per pair: `{mode, versions, model_sha256, threads, spec, input_sha256, seconds, events}`, events
`[{on, off, pitch, amp, bends}]` with times in seconds on the input file's own timeline. `bp-grid` adds
`grid: [{settings, events}]`, every grid point from one inference in the same process (product order over
`GRID_KEYS`); its top-level `events` is the read at `settings`. `bp-shift` adds `shifts: [{offset_s, pad_samples,
events}]`, one inference per offset on the input with that many seconds of leading zeros; its top-level `events` is the
zero-offset read when 0 is listed, else empty. `mt3` and `kong` add `grid: [{options, events}]` when the spec has a
grid (one inference; top-level `events` is the read at `options`), and always `scan` ({pickle member: [globals]}),
`load_report` ([{module, missing, unexpected}], one per `load_state_dict`) and `guards` (what is refused).
`mt3` has no loudness (amp 1.0) and `kong` amp is velocity / 127; neither has bends ([]).

**The torch modes' safety** (review amendment 7), in this order, before any model code runs:
1. the sha256 check; then the pickle scan (`scan_checkpoint`, standard library): every `.pkl` member of the zip
   checkpoint, every GLOBAL, INST and STACK_GLOBAL resolved, memo included; anything it cannot resolve refuses, and so
   does any global on `DENY_NAMES` / `DENY_MODULES` or outside `allow_globals`. The allowlist and the scan are printed;
2. the thread cap and the offline variables; then the network and process refusals (`install_refusals`): socket
   connect, `os.system`, `os.popen`, `os.exec*`, `os.spawn*`, `os.posix_spawn*`, `subprocess` and `_posixsubprocess`;
3. torch is imported and every `torch.load` goes through `GuardedLoad`: only the pinned path (a file object it did not
   open itself refuses), re-hashed and re-scanned on the handle it loads from, `weights_only=True` forced, exactly the
   allowlisted globals made safe; `load_state_dict` is reported (missing and unexpected keys) and a missing key refuses;
4. only then is the tool's own code imported.

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
             "mt3": ("options", "grid", "allow_globals"), "kong": ("options", "grid", "allow_globals")}
REQUIRED = {"bp-grid": ("model", "model_sha256", "settings", "grid"),
            "bp-shift": ("model", "model_sha256", "settings", "offsets_s"),
            "mt3": ("model", "model_sha256", "options", "allow_globals"),
            "kong": ("model", "model_sha256", "options", "allow_globals")}
THREAD_ENV = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
              "NUMEXPR_NUM_THREADS")
OFFLINE_ENV = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1"}

# --- the torch modes' declared options (Phase 2b amendment; review amendment 5) ---------------------------------------
MT3_PROGRAMS = ("pitched", "guitar")     # every pitched (non-drum) program, or the GM guitar programs only
GUITAR_PROGRAMS = tuple(range(24, 32))   # GM 25-32 (0-based 24-31): the guitars
MT3_SHIPPED = {"programs": "pitched"}
MT3_MODEL_KEY = "yptf_moe_nops"          # mt3-infer's key for YPTF.MoE+Multi (noPS); picked from the pinned path
MT3_GLOBAL_ALIASES = {"utils": "mt3_infer.models.yourmt3.utils"}   # the checkpoint's pre-refactor module path
KONG_GRID = {"onset_threshold": (0.2, 0.3, 0.4, 0.5), "frame_threshold": (0.1, 0.2, 0.3)}
KONG_SHIPPED = {"onset_threshold": 0.3, "frame_threshold": 0.1}    # the fork's PianoTranscription at cfe28ed
KONG_FIXED = {"offset_threshold": 0.3, "pedal_offset_threshold": 0.2}   # the fork's own, never varied
KONG_MODEL_TYPE = "Regress_onset_offset_frame_velocity_CRNN"       # hf_midi_transcription's choice for non-piano
KONG_FORK_COMMIT = "cfe28ed26be892ad7d4e8a9aadcf95cb904c9320"      # the manifest's pin; the files' sha256 recorded too
KONG_BATCH = 8                           # hf_midi_transcription's default batch size
KONG_SEGMENT_S = 10                      # hf_midi_transcription: segment_samples = 10 * sample_rate
KONG_RAW_KEYS = ("reg_onset_output", "reg_offset_output", "frame_output", "velocity_output")
TORCH_AXES = {"mt3": {"programs": MT3_PROGRAMS}, "kong": KONG_GRID}
TORCH_ALIASES = {"mt3": MT3_GLOBAL_ALIASES, "kong": {}}

# --- the pickle scan's fixed denylist (review amendment 7) ------------------------------------------------------------
DENY_NAMES = tuple(f"{m}.{n}" for m in ("builtins", "__builtin__")
                   for n in ("eval", "exec", "compile", "getattr", "__import__", "open", "setattr", "delattr",
                             "globals", "breakpoint"))
DENY_MODULES = ("os", "posix", "nt", "subprocess", "sys", "importlib", "runpy", "socket", "shutil", "pickle", "_pickle",
                "marshal", "_posixsubprocess", "ctypes", "pty", "code",
                # Python 2 module names a protocol-2 pickle may carry (the 2026-11-26 audit)
                "commands", "cPickle", "__builtin__", "copy_reg", "cStringIO", "urllib2", "httplib",
                # the modules torch's Python 2 renames lead to (torch._utils.IMPORT_MAPPING's targets, less builtins
                # and collections, whose names are listed below), and the stdlib's for urllib2 and httplib
                "copyreg", "queue", "reprlib", "dbm", "io", "_io", "urllib", "http")
DENY_PATHS = ("collections.abc",)        # a module path denied whole (collections itself holds OrderedDict)
# torch._utils.IMPORT_MAPPING and NAME_MAPPING (torch 2.7.1 and 2.8.0 alike): torch's weights_only unpickler renames
# a Python 2 global before it looks it up (`_read_global_instruction`), so a name is denied as read and as renamed
TORCH_PY2_IMPORTS = {"__builtin__": "builtins", "copy_reg": "copyreg", "Queue": "queue", "repr": "reprlib",
                     "_abcoll": "collections.abc", "UserDict": "collections", "UserList": "collections",
                     "UserString": "collections", "whichdb": "dbm", "StringIO": "io", "cStringIO": "io"}
TORCH_PY2_NAMES = {("__builtin__", "xrange"): ("builtins", "range"), ("__builtin__", "reduce"): ("functools", "reduce"),
                   ("__builtin__", "intern"): ("sys", "intern"), ("__builtin__", "unichr"): ("builtins", "chr"),
                   ("__builtin__", "unicode"): ("builtins", "str"), ("__builtin__", "long"): ("builtins", "int"),
                   ("itertools", "izip"): ("builtins", "zip"), ("itertools", "imap"): ("builtins", "map"),
                   ("itertools", "ifilter"): ("builtins", "filter"),
                   ("itertools", "ifilterfalse"): ("itertools", "filterfalse"),
                   ("itertools", "izip_longest"): ("itertools", "zip_longest"),
                   ("UserDict", "IterableUserDict"): ("collections", "UserDict"),
                   ("UserList", "UserList"): ("collections", "UserList"),
                   ("UserString", "UserString"): ("collections", "UserString"),
                   ("__builtin__", "basestring"): ("builtins", "str"),
                   ("exceptions", "StandardError"): ("builtins", "Exception"),
                   ("UserDict", "UserDict"): ("collections", "UserDict")}
DENY_NAMES = DENY_NAMES + tuple(sorted({f"{m}.{n}" for m, n in TORCH_PY2_NAMES.values()}))   # every rename's target


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
    if "grid" in spec and mode in BP_MODES:
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
    if mode in TORCH_MODES:
        check_torch_spec(mode, spec)
    return spec


def _declared(mode, axis, v):
    vals = TORCH_AXES[mode][axis]
    if mode == "kong":
        return _number(v) and v in vals
    return isinstance(v, str) and v in vals


def check_torch_spec(mode, spec):
    """(Pure.) The torch modes' own keys: `options` exactly the mode's axes, each a declared value; `grid` (optional) a
    non-empty {axis: [values]} over those axes, declared values only, no repeats; `allow_globals` a non-empty list of
    distinct "module.name" strings, none on the denylist."""
    axes = TORCH_AXES[mode]
    o = spec["options"]
    if not isinstance(o, dict) or sorted(o) != sorted(axes):
        refuse(f"{mode} options must be exactly {sorted(axes)}")
    for k, v in o.items():
        if not _declared(mode, k, v):
            refuse(f"{mode} option {k}={v!r} is not among the declared {list(axes[k])}")
    if "grid" in spec:
        g = spec["grid"]
        if not isinstance(g, dict) or not g:
            refuse(f"{mode} grid must be a non-empty object over {sorted(axes)}")
        bad = sorted(set(g) - set(axes))
        if bad:
            refuse(f"{mode} grid axes {bad} are not among {sorted(axes)}")
        for k, vals in g.items():
            if not isinstance(vals, list) or not vals:
                refuse(f"{mode} grid axis {k} must be a non-empty list")
            if not all(_declared(mode, k, v) for v in vals):
                refuse(f"{mode} grid axis {k} holds a value outside the declared {list(axes[k])}")
            if len(set(vals)) != len(vals):
                refuse(f"{mode} grid axis {k} repeats a value")
    a = spec["allow_globals"]
    if not isinstance(a, list) or not a or not all(isinstance(n, str) and "." in n.strip(".") for n in a):
        refuse("allow_globals must be a non-empty list of 'module.name' strings")
    if len(set(a)) != len(a):
        refuse("allow_globals repeats a name")
    denied = sorted(n for n in a if denied_global(n))
    if denied:
        refuse(f"allow_globals holds denylisted globals {denied}")


def parse_args(argv):
    """(Pure.) MODE --spec JSON in out [in out ...] -> (mode, spec, [(in, out)]). Refuses an unknown mode, a missing or
    bad spec, a repeated `--spec`, an odd or empty pair list, and an output named as its own input."""
    if not argv or argv[0] not in MODES:
        refuse(f"the first argument is the mode, one of {list(MODES)}")
    mode, spec, rest, i, seen = argv[0], None, [], 1, False
    while i < len(argv):
        a = argv[i]
        if a == "--spec":
            if seen:
                refuse("give --spec once")
            seen = True
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


def torch_points(mode, options, grid):
    """(Pure.) The torch grid's points as full options dicts: the product over the mode's axes in their declared order
    (the first outermost), an axis left out of `grid` holding `options`' value."""
    keys = tuple(TORCH_AXES[mode])
    axes = [grid.get(k, [options[k]]) for k in keys]
    return [dict(zip(keys, combo)) for combo in itertools.product(*axes)]


def torch_output(mode, options, grid, notes_at):
    """(Pure given `notes_at`.) `notes_at(options) -> [raw event]` on one inference already rebased -> (the read at
    `options` as records, [{options, events}] over `torch_points`, or None without a grid)."""
    base = [event_record(e) for e in notes_at(dict(options))]
    if grid is None:
        return base, None
    rows = [{"options": p, "events": [event_record(e) for e in notes_at(p)]} for p in torch_points(mode, options, grid)]
    return base, rows


def mt3_select(notes, programs):
    """(Pure.) YourMT3+'s notes [(is_drum, program, onset, offset, pitch, velocity)] -> raw events kept by `programs`:
    every non-drum note ("pitched") or the GM guitars only ("guitar"); no loudness (amp 1.0), no bends."""
    if programs not in MT3_PROGRAMS:
        refuse(f"programs {programs!r} is not among {list(MT3_PROGRAMS)}")
    return [(on, off, pitch, 1.0, None) for is_drum, prog, on, off, pitch, _ in notes
            if not is_drum and (programs == "pitched" or prog in GUITAR_PROGRAMS)]


def kong_events(note_events):
    """(Pure.) The fork's post-processed notes [{onset_time, offset_time, midi_note, velocity}] -> raw events: amp the
    velocity / 127, no bends."""
    return [(n["onset_time"], n["offset_time"], n["midi_note"], n["velocity"] / 127.0, None) for n in note_events]


# --- the pickle scan (pure, standard library; review amendment 7) -----------------------------------------------------

_STR_OPS = ("SHORT_BINUNICODE", "BINUNICODE", "BINUNICODE8", "UNICODE", "SHORT_BINSTRING", "BINSTRING", "STRING")
_GET_OPS = ("GET", "BINGET", "LONG_BINGET")
_PUT_OPS = ("PUT", "BINPUT", "LONG_BINPUT")
_NEUTRAL_OPS = ("PROTO", "FRAME")        # touch neither the stack nor the memo
_UNKNOWN = object()                      # a stack top that is not a known string


def denied_global(name):
    """(Pure.) A "module.name" on the fixed denylist, as read or after torch's Python 2 renames: a denied name, any
    dotted part a denied module, or inside a denied module path."""
    return any(n in DENY_NAMES or any(part in DENY_MODULES for part in n.split("."))
               or any(n == d or n.startswith(d + ".") for d in DENY_PATHS) for n in (name, torch_py2_renamed(name)))


def torch_py2_renamed(name):
    """(Pure.) A "module.name" as torch's weights_only unpickler would look it up after its Python 2 renames."""
    module, _, attr = name.rpartition(".")
    if (module, attr) in TORCH_PY2_NAMES:
        return ".".join(TORCH_PY2_NAMES[(module, attr)])
    if module in TORCH_PY2_IMPORTS:
        return f"{TORCH_PY2_IMPORTS[module]}.{attr}"
    return name


def scan_pickle(data):
    """(Pure.) Every global one pickle names, in order, as "module.name". GLOBAL and INST are read from their argument;
    STACK_GLOBAL from the two strings it pops, followed through the memo (PUT, BINPUT, LONG_BINPUT, MEMOIZE and the
    GETs). It only resolves when the two ops before it each pushed a known string; anything else (an unknown operand,
    an extension-registry op, a pickle that does not parse, bytes after STOP) refuses. Nothing is unpickled."""
    import io
    import pickletools

    found, memo, tops = [], {}, []
    stream = io.BytesIO(data)
    try:
        for op, arg, pos in pickletools.genops(stream):
            name = op.name
            if name in _NEUTRAL_OPS:
                continue
            if name in _PUT_OPS:
                memo[arg] = tops[-1] if tops else _UNKNOWN
                continue
            if name == "MEMOIZE":
                memo[len(memo)] = tops[-1] if tops else _UNKNOWN
                continue
            if name in _STR_OPS:
                tops.append(arg if isinstance(arg, str) else _UNKNOWN)
            elif name in _GET_OPS:
                tops.append(memo.get(arg, _UNKNOWN))
            elif name in ("GLOBAL", "INST"):
                module, _, attr = arg.partition(" ")
                found.append(f"{module}.{attr}")
                tops.append(_UNKNOWN)
            elif name == "STACK_GLOBAL":
                if len(tops) < 2 or not all(isinstance(t, str) for t in tops[-2:]):
                    refuse(f"pickle scan: the STACK_GLOBAL at byte {pos} has operands that are not known strings")
                found.append(f"{tops[-2]}.{tops[-1]}")
                tops.append(_UNKNOWN)
            elif name in ("EXT1", "EXT2", "EXT4"):
                refuse(f"pickle scan: the extension-registry op {name} at byte {pos} cannot be resolved")
            else:
                tops.append(_UNKNOWN)
            if len(tops) > 64:
                del tops[:-2]
    except ValueError as e:                                  # pickletools: a bad opcode, a truncated argument, no STOP
        refuse(f"pickle scan: the pickle does not parse ({e})")
    if stream.read():
        refuse("pickle scan: bytes after the pickle's STOP")
    return found


def scan_checkpoint(path_or_file):
    """(Pure, standard library.) A torch zip checkpoint (path or open binary file) -> {member: [globals]} for every
    `.pkl` member, in the zip's order. Not a zip, or a zip without a `.pkl`, refuses: a legacy pickle is never
    scanned or loaded."""
    import zipfile

    try:
        zf = zipfile.ZipFile(path_or_file)
    except zipfile.BadZipFile:
        refuse("pickle scan: not a zip checkpoint (a legacy pickle checkpoint is not scanned)")
    out = {}
    with zf:
        for info in zf.infolist():
            if info.filename.endswith(".pkl"):
                out.setdefault(info.filename, []).extend(scan_pickle(zf.read(info)))
    if not out:
        refuse("pickle scan: the checkpoint has no .pkl member")
    return out


def check_globals(scan, allow):
    """(Pure.) Refuses any scanned global on the denylist or outside `allow`. -> the distinct globals found, sorted."""
    found = sorted({g for gs in scan.values() for g in gs})
    denied = [g for g in found if denied_global(g)]
    if denied:
        refuse(f"pickle scan: denylisted globals {denied}")
    outside = [g for g in found if g not in set(allow)]
    if outside:
        refuse(f"pickle scan: globals outside the allowlist {outside}")
    return found


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


def load_mono(path, target_sr=None):
    """The torch modes' only audio read: the file by soundfile (never `librosa.load`, whose audioread fallback probes
    with ffmpeg in a subprocess), the channel mean as float32 (`librosa.to_mono`'s mono), then `librosa.resample` to
    `target_sr` when it differs (librosa's default resampler, as `librosa.load(path, sr=target_sr)` uses). -> (mono
    float32, its rate)."""
    import numpy as np
    import soundfile as sf

    x, sr = sf.read(path, dtype="float32", always_2d=True)
    y = np.mean(x, axis=1).astype(np.float32)
    if target_sr is None or sr == target_sr:
        return y, sr
    import librosa

    return librosa.resample(y, orig_sr=sr, target_sr=target_sr).astype(np.float32), target_sr


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


# --- the torch modes: the network and process refusals --------------------------------------------------------------------

def _refuser(what):
    def refused(*args, **kwargs):
        refuse(f"{what} is refused in the torch modes (no network, no processes)")
    return refused


def refusal_patches():
    """The network and process refusals as [(owner, attribute, label)]: `os.system`, `os.popen`, every `os.exec*`,
    `os.spawn*` and `os.posix_spawn*` (and their `posix` twins), `subprocess.Popen._execute_child` (every subprocess
    call reaches it), `_posixsubprocess.fork_exec`, and socket connect, connect_ex, sendto, create_connection and
    getaddrinfo."""
    import _posixsubprocess
    import posix
    import socket
    import subprocess

    out = []
    for mod in (os, posix):
        for name in sorted(dir(mod)):
            if (name in ("system", "popen") or name.startswith(("exec", "spawn", "posix_spawn"))) and \
                    callable(getattr(mod, name)):
                out.append((mod, name, f"{mod.__name__}.{name}"))
    out.append((subprocess.Popen, "_execute_child", "subprocess"))
    out.append((_posixsubprocess, "fork_exec", "_posixsubprocess.fork_exec"))
    for name in ("connect", "connect_ex", "sendto"):
        out.append((socket.socket, name, f"socket.socket.{name}"))
    for name in ("create_connection", "getaddrinfo"):
        out.append((socket, name, f"socket.{name}"))
    return out


def install_refusals(setter=setattr):
    """Installs the refusals (before torch or any tool is imported). -> their labels."""
    labels = []
    for owner, attr, label in refusal_patches():
        setter(owner, attr, _refuser(label))
        labels.append(label)
    return labels


# --- the torch modes: the guarded load and the key report -------------------------------------------------------------------

def _handle_sha(fh):
    h = hashlib.sha256()
    for b in iter(lambda: fh.read(1 << 20), b""):
        h.update(b)
    return h.hexdigest()


def resolve_globals(names, aliases):
    """The allowlisted "module.name"s -> [(object, "module.name")] for torch's `safe_globals`, each imported from the
    longest module prefix that imports (a top-level module in `aliases` read as its alias). One that does not resolve
    refuses."""
    import importlib

    out = []
    for full in names:
        if denied_global(full):
            refuse(f"{full} is denylisted")
        parts, obj = full.split("."), None
        for i in range(len(parts) - 1, 0, -1):
            top = parts[0]
            module = ".".join([aliases.get(top, top)] + parts[1:i])
            try:
                obj = importlib.import_module(module)
            except ImportError:
                continue
            try:
                for a in parts[i:]:
                    obj = getattr(obj, a)
            except AttributeError:
                obj = None
            break
        if obj is None:
            refuse(f"the allowlisted global {full} does not resolve")
        out.append((obj, full))
    return out


class GuardedLoad:
    """Every `torch.load` in the torch modes. Only the pinned path loads; a file object refuses unless this wrapper
    opened it itself from that path. The file is opened here, re-hashed and re-scanned on the same handle, and loaded
    from it with `weights_only=True` forced, `map_location="cpu"`, and exactly the allowlisted globals made safe
    (resolved on the first load, after the tool's own import). Any keyword past `map_location`, `weights_only` and
    `mmap` refuses (`pickle_module` among them); the caller's `weights_only` and `mmap` are overridden."""

    def __init__(self, path, sha, allow, aliases, load, safe_globals, resolve=None):
        self.real, self.sha, self.allow, self.aliases = os.path.realpath(path), sha, list(allow), aliases
        self.load_fn, self.safe_globals_fn = load, safe_globals
        self.resolve = resolve_globals if resolve is None else resolve
        self.safe, self.opened, self.loads = None, set(), []

    def __call__(self, f, map_location=None, *args, **kwargs):
        if args:
            refuse("torch.load: positional arguments past map_location are refused")
        bad = sorted(set(kwargs) - {"weights_only", "mmap"})
        if bad:
            refuse(f"torch.load: {bad} refused (weights_only=True is forced)")
        if isinstance(f, (str, bytes, os.PathLike)):
            p = os.fsdecode(os.fspath(f))
            if os.path.realpath(p) != self.real:
                refuse(f"torch.load of {p}: only the pinned checkpoint loads")
        elif id(f) not in self.opened:
            refuse("torch.load of a file object this runner did not open from the pinned path")
        if self.safe is None:
            self.safe = self.resolve(self.allow, self.aliases)
        with open(self.real, "rb") as fh:
            self.opened.add(id(fh))
            try:
                got = _handle_sha(fh)
                if got != self.sha:
                    refuse(f"torch.load: the checkpoint's sha256 is now {got}, not the pinned {self.sha}")
                fh.seek(0)
                check_globals(scan_checkpoint(fh), self.allow)
                fh.seek(0)
                try:
                    with self.safe_globals_fn(self.safe):
                        obj = self.load_fn(fh, map_location="cpu", weights_only=True)
                except Exception as e:                       # e.g. UnpicklingError: a global torch would not allow
                    refuse(f"the guarded load (weights_only=True) refused the checkpoint ({type(e).__name__}: "
                           f"{str(e)[:300]})")
            finally:
                self.opened.discard(id(fh))
        self.loads.append(self.real)
        return obj


class KeyReport:
    """Every `load_state_dict`: called with strict=False, its missing and unexpected keys recorded; a missing key (one
    the model needs) refuses."""

    def __init__(self, original):
        self.original, self.rows = original, []

    def wrapper(self):
        report = self

        def load_state_dict(module, state_dict, strict=True, *args, **kwargs):
            result = report.original(module, state_dict, False, *args, **kwargs)
            missing, unexpected = list(result.missing_keys), list(result.unexpected_keys)
            report.rows.append({"module": type(module).__name__, "strict_asked": bool(strict),
                                "missing": missing, "unexpected": unexpected})
            if missing:
                refuse(f"load_state_dict: {type(module).__name__} lacks {len(missing)} keys the model needs "
                       f"({missing[:3]})")
            return result
        return load_state_dict


def import_torch(threads):
    import torch

    torch.set_num_threads(threads)
    if torch.get_num_interop_threads() != threads:        # settable once per process, before any parallel work
        try:
            torch.set_num_interop_threads(threads)
        except RuntimeError:
            refuse(f"torch's inter-op threads are already {torch.get_num_interop_threads()}, not {threads}")
    return torch


def install_torch_guards(torch, guard, report, setter=setattr):
    """`torch.load` (and `torch.serialization.load`) through the guard; `Module.load_state_dict` through the report."""
    setter(torch, "load", guard)
    setter(torch.serialization, "load", guard)
    setter(torch.nn.Module, "load_state_dict", report.wrapper())


def module_versions(names):
    """Versions read from the imported modules themselves, never from package metadata (lock B's two code archives are
    unpacked, not pip-registered): {name: `__version__` or None} for each module already imported, plus
    {name.file: sha256} for each `.py` named "package.module" (the pinned code identified by its own bytes)."""
    out = {}
    for name in names:
        mod = sys.modules.get(name)
        if mod is None:
            out[name] = None
        elif "." in name:
            out[f"{name}.sha256"] = file_sha(mod.__file__)
        else:
            out[name] = getattr(mod, "__version__", None)
    return out


# --- the torch modes: one adapter per tool (to confirm on install) ----------------------------------------------------------

class Mt3Adapter:
    """YourMT3+ through `mt3-infer` 0.2.0 (tag 2d20ee5b). TO CONFIRM ON INSTALL: the calls below were read from the
    pinned tag's source, not run. `YourMT3Adapter(model_key).load_model(checkpoint_path=<pinned>, device="cpu")`
    (never `mt3_infer.load_model`, whose auto-download clones the Space); the key is checked after the load (it is
    picked from the pinned directory name). A read is the adapter's `preprocess` (its own torchaudio resample) and
    `forward`, then the first half of its `decode` (per channel `detokenize_list_batches`, then
    `merge_zipped_note_events_and_ties_to_notes`, then `mix_notes`), stopping at the note list instead of a MIDI file.
    One inference serves both `programs` options."""

    def __init__(self, spec, threads):
        from mt3_infer.adapters.yourmt3 import YourMT3Adapter

        ad = YourMT3Adapter(model_key=MT3_MODEL_KEY)
        ad.load_model(checkpoint_path=spec["model"], device="cpu")
        if ad.model_key != MT3_MODEL_KEY:
            refuse(f"mt3: the checkpoint loaded as {ad.model_key}, not {MT3_MODEL_KEY}")
        self.ad = ad
        import torchaudio  # noqa: F401                    # its own resample; imported for its version

        self.versions = module_versions(("mt3_infer", "torchaudio", "mt3_infer.adapters.yourmt3",
                                         "mt3_infer.models.yourmt3.inference_loader"))

    def read(self, path):
        from mt3_infer.models.yourmt3.utils.event2note import merge_zipped_note_events_and_ties_to_notes
        from mt3_infer.models.yourmt3.utils.note2event import mix_notes

        audio, sr = load_mono(path)                          # mono, as MT3Base.transcribe makes it; its own resample
        tokens = self.ad.forward(self.ad.preprocess(audio, sr))
        m = self.ad.model
        total = sum(a.shape[0] for a in tokens)
        frames, msr = m.audio_cfg["input_frames"], m.audio_cfg["sample_rate"]
        starts = [frames * i / msr for i in range(total)]
        per_channel = []
        for ch in range(m.task_manager.num_decoding_channels):
            zipped, _, _ = m.task_manager.detokenize_list_batches([a[:, ch, :] for a in tokens], starts,
                                                                  return_events=True)
            notes_ch, _ = merge_zipped_note_events_and_ties_to_notes(zipped)
            per_channel.append(notes_ch)
        return [(bool(n.is_drum), int(n.program), float(n.onset), float(n.offset), int(n.pitch), n.velocity)
                for n in mix_notes(per_channel)]

    @staticmethod
    def notes(raw, options):
        return mt3_select(raw, options["programs"])


class KongAdapter:
    """Riley's guitar models through the `piano_transcription_inference` fork at cfe28ed. TO CONFIRM ON INSTALL: the
    calls below were read from the pinned commit's source, not run. Built as `hf_midi_transcription` 96f6797 builds a
    non-piano model: `PianoTranscription(KONG_MODEL_TYPE, device="cpu", checkpoint_path=<pinned>,
    segment_samples=10 * sample_rate, batch_size=8)` (16 kHz); audio by `load_mono` (soundfile, the channel mean,
    `librosa.resample` to 16 kHz), what its `librosa.load(path, sr=sample_rate)` gives for a wav but never through
    audioread's ffmpeg probe, a subprocess the guard refuses. One `transcribe(audio, None)` gives the model output (the four regression maps kept); each
    (onset, frame) point is then the fork's own `RegressionPostProcessor`, which takes the thresholds as arguments, so
    no patch is needed; offset 0.3 and pedal 0.2 as shipped."""

    def __init__(self, spec, threads):
        import librosa  # noqa: F401                       # its loader; imported for its version
        import piano_transcription_inference.utilities  # noqa: F401
        from piano_transcription_inference import PianoTranscription, sample_rate

        self.sr = sample_rate
        self.tr = PianoTranscription(KONG_MODEL_TYPE, checkpoint_path=spec["model"],
                                     segment_samples=KONG_SEGMENT_S * sample_rate, batch_size=KONG_BATCH, device="cpu")
        self.versions = dict(module_versions(("librosa", "piano_transcription_inference.inference",
                                              "piano_transcription_inference.utilities",
                                              "piano_transcription_inference.models")),
                             piano_transcription_inference_commit=KONG_FORK_COMMIT)

    def read(self, path):
        audio, _ = load_mono(path, self.sr)
        out =self.tr.transcribe(audio, None)["output_dict"]
        missing = [k for k in KONG_RAW_KEYS if k not in out]
        if missing:
            refuse(f"kong: the model output lacks {missing}")
        return {k: out[k] for k in KONG_RAW_KEYS}

    def notes(self, raw, options):
        import numpy as np
        from piano_transcription_inference.utilities import RegressionPostProcessor

        pp = RegressionPostProcessor(self.tr.frames_per_second, classes_num=self.tr.classes_num,
                                     onset_threshold=options["onset_threshold"],
                                     offset_threshold=KONG_FIXED["offset_threshold"],
                                     frame_threshold=options["frame_threshold"],
                                     pedal_offset_threshold=KONG_FIXED["pedal_offset_threshold"])
        notes, _ = pp.output_dict_to_midi_events({k: np.array(v, copy=True) for k, v in raw.items()})
        return kong_events(notes)


ADAPTERS = {"mt3": Mt3Adapter, "kong": KongAdapter}


def run_torch(mode, spec, pairs, model_sha, threads):
    """The torch modes, in the safety order of the module docstring, then one inference per input with every grid
    point post-processed from it."""
    import tempfile

    scan = scan_checkpoint(spec["model"])
    found = check_globals(scan, spec["allow_globals"])
    print(f"readerr_run: allowlist {sorted(spec['allow_globals'])}", flush=True)
    print(f"readerr_run: scanned globals {found}", flush=True)
    cap_threads(threads)
    guards = install_refusals()
    torch = import_torch(threads)
    guard = GuardedLoad(spec["model"], spec["model_sha256"], spec["allow_globals"], TORCH_ALIASES[mode], torch.load,
                        torch.serialization.safe_globals)
    report = KeyReport(torch.nn.Module.load_state_dict)
    install_torch_guards(torch, guard, report)
    adapter = ADAPTERS[mode](spec, threads)                   # the tool's own code is imported only here
    if not guard.loads:
        refuse(f"{mode}: the checkpoint was not loaded through the guarded load")
    if not report.rows:
        refuse(f"{mode}: no load_state_dict was reported")
    versions = dict(adapter.versions, torch=torch.__version__, python=sys.version.split()[0],
                    **module_versions(("numpy",)))
    for src, dst in pairs:
        t0 = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="readerr-") as workdir:
            sr = _input_rate(src)
            n = pad_samples(spec.get("lead_in_s", 0), sr)
            raw = adapter.read(_padded(src, n, workdir))
            base, rows = torch_output(mode, spec["options"], spec.get("grid"),
                                      lambda o: rebase(adapter.notes(raw, o), n / sr))
        out = {"mode": mode, "versions": versions, "model_sha256": model_sha, "threads": threads, "spec": spec,
               "input_sha256": file_sha(src), "seconds": round(time.perf_counter() - t0, 3), "events": base}
        if rows is not None:
            out["grid"] = rows
        out.update(scan=scan, load_report=report.rows, guards=guards)
        write_json(dst, out)
        print(f"readerr_run: {mode} {len(base)} notes -> {dst}", flush=True)


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
    if mode in TORCH_MODES:
        run_torch(mode, spec, pairs, model_sha, threads)
        return
    cap_threads(threads)
    import tempfile

    bp = BasicPitch(spec["model"], threads)
    run = run_bp_grid if mode == "bp-grid" else run_bp_shift
    versions = bp.versions
    for src, dst in pairs:
        t0 = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="readerr-") as workdir:
            body = run(bp, spec, src, workdir)
        out = {"mode": mode, "versions": versions, "model_sha256": model_sha, "threads": threads, "spec": spec,
               "input_sha256": file_sha(src), "seconds": round(time.perf_counter() - t0, 3)}
        out.update(body)
        write_json(dst, out)
        print(f"readerr_run: {mode} {len(out['events'])} notes -> {dst}", flush=True)


if __name__ == "__main__":
    main()
