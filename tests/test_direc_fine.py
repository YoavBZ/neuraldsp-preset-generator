"""Experiment 4's extensions to `learn/direc.py` (`docs/di-fine-structure-plan.md`).

The bit-identity tests (review R9) compare tiny CPU runs of `fit` with hashes recorded from
`learn/direc.py` as of commit a707033, before any experiment-4 change. C′'s defaults must stay
bit-identical: the Mega-53 screen imports `rebuild` from this module.

Torch tests run on the CPU. The MPS gradient check runs only with RUN_MPS_TESTS=1 (MPS is
shared with training)."""

import json
import os

import pytest

torch = pytest.importorskip("torch")
np = pytest.importorskip("numpy")

from learn import direc as D  # noqa: E402
from tests import direc_tiny as T  # noqa: E402

# Recorded at a707033 (before experiment 4), torch 2.14, CPU, one thread.
GOLDEN = {
    "a": ("faf688f2cc42485ad11db1176547952f39820aea5ac3954dfd0a550fece413ca", ["11.535 23.248 7.498 0 1.00"]),
    "b": ("26cf7da9b2ef7c9a4a1bfaed840978bdce672ec5f0f4af0568d1693ea6d7f9df", ["10.827 21.860 7.498 0 1.00"]),
    "c": ("34adfec53fb72c3691c396c296cddbebea2494cfb097b36c0a42466d4f068854", ["11.453 22.626 7.498 0 1.00"]),
    "d": ("4e46b024b1717a279d52ecb5203193877f5e8106d67322f9e81ad7da1c31c790",
          ["11.806 23.339 7.498 0 1.00", "11.414 22.464 7.498 0 1.00", "11.042 22.188 7.498 0 1.00"]),
}
REBUILD_SHA = "4ddba6a13b91dd729a23b7debfd06cfcd54f653ac1088054b7939dcd842db4ba"
MODEL_PARAMS = 9783105
MODEL_SHAPES_SHA = "dddebff0dc82cf2fa339dacc1d213bd1d2e3803088b0a845cb1e16bcff7b96fd"
LOSS_DEFAULT, LOSS_PHASE = 12.706986427307129, 53.5826416015625


@pytest.fixture(scope="module")
def tiny(tmp_path_factory):
    """The four recorded runs, once per module (each is a couple of seconds)."""
    mp = pytest.MonkeyPatch()
    d = tmp_path_factory.mktemp("direc")
    out = {"a": T.tiny_fit(d, mp, out_name="a"),
           "b": T.tiny_fit(d, mp, out_name="b", resume=d / "a" / "fold0.pt"),
           "c": T.tiny_fit(d, mp, out_name="c", lr_end=None),
           "d": T.tiny_fit(d, mp, out_name="d", steps=6, log_every=2)}
    mp.undo()
    return d, out


# --- bit-identity (R9) -----------------------------------------------------------------------

@pytest.mark.parametrize("run", ["a", "b", "c", "d"])
def test_default_fit_is_bit_identical_to_cprime(tiny, run):
    _, out = tiny
    assert out[run] == GOLDEN[run]


def test_explicit_defaults_and_fine_logging_change_nothing(tiny, monkeypatch):
    """`terms=None`, `warmup=0` and the per-validation fine metrics (which must not consume the
    random stream or change the batches) leave the weights and validation figures identical."""
    d, _ = tiny
    got = T.tiny_fit(d, monkeypatch, out_name="e", terms=None, warmup=0, adv=None, fullrate_head=False,
                     overfit=0, log_fine=True)
    assert got == GOLDEN["a"]
    got = T.tiny_fit(d, monkeypatch, out_name="f", resume=d / "a" / "fold0.pt", log_fine=True)
    assert got == GOLDEN["b"]


def test_default_fit_writes_no_new_files(tiny):
    d, _ = tiny
    assert sorted(p.name for p in (d / "a").iterdir()) == ["fold0.pt"]


def test_rebuild_model_and_loss_unchanged(tiny):
    d, _ = tiny
    torch.set_num_threads(1)
    net = D.load_model(d / "a" / "fold0.pt").eval()
    x = np.sin(np.arange(48000 * 7) * 0.01).astype(np.float32) * np.linspace(0, 1, 48000 * 7, dtype=np.float32)
    y = D.rebuild(net, x, device=torch.device("cpu"))
    import hashlib

    assert hashlib.sha256(y.astype(np.float32).tobytes()).hexdigest() == REBUILD_SHA
    torch.manual_seed(0)
    net = D.build_model()
    assert sum(p.numel() for p in net.parameters()) == MODEL_PARAMS
    shapes = ",".join(f"{k}:{tuple(v.shape)}" for k, v in net.state_dict().items())
    assert hashlib.sha256(shapes.encode()).hexdigest() == MODEL_SHAPES_SHA
    torch.manual_seed(0)
    a, b = torch.randn(2, 1, 8192) * 0.1, torch.randn(2, 1, 8192) * 0.1
    assert float(D.training_loss(a, b)) == LOSS_DEFAULT
    assert float(D.training_loss(a, b, "phase")) == LOSS_PHASE
    assert float(D.training_loss(a, b, "default", None)) == LOSS_DEFAULT


def test_warmup_ramps_then_cosine(tiny, monkeypatch):
    d, _ = tiny
    seen = []
    real = torch.optim.AdamW.step

    def step(self, *a, **k):
        seen.append(self.param_groups[0]["lr"])
        return real(self, *a, **k)

    monkeypatch.setattr(torch.optim.AdamW, "step", step)
    T.tiny_fit(d, monkeypatch, out_name="w", steps=6, warmup=2, lr=1e-4, lr_end=2e-5, log_every=6)
    assert seen[:2] == pytest.approx([5e-5, 1e-4])
    assert seen[2] == pytest.approx(1e-4)
    assert seen[2] > seen[3] > seen[4] > seen[5] > 2e-5


# --- the new terms ---------------------------------------------------------------------------

def _pair(seed=0, n=8192):
    g = torch.Generator().manual_seed(seed)
    t = torch.arange(n) / 48000
    y = (torch.sin(2 * torch.pi * 110 * t) * torch.exp(-((t * 8) % 1) * 6))[None, None].repeat(2, 1, 1)
    y = y + 0.01 * torch.randn(2, 1, n, generator=g)
    y[..., 3000:4000] *= 1e-3                                 # a gap
    p = y + 0.02 * torch.randn(2, 1, n, generator=g)
    return p, y


@pytest.mark.parametrize("name", D.FINE_TERMS)
def test_each_term_is_zero_at_target_and_has_finite_gradient(name):
    p, y = _pair()
    assert float(D.fine_terms(y, y, [name])[name]) == pytest.approx(0, abs=1e-5)
    q = p.clone().requires_grad_(True)
    D.fine_terms(q, y, [name])[name].backward()
    assert torch.isfinite(q.grad).all() and q.grad.abs().sum() > 0


def test_phase_term_finite_on_silent_prediction():
    _, y = _pair()
    q = torch.zeros_like(y, requires_grad=True)
    v = D.phase_deriv_loss(q.squeeze(1), y.squeeze(1))
    v.backward()
    assert torch.isfinite(v) and torch.isfinite(q.grad).all()


def test_peakiness_sees_a_smeared_transient():
    _, y = _pair()
    k = torch.ones(1, 1, 97) / 97
    smeared = torch.nn.functional.conv1d(y, k, padding=48)
    smeared = smeared / smeared.std() * y.std()
    assert float(D.peakiness_loss(smeared, y)) > float(D.peakiness_loss(y + 1e-4 * torch.randn_like(y), y)) + 1.0


def test_gap_guard_prices_only_a_louder_gap():
    _, y = _pair()
    quieter = y.clone()
    quieter[..., 3000:4000] *= 0.1
    louder = y.clone()
    louder[..., 3000:4000] += 0.05 * torch.randn(2, 1, 1000)
    assert float(D.gap_guard(quieter, y)) == 0.0
    assert float(D.gap_guard(louder, y)) > 10.0


def test_training_loss_adds_weighted_terms():
    p, y = _pair()
    base = D.training_loss(p, y)
    vals = D.fine_terms(p, y, ["short", "peak"])
    got = D.training_loss(p, y, terms={"short": 1.0, "peak": 0.1})
    assert float(got) == pytest.approx(float(base + vals["short"] + 0.1 * vals["peak"]), rel=1e-6)


def test_parse_terms():
    assert D.parse_terms("short=1,peak=0.1,gap=0.02,phase=1") == {"short": 1.0, "peak": 0.1, "gap": 0.02, "phase": 1.0}
    assert D.parse_terms(None) is None and D.parse_terms("") is None
    with pytest.raises(ValueError):
        D.parse_terms("crest=1")


def test_fine_metrics_reads_crest_gap_snr_and_band():
    p, y = _pair()
    m = D.fine_metrics(y[:, 0].numpy(), y[:, 0].numpy())
    assert m["crest_1ms_err"] == pytest.approx(0, abs=1e-9) and m["hf_3_8k_db"] == pytest.approx(0, abs=1e-9)
    assert m["gap_db"] == pytest.approx(0, abs=1e-6) and m["gap_frames"] > 0
    loud = y[:, 0].numpy().copy()
    loud[:, 3000:4000] += 0.05
    assert D.fine_metrics(loud, y[:, 0].numpy())["gap_db"] > 10
    assert D.fine_metrics(p[:, 0].numpy(), y[:, 0].numpy())["snr_db"] < 100


# --- the full-rate head (arm 1e) ---------------------------------------------------------------

def test_fullrate_head_starts_identical_and_round_trips(tmp_path):
    torch.manual_seed(0)
    base = D.build_model()
    net = D.build_model(fullrate_head=True)
    net.base.load_state_dict(base.state_dict())
    x = torch.randn(1, 1, 8192) * 0.1
    with torch.no_grad():
        assert torch.equal(net(x), base(x))
    torch.save(net.state_dict(), tmp_path / "h.pt")
    back = D.load_model(tmp_path / "h.pt")
    assert hasattr(back, "head")
    with torch.no_grad():
        assert torch.equal(back(x), net(x))
    assert 0.0 <= D.gate_open(back, x) <= 1.0


def test_fit_with_head_resumes_from_a_cprime_checkpoint(tiny, monkeypatch):
    d, _ = tiny
    T.tiny_fit(d, monkeypatch, out_name="h", resume=d / "a" / "fold0.pt", fullrate_head=True, mark_done=True)
    state = torch.load(d / "h" / "fold0.pt")
    assert "head.6.weight" in state and (d / "h" / "DONE").exists()
    cfg = json.loads((d / "h" / "config.json").read_text())
    assert cfg["fullrate_head"] is True and cfg["fold"] == 0


# --- arm 1c ----------------------------------------------------------------------------------------

def test_discriminators_and_losses():
    torch.manual_seed(0)
    discs = D.build_discriminators()
    x = torch.randn(2, 1, 4096) * 0.1
    outs = discs(x)
    assert len(outs) == 8
    assert torch.isfinite(D.disc_loss(outs, discs(x * 0.5)))
    assert float(D.feature_loss(outs, outs).detach()) == 0.0


def test_balancer_scales_each_term_by_its_share():
    b = D.Balancer({"recon": 0.7, "fm": 0.2, "adv": 0.1}, decay=0.0)
    g = {"recon": torch.ones(4) * 2, "fm": torch.ones(4) * 50, "adv": torch.ones(4) * 0.01}
    out = b.combine(g)
    ref = 2 * 2.0                                            # the recon gradient's norm
    exp = sum(s * ref * g[k] / g[k].norm() for k, s in b.shares.items())
    assert torch.allclose(out, exp)


def test_adv_fit_runs_with_micro_batches(tiny, monkeypatch):
    d, _ = tiny
    adv = {**D.ADV_DEFAULT, "warm": 1, "micro": 2}
    T.tiny_fit(d, monkeypatch, out_name="g", steps=3, adv=adv, terms={"short": 1.0, "peak": 0.1})
    state = torch.load(d / "g" / "fold0.pt")
    assert all(torch.isfinite(v).all() for v in state.values())


# --- the zero-render modes (0d, 0e, 1d) ----------------------------------------------------------

def test_calibrate_eval_and_overfit_modes(tiny, monkeypatch):
    d, _ = tiny
    ck = d / "a" / "fold0.pt"
    T.tiny_fit(d, monkeypatch, out_name="cal", resume=ck, calibrate=3)
    cal = json.loads((d / "cal" / "calibrate.json").read_text())
    assert set(cal["means"]) == {"L_C", "mrstft", *D.FINE_TERMS} and cal["batches"] == 3
    assert not (d / "cal" / "fold0.pt").exists()
    T.tiny_fit(d, monkeypatch, out_name="ev", resume=ck, eval_only=True)
    ev = json.loads((d / "ev" / "eval.json").read_text())
    assert ev["ratio"] == pytest.approx(ev["val"] / ev["input_as_di"]) and "crest_1ms_err" in ev["fine"]
    assert ev["val"] == pytest.approx(23.248, abs=2e-3)       # the run's own last validation
    T.tiny_fit(d, monkeypatch, out_name="ov", resume=ck, overfit=2, steps=2, lr_end=None,
               terms={"short": 1.0, "peak": 0.1, "gap": 0.02})
    ov = json.loads((d / "ov" / "overfit.json").read_text())
    assert len(ov["crops"]) == 2 and "snr_db" in ov["start"] and "snr_db" in ov["end"]


# --- MPS (only on request) -------------------------------------------------------------------------

@pytest.mark.skipif(not (os.environ.get("RUN_MPS_TESTS") and torch.backends.mps.is_available()),
                    reason="set RUN_MPS_TESTS=1 with MPS free")
@pytest.mark.parametrize("name", D.FINE_TERMS)
def test_term_gradient_matches_cpu_on_mps_at_crop_length(name):
    torch.manual_seed(0)
    x = torch.randn(2, 1, D.CROP) * 0.1
    y = torch.randn(2, 1, D.CROP) * 0.1

    def grad(dev):
        torch.manual_seed(0)
        net = D.build_model().to(dev)
        D.training_loss(net(x.to(dev)), y.to(dev), terms={name: 1.0}).backward()
        return torch.cat([q.grad.float().cpu().flatten() for q in net.parameters()])

    cpu, mps = grad("cpu"), grad("mps")
    cos = float((cpu * mps).sum() / (cpu.norm() * mps.norm()))
    assert cos >= 0.99
