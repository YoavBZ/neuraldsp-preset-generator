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
