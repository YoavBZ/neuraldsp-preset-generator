"""The window count, W0 (`docs/window-count-plan.md`, ledger `preset-ladder` `phase_wc`).

How often a song offers a 10-s window where the requested guitar part plays and no other guitar does, counted by truth
from multitracks. CPU only: no render, no separation, no training, no listening. It reads no preset and chooses
nothing. Descriptive: it cannot stop the scoped route (about 31% of the locator's songs have one guitar part).

Two sets, each read alone and pooled, clustered by band:
- `locator`: the part locator's development sessions outside every held band (`capture_labels.HELD_BANDS`), with the
  locator's own 100-ms envelopes (`learn/locator_truth.py`); every guitar track the replay's no-other-guitar backing
  left out counts as another guitar (acoustic ones and the keyboard player's included).
- `medleydb`: set 6's songs outside the reserve's bands, truth from MedleyDB's activation-confidence annotations
  (every stem, acoustic guitars included) OR'd with the locator's envelope rule on the electric guitars' raw tracks.

    .venv/bin/python -m learn.window_count run --limit 3      # times the first 3 songs (W0's runtime)
    .venv/bin/python -m learn.window_count run                # every song, both sets; once
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import pathlib
import re
import statistics
import subprocess
import time

HOP_S = 0.1                 # the locator's 100-ms activity frames
WIN, STEP = 100, 10         # 10-s windows on a 1-s step, in frames (the search's section length)
ACTIVE_SHARE = 0.6          # the target plays in at least 60% of the window's frames (the locator's rule)
ACT_DB = 30.0               # a DI is active within 30 dB of its loudest frame (the locator's rule)
NODI_ACT_DB = 20.0          # an amp, mic or raw track within 20 dB of its loudest frame (the locator's rule)
SILENT_DB = -240.0
GAP = WIN // STEP           # windows apart for two windows not to overlap

STRICT = 0.0                # deciding: the other guitars inactive in 100% of the window's frames (C3)
TOLERANT = 0.1              # side count: inactive in at least 90% of them
CURVE = (0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0)     # the other guitars' allowed active share; 1.0 = no condition

WIDE, RARE = 0.5, 0.2       # the user's two shares (2026-11-21, "Agree")

MDB_CONF = 0.5              # MedleyDB's activation confidence: active at or above 0.5
MDB_ELECTRIC = ("clean electric guitar", "distorted electric guitar")
MDB_COMMIT = "537bb7bad0601fc58e4fff8404f71658b86ef60e"
MDB_ANNOT = "medleydb/data/Annotations/Activation_Confidence/{ver}/{song}_ACTIVATION_CONF.lab"
MDB_ANNOT_VERSIONS = ("v2", "original")          # the newer first

SETS = ("locator", "medleydb")
POOL = "pool"

W0_TABLE = {
    "W-wide": {"rule": f"lower end of the 90% interval at {WIDE} or above",
               "reading": "most songs offer a window where the part plays with no other guitar",
               "next": "to the parent and the user: the scoped route can be the main path, with today's path as the "
                       "fallback; W1 (the detector) still needs its redesigned validation and its own review"},
    "W-some": {"rule": f"the rest (the interval reaches below {WIDE} and above {RARE})",
               "reading": "a share of songs offer such a window",
               "next": "to the parent and the user, with the split by scope and role: the route is a branch beside "
                       "today's path; W1 only on the user's go after its own review"},
    "W-rare": {"rule": f"upper end of the 90% interval at {RARE} or below",
               "reading": "few songs offer such a window (out of reach on this set: about 31% of the locator's songs "
                          "are single-guitar)",
               "next": "to the parent and the user: the scoped route alone is not a product"},
    "incomplete": {"rule": "no interval (fewer than 2 bands)", "reading": "not readable", "next": "to the parent"},
}


# --- pure helpers (tests/test_window_count.py) ----------------------------------------------------------------------

def windows(n_frames, win=WIN, step=STEP):
    import numpy as np

    return np.arange(0, max(n_frames - win, 0) + 1, step)


def win_mean(x, starts, win=WIN):
    import numpy as np

    c = np.concatenate([[0.0], np.cumsum(np.asarray(x, np.float64))])
    return (c[starts + win] - c[starts]) / win


def pad(x, n, value=SILENT_DB):
    import numpy as np

    x = np.asarray(x)[:n]
    return np.pad(x, (0, n - len(x)), constant_values=value)


def active(db, n, rel_db):
    """A track's activity on the song's n frames: within rel_db of its own loudest frame (silence padded)."""
    d = pad(db, n)
    return d > d.max() - rel_db


def conf_frames(times, conf, n, hop=HOP_S, thr=MDB_CONF):
    """MedleyDB's activation confidence onto the 100-ms frames: a frame is active when any annotation sample inside it
    reads at least thr. times, conf: 1-D arrays of one stem's column."""
    import numpy as np

    out = np.zeros(n, bool)
    idx = np.floor(np.asarray(times, np.float64) / hop + 1e-9).astype(int)
    ok = (idx >= 0) & (idx < n) & (np.asarray(conf, np.float64) >= thr)
    out[idx[ok]] = True
    return out


def alone(target, others, starts, tol=STRICT, share=ACTIVE_SHARE):
    """Per window: the target active in at least `share` of the frames and the union of the other guitars active in
    at most `tol` of them (tol 0: in none). target: bool[n]; others: list of bool[n]."""
    import numpy as np

    t = win_mean(target, starts) >= share - 1e-12
    if not others:
        return t
    u = np.zeros(len(target), bool)
    for o in others:
        u |= np.asarray(o, bool)
    return t & (win_mean(u, starts) <= tol + 1e-12)


def max_disjoint(hit, gap=GAP):
    """The most windows that pairwise do not overlap (starts at least `gap` windows apart); greedy is optimal here."""
    n, last = 0, None
    for i, h in enumerate(hit):
        if h and (last is None or i - last >= gap):
            n, last = n + 1, i
    return n


def same_part_base(name):
    """A double's base part: a Cambridge "DT" double is the same part (locator_truth's rule, for the side count)."""
    return re.sub(r"dt$", "", re.sub(r"\s+", "", str(name)).lower())


def part_counts(target, others, others_same, starts):
    """One target part's counts. others: every other guitar (deciding); others_same: less the part's own doubles."""
    a = alone(target, others, starts, STRICT)
    tol = alone(target, others, starts, TOLERANT)
    same = alone(target, others_same, starts, STRICT)
    tw = alone(target, [], starts)
    return {"windows": int(len(starts)), "target_windows": int(tw.sum()),
            "alone": int(a.sum()), "alone_90": int(tol.sum()), "alone_same_part": int(same.sum()),
            "offers": bool(a.any()), "offers_90": bool(tol.any()), "offers_same_part": bool(same.any()),
            "offers_3": max_disjoint(a) >= 3, "disjoint": max_disjoint(a),
            "curve": {str(c): bool(alone(target, others, starts, c).any()) for c in CURVE},
            "n_other_guitars": len(others), "n_other_guitars_same_part": len(others_same)}


def clustered(rows):
    """rows: [(band, song, value)] -> the mean of band means (songs averaged inside their band, each song once) with
    the 90% cluster t interval over bands, and the song-weighted mean beside (`pipeline_fix.clustered`)."""
    from learn import pipeline_fix as PF

    r = PF.clustered(rows)
    return {"mean": r["mean"], "lo90": r["lo90"], "hi90": r["hi90"], "bands": r["clusters"],
            "songs": r["parts"], "song_weighted": r.get("part_weighted"),
            "per_band": r.get("per_cluster", {}), "leave_one_band_out": r.get("leave_one_out", {})}


def w0_code(lo, hi, wide=WIDE, rare=RARE):
    if lo is None or hi is None:
        return "incomplete"
    if lo >= wide - 1e-12:
        return "W-wide"
    if hi <= rare + 1e-12:
        return "W-rare"
    return "W-some"


def song_rows(songs, key="offers", parts_filter=None):
    """[(band, song id, share of the song's kept parts with `key`)] for songs with at least one kept part."""
    out = []
    for s in songs:
        ps = [p for p in s["parts"] if parts_filter is None or parts_filter(p)]
        if ps:
            out.append((s["band"], s["id"], statistics.fmean(1.0 if (p["counts"][key] if key in p["counts"]
                                                                       else p["counts"]["curve"][key]) else 0.0
                                                              for p in ps)))
    return out


def summarise(songs, key="offers", parts_filter=None):
    r = clustered(song_rows(songs, key, parts_filter))
    r["code"] = w0_code(r["lo90"], r["hi90"])
    return r


def scope_of(p):
    """The known-scope split (C4): in scope (clean or crunch), high-gain, or unlabelled; MedleyDB's own clean or
    distorted label beside (it does not tell crunch from high-gain)."""
    g = p.get("gain_class")
    if g in ("clean", "crunch"):
        return "in-scope"
    if g == "high-gain":
        return "high-gain"
    if p.get("mdb_label"):
        return "mdb-" + ("clean" if p["mdb_label"] == "clean electric guitar" else "distorted")
    return "unlabelled"


def report(songs_by_set):
    """Every declared reading on {set: [song]}, each set alone and pooled (POOL)."""
    sets = dict(songs_by_set)
    sets[POOL] = [s for k in SETS for s in songs_by_set.get(k, [])]
    out = {}
    for name, songs in sets.items():
        r = {"deciding": summarise(songs),
             "side_90": summarise(songs, "offers_90"),
             "side_same_part": summarise(songs, "offers_same_part"),
             "side_3_disjoint": summarise(songs, "offers_3"),
             "curve": {str(c): summarise(songs, str(c)) for c in CURVE},
             "by_scope": {k: summarise(songs, parts_filter=lambda p, k=k: scope_of(p) == k)
                          for k in ("in-scope", "high-gain", "unlabelled", "mdb-clean", "mdb-distorted")},
             "by_role": {str(k): summarise(songs, parts_filter=lambda p, k=k: p.get("role") == k)
                         for k in ("lead", "rhythm", None)},
             "single_guitar_songs": sum(1 for s in songs if s["single_guitar"]),
             "songs": len(songs), "bands": len({s["band"] for s in songs}),
             "parts": sum(len(s["parts"]) for s in songs),
             "parts_offering": sum(p["counts"]["offers"] for s in songs for p in s["parts"])}
        if name == "medleydb":
            r["side_annotation_only"] = summarise(
                [dict(s, parts=[dict(p, counts=p["counts_annotation_only"]) for p in s["parts"]])
                 for s in songs if all(p.get("counts_annotation_only") for p in s["parts"])])
            r["side_no_bleed"] = summarise([s for s in songs if s.get("has_bleed") != "yes"])
        out[name] = r
    out["headline"] = {"code": out[POOL]["deciding"]["code"],
                       "per_set": {k: out[k]["deciding"]["code"] for k in SETS if k in out}}
    return out


# --- the locator set ------------------------------------------------------------------------------------------------

def locator_sessions(held=None):
    from learn import capture_labels as CL
    from learn import locator_truth as T

    held = set(CL.HELD_BANDS if held is None else held)
    return [s for s in T.sessions() if s["band"] not in held]


def locator_labels():
    """{(song, part): {role, gain_class}} from docs/part-locator-truth.json; a DT double takes its part's labels."""
    from learn import locator_truth as T

    doc = json.loads(T.TRUTH.read_text())
    out = {}
    for s in doc["songs"]:
        by = {q["part"]: q for q in s["parts"]}
        for q in s["parts"]:
            base = by.get(re.sub(r"\s*DT$", "", q["part"]), q)
            out[(s["song"], q["part"])] = {"role": base["role"], "gain_class": base["gain_class"],
                                           "character": base["character"], "keys_gtr": q["keys_gtr"]}
    return out


def locator_groups(s):
    """The session's guitars as the replay's no-other-guitar backing saw them: every track `data_cleaning.track_class`
    calls a guitar (acoustic and the keyboard player's included; never click or talkback), a non-DI track only when it
    is in the session's mix list, DIs always. -> (parts, unowned): parts {part: {"di", "tracks"}} for the locator's
    DI parts; unowned {key: [tracks]} for every other guitar track, grouped by `verify_tracks.guitar_part_key`; a track
    whose key is a locator part's goes to that part."""
    from learn import clean_di as CD
    from learn import data_cleaning as DC
    from learn import verify_tracks as V

    mixset = set(s["mix"])
    gtr = [f for f in s["files"] if DC.track_class(f) == "guitar" and not V.NON_MUSICAL.search(f)
           and (CD.is_guitar_di(f) or not mixset or f in mixset)]
    parts, keys = {}, {}
    for p in s["parts"]:
        tr = [t for t in (p["di"], p["ref"], *p["alts"]) if t]
        parts[p["part"]] = {"di": p["di"], "tracks": tr}
        for t in tr:
            keys[V.guitar_part_key(pathlib.PurePosixPath(t).name)] = p["part"]
    owned = {t for v in parts.values() for t in v["tracks"]}
    unowned = {}
    for f in gtr:
        if f in owned:
            continue
        k = V.guitar_part_key(pathlib.PurePosixPath(f).name)
        if k in keys:
            parts[keys[k]]["tracks"].append(f)
            continue
        unowned.setdefault(k, []).append(f)
    return parts, unowned


def locator_acts(s, db):
    """(n frames, {guitar: bool[n] activity}, parts) of one locator session: a locator part by its DI (ACT_DB), any
    other guitar by its tracks OR'd (a DI at ACT_DB, an amp or mic track at NODI_ACT_DB). db: {track: dB envelope}."""
    from learn import clean_di as CD

    n = max(len(db[m]) for m in s["mix"] if m in db)
    parts, unowned = locator_groups(s)
    acts = {}
    for name, g in parts.items():
        if g["di"] in db:
            acts["part:" + name] = active(db[g["di"]], n, ACT_DB)
    missing = []
    for k, tr in unowned.items():
        a = None
        for t in tr:
            if t not in db:
                missing.append(t)
                continue
            x = active(db[t], n, ACT_DB if CD.is_guitar_di(t) else NODI_ACT_DB)
            a = x if a is None else (a | x)
        if a is not None:
            acts["other:" + k] = a
    if missing:
        raise SystemExit(f"{s['song']}: no envelope for {missing}")
    return n, acts, parts


def locator_song(s, db, labels):
    """One locator session's parts and counts."""
    n, acts, parts = locator_acts(s, db)
    starts = windows(n)
    rows = []
    for name in parts:
        key = "part:" + name
        if key not in acts:
            continue
        others = [v for k, v in acts.items() if k != key]
        base = same_part_base(name)
        others_same = [v for k, v in acts.items() if k != key and same_part_base(k.split(":", 1)[1]) != base]
        lab = labels.get((s["song"], name), {})
        rows.append({"part": name, "role": lab.get("role"), "gain_class": lab.get("gain_class"),
                     "keys_gtr": lab.get("keys_gtr", False),
                     "counts": part_counts(acts[key], others, others_same, starts)})
    return {"set": "locator", "id": f"locator:{s['song']}", "song": s["song"], "band": s["band"],
            "source": s["source"], "length_s": round(n * HOP_S, 1), "single_guitar": len(acts) == 1,
            "guitars": sorted(acts), "parts": rows}


def locator_envelopes(s, cache_dir):
    """The locator's stored envelopes (learn/locator/env), plus this count's own for the guitar tracks they lack
    (cached under cache_dir)."""
    import numpy as np

    from learn import locator_truth as T

    z = np.load(T.ENV / f"{T._slug(s)}.npz")
    db = {k[4:]: z[k] for k in z.files if k.startswith("db::")}
    parts, unowned = locator_groups(s)
    need = sorted({t for v in parts.values() for t in v["tracks"]} | {t for v in unowned.values() for t in v}
                  | set(s["mix"]))
    need = [t for t in need if t not in db]
    if need:
        cache = cache_dir / f"{T._slug(s)}.npz"
        extra = {}
        if cache.exists():
            zz = np.load(cache)
            extra = {k: zz[k] for k in zz.files}
        todo = [t for t in need if t not in extra]
        for t in todo:
            path = T._path(s["root"], t)
            if path is None:
                raise SystemExit(f"{s['song']}: {t} not on disk")
            extra[t] = T._frames(path)[0]
        if todo:
            cache_dir.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(cache, **extra)
        db.update({t: extra[t] for t in need})
    return db


# --- the MedleyDB set -----------------------------------------------------------------------------------------------

def mdb_root(home):
    return home / "references/datasets-medleydb"


def mdb_sessions(home, held=None):
    from learn import capture_labels as CL

    held = set(CL.HELD_BANDS if held is None else held)
    inv = json.loads((mdb_root(home) / "inventory.json").read_text())
    keep = [s for s in inv["sessions"] if s["band"] not in held]
    return keep, [s["song"] for s in inv["sessions"] if s["band"] in held]


def mdb_annotation(home, song):
    """(version, git blob id, {stem: (times, conf)}) of the song's activation confidence, read from the local clone's
    git store at MDB_COMMIT (no download, no checkout change); (None, None, {}) when it has none."""
    import numpy as np

    repo = mdb_root(home) / "mdb-repo"
    for ver in MDB_ANNOT_VERSIONS:
        path = MDB_ANNOT.format(ver=ver, song=song)
        r = subprocess.run(["git", "-C", str(repo), "show", f"{MDB_COMMIT}:{path}"], capture_output=True, text=True)
        if r.returncode != 0:
            continue
        blob = subprocess.run(["git", "-C", str(repo), "rev-parse", f"{MDB_COMMIT}:{path}"], capture_output=True,
                              text=True, check=True).stdout.strip()
        rows = list(csv.reader(io.StringIO(r.stdout)))
        head, data = rows[0], np.array([[float(v) for v in row] for row in rows[1:] if row], np.float64)
        return ver, blob, {h.strip(): (data[:, 0], data[:, i]) for i, h in enumerate(head) if i > 0}
    return None, None, {}


def mdb_metadata(home, song):
    import yaml

    return yaml.safe_load((mdb_root(home) / f"mdb-repo/medleydb/data/Metadata/{song}_METADATA.yaml").read_text())


def mdb_guitar_stems(meta):
    """{stem id: {"instruments", "electric", "raws"}} of every stem whose instrument names a guitar (MedleyDB's
    clean or distorted electric, acoustic and lap steel guitars; not banjo or mandolin, which the replay's backing
    kept)."""
    out = {}
    for sid, st in sorted((meta.get("stems") or {}).items()):
        ins = st.get("instrument")
        ins = list(ins) if isinstance(ins, list) else [ins]
        if any("guitar" in str(i) for i in ins):
            raws = [r["filename"] for r in (st.get("raw") or {}).values()]
            out[sid] = {"instruments": ins, "electric": any(i in MDB_ELECTRIC for i in ins), "raws": raws,
                        "filename": st.get("filename")}
    return out


def mdb_acts(home, inv_s, cache_dir):
    """One MedleyDB song's guitar activity: {"n", "stems", "ann" (version, blob, columns), "env" (raw envelopes),
    "acts" (annotation OR raw rule), "acts_ann" (annotation only), "why" (stems with no truth)}."""
    import numpy as np
    import soundfile as sf

    from learn import locator_truth as T

    root = mdb_root(home)
    song = inv_s["song"]
    meta = mdb_metadata(home, song)
    stems = mdb_guitar_stems(meta)
    on_disk = {r["file"] for e in inv_s["eg_stems"] for r in e["raw"] if r.get("on_disk")}
    raw_dir = root / inv_s["dir"] / f"{song}_RAW"
    try:
        n = int(sf.info(str(root / inv_s["mix"])).duration / HOP_S)
    except Exception:                                   # noqa: BLE001  (an M4A mix: the raws' length instead)
        n = None
    ver, blob, ann = mdb_annotation(home, song)
    cache = cache_dir / f"{song}.npz"
    env = {}
    if cache.exists():
        zz = np.load(cache)
        env = {k: zz[k] for k in zz.files}
    todo = [r for sid, st in stems.items() if st["electric"] for r in st["raws"] if r in on_disk and r not in env]
    for r in todo:
        env[r] = T._frames(raw_dir / r)[0]
    if todo:
        cache_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, **env)
    if n is None:
        n = max(len(v) for v in env.values())
    acts, acts_ann, why = {}, {}, []
    for sid, st in stems.items():
        a_ann = conf_frames(*ann[sid], n) if sid in ann else None
        a_raw = None
        for r in st["raws"]:
            if r in env:
                x = active(env[r], n, NODI_ACT_DB)
                a_raw = x if a_raw is None else (a_raw | x)
        if a_ann is None and a_raw is None:
            why.append(f"{sid} ({'/'.join(map(str, st['instruments']))}): no annotation and no raw on disk")
            continue
        acts[sid] = a_ann if a_raw is None else (a_raw if a_ann is None else (a_ann | a_raw))
        if a_ann is not None:
            acts_ann[sid] = a_ann
    return {"n": n, "stems": stems, "ann": (ver, blob, ann), "env": env, "acts": acts, "acts_ann": acts_ann, "why": why}


def mdb_song(home, inv_s, cache_dir):
    """One MedleyDB song's parts and counts, or {"left_out": why}."""
    import numpy as np

    song = inv_s["song"]
    m = mdb_acts(home, inv_s, cache_dir)
    n, stems, env, acts, acts_ann = m["n"], m["stems"], m["env"], m["acts"], m["acts_ann"]
    ver, blob, ann = m["ann"]
    if m["why"]:
        return {"set": "medleydb", "id": f"medleydb:{song}", "song": song, "band": inv_s["band"], "left_out": m["why"]}
    starts = windows(n)
    rows, agree = [], {}
    for sid, st in stems.items():
        if not st["electric"]:
            continue
        others = [v for k, v in acts.items() if k != sid]
        c = part_counts(acts[sid], others, others, starts)
        c_ann = None
        if len(acts_ann) == len(acts):
            oa = [v for k, v in acts_ann.items() if k != sid]
            c_ann = part_counts(acts_ann[sid], oa, oa, starts)
        lab = next((i for i in st["instruments"] if i in MDB_ELECTRIC), None)
        rows.append({"part": sid, "mdb_label": lab, "role": None, "gain_class": None, "counts": c,
                     "counts_annotation_only": c_ann})
        if sid in ann and any(r in env for r in st["raws"]):
            a_raw = np.zeros(n, bool)
            for r in st["raws"]:
                if r in env:
                    a_raw |= active(env[r], n, NODI_ACT_DB)
            a_ann = conf_frames(*ann[sid], n)
            agree[sid] = {"frames_agree": round(float((a_raw == a_ann).mean()), 4),
                          "raw_active": round(float(a_raw.mean()), 4), "annotation_active": round(float(a_ann.mean()), 4)}
    return {"set": "medleydb", "id": f"medleydb:{song}", "song": song, "band": inv_s["band"],
            "has_bleed": inv_s.get("has_bleed"), "length_s": round(n * HOP_S, 1), "annotation": ver,
            "annotation_blob": blob, "single_guitar": len(acts) == 1, "guitars": sorted(acts),
            "guitar_instruments": {k: v["instruments"] for k, v in stems.items()}, "parts": rows,
            "rule_agreement": agree}


# --- the run --------------------------------------------------------------------------------------------------------

def out_dir(home):
    return home / "learn/window-count"


def cmd_run(a):
    home = pathlib.Path(a.data_dir).expanduser()
    od = out_dir(home)
    od.mkdir(parents=True, exist_ok=True)
    final = od / "w0-results.json"
    if a.limit is None and final.exists():
        raise SystemExit(f"{final} exists: W0 is read once")
    t0 = time.time()
    labels = locator_labels()
    loc = locator_sessions()
    mdb, reserve = mdb_sessions(home)
    jobs = [("locator", s) for s in loc] + [("medleydb", s) for s in mdb]
    if a.limit is not None:
        jobs = jobs[:a.limit]
    songs, left_out, timing = {k: [] for k in SETS}, [], []
    for kind, s in jobs:
        t = time.time()
        if kind == "locator":
            r = locator_song(s, locator_envelopes(s, od / "env-locator"), labels)
        else:
            r = mdb_song(home, s, od / "env-medleydb")
        timing.append({"song": r["id"], "s": round(time.time() - t, 2)})
        if "left_out" in r:
            left_out.append(r)
        else:
            songs[kind].append(r)
        print(f"{r['id']}: {timing[-1]['s']} s", flush=True)
    doc = {"schema": "window-count-w0-1", "plan": "docs/window-count-plan.md", "ledger": "preset-ladder phase_wc",
           "rules": {"hop_s": HOP_S, "window_s": WIN * HOP_S, "step_s": STEP * HOP_S, "active_share": ACTIVE_SHARE,
                     "act_db_di": ACT_DB, "act_db_other": NODI_ACT_DB, "strict": STRICT, "tolerant": TOLERANT,
                     "curve": CURVE, "wide": WIDE, "rare": RARE, "mdb_conf": MDB_CONF, "mdb_commit": MDB_COMMIT},
           "reserve_songs_left_out": reserve, "left_out": left_out,
           "seconds": round(time.time() - t0, 1), "timing": timing,
           "songs": songs, "report": report(songs), "table": W0_TABLE}
    path = final if a.limit is None else od / f"w0-timing-{a.limit}.json"
    text = json.dumps(doc, indent=1, default=str)
    path.write_text(text)
    print(path, hashlib.sha256(text.encode()).hexdigest()[:12], f"{doc['seconds']} s")
    h = doc["report"]["headline"]
    print("headline", h)
    for k in (*SETS, POOL):
        if k in doc["report"]:
            d = doc["report"][k]["deciding"]
            print(k, {x: (None if d[x] is None else round(d[x], 3)) if isinstance(d[x], float) or d[x] is None
                      else d[x] for x in ("mean", "lo90", "hi90", "bands", "songs", "code")})


def cmd_check(a):
    """Zero-outcome check before the declaration merges: every song's inputs resolve (envelopes, annotations, stems)
    and the left-out songs with why. Builds the envelope caches; counts no window."""
    home = pathlib.Path(a.data_dir).expanduser()
    od = out_dir(home)
    loc = locator_sessions()
    mdb, reserve = mdb_sessions(home)
    out = {"locator": [], "medleydb": [], "left_out": [], "reserve_songs_left_out": reserve}
    t0 = time.time()
    for s in loc:
        n, acts, parts = locator_acts(s, locator_envelopes(s, od / "env-locator"))
        out["locator"].append({"song": s["song"], "band": s["band"], "parts": len(parts), "guitars": len(acts)})
    for s in mdb:
        m = mdb_acts(home, s, od / "env-medleydb")
        row = {"song": s["song"], "band": s["band"], "annotation": m["ann"][0],
               "electric": sum(v["electric"] for v in m["stems"].values()), "guitars": len(m["stems"])}
        (out["left_out"] if m["why"] else out["medleydb"]).append({**row, "why": m["why"]} if m["why"] else row)
    out["seconds"] = round(time.time() - t0, 1)
    print(json.dumps({"locator_songs": len(out["locator"]), "locator_bands": len({r["band"] for r in out["locator"]}),
                      "locator_parts": sum(r["parts"] for r in out["locator"]),
                      "medleydb_songs": len(out["medleydb"]),
                      "medleydb_bands": len({r["band"] for r in out["medleydb"]}),
                      "medleydb_parts": sum(r["electric"] for r in out["medleydb"]),
                      "left_out": out["left_out"], "reserve": reserve, "seconds": out["seconds"]}, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--data-dir", default="~/ndsp-presets")
    r.add_argument("--limit", type=int, default=None, help="only the first N songs (the timing run; not the read)")
    c = sub.add_parser("check")
    c.add_argument("--data-dir", default="~/ndsp-presets")
    a = ap.parse_args(argv)
    {"run": cmd_run, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    main()
