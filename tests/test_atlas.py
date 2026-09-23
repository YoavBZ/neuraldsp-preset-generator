"""The M7 response atlas stays deterministic, qualified, and queryable."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("scipy", reason="needs the analysis extra")

from analysis.fingerprint import Fingerprint
from match import atlas
from match import space as space_module
from match.renderer_synth import SyntheticRenderer
from scripts import build_response_atlas as atlas_builder
from scripts.match_preset import _seed_from_template


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _printed(tilt: float) -> dict:
    return Fingerprint(
        source={"regime": "probe", "channels": 1, "lufs_i": -18.0},
        spectrum={
            "band_centres_hz": [100.0, 1000.0, 10000.0],
            "band_db": [-4.0, 0.0, float(tilt)],
            "tilt_db_per_decade": float(tilt),
            "centroid_hz": {"p50": 1000.0 + 10.0 * tilt},
            "rolloff85_hz": {"p50": 5000.0 + 10.0 * tilt},
            "lf_corner_hz": 80.0,
            "hf_corner_hz": 12000.0,
        },
        dynamics={"crest_db": 10.0},
    ).to_dict()


def _document() -> dict:
    return {
        "schema": atlas.SCHEMA,
        "pack": "morgan",
        "amp": "pr12",
        "sample_count": 2,
        "latin_hypercube_seed": 17,
        "dimensions": ["pr12Amp/pr12Treble"],
        "fixed_settings": {"selectedAmp": 1},
        "probe": {"sha256": "abc", "sample_rate": 48000,
                  "channels": 1, "duration_s": 1.0},
        "renderer": SyntheticRenderer().metadata().as_dict(),
        "measurement_caveat": None,
        "achievable_ranges": atlas.achievable_ranges([_printed(-8), _printed(8)]),
        "entries": [
            {"settings": {"pr12Amp/pr12Treble": 20.0},
             "fingerprint": _printed(-8)},
            {"settings": {"pr12Amp/pr12Treble": 80.0},
             "fingerprint": _printed(8)},
        ],
    }


def test_pr12_topology_selects_pr12_and_only_samples_live_continuous_controls():
    space = space_module.build("morgan", amp="pr12")
    values, _ = _seed_from_template(
        ROOT / "samples" / "Example_Clean_PR12.xml", space, "morgan")
    fixed = atlas.tone_topology(values, space, "pr12")
    dimensions = atlas.sampling_dimensions(space, fixed)

    assert fixed[("", "selectedAmp")] in (1, "1")
    assert len(dimensions) == 26
    assert "pr12Amp/pr12Volume" in {dimension.path for dimension in dimensions}
    assert "cabParameters/rightCabDistance" in {
        dimension.path for dimension in dimensions}
    assert all(d.continuous for d in dimensions)
    assert not any("sw50r" in d.path or "Active" in d.path for d in dimensions)
    assert all(fixed.get(tuple(path.split("/"))) is False
               for path in atlas.TONE_EFFECT_BYPASSES)


def test_latin_hypercube_is_deterministic_and_covers_every_stratum():
    space = space_module.build("morgan", amp="pr12")
    dimension = space.by_path("pr12Amp", "pr12Treble")
    first = atlas.latin_hypercube([dimension], 8, 7)
    second = atlas.latin_hypercube([dimension], 8, 7)

    assert first == second
    # Rotation controls quantise to 0.5%, much finer than an eighth of the range.
    strata = {min(7, int(row[dimension.path] / 12.5)) for row in first}
    assert strata == set(range(8))


def test_neutral_baseline_centres_sampled_controls_but_keeps_the_topology():
    space = space_module.build("morgan", amp="pr12")
    fixed = {
        "selectedAmp": 1,
        "pr12EQ/pr12EQActive": True,
        "pr12Amp/pr12Treble": 87.0,
        "pr12EQ/pr12EQBand1": -9.0,
    }
    dimensions = [
        space.by_path("pr12Amp", "pr12Treble"),
        space.by_path("pr12EQ", "pr12EQBand1"),
    ]

    neutral = atlas.neutral_settings(fixed, dimensions)

    assert neutral["selectedAmp"] == 1
    assert neutral["pr12EQ/pr12EQActive"] is True
    assert neutral["pr12Amp/pr12Treble"] == 50.0
    assert neutral["pr12EQ/pr12EQBand1"] == 0.0


def test_nearest_returns_combined_fixed_and_sampled_settings():
    document = _document()
    target = Fingerprint.from_dict(_printed(8))

    match = atlas.nearest(document, target)[0]

    assert match.index == 1
    assert match.score == pytest.approx(0.0)
    assert match.settings == {
        "selectedAmp": 1,
        "pr12Amp/pr12Treble": 80.0,
    }


def test_achievability_reports_a_target_outside_the_sampled_range():
    document = _document()
    target = Fingerprint.from_dict(_printed(12))

    outside = atlas.outside_ranges(document, target)

    tilt = next(row for row in outside
                if row["feature"] == "spectral_tilt_db_per_decade")
    assert tilt == {
        "feature": "spectral_tilt_db_per_decade",
        "direction": "above",
        "value": 12.0,
        "sampled_min": -8.0,
        "sampled_max": 8.0,
    }
    assert atlas.uncomparable_features(document, target) == []


def test_a_feature_neither_side_measured_is_named_rather_than_called_inside():
    """`outside_ranges` skips it silently; the reader has to be told which."""
    document = _document()
    del document["achievable_ranges"]["crest_db"]
    printed = _printed(0)
    printed["spectrum"]["lf_corner_hz"] = None
    target = Fingerprint.from_dict(printed)

    assert atlas.outside_ranges(document, target) == []
    assert atlas.uncomparable_features(document, target) == [
        "crest_db", "low_frequency_corner_hz"]


def test_scale_comparison_requires_one_identical_held_out_experiment():
    baseline = _document()
    candidate = _document()
    baseline["build"] = {"validation": {
        "samples": 2, "seed": 29, "profile": "unpaired-v1",
        "neutral_mean": 2.0, "atlas_mean": 1.5,
        "neutral_median": 2.0, "atlas_median": 1.5,
        "atlas_win_rate": 0.5, "beats_neutral": True,
        "outcomes": [
            {"index": 0, "neutral_score": 2.0, "atlas_score": 1.0},
            {"index": 1, "neutral_score": 2.0, "atlas_score": 2.0},
        ],
    }}
    candidate["build"] = {"validation": {
        "samples": 2, "seed": 29, "profile": "unpaired-v1",
        "neutral_mean": 2.0, "atlas_mean": 1.0,
        "neutral_median": 2.0, "atlas_median": 1.0,
        "atlas_win_rate": 1.0, "beats_neutral": True,
        "outcomes": [
            {"index": 0, "neutral_score": 2.0, "atlas_score": 0.5},
            {"index": 1, "neutral_score": 2.0, "atlas_score": 1.5},
        ],
    }}

    comparison = atlas.compare_scale(baseline, candidate)

    assert comparison["mean_reduction_fraction"] == pytest.approx(1 / 3)
    assert comparison["candidate_better_targets"] == 2
    assert comparison["median_target_reduction_fraction"] == pytest.approx(0.375)

    candidate["build"]["validation"]["seed"] = 30
    with pytest.raises(atlas.AtlasError, match="different held-out seed"):
        atlas.compare_scale(baseline, candidate)


def test_nonreproducible_measurements_cannot_lose_their_caveat():
    document = _document()
    document["renderer"] = dict(document["renderer"], reproducible=False)
    with pytest.raises(atlas.AtlasError, match="must carry its measurement caveat"):
        atlas.validate(document)


def test_achievable_ranges_refuse_unknown_or_backwards_bounds():
    document = _document()
    document["achievable_ranges"]["brightness_centroid_hz"] = {
        "min": 2000.0, "max": 1000.0,
    }
    with pytest.raises(atlas.AtlasError, match="not a finite min/max"):
        atlas.validate(document)

    document = _document()
    document["achievable_ranges"]["marketing_warmth"] = {"min": 0.0, "max": 1.0}
    with pytest.raises(atlas.AtlasError, match="unknown response features"):
        atlas.validate(document)


def test_build_provenance_is_allowed_and_survives_load(tmp_path):
    document = _document()
    document["build"] = {"command": "python scripts/build_response_atlas.py"}
    path = tmp_path / "atlas.json"
    path.write_text(json.dumps(document))

    assert atlas.load(path)["build"]["command"].startswith("python ")


def test_python_provenance_is_portable_without_rewriting_external_interpreters(
        monkeypatch):
    monkeypatch.setattr(
        atlas_builder.sys, "executable", str(ROOT / ".venv" / "bin" / "python"))
    assert atlas_builder._portable_executable() == ".venv/bin/python"

    external = pathlib.Path("/opt/hostedtoolcache/Python/3.13/bin/python")
    monkeypatch.setattr(atlas_builder.sys, "executable", str(external))
    assert atlas_builder._portable_executable() == str(external)


def test_no_response_atlas_ships_with_the_plugin():
    """The committed atlases were 44 of the plugin's 47 MB and measured no help
    to a match, so they were removed (M7-1 in docs/tone-matching-plan.md names
    the commit that still has them). Kept out of the package and out of the
    repository, so a rebuilt one is not committed by accident."""
    package_data = (ROOT / "pyproject.toml").read_text().split(
        "[tool.setuptools.package-data]", 1)[1].split("\n[", 1)[0]
    assert "response_atlas" not in package_data
    try:
        tracked = subprocess.run(
            ["git", "ls-files", "packs"], cwd=ROOT, capture_output=True, text=True)
    except FileNotFoundError:
        pytest.skip("git is not installed")
    if tracked.returncode != 0:
        pytest.skip("not a git checkout")
    assert not [line for line in tracked.stdout.splitlines()
                if "response_atlas_" in line]


def test_dry_run_is_plugin_free_and_names_the_render_arithmetic(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_response_atlas.py"),
         "--renderer", "swift", "--samples", "16", "--held-out", "4",
         "--template", str(ROOT / "samples" / "Example_Clean_PR12.xml"),
         "--out", str(tmp_path / "atlas.json"), "--dry-run"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "26 continuous dimensions" in result.stdout
    assert "21 renders total" in result.stdout
    assert "--dry-run" in result.stdout
    assert not (tmp_path / "atlas.json").exists()


def test_compare_cli_reports_a_scale_step_between_two_builds(tmp_path):
    """The compare tool end to end, on two synthetic builds of one experiment."""
    built = {}
    for samples in (8, 16):
        built[samples] = tmp_path / f"atlas-{samples}.json"
        done = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_response_atlas.py"),
             "--pack", "morgan", "--amp", "pr12", "--renderer", "synthetic",
             "--template", str(ROOT / "samples" / "Example_Clean_PR12.xml"),
             "--samples", str(samples), "--held-out", "4", "--seconds", "1",
             "--out", str(built[samples])],
            cwd=ROOT, capture_output=True, text=True,
        )
        assert done.returncode == 0, done.stderr
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "compare_response_atlases.py"),
         "--baseline", str(built[8]), "--candidate", str(built[16])],
        cwd=ROOT, capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "8 -> 16 atlas points; 4 held-out targets" in result.stdout
    assert "candidate better on" in result.stdout


def test_query_cli_writes_ranked_specs_without_a_plugin(tmp_path):
    atlas_path = tmp_path / "atlas.json"
    atlas_path.write_text(json.dumps(_document()))
    from tests.fixtures_audio import harmonic_note, write_wav

    reference = tmp_path / "reference.wav"
    write_wav(reference, harmonic_note(seconds=1.2))
    out = tmp_path / "out"

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "query_response_atlas.py"),
         "--atlas", str(atlas_path), "--reference", str(reference),
         "--reference-mode", "probe", "--limit", "2", "--out-dir", str(out)],
        cwd=ROOT, capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "2 stored responses" in result.stdout
    assert "entry" in result.stdout
    specs = [json.loads((out / f"atlas-{rank}.json").read_text())
             for rank in (1, 2)]
    assert all(spec["parameters"][0] == {
        "module": "", "key": "selectedAmp", "value": 1,
    } for spec in specs)


def test_query_warns_that_a_noise_probe_atlas_does_not_transfer_to_a_guitar(
        tmp_path):
    """Looked up with renders of a played guitar, noise-probe atlases picked an
    entry better than neutral settings on 27 or 28 of 48, so the tool says so.
    Whatever the reference mode: `probe` means a controlled render of a known
    chain, and the guitar targets in that very measurement were one. Only an
    atlas built from a DI records no probe caveat, and only it is exempt."""
    document = _document()
    document["build"] = {"probe_caveat": "no --probe-di was given"}
    atlas_path = tmp_path / "atlas.json"
    atlas_path.write_text(json.dumps(document))
    from tests.fixtures_audio import harmonic_note, write_wav

    reference = tmp_path / "reference.wav"
    write_wav(reference, harmonic_note(seconds=1.2))

    def query(mode, built=atlas_path):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "query_response_atlas.py"),
             "--atlas", str(built), "--reference", str(reference),
             "--reference-mode", mode, "--out-dir", str(tmp_path / mode)],
            cwd=ROOT, capture_output=True, text=True,
        )

    warning = "stores a synthetic noise probe"
    ranges = "a reference inside or outside them says little"
    for mode in ("separated_stem", "probe"):
        done = query(mode)
        assert done.returncode == 0, done.stderr
        assert warning in done.stdout, mode
        assert ranges in done.stdout, mode
        assert "evidence to distrust the topology" not in done.stdout, mode

    # An atlas built with --probe-di records no probe caveat and gets no warning.
    document["build"] = {"probe_caveat": None}
    real_di = tmp_path / "real-di-atlas.json"
    real_di.write_text(json.dumps(document))
    done = query("separated_stem", real_di)
    assert warning not in done.stdout
    assert "evidence to distrust the topology" in done.stdout


def test_query_refuses_a_waveform_residual_the_atlas_does_not_store(tmp_path):
    atlas_path = tmp_path / "atlas.json"
    atlas_path.write_text(json.dumps(_document()))
    from tests.fixtures_audio import harmonic_note, write_wav

    reference = tmp_path / "reference.wav"
    write_wav(reference, harmonic_note(seconds=1.2))
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "query_response_atlas.py"),
         "--atlas", str(atlas_path), "--reference", str(reference),
         "--loss-profile", "paired-v1", "--out-dir", str(tmp_path / "out")],
        cwd=ROOT, capture_output=True, text=True,
    )

    assert result.returncode == 2
    assert "stores fingerprints rather than waveforms" in result.stderr


# --- Tone King, through the pack's own signal paths ------------------------
#
# The atlas used to resolve an amp through `space.amp_prefix`, which reads Morgan's
# `selectedAmp` and nothing else, so it refused every Tone King topology while the
# search — which goes through `packs.calibration.signal_paths` — handled Tone King
# channels fine. None of these need a Tone King preset: none may ship, and the
# atlas no longer needs one.


def _toneking_topology(amp):
    space = space_module.build("toneking", amp=amp)
    fixed = atlas.tone_topology(atlas.fixed_topology_seed(space, amp), space, amp)
    return space, fixed


@pytest.mark.parametrize("amp,own,other", [
    ("rhythm", "rhythmAmp", "leadAmp"),
    ("lead", "leadAmp", "rhythmAmp"),
])
def test_a_tone_king_channel_sweeps_its_own_amp_and_not_the_other(amp, own, other):
    space, fixed = _toneking_topology(amp)
    assert atlas.selected_path(space, fixed) == amp
    swept = {dimension.path for dimension in atlas.sampling_dimensions(space, fixed)}
    assert any(path.startswith(own) for path in swept), swept
    assert not any(path.startswith(other) for path in swept), (
        "the silent channel's controls cannot change the audio; sweeping them would "
        "spend samples on nothing"
    )


def test_tone_king_topology_holds_effects_off_and_keeps_both_cabinets_live():
    space, fixed = _toneking_topology("rhythm")
    for key in ("compActive", "drive1Active", "drive2Active", "wahActive",
                "chorusActive", "delayActive", "reverbActive"):
        assert fixed[("", key)] is False, key
    # The pack's neutral seed turns both cabinets off, which would make this the
    # amp with no speaker. Morgan's atlases have both cab mics on.
    assert fixed[("", "cab1Active")] is True
    assert fixed[("", "cab2Active")] is True
    swept = {dimension.path for dimension in atlas.sampling_dimensions(space, fixed)}
    assert {"cab1Level", "cab2Level"} <= swept
    # Pinned continuous controls must not be re-swept, or the hypercube undoes the
    # bypass: gate off at its floor, tremolo off at zero depth (and speed then dead).
    assert not {"gateThreshold", "ampTremoloDepth", "ampTremoloSpeed"} & swept
    # ...and that they hold the value that turns them off. Checking only that they
    # were unswept let a pin loop that skipped continuous controls leave the gate
    # at -48 dB and the tremolo at half depth in every atlas point, with the whole
    # suite green.
    assert fixed[("", "gateThreshold")] == -96.0
    assert fixed[("", "ampTremoloDepth")] == 0.0
    assert fixed[("", "ampTremoloSpeed")] == 0.0


def test_a_templates_attenuator_does_not_become_the_atlas_amp():
    """The first real Tone King template pinned the attenuator at -24 dB. Same
    failure as a recipe switching SW50R's Bright off: the template's taste becoming
    the atlas's definition of the amp."""
    space = space_module.build("toneking", amp="rhythm")
    seed = atlas.fixed_topology_seed(space, "rhythm")
    seed[("", "ampAttenuation")] = "1"  # -24 dB
    fixed = atlas.tone_topology(seed, space, "rhythm")
    assert fixed[("", "ampAttenuation")] == "5", "0 dB, the pack's calibration neutral"


def test_an_undeclared_pack_is_refused_rather_than_left_unbypassed():
    """An atlas with no bypass table would keep the template's delay and reverb and
    still call itself a tone atlas."""
    with pytest.raises(atlas.AtlasError, match="no atlas topology is declared"):
        atlas.atlas_pins("gojira")


class _OneOddRender:
    """Delegates to a renderer but spoils one chosen call — a stand-in for the one
    unlucky baseline render that shifted every AC20 target together."""

    def __init__(self, inner, odd_call):
        self.inner, self.odd_call, self.calls = inner, odd_call, 0

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def render(self, probe_di, settings):
        import dataclasses

        import numpy as np

        self.calls += 1
        result = self.inner.render(probe_di, settings)
        if self.calls != self.odd_call:
            return result
        frames = np.asarray(result.audio)
        t = np.arange(frames.shape[0]) / result.metadata.sample_rate
        rumble = 0.5 * np.sin(2 * np.pi * 70.0 * t)[:, None]
        return dataclasses.replace(result, audio=(frames + rumble).astype(frames.dtype))


@pytest.mark.parametrize("odd_call", [1, 3])
def test_a_replicated_baseline_absorbs_one_odd_render(odd_call):
    """The spoiled render is the first replicate in one case and the last in the
    other, so an implementation that took either end instead of the median fails
    one of them. (With the spoil in the middle, first and last both passed.)"""
    from tests.fixtures_audio import plucks

    space = space_module.build("morgan", amp="pr12")
    values, _ = _seed_from_template(ROOT / "samples/Example_Clean_PR12.xml", space, "morgan")
    fixed = atlas.tone_topology(values, space, "pr12")
    probe = plucks(seconds=1.5, gap=0.4, seed=5)
    document = atlas.build(SyntheticRenderer(), space, probe, "morgan", "pr12", 8, 17,
                           fixed=fixed)

    clean = atlas.held_out(SyntheticRenderer(), space, probe, document, 4, 29)
    # With one replicate the baseline is call 1.
    spoiled_one = atlas.held_out(_OneOddRender(SyntheticRenderer(), 1),
                                 space, probe, document, 4, 29)
    # held_out renders every baseline replicate before any target, so with three
    # replicates the baseline is calls 1-3. Spoil the first (1) or the last (3).
    spoiled_of_three = atlas.held_out(_OneOddRender(SyntheticRenderer(), odd_call),
                                      space, probe, document, 4, 29,
                                      neutral_replicates=3)

    scores = lambda result: [row["neutral_score"] for row in result["outcomes"]]
    assert spoiled_of_three["neutral_replicates"] == 3
    assert clean["neutral_replicates"] == 1
    assert scores(spoiled_one) != pytest.approx(scores(clean)), (
        "the premise: one spoiled single baseline moves every target's score"
    )
    assert scores(spoiled_of_three) == pytest.approx(scores(clean)), (
        "two good replicates out of three put the median back on the clean value"
    )


def test_zero_baseline_replicates_is_refused():
    space = space_module.build("morgan", amp="pr12")
    values, _ = _seed_from_template(ROOT / "samples/Example_Clean_PR12.xml", space, "morgan")
    fixed = atlas.tone_topology(values, space, "pr12")
    from tests.fixtures_audio import plucks

    probe = plucks(seconds=1.0, gap=0.4, seed=5)
    document = atlas.build(SyntheticRenderer(), space, probe, "morgan", "pr12", 4, 17,
                           fixed=fixed)
    with pytest.raises(atlas.AtlasError, match="at least 1"):
        atlas.held_out(SyntheticRenderer(), space, probe, document, 2, 29,
                       neutral_replicates=0)


def test_a_tone_king_atlas_needs_no_preset_in_a_dry_run(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_response_atlas.py"),
         "--pack", "toneking", "--amp", "lead", "--renderer", "swift",
         "--samples", "16", "--held-out", "4", "--neutral-replicates", "3",
         "--out", str(tmp_path / "atlas.json"), "--dry-run"],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stderr
    assert "toneking neutral seed" in result.stdout
    assert "23 renders total" in result.stdout, "16 + 4 held-out + 3 baseline"
    assert "ampAttenuation=0 dB" in result.stdout


def test_a_process_policy_without_the_plugin_is_refused_not_ignored(tmp_path):
    """The synthetic chain has no instance to reuse, so `--process-policy fresh`
    there would be accepted and do nothing — a run whose provenance claims a
    render policy it never had."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_response_atlas.py"),
         "--renderer", "synthetic", "--process-policy", "fresh",
         "--out", str(tmp_path / "atlas.json"), "--dry-run"],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode != 0
    assert "plugin renderer only" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("amp", ["pr12", "sw50r", "ac20"])
def test_a_morgan_atlas_without_a_template_still_has_a_speaker(amp):
    """The neutral seed turns Morgan's cab mics off, and an amp with no cabinet
    renders loud and non-silent, so nothing downstream would refuse it. With the
    template optional, that became a one-flag way to build a wrong atlas."""
    space = space_module.build("morgan", amp=amp)
    fixed = atlas.tone_topology(atlas.fixed_topology_seed(space, amp), space, amp)
    assert fixed[("cabParameters", "leftCabActive")] is True
    assert fixed[("cabParameters", "rightCabActive")] is True
    swept = {dimension.path for dimension in atlas.sampling_dimensions(space, fixed)}
    assert "cabParameters/leftCabDistance" in swept


def test_build_with_no_topology_applies_the_pins():
    """`atlas.build(fixed=None)` used the raw neutral seed — gate on, tremolo at
    half depth, no cabinets — rather than the pinned topology."""
    from tests.fixtures_audio import plucks

    space = space_module.build("morgan", amp="pr12")
    probe = plucks(seconds=1.0, gap=0.4, seed=5)
    default = atlas.build(SyntheticRenderer(), space, probe, "morgan", "pr12", 4, 17)
    pinned = atlas.tone_topology(atlas.fixed_topology_seed(space, "pr12"), space, "pr12")
    explicit = atlas.build(SyntheticRenderer(), space, probe, "morgan", "pr12", 4, 17,
                           fixed=pinned)
    assert default["fixed_settings"] == explicit["fixed_settings"]
    assert default["dimensions"] == explicit["dimensions"]


def test_the_templates_still_give_the_topologies_the_removed_atlases_recorded():
    """The atlases are gone but their build commands are documented, and those only
    rebuild the same atlases if each template still yields the fixed settings the
    atlas recorded. Frozen from the files in git history (commit 55490f9)."""
    frozen = json.loads((ROOT / "tests" / "atlas_topologies.json").read_text())
    for amp, recorded in frozen.items():
        space = space_module.build("morgan", amp=amp)
        values, _ = _seed_from_template(ROOT / recorded["template"], space, "morgan")
        recomputed = {atlas._path(key): value for key, value in
                      atlas.tone_topology(values, space, amp).items()}
        for key, value in recorded["fixed_settings"].items():
            assert recomputed.get(key) == value, f"{amp}: {key}"
