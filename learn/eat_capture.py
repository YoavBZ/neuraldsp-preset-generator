"""`M-pcs` and `EW-mix` on the second capture batch, one answer per unit on its search half, for the ML session's N12 (`docs/score-ear-plan.md`).
Built by the review session; the ML session runs it. This file opens no capture row, label or search record.

    $TORCH_PY -m learn.eat_capture control                              # BKS and GOAT only: stops on any difference from the stored answers
    $TORCH_PY -m learn.eat_build real --captures --capture-batch 2      # EfficientAT's input of each capture unit, variant 0, for `EW-mix`
    $TORCH_PY -m learn.eat_embed --net mn10_as --sets captures2 --stats f5 f11 f13 f15
    $TORCH_PY -m learn.eat_capture answers --tags M-pcs EW-mix --out FILE

The recipe is `bakeoff_render.cmd_predict`'s, unchanged: `fit_fold` on every BKS and GOAT record, k None, which `dfix_records` already takes as every
label, with residuals around `RcBG` built by `cmd_goat_centres`' rule on `dfix_records`' lists for k None. Those are cycled to their rows per epoch, as
each fold's are. Each answer starts from that centre, so every control outside `K.space` stays at S. `control` runs the same functions on the four folds.
-> {tag: {unit: {search: {select, settings}}}}
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from learn import bakeoff as B               # noqa: E402
from learn import bakeoff_render as BR       # noqa: E402

TAGS = {"M-pcs": ("mel", "ridge", "real"), "EW-mix": ("mix3:pub", "ridge", "real")}
KIND = "captures2"


def setup():
    """The study's harness, as `eat_render.cmd_predict` sets it. -> the labelled records."""
    from learn import eat_read as ER
    from learn import eat_render as ERN
    from learn import pipeline_fix as P

    ER.real_setup(argparse.Namespace(mid="pub", pcs=64, net="mn10_as"))
    BR.root = ERN.score_root
    brecs, by_unit, folds = P.real_labels(2)
    grecs, gunits, _ = P.goat_labels()
    return brecs, by_unit, folds, grecs, gunits


def records_of(k, data):
    """The labels a centre averages: fold k's, or with k None every label, each list cycled to its rows per epoch."""
    from learn import pipeline_fix as P

    if k is None:
        b, g, _, _ = P.dfix_records(*data, None)
        return b + g
    return P.centre_records(*data, k)["RcBG"]


def centres_of(k, data):
    """`cmd_goat_centres`' `RcBG` for k. -> {(k, amp, cls): settings as `LO.sdict` writes them}."""
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    _, by_unit, _, _, gunits = data
    ms = P.A_menu_S()
    recs = records_of(k, data)
    cls_of = lambda r: (by_unit[r["unit"]] if r["unit"] in by_unit else gunits[r["unit"]])["cls"]      # noqa: E731
    out = {}
    for amp in P.AMPS3:
        for cls in ("clean", "crunch"):
            S = ms[amp][cls][1]
            out[(k, amp, cls)] = LO.sdict(P.rc_setting(K.space(amp, S), S, [LO.tdict(r["label"]) for r in recs if r["amp"] == amp and cls_of(r) == cls]))
    return out


def encoded(centres):
    """`fit_fold`'s centres from the settings. -> {(k, amp, cls): head values}."""
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import trusted_data_t3 as T3

    enc = T3.encode_for(T3.FULL)
    return {q: enc(F.label_of(LO.tdict(st), q[1]))[0].astype(float) for q, st in centres.items()}


def fitted(tag, k, data, values):
    name, fit, _ = TAGS[tag]
    return BR.fit_fold(k, name, fit, data, values, None)


def read(tag, predict, path, k, amp, cls, centres, values):
    """`cmd_predict`'s answer on one file. -> {"A": ask, "B": ask}: a half's ask reads that half alone."""
    from learn import full_space as F
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    cell = (amp, cls)
    sel, S = P.A_menu_S()[amp][cls]
    space = {(d.module, d.key) for d in K.space(amp, S)}
    D = F.by_name()
    dims = [(D[n], j) for j, n in enumerate(F.CONT) if (D[n].module, D[n].key) in space]
    res = predict(B.feature(TAGS[tag][0], None, path, amp, cls), [cell, cell])
    base = LO.tdict(centres[(k, *cell)])
    return {h: {"select": sel, "settings": LO.sdict(BR.overwrite(base, dims, values[(k, *cell)], res[i]))} for i, h in enumerate("AB")}


def search_half(asks, search):
    """Only the half the unit's search read: a capture unit's held half is judged, so no answer from it leaves this file."""
    if search not in ("A", "B"):
        raise SystemExit(f"no search half: {search!r}")
    return {search: asks[search]}


def cmd_control(_a):
    """The centres and both tags on the four folds against every stored answer, as `eat_windows`' controls: any difference stops the run."""
    from learn import pipeline_fix as P

    data = setup()
    units = BR.read_units()
    stored = {w: BR.stored_answers(w, "RcBG") for w in BR.SETS}
    done = 0
    for k in range(P.REAL_FOLDS):
        centres = centres_of(k, data)
        values = encoded(centres)
        here = [(w, q, key) for w, q in units if q["fold"] == k for key in BR.keys_of(w, q)]
        for w, q, key in here:
            if centres[(k, key.rsplit("|", 1)[1], q["cls"])] != stored[w][key][BR.ANY]["settings"]:
                raise SystemExit(f"control: {key}: the centre differs from stored RcBG")
        for tag in TAGS:
            f = fitted(tag, k, data, values)
            want = {w: BR.stored_answers(w, tag) for w in BR.SETS}
            for w, q, key in here:
                got = read(tag, f, str(P.dfix_input_path(q["unit"], 0)), k, key.rsplit("|", 1)[1], q["cls"], centres, values)
                if got != want[w][key]:
                    raise SystemExit(f"control: {tag} {key} differs from its stored answer")
                done += 1
            print(f"fold {k} {tag}: {len(here)} keys equal", flush=True)
    print(f"CONTROL OK: {done} answers equal stored, centres equal stored RcBG", flush=True)


def capture_units():
    """The second batch's units the ML session trusts, through its own loader. Metadata only."""
    from learn import capture_labels as CL

    CL.BATCH = CL.BATCH2
    return sorted(CL.trusted_units()[0], key=lambda u: u["unit"])


def answers_on(tags, units, data):
    """`tags`' all-labels answers. units: [{unit, amp, cls, search}]. -> {tag: {unit: {search: ask}}}."""
    from learn import pipeline_fix as P

    centres = centres_of(None, data)
    values = encoded(centres)
    out = {}
    for tag in tags:
        f = fitted(tag, None, data, values)
        out[tag] = {u["unit"]: search_half(read(tag, f, str(P.dfix_input_path(u["unit"], 0)), None, u["amp"], u["cls"], centres, values), u["search"]) for u in units}
        print(tag, len(out[tag]), "units", flush=True)
    return out


def cmd_answers(a):
    from learn import eat_embed as EE
    from learn import pipeline_fix as P

    if a.smoke:                                         # the same path on five GOAT units, in-sample, to see the file's shape
        data = setup()
        units = [{**data[4][u], "search": "A"} for u in sorted(r["unit"] for r in data[3])[:5]]
    else:
        data = setup()
        units = capture_units()
        if "EW-mix" in a.tags and not (EE.embed_root() / "mn10_as" / KIND / "keys.json").exists():
            raise SystemExit("`EW-mix` needs the captures2 embedding: run `eat_build` and `eat_embed` as above")
        B.feature.paths.update({str(P.dfix_input_path(u["unit"], 0)): (KIND, (u["unit"], 0)) for u in units})
    got = answers_on(a.tags, units, data)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(got, indent=1))
    tmp.replace(out)
    print(f"ANSWERS DONE: {out}, {', '.join(f'{t} {len(v)}' for t, v in got.items())}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("control").set_defaults(fn=cmd_control)
    p = sub.add_parser("answers")
    p.add_argument("--tags", nargs="+", default=list(TAGS), choices=list(TAGS))
    p.add_argument("--out", required=True)
    p.add_argument("--smoke", action="store_true", help="five GOAT units, no capture unit opened")
    p.set_defaults(fn=cmd_answers)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
