"""Part locator, step 1: the truth file (`docs/part-locator-plan.md`). Development only.

From each development session's tracks: where each electric-guitar part plays and dominates,
its character and role labels, each target's base rate, and the band folds. No separation,
no renders, nothing held out.

    .venv/bin/python -m learn.locator_truth tracks     # per-session 100-ms envelopes (cache)
    .venv/bin/python -m learn.locator_truth pyin-jobs  # then run learn/locator_pyin.py
    .venv/bin/python -m learn.locator_truth build      # docs/part-locator-truth.json
"""

from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import re
import sys

import numpy as np

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
HOME = pathlib.Path("~/ndsp-presets").expanduser()
REFS = HOME / "references"
OUT = HOME / "learn/locator"
ENV = OUT / "env"
PYIN = OUT / "pyin"
TRUTH = PLUGIN_ROOT / "docs/part-locator-truth.json"

HOP_S = 0.1                 # activity frames: 100-ms RMS
ACT_DB = 30.0               # a DI is active within 30 dB of its loudest frame
NODI_ACT_DB = 20.0          # a guitar without a DI: its amp track within 20 dB of its loudest
WIN, STEP = 100, 10         # 10-s windows every 1 s, in frames
ACTIVE_SHARE = 0.6          # the part plays in at least 60% of the window's frames
DOMINANCE = 0.5             # and carries at least half the guitars' 1–4 kHz energy
BAND = (1000.0, 4000.0)
LEAD_MAX_COVER, LEAD_MIN_VOICED = 0.5, 0.6
RHYTHM_MIN_COVER, RHYTHM_MAX_VOICED = 0.5, 0.4
PYIN_HOP_S = 512 / 44100

# MUSDB18 overlap (reported with and without): exact names, and The Long Wait by artist
MUSDB_TRAIN = {"It Was My Fault For Waiting", "Femme", "Bannockburn"}
MUSDB_TEST = {"Signs", "Ill Fate"}
MUSDB_ARTIST = {"The Long Wait"}

SET1_BANDS = {"Bourbon": "Rebecca Haviland", "Collide With Me": "Rebecca Haviland",
              "Heather Jane": "Chris Coltraine"}


# --- sessions -----------------------------------------------------------------

def _is_electric(name: str) -> bool:
    b = pathlib.Path(name).name
    if not re.search(r"(elec|gtr|guit)", b, re.I):
        return False
    if re.search(r"(acous|acgtr|ac gtr|bass|vox|vocal)", b, re.I):
        return False
    return not re.search(r"(^|[ _\-\d])DI([ _.\-\d]|$)|DI_T", b)


def _guitar_key(name: str) -> str:
    b = pathlib.Path(name).stem
    m = re.search(r"(ElecGtr\s*\d+|Gtr\s*\d+|GTR\s*\d+|Guitar\s*\d+)", b, re.I)
    return re.sub(r"\s", "", m.group(1)).lower() if m else b


def sessions():
    """Every development session of sets 1–2 (but Guitar-TECHS) and set 3."""
    out = []
    groups = {(s["source"], s["song"]): s["group"]
              for s in json.loads((PLUGIN_ROOT / "docs/validation-sources-2.json").read_text())["sessions"]}
    cat = json.loads((PLUGIN_ROOT / "docs/validation-datasets.json").read_text())
    for s in cat["sessions"]:
        if s["split"] != "development" or s["source"] == "guitar-techs":
            continue
        root = REFS / "datasets" / s["path"]
        wavs = [f for f in s["files"] if f.lower().endswith(".wav")]
        set1 = "mix_tracks" not in s
        mix = ([f for f in wavs if not re.search(r"DI", pathlib.Path(f).name)] if set1
               else list(s["mix_tracks"]))
        parts = [dict(part=p["part"], di=p["di"], ref=p["reference"], alts=p.get("alternate", []),
                      usable=bool(p.get("usable")), excluded=p.get("excluded"),
                      lag=p.get("lag_ms"), gain_class=None)
                 for p in s["parts"] if p.get("di")]
        out.append(dict(set="1" if set1 else "2", source=s["source"], song=s["song"],
                        band=SET1_BANDS.get(s["song"]) or groups[(s["source"], s["song"])],
                        root=str(root), files=wavs, mix=mix, parts=parts))
    d3 = json.loads((PLUGIN_ROOT / "docs/validation-set3.json").read_text())
    me = json.loads((REFS / "datasets-set3/_tools/measured.json").read_text())
    gc = {(p["session_key"], p["part"]): p["gain_class"] for p in d3["parts"]}
    for s in d3["sessions"]:
        if s["split"] != "development":
            continue
        m = me[s["key"]]
        parts = [dict(part=p["part"], di=p["di"], ref=p["reference"], alts=p.get("alternate", []),
                      usable=bool(p.get("usable_rule")), excluded=None, lag=p.get("lag_ms"),
                      gain_class=gc.get((s["key"], p["part"])))
                 for p in m["parts"] if p.get("di")]
        files = m["files"] if isinstance(m["files"], list) else list(m["files"])
        out.append(dict(set="3", source=s["source"], song=s["song"], band=s["band"],
                        root=str(REFS / "datasets-set3" / s["path"]), files=files,
                        mix=list(m["mix_tracks"]), parts=parts))
    return out


def _path(root: str, name: str) -> pathlib.Path | None:
    r = pathlib.Path(root)
    for p in (r / name, r.parent / name):
        if p.exists():
            return p
    hits = list(r.rglob(pathlib.Path(name).name))
    return hits[0] if hits else None


def _slug(s) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", f"{s['set']}-{s['band']}-{s['song']}").strip("_")


# --- step: envelopes ----------------------------------------------------------

def _frames(path: pathlib.Path):
    """(broadband dB per 100-ms frame, 1–4 kHz energy per frame)."""
    import soundfile as sf

    info = sf.info(str(path))
    h = int(round(info.samplerate * HOP_S))
    f = np.fft.rfftfreq(h, 1 / info.samplerate)
    band = (f >= BAND[0]) & (f < BAND[1])
    win = np.hanning(h)
    db, en = [], []
    for blk in sf.blocks(str(path), blocksize=h * 64, always_2d=True, dtype="float32"):
        x = blk.mean(1)
        n = len(x) // h
        if n == 0:
            continue
        X = x[:n * h].reshape(n, h).astype(np.float64)
        db.append(20 * np.log10(np.sqrt((X ** 2).mean(1)) + 1e-12))
        en.append((np.abs(np.fft.rfft(X * win, axis=1)) ** 2)[:, band].sum(1))
    return np.concatenate(db), np.concatenate(en)


def tracks():
    ENV.mkdir(parents=True, exist_ok=True)
    for s in sessions():
        out = ENV / f"{_slug(s)}.npz"
        if out.exists():
            continue
        names = set(s["mix"]) | {f for f in s["files"] if _is_electric(f)}
        for p in s["parts"]:
            names |= {p["di"], p["ref"], *p["alts"]}
        arrs = {}
        for n in sorted(x for x in names if x):
            path = _path(s["root"], n)
            if path is None:
                print("missing", s["song"], n, flush=True)
                continue
            db, en = _frames(path)
            arrs[f"db::{n}"], arrs[f"en::{n}"] = db, en
        np.savez_compressed(out, **arrs)
        print("env", s["song"], len(arrs) // 2, flush=True)


def pyin_jobs():
    jobs = []
    for s in sessions():
        for p in s["parts"]:
            path = _path(s["root"], p["di"])
            if path is not None:
                jobs.append({"key": f"{_slug(s)}--{re.sub(r'[^A-Za-z0-9]+', '_', p['part'])}",
                             "di": str(path)})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pyin-jobs.json").write_text(json.dumps(jobs, indent=0))
    print(len(jobs), "jobs ->", OUT / "pyin-jobs.json")


# --- step: truth --------------------------------------------------------------

def _pad(x, n):
    return np.pad(x[:n], (0, max(0, n - len(x[:n]))))


def _windows(n_frames):
    return np.arange(0, max(n_frames - WIN, 0) + 1, STEP)


def _win_mean(x, starts):
    c = np.concatenate([[0.0], np.cumsum(x, dtype=np.float64)])
    return (c[starts + WIN] - c[starts]) / WIN


def _win_sum(x, starts):
    return _win_mean(x, starts) * WIN


def random_hit3(hit: np.ndarray, gap: int = WIN // STEP) -> float:
    """Exact P(at least one hit) under a uniform draw over non-overlapping triples (starts
    at least `gap` windows apart); for fewer than 3 such windows, over the largest valid sets."""
    n = len(hit)
    for k in (3, 2, 1):
        total, miss = _count_sets(np.ones(n, bool), k, gap), _count_sets(~hit, k, gap)
        if total > 0:
            return 1.0 - miss / total
    return 0.0


def _count_sets(ok: np.ndarray, k: int, gap: int) -> float:
    """Number of k-subsets of the allowed windows with consecutive picks >= gap apart."""
    n = len(ok)
    ways = ok.astype(np.float64)        # sets of size 1 ending at i
    for _ in range(k - 1):
        prev = np.concatenate([[0.0], np.cumsum(ways)])
        nxt = np.zeros(n)
        for i in range(n):
            if ok[i] and i - gap >= 0:
                nxt[i] = prev[i - gap + 1]
        ways = nxt
    return float(ways.sum())


def _character(s, p, gm, classify, load):
    if p["excluded"]:
        return None, "excluded"
    if s["set"] == "3":
        return p["gain_class"], "set-3 catalog" if p["gain_class"] else "no catalog class"
    if not p["usable"]:
        return None, "no passing pair"
    amp, sr = load(p["ref"])
    di, sr2 = load(p["di"])
    assert sr == sr2, (s["song"], p["part"])
    lag = int(round((p["lag"] or 0) * sr / 1000))
    cls = classify(gm.measures(amp, di, sr, lag))[0]
    return cls, "classifier"


def build():
    import soundfile as sf

    sys.path.insert(0, str(REFS / "datasets-set3/_tools"))
    import classify as C
    import gainmeasure as GM

    sess = sessions()
    rows, songs = [], []
    for s in sess:
        z = np.load(ENV / f"{_slug(s)}.npz")
        db = {k[4:]: z[k] for k in z.files if k.startswith("db::")}
        en = {k[4:]: z[k] for k in z.files if k.startswith("en::")}
        n = max(len(db[m]) for m in s["mix"] if m in db)          # the song's length
        starts = _windows(n)

        # guitars: each part's microphones; electric tracks no part owns, grouped by name
        owned = {}
        for p in s["parts"]:
            for t in (p["ref"], *p["alts"]):
                if t:
                    owned[t] = p["part"]
        guitars: dict[str, list[str]] = {}
        for t in sorted(set(en) - {p["di"] for p in s["parts"]}):
            if t in owned:
                guitars.setdefault("part:" + owned[t], []).append(t)
            elif _is_electric(t):
                guitars.setdefault("nodi:" + _guitar_key(t), []).append(t)
        g_en = {g: sum(_pad(en[t], n) for t in ts) for g, ts in guitars.items()}
        all_en = sum(g_en.values()) if g_en else np.zeros(n)
        nodi_act = {}
        for g, ts in guitars.items():
            if g.startswith("nodi:"):
                d = np.max([_pad(db[t], n) for t in ts], axis=0)
                nodi_act[g] = d > d.max() - NODI_ACT_DB
        any_act = np.zeros(n, bool)
        for a in nodi_act.values():
            any_act |= a

        def load(name, _s=s):
            x, sr = sf.read(str(_path(_s["root"], name)), always_2d=True, dtype="float64")
            return x.mean(1), sr

        parts = []
        for p in s["parts"]:
            if p["di"] not in db:
                continue
            d = _pad(db[p["di"]], n)
            act = d > d.max() - ACT_DB
            any_act |= act
            cover = float((_win_mean(act, starts) >= ACTIVE_SHARE).mean())
            key = f"{_slug(s)}--{re.sub(r'[^A-Za-z0-9]+', '_', p['part'])}"
            v = np.load(PYIN / f"{key}.npy")
            # pYIN frames (hop 512 at 44.1 kHz) onto the part's active 100-ms frames
            t = (np.arange(len(v)) * PYIN_HOP_S + 2048 / 44100 / 2)
            fi = np.minimum((t / HOP_S).astype(int), n - 1)
            on = act[fi]
            voiced = float(v[on].mean()) if on.any() else 0.0
            if cover <= LEAD_MAX_COVER and voiced >= LEAD_MIN_VOICED:
                role = "lead"
            elif cover >= RHYTHM_MIN_COVER and voiced <= RHYTHM_MAX_VOICED:
                role = "rhythm"
            else:
                role = None
            cls, how = _character(s, p, GM, C.classify, load)
            character = {"clean": "clean", "crunch": "driven", "high-gain": "driven"}.get(cls)
            parts.append(dict(part=p["part"], act=act, cover=round(cover, 3), voiced=round(voiced, 3),
                              role=role, gain_class=cls, character=character, character_source=how,
                              keys_gtr=bool(p["excluded"])))

        any_win = _win_mean(any_act, starts) >= ACTIVE_SHARE
        song = dict(set=s["set"], source=s["source"], band=s["band"], song=s["song"],
                    windows=len(starts), length_s=round(n * HOP_S, 1),
                    any_guitar_share=round(float(any_win.mean()), 3),
                    musdb=("train" if s["song"] in MUSDB_TRAIN else "test" if s["song"] in MUSDB_TEST
                           else "artist" if s["band"] in MUSDB_ARTIST else None),
                    no_di_guitars={g: ts for g, ts in guitars.items() if g.startswith("nodi:")},
                    parts=[{k: v for k, v in q.items() if k != "act"} for q in parts])
        songs.append(song)

        # targets: parts with both labels, same-description parts merged into one target
        desc = {}
        for q in parts:
            if q["keys_gtr"] or not q["role"] or not q["character"]:
                continue
            scope = "high-gain" if q["gain_class"] == "high-gain" else "in-scope"
            desc.setdefault((q["character"], q["role"], scope), []).append(q)
        for (character, role, scope), qs in sorted(desc.items()):
            act = np.zeros(n, bool)
            for q in qs:
                act |= q["act"]
            mine = sum(g_en.get("part:" + q["part"], np.zeros(n)) for q in qs)
            share = _win_sum(mine, starts) / np.maximum(_win_sum(all_en, starts), 1e-20)
            hit = (_win_mean(act, starts) >= ACTIVE_SHARE) & (share >= DOMINANCE)
            rows.append(dict(set=s["set"], band=s["band"], song=s["song"], character=character,
                             role=role, scope=scope, parts=[q["part"] for q in qs],
                             musdb=song["musdb"], base_rate_hit1=round(float(hit.mean()), 4),
                             base_rate_hit3=round(random_hit3(hit), 4),
                             hit_windows=[int(i) for i in np.flatnonzero(hit)]))
        print(s["song"], [(q["part"], q["role"], q["character"]) for q in parts], flush=True)

    folds = band_folds(sess)
    for r in rows:
        r["fold"] = folds[_fold_band(r["band"])]
    primary = [r for r in rows if r["scope"] == "in-scope" and 0 < r["base_rate_hit3"] <= 0.8]
    reachable = [r for r in rows if r["scope"] == "in-scope" and r["base_rate_hit3"] > 0]
    dropped = [r for r in rows if r["base_rate_hit3"] == 0]
    counts = dict(
        parts=sum(len(s["parts"]) for s in songs),
        role={k: sum(1 for s in songs for q in s["parts"] if q["role"] == k) for k in ("lead", "rhythm", None)},
        character={k: sum(1 for s in songs for q in s["parts"] if q["character"] == k) for k in ("clean", "driven", None)},
        targets=len(rows), in_scope_reachable=len(reachable),
        in_scope_reachable_bands=len({_fold_band(r["band"]) for r in reachable}),
        primary=len(primary), primary_bands=len({_fold_band(r["band"]) for r in primary}),
        primary_by_fold={f: sum(1 for r in primary if r["fold"] == f) for f in (1, 2, 3)},
        dropped_base_rate_0=len(dropped))
    TRUTH.write_text(json.dumps(dict(
        schema="part-locator-truth-1", plan="docs/part-locator-plan.md",
        rules=dict(hop_s=HOP_S, act_db=ACT_DB, nodi_act_db=NODI_ACT_DB, window_s=WIN * HOP_S,
                   step_s=STEP * HOP_S, active_share=ACTIVE_SHARE, dominance=DOMINANCE, band_hz=BAND,
                   lead=f"cover<={LEAD_MAX_COVER} and voiced>={LEAD_MIN_VOICED}",
                   rhythm=f"cover>={RHYTHM_MIN_COVER} and voiced<={RHYTHM_MAX_VOICED}",
                   pyin="librosa 0.11 pyin, fmin 70, fmax 1400, frame 2048, hop 512 at 44.1 kHz, center=False"),
        folds={b: f for b, f in sorted(folds.items())}, counts=counts,
        targets=rows, dropped=[{k: r[k] for k in ("song", "parts", "character", "role")} for r in dropped],
        songs=songs), indent=1, default=str))
    print(json.dumps(counts, indent=1))


def _fold_band(band: str) -> str:
    return band


def band_folds(sess):
    """Stratified 3-fold deal by band (plan, Split). Eat The Feeder stays whole: its set-2 and
    set-3 songs share the band name, so they land in one fold."""
    single_tf = {s["band"] for s in sess if s["source"] == "telefunken" and s["set"] != "3"
                 and sum(1 for p in s["parts"] if not p["excluded"]) == 1}
    multi_tf = {s["band"] for s in sess if s["source"] == "telefunken" and s["set"] != "3"}
    for b in list(single_tf):
        if any(s["band"] == b and sum(1 for p in s["parts"] if not p["excluded"]) > 1 for s in sess):
            single_tf.discard(b)
    cam12 = {s["band"] for s in sess if s["source"] == "cambridge" and s["set"] != "3"}
    s3 = {s["band"] for s in sess if s["set"] == "3"} - cam12          # Eat The Feeder -> cam12
    strata = [sorted(single_tf), sorted(cam12), sorted(multi_tf - single_tf), sorted(s3)]
    folds, deal = {}, itertools.cycle((1, 2, 3))
    for stratum in strata:
        for b in stratum:
            folds.setdefault(b, next(deal))
    return folds


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("tracks", "pyin-jobs", "build"))
    a = ap.parse_args(argv)
    {"tracks": tracks, "pyin-jobs": pyin_jobs, "build": build}[a.step]()


if __name__ == "__main__":
    main()
