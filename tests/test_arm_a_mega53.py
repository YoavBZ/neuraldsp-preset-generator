"""Arm A with Mega-53 (`learn/arm_a_mega53.py`, docs/arm-a-mega53-plan.md, amendment 1): the
fresh pool and the held-out check (fail closed), decide-x, the recipe and its fallback, the gates,
the sharding, the render counts, the rows, the drop rule per contrast and the report's math. Fakes,
plus zero-render checks against the stored data where it exists."""

import json
import math
import random

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import arm_a_levers as L  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import local_objective_1c as C  # noqa: E402
from learn import arm_a_mega53 as M  # noqa: E402

PY = "/x/.venv/bin/python"


# --- the pool --------------------------------------------------------------------------------------

def test_pool_is_the_amendments_21_parts_in_12_bands():
    slugs = M.pool_slugs()
    assert len(slugs) == 21 and len(set(slugs)) == 21 and len(M.F_POOL) == 12
    lt = M.lt_parts()
    assert all(lt[s]["band"] == M.pool_band(s) for s in slugs)
    assert sum(lt[s]["gain_class"] == "clean" for s in slugs) == 11
    assert sum(lt[s]["gain_class"] == "crunch" for s in slugs) == 10
    assert sum(s.startswith("cambridge-") for s in slugs) == 17
    assert set(M.F_SONG) <= set(slugs) and len(M.F_SONG) == 8 and len({M.pool_band(s) for s in M.F_SONG}) == 4
    assert set(M.F_BAND_PARTS) <= set(slugs) and len({M.pool_band(s) for s in M.F_BAND_PARTS}) == 2
    assert M.N_DIRS["F"] == len(slugs) * 3 * 2 and M.N_GROUPS["F"] == len(slugs) * 3


def test_pool_has_no_step3_part():
    step3 = set(M.d_parts())
    assert len(step3) == 24
    assert not step3 & set(M.pool_slugs())


def test_pool_rule_on_toy_menus():
    lt = {"a": {"gain_class": "clean"}, "b": {"gain_class": "crunch"}, "c": {"gain_class": "clean"},
          "s3": {"gain_class": "clean"}}

    def menu(bad=None):
        m = {}
        for amp in K.AMPS:
            for cls in ("clean", "crunch"):
                m.setdefault(amp, {})[K.START[cls][amp]] = {"flat": {"A": 1.0, "B": 2.0}}
        if bad:
            amp, cls, h = bad
            m[amp][K.START[cls][amp]]["flat"][h] = math.inf
        return m
    menus = {"a": menu(), "b": menu(("ac20", "crunch", "B")), "c": None, "s3": menu()}
    assert M.pool_by_rule(lt, {"s3"}, menus.get) == ["a"]
    assert not M.s_finite_everywhere(menu(("pr12", "clean", "A")), {a: K.START["clean"][a] for a in K.AMPS})


@pytest.mark.skipif(not (K.HOME / "learn/label-table").exists(), reason="no stored label-table menus")
def test_pool_rule_on_the_stored_label_table_gives_the_declared_pool():
    rule = M.pool_by_rule(M.lt_parts(), set(M.d_parts()),
                          lambda s: M._load(K.HOME / "learn/label-table" / s / "menu.json"))
    assert rule == M.pool_slugs()


# --- the held-out check (amendment 1, item 2) ------------------------------------------------------

LT = {"telefunken-Song_A-GTR": {"set": 12, "band": "Band A", "crop": "/c/a"},
      "cambridge-song-b-elecgtr1": {"set": 3, "band": "Band B", "crop": "/c/b"}}
CAT12 = {"sessions": [{"source": "telefunken", "song": "Song A", "split": "development", "parts": [{"part": "GTR"}]},
                      {"source": "guitar-techs", "song": "P3_music excerpt 01", "split": "development",
                       "parts": [{"part": "01"}]}],
         "held_out_uses": [{"sessions": ["telefunken/Other"]}]}
CAT3 = {"parts": [{"slug": "cambridge-song-b-elecgtr1", "split": "development", "band": "Band B",
                   "session_key": "cambridge/B_Song_Full"}], "held_out_bands": ["Band Z"], "held_out_uses": []}
LEDGER3 = {"uses": [{"parts": 27, "purpose": "held-out confirmation"}]}


def _hp(lt=LT, cat12=CAT12, cat3=CAT3, ledger=LEDGER3, covers=lambda x: False, slugs=None):
    return M.heldout_problems(list(lt) if slugs is None else slugs, lt, cat12, cat3, ledger, covers)


def test_heldout_check_passes_development_parts():
    assert _hp() == {}


def test_heldout_check_fails_closed_on_parts_not_found():
    assert "not in the label table" in _hp(slugs=["nope"])["nope"][0]
    bad = _hp(cat12={"sessions": [], "held_out_uses": []}, cat3={"parts": [], "held_out_uses": []})
    assert set(bad) == set(LT) and all("0 " in v[0] for v in bad.values())
    assert _hp(covers=None)                                             # no set 4–6 check: not a pass


def test_heldout_check_refuses_held_out_and_used_sessions():
    c = json.loads(json.dumps(CAT12))
    c["sessions"][0]["split"] = "held_out"
    assert "split" in _hp(cat12=c)["telefunken-Song_A-GTR"][0]
    c = json.loads(json.dumps(CAT12))
    c["held_out_uses"].append({"sessions": ["telefunken/Song A"]})
    assert "held_out_uses" in _hp(cat12=c)["telefunken-Song_A-GTR"][0]
    p3 = {"guitar-techs-P3_music_excerpt_01-01": {"set": 12, "band": "x", "crop": "/c/p3"}}
    assert any("P3" in w for w in _hp(lt=p3)["guitar-techs-P3_music_excerpt_01-01"])


def test_heldout_check_refuses_set3_held_out_and_sets_4_to_6():
    c = json.loads(json.dumps(CAT3))
    c["parts"][0]["split"] = "held_out"
    assert _hp(cat3=c)["cambridge-song-b-elecgtr1"]
    c = json.loads(json.dumps(CAT3))
    c["held_out_bands"].append("Band B")
    assert any("held-out band" in w for w in _hp(cat3=c)["cambridge-song-b-elecgtr1"])
    c = json.loads(json.dumps(CAT3))
    c["held_out_uses"].append({"slugs": ["cambridge-song-b-elecgtr1"]})
    assert _hp(cat3=c)["cambridge-song-b-elecgtr1"]
    assert _hp(ledger={"uses": [{"session": "cambridge/B_Song_Full"}]})["cambridge-song-b-elecgtr1"]
    assert set(_hp(covers=lambda x: x == "Band A")) == {"telefunken-Song_A-GTR"}

    def boom(x):
        raise KeyError(x)
    assert set(_hp(covers=boom)) == set(LT)                              # an error is a problem
    assert _hp(lt={"x": {"set": 4, "band": "b", "crop": "/c"}})["x"]


def test_heldout_check_on_the_real_catalogues_passes_the_pool():
    assert M.heldout_check() == {}


# --- decide-x -----------------------------------------------------------------------------------------

def _rep(p1, p2):
    return {"primary": {M.X_P1: p1, M.X_P2: p2}}


def test_decide_x_each_branch():
    pos, neg, zero = {"lo90": 0.01, "hi90": 0.1}, {"lo90": -0.05, "hi90": -0.01}, {"lo90": -0.02, "hi90": 0.04}
    a = M.decide_x(_rep(pos, pos))
    assert a["rule"] == 1 and a["arm_x"] == "csep_mega53" and a["source"] == "mega53" and a["contrast"] == ["X", "M"]
    b = M.decide_x(_rep(pos, zero))
    assert b["rule"] == 2 and b["arm_x"] == "csep_stem" and b["source"] == "stem" and b["contrast"] == ["X", "H"]
    for p1, p2 in ((zero, zero), (neg, neg), (zero, neg), (neg, zero)):
        assert M.decide_x(_rep(p1, p2))["arm_x"] is None
    assert M.decide_x(_rep({"lo90": 0.0}, {"lo90": 0.0}))["arm_x"] is None     # lo90 > 0, strictly


def test_decide_x_incomplete_is_no_x():
    zero = {"lo90": -0.02, "hi90": 0.04}
    for rep in (None, {}, {"primary": {}}, "garbage", _rep({"refused": "x"}, {"refused": "y"}),
                _rep(zero, {"refused": "36 cells"}), _rep({"refused": "x"}, zero), _rep(zero, {"lo90": None}),
                _rep({"lo90": float("nan")}, zero), _rep("garbage", zero)):
        d = M.decide_x(rep)
        assert d["arm_x"] is None and d["rule"] == 3


def test_decide_x_reads_each_rule_on_its_own_primary():
    """Read literally: rule 1 needs only P2 complete with lo90 > 0; rule 2 only P1."""
    pos = {"lo90": 0.01, "hi90": 0.1}
    assert M.decide_x(_rep({"refused": "36 cells"}, pos))["rule"] == 1
    assert M.decide_x(_rep(pos, {"refused": "36 cells"}))["rule"] == 2
    assert M.decide_x(_rep(pos, {"lo90": float("nan")}))["rule"] == 2


def test_ledger_arm_x_is_set_once():
    led = {"tests": [{"test_id": "other"}, {"test_id": "arm-a-mega53"}]}
    out = M.ledger_with_arm_x(led, {"arm_x": None, "rule": 3, "why": "w"}, "t1")
    assert out["tests"][1]["arm_x"]["outcome"] == "none"
    out = M.ledger_with_arm_x(out, {"arm_x": "csep_stem", "rule": 2, "why": "w"}, "t2")
    assert out["tests"][1]["arm_x"]["outcome"] == "none" and out["tests"][1]["arm_x"]["decided"] == "t1"
    with pytest.raises(SystemExit):
        M.ledger_with_arm_x({"tests": []}, {"arm_x": None, "rule": 3, "why": ""}, "t")


def test_arms_per_stage():
    assert M.arms("D", {"arm_x": None}) == ("H", "M", "T")
    assert M.arms("F", {"arm_x": "csep_mega53"}) == ("H", "M", "X")


# --- the recipe ----------------------------------------------------------------------------------------

AMP = "sw50r"


def preset(seed):
    rng = random.Random(seed)
    x = {("parameters", "outputGain"): "5.96", ("cabParameters", "leftCabActive"): "true"}
    for d in K.space(AMP):
        if d.kind == "cat":
            x[(d.module, d.key)] = "3"
        elif d.kind == "switch":
            x[(d.module, d.key)] = "false"
        else:
            x[(d.module, d.key)] = K.fmt(d.from_unit(rng.random()))
    return x


S0 = preset(1)
DIMS = K.space(AMP, S0)


def bowl(x):
    return 1.0 + sum((L.unit(d, x) - 0.3) ** 2 for d in DIMS if d.kind in ("cont", "log"))


def test_constants_are_the_adopted_recipe():
    assert M.MAIN_RENDERS == 52 and M.PER_DIRECTION == 55 and M.SHRINK == 0.5
    assert M.SEED == 20261013 == L.SEED and M.OBJ_LAG == -52 == L.OBJ_LAG
    assert M.TOL == 0.005 and M.SILENT_DBFS == -60.0 and M.TRIM_S == 0.25


def test_recipe_is_main_stage_then_shrink_then_the_probe():
    seen = []
    res = M.recipe(DIMS, S0, bowl, lambda x: (seen.append(x) or (-20.0, 1.0)))
    bx, bv, n = L.main_stage(DIMS, S0, bowl)
    assert res["best_x"] == bx and res["best_value"] == bv and res["evaluations"] == n == 52
    assert res["shrunk_x"] == L.shrink(DIMS, S0, bx, 0.5) == res["output_x"] and res["fallback"] is None
    assert seen == [res["shrunk_x"]]                                      # the probe renders the shrunk setting once


def test_recipe_falls_back_to_S():
    for probe in (lambda x: (-80.0, 1.0), lambda x: (-10.0, math.inf), lambda x: (-math.inf, math.inf)):
        res = M.recipe(DIMS, S0, bowl, probe)
        assert res["fallback"] and res["output_x"] == S0 and res["output_x"] is not S0


def test_fallback_rule_on_toy_renders():
    sr = M.SR
    loud_head = np.zeros(sr * 2)
    loud_head[: int(0.2 * sr)] = 0.9                                      # only the fade-in is loud
    assert M.peak_dbfs(loud_head) == -math.inf
    assert "silent" in M.fallback_reason(M.peak_dbfs(loud_head), 1.0)
    quiet = np.full(sr, 10 ** (-70 / 20))
    assert "silent" in M.fallback_reason(M.peak_dbfs(quiet), 1.0)
    normal = np.full(sr, 0.1)
    assert M.peak_dbfs(normal) == pytest.approx(-20.0)
    assert M.fallback_reason(M.peak_dbfs(normal), 2.0) is None
    assert "refused" in M.fallback_reason(M.peak_dbfs(normal), math.inf)
    assert "refused" in M.fallback_reason(-20.0, None)
    assert M.fallback_reason(-60.0, 1.0) is None                          # at the floor: not silent
    assert M.peak_dbfs(np.stack([normal, normal], 1)) == pytest.approx(-20.0)


def _stored_levers():
    return (L.OUT / "early" / "lever-shrink-0.5").exists() and (L.SS_OUT / "armA").exists() and \
        (L.SS_OUT / "armB" / "menu-S.json").exists()


@pytest.mark.skipif(not _stored_levers(), reason="no stored levers data")
def test_recipe_reproduces_the_stored_3cprime_shrunk_settings_for_H():
    """Zero renders: main_stage on the stored objective curves + shrink 0.5 + a passing probe
    give exactly the stored lever-shrink-0.5 settings (H's stage-D output), on all 144."""
    ms, ps = L.menu_S(), K.parts()
    n = 0
    for f in sorted((L.OUT / "early" / "lever-shrink-0.5").glob("*/*/[AB].json")):
        slug, amp, search = f.parent.parent.name, f.parent.name, f.stem
        stored, _ = L.stored_a(slug, amp, search)
        S = ms[amp][ps[slug]["gain_class"]][1]
        res = M.recipe(K.space(amp, S), S, L.Replay(stored["objective_curve"]), lambda x: (-10.0, 1.0))
        want = L._settings(f)
        assert res["output_x"] == want, (slug, amp, search)
        assert res["evaluations"] == stored["stages"]["main"]["renders"]
        n += 1
    assert n == 144


# --- sharding, counts, caps ------------------------------------------------------------------------

def test_render_counts_match_the_plan():
    d = M.expected_renders("D", 142, 72, ["M", "T"])
    assert d["M"] == d["T"] == 7_882 and d["H_fallback_checks"] == 214 and d["repeat_check"] == 12
    assert d["total"] == M.TABLE["D"] == 15_990 <= M.CAPS["D"]
    assert M.expected_renders("D", 142, 72, ["M", "T", "X"])["total"] - d["total"] == M.TABLE_X["D"] == 7_882
    f = M.expected_renders("F", 126, 63, ["H", "M"])
    assert f["total"] == M.TABLE["F"] == 14_112 <= M.CAPS["F"]
    assert M.expected_renders("F", 126, 63, ["H", "M", "X"])["total"] - f["total"] == 6_993 == M.TABLE_X["F"]
    assert M.TABLE_X["D"] <= M.CAPS_X["D"] and M.TABLE_X["F"] <= M.CAPS_X["F"]
    assert M.CAPS_X["D"] + M.CAPS_X["F"] == 15_500 and M.CAPS["D"] + M.CAPS["F"] == 31_100


def test_cap_problem():
    assert M.cap_problem(100, 50, 150) is None and "exceeds" in M.cap_problem(100, 51, 150)
    assert M.cap_of("D", {"arm_x": None}) == 16_500 and M.cap_of("F", {"arm_x": "csep_stem"}) == 21_900


def test_sharding_keeps_a_part_amps_directions_together_and_partitions():
    dirs = [(s, a, sh, h) for s in ("p1", "p2", "p3", "p4") for a in K.AMPS for sh, h in K.DIRECTIONS]
    dirs.remove(("p2", "pr12", "A", "B"))
    shards = [M.shard_groups(dirs, (i, 3)) for i in range(3)]
    flat = [g for s in shards for g in s]
    assert sorted(flat) == M.groups(dirs) and len(flat) == len(set(flat)) == 12
    assert all(abs(len(s) - 4) <= 1 for s in shards)


def test_repeat_draw_is_seeded_and_from_the_directions():
    dirs = [(f"p{i}", "pr12", "A", "B") for i in range(142)]
    a, b = M.repeat_draw(dirs), M.repeat_draw(list(reversed(dirs)))
    assert a == b == random.Random(20261034).sample(sorted(dirs), 6) and len(set(a)) == 6


def test_stage_f_directions():
    dirs = M.stage_dirs("F")
    assert len(dirs) == 126 and len(M.groups(dirs)) == 63


@pytest.mark.skipif(not _stored_levers(), reason="no stored song-settings data")
def test_stage_d_directions_are_the_142():
    dirs = M.stage_dirs("D")
    assert len(dirs) == 142 and len(M.groups(dirs)) == 72


# --- the gates (amendment 1, item 6) -------------------------------------------------------------

def _ps(n_render, sep=False, extra=()):
    ps = [(100 + i, f"{PY} -u -m learn.arm_a_mega53 search --stage D --shard {i}/3") for i in range(n_render)]
    if sep:
        ps.append((200, f"/t/msst-venv/bin/python -m learn.arm_a_mega53 separate --sep mega53"))
    return ps + [(300, "vim x"), (301, "/bin/zsh learn/arm_a_mega53_run.zsh")] + list(extra)


def test_render_gate():
    assert M.render_blocker(_ps(2)) is None
    assert M.render_blocker(_ps(3)) is not None
    assert M.render_blocker(_ps(3), own={100}) is None                    # itself not counted
    assert M.render_blocker(_ps(1, sep=True)) is None
    assert M.render_blocker(_ps(2, sep=True)) is not None                 # fewer than 2 beside a separation
    other = [(400, f"{PY} -m learn.local_objective render --di csep_stem --shard 0/3"),
             (401, f"{PY} -m learn.ks_extend run"), (402, f"/t/demucs-venv/bin/python -m learn.arm_a_mega53 rebuild --sep x")]
    assert M.render_blocker(_ps(0, extra=other[:2])) is None
    assert M.render_blocker(_ps(1, extra=other[:2])) is not None          # other sessions' renders count
    assert M.render_blocker(_ps(1, extra=other[1:])) is not None          # a rebuild counts as a separation


def test_separation_gate():
    assert M.separation_blockers(_ps(2), {999}, 12.0, 11.0) == []
    assert any("render" in w for w in M.separation_blockers(_ps(3), {999}, 12.0, 11.0))
    assert any("memory" in w for w in M.separation_blockers(_ps(0), {999}, 10.0, 11.0))
    assert M.separation_blockers(_ps(0), {999}, None, 11.0)
    assert any("separation" in w for w in M.separation_blockers(_ps(0, sep=True), {999}, 20.0, 11.0))
    assert M.separation_blockers(_ps(0, sep=True), {200}, 20.0, 11.0) == []          # itself
    tr = [(500, "/t/demucs-venv/bin/python -u -m learn.direc fit --fold 1")]
    assert any("training" in w for w in M.separation_blockers(_ps(0, extra=tr), {999}, 20.0, 11.0))
    assert M.separation_blockers(_ps(2), {999}, None, 0.0) == []           # memory not gated (between parts)


# --- arm-scoped stops (amendment 1, item 3: T and X can't stop a primary) ----------------------

def test_t_and_x_breakage_stops_only_that_arm(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "OUT", tmp_path)
    monkeypatch.setattr(M.LO, "stop_path", lambda: tmp_path / "lo-STOP.json")
    for arm in ("T", "X"):
        with pytest.raises(M.ArmStopped):
            M.breakage(tmp_path / f"{arm}.json", {"x": 1}, "moved", "D", arm)
        assert M.arm_stopped("D", arm) and not M.arm_stopped("F", arm)
        assert json.loads((tmp_path / f"{arm}.json").read_text())["status"] == "check_failed"
    assert not (tmp_path / "STOP.json").exists()
    M.check_stop()                                                        # the global stop is untouched
    assert not M.arm_stopped("D", "M")
    with pytest.raises(SystemExit):
        M.breakage(tmp_path / "m.json", {}, "moved", "D", "M")
    with pytest.raises(SystemExit):
        M.check_stop()


def test_stop_arm_refuses_unscoped_arms(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "OUT", tmp_path)
    M.stop_arm("F", "X", "inputs")
    assert M.arm_stopped("F", "X")
    with pytest.raises(SystemExit):
        M.stop_arm("F", "M", "inputs")


def test_stage_d_inputs_scope_t_and_x(monkeypatch):
    ok = {"cprime_mega53": True, "cprime_ref": False, "csep_stem": False}
    monkeypatch.setattr(M.LO, "rebuilds_ok", lambda di: ok[di])
    monkeypatch.setattr(M.C, "sep_ok", lambda sep: True)
    base, scoped = M.stage_d_input_problems({"arm_x": "csep_stem"})
    assert base == [] and set(scoped) == {"T", "X"}
    ok["cprime_mega53"] = False
    base, _ = M.stage_d_input_problems({"arm_x": None})
    assert base


# --- rebuild checks --------------------------------------------------------------------------------

def test_pair_problems():
    assert M.pair_problems(0, -22.9, -22.91) == []
    assert M.pair_problems(3, -22.9, -22.9) == [] and M.pair_problems(-4, -22.9, -22.9)
    assert M.pair_problems(0, -22.7, -22.72) == []                        # outside the target, within 0.05 LU of the other
    assert len(M.pair_problems(0, -22.7, -22.9)) == 1
    assert len(M.pair_problems(None, float("nan"), -22.9)) == 2


def test_x_pair_problems():
    assert M.x_pair_problems(1, -22.80, -22.84) == []
    assert M.x_pair_problems(1, -22.80, -22.9) and M.x_pair_problems(5, -22.9, -22.9)


def test_identity_problems():
    assert M.identity_problems({"a": 0.0, "b": 1e-7}, 2) == {}
    bad = M.identity_problems({"a": 2e-6, "b": None, "c": float("nan")}, 4)
    assert set(bad) == {"a", "b", "c", "_count"}


def test_identity_diffs():
    arr = {"a": np.zeros(4), "b": np.ones(4)}
    other = {"a": np.zeros(4) + 1e-9, "b": np.ones(5)}

    def miss(s):
        raise FileNotFoundError(s)
    d = M.identity_diffs(arr.get, other.get, ["a", "b"])
    assert d["a"] == pytest.approx(1e-9) and d["b"] is None
    assert M.identity_diffs(arr.get, miss, ["a"]) == {"a": None}


def test_kept_flac_is_trimmed_16_bit(tmp_path):
    sf = pytest.importorskip("soundfile")
    y = np.sin(np.arange(M.SR) * 0.01) * 0.5
    scale = M.save_kept_flac(tmp_path / "x.flac", y)
    info = sf.info(str(tmp_path / "x.flac"))
    assert info.subtype == "PCM_16" and info.frames == M.SR - int(0.25 * M.SR)
    back, _ = sf.read(str(tmp_path / "x.flac"))
    assert np.max(np.abs(back * scale - y[int(0.25 * M.SR):])) < 1e-4


# --- the report: drop rule per contrast, rows, Fieller ---------------------------------------------

BANDS = [f"b{i}" for i in range(12)]


def toy_units(seed=0, t_noise=False):
    rng, rt = random.Random(seed), random.Random(seed + 1)
    units = []
    for i, b in enumerate(BANDS):
        for p in range(2):
            slug = f"{b}-p{p}"
            for amp in K.AMPS:
                for search, held in K.DIRECTIONS:
                    s = 2.0 + rng.random()
                    h = s * math.exp(-0.08 + 0.02 * rng.gauss(0, 1))
                    m = h * math.exp(-0.03 + 0.02 * rng.gauss(0, 1))
                    t = h * math.exp(-0.06 + 0.02 * rt.gauss(0, 1)) if not t_noise else rt.choice([math.inf, 1.0])
                    units.append({"slug": slug, "band": b, "cls": "clean" if i % 2 else "crunch", "amp": amp,
                                  "search": search, "held": held,
                                  "d": {"S": s, "H": h, "M": m, "T": t, "H_unshrunk": h * 1.01, "M_unshrunk": m * 1.02,
                                        "T_unshrunk": t},
                                  "rec": {}})
    return units


ROWS = ("all",)
FILT = {"all": lambda u: True}


def test_primary_is_untouched_by_T():
    a = M.contrast(toy_units(), "M", "H", ROWS, FILT)
    b = M.contrast(toy_units(t_noise=True), "M", "H", ROWS, FILT)
    assert a["rows"]["all"]["all"] == b["rows"]["all"]["all"] and a["directions"] == b["directions"] == 144
    t = M.contrast(toy_units(t_noise=True), "T", "H", ROWS, FILT)
    assert t["directions"] < 144                                          # T's refusals drop only T's contrasts


def test_drop_rule_per_contrast():
    units = toy_units()
    units[0]["d"]["M"] = math.inf
    units[1]["d"]["T"] = math.inf
    p = M.contrast(units, "M", "H", ROWS, FILT)
    t = M.contrast(units, "T", "H", ROWS, FILT)
    assert p["directions"] == 143 and t["directions"] == 142                # T's set includes the base's drops
    assert M.contrast_arms("M", "H") == ("S", "H", "M")
    assert M.contrast_arms("T", "H") == ("S", "H", "M", "T")
    assert M.contrast_arms("X", "S") == ("S", "H", "M", "X")
    assert M.contrast_arms("H_unshrunk", "H") == ("S", "H", "M", "H_unshrunk")


def test_contrast_matches_band_clustered_math():
    units = toy_units()
    c = M.contrast(units, "M", "H", ROWS, FILT)["rows"]["all"]["all"]
    pm = {}
    for u in units:
        pm.setdefault((u["slug"], u["band"]), []).append(math.log(u["d"]["M"] / u["d"]["H"]))
    bands = {}
    for (s, b), v in pm.items():
        bands.setdefault(b, []).append(sum(v) / len(v))
    bm = [sum(v) / len(v) for v in bands.values()]
    assert c["band_weighted_mean"] == pytest.approx(sum(bm) / len(bm))
    from scipy import stats
    import statistics
    half = stats.t.ppf(0.95, len(bm) - 1) * statistics.stdev(bm) / math.sqrt(len(bm))
    assert c["lo90"] == pytest.approx(c["band_weighted_mean"] - half) and c["bands"] == 12
    assert c["band_weighted_mean"] < 0                                    # M closer than H by construction


def test_share_of_t_is_fieller_on_band_means():
    units = toy_units()
    sh = M.share_of_t(units, ROWS, FILT)["all"]
    num, den = M.log_rows(units, "M", "H"), M.log_rows(units, "T", "H")
    want = C.share(num, den)
    assert sh["ratio"] == pytest.approx(want["ratio"]) and sh["bands"] == 12
    assert 0.2 < sh["ratio"] < 0.9


def test_share_of_t_is_unbounded_when_t_minus_h_contains_zero():
    units = toy_units()
    rng = random.Random(5)
    for u in units:                                                       # T − H centred on 0 with noise
        u["d"]["T"] = u["d"]["H"] * math.exp(0.05 * rng.gauss(0, 1))
    sh = M.share_of_t(units, ROWS, FILT)["all"]
    assert sh["bounded"] is False and sh["shape"] in ("two rays", "whole line") and sh["lo90"] is None


def test_rows_have_no_duplicates():
    for st in M.STAGES:
        r = M.rows_for(st)
        assert len(r) == len(set(r)) and r[0] == "all"


def test_rows_filters():
    bt = {"a-p0": {"source": "cambridge", "halves": {"A": {"flag": "low"}, "B": {"flag": "high"}}},
          "z-p0": {"source": "telefunken", "halves": {"A": {"flag": "low"}, "B": {"flag": "low"}}}}
    snr = {"a-p0": 0.5, "z-p0": 3.0}
    ua = {"slug": "a-p0", "band": "Zeno", "search": "A"}
    ub = {"slug": "a-p0", "band": "Zeno", "search": "B"}
    uz = {"slug": "z-p0", "band": "Wall Of Death", "search": "A"}
    f = {r: M.row_filter(r, "F", bt, snr) for r in M.rows_for("F")}
    assert not f["no_high_dir"](ua) and f["no_high_dir"](ub)               # direction A is judged on half B
    assert not f["no_high"](ub) and f["no_high"](uz)
    assert f["cambridge_only"](ua) and not f["cambridge_only"](uz)
    assert not f["without_musdb_train"](uz) and f["without_musdb_train"](ua)
    assert not f["without_any_musdb"](ua) and not f["without_any_musdb"](uz)
    assert f["snr_ge_1db"](uz) and not f["snr_ge_1db"](ua)
    assert not f["f_song"](ua) and f["f_song"]({"slug": "cambridge-wickerman-elecgtr1"})
    assert "f_song" not in M.rows_for("D")
    assert set(C.ROWS) <= set(M.rows_for("D"))


def test_completeness_gate():
    units = toy_units()[:142]
    assert M.complete(units, ("S", "H", "M"), 142) is None
    assert M.complete(units[:141], ("S", "H", "M"), 142)
    units[3]["d"]["M"] = None
    assert "missing" in M.complete(units, ("S", "H", "M"), 142)
    assert M.complete(units, ("S", "H"), 142) is None


def test_report_from_units_refuses_an_incomplete_primary_and_keeps_T_apart():
    units = toy_units()[:142]
    for u in units:
        u["rec"] = {a: {"fallback": None, "activity_fallback": 0, "s_check": {"dev": 0.001}} for a in ("H", "M", "T")}
    units[5]["d"]["T"] = None                                             # T incomplete: primary still read
    rep = M.report_from_units("D", units, ("H", "M", "T"), {"arm_x": None}, {}, {})
    assert rep["primary"]["refused"] is None and rep["primary"]["all"]["band_weighted_mean"] < 0
    assert rep["contrasts"]["T_minus_H"]["refused"] and rep["contrasts"]["H_minus_S"]["refused"] is None
    assert "share_M_of_T" in rep and rep["fallbacks"] == {"H": 0, "M": 0, "T": 0}
    units[7]["d"]["M"] = None
    rep = M.report_from_units("D", units, ("H", "M", "T"), {"arm_x": None}, {}, {})
    assert rep["primary"]["refused"] and rep["primary"]["all"] is None


def test_contrasts_for_x():
    c = M.contrasts_for("F", {"arm_x": "csep_mega53", "contrast": ["X", "M"]})
    assert c["P_F"] == ("M", "H") and c["X_minus_M"] == ("X", "M") and "T_minus_H" not in c
    assert "X_minus_H" in M.contrasts_for("D", {"arm_x": "csep_stem", "contrast": ["X", "H"]})


# --- stored inputs (zero renders) -------------------------------------------------------------------

def test_stored_s_keys_are_the_matched_configurations():
    from learn import local_objective as LO
    assert M.STORED_S["M"][1] == LO.cname(("cprime_mega53", "mega53", "native", "own"))
    assert M.STORED_S["T"][1] == LO.cname(LO.MATCHED)
    assert M.STORED_S["X:stem"][0] == LO.SEPNET_DI["stem"] and M.STORED_S["X:mega53"][0] == LO.SEPNET_DI["mega53"]


@pytest.mark.skipif(not (M.LO.OUT / "renders" / "cprime_mega53").exists(), reason="no stored 1c renders")
def test_stored_s_objectives_exist_for_every_stage_d_cell():
    for slug in M.d_parts():
        for amp in K.AMPS:
            for h in ("A", "B"):
                assert math.isfinite(M.stored_s_objective("M", slug, amp, h))
                assert math.isfinite(M.stored_s_objective("T", slug, amp, h))
