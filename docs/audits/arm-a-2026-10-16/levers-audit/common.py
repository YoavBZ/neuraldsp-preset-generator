"""Independent loaders and stats for the audit (only K.parts, SS.cells and folds borrowed)."""
import json, math, pathlib, statistics, sys
WT = pathlib.Path("/Users/yoavbz/projects/neuraldsp-preset-generator/.claude/worktrees/bridge-cse_01TcpCZvuiya2xZxn5XRQ6PT")
sys.path.insert(0, str(WT)); sys.path.insert(0, str(WT / "research"))
from scipy import stats as st
from learn import knob_ceiling as K
from learn import song_settings as SS

H = pathlib.Path("~/ndsp-presets/learn").expanduser()
SSO = H / "song-settings"; LV = SSO / "levers"; KC = H / "knob-ceiling"
PS = K.parts(); FOLDS = SS.folds()
CELLS = SS.cells()

def J(p): return json.loads(pathlib.Path(p).read_text())
def ok(x): return isinstance(x, (int, float)) and math.isfinite(x) and x > 0

_kc = {}
def kc(slug, amp):
    if (slug, amp) not in _kc: _kc[(slug, amp)] = J(KC / "cells" / slug / amp / "result.json")
    return _kc[(slug, amp)]

def raw_units():
    """{(slug,amp,search): {'band','cls','held', 'd': {...}}} straight from the files."""
    out = {}
    for slug, amp, search, held in CELLS:
        p = PS[slug]; r = kc(slug, amp)
        d = {"S": r["menu"][r["start"]][held]}
        run = r["runs"][search]
        d["K_S"] = run["K_S"]["held"] if "K_S" in run else None
        a = J(SSO / "armA" / slug / amp / f"{search}.json"); assert a["held_half"] == held and a["search_half"] == search
        d["A"] = a["judge"][held]
        e = LV / "exp1" / slug / amp / f"{search}.json"
        if e.exists():
            ee = J(e); assert ee["held"] == held
            for n, v in ee["judge"].items(): d[n] = v[held]
        for tag in ("C'", "lever-shrink-0.5"):
            q = LV / "early" / tag / slug / amp / f"{search}.json"
            if q.exists():
                qq = J(q); assert qq["held"] == held
                d["3-C'" if tag == "C'" else "3-C'+shrink-0.5"] = qq["judge"][held]
        out[(slug, amp, search)] = {"band": p["band"], "cls": p["gain_class"], "held": held, "d": d}
    return out

def tci(xs, conf=0.90):
    xs = list(xs); m = statistics.fmean(xs)
    if len(xs) < 2: return m, None, None
    h = st.t.ppf(0.5 + conf / 2, len(xs) - 1) * statistics.stdev(xs) / math.sqrt(len(xs))
    return m, m - h, m + h

def bw(rows):
    """rows {(slug,amp,search): (band, value)} -> part means -> band means -> mean, 90% t on bands."""
    part = {}
    for (s, a, h), (b, v) in rows.items(): part.setdefault((s, b), []).append(v)
    band = {}
    for (s, b), v in part.items(): band.setdefault(b, []).append(statistics.fmean(v))
    bm = {b: statistics.fmean(v) for b, v in band.items()}
    m, lo, hi = tci(bm.values())
    pm = [statistics.fmean(v) for v in part.values()]
    return {"mean": m, "lo": lo, "hi": hi, "bands": len(bm), "parts": len(pm), "n": len(rows),
            "band_means": bm, "part_ci": tci(pm),
            "lobo": [statistics.fmean([x for c, x in bm.items() if c != b]) for b in sorted(bm)] if len(bm) > 1 else []}

def logrows(U, a, b="S", keys=None):
    out = {}
    for k, u in U.items():
        if keys is not None and k not in keys: continue
        x, y = u["d"].get(a), u["d"].get(b)
        if ok(x) and ok(y): out[k] = (u["band"], math.log(x / y))
    return out

def fmt(r): return f"{r['mean']:+.4f} [{r['lo']:+.4f}, {r['hi']:+.4f}] (bands {r['bands']}, parts {r['parts']}, dirs {r['n']})"
