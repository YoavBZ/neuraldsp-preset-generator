"""The torch-dependent fake checks of `learn/trusted_data_t3_mix.py`, runnable without pytest in the torch venv
(pytest is not installed there, and the main venv has no torch):

    ~/ndsp-presets/tools/demucs-venv/bin/python -m tests.torch_checks_t3_mix

`tests/test_trusted_data_t3_mix.py` calls the same functions where torch is importable. Fakes only: temporary feature
files, no data, no training."""

import argparse
import pathlib
import tempfile

import numpy as np


def _fake_files(tmp, n=4):
    from learn import full_space as F

    rng = np.random.default_rng(1)
    rows, files = [], {}
    for i in range(n):
        mp, sp = tmp / f"{i}-mix.npz", tmp / f"{i}-stem.npz"
        np.savez(mp, mA=rng.integers(40, 200, (96, 446)).astype(np.uint8),
                 mB=rng.integers(40, 200, (96, 446)).astype(np.uint8), lufs=[-11.0, -12.0], gain_db=0.0)
        np.savez(sp, sA=rng.integers(40, 200, (96, 446)).astype(np.uint8),
                 sB=rng.integers(40, 200, (96, 446)).astype(np.uint8), lufs=[-15.0, -16.0])
        files[i] = (str(mp), str(sp))
        rows.append({"i": i, "amp": F.AMPS[i % 3], "base": "clean", "section": f"s{i % 2}", "split": "train",
                     "early_stop": False, "label": None, "lufs_A": -20.0, "lufs_B": -20.0})
    return rows, files


def check_arm_data_inputs_unaugmented(tmp):
    """D_F5mix reads the mix (stem channel and stem loudness zero); D_F5-noaug reads the stem (mix zero); neither is
    augmented, in any epoch."""
    import torch

    from learn import trusted_data_t3_mix as M

    rows, files = _fake_files(pathlib.Path(tmp))
    enc = lambda lab: (np.zeros(3, np.float32), np.ones(3, np.float32))   # noqa: E731
    for arm, kept, zeroed in ((M.MIX_ARM, 1, 0), (M.NOAUG_ARM, 0, 1)):
        data = M.arm_data(arm, rows, files, enc)
        assert data.arm == M.INPUT_OF[arm] and data.aug is False and data.G is None and data.cands == {}
        for epoch in (0, 1, 2, 5):
            x, c, _ = data.batch([0, 1, 2, 3], epoch, torch.device("cpu"))
            assert torch.all(x[:, zeroed] == 0) and torch.any(x[:, kept] != 0)
            assert torch.all(c[:, -2 + zeroed] == 0) and torch.all(c[:, -2 + kept] != 0)
        assert data.applied == {}
    return x, c


def check_net_reads_the_input(tmp):
    """The full-space network takes the mix input unchanged (the same shapes as D_F5's)."""
    from learn import full_space as F

    x, c = check_arm_data_inputs_unaugmented(tmp)
    out = F.build_net()(x, c)
    assert out[0].shape[0] == 4 and out[3].shape == (4, len(F.SW)) and out[5].shape == (4, len(F.AMPS))


def check_train_refuses_another_arm_or_seed():
    from learn import trusted_data_t3_mix as M

    orig = M.require_mix
    M.require_mix = lambda a: None
    try:
        for arm, seed in (("D_F5", 20261042), (M.MIX_ARM, 1)):
            try:
                M.cmd_train(argparse.Namespace(arm=arm, seed=seed, smoke=False, out=None))
            except SystemExit as e:
                assert "--arm in" in str(e)
            else:
                raise AssertionError("train ran with a wrong arm or seed")
    finally:
        M.require_mix = orig


def main():
    with tempfile.TemporaryDirectory() as tmp:
        check_arm_data_inputs_unaugmented(tmp)
        check_net_reads_the_input(tmp)
    check_train_refuses_another_arm_or_seed()
    print("TORCH CHECKS OK (3)")


if __name__ == "__main__":
    main()
