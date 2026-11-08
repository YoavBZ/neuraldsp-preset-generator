"""H4b's page by ear (`learn/score_ear.py` h4b-*), with fakes: no renders, no pages built, no answers read."""
import argparse
import collections
import json
import math
import random

import pytest

from learn import pipeline_fix as P
from learn import score_ear as E


def _ledger(monkeypatch, have=(E.WIDE, E.H4)):
    def require(key):
        if key not in have:
            raise SystemExit(f"the ledger has no {key}")
        return {}
    monkeypatch.setattr(P, "require", require)


def _units():
    """Clean: 4 bands x 3 units, one of them on N12's page each; crunch: 4 bands x 2 units, 4 on N12's page."""
    out = []
    for b in range(4):
        out += [{"unit": f"cl{b}{j}", "player": f"band{b}", "cls": "clean", "amp": "pr12", "di": f"s/d{b}{j}.wav"} for j in range(3)]
        out += [{"unit": f"cr{b}{j}", "player": f"band{b}", "cls": "crunch", "amp": "ac20", "di": f"s/e{b}{j}.wav"} for j in range(2)]
    on = {f"cl{b}0" for b in range(4)} | {f"cr{b}0" for b in range(4)}
    return out, on


# --- the draw -------------------------------------------------------------------------------------------------------

def test_the_draw_takes_8_unheard_clean_and_6_crunch_at_most_2_a_band_in_a_class():
    units, on = _units()
    cards = E.h4b_draw(units, on)
    clean, crunch = [c for c in cards if c["cls"] == "clean"], [c for c in cards if c["cls"] == "crunch"]
    assert len(clean) == 8 and len(crunch) == 6 and len({c["unit"] for c in cards}) == 14
    assert not any(c["unit"] in on for c in clean) and not any(c["heard_on_n12"] for c in clean)
    assert all(c["heard_on_n12"] == (c["unit"] in on) for c in crunch)
    for part in (clean, crunch):
        assert max(collections.Counter(c["player"] for c in part).values()) <= 2
    assert cards == E.h4b_draw(list(reversed(units)), on)                       # seeded, on the units' order alone
    scored = [dict(u, judge=random.random()) for u in units]                    # no score enters it
    assert [c["unit"] for c in E.h4b_draw(scored, on)] == [c["unit"] for c in cards]
    assert [c["unit"] for c in E.h4b_draw(units, on, seed=1)] != [c["unit"] for c in cards]


def test_the_draw_refuses_when_the_band_limit_cant_fill_a_class():
    units, on = _units()
    with pytest.raises(SystemExit, match="at most 2 a band"):
        E.h4b_draw([u for u in units if u["player"] in ("band0", "band1", "band2") or u["cls"] == "crunch"], on)


def test_h4b_draw_stores_the_cards_once_with_n12s_fields(tmp_path, monkeypatch):
    units, on = _units()
    units = [dict(u, di_path=f"/di/{u['unit']}.wav", start_s=10.0) for u in units]
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(E, "wide_units", lambda: (units, {u["unit"]: {"search": "A", "held": "B", "lag": 3} for u in units}, []))
    (tmp_path / E.WIDE_DIR).mkdir()
    (tmp_path / E.WIDE_DIR / "plan.json").write_text(json.dumps({"cards": [{"unit": u} for u in sorted(on)][:5],
                                                                  "spares": [{"unit": u} for u in sorted(on)][5:]}))
    _ledger(monkeypatch, have=(E.WIDE,))
    with pytest.raises(SystemExit, match=E.H4):
        E.cmd_h4b_draw(None)
    _ledger(monkeypatch)
    E.cmd_h4b_draw(None)
    plan = json.loads((tmp_path / E.WIDE_DIR / E.H4B_DIR / "plan.json").read_text())
    assert len(plan["cards"]) == 14 and plan["spares"] == [] and plan["seed"] == 20261112
    c = plan["cards"][0]
    assert {"slug", "band", "cluster", "di", "di_path", "start_s", "search", "held", "lag", "heard_on_n12"} <= set(c)
    with pytest.raises(SystemExit, match="drawn once"):
        E.cmd_h4b_draw(None)


# --- the page order -------------------------------------------------------------------------------------------------

def _n12_page_order(cards, spares, cands, letters, seed=E.PAGE_SEED, gap=4):
    """N12's `page_order` as it stood before H4b, for the unchanged-behaviour check."""
    from learn import capture_ear as C

    keep = C.CANDS, C.LETTERS
    C.CANDS, C.LETTERS = cands, letters
    try:
        rng = random.Random(seed)
        by = {u["unit"]: dict(u, spare=False) for u in cards} | {u["unit"]: dict(u, spare=True) for u in spares}
        twice = [rng.choice(sorted(u["unit"] for u in cards if u["cls"] == c)) for c in ("clean", "crunch")]
        seq = sorted(by) + twice
        while True:
            rng.shuffle(seq)
            if all(seq.index(t) + gap <= len(seq) - 1 - seq[::-1].index(t) for t in twice):
                break
        perms = iter(C.balanced(rng, len(by)))
        items, first = [], {}
        for n, u in enumerate(seq, 1):
            order = tuple(first[u][1][1:] + first[u][1][:1]) if u in first else next(perms)
            items.append({**by[u], "id": f"i{n}", "n": n, "letters": dict(zip(letters, order)), "repeat_of": first[u][0] if u in first else None})
            first.setdefault(u, (f"i{n}", list(order)))
    finally:
        C.CANDS, C.LETTERS = keep
    return items


def test_n12s_page_order_is_unchanged():
    units, on = _units()
    cards, spares = units[:14], units[14:16]
    letters = ("A", "B", "C", "D", "E")
    for seed in (E.PAGE_SEED, 1, 2, 3):
        assert E.page_order(cards, spares, E.CANDS, letters, seed=seed) == _n12_page_order(cards, spares, E.CANDS, letters, seed=seed)


def test_two_repeats_a_class_come_later_on_other_letters():
    units, on = _units()
    cards = E.h4b_draw(units, on)
    letters = ("A", "B", "C", "D", "E")
    items = E.page_order(cards, [], E.H4B_CANDS, letters, seed=E.H4B_SEED, repeats=2)
    assert len(items) == 18 and len([i for i in items if i["repeat_of"] is None]) == 14
    rep = [i for i in items if i["repeat_of"]]
    assert collections.Counter(i["cls"] for i in rep) == {"clean": 2, "crunch": 2}
    by = {i["id"]: i for i in items}
    for r in rep:
        f = by[r["repeat_of"]]
        assert f["unit"] == r["unit"] and r["n"] - f["n"] >= 4
        assert all(f["letters"][k] != r["letters"][k] for k in letters)            # every candidate on another letter
    firsts = [i for i in items if i["repeat_of"] is None]
    per = collections.Counter((k, i["letters"][k]) for i in firsts for k in letters)
    assert max(per.values()) - min(per.values()) <= 1                            # letters balanced over first hearings
    assert all(sorted(i["letters"].values()) == sorted(E.H4B_CANDS) for i in items)


# --- the clips' sources ---------------------------------------------------------------------------------------------

def _src(win=(8, 16)):
    clip = lambda v: [v] * 8                                                      # noqa: E731
    n12 = {"ref": clip(0.0), "S": clip(0.5), "FTm": clip(1.0)}
    base = {**n12, "window": list(win)}
    tag_clip = {t: {"clip": clip(2.0 + j), "window": list(win)} for j, t in enumerate(E.H4B_ARMS)}
    tag_rec = {t: {"window": list(win), "judge": 3.0 + j} for j, t in enumerate(E.H4B_ARMS)}
    n12_rec = {"window": list(win), "judge": {"FTm": 2.0}}
    return n12, base, tag_clip, tag_rec, n12_rec


def test_clips_come_from_n12_where_it_kept_them_else_from_h4as_base():
    n12, base, tc, tr, rec = _src()
    clips, wins, j0 = E.h4b_sources("s", n12, {**base, "S": [9.0] * 8}, tc, tr, rec, 4.0)
    assert clips["S"] == n12["S"] and clips["P2b-ftmg"] == tc["P2b-ftmg"]["clip"]   # N12's clips win over a base file
    assert wins == {c: [8, 16] for c in E.H4B_CANDS}
    assert j0 == {"S": 4.0, "FTm": 2.0, "P2b-ftmf": 3.0, "P2b-ftmg": 4.0, "P2b-ftmc": 5.0}
    clips, _, _ = E.h4b_sources("s", None, base, tc, tr, {"judge": {"FTm": 2.0}}, 4.0)
    assert clips["S"] == base["S"] and clips["ref"] == base["ref"]


@pytest.mark.parametrize("change, why", [
    (lambda a: a.update(n12=None, base=None), "no clips of the reference"),
    (lambda a: a.update(n12=None, base={k: v for k, v in a["base"].items() if k != "S"}), "no clips of the reference"),
    (lambda a: a["tc"].pop("P2b-ftmc"), "no H4a clip"),
    (lambda a: a["tr"].pop("P2b-ftmf"), "no H4a clip"),
    (lambda a: a["tr"]["P2b-ftmg"].update(window=[7, 15]), "window"),
    (lambda a: a["tc"]["P2b-ftmg"].update(window=[7, 15]), "window"),
    (lambda a: a["tr"]["P2b-ftmf"].update(judge=math.inf), "finite stored J0"),
    (lambda a: a["rec"]["judge"].pop("FTm"), "finite stored J0"),
])
def test_a_missing_clip_or_a_moved_window_refuses(change, why):
    n12, base, tc, tr, rec = _src()
    a = {"n12": n12, "base": base, "tc": tc, "tr": tr, "rec": rec}
    change(a)
    with pytest.raises(SystemExit, match=why):
        E.h4b_sources("s", a["n12"], a["base"], a["tc"], a["tr"], a["rec"], 4.0)


def test_h4b_page_stores_n12s_fields_and_refuses_a_missing_clip_before_building(tmp_path, monkeypatch):
    pytest.importorskip("numpy")                                                 # numpy, or ear_eat's imports
    units, on = _units()
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    cards = [dict(c, slug=E.slug_of(c["unit"]), band=c["player"], cluster=c["player"], lag=3, di_path="/d.wav", start_s=1.0)
             for c in E.h4b_draw(units, on)]
    d = tmp_path / E.WIDE_DIR / E.H4B_DIR
    d.mkdir(parents=True)
    (d / "plan.json").write_text(json.dumps({"cards": cards, "spares": []}))
    monkeypatch.setattr(E, "wide_units", lambda: ([], {}, []))
    n12, base, tc, tr, rec = _src()
    srcs = {c["unit"]: E.h4b_sources(c["slug"], n12, base, tc, tr, rec, 4.0) for c in cards}
    monkeypatch.setattr(E, "h4b_card_sources", lambda it, recs: srcs[it["unit"]])
    built = {}

    def parts(items, cands, group_of, cache, listening, page_out, label):
        built.update(items=items, cands=cands, group=group_of(items[0]), listening=listening, out=page_out, cache=cache)
        return [dict(i, part=1) for i in items], ["b1", "b2"]
    monkeypatch.setattr(E, "page_parts", parts)
    _ledger(monkeypatch)
    E.cmd_h4b_page(None)
    key = json.loads((d / "key.json").read_text())
    assert key["builds"] == ["b1", "b2"] and len(key["items"]) == 18 and built["cands"] == E.H4B_CANDS
    it = key["items"][0]
    assert it["windows"] == {c: [8, 16] for c in E.H4B_CANDS} and it["j0"]["P2b-ftmc"] == 5.0
    assert it["lag"] == 3 and it["di_path"] == "/d.wav" and it["start_s"] == 1.0 and "heard_on_n12" in it
    assert built["out"] == d / "page" and built["cache"] == d / "aac-cache" and built["listening"] == "ear-h4b"
    assert sorted(built["group"]) == ["A", "B", "C", "D", "E", "ref"]
    plays = {"S": .5, "FTm": 1., **{t: 2. + j for j, t in enumerate(E.H4B_ARMS)}}          # each letter its candidate's clip
    assert all(float(built["group"][k][0]) == plays[c] for k, c in built["items"][0]["letters"].items())
    assert float(built["group"]["ref"][0]) == 0.0
    with pytest.raises(SystemExit, match="exists"):
        E.cmd_h4b_page(None)
    (d / "key.json").unlink()
    monkeypatch.setattr(E, "h4b_card_sources", lambda it, recs: (_ for _ in ()).throw(SystemExit("no H4a clip")))
    built.clear()
    with pytest.raises(SystemExit, match="no H4a clip"):
        E.cmd_h4b_page(None)
    assert not built and not (d / "key.json").exists()


def test_n12s_page_reads_its_own_clips_as_before(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    units, _ = _units()
    cards = [dict(u, slug=E.slug_of(u["unit"]), band=u["player"]) for u in units[:14]]
    w = tmp_path / E.WIDE_DIR
    w.mkdir()
    (w / "plan.json").write_text(json.dumps({"cards": cards, "spares": [dict(u, slug=E.slug_of(u["unit"]), band=u["player"]) for u in units[14:16]]}))
    for c in cards + [dict(u, slug=E.slug_of(u["unit"])) for u in units[14:16]]:
        (w / "renders" / c["slug"]).mkdir(parents=True)
        np.savez(w / "renders" / c["slug"] / "clips.npz", ref=np.zeros(4), **{k.replace("-", "_"): np.full(4, j) for j, k in enumerate(E.CANDS)})
    seen = {}

    def parts(items, cands, group_of, cache, listening, page_out, label="N12"):
        g = group_of(items[0])
        seen.update(cands=cands, listening=listening, out=page_out, cache=cache, label=label,
                    ok=all(float(g[k][0]) == E.CANDS.index(c) for k, c in items[0]["letters"].items()))
        return items, ["x"]
    monkeypatch.setattr(E, "page_parts", parts)
    E.cmd_page(None)
    assert seen == {"cands": E.CANDS, "listening": E.LISTENING, "out": w / "page", "cache": w / "aac-cache", "label": "N12", "ok": True}
    key = json.loads((w / "key.json").read_text())
    assert list(key) == ["page", "builds", "items", "time"] and key["page"] == E.WIDE_DIR and len(key["items"]) == 18


# --- the read -------------------------------------------------------------------------------------------------------

def test_t_sf_matches_closed_forms():
    for t in (0.0, 0.3, 1.0, 2.5, 7.0, -1.5):
        assert E.t_sf(t, 1) == pytest.approx(0.5 - math.atan(t) / math.pi, abs=1e-12)
        assert E.t_sf(t, 2) == pytest.approx(0.5 - t / (2 * math.sqrt(2 + t * t)), abs=1e-12)
    assert E.t_sf(1.894579, 7) == pytest.approx(0.05, abs=1e-6)                   # the table's t90 at 7 df
    assert E.t_sf(math.inf, 3) == 0.0 and E.t_sf(-math.inf, 3) == 1.0


def test_the_jackknife_t_is_the_band_clustered_delete_one_t():
    pairs = [("a", 1.0), ("a", 1.0), ("b", 1.0), ("b", 0.0), ("c", 0.0), ("d", 1.0)]
    r = E.jackknife_t(pairs)
    th = [2 / 4, 3 / 4, 4 / 5, 3 / 5]                                           # each band left out
    mt = sum(th) / 4
    se = math.sqrt(3 / 4 * sum((x - mt) ** 2 for x in th))
    assert r["share"] == pytest.approx(4 / 6) and r["clusters"] == 4 and r["df"] == 3
    assert r["se"] == pytest.approx(se) and r["t"] == pytest.approx((4 / 6 - 0.5) / se)
    assert r["p"] == pytest.approx(E.t_sf((4 / 6 - 0.5) / se, 3))
    assert E.jackknife_t([("a", 1.0), ("a", 0.0)])["p"] is None                  # one band: no t
    assert E.jackknife_t([("a", 1.0), ("b", 1.0)])["p"] == 0.0                   # every band above: se 0, p 0
    assert E.jackknife_t([("a", 1.0), ("a", 0.0), ("b", 1.0), ("b", 0.0)])["p"] == 0.5


def _card(i, band, ranks, cls="clean", heard=False, di=None):
    """A read card: `ranks` gives S, FTm and the arms' ranks in H4B_CANDS order; closeness 5 less the rank."""
    ear = {c: {"rank": r, "close": 5 - r} for c, r in zip(E.H4B_CANDS, ranks)}
    return {"page": "H4b", "id": f"i{i}", "cluster": band, "cls": cls, "amp": "pr12", "di": di or f"d{i}", "heard_on_n12": heard,
            "ear": ear, "j0": {c: float(r) for c, r in zip(E.H4B_CANDS, ranks)}}


def test_the_primary_is_holm_over_the_three_arm_over_ftm_rows():
    # full beats FTm on every card; gentle on most; the real arm never
    cards = [_card(i, f"b{i % 5}", (5, 3, 1, 2 if i % 4 else 4, 4 if i % 4 else 2)) for i in range(14)]
    rows = E.h4b_primary(cards)
    assert set(rows) == {f"{a} over FTm" for a in E.H4B_ARMS}
    f, g, c = (rows[f"{a} over FTm"] for a in E.H4B_ARMS)
    assert f["jackknife"]["share"] == 1.0 and f["jackknife"]["p"] == 0.0 and f["better_than_FTm"]
    assert c["jackknife"]["share"] < 0.5 and not c["better_than_FTm"]
    ps = {k: r["jackknife"]["p"] for k, r in rows.items()}
    assert {k: r["holm"] for k, r in rows.items()} == E.holm(ps)
    assert all(r["better_than_FTm"] == (r["holm"] < 0.05) for r in rows.values())
    assert {"share", "close_gap", "p_sign"} <= set(f)                           # N12's rows beside
    assert f["p_sign"] == E.sign_p(14, 14)


def test_one_band_gives_no_p_and_no_arm_reads_better():
    cards = [_card(i, "only", (5, 3, 1, 2, 4)) for i in range(14)]             # the full arm wins every card, in one band
    rows = E.h4b_primary(cards)
    f = rows["P2b-ftmf over FTm"]
    assert f["jackknife"]["share"] == 1.0 and f["jackknife"]["p"] is None
    assert f["holm"] == 1.0 and not any(r["better_than_FTm"] for r in rows.values())


def test_the_page_refuses_spares_and_a_tag_name_on_the_page(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    from learn import ear_eat as EE
    from learn import ear_vreal as EV

    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    d = tmp_path / E.WIDE_DIR / E.H4B_DIR
    d.mkdir(parents=True)
    (d / "plan.json").write_text(json.dumps({"cards": [], "spares": [{"unit": "x"}]}))
    _ledger(monkeypatch)
    with pytest.raises(SystemExit, match="no spares"):
        E.cmd_h4b_page(None)
    units, on = _units()
    cards = [dict(c, slug=E.slug_of(c["unit"]), band=c["player"]) for c in E.h4b_draw(units, on)]
    items = E.page_order(cards, [], E.H4B_CANDS, EE.LETTERS, seed=E.H4B_SEED, repeats=2)
    monkeypatch.setattr(EV, "level_group", lambda g: (g, {}))
    monkeypatch.setattr(EV, "encode", lambda y, cache: "x")
    group = lambda it: {"ref": np.zeros(4), **{k: np.zeros(4) for k in EE.LETTERS}}   # noqa: E731
    monkeypatch.setattr(EE, "cards", lambda chunk: "<p>P2b-ftmg</p>")
    from learn import pretrain_set as PS

    monkeypatch.setattr(PS, "HOME", tmp_path / "home")                           # a leak never reaches the real listening dir
    with pytest.raises(SystemExit, match="the page names"):
        E.page_parts(items, E.H4B_CANDS, group, d / "cache", "ear-h4b-test", d / "page", "H4b")
    assert not (d / "page").exists() and not (tmp_path / "home").exists()


def test_the_holm_step_can_turn_a_row_off():
    ps = {"x": 0.02, "y": 0.03, "z": 0.5}
    adj = E.holm(ps)
    assert adj == {"x": 0.06, "y": 0.06, "z": 0.5}                              # 0.02 alone would pass; adjusted it doesn't


def _items(n=14):
    """Key items for the read: 8 clean (never heard), 6 crunch (3 heard on N12), the first one's DI among W's."""
    out = []
    for i in range(n):
        cls = "clean" if i < 8 else "crunch"
        out.append({"id": f"i{i + 1}", "unit": f"u{i}", "cluster": f"b{i % 5}", "cls": cls, "amp": "pr12", "spare": False,
                    "di": "w-di" if i == 0 else f"d{i}", "heard_on_n12": cls == "crunch" and i % 2 == 0, "repeat_of": None,
                    "letters": dict(zip("ABCDE", E.H4B_CANDS)), "j0": {c: 1.0 + k for k, c in enumerate(E.H4B_CANDS)}})
    return out


def _answer(ranks):
    return {"rank": dict(zip("ABCDE", ranks)), "close": {k: "close" for k in "ABCDE"}}


def test_the_read_splits_the_beside_groups_and_applies_the_failure_rule():
    pytest.importorskip("numpy")                                                 # pretrain_set's t90
    from learn import ear_vreal as EV
    from learn import pretrain_set as PS

    close = next(iter(EV.CLOSE_VALUE))
    items = _items()
    worse = {"b0", "b1"}                                                         # the full arm loses to FTm in two bands
    got = {it["id"]: {"rank": dict(zip("ABCDE", (5, 3, 4, 2, 1) if it["cluster"] in worse else (5, 3, 1, 2, 4))),
                      "close": {k: close for k in "ABCDE"}} for it in items}
    rep = E.h4b_report(items, got, frozenset({"w-di"}), PS.t90)
    assert not rep["page_failed"] and len(rep["read"]) == 14
    jk = rep["primary"]["P2b-ftmf over FTm"]["jackknife"]
    assert jk["clusters"] == len({it["cluster"] for it in items}) == 5 and jk["df"] == 4      # by band, not by card
    assert jk == E.jackknife_t([(it["cluster"], float(it["cluster"] not in worse)) for it in items])
    assert jk["share"] == pytest.approx(8 / 14)
    assert rep["beside"]["never_heard_clean"]["cards"] == 8 and rep["beside"]["without_w_di"]["cards"] == 13
    assert set(rep["beside"]["arms_over_S_and_full_over_gentle"]) == {"P2b-ftmf over S", "P2b-ftmg over S", "P2b-ftmc over S",
                                                                         "P2b-ftmf over P2b-ftmg"}
    assert set(rep["j0"]) == {"all", "first_hearings_only", "heard_before_crunch_apart"}
    for i in (1, 2, 3):
        got[f"i{i}"] = {"scope": True}                                           # 3 out: the page still reads
    assert not E.h4b_report(items, got, frozenset(), PS.t90)["page_failed"]
    del got["i4"]                                                                # a fourth unfilled: the page fails
    assert E.h4b_report(items, got, frozenset(), PS.t90)["page_failed"]
    got["i5"] = {**got["i5"], "scope": True}
    with pytest.raises(SystemExit, match="both a scope mark and ranks"):
        E.h4b_report(items, got, frozenset(), PS.t90)


def test_h4b_read_needs_every_parts_answers_under_phase_h4(tmp_path, monkeypatch):
    pytest.importorskip("numpy")                                                 # numpy, or ear_eat's imports
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    d = tmp_path / E.WIDE_DIR / E.H4B_DIR
    d.mkdir(parents=True)
    (d / "key.json").write_text(json.dumps({"builds": ["b1", "b2"], "items": []}))
    f1 = tmp_path / "a1.json"
    f1.write_text(json.dumps({"build": "b1", "answers": {}}))
    _ledger(monkeypatch, have=(E.WIDE,))
    with pytest.raises(SystemExit, match=E.H4):
        E.cmd_h4b_read(argparse.Namespace(out=str(tmp_path / "o.json"), answers=[str(f1)]))
    _ledger(monkeypatch)
    with pytest.raises(SystemExit, match="every part"):
        E.cmd_h4b_read(argparse.Namespace(out=str(tmp_path / "o.json"), answers=[str(f1)]))
    f1.write_text(json.dumps({"build": "zz", "answers": {}}))
    with pytest.raises(SystemExit, match="build zz"):
        E.cmd_h4b_read(argparse.Namespace(out=str(tmp_path / "o.json"), answers=[str(f1)]))


def test_the_band_cap_binds_where_one_band_could_fill_a_class():
    units = [{"unit": f"a{j}", "player": "big", "cls": "clean", "di": f"s/a{j}.wav"} for j in range(10)]
    units += [{"unit": f"b{j}", "player": f"small{j}", "cls": "clean", "di": f"s/b{j}.wav"} for j in range(6)]
    units += [{"unit": f"c{j}", "player": f"cr{j % 3}", "cls": "crunch", "di": f"s/c{j}.wav"} for j in range(6)]
    cards = E.h4b_draw(units, set())
    assert sum(c["player"] == "big" for c in cards) == 2                       # 10 units in one band, 2 taken
    assert len([c for c in cards if c["cls"] == "clean"]) == 8


def test_t_sf_holds_near_zero_with_many_df():
    assert E.t_sf(0.01, 30) == pytest.approx(0.49604374628658887, abs=1e-12)  # scipy.stats.t.sf
    assert E.t_sf(0.01, 100) == pytest.approx(0.49602060511721424, abs=1e-12)
    assert E.t_sf(3.3, 13) == pytest.approx(0.002873859718615479, abs=1e-12)
