"""Set 4's declaration (`docs/validation-set4.md`) and its leakage guard.

Every set-4 band is held out: nothing may train, tune or choose on it before a declared
confirmation (`docs/validation-set4-plan.md`). The guard fails closed:

    from learn import set4
    set4.is_held_out("Tholas P.")              # True: a band, session key or crop slug
    set4.is_held_out("~/ndsp-presets/references/datasets-set4/...")   # True: any path under it
    set4.refuse(path)                          # raises if `path` is set-4 material

Anything under the set-4 dataset root or crop root is held out, listed or not (archives,
amp-only tracks, excluded parts). `covers` says whether a name or path is set 4's at all;
`learn.set3.is_held_out`, `fold_for_band` and `training_dis` consult it, so set-4 files
cannot reach a training list.
"""

from __future__ import annotations

import functools
import json
import os
import pathlib

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
DECLARATION = PLUGIN_ROOT / "docs" / "validation-set4.json"
REFERENCES = pathlib.Path(os.path.expanduser("~/ndsp-presets/references"))
SET4_ROOT = REFERENCES / "datasets-set4"
SET4_CROPS = REFERENCES / "validation-crops-set4"


@functools.lru_cache(maxsize=None)
def _load(path: str) -> dict:
    return json.loads(pathlib.Path(path).read_text())


def load(path: pathlib.Path | str = DECLARATION) -> dict:
    """The declaration as written (a cached object: do not modify it)."""
    return _load(str(path))


def parts(path=DECLARATION) -> list[dict]:
    """Kept parts. All are held out; reading their audio needs a declared confirmation."""
    return list(load(path)["parts"])


def bands(path=DECLARATION) -> list[str]:
    return sorted({s["band"] for s in load(path)["sessions"]})


@functools.lru_cache(maxsize=None)
def _names(path: str = str(DECLARATION)) -> frozenset:
    d = load(path)
    out = set(d["held_out_bands"])
    for s in d["sessions"]:
        out |= {s["band"], s["key"]}
    out |= {p["slug"] for p in [*d["parts"], *d["excluded"]] if p.get("slug")}
    return frozenset(out)


@functools.lru_cache(maxsize=None)
def _relative(path: str = str(DECLARATION)) -> tuple:
    """Session directories as written relative to the set-4 root."""
    return tuple(pathlib.PurePosixPath(s["path"]).parts for s in load(path)["sessions"])


def _roots() -> list[tuple]:
    out = set()
    for root in (SET4_ROOT, SET4_CROPS):
        out |= {root.parts, pathlib.Path(os.path.realpath(root)).parts}
    return sorted(out)


def covers(x: str | os.PathLike, path=DECLARATION) -> bool:
    """Whether `x` is set-4 material: a set-4 band, session key or crop slug, or a path
    (absolute, `~`, or relative to the set-4 root) under the set-4 dataset or crop root."""
    s = os.fspath(x)
    if not isinstance(x, os.PathLike) and s in _names(str(path)):
        return True
    q = os.path.normpath(os.path.expanduser(s))
    if os.path.isabs(q):
        cands = {pathlib.PurePosixPath(q).parts, pathlib.PurePosixPath(os.path.realpath(q)).parts}
        return any(c[:len(r)] == r for c in cands for r in _roots())
    rel = pathlib.PurePosixPath(q).parts
    return any(rel[:len(r)] == r for r in _relative(str(path)))


def is_held_out(x: str | os.PathLike, path=DECLARATION) -> bool:
    """True for anything set 4 covers (every set-4 band is held out); KeyError otherwise."""
    if covers(x, path):
        return True
    raise KeyError(f"not a set-4 band, session, crop or path: {os.fspath(x)!r}")


def refuse(x: str | os.PathLike, path=DECLARATION) -> None:
    """Raise ValueError if `x` is set-4 material (for training, tuning or choosing)."""
    if covers(x, path):
        raise ValueError(f"set-4 material is held out (docs/validation-set4.md): {os.fspath(x)!r}")
