"""The recorded DI-to-amp-track lags: one per set-2 development part, never a held-out
one, each with its stability, read back by `benchmark_recordings.lag_samples`."""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import benchmark_recordings as B  # noqa: E402


def _slug(session, part):
    return "-".join(x.replace("/", "_").replace(" ", "_")
                    for x in (session["source"], session["song"], part["part"]))


def test_every_set_two_development_part_has_one_lag_and_no_held_out_part_does():
    lags = json.loads(B.LAGS.read_text())
    assert lags["schema"] == "validation-lags-1" and lags["latency_samples"] == 52
    catalog = json.loads(B.CATALOG.read_text())
    split = {_slug(s, p): (p.get("split") or s.get("split"), s.get("set"))
             for s in catalog["sessions"] for p in s["parts"]}
    recorded = set(lags["parts"])
    assert all(split[p][0] == "development" for p in recorded)
    assert {p for p, (sp, st) in split.items() if sp == "development" and st == 2} >= recorded
    assert len(recorded) == 43


def test_each_lag_carries_its_stability_and_ambiguity_follows_the_spread():
    for part, row in json.loads(B.LAGS.read_text())["parts"].items():
        assert isinstance(row["lag_samples"], int), part
        assert len(row["subset_lags"]) == 5 and row["renders"] >= 9
        spread = row["subset_spread_ms"]
        assert row["ambiguous"] == (spread is None or spread > 0.5), part


def test_lag_samples_reads_the_record_and_knows_what_it_lacks(tmp_path):
    some = next(iter(json.loads(B.LAGS.read_text())["parts"]))
    assert B.lag_samples(some) == json.loads(B.LAGS.read_text())["parts"][some]["lag_samples"]
    assert B.lag_samples("no-such-part") is None
    assert B.lag_samples(some, tmp_path / "missing.json") is None
