"""EfficientAT as a judge term (`docs/efficientat-plan.md`, task S6), on the model comparison's stored pages. CPU, no renders.

    $TORCH_PY -m learn.eat_judge OUT.json

Terms `J-f6` and `J-f12`: on each half J0 reads, the render brought to the reference's LUFS, both through `eat_net.front` and
`mn10_as`, then the mean absolute difference of their `f` statistics, each dimension in units of its sd on the `wide` set, so no
ear data sets a scale. `bakeoff_judge`'s battery runs unchanged, with J0's `distance` beside as its control. The pages are in-sample,
one listener, 48 items, read many times: a pass is a screen and leads only to a proposal for a fresh blind page.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from learn import bakeoff_judge as J  # noqa: E402
from learn import eat_build as EB  # noqa: E402
from learn import eat_embed as EE  # noqa: E402
from learn import eat_net as E  # noqa: E402

TERMS = {"J-f6": "f6", "J-f12": "f12"}


def level_matched(ref, alt, lufs):
    """alt at ref's loudness."""
    return alt * 10 ** ((lufs(ref) - lufs(alt)) / 20)


def distance(a, b, sd):
    """Mean absolute difference, each dimension in its own sd."""
    return float(np.mean(np.abs(a - b) / np.maximum(sd, 1e-6)))


def stats(net, y):
    x = E.front(EB.to_32k(y)[None], 128)[:, None]
    maps_, logits = E.maps(net, x)
    return {s: v[0].numpy() for s, v in EE.stats_of(maps_, logits).items() if s in TERMS.values()}


def deep_terms(net, sds, ref, alt, halves):
    """{half: {term: value}} on the halves J0 reads."""
    from learn import song_aug as SA

    out = {}
    for h, (a, b) in halves.items():
        lo, hi = int(a * J.SR), int(b * J.SR)
        r, x = np.asarray(ref[lo:hi], np.float64), np.asarray(alt[lo:hi], np.float64)
        sr, sx = stats(net, r), stats(net, level_matched(r, x, SA.lufs))
        out[h] = {t: distance(sr[s], sx[s], sds[s]) for t, s in TERMS.items()}
    return out


def main(out):
    from learn import eat_read as ER
    from learn import knob_ceiling as K

    net = E.load("mn10_as")
    bank = ER.Bank("mn10_as")
    sds = {s: bank.sd(s) for s in TERMS.values()}
    base = J.judged

    def judged(ref, alt, di, latency):
        j0 = base(ref, alt, di, latency)
        deep = deep_terms(net, sds, ref, alt, K.R.HALVES)
        return {h: {**j0[h], **deep[h]} for h in j0}

    J.judged = judged
    J.TERMS = ("distance", *TERMS)
    J.main(out)


if __name__ == "__main__":
    main(sys.argv[1])
