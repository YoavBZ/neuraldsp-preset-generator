"""EfficientAT by the score (`docs/efficientat-plan.md`, task S5), on read 2's units, through `bakeoff_render` unchanged.

    $TORCH_PY -m learn.eat_render predict --tag E-mix --mid pub --pcs 64           # answers, CPU, zero renders
    $MAIN -m learn.eat_render check --shard 0/40                                  # FTm's stored renders come back the same
    $MAIN -m learn.eat_render render --tags E-mix --shard 0/3
    $MAIN -m learn.eat_render report OUT.json --tags E-mix [--vs M-ridge]         # zero renders

`bakeoff_render.root()` points at PF/eat/score, where this study's answers and judges go; the stored judges of S, RcBG, FTm and
`M-ridge` are linked in from PF/bakeoff, not copied. A candidate fits as `bakeoff_render.fit_fold` fits a ridge, on this
study's feature and PC count, with residuals around RcBG's own values.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from learn import bakeoff_render as BR  # noqa: E402

STORED = ("S", "RcBG", BR.FTM, "M-ridge")
TUNED = {"TE-mix": "mix:{mid}", "TE-mid": "{mid}"}
KEEP_ROOT = BR.root


def score_root():
    from learn import eat_embed as EE

    return EE.embed_root().parent / "score"


def linked():
    """The stored judges under this study's root, by link."""
    for which in BR.SETS:
        d = score_root() / "score-judge" / which
        d.mkdir(parents=True, exist_ok=True)
        for tag in STORED:
            if not (d / tag).exists():
                (d / tag).symlink_to(KEEP_ROOT() / "score-judge" / which / tag)


class Seeded:
    """`bakeoff.feature` for a tuned candidate: `bakeoff_render` averages seeds only for a feature named "W", so a tuned body reads
    under that name, each seed through its own bank."""

    def __init__(self, by_seed, rep):
        self.by_seed, self.rep = by_seed, rep

    @property
    def mix_cut(self):
        return {k: v for f in self.by_seed.values() for k, v in f.mix_cut.items()}

    def __call__(self, _name, seed, f, amp, cls):
        return self.by_seed[seed](self.rep, None, f, amp, cls)


def cmd_predict(a):
    from learn import bakeoff as B
    from learn import eat_read as ER

    if a.tag in TUNED:
        ER.declared([a.tag], a)
        ER.real_setup(a)
        paths = B.feature.paths
        B.feature = Seeded({s: ER.Features(ER.Bank(f"body-{s}"), paths) for s in ER.ET_SEEDS}, TUNED[a.tag].format(mid=a.mid))
        B.CANDIDATES = {**B.CANDIDATES, a.tag: ("W", "ridge", "real")}
        BR.root = score_root
        return BR.cmd_predict(a)
    cands = {**ER.candidates(a.mid), **ER.SAME_COUNT}
    if a.tag not in cands or cands[a.tag][2] != "real":
        raise SystemExit("predict takes a real-trained candidate of this study")
    ER.declared(ER.candidates(a.mid), a)
    ER.real_setup(a)
    B.CANDIDATES = {**B.CANDIDATES, a.tag: cands[a.tag]}
    BR.root = score_root
    BR.cmd_predict(a)


def cmd_render(a):
    BR.root = score_root
    BR.cmd_render(a)


def cmd_check(a):
    """FTm's stored answers rendered here must match its stored judges and render hashes; `cmd_render` stops on any difference."""
    BR.root = lambda: score_root().parent / "score-check"
    a.tags = BR.FTM
    BR.cmd_render(a)


def cmd_report(a):
    linked()
    BR.root = score_root
    if a.vs:
        BR.FTM = a.vs
    BR.cmd_report(a)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("predict")
    p.add_argument("--tag", required=True)
    p.add_argument("--mid", required=True)
    p.add_argument("--pcs", type=int, required=True)
    p.add_argument("--net", default="mn10_as")
    p.set_defaults(fn=cmd_predict)
    p = sub.add_parser("check")
    p.add_argument("--shard", type=BR.shard, default=(0, 40))
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser("render")
    p.add_argument("--tags", required=True)
    p.add_argument("--shard", type=BR.shard, default=(0, 1))
    p.set_defaults(fn=cmd_render)
    p = sub.add_parser("report")
    p.add_argument("out")
    p.add_argument("--tags", required=True)
    p.add_argument("--vs")
    p.set_defaults(fn=cmd_report)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
