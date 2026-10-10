"""Lag and gain class of the sets 1–2 held-out parts (`docs/set4-confirmation-plan.md`).

For each authorized part: set 3's waveform same-take test (GCC-PHAT, `gcc.py`) on the whole
session's amp track against its DI, at 48 kHz, gives the lag; set 3's `gainmeasure.py` and
`classify.py` at that lag give the session-level gain class. Reads no method's output.

    .venv/bin/python -m learn.confirm_prep --out ~/ndsp-presets/references/validation-crops-confirm/prep.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TOOLS = pathlib.Path("~/ndsp-presets/references/datasets-set3/_tools").expanduser()
DATA = pathlib.Path("~/ndsp-presets/references/datasets").expanduser()
CROPS = pathlib.Path("~/ndsp-presets/references/validation-crops-confirm").expanduser()
PLAN = ROOT / "docs/set4-confirmation-plan.md"
SR, JUDGE_LATENCY = 48000, 52


def authorized_parts():
    text = PLAN.read_text()
    block = re.search(r"```json\n(\{.*?\})\n```", text, re.S).group(1)
    return json.loads(block)["parts"]


SET1_BANDS = {"telefunken/Rebecca Haviland - 57 Chevy": "Rebecca Haviland",
              "cambridge/ChrisColtraine_ThatsHowIGotToMemphis_Full": "Chris Coltraine",
              "guitar-techs/P3_music": "Guitar-TECHS P3"}


def band(session):
    """The band (artist) a session belongs to: set 2 records it; set 1 by its path."""
    return session.get("artist") or SET1_BANDS[session["path"]]


def slug(part):
    src, song, name = part.split("/", 2)
    return re.sub(r"[^A-Za-z0-9]+", "_", f"{src}-{song}-{name}").strip("_")


def main(argv=None):
    import numpy as np

    from analysis import io

    sys.path.insert(0, str(TOOLS))
    import classify as C
    import gainmeasure as GM
    import gcc

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    args = ap.parse_args(argv)
    cat = json.loads((ROOT / "docs/validation-datasets.json").read_text())
    entries = {f"{s['source']}/{s['song']}/{p['part']}": (s, p)
               for s in cat["sessions"] for p in s["parts"]}
    out = {}
    for part in authorized_parts():
        s, p = entries[part]
        assert s["split"] == "held_out", part

        def load(name):
            a = io.load(DATA / s["path"] / name)
            assert a.sha256 == s["files"][name], name
            return np.asarray(a.mono(), np.float64)

        amp, di = load(p["reference"]), load(p["di"])
        w = gcc.windowed_gcc(amp, di, SR)
        lag = w.get("median_lag_samples")
        m = GM.measures(amp, di, SR, lag or 0)
        cls, conf, why, split = C.classify(m)
        passed = (w.get("windows", 0) >= 3 and w.get("in_step_fraction", 0) >= 0.8
                  and w.get("median_peak_to_sidelobe", 0) >= 2.0)
        out[slug(part)] = {
            "part": part, "band": band(s), "set": s.get("set", 1),
            "waveform_test": {k: v for k, v in w.items() if k != "lags"}, "waveform_pass": passed,
            "lag_samples": lag, "judge_lag_samples": None if lag is None else lag - JUDGE_LATENCY,
            "gain_class": cls, "gain_confidence": conf, "gain_reasons": why, "clean_vs_driven": split,
            "measures": m and {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()},
            "crop": str(CROPS / slug(part)),
        }
        print(f"{part:60s} lag {lag} pass {passed} class {cls}", flush=True)
    args.out.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
