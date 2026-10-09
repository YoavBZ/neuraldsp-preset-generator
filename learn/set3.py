"""Set 3's declaration (`docs/validation-set3.md`): parts by split and fold, and the
leakage guards training code must go through.

    from learn import set3
    set3.parts(split="development", fold=2)        # the fold-2 test parts
    set3.fold_for_band("Eat The Feeder")           # 2: K3's folds merged with set 3's
    set3.training_dis(test_fold=2)                 # DI files a fold-2 network may train on
    set3.is_held_out("V.M.GY")                     # a band, session key, crop slug or path

Held-out bands are never trained on, not even their DIs; every session by a held-out band
is held out, including sessions with no kept part. The guards fail closed: a held-out
band, a name or path they do not know, or a fold clash raises rather than passing.

`is_held_out` also knows sets 1 and 2 (`docs/validation-datasets.json`), so every DI that
`training_dis` returns can be checked by it.
"""

from __future__ import annotations

import functools
import json
import os
import pathlib

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
DECLARATION = PLUGIN_ROOT / "docs" / "validation-set3.json"
SETS_1_2 = PLUGIN_ROOT / "docs" / "validation-datasets.json"
REFERENCES = pathlib.Path(os.path.expanduser("~/ndsp-presets/references"))
SET3_ROOT = REFERENCES / "datasets-set3"
SET3_CROPS = REFERENCES / "validation-crops-set3"
SETS_1_2_ROOT = REFERENCES / "datasets"
GUITAR_TECHS = "Guitar-TECHS P1"           # extra DIs (learn/di_pool.py), never tested on
GUITAR_TECHS_DIR = SETS_1_2_ROOT / "guitar-techs" / "P1-downloads"
EVERY_FOLD = -1                            # fold_for_band: every fold may train on it
N_FOLDS = 4
CLIP_RUNS = 10                             # >= 10 flat-topped full-scale runs: a clipped DI


@functools.lru_cache(maxsize=None)
def _load(path: str) -> dict:
    return json.loads(pathlib.Path(path).read_text())


def load(path: pathlib.Path | str = DECLARATION) -> dict:
    """The declaration as written (a cached object: do not modify it)."""
    return _load(str(path))


def _check(split, fold):
    if split not in (None, "development", "held_out"):
        raise ValueError(f"split must be 'development' or 'held_out', not {split!r}")
    if fold is not None and fold not in range(N_FOLDS):
        raise ValueError(f"fold must be 0-{N_FOLDS - 1}, not {fold!r}")
    if split == "held_out" and fold is not None:
        raise ValueError("held-out parts have no fold")


def parts(split: str | None = None, fold: int | None = None, *, without_marks=(),
          path=DECLARATION) -> list[dict]:
    """Kept parts, filtered by split and fold; `without_marks` drops parts carrying any of
    the named marks (e.g. ("effects_or_bleed",))."""
    _check(split, fold)
    return [p for p in load(path)["parts"]
            if (split is None or p["split"] == split)
            and (fold is None or p["fold"] == fold)
            and not set(without_marks) & set(p["marks"])]


def slugs(split: str | None = None, fold: int | None = None, **kw) -> list[str]:
    return [p["slug"] for p in parts(split, fold, **kw)]


def bands(split: str | None = None, fold: int | None = None, path=DECLARATION) -> list[str]:
    """Bands of the declared sessions (bands with no kept part are development, unfolded)."""
    _check(split, fold)
    return sorted({s["band"] for s in load(path)["sessions"]
                   if (split is None or s["split"] == split)
                   and (fold is None or s["fold"] == fold)})


def training_sessions(test_fold: int | None, path=DECLARATION) -> list[dict]:
    """Set-3 sessions whose DIs (and renders) a network tested on `test_fold` may train
    on: development sessions outside that fold. `None` means a network tested only on
    held-out bands, which may use every development session. Prefer `training_dis`, which
    also applies K3's folds, the clipping rule and the held-out check per file."""
    _check(None, test_fold)
    return [s for s in load(path)["sessions"]
            if s["split"] == "development" and (test_fold is None or s["fold"] != test_fold)]


def lag(slug: str, judge: bool = True, path=DECLARATION) -> int:
    """A part's lag in samples at 48 kHz (positive when the amp track is later); with
    `judge`, less the plugin's 52 samples, as the judge aligns renders."""
    for p in load(path)["parts"]:
        if p["slug"] == slug:
            return p["judge_lag_samples"] if judge else p["lag_samples"]
    raise KeyError(slug)


# --- leakage guards (fail closed) -------------------------------------------------

def _sets_1_2():
    return json.loads(SETS_1_2.read_text())["sessions"]


def _roots(root: pathlib.Path | None, rel: str) -> list[tuple]:
    """Path parts a dataset path may be written as: absolute (as configured and through
    symlinks) or, with `root` None, relative to the dataset root."""
    if root is None:
        return [(".", *pathlib.PurePosixPath(rel).parts)]
    full = root / rel
    return sorted({full.parts, pathlib.Path(os.path.realpath(full)).parts})


@functools.lru_cache(maxsize=None)
def _index(path: str = str(DECLARATION)):
    """(names, prefixes): name -> held out?, and [(path parts, held out?, files or None)].

    A name or directory is held out when anything it covers is held out (fail closed).
    Set 1 shares one directory between sessions of both sides (Guitar-TECHS P3_music);
    under it only the files its catalogue lists are known."""
    d = load(path)
    names: dict[str, bool] = {GUITAR_TECHS: False}

    def name(n, held):
        names[n] = names.get(n, False) or held

    prefixes = []
    for s in d["sessions"]:
        held = s["split"] == "held_out"
        for n in (s["band"], s["key"]):
            name(n, held)
        for root in (SET3_ROOT, None):
            prefixes += [(r, held, None) for r in _roots(root, s["path"])]
    held_bands = set(d["held_out_bands"])
    for p in [*d["parts"], *d["excluded"]]:
        if p.get("slug"):
            held = p["band"] in held_bands
            name(p["slug"], held)
            prefixes += [(r, held, None) for r in _roots(SET3_CROPS, p["slug"])]
    by_dir: dict[str, list] = {}
    for s in _sets_1_2():
        if s.get("group"):
            name(s["group"], s["split"] == "held_out")
        by_dir.setdefault(s["path"], []).append(s)
    for rel, sessions in by_dir.items():
        files = None
        if len({s["split"] for s in sessions}) > 1:
            files = {}
            for s in sessions:
                listed = set(s.get("files", {})) | {p[k] for p in s["parts"]
                                                    for k in ("di", "reference") if p.get(k)}
                for f in listed:
                    files[f] = files.get(f, False) or s["split"] == "held_out"
        held = any(s["split"] == "held_out" for s in sessions)
        for root in (SETS_1_2_ROOT, None):
            prefixes += [(r, held, files) for r in _roots(root, rel)]
    prefixes += [(r, False, None) for r in _roots(GUITAR_TECHS_DIR, "")]
    return names, prefixes


def _parts(s: str) -> list[tuple]:
    q = os.path.normpath(os.path.expanduser(s))
    if os.path.isabs(q):
        return [pathlib.PurePosixPath(q).parts, pathlib.PurePosixPath(os.path.realpath(q)).parts]
    return [(".", *pathlib.PurePosixPath(q).parts)]


def is_held_out(x: str | os.PathLike, path=DECLARATION) -> bool:
    """Whether `x` is held out: a band, a set-3 session key or crop slug, or any file or
    directory under a declared session's directory or a set-3 crop's (absolute, `~`, or
    relative to the dataset root, e.g. "cambridge/VMGY_Omen_Full/..."). Covers sets 1-3
    and Guitar-TECHS P1. Raises KeyError on anything it does not know."""
    names, prefixes = _index(str(path))
    s = os.fspath(x)
    if not isinstance(x, os.PathLike) and s in names:
        return names[s]
    hits = []
    for q in _parts(s):
        for root, held, files in prefixes:
            if q[:len(root)] != root:
                continue
            if files is None:
                hits.append(held)
                continue
            rest = "/".join(q[len(root):])
            under = [v for f, v in files.items() if not rest or f == rest or f.startswith(rest + "/")]
            if under:
                hits.append(any(under))
    if not hits:
        raise KeyError(f"not a known band, session, crop or dataset path: {s!r}")
    return any(hits)


@functools.lru_cache(maxsize=None)
def _fold_map(path: str = str(DECLARATION)) -> dict:
    from learn.train import k3_folds

    k3, _ = k3_folds()
    d = load(path)
    out = dict(k3)
    for s in d["sessions"]:
        if s["split"] != "development":
            continue
        fold = EVERY_FOLD if s["fold"] is None else s["fold"]
        if out.get(s["band"], fold) != fold:
            raise ValueError(f"{s['band']}: K3 fold {out[s['band']]} but set-3 fold {fold}")
        out[s["band"]] = fold
    out[GUITAR_TECHS] = EVERY_FOLD
    return out


def fold_for_band(band: str, path=DECLARATION) -> int:
    """The band's fold across sets 1-3: K3's folds (`learn.train.k3_folds`) merged with
    set 3's development folds. -1 (`EVERY_FOLD`) for Guitar-TECHS P1 and set 3's unfolded
    development bands (no kept part), which every fold may train on. Raises ValueError on
    a held-out band (any set) and KeyError on a band it does not know."""
    names, _ = _index(str(path))
    if names.get(band):
        raise ValueError(f"{band} is held out: no fold may train on it or test it")
    folds = _fold_map(str(path))
    if band not in folds:
        raise KeyError(f"unknown band: {band!r}")
    return folds[band]


def training_dis(test_fold: int | None, path=DECLARATION) -> list[pathlib.Path]:
    """DI files a network to be tested on `test_fold` may train on (`None`: tested only
    on held-out bands, so every development fold may be used):

    - set 2's development DIs and Guitar-TECHS P1's (`learn.di_pool.tracks`), and every DI
      of set 3's development sessions, kept part or not;
    - less those of bands in `test_fold` (`fold_for_band`);
    - less set-3 DIs with 10 or more flat-topped full-scale runs (the catalogue's
      whole-session count, `sessions[].dis[].di_clip_runs`). Set 2's catalogue has no
      clipping count, so set 2's DIs are as `learn.di_pool` uses them.

    Every file is checked again with `is_held_out`; one that is held out, unknown, or of
    an unknown band raises."""
    _check(None, test_fold)
    from learn import di_pool

    rows = [(band, pathlib.Path(f)) for band, f in di_pool.tracks()]
    for s in load(path)["sessions"]:
        if s["split"] != "development":
            continue
        for di in s["dis"]:
            if di["di_clip_runs"] < CLIP_RUNS:
                rows.append((s["band"], SET3_ROOT / di["di"]))
    out = []
    for band, f in rows:
        if fold_for_band(band, path) == test_fold:     # raises on held-out or unknown bands
            continue
        if is_held_out(f, path):
            raise ValueError(f"held-out DI reached the training list: {f}")
        out.append(f)
    return sorted(set(out))
