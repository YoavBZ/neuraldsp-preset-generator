"""The match-pipeline benchmark's summary: loudness, the guitar check, the level trim
and paired distances, computed from per-part results without the plugin."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "research"))

import benchmark_match_pipeline as P  # noqa: E402


def _arm(lu, v3, *, fallback=False, check=None):
    return {"lufs": None if lu is None else -20 + lu, "vs_reference_lu": lu,
            "v3": v3 + .1, "v3_no_level": v3, "v2": v3, "v2_no_level": v3,
            "fallback_to_template": fallback, "guitar_check": check}


def _check(passes=(True, True, True), trim=None):
    return {"candidates": [{"search_rank": i, "passes": p} for i, p in enumerate(passes, 1)],
            "level_trim": {"records": [trim] if trim else []}}


def test_the_summary_pairs_arms_and_reads_the_guitar_check_and_trim():
    trimmed = {"match": 1, "applied": True, "before": -8.0, "after": -18.0, "clamped": False,
               "residual_db": -.2}
    results = [
        {"part": "a/one/g", "template": _arm(1.0, 1.0),
         "no_di": _arm(4.0, 1.5, check=_check(trim=trimmed)), "di": _arm(0.0, .5)},
        {"part": "a/two/g", "template": _arm(-2.0, 1.2),
         "no_di": _arm(2.0, 1.0, check=_check((False, True, True),
                                              {**trimmed, "clamped": True})),
         "di": _arm(.5, .4)},
        {"part": "b/three/g", "errors": {"no_di": "RuntimeError: render failed"},
         "template": _arm(None, 2.0),
         "di": _arm(0.0, .5)},
        {"part": "b/four/g", "template": _arm(0.0, 1.0),
         "no_di": _arm(-5.0, 1.0, check=_check(trim={**trimmed, "residual_db": -2.1}))},
    ]
    summary = P.summarise(results)
    # A later arm's success does not hide an earlier arm's failure.
    assert summary["failed"] == ["b/three/g: no_di"]
    assert summary["template"]["parts"] == 4 and summary["no_di"]["parts"] == 3
    assert summary["template"]["unmeasurable"] == ["b/three/g"]
    assert summary["no_di"]["within_3_lu"] == 1 and summary["di"]["within_3_lu"] == 3
    assert summary["guitar_check_failed_a_candidate"] == ["a/two/g"]
    trim = summary["level_trim_on_match_1"]
    assert trim["applied"] == 3 and trim["clamped"] == 1
    assert trim["moved_db"]["median"] == -10.0
    # Before the trim, each answer played the trim's move louder: 4 + 10, 2 + 10,
    # -5 + 10 — the last only roughly, since its trim landed 2.1 dB off target.
    assert trim["vs_reference_lu_before_trim"]["min"] == 5.0
    assert trim["landed_off_target"] == ["b/four/g"]
    pairs = summary["paired_v3_no_level"]
    assert pairs["di_closer_than_no_di"] == {"closer": 2, "of": 2, "median_change": -.633}
    assert pairs["no_di_closer_than_template"] == {"closer": 1, "of": 3,
                                                   "median_change": 0.0}


def test_a_fallback_to_the_template_is_not_counted_as_a_trim():
    trimmed = {"match": 1, "applied": True, "before": 0.0, "after": -6.0, "clamped": False}
    results = [{"part": "a/one/g", "template": _arm(0.0, 1.0),
                "no_di": _arm(0.0, 1.0, fallback=True, check=_check(trim=trimmed))}]
    summary = P.summarise(results)
    assert summary["level_trim_on_match_1"]["applied"] == 0
    assert summary["no_di"]["fell_back_to_template"] == 1


def test_a_part_directory_name_has_no_separator_or_space():
    assert P.slug(("telefunken", "Hikikomori - Love Does", "Keys GTR")) == (
        "telefunken-Hikikomori_-_Love_Does-Keys_GTR")


def test_the_output_must_be_under_the_checkouts_runs(tmp_path):
    done = subprocess.run([sys.executable, str(ROOT / "research" / "benchmark_match_pipeline.py"),
                           "--out-dir", str(tmp_path / "elsewhere")],
                          capture_output=True, text=True, cwd=ROOT)
    assert done.returncode != 0
    assert "must be under this checkout's runs/" in done.stderr
    assert not (tmp_path / "elsewhere").exists()


def test_the_defaults_are_the_shipped_sw50r_template_and_both_arms():
    args = P.build_parser().parse_args(["--set", "2"])
    assert (args.template, args.pack, args.amp, args.sets, args.arm,
            args.process_policy) == (
        "samples/SW50R_Atlas_Topology.xml", "morgan", "sw50r", [2], None, "reuse")


def test_the_searches_render_with_the_process_policy_asked_for(tmp_path, monkeypatch):
    argvs = []

    def run(self, argv, log):
        argvs.append(argv)
        if argv[1].endswith("match_preset.py"):
            (tmp_path / "no_di").mkdir()
            (tmp_path / "no_di" / "summary.json").write_text('{"caveats": []}')

    monkeypatch.setattr(P.Runner, "run", run)
    args = P.build_parser().parse_args(["--amp", "ac20", "--process-policy", "fresh"])
    crop = {"outputs": {"reference": {"path": "ref.wav"}, "di": {"path": "di.wav"}}}
    P.Runner(args, tmp_path, "abc123").match(crop, tmp_path, "no_di")
    match = argvs[0]
    assert match[1].endswith("match_preset.py")
    assert match[match.index("--process-policy") + 1] == "fresh"
    assert match[match.index("--amp") + 1] == "ac20"
    assert "--search-without-di" in match      # the no-DI arm keeps measuring the search


def test_the_committed_summary_is_what_its_parts_summarise_to():
    committed = json.loads((ROOT / "docs" / "match-pipeline-set2-sw50r.json").read_text())
    # Fields added since it was written (e.g. silent trials) are not in it.
    recomputed = P.summarise(committed["parts"])
    assert {k: v for k, v in recomputed.items() if k in committed["summary"]} == (
        committed["summary"])


def test_a_finished_stage_is_not_run_again_and_a_failure_is_kept_until_it_passes(
        tmp_path, monkeypatch):
    import benchmark_recordings

    crop = {"reference_lufs": -18.0,
            "outputs": {"reference": {"path": "ref.wav", "sha256": "r"},
                        "di": {"path": "di.wav", "sha256": "d"}}}
    monkeypatch.setattr(benchmark_recordings, "crops_for", lambda *a: crop)
    monkeypatch.setattr(P, "score", lambda reference, wav: {
        "lufs": -18.0, "vs_reference_lu": 0.0, "v3": 1.0, "v3_no_level": 1.0})
    calls = []
    broken = {"no_di"}

    def match(self, crop, out, arm):
        calls.append(arm)
        if arm in broken:
            raise RuntimeError("match_preset.py exit 2")
        return {"caveats": [], "search": {}}, False

    monkeypatch.setattr(P.Runner, "match", match)
    monkeypatch.setattr(P.Runner, "render", lambda self, *a: calls.append("render"))
    runner = P.Runner(P.build_parser().parse_args([]), tmp_path, "abc123")
    monkeypatch.setattr(runner, "log", lambda message: None)

    first = runner.part(("s", "song", "g"), ["no_di", "di"], None, None)
    assert first["errors"] == {"no_di": "RuntimeError: match_preset.py exit 2"}
    assert "di" not in first and first["template"]["measured_commit"] == "abc123"
    calls.clear()
    second = runner.part(("s", "song", "g"), ["di"], None, None)
    assert second["errors"] == {"no_di": "RuntimeError: match_preset.py exit 2"}
    assert second["di"]["measured_commit"] == "abc123" and calls == ["di", "render"]
    broken.clear()
    calls.clear()
    third = runner.part(("s", "song", "g"), ["no_di", "di"], None, None)
    assert "errors" not in third and calls == ["no_di", "render"]


def test_a_quieter_copy_differs_from_its_source_only_in_level(tmp_path):
    for module in ("numpy", "scipy", "soundfile", "pyloudnorm"):
        pytest.importorskip(module, reason="needs the analysis extra")
    import soundfile as sf
    from analysis import io
    from analysis.probes import synthetic_guitar

    signal = synthetic_guitar(seconds=6.0, seed=13, target_lufs=-20)
    samples = getattr(signal, "samples", signal)
    sf.write(tmp_path / "loud.wav", samples, io.SAMPLE_RATE, subtype="FLOAT")
    sf.write(tmp_path / "quiet.wav", samples * 10 ** (-12 / 20), io.SAMPLE_RATE,
             subtype="FLOAT")
    row = P.score(tmp_path / "loud.wav", tmp_path / "quiet.wav")
    assert row["vs_reference_lu"] == pytest.approx(-12, abs=.05)
    assert row["v3_no_level"] == pytest.approx(0, abs=1e-6)
    assert row["v3"] > 0.1


def test_a_finished_arm_from_another_process_policy_is_refused_not_reused(
        tmp_path, monkeypatch):
    import benchmark_recordings

    crop = {"reference_lufs": -18.0,
            "outputs": {"reference": {"path": "ref.wav", "sha256": "r"},
                        "di": {"path": "di.wav", "sha256": "d"}}}
    monkeypatch.setattr(benchmark_recordings, "crops_for", lambda *a: crop)
    out = tmp_path / "s-song-g"
    out.mkdir()
    (out / "result.json").write_text(json.dumps({
        "part": "s/song/g", "template": {"lufs": -18.0},
        "no_di": {"v3_no_level": 1.0}}))   # written before the policy was recorded
    args = P.build_parser().parse_args(["--process-policy", "fresh"])
    runner = P.Runner(args, tmp_path, "abc123")
    monkeypatch.setattr(runner, "log", lambda message: None)
    result = runner.part(("s", "song", "g"), ["no_di"], None, None)
    assert "searched with --process-policy reuse" in result["errors"]["no_di"]


def test_a_plugin_that_goes_silent_mid_match_is_a_failure_set_aside_for_a_rerun(
        tmp_path, monkeypatch):
    import benchmark_recordings

    crop = {"reference_lufs": -18.0,
            "outputs": {"reference": {"path": "ref.wav", "sha256": "r"},
                        "di": {"path": "di.wav", "sha256": "d"}}}
    monkeypatch.setattr(benchmark_recordings, "crops_for", lambda *a: crop)
    monkeypatch.setattr(P, "score", lambda reference, wav: {
        "lufs": -18.0, "vs_reference_lu": 0.0, "v3": 1.0, "v3_no_level": 1.0})
    dead = {"caveats": [], "search": {"accounting": {"silent": 6},
                                      "guitar_check": {"template_lufs": None,
                                                       "candidates": []}}}

    def match(self, crop, out, arm):
        (out / arm).mkdir(exist_ok=True)
        (out / arm / "summary.json").write_text(json.dumps(dead))
        return dead, False

    monkeypatch.setattr(P.Runner, "match", match)
    monkeypatch.setattr(P.Runner, "render", lambda self, *a: None)
    runner = P.Runner(P.build_parser().parse_args([]), tmp_path, "abc123")
    monkeypatch.setattr(runner, "log", lambda message: None)
    result = runner.part(("s", "song", "g"), ["no_di"], None, None)
    assert "went silent during the match" in result["errors"]["no_di"]
    assert "no_di" not in result
    part = tmp_path / "s-song-g"
    assert not (part / "no_di").exists()
    assert (part / "no_di.silent-attempt-1" / "no_di" / "summary.json").exists()
    # A second dead attempt keeps the first.
    runner.part(("s", "song", "g"), ["no_di"], None, None)
    assert (part / "no_di.silent-attempt-2" / "no_di" / "summary.json").exists()


def test_the_library_arm_searches_through_its_probe_and_records_it(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy", reason="needs the analysis extra")
    pytest.importorskip("soundfile", reason="needs the analysis extra")
    import benchmark_recordings

    crop = {"reference_lufs": -18.0,
            "outputs": {"reference": {"path": "ref.wav", "sha256": "r"},
                        "di": {"path": "di.wav", "sha256": "d"}}}
    monkeypatch.setattr(benchmark_recordings, "crops_for", lambda *a: crop)
    monkeypatch.setattr(P, "score", lambda reference, wav: {
        "lufs": -18.0, "vs_reference_lu": 0.0, "v3": 1.0, "v3_no_level": 1.0})
    argvs = []

    def run(self, argv, log):
        argvs.append(argv)
        if argv[1].endswith("match_preset.py"):
            out = pathlib.Path(argv[argv.index("--out-dir") + 1])
            out.mkdir(parents=True)
            (out / "summary.json").write_text('{"caveats": ["nothing beat the preset '
                                              'you started from"]}')

    monkeypatch.setattr(P.Runner, "run", run)
    monkeypatch.setattr(P.Runner, "render", lambda self, *a: None)
    part = ("s", "song", "g")
    probe = np.linspace(-0.1, 0.1, 4800).astype(np.float32)
    args = P.build_parser().parse_args(["--arm", "library"])
    runner = P.Runner(args, tmp_path, "abc123", {part: (probe, ["t/x/g", "s/y/g"])})
    monkeypatch.setattr(runner, "log", lambda message: None)
    result = runner.part(part, ["library"], None, None)
    match = argvs[0]
    out = tmp_path / P.slug(part)
    assert match[match.index("--probe-di") + 1] == str(out / "library-probe.wav")
    assert match[match.index("--reference-mode") + 1] == "isolated_stem"
    assert (out / "library-probe.wav").exists()
    assert result["library"]["library_from"] == ["t/x/g", "s/y/g"]
    assert result["library"]["fallback_to_template"] is True
    # Another library in the same directory is refused, not mixed in.
    other = P.Runner(args, tmp_path, "abc123", {part: (probe * 0.5, ["t/x/g"])})
    with pytest.raises(RuntimeError, match="another library"):
        other._library_probe(part, out)


def test_the_library_arm_is_paired_with_the_template_and_the_no_di_arm():
    rows = [{"part": f"p{i}", "template": _arm(0, 1.0), "no_di": _arm(0, 1.2),
             "library": _arm(None, 0.8)} for i in range(3)]
    pairs = P.summarise(rows)["paired_v3_no_level"]
    assert pairs["library_closer_than_template"] == {"closer": 3, "of": 3,
                                                      "median_change": -0.2}
    assert pairs["library_closer_than_no_di"]["closer"] == 3
    assert P.build_parser().parse_args([]).arm is None and P.DEFAULT_ARMS == ("no_di", "di")


def _library_runner(tmp_path, monkeypatch, probe, silent_counts, extra=()):
    import benchmark_recordings

    crop = {"reference_lufs": -18.0,
            "outputs": {"reference": {"path": "ref.wav", "sha256": "r"},
                        "di": {"path": "di.wav", "sha256": "d"}}}
    monkeypatch.setattr(benchmark_recordings, "crops_for", lambda *a: crop)
    monkeypatch.setattr(P, "score", lambda reference, wav: {
        "lufs": -18.0, "vs_reference_lu": 0.0, "v3": 1.0, "v3_no_level": 1.0})
    counts = iter(silent_counts)

    def match(self, crop, out, arm):
        (out / arm).mkdir(exist_ok=True)
        return {"caveats": [], "search": {"accounting": {"silent": next(counts)}}}, False

    monkeypatch.setattr(P.Runner, "match", match)
    monkeypatch.setattr(P.Runner, "render", lambda self, *a: None)
    args = P.build_parser().parse_args(["--arm", "library", *extra])
    runner = P.Runner(args, tmp_path, "abc123", {("s", "song", "g"): (probe, ["t/x/g"])})
    monkeypatch.setattr(runner, "log", lambda message: None)
    return runner


def test_a_library_search_with_silent_renders_is_set_aside_once(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy", reason="needs the analysis extra")
    pytest.importorskip("soundfile", reason="needs the analysis extra")
    probe = np.linspace(-0.1, 0.1, 4800).astype(np.float32)
    runner = _library_runner(tmp_path, monkeypatch, probe, [12, 12],
                             ["--library-from", "other-source"])
    part = ("s", "song", "g")
    first = runner.part(part, ["library"], None, None)
    assert "silent renders" in first["errors"]["library"] and "library" not in first
    assert (tmp_path / P.slug(part) / "library.silent-attempt-1").is_dir()
    second = runner.part(part, ["library"], None, None)   # silent again: kept
    assert second["library"]["silent_trials"] == 12 and "errors" not in second
    assert second["library"]["library_from_mode"] == "other-source"
    assert P.summarise([second])["library"]["silent_trials"] == ["s/song/g"]


def test_a_finished_library_arm_is_refused_when_its_library_changed(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy", reason="needs the analysis extra")
    pytest.importorskip("soundfile", reason="needs the analysis extra")
    probe = np.linspace(-0.1, 0.1, 4800).astype(np.float32)
    part = ("s", "song", "g")
    done = _library_runner(tmp_path, monkeypatch, probe, [0]).part(part, ["library"],
                                                                    None, None)
    assert "library" in done and "errors" not in done
    changed = _library_runner(tmp_path, monkeypatch, probe * 0.5, [])
    again = changed.part(part, ["library"], None, None)
    assert "another library" in again["errors"]["library"]
