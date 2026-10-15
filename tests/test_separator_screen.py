"""The separator screen's pure parts (`learn/separator_screen.py`, `docs/separator-screen-plan.md`)."""

import importlib.util
import json
import math

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
pytest.importorskip("pyloudnorm")

from learn import separator_screen as SS  # noqa: E402

SR = SS.SR


def plucked(seconds=3.0, seed=0):
    """Plucked notes with sharp onsets, exponential decays and uneven note levels."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    x = np.zeros(n)
    t0 = SR // 20
    while t0 < n - SR // 10:
        dur = int(rng.uniform(0.15, 0.45) * SR)
        f0 = rng.uniform(110, 440)
        t = np.arange(min(dur, n - t0)) / SR
        note = sum(np.sin(2 * np.pi * f0 * k * t + rng.uniform(0, 6)) / k for k in range(1, 12))
        x[t0:t0 + len(t)] += rng.uniform(0.2, 1.0) * np.exp(-t / rng.uniform(0.05, 0.2)) * note
        t0 += dur
    return x + 1e-4 * rng.standard_normal(n)


@pytest.fixture(scope="module")
def sig():
    return plucked()


# --- the blend ----------------------------------------------------------------------------------

def test_blend_of_equal_stems_is_the_stem(sig):
    assert np.max(np.abs(SS.blend(sig, sig) - sig)) <= 1e-9


def test_blend_branches_are_complementary_and_minus_6_db_at_6k():
    from scipy.signal import sosfreqz

    f, h = sosfreqz(SS.crossover_sos(), worN=[1000.0, 6000.0, 12000.0], fs=SR)
    lp = np.abs(h) ** 2                                 # sosfiltfilt: |H|², zero phase
    hp = 1 - lp
    assert np.allclose(lp + hp, 1.0)
    assert abs(20 * np.log10(lp[1]) + 6.02) < 0.01     # amplitude
    assert abs(20 * np.log10(hp[1]) + 6.02) < 0.01
    assert lp[0] > 0.99 and hp[2] > 0.99


def test_blend_takes_each_stem_on_its_side():
    rng = np.random.default_rng(1)
    a, b = rng.standard_normal(SR), rng.standard_normal(SR)
    y = SS.blend(a, b)
    assert SS.blend_lag(y, a) == 0                       # zero phase: no shift
    lo = SS._band_db(y, a, 100, 3000)
    hi = SS._band_db(y, b, 10000, 20000)
    assert abs(lo) < 0.5 and abs(hi) < 0.5


def test_relative_lag_is_caught(sig):
    assert SS.blend_lag(sig, sig) == 0
    assert SS.blend_lag(np.roll(sig, 3), sig) == 3


# --- the MSST wrapper ---------------------------------------------------------------------------

class _Cfg:
    class training:
        instruments = ["vocals", "electric-guitar", "guitar"]


class _Model:
    def __init__(self):
        self.mask_estimators = ["h-vocals", "h-electric", "h-guitar"]
        self.num_stems = 3


def test_prune_keeps_only_the_named_head():
    m, c = SS.prune_heads(_Model(), _Cfg(), ["electric-guitar"])
    assert m.mask_estimators == ["h-electric"] and m.num_stems == 1
    assert c.training.instruments == ["electric-guitar"]


def _msst_importable():
    return all(importlib.util.find_spec(m) for m in ("torch", "einops", "rotary_embedding_torch", "beartype")) \
        and (SS.msst_root() / "repo/models/bs_roformer/bs_roformer.py").exists()


@pytest.mark.skipif(not _msst_importable(), reason="MSST imports not available in this interpreter")
def test_pruned_tiny_bsroformer_matches_the_full_model():
    import sys

    import torch

    sys.path.insert(0, str(SS.msst_root() / "repo"))
    from models.bs_roformer.bs_roformer import BSRoformer

    torch.manual_seed(0)
    kw = dict(dim=16, depth=1, stereo=True, num_stems=3, time_transformer_depth=1, freq_transformer_depth=1,
              freqs_per_bands=(64, 64, 129), dim_head=8, heads=2, flash_attn=False, stft_n_fft=512,
              stft_hop_length=128, stft_win_length=512, mask_estimator_depth=1)
    full = BSRoformer(**kw).eval()
    pruned = BSRoformer(**kw).eval()
    pruned.load_state_dict(full.state_dict())
    cfg = _Cfg()
    cfg.training.instruments = ["vocals", "electric-guitar", "guitar"]
    SS.prune_heads(pruned, cfg, ["electric-guitar"])
    x = torch.randn(1, 2, 8192)
    with torch.inference_mode():
        a, b = full(x)[:, 1], pruned(x)[:, 0]
    assert torch.equal(a, b)


def test_hash_check_refuses_a_changed_file(tmp_path):
    w = tmp_path / "weights" / "m.ckpt"
    w.parent.mkdir()
    w.write_bytes(b"weights")
    prov = {"commit": SS.MSST_COMMIT,
            "files": [{"path": "weights/m.ckpt", "sha256": SS._sha_file(w)}]}
    (tmp_path / "provenance.json").write_text(json.dumps(prov))
    assert SS.verify_msst(tmp_path)["files"][0]["path"] == "weights/m.ckpt"
    w.write_bytes(b"weights!")
    with pytest.raises(SystemExit):
        SS.verify_msst(tmp_path)


def test_resample_round_trip_keeps_the_length(sig):
    y = SS.to48(SS.to44(sig), len(sig))
    assert len(y) == len(sig)
    assert np.corrcoef(y, sig)[0, 1] > 0.99


# --- the fake and its level ---------------------------------------------------------------------

def test_fake_gain_lands_at_the_reference_loudness(sig):
    ref = 0.1 * plucked(seed=3)
    g = SS.fake_gain(sig, ref)
    assert abs(SS.loudness(g * sig) - SS.loudness(ref)) < 0.05


def test_di_gain_is_to_lufs():
    from learn.direc_check import to_lufs

    x = plucked(seed=4)
    assert np.allclose(SS.di_gain(x) * x, to_lufs(x))


# --- stem metrics -------------------------------------------------------------------------------

def test_metrics_are_zero_for_identical_signals(sig):
    m = SS.stem_metrics(sig, sig)
    assert abs(m["crest_err"]) < 1e-9 and abs(m["env_var_err"]) < 1e-9
    assert m["attack_slope_err"] == 0
    assert all(abs(v) < 1e-9 for v in m["edge"].values())


def test_compression_flattens_the_envelope(sig):
    y, meta = SS.RM.compress_to_crest(SS.RM.to_lufs(sig), 3.0)
    assert SS.env_variation_err(y, SS.RM.to_lufs(sig)) < 0


def test_a_10_ms_envelope_smear_blunts_attacks(sig):
    x = SS.RM.to_lufs(sig)
    y = SS.RM.envelope_smear(x, 10.0)                    # the ladder's attack-slowing rung
    assert SS.onsets(x)
    assert SS.attack_slope_err(y, x) < 0


# --- decisions ----------------------------------------------------------------------------------

CELLS = [f"c{i}" for i in range(6)]


def _m(pos):
    return {c: (0.1 if c in pos else -0.1) for c in CELLS}


def test_informative_cells():
    d = {"a": {"S": 1.2, "T": 1.0}, "b": {"S": 1.05, "T": 1.0}, "c": {"S": None, "T": 1.0}}
    assert SS.informative_from(d) == ["a"]


def test_screen_advances_a_row_with_more_cells_no_flip_and_coherence():
    m = {"htdemucs": _m(CELLS[:4]), "mega53": _m(CELLS[:5]), "blend": _m(CELLS[:4])}
    s = SS.screen(m, {"htdemucs": 0.13, "mega53": 0.12, "blend": 0.20}, CELLS)
    assert s["rows"]["mega53"]["advances"]
    assert not s["rows"]["blend"]["advances"]            # coherence alone never advances
    assert not s["ceiling"]


def test_one_flip_blocks():
    m = {"htdemucs": _m(CELLS[:4]), "mega53": _m(["c0", "c1", "c2", "c4", "c5"]), "blend": _m([])}
    s = SS.screen(m, {"htdemucs": 0.13, "mega53": 0.13, "blend": 0.13}, CELLS)
    assert s["rows"]["mega53"]["more"] and s["rows"]["mega53"]["flips"] == ["c3"]
    assert not s["rows"]["mega53"]["advances"]


def test_coherence_blocks():
    m = {"htdemucs": _m(CELLS[:4]), "mega53": _m(CELLS[:5]), "blend": _m([])}
    s = SS.screen(m, {"htdemucs": 0.13, "mega53": 0.1099, "blend": 0.13}, CELLS)
    assert not s["rows"]["mega53"]["advances"] and not s["rows"]["mega53"]["coherence_ok"]


def test_refusal_counts_as_not_positive():
    m = {"htdemucs": _m(CELLS[:4]), "mega53": {**_m(CELLS[:5]), "c4": None}, "blend": _m([])}
    s = SS.screen(m, {"htdemucs": 0.13, "mega53": 0.13, "blend": 0.13}, CELLS)
    assert s["rows"]["mega53"]["positive"] == 4 and not s["rows"]["mega53"]["advances"]


def test_ceiling_and_undecided():
    m = {"htdemucs": _m(CELLS), "mega53": _m(CELLS), "blend": _m(CELLS)}
    s = SS.screen(m, {"htdemucs": 0.13, "mega53": 0.2, "blend": 0.2}, CELLS)
    assert s["ceiling"] and not any(r["advances"] for r in s["rows"].values())
    assert SS.screen(m, {}, CELLS[:3])["verdict"] == "undecided"
    assert SS.screen(m, {}, CELLS, hd_lag_fail=True)["verdict"] == "undecided"
    assert SS.reading(m["htdemucs"], CELLS, hd_lag_fail=True)["reading"] == "undecided"


@pytest.mark.parametrize("n,inv,want", [(6, 0, "not-separation"), (6, 1, "not-separation"), (6, 2, "co-equal"),
                                        (7, 2, "partial"), (7, 3, "co-equal"), (10, 3, "partial"),
                                        (10, 4, "co-equal"), (3, 0, "undecided")])
def test_reading_thresholds(n, inv, want):
    cs = [f"c{i}" for i in range(n)]
    m = {c: (-0.1 if i < inv else 0.1) for i, c in enumerate(cs)}
    assert SS.reading(m, cs)["reading"] == want


def test_leave_one_part_out_rescales():
    parts = sorted(SS.PARTS)
    cs = [f"{p}|{a}" for p in parts for a in SS.AMPS]
    hd = {c: 0.1 for c in cs}
    for c in (f"{parts[0]}|pr12", f"{parts[1]}|pr12", f"{parts[2]}|pr12"):
        hd[c] = -0.1                                      # 3 of 10 inverted: partial (ceil(10/3) = 4)
    m = {"htdemucs": hd, "mega53": dict(hd), "blend": dict(hd)}
    coh = {r: {p: 0.1 for p in parts} for r in SS.ROWS}
    assert SS.reading(hd, cs)["reading"] == "partial"
    out = SS.leave_one_part_out(m, coh, cs)
    r = out[parts[4]]["reading"]                          # n' = 8, 3 inversions >= ceil(8/3) = 3
    assert r["n"] == 8 and r["reading"] == "co-equal"
    r0 = out[parts[0]]["reading"]                         # n' = 8, 2 inversions: partial
    assert r0["n"] == 8 and r0["reading"] == "partial"
    assert out[parts[0]]["screen"]["n"] == 8
    frag = SS.fragility((SS.screen(m, {r: 0.1 for r in SS.ROWS}, cs), SS.reading(hd, cs)),
                        {k: (v["screen"], v["reading"]) for k, v in out.items()})
    assert parts[4] in frag and parts[0] not in frag


# --- leaks and the render cap -------------------------------------------------------------------

def test_leak_assertion_refuses_a_band_that_trained_the_network():
    k3 = {"Band K0": 0, "Band K2": 2}
    cache = {"Band K0", "Band K2", "Diesel13", "Guitar-TECHS P1"}
    assert SS.leaks("Diesel13", 1, k3, cache)            # a drawn band in the caches trains every fold
    assert SS.leaks("Band K2", 1, k3, cache)
    assert not SS.leaks("Band K2", 2, k3, cache)         # its own left-out fold
    assert not SS.leaks("Turbosauro", 2, k3, cache)      # in no cache
    assert SS.leaks(SS.P1, 3, k3, set())


def test_render_counter_stops_at_its_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(SS, "out_dir", lambda: tmp_path)
    (tmp_path / "fakes").mkdir()
    (tmp_path / "scores").mkdir()
    for i in range(10):
        (tmp_path / "fakes" / f"{i}.json").write_text(json.dumps({"renders": 2}))
    for i in range(9):
        (tmp_path / "scores" / f"{i}.json").write_text(json.dumps({"renders": 12}))
    assert SS.renders_on_disk() == 128
    assert SS.cap_ok(128, 12) and SS.cap_ok(158, 12) and not SS.cap_ok(159, 12)
    assert math.isclose(SS.CAP, 170)
