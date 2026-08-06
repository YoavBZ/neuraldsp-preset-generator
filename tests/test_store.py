"""The render store: what it remembers, and what it refuses to.

Every test here is about a way the store could quietly lose or misreport a trial,
because that is the only kind of bug it can have — it holds numbers and hands them
back, and the interesting failures are the ones where it hands back the wrong ones
without saying so.

No `importorskip`: the store is stdlib sqlite3 and has to work on a bare clone.
"""

from __future__ import annotations

import pytest

from match.store import Run, Store, StoreError, Trial, open_store


@pytest.fixture
def store():
    with Store() as memory:
        memory.start_run(Run(run_id="r", pack="morgan", budget=300))
        yield memory


def test_a_trial_round_trips_including_its_tuple_keys(store):
    """A caller may key its parameters by tuples, which JSON cannot represent, and
    `json.dumps` fails on rather than storing something wrong."""
    store.add_trial("r", Trial(params={("delay", "delayTime"): 400.0,
                                       "sw50rEQ/sw50rEQBand1": -3.0},
                               objectives={"total": 0.5}, wall_ms=12.0))
    read, = list(store.trials("r"))
    assert read.params == {"delay/delayTime": 400.0, "sw50rEQ/sw50rEQBand1": -3.0}
    assert read.objectives == {"total": 0.5}
    assert read.trial_id == 1


def test_a_failed_trial_is_stored_and_counted(store):
    """A search that drops its failures reports a lower failure rate than it earned,
    and the exit criterion asks for that rate separately so it cannot hide."""
    store.add_trial("r", Trial(params={"a/b": 1}, objectives={"total": 0.4}))
    store.add_trial("r", Trial(params={"a/b": 2}, error="the backend died"))
    store.add_trial("r", Trial(params={"a/b": 3}, silent=True, peak=0.0,
                               objectives={"total": 0.01}))

    summary = store.summary("r")
    assert summary["trials"] == 3
    assert summary["errors"] == 1
    assert summary["silent"] == 1
    assert summary["failures"] == 2, "an error and a silent render are both failures"
    assert summary["failure_rate"] == pytest.approx(2 / 3)

    # And the silent one is not the best match, however well it scored: a silent
    # render is not evidence about a control.
    assert store.best("r").objectives == {"total": 0.4}


def test_the_cache_never_returns_a_failure(store):
    """One transient backend error would otherwise become permanent for the life of
    the store — and a failure is a measurement of the backend on that occasion, not
    of the parameters."""
    store.add_trial("r", Trial(params={"a/b": 1}, objective_key="k",
                               error="timeout"))
    assert store.cached("k") is None

    store.add_trial("r", Trial(params={"a/b": 1}, objective_key="k",
                               objectives={"total": 0.3}))
    hit = store.cached("k")
    assert hit is not None and hit.objectives == {"total": 0.3}

    # The most recent success, so a re-render after a plugin change wins.
    store.add_trial("r", Trial(params={"a/b": 1}, objective_key="k",
                               objectives={"total": 0.2}))
    assert store.cached("k").objectives == {"total": 0.2}
    assert store.cached("never-rendered") is None


def test_best_stays_at_one_input_level_by_default(store):
    """The robustness re-rank stores its own renders of the same parameters 6 dB up
    and down. A quieter DI drives the amp less hard, so it can look like a better
    match for a reason that has nothing to do with the parameters — and `best()`
    picked one of those before `di_offset_db` existed.
    """
    store.add_trial("r", Trial(params={"a/b": 1}, objectives={"total": 0.60},
                               di_offset_db=0.0))
    store.add_trial("r", Trial(params={"a/b": 1}, objectives={"total": 0.20},
                               di_offset_db=-6.0))

    assert store.best("r").objectives["total"] == pytest.approx(0.60)
    assert store.best("r", offset_db=-6.0).objectives["total"] == pytest.approx(0.20)
    assert store.best("r", offset_db=None).objectives["total"] == pytest.approx(0.20)


def test_a_trial_without_a_run_is_refused(store):
    with pytest.raises(StoreError) as raised:
        store.add_trial("no-such-run", Trial(params={}))
    assert "start_run" in str(raised.value)


def test_a_duplicate_run_is_refused_rather_than_merged(store):
    """Two runs under one id interleave their trials, and every query here groups by
    run — so the failure would surface as a benchmark result that is quietly the
    average of two different searches."""
    with pytest.raises(StoreError) as raised:
        store.start_run(Run(run_id="r"))
    assert "already in" in str(raised.value)


def test_an_unknown_run_names_the_ones_that_are_there(store):
    with pytest.raises(StoreError) as raised:
        store.run("other")
    assert "Runs here: r" in str(raised.value)


def test_a_verdict_needs_a_trial_to_be_about(store):
    trial = store.add_trial("r", Trial(params={}, objectives={"total": 0.5}))
    store.add_verdict(trial.trial_id, "yoav", "closer", "top end is right")
    verdict, = store.verdicts("r")
    assert verdict["listener"] == "yoav" and verdict["choice"] == "closer"

    with pytest.raises(StoreError):
        store.add_verdict(9999, "yoav", "closer")


def test_something_json_cannot_hold_is_refused_with_a_way_out(store):
    """`np.float32` and `np.int64` are not serialisable; `np.float64` happens to pass
    because numpy 2 makes it a `float` subclass, which is an accident rather than a
    guarantee. The message has to say what to do."""
    numpy = pytest.importorskip("numpy")

    with pytest.raises(StoreError) as raised:
        store.add_trial("r", Trial(params={"a/b": numpy.float32(1.0)}))
    assert "float(x)" in str(raised.value)

    with pytest.raises(StoreError):
        store.add_trial("r", Trial(params={"a/b": numpy.array([1.0, 2.0])}))


def test_the_schema_version_is_checked_rather_than_assumed(tmp_path):
    """A store written by a future schema must not be read with today's queries."""
    path = tmp_path / "trials.sqlite3"
    Store(str(path)).close()

    import sqlite3

    db = sqlite3.connect(str(path))
    db.execute("UPDATE meta SET value = '99' WHERE key = 'schema_version'")
    db.commit()
    db.close()

    with pytest.raises(StoreError) as raised:
        Store(str(path))
    assert "schema version 99" in str(raised.value)


def test_a_store_from_an_older_schema_is_named_as_one(tmp_path):
    """The version check ran *after* `executescript`, so it never saw the store it
    existed for: `CREATE TABLE IF NOT EXISTS` is a no-op on an existing table with the
    wrong columns, but `CREATE INDEX ... ON trials(objective_key)` is not, and it
    raised inside the schema. The user got "either empty or a store this tool wrote"
    about a store this tool had written one commit earlier.
    """
    import sqlite3

    path = tmp_path / "trials.sqlite3"
    db = sqlite3.connect(str(path))
    db.executescript(
        "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
        "CREATE TABLE runs (run_id TEXT PRIMARY KEY, created_at REAL NOT NULL);"
        "CREATE TABLE trials (trial_id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " run_id TEXT NOT NULL, params_json TEXT NOT NULL, cache_key TEXT);"
        "INSERT INTO meta VALUES ('schema_version', '1');"
    )
    db.commit()
    db.close()

    with pytest.raises(StoreError) as raised:
        Store(str(path))
    message = str(raised.value)
    assert "schema version 1" in message and "version 3" in message
    assert "store this tool wrote" not in message, (
        "it was a store this tool wrote; blaming the file is the wrong answer"
    )


def test_a_store_predating_the_meta_table_is_refused(tmp_path):
    """There is no version to compare, and `SELECT ... FROM meta` is itself the error
    on such a file — which is why the check reads `sqlite_master` first."""
    import sqlite3

    path = tmp_path / "old.sqlite3"
    db = sqlite3.connect(str(path))
    db.execute("CREATE TABLE trials (trial_id INTEGER PRIMARY KEY)")
    db.commit()
    db.close()

    with pytest.raises(StoreError) as raised:
        Store(str(path))
    assert "no schema version" in str(raised.value)


def test_a_store_survives_being_reopened(tmp_path):
    """Every write commits, because a search interrupted after 200 renders must not
    lose them — that is the case the cache exists for."""
    first = open_store(str(tmp_path / "runs" / "one"))
    first.start_run(Run(run_id="r"))
    first.add_trial("r", Trial(params={"a/b": 1}, objective_key="k",
                               objectives={"total": 0.5}))
    del first                                  # not closed: simulate a hard stop

    again = open_store(str(tmp_path / "runs" / "one"))
    assert [t.params for t in again.trials("r")] == [{"a/b": 1}]
    assert again.cached("k") is not None
    again.close()


def test_open_store_creates_the_directory_it_is_given(tmp_path):
    """`--out-dir` is a path a caller names after the song, which will not exist."""
    store = open_store(str(tmp_path / "deep" / "nested" / "run"))
    assert (tmp_path / "deep" / "nested" / "run" / "trials.sqlite3").exists()
    store.close()


def test_the_summary_does_not_pretend_to_count_cache_hits(store):
    """There is no column that records one, and inferring them from `wall_ms == 0`
    would be a proxy. The search knows and says so itself."""
    store.add_trial("r", Trial(params={"a/b": 1}, wall_ms=0.0,
                               objectives={"total": 0.5}))
    assert "cache_hits" not in store.summary("r")


def test_the_cache_is_keyed_on_the_score_not_just_the_render(store):
    """What is cached is a *distance to a reference*, and that is a finer thing than
    the audio: it also depends on which reference, which loss profile, and which seed
    the prior terms measure from. Keyed on the render address alone, a second run in
    the same directory was served the first run's objectives against different audio —
    silently, with no trial row, so every count in the report was zero."""
    store.add_trial("r", Trial(params={"a/b": 1}, cache_key="same-render",
                               objective_key="score-for-reference-A",
                               objectives={"total": 0.345}))

    assert store.cached("score-for-reference-A").objectives == {"total": 0.345}
    assert store.cached("score-for-reference-B") is None, (
        "the same audio against a different reference is a different score"
    )
    # And the render address is still recorded, because it is what identifies the
    # audio for anything that wants to re-render it.
    read, = list(store.trials("r"))
    assert read.cache_key == "same-render"
    assert read.objective_key == "score-for-reference-A"


def test_a_file_that_is_not_a_store_says_so(tmp_path):
    """`sqlite3.connect` succeeds on any readable file — a wav, a preset, a
    half-written download — and it is the first CREATE TABLE that fails, with a bare
    `DatabaseError` naming nothing a person can act on."""
    blocker = tmp_path / "notastore.bin"
    blocker.write_bytes(b"RIFF" + b"\x00" * 200)

    with pytest.raises(StoreError) as raised:
        Store(str(blocker))
    assert "either empty or a store this tool wrote" in str(raised.value)


def test_a_trial_cannot_both_fail_and_score():
    """Stated and unenforced, which held only because M4 has one writer. A row
    carrying both says the render failed *and* scored, and every reader would have to
    pick one to believe."""
    with pytest.raises(StoreError) as raised:
        Trial(params={}, error="died", objectives={"total": 0.1})
    assert "cannot both fail and score" in str(raised.value)

    # Either alone is fine.
    assert Trial(params={}, error="died").failed
    assert not Trial(params={}, objectives={"total": 0.1}).failed


def test_a_trial_with_no_objectives_is_a_failure():
    """`Evaluator.evaluate` stores `objectives=None` on a render that came back but
    produced nothing the profile could weight — a real row, and not a success. Without
    that term such a trial reported as fine and could be returned as the best match."""
    assert Trial(params={}, objectives=None).failed
    assert Trial(params={}, objectives={"total": 0.4}).failed is False

    with Store() as store:
        store.start_run(Run(run_id="r"))
        store.add_trial("r", Trial(params={"a/b": 1}, objectives=None))
        store.add_trial("r", Trial(params={"a/b": 2}, objectives={"total": 0.9}))
        assert store.summary("r")["failures"] == 1
        assert store.best("r").objectives == {"total": 0.9}
