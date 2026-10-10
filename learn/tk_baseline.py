"""Tone King starting presets for clean and crunch (`docs/toneking-baseline-plan.md`).

    $TORCH_PY -m learn.tk_baseline dry                 # dry copies of the menu (regenerated)
    $TORCH_PY -m learn.tk_baseline repeat              # repeatability, in log distance
    $TORCH_PY -m learn.tk_baseline render dev 0 6      # shard 0 of 6, by preset
    $TORCH_PY -m learn.tk_baseline score dev
    $TORCH_PY -m learn.tk_baseline choose              # writes docs/toneking-baseline-choice.json
    $TORCH_PY -m learn.tk_baseline render heldout 0 6  # refused until the choice and ledger are committed
    $TORCH_PY -m learn.tk_baseline score heldout
    $TORCH_PY -m learn.tk_baseline check
"""

from __future__ import annotations

import hashlib
import json
import math
import pathlib
import shutil
import statistics
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import confirm_run as CR  # noqa: E402
from learn import phase2_set3 as P  # noqa: E402
from learn import set3_gap_split as G  # noqa: E402
from learn import songs_check as SC  # noqa: E402

TK_ROOT = pathlib.Path("/Library/Audio/Presets/Neural DSP/Tone King Imperial MKII")
OUT = CR.HOME / "learn/tk-baseline"
PINNED = PLUGIN_ROOT / "docs/sound-desc-test-parts.json"
CHOICE = PLUGIN_ROOT / "docs/toneking-baseline-choice.json"
LEDGER = PLUGIN_ROOT / "docs/validation-datasets.json"
TEST_ID = "toneking-baseline-2026-10-11"
LATENCY = 51            # an impulse through a bypassed preset comes back 51 samples later
PREROLL = 48000         # a fresh Tone King process starts muted for up to 0.87 s
CLASSES = ("clean", "crunch")
PRIMARY = {"clean": "default_dry", "crunch": "median_same_channel"}
# Dry, as the Morgan baselines were measured: time effects, spring, tremolo, gate and wah
# off, the time section itself on. Rooms are kept, as Morgan's rule kept its rooms.
DRY = [("reverbActive", False), ("delayActive", False), ("chorusActive", False),
       ("ampReverb", 0), ("ampTremoloDepth", 0), ("gateThreshold", -96),
       ("wahActive", False), ("timeSectionActive", True)]
MORGAN = {"clean": PLUGIN_ROOT / "docs/clean-baseline-choice.json",
          "crunch": PLUGIN_ROOT / "docs/crunch-baseline-choice.json"}


def _slug(name):
    return "".join(c if c.isalnum() else "-" for c in name).strip("-").lower()


def _sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _state(path):
    from format.parser import parse_file
    from format.structured import build

    return {p.key: p.value for p in build(parse_file(str(path))).parameters}


def menu():
    """name -> {source, channel}: complete Factory/ and Artists/ presets; incomplete ones listed apart."""
    from match.renderer_au import AudioUnitError
    from match.renderer_preset import complete_toneking_state, toneking_channel

    ok, left_out = {}, []
    for path in sorted(TK_ROOT.rglob("*.xml")):
        rel = path.relative_to(TK_ROOT)
        if rel.parts[0] not in ("Factory", "Artists"):
            continue
        name = str(rel.with_suffix(""))
        blob = path.read_bytes()
        try:
            complete_toneking_state(blob)
        except AudioUnitError:
            left_out.append(name)
            continue
        ok[name] = dict(source=str(path), channel=toneking_channel(blob))
    return ok, left_out


def dry():
    """Dry copies of every menu preset and Default.xml, regenerated, with the menu index."""
    from match.renderer_preset import toneking_channel

    ok, left_out = menu()
    ok["Default"] = dict(source=str(TK_ROOT / "Default.xml"),
                         channel=toneking_channel((TK_ROOT / "Default.xml").read_bytes()))
    shutil.rmtree(OUT / "dry", ignore_errors=True)
    (OUT / "dry").mkdir(parents=True)
    spec = OUT / "dry-spec.json"
    spec.write_text(json.dumps({"name": "dry", "parameters": [
        {"module": "", "key": k, "value": v} for k, v in DRY]}))
    for name, m in ok.items():
        out = OUT / "dry" / f"{_slug(name)}.xml"
        subprocess.run([sys.executable, str(PLUGIN_ROOT / "scripts/apply_spec.py"), "--template", m["source"],
                        "--spec", str(spec), "--out", str(out)], check=True, capture_output=True)
        st = _state(out)
        m.update(dry=str(out), sha256=_sha(out),
                 rooms=st.get("cab1RoomActive") == "1" or st.get("cab2RoomActive") == "1")
    (OUT / "menu.json").write_text(json.dumps({"menu": ok, "left_out": left_out}, indent=1))
    print(len(ok) - 1, "presets +Default;", "left out:", left_out)


def load_menu(with_default=False):
    m = json.loads((OUT / "menu.json").read_text())["menu"]
    return m if with_default else {k: v for k, v in m.items() if k != "Default"}


def parts(split):
    """slug -> {crop, judge_lag (Morgan convention), band, gain_class}."""
    if split == "dev":
        pin = json.loads(PINNED.read_text())["parts"]
        s3, s12 = G.parts(), SC.parts()
        out = {}
        for slug, meta in pin.items():
            if slug in s3:
                out[slug] = dict(crop=P.CROPS / slug, judge_lag=s3[slug]["judge_lag_samples"], **meta)
            else:
                out[slug] = dict(crop=s12[slug]["crop"], judge_lag=s12[slug]["judge_lag"], **meta)
        assert len(out) == 35, len(out)
        return out
    out = {s: dict(crop=p["crop"], judge_lag=p["judge_lag"], band=p["band"], gain_class=p["gain_class"])
           for s, p in CR.parts().items() if p["source"] == "sets12" and p["gain_class"] in CLASSES}
    assert len(out) == 20, len(out)
    return out


def _di(slug, part):
    import numpy as np

    path = OUT / "di" / f"{slug}.npy"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, CR.build_di("measfix", part))
    return np.load(path)


def _committed():
    """The held-out guard: the choice and the ledger entry are committed and unmodified."""
    def git(*a):
        return subprocess.run(["git", "-C", str(PLUGIN_ROOT), *a], capture_output=True, text=True)

    for path in (CHOICE, LEDGER):
        rel = str(path.relative_to(PLUGIN_ROOT))
        if git("ls-files", "--error-unmatch", rel).returncode or git("diff", "--quiet", "HEAD", "--", rel).returncode:
            return False
    uses = json.loads(LEDGER.read_text()).get("held_out_uses", [])
    return any(u.get("test_id") == TEST_ID for u in uses)


def _render_one(r, di):
    """One render after the preroll, checked for a start-up mute running past it."""
    import numpy as np

    from match.renderer import _hash_audio

    x = np.concatenate([np.zeros(PREROLL, np.float32), di])
    y = np.asarray(r.render(x, {}, di_sha256=_hash_audio(x)).audio, np.float64)
    y = y.mean(1) if y.ndim > 1 else y
    first_in = PREROLL + int(np.argmax(np.abs(di) > 1e-4))
    first_out = int(np.argmax(np.abs(y) > 1e-6))
    if not np.abs(y).max() > 1e-6 or first_out > first_in + LATENCY + 480:
        raise SystemExit(f"output starts at {first_out}, input at {first_in}: muted past the preroll")
    y = y[PREROLL:]
    if not len(y) or np.abs(y).max() < 1e-4:
        raise SystemExit("silent render")
    return y, first_out


def render(split, i, n):
    import numpy as np
    import soundfile as sf

    from match.renderer_preset import ToneKingPresetRenderer

    if split == "heldout" and not _committed():
        raise SystemExit("commit the choice and the ledger entry before held-out renders")
    ps = parts(split)
    m = load_menu(with_default=True)
    dis = {s: _di(s, ps[s]).astype(np.float32) for s in sorted(ps)}
    for name in sorted(m)[i::n]:
        done = OUT / "renders" / split / "_done" / _slug(name)
        if done.exists():
            continue
        r = ToneKingPresetRenderer(pathlib.Path(m[name]["dry"]), process_policy="fresh")
        starts = {}
        try:
            for s in sorted(ps):
                y, starts[s] = _render_one(r, dis[s])
                d = OUT / "renders" / split / s
                d.mkdir(parents=True, exist_ok=True)
                sf.write(d / f"{_slug(name)}.flac", y * (0.99 / np.abs(y).max()), P.SR, subtype="PCM_24")
        finally:
            r.close()
        done.parent.mkdir(parents=True, exist_ok=True)
        done.write_text(json.dumps({"sha256": _sha(m[name]["dry"]), "first_output_sample": starts}))
        print(split, name, flush=True)


def _distance(ref, y, di, judge_lag, half):
    from analysis.aligned import aligned_distance

    a, b = {"A": P.HALF_A, "B": P.HALF_B}[half]
    # The judge lag is the part's measured lag less the plugin latency (Morgan 52, Tone King 51).
    return aligned_distance(ref, y, di, lag=judge_lag + P.LATENCY - LATENCY,
                            render_latency=LATENCY, start_s=a, end_s=b).distance


def _score_part(job):
    import numpy as np

    split, slug, part, names = job
    ref = CR.mono(pathlib.Path(part["crop"]) / "reference.wav")
    di = np.load(OUT / "di" / f"{slug}.npy")
    res = {}
    for name in names:
        y = P.mono(OUT / "renders" / split / slug / f"{_slug(name)}.flac")
        res[name] = {h: _distance(ref, y, di, part["judge_lag"], h) for h in ("A", "B")}
    print(slug, flush=True)
    return slug, res


def score(split, workers=7):
    from concurrent.futures import ProcessPoolExecutor

    ps, names = parts(split), sorted(load_menu(with_default=True))
    missing = [n for n in names if not (OUT / "renders" / split / "_done" / _slug(n)).exists()]
    if missing:
        raise SystemExit(f"missing renders: {missing[:3]}")
    jobs = [(split, s, {**ps[s], "crop": str(ps[s]["crop"])}, names) for s in sorted(ps)]
    with ProcessPoolExecutor(workers) as ex:
        D = dict(ex.map(_score_part, jobs))
    (OUT / f"distances-{split}.json").write_text(json.dumps(D))


def repeat():
    """Repeatability in the deciding units: 3 repeats x 2 presets x 3 development parts."""
    import numpy as np

    from match.renderer_preset import ToneKingPresetRenderer

    ps, m = parts("dev"), load_menu(with_default=True)
    slugs = sorted(ps)[::12][:3]
    names = ["Default", "Factory/Crunchy Slap"]
    rows = []
    for name in names:
        for s in slugs:
            ref = CR.mono(pathlib.Path(ps[s]["crop"]) / "reference.wav")
            di = _di(s, ps[s])
            d = []
            for _ in range(3):
                r = ToneKingPresetRenderer(pathlib.Path(m[name]["dry"]), process_policy="fresh")
                try:
                    y, _ = _render_one(r, di.astype(np.float32))
                finally:
                    r.close()
                d.append([_distance(ref, y, di, ps[s]["judge_lag"], h) for h in ("A", "B")])
            logs = np.log(np.array(d))
            rows.append(dict(preset=name, part=s, distances=d,
                             max_spread=float((logs.max(0) - logs.min(0)).max())))
            print(rows[-1], flush=True)
    out = {"rows": rows, "max_log_spread": max(r["max_spread"] for r in rows)}
    (OUT / "repeat.json").write_text(json.dumps(out, indent=1))
    print("max log-distance spread over repeats:", out["max_log_spread"])


def _mean(D, s, n):
    v = D.get(s, {}).get(n)
    if not v:
        return None
    a, b = v.get("A"), v.get("B")
    return (a + b) / 2 if a and b else None


def _rule(D, slugs, names):
    """The preset with the lowest median mean-of-halves over parts where every candidate is scored."""
    use = [s for s in slugs if all(_mean(D, s, n) is not None for n in names)]
    med = {n: statistics.median(_mean(D, s, n) for s in use) for n in names}
    order = sorted(med, key=lambda n: (med[n], n))
    return order[0], med, use, order


def choose():
    D = json.loads((OUT / "distances-dev.json").read_text())
    ps, m = parts("dev"), load_menu()
    head = subprocess.run(["git", "-C", str(PLUGIN_ROOT), "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    out = {"rule": "docs/toneking-baseline-plan.md", "code_commit": head, "presets": {}, "channel": {},
           "parts_used": {}, "median_distance": {}, "runner_up": {}, "per_channel": {}, "lbo_picks": {},
           "left_out": json.loads((OUT / "menu.json").read_text())["left_out"],
           "dry_sha256": {n: v["sha256"] for n, v in load_menu(with_default=True).items()}}
    for c in CLASSES:
        slugs = [s for s in ps if ps[s]["gain_class"] == c]
        best, med, use, order = _rule(D, slugs, list(m))
        out["presets"][c], out["channel"][c] = best, m[best]["channel"]
        out["parts_used"][c] = len(use)
        out["median_distance"][c] = round(med[best], 4)
        out["runner_up"][c] = {"preset": order[1], "median_distance": round(med[order[1]], 4)}
        for ch in sorted({v["channel"] for v in m.values()}):
            out["per_channel"][f"{c}|{ch}"] = _rule(D, slugs, [n for n in m if m[n]["channel"] == ch])[0]
        out["lbo_picks"][c] = {b: _rule(D, [s for s in slugs if ps[s]["band"] != b], list(m))[0]
                               for b in sorted({ps[s]["band"] for s in slugs})}
    CHOICE.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "dry_sha256"}, indent=1))


def _morgan(split):
    """{slug: {class: {amp: mean-of-halves}}} for the Morgan starting presets, from existing distances."""
    if split == "heldout":
        D = json.loads((CR.OUT / "distances.json").read_text())
    else:
        from learn import sound_desc_eval as E

        D = {s: v["D"] for s, v in E.test_parts().items()}
    out = {}
    for c, path in MORGAN.items():
        for amp, n in json.loads(path.read_text())["presets"].items():
            for s, d in D.items():
                a, b = d.get(f"flat|{amp}|measfix_A", {}).get(n), d.get(f"flat|{amp}|measfix_B", {}).get(n)
                if a and b and a[0] and b[0]:
                    out.setdefault(s, {}).setdefault(c, {})[amp] = (a[0] + b[0]) / 2
    return out


def report(split, choice=None):
    D = json.loads((OUT / f"distances-{split}.json").read_text())
    ps, m = parts(split), load_menu()
    choice = choice or json.loads(CHOICE.read_text())["presets"]
    morgan = _morgan(split)

    def median_of(names):
        return lambda s: statistics.median(v for v in (_mean(D, s, n) for n in names) if v)

    def rows_for(cls, chosen, against, slugs):
        rows = []
        for s in slugs:
            a, b = _mean(D, s, chosen(s)), against(s)
            if a and b:
                rows.append((ps[s]["band"], math.log(a / b)))
        return rows

    res = {}
    for c in CLASSES:
        slugs = [s for s in ps if ps[s]["gain_class"] == c]
        pick = choice[c]
        ch = m[pick]["channel"]
        comps = {"default_dry": lambda s: _mean(D, s, "Default"),
                 "median_same_channel": median_of([n for n in m if m[n]["channel"] == ch]),
                 "median_all": median_of(list(m)),
                 "median_rooms_off": median_of([n for n in m if not m[n]["rooms"]])}
        if c == "clean":
            comps["median_named_clean"] = median_of([n for n in m if "clean" in n.lower()])
        for amp in ("pr12", "sw50r", "ac20"):
            comps[f"morgan_{amp}"] = lambda s, amp=amp: morgan.get(s, {}).get(c, {}).get(amp)
        for k, f in comps.items():
            rows = rows_for(c, lambda s: pick, f, slugs)
            if rows:
                res[f"{c}|chosen_vs_{k}"] = CR.stats(rows)
        oracle = [(ps[s]["band"], math.log(min(v for v in (_mean(D, s, n) for n in m) if v) / _mean(D, s, pick)))
                  for s in slugs if _mean(D, s, pick)]
        res[f"{c}|oracle_vs_chosen"] = CR.stats(oracle)
        ranks = []
        for s in slugs:
            vals = sorted((v, n) for n, v in ((n, _mean(D, s, n)) for n in m) if v)
            ranks.append(1 + [n for _, n in vals].index(pick))
        res[f"{c}|chosen_rank"] = {"median": statistics.median(ranks), "of": len(m), "ranks": ranks}
        if split == "dev":
            # Leave-band-out: the rule run without each band, applied to that band.
            for k in (PRIMARY[c], "median_all"):
                rows = []
                for b in sorted({ps[s]["band"] for s in slugs}):
                    p_b = _rule(D, [s for s in slugs if ps[s]["band"] != b], list(m))[0]
                    f = (comps[k] if k != "median_same_channel" else
                         median_of([n for n in m if m[n]["channel"] == m[p_b]["channel"]]))
                    rows += rows_for(c, lambda s: p_b, f, [s for s in slugs if ps[s]["band"] == b])
                res[f"{c}|lbo_vs_{k}"] = CR.stats(rows)
    return res


def check():
    out = {"dev": report("dev"), "heldout": report("heldout")}
    rep = OUT / "repeat.json"
    out["repeat_max_log_spread"] = json.loads(rep.read_text())["max_log_spread"] if rep.exists() else None
    for c in CLASSES:
        v = out["heldout"][f"{c}|chosen_vs_{PRIMARY[c]}"]
        out[f"adopt_{c}"] = v["hi90"] < 0
    (OUT / "check.json").write_text(json.dumps(out, indent=1, default=float))
    for split in ("dev", "heldout"):
        for k, s_ in sorted(out[split].items()):
            if "mean" in s_:
                print(f"{split:8s} {k:36s} mean {s_['mean']:+.3f} [{s_['lo90']:+.3f}, {s_['hi90']:+.3f}] "
                      f"W/T/L {s_['wins']}/{s_['ties']}/{s_['losses']} bands {s_['bands']}")
            else:
                print(f"{split:8s} {k:36s} median rank {s_['median']} of {s_['of']}")
    print({k: v for k, v in out.items() if k.startswith(("adopt", "repeat"))})


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "render":
        render(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    elif cmd == "score":
        score(sys.argv[2])
    else:
        {"dry": dry, "repeat": repeat, "choose": choose, "check": check}[cmd]()
