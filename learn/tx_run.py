"""MuScriptor, run inside its own venv (`docs/note-transcriber-plan.md`; ledger `note-transcriber` `phase_tx`). Called
only by `learn/note_tx.py`, as

    HF_HUB_OFFLINE=1 ~/ndsp-presets/tools/muscriptor-venv/bin/python -I learn/tx_run.py --weights PATH \
        --device mps|cpu --settings JSON --inputs MANIFEST in1.wav out1.json [in2.wav out2.json ...]

Several pairs run in one process (the gate's repeat test needs two runs in one process). Nothing in the main `.venv` or
on CI imports MuScriptor or torch: this file imports them inside `main` only, and its module level is the standard
library (it runs under `-I`, so it imports nothing from this repository either). Python 3.10 syntax.

The input guard (MuScriptor's terms forbid transcribing music without the rights to it): MANIFEST is written by
`note_tx` (`note_tx.declared_input`, the only way a row is made) and lists every input's sha256 with its source,
`list:<name>`, `truth:<window key>` or `goat-dev:<item>`. The runner refuses, before the model loads, an input whose
sha256 is not in the manifest and a manifest naming any other kind of source (a row part, a replay part, a stem, a
song). It also refuses: a settings dict other than the two declared ones, a device other than mps or cpu, an odd pair
list, a weights file whose sha256 is not a declared one, and `HF_HUB_OFFLINE` unset (nothing may reach the network).

Each output holds the notes (start, end, MIDI pitch, instrument group; times to 0.1 ms; a note with no end event ends
at the input's end, counted), the settings it ran with, the weights' sha256, the package, torch and Python versions,
the device and dtype, the input's sha256 and source, the model's load seconds and the input's transcription seconds
(timed apart, so the gate's speed is transcription only), and the counts (unfinished notes, drums dropped, end events
with no start, notes per instrument group).

The runner trusts the manifest's labels: it checks that each input's sha256 is listed and that each label's kind is
declared material, but it cannot tell what audio a label names. The real guard is `note_tx.declared_input`, which
`note_tx.run_ms` applies to every source before it writes the inputs and the manifest.
"""

import hashlib
import json
import os
import sys
import time

SETTING_KEYS = ("use_sampling", "cfg_coef", "instruments", "batch_size", "beam_size", "prelude_forcing")
GUITAR_GROUPS = ("acoustic_guitar", "clean_electric_guitar", "distorted_electric_guitar")
MASKED = {"use_sampling": False, "cfg_coef": 1.0, "instruments": list(GUITAR_GROUPS), "batch_size": 1,
          "beam_size": 1, "prelude_forcing": True}          # tx-ms: the guitar groups only
FREE = dict(MASKED, instruments=None)                      # tx-ms-free: no instrument mask (drums dropped)
DECLARED_SETTINGS = (MASKED, FREE)
SOURCE_KINDS = ("list", "truth", "goat-dev")               # the declared material; nothing else is transcribed
WEIGHTS = {                                                # size: (sha256, bytes) of model.safetensors
    "medium": ("ac80adbdf85d87231735fd948af7013441c0afced316c4e9067fd5d8a7fb97ec", 1228144472),
    "small": ("bbd482c786b895cf7d8f44185073d951adae2ebb8a66f82ca84cd1f84569549c", 411888600),
}
DEVICES = ("mps", "cpu")
THREADS = 4
DRUMS = "drums"


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def settings_refusal(settings):
    """(Pure.) Why a settings dict may not run, or None: its key set must be SETTING_KEYS and its values one of the
    two declared settings."""
    if not isinstance(settings, dict) or sorted(settings) != sorted(SETTING_KEYS):
        return f"settings must be exactly {sorted(SETTING_KEYS)}"
    if settings not in [dict(s) for s in DECLARED_SETTINGS]:
        return "settings are not one of the two declared ones (the guitar groups, or no mask)"
    return None


def parse_args(argv):
    """(Pure.) -> {weights, device, settings, inputs, pairs}. Refuses a missing argument, an undeclared device or
    settings, and an odd pair list."""
    got, rest, i = {}, [], 0
    flags = {"--weights": "weights", "--device": "device", "--settings": "settings", "--inputs": "inputs"}
    while i < len(argv):
        a = argv[i]
        if a in flags:
            if i + 1 >= len(argv):
                raise SystemExit(f"tx_run: {a} needs a value")
            got[flags[a]], i = argv[i + 1], i + 2
        else:
            rest.append(a)
            i += 1
    missing = [f for f, k in flags.items() if k not in got]
    if missing:
        raise SystemExit(f"tx_run: {', '.join(missing)} required")
    if got["device"] not in DEVICES:
        raise SystemExit(f"tx_run: the device must be one of {DEVICES}")
    try:
        got["settings"] = json.loads(got["settings"])
    except ValueError:
        raise SystemExit("tx_run: --settings is not JSON")
    why = settings_refusal(got["settings"])
    if why:
        raise SystemExit(f"tx_run: {why}")
    if not rest or len(rest) % 2:
        raise SystemExit("tx_run: give input and output files in pairs")
    got["pairs"] = list(zip(rest[::2], rest[1::2]))
    return got


def env_refusal(env):
    """(Pure.) Why the environment may not run, or None: HF_HUB_OFFLINE must be "1"."""
    if env.get("HF_HUB_OFFLINE") != "1":
        return "HF_HUB_OFFLINE is not 1: nothing may reach the network"
    return None


def source_refusal(source):
    """(Pure.) Why a manifest source is not declared material, or None: `<kind>:<key>` with kind in SOURCE_KINDS and a
    key."""
    if not isinstance(source, str) or ":" not in source:
        return f"{source!r}: not a declared source (kind:key)"
    kind, key = source.split(":", 1)
    if kind not in SOURCE_KINDS:
        return f"{source!r}: the kind {kind!r} is not declared material ({', '.join(SOURCE_KINDS)})"
    if not key:
        return f"{source!r}: no key"
    return None


def manifest_sources(doc):
    """(Pure.) The input manifest {"inputs": [{sha256, source}]} -> {sha256: source}; refuses the whole manifest when
    any row names a source outside the declared material, or one sha256 twice with two sources."""
    out = {}
    for row in (doc or {}).get("inputs") or []:
        why = source_refusal(row.get("source"))
        if why:
            raise SystemExit(f"tx_run: the manifest: {why}")
        sha = row.get("sha256")
        if not isinstance(sha, str) or len(sha) != 64:
            raise SystemExit(f"tx_run: the manifest: {row.get('source')} has no sha256")
        if out.get(sha, row["source"]) != row["source"]:
            raise SystemExit("tx_run: the manifest names one input with two sources")
        out[sha] = row["source"]
    if not out:
        raise SystemExit("tx_run: the manifest lists no input")
    return out


def input_source(sha, sources):
    """(Pure.) An input's declared source, refused when its sha256 is not in the manifest."""
    if sha not in sources:
        raise SystemExit(f"tx_run: input {sha[:12]} is not in the manifest: never transcribed")
    return sources[sha]


def weights_size(sha):
    """(Pure.) The declared weights' size name for a sha256, refused otherwise."""
    for name, (s, _) in WEIGHTS.items():
        if s == sha:
            return name
    raise SystemExit(f"tx_run: weights {sha[:12]} are not a declared MuScriptor checkpoint")


def event_dict(ev):
    """One MuScriptor event as a plain dict: {"type": "start", index, pitch, time, instrument}, {"type": "end",
    index, time}; a progress event (or anything else) -> None. NoteEndEvent carries its start event (`start_event`);
    `start_event_index` is read if a release names it so."""
    name = type(ev).__name__
    if name == "NoteStartEvent":
        return {"type": "start", "index": int(ev.index), "pitch": int(ev.pitch), "time": float(ev.start_time),
                "instrument": str(ev.instrument)}
    if name == "NoteEndEvent":
        st = getattr(ev, "start_event", None)
        idx = st.index if st is not None else getattr(ev, "start_event_index")
        return {"type": "end", "index": int(idx), "time": float(ev.end_time)}
    return None


def notes_from_events(events, end_s):
    """(Pure.) Start and end events paired into notes by the start's index: {on, off, pitch, instrument}, times to
    0.1 ms, in onset order. A start with no end ends at `end_s` (counted unfinished); an end with no start is counted
    and dropped; drums are dropped (counted); an end before its start is held at the start.
    -> (notes, counts {unfinished, drums, orphan_ends, by_group})."""
    starts, ends = {}, {}
    cnt = {"unfinished": 0, "drums": 0, "orphan_ends": 0, "by_group": {}}
    for e in events:
        if e["type"] == "start":
            starts[e["index"]] = e
        elif e["type"] == "end":
            ends.setdefault(e["index"], e["time"])
    cnt["orphan_ends"] = sum(1 for k in ends if k not in starts)
    notes = []
    for k, s in starts.items():
        if s["instrument"] == DRUMS:
            cnt["drums"] += 1
            continue
        if k in ends:
            off = max(s["time"], ends[k])
        else:
            off = max(s["time"], float(end_s))
            cnt["unfinished"] += 1
        notes.append({"on": round(s["time"], 4), "off": round(off, 4), "pitch": int(s["pitch"]),
                      "instrument": s["instrument"]})
        cnt["by_group"][s["instrument"]] = cnt["by_group"].get(s["instrument"], 0) + 1
    notes.sort(key=lambda n: (n["on"], n["pitch"], n["off"]))
    return notes, cnt


def _dtype_name(model):
    for a in ("dtype", "_dtype"):
        v = getattr(model, a, None)
        if v is not None:
            return str(v)
    for a in ("model", "_model", "lm", "_lm"):
        m = getattr(model, a, None)
        if m is not None and hasattr(m, "parameters"):
            return str(next(m.parameters()).dtype)
    return "unknown"


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    why = env_refusal(os.environ)
    if why:
        raise SystemExit(f"tx_run: {why}")
    with open(args["inputs"]) as f:
        sources = manifest_sources(json.load(f))
    plan = [(src, dst, file_sha(src)) for src, dst in args["pairs"]]
    for src, _, sha in plan:                             # every input checked before the model loads
        input_source(sha, sources)
    if not os.path.isfile(args["weights"]):
        raise SystemExit("tx_run: the weights path is not a local file")
    if os.path.getsize(args["weights"]) not in [b for _, b in WEIGHTS.values()]:
        raise SystemExit("tx_run: the weights file has no declared size")
    wsha = file_sha(args["weights"])
    size = weights_size(wsha)
    import importlib.metadata as md

    import soundfile as sf                               # the venv's only: never imported in the main .venv or on CI
    import torch
    from muscriptor import TranscriptionModel

    torch.set_num_threads(THREADS)
    t0 = time.perf_counter()
    model = TranscriptionModel.load_model(args["weights"], device=args["device"], dtype=None)
    meta = {"load_s": time.perf_counter() - t0, "weights_sha256": wsha, "weights_size": size,
            "device": args["device"], "dtype": _dtype_name(model),
            "muscriptor": md.version("muscriptor"), "torch": torch.__version__, "threads": THREADS,
            "python": sys.version.split()[0], "settings": args["settings"]}
    for src, dst, sha in plan:
        t1 = time.perf_counter()
        events = [d for d in (event_dict(e) for e in model.transcribe(src, **args["settings"])) if d]
        secs = time.perf_counter() - t1                  # transcription only: the gate's speed reads this
        notes, counts = notes_from_events(events, sf.info(src).duration)
        out = dict(meta, input_sha256=sha, source=sources[sha], seconds=secs, notes=notes, counts=counts)
        with open(dst, "w") as f:
            json.dump(out, f, indent=1)
        print(f"tx_run: {len(notes)} notes ({sources[sha]}) -> {dst}", flush=True)


if __name__ == "__main__":
    main()
