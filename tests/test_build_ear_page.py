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
