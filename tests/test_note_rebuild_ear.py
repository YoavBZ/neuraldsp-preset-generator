"""The note rebuild's ear check page: its cards, its answers' read, and the player it borrows (pure)."""

import json

import pytest

from learn import note_rebuild_ear as NE


def index(drop=None):
    clips = []
    for item in ("item_9", "item_10"):
        for cls in ("crunch", "clean"):
            for dry in ("true", "nr-plain", "nr-level"):
                if (item, cls, dry) != drop:
                    clips.append({"item": item, "cls": cls, "dry": dry, "file": f"{item}-{dry}-{cls}.wav",
                                  "sha256": f"{item}{dry}{cls}"})
    return {"clips": clips, "all_ok": True}


def test_page_items_order_and_refusal():
    items = NE.page_items(index())
    assert [(it["id"], it["item"], it["cls"]) for it in items] == [
        ("c1", "item_10", "clean"), ("c2", "item_10", "crunch"), ("c3", "item_9", "clean"), ("c4", "item_9", "crunch")]
    assert set(items[0]["clips"]) == {"true", "nr-plain", "nr-level"}
    with pytest.raises(SystemExit):
        NE.page_items(index(drop=("item_9", "clean", "nr-level")))


def test_build_id_stable_and_clip_bound():
    a = NE.page_items(index())
    assert NE.build_id(a) == NE.build_id(NE.page_items(index()))
    b = NE.page_items(index())
    b[0]["clips"]["true"]["sha256"] = "other"
    assert NE.build_id(a) != NE.build_id(b)


def test_ear_verdict():
    items = NE.page_items(index())
    ok = {it["id"]: {"A": {"real": True}, "B": {"real": True}} for it in items}
    assert NE.ear_verdict(items, ok)["verdict"] == "ok"
    ok["c2"]["note"] = "B a bit thin"
    r = NE.ear_verdict(items, ok)
    assert r["verdict"] == "ok" and r["cant_judge"] == []
    assert r["notes"] == [{"n": 2, "item": "item_10", "cls": "crunch", "note": "B a bit thin"}]
    ok["c3"]["B"] = {"cant": True}                          # one can't-judge beside real answers: not ok
    r = NE.ear_verdict(items, ok)
    assert r["verdict"] == "undecided" and r["cant_judge"] == [{"n": 3, "version": "nr-level"}]
    cant = {it["id"]: {"A": {"cant": True}, "B": {"cant": True}} for it in items}
    r = NE.ear_verdict(items, cant)                         # nothing heard as real: never ok
    assert r["verdict"] == "undecided" and len(r["cant_judge"]) == 2 * len(items)
    part = {k: v for k, v in ok.items() if k != "c4"}
    r = NE.ear_verdict(items, part)
    assert r["verdict"] == "incomplete" and len(r["unanswered"]) == 2
    part["c1"]["A"] = {"faults": ["tune", "hiss"]}
    part["c1"]["note"] = "beats on the octave"
    r = NE.ear_verdict(items, part)
    assert r["verdict"] == "fault"
    assert r["faults"] == [{"n": 1, "item": "item_10", "cls": "clean",
                            "heard": [{"version": "nr-plain", "faults": ["hiss", "tune"]}], "note": "beats on the octave"}]


def test_cards_carry_answers_on_each_card():
    items = NE.page_items(index())
    html = NE.cards(items)
    assert html.count('<article class="item"') == 4 and "Recording 4" in html and "4 / 4" in html
    for it in items:
        card = html.split(f'data-id="{it["id"]}"')[1].split("</article>")[0]
        assert card.count('data-a="real"') == 2 and card.count('data-a="cant"') == 2
        assert all(card.count(f'data-f="{f}"') == 2 for f, _ in NE.FAULTS)
        assert 'class="note"' in card and card.count('class="src"') == 3
        assert it["item"] not in card                       # the library unit stays off the page


def test_player_and_artifact_page():
    pytest.importorskip("numpy")
    js = NE.player_js()
    assert 'KEYS = ["ref", "A", "B"]' in js and "note-rebuild-ear:" in js
    assert "function paint()" in js and js.count("function paint()") == 1 and "function exportText()" in js
    assert 'document.getElementById("export")' in js
    items = NE.page_items(index())
    clips = {f"{it['id']}-{k}": "QUFB" for it in items for k in ("ref", "A", "B")}
    page, css, js = NE.page_html(items, clips, "b123")
    assert json.loads(page.split('<script id="data" type="application/json">')[1].split("</script>")[0])["build"] == "b123"
    art = NE.artifact_page(page, css, js)
    assert f"<title>{NE.TITLE}</title>" in page and "ear-vreal-answers" not in js
    assert art.startswith(f"<title>{NE.TITLE}</title>")
    assert '"answers/" + DATA.build' in art and 'id="save"' not in art.split("<script")[0]
    assert "<body>" not in art


# --- the redo's page (`phase_nr_1_redo_ear`) ---------------------------------------------------------------------------------

def redo_index(drop_control=False):
    cards = []
    for n in range(1, 14):
        control = n == 7 and not drop_control
        cards.append({"id": f"c{n}", "n": n, "item": f"item_{n % 8}", "cls": "crunch" if n in (2, 5, 9, 11) else "clean",
                      "control": control, "kind": None,
                      "clips": {"ref": {"file": f"c{n}-ref.wav", "sha256": f"r{n}"},
                                "reb": {"file": f"c{n}-reb.wav", "sha256": f"b{n}"}}})
    return {"cards": list(reversed(cards))}


def test_redo_items_order_and_refusals():
    items = NE.redo_items(redo_index())
    assert [it["n"] for it in items] == list(range(1, 14)) and sum(it["control"] for it in items) == 1
    with pytest.raises(SystemExit):
        NE.redo_items(redo_index(drop_control=True))
    bad = redo_index()
    bad["cards"][0]["clips"].pop("reb")
    with pytest.raises(SystemExit):
        NE.redo_items(bad)
    assert NE.redo_build_id(items) == NE.redo_build_id(NE.redo_items(redo_index()))


def _all_same(items):
    return {it["id"]: {"same": True} for it in items}


def test_redo_verdict_every_reading():
    items = NE.redo_items(redo_index())
    real = [it for it in items if not it["control"]]
    ctl = next(it for it in items if it["control"])
    assert NE.redo_verdict(items, _all_same(items))["verdict"] == "ok"
    a = _all_same(items)
    a[real[0]["id"]] = {"faults": ["missing"]}
    assert NE.redo_verdict(items, a)["verdict"] == "fault-content"
    a = _all_same(items)
    for it in real[:3]:
        a[it["id"]] = {"faults": ["hiss"]}
    assert NE.redo_verdict(items, a)["verdict"] == "fault-signal"
    a[real[3]["id"]] = {"faults": ["chords", "tune"]}                       # a content fault comes first
    assert NE.redo_verdict(items, a)["verdict"] == "fault-content"
    for k in (1, 2):
        a = _all_same(items)
        for it in real[:k]:
            a[it["id"]] = {"faults": ["clicks"]}
        assert NE.redo_verdict(items, a)["verdict"] == "ask"
    a = _all_same(items)
    a[real[4]["id"]] = {"cant": True}
    assert NE.redo_verdict(items, a)["verdict"] == "ask"
    a = _all_same(items)
    a[ctl["id"]] = {"faults": ["short"]}                                    # any fault on the control: to the user
    got = NE.redo_verdict(items, a)
    assert got["verdict"] == "ask" and got["control"]["faults"] == ["short"]
    a = _all_same(items)
    a[ctl["id"]] = {"cant": True}
    assert NE.redo_verdict(items, a)["verdict"] == "ask"
    a = _all_same(items)
    del a[real[5]["id"]]
    assert NE.redo_verdict(items, a)["verdict"] == "incomplete"
    del a[ctl["id"]]
    a[real[5]["id"]] = {"same": True}
    assert NE.redo_verdict(items, a)["verdict"] == "incomplete"            # the control unanswered too
    a = _all_same(items)
    a[real[6]["id"]] = {"same": True, "note": "a little bright"}
    got = NE.redo_verdict(items, a)
    assert got["verdict"] == "ok" and got["notes"][0]["note"] == "a little bright"
    assert set(NE.REDO_VERDICTS) == {"ok", "fault-content", "fault-signal", "ask", "incomplete"}


def test_redo_cards_carry_every_answer_on_each_card():
    items = NE.redo_items(redo_index())
    html = NE.redo_cards(items)
    assert html.count('<article class="item"') == 13 and "Recording 13" in html and "13 / 13" in html
    for it in items:
        card = html.split(f'data-id="{it["id"]}"')[1].split("</article>")[0]
        assert card.count('data-a="same"') == 1 and card.count('data-a="cant"') == 1
        assert all(card.count(f'data-f="{f}"') == 1 for f, _ in NE.CONTENT_FAULTS + NE.SIGNAL_FAULTS)
        assert "Same notes and timing" in card and "the guitar's own sound may differ" in card
        assert card.count('class="src"') == 2 and 'class="note"' in card
        assert it["item"] not in card and "control" not in card            # the item and the control stay hidden
    assert {f for f, _ in NE.CONTENT_FAULTS} == {"missing", "chords", "short", "extra"}


def test_redo_page_folder_is_new():
    assert NE.redo_page_dir().name == "note-rebuild-ear-page-2" and NE.page_dir().name == "note-rebuild-ear-page"
    assert NE.REDO_PHASE == "phase_nr_1_redo_ear" and NE.PHASE == "phase_nr_1_ear"


def test_the_old_page_is_never_overwritten(monkeypatch, tmp_path):
    pytest.importorskip("numpy")
    (tmp_path / "key.json").write_text("{}")
    monkeypatch.setattr(NE, "page_dir", lambda: tmp_path)
    with pytest.raises(SystemExit, match="never overwritten"):
        NE.cmd_page(None)


def test_redo_page_refuses_to_overwrite(monkeypatch, tmp_path):
    pytest.importorskip("numpy")
    (tmp_path / "artifact.html").write_text("")
    monkeypatch.setattr(NE, "redo_page_dir", lambda: tmp_path)
    with pytest.raises(SystemExit, match="never overwritten"):
        NE.cmd_redo_page(None)


def test_redo_player_and_artifact_page():
    pytest.importorskip("numpy")
    js = NE.redo_player_js()
    assert 'KEYS = ["ref", "B"]' in js and "note-rebuild-ear-2:" in js and js.count("function paint()") == 1
    assert "ear-vreal-answers" not in js and "note-rebuild-ear-2-answers-" in js
    items = NE.redo_items(redo_index())
    clips = {f"{it['id']}-{k}": "QUFB" for it in items for k in ("ref", "B")}
    page, css, js = NE.redo_page_html(items, clips, "b9")
    assert f"<title>{NE.REDO_TITLE}</title>" in page
    data = json.loads(page.split('<script id="data" type="application/json">')[1].split("</script>")[0])
    assert data["build"] == "b9" and all(set(x) == {"id", "n"} for x in data["items"])
    art = NE.redo_artifact_page(page, css, js)
    assert art.startswith(f"<title>{NE.REDO_TITLE}</title>") and '"answers/" + DATA.build' in art
