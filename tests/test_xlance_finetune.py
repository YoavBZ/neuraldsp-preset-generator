"""ROADMAP step (b), D_F5ft (`learn/xlance_finetune.py`): the cross-fit's folds and jobs, the stop rule and schedule,
the gate's verdict, the rebuild (the build's mix and the wet target in it), the CLI, the ledger and the chain. Fakes
only: no data files, no renders, no training, no separation."""

import json
import pathlib
import random
import re

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
pytest.importorskip("pyloudnorm")

from learn import direct_stems as DS  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import song_aug as SA  # noqa: E402
from learn import trusted_data as T  # noqa: E402
from learn import local_objective_1c as C  # noqa: E402
from learn import xlance_finetune as X  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHAIN = ROOT / "docs" / "trusted-data-t3-xlance-chain.sh"
SECS = {"A": {f"a{k}" for k in range(7)}, "B": {f"b{k}" for k in range(4)}, "C": {"c0", "c1"}, "D": {"d0"}}


# --- folds and jobs ----------------------------------------------------------------------------------------------

def test_band_folds_balance_examples_and_keep_the_first_band_in_fold_0():
    counts = {"Death Of A Romantic": 1123, "Hollow Ground": 1065, "Storm Of Particles": 986, "Ale Lak": 293}
    f = X.band_folds(counts)
    assert f == {"Ale Lak": 0, "Death Of A Romantic": 0, "Hollow Ground": 1, "Storm Of Particles": 1}   # 1,416 / 2,051
    assert X.band_folds(dict(reversed(list(counts.items())))) == f                     # order-free, no seed
    assert sorted(X.band_folds({"a": 1, "b": 1, "c": 1, "d": 1, "e": 9}).values()) == [0, 0, 1, 1, 1]


def test_alternate_start_moves_the_odd_item():
    assert sorted(X.alternate(["x"], random.Random(0), start=1).values()) == [1]
    assert sorted(X.alternate(["x", "y", "z"], random.Random(0)).values()) == [0, 0, 1]


def test_val_sections_come_from_the_folds_bands_and_move_on_to_reach_three():
    secs = {"A": {"a0", "a1", "a2", "a3"}, "B": {"b0", "b1"}}
    v = X.val_sections(secs, 0)
    assert len(v) == X.VAL_SECTIONS and set(v) <= secs["A"] | secs["B"]
    assert len(set(v) & secs["B"]) <= 1                       # a band keeps a training section
    assert len(set(v) & secs["A"]) >= 2                       # moved on to the next band instead of stopping short
    assert v == X.val_sections(secs, 0)
    assert X.val_sections({"A": {"a0"}, "B": {"b0"}}, 1) == []  # nothing to spare: no validation section taken


def test_val_sections_take_from_the_largest_band_first():
    secs = {"Small": {"s0", "s1", "s2", "s3", "s4"}, "Big": {f"b{k}" for k in range(16)}}
    v = X.val_sections(secs, 0, {"Small": 293, "Big": 1123})
    assert len(set(v) & secs["Big"]) == 2 and len(set(v) & secs["Small"]) == 1


def test_a_stem_counts_as_the_other_workers_only_if_written_during_this_run(tmp_path):
    import os
    import time

    p = tmp_path / "x.npz"
    assert not X.fresh_from_other_worker(p, time.time())
    p.write_bytes(b"0")
    os.utime(p, (1_000, 1_000))                               # a killed run's leftover: made again
    assert not X.fresh_from_other_worker(p, time.time())
    started = time.time() - 5
    p.write_bytes(b"1")
    assert X.fresh_from_other_worker(p, started)


def test_snr_block_is_band_clustered_and_carries_the_wet_snr():
    S = {"band_of_ex": {1: "A", 2: "A", 3: "B", 4: "C"}}
    rows = {i: {"set": "fs5", "snr_audio_db": -2.0 + i, "snr_stock_db": -6.0, "snr_wet_db": -1.0} for i in S["band_of_ex"]}
    b = X.snr_block(rows, S)["fs5"]
    assert b["new_minus_stock_db"]["bands"] == 3 and b["new_minus_stock_db"]["point"] == pytest.approx((5.5 + 7 + 8) / 3)
    assert b["median_new_wet_db"] == -1.0 and "understates" in b["wet_note"]


def test_sep_jobs_are_out_of_band_and_cover_every_example_once():
    band = {1: "A", 2: "A", 3: "B", 4: "C", 5: "D", 6: "B"}       # 6: an FS5 example, separated like F5's
    bf = {"A": 0, "B": 0, "C": 1, "D": 1}
    j0, j1 = X.sep_jobs(0, list(band), band, bf), X.sep_jobs(1, list(band), band, bf)
    assert j0 == [4, 5] and j1 == [1, 2, 3, 6]
    assert sorted(j0 + j1) == sorted(band)


def test_vreal_folds_are_balanced_and_fixed():
    slugs = [f"p{k}" for k in range(11)]
    f = X.vreal_folds(slugs)
    assert f == X.vreal_folds(list(reversed(slugs))) and abs(sum(f.values()) - 5.5) <= 0.5


# --- the schedule and the stop rule ------------------------------------------------------------------------------------

def test_step_limits_follow_the_budget():
    assert X.step_limits(2.0) == (int(5.5 * 3600 / 2.0), 500)
    assert X.step_limits(30.0, budget_h=0.1) == (12, 6)                 # the minimum is half a small maximum


def test_lr_warms_up_then_decays_to_zero():
    lrs = [X.lr_at(s, 1000) for s in range(1000)]
    assert lrs[0] == pytest.approx(X.LR / X.WARMUP) and lrs[X.WARMUP - 1] == pytest.approx(X.LR)
    assert all(a <= b for a, b in zip(lrs[:X.WARMUP], lrs[1:X.WARMUP]))
    assert all(a >= b for a, b in zip(lrs[X.WARMUP:], lrs[X.WARMUP + 1:]))
    assert X.lr_at(1000, 1000) == pytest.approx(0.0)


def test_best_point_needs_the_minimum_gain():
    assert X.best_point([(0, -5.0), (250, -4.95), (500, -4.0)]) == (500, -4.0)
    assert X.best_point([(0, -5.0), (250, -4.95)]) == (0, -5.0)          # 0.05 dB is not a gain


def test_plateau_waits_for_patience_and_the_minimum():
    c = [(0, -5.0), (250, -3.0)] + [(250 * k, -3.0) for k in range(2, 6)]
    assert X.plateau(c, min_steps=500)                                  # 1,000 steps since 250
    assert not X.plateau(c[:-1], min_steps=500)
    assert not X.plateau(c, min_steps=2000)
    assert not X.plateau([(0, -5.0), (250, -5.0), (500, -5.0), (750, -5.0)], min_steps=500)


def test_band_mean_weights_bands_equally():
    assert X.band_mean({1: 0.0, 2: 0.0, 3: 6.0}, {1: "a", 2: "a", 3: "b"}) == 3.0
    assert X.band_mean({}, {}) is None


# --- the gate ------------------------------------------------------------------------------------------------------

def test_cosine_and_gate_ok():
    a = np.arange(1.0, 6.0)
    assert X.cosine(a, a) == pytest.approx(1.0) and X.cosine(a, -a) == pytest.approx(-1.0)
    assert X.cosine(np.zeros(3), np.zeros(3)) == 1.0 and np.isnan(X.cosine(np.zeros(3), a[:3]))
    assert X.gate_ok(1.00005, 1.0, {"trunk 8": 0.9995, "mask estimator": 1.0})
    assert not X.gate_ok(1.001, 1.0, {"trunk 8": 1.0})
    assert not X.gate_ok(1.0, 1.0, {"trunk 8": 0.001})                  # the measured MPS failure
    assert not X.gate_ok(1.0, 1.0, {"trunk 8": float("nan")}) and not X.gate_ok(float("nan"), 1.0, {})


def test_trainable_set_and_groups():
    assert X.is_trainable("layers.8.0.layers.0.0.to_qkv.weight") and X.is_trainable("mask_estimators.0.x")
    assert X.is_trainable("final_norm.gamma")
    assert not X.is_trainable("layers.7.0.x") and not X.is_trainable("band_split.x")
    assert not X.is_trainable("layers.80.x")
    assert not X.is_trainable("layers.9.0.layers.0.0.rotary_embed.freqs")   # shared with layer 0: frozen
    assert X.group_of("layers.11.1.x") == "trunk 11" and X.group_of("mask_estimators.0.y") == "mask estimator"
    assert X.MODES[-1] == "cpu" and X.MODES[0] == "mps"


# --- the rebuild -------------------------------------------------------------------------------------------------------

def test_compress_parts_is_song_aug_compress():
    x = np.random.default_rng(2).normal(0, 0.1, 48_000)
    y, g = X.compress_parts(x, random.Random(7))
    assert np.allclose(y, SA.compress(x, random.Random(7)), atol=1e-12)
    peak = 10 ** (-1 / 20)
    assert np.allclose(y, np.clip(x * g, -peak, peak), atol=0)


def _example(i):
    mastered, _ = DS.master_draw(i)
    return {"i": i, "draw": {"ratio_db": -3.0, "leak_db": -60.0, "target_lufs": -14.0, "mastered": mastered}}


@pytest.mark.parametrize("mastered", [False, True])
def test_rebuild_is_the_builds_mix_and_the_wet_target_sits_in_it(mastered):
    i = next(k for k in range(200) if DS.master_draw(k)[0] == mastered)
    r = np.random.default_rng(i)
    n = 48_000 * 2
    y, oth, st = r.normal(0, 0.05, n), r.normal(0, 0.03, n), r.normal(0, 0.03, n)
    x = _example(i)
    mix, tgt, gains, lb = X.rebuild(y, oth, st, x)
    m2, g2, lb2 = T.self_built_mix(y, oth, st, x)
    assert np.allclose(mix, m2, atol=1e-12) and gains == g2 and lb == lb2
    k = 10 ** (gains["ga"] / 20)
    if not mastered:
        assert np.allclose(tgt, y * k, atol=0)
    else:                                     # the wet target carries the compressor's gain, and the mix's split holds
        _, g = X.compress_parts((y + (oth + st) * 10 ** (gains["gb"] / 20)) * k, DS.master_draw(i)[1])
        assert np.allclose(tgt, y * k * g, atol=1e-12)
        assert not np.allclose(tgt, y * k)


def test_rebuild_refuses_a_changed_mastering_draw():
    x = _example(3)
    x["draw"]["mastered"] = not x["draw"]["mastered"]
    with pytest.raises(SystemExit, match="mastering draw changed"):
        n = 48_000
        X.rebuild(np.full(n, 0.01), np.full(n, 0.01), np.zeros(n), x)


# --- the CLI, the ledger, the design and the chain --------------------------------------------------------------------

@pytest.mark.parametrize("argv", [["train"], ["separate", "--device", "cpu"], ["prep", "--fold", "0"],
                                  ["train-d"], ["fit", "--seed", "20261042"], ["r0", "--shard", "0/3"]])
def test_cli_refuses_misplaced_or_missing_arguments(argv):
    with pytest.raises(SystemExit):
        X.main(argv)


def test_ledger_declares_amendment_4():
    d = json.loads((ROOT / "docs" / "dev-test-ledger.json").read_text())
    e = next(t for t in d["tests"] if t["test_id"] == "trusted-data-t3")
    assert X.LEDGER_MARK in e[X.LEDGER_KEY] and "BY BAND" in e[X.LEDGER_KEY] and "20261113" in e[X.LEDGER_KEY]
    assert X.ledger_declared()


def test_design_heading_matches_the_anchor():
    text = (ROOT / "docs" / "trusted-data-t0-design.md").read_text()
    heads = [ln.lstrip("#").strip() for ln in text.splitlines() if ln.startswith("#")]

    def slug(h):
        return re.sub(r"[^a-z0-9 _-]", "", h.lower()).replace(" ", "-")
    assert X.DESIGN.split("#", 1)[1] in {slug(h) for h in heads}


def test_chain_never_waits_bare_on_caffeinate():
    text = CHAIN.read_text()
    code = [ln.split("#", 1)[0] for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    caf = [ln for ln in code if "caffeinate" in ln]
    assert caf and all(ln.rstrip().endswith("&!") for ln in caf)     # disowned: no job for a wait to hang on
    waits = re.findall(r"^\s*(?:for p in \$pids; do )?(wait[^;\n]*)", text, re.M)
    assert waits and all(re.fullmatch(r"wait \$\w+", w.strip()) for w in waits)


def test_chain_order_and_guards():
    text = CHAIN.read_text()
    assert "setopt no_bg_nice" in text and X.LEDGER_MARK in text
    order = ["xlance_finetune check", "${XF[@]} prep", "${XF[@]} gate", "train --fold $k", "separate --fold $k",
             "vreal-stems", "train-d --seed", "${XF[@]} fit", "${XF[@]} r0", "${XF[@]} probe", "vreal-predict",
             "vreal-render --shard", "${XF[@]} report"]
    pos = [text.index(s) for s in order]
    assert pos == sorted(pos)
    assert "for k in 0 1" in text and "for seed in 20261042 20261043" in text
    assert "--shard $k/3" in text and "for k in 0 1 2" in text           # at most 3 render processes
    assert "--device mps --order asc" in text and "--device cpu --order desc" in text


def test_renders_and_separations_count_under_the_machine_rules():
    ren = "/x/.venv/bin/python -u -m learn.xlance_finetune vreal-render --shard 0/3"
    assert any(re.search(p, ren) for p in LO.RENDERS)
    for other in ("report", "r0", "train --fold 0", "vreal-predict", "separate --fold 0"):
        assert not any(re.search(p, f"/x/python -m learn.xlance_finetune {other}") for p in LO.RENDERS)
    for sep in ("prep", "separate --fold 1 --device cpu", "vreal-stems"):
        assert any(re.search(p, f"/x/python -u -m learn.xlance_finetune {sep}") for p in LO.SEPARATIONS)


def test_torch_checks():
    pytest.importorskip("torch")
    pytest.importorskip("einops")
    if not (DS.XL_ROOT / "code").exists():
        pytest.skip("X-LANCE's code is not installed here")
    from tests import torch_checks_xlance_ft as TC

    TC.main([])


def test_stop_reason_and_pinned_limits():
    c = [(0, -5.0)] + [(250 * k, -5.0) for k in range(1, 5)]
    assert X.stop_reason(c, 1000, 2000, 500, 0.0) == X.PLATEAU_WHY
    assert X.stop_reason(c[:2], 250, 250, 500, 0.0).startswith("the step maximum")
    assert X.stop_reason(c[:2], 250, 2000, 500, 10 * 3600.0) == "the wall guard"
    assert X.stop_reason(c[:2], 250, 2000, 500, 0.0) is None
    gate = {"mode": "fft_cpu", "max_steps": 9000, "min_steps": 500}
    assert X.pinned_limits({}, gate) == ("fft_cpu", 9000, 500)
    assert X.pinned_limits({"mode": "mps", "max_steps": 7000, "min_steps": 500}, gate) == ("mps", 7000, 500)
    assert X.pinned_limits({}, gate, smoke_steps=4) == ("fft_cpu", 4, 1)


def test_gate_train_and_train_d_count_as_mps_training():
    for cmd in ("gate", "train --fold 0", "train-d --seed 20261042"):
        assert C.is_training(f"/x/msst-venv/bin/python -u -m learn.xlance_finetune {cmd}")
    for cmd in ("prep", "separate --fold 0 --device mps", "report", "probe"):
        assert not C.is_training(f"/x/python -u -m learn.xlance_finetune {cmd}")


def test_mps_attention_switches_flash_off():
    import types

    from learn import xlance_finetune as X

    class Attend:
        def __init__(self):
            self.flash = True

    class Other:
        flash = True

    mods = [Attend(), Attend(), Other()]
    model = types.SimpleNamespace(modules=lambda: iter(mods))
    assert X.mps_attention(model) == 2
    assert [m.flash for m in mods] == [False, False, True]
    assert X.mps_attention(model) == 0
