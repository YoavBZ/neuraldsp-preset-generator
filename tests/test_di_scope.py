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


# --- the review's guards: answers only add, and a file that will never be ready -------------------------------------

def _key(tmp_path, n=3):
    (tmp_path / D.DIR).mkdir(exist_ok=True)
    (tmp_path / D.DIR / "key.json").write_text(json.dumps({"build": D.BUILD, "items": [
        {"id": f"d{i}", "di": f"lib/{i}"} for i in range(n)]}))


def _sitting(tmp_path, answers):
    pytest.importorskip("numpy")                      # CI's light runner has no numpy (`answers` reads through ear_eat)
    import argparse
    store = tmp_path / "store.json"
    store.write_text(json.dumps({"build": D.BUILD, "answers": {k: {"v": v} for k, v in answers.items()}}))
    D.cmd_answers(argparse.Namespace(store=str(store)))
    return json.loads((tmp_path / D.DIR / "verdicts.json").read_text())


def test_a_later_sitting_may_only_add_answers(tmp_path, monkeypatch):
    from learn import pipeline_fix as P
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(P, "require", lambda k: {})
    _key(tmp_path)
    v = _sitting(tmp_path, {"d0": "heavy"})
    assert v["verdicts"] == {"lib/0": "heavy"} and not v["complete"]
    v = _sitting(tmp_path, {"d1": "keep", "d2": "unsure"})                         # adds; d0 kept from the first
    assert v["verdicts"] == {"lib/0": "heavy", "lib/1": "keep", "lib/2": "unsure"} and v["complete"]
    assert v["dropped"] == ["lib/0", "lib/2"]
    v = _sitting(tmp_path, {"d0": "heavy", "d1": "keep"})                          # the same answers again: fine
    with pytest.raises(SystemExit, match="would change"):
        _sitting(tmp_path, {"d0": "keep"})
    assert json.loads((tmp_path / D.DIR / "verdicts.json").read_text())["verdicts"]["lib/0"] == "heavy"


def test_merged_verdicts_refuse_another_builds_record():
    with pytest.raises(SystemExit, match="move it aside"):
        D.merged_verdicts({"build": "other", "verdicts": {}}, {"a": "keep"}, D.BUILD)


def test_ready_says_complete_not_yet_or_never(tmp_path, monkeypatch):
    from learn import pipeline_fix as P
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    assert D.ready_state()[0] == 3                                                 # no verdicts yet
    (tmp_path / D.DIR).mkdir()
    vp = tmp_path / D.DIR / "verdicts.json"
    vp.write_text(json.dumps({"build": D.BUILD, "verdicts": {"a": "keep"}}))
    assert D.ready_state()[0] == 3                                                 # partial
    vp.write_text(json.dumps({"build": D.BUILD, "verdicts": {f"x{i}": "keep" for i in range(D.N_CARDS)}}))
    assert D.ready_state()[0] == 0
    vp.write_text(json.dumps({"build": "other", "verdicts": {}}))
    code, why = D.ready_state()
    assert code == 2 and "other" in why
    vp.write_text("{not json")
    assert D.ready_state()[0] == 2
    with pytest.raises(SystemExit) as e:
        D.cmd_ready(None)
    assert e.value.code == 2


def test_the_training_launcher_stops_on_a_verdicts_file_that_will_never_be_ready(tmp_path):
    import pathlib
    import shutil
    import subprocess
    if shutil.which("zsh") is None:
        pytest.skip("no zsh")
    text = (pathlib.Path(__file__).resolve().parents[1] / "logs" / "launch-c3r-train.zsh").read_text()
    fn = text[text.index("scope_ready() {"):text.index('note "waiting for C2r')]
    fake = tmp_path / "py"
    log = tmp_path / "train.log"
    for rc, want_exit, want_log in ((2, 1, "FAILED: the DI scope's readiness check exited 2"),
                                    (1, 1, "FAILED: the DI scope's readiness check exited 1"), (3, 7, None), (0, 0, None)):
        fake.write_text(f"#!/bin/zsh\necho 'DI SCOPE STATE {rc}'\nexit {rc}\n")
        fake.chmod(0o755)
        log.write_text("")
        script = (f"PY={fake}\nLOGS={tmp_path}\nnote() {{ echo \"$1\" >> {log}; }}\n{fn}\n"
                  "scope_ready && exit 0\nexit 7\n")
        r = subprocess.run(["zsh", "-c", script], capture_output=True, text=True)
        assert r.returncode == want_exit, (rc, r.returncode, r.stderr)
        if want_log:
            assert want_log in log.read_text() and f"DI SCOPE STATE {rc}" in log.read_text()
        else:
            assert log.read_text() == ""


# --- the amp-track page (2026-11-11, the user's ask) ------------------------------------------------------------------

def test_the_amp_page_keeps_the_cards_and_adds_the_switch_and_the_processed_verdict():
    page = D.page_html_amp(["d1", "d2"], {"d1": "", "d1a": "", "d2": ""}, {"d1": "d1a"}, {"d2": D.NO_AMP_NOTE}, "b1")
    assert '"items": ["d1", "d2"], "amp": {"d1": "d1a"}' in page and D.NO_AMP_NOTE in page
    assert 'id="sd"' in page and 'id="sa"' in page and 'data-v="processed"' in page and "Drop: processed" in page
    assert "Playing (it loops)" not in page and "setSide" in page and 'answer("processed")' in page
    assert "2 dry guitar recordings (DIs)" in page and D.leaks(page) == []


def test_processed_is_a_verdict_and_drops():
    items = [{"id": "d1", "di": "a"}, {"id": "d2", "di": "b"}]
    got = D.di_verdicts({"d1": {"v": "processed"}, "d2": {"v": "keep"}}, items)
    assert got == {"a": "processed", "b": "keep"}
    assert D.dropped_of({"verdicts": got}) == {"a"}


def test_amp_sources_take_the_sessions_track_or_none_and_refuse_an_unnamed_di():
    di = next(iter(D.SESSION_AMP))
    n12 = [{"unit": "cap/x", "di_item": "lib-1"}, {"unit": "cap/y", "di_item": "lib-2"}]
    panel = [{"unit": "panel/p", "amp_file": "/s/amp.wav", "window_s": 220.0, "di_file": "/s/di.wav"}]
    meta = {"lib-1": {"di_path": "/lib/song/di.wav", "start_s": 40.0}, "lib-2": {"di_path": "/lib/dark/di.wav", "start_s": 5}}
    items = [{"id": "d1", "set": "n12", "unit": "cap/x", "di": di},
             {"id": "d2", "set": "n12", "unit": "cap/y", "di": D.NO_SESSION_AMP[0]},
             {"id": "d3", "set": "panel", "unit": "panel/p", "di": "panel/p"}]
    got = D.amp_sources(items, n12, panel, meta)
    assert got["d1"] == {"path": "/lib/song/" + D.SESSION_AMP[di], "start": 40.0, "di_file": "/lib/song/di.wav"}
    assert got["d2"] is None and got["d3"] == {"path": "/s/amp.wav", "start": 220.0, "di_file": "/s/di.wav"}
    with pytest.raises(SystemExit):
        D.amp_sources([dict(items[0], di="cambridge/other/DI.wav")], n12, panel, meta)


def test_every_n12_card_is_named_and_its_amp_track_exists():
    import pathlib
    from learn import pipeline_fix as P
    key = P.out_dir() / D.DIR / "key.json"
    if not key.exists():
        pytest.skip("no stored data")
    k = json.loads(key.read_text())
    meta = json.loads((P.out_dir() / "captures2" / "plan.json").read_text())["di_meta"]
    n12 = [it for it in k["items"] if it["set"] == "n12"]
    assert {it["di"] for it in n12} == set(D.SESSION_AMP) | set(D.NO_SESSION_AMP)
    folders = {m["di"]: pathlib.Path(m["di_path"]).parent for m in meta.values()}
    for di, amp in D.SESSION_AMP.items():
        assert (folders[di] / amp).exists(), (di, amp)


def test_the_four_pairs_not_the_same_take_carry_the_note():
    assert set(D.UNALIGNED) <= set(D.SESSION_AMP) and len(D.UNALIGNED) == 4
    assert "not the same take" in D.UNALIGNED_NOTE


def test_the_built_page_is_the_published_build_with_its_notes():
    from learn import pipeline_fix as P
    d = P.out_dir() / D.DIR
    if not (d / D.AMP_PAGE).exists():
        pytest.skip("no stored data")
    page, k = (d / D.AMP_PAGE).read_text(), json.loads((d / D.AMP_KEY).read_text())
    t = '<script id="data" type="application/json">'
    data = json.loads(page[page.index(t) + len(t):page.index("</script>", page.index(t))])
    key = json.loads((d / "key.json").read_text())
    assert data["build"] == D.BUILD and data["items"] == [it["id"] for it in key["items"]]
    unaligned = {it["id"] for it in key["items"] if it["di"] in D.UNALIGNED}
    none = {it["id"] for it in key["items"] if it["di"] in D.NO_SESSION_AMP}
    assert {i for i, n in data["notes"].items() if n == D.UNALIGNED_NOTE} == unaligned and len(unaligned) == 4
    assert {i for i, n in data["notes"].items() if n == D.NO_AMP_NOTE} == none and not none & set(data["amp"])
    assert len(data["amp"]) == 23 and len(k["items"]) == 26 and D.leaks(page) == []

