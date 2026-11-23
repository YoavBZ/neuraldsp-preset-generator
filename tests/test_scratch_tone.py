"""The tone split (`learn/scratch_tone.py`, `docs/scratch-search-plan.md` section 11): the frozen settings, the tilt
form and its fit, the planted sign, MC_TABLE (one reading a row, each row's from its own interval), the joint
sentences, TN_TABLE and its wording rule, the shares, phi, the reach rule, the linear answer, the per-part numbers, the
split's per-part body with a stub renderer (18 renders a part, the Cen control, the dry guitars' hashes before any
render), the key prefix outside every guarded prefix, and every refusal. Pure: runs on the light CI runner (no numpy).
The audio tests need numpy; the fit's numbers need the stored data (skipped elsewhere). No test names a part key."""
import itertools
import json
import math
import pathlib
import re

import pytest

from learn import note_transcribe as NT
from learn import scratch_notes as SN
from learn import scratch_search as S
from learn import scratch_tone as T

REPO = pathlib.Path(__file__).resolve().parents[1]


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


# --- the frozen settings ----------------------------------------------------------------------------------------------------

def test_the_frozen_settings():
    T.table_guard()
    assert (T.PHASE, T.PHASE_SPLIT, T.GATE) == ("phase_scratch_tone", "phase_scratch_tone_split",
                                                "phase_scratch_both_outcome")
    assert T.HELD_KEYS == ("phase_scratch_tone_hook", "phase_scratch_tone_answers", "phase_scratch_tone_outcome")
    assert T.ROWS == ("fs-stem", "fs-both") and T.ROW_OF == {"b": "fs-stem", "c": "fs-both"}
    assert T.PARTS == 47 and T.REFUSAL_STOP == 3 and (T.SMALL, T.BIG) == (S.SMALL, S.BIG) == (0.05, 0.10)
    assert dict(T.ARMS) == {"true": ("cen",), "true-noclip": ("cen", "c", "b"), "avg": ("c",),
                            "true+planted": ("c",), "true+tilt": ("c",), "avg+mild": ("cen", "c")}
    assert T.RENDERS_PER_PART == 18 and set(T.BUILT) | set(T.STORED_DRY) | {T.CODED} == set(T.DRIES)
    assert (T.PLANTED_DB, T.TILT_CAP, T.REACH, T.CLIP_DB) == (3.0, 8.0, 12.0, 15.0)
    assert (T.GRID_N, T.GRID_LO, T.GRID_HI, T.BAND) == (81, 80.0, 8000.0, (80.0, 8000.0))
    assert T.FIT_VERSION == 1 and T.fit_path().name == "fit-v1.json"
    assert set(T.C_NUMBERS) == {"C_fix", "C_avg", "C_planted", "C_tilt", "C_blur"}
    assert set(T.TONE_NUMBERS) == set(T.C_NUMBERS) - {"C_blur"}


def test_the_key_prefix_is_outside_every_guarded_prefix():
    pre = [p for ps in NT.KEY_PREFIXES.values() for p in ps]
    for k in (T.PHASE, T.PHASE_SPLIT) + T.HELD_KEYS:
        assert k.startswith(T.KEY_PREFIX)
        assert not k.startswith(tuple(pre)) and not k.startswith("phase_fs")
        assert not S.fs_keys({k: 1}) and not NT.guarded_keys({k: 1}, pre)
    assert T.tone_keys({T.PHASE: 1, "phase_scratch_notes": 2, "phase_fs": 3}) == {T.PHASE: 1}


def test_the_paths_sit_under_pf_fs_tone():
    for p in (T.fit_path(), T.dry_path("true-noclip", "x"), T.split_path("x"), T.rows_path(), T.report_path()):
        assert p.relative_to(S.fs_dir() / "tone")
    assert T.dry_path("true+tilt", "x", version=2) != T.dry_path("true+tilt", "x")
    with pytest.raises(ValueError):
        T.dry_path("avg", "x")                     # stored dry guitars are never written here


# --- the tilt and its fit ---------------------------------------------------------------------------------------------------

def test_the_tilt_form():
    g = T.tilt_gain_db([1000.0, 10000.0, 100.0, 20000.0, 20.0, 0.0, 3162.2776601683795], 3.0)
    assert g[0] == 0.0 and g[1] == pytest.approx(3.0) and g[2] == pytest.approx(-3.0)
    assert g[3] == 3.0 and g[4] == -3.0 and g[5] == -3.0          # flat outside
    assert g[6] == pytest.approx(1.5)
    assert T.tilt_gain_db([1000.0, 10000.0], -2.0) == [0.0, pytest.approx(-2.0)]


def test_the_grid():
    g = T.grid_freqs()
    assert len(g) == 81 and g[0] == pytest.approx(80.0) and g[-1] == pytest.approx(8000.0)
    assert all(b / a == pytest.approx(g[1] / g[0]) for a, b in zip(g, g[1:]))


@pytest.mark.parametrize("s", [3.0, -3.0, 0.7, -8.0])
def test_fit_slope_returns_a_planted_slope_exactly(s):
    grid = T.grid_freqs()
    curve = [v + 4.2 for v in T.tilt_gain_db(grid, s)]
    assert T.fit_slope(curve, grid) == pytest.approx(s, abs=1e-12)
    assert max(abs(v) for v in T.detilt(curve, grid, s)) < 1e-12
    assert T.rms(T.detilt(curve, grid, 0.0)) > 0


def test_capped_and_the_planted_sign():
    assert T.capped(9.5) == 8.0 and T.capped(-12.6) == -8.0 and T.capped(3.1) == 3.1
    import random

    for k in ("a|pr12", "b|ac20", "c|sw50r"):
        want = random.Random(f"20261202|mild|{k}").choice((-1, 1))
        assert T.planted_sign(k) == want and T.planted_slope(k) == 3.0 * want


# --- the readings and MC_TABLE --------------------------------------------------------------------------------------------

READ_IV = {"level": _iv(0.01, -0.04, 0.05), "moves+": _iv(0.08, 0.02, 0.14), "moves-": _iv(-0.06, -0.11, -0.01),
           "undecided": _iv(0.04, 0.01, 0.07), "wide": _iv(0.02, -0.12, 0.16), "short": _iv(-0.04, -0.07, -0.01)}


def test_every_interval_gives_exactly_one_reading_a_row_each_reachable():
    got = {}
    for name, iv in READ_IV.items():
        for row in ("c", "b"):
            c = T.row_code(row, iv)
            hits = [t for t in T.MC_TABLE if t[0] == c["code"]]
            assert len(hits) == 1 and hits[0][1] == row and c["code"].startswith(f"MC-{row}-")
            got.setdefault(row, set()).add(c["code"])
    assert got == {"c": {"MC-c-level", "MC-c-moves", "MC-c-undecided"},
                   "b": {"MC-b-level", "MC-b-moves", "MC-b-undecided"}}
    assert T.mc_reading(READ_IV["moves-"]) == "moves" and T.mc_reading(READ_IV["short"]) == "undecided"
    assert T.mc_reading(READ_IV["undecided"]) == "undecided"          # clear of zero, the mean under 0.05
    assert T.mc_reading(_iv(0.05, 0.01, 0.09)) == "moves"             # the mean at 0.05
    assert T.row_code("c", None) is None and T.row_code("b", {"mean": 0.1}) is None
    with pytest.raises(ValueError):
        T.row_code("a", READ_IV["level"])


def test_the_level_reading_is_not_readable_by_the_score():
    assert T.readable(READ_IV["level"]) is False and T.readable(_iv(0.0, -0.05, 0.05)) is False
    assert T.readable(READ_IV["moves+"]) is True and T.readable(None) is None
    assert T.row_code("c", READ_IV["level"])["readable"] is False


def test_p_b_never_changes_row_cs_code_nor_p_c_row_bs():
    for (nc, ivc), (nb, ivb) in itertools.product(READ_IV.items(), READ_IV.items()):
        assert T.row_code("c", ivc) == T.row_code("c", READ_IV[nc])
        assert T.row_code("b", ivb) == T.row_code("b", READ_IV[nb])
    for ivc in READ_IV.values():
        codes = {T.row_code("b", ivb)["code"] for ivb in READ_IV.values()}
        assert len(codes) == 3 and T.row_code("c", ivc)["code"] in {"MC-c-level", "MC-c-moves", "MC-c-undecided"}


def test_the_joint_sentences():
    assert T.mc_together("MC-c-level", "MC-b-level").startswith("rows (b) and (c) stand")
    assert T.mc_together("MC-c-moves", "MC-b-level").startswith("restate row (c)")
    for c in ("MC-c-level", "MC-c-moves", "MC-c-undecided"):
        assert "row (b)'s redo" in T.mc_together(c, "MC-b-moves")
    assert T.mc_together("MC-c-undecided", "MC-b-level") is None
    assert T.mc_together("MC-c-level", "MC-b-undecided") is None
    assert T.mc_together(None, None) is None


def test_mc_b_moves_claims_nothing_above_and_names_the_redo():
    text = dict((c, t) for c, _, _, t in T.MC_TABLE)["MC-b-moves"]
    assert "Nothing is claimed above it" in text and "not a ceiling" in text
    assert "12,351 + 940 renders, about 1 h 59 min" in text


# --- TN_TABLE --------------------------------------------------------------------------------------------------------------

C_IV = {"reach": _iv(-0.12, -0.2, -0.04), "below": _iv(-0.06, -0.1, -0.01), "level": _iv(0.0, -0.04, 0.04),
        "above": _iv(0.08, 0.02, 0.14), None: None}


def _reference_tn(cs):
    below = [n for n in T.C_NUMBERS if cs[n] is not None and cs[n]["hi90"] < 0]
    reach = cs["C_tilt"] is not None and cs["C_tilt"]["hi90"] < 0 and cs["C_tilt"]["mean"] <= -0.10
    return "TN-reach" if reach else "TN-short" if below else "TN-search"


def test_every_set_of_five_gives_exactly_one_tn_code_each_reachable():
    names = list(T.C_NUMBERS)
    seen = set()
    for combo in itertools.product(C_IV, repeat=len(names)):
        cs = {n: C_IV[c] for n, c in zip(names, combo)}
        got = T.tn_code(cs)
        assert got["code"] == _reference_tn(cs)
        seen.add(got["code"])
        if got["code"] == "TN-short":
            tone = any(cs[n] is not None and cs[n]["hi90"] < 0 for n in T.TONE_NUMBERS)
            assert got["wording"].startswith("the tone costs" if tone else "the blur (smear, soft clip and bleed")
    assert seen == set(T.TN_CODES)
    with pytest.raises(SystemExit):
        T.tn_code({"C_tilt": None})


def test_tn_short_says_tone_only_for_the_four_tone_numbers():
    base = {n: C_IV["level"] for n in T.C_NUMBERS}
    for n in T.C_NUMBERS:
        got = T.tn_code(dict(base, **{n: C_IV["below"]}))
        assert got["code"] == "TN-short" and got["below_zero"] == [n]
        assert got["tone"] == (n in T.TONE_NUMBERS)
        assert ("the tone costs" in got["wording"]) == (n != "C_blur")
    assert T.tn_code(dict(base, C_tilt=C_IV["reach"]))["code"] == "TN-reach"
    assert T.tn_code(dict(base, C_planted=C_IV["reach"]))["code"] == "TN-short"   # only C_tilt reaches
    assert T.tn_code(base)["wording"].startswith("not shown by the split")


# --- the numbers -------------------------------------------------------------------------------------------------------------

def test_the_restated_share_takes_both_through_true_noclip():
    got = T.shares({"mean": -0.10}, {"mean": -0.25}, {"mean": -0.315}, {"mean": -0.148})
    assert got["share_one_yardstick"] == pytest.approx(0.40)
    assert got["share_stored"] == pytest.approx(0.148 / 0.315)
    mixed = [k for k in got if "mixed" in k]
    assert mixed == ["share_mixed_c_rescored_over_b_stored"] and got[mixed[0]] == pytest.approx(0.10 / 0.315)
    assert T.shares(None, {"mean": -0.2}, None, None)["share_one_yardstick"] is None


def test_beyond_reach_and_the_linear_answer():
    assert T.beyond_reach(12.5, -3) and T.beyond_reach(3, -12.1) and not T.beyond_reach(12.0, -12.0)
    off = {k: "false" for k in S.DRIVE_KEYS}
    assert T.linear_answer(off) and T.linear_answer({})
    for k in S.DRIVE_KEYS:
        assert not T.linear_answer(dict(off, **{k: "true"}))
    assert T.linear_answer(dict(off, **{"gate/gateActive": "true"}))       # the gate does not count


def test_own_terms_and_the_part_values():
    held = {"true": {"cen": 1.0}, "true-noclip": {"cen": 1.2, "c": 1.0, "b": 0.9}, "avg": {"c": 1.1},
            "true+planted": {"c": 1.05}, "true+tilt": {"c": 0.95}, "avg+mild": {"cen": 1.3, "c": 1.2}}
    stored = {"G_c": math.log(0.9), "G_b": math.log(0.8), "c": 0.9}
    v = T.part_values(held, stored)
    assert v["G_c_noclip"] == pytest.approx(math.log(1.0 / 1.2)) and v["G_b_noclip"] == pytest.approx(math.log(0.75))
    assert v["P_c"] == pytest.approx(math.log(1.0 / 1.2) - math.log(0.9))
    assert v["P_b"] == pytest.approx(math.log(0.75) - math.log(0.8))
    for n, dry in T.C_NUMBERS.items():
        assert v[n] == pytest.approx(math.log(held[dry]["c"] / 0.9))
    assert v["cen_shift_noclip"] == pytest.approx(math.log(1.2)) and v["cen_shift_avg_mild"] == pytest.approx(
        math.log(1.3))
    assert v["c_own_terms_avg_mild"] == pytest.approx(math.log(1.2 / 1.3))
    assert T.own_terms(held, "avg", "c") is None                        # no Cen through avg
    assert T.part_values({"true": {"cen": 1.0}}, stored)["P_c"] is None


def test_held_values_apply_b3_inside_each_dry_guitar():
    rec = {"held": {"true": {"cen": 1.0}, "true-noclip": {"cen": 1.2, "c": math.inf, "b": 0.9},
                    "avg": {"c": math.inf}, "avg+mild": {"cen": math.inf, "c": 1.0}}}
    got, rep = T.held_values(rec)
    assert got["true-noclip"]["c"] == 1.2 and rep["true-noclip"] == ["c"]   # the worst finite, never better than Cen
    assert got["avg"] == {"c": 1.0} and rep["avg"] == ["c"]                 # the coded Cen stands in
    assert "avg+mild" not in got and rep["avg+mild"] == ["cen"]             # its own Cen non-finite: no numbers


def test_phi_part():
    err = [math.sin(i / 5) + 2.0 for i in range(81)]
    assert T.phi_part([-e for e in err], err) == pytest.approx(1.0)
    assert T.phi_part([7.0] * 81, err) == pytest.approx(0.0)
    assert T.phi_part([0.0] * 81, err) == 0.0
    assert T.phi_part([-0.3 * e + 1.0 for e in err], err) == pytest.approx(0.3)
    assert T.phi_part([e for e in err], err) == pytest.approx(-1.0)       # moved the wrong way
    assert T.phi_part(err, [3.0] * 81) is None


def _eq(amp, bands):
    return {f"{amp}EQ/{amp}EQBand{i}": f"{v:.3f}" for i, v in enumerate(bands, 1)}


def test_phi_eq_is_one_for_full_compensation_by_octave_bands():
    slopes = {"p": 3.0, "q": -3.0, "r": 1.5, "s": -6.0}
    amps = {"p": "pr12", "q": "ac20", "r": "sw50r", "s": "pr12"}
    other = {"pr12": "ac20", "ac20": "sw50r", "sw50r": "pr12"}
    flat = {k: {**_eq(a, [0.0] * 9), **_eq(other[a], [5.0 * i for i in range(9)])} for k, a in amps.items()}
    full = {k: {**_eq(a, [-(i - 5) * T.EQ_BAND_DECADES * slopes[k] for i in range(1, 10)]),
                **_eq(other[a], [0.0] * 9)} for k, a in amps.items()}
    got = T.phi_eq(flat, full, slopes, amps)
    assert got["parts"] == 4 and got["phi"] == pytest.approx(1.0, abs=1e-3)       # every other amp's EQ ignored
    assert T.phi_eq(flat, flat, slopes, amps)["phi"] == pytest.approx(0.0)
    assert T.phi_eq(flat, full, {"p": 3.0}, amps)["phi"] is None
    assert T.eq_slope({"x": 1}, "pr12") is None


def test_negated_is_minus_c_avg():
    assert T.negated(_iv(-0.1, -0.2, 0.02)) == _iv(0.1, -0.02, 0.2)
    assert T.negated(None) is None


# --- the split's per-part body, with a stub renderer ----------------------------------------------------------------------

def _stub(cen_ok=True):
    calls = []

    def score(dry, select, settings):
        calls.append((dry, settings["name"]))
        if dry == "true" and settings["name"] == "cen":
            return (1.0 if cen_ok else 1.01), "cen-sha", [0.0] * 81
        return 0.9, f"{dry}-{settings['name']}", [float(len(calls))] * 81
    return calls, score


def _split(k, calls_score, want=None):
    calls, score = calls_score
    dries = {d: f"audio-{d}" for d in T.DRIES}
    want = want or {d: f"sha-{d}" for d in T.DRIES}
    sets = {n: ("sel", {"name": n}) for n in ("cen", "c", "b")}
    return T.split_part(k, dries, want, lambda a: "sha-" + a.split("-", 1)[1], sets, score,
                        {"b": (1.0, "cen-sha"), "c": (1.0, "cen-sha")}), calls


def test_the_split_renders_18_a_part():
    for k in ("first", "second"):
        rec, calls = _split(k, _stub())
        assert rec["renders"] == 18 and len(calls) == 9 and "refused" not in rec
        assert calls[0] == ("true", "cen")                         # the control first
        assert sorted(calls) == sorted((d, n) for d, ns in T.ARMS for n in ns)
        assert set(rec["held"]) == set(T.DRIES) and set(rec["spectra_noclip"]) == {"c", "b"}
        assert rec["control"]["ok"] and rec["dry_sha256"] == {d: f"sha-{d}" for d in T.DRIES}
        assert not any(isinstance(v, dict) and "settings" in v for v in rec.values())


def test_a_wrong_cen_refuses_the_part():
    rec, calls = _split("x", _stub(cen_ok=False))
    assert "refused" in rec and rec["renders"] == 2 and calls == [("true", "cen")]
    assert not rec["control"]["ok"] and "held" not in rec
    v = T.control_verdict(1.0, "h", {"b": (1.0, "h"), "c": (1.0, "other")})
    assert not v["ok"]                                             # both rows' stored render must match


def test_a_wrong_dry_guitar_sha256_refuses_before_any_render():
    for d in T.DRIES:
        want = {q: f"sha-{q}" for q in T.DRIES}
        want[d] = "sha-something-else"
        calls_score = _stub()
        with pytest.raises(SystemExit, match=re.escape(d)):
            _split("x", calls_score, want)
        assert calls_score[0] == []


# --- the refusals --------------------------------------------------------------------------------------------------------

def test_the_declaration_refusal():
    good = {T.PHASE: {"fit": {"version": 1, "sha256": "F"}, "user_go": {"date": "2026-11-23"}}, T.GATE: {}}
    assert T.declaration_refusal(good, "F") is None
    assert "has no phase_scratch_tone" in T.declaration_refusal({}, "F")
    assert "not this fit" in T.declaration_refusal(good, "G")
    assert "not this fit" in T.declaration_refusal(
        {**good, T.PHASE: {**good[T.PHASE], "fit": {"version": 2, "sha256": "F"}}}, "F")
    assert "no user's go" in T.declaration_refusal({**good, T.PHASE: {"fit": {"version": 1, "sha256": "F"}}}, "F")
    assert T.GATE in T.declaration_refusal({T.PHASE: good[T.PHASE]}, "F")


@pytest.mark.parametrize("cmd", ["split", "split-read"])
def test_the_split_and_its_read_refuse_off_main(monkeypatch, cmd):
    monkeypatch.setattr(T, "on_main", lambda: (None, "this checkout's learn/scratch_tone.py differs from main's"))
    with pytest.raises(SystemExit, match="differs from main's"):
        T.COMMANDS[cmd](type("A", (), {"shard": (0, 1)})())


@pytest.mark.parametrize("cmd", ["split", "split-read"])
def test_the_split_and_its_read_refuse_without_the_fit_or_the_declaration(monkeypatch, tmp_path, cmd):
    monkeypatch.setattr(T, "on_main", lambda: ({T.GATE: {}}, None))
    monkeypatch.setattr(T, "fit_path", lambda version=1: tmp_path / f"fit-v{version}.json")
    with pytest.raises(SystemExit, match="no fit v1"):
        T.COMMANDS[cmd](type("A", (), {"shard": (0, 1)})())
    (tmp_path / "fit-v1.json").write_text("{}")
    with pytest.raises(SystemExit, match="has no phase_scratch_tone"):
        T.COMMANDS[cmd](type("A", (), {"shard": (0, 1)})())


def test_the_fit_refuses_off_main(monkeypatch, tmp_path):
    (tmp_path / "draw.json").write_text("{}")
    monkeypatch.setattr(S, "draw_path", lambda: tmp_path / "draw.json")
    monkeypatch.setattr(S, "on_main", lambda: (None, "this checkout's learn/scratch_search.py differs from main's"))
    with pytest.raises(SystemExit, match="differs from main's"):
        T.cmd_fit(None)


def test_on_main_guards_both_files():
    assert T.CODE_FILES == ("learn/scratch_search.py", "learn/scratch_tone.py")


# --- the ledger and the repo ----------------------------------------------------------------------------------------------

def _ladder():
    d = json.loads((REPO / "docs/dev-test-ledger.json").read_text())
    return next(t for t in d["tests"] if t.get("test_id") == T.LEDGER_ID)


def test_the_ledger_holds_the_declaration_and_holds_fs_tone_back():
    e = _ladder()
    rec = e[T.PHASE]
    assert rec["fit"]["version"] == T.FIT_VERSION and re.fullmatch(r"[0-9a-f]{64}", rec["fit"]["sha256"])
    assert rec["user_go"]["date"] == "2026-11-23" and "Run the quick check" in rec["user_go"]["answer"]
    assert rec["held"]["row"] == T.HELD_ROW
    assert set(rec["mc_table"]) == set(T.MC_CODES) and set(rec["tn_table"]) == set(T.TN_CODES)
    assert rec["renders"] == 846 == T.PARTS * T.RENDERS_PER_PART
    for k in T.HELD_KEYS + (T.PHASE_SPLIT,):
        assert k not in e                                          # nothing beyond the declaration yet
    assert set(T.tone_keys(e)) == {T.PHASE}


def test_no_part_key_and_no_module_level_numpy_in_these_files():
    for f in (REPO / "tests/test_scratch_tone.py", REPO / "learn/scratch_tone.py"):
        text = f.read_text()
        assert not re.search(r"\b(bks|goat|panel)__", text), f
        assert not re.search(r"^(import numpy|from numpy)", text, re.M), f
    rec = json.dumps(_ladder()[T.PHASE])
    assert not re.search(r"\b(bks|goat|panel)__", rec) and "/Users/" not in rec


# --- with numpy -------------------------------------------------------------------------------------------------------------

def test_the_tilt_form_is_degrades_formula():
    np = pytest.importorskip("numpy")
    f = np.fft.rfftfreq(4096, 1 / 48000)
    for sign in (-1, 1):
        want = sign * 3.0 * np.clip((np.log10(np.maximum(f, 1)) - 3.0), -1, 1)
        assert np.array_equal(T.tilt_gain_db(f, 3.0 * sign), want)
    assert T.tilt_gain_db(f, 3.0)[0] == -3.0


def test_apply_tilt_on_noise():
    np = pytest.importorskip("numpy")
    from learn import di_robustness as DR

    x = np.random.default_rng(7).standard_normal(48000 * 4).astype(np.float32)
    assert T.apply_tilt(x, 0) is x
    grid = T.grid_freqs()
    base = T.on_grid(DR.smoothed_spectrum(x.astype(np.float64)))
    for s in (3.0, -5.0):
        y = T.apply_tilt(x, s)
        assert y.dtype == np.float32 and len(y) == len(x)
        rx, ry = np.sqrt(np.mean(x.astype(np.float64) ** 2)), np.sqrt(np.mean(y.astype(np.float64) ** 2))
        assert abs(ry / rx - 1) < 1e-6
        moved = T.fit_slope(T.on_grid(DR.smoothed_spectrum(y.astype(np.float64))) - base, grid)
        assert abs(moved - s) < 0.1
        c = np.fft.irfft(np.fft.rfft(x, 2 * len(x)) * np.conj(np.fft.rfft(y, 2 * len(x))))
        assert int(np.argmax(np.abs(c))) == 0


def test_no_clip_measure_equals_measure_where_the_gain_never_clips(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    pytest.importorskip("pyloudnorm")
    from learn import confirm_run as CR
    from learn import di_robustness as DR
    from learn import song_bank as SB

    x = np.random.default_rng(3).standard_normal(48000 * 3).astype(np.float32) * 0.05
    own = DR.smoothed_spectrum(x.astype(np.float64))
    avg = (own - own.mean()) + np.asarray(T.tilt_gain_db(np.fft.rfftfreq(4096, 1 / 48000), 4.0))
    np.save(tmp_path / "avg.npy", avg)
    monkeypatch.setattr(CR, "AVERAGE", tmp_path / "avg.npy")
    assert np.abs(T.measure_gain(x)).max() < 15
    assert np.array_equal(T.no_clip_measure(x), SB.measure(x))
    np.save(tmp_path / "avg.npy", avg + np.asarray(T.tilt_gain_db(np.fft.rfftfreq(4096, 1 / 48000), 30.0)))
    assert np.abs(T.measure_gain(x)).max() > 15
    assert not np.allclose(T.no_clip_measure(x), SB.measure(x))     # where it clips, they part


def test_band_distance_is_zero_for_a_constant_offset():
    np = pytest.importorskip("numpy")
    a = np.linspace(-20, 5, 2049)
    assert T.band_distance(a + 3.0, a) == pytest.approx(0.0, abs=1e-12)
    assert T.band_distance(a, np.zeros(2049)) > 0


# --- with the stored data --------------------------------------------------------------------------------------------------

def _fit():
    pytest.importorskip("numpy")
    if not T.fit_path().exists() or not S.draw_path().exists():
        pytest.skip("no stored fit")
    return json.loads(T.fit_path().read_text())


def test_the_fit_is_the_declared_one():
    _fit()
    assert S.file_sha(T.fit_path()) == _ladder()[T.PHASE]["fit"]["sha256"]


def test_the_fit_reproduces_section_2():
    fit = _fit()
    s = fit["summary"]
    goat, forty, all47 = s["goat"], s["bks_goat"], s["all"]
    assert goat["parts"] == 24 and forty["parts"] == 40 and all47["parts"] == 47
    assert goat["err_rms_over_parts_and_grid"] == pytest.approx(3.69, abs=0.02)
    assert goat["err_rms_after_tilt_over_parts_and_grid"] == pytest.approx(2.11, abs=0.02)
    assert forty["err_rms_over_parts_and_grid"] == pytest.approx(3.34, abs=0.02)
    assert forty["err_rms_after_tilt_over_parts_and_grid"] == pytest.approx(2.07, abs=0.02)
    assert forty["slopes_inside_cap"] == 38
    assert forty["dist_true"]["mean"] == pytest.approx(2.7, abs=0.1)
    assert forty["dist_true"]["max"] == pytest.approx(7.1, abs=0.1)
    assert forty["dist_true_noclip"]["mean"] == pytest.approx(1.3, abs=0.1)
    assert forty["dist_true_noclip"]["max"] == pytest.approx(2.0, abs=0.1)
    assert forty["planted_sign_matches_mild"] == 40
    assert all47["beyond_reach"] == 38
    assert all47["fixed_avg_vs_avg"]["mean"] == pytest.approx(1.03, abs=0.1)
    assert all47["fixed_avg_vs_avg"]["max"] == pytest.approx(1.53, abs=0.1)
    assert all47["fixed_avg_vs_true_noclip"]["mean"] == pytest.approx(0.65, abs=0.1)
    assert all47["hf_rise_db"]["max"] == pytest.approx(13.4, abs=0.1)
    assert all47["peak_rise_db"]["max"] == pytest.approx(9.8, abs=0.1)
    assert forty["avg_vs_true_noclip"]["mean"] == pytest.approx(1.2, abs=0.1)
    assert forty["avg_vs_true"]["mean"] == pytest.approx(2.4, abs=0.1)
    assert s["panel"]["avg_vs_true_noclip"]["mean"] == pytest.approx(0.8, abs=0.1)
    assert s["panel"]["avg_vs_true"]["mean"] == pytest.approx(3.1, abs=0.1)
    for k, r in fit["parts"].items():
        assert set(r["sha256"]) == set(T.DRIES) and len(r["err_curve"]) == T.GRID_N
        assert r["slope_used"] == T.capped(r["slope_fit"]) and r["slope_planted"] == T.planted_slope(k)


def test_the_stored_answers_linear_group():
    fit = _fit()
    ans = json.loads(S.answers_path("fs-both").read_text())["parts"]
    lin = {k for k, a in ans.items() if T.linear_answer(a["answer"])}
    sets = {k: (r["set"], r["cls"]) for k, r in fit["parts"].items()}
    forty = [k for k in lin if sets[k][0] in ("bks", "goat")]
    assert len(forty) == 12 and sum(sets[k][1] == "clean" for k in forty) == 10
    assert len(lin) - len(forty) == 3


def test_phi_from_the_eq_answers_reproduces_the_review():
    fit = _fit()
    a = {r: json.loads(S.answers_path(r).read_text())["parts"] for r in T.ROWS}
    sets = {k: (r["set"], r["cls"]) for k, r in fit["parts"].items()}
    amps = {p["pkey"]: p["amp"] for p in json.loads(S.draw_path().read_text())["parts"]}

    def phi(sel):
        ks = [k for k in fit["parts"] if sel(sets[k])]
        return T.phi_eq({k: a["fs-stem"][k]["answer"] for k in ks}, {k: a["fs-both"][k]["answer"] for k in ks},
                        {k: fit["parts"][k]["slope_fit"] for k in ks}, amps)["phi"]
    assert phi(lambda s: s == ("goat", "clean")) == pytest.approx(0.3, abs=0.1)
    assert phi(lambda s: s[0] in ("bks", "goat") and s[1] == "clean") == pytest.approx(0.45, abs=0.1)
    assert phi(lambda s: s[0] in ("bks", "goat") and s[1] == "crunch") == pytest.approx(0.0, abs=0.1)


def test_the_first_parts_built_guitars_are_the_fits():
    fit = _fit()
    np = pytest.importorskip("numpy")
    from learn import note_replay as R
    from learn import pretrain_set as PS

    draw = json.loads(S.draw_path().read_text())
    p = sorted(draw["parts"], key=lambda q: q["pkey"])[0]
    k = p["pkey"]
    sd = R.Stored()
    prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
    di32 = R.di_section(prt)
    raw = np.asarray(PS.section_audio(prt["di_path"], prt["start_s"]), np.float64)
    want = fit["parts"][k]["sha256"]
    assert S.npy_sha(di32) == want["true"]
    assert S.npy_sha(np.asarray(T.no_clip_measure(raw), np.float32)) == want["true-noclip"]
    assert S.npy_sha(T.apply_tilt(di32, T.planted_slope(k))) == want["true+planted"]
    assert S.npy_sha(T.apply_tilt(di32, fit["parts"][k]["slope_used"])) == want["true+tilt"]
    for d in T.BUILT:
        assert S.file_sha(T.dry_path(d, k)) == want[d]
