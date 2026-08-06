"""The two M4 scripts, run as a person runs them.

These had no tests at all — 490 lines of the code a guitarist actually touches,
covered only by a mention inside a docstring. What is checked here is not the DSP
(that is `test_search.py`'s job) but the things only a real invocation exercises:
that the whole loop closes, that the output names its next step, and that an ordinary
mistake produces a sentence rather than a stack.

The budgets are small and the DI is short, so the whole file is a few seconds.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("scipy", reason="needs the analysis extra")
pytest.importorskip("soundfile", reason="needs the analysis extra")

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "samples" / "Example_Clean_PR12.xml"


def run(script: str, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
        capture_output=True, text=True, cwd=ROOT,
    )


@pytest.fixture(scope="module")
def audio(tmp_path_factory):
    """A reference rendered through the synthetic chain, and the DI behind it."""
    from analysis import refchain
    from tests import fixtures_audio as fx

    directory = tmp_path_factory.mktemp("audio")
    di = fx.plucks(seconds=2.0, gap=0.9, seed=5)
    fx.write_wav(str(directory / "ref.wav"), refchain.render(di, {
        "sw50rAmp/sw50rVolume": 82.0, "sw50rAmp/sw50rTreble": 20.0}))
    fx.write_wav(str(directory / "probe.wav"), di)
    return directory


# --- the whole loop ---------------------------------------------------------


def test_a_match_produces_a_spec_a_preset_and_a_report(audio, tmp_path):
    """And the spec applies. This is the claim the module docstring makes — that the
    winner is written by the same validated path as a hand-authored preset — and it is
    only true if `apply_spec.py` accepts what came out."""
    out = tmp_path / "run"
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--reference-mode", "probe",
               "--probe-di", audio / "probe.wav", "--amp", "sw50r",
               "--budget", "60", "--shortlist", "2", "--out-dir", out)
    assert done.returncode == 0, done.stdout + done.stderr

    assert (out / "trials.sqlite3").exists()
    assert (out / "report.html").exists()
    spec = json.loads((out / "match-1.json").read_text())
    assert spec["parameters"], "a spec with no parameters is not a match"
    assert (out / "match-2.json").exists(), "--shortlist 2 means two of them"

    # The next command, printed rather than left in a docstring the user never sees.
    assert "apply_spec.py" in done.stdout

    applied = run("apply_spec.py", "--template", TEMPLATE,
                  "--spec", out / "match-1.json", "--out", tmp_path / "matched.xml")
    assert applied.returncode == 0, applied.stdout + applied.stderr

    shown = run("show.py", tmp_path / "matched.xml", "--text")
    assert shown.returncode == 0, shown.stderr
    assert "match 1" in shown.stdout, "the preset carries the name the spec gave it"


def test_the_run_reports_its_caveats_and_its_cost(audio, tmp_path):
    """The number is not the deliverable on its own. A run that printed a distance and
    no caveats would be presenting a measurement as a verdict."""
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--reference-mode", "probe",
               "--probe-di", audio / "probe.wav", "--amp", "sw50r",
               "--budget", "60", "--out-dir", tmp_path / "run")
    assert done.returncode == 0, done.stderr

    assert "distance to the reference" in done.stdout
    assert "renders in" in done.stdout
    assert "caveats — read them before trusting the number" in done.stdout
    assert "parameters searched" in done.stdout


def test_what_the_reference_could_not_be_measured_for_is_said(audio, tmp_path):
    """`Fingerprint.caveats()` is documented as "everything a report has to say out loud
    about this measurement", and `fingerprint.py` and `compare_audio.py` both call it.
    This script reimplemented one of its five clauses — the `mix` one — and dropped the
    rest, so a reference with no sustained note to measure distortion from said so under
    `compare_audio.py` and said nothing here, after an hour of renders."""
    out = tmp_path / "run"
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--reference-mode", "separated_stem",
               "--probe-di", audio / "probe.wav", "--amp", "sw50r",
               "--budget", "60", "--out-dir", out)
    assert done.returncode == 0, done.stderr

    from analysis import io
    from analysis.fingerprint import fingerprint

    target = fingerprint(io.load(str(audio / "ref.wav")), regime="separated_stem",
                         excerpt_s=None)
    expected = target.caveats()
    assert expected, "the fixture has to produce some, or this asserts nothing"
    for text in expected:
        assert text in done.stdout, f"dropped: {text}"

    # And no caveat is printed twice: the reference-side list and the inversion's own
    # overlap in subject (both talk about delay and modulation) and must not in wording.
    printed = [line.strip()[2:] for line in done.stdout.splitlines()
               if line.startswith("  - ")]
    assert len(printed) == len(set(printed)), (
        f"duplicated: {[c for c in printed if printed.count(c) > 1]}"
    )


def test_a_report_is_self_contained(audio, tmp_path):
    """It has to open a year later next to the store, with no network."""
    out = tmp_path / "run"
    run("match_preset.py", "--template", TEMPLATE,
        "--reference", audio / "ref.wav", "--reference-mode", "probe",
        "--probe-di", audio / "probe.wav", "--amp", "sw50r",
        "--budget", "60", "--out-dir", out)

    html = (out / "report.html").read_text()
    for forbidden in ("http://", "https://", "<script", "src=", "@import"):
        assert forbidden not in html, forbidden
    assert "<svg" in html


def test_the_store_holds_what_the_run_reported(audio, tmp_path):
    """The store is the record, so its counts have to be the ones printed.

    Two counts, because there are two: the renders the search spent against the budget,
    which are the rows in the store, and the ones made outside it — the template, the
    inversion's probe, one per shortlisted candidate for the report's overlays. The
    headline used to be the first while claiming to be the total, so a run that printed
    293 had made 298. On the synthetic chain that is 5 spare seconds; on a real plugin
    backend it is 5 renders nobody is accounting for.
    """
    out = tmp_path / "run"
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--reference-mode", "probe",
               "--probe-di", audio / "probe.wav", "--amp", "sw50r",
               "--budget", "80", "--shortlist", "2", "--out-dir", out)
    assert done.returncode == 0, done.stdout + done.stderr

    from match.store import Store

    total = int(done.stdout.split(" renders in")[0].split()[-1])
    budgeted = int(done.stdout.split(" of them against the")[0].split("\n")[-1])
    outside = int(done.stdout.split("budget; ")[1].split()[0])

    with Store(str(out / "trials.sqlite3")) as store:
        run_row, = store.runs()
        assert run_row.pack == "morgan" and run_row.budget == 80
        assert run_row.regime == "probe"
        # Only the search writes rows, so the store's count is the budgeted one.
        assert store.summary(run_row.run_id)["trials"] == budgeted

    assert total == budgeted + outside, "the arithmetic has to close"
    # The template's render, the inversion's probe, and one per shortlisted candidate.
    assert outside == 2 + len(list(out.glob("match-*.json")))


# --- the mistakes a person makes --------------------------------------------


def test_every_reference_mode_offered_is_one_the_fingerprint_accepts():
    """`--reference-mode` had five choices and two of them did not exist. `fingerprint()`
    refuses an unknown regime by name, so `--reference-mode reamp` passed argparse and
    died with "unknown regime 'reamp'"; `--reference-mode isolated` did the same; and
    `separated_stem`, which the fingerprint scores at 0.55, could not be chosen at all.

    Two dead choices and one missing one, in the flag that decides how much the whole run
    is worth — and the help text glossed all five as though they worked. The list is a
    literal in `match_preset.py` because `build_parser()` runs before the missing-extra
    check and must not need numpy to print `--help`, so this is what stops it drifting.
    """
    import importlib.util

    from analysis.fingerprint import REGIMES as REAL

    spec = importlib.util.spec_from_file_location(
        "_match_preset_for_test", ROOT / "scripts" / "match_preset.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert set(module.REGIMES) == set(REAL), (
        f"offered but not accepted: {sorted(set(module.REGIMES) - set(REAL))}; "
        f"accepted but not offered: {sorted(set(REAL) - set(module.REGIMES))}"
    )


@pytest.mark.parametrize("mode", ["paired_di", "isolated_stem", "separated_stem",
                                  "mix", "probe"])
def test_each_reference_mode_actually_runs(audio, tmp_path, mode):
    """Not just present in the list: a regime that argparse accepts and the fingerprint
    then refuses is a flag that fails after the user has committed to a run."""
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--reference-mode", mode,
               "--probe-di", audio / "probe.wav", "--amp", "sw50r",
               "--budget", "60", "--out-dir", tmp_path / mode)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "unknown regime" not in done.stderr


@pytest.mark.parametrize("extra,expected", [
    (["--budget", "0"], "must be at least 1"),
    (["--loss-profile", "nope"], "unknown loss profile"),
    (["--renderer", "swift"], "not built yet"),
    (["--reference-mode", "reamp"], "invalid choice"),
])
def test_a_bad_flag_is_a_sentence_not_a_stack(audio, tmp_path, extra, expected):
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--probe-di", audio / "probe.wav",
               "--amp", "sw50r", "--out-dir", tmp_path / "run", *extra)
    assert done.returncode != 0
    assert expected in done.stderr, done.stderr
    assert "Traceback" not in done.stderr


def test_a_reference_that_is_not_audio_says_so(tmp_path):
    """`soundfile` raises a `RuntimeError`, which is the one remaining way an ordinary
    mistake reached a person as fifteen frames of traceback."""
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", ROOT / "pyproject.toml", "--amp", "sw50r",
               "--out-dir", tmp_path / "run")
    assert done.returncode != 0
    assert "Traceback" not in done.stderr, done.stderr
    assert "Format not recognised" in done.stderr


def test_a_silent_reference_is_refused_before_the_renders(tmp_path):
    """Matching against silence is not a caveat, it is an hour of renders for an
    answer that means nothing — and it used to produce a report headed "42% closer"."""
    import numpy as np

    from tests import fixtures_audio as fx

    silent = tmp_path / "silent.wav"
    fx.write_wav(str(silent), np.zeros((48000 * 2, 1)))
    done = run("match_preset.py", "--template", TEMPLATE, "--reference", silent,
               "--reference-mode", "probe", "--amp", "sw50r",
               "--budget", "60", "--out-dir", tmp_path / "run")

    assert done.returncode != 0
    assert "silent" in done.stderr, done.stderr
    assert not (tmp_path / "run" / "match-1.json").exists()


def test_a_template_that_is_not_a_preset_is_refused_before_the_renders(audio, tmp_path):
    """`parse_file` reads anything and `build_preset` yields zero parameters, so
    `--template pyproject.toml` searched from an empty seed, spent the whole budget,
    wrote a report with a distance in it, and printed an `apply_spec.py` command that
    refuses the same file — the one downstream tool that checked was the one this run
    told the user to go and run next."""
    out = tmp_path / "run"
    done = run("match_preset.py", "--template", ROOT / "pyproject.toml",
               "--reference", audio / "ref.wav", "--reference-mode", "probe",
               "--amp", "sw50r", "--budget", "60", "--out-dir", out)

    assert done.returncode != 0
    assert "does not look like a plugin preset" in done.stderr, done.stderr
    assert "Traceback" not in done.stderr
    assert not (out / "match-1.json").exists(), "and nothing was written"
    assert not (out / "report.html").exists()


def test_a_budget_that_cannot_afford_a_round_says_so_first_and_names_the_number(
        audio, tmp_path):
    """Two messages used to describe this one fact, and the one that fired on Morgan's
    18 searchable parameters said "raise --budget to at least 12 more than the fixed
    costs above" — with nothing above having printed a fixed cost. It arrived ninth of
    eleven caveats, below a note about palm-muted playing, while the headline it
    invalidates was the second line of the output."""
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--reference-mode", "probe",
               "--probe-di", audio / "probe.wav", "--amp", "sw50r",
               "--budget", "40", "--out-dir", tmp_path / "run")
    assert done.returncode == 0, done.stderr

    caveats = [line.strip()[2:] for line in done.stdout.splitlines()
               if line.startswith("  - ")]
    assert len(caveats) > 8, "the point is that this one is not buried among the rest"
    first = caveats[0]
    assert "the optimiser never ran" in first, (
        f"it arrived at position {[i for i, c in enumerate(caveats) if 'never ran' in c]}"
    )

    # And it names a number to raise --budget to, which then works.
    import re

    target = int(re.search(r"Raise --budget to at least (\d+)", first).group(1))
    assert target > 40
    better = run("match_preset.py", "--template", TEMPLATE,
                 "--reference", audio / "ref.wav", "--reference-mode", "probe",
                 "--probe-di", audio / "probe.wav", "--amp", "sw50r",
                 "--budget", str(target), "--out-dir", tmp_path / "again")
    assert better.returncode == 0, better.stderr
    assert "the optimiser never ran" not in better.stdout, (
        f"raising --budget to the {target} it asked for still did not buy a round"
    )


def test_a_reused_out_dir_does_not_leave_the_previous_runs_specs(audio, tmp_path):
    """A second run with a shorter --shortlist left match-2.json and match-3.json from
    the first beside the new match-1.json and the new report, with nothing in either
    file saying which run it came from — so applying the runner-up gave you the
    *previous* search's runner-up."""
    out = tmp_path / "run"
    common = ["--template", TEMPLATE, "--reference", audio / "ref.wav",
              "--reference-mode", "probe", "--probe-di", audio / "probe.wav",
              "--amp", "sw50r", "--budget", "60", "--out-dir", out]

    assert run("match_preset.py", *common, "--shortlist", "3").returncode == 0
    assert (out / "match-3.json").exists()

    assert run("match_preset.py", *common, "--shortlist", "1").returncode == 0
    assert sorted(p.name for p in out.glob("match-*.json")) == ["match-1.json"], (
        "the second run's shortlist is one, so one spec is what the directory holds"
    )


def test_a_template_from_another_pack_names_the_pack_it_is_from(audio, tmp_path):
    """It used to say "the template does not say which amp is selected" about a
    template that says PR12, and then advise a Morgan amp."""
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--reference-mode", "probe",
               "--pack", "toneking", "--budget", "60",
               "--out-dir", tmp_path / "run")
    assert done.returncode != 0
    assert "PR12" in done.stderr and "morgan" in done.stderr, done.stderr
    assert "Traceback" not in done.stderr


def test_an_out_dir_that_is_a_file_says_which_part_of_the_path(audio, tmp_path):
    blocker = tmp_path / "afile"
    blocker.write_text("not a directory")
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--reference-mode", "probe",
               "--amp", "sw50r", "--budget", "60", "--out-dir", blocker)

    assert done.returncode != 0
    assert "names a directory" in done.stderr, done.stderr
    assert "Errno" not in done.stderr, "errno is not an answer"


# --- the benchmark ----------------------------------------------------------


def test_the_benchmark_runs_and_reports_every_number_separately(tmp_path):
    """Small, but the whole shape: three arms, four measures, and a verdict that says
    which baselines were beaten."""
    out = tmp_path / "bench.json"
    done = run("benchmark_match.py", "--targets", "2", "--budget", "30",
               "--seconds", "1.5", "--json", out)
    assert done.returncode in (0, 1), done.stdout + done.stderr

    for header in ("param MAE", "selector", "objective", "renders", "fail%"):
        assert header in done.stdout, header
    for arm in ("recipe", "inversion", "full"):
        assert arm in done.stdout
    assert ("SHIPS" in done.stdout) or ("DOES NOT SHIP" in done.stdout)
    # "MAE" is jargon wherever the user reads it, so it is expanded there.
    assert "mean absolute error" in done.stdout

    written = json.loads(out.read_text())
    assert set(written["summaries"]) == {"recipe", "inversion", "full"}
    assert len(written["outcomes"]) == 6, "two targets by three arms"
    assert isinstance(written["ships"], bool)


def test_the_benchmarks_exit_code_is_the_verdict(tmp_path):
    """So it can gate something. Zero when it ships, non-zero when it does not."""
    done = run("benchmark_match.py", "--targets", "1", "--budget", "30",
               "--seconds", "1.5", "--arms", "full")
    assert done.returncode == 1, "with no baseline there is nothing to beat"
    assert "was not run" in done.stdout


def test_an_unknown_arm_is_refused_by_name(tmp_path):
    done = run("benchmark_match.py", "--targets", "1", "--arms", "magic")
    assert done.returncode != 0
    assert "unknown arm(s) magic" in done.stderr
    assert "recipe, inversion, full" in done.stderr
