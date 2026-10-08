"""Confirmation preparation only: every part, manifest and cache here is synthetic."""

import json
from dataclasses import replace
import multiprocessing
import pickle
import sys
import types
from concurrent.futures import ProcessPoolExecutor

import pytest

from learn import phase2_set3 as P
from learn import set3


PARTS = [
    {"slug": "synthetic-a", "judge_lag_samples": 7, "band": "Fake A", "gain_class": "clean"},
    {"slug": "synthetic-b", "judge_lag_samples": -3, "band": "Fake B", "gain_class": "clean"},
]
NAMES = {"sw50r": ["template+R", "factory:synthetic"]}


@pytest.fixture(autouse=True)
def synthetic_parts(monkeypatch, tmp_path):
    # No test may fall through to real set-3 metadata or data roots.
    monkeypatch.setattr(set3, "parts", lambda split: [dict(p, split=split) for p in PARTS])
    for name in ("OUT", "CROPS", "STEMS", "CACHE"):
        monkeypatch.setattr(P, name, tmp_path / name.lower())


@pytest.fixture
def confirmation(tmp_path):
    manifest = tmp_path / "synthetic-manifest.json"
    manifest.write_text('{"synthetic": true}')
    config = P.RunConfig(split="held_out", amps=("sw50r",), workers=2,
                         confirmation_manifest=manifest, model=tmp_path / "synthetic.pt")
    return replace(config, confirmation_sha256=P._manifest_digest(config))


def validator(monkeypatch, function):
    module = types.ModuleType("learn.set3_confirmation")
    module.validate_manifest = function
    module.summarize = lambda distances, parts, manifest: {"synthetic_summary": True}
    module.combined_verdict = lambda waveform, onset, amps: {"synthetic_combined": list(amps)}
    monkeypatch.setitem(sys.modules, "learn.set3_confirmation", module)
    monkeypatch.setattr(__import__("learn", fromlist=["set3_confirmation"]),
                        "set3_confirmation", module, raising=False)


def fake_panel(monkeypatch):
    module = types.ModuleType("render_preset_panel")
    module._slug = lambda name: name.replace(":", "_").replace("/", "_")
    module.FACTORY = "synthetic-factory"
    module.candidates = lambda args, pack, renderer: {n: None for n in [*NAMES[args.amp], "template"]}
    monkeypatch.setitem(sys.modules, "render_preset_panel", module)
    return module


def complete(config, panel, slug, kind):
    base = config.out / kind / slug
    base.mkdir(parents=True, exist_ok=True)
    (base / "done").write_text(P._manifest_digest(config))
    (base / "di.npy").write_bytes(b"synthetic DI placeholder; scoring mocks numpy.load")
    for amp, names in NAMES.items():
        (base / amp).mkdir(exist_ok=True)
        for name in names:
            (base / amp / f"{panel._slug(name)}.flac").write_bytes(b"synthetic render placeholder")


def test_default_config_and_cli_preserve_development(monkeypatch):
    config = P.RunConfig()
    assert (config.split, config.out, config.amps, config.workers) == (
        "development", P.OUT.resolve(), P.AMPS, 6)
    called = []
    monkeypatch.setattr(P, "render", lambda *args, **kw: called.append((args, kw)))
    P.main(["render"])
    args, kw = called.pop()
    assert args[:1] == (["measure", "flatref"],)
    assert kw["config"] == config


@pytest.mark.parametrize("settings", [
    {"split": "typo"}, {"split": "held_out"}, {"workers": 0},
    {"amps": ()}, {"amps": ("unknown",)}, {"amps": ("pr12", "pr12")},
])
def test_invalid_config_fails_closed(settings):
    with pytest.raises(ValueError):
        P.RunConfig(**settings)
    assert not P.OUT.exists()


@pytest.mark.parametrize("kind", ["flatstem", "netstem"])
def test_heldout_declaration_does_not_authorize_stem_reads(confirmation, kind):
    with pytest.raises(ValueError, match="does not authorize reading stems"):
        P.render([kind], str(confirmation.model), config=confirmation)
    assert not confirmation.out.exists()


@pytest.mark.parametrize("operation", ["render", "score"])
def test_validator_failure_precedes_operational_io(monkeypatch, confirmation, operation):
    called = []

    def reject(path, **kw):
        called.append((path, kw))
        raise ValueError("draft declaration")

    validator(monkeypatch, reject)
    monkeypatch.setattr(P, "_prepare_output", lambda config: pytest.fail("output touched before approval"))
    monkeypatch.setattr(P, "recording", lambda *args: pytest.fail("audio read before approval"))
    with pytest.raises(ValueError, match="draft declaration"):
        if operation == "render":
            P.render(["net"], confirmation.model, shard=(1, 2), config=confirmation)
        else:
            P.score(config=confirmation)
    path, kw = called.pop()
    assert path == confirmation.confirmation_manifest
    assert kw == dict(model=confirmation.model, amps=confirmation.amps,
                      parts=[dict(p, split="held_out") for p in PARTS],
                      out=confirmation.out, require_declared=True)
    assert not confirmation.out.exists()


def test_missing_verifier_has_no_fallback(monkeypatch, confirmation):
    monkeypatch.setitem(sys.modules, "learn.set3_confirmation", None)
    monkeypatch.delattr(__import__("learn"), "set3_confirmation", raising=False)
    with pytest.raises(ImportError):
        P._prepare_run(confirmation)
    assert not confirmation.out.exists()


def test_development_selects_parts_without_validator(monkeypatch):
    validator(monkeypatch, lambda *args, **kw: pytest.fail("development called verifier"))
    config, parts, manifest = P._prepare_run(P.RunConfig())
    assert list(parts) == [p["slug"] for p in PARTS]
    assert manifest is None


@pytest.mark.parametrize("suffix", ["same", "child", "parent", "alias"])
def test_heldout_rejects_development_output_overlap(tmp_path, confirmation, suffix):
    out = {"same": P.OUT, "child": P.OUT / "child", "parent": P.OUT.parent}.get(suffix)
    if suffix == "alias":
        P.OUT.mkdir()
        out = tmp_path / "alias"
        out.symlink_to(P.OUT, target_is_directory=True)
    with pytest.raises(ValueError, match="separate from development"):
        P.RunConfig(split="held_out", out=out,
                    confirmation_manifest=confirmation.confirmation_manifest)


def test_custom_output_cannot_change_split_or_manifest(tmp_path, confirmation):
    P._prepare_output(confirmation)
    P._prepare_output(confirmation)  # same frozen run may resume
    with pytest.raises(ValueError, match="differs"):
        P._prepare_output(P.RunConfig(out=confirmation.out))
    confirmation.confirmation_manifest.write_text('{"synthetic": "changed"}')
    with pytest.raises(ValueError, match="changed since validation"):
        P._prepare_output(confirmation)


def test_heldout_rejects_unmarked_cache_and_custom_development_ancestor(tmp_path, confirmation):
    confirmation.out.mkdir()
    (confirmation.out / "old-cache").write_text("synthetic")
    with pytest.raises(ValueError, match="unverified cache"):
        P._prepare_output(confirmation)
    custom_dev = tmp_path / "custom-development"
    P._prepare_output(P.RunConfig(out=custom_dev))
    nested = P.RunConfig(split="held_out", out=custom_dev / "held",
                         confirmation_manifest=confirmation.confirmation_manifest,
                         confirmation_sha256=confirmation.confirmation_sha256)
    with pytest.raises(ValueError, match="nested"):
        P._prepare_output(nested)


def test_manifest_change_during_validation_fails(monkeypatch, confirmation):
    validator(monkeypatch, lambda path, **kw: path.write_text('{"changed": true}'))
    with pytest.raises(ValueError, match="changed during validation"):
        P._prepare_run(confirmation)
    assert not confirmation.out.exists()


def test_incomplete_and_unverified_completion_markers_fail(monkeypatch, confirmation):
    panel = fake_panel(monkeypatch)
    complete(confirmation, panel, "synthetic-a", "net")
    base = confirmation.out / "net" / "synthetic-a"
    P._require_complete(confirmation, "net", "synthetic-a", NAMES)
    (base / "done").write_text("")
    with pytest.raises(ValueError, match="unverified"):
        P._require_complete(confirmation, "net", "synthetic-a", NAMES)
    (base / "done").write_text(P._manifest_digest(confirmation))
    (base / "sw50r" / f"{panel._slug('factory:synthetic')}.flac").unlink()
    with pytest.raises(ValueError, match="incomplete net"):
        P._require_complete(confirmation, "net", "synthetic-a", NAMES)


def scoring_dependencies(monkeypatch):
    panel = fake_panel(monkeypatch)
    import match.renderer_au
    import packs.loader

    monkeypatch.setattr(packs.loader, "load_pack", lambda name: object())
    return panel


@pytest.mark.parametrize("missing", ["measure", "net", "candidate", "di"])
def test_score_requires_every_part_and_candidate_before_workers(monkeypatch, confirmation, missing):
    panel = scoring_dependencies(monkeypatch)
    validator(monkeypatch, lambda *args, **kw: {})
    P._prepare_run(confirmation)
    for part in PARTS:
        for kind in ("measure", "net"):
            complete(confirmation, panel, part["slug"], kind)
    base = confirmation.out / (missing if missing in ("measure", "net") else "net") / "synthetic-b"
    target = base / ("di.npy" if missing == "di" else "done")
    if missing == "candidate":
        target = base / "sw50r" / f"{panel._slug('template+R')}.flac"
    target.unlink()
    monkeypatch.setattr("concurrent.futures.ProcessPoolExecutor",
                        lambda *args, **kw: pytest.fail("workers started with incomplete parts"))
    with pytest.raises(ValueError, match="incomplete"):
        P.score(config=confirmation)


@pytest.mark.parametrize("failure", [None, "manifest_changed", "missing_part"])
def test_score_passes_config_and_keeps_refusals_with_separate_summary(monkeypatch, confirmation, failure):
    panel = scoring_dependencies(monkeypatch)
    validator(monkeypatch, lambda *args, **kw: {})
    P._prepare_run(confirmation)
    for part in PARTS:
        for kind in ("measure", "net"):
            complete(confirmation, panel, part["slug"], kind)
    seen = []

    class Executor:
        def __init__(self, workers):
            assert workers == confirmation.workers

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def map(self, worker, jobs):
            assert worker is P._score_part
            for job in jobs:
                config, slug, lag, names, frozen = pickle.loads(pickle.dumps(job))
                assert config == confirmation and names == NAMES
                assert frozen is None
                seen.append((slug, lag))
                if failure == "manifest_changed":
                    confirmation.confirmation_manifest.write_text('{"changed_after_validation": true}')
                if failure == "missing_part" and slug == "synthetic-b":
                    continue
                yield slug, {"recording|sw50r|net_A": {"template+R": None}}

    monkeypatch.setattr("concurrent.futures.ProcessPoolExecutor", Executor)
    monkeypatch.setitem(sys.modules, "kill_tests", None)
    if failure:
        with pytest.raises(ValueError, match="changed since validation|every selected part"):
            P.score(config=confirmation)
        assert not (confirmation.out / "distances.json").exists()
        return
    distances = P.score(config=confirmation)
    assert seen == [(p["slug"], p["judge_lag_samples"]) for p in PARTS]
    assert json.loads((confirmation.out / "distances.json").read_text()) == distances
    assert distances["synthetic-a"]["recording|sw50r|net_A"]["template+R"] is None
    assert json.loads((confirmation.out / "confirmation.json").read_text()) == {"synthetic_summary": True}
    assert not (confirmation.out / "result.json").exists()
    assert not (confirmation.out / "confirmation-verdict.json").exists()


def _spawned_paths(config):
    # Imported afresh under spawn: parent monkeypatches of module globals are absent.
    return config.out, config.crops, config.stems, config.cache, config.amps, P.OUT


def test_worker_config_survives_real_spawn(tmp_path):
    config = P.RunConfig(out=tmp_path / "explicit-output", amps=("sw50r",), workers=1)
    with ProcessPoolExecutor(1, mp_context=multiprocessing.get_context("spawn")) as executor:
        result = executor.submit(_spawned_paths, config).result(timeout=30)
    assert result[:5] == (config.out, config.crops, config.stems, config.cache, config.amps)
    assert result[5] != P.OUT  # confirms the child really reimported the original globals


def test_score_worker_uses_explicit_paths_and_preserves_none(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    config = P.RunConfig(out=tmp_path / "explicit-output", amps=("sw50r",))
    panel = fake_panel(monkeypatch)
    for kind in ("measure", "net"):
        base = config.out / kind / "synthetic-a"
        base.mkdir(parents=True)
        (base / "done").write_text("")
        np.save(base / "di.npy", np.zeros(8))
    reads = []
    monkeypatch.setattr(P, "mono", lambda path: reads.append(path) or np.zeros(8))
    aligned = types.ModuleType("analysis.aligned")
    aligned.aligned_distance = lambda *args, **kw: types.SimpleNamespace(distance=None)
    monkeypatch.setitem(sys.modules, "analysis.aligned", aligned)
    monkeypatch.setattr(P, "OUT", tmp_path / "wrong-global-out")
    monkeypatch.setattr(P, "CROPS", tmp_path / "wrong-global-crops")
    slug, distances = P._score_part((config, "synthetic-a", 7, NAMES, None))
    assert slug == "synthetic-a"
    assert reads[0] == config.crops / slug / "reference.wav"
    assert all(path.is_relative_to(config.out) or path.is_relative_to(config.crops) for path in reads)
    assert all(value is None for row in distances.values() for value in row.values())


@pytest.mark.parametrize("result, expected", [("disagrees", 71), ("agrees", 7), ("unchecked", 7)])
def test_onset_uses_only_declared_disagreement(confirmation, result, expected):
    part = dict(PARTS[0], onset_check={"result": result, "onset_lag_samples": 123})
    assert P._score_lag(part, replace(confirmation, lag_mode="onset")) == expected
    assert P._score_lag(part, confirmation) == 7


def test_onset_invalid_or_missing_declared_lag_fails(confirmation):
    config = replace(confirmation, lag_mode="onset")
    with pytest.raises(KeyError):
        P._score_lag(dict(PARTS[0], onset_check={"result": "disagrees"}), config)
    with pytest.raises(ValueError, match="invalid declared"):
        P._score_lag(dict(PARTS[0], onset_check={"result": "disagrees", "onset_lag_samples": None}), config)


def test_onset_is_scoring_only(confirmation):
    with pytest.raises(ValueError, match="only defined"):
        P.RunConfig(lag_mode="onset")
    with pytest.raises(ValueError, match="scoring sensitivity"):
        P.render(["measure"], confirmation.model, config=replace(confirmation, lag_mode="onset"))


def test_onset_output_and_frozen_network_selection(monkeypatch, confirmation):
    panel = scoring_dependencies(monkeypatch)
    validator(monkeypatch, lambda *args, **kw: {"synthetic_verified": True})
    P._prepare_run(confirmation)
    primary = {}
    for part in PARTS:
        for kind in ("measure", "net"):
            complete(confirmation, panel, part["slug"], kind)
        primary[part["slug"]] = {f"{bs}|sw50r|net_A": {"template+R": 8, "factory:synthetic": None}
                                 for bs in P.BAND_SETS}
    waveform = confirmation.out / "distances.json"
    waveform.write_text(json.dumps(primary))
    primary_bytes = waveform.read_bytes()
    (confirmation.out / "confirmation.json").write_text('{"synthetic_primary_summary": true}')
    config = replace(confirmation, lag_mode="onset")
    seen = []

    class Executor:
        def __init__(self, workers):
            assert workers == config.workers

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def map(self, worker, jobs):
            for actual, slug, lag, names, frozen_A in jobs:
                assert actual == config
                assert frozen_A == (primary[slug] if actual.lag_mode == "onset" else None)
                seen.append(slug)
                yield slug, primary[slug]

    monkeypatch.setattr("concurrent.futures.ProcessPoolExecutor", Executor)
    distances = P.score(config=config)
    assert set(seen) == {p["slug"] for p in PARTS}
    assert json.loads((config.out / "distances-onset.json").read_text()) == distances
    assert (config.out / "confirmation-onset.json").is_file()
    assert waveform.read_bytes() == primary_bytes
    assert json.loads((config.out / "confirmation.json").read_text()) == {"synthetic_primary_summary": True}
    assert json.loads((config.out / "confirmation-verdict.json").read_text()) == {
        "synthetic_combined": ["sw50r"]}
    # Replacing the primary invalidates sensitivity that froze the old selections.
    primary["synthetic-a"]["recording|sw50r|net_A"]["template+R"] = 0.25
    config = confirmation
    P.score(config=config)
    assert json.loads(waveform.read_text()) == primary
    for stale in ("distances-onset.json", "confirmation-onset.json", "confirmation-verdict.json"):
        assert not (config.out / stale).exists()


def test_onset_requires_complete_waveform_selections(confirmation):
    config = replace(confirmation, lag_mode="onset")
    config.out.mkdir()
    with pytest.raises(FileNotFoundError):
        P._waveform_selections(config, {p["slug"]: p for p in PARTS}, NAMES)
    (config.out / "distances.json").write_text(json.dumps({p["slug"]: {} for p in PARTS}))
    with pytest.raises(ValueError, match="missing waveform selections"):
        P._waveform_selections(config, {p["slug"]: p for p in PARTS}, NAMES)


def test_onset_worker_scores_measure_at_sensitivity_lag_without_rebuilding_picks(monkeypatch, confirmation):
    np = pytest.importorskip("numpy")
    config = replace(confirmation, lag_mode="onset")
    panel = fake_panel(monkeypatch)
    for kind in ("measure", "net"):
        complete(config, panel, "synthetic-a", kind)
        np.save(config.out / kind / "synthetic-a" / "di.npy", np.zeros(8))
    monkeypatch.setattr(P, "mono", lambda path: np.zeros(8))
    calls = []
    aligned = types.ModuleType("analysis.aligned")

    def distance(*args, **kw):
        calls.append(kw)
        return types.SimpleNamespace(distance=5)

    aligned.aligned_distance = distance
    monkeypatch.setitem(sys.modules, "analysis.aligned", aligned)
    frozen = {f"{bs}|sw50r|net_A": {"template+R": 2, "factory:synthetic": None} for bs in P.BAND_SETS}
    slug, distances = P._score_part((config, "synthetic-a", 71, NAMES, frozen))
    assert calls and all(call["lag"] == 71 for call in calls)
    assert all(distances[key] == values for key, values in frozen.items())


@pytest.mark.parametrize("setting", ["cache", "crops", "stems"])
def test_heldout_rejects_unvalidated_data_root_overrides(monkeypatch, tmp_path, confirmation, setting):
    validator(monkeypatch, lambda *args, **kw: pytest.fail("unvalidated override reached validator"))
    config = replace(confirmation, **{setting: tmp_path / "unvalidated-root"})
    with pytest.raises(ValueError, match=f"validated default {setting}"):
        P._prepare_run(config)
    assert not config.out.exists()


@pytest.mark.parametrize("lag_mode", ["waveform", "onset"])
@pytest.mark.parametrize("failure", ["missing_render", "worker", "validator"])
def test_failed_attempt_archives_prior_pass_before_checks(monkeypatch, confirmation, lag_mode, failure):
    config = replace(confirmation, lag_mode=lag_mode)
    panel = scoring_dependencies(monkeypatch)
    P._prepare_output(config)
    for part in PARTS:
        for kind in ("measure", "net"):
            complete(config, panel, part["slug"], kind)
    primary = {p["slug"]: {f"{bs}|sw50r|net_A": dict.fromkeys(NAMES["sw50r"], 1.0)
                           for bs in P.BAND_SETS} for p in PARTS}
    artifacts = {
        "distances.json": json.dumps(primary),
        "distances-onset.json": '{"synthetic_old_sensitivity": true}',
        "confirmation.json": '{"passed": true}',
        "confirmation-onset.json": '{"passed": true}',
        "confirmation-verdict.json": '{"confirmed_amp_track_only": true}',
    }
    for name, data in artifacts.items():
        (config.out / name).write_text(data)

    def assert_pending():
        status = json.loads((config.out / "score-attempt.json").read_text())
        assert status["state"] == "pending" and status["lag_mode"] == lag_mode
        assert all(not (config.out / name).exists() for name in artifacts)

    def validate(*args, **kw):
        assert_pending()
        if failure == "validator":
            raise ValueError("synthetic validation failure")
        return {}

    validator(monkeypatch, validate)
    if failure == "missing_render":
        (config.out / "net" / "synthetic-b" / "done").unlink()

    class Executor:
        def __init__(self, workers):
            assert_pending()
            if failure != "worker":
                pytest.fail("incomplete/invalid run reached workers")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def map(self, worker, jobs):
            raise RuntimeError("synthetic worker failure")

    monkeypatch.setattr("concurrent.futures.ProcessPoolExecutor", Executor)
    with pytest.raises((ValueError, RuntimeError), match="incomplete|synthetic"):
        P.score(config=config)
    status = json.loads((config.out / "score-attempt.json").read_text())
    assert status["state"] == "failed" and status["error"]["message"]
    assert all(not (config.out / name).exists() for name in artifacts)
    history = config.out / status["history"]
    for name, data in artifacts.items():
        assert (history / name).read_text() == data
    assert json.loads((history / "attempt.json").read_text()) == status


@pytest.mark.parametrize("identity", ["development", "other_manifest", "canonical_development"])
def test_validation_failure_does_not_modify_unverified_or_development_output(
        monkeypatch, confirmation, identity):
    config = confirmation
    if identity == "canonical_development":
        # Defensive check even if a caller bypasses the frozen config's constructor.
        object.__setattr__(config, "out", P.OUT)
    config.out.mkdir()
    marker = {"split": "development"} if identity == "development" else {
        "split": "held_out", "confirmation_manifest_sha256": "different manifest"}
    if identity == "canonical_development":
        marker["confirmation_manifest_sha256"] = P._manifest_digest(config)
    (config.out / "split.json").write_text(json.dumps(marker))
    verdict = config.out / "confirmation-verdict.json"
    verdict.write_text("synthetic existing artifact")

    def reject(*args, **kw):
        raise ValueError("synthetic rejected manifest")

    validator(monkeypatch, reject)
    with pytest.raises(ValueError, match="rejected manifest"):
        P.score(config=config)
    assert verdict.read_text() == "synthetic existing artifact"
    assert {p.name for p in config.out.iterdir()} == {"split.json", verdict.name}
