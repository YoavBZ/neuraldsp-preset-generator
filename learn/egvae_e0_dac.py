"""E0's DAC half (`docs/egvae-lite-plan.md`, "E0's bar"): run with the DAC venv, which has no
access to the learn modules (Python 3.9, descript-audio-codec 1.0.0, MIT weights, 44 kHz).

    $DAC_PY learn/egvae_e0_dac.py roundtrip DIR    # DIR/*/true44.wav -> DIR/*/dac44.wav
    $DAC_PY learn/egvae_e0_dac.py roundtrip DIR 4  # E0b: only the first 4 codebooks
    $DAC_PY learn/egvae_e0_dac.py mel DIR          # DIR/*/{true,di}.npy -> DIR/mel.json

The round trip is the codec's own path: `compress` unchunked (one window over the whole crop),
loudness-normalised to −16 LUFS as DAC does by default, all 9 codebooks, then `decompress`
(which restores the input loudness). CPU only; no gradients.

The mel distance is DAC's own multi-scale L1 log-mel (`MelSpectrogramLoss` with the training
configuration of DAC's `conf/base.yml`), the metric EG-VAE reports.
"""

import json
import pathlib
import sys

import numpy as np
import soundfile as sf
import torch

SR44, SR48 = 44100, 48000


def roundtrip(root, n_quantizers=None):
    import dac
    from audiotools import AudioSignal

    torch.set_grad_enabled(False)
    model = dac.DAC.load(dac.utils.download(model_type="44khz")).eval().to("cpu")
    for d in sorted(p for p in root.iterdir() if (p / "true44.wav").exists()):
        out = d / "dac44.wav"
        if out.exists():
            continue
        x, sr = sf.read(str(d / "true44.wav"), dtype="float32")
        assert sr == SR44
        sig = AudioSignal(torch.from_numpy(x)[None, None], SR44)
        c = model.compress(sig, win_duration=None, normalize_db=-16, n_quantizers=n_quantizers)
        y = model.decompress(c).audio_data[0, 0].numpy()[: len(x)]
        sf.write(str(out), y, SR44, subtype="FLOAT")
        print(d.name, c.codes.shape, flush=True)


def mel(root):
    from audiotools import AudioSignal
    from dac.nn.loss import MelSpectrogramLoss

    loss = MelSpectrogramLoss(n_mels=[5, 10, 20, 40, 80, 160, 320],
                              window_lengths=[32, 64, 128, 256, 512, 1024, 2048],
                              mel_fmin=[0] * 7, mel_fmax=[None] * 7, pow=1.0,
                              clamp_eps=1e-5, mag_weight=0.0, log_weight=1.0)
    res = {}
    with torch.no_grad():
        for d in sorted(p for p in root.iterdir() if (p / "di.npy").exists()):
            a, b = np.load(d / "di.npy"), np.load(d / "true.npy")
            n = min(len(a), len(b))
            sa = AudioSignal(torch.from_numpy(a[:n].astype(np.float32))[None, None], SR48)
            sb = AudioSignal(torch.from_numpy(b[:n].astype(np.float32))[None, None], SR48)
            res[d.name] = float(loss(sa, sb))
            print(d.name, round(res[d.name], 4), flush=True)
    (root / "mel.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    extra = [int(a) for a in sys.argv[3:]]
    {"roundtrip": roundtrip, "mel": mel}[sys.argv[1]](pathlib.Path(sys.argv[2]).expanduser(), *extra)
