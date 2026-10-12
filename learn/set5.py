"""Set 5's declaration (`docs/validation-set5.md`) and its leakage guard.

Every set-5 band is held out: nothing may train, tune or choose on it before a declared
confirmation. The guard fails closed, as set 4's does (`learn/set4.py`):

    from learn import set5
    set5.is_held_out("Ronnie Jones")           # True: a band, session key or crop slug
    set5.is_held_out("~/ndsp-presets/references/datasets-set5/...")   # True: any path under it
    set5.refuse(path)                          # raises if `path` is set-5 material
    set5.parts(scope="in_scope")               # the clean and crunch parts

Anything under the set-5 dataset root or crop root is held out, listed or not (failed
sessions, amp-only tracks, excluded parts). `covers` says whether a name or path is set
5's at all; `learn.set3.is_held_out`, `fold_for_band` and `training_dis` consult it, so
set-5 files cannot reach a training list.
"""

from __future__ import annotations

import functools
import json
import os
import pathlib

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
DECLARATION = PLUGIN_ROOT / "docs" / "validation-set5.json"
REFERENCES = pathlib.Path(os.path.expanduser("~/ndsp-presets/references"))
SET5_ROOT = REFERENCES / "datasets-set5"
SET5_CROPS = REFERENCES / "validation-crops-set5"
SCOPES = ("in_scope", "report_only")

# Every set-5 session, passing or not. Known here as well as from the declaration, so the
# guard fails closed even on a declaration that lags behind; tests check that the two
# agree. session key -> (band, directory under SET5_ROOT)
SESSIONS = {
    "cambridge/RonnieJones_WhyDontYouStay_Full":
        ("Ronnie Jones", "Ronnie Jones - Why Don't You Stay/RonnieJones_WhyDontYouStay_Full"),
    "cambridge/Hazael_AMiLado_Full": ("Hazael", "Hazael - A Mi Lado/Hazael_AMiLado_Full"),
    "cambridge/Hazael_ResistenciaParaUnNuevoComenzar_Full":
        ("Hazael", "Hazael - Resistencia Para Un Nuevo Comenzar/Hazael_ResistenciaParaUnNuevoComenzar_Full"),
    "cambridge/MR0905_ChrisDurban_Full": ("Chris Durban", "Chris Durban - Celebrate/MR0905_ChrisDurban_Full"),
    "cambridge/BKS_TooMuch_Full": ("BKS", "BKS - Too Much/BKS_TooMuch_Full"),
    "cambridge/BKS_Bulldozer_Full": ("BKS", "BKS - Bulldozer/BKS_Bulldozer_Full"),
    "cambridge/SaturnSyndicate_NeverLeaveTheNightAlone_Full":
        ("Saturn Syndicate",
         "Saturn Syndicate - Never Leave The Night Alone/SaturnSyndicate_NeverLeaveTheNightAlone_Full"),
    "cambridge/NovaOneStudio_FourGraham_Full":
        ("Nova-One Studio", "Nova-One Studio - Four Graham/NovaOneStudio_FourGraham_Full"),
    "cambridge/PeterWhite_CrazyGirl_Full": ("Peter White", "Peter White - Crazy Girl/PeterWhite_CrazyGirl_Full"),
    "cambridge/HannesKeseberg_YouKnowBetter_Full":
        ("Hannes Keseberg", "Hannes Keseberg - You Know Better/HannesKeseberg_YouKnowBetter_Full"),
    # Hugging Face re-host (kwatcharasupat/mixing-secrets-rawstems, pinned revision)
    "hf-rawstems/The_Ferryboat_Men - The_Winds_Of_Gypsy_Moor":
        ("The Ferryboat Men", "The Ferryboat Men - The Winds Of Gypsy Moor/Gtr_EG"),
    "hf-rawstems/Jeff_Hirata - Sunshine": ("Jeff Hirata", "Jeff Hirata - Sunshine/Gtr_EG"),
    "hf-rawstems/Fytakyte - Too_Much": ("Fytakyte", "Fytakyte - Too Much/Gtr_EG"),
    "hf-rawstems/MOPP - Ukraina": ("MOPP", "MOPP - Ukraina/Gtr_EG"),
}


@functools.lru_cache(maxsize=None)
def _load(path: str) -> dict:
    return json.loads(pathlib.Path(path).read_text())


def load(path: pathlib.Path | str = DECLARATION) -> dict:
    """The declaration as written (a cached object: do not modify it)."""
    return _load(str(path))


def parts(path=DECLARATION, scope: str | None = None) -> list[dict]:
    """Kept parts, all held out; `scope` "in_scope" (clean, crunch) or "report_only"
    (high-gain). Reading their audio needs a declared confirmation."""
    if scope is not None and scope not in SCOPES:
        raise ValueError(f"unknown scope {scope!r}")
    return [p for p in load(path)["parts"] if scope is None or p["scope"] == scope]


def bands(path=DECLARATION) -> list[str]:
    return sorted({s["band"] for s in load(path)["sessions"]})


@functools.lru_cache(maxsize=None)
def _names(path: str = str(DECLARATION)) -> frozenset:
    d = load(path)
    out = set(d["held_out_bands"]) | set(SESSIONS) | {band for band, _ in SESSIONS.values()}
    for s in d["sessions"]:
        out |= {s["band"], s["key"]}
    out |= {p["slug"] for p in [*d["parts"], *d["excluded"]] if p.get("slug")}
    return frozenset(out)


@functools.lru_cache(maxsize=None)
def _relative(path: str = str(DECLARATION)) -> tuple:
    """Session directories as written relative to the set-5 root."""
    dirs = {s["path"] for s in load(path)["sessions"]} | {d for _, d in SESSIONS.values()}
    return tuple(pathlib.PurePosixPath(d).parts for d in sorted(dirs))


def _roots() -> list[tuple]:
    out = set()
    for root in (SET5_ROOT, SET5_CROPS):
        out |= {root.parts, pathlib.Path(os.path.realpath(root)).parts}
    return sorted(out)


def covers(x: str | os.PathLike, path=DECLARATION) -> bool:
    """Whether `x` is set-5 material: a set-5 band, session key or crop slug, or a path
    (absolute, `~`, or relative to the set-5 root) under the set-5 dataset or crop root."""
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
    """True for anything set 5 covers (every set-5 band is held out); KeyError otherwise."""
    if covers(x, path):
        return True
    raise KeyError(f"not a set-5 band, session, crop or path: {os.fspath(x)!r}")


def refuse(x: str | os.PathLike, path=DECLARATION) -> None:
    """Raise ValueError if `x` is set-5 material (for training, tuning or choosing)."""
    if covers(x, path):
        raise ValueError(f"set-5 material is held out (docs/validation-set5.md): {os.fspath(x)!r}")
