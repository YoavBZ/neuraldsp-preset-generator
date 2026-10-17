"""Part C's pure parts (`learn/pretrain_set.py`, `docs/pretrain-set-plan.md`)."""

import math
import random

import pytest

from learn import pretrain_set as M


def _inv(*recs):
    return {"dis": [dict(r) for r in recs]}


def _rec(di, band="Band A", split="library", ok=True, notes=(), mix=("a.wav",), source="cambridge"):
    return {"id": di, "path": f"/x/{di}", "band": band, "split": split, "training_ok": ok, "notes": list(notes),
            "mix": list(mix) if mix else None, "session_dir": "/x/s", "source": source}


def _row(di, start, band="Band A", clean=True, disjoint=True, split="library", ok=True, source="cambridge"):
    return {"di": di, "path": f"/x/{di}", "start_s": start, "band": band, "clean": clean, "disjoint": disjoint,
            "split": split, "training_ok": ok, "source": source}


def test_training_ok_matches_clean_di():
    pytest.importorskip("numpy")
    from learn import clean_di as CD

    inv = _inv(_rec("a"), _rec("b", split="known_answer", ok=False), _rec("c", ok=False))
    for path in ("/x/a", "/x/b", "/x/c", "/x/missing"):
        ok, _ = M.training_ok(path, inv)
        try:
            CD.assert_training_ok([path], inv)
            ref = True
        except (KeyError, ValueError):
            ref = False
        assert ok == ref, path


def test_pool_drops_the_hum_superset_guitar_techs_and_the_timezone():
    hum = sorted(M.HUM_SUSPECT)
    assert len(hum) == 11 and sum(h.startswith("guitar-techs/P1") for h in hum) == 7
    inv = _inv(_rec("a"), _rec(hum[-1]), _rec("gt", source="guitar-techs"), _rec("tz", band="Timo And The Timezone"),
               _rec("ka", split="known_answer", ok=False))
    man = {"sections": [_row("a", 0), _row(hum[-1], 0), _row("gt", 0, source="guitar-techs"),
                        _row("tz", 0, band="Timo And The Timezone"), _row("ka", 0, split="known_answer", ok=False),
                        _row("a", 10, clean=False), _row("a", 20, disjoint=False)]}
    seen = []
    rows, dropped = M.pool_rows(man, inv, refuse=lambda rec: seen.append(rec["id"]))
    assert [r["di"] for r in rows] == ["a"]
    assert seen == ["a"]
    assert dropped["hum-audit superset"] == 1 and dropped["Guitar-TECHS"] == 1
    assert dropped["band excluded (part B2 candidate)"] == 1


def test_pool_refuses_held_out_through_the_callback():
    inv = _inv(_rec("a"))
    man = {"sections": [_row("a", 0)]}

    def refuse(rec):
        raise ValueError("held out")

    with pytest.raises(ValueError):
        M.pool_rows(man, inv, refuse=refuse)


def test_gate_needs_a_positive_marker():
    old = M.PRE_AMENDMENT_SHA + "0" * 48
    new = "ab" * 32
    assert not M.hum_amended({"hum_amendment": "x"}, old, None)
    assert not M.hum_amended({}, new, None)
    assert not M.hum_amended({}, new, {"manifest_sha256": "cd" * 32})
    assert M.hum_amended({}, new, {"manifest_sha256": new})
    assert M.hum_amended({"hum_amendment": "2026-10-19"}, new, None)
    assert M.hum_amended({"version": 2, "amendments": [1, 2, 3]}, new, None)
    assert not M.hum_amended({"version": 1, "amendments": [1, 2]}, new, None)


def test_split_reserve_val_and_minimum_band_size():
    inv = _inv(*[_rec(f"d{b}", band=f"B{b}") for b in range(14)], _rec("sf", band="B0", notes=["stage F part (used once)"]))
    rows = [_row("sf", 0, band="B0")]
    sizes = {0: 40, 1: 30, 2: 25, 3: 2, 4: 6, 5: 7, 6: 8, 7: 9, 8: 10, 9: 6, 10: 6, 11: 7, 12: 8, 13: 1}
    for b, n in sizes.items():
        rows += [_row(f"d{b}", 10 * k, band=f"B{b}") for k in range(n)]
    split, val = M.split_pool(rows, inv, has_backing=lambda r: True)
    assert split[M.section_id(rows[0])] == "reserve"
    assert not {"B0", "B1", "B2"} & set(val)                # the three largest stay in train
    assert "B3" not in val and "B13" not in val              # under 5 sections
    rest = [r for r in rows if split[M.section_id(r)] != "reserve"]
    n_val = sum(split[M.section_id(r)] == "val" for r in rest)
    assert len(val) >= 8 or n_val >= 0.15 * len(rest)
    assert M.split_pool(rows, inv, has_backing=lambda r: True) == (split, val)


def test_section_for_uses_every_section_equally():
    n = 37
    got = [M.section_for(i, n) for i in range(5 * n)]
    assert sorted(got) == sorted(list(range(n)) * 5)
    assert got[:n] != list(range(n))
    assert M.section_for(1234, n) == M.section_for(1234, n)


def test_modes_and_plan_are_deterministic():
    assert M.mode_of(0.0) == "factory" and M.mode_of(0.39) == "factory"
    assert M.mode_of(0.41) == "start" and M.mode_of(0.61) == "wide" and M.mode_of(0.999) == "wide"
    counts = {"factory": 0, "start": 0, "wide": 0}
    for i in range(3000):
        _, amp, mode, base = M.plan_example(i)
        counts[mode] += 1
        assert amp in ("pr12", "sw50r", "ac20") and base in ("clean", "crunch")
    assert abs(counts["factory"] / 3000 - 0.4) < 0.04 and abs(counts["wide"] / 3000 - 0.4) < 0.04
    a, b = M.plan_example(77), M.plan_example(77)
    assert a[1:] == b[1:] and a[0].random() == b[0].random()


class _Dim:
    def __init__(self, module, key, kind, lo=0.0, hi=1.0, values=()):
        self.module, self.key, self.kind, self.lo, self.hi, self.values = module, key, kind, lo, hi, values

    @property
    def name(self):
        return f"{self.module}/{self.key}"

    def to_unit(self, v):
        return (min(max(float(v), self.lo), self.hi) - self.lo) / (self.hi - self.lo)

    def from_unit(self, u):
        return self.lo + min(max(u, 0.0), 1.0) * (self.hi - self.lo)


def _space(amp, S):
    return [_Dim("p", "gain", "cont", -20, 12), _Dim("a", "tone", "cont"), _Dim("a", "bright", "switch", values=("false", "true")),
            _Dim("c", "mic", "cat", values=tuple(str(i) for i in range(10)))]


MENU = {"pr12": {"S-clean": ("sel", {("p", "gain"): "0", ("a", "tone"): "0.5", ("a", "bright"): "false",
                                      ("c", "mic"): "3", ("x", "pedal"): "on"}),
                 "S-crunch": ("sel", {("p", "gain"): "6", ("a", "tone"): "0.7", ("a", "bright"): "true",
                                       ("c", "mic"): "4", ("x", "pedal"): "drive"}),
                 "Factory": ("sel2", {("p", "gain"): "-10", ("a", "tone"): "0.1", ("a", "bright"): "true",
                                      ("c", "mic"): "7", ("x", "pedal"): "fuzz"})}}
START = {"clean": {"pr12": "S-clean"}, "crunch": {"pr12": "S-crunch"}}


def test_settings_keep_the_base_modules_and_label_the_space():
    fmt = lambda v: f"{v:.6g}"  # noqa: E731
    for mode in ("factory", "start", "wide"):
        for seed in range(20):
            sel, x, label, cname = M.settings_for(random.Random(seed), "pr12", mode, "clean", MENU, START, _space, fmt)
            assert sel == "sel" and x[("x", "pedal")] == "on"              # S's other modules, S's select
            assert set(label) == {"p/gain", "a/tone", "a/bright", "c/mic"}
            assert 0.0 <= label["a/tone"] <= 1.0 and x[("a", "bright")] in ("false", "true")
            assert (cname is None) == (mode == "wide")


def test_factory_mode_centres_on_the_factory_preset():
    fmt = lambda v: f"{v:.6g}"  # noqa: E731
    keep = 0
    tones = []
    for seed in range(300):
        rng = random.Random(seed)
        sel, x, label, cname = M.settings_for(rng, "pr12", "factory", "crunch", MENU, START, _space, fmt, sigma=0.0)
        if cname == "Factory":
            tones.append(label["a/tone"])
            keep += x[("c", "mic")] == "7"
    assert tones and all(abs(t - 0.1) < 1e-9 for t in tones)
    assert 0.6 < keep / len(tones) < 0.85                                # kept with p 0.7 (+ chance hits)


def test_quantiser_round_trip():
    np = pytest.importorskip("numpy")
    x = np.linspace(-130, 20, 1001)
    q = M.quant(x)
    back = M.dequant(q)
    inside = (x >= M.Q_LO_DB) & (x <= M.Q_LO_DB + 255 * M.Q_STEP_DB)
    assert np.max(np.abs(back[inside] - x[inside])) <= 0.25 + 1e-6
    assert q.dtype == np.uint8 and q.min() == 0 and q.max() == 255


def test_powersum_and_mix_gains():
    np = pytest.importorskip("numpy")
    g, b = np.array([-20.0, -60.0]), np.array([-30.0, -30.0])
    out = M.powersum_db(g, b, 0.0, 0.0)
    assert np.allclose(out, 10 * np.log10(10 ** (g / 10) + 10 ** (b / 10)))
    gb, gl, ga = M.mix_gains_db(-20.0, -25.0, -8.0, 3.0, -12.0)
    assert math.isclose(-20.0 - (-25.0 + gb), -8.0) and math.isclose(-20.0 - (-25.0 + gl), 3.0)
    assert math.isclose(M.db_sum(-20.0, -25.0 + gb) + ga, -12.0)


def test_ratio_draw_is_band_weighted():
    ratios = {"big": [-1.0] * 1000, "small": [-20.0]}
    got = [M.mix_params(i, ratios, True, -12.0)[0] for i in range(2000)]
    share = sum(v == -20.0 for v in got) / len(got)
    assert 0.4 < share < 0.6
    assert M.mix_params(5, ratios, False, -12.0)[1] is False


def test_backing_tracks():
    pytest.importorskip("numpy")
    rec = {"mix": ["01_Kick.wav", "05_ElecGtr1.wav", "06_ElecGtr1DI.wav", "07_ElecGtr2.wav", "09_LeadVox.wav", "10_Bass.wav"],
           "own": ["05_ElecGtr1.wav"], "vocals": ["09_LeadVox.wav"]}
    withv, nov = M.backing_tracks(rec, [], leaking=["10_Bass.wav"])
    assert withv == ["01_Kick.wav", "07_ElecGtr2.wav", "09_LeadVox.wav"]
    assert nov == ["01_Kick.wav", "07_ElecGtr2.wav"]
    rec2 = {"mix": None, "own": [], "vocals": None}
    w2, n2 = M.backing_tracks(rec2, ["01_Drums.wav", "02_GtrDI.wav", "03_Vox1.wav", "readme.txt"])
    assert w2 == ["01_Drums.wav", "03_Vox1.wav"] and n2 == ["01_Drums.wav"]


def test_band_interval_and_decisions():
    m, lo, hi, n = M.band_t_interval({"a": [-0.02, -0.03], "b": [-0.01], "c": [-0.02]})
    assert n == 3 and lo < m < hi and math.isclose(m, (-0.025 - 0.01 - 0.02) / 3)
    assert M.decide((-0.02, -0.03, -0.01, 8)) == "EXTEND"
    assert M.decide((-0.02, -0.05, 0.01, 8)) == "STOP"
    neg = (-0.02, -0.03, -0.01, 8)
    pos = (-0.02, -0.05, 0.01, 8)
    assert M.decide_full({"avg": neg, "1": neg, "2": neg}, -0.05) == ("EXTEND", "improving")
    assert M.decide_full({"avg": neg, "1": neg, "2": pos}, -0.05)[0] == "STOP"
    assert M.decide_full({"avg": (-0.001, -0.004, 0.002, 8)}, -0.03) == ("STOP", "flat")
    assert M.decide_full({"avg": (-0.01, -0.04, 0.02, 8)}, -0.03) == ("STOP", "undecided")


def test_curve_runs_and_table():
    runs = M.curve_runs(40_000)
    labels = [(r[0], r[2]) for r in runs]
    assert ("5000", 20261044) not in labels and ("20000", 20261044) in labels
    assert ("20000-halfsec", 20261042) in labels
    assert max(r[1] for r in runs if not r[3]) == 40_000
    assert max(r[1] for r in M.curve_runs(80_000) if not r[3]) == 80_000
    res = {"runs": {}}
    band_of = {"1": "a", "2": "a", "3": "b", "4": "c"}
    for n, base in ((10_000, 0.20), (20_000, 0.15)):
        for k, s in enumerate((7, 8)):
            res["runs"][f"{n}-{s}"] = {"n": n, "seed": s, "per_example": {i: base + 0.01 * k + 0.001 * int(i) for i in band_of}}
    E, d = M.curve_table(res, band_of, set(band_of))
    assert set(E) == {10_000, 20_000}
    assert math.isclose(d["10000->20000"]["avg"][0], -0.05, abs_tol=1e-9)
    assert set(d["10000->20000"]) == {"avg", "7", "8"}
    E2, _ = M.curve_table(res, band_of, {"1", "2"})
    assert E2[10_000][3] == 1


def test_beyond_threshold():
    rows = [{"amp": "pr12", "mode": "start", "base": "crunch", "gain": {"slope": s}} for s in (0.0, 0.1, 0.2, 0.3, 0.4,
                                                                                               0.5, 0.6, 0.7, 0.8, 0.9, 1.0)]
    thr = M.beyond_threshold(rows + [{"amp": "pr12", "mode": "wide", "base": "crunch", "gain": {"slope": -5}}])
    assert math.isclose(thr["pr12"], 0.1)
    assert M.is_beyond({"amp": "pr12", "gain": {"slope": 0.05}}, thr)
    assert not M.is_beyond({"amp": "pr12", "gain": {"slope": 0.1}}, thr)
    assert not M.is_beyond({"amp": "sw50r", "gain": {"slope": -1}}, thr)


def test_disk_guard_and_shards():
    assert not M.disk_ok(31.0, free=30.9) and M.disk_ok(31.0, free=31.0)
    ids = M.example_ids(10, 4)
    assert ids[-1] == M.VAL_BASE + 3
    parts = [M.shard_ids(ids, (k, 3)) for k in range(3)]
    assert sorted(sum(parts, [])) == sorted(ids)


def test_read_rows_cuts_a_torn_last_line(tmp_path):
    f = tmp_path / "shard-0.jsonl"
    f.write_text('{"i": 1}\n{"i": 2}\n{"i": 3, "x"')
    assert [r["i"] for r in M.read_rows(f)] == [1, 2]
    assert f.read_text().endswith('"x"')
    assert [r["i"] for r in M.read_rows(f, repair=True)] == [1, 2]
    assert f.read_text() == '{"i": 1}\n{"i": 2}\n'
    with open(f, "a") as fh:
        fh.write('{"i": 4}\n')
    assert [r["i"] for r in M.read_rows(f)] == [1, 2, 4]
    f.write_text('{"i": 1}\nbroken\n{"i": 2}\n')
    with pytest.raises(Exception):
        M.read_rows(f)


def test_quiet_backing_gain_is_capped():
    gb, gl, ga = M.mix_gains_db(-20.0, -70.0, -8.0, 3.0, -12.0)
    assert gb <= 40.0 + 8.0
