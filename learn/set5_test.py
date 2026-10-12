"""The set-5 held-out test (`docs/set5-test-plan.md`): the corrected DI network (three seeds)
against the old network and against `generate`'s starting presets.

    $TORCH_PY -m learn.set5_test render 0 6      # refused until the ledger entry is committed
    $TORCH_PY -m learn.set5_test score
    $TORCH_PY -m learn.set5_test report
"""

from __future__ import annotations

import json
import math
import pathlib
import statistics
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import confirm_run as CR  # noqa: E402
from learn import phase2_set3 as P  # noqa: E402
from learn import set3_gap_split as G  # noqa: E402

D3 = CR.HOME / "learn/direc"
OUT = D3 / "set5-test"
DECL = PLUGIN_ROOT / "docs/validation-set5.json"
TEST_ID = "set5-cprime-test-2026-10-12"
NETS = {"C": D3 / "models-set3/fold2.pt", "Cp0": D3 / "models-cprime/fold2.pt",
        "Cp1": D3 / "models-cprime-s1/fold2.pt", "Cp2": D3 / "models-cprime-s2/fold2.pt"}
SEEDS = ("Cp0", "Cp1", "Cp2")
KINDS = ("measfix",) + tuple(NETS)
STARTS = {"clean": PLUGIN_ROOT / "docs/clean-baseline-choice.json",
          "crunch": PLUGIN_ROOT / "docs/crunch-baseline-choice.json"}
T90 = {1: 6.314, 2: 2.920, 3: 2.353, 4: 2.132, 5: 2.015, 6: 1.943, 7: 1.895, 8: 1.860}


def parts():
    """slug -> {crop, judge_lag, band, gain_class, scope, publisher_original}: kept set-5 parts."""
    d = json.loads(DECL.read_text())
    root = pathlib.Path(d["crops_root"]).expanduser()
    out = {}
    for p in d["parts"]:
        crop = root / p["slug"]
        if not (crop / "di.wav").exists():
            continue
        out[p["slug"]] = dict(crop=crop, judge_lag=p["judge_lag_samples"], band=p["band"],
                              gain_class=p["gain_class"], scope=p["scope"],
                              publisher_original=p["publisher_original"])
    return out


def _ledger_committed():
    def git(*a):
        return subprocess.run(["git", "-C", str(PLUGIN_ROOT), *a], capture_output=True, text=True)

    rel = str(DECL.relative_to(PLUGIN_ROOT))
    if git("diff", "--quiet", "HEAD", "--", rel).returncode:
        return False
    return any(u.get("test_id") == TEST_ID for u in json.loads(DECL.read_text()).get("held_out_uses", []))


def build_di(kind, part, net):
    import numpy as np
    import torch

    from learn import direc as D
    from learn.direc_check import to_lufs

    if kind == "measfix":
        return CR.build_di("measfix", part)
    rec = CR.mono(pathlib.Path(part["crop"]) / "reference.wav")
    return to_lufs(D.rebuild(net, rec.astype(np.float32), device=torch.device("cpu")).astype(np.float64))


def render(shard):
    import numpy as np
    import soundfile as sf

    import render_preset_panel as RP
    from learn import direc as D
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    if not _ledger_committed():
        raise SystemExit("commit the ledger entry before any set-5 render")
    pack = load_pack("morgan")

    class PanelRenderer(AudioUnitRenderer):
        commands: dict = {}

        def _state_command(self, settings):
            select, edits = self.commands[settings["panel"]]
            command = {"edits": edits}
            if select is not None:
                command["selectAmp"] = select
            return command

    nets = {k: D.load_model(v).eval() for k, v in NETS.items()}
    r = PanelRenderer("morgan", process_policy="reuse")
    M = P.menus(pack, r)
    PanelRenderer.commands = {f"{amp}|{n}": v for amp, m in M.items() for n, v in m.items()}
    ps = parts()
    try:
        for slug in sorted(ps)[shard[0]::shard[1]]:
            for kind in KINDS:
                base = OUT / kind / slug
                if (base / "done").exists():
                    continue
                base.mkdir(parents=True, exist_ok=True)
                di = build_di(kind, ps[slug], nets.get(kind))
                np.save(base / "di.npy", di)
                d32 = di.astype(np.float32)
                for amp, m in M.items():
                    (base / amp).mkdir(exist_ok=True)
                    r.render(d32, {"panel": f"{amp}|template+R"})            # warm-up per amp
                    for n in m:
                        y = np.asarray(r.render(d32, {"panel": f"{amp}|{n}"}).audio, np.float64)
                        sf.write(base / amp / f"{RP._slug(n)}.flac",
                                 y * (0.99 / max(np.abs(y).max(), 1e-12)), P.SR, subtype="PCM_24")
                (base / "done").write_text("")
                print(slug, kind, flush=True)
    finally:
        r.close()


def _score_part(job):
    import numpy as np

    import render_preset_panel as RP
    from analysis.aligned import aligned_distance
    from learn.rebuilt_judge import rebuilt_distance

    slug, part, names = job
    ref = CR.mono(pathlib.Path(part["crop"]) / "reference.wav")
    res = {}
    for kind in KINDS:
        d = OUT / kind / slug
        di = np.load(d / "di.npy")
        for amp, ns in names.items():
            for n in ns:
                y = P.mono(d / amp / f"{RP._slug(n)}.flac")
                for h, (a, b) in (("A", P.HALF_A), ("B", P.HALF_B)):
                    if kind == "measfix":
                        x, proxy = aligned_distance(ref, y, di, lag=part["judge_lag"], render_latency=P.LATENCY,
                                                    start_s=a, end_s=b), False
                    else:
                        x, proxy = rebuilt_distance(ref, y, di, start_s=a, end_s=b)
                    res.setdefault(f"{kind}|{amp}|{h}", {})[n] = (x.distance, proxy)
    print(slug, flush=True)
    return slug, res


def score(workers=7):
    from concurrent.futures import ProcessPoolExecutor

    ps, names = parts(), G.menu_names()
    for s in ps:
        for k in KINDS:
            if not (OUT / k / s / "done").exists():
                raise SystemExit(f"missing renders: {k}/{s}")
    jobs = [(s, {**ps[s], "crop": str(ps[s]["crop"])}, names) for s in sorted(ps)]
    with ProcessPoolExecutor(workers) as ex:
        R = dict(ex.map(_score_part, jobs))
    (OUT / "distances.json").write_text(json.dumps(R))


def _pick(row):
    row = {n: v[0] for n, v in row.items() if v[0]}
    return min(row, key=lambda n: (row[n], n)) if row else None


def _band_gate(rows):
    """rows: (band, x). The plan's gate on band means: t-interval, bands − 1 df."""
    by = {}
    for b, x in rows:
        by.setdefault(b, []).append(x)
    bm = [statistics.fmean(v) for v in by.values()]
    out = {"bands": len(bm), "per_band": {b: round(statistics.fmean(v), 4) for b, v in sorted(by.items())},
           "cells": len(rows), "part_weighted": round(statistics.fmean(x for _, x in rows), 4) if rows else None}
    if len(bm) < 2:
        out["outcome"] = "too few bands"
        return out
    mu, se = statistics.fmean(bm), statistics.stdev(bm) / math.sqrt(len(bm))
    t = T90[len(bm) - 1]
    out.update(band_mean=round(mu, 4), lo90=round(mu - t * se, 4), hi90=round(mu + t * se, 4),
               bands_negative=sum(x < 0 for x in bm), smallest_detectable=round(-t * se, 4))
    out["outcome"] = ("helps" if out["hi90"] < 0 and out["bands_negative"] > len(bm) / 2 else
                      "futile" if out["lo90"] > -0.02 else "inconclusive")
    out["leave_one_band_out"] = {b: round(statistics.fmean([x for bb, x in zip(by, bm) if bb != b]), 4) for b in by}
    return out


def report():
    ps = parts()
    R = json.loads((OUT / "distances.json").read_text())
    starts = {c: json.loads(p.read_text())["presets"] for c, p in STARTS.items()}
    cells = {}                                   # (slug, amp) -> {who: [score per direction]}
    proxies = {k: 0 for k in NETS}
    for s in ps:
        for amp in P.AMPS:
            per = {}
            for h, other in (("A", "B"), ("B", "A")):
                M = R[s][f"measfix|{amp}|{other}"]
                picks = {k: _pick(R[s][f"{k}|{amp}|{h}"]) for k in NETS}
                for k in NETS:
                    proxies[k] += sum(v[1] for v in R[s][f"{k}|{amp}|{h}"].values())
                picks["oracle"] = _pick(R[s][f"measfix|{amp}|{h}"])
                cls = ps[s]["gain_class"]
                picks["start"] = starts[cls][amp] if cls in starts else None
                for k, n in picks.items():
                    per.setdefault(k, []).append(M[n][0] if n and M.get(n) and M[n][0] else None)
            cells[(s, amp)] = per

    def ratio(per, a, b):
        """The mean over directions of log(a/b); a may be a tuple of seeds (their mean)."""
        vals = []
        for i in range(2):
            num = [per[k][i] for k in (a if isinstance(a, tuple) else (a,))]
            den = per[b][i]
            if not den or not all(num):
                return None
            vals.append(statistics.fmean(math.log(x / den) for x in num))
        return statistics.fmean(vals)

    def rows(a, b, cls=None, scope="in_scope", originals=False):
        out = []
        for (s, amp), per in cells.items():
            p = ps[s]
            if p["scope"] != scope or (cls and p["gain_class"] != cls) or (originals and not p["publisher_original"]):
                continue
            x = ratio(per, a, b)
            if x is not None:
                out.append((p["band"], x))
        return out

    res = {}
    for tag, cls in (("all", None), ("clean", "clean"), ("crunch", "crunch")):
        for name, a, b in (("gate1_Cp_vs_C", SEEDS, "C"), ("gate2_Cp_vs_start", SEEDS, "start"),
                           ("C_vs_start", "C", "start"), ("oracle_vs_start", "oracle", "start"),
                           *((f"{k}_vs_C", k, "C") for k in SEEDS), *((f"{k}_vs_start", k, "start") for k in SEEDS)):
            res[f"{name}|{tag}"] = _band_gate(rows(a, b, cls))
            res[f"{name}|{tag}|originals"] = _band_gate(rows(a, b, cls, originals=True))
    res["high_gain_report_only|Cp_vs_C"] = _band_gate(rows(SEEDS, "C", scope="report_only"))
    out = {"gate1": res["gate1_Cp_vs_C|all"], "gate2_crunch": res["gate2_Cp_vs_start|crunch"],
           "gate2_pooled": res["gate2_Cp_vs_start|all"], "proxy_uses": proxies, "results": res}
    (OUT / "result.json").write_text(json.dumps(out, indent=1, default=float))
    print("GATE 1 (C′ vs C, pooled):", out["gate1"].get("outcome"), {k: out["gate1"].get(k) for k in ("band_mean", "lo90", "hi90", "bands_negative", "bands")})
    print("GATE 2 (C′ vs start, crunch):", out["gate2_crunch"].get("outcome"), {k: out["gate2_crunch"].get(k) for k in ("band_mean", "lo90", "hi90", "bands_negative", "bands")})
    for k, v in res.items():
        if "band_mean" in v:
            print(f"  {k:40s} band {v['band_mean']:+.3f} [{v['lo90']:+.3f}, {v['hi90']:+.3f}] part {v['part_weighted']:+.3f} "
                  f"neg {v['bands_negative']}/{v['bands']} {v['outcome']}")
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "render":
        render((int(sys.argv[2]), int(sys.argv[3])))
    else:
        {"score": score, "report": report}[cmd]()
