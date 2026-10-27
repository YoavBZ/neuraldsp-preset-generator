"""The torch-dependent fake checks of `learn/xlance_finetune.py`, runnable without pytest in the msst venv (it has
torch and X-LANCE's dependencies; the main venv has no torch):

    ~/ndsp-presets/tools/msst-venv/bin/python -m tests.torch_checks_xlance_ft [--mps]

A tiny BS-RoFormer from X-LANCE's own code (no weights): the module's loss equals the model's own, the CPU-FFT routing
leaves the CPU step unchanged and restores the module, the trainable set round-trips, the clip works. `--mps` also
runs the gate's comparison on the tiny model (needs MPS to be free). Fakes only: no data, no training."""

import argparse
import sys

import torch


def tiny():
    from learn import direct_stems as DS

    code = str(DS.XL_ROOT / "code")
    sys.path.insert(0, code)
    try:
        from models.bs_roformer.bs_roformer import BSRoformer
    finally:
        DS.xl_unload(code)
    torch.manual_seed(0)
    return BSRoformer(dim=16, depth=12, stereo=True, num_stems=1, time_transformer_depth=1,
                      freq_transformer_depth=1, freqs_per_bands=(32, 32, 65), dim_head=8, heads=2,
                      stft_n_fft=256, stft_hop_length=64, stft_win_length=256, mask_estimator_depth=1,
                      multi_stft_resolutions_window_sizes=(256, 128), multi_stft_hop_size=64, flash_attn=False)


def batch(n=4096):
    g = torch.Generator().manual_seed(1)
    m = torch.randn(1, 1, n, generator=g).repeat(1, 2, 1) * 0.1
    t = torch.randn(1, 1, n, generator=g).repeat(1, 2, 1) * 0.05
    return m, t


def check_own_loss_is_the_models():
    from learn import xlance_finetune as X

    m = tiny().eval()
    mix, tgt = batch()
    a = m(mix, target=tgt)
    b = X.own_loss(m, m(mix), tgt)
    assert torch.allclose(a, b, rtol=1e-6, atol=1e-7), (float(a), float(b))


def check_fft_mode_is_a_passthrough_on_cpu_and_restores():
    from learn import xlance_finetune as X

    m = tiny().eval()
    mix, tgt = batch()
    g = type(m).forward.__globals__
    before = g["torch"]
    ref = m(mix, target=tgt)
    for mode in ("fft_cpu", "fft_loss_cpu"):
        out = X.step_loss(m, mode, mix, tgt)
        assert torch.allclose(out, ref, rtol=1e-6), (mode, float(out), float(ref))
        assert g["torch"] is before
    with X.fft_mode(m, True):
        assert isinstance(g["torch"], X._CpuFFT)
    assert g["torch"] is before


def check_trainable_round_trip_and_clip():
    from learn import xlance_finetune as X

    m = tiny()
    for n, p in m.named_parameters():
        p.requires_grad_(X.is_trainable(n))
    names = [n for n, p in m.named_parameters() if p.requires_grad]
    assert names and all(n.startswith(("layers.8.", "layers.9.", "layers.10.", "layers.11.", "final_norm.",
                                       "mask_estimators.")) for n in names)
    assert not any(p.requires_grad for n, p in m.named_parameters() if n.startswith(("layers.7.", "band_split.")))
    st = X.trainable_state(m)
    m2 = tiny()
    with torch.no_grad():
        for p in m2.parameters():
            p.add_(1.0)
    frozen = {k: v.clone() for k, v in m2.state_dict().items() if not X.is_trainable(k)}
    X.load_trainable(m2, st)
    for k, v in st.items():
        assert torch.equal(m2.state_dict()[k], v)
    assert frozen and all(torch.equal(m2.state_dict()[k], v) for k, v in frozen.items())   # the rest untouched
    try:
        X.load_trainable(m2, {k: v for k, v in list(st.items())[1:]})
        raise AssertionError("a partial checkpoint loaded")
    except SystemExit:
        pass
    params = [p for p in m.parameters() if p.requires_grad]
    for p in params:
        p.grad = torch.full_like(p, 10.0)
    norm = X.clip_grads(params, max_norm=1.0)
    after = sum(float(p.grad.pow(2).sum()) for p in params) ** 0.5
    assert norm > 1.0 and abs(after - 1.0) < 1e-3


def check_gate_on_mps():
    """The gate's comparison on the tiny model: every mode's loss and gradients against the CPU's (printed)."""
    import copy

    from learn import xlance_finetune as X

    ref = tiny().eval()
    for n, p in ref.named_parameters():
        p.requires_grad_(X.is_trainable(n))
    mix, tgt = batch(96_000)                            # above the 65,536-sample MPS STFT bug's threshold
    ref(mix, target=tgt).backward()
    rg = X.grads_by_group(ref)
    for mode in X.MODES[:-1]:
        m = copy.deepcopy(ref).to("mps")
        m.zero_grad(set_to_none=True)
        loss = X.step_loss(m, mode, mix.to("mps"), tgt.to("mps"))
        loss.backward()
        cos = {g: X.cosine(v, rg[g]) for g, v in X.grads_by_group(m).items()}
        print(mode, float(loss), float(ref(mix, target=tgt)), min(cos.values()))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mps", action="store_true")
    a = ap.parse_args(argv)
    for f in (check_own_loss_is_the_models, check_fft_mode_is_a_passthrough_on_cpu_and_restores,
              check_trainable_round_trip_and_clip):
        f()
        print("ok", f.__name__)
    if a.mps:
        check_gate_on_mps()
    print("TORCH CHECKS OK")


if __name__ == "__main__":
    main()
