"""The DI scope (docs/full-controls-plan.md, "C2r and C3r, Amendment 1"): learn/di_scope.py."""
import json

import pytest

from learn import di_scope as D


def test_one_card_per_di_file_from_its_first_unit_n12_before_the_panel():
    n12 = [{"unit": "cap/b", "di": "lib/1", "di_path": "/b", "start_s": 2.0},
           {"unit": "cap/a", "di": "lib/1", "di_path": "/a", "start_s": 1.0},
           {"unit": "cap/c", "di": "lib/2", "di_path": "/c", "start_s": 3.0}]
    panel = [{"unit": "panel/x", "di": "lib/2", "di_path": "/x", "start_s": 9},
             {"unit": "panel/y", "di": "panel/y", "di_path": "/y", "start_s": 4}]
    got = D.card_sources(n12, panel)
    assert got == {"lib/1": {"set": "n12", "unit": "cap/a", "path": "/a", "start": 1.0},
                   "lib/2": {"set": "n12", "unit": "cap/c", "path": "/c", "start": 3.0},
                   "panel/y": {"set": "panel", "unit": "panel/y", "path": "/y", "start": 4.0}}


def test_ids_order_and_build_are_the_published_builders():
    import hashlib
    import random
    dis = ["c", "a", "b"]
    want = sorted(dis)
    random.Random(D.SEED).shuffle(want)
    assert D.card_order(dis) == want
    assert D.card_id("a") == "d" + hashlib.sha256(f"{D.SEED}|a".encode()).hexdigest()[:10]
    ids = [D.card_id(d) for d in want]
    assert D.build_of(ids) == hashlib.sha256(json.dumps(ids).encode()).hexdigest()[:12]


def test_verdicts_keep_a_partial_sitting_partial_and_refuse_what_the_page_never_showed():
    items = [{"id": "d1", "di": "a"}, {"id": "d2", "di": "b"}, {"id": "d3", "di": "c"}]
    assert D.di_verdicts({"d1": {"v": "keep"}, "d2": {"v": "heavy"}}, items) == {"a": "keep", "b": "heavy"}
    for bad in ({"d9": {"v": "keep"}}, {"d1": {"v": "metal"}}):
        with pytest.raises(SystemExit):
            D.di_verdicts(bad, items)


def test_only_keep_stays_and_training_waits_for_every_answer():
    v = {"build": D.BUILD, "verdicts": {"a": "keep", "b": "heavy", "c": "unsure"}}
    assert D.dropped_of(v) == {"b", "c"}
    assert "3 of 26" in D.complete_refusal(v)
    full = {"build": D.BUILD, "verdicts": {f"x{i}": "keep" for i in range(26)}}
    assert D.complete_refusal(full) is None
    assert "build other" in D.complete_refusal(dict(full, build="other"))


def test_no_verdicts_is_none_not_an_empty_drop(tmp_path, monkeypatch):
    from learn import pipeline_fix as P
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    assert D.verdicts() is None and D.dropped_dis() is None and "missing" in D.complete_refusal()
    (tmp_path / D.DIR).mkdir()
    (tmp_path / D.DIR / "verdicts.json").write_text(json.dumps({"build": D.BUILD, "verdicts": {"a": "heavy"}}))
    assert D.dropped_dis() == {"a"}
    (tmp_path / D.DIR / "verdicts.json").write_text(json.dumps({"build": "other", "verdicts": {}}))
    with pytest.raises(SystemExit):
        D.verdicts()


def test_answers_reads_the_stored_copy_into_verdicts(tmp_path, monkeypatch):
    pytest.importorskip("numpy")                      # CI's light runner has no numpy (bakeoff_render imports it)
    from learn import pipeline_fix as P
    import argparse
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(P, "require", lambda k: {})
    (tmp_path / D.DIR).mkdir()
    (tmp_path / D.DIR / "key.json").write_text(json.dumps({"build": D.BUILD, "items": [
        {"id": "d1", "di": "a"}, {"id": "d2", "di": "b"}]}))
    store = tmp_path / "store.json"
    store.write_text(json.dumps({"data": {"build": D.BUILD, "answers": {"d1": {"v": "keep"}, "d2": {"v": "unsure"}}}}))
    D.cmd_answers(argparse.Namespace(store=str(store)))
    v = json.loads((tmp_path / D.DIR / "verdicts.json").read_text())
    assert v["verdicts"] == {"a": "keep", "b": "unsure"} and v["dropped"] == ["b"] and v["complete"]
    store.write_text(json.dumps({"build": "other", "answers": {}}))
    with pytest.raises(SystemExit):
        D.cmd_answers(argparse.Namespace(store=str(store)))


def test_the_page_names_no_source_and_carries_its_own_verdicts():
    page = D.page_html(["d1", "d2"], {"d1": "", "d2": ""}, "b1")
    assert "<title>Guitar DI Check</title>" in page and "2 dry guitar recordings (DIs)" in page
    assert "Drop: too low or too metal" in page and D.leaks(page) == []
    from learn import scope_page as SP
    assert SP.VERDICTS[1][1] == "Too heavy or distorted"                         # the scope page's own, restored
    assert D.leaks(page.replace("</main>", "ElecGtr</main>")) == ["ElecGtr"]


def test_the_cards_reproduce_the_published_build():
    from learn import pipeline_fix as P
    key = P.out_dir() / D.DIR / "key.json"
    if not key.exists():
        pytest.skip("no stored data")
    k = json.loads(key.read_text())
    cards, ids, build = D.page_cards()
    assert build == k["build"] == D.BUILD and ids == [it["id"] for it in k["items"]] and len(ids) == D.N_CARDS
    assert [(c["di"], c["set"], c["unit"], c["start"]) for c in cards] == [
        (it["di"], it["set"], it["unit"], it["start"]) for it in k["items"]]
