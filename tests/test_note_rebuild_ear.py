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
    ok["c3"]["B"] = {"cant": True}
    r = NE.ear_verdict(items, ok)
    assert r["verdict"] == "ok" and r["cant_judge"] == [{"n": 3, "version": "nr-level"}]
    assert r["notes"] == [{"n": 2, "item": "item_10", "cls": "crunch", "note": "B a bit thin"}]
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
    assert art.startswith(f"<title>{NE.TITLE}</title>")
    assert '"answers/" + DATA.build' in art and 'id="save"' not in art.split("<script")[0]
    assert "<body>" not in art
