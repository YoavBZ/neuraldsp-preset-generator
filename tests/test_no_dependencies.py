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


def run_without_analysis(code: str):
    script = BLOCKER.format(blocked=BLOCKED) + textwrap.dedent(code)
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
                                    "analysis.compare"])
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
