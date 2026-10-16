"""The arms, training and evaluation (`learn/song_soundspace.py`, docs/song-to-settings-soundspace-plan.md):
the censored head and the losses (B1 equals B0 at weights 1; the set loss is mode-seeking), the
right-cab mask in the members, the fold rule and the record-like weight, B0's dry run and the
memory gate, the refusal rule, E1's unit lists and the provisional decider, E2's scores, C-fine,
and the approval gates and caps. Synthetic inputs only; the torch tests need the torch interpreter."""

import json
import math
import random

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import knob_ceiling as K  # noqa: E402
from learn import song_relabel as RL  # noqa: E402
from learn import song_soundspace as SP  # noqa: E402

INF = math.inf


def S_for(amp, right="true"):
    S = {("cabParameters", "leftCabActive"): "true"}
    for d in K.space(amp, S):
        S[(d.module, d.key)] = K.fmt(d.from_unit(0.5)) if d.kind in ("cont", "log") else d.values[0]
    S[("cabParameters", "rightCabActive")] = right
    return S


def bank_label(amp, seed, right="true"):
    from learn import song_diag as D

    S = S_for(amp, right)
    _, lab = D.broad(K.space(amp, S), S, random.Random(seed))
    lab[RL.RIGHT_ACTIVE] = right
    return lab


# ------------------------------------------------------------------------------ gates and caps

def test_c_start_is_offered_only_after_E3_chose_B1_or_B2_and_needs_its_yes():
    for chosen in ("S", "constant", "B0"):
        with pytest.raises(SystemExit):
            SP.c_start_allowed({"chosen": chosen}, True)
    with pytest.raises(SystemExit):
        SP.c_start_allowed({"chosen": "B2"}, False)
    with pytest.raises(SystemExit):
        SP.c_start_allowed(None, True)
    assert SP.c_start_allowed({"chosen": "B1"}, True) == "B1"


def test_optional_arms_need_their_own_yes():
    SP.arm_allowed("B1", False)
    SP.arm_allowed("B2", False)
    for arm in ("B1r", "B2a"):
        with pytest.raises(SystemExit):
            SP.arm_allowed(arm, False)
        SP.arm_allowed(arm, True)
    with pytest.raises(SystemExit):
        SP.arm_allowed("B3", True)


def test_songs_steps_need_the_songs_yes(monkeypatch):
    for fn, args in ((SP.cmd_bridge, (False,)), (SP.cmd_songs_top, (False,)), (SP.cmd_report_2, (False,)),
                     (SP.cmd_songs_more, (False, False)), (SP.cmd_score_songs, ("top", False, (0, 1)))):
        with pytest.raises(SystemExit):
            fn(*args)


def test_caps_match_the_plan():
    assert SP.CAPS == {"e1": 4350, "e1_b2a": 1450, "e3": 1750, "cfine": 450, "b0best8": 1150, "c_start": 7650}
    SP.check_cap("e3", 1700, 50)
    with pytest.raises(SystemExit):
        SP.check_cap("e3", 1700, 51)


def test_seeds_are_distinct_for_E1_and_E3():
    assert SP.SEED_E1 == 20261029 and SP.SEED_E3 == 20261030
    a = SP.e1_sample_rng(3, "1b", "A").random()
    assert a == SP.e1_sample_rng(3, "1b", "A").random() and a != SP.e1_sample_rng(3, "1b", "B").random()
    assert SP.ARM_SPEC["B1"]["seed"] == SP.ARM_SPEC["B2"]["seed"] == 20261018
    assert SP.ARM_SPEC["B1r"]["seed"] == 20261031


# ------------------------------------------------------------------------------ memory

def test_peak_rss_units():
    assert SP.peak_rss_bytes(2048, "Darwin") == 2048
    assert SP.peak_rss_bytes(2048, "Linux") == 2048 * 1024


def test_beside_ok_keeps_six_gb_with_three_render_processes():
    assert SP.beside_ok(20e9, 2e9)                     # 20 + 6 + 6 = 32
    assert not SP.beside_ok(20.1e9, 2e9)


def test_parse_ps_rss_finds_render_shards_only():
    text = ("  1048576 python -m learn.song_relabel probe --shard 0/3\n"
            "   512000 python -m learn.song_soundspace train --arm B1 --fold 0\n"
            "  2097152 /usr/bin/python -m learn.song_soundspace score-targets --arm B1 --shard 1/3\n")
    assert SP.parse_ps_rss(text) == [1048576 * 1024, 2097152 * 1024]


def synthetic_idx(tmp_path, n_bands=6, per_band=4, frames=12):
    idx = []
    i = 0
    for b in range(n_bands):
        for k in range(per_band):
            amp = K.AMPS[i % 3]
            S = S_for(amp)
            from learn import song_diag as D
            _, lab = D.broad(K.space(amp, S), S, random.Random(i))
            fold = b % 4
            band = f"band{b}" if b < n_bands - 1 else "Guitar-TECHS P1"
            idx.append((i, fold, band, amp, "clean", lab))
            np.savez(tmp_path / f"{i}.npz", featA=np.full((2, 96, frames), -40, np.float16),
                     featB=np.full((2, 96, frames), -30, np.float16), lufsA=np.array([-20, -14], np.float32),
                     lufsB=np.array([-21, -15], np.float32))
            i += 1
    return idx


def test_b0_dry_run_records_peak_rss_and_uses_b0s_split(tmp_path):
    idx = synthetic_idx(tmp_path)
    rep = SP.dry_run_b0(0, idx, lambda i: tmp_path / f"{i}.npz", tmp_path / "mem" / "B0-dry-fold0.json")
    stored = json.loads((tmp_path / "mem" / "B0-dry-fold0.json").read_text())
    assert stored == rep and rep["peak_rss_bytes"] > 0
    tr, va, vb = SP.b0_split(idx, 0)
    assert rep["train_rows"] == len(tr) and rep["val_rows"] == len(va) and rep["val_bands"] == sorted(vb)
    assert rep["train_bytes"] == 2 * len(tr) * 2 * 96 * 12 * 4
    assert not any(r[1] == 0 for r in tr + va)
    assert not any(b.startswith("Guitar-TECHS") for b in vb)


def test_b0_split_matches_the_stored_validation_bands():
    from learn import song_model as M

    if not (SP.B0_MODELS / "fold0" / "log.json").exists() or not (M.B.OUT / "examples.json").exists():
        pytest.skip("the bank is not on this machine")
    idx = M.bank_index()
    for f in range(4):
        _, _, vb = SP.b0_split(idx, f)
        assert sorted(vb) == json.loads((SP.B0_MODELS / f"fold{f}" / "log.json").read_text())["val_bands"]


# ------------------------------------------------------------------------------ rows, weights, members

def test_split_rows_keeps_model_f_off_fold_f_and_uses_b0s_val_bands():
    rows = [{"i": i, "fold": i % 4, "band": f"b{i % 7}"} for i in range(40)]
    tr, va = SP.split_rows(rows, 2, {"b1", "b3"})
    assert not any(r["fold"] == 2 for r in tr + va)
    assert {r["band"] for r in va} <= {"b1", "b3"} and not {r["band"] for r in tr} & {"b1", "b3"}
    assert len(tr) + len(va) == sum(r["fold"] != 2 for r in rows)


def test_record_weight_gives_ks_centred_rows_half_the_loss():
    rows = [{"ks": i % 4 == 0} for i in range(103)]
    w = SP.record_weights(rows)
    ks = sum(x for x, r in zip(w, rows) if r["ks"])
    other = sum(x for x, r in zip(w, rows) if not r["ks"])
    assert ks == pytest.approx(other)
    assert SP.record_weights([{"ks": False}] * 3) == [1.0] * 3


def test_is_ks_centred():
    assert SP.is_ks_centred({"mode": "jitter", "centre": "/x/K_S-A.json"})
    assert not SP.is_ks_centred({"mode": "jitter", "centre": "S"})
    assert not SP.is_ks_centred({"mode": "broad", "centre": None})


def test_encode_member_applies_s_j_and_the_right_cab_mask():
    from learn import song_model as M

    on, off = bank_label("ac20", 1, "true"), bank_label("ac20", 1, "false")
    c, sc, s, ss, k, km = SP.encode_member("ac20", on, RL.PLAN_TABLE)
    _, sc_off, _, _, _, km_off = SP.encode_member("ac20", off, RL.PLAN_TABLE)
    j = M.CONT.index("ac20Amp/ac20Volume")
    assert sc[j] == pytest.approx(1.93) and sc_off[j] == pytest.approx(1.93)
    for n in RL.RIGHT_GATED:
        assert sc[M.CONT.index(n)] > 0 and sc_off[M.CONT.index(n)] == 0
    assert km[M.CAT.index(RL.RIGHT_MIC)] == 1 and km_off[M.CAT.index(RL.RIGHT_MIC)] == 0
    assert ss[M.SW.index("ac20Amp/ac20BassTreble")] == pytest.approx(3.44)


def test_members_for_uses_the_set_unless_the_half_is_a_point():
    row = {"i": 5, "label": {"x": 1}}
    sets = {5: {"A": {"point": False, "members": [{"label": {"x": 1}, "logw": -0.1}, {"label": {"x": 2}, "logw": -2.3}]},
                "B": {"point": True, "members": [{"label": {"x": 1}, "logw": 0.0}]}}}
    assert SP.members_for(row, "A", sets) == [({"x": 1}, -0.1), ({"x": 2}, -2.3)]
    assert SP.members_for(row, "B", sets) == [({"x": 1}, 0.0)]
    assert SP.members_for({"i": 6, "label": {"x": 3}}, "A", sets) == [({"x": 3}, 0.0)]


def test_member_arrays_pad_with_minus_infinity():
    lab = bank_label("pr12", 2)
    rows = [{"i": 1, "amp": "pr12", "label": lab}]
    sets = {1: {"A": {"point": False, "members": [{"label": lab, "logw": -0.5}, {"label": lab, "logw": -1.0}]},
                "B": {"point": True, "members": []}}}
    arr = SP.member_arrays(rows, sets, RL.PLAN_TABLE)
    assert arr["logw"].shape == (2, SP.M_MAX)
    assert list(arr["logw"][0, :3]) == [-0.5, -1.0, -INF] and arr["logw"][1, 0] == 0.0
    assert np.isinf(arr["logw"][1, 1:]).all()


def test_load_features_fills_preallocated_float32(tmp_path):
    idx = synthetic_idx(tmp_path, n_bands=2, per_band=2)
    rows = [{"i": r[0], "amp": r[3], "cls": r[4]} for r in idx]
    X, C = SP.load_features(rows, lambda r: tmp_path / f"{r['i']}.npz")
    assert X.dtype == np.float32 and X.shape == (8, 2, 96, 12) and C.shape[0] == 8
    assert X[0, 0, 0, 0] == pytest.approx((-40 + 60) / 30) and X[1, 0, 0, 0] == pytest.approx((-30 + 60) / 30)


# ------------------------------------------------------------------------------ the refusal rule

def test_refused_answers_score_as_S():
    assert SP.as_S(INF, 2.0) == (2.0, True) and SP.as_S(1.5, 2.0) == (1.5, False)
    assert SP.as_S(None, 2.0) == (2.0, True) and SP.as_S(0.0, 2.0) == (2.0, True)
    u = {"d": {"S": 2.0, "x": INF, "y": 1.0}}
    assert SP.log_vs_S(u, "x") == (0.0, True)
    assert SP.log_vs_S(u, "y") == (pytest.approx(math.log(0.5)), False)
    assert SP.log_vs_S(u, "S") == (0.0, False)


def test_best_of_k_scores_each_refused_sample_as_S_on_that_half():
    v, j, n = SP.best_of_refusal([INF, 0.5, 0.9], [0.1, INF, 0.7], 1.0, 2.0)
    assert j == 1 and v == 2.0 and n == 2                  # picked on search, its held half refused -> S
    v, j, n = SP.best_of_refusal([0.9, 0.8], [0.4, 0.3], 1.0, 2.0)
    assert (v, j, n) == (0.3, 1, 0)


def units(n_bands=6, per=4, arms=("B1", "B2"), better=None, refuse=None, types=("broad", "ks_prior")):
    """E1-like units: S = 1, B0 top 0.9, constant 1.0; better[(arm, type)] = d for that arm."""
    out = []
    t = 0
    for b in range(n_bands):
        for k in range(per):
            for typ in types:
                for search in "AB":
                    d = {"S": 1.0, "constant": 1.0, f"1b:{search}:top": 0.9, "target": 0.0, "target_repeat": 0.0}
                    for a in arms:
                        d[f"{a}|1b:{search}:top"] = (better or {}).get((a, typ), 0.9) + 0.01 * ((t + k) % 3)
                    if refuse:
                        d[f"{refuse}|1b:{search}:top"] = INF
                    out.append({"band": f"band{b}", "target": t, "type": typ, "search": search, "d": d,
                                "s": dict(d)})
                t += 1
    return out


def test_refused_new_arm_counts_against_it_and_drops_nothing():
    us = units(refuse="B2")
    ch = SP.provisional_choice(us, ["B1", "B2"])
    assert ch["broad"]["refused"]["B2"] == len([u for u in us if u["type"] == "broad"])
    assert ch["broad"]["refused"]["B1"] == 0
    assert ch["broad"]["means"]["B2"] == pytest.approx(0.0)    # refused = S, not dropped


# ------------------------------------------------------------------------------ the provisional decider

def test_provisional_decider_uses_broad_targets_and_reports_ks_prior_beside():
    us = units(better={("B2", "broad"): 0.5, ("B2", "ks_prior"): 0.5})
    ch = SP.provisional_choice(us, ["B1", "B2"])
    assert ch["provisional"] and ch["broad"]["chosen"] == "B2" and ch["chosen"] == "B2"


def test_provisional_decider_is_undecided_when_the_halves_disagree():
    us = units(better={("B2", "broad"): 0.5, ("B1", "ks_prior"): 0.5, ("B2", "ks_prior"): 0.95})
    ch = SP.provisional_choice(us, ["B1", "B2"])
    assert ch["broad"]["chosen"] == "B2" and ch["ks_prior"]["chosen"] == "B1" and ch["chosen"] == "undecided"


def test_ties_go_to_the_cheaper_arm():
    us = units(better={("B1", "broad"): 0.9, ("B2", "broad"): 0.9}, types=("broad",))
    ch = SP.decide(us, SP.e1_names(["B1", "B2"]), SP.COST_ORDER, SP.e1_unit_id)
    assert ch["chosen"] in ("B0",) and ch["best"] in ("B0", "B1", "B2")


def test_decide_refuses_an_unscored_candidate():
    us = units(arms=("B1",), types=("broad",))
    with pytest.raises(SystemExit):
        SP.decide(us, SP.e1_names(["B1", "B2"]), SP.COST_ORDER, SP.e1_unit_id)


def test_select_units_report_and_audit_lists():
    us = []
    for t in range(6):
        for search in "AB":
            ds = 0.05 if (t == 2 and search == "B") else 1.0
            us.append({"target": t, "search": search, "band": "b",
                       "d": {"S": ds, "target": 0.0, "target_repeat": 0.0}})
    rep = SP.select_units(us, ["4"], "report")
    aud = SP.select_units(us, ["4"], "audit")
    assert len(rep) == 9 and len(aud) == 8
    assert SP.units_hash(rep) == SP.units_hash(list(reversed(rep))) != SP.units_hash(aud)


def test_e1_units_reproduce_the_reports_228():
    if not (SP.DIAG / "report.json").exists():
        pytest.skip("the diagnostics' files are not on this machine")
    us, _, _ = SP.e1_load_units("report")
    au, _, _ = SP.e1_load_units("audit")
    assert len(us) == 228 and len(au) == 224


def test_paired_averages_per_part_and_skips_unscored_units():
    us = [{"target": 1, "band": "b1", "d": {"S": 1.0, "x": 0.5}},
          {"target": 1, "band": "b1", "d": {"S": 1.0, "x": 1.0}},
          {"target": 2, "band": "b2", "d": {"S": 1.0, "x": 1.0}},
          {"target": 3, "band": "b2", "d": {"S": 1.0}}]
    r = SP.paired(us, lambda u: "x", lambda u: "S")
    assert r["missing"] == 1 and r["units"] == 3
    assert r["band_weighted_mean"] == pytest.approx((math.log(0.5) / 2 + 0.0) / 2)


# ------------------------------------------------------------------------------ E2, C-fine, answers

def heads_for(amp, mu=0.3, sigma=0.1, k=2):
    from learn import song_model as M

    n = len(M.CONT)
    return {"pi": np.full(k, 1.0 / k), "mu": np.full((k, n), mu), "sigma": np.full((k, n), sigma),
            "sw_p": np.full(len(M.SW), 0.7), "mic_p": [np.full(10, 0.1) for _ in M.CAT]}


def test_box_score_at_a_limit_takes_the_censored_mass():
    from scipy.stats import norm

    from learn import song_model as M

    amp = "pr12"
    S = S_for(amp)
    x = dict(S)
    x[("pr12Amp", "pr12Volume")] = "0"
    h = heads_for(amp, mu=-0.2, sigma=0.1, k=1)
    base = SP.box_logprob(h, S, amp, "censored")
    lim = SP.box_logprob(h, x, amp, "censored")
    # volume moved from 0.5 to the limit 0: the box [−0.02, 0.02] takes Φ((0.02 − μ)/σ), all mass below 0 included
    want = math.log(norm.cdf((0.02 + 0.2) / 0.1)) - math.log(norm.cdf((0.52 + 0.2) / 0.1) - norm.cdf((0.48 + 0.2) / 0.1))
    assert lim - base == pytest.approx(want, rel=1e-6)
    assert math.isfinite(SP.box_logprob(h, x, amp, "truncated"))
    assert len(M.CONT) > 0


def test_trunc_logdensity_and_box_scores_are_finite():
    amp = "sw50r"
    S = S_for(amp)
    h = heads_for(amp)
    for f in (lambda: SP.trunc_logdensity(h, S, amp), lambda: SP.box_logprob(h, S, amp, "truncated")):
        assert math.isfinite(f())


def test_top_answer_is_the_clipped_top_mean_and_samples_clip():
    from learn import song_model as M

    amp = "ac20"
    S = S_for(amp)
    h = heads_for(amp, mu=1.4, sigma=0.5, k=2)
    h["pi"] = np.array([0.3, 0.7])
    h["mu"][1] = -0.6
    x = SP.top_answer2(h, amp, S)
    for d in K.space(amp, S):
        if d.kind in ("cont", "log"):
            assert d.to_unit(x[(d.module, d.key)]) == 0.0
    rng = np.random.default_rng(0)
    vals = [v for _ in range(200) for v in SP.sample2(h, rng)[0]]
    assert min(vals) == 0.0 and max(vals) == 1.0 and all(0.0 <= v <= 1.0 for v in vals)
    assert len(SP.sample2(h, rng)[0]) == len(M.CONT)


def test_path_picks_and_spearman():
    scores = list(range(20))
    held = [20 - i for i in range(20)]
    assert SP.path_spearman(scores, held) == pytest.approx(-1.0)
    assert SP.path_spearman(scores[:9], held[:9]) is None
    p = SP.path_picks(scores, [float(h) for h in held], [float(h) for h in held], 10.0)
    assert p["maxscore8"] == pytest.approx(math.log(13 / 10)) and p["maxscore_all"] == pytest.approx(math.log(1 / 10))
    assert p["ks8"] == pytest.approx(math.log(13 / 10))


def test_cfine_picks_by_score_among_the_lowest_objectives():
    xs = [{"i": i} for i in range(12)]
    obj = [5, 1, 2, INF, 3, 4, 0.5, 6, 7, 8, 9, 0.1]
    j = SP.cfine_pick(xs, obj, lambda x: -abs(x["i"] - 4), n=8)
    assert j == 4
    lowest = sorted((i for i, v in enumerate(obj) if math.isfinite(v)), key=lambda i: obj[i])[:8]
    assert SP.cfine_pick(xs, obj, lambda x: x["i"], n=8) == max(lowest)
    assert SP.cfine_pick(xs, [INF] * 12, lambda x: 0) is None


def test_main_stage_replay_returns_the_evaluated_settings_in_order():
    amp = "pr12"
    S = S_for(amp)
    dims = K.space(amp, S)
    curve = [10.0 - 0.1 * i for i in range(60)]
    xs, obj = SP.main_stage_settings(dims, S, curve)
    assert len(xs) == len(obj) == 52 and obj == curve[:52] and xs[0] == S


def test_answer_shape():
    amp = "pr12"
    S = S_for(amp)
    rows = []
    for k in range(5):
        t = dict(S)
        t[("parameters", "inputGain")] = str(-20 + 6 * k)
        x = dict(t)
        x[("pr12Amp", "pr12Volume")] = "0"
        rows.append((amp, x, t))
    sh = SP.answer_shape(rows)
    assert sh["spearman"]["parameters/inputGain"] == pytest.approx(1.0)
    assert sh["switch_accuracy"] == 1.0 and 0 < sh["limit_share"] < 1


# ------------------------------------------------------------------------------ torch: head and losses

torch = None


@pytest.fixture
def T():
    return pytest.importorskip("torch")


def test_censored_lp_density_inside_and_tail_mass_at_the_limits(T):
    from scipy.stats import norm

    mu, ls = T.tensor([0.3, 0.3, 0.3]), T.log(T.tensor([0.2, 0.2, 0.2]))
    u = T.tensor([0.5, 0.0 + 5e-7, 1.0 - 5e-7])
    lp = SP.censored_lp(u, mu, ls)
    assert float(lp[0]) == pytest.approx(norm.logpdf(0.5, 0.3, 0.2), rel=1e-5)
    assert float(lp[1]) == pytest.approx(norm.logcdf(0.0, 0.3, 0.2), rel=1e-5)
    assert float(lp[2]) == pytest.approx(norm.logsf(1.0, 0.3, 0.2), rel=1e-5)
    assert float(SP.censored_lp(T.tensor([2e-6]), mu[:1], ls[:1])) == pytest.approx(
        norm.logpdf(2e-6, 0.3, 0.2), rel=1e-5)                          # outside the 1e-6 tolerance


def test_soft_bound_keeps_a_gradient_outside(T):
    z = T.tensor([8.0, -8.0, 0.0], requires_grad=True)
    mu = SP.MU_LO + (SP.MU_HI - SP.MU_LO) * T.sigmoid(z)
    mu.sum().backward()
    assert (z.grad > 0).all() and float(mu.detach()[0]) < SP.MU_HI and float(mu.detach()[1]) > SP.MU_LO


def test_build_model2_bounds_the_means_and_keeps_b0s_keys(T):
    from learn import song_model as M

    net = SP.build_model2().eval()
    assert set(net.state_dict()) == set(M.build_model().state_dict())
    x = T.randn(2, 2, 96, 64)
    c = T.zeros(2, len(M.AMPS) + len(M.CLASSES) + 2)
    with T.no_grad():
        logpi, mu, ls, swl, catl = net(x, c)
    assert mu.shape == (2, M.K_MIX, len(M.CONT)) and float(mu.min()) > -1 and float(mu.max()) < 2


def rand_out(T, B=6, K_=4, seed=0):
    from learn import song_model as M

    g = T.Generator().manual_seed(seed)
    n = len(M.CONT)
    logpi = T.log_softmax(T.randn(B, K_, generator=g), -1)
    mu = T.sigmoid(T.randn(B, K_, n, generator=g))
    ls = -1.0 - T.rand(B, K_, n, generator=g)
    swl = T.randn(B, len(M.SW), generator=g)
    catl = [T.randn(B, 10, generator=g) for _ in M.CAT]
    c = 0.05 + 0.9 * T.rand(B, n, generator=g)
    cm = (T.rand(B, n, generator=g) > 0.3).float()
    s = (T.rand(B, len(M.SW), generator=g) > 0.5).float()
    sm = (T.rand(B, len(M.SW), generator=g) > 0.3).float()
    k = T.randint(0, 10, (B, len(M.CAT)), generator=g)
    km = (T.rand(B, len(M.CAT), generator=g) > 0.2).float()
    return (logpi, mu, ls, swl, catl), (c, cm, s, sm, k, km)


def bt_from(T, lab, sc=None, ss=None, M_=1, logw=None, omega=None):
    c, cm, s, sm, k, km = lab
    B = c.shape[0]

    def m(t):
        return t[:, None].expand(B, M_, *t.shape[1:]).clone()

    bt = {"c": m(c), "sc": m(cm if sc is None else sc), "s": m(s), "ss": m(sm if ss is None else ss),
          "k": m(k), "km": m(km)}
    lw = T.full((B, M_), -math.inf)
    lw[:, 0] = 0.0
    bt["logw"] = lw if logw is None else logw
    bt["omega"] = T.ones(B) if omega is None else omega
    return bt


def test_b1_loss_equals_b0s_at_weights_one(T):
    from learn import song_model as M

    out, lab = rand_out(T)
    b0 = M.loss_fn(out, *lab)
    for lp in (SP.gaussian_lp, SP.censored_lp):                      # labels are inside (0, 1)
        got = SP.loss_soundspace(out, bt_from(T, lab), lp_fn=lp)
        assert float(got) == pytest.approx(float(b0), rel=1e-5)


def test_set_loss_with_one_member_equals_the_point_loss(T):
    out, lab = rand_out(T, seed=1)
    one = SP.loss_soundspace(out, bt_from(T, lab))
    padded = SP.loss_soundspace(out, bt_from(T, lab, M_=4))         # extra members at log w = −inf
    assert float(padded) == pytest.approx(float(one), rel=1e-6)


def test_record_weights_reweight_examples(T):
    out, lab = rand_out(T, B=4, seed=2)
    L, _, _ = SP.member_terms(out, bt_from(T, lab))
    w = T.tensor([3.0, 1.0, 1.0, 1.0])
    got = SP.loss_soundspace(out, bt_from(T, lab, omega=w))
    assert float(got) == pytest.approx(float((w * L[:, 0]).sum() / w.mean()), rel=1e-6)


def test_weights_scale_the_settings_inside_the_group(T):
    out, lab = rand_out(T, seed=3)
    c, cm, s, sm, k, km = lab
    sc = cm.clone()
    sc[:, 0] *= 3.0
    a = SP.loss_soundspace(out, bt_from(T, lab))
    b = SP.loss_soundspace(out, bt_from(T, lab, sc=sc))
    assert float(a) != pytest.approx(float(b))


def test_responsibilities_follow_the_tempered_ratio_not_one_and_zero(T):
    logw = T.log(T.tensor([[0.5, 0.5]]))
    joint = T.tensor([[-10.0, -40.0]])                # the model prefers member A by 30 nats
    D = T.tensor([[10.0, 10.0]])
    g = SP.responsibilities(logw, joint, D)
    assert float(g[0, 1]) > 0.01                       # untempered it would be e^-30
    assert float(g[0, 0] / g[0, 1]) == pytest.approx(math.exp(3.0), rel=1e-5)
    g2 = SP.responsibilities(T.log(T.tensor([[0.8, 0.2]])), joint, T.tensor([[10.0, 5.0]]))
    assert float(g2[0, 0] / g2[0, 1]) == pytest.approx(4.0 * math.exp(-1.0 + 8.0), rel=1e-5)
    pad = SP.responsibilities(T.tensor([[0.0, -math.inf]]), joint, D)
    assert float(pad[0, 1]) == 0.0 and float(pad[0, 0]) == 1.0


def test_member_terms_count_active_terms_per_member(T):
    out, lab = rand_out(T, seed=4)
    c, cm, s, sm, k, km = lab
    _, _, n = SP.member_terms(out, bt_from(T, lab))
    want = cm.sum(-1) + sm.sum(-1) + km.sum(-1)
    assert T.equal(n[:, 0], want.clamp(min=1))


def toy_fit(T, mode_seeking, steps=600):
    """One continuous setting, one component, two members (0.2, 0.8) at equal weight."""
    z = T.tensor([[math.log(0.45 + 1) - math.log(2 - 0.45)]], requires_grad=True)  # mu = 0.45
    ls = T.tensor([[math.log(0.3)]], requires_grad=True)
    opt = T.optim.Adam([z, ls], lr=0.03)
    c = T.tensor([[[0.2], [0.8]]])
    bt = {"c": c, "sc": T.ones(1, 2, 1), "s": T.zeros(1, 2, 0), "ss": T.zeros(1, 2, 0),
          "k": T.zeros(1, 2, 0, dtype=T.long), "km": T.zeros(1, 2, 0), "logw": T.log(T.tensor([[0.5, 0.5]])),
          "omega": T.ones(1)}
    for _ in range(steps):
        mu = (SP.MU_LO + (SP.MU_HI - SP.MU_LO) * T.sigmoid(z)).view(1, 1, 1)
        out = (T.zeros(1, 1), mu, ls.clamp(-6, 1).view(1, 1, 1), T.zeros(1, 0), [])
        if mode_seeking:
            loss = SP.loss_soundspace(out, bt)
        else:                                                          # fixed responsibilities: the average
            L, _, _ = SP.member_terms(out, bt)
            loss = (0.5 * L).sum()
        opt.zero_grad()
        loss.backward()
        opt.step()
    return float(SP.MU_LO + (SP.MU_HI - SP.MU_LO) * T.sigmoid(z.detach()))


def test_toy_set_loss_lands_on_a_member_not_the_midpoint(T):
    mu = toy_fit(T, True)
    assert min(abs(mu - 0.2), abs(mu - 0.8)) < 0.05
    assert abs(toy_fit(T, False) - 0.5) < 0.05                        # the averaging loss it replaces
