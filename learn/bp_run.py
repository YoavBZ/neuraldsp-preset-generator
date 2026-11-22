"""Basic Pitch, run inside its own venv (`docs/note-rebuild-plan.md` section 12; ledger `note-rebuild`
`phase_nr_1_redo`). Called only by `learn/note_transcribe.py`, as

    ~/ndsp-presets/tools/basic-pitch-venv/bin/python -I learn/bp_run.py --model NMP_ONNX --settings JSON \
        in1.wav out1.json [in2.wav out2.json ...]

Several pairs run in one process (the install gate's repeat test needs two runs in one process). Nothing in the main
`.venv` or on CI imports Basic Pitch: this file imports it inside `main` only, and its module level is the standard
library (it runs under `-I`, so it imports nothing from this repository either). Python 3.9 syntax.

The model is ONNX on the CPU: the package's `Model` builds its own `InferenceSession` with no options, so this replaces
`model.model` with a session of one intra-op and one inter-op thread, on the `.onnx` file passed by path, and asserts
the model type is ONNX and the provider list is exactly ["CPUExecutionProvider"]. Each output holds the note events
(start, end, MIDI pitch, amplitude, bend track; times to 0.1 ms), the settings it ran with, the model file's sha256, the
package versions and the provider list.
"""

import hashlib
import json
import sys

PROVIDERS = ["CPUExecutionProvider"]
THREADS = 1
SETTING_KEYS = ("onset_threshold", "frame_threshold", "minimum_note_length", "minimum_frequency",
                "maximum_frequency", "melodia_trick", "multiple_pitch_bends")


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def event_record(ev):
    """(Pure.) One Basic Pitch note event (start s, end s, MIDI pitch, amplitude, bends or None) as stored: times to
    0.1 ms, the amplitude to 1e-6, the bend track as ints (thirds of a semitone per frame)."""
    start, end, pitch, amp, bends = ev
    return {"on": round(float(start), 4), "off": round(float(end), 4), "pitch": int(pitch),
            "amp": round(float(amp), 6), "bends": [int(b) for b in bends] if bends is not None else []}


def parse_args(argv):
    """(Pure.) -> (model path, settings, [(in, out)]). Refuses a missing or unknown setting and an odd pair list."""
    model, settings, rest, i = None, None, [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--model":
            model, i = argv[i + 1], i + 2
        elif a == "--settings":
            settings, i = json.loads(argv[i + 1]), i + 2
        else:
            rest.append(a)
            i += 1
    if model is None or settings is None:
        raise SystemExit("bp_run: --model and --settings are required")
    if sorted(settings) != sorted(SETTING_KEYS):
        raise SystemExit(f"bp_run: settings must be exactly {sorted(SETTING_KEYS)}")
    if not rest or len(rest) % 2:
        raise SystemExit("bp_run: give input and output files in pairs")
    return model, settings, list(zip(rest[::2], rest[1::2]))


def main(argv=None):
    model_path, settings, pairs = parse_args(sys.argv[1:] if argv is None else argv)
    import basic_pitch                                   # the venv's only: never imported in the main .venv or on CI
    import onnxruntime as ort
    from basic_pitch.inference import Model, predict

    opts = ort.SessionOptions()
    opts.intra_op_num_threads = THREADS
    opts.inter_op_num_threads = THREADS
    model = Model(model_path)
    if model.model_type != Model.MODEL_TYPES.ONNX:
        raise SystemExit(f"bp_run: the model loaded as {model.model_type}, not ONNX")
    model.model = ort.InferenceSession(str(model_path), sess_options=opts, providers=PROVIDERS)
    got = list(model.model.get_providers())
    if got != PROVIDERS:
        raise SystemExit(f"bp_run: providers {got}, not {PROVIDERS}")
    meta = {"model_sha256": file_sha(model_path), "providers": got, "threads": THREADS,
            "basic_pitch": getattr(basic_pitch, "__version__", None), "onnxruntime": ort.__version__,
            "python": sys.version.split()[0], "settings": settings}
    for src, dst in pairs:
        _, _, events = predict(src, model, **settings)
        out = dict(meta, input_sha256=file_sha(src), events=[event_record(e) for e in events])
        with open(dst, "w") as f:
            json.dump(out, f, indent=1)
        print(f"bp_run: {len(events)} notes -> {dst}", flush=True)


if __name__ == "__main__":
    main()
