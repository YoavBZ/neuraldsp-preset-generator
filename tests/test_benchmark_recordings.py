"""The recordings benchmark picks development parts only and pairs 'other' across songs."""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import benchmark_recordings as R  # noqa: E402

CATALOG = {"sessions": [
    {"source": "a", "song": "one", "split": "development",
     "files": {"di.wav": "d1", "amp.wav": "a1"},
     "parts": [{"part": "g1", "usable": True, "di": "di.wav", "reference": "amp.wav"},
               {"part": "g2", "usable": True},
               {"part": "g3", "usable": False}]},
    {"source": "a", "song": "two", "split": "held_out",
     "parts": [{"part": "g1", "usable": True}]},
    {"source": "b", "song": "three", "split": "development",
     "parts": [{"part": "x", "usable": True}]},
]}


def test_only_usable_development_parts_are_targets():
    assert R.development_parts(CATALOG) == [("a", "one", "g1"), ("a", "one", "g2"),
                                            ("b", "three", "x")]


def test_set_picks_parts_by_validation_set_and_an_unmarked_session_is_the_first():
    catalog = {"sessions": [*CATALOG["sessions"],
                            {"source": "c", "song": "four", "split": "development",
                             "set": 2, "parts": [{"part": "y", "usable": True}]}]}
    assert R.development_parts(catalog, sets=[1]) == R.development_parts(CATALOG)
    assert R.development_parts(catalog, sets=[2]) == [("c", "four", "y")]
    assert len(R.development_parts(catalog)) == 4
    assert R.build_parser().parse_args(
        ["--amp", "x", "--signal", "same", "--set", "1"]).sets == [1]


def test_another_songs_di_comes_from_a_different_session():
    parts = R.development_parts(CATALOG)
    assert [R.other_di_index(parts, i) for i in range(3)] == [2, 2, 0]
    assert R.other_di_index([("a", "one", "g1"), ("a", "one", "g2")], 0) is None


def _cached(tmp_path, record_changes=None):
    """A catalog and a cached crop record for development part a/one/g1."""
    import hashlib
    import json

    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({**CATALOG, "schema": "validation-datasets-2"}))
    out_dir = tmp_path / "crops" / "a-one-g1"
    out_dir.mkdir(parents=True)
    wav = out_dir / "di.wav"
    wav.write_bytes(b"crop")
    record = {"source": "a", "song": "one", "part": "g1", "split": "development",
              "catalog": {"sha256": hashlib.sha256(catalog.read_bytes()).hexdigest()},
              "verified_source_sha256": {"di.wav": "d1", "amp.wav": "a1"},
              "removed_own_amp_tracks": ["amp.wav"], "excluded_guitar_dis": ["di.wav"],
              "outputs": {"di": {"path": str(wav),
                                 "sha256": hashlib.sha256(b"crop").hexdigest()}}}
    record.update(record_changes or {})
    (out_dir / "record.json").write_text(json.dumps(record))
    return catalog, wav


def test_a_cached_crop_is_reused_only_for_its_own_part_and_sources(tmp_path):
    import json

    catalog, _ = _cached(tmp_path)
    assert R.crops_for(catalog, tmp_path, tmp_path / "crops", "a", "one", "g1")["part"] == "g1"

    # A growing held-out ledger changes the catalog file but not the crop.
    document = json.loads(catalog.read_text())
    document["held_out_uses"] = [{"test_id": "t"}]
    catalog.write_text(json.dumps(document))
    assert R.crops_for(catalog, tmp_path, tmp_path / "crops", "a", "one", "g1")["part"] == "g1"

    for name, changes in (("split", {"split": "held_out"}), ("part", {"part": "g2"}),
                          ("source", {"verified_source_sha256": {"di.wav": "changed"}}),
                          ("none", {"verified_source_sha256": {}}),
                          ("amps", {"removed_own_amp_tracks": ["other.wav"]}),
                          ("dis", {"excluded_guitar_dis": []})):
        other = tmp_path / name
        other.mkdir()
        catalog, _ = _cached(other, changes)
        with pytest.raises(SystemExit):
            R.crops_for(catalog, other, other / "crops", "a", "one", "g1")

    # The catalog moving the session to held out, changing the part's roles or
    # declaring another mix makes a development record stale even though its own
    # fields are unchanged.
    for name, edit in (("held", lambda s, part: s.update(split="held_out")),
                       ("role", lambda s, part: part.update(alternate=["tf11.wav"])),
                       ("mix", lambda s, part: s.update(mix_tracks=["amp.wav"],
                                                        vocal_tracks=[]))):
        other = tmp_path / f"catalog-{name}"
        other.mkdir()
        catalog, _ = _cached(other)
        document = json.loads(catalog.read_text())
        edit(document["sessions"][0], document["sessions"][0]["parts"][0])
        catalog.write_text(json.dumps(document))
        with pytest.raises(SystemExit):
            R.crops_for(catalog, other, other / "crops", "a", "one", "g1")


def test_a_cached_crop_of_a_declared_mix_is_reused_while_the_mix_is_unchanged(tmp_path):
    import json

    catalog, _ = _cached(tmp_path, {"included_mix_tracks": ["amp.wav", "vox.wav"],
                                    "vocal_tracks": ["vox.wav"]})
    document = json.loads(catalog.read_text())
    document["sessions"][0].update(mix_tracks=["amp.wav", "vox.wav"],
                                   vocal_tracks=["vox.wav"])
    catalog.write_text(json.dumps(document))
    assert R.crops_for(catalog, tmp_path, tmp_path / "crops", "a", "one", "g1")["part"] == "g1"
    document["sessions"][0]["vocal_tracks"] = []
    catalog.write_text(json.dumps(document))
    with pytest.raises(SystemExit):
        R.crops_for(catalog, tmp_path, tmp_path / "crops", "a", "one", "g1")


def test_a_changed_crop_is_refused(tmp_path):
    catalog, wav = _cached(tmp_path)
    wav.write_bytes(b"edited")
    with pytest.raises(SystemExit):
        R.crops_for(catalog, tmp_path, tmp_path / "crops", "a", "one", "g1")


def test_a_held_out_part_is_never_cut(tmp_path):
    import json

    pytest.importorskip("numpy", reason="needs the analysis extra")
    pytest.importorskip("soundfile", reason="needs the analysis extra")

    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({**CATALOG, "schema": "validation-datasets-2"}))
    with pytest.raises(ValueError, match="held-out"):
        R.crops_for(catalog, tmp_path, tmp_path / "crops", "a", "two", "g1")
    assert not (tmp_path / "crops").exists()


def test_the_catalog_is_not_a_command_line_choice():
    with pytest.raises(SystemExit):
        R.build_parser().parse_args(["--amp", "sw50r", "--signal", "same",
                                     "--catalog", "elsewhere.json"])


def test_a_library_probe_is_real_guitar_from_other_bands_at_one_loudness():
    np = pytest.importorskip("numpy", reason="needs the analysis extra")
    pytest.importorskip("pyloudnorm", reason="needs the analysis extra")
    from analysis import io

    rate = 48000
    rng = np.random.default_rng(0)
    parts = [("s", f"song{i}", "g") for i in range(5)] + [("t", f"song{i}", "g")
                                                           for i in range(5, 9)]
    groups = ["A", "A", "B", "B", "C", "D", "D", "E", "F"]
    dis = [rng.standard_normal(3 * rate) * (0.01 * (i + 1)) for i in range(9)]
    probe, sources = R.library_probe(0, parts, dis, groups)
    assert len(probe) == 4 * int(1.5 * rate)
    # Never the part's own band, one clip per band, alternating the other source
    # and the part's own, each in catalog order after it.
    assert sources == ["t/song5/g", "s/song2/g", "t/song7/g", "s/song4/g"]
    clip = probe[:int(1.5 * rate)]
    assert abs(clip[0]) < 1e-9 and abs(clip[-1]) < 1e-6   # faded
    middle = probe[int(0.2 * rate):int(1.3 * rate)].astype(np.float64)
    assert io.loudness_lufs(io.from_samples(middle, rate)) == pytest.approx(-22.9, abs=0.6)
    with pytest.raises(SystemExit):
        R.library_probe(0, parts[:3], dis[:3], groups[:3])


def test_a_session_without_a_group_is_its_own_band():
    catalog = {"sessions": [{"source": "a", "song": "one", "group": "Band"},
                            {"source": "b", "song": "two"}]}
    assert R.part_groups(catalog, [("a", "one", "g"), ("b", "two", "x")]) == ["Band", "b/two"]


def test_no_search_is_a_flag_and_library_a_signal():
    args = R.build_parser().parse_args(["--amp", "x", "--signal", "library", "--no-search"])
    assert args.no_search and args.signal == ["library"]
