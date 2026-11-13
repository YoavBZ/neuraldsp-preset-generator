"""R1 Amendment 3, the part-matched DIs (`docs/full-controls-plan.md`, "R1 in detail"; ledger `pipeline-fix`
`phase_r1_a3`): the listener heard the first page and found it can't compare. The songs' parts are mostly single-note
solos and riffs, while every arm played A1's two stock DIs (strummed chords, and one held note), in another register.
So each song's arms play the two DI segments from the trusted pool that play most like its part. The same pitch
tracker (pYIN) runs on both sides: on the song's stem, the half the page plays, and on every 4.5-s segment of the pool's
DIs. The match is by register (the voiced pitch's median and its 10th and 90th percentiles), texture (the voiced share
of the active frames: single notes read high, chords low) and density (onsets a second).

    $TORCH_PY -m learn.r1_di di-pool --shard 0/3      # pYIN on every trusted DI file (librosa; zero renders)
    $TORCH_PY -m learn.r1_di di-song                  # the same on each song's stem, half A
    $TORCH_PY -m learn.r1_di di-calibrate             # E1e's stem-to-DI offsets and spreads, by class (the review)
    $TORCH_PY -m learn.r1_di di-match                 # four candidates per song, distinct performances -> candidates.json
    .venv/bin/python -m learn.r1_di di-check-page     # the user's DI check on the candidates not checked before
    .venv/bin/python -m learn.r1_di di-final --store F   # the two nearest kept per song -> r1/matched-dis.json

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
CANDIDATES = 4                       # the nearest four per song go to the DI check; the best two kept are played
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


FEATS = ("median", "p10", "p90", "voiced", "log2_onsets")
SPREAD_FLOOR = {"median": 0.5, "p10": 0.5, "p90": 0.5, "voiced": 0.05, "log2_onsets": 0.15}


def vec(f):
    """A features record -> {feature: value} on FEATS (onsets as log2, floored at 0.2 a second)."""
    import math

    return {"median": f["median"], "p10": f["p10"], "p90": f["p90"], "voiced": f["voiced"],
            "log2_onsets": math.log2(max(f["onset_rate"], 0.2))}


def calibration(pairs):
    """pairs: [(stem features, DI features)] of one class -> {feature: (median offset stem - DI, robust spread)}: the
    spread is 1.4826 x the offsets' median absolute deviation, floored (SPREAD_FLOOR), so an octave flip on a few pairs
    doesn't widen it and a feature the stem reads badly weighs little."""
    import statistics as st

    out = {}
    for f in FEATS:
        d = [vec(a)[f] - vec(b)[f] for a, b in pairs]
        med = st.median(d)
        mad = st.median(abs(x - med) for x in d)
        out[f] = (med, max(1.4826 * mad, SPREAD_FLOOR[f]))
    return out


def cal_distance(song, seg, cal):
    """The declared match distance after the calibration (Amendment 3, the review): the song's features moved into the DI
    domain by the class's median offsets, then each feature's gap in units of its spread, summed."""
    a, b = vec(song), vec(seg)
    return sum(abs(a[f] - cal[f][0] - b[f]) / cal[f][1] for f in FEATS)


def pick(song, segs, k=2, dist=None):
    """The k nearest segments on distinct source performances (`di`, the review: distinct files can cut one take).
    segs: [{di, file, start, ...features}] -> [seg + distance]."""
    dist = dist or distance
    ranked = sorted(({**s, "distance": dist(song, s)} for s in segs), key=lambda s: (s["distance"], s["di"], s["start"]))
    out, used = [], set()
    for s in ranked:
        if s["di"] not in used:
            out.append(s)
            used.add(s["di"])
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


def cmd_calibrate(_args):
    """The review's calibration, zero renders: E1e's 770 items, each stem's half A against its own DI over the same
    span, by class -> di-match/calibration.json (and the effects-off subset beside)."""
    import argparse as AP
    import pathlib

    import numpy as np

    from learn import cc_build as CB
    from learn import fx_t0 as T0
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    P.require(PHASE)
    plan = {x["i"]: x for x in CB.load_plan(AP.Namespace(out=None, smoke=False))["examples"]}
    its, _ = T0.items()
    h = PS.half_slices()["A"]
    a0, a1 = h.start / PS.SR, h.stop / PS.SR
    rows = []
    for m, it in enumerate(its):
        x = plan[it["i"]]
        stem = np.load(pathlib.Path(T0.root()) / "e1e" / "audio" / f"{it['i']:07d}.npz")["stem"]
        di_path = pathlib.Path(x["session_dir"]) / pathlib.PurePosixPath(x["di"]).name
        start = float(x["section"].rsplit("@", 1)[1])
        di = PS.load_mono(str(di_path), PS.SR, start + a0, a1 - a0)
        fs = seg_features(*track(np.asarray(stem, np.float64)[h], PS.SR)[:4], 0.0, SEG_S, HOP / SR_PT, min_active=0.0)
        fd = seg_features(*track(di, PS.SR)[:4], 0.0, SEG_S, HOP / SR_PT, min_active=0.0)
        lab = T0.labels(it["settings"])
        rows.append({"i": it["i"], "cls": x["cls"], "stem": fs, "di": fd,
                     "effects_off": all(lab[k] == 0 for k in ("ron", "don", "ton"))})
        if m % 100 == 0:
            print(f"calibrate {m + 1}/{len(its)}", flush=True)
    ok = [r for r in rows if r["stem"] and r["di"]]
    rep = {"phase": PHASE, "items": len(rows), "usable": len(ok), "by_class": {}, "effects_off": {}}
    for c in ("clean", "crunch"):
        pc = [(r["stem"], r["di"]) for r in ok if r["cls"] == c]
        rep["by_class"][c] = {"n": len(pc), "cal": calibration(pc)}
        po = [(r["stem"], r["di"]) for r in ok if r["cls"] == c and r["effects_off"]]
        if len(po) >= 10:
            rep["effects_off"][c] = {"n": len(po), "cal": calibration(po)}
    rep["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(out_dir() / "calibration.json", rep)
    P.save(out_dir() / "calibration-rows.json", {"rows": rows})
    print(json.dumps({c: v for c, v in rep["by_class"].items()}, indent=1))


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
    cal = json.loads((out_dir() / "calibration.json").read_text())["by_class"]
    from learn import r1_ear as R

    cls = {x["song"]: x["cls"] for x in json.loads((R.ear_dir() / "plan.json").read_text())["songs"]}
    out = {}
    for s, f in songs.items():
        c = {k: tuple(v) for k, v in cal[cls[s]]["cal"].items()}
        best = pick(f, segs, k=CANDIDATES, dist=lambda a, b, c=c: cal_distance(a, b, c))
        out[s] = {"song": f, "cls": cls[s], "dis": [{"di": f"{b['di']}@{b['start']:.1f}", "source": b["di"],
                                                    "di_path": b["file"],
                                       "start_s": round(b["start"] - LEAD_S, 3), "set": b["set"],
                                       "features": {k: b[k] for k in ("voiced", "median", "p10", "p90", "onset_rate")},
                                       "distance": b["distance"]} for b in best]}
        print(s, "->", [(x["di"], round(x["distance"], 2)) for x in out[s]["dis"]], flush=True)
    P.save(out_dir() / "candidates.json", {"phase": PHASE, "segments": len(segs), "songs": out,
                                           "time": time.strftime("%Y-%m-%d %H:%M:%S")})


CHECK_INTRO = ("guitar recordings (DIs), each on its own, looping. Each will stand in for a song's guitar part on the "
               "next R1 page. Drop one if it is tuned too low or played too metal for a clean or crunch song part, or if it "
               "is processed, as on the earlier DI check. Only Keep stays in, so Not sure counts as dropped. All are set to "
               "the same loudness, and a tap moves on to the next one. ")


def checked_keep():
    """The DI files the user's DI check (`di_scope`) already kept."""
    from learn import di_scope as DSC

    v = DSC.verdicts() or {}
    v = v.get("verdicts", v) if isinstance(v, dict) else {}
    return {di for di, x in v.items() if x == "keep"}


def check_cards(cands, kept):
    """The DI check's cards: each source among the songs' candidates the earlier check didn't keep, once, on its best
    candidate (the least distance). -> [{source, di_path, start_s, set}] sorted by source."""
    best = {}
    for v in cands.values():
        for d in v["dis"]:
            if d["source"] in kept:
                continue
            if d["source"] not in best or d["distance"] < best[d["source"]]["distance"]:
                best[d["source"]] = d
    return [best[k] for k in sorted(best)]


def final_pick(cands, verdict, kept, k=2):
    """The two nearest candidates per song whose source is kept (the earlier check or this one). -> {song: [dis]} or a
    refusal naming the songs left short."""
    out, short = {}, []
    for s, v in cands.items():
        ok = [d for d in sorted(v["dis"], key=lambda d: d["distance"]) if d["source"] in kept or verdict.get(d["source"]) == "keep"]
        out[s] = ok[:k]
        if len(ok) < k:
            short.append(s)
    if short:
        raise SystemExit(f"fewer than {k} kept candidates for {short}: widen CANDIDATES and check again")
    return out


def cmd_check_page(_args):
    """The DI check page -> di-match/check/{page.html, artifact.html, key.json}; refuses over a key."""
    from learn import build_data_review as BDR
    from learn import di_scope as DSC
    from learn import ear_eat as EE
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import scope_page as SP

    P.require(PHASE)
    d = out_dir() / "check"
    if (d / "key.json").exists():
        raise SystemExit(f"{d / 'key.json'} exists: a rebuild hides the stored answers")
    d.mkdir(parents=True, exist_ok=True)
    cands = json.loads((out_dir() / "candidates.json").read_text())["songs"]
    cards = check_cards(cands, checked_keep())
    ids = [hashlib.sha256(f"r1-di|{c['source']}".encode()).hexdigest()[:8] for c in cards]
    build = hashlib.sha256(json.dumps(ids).encode()).hexdigest()[:12]
    clips, items = {}, []
    for i, c in zip(ids, cards):
        y = PS.load_mono(c["di_path"], PS.SR, c["start_s"], 10.0)
        y, gain, _, cut = BDR.level_clip(y)
        clips[i] = SP.encode(y, d / "aac-cache")
        items.append({"id": i, "di": c["source"], "set": c["set"], "di_path": c["di_path"], "start_s": c["start_s"]})
    page = DSC.page_html(ids, clips, build).replace(f"{len(ids)} " + DSC.INTRO, f"{len(ids)} " + CHECK_INTRO)
    if CHECK_INTRO not in page:
        raise SystemExit("the DI check's intro didn't take")
    shown = DSC.leaks(page) + [w for w in ("goat", "GOAT", "BKS", "item_") if w in page.split('<script id="clips"')[0]]
    if shown:
        raise SystemExit(f"the page names {shown}")
    (d / "page.html").write_text(page)
    (d / "key.json").write_text(json.dumps({"phase": PHASE, "build": build, "items": items,
                                            "time": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1))
    print(f"R1 DI CHECK PAGE: {len(items)} cards, build {build} -> {d / 'page.html'}")


def cmd_final(args):
    """The stored answers -> r1/matched-dis.json: the two nearest kept candidates per song."""
    import pathlib

    from learn import di_scope as DSC
    from learn import ear_eat as EE
    from learn import pipeline_fix as P

    P.require(PHASE)
    d = out_dir() / "check"
    key = json.loads((d / "key.json").read_text())
    ex = EE.stored_answers(pathlib.Path(args.store).read_text())
    if ex.get("build") != key["build"]:
        raise SystemExit(f"{args.store}: build {ex.get('build')}, the page's is {key['build']}")
    verdict = DSC.di_verdicts(ex.get("answers") or {}, key["items"])
    if len(verdict) < len(key["items"]):
        raise SystemExit(f"{len(verdict)} of {len(key['items'])} cards answered")
    cands = json.loads((out_dir() / "candidates.json").read_text())["songs"]
    out = final_pick(cands, verdict, checked_keep())
    P.save(R1_MATCHED(), {"phase": PHASE, "check_build": key["build"], "verdicts": verdict,
                          "songs": {s: {"song": cands[s]["song"], "dis": v} for s, v in out.items()},
                          "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    for s, v in out.items():
        print(s, "->", [(x["di"], round(x["distance"], 2)) for x in v])


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
    sub.add_parser("di-calibrate").set_defaults(fn=cmd_calibrate)
    sub.add_parser("di-match").set_defaults(fn=cmd_match)
    sub.add_parser("di-check-page").set_defaults(fn=cmd_check_page)
    f = sub.add_parser("di-final")
    f.add_argument("--store", required=True)
    f.set_defaults(fn=cmd_final)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
