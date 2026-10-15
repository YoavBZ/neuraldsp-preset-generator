"""The development test ledger (`docs/dev-test-ledger.json`) stays well-formed."""

import json
import pathlib

LEDGER = pathlib.Path(__file__).resolve().parents[1] / "docs" / "dev-test-ledger.json"


def test_every_entry_names_its_plan_parts_bands_and_gate():
    doc = json.loads(LEDGER.read_text())
    assert doc["schema"] == "dev-test-ledger-1"
    ids = [t["test_id"] for t in doc["tests"]]
    assert len(ids) == len(set(ids))
    for t in doc["tests"]:
        for k in ("plan", "parts", "bands", "gate"):
            assert t.get(k), (t["test_id"], k)
        assert (LEDGER.parent.parent / t["plan"]).exists(), t["plan"]


def test_cprime_folds_verdict_is_one_sided():
    from learn.cprime_folds import verdict

    seeds = [0.1360, 0.1326, 0.1343]
    assert verdict(0.20, seeds) and verdict(0.1130, seeds)
    assert not verdict(0.1120, seeds)


def test_label_table_parts_are_the_declared_59():
    doc = json.loads((LEDGER.parent / "label-table-parts.json").read_text())
    assert doc["classed"] == 76 and doc["clean_or_crunch"] == 59 == len(doc["parts"])
    assert all(v["gain_class"] in ("clean", "crunch") for v in doc["parts"].values())
