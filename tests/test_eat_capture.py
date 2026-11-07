"""`learn/eat_capture.py`'s pure parts."""
import pytest

pytest.importorskip("numpy")
pytest.importorskip("torch")

import argparse

from learn import capture_labels as CL
from learn import eat_build as EB
from learn import eat_capture as C
from learn import eat_embed as EE
from learn import pipeline_fix as P


def test_only_the_search_half_leaves():
    asks = {"A": {"select": "a"}, "B": {"select": "b"}}
    assert C.search_half(asks, "B") == {"B": {"select": "b"}}


def test_a_unit_with_no_search_half_stops():
    with pytest.raises(SystemExit):
        C.search_half({"A": {}, "B": {}}, None)


def test_captures2_reads_the_batch_loader_on_variant_0(monkeypatch):
    monkeypatch.setattr(CL, "BATCH", CL.BATCH)
    monkeypatch.setattr(CL, "trusted_units", lambda: ([{"unit": "cap/b#ac20"}, {"unit": "cap/a#pr12"}], {}))
    got = EE.keys_of("captures2")
    assert CL.BATCH is CL.BATCH2 and [k for k, _ in got] == [("cap/a#pr12", 0), ("cap/b#ac20", 0)]


def test_batch_2_builds_variant_0_and_checks_every_input(monkeypatch):
    seen = {}

    def build(args):
        seen.update(batch=args.capture_batch, variants=P.DFIX_K, every=EB.PARITY_EVERY)

    keep = P.DFIX_K
    monkeypatch.setattr(EB, "PARITY_EVERY", EB.PARITY_EVERY)
    monkeypatch.setattr(P, "cmd_build_dfix_real", build)
    monkeypatch.setattr(EB, "run", lambda cmd, *_q, **kw: (cmd(), seen.update(kind=kw["kind"])))
    EB.cmd_real(argparse.Namespace(shard=(0, 1), reads_only=False, captures=True, capture_batch=2))
    assert seen == {"batch": 2, "variants": 1, "every": 1, "kind": "captures2"} and P.DFIX_K == keep
