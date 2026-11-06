"""EfficientAT's MobileNets (Schmid et al., github.com/fschmid56/EfficientAT, MIT, commit a425fdce) without torchvision or
torchaudio: the network as its `models/mn` builds it, so that its state dicts load strictly, and its evaluation front end.
Weights stay outside the repo and are checked against the hashes below; they load with `weights_only=True`.

    python -m learn.eat_net tags FILE.wav [--name mn10_as]     # the top AudioSet tags of a file
"""
import argparse
import csv
import functools
import hashlib
import math
import pathlib

HOME = pathlib.Path("~/ndsp-presets/tools/efficientat").expanduser()
WEIGHTS = HOME / "weights"
CLASSES = HOME / "repo" / "metadata" / "class_labels_indices.csv"
SR = 32000
N_FFT, WIN, HOP = 1024, 800, 320
FMAX = 15000.0                                         # `AugmentMelSTFT`'s default: sr / 2 less half the augmentation range
EPS = 0.00001
NAMES = {                                              # name: (file, width, mel bands, sha256)
    "mn04_as": ("mn04_as_mAP_432.pt", 0.4, 128, "899a8c6217063f69"),
    "mn10_as": ("mn10_as_mAP_471.pt", 1.0, 128, "0bd7dc2443af498c"),
    "mn20_as": ("mn20_as_mAP_478.pt", 2.0, 128, "1561abc3a70373eb"),
    "mn10_m64": ("mn10_as_mels_64_mAP_461.pt", 1.0, 64, "50d004a4d0bb2dc7"),
    "mn10_im": ("mn10_im.pt", 1.0, 128, "c55942154e5926e7"),
}
BLOCKS = (                                             # (input, kernel, expanded, output, squeeze-excite, hard swish, stride)
    (16, 3, 16, 16, False, False, 1),
    (16, 3, 64, 24, False, False, 2),
    (24, 3, 72, 24, False, False, 1),
    (24, 5, 72, 40, True, False, 2),
    (40, 5, 120, 40, True, False, 1),
    (40, 5, 120, 40, True, False, 1),
    (40, 3, 240, 80, False, True, 2),
    (80, 3, 200, 80, False, True, 1),
    (80, 3, 184, 80, False, True, 1),
    (80, 3, 184, 80, False, True, 1),
    (80, 3, 480, 112, True, True, 1),
    (112, 3, 672, 112, True, True, 1),
    (112, 5, 672, 160, True, True, 2),
    (160, 5, 960, 160, True, True, 1),
    (160, 5, 960, 160, True, True, 1),
)


def divisible(v, divisor=8):
    new = max(divisor, int(v + divisor / 2) // divisor * divisor)
    return new + divisor if new < 0.9 * v else new


def conv_norm(nn, a, b, kernel, stride=1, groups=1, act=None):
    """torchvision's `ConvNormActivation` with this network's batch norm."""
    parts = [nn.Conv2d(a, b, kernel, stride, (kernel - 1) // 2, groups=groups, bias=False),
             nn.BatchNorm2d(b, eps=0.001, momentum=0.01)]
    if act is not None:
        parts.append(act(inplace=True))
    return nn.Sequential(*parts)


def network(width=1.0, classes=527):
    """The MobileNet of `models/mn/model.py` with its `mlp` head and channel squeeze-excitation. A model's output is
    (logits, the 960-wide pooled last layer at width 1)."""
    import torch
    import torch.nn.functional as F
    from torch import nn

    class Squeeze(nn.Module):
        def __init__(self, c):
            super().__init__()
            hidden = divisible(c // 4)
            self.fc1 = nn.Linear(c, hidden)
            self.fc2 = nn.Linear(hidden, c)

        def forward(self, x):
            s = x.mean((2, 3))
            return x * torch.sigmoid(self.fc2(torch.relu(self.fc1(s))))[:, :, None, None]

    class Excite(nn.Module):
        def __init__(self, c):
            super().__init__()
            self.conc_se_layers = nn.ModuleList([Squeeze(c)])

        def forward(self, x):
            return self.conc_se_layers[0](x)

    class Inverted(nn.Module):
        def __init__(self, a, kernel, mid, b, excite, hard, stride):
            super().__init__()
            act = nn.Hardswish if hard else nn.ReLU
            parts = [] if mid == a else [conv_norm(nn, a, mid, 1, act=act)]
            parts.append(conv_norm(nn, mid, mid, kernel, stride, groups=mid, act=act))
            if excite:
                parts.append(Excite(mid))
            parts.append(conv_norm(nn, mid, b, 1))
            self.block = nn.Sequential(*parts)
            self.residual = stride == 1 and a == b

        def forward(self, x):
            return self.block(x) + x if self.residual else self.block(x)

    class MN(nn.Module):
        def __init__(self):
            super().__init__()
            w = lambda c: divisible(c * width)                      # noqa: E731
            cfg = [(w(a), k, w(m), w(b), e, h, s) for a, k, m, b, e, h, s in BLOCKS]
            last = 6 * cfg[-1][3]
            self.features = nn.Sequential(conv_norm(nn, 1, cfg[0][0], 3, 2, act=nn.Hardswish),
                                          *(Inverted(*c) for c in cfg),
                                          conv_norm(nn, cfg[-1][3], last, 1, act=nn.Hardswish))
            hidden = divisible(1280 * width)
            self.classifier = nn.Sequential(nn.AdaptiveAvgPool2d(1), nn.Flatten(1), nn.Linear(last, hidden),
                                            nn.Hardswish(inplace=True), nn.Dropout(0.2, inplace=True),
                                            nn.Linear(hidden, classes))

        def forward(self, x):
            x = self.features(x)
            return self.classifier(x), F.adaptive_avg_pool2d(x, 1).flatten(1)

    return MN()


def load(name):
    """A pretrained network in eval mode, checked against its pinned hash."""
    import torch

    file, width, _, sha = NAMES[name]
    path = WEIGHTS / file
    if not hashlib.sha256(path.read_bytes()).hexdigest().startswith(sha):
        raise SystemExit(f"{path}: not the pinned weights")
    state = torch.load(path, map_location="cpu", weights_only=True)
    net = network(width, state["classifier.5.bias"].numel())
    net.load_state_dict(state, strict=True)
    return net.eval()


def scale(f):
    return 1127.0 * math.log(1.0 + f / 700.0)


@functools.lru_cache(maxsize=4)
def mel_banks(bands, fmin=0.0, fmax=FMAX):
    """torchaudio's `compliance.kaldi.get_mel_banks` at this front end's settings, with its zero Nyquist column.
    -> [bands, N_FFT / 2 + 1] float32 array."""
    import numpy as np

    lo, hi = scale(fmin), scale(fmax)
    delta = (hi - lo) / (bands + 1)
    b = np.arange(bands)[:, None]
    left, centre, right = lo + b * delta, lo + (b + 1.0) * delta, lo + (b + 2.0) * delta
    mel = 1127.0 * np.log1p(SR / N_FFT * np.arange(N_FFT // 2) / 700.0)[None, :]
    bank = np.maximum(0.0, np.minimum((mel - left) / (centre - left), (right - mel) / (right - centre)))
    return np.pad(bank, ((0, 0), (0, 1))).astype(np.float32)


def band_centres(bands, fmin=0.0, fmax=FMAX):
    """The bands' centres in Hz."""
    import numpy as np

    lo, hi = scale(fmin), scale(fmax)
    m = lo + (np.arange(bands) + 1.0) * (hi - lo) / (bands + 1)
    return 700.0 * (np.exp(m / 1127.0) - 1.0)


def front(wave, bands=128):
    """`AugmentMelSTFT` in evaluation: waveform [N, samples] at SR -> [N, bands, frames], its normalised log-mels."""
    import torch

    x = torch.as_tensor(wave, dtype=torch.float32)
    x = torch.nn.functional.conv1d(x[:, None], torch.tensor([[[-0.97, 1.0]]])).squeeze(1)
    window = torch.hann_window(WIN, periodic=False)
    z = torch.stft(x, N_FFT, hop_length=HOP, win_length=WIN, center=True, window=window, return_complex=True)
    p = z.real ** 2 + z.imag ** 2
    return (((torch.tensor(mel_banks(bands)) @ p) + EPS).log() + 4.5) / 5.0


def maps(net, x):
    """Every layer's map of a [N, 1, bands, frames] batch: {layer index: tensor}, and the logits."""
    import torch

    got, hooks = {}, []
    for i, layer in enumerate(net.features):
        hooks.append(layer.register_forward_hook(lambda _m, _i, o, i=i: got.__setitem__(i, o.detach())))
    try:
        with torch.no_grad():
            logits, _ = net(x)
    finally:
        for h in hooks:
            h.remove()
    return got, logits


def class_names():
    with open(CLASSES, newline="") as f:
        return [r["display_name"] for r in csv.DictReader(f)]


def read_wave(path):
    """A file as mono at SR."""
    from math import gcd

    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    y, sr = sf.read(str(path), always_2d=True, dtype="float32")
    y = y.mean(1)
    g = gcd(sr, SR)
    return y if sr == SR else resample_poly(y, SR // g, sr // g).astype(np.float32)


def cmd_tags(args):
    import torch

    x = front(read_wave(args.file)[None], NAMES[args.name][2])
    logits, _ = load(args.name)(x[:, None])
    p = torch.sigmoid(logits)[0]
    names = class_names()
    for i in p.argsort(descending=True)[:args.top].tolist():
        print(f"{p[i]:.3f}  {names[i]}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tags")
    t.add_argument("file")
    t.add_argument("--name", default="mn10_as", choices=NAMES)
    t.add_argument("--top", type=int, default=10)
    t.set_defaults(fn=cmd_tags)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
