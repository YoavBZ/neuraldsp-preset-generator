"""The two M4 scripts, run as a person runs them.

These had no tests at all — 490 lines of the code a guitarist actually touches,
covered only by a mention inside a docstring. What is checked here is not the DSP
(that is `test_search.py`'s job) but the things only a real invocation exercises:
that the whole loop closes, that the output names its next step, and that an ordinary
mistake produces a sentence rather than a stack.

The budgets are small and the DI is short, so the whole file is a few seconds.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
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


def test_the_template_score_uses_the_mean_and_keeps_partial_evidence():
    from match.search import Candidate
    from scripts import match_preset as cli

    samples = iter([
        Candidate(values={"gain": 1}, objectives={"total": 0.9, "timbre": 0.8},
                  total=0.9),
        Candidate(values={"gain": 1}, error="silent render"),
        Candidate(values={"gain": 1}, objectives={"total": 0.7},
                  total=0.7),
    ])

    class Evaluator:
        def evaluate(self, values):
            return next(samples)

    start = cli._replicated_start(
        Evaluator(), {"gain": 1}, requested=3)

    assert start is not None
    assert start.observations == 2
    assert start.spread == pytest.approx(0.2)
    assert start.trial.total == pytest.approx(0.9)
    assert start.estimate.total == pytest.approx(0.8)
    assert start.estimate.objectives == pytest.approx(
        {"total": 0.8, "timbre": 0.8})
    assert start.objective_observations == {"total": 2, "timbre": 1}
    assert start.objective_spreads == {"total": pytest.approx(0.2),
                                       "timbre": None}


def test_the_template_score_refuses_when_every_observation_fails():
    from match.search import Candidate
    from scripts import match_preset as cli

    class Evaluator:
        def evaluate(self, values):
            return Candidate(values=dict(values), error="silent render")

    assert cli._replicated_start(Evaluator(), {"gain": 1}, requested=3) is None


def test_the_no_better_caveat_only_names_evidence_asymmetry_when_it_exists():
    from scripts import match_preset as cli

    equal = cli._no_better(0.8, 0.7, 300, 3, 3)
    thin = cli._no_better(0.8, 0.7, 300, 2, 3)

    assert "unequal evidence" not in equal
    assert "candidate averages 2 observations" in thin
    assert "template 3" in thin


@pytest.fixture(scope="module")
def audio(tmp_path_factory):
    """A reference rendered through the synthetic chain, and the DI behind it."""
    from analysis import refchain
    from tests import fixtures_audio as fx

    directory = tmp_path_factory.mktemp("audio")
    di = fx.plucks(seconds=2.0, gap=0.9, seed=5)
    fx.write_wav(str(directory / "probe.wav"), di)
    fx.write_wav(str(directory / "ref.wav"), refchain.render(di, {
        "sw50rAmp/sw50rVolume": 82.0, "sw50rAmp/sw50rTreble": 20.0}))
    spec = directory / "target.json"
    spec.write_text(json.dumps({
        "name": "paired target",
        "parameters": [
            {"module": "sw50rAmp", "key": "sw50rVolume", "value": 82.0},
            {"module": "sw50rAmp", "key": "sw50rTreble", "value": 20.0},
        ],
    }))
    target = directory / "target.xml"
    applied = run("apply_spec.py", "--template", TEMPLATE, "--spec", spec,
                  "--out", target)
    assert applied.returncode == 0, applied.stdout + applied.stderr
    rendered = run(
        "render_paired_reference.py", "--preset", target,
        "--probe-di", directory / "probe.wav",
        "--out", directory / "paired-ref.wav",
        "--pack", "morgan", "--amp", "sw50r", "--renderer", "synthetic",
    )
    assert rendered.returncode == 0, rendered.stdout + rendered.stderr
    return directory


# --- the whole loop ---------------------------------------------------------


def test_a_match_produces_a_spec_a_preset_and_a_report(audio, tmp_path):
    """And the spec applies. This is the claim the module docstring makes — that the
    winner is written by the same validated path as a hand-authored preset — and it is
    only true if `apply_spec.py` accepts what came out."""
    out = tmp_path / "run"
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "paired-ref.wav",
               "--reference-mode", "paired_di",
               "--probe-di", audio / "probe.wav", "--amp", "sw50r",
               "--paired-provenance", audio / "paired-ref.wav.paired.json",
               "--budget", "60", "--shortlist", "2", "--out-dir", out)
    assert done.returncode == 0, done.stdout + done.stderr

    assert (out / "trials.sqlite3").exists()
    assert (out / "report.html").exists()
    summary = json.loads((out / "summary.json").read_text())
    assert summary["schema"] == "tone-match-summary-v1"
    assert summary["reference"]["regime"] == "paired_di"
    assert summary["reference"]["pairing"]["schema"] == "paired-di-reference-1"
    assert pathlib.Path(summary["reference"]["pairing"]["path"]) == \
        (audio / "paired-ref.wav.paired.json").resolve()
    assert pathlib.Path(summary["reference"]["path"]).is_absolute()
    assert summary["reference"]["regime_confidence"] == 1.0
    assert summary["reference"]["excerpt"] == {
        "start_s": 0.0,
        "end_s": pytest.approx(2.0, abs=0.01),
        "duration_s": pytest.approx(2.0, abs=0.01),
        "source_duration_s": pytest.approx(2.0, abs=0.01),
        "requested_s": None,
        "policy": "full_source",
    }
    assert summary["renderer"]["renderer_id"] == "synthetic"
    assert summary["inversion"]["used"] is True
    assert summary["inversion"]["changes"]
    # A paired reamp measured whole, so the shortlist's output level was checked
    # against the reference: one record per shortlisted candidate, without its vector.
    trims = summary["search"]["level_trims"]
    assert len(trims) == 2
    assert all("values_before" not in record for record in trims)
    assert summary["inversion"]["detail"]["signal_path"] == "sw50r"
    assert not any(change["path"] == "/selectedAmp"
                   for change in summary["inversion"]["changes"]), (
        "explicit --amp must select SW50R before the inversion probe is rendered"
    )
    assert summary["search"]["searched"]
    assert summary["search"]["starting_settings"]["/selectedAmp"] == "SW50R"
    assert summary["search"]["sensitivity_floor_observations"] == 1
    command = summary["command_accounting"]
    assert command["total_renders"] == (
        command["budgeted_renders"] + command["outside_budget_renders"]
    )
    assert command["outside_budget_by_source"] == {
        "template": 1,
        "inversion_probe": 1,
        "report_candidates": 2,
        "guitar_check": 0,          # a DI was given, so no guitar check ran
    }
    assert summary["starting_point"]["observations"] == 1
    assert summary["starting_point"]["spread"] is None
    assert summary["starting_point"]["reference_level_score"] == pytest.approx(
        summary["starting_point"]["score"])
    assert summary["starting_point"]["settings"]["/selectedAmp"] == "SW50R"
    template_source = summary["starting_point"]["template"]
    assert pathlib.Path(template_source["path"]) == TEMPLATE.resolve()
    assert template_source["sha256"] == hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()
    assert all(candidate["trial_id"] is not None
               for candidate in summary["shortlist"])
    for candidate in summary["shortlist"]:
        # A deterministic backend measures each level once, and the reference-level
        # score a reader is shown is that one render. The fields still have to be
        # there and agree, because the report and the skill read them either way.
        assert candidate["input_level_observations"] == {
            "0.0": 1, "-6.0": 1, "6.0": 1
        }
        assert candidate["reference_level_score"] == pytest.approx(
            candidate["score"]
        )
        assert candidate["input_level_spread"] == {}
    assert all(candidate["fingerprint"] is not None
               for candidate in summary["shortlist"])
    assert summary["shortlist"][0]["fingerprint_delta"]
    assert summary["caveats"]
    spec = json.loads((out / "match-1.json").read_text())
    assert spec["parameters"], "a spec with no parameters is not a match"
    assert (out / "match-2.json").exists(), "--shortlist 2 means two of them"

    # The next command, printed rather than left in a docstring the user never sees.
    assert "apply_spec.py" in done.stdout
    assert "export_match_audition.py" in done.stdout
    assert "reference excerpt 0.000000–2.000000 s" in done.stdout


def test_a_stateful_run_replicates_the_template_and_accounts_for_it(
        audio, tmp_path, monkeypatch, capsys):
    from dataclasses import replace

    from match.renderer_synth import SyntheticRenderer
    from scripts import match_preset as cli

    class StatefulSynthetic(SyntheticRenderer):
        def metadata(self):
            return replace(super().metadata(), reproducible=False,
                           band_noise_db=0.23)

    renderer = StatefulSynthetic()
    monkeypatch.setattr(cli, "_renderer", lambda name, pack, **_: renderer)
    out = tmp_path / "stateful"
    monkeypatch.setattr(sys, "argv", [
        "match_preset.py",
        "--template", str(TEMPLATE),
        "--reference", str(audio / "ref.wav"),
        "--reference-mode", "probe",
        "--probe-di", str(audio / "probe.wav"),
        "--amp", "sw50r",
        "--no-invert",
        "--budget", "90",
        "--shortlist", "1",
        "--renderer", "synthetic",
        "--out-dir", str(out),
    ])

    cli.main()

    summary = json.loads((out / "summary.json").read_text())
    starting = summary["starting_point"]
    assert summary["command_accounting"]["outside_budget_by_source"]["template"] == 3
    assert starting["observations"] == 3
    assert starting["spread"] == pytest.approx(0.0)
    assert starting["score"] == pytest.approx(starting["reference_level_score"])
    assert set(starting["objective_observations"].values()) == {3}
    assert summary["shortlist"][0]["input_level_observations"]["0.0"] == 3
    output = capsys.readouterr().out
    assert "candidate mean of 3 renders; starting score mean of 3" in output

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
               "--reference", audio / "paired-ref.wav",
               "--reference-mode", "paired_di",
               "--probe-di", audio / "probe.wav", "--loss-profile", "paired-v1",
               "--paired-provenance", audio / "paired-ref.wav.paired.json",
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


def test_paired_provenance_refuses_a_changed_pair(audio, tmp_path):
    provenance = json.loads((audio / "paired-ref.wav.paired.json").read_text())
    provenance["probe_di"]["sha256"] = "0" * 64
    changed = tmp_path / "changed-pair.json"
    changed.write_text(json.dumps(provenance))
    done = run(
        "match_preset.py", "--template", TEMPLATE,
        "--reference", audio / "paired-ref.wav", "--reference-mode", "paired_di",
        "--probe-di", audio / "probe.wav", "--paired-provenance", changed,
        "--amp", "sw50r", "--budget", "60", "--out-dir", tmp_path / "run",
    )
    assert done.returncode != 0
    assert "--probe-di no longer matches its paired provenance" in done.stderr
    assert not (tmp_path / "run" / "trials.sqlite3").exists()


@pytest.mark.parametrize("section,bad", [("reference", []), ("probe_di", "wrong"),
                                        ("renderer", []), ("preset", {})])
def test_malformed_pairing_is_a_cli_error(audio, tmp_path, section, bad):
    document = json.loads((audio / "paired-ref.wav.paired.json").read_text())
    document[section] = bad
    sidecar = tmp_path / "bad.json"
    sidecar.write_text(json.dumps(document))
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "paired-ref.wav", "--reference-mode", "paired_di",
               "--probe-di", audio / "probe.wav", "--paired-provenance", sidecar,
               "--renderer", "synthetic", "--out-dir", tmp_path / "run")
    assert done.returncode == 2
    assert "paired provenance" in done.stderr
    assert "Traceback" not in done.stderr
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize("field,value", [("sample_rate", 44100), ("block_size", 1024),
                                       ("quality_mode", "different")])
def test_pairing_checks_render_affecting_metadata(audio, tmp_path, field, value):
    document = json.loads((audio / "paired-ref.wav.paired.json").read_text())
    document["renderer"][field] = value
    sidecar = tmp_path / "different-renderer.json"
    sidecar.write_text(json.dumps(document))
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "paired-ref.wav", "--reference-mode", "paired_di",
               "--probe-di", audio / "probe.wav", "--paired-provenance", sidecar,
               "--renderer", "synthetic", "--out-dir", tmp_path / "run")
    assert done.returncode == 2
    assert "differs from --paired-provenance" in done.stderr
    assert not (tmp_path / "run").exists()


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
    (["--renderer", "pedalboard"], "invalid choice"),
    (["--reference-mode", "reamp"], "invalid choice"),
])
def test_a_bad_flag_is_a_sentence_not_a_stack(audio, tmp_path, extra, expected):
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--probe-di", audio / "probe.wav",
               "--amp", "sw50r", "--out-dir", tmp_path / "run", *extra)
    assert done.returncode != 0
    assert expected in done.stderr, done.stderr
    assert "Traceback" not in done.stderr


def test_an_unknown_renderer_name_is_refused_in_a_sentence():
    """Every CLI limits --renderer to its choices; a direct caller still gets a sentence."""
    from scripts import match_preset as cli

    with pytest.raises(SystemExit):
        cli._renderer("bogus")


@pytest.mark.parametrize("regime", ["mix", "separated_stem", "isolated_stem"])
def test_without_a_di_a_recording_is_not_searched_and_the_template_kept(
        audio, tmp_path, regime):
    """Measured on 43 recordings per amp, no search without a DI beat the starting
    preset as it is, so the tool refuses rather than write a worse preset."""
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--reference-mode", regime,
               "--amp", "sw50r", "--renderer", "synthetic", "--budget", "60",
               "--out-dir", tmp_path / "run")
    assert done.returncode != 0 and "Traceback" not in done.stderr
    assert "use it as it is" in done.stderr and "--search-without-di" in done.stderr
    assert not (tmp_path / "run").exists()        # no store, no spec, nothing written
    # The flag is for a run with no DI; with one it is a contradiction.
    done = run("match_preset.py", "--search-without-di", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--probe-di", audio / "probe.wav",
               "--amp", "sw50r", "--renderer", "synthetic", "--out-dir", tmp_path / "both")
    assert done.returncode != 0 and "drop one of them" in done.stderr


def test_a_probe_reference_without_a_di_is_still_searched(audio, tmp_path):
    """A `probe` reference is a render through the noise probe itself: still searched.

    Its own test rather than a third step of the one above, which it used to be: it
    does not depend on that test's `regime`, and it is the only one of the three
    steps that runs a search, so it was the same search paid for three times."""
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--reference-mode", "probe",
               "--amp", "sw50r", "--renderer", "synthetic", "--budget", "60",
               "--out-dir", tmp_path / "probe")
    assert done.returncode == 0, done.stdout + done.stderr


def test_a_reference_that_is_not_audio_says_so(tmp_path):
    """`soundfile` raises a `RuntimeError`, which is the one remaining way an ordinary
    mistake reached a person as fifteen frames of traceback."""
    done = run("match_preset.py", "--search-without-di", "--template", TEMPLATE,
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


def test_the_pack_comes_from_the_template_when_not_named(tmp_path):
    """show.py and apply_spec.py detect the pack from the header; so does this.

    It defaulted to Morgan, so a Tone King template without `--pack toneking`
    was refused as the wrong plugin. The synthetic chain models no Tone King
    control, so the run stops there — naming the pack it detected.
    """
    import struct

    from scripts.match_preset import _pack_of

    body = b"ampType"
    template = tmp_path / "ToneKing.xml"
    template.write_bytes(
        b"neural_dsp_toneking\x00PARAM\x00\x01\x02id\x00"
        + bytes([0x01, len(body) + 2, 0x05]) + body + b"\x00"
        + b"value\x00\x01\x09\x04" + struct.pack("<d", 1.0) + b"\x00"
    )
    assert _pack_of(template) == "toneking"
    assert _pack_of(pathlib.Path(TEMPLATE)) == "morgan"

    done = run("match_preset.py", "--search-without-di", "--template", template,
               "--reference", tmp_path / "unused.wav", "--out-dir", tmp_path / "run")
    assert done.returncode != 0
    assert "pack toneking" in done.stderr, done.stderr
    assert "not a preset for pack" not in done.stderr, done.stderr


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
    assert written["schema"] == "benchmark-match-3"
    assert len(written["source_commit"]) == 40
    assert written["elapsed_s"] > 0
    assert written["target_sampler"] == "seed-sequence-spawn-1"
    assert written["probe"] == {
        "kind": "synthetic-decaying-noise-bursts",
        "seconds": 1.5,
        "gap_s": 0.9,
        "seed": 13,
    }
    assert written["workers"] == written["workers_requested"] == 1
    assert written["budget"] == written["budget_requested"] == 30
    assert written["budget_per_topology"] is False
    assert written["topology_variants"] == 1
    assert written["enumerated"] == []
    assert written["targets_completed"] == 2
    assert set(written["summaries"]) == {"recipe", "inversion", "full"}
    assert len(written["outcomes"]) == 6, "two targets by three arms"
    assert isinstance(written["ships"], bool)


def test_the_benchmarks_exit_code_is_the_verdict(tmp_path):
    """So it can gate something. Zero when it ships, non-zero when it does not."""
    done = run("benchmark_match.py", "--targets", "1", "--budget", "30",
               "--seconds", "1.5", "--arms", "full")
    assert done.returncode == 1, "with no baseline there is nothing to beat"
    assert "was not run" in done.stdout


def _synthetic_atlas(tmp_path, seconds: float) -> pathlib.Path:
    """A small SW50R atlas on the synthetic chain, built on the benchmark's own
    synthetic probe at this length."""
    from match import atlas, space as space_module
    from match.renderer_synth import SyntheticRenderer
    from scripts._cli import probe_di

    space = space_module.build("morgan", amp="sw50r")
    di, _ = probe_di(None, seconds)
    document = atlas.build(SyntheticRenderer(), space, di, "morgan", "sw50r",
                           samples=8, seed=17)
    path = tmp_path / "atlas.json"
    path.write_text(json.dumps(document))
    return path


def test_an_atlas_benchmark_reports_whether_the_atlas_start_helped(tmp_path):
    atlas_path = _synthetic_atlas(tmp_path, 1.5)
    out = tmp_path / "bench.json"
    done = run("benchmark_match.py", "--atlas", atlas_path, "--targets", "2",
               "--budget", "30", "--seconds", "1.5", "--json", out)
    assert done.returncode in (0, 1), done.stdout + done.stderr
    assert ("ATLAS START HELPS" in done.stdout
            or "ATLAS START DOES NOT HELP" in done.stdout)
    assert "different probe" not in done.stdout

    assert "not M4's" in done.stdout, "M4's gate is labelled as not M4's verdict"

    written = json.loads(out.read_text())
    assert written["ships"] is None, "an atlas run records no M4 verdict"
    assert set(written["summaries"]) == {
        "recipe", "inversion", "full", "atlas", "atlas-inversion", "atlas-full"}
    assert len(written["outcomes"]) == 12, "two targets by six arms"
    assert {row["position"] for row in written["outcomes"]} == set(range(6))
    assert written["atlas"]["probe_matches"] is True
    assert written["atlas"]["amp"] == "sw50r"
    assert isinstance(written["atlas_helps"], bool)
    assert done.returncode == (0 if written["atlas_helps"] else 1), (
        "with --atlas the exit status is whether the atlas start helped")


def test_an_atlas_on_another_probe_is_run_and_says_so(tmp_path):
    atlas_path = _synthetic_atlas(tmp_path, 1.5)
    out = tmp_path / "bench.json"
    done = run("benchmark_match.py", "--atlas", atlas_path, "--targets", "1",
               "--budget", "30", "--seconds", "2", "--arms", "full,atlas-full",
               "--json", out)
    assert done.returncode in (0, 1), done.stdout + done.stderr
    assert "different probe than the atlas" in done.stdout
    assert json.loads(out.read_text())["atlas"]["probe_matches"] is False


@pytest.mark.parametrize("extra, message", [
    (("--enumerate", "cabParameters/leftCabActive"), "do not apply with --atlas"),
    (("--amp", "pr12"), "contradicts the atlas"),
    (("--pack", "toneking"), "contradicts the atlas"),
    (("--arms", "full"), "needs both the full and atlas-full arms"),
    (("--list-enumerable",), "do not apply with --atlas"),
    (("--budget-per-topology",), "does not apply with --atlas"),
])
def test_an_atlas_benchmark_refuses_what_it_cannot_answer(tmp_path, extra, message):
    done = run("benchmark_match.py", "--atlas", _synthetic_atlas(tmp_path, 1.5),
               "--targets", "1", *extra)
    assert done.returncode != 0
    assert message in done.stderr


def test_an_atlas_from_another_backend_is_refused(tmp_path):
    """An atlas of the plugin's renders looked up against the synthetic chain's
    describes another backend, so the run is refused rather than caveated."""
    atlas_path = _synthetic_atlas(tmp_path, 1.5)
    document = json.loads(atlas_path.read_text())
    document["renderer"]["renderer_id"] = "swift"
    atlas_path.write_text(json.dumps(document))
    done = run("benchmark_match.py", "--atlas", atlas_path, "--targets", "1")
    assert done.returncode != 0
    assert "built by the swift renderer" in done.stderr


def test_an_atlas_from_another_build_is_a_caveat_not_a_refusal(tmp_path):
    """Both searches render on this build, so the comparison stays fair; only the
    lookup reads responses measured on another one."""
    atlas_path = _synthetic_atlas(tmp_path, 1.5)
    document = json.loads(atlas_path.read_text())
    document["renderer"]["renderer_build"] = "an-older-build"
    atlas_path.write_text(json.dumps(document))
    done = run("benchmark_match.py", "--atlas", atlas_path, "--targets", "1",
               "--budget", "30", "--seconds", "1.5", "--arms", "full,atlas-full")
    assert done.returncode in (0, 1), done.stdout + done.stderr
    assert "differs in renderer_build" in done.stdout


def test_the_atlas_arms_need_an_atlas(tmp_path):
    done = run("benchmark_match.py", "--targets", "1", "--arms", "full,atlas-full")
    assert done.returncode != 0
    assert "need --atlas" in done.stderr


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
    done = run("match_preset.py", "--search-without-di", "--template", TEMPLATE,
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
    done = run("match_preset.py", "--search-without-di", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--amp", "sw50r",
               "--budget", "400", "--out-dir", tmp_path / "run",
               "--enumerate", "cabParameters/leftMicType")
    assert done.returncode != 0
    assert "this renderer cannot drive it" in done.stderr, done.stderr
    assert "real-plugin renderer" in done.stderr


def test_enumerating_one_control_twice_is_not_four_topologies(audio, tmp_path):
    done = run("match_preset.py", "--search-without-di", "--template", TEMPLATE,
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
    done = run("match_preset.py", "--search-without-di", "--template", TEMPLATE,
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


def test_a_per_topology_budget_scales_the_total_explicitly(audio, tmp_path):
    common = (
        "--template", TEMPLATE,
        "--reference", audio / "ref.wav",
        "--reference-mode", "probe",
        "--probe-di", audio / "probe.wav",
        "--amp", "sw50r",
        "--budget", "45",
        "--shortlist", "1",
        "--enumerate", "sw50rAmp/sw50rBright",
    )
    refused = run("match_preset.py", *common, "--out-dir", tmp_path / "refused")
    assert refused.returncode != 0
    assert "2 topologies do not fit" in refused.stderr

    out = tmp_path / "scaled"
    scaled = run("match_preset.py", *common, "--budget-per-topology",
                 "--out-dir", out)
    assert scaled.returncode == 0, scaled.stdout + scaled.stderr
    summary = json.loads((out / "summary.json").read_text())
    assert summary["search"]["budget"] == 90
    assert "--budget 45 was multiplied by 2 enumerated topologies" in \
        scaled.stdout

    too_small = run(
        "match_preset.py",
        "--template", TEMPLATE,
        "--reference", audio / "ref.wav",
        "--reference-mode", "probe",
        "--probe-di", audio / "probe.wav",
        "--amp", "sw50r",
        "--budget", "20",
        "--budget-per-topology",
        "--shortlist", "1",
        "--enumerate", "sw50rAmp/sw50rBright",
        "--out-dir", tmp_path / "scaled-refused",
    )
    assert too_small.returncode != 0
    assert "40-render total (20 requested × 2)" in too_small.stderr
    recommendation = re.search(
        r"Raise --budget to about (\d+) with --budget-per-topology "
        r"\((\d+) effective renders\)", too_small.stderr)
    assert recommendation, too_small.stderr
    requested, effective = map(int, recommendation.groups())
    assert requested == (effective + 1) // 2
    assert f"Raise --budget to about {effective} with --budget-per-topology" \
        not in too_small.stderr


def test_the_benchmark_records_a_per_topology_budget(tmp_path):
    out = tmp_path / "bench-topology.json"
    done = run(
        "benchmark_match.py", "--targets", "1", "--budget", "45",
        "--budget-per-topology", "--seconds", "1.5", "--arms", "full",
        "--enumerate", "sw50rAmp/sw50rBright", "--json", out)
    assert done.returncode in (0, 1), done.stdout + done.stderr

    written = json.loads(out.read_text())
    assert written["budget"] == 90
    assert written["budget_requested"] == 45
    assert written["budget_per_topology"] is True
    assert written["topology_variants"] == 2
    assert written["enumerated"] == ["sw50rAmp/sw50rBright"]
    assert "45 requested/topology × 2" in done.stdout


def test_the_topology_simulation_is_reproducible_and_structured(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    args = ("--trials", "20", "--seed", "7")
    one = run("simulate_topology_replication.py", *args, "--out", first)
    two = run("simulate_topology_replication.py", *args, "--out", second)
    assert one.returncode == two.returncode == 0, one.stderr + two.stderr
    assert first.read_bytes() == second.read_bytes()

    result = json.loads(first.read_text())
    assert result["schema"] == "topology-replication-simulation-1"
    assert result["seed"] == 7
    assert result["trials_per_configuration"] == 20
    assert len(result["rows"]) == 9
    assert {(row["topologies"], row["noise_sigma"])
            for row in result["rows"]} == {
                (variants, sigma)
                for variants in (2, 4, 8)
                for sigma in (0.05, 0.15, 0.30)
            }


def test_the_topology_pilot_manifest_pins_every_artifact():
    manifest = json.loads(
        (ROOT / "docs" / "topology-budget-pilot-manifest.json").read_text())
    assert manifest["source_commit"].startswith("7966f53")
    assert len(manifest["artifacts"]) == 3
    for entry in manifest["artifacts"]:
        artifact = ROOT / entry["path"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == entry["sha256"]
        assert json.loads(artifact.read_text())["source_commit"].startswith("7966f53")
        assert "scripts/benchmark_match.py" in entry["command"]
    simulation = manifest["simulation"]
    assert hashlib.sha256((ROOT / simulation["artifact"]).read_bytes()).hexdigest() \
        == simulation["sha256"]
    assert simulation["script"] == "scripts/simulate_topology_replication.py"


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


def test_a_process_policy_without_the_plugin_is_refused(audio, tmp_path):
    """On AC20 a reused instance's output depends on what it rendered before, and
    `--process-policy fresh` is how a match avoids that. The synthetic chain has no
    instance, so accepting the flag there would record a policy the run never had."""
    result = run("match_preset.py", "--template", TEMPLATE,
                 "--reference", audio / "paired-ref.wav",
                 "--reference-mode", "probe", "--probe-di", audio / "probe.wav",
                 "--renderer", "synthetic", "--process-policy", "fresh",
                 "--out-dir", tmp_path / "run")
    assert result.returncode != 0
    assert "plugin renderer only" in result.stderr
    assert "Traceback" not in result.stderr


def test_a_match_scores_with_the_profile_that_drops_rt60_and_harmonic_by_default():
    """New matches use unpaired-v3; -v2 and -v1 stay selectable to reproduce
    earlier runs."""
    from scripts.match_preset import build_parser

    assert build_parser().get_default("loss_profile") == "unpaired-v3"



@pytest.mark.parametrize("with_di", [False, True])
def test_only_a_paired_reamp_has_its_output_level_trimmed(audio, tmp_path, with_di):
    """Measured on Tone King: through another passage's DI or the noise probe a
    loudness matched through the probe does not carry over, so an unpaired match
    runs no trim — with a DI or without — and the summary says so by being empty."""
    out = tmp_path / "run"
    di = ["--probe-di", audio / "probe.wav"] if with_di else ["--search-without-di"]
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "ref.wav", "--reference-mode", "isolated_stem",
               *di, "--amp", "sw50r", "--budget", "40", "--shortlist", "1",
               "--out-dir", out)
    assert done.returncode == 0, done.stdout + done.stderr
    assert json.loads((out / "summary.json").read_text())["search"]["level_trims"] == []



def test_a_paired_run_on_an_excerpt_is_not_trimmed(audio, tmp_path):
    """An excerpt's loudness is not the whole DI's, which every candidate renders."""
    out = tmp_path / "run"
    done = run("match_preset.py", "--template", TEMPLATE,
               "--reference", audio / "paired-ref.wav",
               "--reference-mode", "paired_di",
               "--probe-di", audio / "probe.wav", "--amp", "sw50r",
               "--paired-provenance", audio / "paired-ref.wav.paired.json",
               "--loss-profile", "unpaired-v2", "--excerpt", "1",
               "--budget", "40", "--shortlist", "1", "--out-dir", out)
    assert done.returncode == 0, done.stdout + done.stderr
    assert json.loads((out / "summary.json").read_text())["search"]["level_trims"] == []


def test_the_printed_apply_command_survives_a_path_with_spaces(audio, tmp_path):
    """The plugin's User presets live under "Neural DSP/Morgan Amps Suite", so the
    template path a user passes usually has spaces; the printed command must run
    as pasted."""
    import shlex
    import shutil

    spaced = tmp_path / "My Presets" / "Autumn Leaves - Clapton.xml"
    spaced.parent.mkdir()
    shutil.copy(TEMPLATE, spaced)
    out = tmp_path / "run dir"
    done = run("match_preset.py", "--search-without-di", "--template", spaced,
               "--reference", audio / "ref.wav", "--reference-mode", "isolated_stem",
               "--amp", "sw50r", "--budget", "40", "--shortlist", "1",
               "--out-dir", out)
    assert done.returncode == 0, done.stdout + done.stderr
    lines = done.stdout.split("to hear it:")[1].strip().splitlines()[:3]
    command = shlex.split(" ".join(line.rstrip("\\").strip() for line in lines))
    assert command[command.index("--template") + 1] == str(spaced)
    assert command[command.index("--out") + 1] == str(out / "match-1.xml")


# --- the guitar check, without a DI ------------------------------------------


class _GainRenderer:
    """Renders the input scaled by the settings' `gain`: None is an all-zero
    render, "error" raises the way a plugin failure does."""

    def render(self, signal, settings):
        import types

        from match.renderer import RenderError

        gain = settings["gain"]
        if gain == "error":
            raise RenderError("the plugin did not answer")
        audio = signal * 0.0 if gain is None else signal * gain
        return types.SimpleNamespace(audio=audio, silent=gain is None,
                                     metadata=types.SimpleNamespace(sample_rate=48000))


class _Settings:
    def _settings(self, values):
        return values


def _check(template_gain, *gains):
    from match.search import Candidate
    from scripts import match_preset as cli

    shortlist = [Candidate(values={"gain": gain}) for gain in gains]
    return cli, shortlist, cli._guitar_check(_GainRenderer(), _Settings(),
                                             {"gain": template_gain}, shortlist)


def test_the_guitar_check_fails_unmeasurable_and_far_quieter_candidates():
    # 1e-5 is not silence but is under loudness's gate: the real failures were that.
    cli, shortlist, check = _check(1.0, 0.05, 0.5, None, 2.0, 1e-5)

    rows = {row["search_rank"]: row for row in check["candidates"]}
    assert rows[1]["vs_template_db"] == pytest.approx(-26.0, abs=0.1)
    assert [rows[r]["passes"] for r in (1, 2, 3, 4, 5)] == [False, True, False, True, False]
    assert rows[3]["lufs"] is None and rows[5]["lufs"] is None and check["renders"] == 6
    # Each row says which match-N file it ends up in.
    assert [rows[r]["match"] for r in (1, 2, 3, 4, 5)] == [3, 1, 4, 2, 5]

    reordered = cli._passing_first(shortlist, check)
    assert [c.values["gain"] for c in reordered] == [0.5, 2.0, 0.05, None, 1e-5]
    caveat, = cli._guitar_check_caveats(check)
    assert caveat.startswith("3 of 5 shortlisted candidates failed")
    assert "match-3 (the search's choice 1) was 26 dB under" in caveat
    assert "match-4 (the search's choice 3) had no measurable loudness" in caveat


def test_the_guitar_check_line_is_twenty_decibels():
    _, _, check = _check(1.0, 10 ** (-20.05 / 20), 10 ** (-19.95 / 20))
    assert [row["passes"] for row in check["candidates"]] == [False, True]


def test_the_guitar_check_says_when_nothing_passed_or_nothing_could_be_judged():
    cli, quiet, check = _check(1.0, 0.01)
    assert "every shortlisted candidate failed" in cli._guitar_check_caveats(check)[0]

    cli, quiet, unjudged = _check(None, 0.01)
    assert unjudged["candidates"][0]["passes"] is None
    assert cli._passing_first(quiet, unjudged) == quiet
    assert "could not run" in cli._guitar_check_caveats(unjudged)[0]


def test_a_render_error_in_the_guitar_check_judges_nothing_and_loses_nothing():
    cli, shortlist, check = _check(1.0, "error", 0.5)
    first = check["candidates"][0]
    assert first["passes"] is None and "did not answer" in first["error"]
    assert cli._passing_first(shortlist, check) == shortlist
    assert "could not render match-1" in cli._guitar_check_caveats(check)[0]

    # One failed and the only other errored: that is still "every judged one failed".
    cli, shortlist, check = _check(1.0, 0.01, "error")
    assert "every shortlisted candidate failed" in cli._guitar_check_caveats(check)[0]

    cli, shortlist, check = _check("error", 0.5)
    assert check["candidates"][0]["passes"] is None and "template_error" in check
    assert "the preset you started from" in cli._guitar_check_caveats(check)[0]


def _no_di_run(audio, out, monkeypatch=None, fail_rank=None):
    """In process, so the check can be made to fail a chosen candidate."""
    from scripts import match_preset as cli

    if fail_rank is not None:
        real = cli._guitar_check

        def failing(*args, **kwargs):
            check = real(*args, **kwargs)
            for row in check["candidates"]:
                row["passes"] = row["search_rank"] != fail_rank
            order = cli._passing_first(list(range(1, len(check["candidates"]) + 1)),
                                       check)
            for row in check["candidates"]:
                row["match"] = order.index(row["search_rank"]) + 1
            return check

        monkeypatch.setattr(cli, "_guitar_check", failing)
    monkeypatch.setattr(sys, "argv", [
        "match_preset.py", "--search-without-di", "--template", str(TEMPLATE),
        "--reference", str(audio / "ref.wav"), "--reference-mode", "isolated_stem",
        "--amp", "sw50r", "--renderer", "synthetic", "--budget", "80",
        "--shortlist", "2", "--seed", "0", "--out-dir", str(out)])
    cli.main()
    return json.loads((out / "summary.json").read_text())


def test_a_failed_first_choice_is_written_as_the_last_match(audio, tmp_path, monkeypatch):
    before = _no_di_run(audio, tmp_path / "plain", monkeypatch)
    assert all(row["passes"] for row in before["search"]["guitar_check"]["candidates"])
    after = _no_di_run(audio, tmp_path / "failed", monkeypatch, fail_rank=1)

    plain, failed = tmp_path / "plain", tmp_path / "failed"

    def settings(path):
        return json.loads(path.read_text())["parameters"]

    def but_level(path):     # a failed candidate keeps its output gain untrimmed
        return [p for p in settings(path) if p["key"] != "outputGain"]

    assert settings(failed / "match-1.json") == settings(plain / "match-2.json")
    assert but_level(failed / "match-2.json") == but_level(plain / "match-1.json")
    assert after["caveats"][0].startswith("1 of 2 shortlisted candidates failed")
    command = after["command_accounting"]
    assert command["total_renders"] == (command["budgeted_renders"]
                                        + command["outside_budget_renders"])
    applied = sum(r["applied"] for r in after["search"]["guitar_check"]["level_trim"]["records"])
    # The template, both candidates, and a check and a score per trimmed candidate.
    assert command["outside_budget_by_source"]["guitar_check"] == 3 + 2 * applied


def test_only_a_match_without_a_di_runs_the_guitar_check(audio, tmp_path):
    for label, extra in (("no-di", ["--search-without-di"]),
                         ("di", ["--probe-di", audio / "probe.wav"])):
        out = tmp_path / label
        done = run("match_preset.py", "--template", TEMPLATE,
                   "--reference", audio / "ref.wav", "--reference-mode", "isolated_stem",
                   *extra, "--amp", "sw50r", "--renderer", "synthetic",
                   "--budget", "80", "--shortlist", "2", "--seed", "0",
                   "--out-dir", out)
        assert done.returncode == 0, done.stdout + done.stderr
        summary = json.loads((out / "summary.json").read_text())
        check = summary["search"]["guitar_check"]
        sources = summary["command_accounting"]["outside_budget_by_source"]
        if label == "di":
            assert check is None and sources["guitar_check"] == 0
        else:
            assert check["signal"]["lufs"] == -24.0
            assert len(check["candidates"]) == len(summary["shortlist"])
            applied = sum(r["applied"] for r in check["level_trim"]["records"])
            assert sources["guitar_check"] == 1 + len(summary["shortlist"]) + 2 * applied
            assert "for the guitar check" in done.stdout
            trim = check["level_trim"]
            assert trim["control"] == "parameters/outputGain"
            assert trim["target_lufs"] == pytest.approx(summary["reference"]["fingerprint"]
                                                        ["source"]["lufs_i"], abs=0.01)
            assert len(trim["records"]) == len(summary["shortlist"])
            applied = [r for r in trim["records"] if r["applied"]]
            assert applied, "the synthetic run should trim at least one candidate"
            first = next(r for r in trim["records"] if r["match"] == 1)
            spec = json.loads((out / "match-1.json").read_text())
            gain = next(p["value"] for p in spec["parameters"] if p["key"] == "outputGain")
            if first["applied"]:
                assert gain == pytest.approx(first["after"])
            # The written spec, the summary and the trial store describe one preset.
            from match.verdict import validate_candidate
            assert validate_candidate(out, 1).trial is not None


class _OutputGainRenderer:
    """The signal through a fixed -6 dB amp, then the output gain in dB; `power`
    below 1 compresses after the gain, `mute_above` goes silent past a gain."""

    def __init__(self, power=1.0, mute_above=None):
        self.power, self.mute_above = power, mute_above

    def render(self, signal, settings):
        import types

        import numpy as np

        gain_db = settings[("parameters", "outputGain")]
        silent = self.mute_above is not None and gain_db > self.mute_above
        audio = (np.zeros_like(signal) if silent
                 else signal * 10 ** (self.power * (gain_db - 6.0) / 20))
        return types.SimpleNamespace(audio=audio, silent=silent,
                                     metadata=types.SimpleNamespace(sample_rate=48000))


class _ScoringEvaluator(_Settings):
    """Scores a vector as a new trial, the way `search.Evaluator` does."""

    def __init__(self):
        self.renders = 0

    def evaluate(self, values):
        from match.search import Candidate

        self.renders += 1
        return Candidate(values=dict(values), objectives={"total": 0.5, "level": 1.0},
                         total=0.5, trial_id=100 + self.renders)


def _trim(renderer, *gains, target=-24.0, template=0.0):
    from match import space as space_module
    from match.search import Candidate
    from scripts import match_preset as cli

    gain = ("parameters", "outputGain")
    shortlist = [Candidate(values={gain: g}, total=0.4, trial_id=i)
                 for i, g in enumerate(gains, start=1)]
    evaluator = _ScoringEvaluator()
    check = cli._guitar_check(renderer, evaluator, {gain: template}, shortlist)
    shortlist = cli._passing_first(shortlist, check)
    trimmed = cli._guitar_level_trim(renderer, evaluator,
                                     space_module.build("morgan", amp="sw50r"),
                                     shortlist, check, target, "parameters/outputGain")
    return cli, gain, check, trimmed, evaluator


def test_the_guitar_level_trim_lands_on_the_reference_and_scores_the_trimmed_preset():
    # Through the -6 dB amp the -24 LUFS guitar plays at -30 LUFS with 0 dB of
    # output gain, so the reference's -24 needs +6 dB.
    cli, gain, check, trimmed, evaluator = _trim(_OutputGainRenderer(), 0.0, -30.0, 18.0)

    records = {r["match"]: r for r in check["level_trim"]["records"]}
    assert trimmed[0].values[gain] == pytest.approx(6.0) and trimmed[1].values[gain] == pytest.approx(6.0)
    assert records[1]["applied"] and records[1]["residual_db"] == pytest.approx(0.0, abs=0.05)
    # Each trimmed preset is its own scored trial, so a verdict can bind to it.
    assert trimmed[0].trial_id == records[1]["trial_after"] != records[1]["trial_before"]
    # -30 dB of output gain is 30 dB under the template: it failed, kept its gain.
    assert trimmed[2].values[gain] == -30.0 and not records[3]["applied"]
    assert records[3]["reason"] == "it failed the guitar check"
    # The check's four and one per trim; the caller adds the scorer's two.
    assert check["renders"] == 4 + 2 and evaluator.renders == 2
    trimmed_caveat, kept_caveat = cli._guitar_level_caveat(check)
    assert "match-1, match-2" in trimmed_caveat and "not linear" not in trimmed_caveat
    assert "match-3 (it failed the guitar check)" in kept_caveat


def test_a_trim_past_the_controls_range_is_clamped_and_said_so():
    cli, gain, check, trimmed, _ = _trim(_OutputGainRenderer(), 0.0, target=10.0)
    record = check["level_trim"]["records"][0]
    assert record["clamped"] and trimmed[0].values[gain] == pytest.approx(24.0)
    assert "ran out of range" in cli._guitar_level_caveat(check)[0]


def test_a_trim_that_does_not_land_is_reported():
    # Compression after the gain: +12 dB of output gain moves the output 6 dB.
    cli, gain, check, trimmed, _ = _trim(_OutputGainRenderer(power=0.5), 0.0,
                                         target=-21.0)
    record = check["level_trim"]["records"][0]
    assert record["applied"] and abs(record["residual_db"]) > 1.0
    assert "not linear" in cli._guitar_level_caveat(check)[0]


def test_a_trim_that_goes_silent_keeps_the_candidate_but_fails_the_check():
    cli, gain, check, trimmed, evaluator = _trim(_OutputGainRenderer(mute_above=3.0), 0.0)
    record = check["level_trim"]["records"][0]
    assert not record["applied"] and "no measurable loudness" in record["reason"]
    assert trimmed[0].values[gain] == 0.0 and trimmed[0].trial_id == 1
    assert evaluator.renders == 0
    row = check["candidates"][0]
    assert row["passes"] is False and row["failed_by"] == "level_trim"
    caveat = cli._guitar_check_caveats(check)[0]
    assert caveat.startswith("every shortlisted candidate failed the guitar check")
    assert "lost all measurable loudness when its output gain moved +6.0 dB" in caveat


class _CliffRenderer(_OutputGainRenderer):
    """A candidate with its input gain far down plays only while its output gain
    stays at 7 dB or more: a gain stage at a cliff, so trimming it down silences it."""

    def render(self, signal, settings):
        import types

        import numpy as np

        gain_db = settings[("parameters", "outputGain")]
        input_db = settings.get(("parameters", "inputGain"), 0.0)
        silent = input_db < -10 and gain_db < 7.0
        audio = (np.zeros_like(signal) if silent
                 else signal * 10 ** ((gain_db - 6.0 + input_db) / 20))
        return types.SimpleNamespace(audio=audio, silent=silent,
                                     metadata=types.SimpleNamespace(sample_rate=48000))


def test_a_candidate_that_goes_silent_when_trimmed_moves_behind_those_that_pass():
    from match import space as space_module
    from match.search import Candidate
    from scripts import match_preset as cli

    gain, inp = ("parameters", "outputGain"), ("parameters", "inputGain")
    shortlist = [Candidate(values={gain: 7.75, inp: -14.0}, total=0.3, trial_id=1),
                 Candidate(values={gain: 0.0, inp: 0.0}, total=0.4, trial_id=2)]
    renderer, evaluator = _CliffRenderer(), _ScoringEvaluator()
    check = cli._guitar_check(renderer, evaluator, {gain: 0.0, inp: 0.0}, shortlist)
    # As searched, both pass: the first plays 6 dB under the template.
    assert [row["passes"] for row in check["candidates"]] == [True, True]
    shortlist = cli._passing_first(shortlist, check)
    trimmed = cli._guitar_level_trim(renderer, evaluator,
                                     space_module.build("morgan", amp="sw50r"),
                                     shortlist, check, -40.0, "parameters/outputGain")

    assert [c.trial_id for c in trimmed] == [evaluator.renders + 100, 1]
    assert trimmed[0].values[gain] == pytest.approx(-10.0)
    assert trimmed[1].values == {gain: 7.75, inp: -14.0}
    first, second = check["candidates"]
    assert (first["passes"], first["failed_by"], first["match"]) == (False, "level_trim", 2)
    assert (second["passes"], second["match"]) == (True, 1)
    records = check["level_trim"]["records"]
    assert [(r["match"], r["applied"]) for r in records] == [(1, True), (2, False)]
    caveat = cli._guitar_check_caveats(check)[0]
    assert caveat.startswith("1 of 2 shortlisted candidates failed the guitar check")
    assert ("match-2 (the search's choice 1) lost all measurable loudness when its "
            "output gain moved -3.8 dB") in caveat
    assert "match-2 (the trimmed candidate had no measurable loudness)" in (
        cli._guitar_level_caveat(check)[1])


def test_paired_di_without_its_di_is_refused_by_name(audio, tmp_path):
    """A reamp's own DI is what paired_di asserts; without it there is no pair, and
    the no-DI search flag does not stand in for one."""
    for extra in ([], ["--search-without-di"]):
        out = tmp_path / f"paired-no-di{len(extra)}"
        done = run("match_preset.py", *extra, "--template", TEMPLATE,
                   "--reference", audio / "paired-ref.wav", "--reference-mode", "paired_di",
                   "--loss-profile", "paired-v2", "--excerpt", "0", "--amp", "sw50r",
                   "--renderer", "synthetic", "--budget", "80", "--out-dir", out)
        assert done.returncode != 0 and "Traceback" not in done.stderr
        assert "paired_di needs the reference's own DI" in done.stderr
        assert not out.exists()


def test_a_trimmed_score_past_the_templates_is_said_so(audio, tmp_path, monkeypatch):
    import dataclasses

    from scripts import match_preset as cli

    real = cli._guitar_level_trim

    def worse(*args, **kwargs):
        return [dataclasses.replace(c, total=99.0) for c in real(*args, **kwargs)]

    monkeypatch.setattr(cli, "_guitar_level_trim", worse)
    summary = _no_di_run(audio, tmp_path / "worse", monkeypatch)
    assert any(c.startswith("after its level was set through a synthetic guitar")
               for c in summary["caveats"])


def test_a_trim_failure_goes_behind_the_passes_and_ahead_of_the_checks_failures():
    """Searched order: one silenced by its trim, one that passes, one the check
    failed. Afterwards: the pass, then the trim failure, then the check failure."""
    from match import space as space_module
    from match.search import Candidate
    from scripts import match_preset as cli

    gain, inp = ("parameters", "outputGain"), ("parameters", "inputGain")
    shortlist = [Candidate(values={gain: 7.75, inp: -14.0}, total=0.3, trial_id=1),
                 Candidate(values={gain: 0.0, inp: 0.0}, total=0.4, trial_id=2),
                 Candidate(values={gain: -30.0, inp: 0.0}, total=0.5, trial_id=3)]
    renderer, evaluator = _CliffRenderer(), _ScoringEvaluator()
    check = cli._guitar_check(renderer, evaluator, {gain: 0.0, inp: 0.0}, shortlist)
    assert [row["passes"] for row in check["candidates"]] == [True, True, False]
    shortlist = cli._passing_first(shortlist, check)
    trimmed = cli._guitar_level_trim(renderer, evaluator,
                                     space_module.build("morgan", amp="sw50r"),
                                     shortlist, check, -40.0, "parameters/outputGain")

    assert [c.values[gain] for c in trimmed] == [pytest.approx(-10.0), 7.75, -30.0]
    by_rank = {row["search_rank"]: row for row in check["candidates"]}
    assert [by_rank[rank]["match"] for rank in (1, 2, 3)] == [2, 1, 3]
    assert by_rank[1]["failed_by"] == "level_trim" and "failed_by" not in by_rank[3]
    records = check["level_trim"]["records"]
    assert [r["match"] for r in records] == [1, 2, 3]
    assert [r["reason"] for r in records[1:]] == [
        "the trimmed candidate had no measurable loudness", "it failed the guitar check"]
    caveat = cli._guitar_check_caveats(check)[0]
    assert caveat.startswith("2 of 3 shortlisted candidates failed")
    assert "match-2 (the search's choice 1) lost all measurable loudness" in caveat
    assert "match-3 (the search's choice 3) was 30 dB under" in caveat
    assert "except that a candidate the trim silenced moved to the end" in (
        cli._guitar_level_caveat(check)[0])
