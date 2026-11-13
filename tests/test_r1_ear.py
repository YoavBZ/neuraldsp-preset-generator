from learn import r1_ear as R


def h(r, m, d):
    return {"R": {"rank": r}, "M": {"rank": m}, "D": {"rank": d}}


def test_card_score_and_song_tally():
    assert R.card_score(h(2, 1, 3)) == 1 and R.card_score(h(1, 2, 2)) == -1 and R.card_score(h(1, 1, 2)) == 0
    assert R.song_tally({"a": [1, 0], "b": [1, -1], "c": [-1, -1], "d": []}) == {"a": "ahead", "b": "level", "c": "behind"}


def test_rule_is_declared():
    t = {f"s{i}": v for i, v in enumerate(["ahead"] * 5 + ["level", "behind"])}
    assert R.rule(t) == "the model ahead"
    t = {f"s{i}": v for i, v in enumerate(["ahead"] * 5 + ["behind", "behind"])}
    assert R.rule(t) == "level"
    t = {f"s{i}": v for i, v in enumerate(["behind"] * 6 + ["ahead"])}
    assert R.rule(t) == "research ahead"
    assert R.rule(t, page_failed=True) == "not read"


def test_delay_rule():
    assert R.delay_rule({}) == "undecided (none switched on)"
    assert R.delay_rule({"a": [0, 1], "b": [0, 0]}) == "stays the candidate"
    assert R.delay_rule({"a": [-1, 0], "b": [-1, -1], "c": [1, 0]}) == "off"
    assert R.delay_rule({"a": [-1, 0], "b": [1, 0]}) == "undecided"


def test_same_preset():
    assert R.same_preset((1, {("delay", "delayActive"): "false"}), (1, {("delay", "delayActive"): "false"}))
    assert not R.same_preset((1, {("delay", "delayActive"): "false"}), (1, {("delay", "delayActive"): "true"}))
    assert not R.same_preset((1, {}), (2, {}))


def test_ear_read_unblinds_and_tallies():
    items, got = [], {}
    for n, (song, on) in enumerate([("a", True), ("a", True), ("b", False), ("b", False)], 1):
        it = {"id": f"i{n}", "n": n, "song": song, "di": n % 2, "cls": "clean", "reader_on": on, "repeat_of": None,
              "letters": {"A": "R", "B": "M", "C": "D"}}
        items.append(it)
        got[it["id"]] = {"rank": {"A": 2, "B": 1, "C": 1 if on else 1}}
    rep = R.ear_read(items, got)
    assert rep["songs"] == {"a": "ahead", "b": "ahead"}
    assert rep["delay"]["on_songs"] == ["a"] and rep["delay"]["rule"] == "stays the candidate"
    assert all(c["tied"] for c in rep["delay"]["identical_check"])
    assert rep["page_failed"]                     # 4 of 14 first hearings


def test_page_parts_build():
    js = R.player_js()
    assert '"mix"' in js and 'g: "ref"' in js and "r1-ear" in js
    html = R.cards([{"id": "i1", "n": 1}])
    assert "Guitar (G)" in html and "Song (S)" in html and "Record" not in html


def test_tail_decision_is_the_declared_rule():
    assert R.tail_decision(2.5, [-70.0] * 10)["pre_s"] == R.PAD_S
    assert R.tail_decision(45.0, [-70.0, -55.0])["pre_s"] == R.PAD_S
    d = R.tail_decision(45.0, [-70.0] * 10)
    assert d["pre_s"] == 0.0 and d["why"] == "neither trigger"


def test_r1_check_runs_on_its_inputs(tmp_path, monkeypatch):
    pytest = __import__("pytest")
    pytest.importorskip("numpy")
    import json as J

    from learn import pipeline_fix as P
    import packs.loader

    song = tmp_path / "song.wav"
    song.write_bytes(b"x")
    J.dump({"songs": {f"s{i}": str(song) for i in range(R.N_SONGS)}}, open(tmp_path / "songs.json", "w"))
    for i in range(R.N_SONGS):
        d = tmp_path / f"s{i}"
        (d / "arms").mkdir(parents=True)
        for f in ("window.npz", "arms/R.xml", "arms/M.xml", "arms/D.xml"):
            (d / f).write_text(f)
        J.dump({"start_s": 1.0}, open(d / "window.json", "w"))
        J.dump({"cls": "clean"}, open(d / "research.json", "w"))
    monkeypatch.setattr(R, "ear_dir", lambda: tmp_path)
    monkeypatch.setattr(P, "require", lambda k: None)
    monkeypatch.setattr(packs.loader, "load_pack", lambda n: None)
    monkeypatch.setattr(R, "parse_preset", lambda p, pack: (0, {("amp", "gain"): "1"}))
    R.cmd_check(None)
    plan = J.load(open(tmp_path / "plan.json"))
    assert len(plan["songs"]) == R.N_SONGS and all(x["D_is_M"] and not x["reader_on"] for x in plan["songs"])


def test_the_artifact_page_builds():
    __import__("pytest").importorskip("numpy")                         # C1a's wrapper imports it; the light CI runners have none
    from learn import c1a_ear as C

    items = [{"id": "i1", "n": 1}]
    page, css, js = R.page_html(items, {"i1-ref": "", "i1-mix": "", "i1-A": "", "i1-B": "", "i1-C": ""}, "b0")
    art = C.artifact_page(page, css, js)
    assert "Guitar (G)" in art and "Export</b> any time" not in art
