"""The crunch starting presets from the labels' centre (Cen): recipes `start/crunch-<amp>` for generate's step 4.

The ladder (docs/preset-ladder-plan.md, `centres.json`'s all-labels cells) read Cen better than S, the crunch
baselines made dry, both by the score (docs/preset-ladder-results.md) and by ear on crunch
(docs/ladder-ear-results.md). The user approved switching generate's crunch start to Cen on 2026-11-19.

`build` writes one recipe per amp into packs/morgan/recipes.json: every setting where Cen differs from the factory
baseline made dry with `dry/<amp>` (the effects, transpose and selector are refused: Cen holds them at S's), plus the
output gain fitted so the preset plays at S's loudness through the class's two stock DIs, as the model path's loudness
step fits it (`loudness_step.matched_gain`, fitted from 6 CPU renders, stored in `--gains`). `check` applies the factory
baseline, `dry/<amp>` and `start/crunch-<amp>` with apply_spec and requires the result to equal Cen's cell on every
setting but the output gain. Dev machine only: it reads ~/ndsp-presets and the factory presets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from format.parser import parse_file  # noqa: E402
from format.structured import build as build_preset  # noqa: E402
from format.translate import from_binary  # noqa: E402
from packs.loader import load_pack  # noqa: E402

HOME = pathlib.Path("~/ndsp-presets").expanduser()
CENTRES = HOME / "learn/trusted-data/pipeline-fix/ladder/centres.json"
FACTORY = pathlib.Path("/Library/Audio/Presets/Neural DSP/Morgan Amps Suite")
RECIPES = ROOT / "packs/morgan/recipes.json"
GAINS = HOME / "learn/cen-crunch-start/gains.json"
# generate's crunch baselines (skills/generate/SKILL.md step 4; `knob_ceiling.START["crunch"]`, the ladder's S).
BASELINE = {"pr12": "Artists/Keyan Houshmand/Modern Metal (Pick Hard).xml",
            "sw50r": "Neural DSP/Hair Metal.xml",
            "ac20": "Neural DSP/AC20 Mid-Gain Drive.xml"}
AMP_NAME = {"pr12": "PR12", "sw50r": "SW50R", "ac20": "AC20"}
OUTPUT = ("parameters", "outputGain")
# Cen holds these at S's (effects follow research; transpose and the amp are not the centre's).
REFUSED_MODULES = {"delay", "reverb", "tremolo", "fxParameters"}
REFUSED_KEYS = {("parameters", "doublerActive"), ("parameters", "doublerSpread"), ("parameters", "transpose"),
                ("pr12Amp", "pr12Reverb"), ("pr12Amp", "pr12Dwell"), ("sw50rAmp", "sw50rReverb"),
                ("", "selectedAmp")}
TOL = 1e-4


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def settings_of(path):
    """A preset's {(module, key): stored} (the plugin's stored strings)."""
    return {k: p.value for k, p in build_preset(parse_file(str(path))).by_path.items()}


def apply(template, recipes, out):
    cmd = [sys.executable, str(ROOT / "scripts/apply_spec.py"), "--template", str(template), "--out", str(out),
           "--strip-irs"]
    for r in recipes:
        cmd += ["--recipe", r]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return settings_of(out)


def same(a, b):
    if a == b:
        return True
    try:
        return abs(float(a) - float(b)) <= TOL * max(1.0, abs(float(b)))
    except ValueError:
        return False


def human(pack, module, key, stored):
    """Cen's stored value in the unit a recipe is written in."""
    spec = pack.require(module, key)
    if spec.kind == "enum" and spec.members:
        name = spec.member_name(stored)
        if name is None:
            raise SystemExit(f"{module}/{key}: {stored!r} is not a known member")
        return name
    v = from_binary(spec.kind, stored, spec.unit)
    return round(v, 6) if isinstance(v, float) else v


def cen_cells():
    doc = json.loads(CENTRES.read_text())
    return doc, {a: doc["centres"]["cen"][a]["crunch"] for a in BASELINE}


def cmd_fit(args):
    """Cen's crunch cell on each amp through the class's two stock DIs (fresh, primed, trimmed, as the model path's
    render stage), and the output gain that brings it to S's loudness there (`loudness_step.matched_gain` against
    `ls/s-table.json`). 6 CPU renders; main .venv. -> --out."""
    import numpy as np

    from learn import amp_di_compare as A1
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import loudness_step as L
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_aug as SA
    from learn import song_bank as B

    _, cells = cen_cells()
    tab = json.loads((P.out_dir() / "ls" / "s-table.json").read_text())["table"]
    stock = json.loads((A1.a1_dir() / "plan.json").read_text())["stock"]["crunch"]
    dis = [B.measure(PS.section_audio(s["di_path"], s["start_s"])).astype(np.float32) for s in stock]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    out = {"stock": [s["di"] for s in stock], "centres_sha256": sha256(CENTRES)}
    for a in BASELINE:
        x = cells[a]
        st = LO.tdict(x["settings"])
        lu = [float(SA.lufs(np.asarray(AM.fresh_render(CB.new_renderer, di, x["select"], st, st),
                                       np.float64)[trim[0]:trim[1]])) for di in dis]
        g0 = float(x["settings"]["/".join(OUTPUT)])
        gain, want, short = L.matched_gain(g0, tab[a]["crunch"], lu)
        out[a] = {"lufs": lu, "S_lufs": tab[a]["crunch"], "g0": g0, "gain": gain, "want": want, "short": short}
        print(f"{a}: {g0:+.1f} -> {gain:+.1f} dB" + (f" ({short:.2f} dB short)" if short else ""), flush=True)
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text(json.dumps(out, indent=1))


def cmd_build(args):
    pack = load_pack("morgan")
    doc, cells = cen_cells()
    gains = json.loads(pathlib.Path(args.gains).read_text())
    raw = json.loads(RECIPES.read_text())
    layer = {}
    with tempfile.TemporaryDirectory() as td:
        for amp, rel in BASELINE.items():
            cell = {tuple(k.rsplit("/", 1)): v for k, v in cells[amp]["settings"].items()}
            dry = apply(FACTORY / rel, [f"dry/{amp}"], pathlib.Path(td) / f"{amp}.xml")
            if str(cells[amp]["select"]) != dry[("", "selectedAmp")]:
                raise SystemExit(f"{amp}: Cen selects {cells[amp]['select']}, the baseline {dry[('', 'selectedAmp')]}")
            params = []
            for (m, k), v in sorted(cell.items()):
                if (m, k) == OUTPUT or same(dry.get((m, k)), v):
                    continue
                if m in REFUSED_MODULES or (m, k) in REFUSED_KEYS:
                    raise SystemExit(f"{amp}: Cen moves {m}/{k} ({dry.get((m, k))} -> {v}), which it should hold at S's")
                if (m, k) not in dry:
                    raise SystemExit(f"{amp}: {m}/{k} is not in the baseline")
                params.append({"module": m, "key": k, "value": human(pack, m, k, v)})
            g = gains[amp]
            params.append({"module": OUTPUT[0], "key": OUTPUT[1], "value": round(float(g["gain"]), 1)})
            short = f", {g['short']:.1f} dB short at the output's limit" if g["short"] else ""
            layer[f"crunch-{amp}"] = {
                "title": f"{AMP_NAME[amp]} crunch start: the labels' centre",
                "use_when": f"generate's crunch start on {AMP_NAME[amp]}, after dry/{amp} on the factory crunch baseline",
                "for_amp": AMP_NAME[amp],
                "note": (f"Apply on {rel} after dry/{amp}. The centre of the trusted training labels for "
                         f"{AMP_NAME[amp]} crunch (the ladder's Cen), with the output fitted to the baseline's "
                         f"loudness through two stock DIs ({g['g0']:+.1f} -> {g['gain']:+.1f} dB{short}). Effects "
                         f"stay the baseline's dry ones, for research to set."),
                "parameters": params,
                "evidence": {"class": "measured",
                             "source": "docs/preset-ladder-results.md, docs/ladder-ear-results.md",
                             "centres_sha256": sha256(CENTRES), "model_sha256": doc["model_sha256"],
                             "records": doc["records_used"][f"None|{amp}|crunch"]["records"],
                             "built_by": "learn/cen_crunch_start.py"},
            }
            print(f"{amp}: {len(params)} settings, output {g['g0']:+.1f} -> {g['gain']:+.1f} dB")
    if "start" in raw["layers"]:
        raise SystemExit("recipes.json already has a start layer: restore it from git before rebuilding")
    text, end = RECIPES.read_text(), "\n  }\n}"
    body = text.rstrip("\n")
    if not body.endswith(end):
        raise SystemExit("recipes.json does not end with its layers object")
    block = json.dumps(layer, indent=2, ensure_ascii=False).replace("\n", "\n    ")
    RECIPES.write_text(body[:-len(end)] + ',\n    "start": ' + block + end + text[len(body):])
    if json.loads(RECIPES.read_text())["layers"]["start"] != layer:
        raise SystemExit("recipes.json: the start layer did not read back")


def cmd_check(_args):
    _, cells = cen_cells()
    bad = 0
    with tempfile.TemporaryDirectory() as td:
        for amp, rel in BASELINE.items():
            got = apply(FACTORY / rel, [f"dry/{amp}", f"start/crunch-{amp}"], pathlib.Path(td) / f"{amp}.xml")
            cell = {tuple(k.rsplit("/", 1)): v for k, v in cells[amp]["settings"].items()}
            diff = [(m, k, got.get((m, k)), v) for (m, k), v in cell.items()
                    if (m, k) != OUTPUT and not same(got.get((m, k)), v)]
            bad += len(diff)
            print(f"{amp}: {len(cell) - 1 - len(diff)}/{len(cell) - 1} settings equal Cen's; output {got[OUTPUT]}")
            for d in diff:
                print("  differs:", d)
    if bad:
        raise SystemExit(f"{bad} setting(s) differ from Cen")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit")
    f.add_argument("--out", default=str(GAINS))
    b = sub.add_parser("build")
    b.add_argument("--gains", default=str(GAINS), help="the fitted output gains (`fit`'s file)")
    sub.add_parser("check")
    args = ap.parse_args(argv)
    {"fit": cmd_fit, "build": cmd_build, "check": cmd_check}[args.cmd](args)


if __name__ == "__main__":
    main()
