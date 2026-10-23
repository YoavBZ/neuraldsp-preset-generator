"""The trusted-data ear page: part plan, blindness of the DI part, and answers that verify_tracks decodes."""
import json

import pytest

from learn import build_ear_page as E
from learn import verify_tracks as VT


def _item(kind, family, key, start, **paths):
    return {"id": VT.item_id(kind, key, start), "kind": kind, "family": family, "key": key, "start_s": start,
            "dur_s": 10.0, "paths": paths, "half": "A" if start < 2 else "B"}


QUEUE = [
    _item("di_flagged", "di", "a", 30.0, di="/x/S_Full/02_GtrDI.wav"),
    _item("target", "target", "cambridge-Song_Name-ElecGtr1", 0.5,
          di="/c/cambridge-Song_Name-ElecGtr1/di.wav", target="/c/cambridge-Song_Name-ElecGtr1/reference.wav"),
    _item("di_sample", "di", "b", 5.0, di="/x/S_Full/04_GtrDI.wav"),
    _item("di_flagged", "di", "a", 10.0, di="/x/S_Full/02_GtrDI.wav"),
    _item("di_amp", "di_amp", "c", 15.0, di="/x/S_Full/06_GtrDI.wav", amp="/x/S_Full/05_Gtr.wav"),
]


def test_parts_split_by_question_and_keep_each_file_in_time_order():
    parts = E.plan_parts(QUEUE)
    assert [len(parts[p]) for p in (1, 2, 3)] == [1, 1, 3]
    di = [(i["paths"]["di"], i["start_s"]) for i in parts[3]]
    a = [s for f, s in di if f.endswith("02_GtrDI.wav")]
    assert a == [10.0, 30.0]
    assert sorted(f for f, _ in di) == sorted(i["paths"]["di"] for i in QUEUE if i["family"] == "di")


def test_unknown_family_refused():
    with pytest.raises(SystemExit):
        E.plan_parts(QUEUE + [dict(QUEUE[0], family="new")])


def test_labels_are_the_verdicts_verify_tracks_accepts():
    for fam, labels in E.LABELS.items():
        assert tuple(v for v, _ in labels) == VT.EAR_VERDICTS[fam]


def test_page_hides_why_an_item_is_queued():
    items = E.plan_parts(QUEUE)[3]
    clips = {k: "" for i in items for k, *_ in E.item_clips(i)}
    page = E.page_html(3, items, clips, "b", 3)
    for word in ("di_flagged", "di_sample", "D4", "flag", "sample"):
        assert word not in page


def test_titles():
    assert E.title_of(QUEUE[1]) == "Song Name · ElecGtr1"
    assert E.title_of(QUEUE[0]) == "S · 02_GtrDI"


def test_export_is_read_by_verify_tracks(tmp_path):
    reg = {i["id"]: i for i in QUEUE}
    answers = [{"id": i["id"], "verdict": E.LABELS[i["family"]][0][0]} for i in QUEUE]
    answers.append({"id": QUEUE[0]["id"], "verdict": None})
    p = tmp_path / "e.json"
    p.write_text(json.dumps({"page": VT.EAR_PAGE, "part": 1, "answers": answers}))
    out = VT.ear_answers([str(p)], [], reg)
    assert out["di_pairs"] == {"c": ["amp"]}
    assert out["target_amp"] == {"cambridge-Song_Name-ElecGtr1": ["amp"]}
    assert sorted(out["di_windows"]) == ["a", "b"]


def _real(i, reason="r"):
    return dict(i, reason=reason, verdicts=list(VT.EAR_VERDICTS[i["family"]]), crest_db=9.0)


def test_di_part_keeps_files_contiguous_and_is_deterministic():
    q = [_real(_item("di_flagged", "di", f"k{f}", float(t), di=f"/x/S_Full/{f:02d}_GtrDI.wav"), "D4 flags it")
         for f in range(6) for t in (40, 10, 25)]
    a, b = E.plan_parts(q)[3], E.plan_parts(list(reversed(q)))[3]
    assert [i["id"] for i in a] == [i["id"] for i in b]
    files = [i["paths"]["di"] for i in a]
    runs = [f for k, f in enumerate(files) if k == 0 or files[k - 1] != f]
    assert len(runs) == 6 and runs != sorted(runs)          # contiguous per file, shuffled across files
    assert all([i["start_s"] for i in a if i["paths"]["di"] == f] == [10.0, 25.0, 40.0] for f in runs)


def test_real_fields_never_reach_the_page():
    items = [_real(i, "D4 flags this section (unheard)") for i in E.plan_parts(QUEUE)[3]]
    page = E.page_html(3, items, {k: "" for i in items for k, *_ in E.item_clips(i)}, "b", 3)
    assert "unheard" not in page and "crest" not in page and "9.0" not in page


def test_main_button_plays_di_first_and_small_buttons_map():
    t, p = QUEUE[1], QUEUE[4]
    ht = E.item_html(t, 1, 1)
    assert f'data-seq="{t["id"]}-di,{t["id"]}-target" data-names="the DI|the target track"' in ht
    assert f'data-seq="{t["id"]}-target" data-names="the target track">Target only' in ht
    hp = E.item_html(p, 1, 1)
    assert f'data-seq="{p["id"]}-di,{p["id"]}-amp"' in hp and ">Amp only<" in hp
    assert "class=\"ask\"" not in hp and "class=\"ask\"" in E.item_html(p, 1, 1, ask=True)


def test_subtitles():
    assert E.mmss(202.5) == "3:22.5" and E.mmss(65.0) == "1:05"
    assert E.subtitle_of(dict(QUEUE[1], start_s=4.0, dur_s=6.0, half="B")).startswith("Crop 4.0–10.0 s (covers its second half)")


def test_silent_window_refused(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    pytest.importorskip("soundfile")
    from learn import build_data_review as BDR
    monkeypatch.setattr(BDR, "load", lambda path, a, d: np.zeros(int(d * BDR.SR)))
    with pytest.raises(SystemExit, match="silent window"):
        E.clip_b64("/x.wav", 0.0, 1.0, tmp_path)


def test_extra_part_holds_only_unbuilt_items(monkeypatch, tmp_path):
    built = E.plan_parts(QUEUE[:3])
    (tmp_path / "manifest.json").write_text(json.dumps(
        {"page": VT.EAR_PAGE, "seed": E.SEED, "parts": {str(k): {"items": [i["id"] for i in v]} for k, v in built.items()}}))
    monkeypatch.setattr(E, "load_queue", lambda: (QUEUE, "b2"))
    got = {}
    monkeypatch.setattr(E, "write_part", lambda out, part, items, build, n, title=None: got.update(
        part=part, ids=[i["id"] for i in items]) or {"items": [i["id"] for i in items]})
    E.cmd_extra(type("A", (), {"out": str(tmp_path)})())
    assert got == {"part": 4, "ids": [QUEUE[4]["id"], QUEUE[3]["id"]]}
    assert json.loads((tmp_path / "manifest.json").read_text())["parts"]["4"]["items"] == got["ids"]


def test_queue_never_picks_a_silent_section_and_retires_silent_answers(tmp_path):
    secs = [{"section": "s1", "start_s": 10.0, "D4": {"crest_db": None, "frames": 100}},
            {"section": "s2", "start_s": 20.0, "D4": {"crest_db": 8.0, "frames": 90}}]
    assert VT.busiest_audible(secs)["start_s"] == 20.0
    old = _item("di_only", "di", "k/a.wav", 10.0, di="/x/a.wav")
    reg = {old["id"]: old}
    assert VT.silent_items(reg, {"k/a.wav": {"sections": secs}}) == {old["id"]}
    reg[old["id"]]["retired"] = "silent"
    p = tmp_path / "e.json"
    p.write_text(json.dumps({"page": VT.EAR_PAGE, "answers": [{"id": old["id"], "verdict": "clean"}]}))
    assert VT.ear_answers([str(p)], [], reg)["di_windows"] == {}
