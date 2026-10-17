"""Experiment 1d (`docs/local-objective-plan.md`, amendment 4): the separator-robust rebuild
(`docs/cprime-sep-plan.md`) in 1b's matched design. Each part's fold's separator-robust network
rebuilds (i) step 3's htdemucs stem and (ii) 1c's Mega-53 crop; Σ renders through each rebuild and
is scored against the rebuild's own source. Development only; estimates with 90% band-clustered
intervals, no pass/fail bars.

    $TORCH_PY -m learn.local_objective_1d rebuild --src stem      # CPU, zero renders; 4a identity + 2a checks
    $TORCH_PY -m learn.local_objective_1d rebuild --src mega53
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.local_objective render --di csep_stem,csep_mega53 --shard i/3
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.local_objective score --di csep_stem,csep_mega53 --workers 3
    .venv/bin/python -m learn.local_objective_1d report

TORCH_PY is ~/ndsp-presets/tools/demucs-venv/bin/python. Outputs go to
~/ndsp-presets/learn/local-objective/ (`rebuilt-csep-<src>/`, `report-1d.json`)."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import knob_ceiling as K  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import local_objective_1c as C  # noqa: E402

DI_STEM, DI_MEGA = LO.SEPNET_DI["stem"], LO.SEPNET_DI["mega53"]
MEGA_1C = LO.SEP_DI["mega53"]
EXPECTED = {"cells": 72, "renders": 3528}          # per 1d DI (amendment 4)
# Amendment 4a: the four networks, pinned before any render (fold{f}.pt == fold{f}-best.pt).
SEPNET_SHA256 = {0: "d5f76975753bd314ff04c981404e355aaf21e74de3b9f03eb19e6770cb5006a3",
                 1: "2b8a4fb51931af846271a57bafe0ae7ce9ced587adf216e6ae4c01fe24ba20d4",
                 2: "d4e8e43204b6c457bc730c85621e16c936918964d9bd746a2734c25c3b43e328",
                 3: "ab4760d5d5567680be6c3c19e5574174c1edc5919a10cc83ee442f31ce4d9e0f"}
IDENTITY_TOL = 1e-6              # 4a: C′ through the generalised rebuild against the stored rebuilds (max |Δ|)
SCOPE = C.SCOPE

# name -> (configuration, the score directory it reads)
CFGS = {
    "sepnet_stem": ((DI_STEM, "stem", "native", "own"), DI_STEM),                 # (i), declared
    "sepnet_stem_gcc": ((DI_STEM, "stem", "gcc", "own"), DI_STEM),
    "sepnet_stem_vs_mega53": ((DI_STEM, "mega53", "native", "own"), DI_STEM),     # with 1c's reference
    "sepnet_mega53": ((DI_MEGA, "mega53", "native", "own"), DI_MEGA),             # (ii), declared
    "sepnet_mega53_gcc": ((DI_MEGA, "mega53", "gcc", "own"), DI_MEGA),
    "sepnet_mega53_rebuild_only": ((DI_MEGA, "stem", "native", "own"), DI_MEGA),
    "current": (LO.CURRENT, "cprime"),                                            # today's objective
    "matched_1b": (LO.MATCHED, LO.MATCHED_DI),
    "mega53": ((MEGA_1C, "mega53", "native", "own"), MEGA_1C),                    # 1c's cell
    "mega53_rebuild_only": ((MEGA_1C, "stem", "native", "own"), MEGA_1C),
    "reference_only": (("cprime", "mega53", "native", "own"), "cprime@mega53"),
}
BASE = ("current", "matched_1b", "mega53")          # every cell needs these (experiments 1, 1b, 1c)
PRIMARY = {"P1_sepnet_stem_minus_current": ("sepnet_stem", "current"),
           "P2_sepnet_mega53_minus_mega53": ("sepnet_mega53", "mega53")}
DIFFS = {**PRIMARY,
         "sepnet_mega53_minus_current": ("sepnet_mega53", "current"),          # the stacked route
         "sepnet_stem_minus_matched_1b": ("sepnet_stem", "matched_1b"),
         "sepnet_mega53_minus_matched_1b": ("sepnet_mega53", "matched_1b"),
         "sepnet_mega53_minus_sepnet_stem": ("sepnet_mega53", "sepnet_stem"),
         "mega53_minus_current": ("mega53", "current"),
         "sepnet_stem_gcc_minus_current": ("sepnet_stem_gcc", "current"),
         "sepnet_stem_vs_mega53_minus_reference_only": ("sepnet_stem_vs_mega53", "reference_only"),
         "sepnet_mega53_rebuild_only_minus_mega53_rebuild_only": ("sepnet_mega53_rebuild_only",
                                                                  "mega53_rebuild_only")}
# shares, (numerator a − b) / (denominator c − d), band-weighted with Fieller's interval
SHARES = {"sepnet_stem_of_1b_gain": (("sepnet_stem", "current"), ("matched_1b", "current")),
          "sepnet_mega53_of_1b_gain": (("sepnet_mega53", "current"), ("matched_1b", "current")),
          "P2_of_1b_minus_mega53": (("sepnet_mega53", "mega53"), ("matched_1b", "mega53"))}
ROW_DIFFS = ("P1_sepnet_stem_minus_current", "P2_sepnet_mega53_minus_mega53", "sepnet_mega53_minus_current")
KEYS = ("cross_half", "reliable_accuracy")


def out():
    return LO.OUT


def net_path(fold):
    return K.HOME / LO.SEPNET_PATTERN.format(f=fold)


def library_bands(cfg, lib_rows):
    """The bands of the residual-library entries (training and validation) a separator-robust
    network used, from its `config.json` and the library's `lib.json` rows."""
    band = {m["id"]: m["band"] for m in lib_rows}
    used = cfg.get("sep") or {}
    if not used:
        raise AssertionError("not a separator-robust network: its config has no library entries")
    return {band[i] for i in list(used.get("train", [])) + list(used.get("val", []))}


def sepnet_pool(cfg, fold, lib_rows, pool_of):
    """Amendment 4a: every band a separator-robust network learned from: its parent C′'s training
    pool (all three caches, as 1b/1c's C′ check), the fine-tune's own caches, and the residual
    library's entries (training and validation). `pool_of(fold, cache_dirs)` is
    `di_fine_structure.train_pool_bands`."""
    from learn import di_fine_structure as DF

    parent = pool_of(fold, [DF.MODELS / c for c in DF.CACHES])
    own = pool_of(fold, [pathlib.Path(c) for c in cfg.get("caches", [])])
    return set(parent) | set(own) | library_bands(cfg, lib_rows)


def assert_sepnet_ok(band, path, fold, lib_rows=None, pool_of=None, sha=None):
    """Amendment 4a: the network is the pinned one for `fold`, fine-tuned from that fold's C′ with
    fold `fold`, and the part's band is in none of its pools."""
    from learn import di_fine_structure as DF
    from learn import song_settings as SS

    path = pathlib.Path(path)
    want = SEPNET_SHA256[fold]
    got = (sha or LO.file_sha256)(path)
    if got != want:
        raise AssertionError(f"{path} hashes to {got}, not the pinned {want}")
    cfg = json.loads((path.parent / "config.json").read_text())
    if cfg.get("fold") != fold:
        raise AssertionError(f"{path} was fine-tuned for fold {cfg.get('fold')}, not {fold}")
    if pathlib.Path(cfg.get("resume", "")) != pathlib.Path(SS.cprime(fold)):
        raise AssertionError(f"{path} resumed from {cfg.get('resume')}, not fold {fold}'s C′")
    if lib_rows is None:
        lib_rows = json.loads((path.parent.parent / "lib.json").read_text())["rows"]
    if band in sepnet_pool(cfg, fold, lib_rows, pool_of or DF.train_pool_bands):
        raise AssertionError(f"leak: band {band!r} is in {path}'s training pool or residual library")


def _source(src):
    import numpy as np

    from learn import song_settings as SS

    return {"stem": lambda slug, part: SS.stem(slug),
            "mega53": lambda slug, part: np.load(LO.sep_crop_path("mega53", slug))}[src]


def stored_rebuild(src, slug):
    """The C′ rebuild 1d's cell is compared with: step 3's (`song_settings` rebuilt/) or 1c's."""
    import numpy as np

    from learn import song_settings as SS

    return np.load(SS.OUT / "rebuilt" / f"{slug}.npy" if src == "stem"
                   else out() / LO.REBUILD_DIR[MEGA_1C] / f"{slug}.npy")


def identity_problems(diffs, tol=IDENTITY_TOL):
    """{slug: max |Δ| or None (missing / length mismatch)} -> the problems."""
    return {s: d for s, d in diffs.items() if d is None or not d <= tol}


def cmd_identity(src):
    """Amendment 4a (zero renders): C′ through the generalised `rebuild_from` reproduces the stored
    C′ rebuild of the same source (step 3's for the stem, 1c's for Mega-53), so only the network
    changes between the cells. -> ok; writes rebuilt-csep-<src>/identity.json."""
    import numpy as np

    tmp = out() / f"identity-csep-{src}"
    LO.rebuild_from(LO.SEPNET_DI[src], _source(src), out_dir=tmp, gate=False)
    diffs = {}
    for f in sorted(tmp.glob("*.npy")):
        a, b = np.load(f), stored_rebuild(src, f.stem)
        diffs[f.stem] = float(np.max(np.abs(a - b))) if a.shape == b.shape else None
    bad = identity_problems(diffs)
    n = len(diffs)
    rec = {"ok": not bad and n == 24, "parts": n, "max_abs_diff": max((d for d in diffs.values() if d is not None),
                                                                     default=None),
           "tol": IDENTITY_TOL, "problems": bad, "per_part": diffs}
    d = out() / LO.REBUILD_DIR[LO.SEPNET_DI[src]]
    d.mkdir(parents=True, exist_ok=True)
    K._atomic(d / "identity.json", rec)
    print(f"identity {src}: {n} parts, largest |Δ| {rec['max_abs_diff']}, ok {rec['ok']}", flush=True)
    return rec["ok"]


def cmd_rebuild(src):
    """4a's identity check first; then the fold's separator-robust network (pinned) rebuilds `src`
    (the htdemucs stem, or 1c's Mega-53 crop) exactly as 1b and 1c rebuilt theirs
    (`LO.rebuild_from`), with 4a's network and leak assertions. Amendment 4b: the level check is
    against the paired comparator's stored C′ rebuild of the same source, within 0.05 LU. `check.json`
    gates the renders and is ok only if the identity check passed too."""
    if src == "mega53" and not C.sep_ok("mega53"):
        raise SystemExit("mega53: 1c's separation checks have not passed")
    if not cmd_identity(src):
        d = out() / LO.REBUILD_DIR[LO.SEPNET_DI[src]]
        d.mkdir(parents=True, exist_ok=True)
        K._atomic(d / "check.json", {"ok": False, "problems": "identity check failed (identity.json)"})
        raise SystemExit(f"{src}: C′ through the generalised rebuild doesn't reproduce the stored rebuild")
    LO.rebuild_from(LO.SEPNET_DI[src], _source(src), net=net_path, extra_leak=assert_sepnet_ok,
                    level_ref=lambda slug: LO.lufs(stored_rebuild(src, slug)))


def complete(cells, renders, expected=EXPECTED):
    """Amendment 4 (as 2a): figures for a 1d cell only with 72 cells and exactly 3,528 renders."""
    if cells != expected["cells"] or renders != expected["renders"]:
        return f"{cells} cells and {renders} renders, not {expected['cells']} and {expected['renders']}"
    return None


def renders_of(di):
    return sum(json.loads(p.read_text())["renders"] for p in (out() / "renders" / di).glob("*/*.json"))


def comparator_summary():
    """4a's C′-at-S renders (two per cell, apart from the 3,528): count and deviations."""
    devs, n, cells = [], 0, 0
    for di in (DI_STEM, DI_MEGA):
        for p in (out() / "renders" / di).glob("*/*.json"):
            c = json.loads(p.read_text()).get("comparator")
            if c:
                cells += 1
                n += c["renders"]
                devs.append(c["max_dev"])
    return {"cells": cells, "renders": n, "max_dev": max(devs, default=None),
            "over_tol": sum(v > LO.CHECK_TOL for v in devs)}


def flac_vs_float(di, cells):
    devs = []
    for c in cells:
        f = out() / "scores" / di / c[0] / f"{c[1]}.json"
        if f.exists():
            fv = json.loads(f.read_text()).get("flac_vs_float_S") or {}
            devs += [v for hv in fv.values() for v in hv.values()]
    return {"n": len(devs), "max": max(devs, default=None), "over_tol": sum(v > LO.CHECK_TOL for v in devs)}


def load_cell(c):
    """{score dir: scores} for a cell, or None without the measure DI's or a base score."""
    dirs = {"measure", *(d for _, d in CFGS.values())}
    files = {d: out() / "scores" / d / c[0] / f"{c[1]}.json" for d in dirs}
    if not files["measure"].exists() or not all(files[CFGS[n][1]].exists() for n in BASE):
        return None
    return {d: json.loads(f.read_text())["scores"] for d, f in files.items() if f.exists()}


def _paired_rows(rows, a, b):
    return LO.paired(rows[a], rows[b]) if a in rows and b in rows else {}


def diffs_and_shares(rows):
    """rows: {name: {cell: (slug, band, cls, value)}} -> the declared differences, the interaction
    P2 − P1, and the shares (Fieller), each on the cells with both sides."""
    r = {dn: LO.agg(_paired_rows(rows, a, b)) for dn, (a, b) in DIFFS.items()}
    p1, p2 = _paired_rows(rows, *PRIMARY["P1_sepnet_stem_minus_current"]), _paired_rows(
        rows, *PRIMARY["P2_sepnet_mega53_minus_mega53"])
    r["interaction_P2_minus_P1"] = LO.agg(LO.paired(p2, p1))
    sh = {}
    for name, ((a, b), (c, d)) in SHARES.items():
        num, den = _paired_rows(rows, a, b), _paired_rows(rows, c, d)
        both = set(num) & set(den)
        sh[name] = C.share({k: num[k] for k in both}, {k: den[k] for k in both}) if both else None
    r["shares"] = sh
    return r


def row_report(dirvals, ceil, ps, bt, row):
    """One bleed or leak row (amendment 3a's rows): each name's cross-half on the row's kept
    directions, P1, P2 and the stacked route, and the shares, on the same cells."""
    rr = {n: C.row_rows(dirvals, ps, bt, row, n) for n in CFGS}
    rr = {n: v for n, v in rr.items() if v}
    o = {n: LO.agg(v) for n, v in rr.items() if n in ("sepnet_stem", "sepnet_mega53", *BASE)}
    cells = set(rr.get("current", {}))
    o["ceiling"] = LO.agg({c: (c[0], ps[c[0]]["band"], ps[c[0]]["gain_class"], ceil[c]) for c in cells if c in ceil})
    d = diffs_and_shares(rr)
    o.update({k: d[k] for k in ROW_DIFFS})
    o["shares"] = d["shares"]
    return o


def cmd_report():
    """Zero renders: the two 1d cells against the truth (experiment 1's measure-DI scores), paired
    with today's objective, 1b and 1c; on all of Σ, its subsets and without arm A; per band; the
    bleed and leak rows; the rebuild checks, renders and FLAC against float; completeness."""
    meta, sig = LO.load_sigma()
    ps = K.parts()
    per, dirvals, ceil = {}, {}, {}
    for c, pts in sorted(sig.items()):
        sc = load_cell(c)
        if sc is None:
            continue
        true = LO._vals(sc["measure"], LO.TRUE)
        per[c] = {n: {sub: LO.subset_measures(pts, LO._vals(sc[d], cfg), true, srcs)
                      for sub, srcs in C.SUBSETS_1C.items()}
                  for n, (cfg, d) in CFGS.items() if d in sc}
        ceil[c] = LO.ceiling(true)
        dirvals[c] = {n: C.directions(LO._vals(sc[d], cfg), true) for n, (cfg, d) in CFGS.items() if d in sc}

    def rows(name, sub, key):
        return {c: (c[0], ps[c[0]]["band"], ps[c[0]]["gain_class"], v[name][sub][key]) for c, v in per.items()
                if name in v}

    status = {}
    for di in (DI_STEM, DI_MEGA):
        n_cells = sum(1 for c in per if (out() / "scores" / di / c[0] / f"{c[1]}.json").exists())
        n_r = renders_of(di)
        chk = out() / LO.REBUILD_DIR[di] / "check.json"
        status[di] = {"cells_scored": n_cells, "renders_used": n_r, "renders_expected": EXPECTED["renders"],
                      "incomplete": complete(n_cells, n_r),
                      "rebuild_check": json.loads(chk.read_text()) if chk.exists() else None,
                      "flac_vs_float_S": flac_vs_float(di, per)}
    rep = {"sigma": meta["hash"], "cells": len(per), "scope": SCOPE, "status": status, "subsets": {}}
    for sub in C.SUBSETS_1C:
        r = {"ceiling": LO.agg(rows("current", sub, "ceiling"))}
        for name in CFGS:
            r[name] = {k: LO.agg(rows(name, sub, k)) for k in (*KEYS, "same_half")}
        for k in KEYS:
            d = diffs_and_shares({n: rows(n, sub, k) for n in CFGS})
            for dn, v in d.items():
                r.setdefault(dn, {})[k] = v
        rep["subsets"][sub] = r
    bt = C.load_bleed_table()
    rep["bleed_and_leak_rows"] = {row: row_report(dirvals, ceil, ps, bt, row) for row in C.ROWS}
    per_band = {}
    names = ("sepnet_stem", "sepnet_mega53", "current", "mega53", "matched_1b")
    for c, v in per.items():
        per_band.setdefault(ps[c[0]]["band"], {}).setdefault(c[0], []).append(
            {**{n: v[n]["all"]["cross_half"] for n in names if n in v}, "ceiling": v["current"]["all"]["ceiling"]})
    rep["per_band_cross_half"] = {}
    for b, pp in sorted(per_band.items()):
        m = {k: LO._mean(LO._mean(t.get(k) for t in vals) for vals in pp.values()) for k in (*names, "ceiling")}
        for dn, (a, z) in PRIMARY.items():
            m[dn] = None if m.get(a) is None or m.get(z) is None else m[a] - m[z]
        rep["per_band_cross_half"][b] = m
    rep["comparator"] = comparator_summary()
    rep["renders_used"] = sum(s["renders_used"] for s in status.values()) + rep["comparator"]["renders"]
    rep["renders_expected"] = 2 * EXPECTED["renders"] + 2 * EXPECTED["cells"]
    a = rep["subsets"]["all"]
    rep["primary"] = {}
    for dn, (x, _) in PRIMARY.items():
        di = CFGS[x][1]
        rep["primary"][dn] = ({"refused": status[di]["incomplete"]} if status[di]["incomplete"]
                              else a[dn]["cross_half"])
    K._atomic(out() / "report-1d.json", rep)

    def f(s):
        if not s or s.get("band_weighted_mean") is None:
            return str(s)
        if s.get("lo90") is None:
            return f"{s['band_weighted_mean']:+.3f}"
        return f"{s['band_weighted_mean']:+.3f} [{s['lo90']:+.3f}, {s['hi90']:+.3f}]"

    for n in ("sepnet_stem", "sepnet_mega53", "current", "mega53", "matched_1b"):
        print(f"{n} cross-half:", f(a[n]["cross_half"]))
    print("ceiling:", f(a["ceiling"]))
    for dn in (*PRIMARY, "sepnet_mega53_minus_current", "interaction_P2_minus_P1"):
        print(dn, "cross-half:", f(a[dn]["cross_half"]), "| reliable acc:", f(a[dn]["reliable_accuracy"]))
    for name, s in a["shares"]["cross_half"].items():
        print("share", name, s)
    for row, rr in rep["bleed_and_leak_rows"].items():
        print(f"  {row}:", "; ".join(f"{k} {f(rr[k])}" for k in ROW_DIFFS))
    print("comparator (C′ at S against experiment 1):", rep["comparator"])
    for di, s in status.items():
        print(di, "renders", s["renders_used"], "of", s["renders_expected"], "cells", s["cells_scored"],
              "flac vs float", s["flac_vs_float_S"], "incomplete:" if s["incomplete"] else "complete",
              s["incomplete"] or "")
    print(SCOPE)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("identity", "rebuild", "report"))
    ap.add_argument("--src", choices=LO.SEPNET_SOURCES, default="stem")
    a = ap.parse_args(argv)
    if a.cmd == "identity":
        cmd_identity(a.src)
    elif a.cmd == "rebuild":
        cmd_rebuild(a.src)
    else:
        cmd_report()


if __name__ == "__main__":
    main()
