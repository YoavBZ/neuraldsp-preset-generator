"""C1a by ear (docs/full-controls-plan.md): learn/c1a_ear.py's draw, order, read, page and render."""
import json
import re

import pytest

from learn import c1a_ear as C
from learn import local_objective as LO


def unit(u, cls="clean"):
    return {"unit": u, "cls": cls}


def test_never_heard_leaves_out_cards_spares_played_items_and_h4bs_cards():
    units = [unit(f"u{i}") for i in range(8)]
    n12 = {"cards": [unit("u0")], "spares": [unit("u1")]}
    key = {"items": [{"unit": "u2"}, {"unit": "u0"}]}
    h4b = {"cards": [unit("u3")]}
    assert C.never_heard(units, n12, key, h4b) == ["u4", "u5", "u6", "u7"]


def bks(i, di, cls="clean", real_out=False):
    return {"set": "bks", "key": f"k{i}", "cluster": di, "cls": cls, "real_out": real_out}


def test_bks_draw_is_seeded_one_a_di_and_skips_real_out():
    recs = [bks(i, f"d{i % 8}", "clean" if i % 8 < 4 else "crunch") for i in range(32)] + [bks(99, "d9", real_out=True)]
    a, b = C.bks_draw(recs), C.bks_draw(list(reversed(recs)))
    assert [r["key"] for r in a] == [r["key"] for r in b] and len(a) == 7
    assert len({r["cluster"] for r in a}) == 7 and "d9" not in {r["cluster"] for r in a}
    assert C.bks_draw(recs, seed=1) != a
    assert len({frozenset(r["cluster"] for r in C.bks_draw(recs, seed=s)) for s in range(12)}) > 1   # the DIs are drawn
    with pytest.raises(SystemExit):
        C.bks_draw([bks(i, f"d{i}") for i in range(6)])


def items14():
    return ([{"set": "n12", "key": f"n{i}", "cls": "clean"} for i in range(7)]
            + [{"set": "bks", "key": f"b{i}", "cls": "crunch"} for i in range(7)])


def test_page_order_one_repeat_a_set_far_enough_with_the_letters_swapped():
    for seed in range(20):
        out = C.page_order(items14(), seed=seed)
        assert len(out) == 16 and [o["n"] for o in out] == list(range(1, 17))
        reps = [o for o in out if o["repeat_of"]]
        assert sorted(o["set"] for o in reps) == ["bks", "n12"]
        for r in reps:
            f = next(o for o in out if o["id"] == r["repeat_of"])
            assert f["key"] == r["key"] and r["n"] - f["n"] >= C.GAP
            assert r["letters"] == {"A": f["letters"]["B"], "B": f["letters"]["A"]}
        firsts = [o for o in out if not o["repeat_of"]]
        assert sum(o["letters"]["A"] == "label" for o in firsts) == 7               # balanced
        assert all(sorted(o["letters"].values()) == ["C1a", "label"] for o in out)
    assert C.page_order(items14()) == C.page_order(list(reversed(items14())))


def item(i, a="label", cluster="c", st="n12", cls="clean", rep=None, j0=(2.0, 1.8)):
    lets = {"A": a, "B": "C1a" if a == "label" else "label"}
    return {"id": f"i{i}", "letters": lets, "cluster": cluster, "set": st, "cls": cls, "repeat_of": rep,
            "j0": {"label": j0[0], "C1a": j0[1]}}


def test_unblind_allows_a_tie_and_needs_both_ranks():
    it = item(1, a="label")
    assert C.unblind(it, {"rank": {"A": 1, "B": 1}}) == {"label": {"rank": 1, "close": None}, "C1a": {"rank": 1, "close": None}}
    got = C.unblind(it, {"rank": {"A": 2, "B": 1}, "close": {"A": "far", "B": "close"}})
    assert got == {"label": {"rank": 2, "close": 0}, "C1a": {"rank": 1, "close": 2}}
    assert C.unblind(it, {"rank": {"A": 1}}) is None and C.unblind(it, {"rank": {"A": 1, "B": 3}}) is None
    assert C.unblind(it, None) is None
    assert C.pref(got) == 1.0 and C.pref(C.unblind(it, {"rank": {"A": 1, "B": 2}})) == 0.0
    assert C.pref(C.unblind(it, {"rank": {"A": 2, "B": 2}})) == 0.5


def test_ear_read_counts_a_tie_as_a_half_clusters_by_set_and_reads_repeats_and_j0():
    items = [item(1, "label", "x"), item(2, "C1a", "x"), item(3, "label", "y", st="bks", cls="crunch", j0=(1.0, 1.2)),
             item(4, "C1a", "z", st="bks"), item(5, "C1a", "x", rep="i1")]
    got = {"i1": {"rank": {"A": 2, "B": 1}},                 # C1a (B) above
           "i2": {"rank": {"A": 1, "B": 1}},                 # a tie
           "i3": {"rank": {"A": 1, "B": 2}},                 # the label above
           "i4": {"rank": {"A": 1, "B": 2}, "close": {"A": "close", "B": "some"}},   # C1a (A) above, closer by 1
           "i5": {"rank": {"A": 1, "B": 2}}}                 # the repeat: C1a on A, above again
    r = C.ear_read(items, got)
    assert r["read"] == 4 and r["unanswered"] == [] and r["page_failed"]
    assert r["primary"]["share"] == pytest.approx((1 + 0.5 + 0 + 1) / 4)
    assert (r["primary"]["above"], r["primary"]["ties"], r["primary"]["below"]) == (2, 1, 1)
    assert r["primary"]["clusters"] == 3                                         # n12:x, bks:y, bks:z
    assert r["by_set"]["n12"]["share"] == pytest.approx(0.75) and r["by_set"]["bks"]["share"] == pytest.approx(0.5)
    assert r["by_class"]["crunch"]["share"] == 0.0
    assert r["repeats"] == [{"id": "i5", "repeat_of": "i1", "first": 1.0, "again": 1.0, "agree": True}]
    assert r["j0_agrees"] == {"decided": 3, "agree": 3, "j0_closer_c1a": 3}       # i3: J0 and the ear both say the label
    assert r["close_gap_mean"] == pytest.approx(1.0) and r["close_gap_n"] == 1


def test_share_row_counts_ties_apart_and_clusters_keep_their_set():
    row = C.share_row([{"cluster": c, "pref": p} for c, p in (("a", 1.0), ("b", 0.5), ("c", 0.5), ("d", 0.0))])
    assert (row["above"], row["ties"], row["below"]) == (1, 2, 1) and row["share"] == pytest.approx(0.5)
    items = [item(1, "label", "x"), item(2, "label", "x", st="bks")]
    r = C.ear_read(items, {"i1": {"rank": {"A": 2, "B": 1}}, "i2": {"rank": {"A": 2, "B": 1}}})
    assert r["primary"]["clusters"] == 2                                         # n12:x and bks:x are two clusters


def test_ear_read_reads_with_ten_answered():
    items = [item(i, "label", f"c{i % 5}") for i in range(1, 15)]
    got = {f"i{i}": {"rank": {"A": 2, "B": 1}} for i in range(1, 11)}
    r = C.ear_read(items, got)
    assert r["read"] == 10 and not r["page_failed"] and len(r["unanswered"]) == 4
    assert r["primary"]["share"] == 1.0
    got.pop("i10")
    assert C.ear_read(items, got)["page_failed"]


def test_the_player_allows_ties_two_letters_and_optional_ratings():
    js = C.player_js()
    assert "delete r[o]" not in js and '"C"' not in js and '"D"' not in js
    assert 'KEYS = ["ref", "A", "B"]' in js and 'const full = ["A", "B"].every(l => r[l]);' in js
    assert 'const STORE = "c1a-ear:" + DATA.build;' in js and "ear-vreal" not in js


def test_cards_give_ranks_one_and_two_for_each_letter_and_no_third():
    html = C.cards([{"id": "i1", "n": 1}, {"id": "i2", "n": 2}])
    for k in ("A", "B"):
        for r in (1, 2):
            assert f'data-l="{k}" data-r="{r}"' in html
    assert 'data-r="3"' not in html and 'data-l="C"' not in html and "scope" not in html
    assert html.count('class="item"') == 2


def test_the_artifact_page_syncs_answers_and_drops_the_file_save():
    pytest.importorskip("numpy")                                                 # ear_eat imports the renderers
    page, css, js = C.page_html([{"id": "i1", "n": 1}], {}, "b123")
    art = C.artifact_page(page, css, js)
    assert 'db.doc("answers/" + DATA.build)' in art and ".scope" not in art
    assert 'id="save"' not in art and "if (false) document.getElementById(\"save\")" in art
    assert "<title>Record A/B Check</title>" in art and '"build": "b123"' in art


def test_leaks_names_units_keys_bands_di_stems_and_the_c1a_tag():
    its = [{"unit": "cap/abc#ac20", "key": "cap/abc#ac20|ac20", "cluster": "set5/BKS_X/19_ElecGtr1aDI.wav", "slug": "s1x"}]
    assert C.leaks("nothing here", its) == []
    assert C.leaks("a 19_ElecGtr1aDI.wav b", its) == ["19_ElecGtr1aDI.wav"]
    assert C.leaks("C1a", its) == ["C1a"] and C.leaks("cap/abc#ac20", its) == ["cap/abc#ac20"]


def test_only_the_render_is_a_render_command():
    assert any(re.search(p, "python -u -m learn.c1a_ear c1a-ear-render --shard 0/3") for p in LO.RENDERS)
    for cmd in ("c1a-ear-draw", "c1a-ear-page", "c1a-ear-read"):
        assert not any(re.search(p, f"python -m learn.c1a_ear {cmd}") for p in LO.RENDERS)


def _render_stub(tmp_path, monkeypatch, off=0.0):
    import argparse  # noqa: F401
    np = pytest.importorskip("numpy")
    from learn import audibility_measure as AM
    from learn import full_controls as F
    from learn import knob_ceiling as K
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import score_ear as SE
    from learn import song_bank as B

    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(P, "require", lambda k: {})
    monkeypatch.setattr(LO, "_wait_cap", lambda *a: None)
    monkeypatch.setattr(PS, "free_gb", lambda: 1e9)
    monkeypatch.setattr(PS, "TRIM_S", 0.0)
    monkeypatch.setattr(PS, "SEC_S", 2.0)
    monkeypatch.setattr(PS, "SR", 4)
    monkeypatch.setattr(PS, "section_audio", lambda path, start: np.zeros(8))
    monkeypatch.setattr(B, "measure", lambda a: np.zeros(8))
    monkeypatch.setattr(P, "real_amp_track", lambda sd, track, start: np.arange(8.0))
    monkeypatch.setattr(SE, "h4_window", lambda held, n_ref, n_ren, lag: (2, 6))
    calls = {"n": 0}
    level = {"label": 2.0, "C1a": 1.5}

    def fresh(make, di, sel, xp, x):
        calls["n"] += 2
        assert xp == x
        return np.arange(8.0) + level[x[("t", "who")]]
    monkeypatch.setattr(AM, "fresh_render", fresh)
    monkeypatch.setattr(K, "judge", lambda ref, y, di, lag: {"A": 9.0, "B": float(y[0])})
    rows = []
    for i, st in enumerate(("n12", "bks")):
        u = f"{'cap' if st == 'n12' else 'set5'}/u{i}"
        key = f"{u}|pr12"
        src = tmp_path / "src" / f"u{i}.json"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(json.dumps({"unit": u, "amp": "pr12", "held": "B", "lag": 1, "select": 0,
                                   "best": {"settings": {"t/who": "label"}, "judge": {"B": 2.0 + off}}}))
        root, sub = F.OUT_DIRS[st]
        c1 = tmp_path / root / sub / f"{F.fname(key)}.json"
        c1.parent.mkdir(parents=True, exist_ok=True)
        c1.write_text(json.dumps({"unit": u, "amp": "pr12", "held": "B", "lag": 1, "label": {"t/who": "C1a"},
                                  "fresh": {"best": {"judge": {"B": 1.5}}}}))
        rows.append({"set": st, "key": key, "unit": u, "amp": "pr12", "cls": "clean", "cluster": f"c{i}", "source": str(src),
                     "prt": {"di_path": "", "start_s": 0.0, "sd": "", "track": ""}, "slug": f"s{i}"})
    (tmp_path / "c1a" / "ear").mkdir(parents=True, exist_ok=True)
    (tmp_path / "c1a" / "ear" / "plan.json").write_text(json.dumps({"items": rows}))
    return rows, calls, np


def test_cmd_render_holds_each_render_to_its_stored_held_judge_and_resumes(tmp_path, monkeypatch, capsys):
    import argparse
    rows, calls, np = _render_stub(tmp_path, monkeypatch)
    done = tmp_path / "c1a" / "ear" / "clips" / "s1.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    done.write_text("{}")
    C.cmd_render(argparse.Namespace(shard=(0, 1)))
    assert json.loads(done.read_text()) == {}                                    # resume: skipped
    z = np.load(tmp_path / "c1a" / "ear" / "clips" / "s0.npz")
    assert list(z["ref"]) == [2.0, 3.0, 4.0, 5.0] and list(z["window"]) == [2, 6]
    assert list(z["label"]) == [3.0, 4.0, 5.0, 6.0] and list(z["C1a"]) == [2.5, 3.5, 4.5, 5.5]   # the window less the lag
    rec = json.loads((tmp_path / "c1a" / "ear" / "clips" / "s0.json").read_text())
    assert rec["cands"]["label"]["judge"] == 2.0 and rec["cands"]["C1a"]["stored"] == 1.5 and rec["window"] == [2, 6]
    assert "C1A-EAR RENDER DONE 0/1: 4 renders" in capsys.readouterr().out and calls["n"] == 4


def test_cmd_render_stops_on_a_held_judge_off_its_stored_one(tmp_path, monkeypatch):
    import argparse
    _render_stub(tmp_path, monkeypatch, off=0.05)
    with pytest.raises(SystemExit, match="label's fresh held judge"):
        C.cmd_render(argparse.Namespace(shard=(0, 1)))
