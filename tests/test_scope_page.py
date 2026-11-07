"""The keep-or-drop page's pure parts (`learn/scope_page.py`)."""
import argparse
import json

import pytest

from learn import scope_page as S


def test_ask_takes_the_unmarked_at_or_over_the_line():
    nl = {"a": -2.91, "b": -3.0, "c": 4.0, "d": 1.0}
    assert S.ask(nl, {"c": "keep"}) == ["a", "d"]


def test_ask_refuses_a_recording_with_no_measure():
    with pytest.raises(SystemExit):
        S.ask({"a": None}, {})


def test_merge_marks_lets_out_win_in_either_order():
    rows = [("p", "1", "a", False), ("q", "2", "a", True), ("q", "3", "b", True), ("p", "4", "b", False)]
    assert S.merge_marks(rows) == {"a": "out", "b": "out"}


def test_merge_marks_counts_the_slip_as_keep():
    assert S.merge_marks([(*S.SLIP, "a", True)]) == {"a": "keep"}
    assert S.merge_marks([("ear-eat-2", S.SLIP[1], "a", True)]) == {"a": "out"}


def test_order_is_seeded_and_keeps_every_unit():
    units = [f"u{j}" for j in range(30)]
    assert S.order(units) == S.order(units) != units
    assert sorted(S.order(units)) == sorted(units)


ITEMS = [{"id": "r1", "unit": "a"}, {"id": "r2", "unit": "b"}]


def test_unit_verdicts_maps_ids_to_verdicts():
    got = S.unit_verdicts({"r1": {"v": "keep", "t": 1}, "r2": {"v": "heavy", "t": 2}}, ITEMS)
    assert got == {"a": "keep", "b": "heavy"}


@pytest.mark.parametrize("bad", [{"r1": {"v": "keep"}, "r3": {"v": "keep"}}, {"r1": {"v": "keep"}, "r2": {"v": "maybe"}},
                                 {"r1": {"v": "keep"}}])
def test_unit_verdicts_refuses_a_partial_sitting_and_what_the_page_never_showed(bad):
    with pytest.raises(SystemExit):
        S.unit_verdicts(bad, ITEMS)


def test_out_units_is_everything_not_kept_and_every_earlier_out():
    got = S.out_units({"a": "keep", "b": "heavy", "c": "unsure"}, {"d": "out", "e": "keep", "a": "keep"})
    assert got == ["b", "c", "d"]


def test_the_page_carries_ids_and_no_names():
    units = ["set5/BKS_Bulldozer_Full/x.wav@1.0#y", "goat/item_1@2.0#amp_1"]
    ids = [S.item_id(u) for u in units]
    page = S.page_html(ids, {i: "AAAA" for i in ids}, "b1")
    assert page.startswith("<title>Keep Or Drop</title>")
    assert S.leaks(page, units) == []
    assert all(t in page for _, t, _ in S.VERDICTS)


def test_leaks_finds_a_name_outside_the_clips_and_none_inside_them():
    page = S.page_html(["r1"], {"r1": "Reamp"}, "b1")
    assert S.leaks(page, ["u1"]) == []
    assert S.leaks(page.replace("<h1>", "<h1>u1 "), ["u1"]) == ["u1"]
    assert S.leaks(page.replace("<h1>", "<h1>goat "), []) == ["goat"]


def test_stored_marks_reads_each_page_and_skips_a_card_with_no_answer(tmp_path, monkeypatch):
    from learn import pipeline_fix as P

    monkeypatch.setattr(P, "out_dir", lambda: tmp_path)
    (tmp_path / P.GOAT_DIR).mkdir()
    (tmp_path / "eat" / "ear").mkdir(parents=True)
    (tmp_path / "eat" / "ear2").mkdir()
    (tmp_path / P.GOAT_DIR / "heavy.json").write_text(json.dumps({"verdicts": {"h1": {"verdict": "keep"}, "h2": {"verdict": "heavy"}, "h3": {"verdict": "unsure"}}}))
    (tmp_path / "eat" / "ear" / "key.json").write_text(json.dumps({"items": [{"id": "i1", "unit": "e1"}, {"id": "i2", "unit": "e2"}, {"id": "i3", "unit": "e3"}]}))
    (tmp_path / "eat" / "ear" / "answers.txt").write_text("Answers\n" + json.dumps({"answers": {"i1": {"scope": True}, "i2": {"scope": True}}}))
    (tmp_path / "eat" / "ear2" / "key.json").write_text(json.dumps({"items": [{"id": "i1", "unit": "f1"}, {"id": "i2", "unit": "f2"}]}))
    (tmp_path / "eat" / "ear2" / "answers.json").write_text(json.dumps({"data": {"answers": {"i1": {}, "i2": {"scope": True}}}}))
    assert S.stored_marks() == {"h1": "keep", "h2": "out", "h3": "out", "e1": "out", "e2": "keep", "f1": "keep", "f2": "out"}


def test_answers_refuses_another_build(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "scope_dir", lambda: tmp_path)
    (tmp_path / "key.json").write_text(json.dumps({"build": "b1", "items": ITEMS}))
    f = tmp_path / "stored.json"
    f.write_text(json.dumps({"build": "b2", "answers": {}}))
    with pytest.raises(SystemExit):
        S.cmd_answers(argparse.Namespace(stored=str(f)))
