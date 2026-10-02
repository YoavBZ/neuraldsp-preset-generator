"""The match-pipeline benchmark's summary: loudness, the guitar check, the level trim
and paired distances, computed from per-part results without the plugin."""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import benchmark_match_pipeline as P  # noqa: E402


def _arm(lu, v3, *, fallback=False, check=None):
    return {"lufs": None if lu is None else -20 + lu, "vs_reference_lu": lu,
            "v3": v3 + .1, "v3_no_level": v3, "v2": v3, "v2_no_level": v3,
            "fallback_to_template": fallback, "guitar_check": check}


def _check(passes=(True, True, True), trim=None):
    return {"candidates": [{"search_rank": i, "passes": p} for i, p in enumerate(passes, 1)],
            "level_trim": {"records": [trim] if trim else []}}


def test_the_summary_pairs_arms_and_reads_the_guitar_check_and_trim():
    trimmed = {"match": 1, "applied": True, "before": -8.0, "after": -18.0, "clamped": False}
    results = [
        {"part": "a/one/g", "template": _arm(1.0, 1.0),
         "no_di": _arm(4.0, 1.5, check=_check(trim=trimmed)), "di": _arm(0.0, .5)},
        {"part": "a/two/g", "template": _arm(-2.0, 1.2),
         "no_di": _arm(2.0, 1.0, check=_check((False, True, True),
                                              {**trimmed, "clamped": True})),
         "di": _arm(.5, .4)},
        {"part": "b/three/g", "error": "RuntimeError: render failed",
         "template": _arm(None, 2.0)},
    ]
    summary = P.summarise(results)
    assert summary["failed"] == ["b/three/g"]
    assert summary["template"]["parts"] == 3 and summary["no_di"]["parts"] == 2
    assert summary["template"]["unmeasurable"] == ["b/three/g"]
    assert summary["no_di"]["within_3_lu"] == 1 and summary["di"]["within_3_lu"] == 2
    assert summary["guitar_check_failed_a_candidate"] == ["a/two/g"]
    trim = summary["level_trim_on_match_1"]
    assert trim["applied"] == 2 and trim["clamped"] == 1
    assert trim["moved_db"]["median"] == -10.0
    # Before the trim, each answer played the trim's move louder: 4 + 10, 2 + 10.
    assert trim["vs_reference_lu_before_trim"]["min"] == 12.0
    pairs = summary["paired_v3_no_level"]
    assert pairs["di_closer_than_no_di"] == {"closer": 2, "of": 2, "median_change": -.633}
    assert pairs["no_di_closer_than_template"]["closer"] == 1


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
    pytest.importorskip("numpy", reason="needs the analysis extra")
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "benchmark_match_pipeline.py"),
                           "--out-dir", str(tmp_path / "elsewhere")],
                          capture_output=True, text=True, cwd=ROOT)
    assert done.returncode != 0
    assert "must be under this checkout's runs/" in done.stderr
    assert not (tmp_path / "elsewhere").exists()


def test_the_defaults_are_the_shipped_sw50r_template_and_both_arms():
    args = P.build_parser().parse_args(["--set", "2"])
    assert (args.template, args.pack, args.amp, args.sets, args.arm) == (
        "samples/SW50R_Atlas_Topology.xml", "morgan", "sw50r", [2], None)
