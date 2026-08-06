"""The preset tools must keep working on a bare clone.

`pyproject.toml` declares `dependencies = []`, and that is a promise: someone
who clones this repository and runs `show.py` against their own preset should
not need numpy to do it. Adding audio analysis put a numpy-shaped temptation in
the tree, so this test holds the line by running the tools in a subprocess with
every analysis package made unimportable.

If this fails, something in `format/`, `packs/` or one of the four preset
scripts grew a top-level import of a third-party module. Move it inside the
function that needs it, or behind an extra.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import textwrap

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BLOCKED = ("numpy", "scipy", "soundfile", "pyloudnorm", "pedalboard")

# A blocker installed ahead of the real packages on sys.path. Importing any of
# them raises, which is what a bare clone looks like from the inside.
BLOCKER = textwrap.dedent(
    """
    import sys
    BLOCKED = {blocked!r}

    class Blocker:
        def find_module(self, name, path=None):
            return self if name.split(".")[0] in BLOCKED else None

        def load_module(self, name):
            raise ImportError(f"{{name}} is not installed (blocked by the test)")

        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in BLOCKED:
                raise ImportError(f"{{name}} is not installed (blocked by the test)")
            return None

    sys.meta_path.insert(0, Blocker())
    """
)


def run_without_analysis(code: str, blocked=BLOCKED):
    script = BLOCKER.format(blocked=blocked) + textwrap.dedent(code)
    return subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, cwd=ROOT
    )


def test_the_blocker_actually_blocks():
    """Guard the guard: a test that cannot fail proves nothing."""
    result = run_without_analysis("import numpy")
    assert result.returncode != 0
    assert "not installed" in result.stderr


@pytest.mark.parametrize("module", ["format.parser", "format.writer", "format.structured",
                                    "format.translate", "packs.loader", "packs.recipes",
                                    "packs.timing", "packs.observed", "packs.paths"])
def test_core_modules_import_with_no_third_party_packages(module):
    result = run_without_analysis(f"import {module}")
    assert result.returncode == 0, result.stderr


def test_show_runs_on_the_bundled_preset_with_no_third_party_packages():
    result = run_without_analysis(
        """
        import runpy, sys
        sys.argv = ["show.py", "samples/Example_Clean_PR12.xml", "--text"]
        runpy.run_path("scripts/show.py", run_name="__main__")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "Example Clean PR12" in result.stdout


def test_apply_spec_runs_with_no_third_party_packages(tmp_path):
    spec = tmp_path / "spec.json"
    spec.write_text(
        '{"name": "Bare Clone", "parameters": ['
        '{"module": "sw50rAmp", "key": "sw50rVolume", "value": 62}]}'
    )
    out = tmp_path / "out.xml"
    result = run_without_analysis(
        f"""
        import runpy, sys
        sys.argv = ["apply_spec.py", "--template", "samples/Example_Clean_PR12.xml",
                    "--spec", {str(spec)!r}, "--strip-irs", "--out", {str(out)!r}]
        runpy.run_path("scripts/apply_spec.py", run_name="__main__")
        """
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()


@pytest.mark.parametrize("script,argv", [
    ("show.py", ["samples/Example_Clean_PR12.xml", "--text"]),
    ("bootstrap_pack.py", ["--help"]),
])
def test_the_preset_scripts_do_not_touch_the_analysis_package_at_all(script, argv,
                                                                    tmp_path):
    """Stricter than blocking numpy: this blocks `analysis` itself.

    Blocking numpy only proves the *analysis package* degrades gracefully — `analysis`
    still imports, and `from analysis import AnalysisUnavailable` still succeeds. So a
    top-level import of `analysis` in shared plumbing passed every test here while
    breaking the actual bare clone, where the directory may not be present at all.

    That is not hypothetical: `scripts/_cli.py`'s `guarded()` imported `analysis` for one
    exception name, and `bootstrap_pack.py` — run against a partial tree, which is what
    `tests/test_skills.py` builds and what a plugin install looks like — died with
    `ModuleNotFoundError: No module named 'analysis'` from inside the very handler that
    exists to stop tracebacks reaching people. CI missed it because CI installs the
    package, which makes `analysis` importable from any working directory.
    """
    result = run_without_analysis(
        f"""
        import runpy, sys
        sys.argv = [{script!r}] + {argv!r}
        runpy.run_path({f"scripts/{script}"!r}, run_name="__main__")
        """,
        blocked=BLOCKED + ("analysis",),
    )
    assert "No module named 'analysis'" not in result.stderr, result.stderr
    assert result.returncode == 0, result.stderr


def test_analysis_entry_points_explain_themselves_without_the_extra():
    """A missing extra prints one line a person can act on, not a traceback."""
    result = run_without_analysis(
        """
        import runpy, sys
        sys.argv = ["fingerprint.py", "samples/Example_Clean_PR12.xml"]
        runpy.run_path("scripts/fingerprint.py", run_name="__main__")
        """
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "pip install -e '.[analysis]'" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("module", ["analysis", "analysis.io", "analysis.features",
                                    "analysis.align", "analysis.fingerprint",
                                    "analysis.compare", "analysis.refchain",
                                    "match", "match.renderer", "match.renderer_synth",
                                    "match.space", "match.invert", "match.search",
                                    "match.store", "match.report",
                                    "match.benchmark"])
def test_analysis_modules_import_without_numpy(module):
    """Importing is free; only calling costs a dependency.

    This is what lets the CLIs import their own error message. Every numpy use
    in this package is inside a function for that reason.
    """
    result = run_without_analysis(f"import {module}")
    assert result.returncode == 0, result.stderr


def test_the_analysis_package_imports_without_numpy():
    """Importing `analysis` must not import numpy: the CLIs import it to reach
    the error message that explains numpy is missing."""
    result = run_without_analysis(
        """
        import analysis
        from analysis import AnalysisUnavailable, require
        try:
            require("test")
        except AnalysisUnavailable as e:
            assert "pip install" in str(e)
            print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_the_render_store_works_with_no_third_party_packages():
    """`match/store.py` is stdlib sqlite3 and its docstring rests on that: a store a
    person cannot open is a store they will not trust, and a bare clone has to be able
    to read one. Asserted by *use* rather than by import, because `import` proves
    nothing about a module whose numpy is all inside functions.
    """
    result = run_without_analysis(
        """
        import tempfile, pathlib
        from match.store import Run, Store, Trial, open_store

        with tempfile.TemporaryDirectory() as directory:
            store = open_store(directory)
            store.start_run(Run(run_id="bare", pack="morgan", budget=10))
            store.add_trial("bare", Trial(params={("delay", "delayTime"): 400.0},
                                          objective_key="k",
                                          objectives={"total": 0.5}))
            assert store.cached("k").objectives == {"total": 0.5}
            assert store.summary("bare")["trials"] == 1
            assert store.best("bare").params == {"delay/delayTime": 400.0}
            store.close()
        print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_the_report_needs_no_third_party_packages_either():
    """Inline SVG and inline CSS, so there is nothing for it to need. Worth pinning:
    reaching for matplotlib would be the obvious way to add a chart, and it would put
    the report behind an extra."""
    result = run_without_analysis(
        """
        from match.report import render_report
        from match.search import Candidate

        html = render_report(
            run_id="bare", target=None,
            shortlist=[Candidate(values={}, objectives={"total": 0.4}, total=0.4)],
            caveats=["something to distrust"],
            convergence=[{"total": 0.9}, {"total": 0.4}],
            summary={"trials": 2, "failures": 0},
        )
        assert "<svg" in html and "something to distrust" in html
        print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_match_preset_explains_the_missing_extra_rather_than_failing():
    """It is the first thing a guitarist runs, and on a bare clone it has to say what
    to install rather than trace."""
    result = run_without_analysis(
        """
        import runpy, sys
        sys.argv = ["match_preset.py", "--template", "samples/Example_Clean_PR12.xml",
                    "--reference", "/tmp/none.wav", "--out-dir", "/tmp/none"]
        runpy.run_path("scripts/match_preset.py", run_name="__main__")
        """
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "pip install -e '.[analysis]'" in result.stderr
    assert "Traceback" not in result.stderr
