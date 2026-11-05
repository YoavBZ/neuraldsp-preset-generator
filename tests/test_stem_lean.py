"""N8's pure parts (`learn/stem_lean.py`)."""

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import stem_lean as L  # noqa: E402


def _o(level, gain, dt=False, di="d"):
    return {"render_lufs": level, "gain_db": gain, "dt": dt, "di": di, "amp": "ac20", "settings": {"a/b": "1"}}


def test_the_dominant_other_is_the_loudest_and_never_a_double():
    a, b = _o(-20, -2), _o(-18, -8)
    assert L.dominant([a, b]) is a
    assert L.dominant([a, _o(-10, 0, dt=True)]) is None
    assert L.dominant([]) is None


def test_other_rows_carry_the_others_label_and_keep_the_section():
    rows = [{"i": 1, "amp": "pr12", "base": "clean", "section": "s", "label": {"amp": "pr12"}},
            {"i": 2, "amp": "pr12", "base": "clean", "section": "t", "label": {}}]
    render = {1: {"others": [_o(-20, 0, di="x")]}, 2: {"others": [_o(-20, 0, dt=True, di="y")]}}
    plan = {1: [{"di": "x", "draw": {"base": "crunch", "mode": "wide"}}], 2: [{"di": "y", "draw": "target"}]}
    pairs = L.other_rows(rows, render, plan)
    assert len(pairs) == 1
    t, o = pairs[0]
    assert t is rows[0] and (o["amp"], o["base"], o["section"], o["mode"]) == ("ac20", "crunch", "s", "wide")
    assert o["label"]["amp"] == "ac20" and o["label"]["settings"] == {"a/b": "1"}


def test_hits_read_the_top_answer():
    p = [[0.1, 0.7, 0.2], [0.5, 0.2, 0.3]]
    assert L.hits(p, ["b", "b"], ["a", "b", "c"]).tolist() == [1.0, 0.0]


def test_demeaning_and_the_two_correlations():
    assert L.demean([1.0, 3.0, 5.0, 9.0], ["x", "x", "y", "y"]).tolist() == [-1.0, 1.0, -2.0, 2.0]
    a = np.array([1.0, -1.0, 2.0, -2.0])
    assert L.group_rows(a, a, -a) == pytest.approx((1.0, -1.0))


def test_an_answer_that_only_knows_its_cell_reads_nothing():
    rng = np.random.default_rng(1)
    n = 3000
    cell = rng.integers(0, 6, n)
    sec = rng.integers(0, 12, n)
    level = rng.normal(0, 1, 6)
    answer = level[cell]                                     # no audio: the constant of T's own cell
    y_t = level[cell] + rng.normal(0, 1, n)
    y_o = rng.normal(0, 1, n)
    tc, sc = [str(c) for c in cell], [str(s) for s in sec]
    biased = L.group_rows(*(L.demean(v, sc) for v in (answer, y_t, y_o)))
    fair = L.group_rows(*(L.clean_of_cells(v, tc, sc) for v in (answer, y_t, y_o)))
    assert biased[0] - biased[1] > 0.4
    assert abs(fair[0] - fair[1]) < 0.1 or np.isnan(fair[0])


def test_the_jackknife_widens_with_the_sections_spread():
    s = np.repeat(np.arange(6), 3)
    r = L.jackknife(lambda k: 0.25, s, lambda df: 2.0)
    assert r["point"] == 0.25 and r["lo"] == r["hi"] == 0.25 and r["sections"] == 6
    v = np.repeat(np.array([0.0, 1.0, 0.0, 1.0, 0.0, 1.0]), 3)
    w = L.jackknife(lambda k: float(v[k].mean()), s, lambda df: 2.0)
    assert w["point"] == 0.5 and w["lo"] < 0.2 and w["hi"] > 0.8


def test_the_reading():
    up = {"lo": 0.01, "hi": 0.2}
    span = {"lo": -0.1, "hi": 0.1}
    down = {"lo": -0.2, "hi": -0.01}
    none = {"lo": None, "hi": None}
    assert L.reading(up, span, span, up, True) == "the lead holds"
    assert L.reading(up, span, up, up, True) == "the lead holds"                 # the stem adds to what the mix has
    assert L.reading(up, span, up, span, True) == "already in the mix"
    assert L.reading(up, span, span, span, True) == "not shown"                  # clear on the stem only, no gap shown
    assert L.reading(up, span, span, up, False) == "void"
    assert L.reading(span, up, span, up, True) == "not shown"
    assert L.reading(down, up, span, span, True) == "the lead does not hold"
    assert L.reading(down, span, span, span, True) == "not shown"
    assert L.reading(none, up, none, none, True) == "not shown"


def _settings(rng, amp):
    from learn import full_space as F
    from learn import knob_ceiling as K

    D = F.by_name()
    x = {}
    for n in F.CONT:
        d = D[n]
        x[(d.module, d.key)] = K.fmt(d.from_unit(rng.random()))
    for n in F.SW:
        d = D[n]
        if d.key != F.SPRING_KEY:
            x[(d.module, d.key)] = rng.choice(("true", "false"))
    for n in F.CAT:
        d = D[n]
        x[(d.module, d.key)] = rng.choice(list(F.MICS))
    x.update(F.FREE)
    for s in F.SECTIONS:
        x[(s, "sectionActive")] = "true"
    return F.label_of(x, amp)["settings"]


def test_a_reader_is_built_on_its_own_full_labels_and_constant():
    import random

    from learn import full_space as F

    rng = random.Random(3)

    def row(i, sec):
        amp, base = rng.choice(F.AMPS), rng.choice(("clean", "crunch"))
        return {"i": i, "section": sec, "amp": amp, "base": base, "settings": _settings(rng, amp), "label": {"today": 1}}

    tr = L.core_rows([row(i, f"s{i % 6}") for i in range(90)])
    fs = L.core_rows([row(100 + i, f"t{i % 3}") for i in range(30)])
    assert tr[0]["label"] == {"amp": tr[0]["amp"], "settings": tr[0]["settings"]}
    rows = tr + fs
    X = np.random.default_rng(4).normal(size=(len(rows), 12))
    S = L.prepared(tr, fs, {k: X for k in L.INPUTS}, {r["i"]: n for n, r in enumerate(rows)})
    assert S["const_tr"].shape == (90, len(F.CONT)) and S["X_of"]("c", fs).shape == (30, 12)
    assert S["X_of"]("cond", fs).shape == (30, 1) and S["lab_te"][6].shape == (30,)
    assert S["info"][100]["amp"] == fs[0]["amp"] and set(S["ids"]) == {r["i"] for r in fs}
    from learn import tone_info_probe as P

    p = P.fit_input(S, "c", tr, fs)[0]
    names = [r["name"] for r in L.read_rows(S, p)]
    assert len(names) == len(set(names)) and any(r["family"] == L.FAMILY for r in L.read_rows(S, p))


def test_the_summary_pass_reads_the_three_core_files(tmp_path, monkeypatch):
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    m = np.random.default_rng(5).integers(0, 255, (96, 446)).astype(np.uint8)
    np.savez(tmp_path / "g.npz", gA=m, gB=m)
    np.savez(tmp_path / "m.npz", mA=m // 2, mB=m // 2)
    np.savez(tmp_path / "s.npz", sA=m // 3, sB=m // 3)
    monkeypatch.setattr(PS, "example_path", lambda i: tmp_path / "g.npz")
    monkeypatch.setattr(T, "ex_path", lambda root, stage, i, kind: tmp_path / ("m.npz" if kind == "mix-t2" else "s.npz"))
    i, d = L._feats((None, 7))
    from learn import tone_info_probe as P

    assert i == 7 and set(d) == set(L.INPUTS) and d["a"].shape == (740,)
    assert np.allclose(d["b"], P.mel_summary({"A": m // 2, "B": m // 2}))
    assert not np.allclose(d["a"], d["c"])
