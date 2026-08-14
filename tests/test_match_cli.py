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
    summary = json.loads((out / "summary.json").read_text())
    assert summary["schema"] == "tone-match-summary-v1"
    assert summary["reference"]["regime"] == "probe"
    assert summary["reference"]["regime_confidence"] == 1.0
    assert summary["reference"]["excerpt"] == {
        "start_s": 0.0,
        "end_s": pytest.approx(2.0, abs=0.01),
        "duration_s": pytest.approx(2.0, abs=0.01),
        "source_duration_s": pytest.approx(2.0, abs=0.01),
        "requested_s": 20.0,
        "policy": "full_source",
    }
    assert summary["renderer"]["renderer_id"] == "synthetic"
    assert summary["inversion"]["used"] is True
    assert summary["inversion"]["changes"]
    assert summary["inversion"]["detail"]["signal_path"] == "sw50r"
    assert not any(change["path"] == "/selectedAmp"
                   for change in summary["inversion"]["changes"]), (
        "explicit --amp must select SW50R before the inversion probe is rendered"
    )
    assert summary["search"]["searched"]
    assert summary["search"]["sensitivity_floor_observations"] == 1
    command = summary["command_accounting"]
    assert command["total_renders"] == (
        command["budgeted_renders"] + command["outside_budget_renders"]
    )
    assert command["outside_budget_by_source"] == {
        "template": 1,
        "inversion_probe": 1,
        "report_candidates": 2,
    }
    assert all(candidate["trial_id"] is not None
               for candidate in summary["shortlist"])
    assert all(candidate["fingerprint"] is not None
               for candidate in summary["shortlist"])
    assert summary["shortlist"][0]["fingerprint_delta"]
    assert summary["caveats"]
    spec = json.loads((out / "match-1.json").read_text())
    assert spec["parameters"], "a spec with no parameters is not a match"
    assert (out / "match-2.json").exists(), "--shortlist 2 means two of them"

    # The next command, printed rather than left in a docstring the user never sees.
    assert "apply_spec.py" in done.stdout
    assert "reference excerpt 0.000000–2.000000 s" in done.stdout

    applied = run("apply_spec.py", "--template", TEMPLATE,
                  "--spec", out / "match-1.json", "--out", tmp_path / "matched.xml")
    assert applied.returncode == 0, applied.stdout + applied.stderr

    shown = run("show.py", tmp_path / "matched.xml", "--text")
    assert shown.returncode == 0, shown.stderr
    assert "match 1" in shown.stdout, "the preset carries the name the spec gave it"

    listened = run(
        "log_match_verdict.py", "--run-dir", out, "--candidate", "1",
        "--choice", "candidate", "--listener", "end-to-end-test",
        "--comment", "candidate is closer", "--data-dir", tmp_path / "user-data",
    )
    assert listened.returncode == 0, listened.stdout + listened.stderr
    assert (tmp_path / "user-data" / "packs" / "morgan" /
            "learned-tones.md").exists()


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


def test_match_and_fingerprint_share_the_same_excerpt_default():
    """Preflight must measure the target the expensive match will actually use."""
    import importlib.util

    from analysis.fingerprint import DEFAULT_EXCERPT_S

    spec = importlib.util.spec_from_file_location(
        "_match_preset_excerpt_test", ROOT / "scripts" / "match_preset.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    common = ["--template", str(TEMPLATE), "--reference", "reference.wav",
              "--out-dir", "run"]
    parsed = module.build_parser().parse_args(common)
    assert module.resolved_excerpt(parsed.excerpt, "mix") == DEFAULT_EXCERPT_S
    assert module.resolved_excerpt(parsed.excerpt, "paired_di") is None
    explicit_all = module.build_parser().parse_args([*common, "--excerpt", "0"])
    assert module.resolved_excerpt(explicit_all.excerpt, "mix") is None


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


def test_paired_profile_reaches_the_search_and_records_residual(audio, tmp_path):
    out = tmp_path / "paired"
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--reference-mode", "paired_di",
               "--probe-di", audio / "probe.wav", "--loss-profile", "paired-v1",
               "--amp", "sw50r", "--budget", "60", "--out-dir", out)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "paired waveform residual was measured" in done.stdout

    import sqlite3

    db = sqlite3.connect(out / "trials.sqlite3")
    rows = [json.loads(row[0]) for row in db.execute(
        "select objectives_json from trials where objectives_json is not null")]
    db.close()
    assert rows and all("residual" in row for row in rows)

    summary = json.loads((out / "summary.json").read_text())
    assert summary["loss_profile"] == "paired-v1"
    assert summary["reference"]["regime"] == "paired_di"
    assert summary["reference"]["regime_confidence"] == 1.0
    assert all("residual" in candidate["objectives"]
               for candidate in summary["shortlist"])


def test_paired_profile_refuses_a_different_performance_mode(audio, tmp_path):
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--reference-mode", "probe",
               "--probe-di", audio / "probe.wav", "--loss-profile", "paired-v1",
               "--amp", "sw50r", "--budget", "60",
               "--out-dir", tmp_path / "wrong-mode")
    assert done.returncode != 0
    assert "only meaningful" in done.stderr
    assert "--reference-mode paired_di" in done.stderr
    assert "Traceback" not in done.stderr


def test_paired_profile_refuses_an_excerpt_instead_of_mixing_scopes(audio, tmp_path):
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--reference-mode", "paired_di",
               "--probe-di", audio / "probe.wav", "--loss-profile", "paired-v1",
               "--excerpt", "1", "--amp", "sw50r", "--budget", "60",
               "--out-dir", tmp_path / "paired-excerpt")
    assert done.returncode != 0
    assert "complete reamp and DI" in done.stderr
    assert "Traceback" not in done.stderr


@pytest.mark.parametrize("extra,expected", [
    (["--budget", "0"], "must be at least 1"),
    (["--excerpt", "-1"], "must be zero or greater"),
    (["--loss-profile", "nope"], "unknown loss profile"),
    # `swift` used to belong here. It is M5 and it is built, so on a machine with
    # the plugin it is a working backend rather than a bad flag; `pedalboard` is
    # the one still unbuilt and is what this now asserts about.
    (["--renderer", "pedalboard"], "not built yet"),
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


def test_an_excerpt_too_short_to_measure_is_refused_before_rendering(audio, tmp_path):
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--reference-mode", "probe",
               "--excerpt", "0.5", "--amp", "sw50r", "--budget", "60",
               "--out-dir", tmp_path / "short-excerpt")
    assert done.returncode != 0
    assert "selected reference excerpt is 0.50 s" in done.stderr
    assert not (tmp_path / "short-excerpt" / "trials.sqlite3").exists()


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


def test_tone_king_template_seeds_top_level_controls_and_the_selected_channel(tmp_path):
    """Tone King's whole writable namespace is top-level.

    Looking ParamSpecs up by Dimension.path omitted the canonical leading slash,
    so every value was skipped and a run used the plugin's boot state instead of
    its template. The channel selector was absent too, leaving both channels live.
    """
    import struct

    from match import space as space_module
    from scripts.match_preset import _seed_from_template

    def text(value: str) -> bytes:
        body = value.encode()
        return bytes([0x01, len(body) + 2, 0x05]) + body + b"\x00"

    def record(key: str, value: float) -> bytes:
        return (b"PARAM\x00\x01\x02id\x00" + text(key)
                + b"value\x00\x01\x09\x04" + struct.pack("<d", value) + b"\x00")

    template = tmp_path / "ToneKing.xml"
    template.write_bytes(
        b"neural_dsp_toneking\x00"
        + record("ampType", 1.0)
        + record("leadAmpVolume", 0.72)
        + record("rhythmAmpVolume", 0.38)
    )
    space = space_module.build("toneking")
    seed, _ = _seed_from_template(template, space, "toneking")
    live = {dimension.path for dimension in space.active(seed)}

    assert seed[("", "ampType")] == "1"
    assert seed[("", "leadAmpVolume")] == pytest.approx(0.72)
    assert seed[("", "rhythmAmpVolume")] == pytest.approx(0.38)
    assert "leadAmpVolume" in live
    assert "rhythmAmpVolume" not in live


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


# --- --enumerate ------------------------------------------------------------
# The topology stage was written and tested in M4 and no caller ever reached it,
# so every run left the cabinet, the microphone and the amp wherever the template
# had them and said so in a caveat. These cover the wiring, not `topologies()`.

def test_list_enumerable_names_the_paths_and_their_positions(tmp_path):
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", ROOT / "pyproject.toml", "--amp", "sw50r",
               "--out-dir", tmp_path / "run", "--list-enumerable")
    assert done.returncode == 0, done.stderr
    assert "sw50rAmp/sw50rBright" in done.stdout
    assert "cabParameters/leftMicType" not in done.stdout, (
        "the synthetic backend does not model microphone type, so listing it "
        "would advertise several topologies that all render identically"
    )
    assert "2 positions" in done.stdout, done.stdout
    assert "(switch)" in done.stdout
    # It exits before reading the reference, which here is not audio at all.
    assert "Format not recognised" not in done.stderr


def test_amp_display_alias_is_normalised_before_building_the_space(tmp_path):
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", ROOT / "pyproject.toml", "--amp", "SW50R",
               "--out-dir", tmp_path / "run", "--list-enumerable")

    assert done.returncode == 0, done.stderr
    assert "sw50rAmp/sw50rBright" in done.stdout


def test_benchmark_amp_display_alias_is_normalised_before_the_space():
    done = run("benchmark_match.py", "--amp", "SW50R", "--list-enumerable")

    assert done.returncode == 0, done.stderr
    assert "sw50rAmp/sw50rBright" in done.stdout


def test_benchmark_refuses_a_renderer_that_cannot_search_the_pack():
    done = run(
        "benchmark_match.py", "--pack", "toneking", "--amp", "lead",
        "--renderer", "synthetic", "--list-enumerable",
    )

    assert done.returncode != 0
    assert "supports no searchable controls for toneking/lead" in done.stderr
    assert "--renderer swift" in done.stderr


def test_match_refuses_a_renderer_that_cannot_search_the_pack(tmp_path):
    done = run(
        "match_preset.py", "--pack", "toneking", "--renderer", "synthetic",
        "--template", TEMPLATE, "--reference", ROOT / "pyproject.toml",
        "--out-dir", tmp_path / "run", "--list-enumerable",
    )

    assert done.returncode != 0
    assert "supports no searchable controls for pack toneking" in done.stderr
    assert "--renderer swift" in done.stderr


def test_an_unenumerable_path_is_refused_by_name(audio, tmp_path):
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--amp", "sw50r",
               "--out-dir", tmp_path / "run", "--enumerate", "sw50rAmp/sw50rVolume")
    assert done.returncode != 0
    # A continuous control: enumerating a knob is a category error, and the
    # message has to say where the real list is.
    assert "not a switch or selector" in done.stderr, done.stderr
    assert "--list-enumerable" in done.stderr


def test_a_discrete_control_the_renderer_does_not_model_is_refused(audio, tmp_path):
    """A path can be valid for the pack and still be imaginary for the backend.

    Before this guard, eleven microphone values became eleven identical synthetic
    renders because Evaluator._settings dropped the unsupported selector later.
    The budget was split eleven ways and the run looked like enumeration worked.
    """
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--amp", "sw50r",
               "--budget", "400", "--out-dir", tmp_path / "run",
               "--enumerate", "cabParameters/leftMicType")
    assert done.returncode != 0
    assert "this renderer cannot drive it" in done.stderr, done.stderr
    assert "real-plugin renderer" in done.stderr


def test_enumerating_one_control_twice_is_not_four_topologies(audio, tmp_path):
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--amp", "sw50r",
               "--budget", "300", "--out-dir", tmp_path / "run",
               "--enumerate", "sw50rAmp/sw50rBright",
               "--enumerate", "sw50rAmp/sw50rBright")
    assert done.returncode != 0
    assert "more than once" in done.stderr, done.stderr
    assert "duplicates every topology" in done.stderr


def test_a_topology_product_that_cannot_be_searched_is_refused_with_the_sums(audio, tmp_path):
    """A topology with no search behind it is its starting point scored once.

    Refused before the renders rather than reported after them: `search()` says
    afterwards that each variant got a thin share, which is an hour too late.
    """
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--amp", "sw50r",
               "--budget", "300", "--out-dir", tmp_path / "run",
               "--enumerate", "sw50rAmp/sw50rBright",
               "--enumerate", "cabParameters/leftCabActive",
               "--enumerate", "compressor/compressorActive",
               "--enumerate", "drive1/drive1Active",
               "--enumerate", "delay/delayActive")
    assert done.returncode != 0
    assert "32 topologies do not fit" in done.stderr, done.stderr
    assert "Raise --budget to about" in done.stderr
    assert "Traceback" not in done.stderr


def test_enumerating_reaches_the_search_and_drops_the_caveat(audio, tmp_path):
    """The caveat that says nothing was enumerated must stop appearing once
    something is, or it is the one line a reader would trust and shouldn't."""
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--reference-mode", "probe",
               "--probe-di", audio / "probe.wav", "--amp", "sw50r",
               "--budget", "90", "--shortlist", "1", "--out-dir", tmp_path / "run",
               "--enumerate", "sw50rAmp/sw50rBright")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "no switches or selectors were enumerated" not in done.stdout, done.stdout


def test_the_benchmark_offers_the_flag_its_own_error_names(tmp_path):
    """`enumerated()` tells the reader to run --list-enumerable, and it is shared
    by both CLIs — so both have to have it, or the advice is a dead end on one."""
    listed = run("benchmark_match.py", "--list-enumerable")
    assert listed.returncode == 0, listed.stderr
    assert "sw50rAmp/sw50rBright" in listed.stdout
    assert "cabParameters/leftMicType" not in listed.stdout

    refused = run("benchmark_match.py", "--enumerate", "nope")
    assert refused.returncode != 0
    assert "--list-enumerable" in refused.stderr
