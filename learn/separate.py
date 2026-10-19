"""Guitar separators for the ML steps, and htdemucs_6s guitar stems for validation crops (ML plan
2026-10, step 0).

**The default separator is Mega-53** (`DEFAULT_SEPARATOR`; the user's listening of the separation
samples, 2026-10-19, `docs/stereo-and-mix-check-results.md`): BS-Roformer Mega-53's pruned
electric-guitar head (`separator_screen.MsstSeparator`, the msst-venv). htdemucs_6s stays
selectable (`guitar_separator("htdemucs")`, the demucs-venv); every stored result keeps the
separator it was run with.

Recovered from the songs check's scripts (`~/ndsp-presets/learn/poc/stems/_work/
build_contexts.py` and `separate_demucs.py`), with the settings unchanged:
- **the context:** about 30 s centred on the crop (crop −10 s … crop +10 s, shifted inside
  the session). It is rebuilt from the session's tracks exactly as
  `scripts/build_validation_crops.py` built the crop: the record's mix tracks summed at unity,
  mono channel mean, `analysis.io.load` resampling, padded or cut to the session length.
  "Instrumental" drops the record's vocal tracks;
- **the separator:** htdemucs_6s (demucs 4.1.0, MIT), `shifts=0`, overlap 0.25, split. The mono
  48 kHz input is duplicated to two channels and resampled to 44.1 kHz. The guitar stem is
  channel-meaned, resampled back to 48 kHz with julius, padded or cut to the input, and the
  crop's 10 s cut out.

It runs in the separator's own environment, not the main `.venv`:

    ~/ndsp-presets/tools/demucs-venv/bin/python -m learn.separate CROP_DIR ... --out DIR
        [--role mix_instrumental|mix] [--crop-only]

It writes `DIR/<crop name>/<role>_guitar.wav` (48 kHz float32, the crop's length) and
`DIR/run.json`.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
DATA = HOME / "references/datasets"
SR = 48000
PAD_S = 10
MODEL, OVERLAP, SHIFTS = "htdemucs_6s", 0.25, 0
SEPARATORS = ("mega53", "htdemucs")
DEFAULT_SEPARATOR = "mega53"


def check_separator(name):
    """`name` if it is a known separator, else ValueError."""
    if name not in SEPARATORS:
        raise ValueError(f"unknown separator {name!r} (one of {SEPARATORS})")
    return name


def guitar_separator(name=DEFAULT_SEPARATOR, prune=True):
    """A CPU guitar separator, called on mono 48-kHz audio and returning the stem at 48 kHz, the same
    length. "mega53": Mega-53's electric-guitar head (`prune` its other heads, as stored; run in
    the msst-venv); "htdemucs": `GuitarSeparator` on the CPU (the demucs-venv)."""
    import os

    check_separator(name)
    if name == "mega53":
        from learn import separator_screen as SCR

        return SCR.MsstSeparator(prune=prune)
    os.environ["DEVICE"] = "cpu"
    sep = GuitarSeparator()
    if sep.device != "cpu":
        raise SystemExit(f"htdemucs runs on {sep.device}, not the CPU")
    return sep


def window(n, a, b, pad):
    """The context [cs, ce) around the crop [a, b) in a session of n frames: `pad` either side,
    shifted (not shrunk) to stay inside the session where it can."""
    cs, ce = a - pad, b + pad
    if cs < 0:
        ce, cs = min(n, ce - cs), 0
    if ce > n:
        cs, ce = max(0, cs - (ce - n)), n
    return cs, ce


def context(crop_dir, catalog):
    """(mix, instrumental, crop offset) for a crop folder, rebuilt from its session's tracks."""
    import numpy as np
    import soundfile as sf

    from analysis import io

    rec = json.loads((crop_dir / "record.json").read_text())
    sess = [s for s in catalog["sessions"] if s["source"] == rec["source"] and s["song"] == rec["song"]]
    assert len(sess) == 1, crop_dir
    s = sess[0]
    n, a, b = rec["session_frames"], rec["excerpt_start_frame"], rec["excerpt_end_frame"]
    cs, ce = window(n, a, b, PAD_S * SR)
    mix, sing = np.zeros(ce - cs), np.zeros(ce - cs)
    vocals = set(rec.get("vocal_tracks", []))
    for name in rec["included_mix_tracks"]:
        audio = io.load(DATA / s["path"] / name)
        assert audio.sha256 == rec["verified_source_sha256"][name], (crop_dir, name)
        x = np.zeros(n, np.float32)
        m = audio.mono().astype(np.float32)[:n]
        x[:len(m)] = m
        mix += x[cs:ce]
        if name in vocals:
            sing += x[cs:ce]
    inst = mix - sing
    for role, ctx in (("mix", mix), ("mix_instrumental", inst)):   # the line-up check
        path = crop_dir / f"{role}.wav"
        if path.exists():
            crop, _ = sf.read(str(path), dtype="float32")
            diff = float(np.max(np.abs(ctx[a - cs:b - cs].astype(np.float32) - crop)))
            assert diff < 1e-6, (crop_dir, role, diff)
    return mix.astype(np.float32), inst.astype(np.float32), a - cs


class GuitarSeparator:
    def __init__(self):
        import torch
        from demucs.api import Separator

        torch.set_num_threads(2)
        import os

        self.device = os.environ.get("DEVICE") or ("mps" if torch.backends.mps.is_available() else "cpu")
        self.sep = Separator(model=MODEL, device=self.device, shifts=SHIFTS, overlap=OVERLAP, split=True,
                             segment=None, progress=False)

    def __call__(self, x):
        """The guitar stem of mono 48 kHz `x`, at 48 kHz, the same length."""
        import julius
        import numpy as np
        import torch

        wav = torch.from_numpy(np.ascontiguousarray(x, np.float32))[None].expand(2, -1).contiguous()
        _, stems = self.sep.separate_tensor(wav, SR)
        g = julius.resample_frac(stems["guitar"].mean(0)[None], self.sep.samplerate, SR)[0].numpy()
        out = np.zeros(len(x), np.float32)
        k = min(len(x), len(g))
        out[:k] = g[:k]
        return out

    def info(self):
        import demucs
        import torch

        return {"model": MODEL, "demucs_version": demucs.__version__, "torch_version": torch.__version__,
                "device": self.device, "shifts": SHIFTS, "overlap": OVERLAP, "split": True,
                "model_samplerate": self.sep.samplerate, "context_pad_s": PAD_S}


def main(argv=None):
    import soundfile as sf

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("crops", nargs="+", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--role", default="mix_instrumental", choices=("mix_instrumental", "mix"))
    ap.add_argument("--crop-only", action="store_true", help="separate the 10-s crop alone, no context")
    a = ap.parse_args(argv)
    catalog = json.loads((PLUGIN_ROOT / "docs/validation-datasets.json").read_text())
    sep = GuitarSeparator()
    log = {}
    for crop in a.crops:
        target = a.out / crop.name / f"{a.role}_guitar.wav"
        if target.exists():
            continue
        t = time.time()
        if a.crop_only:
            x, sr = sf.read(str(crop / f"{a.role}.wav"), dtype="float32")
            assert sr == SR and x.ndim == 1
            off, length = 0, len(x)
        else:
            mix, inst, off = context(crop, catalog)
            x = inst if a.role == "mix_instrumental" else mix
            length = int(json.loads((crop / "record.json").read_text())["excerpt_end_frame"]
                         - json.loads((crop / "record.json").read_text())["excerpt_start_frame"])
        stem = sep(x)[off:off + length]
        assert len(stem) == length
        target.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(target), stem, SR, subtype="FLOAT")
        log[crop.name] = {"input_s": len(x) / SR, "seconds": round(time.time() - t, 1)}
        print(crop.name, log[crop.name], flush=True)
    run = a.out / "run.json"
    old = json.loads(run.read_text()) if run.exists() else {}
    old.update(sep.info(), crop_only=a.crop_only, role=a.role)
    old.setdefault("runs", {}).update(log)
    a.out.mkdir(parents=True, exist_ok=True)
    run.write_text(json.dumps(old, indent=1))


if __name__ == "__main__":
    main()
