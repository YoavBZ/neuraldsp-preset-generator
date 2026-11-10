"""L1c, the third capture batch (`docs/full-controls-plan.md`, ledger `phase_l1c`): its pure parts."""
import json

import pytest

from learn import capture_labels as L
from learn import capture_units as U


def players():
    return {"p1": [f"a{j}" for j in range(20)], "p2": [f"b{j}" for j in range(20)]}


def test_walk_takes_the_tagged_class_first_and_crunch_first_by_default():
    cls = lambda c, it: "crunch" if int(it[1:]) % 2 else "clean"     # every capture has both classes among its tries
    caps = ["c-clean", "c-crunch", "c-none"]
    amp_of = {c: "pr12" for c in caps}
    taken, _ = U.walk(caps, players(), cls, 5, amp_of=amp_of, prefer={"c-clean": "clean", "c-crunch": "crunch"})
    assert cls("c-clean", taken["c-clean"]["pr12"]) == "clean"
    assert cls("c-crunch", taken["c-crunch"]["pr12"]) == "crunch"
    assert cls("c-none", taken["c-none"]["pr12"]) == "crunch"         # no tag: L1a's and L1b's crunch first
    only_crunch = lambda c, it: "crunch"
    t2, _ = U.walk(["x"], players(), only_crunch, 5, amp_of={"x": "ac20"}, prefer={"x": "clean"})
    assert "ac20" in t2["x"]                                             # no clean candidate: the other class plays
    heavy = lambda c, it: "high-gain"
    t3, _ = U.walk(["y"], players(), heavy, 5, amp_of={"y": "ac20"}, prefer={"y": "clean"})
    assert t3["y"] == {}                                                 # high gain still plays nothing
    with pytest.raises(SystemExit):
        U.walk(["z"], players(), cls, 5, prefer={"z": "heavy"})


def test_walk_without_prefer_is_unchanged():
    cls = lambda c, it: "crunch" if (len(c) + int(it[1:])) % 3 == 0 else "clean"
    caps = [f"cap{j}" for j in range(12)]
    assert U.walk(caps, players(), cls, 9) == U.walk(caps, players(), cls, 9, prefer=None)


def test_earlier_overlap_by_sha_or_model_id():
    rows = [{"file_name": "a.nam", "sha256": "s1", "model_id": "1"}, {"file_name": "b.nam", "sha256": "s2", "model_id": "2"},
            {"file_name": "c.nam", "sha256": "s3", "model_id": ""}]
    earlier = [{"sha256": "s1", "model_id": "9"}, {"sha256": "zz", "model_id": "2"}, {"sha256": "", "model_id": ""}]
    assert L.earlier_overlap(rows, earlier) == ["a.nam", "b.nam"]
    assert L.earlier_overlap(rows, []) == []


def test_l1c_sections_keep_t0_verified_unplayed_dis_outside_w():
    secs = [{"di": "x/1.wav"}, {"di": "x/2.wav"}, {"di": "x/3.wav"}, {"di": "w/4.wav"}, {"di": "x/5.wav"}]
    verdict = {"x/1.wav": "verified", "x/2.wav": "excluded", "w/4.wav": "verified", "x/5.wav": "verified"}.get   # x/3: none
    assert L.l1c_sections(secs, verdict, frozenset({"w/4.wav"})) == [{"di": "x/1.wav"}, {"di": "x/5.wav"}]
    assert L.l1c_sections(secs, verdict, frozenset({"w/4.wav"}), frozenset({"x/5.wav"})) == [{"di": "x/1.wav"}]


def test_played_dis_take_every_ranked_card_c1a_s_by_its_part():
    n12 = [{"unit": "u1", "di": "a.wav"}, {"unit": "u2", "di": "b.wav"}]
    c1a = [{"unit": "u3", "prt": {"di": "c.wav"}}, {"unit": "u4", "prt": {"di": "a.wav"}}]     # C1a's ear plan keeps the part
    assert L.played_dis(n12, c1a) == frozenset({"a.wav", "b.wav", "c.wav"})
    with pytest.raises(SystemExit, match="u5"):
        L.played_dis([{"unit": "u5"}])


def test_batch3_runs_only_its_own_commands():
    for cmd in ("items", "stage-check", "night-check", "scope"):
        with pytest.raises(SystemExit, match="not L1c's"):
            L.main(["--batch", "3", cmd])
    with pytest.raises(SystemExit, match="not L1c's"):
        L.main(["--batch", "3", "search", "--before-ear"])


def test_the_ear_page_names_too_distorted_apart_from_odd():
    vs = dict(L.VERDICTS3)
    assert {"amp", "distorted", "odd", "di_bad", "unsure"} == set(vs)
    assert L.VERDICTS3[0][0] == "amp"
    assert "distorted" in L.EAR_SPEC3["ask"] and L.EAR_SPEC3["ask"] != L.EAR_SPEC["ask"]
    assert L.BATCH3["minimum"] is False and L.BATCH3["night"] is None and L.BATCH3["dir"] == "captures3"


def test_gate_read_tallies_the_declared_tables():
    amp = lambda j: "pr12" if j % 2 else "ac20"
    units = [{"unit": f"cap/u{j}#{amp(j)}", "capture": f"u{j}", "label": "clean" if j < 3 else "crunch",
              "cls": "clean" if j < 2 else "crunch", "amp": amp(j), "creator": f"m{j % 2}", "player": "Band A",
              "di": f"d{j % 3}.wav", "di_item": f"s{j % 2}"} for j in range(5)]
    ear = {"u0": {"verdict": "amp"}, "u1": {"verdict": "amp"}, "u2": {"verdict": "distorted"}, "u3": {"verdict": "odd"}}
    r = L.gate_read(units, ear, {"cap/u0#ac20", "cap/u1#pr12"})
    assert (r["units"], r["heard"], r["passed"], r["trusted"]) == (5, 4, 2, 2)
    assert r["distorted_vs_odd"] == {"distorted": 1, "odd": 1}
    assert r["by_tag"]["clean"] == {"amp": 2, "distorted": 1} and r["by_tag"]["crunch"] == {"odd": 1, "unheard": 1}
    assert r["trusted_by"]["amp_class"] == {"('ac20', 'clean')": 1, "('pr12', 'clean')": 1}
    assert r["yield"]["passed_share"] == 0.5
    assert r["yield"]["batch2_passed_share (the ear page alone, like for like)"] == pytest.approx(49 / 147)
    assert r["units_per_section"] == {"s0": 3, "s1": 2} and r["bad_di_on_t0_verified"] == []
    assert r["units_per_di_file"] == {"d0.wav": 2, "d1.wav": 2, "d2.wav": 1}


def test_read_export_takes_the_stored_copy(tmp_path, monkeypatch):
    pytest.importorskip("numpy")
    monkeypatch.setattr(L, "root", lambda: tmp_path)
    (tmp_path / "ear-key.json").write_text(json.dumps({"build": "b1", "items": [{"id": "cap-1", "capture": "u1"}]}))
    doc = {"id": "b1-part1", "data": {"page": "capture-ear-3", "part": 1, "build": "b1",
                                      "answers": [{"id": "cap-1", "verdict": "distorted", "note": "fuzzy"}]}}
    f = tmp_path / "stored.json"
    f.write_text(json.dumps(doc))
    _, _, got = L.read_export([f], "ear-key.json", "capture-ear-3")
    assert got == {"cap-1": {"verdict": "distorted", "note": "fuzzy"}}
    bad = tmp_path / "other.json"
    bad.write_text(json.dumps(dict(doc["data"], build="b2")))
    with pytest.raises(SystemExit):
        L.read_export([bad], "ear-key.json", "capture-ear-3")


def test_read_export_refuses_answers_that_differ_and_the_store_wins(tmp_path, monkeypatch):
    pytest.importorskip("numpy")
    monkeypatch.setattr(L, "root", lambda: tmp_path)
    (tmp_path / "ear-key.json").write_text(json.dumps({"build": "b1", "items": [{"id": "c1"}, {"id": "c2"}, {"id": "c3"}]}))

    def write(name, answers):
        f = tmp_path / name
        f.write_text(json.dumps({"page": "capture-ear-3", "part": 1, "build": "b1",
                                 "answers": [{"id": i, "verdict": v, "note": ""} for i, v in answers.items()]}))
        return f

    store = write("store.json", {"c1": "amp", "c2": "odd", "c3": "distorted"})
    early = write("early.json", {"c1": "amp", "c2": "odd"})                 # an earlier, partial Export: agrees
    late = write("late.json", {"c1": "amp", "c2": "amp"})                   # a later change on c2: refused, named
    _, _, got = L.read_export([early], "ear-key.json", "capture-ear-3", store)
    assert {i: a["verdict"] for i, a in got.items()} == {"c1": "amp", "c2": "odd", "c3": "distorted"}
    with pytest.raises(SystemExit, match="c2"):
        L.read_export([late], "ear-key.json", "capture-ear-3", store)
    with pytest.raises(SystemExit, match="c2"):
        L.read_export([early, late], "ear-key.json", "capture-ear-3")     # no store: the order cannot decide
    short = write("short.json", {"c1": "amp"})
    extra = write("extra.json", {"c3": "amp"})
    with pytest.raises(SystemExit, match="c3"):
        L.read_export([extra], "ear-key.json", "capture-ear-3", short)      # an id the stored copy lacks: refused
    _, _, both = L.read_export([short, extra], "ear-key.json", "capture-ear-3")
    assert set(both) == {"c1", "c3"}


def test_answers_needs_a_file():
    with pytest.raises(SystemExit, match="stored copy"):
        L.main(["--batch", "3", "answers"])


def test_artifact_gate_keeps_answers_in_the_store_and_drops_the_file_save():
    pytest.importorskip("numpy")
    from learn import build_ear_page as BEP
    from learn import cc_drive_page as CDP
    from learn import goat_ear_page as G

    items = [{"id": "cap-1"}, {"id": "cap-2"}]
    clips = {f"{i['id']}-{k}": "AAAA" for i in items for k in (1, 2)}
    page = G.page_html(items, clips, "b1", 1, 1, 1, dict(L.EAR_SPEC3, page="capture-ear-3", verdicts=L.VERDICTS3))
    js = BEP.JS_HEAD + CDP.PLAYER_JS.replace("XFADE_S", repr(CDP.XFADE_S)) + BEP.JS_ANSWERS
    out = L.artifact_gate(page, js)
    assert "<body>" not in out and "<!doctype" not in out.lower()
    assert "Save file" not in out and 'if (false) document.getElementById("save")' in out
    assert "let save = () => {" in out and "const save = () => {" not in out
    assert 'db.doc("answers/" + DATA.build + "-part" + DATA.part)' in out
    assert L.ARTIFACT_INTRO[1] in out and L.ARTIFACT_INTRO[0] not in out
    assert 'data-v="distorted"' in out and out.startswith("<title>Capture ear 1</title>")
    assert 'id="sync"' in out and 'el.textContent = "Saved."' in out
    assert out.count("Not saving here") == 4            # no store, no viewer, a failed read, a failed write
