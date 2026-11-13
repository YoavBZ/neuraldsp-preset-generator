"""R1 Amendment 3, the part-matched DIs (`docs/full-controls-plan.md`, "R1 in detail"; ledger `pipeline-fix`
`phase_r1_a3`): the listener heard the first page and found it can't compare. The songs' parts are mostly single-note
solos and riffs, while every arm played A1's two stock DIs (strummed chords, and one held note), in another register.
So each song's arms play the two DI segments from the trusted pool that play most like its part. The same pitch
tracker (pYIN) runs on both sides: on the song's stem, the half the page plays, and on every 4.5-s segment of the pool's
DIs. The match is by register (the voiced pitch's median and its 10th and 90th percentiles), texture (the voiced share
of the active frames: single notes read high, chords low) and density (onsets a second).

    $TORCH_PY -m learn.r1_di di-pool --shard 0/3      # pYIN on every trusted DI file (librosa; zero renders)
    $TORCH_PY -m learn.r1_di di-song                  # the same on each song's stem, half A
    $TORCH_PY -m learn.r1_di di-match                 # two segments per song, on distinct DI files -> r1/matched-dis.json

The pure parts (the segment features, the distance and the pick) are unit-tested.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import types

PHASE = "phase_r1_a3"
SR_PT = 22050                        # pYIN's rate
FRAME, HOP = 2048, 512
FMIN, FMAX = 80.0, 1500.0            # the guitar's range (E2 is 82 Hz): below it, a stem's pitch is the bass's bleed
SEG_S, SEG_HOP_S = 4.5, 0.5          # the page's half A, on a half-second hop
LEAD_S = 1.0                         # half A starts 1.0 s into the rendered window
ACTIVE_DB, MIN_ACTIVE = 30.0, 0.8    # a frame is active within 30 dB of the file's loudest; a segment 80% active
W_P10_P90, W_VOICED, W_ONSETS = 0.5, 8.0, 2.0   # the distance: semitones on the median, half on each tail, 8 per unit
#                                                of voiced share (0.1 = 0.8 st), 2 per octave of onset rate


def _lzma_stub():
    """This Python has no _lzma; librosa's imports (pooch, joblib) only need the names."""
    if "lzma" in sys.modules:
        return
    try:
        import lzma  # noqa: F401
        return
    except ImportError:
        pass
    m = types.ModuleType("lzma")
    io = {k: (lambda self, *a, **kw: None) for k in ("read", "write", "seek", "tell", "close", "flush", "readline")}
    for k in ("LZMAFile", "LZMACompressor", "LZMADecompressor"):
        setattr(m, k, type(k, (), dict(io)))
    m.LZMAError = type("LZMAError", (Exception,), {})
    for i, k in enumerate(("FORMAT_AUTO", "FORMAT_XZ", "FORMAT_ALONE", "FORMAT_RAW", "CHECK_NONE", "CHECK_CRC64")):
        setattr(m, k, i)
    sys.modules["lzma"] = m


def out_dir():
    from learn import r1_ear as R

    return R.ear_dir() / "di-match"


# --- the pure parts -------------------------------------------------------------------------------------------------------

def seg_features(midi, voiced, active, onsets_s, a, b, hop_s, min_active=MIN_ACTIVE):
    """One segment's features from frame arrays (pitch in MIDI or NaN, voiced and active flags, frame times = i * hop_s)
    and onset times. -> {active, voiced, median, p10, p90, onset_rate} or None when under MIN_ACTIVE or unvoiced."""
    import numpy as np

    i0, i1 = int(round(a / hop_s)), int(round(b / hop_s))
    act = np.asarray(active[i0:i1], bool)
    if not len(act) or not act.any() or act.mean() < min_active:
        return None
    v = np.asarray(voiced[i0:i1], bool) & act
    m = np.asarray(midi[i0:i1], float)[v]
    m = m[np.isfinite(m)]
    if len(m) < 5:
        return None
    on = np.asarray(onsets_s, float)
    return {"active": float(act.mean()), "voiced": float(v.sum() / act.sum()), "median": float(np.median(m)),
            "p10": float(np.percentile(m, 10)), "p90": float(np.percentile(m, 90)),
            "onset_rate": float(((on >= a) & (on < b)).sum() / (b - a))}


def distance(song, seg):
    """The declared match distance (semitones, with texture and density converted)."""
    import math

    return (abs(song["median"] - seg["median"]) + W_P10_P90 * (abs(song["p10"] - seg["p10"]) + abs(song["p90"] - seg["p90"]))
            + W_VOICED * abs(song["voiced"] - seg["voiced"])
            + W_ONSETS * abs(math.log2(max(song["onset_rate"], 0.2) / max(seg["onset_rate"], 0.2))))


def pick(song, segs, k=2):
    """The k nearest segments on distinct DI files. segs: [{file, start, ...features}] -> [seg + distance]."""
    ranked = sorted(({**s, "distance": distance(song, s)} for s in segs), key=lambda s: (s["distance"], s["file"], s["start"]))
    out, used = [], set()
    for s in ranked:
        if s["file"] not in used:
            out.append(s)
            used.add(s["file"])
        if len(out) == k:
            break
    return out


# --- the measures ---------------------------------------------------------------------------------------------------------

def track(y, sr):
    """pYIN and onsets on a mono signal. -> (midi per frame or NaN, voiced, active, onset times s, frame hop s)."""
    _lzma_stub()
    import librosa
    import numpy as np

    x = librosa.resample(np.asarray(y, np.float64), orig_sr=sr, target_sr=SR_PT)
    f0, vflag, _ = librosa.pyin(x, fmin=FMIN, fmax=FMAX, sr=SR_PT, frame_length=FRAME, hop_length=HOP)
    rms = librosa.feature.rms(y=x, frame_length=FRAME, hop_length=HOP)[0][:len(f0)]
    active = rms > rms.max() * 10 ** (-ACTIVE_DB / 20)
    on = librosa.onset.onset_detect(y=x, sr=SR_PT, hop_length=HOP, units="time")
    midi = np.where(np.isfinite(f0), librosa.hz_to_midi(np.where(np.isfinite(f0), f0, 1.0)), np.nan)
    return midi, vflag & active, active, on, HOP / SR_PT


def pool_files():
    """The trusted DI files the reads train and judge on (C3r's read units: GOAT, cap1, BKS, n12 and the panel). Their
    DI files passed the data checks, and the library's the user's by-ear DI check."""
    from learn import full_controls_c3r as R3

    files = {}
    for r in R3.read_units(R3.state()):
        files.setdefault(r["prt"]["di_path"], {"di": r["prt"]["di"], "set": r["set"]})
    return dict(sorted(files.items()))


def cmd_pool(args):
    import numpy as np

    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    P.require(PHASE)
    k, n = args.shard
    d = out_dir() / "pool"
    d.mkdir(parents=True, exist_ok=True)
    files = list(pool_files().items())
    t0 = time.time()
    for m, (path, meta) in enumerate(files[k::n]):
        p = d / f"{hashlib.sha1(path.encode()).hexdigest()[:16]}.npz"
        if p.exists():
            continue
        y = PS.load_mono(path, PS.SR)
        midi, voiced, active, on, hop = track(y, PS.SR)
        np.savez(p, midi=midi, voiced=voiced, active=active, onsets=on, hop=np.array([hop]),
                 path=np.array([path]), di=np.array([meta["di"]]), set=np.array([meta["set"]]),
                 seconds=np.array([len(y) / PS.SR]))
        if m % 10 == 0:
            print(f"pool {k}/{n}: {m + 1} files, {time.time() - t0:.0f} s", flush=True)
    print(f"DI POOL DONE {k}/{n}", flush=True)


def cmd_song(_args):
    import numpy as np

    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import r1_ear as R

    P.require(PHASE)
    h = PS.half_slices()["A"]
    out = {}
    for s in R.songs():
        stem = np.load(R.ear_dir() / s / "window.npz")["stem"]
        midi, voiced, active, on, hop = track(np.asarray(stem, np.float64)[h], PS.SR)
        f = seg_features(midi, voiced, active, on, 0.0, SEG_S, hop, min_active=0.0)   # the whole half: the page's clip
        out[s] = f
        print(s, json.dumps({k: round(v, 2) for k, v in f.items()}), flush=True)
    P.save(out_dir() / "songs.json", {"phase": PHASE, "songs": out, "time": time.strftime("%Y-%m-%d %H:%M:%S")})


def cmd_match(_args):
    import numpy as np

    from learn import pipeline_fix as P

    P.require(PHASE)
    songs = json.loads((out_dir() / "songs.json").read_text())["songs"]
    segs = []
    for p in sorted((out_dir() / "pool").glob("*.npz")):
        z = np.load(p)
        hop, dur, path = float(z["hop"][0]), float(z["seconds"][0]), str(z["path"][0])
        a = LEAD_S
        while a + SEG_S <= dur - 0.25:
            f = seg_features(z["midi"], z["voiced"], z["active"], z["onsets"], a, a + SEG_S, hop)
            if f:
                segs.append({"file": path, "di": str(z["di"][0]), "set": str(z["set"][0]), "start": round(a, 3), **f})
            a += SEG_HOP_S
    out = {}
    for s, f in songs.items():
        best = pick(f, segs)
        out[s] = {"song": f, "dis": [{"di": f"{b['di']}@{b['start']:.1f}", "di_path": b["file"],
                                       "start_s": round(b["start"] - LEAD_S, 3), "set": b["set"],
                                       "features": {k: b[k] for k in ("voiced", "median", "p10", "p90", "onset_rate")},
                                       "distance": b["distance"]} for b in best]}
        print(s, "->", [(x["di"], round(x["distance"], 2)) for x in out[s]["dis"]], flush=True)
    P.save(R1_MATCHED(), {"phase": PHASE, "segments": len(segs), "songs": out,
                          "time": time.strftime("%Y-%m-%d %H:%M:%S")})


def R1_MATCHED():
    from learn import r1_ear as R

    return R.ear_dir() / "matched-dis.json"


def shard(s):
    k, n = (int(x) for x in s.split("/"))
    return k, n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("di-pool")
    p.add_argument("--shard", type=shard, default=(0, 1))
    p.set_defaults(fn=cmd_pool)
    sub.add_parser("di-song").set_defaults(fn=cmd_song)
    sub.add_parser("di-match").set_defaults(fn=cmd_match)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
