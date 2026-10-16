"""Summarise step 0c's per-cell DAC files into a small committed JSON (zero renders)."""
import json, pathlib, statistics
B = pathlib.Path("~/ndsp-presets/learn/di-fine-structure/step0").expanduser()
OUT = pathlib.Path(__file__).resolve().parent / "exp4-step0c-dac-cells.json"
reading = json.loads((B / "dac" / "reading.json").read_text())
f3 = set(reading["cells"])
FINE = ("crest_1ms_err", "crest_5ms_err", "crest_10ms_err", "quiet_db", "quiet_frames", "gap_db", "snr_db", "hf_3_8k_db")
def r4(x): return None if x is None else round(x, 4)
cells = {}
for p in sorted((B / "dac").glob("*.json")):
    if p.name == "reading.json": continue
    r = json.loads(p.read_text()); k = r["cell"]
    d0 = json.loads((B / "d0" / p.name).read_text())
    c = {"fold3": k in f3, "renders": r["renders"],
         "m_true_di": {h: r4(v) for h, v in d0["measure"]["m"]["measure"].items()},
         "m_cprime": {h: r4(v) for h, v in d0["cprime"]["m"]["measure"].items()}}
    for q, name in (("rs", "resample_only"), ("q4", "dac4"), ("q9", "dac9")):
        e = {"fine": {f: r4(r[q]["fine"].get(f)) for f in FINE}}
        if q != "rs":
            e["gcc_lag"] = r[q]["gcc_lag"]
            e["m"] = {h: r4(v) for h, v in r[q]["m"]["measure"].items()} if "m" in r[q] else None
            e["mask_null"] = r[q]["m"]["v"] == r[q]["m"]["measure"] if "m" in r[q] else None
            if "dropped" in r[q]: e["dropped"] = r[q]["dropped"]
        c[name] = e
    cells[k] = c
def mean(xs): xs = [x for x in xs if x is not None]; return r4(statistics.fmean(xs)) if xs else None
summ = {}
for sel, keys in (("fold3", [k for k in cells if cells[k]["fold3"]]), ("all12", list(cells))):
    s = {"cells": len(keys), "m_true_di": mean(cells[k]["m_true_di"]["full"] for k in keys),
         "m_cprime": mean(cells[k]["m_cprime"]["full"] for k in keys)}
    for q in ("dac4", "dac9"):
        s[f"m_{q}"] = mean((cells[k][q]["m"] or {}).get("full") for k in keys)
        s[f"m_{q}_positive"] = sum(((cells[k][q]["m"] or {}).get("full") or 0) > 0 for k in keys)
    for q in ("resample_only", "dac4", "dac9"):
        for f in ("crest_1ms_err", "crest_5ms_err", "crest_10ms_err", "quiet_db", "snr_db"):
            s[f"{q}_{f}_mean"] = mean(cells[k][q]["fine"][f] for k in keys)
            if f.startswith("crest") or f == "quiet_db":
                s[f"{q}_{f}_maxabs"] = r4(max((abs(cells[k][q]["fine"][f]) for k in keys if cells[k][q]["fine"][f] is not None), default=None))
    summ[sel] = s
out = {"source": "~/ndsp-presets/learn/di-fine-structure/step0/dac/*.json and step0/d0/*.json (exp4 step 0c)",
       "built": "2026-10-16, zero renders, by a summary script over the stored files",
       "notes": ["m is the S-against-T margin (log units) scored with the measure DI's activity mask; 'mask_null' is true where the round trip's own mask gives the identical margin",
                 "m_true_di and m_cprime are D0's measure-DI and C' renders of the same cells, the comparators the reading used",
                 "fine metrics are the round trip against the measure DI: crest errors in dB per 1/5/10-ms frame, quiet_db is the 5-ms level over frames >=20 dB under the target's loudest, dB re the target",
                 "resample_only is the 44.1 kHz resample there and back with no codec, rendered nowhere (fine metrics only)"],
       "reading": {k: reading[k] for k in ("cells", "opens", "mean_m_q9", "mean_m_true", "bar", "max_crest1_err")},
       "summary": summ, "cells": cells}
OUT.write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps(summ, indent=1))
