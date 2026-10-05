#!/usr/bin/env python3
"""Collect guitar DIs to audition presets through, from development crops only.

    python scripts/build_di_library.py [--crops-dir DIR] [--data-dir DIR]

An audition (`audition.py`) plays every candidate through the same guitar riff, a
DI of another performance than the song's. This copies each development part's
crop-rule-2 DI (the 10 seconds where the part's DI plays most) into
`<data root>/di-library/`, with an index saying what each riff is and how it plays:

- `playing`: the share of frames the DI plays in;
- `notes_per_s`: note onsets per second while it plays (spectral-flux peaks), and
  `pace`, the third of the library it falls in ("sparse", "moderate", "busy"). Rough:
  checked on synthetic plucks only; a strum counts as one note;
- `brightness_hz`: the DI's median spectral centroid while it plays, from the
  pickup and the register together, and `brightness` ("dark", "middle", "bright").

Thirds of this library rather than fixed thresholds, so two riffs can always be
chosen to differ.

These describe the playing, measured from the DI; they say nothing about tone.
Held-out parts are refused, and parts whose DI plays in under half the window are
left out. The DIs come from datasets you downloaded: they stay in your data root
and are never shipped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import add_data_dir_arg, die, guarded

MIN_PLAYING = 0.5
FRAME, HOP = 1024, 512
FLOOR_DB = -40.0            # a frame plays when within 40 dB of the DI's loudest
MIN_GAP_S = 0.05            # onsets closer than this are one note
LOCAL_S = 0.25              # the median around a peak is taken over this much each side


def describe(mono, rate):
    """(playing share, notes per second while playing, median centroid in Hz)."""
    import numpy as np

    from analysis import io

    levels = io.frame_rms_db(mono, FRAME, HOP)
    playing = levels >= levels.max() + FLOOR_DB
    count = len(levels)
    windows = np.lib.stride_tricks.as_strided(
        np.pad(np.asarray(mono, dtype=np.float64), (0, FRAME)),
        shape=(count, FRAME), strides=(8 * HOP, 8))
    spectrum = np.abs(np.fft.rfft(windows * np.hanning(FRAME), axis=1))
    freqs = np.fft.rfftfreq(FRAME, 1 / rate)
    log = np.log1p(1000 * spectrum / (spectrum.max() + 1e-12))
    flux = np.concatenate(([0.0], np.maximum(np.diff(log, axis=0), 0).sum(axis=1)))
    flux[~playing] = 0.0
    # A peak counts when it clears the local median by a fifth of the riff's strong
    # attacks: a fixed share of the strongest, so decays and hiss between notes
    # (whose flux is near zero but never exactly) do not count.
    strong = np.percentile(flux[playing], 99) if playing.any() else 0.0
    half = max(1, round(LOCAL_S * rate / HOP))
    gap = max(1, round(MIN_GAP_S * rate / HOP))
    onsets, last = 0, -gap
    for i in range(1, count - 1):
        local = np.median(flux[max(0, i - half):i + half + 1])
        if (flux[i] > local + 0.2 * strong and flux[i] >= flux[i - 1]
                and flux[i] >= flux[i + 1] and i - last >= gap):
            onsets, last = onsets + 1, i
    seconds = playing.sum() * HOP / rate
    power = spectrum[playing] ** 2
    centroid = (power * freqs).sum(axis=1) / (power.sum(axis=1) + 1e-20)
    return (float(playing.mean()), onsets / seconds if seconds else 0.0,
            float(np.median(centroid)))


def thirds(values, words):
    """{key: word} placing each value in a third of `values`, by rank."""
    order = sorted(values, key=lambda k: (values[k], k))
    return {k: words[min(2, 3 * i // len(order))] for i, k in enumerate(order)}


def _sha(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops-2"))
    add_data_dir_arg(ap)
    args = ap.parse_args()
    from analysis import require

    require("building the DI library")
    from analysis import io
    from packs import paths

    if args.data_dir:
        paths.set_data_root(args.data_dir)
    catalog = json.loads((PLUGIN_ROOT / "docs" / "validation-datasets.json").read_text(encoding="utf-8"))
    split, band = {}, {}
    for s in catalog["sessions"]:
        for p in s["parts"]:
            slug = "-".join(x.replace("/", "_").replace(" ", "_")
                            for x in (s["source"], s["song"], p["part"]))
            split[slug] = p.get("split") or s.get("split")
            band[slug] = s.get("group") or s["song"]
    crops = args.crops_dir.expanduser()
    out = paths.data_root() / "di-library"
    out.mkdir(parents=True, exist_ok=True)
    riffs, skipped = {}, []
    for crop in sorted(p for p in crops.iterdir() if (p / "record.json").exists()):
        record = json.loads((crop / "record.json").read_text())
        # Both the crop's own record and the catalogue must call it development.
        if record.get("split") != "development" or split.get(crop.name) != "development":
            die(f"{crop.name} is not a development part; the library takes no other")
        di = io.load(crop / "di.wav")
        playing, notes, brightness = describe(di.mono(), di.sample_rate)
        if playing < MIN_PLAYING:
            skipped.append(crop.name)
            continue
        target = out / f"{crop.name}.wav"
        shutil.copy2(crop / "di.wav", target)
        riffs[crop.name] = {"file": target.name, "sha256": _sha(target),
                            "band": band.get(crop.name), "song": record["song"],
                            "part": record["part"], "source": record["source"],
                            "starts_at_s": record["excerpt_start_s"],
                            "playing": round(playing, 3), "notes_per_s": round(notes, 2),
                            "brightness_hz": round(brightness)}
    if not riffs:
        die(f"no usable development DI under {crops}")
    pace = thirds({k: v["notes_per_s"] for k, v in riffs.items()}, ("sparse", "moderate", "busy"))
    third = thirds({k: v["brightness_hz"] for k, v in riffs.items()}, ("dark", "middle", "bright"))
    for k, v in riffs.items():
        v["pace"], v["brightness"] = pace[k], third[k]
    index = {"schema": "di-library-v1", "crops_dir": str(crops), "riffs": riffs,
             "skipped_quiet": skipped}
    (out / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    print(f"{len(riffs)} riffs in {out} ({len(skipped)} left out as mostly silent)")


if __name__ == "__main__":
    guarded(main)
