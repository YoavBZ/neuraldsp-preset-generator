"""The rank-margin ladder's pure parts (`learn/rank_margin.py`, `docs/rank-margin-ladder-plan.md`)."""

import math

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
pytest.importorskip("pyloudnorm")

from learn import rank_margin as RM  # noqa: E402

SR = RM.SR


def plucked(seconds=3.0, seed=0):
    """Plucked notes: harmonic tones with exponential decays and uneven note levels."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    x = np.zeros(n)
    t0 = 0
    while t0 < n - SR // 10:
        dur = int(rng.uniform(0.15, 0.45) * SR)
        f0 = rng.uniform(110, 440)
        t = np.arange(min(dur, n - t0)) / SR
        note = sum(np.sin(2 * np.pi * f0 * k * t + rng.uniform(0, 6)) / k for k in range(1, 12))
        x[t0:t0 + len(t)] += rng.uniform(0.2, 1.0) * np.exp(-t / rng.uniform(0.05, 0.2)) * note
        t0 += dur
    x += 1e-4 * rng.standard_normal(n)
    return RM.to_lufs(x)


@pytest.fixture(scope="module")
def sig():
    return plucked()


def _bands(x, ref):
    return RM.band_levels(x, ref)


# --- the rungs ----------------------------------------------------------------------------------

@pytest.mark.parametrize("delta", [1.5, 3.0])
def test_compressor_solves_crest_on_the_final_signal_and_keeps_the_spectrum(sig, delta):
    y, meta = RM.compress_to_crest(sig, delta)
    assert meta["reached"]
    # the crest is measured on the final, re-EQ'd, LUFS-matched output
    assert abs((RM.crest_db(sig) - RM.crest_db(y)) - delta) <= RM.CREST_TOL
    assert abs(meta["crest_change"] + delta) <= RM.CREST_TOL
    assert all(abs(b) < 0.5 for b in _bands(y, sig))
    assert abs(RM.rms(y) / RM.rms(RM.to_lufs(y)) - 1) < 1e-3          # already at −22.9 LUFS


def test_compressor_without_reduction_returns_x(sig):
    y, meta = RM.compress_to_crest(sig, 0)
    assert np.array_equal(y, sig) and meta["reached"]


def test_unreachable_crest_is_reported():
    x = RM.to_lufs(np.sin(2 * np.pi * 220 * np.arange(2 * SR) / SR))   # a flat envelope
    y, meta = RM.compress_to_crest(x, 5.0)
    assert not meta["reached"] and meta["ratio"] == 10.0


@pytest.mark.parametrize("fn", [lambda x: RM.envelope_smear(x, 10.0), lambda x: RM.envelope_smear(x, 30.0),
                                lambda x: RM.envelope_swap(x, plucked(seed=3)),
                                lambda x: RM.transplant(x, plucked(seed=4), 5.0)])
def test_dynamics_rungs_keep_the_long_term_spectrum(sig, fn):
    y = fn(sig)
    assert len(y) == len(sig) and np.all(np.isfinite(y))
    assert all(abs(b) < 0.5 for b in _bands(y, sig))


@pytest.mark.parametrize("fn,below", [(RM.placebo_smear, None), (lambda x: RM.shelf(x, -4), None),
                                      (lambda x: RM.bell(x, 5), None), (lambda x: RM.envelope_smear(x, 10.0), None),
                                      (lambda x: RM.phase_scramble(x, 7, x), 1000),
                                      (lambda x: RM.bleed(x, plucked(seed=5), -10), None)])
def test_every_rung_keeps_length_level_and_alignment(sig, fn, below):
    import pyloudnorm

    y = fn(sig)
    assert len(y) == len(sig) and np.all(np.isfinite(y))
    assert abs(pyloudnorm.Meter(SR).integrated_loudness(y) + 22.9) < 0.05
    lag = RM.gcc_lag(y, sig, below_hz=below)                # as `build_variants` checks it
    assert lag == 0 if below is None else abs(lag) <= RM.LAG_TOL


def test_shelf_and_bell_match_their_curves(sig):
    f = np.fft.rfftfreq(4096, 1 / SR)
    for y, curve in ((RM.shelf(sig, -4), RM.shelf_curve(-4)), (RM.bell(sig, 3), RM.bell_curve(3))):
        got = RM.lt(y) - RM.lt(sig)
        want = curve - curve.mean()
        m = (f >= 100) & (f <= 8000)
        err = (got - want)[m]
        assert abs(np.median(err - np.median(err))) < 0.3
        assert np.percentile(np.abs(err - np.median(err)), 90) < 0.3


def test_bell_curve_shape():
    f = np.fft.rfftfreq(4096, 1 / SR)
    c = RM.bell_curve(5.0)
    assert np.allclose(c[(f >= 200) & (f <= 1000)], 5.0)
    assert np.all(c[f < 200 / math.sqrt(2) - 1] == 0) and np.all(c[f > 1000 * math.sqrt(2) + 1] == 0)


def test_placebo_smear_barely_moves_the_envelope(sig):
    y = RM.placebo_smear(sig)
    ey, ex = RM._frames_db(y), RM._frames_db(sig)
    p = ex >= ex.max() - 40
    assert np.corrcoef(ey[p], ex[p])[0, 1] >= 0.99


def test_phase_scramble_keeps_the_spectrum_and_is_deterministic(sig):
    a, b = RM.phase_scramble(sig, 11, sig), RM.phase_scramble(sig, 11, sig)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, RM.phase_scramble(sig, 12, sig))
    assert all(abs(x) < 0.5 for x in _bands(a, sig))


def test_phase_scramble_is_aligned_by_construction():
    x = np.zeros(2 * SR)
    x[::4800] = 1.0
    x = RM.to_lufs(x + 1e-6 * np.random.default_rng(0).standard_normal(len(x)))
    assert abs(RM.gcc_lag(RM.phase_scramble(x, 1, x), x, below_hz=1000)) <= RM.LAG_TOL


def test_transplant_onto_itself_is_identity_and_recovers_an_envelope(sig):
    y = RM.transplant(sig, sig, 10.0)
    assert np.max(np.abs(y - sig)) < 1e-3 * np.max(np.abs(sig))
    rng = np.random.default_rng(9)
    t = np.arange(3 * SR) / SR
    known = 0.2 + np.abs(np.sin(2 * np.pi * 1.5 * t))            # a slow, known envelope
    carrier = RM.to_lufs(rng.standard_normal(len(t)))
    z = RM.transplant(carrier, RM.to_lufs(known * rng.standard_normal(len(t))), 10.0)
    ez, ek = RM._frames_db(z), 20 * np.log10(known[:len(RM._frames_db(z)) * 480].reshape(-1, 480).mean(1))
    assert np.corrcoef(ez, ek)[0, 1] > 0.95


def test_gcc_lag_finds_a_shift(sig):
    assert RM.gcc_lag(np.roll(sig, 7), sig) == 7


# --- proxies ------------------------------------------------------------------------------------

def test_proxies_are_perfect_against_themselves_and_respect_the_floor():
    x = plucked(seconds=10.5, seed=2)
    p = RM.proxies(x, x, "full")
    assert p["crest_err"] == 0 and p["spread_err"] == 0 and abs(p["onset_err"]) < 1e-9
    assert abs(p["coherence"] - 1) < 1e-6 and p["env_corr"] == pytest.approx(1.0)
    flat = RM.to_lufs(np.sin(2 * np.pi * 220 * np.arange(int(10.5 * SR)) / SR))
    assert RM.proxies(flat, flat, "full")["env_corr"] is None


# --- the margin and step A ----------------------------------------------------------------------

def test_margin_signs():
    assert RM.margin(2.0, 1.0) > 0 and RM.margin(1.0, 2.0) < 0
    assert RM.margin(None, 1.0) is None and RM.margin(math.inf, 1.0) is None


def _rows(measure, cprime):
    """measure/cprime: lists of (m > 0, success)."""
    return ([{"run": "measure", "m": 1.0 if a else -1.0, "success": s} for a, s in measure]
            + [{"run": "cprime", "m": 1.0 if a else -1.0, "success": s} for a, s in cprime])


def test_step_a_run_identity_baseline_is_not_adopted():
    # all measure searches succeed with m > 0; C′: 3 successes, 6 failures, m ≤ 0 everywhere
    rows = _rows([(True, True)] * 9, [(False, True)] * 3 + [(False, False)] * 6)
    r = RM.step_a_rule(rows)
    assert r["agree"] == 15 and not r["cprime_row"] and r["verdict"] == "screen"


def test_step_a_provisional_and_not_adopted():
    rows = _rows([(True, True)] * 9, [(True, True)] * 2 + [(False, True)] + [(False, False)] * 4 + [(True, False)] * 2)
    r = RM.step_a_rule(rows)
    assert r["agree"] == 15 and r["cprime_row"] and r["verdict"] == "provisional"
    assert r["table"] == {"m>0&ok": 11, "m>0&miss": 2, "m<=0&ok": 1, "m<=0&miss": 4}
    bad = _rows([(False, True)] * 6 + [(True, True)] * 3, [(True, False)] * 6 + [(False, True)] * 3)
    assert RM.step_a_rule(bad)["verdict"] == "not adopted"


def test_step_a_lags_must_agree():
    assert RM.combine_lags({"0": {"verdict": "provisional"}, "-52": {"verdict": "provisional"}}) == "provisional"
    assert RM.combine_lags({"0": {"verdict": "provisional"}, "-52": {"verdict": "screen"}}).startswith("screen")


def test_informative_rule():
    res = {"a": {"S": {"B": 3.0}, "target": {"B": 2.85}}, "b": {"S": {"B": 3.0}, "target": {"B": 2.95}}}
    assert RM.informative_from(res) == ["a"]


def test_predictions():
    assert RM.predictions({"x": 0.2, "y": -0.1, "z": None}) == {"x": True, "y": False, "z": None}


# --- draws and leaks ----------------------------------------------------------------------------

def test_bleed_draw_is_deterministic_and_outside_the_control_bands():
    parts = {f"p{i}": {"band": f"b{i % 5}"} for i in range(20)}
    parts["telefunken-Honey-GTR"] = {"band": "honey"}
    a = RM.draw_bleed(parts, {"b0", "b1"})
    assert a == RM.draw_bleed(parts, {"b0", "b1"}) and parts[a]["band"] not in {"b0", "b1", "honey"}


def test_bleed_draw_on_the_catalogue():
    try:
        part = RM.bleed_part()
    except (FileNotFoundError, KeyError, OSError) as e:
        pytest.skip(f"catalogue not available: {e}")
    assert part == "cambridge-get-out-of-bed-elecgtr1"


def test_leak_assertion():
    k3 = {"BandA": 1, "BandB": 3}
    assert RM.leaks("BandA", 3, 1, k3, set())                 # another fold's C′
    assert not RM.leaks("BandA", 1, 1, k3, set())             # its own fold
    assert RM.leaks("Set2Band", 1, 1, k3, {"Set2Band"})       # trained every fold
    assert not RM.leaks("Set3Band", 2, 2, k3, set())          # never trained


def test_render_cap():
    assert RM.cap_ok(0, 4) and RM.cap_ok(RM.CAP - 12, 4)
    assert not RM.cap_ok(RM.CAP - 11, 4) and not RM.cap_ok(RM.CAP, 1)


# --- decisions ----------------------------------------------------------------------------------

INF = [f"c{i}" for i in range(9)]


def _m(base=None, **variants):
    """variant -> cell -> m; base > 0 on all 9 informative cells unless given."""
    out = {"base": base or {c: 0.3 for c in INF}}
    for v, spec in variants.items():
        out[v.replace("_", "-")] = spec
    return out


def _inv(k, cells=INF):
    """m ≤ 0 on the first k cells, > 0 on the rest."""
    return {c: (-0.1 if i < k else 0.2) for i, c in enumerate(cells)}


def test_inversions_use_the_base_set():
    base = {c: 0.3 for c in INF}
    base["c0"] = -0.05                                         # half disagrees: not in the base set
    m = _m(base=base, crest_3={**_inv(3), "c8": None})         # c8 unreached
    inv, n = RM.count_inversions(m, "crest-3", INF)
    assert (inv, n) == (2, 7)                                  # c1, c2 of c1..c7


def test_d1_readings():
    rows = dict(placebo_smear=_inv(0), cprime_spectrum=_inv(1))
    assert RM.d1(_m(crest_3=_inv(5), **rows), INF)["reading"] == "dynamics confirmed"
    assert RM.d1(_m(crest_3=_inv(5), placebo_smear=_inv(0), cprime_spectrum=_inv(2)), INF)["reading"] \
        == "dynamics and tilt"
    assert RM.d1(_m(crest_3=_inv(4), placebo_smear=_inv(0), cprime_spectrum=_inv(5)), INF)["reading"] \
        == "tilt, not dynamics"
    assert RM.d1(_m(crest_3=_inv(4), **rows), INF)["reading"] == "neither"
    assert RM.d1(_m(crest_3=_inv(9), placebo_smear=_inv(2), cprime_spectrum=_inv(0)), INF)["reading"].startswith(
        "undecided (placebo")
    few = {c: (-0.1 if c in INF[:4] else None) for c in INF}  # crest −3 reached on 4 cells
    assert RM.d1(_m(crest_3=few, **rows), INF)["reading"].startswith("undecided (crest")


def test_d1_rescales_with_the_reached_count():
    # Passing Ships' 2 cells unreached: crest −3 reached on 7, half rounded up is 4
    seven = {**_inv(4, INF[:7]), "c7": None, "c8": None}
    assert RM.d1(_m(crest_3=seven, placebo_smear=_inv(0), cprime_spectrum=_inv(1)), INF)["reading"] \
        == "dynamics confirmed"


def test_d2_readings():
    def m(t5, t10, teq, cp=_inv(9)):
        return _m(cprime=cp, transplant_5=t5, transplant_10=t10, cprime_eq_transplant_10=teq)
    assert RM.d2(m(_inv(3), _inv(9), _inv(9)), INF)["reading"] == "plain transplant restores"     # 6/9 > 0
    assert RM.d2(m(_inv(4), _inv(4), _inv(2)), INF)["reading"] == "only the oracle-EQ transplant restores"
    assert RM.d2(m(_inv(4), _inv(4), _inv(4)), INF)["reading"] == "none restores"
    # must also beat C′ itself
    assert RM.d2(m(_inv(3), _inv(3), _inv(3), cp=_inv(0)), INF)["reading"] == "none restores"


def test_within_cell_rho():
    assert RM.within_cell_rho({"a": 1, "b": 2, "c": 3}, {"a": 0.1, "b": 0.2, "c": 0.3}) == pytest.approx(1)
    assert RM.within_cell_rho({"a": 1, "b": 2}, {"a": 0.1, "b": 0.2}) is None
    assert RM.within_cell_rho({"a": 1, "b": 1, "c": 1}, {"a": 0.1, "b": 0.2, "c": 0.3}) is None


def _rho(cells_by_band, value):
    return {c: value(b) for b, cs in cells_by_band.items() for c in cs}


def test_d3_adoption():
    bands = {f"B{i}": [f"B{i}c0", f"B{i}c1"] for i in range(6)}
    band_of = {c: b for b, cs in bands.items() for c in cs}
    rho = {p: _rho(bands, lambda b: 0.1) for p in RM.PROXIES}
    rho["crest_err"] = _rho(bands, lambda b: 0.8)                     # strong, every band
    rho["env_corr"] = _rho(bands, lambda b: 0.9 if b != "B0" else -0.5)  # beats coherence in 5 of 6
    rho["spread_err"] = _rho(bands, lambda b: 0.9 if b not in ("B0", "B1") else 0.0)  # 4 of 6
    rho["lsd"] = _rho(bands, lambda b: 0.95)                          # a baseline: never adopted
    r = RM.d3(rho, band_of, draws=2000)
    assert r["proxies"]["crest_err"]["passes"]
    assert r["proxies"]["env_corr"]["bands_beating_coherence"] == [5, 6]
    assert not r["proxies"]["spread_err"]["passes"]                    # beats coherence in 4 of 6 only
    assert not r["proxies"]["lsd"].get("passes")
    assert r["adopted"] == "crest_err"


def test_d3_requires_the_paired_bound():
    bands = {f"B{i}": [f"B{i}c0"] for i in range(6)}
    band_of = {c: b for b, cs in bands.items() for c in cs}
    rho = {p: _rho(bands, lambda b: 0.0) for p in RM.PROXIES}
    rho["coherence"] = _rho(bands, lambda b: 0.7)
    rho["crest_err"] = _rho(bands, lambda b: 0.75 if b != "B0" else 0.0)   # ρ ≥ 0.6, 5 of 6, bound ≤ 0
    r = RM.d3(rho, band_of, draws=2000)
    assert r["proxies"]["crest_err"]["bands_beating_coherence"] == [5, 6]
    assert r["proxies"]["crest_err"]["diff_lo90"] <= 0 and not r["proxies"]["crest_err"]["passes"]
