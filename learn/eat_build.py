"""EfficientAT's own input for W's plugin rows and for BKS's and GOAT's labelled units (`docs/efficientat-plan.md`, task S1).
CPU, zero renders. `eat_net.front` stands in for the stored mel inside the ML session's own builders, whose mixes it leaves
unchanged, and the builders' file paths point at PF/eat/front. Every PARITY_EVERY-th input the rebuilt audio's usual mel is
compared with the stored file W or FTm read: a difference over one grid step stops the build. Nothing else is written: no
audio, and none of `pipeline_fix`'s own outputs.

    $TORCH_PY -m learn.eat_build clean --shard 0/3      # W's plugin rows, the target at its gain, no backing
    $TORCH_PY -m learn.eat_build wide --shard 0/3       # W's plugin rows in their first WIDE_K pool backings
    $TORCH_PY -m learn.eat_build real --shard 0/3       # BKS's and GOAT's labelled units in their 25 backings
    $TORCH_PY -m learn.eat_build amp --shard 0/3        # the same units' amp tracks alone, as `real_input_path` holds them
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from learn import eat_net as E  # noqa: E402

OUT = "eat"
WIDE_K = 4
PARITY_EVERY = 25
FLOOR_GB = 33.0
Q_LO, Q_SCALE = -1.5, 50.0                              # 0.02 of the normalised input, about 0.43 dB


def quant(x):
    return np.clip(np.round((np.asarray(x, np.float64) - Q_LO) * Q_SCALE), 0, 255).astype(np.uint8)


def dequant(q):
    return np.asarray(q, np.float32) / Q_SCALE + Q_LO


def front_root():
    from learn import pipeline_fix as P

    return P.out_dir() / OUT / "front"


def clean_path(i):
    return front_root() / "clean" / f"{i:07d}.npz"


def wide_path(i, k):
    return front_root() / "wide" / f"{i:07d}-k{k}.npz"


def real_path(unit, v):
    return front_root() / "real" / f"{unit.replace('/', '__')}-v{v:02d}.npz"


def amp_path(unit):
    return front_root() / "amp" / f"{unit.replace('/', '__')}.npz"


def to_32k(y):
    from scipy.signal import resample_poly

    return resample_poly(np.asarray(y, np.float64), 2, 3).astype(np.float32)


def half_features(y, logmel=None, lufs=None):
    """`direct_stems.half_features`'s shape with EfficientAT's input in place of the mel: uint8 [128, 450] per half."""
    from learn import pretrain_set as PS
    from learn import song_aug as SA

    y = np.asarray(y, np.float64)
    mels, lu = {}, {}
    for h, sl in PS.half_slices().items():
        mels[h] = quant(E.front(to_32k(y[sl])[None], 128)[0].numpy())
        lu[h] = float(SA.lufs(y[sl]))
    return mels, lu, 0.0


class Patched:
    """The ML session's builders with this module's input and paths, for one command. `stored(path)` -> the file that
    command's rows read, for the parity check; `saved` counts inputs and `worst` holds the largest difference met."""

    def __init__(self, stored):
        self.stored, self.saved, self.worst, self.checked, self.last = stored, 0, 0, 0, None

    def __enter__(self):
        from learn import direct_stems as DS

        self.DS, self.keep = DS, (DS.half_features, DS._save_npz)

        def features(y, logmel=None, lufs=None):
            self.last = y
            return half_features(y)

        def save_npz(path, **arrays):
            self.check(path)
            self.saved += 1
            self.keep[1](path, **arrays)

        DS.half_features, DS._save_npz = features, save_npz
        return self

    def __exit__(self, *_):
        self.DS.half_features, self.DS._save_npz = self.keep

    def check(self, path):
        from learn import pretrain_set as PS

        if PS.free_gb() < FLOOR_GB:
            raise SystemExit(f"free disk below {FLOOR_GB:.0f} GB")
        if self.saved % PARITY_EVERY:
            return
        mel, _, _ = self.keep[0](self.last)
        z = np.load(self.stored(path))
        a, b = ("mA", "mB") if "mA" in z.files else ("sA", "sB")
        dev = max(int(np.abs(mel[h].astype(int) - z[n].astype(int)).max()) for h, n in (("A", a), ("B", b)))
        self.worst, self.checked = max(self.worst, dev), self.checked + 1
        if dev > 1:
            raise SystemExit(f"{path}: the rebuilt audio differs from the stored input by {dev} grid steps")


def run(cmd, stored, shard, **fields):
    """One builder under `Patched`, with its record."""
    t0 = time.time()
    with Patched(stored) as p:
        cmd()
    rec = {"saved": p.saved, "parity_checked": p.checked, "parity_worst_grid_steps": p.worst, "minutes": (time.time() - t0) / 60,
           "shard": shard, **fields}
    path = front_root() / f"record-{fields['kind']}-{shard[0]}-of-{shard[1]}.json"
    path.write_text(json.dumps(rec, indent=1) + "\n")
    print(rec, flush=True)


def cmd_wide(a):
    from learn import pipeline_fix as P

    keep = P.wide_path, P.wide_draws
    stored = {}

    def path(i, k):
        p = wide_path(i, k)
        stored[str(p)] = keep[0](i, k)
        return p

    P.wide_path = path
    P.wide_draws = lambda *q, **kw: {i: d[:WIDE_K] for i, d in keep[1](*q, **kw).items()}
    try:
        run(lambda: P.cmd_build_wide(argparse.Namespace(shard=a.shard)), lambda p: stored[str(p)], a.shard, kind="wide")
    finally:
        P.wide_path, P.wide_draws = keep


def cmd_real(a):
    from learn import pipeline_fix as P

    keep = P.dfix_input_path, P.save
    stored = {}

    def path(unit, v):
        p = real_path(unit, v)
        stored[str(p)] = keep[0](unit, v)
        return p

    P.dfix_input_path = path
    P.save = lambda *_q, **_kw: None                    # `lends-*.json` stay the ML session's
    try:
        run(lambda: P.cmd_build_dfix_real(argparse.Namespace(shard=a.shard, reads_only=a.reads_only, captures=False)),
            lambda p: stored[str(p)], a.shard, kind="real", reads_only=a.reads_only)
    finally:
        P.dfix_input_path, P.save = keep


def cmd_clean(a):
    """Rung a's audio, the target at its gain in its mix, on W's rows: the stored `tgtl-cc` input's own signal."""
    from learn import bakeoff as B
    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import pipeline_fix as P
    from learn import trusted_data as T

    e = P.require("phase_3")
    croot, _, rend, _, _ = P.recipe_inputs(pin=e.get("phase_3_doubles"))
    built = T.rows_of(croot, CB.STAGE, "build")
    rows, _ = B.plugin_set()
    k, n = a.shard
    stored = {str(clean_path(r["i"])): P.input_path(P.DATA, r["i"], P.RUNG_KINDS["a"]) for r in rows}

    def build():
        for r in rows[k::n]:
            i = r["i"]
            if clean_path(i).exists():
                continue
            rw = rend[i]
            y = np.asarray(G.read_flac(T.flac_path(croot, CB.STAGE, i, "target"), rw["target"]["scale"], rw["target"]["sha256"]),
                           np.float64)
            f, lu, _ = DS.half_features(y * 10 ** (built[i]["gains_db"]["ga"] / 20))
            DS._save_npz(clean_path(i), sA=f["A"], sB=f["B"], lufs=[lu["A"], lu["B"]])

    run(build, lambda p: stored[str(p)], a.shard, kind="clean")


def cmd_amp(a):
    """A unit's amp track with no backing, at the level of its stored `real_input_path` or `goat_input_path` input."""
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import pipeline_fix as P

    k, n = a.shard
    units = P.dfix_units()
    stored_of = {str(amp_path(u)): P.real_input_path(u) if kind == "bks" else P.goat_input_path(u) for u, kind, _ in units}

    def build():
        for u, _, prt in units[k::n]:
            if amp_path(u).exists():
                continue
            ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
            g = DE.inference_gain_db(ref, float(np.load(stored_of[str(amp_path(u))])["target"]))
            f, lu, _ = DS.half_features(DE.mono(ref) * 10 ** (g / 20))
            DS._save_npz(amp_path(u), sA=f["A"], sB=f["B"], lufs=[lu["A"], lu["B"]])

    run(build, lambda p: stored_of[str(p)], a.shard, kind="amp")


def shard(s):
    k, n = s.split("/")
    return int(k), int(n)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("clean", cmd_clean), ("wide", cmd_wide), ("real", cmd_real), ("amp", cmd_amp)):
        s = sub.add_parser(name)
        s.add_argument("--shard", type=shard, default=(0, 1))
        if name == "real":
            s.add_argument("--reads-only", action="store_true")
        s.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
