"""Experiment 1d (`learn/local_objective_1d.py` and its DIs in `learn/local_objective.py`;
docs/local-objective-plan.md, amendments 4 and 4a): the separator-robust rebuild's DIs, the network
pins and leak checks, the identity check, the comparator renders, and the report. Fakes, plus a
check of the real networks against their pins and pools (zero renders)."""

import json
import pathlib
import random

import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import knob_ceiling as K  # noqa: E402
from learn import local_objective as M  # noqa: E402
from learn import local_objective_1c as C  # noqa: E402
from learn import local_objective_1d as D  # noqa: E402

ST, MG = M.SEPNET_DI["stem"], M.SEPNET_DI["mega53"]


# --- the DIs -----------------------------------------------------------------------------------------------

def test_sepnet_dis_configs_and_lags():
    assert (ST, MG) == ("csep_stem", "csep_mega53")
    for d, src, other in ((ST, "stem", "mega53"), (MG, "mega53", "stem")):
        assert d in M.REBUILT and d in M.NO_STORED and M.REBUILD_SOURCE[d] == src
        assert M.configs(d) == [(d, src, "native", "own"), (d, src, "gcc", "own"), (d, other, "native", "own")]
        assert M.native_config(d) == (d, src, "native", "own")
        assert M.lag_value("native", d, 914) == -52
    assert M.REBUILD_DIR[ST] == "rebuilt-csep-stem" and M.REBUILD_DIR[MG] == "rebuilt-csep-mega53"
    assert M.configs(M.SEP_DI["mega53"])[0] == ("cprime_mega53", "mega53", "native", "own")   # 1c unchanged
    assert len(M.configs("cprime")) == 16


def test_render_refuses_sepnet_without_checks(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "OUT", tmp_path)
    monkeypatch.setattr(M, "load_sigma", lambda: ({"hash": M.SIGMA_HASH}, {}))
    with pytest.raises(SystemExit, match="local_objective_1d"):
        M.cmd_render((0, 3), di_name=f"{ST},{MG}")
    (tmp_path / "rebuilt-csep-stem").mkdir()
    (tmp_path / "rebuilt-csep-stem" / "check.json").write_text(json.dumps({"ok": True}))
    assert M.rebuilds_ok(ST) and not M.rebuilds_ok(MG)


def test_part_signals_for_both_cells(tmp_path, monkeypatch):
    import numpy as np

    from learn import confirm_run as CR
    from learn import song_settings as SS

    monkeypatch.setattr(M, "OUT", tmp_path)
    monkeypatch.setattr(K, "parts", lambda: {"p": {"crop": tmp_path}})
    monkeypatch.setattr(SS, "stem", lambda slug: np.full(4, 2.0))
    monkeypatch.setattr(CR, "mono", lambda path: np.full(4, 3.0))
    (tmp_path / "sep" / "mega53" / "crop").mkdir(parents=True)
    np.save(tmp_path / "sep" / "mega53" / "crop" / "p.npy", np.full(4, 5.0, np.float32))
    for d, v in (("rebuilt-csep-stem", 8.0), ("rebuilt-csep-mega53", 9.0)):
        (tmp_path / d).mkdir()
        np.save(tmp_path / d / "p.npy", np.full(4, v))
    s, _ = M.part_signals("p", ST)
    assert s["di"][0] == 8.0 and s["stem"][0] == 2.0 and s["mega53"][0] == 5.0
    s, _ = M.part_signals("p", MG)
    assert s["di"][0] == 9.0 and s["mega53"][0] == 5.0


# --- 4a: pins, pools, identity ----------------------------------------------------------------------------

def _net(tmp_path, fold=1, resume=None, train=("a|x",), val=("b|x",)):
    from learn import song_settings as SS

    d = tmp_path / f"models-sep-f{fold}"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"fold{fold}.pt").write_bytes(b"net")
    cfg = {"fold": fold, "resume": str(resume or SS.cprime(fold)), "caches": [str(tmp_path / "cache")],
           "sep": {"train": list(train), "val": list(val)}}
    (d / "config.json").write_text(json.dumps(cfg))
    rows = [{"id": "a|x", "band": "Band A"}, {"id": "b|x", "band": "Band B"}, {"id": "c|x", "band": "Band C"}]
    return d / f"fold{fold}.pt", rows


def test_library_bands_and_pool_union(tmp_path):
    path, rows = _net(tmp_path)
    cfg = json.loads((path.parent / "config.json").read_text())
    assert D.library_bands(cfg, rows) == {"Band A", "Band B"}
    calls = []

    def pool_of(fold, caches):
        calls.append([pathlib.Path(c).name for c in caches])
        return {"Parent"} if len(caches) == 3 else {"Own"}
    assert D.sepnet_pool(cfg, 1, rows, pool_of) == {"Parent", "Own", "Band A", "Band B"}
    assert calls[0] == ["cache", "cache-sw50r", "cache-ac20"] and calls[1] == ["cache"]   # C′'s three caches
    with pytest.raises(AssertionError, match="no library entries"):
        D.library_bands({"sep": {}}, rows)


def test_assert_sepnet_ok(tmp_path, monkeypatch):
    path, rows = _net(tmp_path)
    pool_of = lambda fold, caches: {"Parent"} if len(caches) == 3 else set()  # noqa: E731
    sha = lambda p: D.SEPNET_SHA256[1]  # noqa: E731
    D.assert_sepnet_ok("Band C", path, 1, rows, pool_of, sha)
    for band in ("Band A", "Band B", "Parent"):
        with pytest.raises(AssertionError, match="leak"):
            D.assert_sepnet_ok(band, path, 1, rows, pool_of, sha)
    with pytest.raises(AssertionError, match="pinned"):
        D.assert_sepnet_ok("Band C", path, 1, rows, pool_of, lambda p: "0" * 64)
    with pytest.raises(AssertionError, match="fine-tuned for fold"):
        D.assert_sepnet_ok("Band C", path, 2, rows, pool_of, lambda p: D.SEPNET_SHA256[2])
    p3, _ = _net(tmp_path / "x", fold=1, resume="/elsewhere/fold1.pt")
    with pytest.raises(AssertionError, match="resumed from"):
        D.assert_sepnet_ok("Band C", p3, 1, rows, pool_of, sha)


def test_identity_problems():
    assert D.identity_problems({"a": 0.0, "b": 5e-7}) == {}
    assert D.identity_problems({"a": 2e-6, "b": None, "c": float("nan")}).keys() == {"a", "b", "c"}


def test_rebuild_refuses_on_a_failed_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "OUT", tmp_path)
    monkeypatch.setattr(D, "cmd_identity", lambda src: False)
    monkeypatch.setattr(C, "sep_ok", lambda sep: True)
    with pytest.raises(SystemExit, match="reproduce the stored rebuild"):
        D.cmd_rebuild("stem")
    assert json.loads((tmp_path / "rebuilt-csep-stem" / "check.json").read_text())["ok"] is False
    assert not M.rebuilds_ok(ST)


# --- 4a: the comparator ------------------------------------------------------------------------------------

def test_comparator_check(tmp_path, monkeypatch):
    import numpy as np

    monkeypatch.setattr(M, "OUT", tmp_path)
    monkeypatch.setattr(M, "part_signals", lambda slug, d: ({"di": np.zeros(4)}, {"judge_lag": 900}))
    calls = []

    class R:
        def render(self, x, sel, setting):
            calls.append(setting)
            return 2.0

    def fake_score(y, di, sig, jl, aligned, gcc=None, only=None):
        assert di == "cprime" and only == {M.CURRENT}
        return {M.cname(M.CURRENT): {"A": y, "B": y * 1.01}}, {}
    monkeypatch.setattr(M, "score_render", fake_score)
    p = tmp_path / "scores" / "cprime" / "s" / "pr12.json"
    p.parent.mkdir(parents=True)
    stored = [{M.cname(M.CURRENT): {"A": 9.0, "B": 9.0}}, {M.cname(M.CURRENT): {"A": 2.0, "B": 2.0}}]
    p.write_text(json.dumps({"scores": stored}))
    pts = [{"source": "nbr", "x": "n"}, {"source": "S", "x": "s"}]
    c = M.comparator_check(R(), "sel", "s", "pr12", pts, None)
    assert calls == ["s", "s"] and c["index"] == 1 and c["renders"] == 2
    assert c["devs"]["A"] == 0.0 and c["max_dev"] == pytest.approx(np.log(1.01))


# --- the report ---------------------------------------------------------------------------------------------

def test_report_on_fake_scores(tmp_path, monkeypatch):
    """A perfect 1d rebuild (its objective is the truth) beats today's objective and 1c's cell; the
    primaries are refused on an incomplete set; the shares, the interaction, the bleed rows and the
    comparator summary are present."""
    monkeypatch.setattr(M, "OUT", tmp_path)
    rng = random.Random(5)
    srcs = ["S"] + ["nbr"] * 5 + ["ks"] * 4 + ["armA"] * 2
    ps, sig, cells = {}, {}, {}
    for i in range(8):
        slug = f"p{i}"
        ps[slug] = {"band": f"b{i % 6}", "gain_class": "clean"}
        for amp in ("pr12", "sw50r"):
            pts = [{"source": s, "key": f"{slug}{amp}{j}"} for j, s in enumerate(srcs)]
            sig[(slug, amp)] = pts
            cells[f"{slug}|{amp}"] = pts
            true = [{"A": 1 + j + rng.random(), "B": 1 + j + rng.random()} for j in range(len(srcs))]
            noisy = lambda s: [{h: t[h] + rng.gauss(0, s) for h in "AB"} for t in true]  # noqa: E731
            mega = M.SEP_DI["mega53"]
            files = {"measure": {M.cname(M.TRUE): true}, "cprime": {M.cname(M.CURRENT): noisy(6.0)},
                     M.MATCHED_DI: {M.cname(M.MATCHED): noisy(1.5)},
                     mega: {f"{mega}|mega53|native|own": noisy(3.0), f"{mega}|stem|native|own": noisy(4.0)},
                     "cprime@mega53": {"cprime|mega53|native|own": noisy(3.0)},
                     ST: {f"{ST}|stem|native|own": noisy(2.0), f"{ST}|stem|gcc|own": noisy(2.0),
                          f"{ST}|mega53|native|own": noisy(2.0)}}
            if i < 6:                                                    # csep_mega53 only on 12 of 16 cells
                files[MG] = {f"{MG}|mega53|native|own": noisy(0.0), f"{MG}|mega53|gcc|own": noisy(0.5),
                             f"{MG}|stem|native|own": noisy(4.0)}
            for d, cfg in files.items():
                p = tmp_path / "scores" / d / slug / f"{amp}.json"
                p.parent.mkdir(parents=True, exist_ok=True)
                scores = [{c: v[j] for c, v in cfg.items()} for j in range(len(srcs))]
                extra = {"flac_vs_float_S": {f"{d}|x": {"A": 1e-6, "B": 3e-6}}} if d in (ST, MG) else {}
                p.write_text(json.dumps({"scores": scores, **extra}))
            for d in (ST, MG):
                if d == MG and i >= 6:
                    continue
                r = tmp_path / "renders" / d / slug / f"{amp}.json"
                r.parent.mkdir(parents=True, exist_ok=True)
                comp = {"comparator": {"renders": 2, "max_dev": 1e-4}} if d == ST else {}
                r.write_text(json.dumps({"renders": len(srcs) + 1, **comp}))
    monkeypatch.setattr(M, "load_sigma", lambda: ({"hash": M.SIGMA_HASH, "cells": cells}, sig))
    monkeypatch.setattr(K, "parts", lambda: ps)
    monkeypatch.setattr(C, "load_bleed_table", lambda: {
        f"p{i}": {"source": "cambridge" if i < 5 else "telefunken",
                  "halves": {"A": {"flag": "high" if i == 7 else "low"}, "B": {"flag": "low"}}} for i in range(8)})
    D.cmd_report()
    rep = json.loads((tmp_path / "report-1d.json").read_text())
    a = rep["subsets"]["all"]
    assert rep["cells"] == 16
    assert a["sepnet_mega53"]["cross_half"]["cells"] == 12 and a["sepnet_stem"]["cross_half"]["cells"] == 16
    assert a["P2_sepnet_mega53_minus_mega53"]["cross_half"]["band_weighted_mean"] > 0
    assert a["P1_sepnet_stem_minus_current"]["cross_half"]["band_weighted_mean"] > 0
    assert a["interaction_P2_minus_P1"]["cross_half"]["cells"] == 12
    assert set(a["shares"]["cross_half"]) == set(D.SHARES)
    for dn in D.PRIMARY:
        assert rep["primary"][dn]["refused"].startswith("16 cells") or rep["primary"][dn]["refused"].startswith("12 cells")
    assert rep["status"][ST]["renders_used"] == 16 * 13 and rep["status"][MG]["renders_used"] == 12 * 13
    assert rep["status"][ST]["flac_vs_float_S"]["n"] == 32 and rep["status"][ST]["flac_vs_float_S"]["over_tol"] == 0
    assert rep["comparator"] == {"cells": 16, "renders": 32, "max_dev": 1e-4, "over_tol": 0}
    assert rep["renders_used"] == 16 * 13 + 12 * 13 + 32
    assert set(rep["subsets"]) == {"all", "neighbourhood", "ks", "armA", "without_armA"}
    rows = rep["bleed_and_leak_rows"]
    assert set(rows) == set(C.ROWS)
    assert rows["all"]["P1_sepnet_stem_minus_current"]["band_weighted_mean"] == pytest.approx(
        a["P1_sepnet_stem_minus_current"]["cross_half"]["band_weighted_mean"])
    assert rows["no_high"]["P1_sepnet_stem_minus_current"]["cells"] == 14
    assert len(rep["per_band_cross_half"]) == 6


def test_complete():
    assert D.complete(72, 3528) is None
    assert D.complete(72, 3529).startswith("72 cells and 3529")


# --- the real networks (zero renders) -----------------------------------------------------------------------

def test_real_networks_match_their_pins_and_are_leak_free():
    from learn import song_settings as SS

    paths = {f: D.net_path(f) for f in range(4)}
    if not all(p.exists() for p in paths.values()):
        pytest.skip("the separator-robust networks are not on this machine")
    lib = json.loads((paths[0].parent.parent / "lib.json").read_text())["rows"]
    fo = SS.folds()
    for slug, part in sorted(K.parts().items()):
        if slug in M.EXCLUDED:
            continue
        f = fo[part["band"]]
        D.assert_sepnet_ok(part["band"], paths[f], f, lib)


def test_level_check_against_the_comparator():
    """Amendment 4b: magilla's 1d stem rebuild (−23.020) sits 0.002 LU from C′'s (−23.018)."""
    assert M.rebuild_ref_problems(0, -23.020, target=-23.018) == []
    assert M.rebuild_ref_problems(0, -23.020) != []                    # 2a's absolute target would stop it
    assert M.rebuild_ref_problems(0, -22.80, target=-22.9) != []
