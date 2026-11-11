"""C3s (`docs/full-controls-plan.md`, "C3s in detail"; ledger `phase_c3s`): C3i's (b) follow-up, C3's recipe with the
core's share of the loss restored. The split loss, its hook into training, the core masks, the read wiring, the
reading and the launchers."""

import math
import pathlib

import pytest

np = pytest.importorskip("numpy")

from learn import full_controls_c3 as X  # noqa: E402
from learn import full_space as F  # noqa: E402
from learn import pipeline_fix as P  # noqa: E402

LOGS = pathlib.Path(__file__).resolve().parents[1] / "logs"


def _out_and_y(torch, n=4, seed=0):
    g = torch.Generator().manual_seed(seed)
    nc, ns = len(F.CONT), len(F.SW)
    K = 3
    logpi = torch.log_softmax(torch.randn(n, K, generator=g), -1)
    mu, ls = torch.randn(n, K, nc, generator=g), 0.3 * torch.randn(n, K, nc, generator=g)
    swl = torch.randn(n, ns, generator=g)
    catl = [torch.randn(n, 10, generator=g) for _ in F.CAT]
    ampl = torch.randn(n, 3, generator=g)
    c = torch.randn(n, nc, generator=g)
    cm = (torch.rand(n, nc, generator=g) > 0.3).float()
    s = (torch.rand(n, ns, generator=g) > 0.5).float()
    sm = (torch.rand(n, ns, generator=g) > 0.3).float()
    k = torch.zeros(n, len(F.CAT), dtype=torch.long)
    km = torch.ones(n, len(F.CAT))
    a = torch.tensor([-100] * n)
    return (logpi, mu, ls, swl, catl, ampl), (c, cm, s, sm, k, km, a)


def test_split_loss_is_loss_fn_when_every_dim_is_core():
    torch = pytest.importorskip("torch")
    out, y = _out_and_y(torch)
    ones_c, ones_s = torch.ones_like(y[1]), torch.ones_like(y[3])
    assert torch.allclose(F.loss_split(out, *y, ones_c, ones_s), F.loss_fn(out, *y))


def test_split_loss_is_c3is_core_plus_the_added_controls_own_term():
    torch = pytest.importorskip("torch")
    out, y = _out_and_y(torch, seed=1)
    c, cm, s, sm, k, km, a = y
    cc = torch.zeros_like(cm)
    cc[:, : cm.shape[1] // 2] = 1
    sc = torch.zeros_like(sm)
    sc[:, : sm.shape[1] // 2] = 1
    core = F.loss_fn(out, c, cm * cc, s, sm * sc, k, km, a)
    logpi, mu, ls, swl, _, _ = out
    nm = cm * (1 - cc)
    terms = []
    for i in range(cm.shape[0]):
        if nm[i].sum() == 0:
            continue
        lp = sum(nm[i, d] * (-0.5 * ((c[i, d] - mu[i, :, d]) / ls[i, :, d].exp()) ** 2 - ls[i, :, d] - 0.5 * math.log(2 * math.pi))
                 for d in range(cm.shape[1]))
        terms.append(float(-torch.logsumexp(logpi[i] + lp, 0) / nm[i].sum()))
    nsm = sm * (1 - sc)
    bce = float((torch.nn.functional.binary_cross_entropy_with_logits(swl, s, reduction="none") * nsm).sum() / nsm.sum())
    want = float(core) + sum(terms) / len(terms) + bce
    assert float(F.loss_split(out, *y, cc, sc)) == pytest.approx(want, rel=1e-5)


def test_batch_loss_uses_the_split_only_when_the_data_carries_core_masks():
    torch = pytest.importorskip("torch")
    out, y = _out_and_y(torch, seed=2)

    class D:
        pass

    d = D()
    assert torch.allclose(P.batch_loss(d, out, y, [0, 1, 2, 3], "cpu"), F.loss_fn(out, *y))
    cc = np.zeros((6, len(F.CONT)), np.float32)
    sc = np.ones((6, len(F.SW)), np.float32)
    d.core = (cc, sc)
    got = P.batch_loss(d, out, y, [5, 4, 3, 2], "cpu")
    assert torch.allclose(got, F.loss_split(out, *y, torch.tensor(cc[[5, 4, 3, 2]]), torch.tensor(sc[[5, 4, 3, 2]])))


def test_core_masks_are_ftms_mask_on_real_rows_and_every_dim_on_plugin_rows(monkeypatch):
    c = np.zeros(len(F.CONT), np.float32)
    c[:3] = 1
    s_ = np.zeros(len(F.SW), np.float32)
    s_[1] = 1
    monkeypatch.setattr(P, "searched_heads", lambda amp, S: (c, s_, None))
    ms = {"sw50r": {"clean": ("sel", {"S": 1})}}
    cc, sc = P.core_masks([{"i": 0}, {"i": 1, "real": "u", "amp": "sw50r", "cls": "clean"}], ms)
    assert cc[0].all() and sc[0].all() and (cc[1] == c).all() and (sc[1] == s_).all()


def test_c3s_tags_read_through_c3s_paths_with_their_own_runs_and_c3s_holds(monkeypatch):
    assert P.C3S_TAGS <= P.C3_READ and set(X.C3S_HOLD) == set(P.C3S_TAGS)
    assert all(P.model_base(t) == X.C3S_BASE for t in P.C3S_TAGS) and X.C3S_BASE not in (X.C3_BASE, X.C3I_BASE, X.C3B_BASE)
    assert all(P.read_phase(t) == "phase_c3s" for t in P.C3S_TAGS)
    assert P.report_phase({"C3s-cabS", "C3-cabS"}) == "phase_c3s" and P.report_phase({"C3s-core", "C3i"}) == "phase_c3s"
    monkeypatch.setattr(X, "hold_for", lambda tag: ("hold", tag))
    assert P.answer_hold("C3s-cabS") == ("hold", "C3-cabS") and P.answer_hold("C3s-core") == ("hold", "C3-core")
    assert X.c3s_pairs() == "C3s-cabS:C3-cabS,C3s-core:C3i,C3s-core:C3-core,C3s-cabS:S"


def test_c3s_is_adopted_for_later_steps_only_if_shown_better_and_worse_nowhere():
    row = lambda lo, hi: {"mean": (lo + hi) / 2, "lo90": lo, "hi90": hi, "clusters": 8}   # noqa: E731
    und = {"bks": row(-0.02, 0.01), "goat": row(-0.01, 0.02), "pooled": row(-0.01, 0.01)}
    better = {"bks": row(-0.05, -0.01), "goat": None, "pooled": None}
    split = {"bks": row(0.01, 0.05), "goat": row(-0.05, -0.01), "pooled": None}
    assert X.c3s_reading(better, und, und)["adopt"] is True
    assert X.c3s_reading(und, better, better)["adopt"] is False
    assert X.c3s_reading(split, und, und)["adopt"] is False and X.c3s_reading(split, und, und)["cabS"] == "split"


def test_c3s_launchers_wait_for_the_mps_and_the_render_slots():
    t, r = (LOGS / "launch-c3s-train.zsh").read_text(), (LOGS / "launch-c3s-read.zsh").read_text()
    assert t.count("--masked --c3s") == 2 and "--c3i" not in t and "--inner" in t and "mv ${PIDS} ${PIDS}." in t
    assert "kill -0 ${WAIT_PID}" in t and 'pgrep -f "python[0-9.]* -u -m learn.pipeline_fix train-ft"' in t
    assert "c3s-train.log" in r and "kill -0 ${p}" in r and "c3s-rows" in r and "--label c3s" in r
    assert "TAGS=C3s-cabS,C3s-core" in r and "for k in 0 1 2" in r and "train-ft" not in r


def test_only_one_of_the_c3_variants_trains():
    pytest.importorskip("torch")
    import argparse
    a = argparse.Namespace(c3=False, c3i=True, c3b=False, c3s=True, masked=True, real_fold=0, seed=20261042, inner=False)
    with pytest.raises(SystemExit, match="one of --c3, --c3i, --c3b, --c3s or --c3c"):
        P.cmd_train_ft(a)
