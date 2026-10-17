"""Multi-section matching (`learn/multi_section.py`, docs/multi-section-plan.md): the section
grid and activity rule, the tone curve, section roles and batches, the scores, the readout and
the yield rule. Synthetic signals and fake objectives; zero renders."""

import json
import math
import random

import pytest

np = pytest.importorskip("numpy")

from learn import knob_ceiling as K  # noqa: E402
from learn import multi_section as M  # noqa: E402

SR = M.SR


def test_grid_fits_whole_windows():
    n = int(32.3 * SR)
    g = M.grid(n)
    assert g == [0, 5 * SR, 10 * SR, 15 * SR, 20 * SR]
    assert all(s + 10 * SR <= n for s in g)
    assert M.grid(9 * SR) == []


def test_frames_in_matches_crop_rule_span():
    # crop rule 2: frames s//1024 .. (s + L - 2048)//1024 for s on the 0.5-s grid
    s, L = 24000, 480000
    r = M.frames_in(s, s + L, 10 ** 6)
    assert (r.start, r.stop) == (s // 1024 + (s % 1024 > 0), (s + L - 2048) // 1024 + 1)


def test_activity_and_pass_rule():
    x = np.zeros(30 * SR)
    rng = np.random.default_rng(0)
    x[:12 * SR] = rng.standard_normal(12 * SR)          # plays 0-12 s
    x[20 * SR:] = 1e-3 * rng.standard_normal(10 * SR)    # 60 dB down: does not play
    play = M.playing(M.frame_db(x))
    share, halves = M.section_activity(play, 0)
    assert share > 0.99 and M.passes(share, halves)
    share, halves = M.section_activity(play, 5 * SR)     # 5-15 s: plays 7 of 10 s
    assert 0.65 < share < 0.75 and not M.passes(share, halves)
    assert halves["A"] > 0.99 and 0.3 < halves["B"] < 0.37      # 10.5-15 s: plays 1.5 of 4.5 s
    share, _ = M.section_activity(play, 20 * SR)
    assert share == 0.0


def test_silence_never_plays():
    assert not M.playing(M.frame_db(np.zeros(SR))).any()


def test_disjoint_is_greedy_earliest():
    L = 10 * SR
    starts = [0, 5 * SR, 10 * SR, 25 * SR, 30 * SR, 35 * SR]
    assert M.disjoint(starts) == [0, 10 * SR, 25 * SR, 35 * SR]
    assert all(b - a >= L for a, b in zip(M.disjoint(starts), M.disjoint(starts)[1:]))


def test_tone_curve_sees_a_filter_and_ignores_level_and_lag():
    from scipy import signal

    rng = np.random.default_rng(1)
    di = rng.standard_normal(10 * SR)
    b, a = signal.butter(2, 1000, "lowpass", fs=SR)
    ref = 3.0 * signal.lfilter(b, a, di)
    c, lvl = M.tone_curve(ref, di)
    f = M.third_octaves()
    assert c[np.argmin(abs(f - 4000))] < c[np.argmin(abs(f - 200))] - 15     # the low-pass shows
    c2, lvl2 = M.tone_curve(0.5 * ref, di)                                   # level: offset only
    assert M.curve_distance(c, c2) < 1e-9 and abs((lvl - lvl2) - 20 * math.log10(2)) < 1e-6
    lagged = np.concatenate([np.zeros(500), ref[:-500]])                      # 500 samples later
    c3, _ = M.tone_curve(lagged, di, lag=500)
    assert M.curve_distance(c, c3) < 0.05
    same, _ = M.tone_curve(di, di)
    assert np.allclose(same, 0, atol=1e-9)


def test_snr():
    rng = np.random.default_rng(2)
    g = rng.standard_normal(SR)
    assert abs(M.snr_db(g, 0.1 * g) - 20) < 1e-9
    assert M.snr_db(np.zeros(5), g[:5]) == -math.inf


def test_choose_sections_spread_roles_and_determinism():
    starts = [float(5 * i) for i in range(20)]
    a = M.choose_sections("x", starts)
    assert a == M.choose_sections("x", starts)
    search, held = a
    assert len(search) == 3 and len(held) == 3 and not set(search) & set(held)
    used = sorted(search + held)
    assert used[0] == 0.0 and used[-1] == 95.0                              # spread over the song
    s4, h4 = M.choose_sections("x", [0.0, 10.0, 20.0, 30.0])
    assert len(s4) == 3 and len(h4) == 1
    others = {tuple(M.choose_sections(f"p{i}", starts)[0]) for i in range(10)}
    assert len(others) > 1                                                  # roles depend on the part


def test_batches_whole_bands_step3_first():
    by_band = {f"b{i}": [f"b{i}-p{j}" for j in range(1 + i % 3)] for i in range(12)}
    first = {s for i in range(6) for s in by_band[f"b{i}"]}
    bs = M.batches(by_band, first, size=5)
    flat = [s for b in bs for s in b]
    assert sorted(flat) == sorted(s for ss in by_band.values() for s in ss)
    # step 3's parts come first and never share a batch with the rest
    n_first = len(first)
    assert set(flat[:n_first]) == first
    for b in bs:
        assert len({s in first for s in b}) == 1
        bands = {s.split("-")[0] for s in b}
        for band in bands:                                                   # whole bands
            assert set(by_band[band]) <= set(b)
    assert bs == M.batches(by_band, first, size=5)


def test_section_score_and_held_gain():
    assert M.section_score({"A": math.e, "B": math.e ** 3}) == pytest.approx(2.0)
    assert M.section_score({"A": None, "B": 1.0}) == math.inf
    assert M.section_score({"A": math.inf, "B": 1.0}) == math.inf
    s0 = {"1": 0.0, "2": 1.0}
    assert M.held_gain({"1": -0.2, "2": 0.8}, s0, ["1", "2"]) == pytest.approx(-0.2)
    assert M.held_gain({"1": math.inf, "2": 0.8}, s0, ["1", "2"]) is None


def test_incumbents():
    trace = [(1, 5.0, "a"), (2, 4.0, "b"), (3, 4.5, "c"), (30, 3.0, "d"), (60, 3.5, "e")]
    inc = M.incumbents(trace, checkpoints=(2, 25, 50, 150))
    assert inc == {2: "b", 25: "b", 50: "d", 150: "d"}


def test_regrets():
    cross = {(i, j): float(i == j) * -1.0 + 0.1 * i for i in (1, 2, 3) for j in (1, 2, 3)}
    own = {j: cross[(j, j)] for j in (1, 2, 3)}
    r = M.regrets(cross, own)
    assert len(r) == 6 and all(v > 0 for v in r.values())


def test_unit_distance():
    dims = K.space("pr12")
    x = {(d.module, d.key): (d.values[0] if d.values else K.fmt(d.from_unit(0.2))) for d in dims}
    assert M.unit_distance(dims, x, x) == 0.0
    y = dict(x)
    d0 = next(d for d in dims if d.kind == "cont")
    y[(d0.module, d0.key)] = K.fmt(d0.from_unit(0.7))
    assert M.unit_distance(dims, x, y) == pytest.approx(0.5 / len(dims), rel=1e-3)


def test_amp_choice():
    inf = math.inf
    menu = {"pr12": {"a": {"flat": {"A": 2.0, "B": 2.0}}, "b": {"flat": {"A": inf, "B": inf}}},
            "sw50r": {"a": {"flat": {"A": 1.5, "B": 1.7}}},
            "ac20": {"a": {"flat": {"A": 1.9, "B": 1.5}}}}
    assert M.amp_choice(menu) == "sw50r"
    menu["pr12"]["b"]["flat"]["B"] = 0.1          # a preset with one refused half counts its finite half
    assert M.amp_choice(menu) == "pr12"
    none = {a: {"x": {"flat": {"A": inf, "B": inf}}} for a in ("pr12", "sw50r", "ac20")}
    assert M.amp_choice(none) == M.AMP_FALLBACK == "pr12"


def test_amp_choice_on_every_eligible_part():
    if not (M.HOME / "learn/label-table").exists() or not (M.OUT / "sections").exists():
        pytest.skip("stored menus or sections are not on this machine")
    bs, _, _ = M.plan_batches()
    for slug in (s for b in bs for s in b):
        menu = json.loads((M.HOME / "learn/label-table" / slug / "menu.json").read_text())
        assert M.amp_choice(menu) in ("pr12", "sw50r", "ac20")


def test_yield_rule_matches_rebuild_tone_renders_and_scoring_only():
    ps = [(1, "/x/.venv/bin/python -u -m learn.rebuild_tone render --stage tr1 --arms a --shard 0/3"),
          (2, "/x/.venv/bin/python -u -m learn.rebuild_tone score --workers 3"),
          (3, "/x/demucs-venv/bin/python -u -m learn.rebuild_tone_train train --fold 0 --arm stm --seed 0"),
          (4, "zsh learn/rebuild_tone_run.zsh"),
          (5, "/x/.venv/bin/python -u -m learn.multi_section run --worker 0/2 --batch 0"),
          (6, "/x/demucs-venv/bin/python -u -m learn.rebuild_tone_train gate --fold 0"),
          (7, "/x/demucs-venv/bin/python -u -m learn.rebuild_tone_train rebuild --arm stm")]
    assert M.must_yield(ps) == [1, 2, 6, 7]


def test_render_pattern_counted_machine_wide():
    from learn import local_objective as LO

    assert LO.is_render_process("/x/.venv/bin/python -u -m learn.multi_section run --worker 0/2 --batch 0")
    assert not LO.is_render_process("/x/.venv/bin/python -u -m learn.multi_section sections")


def test_part_readout_on_a_fake_result():
    s0 = {"10.0": 0.0, "30.0": 0.0, "50.0": 0.0, "70.0": 0.0, "90.0": 0.0}
    search, held = [10.0, 30.0, 50.0], [70.0, 90.0]

    def row(own_sec, own, other):
        return {str(s): (own if str(s) == own_sec else other) for s in search + held}

    table = {f"single{i}": {c: row(str(search[i - 1]), -0.3, -0.05) for c in map(str, M.CHECKPOINTS)}
             for i in (1, 2, 3)}
    table["multi"] = {c: {**{str(s): -0.2 for s in search}, **{str(s): -0.15 for s in held}}
                      for c in map(str, M.CHECKPOINTS)}
    res = {"table": table, "s_scores": s0, "held_sections": held, "search_sections": search}
    r = M.part_readout(res)
    assert r["multi"] == pytest.approx(-0.15) and r["single_mean"] == pytest.approx(-0.05)
    assert r["P"] == pytest.approx(-0.10)
    assert r["single_own"] == pytest.approx(-0.3) and r["single_other_search"] == pytest.approx(-0.05)
    assert r["regret_mean"] == pytest.approx(0.25) and r["transfer_worse_than_S"] == 0.0
    assert r["multi_own"] == pytest.approx(-0.2)


def test_pool_excludes_stage_f_and_is_development():
    ps = M.pool()
    assert not set(ps) & set(M.STAGE_F)
    assert set(M.step3_parts()) <= set(ps)
    assert all(p["gain_class"] in ("clean", "crunch") for p in ps.values())


def test_stage_f_list_matches_the_stored_report():
    path = M.HOME / "learn/arm-a-mega53/report-F.json"
    if not path.exists():
        pytest.skip("stage F's report is not on this machine")
    assert set(json.loads(path.read_text())["snr_db_htdemucs_instrumental"]) == set(M.STAGE_F)


def test_held_out_parts_never_in_the_pool():
    cat = json.loads((M.PLUGIN_ROOT / "docs/validation-datasets.json").read_text())
    held = {(s["source"], s["song"]) for s in cat["sessions"] if s.get("split") == "held_out"}
    for slug, p in M.pool().items():
        rec_path = M.pathlib.Path(p["crop"]) / "record.json"
        if not rec_path.exists():
            pytest.skip("crops are not on this machine")
        rec = json.loads(rec_path.read_text())
        assert (rec["source"], rec["song"]) not in held, slug


def test_knob_search_resumes_identically_from_a_cache():
    dims = K.space("pr12")
    x0 = {(d.module, d.key): (d.values[0] if d.values else K.fmt(d.from_unit(0.5))) for d in dims}
    rng = random.Random(0)
    w = {d.name: rng.uniform(-1, 1) for d in dims}

    def obj(x):
        return sum(w[d.name] * (d.to_unit(x[(d.module, d.key)]) if d.kind in ("cont", "log")
                                else float(x[(d.module, d.key)] in ("1", "true"))) for d in dims)

    calls = []

    def f(x):
        calls.append(K.key(x))
        return obj(x)

    a = K.knob_search(dims, x0, f, 40, M.SEED)
    cache = {}

    def g(x):
        k = K.key(x)
        if k not in cache:
            cache[k] = obj(x)
        return cache[k]

    b = K.knob_search(dims, x0, g, 40, M.SEED)
    assert a[1] == b[1] and K.key(a[0]) == K.key(b[0])


def _fake_result(slug, band, p_shift, cls="clean"):
    search, held = [10.0, 30.0, 50.0], [70.0, 90.0]
    s0 = {str(s): 0.0 for s in search + held}

    def row(own_sec, own, other):
        return {str(s): (own if str(s) == own_sec else other) for s in search + held}

    table = {f"single{i}": {c: row(str(search[i - 1]), -0.3, -0.05) for c in map(str, M.CHECKPOINTS)}
             for i in (1, 2, 3)}
    table["multi"] = {c: {str(s): -0.05 + p_shift for s in search + held} for c in map(str, M.CHECKPOINTS)}
    return {"slug": slug, "band": band, "gain_class": cls, "table": table, "s_scores": s0, "held_sections": held,
            "search_sections": search, "renders": 970, "repeat_dev": 0.0}


def test_part_readout_guards_refusals_and_reads_the_seed_floor():
    r = _fake_result("cambridge-a", "a", -0.1)
    r["table"]["single1b"] = {c: dict(r["table"]["single1"][c]) for c in r["table"]["single1"]}
    for c in r["table"]["single1b"]:
        r["table"]["single1b"][c]["10.0"] = -0.25          # its own section: 0.05 short of single1's
        r["table"]["single1b"][c]["30.0"] = -0.10          # on s2: 0.05 better than single1
    pr = M.part_readout(r)
    assert pr["seed_gap_own"] == pytest.approx(0.05)
    assert pr["seed_regret_change"] == pytest.approx(0.025)
    assert pr["single1b_held_minus_single1"] == pytest.approx(0.0)
    r["table"]["single2"]["150"]["10.0"] = math.inf          # a refused cross-section render
    pr = M.part_readout(r)
    assert pr["regret_mean"] is None and pr["transfer_worse_than_S"] is None and pr["single_other_search"] is None
    assert pr["P"] == pytest.approx(-0.1)                    # the held sections are untouched
    assert M.held_gaps(r) == [20.0, 40.0]


def test_report_and_decide(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "OUT", tmp_path)
    (tmp_path / "sections").mkdir()
    shifts = {"a": -0.100, "b": -0.101, "c": -0.099, "d": -0.110}
    for i, (band, sh) in enumerate(shifts.items()):
        slug = f"cambridge-{band}"
        (tmp_path / "parts" / slug).mkdir(parents=True)
        (tmp_path / "parts" / slug / "result.json").write_text(json.dumps(_fake_result(slug, band, sh)))
        tone = {str(s): [float(i + k) for k in range(3)] for s in (10.0, 30.0, 50.0)}
        rows = [{"start_s": float(s), "tone": t} for s, t in tone.items()]
        (tmp_path / "sections" / f"{slug}.json").write_text(json.dumps({"bleed_flag": "none (cambridge)", "rows": rows}))
    bad = _fake_result("telefunken-x", "x", 0.5)
    bad["repeat_failed"], bad["repeat_dev"] = True, 0.01
    (tmp_path / "parts" / "telefunken-x").mkdir()
    (tmp_path / "parts" / "telefunken-x" / "result.json").write_text(json.dumps(bad))
    out = M.report()
    assert out["parts"] == 4 and "telefunken-x" in out["dropped"]
    assert out["all"]["P"]["band_weighted_mean"] == pytest.approx(-0.1025)
    assert out["tone_vs_regret"]["all"]["pairs"] == 12 and out["P_none"] == []
    monkeypatch.setattr(M, "plan_batches", lambda: ([["a"], ["b"]], {}, {}))
    assert M.decide(0) is True                                   # half-width small: stop
    shifts_wide = {"a": -0.5, "b": 0.4, "c": -0.3, "d": 0.2}
    for band, sh in shifts_wide.items():
        slug = f"cambridge-{band}"
        (tmp_path / "parts" / slug / "result.json").write_text(json.dumps(_fake_result(slug, band, sh)))
    assert M.decide(0) is False and M.decide(1) is True           # wide: continue, unless the pool is spent
