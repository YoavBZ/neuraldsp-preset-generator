"""Private listening evidence must not become independent validation by repetition."""
import copy
import json
import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")
pytest.importorskip("scipy")
pytest.importorskip("pyloudnorm")
from analysis import io
from analysis.compare import Objectives, compare, scalar
from analysis.fingerprint import fingerprint
from analysis.listening import attach_verdict, score_record, agreement_report, sha256
from analysis.listening import verified_fresh_ac20


@pytest.fixture
def record(tmp_path):
    time = np.arange(48000) / 48000
    paths = []
    for i, frequency in enumerate((220, 220, 440)):
        path = tmp_path / f"{i}.wav"
        sf.write(path, .1 * np.sin(2 * np.pi * frequency * time), 48000, subtype="FLOAT")
        paths.append({"path": str(path), "sha256": sha256(path)})
    return {"id": "one", "target_id": "song", "reference": {**paths[0], "regime": "probe"},
            "alternatives": dict(zip(("A", "B"), paths[1:])),
            "verdict": {"closer": "A", "preferred": "B"}}


def test_exact_profile_parity_and_separate_questions(record):
    result = score_record(record)
    target = fingerprint(io.load(record["reference"]["path"]), regime="probe", excerpt_s=None)
    other = fingerprint(io.load(record["alternatives"]["B"]["path"]), regime="probe", excerpt_s=None)
    objectives = compare(target, other, profile="unpaired-v1")
    assert result["objective_scoring"]["alternatives"]["B"]["distance_with_level"] == scalar(objectives)
    objectives.values["level"] = None
    assert result["objective_scoring"]["alternatives"]["B"]["distance"] == scalar(objectives)
    assert result["objective_scoring"]["prediction"] == "A"
    assert result["agreement"]["closer"]["status"] == "agree"
    assert result["agreement"]["preferred"]["status"] == "disagree"


def test_post_listening_verdict_uses_frozen_scores_without_audio_analysis(record, monkeypatch):
    import analysis.listening as listening

    frozen = score_record({**record, "verdict": {}})

    def must_not_rescore(*args, **kwargs):
        raise AssertionError("a listener answer must not change the prediction")

    monkeypatch.setattr(listening, "compare", must_not_rescore)
    finished = attach_verdict(frozen, {"closer": "A", "preferred": "B"})
    assert finished["objective_scoring"] == frozen["objective_scoring"]
    assert finished["agreement"]["closer"]["status"] == "agree"
    assert finished["agreement"]["preferred"]["status"] == "disagree"
    assert frozen["agreement"]["closer"]["status"] == "no_verdict"


def test_hash_verified_even_with_cache(record):
    cache = {}
    score_record(record, cache)
    record["alternatives"]["A"]["sha256"] = "changed"
    with pytest.raises(ValueError, match="hash"):
        score_record(record, cache)


@pytest.mark.parametrize("duration", [float("nan"), float("inf"), -.1, .1, 2])
def test_bad_regions_fail(record, duration):
    record["reference"]["duration_s"] = duration
    with pytest.raises(ValueError):
        score_record(record)


def test_repeats_do_not_raise_target_n(record):
    scored = score_record(record)
    rows = [{**scored, "id": str(i)} for i in range(20)]
    other = copy.deepcopy(scored)
    other.update(id="other", target_id="other-song")
    other["agreement"]["closer"]["status"] = "disagree"
    report = agreement_report(rows + [other])
    assert report["summary"]["closer"] == {
        "target_groups_with_decisive_verdicts": 2, "equal_target_weighted_agreement": .5}
    assert agreement_report([{**scored, "target_id": "unassigned"}])["summary"]["closer"]["target_groups_with_decisive_verdicts"] == 0


def test_ties_and_unknown_preference_are_not_invented(record):
    record["verdict"] = {"closer": "indistinguishable"}
    result = score_record(record)
    assert result["agreement"]["closer"]["status"] == "listener_tie"
    assert result["agreement"]["preferred"]["status"] == "no_verdict"
    assert agreement_report([result])["summary"]["closer"]["equal_target_weighted_agreement"] is None


def test_failed_rescore_never_counts_stale_agreement(record):
    scored = score_record(record)
    scored["scoring_error"] = "hash changed"
    report = agreement_report([scored])
    assert report["summary"]["closer"]["target_groups_with_decisive_verdicts"] == 0


@pytest.mark.parametrize("missing_component", [False, True])
def test_unequal_objective_coverage_is_not_decisive(record, monkeypatch, missing_component):
    import analysis.listening as listening
    original_compare = listening.compare
    calls = 0

    def uneven_compare(*args, **kwargs):
        nonlocal calls
        result = original_compare(*args, **kwargs)
        calls += 1
        if calls == 2:
            if missing_component:
                result.detail["timbre"].pop(next(iter(result.detail["timbre"])))
            else:
                result.values["timbre"] = None
                result.detail["timbre"] = {}
        return result

    monkeypatch.setattr(listening, "compare", uneven_compare)
    scored = score_record(record)
    assert not scored["objective_scoring"]["prediction_comparable"]
    assert scored["agreement"]["closer"] == {"status": "unequal_coverage", "agrees": None}
    assert scored["agreement"]["preferred"] == {"status": "unequal_coverage", "agrees": None}
    # A previously written agreement must not bypass the report's coverage gate.
    scored["agreement"]["closer"] = {"status": "agree", "agrees": True}
    report = agreement_report([scored])
    assert report["summary"]["closer"]["target_groups_with_decisive_verdicts"] == 0
    assert report["target_groups"]["song"]["closer"]["diagnostic_counts_not_independent_n"] == {"unequal_coverage": 1}


def test_missing_reference_regime_is_not_inferred(record):
    del record["reference"]["regime"]
    with pytest.raises(KeyError):
        score_record(record)


def test_channel_promotion_reproduces_playback(record):
    from analysis.listening import _audio
    source = record["alternatives"]["A"]
    mono = _audio(source)
    stereo = _audio({**source, "promote_stereo": True})
    assert stereo.channels == 2
    assert np.array_equal(stereo.samples[:, 0], mono.samples[:, 0])
    assert np.array_equal(stereo.samples[:, 1], mono.samples[:, 0])


def test_cli_retains_failed_record_but_discards_stale_scores(record, tmp_path):
    import json
    import pathlib
    import subprocess
    import sys
    stale = score_record(record)
    stale["alternatives"]["A"]["sha256"] = "changed"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"comparisons": [stale]}))
    output = tmp_path / "audit"
    done = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve().parents[1] / "scripts/score_listening.py"),
                           "--manifest", str(manifest), "--out-dir", str(output)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    row = json.loads((output / "comparison-001.json").read_text())
    assert "scoring_error" in row
    assert "objective_scoring" not in row and "agreement" not in row
    report = json.loads((output / "report.json").read_text())
    assert report["scored_count"] == 0
    assert report["summary"]["closer"]["target_groups_with_decisive_verdicts"] == 0


def test_cli_refuses_unignored_private_audit_inside_git(record, tmp_path):
    import pathlib
    import subprocess
    import sys
    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"comparisons": [record]}))
    output = repository / "private" / "audit"
    command = [sys.executable, str(pathlib.Path(__file__).resolve().parents[1] / "scripts/score_listening.py"),
               "--manifest", str(manifest), "--out-dir", str(output)]
    refused = subprocess.run(command, capture_output=True, text=True)
    assert refused.returncode != 0 and "not Git-ignored" in refused.stderr
    assert not output.exists()
    (repository / ".gitignore").write_text("private/audit/report.json\nprivate/audit/comparison-001.json\n")
    partial = subprocess.run(command, capture_output=True, text=True)
    assert partial.returncode != 0 and "not Git-ignored" in partial.stderr
    assert not output.exists()
    (repository / ".gitignore").write_text("private/\n")
    allowed = subprocess.run(command, capture_output=True, text=True)
    assert allowed.returncode == 0, allowed.stderr
    assert (output / "report.json").exists()


def test_private_objective_verdict_sidecar_is_git_ignored():
    import pathlib
    import subprocess
    root = pathlib.Path(__file__).resolve().parents[1]
    # Check the pattern outside runs/ too; the verdict tool follows its key.
    for name in ("example.flac.key.json.123.objective-verdict.json",
                 "custom.json.123.objective-verdict.json"):
        sidecar = root / name
        subprocess.run(["git", "-C", str(root), "check-ignore", "--quiet", "--", str(sidecar)], check=True)


def test_ac20_history_remains_uncertain_without_bound_fresh_proof(record, tmp_path):
    record["render_provenance"] = {"A": {"amp_model": "AC20", "process_policy": "fresh"}}
    assert score_record(record)["objective_scoring"]["ac20_history_uncertain"] == ["A"]
    assert score_record(record)["objective_scoring"]["amp_model_unknown"] == ["B"]
    proof_path = tmp_path / "fresh.json"
    proof = {"schema": "listening-fresh-render-v1", "pack": "morgan", "amp_model": "AC20",
             "process_policy": "fresh", "renderer": {"quality_mode": "process=fresh"},
             "audio": record["alternatives"]["A"]}
    proof_path.write_text(json.dumps(proof))
    record["render_provenance"]["A"]["render_record"] = {"path": str(proof_path), "sha256": sha256(proof_path)}
    assert score_record(record)["objective_scoring"]["ac20_history_uncertain"] == []
    proof["renderer"]["quality_mode"] = "process=reuse"
    proof_path.write_text(json.dumps(proof))
    record["render_provenance"]["A"]["render_record"]["sha256"] = sha256(proof_path)
    with pytest.raises(ValueError, match="does not prove"):
        score_record(record)


def test_missing_amp_provenance_is_explicitly_unknown(record):
    result = score_record(record)
    assert result["objective_scoring"]["amp_model_unknown"] == ["A", "B"]
    assert result["objective_scoring"]["ac20_history_uncertain"] == []
    group = agreement_report([result])["target_groups"]["song"]
    assert group["amp_model_unknown_count_not_independent_n"] == 1


def test_fresh_renderer_keeps_every_writable_setting():
    from packs.loader import load_pack
    from scripts.render_listening_guitar import _all_writable_settings, _amp
    pack = load_pack("morgan")
    values = {"/selectedAmp": "AC20", "parameters/transpose": 2,
              "ac20Amp/ac20Volume": 30}
    mapped = _all_writable_settings(values, pack, {"selectedAmp", "parameters/transpose", "ac20Amp/ac20Volume"})
    assert mapped == {"selectedAmp": "AC20", "parameters/transpose": 2, "ac20Amp/ac20Volume": 30}
    assert _amp(mapped, pack) == "AC20"
    assert _all_writable_settings({"/selectedAmp": "AC20", "/parameters/transpose": 2},
                                  pack, None) == {"selectedAmp": "AC20", "parameters/transpose": 2}
    with pytest.raises(ValueError, match="unsupported"):
        _all_writable_settings({**values, "invented/control": 1}, pack, None)
    with pytest.raises(ValueError, match="unsupported"):
        _all_writable_settings(values, pack, {"selectedAmp", "ac20Amp/ac20Volume"})


def test_fresh_renderer_reads_full_xml_preset_not_only_search_dimensions():
    import pathlib
    from packs.loader import load_pack
    from scripts.render_listening_guitar import _settings_from_preset

    pack = load_pack("morgan")
    root = pathlib.Path(__file__).resolve().parents[1]
    values = _settings_from_preset(root / "samples/Example_Clean_PR12.xml", pack, None)
    assert values["selectedAmp"] == "1"
    assert "name" in values
    assert "parameters/transpose" in values
    assert len(values) > 100
    assert "version" not in values


def test_fresh_renderer_rejects_a_parseable_preset_missing_one_control(tmp_path):
    import pathlib
    from format.parser import parse_file
    from format.structured import build
    from format.writer import write_file
    from packs.loader import load_pack
    from scripts.render_listening_guitar import _settings_from_preset

    sample = pathlib.Path(__file__).resolve().parents[1] / "samples/Example_Clean_PR12.xml"
    tokens = parse_file(str(sample))
    parameter = build(tokens).by_path[("parameters", "transpose")]
    omitted = {parameter.key_index, parameter.value_index}
    incomplete = tmp_path / "incomplete.xml"
    write_file(str(incomplete), (token for index, token in enumerate(tokens)
                                 if index not in omitted))
    assert ("parameters", "transpose") not in build(parse_file(str(incomplete))).by_path
    with pytest.raises(ValueError, match="preset omits 1 writable control.*parameters/transpose"):
        _settings_from_preset(incomplete, load_pack("morgan"), None)


def test_toneking_channel_and_record_preset_are_read_without_morgan_assumptions(tmp_path):
    from packs.loader import load_pack
    from scripts.render_listening_guitar import _all_writable_settings, _amp, _settings_from_preset
    from match.renderer_preset import toneking_channel
    from tests.test_records import preset, record as binary_record

    pack = load_pack("toneking")
    assert _amp({"ampType": "Lead Channel"}, pack) == "Lead Channel"
    assert _all_writable_settings({"/ampType": 1, "/leadAmpMidBite": .5}, pack, None) == {
        "ampType": 1, "leadAmpMidBite": .5}
    with pytest.raises(ValueError, match="omit ampType"):
        _all_writable_settings({"leadAmpMidBite": .5}, pack, None)

    # Keep this fixture synthetic: the installed factory preset is not ours to
    # commit. A small pack still exercises the production record-state parser.
    path = tmp_path / "toneking.xml"
    path.write_bytes(preset(binary_record("ampType", 1),
                            binary_record("drive1Treble"),
                            binary_record("opaqueFutureControl", .5)))
    assert toneking_channel(path.read_bytes()) == "Lead Channel"
    with pytest.raises(ValueError, match="only Morgan"):
        _settings_from_preset(path, pack, None)
    path.write_bytes(preset(binary_record("ampType", 0)))
    assert toneking_channel(path.read_bytes()) == "Rhythm Channel"


def test_toneking_objective_diagnostic_knows_verified_channels(record):
    record["render_provenance"] = {
        "A": {"pack": "toneking", "amp_model": "Lead Channel"},
        "B": {"pack": "toneking", "amp_model": "Rhythm Channel"},
    }
    assert score_record(record)["objective_scoring"]["amp_model_unknown"] == []
