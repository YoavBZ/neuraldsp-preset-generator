"""Where a run's renders and objectives are kept, so nothing is measured twice.

A search spends its whole budget on renders, and the binding constraint is how
many of them fit in a session (§2, D3). Two things follow, and they are the only
two reasons this module exists:

**A repeated render is free.** The optimiser revisits parameter vectors — CMA-ES
resamples near its mean, the robustness re-rank re-renders the shortlist, a second
run on the same reference starts from the same recipe seed. Every trial is stored
against the content address in §6.3, which includes the plugin and renderer builds,
so a plugin update invalidates the cache instead of silently serving audio the
current plugin would not produce.

**A run has to be explicable afterwards.** `trials` keeps the objectives and the
fingerprint for every trial, not just the winner, because the interesting question
after a bad match is what the search *tried*. `verdicts` is for listening tests:
whatever the objective says, a person deciding by ear is the ground truth this
project is aiming at, and their choice belongs next to the trial it was about.

sqlite3 from the standard library, no ORM, no dependency. Not minimalism: a store a
person cannot open is a store they will not trust, and `sqlite3 trials.sqlite3` plus
one SELECT is a tool everybody already has. (An earlier version of this paragraph
claimed `show.py` and `apply_spec.py` open the store. They do not — they have nothing
to do with it, and the reason given for a decision should be the actual reason.)

Audio is **not** stored: a run of 300 renders at 48 kHz is gigabytes, and `render_sha`
plus the cache key identifies the audio well enough to re-render it.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Mapping, Optional

SCHEMA_VERSION = 1

# The file a run's trials go in, inside its `--out-dir`. A constant rather than a
# parameter, because it was a parameter nothing ever passed.
STORE_NAME = "trials.sqlite3"

# §6.4, with `schema_version` added so a future change can be detected rather than
# producing a confusing error six frames into a query.
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    run_id         TEXT PRIMARY KEY,
    created_at     REAL NOT NULL,
    pack           TEXT,
    template       TEXT,
    reference_sha  TEXT,
    regime         TEXT,
    loss_profile   TEXT,
    budget         INTEGER,
    renderer_id    TEXT,
    plugin_version TEXT,
    notes          TEXT
);

CREATE TABLE IF NOT EXISTS trials (
    trial_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    params_json     TEXT NOT NULL,
    -- §6.3's content address for the *render*: what audio came out.
    cache_key       TEXT,
    -- The content address for the *score*, which is a strictly finer thing: an
    -- objective depends on the target fingerprint, the loss profile and the recipe
    -- seed as well as on the render. Keyed on `cache_key` alone, the cache served
    -- run 2's candidate the objective run 1 measured against a different reference —
    -- 0.345 for a vector whose true distance was 0.634, with zero trial rows written,
    -- so the report's headline scored a match against somebody else's recording.
    -- Not in §6.4, and neither is `di_sha`: a trial is "these parameters through this
    -- signal, against that reference", and §6.3's own render key includes `di_sha256`
    -- for exactly that reason.
    objective_key   TEXT,
    di_sha          TEXT,
    di_offset_db    REAL DEFAULT 0.0,
    render_sha      TEXT,
    peak            REAL,
    silent          INTEGER,
    wall_ms         REAL,
    objectives_json TEXT,
    fingerprint_json TEXT,
    error           TEXT
);

CREATE INDEX IF NOT EXISTS trials_by_run ON trials(run_id);
-- Not UNIQUE: the same render legitimately appears in two runs, and the cache
-- lookup wants the most recent row rather than a constraint violation.
CREATE INDEX IF NOT EXISTS trials_by_key ON trials(cache_key);
CREATE INDEX IF NOT EXISTS trials_by_objective ON trials(objective_key);

CREATE TABLE IF NOT EXISTS verdicts (
    trial_id   INTEGER NOT NULL REFERENCES trials(trial_id),
    listener   TEXT NOT NULL,
    choice     TEXT NOT NULL,
    comment    TEXT,
    created_at REAL NOT NULL
);
"""


class StoreError(ValueError):
    """A store that cannot be opened, or a row that cannot mean what it says."""


@dataclass
class Trial:
    """One render and what it scored. `error` and `objectives` are exclusive.

    A trial that failed still gets a row. A search that quietly drops its failures
    reports a lower failure rate than it earned, and the M4 exit criterion asks for
    that rate as a separate number precisely so it cannot hide inside the others.
    """

    params: Dict[str, Any]
    cache_key: Optional[str] = None
    objective_key: Optional[str] = None
    di_sha: Optional[str] = None
    di_offset_db: float = 0.0
    render_sha: Optional[str] = None
    peak: Optional[float] = None
    silent: Optional[bool] = None
    wall_ms: Optional[float] = None
    objectives: Optional[Dict[str, float]] = None
    fingerprint: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    trial_id: Optional[int] = None

    @property
    def failed(self) -> bool:
        """Nothing usable came back. Silence counts, and that is deliberate: the
        repository's standing rule is that a silent render is not evidence about a
        control, so scoring one would be scoring the absence of a measurement."""
        return self.error is not None or self.objectives is None or bool(self.silent)

    def __post_init__(self) -> None:
        # "`error` and `objectives` are exclusive" was stated and unenforced, which
        # held only because M4 has one writer. A row carrying both says the render
        # failed *and* scored, and every reader here would have to pick one to
        # believe — so the writer is refused instead of the readers guessing.
        if self.error is not None and self.objectives is not None:
            raise StoreError(
                f"a trial cannot both fail and score: error is {self.error!r} and "
                f"objectives is {self.objectives!r}.\n"
                f"  If the render succeeded and something later went wrong, store the "
                f"objectives and put the later problem in a caveat; a trial row is "
                f"about whether audio came back."
            )


@dataclass
class Run:
    """The header row: what was being matched, against what, with what budget."""

    run_id: str
    created_at: float = field(default_factory=time.time)
    pack: Optional[str] = None
    template: Optional[str] = None
    reference_sha: Optional[str] = None
    regime: Optional[str] = None
    loss_profile: Optional[str] = None
    budget: Optional[int] = None
    renderer_id: Optional[str] = None
    plugin_version: Optional[str] = None
    notes: Optional[str] = None


class Store:
    """A run's trials on disk, or in memory for a test.

    Used as a context manager, or closed by hand. Every write commits, because a
    search that is interrupted after 200 renders must not lose them — that is
    exactly the case the cache exists for.
    """

    def __init__(self, path: str = ":memory:") -> None:
        self.path = str(path)
        # `executescript` is inside the guard too. `connect` succeeds on any readable
        # file — a wav, a preset, a half-written download — and it is the first CREATE
        # TABLE that fails, with a bare `DatabaseError` naming nothing a person can
        # act on. Pointing `--out-dir` at a directory that already holds something is
        # an ordinary mistake.
        try:
            self._db = sqlite3.connect(self.path)
            self._db.row_factory = sqlite3.Row
            self._db.executescript(SCHEMA)
        except sqlite3.Error as e:
            raise StoreError(
                f"cannot open the render store at {self.path}: {e}\n"
                f"  It has to be a writable path, in a directory that exists, and "
                f"either empty or a store this tool wrote. A run appends here after "
                f"every render, so it is not optional."
            ) from e
        self._check_version()

    def _check_version(self) -> None:
        row = self._db.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        if row is None:
            self._db.execute("INSERT INTO meta VALUES ('schema_version', ?)",
                             (str(SCHEMA_VERSION),))
            self._db.commit()
            return
        found = str(row["value"])
        if found != str(SCHEMA_VERSION):
            raise StoreError(
                f"{self.path} was written by schema version {found}; this is "
                f"version {SCHEMA_VERSION}.\n"
                f"  Point --out-dir somewhere new rather than mixing them: the "
                f"columns a query reads may not be the columns that are there."
            )

    # --- context management --------------------------------------------------

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self._db.close()

    # --- writing -------------------------------------------------------------

    def start_run(self, run: Run) -> Run:
        """Record a run header. Refuses a duplicate `run_id` rather than merging.

        Two runs sharing an id would interleave their trials, and every query in
        this module groups by run — so the failure would show up as a benchmark
        result that is quietly the average of two different searches.
        """
        try:
            self._db.execute(
                "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (run.run_id, run.created_at, run.pack, run.template,
                 run.reference_sha, run.regime, run.loss_profile, run.budget,
                 run.renderer_id, run.plugin_version, run.notes),
            )
        except sqlite3.IntegrityError as e:
            raise StoreError(
                f"run {run.run_id!r} is already in {self.path}.\n"
                f"  Use a new id: two runs under one id interleave their trials, "
                f"and every result here is grouped by run."
            ) from e
        self._db.commit()
        return run

    def add_trial(self, run_id: str, trial: Trial) -> Trial:
        """Store one trial and give it its id."""
        if not self._db.execute("SELECT 1 FROM runs WHERE run_id = ?",
                                (run_id,)).fetchone():
            raise StoreError(
                f"no run {run_id!r} in {self.path}; call start_run() first so the "
                f"trial has a header to belong to"
            )
        cursor = self._db.execute(
            "INSERT INTO trials (run_id, params_json, cache_key, objective_key,"
            " di_sha, di_offset_db, render_sha, peak, silent, wall_ms,"
            " objectives_json, fingerprint_json, error)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, _dump(trial.params), trial.cache_key, trial.objective_key,
             trial.di_sha, float(trial.di_offset_db), trial.render_sha,
             trial.peak, None if trial.silent is None else int(trial.silent),
             trial.wall_ms, _dump(trial.objectives), _dump(trial.fingerprint),
             trial.error),
        )
        self._db.commit()
        trial.trial_id = int(cursor.lastrowid)
        return trial

    def add_verdict(self, trial_id: int, listener: str, choice: str,
                    comment: Optional[str] = None) -> None:
        """What a person said about a trial, whatever the objective said.

        The verdict is the ground truth this whole apparatus is approximating, so
        it is stored rather than compared: if the objective and the listener
        disagree, the loss profile is what should change, and that argument needs
        both numbers.
        """
        if not self._db.execute("SELECT 1 FROM trials WHERE trial_id = ?",
                                (trial_id,)).fetchone():
            raise StoreError(f"no trial {trial_id} in {self.path} to record a "
                             f"verdict against")
        self._db.execute("INSERT INTO verdicts VALUES (?,?,?,?,?)",
                         (trial_id, listener, choice, comment, time.time()))
        self._db.commit()

    # --- the cache -----------------------------------------------------------

    def cached(self, objective_key: str) -> Optional[Trial]:
        """A previous trial that scored *this* vector against *this* reference.

        Keyed on `objective_key`, not on the render address, because what is being
        reused is a score. The two differ by the target fingerprint, the loss profile
        and the recipe seed, and keying on the render alone served one run's score to
        another run against a different reference — silently, with no trial row, so
        every count in the report was a count of zero.

        The most recent, and only if it *succeeded*. Returning a failed trial from
        the cache would make one transient error permanent for the life of the
        store — and a failure is not a measurement of the parameters, it is a
        measurement of the backend on that occasion.
        """
        row = self._db.execute(
            "SELECT * FROM trials WHERE objective_key = ? AND error IS NULL"
            " AND objectives_json IS NOT NULL ORDER BY trial_id DESC LIMIT 1",
            (objective_key,),
        ).fetchone()
        return _to_trial(row) if row is not None else None

    # --- reading -------------------------------------------------------------

    def run(self, run_id: str) -> Run:
        row = self._db.execute("SELECT * FROM runs WHERE run_id = ?",
                               (run_id,)).fetchone()
        if row is None:
            known = [r["run_id"] for r in
                     self._db.execute("SELECT run_id FROM runs ORDER BY created_at")]
            listed = ", ".join(known[:8]) or "none"
            raise StoreError(f"no run {run_id!r} in {self.path}.\n"
                             f"  Runs here: {listed}.")
        return Run(**{key: row[key] for key in row.keys()})

    def runs(self) -> List[Run]:
        return [Run(**{k: row[k] for k in row.keys()}) for row in
                self._db.execute("SELECT * FROM runs ORDER BY created_at")]

    def trials(self, run_id: str) -> Iterator[Trial]:
        """Every trial of a run, in the order it was made.

        A generator, because a 300-render run carries 300 fingerprints and the
        report streams them rather than holding them all.
        """
        for row in self._db.execute(
                "SELECT * FROM trials WHERE run_id = ? ORDER BY trial_id",
                (run_id,)):
            yield _to_trial(row)

    def verdicts(self, run_id: str) -> List[Dict[str, Any]]:
        return [dict(row) for row in self._db.execute(
            "SELECT v.* FROM verdicts v JOIN trials t USING (trial_id)"
            " WHERE t.run_id = ? ORDER BY v.created_at", (run_id,))]

    def best(self, run_id: str, key: str = "total",
             offset_db: Optional[float] = 0.0) -> Optional[Trial]:
        """The lowest-scoring successful trial by one objective dimension.

        `key` is a dimension name, or `"total"` for the weighted scalar the search
        was minimising. Failed and silent trials are excluded, so this never returns
        "the best match" for something that produced no audio.

        `offset_db` restricts to trials rendered at one input level, and defaults to
        the reference level rather than to all of them. The robustness re-rank stores
        its own renders of the same parameters 6 dB up and down, and those score
        differently for a reason that is nothing to do with the parameters — a
        quieter DI drives the amp less hard, so it can look like a better match. This
        picked one of those. Pass `offset_db=None` to compare across every level.
        """
        best: Optional[Trial] = None
        lowest = float("inf")
        for trial in self.trials(run_id):
            if trial.failed:
                continue
            if offset_db is not None and abs(trial.di_offset_db - offset_db) > 1e-9:
                continue
            value = (trial.objectives or {}).get(key)
            if value is None:
                continue
            if float(value) < lowest:
                best, lowest = trial, float(value)
        return best

    def summary(self, run_id: str) -> Dict[str, Any]:
        """Counts a report and a benchmark both need, computed once.

        `failures` counts errors *and* silent renders together, because both mean
        the same thing to a caller — no usable measurement came back — and
        separating them here would invite reporting only the smaller number. They
        are still available apart, because the causes are different: a silent render
        is a known property of the bare Tone King instantiation, an error is not.

        Cache hits are deliberately absent. There is no column that records one, and
        inferring them from `wall_ms == 0` would be a proxy — the search knows how
        many times it hit the cache and should say so itself.
        """
        total = failures = errors = silent = 0
        wall_ms = 0.0
        for trial in self.trials(run_id):
            total += 1
            if trial.error is not None:
                errors += 1
            if trial.silent:
                silent += 1
            if trial.failed:
                failures += 1
            if trial.wall_ms is not None:
                wall_ms += float(trial.wall_ms)
        return {
            "run_id": run_id,
            "trials": total,
            "failures": failures,
            "errors": errors,
            "silent": silent,
            "failure_rate": (failures / total) if total else 0.0,
            "wall_ms": round(wall_ms, 1),
        }


def _dump(value: Optional[Any]) -> Optional[str]:
    """JSON, with the key normalisation `renderer.canonical_settings` uses.

    A parameter dict may be keyed by tuples — `("delay", "delayTime")` — which JSON
    cannot represent, and `json.dumps` fails on it rather than storing something
    wrong. Normalising here means a caller can hand over whichever spelling it has,
    which is the same courtesy `space._get` extends.
    """
    if value is None:
        return None
    if isinstance(value, Mapping):
        flat = {}
        for key, item in value.items():
            text = key if isinstance(key, str) else "/".join(str(part) for part in key)
            flat[text] = item
        value = flat
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as e:
        raise StoreError(
            f"cannot store this as JSON: {e}\n"
            f"  Trials hold plain numbers, strings and booleans. Convert first — "
            f"`float(x)` for a numpy scalar, `x.tolist()` for an array — so the row "
            f"means the same thing when it is read back. Note that `np.float64` "
            f"happens to pass because numpy 2 makes it a `float` subclass, while "
            f"`np.float32` and `np.int64` do not, so relying on it is relying on an "
            f"accident."
        ) from e


def _load(text: Optional[str]) -> Optional[Any]:
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise StoreError(f"a stored JSON column is malformed: {e}") from e


def _to_trial(row: sqlite3.Row) -> Trial:
    return Trial(
        params=_load(row["params_json"]) or {},
        cache_key=row["cache_key"],
        objective_key=row["objective_key"],
        di_sha=row["di_sha"],
        di_offset_db=float(row["di_offset_db"] or 0.0),
        render_sha=row["render_sha"],
        peak=row["peak"],
        silent=None if row["silent"] is None else bool(row["silent"]),
        wall_ms=row["wall_ms"],
        objectives=_load(row["objectives_json"]),
        fingerprint=_load(row["fingerprint_json"]),
        error=row["error"],
        trial_id=int(row["trial_id"]),
    )


def open_store(out_dir: str) -> Store:
    """The store for a run directory, creating the directory if it is not there.

    A run writes its report next to its store, so the caller has a directory
    already; making it here means `--out-dir` works on a path that does not exist
    yet, which is what a caller naming a run after the song is going to type.
    """
    import pathlib

    directory = pathlib.Path(out_dir)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except NotADirectoryError as e:
        raise StoreError(
            f"cannot use {out_dir} for the run: part of that path is a file.\n"
            f"  --out-dir names a directory the run writes its store, spec and report "
            f"into. Give it a path of its own, one per run."
        ) from e
    except FileExistsError as e:
        raise StoreError(
            f"cannot use {out_dir} for the run: there is already a file with that "
            f"name.\n"
            f"  --out-dir names a directory, not a file. Give it a path of its own, "
            f"one per run."
        ) from e
    except OSError as e:
        # `[Errno 2] No such file or directory` is what a caller gets for `/proc/x`,
        # which is errno rather than an answer.
        raise StoreError(
            f"cannot create the run directory {out_dir}: {e.strerror or e}.\n"
            f"  It has to be somewhere writable — under $NDSP_PRESET_DATA, or "
            f"anywhere you can create a folder."
        ) from e
    return Store(str(directory / STORE_NAME))
