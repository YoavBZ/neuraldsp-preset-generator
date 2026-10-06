"""Set 3's declaration (`docs/validation-set3.md`): parts by split and fold.

Training code uses it to keep held-out and test-fold DIs out:

    from learn import set3
    set3.parts(split="development", fold=2)        # the fold-2 test parts
    set3.training_sessions(test_fold=2)            # sessions whose DIs fold 2 may train on
    set3.is_held_out("V.M.GY")                     # a band or a session key

Held-out bands are never trained on, not even their DIs; every session by a held-out band
is held out, including sessions with no kept part.
"""

from __future__ import annotations

import functools
import json
import pathlib

DECLARATION = pathlib.Path(__file__).resolve().parents[1] / "docs" / "validation-set3.json"
N_FOLDS = 4


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


def is_held_out(band_or_session_key: str, path=DECLARATION) -> bool:
    d = load(path)
    return any(band_or_session_key in (s["band"], s["key"], s["path"])
               and s["split"] == "held_out" for s in d["sessions"])


def training_sessions(test_fold: int | None, path=DECLARATION) -> list[dict]:
    """Sessions whose DIs (and renders) a network tested on `test_fold` may train on:
    development sessions outside that fold. `None` means a network tested only on
    held-out bands, which may use every development session."""
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
