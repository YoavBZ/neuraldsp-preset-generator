"""The DI network's training loss must give the same gradient on MPS as on the CPU.

torch.stft's gradient on MPS is wrong for signals longer than 65,536 samples (torch 2.8
and 2.14, measured 2026-10-11), and training crops are longer, so every DI network trained
on MPS before then learned from a wrong spectral gradient. `learn.direc.mrstft` now
computes on the CPU when given MPS tensors. The test uses the training crop length:
shorter signals don't show the bug."""

import pytest

torch = pytest.importorskip("torch")

pytestmark = pytest.mark.skipif(not torch.backends.mps.is_available(), reason="needs MPS")


def test_training_loss_gradient_matches_cpu_on_mps():
    from learn import direc as D

    torch.manual_seed(0)
    x = torch.randn(2, 1, D.CROP) * 0.1
    y = torch.randn(2, 1, D.CROP) * 0.1

    def grad(dev):
        torch.manual_seed(0)
        net = D.build_model().to(dev)
        D.training_loss(net(x.to(dev)), y.to(dev)).backward()
        return torch.cat([q.grad.float().cpu().flatten() for q in net.parameters()])

    cpu, mps = grad("cpu"), grad("mps")
    assert bool(torch.isfinite(mps).all())
    assert float((cpu - mps).norm() / cpu.norm()) < 1e-2
